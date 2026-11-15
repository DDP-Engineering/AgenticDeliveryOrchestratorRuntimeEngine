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
@brief   Refusal of removed launch-command settings.
@details Offline requests verify removed commands cannot be staged or applied.
"""

from pathlib import Path

from adore.profiles import ProfileStore
from adore.web.app import create_app

from tests.configuration_client import TestClient

PRESET = "pi -p --mode json --model {model} {prompt}"


def test_launch_preset_is_reviewed_and_fails_closed(tmp_path):
    """@brief Removed command settings are absent and refused without changing TOML."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha", store_root=str(tmp_path / "state"))
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    path.write_bytes(example.read_bytes())
    with TestClient(create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        headers = {"X-CSRF-Token": csrf}
        base = "/api/v1/projects/alpha/config"
        config = client.get(base).json()
        assert not any(row["key"] == "executor.command" for row in config["settings"])
        saved = path.read_bytes()
        body = {"key": "executor.command", "value": PRESET, "revision": config["revision"]}
        assert client.post(base + "/pending", json=body).status_code == 403
        assert client.post(base + "/pending", json=body, headers=headers).status_code == 400
        assert client.put(base, json=body, headers=headers).status_code == 400
        assert path.read_bytes() == saved
