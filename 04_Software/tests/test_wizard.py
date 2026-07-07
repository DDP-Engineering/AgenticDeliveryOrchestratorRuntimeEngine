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
@file test_wizard.py
@brief Tests for the `ador init` wizard - driven offline with a scripted asker
       and a fake command runner; the golden assertion is that every profile it
       writes passes validate_config.
@author Eng. Dan Dumitru Pasare
@date 2026-07-07
@version 0.2.0
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Sequence
from pathlib import Path

from ador.config import load_config, validate_config
from ador.profiles import ProfileStore
from ador.util import CommandResult
from ador.wizard import (
    ConsoleAsker,
    FieldSpec,
    ScriptedAsker,
    WizardError,
    _validate_or_raise,
    ask,
    run_wizard,
)
import pytest

# CONSTANTS

FIXED_NOW = "2026-07-05T00:00:00Z"

# HELPER FUNCTIONS


class FakeRunner:
    """
    @brief   Command runner double: present tools authenticate cleanly.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-05
    @version 0.1.0
    """

    def __init__(self, present: dict[str, CommandResult]) -> None:
        self.present = present

    def __call__(self, argv: Sequence[str], *, cwd=None, timeout=None, env=None) -> CommandResult:
        key = " ".join(str(part) for part in argv)
        for prefix, result in self.present.items():
            if key.startswith(prefix):
                return result
        return CommandResult(argv=list(argv), exit_code=127, stderr="not found")


def _runner() -> FakeRunner:
    ok = CommandResult(exit_code=0, stdout="ok")
    return FakeRunner({
        "git --version": ok,
        "glab --version": ok,
        "glab auth status": ok,
        "docker --version": ok,
    })


def _store(tmp_path: Path) -> ProfileStore:
    return ProfileStore(tmp_path / "home", now=lambda: FIXED_NOW)


