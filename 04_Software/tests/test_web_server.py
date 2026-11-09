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
@file test_web_server.py
@brief Web listener exposure boundary.
@details A reverse proxy must carry remote login traffic over TLS.
"""

import sqlite3

from adore.state import StateStore
from adore.web.app import create_app
from adore.web.server import main
from fastapi.testclient import TestClient
import pytest


def test_loopback_listener_starts(tmp_path, monkeypatch):
    """@brief The supported local listener delegates to Uvicorn."""
    calls = []
    monkeypatch.setattr("adore.web.server.uvicorn.run", lambda app, **kwargs: calls.append(kwargs))
    assert main(["--home", str(tmp_path), "--host", "127.0.0.1", "--port", "18765"]) == 0
    assert calls == [{"host": "127.0.0.1", "port": 18765,
                      "proxy_headers": True,
                      "forwarded_allow_ips": "127.0.0.1,::1"}]


def test_tls_login_cookie_and_untrusted_forwarded_header(tmp_path):
    """@brief HTTPS gets a Secure cookie; a raw forwarding header is ignored."""
    app = create_app(tmp_path)
    with TestClient(app, base_url="https://adore.internal") as client:
        response = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        assert response.status_code == 200
        cookie = response.headers["set-cookie"].lower()
        assert "secure" in cookie and "httponly" in cookie and "samesite" in cookie
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"},
            headers={"X-Forwarded-Proto": "https"})
        assert response.status_code == 200
        assert "secure" not in response.headers["set-cookie"].lower()


def test_non_loopback_plain_listener_is_rejected(capsys):
    """@brief The CLI refuses a network-facing HTTP bind."""
    with pytest.raises(SystemExit) as exit_info:
        main(["--host", "0.0.0.0"])
    assert exit_info.value.code == 2
    assert "TLS reverse proxy" in capsys.readouterr().err


def test_api_health_and_worker_readiness_are_distinct(tmp_path):
    """@brief Live HTTP alone does not claim the control worker is ready."""
    app = create_app(tmp_path)
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json() == {"status": "alive"}
        missing = client.get("/api/v1/ready")
        assert missing.status_code == 503
        assert missing.json()["detail"]["code"] == "worker_unavailable"
        app.state.web_store.touch_worker()
        assert client.get("/api/v1/ready").json() == {
            "status": "ready", "worker": "ready", "activity": "unknown"}
        web = app.state.web_store
        lock = StateStore(web.path.parent / "web-control", "adore-web")
        assert lock.acquire_lock()
        web.set_worker_activity("busy")
        assert client.get("/api/v1/ready").json()["activity"] == "busy"
        old_activity = web.path.with_name(web.path.name + ".activity").read_bytes()
        lock.release_lock()
        assert lock.acquire_lock()
        web.path.with_name(web.path.name + ".activity").write_bytes(old_activity)
        assert client.get("/api/v1/ready").json()["activity"] == "unknown"
        web.path.with_name(web.path.name + ".activity").write_bytes(b"invalid")
        assert client.get("/api/v1/ready").json()["activity"] == "unknown"
        lock.release_lock()
        app.state.web_store.clear_worker()
        assert client.get("/api/v1/ready").status_code == 503


def test_corrupt_or_stale_worker_heartbeat_fails_readiness(tmp_path):
    """@brief Persisted clock corruption and a stopped worker fail closed."""
    app = create_app(tmp_path)
    web = app.state.web_store
    web.touch_worker()
    with sqlite3.connect(web.path) as connection:
        connection.execute("UPDATE worker_heartbeat SET updated_at=?", (
            "2020-01-01T00:00:00+00:00",))
    with TestClient(app) as client:
        assert client.get("/api/v1/ready").status_code == 503
        with sqlite3.connect(web.path) as connection:
            connection.execute("UPDATE worker_heartbeat SET updated_at=?", (
                "not-a-timestamp",))
        response = client.get("/api/v1/ready")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "web_store_corrupt"


def test_about_includes_bundled_third_party_notices(tmp_path):
    """@brief About exposes release/license text and bundled dependency notices."""
    with TestClient(create_app(tmp_path)) as client:
        response = client.get("/api/v1/about")
        assert response.status_code == 200
        value = response.json()
        assert value["version"]
        assert "PolyForm Noncommercial License" in value["license_text"]
        assert "React" in value["third_party_notices"]
        assert "FastAPI" in value["third_party_notices"]
