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
@brief The `ador init` assisted-configuration wizard (Assisted_Config_And_
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
@author Eng. Dan Dumitru Pasare
@date 2026-07-05
@version 0.1.0
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
import re
import tempfile

from ador import doctor
from ador.config import load_config, validate_config
from ador.profiles import Profile, ProfileStore
from ador.util import CommandRunner, run_command

# CONSTANTS

_LICENSE_LINES = (
    "# Copyright (c) 2026 DDP Engineering",
    "# This software is licensed under the PolyForm Noncommercial License 1.0.0.",
    "# Commercial use requires a separate commercial license.",
    "# See the LICENSE.txt file for full license details.",
    "# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0",
)
_OPENCODE_COMMAND = "opencode run --dir {worktree} -m {model} --format json {prompt}"
_PI_COMMAND = "pi -p --mode json --model {model} {prompt}"
_KNOWN_EXECUTORS = ("opencode", "pi")
_DEFAULT_MODEL = "openai/gpt-5.5"
_RECOMMENDED_BUDGETS = {
    "max_iterations": 12,
    "max_wall_clock_seconds": 5400,
    "max_cost_usd": 5.0,
    "max_files_touched": 40,
}

# DATA MODELS / TYPEDEFINITIONS


class WizardError(RuntimeError):
    """
    @brief   Raised when the wizard cannot complete (aborted, or a required
             non-interactive answer is missing/invalid).
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-05
    @version 0.1.0
    """


@dataclass
class FieldSpec:
    """
    @brief   One explicit prompt: label, description, example, default,
             optional fixed choices, and a validator returning an error or None.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-05
    @version 0.1.0
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
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-05
    @version 0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-05
        @version    0.1.0
        """
        self._out(f"\n{spec.prompt}")
        if spec.description:
            self._out(f"  {spec.description}")
        if spec.example:
            self._out(f"  example: {spec.example}")
        if spec.choices:
            self._out(f"  choices: {' / '.join(spec.choices)}")
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
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-05
    @version 0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-05
        @version    0.1.0
        """
        self.reads.append(spec.key)
        queue = self.answers.get(spec.key)
        if not queue:
            return None
        return queue.pop(0)


# HELPER FUNCTIONS - validators


def _require(value: str) -> str | None:
    """@brief Non-empty check. @version 0.1.0"""
    return None if value.strip() else "a value is required"


def _valid_regex(value: str) -> str | None:
    """@brief The value must compile as a regular expression. @version 0.1.0"""
    try:
        re.compile(value)
    except re.error as exc:
        return f"not a valid regex: {exc}"
    return None


def _existing_dir(value: str) -> str | None:
    """@brief The path must be an existing directory. @version 0.1.0"""
    if not value.strip():
        return "a path is required"
    if not Path(value).expanduser().is_dir():
        return f"directory not found: {value}"
    return None


def _runtime_ok(value: str) -> str | None:
    """@brief Last token must be docker/podman (matches config validation). @version 0.1.0"""
    tokens = value.split()
    if not tokens or tokens[-1] not in ("docker", "podman"):
        return 'must end in "docker" or "podman" (optionally wrapped, e.g. "wsl -d D -- docker")'
    return None


def _positive_int(value: str) -> str | None:
    """@brief A positive integer. @version 0.1.0"""
    try:
        if int(value) <= 0:
            return "must be a positive whole number"
    except ValueError:
        return "must be a whole number"
    return None


def _positive_number(value: str) -> str | None:
    """@brief A positive number (float ok). @version 0.1.0"""
    try:
        if float(value) <= 0:
            return "must be a positive number"
    except ValueError:
        return "must be a number"
    return None


def _slugify(name: str) -> str:
    """
    @brief      Derive a config slug from a display name (matches config rules).
    @param[in]  name Display name.
    @return     A lowercase [a-z][a-z0-9-]* slug (fallback "ador").
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    slug = re.sub(r"[^a-z0-9-]", "", name.lower())
    return slug if re.match(r"^[a-z][a-z0-9-]*$", slug) else "ador"


def ask(spec: FieldSpec, asker: ConsoleAsker | ScriptedAsker, out: Callable[[str], None]) -> str:
    """
    @brief      Prompt one field: read, apply default, validate, re-prompt.
    @details    An empty read falls back to the default. `choices` is enforced.
                On a validation error the interactive asker re-prompts; a
                non-interactive asker fails fast with WizardError (D7).
    @param[in]  spec The field to collect.
    @param[in]  asker The prompt reader (Console/Scripted).
    @param[in]  out Output sink for error lines.
    @return     The validated string value.
    @exception  WizardError When a non-interactive answer is invalid/missing.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    while True:
        raw = asker.read(spec)
        value = raw if raw is not None else (spec.default or "")
        error: str | None = None
        if spec.choices and value not in spec.choices:
            error = f"choose one of: {', '.join(spec.choices)}"
        elif spec.validate is not None:
            error = spec.validate(value)
        if error is None:
            return value
        if not asker.interactive:
            raise WizardError(f"{spec.key}: {error} (got {value!r})")
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    if "'" not in value and "\n" not in value:
        return f"'{value}'"
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_value(value: object) -> str:
    """
    @brief      Encode a scalar / list-of-scalars as a TOML value.
    @param[in]  value bool / int / float / str / list.
    @return     The TOML token.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_string(str(item)) for item in value) + "]"
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    lines = list(_LICENSE_LINES)
    lines.append("#")
    lines.append(f"# Generated by `ador init` for profile '{profile_name}' on {stamp}.")
    lines.append(f"# Re-run `ador init --profile {profile_name} --force` to regenerate,")
    lines.append("# or edit by hand (see 00_Planning/Configuration_Reference.md).")
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
) -> Profile:
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
    @return     The saved Profile.
    @exception  WizardError On abort, an existing profile without --force, or a
                config that fails validation.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    key = os_key or doctor.detect_os()

    # -- Phase B (name first, so we can guard existence early) --------------------
    if name is None:
        name = ask(FieldSpec(
            "profile_name", "Name this runtime-project profile:",
            "a short, filesystem-safe id you'll pass as --profile <name>",
            "cockpit-gcp",
            validate=lambda v: None if re.match(r"^[a-z0-9][a-z0-9._-]{0,63}$", v)
            else "use lowercase letters/digits/._- (start alphanumeric)",
        ), asker, out)
    if store.exists(name) and not force:
        raise WizardError(f"profile {name!r} already exists (use --force to overwrite)")

    description = ask(FieldSpec(
        "description", "One-line description (optional):",
        "shown in `ador profile list`", "GCP analytics platform - TF + Python + TS",
        default="",
    ), asker, out)
    agent_name = ask(FieldSpec(
        "agent_name", "Bot display name:",
        "names branches/containers via its slug; keep the default unless you have a reason",
        "ADOR", default="ADOR",
    ), asker, out)
    slug = _slugify(agent_name)

    # -- Phase C (platform & repository) ------------------------------------------
    kind = ask(FieldSpec(
        "kind", "Is the project on GitLab or GitHub?",
        "selects the platform adapter", "gitlab",
        default="gitlab", choices=("gitlab", "github"),
    ), asker, out)

    # Phase A guidance is informational and platform-aware; print it now.
    _report_environment(out, runner, key, kind)

    hosting = ask(FieldSpec(
        "hosting", "Public service or corporate/self-hosted instance?",
        "gitlab.com/github.com, or a company instance", "corporate",
        default="public", choices=("public", "corporate"),
    ), asker, out)
    host = ""
    if hosting == "corporate":
        host = ask(FieldSpec(
            "host_url", "Instance URL:",
            "the CLI must be authenticated against this host "
            "(glab auth login --hostname <host>)",
            "https://gitlab.mycorp.fr",
            validate=lambda v: None if v.startswith("http") else "must be a URL",
        ), asker, out)
    # Visibility is informational: it decides whether auth is mandatory (the
    # environment check above already surfaces the token/login guidance).
    ask(FieldSpec(
        "visibility", "Is the repository public or private/corporate?",
        "a private repo needs CLI auth or a token (see the guidance above)",
        "private", default="private", choices=("public", "private"),
    ), asker, out)
    repo = ask(FieldSpec(
        "repo", "Repository path (group/subgroup/project, NOT a URL):",
        "the project's path on the platform",
        "rd/internal/france/delivery-tools/delivery-cockpit/cockpit-gcp",
        validate=_require,
    ), asker, out)

    # -- Phase D (local clone & worktree) -----------------------------------------
    repo_path = ask(FieldSpec(
        "repo_path", "Absolute path to the local clone:",
        "ADOR creates per-run worktrees from it and mounts it into the container",
        "D:/projects/cockpit-gcp  (Windows)  |  /home/you/cockpit-gcp  (Linux)",
        validate=_existing_dir,
    ), asker, out)
    if not (Path(repo_path).expanduser() / ".git").exists():
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
            "ADOR checks the branch template against it",
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
    runtimes = doctor.detect_runtimes(runner, os_key=key)
    suggested = _suggest_runtime(key, runtimes)
    runtime = ask(FieldSpec(
        "runtime", "Container runtime:",
        "docker/podman, optionally wrapped for Docker/podman inside WSL2",
        'docker  |  podman  |  wsl -d Ubuntu-24.04 -- docker',
        default=suggested, validate=_runtime_ok,
    ), asker, out)
    run_args: list[str] = []
    if runtime.split()[-1] == "podman":
        run_args = ["--userns=keep-id"]
        out("  note: rootless podman -> adding run_args = [\"--userns=keep-id\"].")
    image = ask(FieldSpec(
        "image", "Executor image name:",
        "build it once per docker/README.md before the first run",
        "ador-executor:latest", default="ador-executor:latest", validate=_require,
    ), asker, out)
    executor_cli = ask(FieldSpec(
        "executor_cli", "Executor CLI:",
        "the agent that runs each gate (both read AGENTS.md and get their "
        "push/merge guardrails from the repo adapter)", "opencode",
        default="opencode", choices=_KNOWN_EXECUTORS,
    ), asker, out)
    model = ask(FieldSpec(
        "model", "Model id (provider/model):",
        "the executor's model", _DEFAULT_MODEL, default=_DEFAULT_MODEL,
        validate=_require,
    ), asker, out)
    auth_mode = ask(FieldSpec(
        "auth_mode", "Executor auth mode:",
        "api-key sets a provider key in .env (production); host-auth bridges a "
        "local OAuth session (pilot only)",
        "api-key", default="api-key", choices=("api-key", "host-auth"),
    ), asker, out)

    # -- Phase G (delivery) -------------------------------------------------------
    reviewers_raw = ask(FieldSpec(
        "reviewers", "Reviewer username(s) for the draft MR (comma-separated):",
        "at least one; the MR is always a DRAFT and ADOR never merges",
        "dan.pasare, jane.doe",
        validate=lambda v: None if [p for p in v.split(",") if p.strip()]
        else "at least one reviewer is required",
    ), asker, out)
    reviewers = [part.strip() for part in reviewers_raw.split(",") if part.strip()]

    # -- Phase H (budgets & policy) -----------------------------------------------
    budgets_choice = ask(FieldSpec(
        "budgets_choice", "Budgets: recommended supervised, or customize?",
        "recommended = 12 iters / 90 min / $5 / 40 files (6 crawl / 12-15 "
        "supervised / 20 unattended)",
        "recommended", default="recommended", choices=("recommended", "custom"),
    ), asker, out)
    budgets = dict(_RECOMMENDED_BUDGETS)
    if budgets_choice == "custom":
        budgets["max_iterations"] = int(ask(FieldSpec(
            "max_iterations", "Max executor launches per run:",
            "6 crawl / 12-15 supervised / 20 unattended", "12",
            default="12", validate=_positive_int), asker, out))
        budgets["max_wall_clock_seconds"] = int(ask(FieldSpec(
            "max_wall_clock_seconds", "Max active wall-clock per run (seconds):",
            "restarts on retry/resume", "5400", default="5400",
            validate=_positive_int), asker, out))
        budgets["max_cost_usd"] = float(ask(FieldSpec(
            "max_cost_usd", "Max model spend per run (USD):", "", "5.0",
            default="5.0", validate=_positive_number), asker, out))
        budgets["max_files_touched"] = int(ask(FieldSpec(
            "max_files_touched", "Max files a run may change:", "", "40",
            default="40", validate=_positive_int), asker, out))
    polling_mode = ask(FieldSpec(
        "polling_mode", "Run mode:",
        "once = single pass (cron/Task Scheduler); loop = long-running service",
        "once", default="once", choices=("once", "loop"),
    ), asker, out)
    state_location = ask(FieldSpec(
        "state_location", "Where should this project's ADOR state live?",
        "profile = under the profile (recommended, isolated); project = a "
        ".ador beside the clone",
        "profile", default="profile", choices=("profile", "project"),
    ), asker, out)
    store_root = (
        str(store.default_store_root(name)) if state_location == "profile"
        else str(Path(repo_path).expanduser() / ".ador")
    )

    # -- assemble the minimal config ----------------------------------------------
    sections = _assemble_sections(
        agent_name=agent_name, kind=kind, repo=repo, store_root=store_root,
        repo_path=repo_path, worktree_root=worktree_root, branch_template=branch_template,
        branch_rule=branch_rule, runtime=runtime, run_args=run_args, image=image,
        executor_cli=executor_cli, command=_command_for(executor_cli), model=model,
        auth_mode=auth_mode, target_branch=target_branch, reviewers=reviewers,
        budgets=budgets, budgets_choice=budgets_choice, polling_mode=polling_mode,
    )

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
    _validate_or_raise(document, out)

    config_path = store.config_path(name)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(document, encoding="utf-8")
    profile = store.create(
        name, overwrite=force, description=description, platform=kind, host=host,
        repo=repo, runtime=runtime, host_os=key, config_path=str(config_path),
        store_root=store_root,
    )
    _print_next_steps(out, name, kind, auth_mode, model, runtime, image)
    return profile


