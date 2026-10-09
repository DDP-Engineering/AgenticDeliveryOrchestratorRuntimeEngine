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
@file    test_branch_naming.py
@brief   Shared branch naming preview and configuration boundary tests.
@details Exercises public Python formatting, regex and bounded process results offline.
"""

# IMPORTS
from dataclasses import replace
import subprocess

from adore.config import branch_naming_preview, default_config, validate_config
import pytest


# PUBLIC API
def test_branch_naming_preview_matches_python_and_empty_rule():
    """@brief Examples carry explicit identity and Python regex semantics."""
    for rule in ("", r"^(?P<prefix>feature)/adore-\d+$"):
        result = branch_naming_preview("feature/{slug}-{iid}", rule, "adore")
        assert result == {"template": "feature/{slug}-{iid}", "rule": rule,
                          "slug": "adore", "iid": 1, "run_id": "sample-run-1",
                          "name": "feature/adore-1", "valid": True,
                          "rule_matches": True if rule else None, "issues": []}
    assert branch_naming_preview("{slug}/{run_id}", "", "adore")["name"] == "adore/sample-run-1"


@pytest.mark.parametrize(("template", "rule", "issue"), [
    (None, "", "invalid_template"),
    (12, "", "invalid_template"),
    ("feature/{iid}", 12, "invalid_rule"),
    ("feature/{other}-{iid}", "", "invalid_template"),
    ("feature/{slug.__class__}-{iid}", "", "invalid_template"),
    ("feature/{iid:04d}", "", "invalid_template"),
    ("feature/{iid!r}", "", "invalid_template"),
    ("feature/{iid", "", "invalid_template"),
    ("feature/{slug}", "", "missing_identity"),
    ("feature/bad name-{iid}", "", "invalid_branch"),
    ("feature/.hidden-{iid}", "", "invalid_branch"),
    ("feature/{iid}.lock", "", "invalid_branch"),
    ("feature/../{iid}", "", "invalid_branch"),
    ("-feature-{iid}", "", "invalid_branch"),
    ("feature/{iid}", "[", "invalid_rule"),
    ("feature/{iid}", "(" * 255 + "a" + ")" * 254, "invalid_rule"),
    ("feature/{iid}", "^bugfix/.*$", "rule_mismatch"),
    ("x" * 513 + "{iid}", "", "too_long"),
    ("feature/{iid}", "x" * 513, "too_long"),
])
def test_branch_naming_bad_input_is_reported_in_preview_and_config(template, rule, issue):
    """@brief Invalid configuration reports deterministic findings before a run."""
    result = branch_naming_preview(template, rule, "adore")
    assert result["valid"] is False and issue in result["issues"]
    config = default_config()
    config = replace(config, worktree=replace(config.worktree,
                                             branch_template=template, branch_rule=rule))
    assert any("[worktree]" in finding for finding in validate_config(config))


@pytest.mark.parametrize("failure", ["timeout", "exit", "json", "type", "missing"])
def test_branch_rule_process_boundary_fails_closed(monkeypatch, failure):
    """@brief Regex timeout, unavailable process and corrupt output cannot validate."""
    def run(*args, **kwargs):
        """@brief Simulate the regex evaluation process boundary."""
        assert kwargs["timeout"] == 1
        assert "shell" not in kwargs
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
        if failure == "missing":
            raise OSError("unavailable")
        return subprocess.CompletedProcess(args[0], 1 if failure == "exit" else 0,
                                           "garbage" if failure == "json" else "1", "")
    monkeypatch.setattr("adore.config.subprocess.run", run)
    result = branch_naming_preview("feature/{iid}", "^feature/", "adore")
    assert result["valid"] is False
    assert result["rule_matches"] is None
    assert result["issues"] == ["rule_timeout" if failure == "timeout" else "rule_check_failed"]

# END OF FILE
