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

from adore.config import Config, egress_policy, load_config, validate_config
from adore.pi_providers import secret_names
import pytest

# CONSTANTS

MINIMAL_VALID = """
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../runtime-project"

[executor]
provider = "openai"
model = "gpt-5.4-fast"

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


@pytest.mark.parametrize(("addition", "key"), [
    ('[executor.opencode]\ncommand = "opencode run {prompt}"\nmodel = "m"\n',
     "[executor] unknown key 'opencode'"),
    ('[executor.codex]\ncommand = "codex exec {prompt}"\nmodel = "m"\n',
     "[executor] unknown key 'codex'"),
    ('[executor.qwen]\ncommand = "qwen -p {prompt}"\nmodel = "m"\n',
     "[executor] unknown key 'qwen'"),
    ('[executor.pi]\ncommand = "pi -p {prompt}"\nmodel = "m"\n',
     "[executor] unknown key 'pi'"),
    ('[labels.executor]\nprefix = "agent-exec:"\n', "[labels] unknown key 'executor'"),
])
def test_removed_agent_tables_are_refused_with_the_fix(tmp_path, addition, key) -> None:
    """@brief A table of a removed coding agent is refused, naming the key and the fix."""
    issues = validate_config(load_config(_write_config(tmp_path, MINIMAL_VALID + addition)))
    assert f"{key}: remove it from config.toml" in issues


@pytest.mark.parametrize("line", ['default = "codex"', 'default = "opencode"',
                                  'default = "pi"', "stage_host_auth = true"])
def test_removed_agent_keys_are_refused_with_the_fix(tmp_path, line) -> None:
    """@brief The agent choice and host sign-in staging keys are refused, naming the key."""
    text = MINIMAL_VALID.replace("[executor]\n", f"[executor]\n{line}\n")
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    name = line.split(" ")[0]
    assert f"[executor] unknown key {name!r}: remove it from config.toml" in issues


@pytest.mark.parametrize(("table", "name"), [
    ("[container.runtime_env]", "OPENCODE_CONFIG_CONTENT"),
    ("[container.runtime_env]", "CODEX_HOME"),
    ("[local.environment]", "QWEN_CODE_UNATTENDED_RETRY"),
])
def test_removed_agent_environment_is_refused_with_the_fix(tmp_path, table, name) -> None:
    """@brief An environment variable of a removed coding agent is refused, naming it."""
    text = MINIMAL_VALID + f'\n{table}\n{name} = "x"\n'
    section = table.strip("[]")
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert (f"[{section.split('.')[0]}] {section.split('.')[1]}.{name} configures a "
            "removed coding agent: remove it from config.toml") in issues


def test_pi_is_the_only_executor_and_needs_only_a_provider_and_model(tmp_path: Path) -> None:
    """@brief [executor] provider and model are valid; the Pi launch template is the default."""
    config = load_config(_write_config(tmp_path, MINIMAL_VALID))
    assert validate_config(config) == []
    assert (config.executor.provider, config.executor.model) == ("openai", "gpt-5.4-fast")
    assert config.executor.env_keys == []
    assert config.executor.command == "pi -p --mode json --model {model} {prompt}"


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
        MINIMAL_VALID.replace("[executor]\n", '[executor]\nquestions_file = "ASK.md"\n')
        + '\n[state]\nstore_root = ".custom"\n'
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

[executor]
model = "m"

[delivery]
reviewers = ["r"]
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert any("[platform] kind" in issue for issue in issues)
    assert any("[platform] repo" in issue for issue in issues)
    assert any("[state] unknown key 'channel': remove it from config.toml" in issue
               for issue in issues)
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


def test_validation_requires_a_model_and_prompt_placeholder(tmp_path: Path) -> None:
    """
    @brief   Pi needs a model, and a command template must carry {prompt}.
    """
    text = """
[platform]
repo = "g/p"

[executor]
command = "pi -p --model {model}"

