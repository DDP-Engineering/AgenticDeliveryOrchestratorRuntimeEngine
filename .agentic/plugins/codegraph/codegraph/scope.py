#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file scope.py
@brief Which repository files CodeGraph indexes.
@details Candidate files come from Git (tracked plus non-ignored untracked
         files) in a Git work tree, otherwise from a walk of the configured
         folders. Selection reuses the AEGIS layout matching rules exactly, so
         a pattern means the same thing to `check` and to CodeGraph. Project
         manifests above the selected sources are discovered separately: they
         shape module names and freshness but never contribute symbols.
"""

# IMPORTS

from __future__ import annotations

import fnmatch
import hashlib
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from codegraph import programs
from codegraph.config import Settings

# CONSTANTS

GIT = "git"
#: path components that are never source input
EXCLUDED_PARTS = frozenset({".git", "node_modules", "__pycache__", ".venv", "venv",
                            ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
                            "dist", "build", ".eggs"})
PYTHON_SUFFIXES = (".py", ".pyi")
MANIFEST_NAMES = ("pyproject.toml", "setup.cfg")
BINARY_PROBE_BYTES = 8192

# DATA MODELS / TYPEDEFINITIONS


class ScopeError(Exception):
    """A scope problem with a machine reason (`scope_missing`, `inventory_failed`)."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass
class Inventory:
    """Candidate files and how they were found."""

    mode: str
    paths: list[str]


@dataclass
class SelectedFile:
    """One file chosen for indexing."""

    path: str
    role: str
    language: str
    size: int


@dataclass
class Selection:
    """The indexing scope: selected files, skips, and discovered manifests."""

    inventory: str
    files: list[SelectedFile] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)
    manifests: list[str] = field(default_factory=list)

# HELPER FUNCTIONS


def match_path(path: str, pattern: str) -> bool:
    """
    @brief One layout entry against one repository-relative path.
    @details The AEGIS CLI rule: a trailing `/` or a bare name matches the
             folder and everything below it; glob characters use the
             case-sensitive `fnmatchcase`; anything else is an exact path.
    """
    if pattern.endswith("/"):
        return path.startswith(pattern) or path == pattern.rstrip("/")
    if any(char in pattern for char in "*?["):
        return fnmatch.fnmatchcase(path, pattern)
    return path == pattern or path.startswith(pattern + "/")


def match_any(path: str, patterns: list[str]) -> bool:
    """@brief True when any pattern matches the path."""
    return any(match_path(path, pattern) for pattern in patterns)


def _excluded(path: str, settings: Settings) -> bool:
    """@brief Built-in, configured and installed-payload exclusions."""
    parts = path.split("/")
    if parts[0] == ".agentic":
        return True
    if any(part in EXCLUDED_PARTS or part.endswith(".egg-info") for part in parts):
        return True
    return match_any(path, settings.exclude)


def _patterns(settings: Settings) -> list[str]:
    """@brief Every pattern that can select a file."""
    tests = settings.tests if settings.index_tests else []
    return [*settings.source, *tests, *settings.include]


