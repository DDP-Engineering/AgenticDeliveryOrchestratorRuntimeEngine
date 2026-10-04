#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file safety.py
@brief Preconditions and guards for every CodeGraph write.
@details Indexing checks, in order: the Git state of the storage folder
         (before any filesystem change), an operating-system writer lock on
         the stable `codegraph.lock` file, and ownership of an existing
         database. The lock is released by the operating system when its
         holder exits, so it can never go stale, and the lock file is never
         deleted or recreated. The plugin-content identity lets a run detect
         that its own code changed underneath it before publishing.
"""

# IMPORTS

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Self

from codegraph import natives, programs, store
from codegraph.config import LOCK_NAME, Settings

# CONSTANTS

GIT = "git"
TEMP_PROBE = ".codegraph-rebuild-0000000000000000.tmp"
REPLACE_ATTEMPTS = 20
REPLACE_DELAY_SECONDS = 0.1
#: generated folders that are not plugin content
IDENTITY_SKIPPED = frozenset({"__pycache__", ".pytest_cache", ".ruff_cache"})

# DATA MODELS / TYPEDEFINITIONS


class Refused(Exception):
    """A write that was not attempted, with its protocol reason and index state."""

    def __init__(self, reason: str, message: str, index: str | None = None) -> None:
        super().__init__(message)
        self.reason = reason
        self.index = index


class WriterLock:
    """Exclusive, non-blocking operating-system lock on `codegraph.lock`."""

    def __init__(self, storage: Path) -> None:
        self.path = storage / LOCK_NAME
        self.fd = -1

    def __enter__(self) -> Self:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            if sys.platform == "win32":
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            raise Refused("busy", "another CodeGraph indexing run is active; "
                                  "try again when it finishes", index="busy") from None
        self.fd = fd
        return self

    def __exit__(self, *_exc) -> None:
        if self.fd < 0:
            return
        try:
            if sys.platform == "win32":
                import msvcrt
                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(self.fd)
            self.fd = -1

# HELPER FUNCTIONS


def _git(settings: Settings, *args: str) -> subprocess.CompletedProcess | None:
    """@brief Run Git in the root with empty input; None when no Git outside the root exists."""
    git = programs.find(GIT, settings.root)
    if git is None:
        return None
    try:
        return subprocess.run([git, "-C", str(settings.root), *args], capture_output=True,
                              stdin=subprocess.DEVNULL, check=False, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None

# PUBLIC API


def destination_state(settings: Settings) -> dict:
    """
    @brief What Git thinks of the storage folder, without writing anything.
    @return `repository`, `ignored` (None outside Git) and `tracked` paths.
    """
    probe = _git(settings, "rev-parse", "--is-inside-work-tree")
    if probe is None or probe.returncode != 0 or probe.stdout.strip() != b"true":
        return {"repository": False, "ignored": None, "tracked": []}
    storage = settings.storage.relative_to(settings.root).as_posix()
    names = (settings.database.name, LOCK_NAME, TEMP_PROBE)
    ignored = all(
        (done := _git(settings, "check-ignore", "-q", "--", f"{storage}/{name}")) is not None
        and done.returncode == 0 for name in names)
    listed = _git(settings, "ls-files", "-z", "--", f"{storage}/")
    tracked = ([] if listed is None else
               [name for name in listed.stdout.decode("utf-8", "replace").split("\0") if name])
    return {"repository": True, "ignored": ignored, "tracked": tracked}


def require_ignored_storage(settings: Settings) -> None:
    """
    @brief Refuse to write storage that Git would record.
    @exception Refused `destination_tracked` or `destination_not_ignored`.
    """
    state = destination_state(settings)
    if not state["repository"]:
        return
    storage = settings.storage.relative_to(settings.root).as_posix()
    if state["tracked"]:
        raise Refused("destination_tracked",
                      f"{storage}/ holds files Git tracks; untrack them with: "
                      f"git rm --cached -r -- {storage}/")
    if not state["ignored"]:
        raise Refused("destination_not_ignored",
                      f"Git does not ignore {storage}/; add it to .gitignore "
                      "and index again")


def require_ownership(path: Path) -> None:
    """
    @brief Refuse to open anything but a CodeGraph database read-write.
    @exception Refused `foreign_database`; the file is left untouched.
    """
    if store.header_kind(path) == "foreign":
        raise Refused("foreign_database",
                      f"{path.name} is not a CodeGraph database and was left untouched; "
                      "configure another [codegraph] database name or move the file",
                      index="incompatible")


def plugin_identity(root: Path = natives.PLUGIN_ROOT) -> str:
    """@brief SHA-256 over every plugin file's path and content."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (not path.is_file() or path.suffix == ".pyc"
                or IDENTITY_SKIPPED.intersection(relative.parts)):
            continue
        digest.update(relative.as_posix().encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def replace_file(temporary: Path, target: Path) -> None:
    """
    @brief Move a validated database into place, retrying sharing conflicts.
    @exception Refused `replace_failed` after the bounded retries.
    """
    for attempt in range(REPLACE_ATTEMPTS):
        try:
            os.replace(temporary, target)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS - 1:
                break
            time.sleep(REPLACE_DELAY_SECONDS)
    raise Refused("replace_failed", f"{target.name} is in use and could not be replaced; "
                                    "the previous database was kept")

# END OF FILE
