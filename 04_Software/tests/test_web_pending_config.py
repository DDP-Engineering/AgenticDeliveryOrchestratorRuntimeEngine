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


def test_legacy_environment_candidate_is_readable_discardable_but_not_applicable(tmp_path):
    """@brief A valid pre-upgrade candidate for a still-external key remains recoverable."""
    from hashlib import sha256

    profiles, path, _state = _project(tmp_path)
    original = path.read_bytes()
    current = load_config(path).container.uv_cache_volume
    candidate = original.decode("utf-8").replace('uv_cache_volume  = "' + current + '"',
                                                'uv_cache_volume  = "legacy-cache"')
    assert candidate.encode() != original
    pending = {"schema": 1, "base_revision": sha256(original).hexdigest(),
               "candidate_revision": sha256(candidate.encode()).hexdigest(),
               "candidate_text": candidate, "key": "container.uv_cache_volume",
               "value": "legacy-cache",
               "created_at": "2026-10-07T20:00:00+00:00", "restart_required": True}
    retained = path.parent / "pending_config.json"
    retained.write_text(json.dumps(pending), encoding="utf-8")
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        viewed = client.get("/api/v1/projects/alpha/config/pending")
        assert viewed.status_code == 200, viewed.text
        response = client.post("/api/v1/projects/alpha/config/apply", headers=headers,
            json={"candidate_revision": pending["candidate_revision"]})
        assert response.status_code == 400, response.text
        assert response.json()["detail"]["code"] == "environment_managed_externally"
        assert path.read_bytes() == original and retained.exists()
        assert client.delete(
            "/api/v1/projects/alpha/config/pending", headers=headers).status_code == 200
        assert not retained.exists() and path.read_bytes() == original


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
    ("value", "mismatched-review-value"),
    ("key", "platform.repo"),
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


def test_pending_review_uses_safe_typed_candidate_values(tmp_path):
    """@brief Review exposes typed proposed data and redacts credential URLs."""
    profiles, path, _state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        staged = client.post("/api/v1/projects/alpha/config/pending", json={
            "key": "budgets.max_iterations", "value": "12", "revision": revision,
        }, headers=headers)
        assert staged.status_code == 200
        assert staged.json()["proposed_value"] == 12
        assert "candidate_text" not in staged.json()
        assert "actor" not in staged.json()
        assert client.delete("/api/v1/projects/alpha/config/pending",
                             headers=headers).status_code == 200
        before = path.read_bytes()
        secret = client.post("/api/v1/projects/alpha/config/pending", json={
            "key": "executor.opencode.model",
            "value": "https://user:password@model.local/v1", "revision": revision,
        }, headers=headers)
        assert secret.status_code == 400
        assert path.read_bytes() == before


def test_settings_metadata_projects_server_domains(tmp_path):
    """@brief Server metadata supplies domains rather than browser guesses."""
    profiles, _path, _state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        _headers(client)
        response = client.get("/api/v1/projects/alpha/config").json()
        rows = {row["key"]: row for row in response["settings"]}
        assert rows["platform.kind"]["choices"] == ["gitlab", "github", "gitea"]
        assert rows["budgets.max_iterations"]["type"] == "integer"
        assert rows["budgets.max_iterations"]["minimum"] == 1
        assert rows["container.egress.proxy_port"]["maximum"] == 65535
        assert rows["delivery.draft"]["choices"] == [True, False]


@pytest.mark.parametrize("value", ["false", "true"])
def test_review_state_is_applied_only_after_review(tmp_path, value):
    """@brief Both review states use the exact reviewed configuration boundary."""
    profiles, path, _state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        original = path.read_bytes()
        staged = client.post("/api/v1/projects/alpha/config/pending", headers=headers,
            json={"key": "delivery.draft", "value": value, "revision": revision})
        assert staged.status_code == 200, staged.text
        assert staged.json()["proposed_value"] is (value == "true")
        assert path.read_bytes() == original
        applied = client.post("/api/v1/projects/alpha/config/apply", headers=headers,
            json={"candidate_revision": staged.json()["candidate_revision"]})
        assert applied.status_code == 200, applied.text
        assert load_config(path).delivery.draft is (value == "true")


