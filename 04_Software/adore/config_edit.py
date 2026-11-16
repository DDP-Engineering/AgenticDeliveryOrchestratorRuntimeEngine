"""Coordinate ADORE CLI and web configuration writes on one host."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from adore.state import StateStore


class ConfigEditLockedError(RuntimeError):
    """Another ADORE process owns the configuration edit lock."""


@contextmanager
def config_edit_lock(path: Path) -> Iterator[None]:
    """
    Hold an exclusive edit lock for one configuration directory.
    path: Config file being edited.
    Raises ConfigEditLockedError: When another local editor owns the lock.
    """
    guard = StateStore(path.parent, "adore-config")
    if not guard.acquire_lock():
        raise ConfigEditLockedError("another ADORE config edit holds the lock")
    try:
        yield
    finally:
        guard.release_lock()
