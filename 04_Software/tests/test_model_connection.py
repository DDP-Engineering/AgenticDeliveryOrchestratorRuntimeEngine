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
@file test_model_connection.py
@brief Explicit all-executor model connection contracts.
@details External command output is faked and never returned to the browser.
"""

import contextlib
import importlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys

from adore.config import load_config
from adore.profiles import ProfileStore
from adore.util import CommandResult
from adore.web.model_connection import probe_model_connection
from fastapi.testclient import TestClient
import pytest


def project(tmp_path, provider="gitlab", kind="opencode"):
    """@brief Create an offline project with real API identity/config storage."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha", store_root=str(tmp_path / "state"))
    path = profiles.config_path("alpha")
    raw = (Path(__file__).resolve().parents[1] / "config.example.toml").read_text()
    raw = raw.replace('store_root = ".adore"', f'store_root = "{(tmp_path / "state").as_posix()}"')
    raw = raw.replace('repo = "group/subgroup/project"', 'repo = "mygroup/myproject"')
    raw = raw.replace('kind = "gitlab"', f'kind = "{provider}"')
    raw = raw.replace('default = "opencode"', f'default = "{kind}"')
    if kind != "opencode":
        raw = raw.replace(f"# [executor.{kind}]", f"[executor.{kind}]")
        lines = raw.splitlines()
        start = lines.index(f"[executor.{kind}]")
        for index in (start + 1, start + 2):
            lines[index] = lines[index].removeprefix("# ")
        raw = "\n".join(lines)
    path.write_text(raw, encoding="utf-8")
    return profiles


@pytest.mark.parametrize("kind", ["opencode", "pi", "codex", "qwen"])
def test_explicit_model_test_returns_scoped_evidence(tmp_path, monkeypatch, kind):
    """@brief Only explicit requests run the selected model probe."""
    module = importlib.import_module("adore.web.app")
    profiles = project(tmp_path, kind=kind)
    calls = []

    def probe(config, runner, env_file):
        """@brief Fake one external model call without a paid provider."""
        assert config.executor.default == kind
        calls.append(env_file)
        return {"ready": True, "reason": "ready", "executor": kind, "model": "test-model"}

    monkeypatch.setattr(module, "probe_model_connection", probe, raising=False)
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        result = client.post(
            "/api/v1/projects/alpha/model-connection-test", headers={"X-CSRF-Token": csrf}
        )
        assert result.status_code == 200
        assert result.json()["project_id"] == profiles.load("alpha").project_id
        assert result.json()["executor"] == kind and result.json()["ready"] is True
        assert len(calls) == 1


@pytest.mark.parametrize("mode", ["anonymous", "csrf", "developer", "locked", "corrupt", "stale"])
def test_model_test_rejects_trust_boundary(tmp_path, monkeypatch, mode):
    """@brief Untrusted requests/state cannot initiate or retain model evidence."""
    module = importlib.import_module("adore.web.app")
    profiles = project(tmp_path)
    calls = []

    def probe(config, runner, env_file):
        """@brief Simulate concurrent configuration drift after the request."""
        calls.append(True)
        if mode == "stale":
            path = profiles.config_path("alpha")
            path.write_text(path.read_text() + "\n# changed\n")
        return {"ready": True, "reason": "ready", "executor": "opencode", "model": "test"}

    monkeypatch.setattr(module, "probe_model_connection", probe)
    app = module.create_app(profiles.home)
    if mode == "developer":
        dev = app.state.web_store.create_user("dev", "longer-password", "developer")
        app.state.web_store.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        if mode == "developer":
            client.cookies.clear()
            csrf = client.post(
                "/api/v1/session", json={"username": "dev", "password": "longer-password"}
            ).json()["csrf"]
        if mode == "anonymous":
            client.cookies.clear()
        if mode == "corrupt":
            profiles.config_path("alpha").write_text("corrupt [")
        if mode == "locked":
            from adore.state import StateStore

            store = StateStore(tmp_path / "state")
            store.acquire_lock()
        try:
            response = client.post(
                "/api/v1/projects/alpha/model-connection-test",
                headers={} if mode == "csrf" else {"X-CSRF-Token": csrf},
            )
            assert response.status_code in (401, 403, 409, 503)
            assert len(calls) == (1 if mode == "stale" else 0)
        finally:
            if mode == "locked":
                store.release_lock()


