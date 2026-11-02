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
@file isolation.py
@brief Code and execution isolation for a run (design doc 10/10a).
@details Two layers per run, both keyed by the stable run-id: a git worktree
         (code isolation: one folder + branch per ticket, sharing the repo
         object store) mounted into a container (execution isolation). The
         worktree's `.git` pointer file holds an absolute HOST path, invalid
         inside the container, so the repo and worktree are mounted at fixed
         container paths and git is directed with GIT_DIR / GIT_COMMON_DIR /
         GIT_WORK_TREE environment variables instead of path discovery. The container
         runtime may be a wrapped command (for example
         "wsl -d Ubuntu-24.04 -- docker" for Docker Engine inside WSL2); in
         WSL mode mount sources are translated to /mnt/<drive>/ paths and
         env-value propagation crosses the WSL boundary via WSLENV.
         `WorktreeManager.remove` retries past the WSL2 bind-mount teardown
         race (moved here from orchestrator.py per ADORE-ARCH-009 - this is
         isolation-layer platform knowledge, not core-loop logic).
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable, Sequence
import hashlib
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shlex
import stat
import subprocess
import time

from adore.branding import (
    CONTAINER_HOME,
    CONTAINER_IO_MOUNT,
    CONTAINER_NPM_CACHE_MOUNT,
    CONTAINER_REPO_MOUNT,
    CONTAINER_UV_CACHE_MOUNT,
    CONTAINER_WORKTREE_MOUNT,
    EGRESS_NETWORK_PREFIX,
    EGRESS_PROXY_ALIAS,
)
from adore.config import SELINUX_RELABEL_OPTIONS, ContainerEgressConfig
from adore.util import (
    DEFAULT_COMMAND_TIMEOUT,
    CommandResult,
    CommandRunner,
    run_command,
    strict_json_loads,
)

# CONSTANTS

_ABSENT_MARKERS = ("no such container", "no such object", "not found")
# podman `volume create` errors when the volume already exists; docker is
# idempotent and stays silent (live finding 2026-07-05, podman pilot).
_EXISTS_MARKERS = ("already exists",)
_CONNECTED_MARKERS = ("already exists", "is already connected")
_DRIVE_RE = re.compile(r"^([A-Za-z]):[\\/]")
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
# The mode -> per-mount option map comes from config (SELINUX_RELABEL_OPTIONS)
# so there is one list, not two that can drift apart. Only HOST BIND MOUNTS
# take the option: the uv/npm cache mounts are NAMED VOLUMES, which the runtime
# already creates carrying a container-readable label, and relabeling those
# would be both pointless and slow.
_PROXY_SUFFIX = "-egress-proxy"
# Per-run egress names stay within these lengths (a 50-character proxy stem
# plus the suffix is a 63-character DNS label); a longer runtime-safe executor
# name keeps its start and ends in a short digest of the full name.
_PROXY_NAME_LIMIT = 50
_NETWORK_NAME_LIMIT = 48
_NAME_DIGEST_LENGTH = 10
PROXY_ALIAS = EGRESS_PROXY_ALIAS
_INLINE_ENV_KEYS = frozenset({
    "HOME",
    "GIT_DIR",
    "GIT_COMMON_DIR",
    "GIT_WORK_TREE",
    "GIT_AUTHOR_NAME",
    "GIT_AUTHOR_EMAIL",
    "GIT_COMMITTER_NAME",
    "GIT_COMMITTER_EMAIL",
    "PI_CODING_AGENT_DIR",
    "PI_OFFLINE",
    "PI_TELEMETRY",
    "PI_SKIP_VERSION_CHECK",
    "UV_CACHE_DIR",
    "UV_LINK_MODE",
    "UV_PROJECT_ENVIRONMENT",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
})

# Worktree removal right after container removal can transiently fail on WSL2:
# `docker/podman rm` returns before the kernel releases the container's
# 9P/drvfs bind mount on the worktree, so git's delete hits these errors until
# the mount clears (a few seconds). Retrying past them avoids leaving a husk
# for `adore cleanup` (live finding 2026-07-04/05; moved here from
# orchestrator.py per ADORE-ARCH-009 - this is isolation-layer, not
# core-loop, knowledge).
_TEARDOWN_RACE_MARKERS = (
    "function not implemented",   # ENOSYS - the observed WSL signature
    "device or resource busy",    # EBUSY  - mount still attached
    "resource busy",
    "directory not empty",        # ENOTEMPTY - files not yet released
)
_TEARDOWN_RETRY_DELAYS = (1.0, 2.0, 4.0)  # ~7s ceiling; the race clears in seconds

# Paths a TOOL regenerates rather than a person editing them. Excluded from the
# stage PROGRESS fingerprint only: rerunning a configured command rewrites them,
# and that must never read as a session having made candidate progress.
# Deliberately narrow - anything whose content a person could meaningfully
# author stays inside the fingerprint.
_GENERATED_PATHSPECS = (
    ":(exclude)**/__pycache__/**",
    ":(exclude)**/*.pyc",
    ":(exclude)**/*.pyo",
    ":(exclude)**/.pytest_cache/**",
    ":(exclude)**/.ruff_cache/**",
    ":(exclude)**/.mypy_cache/**",
)

# DATA MODELS / TYPEDEFINITIONS


class IsolationError(RuntimeError):
    """
    @brief   Raised when a git or container-runtime call fails unexpectedly.
    @details Carries the command and stderr so failures are diagnosable from
             the journal without re-running anything (same shape as
             ForgeError / StateError; fail closed, never guess).
    """

    def __init__(self, message: str, argv: list[str] | None = None, stderr: str = "") -> None:
        """
        @brief      Build the error with command context.
        @param[in]  message Human-readable summary.
        @param[in]  argv The command that failed.
        @param[in]  stderr Captured stderr from the tool.
        """
        detail = message
        if argv:
            detail += f" | argv: {' '.join(argv)}"
        if stderr.strip():
            detail += f" | stderr: {stderr.strip()}"
        super().__init__(detail)
        self.argv = argv or []
        self.stderr = stderr


def _is_teardown_race(exc: IsolationError) -> bool:
    """
    @brief      Whether a worktree-removal failure is the transient WSL
                bind-mount teardown race (worth retrying) vs a real error.
    @param[in]  exc The IsolationError raised by worktree removal.
    @return     True when the stderr matches a known mount-release signature.
    """
    text = (getattr(exc, "stderr", "") or str(exc)).lower()
    return any(marker in text for marker in _TEARDOWN_RACE_MARKERS)


# PUBLIC API


def wsl_mount_path(path: str | Path) -> str:
    """
    @brief      Translate a Windows host path to its WSL view for mounting.
    @details    A daemon running inside WSL2 cannot resolve "D:/x/y"; the same
                directory is visible there as "/mnt/d/x/y". Paths without a
                drive letter (already POSIX) pass through unchanged.
    @param[in]  path Host path.
    @return     The mount source usable by a WSL-side docker daemon.
    """
    # Path.as_posix() follows the current host's path flavour. On Linux a
    # Windows-looking string remains full of backslashes, so normalize the
    # external path syntax explicitly before matching its drive letter.
    posix = os.fspath(path).replace("\\", "/")
    match = _DRIVE_RE.match(posix)
    if not match:
        return posix
    drive = match.group(1).lower()
    return f"/mnt/{drive}/{posix[3:]}"


