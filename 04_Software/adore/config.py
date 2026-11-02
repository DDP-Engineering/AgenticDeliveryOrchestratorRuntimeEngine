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
@file config.py
@brief Load and validate ADORE configuration from config.toml.
@details Parses config.toml with the standard-library tomllib into typed
         section dataclasses (one per section of Configuration_Reference.md).
         Missing keys fall back to the documented defaults; names derived from
         the agent slug (state dir, questions file) are resolved at load time.
         Secrets are read from the environment, never from here.
"""

from __future__ import annotations

# IMPORTS
from dataclasses import asdict, dataclass, field, fields
import json
import math
from pathlib import Path
import re
import shlex
from string import Formatter
import subprocess
import sys
import tomllib
from typing import Any

from adore.aegis import RUN_KINDS
from adore.branding import (
    EGRESS_NETWORK_PREFIX,
    EGRESS_PROXY_IMAGE,
    EXECUTOR_BASE_IMAGE,
    NPM_CACHE_VOLUME,
    PI_NATIVE_COMMAND,
    PRODUCT_ACRONYM,
    PRODUCT_SLUG,
    UV_CACHE_VOLUME,
)
from adore.util import parse_duration

# CONSTANTS

_QUIET_HOURS_RE = re.compile(r"^\d{2}:\d{2}-\d{2}:\d{2}$")
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_MANAGED_CONTAINER_ENV = frozenset({
    "HOME",
    "GIT_DIR",
    "GIT_COMMON_DIR",
    "GIT_WORK_TREE",
    "GIT_AUTHOR_NAME",
    "GIT_AUTHOR_EMAIL",
    "GIT_COMMITTER_NAME",
    "GIT_COMMITTER_EMAIL",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
})
_SHELL_CONTROL_CHARS = frozenset("|&;<>")
#: Environment names of the coding agents ADORE no longer supports; Pi is the
#: only one. A variable with one of these prefixes is refused, not ignored.
REMOVED_AGENT_ENV_PREFIXES = ("OPENCODE_", "CODEX_", "QWEN_")
_FORGE_CREDENTIAL_ENV = frozenset({
    "GITHUB_TOKEN", "GH_TOKEN", "GITLAB_TOKEN", "GLAB_TOKEN", "GITEA_TOKEN",
    "TEA_TOKEN",
})
#: Accepted `[container] selinux_relabel` values, mapped to the per-mount
#: option each one appends to ADORE's host bind mounts. "shared" appends `z`,
#: which an SELinux-enforcing host needs before a container may read the
#: mounted clone, worktree and io directory. The private `Z` label is
#: deliberately NOT offered: it relabels content with a per-container MCS
#: category, and the repository clone is shared by every run and by host git,
#: so a private label would lock the clone to one container and break the next
#: run. An operator who truly needs `Z` can still pass a mount through
#: [container] run_args and own that decision explicitly.
#:
#: This mapping is the single source of truth. The accepted-mode tuple is
#: derived from it rather than written out again, so a mode can never be
#: accepted by validation and then have no option to apply.
SELINUX_RELABEL_OPTIONS = {"off": "", "shared": "z"}
SELINUX_RELABEL_MODES = tuple(SELINUX_RELABEL_OPTIONS)

# The AEGIS task stages a per-stage timeout override may target: the stages
# that launch an executor session. Validate closes the task in AEGIS 0.15.0,
# so no deliver stage remains to bound. Declared here rather than imported
# from the orchestrator so configuration validation stays free of the engine.
AEGIS_STAGES = ("frame", "specify", "design", "build", "validate")
_HOST_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")

KNOWN_SECTIONS = frozenset(
    {
        "agent",
        "platform",
        "state",
        "polling",
        "readiness",
        "labels",
        "executor",
        "execution",
        "local",
        "clarification",
        "container",
        "worktree",
        "workflow",
        "recovery",
        "budgets",
        "delivery",
        "review",
        "reconcile",
        "metrics",
    }
)

# DATA MODELS / TYPEDEFINITIONS


@dataclass
class AgentConfig:
    """
    @brief   [agent] - bot identity; the slug derives every local name.
    @details email is the git commit author email used inside the executor
             container (Security_And_Credentials.md); derived from the
             slug when empty.
    """

    name: str = PRODUCT_ACRONYM
    slug: str = ""
    email: str = ""


@dataclass
class PlatformConfig:
    """
    @brief   [platform] - which Git-platform adapter and repository to use.
    @details `login` names the tea login (`tea logins list`) for kind
             "gitea", where one CLI can hold several instance/account logins;
             empty uses tea's default login. Meaningless for glab/gh (their
             auth binds to the host), so validation rejects it there.
    """

    kind: str = "gitlab"
    repo: str = ""
    login: str = ""


@dataclass
class StateConfig:
    """
    @brief   [state] - where run state lives.
    @details The status comment is always one comment edited in place, with the
             lifecycle labels; there is no per-change mode.
    """

    store_root: str = ""


@dataclass
class PollingConfig:
    """
    @brief   [polling] - poll loop cadence and concurrency.
    """

    mode: str = "loop"
    poll_interval_seconds: int = 60
    poll_jitter_seconds: int = 5
    poll_backoff: bool = True
    max_concurrent_runs: int = 1
    quiet_hours: list[str] = field(default_factory=list)


@dataclass
class ReadinessConfig:
    """
    @brief   [readiness] - selection filter applied after eligibility.
    """

    require_acceptance_criteria: bool = False
    require_priority_label: bool = True
    max_scope_hint: str = "small"


@dataclass
class LifecycleLabels:
    """
    @brief   [labels.lifecycle] - orchestrator-managed run-state labels.
    """

    ready: str = "agent-ready"
    working: str = "agent-working"
    clarify: str = "agent-clarify"
    answered: str = "agent-answered"
    review: str = "agent-mr"
    failed: str = "agent-failed"
    done: str = "agent-done"


@dataclass
class SelectionLabels:
    """
    @brief   [labels.selection] - human-managed priority/type labels.
    """

    priority_high: str = "P1"
    priority_medium: str = "P2"
    priority_low: str = "P3"
    type_feature: str = "feature"
    type_bug: str = "bug"

    def priority_order(self) -> list[str]:
        """
        @brief   Priority labels from highest to lowest.
        @return  Ordered label list used for queue ranking.
        """
        return [self.priority_high, self.priority_medium, self.priority_low]


@dataclass
class ControlLabels:
    """
    @brief   [labels.control] - human overrides checked before eligibility.
    """

    hold: str = "agent-hold"
    exclude: str = "no-agent"


@dataclass
class LabelsConfig:
    """
    @brief   [labels.*] - all label categories; roles, never hard-coded strings.
    """

    lifecycle: LifecycleLabels = field(default_factory=LifecycleLabels)
    selection: SelectionLabels = field(default_factory=SelectionLabels)
    control: ControlLabels = field(default_factory=ControlLabels)


@dataclass
class ExecutorConfig:
    """
    @brief   [executor] - how ADORE launches Pi, its only coding agent.
    @details `model` is the Pi model in provider/model form. `command` is the
             argv template of a native (installed) Pi run; a container run
             uses the image's pinned Pi and ignores it. env_keys names the
             secret subset injected into the executor (from the environment /
             .env); only these keys ever reach it (design 12b: scope
             minimally).
    """

    model: str = ""
    command: str = PI_NATIVE_COMMAND
    mode: str = "thick"
    questions_file: str = ""
    env_keys: list[str] = field(
        default_factory=lambda: ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    )


@dataclass
class ContainerEgressConfig:
    """
    @brief   [container.egress] - outbound network policy for executor runs.
    @details open provides unrestricted egress; none disables container
             networking; allowlist-proxy routes HTTP/HTTPS through a per-run
             ADORE proxy with exact/wildcard hostname allowlists.
    """

    mode: str = "open"
    allowlist: list[str] = field(default_factory=list)
    no_proxy: list[str] = field(default_factory=lambda: ["localhost", "127.0.0.1", "::1"])
    proxy_image: str = EGRESS_PROXY_IMAGE
    proxy_port: int = 3128
    network_prefix: str = EGRESS_NETWORK_PREFIX


@dataclass
class ClarificationConfig:
    """
    @brief   [clarification] - park/resume bounds and timeouts.
    """

    max_rounds: int = 3
    reminder_after: str = "24h"
    answer_timeout: str = "72h"
    timeout_state: str = "failed"

    def reminder_after_seconds(self) -> int:
        """
        @brief   The reminder delay parsed to seconds.
        @return  Seconds after parked_at before the single nudge.
        """
        return parse_duration(self.reminder_after)

    def answer_timeout_seconds(self) -> int:
        """
        @brief   The hard answer timeout parsed to seconds.
        @return  Seconds after parked_at before the run is released.
        """
        return parse_duration(self.answer_timeout)


@dataclass
class ExecutionConfig:
    """
    @brief   [execution] - shared backend and reviewed container preparation.
    @details Preparation is path#job@full-commit; empty retains legacy behavior.
             Bounds apply to setup independently of the total run budget.
    """

    backend: str = "container"
    preparation: str = ""
    preparation_step_timeout_seconds: int = 300
    preparation_total_timeout_seconds: int = 900
    preparation_max_attempts: int = 2


@dataclass
class LocalConfig:
    """
    @brief   [local] - preinstalled native service-account environment.
    @details Selects existing home/PATH without impersonation or installation.
             Linux requires an operator-delegated cgroup-v2 root for ownership.
    """

    account: str = "current"
    home: str = ""
    path: str = ""
    environment: dict[str, str] = field(default_factory=dict)
    cgroup_root: str = ""


@dataclass
class ContainerConfig:
    """
    @brief   [container] - execution isolation and parked-container TTL.
    @details run_args are extra option tokens for `<runtime> run` (e.g.
             "--userns=keep-id" for rootless podman - live finding
             2026-07-04 - or resource limits like "--memory=2g").
             runtime_env is the non-secret environment injected into both
             container creation and exec calls; values travel through the same
             non-secret/secret split as executor env. required_tool_checks are
             project-image checks run after provision so a profile fails fast
             when the selected runtime-project image lacks required tooling.
             egress controls the run container's outbound network boundary.
             selinux_relabel adds the SELinux relabel suffix ADORE's host bind
             mounts need on an enforcing host; see SELINUX_RELABEL_MODES for
             why only the shared label is offered.
    @details `parked_state` was removed (review finding ADORE-ARCH-007): it
             was validated but never consulted at runtime - `keep_parked` is
             the field parking actually reads - so a redundant, misleading
             twin was deleted rather than kept as permanent dead config.
    """

    runtime: str = "docker"
    image: str = EXECUTOR_BASE_IMAGE
    keep_parked: bool = True
    parked_ttl_mode: str = "polls"
    parked_ttl_seconds: int = 7200
    parked_ttl_polls: int = 30
    uv_cache_volume: str = UV_CACHE_VOLUME
    npm_cache_volume: str = NPM_CACHE_VOLUME
    run_args: list[str] = field(default_factory=list)
    runtime_env: dict[str, str] = field(default_factory=lambda: {"UV_LINK_MODE": "copy"})
    required_tool_checks: list[str] = field(default_factory=list)
    selinux_relabel: str = "off"
    egress: ContainerEgressConfig = field(default_factory=ContainerEgressConfig)


@dataclass
class WorktreeConfig:
    """
    @brief   [worktree] - local clone of the target repo and worktree root.
    @details repo_path is the local clone that per-run worktrees are created
             from; it is mounted (with the worktree) into the executor
             container. Required for the isolation layer. branch_template
             names the run branch ({slug}, {run_id}, {iid} placeholders) so
             repo conventions like a mandatory "feature/" prefix are a config
             change, not code.
    """

    repo_path: str = ""
    root: str = "worktrees"
    branch_template: str = "{slug}/{run_id}"
    branch_rule: str = ""


@dataclass
class WorkflowConfig:
    """
    @brief   [workflow] - how ticket labels map onto an AEGIS task.
    @details `kind_labels` maps a ticket label to an AEGIS task type; fix/bug
             labels win over change, then configured feature labels, with
             `default_kind` used when none match. The quick label is a framing
             hint only; the executor must still apply
             AEGIS's documented eligibility rules. `stage_timeout_overrides`
             raises or lowers the
             per-executor-launch bound for individual stages; anything absent
             uses [budgets] per_gate_timeout_seconds.
    """

    default_kind: str = "feature"
    kind_labels: dict[str, str] = field(
        default_factory=lambda: {"bug": "fix", "fix": "fix", "change": "change"}
    )
    quick_label: str = "agent-quick"
    aegis_python: str = "python"
    stage_timeout_overrides: dict[str, int] = field(default_factory=dict)


@dataclass
class RecoveryConfig:
    """@brief [recovery] - bounded stage and transient failure handling."""

    max_stage_failures: int = 3
    max_transient_retries: int = 3
    retry_backoff_seconds: list[int] = field(default_factory=lambda: [5, 30, 120])


@dataclass
class BudgetsConfig:
    """
    @brief   [budgets] - hard bounds so a run can never thrash forever.
    @details `per_gate_timeout_seconds` bounds ONE executor launch (the
             wall-clock a single gate/fix relaunch may take);
             `max_wall_clock_seconds` bounds the WHOLE run since pickup. They
             are independent knobs - a generous per-gate limit no longer forces
             an equally generous total, and a tight total no longer throttles
             every individual gate.
    """

    max_iterations: int = 20
    max_wall_clock_seconds: int = 3600
    per_gate_timeout_seconds: int = 1800
    max_cost_usd: float = 5.0  # Zero explicitly disables reported-cost enforcement.
    # AEGIS task journals, step files, anchors, evolution records and reports
    # count alongside product changes. Keep the run bounded while leaving
    # honest headroom for governance evidence and the product diff.
    max_files_touched: int = 120


@dataclass
class DeliveryConfig:
    """
    @brief   [delivery] - draft MR/PR boundary; never merges.
    """

    target_branch: str = "develop"
    draft: bool = True
    reviewers: list[str] = field(default_factory=list)
    remove_source_branch: bool = True
    approval_label: str = "agent-approved"
    publish_checkpoints: bool = True


@dataclass
class ReviewConfig:
    """
    @brief   [review] - post-MR revise loop triggers and bounds.
    @details `on_pipeline_failure` decides what a red forge pipeline on the
             published draft does. "revise" starts a governed repair round on
             the SAME bounded path the revise label uses, so the repair still
             ends at a fresh human approval before anything is pushed;
             "notify" posts one comment and waits for a human; "ignore" skips
             the pipeline read entirely. Every mode obeys `max_review_rounds`.
    """

    trigger: str = "label"
    revise_label: str = "agent-revise"
    max_review_rounds: int = 5
    review_reminder_after: str = "48h"
    on_pipeline_failure: str = "revise"


@dataclass
class ReconcileConfig:
    """
    @brief   [reconcile] - reactions to external ticket changes.
    """

    on_ticket_deleted: str = "abort-cleanup"
    on_ticket_closed: str = "cancel"
    on_trigger_removed: str = "pause"


@dataclass
class MetricsConfig:
    """
    @brief   [metrics] - stdlib-only statistics capture.
    """

    enabled: bool = True
    db_path: str = ""
    export_jsonl: str = ""
    capture_tokens: bool = True
    capture_resource: bool = True
    html_out: str = ""


@dataclass
class Config:
    """
    @brief   Parsed, typed ADORE configuration (one attribute per section).
    @details Derived defaults (store_root, questions_file, metrics paths) are
             resolved from the agent slug at load time. The raw mapping is kept
             for validation of unknown sections and for `adore config show`.
    """

    agent: AgentConfig = field(default_factory=AgentConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)
    state: StateConfig = field(default_factory=StateConfig)
    polling: PollingConfig = field(default_factory=PollingConfig)
    readiness: ReadinessConfig = field(default_factory=ReadinessConfig)
    labels: LabelsConfig = field(default_factory=LabelsConfig)
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    local: LocalConfig = field(default_factory=LocalConfig)
    clarification: ClarificationConfig = field(default_factory=ClarificationConfig)
    container: ContainerConfig = field(default_factory=ContainerConfig)
    worktree: WorktreeConfig = field(default_factory=WorktreeConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    recovery: RecoveryConfig = field(default_factory=RecoveryConfig)
    budgets: BudgetsConfig = field(default_factory=BudgetsConfig)
    delivery: DeliveryConfig = field(default_factory=DeliveryConfig)
    review: ReviewConfig = field(default_factory=ReviewConfig)
    reconcile: ReconcileConfig = field(default_factory=ReconcileConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        @brief   Resolved configuration as a plain nested mapping.
        @return  Mapping suitable for JSON output (`adore config show`).
        """
        result = {
            name: asdict(getattr(self, name))
            for name in (
                "agent",
                "platform",
                "state",
                "polling",
                "readiness",
                "labels",
                "executor",
                "execution",
                "local",
                "clarification",
                "container",
                "worktree",
                "workflow",
                "recovery",
                "budgets",
                "delivery",
                "review",
                "reconcile",
                "metrics",
            )
        }
        return result


