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
@brief Tests for the `adore init` wizard - driven offline with a scripted asker
       and a fake command runner; the golden assertion is that every profile it
       writes passes validate_config.
@details Known branch-rule fixture evaluation is injected; real matcher and
         process-protocol verification remains in test_branch_naming.py.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Sequence
import json
from pathlib import Path
import re
import subprocess
import tomllib

from adore import wizard
from adore.config import load_config, validate_config
from adore.profiles import ProfileStore
from adore.util import CommandResult
from adore.wizard import (
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


@pytest.fixture(autouse=True)
def isolated_branch_rule_process(monkeypatch):
    """
    @brief Keep wizard assembly tests independent of host Python startup latency.
    @details Trusted fixture rules still match the actual generated branch; the
             real bounded process and corrupt-output contract are exercised by
             test_branch_naming.py, with the product's one-second limit intact.
    """
    def evaluate(argv, **kwargs):
        """@brief Simulate only the known JSON-in/boolean-out regex boundary."""
        assert argv[1:3] == ["-I", "-c"]
        assert kwargs["timeout"] == 1 and kwargs["capture_output"]
        rule, name = json.loads(kwargs["input"])
        return subprocess.CompletedProcess(
            argv, 0, json.dumps(re.match(rule, name) is not None), "")
    monkeypatch.setattr("adore.config.subprocess.run", evaluate)


class FakeRunner:
    """
    @brief   Command runner double: present tools authenticate cleanly.
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
    """
    answers: dict[str, object] = {
        "description": "test project",
        "kind": "gitlab",
        "repo": "grp/sub/proj",
        "repo_path": str(clone),
        "has_push_rule": "yes",
        "branch_rule": r"^(feature|bugfix|release|hotfix)/.*$",
        "branch_template": "feature/{slug}-{iid}",
        "runtime": "docker",
        "provider": "openai", "model": "gpt-5.5",
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
    assert config.delivery.approval_label == "agent-approved"
    assert config.recovery.max_stage_failures == 3
    assert config.recovery.retry_backoff_seconds == [5, 30, 120]
    assert config.budgets.max_iterations == 20
    assert config.budgets.max_files_touched == 120
    assert config.state.store_root.endswith("state")         # profile-owned (D2)
    assert profile.platform == "gitlab" and profile.repo == "grp/sub/proj"


def test_wizard_writes_pi_without_agent_choice_or_host_sign_in(tmp_path: Path) -> None:
    """@brief The wizard asks for no agent, writes [executor] model and refuses host-auth."""
    store = _store(tmp_path)
    clone = _clone(tmp_path)
    asked: list[str] = []
    asker = ScriptedAsker(_answers(clone), interactive=False)
    original = asker.read

    def record(spec):
        asked.append(spec.key)
        return original(spec)

    asker.read = record
    run_wizard(store, asker=asker, out=lambda _line: None,
               runner=_runner(), os_key="linux", name="pi")
    assert "executor_cli" not in asked and "auth_mode" not in asked
    document = tomllib.loads(store.config_path("pi").read_text(encoding="utf-8"))
    assert document["executor"] == {"provider": "openai", "model": "gpt-5.5",
                                    "env_keys": []}
    asker = ScriptedAsker(_answers(
        clone, execution_backend="local", auth_mode="host-auth"
    ), interactive=False)
    with pytest.raises(WizardError, match="auth_mode"):
        run_wizard(store, asker=asker, out=lambda _line: None,
                   runner=_runner(), os_key="linux", name="pi-host-auth")
    assert not store.exists("pi-host-auth")


def test_wizard_podman_adds_userns_keepid(tmp_path: Path) -> None:
    """
    @brief   Choosing a podman runtime auto-adds run_args=["--userns=keep-id"].
    """
    store = _store(tmp_path)
    asker = ScriptedAsker(_answers(_clone(tmp_path), runtime="podman"))
    run_wizard(store, asker=asker, out=lambda _l: None, runner=_runner(),
               os_key="linux", name="p")
    config = load_config(store.config_path("p"))
    assert config.container.run_args == ["--userns=keep-id"]
    assert validate_config(config) == []


def test_wizard_writes_custom_recovery_and_approval(tmp_path: Path) -> None:
    """@brief Fail-loud thresholds and approval label are assisted settings."""
    store = _store(tmp_path)
    asker = ScriptedAsker(_answers(
        _clone(tmp_path),
        max_stage_failures="4",
        max_transient_retries="2",
        retry_backoff_seconds="1,10",
        approval_label="human-approved",
    ))
    run_wizard(store, asker=asker, out=lambda _l: None, runner=_runner(),
               os_key="linux", name="recovery")
    config = load_config(store.config_path("recovery"))
    assert config.recovery.max_stage_failures == 4
    assert config.recovery.max_transient_retries == 2
    assert config.recovery.retry_backoff_seconds == [1, 10]
    assert config.delivery.approval_label == "human-approved"


# PUBLIC API / TESTS - re-prompting on invalid input


def test_wizard_reprompts_on_invalid_repo_path(tmp_path: Path) -> None:
    """
    @brief   A non-existent clone path is rejected and re-prompted (the queue's
             second answer, a real dir, is accepted).
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


def test_wizard_gitlab_uses_cli_host_guidance_without_dead_prompts(
    tmp_path: Path,
) -> None:
    """
    @brief   GitLab/GitHub routing stays with the CLI's active/default host;
             the wizard neither collects nor records ineffective host data.
    """
    store = _store(tmp_path)
    asker = ScriptedAsker(_answers(_clone(tmp_path)))
    output: list[str] = []
    profile = run_wizard(store, asker=asker, out=output.append, runner=_runner(),
                         os_key="linux", name="corp")
    assert profile.host == ""
    assert {"hosting", "host_url", "visibility"}.isdisjoint(asker.reads)
    assert any("active/default authenticated host" in line for line in output)
    assert any("adore profile path corp" in line for line in output)


def test_wizard_gitea_asks_login_instead_of_hosting(tmp_path: Path) -> None:
    """
    @brief   The gitea path keeps its tea login selector (tea binds host + token
             to a login) and writes it to [platform] login.
    """
    store = _store(tmp_path)
    asker = ScriptedAsker(_answers(_clone(tmp_path), kind="gitea",
                                   login="home", repo="owner/repo"))
    profile = run_wizard(store, asker=asker, out=lambda _l: None, runner=_runner(),
                         os_key="linux", name="gitea-proj")
    config = load_config(store.config_path("gitea-proj"))
    assert validate_config(config) == []
    assert config.platform.kind == "gitea"
    assert config.platform.login == "home"
    assert profile.platform == "gitea" and profile.host == ""
    assert asker.reads.count("login") == 1
    assert {"hosting", "host_url", "visibility"}.isdisjoint(asker.reads)


def test_wizard_custom_budgets_are_written(tmp_path: Path) -> None:
    """
    @brief   The custom-budgets branch asks the four values and writes them.
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
    """
    bad_doc = "[platform]\nkind = 'bitbucket'\n"              # invalid kind, no repo
    with pytest.raises(WizardError):
        _validate_or_raise(bad_doc, lambda _l: None)


def test_wizard_defaults_omit_the_workflow_section(tmp_path: Path) -> None:
    """
    @brief   Accepting every workflow-label default writes no [workflow] table
             at all: the emitted config stays minimal and the defaults live in
             one place (decision D4).
    """
    clone = _clone(tmp_path)
    store = ProfileStore(tmp_path / "home")
    run_wizard(store, asker=ScriptedAsker(_answers(clone)), out=lambda _: None,
               runner=_runner(), os_key="linux", name="p")
    text = store.config_path("p").read_text(encoding="utf-8")
    assert "[workflow]" not in text
    assert "[labels.lifecycle]" not in text


def test_wizard_writes_custom_workflow_labels(tmp_path: Path) -> None:
    """
    @brief   Custom ready / fix / change / quick labels land in the config as
             the label map ADORE resolves the AEGIS run kind and profile from,
             and the result validates.
    """
    clone = _clone(tmp_path)
    store = ProfileStore(tmp_path / "home")
    answers = _answers(clone, ready_label="ai-ready", fix_label="defect",
                       change_label="tweak", quick_label="ai-quick")
    run_wizard(store, asker=ScriptedAsker(answers), out=lambda _: None,
               runner=_runner(), os_key="linux", name="p")
    text = store.config_path("p").read_text(encoding="utf-8")
    assert "ready = 'ai-ready'" in text
    assert "'defect' = 'fix'" in text and "'tweak' = 'change'" in text
    assert "quick_label = 'ai-quick'" in text

    config = load_config(store.config_path("p"))
    assert validate_config(config) == []
    assert config.labels.lifecycle.ready == "ai-ready"
    assert config.workflow.kind_labels == {"defect": "fix", "tweak": "change"}
    assert config.workflow.quick_label == "ai-quick"


def test_wizard_reports_a_missing_aegis_payload(tmp_path: Path) -> None:
    """
    @brief Missing AEGIS is direct-workflow information, not a setup defect.
    """
    clone = _clone(tmp_path)
    store = ProfileStore(tmp_path / "home")
    lines: list[str] = []
    base_runner = _runner()

    def probe(argv, **kwargs):
        """@brief Missing payloads cannot trigger even a failed AEGIS command."""
        assert ".agentic/aegis.py" not in argv
        return base_runner(argv, **kwargs)

    run_wizard(store, asker=ScriptedAsker(_answers(clone)), out=lines.append,
               runner=probe, os_key="linux", name="p")
    printed = "\n".join(lines)
    assert "  [INFO] No AEGIS found: tickets run in the direct workflow" in lines
    assert "[CHECK] AEGIS payload" not in printed and "JSON schema 1" not in printed
    assert store.config_path("p").is_file()  # never blocks
    assert validate_config(load_config(store.config_path("p"))) == []


@pytest.mark.parametrize("interpreter", ["python", "python3"])
@pytest.mark.parametrize("available", [True, False])
def test_wizard_probes_with_effective_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interpreter: str, available: bool,
) -> None:
    """@brief Real candidate validation supplies probe Python; failures never gate saving."""
    clone = _clone(tmp_path)
    wrapper = clone / ".agentic" / "aegis.py"
    wrapper.parent.mkdir()
    wrapper.write_text("# fake companion\n", encoding="utf-8")
    if interpreter != "python":
        original = wizard._assemble_sections

        def assemble(**kwargs):
            """@brief Arrange an existing config key, without adding a wizard answer."""
            sections = original(**kwargs)
            for header, values in sections:
                if header == "workflow":
                    values["aegis_python"] = interpreter
                    break
            else:
                sections.append(("workflow", {"aegis_python": interpreter}))
            return sections

        monkeypatch.setattr(wizard, "_assemble_sections", assemble)

    calls: list[list[str]] = []
    base_runner = _runner()

    def probe(argv, **kwargs):
        """@brief Fake external probes, preserving argv and candidate-read ordering."""
        if len(argv) > 1 and argv[1] == ".agentic/aegis.py":
            assert kwargs["cwd"] == str(clone)
            assert "confirm" in asker.reads
            calls.append(list(argv))
            if not available:
                return CommandResult(exit_code=127, stderr="not found")
            if argv[-1] == "--version":
                return CommandResult(exit_code=0, stdout="aegis 0.15.2")
            return CommandResult(exit_code=0, stdout=json.dumps({
                "schema": 1, "command": "status", "tasks": [], "unreadable": [],
            }))
        return base_runner(argv, **kwargs)

    store = _store(tmp_path)
    asker = ScriptedAsker(_answers(clone))
    lines: list[str] = []
    run_wizard(store, asker=asker, out=lines.append, runner=probe, os_key="linux", name="p")
    config = load_config(store.config_path("p"))
    assert validate_config(config) == []
    assert config.workflow.aegis_python == interpreter
    expected = [[interpreter, ".agentic/aegis.py", "--version"]]
    if available:
        expected.append([interpreter, ".agentic/aegis.py", "status", "--all", "--json"])
        assert "  [OK] AEGIS payload (schema 1)" in lines
    else:
        assert "  [CHECK] AEGIS payload" in lines
        printed = "\n".join(lines)
        assert f"{interpreter} is not available to run the AEGIS companion CLI" in printed
        assert "JSON schema 1" in printed
    assert calls == expected


def test_wizard_reports_unsupported_present_payload_without_direct_fallback(tmp_path: Path) -> None:
    """@brief A broken installed contract is CHECK, not absence or a profile-save block."""
    clone = _clone(tmp_path)
    wrapper = clone / ".agentic" / "aegis.py"
    wrapper.parent.mkdir()
    wrapper.write_text("# fake companion\n", encoding="utf-8")
    base_runner = _runner()
    calls = []

    def probe(argv, **kwargs):
        """@brief An unsupported version must stop probing before status."""
        if ".agentic/aegis.py" in argv:
            calls.append(list(argv))
            return CommandResult(stdout="aegis 1.0.0")
        return base_runner(argv, **kwargs)

    store = _store(tmp_path)
    lines = []
    run_wizard(store, asker=ScriptedAsker(_answers(clone)), out=lines.append,
               runner=probe, os_key="linux", name="unsupported")
    assert calls == [["python", ".agentic/aegis.py", "--version"]]
    assert "  [CHECK] AEGIS payload" in lines
    assert any("aegis 1.0.0" in line for line in lines)
    assert not any("No AEGIS found" in line for line in lines)
    assert validate_config(load_config(store.config_path("unsupported"))) == []


@pytest.mark.parametrize("child", [False, True])
@pytest.mark.parametrize("choice,answer,expected", [
    (None, None, "npm test"),
    ("use suggestion", None, "npm test"),
    ("enter another command", None, "npm test"),
    ("enter another command", "  printf '$HOME café💡\\\\' | cat  ",
     "  printf '$HOME café💡\\\\' | cat  "),
    ("enter another command", "printf '\x7f💡\x01'", "printf '\x7f💡\x01'"),
    ("no verification", None, ""),
])
def test_wizard_verification_hint_choices_and_exact_save(tmp_path, child, choice, answer, expected):
    """@brief Shared defaults/provenance stay optional and save only human choices."""
    from adore.verification_hint import suggest_verification_command

    clone = _clone(tmp_path)
    manifest = clone / "service" / "package.json" if child else clone / "package.json"
    manifest.parent.mkdir(exist_ok=True)
    manifest.write_text('{"scripts":{"test":"vitest run"}}', encoding="utf-8")
    command, source = suggest_verification_command(clone)
    answers = _answers(clone)
    if choice is not None:
        answers["verification_choice"] = choice
    if answer is not None:
        answers["verify_command"] = answer
    asker = ScriptedAsker(answers, interactive=False)
    seen = {}
    read = asker.read

    def record(spec):
        seen[spec.key] = spec
        return read(spec)

    asker.read = record
    store = _store(tmp_path)
    run_wizard(store, asker=asker, out=lambda _: None,
               runner=_runner(), os_key="linux", name="hint")
    action = seen["verification_choice"]
    assert action.default == "use suggestion"
    assert source in action.description and command in action.description
    if choice == "enter another command":
        assert seen["verify_command"].default == command
    if child and expected == "npm test":
        expected = "cd service && npm test"
    assert load_config(store.config_path("hint")).workflow.verify_command == expected


@pytest.mark.parametrize("choice", [None, "enter another command"])
def test_wizard_no_match_defaults_to_none(tmp_path, choice):
    """@brief No eligible file leaves an empty optional answer, not an invented command."""
    clone = _clone(tmp_path)
    store = _store(tmp_path)
    answers = _answers(clone)
    if choice:
        answers["verification_choice"] = choice
    asker = ScriptedAsker(answers, interactive=False)
    seen = {}
    read = asker.read

    def record(spec):
        seen[spec.key] = spec
        return read(spec)

    asker.read = record
    run_wizard(store, asker=asker, out=lambda _: None, runner=_runner(), os_key="linux", name="p")
    assert seen["verification_choice"].default == "no verification"
    assert "Suggested from" not in seen["verification_choice"].description
    if choice:
        assert seen["verify_command"].default == ""
    assert load_config(store.config_path("p")).workflow.verify_command == ""


@pytest.mark.parametrize("prepare_only,aegis", [(True, False), (True, True), (False, True)])
def test_wizard_skips_hints_for_aegis_and_offline_preparation(tmp_path, prepare_only, aegis):
    """@brief Payload presence, even unusable, and prepare-only never discover CLI hints."""
    clone = _clone(tmp_path)
    (clone / "package.json").write_text('{"scripts":{"test":"vitest run"}}', encoding="utf-8")
    if aegis:
        (clone / ".agentic").mkdir()
        (clone / ".agentic" / "aegis.py").write_text("broken", encoding="utf-8")
    asker = ScriptedAsker(_answers(clone), interactive=False)
    store = _store(tmp_path)
    lines = []
    run_wizard(store, asker=asker, out=lines.append, runner=_runner(), os_key="linux",
               name="p", prepare_only=prepare_only)
    assert "verification_choice" not in asker.reads and "verify_command" not in asker.reads
    assert not any("Suggested from" in line for line in lines)
    if not prepare_only:
        assert load_config(store.config_path("p")).workflow.verify_command == ""


@pytest.mark.parametrize("changes,field", [
    ({"verification_choice": "run now"}, "verification_choice"),
    ({"verification_choice": "enter another command", "verify_command": "one\ntwo"},
     "verify_command"),
    ({"verification_choice": "enter another command", "verify_command": "one\rtwo"},
     "verify_command"),
    ({"verification_choice": "enter another command", "verify_command": "one\0two"},
     "verify_command"),
    ({"confirm": "no"}, "config"),
])
def test_wizard_verification_invalid_or_cancelled_never_saves(tmp_path, changes, field):
    """@brief Invalid command/choice and cancellation fail before profile publication."""
    clone = _clone(tmp_path)
    (clone / "go.mod").touch()
    store = _store(tmp_path)
    with pytest.raises(WizardError) as error:
        run_wizard(store, asker=ScriptedAsker(_answers(clone, **changes), interactive=False),
                   out=lambda _: None, runner=_runner(), os_key="linux", name="p")
    assert error.value.field == field
    assert not store.exists("p") and not store.config_path("p").exists()


@pytest.mark.parametrize("text", [
    "[" * 2000,
    '{"scripts":{"test":' + "1" * 5000 + "}}",
    '{"unused":' + "[" * 2000 + "0" + "]" * 2000 + "}",
], ids=["truncated-deep-json", "oversized-integer", "deep-json"])
@pytest.mark.parametrize("fallback", [False, True])
def test_wizard_hint_package_decoder_failure_is_a_miss(tmp_path, text, fallback):
    """@brief Package decoder failures still offer the no-match or later-row CLI default."""
    clone = _clone(tmp_path)
    (clone / "package.json").write_text(text, encoding="utf-8")
    if fallback:
        (clone / "go.mod").touch()
    store = _store(tmp_path)
    asker = ScriptedAsker(_answers(clone), interactive=False)
    run_wizard(store, asker=asker, out=lambda _: None, runner=_runner(), os_key="linux", name="p")
    assert "verification_choice" in asker.reads
    assert load_config(store.config_path("p")).workflow.verify_command == (
        "go test ./..." if fallback else "")


def test_wizard_hint_symlink_loop_is_field_addressed(tmp_path):
    """@brief A static manifest link loop refuses setup before saving a profile."""
    clone = _clone(tmp_path)
    manifest = clone / "package.json"
    manifest.symlink_to(manifest)
    store = _store(tmp_path)
    with pytest.raises(WizardError) as error:
        run_wizard(store, asker=ScriptedAsker(_answers(clone)), out=lambda _: None,
                   runner=_runner(), os_key="linux", name="p")
    assert error.value.field == "repo_path"
    assert str(manifest) not in str(error.value)
    assert not store.exists("p") and not store.config_path("p").exists()


def test_wizard_hint_access_failure_is_field_addressed(tmp_path, monkeypatch):
    """@brief Unreadable evidence is an explicit refusal, not a guessed empty default."""
    clone = _clone(tmp_path)
    original = Path.iterdir

    def denied(path):
        if path == clone:
            raise PermissionError("fixture denied")
        return original(path)

    monkeypatch.setattr(Path, "iterdir", denied)
    store = _store(tmp_path)
    with pytest.raises(WizardError) as error:
        run_wizard(store, asker=ScriptedAsker(_answers(clone)), out=lambda _: None,
                   runner=_runner(), os_key="linux", name="p")
    assert error.value.field == "repo_path"
    assert not store.exists("p")


@pytest.mark.parametrize("raw", ["", "  echo 'café💡' | cat  ", "   "])
def test_console_command_only_preserves_exact_input(raw):
    """@brief Only command answers are verbatim; Enter still selects the default."""
    asker = ConsoleAsker(input_fn=lambda _: raw, out=lambda _: None)
    assert ask(FieldSpec("verify_command", "Command?", default="npm test"),
               asker, lambda _: None) == (raw if raw else "npm test")


@pytest.mark.parametrize("name,choices,command", [
    ("keep", [""], "go test ./..."), ("clear", ["3"], ""),
    ("edit", ["bad", "2", "  echo chosen  "], "  echo chosen  "),
])
def test_console_wizard_enter_keeps_and_explicit_none_clears(tmp_path, name, choices, command):
    """@brief Real interactive readers can accept, edit, clear and re-prompt safely."""
    clone = _clone(tmp_path)
    (clone / "go.mod").touch()
    store = _store(tmp_path)
    scripted = ScriptedAsker(_answers(clone))
    replies = iter(choices)
    console = ConsoleAsker(input_fn=lambda _: next(replies), out=lambda _: None)
    read = scripted.read

    def mixed(spec):
        return console.read(spec) if spec.key in {"verification_choice", "verify_command"} \
            else read(spec)

    scripted.read = mixed
    run_wizard(store, asker=scripted, out=lambda _: None, runner=_runner(),
               os_key="linux", name=name)
    assert load_config(store.config_path(name)).workflow.verify_command == command


# END OF FILE
