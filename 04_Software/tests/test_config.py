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
"""

from __future__ import annotations

# IMPORTS
from pathlib import Path

from adore.config import Config, load_config, validate_config
import pytest

# CONSTANTS

MINIMAL_VALID = """
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../runtime-project"

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
    """
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    return path


# PUBLIC API / TESTS


def test_pickup_and_review_defaults_and_explicit_overrides(tmp_path: Path) -> None:
    """@brief Shared defaults apply only when the operator omits the values."""
    config = load_config(_write_config(tmp_path, MINIMAL_VALID))
    assert config.readiness.require_acceptance_criteria is False
    assert config.readiness.require_priority_label is True
    assert config.review.max_review_rounds == 5
    assert not hasattr(config.readiness, "require_known_component")
    assert validate_config(config) == []
    explicit = MINIMAL_VALID + (
        "\n[readiness]\nrequire_acceptance_criteria = true\n"
        "\n[review]\nmax_review_rounds = 2\n"
    )
    override = load_config(_write_config(tmp_path, explicit))
    assert override.readiness.require_acceptance_criteria is True
    assert override.review.max_review_rounds == 2
    assert validate_config(override) == []
    invalid = load_config(_write_config(
        tmp_path, explicit.replace("max_review_rounds = 2", "max_review_rounds = 0")
    ))
    assert any("max_review_rounds" in issue for issue in validate_config(invalid))
    sample = load_config(Path(__file__).parents[1] / "config.example.toml")
    assert sample.readiness.require_acceptance_criteria is False
    assert sample.review.max_review_rounds == 5
    assert "require_known_component" not in sample.raw["readiness"]


def test_minimal_config_is_valid_with_defaults(tmp_path: Path) -> None:
    """
    @brief   A minimal file loads, defaults apply, and validation passes.
    """
    config = load_config(_write_config(tmp_path, MINIMAL_VALID))
    assert validate_config(config) == []
    assert config.agent.name == "ADORE"
    assert config.polling.poll_interval_seconds == 60
    assert config.labels.lifecycle.ready == "agent-ready"
    assert config.labels.selection.priority_order() == ["P1", "P2", "P3"]
    assert config.budgets.max_cost_usd == 5.0
    assert config.budgets.max_files_touched == 120
    assert config.review.trigger == "label"


@pytest.mark.parametrize("reviewers", ["alice", [1], ["--repo"], ["two names"]])
def test_reviewer_config_requires_account_list(tmp_path, reviewers):
    """@brief Human-authored reviewer configuration fails closed before forge invocation."""
    config = load_config(_write_config(tmp_path, MINIMAL_VALID))
    config.delivery.reviewers = reviewers
    assert any("reviewers" in issue for issue in validate_config(config))


def test_host_auth_requires_supported_executor(tmp_path: Path) -> None:
    """@brief Host OAuth staging works for OpenCode but rejects Pi."""
    supported = MINIMAL_VALID.replace(
        "[executor.opencode]", "[executor]\nstage_host_auth = true\n\n[executor.opencode]"
    )
    assert validate_config(load_config(_write_config(tmp_path, supported))) == []

    unsupported = supported.replace(
        "stage_host_auth = true", "default = 'pi'\nstage_host_auth = true"
    )
    unsupported = unsupported.replace("[executor.opencode]", "[executor.pi]")
    unsupported = unsupported.replace("opencode run --dir {worktree} -m {model} {prompt}",
                                      "pi -p --mode json --model {model} {prompt}")
    issues = validate_config(load_config(_write_config(tmp_path, unsupported)))
    assert any("stage_host_auth" in issue and "pi" in issue for issue in issues)


def test_derived_names_follow_the_slug(tmp_path: Path) -> None:
    """
    @brief   slug, store_root, questions file, and metrics paths derive from
             the agent name when unset.
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


