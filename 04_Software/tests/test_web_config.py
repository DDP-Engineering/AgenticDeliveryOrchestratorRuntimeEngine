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
@file test_web_config.py
@brief Web project config edit and local endpoint boundary tests.
@details A complete local example config is edited through authenticated HTTP.
"""

import json
from pathlib import Path

from adore.cli import EXIT_ERROR, EXIT_OK, main
from adore.config import load_config
from adore.profiles import ProfileStore
from adore.state import StateStore
from adore.web.app import create_app
from fastapi.testclient import TestClient


def test_local_endpoint_edit_is_validated_and_revision_checked(tmp_path):
    """@brief Admin can set a local URL; stale or hostile edits fail closed."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    path.write_bytes(example.read_bytes())
    StateStore(profiles.default_store_root("alpha")).pause()
    app = create_app(profiles.home)
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        csrf = login.json()["csrf"]
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        target = "/api/v1/projects/alpha/config"
        body = {"key": "container.runtime_env.OPENAI_BASE_URL",
                "value": "http://model.local:1234/v1", "revision": revision}
        assert client.put(target, json=body).status_code == 403
        bad = {**body, "value": "javascript:alert(1)"}
        assert client.put(target, json=bad, headers={"X-CSRF-Token": csrf}).status_code == 400
        response = client.put(target, json=body, headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        runtime_env = load_config(path).container.runtime_env
        assert runtime_env["OPENAI_BASE_URL"] == body["value"]
        provider = json.loads(runtime_env["OPENCODE_CONFIG_CONTENT"])["provider"]["openai"]
        assert provider["npm"] == "@ai-sdk/openai-compatible"
        assert provider["options"]["baseURL"] == body["value"]
        assert "gpt-5.4-fast" in provider["models"]
        assert client.put(target, json=body, headers={"X-CSRF-Token": csrf}).status_code == 409


def test_local_model_and_endpoint_are_saved_atomically(tmp_path):
    """@brief One administrator edit sets a local model and URL together."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    path.write_bytes(example.read_bytes())
    StateStore(profiles.default_store_root("alpha")).pause()
    app = create_app(profiles.home)
    with TestClient(app) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        target = "/api/v1/projects/alpha/config"
        body = {"key": "container.runtime_env.OPENAI_BASE_URL",
                "value": "http://model.local:1234/v1", "model": "local/test",
                "revision": revision}
        original = path.read_bytes()
        for bad_model in ("bad model", "local/bad model", "local/"):
            invalid = {**body, "model": bad_model}
            assert client.put(target, json=invalid,
                              headers={"X-CSRF-Token": csrf}).status_code == 400
            assert path.read_bytes() == original
        stray = {"key": "budgets.max_iterations", "value": "12",
                 "model": "local/test", "revision": revision}
        assert client.put(target, json=stray,
                          headers={"X-CSRF-Token": csrf}).status_code == 400
        assert path.read_bytes() == original
        assert client.put(target, json=body,
                          headers={"X-CSRF-Token": csrf}).status_code == 200
    config = load_config(path)
    assert config.executor.commands["opencode"].model == "local/test"
    provider = json.loads(config.container.runtime_env["OPENCODE_CONFIG_CONTENT"])
    assert provider["provider"]["local"]["models"] == {"test": {"name": "test"}}


def test_local_endpoint_uses_only_allowlisted_auth_reference(tmp_path):
    """@brief Endpoint auth references an executor environment key, never a value."""
    profiles = ProfileStore(tmp_path / "home")
    state_root = tmp_path / "state"
    profiles.create("alpha", store_root=str(state_root))
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    path.write_bytes(example.read_bytes().replace(
        b'store_root = ".adore"',
        f'store_root = "{state_root.as_posix()}"'.encode(),
    ))
    StateStore(state_root).pause()
    app = create_app(profiles.home)
    with TestClient(app) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        target = "/api/v1/projects/alpha/config/pending"
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        body = {"key": "container.runtime_env.OPENAI_BASE_URL",
                "value": "https://model.local/v1", "model": "local/test",
                "auth_env": "OPENAI_API_KEY", "revision": revision}
        original = path.read_bytes()
        for invalid in ("raw-secret", "MISSING_KEY", "{env:OPENAI_API_KEY}"):
            response = client.post(target, json={**body, "auth_env": invalid},
                                   headers={"X-CSRF-Token": csrf})
            assert response.status_code == 400
            assert path.read_bytes() == original
        staged = client.post(target, json=body, headers={"X-CSRF-Token": csrf})
        assert staged.status_code == 200, staged.text
        applied = client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": staged.json()["candidate_revision"]},
            headers={"X-CSRF-Token": csrf})
        assert applied.status_code == 200, applied.text
        viewed = client.get("/api/v1/projects/alpha/config").json()
        assert "OPENCODE_CONFIG_CONTENT" not in str(viewed)
    provider = json.loads(load_config(path).container.runtime_env[
        "OPENCODE_CONFIG_CONTENT"])["provider"]["local"]
    assert provider["options"]["apiKey"] == "{env:OPENAI_API_KEY}"


def test_local_endpoint_profile_persists_timeout_and_custom_ca(tmp_path):
    """@brief One staged edit passes the bounded HTTP policy to OpenCode."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha", store_root=str(tmp_path / "state"))
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    path.write_bytes(example.read_bytes().replace(
        b'store_root = ".adore"',
        f'store_root = "{(tmp_path / "state").as_posix()}"'.encode(),
    ))
    StateStore(tmp_path / "state").pause()
    with TestClient(create_app(profiles.home)) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        target = "/api/v1/projects/alpha/config/pending"
        body = {"key": "container.runtime_env.OPENAI_BASE_URL",
                "value": "https://model.local/v1", "model": "local/test",
                "protocol": "openai-chat-completions", "timeout_seconds": 45,
                "ca_file": "/etc/ssl/adore-model-ca.pem", "revision": revision}
        original = path.read_bytes()
        for bad in (
            {"protocol": "anthropic"}, {"timeout_seconds": 0},
            {"timeout_seconds": 601}, {"ca_file": "../ca.pem"},
            {"ca_file": "/etc/../secret"},
            {"value": "http://model.local/v1"},
        ):
            response = client.post(target, json={**body, **bad},
                                   headers={"X-CSRF-Token": csrf})
            assert response.status_code in (400, 422), response.text
            assert path.read_bytes() == original
        staged = client.post(target, json=body, headers={"X-CSRF-Token": csrf})
        assert staged.status_code == 200, staged.text
        assert staged.json()["endpoint"] == {
            "protocol": "openai-chat-completions", "model": "local/test",
            "auth_env": None, "timeout_seconds": 45,
            "ca_file": "/etc/ssl/adore-model-ca.pem",
        }
        applied = client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": staged.json()["candidate_revision"]},
            headers={"X-CSRF-Token": csrf})
        assert applied.status_code == 200, applied.text
        assert load_config(path).container.runtime_env[
            "NODE_EXTRA_CA_CERTS"] == body["ca_file"]
        next_revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        cleared = client.post(target, json={
            **body, "value": "http://model.local/v1", "ca_file": "",
            "revision": next_revision}, headers={"X-CSRF-Token": csrf})
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["endpoint"]["ca_file"] is None
        assert client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": cleared.json()["candidate_revision"]},
            headers={"X-CSRF-Token": csrf}).status_code == 200
    config = load_config(path)
    assert config.container.runtime_env["NODE_EXTRA_CA_CERTS"] == ""
    provider = json.loads(config.container.runtime_env[
        "OPENCODE_CONFIG_CONTENT"])["provider"]["local"]
    assert provider["options"]["timeout"] == 45000
    assert provider["options"]["baseURL"] == "http://model.local/v1"