@pytest.mark.parametrize("key,value", [
    ("budgets.max_iterations", "true"),
    ("budgets.max_iterations", "1.5"),
    ("budgets.max_iterations", "0"),
    ("budgets.max_cost_usd", "-1"),
    ("platform.kind", "unknown"),
    ("delivery.draft", '"false"'),
    ("delivery.draft", "1"),
])
def test_preparing_invalid_catalog_types_and_bounds_fails_closed(tmp_path, key, value):
    """@brief Scalar inference cannot bypass declared configuration types."""
    profiles, path, _state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        original = path.read_bytes()
        response = client.post("/api/v1/projects/alpha/config/pending", json={
            "key": key, "value": value, "revision": revision,
        }, headers=headers)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "invalid_config"
        assert path.read_bytes() == original
        assert client.get("/api/v1/projects/alpha/config/pending").json() is None


def test_developer_catalog_redacts_financial_setting_and_credential_url(tmp_path):
    """@brief Granted Dev gets safe purpose rows without financial or URL secrets."""
    profiles, path, _state = _project(tmp_path)
    path.write_text(path.read_text(encoding="utf-8").replace(
        'model = "openai/gpt-5.4-fast"',
        'model = "https://user:secret-value@model.local/v1"'), encoding="utf-8")
    assert "secret-value" in path.read_text(encoding="utf-8")
    app = create_app(profiles.home)
    user = app.state.web_store.create_user("dev", "longer-password", "developer")
    app.state.web_store.set_memberships(user["id"], ["alpha"])
    with TestClient(app) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"}).json()["csrf"]
        viewed = client.get("/api/v1/projects/alpha/config")
        assert viewed.status_code == 200
        assert "max_cost_usd" not in viewed.text
        assert "secret-value" not in viewed.text
        assert "OPENCODE_CONFIG_CONTENT" not in viewed.text
        assert client.get("/api/v1/projects/alpha/config/pending").status_code == 403
        for route in ("config/pending", "config/apply"):
            assert client.post(f"/api/v1/projects/alpha/{route}", json={
                "key": "budgets.max_iterations", "value": "12", "revision": "stale",
                "candidate_revision": "a" * 64,
            }, headers={"X-CSRF-Token": csrf}).status_code == 403
        assert client.delete("/api/v1/projects/alpha/config/pending",
                             headers={"X-CSRF-Token": csrf}).status_code == 403


def test_apply_binds_the_reviewed_base_as_well_as_candidate(tmp_path):
    """@brief Explicit reviewed base cannot be replaced by another saved base."""
    profiles, path, _state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        original = path.read_bytes()
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        pending = client.post("/api/v1/projects/alpha/config/pending", json={
            "key": "budgets.max_iterations", "value": "12", "revision": revision,
        }, headers=headers).json()
        applied = client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": pending["candidate_revision"], "base_revision": "0" * 64,
        }, headers=headers)
        assert applied.status_code == 409
        assert applied.json()["detail"]["code"] == "stale_config_revision"
        assert path.read_bytes() == original
        assert client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": pending["candidate_revision"], "base_revision": revision,
        }, headers=headers).status_code == 200