def test_platform_gitea_repo_shape_and_login_rules(tmp_path: Path) -> None:
    """
    @brief   kind "gitea" is valid with an OWNER/REPO slug and an optional tea
             login; a nested repo path fails closed (Gitea has no subgroups),
             and a login on glab/gh platforms is rejected (their auth binds to
             the host, so a silently ignored login would mislead).
    """
    good = MINIMAL_VALID.replace(
        'kind = "gitlab"\nrepo = "group/project"',
        'kind = "gitea"\nrepo = "owner/repo"\nlogin = "home"',
    )
    config = load_config(_write_config(tmp_path, good))
    assert validate_config(config) == []
    assert config.platform.login == "home"

    nested = MINIMAL_VALID.replace(
        'kind = "gitlab"\nrepo = "group/project"',
        'kind = "gitea"\nrepo = "owner/group/repo"',
    )
    issues = validate_config(load_config(_write_config(tmp_path, nested)))
    assert any("OWNER/REPO" in issue for issue in issues)

    login_on_gitlab = MINIMAL_VALID.replace(
        'kind = "gitlab"\nrepo = "group/project"',
        'kind = "gitlab"\nrepo = "group/project"\nlogin = "home"',
    )
    issues = validate_config(load_config(_write_config(tmp_path, login_on_gitlab)))
    assert any("login is only supported for gitea" in issue for issue in issues)


def test_validation_requires_matching_executor_table(tmp_path: Path) -> None:
    """
    @brief   The default executor must have a command table with {prompt}.
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


def test_validation_catches_bad_durations(tmp_path: Path) -> None:
    """
    @brief   Unparseable durations are rejected.
    """
    text = MINIMAL_VALID + """
[clarification]
answer_timeout = "three days"

[delivery.extra]
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert any("answer_timeout" in issue for issue in issues)


@pytest.mark.parametrize("draft", ["true", "false"])
def test_delivery_draft_accepts_both_booleans(tmp_path: Path, draft: str) -> None:
    """@brief Both requested review states are valid human configuration."""
    text = MINIMAL_VALID.replace(
        'reviewers = ["dan.pasare"]', f'reviewers = ["dan.pasare"]\ndraft = {draft}'
    )
    config = load_config(_write_config(tmp_path, text))
    assert validate_config(config) == []
    assert config.delivery.draft is (draft == "true")


@pytest.mark.parametrize("draft", ['"false"', '"true"', "0", "1", "[]"])
def test_delivery_draft_rejects_non_booleans(tmp_path: Path, draft: str) -> None:
    """@brief Truthy values cannot bypass the review-state boolean contract."""
    text = MINIMAL_VALID.replace(
        'reviewers = ["dan.pasare"]', f'reviewers = ["dan.pasare"]\ndraft = {draft}'
    )
    assert any("draft" in issue for issue in validate_config(
        load_config(_write_config(tmp_path, text))
    ))


def test_per_gate_timeout_defaults_and_is_validated(tmp_path: Path) -> None:
    """
    @brief   per_gate_timeout_seconds defaults to 1800 and is an independent
             positive knob from max_wall_clock_seconds (the whole-run ceiling).
    """
    config = load_config(_write_config(tmp_path, MINIMAL_VALID))
    assert config.budgets.per_gate_timeout_seconds == 1800
    assert config.budgets.max_wall_clock_seconds == 3600
    bad = MINIMAL_VALID + "\n[budgets]\nper_gate_timeout_seconds = 0\n"
    issues = validate_config(load_config(_write_config(tmp_path, bad)))
    assert any("per_gate_timeout_seconds" in issue for issue in issues)


def test_file_budget_rejects_zero(tmp_path: Path) -> None:
    """
    @brief   Human-configured file budgets fail closed at zero; the positive
             default is covered by the minimal-config happy path.
    """
    bad = MINIMAL_VALID + "\n[budgets]\nmax_files_touched = 0\n"
    issues = validate_config(load_config(_write_config(tmp_path, bad)))
    assert any("max_files_touched" in issue for issue in issues)


def test_validation_accepts_answer_timeout_independently_of_reserved_reminder(
        tmp_path: Path) -> None:
    """@brief An active positive answer deadline is independent of the reserved reminder."""
    text = MINIMAL_VALID + '\n[clarification]\nreminder_after = "24h"\nanswer_timeout = "12h"\n'
    assert validate_config(load_config(_write_config(tmp_path, text))) == []
    for timeout in ('0s', 'invalid'):
        bad = text.replace('answer_timeout = "12h"', f'answer_timeout = "{timeout}"')
        assert any('answer_timeout' in issue for issue in validate_config(
            load_config(_write_config(tmp_path, bad))))


def test_validation_flags_unknown_sections(tmp_path: Path) -> None:
    """
    @brief   A typo'd section name is reported instead of silently ignored.
    """
    issues = validate_config(load_config(_write_config(tmp_path, MINIMAL_VALID + "\n[polling2]\n")))
    assert any("unknown section: [polling2]" in issue for issue in issues)