def _answers(clone: Path, **overrides: object) -> dict[str, object]:
    """
    @brief      A complete, valid happy-path answer set (fields with defaults
                are omitted so defaults are exercised).
    @param[in]  clone An existing directory to use as the local clone path.
    @param[in]  overrides Field overrides (e.g. a queue for a re-prompt test).
    @return     The answers mapping.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    answers: dict[str, object] = {
        "description": "test project",
        "kind": "gitlab",
        "hosting": "public",
        "visibility": "private",
        "repo": "grp/sub/proj",
        "repo_path": str(clone),
        "has_push_rule": "yes",
        "branch_rule": r"^(feature|bugfix|release|hotfix)/.*$",
        "branch_template": "feature/{slug}-{iid}",
        "runtime": "docker",
        "model": "openai/gpt-5.5",
        "auth_mode": "api-key",
        "reviewers": "reviewer.one, reviewer.two",
        "budgets_choice": "recommended",
        "polling_mode": "once",
        "state_location": "profile",
        "confirm": "yes",
    }
    answers.update(overrides)
    return answers


def _clone(tmp_path: Path) -> Path:
    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True)
    return clone


# PUBLIC API / TESTS - happy path


def test_wizard_writes_a_valid_minimal_profile(tmp_path: Path) -> None:
    """
    @brief   The golden test: a full scripted run writes a profile whose
             config.toml loads and passes validate_config, with the expected
             metadata and a profile-owned state root.
    @version 0.1.1
    """
    store = _store(tmp_path)
    asker = ScriptedAsker(_answers(_clone(tmp_path)))
    profile = run_wizard(store, asker=asker, out=lambda _line: None,
                         runner=_runner(), os_key="linux", name="sample")

    assert store.exists("sample")
    config = load_config(store.config_path("sample"))
    assert validate_config(config) == []                     # <-- the golden assertion
    assert config.platform.repo == "grp/sub/proj"
    assert config.container.runtime == "docker"
    assert config.worktree.branch_rule.startswith("^(feature")
    assert config.delivery.reviewers == ["reviewer.one", "reviewer.two"]
    assert config.state.store_root.endswith("state")         # profile-owned (D2)
    assert profile.platform == "gitlab" and profile.repo == "grp/sub/proj"


def test_wizard_podman_adds_userns_keepid(tmp_path: Path) -> None:
    """
    @brief   Choosing a podman runtime auto-adds run_args=["--userns=keep-id"].
    @version 0.1.1
    """
    store = _store(tmp_path)
    asker = ScriptedAsker(_answers(_clone(tmp_path), runtime="podman"))
    run_wizard(store, asker=asker, out=lambda _l: None, runner=_runner(),
               os_key="linux", name="p")
    config = load_config(store.config_path("p"))
    assert config.container.run_args == ["--userns=keep-id"]
    assert validate_config(config) == []


# PUBLIC API / TESTS - re-prompting on invalid input


def test_wizard_reprompts_on_invalid_repo_path(tmp_path: Path) -> None:
    """
    @brief   A non-existent clone path is rejected and re-prompted (the queue's
             second answer, a real dir, is accepted).
    @version 0.1.0
    """
    store = _store(tmp_path)
    clone = _clone(tmp_path)
    asker = ScriptedAsker(_answers(clone, repo_path=[str(tmp_path / "nope"), str(clone)]))
    run_wizard(store, asker=asker, out=lambda _l: None, runner=_runner(),
               os_key="linux", name="r")
    assert asker.reads.count("repo_path") == 2               # asked twice
    assert store.exists("r")


def test_wizard_reprompts_on_bad_regex_then_template_mismatch(tmp_path: Path) -> None:
    """
    @brief   An uncompilable push-rule regex re-prompts; then a branch template
             that the rule would reject re-prompts until it matches.
    @version 0.1.0
    """
    store = _store(tmp_path)
    clone = _clone(tmp_path)
    asker = ScriptedAsker(_answers(
        clone,
        branch_rule=["(unclosed", r"^feature/.*$"],          # bad regex, then good
        branch_template=["main/{iid}", "feature/{iid}"],     # rejected, then accepted
    ))
    run_wizard(store, asker=asker, out=lambda _l: None, runner=_runner(),
               os_key="linux", name="b")
    assert asker.reads.count("branch_rule") == 2
    assert asker.reads.count("branch_template") == 2
    config = load_config(store.config_path("b"))
    assert validate_config(config) == []
    assert config.worktree.branch_template == "feature/{iid}"


# PUBLIC API / TESTS - existing profile / abort / non-interactive


def test_wizard_refuses_existing_profile_without_force(tmp_path: Path) -> None:
    """
    @brief   An existing profile is not overwritten unless --force is given.
    @version 0.1.0
    """
    store = _store(tmp_path)
    store.create("taken")
    asker = ScriptedAsker(_answers(_clone(tmp_path)))
    with pytest.raises(WizardError):
        run_wizard(store, asker=asker, out=lambda _l: None, runner=_runner(),
                   os_key="linux", name="taken")


def test_wizard_abort_writes_nothing(tmp_path: Path) -> None:
    """
    @brief   Answering "no" to the final confirm aborts and saves no profile.
    @version 0.1.0
    """
    store = _store(tmp_path)
    asker = ScriptedAsker(_answers(_clone(tmp_path), confirm="no"))
    with pytest.raises(WizardError):
        run_wizard(store, asker=asker, out=lambda _l: None, runner=_runner(),
                   os_key="linux", name="x")
    assert not store.exists("x")


def test_wizard_non_interactive_is_reproducible_and_fails_fast(tmp_path: Path) -> None:
    """
    @brief   The non-interactive path is deterministic (same answers + fixed
             clock -> identical config.toml) and fails fast on a bad answer
             instead of looping.
    @version 0.1.0
    """
    store = _store(tmp_path)
    clone = _clone(tmp_path)
    first = ScriptedAsker(_answers(clone), interactive=False)
    run_wizard(store, asker=first, out=lambda _l: None, runner=_runner(),
               os_key="linux", name="det")
    bytes_1 = store.config_path("det").read_bytes()

    second = ScriptedAsker(_answers(clone), interactive=False)
    run_wizard(store, asker=second, out=lambda _l: None, runner=_runner(),
               os_key="linux", name="det", force=True)
    assert store.config_path("det").read_bytes() == bytes_1   # reproducible

    bad = ScriptedAsker(_answers(clone, runtime="apache"), interactive=False)
    with pytest.raises(WizardError):                          # no re-prompt loop
        run_wizard(store, asker=bad, out=lambda _l: None, runner=_runner(),
                   os_key="linux", name="bad", force=True)


# PUBLIC API / TESTS - conditional branches (host / budgets / agent)


def test_wizard_corporate_host_is_recorded(tmp_path: Path) -> None:
    """
    @brief   Choosing a corporate/self-hosted instance asks for and records the
             host URL in the profile metadata.
    @version 0.1.0
    """
    store = _store(tmp_path)
    asker = ScriptedAsker(_answers(_clone(tmp_path), hosting="corporate",
                                   host_url="https://gitlab.example.com"))
    profile = run_wizard(store, asker=asker, out=lambda _l: None, runner=_runner(),
                         os_key="linux", name="corp")
    assert profile.host == "https://gitlab.example.com"
    assert asker.reads.count("host_url") == 1


def test_wizard_custom_budgets_are_written(tmp_path: Path) -> None:
    """
    @brief   The custom-budgets branch asks the four values and writes them.
    @version 0.1.0
    """
    store = _store(tmp_path)
    asker = ScriptedAsker(_answers(
        _clone(tmp_path), budgets_choice="custom", max_iterations="9",
        max_wall_clock_seconds="1200", max_cost_usd="2.5", max_files_touched="15",
    ))
    run_wizard(store, asker=asker, out=lambda _l: None, runner=_runner(),
               os_key="linux", name="cb")
    config = load_config(store.config_path("cb"))
    assert config.budgets.max_iterations == 9
    assert config.budgets.max_wall_clock_seconds == 1200
    assert config.budgets.max_cost_usd == 2.5
    assert config.budgets.max_files_touched == 15
    assert validate_config(config) == []


def test_wizard_custom_agent_name_sets_slug(tmp_path: Path) -> None:
    """
    @brief   A non-default bot name is written and its slug is derived, so the
             branch template still validates against the push rule.
    @version 0.1.0
    """
    store = _store(tmp_path)
    asker = ScriptedAsker(_answers(_clone(tmp_path), agent_name="MyBot",
                                   branch_template="feature/{slug}-{iid}"))
    run_wizard(store, asker=asker, out=lambda _l: None, runner=_runner(),
               os_key="linux", name="ag")
    config = load_config(store.config_path("ag"))
    assert config.agent.name == "MyBot" and config.agent.slug == "mybot"
    assert validate_config(config) == []


def test_wizard_non_interactive_missing_required_fails(tmp_path: Path) -> None:
    """
    @brief   A required field absent from the answers (no default) fails fast in
             non-interactive mode instead of looping, and saves nothing.
    @version 0.1.0
    """
    store = _store(tmp_path)
    answers = _answers(_clone(tmp_path))
    del answers["repo"]                                       # required, no default
    asker = ScriptedAsker(answers, interactive=False)
    with pytest.raises(WizardError):
        run_wizard(store, asker=asker, out=lambda _l: None, runner=_runner(),
                   os_key="linux", name="mr")
    assert not store.exists("mr")


# PUBLIC API / TESTS - the interactive ConsoleAsker + ask() primitive


def test_console_asker_reads_value_and_empty_is_default() -> None:
    """
    @brief   ConsoleAsker returns the typed value; an empty line means the
             default is used by ask().
    @version 0.1.0
    """
    typed = ConsoleAsker(input_fn=lambda _p: " docker ", out=lambda _l: None)
    assert ask(FieldSpec("rt", "Runtime?", default="podman"),
               typed, lambda _l: None) == "docker"
    empty = ConsoleAsker(input_fn=lambda _p: "", out=lambda _l: None)
    assert ask(FieldSpec("rt", "Runtime?", default="podman"),
               empty, lambda _l: None) == "podman"


def test_console_asker_reprompts_on_invalid_choice() -> None:
    """
    @brief   ask() re-prompts an interactive asker until the choice is valid,
             printing the error each time.
    @version 0.1.0
    """
    replies = iter(["apache", "docker"])
    seen: list[str] = []
    asker = ConsoleAsker(input_fn=lambda _p: next(replies), out=seen.append)
    value = ask(FieldSpec("rt", "Runtime?", choices=("docker", "podman")),
                asker, seen.append)
    assert value == "docker"
    assert any("choose one of" in line for line in seen)


def test_console_asker_accepts_numbered_choice() -> None:
    """
    @brief   Numbered choices are resolved to the configured string value.
    @version 0.1.0
    """
    seen: list[str] = []
    asker = ConsoleAsker(input_fn=lambda _p: "2", out=seen.append)
    value = ask(FieldSpec("rt", "Runtime?", choices=("docker", "podman")),
                asker, seen.append)

    assert value == "podman"
    assert "    1. docker" in seen
    assert "    2. podman" in seen


# PUBLIC API / TESTS - the never-save-invalid safety net


def test_validate_or_raise_rejects_invalid_config(tmp_path: Path) -> None:
    """
    @brief   The write-then-validate guard raises on a config that would fail
             validation, so an invalid profile is never committed.
    @version 0.1.0
    """
    bad_doc = "[platform]\nkind = 'bitbucket'\n"              # invalid kind, no repo
    with pytest.raises(WizardError):
        _validate_or_raise(bad_doc, lambda _l: None)


# END OF FILE
