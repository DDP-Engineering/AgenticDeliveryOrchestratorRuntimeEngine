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
"""

from __future__ import annotations

# IMPORTS
import hashlib
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

from adore.config import EgressPolicy
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
from adore.util import DEFAULT_COMMAND_TIMEOUT, CommandResult
import pytest

# DATA MODELS / TYPEDEFINITIONS


class FakeRunner:
    """
    @brief   Command runner double: records argv + kwargs, replays results.
    @details The `timeout` default mirrors the real `run_command`, not the
             looser `CommandRunner` protocol, so a recorded `None` means a
             caller explicitly asked for an UNBOUNDED subprocess rather than
             simply omitting the keyword. That distinction is what the
             no-unbounded-exec regression test asserts on.
    """

    def __init__(self, *results: CommandResult) -> None:
        """
        @brief      Queue the results to replay in order.
        @param[in]  results CommandResults returned call by call.
        """
        self.results = list(results)
        self.calls: list[list[str]] = []
        self.envs: list[dict[str, str] | None] = []
        self.timeouts: list[float | None] = []

    def __call__(
        self,
        argv: list[str],
        *,
        cwd: str | Path | None = None,
        timeout: float | None = DEFAULT_COMMAND_TIMEOUT,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        """
        @brief      Record the call and pop the next canned result.
        @param[in]  argv Command vector.
        @param[in]  cwd Ignored.
        @param[in]  timeout Recorded; `None` means the caller forwarded an
                            explicit "no bound".
        @param[in]  env Recorded for secret-handling assertions.
        @return     The next queued CommandResult.
        """
        self.calls.append([str(part) for part in argv])
        self.envs.append(env)
        self.timeouts.append(timeout)
        return self.results.pop(0)


# HELPER FUNCTIONS


def _ok(stdout: str = "") -> CommandResult:
    """
    @brief      A successful canned result.
    @param[in]  stdout Canned stdout.
    @return     CommandResult with exit code 0.
    """
    return CommandResult(exit_code=0, stdout=stdout)


def _fail(stderr: str, exit_code: int = 1) -> CommandResult:
    """
    @brief      A failing canned result.
    @param[in]  stderr Canned stderr.
    @param[in]  exit_code Non-zero exit code.
    @return     The failing CommandResult.
    """
    return CommandResult(exit_code=exit_code, stderr=stderr)


def _manager(runner: FakeRunner) -> ContainerManager:
    """
    @brief      A ContainerManager with test wiring.
    @param[in]  runner The fake runner.
    @return     The manager (docker, test image, test volumes).
    """
    return ContainerManager("docker", "adore-executor-base:1.0.0", "uv-cache",
                            "npm-cache", runner)


def _bounded(name: str, limit: int) -> str:
    """
    @brief      Expected per-run name part for a runtime-safe executor name.
    @param[in]  name Executor container name (already runtime-safe).
    @param[in]  limit Maximum length of the part.
    @return     The name itself when it fits, else its start plus a 10-hex
                SHA-256 suffix of the full name.
    """
    if len(name) <= limit:
        return name
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:10]
    return f"{name[:limit - 11].rstrip('-._')}-{digest}"


def _provisioned_egress(tmp_path: Path, name: str) -> tuple[str, str]:
    """
    @brief      Provision one allowlist-proxy run on a fresh fake runtime.
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  name Executor container name.
    @return     (egress network, proxy container) names the runtime was given;
                the executor joins that network and the proxy is connected to it.
    """
    runner = FakeRunner(
        _fail(f"No such container: {name}"),
        _ok("network"),
        _fail("No such container: proxy"),
        _ok("proxy"),
        _ok(),
        _ok("cid"),
    )
    manager = ContainerManager(
        "docker", "adore-executor-base:1.0.0", "uv-cache", "npm-cache", runner,
        egress=EgressPolicy(mode="allowlist-proxy", allowlist=["example.com"]),
    )
    manager.provision(name, tmp_path / "repo", tmp_path / "wt", tmp_path / "io",
                      {"HOME": "/home/adore"})
    network = runner.calls[1][-1]
    proxy = runner.calls[3][4]
    executor_run = runner.calls[5]
    assert executor_run[executor_run.index("--network") + 1] == network
    assert runner.calls[4][-2:] == [network, proxy]
    return network, proxy


def _fake_worktree(tmp_path: Path, run_id: str, gitdir: str) -> WorktreeManager:
    """
    @brief      A WorktreeManager whose worktree exists on disk with a pointer.
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  run_id Run identifier.
    @param[in]  gitdir Content of the gitdir line in the .git pointer file.
    @return     The manager rooted in tmp_path.
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
    """
    manager = _fake_worktree(tmp_path, "run-1", "/repo/.git/worktrees/run-1")
    path = manager.create("run-1", "adore/run-1", "origin/develop")
    assert path == manager.path_for("run-1")
    assert manager.runner.calls == []  # type: ignore[attr-defined]


def test_worktree_create_fails_closed_on_git_error(tmp_path: Path) -> None:
    """
    @brief   A git failure raises IsolationError with command context.
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
    """
    manager = _fake_worktree(tmp_path, "run-1", "/repo/.git/worktrees/run-1")
    runner = FakeRunner(_ok(), _ok(), _ok("abc"), _ok())  # remove, prune, verify, -D
    manager.runner = runner
    manager.remove("run-1", delete_branch="adore/run-1")
    assert runner.calls[0][3:6] == ["worktree", "remove", "--force"]
    assert "prune" in runner.calls[1]
    assert "-D" in runner.calls[3] and "adore/run-1" in runner.calls[3]


def test_worktree_remove_retries_past_the_wsl_bind_mount_race(tmp_path: Path) -> None:
    """
    @brief   Removal that transiently fails with the WSL mount-race signature
             (ENOSYS) is retried with backoff until it succeeds - no husk
             left, no manual cleanup needed (ADORE-ARCH-009: this retry now
             lives here, not in the orchestrator's core loop).
    """
    manager = _fake_worktree(tmp_path, "run-1", "/repo/.git/worktrees/run-1")
    enosys = _fail("failed to delete '...': Function not implemented")
    runner = FakeRunner(enosys, enosys, _ok(), _ok())  # clears on the 3rd attempt
    manager.runner = runner
    sleeps: list[float] = []
    manager.sleep = sleeps.append

    manager.remove("run-1")

    assert len(runner.calls) == 4                 # 2 failed + (remove, prune)
    assert runner.calls[2][3:6] == ["worktree", "remove", "--force"]
    assert "prune" in runner.calls[3]
    assert sleeps == [1.0, 2.0]                   # two backoff waits


def test_worktree_remove_does_not_retry_a_real_error(tmp_path: Path) -> None:
    """
    @brief   A non-transient removal error is NOT retried (retries must not
             mask real failures) and is raised on the first attempt.
    """
    manager = _fake_worktree(tmp_path, "run-1", "/repo/.git/worktrees/run-1")
    runner = FakeRunner(_fail("fatal: not a valid object name"))
    manager.runner = runner
    sleeps: list[float] = []
    manager.sleep = sleeps.append

    with pytest.raises(IsolationError, match="not a valid object name"):
        manager.remove("run-1")

    assert len(runner.calls) == 1   # only one attempt consumed
    assert sleeps == []             # no retry on a real error


def test_worktree_admin_dir_name_reads_pointer(tmp_path: Path) -> None:
    """
    @brief   The admin dir name comes from the .git pointer file, so a
             collision-suffixed name is picked up correctly.
    """
    manager = _fake_worktree(tmp_path, "run-1", "D:/repos/x/.git/worktrees/run-11")
    assert manager.admin_dir_name("run-1") == "run-11"


def test_worktree_admin_dir_name_fails_closed(tmp_path: Path) -> None:
    """
    @brief   A missing or malformed pointer file raises IsolationError.
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
    """
    runner = FakeRunner(_fail("Error: No such object: adore-run-x"), _ok("cid"),
                        _ok("adore-git-binding-v1\n"))
    manager = _manager(runner)
    io_dir = tmp_path / "state" / "runs" / "x" / "io"
    manager.provision(
        "adore-run-x",
        tmp_path / "repo",
        tmp_path / "worktrees" / "x",
        io_dir,
        {"HOME": "/home/adore", "GIT_DIR": "/adore/repo/.git/worktrees/x",
         "PI_CODING_AGENT_DIR": "/home/adore/.adore-pi-agent", "UV_LINK_MODE": "copy",
         "ANTHROPIC_API_KEY": "sk-secret"},
    )
    run_argv = runner.calls[1]
    assert run_argv[:3] == ["docker", "run", "--detach"]
    # Safe runtime values travel inline; they are not secrets and must survive
    # wrapped runtimes consistently.
    env_values = [run_argv[i + 1] for i, part in enumerate(run_argv[:-1])
                  if part == "--env"]
    assert "HOME=/home/adore" in env_values
    assert "GIT_DIR" in env_values  # unset image defaults, not a global selector
    assert not any(value.startswith("GIT_DIR=") for value in env_values)
    assert "PI_CODING_AGENT_DIR=/home/adore/.adore-pi-agent" in env_values
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


def test_container_provision_relabels_only_bind_mounts_for_selinux(
    tmp_path: Path,
) -> None:
    """
    @brief   selinux_relabel="shared" appends `z` to the three HOST bind
             mounts, so an enforcing host lets container_t read the clone,
             worktree and io dir instead of denying every stage. The named
             cache VOLUMES keep no suffix: the runtime already labels those.
             The unlabeled default is pinned by
             test_container_provision_creates_when_absent's exact mounts.
    """
    runner = FakeRunner(_fail("Error: No such object: adore-run-x"), _ok("cid"))
    manager = ContainerManager(
        "podman", "adore-executor-base:1.0.0", "uv-cache", "npm-cache", runner,
        selinux_relabel="shared",
    )
    io_dir = tmp_path / "io"
    manager.provision("adore-run-x", tmp_path / "repo", tmp_path / "wt",
                      io_dir, {"HOME": "/home/adore"})
    run_argv = runner.calls[1]
    mounts = [run_argv[index + 1] for index, part in enumerate(run_argv[:-1])
              if part == "--volume"]
    assert f"{(tmp_path / 'repo').as_posix()}:{CONTAINER_REPO_MOUNT}:z" in mounts
    assert f"{(tmp_path / 'wt').as_posix()}:{CONTAINER_WORKTREE_MOUNT}:z" in mounts
    assert f"{io_dir.as_posix()}:{CONTAINER_IO_MOUNT}:z" in mounts
    assert "uv-cache:/home/adore/.cache/uv" in mounts
    assert "npm-cache:/home/adore/.npm" in mounts


def test_container_proxy_config_mount_combines_ro_and_relabel(
    tmp_path: Path,
) -> None:
    """
    @brief   The generated squid config is a host bind mount too, so under
             selinux_relabel="shared" it carries BOTH options as `ro,z`, the
             comma form docker and podman both accept. Relabeling only the
             executor mounts would still break allowlist-proxy egress on an
             enforcing host, because squid could not read its own config.
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
        "podman", "adore-executor-base:1.0.0", "uv-cache", "npm-cache", runner,
        egress=EgressPolicy(
            mode="allowlist-proxy", allowlist=["api.openai.com"],
        ),
        selinux_relabel="shared",
    )
    io_dir = tmp_path / "io"
    manager.provision("adore-run-x", tmp_path / "repo", tmp_path / "wt",
                      io_dir, {"HOME": "/home/adore"})
    proxy_run = runner.calls[3]
    config_source = (io_dir / "egress-proxy" / "squid.conf").as_posix()
    assert f"{config_source}:/etc/squid/squid.conf:ro,z" in proxy_run


