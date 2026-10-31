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
@file    test_executor_discovery.py
@brief   Installed native executor discovery and HTTP authority boundaries.
@details Offline filesystem fixtures exercise host installations without running
         a CLI, reading credentials or using external services.
"""

from __future__ import annotations

# IMPORTS
import os
from pathlib import Path

from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest


# LOCAL HELPERS
def installed(path: Path) -> Path:
    """@brief Create an executable fixture that must never be run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("DO NOT EXECUTE", encoding="utf-8")
    path.chmod(0o755)
    return path


# PUBLIC CONTRACT TESTS
def test_detected_account_uses_process_identity_not_environment(tmp_path, monkeypatch):
    """@brief The displayed account identifies the process, not a shell environment label."""
    from adore.executor_discovery import discover_executors
    from adore.local_process import native_context

    actual = native_context()
    for key in ("LOGNAME", "USER", "LNAME", "USERNAME"):
        monkeypatch.setenv(key, "not-the-process-account")
    result = discover_executors(environment={"PATH": ""}, home=tmp_path, excluded=())
    assert result["account"] == actual["account"]
    assert result["machine"] == actual["machine"]


def test_admin_discovers_host_executors_without_running_commands(tmp_path, monkeypatch):
    """@brief A native PATH installation becomes an absolute launch suggestion."""
    executable = installed(tmp_path / "bin" / ("opencode.exe" if os.name == "nt" else "opencode"))
    monkeypatch.setenv("PATH", str(executable.parent))
    monkeypatch.setenv("HOME", str(tmp_path / "account"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "account"))

    def no_commands(*_args, **_kwargs):
        raise AssertionError("Discovery must not execute tools")

    app = create_app(tmp_path / "adore-home", probe_runner=no_commands)
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        assert login.status_code == 200
        response = client.get("/api/v1/local-executors")
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["system"] in {"Windows", "Linux"}
        assert result["machine"] and result["account"]
        choices = next(
            item["installations"] for item in result["executors"] if item["agent"] == "opencode"
        )
        assert any(item["executable"] == str(executable.resolve()) for item in choices)
        assert all("{prompt}" in item["command"] for item in choices)
        assert response.headers["cache-control"] == "no-store"


def test_executor_discovery_requires_administrator(tmp_path):
    """@brief Filesystem paths are unavailable to anonymous users or developers."""
    app = create_app(tmp_path / "home")
    app.state.web_store.create_user("dev", "longer-password", "developer")
    with TestClient(app) as client:
        assert client.get("/api/v1/local-executors").status_code == 401
        client.post("/api/v1/session", json={"username": "dev", "password": "longer-password"})
        assert client.get("/api/v1/local-executors").status_code == 403


def test_unavailable_native_identity_does_not_guess_an_account(tmp_path, monkeypatch):
    """@brief An unreadable native identity returns explicit unavailable detection."""
    from adore.local_process import LocalExecutionError

    def unavailable():
        raise LocalExecutionError("private identity failure")
    monkeypatch.setattr("adore.executor_discovery.native_context", unavailable)
    with TestClient(create_app(tmp_path / "home")) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/local-executors")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "local_host_identity_unavailable"
        assert "private identity failure" not in response.text


