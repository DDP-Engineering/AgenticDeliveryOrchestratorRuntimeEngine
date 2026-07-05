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
@file test_isolation.py
@brief Tests for the worktree and container isolation layer.
@details No real git or docker is invoked; a fake runner records every argv
         (and the env kwarg) and replays canned results, so command
         construction, idempotency, and fail-closed behavior are verified
         offline. Worktree-on-disk states are simulated with tmp_path files.
@author Eng. Dan Dumitru Pasare
@date 2026-07-03
@version 0.1.0
"""

from __future__ import annotations

# IMPORTS
import os
from pathlib import Path

from ador.isolation import (
    CONTAINER_IO_MOUNT,
    CONTAINER_REPO_MOUNT,
    CONTAINER_WORKTREE_MOUNT,
    ContainerManager,
    IsolationError,
    WorktreeManager,
    build_container_env,
    wsl_mount_path,
)
from ador.util import CommandResult
import pytest

# DATA MODELS / TYPEDEFINITIONS


class FakeRunner:
    """
    @brief   Command runner double: records argv + kwargs, replays results.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.0
    """

    def __init__(self, *results: CommandResult) -> None:
        """
        @brief      Queue the results to replay in order.
        @param[in]  results CommandResults returned call by call.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        self.results = list(results)
        self.calls: list[list[str]] = []
        self.envs: list[dict[str, str] | None] = []

    def __call__(
        self,
        argv: list[str],
        *,
        cwd: str | Path | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        """
        @brief      Record the call and pop the next canned result.
        @param[in]  argv Command vector.
        @param[in]  cwd Ignored.
        @param[in]  timeout Recorded implicitly via kwargs when needed.
        @param[in]  env Recorded for secret-handling assertions.
        @return     The next queued CommandResult.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        self.calls.append([str(part) for part in argv])
        self.envs.append(env)
        return self.results.pop(0)


# HELPER FUNCTIONS


def _ok(stdout: str = "") -> CommandResult:
    """
    @brief      A successful canned result.
    @param[in]  stdout Canned stdout.
    @return     CommandResult with exit code 0.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    return CommandResult(exit_code=0, stdout=stdout)


def _fail(stderr: str, exit_code: int = 1) -> CommandResult:
    """
    @brief      A failing canned result.
    @param[in]  stderr Canned stderr.
    @param[in]  exit_code Non-zero exit code.
    @return     The failing CommandResult.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    return CommandResult(exit_code=exit_code, stderr=stderr)


def _manager(runner: FakeRunner) -> ContainerManager:
    """
    @brief      A ContainerManager with test wiring.
    @param[in]  runner The fake runner.
    @return     The manager (docker, test image, test volumes).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    return ContainerManager("docker", "ador-executor:latest", "uv-cache", "npm-cache", runner)


def _fake_worktree(tmp_path: Path, run_id: str, gitdir: str) -> WorktreeManager:
    """
    @brief      A WorktreeManager whose worktree exists on disk with a pointer.
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  run_id Run identifier.
    @param[in]  gitdir Content of the gitdir line in the .git pointer file.
    @return     The manager rooted in tmp_path.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", FakeRunner())
    wt = manager.path_for(run_id)
    wt.mkdir(parents=True)
    (wt / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
    return manager


# PUBLIC API / TESTS - worktrees


def test_worktree_create_new_branch(tmp_path: Path) -> None:
    """
    @brief   A fresh run gets `worktree add -b <branch> <path> <base_ref>`.
    @version 0.1.0
    """
    runner = FakeRunner(_fail("", exit_code=1), _ok())  # branch missing, add ok
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    path = manager.create("run-1", "ador/run-1", "origin/develop")
    assert path == tmp_path / "worktrees" / "run-1"
    verify_argv, add_argv = runner.calls
    assert "rev-parse" in verify_argv and "refs/heads/ador/run-1" in verify_argv
    assert add_argv[:3] == ["git", "-C", str(tmp_path / "repo")]
    assert add_argv[3:5] == ["worktree", "add"]
    assert "-b" in add_argv and "origin/develop" in add_argv


def test_worktree_create_reattaches_existing_branch(tmp_path: Path) -> None:
    """
    @brief   When the branch survives but the worktree is gone (resume after
             cleanup), the branch is re-attached without -b.
    @version 0.1.0
    """
    runner = FakeRunner(_ok("abc123"), _ok())  # branch exists, add ok
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    manager.create("run-1", "ador/run-1", "origin/develop")
    add_argv = runner.calls[1]
    assert "-b" not in add_argv
    assert "ador/run-1" in add_argv


def test_worktree_create_is_idempotent(tmp_path: Path) -> None:
    """
    @brief   An existing worktree is reused; git is not called at all.
    @version 0.1.0
    """
    manager = _fake_worktree(tmp_path, "run-1", "/repo/.git/worktrees/run-1")
    path = manager.create("run-1", "ador/run-1", "origin/develop")
    assert path == manager.path_for("run-1")
    assert manager.runner.calls == []  # type: ignore[attr-defined]


def test_worktree_create_fails_closed_on_git_error(tmp_path: Path) -> None:
    """
    @brief   A git failure raises IsolationError with command context.
    @version 0.1.0
    """
    runner = FakeRunner(_fail("", exit_code=1), _fail("fatal: base ref not found"))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(IsolationError) as excinfo:
        manager.create("run-1", "ador/run-1", "origin/nope")
    assert "base ref not found" in str(excinfo.value)


def test_worktree_remove_missing_is_not_an_error(tmp_path: Path) -> None:
    """
    @brief   Removing an already-gone worktree only prunes (idempotent).
    @version 0.1.0
    """
    runner = FakeRunner(_ok())  # prune only
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    manager.remove("run-1")
    assert len(runner.calls) == 1
    assert "prune" in runner.calls[0]


def test_worktree_remove_with_branch_delete(tmp_path: Path) -> None:
    """
    @brief   Terminal cleanup removes the worktree, prunes, and deletes the
             branch only when asked.
    @version 0.1.0
    """
    manager = _fake_worktree(tmp_path, "run-1", "/repo/.git/worktrees/run-1")
    runner = FakeRunner(_ok(), _ok(), _ok("abc"), _ok())  # remove, prune, verify, -D
    manager.runner = runner
    manager.remove("run-1", delete_branch="ador/run-1")
    assert runner.calls[0][3:6] == ["worktree", "remove", "--force"]
    assert "prune" in runner.calls[1]
    assert "-D" in runner.calls[3] and "ador/run-1" in runner.calls[3]


def test_worktree_admin_dir_name_reads_pointer(tmp_path: Path) -> None:
    """
    @brief   The admin dir name comes from the .git pointer file, so a
             collision-suffixed name is picked up correctly.
    @version 0.1.0
    """
    manager = _fake_worktree(tmp_path, "run-1", "D:/repos/x/.git/worktrees/run-11")
    assert manager.admin_dir_name("run-1") == "run-11"


def test_worktree_admin_dir_name_fails_closed(tmp_path: Path) -> None:
    """
    @brief   A missing or malformed pointer file raises IsolationError.
    @version 0.1.0
    """
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", FakeRunner())
    with pytest.raises(IsolationError):
        manager.admin_dir_name("absent-run")
    broken = _fake_worktree(tmp_path, "run-2", "x")
    (broken.path_for("run-2") / ".git").write_text("no gitdir here\n", encoding="utf-8")
    with pytest.raises(IsolationError):
        broken.admin_dir_name("run-2")


# PUBLIC API / TESTS - container env


def test_build_container_env_targets_the_mounts() -> None:
    """
    @brief   GIT_DIR/GIT_WORK_TREE point into the fixed container mounts and
             the bot identity fills the author fields.
    @version 0.1.0
    """
    env = build_container_env("run-1", "ADOR", "ador-bot@local")
    assert env["HOME"] == "/home/ador"  # force correct home over daemon leak
    assert env["GIT_DIR"] == f"{CONTAINER_REPO_MOUNT}/.git/worktrees/run-1"
    assert env["GIT_WORK_TREE"] == CONTAINER_WORKTREE_MOUNT
    assert env["GIT_AUTHOR_NAME"] == "ADOR"
    assert env["GIT_COMMITTER_EMAIL"] == "ador-bot@local"


# PUBLIC API / TESTS - containers


def test_container_provision_creates_when_absent(tmp_path: Path) -> None:
    """
    @brief   An absent container is created with all four mounts, workdir,
             env keys (values via process env, never argv), and sleep
             infinity; the io dir is created on demand.
    @version 0.1.1
    """
    runner = FakeRunner(_fail("Error: No such object: ador-run-x"), _ok("cid"))
    manager = _manager(runner)
    io_dir = tmp_path / "state" / "runs" / "x" / "io"
    manager.provision(
        "ador-run-x",
        tmp_path / "repo",
        tmp_path / "worktrees" / "x",
        io_dir,
        {"HOME": "/home/ador", "GIT_DIR": "/ador/repo/.git/worktrees/x",
         "ANTHROPIC_API_KEY": "sk-secret"},
    )
    run_argv = runner.calls[1]
    assert run_argv[:3] == ["docker", "run", "--detach"]
    # HOME travels inline (not a secret; WSL login shells reset a bare HOME)
    env_values = [run_argv[i + 1] for i, part in enumerate(run_argv[:-1])
                  if part == "--env"]
    assert "HOME=/home/ador" in env_values
    assert "HOME" not in env_values  # bare key would take the WSL user's HOME
    assert f"{(tmp_path / 'repo').as_posix()}:{CONTAINER_REPO_MOUNT}" in run_argv
    assert f"{io_dir.as_posix()}:{CONTAINER_IO_MOUNT}" in run_argv
    assert io_dir.is_dir()  # created on demand
    assert "uv-cache:/home/ador/.cache/uv" in run_argv
    assert "--workdir" in run_argv and CONTAINER_WORKTREE_MOUNT in run_argv
    assert run_argv[-2:] == ["sleep", "infinity"]
    # secrets: key present as bare --env KEY, value only in the process env
    assert "ANTHROPIC_API_KEY" in run_argv
    assert not any("sk-secret" in part for part in run_argv)
    assert runner.envs[1] is not None
    assert runner.envs[1]["ANTHROPIC_API_KEY"] == "sk-secret"


def test_container_provision_inserts_run_args(tmp_path: Path) -> None:
    """
    @brief   [container] run_args tokens land right after `run --detach`
             (e.g. --userns=keep-id for rootless podman - live finding
             2026-07-04). The default (no run_args) is proven clean by
             test_container_provision_creates_when_absent's argv prefix.
    @version 0.1.0
    """
    runner = FakeRunner(_fail("Error: No such object: p-run-x"), _ok("cid"))
    manager = ContainerManager("podman", "ador-executor:latest", "uv-cache",
                               "npm-cache", runner,
                               run_args=["--userns=keep-id"])
    manager.provision("p-run-x", tmp_path / "repo", tmp_path / "wt",
                      tmp_path / "io", {"HOME": "/home/ador"})
    run_argv = runner.calls[1]
    assert run_argv[:4] == ["podman", "run", "--detach", "--userns=keep-id"]
    assert run_argv[4:6] == ["--name", "p-run-x"]


def test_container_provision_is_idempotent(tmp_path: Path) -> None:
    """
    @brief   running -> no-op; exited -> start (keep-warm resume).
    @version 0.1.1
    """
    running = FakeRunner(_ok("running\n"))
    _manager(running).provision("c", "r", "w", tmp_path / "io", {})
    assert len(running.calls) == 1  # inspect only

    exited = FakeRunner(_ok("exited\n"), _ok())
    _manager(exited).provision("c", "r", "w", tmp_path / "io", {})
    assert exited.calls[1][:2] == ["docker", "start"]


def test_container_status_absent_vs_error() -> None:
    """
    @brief   "No such container" maps to absent; other failures raise.
    @version 0.1.0
    """
    assert _manager(FakeRunner(_fail("Error: No such container: c"))).status("c") == "absent"
    with pytest.raises(IsolationError):
        _manager(FakeRunner(_fail("Cannot connect to the Docker daemon"))).status("c")


def test_container_stop_remove_idempotent_but_fail_closed() -> None:
    """
    @brief   stop/remove of an absent container is fine; a real failure on an
             existing container raises.
    @version 0.1.0
    """
    gone = FakeRunner(_fail("No such container: c"), _fail("No such container: c"))
    _manager(gone).stop("c")  # stop fails -> status says absent -> ok

    stuck = FakeRunner(_fail("permission denied"), _ok("running\n"))
    with pytest.raises(IsolationError):
        _manager(stuck).remove("c")


def test_container_ensure_volumes_and_failure() -> None:
    """
    @brief   Both cache volumes are created; a runtime failure raises.
    @version 0.1.0
    """
    runner = FakeRunner(_ok(), _ok())
    _manager(runner).ensure_volumes()
    assert runner.calls[0] == ["docker", "volume", "create", "uv-cache"]
    assert runner.calls[1] == ["docker", "volume", "create", "npm-cache"]
    with pytest.raises(IsolationError):
        _manager(FakeRunner(_fail("daemon down"))).ensure_volumes()


def test_container_exec_returns_result_as_data() -> None:
    """
    @brief   exec passes the exit code through as data - a failing gate
             command is a conductor signal, not an isolation error.
    @version 0.1.0
    """
    runner = FakeRunner(_fail("gate failed", exit_code=3))
    result = _manager(runner).exec("c", ["opencode", "run", "prompt"])
    assert result.exit_code == 3
    assert runner.calls[0][:3] == ["docker", "exec", "c"]


def test_worktree_relative_root_resolves_against_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief   A relative worktrees root becomes absolute at construction:
             `git -C <repo>` resolves relative paths against the REPO, which
             scattered worktrees into the target repository (pilot finding
             2026-07-03).
    @version 0.1.0
    """
    monkeypatch.chdir(tmp_path)
    runner = FakeRunner(_fail("", exit_code=1), _ok())
    manager = WorktreeManager("repo", "wt-root", runner)
    assert manager.root.is_absolute()
    manager.create("r1", "ador/r1", "HEAD")
    add_argv = runner.calls[1]
    assert str(tmp_path / "wt-root" / "r1") in add_argv
    assert "wt-root/r1" not in add_argv and "wt-root\\r1" not in add_argv


def test_container_mount_sources_are_always_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief   Relative mount sources are resolved before hitting docker - a
             bare relative source would be read as a NAMED VOLUME and mount
             an empty volume over the worktree.
    @version 0.1.0
    """
    monkeypatch.chdir(tmp_path)
    runner = FakeRunner(_fail("No such container"), _ok("cid"))
    _manager(runner).provision("c", "repo", "wt", ".ador/runs/x/io", {})
    run_argv = runner.calls[1]
    assert f"{(tmp_path / 'repo').as_posix()}:{CONTAINER_REPO_MOUNT}" in run_argv
    assert f"{(tmp_path / '.ador/runs/x/io').as_posix()}:{CONTAINER_IO_MOUNT}" in run_argv
    assert not any(part.startswith(".ador") for part in run_argv)


# PUBLIC API / TESTS - WSL-wrapped runtime


def _wsl_manager(runner: FakeRunner) -> ContainerManager:
    """
    @brief      A ContainerManager driving Docker Engine inside WSL2.
    @param[in]  runner The fake runner.
    @return     The manager with a wrapped runtime command.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    return ContainerManager(
        "wsl -d Ubuntu-24.04 -- docker",
        "ador-executor:latest",
        "uv-cache",
        "npm-cache",
        runner,
    )


def test_wsl_mount_path_translates_drive_letters() -> None:
    """
    @brief   Windows paths become /mnt/<drive>/ paths; POSIX paths pass
             through unchanged.
    @version 0.1.0
    """
    assert wsl_mount_path(r"D:\TEMP\ador\worktrees\run-1") == "/mnt/d/TEMP/ador/worktrees/run-1"
    assert wsl_mount_path("C:/Users/x") == "/mnt/c/Users/x"
    assert wsl_mount_path("/already/posix") == "/already/posix"


def test_wsl_runtime_prefixes_every_command() -> None:
    """
    @brief   A wrapped runtime string is split and prefixed onto the argv.
    @version 0.1.0
    """
    runner = FakeRunner(_ok("running\n"))
    manager = _wsl_manager(runner)
    assert manager.wsl_mode is True
    assert manager.status("c") == "running"
    assert runner.calls[0][:5] == ["wsl", "-d", "Ubuntu-24.04", "--", "docker"]
    assert runner.calls[0][5] == "inspect"


def test_wsl_provision_translates_mounts_and_sets_wslenv(tmp_path: Path) -> None:
    """
    @brief   In WSL mode mount sources are /mnt/<drive>/ paths and env keys
             are listed in WSLENV so the values cross the WSL boundary;
             values still never appear in argv.
    @version 0.1.1
    """
    runner = FakeRunner(_fail("No such container"), _ok("cid"))
    manager = _wsl_manager(runner)
    io_dir = tmp_path / "io"
    manager.provision(
        "ador-run-x",
        r"D:\repos\cockpit",
        r"D:\ador\worktrees\x",
        io_dir,
        {"GIT_DIR": "/ador/repo/.git/worktrees/x", "ANTHROPIC_API_KEY": "sk-secret"},
    )
    run_argv = runner.calls[1]
    assert f"/mnt/d/repos/cockpit:{CONTAINER_REPO_MOUNT}" in run_argv
    assert f"/mnt/d/ador/worktrees/x:{CONTAINER_WORKTREE_MOUNT}" in run_argv
    assert f"{wsl_mount_path(io_dir)}:{CONTAINER_IO_MOUNT}" in run_argv
    assert not any("sk-secret" in part for part in run_argv)
    process_env = runner.envs[1]
    assert process_env is not None
    assert "GIT_DIR" in process_env["WSLENV"]
    assert "ANTHROPIC_API_KEY" in process_env["WSLENV"]
    assert "HOME" not in process_env["WSLENV"]  # WSL login resets HOME


def test_plain_docker_runtime_does_not_set_wslenv(tmp_path: Path) -> None:
    """
    @brief   Outside WSL mode, WSLENV is left exactly as the host had it.
    @version 0.1.1
    """
    runner = FakeRunner(_fail("No such container"), _ok("cid"))
    _manager(runner).provision("c", tmp_path, tmp_path, tmp_path / "io", {"K": "v"})
    process_env = runner.envs[1]
    assert process_env is not None
    assert process_env.get("WSLENV", "") == os.environ.get("WSLENV", "")


# END OF FILE
