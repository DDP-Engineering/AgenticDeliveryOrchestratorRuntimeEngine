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
@file wizard.py
@brief The `adore init` assisted-configuration wizard (Assisted_Config_And_
       Profiles_Plan, task 3).
@details Detection-first, every prompt explicit (description + example +
         default + validation, with friendly re-prompting). Walks the plan's
         Phase A-I flow - environment/prerequisites, project identity, platform
         & repo, local clone, branch conventions, runtime & executor, delivery,
         budgets/policy - then writes a MINIMAL, valid `config.toml` into a
         runtime-project profile and validates it (never saves an invalid one).
         Fully injectable: the prompt reader (`Asker`), the output sink, the
         command runner (for `doctor` probes) and the OS key are all
         parameters, so the whole flow is unit-tested offline with a scripted
         asker + a fake runner. A non-interactive `--answers FILE` path reuses
         the same field keys (decision D7).
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import math
from pathlib import Path
import re
import tempfile

from adore import doctor
from adore.branding import (
    DEFAULT_STATE_ROOT,
    EXECUTOR_BASE_IMAGE,
    PRODUCT_ACRONYM,
    PRODUCT_SLUG,
)
from adore.config import Config, load_config, validate_config
from adore.pi_providers import (
    CHATGPT,
    CUSTOM,
    DEFAULT_ENDPOINT_API,
    ENDPOINT_APIS,
    MODEL_ID_RE,
    catalog,
    credential_variable,
    provider_ids,
    valid_endpoint_url,
)
from adore.profiles import Profile, ProfileStore
from adore.util import CommandRunner, run_command

# CONSTANTS

_LICENSE_LINES = (
    "# Copyright (c) 2026 DDP Engineering",
    "# This software is licensed under the PolyForm Noncommercial License 1.0.0.",
    "# Commercial use requires a separate commercial license.",
    "# See the LICENSE.txt file for full license details.",
    "# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0",
)
_DEFAULT_PROVIDER = "openai"
_DEFAULT_MODEL = "gpt-5.5"
_RECOMMENDED_BUDGETS = {
    "max_iterations": 20,
    "max_wall_clock_seconds": 5400,
    "max_cost_usd": 5.0,
    "max_files_touched": 120,
}

# DATA MODELS / TYPEDEFINITIONS


class WizardError(RuntimeError):
    """
    @brief Raised when a required setup answer or assembled config is invalid.
    """

    def __init__(self, message: str, *, field: str = "config"):
        """@brief Keep setup findings addressable without exposing answer values."""
        super().__init__(message)
        self.field = field


@dataclass
class WizardSetup:
    """@brief Validated local setup candidate, without publication or host probes."""

    name: str
    document: str
    metadata: dict[str, object]


@dataclass
class FieldSpec:
    """
    @brief   One explicit prompt: label, description, example, default,
             optional fixed choices, and a validator returning an error or None.
    """

    key: str
    prompt: str
    description: str = ""
    example: str = ""
    default: str | None = None
    choices: Sequence[str] | None = None
    validate: Callable[[str], str | None] | None = None


class ConsoleAsker:
    """
    @brief   Interactive prompt reader over stdin/stdout (the real user).
    @details Renders each FieldSpec (description, example, choices, default) and
             reads one line; empty input means "accept the default".
    """

    interactive = True

    def __init__(
        self,
        input_fn: Callable[[str], str] = input,
        out: Callable[[str], None] = print,
    ) -> None:
        self._input = input_fn
        self._out = out

    def read(self, spec: FieldSpec) -> str | None:
        """
        @brief      Render a field and read one raw line.
        @param[in]  spec The field to prompt.
        @return     The stripped input, or None when the user just pressed Enter.
        """
        self._out(f"\n{spec.prompt}")
        if spec.description:
            self._out(f"  {spec.description}")
        if spec.example:
            self._out(f"  example: {spec.example}")
        if spec.choices:
            self._out("  choices:")
            for index, choice in enumerate(spec.choices, start=1):
                marker = " [default]" if choice == spec.default else ""
                self._out(f"    {index}. {choice}{marker}")
        if spec.default is not None:
            self._out(f"  [default: {spec.default}]")
        raw = self._input("> ").strip()
        return raw or None


class ScriptedAsker:
    """
    @brief   Non-interactive reader over a mapping of field-key -> answer(s).
    @details Backs both tests and `--answers FILE`. A value may be a single
             string or a queue (list) consumed across re-prompts. `interactive`
             controls whether a validation failure re-prompts (tests) or fails
             fast (an answers file, decision D7).
    """

    def __init__(
        self,
        answers: dict[str, object],
        *,
        interactive: bool = True,
    ) -> None:
        self.answers: dict[str, list[str]] = {
            key: [str(item) for item in value]
            if isinstance(value, list | tuple)
            else [str(value)]
            for key, value in answers.items()
        }
        self.interactive = interactive
        self.reads: list[str] = []

    def read(self, spec: FieldSpec) -> str | None:
        """
        @brief      Return the next scripted answer for a field, or None.
        @param[in]  spec The field being asked.
        @return     The answer string, or None to fall back to the default.
        """
        self.reads.append(spec.key)
        queue = self.answers.get(spec.key)
        if not queue:
            return None
        return queue.pop(0)