@pytest.mark.parametrize("system", ["Windows", "Linux"])
def test_native_and_npm_installations_are_detected_and_deduplicated(tmp_path, system):
    """@brief Native and Node/JS choices use existing files with normal arguments."""
    from adore.executor_discovery import discover_executors

    if system == "Linux" and os.name == "nt":
        pytest.skip("Unix PATH and executable permissions are exercised natively on Linux")
    binary = tmp_path / "installed tools"
    suffix = ".exe" if system == "Windows" else ""
    installed(binary / ("node" + suffix))
    native = installed(binary / ("opencode" + suffix))
    script = installed(binary / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js")
    separator = ";" if system == "Windows" else ":"
    result = discover_executors(
        system=system,
        environment={"PATH": separator.join([str(binary)] * 3)},
        home=tmp_path / "account",
        excluded=(),
    )
    records = {item["agent"]: item["installations"] for item in result["executors"]}
    assert len([item for item in records["opencode"] if item["executable"] == str(native)]) == 1
    assert any(
        item["entrypoint"] == str(script) and '"' in item["command"] for item in records["pi"]
    )


def test_windows_npm_opencode_uses_real_binary_and_not_shell_shims(tmp_path):
    """@brief npm executable wrappers never become launch authority."""
    from adore.executor_discovery import discover_executors

    root = tmp_path / "npm"
    installed(root / "opencode.cmd")
    installed(root / "pi.ps1")
    native = installed(root / "node_modules/opencode-ai/bin/opencode.exe")
    result = discover_executors(
        system="Windows", environment={"PATH": str(root)}, home=tmp_path / "account", excluded=()
    )
    choices = result["executors"][0]["installations"]
    assert choices == [
        {
            "executable": str(native),
            "entrypoint": None,
            "source": "npm",
            "command": (f'"{native.as_posix()}" run --dir {{worktree}} '
                        '-m {model} --format json {prompt}'),
        }
    ]
    assert result["executors"][1]["installations"] == []


@pytest.mark.parametrize("case", ["relative", "excluded", "checkout", "missing", "unsafe_name"])
def test_unsafe_or_unavailable_installations_are_omitted(tmp_path, monkeypatch, case):
    """@brief Only installed native files outside project trees may be proposed."""
    from adore.executor_discovery import discover_executors

    directory = tmp_path / ('bad"name' if case == "unsafe_name" and os.name != "nt" else "bin")
    if case == "unsafe_name" and os.name == "nt":
        directory = tmp_path / "bad{prompt}name"
    if case != "missing":
        installed(directory / "opencode.exe")
    if case == "checkout":
        (directory / ".git").mkdir()
    if case == "relative":
        monkeypatch.chdir(tmp_path)
    result = discover_executors(
        system="Windows",
        environment={"PATH": "bin" if case == "relative" else str(directory)},
        home=tmp_path / "account",
        excluded=(directory,) if case == "excluded" else (),
    )
    assert all(not item["installations"] for item in result["executors"])


def test_non_executable_linux_files_and_missing_node_are_omitted(tmp_path):
    """@brief A JS file alone and a non-executable Unix binary are not installations."""
    from adore.executor_discovery import discover_executors

    root = tmp_path / "bin"
    binary = installed(root / "opencode")
    binary.chmod(0o644)
    installed(root / "node_modules/@openai/codex/bin/codex.js")
    result = discover_executors(
        system="Linux", environment={"PATH": str(root)}, home=tmp_path / "home", excluded=()
    )
    if os.name != "nt":
        assert not any(
            item["executable"] == str(binary) for item in result["executors"][0]["installations"]
        )
    assert not any(item["entrypoint"] for item in result["executors"][2]["installations"])


def test_discovery_is_bounded_and_does_not_export_environment_values(tmp_path):
    """@brief Oversized PATH and provider variables never escape the bounded listing."""
    from adore.executor_discovery import discover_executors

    roots = [installed(tmp_path / str(index) / "opencode.exe").parent for index in range(75)]
    result = discover_executors(
        system="Windows",
        environment={"PATH": ";".join(map(str, roots)), "OPENAI_API_KEY": "secret-fixture"},
        home=tmp_path / "home",
        excluded=(),
    )
    assert len(result["executors"][0]["installations"]) == 12
    assert "secret-fixture" not in str(result)


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlinks tested natively on Linux")
def test_project_symlink_and_shell_alias_are_not_discovered(tmp_path):
    """@brief Resolving a link cannot turn a project PATH entry into installed authority."""
    from adore.executor_discovery import discover_executors

    actual = installed(tmp_path / "installed/opencode")
    project = tmp_path / "project"
    (project / ".git").mkdir(parents=True)
    (project / "opencode").symlink_to(actual)
    result = discover_executors(system="Linux", environment={"PATH": str(project)},
                                home=tmp_path / "home", excluded=())
    assert all(not record["installations"] for record in result["executors"])
    shell = installed(tmp_path / "native/sh")
    alias = tmp_path / "bin/opencode"
    alias.parent.mkdir()
    alias.symlink_to(shell)
    result = discover_executors(system="Linux", environment={"PATH": str(alias.parent)},
                                home=tmp_path / "home", excluded=())
    assert all(not record["installations"] for record in result["executors"])


# END OF FILE
