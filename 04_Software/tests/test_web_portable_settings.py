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
@file    test_web_portable_settings.py
@brief   Admin-only authoritative portable export HTTP contract.
@details Offline authorization, source corruption and preview binding tests.
"""

# IMPORTS
from pathlib import Path

from adore.portable_settings import export_settings, parse_settings
from adore.profiles import ProfileStore
from adore.web.app import create_app
import pytest

from tests.configuration_client import TestClient

# CONSTANTS
EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.toml"
URL = "/api/v1/projects/alpha/config/portable-settings"

# PUBLIC API / TESTS


def test_admin_preview_download_is_active_canonical_and_bound(tmp_path):
    """@brief Admin downloads exact active rules and stale preview fails closed."""
    profiles = ProfileStore(tmp_path / "home")
    item = profiles.create("alpha")
    path = profiles.config_path("alpha")
    raw = EXAMPLE.read_bytes()
    path.write_bytes(raw)
    pending = profiles.profile_dir("alpha") / "pending_config.json"
    pending.write_text('{"secret":"PENDING-SENTINEL"}', encoding="utf-8")
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        result = client.get(URL)
        assert result.status_code == 200, result.text
        assert result.content == export_settings(raw)
        assert result.headers["cache-control"] == "no-store"
        assert "PENDING" not in result.text
        checksum = result.json()["checksum"]
        downloaded = client.get(URL, params={"download": True, "checksum": checksum})
        assert downloaded.content == result.content
        assert (
            downloaded.headers["content-disposition"]
            == 'attachment; filename="adore-project-settings.json"'
        )
        assert parse_settings(downloaded.content) == result.json()["settings"]
        assert client.get(URL.replace("alpha", item.project_id)).content == result.content
        path.write_bytes(
            raw.replace(b"max_iterations           = 20", b"max_iterations           = 37")
        )
        stale = client.get(URL, params={"download": True, "checksum": checksum})
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "portable_settings_changed"
        assert client.get(URL, params={"checksum": "secret-input"}).status_code == 409
        assert client.get(URL.replace("alpha", "absent")).status_code == 404
        assert pending.read_text() == '{"secret":"PENDING-SENTINEL"}'


def test_export_role_and_session_denial_before_project_io(tmp_path, monkeypatch):
    """@brief Dev and invalid sessions receive no existence/config metadata."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha", repo="PRIVATE-METADATA")
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    monkeypatch.setattr(ProfileStore, "exists", lambda *_: pytest.fail("unauthorized project IO"))
    with TestClient(app) as client:
        for url in (URL, URL.replace("alpha", "absent")):
            assert client.get(url).status_code == 401
        csrf = client.post(
            "/api/v1/session", json={"username": "dev", "password": "longer-password"}
        ).json()["csrf"]
        for url in (URL, URL.replace("alpha", "absent"), URL + "?download=true"):
            response = client.get(url)
            assert response.status_code == 403
            assert response.json() == {"detail": {"code": "admin_required"}}
        web.set_memberships(dev["id"], [])
        assert client.get(URL).status_code == 403
        client.delete("/api/v1/session", headers={"X-CSRF-Token": csrf})
        assert client.get(URL).status_code == 401


@pytest.mark.parametrize(
    "corruption",
    [
        b"",
        b"[broken",
        b"\xff",
        b'\n[extra]\nsecret="SECRET-SENTINEL"',
        b'\n[polling.secret]\nvalue="SECRET-SENTINEL"',
    ],
)
def test_export_invalid_source_never_leaks_data(tmp_path, corruption):
    """@brief Invalid, unknown or unreadable active config yields safe error only."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    path.write_bytes(
        EXAMPLE.read_bytes() + corruption if corruption.startswith(b"\n") else corruption
    )
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get(URL)
        assert response.status_code == 503
        assert response.json() == {"detail": {"code": "portable_settings_invalid"}}
        assert "SECRET" not in response.text
        path.unlink()
        assert client.get(URL).status_code == 503


def test_export_rechecks_project_identity_after_snapshot(tmp_path, monkeypatch):
    """@brief Replaced profile ownership cannot produce a result for an old selection."""
    from adore.web import app as api

    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    profiles.config_path("alpha").write_bytes(EXAMPLE.read_bytes())
    original = api.export_settings

    def replace_profile(raw):
        """@brief Simulate profile replacement after a valid snapshot has been read."""
        encoded = original(raw)
        item = profiles.load("alpha")
        item.project_id = "b" * 32
        profiles.save(item)
        return encoded

    monkeypatch.setattr(api, "export_settings", replace_profile)
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get(URL)
        assert response.status_code == 409
        assert response.json() == {"detail": {"code": "project_changed"}}


# END OF FILE
