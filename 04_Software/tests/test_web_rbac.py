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
@file test_web_rbac.py
@brief Public API project-scope and financial privacy tests.
@details Uses the ASGI application with local profile and state fixtures.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3

from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest


def test_developer_project_scope_and_cost_privacy(tmp_path):
    """@brief A developer sees only assigned project data without money fields."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha", repo="org/alpha")
    profiles.create("beta", repo="org/beta")
    app = create_app(tmp_path / "home")
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        assert client.get("/api/v1/projects").status_code == 401
        login = client.post(
            "/api/v1/session",
            json={"username": "dev", "password": "longer-password"},
        )
        assert login.status_code == 200
        response = client.get("/api/v1/projects")
        assert [item["name"] for item in response.json()] == ["alpha"]
        assert client.get("/api/v1/projects/beta").status_code == 404
        assert client.get("/api/v1/projects/beta/metrics").status_code == 404
        assert "cost" not in str(client.get("/api/v1/projects/alpha/metrics").json()).lower()
        assert client.get("/api/v1/users").status_code == 403
        assert client.post(
            "/api/v1/users/1/enable", headers={"X-CSRF-Token": login.json()["csrf"]}
        ).status_code == 403


def test_account_preferences_require_session_csrf_and_allowed_values(tmp_path):
    """@brief Preferences are account-scoped and validated at the HTTP boundary."""
    app = create_app(tmp_path / "home")
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    with TestClient(app) as client:
        assert client.get("/api/v1/me/preferences").status_code == 401
        login = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        csrf = login.json()["csrf"]
        assert client.patch("/api/v1/me/preferences", json={
            "language": "de"}).status_code == 403
        assert client.patch("/api/v1/me/preferences", headers={
            "X-CSRF-Token": csrf}, json={"language": "es"}).status_code == 422
        assert client.patch("/api/v1/me/preferences", headers={
            "X-CSRF-Token": csrf}, json={}).status_code == 422
        changed = client.patch("/api/v1/me/preferences", headers={
            "X-CSRF-Token": csrf}, json={"language": "de"})
        assert changed.status_code == 200
        assert changed.json() == {"language": "de", "theme": None}
        changed = client.patch("/api/v1/me/preferences", headers={
            "X-CSRF-Token": csrf}, json={"theme": "dark"})
        assert changed.json() == {"language": "de", "theme": "dark"}
        client.delete("/api/v1/session", headers={"X-CSRF-Token": csrf})
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        assert client.get("/api/v1/me/preferences").json() == {
            "language": None, "theme": None}
        assert web.preferences(dev["id"]) == {"language": "de", "theme": "dark"}
        with sqlite3.connect(web.path) as connection:
            connection.execute("UPDATE user_preferences SET theme='invalid' WHERE user_id=?",
                               (dev["id"],))
        client.delete("/api/v1/session", headers={
            "X-CSRF-Token": client.get("/api/v1/me").json()["csrf"]})
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        corrupt = client.get("/api/v1/me/preferences")
        assert corrupt.status_code == 503
        assert corrupt.json()["detail"]["code"] == "preferences_corrupt"


def test_untrusted_mr_link_is_not_sent_to_browser(tmp_path):
    """@brief A persisted non-HTTP link cannot become a clickable draft link."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=1, mr_url="javascript:alert(1)"))
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        body = client.get("/api/v1/projects/alpha/runs").json()
        assert body[0]["mr_url"] == ""


