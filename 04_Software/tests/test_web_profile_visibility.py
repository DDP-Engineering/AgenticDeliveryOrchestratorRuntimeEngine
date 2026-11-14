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
@file       test_web_profile_visibility.py
@brief      Operation identity remains reliable across profile read contention.
@details    Offline accepted-operation polls preserve storage and authorization boundaries.
"""

# IMPORTS
import errno
from pathlib import Path

from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest

from tests.test_web_pending_config import _headers, _project


# PUBLIC API / TESTS
@pytest.mark.parametrize("boundary", ["transient", "persistent", "corrupt", "deleted"])
def test_configuration_operation_preserves_profile_read_boundaries(tmp_path, monkeypatch, boundary):
    """@brief Recover brief denial; unreadable, corrupt and deleted projects retain typed errors."""
    profiles, path, _state = _project(tmp_path)
    identity = profiles.load("alpha").project_id
    metadata = profiles.profile_dir("alpha") / "profile.json"
    original_open = Path.open
    attempts = []
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        response = client.put("/api/v1/projects/alpha/config", headers=headers, json={
            "key": "budgets.max_iterations", "value": "19", "revision": revision,
        })
        assert response.status_code == 202
        accepted = response.json()
        assert accepted["project_id"] == identity
        app.state.web_store.create_user("reader", "longer-password", "developer")
        signed_in = client.post("/api/v1/session", json={
            "username": "reader", "password": "longer-password",
        })
        assert signed_in.status_code == 200
        hidden = client.get("/api/v1/operations/" + str(accepted["id"]))
        assert hidden.status_code == 404
        assert hidden.json()["detail"]["code"] == "operation_not_found"
        _headers(client)
        before = path.read_bytes()
        if boundary == "deleted":
            profiles.delete("alpha")
        elif boundary == "corrupt":
            metadata.write_text("{corrupt", encoding="utf-8")
        else:
            def contended(target, *args, **kwargs):
                """@brief Model the observed CRT permission error without a winerror attribute."""
                if target == metadata:
                    attempts.append(True)
                    if boundary == "persistent" or len(attempts) <= 2:
                        raise PermissionError(errno.EACCES, "fixture-private metadata denial")
                return original_open(target, *args, **kwargs)

            monkeypatch.setattr(Path, "open", contended)
            monkeypatch.setattr("adore.profiles.sleep", lambda seconds: None)
        observed = client.get("/api/v1/operations/" + str(accepted["id"]))
        if boundary == "transient":
            assert observed.status_code == 200, observed.text
            assert observed.json()["project_id"] == identity
            assert observed.json()["status"] == "pending"
            assert observed.json()["outcome"] is None
        else:
            assert observed.status_code == (404 if boundary == "deleted" else 503)
            assert observed.json()["detail"]["code"] == (
                "project_not_found" if boundary == "deleted" else "web_store_corrupt")
            assert "fixture-private" not in observed.text
            if boundary == "persistent":
                assert len(attempts) == 5
        if boundary == "deleted":
            assert not profiles.profile_dir("alpha").exists()
        else:
            assert path.read_bytes() == before

# END OF FILE
