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
@file test_config_line_endings.py
@brief Configuration edits keep the file's line endings on every OS.
@details Files are written and read as explicit bytes, so each test fails on
         Linux and on Windows when an edit translates line endings.
"""

import json
import tomllib

from adore.cli import EXIT_OK, _set_toml_scalar, main
from adore.config import load_config
from adore.profiles import ProfileStore
from adore.state import StateStore
from adore.web.app import _set_endpoint, create_app
from fastapi.testclient import TestClient
import pytest

_CONFIG = """[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../runtime-project"

[executor.opencode]
command = "opencode run --dir {worktree} -m {model} {prompt}"
model   = "openai/gpt-5.4-fast"

[delivery]
reviewers = ["reviewer.one"]

[budgets]
max_iterations = 20  # keep this comment

[container]
runtime_env = { UV_LINK_MODE = "copy" }
"""
_HEAD = _CONFIG.split("[worktree]")[0]  # lines no edit below touches


def _assert_endings(data: bytes, newline: str) -> None:
    """@brief Every line ends with `newline`; no CR is added or doubled."""
    if newline == "\r\n":
        assert b"\r\r" not in data
        assert data.count(b"\n") == data.count(b"\r\n")
    else:
        assert b"\r" not in data


@pytest.mark.parametrize("newline", ["\r\n", "\n"])
def test_scalar_edit_keeps_the_text_line_endings(newline):
    """
    @brief   Replaced, inserted and appended lines use the text's own ending,
             and every other line is returned unchanged.
    """
    def native(text):
        return text.replace("\n", newline)

    text = native("[budgets]\nmax_iterations = 20  # keep\n")
    assert _set_toml_scalar(text, "budgets.max_iterations", "30") == native(
        "[budgets]\nmax_iterations = 30  # keep\n")
    assert _set_toml_scalar(text, "budgets.max_files_touched", "5") == native(
        "[budgets]\nmax_files_touched = 5\nmax_iterations = 20  # keep\n")
    assert _set_toml_scalar(text, "polling.poll_interval_seconds", "60") == native(
        "[budgets]\nmax_iterations = 20  # keep\n\n[polling]\npoll_interval_seconds = 60\n")
    unterminated = native("a = 1\n[budgets]")
    assert _set_toml_scalar(unterminated, "budgets.max_iterations", "3") == native(
        "a = 1\n[budgets]\nmax_iterations = 3")
    last_key = native("[budgets]\nmax_iterations = 20")
    assert _set_toml_scalar(last_key, "budgets.max_iterations", "4") == native(
        "[budgets]\nmax_iterations = 4")
    no_final_newline = native("a = 1\nb = 2")
    assert _set_toml_scalar(no_final_newline, "polling.poll_interval_seconds", "60") == native(
        "a = 1\nb = 2\n\n[polling]\npoll_interval_seconds = 60\n")


def test_scalar_edit_in_a_mixed_file_keeps_each_line_ending():
    """@brief A replaced line keeps its own ending; an added line takes CR LF."""
    text = "[budgets]\r\nmax_iterations = 20\nmax_files_touched = 5\r\n"
    assert _set_toml_scalar(text, "budgets.max_iterations", "30") == (
        "[budgets]\r\nmax_iterations = 30\nmax_files_touched = 5\r\n")
    assert _set_toml_scalar(text, "budgets.max_cost_usd", "2.5") == (
        "[budgets]\r\nmax_cost_usd = 2.5\r\nmax_iterations = 20\nmax_files_touched = 5\r\n")


@pytest.mark.parametrize("newline", ["\r\n", "\n"])
@pytest.mark.parametrize("container", [
    '[container]\nruntime_env = { UV_LINK_MODE = "copy" }\n',
    '[container.runtime_env]\nUV_LINK_MODE = "copy"\n',
])
def test_endpoint_edit_keeps_the_text_line_endings(newline, container):
    """
    @brief   The OpenCode endpoint edit, which may rewrite the inline runtime
             environment as a section and sets several keys in a row, keeps
             the text's line endings and every line before the container table.
    """
    head = "[platform]\nkind = \"gitlab\"\n\n".replace("\n", newline)
    text = head + container.replace("\n", newline)
    changed = _set_endpoint(text, "https://model.local/v1", "openai/gpt-x",
                            timeout_seconds=30, ca_file="/etc/ssl/model-ca.pem")
    _assert_endings(changed.encode("utf-8"), newline)
    assert changed.startswith(head)
    runtime_env = tomllib.loads(changed)["container"]["runtime_env"]
    assert runtime_env["OPENAI_BASE_URL"] == "https://model.local/v1"
    assert runtime_env["NODE_EXTRA_CA_CERTS"] == "/etc/ssl/model-ca.pem"
    assert runtime_env["UV_LINK_MODE"] == "copy"


def test_endpoint_edit_in_a_mixed_file_keeps_the_previous_line_ending():
    """
    @brief   Removing an unterminated last inline table gives the line before it
             back its own LF, even in a file that also uses CR LF.
    """
    text = '[container]\r\nimage = "x"\nruntime_env = { UV_LINK_MODE = "copy" }'
    changed = _set_endpoint(text, "https://model.local/v1", "openai/gpt-x")
    assert changed.startswith('[container]\r\nimage = "x"\n\r\n[container.runtime_env]\r\n')
    assert tomllib.loads(changed)["container"]["runtime_env"]["UV_LINK_MODE"] == "copy"


@pytest.mark.parametrize("newline", ["\r\n", "\n"])
def test_endpoint_edit_keeps_trailing_lines_when_moving_the_inline_table(newline):
    """
    @brief   Moving an inline runtime environment into its own section removes
             only that line; trailing spaces and blank lines stay as they were.
    """
    def native(text):
        return text.replace("\n", newline)

    text = native('[container]\nruntime_env = { UV_LINK_MODE = "copy" }\nimage = "x"  \n\n')
    changed = _set_endpoint(text, "https://model.local/v1", "openai/gpt-x")
    assert changed.startswith(native('[container]\nimage = "x"  \n\n'))
    _assert_endings(changed.encode("utf-8"), newline)
    assert tomllib.loads(changed)["container"]["runtime_env"]["UV_LINK_MODE"] == "copy"

    # The inline table as the unterminated last line.
    last = native('[container]\nimage = "x"\nruntime_env = { UV_LINK_MODE = "copy" }')
    changed = _set_endpoint(last, "https://model.local/v1", "openai/gpt-x")
    assert changed.startswith(native('[container]\nimage = "x"\n'))
    _assert_endings(changed.encode("utf-8"), newline)
    assert tomllib.loads(changed)["container"]["runtime_env"]["UV_LINK_MODE"] == "copy"


@pytest.mark.parametrize("newline", ["\r\n", "\n"])
def test_cli_config_set_keeps_the_file_line_endings(tmp_path, newline):
    """
    @brief   `adore config set` changes only the edited value, on every OS,
             and an appended table uses the file's line ending.
    """
    path = tmp_path / "config.toml"
    original = _CONFIG.replace("\n", newline).encode("utf-8")
    path.write_bytes(original)

    assert main(["-c", str(path), "config", "set", "budgets.max_iterations", "12"]) == EXIT_OK
    assert path.read_bytes() == original.replace(b"max_iterations = 20", b"max_iterations = 12")

    assert main(["-c", str(path), "config", "set", "recovery.max_stage_failures", "4"]) == EXIT_OK
    data = path.read_bytes()
    _assert_endings(data, newline)
    assert data.startswith(_HEAD.replace("\n", newline).encode("utf-8"))
    assert load_config(path).recovery.max_stage_failures == 4


@pytest.mark.parametrize("newline", ["\r\n", "\n"])
def test_web_edits_keep_the_file_line_endings(tmp_path, newline):
    """
    @brief   Staging and applying a key whose table is absent, a direct edit
             and the OpenCode endpoint edit all succeed and keep the file's
             line endings.
    """
    profiles = ProfileStore(tmp_path / "home")
    root = tmp_path / "state"
    profiles.create("alpha", store_root=str(root))
    path = profiles.config_path("alpha")
    text = _CONFIG + f'\n[state]\nstore_root = "{root.as_posix()}"\n'
    original = text.replace("\n", newline).encode("utf-8")
    path.write_bytes(original)
    StateStore(root).pause()
    head = _HEAD.replace("\n", newline).encode("utf-8")
    with TestClient(create_app(profiles.home)) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        headers = {"X-CSRF-Token": csrf}

        def revision():
            return client.get("/api/v1/projects/alpha/config").json()["revision"]

        staged = client.post("/api/v1/projects/alpha/config/pending", json={
            "key": "recovery.max_stage_failures", "value": "4",
            "revision": revision()}, headers=headers)
        assert staged.status_code == 200, staged.text
        applied = client.post("/api/v1/projects/alpha/config/apply", json={
            "candidate_revision": staged.json()["candidate_revision"]}, headers=headers)
        assert applied.status_code == 200, applied.text
        before = path.read_bytes()
        _assert_endings(before, newline)
        assert before.startswith(original)  # the new table is appended
        assert load_config(path).recovery.max_stage_failures == 4

        direct = client.put("/api/v1/projects/alpha/config", json={
            "key": "budgets.max_iterations", "value": "15", "revision": revision()},
            headers=headers)
        assert direct.status_code == 200, direct.text
        assert path.read_bytes() == before.replace(b"max_iterations = 20", b"max_iterations = 15")

        endpoint = client.put("/api/v1/projects/alpha/config", json={
            "key": "container.runtime_env.OPENAI_BASE_URL",
            "value": "http://model.local:1234/v1", "revision": revision()},
            headers=headers)
        assert endpoint.status_code == 200, endpoint.text
        data = path.read_bytes()
        _assert_endings(data, newline)
        assert data.startswith(head)
        runtime_env = load_config(path).container.runtime_env
        assert runtime_env["OPENAI_BASE_URL"] == "http://model.local:1234/v1"
        assert runtime_env["UV_LINK_MODE"] == "copy"
        assert "openai" in json.loads(runtime_env["OPENCODE_CONFIG_CONTENT"])["provider"]