def build_container_env(git_dir_name: str, git_name: str, git_email: str) -> dict[str, str]:
    """
    @brief      Compose the git environment injected into a run's container.
    @details    GIT_DIR points at the worktree's admin dir under the mounted
                repo, GIT_COMMON_DIR at the mounted repository's common
                object/config store, and GIT_WORK_TREE at the mounted
                worktree. This bypasses the worktree's `.git` pointer file,
                whose absolute host path is meaningless inside the container,
                while keeping linked-worktree git discovery stable for CLIs
                that inspect the repository deeply. The identity variables
                give commits the configured bot authorship
                (Security_And_Credentials.md).
    @param[in]  git_dir_name The worktree admin dir name under
                             `.git/worktrees/` (WorktreeManager.admin_dir_name).
    @param[in]  git_name Commit author/committer name (agent.name).
    @param[in]  git_email Commit author/committer email (agent.email).
    @return     Environment mapping for ContainerManager.provision.
    """
    return {
        # Force the container user's home explicitly: some daemons (Docker
        # Engine in WSL2) inject the host user's HOME into every container,
        # overriding the image and breaking every HOME-based cache - tflint's
        # bundled plugin, uv, npm, agent auth (live finding 2026-07-04).
        "HOME": CONTAINER_HOME,
        "GIT_DIR": f"{CONTAINER_REPO_MOUNT}/.git/worktrees/{git_dir_name}",
        "GIT_COMMON_DIR": f"{CONTAINER_REPO_MOUNT}/.git",
        "GIT_WORK_TREE": CONTAINER_WORKTREE_MOUNT,
        "GIT_AUTHOR_NAME": git_name,
        "GIT_AUTHOR_EMAIL": git_email,
        "GIT_COMMITTER_NAME": git_name,
        "GIT_COMMITTER_EMAIL": git_email,
    }


class CheckpointConflictError(IsolationError):
    """@brief Remote ticket branch changed outside the conductor's ownership."""


class CheckpointProtocolError(IsolationError):
    """@brief Git checkpoint identity cannot be trusted; automatic work must stop."""


