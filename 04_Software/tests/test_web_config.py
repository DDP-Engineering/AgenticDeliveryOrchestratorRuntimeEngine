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
@brief Web project config edit boundary tests.
@details A complete local example config is edited through authenticated HTTP.
"""

import json
from pathlib import Path
import tomllib

from adore.cli import EXIT_ERROR, EXIT_OK, main
from adore.config import load_config
from adore.profiles import ProfileStore
from adore.state import StateStore
from adore.web.app import create_app
import pytest

from tests.configuration_client import TestClient


@pytest.mark.parametrize("multiline", [False, True])
def test_reviewer_list_candidate_applies_without_changing_other_settings(tmp_path, multiline):
    """@brief Admin reviews a reviewer list and changes only that complete TOML value."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha", store_root=str(tmp_path / "state"))
    path = profiles.config_path("alpha")
    text = (Path(__file__).resolve().parents[1] / "config.example.toml").read_text(encoding="utf-8")
    text = text.replace('store_root = ".adore"',
                        f'store_root = "{(tmp_path / "state").as_posix()}"')
    if multiline:
        text = text.replace('reviewers = ["dan.pasare"]', 'reviewers = [\n  "dan.pasare",\n]')
    path.write_bytes(text.replace("\n", "\r\n").encode())
    original = path.read_bytes()
    app = create_app(profiles.home)
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        response = client.post("/api/v1/projects/alpha/config/pending", headers=headers,
                               json={"key": "delivery.reviewers", "value": '["alice", "bob.smith"]',
                                     "revision": revision})
        assert response.status_code == 200, response.text
        candidate = response.json()
        assert candidate["proposed_value"] == ["alice", "bob.smith"]
        assert json.loads(candidate["value"]) == candidate["proposed_value"]
        assert candidate["restart_required"] is False
        assert path.read_bytes() == original
        assert client.get("/api/v1/projects/alpha/config/pending").json() == candidate
        result = client.post("/api/v1/projects/alpha/config/apply", headers=headers,
                             json={"candidate_revision": candidate["candidate_revision"],
                                   "base_revision": candidate["base_revision"]})
        assert result.status_code == 200, result.text
    expected = tomllib.loads(original.decode())
    expected["delivery"]["reviewers"] = ["alice", "bob.smith"]
    assert tomllib.loads(path.read_text(encoding="utf-8")) == expected
    assert b"\r\n" in path.read_bytes()



def test_approval_policy_review_and_apply(tmp_path):
    """@brief An admin can review and save only the selected project's approval policy."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha", store_root=str(tmp_path / "state"))
    path = profiles.config_path("alpha")
    text = (Path(__file__).resolve().parents[1] / "config.example.toml").read_text(encoding="utf-8")
    text = text.replace('store_root = ".adore"',
                        f'store_root = "{(tmp_path / "state").as_posix()}"')
    path.write_text(text, encoding="utf-8")
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        view = client.get("/api/v1/projects/alpha/config").json()
        row = next(row for row in view["settings"]
                   if row["key"] == "delivery.require_human_approval")
        assert row["editable"] and row["type"] == "boolean" and row["default"] is True
        response = client.post("/api/v1/projects/alpha/config/pending", headers=headers,
                               json={"key": row["key"], "value": "false",
                                     "revision": view["revision"]})
        assert response.status_code == 200, response.text
        candidate = response.json()
        assert candidate["proposed_value"] is False
        result = client.post("/api/v1/projects/alpha/config/apply", headers=headers,
                             json={"candidate_revision": candidate["candidate_revision"],
                                   "base_revision": candidate["base_revision"]})
        assert result.status_code == 200, result.text
    assert load_config(path).delivery.require_human_approval is False



@pytest.mark.parametrize("value", ["maybe", "1", "null", ""])
def test_approval_policy_rejects_invalid_web_values(tmp_path, value):
    """@brief Invalid policy input cannot produce a pending reviewed candidate."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    path.write_bytes((Path(__file__).resolve().parents[1] / "config.example.toml").read_bytes())
    original = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        view = client.get("/api/v1/projects/alpha/config").json()
        response = client.post("/api/v1/projects/alpha/config/pending", headers=headers,
                               json={"key": "delivery.require_human_approval", "value": value,
                                     "revision": view["revision"]})
        assert response.status_code == 400, response.text
        assert client.get("/api/v1/projects/alpha/config/pending").json() is None
    assert path.read_bytes() == original


