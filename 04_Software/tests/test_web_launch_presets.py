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

PRESET = "pi -p --mode json --model {model} {prompt}"


def test_launch_preset_is_reviewed_and_fails_closed(tmp_path):
    """@brief Only the Pi preset passes authenticated reviewed apply on a container project."""
    profiles = ProfileStore(tmp_path / "home")
    state_root = tmp_path / "state"
    profiles.create("alpha", store_root=str(state_root))
    path = profiles.config_path("alpha")
    original = Path(__file__).resolve().parents[1] / "config.example.toml"
    text = original.read_text(encoding="utf-8")
    text = text.replace('store_root = ".adore"', f'store_root = "{state_root.as_posix()}"')
    text = text.replace(
        f'# command = "{PRESET}"',
        'command = "pi -p --mode json --model {model} --thinking medium {prompt}"', 1)
    assert "--thinking medium" in text
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
            if item["key"] == "executor.command"
        )
        assert row["editable"] is True
        assert row["choices"] == [PRESET]
        body = {
            "key": "executor.command",
            "value": PRESET,
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
            (body["key"], PRESET + "; echo unsafe"),
            ("executor.unknown.command", "unknown {prompt}"),
            ("executor.opencode.command", "opencode run {prompt}"),
        ):
            invalid = {**body, "key": key, "value": value}
            assert client.post(base + "/pending", json=invalid, headers=headers).status_code == 400
            assert client.put(base, json=invalid, headers=headers).status_code == 400
            assert path.read_bytes() == saved
        staged = client.post(base + "/pending", json=body, headers=headers)
        assert staged.status_code == 200, staged.text
        assert staged.json()["proposed_value"] == PRESET
        assert path.read_bytes() == saved
        apply = {"candidate_revision": staged.json()["candidate_revision"],
                 "base_revision": staged.json()["base_revision"]}
        assert client.post(base + "/apply", json=apply).status_code == 403
        state.resume()
        assert client.post(base + "/apply", json=apply, headers=headers).status_code == 409
        state.pause()
        response = client.post(base + "/apply", json=apply, headers=headers)
        assert response.status_code == 200, response.text
        assert load_config(path).executor.command == PRESET
        assert client.post(base + "/apply", json=apply, headers=headers).status_code == 404
        revision = client.get(base).json()["revision"]
        body["revision"] = revision
        direct = client.put(base, json=body, headers=headers)
        assert direct.status_code == 200, direct.text
        assert load_config(path).executor.command == PRESET
        body["revision"] = client.get(base).json()["revision"]
        assert client.post(base + "/pending", json=body, headers=headers).status_code == 200
        pending = profiles.profile_dir("alpha") / "pending_config.json"
        record = json.loads(pending.read_text(encoding="utf-8"))
        record["value"] = PRESET + "; echo unsafe"
        record["candidate_text"] = record["candidate_text"].replace(
            PRESET, record["value"], 1
        )
        record["candidate_revision"] = sha256(record["candidate_text"].encode()).hexdigest()
        pending.write_text(json.dumps(record), encoding="utf-8")
        applied_bytes = path.read_bytes()
        assert client.get(base + "/pending").status_code == 503
        assert (
            client.post(
                base + "/apply",
                json={"candidate_revision": record["candidate_revision"],
                      "base_revision": record["base_revision"]},
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
