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
         container paths and git is directed with GIT_DIR / GIT_WORK_TREE
         environment variables instead of path discovery. The container
         runtime may be a wrapped command (for example
         "wsl -d Ubuntu-24.04 -- docker" for Docker Engine inside WSL2); in
         WSL mode mount sources are translated to /mnt/<drive>/ paths and
         env-value propagation crosses the WSL boundary via WSLENV.
@author Eng. Dan Dumitru Pasare
@date 2026-07-05
@version 0.3.0
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Sequence
import os
from pathlib import Path
import re
import shlex

from ador.util import CommandResult, CommandRunner, run_command

# CONSTANTS

CONTAINER_HOME = "/home/ador"
CONTAINER_REPO_MOUNT = "/ador/repo"
CONTAINER_WORKTREE_MOUNT = "/ador/work"
CONTAINER_IO_MOUNT = "/ador/io"
CONTAINER_UV_CACHE_MOUNT = f"{CONTAINER_HOME}/.cache/uv"
CONTAINER_NPM_CACHE_MOUNT = f"{CONTAINER_HOME}/.npm"

_ABSENT_MARKERS = ("no such container", "no such object", "not found")
# podman `volume create` errors when the volume already exists; docker is
# idempotent and stays silent (live finding 2026-07-05, podman pilot).
_EXISTS_MARKERS = ("already exists",)
_DRIVE_RE = re.compile(r"^([A-Za-z]):[\\/]")

# DATA MODELS / TYPEDEFINITIONS


class IsolationError(RuntimeError):
    """
    @brief   Raised when a git or container-runtime call fails unexpectedly.
    @details Carries the command and stderr so failures are diagnosable from
             the journal without re-running anything (same shape as
             ForgeError / StateError; fail closed, never guess).
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.0
    """

    def __init__(self, message: str, argv: list[str] | None = None, stderr: str = "") -> None:
        """
        @brief      Build the error with command context.
        @param[in]  message Human-readable summary.
        @param[in]  argv The command that failed.
        @param[in]  stderr Captured stderr from the tool.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        detail = message
        if argv:
            detail += f" | argv: {' '.join(argv)}"
        if stderr.strip():
            detail += f" | stderr: {stderr.strip()}"
        super().__init__(detail)
        self.argv = argv or []
        self.stderr = stderr


# PUBLIC API


def wsl_mount_path(path: str | Path) -> str:
    """
    @brief      Translate a Windows host path to its WSL view for mounting.
    @details    A daemon running inside WSL2 cannot resolve "D:/x/y"; the same
                directory is visible there as "/mnt/d/x/y". Paths without a
                drive letter (already POSIX) pass through unchanged.
    @param[in]  path Host path.
    @return     The mount source usable by a WSL-side docker daemon.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    posix = Path(path).as_posix()
    match = _DRIVE_RE.match(posix)
    if not match:
        return posix
    drive = match.group(1).lower()
    return f"/mnt/{drive}/{posix[3:]}"