def test_reviewer_list_accepts_an_empty_list(tmp_path):
    """@brief An empty reviewer list is a valid candidate: the MR/PR requests no review."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    path.write_bytes((Path(__file__).resolve().parents[1] / "config.example.toml").read_bytes())
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        response = client.post("/api/v1/projects/alpha/config/pending", headers=headers,
                               json={"key": "delivery.reviewers", "value": "[]",
                                     "revision": revision})
        assert response.status_code == 200, response.text


@pytest.mark.parametrize("value", ['[1]', '[true]', '["alice", 1]', '"alice"',
                                 '[""]', '["two names"]', '["--repo"]',
                                 '["alice\\nother"]', '["' + "a" * 256 + '"]'])
def test_reviewer_list_rejects_invalid_input(tmp_path, value):
    """@brief Human list input fails closed without writing active or pending configuration."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    path.write_bytes((Path(__file__).resolve().parents[1] / "config.example.toml").read_bytes())
    original = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        response = client.post("/api/v1/projects/alpha/config/pending", headers=headers,
                               json={"key": "delivery.reviewers", "value": value,
                                     "revision": revision})
        assert response.status_code == 400, response.text
        assert path.read_bytes() == original
        assert client.get("/api/v1/projects/alpha/config/pending").json() is None


@pytest.mark.parametrize("claimed", ['["other"]', '"alice"', '[1]'])
def test_reviewer_pending_list_rejects_forged_value(tmp_path, claimed):
    """@brief Persisted list metadata must agree exactly with the prepared candidate."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    path.write_bytes((Path(__file__).resolve().parents[1] / "config.example.toml").read_bytes())
    original = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        candidate = client.post("/api/v1/projects/alpha/config/pending", headers=headers,
                                json={"key": "delivery.reviewers", "value": '["alice"]',
                                      "revision": revision})
        assert candidate.status_code == 200
        pending = profiles.profile_dir("alpha") / "pending_config.json"
        record = json.loads(pending.read_text(encoding="utf-8"))
        record["value"] = claimed
        pending.write_text(json.dumps(record), encoding="utf-8")
        response = client.get("/api/v1/projects/alpha/config/pending")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "pending_config_corrupt"
        assert path.read_bytes() == original


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


@pytest.mark.parametrize("table", ["container.runtime_env", "local.environment"])
def test_config_view_hides_a_removed_agents_environment_value(tmp_path, table):
    """@brief A stale removed-agent variable is refused and its value never reaches the UI."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    inline = json.dumps({"provider": {"x": {"options": {"apiKey": "stale-private-value"}}}})
    text = example.read_text(encoding="utf-8")
    if table == "container.runtime_env":
        line = 'runtime_env = { UV_LINK_MODE = "copy" }'
        assert line in text
        # A dotted name is still one variable and stays hidden.
        text = text.replace(line, "runtime_env = { OPENCODE_CONFIG_CONTENT = "
                            + json.dumps(inline) + ', "OPENCODE_X.Y" = "stale-private-value" }')
    else:
        text += f"\n[{table}]\nOPENCODE_CONFIG_CONTENT = {json.dumps(inline)}\n"
    path.write_text(text, encoding="utf-8")
    app = create_app(profiles.home)
    web = app.state.web_store
    developer = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(developer["id"], ["alpha"])
    with TestClient(app) as client:
        for user, password in (("admin", "admin"), ("dev", "longer-password")):
            client.post("/api/v1/session", json={"username": user, "password": password})
            response = client.get("/api/v1/projects/alpha/config")
            assert response.status_code == 200
            assert "stale-private-value" not in response.text
            reason = ("configures a removed coding agent" if table == "container.runtime_env"
                      else "[local] unknown field: environment; remove it from config.toml")
            assert any(reason in issue for issue in response.json()["issues"])