# HELPER FUNCTIONS - validators


def _require(value: str) -> str | None:
    """@brief Non-empty check."""
    return None if value.strip() else "a value is required"


def _valid_regex(value: str) -> str | None:
    """@brief The value must compile as a regular expression."""
    try:
        re.compile(value)
    except re.error as exc:
        return f"not a valid regex: {exc}"
    return None


def _existing_dir(value: str) -> str | None:
    """@brief The path must be an existing directory."""
    if not value.strip():
        return "a path is required"
    if not Path(value).expanduser().is_dir():
        return f"directory not found: {value}"
    return None


def _runtime_ok(value: str) -> str | None:
    """@brief Last token must be docker/podman (matches config validation)."""
    tokens = value.split()
    if not tokens or tokens[-1] not in ("docker", "podman"):
        return 'must end in "docker" or "podman" (optionally wrapped, e.g. "wsl -d D -- docker")'
    return None


def _positive_int(value: str) -> str | None:
    """@brief A positive integer."""
    try:
        if int(value) <= 0:
            return "must be a positive whole number"
    except ValueError:
        return "must be a whole number"
    return None


def _nonnegative_number(value: str) -> str | None:
    """@brief A finite nonnegative number; zero explicitly disables the cost cap."""
    try:
        number = float(value)
        if not math.isfinite(number) or number < 0:
            return "must be a finite nonnegative number (0 disables the cost cap)"
    except ValueError:
        return "must be a number"
    return None


def _nonnegative_int_list(value: str) -> str | None:
    """@brief Validate a nonempty comma-separated nonnegative integer list."""
    parts = [item.strip() for item in value.split(",")]
    if not parts or any(not item or not item.isdigit() for item in parts):
        return "use comma-separated nonnegative whole seconds, e.g. 5,30,120"
    return None


def _slugify(name: str) -> str:
    """
    @brief      Derive a config slug from a display name (matches config rules).
    @param[in]  name Display name.
    @return     A lowercase [a-z][a-z0-9-]* slug (fallback "adore").
    """
    slug = re.sub(r"[^a-z0-9-]", "", name.lower())
    return slug if re.match(r"^[a-z][a-z0-9-]*$", slug) else PRODUCT_SLUG


def _resolve_choice(spec: FieldSpec, value: str) -> str:
    """
    @brief      Resolve numbered choice input to the configured choice value.
    @param[in]  spec The field whose choices are being resolved.
    @param[in]  value Raw answer after default handling.
    @return     The matching configured choice, or the original answer.
    """
    if not spec.choices:
        return value
    stripped = value.strip()
    if not stripped.isdigit():
        return value
    index = int(stripped)
    if 1 <= index <= len(spec.choices):
        return spec.choices[index - 1]
    return value


def ask(spec: FieldSpec, asker: ConsoleAsker | ScriptedAsker, out: Callable[[str], None]) -> str:
    """
    @brief      Prompt one field: read, apply default, validate, re-prompt.
    @details    An empty read falls back to the default. `choices` accepts the
                exact choice text or a 1-based number. On a validation error the
                interactive asker re-prompts; a non-interactive asker fails fast
                with WizardError (D7).
    @param[in]  spec The field to collect.
    @param[in]  asker The prompt reader (Console/Scripted).
    @param[in]  out Output sink for error lines.
    @return     The validated string value.
    @exception  WizardError When a non-interactive answer is invalid/missing.
    """
    while True:
        raw = asker.read(spec)
        value = raw if raw is not None else (spec.default or "")
        value = _resolve_choice(spec, value)
        error: str | None = None
        if spec.choices and value not in spec.choices:
            error = f"choose one of: {', '.join(spec.choices)}"
        elif spec.validate is not None:
            error = spec.validate(value)
        if error is None:
            return value
        if not asker.interactive:
            raise WizardError(f"{spec.key}: {error} (got {value!r})", field=spec.key)
        out(f"  ! {error}")


# HELPER FUNCTIONS - TOML emission