def test_container_rejects_unknown_selinux_relabel_mode() -> None:
    """
    @brief   An unknown relabel mode fails closed at construction. The private
             `Z` label is the one operators reach for by habit; accepting it
             would relabel the shared clone per container and break the next
             run, so it is refused here as well as in config validation.
    """
    with pytest.raises(ValueError, match="selinux_relabel"):
        ContainerManager("docker", "adore-executor-base:1.0.0", "uv-cache",
                         "npm-cache", FakeRunner(), selinux_relabel="Z")


def test_container_provision_none_uses_no_network(tmp_path: Path) -> None:
    """
    @brief   [container.egress] mode none starts the executor with
             --network none and injects no proxy variables.
    """
    runner = FakeRunner(_fail("No such container"), _ok("cid"))
    manager = ContainerManager(
        "docker",
        "adore-executor-base:1.0.0",
        "uv-cache",
        "npm-cache",
        runner,
        egress=EgressPolicy(mode="none"),
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
        egress=EgressPolicy(
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


def test_proxy_config_admits_names_by_domain_and_addresses_by_dst(tmp_path: Path) -> None:
    """
    @brief   Host names become a dstdomain rule, IP literals a dst rule, and
             every other destination is denied; no address means no dst rule.
    """
    manager = ContainerManager(
        "docker", "adore-executor-base:1.0.0", "uv-cache", "npm-cache", FakeRunner(),
        egress=EgressPolicy(mode="allowlist-proxy", allowlist=[
            "api.openai.com", "*.pythonhosted.org", "192.168.1.20", "::1"]),
    )
    lines = manager._write_proxy_config(tmp_path / "mixed").read_text(
        encoding="utf-8").splitlines()
    assert "acl allowed_domains dstdomain api.openai.com .pythonhosted.org" in lines
    assert "acl allowed_addresses dst 192.168.1.20 ::1" in lines
    allow = [line for line in lines if line.startswith("http_access")]
    assert allow == ["http_access allow allowed_domains",
                     "http_access allow allowed_addresses", "http_access deny all"]

    manager.egress = EgressPolicy(mode="allowlist-proxy", allowlist=["api.anthropic.com"])
    text = manager._write_proxy_config(tmp_path / "names").read_text(encoding="utf-8")
    assert "dst " not in text and "allowed_addresses" not in text
    manager.egress = EgressPolicy(mode="allowlist-proxy", allowlist=["10.0.0.5"])
    text = manager._write_proxy_config(tmp_path / "addresses").read_text(encoding="utf-8")
    assert "dstdomain" not in text and "acl allowed_addresses dst 10.0.0.5" in text


def test_proxy_gets_the_executor_host_aliases(tmp_path: Path) -> None:
    """
    @brief   The proxy container receives the --add-host options of run_args
             (both spellings) and none of the other run options.
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
        "docker", "adore-executor-base:1.0.0", "uv-cache", "npm-cache", runner,
        run_args=["--add-host=host.docker.internal:host-gateway", "--userns=keep-id",
                  "--add-host", "llm.lan:192.168.1.20"],
        egress=EgressPolicy(mode="allowlist-proxy", allowlist=["host.docker.internal"]),
    )
    manager.provision("adore-run-x", tmp_path / "repo", tmp_path / "wt",
                      tmp_path / "io", {"HOME": "/home/adore"})
    proxy_run = runner.calls[3]
    assert "--add-host=host.docker.internal:host-gateway" in proxy_run
    assert proxy_run[proxy_run.index("--add-host") + 1] == "llm.lan:192.168.1.20"
    assert "--userns=keep-id" not in proxy_run
    assert "--userns=keep-id" in runner.calls[5]


def test_disposable_probe_never_pulls_executor_or_egress_proxy(tmp_path: Path) -> None:
    """@brief A local-only probe applies the no-pull policy to both images."""
    runner = FakeRunner(
        _fail("No such container: adore-probe-x"), _ok("network"),
        _fail("No such container: adore-probe-x-egress-proxy"),
        _ok("proxy"), _ok(), _ok("cid"),
    )
    manager = ContainerManager(
        "docker", "executor:local", "uv-cache", "npm-cache", runner,
        egress=EgressPolicy(
            mode="allowlist-proxy", allowlist=["model.internal"]),
        pull_never=True,
    )
    manager.provision("adore-probe-x", tmp_path / "repo", tmp_path / "work",
                      tmp_path / "io", {})
    assert "--pull=never" in runner.calls[3]
    assert "--pull=never" in runner.calls[5]


def test_container_provision_allowlist_proxy_failure_raises(tmp_path: Path) -> None:
    """
    @brief   Proxy network/runtime failures fail closed with IsolationError.
    """
    runner = FakeRunner(_fail("No such container: adore-run-x"), _fail("daemon down"))
    manager = ContainerManager(
        "docker",
        "adore-executor-base:1.0.0",
        "uv-cache",
        "npm-cache",
        runner,
        egress=EgressPolicy(mode="allowlist-proxy", allowlist=["example.com"]),
    )
    with pytest.raises(IsolationError):
        manager.provision("adore-run-x", tmp_path / "repo", tmp_path / "wt",
                          tmp_path / "io", {})


def test_container_remove_allowlist_proxy_removes_proxy_and_network() -> None:
    """
    @brief   Terminal cleanup removes executor, per-run proxy, and egress
             network in proxy mode.
    """
    runner = FakeRunner(_ok(), _ok(), _ok())
    manager = ContainerManager(
        "docker",
        "adore-executor-base:1.0.0",
        "uv-cache",
        "npm-cache",
        runner,
        egress=EgressPolicy(mode="allowlist-proxy", allowlist=["example.com"]),
    )
    manager.remove("adore-run-x")
    assert runner.calls == [
        ["docker", "rm", "--force", "adore-run-x"],
        ["docker", "rm", "--force", "adore-run-x-egress-proxy"],
        ["docker", "network", "rm", "adore-egress-adore-run-x"],
    ]


def test_cleanup_container_sweeps_remove_only_exact_targets() -> None:
    """
    @brief   Executor/proxy sweeps remove only listed names derived from the
             targets: retained companions, untargeted names under the same
             prefix, absent targets and filter overmatch are left alone.
    """
    listing = "\n".join([
        "not-adore-run-x",
        "adore-run-active",
        "adore-run-orphan",
        "adore-run-other",
        "adore-run-active-egress-proxy",
        "adore-run-orphan-egress-proxy",
        "adore-run-other-egress-proxy",
    ])
    runner = FakeRunner(_ok(listing), _ok(), _ok(listing), _ok())
    manager = _manager(runner)
    targets = {"adore-run-orphan", "adore-run-gone"}
    retained = {"adore-run-active"}

    executors = manager.cleanup_orphan_containers("adore-run-", targets, retained)
    proxies = manager.cleanup_egress_proxies(targets, retained)

    assert executors == ["adore-run-orphan"]
    assert proxies == ["adore-run-orphan-egress-proxy"]
    assert runner.calls[2] == ["docker", "ps", "--all", "--filter", "name=-egress-proxy",
                               "--format", "{{.Names}}"]
    assert runner.calls[1] == ["docker", "rm", "--force", "adore-run-orphan"]
    assert runner.calls[3] == [
        "docker", "rm", "--force", "adore-run-orphan-egress-proxy",
    ]
    assert len(runner.calls) == 4


def test_cleanup_network_sweep_survives_allowlist_mode_change() -> None:
    """
    @brief   Open-mode cleanup still reclaims a target's networks under the
             canonical and configured prefixes and leaves every other network.
    """
    canonical = "\n".join([
        "other-adore-egress-unowned",
        "adore-egress-adore-run-active",
        "adore-egress-adore-run-orphan",
        "adore-egress-adore-run-other",
    ])
    configured = "\n".join([
        "team-egress-adore-run-orphan",
        "team-egress-adore-run-other",
    ])
    runner = FakeRunner(_ok(canonical), _ok(), _ok(configured), _ok())
    manager = ContainerManager(
        "docker",
        "adore-executor-base:1.0.0",
        "uv-cache",
        "npm-cache",
        runner,
        egress=EgressPolicy(mode="open", network_prefix="team-egress"),
    )

    removed = manager.cleanup_egress_networks(
        {"adore-run-orphan"}, {"adore-run-active"}
    )

    assert removed == ["adore-egress-adore-run-orphan", "team-egress-adore-run-orphan"]
    assert runner.calls[1] == [
        "docker", "network", "rm", "adore-egress-adore-run-orphan",
    ]
    assert runner.calls[3] == [
        "docker", "network", "rm", "team-egress-adore-run-orphan",
    ]
    assert len(runner.calls) == 4


def test_cleanup_egress_sweeps_keep_names_shared_with_retained_runs() -> None:
    """
    @brief   Old cut proxy/network names shared by a finished and a retained
             run of one long-named project are kept; the finished run's own
             per-run names go.
    """
    stem = "adore-run-gitea-dpasare-2026_Networked_Intelligent_Lab_Orchestrator-"
    done, kept = stem + "26", stem + "27"
    old_proxy = "adore-run-gitea-dpasare-2026_Networked_Intelligent-egress-proxy"
    old_network = "adore-egress-adore-run-gitea-dpasare-2026_Networked_Intellige"
    proxies_listed = [old_proxy] + [f"{_bounded(n, 50)}-egress-proxy" for n in (done, kept)]
    networks_listed = [old_network] + [f"adore-egress-{_bounded(n, 48)}" for n in (done, kept)]
    runner = FakeRunner(_ok("\n".join(proxies_listed)), _ok(),
                        _ok("\n".join(networks_listed)), _ok())
    manager = _manager(runner)

    proxies = manager.cleanup_egress_proxies({done}, {kept})
    networks = manager.cleanup_egress_networks({done}, {kept})

    assert proxies == [proxies_listed[1]]
    assert networks == [networks_listed[1]]
    assert len(runner.calls) == 4


def test_cleanup_egress_proxy_sweep_finds_proxies_of_long_slugs() -> None:
    """
    @brief   A per-run proxy whose bounded name no longer starts with a long
             slug's executor prefix is still found and removed.
    """
    executor = "examplex-digital-delivery-agent-prod-run-gitea-dpasare-alpha-9"
    proxy = "examplex-digital-delivery-agent-prod-ru-1cb1a4a1e2-egress-proxy"
    assert not proxy.startswith("examplex-digital-delivery-agent-prod-run-")
    runner = FakeRunner(_ok(f"unrelated-egress-proxy\n{proxy}"), _ok())

    assert _manager(runner).cleanup_egress_proxies({executor}, set()) == [proxy]
    assert runner.calls[1] == ["docker", "rm", "--force", proxy]


def test_allowlist_egress_names_are_unique_per_run(tmp_path: Path) -> None:
    """
    @brief   Long executor names that share their first characters (two runs of
             one project, another project) get their own bounded proxy and
             network names; a short name keeps today's names.
    """
    stem = "adore-run-gitea-dpasare-2026_Networked_Intelligent_Lab_"
    names = [stem + "Orchestrator-26", stem + "Orchestrator-27", stem + "Other-26"]

    derived = [_provisioned_egress(tmp_path / str(index), name)
               for index, name in enumerate(names)]

    assert len({network for network, _ in derived}) == 3
    assert len({proxy for _, proxy in derived}) == 3
    for name, (network, proxy) in zip(names, derived, strict=True):
        assert proxy == f"{_bounded(name, 50)}-egress-proxy" and len(proxy) <= 63
        assert network == f"adore-egress-{_bounded(name, 48)}"
        assert len(network) - len("adore-egress-") <= 48
    assert derived[0] == (
        "adore-egress-adore-run-gitea-dpasare-2026_Networke-bdeedb3462",
        "adore-run-gitea-dpasare-2026_Networked-bdeedb3462-egress-proxy",
    )
    assert _provisioned_egress(tmp_path / "short", "adore-run-x") == (
        "adore-egress-adore-run-x", "adore-run-x-egress-proxy",
    )


def test_remove_egress_removes_only_the_runs_own_proxy_and_network(tmp_path: Path) -> None:
    """@brief Reaping one long-named run leaves another run's proxy and network alone."""
    stem = "adore-run-gitea-dpasare-2026_Networked_Intelligent_Lab_Orchestrator-"
    network26, proxy26 = _provisioned_egress(tmp_path / "26", stem + "26")
    network27, proxy27 = _provisioned_egress(tmp_path / "27", stem + "27")
    runner = FakeRunner(_ok(), _ok())
    manager = ContainerManager(
        "docker", "adore-executor-base:1.0.0", "uv-cache", "npm-cache", runner,
        egress=EgressPolicy(mode="allowlist-proxy", allowlist=["example.com"]),
    )

    manager.remove_egress(stem + "26")

    assert runner.calls == [
        ["docker", "rm", "--force", proxy26],
        ["docker", "network", "rm", network26],
    ]
    assert proxy27 != proxy26 and network27 != network26


def test_cleanup_container_sweep_continues_after_one_remove_failure() -> None:
    """@brief One orphan removal failure does not block later cleanup work."""
    runner = FakeRunner(
        _ok("adore-run-stuck\nadore-run-removable\n"),
        _fail("permission denied"),
        _ok("running"),
        _ok(),
    )

    removed = _manager(runner).cleanup_orphan_containers(
        "adore-run-", {"adore-run-stuck", "adore-run-removable"}, set()
    )

    assert removed == ["adore-run-removable"]


def test_container_provision_is_idempotent(tmp_path: Path) -> None:
    """
    @brief   running -> no-op; exited -> start (keep-warm resume).
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
    """
    assert _manager(FakeRunner(_fail("Error: No such container: c"))).status("c") == "absent"
    with pytest.raises(IsolationError):
        _manager(FakeRunner(_fail("Cannot connect to the Docker daemon"))).status("c")


def test_container_stop_remove_idempotent_but_fail_closed() -> None:
    """
    @brief   stop/remove of an absent container is fine; a real failure on an
             existing container raises.
    """
    gone = FakeRunner(_fail("No such container: c"), _fail("No such container: c"))
    _manager(gone).stop("c")  # stop fails -> status says absent -> ok

    stuck = FakeRunner(_fail("permission denied"), _ok("running\n"))
    with pytest.raises(IsolationError):
        _manager(stuck).remove("c")


def test_container_interrupt_is_bounded_and_fails_closed() -> None:
    """@brief Cancel uses a short stop, and runtime failure is explicit."""
    okay = FakeRunner(_ok())
    _manager(okay).interrupt("adore-run-one")
    assert okay.calls == [["docker", "stop", "--time", "2", "adore-run-one"]]
    assert okay.timeouts == [20]

    stuck = FakeRunner(_fail("daemon unavailable"))
    with pytest.raises(IsolationError):
        _manager(stuck).interrupt("adore-run-one")


def test_container_ensure_volumes_and_failure() -> None:
    """
    @brief   Both cache volumes are created; a runtime failure raises.
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
    """
    runner = FakeRunner(_fail("gate failed", exit_code=3))
    result = _manager(runner).exec("c", ["pi", "-p", "prompt"])
    assert result.exit_code == 3
    assert runner.calls[0][:2] == ["docker", "exec"]
    assert runner.calls[0][-4:] == ["c", "pi", "-p", "prompt"]


def test_container_exec_passes_safe_env_inline_and_secret_env_bare() -> None:
    """
    @brief   Exec-time env mirrors provision: PI_CODING_AGENT_DIR is inline so Podman
             exec sees it; secret values stay out of argv.
    """
    runner = FakeRunner(_ok())
    _manager(runner).exec(
        "c",
        ["env"],
        env={"PI_CODING_AGENT_DIR": "/home/adore/.adore-pi-agent", "UV_LINK_MODE": "copy",
             "OPENAI_API_KEY": "sk-secret", "GIT_PAGER": "less", "pager": "more"},
    )
    argv = runner.calls[0]
    assert argv[:2] == ["docker", "exec"]
    assert "PI_CODING_AGENT_DIR=/home/adore/.adore-pi-agent" in argv
    assert "UV_LINK_MODE=copy" in argv
    assert "GIT_PAGER=cat" in argv and "PAGER=cat" in argv
    assert "GIT_PAGER=less" not in argv and "pager" not in argv
    assert "OPENAI_API_KEY" in argv
    assert not any("sk-secret" in part for part in argv)
    assert argv[-2:] == ["c", "env"]
    assert runner.envs[0] is not None
    assert runner.envs[0]["OPENAI_API_KEY"] == "sk-secret"


def test_container_spawn_attaches_stdin_with_the_exec_env_contract() -> None:
    """
    @brief   spawn starts `exec -i` with live pipes and exec's env handling:
             Pi isolation values inline, secret values only in the process env.
    """
    started = {}

    def popen(argv, **kwargs):
        started.update(argv=list(argv), **kwargs)
        return "process"

    process = _manager(FakeRunner()).spawn(
        "c", ["node", "cli.js", "--mode", "rpc"],
        env={"PI_CODING_AGENT_DIR": "/home/adore/.adore-pi-agent", "PI_OFFLINE": "1",
             "OPENAI_API_KEY": "sk-secret"},
        popen=popen,
    )
    assert process == "process"
    argv = started["argv"]
    assert argv[:3] == ["docker", "exec", "-i"]
    assert "PI_CODING_AGENT_DIR=/home/adore/.adore-pi-agent" in argv
    assert "PI_OFFLINE=1" in argv and "OPENAI_API_KEY" in argv
    assert not any("sk-secret" in part for part in argv)
    assert argv[-5:] == ["c", "node", "cli.js", "--mode", "rpc"]
    assert started["env"]["OPENAI_API_KEY"] == "sk-secret"
    assert {started[key] for key in ("stdin", "stdout", "stderr")} == {subprocess.PIPE}


def test_container_verify_required_tools_execs_checks() -> None:
    """
    @brief   Required project-image tool checks are parsed without a shell and
             executed inside the container with the provision env.
    """
    runner = FakeRunner(_ok(), _ok())
    _manager(runner).verify_required_tools(
        "c",
        ["make --version", "terraform --version"],
        env={"UV_LINK_MODE": "copy"},
    )
    for argv, tool in zip(runner.calls, ["make", "terraform"], strict=True):
        assert argv[:2] == ["docker", "exec"]
        assert argv[-3:] == ["c", tool, "--version"]
        assert argv[2:-3:2] == ["--env"] * 3
        assert set(argv[3:-3:2]) == {"UV_LINK_MODE=copy", "GIT_PAGER=cat", "PAGER=cat"}


def test_container_exec_is_never_unbounded() -> None:
    """
    @brief   The container exec seam always bounds the subprocess.
    @details `run_command`'s own default applies only when the caller omits
             the keyword, so forwarding `timeout=None` would reach
             `subprocess.run(timeout=None)` and hang the single-threaded poll
             loop forever. Every container command the orchestrator issues -
             `_provision`'s tool checks, `verify_required_tools`, and
             `_stage_host_auth`'s mkdir/cp - goes through this one seam, so
             bounding it here bounds all of them. An explicit `None` means
             "use the default bound", never "no bound"; an explicit budget
             still wins.
    """
    runner = FakeRunner(_ok(), _ok(), _ok(), _ok())
    manager = _manager(runner)

    manager.exec("c", ["mkdir", "-p", "/adore/auth"])       # omitted
    manager.exec("c", ["cp", "a", "b"], timeout=None)       # explicit None
    manager.exec("c", ["sh", "gate.sh"], timeout=1800.0)    # explicit budget
    manager.verify_required_tools("c", ["terraform --version"])

    assert None not in runner.timeouts
    assert runner.timeouts == [
        DEFAULT_COMMAND_TIMEOUT,
        DEFAULT_COMMAND_TIMEOUT,
        1800.0,
        DEFAULT_COMMAND_TIMEOUT,
    ]


def test_container_verify_required_tools_fails_closed() -> None:
    """
    @brief   Malformed checks and non-zero exits raise IsolationError with
             command context.
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
    """
    monkeypatch.chdir(tmp_path)
    runner = FakeRunner(_fail("", exit_code=1), _ok())
    manager = WorktreeManager("repo", "wt-root", runner)
    assert manager.root.is_absolute()
    manager.create("r1", "adore/r1", "HEAD")
    add_argv = runner.calls[1]
    assert str(tmp_path / "wt-root" / "r1") in add_argv
    assert "wt-root/r1" not in add_argv and "wt-root\\r1" not in add_argv


@pytest.mark.parametrize("listing", [
    "%SystemDrive%/ProgramData/Microsoft/Windows/Caches/test.db\0",
    "ProgramData/Microsoft/Windows/Caches/\u00e9 space.db\0",
])
def test_checkpoint_rejects_suspicious_new_path(tmp_path: Path, listing: str) -> None:
    """@brief Suspicious untracked paths stop before staging and identify the path."""
    runner = FakeRunner(_ok("?? file\0"), _ok(listing), _ok())
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(IsolationError, match="suspicious") as error:
        manager.commit_all_if_dirty("run-1", "checkpoint")
    assert listing[:-1] in str(error.value)
    assert all("add" not in call and "commit" not in call for call in runner.calls)


def test_checkpoint_rejects_staged_suspicious_path(tmp_path: Path) -> None:
    """@brief Already staged additions are inspected before checkpointing."""
    runner = FakeRunner(_ok("A  file\0"), _ok(), _ok("%TEMP%/file\0"))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(IsolationError, match="suspicious"):
        manager.commit_all_if_dirty("run-1", "checkpoint")
    assert all("add" not in call and "commit" not in call for call in runner.calls)


@pytest.mark.parametrize("listing", ["unterminated", "../escape\0", "a\0\0"])
def test_checkpoint_rejects_invalid_git_path_evidence(tmp_path: Path, listing: str) -> None:
    """@brief Malformed Git evidence fails closed before staging."""
    runner = FakeRunner(_ok("?? file\0"), _ok(listing), _ok())
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(IsolationError, match="invalid"):
        manager.commit_all_if_dirty("run-1", "checkpoint")
    assert all("add" not in call and "commit" not in call for call in runner.calls)



def test_checkpoint_accepts_ordinary_names(tmp_path: Path) -> None:
    """@brief Names with spaces, Unicode, percent signs and ordinary caches remain eligible."""
    runner = FakeRunner(_ok("?? file\0"), _ok("docs/100% done/é.txt\0.cache/data\0"),
                        _ok(), _ok(), _ok(), _ok("A  file\0"), _ok())
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    assert manager.commit_all_if_dirty("run-1", "checkpoint")
    assert runner.calls[1][-4:] == ["ls-files", "--others", "--exclude-standard", "-z"]
    assert runner.calls[2][-6:] == [
        "diff", "--cached", "--no-renames", "--name-only", "--diff-filter=A", "-z",
    ]



def test_checkpoint_accepts_tracked_type_change(tmp_path: Path) -> None:
    """@brief A valid Git type-change status remains checkpointable."""
    runner = FakeRunner(_ok(" T file\0"), _ok(), _ok(), _ok(), _ok(),
                        _ok("T  file\0"), _ok())
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    assert manager.commit_all_if_dirty("run-1", "checkpoint")



@pytest.mark.parametrize("status", ["?? new/nested.txt\0", "AA conflict\0",
                                    " R new\0old\0"])
def test_checkpoint_accepts_other_valid_statuses(tmp_path: Path, status: str) -> None:
    """@brief Nested untracked, conflict and rename statuses follow normal Git behavior."""
    runner = FakeRunner(_ok(status), _ok(), _ok(), _ok(), _ok(),
                        _ok("M  file\0"), _ok())
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    assert manager.commit_all_if_dirty("run-1", "checkpoint")
    assert "--untracked-files=all" in runner.calls[0]



def test_checkpoint_accepts_untracked_embedded_repository(tmp_path: Path) -> None:
    """@brief Git can list an embedded repository with a trailing slash."""
    runner = FakeRunner(_ok("?? nested/\0"), _ok("nested/\0"), _ok(),
                        _ok(), _ok("nested\0"), _ok("A  nested\0"), _ok())
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    assert manager.commit_all_if_dirty("run-1", "checkpoint")


def test_checkpoint_git_listing_failure_stops(tmp_path: Path) -> None:
    """@brief Git failure is distinct from a suspicious path and prevents commit."""
    runner = FakeRunner(_ok("?? file\0"), _ok(), _fail("broken index"))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(IsolationError, match="git diff failed"):
        manager.commit_all_if_dirty("run-1", "checkpoint")
    assert all("add" not in call and "commit" not in call for call in runner.calls)



@pytest.mark.parametrize("result", [CommandResult(exit_code=False),
                                    CommandResult(exit_code=0, timed_out=True),
                                    _ok("?? incomplete"),
                                    _ok(" M ../escape\0"),
                                    _ok("?M file\0"),
                                    _ok("TU file\0"),
                                    _ok("R  dest\0../source\0")])
def test_checkpoint_rejects_invalid_status(tmp_path: Path, result: CommandResult) -> None:
    """@brief Bad status evidence cannot produce a clean checkpoint."""
    runner = FakeRunner(result)
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(IsolationError):
        manager.commit_all_if_dirty("run-1", "checkpoint")
    assert len(runner.calls) == 1


def test_checkpoint_rechecks_additions_before_commit(tmp_path: Path) -> None:
    """@brief A suspicious addition discovered after staging stops the commit."""
    runner = FakeRunner(_ok("?? file\0"), _ok(), _ok(), _ok(),
                        _ok("%TEMP%/new\0"))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(IsolationError, match="suspicious"):
        manager.commit_all_if_dirty("run-1", "checkpoint")
    assert all("commit" not in call for call in runner.calls)



def test_checkpoint_corrupt_evidence_takes_priority_over_suspicion(tmp_path: Path) -> None:
    """@brief Partial evidence is reported as invalid rather than as a path finding."""
    runner = FakeRunner(_ok("?? file\0"), _ok("%TEMP%/file\0"), _ok("partial"))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(IsolationError, match="invalid"):
        manager.commit_all_if_dirty("run-1", "checkpoint")


@pytest.mark.parametrize("index", [3, 6])
def test_checkpoint_rejects_corrupt_mutation_exit(tmp_path: Path, index: int) -> None:
    """@brief Invalid add and commit exit evidence fails closed."""
    results = [_ok("?? file\0"), _ok(), _ok(), _ok(), _ok(),
               _ok("A  file\0"), _ok()]
    results[index] = CommandResult(exit_code=False)
    runner = FakeRunner(*results)
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(IsolationError, match="invalid"):
        manager.commit_all_if_dirty("run-1", "checkpoint")


def test_checkpoint_commit_uses_configured_git_identity(tmp_path: Path) -> None:
    """@brief A fresh clone needs no global Git identity for ADORE commits."""
    runner = FakeRunner(_ok(" M file.py\0"), _ok(), _ok(), _ok(), _ok(), _ok("M  file.py\0"), _ok())
    manager = WorktreeManager(
        tmp_path / "repo", tmp_path / "worktrees", runner,
        git_name="ADORE Bot", git_email="adore@example.invalid",
    )
    assert manager.commit_all_if_dirty("run-1", "checkpoint") is True
    assert runner.calls[-1][-7:] == [
        "-c", "user.name=ADORE Bot", "-c",
        "user.email=adore@example.invalid", "commit", "-m", "checkpoint",
    ]


def test_checkpoint_commit_reports_git_failure(tmp_path: Path) -> None:
    """@brief Git commit failure remains a typed isolation error."""
    runner = FakeRunner(
        _ok(" M file.py\0"), _ok(), _ok(), _ok(), _ok(), _ok("M  file.py\0"),
        _fail("commit rejected"),
    )
    manager = WorktreeManager(
        tmp_path / "repo", tmp_path / "worktrees", runner,
        git_name="ADORE Bot", git_email="adore@example.invalid",
    )
    with pytest.raises(IsolationError, match="git commit failed"):
        manager.commit_all_if_dirty("run-1", "checkpoint")


def test_container_mount_sources_are_always_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief   Relative mount sources are resolved before hitting docker - a
             bare relative source would be read as a NAMED VOLUME and mount
             an empty volume over the worktree.
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
    """
    assert wsl_mount_path(r"D:\TEMP\adore\worktrees\run-1") == "/mnt/d/TEMP/adore/worktrees/run-1"
    assert wsl_mount_path("C:/Users/x") == "/mnt/c/Users/x"
    assert wsl_mount_path("/already/posix") == "/already/posix"


def test_wsl_runtime_prefixes_every_command() -> None:
    """
    @brief   A wrapped runtime string is split and prefixed onto the argv.
    """
    runner = FakeRunner(_ok("running\n"))
    manager = _wsl_manager(runner)
    assert manager.wsl_mode is True
    assert manager.status("c") == "running"
    assert runner.calls[0][:5] == ["wsl", "-d", "Ubuntu-24.04", "--exec", "docker"]
    assert runner.calls[0][5] == "inspect"


def test_wsl_provision_translates_mounts_and_sets_wslenv(tmp_path: Path) -> None:
    """
    @brief   In WSL mode mount sources are /mnt/<drive>/ paths; safe runtime
             env values are inline, while secret env values cross via WSLENV.
    """
    runner = FakeRunner(_fail("No such container"), _ok("cid"),
                        _ok("adore-git-binding-v1\n"))
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
    assert "GIT_DIR" in env_values
    assert not any(value.startswith("GIT_DIR=") for value in env_values)
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
        egress=EgressPolicy(mode="allowlist-proxy", allowlist=["example.com"]),
    )
    manager.provision("adore-run-x", r"D:\repo", r"D:\wt", tmp_path / "io", {})
    for call in runner.calls:
        assert call[:5] == ["wsl", "-d", "Ubuntu-24.04", "--exec", "docker"]
    assert runner.calls[1][5:8] == ["network", "create", "--internal"]
    assert runner.calls[4][5:8] == ["network", "connect", "--alias"]
    assert runner.calls[5][5:7] == ["run", "--detach"]


def test_plain_docker_runtime_does_not_set_wslenv(tmp_path: Path) -> None:
    """
    @brief   Outside WSL mode, WSLENV is left exactly as the host had it.
    """
    runner = FakeRunner(_fail("No such container"), _ok("cid"))
    _manager(runner).provision("c", tmp_path, tmp_path, tmp_path / "io", {"K": "v"})
    process_env = runner.envs[1]
    assert process_env is not None
    assert process_env.get("WSLENV", "") == os.environ.get("WSLENV", "")


# END OF FILE



def test_worktree_progress_observes_content_and_excludes_bookkeeping(tmp_path):
    """@brief Tracked and untracked bytes contribute; journals and caches are excluded."""
    runner = FakeRunner(_ok("diff-one"), _ok("new file.py\0"),
                        _ok("diff-one"), _ok("new file.py\0"),
                        _ok("diff-two"), _ok("new file.py\0"))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    wt = manager.path_for("run-1")
    wt.mkdir(parents=True)
    source = wt / "new file.py"
    source.write_text("one")
    first = manager.worktree_progress_fingerprint("run-1")
    source.write_text("two")
    second = manager.worktree_progress_fingerprint("run-1")
    third = manager.worktree_progress_fingerprint("run-1")
    assert first != second != third
    assert all(":(exclude).agentic/tasks/**" in call for call in runner.calls)
    assert all(":(exclude)**/__pycache__/**" in call for call in runner.calls)


@pytest.mark.parametrize("name", ["../secret", "/absolute", "C:/outside", "missing", "dir/file"])
def test_worktree_progress_refuses_unsafe_or_unreadable_paths(tmp_path, name):
    """@brief Git-supplied paths cannot escape or silently ignore missing content."""
    runner = FakeRunner(_ok(), _ok(name + "\0"))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    manager.path_for("run-1").mkdir(parents=True)
    with pytest.raises(IsolationError):
        manager.worktree_progress_fingerprint("run-1")


def test_worktree_progress_refuses_git_failure(tmp_path):
    """@brief An unavailable diff never becomes a false empty progress snapshot."""
    runner = FakeRunner(CommandResult(exit_code=1, stderr="bad diff"))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    with pytest.raises(IsolationError, match="bad diff"):
        manager.worktree_progress_fingerprint("run-1")



def test_worktree_progress_hashes_links_without_following_and_rejects_link_parents(tmp_path):
    """@brief A link target counts without external reads; linked directories are refused."""
    runner = FakeRunner(_ok(), _ok("link\0"), _ok(), _ok("link\0"),
                        _ok(), _ok("directory/secret\0"))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    wt = manager.path_for("run-1")
    wt.mkdir(parents=True)
    link = wt / "link"
    try:
        link.symlink_to(tmp_path / "absent-one")
    except OSError:
        pytest.skip("platform does not permit unprivileged symbolic links")
    first = manager.worktree_progress_fingerprint("run-1")
    link.unlink()
    link.symlink_to(tmp_path / "absent-two")
    assert first != manager.worktree_progress_fingerprint("run-1")
    (wt / "directory").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(IsolationError, match="symlink parent"):
        manager.worktree_progress_fingerprint("run-1")


# PUBLIC API / TESTS - direct exchange exclusions


def _exchange_symlink(source: Path, target: Path, *, directory: bool = False) -> None:
    """@brief Create a boundary-test link, skipping only Windows privilege refusal.
    @param[in] source Link path inside the fake owned worktree.
    @param[in] target External target which must remain untouched.
    @param[in] directory Whether the target is a directory.
    """
    try:
        source.symlink_to(target, target_is_directory=directory)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows account lacks symbolic-link privilege")
        raise


@pytest.mark.parametrize("tracked", [False, True])
def test_progress_excludes_literal_exchange_paths(tmp_path: Path, tracked: bool) -> None:
    """@brief Exchange edits are invisible but product edits still change progress."""
    excluded = ("ADORE_SUMMARY.md", "notes/questions[1].md")
    expected = {f":(top,literal,exclude){name}" for name in excluded}
    calls = []
    product_diff = "one"

    def runner(argv, **kwargs):
        """@brief Model filtered Git output and require literal exclusions on both lists."""
        calls.append(argv)
        if "ls-tree" in argv:
            return _ok()
        assert expected.issubset(argv)
        if "diff" in argv:
            # Indexed exchange additions must be filtered by Git, not Python parsing.
            return _ok(product_diff)
        assert "ls-files" in argv
        return _ok("source.py\0")

    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    wt = manager.path_for("run-1")
    (wt / "notes").mkdir(parents=True)
    (wt / "source.py").write_text("one", encoding="utf-8")
    for name in excluded:
        (wt / name).write_text("first", encoding="utf-8")
    first = manager.worktree_progress_fingerprint("run-1", exclude_paths=excluded)
    for name in excluded:
        (wt / name).write_text("second", encoding="utf-8")
    second = manager.worktree_progress_fingerprint("run-1", exclude_paths=excluded)
    assert first == second
    if tracked:
        product_diff = "two"
    else:
        (wt / "source.py").write_text("two", encoding="utf-8")
    assert second != manager.worktree_progress_fingerprint("run-1", exclude_paths=excluded)
    assert all("--" in call for call in calls if "ls-tree" not in call)


@pytest.mark.parametrize("method", ["progress", "checkpoint"])
@pytest.mark.parametrize("path", ["", ".", "../escape", "/absolute", "C:/outside",
                                   "a/../b", "a//b", "a\\b", ".git/config", "bad\0name", None])
def test_exchange_exclusions_refuse_unsafe_paths(tmp_path: Path, method: str, path: str) -> None:
    """@brief Exclusion inputs cannot escape the worktree or hide its Git administration."""
    runner = FakeRunner()
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    with pytest.raises(IsolationError, match="exchange path"):
        if method == "progress":
            manager.worktree_progress_fingerprint("run-1", exclude_paths=(path,))
        else:
            manager.commit_all_if_dirty("run-1", "checkpoint", exclude_paths=(path,))
    assert runner.calls == []


@pytest.mark.parametrize("method", ["progress", "checkpoint"])
@pytest.mark.parametrize("entry", ["ADORE_SUMMARY.md\0", "ADORE_SUMMARY.md/child\0"])
def test_exchange_paths_refuse_source_collisions(tmp_path: Path, method: str, entry: str) -> None:
    """@brief Existing source at an exchange path cannot be hidden or overwritten."""
    runner = FakeRunner(_ok(entry))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    manager.path_for("run-1").mkdir(parents=True)
    with pytest.raises(IsolationError, match="source-owned exchange path"):
        if method == "progress":
            manager.worktree_progress_fingerprint("run-1", exclude_paths=("ADORE_SUMMARY.md",))
        else:
            manager.commit_all_if_dirty("run-1", "checkpoint", exclude_paths=("ADORE_SUMMARY.md",))
    assert len(runner.calls) == 1
    assert runner.calls[0][3:] == ["ls-tree", "-r", "--full-tree", "--name-only", "-z", "HEAD"]


@pytest.mark.parametrize("observed", ["incomplete", "\0", "../escape\0"])
def test_exchange_paths_refuse_corrupt_collision_evidence(tmp_path: Path, observed: str) -> None:
    """@brief Untrusted Git collision checks never silently enable an exclusion."""
    runner = FakeRunner(_ok(observed))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    manager.path_for("run-1").mkdir(parents=True)
    with pytest.raises(IsolationError, match="invalid Git exchange"):
        manager.worktree_progress_fingerprint("run-1", exclude_paths=("ADORE_SUMMARY.md",))


def test_checkpoint_unstages_and_excludes_exchange_files(tmp_path: Path) -> None:
    """@brief Already-staged exchange additions are restored before literal staging."""
    excluded = ("ADORE_SUMMARY.md", "notes/questions[1].md")
    runner = FakeRunner(
        _ok(),  # No source-owned exchange paths in HEAD.
        _ok(),  # Unstage exchange additions (including removed summary).
        _ok(" M source.py\0?? ADORE_SUMMARY.md\0?? notes/questions[1].md\0"),
        _ok("source.py\0ADORE_SUMMARY.md\0notes/questions[1].md\0"),
        _ok(), _ok(), _ok("source.py\0"),  # Add; inspect additions.
        _ok("source.py\0"),  # Full staged set, not only additions.
        _ok("M  source.py\0?? ADORE_SUMMARY.md\0?? notes/questions[1].md\0"),
        _ok(),
    )
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    manager.path_for("run-1").mkdir(parents=True)
    assert manager.commit_all_if_dirty("run-1", "checkpoint", exclude_paths=excluded)
    assert runner.calls[1][3:] == [
        "reset", "-q", "HEAD", "--", *[f":(top,literal){name}" for name in excluded],
    ]
    add = next(call for call in runner.calls if "add" in call)
    assert add[3:] == ["add", "-A", "--", ".",
                       *[f":(top,literal,exclude){name}" for name in excluded]]
    assert runner.calls[-1][-3:] == ["commit", "-m", "checkpoint"]
    assert not runner.results


@pytest.mark.parametrize("staged", ["ADORE_SUMMARY.md\0", "notes/questions[1].md\0",
                                    "ADORE_SUMMARY.md/child\0", "incomplete", "../escape\0"])
def test_checkpoint_rechecks_all_staged_exchange_paths(tmp_path: Path, staged: str) -> None:
    """@brief A staged modification/deletion or race at an exchange path prevents commit."""
    runner = FakeRunner(_ok(), _ok(), _ok(" M source.py\0"), _ok(), _ok(),
                        _ok(), _ok(), _ok(staged), _ok("M  source.py\0"), _ok())
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    manager.path_for("run-1").mkdir(parents=True)
    with pytest.raises(IsolationError, match="exchange|invalid"):
        manager.commit_all_if_dirty("run-1", "checkpoint",
                                    exclude_paths=("ADORE_SUMMARY.md", "notes/questions[1].md"))
    assert all("commit" not in call for call in runner.calls)


def test_checkpoint_exchange_only_is_noop(tmp_path: Path) -> None:
    """@brief An untracked exchange file alone never authorizes an empty commit."""
    runner = FakeRunner(_ok(), _ok(), _ok("?? ADORE_SUMMARY.md\0"))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    manager.path_for("run-1").mkdir(parents=True)
    assert not manager.commit_all_if_dirty("run-1", "checkpoint",
                                           exclude_paths=("ADORE_SUMMARY.md",))
    assert all("commit" not in call and "add" not in call for call in runner.calls)


@pytest.mark.parametrize("result", [_fail("cannot unstage"), CommandResult(exit_code=False),
                                    CommandResult(exit_code=0, timed_out=True)])
def test_checkpoint_exchange_unstage_failure_stops(tmp_path: Path, result: CommandResult) -> None:
    """@brief Failed or untrustworthy index restoration cannot reach staging or commit."""
    runner = FakeRunner(_ok(), result)
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    manager.path_for("run-1").mkdir(parents=True)
    with pytest.raises(IsolationError):
        manager.commit_all_if_dirty("run-1", "checkpoint", exclude_paths=("ADORE_SUMMARY.md",))
    assert all("commit" not in call and "add" not in call for call in runner.calls)


# PUBLIC API / TESTS - summary artifact trust boundary


@pytest.mark.parametrize("text", ["", "What changed: café\nChecked: tests passed\n",
                                  "é" * 9000 + "\nlast checks\n"],
                         ids=["empty", "unicode", "bounded-tail"])
def test_summary_read_then_owned_removal(tmp_path: Path, text: str) -> None:
    """@brief Bounded UTF-8 evidence is read without mutation, then removed explicitly."""
    runner = FakeRunner(_ok(), _ok())
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    wt = manager.path_for("run-1")
    wt.mkdir(parents=True)
    source = wt / "ADORE_SUMMARY.md"
    source.write_text(text, encoding="utf-8", newline="\n")
    artifact = manager.read_summary("run-1", max_chars=6000)
    assert artifact is not None and artifact.text == text[-6000:]
    assert source.read_text(encoding="utf-8") == text  # Caller must persist before removal.
    manager.remove_summary("run-1", artifact)
    assert not source.exists()
    assert all("commit" not in call for call in runner.calls)


@pytest.mark.parametrize("changed", [False, True])
def test_summary_compares_change_times_within_each_metadata_api(tmp_path, monkeypatch, changed):
    """@brief Different path/descriptor clocks are valid; a changed open file is refused."""
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=FakeRunner(_ok(), _ok()))
    source = manager.path_for("run-1") / "ADORE_SUMMARY.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"rewritten summary\r\nwith control \x1a and trailing text")
    original = os.fstat
    calls = 0

    def descriptor_stat(fd):
        """@brief Model Windows metadata clocks without changing any file contents."""
        nonlocal calls
        calls += 1
        info = original(fd)
        values = {key: getattr(info, key) for key in (
            "st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")}
        values["st_ctime_ns"] += 100 + (calls if changed else 0)
        return SimpleNamespace(**values)

    monkeypatch.setattr(os, "fstat", descriptor_stat)
    if changed:
        with pytest.raises(IsolationError, match="changed during read"):
            manager.read_summary("run-1", max_chars=6000)
        assert source.exists()
    else:
        artifact = manager.read_summary("run-1", max_chars=6000)
        assert artifact.text == source.read_bytes().decode("utf-8")
        manager.remove_summary("run-1", artifact)
        assert not source.exists()


def test_summary_absence_is_not_an_error(tmp_path: Path) -> None:
    """@brief Missing requested output is allowed, never invented or created."""
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=FakeRunner(_ok()))
    manager.path_for("run-1").mkdir(parents=True)
    assert manager.read_summary("run-1", max_chars=6000) is None
    assert list(manager.path_for("run-1").iterdir()) == []


@pytest.mark.parametrize("kind", ["invalid-utf8", "directory", "symlink", "hardlink"])
def test_summary_refuses_unsafe_artifact(tmp_path: Path, kind: str) -> None:
    """@brief Corrupt, linked and non-file executor output fails closed without deletion."""
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=FakeRunner(_ok()))
    wt = manager.path_for("run-1")
    wt.mkdir(parents=True)
    source = wt / "ADORE_SUMMARY.md"
    outside = tmp_path / "outside"
    outside.write_bytes(b"not summary")
    if kind == "invalid-utf8":
        # An invalid prefix must not be hidden by retained tail truncation.
        source.write_bytes(b"\xff" + b"x" * 9000)
    elif kind == "directory":
        source.mkdir()
    elif kind == "symlink":
        _exchange_symlink(source, outside)
    else:
        os.link(outside, source)
    with pytest.raises(IsolationError, match="summary|exchange"):
        manager.read_summary("run-1", max_chars=6000)
    assert source.exists() or source.is_symlink()
    assert outside.read_bytes() == b"not summary"


@pytest.mark.parametrize("operation", ["read", "remove"])
def test_summary_io_failure_is_typed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                     operation: str) -> None:
    """@brief Read/unlink errors preserve the artifact and the previously captured text."""
    runner = FakeRunner(_ok(), _ok())
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    source = manager.path_for("run-1") / "ADORE_SUMMARY.md"
    source.parent.mkdir(parents=True)
    source.write_text("kept evidence", encoding="utf-8")

    def denied(*args, **kwargs):
        """@brief Inject a permission boundary rather than depend on the test account UID."""
        raise PermissionError("denied summary")

    if operation == "read":
        monkeypatch.setattr(os, "open", denied)
        with pytest.raises(IsolationError, match="summary"):
            manager.read_summary("run-1", max_chars=6000)
    else:
        artifact = manager.read_summary("run-1", max_chars=6000)
        monkeypatch.setattr(Path, "unlink", denied)
        with pytest.raises(IsolationError, match="summary"):
            manager.remove_summary("run-1", artifact)
        assert artifact.text == "kept evidence"
    assert source.read_text(encoding="utf-8") == "kept evidence"


@pytest.mark.parametrize("mutation", ["replace", "edit", "missing", "symlink"])
def test_summary_removal_rejects_changed_identity(tmp_path: Path, mutation: str) -> None:
    """@brief A stale read cannot authorize deletion of a new or changed artifact."""
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=FakeRunner(_ok(), _ok()))
    source = manager.path_for("run-1") / "ADORE_SUMMARY.md"
    source.parent.mkdir(parents=True)
    source.write_text("original", encoding="utf-8")
    artifact = manager.read_summary("run-1", max_chars=6000)
    outside = tmp_path / "outside"
    outside.write_text("replacement", encoding="utf-8")
    if mutation == "replace":
        os.replace(outside, source)
    elif mutation == "edit":
        source.write_text("changed", encoding="utf-8")
    else:
        source.unlink()
        if mutation == "symlink":
            _exchange_symlink(source, outside)
    with pytest.raises(IsolationError, match="summary|exchange"):
        manager.remove_summary("run-1", artifact)
    if mutation != "missing":
        assert source.exists()
    assert artifact.text == "original"


def test_summary_refuses_a_linked_worktree(tmp_path: Path) -> None:
    """@brief Even a missing summary behind an aliased root is not safe absence."""
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=FakeRunner())
    manager.root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "ADORE_SUMMARY.md").write_text("private", encoding="utf-8")
    _exchange_symlink(manager.path_for("run-1"), outside, directory=True)
    with pytest.raises(IsolationError, match="exchange"):
        manager.read_summary("run-1", max_chars=6000)
    assert (outside / "ADORE_SUMMARY.md").read_text(encoding="utf-8") == "private"


def test_summary_source_owned_collision_is_not_consumed(tmp_path: Path) -> None:
    """@brief A repository's existing summary-named source is never agent output."""
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work",
                              runner=FakeRunner(_ok("ADORE_SUMMARY.md\0")))
    source = manager.path_for("run-1") / "ADORE_SUMMARY.md"
    source.parent.mkdir(parents=True)
    source.write_text("repository source", encoding="utf-8")
    with pytest.raises(IsolationError, match="source-owned exchange path"):
        manager.read_summary("run-1", max_chars=6000)
    assert source.read_text(encoding="utf-8") == "repository source"


@pytest.mark.parametrize("bound", [0, -1, True, None, "6000"])
def test_summary_refuses_invalid_evidence_bound(tmp_path: Path, bound: object) -> None:
    """@brief A malformed retention bound never reads or removes executor output."""
    runner = FakeRunner()
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    with pytest.raises(IsolationError, match="summary evidence bound"):
        manager.read_summary("run-1", max_chars=bound)
    assert not runner.calls


def test_summary_removal_refuses_wrong_worktree(tmp_path: Path) -> None:
    """@brief Text read from one run does not authorize deleting another run's summary."""
    runner = FakeRunner(_ok())
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    for run_id in ("run-1", "run-2"):
        source = manager.path_for(run_id) / "ADORE_SUMMARY.md"
        source.parent.mkdir(parents=True)
        source.write_text(run_id, encoding="utf-8")
    artifact = manager.read_summary("run-1", max_chars=6000)
    with pytest.raises(IsolationError, match="different worktree"):
        manager.remove_summary("run-2", artifact)
    assert (manager.path_for("run-2") / "ADORE_SUMMARY.md").read_text(encoding="utf-8") == "run-2"
    assert len(runner.calls) == 1


@pytest.mark.parametrize("phase", ["open", "read"])
def test_summary_refuses_mutation_during_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str,
) -> None:
    """@brief Pre-read replacement and mid-read edits cannot yield a valid summary receipt."""
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=FakeRunner(_ok()))
    source = manager.path_for("run-1") / "ADORE_SUMMARY.md"
    source.parent.mkdir(parents=True)
    source.write_text("original", encoding="utf-8")
    if phase == "open":
        original_open = os.open

        def replace_at_open(path, flags):
            """@brief Swap in a distinct regular file after the first path check."""
            replacement = source.with_suffix(".new")
            replacement.write_text("replacement", encoding="utf-8")
            os.replace(replacement, source)
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", replace_at_open)
    else:
        original_fstat = os.fstat
        checks = 0

        def mutate_after_precheck(fd):
            """@brief Change the same inode while the summary stream is being consumed."""
            nonlocal checks
            info = original_fstat(fd)
            checks += 1
            if checks == 1:
                source.write_text("changed content", encoding="utf-8")
            return info

        monkeypatch.setattr(os, "fstat", mutate_after_precheck)
    with pytest.raises(IsolationError, match="summary changed"):
        manager.read_summary("run-1", max_chars=6000)
    assert source.exists()