def test_local_endpoint_rejects_non_opencode_profile(tmp_path):
    """@brief A URL edit cannot pretend Codex understands OpenCode settings."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    path.write_text(example.read_text(encoding="utf-8").replace(
        'default = "opencode"', 'default = "codex"'), encoding="utf-8")
    StateStore(profiles.default_store_root("alpha")).pause()
    app = create_app(profiles.home)
    with TestClient(app) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        response = client.put("/api/v1/projects/alpha/config", json={
            "key": "container.runtime_env.OPENAI_BASE_URL",
            "value": "http://model.local:1234/v1", "revision": revision,
        }, headers={"X-CSRF-Token": csrf})
        assert response.status_code == 400
        assert "OPENCODE_CONFIG_CONTENT" not in path.read_text(encoding="utf-8")


def test_cli_and_web_config_edits_share_process_lock(tmp_path, capsys):
    """@brief Concurrent ADORE editors reject a held project config lock."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    path.write_bytes(example.read_bytes())
    original = path.read_bytes()
    guard = StateStore(path.parent, "adore-config")
    assert guard.acquire_lock()
    try:
        app = create_app(profiles.home)
        with TestClient(app) as client:
            csrf = client.post("/api/v1/session", json={
                "username": "admin", "password": "admin"}).json()["csrf"]
            revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
            response = client.put("/api/v1/projects/alpha/config", json={
                "key": "budgets.max_iterations", "value": "12", "revision": revision,
            }, headers={"X-CSRF-Token": csrf})
            assert response.status_code == 409
        assert main(["-c", str(path), "config", "set",
                     "budgets.max_iterations", "12"]) == EXIT_ERROR
        assert "lock" in capsys.readouterr().out.lower()
        assert path.read_bytes() == original
    finally:
        guard.release_lock()
    assert main(["-c", str(path), "config", "set",
                 "budgets.max_iterations", "12"]) == EXIT_OK
    assert load_config(path).budgets.max_iterations == 12