def _toml_string(value: str) -> str:
    """
    @brief      Encode a string as TOML, preferring literal quotes.
    @details    Literal single-quoted strings do no escaping, which is ideal
                for regexes and Windows paths (backslashes); a value that
                contains a single quote or newline falls back to a basic string.
    @param[in]  value The string.
    @return     A TOML string token.
    """
    if "'" not in value and "\n" not in value:
        return f"'{value}'"
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_value(value: object) -> str:
    """
    @brief      Encode a scalar / list / string map as a TOML value.
    @details    Maps render as inline tables, which is what `[workflow]
                kind_labels` needs and keeps the emitted file one table per
                section.
    @param[in]  value bool / int / float / str / list / dict.
    @return     The TOML token.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        items = ", ".join(
            f"{_toml_string(str(key))} = {_toml_value(item)}"
            for key, item in value.items()
        )
        return "{" + items + "}"
    return _toml_string(str(value))


def _emit_config_toml(
    sections: list[tuple[str, dict[str, object]]], profile_name: str, stamp: str
) -> str:
    """
    @brief      Render the minimal profile config.toml (with license header).
    @param[in]  sections Ordered (table-header, key->value) pairs.
    @param[in]  profile_name The profile this config belongs to.
    @param[in]  stamp Human timestamp for the generated-by comment.
    @return     The complete TOML document text.
    """
    lines = list(_LICENSE_LINES)
    lines.append("#")
    lines.append(f"# Generated by `adore init` for profile '{profile_name}' on {stamp}.")
    lines.append(f"# Re-run `adore init --profile {profile_name} --force` to regenerate,")
    lines.append("# or edit by hand (see the ADORE Configuration Reference).")
    lines.append("")
    for header, mapping in sections:
        lines.append(f"[{header}]")
        for key, value in mapping.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# PUBLIC API


def run_wizard(
    store: ProfileStore,
    *,
    asker: ConsoleAsker | ScriptedAsker,
    out: Callable[[str], None] = print,
    runner: CommandRunner = run_command,
    os_key: str | None = None,
    name: str | None = None,
    force: bool = False,
    prepare_only: bool = False,
    pending_clone: bool = False,
) -> Profile | WizardSetup:
    """
    @brief      Run the assisted-config flow and save a validated profile.
    @details    Phases A-I from the plan. Detection is informational (prints
                guidance for missing prerequisites, never blocks); the config
                is assembled MINIMALLY (only the keys a project needs), written
                to a temp file, loaded and validated, and only then committed to
                the profile - an invalid config is never saved.
    @param[in]  store The profile store to write into.
    @param[in]  asker The prompt reader (Console for users, Scripted for tests
                      and --answers).
    @param[in]  out Output sink (defaults to print).
    @param[in]  runner Command runner for doctor probes (injectable).
    @param[in]  os_key Host OS key (defaults to doctor.detect_os()).
    @param[in]  name Profile name (asked when None).
    @param[in]  force Overwrite an existing profile.
    @param[in]  pending_clone Accept a clone path that ADORE creates only at creation.
    @param[in]  prepare_only Return a validated candidate without writes or probes.
    @return     The saved Profile, or WizardSetup when preparation is requested.
    @exception  WizardError On abort, an existing profile without --force, or a
                config that fails validation.
    """
    key = os_key or doctor.detect_os()

    # -- Phase B (name first, so we can guard existence early) --------------------
    if name is None:
        name = ask(FieldSpec(
            "profile_name", "Name this runtime-project profile:",
            "a short, filesystem-safe id you'll pass as --profile <name>",
            "sample-project",
            validate=lambda v: None if re.match(r"^[a-z0-9][a-z0-9._-]{0,63}$", v)
            else "use lowercase letters/digits/._- (start alphanumeric)",
        ), asker, out)
    if store.exists(name) and not force:
        raise WizardError(f"profile {name!r} already exists (use --force to overwrite)")

    description = ask(FieldSpec(
        "description", "One-line description (optional):",
        "shown in `adore profile list`", "Example service - Python + Terraform",
        default="",
    ), asker, out)
    agent_name = ask(FieldSpec(
        "agent_name", "Bot display name:",
        "names branches/containers via its slug; keep the default unless you have a reason",
        PRODUCT_ACRONYM, default=PRODUCT_ACRONYM,
    ), asker, out)
    slug = _slugify(agent_name)

    # -- Phase C (platform & repository) ------------------------------------------
    kind = ask(FieldSpec(
        "kind", "Is the project on GitLab, GitHub or Gitea?",
        "selects the platform adapter", "gitlab",
        default="gitlab", choices=("gitlab", "github", "gitea"),
    ), asker, out)

    # Phase A guidance is informational and platform-aware; print it now.
    if not prepare_only:
        _report_environment(out, runner, key, kind)

    login = ""
    if kind == "gitea":
        # Gitea is always an instance; tea binds host + token to a named
        # login, so the login name selects the runtime route explicitly.
        login = ask(FieldSpec(
            "login", "tea login name (see `tea logins list`; blank = default):",
            "selects which authenticated Gitea instance/account tea uses",
            "home", default="",
        ), asker, out).strip()
    repo = ask(FieldSpec(
        "repo", "Repository path (group/subgroup/project, NOT a URL):"
        if kind != "gitea" else "Repository path (owner/repo, NOT a URL):",
        "the project's path on the platform",
        "group/subgroup/project" if kind != "gitea" else "owner/repo",
        validate=_require,
    ), asker, out)

    # -- Phase D (local clone & worktree) -----------------------------------------
    repo_path = ask(FieldSpec(
        "repo_path", "Absolute path to the local clone:",
        "ADORE creates per-run worktrees from it and mounts it into the container",
        "D:/projects/sample-project  (Windows)  |  /home/you/sample-project  (Linux)",
        # A web enrollment from a repository URL clones only at creation.
        validate=_require if pending_clone else _existing_dir,
    ), asker, out)
    if not pending_clone and not (Path(repo_path).expanduser() / ".git").exists():
        out("  note: that path has no .git - make sure it is the clone root.")
    worktree_root = ask(FieldSpec(
        "worktree_root", "Worktree root (host dir holding per-run worktrees):",
        "relative to the run, or an absolute path", "worktrees", default="worktrees",
        validate=_require,
    ), asker, out)
    target_branch = ask(FieldSpec(
        "target_branch", "Target/base branch (MRs target this; runs merge it):",
        "usually the integration branch", "develop", default="develop",
        validate=_require,
    ), asker, out)

    # -- Phase E (branch conventions) ---------------------------------------------
    has_rule = ask(FieldSpec(
        "has_push_rule", "Does the repo enforce a branch-name push rule?",
        "some repos reject branches that don't match a pattern (e.g. feature/*)",
        "yes", default="no", choices=("yes", "no"),
    ), asker, out)
    branch_rule = ""
    default_template = "{slug}/{run_id}"
    if has_rule == "yes":
        branch_rule = ask(FieldSpec(
            "branch_rule", "The required branch-name regex:",
            "ADORE checks the branch template against it",
            r"^(feature|bugfix|release|hotfix)/.*$",
            validate=_valid_regex,
        ), asker, out)
        default_template = "feature/{slug}-{iid}"

    def _template_ok(value: str) -> str | None:
        if "{run_id}" not in value and "{iid}" not in value:
            return "must contain {run_id} or {iid} (branches must be unique per ticket)"
        try:
            sample = value.format(slug=slug, run_id="sample-run-1", iid=1)
        except (KeyError, IndexError):
            return "only {slug}, {run_id}, {iid} placeholders are allowed"
        if branch_rule and not re.compile(branch_rule).match(sample):
            return f"renders {sample!r}, which the push rule would REJECT"
        return None

    branch_template = ask(FieldSpec(
        "branch_template", "Run-branch name template:",
        "placeholders: {slug}, {run_id}, {iid}", default_template,
        default=default_template, validate=_template_ok,
    ), asker, out)

    # -- Phase F (runtime & executor) ---------------------------------------------
    execution_backend = ask(FieldSpec(
        "execution_backend", "Execution backend:",
        "container or installed local CLI on the ADORE machine/current account",
        default="container", choices=("container", "local")), asker, out)
    suggested = "docker"
    if not prepare_only and execution_backend == "container":
        runtimes = doctor.detect_runtimes(runner, os_key=key)
        suggested = _suggest_runtime(key, runtimes)
    runtime = "docker" if execution_backend == "local" else ask(FieldSpec(
        "runtime", "Container runtime:",
        "docker/podman, optionally wrapped for Docker/podman inside WSL2",
        'docker  |  podman  |  wsl -d Ubuntu-24.04 -- docker',
        default=suggested, validate=_runtime_ok,
    ), asker, out)
    run_args: list[str] = []
    if runtime.split()[-1] == "podman":
        run_args = ["--userns=keep-id"]
        out("  note: rootless podman -> adding run_args = [\"--userns=keep-id\"].")
    image = EXECUTOR_BASE_IMAGE if execution_backend == "local" else ask(FieldSpec(
        "image", "Executor image name:",
        "base image for executor-only validation, or a runtime-project image",
        f"{EXECUTOR_BASE_IMAGE}  |  adore-executor-project:latest",
        default=EXECUTOR_BASE_IMAGE, validate=_require,
    ), asker, out)
    provider = ask(FieldSpec(
        "provider", "Model provider:",
        'a Pi API-key provider id, "chatgpt" (this server\'s ChatGPT Plus/Pro sign-in) '
        'or "custom" (an OpenAI-compatible endpoint such as LM Studio, Ollama or vLLM)',
        "openai  |  anthropic  |  openrouter  |  custom", default=_DEFAULT_PROVIDER,
        validate=_provider_ok,
    ), asker, out)
    endpoint: dict[str, str] = {}
    if provider == CUSTOM:
        endpoint["base_url"] = ask(FieldSpec(
            "endpoint_base_url", "Endpoint base URL:",
            "the address as seen by Pi (host.docker.internal works only on "
            "Docker Desktop; otherwise use the host's address)",
            "http://192.168.1.20:1234/v1", validate=_endpoint_url_ok,
        ), asker, out)
        endpoint["api"] = ask(FieldSpec(
            "endpoint_api", "Endpoint API type:", "the Pi API type the server speaks",
            default=DEFAULT_ENDPOINT_API, choices=ENDPOINT_APIS,
        ), asker, out)
    chatgpt_models = catalog()["chatgpt_models"] if provider == CHATGPT else []
    model = ask(FieldSpec(
        "model", "Model id:",
        ("a model a ChatGPT subscription serves: " + ", ".join(chatgpt_models))
        if chatgpt_models else
        "the model within the provider (Pi's list or any id the provider accepts)",
        chatgpt_models[0] if chatgpt_models else _DEFAULT_MODEL,
        default=(chatgpt_models[0] if chatgpt_models else
                 _DEFAULT_MODEL if provider == _DEFAULT_PROVIDER else None),
        validate=_model_ok,
    ), asker, out)
    if isinstance(asker, ScriptedAsker):
        retired = {"executor_command", "local_home", "local_cgroup_root"} & asker.answers.keys()
        if retired:
            raise WizardError(f"remove unsupported setup answers: {', '.join(sorted(retired))}")
        if asker.answers.get("auth_mode", ["api-key"]) != ["api-key"]:
            raise WizardError("auth_mode: only api-key is supported; remove personal sign-in")
        if asker.answers.get("local_account", ["current"]) != ["current"]:
            raise WizardError("local_account must be current")
    local_settings = {}
    if execution_backend == "local":
        from adore.local_process import native_context

        context = native_context()
        out(f"Local execution machine: {context['machine']}; account: {context['account']}. "
            "You independently choose/install/prep project tools, versions, SDKs "
            "and libraries there. "
            "A worktree is not a host sandbox; use a dedicated account without forge credentials.")
        out("Install and verify managed Pi as this account with 'adore pi install' "
            "and 'adore pi verify'.")
        local_settings = {"account": "current", "path": ask(FieldSpec(
            "local_path", "Project tools PATH:", "Leave empty to use the server PATH.",
            default=""), asker, out)}

    # -- Phase F2 (workflow labels) -----------------------------------------------
    ready_label = ask(FieldSpec(
        "ready_label", "Label that makes a ticket eligible for ADORE:",
        "humans apply it; ADORE removes it when it starts working",
        "agent-ready", default="agent-ready", validate=_require,
    ), asker, out)
    fix_label = ask(FieldSpec(
        "fix_label", "Label marking a ticket as a FIX (bug) run:",
        "maps the created AEGIS task type to fix; anything else is feature",
        "bug", default="bug", validate=_require,
    ), asker, out)
    change_label = ask(FieldSpec(
        "change_label", "Label marking a ticket as a CHANGE run:",
        "maps the created AEGIS task type to change",
        "change", default="change", validate=_require,
    ), asker, out)
    quick_label = ask(FieldSpec(
        "quick_label", "Label hinting that frame should consider QUICK:",
        "a hint only; the frame executor applies AEGIS eligibility and records "
        "the full/quick justification. Empty disables the hint.",
        "agent-quick", default="agent-quick",
    ), asker, out)

    # -- Phase G (delivery) -------------------------------------------------------
    reviewers_raw = ask(FieldSpec(
        "reviewers", "Reviewer username(s) for the draft MR (comma-separated, blank = none):",
        "optional; the MR is always a DRAFT and ADORE never merges",
        "reviewer.one, reviewer.two", default="",
    ), asker, out)
    reviewers = [part.strip() for part in reviewers_raw.split(",") if part.strip()]
    approval_label = ask(FieldSpec(
        "approval_label", "Fresh human approval label:",
        "ADORE removes it before presenting evidence and accepts only a re-add",
        "agent-approved", default="agent-approved", validate=_require,
    ), asker, out)

    # -- Phase H (budgets & policy) -----------------------------------------------
    budgets_choice = ask(FieldSpec(
        "budgets_choice", "Budgets: recommended supervised, or customize?",
        "recommended = 20 launches / 90 active min / $5 / 120 files",
        "recommended", default="recommended", choices=("recommended", "custom"),
    ), asker, out)
    budgets = dict(_RECOMMENDED_BUDGETS)
    if budgets_choice == "custom":
        budgets["max_iterations"] = int(ask(FieldSpec(
            "max_iterations", "Max executor launches per run:",
            "20 recommended; customize for the task", "20",
            default="20", validate=_positive_int), asker, out))
        budgets["max_wall_clock_seconds"] = int(ask(FieldSpec(
            "max_wall_clock_seconds", "Max active wall-clock per run (seconds):",
            "cumulative; excludes waiting and retains work on retry/resume", "5400", default="5400",
            validate=_positive_int), asker, out))
        budgets["max_cost_usd"] = float(ask(FieldSpec(
            "max_cost_usd", "Max reported model cost per run (USD):",
            "0 disables the dollar cap for subscription/local execution", "5.0",
            default="5.0", validate=_nonnegative_number), asker, out))
        budgets["max_files_touched"] = int(ask(FieldSpec(
            "max_files_touched", "Max files a run may change:", "", "120",
            default="120", validate=_positive_int), asker, out))
    max_stage_failures = int(ask(FieldSpec(
        "max_stage_failures", "Failed attempts allowed per AEGIS stage:",
        "the final attempt aborts; 3 means there is no fourth launch",
        "3", default="3", validate=_positive_int,
    ), asker, out))
    max_transient_retries = int(ask(FieldSpec(
        "max_transient_retries", "Transient infrastructure attempts:",
        "container, fetch and forge transport; does not consume stage attempts",
        "3", default="3", validate=_positive_int,
    ), asker, out))
    retry_backoff_raw = ask(FieldSpec(
        "retry_backoff_seconds", "Transient/outbox backoff seconds:",
        "comma-separated, capped at the last value", "5,30,120",
        default="5,30,120", validate=_nonnegative_int_list,
    ), asker, out)
    retry_backoff_seconds = [
        int(item.strip()) for item in retry_backoff_raw.split(",")
    ]
    polling_mode = ask(FieldSpec(
        "polling_mode", "Run mode:",
        "once = single pass (cron/Task Scheduler); loop = long-running service",
        "once", default="once", choices=("once", "loop"),
    ), asker, out)
    state_location = ask(FieldSpec(
        "state_location", "Where should this project's ADORE state live?",
        "profile = under the profile (recommended, isolated); project = a "
        f"{DEFAULT_STATE_ROOT} beside the clone",
        "profile", default="profile", choices=("profile", "project"),
    ), asker, out)
    store_root = (
        str(store.default_store_root(name)) if state_location == "profile"
        else str(Path(repo_path).expanduser() / DEFAULT_STATE_ROOT)
    )

    # -- assemble the minimal config ----------------------------------------------
    sections = _assemble_sections(
        agent_name=agent_name, kind=kind, repo=repo, login=login, store_root=store_root,
        repo_path=repo_path, worktree_root=worktree_root, branch_template=branch_template,
        branch_rule=branch_rule, runtime=runtime, run_args=run_args, image=image,
        provider=provider, model=model, endpoint=endpoint,
        target_branch=target_branch, reviewers=reviewers,
        approval_label=approval_label,
        budgets=budgets, budgets_choice=budgets_choice, polling_mode=polling_mode,
        max_stage_failures=max_stage_failures,
        max_transient_retries=max_transient_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        ready_label=ready_label, fix_label=fix_label, change_label=change_label,
        quick_label=quick_label,
    )
    if execution_backend == "local":
        sections = [(name, values) for name, values in sections if name != "container"]
        sections.extend([("execution", {"backend": "local"}), ("local", local_settings)])

    # -- Phase I (summary, validate, save) ----------------------------------------
    _print_summary(out, name, sections)
    confirm = ask(FieldSpec(
        "confirm", "Write this profile?", "", "yes",
        default="yes", choices=("yes", "no"),
    ), asker, out)
    if confirm != "yes":
        raise WizardError("aborted by user; nothing written")

    stamp = store._now()
    document = _emit_config_toml(sections, name, stamp)
    config = _validate_or_raise(document, out)

    if prepare_only:
        return WizardSetup(name, document, {
            "description": description, "platform": kind, "repo": repo,
            "runtime": "local" if execution_backend == "local" else runtime, "host_os": key,
            "config_path": str(store.config_path(name)), "store_root": store_root,
        })

    _report_aegis(out, runner, repo_path, key, config.workflow.aegis_python)

    config_path = store.config_path(name)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(document, encoding="utf-8")
    profile = store.create(
        name, overwrite=force, description=description, platform=kind,
        repo=repo, runtime="local" if execution_backend == "local" else runtime,
        host_os=key, config_path=str(config_path),
        store_root=store_root,
    )
    if execution_backend == "container":
        _print_next_steps(out, name, kind, provider, runtime, image)
    return profile


# LOCAL HELPERS


def _suggest_runtime(os_key: str, runtimes: doctor.RuntimeDetection) -> str:
    """
    @brief      Best-guess default runtime string from detection.
    @param[in]  os_key Host OS key.
    @param[in]  runtimes Detected runtimes.
    @return     A runtime string (docker/podman, WSL-wrapped on Windows).
    """
    if os_key == "windows" and runtimes.wsl_distros:
        distro = runtimes.wsl_distros[0]
        tool = "docker" if runtimes.docker.present or not runtimes.podman.present else "podman"
        return f"wsl -d {distro} -- {tool}"
    if runtimes.docker.present:
        return "docker"
    if runtimes.podman.present:
        return "podman"
    return "docker"


def _report_aegis(
    out: Callable[[str], None],
    runner: CommandRunner,
    repo_path: str,
    os_key: str,
    aegis_python: str,
) -> None:
    """
    @brief      Report whether the target clone carries usable AEGIS.
    @details    An absent payload is direct-workflow information. Present but
                unusable AEGIS prints CHECK with its diagnostic and supported
                contract, without preventing a valid profile from being saved.
                The report never installs a payload or changes web readiness.
    @param[in]  out Output sink.
    @param[in]  runner Command runner for the probe.
    @param[in]  repo_path Local clone to probe.
    @param[in]  os_key Host OS key (selects guidance wording).
    @param[in]  aegis_python Interpreter from the validated candidate configuration.
    """
    status = doctor.detect_aegis(repo_path, runner, aegis_python=aegis_python)
    if not status.wrapper_present:
        out(f"  [INFO] {status.detail}")
    else:
        out(f"  [{'OK' if status.ok else 'CHECK'}] AEGIS payload"
            + (f" (schema {status.schema_version})" if status.ok else ""))
        if not status.ok:
            if status.detail:
                out(f"        {status.detail}")
            out("        " + doctor.guidance_for(doctor.AEGIS, os_key))
    # Host git push access is probed here because this is where the clone path
    # is known. It is the one prerequisite that otherwise fails at the very end
    # of a run, discarding a human approval (see doctor.detect_push_access).
    ignore = doctor.detect_gitignore(repo_path)
    out(f"  [{'OK' if ignore.present else 'CHECK'}] target .gitignore")
    if not ignore.present:
        out(f"        {ignore.detail}")
        out("        " + doctor.guidance_for(doctor.GITIGNORE, os_key))
    push = doctor.detect_push_access(repo_path, runner)
    out(f"  [{'OK' if push.version else 'CHECK'}] host git push access"
        + (f" ({push.version})" if push.version else ""))
    if push.version:
        return
    if push.detail:
        out(f"        {push.detail}")
    out("        " + doctor.guidance_for(doctor.GIT_PUSH, os_key))


def _report_environment(
    out: Callable[[str], None], runner: CommandRunner, os_key: str, kind: str
) -> None:
    """
    @brief      Print a prerequisite report + guidance for anything missing.
    @details    Informational only (never blocks): the wizard proceeds so a
                user can fix prerequisites in another terminal and continue.
    @param[in]  out Output sink.
    @param[in]  runner Command runner for probes.
    @param[in]  os_key Host OS key.
    @param[in]  kind Platform kind (selects glab/gh/tea).
    """
    out("\n--- Environment check (informational) ---")
    git = doctor.detect_git(runner)
    cli = doctor.detect_platform_cli(kind, runner)
    for status in (git, cli):
        out(f"  [{'OK' if status.present else 'MISSING'}] {status.name}")
        if not status.present:
            out("        " + doctor.guidance_for(status.name, os_key))
    auth = doctor.auth_status(kind, runner)
    out(f"  [{'OK' if auth.authenticated else 'CHECK'}] {auth.cli} auth")
    if not auth.authenticated:
        out("        " + doctor.guidance_for(doctor.auth_component_for_kind(kind), os_key))
    if kind in {"gitlab", "github"}:
        out(f"        ADORE uses {auth.cli}'s active/default authenticated host; "
            "for corporate instances, verify it is the intended host.")
    out("-----------------------------------------")


def _assemble_sections(**a: object) -> list[tuple[str, dict[str, object]]]:
    """
    @brief      Build the ordered, MINIMAL config sections from answers.
    @details    Writes the fields validation requires plus any that differ from
                the dataclass defaults; true defaults are omitted so the file
                stays small (decision D4).
    @param[in]  a Collected answers (see run_wizard).
    @return     Ordered (table-header, key->value) pairs.
    """
    sections: list[tuple[str, dict[str, object]]] = []
    if a["agent_name"] != PRODUCT_ACRONYM:
        sections.append(("agent", {"name": a["agent_name"]}))
    platform: dict[str, object] = {"kind": a["kind"], "repo": a["repo"]}
    if a["login"]:
        platform["login"] = a["login"]
    sections.append(("platform", platform))
    sections.append(("state", {"store_root": a["store_root"]}))

    worktree: dict[str, object] = {"repo_path": a["repo_path"]}
    if a["worktree_root"] != "worktrees":
        worktree["root"] = a["worktree_root"]
    if a["branch_template"] != "{slug}/{run_id}":
        worktree["branch_template"] = a["branch_template"]
    if a["branch_rule"]:
        worktree["branch_rule"] = a["branch_rule"]
    sections.append(("worktree", worktree))

    container: dict[str, object] = {"runtime": a["runtime"], "image": a["image"]}
    if a["run_args"]:
        container["run_args"] = a["run_args"]
    sections.append(("container", container))

    executor: dict[str, object] = {"provider": a["provider"], "model": a["model"]}
    # The provider's key variable always reaches Pi; these are additional names.
    executor["env_keys"] = []
    sections.append(("executor", executor))
    if a["endpoint"]:
        sections.append(("executor.endpoint", dict(a["endpoint"])))  # type: ignore[arg-type]

    delivery: dict[str, object] = {
        "reviewers": a["reviewers"],
        "approval_label": a["approval_label"],
    }
    if a["target_branch"] != "develop":
        delivery["target_branch"] = a["target_branch"]
    sections.append(("delivery", delivery))

    sections.append(("recovery", {
        "max_stage_failures": a["max_stage_failures"],
        "max_transient_retries": a["max_transient_retries"],
        "retry_backoff_seconds": a["retry_backoff_seconds"],
    }))

    if a["budgets_choice"] == "custom" or a["budgets"] != _RECOMMENDED_BUDGETS:
        sections.append(("budgets", dict(a["budgets"])))  # type: ignore[arg-type]
    else:
        sections.append(("budgets", dict(_RECOMMENDED_BUDGETS)))

    if a["ready_label"] != "agent-ready":
        sections.append(("labels.lifecycle", {"ready": a["ready_label"]}))

    workflow: dict[str, object] = {}
    kind_labels = {
        str(a["fix_label"]): "fix",
        str(a["change_label"]): "change",
    }
    if kind_labels != {"bug": "fix", "change": "change"}:
        workflow["kind_labels"] = kind_labels
    if a["quick_label"] != "agent-quick":
        workflow["quick_label"] = a["quick_label"]
    if workflow:
        sections.append(("workflow", workflow))

    if a["polling_mode"] != "loop":
        sections.append(("polling", {"mode": a["polling_mode"]}))
    return sections


def _provider_ok(value: str) -> str | None:
    """@brief Accept a Pi API-key provider id, chatgpt or custom."""
    if value in provider_ids():
        return None
    return 'unknown provider: use a Pi API-key provider id, "chatgpt" or "custom"'


def _model_ok(value: str) -> str | None:
    """@brief Accept one model id without spaces, quotes or control characters."""
    return None if MODEL_ID_RE.fullmatch(value) else "enter one model id without spaces"


def _endpoint_url_ok(value: str) -> str | None:
    """@brief Accept an endpoint address by the shared rule (pi_providers)."""
    return None if valid_endpoint_url(value) else "enter an http(s) address such as http://192.168.1.20:1234/v1"


def _validate_or_raise(document: str, out: Callable[[str], None]) -> Config:
    """
    @brief      Load + validate the emitted config; raise on any issue.
    @details    Validates the ACTUAL written document (via a temp file) the same
                way the engine will at startup, so a saved profile is always
                loadable and valid (never save an invalid one).
    @param[in]  document The config.toml text.
    @param[in]  out Output sink for the issue list.
    @return     The loaded, validated candidate configuration.
    @exception  WizardError When validation finds issues.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False,
                                     encoding="utf-8") as handle:
        handle.write(document)
        tmp_path = Path(handle.name)
    try:
        config = load_config(tmp_path)
        issues = validate_config(config)
    finally:
        tmp_path.unlink(missing_ok=True)
    if issues:
        out("\nThe assembled config is invalid (not saved):")
        for issue in issues:
            out(f"  - {issue}")
        raise WizardError(f"config validation failed with {len(issues)} issue(s)")
    return config


