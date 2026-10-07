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
@file    test_web_launch_presets.py
@brief   Reviewed launch preset HTTP contracts.
@details Offline authenticated selection proves supported commands and rejects
         unsafe, unauthorized, stale and corrupt proposals before publication.
"""

from hashlib import sha256
import json
from pathlib import Path

from adore.config import load_config
from adore.profiles import ProfileStore
from adore.state import StateStore
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest

PRESETS = {
    "opencode": "opencode run --dir {worktree} -m {model} --format json {prompt}",
    "pi": "pi -p --mode json --model {model} {prompt}",
    "codex": (
        "codex exec {resume}--json --model {model} --ignore-user-config "
        "--disable plugins --dangerously-bypass-approvals-and-sandbox {prompt}"
    ),
    "qwen": "qwen -p --model {model} --output-format json {prompt}",
}


@pytest.mark.parametrize("executor", PRESETS)
def test_launch_presets_are_reviewed_and_fail_closed(tmp_path, executor):
    """@brief Only configured supported presets pass authenticated reviewed apply."""
    profiles = ProfileStore(tmp_path / "home")
    state_root = tmp_path / "state"
    profiles.create("alpha", store_root=str(state_root))
    path = profiles.config_path("alpha")
    original = Path(__file__).resolve().parents[1] / "config.example.toml"
    text = original.read_text(encoding="utf-8")
    text = text.replace('store_root = ".adore"', f'store_root = "{state_root.as_posix()}"')
    text = text.replace("[executor.opencode]", f"[executor.{executor}]")
    text = text.replace('default = "opencode"', f'default = "{executor}"')
    text = text.replace(PRESETS["opencode"], PRESETS[executor])
    if executor == "pi":
        text = text.replace(
            PRESETS["pi"], "pi -p --mode json --model {model} --thinking medium {prompt}", 1
        )
    path.write_text(text, encoding="utf-8")
    state = StateStore(state_root)
    state.pause()
    app = create_app(profiles.home)
    dev = app.state.web_store.create_user("dev", "longer-password", "developer")
    app.state.web_store.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        headers = {"X-CSRF-Token": csrf}
        base = "/api/v1/projects/alpha/config"
        config = client.get(base).json()
        row = next(
            item
            for item in config["settings"]
            if item["key"] == f"executor.commands.{executor}.command"
        )
        assert row["editable"] is True
        assert row["choices"] == [PRESETS[executor]]
        body = {
            "key": f"executor.{executor}.command",
            "value": PRESETS[executor],
            "revision": config["revision"],
        }
        saved = path.read_bytes()
        assert client.post(base + "/pending", json=body).status_code == 403
        assert (
            client.post(
                base + "/pending", json={**body, "revision": "0" * 64}, headers=headers
            ).status_code
            == 409
        )
        for key, value in (
            (body["key"], PRESETS[executor] + "; echo unsafe"),
            ("executor.unknown.command", "unknown {prompt}"),
            (
                f"executor.{'pi' if executor != 'pi' else 'qwen'}.command",
                PRESETS["pi" if executor != "pi" else "qwen"],
            ),
        ):
            invalid = {**body, "key": key, "value": value}
            assert client.post(base + "/pending", json=invalid, headers=headers).status_code == 400
            assert client.put(base, json=invalid, headers=headers).status_code == 400
            assert path.read_bytes() == saved
        staged = client.post(base + "/pending", json=body, headers=headers)
        assert staged.status_code == 200, staged.text
        assert staged.json()["proposed_value"] == PRESETS[executor]
        assert path.read_bytes() == saved
        apply = {"candidate_revision": staged.json()["candidate_revision"]}
        assert client.post(base + "/apply", json=apply).status_code == 403
        state.resume()
        assert client.post(base + "/apply", json=apply, headers=headers).status_code == 409
        state.pause()
        response = client.post(base + "/apply", json=apply, headers=headers)
        assert response.status_code == 200, response.text
        assert load_config(path).executor.commands[executor].command == PRESETS[executor]
        assert client.post(base + "/apply", json=apply, headers=headers).status_code == 404
        revision = client.get(base).json()["revision"]
        body["revision"] = revision
        direct = client.put(base, json=body, headers=headers)
        assert direct.status_code == 200, direct.text
        assert load_config(path).executor.commands[executor].command == PRESETS[executor]
        body["revision"] = client.get(base).json()["revision"]
        assert client.post(base + "/pending", json=body, headers=headers).status_code == 200
        pending = profiles.profile_dir("alpha") / "pending_config.json"
        record = json.loads(pending.read_text(encoding="utf-8"))
        record["value"] = PRESETS[executor] + "; echo unsafe"
        record["candidate_text"] = record["candidate_text"].replace(
            PRESETS[executor], record["value"], 1
        )
        record["candidate_revision"] = sha256(record["candidate_text"].encode()).hexdigest()
        pending.write_text(json.dumps(record), encoding="utf-8")
        applied_bytes = path.read_bytes()
        assert client.get(base + "/pending").status_code == 503
        assert (
            client.post(
                base + "/apply",
                json={"candidate_revision": record["candidate_revision"]},
                headers=headers,
            ).status_code
            == 503
        )
        assert path.read_bytes() == applied_bytes
        dev_csrf = client.post(
            "/api/v1/session", json={"username": "dev", "password": "longer-password"}
        ).json()["csrf"]
        assert (
            client.post(
                base + "/pending", json=body, headers={"X-CSRF-Token": dev_csrf}
            ).status_code
            == 403
        )
