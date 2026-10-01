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
@file test_web_pending_config.py
@brief Staged administrator configuration edit contract tests.
@details A reviewed candidate applies only when the project is quiescent.
"""

import json
from pathlib import Path

from adore.config import load_config
from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest


def _project(tmp_path):
    """@brief Make a profile whose metadata and config share one state root."""
    profiles = ProfileStore(tmp_path / "home")
    root = tmp_path / "state"
    profiles.create("alpha", store_root=str(root))
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    text = example.read_text(encoding="utf-8").replace(
        'store_root = ".adore"', f'store_root = "{root.as_posix()}"')
    path.write_text(text, encoding="utf-8")
    return profiles, path, StateStore(root)


def _headers(client):
    """@brief Authenticate the bootstrap administrator."""
    csrf = client.post("/api/v1/session", json={
        "username": "admin", "password": "admin"}).json()["csrf"]
    return {"X-CSRF-Token": csrf}


def test_stage_review_apply_and_discard_config(tmp_path):
    """@brief Stage leaves live TOML untouched until explicit safe apply."""
    profiles, path, state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        original = path.read_bytes()
        body = {"key": "budgets.max_iterations", "value": "12", "revision": revision}
        stage = client.post("/api/v1/projects/alpha/config/pending", json=body,
                            headers=headers)
        assert stage.status_code == 200, stage.text
        candidate = stage.json()["candidate_revision"]
        assert stage.json()["key"] == "budgets.max_iterations"
        assert path.read_bytes() == original
        assert client.get("/api/v1/projects/alpha/config/pending").json() == stage.json()
        assert client.post("/api/v1/projects/alpha/config/pending", json=body,
                           headers=headers).status_code == 409
        state.save(RunState(run_id="working", ticket_iid=42, lifecycle="working"))
        blocked = client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": candidate}, headers=headers)
        assert blocked.status_code == 409
        assert path.read_bytes() == original
        state.save(RunState(run_id="working", ticket_iid=42, lifecycle="done"))
        applied = client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": candidate}, headers=headers)
        assert applied.status_code == 200, applied.text
        assert applied.json()["revision"] == candidate
        assert load_config(path).budgets.max_iterations == 12
        assert client.get("/api/v1/projects/alpha/config/pending").json() is None
        fresh = client.get("/api/v1/projects/alpha/config").json()["revision"]
        stage = client.post("/api/v1/projects/alpha/config/pending", json={
            "key": "budgets.max_iterations", "value": "13", "revision": fresh},
            headers=headers)
        assert stage.status_code == 200
        assert client.delete("/api/v1/projects/alpha/config/pending",
                             headers=headers).status_code == 200
        assert load_config(path).budgets.max_iterations == 12


def test_pending_config_rejects_stale_corrupt_and_unauthorized_actions(tmp_path):
    """@brief Pending state and administrator/CSRF boundaries fail closed."""
    profiles, path, state = _project(tmp_path)
    app = create_app(profiles.home)
    web = app.state.web_store
    developer = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(developer["id"], ["alpha"])
    with TestClient(app) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        body = {"key": "budgets.max_iterations", "value": "12", "revision": revision}
        assert client.post("/api/v1/projects/alpha/config/pending",
                           json=body).status_code == 403
        assert client.post("/api/v1/projects/alpha/config/pending", json={
            **body, "revision": "stale"}, headers=headers).status_code == 409
        staged = client.post("/api/v1/projects/alpha/config/pending",
                             json=body, headers=headers)
        assert staged.status_code == 200
        assert client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": "0" * 64}, headers=headers).status_code == 409
        assert state.acquire_lock()
        try:
            assert client.post("/api/v1/projects/alpha/config/apply", json={
                "candidate_revision": staged.json()["candidate_revision"]},
                headers=headers).status_code == 409
        finally:
            state.release_lock()
        path.write_text(path.read_text(encoding="utf-8") + "\n# host edit\n",
                        encoding="utf-8")
        assert client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": staged.json()["candidate_revision"]},
            headers=headers).status_code == 409
        pending_path = profiles.profile_dir("alpha") / "pending_config.json"
        pending_path.write_text("{bad-json", encoding="utf-8")
        assert client.get("/api/v1/projects/alpha/config/pending").status_code == 503
        assert client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": staged.json()["candidate_revision"]},
            headers=headers).status_code == 503
        client.delete("/api/v1/session", headers=headers)
        dev_csrf = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"}).json()["csrf"]
        assert client.get("/api/v1/projects/alpha/config/pending").status_code == 403
        assert client.delete("/api/v1/projects/alpha/config/pending", headers={
            "X-CSRF-Token": dev_csrf}).status_code == 403


def test_direct_config_edit_cannot_bypass_active_or_pending_work(tmp_path):
    """@brief Legacy direct edits observe the same safe application boundary."""
    profiles, path, state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        body = {"key": "budgets.max_iterations", "value": "12", "revision": revision}
        original = path.read_bytes()
        state.save(RunState(run_id="working", ticket_iid=42, lifecycle="working"))
        assert client.put("/api/v1/projects/alpha/config", json=body,
                          headers=headers).status_code == 409
        state.save(RunState(run_id="working", ticket_iid=42, lifecycle="done"))
        assert client.post("/api/v1/projects/alpha/config/pending", json=body,
                           headers=headers).status_code == 200
        assert client.put("/api/v1/projects/alpha/config", json=body,
                          headers=headers).status_code == 409
        assert path.read_bytes() == original


def test_identity_edit_requires_paused_pickup_before_apply(tmp_path):
    """@brief High-impact configuration needs an explicit pickup pause."""
    profiles, path, state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        staged = client.post("/api/v1/projects/alpha/config/pending", json={
            "key": "platform.repo", "value": "org/renamed", "revision": revision,
        }, headers=headers)
        assert staged.status_code == 200, staged.text
        assert staged.json()["restart_required"] is True
        candidate = staged.json()["candidate_revision"]
        assert client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": candidate}, headers=headers).status_code == 409
        state.pause()
        assert client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": candidate}, headers=headers).status_code == 200
        assert load_config(path).platform.repo == "org/renamed"
        assert client.get("/api/v1/projects/alpha").json()["repo"] == "org/renamed"
        assert profiles.load("alpha").repo == "org/renamed"


def test_direct_identity_edit_also_requires_paused_pickup(tmp_path):
    """@brief Legacy direct configuration cannot bypass restart coordination."""
    profiles, path, state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        body = {"key": "platform.repo", "value": "org/renamed", "revision": revision}
        assert client.put("/api/v1/projects/alpha/config", json=body,
                          headers=headers).status_code == 409
        state.pause()
        assert client.put("/api/v1/projects/alpha/config", json=body,
                          headers=headers).status_code == 200
        assert load_config(path).platform.repo == "org/renamed"
        assert client.get("/api/v1/projects/alpha").json()["repo"] == "org/renamed"


@pytest.mark.parametrize("field,value", [
    ("schema", True),
    ("candidate_revision", "not-a-digest"),
    ("restart_required", "false"),
    ("created_at", "2026-09-30T12:00:00"),
])
def test_pending_config_rejects_corrupt_persisted_fields(tmp_path, field, value):
    """@brief Restored candidate metadata must retain its typed contract."""
    profiles, path, _state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        staged = client.post("/api/v1/projects/alpha/config/pending", json={
            "key": "budgets.max_iterations", "value": "12", "revision": revision,
        }, headers=headers)
        assert staged.status_code == 200
        pending_path = profiles.profile_dir("alpha") / "pending_config.json"
        record = json.loads(pending_path.read_text(encoding="utf-8"))
        record[field] = value
        pending_path.write_text(json.dumps(record), encoding="utf-8")
        assert client.get("/api/v1/projects/alpha/config/pending").status_code == 503
        assert client.delete("/api/v1/projects/alpha/config/pending",
                             headers=headers).status_code == 200
        assert load_config(path).budgets.max_iterations != 12


def test_pending_config_apply_rejects_missing_live_config(tmp_path):
    """@brief A vanished config is a typed service error, not an HTTP crash."""
    profiles, path, _state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        staged = client.post("/api/v1/projects/alpha/config/pending", json={
            "key": "budgets.max_iterations", "value": "12", "revision": revision,
        }, headers=headers)
        assert staged.status_code == 200
        path.unlink()
        response = client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": staged.json()["candidate_revision"],
        }, headers=headers)
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "config_corrupt"


def test_pending_config_apply_finishes_interrupted_metadata_commit(tmp_path):
    """@brief Retrying an interrupted apply reconciles exact candidate bytes."""
    profiles, path, state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        staged = client.post("/api/v1/projects/alpha/config/pending", json={
            "key": "platform.repo", "value": "org/recovered", "revision": revision,
        }, headers=headers)
        assert staged.status_code == 200
        pending_path = profiles.profile_dir("alpha") / "pending_config.json"
        record = json.loads(pending_path.read_text(encoding="utf-8"))
        path.write_bytes(record["candidate_text"].encode("utf-8"))
        state.pause()
        response = client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": record["candidate_revision"],
        }, headers=headers)
        assert response.status_code == 200, response.text
        assert profiles.load("alpha").repo == "org/recovered"
        assert not pending_path.exists()