_PARTIAL_CONFIG = """
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../runtime-project"

[executor]
provider = "openai"
model = "gpt-5.4-fast"

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


def test_progress_publication_explicit_false_is_retained_in_gui(tmp_path):
    """@brief A saved false overrides the enabled GUI default without rewriting TOML."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    original = _PARTIAL_CONFIG.replace(
        "[delivery]", "[delivery]\npublish_checkpoints = false").encode("utf-8")
    path.write_bytes(original)
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        body = client.get("/api/v1/projects/alpha/config").json()
    setting = next(item for item in body["settings"]
                   if item["key"] == "delivery.publish_checkpoints")
    assert body["config"]["delivery"]["publish_checkpoints"] is False
    assert setting["default"] is True and setting["source"] == "project"
    assert path.read_bytes() == original


@pytest.mark.parametrize("explicit", [False, True])
def test_pickup_review_defaults_and_supported_catalog(tmp_path, explicit):
    """@brief GUI uses shared defaults, retains overrides and omits inactive fields."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    original = _PARTIAL_CONFIG + (
        "\n[readiness]\nrequire_acceptance_criteria = true\n"
        "\n[review]\nmax_review_rounds = 2\n" if explicit else ""
    )
    path.write_text(original, encoding="utf-8")
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/config")
        assert response.status_code == 200
        body = response.json()
    rows = {row["key"]: row for row in body["settings"]}
    assert rows["readiness.require_acceptance_criteria"]["default"] is False
    assert rows["review.max_review_rounds"]["default"] == 5
    assert body["config"]["readiness"]["require_acceptance_criteria"] is explicit
    assert body["config"]["review"]["max_review_rounds"] == (2 if explicit else 5)
    assert rows["review.max_review_rounds"]["source"] == ("project" if explicit else "default")
    assert "require_known_component" not in body["config"]["readiness"]
    assert "readiness.require_known_component" not in rows
    assert path.read_text(encoding="utf-8") == original


def test_cli_shows_shared_defaults_without_component_setting(tmp_path, capsys):
    """@brief CLI JSON exposes the same supported defaults as the GUI catalog."""
    path = tmp_path / "config.toml"
    path.write_text(_PARTIAL_CONFIG, encoding="utf-8")
    assert main(["--config", str(path), "config", "show"]) == EXIT_OK
    shown = json.loads(capsys.readouterr().out)
    assert shown["readiness"]["require_acceptance_criteria"] is False
    assert shown["review"]["max_review_rounds"] == 5
    assert "require_known_component" not in shown["readiness"]


def test_statistics_storage_settings_are_external_and_cannot_prepare(tmp_path):
    """@brief Informational statistics paths retain TOML values without web write authority."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    path.write_bytes(_PARTIAL_CONFIG.encode("utf-8"))
    before = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        config = client.get("/api/v1/projects/alpha/config").json()
        settings = {item["key"]: item for item in config["settings"]}
        for key in ("metrics.db_path", "metrics.export_jsonl", "metrics.html_out"):
            assert settings[key]["editable"] is False
            response = client.post("/api/v1/projects/alpha/config/pending", headers=headers,
                                   json={"key": key, "value": "other-file",
                                         "revision": config["revision"]})
            assert response.status_code == 400
        assert client.get("/api/v1/projects/alpha/config/pending").json() is None
    assert path.read_bytes() == before


