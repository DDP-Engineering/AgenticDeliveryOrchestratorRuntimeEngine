"""Bounded crash-released locks for shared host resource mutations."""

from collections.abc import Iterator
from contextlib import contextmanager
import errno
import math
import os
from pathlib import Path
import stat
import tempfile
from threading import local
from time import monotonic, sleep

_HELD = local()




class ResourceLockError(RuntimeError):
    """A shared resource is busy or its lock storage is unsafe."""


@contextmanager
def resource_lock(path: Path, *, timeout: float = 10) -> Iterator[None]:
    """
    Serialize one resource mutation with bounded kernel contention.
    path: Stable lock filename, independent of mutable output files.
    timeout: Maximum wait in seconds; zero attempts once.
    Raises ResourceLockError: Busy, aliased or unavailable lock storage.
    Note: The caller owns operation timeouts; this bound covers acquisition.
    """
    path = Path(path).absolute()
    try:
        valid_timeout = type(timeout) in (int, float) and math.isfinite(timeout) and timeout >= 0
    except OverflowError:
        valid_timeout = False
    if not valid_timeout:
        raise ResourceLockError("invalid shared resource lock timeout")
    held = getattr(_HELD, "paths", None)
    if held is None:
        held = _HELD.paths = set()
    key = os.path.normcase(str(path))
    if key in held:
        yield
        return
    handle = None
    acquired = False
    try:
        for part in (path, *path.parents):
            if part.exists() or part.is_symlink():
                info = part.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                    raise ResourceLockError("shared resource lock storage is linked")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        handle = os.fdopen(descriptor, "r+b")
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ResourceLockError("shared resource lock is not a private regular file")
        deadline = monotonic() + timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                held.add(key)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise ResourceLockError(
                        "shared resource is busy; retry after its owner finishes") from exc
                sleep(min(0.025, remaining))
    except OSError as exc:
        if handle is not None:
            handle.close()
        raise ResourceLockError("shared resource lock storage is unavailable") from exc
    except BaseException:
        if handle is not None:
            handle.close()
        raise
    try:
        yield
    finally:
        try:
            if acquired:
                held.remove(key)
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def atomic_write(path: Path, data: str) -> None:
    """
    Publish complete UTF-8 output using an exclusively owned sibling.
    path: Destination whose caller already owns the mutation scope.
    data: Complete text to publish.
    Raises OSError: Failed write or replacement; existing output is retained.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
