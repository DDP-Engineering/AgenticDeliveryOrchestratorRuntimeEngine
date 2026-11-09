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
@file test_web_delete.py
@brief Web project deletion contract tests.
@details Only a confirmed, archived and idle project is queued for deletion,
         and the worker rechecks role, archive state and identity before it
         runs the resource-removing CLI delete.
"""

# IMPORTS
import sys

from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from adore.web.commands import CommandWorker
from fastapi.testclient import TestClient


# LOCAL HELPERS
def _login(client: TestClient, user: str = "admin", password: str = "admin") -> dict:
    login = client.post("/api/v1/session", json={"username": user, "password": password})
    csrf = login.json()["csrf"]
    return {"X-CSRF-Token": csrf}


def _archived_project(home, name="alpha", lifecycle="done") -> ProfileStore:
    profiles = ProfileStore(home)
    profiles.create(name)
    StateStore(profiles.default_store_root(name)).save(
        RunState(run_id="run-1", ticket_iid=1, lifecycle=lifecycle))
    profile = profiles.load(name)
    profile.archived = True
    profiles.save(profile)
    return profiles


def _delete(client, headers, name="alpha", confirm="alpha", key="delete-key-1"):
    return client.post(f"/api/v1/projects/{name}/delete", headers=headers,
                       json={"confirm_name": confirm, "idempotency_key": key})


# TESTS
def test_confirmed_archived_project_is_deleted_by_the_worker(tmp_path):
    """@brief The API queues the delete; the worker runs the CLI and the project goes."""
    profiles = _archived_project(tmp_path / "home")
    app = create_app(profiles.home)
    web = app.state.web_store
    calls = []

    def runner(argv, env):
        calls.append(argv)
        profiles.delete("alpha")  # what the real CLI does after removing resources
        return 0

    with TestClient(app) as client:
        headers = _login(client)
        queued = _delete(client, headers)
        assert queued.status_code == 200, queued.text
        operation = queued.json()
        assert operation["status"] == "pending"
        assert CommandWorker(profiles, web, runner=runner).run_pending() == 1
        assert calls == [[sys.executable, "-m", "adore", "profile", "delete", "alpha",
                          "--force", "--remove-resources"]]
        assert not profiles.exists("alpha")
        status = client.get(f"/api/v1/operations/{operation['id']}")
        assert status.status_code == 200, status.text
        assert status.json()["status"] == "succeeded" and status.json()["action"] == "delete"
        actions = [row["action"] for row in web.recent_audit(20)]
        assert "project-delete-requested" in actions and "project-deleted" in actions
        assert "alpha" not in [item["name"] for item in client.get("/api/v1/projects").json()]
        web.create_user("dev", "longer-password", "developer")
        _login(client, "dev", "longer-password")
        hidden = client.get(f"/api/v1/operations/{operation['id']}")
        assert hidden.status_code == 404


def test_delete_is_refused_unless_archived_confirmed_and_idle(tmp_path):
    """@brief Every unsafe request is refused with a stable code and changes nothing."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    state = StateStore(profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="done"))
    app = create_app(profiles.home)
    web = app.state.web_store
    web.create_user("dev", "longer-password", "developer")
    with TestClient(app) as client:
        headers = _login(client)
        response = _delete(client, headers)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "project_not_archived"
        profile = profiles.load("alpha")
        profile.archived = True
        profiles.save(profile)
        response = _delete(client, headers, confirm="Alpha")
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "delete_confirmation_mismatch"
        assert client.post("/api/v1/projects/alpha/delete", json={
            "confirm_name": "alpha", "idempotency_key": "delete-key-1"}).status_code == 403
        state.save(RunState(run_id="run-2", ticket_iid=2, lifecycle="working"))
        response = _delete(client, headers)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "project_has_active_work"
        state.save(RunState(run_id="run-2", ticket_iid=2, lifecycle="handed-off"))
        assert _delete(client, headers, key="delete-key-2").status_code == 200
        response = _delete(client, headers, key="delete-key-3")
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "project_has_active_work"
        dev_headers = _login(client, "dev", "longer-password")
        response = _delete(client, dev_headers, key="delete-key-4")
        assert response.status_code == 403 and response.json()["detail"]["code"] == "admin_required"
    assert profiles.exists("alpha")


def test_corrupt_run_state_blocks_deletion(tmp_path):
    """@brief Unreadable run state is reported, never deleted through the web."""
    profiles = _archived_project(tmp_path / "home")
    broken = StateStore(profiles.default_store_root("alpha")).root / "runs" / "broken"
    broken.mkdir(parents=True)
    (broken / "state.json").write_text("{not json", encoding="utf-8")
    with TestClient(create_app(profiles.home)) as client:
        response = _delete(client, _login(client))
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "run_state_corrupt"
    assert profiles.exists("alpha")


def test_worker_refuses_delete_after_actor_or_identity_changes(tmp_path):
    """@brief A demoted, disabled or replaced-project delete never runs."""
    import sqlite3

    profiles = _archived_project(tmp_path / "home")
    app = create_app(profiles.home)
    web = app.state.web_store
    second = web.create_user("second", "longer-password", "admin")
    calls = []
    worker = CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0)
    with TestClient(app) as client:
        queued = _delete(client, _login(client, "second", "longer-password")).json()
    with sqlite3.connect(profiles.home / "web.db") as connection:
        connection.execute("UPDATE users SET role='developer' WHERE id=?", (second["id"],))
    assert worker.run_pending() == 1
    assert web.operation(queued["id"])["status"] == "failed"
    third = web.create_user("third", "longer-password", "admin")
    with TestClient(app) as client:
        headers = _login(client, "third", "longer-password")
        queued = _delete(client, headers, key="delete-key-8").json()
    web.disable_user(third["id"])
    assert worker.run_pending() == 1
    assert web.operation(queued["id"])["status"] == "failed"
    with TestClient(app) as client:
        queued = _delete(client, _login(client), key="delete-key-9").json()
    profiles.delete("alpha")
    _archived_project(tmp_path / "home")  # same name, new immutable project ID
    assert worker.run_pending() == 1
    assert web.operation(queued["id"])["status"] == "failed"
    assert calls == [] and profiles.exists("alpha")


def test_worker_rechecks_archive_state_before_deleting(tmp_path):
    """@brief A project restored after queuing is not deleted."""
    profiles = _archived_project(tmp_path / "home")
    app = create_app(profiles.home)
    web = app.state.web_store
    calls = []
    with TestClient(app) as client:
        headers = _login(client)
        operation = _delete(client, headers).json()
    profile = profiles.load("alpha")
    profile.archived = False
    profiles.save(profile)
    worker = CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0)
    assert worker.run_pending() == 1
    assert calls == []
    assert web.operation(operation["id"])["status"] == "failed"
    assert profiles.exists("alpha")


# END OF FILE
