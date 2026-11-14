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
@file       test_web_user_creation.py
@brief      Atomic reviewed account creation at public trust boundaries.
@details    Offline API, authentication, stable grants and rollback/race proof.
"""

# IMPORTS
import sqlite3

from adore.profiles import ProfileStore
from adore.web.app import create_app
import adore.web.store as store_module
from adore.web.store import WebStore
import pytest

from tests.configuration_client import TestClient


# LOCAL HELPERS
def setup(tmp_path):
    """@brief Prepare two visible profiles and a local API with no external tools."""
    home = tmp_path / "home"
    profiles = ProfileStore(home)
    alpha, beta = profiles.create("alpha"), profiles.create("beta")
    app = create_app(home)
    return app, WebStore(home / "web.db"), profiles, alpha, beta


def login(client, username="admin", password="admin"):
    """@brief Authenticate through the API and return its CSRF header."""
    response = client.post("/api/v1/session", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf"]}


def intent(selected_ids, **updates):
    return {"username": "newdev", "password": "test-password", "role": "developer",
            "project_ids": selected_ids, "allow_no_projects": False, **updates}


# PUBLIC API
@pytest.mark.parametrize("role", ["admin", "developer"])
def test_atomic_create_assigns_exact_access_and_keeps_secrets_private(tmp_path, role):
    """@brief Admin global and Dev selected access work through recipient login."""
    app, web, _profiles, alpha, beta = setup(tmp_path)
    ids = [alpha.project_id] if role == "developer" else []
    with TestClient(app) as client:
        headers = login(client)
        response = client.post("/api/v1/users/with-access", headers=headers,
                               json=intent(ids, role=role))
        assert response.status_code == 200, response.text
        created = response.json()
        assert created["role"] == role and created["project_ids"] == ids
        assert web.memberships(created["id"]) == ({"alpha"} if ids else set())
        listed = next(row for row in client.get("/api/v1/users").json()
                      if row["id"] == created["id"])
        assert listed["project_ids"] == ids
        assert "test-password" not in response.text + str(web.recent_audit(None))
        assert "password_hash" not in response.text
        login(client, "newdev", "test-password")
        visible = client.get("/api/v1/projects").json()
        assert {row["id"] for row in visible} == (
            {alpha.project_id} if ids else {alpha.project_id, beta.project_id})
        assert client.get("/api/v1/users").status_code == (403 if ids else 200)
        if ids:
            assert client.get(f"/api/v1/projects/{beta.name}/config").status_code == 404
            assert client.get(f"/api/v1/projects/{alpha.name}/prices").status_code == 403


@pytest.mark.parametrize("updates", [
    {"username": "bad name"}, {"username": "admin"}, {"username": ""},
    {"role": "owner"}, {"role": None}, {"password": "short"}, {"password": "x" * 1025},
    {"project_ids": ["0" * 32]}, {"project_ids": ["alpha"]},
    {"project_ids": [123]}, {"project_ids": None}, {"project_ids": "alpha"},
    {"project_ids": []}, {"role": "admin"}, {"allow_no_projects": "true"},
    {"unknown": "ignored?"},
])
def test_invalid_intent_leaves_no_partial_account_or_success_audit(tmp_path, updates):
    """@brief Invalid and coercible external data is rejected without a partial write."""
    app, web, _profiles, alpha, _beta = setup(tmp_path)
    with TestClient(app) as client:
        headers = login(client)
        before, audit = web.list_users(), web.recent_audit(None)
        result = client.post("/api/v1/users/with-access", headers=headers,
                             json=intent([alpha.project_id], **updates))
        assert result.status_code in (400, 409, 422), result.text
        assert web.list_users() == before and web.recent_audit(None) == audit
        assert "test-password" not in result.text


def test_explicit_empty_dev_and_duplicate_grants(tmp_path):
    """@brief Zero-project Dev requires deliberate choice; duplicate IDs fail closed."""
    app, web, _profiles, alpha, _beta = setup(tmp_path)
    with TestClient(app) as client:
        headers = login(client)
        response = client.post("/api/v1/users/with-access", headers=headers,
                               json=intent([], allow_no_projects=True))
        assert response.status_code == 200, response.text
        assert web.memberships(response.json()["id"]) == set()
        response = client.post("/api/v1/users/with-access", headers=headers,
                               json=intent([alpha.project_id] * 2, username="duplicategrants"))
        assert response.status_code == 400
        assert not web.authenticate("duplicategrants", "test-password")


@pytest.mark.parametrize("change", ["archive", "delete", "replace", "rename"])
def test_project_change_during_hashing_rolls_back_creation(tmp_path, monkeypatch, change):
    """@brief A live project change during creation cannot leave an account behind."""
    app, web, profiles, alpha, _beta = setup(tmp_path)
    original = store_module._HASHER.hash

    def hashing(_hasher, password):
        """@brief Inject a lifecycle race at the real credential hashing boundary."""
        hashed = original(password)
        if change == "archive":
            alpha.archived = True
            profiles.save(alpha)
        elif change == "rename":
            profiles.rename("alpha", "renamed")
        else:
            profiles.delete("alpha")
            if change == "replace":
                profiles.create("alpha")
        return hashed

    with TestClient(app) as client:
        headers = login(client)
        before, audit = web.list_users(), web.recent_audit(None)
        monkeypatch.setattr(type(store_module._HASHER), "hash", hashing)
        response = client.post("/api/v1/users/with-access", headers=headers,
                               json=intent([alpha.project_id]))
        assert response.status_code == 409, response.text
        assert web.list_users() == before and web.recent_audit(None) == audit


def test_archived_and_corrupt_projects_fail_closed(tmp_path):
    """@brief Archived or corrupt metadata never produces a grant or account."""
    app, web, profiles, alpha, _beta = setup(tmp_path)
    alpha.archived = True
    profiles.save(alpha)
    with TestClient(app) as client:
        headers = login(client)
        before = web.list_users()
        response = client.post("/api/v1/users/with-access", headers=headers,
                               json=intent([alpha.project_id]))
        assert response.status_code == 400
        (profiles.profile_dir("beta") / "profile.json").write_text("corrupt", encoding="utf-8")
        response = client.post("/api/v1/users/with-access", headers=headers,
                               json=intent([alpha.project_id]))
        assert response.status_code == 503, response.text
        assert web.list_users() == before


def test_membership_write_failure_rolls_back_user_and_all_grants(tmp_path):
    """@brief A storage fault after user and first grant insertion rolls everything back."""
    app, web, _profiles, alpha, beta = setup(tmp_path)
    with sqlite3.connect(web.path) as connection:
        connection.execute("CREATE TRIGGER reject_beta BEFORE INSERT ON memberships "
                           "WHEN NEW.project='beta' BEGIN SELECT RAISE(ABORT,'fault'); END")
    with TestClient(app) as client:
        headers = login(client)
        before, audit = web.list_users(), web.recent_audit(None)
        response = client.post("/api/v1/users/with-access", headers=headers,
                               json=intent([alpha.project_id, beta.project_id]))
        assert response.status_code == 503, response.text
        assert web.list_users() == before and web.recent_audit(None) == audit
        with sqlite3.connect(web.path) as connection:
            assert connection.execute("SELECT COUNT(*) FROM memberships").fetchone()[0] == 0


def test_only_active_admin_with_csrf_can_create_and_legacy_api_works(tmp_path):
    """@brief New endpoint preserves server authorization and the supported old contract."""
    app, web, _profiles, alpha, _beta = setup(tmp_path)
    with TestClient(app) as client:
        headers = login(client)
        assert client.post("/api/v1/users/with-access", json=intent([])).status_code == 403
        response = client.post("/api/v1/users", headers=headers,
                               json={"username": "olddev", "password": "test-password"})
        assert response.status_code == 200
        dev = response.json()
        dev_headers = login(client, "olddev", "test-password")
        assert client.post("/api/v1/users/with-access", headers=dev_headers,
                           json=intent([alpha.project_id])).status_code == 403
        for suffix in ("disable", "reset-password"):
            assert client.post(f"/api/v1/users/{dev['id']}/{suffix}",
                               headers=dev_headers,
                               json={"replacement": "test-password"}).status_code == 403
        assert client.put(f"/api/v1/users/{dev['id']}/projects", headers=dev_headers,
                          json={"projects": []}).status_code == 403
        web.disable_user(dev["id"])
        assert client.post("/api/v1/users/with-access", headers=dev_headers,
                           json=intent([alpha.project_id])).status_code == 401
        headers = login(client)
        admin_id = web.authenticate("admin", "admin")["id"]
        assert client.post(f"/api/v1/users/{admin_id}/disable", headers=headers).status_code == 409


def test_project_deleted_after_grant_write_rolls_back_everything(tmp_path, monkeypatch):
    """@brief The final lifecycle check rolls back rows already written in the transaction."""
    app, web, profiles, alpha, _beta = setup(tmp_path)
    original = WebStore._prune_audit

    def prune(store, connection):
        """@brief Simulate external deletion during the transaction's final audit write."""
        original(store, connection)
        profiles.delete("alpha")

    with TestClient(app) as client:
        headers = login(client)
        before, audit = web.list_users(), web.recent_audit(None)
        monkeypatch.setattr(WebStore, "_prune_audit", prune)
        response = client.post("/api/v1/users/with-access", headers=headers,
                               json=intent([alpha.project_id]))
        assert response.status_code == 409
        monkeypatch.undo()
        assert web.list_users() == before and web.recent_audit(None) == audit
        with sqlite3.connect(web.path) as connection:
            assert connection.execute("SELECT COUNT(*) FROM memberships").fetchone()[0] == 0


