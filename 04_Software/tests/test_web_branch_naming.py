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
@file    test_web_branch_naming.py
@brief   Scoped no-write previews and reviewed branch naming edits.
@details Tests administrator/developer, revision, CSRF and external environment boundaries.
"""

# IMPORTS
from pathlib import Path
import tomllib

from adore.config import load_config
from adore.profiles import ProfileStore
from adore.state import StateStore
from adore.web.app import create_app
import pytest

from tests.configuration_client import TestClient


# HELPER FUNCTIONS
@pytest.fixture
def project(tmp_path):
    """@brief Isolate a paused profile, local source and authenticated administrator."""
    profiles = ProfileStore(tmp_path / "home")
    root = tmp_path / "state"
    profiles.create("alpha", store_root=str(root))
    path = profiles.config_path("alpha")
    text = (Path(__file__).resolve().parents[1] / "config.example.toml").read_text()
    text = text.replace('store_root = ".adore"', f'store_root = "{root.as_posix()}"')
    path.write_bytes(text.replace("\n", "\r\n").encode())
    state = StateStore(root)
    state.pause()
    app = create_app(profiles.home)
    with TestClient(app) as client:
        session = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()
        yield client, profiles, path, state, app, {"X-CSRF-Token": session["csrf"]}


# PUBLIC API
def test_preview_and_each_reviewed_branch_edit_leave_other_values_unchanged(project):
    """@brief Preview has no side effects and both scalar candidates apply exactly."""
    client, profiles, path, state, _app, headers = project
    original = path.read_bytes()
    viewed = client.get("/api/v1/projects/alpha/config").json()
    for key in ("worktree.branch_template", "worktree.branch_rule"):
        meta = next(row for row in viewed["settings"] if row["key"] == key)
        assert meta["editable"] is True and meta["restart"] is True
    preview = client.post("/api/v1/projects/alpha/config/branch-preview", headers=headers,
                          json={"template": "feature/{slug}-{iid}", "rule": r"^feature/.*$",
                                "revision": viewed["revision"]})
    assert preview.status_code == 200, preview.text
    result = preview.json()
    assert result["name"] == f"feature/{viewed['config']['agent']['slug']}-1"
    assert result["valid"] is True and result["rule_matches"] is True
    assert result["revision"] == viewed["revision"]
    assert path.read_bytes() == original
    assert not (profiles.profile_dir("alpha") / "pending_config.json").exists()
    for key, value in [("worktree.branch_template", "feature/{slug}-{iid}"),
                       ("worktree.branch_rule", "^feature/.*$")]:
        active = client.get("/api/v1/projects/alpha/config").json()
        before = path.read_bytes()
        staged = client.post("/api/v1/projects/alpha/config/pending", headers=headers,
                             json={"key": key, "value": value, "revision": active["revision"]})
        assert staged.status_code == 200, staged.text
        assert path.read_bytes() == before
        state.resume()
        target = "/api/v1/projects/alpha/config/apply"
        body = {"candidate_revision": staged.json()["candidate_revision"],
                "base_revision": staged.json()["base_revision"]}
        assert client.post(target, headers=headers, json=body).status_code == 409
        assert path.read_bytes() == before
        state.pause()
        applied = client.post(target, headers=headers, json=body)
        assert applied.status_code == 200, applied.text
        expected = tomllib.loads(before.decode())
        expected["worktree"][key.split(".")[1]] = value
        assert tomllib.loads(path.read_text()) == expected
        assert b"\r\n" in path.read_bytes()
    assert load_config(path).worktree.branch_rule == "^feature/.*$"


@pytest.mark.parametrize(("key", "value"), [
    ("worktree.branch_template", "feature/{missing}-{iid}"),
    ("worktree.branch_template", "feature/{iid:04d}"),
    ("worktree.branch_template", "feature/{iid"),
    ("worktree.branch_template", "feature/{slug}"),
    ("worktree.branch_rule", "["),
    ("worktree.branch_rule", "^bugfix/"),
])
def test_invalid_preview_and_candidate_never_change_source(project, key, value):
    """@brief Malformed or incompatible drafts are explicit failures, including legacy PUT."""
    client, _profiles, path, _state, _app, headers = project
    original = path.read_bytes()
    active = client.get("/api/v1/projects/alpha/config").json()
    values = {"template": active["config"]["worktree"]["branch_template"],
              "rule": active["config"]["worktree"]["branch_rule"], "revision": active["revision"]}
    values["template" if key.endswith("template") else "rule"] = value
    response = client.post("/api/v1/projects/alpha/config/branch-preview",
                           headers=headers, json=values)
    assert response.status_code == 200, response.text
    assert response.json()["valid"] is False and response.json()["issues"]
    for method, target in [(client.post, "config/pending"), (client.put, "config")]:
        rejected = method(f"/api/v1/projects/alpha/{target}", headers=headers,
                          json={"key": key, "value": value, "revision": active["revision"]})
        assert rejected.status_code == 400, rejected.text
        assert path.read_bytes() == original


def test_preview_http_and_external_environment_boundaries(project):
    """@brief Strict request, exact revision and external path/runtime restrictions persist."""
    client, _profiles, path, _state, _app, headers = project
    original = path.read_bytes()
    revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
    target = "/api/v1/projects/alpha/config/branch-preview"
    body = {"template": "feature/{iid}", "rule": "", "revision": revision}
    assert client.post(target, json=body).status_code == 403
    assert client.post(target, headers=headers,
                       json={**body, "revision": "0" * 64}).status_code == 409
    for invalid in [{"template": 1}, {"rule": None}, {"extra": "forbidden"},
                    {"template": "x" * 513}, {"rule": "x" * 513}, {"revision": "bad"}]:
        assert client.post(target, headers=headers, json={**body, **invalid}).status_code == 422
    for key in ("worktree.root", "worktree.repo_path", "container.uv_cache_volume"):
        for method, route in [(client.post, "config/pending"), (client.put, "config")]:
            response = method(f"/api/v1/projects/alpha/{route}", headers=headers,
                              json={"key": key, "value": "anything", "revision": revision})
            assert response.status_code == 400
            assert response.json()["detail"]["code"] == "environment_managed_externally"
    assert path.read_bytes() == original


def test_scoped_developer_can_preview_but_not_edit_or_cross_projects(project):
    """@brief Nonmutating previews follow project grants, while writes remain Admin-only."""
    client, profiles, _path, _state, app, _headers = project
    web = app.state.web_store
    account = web.create_user("dev", "test-password", "developer")
    web.set_memberships(account["id"], ["alpha"])
    profiles.create("other")
    client.delete("/api/v1/session")
    session = client.post("/api/v1/session", json={
        "username": "dev", "password": "test-password"}).json()
    headers = {"X-CSRF-Token": session["csrf"]}
    revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
    body = {"template": "feature/{iid}", "rule": "", "revision": revision}
    target = "/api/v1/projects/{}/config/branch-preview"
    assert client.post(target.format("alpha"), headers=headers, json=body).status_code == 200
    assert client.post(target.format("other"), headers=headers, json=body).status_code == 404
    assert client.post("/api/v1/projects/alpha/config/pending", headers=headers,
                       json={"key": "worktree.branch_template", "value": "feature/{iid}",
                             "revision": revision}).status_code == 403


def test_preview_rejects_source_changed_during_evaluation_and_corrupt_source(project, monkeypatch):
    """@brief A response cannot validate a draft against a changed or unreadable source."""
    client, _profiles, path, _state, _app, headers = project
    active = client.get("/api/v1/projects/alpha/config").json()
    original = path.read_bytes()
    from adore.config import branch_naming_preview

    def evaluate(*args):
        """@brief Simulate an external operator edit during fixed-sample evaluation."""
        path.write_bytes(original + b"\r\n# external edit\r\n")
        return branch_naming_preview(*args)
    monkeypatch.setattr("adore.web.app.branch_naming_preview", evaluate)
    body = {"template": "feature/{iid}", "rule": "", "revision": active["revision"]}
    target = "/api/v1/projects/alpha/config/branch-preview"
    assert client.post(target, headers=headers, json=body).status_code == 409
    path.write_bytes(b"invalid TOML = [")
    from hashlib import sha256

    body["revision"] = sha256(path.read_bytes()).hexdigest()
    failed = client.post(target, headers=headers, json=body)
    assert failed.status_code == 503
    assert failed.json()["detail"]["code"] == "config_corrupt"

# END OF FILE
