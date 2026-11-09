#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_execution.py
@brief   Shared execution identity and bounded preparation file contracts.
@details All command/process boundaries are injected and remain offline.
"""

# IMPORTS
import io
import json
from pathlib import Path
import subprocess

from adore import preparation_runner
from adore.execution import ExecutionPaths, redact_output, run_preparation_step
from adore.isolation import ContainerManager, IsolationError
from adore.util import CommandResult
import pytest

# PUBLIC API / TESTS


def test_transport_rejects_linked_parents_before_creating_files(tmp_path, monkeypatch):
    """@brief Linked executor-controlled parents cannot cause host-side writes."""
    original = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink", lambda path: path == tmp_path / "preparation" or original(path)
    )
    with pytest.raises(IsolationError):
        run_preparation_step(
            None, tmp_path, 1, 0, {"name": "setup", "run": "true"}, timeout=1, secrets={}
        )
    assert not (tmp_path / "preparation").exists()


def test_preparation_runner_uses_file_transport_and_authoritative_result(tmp_path):
    """@brief Multiline scripts are files with bounded redacted evidence."""

    class Target:
        """@brief Fake target writes the file protocol through mounted IO."""

        paths = ExecutionPaths()

        def __call__(self, argv, **kwargs):
            assert len(argv) == 5 and "echo" not in " ".join(argv)
            directory = tmp_path / "preparation/attempt-1/step-1"
            assert (directory / "run.sh").read_text().endswith('echo "space path"\necho done\n')
            (directory / "stdout.txt").write_text("secret-value " + "x" * 70000)
            (directory / "stderr.txt").write_text("")
            (directory / "result.json").write_text('{"exit_code":0,"timed_out":false}')
            return CommandResult()

    result = run_preparation_step(
        Target(),
        tmp_path,
        1,
        0,
        {"name": "setup", "run": 'echo "space path"\necho done'},
        timeout=10,
        secrets={"MODEL_KEY": "secret-value"},
    )
    assert result["exit_code"] == 0 and not result["timed_out"]
    assert "secret-value" not in result["stdout"]
    assert len(result["stdout"].encode()) <= 65536


def test_container_identity_reports_actual_container_and_image_ids():
    """@brief Authoritative inspect IDs govern resource identity."""
    manager = ContainerManager(
        "docker",
        "project:1",
        "uv",
        "npm",
        runner=lambda *args, **kwargs: CommandResult(
            stdout=json.dumps(
                [
                    {
                        "Id": "a" * 64,
                        "Image": "sha256:" + "b" * 64,
                        "Name": "/owned-run",
                        "State": {"Status": "running"},
                    }
                ]
            )
        ),
    )
    identity = manager.resource_identity("owned-run")
    assert identity["container_id"] == "a" * 64
    assert identity["image_id"] == "sha256:" + "b" * 64


@pytest.mark.parametrize(
    "output",
    [
        "",
        "{}",
        "[{}]",
        "null",
        "[1]",
        '[{"Id":"short","Image":"x","Name":"/other","State":{"Status":"running"}}]',
        '[{"Id":"short","Id":"other"}]',
    ],
)
def test_container_identity_rejects_corrupt_or_foreign_resources(output):
    """@brief Malformed or duplicate inspect values cannot authorize a target."""
    manager = ContainerManager(
        "podman",
        "project:1",
        "uv",
        "npm",
        runner=lambda *args, **kwargs: CommandResult(stdout=output),
    )
    with pytest.raises(IsolationError):
        manager.resource_identity("owned-run")


@pytest.mark.parametrize("mode", ["ok", "exit124", "timeout"])
def test_standalone_preparation_runner_bounds_output_and_process_lifetime(
    tmp_path, monkeypatch, mode
):
    """@brief File runner bounds retention and distinguishes shell exit from timeout."""
    secret = "secret-" + "z" * 200
    monkeypatch.setenv("MODEL_KEY", secret)
    (tmp_path / "secret-keys.json").write_text('["MODEL_KEY"]')
    calls = []

    class Process:
        """@brief Fake pipes exercise redaction without launching a command."""

        pid = 123
        stdout = io.BytesIO(("x" * 4090 + secret + "\U0001f600" * 40000).encode())
        stderr = io.BytesIO(b"bounded stderr")
        waited = False

        def wait(self, timeout=None):
            if mode == "timeout" and not self.waited:
                self.waited = True
                raise subprocess.TimeoutExpired("sh", timeout)
            return 124 if mode == "exit124" else 0

    def start(argv, **kwargs):
        assert argv == ["sh", "-eu", str(tmp_path / "run.sh")]
        assert kwargs["cwd"] == "worktree with spaces" and kwargs["start_new_session"]
        return Process()

    monkeypatch.setattr(preparation_runner.signal, "SIGKILL", 9, raising=False)
    monkeypatch.setattr(preparation_runner.subprocess, "Popen", start)
    monkeypatch.setattr(
        preparation_runner.os, "killpg", lambda *args: calls.append(args), raising=False
    )
    assert preparation_runner.main(["1", str(tmp_path), "worktree with spaces"]) == (
        0 if mode == "ok" else 124
    )
    record = json.loads((tmp_path / "result.json").read_text())
    assert record["timed_out"] == (mode == "timeout")
    assert secret.encode() not in (tmp_path / "stdout.txt").read_bytes()
    assert (tmp_path / "stdout.txt").stat().st_size <= 65536
    assert calls


def test_bound_target_spawn_verifies_identity_and_merges_env():
    """@brief Streaming spawn checks the pinned container first and adds the extra env."""
    from adore.execution import BoundTarget, ContainerBackend, ExecutionRecoveryError

    calls = []

    class Manager:
        def spawn(self, name, argv, *, env=None):
            calls.append(("spawn", name, list(argv), dict(env)))
            return "process"

    backend = ContainerBackend(Manager())
    backend._admit_command = lambda name, expected: (
        calls.append(("verify", name, expected, True)) or {"container_id": "id"})
    target = BoundTarget(backend, "c", {"OPENAI_API_KEY": "k", "HOME": "/h"}, {"pinned": 1})
    assert target.spawn(["node", "cli.js"], env={"PI_OFFLINE": "1"}) == "process"
    assert calls == [
        ("verify", "c", {"pinned": 1}, True),
        ("spawn", "id", ["node", "cli.js"],
         {"OPENAI_API_KEY": "k", "HOME": "/h", "PI_OFFLINE": "1"}),
    ]

    def refuse(name, expected, running=False):
        raise ExecutionRecoveryError("execution resource identity changed")

    backend._admit_command = refuse
    calls.clear()
    with pytest.raises(ExecutionRecoveryError):
        target.spawn(["node"])
    assert calls == []


def test_redacted_unicode_output_respects_byte_limit():
    """@brief Multibyte truncation never exceeds the retained UTF-8 byte limit."""
    assert len(redact_output("\U0001f600" * 20000, {}).encode()) <= 65536


# END OF FILE