def test_created_grants_survive_rename_restart_and_do_not_transfer_to_replacement(tmp_path):
    """@brief Public durable memberships follow IDs and never a recycled name."""
    app, web, profiles, alpha, _beta = setup(tmp_path)
    with TestClient(app) as client:
        headers = login(client)
        created = client.post("/api/v1/users/with-access", headers=headers,
                              json=intent([alpha.project_id])).json()
    profiles.rename("alpha", "renamed")
    profiles.create("alpha")
    restored = WebStore(web.path)
    assert restored.memberships(created["id"]) == {"renamed"}
    assert restored.membership_ids(created["id"]) == [alpha.project_id]
    profiles.delete("renamed")
    assert restored.memberships(created["id"]) == set()
    assert restored.membership_ids(created["id"]) == []


@pytest.mark.parametrize("field", ["role", "project_ids"])
def test_atomic_creation_requires_explicit_access_fields(tmp_path, field):
    """@brief The reviewed API cannot silently infer a role or project selection."""
    app, web, _profiles, alpha, _beta = setup(tmp_path)
    with TestClient(app) as client:
        headers = login(client)
        body = intent([alpha.project_id])
        del body[field]
        before = web.list_users()
        assert client.post("/api/v1/users/with-access", headers=headers,
                           json=body).status_code == 422
        assert web.list_users() == before


@pytest.mark.parametrize("corruption", ["audit_policy", "audit_write"])
def test_audit_failure_cannot_leave_a_successful_account(tmp_path, corruption):
    """@brief Corrupt policy and failed audit writes roll back the entire mutation."""
    app, web, _profiles, alpha, _beta = setup(tmp_path)
    with TestClient(app) as client:
        headers = login(client)
        before = web.list_users()
        with sqlite3.connect(web.path) as connection:
            if corruption == "audit_policy":
                connection.execute("UPDATE audit_policy SET retention_days=-1")
            else:
                connection.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON audit "
                                   "WHEN NEW.action='user-created' "
                                   "BEGIN SELECT RAISE(ABORT,'fault'); END")
        response = client.post("/api/v1/users/with-access", headers=headers,
                               json=intent([alpha.project_id]))
        assert response.status_code == 503, response.text
        assert web.list_users() == before
        with sqlite3.connect(web.path) as connection:
            assert connection.execute("SELECT COUNT(*) FROM memberships").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM audit "
                                      "WHERE action='user-created'").fetchone()[0] == 0


# END OF FILE
