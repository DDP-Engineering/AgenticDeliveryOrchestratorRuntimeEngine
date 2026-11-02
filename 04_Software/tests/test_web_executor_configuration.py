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
@brief      Reviewed agent connection (provider, model, endpoint) and provider-name API contracts.
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
def _connection(provider, model, base_url="", api=""):
    """@brief The strict JSON wire value of one agent connection edit."""
    return json.dumps({"provider": provider, "model": model, "base_url": base_url, "api": api})


def _stage_and_apply(client, headers, value):
    """@brief Stage one executor.connection edit and apply it; return the pending view."""
    view = client.get("/api/v1/projects/alpha/config").json()
    response = client.post("/api/v1/projects/alpha/config/pending", headers=headers, json={
        "key": "executor.connection", "value": value, "revision": view["revision"]})
    assert response.status_code == 200, response.text
    pending = response.json()
    response = client.post("/api/v1/projects/alpha/config/apply", headers=headers,
                           json={"candidate_revision": pending["candidate_revision"],
                                 "base_revision": pending["base_revision"]})
    assert response.status_code == 200, response.text
    return pending


def test_connection_is_one_reviewed_edit_and_no_agent_choice_exists(tmp_path):
    """@brief Provider, model and endpoint rows share one atomic reviewed edit; no agent row."""
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
        for key in ("executor.provider", "executor.model", "executor.endpoint.base_url",
                    "executor.endpoint.api"):
            assert metadata[key]["edit_key"] == "executor.connection"
            assert metadata[key]["editable"] is True
        assert "custom" in metadata["executor.provider"]["choices"]
        assert "chatgpt" in metadata["executor.provider"]["choices"]
        assert metadata["executor.endpoint.api"]["choices"][0] == "openai-completions"
        assert metadata["executor.command"]["choices"] == [
            "pi -p --mode json --model {model} {prompt}"]
        direct = client.post("/api/v1/projects/alpha/config/pending", headers=headers, json={
            "key": "executor.model", "value": "gpt-5.4", "revision": view["revision"]})
        assert direct.status_code == 400
        pending = _stage_and_apply(client, headers, _connection("anthropic", "claude-x"))
        assert pending["proposed_value"] == {"provider": "anthropic", "model": "claude-x",
                                             "base_url": "", "api": ""}
        assert pending["restart_required"] is True
    expected = deepcopy(tomllib.loads(original.decode()))
    expected["executor"].update(provider="anthropic", model="claude-x")
    assert tomllib.loads(path.read_text(encoding="utf-8")) == expected


def test_connection_adds_and_removes_the_endpoint_table(tmp_path):
    """@brief openai -> custom adds [executor.endpoint]; custom -> openai removes it."""
    profiles = project(tmp_path)
    StateStore(tmp_path / "state").pause()
    path = profiles.config_path("alpha")
    original = tomllib.loads(path.read_text(encoding="utf-8"))
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        pending = _stage_and_apply(client, headers, _connection(
            "custom", "qwen/qwen3.5-9b", "http://172.27.80.1:1234/v1", "openai-completions"))
        assert pending["proposed_value"]["base_url"] == "http://172.27.80.1:1234/v1"
        custom = load_config(path)
        assert custom.executor.provider == "custom"
        assert custom.executor.endpoint.base_url == "http://172.27.80.1:1234/v1"
        expected = deepcopy(original)
        expected["executor"].update(provider="custom", model="qwen/qwen3.5-9b", endpoint={
            "base_url": "http://172.27.80.1:1234/v1", "api": "openai-completions"})
        assert tomllib.loads(path.read_text(encoding="utf-8")) == expected
        view = client.get("/api/v1/projects/alpha/config").json()
        assert view["config"]["executor"]["endpoint"]["base_url"] == "http://172.27.80.1:1234/v1"
        _stage_and_apply(client, headers, _connection("openai", "gpt-5.5"))
    assert tomllib.loads(path.read_text(encoding="utf-8")) == original


@pytest.mark.parametrize("model", ["7", "1.5", "true", "007"])
def test_numeric_looking_model_id_stays_a_string(tmp_path, model):
    """@brief A model ID that reads like a number or boolean is written as a TOML string."""
    profiles = project(tmp_path)
    StateStore(tmp_path / "state").pause()
    path = profiles.config_path("alpha")
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        pending = _stage_and_apply(client, {"X-CSRF-Token": login.json()["csrf"]},
                                   _connection("openai", model))
        assert pending["proposed_value"]["model"] == model
    assert tomllib.loads(path.read_text(encoding="utf-8"))["executor"]["model"] == model
    assert load_config(path).executor.model == model


@pytest.mark.parametrize("value", [
    _connection("no-such-provider", "m"),
    _connection("openai", ""),
    _connection("openai", "model with spaces"),
    _connection("openai", "m", "http://h/v1", "openai-completions"),
    _connection("custom", "m"),
    _connection("custom", "m", "http://u:p@h/v1", "openai-completions"),
    _connection("custom", "m", "http://h/v1?key=1", "openai-completions"),
    _connection("custom", "m", "file:///etc/passwd", "openai-completions"),
    _connection("custom", "m", "http://h/v1", "bedrock"),
    json.dumps({"provider": "openai", "model": "m", "base_url": "", "api": "",
                "api_key": "sk-inline"}),
    json.dumps({"provider": "openai", "model": "m"}),
    "not json",
])
def test_invalid_connection_is_refused_and_files_stay(tmp_path, value):
    """@brief Unknown providers, bad models or URLs and extra fields are refused unstaged."""
    profiles = project(tmp_path)
    path = profiles.config_path("alpha")
    original = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.post("/api/v1/projects/alpha/config/pending",
                               headers={"X-CSRF-Token": login.json()["csrf"]},
                               json={"key": "executor.connection", "value": value,
                                     "revision": sha256(original).hexdigest()})
        assert response.status_code == 400, response.text
        assert client.get("/api/v1/projects/alpha/config/pending").json() is None
    assert path.read_bytes() == original


def test_provider_catalog_is_served_to_signed_in_users_only(tmp_path):
    """@brief The pinned Pi catalog plus chatgpt/custom; anonymous reads are refused."""
    profiles = project(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        assert client.get("/api/v1/pi-providers").status_code == 401
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        catalog = client.get("/api/v1/pi-providers").json()
    providers = {item["id"]: item for item in catalog["providers"]}
    assert providers["openai"]["variable"] == "OPENAI_API_KEY"
    assert "gpt-5.5" in providers["openai"]["models"]
    assert catalog["chatgpt"] == {"id": "chatgpt"}
    assert catalog["custom"]["variable"] == "ADORE_ENDPOINT_API_KEY"
    assert catalog["custom"]["apis"][0] == "openai-completions"
    assert catalog["pi_version"] == "1.4.0"


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
        'env_keys = []',
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
