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
@file    test_web_executor_session.py
@brief   Offline authenticated archived-session contracts.
@details Replays recorded Pi stdout and exercises untrusted file boundaries.
"""

# IMPORTS
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from tests.test_web_jobs import _fixture, _login


# LOCAL HELPERS
def _archive(store, name="build-attempt-2-attempt1", records=None):
    """@brief Write one physical launch in the current archive format."""
    folder = store.run_dir("same") / "io" / "archive" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "meta.json").write_text(json.dumps({
        "created_at": "2026-11-14T10:00:00Z", "archive_stem": name.split("-attempt1")[0],
        "exit_code": 0, "timed_out": False, "argv": ["ignored"], "timeout": 300,
        "output_file_present": True, "stderr_file_present": True,
    }), encoding="utf-8")
    if records is None:
        fixture = (Path(__file__).parents[2] / "00_Planning" /
                   "2026-11-01_Pi_Single_Executor/fixtures/run_tool_calls_chatgpt.jsonl")
        records = [item["record"] for line in fixture.read_text(encoding="utf-8").splitlines()
                   if (item := json.loads(line))["dir"] == "stdout"]
    (folder / "output.jsonl").write_bytes(b"".join(
        (json.dumps(record, ensure_ascii=False) + "\n").encode() for record in records))
    return folder


def _url(item, suffix=""):
    return f"/api/v1/jobs/{item.project_id}/same/sessions{suffix}"


# PUBLIC CONTRACT TESTS
@pytest.mark.parametrize("role", ["admin", "developer"])
def test_recorded_session_replay_visibility_and_pagination(tmp_path, role):
    """@brief Both authorized roles see recorded text without system or duplicates."""
    _, items, stores, app = _fixture(tmp_path)
    folder = _archive(stores[0])
    records = [
        {"type": "message_end", "message": {"role": "system", "content": "SYSTEM_NEVER"}},
        {"type": "message_end", "message": {"role": "user", "content": "literal prompt"}},
        {"type": "message_end", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "answer"}, {"type": "thinking", "thinking": "reason"}],
            "usage": {"input": 7, "output": 9, "cost": {"total": 1.23}}}},
        {"type": "tool_execution_start", "toolCallId": "x", "toolName": "bash",
         "args": {"command": "echo API_KEY=fake-key-EXACT"}},
        {"type": "tool_execution_end", "toolCallId": "x", "toolName": "bash", "isError": False,
         "result": {"content": [{"type": "text", "text": "API_KEY=fake-key-EXACT"}]}},
        {"type": "message_update", "assistantMessageEvent": {"delta": "DELTA_NEVER"}},
        {"type": "agent_end", "messages": [{"content": "DUPLICATE_NEVER"}]},
    ]
    with (folder / "output.jsonl").open("ab") as handle:
        handle.write(b"".join((json.dumps(x) + "\n").encode() for x in records))
    if role == "developer":
        user = app.state.web_store.create_user("dev", "test-password", "developer")
        app.state.web_store.set_memberships(user["id"], ["alpha"])
    with TestClient(app) as client:
        _login(client) if role == "admin" else _login(client, "dev", "test-password")
        response = client.get(_url(items[0]))
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        session = response.json()["sessions"][0]
        assert session["id"] == folder.name and session["stage"] == "build"
        assert session["attempt"] == 2 and session["start_at"] is None
        assert session["outcome"] == "succeeded"
        cursor, all_items = 0, []
        while True:
            response = client.get(_url(items[0], f"/{folder.name}?cursor={cursor}&limit=1"))
            assert response.status_code == 200, response.text
            assert response.headers["cache-control"] == "no-store"
            page = response.json()
            assert 0 <= len(page["items"]) <= 1
            all_items.extend(part for item in page["items"] for part in item.get("parts", [item]))
            if page["next_cursor"] is None:
                break
            assert page["next_cursor"] > cursor
            cursor = page["next_cursor"]
        rendered = json.dumps(all_items)
        assert all(kind in {x["kind"] for x in all_items} for kind in
                   ["prompt", "assistant", "reasoning", "tool_call", "tool_result",
                    "turn", "usage"])
        assert "fake-key-EXACT" in rendered
        assert all(value not in rendered for value in
                   ["SYSTEM_NEVER", "DELTA_NEVER", "DUPLICATE_NEVER"])
        assert ("cost" in json.dumps(all_items[-3:])) is (role == "admin")
        assert client.get(_url(items[1])).status_code == (200 if role == "admin" else 404)
        output = client.get(f"/api/v1/jobs/{items[0].project_id}/same/executor-output")
        assert output.status_code == 200


def test_bad_lines_bounds_and_incomplete_tail_are_isolated(tmp_path):
    """@brief Bad records are notices, text is bounded and unfinished data waits."""
    _, items, stores, app = _fixture(tmp_path)
    folder = _archive(stores[0], records=[])
    source = folder / "output.jsonl"
    source.write_bytes(b'not json\n\xff\n' + b'x' * (300 * 1024) + b'\n' +
                       b'{"adore_omitted_bytes":100}\n{"adore_output_truncated":true}\n' +
                       b'{"type":"adore_malformed_record","bytes":13,"head":"bad"}\n' +
                       b'{"type":"message_end","message":{"role":"system",'
                       b'"role":"user","content":"DUPLICATE_SYSTEM_NEVER"}}\n' +
                       (json.dumps({"type": "message_end", "message": {"role": "user",
                        "content": "🙂" * 10000}}) + "\n").encode() + b'{"unfinished":')
    with TestClient(app) as client:
        _login(client)
        response = client.get(_url(items[0], f"/{folder.name}"))
        assert response.status_code == 200, response.text
        data = response.json()
        assert len([x for x in data["items"] if x["kind"] == "notice"]) == 7
        assert "DUPLICATE_SYSTEM_NEVER" not in response.text
        item = next(x for x in data["items"] if x["kind"] == "prompt")
        assert len(item["text"].encode()) <= 16 * 1024
        assert item["text"].endswith("[truncated]")
        assert "unfinished" not in response.text


def test_collision_suffix_ten_and_huge_physical_record_are_bounded(tmp_path):
    """@brief Valid decimal collision suffixes survive and huge sources emit a notice."""
    _, items, stores, app = _fixture(tmp_path)
    folder = _archive(stores[0], name="build-attempt-2-attempt1-10", records=[])
    with (folder / "output.jsonl").open("wb") as source:
        source.truncate(65 * 1024 * 1024)
    with TestClient(app) as client:
        _login(client)
        assert client.get(_url(items[0])).json()["sessions"][0]["id"] == folder.name
        response = client.get(_url(items[0], f"/{folder.name}"))
        assert response.status_code == 200
        assert response.json()["items"][0]["kind"] == "notice"
        assert response.json()["next_cursor"] is None


def test_huge_usage_integer_is_a_notice_and_later_text_survives(tmp_path):
    """@brief An untrusted cost cannot overflow float conversion or stop the page."""
    _, items, stores, app = _fixture(tmp_path)
    folder = _archive(stores[0], records=[
        {"type": "message_end", "message": {"role": "assistant", "content": [],
         "usage": {"input": 1, "cost": {"total": 10**400}}}},
        {"type": "message_end", "message": {"role": "user", "content": "after corruption"}},
    ])
    with TestClient(app) as client:
        _login(client)
        response = client.get(_url(items[0], f"/{folder.name}"))
        assert response.status_code == 200
        assert [x["kind"] for x in response.json()["items"]] == ["notice", "prompt"]
        assert response.json()["items"][1]["text"] == "after corruption"


@pytest.mark.parametrize("field,value", [("created_at", ""), ("exit_code", True),
    ("archive_stem", "../outside"), ("timed_out", "false")])
def test_corrupt_archive_metadata_fails_closed(tmp_path, field, value):
    """@brief Metadata corruption is refused, never guessed or automatically repaired."""
    _, items, stores, app = _fixture(tmp_path)
    folder = _archive(stores[0], records=[])
    path = folder / "meta.json"
    meta = json.loads(path.read_text())
    meta[field] = value
    raw = json.dumps(meta).encode()
    path.write_bytes(raw)
    with TestClient(app) as client:
        _login(client)
        assert client.get(_url(items[0])).status_code == 503
        assert client.get(_url(items[0], f"/{folder.name}")).status_code == 503
    assert path.read_bytes() == raw


@pytest.mark.parametrize("suffix", ["unknown", "build-attempt-2-attempt1?cursor=1",
    "build-attempt-2-attempt1?cursor=-1", "build-attempt-2-attempt1?cursor=9999999",
    "build-attempt-2-attempt1?limit=201", "build-attempt-2-attempt1?limit=0",
    "%2E%2E", "build-attempt-2-attempt1?cursor=abc"])
def test_invalid_session_requests_fail_closed(tmp_path, suffix):
    """@brief Untrusted identities and non-line cursors never expose raw files."""
    _, items, stores, app = _fixture(tmp_path)
    _archive(stores[0])
    with TestClient(app) as client:
        assert client.get(_url(items[0])).status_code == 401
        _login(client)
        response = client.get(_url(items[0], "/" + suffix))
        assert response.status_code in {400, 404, 422, 503}, response.text


@pytest.mark.parametrize("target", ["archive", "attempt", "output", "meta", "hardlink"])
def test_linked_session_sources_fail_closed(tmp_path, target):
    """@brief Session reads share the existing no-link identity boundary."""
    _, items, stores, app = _fixture(tmp_path)
    folder = _archive(stores[0])
    path = {"archive": folder.parent, "attempt": folder, "output": folder / "output.jsonl",
            "meta": folder / "meta.json", "hardlink": folder / "output.jsonl"}[target]
    external = tmp_path / "external"
    path.rename(external)
    try:
        if target == "hardlink":
            path.hardlink_to(external)
        else:
            path.symlink_to(external, target_is_directory=external.is_dir())
    except OSError:
        pytest.skip("host does not permit symlinks")
    with TestClient(app) as client:
        _login(client)
        response = client.get(_url(items[0], f"/{folder.name}"))
        assert response.status_code in {404, 503}, response.text