[delivery]
reviewers = ["r"]
"""
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    assert "[executor] model is required" in issues
    assert "[executor] command must contain a {prompt} placeholder" in issues


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
    assert config.container.egress.allowlist == []
    assert config.executor.internet is False
    assert config.executor.web.search == "exa"
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
        "[executor]\n",
        '[executor]\ncommand = "pi -p --auto --model {model} {prompt}"\n',
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
             until the stage budget is spent, pointing at nothing. No executor
             supplies {resume} any more, and a shell `${HOME}` fails the same
             way. Both are caught at setup instead.
    """
    text = MINIMAL_VALID.replace(
        "[executor]\n",
        '[executor]\ncommand = "pi -p --model {model} {resume}${HOME} {prompt}"\n',
    )
    issues = validate_config(load_config(_write_config(tmp_path, text)))
    placeholder = [issue for issue in issues if "placeholder" in issue]
    assert len(placeholder) == 2
    assert any("{resume}" in issue for issue in placeholder)
    assert any("{HOME}" in issue for issue in placeholder)


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

[executor]
provider = "openai"
model = "gpt-5.4-fast"

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


def _with_executor(text: str) -> str:
    """
    @brief      MINIMAL_VALID with extra lines in its [executor] table.
    @param[in]  text TOML lines for [executor] (a following table may come after them).
    @return     The configuration text.
    """
    return MINIMAL_VALID.replace('model = "gpt-5.4-fast"\n', 'model = "gpt-5.4-fast"\n' + text)


def _with_provider(provider: str, model: str, extra: str = "") -> str:
    """
    @brief      MINIMAL_VALID with another provider and model.
    @param[in]  provider `[executor] provider`.
    @param[in]  model `[executor] model`.
    @param[in]  extra TOML appended after the [executor] table.
    @return     The configuration text.
    """
    return MINIMAL_VALID.replace(
        'provider = "openai"\nmodel = "gpt-5.4-fast"\n',
        f'provider = "{provider}"\nmodel = "{model}"\n{extra}')


def test_internet_defaults_off_with_exa_search(tmp_path: Path) -> None:
    """
    @brief   Without the keys internet access is off and search is Exa;
             every search choice loads unchanged with internet on.
    """
    defaulted = load_config(_write_config(tmp_path, MINIMAL_VALID))
    assert defaulted.executor.internet is False
    assert defaulted.executor.web.search == "exa"
    assert validate_config(defaulted) == []
    for search in ("exa", "brave", "tavily", "none"):
        config = load_config(_write_config(tmp_path, _with_executor(
            f'internet = true\n\n[executor.web]\nsearch = "{search}"\n')))
        assert config.executor.internet is True
        assert config.executor.web.search == search
        assert validate_config(config) == []


def test_internet_and_search_values_are_validated(tmp_path: Path) -> None:
    """
    @brief   A non-boolean switch and an unknown search provider are refused by name.
    """
    config = load_config(_write_config(tmp_path, _with_executor(
        'internet = "yes"\n\n[executor.web]\nsearch = "google"\nextra = 1\n')))
    issues = validate_config(config)
    assert any(issue.startswith("[executor] internet must be true or false") for issue in issues)
    assert any(issue.startswith("[executor.web] search must be") for issue in issues)
    assert any("[executor.web] unknown key 'extra'" in issue for issue in issues)


def test_container_egress_mode_is_refused_naming_the_switch(tmp_path: Path) -> None:
    """
    @brief   The removed [container.egress] mode is refused and points at
             [executor] internet; the remaining egress settings validate.
    """
    old = load_config(_write_config(tmp_path, MINIMAL_VALID + """
[container.egress]
mode = "open"
"""))
    issues = validate_config(old)
    assert any("[container.egress] unknown key 'mode'" in issue
               and "[executor] internet" in issue for issue in issues)
    current = load_config(_write_config(tmp_path, MINIMAL_VALID + """
[container.egress]
allowlist = ["gitlab.example.com", "*.pythonhosted.org"]
no_proxy = ["localhost", "127.0.0.1", "::1", "*.internal.example"]
proxy_image = "adore-egress-proxy:1.0.0"
proxy_port = 3128
network_prefix = "adore-egress"
"""))
    assert current.container.egress.allowlist == ["gitlab.example.com", "*.pythonhosted.org"]
    assert validate_config(current) == []


