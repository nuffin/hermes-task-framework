#!/usr/bin/env python3
"""Opt-in cooperative task checkpoint transport. No arbitrary-writer guarantee."""
from __future__ import annotations
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import uuid
import contextvars
import functools
import sys

TASK_SCRIPTS = Path(__file__).resolve().parents[2] / "task-framework" / "scripts"
sys.path.insert(0, str(TASK_SCRIPTS))
from task_symlink_policy import require_tasks_root  # pyright: ignore[reportMissingImports]  # noqa: E402

_DEADLINE: contextvars.ContextVar[float | None] = contextvars.ContextVar('task_sync_deadline', default=None)


def bounded_transaction(function):
    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        token = _DEADLINE.set(time.monotonic() + 180)
        try:
            return function(*args, **kwargs)
        finally:
            _DEADLINE.reset(token)
    return wrapped


def run(root, *args, timeout: float = 30.0, env=None):
    deadline = _DEADLINE.get()
    if deadline is not None:
        timeout = min(timeout, deadline - time.monotonic())
        if timeout <= 0:
            raise ValueError('sync transaction timeout')
    environment = os.environ.copy()
    for key in list(environment):
        if key.startswith('GIT_') and key not in {'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_SYSTEM',
                                                   'GIT_CONFIG_NOSYSTEM', 'GIT_AUTHOR_NAME',
                                                   'GIT_AUTHOR_EMAIL', 'GIT_COMMITTER_NAME',
                                                   'GIT_COMMITTER_EMAIL'}:
            environment.pop(key)
    environment.update(GIT_TERMINAL_PROMPT='0', GIT_EDITOR='true', GIT_SEQUENCE_EDITOR='true')
    if env:
        environment.update(env)
    import signal
    command = ['git']
    cache_only_gpg = Path(__file__).with_name('gpg-agent-cache-only.sh')
    if cache_only_gpg.is_file():
        # The deploy bundle co-locates this trusted wrapper. Source-tree runs retain
        # the user's ordinary Git/GPG configuration unchanged.
        command.extend(['-c', f'gpg.program={cache_only_gpg}'])
    command.extend(['-C', str(root), *args])
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=environment, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        raise
    if process.returncode:
        raise ValueError(stderr.decode(errors='replace').strip() or 'git command failed')
    return stdout.decode(errors='surrogateescape').rstrip('\n')