# HELPER FUNCTIONS


def _build_section(cls: type, data: Any) -> Any:
    """
    @brief      Build one section dataclass from a raw mapping.
    @details    Unknown keys are left out here and refused by validate_config;
                known keys override the documented defaults.
    @param[in]  cls The section dataclass type.
    @param[in]  data Raw mapping from tomllib (or anything else -> defaults).
    @return     A populated section instance.
    """
    if not isinstance(data, dict):
        return cls()
    known = {f.name for f in fields(cls)}
    kwargs = {key: value for key, value in data.items() if key in known}
    return cls(**kwargs)


def _build_labels(data: Any) -> LabelsConfig:
    """
    @brief      Build the nested [labels.*] categories.
    @param[in]  data Raw [labels] mapping.
    @return     A populated LabelsConfig.
    """
    if not isinstance(data, dict):
        return LabelsConfig()
    return LabelsConfig(
        lifecycle=_build_section(LifecycleLabels, data.get("lifecycle")),
        selection=_build_section(SelectionLabels, data.get("selection")),
        control=_build_section(ControlLabels, data.get("control")),
    )


def _build_container(data: Any) -> ContainerConfig:
    """
    @brief      Build [container] including the nested [container.egress].
    @param[in]  data Raw [container] mapping.
    @return     A populated ContainerConfig.
    """
    if not isinstance(data, dict):
        return ContainerConfig()
    scalars = {key: value for key, value in data.items() if key != "egress"}
    section = _build_section(ContainerConfig, scalars)
    section.egress = _build_section(ContainerEgressConfig, data.get("egress"))
    return section