def _print_summary(
    out: Callable[[str], None], name: str, sections: list[tuple[str, dict[str, object]]]
) -> None:
    """@brief Print the resolved config for confirmation."""
    out(f"\n=== Profile '{name}' - review ===")
    for header, mapping in sections:
        out(f"[{header}]")
        for key, value in mapping.items():
            out(f"  {key} = {value}")
    out("=================================")


def _print_next_steps(
    out: Callable[[str], None], name: str, kind: str,
    provider: str, runtime: str, image: str,
) -> None:
    """@brief Print OS-agnostic next steps after a successful write."""
    out(f"\nProfile '{name}' created and validated.")
    out("Next steps:")
    variable = credential_variable(provider)
    if variable:
        out(f"  1. Put your provider key ({variable}) in .env beside this profile's "
            f"config.toml (`adore profile path {name}`), or save it in Settings -> "
            "Agent and model.")
    else:
        out("  1. Sign in with ChatGPT once for this server in the web interface: "
            "Settings -> Agent and model -> Sign in with ChatGPT.")
    out(f"  2. Build the executor image ({image}) - see docker/README.md.")
    out(f"  3. Validate:  adore --profile {name} config validate")
    out(f"  4. Dry-run:   adore --profile {name} run --dry-run")
    out(f"  5. Make active (optional):  adore profile use {name}")


# END OF FILE
