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
@version 0.4.0
"""

from __future__ import annotations

# IMPORTS
import os
from pathlib import Path

from adore.config import ContainerEgressConfig
from adore.isolation import (
    CONTAINER_IO_MOUNT,
    CONTAINER_REPO_MOUNT,
    CONTAINER_WORKTREE_MOUNT,
    ContainerManager,
    IsolationError,
    WorktreeManager,
    build_container_env,
    wsl_mount_path,
)
from adore.util import CommandResult
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
    @version    0.1.2
    """
    return ContainerManager("docker", "adore-executor-base:1.0.0", "uv-cache",
                            "npm-cache", runner)


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
    @version 0.1.2
    """
    runner = FakeRunner(_fail("", exit_code=1), _ok())  # branch missing, add ok
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    path = manager.create("run-1", "adore/run-1", "origin/develop")
    assert path == tmp_path / "worktrees" / "run-1"
    verify_argv, add_argv = runner.calls
    assert "rev-parse" in verify_argv and "refs/heads/adore/run-1" in verify_argv
    assert add_argv[:3] == ["git", "-C", str(tmp_path / "repo")]
    assert add_argv[3:5] == ["worktree", "add"]
    assert "-b" in add_argv and "origin/develop" in add_argv


def test_worktree_create_reattaches_existing_branch(tmp_path: Path) -> None:
    """
    @brief   When the branch survives but the worktree is gone (resume after
             cleanup), the branch is re-attached without -b.
    @version 0.1.1
    """
    runner = FakeRunner(_ok("abc123"), _ok())  # branch exists, add ok
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    manager.create("run-1", "adore/run-1", "origin/develop")
    add_argv = runner.calls[1]
    assert "-b" not in add_argv
    assert "adore/run-1" in add_argv


def test_worktree_create_is_idempotent(tmp_path: Path) -> None:
    """
    @brief   An existing worktree is reused; git is not called at all.
    @version 0.1.1
    """
    manager = _fake_worktree(tmp_path, "run-1", "/repo/.git/worktrees/run-1")
    path = manager.create("run-1", "adore/run-1", "origin/develop")
    assert path == manager.path_for("run-1")
    assert manager.runner.calls == []  # type: ignore[attr-defined]


def test_worktree_create_fails_closed_on_git_error(tmp_path: Path) -> None:
    """
    @brief   A git failure raises IsolationError with command context.
    @version 0.1.1
    """
    runner = FakeRunner(_fail("", exit_code=1), _fail("fatal: base ref not found"))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(IsolationError) as excinfo:
        manager.create("run-1", "adore/run-1", "origin/nope")
    assert "base ref not found" in str(excinfo.value)


def test_changed_files_counts_renames_and_quoted_paths_once(tmp_path: Path) -> None:
    """
    @brief   The files-touched budget counts a rename as ONE file (its
             destination), strips git's quotes, and de-dups paths appearing in
             both the committed diff and the pending status.
    @version 0.1.0
    """
    committed = _ok("src/a.py\nsrc/b.py\n")
    pending = _ok('R  old.py -> src/new.py\n M src/a.py\n?? "weird name.py"\n')
    runner = FakeRunner(committed, pending)
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    # src/a.py (both sides), src/b.py, src/new.py (rename dest), weird name.py
    assert manager.changed_files("run-1", "origin/develop") == 4


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
    @version 0.1.1
    """
    manager = _fake_worktree(tmp_path, "run-1", "/repo/.git/worktrees/run-1")
    runner = FakeRunner(_ok(), _ok(), _ok("abc"), _ok())  # remove, prune, verify, -D
    manager.runner = runner
    manager.remove("run-1", delete_branch="adore/run-1")
    assert runner.calls[0][3:6] == ["worktree", "remove", "--force"]
    assert "prune" in runner.calls[1]
    assert "-D" in runner.calls[3] and "adore/run-1" in runner.calls[3]


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
    @brief   GIT_DIR/GIT_COMMON_DIR/GIT_WORK_TREE point into the fixed
             container mounts and the bot identity fills the author fields.
    @version 0.1.1
    """
    env = build_container_env("run-1", "ADORE", "adore-bot@local")
    assert env["HOME"] == "/home/adore"  # force correct home over daemon leak
    assert env["GIT_DIR"] == f"{CONTAINER_REPO_MOUNT}/.git/worktrees/run-1"
    assert env["GIT_COMMON_DIR"] == f"{CONTAINER_REPO_MOUNT}/.git"
    assert env["GIT_WORK_TREE"] == CONTAINER_WORKTREE_MOUNT
    assert env["GIT_AUTHOR_NAME"] == "ADORE"
    assert env["GIT_COMMITTER_EMAIL"] == "adore-bot@local"


def test_scrub_container_worktree_config_only_removes_adore_mount(tmp_path: Path) -> None:
    """
    @brief   If a container git command persists `/adore/work` into the host
             repo config, ADORE scrubs that host-breaking value only.
    @version 0.1.0
    """
    repo = tmp_path / "repo"
    git_dir = repo / ".git"
    git_dir.mkdir(parents=True)
    config_path = git_dir / "config"
    config_path.write_text(
        "[core]\n"
        "\trepositoryformatversion = 0\n"
        "\tworktree = /adore/work\n"
        "\tbare = false\n"
        "[remote \"origin\"]\n"
        "\turl = git@example/repo.git\n",
        encoding="utf-8",
    )
    manager = WorktreeManager(repo, tmp_path / "worktrees", FakeRunner())
    manager.scrub_container_worktree_config()
    scrubbed = config_path.read_text(encoding="utf-8")
    assert "worktree = /adore/work" not in scrubbed
    assert "repositoryformatversion = 0" in scrubbed
    assert "url = git@example/repo.git" in scrubbed

    config_path.write_text("[core]\n\tworktree = D:/repo\n", encoding="utf-8")
    manager.scrub_container_worktree_config()
    assert "worktree = D:/repo" in config_path.read_text(encoding="utf-8")


# PUBLIC API / TESTS - containers


def test_container_provision_creates_when_absent(tmp_path: Path) -> None:
    """
    @brief   An absent container is created with all four mounts, workdir,
             safe runtime env inline, secret keys without values, and sleep
             infinity; the io dir is created on demand.
    @version 0.1.3
    """
    runner = FakeRunner(_fail("Error: No such object: adore-run-x"), _ok("cid"))
    manager = _manager(runner)
    io_dir = tmp_path / "state" / "runs" / "x" / "io"
    manager.provision(
        "adore-run-x",
        tmp_path / "repo",
        tmp_path / "worktrees" / "x",
        io_dir,
        {"HOME": "/home/adore", "GIT_DIR": "/adore/repo/.git/worktrees/x",
         "CODEX_HOME": "/home/adore/.adore-codex", "UV_LINK_MODE": "copy",
         "ANTHROPIC_API_KEY": "sk-secret"},
    )
    run_argv = runner.calls[1]
    assert run_argv[:3] == ["docker", "run", "--detach"]
    # Safe runtime values travel inline; they are not secrets and must survive
    # wrapped runtimes consistently.
    env_values = [run_argv[i + 1] for i, part in enumerate(run_argv[:-1])
                  if part == "--env"]
    assert "HOME=/home/adore" in env_values
    assert "GIT_DIR=/adore/repo/.git/worktrees/x" in env_values
    assert "CODEX_HOME=/home/adore/.adore-codex" in env_values
    assert "UV_LINK_MODE=copy" in env_values
    assert "HOME" not in env_values  # bare key would take the WSL user's HOME
    assert f"{(tmp_path / 'repo').as_posix()}:{CONTAINER_REPO_MOUNT}" in run_argv
    assert f"{io_dir.as_posix()}:{CONTAINER_IO_MOUNT}" in run_argv
    assert io_dir.is_dir()  # created on demand
    assert "uv-cache:/home/adore/.cache/uv" in run_argv
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
    @version 0.1.1
    """
    runner = FakeRunner(_fail("Error: No such object: p-run-x"), _ok("cid"))
    manager = ContainerManager("podman", "adore-executor-base:1.0.0", "uv-cache",
                               "npm-cache", runner,
                               run_args=["--userns=keep-id"])
    manager.provision("p-run-x", tmp_path / "repo", tmp_path / "wt",
                      tmp_path / "io", {"HOME": "/home/adore"})
    run_argv = runner.calls[1]
    assert run_argv[:4] == ["podman", "run", "--detach", "--userns=keep-id"]
    assert run_argv[4:6] == ["--name", "p-run-x"]


