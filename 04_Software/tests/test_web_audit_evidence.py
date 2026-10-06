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
@file test_web_audit_evidence.py
@brief Structured change evidence and audit trust-boundary tests.
@details All services and mutations use offline local fixtures.
"""

import json
import sqlite3

from adore.profiles import ProfileStore
from adore.web.app import create_app
from adore.web.store import WebStore, WebStoreError
from fastapi.testclient import TestClient
import pytest

from tests.test_web_enrollment import (  # noqa: F401
    _body,
    _import_body,
    _login,
    _no_probe,
    offline_wizard,
)
from tests.test_web_transfer import _review, _source

# PUBLIC API


def test_account_evidence_is_structured_and_transactional(tmp_path):
    """@brief Account evidence records known noncredential values atomically."""
    web = WebStore(tmp_path / "web.db")
    account = web.create_user_with_access("dev", "secret-password", "developer", [], True, 1)
    event = web.recent_audit()[0]
    assert event["phase"] == "apply" and event["result"] == "applied"
    assert event["resource_id"] == str(account["id"])
    assert event["before"] == {"exists": False}
    assert event["after"] == {"role": "developer", "project_ids": [], "disabled": False}
    assert event["actor_id"] == 1 and event["actor"] == "admin"
    assert "secret-password" not in json.dumps(event)
    with sqlite3.connect(web.path) as connection:
        connection.execute(
            "CREATE TRIGGER reject_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT,'no'); END"
        )
    with pytest.raises(WebStoreError):
        web.create_user_with_access("second", "secret-password", "developer", [], True, 1)
    assert [row["username"] for row in web.list_users()] == ["admin", "dev"]


def test_completion_replay_and_crash_evidence(tmp_path):
    """@brief Completion and audit commit together; replay cannot duplicate success."""
    profiles = ProfileStore(tmp_path)
    item = profiles.create("alpha")
    web = WebStore(tmp_path / "web.db")
    op = web.enqueue(1, "alpha", "resume", "", "caller-secret-key")
    web.claim_next()
    web.finish(op["id"], "succeeded", "completed")
    web.finish(op["id"], "succeeded", "completed")
    rows = [row for row in web.recent_audit(None) if row["action"] == "operation-finished"]
    assert len(rows) == 1 and rows[0]["result"] == "applied"
    assert rows[0]["project_id"] == item.project_id
    assert rows[0]["after"] == {"pickup": "active"}
    assert "caller-secret-key" not in json.dumps(rows)
    with pytest.raises(WebStoreError):
        web.finish(op["id"], "failed", "bad")
    second = web.enqueue(1, "alpha", "pause", "", "second")
    web.claim_next()
    assert web.recover_interrupted() == 1
    assert web.operation(second["id"])["status"] == "uncertain"
    assert web.recent_audit()[0]["result"] == "uncertain"


def test_authorized_server_filters_counts_and_paging(tmp_path):
    """@brief SQL paging/count sees only the exact permitted stable project."""
    profiles = ProfileStore(tmp_path)
    alpha, beta = profiles.create("alpha"), profiles.create("beta")
    app = create_app(tmp_path)
    web = app.state.web_store
    dev = web.create_user("dev", "secret-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    for index, name in enumerate(("alpha", "alpha", "beta")):
        web.enqueue(1, name, "pause", "", str(index))
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "dev", "password": "secret-password"})
        assert client.get("/api/v1/audit-page").status_code == 403
        assert (
            client.get("/api/v1/audit-page", params={"project_id": beta.project_id}).status_code
            == 403
        )
        page = client.get(
            "/api/v1/audit-page",
            params={
                "project_id": alpha.project_id,
                "action": "operation-submitted",
                "limit": 1,
                "offset": 1,
            },
        )
        assert page.status_code == 200, page.text
        assert page.json()["total"] == 2 and len(page.json()["items"]) == 1
        assert page.json()["items"][0]["project_id"] == alpha.project_id


def test_legacy_rows_have_explicit_unknowns_and_schema14(tmp_path):
    """@brief Upgrade preserves identities and historical unknown values."""
    web = WebStore(tmp_path / "web.db")
    with sqlite3.connect(web.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 14
        connection.execute(
            "INSERT INTO audit(actor_id,action,project,detail,created_at) "
            "VALUES (1,'old','alpha','historic','2020-01-01T00:00:00+00:00')"
        )
    row = WebStore(web.path).recent_audit()[0]
    assert row["before"] is None and row["result"] is None and row["project_id"] is None
    assert row["detail"] == "[redacted]"


def test_corrupt_legacy_project_fails_closed_on_public_reads(tmp_path):
    """@brief Persisted project metadata cannot expose credential-bearing URLs."""
    app = create_app(tmp_path)
    web = app.state.web_store
    secret = "https://user:fixture-password@example.test"
    with TestClient(app) as client:
        _login(client)
        connection = sqlite3.connect(web.path)
        try:
            connection.execute(
                "INSERT INTO audit(actor_id,action,project,detail,created_at) "
                "VALUES (1,'old',?,'','2020-01-01T00:00:00+00:00')", (secret,)
            )
            connection.commit()
        finally:
            connection.close()
        with pytest.raises(WebStoreError, match="audit row is corrupt"):
            web.recent_audit()
        with pytest.raises(WebStoreError, match="audit row is corrupt"):
            WebStore(web.path)
        response = client.get("/api/v1/audit-page")
        assert response.status_code == 503
        assert secret not in response.text and "fixture-password" not in response.text


def test_config_prepare_apply_discard_truthful_values(tmp_path):
    """@brief Preparing never claims application and discard preserves live value."""
    from pathlib import Path

    from adore.state import StateStore

    def _project(tmp_path):
        profiles = ProfileStore(tmp_path / "home")
        root = tmp_path / "state"
        profiles.create("alpha", store_root=str(root))
        path = profiles.config_path("alpha")
        example = Path(__file__).resolve().parents[1] / "config.example.toml"
        path.write_text(
            example.read_text().replace(
                'store_root = ".adore"', f'store_root = "{root.as_posix()}"'
            )
        )
        return profiles, path, StateStore(root)

    def _headers(client):
        return {
            "X-CSRF-Token": client.post(
                "/api/v1/session", json={"username": "admin", "password": "admin"}
            ).json()["csrf"]
        }

    profiles, path, _state = _project(tmp_path)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        current = client.get("/api/v1/projects/alpha/config").json()["revision"]
        staged = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "12", "revision": current},
        )
        assert staged.status_code == 200
        event = app.state.web_store.recent_audit()[0]
        assert event["phase"] == "prepare" and event["result"] == "prepared"
        assert event["before"] == {"value": 20} and event["after"] == {"value": 12}
        assert event["base_revision"] == current
        applied = client.post(
            "/api/v1/projects/alpha/config/apply",
            headers=headers,
            json={"candidate_revision": staged.json()["candidate_revision"]},
        )
        assert applied.status_code == 200
        event = app.state.web_store.recent_audit()[0]
        assert event["result"] == "applied" and event["before"] == {"value": 20}
        fresh = applied.json()["revision"]
        client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "13", "revision": fresh},
        )
        assert (
            client.delete("/api/v1/projects/alpha/config/pending", headers=headers).status_code
            == 200
        )
        assert app.state.web_store.recent_audit()[0]["result"] == "discarded"


def test_access_update_rolls_back_when_audit_write_fails(tmp_path):
    """@brief Account access and its known stable grant diff commit atomically."""
    profiles = ProfileStore(tmp_path)
    alpha = profiles.create("alpha")
    app = create_app(tmp_path)
    web = app.state.web_store
    dev = web.create_user("dev", "secret-password", "developer")
    with TestClient(app) as client:
        headers = {
            "X-CSRF-Token": client.post(
                "/api/v1/session", json={"username": "admin", "password": "admin"}
            ).json()["csrf"]
        }
        response = client.put(
            "/api/v1/projects/alpha/access/" + str(dev["id"]),
            headers=headers,
            json={"granted": True},
        )
        assert response.status_code == 200
        row = web.recent_audit()[0]
        assert row["before"] == {"project_ids": []}
        assert row["after"] == {"project_ids": [alpha.project_id]}
        with sqlite3.connect(web.path) as connection:
            connection.execute(
                "CREATE TRIGGER reject_audit BEFORE INSERT ON audit "
                "BEGIN SELECT RAISE(ABORT,'no'); END"
            )
        response = client.put(
            "/api/v1/projects/alpha/access/" + str(dev["id"]),
            headers=headers,
            json={"granted": False},
        )
        assert response.status_code != 200
        assert web.membership_ids(dev["id"]) == [alpha.project_id]


def test_nested_secret_and_error_metadata_is_redacted(tmp_path):
    """@brief Nested credential, environment and arbitrary text never reach evidence."""
    web = WebStore(tmp_path / "web.db")
    web.audit(
        1,
        "config-updated",
        detail="sensitive-password",
        resource_type="config",
        resource_id="executor.default",
        before={
            "password": "nested-password",
            "value": {"env": {"API_KEY": "hidden"}, "value": "arbitrary-secret"},
        },
        after={"token": "secret-token", "value": "secret-value"},
    )
    text = json.dumps(web.recent_audit())
    for secret in (
        "sensitive-password",
        "nested-password",
        "hidden",
        "arbitrary-secret",
        "secret-token",
        "secret-value",
    ):
        assert secret not in text
    with sqlite3.connect(web.path) as connection:
        raw = connection.execute("SELECT detail,evidence FROM audit").fetchone()
    assert "sensitive-password" not in str(raw)


def test_retention_does_not_break_filesystem_confirmation(tmp_path):
    """@brief Explicit history deletion never prevents finishing an owning change."""
    web = WebStore(tmp_path / "web.db")
    web.set_audit_policy(None, 1)
    key = web.begin_change(
        1, "config-applied", resource_type="config", resource_id="budgets.max_iterations"
    )
    web.confirm_change(key, after={"value": 12})
    assert web.recent_audit() == []


def test_schema13_upgrade_preserves_actual_legacy_identity(tmp_path):
    """@brief A genuine old audit shape upgrades atomically without historic fabrication."""
    web = WebStore(tmp_path / "web.db")
    web.change_password(1, "admin", "replacement-password")
    with sqlite3.connect(web.path) as connection:
        connection.execute("DROP TABLE audit")
        connection.execute("DROP TABLE audit_attempts")
        connection.execute(
            "CREATE TABLE audit(id INTEGER PRIMARY KEY, actor_id INTEGER, "
            "action TEXT NOT NULL, project TEXT NOT NULL DEFAULT '', "
            "detail TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO audit VALUES(7,1,'config-applied','alpha',"
            "'budgets.max_iterations','2020-01-01T00:00:00+00:00')"
        )
        connection.execute("PRAGMA user_version=13")
    restored = WebStore(web.path)
    assert restored.authenticate("admin", "replacement-password")["id"] == 1
    row = restored.recent_audit()[0]
    assert row["id"] == 7 and row["action"] == "config-applied"
    assert all(row[field] is None for field in ("result", "before", "after", "project_id"))
    assert restored.audit_policy() == {"retention_days": None, "max_bytes": None}


@pytest.mark.parametrize(
    "damage", ["schema", "timestamp", "json", "secret", "duplicate", "column", "index", "attempt"]
)
def test_corrupt_audit_storage_fails_closed_without_identity_reset(tmp_path, damage):
    """@brief Persisted malformed evidence/shape rejects initialization and reads."""
    web = WebStore(tmp_path / "web.db")
    web.change_password(1, "admin", "replacement-password")
    web.audit(1, "config-applied", resource_type="config", resource_id="budgets.max_iterations")
    with sqlite3.connect(web.path) as connection:
        if damage == "schema":
            connection.execute("PRAGMA user_version=99")
        elif damage == "timestamp":
            connection.execute("UPDATE audit SET created_at='bad'")
        elif damage in ("json", "secret", "duplicate"):
            raw = connection.execute("SELECT evidence FROM audit").fetchone()[0]
            if damage == "json":
                raw = "{bad"
            elif damage == "secret":
                payload = json.loads(raw)
                payload["before"] = {"password": "not-safe"}
                raw = json.dumps(payload)
            else:
                raw = raw.replace('"schema":1', '"schema":1,"schema":1')
            connection.execute("UPDATE audit SET evidence=?", (raw,))
        elif damage == "column":
            connection.execute("ALTER TABLE audit DROP COLUMN evidence")
        elif damage == "index":
            connection.execute("DROP INDEX audit_event_key")
        else:
            connection.execute("DROP TABLE audit_attempts")
    with pytest.raises(WebStoreError):
        WebStore(web.path)
    with pytest.raises(WebStoreError):
        web.recent_audit(None)
    with sqlite3.connect(web.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert connection.execute("SELECT password_hash FROM users").fetchone()[0] != "admin"


def test_bad_legacy_upgrade_rolls_back_schema_atomically(tmp_path):
    """@brief Invalid old audit rows leave the version and identity intact."""
    web = WebStore(tmp_path / "web.db")
    with sqlite3.connect(web.path) as connection:
        connection.execute("DROP TABLE audit")
        connection.execute("DROP TABLE audit_attempts")
        connection.execute(
            "CREATE TABLE audit(id INTEGER PRIMARY KEY, actor_id INTEGER, "
            "action TEXT NOT NULL, project TEXT NOT NULL DEFAULT '', "
            "detail TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL)"
        )
        connection.execute("INSERT INTO audit VALUES(1,1,'config-applied','alpha','','bad')")
        connection.execute("PRAGMA user_version=13")
    with pytest.raises(WebStoreError):
        WebStore(web.path)
    with sqlite3.connect(web.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 13
        assert "evidence" not in {row[1] for row in connection.execute("PRAGMA table_info(audit)")}
        assert connection.execute("SELECT COUNT(*) FROM audit").fetchone()[0] == 1


def test_operation_completion_fault_rolls_back_status_and_event(tmp_path):
    """@brief A failed audit commit leaves the running operation available for reconciliation."""
    ProfileStore(tmp_path).create("alpha")
    web = WebStore(tmp_path / "web.db")
    op = web.enqueue(1, "alpha", "pause", "", "one")
    web.claim_next()
    with sqlite3.connect(web.path) as connection:
        connection.execute(
            "CREATE TRIGGER reject_audit BEFORE INSERT ON audit "
            "BEGIN SELECT RAISE(ABORT,'private-secret'); END"
        )
    with pytest.raises(WebStoreError, match="is corrupt"):
        web.finish(op["id"], "succeeded", "completed")
    assert web.operation(op["id"])["status"] == "running"
    assert not [row for row in web.recent_audit() if row["result"] == "applied"]


def test_admin_filters_counts_period_and_bad_queries(tmp_path):
    """@brief Combined SQL filters and half-open dates count all matching rows."""
    profiles = ProfileStore(tmp_path)
    alpha, beta = profiles.create("alpha"), profiles.create("beta")
    app = create_app(tmp_path)
    web = app.state.web_store
    other = web.create_user("other", "secret-password", "admin")
    web.audit(1, "config-applied", "alpha", resource_type="config", resource_id="setting")
    web.audit(other["id"], "config-applied", "beta", resource_type="config", resource_id="setting")
    web.audit(
        1,
        "config-staged",
        "alpha",
        resource_type="config",
        resource_id="setting",
        phase="prepare",
        result="prepared",
    )
    with sqlite3.connect(web.path) as connection:
        connection.execute("UPDATE audit SET created_at='2026-01-02T00:00:00+00:00'")
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        query = {
            "actor_id": 1,
            "project_id": alpha.project_id,
            "action": "config-applied",
            "limit": 1,
            "from": "2026-01-02T00:00:00Z",
            "to": "2026-01-03T00:00:00Z",
        }
        response = client.get("/api/v1/audit-page", params=query)
        assert response.status_code == 200 and response.json()["total"] == 1
        assert response.json()["items"][0]["project_id"] == alpha.project_id
        assert client.get("/api/v1/audit-page", params={**query, "offset": 1}).json()["items"] == []
        assert (
            client.get(
                "/api/v1/audit-page",
                params={**query, "to": "2026-01-02T00:00:00Z", "from": "2026-01-01T00:00:00Z"},
            ).json()["total"]
            == 0
        )
        assert (
            client.get("/api/v1/audit-page", params={"project_id": beta.project_id}).json()["total"]
            == 1
        )
        for oversized in ({"actor_id": 2**80}, {"offset": 2**80}):
            with pytest.raises(WebStoreError):
                web.audit_page(10, oversized.get("offset", 0), actor_id=oversized.get("actor_id"))
        for bad in (
            {"from": "bad"},
            {"from": "2026-01-02T00:00:00"},
            {"actor_id": -1},
            {"actor_id": 2**80},
            {"offset": 2**80},
            {"project_id": "bad"},
            {"action": "secret/value"},
            {"limit": "bad"},
            {"offset": -1},
        ):
            assert client.get("/api/v1/audit-page", params=bad).status_code == 422


def test_dev_project_history_excludes_admin_and_legacy_metadata(tmp_path):
    """@brief Grant filtering excludes administrator access/price rows and old name-only events."""
    profiles = ProfileStore(tmp_path)
    alpha = profiles.create("alpha")
    app = create_app(tmp_path)
    web = app.state.web_store
    dev = web.create_user("dev", "secret-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    web.audit(1, "membership-changed", "alpha", resource_type="access", resource_id=str(dev["id"]))
    web.audit(1, "price-created", "alpha")
    web.audit(
        1,
        "config-applied",
        "alpha",
        resource_type="config",
        resource_id="budgets.max_cost_usd",
        before={"value": 100},
        after={"value": 200},
    )
    web.audit(
        1, "config-applied", "alpha", resource_type="config", resource_id="budgets.max_iterations"
    )
    with sqlite3.connect(web.path) as connection:
        connection.execute(
            "INSERT INTO audit(actor_id,action,project,detail,created_at) "
            "VALUES(1,'config-applied','alpha','','2020-01-01T00:00:00+00:00')"
        )
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "dev", "password": "secret-password"})
        response = client.get("/api/v1/audit-page", params={"project_id": alpha.project_id})
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["action"] == "config-applied"
        web.set_memberships(dev["id"], [])
        assert (
            client.get("/api/v1/audit-page", params={"project_id": alpha.project_id}).status_code
            == 403
        )


def test_filesystem_apply_crash_retry_preserves_original_before_once(tmp_path, monkeypatch):
    """@brief Crash after file replacement stays uncertain; retry confirms the same attempt."""
    from pathlib import Path

    profiles = ProfileStore(tmp_path / "home")
    root = tmp_path / "state"
    profiles.create("alpha", store_root=str(root))
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    path.write_text(
        example.read_text().replace('store_root = ".adore"', f'store_root = "{root.as_posix()}"')
    )
    app = create_app(profiles.home)
    web = app.state.web_store
    original = web.confirm_change
    with TestClient(app) as client:
        headers = {
            "X-CSRF-Token": client.post(
                "/api/v1/session", json={"username": "admin", "password": "admin"}
            ).json()["csrf"]
        }
        base = client.get("/api/v1/projects/alpha/config").json()["revision"]
        staged = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "12", "revision": base},
        ).json()

        def crash(*args, **kwargs):
            """@brief Simulate failed audit confirmation after the config replacement."""
            raise WebStoreError("private-sensitive-crash")

        monkeypatch.setattr(web, "confirm_change", crash)
        response = client.post(
            "/api/v1/projects/alpha/config/apply",
            headers=headers,
            json={"candidate_revision": staged["candidate_revision"]},
        )
        assert response.status_code == 503 and "private-sensitive-crash" not in response.text
        row = [row for row in web.recent_audit() if row["action"] == "config-applied"][0]
        assert row["result"] == "uncertain" and row["after"] is None
        assert row["before"] == {"value": 20}
        assert (profiles.profile_dir("alpha") / "pending_config.json").is_file()
        monkeypatch.setattr(web, "confirm_change", original)
    # Reopen persistent storage and the HTTP service, retaining only durable evidence.
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = {
            "X-CSRF-Token": client.post(
                "/api/v1/session", json={"username": "admin", "password": "admin"}
            ).json()["csrf"]
        }
        response = client.post(
            "/api/v1/projects/alpha/config/apply",
            headers=headers,
            json={"candidate_revision": staged["candidate_revision"]},
        )
        assert response.status_code == 200
        rows = [
            row for row in app.state.web_store.recent_audit() if row["action"] == "config-applied"
        ]
        assert len(rows) == 1
        assert rows[0]["before"] == {"value": 20} and rows[0]["after"] == {"value": 12}
        assert rows[0]["result"] == "applied"


@pytest.mark.parametrize("code", [None, True, "0", 0.0])
def test_invalid_executor_exit_code_cannot_claim_applied(tmp_path, code):
    """@brief A malformed injected command result remains uncertain without known after."""
    from adore.web.commands import CommandWorker

    profiles = ProfileStore(tmp_path)
    profiles.create("alpha")
    web = WebStore(tmp_path / "web.db")
    op = web.enqueue(1, "alpha", "pause", "", "one")
    worker = CommandWorker(profiles, web, runner=lambda _argv, _env: code)
    assert worker.run_pending() == 1
    assert web.operation(op["id"])["status"] == "uncertain"
    row = web.recent_audit()[0]
    assert row["result"] == "uncertain" and row["after"] is None


def test_enrollment_and_exact_import_evidence_has_known_identity_and_stopped_result(tmp_path):
    """@brief Preview stays prepared; enrollment/import commits known stopped state."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers = _login(client)
        body = _body(tmp_path)
        response = client.post("/api/v1/projects/setup-preview", json=body, headers=headers)
        assert response.status_code == 200
        assert app.state.web_store.recent_audit()[0]["result"] == "prepared"
        created = client.post(
            "/api/v1/projects/setup-create",
            json={**body, "revision": response.json()["revision"]},
            headers=headers,
        )
        assert created.status_code == 200, created.text
        event = app.state.web_store.recent_audit()[0]
        assert event["result"] == "applied" and event["project_id"] == created.json()["id"]
        assert event["before"] == {"exists": False}
        assert event["after"] == {"exists": True, "pickup": "stopped"}
        import_body = _import_body(tmp_path / "import")
        preview = client.post("/api/v1/projects/import-preview", json=import_body, headers=headers)
        assert preview.status_code == 200, preview.text
        assert app.state.web_store.recent_audit()[0]["action"] == "toml-import-prepared"
        imported = client.post(
            "/api/v1/projects/import",
            json={**import_body, "revision": preview.json()["revision"]},
            headers=headers,
        )
        assert imported.status_code == 200, imported.text
        event = app.state.web_store.recent_audit()[0]
        assert event["action"] == "project-imported" and event["result"] == "applied"
        assert (
            event["project_id"] == imported.json()["id"] and event["after"]["pickup"] == "stopped"
        )


