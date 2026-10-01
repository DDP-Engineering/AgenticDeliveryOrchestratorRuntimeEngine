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
@file test_web_projects.py
@brief Project directory search and status contract tests.
@details Authorized project cards expose configuration state and last activity.
"""

import json
from pathlib import Path

from adore.config import load_config
from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.util import CommandResult
from adore.web.app import create_app
from adore.wizard import run_wizard
from fastapi.testclient import TestClient


def test_project_directory_filters_with_grants_and_status(tmp_path):
    """@brief Search and state filters operate only on authorized projects."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = profiles.create("alpha", description="Core service", repo="org/alpha",
                            store_root=str(tmp_path / "alpha-state"))
    beta = profiles.create("beta", description="Worker", repo="org/beta",
                           store_root=str(tmp_path / "beta-state"))
    gamma = profiles.create("gamma", description="Retired", repo="org/gamma",
                            store_root=str(tmp_path / "gamma-state"))
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    profiles.config_path("alpha").write_bytes(example.read_bytes())
    state = StateStore(alpha.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="done"))
    path = state.run_dir("run-1") / "state.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["updated_at"] = "2026-09-30T12:30:00+02:00"
    path.write_text(json.dumps(data), encoding="utf-8")
    StateStore(beta.store_root).pause()
    gamma.archived = True
    profiles.save(gamma)
    app = create_app(profiles.home)
    web = app.state.web_store
    developer = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(developer["id"], ["alpha", "beta"])
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        rows = client.get("/api/v1/projects").json()
        assert {row["name"]: row["readiness"] for row in rows} == {
            "alpha": "configured", "beta": "paused", "gamma": "archived"}
        assert rows[0]["executor"] == "opencode"
        assert rows[0]["last_activity"] == "2026-09-30T10:30:00+00:00"
        assert [row["name"] for row in client.get(
            "/api/v1/projects?q=ORG/BETA&state=paused").json()] == ["beta"]
        assert [row["name"] for row in client.get(
            "/api/v1/projects?state=archived").json()] == ["gamma"]
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        assert client.get("/api/v1/projects?state=archived").json() == []
        assert [row["name"] for row in client.get(
            "/api/v1/projects?q=core").json()] == ["alpha"]
        assert client.get("/api/v1/projects/gamma").status_code == 404


def test_project_directory_rejects_bad_filters_and_corrupt_activity(tmp_path):
    """@brief Bad queries and malformed persisted times fail with typed errors."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="done"))
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        for query in ("q=%20%20", "q=" + "x" * 81, "state=unknown"):
            assert client.get(f"/api/v1/projects?{query}").status_code == 422
        path = state.run_dir("run-1") / "state.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["updated_at"] = "not-a-date"
        path.write_text(json.dumps(data), encoding="utf-8")
        assert client.get("/api/v1/projects").status_code == 503
        assert client.get("/api/v1/projects/alpha").status_code == 503


def test_web_project_has_stable_absolute_worktree_root(tmp_path, monkeypatch):
    """@brief Web jobs use one worktree path regardless of worker cwd."""
    import adore.web.app as web_app

    def offline_wizard(*args, **kwargs):
        return run_wizard(*args, **kwargs, runner=lambda _argv, **_options:
                          CommandResult(exit_code=127))

    monkeypatch.setattr(web_app, "run_wizard", offline_wizard)
    home = tmp_path / "home"
    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True)
    with TestClient(create_app(home)) as client:
        session = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()
        body = {
            "name": "alpha", "kind": "gitlab", "repo": "group/alpha",
            "repo_path": str(clone), "reviewers": "reviewer",
            "executor_cli": "opencode", "model": "openai/gpt-5.5",
            "auth_mode": "api-key", "image": "adore-test:latest",
        }
        headers = {"X-CSRF-Token": session["csrf"]}
        response = client.post("/api/v1/projects", json=body, headers=headers)
        assert response.status_code == 200, response.text
        config = load_config(home / "profiles" / "alpha" / "config.toml")
        assert config.worktree.root == str((home / "worktrees" / "alpha").resolve())
        assert Path(config.worktree.root).is_absolute()
        assert client.post("/api/v1/projects", json={
            **body, "name": "../escape"}, headers=headers).status_code == 400