def test_container_provision_none_uses_no_network(tmp_path: Path) -> None:
    """
    @brief   [container.egress] mode none starts the executor with
             --network none and injects no proxy variables.
    @version 0.1.1
    """
    runner = FakeRunner(_fail("No such container"), _ok("cid"))
    manager = ContainerManager(
        "docker",
        "adore-executor-base:1.0.0",
        "uv-cache",
        "npm-cache",
        runner,
        egress=ContainerEgressConfig(mode="none"),
    )
    manager.provision("adore-run-x", tmp_path / "repo", tmp_path / "wt",
                      tmp_path / "io", {"HOME": "/home/adore"})
    run_argv = runner.calls[1]
    network_index = run_argv.index("--network")
    assert run_argv[network_index + 1] == "none"
    assert not any("HTTP_PROXY" in part for part in run_argv)


def test_container_provision_allowlist_proxy_lifecycle(tmp_path: Path) -> None:
    """
    @brief   allowlist-proxy creates the internal network, starts the proxy,
             connects it with the alias, and starts the executor on that
             network with proxy env inline.
    @version 0.1.1
    """
    runner = FakeRunner(
        _fail("No such container: adore-run-x"),
        _ok("network"),
        _fail("No such container: adore-run-x-egress-proxy"),
        _ok("proxy"),
        _ok(),
        _ok("cid"),
    )
    manager = ContainerManager(
        "docker",
        "adore-executor-base:1.0.0",
        "uv-cache",
        "npm-cache",
        runner,
        egress=ContainerEgressConfig(
            mode="allowlist-proxy",
            allowlist=["api.openai.com", "*.pythonhosted.org"],
        ),
    )
    io_dir = tmp_path / "io"
    manager.provision("adore-run-x", tmp_path / "repo", tmp_path / "wt",
                      io_dir, {"HOME": "/home/adore"})

    assert runner.calls[1] == [
        "docker", "network", "create", "--internal", "adore-egress-adore-run-x",
    ]
    proxy_run = runner.calls[3]
    assert proxy_run[:5] == ["docker", "run", "--detach", "--name",
                             "adore-run-x-egress-proxy"]
    assert "adore-egress-proxy:1.0.0" in proxy_run
    proxy_config = io_dir / "egress-proxy" / "squid.conf"
    proxy_config_text = proxy_config.read_text(encoding="utf-8")
    assert "api.openai.com" in proxy_config_text
    assert ".pythonhosted.org" in proxy_config_text
    assert "access_log stdio:/var/log/squid/access.log" in proxy_config_text
    assert "cache_log /var/log/squid/cache.log" in proxy_config_text
    assert "/dev/stdout" not in proxy_config_text
    assert "/dev/stderr" not in proxy_config_text

    assert runner.calls[4] == [
        "docker", "network", "connect", "--alias", "adore-egress-proxy",
        "adore-egress-adore-run-x", "adore-run-x-egress-proxy",
    ]
    executor_run = runner.calls[5]
    network_index = executor_run.index("--network")
    assert executor_run[network_index + 1] == "adore-egress-adore-run-x"
    env_values = [executor_run[i + 1] for i, part in enumerate(executor_run[:-1])
                  if part == "--env"]
    assert "HTTP_PROXY=http://adore-egress-proxy:3128" in env_values
    assert "NO_PROXY=localhost,127.0.0.1,::1" in env_values