def _command_placeholder_issues(command: str) -> list[str]:
    """
    @brief      Reject a command template whose braces the launcher cannot fill.
    @details    The launcher renders the template with `str.format`, so any
                brace the executor does not supply raises `KeyError` at GATE
                time - after provisioning, once per attempt, until the stage
                budget is spent - with nothing pointing at the real cause.
                A shell brace such as `${HOME}` or an inline JSON argument
                fails the same way.
                Catching it here turns an opaque runtime failure into a setup
                message.
    @param[in]  command The configured command template.
    @return     One issue per unsupported or malformed placeholder.
    """
    supported = {"prompt", "model", "worktree"}
    try:
        fields = {
            name for _, name, _, _ in Formatter().parse(command) if name is not None
        }
    except ValueError as exc:
        return [
            f"[executor] command has malformed placeholder braces: {exc}"
        ]
    unsupported = sorted(name for name in fields if name.split(".")[0] not in supported)
    return [
        "[executor] command uses a placeholder the launcher cannot "
        f"fill: {{{name}}} (supported: {', '.join(sorted(supported))}). A literal "
        "brace must be doubled."
        for name in unsupported
    ]


def _valid_hostname_pattern(value: str) -> bool:
    """
    @brief      Check an egress allowlist hostname or leading wildcard.
    @param[in]  value Hostname pattern, optionally starting with "*.".
    @return     True when the pattern is syntactically safe.
    """
    host = value[2:] if value.startswith("*.") else value
    if not host or len(host) > 253 or host.endswith(".") or "." not in host:
        return False
    return all(_HOST_LABEL_RE.match(label) for label in host.split("."))


