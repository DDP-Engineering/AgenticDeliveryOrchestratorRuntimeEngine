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
@file       test_container_git.py
@brief      Public container Git-binding contracts, with offline runtime doubles.
@details    Temporary pointer files and recorded CLI arguments establish native
            discovery construction without executing real Git or containers.
"""

from __future__ import annotations

# IMPORTS
import os
from pathlib import Path
import stat

from adore.isolation import ContainerManager, IsolationError, build_container_env
from adore.util import CommandResult
import pytest

from tests.test_isolation import FakeRunner, owned_container_receipt

# PUBLIC API / TESTS

@pytest.mark.parametrize("runtime", [
    "wsl -d Ubuntu -- docker", "wsl -d Ubuntu docker",
    "wsl -d Ubuntu --exec docker", "wsl -d Ubuntu -e docker",
])
def test_wsl_container_commands_use_direct_argv_transport(runtime):
    """@brief Supported WSL prefixes carry literal data without default-shell expansion.
    @param[in] runtime Supported WSL command notation.
    """
    runner = FakeRunner(CommandResult(stdout="ok"))
    manager = ContainerManager(runtime, "image", "uv", "npm", runner)
    manager.exec("c", ["printf", "$(literal) and $DATA; no shell"])
    argv = runner.calls[0]
    assert "--exec" in argv or "-e" in argv
    assert "--" not in argv[:argv.index("docker")]
    assert argv[-1] == "$(literal) and $DATA; no shell"


def test_ambiguous_wsl_runtime_requires_explicit_command_boundary():
    """@brief A custom WSL command identifies its direct execution boundary."""
    with pytest.raises(ValueError, match="explicit"):
        ContainerManager("wsl -d Ubuntu custom-wrapper", "image", "uv", "npm", FakeRunner())


@pytest.mark.parametrize("runtime,expected", [
    ("wsl -d docker docker", ["wsl", "-d", "docker", "--exec", "docker"]),
    ("wsl -d Ubuntu -u docker docker",
     ["wsl", "-d", "Ubuntu", "-u", "docker", "--exec", "docker"]),
    ("wsl --distribution Ubuntu --user podman --cd /home/docker docker",
     ["wsl", "--distribution", "Ubuntu", "--user", "podman", "--cd", "/home/docker",
      "--exec", "docker"]),
    ("wsl -d Ubuntu -- custom-wrapper --exec docker",
     ["wsl", "-d", "Ubuntu", "--exec", "custom-wrapper", "--exec", "docker"]),
    ("wsl -d Ubuntu -- custom-wrapper -e docker",
     ["wsl", "-d", "Ubuntu", "--exec", "custom-wrapper", "-e", "docker"]),
    ("wsl -d Ubuntu -e custom-wrapper --exec docker",
     ["wsl", "-d", "Ubuntu", "-e", "custom-wrapper", "--exec", "docker"]),
    ("wsl --distribution-id guid --system --shell-type none -- docker",
     ["wsl", "--distribution-id", "guid", "--system", "--shell-type", "none",
      "--exec", "docker"]),
])
def test_wsl_options_and_wrapper_arguments_keep_their_positions(runtime, expected):
    """@brief Only the WSL command boundary controls direct transport.
    @param[in] runtime Option operands or wrapper arguments resembling runtime markers.
    @param[in] expected Exact admitted prefix, preserving all operand data.
    """
    runner = FakeRunner(CommandResult(stdout="ok"))
    manager = ContainerManager(runtime, "image", "uv", "npm", runner)
    manager.exec("c", ["printf", "$(literal)"])
    assert runner.calls[0][:len(expected) + 1] == [*expected, "exec"]
    assert runner.calls[0][-3:] == ["c", "printf", "$(literal)"]


@pytest.mark.parametrize("runtime", [
    "wsl -d", "wsl -d Ubuntu --exec", "wsl -d Ubuntu --",
    "wsl --unknown-option docker", "wsl --cd /home/docker custom-wrapper",
])
def test_wsl_incomplete_or_unsupported_options_fail_before_execution(runtime):
    """@brief Unknown or incomplete WSL prefixes cannot select a guessed command.
    @param[in] runtime Invalid or ambiguous WSL execution prefix.
    """
    runner = FakeRunner()
    with pytest.raises(ValueError):
        ContainerManager(runtime, "image", "uv", "npm", runner)
    assert runner.calls == []


def test_fresh_git_container_mounts_native_pointer_and_clears_selection(
    tmp_path: Path, monkeypatch,
) -> None:
    """@brief Fresh repository containers admit a pointer and clear inherited selectors.
    @param[in] tmp_path Temporary host filesystem, outside the candidate tree.
    @param[in] monkeypatch Inject inherited host selection variables.
    """
    monkeypatch.setenv("GIT_DIR", "/host-wrong")
    runner = FakeRunner(
        CommandResult(exit_code=1, stderr="No such container: adore-git-check"),
        CommandResult(stdout="created-id"),
        CommandResult(stdout="adore-git-binding-v1\n"),
    )
    manager = ContainerManager("docker", "test-image", "uv-cache", "npm-cache", runner)
    io = tmp_path / "io"
    metadata = build_container_env("run-1", "Bot", "bot@example.test")

    assert manager.provision(
        "adore-git-check", tmp_path / "repo", tmp_path / "work", io, metadata,
    ) == "created"

    pointer = io / "container.git"
    assert pointer.read_bytes() == b"gitdir: /adore/repo/.git/worktrees/run-1\n"
    created = runner.calls[1]
    assert f"{pointer.as_posix()}:/adore/work/.git:ro" in created
    assert "io.ddp.adore.git-binding=pointer-v1" in created
    env_values = [created[i + 1] for i, part in enumerate(created[:-1]) if part == "--env"]
    for key in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE"):
        assert key in env_values  # Docker bare-key removal overrides image defaults.
        assert not any(value.startswith(key + "=") for value in env_values)
        assert key not in runner.envs[1]
    assert "GIT_AUTHOR_NAME=Bot" in env_values
    assert runner.calls[2][:2] == ["docker", "exec"]


def test_bound_exec_does_not_forward_git_selection_metadata() -> None:
    """@brief Descendants receive author identity and secrets, without Git selectors."""
    runner = FakeRunner(CommandResult(stdout="ok"))
    manager = ContainerManager("docker", "test-image", "uv-cache", "npm-cache", runner)
    metadata = build_container_env("run-1", "Bot", "bot@example.test")
    metadata["OPENAI_API_KEY"] = "fake-test-key"

    assert manager.exec("adore-git-check", ["python3", "test.py"], env=metadata).ok

    argv = runner.calls[0]
    values = [argv[i + 1] for i, part in enumerate(argv[:-1]) if part == "--env"]
    assert not any(value.split("=", 1)[0] in {
        "GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE",
    } for value in values)
    assert "GIT_AUTHOR_NAME=Bot" in values
    assert "OPENAI_API_KEY" in values
    assert not any("fake-test-key" in part for part in argv)


@pytest.mark.parametrize("runtime,expected", [
    ("podman", "podman"),
    ("wsl -d Ubuntu -- podman", "podman"),
    ("wsl -d Ubuntu -- docker", "docker"),
    ("wsl -d podman -- docker", "docker"),
    ("docker --context podman", "docker"),
    ("podman --connection docker", "podman"),
])
def test_git_pointer_binding_preserves_runtime_transport(tmp_path, runtime, expected):
    """@brief Each supported runtime keeps the same pointer and unset contract.
    @param[in] tmp_path Isolated IO root.
    @param[in] runtime Supported native or WSL runtime prefix.
    @param[in] expected Container CLI dialect.
    """
    runner = FakeRunner(
        CommandResult(exit_code=1, stderr="No such container: c"),
        CommandResult(stdout="created"),
        CommandResult(stdout="adore-git-binding-v1\n"),
    )
    manager = ContainerManager(runtime, "test-image", "uv", "npm", runner)
    manager.provision("c", tmp_path / "repo", tmp_path / "work", tmp_path / "io",
                      build_container_env("run-1", "Bot", "bot@example.test"))
    argv = runner.calls[1]
    assert any(part.endswith(":/adore/work/.git:ro") for part in argv)
    assert argv[:len(manager.runtime_argv)] == manager.runtime_argv
    for key in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE"):
        assert ("--unsetenv" if expected == "podman" else "--env") in argv
        assert key in argv
        assert not any(part.startswith(key + "=") for part in argv)
    assert ("--unsetenv" in argv) == (expected == "podman")


@pytest.mark.parametrize("value", [
    "", "/foreign/worktrees/x", "/adore/repo/.git/worktrees/../x",
    "/adore/repo/.git/worktrees/x/y", "/adore/repo/.git/worktrees/x\\y",
    "/adore/repo/.git/worktrees/x\nother", "/adore/repo/.git/worktrees/..",
    "/adore/repo/.git/worktrees/x\x85other",
    None, 42,
])
def test_git_binding_rejects_invalid_admin_metadata(tmp_path, value):
    """@brief Malformed Git metadata cannot admit a new resource.
    @param[in] tmp_path Isolated IO root.
    @param[in] value Corrupt external metadata.
    """
    runner = FakeRunner(
        CommandResult(exit_code=1, stderr="No such container: c"),
        CommandResult(stdout="created"),
    )
    manager = ContainerManager("docker", "test-image", "uv", "npm", runner)
    env = build_container_env("run-1", "Bot", "bot@example.test")
    env["GIT_DIR"] = value
    with pytest.raises(IsolationError):
        manager.provision("c", tmp_path / "repo", tmp_path / "work", tmp_path / "io", env)
    assert not any("run" in call for call in runner.calls)


@pytest.mark.parametrize("key,value", [
    ("GIT_COMMON_DIR", "/foreign"), ("GIT_WORK_TREE", "/foreign"),
])
def test_git_binding_rejects_contradictory_mount_metadata(tmp_path, key, value):
    """@brief Metadata agrees with the managed mounts before resource creation.
    @param[in] tmp_path Isolated IO root.
    @param[in] key Contradictory selection field.
    @param[in] value Foreign mount path.
    """
    runner = FakeRunner(CommandResult(exit_code=1, stderr="No such container: c"),
                        CommandResult(stdout="created"))
    manager = ContainerManager("docker", "test-image", "uv", "npm", runner)
    env = build_container_env("run-1", "Bot", "bot@example.test")
    env[key] = value
    with pytest.raises(IsolationError):
        manager.provision("c", tmp_path / "repo", tmp_path / "work", tmp_path / "io", env)
    assert not any("run" in call for call in runner.calls)


@pytest.mark.parametrize("kind", ["wrong-bytes", "directory"])
def test_git_binding_preserves_and_rejects_corrupt_pointer(tmp_path, kind):
    """@brief Existing corrupt binding evidence is rejected without overwrite.
    @param[in] tmp_path Isolated IO root.
    @param[in] kind Invalid filesystem evidence.
    """
    io = tmp_path / "io"
    io.mkdir()
    pointer = io / "container.git"
    if kind == "directory":
        pointer.mkdir()
    else:
        pointer.write_bytes(b"gitdir: /foreign\n")
    runner = FakeRunner(CommandResult(exit_code=1, stderr="No such container: c"),
                        CommandResult(stdout="created"))
    manager = ContainerManager("docker", "test-image", "uv", "npm", runner)
    with pytest.raises(IsolationError):
        manager.provision("c", tmp_path / "repo", tmp_path / "work", io,
                          build_container_env("run-1", "Bot", "bot@example.test"))
    assert not any("run" in call for call in runner.calls)
    if kind == "wrong-bytes":
        assert pointer.read_bytes() == b"gitdir: /foreign\n"


def test_git_binding_rejects_link_evidence_before_open(tmp_path, monkeypatch):
    """@brief A filesystem-reported link is rejected before admission on every host.
    @param[in] tmp_path Isolated IO root.
    @param[in] monkeypatch Inject link metadata without Windows symlink privileges.
    """
    io = tmp_path / "io"
    io.mkdir()
    pointer = io / "container.git"
    pointer.write_bytes(b"gitdir: /adore/repo/.git/worktrees/run-1\n")
    original = Path.lstat

    def linked(path, *args, **kwargs):
        """@brief Supply a link-mode filesystem receipt for the one boundary file.
        @param[in] path Requested filesystem path.
        @return Native stat result with the injected link type where selected.
        """
        result = original(path, *args, **kwargs)
        if Path(path) == pointer:
            fields = list(result)
            fields[0] = stat.S_IFLNK | 0o777
            return os.stat_result(fields)
        return result

    monkeypatch.setattr(Path, "lstat", linked)
    runner = FakeRunner(CommandResult(exit_code=1, stderr="No such container: c"))
    manager = ContainerManager("docker", "test-image", "uv", "npm", runner)
    with pytest.raises(IsolationError):
        manager.provision("c", tmp_path / "repo", tmp_path / "work", io,
                          build_container_env("run-1", "Bot", "bot@example.test"))
    assert not any("run" in call for call in runner.calls)


@pytest.mark.parametrize("status", ["running", "exited"])
@pytest.mark.parametrize("mode", ["legacy", "pointer"])
def test_git_binding_warm_reuse_preserves_creation_mode(tmp_path, status, mode):
    """@brief Warm recovery preserves exact resources and validates new-mode evidence.
    @param[in] tmp_path Isolated IO root.
    @param[in] status Observed owned resource state.
    @param[in] mode Existing creation-time binding mode.
    """
    io = tmp_path / "io"
    io.mkdir()
    if mode == "pointer":
        (io / "container.git").write_bytes(b"gitdir: /adore/repo/.git/worktrees/run-1\n")
    replies = [CommandResult(stdout=status), CommandResult(
        stdout='"pointer-v1"' if mode == "pointer" else '""')]
    if status == "exited":
        replies.append(CommandResult())
    if mode == "pointer":
        replies.append(CommandResult(stdout="adore-git-binding-v1\n"))
    runner = FakeRunner(*replies)
    manager = ContainerManager("docker", "test-image", "uv", "npm", runner)

    runner.results.insert(2, owned_container_receipt(
        manager, "c", tmp_path / "repo", tmp_path / "work", io))
    assert manager.provision("c", tmp_path / "repo", tmp_path / "work", io,
                             build_container_env("run-1", "Bot", "bot@example.test")) == (
        "running" if status == "running" else "started")
    assert not any("run" in call or "rm" in call for call in runner.calls)
    assert any("start" in call for call in runner.calls) == (status == "exited")
    assert any("exec" in call for call in runner.calls) == (mode == "pointer")
    assert any("io.ddp.adore.git-binding" in part for call in runner.calls for part in call)


@pytest.mark.parametrize("reply", [
    CommandResult(stdout="garbage"), CommandResult(stdout="true"),
    CommandResult(stdout='"unknown"'), CommandResult(stdout='"' + "x" * 1100 + '"'),
    CommandResult(exit_code=1, stderr="denied"), CommandResult(timed_out=True),
])
def test_git_binding_reuse_rejects_untrusted_mode_receipts(tmp_path, reply):
    """@brief Corrupt or failed inspect data cannot downgrade to historical mode.
    @param[in] tmp_path Isolated IO root.
    @param[in] reply Untrusted CLI receipt.
    """
    runner = FakeRunner(CommandResult(stdout="running"), reply)
    manager = ContainerManager("docker", "test-image", "uv", "npm", runner)
    with pytest.raises(IsolationError):
        manager.provision("c", tmp_path / "repo", tmp_path / "work", tmp_path / "io",
                          build_container_env("run-1", "Bot", "bot@example.test"))
    assert not any("start" in call or "run" in call or "exec" in call for call in runner.calls)


@pytest.mark.parametrize("reply", [
    CommandResult(stdout="wrong"), CommandResult(exit_code=1),
    CommandResult(stdout="adore-git-binding-v1\n", timed_out=True),
])
def test_git_binding_requires_exact_runtime_confirmation(tmp_path, reply):
    """@brief Fresh binding is admitted only after a successful exact runtime receipt.
    @param[in] tmp_path Isolated IO root.
    @param[in] reply Failed or contradictory environment/native-Git confirmation.
    """
    runner = FakeRunner(CommandResult(exit_code=1, stderr="No such container: c"),
                        CommandResult(stdout="created"), reply)
    manager = ContainerManager("docker", "test-image", "uv", "npm", runner)
    with pytest.raises(IsolationError):
        manager.provision("c", tmp_path / "repo", tmp_path / "work", tmp_path / "io",
                          build_container_env("run-1", "Bot", "bot@example.test"))


def test_git_binding_new_mode_requires_saved_pointer_before_start(tmp_path):
    """@brief Missing mounted-mode data is corruption, never a legacy fallback.
    @param[in] tmp_path Isolated IO root without saved pointer evidence.
    """
    runner = FakeRunner(CommandResult(stdout="exited"), CommandResult(stdout='"pointer-v1"'),
                        CommandResult())
    manager = ContainerManager("docker", "test-image", "uv", "npm", runner)
    with pytest.raises(IsolationError):
        manager.provision("c", tmp_path / "repo", tmp_path / "work", tmp_path / "io",
                          build_container_env("run-1", "Bot", "bot@example.test"))
    assert not any("start" in call for call in runner.calls)


# END OF FILE