def test_container_provision_allowlist_proxy_failure_raises(tmp_path: Path) -> None:
    """
    @brief   Proxy network/runtime failures fail closed with IsolationError.
    @version 0.1.1
    """
    runner = FakeRunner(_fail("No such container: adore-run-x"), _fail("daemon down"))
    manager = ContainerManager(
        "docker",
        "adore-executor-base:1.0.0",
        "uv-cache",
        "npm-cache",
        runner,
        egress=ContainerEgressConfig(mode="allowlist-proxy", allowlist=["example.com"]),
    )
    with pytest.raises(IsolationError):
        manager.provision("adore-run-x", tmp_path / "repo", tmp_path / "wt",
                          tmp_path / "io", {})


def test_container_remove_allowlist_proxy_removes_proxy_and_network() -> None:
    """
    @brief   Terminal cleanup removes executor, per-run proxy, and egress
             network in proxy mode.
    @version 0.1.1
    """
    runner = FakeRunner(_ok(), _ok(), _ok())
    manager = ContainerManager(
        "docker",
        "adore-executor-base:1.0.0",
        "uv-cache",
        "npm-cache",
        runner,
        egress=ContainerEgressConfig(mode="allowlist-proxy", allowlist=["example.com"]),
    )
    manager.remove("adore-run-x")
    assert runner.calls == [
        ["docker", "rm", "--force", "adore-run-x"],
        ["docker", "rm", "--force", "adore-run-x-egress-proxy"],
        ["docker", "network", "rm", "adore-egress-adore-run-x"],
    ]


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