def _valid_no_proxy_entry(value: str) -> bool:
    """
    @brief      Check a NO_PROXY entry accepted by ADORE config validation.
    @param[in]  value Hostname, leading wildcard, localhost, or loopback IP.
    @return     True when the value is syntactically safe.
    """
    if value in ("localhost", "127.0.0.1", "::1"):
        return True
    return _valid_hostname_pattern(value)


def _derive_names(config: Config) -> None:
    """
    @brief      Resolve slug-derived defaults left empty in the file.
    @details    slug <- lowercase agent name; email <- "<slug>-bot@local";
                store_root <- ".<slug>"; questions_file <-
                "<SLUG>_QUESTIONS.md"; metrics paths under the store root.
                Explicit values are never overridden.
    @param[in,out] config The configuration to complete in place.
    """
    if not config.agent.slug:
        config.agent.slug = (
            re.sub(r"[^a-z0-9-]", "", config.agent.name.lower()) or PRODUCT_SLUG
        )
    slug = config.agent.slug
    if not config.agent.email:
        config.agent.email = f"{slug}-bot@local"
    if not config.state.store_root:
        config.state.store_root = f".{slug}"
    if not config.executor.questions_file:
        config.executor.questions_file = f"{slug.upper()}_QUESTIONS.md"
    store = config.state.store_root
    if not config.metrics.db_path:
        config.metrics.db_path = f"{store}/metrics.db"
    if not config.metrics.export_jsonl:
        config.metrics.export_jsonl = f"{store}/metrics/runs.jsonl"
    if not config.metrics.html_out:
        config.metrics.html_out = f"{store}/metrics/stats.html"


# PUBLIC API


def default_config() -> Config:
    """
    @brief   ADORE's built-in configuration, as a file that sets nothing gets it.
    @details Name-derived defaults are resolved from the default agent name
             (slug `adore`, `.adore` state root and the paths under it).
    @return  A new default configuration.
    """
    config = Config()
    _derive_names(config)
    return config


def load_config(path: str | Path) -> Config:
    """
    @brief      Load configuration from a TOML file into typed sections.
    @details    Missing keys take the documented defaults and unknown keys
                are left out, so `adore config validate` reports every problem,
                unknown keys included, in one pass instead of dying on the first.
    @param[in]  path Path to config.toml.
    @return     A populated Config instance.
    @exception  FileNotFoundError When the file does not exist.
    @exception  tomllib.TOMLDecodeError When the file is not valid TOML.
    """
    with Path(path).open("rb") as handle:
        raw = tomllib.load(handle)
    config = Config(
        agent=_build_section(AgentConfig, raw.get("agent")),
        platform=_build_section(PlatformConfig, raw.get("platform")),
        state=_build_section(StateConfig, raw.get("state")),
        polling=_build_section(PollingConfig, raw.get("polling")),
        readiness=_build_section(ReadinessConfig, raw.get("readiness")),
        labels=_build_labels(raw.get("labels")),
        executor=_build_section(ExecutorConfig, raw.get("executor")),
        execution=_build_section(ExecutionConfig, raw.get("execution")),
        local=_build_section(LocalConfig, raw.get("local")),
        clarification=_build_section(ClarificationConfig, raw.get("clarification")),
        container=_build_container(raw.get("container")),
        worktree=_build_section(WorktreeConfig, raw.get("worktree")),
        workflow=_build_section(WorkflowConfig, raw.get("workflow")),
        recovery=_build_section(RecoveryConfig, raw.get("recovery")),
        budgets=_build_section(BudgetsConfig, raw.get("budgets")),
        delivery=_build_section(DeliveryConfig, raw.get("delivery")),
        review=_build_section(ReviewConfig, raw.get("review")),
        reconcile=_build_section(ReconcileConfig, raw.get("reconcile")),
        metrics=_build_section(MetricsConfig, raw.get("metrics")),
        raw=raw,
    )
    _derive_names(config)
    return config


def valid_reviewers(value: object) -> bool:
    """
    @brief Validate a list of forge account names before CLI submission; empty requests no review.
    @param[in] value Human-authored reviewer list.
    @return True for bounded names without whitespace, controls or option prefixes.
    """
    return isinstance(value, list) and all(
        isinstance(name, str) and 1 <= len(name) <= 255 and not name.startswith("-")
        and not any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in name)
        for name in value
    )


