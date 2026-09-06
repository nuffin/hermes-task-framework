"""Cooperative task-root writer lease for canonical task-framework writers.

Not a sandbox: arbitrary editors and third-party writers do not participate.
"""
import contextlib
try:
    import fcntl
except ImportError:  # Preserve existing non-POSIX canonical command support.
    fcntl = None
import functools
import os
from pathlib import Path
import subprocess

import threading

class _ThreadHeld(threading.local):
    def __init__(self):
        self.values = {}

_THREAD_STATE = _ThreadHeld()


def _held():
    return _THREAD_STATE.values


def lock_path(root):
    root = Path(root).resolve()
    if not (root / '.git').exists():
        return None
    output = subprocess.run(['git', '-C', str(root), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                            capture_output=True, text=True, check=True, timeout=10)
    directory = Path(output.stdout.strip()) / 'task-sync'
    directory.mkdir(mode=0o700, exist_ok=True)
    return directory / 'writer.lock'


@contextlib.contextmanager
def task_writer_lock(root, reentrant=True):
    if fcntl is None:
        yield None
        return
    path = lock_path(root)
    if path is None:
        yield None
        return
    if path in _held():
        if not reentrant:
            raise ValueError('task writer lock busy')
        yield _held()[path]
        return
    inherited = os.environ.get('HERMES_TASK_WRITER_LOCK_FD', '')
    if inherited.isdigit():
        descriptor = int(inherited)
        valid = False
        try:
            stat = os.fstat(descriptor)
            actual = path.stat()
            valid = (stat.st_dev, stat.st_ino) == (actual.st_dev, actual.st_ino)
            if valid:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            valid = False
        if valid:
            _held()[path] = descriptor
            try:
                yield descriptor
            finally:
                _held().pop(path)
            return
    with path.open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('task writer lock busy') from exc
        _held()[path] = stream.fileno()
        try:
            yield stream.fileno()
        finally:
            _held().pop(path)
            fcntl.flock(stream, fcntl.LOCK_UN)


def child_lease(root):
    path = lock_path(root)
    descriptor = _held().get(path)
    if descriptor is None:
        return {}
    return {'env': {**os.environ, 'HERMES_TASK_WRITER_LOCK_FD': str(descriptor)},
            'pass_fds': (descriptor,)}


def guarded(root_getter):
    def decorate(function):
        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            with task_writer_lock(root_getter()):
                return function(*args, **kwargs)
        return wrapped
    return decorate