def test_container_ensure_volumes_tolerates_existing_volume() -> None:
    """
    @brief   podman errors when a cache volume already exists (docker is
             silent); an existing volume is the success case, so that error
             is swallowed while an unrelated failure still raises.
    @version 0.1.0
    """
    exists = _fail(
        "Error: volume with name uv-cache already exists: volume already exists",
        exit_code=125,
    )
    runner = FakeRunner(exists, _ok())  # uv exists, npm created fresh
    _manager(runner).ensure_volumes()  # must not raise
    assert len(runner.calls) == 2
    with pytest.raises(IsolationError):  # a different error is NOT tolerated
        _manager(FakeRunner(_fail("permission denied"))).ensure_volumes()


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


def test_container_exec_passes_safe_env_inline_and_secret_env_bare() -> None:
    """
    @brief   Exec-time env mirrors provision: CODEX_HOME is inline so Podman
             exec sees it; secret values stay out of argv.
    @version 0.1.1
    """
    runner = FakeRunner(_ok())
    _manager(runner).exec(
        "c",
        ["env"],
        env={"CODEX_HOME": "/home/adore/.adore-codex", "UV_LINK_MODE": "copy",
             "OPENAI_API_KEY": "sk-secret"},
    )
    argv = runner.calls[0]
    assert argv[:2] == ["docker", "exec"]
    assert "CODEX_HOME=/home/adore/.adore-codex" in argv
    assert "UV_LINK_MODE=copy" in argv
    assert "OPENAI_API_KEY" in argv
    assert not any("sk-secret" in part for part in argv)
    assert argv[-2:] == ["c", "env"]
    assert runner.envs[0] is not None
    assert runner.envs[0]["OPENAI_API_KEY"] == "sk-secret"


def test_container_verify_required_tools_execs_checks() -> None:
    """
    @brief   Required project-image tool checks are parsed without a shell and
             executed inside the container with the provision env.
    @version 0.1.0
    """
    runner = FakeRunner(_ok(), _ok())
    _manager(runner).verify_required_tools(
        "c",
        ["make --version", "terraform --version"],
        env={"UV_LINK_MODE": "copy"},
    )
    assert runner.calls[0] == [
        "docker", "exec", "--env", "UV_LINK_MODE=copy", "c", "make", "--version",
    ]
    assert runner.calls[1] == [
        "docker", "exec", "--env", "UV_LINK_MODE=copy", "c", "terraform", "--version",
    ]


def test_container_verify_required_tools_fails_closed() -> None:
    """
    @brief   Malformed checks and non-zero exits raise IsolationError with
             command context.
    @version 0.1.0
    """
    with pytest.raises(IsolationError):
        _manager(FakeRunner()).verify_required_tools("c", ['"unterminated'])
    with pytest.raises(IsolationError) as excinfo:
        _manager(FakeRunner(_fail("terraform: not found"))).verify_required_tools(
            "c", ["terraform --version"]
        )
    assert "terraform --version" in str(excinfo.value)
    assert "not found" in str(excinfo.value)


