#!/usr/bin/env python3
# -*- coding: utf-8 -*-  # noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_config.py
@brief Tests for typed config loading, derived names, and validation.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.1.1
"""

from __future__ import annotations

# IMPORTS
from pathlib import Path

from ador.config import Config, load_config, validate_config

# CONSTANTS

MINIMAL_VALID = """
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../cockpit-gcp"

[executor.opencode]
command = "opencode run --dir {worktree} -m {model} {prompt}"
model   = "openai/gpt-5.4-fast"

[delivery]
reviewers = ["dan.pasare"]
"""

# HELPER FUNCTIONS


def _write_config(tmp_path: Path, text: str) -> Path:
    """
    @brief      Write a config.toml into the test dir.
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  text TOML content.
    @return     The config file path.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    return path


# PUBLIC API / TESTS


def test_minimal_config_is_valid_with_defaults(tmp_path: Path) -> None:
    """
    @brief   A minimal file loads, defaults apply, and validation passes.
    @version 0.1.0
    """
    config = load_config(_write_config(tmp_path, MINIMAL_VALID))
    assert validate_config(config) == []
    assert config.agent.name == "ADOR"
    assert config.polling.poll_interval_seconds == 60
    assert config.labels.lifecycle.ready == "agent-ready"
    assert config.labels.selection.priority_order() == ["P1", "P2", "P3"]
    assert config.budgets.max_cost_usd == 5.0
    assert config.review.trigger == "label"


def test_derived_names_follow_the_slug(tmp_path: Path) -> None:
    """
    @brief   slug, store_root, questions file, and metrics paths derive from
             the agent name when unset.
    @version 0.1.0
    """
    config = load_config(_write_config(tmp_path, '[agent]\nname = "Robo"\n' + MINIMAL_VALID))
    assert config.agent.slug == "robo"
    assert config.agent.email == "robo-bot@local"
    assert config.state.store_root == ".robo"
    assert config.executor.questions_file == "ROBO_QUESTIONS.md"
    assert config.metrics.db_path == ".robo/metrics.db"


def test_explicit_values_are_never_overridden(tmp_path: Path) -> None:
    """
    @brief   Explicit store_root/questions_file win over derivation.
    @version 0.1.0
    """
    text = (
        MINIMAL_VALID
        + '\n[state]\nstore_root = ".custom"\n'
        + '\n[executor]\nquestions_file = "ASK.md"\n'
    )
    config = load_config(_write_config(tmp_path, text))
    assert config.state.store_root == ".custom"
    assert config.executor.questions_file == "ASK.md"


def test_validation_reports_bad_enums_and_missing_repo(tmp_path: Path) -> None:
    """
    @brief   Bad enum values and a missing repo each yield one issue.
    @version 0.1.0
    """
    text = """
[platform]
kind = "bitbucket"

[state]
channel = "smoke-signals"

[executor.opencode]
command = "opencode {prompt}"
model = "m"

[delivery]
reviewers = ["r"]
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert any("[platform] kind" in issue for issue in issues)
    assert any("[platform] repo" in issue for issue in issues)
    assert any("[state] channel" in issue for issue in issues)
    assert any("[worktree] repo_path" in issue for issue in issues)


def test_validation_requires_matching_executor_table(tmp_path: Path) -> None:
    """
    @brief   The default executor must have a command table with {prompt}.
    @version 0.1.0
    """
    text = """
[platform]
repo = "g/p"

[executor]
default = "pi"

[delivery]
reviewers = ["r"]
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert any("[executor.pi]" in issue or "default 'pi'" in issue for issue in issues)


def test_validation_catches_bad_durations_and_draft_false(tmp_path: Path) -> None:
    """
    @brief   Unparseable durations and draft=false are rejected.
    @version 0.1.0
    """
    text = MINIMAL_VALID + """
[clarification]
answer_timeout = "three days"

[delivery.extra]
"""
    # draft=false must be flagged: never open a ready (mergeable) MR.
    text = text.replace('reviewers = ["dan.pasare"]', 'reviewers = ["dan.pasare"]\ndraft = false')
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert any("answer_timeout" in issue for issue in issues)
    assert any("draft" in issue for issue in issues)


def test_validation_flags_unknown_sections(tmp_path: Path) -> None:
    """
    @brief   A typo'd section name is reported instead of silently ignored.
    @version 0.1.0
    """
    issues = validate_config(load_config(_write_config(tmp_path, MINIMAL_VALID + "\n[polling2]\n")))
    assert any("unknown section: [polling2]" in issue for issue in issues)


def test_defaults_without_file_sections() -> None:
    """
    @brief   A bare Config carries the documented defaults.
    @version 0.1.0
    """
    config = Config()
    assert config.container.parked_ttl_polls == 30
    assert config.clarification.max_rounds == 3
    assert config.reconcile.on_trigger_removed == "pause"


def test_validation_rejects_bad_polling_and_slug(tmp_path: Path) -> None:
    """
    @brief   Invalid slug, non-positive interval, and malformed quiet_hours
             windows are each reported.
    @version 0.1.0
    """
    text = MINIMAL_VALID + """
[agent]
slug = "Bad Slug"

[polling]
poll_interval_seconds = 0
quiet_hours = ["late night"]
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert any("[agent] slug" in issue for issue in issues)
    assert any("poll_interval_seconds" in issue for issue in issues)
    assert any("quiet_hours" in issue for issue in issues)


def test_validation_rejects_auto_flag_in_executor_command(tmp_path: Path) -> None:
    """
    @brief   --auto in the executor command is a validation error (it would
             auto-approve the push/merge permissions; prereq report sec. 6).
    @version 0.1.0
    """
    text = MINIMAL_VALID.replace(
        'command = "opencode run --dir {worktree} -m {model} {prompt}"',
        'command = "opencode run --auto --dir {worktree} -m {model} {prompt}"',
    )
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert any("--auto" in issue for issue in issues)


# END OF FILE
