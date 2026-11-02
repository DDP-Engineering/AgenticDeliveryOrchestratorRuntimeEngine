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
@file       test_web_executor_configuration.py
@brief      Reviewed executor selection and provider-name API contracts.
@details    Offline fixtures prove exact mutation scope and external input refusal.
"""

# IMPORTS
from copy import deepcopy
from hashlib import sha256
import json
import tomllib

from adore.config import load_config
from adore.state import StateStore
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest

from tests.test_model_connection import project


# PUBLIC API
def test_model_is_a_reviewed_setting_and_no_agent_choice_exists(tmp_path):
    """@brief Pi is the only agent: the model is one reviewed edit and no agent row exists."""
    profiles = project(tmp_path)
    StateStore(tmp_path / "state").pause()
    path = profiles.config_path("alpha")
    original = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        view = client.get("/api/v1/projects/alpha/config").json()
        metadata = {row["key"]: row for row in view["settings"]}
        removed = ("executor.default", "executor.commands", "executor.selection",
                   "executor.stage_host_auth", "labels.executor")
        assert not any(key.startswith(removed) for key in metadata)
        assert metadata["executor.model"]["editable"] is True
        assert metadata["executor.command"]["choices"] == [
            "pi -p --mode json --model {model} {prompt}"]
        payload = {"key": "executor.model", "value": "openai/offline-model",
                   "revision": view["revision"]}
        response = client.post("/api/v1/projects/alpha/config/pending",
                               json=payload, headers=headers)
        assert response.status_code == 200, response.text
        pending = response.json()
        assert pending["proposed_value"] == "openai/offline-model"
        assert pending["restart_required"] is True
        assert path.read_bytes() == original
        response = client.post("/api/v1/projects/alpha/config/apply", headers=headers,
                               json={"candidate_revision": pending["candidate_revision"],
                                     "base_revision": pending["base_revision"]})
        assert response.status_code == 200, response.text
    expected = deepcopy(tomllib.loads(original.decode()))
    expected["executor"]["model"] = "openai/offline-model"
    assert tomllib.loads(path.read_text(encoding="utf-8")) == expected
    assert load_config(path).executor.model == "openai/offline-model"


@pytest.mark.parametrize("variables", [["OPENROUTER_API_KEY"], [],
                                       ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]])
def test_provider_names_are_reviewed_without_changing_private_values(tmp_path, variables):
    """@brief Known names and subscription-only empty lists preserve private dotenv bytes."""
    profiles = project(tmp_path)
    StateStore(tmp_path / "state").pause()
    path = profiles.config_path("alpha")
    env = profiles.profile_dir("alpha") / ".env"
    env.write_text("OPENAI_API_KEY=offline-private-key\n")
    private = env.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        view = client.get("/api/v1/projects/alpha/config").json()
        response = client.post("/api/v1/projects/alpha/config/pending", headers=headers,
                               json={"key": "executor.env_keys", "value": json.dumps(variables),
                                     "revision": view["revision"]})
        assert response.status_code == 200, response.text
        pending = response.json()
        assert pending["proposed_value"] == variables
        assert "offline-private-key" not in response.text
        response = client.post("/api/v1/projects/alpha/config/apply", headers=headers,
                               json={"candidate_revision": pending["candidate_revision"],
                                     "base_revision": pending["base_revision"]})
        assert response.status_code == 200, response.text
    assert load_config(path).executor.env_keys == variables
    assert env.read_bytes() == private


@pytest.mark.parametrize("key,value", [
    ("executor.selection", {"agent": "pi", "command": "pi {prompt}", "model": "model"}),
    ("executor.default", "codex"),
    ("executor.command", "echo unsafe {prompt}"),
    ("executor.model", ""),
    ("executor.model", "model with spaces"),
    ("executor.env_keys", ["GITHUB_TOKEN"]),
    ("executor.env_keys", ["OPENAI_API_KEY", "OPENAI_API_KEY"]),
    ("executor.env_keys", ["NEW_UNKNOWN_KEY"]),
    ("executor.env_keys", ["OPENAI_API_KEY=value"]),
    ("executor.env_keys", [True]),
    ("executor.env_keys", {"OPENAI_API_KEY": "private"}),
])
def test_executor_candidate_boundary_preserves_live_files(tmp_path, key, value):
    """@brief Agent choices, malformed values and unsafe credential names fail unstaged."""
    profiles = project(tmp_path)
    path = profiles.config_path("alpha")
    original = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.post("/api/v1/projects/alpha/config/pending",
                               headers={"X-CSRF-Token": login.json()["csrf"]},
                               json={"key": key, "value": value if isinstance(value, str)
                                     else json.dumps(value),
                                     "revision": sha256(original).hexdigest()})
        assert response.status_code == 400, response.text
        assert client.get("/api/v1/projects/alpha/config/pending").json() is None
    assert path.read_bytes() == original


@pytest.mark.parametrize("mode", ["stale", "unpaused", "developer", "tampered"])
def test_executor_edit_rejects_authority_and_persisted_scope_changes(tmp_path, mode):
    """@brief An executor edit follows revision, idle, role and complete persisted scope checks."""
    profiles = project(tmp_path)
    StateStore(tmp_path / "state").pause()
    path = profiles.config_path("alpha")
    original = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        view = client.get("/api/v1/projects/alpha/config").json()
        payload = {"key": "executor.env_keys", "value": '["OPENAI_API_KEY"]',
                   "revision": "0" * 64 if mode == "stale" else view["revision"]}
        if mode == "developer":
            web = client.app.state.web_store
            user = web.create_user("dev", "longer-password", "developer")
            web.set_memberships(user["id"], ["alpha"])
            login = client.post("/api/v1/session",
                                json={"username": "dev", "password": "longer-password"})
            headers = {"X-CSRF-Token": login.json()["csrf"]}
        response = client.post("/api/v1/projects/alpha/config/pending",
                               headers=headers, json=payload)
        if mode in {"stale", "developer"}:
            assert response.status_code == (409 if mode == "stale" else 403)
        else:
            assert response.status_code == 200, response.text
            pending = response.json()
            if mode == "unpaused":
                StateStore(tmp_path / "state").resume()
            else:
                stored_path = profiles.profile_dir("alpha") / "pending_config.json"
                stored = json.loads(stored_path.read_text(encoding="utf-8"))
                stored["candidate_text"] += '\n[unexpected]\nfield = "unreviewed"\n'
                stored["candidate_revision"] = sha256(stored["candidate_text"].encode()).hexdigest()
                stored_path.write_text(json.dumps(stored), encoding="utf-8")
                pending["candidate_revision"] = stored["candidate_revision"]
                assert client.get("/api/v1/projects/alpha/config/pending").status_code == 503
            response = client.post("/api/v1/projects/alpha/config/apply", headers=headers,
                                   json={"candidate_revision": pending["candidate_revision"],
                                         "base_revision": pending["base_revision"]})
            assert response.status_code == (409 if mode == "unpaused" else 503), response.text
    assert path.read_bytes() == original


def test_existing_custom_provider_names_can_be_retained_or_removed(tmp_path):
    """@brief Operator-owned custom names survive reviewed edits without adding new names."""
    profiles = project(tmp_path)
    path = profiles.config_path("alpha")
    original = path.read_text(encoding="utf-8").replace(
        'env_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]',
        'env_keys = ["CUSTOM_PROVIDER_KEY"]')
    assert "CUSTOM_PROVIDER_KEY" in original
    path.write_text(original, encoding="utf-8")
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        view = client.get("/api/v1/projects/alpha/config").json()
        response = client.post("/api/v1/projects/alpha/config/pending",
                               headers={"X-CSRF-Token": login.json()["csrf"]},
                               json={"key": "executor.env_keys",
                                     "value": '["CUSTOM_PROVIDER_KEY", "OPENAI_API_KEY"]',
                                     "revision": view["revision"]})
        assert response.status_code == 200, response.text
        assert response.json()["proposed_value"] == ["CUSTOM_PROVIDER_KEY", "OPENAI_API_KEY"]
    assert path.read_text(encoding="utf-8") == original


# END OF FILE