# LOCAL HELPERS


def _command_for(executor_cli: str) -> str:
    """
    @brief      A safe command template for an executor CLI.
    @details    opencode uses the proven template; any other CLI gets a generic
                one that still carries {prompt} and never --auto (so config
                validation passes). Advanced users edit config.toml by hand.
    @param[in]  executor_cli Executor name.
    @return     The command template.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    if executor_cli == "opencode":
        return _OPENCODE_COMMAND
    if executor_cli == "pi":
        return _PI_COMMAND
    return f"{executor_cli} run --dir {{worktree}} -m {{model}} {{prompt}}"


def _suggest_runtime(os_key: str, runtimes: doctor.RuntimeDetection) -> str:
    """
    @brief      Best-guess default runtime string from detection.
    @param[in]  os_key Host OS key.
    @param[in]  runtimes Detected runtimes.
    @return     A runtime string (docker/podman, WSL-wrapped on Windows).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
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
    @param[in]  kind Platform kind (selects glab/gh).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
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
    out("-----------------------------------------")


def _assemble_sections(**a: object) -> list[tuple[str, dict[str, object]]]:
    """
    @brief      Build the ordered, MINIMAL config sections from answers.
    @details    Writes the fields validation requires plus any that differ from
                the dataclass defaults; true defaults are omitted so the file
                stays small (decision D4).
    @param[in]  a Collected answers (see run_wizard).
    @return     Ordered (table-header, key->value) pairs.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    sections: list[tuple[str, dict[str, object]]] = []
    if a["agent_name"] != "ADOR":
        sections.append(("agent", {"name": a["agent_name"]}))
    sections.append(("platform", {"kind": a["kind"], "repo": a["repo"]}))
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

    executor: dict[str, object] = {}
    if a["executor_cli"] != "opencode":
        executor["default"] = a["executor_cli"]
    if a["auth_mode"] == "host-auth":
        executor["stage_host_auth"] = True
    else:
        executor["env_keys"] = _env_keys_for_model(str(a["model"]))
    if executor:
        sections.append(("executor", executor))
    sections.append((f"executor.{a['executor_cli']}",
                     {"command": a["command"], "model": a["model"]}))

    delivery: dict[str, object] = {"reviewers": a["reviewers"]}
    if a["target_branch"] != "develop":
        delivery["target_branch"] = a["target_branch"]
    sections.append(("delivery", delivery))

    if a["budgets_choice"] == "custom" or a["budgets"] != _RECOMMENDED_BUDGETS:
        sections.append(("budgets", dict(a["budgets"])))  # type: ignore[arg-type]
    else:
        sections.append(("budgets", dict(_RECOMMENDED_BUDGETS)))

    if a["polling_mode"] != "loop":
        sections.append(("polling", {"mode": a["polling_mode"]}))
    return sections


def _env_keys_for_model(model: str) -> list[str]:
    """
    @brief      The provider secret key name(s) implied by a model id.
    @param[in]  model e.g. "openai/gpt-5.5" or "anthropic/claude-...".
    @return     The env-key NAMES to inject (never values).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    lowered = model.lower()
    if lowered.startswith("anthropic"):
        return ["ANTHROPIC_API_KEY"]
    if lowered.startswith("openai"):
        return ["OPENAI_API_KEY"]
    return ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]


