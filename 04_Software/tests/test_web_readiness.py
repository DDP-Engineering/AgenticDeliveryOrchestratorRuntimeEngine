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
from adore.util import CommandResult
from adore.web.app import create_app
from fastapi.testclient import TestClient


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
        assert "model_endpoint" not in value["checks"] and "model_probe" not in value
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
        assert any(argv[-1] == "pi" for argv in calls if "--entrypoint" in argv)


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


# END OF FILE