def branch_naming_preview(template: str, rule: str, slug: str) -> dict[str, Any]:
    """
    @brief Render a fixed job-branch example and check the optional Python regex.
    @param[in] template Branch template using only slug, run_id and iid fields.
    @param[in] rule Optional repository naming regex; empty disables this check.
    @param[in] slug Effective agent slug from the selected configuration.
    @return Explicit sample identity, name, match result and closed issue codes.
    @note An example proves this identity only; it creates no branch or config.
          Regex execution is isolated and bounded to one second, failing closed.
    """
    result: dict[str, Any] = {"template": template, "rule": rule, "slug": slug,
                              "iid": 1, "run_id": "sample-run-1", "name": None,
                              "valid": False, "rule_matches": None, "issues": []}
    issues = result["issues"]
    if not isinstance(template, str) or not isinstance(slug, str):
        issues.append("invalid_template")
        return result
    if not isinstance(rule, str):
        issues.append("invalid_rule")
        return result
    if len(template) > 512 or len(rule) > 512 or len(slug) > 255:
        issues.append("too_long")
        return result
    try:
        names = []
        for _text, name, spec, conversion in Formatter().parse(template):
            if name is not None:
                if name not in ("slug", "run_id", "iid") or spec or conversion:
                    raise ValueError("unsupported branch field")
                names.append(name)
        if not {"iid", "run_id"}.intersection(names):
            issues.append("missing_identity")
        name = template.format(slug=slug, run_id=result["run_id"], iid=result["iid"])
    except (ValueError, KeyError, IndexError):
        issues.append("invalid_template")
        return result
    result["name"] = name
    if (not name or len(name) > 255 or name == "@" or name.startswith(("-", "/"))
            or name.endswith(("/", ".")) or any(part in name for part in ("..", "@{", "//"))
            or any(ord(char) <= 32 or ord(char) == 127 or char in "~^:?*[\\" for char in name)
            or any(part.startswith(".") or part.endswith(".lock") for part in name.split("/"))):
        issues.append("invalid_branch")
    if rule:
        try:
            re.compile(rule)
        except (re.error, RecursionError):
            issues.append("invalid_rule")
            return result
        # JSON on stdin keeps human regex/source out of executable Python text.
        code = ("import json,re,sys; rule,name=json.load(sys.stdin); "
                "print(json.dumps(re.match(rule,name) is not None))")
        try:
            checked = subprocess.run([sys.executable, "-I", "-c", code],
                                     input=json.dumps([rule, name]), capture_output=True,
                                     text=True, timeout=1)
            if checked.returncode != 0:
                raise ValueError("regex process failed")
            matched = json.loads(checked.stdout)
            if type(matched) is not bool:
                raise ValueError("invalid regex result")
            result["rule_matches"] = matched
            if not matched:
                issues.append("rule_mismatch")
        except subprocess.TimeoutExpired:
            issues.append("rule_timeout")
        except (OSError, ValueError):
            issues.append("rule_check_failed")
    result["valid"] = not issues
    return result


def _unknown_key_issues(raw: dict) -> list[str]:
    """
    @brief      Name every config.toml key this build does not read.
    @details    There is no compatibility while ADORE is in development: a key
                left by an earlier build is refused, not silently ignored.
                [local] and [execution] are checked by their own validators.
    @param[in]  raw Parsed config.toml mapping.
    @return     One issue per unknown key, naming the key to remove.
    """
    issues: list[str] = []

    def check(where: str, table: Any, cls: type) -> None:
        if not isinstance(table, dict):
            return
        allowed = {item.name for item in fields(cls)}
        for key in sorted(set(table) - allowed):
            issues.append(f"[{where}] unknown key {key!r}: remove it from config.toml")

    for name, cls in (
        ("agent", AgentConfig), ("platform", PlatformConfig), ("state", StateConfig),
        ("polling", PollingConfig), ("readiness", ReadinessConfig),
        ("clarification", ClarificationConfig), ("worktree", WorktreeConfig),
        ("workflow", WorkflowConfig), ("recovery", RecoveryConfig),
        ("budgets", BudgetsConfig), ("delivery", DeliveryConfig),
        ("review", ReviewConfig), ("reconcile", ReconcileConfig),
        ("metrics", MetricsConfig),
    ):
        check(name, raw.get(name), cls)
    labels = raw.get("labels")
    if isinstance(labels, dict):
        tables = {"lifecycle": LifecycleLabels, "selection": SelectionLabels,
                  "control": ControlLabels}
        for key in sorted(set(labels) - tables.keys()):
            issues.append(f"[labels] unknown key {key!r}: remove it from config.toml")
        for name, cls in tables.items():
            check(f"labels.{name}", labels.get(name), cls)
    # A table of a removed coding agent ([executor.<name>]) is a key of
    # [executor] here, so it is refused by name like any other key.
    check("executor", raw.get("executor"), ExecutorConfig)
    container = raw.get("container")
    if isinstance(container, dict):
        check("container", {key: value for key, value in container.items()
                            if key != "egress"}, ContainerConfig)
        check("container.egress", container.get("egress"), ContainerEgressConfig)
    return issues


