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
@file    test_web_settings_batch.py
@brief   Public multi-setting candidate and atomic Save contracts.
@details External requests and persisted candidate evidence are untrusted.
         No real forge, executor, container or setup command is run.
"""

# IMPORTS
from hashlib import sha256
import json
import re
import tomllib

from adore.config import load_config
from adore.web.app import create_app
from adore.web.store import WebStore
from fastapi.testclient import TestClient
import pytest

from tests.test_web_pending_config import _headers, _project

# CONSTANTS
PENDING = "/api/v1/projects/alpha/config/pending"
APPLY = "/api/v1/projects/alpha/config/apply"
CONFIG = "/api/v1/projects/alpha/config"
BATCH = "settings.batch"


# HELPER FUNCTIONS
@pytest.fixture
def project(tmp_path):
    """@brief Lend one idle project and authenticated administrator client."""
    profiles, path, state = _project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        yield profiles, path, state, client, headers


def stage(project, edits, **binding):
    """@brief Prepare a batch through the public route with its inspected base."""
    _, _, _, client, headers = project
    revision = client.get(CONFIG).json()["revision"]
    return client.post(PENDING, headers=headers, json={
        "key": BATCH, "value": json.dumps(edits), "revision": revision, **binding,
    })


def apply(project, candidate):
    """@brief Apply only the exact candidate/base pair returned by preparation."""
    _, _, _, client, headers = project
    return client.post(APPLY, headers=headers, json={
        key: candidate[key] for key in ("base_revision", "candidate_revision")
    })


# PUBLIC API
def test_batch_prepares_and_applies_all_values_together(project):
    """@brief A single bound candidate changes several settings atomically."""
    _, path, _, client, _ = project
    original = path.read_bytes()
    response = stage(project, [
        {"key": "budgets.max_iterations", "value": "12"},
        {"key": "polling.poll_interval_seconds", "value": "75"},
    ])
    assert response.status_code == 200, response.text
    candidate = response.json()
    assert candidate["proposed_value"] == {
        "budgets.max_iterations": 12, "polling.poll_interval_seconds": 75,
    }
    assert candidate["value"] == json.dumps(candidate["proposed_value"], separators=(",", ":"))
    assert not candidate["restart_required"]
    assert path.read_bytes() == original
    assert client.get(PENDING).json() == candidate
    result = apply(project, candidate)
    assert result.status_code == 200, result.text
    config = load_config(path)
    assert config.budgets.max_iterations == 12
    assert config.polling.poll_interval_seconds == 75
    assert client.get(PENDING).json() is None


def test_batch_validates_the_combined_configuration(project):
    """@brief Interdependent timeout/provider edits need no invalid intermediate write."""
    _, path, state, _, _ = project
    state.pause()
    response = stage(project, [
        {"key": "executor.connection", "value": json.dumps({
            "provider": "chatgpt", "model": "gpt-5.6-luna", "base_url": "", "api": "",
        })},
        {"key": "budgets.per_gate_timeout_seconds", "value": "300"},
    ])
    assert response.status_code == 200, response.text
    result = apply(project, response.json())
    assert result.status_code == 200, result.text
    config = load_config(path)
    assert config.executor.provider == "chatgpt"
    assert config.budgets.per_gate_timeout_seconds == 300


@pytest.mark.parametrize("edits", [
    [],
    {},
    [{"key": "budgets.max_iterations", "value": 12}],
    [{"key": "budgets.max_iterations", "value": "12", "extra": True}],
    [{"key": "budgets.max_iterations"}],
    [{"key": "budgets.max_iterations", "value": "12"}] * 2,
    [{"key": "settings.batch", "value": "[]"}],
    [{"key": "worktree.repo_path", "value": "/changed"}],
    [{"key": "executor.endpoint.api_key", "value": "unsafe"}],
    [{"key": "unknown.setting", "value": "12"}],
    [{"key": "polling.poll_interval_seconds", "value": "0"}],
    [{"key": "budgets.max_iterations", "value": "12"},
     {"key": "polling.poll_interval_seconds", "value": "0"}],
    [{"key": "workflow.stage_timeout_overrides", "value": "{}"},
     {"key": "workflow.stage_timeout_overrides.build", "value": "12"}],
    [{"key": "executor.connection", "value": "{}"},
     {"key": "executor.model", "value": "another-model"}],
    [{"key": f"unknown.{index}", "value": "1"} for index in range(101)],
])
def test_invalid_batch_preserves_active_and_previous_candidate(project, edits):
    """@brief One bad member never publishes a partial batch or replaces evidence."""
    _, path, _, client, headers = project
    raw = path.read_bytes()
    revision = client.get(CONFIG).json()["revision"]
    initial = client.post(PENDING, headers=headers, json={
        "key": "budgets.max_iterations", "value": "11", "revision": revision,
    })
    assert initial.status_code == 200
    retained = path.parent / "pending_config.json"
    previous = retained.read_bytes()
    result = stage(project, edits, pending_revision=initial.json()["candidate_revision"])
    assert result.status_code == 400, result.text
    assert path.read_bytes() == raw and retained.read_bytes() == previous


def test_replacing_candidate_requires_exact_pending_binding(project):
    """@brief Bound replacement supports correction without unreviewed overwrite."""
    _, path, _, client, _ = project
    edits = [{"key": "budgets.max_iterations", "value": "12"}]
    initial = stage(project, edits)
    assert initial.status_code == 200, initial.text
    previous = (path.parent / "pending_config.json").read_bytes()
    assert stage(project, edits).status_code == 409
    assert stage(project, edits, pending_revision="0" * 64).status_code == 409
    assert (path.parent / "pending_config.json").read_bytes() == previous
    replacement = stage(project, [
        {"key": "budgets.max_iterations", "value": "13"},
        {"key": "polling.poll_interval_seconds", "value": "90"},
    ], pending_revision=initial.json()["candidate_revision"])
    assert replacement.status_code == 200, replacement.text
    assert replacement.json()["proposed_value"]["budgets.max_iterations"] == 13
    assert client.get(PENDING).json() == replacement.json()


def test_absent_or_stale_base_does_not_accept_replacement(project):
    """@brief A pending hash cannot authorize another active revision."""
    _, path, _, _, _ = project
    edits = [{"key": "budgets.max_iterations", "value": "12"}]
    assert stage(project, edits, pending_revision="0" * 64).status_code == 409
    initial = stage(project, edits)
    assert initial.status_code == 200, initial.text
    previous = (path.parent / "pending_config.json").read_bytes()
    path.write_bytes(path.read_bytes() + b"\n# external edit\n")
    result = stage(project, edits, pending_revision=initial.json()["candidate_revision"])
    assert result.status_code == 409
    assert (path.parent / "pending_config.json").read_bytes() == previous


def test_batch_runtime_permission_retains_pause_guard(project):
    """@brief Any runtime member requires paused monitoring before atomic apply."""
    _, path, state, _, _ = project
    original = path.read_bytes()
    response = stage(project, [
        {"key": "container.system_packages", "value": "true"},
        {"key": "polling.poll_interval_seconds", "value": "75"},
    ])
    assert response.status_code == 200, response.text
    assert response.json()["restart_required"]
    assert apply(project, response.json()).status_code == 409
    assert path.read_bytes() == original
    state.pause()
    assert apply(project, response.json()).status_code == 200


def test_batch_candidate_rejects_collateral_persisted_changes(project):
    """@brief A recomputed hash cannot hide an unrelated change in saved evidence."""
    _, path, _, client, _ = project
    original = path.read_bytes()
    response = stage(project, [{"key": "polling.poll_interval_seconds", "value": "75"}])
    assert response.status_code == 200, response.text
    retained = path.parent / "pending_config.json"
    value = json.loads(retained.read_text(encoding="utf-8"))
    value["candidate_text"], changed = re.subn(
        r"(?m)^(max_iterations\s*=\s*)\d+",
        r"\g<1>999", value["candidate_text"],
    )
    assert changed == 1 and tomllib.loads(value["candidate_text"])
    value["candidate_revision"] = sha256(value["candidate_text"].encode()).hexdigest()
    retained.write_text(json.dumps(value), encoding="utf-8")
    assert client.get(PENDING).status_code == 503
    assert apply(project, value).status_code == 503
    corrupt = retained.read_bytes()
    replacement = stage(project, [{"key": "polling.poll_interval_seconds", "value": "80"}],
                        pending_revision=value["candidate_revision"])
    assert replacement.status_code == 503
    assert replacement.json()["detail"]["code"] == "pending_config_corrupt"
    assert retained.read_bytes() == corrupt
    assert path.read_bytes() == original


def test_batch_preserves_admin_and_csrf_boundaries(project):
    """@brief The batch vocabulary grants no additional mutation access."""
    profiles, _, _, client, _ = project
    body = {"key": BATCH, "value": json.dumps([
        {"key": "polling.poll_interval_seconds", "value": "75"},
    ]), "revision": client.get(CONFIG).json()["revision"]}
    assert client.post(PENDING, json=body).status_code == 403
    WebStore(profiles.home / "web.db").create_user("batchdev", "test-password", "developer")
    session = client.post("/api/v1/session", json={
        "username": "batchdev", "password": "test-password",
    }).json()
    assert client.post(PENDING, json=body, headers={
        "X-CSRF-Token": session["csrf"],
    }).status_code == 403


def test_direct_batch_write_requires_candidate_review(project):
    """@brief A batch cannot bypass the exact candidate publication boundary."""
    _, path, _, client, headers = project
    original = path.read_bytes()
    response = client.put(CONFIG, headers=headers, json={
        "key": BATCH, "value": json.dumps([
            {"key": "polling.poll_interval_seconds", "value": "75"},
        ]), "revision": client.get(CONFIG).json()["revision"],
    })
    assert response.status_code == 409
    assert path.read_bytes() == original


def test_batch_collection_and_connection_values_remain_safe(project):
    """@brief Approved key names and structured connection values are not secrets."""
    _, _, state, _, _ = project
    state.pause()
    result = stage(project, [
        {"key": "executor.env_keys", "value": '["OPENAI_API_KEY"]'},
        {"key": "executor.connection", "value": json.dumps({
            "provider": "openai", "model": "gpt-5.5", "base_url": "", "api": "",
        })},
        {"key": "delivery.reviewers", "value": '["reviewer"]'},
    ])
    assert result.status_code == 200, result.text
    assert apply(project, result.json()).status_code == 200


def test_preview_validates_without_creating_or_replacing_pending(project):
    """@brief A notification preview is not a persisted configuration edit."""
    _, path, _, client, headers = project
    original = path.read_bytes()
    body = {"key": BATCH, "value": json.dumps([
        {"key": "budgets.max_iterations", "value": "12"},
    ]), "revision": client.get(CONFIG).json()["revision"]}
    preview = client.post(CONFIG + "/preview", headers=headers, json=body)
    assert preview.status_code == 200, preview.text
    assert preview.json()["proposed_value"] == {"budgets.max_iterations": 12}
    retained = path.parent / "pending_config.json"
    assert not retained.exists() and path.read_bytes() == original
    initial = stage(project, [{"key": "budgets.max_iterations", "value": "13"}])
    assert initial.status_code == 200
    previous = retained.read_bytes()
    assert client.post(CONFIG + "/preview", headers=headers, json=body).status_code == 200
    assert retained.read_bytes() == previous and path.read_bytes() == original
    body["value"] = "[]"
    assert client.post(CONFIG + "/preview", headers=headers, json=body).status_code == 400
    assert retained.read_bytes() == previous and path.read_bytes() == original


def test_preview_requires_admin_csrf_and_current_revision(project):
    """@brief The no-write preview keeps the same trust and stale-source checks."""
    profiles, _, _, client, headers = project
    body = {"key": BATCH, "value": json.dumps([
        {"key": "budgets.max_iterations", "value": "12"},
    ]), "revision": "0" * 64}
    assert client.post(CONFIG + "/preview", headers=headers, json=body).status_code == 409
    body["revision"] = client.get(CONFIG).json()["revision"]
    assert client.post(CONFIG + "/preview", json=body).status_code == 403
    WebStore(profiles.home / "web.db").create_user("previewdev", "test-password", "developer")
    user = client.post("/api/v1/session", json={
        "username": "previewdev", "password": "test-password",
    }).json()
    assert client.post(CONFIG + "/preview", headers={
        "X-CSRF-Token": user["csrf"],
    }, json=body).status_code == 403



def test_bound_replacement_refuses_corrupt_active_bytes(project):
    """@brief Invalid UTF-8 at the active boundary preserves both evidence files."""
    _, path, _, client, headers = project
    prepared = stage(project, [{"key": "polling.poll_interval_seconds", "value": "75"}])
    assert prepared.status_code == 200
    candidate = prepared.json()
    retained = path.parent / "pending_config.json"
    previous = retained.read_bytes()
    path.write_bytes(b"\xff")
    response = client.post(PENDING, headers=headers, json={
        "key": BATCH, "value": json.dumps([
            {"key": "polling.poll_interval_seconds", "value": "80"},
        ]), "revision": candidate["base_revision"],
        "pending_revision": candidate["candidate_revision"],
    })
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "config_corrupt"
    assert path.read_bytes() == b"\xff"
    assert retained.read_bytes() == previous


# END OF FILE