def test_run_query_pages_filters_and_enforces_project_scope(tmp_path):
    """@brief A developer pages only assigned runs and invalid bounds fail."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = profiles.create("alpha", store_root=str(tmp_path / "alpha-state"))
    profiles.create("beta", store_root=str(tmp_path / "beta-state"))
    state = StateStore(alpha.store_root)
    state.save(RunState(run_id="old", ticket_iid=1, stage="build",
                        lifecycle="done", outcome="merged by human",
                        updated_at="2026-01-01T10:00:00+00:00"))
    state.save(RunState(run_id="new", ticket_iid=2, stage="validate",
                        lifecycle="failed", outcome="VALIDATION_FAILED: tests",
                        updated_at="2026-01-03T10:00:00+00:00"))
    state.save(RunState(run_id="middle", ticket_iid=3, stage="validate",
                        lifecycle="working", updated_at="2026-01-02T10:00:00+00:00"))
    for run_id, day in (("old", "01"), ("middle", "02"), ("new", "03")):
        path = state.run_dir(run_id) / "state.json"
        saved = json.loads(path.read_text(encoding="utf-8"))
        saved["updated_at"] = f"2026-01-{day}T10:00:00+00:00"
        path.write_text(json.dumps(saved), encoding="utf-8")
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        assert client.get("/api/v1/projects/alpha/runs-page").status_code == 401
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        first = client.get("/api/v1/projects/alpha/runs-page?limit=1")
        assert first.status_code == 200
        assert first.json()["total"] == 3
        assert first.json()["counts"] == {"done": 1, "failed": 1, "working": 1}
        assert "cost" not in first.text.lower()
        assert [item["run_id"] for item in first.json()["items"]] == ["new"]
        second = client.get("/api/v1/projects/alpha/runs-page?limit=1&offset=1")
        assert [item["run_id"] for item in second.json()["items"]] == ["middle"]
        all_rows = client.get("/api/v1/projects/alpha/runs-page?limit=all")
        assert all_rows.status_code == 200
        assert [item["run_id"] for item in all_rows.json()["items"]] == [
            "new", "middle", "old"]
        filtered = client.get(
            "/api/v1/projects/alpha/runs-page?lifecycle=failed&stage=validate")
        assert filtered.json()["total"] == 1
        assert [item["run_id"] for item in filtered.json()["items"]] == ["new"]
        dated = client.get(
            "/api/v1/projects/alpha/runs-page?updated_from=2026-01-02&updated_to=2026-01-02")
        assert dated.status_code == 200
        assert [item["run_id"] for item in dated.json()["items"]] == ["middle"]
        by_outcome = client.get(
            "/api/v1/projects/alpha/runs-page?outcome=validation_failed&stage=validate")
        assert by_outcome.status_code == 200
        assert [item["run_id"] for item in by_outcome.json()["items"]] == ["new"]
        assert "cost" not in by_outcome.text.lower()
        assert client.get("/api/v1/projects/beta/runs-page?outcome=merged").status_code == 404
        assert client.get("/api/v1/projects/alpha/runs-page?outcome=%20%20").status_code == 422
        assert client.get(
            "/api/v1/projects/alpha/runs-page?outcome=" + "x" * 81).status_code == 422
        assert client.get(
            "/api/v1/projects/alpha/runs-page?updated_from=2026-01-03&updated_to=2026-01-01"
        ).status_code == 422
        assert client.get(
            "/api/v1/projects/alpha/runs-page?updated_from=not-a-date"
        ).status_code == 422
        assert client.get("/api/v1/projects/beta/runs-page").status_code == 404
        assert client.get("/api/v1/projects/alpha/runs-page?limit=0").status_code == 422
        assert client.get("/api/v1/projects/alpha/runs-page?limit=101").status_code == 422
        assert client.get(
            "/api/v1/projects/alpha/runs-page?limit=" + "9" * 5000
        ).status_code == 422
        assert client.get("/api/v1/projects/alpha/runs-page?offset=-1").status_code == 422
        assert client.get("/api/v1/projects/alpha/runs-page?stage=unknown").status_code == 422
        corrupt = state.run_dir("corrupt")
        corrupt.mkdir(parents=True)
        (corrupt / "state.json").write_text("{broken", encoding="utf-8")
        response = client.get("/api/v1/projects/alpha/runs-page")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "run_state_corrupt"


def test_run_page_date_filter_uses_utc_and_rejects_corrupt_timestamp(tmp_path):
    """@brief Last-update dates cross offsets and malformed state fails closed."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="offset", ticket_iid=4))
    path = state.run_dir("offset") / "state.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved["updated_at"] = "2026-01-01T23:30:00-02:00"
    path.write_text(json.dumps(saved), encoding="utf-8")
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get(
            "/api/v1/projects/alpha/runs-page?updated_from=2026-01-02&updated_to=2026-01-02")
        assert [item["run_id"] for item in response.json()["items"]] == ["offset"]
        saved["updated_at"] = "2026-01-02T01:30:00"
        path.write_text(json.dumps(saved), encoding="utf-8")
        invalid = client.get("/api/v1/projects/alpha/runs-page?updated_from=2026-01-02")
        assert invalid.status_code == 503
        assert invalid.json()["detail"]["code"] == "run_state_corrupt"


def test_run_page_outcome_filter_rejects_corrupt_persisted_outcome(tmp_path):
    """@brief A non-text outcome cannot be searched as if it were valid state."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="bad-outcome", ticket_iid=5))
    path = state.run_dir("bad-outcome") / "state.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved["outcome"] = {"secret": "untrusted"}
    path.write_text(json.dumps(saved), encoding="utf-8")
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        invalid = client.get("/api/v1/projects/alpha/runs-page?outcome=failed")
        assert invalid.status_code == 503
        assert invalid.json()["detail"]["code"] == "run_state_corrupt"
        assert "untrusted" not in invalid.text


def test_run_page_filters_observed_executor_and_rejects_bad_identity(tmp_path):
    """@brief Executor filter uses observed journal identity and fails closed."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="codex-run", ticket_iid=1))
    state.save(RunState(run_id="other-run", ticket_iid=2))
    state.journal("codex-run", "executor-usage", executor="codex", tokens_in=5)
    state.journal("other-run", "executor-usage", executor="opencode", tokens_in=7)
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        filtered = client.get("/api/v1/projects/alpha/runs-page?executor=codex")
        assert filtered.status_code == 200
        assert [item["run_id"] for item in filtered.json()["items"]] == ["codex-run"]
        assert filtered.json()["total"] == 1
        assert client.get("/api/v1/projects/alpha/runs-page?executor=%20").status_code == 422
        state.journal("codex-run", "executor-usage", executor={"bad": "identity"})
        invalid = client.get("/api/v1/projects/alpha/runs-page?executor=codex")
        assert invalid.status_code == 503
        assert invalid.json()["detail"]["code"] == "run_journal_corrupt"


