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
@file test_web_readiness.py
@brief Administrator host-readiness probe contract tests.
@details External command output is faked and never returned to the browser.
"""

from pathlib import Path

from adore.profiles import ProfileStore
from adore.state import StateStore
from adore.util import CommandResult
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest


def _project(tmp_path):
    """@brief Register one valid but deliberately unprovisioned project."""
    profiles = ProfileStore(tmp_path / "home")
    root = tmp_path / "state"
    profiles.create("alpha", store_root=str(root))
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    path.write_bytes(example.read_bytes().replace(
        b'store_root = ".adore"',
        f'store_root = "{root.as_posix()}"'.encode(),
    ))
    return profiles, path


def test_admin_can_probe_host_prerequisites_without_disclosing_cli_output(tmp_path):
    """@brief An explicit probe reports booleans and bounds every command."""
    profiles, _path = _project(tmp_path)
    calls = []

    def runner(argv, *, cwd=None, timeout=None, env=None):
        calls.append((list(argv), timeout))
        return CommandResult(argv=list(argv), exit_code=127 if argv[0] == "glab" else 0,
                             stdout="secret-host-output", stderr="secret-auth-detail")

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        response = client.post("/api/v1/projects/alpha/readiness-check",
                               headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        value = response.json()
        assert value["context"] == "api-host"
        assert value["checks"]["git"] is True
        assert value["checks"]["forge_cli"] is False
        assert value["checks"]["forge_auth"] is False
        assert value["checks"]["aegis_files"] is False
        assert value["checks"]["executor_cli"] is True
        assert value["checks"]["model_endpoint"] == "not-checked"
        assert "secret" not in response.text
        assert calls and all(timeout <= 8 for _argv, timeout in calls)
        assert any("--pull=never" in argv and "--network" in argv
                   and "none" in argv for argv, _timeout in calls)


def test_host_executor_presence_does_not_hide_missing_image_tool(tmp_path):
    """@brief Readiness checks the actual executor image without a pull."""
    profiles, _path = _project(tmp_path)
    calls = []

    def runner(argv, *, cwd=None, timeout=None, env=None):
        calls.append(list(argv))
        return CommandResult(argv=list(argv),
                             exit_code=1 if "--entrypoint" in argv else 0,
                             stdout="", stderr="private runtime detail")

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        response = client.post("/api/v1/projects/alpha/readiness-check",
                               headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        assert response.json()["checks"]["executor_cli"] is False
        assert "private" not in response.text
        assert any("--entrypoint" in argv for argv in calls)
        assert not any(argv[0] == "opencode" for argv in calls)


def test_readiness_probe_requires_admin_csrf_and_valid_config(tmp_path):
    """@brief Membership alone cannot launch a host probe; corrupt TOML fails."""
    profiles, path = _project(tmp_path)

    def runner(argv, *, cwd=None, timeout=None, env=None):
        raise AssertionError(f"unexpected probe: {argv}")

    app = create_app(profiles.home, probe_runner=runner)
    user = app.state.web_store.create_user("dev", "longer-password", "developer")
    app.state.web_store.set_memberships(user["id"], ["alpha"])
    with TestClient(app) as client:
        admin_csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        assert client.post("/api/v1/projects/alpha/readiness-check").status_code == 403
        assert client.post("/api/v1/projects/missing/readiness-check",
                           headers={"X-CSRF-Token": admin_csrf}).status_code == 404
        path.write_text("[broken", encoding="utf-8")
        corrupt = client.post("/api/v1/projects/alpha/readiness-check",
                              headers={"X-CSRF-Token": admin_csrf})
        assert corrupt.status_code == 503
        client.delete("/api/v1/session", headers={"X-CSRF-Token": admin_csrf})
        dev_csrf = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"}).json()["csrf"]
        assert client.post("/api/v1/projects/alpha/readiness-check",
                           headers={"X-CSRF-Token": dev_csrf}).status_code == 403


def test_local_model_readiness_uses_disposable_executor_container(tmp_path):
    """@brief A streamed tool probe must run in the configured image context."""
    profiles, path = _project(tmp_path)
    StateStore(tmp_path / "state").pause()
    calls = []

    def runner(argv, *, cwd=None, timeout=None, env=None):
        calls.append((list(argv), timeout))
        if argv[0] == "docker" and "inspect" in argv and "image" not in argv:
            return CommandResult(argv=list(argv), exit_code=1, stdout="",
                                 stderr="No such object")
        if argv[0] == "docker" and "exec" in argv:
            assert "python" in argv and "-c" in argv
            assert env["ADORE_PROBE_MODEL"] == "test"
            assert env["SSL_CERT_FILE"] == "/etc/ssl/adore-model-ca.pem"
            return CommandResult(argv=list(argv), exit_code=0,
                                 stdout="ready\n", stderr="")
        return CommandResult(argv=list(argv), exit_code=0,
                             stdout="", stderr="")

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        saved = client.put("/api/v1/projects/alpha/config", json={
            "key": "container.runtime_env.OPENAI_BASE_URL",
            "value": "https://model.internal:1234/v1", "model": "local/test",
            "ca_file": "/etc/ssl/adore-model-ca.pem", "timeout_seconds": 45,
            "revision": revision}, headers={"X-CSRF-Token": csrf})
        assert saved.status_code == 200, saved.text
        response = client.post("/api/v1/projects/alpha/readiness-check",
                               headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        assert response.json()["checks"]["model_endpoint"] is True
        assert response.json()["model_probe"] == {
            "context": "executor-container", "ready": True,
            "model": "local/test", "reason": "ready"}
        assert any("--pull=never" in argv for argv, _ in calls)
        assert any("rm" in argv for argv, _ in calls)
        assert all(timeout is None or timeout <= 8 for _, timeout in calls)
    assert "model.internal" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("reason", (
    "tool-stream-incompatible", "redirect-rejected", "http-401",
    "endpoint-unreachable-or-incompatible", "credential-missing",
))
def test_local_model_readiness_rejects_incompatible_container_result(tmp_path, reason):
    """@brief Host success does not substitute for an incompatible model stream."""
    profiles, _path = _project(tmp_path)
    StateStore(tmp_path / "state").pause()

    def runner(argv, *, cwd=None, timeout=None, env=None):
        if argv[0] == "docker" and "inspect" in argv and "image" not in argv:
            return CommandResult(argv=list(argv), exit_code=1, stdout="",
                                 stderr="No such object")
        if argv[0] == "docker" and "exec" in argv:
            return CommandResult(argv=list(argv), exit_code=2,
                                 stdout=f"{reason}\n", stderr="secret")
        return CommandResult(argv=list(argv), exit_code=0, stdout="", stderr="")

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        saved = client.put("/api/v1/projects/alpha/config", json={
            "key": "container.runtime_env.OPENAI_BASE_URL",
            "value": "http://model.internal/v1", "model": "local/test",
            "revision": revision}, headers={"X-CSRF-Token": csrf})
        assert saved.status_code == 200, saved.text
        response = client.post("/api/v1/projects/alpha/readiness-check",
                               headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        assert response.json()["checks"]["model_endpoint"] is False
        assert response.json()["model_probe"]["reason"] == reason
        assert "secret" not in response.text