@pytest.mark.parametrize("old,new", [
    ("@ai-sdk/openai-compatible", "@ai-sdk/anthropic"),
    ("{env:OPENAI_API_KEY}", "raw-credential-value"),
    ("/etc/ssl/model-ca.pem", "https://user:ca-secret@model.local/ca"),
    ("/etc/ssl/model-ca.pem", "../invalid-ca.pem"),
])
def test_restored_endpoint_review_rejects_changed_protocol_or_credentials(tmp_path, old, new):
    """@brief Corrupt restored connection metadata fails before review or apply."""
    from hashlib import sha256

    profiles, path, state = _project(tmp_path)
    state.pause()
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        original = path.read_bytes()
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        staged = client.post("/api/v1/projects/alpha/config/pending", json={
            "key": "container.runtime_env.OPENAI_BASE_URL", "value": "https://model.local/v1",
            "model": "local/test", "auth_env": "OPENAI_API_KEY",
            "ca_file": "/etc/ssl/model-ca.pem", "revision": revision,
        }, headers=headers)
        assert staged.status_code == 200
        pending_path = profiles.profile_dir("alpha") / "pending_config.json"
        record = json.loads(pending_path.read_text(encoding="utf-8"))
        assert old in record["candidate_text"]
        record["candidate_text"] = record["candidate_text"].replace(old, new)
        record["candidate_revision"] = sha256(record["candidate_text"].encode()).hexdigest()
        pending_path.write_text(json.dumps(record), encoding="utf-8")
        viewed = client.get("/api/v1/projects/alpha/config/pending")
        assert viewed.status_code == 503
        assert new not in viewed.text
        rejected = client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": record["candidate_revision"], "base_revision": revision,
        }, headers=headers)
        assert rejected.status_code == 503
        assert rejected.json()["detail"]["code"] == "pending_config_corrupt"
        assert path.read_bytes() == original
        assert client.delete("/api/v1/projects/alpha/config/pending",
                             headers=headers).status_code == 200