def test_admin_can_reset_password_and_journal_is_sanitized(tmp_path):
    """@brief Reset requires an admin; no arbitrary journal fields cross the API."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=1))
    state.journal("run-1", "stage-failed", stage="build",
                  evidence="secret-value", cost_usd=25)
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        csrf = login.json()["csrf"]
        assert client.post(f"/api/v1/users/{dev['id']}/reset-password",
                           headers={"X-CSRF-Token": csrf},
                           json={"replacement": "new-long-password"}).status_code == 403
        client.delete("/api/v1/session", headers={"X-CSRF-Token": csrf})
        admin = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        csrf = admin.json()["csrf"]
        response = client.get("/api/v1/projects/alpha/runs/run-1")
        assert response.status_code == 200
        assert "secret-value" not in response.text
        assert response.json()["events"][0]["cost_usd"] == 25
        assert client.post(f"/api/v1/users/{dev['id']}/reset-password",
                           headers={"X-CSRF-Token": csrf},
                           json={"replacement": "new-long-password"}).status_code == 200
        assert web.authenticate("dev", "new-long-password")


def test_audit_history_is_administrator_only(tmp_path):
    """@brief Audited actions are inspectable without developer access."""
    app = create_app(tmp_path / "home")
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.audit(dev["id"], "test-action", "alpha", "bounded detail")
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        assert client.get("/api/v1/audit").status_code == 403
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        response = client.get("/api/v1/audit?limit=5")
        assert response.status_code == 200
        assert response.json()[0]["action"] == "login"
        assert any(row["action"] == "test-action" for row in response.json())
        assert client.get("/api/v1/audit?limit=0").status_code == 422
        assert client.get("/api/v1/audit?limit=" + "9" * 5000).status_code == 422


def test_audit_policy_retains_history_until_admin_sets_limits(tmp_path):
    """@brief Admin-configured age and byte limits prune oldest audit events."""
    app = create_app(tmp_path / "home")
    web = app.state.web_store
    for index in range(12):
        web.audit(None, f"sample-{index}", detail="x" * 40)
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()
        csrf = {"X-CSRF-Token": login["csrf"]}
        assert client.get("/api/v1/audit-policy").json() == {
            "retention_days": None, "max_bytes": None}
        assert len(client.get("/api/v1/audit?limit=all").json()) >= 12
        assert client.put("/api/v1/audit-policy", headers=csrf, json={
            "retention_days": 30, "max_bytes": 250}).status_code == 200
        retained = client.get("/api/v1/audit?limit=all").json()
        assert len(retained) == 0  # Structured rows exceed this deliberately tiny byte bound.
        assert retained == sorted(retained, key=lambda row: row["id"], reverse=True)
        assert client.get("/api/v1/audit-policy").json() == {
            "retention_days": 30, "max_bytes": 250}


def test_audit_policy_rejects_bad_values_and_forbidden_access(tmp_path):
    """@brief Invalid policies and unauthorized writes cannot change retention."""
    app = create_app(tmp_path / "home")
    web = app.state.web_store
    web.create_user("dev", "longer-password", "developer")
    with TestClient(app) as client:
        assert client.get("/api/v1/audit-policy").status_code == 401
        admin = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()
        for body in ({"retention_days": 0}, {"max_bytes": -1},
                     {"max_bytes": "garbage"}, {"other": 1}):
            assert client.put("/api/v1/audit-policy", headers={
                "X-CSRF-Token": admin["csrf"]}, json=body).status_code == 422
        assert client.put("/api/v1/audit-policy", json={
            "retention_days": 1, "max_bytes": None}).status_code == 403
        client.delete("/api/v1/session", headers={"X-CSRF-Token": admin["csrf"]})
        dev = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"}).json()
        assert client.get("/api/v1/audit-policy").status_code == 403
        assert client.put("/api/v1/audit-policy", headers={
            "X-CSRF-Token": dev["csrf"]}, json={
                "retention_days": 1, "max_bytes": None}).status_code == 403
    assert web.audit_policy() == {"retention_days": None, "max_bytes": None}


def test_audit_policy_rejects_corrupt_persisted_state(tmp_path):
    """@brief Bad policy or audit timestamps fail closed after a restart."""
    app = create_app(tmp_path / "home")
    web = app.state.web_store
    web.set_audit_policy(1, None)
    web.audit(None, "test")
    with sqlite3.connect(web.path) as connection:
        connection.execute("UPDATE audit_policy SET retention_days='invalid'")
    from adore.web.store import WebStoreError

    with pytest.raises(WebStoreError):
        web.recent_audit()
    with sqlite3.connect(web.path) as connection:
        connection.execute("UPDATE audit_policy SET retention_days=1")
        connection.execute(
            "UPDATE audit SET created_at='invalid' "
            "WHERE id=(SELECT MIN(id) FROM audit)")
    with pytest.raises(WebStoreError):
        web.recent_audit()


def test_audit_retention_age_and_unlimited_read_integrity(tmp_path):
    """@brief An old event is pruned; malformed dates never reach the browser."""
    from adore.web.store import WebStoreError

    app = create_app(tmp_path / "home")
    web = app.state.web_store
    web.audit(None, "old-event")
    with sqlite3.connect(web.path) as connection:
        connection.execute(
            "UPDATE audit SET created_at='2020-01-01T00:00:00+00:00' "
            "WHERE action='old-event'")
    assert any(row["action"] == "old-event" for row in web.recent_audit())
    web.set_audit_policy(1, None)
    assert not any(row["action"] == "old-event" for row in web.recent_audit())
    web.set_audit_policy(None, None)
    web.audit(None, "bad-event")
    with sqlite3.connect(web.path) as connection:
        connection.execute(
            "UPDATE audit SET created_at='garbage' WHERE action='bad-event'")
    with pytest.raises(WebStoreError):
        web.recent_audit(None)


def test_ten_users_twenty_projects_keep_concurrent_project_scopes(tmp_path):
    """@brief First-release account/project target retains independent grants."""
    profiles = ProfileStore(tmp_path / "home")
    for index in range(20):
        profiles.create(f"project-{index:02d}")
    app = create_app(profiles.home)
    web = app.state.web_store
    for index in range(9):
        user = web.create_user(f"dev{index}", "longer-password", "developer")
        web.set_memberships(user["id"], [f"project-{index:02d}"])

    def inspect(index):
        with TestClient(app) as client:
            login = client.post("/api/v1/session", json={
                "username": f"dev{index}", "password": "longer-password"})
            assert login.status_code == 200
            visible = client.get("/api/v1/projects")
            assert visible.status_code == 200
            assert [row["name"] for row in visible.json()] == [f"project-{index:02d}"]
            assert client.get("/api/v1/projects/project-19/metrics").status_code == 404

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(inspect, range(5)))
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        assert len(client.get("/api/v1/projects").json()) == 20
        assert len(client.get("/api/v1/metrics").json()) == 20


def test_membership_does_not_transfer_to_replaced_profile(tmp_path):
    """@brief A reused project name cannot inherit an earlier grant."""
    profiles = ProfileStore(tmp_path / "home")
    first = profiles.create("alpha")
    first.created_at = "2026-01-01T00:00:00+00:00"
    profiles.save(first)
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], [first.name])
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        assert [item["name"] for item in client.get("/api/v1/projects").json()] == ["alpha"]
        replacement = profiles.create("alpha", overwrite=True)
        replacement.created_at = "2026-02-01T00:00:00+00:00"
        profiles.save(replacement)
        assert client.get("/api/v1/projects").json() == []
        assert client.get("/api/v1/projects/alpha/metrics").status_code == 404


def test_project_id_route_survives_rename_and_reused_name(tmp_path):
    """@brief Stable API project references retain grants across a relabel."""
    profiles = ProfileStore(tmp_path / "home")
    original = profiles.create("alpha")
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    profiles.rename("alpha", "renamed")
    profiles.create("alpha")
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        visible = client.get("/api/v1/projects")
        assert visible.status_code == 200
        assert [(row["id"], row["name"]) for row in visible.json()] == [
            (original.project_id, "renamed")]
        by_id = client.get(f"/api/v1/projects/{original.project_id}")
        assert by_id.status_code == 200
        assert by_id.json()["name"] == "renamed"
        assert client.get("/api/v1/projects/alpha").status_code == 404


def test_corrupt_persisted_membership_returns_typed_error(tmp_path):
    """@brief A damaged project grant cannot disclose other project data."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    with sqlite3.connect(web.path) as connection:
        connection.execute(
            "UPDATE memberships SET project='../outside' WHERE user_id=?",
            (dev["id"],),
        )
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        response = client.get("/api/v1/projects")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "web_store_corrupt"
