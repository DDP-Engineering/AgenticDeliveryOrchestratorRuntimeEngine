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
@file test_web_package.py
@brief Bundled third-party notice consistency.
@details Checks notice versions against the application dependency lockfiles.
"""

import json
from pathlib import Path
import tomllib


def test_third_party_notices_match_locked_runtime_versions():
    """@brief About notices track the offline web dependency lockfiles."""
    software = Path(__file__).resolve().parents[1]
    source = (software / "web" / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    bundled = (software / "adore" / "web" / "static"
               / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert bundled == source
    with (software / "uv.lock").open("rb") as handle:
        python_versions = {item["name"]: item["version"]
                           for item in tomllib.load(handle)["package"]}
    node_lock = json.loads((software / "web" / "package-lock.json").read_text(
        encoding="utf-8"))["packages"]
    node_names = {
        "React": "react",
        "React DOM": "react-dom",
        "Scheduler": "scheduler",
        "react-markdown": "react-markdown",
        "remark-gfm": "remark-gfm",
    }
    for line in source.splitlines():
        if not line.startswith("| ") or "---" in line or "Component" in line:
            continue
        _, name, version, _license, _ = line.split("|")
        name, version = name.strip(), version.strip()
        if name in node_names:
            assert node_lock[f"node_modules/{node_names[name]}"]["version"] == version
        else:
            assert python_versions[name.lower()] == version
