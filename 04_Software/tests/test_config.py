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
@version 0.3.0
"""

from __future__ import annotations

# IMPORTS
from pathlib import Path

from adore.config import Config, load_config, validate_config

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
    @version 0.1.1
    """
    config = load_config(_write_config(tmp_path, MINIMAL_VALID))
    assert validate_config(config) == []
    assert config.agent.name == "ADORE"
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
    @version 0.1.1
    """
    config = Config()
    assert config.container.image == "adore-executor-base:1.0.0"
    assert config.container.egress.mode == "open"
    assert config.container.required_tool_checks == []
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


def test_validation_checks_container_run_args(tmp_path: Path) -> None:
    """
    @brief   run_args entries must be single option tokens; a bare word or a
             token with spaces (would corrupt the run argv) is reported,
             while a valid option like --userns=keep-id passes.
    @version 0.1.0
    """
    text = MINIMAL_VALID + """
[container]
run_args = ["--userns=keep-id", "rm", "--memory 2g"]
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    run_args_issues = [issue for issue in issues if "run_args" in issue]
    assert len(run_args_issues) == 2  # "rm" and "--memory 2g"; keep-id is fine
    assert any("'rm'" in issue for issue in run_args_issues)


def _codex_config(command: str) -> str:
    """
    @brief      A minimal config with codex as the default executor.
    @param[in]  command The [executor.codex] command template to test.
    @return     The TOML text.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    return f"""
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../cockpit-gcp"

[executor]
default = "codex"

[executor.codex]
command = "{command}"
model   = "gpt-5.5-codex"

[delivery]
reviewers = ["dan.pasare"]
"""


def test_codex_requires_non_interactive_sandboxed_json(tmp_path: Path) -> None:
    """
    @brief   A codex command without JSON + workspace sandboxing is reported;
             adding the current non-interactive CLI shape fixes it.
    @version 0.1.1
    """
    blocking = "codex exec {resume}--json --model {model} {prompt}"
    issues = validate_config(load_config(_write_config(tmp_path, _codex_config(blocking))))
    assert any("non-interactively" in issue for issue in issues)

    ok = (
        "codex exec {resume}--json --model {model} --ignore-user-config "
        "--disable plugins --sandbox workspace-write {prompt}"
    )
    assert validate_config(load_config(_write_config(tmp_path, _codex_config(ok)))) == []


def test_codex_accepts_external_container_sandbox_bypass(tmp_path: Path) -> None:
    """
    @brief   Codex full-auto mode is accepted because ADORE provides the
             external container sandbox boundary.
    @version 0.1.2
    """
    bypass = (
        "codex exec {resume}--json --model {model} "
        "--ignore-user-config --disable plugins "
        "--dangerously-bypass-approvals-and-sandbox {prompt}"
    )
    assert validate_config(load_config(_write_config(tmp_path, _codex_config(bypass)))) == []


def test_codex_rejects_machine_local_user_config(tmp_path: Path) -> None:
    """
    @brief   Codex runs must ignore machine-local user config/plugin state and
             use ADORE's staged CODEX_HOME instead.
    @version 0.1.1
    """
    command = (
        "codex exec {resume}--json --model {model} "
        "--dangerously-bypass-approvals-and-sandbox {prompt}"
    )
    issues = validate_config(load_config(_write_config(tmp_path, _codex_config(command))))
    assert any("--ignore-user-config" in issue for issue in issues)


def test_codex_rejects_plugin_materialization(tmp_path: Path) -> None:
    """
    @brief   Codex runs must disable bundled plugins so marketplace files are
             not materialized into the target worktree.
    @version 0.1.0
    """
    command = (
        "codex exec {resume}--json --model {model} --ignore-user-config "
        "--dangerously-bypass-approvals-and-sandbox {prompt}"
    )
    issues = validate_config(load_config(_write_config(tmp_path, _codex_config(command))))
    assert any("--disable plugins" in issue for issue in issues)


def test_qwen_bans_yolo(tmp_path: Path) -> None:
    """
    @brief   A qwen command with --yolo (or --approval-mode yolo) is reported;
             a plain qwen command is accepted.
    @version 0.1.0
    """
    base = """
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../cockpit-gcp"

[executor]
default = "qwen"

[executor.qwen]
command = "{command}"
model   = "qwen3-coder-plus"

