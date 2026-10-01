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
@file test_web_import.py
@brief Existing configuration import through the web trust boundary.
@details Preview and save preserve source bytes and start with pickup paused.
"""

from pathlib import Path

from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from adore.web.store import WebStore
from fastapi.testclient import TestClient


def _document(tmp_path):
    """@brief Adapt the sample config to unambiguous absolute local paths."""
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    text = example.read_text(encoding="utf-8")
    paths = {
        'store_root = ".adore"': f'store_root = "{(tmp_path / "state").as_posix()}"',
        'repo_path = "../project"': f'repo_path = "{(tmp_path / "repo").as_posix()}"',
        'root = "worktrees"': f'root = "{(tmp_path / "trees").as_posix()}"',
        'db_path = ".adore/metrics.db"':
            f'db_path = "{(tmp_path / "state" / "metrics.db").as_posix()}"',
        'export_jsonl = ".adore/metrics/runs.jsonl"':
            f'export_jsonl = "{(tmp_path / "state" / "metrics" / "runs.jsonl").as_posix()}"',
        'html_out = ".adore/metrics/stats.html"':
            f'html_out = "{(tmp_path / "state" / "metrics" / "stats.html").as_posix()}"',
    }
    for old, new in paths.items():
        assert old in text
        text = text.replace(old, new)
    return text


def _csrf(client):
    """@brief Authenticate the bootstrap administrator."""
    return client.post("/api/v1/session", json={
        "username": "admin", "password": "admin"}).json()["csrf"]


def test_admin_previews_then_imports_exact_config_paused(tmp_path):
    """@brief Import copies validated TOML and retains external state path."""
    profiles = ProfileStore(tmp_path / "home")
    document = _document(tmp_path)
    existing_state = StateStore(tmp_path / "state")
    existing_state.save(RunState(run_id="old-run", ticket_iid=42, lifecycle="done"))
    body = {"name": "alpha", "description": "Imported", "config_text": document}
    with TestClient(create_app(profiles.home)) as client:
        csrf = _csrf(client)
        headers = {"X-CSRF-Token": csrf}
        preview = client.post("/api/v1/projects/import-preview", json=body, headers=headers)
        assert preview.status_code == 200, preview.text
        assert preview.json()["issues"] == []
        assert preview.json()["repo"] == "group/subgroup/project"
        assert not profiles.exists("alpha")
        response = client.post("/api/v1/projects/import", json={
            **body, "revision": preview.json()["revision"]}, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["paused"] is True
        assert profiles.config_path("alpha").read_text(encoding="utf-8") == document
        assert Path(profiles.load("alpha").store_root) == tmp_path / "state"
        assert StateStore(tmp_path / "state").is_paused()
        assert client.get("/api/v1/projects/alpha/runs").json()[0]["run_id"] == "old-run"
        assert client.get("/api/v1/projects/alpha/config").status_code == 200


def test_import_rejects_invalid_secret_relative_and_stale_input(tmp_path):
    """@brief Unreviewed or ambiguous input cannot create a profile."""
    profiles = ProfileStore(tmp_path / "home")
    document = _document(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        csrf = _csrf(client)
        headers = {"X-CSRF-Token": csrf}
        body = {"name": "alpha", "config_text": document}
        preview = client.post("/api/v1/projects/import-preview", json=body,
                              headers=headers).json()
        assert client.post("/api/v1/projects/import", json={
            **body, "revision": "bad-hash"}, headers=headers).status_code == 409
        for bad in (document + "\n[bad\n", document.replace(
            'store_root = "', 'store_root = "relative/'), document +
            '\n[unsafe]\napi_key = "not-a-real-secret"\n'):
            response = client.post("/api/v1/projects/import-preview", json={
                **body, "config_text": bad}, headers=headers)
            assert response.status_code == 200, response.text
            assert response.json()["issues"]
            assert client.post("/api/v1/projects/import", json={
                **body, "config_text": bad,
                "revision": response.json()["revision"]}, headers=headers).status_code == 400
        assert preview["issues"] == []
        assert not profiles.exists("alpha")


def test_import_requires_admin_csrf_and_unique_state_root(tmp_path):
    """@brief Developers and duplicate state owners cannot import."""
    profiles = ProfileStore(tmp_path / "home")
    document = _document(tmp_path)
    web = WebStore(profiles.home / "web.db")
    web.create_user("dev", "longer-password", "developer")
    body = {"name": "alpha", "config_text": document}
    with TestClient(create_app(profiles.home)) as client:
        csrf = _csrf(client)
        assert client.post("/api/v1/projects/import-preview", json=body).status_code == 403
        headers = {"X-CSRF-Token": csrf}
        preview = client.post("/api/v1/projects/import-preview", json=body,
                              headers=headers).json()
        assert client.post("/api/v1/projects/import", json={
            **body, "revision": preview["revision"]}).status_code == 403
        assert client.post("/api/v1/projects/import", json={
            **body, "revision": preview["revision"]}, headers=headers).status_code == 200
        other = {**body, "name": "beta"}
        conflict = client.post("/api/v1/projects/import-preview", json=other,
                               headers=headers)
        assert conflict.status_code == 200
        assert conflict.json()["issues"]
        client.delete("/api/v1/session", headers=headers)
        dev_csrf = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"}).json()["csrf"]
        assert client.post("/api/v1/projects/import-preview", json=other,
                           headers={"X-CSRF-Token": dev_csrf}).status_code == 403


def test_import_rejects_active_state_and_conductor_lock(tmp_path):
    """@brief Existing active work must finish before ownership is imported."""
    profiles = ProfileStore(tmp_path / "home")
    document = _document(tmp_path)
    state = StateStore(tmp_path / "state")
    body = {"name": "alpha", "config_text": document}
    with TestClient(create_app(profiles.home)) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        revision = client.post("/api/v1/projects/import-preview", json=body,
                               headers=headers).json()["revision"]
        state.save(RunState(run_id="running", ticket_iid=42, lifecycle="working"))
        assert client.post("/api/v1/projects/import", json={
            **body, "revision": revision}, headers=headers).status_code == 409
        assert not profiles.exists("alpha")
        state.save(RunState(run_id="running", ticket_iid=42, lifecycle="done"))
        assert state.acquire_lock()
        try:
            assert client.post("/api/v1/projects/import", json={
                **body, "revision": revision}, headers=headers).status_code == 409
        finally:
            state.release_lock()
        assert not profiles.exists("alpha")