def test_developer_reads_assigned_config_but_cannot_edit_or_read_other_project(tmp_path):
    """@brief Scoped redacted reads stay separate from administrator edits."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    profiles.create("beta")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    for name in ("alpha", "beta"):
        profiles.config_path(name).write_bytes(example.read_bytes())
    app = create_app(profiles.home)
    web = app.state.web_store
    developer = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(developer["id"], ["alpha"])
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/session", json={"username": "dev", "password": "longer-password"}
        )
        visible = client.get("/api/v1/projects/alpha/config")
        assert visible.status_code == 200
        assert visible.json()["config"]["platform"]["repo"] == "group/subgroup/project"
        assert client.get("/api/v1/projects/beta/config").status_code == 404
        assert client.get("/api/v1/projects/alpha/config/pending").status_code == 403
        assert client.put(
            "/api/v1/projects/alpha/config",
            json={"key": "polling.poll_interval_seconds", "value": "60", "revision": "x"},
            headers={"X-CSRF-Token": login.json()["csrf"]},
        ).status_code == 403


def test_config_view_redacts_accidental_secret_values(tmp_path):
    """@brief A config file with misplaced credentials never sends them to UI."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    text = example.read_text(encoding="utf-8")
    text = text.replace('runtime_env = { UV_LINK_MODE = "copy" }',
                        'runtime_env = { UV_LINK_MODE = "copy", API_KEY = "private-value" }')
    assert "private-value" in text
    path.write_text(text, encoding="utf-8")
    app = create_app(profiles.home)
    web = app.state.web_store
    developer = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(developer["id"], ["alpha"])
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/config")
        assert response.status_code == 200
        assert "private-value" not in response.text
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        response = client.get("/api/v1/projects/alpha/config")
        assert response.status_code == 200
        assert "private-value" not in response.text


_PARTIAL_CONFIG = """
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../runtime-project"

[executor.opencode]
command = "opencode run --dir {worktree} -m {model} {prompt}"
model   = "openai/gpt-5.4-fast"

[delivery]
reviewers = ["dan.pasare"]

[budgets]
max_iterations = 20

[container]
runtime_env = { UV_LINK_MODE = "copy", API_KEY = "private-value" }
"""


def _leaves(value, prefix=""):
    """@brief Dotted keys of the leaves of a nested mapping (non-empty mappings are walked)."""
    if isinstance(value, dict) and value:
        return [leaf for key, child in value.items()
                for leaf in _leaves(child, f"{prefix}.{key}" if prefix else key)]
    return [prefix]


