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
@file test_web_storage.py
@brief Administrator storage-warning API contract tests.
@details Disk measurements are faked; no host capacity is assumed.
"""

from collections import namedtuple

from adore.profiles import ProfileStore
from adore.web.app import create_app
from fastapi.testclient import TestClient

Usage = namedtuple("Usage", "total used free")


def test_admin_storage_warns_for_low_project_volume(tmp_path, monkeypatch):
    """@brief Storage warnings cover home and project state roots."""
    home = tmp_path / "home"
    root = tmp_path / "project-state"
    root.mkdir()
    ProfileStore(home).create("alpha", store_root=str(root))
    checked = []

    def disk_usage(path):
        checked.append(path)
        free = 512 * 1024 * 1024 if path == root else 2 * 1024**3
        return Usage(10 * 1024**3, 10 * 1024**3 - free, free)

    monkeypatch.setattr("adore.web.app.shutil.disk_usage", disk_usage)
    with TestClient(create_app(home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/system/storage")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["threshold_bytes"] == 1024**3
        assert data["low"] is True
        device = str(tmp_path.stat().st_dev)
        assert data["volumes"] == [
            {"scope": "home", "project": None, "free_bytes": 2 * 1024**3,
             "total_bytes": 10 * 1024**3, "low": False, "volume_id": device},
            {"scope": "project", "project": "alpha", "free_bytes": 512 * 1024 * 1024,
             "total_bytes": 10 * 1024**3, "low": True, "volume_id": device},
        ]
        assert len(checked) == 2


def test_storage_requires_admin_and_fails_closed_on_measurement_error(tmp_path, monkeypatch):
    """@brief A developer cannot read host capacity; failed checks are explicit."""
    home = tmp_path / "home"
    app = create_app(home)
    app.state.web_store.create_user("dev", "longer-password", "developer")
    with TestClient(app) as client:
        assert client.get("/api/v1/system/storage").status_code == 401
        client.post("/api/v1/session", json={"username": "dev", "password": "longer-password"})
        assert client.get("/api/v1/system/storage").status_code == 403
        csrf = client.get("/api/v1/me").json()["csrf"]
        client.delete("/api/v1/session", headers={"X-CSRF-Token": csrf})
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})

        def disk_usage(_path):
            raise OSError("private host path")

        monkeypatch.setattr("adore.web.app.shutil.disk_usage", disk_usage)
        failure = client.get("/api/v1/system/storage")
        assert failure.status_code == 503
        assert failure.json()["detail"]["code"] == "storage_check_failed"
        assert "private host path" not in failure.text