[delivery]
reviewers = ["dan.pasare"]
"""
    yolo = base.replace("{command}",
                        "qwen -p --model {model} --yolo {prompt}")
    assert any("--yolo" in i for i in
               validate_config(load_config(_write_config(tmp_path, yolo))))

    ok = base.replace("{command}",
                     "qwen -p --model {model} --output-format json {prompt}")
    qwen_issues = [i for i in validate_config(load_config(_write_config(tmp_path, ok)))
                   if "qwen" in i]
    assert qwen_issues == []


def test_container_runtime_env_defaults_and_validation(tmp_path: Path) -> None:
    """
    @brief   [container] runtime_env is a non-secret customization surface:
             uv copy-link mode defaults on, while managed git env cannot be
             overridden by human config.
    @version 0.1.1
    """
    base = """
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../cockpit-gcp"

[executor.opencode]
command = "opencode run --dir {worktree} -m {model} --format json {prompt}"
model   = "openai/gpt-5.4-fast"

[delivery]
reviewers = ["dan.pasare"]
"""
    config = load_config(_write_config(tmp_path, base))
    assert config.container.runtime_env["UV_LINK_MODE"] == "copy"
    assert validate_config(config) == []

    overridden = base + """
[container.runtime_env]
GIT_DIR = "/tmp/nope"
"""
    issues = validate_config(load_config(_write_config(tmp_path, overridden)))
    assert any("runtime_env.GIT_DIR is managed by ADORE" in issue for issue in issues)


def test_container_required_tool_checks_validation(tmp_path: Path) -> None:
    """
    @brief   required_tool_checks accepts shell-free command strings and
             rejects malformed or shell-controlled entries.
    @version 0.1.0
    """
    valid = MINIMAL_VALID + """
[container]
required_tool_checks = ["make --version", "terraform --version"]
"""
    config = load_config(_write_config(tmp_path, valid))
    assert config.container.required_tool_checks == [
        "make --version",
        "terraform --version",
    ]
    assert validate_config(config) == []

    invalid = MINIMAL_VALID + """
[container]
required_tool_checks = ["", "--version", "make --version && rm -rf /", "unterminated 'quote"]
"""
    issues = validate_config(load_config(_write_config(tmp_path, invalid)))
    assert sum("required_tool_checks" in issue for issue in issues) == 4
    assert any("must not be empty" in issue for issue in issues)
    assert any("must start with a tool name" in issue for issue in issues)
    assert any("shell control" in issue for issue in issues)
    assert any("not parseable" in issue for issue in issues)


def test_container_egress_defaults_and_valid_modes(tmp_path: Path) -> None:
    """
    @brief   Missing [container.egress] defaults to unrestricted open egress;
             none and allowlist-proxy validate when explicitly configured.
    @version 0.1.1
    """
    defaulted = load_config(_write_config(tmp_path, MINIMAL_VALID))
    assert defaulted.container.egress.mode == "open"
    assert validate_config(defaulted) == []

    none = load_config(_write_config(tmp_path, MINIMAL_VALID + """
[container.egress]
mode = "none"
"""))
    assert none.container.egress.mode == "none"
    assert validate_config(none) == []

    proxy = load_config(_write_config(tmp_path, MINIMAL_VALID + """
[container.egress]
mode = "allowlist-proxy"
allowlist = ["gitlab.example.com", "*.pythonhosted.org"]
no_proxy = ["localhost", "127.0.0.1", "::1", "*.internal.example"]
proxy_image = "adore-egress-proxy:1.0.0"
proxy_port = 3128
network_prefix = "adore-egress"
"""))
    assert proxy.container.egress.allowlist == [
        "gitlab.example.com",
        "*.pythonhosted.org",
    ]
    assert validate_config(proxy) == []


def test_container_egress_rejects_bad_allowlist_entries(tmp_path: Path) -> None:
    """
    @brief   allowlist-proxy fails closed on empty or unsafe host patterns.
    @version 0.1.0
    """
    empty = load_config(_write_config(tmp_path, MINIMAL_VALID + """
[container.egress]
mode = "allowlist-proxy"
allowlist = []
"""))
    assert any("non-empty allowlist" in issue for issue in validate_config(empty))

    invalid = load_config(_write_config(tmp_path, MINIMAL_VALID + """
[container.egress]
mode = "allowlist-proxy"
allowlist = ["https://api.openai.com", "gitlab.example.com/path", "bad host", "ok.com;rm"]
"""))
    issues = validate_config(invalid)
    assert sum("allowlist entries" in issue for issue in issues) == 4


def test_container_egress_proxy_env_is_managed(tmp_path: Path) -> None:
    """
    @brief   Humans cannot override ADORE-managed proxy env through runtime_env.
    @version 0.1.1
    """
    text = MINIMAL_VALID + """
[container.runtime_env]
HTTPS_PROXY = "http://example.invalid:3128"
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert any("runtime_env.HTTPS_PROXY is managed by ADORE" in issue for issue in issues)


# END OF FILE