def test_installation_settings_are_external_and_cannot_be_mutated(tmp_path):
    """@brief Installation values are readable while direct and staged writes are refused."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    path.write_bytes(_PARTIAL_CONFIG.encode("utf-8"))
    before = path.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        view = client.get("/api/v1/projects/alpha/config").json()
        settings = {item["key"]: item for item in view["settings"]}
        for key in ("workflow.aegis_python", "state.store_root",
                    "worktree.repo_path", "worktree.root"):
            assert settings[key]["editable"] is False, key
            section, name = key.split(".")
            assert name in view["config"][section]
            for method, route in ((client.put, "/api/v1/projects/alpha/config"),
                                  (client.post, "/api/v1/projects/alpha/config/pending")):
                response = method(route, headers=headers,
                                  json={"key": key, "value": "other-value",
                                        "revision": view["revision"]})
                assert response.status_code == 400, (key, response.text)
                assert path.read_bytes() == before
                assert client.get("/api/v1/projects/alpha/config/pending").json() is None


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
            "default": True, "type": "boolean", "choices": [True, False],
            "minimum": None, "maximum": None}  # boolean
        assert body["config"]["delivery"]["publish_checkpoints"] is True
        assert settings["delivery.publish_checkpoints"]["default"] is True
        assert settings["delivery.publish_checkpoints"]["source"] == "default"
        assert settings["metrics.db_path"]["default"] == ".adore/metrics.db"  # derived
        assert settings["agent.slug"]["default"] == "adore"
        model = settings["executor.model"]
        assert model["edit_key"] == "executor.connection"
        assert model["source"] == "project" and model["editable"] and model["restart"]
        assert model["default"] == ""  # no universal model default
        command = settings["executor.command"]
        assert command["source"] == "default" and command["editable"] is True
        assert command["choices"] == [command["default"]]
        assert settings["delivery.reviewers"]["editable"] is True
        assert settings["delivery.reviewers"]["type"] == "list"
        not_editable = ["container.egress.allowlist", "container.runtime_env.UV_LINK_MODE",
                        "state.store_root", "clarification.reminder_after"]
        for key in not_editable:
            assert settings[key]["editable"] is False, key
        assert "container.runtime_env.API_KEY" not in settings  # redacted, never listed
        assert settings["delivery.reviewers"]["source"] == "project"
        assert settings["container.egress.allowlist"]["source"] == "default"
        assert all(not item["editable"] for key, item in settings.items()
                   if key.startswith("state.") or key in {
                       "clarification.reminder_after", "clarification.timeout_state"})

        revision = body["revision"]
        target = "/api/v1/projects/alpha/config/pending"
        for key, value in (("budgets.max_wall_clock_seconds", "7200"),
                           ("executor.connection", '{"provider":"openai","model":"gpt-5.4",'
                                                   '"thinking":"","base_url":"","api":""}'),
                           ("polling.poll_interval_seconds", "60")):
            staged = client.post(target, json={"key": key, "value": value,
                                               "revision": revision}, headers=csrf)
            assert staged.status_code == 200, (key, staged.text)
            assert client.delete(target, headers=csrf).status_code == 200
        for key in ("executor.unknown.command", "state.store_root", "executor.model",
                    "clarification.reminder_after", "container.runtime_env.api_key"):
            refused = client.post(target, json={"key": key, "value": "x",
                                                "revision": revision}, headers=csrf)
            assert refused.status_code == 400, key
            assert refused.json()["detail"]["code"] == "setting_not_editable"

        original = profiles.config_path("alpha").read_bytes()
        for method, route in ((client.put, "/api/v1/projects/alpha/config"),
                              (client.post, target)):
            refused = method(route, json={"key": "state.store_root", "value": "elsewhere",
                                          "revision": revision}, headers=csrf)
            assert refused.status_code == 400
            assert refused.json()["detail"]["code"] == "setting_not_editable"
            assert profiles.config_path("alpha").read_bytes() == original
        assert not (profiles.profile_dir("alpha") / "pending_config.json").exists()

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
