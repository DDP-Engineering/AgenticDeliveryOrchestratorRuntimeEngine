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
@file test_executor_settings.py
@brief Project executor credential and durable evidence contracts.
@details External command output is faked and never returned to the browser.
"""

from hashlib import sha256
import importlib
import json

from adore.state import StateStore
from fastapi.testclient import TestClient
import pytest

from tests.test_model_connection import project


@pytest.mark.parametrize("kind", ["opencode", "pi", "codex", "qwen"])
def test_provider_credentials_are_private_scoped_and_reversible(tmp_path, monkeypatch, kind):
    """@brief Save only an approved variable used by real executor environment injection."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    profiles = project(tmp_path, kind=kind)
    StateStore(tmp_path / "state").pause()
    env = profiles.profile_dir("alpha") / ".env"
    env.write_text("# retained\nANTHROPIC_API_KEY=other-private\n", encoding="utf-8")
    module = importlib.import_module("adore.web.app")
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        headers = {"X-CSRF-Token": csrf}
        payload = {
            "variable": "OPENAI_API_KEY",
            "token": "private-provider-key",
            "revision": revision,
        }
        result = client.put(
            "/api/v1/projects/alpha/executor-credentials", json=payload, headers=headers
        )
        assert result.status_code == 200
        assert "private-provider-key" not in result.text
        assert "OPENAI_API_KEY=private-provider-key" in env.read_text(encoding="utf-8")
        assert "ANTHROPIC_API_KEY=other-private" in env.read_text(encoding="utf-8")
        assert client.get("/api/v1/projects/alpha/executor-credentials").json()["variables"][0][
            "source"
        ] in ("project", "missing")
        result = client.request(
            "DELETE",
            "/api/v1/projects/alpha/executor-credentials",
            json={"variable": "OPENAI_API_KEY", "revision": revision},
            headers=headers,
        )
        assert result.status_code == 200
        assert "OPENAI_API_KEY=" not in env.read_text(encoding="utf-8")
        assert "other-private" in env.read_text(encoding="utf-8")
        assert "private-provider-key" not in client.get("/api/v1/projects/alpha/config").text


@pytest.mark.parametrize(
    "mode",
    [
        "csrf",
        "developer",
        "stale",
        "variable",
        "token",
        "corrupt-env",
        "duplicate-env",
        "locked",
        "pending",
        "corrupt-evidence",
        "unpaused",
        "ambient",
        "ambient-empty",
    ],
)
def test_credential_boundary_preserves_original_bytes(tmp_path, monkeypatch, mode):
    """@brief Invalid requests or corrupt stored inputs never overwrite project credentials."""
    profiles = project(tmp_path)
    StateStore(tmp_path / "state").pause()
    env = profiles.profile_dir("alpha") / ".env"
    original = "OPENAI_API_KEY=retained-private\n"
    if mode == "corrupt-env":
        original += "malformed-line\n"
    if mode == "duplicate-env":
        original += "OPENAI_API_KEY=duplicate\n"
    env.write_text(original, encoding="utf-8")
    module = importlib.import_module("adore.web.app")
    app = module.create_app(profiles.home)
    if mode == "developer":
        user = app.state.web_store.create_user("dev", "longer-password", "developer")
        app.state.web_store.set_memberships(user["id"], ["alpha"])
    with TestClient(app) as client:
        username = "dev" if mode == "developer" else "admin"
        csrf = client.post(
            "/api/v1/session",
            json={
                "username": username,
                "password": "longer-password" if mode == "developer" else "admin",
            },
        ).json()["csrf"]
        revision = sha256(profiles.config_path("alpha").read_bytes()).hexdigest()
        if mode == "pending":
            client.post(
                "/api/v1/projects/alpha/config/pending",
                json={"key": "budgets.max_iterations", "value": "22", "revision": revision},
                headers={"X-CSRF-Token": csrf},
            )
        if mode == "corrupt-evidence":
            (env.parent / "model-connection.json").write_text("{broken", encoding="utf-8")
        store = StateStore(tmp_path / "state")
        if mode == "unpaused":
            store.resume()
        if mode in {"ambient", "ambient-empty"}:
            monkeypatch.setenv("OPENAI_API_KEY", "ambient-private" if mode == "ambient" else "")
        if mode == "locked":
            store.acquire_lock()
        try:
            result = client.put(
                "/api/v1/projects/alpha/executor-credentials",
                json={
                    "variable": "GITEA_TOKEN" if mode == "variable" else "OPENAI_API_KEY",
                    "token": "line\nbreak" if mode == "token" else "replacement-private",
                    "revision": "0" * 64 if mode == "stale" else revision,
                },
                headers={} if mode == "csrf" else {"X-CSRF-Token": csrf},
            )
            assert result.status_code in (400, 403, 409, 422, 503)
            assert env.read_text(encoding="utf-8") == original
            assert "replacement-private" not in result.text
        finally:
            if mode == "locked":
                store.release_lock()


def test_model_evidence_saves_and_returns_a_tool_call_failure(tmp_path, monkeypatch):
    """@brief A local agent that cannot run its shell call yields saved, readable evidence."""
    profiles = project(tmp_path, kind="pi")
    module = importlib.import_module("adore.web.app")
    from adore.config import load_config

    model = load_config(profiles.config_path("alpha")).executor.commands["pi"].model
    monkeypatch.setattr(
        module,
        "probe_model_connection",
        lambda *args: {"executor": "pi", "model": model, "ready": False,
                       "reason": "tool-call-failed"},
    )
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        result = client.post(
            "/api/v1/projects/alpha/model-connection-test", headers={"X-CSRF-Token": csrf}
        )
        assert result.status_code == 200
        assert (result.json()["ready"], result.json()["reason"]) == (False, "tool-call-failed")
        assert client.get("/api/v1/projects/alpha/config").json()["model_connection"] == (
            result.json()
        )


