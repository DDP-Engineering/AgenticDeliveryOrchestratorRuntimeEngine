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
@file test_web_archive.py
@brief Project archive and restore contract tests.
@details Archived projects retain history but cannot start new work.
"""

import json
from pathlib import Path

from adore.cli import EXIT_ERROR, main
from adore.profiles import ProfileError, ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from adore.web.commands import CommandWorker
from adore.web.store import WebStore
from fastapi.testclient import TestClient
import pytest


def _login(client):
    """@brief Return the administrator's CSRF token."""
    return client.post("/api/v1/session", json={
        "username": "admin", "password": "admin"}).json()["csrf"]


def test_archive_retains_history_and_restore_reenables_operations(tmp_path):
    """@brief Archived history remains readable and restore permits pickup."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    state = StateStore(profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="done"))
    with TestClient(create_app(profiles.home)) as client:
        csrf = _login(client)
        headers = {"X-CSRF-Token": csrf}
        response = client.post("/api/v1/projects/alpha/archive", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["archived"] is True
        assert client.get("/api/v1/projects/alpha").json()["runs"] == 1
        assert client.get("/api/v1/projects/alpha/runs").status_code == 200
        blocked = client.post("/api/v1/projects/alpha/operations/start", headers=headers,
                              json={"ticket_iid": 43, "idempotency_key": "new-start"})
        assert blocked.status_code == 409
        response = client.post("/api/v1/projects/alpha/restore", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["archived"] is False
        queued = client.post("/api/v1/projects/alpha/operations/start", headers=headers,
                             json={"ticket_iid": 43, "idempotency_key": "new-start"})
        assert queued.status_code == 200


def test_archive_rejects_nonterminal_runs_and_queued_operations(tmp_path):
    """@brief Archive never strands an active run or already queued work."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    state = StateStore(profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="working"))
    with TestClient(create_app(profiles.home)) as client:
        csrf = _login(client)
        headers = {"X-CSRF-Token": csrf}
        assert client.post("/api/v1/projects/alpha/archive", headers=headers).status_code == 409
        state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="done"))
        web = WebStore(profiles.home / "web.db")
        admin = web.authenticate("admin", "admin")
        web.enqueue(admin["id"], "alpha", "start", "43", "queued")
        assert client.post("/api/v1/projects/alpha/archive", headers=headers).status_code == 409
        assert profiles.load("alpha").archived is False


def test_human_handoff_is_visible_and_preserves_web_ownership(tmp_path):
    """@brief A pending transfer blocks writes; completed handoff is terminal history."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    state = StateStore(profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=42,
                        lifecycle="handoff-pending"))
    with TestClient(create_app(profiles.home)) as client:
        headers = {"X-CSRF-Token": _login(client)}
        cancel = "/api/v1/projects/alpha/operations/cancel"
        body = {"run_id": "run-1", "idempotency_key": "pending-cancel", "confirmed": True}
        response = client.post(cancel, headers=headers, json=body)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "run_already_finished"
        assert client.post("/api/v1/projects/alpha/archive",
                           headers=headers).status_code == 409
        state.save(RunState(run_id="run-1", ticket_iid=42,
                            lifecycle="handed-off"))
        page = client.get("/api/v1/projects/alpha/runs-page?lifecycle=handed-off")
        assert page.status_code == 200, page.text
        assert [row["run_id"] for row in page.json()["items"]] == ["run-1"]
        body["idempotency_key"] = "terminal-cancel"
        response = client.post(cancel, headers=headers, json=body)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "run_already_finished"
        assert client.post("/api/v1/projects/alpha/archive",
                           headers=headers).status_code == 200


def test_archive_rejects_active_conductor_lock(tmp_path):
    """@brief An idle-looking project with a running poll cannot archive."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    state = StateStore(profiles.default_store_root("alpha"))
    assert state.acquire_lock()
    try:
        with TestClient(create_app(profiles.home)) as client:
            csrf = _login(client)
            response = client.post("/api/v1/projects/alpha/archive",
                                   headers={"X-CSRF-Token": csrf})
            assert response.status_code == 409
    finally:
        state.release_lock()
    assert profiles.load("alpha").archived is False


def test_archive_requires_admin_csrf_and_rejects_corrupt_metadata(tmp_path):
    """@brief Developer writes and malformed stored archive flags fail closed."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    web = WebStore(profiles.home / "web.db")
    developer = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(developer["id"], ["alpha"])
    with TestClient(create_app(profiles.home)) as client:
        csrf = _login(client)
        assert client.post("/api/v1/projects/alpha/archive").status_code == 403
        client.delete("/api/v1/session", headers={"X-CSRF-Token": csrf})
        dev_csrf = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"}).json()["csrf"]
        assert client.post("/api/v1/projects/alpha/archive", headers={
            "X-CSRF-Token": dev_csrf}).status_code == 403
    path = profiles.profile_dir("alpha") / "profile.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["archived"] = "false"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProfileError):
        profiles.load("alpha")


def test_worker_rejects_queued_work_after_external_archive(tmp_path):
    """@brief A stale queued command cannot execute after archive."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    web = WebStore(profiles.home / "web.db")
    admin = web.authenticate("admin", "admin")
    operation = web.enqueue(admin["id"], "alpha", "start", "42", "queued")
    profile = profiles.load("alpha")
    profile.archived = True
    profiles.save(profile)
    calls = []
    worker = CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0)
    assert worker.run_pending() == 1
    assert calls == []
    assert web.operation(operation["id"])["status"] == "failed"


def test_named_cli_profile_cannot_poll_while_archived(tmp_path, monkeypatch, capsys):
    """@brief CLI pickup observes archive, including active-profile resolution."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    profiles.config_path("alpha").write_bytes(example.read_bytes())
    profile.archived = True
    profiles.save(profile)
    profiles.set_active("alpha")
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    assert main(["--profile", "alpha", "run", "--once"]) == EXIT_ERROR
    assert main(["run", "--once"]) == EXIT_ERROR
    assert "archived" in capsys.readouterr().out