def test_container_egress_rejects_bad_allowlist_entries(tmp_path: Path) -> None:
    """
    @brief   The extra allowlist fails closed on unsafe host patterns; an
             empty one is the default.
    """
    invalid = load_config(_write_config(tmp_path, MINIMAL_VALID + """
[container.egress]
allowlist = ["https://api.openai.com", "gitlab.example.com/path", "bad host", "ok.com;rm"]
"""))
    issues = validate_config(invalid)
    assert sum("allowlist entries" in issue for issue in issues) == 4


def test_egress_policy_off_admits_only_the_provider_hosts(tmp_path: Path) -> None:
    """
    @brief   Internet off derives allowlist-proxy egress with the provider's
             hosts plus the configured extra hosts; on derives open egress.
    """
    off = load_config(_write_config(tmp_path, MINIMAL_VALID + """
[container.egress]
allowlist = ["pypi.org"]
"""))
    policy = egress_policy(off)
    assert policy.mode == "allowlist-proxy"
    assert policy.allowlist == ["api.openai.com", "pypi.org"]
    assert policy.proxy_image == off.container.egress.proxy_image
    assert policy.no_proxy == off.container.egress.no_proxy

    anthropic = load_config(_write_config(
        tmp_path, _with_provider("anthropic", "claude-sonnet-4-5")))
    assert egress_policy(anthropic).allowlist == ["api.anthropic.com"]
    chatgpt = load_config(_write_config(tmp_path, _with_provider("chatgpt", "gpt-5.6-luna")))
    assert egress_policy(chatgpt).allowlist == ["api.openai.com"]
    custom = load_config(_write_config(tmp_path, _with_provider(
        "custom", "qwen3-coder",
        '\n[executor.endpoint]\nbase_url = "http://192.168.1.20:1234/v1"\n')))
    assert egress_policy(custom).allowlist == ["192.168.1.20"]

    on = load_config(_write_config(tmp_path, _with_executor("internet = true\n")))
    opened = egress_policy(on)
    assert opened.mode == "open"
    assert opened.allowlist == []


def test_search_key_reaches_only_an_internet_on_run(tmp_path: Path) -> None:
    """
    @brief   BRAVE_API_KEY / TAVILY_API_KEY are launch secrets only with
             internet on and that search provider.
    """
    def names(text: str) -> list[str]:
        return secret_names(load_config(_write_config(tmp_path, _with_executor(text))).executor)

    assert "BRAVE_API_KEY" in names('internet = true\n\n[executor.web]\nsearch = "brave"\n')
    assert "TAVILY_API_KEY" in names('internet = true\n\n[executor.web]\nsearch = "tavily"\n')
    off = names('internet = false\n\n[executor.web]\nsearch = "brave"\n')
    exa = names("internet = true\n")
    for listed in (off, exa):
        assert "BRAVE_API_KEY" not in listed and "TAVILY_API_KEY" not in listed
    assert "OPENAI_API_KEY" in exa
    brave = load_config(_write_config(tmp_path, _with_executor(
        'internet = true\n\n[executor.web]\nsearch = "brave"\n'))).executor
    # Pi installed on the server loads no web tools, so it never gets the key.
    assert "BRAVE_API_KEY" not in secret_names(brave, "local")
    assert "BRAVE_API_KEY" in secret_names(brave, "container")


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


def test_stage_timeout_overrides_accept_five_stages_and_refuse_deliver(
    tmp_path: Path,
) -> None:
    """
    @brief   AEGIS 0.15.0 conducts five stages; deliver is no longer one.
    @details Validate closes the task, so an override for deliver bounds
             nothing and is reported like any other unknown stage.
    """
    accepted = validate_config(load_config(_write_config(tmp_path, MINIMAL_VALID + """
[workflow.stage_timeout_overrides]
frame = 600
specify = 600
design = 600
build = 5400
validate = 3600
""")))
    assert not any("stage_timeout_overrides" in i for i in accepted)
    refused = validate_config(load_config(_write_config(tmp_path, MINIMAL_VALID + """
[workflow.stage_timeout_overrides]
deliver = 900
""")))
    message = next(i for i in refused if "stage_timeout_overrides.deliver" in i)
    assert "is not an AEGIS stage (frame, specify, design, build, validate)" in message


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
    text = MINIMAL_VALID.replace(
        "[executor]\n",
        '[executor]\nenv_keys = ["OPENAI_API_KEY", "GITHUB_TOKEN", "GITLAB_TOKEN"]\n')
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