def _git(settings: Settings, *args: str) -> subprocess.CompletedProcess | None:
    """
    @brief Run Git in the root; None when no Git outside the root exists.
    @details Git is located by `programs.find`, never inside the repository.
             It gets its own empty standard input: on Windows, starting a child
             that inherits a pipe another thread is reading blocks until that
             read ends, which would stall indexing under `--watch-stdin`.
    """
    git = programs.find(GIT, settings.root)
    if git is None:
        return None
    try:
        return subprocess.run([git, "-C", str(settings.root), *args],
                              stdin=subprocess.DEVNULL, capture_output=True, check=False,
                              timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None


def _git_paths(done: subprocess.CompletedProcess) -> list[str]:
    """@brief NUL-separated Git output as paths."""
    return [name for name in done.stdout.decode("utf-8", "replace").split("\0") if name]


def _walk_roots(settings: Settings) -> list[Path]:
    """@brief The literal leading folders of the selection patterns."""
    roots: list[Path] = []
    for pattern in _patterns(settings):
        literal: list[str] = []
        for part in pattern.rstrip("/").split("/"):
            if any(char in part for char in "*?["):
                break
            literal.append(part)
        roots.append(settings.root.joinpath(*literal) if literal else settings.root)
    return roots


def _walk(settings: Settings) -> list[str]:
    """@brief Repository-relative files below the scoped folders, pruned."""
    found: set[str] = set()
    pending = [path for path in _walk_roots(settings) if path.exists()]
    while pending:
        current = pending.pop()
        if current.is_file():
            found.add(current.relative_to(settings.root).as_posix())
            continue
        with os.scandir(current) as entries:
            for entry in entries:
                if entry.name in EXCLUDED_PARTS or entry.name.endswith(".egg-info"):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    found.add(Path(entry.path).relative_to(settings.root).as_posix())
    return sorted(found)


def _is_binary(path: Path) -> bool:
    """@brief A NUL byte in the first block marks a binary file."""
    with path.open("rb") as handle:
        return b"\0" in handle.read(BINARY_PROBE_BYTES)


def _manifests(settings: Settings, inventory: Inventory, files: list[SelectedFile]) -> list[str]:
    """@brief Recognized manifests in the selected folders and their ancestors."""
    visible = set(inventory.paths) if inventory.mode == "git" else None
    folders: set[str] = set()
    for item in files:
        parts = item.path.split("/")[:-1]
        for depth in range(len(parts) + 1):
            folders.add("/".join(parts[:depth]))
    found: list[str] = []
    for folder in sorted(folders):
        for name in MANIFEST_NAMES:
            relative = f"{folder}/{name}" if folder else name
            present = (relative in visible if visible is not None
                       else (settings.root / relative).is_file())
            if present and not _excluded(relative, settings):
                found.append(relative)
    return found

# PUBLIC API


def inventory(settings: Settings) -> Inventory:
    """
    @brief List candidate files from Git or, outside Git, the filesystem.
    @exception ScopeError `inventory_failed` when a Git work tree cannot be listed.
    """
    probe = _git(settings, "rev-parse", "--is-inside-work-tree")
    if probe is None or probe.returncode != 0 or probe.stdout.strip() != b"true":
        return Inventory("filesystem", _walk(settings))
    paths: set[str] = set()
    listings = [("ls-files", "--cached", "-z")]
    if settings.include_untracked:
        listings.append(("ls-files", "--others", "--exclude-standard", "-z"))
    for args in listings:
        done = _git(settings, *args)
        if done is None or done.returncode != 0:
            raise ScopeError("inventory_failed",
                             "git could not list the repository files; nothing was indexed")
        paths.update(_git_paths(done))
    present = sorted(path for path in paths if (settings.root / path).is_file())
    return Inventory("git", present)


def require_scope(settings: Settings) -> None:
    """
    @brief Refuse a configuration that cannot select anything, from settings alone.
    @exception ScopeError `scope_missing`.
    """
    if not (settings.source or (settings.index_tests and settings.tests) or settings.include):
        raise ScopeError("scope_missing",
                         "no source scope: configure [layout] source/tests or "
                         "[codegraph] include in .agentic/aegis.toml")


def select(settings: Settings, found: Inventory | None = None) -> Selection:
    """
    @brief Choose the files to index, with skip reasons and manifests.
    @exception ScopeError `scope_missing` when no pattern can select anything.
    """
    require_scope(settings)
    found = found or inventory(settings)
    selection = Selection(inventory=found.mode)
    patterns = _patterns(settings)
    for path in found.paths:
        if not match_any(path, patterns) or _excluded(path, settings):
            continue
        is_test = match_any(path, settings.tests)
        if is_test and not settings.index_tests:
            continue
        if path.rsplit("/", 1)[-1] in MANIFEST_NAMES:
            continue
        if not path.endswith(PYTHON_SUFFIXES):
            selection.skipped[path] = "unsupported"
            continue
        absolute = settings.root / path
        size = absolute.stat().st_size
        if size > settings.max_file_bytes:
            selection.skipped[path] = "too-large"
        elif _is_binary(absolute):
            selection.skipped[path] = "binary"
        else:
            selection.files.append(SelectedFile(path, "test" if is_test else "source",
                                                "python", size))
    selection.manifests = _manifests(settings, found, selection.files)
    return selection


def manifest_hashes(settings: Settings, manifests: list[str]) -> dict[str, str]:
    """@brief SHA-256 of each manifest's content, keyed by path."""
    return {path: hashlib.sha256((settings.root / path).read_bytes()).hexdigest()
            for path in manifests}


def report(settings: Settings) -> dict:
    """@brief The scope preview: patterns, totals, counts, skips and manifests."""
    selection = select(settings)
    by_role: dict[str, int] = {}
    by_language: dict[str, int] = {}
    skipped: dict[str, int] = {}
    for item in selection.files:
        by_role[item.role] = by_role.get(item.role, 0) + 1
        by_language[item.language] = by_language.get(item.language, 0) + 1
    for reason in selection.skipped.values():
        skipped[reason] = skipped.get(reason, 0) + 1
    return {
        "patterns": {"source": settings.source, "tests": settings.tests,
                     "include": settings.include, "exclude": settings.exclude},
        "inventory": selection.inventory,
        "totals": {"files": len(selection.files),
                   "bytes": sum(item.size for item in selection.files)},
        "by_role": by_role,
        "by_language": by_language,
        "skipped": skipped,
        "manifests": selection.manifests,
    }

# END OF FILE