def test_defaults_without_file_sections() -> None:
    """
    @brief   A bare Config carries the documented defaults.
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
    """
    text = MINIMAL_VALID + """
[container]
run_args = ["--userns=keep-id", "rm", "--memory 2g"]
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    run_args_issues = [issue for issue in issues if "run_args" in issue]
    assert len(run_args_issues) == 2  # "rm" and "--memory 2g"; keep-id is fine
    assert any("'rm'" in issue for issue in run_args_issues)


def test_container_selinux_relabel_accepts_shared_and_defaults_off(
    tmp_path: Path,
) -> None:
    """
    @brief   selinux_relabel defaults to off and accepts "shared", the mode an
             SELinux-enforcing host needs so container_t can read the bind
             mounts.
    """
    default = load_config(_write_config(tmp_path, MINIMAL_VALID))
    assert default.container.selinux_relabel == "off"
    assert not validate_config(default)
    text = MINIMAL_VALID + """
[container]
selinux_relabel = "shared"
"""
    config = load_config(_write_config(tmp_path, text))
    assert config.container.selinux_relabel == "shared"
    assert not validate_config(config)


def test_container_selinux_relabel_rejects_the_private_label(
    tmp_path: Path,
) -> None:
    """
    @brief   The private SELinux `Z` label is refused, and the message says
             why: it labels content per container, so the repository clone
             every run shares would be locked to whichever container mounted
             it first.
    """
    text = MINIMAL_VALID + """
[container]
selinux_relabel = "Z"
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    relabel_issues = [issue for issue in issues if "selinux_relabel" in issue]
    assert len(relabel_issues) == 1
    assert "shared" in relabel_issues[0]
    assert "clone" in relabel_issues[0]


def test_executor_command_rejects_a_placeholder_the_launcher_cannot_fill(
    tmp_path: Path,
) -> None:
    """
    @brief   The launcher renders the template with str.format, so an
             unsupported brace raises KeyError at GATE time, once per attempt
             until the stage budget is spent, pointing at nothing. Only Codex
             supplies {resume}; a shell `${HOME}` fails the same way. Both are
             caught at setup instead.
    """
    text = MINIMAL_VALID.replace(
        'command = "opencode run --dir {worktree} -m {model} {prompt}"',
        'command = "opencode run -m {model} {resume}${HOME} {prompt}"',
    )
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    placeholder = [issue for issue in issues if "placeholder" in issue]
    assert len(placeholder) == 2
    assert any("{resume}" in issue for issue in placeholder)
    assert any("{HOME}" in issue for issue in placeholder)


def _codex_config(command: str) -> str:
    """
    @brief      A minimal config with codex as the default executor.
    @param[in]  command The [executor.codex] command template to test.
    @return     The TOML text.
    """
    return f"""
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../runtime-project"

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
    """
    base = """
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../runtime-project"

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
    """
    base = """
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../runtime-project"

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
    """
    text = MINIMAL_VALID + """
[container.runtime_env]
HTTPS_PROXY = "http://example.invalid:3128"
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert any("runtime_env.HTTPS_PROXY is managed by ADORE" in issue for issue in issues)


def test_workflow_defaults_are_valid_and_documented(tmp_path: Path) -> None:
    """
    @brief   An absent [workflow] section is valid and yields the documented
             defaults: feature runs, the bug/fix/change label map, and the
             quick label.
    """
    config = load_config(_write_config(tmp_path, MINIMAL_VALID))
    assert validate_config(config) == []
    assert config.workflow.default_kind == "feature"
    assert config.workflow.kind_labels == {"bug": "fix", "fix": "fix",
                                           "change": "change"}
    assert config.workflow.quick_label == "agent-quick"
    assert config.workflow.aegis_python == "python"
    assert config.workflow.stage_timeout_overrides == {}
    assert config.recovery.max_stage_failures == 3
    assert config.recovery.max_transient_retries == 3
    assert config.recovery.retry_backoff_seconds == [5, 30, 120]


def test_workflow_rejects_kinds_aegis_does_not_conduct(tmp_path: Path) -> None:
    """
    @brief   Only feature/fix/change may be started by ADORE. An unknown kind
             and the interactive "adoption" kind are both rejected, in
             default_kind and in the label map.
    """
    issues = validate_config(load_config(_write_config(tmp_path, MINIMAL_VALID + """