def test_config_view_reports_each_settings_source_and_editability(tmp_path):
    """
    @brief   Every effective setting says whether the project's file sets it,
             whether the browser can edit it (by the same rule the staging
             endpoint applies), its file key, and whether a change restarts.
    """
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    profiles.config_path("alpha").write_bytes(_PARTIAL_CONFIG.encode("utf-8"))  # LF, as on the host
    app = create_app(profiles.home)
    web = app.state.web_store
    developer = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(developer["id"], ["alpha"])
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        csrf = {"X-CSRF-Token": login.json()["csrf"]}
        body = client.get("/api/v1/projects/alpha/config").json()
        settings = {item["key"]: item for item in body["settings"]}

        assert [item["key"] for item in body["settings"]] == sorted(settings)
        assert set(settings) == set(_leaves(body["config"]))
        assert settings["platform.repo"] == {
            "key": "platform.repo", "edit_key": "platform.repo",
            "source": "project", "editable": True, "restart": True, "default": "",
            "type": "text", "choices": [], "minimum": None, "maximum": None}
        assert settings["budgets.max_iterations"]["source"] == "project"  # equals default
        assert settings["budgets.max_iterations"]["default"] == 20
        assert settings["budgets.max_wall_clock_seconds"] == {
            "key": "budgets.max_wall_clock_seconds",
            "edit_key": "budgets.max_wall_clock_seconds",
            "source": "default", "editable": True, "restart": False, "default": 3600,
            "type": "integer", "choices": [], "minimum": 1, "maximum": None}
        assert settings["delivery.draft"] == {
            "key": "delivery.draft", "edit_key": "delivery.draft",
            "source": "default", "editable": True, "restart": False,
            "default": True, "type": "boolean", "choices": [True],
            "minimum": None, "maximum": None}  # boolean
        assert settings["metrics.db_path"]["default"] == ".adore/metrics.db"  # derived
        assert settings["agent.slug"]["default"] == "adore"
        model = settings["executor.commands.opencode.model"]
        assert model["edit_key"] == "executor.opencode.model"
        assert model["source"] == "project" and model["editable"] and model["restart"]
        assert model["default"] is None  # no command table in the default configuration
        assert settings["executor.commands.opencode.command"]["source"] == "project"
        not_editable = ["executor.commands.opencode.command", "delivery.reviewers",
                        "container.egress.allowlist", "container.runtime_env.UV_LINK_MODE",
                        "state.store_root", "clarification.max_rounds"]
        for key in not_editable:
            assert settings[key]["editable"] is False, key
        assert "container.runtime_env.API_KEY" not in settings  # redacted, never listed
        assert settings["delivery.reviewers"]["source"] == "project"
        assert settings["container.egress.allowlist"]["source"] == "default"
        assert all(not item["editable"] for key, item in settings.items()
                   if key.startswith(("state.", "clarification.")))

        revision = body["revision"]
        target = "/api/v1/projects/alpha/config/pending"
        for key, value in (("budgets.max_wall_clock_seconds", "7200"),
                           ("executor.opencode.model", "openai/gpt-5.4"),
                           ("polling.poll_interval_seconds", "60")):
            staged = client.post(target, json={"key": key, "value": value,
                                               "revision": revision}, headers=csrf)
            assert staged.status_code == 200, (key, staged.text)
            assert client.delete(target, headers=csrf).status_code == 200
        for key in ("executor.opencode.command", "state.store_root",
                    "clarification.max_rounds", "container.runtime_env.api_key"):
            refused = client.post(target, json={"key": key, "value": "x",
                                                "revision": revision}, headers=csrf)
            assert refused.status_code == 400, key
            assert refused.json()["detail"]["code"] == "setting_not_editable"

        client.post("/api/v1/session", json={"username": "dev", "password": "longer-password"})
        seen = client.get("/api/v1/projects/alpha/config").json()["settings"]
        assert seen == [item for item in body["settings"]
                        if item["key"] != "budgets.max_cost_usd"]


def test_config_view_default_of_an_emptied_map_is_the_built_in_map(tmp_path):
    """
    @brief   A project that empties a map setting sees ADORE's built-in map as
             that row's default, not "none".
    """
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    emptied = _PARTIAL_CONFIG.replace(
        'runtime_env = { UV_LINK_MODE = "copy", API_KEY = "private-value" }',
        "runtime_env = {}") + "[workflow]\nkind_labels = {}\n"
    profiles.config_path("alpha").write_bytes(emptied.encode("utf-8"))
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        body = client.get("/api/v1/projects/alpha/config").json()
        settings = {item["key"]: item for item in body["settings"]}

        assert settings["workflow.kind_labels"]["source"] == "project"
        assert settings["workflow.kind_labels"]["default"] == {
            "bug": "fix", "fix": "fix", "change": "change"}
        assert settings["container.runtime_env"]["default"] == {"UV_LINK_MODE": "copy"}
        assert settings["workflow.stage_timeout_overrides"]["default"] == {}