def test_worktree_relative_root_resolves_against_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief   A relative worktrees root becomes absolute at construction:
             `git -C <repo>` resolves relative paths against the REPO, which
             scattered worktrees into the target repository (pilot finding
             2026-07-03).
    @version 0.1.1
    """
    monkeypatch.chdir(tmp_path)
    runner = FakeRunner(_fail("", exit_code=1), _ok())
    manager = WorktreeManager("repo", "wt-root", runner)
    assert manager.root.is_absolute()
    manager.create("r1", "adore/r1", "HEAD")
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
    @version 0.1.1
    """
    monkeypatch.chdir(tmp_path)
    runner = FakeRunner(_fail("No such container"), _ok("cid"))
    _manager(runner).provision("c", "repo", "wt", ".adore/runs/x/io", {})
    run_argv = runner.calls[1]
    assert f"{(tmp_path / 'repo').as_posix()}:{CONTAINER_REPO_MOUNT}" in run_argv
    assert f"{(tmp_path / '.adore/runs/x/io').as_posix()}:{CONTAINER_IO_MOUNT}" in run_argv
    assert not any(part.startswith(".adore") for part in run_argv)


# PUBLIC API / TESTS - WSL-wrapped runtime


def _wsl_manager(runner: FakeRunner) -> ContainerManager:
    """
    @brief      A ContainerManager driving Docker Engine inside WSL2.
    @param[in]  runner The fake runner.
    @return     The manager with a wrapped runtime command.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.1
    """
    return ContainerManager(
        "wsl -d Ubuntu-24.04 -- docker",
        "adore-executor-base:1.0.0",
        "uv-cache",
        "npm-cache",
        runner,
    )


def test_wsl_mount_path_translates_drive_letters() -> None:
    """
    @brief   Windows paths become /mnt/<drive>/ paths; POSIX paths pass
             through unchanged.
    @version 0.1.1
    """
    assert wsl_mount_path(r"D:\TEMP\adore\worktrees\run-1") == "/mnt/d/TEMP/adore/worktrees/run-1"
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
    @brief   In WSL mode mount sources are /mnt/<drive>/ paths; safe runtime
             env values are inline, while secret env values cross via WSLENV.
    @version 0.1.3
    """
    runner = FakeRunner(_fail("No such container"), _ok("cid"))
    manager = _wsl_manager(runner)
    io_dir = tmp_path / "io"
    manager.provision(
        "adore-run-x",
        r"D:\repos\runtime-project",
        r"D:\adore\worktrees\x",
        io_dir,
        {"GIT_DIR": "/adore/repo/.git/worktrees/x", "ANTHROPIC_API_KEY": "sk-secret"},
    )
    run_argv = runner.calls[1]
    assert f"/mnt/d/repos/runtime-project:{CONTAINER_REPO_MOUNT}" in run_argv
    assert f"/mnt/d/adore/worktrees/x:{CONTAINER_WORKTREE_MOUNT}" in run_argv
    assert f"{wsl_mount_path(io_dir)}:{CONTAINER_IO_MOUNT}" in run_argv
    env_values = [run_argv[i + 1] for i, part in enumerate(run_argv[:-1])
                  if part == "--env"]
    assert "GIT_DIR=/adore/repo/.git/worktrees/x" in env_values
    assert not any("sk-secret" in part for part in run_argv)
    process_env = runner.envs[1]
    assert process_env is not None
    assert "GIT_DIR" not in process_env["WSLENV"]
    assert "ANTHROPIC_API_KEY" in process_env["WSLENV"]
    assert "HOME" not in process_env["WSLENV"]  # WSL login resets HOME


def test_wsl_allowlist_proxy_prefixes_network_commands(tmp_path: Path) -> None:
    """
    @brief   WSL-wrapped runtimes prefix proxy network/create/connect and
             executor run commands consistently.
    @version 0.1.1
    """
    runner = FakeRunner(
        _fail("No such container: adore-run-x"),
        _ok("network"),
        _fail("No such container: adore-run-x-egress-proxy"),
        _ok("proxy"),
        _ok(),
        _ok("cid"),
    )
    manager = ContainerManager(
        "wsl -d Ubuntu-24.04 -- docker",
        "adore-executor-base:1.0.0",
        "uv-cache",
        "npm-cache",
        runner,
        egress=ContainerEgressConfig(mode="allowlist-proxy", allowlist=["example.com"]),
    )
    manager.provision("adore-run-x", r"D:\repo", r"D:\wt", tmp_path / "io", {})
    for call in runner.calls:
        assert call[:5] == ["wsl", "-d", "Ubuntu-24.04", "--", "docker"]
    assert runner.calls[1][5:8] == ["network", "create", "--internal"]
    assert runner.calls[4][5:8] == ["network", "connect", "--alias"]
    assert runner.calls[5][5:7] == ["run", "--detach"]


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