def test_model_evidence_survives_reload_and_invalidates_on_credentials(tmp_path, monkeypatch):
    """@brief A current explicit result survives host checks and credential drift hides it."""
    profiles = project(tmp_path, kind="pi")
    module = importlib.import_module("adore.web.app")
    from adore.config import load_config

    model = load_config(profiles.config_path("alpha")).executor.commands["pi"].model
    monkeypatch.setattr(
        module,
        "probe_model_connection",
        lambda *args: {"executor": "pi", "model": model, "ready": True, "reason": "ready"},
    )
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        result = client.post(
            "/api/v1/projects/alpha/model-connection-test", headers={"X-CSRF-Token": csrf}
        )
        assert result.status_code == 200
        config = client.get("/api/v1/projects/alpha/config").json()
        assert config.get("model_connection") == result.json()
        assert (profiles.profile_dir("alpha") / "model-connection.json").exists()
        monkeypatch.setattr(
            module,
            "_probe_setup",
            lambda *args: {
                "checks": {
                    "git": True,
                    "forge_cli": True,
                    "forge_auth": True,
                    "container_runtime": True,
                    "executor_cli": True,
                    "aegis_files": True,
                    "model_endpoint": "not-checked",
                },
                "model_probe": {
                    "context": "executor-container",
                    "ready": False,
                    "model": model,
                    "reason": "unsupported-executor",
                },
            },
        )
        assert (
            client.post(
                "/api/v1/projects/alpha/readiness-check", headers={"X-CSRF-Token": csrf}
            ).status_code
            == 200
        )
        assert (
            client.get("/api/v1/projects/alpha/config").json()["model_connection"] == result.json()
        )

        (profiles.profile_dir("alpha") / ".env").write_text(
            "OPENAI_API_KEY=changed-private\n", encoding="utf-8"
        )
        assert client.get("/api/v1/projects/alpha/config").json()["model_connection"] is None


@pytest.mark.parametrize(
    "mode", ["foreign", "duplicate", "invalid-reason", "invalid-time", "extra"]
)
def test_model_evidence_corruption_fails_closed(tmp_path, monkeypatch, mode):
    """@brief Stored records are validated before checking if they are stale."""
    profiles = project(tmp_path)
    module = importlib.import_module("adore.web.app")
    from adore.config import load_config

    model = load_config(profiles.config_path("alpha")).executor.commands["opencode"].model
    monkeypatch.setattr(
        module,
        "probe_model_connection",
        lambda *args: {"executor": "opencode", "model": model, "ready": True, "reason": "ready"},
    )
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        assert (
            client.post(
                "/api/v1/projects/alpha/model-connection-test", headers={"X-CSRF-Token": csrf}
            ).status_code
            == 200
        )
        path = profiles.profile_dir("alpha") / "model-connection.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        if mode == "foreign":
            value["project_id"] = "f" * 32
        if mode == "invalid-reason":
            value["reason"] = "timeout"
        if mode == "invalid-time":
            value["checked_at"] = "2000-01-01"
        if mode == "extra":
            value["token"] = "must-not-leak"
        raw = json.dumps(value)
        if mode == "duplicate":
            raw = raw[:-1] + ',"ready":false}'
        path.write_text(raw, encoding="utf-8")
        result = client.get("/api/v1/projects/alpha/config")
        assert result.status_code == 503
        assert "must-not-leak" not in result.text


def test_private_write_failure_preserves_credentials(tmp_path, monkeypatch):
    """@brief Failed atomic publication leaves prior key bytes and no temporary secret file."""
    profiles = project(tmp_path)
    StateStore(tmp_path / "state").pause()
    directory = profiles.profile_dir("alpha")
    path = directory / ".env"
    path.write_text("OPENAI_API_KEY=retained-private\n", encoding="utf-8")
    module = importlib.import_module("adore.web.app")
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]

        def fail(*args):
            """@brief Simulate the secret-file publication trust boundary."""
            raise OSError("private error")

        monkeypatch.setattr("adore.web.executor_settings.os.replace", fail)
        result = client.put(
            "/api/v1/projects/alpha/executor-credentials",
            json={
                "revision": sha256(profiles.config_path("alpha").read_bytes()).hexdigest(),
                "variable": "OPENAI_API_KEY",
                "token": "replacement-private",
            },
            headers={"X-CSRF-Token": csrf},
        )
        assert result.status_code == 503
        assert path.read_text(encoding="utf-8") == "OPENAI_API_KEY=retained-private\n"
        assert not list(directory.glob(".executor-*"))
        assert "private error" not in result.text


def test_credentials_changing_during_test_do_not_publish_evidence(tmp_path, monkeypatch):
    """@brief External credential drift during a diagnostic never records a current success."""
    profiles = project(tmp_path)
    module = importlib.import_module("adore.web.app")

    def probe(config, runner, env_file):
        """@brief Change an external credential after the initial snapshot."""
        env_file.write_text("OPENAI_API_KEY=concurrent-change\n", encoding="utf-8")
        return {
            "executor": config.executor.default,
            "model": config.executor.commands[config.executor.default].model,
            "ready": True,
            "reason": "ready",
        }

    monkeypatch.setattr(module, "probe_model_connection", probe)
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        response = client.post(
            "/api/v1/projects/alpha/model-connection-test", headers={"X-CSRF-Token": csrf}
        )
        assert response.status_code == 409
        assert not (profiles.profile_dir("alpha") / "model-connection.json").exists()
