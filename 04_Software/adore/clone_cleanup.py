#!/usr/bin/env python3
# -*- coding: utf-8 -*-  # noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file clone_cleanup.py
@brief Decide whether a deleted project's local clone may be removed.
@details Enrollment clones repositories into <ADORE home>/repos. When an
         administrator asks for it, project deletion removes that clone too,
         but only when it is plainly ADORE's own: under <ADORE home>/repos and
         not reached through a symlink, a git clone of the project's
         repository, not another project's clone, with no linked worktree and
         no uncommitted changes. Every other case keeps the clone and names
         the reason, so the web dialog and the CLI can say why.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Iterable
from dataclasses import dataclass
import os
from pathlib import Path

from adore.config import Config, load_config
from adore.profiles import ProfileStore
from adore.util import CommandRunner, run_command
from adore.web.repository_source import RepositorySourceError, parse_repository_url, read_origin

# CONSTANTS
STATUS_TIMEOUT = 30
REASONS = (
    "outside-repos",
    "missing",
    "not-a-clone",
    "origin-mismatch",
    "shared",
    "worktrees",
    "uncommitted",
    "unknown",
)


@dataclass(frozen=True)
class CloneDecision:
    """@brief Whether a project's clone may be removed, and why not when it may not."""

    path: str
    removable: bool
    reason: str = ""

    def view(self) -> dict:
        """@brief JSON form for the API and the CLI report."""
        return {"path": self.path, "removable": self.removable, "reason": self.reason}


def _keep(path: Path | str, reason: str) -> CloneDecision:
    return CloneDecision(str(path), False, reason)


def _same_repository(clone: Path, repo: str) -> bool:
    """@brief True when the clone's origin names the project's owner/repository."""
    origin = read_origin(clone)
    if not origin:
        return False
    try:
        parsed = parse_repository_url(origin)
    except RepositorySourceError:
        return False
    return parsed.repo.casefold() == repo.strip().strip("/").casefold()


def _redirects(part: Path) -> bool:
    """@brief True when this path component is a symlink or a Windows junction."""
    if part.is_symlink():
        return True
    real = os.path.normcase(os.path.realpath(part))
    return real != os.path.normcase(os.path.join(os.path.realpath(part.parent), part.name))


def _linked_folders(clone: Path) -> list[Path]:
    """@brief Folders of the worktrees linked to the clone that still exist."""
    folders = []
    linked = clone / ".git" / "worktrees"
    for entry in linked.iterdir() if linked.is_dir() else ():
        try:
            # git may record the path relative to the record folder.
            folder = (entry / (entry / "gitdir").read_text(encoding="utf-8").strip()).parent
        except (OSError, UnicodeError):
            folders.append(entry)  # unreadable record: treat as a live worktree
            continue
        if folder.is_dir():
            folders.append(folder.resolve())
    return folders


def _inside(value: str, clone: Path) -> bool:
    """@brief True when another project's path is the clone, lies in it, or is not absolute."""
    if not value:
        return False
    path = Path(value)
    return not path.is_absolute() or path.resolve().is_relative_to(clone)


def _used_elsewhere(store: ProfileStore, name: str, clone: Path) -> bool:
    """@brief True when another project uses the clone, or that cannot be ruled out."""
    if [other for other in store.invalid_profiles() if other != name]:
        return True
    for profile in store.list_profiles():
        if profile.name == name:
            continue
        try:
            other = load_config(
                Path(profile.config_path)
                if profile.config_path
                else store.config_path(profile.name)
            )
            # Its clone, worktrees or state inside this clone; a relative clone path
            # may resolve here too.
            if _inside(other.worktree.repo_path, clone) or any(
                value and Path(value).is_absolute() and _inside(value, clone)
                for value in (other.worktree.root, other.state.store_root)
            ):
                return True
        except (OSError, ValueError, TypeError, AttributeError):
            return True
    return False


