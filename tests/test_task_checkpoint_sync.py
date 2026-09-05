"""Checkpoint synchronization contract tests using only temporary real repositories."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = (Path(__file__).resolve().parents[1] / "skills" /
          "task-cross-machine-sync" / "scripts" / "task_checkpoint_sync.py")


class TaskCheckpointSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("task_checkpoint_sync_under_test", SCRIPT)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="checkpoint-sync-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "tasks"
        self.remote = self.base / "remote.git"
        # Isolate Git identity, signing, hooks and config from the developer machine.
        self.environment = patch.dict(os.environ, {
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "Checkpoint Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Checkpoint Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.git(self.base, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.git(self.base, "init", "--initial-branch=main", str(self.root))
        self.write("note.txt", "base\n")
        self.write("delete.txt", "delete me\n")
        self.write(".gitignore", "ignored/\n")
        self.git(self.root, "add", ".")
        self.git(self.root, "commit", "-m", "initial fixture")
        self.git(self.root, "remote", "add", "origin", str(self.remote))
        self.git(self.root, "push", "--set-upstream", "origin", "main")

    def git(self, root, *args):
        result = subprocess.run(["git", "-C", str(root), *args], text=True,
                                capture_output=True, timeout=20, check=False)
        if result.returncode:
            self.fail(f"git {args!r} failed ({result.returncode}): {result.stderr}")
        return result.stdout.strip()

    def write(self, name, content, root=None):
        target = (root or self.root) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def sync(self, **overrides):
        options = dict(root=self.root, remote="origin", remote_url=str(self.remote),
                       branch="main", node="test-node", execute=True,
                       authorize_push=True, cooperative_writers=True,
                       max_blob_bytes=10485760, timeout=10, retries=2)
        options.update(overrides)
        return self.module.sync(**options)

    def snapshot(self):
        files = {str(p.relative_to(self.root)): p.read_bytes()
                 for p in self.root.rglob("*")
                 if p.is_file() and ".git" not in p.relative_to(self.root).parts}
        return (self.git(self.root, "rev-parse", "HEAD"),
                self.git(self.root, "ls-files", "--stage"), files)

    def assert_published(self):
        self.assertEqual(self.git(self.root, "rev-parse", "HEAD"),
                         self.git(self.remote, "rev-parse", "refs/heads/main"))
        self.assertEqual(self.git(self.root, "status", "--porcelain"), "")
        self.assertEqual(self.git(self.root, "branch", "--show-current"), "main")

    def peer(self):
        peer = self.base / "peer"
        self.git(self.base, "clone", str(self.remote), str(peer))
        return peer

    def test_mixed_checkpoint_preserves_partial_index_untracked_ignored_and_deletion(self):
        self.write("note.txt", "staged version\n")
        self.git(self.root, "add", "note.txt")
        staged_blob = self.git(self.root, "rev-parse", ":note.txt")
        self.write("note.txt", "unstaged final version\n")
        self.write("new.txt", "new untracked task\n")
        ignored = self.write("ignored/cache.txt", "local cache must survive\n")
        (self.root / "delete.txt").unlink()
        result = self.sync()
        self.assertIsInstance(result, dict)
        self.assert_published()
        self.assertEqual((self.root / "note.txt").read_text(), "unstaged final version\n")
        self.assertEqual((self.root / "new.txt").read_text(), "new untracked task\n")
        self.assertEqual(ignored.read_text(), "local cache must survive\n")
        self.assertFalse((self.root / "delete.txt").exists())
        self.assertNotIn("ignored/", self.git(self.root, "ls-tree", "-r", "--name-only", "HEAD"))
        self.assertEqual(self.git(self.remote, "show", "main:note.txt"), "unstaged final version")
        self.assertEqual(self.git(self.remote, "show", "main:new.txt"), "new untracked task")
        refs = self.git(self.root, "for-each-ref", "--format=%(refname)").splitlines()
        backups = [ref for ref in refs if not ref.startswith(("refs/heads/", "refs/remotes/", "refs/tags/"))]
        self.assertTrue(backups, "Checkpoint must retain durable recovery refs")
        objects = self.git(self.root, "rev-list", "--objects", *backups)
        self.assertIn(staged_blob, {line.split()[0] for line in objects.splitlines()},
                      "The partially staged version must remain reachable through backup refs")

    def test_clean_sync_is_idempotent(self):
        self.sync()  # initial normalization may create derived root indexes
        before = self.git(self.root, "rev-parse", "HEAD")
        self.sync()
        self.sync()
        self.assert_published()
        self.assertEqual(self.git(self.root, "rev-parse", "HEAD"), before)

    def test_remote_divergence_rebases_without_losing_either_side(self):
        peer = self.peer()
        self.write("remote.txt", "remote task\n", peer)
        self.git(peer, "add", ".")
        self.git(peer, "commit", "-m", "remote addition")
        self.git(peer, "push", "origin", "main")
        remote_head = self.git(peer, "rev-parse", "HEAD")
        self.write("local.txt", "local task\n")
        self.sync()
        self.assert_published()
        self.assertEqual((self.root / "remote.txt").read_text(), "remote task\n")
        self.assertEqual((self.root / "local.txt").read_text(), "local task\n")
        self.assertEqual(self.git(self.root, "merge-base", "HEAD", remote_head), remote_head)

    def test_conflict_leaves_main_content_and_remote_intact(self):
        peer = self.peer()
        self.write("note.txt", "remote incompatible edit\n", peer)
        self.git(peer, "add", "note.txt")
        self.git(peer, "commit", "-m", "remote edit")
        self.git(peer, "push", "origin", "main")
        remote_head = self.git(self.remote, "rev-parse", "main")
        self.write("note.txt", "local incompatible edit\n")
        self.write("new.txt", "also preserve untracked content\n")
        ignored = self.write("ignored/cache", "retain ignored\n")
        with self.assertRaises(ValueError):
            self.sync()
        self.assertEqual((self.root / "note.txt").read_text(), "local incompatible edit\n")
        self.assertEqual((self.root / "new.txt").read_text(), "also preserve untracked content\n")
        self.assertEqual(ignored.read_text(), "retain ignored\n")
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), remote_head)
        self.assertEqual(self.git(self.root, "branch", "--show-current"), "main")
        self.assertEqual(self.git(self.root, "ls-files", "--unmerged"), "")
        self.assertFalse((self.root / ".git/rebase-merge").exists())
        self.assertFalse((self.root / ".git/rebase-apply").exists())

    def test_rejected_push_retains_data_and_next_sync_recovers(self):
        hook = self.remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nprintf 'rejected\\n' >> \"$GIT_DIR/rejected-attempts\"\nexit 1\n")
        hook.chmod(0o755)
        remote_head = self.git(self.remote, "rev-parse", "main")
        self.write("note.txt", "unsent checkpoint\n")
        self.write("new.txt", "unsent new task\n")
        with self.assertRaises(ValueError):
            self.sync()
        self.assertTrue((self.remote / "rejected-attempts").is_file())
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), remote_head)
        self.assertEqual((self.root / "note.txt").read_text(), "unsent checkpoint\n")
        self.assertEqual((self.root / "new.txt").read_text(), "unsent new task\n")
        hook.unlink()
        self.sync()
        self.assert_published()
        self.assertEqual(self.git(self.remote, "show", "main:note.txt"), "unsent checkpoint")
        self.assertEqual(self.git(self.remote, "show", "main:new.txt"), "unsent new task")

    def test_transient_push_rejection_is_retried_in_one_sync(self):
        hook = self.remote / "hooks/pre-receive"
        hook.write_text(
            "#!/bin/sh\n"
            "if test ! -f \"$GIT_DIR/first-rejection\"; then\n"
            "  touch \"$GIT_DIR/first-rejection\"\n"
            "  exit 1\n"
            "fi\n"
            "exit 0\n"
        )
        hook.chmod(0o755)
        self.write("retry.txt", "content survives the retry\n")
        self.sync(retries=2)
        self.assertTrue((self.remote / "first-rejection").is_file())
        self.assert_published()
        self.assertEqual(self.git(self.remote, "show", "main:retry.txt"),
                         "content survives the retry")

    def test_missing_authorizations_do_not_checkpoint(self):
        self.write("note.txt", "pending changes\n")
        before = self.snapshot()
        for flag in ("authorize_push", "cooperative_writers"):
            with self.subTest(flag=flag):
                with self.assertRaises(ValueError):
                    self.sync(**{flag: False})
                self.assertEqual(self.snapshot(), before)

    def test_mismatched_fetch_url_is_rejected_without_changes(self):
        self.write("note.txt", "pending changes\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync(remote_url=str(self.base / "unapproved.git"))
        self.assertEqual(self.snapshot(), before)

    def test_mismatched_push_url_is_rejected_without_changes(self):
        self.git(self.root, "remote", "set-url", "--push", "origin", str(self.base / "unapproved.git"))
        self.write("note.txt", "pending changes\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync()
        self.assertEqual(self.snapshot(), before)

    def test_subdirectory_is_not_accepted_as_repository_root(self):
        subdirectory = self.root / "subdirectory"
        subdirectory.mkdir()
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync(root=subdirectory)
        self.assertEqual(self.snapshot(), before)

    def test_non_main_checkout_is_rejected(self):
        self.git(self.root, "switch", "-c", "topic")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync()
        self.assertEqual(self.snapshot(), before)

    def test_non_main_target_is_rejected(self):
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync(branch="topic")
        self.assertEqual(self.snapshot(), before)

    def test_unsafe_credentials_are_not_staged(self):
        for name in (".env", "credentials.json", "id_rsa", "private.pem", "nested/.env"):
            with self.subTest(name=name):
                path = self.write(name, "sensitive fixture content\n")
                before = self.snapshot()
                with self.assertRaises(ValueError):
                    self.sync()
                self.assertEqual(self.snapshot(), before)
                path.unlink()

    def test_numbered_git_backup_directory_is_rejected(self):
        self.write(".git.1/config", "backup metadata\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync()
        self.assertEqual(self.snapshot(), before)

    def test_nested_git_repository_is_rejected(self):
        nested = self.root / "nested"
        self.git(self.root, "init", "--initial-branch=main", str(nested))
        self.write("payload", "nested repository content\n", nested)
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync()
        self.assertEqual(self.snapshot(), before)
        self.assertTrue((nested / ".git").is_dir())

    def test_new_oversized_blob_is_rejected_without_staging(self):
        self.write("large.bin", "x" * 129)
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync(max_blob_bytes=128)
        self.assertEqual(self.snapshot(), before)

    def test_oversized_partially_staged_blob_cannot_hide_behind_small_worktree(self):
        self.write("note.txt", "x" * 129)
        self.git(self.root, "add", "note.txt")
        self.write("note.txt", "small final content\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync(max_blob_bytes=128)
        self.assertEqual(self.snapshot(), before)

    def _assert_symlink_index_safe(self, name, incoming=False):
        external = self.base / 'external-document'
        external.write_bytes(b'EXTERNAL ORIGINAL BYTES\n')
        target_root = self.peer() if incoming else self.root
        (target_root / name).symlink_to(external)
        if incoming:
            self.git(target_root, 'add', name)
            self.git(target_root, 'commit', '-m', 'incoming index symlink')
            self.git(target_root, 'push', 'origin', 'main')
        before = self.git(self.root, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.sync()
        self.assertEqual(external.read_bytes(), b'EXTERNAL ORIGINAL BYTES\n')
        self.assertEqual(self.git(self.root, 'rev-parse', 'HEAD'), before)

    def test_local_readme_symlink_cannot_overwrite_external_file(self):
        self._assert_symlink_index_safe('README.md')

    def test_local_tasks_symlink_cannot_overwrite_external_file(self):
        self._assert_symlink_index_safe('TASKS.md')

    def test_incoming_readme_symlink_cannot_overwrite_external_file(self):
        self._assert_symlink_index_safe('README.md', incoming=True)

    def test_incoming_tasks_symlink_cannot_overwrite_external_file(self):
        self._assert_symlink_index_safe('TASKS.md', incoming=True)

    def test_generator_itself_refuses_symlink_output(self):
        external = self.base / 'external-document'
        external.write_text('external original\n')
        (self.root / 'README.md').symlink_to(external)
        generator = SCRIPT.parents[2] / 'task-framework/scripts/update-index.py'
        result = subprocess.run([sys.executable, str(generator), '--tasks-dir', str(self.root)],
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(external.read_text(), 'external original\n')

    def test_failed_promotion_restores_owned_index_and_blocks_repeat(self):
        self.write('note.txt', 'staged\n')
        self.git(self.root, 'add', 'note.txt')
        self.write('note.txt', 'working\n')
        before = self.snapshot()
        original = self.module.run
        def failing(root, *args, **kwargs):
            if Path(root) == self.root and args[:3] == ('read-tree', '-m', '-u'):
                raise ValueError('injected promotion failure')
            return original(root, *args, **kwargs)
        with patch.object(self.module, 'run', side_effect=failing):
            with self.assertRaisesRegex(ValueError, 'injected promotion failure'):
                self.sync()
        self.assertEqual(self.snapshot(), before)
        with self.assertRaisesRegex(ValueError, 'unresolved transaction'):
            self.sync()

    def test_cli_config_executes_and_requires_explicit_execute(self):
        import json
        config = self.base / 'sync.json'
        config.write_text(json.dumps(dict(tasks_root=str(self.root), remote='origin',
                                         remote_url=str(self.remote), branch='main', node_id='fixture',
                                         auto_push=True, cooperative_writers=True)))
        script = SCRIPT.with_name('task_git_sync.py')
        result = subprocess.run([sys.executable, str(script), 'sync', '--config', str(config)],
                                capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--execute', result.stderr)
        result = subprocess.run([sys.executable, str(script), 'sync', '--config', str(config), '--execute'],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['phase'], 'complete')
        self.assert_published()

    def test_derived_conflict_regenerates_deterministically(self):
        self.sync()
        peer = self.peer()
        self.write('README.md', 'peer-derived\n', peer)
        self.git(peer, 'add', 'README.md')
        self.git(peer, 'commit', '-m', 'peer stale index')
        self.git(peer, 'push', 'origin', 'main')
        self.write('README.md', 'local-derived\n')
        self.sync()
        before = self.git(self.root, 'rev-parse', 'HEAD')
        self.assertNotIn('local-derived', (self.root / 'README.md').read_text())
        self.assertNotIn('peer-derived', (self.root / 'README.md').read_text())
        self.sync()
        self.assertEqual(self.git(self.root, 'rev-parse', 'HEAD'), before)

    def test_unresolved_conflict_blocks_second_transaction(self):
        peer = self.peer()
        self.write('note.txt', 'peer\n', peer)
        self.git(peer, 'add', '.')
        self.git(peer, 'commit', '-m', 'peer change')
        self.git(peer, 'push', 'origin', 'main')
        self.write('note.txt', 'local\n')
        with self.assertRaises(ValueError):
            self.sync()
        journals = sorted((self.root / '.git/task-sync').glob('*/*.json'))
        worktrees = self.git(self.root, 'worktree', 'list', '--porcelain')
        with self.assertRaisesRegex(ValueError, 'unresolved transaction'):
            self.sync()
        self.assertEqual(sorted((self.root / '.git/task-sync').glob('*/*.json')), journals)
        self.assertEqual(self.git(self.root, 'worktree', 'list', '--porcelain'), worktrees)

    def test_commit_hooks_are_honored_before_push(self):
        before = self.snapshot()
        self.write('note.txt', 'changed\n')
        hook = self.root / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        remote_before = self.git(self.remote, 'rev-parse', 'main')
        with self.assertRaises(ValueError):
            self.sync()
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), remote_before)
        self.assertEqual((self.root / 'note.txt').read_text(), 'changed\n')
        self.assertEqual(self.git(self.root, 'rev-parse', 'HEAD'), before[0])

    def test_signing_failure_never_falls_back_unsigned(self):
        self.write('note.txt', 'signed change\n')
        self.git(self.root, 'config', 'commit.gpgsign', 'true')
        self.git(self.root, 'config', 'gpg.program', '/bin/false')
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), before[0])

    def test_canonical_writer_is_blocked_by_sync_lease(self):
        generator = SCRIPT.parents[2] / 'task-framework/scripts/update-index.py'
        with self.module.writer_lock(self.root):
            result = subprocess.run([sys.executable, str(generator), '--tasks-dir', str(self.root)],
                                    capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('writer lock busy', result.stderr)

    def test_ignored_incoming_obstruction_is_not_overwritten(self):
        peer = self.peer()
        self.write('ignored/local.txt', 'remote copy\n', peer)
        self.git(peer, 'add', '-f', 'ignored/local.txt')
        self.git(peer, 'commit', '-m', 'incoming ignored obstruction')
        self.git(peer, 'push', 'origin', 'main')
        self.write('ignored/local.txt', 'private local copy\n')
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync()
        self.assertEqual(self.snapshot(), before)

    def test_concurrent_external_edit_before_push_is_preserved(self):
        self.write('note.txt', 'snapshot\n')
        original = self.module.run
        injected = False
        def racing(root, *args, **kwargs):
            nonlocal injected
            value = original(root, *args, **kwargs)
            if args and args[0] == 'rebase' and not injected:
                injected = True
                self.write('note.txt', 'concurrent writer\n')
            return value
        before = self.git(self.remote, 'rev-parse', 'main')
        with patch.object(self.module, 'run', side_effect=racing):
            with self.assertRaisesRegex(ValueError, 'concurrent edit'):
                self.sync()
        self.assertEqual((self.root / 'note.txt').read_text(), 'concurrent writer\n')
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), before)

    def test_real_push_race_fetches_and_rebases_again(self):
        peer = self.peer()
        self.write('local.txt', 'local\n')
        original = self.module.run
        injected = False
        def racing(root, *args, **kwargs):
            nonlocal injected
            if args and args[0] == 'push' and not injected:
                injected = True
                self.write('racer.txt', 'racer\n', peer)
                self.git(peer, 'add', '.')
                self.git(peer, 'commit', '-m', 'racing peer')
                self.git(peer, 'push', 'origin', 'main')
            return original(root, *args, **kwargs)
        with patch.object(self.module, 'run', side_effect=racing):
            self.sync()
        self.assert_published()
        self.assertEqual((self.root / 'racer.txt').read_text(), 'racer\n')
        self.assertEqual((self.root / 'local.txt').read_text(), 'local\n')

    def test_timeout_kills_owned_hook_descendant(self):
        import time
        marker = self.base / 'must-not-appear'
        hook = self.root / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\n(sleep 1; touch "' + str(marker) + '") &\nwait\n')
        hook.chmod(0o755)
        self.write('note.txt', 'changed\n')
        self.git(self.root, 'add', 'note.txt')
        with self.assertRaises(subprocess.TimeoutExpired):
            self.module.run(self.root, 'commit', '-m', 'timeout', timeout=0.1)
        time.sleep(1.1)
        self.assertFalse(marker.exists())

    def test_checkpoint_commit_boundary_is_published(self):
        self.write('note.txt', 'staged\n')
        self.git(self.root, 'add', 'note.txt')
        self.write('note.txt', 'working\n')
        self.sync()
        history = self.git(self.remote, 'log', '--format=%s', 'main')
        self.assertIn('task checkpoint test-node: staged', history)
        self.assertIn('task checkpoint test-node: working', history)

    def test_interrupted_operation_is_refused(self):
        (self.root / '.git/MERGE_HEAD').write_text(self.git(self.root, 'rev-parse', 'HEAD'))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'interrupted/busy'):
            self.sync()
        self.assertEqual(self.snapshot(), before)

    def test_unchanged_historical_backup_is_not_rejected(self):
        self.write('.git.0/config', 'historical backup\n')
        self.git(self.root, 'add', '.git.0/config')
        self.git(self.root, 'commit', '-m', 'authorized historical backup')
        self.git(self.root, 'push', 'origin', 'main')
        self.sync()
        self.assert_published()
        self.assertEqual((self.root / '.git.0/config').read_text(), 'historical backup\n')

    def test_writer_lock_blocks_sync_without_mutating_files(self):
        self.write("note.txt", "writer in progress\n")
        before = self.snapshot()
        with self.module.writer_lock(self.root):
            with self.assertRaises(ValueError):
                self.sync()
        self.assertEqual(self.snapshot(), before)
        self.sync()
        self.assert_published()


if __name__ == "__main__":
    unittest.main()