@pytest.mark.parametrize("method", ["file", "project"])
def test_transfer_evidence_distinguishes_import_clone_and_preparation(tmp_path, method):
    """@brief Transfer records known source and stable target revisions truthfully."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers, body, _preview, _raw = _source(client, app, tmp_path, method)
        reviewed, preview = _review(client, body, headers)
        event = app.state.web_store.recent_audit()[0]
        assert event["result"] == "prepared" and event["phase"] == "prepare"
        assert event["base_revision"] == body["source_revision"]
        assert event["action"] == (
            "clone-prepared" if method == "project" else "settings-import-prepared"
        )
        result = client.post("/api/v1/projects/transfer-create", json=reviewed, headers=headers)
        assert result.status_code == 200, result.text
        event = app.state.web_store.recent_audit()[0]
        assert event["result"] == "applied" and event["project_id"] == result.json()["id"]
        assert event["candidate_revision"] == preview["config_revision"]
        assert event["base_revision"] == body["source_revision"]
        assert event["action"] == ("project-cloned" if method == "project" else "settings-imported")


def test_policy_evidence_and_pruning_share_one_transaction(tmp_path):
    """@brief Policy diffs and deletion count agree; write failure rolls limits back."""
    web = WebStore(tmp_path / "web.db")
    saved = web.set_audit_policy(30, None, actor_id=1)
    assert saved == {"retention_days": 30, "max_bytes": None, "deleted_events": 0}
    event = web.recent_audit()[0]
    assert event["before"] == {"retention_days": None, "max_bytes": None}
    assert event["after"] == {"retention_days": 30, "max_bytes": None}
    with sqlite3.connect(web.path) as connection:
        connection.execute(
            "CREATE TRIGGER reject_policy BEFORE INSERT ON audit "
            "BEGIN SELECT RAISE(ABORT,'private fault'); END"
        )
    with pytest.raises(WebStoreError):
        web.set_audit_policy(None, 1, actor_id=1)
    assert web.audit_policy() == {"retention_days": 30, "max_bytes": None}
    assert len(web.recent_audit()) == 1
    with sqlite3.connect(web.path) as connection:
        connection.execute("DROP TRIGGER reject_policy")
    assert web.set_audit_policy(None, 1, actor_id=1)["deleted_events"] == 2
    assert web.recent_audit() == []
    assert web.audit_policy() == {"retention_days": None, "max_bytes": 1}


def test_enrollment_rollback_retains_uncertain_attempt(tmp_path, monkeypatch):
    """@brief Failed publication retains no applied claim or visible project."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers = _login(client)
        body = _body(tmp_path)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        original = app.state.web_store.audit

        def fault(actor, action, *args, **kwargs):
            """@brief Reject owning confirmation without exposing its private cause."""
            if action == "project-created":
                raise WebStoreError("private audit credential secret")
            return original(actor, action, *args, **kwargs)

        monkeypatch.setattr(app.state.web_store, "audit", fault)
        result = client.post(
            "/api/v1/projects/setup-create",
            json={**body, "revision": preview["revision"]},
            headers=headers,
        )
        assert result.status_code >= 400
        assert "private audit" not in result.text
        assert app.state.profiles.list_profiles() == []
        event = app.state.web_store.recent_audit()[0]
        assert event["action"] == "project-created" and event["result"] == "uncertain"
        assert event["after"] is None and event["project_id"] is None
        assert "private audit" not in json.dumps(event)


# END OF FILE