@pytest.mark.parametrize("kind", ["opencode", "pi", "codex", "qwen"])
@pytest.mark.parametrize("invalid", [False, True, "wrong-nonce", "tool"])
def test_public_probe_challenge_protocol_and_cleanup(tmp_path, monkeypatch, kind, invalid):
    """@brief Run the actual diagnostic script with fake CLI responses offline."""
    profiles = project(tmp_path, kind=kind)
    config = load_config(profiles.config_path("alpha"))
    calls, roots, cli = [], [], []

    class Process:
        """@brief Write only fake protocol output to the subprocess capture files."""

        returncode = 0

        def __init__(self, argv, **kwargs):
            cli.append(argv)
            nonce = argv[-1].split()[-1]
            if invalid == "wrong-nonce":
                nonce = "wrong"
            if kind == "qwen":
                events = [
                    {"type": "result", "result": nonce, "subtype": "success", "is_error": False}
                ]
            elif kind == "pi":
                events = [
                    {
                        "type": "message_end",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "text", "text": nonce}],
                            "stopReason": "stop",
                        },
                    }
                ]
            elif kind == "codex":
                events = [
                    {"type": "item.completed", "item": {"type": "agent_message", "text": nonce}},
                    {"type": "turn.completed"},
                ]
            else:
                events = [
                    {"type": "text", "part": {"text": nonce}},
                    {"type": "step_finish", "part": {"reason": "stop"}},
                ]
            if invalid == "tool":
                events.append({"type": "tool_use"})
            raw = json.dumps(events) if kind == "qwen" else "\n".join(json.dumps(e) for e in events)
            kwargs["stdout"].write(("invalid secret-value" if invalid is True else raw).encode())

        def poll(self):
            """@brief The fake process has completed."""
            return 0

    monkeypatch.setattr(subprocess, "Popen", Process)
    monkeypatch.setattr(shutil, "which", lambda value: value)

    def runner(argv, **kwargs):
        """@brief Simulate the runtime and execute its mounted script in isolation."""
        calls.append((argv, kwargs))
        if "inspect" in argv and "image" not in argv:
            return CommandResult(argv, 1, stderr="No such container")
        if "run" in argv:
            mounts = [arg for arg in argv if ":/adore/io" in arg]
            root = Path(mounts[0].split(":/adore/io")[0])
            roots.append(root)
        if "/adore/io/probe.py" in argv:
            index = argv.index("/adore/io/probe.py")
            monkeypatch.setattr(sys, "argv", argv[index:])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(compile((roots[0] / "probe.py").read_text(), "probe.py", "exec"), {})
            return CommandResult(argv, stdout=output.getvalue())
        return CommandResult(argv)

    result = probe_model_connection(config, runner, profiles.profile_dir("alpha") / ".env")
    assert result["ready"] is (not invalid)
    assert result["reason"] == ("invalid-response" if invalid else "ready")
    assert "secret-value" not in json.dumps(result)
    assert cli[0][0] == kind
    assert any("rm" in argv for argv, _ in calls)
    assert all(not root.exists() for root in roots)
    assert all("pull" not in argv for argv, _ in calls)


@pytest.mark.parametrize(
    "output",
    [
        '{"ready":true,"ready":false,"reason":"ready"}',
        '{"ready":true,"reason":"timeout"}',
        "secret-value",
    ],
)
def test_external_envelope_fails_closed(tmp_path, output):
    """@brief Duplicate, contradictory and non-JSON runtime data fails closed."""
    profiles = project(tmp_path)
    calls = []

    def runner(argv, **kwargs):
        """@brief Fake an untrusted runtime envelope."""
        calls.append(argv)
        if "inspect" in argv and "image" not in argv:
            return CommandResult(argv, 1, stderr="No such container")
        return CommandResult(argv, stdout=output if "/adore/io/probe.py" in argv else "")

    result = probe_model_connection(
        load_config(profiles.config_path("alpha")), runner, profiles.profile_dir("alpha") / ".env"
    )
    assert result["reason"] == "invalid-response" and result["ready"] is False
    assert any("rm" in argv for argv in calls)


def test_wrapper_timeout_releases_container(tmp_path):
    """@brief Runtime timeout remains bounded and always attempts resource cleanup."""
    profiles = project(tmp_path)
    calls = []

    def runner(argv, **kwargs):
        """@brief Time out the inference command only."""
        calls.append(argv)
        if "inspect" in argv and "image" not in argv:
            return CommandResult(argv, 1, stderr="No such container")
        return CommandResult(argv, timed_out="/adore/io/probe.py" in argv)

    result = probe_model_connection(
        load_config(profiles.config_path("alpha")), runner, profiles.profile_dir("alpha") / ".env"
    )
    assert result["reason"] == "timeout"
    assert any("rm" in argv for argv in calls)


@pytest.mark.parametrize("mode", ["secrets", "image", "cleanup"])
def test_environment_selection_and_runtime_failure(tmp_path, monkeypatch, mode):
    """@brief Secrets use the selected profile and remain outside command arguments."""
    profiles = project(tmp_path)
    env_file = profiles.profile_dir("alpha") / ".env"
    env_file.write_text("OPENAI_API_KEY=selected-private-key\nGITEA_TOKEN=forge-private-key\n")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    calls = []

    def runner(argv, **kwargs):
        """@brief Observe safe env names and fake setup/cleanup failure."""
        calls.append((argv, kwargs))
        if "image" in argv and mode == "image":
            return CommandResult(argv, 1)
        if "inspect" in argv and "image" not in argv:
            if mode == "cleanup" and any("rm" in previous for previous, _ in calls):
                return CommandResult(argv, stdout="running")
            return CommandResult(argv, 1, stderr="No such container")
        if "rm" in argv and mode == "cleanup":
            return CommandResult(argv, 1, stderr="permission denied secret")
        return CommandResult(argv, stdout='{"ready":true,"reason":"ready"}')

    config = load_config(profiles.config_path("alpha"))
    if mode == "cleanup":
        from adore.isolation import IsolationError

        with pytest.raises(IsolationError):
            probe_model_connection(config, runner, env_file)
        return
    result = probe_model_connection(config, runner, env_file)
    assert result["reason"] == ("image-missing" if mode == "image" else "ready")
    assert all("selected-private-key" not in " ".join(argv) for argv, _ in calls)
    if mode == "secrets":
        invocation = next(kwargs for argv, kwargs in calls if "/adore/io/probe.py" in argv)
        assert invocation["env"]["OPENAI_API_KEY"] == "selected-private-key"
        assert "GITEA_TOKEN" not in invocation["env"]
    else:
        assert not any("run" in argv for argv, _ in calls)