@pytest.mark.parametrize("method", ["progress", "checkpoint"])
def test_exchange_refuses_linked_question_parent(tmp_path: Path, method: str) -> None:
    """@brief A configured nested questions path cannot enter an external linked directory."""
    runner = FakeRunner()
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=runner)
    wt = manager.path_for("run-1")
    wt.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "questions.md").write_text("private", encoding="utf-8")
    _exchange_symlink(wt / "notes", outside, directory=True)
    with pytest.raises(IsolationError, match="exchange path parent"):
        if method == "progress":
            manager.worktree_progress_fingerprint("run-1", exclude_paths=("notes/questions.md",))
        else:
            manager.commit_all_if_dirty("run-1", "checkpoint",
                                        exclude_paths=("notes/questions.md",))
    assert (outside / "questions.md").read_text(encoding="utf-8") == "private"
    assert not runner.calls


@pytest.mark.parametrize("result", [CommandResult(exit_code=False),
                                    CommandResult(exit_code=0, stdout=None),
                                    CommandResult(exit_code=0, stdout="\ufffd"),
                                    CommandResult(exit_code=0, timed_out=True),
                                    _fail("Git failed")])
@pytest.mark.parametrize("index", [0, 1, 2])
def test_direct_progress_refuses_untrusted_git_results(tmp_path: Path, result: CommandResult,
                                                      index: int) -> None:
    """@brief Neither collision lists, binary diffs nor untracked lists may be corrupt."""
    results = [_ok(), _ok(), _ok()]
    results[index] = result
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner=FakeRunner(*results))
    manager.path_for("run-1").mkdir(parents=True)
    with pytest.raises(IsolationError):
        manager.worktree_progress_fingerprint("run-1", exclude_paths=("ADORE_SUMMARY.md",))