def build_container_env(git_dir_name: str, git_name: str, git_email: str) -> dict[str, str]:
    """
    @brief      Compose the git environment injected into a run's container.
    @details    GIT_DIR points at the worktree's admin dir under the mounted
                repo, GIT_WORK_TREE at the mounted worktree - this bypasses
                the worktree's `.git` pointer file, whose absolute host path
                is meaningless inside the container. The identity variables
                give commits the configured bot authorship
                (Setup_And_Credentials.md section 4).
    @param[in]  git_dir_name The worktree admin dir name under
                             `.git/worktrees/` (WorktreeManager.admin_dir_name).
    @param[in]  git_name Commit author/committer name (agent.name).
    @param[in]  git_email Commit author/committer email (agent.email).
    @return     Environment mapping for ContainerManager.provision.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    return {
        # Force the container user's home explicitly: some daemons (Docker
        # Engine in WSL2) inject the host user's HOME into every container,
        # overriding the image and breaking every HOME-based cache - tflint's
        # bundled plugin, uv, npm, opencode auth (live finding 2026-07-04).
        "HOME": CONTAINER_HOME,
        "GIT_DIR": f"{CONTAINER_REPO_MOUNT}/.git/worktrees/{git_dir_name}",
        "GIT_WORK_TREE": CONTAINER_WORKTREE_MOUNT,
        "GIT_AUTHOR_NAME": git_name,
        "GIT_AUTHOR_EMAIL": git_email,
        "GIT_COMMITTER_NAME": git_name,
        "GIT_COMMITTER_EMAIL": git_email,
    }


class WorktreeManager:
    """
    @brief   Per-run git worktrees on the host (code isolation).
    @details One worktree + one branch per run-id, created from the local
             clone at repo_path. Creation is idempotent so restart/resume
             reuses the same worktree instead of duplicating it (design 8a).
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.0
    """

    def __init__(
        self,
        repo_path: str | Path,
        root: str | Path,
        runner: CommandRunner = run_command,
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.1
        """
        self.repo_path = Path(repo_path).resolve()
        self.root = Path(root).resolve()
        self.runner = runner

    def path_for(self, run_id: str) -> Path:
        """
        @brief      The worktree directory for a run.
        @param[in]  run_id Stable run identifier.
        @return     `<root>/<run-id>`.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        return self.root / run_id

    def exists(self, run_id: str) -> bool:
        """
        @brief      Whether the run's worktree is present on disk.
        @param[in]  run_id Stable run identifier.
        @return     True when the worktree dir with its `.git` pointer exists.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @param[in]  branch Run branch name (for example "ador/<run-id>").
        @param[in]  base_ref Base ref for a new branch (for example
                             "origin/develop").
        @return     The worktree path.
        @exception  IsolationError When git fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @param[in]  run_id Stable run identifier.
        @param[in]  delete_branch Branch to force-delete, or None to keep it.
        @exception  IsolationError When git fails for another reason.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        path = self.path_for(run_id)
        if (path / ".git").exists():
            self._git("worktree", "remove", "--force", str(path))
        self._git("worktree", "prune")
        if delete_branch and self._branch_exists(delete_branch):
            self._git("branch", "-D", delete_branch)

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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
                 WSL bind-mount race) - exactly what `ador cleanup` sweeps.
        @return  Child directories, sorted.
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-04
        @version 0.1.0
        """
        if not self.root.is_dir():
            return []
        return sorted(entry for entry in self.root.iterdir() if entry.is_dir())

    def fetch(self, remote: str = "origin") -> None:
        """
        @brief      Fetch the remote into the local clone.
        @param[in]  remote Remote name.
        @exception  IsolationError When git fails (offline, auth, ...).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        return self.runner(
            ["git", "-C", str(self.path_for(run_id)), "merge", "--no-edit", ref]
        )

    def merge_in_progress(self, run_id: str) -> bool:
        """
        @brief      Whether an unconcluded merge sits in the worktree.
        @param[in]  run_id Stable run identifier.
        @return     True when MERGE_HEAD exists (conflicts not yet committed).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        result = self.runner(
            ["git", "-C", str(self.path_for(run_id)),
             "rev-parse", "-q", "--verify", "MERGE_HEAD"]
        )
        return result.ok

    def push(self, run_id: str, branch: str) -> CommandResult:
        """
        @brief      Push the run branch to origin (orchestrator-owned).
        @details    The ONLY remote-writing git call in ADOR; the executor is
                    blocked from pushing (design 11). Returned as data so the
                    conductor decides (auth/protection failures escalate).
        @param[in]  run_id Stable run identifier.
        @param[in]  branch Branch name to push.
        @return     The captured CommandResult.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        return self.runner(
            ["git", "-C", str(self.path_for(run_id)),
             "push", "--set-upstream", "origin", branch]
        )

    def is_dirty(self, run_id: str) -> bool:
        """
        @brief      Whether the run's worktree has uncommitted changes.
        @details    Conductor check before delivery: a validated run with a
                    dirty tree has work that would never reach the MR
                    (pilot finding 2026-07-03).
        @param[in]  run_id Stable run identifier.
        @return     True when `git status --porcelain` reports anything.
        @exception  IsolationError When git fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        result = self._run_wt(str(self.path_for(run_id)), "status", "--porcelain")
        return bool(result.stdout.strip())

    def commits_ahead(self, run_id: str, base_ref: str) -> int:
        """
        @brief      How many commits the run branch has over its base ref.
        @param[in]  run_id Stable run identifier.
        @param[in]  base_ref The ref the run branched from.
        @return     Commit count (0 = nothing to deliver).
        @exception  IsolationError When git fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        result = self._run_wt(
            str(self.path_for(run_id)), "rev-list", "--count", f"{base_ref}..HEAD"
        )
        return int(result.stdout.strip() or 0)

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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        wt = str(self.path_for(run_id))
        committed = self._run_wt(wt, "diff", "--name-only", f"{base_ref}...HEAD")
        pending = self._run_wt(wt, "status", "--porcelain")
        names = {line.strip() for line in committed.stdout.splitlines() if line.strip()}
        for line in pending.stdout.splitlines():
            if line.strip():
                names.add(line[3:].strip())
        return len(names)

    # -- internals ------------------------------------------------------------------

    def _branch_exists(self, branch: str) -> bool:
        """
        @brief      Whether a local branch exists in the clone.
        @param[in]  branch Branch name.
        @return     True when `git rev-parse --verify` succeeds.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        argv = ["git", "-C", worktree, *args]
        result = self.runner(argv)
        if not result.ok:
            raise IsolationError(f"git {args[0]} failed", result.argv, result.stderr)
        return result


class ContainerManager:
    """
    @brief   Per-run executor containers (execution isolation).
    @details One long-lived container per run-id, kept idle with
             `sleep infinity`; the executor is launched inside it via exec.
             Stopped (not removed) on park for fast resume; reaped (stopped +
             removed) when the parked TTL expires (design 8b). The worktree
             and repo are bind-mounted; project dependencies resolve into the
             mounted cache volumes, never into the worktree (design 10a).
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.1
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-04
        @version    0.2.0
        """
        self.runtime = runtime
        self.runtime_argv = shlex.split(runtime)
        self.wsl_mode = Path(self.runtime_argv[0]).stem.lower() == "wsl"
        self.image = image
        self.uv_cache_volume = uv_cache_volume
        self.npm_cache_volume = npm_cache_volume
        self.runner = runner
        self.run_args = [str(arg) for arg in run_args]

    def status(self, name: str) -> str:
        """
        @brief      The container's lifecycle state.
        @param[in]  name Container name ("<slug>-run-<run-id>").
        @return     "running", "exited", "created", ... or "absent".
        @exception  IsolationError When the runtime fails for another reason.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.1
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

    def list_containers(self, prefix: str) -> list[str]:
        """
        @brief      Names of all containers (any state) with a name prefix.
        @param[in]  prefix Container-name prefix ("<slug>-run-").
        @return     Matching container names.
        @exception  IsolationError When the runtime fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-04
        @version    0.1.0
        """
        result = self._run(
            [*self.runtime_argv, "ps", "--all",
             "--filter", f"name={prefix}", "--format", "{{.Names}}"]
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def ensure_volumes(self) -> None:
        """
        @brief   Create the persistent cache volumes, idempotently.
        @details docker `volume create` is idempotent, but podman errors when
                 the volume already exists (live finding 2026-07-05); an
                 existing volume is the success case for both, so that error
                 is tolerated while any other failure still raises.
        @exception IsolationError When the runtime fails for another reason.
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-05
        @version 0.2.0
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
                    never appear in argv: env keys are passed as bare
                    `--env KEY` and the values travel via the runtime CLI's
                    own process environment. In WSL mode the mount sources
                    are translated to /mnt/<drive>/ form and the env keys are
                    additionally listed in WSLENV so Windows-side values
                    cross into the WSL process (wsl.exe does not forward
                    arbitrary env vars otherwise).
        @param[in]  name Container name ("<slug>-run-<run-id>").
        @param[in]  repo_path Host path of the local clone (mounted at
                              /ador/repo; needed for the shared object store).
        @param[in]  worktree_path Host path of the run worktree (mounted at
                              /ador/work, the container working dir).
        @param[in]  io_path Host path of the run's io exchange dir (mounted
                              at /ador/io; gate scripts in, event streams out
                              - outside the worktree so the executor can
                              never commit them).
        @param[in]  env Environment for the container (git env from
                        build_container_env plus the executor's secret subset).
        @return     What happened: "running" (no-op), "started" (warm
                    resume), or "created" (fresh container - anything that
                    lived only inside the old one, like executor sessions, is
                    gone; live finding 2026-07-03).
        @exception  IsolationError When the runtime fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-04
        @version    0.1.4
        """
        state = self.status(name)
        if state == "running":
            return "running"
        if state != "absent":
            self.start(name)
            return "started"
        Path(io_path).mkdir(parents=True, exist_ok=True)
        argv = [
            *self.runtime_argv, "run", "--detach", *self.run_args,
            "--name", name,
            "--volume", f"{self._mount_source(repo_path)}:{CONTAINER_REPO_MOUNT}",
            "--volume", f"{self._mount_source(worktree_path)}:{CONTAINER_WORKTREE_MOUNT}",
            "--volume", f"{self._mount_source(io_path)}:{CONTAINER_IO_MOUNT}",
            "--volume", f"{self.uv_cache_volume}:{CONTAINER_UV_CACHE_MOUNT}",
            "--volume", f"{self.npm_cache_volume}:{CONTAINER_NPM_CACHE_MOUNT}",
            "--workdir", CONTAINER_WORKTREE_MOUNT,
        ]
        # HOME goes inline with its value: it is not a secret, and the
        # bare-key/WSLENV path does NOT survive the WSL login shell (which
        # resets HOME), silently overriding the image's correct ENV (live
        # finding 2026-07-04). Bare keys stay reserved for secrets.
        secret_env = dict(env)
        home = secret_env.pop("HOME", None)
        if home:
            argv += ["--env", f"HOME={home}"]
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

    def start(self, name: str) -> None:
        """
        @brief      Start a stopped container (fast resume from park).
        @param[in]  name Container name.
        @exception  IsolationError When the runtime fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.1
        """
        self._run([*self.runtime_argv, "start", name])

    def stop(self, name: str) -> None:
        """
        @brief      Stop the container, keeping its filesystem (park).
        @details    Idempotent: an absent container is not an error.
        @param[in]  name Container name.
        @exception  IsolationError When the runtime fails for another reason.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.1
        """
        result = self.runner([*self.runtime_argv, "stop", name])
        if not result.ok and self.status(name) != "absent":
            raise IsolationError(f"{self.runtime} stop failed", result.argv, result.stderr)

    def remove(self, name: str) -> None:
        """
        @brief      Force-remove the container (reap / terminal cleanup).
        @details    Idempotent: an absent container is not an error. The
                    worktree and `.ador` state always survive a reap.
        @param[in]  name Container name.
        @exception  IsolationError When the runtime fails for another reason.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.1
        """
        result = self.runner([*self.runtime_argv, "rm", "--force", name])
        if not result.ok and self.status(name) != "absent":
            raise IsolationError(f"{self.runtime} rm failed", result.argv, result.stderr)

    def exec(
        self,
        name: str,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> CommandResult:
        """
        @brief      Run a command inside the container (the executor seam).
        @details    Returns the CommandResult as data instead of raising: the
                    executed command's exit code is a conductor signal
                    (gate pass/fail), not an isolation failure. Runs in the
                    container's working dir (/ador/work).
        @param[in]  name Container name.
        @param[in]  argv Command and arguments to run inside.
        @param[in]  timeout Optional wall-clock bound (run budgets).
        @return     The captured CommandResult.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.1
        """
        full = [*self.runtime_argv, "exec", name, *[str(part) for part in argv]]
        return self.runner(full, timeout=timeout)

    # -- internals ------------------------------------------------------------------

    def _mount_source(self, path: str | Path) -> str:
        """
        @brief      The mount-source string for a host path.
        @details    Resolved to absolute first: a bare relative source would
                    be read by docker as a NAMED VOLUME, silently mounting an
                    empty volume instead of the host dir.
        @param[in]  path Host path.
        @return     WSL-translated (/mnt/<drive>/...) in WSL mode, POSIX-style
                    otherwise.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.1
        """
        absolute = Path(path).resolve()
        return wsl_mount_path(absolute) if self.wsl_mode else absolute.as_posix()

    def _run(self, argv: list[str]) -> CommandResult:
        """
        @brief      Run a container-runtime command, raising on failure.
        @param[in]  argv Full command vector (runtime prefix included).
        @return     The successful CommandResult.
        @exception  IsolationError When the command exits non-zero.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.1
        """
        result = self.runner(argv)
        if not result.ok:
            subcommand = argv[len(self.runtime_argv)] if len(argv) > len(self.runtime_argv) else "?"
            raise IsolationError(
                f"{self.runtime} {subcommand} failed", result.argv, result.stderr
            )
        return result


# END OF FILE