def _validate_or_raise(document: str, out: Callable[[str], None]) -> None:
    """
    @brief      Load + validate the emitted config; raise on any issue.
    @details    Validates the ACTUAL written document (via a temp file) the same
                way the engine will at startup, so a saved profile is always
                loadable and valid (never save an invalid one).
    @param[in]  document The config.toml text.
    @param[in]  out Output sink for the issue list.
    @exception  WizardError When validation finds issues.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False,
                                     encoding="utf-8") as handle:
        handle.write(document)
        tmp_path = Path(handle.name)
    try:
        issues = validate_config(load_config(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)
    if issues:
        out("\nThe assembled config is invalid (not saved):")
        for issue in issues:
            out(f"  - {issue}")
        raise WizardError(f"config validation failed with {len(issues)} issue(s)")


def _print_summary(
    out: Callable[[str], None], name: str, sections: list[tuple[str, dict[str, object]]]
) -> None:
    """@brief Print the resolved config for confirmation. @version 0.1.0"""
    out(f"\n=== Profile '{name}' - review ===")
    for header, mapping in sections:
        out(f"[{header}]")
        for key, value in mapping.items():
            out(f"  {key} = {value}")
    out("=================================")


def _print_next_steps(
    out: Callable[[str], None], name: str, kind: str, auth_mode: str,
    model: str, runtime: str, image: str,
) -> None:
    """@brief Print OS-agnostic next steps after a successful write. @version 0.1.0"""
    out(f"\nProfile '{name}' created and validated.")
    out("Next steps:")
    if auth_mode == "api-key":
        keys = " / ".join(_env_keys_for_model(model))
        out(f"  1. Put your provider key ({keys}) in a .env file beside the clone.")
    else:
        out("  1. host-auth mode: ensure your local opencode session is authorized.")
    out(f"  2. Build the executor image ({image}) - see docker/README.md.")
    out(f"  3. Validate:  ador --profile {name} config validate")
    out(f"  4. Dry-run:   ador --profile {name} run --dry-run")
    out(f"  5. Make active (optional):  ador profile use {name}")


# END OF FILE