def test_catalog_fails_closed_on_corrupt_declared_scalar_type(tmp_path):
    """@brief Active scalar type corruption is a typed read error, not a guessed control."""
    profiles, path, _state = _project(tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "max_iterations           = 20" in text
    changed = text.replace("max_iterations           = 20", "max_iterations           = true")
    path.write_text(changed, encoding="utf-8")
    with TestClient(create_app(profiles.home)) as client:
        _headers(client)
        viewed = client.get("/api/v1/projects/alpha/config")
        assert viewed.status_code == 503
        assert viewed.json()["detail"]["code"] == "config_corrupt"


def test_execution_setting_direct_write_requires_review(tmp_path):
    """@brief Preparation belongs to the external operator configuration."""
    profiles, path, _ = _project(tmp_path)
    original = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        response = client.put("/api/v1/projects/alpha/config", headers=headers,
            json={"key": "execution.preparation", "value": "prepare.yml#setup@" + "a" * 40,
                  "revision": revision})
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "environment_managed_externally"
        assert path.read_bytes() == original


@pytest.mark.parametrize("key,value,expected", [
    ("clarification.answer_timeout", "12h", "12h"),
    ("clarification.max_rounds", "5", 5),
    ("recovery.retry_backoff_seconds", "[0,10,45]", [0, 10, 45]),
    ("workflow.stage_timeout_overrides", '{"build":5400,"validate":3600}',
     {"build": 5400, "validate": 3600}),
    ("workflow.stage_timeout_overrides",
     '{"frame":600,"specify":600,"design":600,"build":5400,"validate":3600}',
     {"frame": 600, "specify": 600, "design": 600, "build": 5400, "validate": 3600}),
])
def test_implementation_settings_review_and_apply_exact_value(tmp_path, key, value, expected):
    """@brief New typed controls retain reviewed apply and every unrelated config value."""
    profiles, path, _ = _project(tmp_path)
    before = load_config(path).to_dict()
    original = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        view = client.get('/api/v1/projects/alpha/config').json()
        meta = {row['key']: row for row in view['settings']}
        assert meta[key]['editable'] is True
        result = client.post('/api/v1/projects/alpha/config/pending', headers=headers,
                             json={'key': key, 'value': value, 'revision': view['revision']})
        assert result.status_code == 200, result.text
        assert result.json()['proposed_value'] == expected
        assert path.read_bytes() == original
        assert client.get('/api/v1/projects/alpha/config/pending').json() == result.json()
        applied = client.post('/api/v1/projects/alpha/config/apply', headers=headers,
                              json={'candidate_revision': result.json()['candidate_revision']})
        assert applied.status_code == 200, applied.text
        section, name = key.split('.')
        before[section][name] = expected
        assert load_config(path).to_dict() == before


def test_stored_deliver_timeout_is_not_an_editable_stage_map(tmp_path):
    """
    @brief   A stored map naming deliver is outside the closed five-stage editor.
    @details AEGIS 0.15.0 removed the deliver stage, so the Settings row for a
             persisted deliver override is shown but not offered for editing.
    """
    profiles, path, _ = _project(tmp_path)
    text = path.read_text(encoding='utf-8')
    path.write_text(text.replace('stage_timeout_overrides = {}',
                                 'stage_timeout_overrides = { deliver = 900 }'),
                    encoding='utf-8')
    with TestClient(create_app(profiles.home)) as client:
        _headers(client)
        response = client.get('/api/v1/projects/alpha/config')
        assert response.status_code == 200, response.text
        rows = {row['key']: row for row in response.json()['settings']}
        assert rows['workflow.stage_timeout_overrides']['editable'] is False


@pytest.mark.parametrize('shape', ['inline', 'table', 'quoted', 'missing'])
def test_stage_timeout_map_handles_human_toml_and_removes_override(tmp_path, shape):
    """@brief Complete stage edits handle supported TOML spelling without touching other keys."""
    profiles, path, _ = _project(tmp_path)
    text = path.read_text(encoding='utf-8')
    replacements = {
        'inline': 'stage_timeout_overrides = { build = 5400, validate = 3600 }',
        'quoted': '\"stage_timeout_overrides\" = { build = 5400 }',
        'missing': '',
        'table': '',
    }
    text = text.replace('stage_timeout_overrides = {}', replacements[shape])
    if shape == 'table':
        text += ('\n[workflow.stage_timeout_overrides] # operator limits\n'
                 'build = 5400\nvalidate = 3600\n')
    text = text.replace('retry_backoff_seconds = [5, 30, 120]',
                        'retry_backoff_seconds = [\n 5, # first delay\n 30, 120,\n]')
    path.write_bytes(text.replace('\n', '\r\n').encode())
    before = load_config(path).to_dict()
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        for key, value, expected in [
                ('workflow.stage_timeout_overrides', '{}', {}),
                ('recovery.retry_backoff_seconds', '[0,2]', [0, 2])]:
            view = client.get('/api/v1/projects/alpha/config').json()
            assert sum(row['key'] == 'workflow.stage_timeout_overrides'
                       for row in view['settings']) == 1
            response = client.post('/api/v1/projects/alpha/config/pending', headers=headers,
                                  json={'key': key, 'value': value, 'revision': view['revision']})
            assert response.status_code == 200, response.text
            applied = client.post('/api/v1/projects/alpha/config/apply', headers=headers,
                                  json={'candidate_revision':
                                        response.json()['candidate_revision']})
            assert applied.status_code == 200, applied.text
            section, name = key.split('.')
            before[section][name] = expected
            assert load_config(path).to_dict() == before
            assert b'\r\n' in path.read_bytes()


@pytest.mark.parametrize('key,value', [
    ('clarification.answer_timeout','0s'), ('clarification.max_rounds','0'),
    ('clarification.reminder_after','1h'), ('clarification.timeout_state','stale'),
    ('recovery.retry_backoff_seconds','[9007199254740992]'),
    ('recovery.retry_backoff_seconds','[]'), ('recovery.retry_backoff_seconds','[true]'),
    ('recovery.retry_backoff_seconds','[-1]'), ('recovery.retry_backoff_seconds','[1.5]'),
    ('workflow.stage_timeout_overrides','{"build":0}'),
    ('workflow.stage_timeout_overrides','{"build":true}'),
    ('workflow.stage_timeout_overrides','{"unknown":30}'),
    ('workflow.stage_timeout_overrides','{"deliver":900}'),
    ('workflow.stage_timeout_overrides','{"build":30,"build":60}'),
    ('workflow.stage_timeout_overrides','[30]'),
])
def test_implementation_setting_bad_input_never_writes(tmp_path, key, value):
    """@brief Closed collection/scalar authority rejects malformed human input atomically."""
    profiles, path, _ = _project(tmp_path)
    original = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get('/api/v1/projects/alpha/config').json()['revision']
        response = client.post('/api/v1/projects/alpha/config/pending', headers=headers,
                              json={'key':key,'value':value,'revision':revision})
        assert response.status_code == 400, response.text
        assert path.read_bytes() == original
        assert client.get('/api/v1/projects/alpha/config/pending').json() is None


@pytest.mark.parametrize('key,value,claimed', [
    ('recovery.retry_backoff_seconds','[5,30]','[true]'),
    ('workflow.stage_timeout_overrides','{"build":300}','{"design":300}'),
])
def test_implementation_collection_corrupt_pending_is_refused(tmp_path,key,value,claimed):
    """@brief Corrupt persisted typed evidence cannot be read or applied as a reviewed value."""
    profiles,path,_ = _project(tmp_path)
    original = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get('/api/v1/projects/alpha/config').json()['revision']
        response = client.post('/api/v1/projects/alpha/config/pending', headers=headers,
                              json={'key':key,'value':value,'revision':revision})
        assert response.status_code == 200, response.text
        pending = path.parent/'pending_config.json'
        record = json.loads(pending.read_text(encoding='utf-8'))
        record['value'] = claimed
        pending.write_text(json.dumps(record),encoding='utf-8')
        assert client.get('/api/v1/projects/alpha/config/pending').status_code == 503
        assert client.post('/api/v1/projects/alpha/config/apply',headers=headers,
            json={'candidate_revision':response.json()['candidate_revision']}).status_code == 503
        assert path.read_bytes() == original


@pytest.mark.parametrize("key,value", [
    ("recovery.retry_backoff_seconds", "[5,30]"),
    ("workflow.stage_timeout_overrides", '{"build":300}'),
])
def test_implementation_collections_keep_role_csrf_revision_and_integrity_gates(
        tmp_path, key, value):
    """@brief Collection candidates reject unauthorized edits and unrelated persisted changes."""
    from hashlib import sha256

    profiles, path, _ = _project(tmp_path)
    original = path.read_bytes()
    app = create_app(profiles.home)
    developer = app.state.web_store.create_user("dev", "longer-password", "developer")
    app.state.web_store.set_memberships(developer["id"], ["alpha"])
    with TestClient(app) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        body = {"key": key, "value": value, "revision": revision}
        assert client.post("/api/v1/projects/alpha/config/pending", json=body).status_code == 403
        assert client.post("/api/v1/projects/alpha/config/pending", headers=headers,
                           json={**body, "revision": "stale"}).status_code == 409
        response = client.post("/api/v1/projects/alpha/config/pending", headers=headers, json=body)
        assert response.status_code == 200, response.text
        pending = path.parent / "pending_config.json"
        record = json.loads(pending.read_text(encoding="utf-8"))
        record["candidate_text"] = record["candidate_text"].replace(
            "max_iterations           = 20", "max_iterations           = 21")
        record["candidate_revision"] = sha256(record["candidate_text"].encode()).hexdigest()
        pending.write_text(json.dumps(record), encoding="utf-8")
        assert client.get("/api/v1/projects/alpha/config/pending").status_code == 503
        refused = client.post("/api/v1/projects/alpha/config/apply", headers=headers,
                              json={"candidate_revision": record["candidate_revision"]})
        assert refused.status_code == 503
        client.post("/api/v1/session/logout", headers=headers)
        csrf = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"}).json()["csrf"]
        assert client.post("/api/v1/projects/alpha/config/pending", json=body,
                           headers={"X-CSRF-Token": csrf}).status_code == 403
        assert client.post("/api/v1/projects/alpha/config/apply",
                           json={"candidate_revision": record["candidate_revision"]},
                           headers={"X-CSRF-Token": csrf}).status_code == 403
        assert path.read_bytes() == original


def test_implementation_collection_unsupported_human_spelling_fails_without_write(tmp_path):
    """@brief A valid but unsupported dotted TOML value cannot alter adjacent settings."""
    profiles, path, _ = _project(tmp_path)
    text = path.read_text(encoding="utf-8").replace(
        "stage_timeout_overrides = {}", "stage_timeout_overrides.build = 300")
    path.write_text(text, encoding="utf-8")
    assert load_config(path).workflow.stage_timeout_overrides == {"build": 300}
    original = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        response = client.post("/api/v1/projects/alpha/config/pending", headers=headers,
            json={"key": "workflow.stage_timeout_overrides", "value": "{}", "revision": revision})
        assert response.status_code == 400, response.text
        assert client.get("/api/v1/projects/alpha/config/pending").json() is None
        assert path.read_bytes() == original
