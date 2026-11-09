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
@file       test_web_config_raw.py
@brief      Administrator original TOML download and trust boundaries.
@details    Offline HTTP tests preserve exact bytes and prevent denied disclosure.
"""

# IMPORTS
from pathlib import Path

from adore.profiles import ProfileStore
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def raw_project(tmp_path):
    """@brief Create an isolated saved profile with a private inline fixture field."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    source = (Path(__file__).resolve().parents[1] / "config.example.toml").read_text(
        encoding="utf-8").encode("utf-8")
    raw = (source + b'\n[private_fixture]\nvalue = "inline-private-fixture"\n').replace(
        b"\n", b"\r\n"
    )
    path.write_bytes(raw)
    return profiles, path, raw


def test_admin_raw_configuration_preserves_original_bytes(raw_project):
    """@brief Both read forms retain saved bytes, private fields and config revision."""
    profiles, path, raw = raw_project
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        for suffix in ("", "?download=true"):
            response = client.get("/api/v1/projects/alpha/config/raw" + suffix)
            assert response.status_code == 200
            assert response.content == raw
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["content-type"].startswith("text/plain")
            if suffix:
                assert (
                    response.headers["content-disposition"] == 'attachment; filename="config.toml"'
                )
        assert path.read_bytes() == raw
        assert not (path.parent / "pending_config.json").exists()


@pytest.mark.parametrize(
    "payload",
    [b"", b"[broken", b"value=\xff", b"#" * 524289],
    ids=["empty", "invalid-toml", "invalid-utf8", "oversized"],
)
def test_raw_configuration_corruption_withholds_bytes(raw_project, payload):
    """@brief Empty, malformed, invalid UTF-8 and oversized files fail closed."""
    profiles, path, _ = raw_project
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        path.write_bytes(payload)
        response = client.get("/api/v1/projects/alpha/config/raw")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "config_corrupt"


def test_raw_configuration_denied_roles_and_missing_source(raw_project):
    """@brief Anonymous and Dev reads disclose nothing; missing source is typed."""
    profiles, path, _ = raw_project
    app = create_app(profiles.home)
    with TestClient(app) as client:
        target = "/api/v1/projects/alpha/config/raw"
        assert client.get(target).status_code == 401
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        csrf = login.json()["csrf"]
        created = client.post(
            "/api/v1/users",
            json={"username": "reader", "password": "fixture-password", "role": "developer"},
            headers={"X-CSRF-Token": csrf},
        )
        assert created.status_code == 200
        app.state.web_store.set_memberships(created.json()["id"], ["alpha"])
        client.delete("/api/v1/session", headers={"X-CSRF-Token": csrf})
        client.post("/api/v1/session", json={"username": "reader", "password": "fixture-password"})
        assert client.get(target).status_code == 403
        assert client.get("/api/v1/projects/missing/config/raw").status_code == 403
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        assert client.get("/api/v1/projects/missing/config/raw").status_code == 404
        path.unlink()
        assert client.get(target).status_code == 503


def test_raw_configuration_changed_source_fails_closed(raw_project, monkeypatch):
    """@brief Concurrent saved-file replacement cannot produce a mixed snapshot."""
    profiles, path, raw = raw_project
    original_open = Path.open
    reads = 0

    def changing_open(source, *args, **kwargs):
        """@brief Simulate an external writer replacing the configured file."""
        nonlocal reads
        if source == path and args and args[0] == "rb":
            reads += 1
            if reads == 2:
                with original_open(path, "wb") as writer:
                    writer.write(raw + b"\n# external writer\n")
        return original_open(source, *args, **kwargs)

    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        monkeypatch.setattr(Path, "open", changing_open)
        response = client.get("/api/v1/projects/alpha/config/raw")
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "stale_config_revision"


# END OF FILE
