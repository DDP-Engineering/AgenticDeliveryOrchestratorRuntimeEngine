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
@file test_web_project_access.py
@brief Administrators see and change one project's developer access from the
       project itself, one developer at a time.
"""

from adore.profiles import ProfileStore
from adore.web.app import create_app
from adore.web.store import WebStore, WebStoreError
from fastapi.testclient import TestClient
import pytest


def _setup(tmp_path):
    """@brief Two projects and two developers: dev1 has both, dev2 only beta."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    profiles.create("beta")
    app = create_app(profiles.home)
    web = app.state.web_store
    dev1 = web.create_user("dev1", "longer-password", "developer")
    dev2 = web.create_user("dev2", "longer-password", "developer")
    web.set_memberships(dev1["id"], ["alpha", "beta"])
    web.set_memberships(dev2["id"], ["beta"])
    return app, web, dev1, dev2


def _login(client, username, password):
    """@brief Sign in and return the CSRF header for writes."""
    csrf = client.post("/api/v1/session", json={
        "username": username, "password": password}).json()["csrf"]
    return {"X-CSRF-Token": csrf}


def test_administrator_grants_and_removes_one_developer(tmp_path):
    """
    @brief   A grant or removal changes exactly one developer's access to one
             project, is audited, and the developer's project list follows.
    """
    app, web, dev1, dev2 = _setup(tmp_path)
    with TestClient(app) as client:
        headers = _login(client, "admin", "admin")
        listed = client.get("/api/v1/projects/alpha/access")
        assert listed.status_code == 200, listed.text
        assert listed.json() == {"developers": [
            {"id": dev1["id"], "username": "dev1", "disabled": False, "granted": True},
            {"id": dev2["id"], "username": "dev2", "disabled": False, "granted": False},
        ]}

        granted = client.put(f"/api/v1/projects/alpha/access/{dev2['id']}",
                             json={"granted": True}, headers=headers)
        assert granted.status_code == 200, granted.text
        assert granted.json() == {"id": dev2["id"], "granted": True}
        assert web.memberships(dev1["id"]) == {"alpha", "beta"}  # another developer untouched
        removed = client.put(f"/api/v1/projects/alpha/access/{dev1['id']}",
                             json={"granted": False}, headers=headers)
        assert removed.status_code == 200, removed.text

        assert web.memberships(dev1["id"]) == {"beta"}           # other project kept
        assert web.memberships(dev2["id"]) == {"alpha", "beta"}  # grant added, beta kept
        audit = {(row["action"], row["project"], row["detail"]) for row in web.recent_audit(10)}
        assert ("membership-changed", "alpha", f"user {dev2['id']} granted") in audit
        assert ("membership-changed", "alpha", f"user {dev1['id']} removed") in audit

        web.disable_user(dev1["id"])
        again = client.get("/api/v1/projects/alpha/access").json()["developers"]
        assert [(row["username"], row["disabled"], row["granted"]) for row in again] == [
            ("dev1", True, False), ("dev2", False, True)]

        _login(client, "dev2", "longer-password")
        assert {item["name"] for item in client.get("/api/v1/projects").json()} == {"alpha", "beta"}


def test_access_api_refuses_non_administrators_and_bad_targets(tmp_path):
    """@brief Role, CSRF, unknown project or account and non-developers are refused."""
    app, web, _dev1, dev2 = _setup(tmp_path)
    admin_id = next(user["id"] for user in web.list_users() if user["username"] == "admin")
    target = f"/api/v1/projects/alpha/access/{dev2['id']}"
    with TestClient(app) as client:
        headers = _login(client, "admin", "admin")
        assert client.put(target, json={"granted": True}).status_code == 403  # no CSRF token
        missing = client.put(f"/api/v1/projects/missing/access/{dev2['id']}",
                             json={"granted": True}, headers=headers)
        assert missing.status_code == 404
        nobody = client.put("/api/v1/projects/alpha/access/9999",
                            json={"granted": True}, headers=headers)
        assert nobody.status_code == 404
        assert nobody.json()["detail"]["code"] == "user_not_found"
        admin = client.put(f"/api/v1/projects/alpha/access/{admin_id}",
                           json={"granted": True}, headers=headers)
        assert admin.status_code == 400
        assert admin.json()["detail"]["code"] == "user_not_developer"
        assert web.memberships(dev2["id"]) == {"beta"}

        dev_headers = _login(client, "dev2", "longer-password")
        assert client.get("/api/v1/projects/beta/access").status_code == 403
        assert client.put(target, json={"granted": True}, headers=dev_headers).status_code == 403
        assert web.memberships(dev2["id"]) == {"beta"}


def test_access_follows_the_project_identity_across_a_rename(tmp_path):
    """
    @brief   A grant made before a rename can be removed afterwards, and a new
             project that reuses the old name is granted without taking the
             renamed project's grant away.
    """
    app, web, dev1, _dev2 = _setup(tmp_path)
    profiles = ProfileStore(tmp_path / "home")
    profiles.rename("alpha", "renamed")
    profiles.create("alpha")
    with TestClient(app) as client:
        headers = _login(client, "admin", "admin")
        granted = client.put(f"/api/v1/projects/alpha/access/{dev1['id']}",
                             json={"granted": True}, headers=headers)
        assert granted.status_code == 200, granted.text
        assert web.memberships(dev1["id"]) == {"alpha", "beta", "renamed"}

        removed = client.put(f"/api/v1/projects/renamed/access/{dev1['id']}",
                             json={"granted": False}, headers=headers)
        assert removed.status_code == 200, removed.text
        assert web.memberships(dev1["id"]) == {"alpha", "beta"}
        listed = client.get("/api/v1/projects/renamed/access").json()["developers"]
        assert [(row["username"], row["granted"]) for row in listed] == [
            ("dev1", False), ("dev2", False)]


def test_a_rename_racing_a_grant_is_refused_cleanly(tmp_path, monkeypatch):
    """
    @brief   When a rename lands between the project snapshot and the write, the
             grant is refused as a store error and nothing changes.
    """
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    web = WebStore(tmp_path / "home" / "web.db")
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    stale = web._projects_by_id()          # alpha still carries its old name here
    profiles.rename("alpha", "renamed")
    profiles.create("alpha")
    monkeypatch.setattr(web, "_projects_by_id", lambda: stale)
    with pytest.raises(WebStoreError, match="project changed during the update"):
        web.set_membership(dev["id"], "alpha", True)
    monkeypatch.undo()
    assert web.memberships(dev["id"]) == {"renamed"}


def test_the_access_route_reports_a_racing_rename_as_project_changed(tmp_path, monkeypatch):
    """@brief The API answers 409 project_changed, changes nothing and audits nothing."""
    app, web, dev1, _dev2 = _setup(tmp_path)
    stale = web._projects_by_id()
    profiles = ProfileStore(tmp_path / "home")
    profiles.rename("alpha", "renamed")
    profiles.create("alpha")
    monkeypatch.setattr(web, "_projects_by_id", lambda: stale)
    with TestClient(app) as client:
        headers = _login(client, "admin", "admin")
        raced = client.put(f"/api/v1/projects/alpha/access/{dev1['id']}",
                           json={"granted": True}, headers=headers)
        assert raced.status_code == 409
        assert raced.json()["detail"]["code"] == "project_changed"
    monkeypatch.undo()
    assert web.memberships(dev1["id"]) == {"renamed", "beta"}
    assert not [row for row in web.recent_audit(20) if row["action"] == "membership-changed"]