def state_dir(root):
    common = Path(run(root, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    return common / 'task-sync'


@contextlib.contextmanager
def writer_lock(root):
    """Shared lease used by canonical writers and opt-in sync."""
    import sys
    scripts = Path(__file__).resolve().parents[2] / 'task-framework/scripts'
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from task_write_lock import task_writer_lock
    with task_writer_lock(root, reentrant=False) as descriptor:
        yield descriptor


def live_writer(root):
    """Conservative Linux guard; shells alone are not evidence of a writer."""
    proc = Path('/proc')
    if not proc.exists():
        raise ValueError('live writer guard requires Linux /proc')
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            cwd = (entry / 'cwd').resolve(strict=True)
            command = (entry / 'cmdline').read_bytes().lower()
            if cwd.is_relative_to(root) and (b'hermes' in command or b'python' in command):
                raise ValueError(f'live task writer process: {entry.name}')
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue


def fingerprint(root, deadline=None):
    digest = hashlib.sha256()
    names = run(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0')
    for name in sorted(set(names)):
        if not name:
            continue
        if deadline and time.monotonic() > deadline:
            raise ValueError('snapshot timeout')
        p = root / name
        digest.update(os.fsencode(name))
        try:
            stat = p.lstat()
            digest.update(str((stat.st_mode, stat.st_size, stat.st_mtime_ns)).encode())
            if p.is_symlink():
                digest.update(os.fsencode(os.readlink(p)))
            elif p.is_file():
                with p.open('rb') as stream:
                    while block := stream.read(1024 * 1024):
                        if deadline and time.monotonic() > deadline:
                            raise ValueError('snapshot timeout')
                        digest.update(block)
        except FileNotFoundError:
            digest.update(b'missing')
    digest.update(run(root, 'ls-files', '--stage', '-z').encode(errors='surrogateescape'))
    digest.update(run(root, 'rev-parse', 'HEAD').encode())
    return digest.hexdigest()


def unsafe_path(path):
    return any(re.fullmatch(r'\.git(?:\.\d+)?', part) or
               part.lower() in {'.env', 'credentials.json', 'id_rsa', 'id_ed25519', '.netrc'} or
               part.lower().endswith(('.pem', '.key')) or part.lower().startswith('.env.')
               for part in Path(path).parts)


def validate_content(root, max_blob_bytes, index_env):
    changed = run(root, 'diff', '--cached', '--name-only', '--diff-filter=ACMRT', '-z', 'HEAD', env=index_env).split('\0')
    for relative in changed:
        if relative and unsafe_path(relative):
            raise ValueError(f'unsafe path: {relative}')
    for line in run(root, 'ls-files', '--stage', '-z', env=index_env).split('\0'):
        if line.startswith('160000 ') and line.split('\t', 1)[-1] in changed:
            raise ValueError('new/changed nested repository/gitlink refused')
    additions = run(root, 'diff', '--cached', '--name-only', '--diff-filter=AM', '-z', 'HEAD', env=index_env)
    for path in additions.split('\0'):
        if path and int(run(root, 'cat-file', '-s', ':' + path, env=index_env)) > max_blob_bytes:
            raise ValueError(f'new blob exceeds size limit: {path}')


@bounded_transaction
def sync(root: Path, remote: str, remote_url: str, branch: str, node: str,
         execute: bool, authorize_push: bool, cooperative_writers: bool,
         max_blob_bytes: int = 10485760, timeout: int = 30, retries: int = 2) -> dict:
    root = Path(root).expanduser().resolve()
    if not execute or not authorize_push or not cooperative_writers:
        raise ValueError('requires --execute, auto_push and cooperative_writers authorization')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', node):
        raise ValueError('invalid node identity')
    if branch != 'main' or run(root, 'branch', '--show-current') != 'main':
        raise ValueError('sync requires main')
    if str(root) != run(root, 'rev-parse', '--show-toplevel'):
        raise ValueError('tasks root must be exact repository root')
    if not remote or remote.startswith('-') or not remote_url:
        raise ValueError('explicit remote and remote_url required')
    if timeout <= 0 or timeout > 60 or retries < 0 or retries > 5 or max_blob_bytes <= 0:
        raise ValueError('invalid limits')
    for option in ([], ['--push']):
        if run(root, 'remote', 'get-url', '--all', *option, remote).splitlines() != [remote_url]:
            raise ValueError('remote URL differs from authorization')
    deadline = time.monotonic() + 180
    initial_post_flight = require_tasks_root(root)
    def g(where, *args, **kw):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('sync transaction timeout')
        return run(where, *args, timeout=min(timeout, remaining), **kw)
    with writer_lock(root) as writer_descriptor:
        live_writer(root)
        directory = state_dir(root)
        gitdir = Path(g(root, 'rev-parse', '--absolute-git-dir'))
        for marker in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply', 'index.lock'):
            if (gitdir / marker).exists():
                raise ValueError(f'interrupted/busy Git operation: {marker}')
        journal = directory / 'journal.json'
        if journal.exists():
            previous = json.loads(journal.read_text())
            if previous.get('phase') in {'promoting', 'conflict', 'promotion-failed', 'recovery-required'}:
                raise ValueError('unresolved transaction; inspect journal and backup refs manually')
        transaction = node + '-' + uuid.uuid4().hex
        prefix = 'refs/task-sync/' + transaction
        record = {
            'transaction': transaction,
            'root': str(root),
            'backup_ref': prefix,
            'postflight_precheck': {'scope': 'tasks-root', 'ok': initial_post_flight['ok'],
                                   'symlink_count': len(initial_post_flight['symlinks'])},
        }
        def save(phase, **fields):
            record.update(phase=phase, **fields)
            event_dir = directory / transaction
            event_dir.mkdir(exist_ok=True)
            event = event_dir / (str(time.time_ns()) + '-' + phase + '.json')
            with event.open('x') as output:
                output.write(json.dumps(record, indent=2) + '\n')
            temporary = journal.with_suffix('.tmp')
            temporary.write_text(json.dumps(record, indent=2) + '\n')
            os.replace(temporary, journal)
        before = fingerprint(root, deadline)
        base = g(root, 'rev-parse', 'HEAD')
        g(root, 'update-ref', prefix + '/before', base)
        work = Path(tempfile.mkdtemp(prefix='checkpoint-', dir=directory))
        index = work / 'index'
        shutil.copyfile(gitdir / 'index', index)
        original_index = (gitdir / 'index').read_bytes()
        env = {'GIT_INDEX_FILE': str(index)}
        candidate = base
        try:
            validate_content(root, max_blob_bytes, env)
            snapshots = [('staged', g(root, 'write-tree', env=env))]
            g(root, 'add', '-A', '--', '.', env=env)
            validate_content(root, max_blob_bytes, env)
            snapshots.append(('working', g(root, 'write-tree', env=env)))
            checkout = work / 'integration'
            g(root, 'worktree', 'add', '--detach', str(checkout), base)
            for phase, tree in snapshots:
                if tree != g(checkout, 'rev-parse', 'HEAD^{tree}'):
                    g(checkout, 'read-tree', '-m', '-u', 'HEAD', tree)
                    g(checkout, 'commit', '-m', f'task checkpoint {node}: {phase}')
                    if g(checkout, 'rev-parse', 'HEAD^{tree}') != tree:
                        raise ValueError('commit hook changed snapshot tree; manual review required')
                candidate = g(checkout, 'rev-parse', 'HEAD')
                g(root, 'update-ref', prefix + '/' + phase, candidate)
            save('checkpointed', base=base, checkpoint=candidate)
            if fingerprint(root, deadline) != before:
                raise ValueError('concurrent edit during checkpoint; backup retained')
            for attempt in range(retries + 1):
                g(root, 'fetch', '--no-tags', remote, 'refs/heads/main')
                upstream = g(root, 'rev-parse', 'FETCH_HEAD')
                # Replay actual commits: preserve staged/working and user history.
                try:
                    g(checkout, 'rebase', upstream)
                except ValueError as exc:
                    # Only root derived-index conflicts are mechanically resolvable.
                    # Any task conflict stops in the isolated worktree, never in main.
                    for continuation in range(100):
                        conflicts = g(checkout, 'diff', '--name-only', '--diff-filter=U', '-z').split('\0')
                        conflicts = [p for p in conflicts if p]
                        if not conflicts or set(conflicts) - {'README.md', 'TASKS.md'}:
                            save('conflict', integration=str(checkout))
                            raise ValueError('isolated rebase conflict; main untouched: ' + str(exc)) from exc
                        for name in conflicts:
                            # The current rebased HEAD supplies the integrated version.
                            try:
                                g(checkout, 'restore', '--source=HEAD', '--staged', '--worktree', '--', name)
                            except ValueError:
                                g(checkout, 'rm', '-f', '--', name)
                        try:
                            g(checkout, 'rebase', '--continue')
                            break
                        except ValueError as next_exc:
                            exc = next_exc
                    else:
                        raise ValueError('derived conflict continuation limit')
                postflight_rebased = require_tasks_root(checkout)
                generator = Path(__file__).resolve().parents[2] / 'task-framework/scripts/update-index.py'
                import sys
                remaining = deadline - time.monotonic()
                subprocess.run([sys.executable, str(generator)], check=True, capture_output=True,
                               timeout=max(0.001, min(timeout, remaining)),
                               pass_fds=(writer_descriptor,),
                               env={**os.environ, 'HERMES_TASKS_ROOT': str(checkout),
                                    'HERMES_TASK_WRITER_LOCK_FD': str(writer_descriptor)})
                g(checkout, 'add', '-A', '--', 'README.md', 'TASKS.md')
                generated = g(checkout, 'write-tree')
                integrated = g(checkout, 'rev-parse', 'HEAD')
                if generated != g(checkout, 'rev-parse', 'HEAD^{tree}'):
                    g(checkout, 'commit', '-m', f'task indexes {node}')
                    integrated = g(checkout, 'rev-parse', 'HEAD')
                    if g(checkout, 'rev-parse', 'HEAD^{tree}') != generated:
                        raise ValueError('index commit hook changed generated tree')
                g(root, 'update-ref', prefix + '/integrated', integrated)
                g(root, 'read-tree', integrated, env=env)
                validate_content(root, max_blob_bytes, env)
                g(root, 'read-tree', candidate, env=env)
                if fingerprint(root, deadline) != before:
                    raise ValueError('concurrent edit; refusing push/promotion')
                g(root, 'update-index', '--refresh', env=env)
                incoming = g(root, 'diff', '--name-only', '--diff-filter=A', '-z', candidate, integrated)
                for incoming_path in filter(None, incoming.split('\0')):
                    destination = root / incoming_path
                    if os.path.lexists(destination):
                        raise ValueError('incoming path would overwrite local untracked/ignored content: ' + incoming_path)
                if fingerprint(root, deadline) != before:
                    raise ValueError('concurrent edit; refusing push/promotion')
                try:
                    g(root, 'push', remote, integrated + ':refs/heads/main')
                except ValueError:
                    save('push-failed', attempt=attempt)
                    if attempt == retries:
                        raise
                    # Start next isolated replay from original snapshot, never a dirty main.
                    g(checkout, 'reset', '--keep', candidate)
                    continue
                observed = g(root, 'ls-remote', remote, 'refs/heads/main').split()[0]
                if observed != integrated:
                    save('remote-advanced', integrated=integrated)
                    raise ValueError('remote advanced after push; local snapshot retained for retry')
                live_writer(root)
                if fingerprint(root, deadline) != before:
                    raise ValueError('concurrent edit after push; refusing promotion')
                postflight_final = require_tasks_root(root)
                save('postflight', postflight={
                    'scope': 'tasks-root',
                    'ok': postflight_final['ok'],
                    'symlink_count': len(postflight_final['symlinks']),
                    'rebased_symlink_count': len(postflight_rebased['symlinks']),
                })
                # Check with the private final-snapshot index before touching the live index.
                g(root, 'read-tree', '-n', '-m', '-u', candidate, integrated, env=env)
                save('promoting', integrated=integrated, original_index=str(work / 'original-index'))
                (work / 'original-index').write_bytes(original_index)
                g(root, 'read-tree', candidate)
                owned_index = (gitdir / 'index').read_bytes()
                try:
                    g(root, 'update-index', '--refresh')
                    owned_index = (gitdir / 'index').read_bytes()
                    g(root, 'read-tree', '-m', '-u', candidate, integrated)
                    g(root, 'update-ref', 'refs/heads/main', integrated, base)
                except BaseException:
                    # Never blindly restore over an independently changed index.
                    acquired = False
                    try:
                        with (gitdir / 'index.lock').open('xb') as rollback:
                            acquired = True
                            if (gitdir / 'index').read_bytes() == owned_index:
                                rollback.write(original_index)
                                rollback.flush()
                                os.replace(gitdir / 'index.lock', gitdir / 'index')
                    finally:
                        if acquired and (gitdir / 'index.lock').exists():
                            (gitdir / 'index.lock').unlink()
                        save('promotion-failed', integrated=integrated)
                    raise
                save('complete', integrated=integrated)
                g(root, 'worktree', 'remove', str(checkout))
                return record
            raise ValueError('retry limit exhausted')
        except BaseException:
            checkout = work / 'integration'
            if checkout.exists() and record.get('phase') not in {'conflict', 'promoting', 'promotion-failed'}:
                try:
                    g(root, 'worktree', 'remove', str(checkout))
                except (ValueError, subprocess.SubprocessError):
                    save('recovery-required', integration=str(checkout))
            raise
        finally:
            if (work / 'integration').exists() is False:
                shutil.rmtree(work)