def validate_config(config: Config) -> list[str]:
    """
    @brief      Validate a Config and return a list of human-readable issues.
    @details    Structural and cross-field checks per Configuration_Reference:
                enum values, positive bounds, parseable durations, and a
                Pi model and launch template. Run at startup so typos
                are caught before the poll loop starts.
    @param[in]  config The configuration to validate.
    @return     Empty list when valid; otherwise one message per issue.
    """
    issues: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            issues.append(message)

    for section in config.raw:
        check(section in KNOWN_SECTIONS, f"unknown section: [{section}]")
    issues.extend(_unknown_key_issues(config.raw))

    check(bool(config.agent.name.strip()), "[agent] name must not be empty")
    check(
        bool(_SLUG_RE.match(config.agent.slug)),
        f"[agent] slug must be lowercase alphanumeric/dash: {config.agent.slug!r}",
    )

    check(
        config.platform.kind in ("gitlab", "github", "gitea"),
        f'[platform] kind must be "gitlab", "github" or "gitea": '
        f"{config.platform.kind!r}",
    )
    check(bool(config.platform.repo.strip()), "[platform] repo is required")
    if config.platform.kind == "gitea":
        parts = config.platform.repo.split("/")
        check(
            len(parts) == 2 and all(part.strip() for part in parts),
            f"[platform] gitea repo must be OWNER/REPO (no subgroups): "
            f"{config.platform.repo!r}",
        )
    else:
        check(
            not config.platform.login,
            f"[platform] login is only supported for gitea, not "
            f"{config.platform.kind!r}",
        )

    check(
        config.polling.mode in ("loop", "once"),
        f"[polling] mode must be loop/once: {config.polling.mode!r}",
    )
    check(config.polling.poll_interval_seconds > 0, "[polling] poll_interval_seconds must be > 0")
    check(config.polling.poll_jitter_seconds >= 0, "[polling] poll_jitter_seconds must be >= 0")
    check(config.polling.max_concurrent_runs >= 1, "[polling] max_concurrent_runs must be >= 1")
    for window in config.polling.quiet_hours:
        check(
            bool(_QUIET_HOURS_RE.match(str(window))),
            f'[polling] quiet_hours entries must look like "22:00-06:00": {window!r}',
        )

    check(
        config.executor.mode in ("thick", "headless"),
        f"[executor] mode must be thick/headless: {config.executor.mode!r}",
    )
    check(
        not (_FORGE_CREDENTIAL_ENV & set(config.executor.env_keys)),
        "[executor] env_keys must not expose forge credentials to executors: "
        f"{sorted(_FORGE_CREDENTIAL_ENV & set(config.executor.env_keys))}",
    )
    command = config.executor.command
    issues.extend(_command_placeholder_issues(command))
    check(bool(command.strip()), "[executor] command is required")
    check(bool(config.executor.model.strip()), "[executor] model is required")
    check("{prompt}" in command, "[executor] command must contain a {prompt} placeholder")
    check(
        "--auto" not in command.split(),
        "[executor] command must not use --auto (it would auto-approve the "
        "push/pr/merge permissions that keep the executor off the remote)",
    )

    check(config.clarification.max_rounds >= 1, "[clarification] max_rounds must be >= 1")
    durations_ok = True
    for key in ("reminder_after", "answer_timeout"):
        try:
            parse_duration(getattr(config.clarification, key))
        except ValueError:
            durations_ok = False
            issues.append(
                f"[clarification] {key} is not a valid duration: "
                f"{getattr(config.clarification, key)!r}"
            )
    if durations_ok:
        check(config.clarification.answer_timeout_seconds() > 0,
              "[clarification] answer_timeout must be positive")
    check(
        config.clarification.timeout_state in ("failed", "stale"),
        f"[clarification] timeout_state must be failed/stale: "
        f"{config.clarification.timeout_state!r}",
    )

    runtime_tokens = config.container.runtime.split()
    check(
        bool(runtime_tokens) and runtime_tokens[-1] in ("docker", "podman"),
        "[container] runtime must be docker/podman, optionally wrapped "
        f'(e.g. "wsl -d Ubuntu-24.04 -- docker"): {config.container.runtime!r}',
    )
    for arg in config.container.run_args:
        check(
            isinstance(arg, str) and arg.startswith("-") and " " not in arg,
            "[container] run_args entries must be single option tokens "
            f'starting with "-" (e.g. "--userns=keep-id"): {arg!r}',
        )
    check(
        config.container.selinux_relabel in SELINUX_RELABEL_MODES,
        "[container] selinux_relabel must be "
        f"{'/'.join(SELINUX_RELABEL_MODES)} (the private SELinux `Z` label is "
        "not offered: it would lock the shared repository clone to one "
        f"container): {config.container.selinux_relabel!r}",
    )
    check(
        isinstance(config.container.runtime_env, dict),
        "[container] runtime_env must be a TOML inline table or section",
    )
    if isinstance(config.container.runtime_env, dict):
        for key, value in config.container.runtime_env.items():
            check(
                isinstance(key, str) and bool(key.strip()),
                "[container] runtime_env keys must be non-empty strings",
            )
            check(
                isinstance(value, str),
                f"[container] runtime_env.{key} must be a string",
            )
            check(
                key not in _MANAGED_CONTAINER_ENV,
                f"[container] runtime_env.{key} is managed by ADORE and cannot be overridden",
            )
            check(
                not str(key).upper().startswith(REMOVED_AGENT_ENV_PREFIXES),
                f"[container] runtime_env.{key} configures a removed coding agent: "
                "remove it from config.toml",
            )
    check(
        isinstance(config.container.required_tool_checks, list),
        "[container] required_tool_checks must be a list of command strings",
    )
    if isinstance(config.container.required_tool_checks, list):
        for check_cmd in config.container.required_tool_checks:
            if not isinstance(check_cmd, str):
                issues.append(
                    f"[container] required_tool_checks entries must be strings: {check_cmd!r}"
                )
                continue
            stripped = check_cmd.strip()
            if not stripped:
                issues.append("[container] required_tool_checks entries must not be empty")
                continue
            if any(char in stripped for char in _SHELL_CONTROL_CHARS):
                issues.append(
                    "[container] required_tool_checks entries must be simple commands "
                    f"without shell control characters: {check_cmd!r}"
                )
                continue
            try:
                parts = shlex.split(stripped)
            except ValueError as exc:
                issues.append(
                    f"[container] required_tool_checks entry is not parseable: "
                    f"{check_cmd!r} ({exc})"
                )
                continue
            if not parts:
                issues.append("[container] required_tool_checks entries must not be empty")
                continue
            if parts[0].startswith("-"):
                issues.append(
                    "[container] required_tool_checks command must start with a tool name: "
                    f"{check_cmd!r}"
                )
    check(
        config.container.parked_ttl_mode in ("seconds", "polls"),
        f"[container] parked_ttl_mode must be seconds/polls: "
        f"{config.container.parked_ttl_mode!r}",
    )
    check(config.execution.backend in ("container", "local"),
          "[execution] backend must be container/local")
    local = config.local
    if "local" in config.raw:
        declaration = config.raw["local"]
        check(isinstance(declaration, dict), "[local] must be a table")
        if isinstance(declaration, dict):
            for key in set(declaration) - {item.name for item in fields(LocalConfig)}:
                issues.append(f"[local] unknown field: {key}")
    for key in ("account", "home", "path", "cgroup_root"):
        value = getattr(local, key)
        check(isinstance(value, str) and not any(ord(c) < 32 for c in value),
              f"[local] {key} must be plain text")
    check(bool(local.account), "[local] account is required")
    check(isinstance(local.environment, dict), "[local] environment must be a table")
    if isinstance(local.environment, dict):
        for key, value in local.environment.items():
            check(isinstance(key, str) and not re.search(
                r"(?:^|_)(?:TOKEN|SECRET|PASSWORD|API_KEY|PRIVATE_KEY)$", key.upper()),
                "[local] secret values belong in approved executor env_keys, not environment")
            check(isinstance(key, str) and bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key))
                  and isinstance(value, str) and "\x00" not in value,
                  "[local] environment requires plain string names/values")
            check(isinstance(key, str) and key.upper() not in _FORGE_CREDENTIAL_ENV | {
                "HOME", "USERPROFILE", "PATH", "SYSTEMROOT", "COMSPEC", "USERNAME",
                "USER", "LOGNAME", "GIT_DIR", "GIT_WORK_TREE", "PYTHONPATH",
            }, "[local] environment cannot override managed account or forge variables")
            check(not str(key).upper().startswith(REMOVED_AGENT_ENV_PREFIXES),
                  f"[local] environment.{key} configures a removed coding agent: "
                  "remove it from config.toml")
    if config.execution.backend == "local":
        check(not config.execution.preparation, "[local] container preparation is unsupported")
        check(config.container.egress.mode == "open", "[local] container egress must be open")
        check(not config.container.run_args and not config.container.required_tool_checks
              and config.container.selinux_relabel == "off",
              "[local] container runtime options/tool checks are unsupported")
        check(config.container.runtime_env == ContainerConfig().runtime_env,
              "[local] configure environment in [local], not [container] runtime_env")
        try:
            tokens = shlex.split(config.executor.command)
            check(not any(token in {"&&", "||", ";", "|", ">", "<", "&"} for token in tokens),
                  "[local] executor command must be argv without shell compounds")
        except ValueError:
            issues.append("[local] executor command is invalid")
    if "execution" in config.raw:
        declaration = config.raw["execution"]
        check(isinstance(declaration, dict), "[execution] must be a table")
        if isinstance(declaration, dict):
            for key in set(declaration) - {item.name for item in fields(ExecutionConfig)}:
                issues.append(f"[execution] unknown field: {key}")
    if not isinstance(config.execution.preparation, str):
        issues.append("[execution] preparation must be text")
    elif config.execution.preparation:
        from adore.preparation import PreparationError, parse_selection

        try:
            parse_selection(config.execution.preparation)
        except PreparationError as exc:
            issues.append(f"[execution] preparation: {exc}")
    for key, maximum in (("preparation_step_timeout_seconds", 1800),
                         ("preparation_total_timeout_seconds", 3600),
                         ("preparation_max_attempts", 3)):
        value = getattr(config.execution, key)
        check(type(value) is int and 1 <= value <= maximum,
              f"[execution] {key} must be an integer in 1..{maximum}")
    check(config.execution.backend == "local" or bool(config.container.image.strip())
          or bool(config.execution.preparation),
          "[container] image is required without preparation")
    egress = config.container.egress
    check(
        egress.mode in ("open", "allowlist-proxy", "none"),
        f'[container.egress] mode must be "open", "allowlist-proxy", or "none": '
        f"{egress.mode!r}",
    )
    check(
        isinstance(egress.allowlist, list),
        "[container.egress] allowlist must be a list of hostnames",
    )
    if isinstance(egress.allowlist, list):
        if egress.mode == "allowlist-proxy":
            check(
                bool(egress.allowlist),
                "[container.egress] allowlist-proxy requires a non-empty allowlist",
            )
        for item in egress.allowlist:
            if not isinstance(item, str):
                issues.append(
                    f"[container.egress] allowlist entries must be strings: {item!r}"
                )
                continue
            value = item.strip()
            if (
                not value
                or value != item
                or "://" in value
                or "/" in value
                or "\\" in value
                or any(char.isspace() for char in value)
                or any(char in value for char in _SHELL_CONTROL_CHARS)
                or not _valid_hostname_pattern(value)
            ):
                issues.append(
                    "[container.egress] allowlist entries must be exact or wildcard "
                    f"hostnames only: {item!r}"
                )
    check(
        isinstance(egress.no_proxy, list),
        "[container.egress] no_proxy must be a list of hostnames",
    )
    if isinstance(egress.no_proxy, list):
        for item in egress.no_proxy:
            if not isinstance(item, str):
                issues.append(
                    f"[container.egress] no_proxy entries must be strings: {item!r}"
                )
                continue
            value = item.strip()
            if (
                not value
                or value != item
                or "://" in value
                or "/" in value
                or "\\" in value
                or any(char.isspace() for char in value)
                or any(char in value for char in _SHELL_CONTROL_CHARS)
                or not _valid_no_proxy_entry(value)
            ):
                issues.append(
                    "[container.egress] no_proxy entries must be safe hostnames "
                    f"or loopback values: {item!r}"
                )
    check(
        isinstance(egress.proxy_port, int) and 0 < egress.proxy_port < 65536,
        "[container.egress] proxy_port must be 1-65535",
    )
    check(
        isinstance(egress.proxy_image, str) and bool(egress.proxy_image.strip()),
        "[container.egress] proxy_image is required",
    )
    check(
        isinstance(egress.network_prefix, str)
        and bool(re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", egress.network_prefix)),
        "[container.egress] network_prefix must contain only letters, digits, dot, "
        "underscore, or dash",
    )

    check(
        bool(config.worktree.repo_path.strip()),
        "[worktree] repo_path is required (local clone the run worktrees are created from)",
    )
    check(bool(config.worktree.root.strip()), "[worktree] root must not be empty")
    branch = branch_naming_preview(config.worktree.branch_template,
                                   config.worktree.branch_rule, config.agent.slug)
    branch_messages = {
        "missing_identity": "branch_template must contain {run_id} or {iid}",
        "invalid_template": ("branch_template accepts only {slug}, {run_id}, {iid} "
                             "without format modifiers"),
        "invalid_branch": "branch_template renders an invalid Git branch name",
        "invalid_rule": "branch_rule is not a valid regex",
        "rule_mismatch": "branch_template renders a name the repo push rule would REJECT",
        "rule_timeout": "branch_rule evaluation exceeded one second",
        "rule_check_failed": "branch_rule evaluation failed",
        "too_long": "branch_template and branch_rule must be at most 512 characters",
    }
    issues.extend("[worktree] " + branch_messages[code] for code in branch["issues"])

    workflow = config.workflow
    check(
        workflow.default_kind in RUN_KINDS,
        f"[workflow] default_kind must be one of {', '.join(RUN_KINDS)}: "
        f"{workflow.default_kind!r}",
    )
    check(
        isinstance(workflow.kind_labels, dict),
        "[workflow] kind_labels must be a table of label -> AEGIS task type",
    )
    if isinstance(workflow.kind_labels, dict):
        for label, kind in workflow.kind_labels.items():
            if not isinstance(label, str) or not label.strip():
                issues.append("[workflow] kind_labels keys must be non-empty "
                              "label names")
                continue
            if not isinstance(kind, str) or kind not in RUN_KINDS:
                issues.append(
                    f"[workflow] kind_labels.{label} must name an AEGIS run "
                    f"kind ({', '.join(RUN_KINDS)}): {kind!r}"
                )
                continue
    check(
        isinstance(workflow.quick_label, str),
        "[workflow] quick_label must be a label name or an empty string",
    )
    check(
        isinstance(workflow.aegis_python, str)
        and bool(workflow.aegis_python.strip())
        and (config.execution.backend == "local"
             or not any(char.isspace() for char in workflow.aegis_python))
        and not any(char in workflow.aegis_python for char in "\x00\r\n"),
        "[workflow] aegis_python must be one executable token",
    )
    check(
        isinstance(workflow.stage_timeout_overrides, dict),
        "[workflow] stage_timeout_overrides must be a table of stage -> seconds",
    )
    if isinstance(workflow.stage_timeout_overrides, dict):
        for stage, seconds in workflow.stage_timeout_overrides.items():
            if not isinstance(stage, str) or stage not in AEGIS_STAGES:
                issues.append(
                    f"[workflow] stage_timeout_overrides.{stage} is not an "
                    f"AEGIS stage ({', '.join(AEGIS_STAGES)})"
                )
                continue
            if not isinstance(seconds, int) or isinstance(seconds, bool) \
                    or seconds < 1:
                issues.append(
                    f"[workflow] stage_timeout_overrides.{stage} must be a "
                    f"positive whole number of seconds: {seconds!r}"
                )

    recovery = config.recovery
    check(
        isinstance(recovery.max_stage_failures, int)
        and not isinstance(recovery.max_stage_failures, bool)
        and recovery.max_stage_failures >= 1,
        "[recovery] max_stage_failures must be >= 1",
    )
    check(
        isinstance(recovery.max_transient_retries, int)
        and not isinstance(recovery.max_transient_retries, bool)
        and recovery.max_transient_retries >= 1,
        "[recovery] max_transient_retries must be >= 1",
    )
    check(
        isinstance(recovery.retry_backoff_seconds, list)
        and bool(recovery.retry_backoff_seconds),
        "[recovery] retry_backoff_seconds must be a non-empty integer list",
    )
    if isinstance(recovery.retry_backoff_seconds, list):
        for value in recovery.retry_backoff_seconds:
            check(
                isinstance(value, int) and not isinstance(value, bool) and value >= 0,
                f"[recovery] retry_backoff_seconds entries must be >= 0: {value!r}",
            )
    check(config.budgets.max_iterations >= 1, "[budgets] max_iterations must be >= 1")
    check(
        config.budgets.max_wall_clock_seconds >= 1,
        "[budgets] max_wall_clock_seconds must be >= 1",
    )
    check(
        config.budgets.per_gate_timeout_seconds >= 1,
        "[budgets] per_gate_timeout_seconds must be >= 1",
    )
    cost_cap = config.budgets.max_cost_usd
    check(
        isinstance(cost_cap, (int, float)) and not isinstance(cost_cap, bool)
        and cost_cap >= 0
        and (not isinstance(cost_cap, float) or math.isfinite(cost_cap)),
        "[budgets] max_cost_usd must be a finite nonnegative number (0 disables the cap)",
    )
    check(config.budgets.max_files_touched >= 1, "[budgets] max_files_touched must be >= 1")

    check(bool(config.delivery.target_branch.strip()), "[delivery] target_branch is required")
    check(
        type(config.delivery.publish_checkpoints) is bool,
        "[delivery] publish_checkpoints must be a boolean",
    )
    check(valid_reviewers(config.delivery.reviewers),
          "[delivery] reviewers must list valid human account names (empty requests no review)")
    check(type(config.delivery.draft) is bool, "[delivery] draft must be a boolean")
    check(
        type(config.delivery.remove_source_branch) is bool,
        "[delivery] remove_source_branch must be a boolean",
    )
    check(
        isinstance(config.delivery.approval_label, str)
        and bool(config.delivery.approval_label.strip()),
        "[delivery] approval_label must be a non-empty label",
    )
    lifecycle_labels = set(asdict(config.labels.lifecycle).values())
    control_labels = set(asdict(config.labels.control).values())
    check(
        config.delivery.approval_label not in lifecycle_labels | control_labels,
        "[delivery] approval_label must be distinct from lifecycle/control labels",
    )

    check(
        config.review.trigger == "label",
        f"[review] trigger must be label in ADORE: {config.review.trigger!r}",
    )
    check(config.review.max_review_rounds >= 1, "[review] max_review_rounds must be >= 1")
    check(
        config.review.on_pipeline_failure in ("revise", "notify", "ignore"),
        "[review] on_pipeline_failure must be revise/notify/ignore: "
        f"{config.review.on_pipeline_failure!r}",
    )

    check(
        config.reconcile.on_ticket_deleted in ("abort-cleanup", "ignore"),
        f"[reconcile] on_ticket_deleted must be abort-cleanup/ignore: "
        f"{config.reconcile.on_ticket_deleted!r}",
    )
    check(
        config.reconcile.on_ticket_closed in ("cancel", "ignore"),
        f"[reconcile] on_ticket_closed must be cancel/ignore: "
        f"{config.reconcile.on_ticket_closed!r}",
    )
    check(
        config.reconcile.on_trigger_removed in ("pause", "abort", "ignore"),
        f"[reconcile] on_trigger_removed must be pause/abort/ignore: "
        f"{config.reconcile.on_trigger_removed!r}",
    )

    check(
        type(config.metrics.capture_tokens) is bool,
        "[metrics] capture_tokens must be a boolean",
    )
    if config.metrics.enabled:
        check(bool(config.metrics.db_path.strip()), "[metrics] db_path is required when enabled")

    return issues


# END OF FILE