def clone_decision(
    store: ProfileStore,
    name: str,
    repo_path: str,
    repo: str,
    runner: CommandRunner = run_command,
    *,
    linked_worktrees_ok: bool = False,
) -> CloneDecision:
    """
    @brief      Decide whether the clone at repo_path may be removed with project name.
    @param[in]  store Profile store; its home defines <ADORE home>/repos.
    @param[in]  name Project being deleted (its own profile is not "another project").
    @param[in]  repo_path The project's configured clone path.
    @param[in]  repo The project's owner/repository identifier.
    @param[in]  runner Command boundary for `git status`.
    @param[in]  linked_worktrees_ok Ignore linked worktrees (before the resource sweep,
                which removes ADORE's own; the caller checks the kept ones).
    @return     A removable decision, or the first reason to keep the clone.
    """
    try:
        return _decide(store, name, repo_path, repo, runner, linked_worktrees_ok)
    except (OSError, ValueError, TypeError, AttributeError):
        # A malformed configuration or an unreadable path never removes anything.
        return _keep(repo_path if isinstance(repo_path, str) else "", "unknown")


def _decide(
    store: ProfileStore,
    name: str,
    repo_path: str,
    repo: str,
    runner: CommandRunner,
    linked_worktrees_ok: bool,
) -> CloneDecision:
    """@brief clone_decision without the guard for malformed input."""
    raw = Path(repo_path) if repo_path else None
    if raw is None or not raw.is_absolute():
        return _keep(repo_path, "outside-repos")
    repos = (store.home / "repos").resolve()
    clone = raw.resolve()
    if clone == repos or not clone.is_relative_to(repos):
        return _keep(clone, "outside-repos")
    # No folder between repos and the clone, nor the clone itself, may be a link.
    for part in (raw, *raw.parents):
        if part.resolve() == repos:
            break
        if _redirects(part):
            return _keep(clone, "outside-repos")
    if not clone.is_dir():
        return _keep(clone, "missing")
    if not (clone / ".git").is_dir():
        return _keep(clone, "not-a-clone")
    if not _same_repository(clone, repo):
        return _keep(clone, "origin-mismatch")
    if _used_elsewhere(store, name, clone):
        return _keep(clone, "shared")
    linked = clone / ".git" / "worktrees"
    if not linked_worktrees_ok and linked.is_dir() and any(linked.iterdir()):
        return _keep(clone, "worktrees")
    status = runner(
        ["git", "-C", str(clone), "status", "--porcelain", "--untracked-files=normal"],
        timeout=STATUS_TIMEOUT,
    )
    if not status.ok:
        return _keep(clone, "not-a-clone")
    if status.stdout.strip():
        return _keep(clone, "uncommitted")
    return CloneDecision(str(clone), True)


def project_clone_decision(
    store: ProfileStore,
    name: str,
    config: Config,
    runs: Iterable,
    runner: CommandRunner = run_command,
) -> CloneDecision:
    """
    @brief      clone_decision plus the worktrees that deletion will keep.
    @details    Before resources are purged: ADORE's own worktrees are about to be
                removed, but the sweep keeps those of handed-off runs and of runs
                made by the local backend while the project now uses containers.
    @param[in]  runs The project's run states.
    """
    from adore.isolation import WorktreeManager

    decision = clone_decision(
        store,
        name,
        config.worktree.repo_path,
        config.platform.repo,
        runner,
        linked_worktrees_ok=True,
    )
    if not decision.removable:
        return decision
    worktrees = WorktreeManager(config.worktree.repo_path, config.worktree.root, runner)
    swept = set()
    for run in runs:
        kept = run.lifecycle in {"handed-off", "handoff-pending"} or (
            config.execution.backend != "local"
            and run.execution.get("plan", {}).get("backend") == "local"
        )
        if kept and worktrees.path_for(run.run_id).is_dir():
            return _keep(decision.path, "worktrees")
        swept.add(worktrees.path_for(run.run_id).resolve())
    # A linked worktree that is not one of this project's runs survives the sweep.
    if any(folder not in swept for folder in _linked_folders(Path(decision.path))):
        return _keep(decision.path, "worktrees")
    return decision


# END OF FILE