[workflow]
default_kind = "refactor"
kind_labels = { bug = "fix", legacy = "adoption", odd = "nonsense", dead = "bug" }
""")))
    assert any("default_kind must be one of" in issue for issue in issues)
    assert any("kind_labels.legacy must name an AEGIS run kind" in issue
               for issue in issues)
    assert any("kind_labels.odd must name an AEGIS run kind" in issue
               for issue in issues)
    assert any("kind_labels.dead must name an AEGIS run kind" in issue
               for issue in issues)

    adoption = validate_config(load_config(_write_config(tmp_path, MINIMAL_VALID + """
[workflow]
default_kind = "adoption"
""")))
    assert any("default_kind must be one of" in issue for issue in adoption)


def test_quick_label_is_only_a_frame_hint(
    tmp_path: Path,
) -> None:
    """
    @brief   The hint stays valid even when framing ultimately selects full;
             ADORE never preselects the path from this label.
    """
    dead = validate_config(load_config(_write_config(tmp_path, MINIMAL_VALID + """
[workflow]
default_kind = "feature"
kind_labels = {}
quick_label = "agent-quick"
""")))
    assert dead == []

    reachable = validate_config(load_config(_write_config(tmp_path, MINIMAL_VALID + """
[workflow]
default_kind = "feature"
kind_labels = { bug = "fix" }
quick_label = "agent-quick"
""")))
    assert reachable == []

    disabled = validate_config(load_config(_write_config(tmp_path, MINIMAL_VALID + """
[workflow]
kind_labels = {}
quick_label = ""
""")))
    assert disabled == []


def test_stage_timeout_overrides_must_name_stages_and_positive_seconds(
    tmp_path: Path,
) -> None:
    """
    @brief   An override key that is not an AEGIS stage, or a non-positive
             value, is rejected rather than silently ignored.
    """
    issues = validate_config(load_config(_write_config(tmp_path, MINIMAL_VALID + """
[workflow.stage_timeout_overrides]
build = 5400
publication = 900
validate = 0
design = "long"
""")))
    assert any("stage_timeout_overrides.publication is not an AEGIS stage" in i
               for i in issues)
    assert any("stage_timeout_overrides.validate must be a positive" in i
               for i in issues)
    assert any("stage_timeout_overrides.design must be a positive" in i
               for i in issues)
    assert not any("stage_timeout_overrides.build" in i for i in issues)


def test_recovery_and_approval_settings_fail_closed(tmp_path: Path) -> None:
    """@brief Retry limits, backoff and approval identity are validated."""
    text = MINIMAL_VALID.replace(
        'reviewers = ["dan.pasare"]',
        'reviewers = ["dan.pasare"]\napproval_label = "agent-ready"',
    ) + """
[recovery]
max_stage_failures = 0
max_transient_retries = 0
retry_backoff_seconds = []
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert any("max_stage_failures must be >= 1" in item for item in issues)
    assert any("max_transient_retries must be >= 1" in item for item in issues)
    assert any("retry_backoff_seconds must be a non-empty" in item for item in issues)
    assert any("approval_label must be distinct" in item for item in issues)


def test_executor_cannot_receive_forge_credentials(tmp_path: Path) -> None:
    """@brief Executor env allowlists reject host forge credential names."""
    text = MINIMAL_VALID + """
[executor]
env_keys = ["OPENAI_API_KEY", "GITHUB_TOKEN", "GITLAB_TOKEN"]
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert any("must not expose forge credentials" in item for item in issues)


# END OF FILE


@pytest.mark.parametrize("cap", ["0", "0.0", "6.5", "-1", "nan", "inf", "true", '\"free\"'])
def test_cost_cap_zero_is_explicit_opt_out_and_invalid_inputs_fail_closed(tmp_path, cap):
    """@brief Only finite nonnegative numeric cost caps pass configuration validation."""
    text = MINIMAL_VALID + "\n[budgets]\nmax_cost_usd = " + cap + "\n"
    cfg = load_config(_write_config(tmp_path, text))
    issues = validate_config(cfg)
    if cap in ("0", "0.0", "6.5"):
        assert issues == []
    else:
        assert any("max_cost_usd" in issue for issue in issues)