class WorktreeManager:
    """
    @brief   Per-run git worktrees on the host (code isolation).
    @details One worktree + one branch per run-id, created from the local
             clone at repo_path. Creation is idempotent so restart/resume
             reuses the same worktree instead of duplicating it (design 8a).
             `remove` retries past the WSL bind-mount teardown race
             (ADORE-ARCH-009: this platform-specific handling used to live in
             the orchestrator's core loop; it belongs here instead).
    """

    def __init__(
        self,
        repo_path: str | Path,
        root: str | Path,
        runner: CommandRunner = run_command,
        sleep: Callable[[float], None] = time.sleep,
        *,
        git_name: str = "",
        git_email: str = "",
    ) -> None:
        """
        @brief      Bind the manager to a local clone and a worktrees root.
        @details    Both paths are resolved to absolute immediately: git -C
                    resolves relative paths against the REPO, not our cwd, so
                    a relative root would scatter worktrees into the target
                    repository (pilot finding 2026-07-03).
        @param[in]  repo_path Local clone of the target repository.
        @param[in]  root Directory holding per-run worktrees (<root>/<run-id>).
        @param[in]  runner Command runner (injectable for tests).
        @param[in]  sleep Sleep function used by `remove`'s teardown-race
                          backoff (test override).
        @param[in]  git_name Name for host-side ADORE checkpoint commits.
        @param[in]  git_email Email for host-side ADORE checkpoint commits.
        """
        self.repo_path = Path(repo_path).resolve()
        self.root = Path(root).resolve()
        self.runner = runner
        self.sleep = sleep
        self.git_name = git_name
        self.git_email = git_email

    def path_for(self, run_id: str) -> Path:
        """
        @brief      The worktree directory for a run.
        @param[in]  run_id Stable run identifier.
        @return     `<root>/<run-id>`.
        """
        return self.root / run_id

    def exists(self, run_id: str) -> bool:
        """
        @brief      Whether the run's worktree is present on disk.
        @param[in]  run_id Stable run identifier.
        @return     True when the worktree dir with its `.git` pointer exists.
        """
        return (self.path_for(run_id) / ".git").exists()

    def create(self, run_id: str, branch: str, base_ref: str) -> Path:
        """
        @brief      Create (or reuse) the run's worktree on its branch.
        @details    Idempotent, in resume order: an existing worktree is
                    reused as-is; an existing branch (worktree lost) is
                    re-attached; otherwise branch + worktree are created from
                    base_ref. The worktrees root is created on demand.
        @param[in]  run_id Stable run identifier.
        @param[in]  branch Run branch name (for example "adore/<run-id>").
        @param[in]  base_ref Base ref for a new branch (for example
                             "origin/develop").
        @return     The worktree path.
        @exception  IsolationError When git fails.
        """
        path = self.path_for(run_id)
        if self.exists(run_id):
            return path
        self.root.mkdir(parents=True, exist_ok=True)
        if self._branch_exists(branch):
            self._git("worktree", "add", str(path), branch)
        else:
            self._git("worktree", "add", "-b", branch, str(path), base_ref)
        return path

    def remove(self, run_id: str, *, delete_branch: str | None = None) -> None:
        """
        @brief      Remove the run's worktree (and optionally its branch).
        @details    Idempotent: a missing worktree is not an error; stale
                    worktree registrations are pruned either way. The branch
                    is deleted only when explicitly named (terminal cleanup;
                    an in-review run keeps its branch).

                    Retries the whole operation past the WSL2 bind-mount
                    teardown race: `docker/podman rm` returns before the
                    kernel releases the container's 9P/drvfs mount on the
                    worktree, so an immediate removal can fail with
                    ENOSYS/EBUSY/ENOTEMPTY until it clears (live finding
                    2026-07-04/05). Retried ONLY on those transient
                    signatures, with backoff, up to `_TEARDOWN_RETRY_DELAYS`;
                    a real error is raised on the first attempt. Native
                    docker/Linux succeeds on the first try (no sleeps). The
                    caller decides what to do with an exhausted retry (ADORE
                    logs and leaves the husk for `adore cleanup`).
        @param[in]  run_id Stable run identifier.
        @param[in]  delete_branch Branch to force-delete, or None to keep it.
        @exception  IsolationError When git fails for another reason, or the
                    teardown race persists past every retry.
        """
        path = self.path_for(run_id)
        last: IsolationError | None = None
        for delay in (0.0, *_TEARDOWN_RETRY_DELAYS):
            if delay:
                self.sleep(delay)
            try:
                if (path / ".git").exists():
                    self._git("worktree", "remove", "--force", str(path))
                self._git("worktree", "prune")
                if delete_branch and self._branch_exists(delete_branch):
                    self._git("branch", "-D", delete_branch)
                return
            except IsolationError as exc:
                last = exc
                if not _is_teardown_race(exc):
                    raise  # a real failure - do not burn retries masking it
        raise last  # every retry exhausted; still the teardown race

    def admin_dir_name(self, run_id: str) -> str:
        """
        @brief      The worktree's admin dir name under `.git/worktrees/`.
        @details    Read from the worktree's `.git` pointer file rather than
                    assumed: git normally uses the directory basename but
                    appends a suffix on collision, so the file is the truth.
                    Feeds GIT_DIR for the container (build_container_env).
        @param[in]  run_id Stable run identifier.
        @return     The admin dir name (usually the run-id).
        @exception  IsolationError When the pointer file is missing/unreadable
                    or carries no gitdir line (fail closed, never guess).
        """
        pointer = self.path_for(run_id) / ".git"
        try:
            content = pointer.read_text(encoding="utf-8")
        except OSError as exc:
            raise IsolationError(
                f"worktree pointer unreadable for run {run_id!r}: {exc}"
            ) from exc
        prefix = "gitdir:"
        for line in content.splitlines():
            if line.startswith(prefix):
                gitdir = line[len(prefix):].strip()
                return Path(gitdir).name
        raise IsolationError(f"worktree pointer has no gitdir line for run {run_id!r}")

    def list_dirs(self) -> list[Path]:
        """
        @brief   Directories currently under the worktrees root.
        @details Includes husks (deregistered but not deleted, e.g. after the
                 WSL bind-mount race). `adore cleanup` reads it to find the
                 project's run IDs that have no state.
        @return  Child directories, sorted.
        """
        if not self.root.is_dir():
            return []
        return sorted(entry for entry in self.root.iterdir() if entry.is_dir())

    def fetch(self, remote: str = "origin") -> None:
        """
        @brief      Fetch the remote into the local clone.
        @param[in]  remote Remote name.
        @exception  IsolationError When git fails (offline, auth, ...).
        """
        self._git("fetch", remote)

    def merge(self, run_id: str, ref: str) -> CommandResult:
        """
        @brief      Merge a ref into the run branch (delivery integration).
        @details    Returns the result as DATA: a conflicted merge is a
                    conductor signal (relaunch the executor to resolve), not
                    an isolation failure. The merge is left in progress on
                    conflict so the executor can complete it (design 11a).
        @param[in]  run_id Stable run identifier.
        @param[in]  ref Ref to merge (for example "origin/develop").
        @return     The captured CommandResult.
        """
        self.scrub_container_worktree_config()
        return self.runner(
            ["git", "-C", str(self.path_for(run_id)), "merge", "--no-edit", ref]
        )

    def merge_in_progress(self, run_id: str) -> bool:
        """
        @brief      Whether an unconcluded merge sits in the worktree.
        @param[in]  run_id Stable run identifier.
        @return     True when MERGE_HEAD exists (conflicts not yet committed).
        """
        self.scrub_container_worktree_config()
        result = self.runner(
            ["git", "-C", str(self.path_for(run_id)),
             "rev-parse", "-q", "--verify", "MERGE_HEAD"]
        )
        return result.ok

    def push(self, run_id: str, branch: str) -> CommandResult:
        """
        @brief      Push the run branch to origin (orchestrator-owned).
        @details    Approved delivery uses this push; guarded WIP publication
                    uses push_checkpoint. The executor is blocked from pushing.
                    Returned as data so the
                    conductor decides (auth/protection failures escalate).
        @param[in]  run_id Stable run identifier.
        @param[in]  branch Branch name to push.
        @return     The captured CommandResult.
        """
        self.scrub_container_worktree_config()
        return self.runner(
            ["git", "-C", str(self.path_for(run_id)),
             "push", "--set-upstream", "origin", branch]
        )

    def push_checkpoint(self, run_id: str, branch: str, expected: str) -> str:
        """
        @brief Publish an owned, fast-forward checkpoint with an exact remote lease.
        @param[in] run_id Run whose clean checkpoint is being published.
        @param[in] branch Ticket branch, never the target branch.
        @param[in] expected Last verified remote commit, or empty for a new branch.
        @return Full commit verified on the remote after publication.
        @exception CheckpointConflictError When remote ownership or ancestry changed.
        @exception IsolationError When Git output or transport cannot be trusted.
        """
        ref = f"refs/heads/{branch}"
        if not branch or branch.startswith("-") or (expected and re.fullmatch(
            r"[0-9a-f]{40}|[0-9a-f]{64}", expected
        ) is None):
            raise CheckpointProtocolError("invalid checkpoint branch or expected commit")
        try:
            self._git("check-ref-format", ref)
        except IsolationError as exc:
            raise CheckpointProtocolError("invalid checkpoint branch format") from exc
        current = self._run_wt(str(self.path_for(run_id)), "symbolic-ref", "-q", "HEAD")
        if current.stdout.strip() != ref:
            raise CheckpointConflictError("local worktree is no longer on the ticket branch")
        head = self.ref_head(ref)
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", head) is None:
            raise CheckpointProtocolError("invalid local checkpoint commit")

        def remote_head() -> str:
            """@brief Parse one exact remote branch identity, rejecting foreign output."""
            output = self._git("ls-remote", "--heads", "origin", ref).stdout.strip()
            if not output:
                return ""
            match = re.fullmatch(r"([0-9a-f]{40}|[0-9a-f]{64})\t" + re.escape(ref), output)
            if match is None:
                raise CheckpointProtocolError("invalid remote checkpoint identity")
            return match[1]

        remote = remote_head()
        if remote == head:
            return head  # Recover an already successful push after a state-write crash.
        if remote != expected:
            raise CheckpointConflictError("remote ticket branch changed outside ADORE")
        if remote:
            ancestry = self.runner([
                "git", "-C", str(self.repo_path), "merge-base", "--is-ancestor", remote, head,
            ])
            if not ancestry.ok:
                raise CheckpointConflictError("checkpoint would replace remote history")
        self.scrub_container_worktree_config()
        result = self.runner([
            "git", "-C", str(self.path_for(run_id)), "push",
            f"--force-with-lease={ref}:{remote}", "origin", f"{head}:{ref}",
        ])
        observed = remote_head()
        if observed == head:
            return head
        if observed != remote:
            raise CheckpointConflictError("remote branch changed during checkpoint push")
        raise IsolationError("checkpoint push not verified", result.argv, result.stderr)

    def remove_remote_branch(self, branch: str, expected: str, target: str) -> None:
        """
        @brief Remove an unchanged human-merged run branch using an exact remote lease.
        @param[in] branch Owned run branch selected by the conductor.
        @param[in] expected Last published commit, which every publication records.
        @param[in] target Protected delivery target branch.
        @exception IsolationError When identity, transport or deletion cannot be verified.
        @note An already absent branch succeeds without requiring its local counterpart.
        """
        ref = f"refs/heads/{branch}"
        if (not branch or branch.startswith("-") or branch == target
                or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", expected or "") is None):
            raise IsolationError("invalid or protected branch cleanup identity")
        self._git("check-ref-format", ref)

        def remote_head() -> str:
            """@brief Reject remote output that does not identify exactly the requested ref."""
            output = self._git("ls-remote", "--heads", "origin", ref).stdout.strip()
            if not output:
                return ""
            match = re.fullmatch(r"([0-9a-f]{40}|[0-9a-f]{64})\t" + re.escape(ref), output)
            if match is None:
                raise IsolationError("invalid remote branch cleanup identity")
            return match[1]

        remote = remote_head()
        if not remote:
            return
        if remote != expected:
            raise IsolationError("remote run branch changed outside ADORE")
        self.scrub_container_worktree_config()
        result = self.runner([
            "git", "-C", str(self.repo_path), "push",
            f"--force-with-lease={ref}:{expected}", "origin", f":{ref}",
        ])
        if not remote_head():
            return
        raise IsolationError("remote branch deletion not verified", result.argv, result.stderr)

    def is_dirty(self, run_id: str) -> bool:
        """
        @brief      Whether the run's worktree has uncommitted changes.
        @details    Conductor check before fingerprinting: a validated run with a
                    dirty tree has work that would never reach the MR
                    (pilot finding 2026-07-03).
        @param[in]  run_id Stable run identifier.
        @return     True when `git status --porcelain` reports anything.
        @exception  IsolationError When git fails.
        """
        result = self._run_wt(str(self.path_for(run_id)), "status", "--porcelain")
        return bool(result.stdout.strip())

    def changed_files(self, run_id: str, base_ref: str) -> int:
        """
        @brief      How many files the run has touched vs its base ref.
        @details    Committed changes (base..HEAD) plus uncommitted ones,
                    counted on the HOST worktree; feeds the
                    max_files_touched run budget.
        @param[in]  run_id Stable run identifier.
        @param[in]  base_ref The ref the run branched from.
        @return     Count of distinct changed file paths.
        @exception  IsolationError When git fails.
        """
        wt = str(self.path_for(run_id))
        committed = self._run_wt(wt, "diff", "--name-only", f"{base_ref}...HEAD")
        pending = self._run_wt(wt, "status", "--porcelain")
        names = {line.strip() for line in committed.stdout.splitlines() if line.strip()}
        for line in pending.stdout.splitlines():
            entry = self._porcelain_path(line)
            if entry:
                names.add(entry)
        return len(names)

    def ref_head(self, ref: str) -> str:
        """
        @brief      Resolve a ref to its exact commit identifier.
        @param[in]  ref Local or remote ref to resolve.
        @return     Full commit SHA.
        @exception  IsolationError When the ref is missing or git fails.
        """
        return self._git("rev-parse", "--verify", f"{ref}^{{commit}}").stdout.strip()

    def candidate_fingerprint(self, run_id: str, base_ref: str) -> str:
        """
        @brief      Fingerprint the clean candidate and its exact commit series.
        @details    The target head, candidate head/tree and ordered commits are
                    bound together so either candidate mutation or target drift
                    invalidates a previously presented approval.
        @param[in]  run_id Stable run identifier.
        @param[in]  base_ref Target ref used as the integration base.
        @return     Lower-case SHA-256 hexadecimal fingerprint.
        @exception  IsolationError When the tree is dirty or git fails.
        """
        if self.is_dirty(run_id):
            raise IsolationError("cannot fingerprint a dirty candidate worktree")
        wt = str(self.path_for(run_id))
        tree = self._run_wt(wt, "rev-parse", "HEAD^{tree}").stdout.strip()
        head = self._run_wt(wt, "rev-parse", "HEAD^{commit}").stdout.strip()
        target = self.ref_head(base_ref)
        commits = self._run_wt(
            wt, "rev-list", "--reverse", f"{base_ref}..HEAD"
        ).stdout.strip()
        material = "\0".join((target, head, tree, commits)).encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def worktree_progress_fingerprint(self, run_id: str) -> str:
        """
        @brief      Observe candidate changes independently of task bookkeeping.
        @details    Hash tracked diff against HEAD and untracked content, excluding
                    journals and generated caches. Symlinks contribute their target
                    text; directory symlinks and malformed paths fail closed.
        @param[in]  run_id Stable run identifier.
        @return     SHA-256 fingerprint, including dirty candidate changes.
        @exception  IsolationError When Git or a content observation fails.
        """
        wt = self.path_for(run_id)
        paths = (".", ":(exclude).agentic/tasks/**", *_GENERATED_PATHSPECS)
        diff = self._run_wt(str(wt), "diff", "--binary", "HEAD", "--", *paths)
        untracked = self._run_wt(
            str(wt), "ls-files", "-z", "--others", "--exclude-standard", "--", *paths
        ).stdout
        if untracked and not untracked.endswith("\0"):
            raise IsolationError("unterminated untracked progress path list")
        digest = hashlib.sha256(diff.stdout.encode("utf-8"))
        for name in sorted(untracked.split("\0")[:-1]):
            relative = PurePosixPath(name)
            if (not name or relative.is_absolute() or PureWindowsPath(name).drive
                    or "\\" in name or ".." in relative.parts
                    or relative.as_posix() != name):
                raise IsolationError(f"unsafe untracked progress path: {name!r}")
            source = wt.joinpath(*relative.parts)
            try:
                for parent in source.parents:
                    if parent == wt:
                        break
                    if parent.is_symlink():
                        raise IsolationError(f"symlink parent in progress path: {name!r}")
                mode = source.lstat().st_mode
                if stat.S_ISLNK(mode):
                    kind, content = b"link", os.fsencode(os.readlink(source))
                elif stat.S_ISREG(mode):
                    kind, content = b"file", source.read_bytes()
                else:
                    raise IsolationError(f"unsupported progress file: {name!r}")
            except OSError as exc:
                raise IsolationError(f"cannot observe progress file {name!r}: {exc}") from exc
            for value in (name.encode("utf-8"), kind, content):
                digest.update(len(value).to_bytes(8, "big"))
                digest.update(value)
        return digest.hexdigest()

    def commit_series(self, run_id: str, base_ref: str) -> list[str]:
        """@brief Return the ordered SHA and subject series over the target."""
        result = self._run_wt(
            str(self.path_for(run_id)),
            "log",
            "--format=%H %s",
            "--reverse",
            f"{base_ref}..HEAD",
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    @staticmethod
    def _porcelain_path(line: str) -> str:
        """
        @brief      The changed path from one `git status --porcelain` line.
        @details    Strips the two status columns and their trailing space, and
                    resolves a rename/copy entry ("R  old -> new") to the NEW
                    path so a single rename counts as one file, not as the odd
                    string "old -> new". Surrounding quotes git adds for paths
                    with special characters are removed.
        @param[in]  line One porcelain status line.
        @return     The repository-relative path, or "" for a blank line.
        """
        entry = line[3:].strip() if len(line) > 3 else line.strip()
        if not entry:
            return ""
        if " -> " in entry:  # rename/copy: count the destination path
            entry = entry.split(" -> ", 1)[1].strip()
        return entry.strip('"')

    def commit_all_if_dirty(self, run_id: str, message: str) -> bool:
        """
        @brief      Commit pending worktree changes as one checkpoint.
        @details    Used by the conductor after each executor stage and after
                    its own verification. `git add -A` includes non-ignored
                    workflow artifacts (for example the AEGIS task journal) while
                    naturally leaving ignored dependency caches out of the
                    branch. Empty status is a no-op.
        @param[in]  run_id Stable run identifier.
        @param[in]  message Commit message.
        @return     True when a commit was created.
        @exception  IsolationError When git fails.
        """
        wt = str(self.path_for(run_id))
        if not self._run_wt(wt, "status", "--porcelain").stdout.strip():
            return False
        self._run_wt(wt, "add", "-A")
        if not self._run_wt(wt, "status", "--porcelain").stdout.strip():
            return False
        self._run_wt(wt, "commit", "-m", message)
        return True

    def scrub_container_worktree_config(self) -> None:
        """
        @brief   Remove ADORE container worktree paths from the host repo config.
        @details Some executor CLIs or git recovery paths may persist
                 `core.worktree = /adore/work` into the shared `.git/config`
                 when Git is driven through container-only GIT_DIR/GIT_WORK_TREE
                 values. That breaks host Git after the container exits because
                 `/adore/work` is not a host path. This scrub is intentionally
                 narrow: it removes only `[core] worktree` values pointing at
                 ADORE's `/adore/...` container mount, leaving legitimate host
                 paths and all other config intact.
        """
        config_path = self.repo_path / ".git" / "config"
        try:
            lines = config_path.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError:
            return
        in_core = False
        changed = False
        kept: list[str] = []
        for line in lines:
            stripped = line.strip()
            lowered = stripped.lower()
            if lowered.startswith("[") and lowered.endswith("]"):
                in_core = lowered == "[core]"
            if in_core and lowered.startswith("worktree"):
                _, _, value = stripped.partition("=")
                if value.strip().startswith("/adore/"):
                    changed = True
                    continue
            kept.append(line)
        if changed:
            config_path.write_text("".join(kept), encoding="utf-8")

    # -- internals ------------------------------------------------------------------

    def _branch_exists(self, branch: str) -> bool:
        """
        @brief      Whether a local branch exists in the clone.
        @param[in]  branch Branch name.
        @return     True when `git rev-parse --verify` succeeds.
        """
        self.scrub_container_worktree_config()
        result = self.runner(
            [
                "git", "-C", str(self.repo_path),
                "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}",
            ]
        )
        return result.ok

    def _git(self, *args: str) -> CommandResult:
        """
        @brief      Run git against the local clone, raising on failure.
        @param[in]  args git subcommand and arguments.
        @return     The successful CommandResult.
        @exception  IsolationError When git exits non-zero.
        """
        self.scrub_container_worktree_config()
        argv = ["git", "-C", str(self.repo_path), *args]
        result = self.runner(argv)
        if not result.ok:
            raise IsolationError(f"git {args[0]} failed", result.argv, result.stderr)
        return result

    def _run_wt(self, worktree: str, *args: str) -> CommandResult:
        """
        @brief      Run git against a worktree dir, raising on failure.
        @param[in]  worktree Worktree path.
        @param[in]  args git subcommand and arguments.
        @return     The successful CommandResult.
        @exception  IsolationError When git exits non-zero.
        """
        self.scrub_container_worktree_config()
        identity = (["-c", f"user.name={self.git_name}",
                     "-c", f"user.email={self.git_email}"]
                    if args[0] == "commit" and self.git_name and self.git_email
                    else [])
        argv = ["git", "-C", worktree, *identity, *args]
        result = self.runner(argv)
        if not result.ok:
            raise IsolationError(f"git {args[0]} failed", result.argv, result.stderr)
        return result


class ContainerManager:
    """
    @brief   Per-run executor containers (execution isolation).
    @details One long-lived container per run-id, kept idle with
             `sleep infinity`; the executor is launched inside it via exec.
             Parked containers are stopped and retained for resume or explicit
             cleanup boundaries. The worktree and repo are bind-mounted;
             project dependencies resolve into the mounted cache volumes,
             never into the worktree (design 10a).
    """

    def __init__(
        self,
        runtime: str,
        image: str,
        uv_cache_volume: str,
        npm_cache_volume: str,
        runner: CommandRunner = run_command,
        *,
        run_args: Sequence[str] = (),
        egress: ContainerEgressConfig | None = None,
        selinux_relabel: str = "off",
        pull_never: bool = False,
    ) -> None:
        """
        @brief      Configure the manager from the [container] section.
        @details    The runtime may be a plain binary ("docker" / "podman") or
                    a wrapped command ("wsl -d Ubuntu-24.04 -- docker"). WSL
                    mode is detected from the first token and switches on
                    mount-path translation and WSLENV env propagation.
        @param[in]  runtime Container runtime command (may contain spaces).
        @param[in]  image Executor image reference.
        @param[in]  uv_cache_volume Persistent uv cache volume name.
        @param[in]  npm_cache_volume Persistent npm cache volume name.
        @param[in]  runner Command runner (injectable for tests).
        @param[in]  run_args Extra option tokens for `<runtime> run`
                             ([container] run_args; e.g. "--userns=keep-id"
                             for rootless podman, live finding 2026-07-04).
        @param[in]  egress Optional egress policy for executor containers.
        @param[in]  selinux_relabel [container] selinux_relabel mode; "shared"
                             appends `z` to every host bind mount so an
                             SELinux-enforcing host lets the container read
                             them. Config validation is the operator-facing
                             gate; an unknown value fails closed here too
                             rather than silently mounting unlabeled.
        @param[in]  pull_never Require both executor and proxy images to be
                    present locally. The disposable web readiness probe uses
                    this without changing normal conductor image policy.
        @exception  ValueError When selinux_relabel is not a known mode.
        """
        if selinux_relabel not in SELINUX_RELABEL_OPTIONS:
            raise ValueError(
                f"unsupported selinux_relabel mode: {selinux_relabel!r}"
            )
        self.runtime = runtime
        self.runtime_argv = shlex.split(runtime)
        self.wsl_mode = Path(self.runtime_argv[0]).stem.lower() == "wsl"
        self.image = image
        self.uv_cache_volume = uv_cache_volume
        self.npm_cache_volume = npm_cache_volume
        self.runner = runner
        self.run_args = [str(arg) for arg in run_args]
        self.egress = egress or ContainerEgressConfig()
        self.selinux_relabel = selinux_relabel
        self.pull_never = pull_never

    def status(self, name: str) -> str:
        """
        @brief      The container's lifecycle state.
        @param[in]  name Container name ("<slug>-run-<run-id>").
        @return     "running", "exited", "created", ... or "absent".
        @exception  IsolationError When the runtime fails for another reason.
        """
        result = self.runner(
            [*self.runtime_argv, "inspect", "--format", "{{.State.Status}}", name]
        )
        if result.ok:
            return result.stdout.strip() or "absent"
        text = (result.stderr + result.stdout).lower()
        if any(marker in text for marker in _ABSENT_MARKERS):
            return "absent"
        raise IsolationError(f"{self.runtime} inspect failed", result.argv, result.stderr)

    def resource_identity(self, name: str) -> dict[str, str]:
        """
        @brief Read actual owned resource/image identity with strict inspect validation.
        @param[in] name Exact expected run container name.
        @return Container ID, image ID and observed lifecycle status.
        @exception IsolationError For missing, corrupt or foreign resources.
        """
        result = self.runner([*self.runtime_argv, "inspect", name], timeout=30)
        try:
            if not result.ok or result.timed_out:
                raise ValueError
            if len(result.stdout) > 1_000_000:
                raise ValueError
            data = strict_json_loads(result.stdout)
            if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
                raise ValueError
            item = data[0]
            cid, image, status = item["Id"], item["Image"], item["State"]["Status"]
            if (
                item["Name"].lstrip("/") != name
                or not isinstance(cid, str)
                or not re.fullmatch(r"[0-9a-f]{64}", cid)
                or not isinstance(image, str)
                or not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", image)
                or status not in {"running", "exited", "created", "paused", "restarting", "dead"}
            ):
                raise ValueError
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise IsolationError("container identity unavailable or corrupt") from exc
        return {"container_id": cid, "image_id": image, "status": status}

    def image_identity(self, image: str) -> str:
        """
        @brief Resolve a locally available image ID without pulling or installing.
        @param[in] image Effective reviewed image reference.
        @return Exact runtime image ID.
        @exception IsolationError For missing or malformed runtime output.
        """
        result = self.runner(
            [*self.runtime_argv, "image", "inspect", "--format", "{{.Id}}", image], timeout=30
        )
        value = result.stdout.strip()
        if (
            not result.ok
            or result.timed_out
            or not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", value)
        ):
            raise IsolationError("image identity unavailable or corrupt")
        return value

    def list_containers(self, prefix: str) -> list[str]:
        """
        @brief      Names of all containers (any state) with a name prefix.
        @param[in]  prefix Container-name prefix ("<slug>-run-").
        @return     Matching container names.
        @exception  IsolationError When the runtime fails.
        """
        result = self._run(
            [*self.runtime_argv, "ps", "--all",
             "--filter", f"name={prefix}", "--format", "{{.Names}}"]
        )
        return [
            name for line in result.stdout.splitlines()
            if (name := line.strip()) and name.startswith(prefix)
        ]

    def list_executors(self, prefix: str) -> list[str]:
        """
        @brief      Names of all executor containers (any state) with a prefix.
        @details    `list_containers` without egress proxy containers: a proxy
                    name often starts with the executor prefix but is not an
                    executor.
        @param[in]  prefix Container-name prefix ("<slug>-run-").
        @return     Matching executor container names.
        @exception  IsolationError When the runtime fails.
        """
        return [
            name for name in self.list_containers(prefix)
            if not name.endswith(_PROXY_SUFFIX)
        ]

    def list_egress_networks(self, prefix: str | None = None) -> list[str]:
        """
        @brief      Names of ADORE egress networks.
        @param[in]  prefix Optional network-name prefix override.
        @return     Matching network names.
        @exception  IsolationError When the runtime fails.
        """
        network_prefix = prefix or self.egress.network_prefix
        result = self._run(
            [*self.runtime_argv, "network", "ls",
             "--filter", f"name={network_prefix}", "--format", "{{.Name}}"]
        )
        owned_prefix = f"{network_prefix}-"
        return [
            name for line in result.stdout.splitlines()
            if (name := line.strip()) and name.startswith(owned_prefix)
        ]

    def cleanup_orphan_containers(
        self,
        prefix: str,
        targets: set[str],
        retained: set[str],
    ) -> list[str]:
        """
        @brief      Best-effort removal of listed target executor containers.
        @details    Removes a listed executor only when its exact name is one
                    of `targets` and not one of `retained`, so containers of
                    other projects under a shared prefix are never touched.
                    The runtime filter supplies candidates only; exact prefix
                    filtering happens in `list_containers`. Egress proxies are
                    handled separately so cleanup can report them after a
                    profile changes egress mode.
        @param[in]  prefix Deterministic executor-container prefix.
        @param[in]  targets Exact executor names cleanup may remove.
        @param[in]  retained Exact executor names to keep.
        @return     Executor container names successfully removed.
        """
        wanted = targets - retained
        removed: list[str] = []
        for name in self.list_containers(prefix):
            if name not in wanted:
                continue
            try:
                self._remove_container(name)
            except IsolationError:
                continue
            removed.append(name)
        return removed

    def cleanup_egress_proxies(
        self,
        targets: set[str],
        retained: set[str],
    ) -> list[str]:
        """
        @brief      Best-effort removal of the target executors' proxy containers.
        @details    Covers each executor's per-run proxy name; a name also
                    derived from a retained executor is kept. Candidates are
                    listed by the proxy suffix, not the executor prefix: a
                    bounded per-run name of a long slug no longer starts with
                    `<slug>-run-`.
        @param[in]  targets Exact executor names whose proxies may go.
        @param[in]  retained Exact executor names whose proxies stay.
        @return     Proxy container names successfully removed.
        """
        wanted = (
            {self._proxy_name(name) for name in targets}
            - {self._proxy_name(name) for name in retained}
        )
        result = self._run(
            [*self.runtime_argv, "ps", "--all",
             "--filter", f"name={_PROXY_SUFFIX}", "--format", "{{.Names}}"]
        )
        listed = [
            name for line in result.stdout.splitlines()
            if (name := line.strip()) and name.endswith(_PROXY_SUFFIX)
        ]
        removed: list[str] = []
        for name in listed:
            if name not in wanted:
                continue
            try:
                self._remove_container(name)
            except IsolationError:
                continue
            removed.append(name)
        return removed

    def cleanup_egress_networks(
        self,
        targets: set[str],
        retained: set[str],
    ) -> list[str]:
        """
        @brief      Best-effort removal of the target executors' egress networks.
        @details    Covers both the canonical ADORE prefix and the current
                    configured prefix even when the current mode is not
                    allowlist-proxy. Arbitrary historical prefixes are never
                    guessed. Each executor's per-run network names are
                    covered; a name also derived from a retained executor is
                    kept.
        @param[in]  targets Exact executor names whose networks may go.
        @param[in]  retained Exact executor names whose networks stay.
        @return     Egress network names successfully removed.
        """
        prefixes = {EGRESS_NETWORK_PREFIX, self.egress.network_prefix}

        def networks(executors: set[str]) -> set[str]:
            return {
                network
                for prefix in prefixes
                for name in executors
                for network in (self._egress_network_name(name, prefix=prefix),)
            }

        wanted = networks(targets) - networks(retained)
        removed: list[str] = []
        seen: set[str] = set()
        for prefix in sorted(prefixes):
            for name in self.list_egress_networks(prefix):
                if name in seen or name not in wanted:
                    continue
                seen.add(name)
                try:
                    self._remove_network(name)
                except IsolationError:
                    continue
                removed.append(name)
        return removed

    def ensure_volumes(self) -> None:
        """
        @brief   Create the persistent cache volumes, idempotently.
        @details docker `volume create` is idempotent, but podman errors when
                 the volume already exists (live finding 2026-07-05); an
                 existing volume is the success case for both, so that error
                 is tolerated while any other failure still raises.
        @exception IsolationError When the runtime fails for another reason.
        """
        for volume in (self.uv_cache_volume, self.npm_cache_volume):
            result = self.runner([*self.runtime_argv, "volume", "create", volume])
            if result.ok:
                continue
            text = (result.stderr + result.stdout).lower()
            if any(marker in text for marker in _EXISTS_MARKERS):
                continue
            raise IsolationError(
                f"{self.runtime} volume create failed", result.argv, result.stderr
            )

    def provision(
        self,
        name: str,
        repo_path: str | Path,
        worktree_path: str | Path,
        io_path: str | Path,
        env: dict[str, str],
    ) -> str:
        """
        @brief      Bring the run's container up (create or restart).
        @details    Idempotent against the current state: running -> no-op;
                    stopped/created -> start (keep-warm resume, design 8b);
                    absent -> create fresh with the mounts and env. Secrets
                    never appear in argv: secret env keys are passed as bare
                    `--env KEY` and the values travel via the runtime CLI's
                    own process environment. Safe runtime variables (HOME,
                    Git mount paths, Pi agent settings, bot identity) are passed
                    inline so they survive wrapped runtimes consistently. In
                    WSL mode the mount sources are translated to /mnt/<drive>/
                    form and bare env keys are additionally listed in WSLENV
                    so Windows-side secret values cross into the WSL process
                    (wsl.exe does not forward arbitrary env vars otherwise).
        @param[in]  name Container name ("<slug>-run-<run-id>").
        @param[in]  repo_path Host path of the local clone (mounted at
                              /adore/repo; needed for the shared object store).
        @param[in]  worktree_path Host path of the run worktree (mounted at
                              /adore/work, the container working dir).
        @param[in]  io_path Host path of the run's io exchange dir (mounted
                              at /adore/io; gate scripts in, event streams out
                              - outside the worktree so the executor can
                              never commit them).
        @param[in]  env Environment for the container (git env from
                        build_container_env plus the executor's secret subset).
        @return     What happened: "running" (no-op), "started" (warm
                    resume), or "created" (fresh container - anything that
                    lived only inside the old one, like executor sessions, is
                    gone; live finding 2026-07-03).
        @exception  IsolationError When the runtime fails.
        """
        state = self.status(name)
        if state == "running":
            return "running"
        if self.egress.mode == "allowlist-proxy":
            self._ensure_proxy_context(name, io_path)
        if state != "absent":
            self.start(name)
            return "started"
        Path(io_path).mkdir(parents=True, exist_ok=True)
        argv = [
            *self.runtime_argv, "run", "--detach", *self.run_args,
            *(["--pull=never"] if self.pull_never else []),
            "--name", name,
            "--volume", self._bind_mount(repo_path, CONTAINER_REPO_MOUNT),
            "--volume", self._bind_mount(worktree_path, CONTAINER_WORKTREE_MOUNT),
            "--volume", self._bind_mount(io_path, CONTAINER_IO_MOUNT),
            "--volume", f"{self.uv_cache_volume}:{CONTAINER_UV_CACHE_MOUNT}",
            "--volume", f"{self.npm_cache_volume}:{CONTAINER_NPM_CACHE_MOUNT}",
            "--workdir", CONTAINER_WORKTREE_MOUNT,
        ]
        if self.egress.mode == "none":
            argv += ["--network", "none"]
        elif self.egress.mode == "allowlist-proxy":
            argv += ["--network", self._egress_network_name(name)]
            env = {**env, **self._proxy_env()}
        # Safe runtime values go inline: they are not secrets, and the
        # bare-key/WSLENV path is brittle across wrapped runtimes (HOME is
        # reset by login shells; an agent home variable was dropped by
        # the WSL/Podman path in an earlier pilot). Bare keys stay reserved for secrets.
        secret_env = dict(env)
        for key in _INLINE_ENV_KEYS:
            value = secret_env.pop(key, None)
            if value is not None:
                argv += ["--env", f"{key}={value}"]
        for key in secret_env:
            argv += ["--env", key]
        argv += [self.image, "sleep", "infinity"]
        process_env = {**os.environ, **secret_env}
        if self.wsl_mode and secret_env:
            existing = process_env.get("WSLENV", "")
            shared = ":".join(secret_env)
            process_env["WSLENV"] = f"{existing}:{shared}" if existing else shared
        result = self.runner(argv, env=process_env)
        if not result.ok:
            raise IsolationError(f"{self.runtime} run failed", result.argv, result.stderr)
        return "created"

    def verify_required_tools(
        self,
        name: str,
        checks: Sequence[str],
        *,
        env: dict[str, str] | None = None,
    ) -> None:
        """
        @brief      Run project-image required tool checks inside the container.
        @details    Each check is a shell-free command string parsed with
                    shlex and executed through the same `exec` path as gates.
                    This catches a missing runtime-project dependency at
                    provision time, before an executor spends iterations
                    discovering it mid-delivery.
        @param[in]  name Container name.
        @param[in]  checks Command strings such as "terraform --version".
        @param[in]  env Optional exec-time environment.
        @exception  IsolationError When a check is malformed or exits non-zero.
        """
        for check in checks:
            try:
                argv = shlex.split(check)
            except ValueError as exc:
                raise IsolationError(
                    f"required tool check is not parseable: {check!r}",
                    stderr=str(exc),
                ) from exc
            if not argv:
                raise IsolationError("required tool check is empty")
            result = self.exec(name, argv, env=env)
            if not result.ok:
                stderr = result.stderr or result.stdout
                raise IsolationError(
                    f"required tool check failed: {check}",
                    result.argv,
                    stderr,
                )

    def start(self, name: str) -> None:
        """
        @brief      Start a stopped container (fast resume from park).
        @param[in]  name Container name.
        @exception  IsolationError When the runtime fails.
        """
        self._run([*self.runtime_argv, "start", name])

    def stop(self, name: str) -> None:
        """
        @brief      Stop the container, keeping its filesystem (park).
        @details    Idempotent: an absent container is not an error.
        @param[in]  name Container name.
        @exception  IsolationError When the runtime fails for another reason.
        """
        result = self.runner([*self.runtime_argv, "stop", name])
        if not result.ok and self.status(name) != "absent":
            raise IsolationError(f"{self.runtime} stop failed", result.argv, result.stderr)

    def interrupt(self, name: str) -> None:
        """
        @brief Promptly stop an active executor container after a cancel request.
        @param[in] name Exact run container name.
        @exception IsolationError When the bounded stop fails.
        """
        result = self.runner(
            [*self.runtime_argv, "stop", "--time", "2", name], timeout=20,
        )
        if not result.ok:
            raise IsolationError(
                f"{self.runtime} interrupt failed", result.argv, result.stderr,
            )

    def remove(self, name: str) -> None:
        """
        @brief      Force-remove the container (reap / terminal cleanup).
        @details    Idempotent: an absent container is not an error. The
                    worktree and `.adore` state always survive a reap.
        @param[in]  name Container name.
        @exception  IsolationError When the runtime fails for another reason.
        """
        self._remove_container(name)
        self.remove_egress(name)

    def remove_egress(self, name: str) -> None:
        """
        @brief      Remove the proxy container and network for one run.
        @param[in]  name Executor container name.
        @exception  IsolationError When the runtime fails unexpectedly.
        """
        if self.egress.mode != "allowlist-proxy":
            return
        proxy_name = self._proxy_name(name)
        self._remove_container(proxy_name)
        network = self._egress_network_name(name)
        self._remove_network(network)

    def exec(
        self,
        name: str,
        argv: Sequence[str],
        *,
        timeout: float | None = DEFAULT_COMMAND_TIMEOUT,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        """
        @brief      Run a command inside the container (the executor seam).
        @details    Returns the CommandResult as data instead of raising: the
                    executed command's exit code is a conductor signal
                    (gate pass/fail), not an isolation failure. Runs in the
                    container's working dir (/adore/work).

                    This seam is ALWAYS bounded. `run_command`'s own default
                    applies only when a caller omits the keyword, so forwarding
                    a `None` would reach `subprocess.run(timeout=None)` and
                    hang the single-threaded poll loop for good on a wedged
                    container runtime or an interactive required-tool check.
                    An explicit `None` therefore resolves to
                    `DEFAULT_COMMAND_TIMEOUT` here rather than meaning
                    "unbounded"; callers that need longer (an executor gate
                    launch) pass their own budget.
        @param[in]  name Container name.
        @param[in]  argv Command and arguments to run inside.
        @param[in]  timeout Wall-clock bound in seconds; `None` means "use the
                            default bound", never "no bound".
        @param[in]  env Optional exec-time env; safe values go inline, secrets
                        are passed by bare key/process environment.
        @return     The captured CommandResult.
        """
        if timeout is None:
            timeout = DEFAULT_COMMAND_TIMEOUT
        full, process_env = self._exec_command(name, argv, env, interactive=False)
        return self.runner(full, timeout=timeout, env=process_env)

    def spawn(
        self,
        name: str,
        argv: Sequence[str],
        *,
        env: dict[str, str] | None = None,
        popen: Callable[..., subprocess.Popen] = subprocess.Popen,
    ) -> subprocess.Popen:
        """
        @brief      Start a long-lived command inside the container with live pipes.
        @details    The streaming counterpart of `exec` for executors driven over
                    stdin/stdout (Pi's RPC mode): `exec -i` keeps the command's
                    stdin attached, and the environment follows exactly `exec`'s
                    rules (safe values inline, secret values only in the client
                    process environment). The caller owns the process: it bounds
                    the run and ends it. Closing stdin, or ending the client,
                    closes the command's stdin inside the container.
        @param[in]  name Container name.
        @param[in]  argv Command and arguments to run inside.
        @param[in]  env Optional exec-time env, as for `exec`.
        @param[in]  popen Process factory (tests inject a recorder).
        @return     The started client process with binary stdin/stdout/stderr pipes.
        @exception  OSError When the runtime client cannot be started.
        """
        full, process_env = self._exec_command(name, argv, env, interactive=True)
        return popen(  # noqa: S603 - fixed argv, no shell
            full,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=process_env,
        )

    def _exec_command(
        self,
        name: str,
        argv: Sequence[str],
        env: dict[str, str] | None,
        *,
        interactive: bool,
    ) -> tuple[list[str], dict[str, str] | None]:
        """
        @brief      Build one `exec` argv and the client process environment.
        @param[in]  name Container name.
        @param[in]  argv Command and arguments to run inside.
        @param[in]  env Optional exec-time env; safe keys inline, secrets bare.
        @param[in]  interactive Attach stdin (`-i`) for a streaming command.
        @return     (full argv, process env or None when no env is passed).
        """
        full = [*self.runtime_argv, "exec", *(["-i"] if interactive else [])]
        exec_env = dict(env or {})
        if self.egress.mode == "allowlist-proxy":
            exec_env.update(self._proxy_env())
        secret_env = exec_env
        for key in _INLINE_ENV_KEYS:
            value = secret_env.pop(key, None)
            if value is not None:
                full += ["--env", f"{key}={value}"]
        for key in secret_env:
            full += ["--env", key]
        full += [name, *[str(part) for part in argv]]
        process_env = {**os.environ, **secret_env}
        if self.wsl_mode and secret_env:
            existing = process_env.get("WSLENV", "")
            shared = ":".join(secret_env)
            process_env["WSLENV"] = f"{existing}:{shared}" if existing else shared
        return full, process_env if exec_env else None

    # -- internals ------------------------------------------------------------------

    def _safe_name(self, value: str) -> str:
        """
        @brief      Convert a run/container id into a runtime-safe name segment.
        @param[in]  value Raw name.
        @return     Runtime-safe name segment ("run" when nothing is left).
        """
        safe = _SAFE_NAME_RE.sub("-", value).strip("-._")
        return safe or "run"

    def _bounded_name(self, value: str, limit: int) -> str:
        """
        @brief      Runtime-safe name segment of at most `limit` characters.
        @details    A segment that fits is returned unchanged. A longer one
                    keeps its start and ends in "-" plus the first hex
                    characters of the SHA-256 of the full value, so values that
                    agree in their first characters (two runs of one long-named
                    project) still get different segments.
        @param[in]  value Raw name (an executor container name).
        @param[in]  limit Maximum returned length.
        @return     Bounded, per-value name segment.
        """
        safe = self._safe_name(value)
        if len(safe) <= limit:
            return safe
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:_NAME_DIGEST_LENGTH]
        stem = safe[:limit - _NAME_DIGEST_LENGTH - 1].rstrip("-._")
        return f"{stem}-{digest}"

    def _egress_network_name(self, name: str, *, prefix: str | None = None) -> str:
        """
        @brief      Per-run internal egress network name.
        @param[in]  name Executor container name.
        @param[in]  prefix Optional owned network prefix override.
        @return     Network name.
        """
        bounded = self._bounded_name(name, _NETWORK_NAME_LIMIT)
        return f"{prefix or self.egress.network_prefix}-{bounded}"

    def _remove_container(self, name: str) -> None:
        """
        @brief      Idempotently force-remove one exact container name.
        @param[in]  name Executor or proxy container name.
        @exception  IsolationError When the runtime fails for another reason.
        """
        result = self.runner([*self.runtime_argv, "rm", "--force", name])
        if not result.ok and self.status(name) != "absent":
            raise IsolationError(f"{self.runtime} rm failed", result.argv, result.stderr)

    def _remove_network(self, name: str) -> None:
        """
        @brief      Idempotently remove one exact egress network name.
        @param[in]  name Egress network name from an owned-prefix listing.
        @exception  IsolationError When the runtime fails unexpectedly.
        """
        result = self.runner([*self.runtime_argv, "network", "rm", name])
        if result.ok:
            return
        text = (result.stderr + result.stdout).lower()
        if any(marker in text for marker in _ABSENT_MARKERS):
            return
        raise IsolationError(
            f"{self.runtime} network rm failed", result.argv, result.stderr
        )

    def _proxy_name(self, name: str) -> str:
        """
        @brief      Per-run proxy container name.
        @param[in]  name Executor container name.
        @return     Proxy container name (at most 63 characters).
        """
        return f"{self._bounded_name(name, _PROXY_NAME_LIMIT)}{_PROXY_SUFFIX}"

    def _proxy_env(self) -> dict[str, str]:
        """
        @brief      Proxy variables injected into executor containers/execs.
        @return     Uppercase and lowercase HTTP proxy environment mapping.
        """
        proxy_url = f"http://{PROXY_ALIAS}:{self.egress.proxy_port}"
        no_proxy = ",".join(self.egress.no_proxy)
        return {
            "HTTP_PROXY": proxy_url,
            "HTTPS_PROXY": proxy_url,
            "ALL_PROXY": proxy_url,
            "NO_PROXY": no_proxy,
            "http_proxy": proxy_url,
            "https_proxy": proxy_url,
            "all_proxy": proxy_url,
            "no_proxy": no_proxy,
        }

    def _squid_domain(self, pattern: str) -> str:
        """
        @brief      Convert an ADORE hostname pattern to Squid dstdomain form.
        @param[in]  pattern Exact or wildcard hostname.
        @return     Squid dstdomain token.
        """
        return f".{pattern[2:]}" if pattern.startswith("*.") else pattern

    def _write_proxy_config(self, io_path: str | Path) -> Path:
        """
        @brief      Write the per-run Squid allowlist configuration.
        @param[in]  io_path Run IO directory.
        @return     Host path to the generated Squid config.
        """
        proxy_dir = Path(io_path) / "egress-proxy"
        proxy_dir.mkdir(parents=True, exist_ok=True)
        domains = " ".join(self._squid_domain(host) for host in self.egress.allowlist)
        config_path = proxy_dir / "squid.conf"
        config_path.write_text(
            "\n".join([
                f"http_port {self.egress.proxy_port}",
                f"acl allowed_domains dstdomain {domains}",
                "http_access allow allowed_domains",
                "http_access deny all",
                "access_log stdio:/var/log/squid/access.log",
                "cache_log /var/log/squid/cache.log",
                "coredump_dir /var/spool/squid",
                "",
            ]),
            encoding="utf-8",
        )
        return config_path

    def _ensure_proxy_context(self, name: str, io_path: str | Path) -> None:
        """
        @brief      Ensure the per-run proxy network and proxy container exist.
        @param[in]  name Executor container name.
        @param[in]  io_path Run IO directory for generated proxy config.
        @exception  IsolationError When any runtime operation fails.
        """
        network = self._egress_network_name(name)
        result = self.runner([*self.runtime_argv, "network", "create", "--internal", network])
        if not result.ok:
            text = (result.stderr + result.stdout).lower()
            if not any(marker in text for marker in _EXISTS_MARKERS):
                raise IsolationError(
                    f"{self.runtime} network create failed", result.argv, result.stderr
                )
        proxy_name = self._proxy_name(name)
        proxy_state = self.status(proxy_name)
        if proxy_state == "absent":
            config_path = self._write_proxy_config(io_path)
            self._run([
                *self.runtime_argv, "run", "--detach",
                *(["--pull=never"] if self.pull_never else []),
                "--name", proxy_name,
                "--volume", self._bind_mount(config_path, "/etc/squid/squid.conf", "ro"),
                self.egress.proxy_image,
            ])
        elif proxy_state != "running":
            self.start(proxy_name)
        connect = self.runner([
            *self.runtime_argv, "network", "connect",
            "--alias", PROXY_ALIAS, network, proxy_name,
        ])
        if connect.ok:
            return
        text = (connect.stderr + connect.stdout).lower()
        if any(marker in text for marker in _CONNECTED_MARKERS):
            return
        raise IsolationError(
            f"{self.runtime} network connect failed", connect.argv, connect.stderr
        )

    def _mount_source(self, path: str | Path) -> str:
        """
        @brief      The mount-source string for a host path.
        @details    Resolved to absolute first: a bare relative source would
                    be read by docker as a NAMED VOLUME, silently mounting an
                    empty volume instead of the host dir.
        @param[in]  path Host path.
        @return     WSL-translated (/mnt/<drive>/...) in WSL mode, POSIX-style
                    otherwise.
        """
        raw = os.fspath(path)
        if self.wsl_mode and _DRIVE_RE.match(raw.replace("\\", "/")):
            return wsl_mount_path(raw)
        absolute = Path(path).resolve()
        return wsl_mount_path(absolute) if self.wsl_mode else absolute.as_posix()

    def _bind_mount(self, source: str | Path, target: str, *options: str) -> str:
        """
        @brief      Compose one HOST BIND MOUNT argument for `--volume`.
        @details    Appends the configured SELinux relabel option after any
                    caller-supplied option, producing forms like `ro,z` that
                    both docker and podman accept. Without it, an enforcing
                    host leaves the mounted content carrying its host file
                    label, which `container_t` cannot read, and every stage
                    fails on permission denied. Named cache VOLUMES must not be
                    built here - see `SELINUX_RELABEL_OPTIONS` in config.
        @param[in]  source Host path to mount.
        @param[in]  target Container mount point.
        @param[in]  options Extra per-mount options, for example "ro".
        @return     The `source:target[:options]` argument value.
        """
        parts = [*options]
        relabel = SELINUX_RELABEL_OPTIONS[self.selinux_relabel]
        if relabel:
            parts.append(relabel)
        suffix = f":{','.join(parts)}" if parts else ""
        return f"{self._mount_source(source)}:{target}{suffix}"

    def _run(self, argv: list[str]) -> CommandResult:
        """
        @brief      Run a container-runtime command, raising on failure.
        @param[in]  argv Full command vector (runtime prefix included).
        @return     The successful CommandResult.
        @exception  IsolationError When the command exits non-zero.
        """
        result = self.runner(argv)
        if not result.ok:
            subcommand = argv[len(self.runtime_argv)] if len(argv) > len(self.runtime_argv) else "?"
            raise IsolationError(
                f"{self.runtime} {subcommand} failed", result.argv, result.stderr
            )
        return result


# END OF FILE
