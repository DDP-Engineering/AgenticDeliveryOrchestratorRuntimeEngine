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
@file test_secret_setting_names.py
@brief ADORE's own non-secret settings with credential-looking names stay
       visible and editable; every other such name stays a secret.
"""

from adore.cli import EXIT_ERROR, EXIT_OK, main
from adore.config import load_config
from adore.profiles import ProfileStore
from adore.state import StateStore
from adore.web.app import create_app
from fastapi.testclient import TestClient

_CONFIG = """[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../runtime-project"

[executor]
model = "openai/gpt-5.4-fast"

[delivery]
reviewers = ["reviewer.one"]

[container]
runtime_env = { UV_LINK_MODE = "copy", GITHUB_TOKEN = "example-value" }
"""


def test_web_lists_and_edits_capture_tokens_but_not_secret_names(tmp_path):
    """
    @brief   metrics.capture_tokens has a row an administrator can edit; a
             runtime entry named like a token stays hidden and uneditable.
    """
    profiles = ProfileStore(tmp_path / "home")
    root = tmp_path / "state"
    profiles.create("alpha", store_root=str(root))
    path = profiles.config_path("alpha")
    path.write_bytes((_CONFIG + f'\n[state]\nstore_root = "{root.as_posix()}"\n').encode("utf-8"))
    StateStore(root).pause()
    with TestClient(create_app(profiles.home)) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        headers = {"X-CSRF-Token": csrf}
        response = client.get("/api/v1/projects/alpha/config")
        assert "example-value" not in response.text
        body = response.json()
        settings = {item["key"]: item for item in body["settings"]}

        tokens = settings["metrics.capture_tokens"]
        assert tokens["editable"] is True and tokens["default"] is True
        assert tokens["source"] == "default"
        assert body["config"]["metrics"]["capture_tokens"] is True
        assert "container.runtime_env.GITHUB_TOKEN" not in settings
        assert "GITHUB_TOKEN" not in body["config"]["container"]["runtime_env"]

        edited = client.put("/api/v1/projects/alpha/config", json={
            "key": "metrics.capture_tokens", "value": "false",
            "revision": body["revision"]}, headers=headers)
        assert edited.status_code == 200, edited.text
        assert load_config(path).metrics.capture_tokens is False

        not_boolean = client.put("/api/v1/projects/alpha/config", json={
            "key": "metrics.capture_tokens", "value": "ghp_example",
            "revision": edited.json()["revision"]}, headers=headers)
        assert not_boolean.status_code == 400
        assert not_boolean.json()["detail"]["code"] == "invalid_config"

        refused = client.put("/api/v1/projects/alpha/config", json={
            "key": "container.runtime_env.GITHUB_TOKEN", "value": "other",
            "revision": edited.json()["revision"]}, headers=headers)
        assert refused.status_code == 400
        assert refused.json()["detail"]["code"] == "setting_not_editable"


def test_a_non_boolean_capture_tokens_value_stays_hidden(tmp_path):
    """
    @brief   The exemption covers the boolean setting only: a string written
             into metrics.capture_tokens by hand is still treated as a secret.
    """
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    path.write_bytes((_CONFIG + '\n[metrics]\ncapture_tokens = "ghp_filevalue"\n').encode("utf-8"))
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/config")
        assert response.status_code == 200, response.text
        assert "ghp_filevalue" not in response.text
        keys = {item["key"] for item in response.json()["settings"]}
        assert "metrics.capture_tokens" not in keys


def test_cli_sets_capture_tokens_but_refuses_secret_names(tmp_path, capsys):
    """@brief `adore config set` accepts metrics.capture_tokens only."""
    path = tmp_path / "config.toml"
    path.write_bytes(_CONFIG.encode("utf-8"))

    assert main(["-c", str(path), "config", "set", "metrics.capture_tokens", "false"]) == EXIT_OK
    assert load_config(path).metrics.capture_tokens is False

    before = path.read_bytes()
    assert main(["-c", str(path), "config", "set",
                 "metrics.capture_tokens", "ghp_example"]) == EXIT_ERROR
    assert path.read_bytes() == before
    capsys.readouterr()
    assert main(["-c", str(path), "config", "set",
                 "container.runtime_env.GITHUB_TOKEN", "other"]) == EXIT_ERROR
    assert ".env" in capsys.readouterr().out
    assert path.read_bytes() == before
