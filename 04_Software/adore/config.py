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
@author Eng. Dan Dumitru Pasare
@date 2026-07-07
@version 0.3.0
"""

from __future__ import annotations

# IMPORTS
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
import re
import shlex
import tomllib
from typing import Any

from adore.branding import (
    EGRESS_NETWORK_PREFIX,
    EGRESS_PROXY_IMAGE,
    EXECUTOR_BASE_IMAGE,
    NPM_CACHE_VOLUME,
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
    "CODEX_HOME",
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
        "clarification",
        "container",
        "worktree",
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
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.2
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
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-29
    @version 0.1.1
    """

    kind: str = "gitlab"
    repo: str = ""
    login: str = ""


@dataclass
class StateConfig:
    """
    @brief   [state] - how run state is signaled on the ticket.
    @details The status comment is always one comment edited in place; there
             is no per-change mode.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-05
    @version 0.2.0
    """

    channel: str = "comments"
    store_root: str = ""


@dataclass
class PollingConfig:
    """
    @brief   [polling] - poll loop cadence and concurrency.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
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
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    require_acceptance_criteria: bool = True
    require_priority_label: bool = True
    require_known_component: bool = True
    max_scope_hint: str = "small"


@dataclass
class LifecycleLabels:
    """
    @brief   [labels.lifecycle] - orchestrator-managed run-state labels.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
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
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
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
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-02
        @version 0.1.0
        """
        return [self.priority_high, self.priority_medium, self.priority_low]


@dataclass
class ControlLabels:
    """
    @brief   [labels.control] - human overrides checked before eligibility.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    hold: str = "agent-hold"
    exclude: str = "no-agent"


@dataclass
class ExecutorLabels:
    """
    @brief   [labels.executor] - optional per-ticket executor pin.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    prefix: str = "agent-exec:"


@dataclass
class LabelsConfig:
    """
    @brief   [labels.*] - all label categories; roles, never hard-coded strings.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    lifecycle: LifecycleLabels = field(default_factory=LifecycleLabels)
    selection: SelectionLabels = field(default_factory=SelectionLabels)
    control: ControlLabels = field(default_factory=ControlLabels)
    executor: ExecutorLabels = field(default_factory=ExecutorLabels)


@dataclass
class ExecutorCommand:
    """
    @brief   One [executor.<name>] entry: command template plus model.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    command: str = ""
    model: str = ""


@dataclass
class ExecutorConfig:
    """
    @brief   [executor] - which executor to launch and how.
    @details env_keys names the secret subset injected into the container
             (from the environment / .env); only these keys ever reach the
             executor (design 12b: scope minimally). stage_host_auth copies
             the HOST's opencode auth.json into the run container at
             provision - a pilot-only bridge for OAuth (ChatGPT-account)
             sessions that have no API key (Security_And_Credentials.md);
             production should use a real provider key instead.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.2
    """

    default: str = "opencode"
    mode: str = "thick"
    questions_file: str = ""
    env_keys: list[str] = field(
        default_factory=lambda: ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    )
    stage_host_auth: bool = False
    commands: dict[str, ExecutorCommand] = field(default_factory=dict)


@dataclass
class ContainerEgressConfig:
    """
    @brief   [container.egress] - outbound network policy for executor runs.
    @details open provides unrestricted egress; none disables container
             networking; allowlist-proxy routes HTTP/HTTPS through a per-run
             ADORE proxy with exact/wildcard hostname allowlists.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-07
    @version 0.1.1
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
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    max_rounds: int = 3
    reminder_after: str = "24h"
    answer_timeout: str = "72h"
    timeout_state: str = "failed"

    def reminder_after_seconds(self) -> int:
        """
        @brief   The reminder delay parsed to seconds.
        @return  Seconds after parked_at before the single nudge.
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-02
        @version 0.1.0
        """
        return parse_duration(self.reminder_after)

    def answer_timeout_seconds(self) -> int:
        """
        @brief   The hard answer timeout parsed to seconds.
        @return  Seconds after parked_at before the run is released.
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-02
        @version 0.1.0
        """
        return parse_duration(self.answer_timeout)


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
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-07
    @version 0.5.1
    """

    runtime: str = "docker"
    image: str = EXECUTOR_BASE_IMAGE
    keep_parked: bool = True
    parked_ttl_mode: str = "polls"
    parked_ttl_seconds: int = 7200
    parked_ttl_polls: int = 30
    parked_state: str = "stopped"
    uv_cache_volume: str = UV_CACHE_VOLUME
    npm_cache_volume: str = NPM_CACHE_VOLUME
    run_args: list[str] = field(default_factory=list)
    runtime_env: dict[str, str] = field(default_factory=lambda: {"UV_LINK_MODE": "copy"})
    required_tool_checks: list[str] = field(default_factory=list)
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
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.2
    """

    repo_path: str = ""
    root: str = "worktrees"
    branch_template: str = "{slug}/{run_id}"
    branch_rule: str = ""


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
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-24
    @version 0.2.0
    """

    max_iterations: int = 20
    max_wall_clock_seconds: int = 3600
    per_gate_timeout_seconds: int = 1800
    max_cost_usd: float = 5.0
    max_files_touched: int = 40


@dataclass
class DeliveryConfig:
    """
    @brief   [delivery] - draft MR/PR boundary; never merges.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    target_branch: str = "develop"
    draft: bool = True
    reviewers: list[str] = field(default_factory=list)
    remove_source_branch: bool = True


@dataclass
class ReviewConfig:
    """
    @brief   [review] - post-MR revise loop trigger and bounds.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    trigger: str = "label"
    revise_label: str = "agent-revise"
    max_review_rounds: int = 3
    review_reminder_after: str = "48h"


@dataclass
class ReconcileConfig:
    """
    @brief   [reconcile] - reactions to external ticket changes.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    on_ticket_deleted: str = "abort-cleanup"
    on_ticket_closed: str = "cancel"
    on_trigger_removed: str = "pause"


@dataclass
class MetricsConfig:
    """
    @brief   [metrics] - stdlib-only statistics capture.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
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
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.1
    """

    agent: AgentConfig = field(default_factory=AgentConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)
    state: StateConfig = field(default_factory=StateConfig)
    polling: PollingConfig = field(default_factory=PollingConfig)
    readiness: ReadinessConfig = field(default_factory=ReadinessConfig)
    labels: LabelsConfig = field(default_factory=LabelsConfig)
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)
    clarification: ClarificationConfig = field(default_factory=ClarificationConfig)
    container: ContainerConfig = field(default_factory=ContainerConfig)
    worktree: WorktreeConfig = field(default_factory=WorktreeConfig)
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
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-02
        @version 0.1.1
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
                "clarification",
                "container",
                "worktree",
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
    @details    Unknown keys are ignored here (reported by validate_config);
                known keys override the documented defaults.
    @param[in]  cls The section dataclass type.
    @param[in]  data Raw mapping from tomllib (or anything else -> defaults).
    @return     A populated section instance.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    if not isinstance(data, dict):
        return LabelsConfig()
    return LabelsConfig(
        lifecycle=_build_section(LifecycleLabels, data.get("lifecycle")),
        selection=_build_section(SelectionLabels, data.get("selection")),
        control=_build_section(ControlLabels, data.get("control")),
        executor=_build_section(ExecutorLabels, data.get("executor")),
    )


def _build_executor(data: Any) -> ExecutorConfig:
    """
    @brief      Build [executor] including the per-executor command tables.
    @details    Scalar keys configure the launcher; every dict-valued key is an
                [executor.<name>] command/model entry.
    @param[in]  data Raw [executor] mapping.
    @return     A populated ExecutorConfig.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    if not isinstance(data, dict):
        return ExecutorConfig()
    scalars = {key: value for key, value in data.items() if not isinstance(value, dict)}
    section = _build_section(ExecutorConfig, scalars)
    section.commands = {
        name: _build_section(ExecutorCommand, table)
        for name, table in data.items()
        if isinstance(table, dict)
    }
    return section


def _build_container(data: Any) -> ContainerConfig:
    """
    @brief      Build [container] including the nested [container.egress].
    @param[in]  data Raw [container] mapping.
    @return     A populated ContainerConfig.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-07
    @version    0.1.0
    """
    if not isinstance(data, dict):
        return ContainerConfig()
    scalars = {key: value for key, value in data.items() if key != "egress"}
    section = _build_section(ContainerConfig, scalars)
    section.egress = _build_section(ContainerEgressConfig, data.get("egress"))
    return section


def _valid_hostname_pattern(value: str) -> bool:
    """
    @brief      Check an egress allowlist hostname or leading wildcard.
    @param[in]  value Hostname pattern, optionally starting with "*.".
    @return     True when the pattern is syntactically safe.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-07
    @version    0.1.0
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-07
    @version    0.1.1
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.2
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


def load_config(path: str | Path) -> Config:
    """
    @brief      Load configuration from a TOML file into typed sections.
    @details    Lenient by design: unknown keys are skipped and missing keys
                default, so `adore config validate` can report all problems in
                one pass instead of dying on the first.
    @param[in]  path Path to config.toml.
    @return     A populated Config instance.
    @exception  FileNotFoundError When the file does not exist.
    @exception  tomllib.TOMLDecodeError When the file is not valid TOML.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-07
    @version    0.1.2
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
        executor=_build_executor(raw.get("executor")),
        clarification=_build_section(ClarificationConfig, raw.get("clarification")),
        container=_build_container(raw.get("container")),
        worktree=_build_section(WorktreeConfig, raw.get("worktree")),
        budgets=_build_section(BudgetsConfig, raw.get("budgets")),
        delivery=_build_section(DeliveryConfig, raw.get("delivery")),
        review=_build_section(ReviewConfig, raw.get("review")),
        reconcile=_build_section(ReconcileConfig, raw.get("reconcile")),
        metrics=_build_section(MetricsConfig, raw.get("metrics")),
        raw=raw,
    )
    _derive_names(config)
    return config


def validate_config(config: Config) -> list[str]:
    """
    @brief      Validate a Config and return a list of human-readable issues.
    @details    Structural and cross-field checks per Configuration_Reference:
                enum values, positive bounds, parseable durations, and a
                matching [executor.<default>] entry. Run at startup so typos
                are caught before the poll loop starts.
    @param[in]  config The configuration to validate.
    @return     Empty list when valid; otherwise one message per issue.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.1.10
    """
    issues: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            issues.append(message)

    for section in config.raw:
        check(section in KNOWN_SECTIONS, f"unknown section: [{section}]")

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
        config.state.channel in ("comments", "labels", "both"),
        f"[state] channel must be comments/labels/both: {config.state.channel!r}",
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
    default = config.executor.default
    entry = config.executor.commands.get(default)
    if entry is None:
        issues.append(f"[executor] default {default!r} has no [executor.{default}] table")
    else:
        check(bool(entry.command.strip()), f"[executor.{default}] command is required")
        check(bool(entry.model.strip()), f"[executor.{default}] model is required")
        check(
            "{prompt}" in entry.command,
            f"[executor.{default}] command must contain a {{prompt}} placeholder",
        )
        check(
            "--auto" not in entry.command.split(),
            f"[executor.{default}] command must not use --auto (it would "
            "auto-approve the push/pr/merge permissions that keep the "
            "executor off the remote)",
        )
        if default == "codex":
            command = entry.command
            check(
                "--json" in command
                and (
                    "--sandbox workspace-write" in command
                    or "--dangerously-bypass-approvals-and-sandbox" in command
                    or "--full-auto" in command
                ),
                "[executor.codex] command must run non-interactively: add "
                "--json with --sandbox workspace-write, --full-auto, or "
                "--dangerously-bypass-approvals-and-sandbox so Codex does not "
                "block waiting for approval headless",
            )
            check(
                "--ignore-user-config" in command.split(),
                "[executor.codex] command must include --ignore-user-config so "
                "headless runs use ADORE's staged CODEX_HOME instead of a "
                "machine-local desktop config/plugin state",
            )
            check(
                "--disable plugins" in command,
                "[executor.codex] command must include --disable plugins so "
                "Codex does not materialize its bundled plugin marketplace "
                "inside the target worktree",
            )
        if default == "qwen":
            command = entry.command
            check(
                "--yolo" not in command.split() and "--approval-mode yolo" not in command,
                "[executor.qwen] command must not use --yolo / --approval-mode yolo "
                "(auto-approves all tools; rely on the .qwen deny-hooks + "
                "container isolation)",
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
        # a reminder that fires at or after the hard timeout can never nudge
        # before the run is released - reject the ordering, not just the format
        check(
            config.clarification.reminder_after_seconds()
            < config.clarification.answer_timeout_seconds(),
            "[clarification] reminder_after must be shorter than answer_timeout",
        )
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
    check(
        config.container.parked_state in ("stopped", "removed"),
        f"[container] parked_state must be stopped/removed: {config.container.parked_state!r}",
    )
    check(bool(config.container.image.strip()), "[container] image is required")
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
    check(
        "{run_id}" in config.worktree.branch_template
        or "{iid}" in config.worktree.branch_template,
        "[worktree] branch_template must contain {run_id} or {iid} so branches "
        f"stay unique per ticket: {config.worktree.branch_template!r}",
    )
    if config.worktree.branch_rule:
        sample = config.worktree.branch_template.format(
            slug=config.agent.slug, run_id="sample-run-1", iid=1
        )
        try:
            rule = re.compile(config.worktree.branch_rule)
        except re.error as exc:
            issues.append(f"[worktree] branch_rule is not a valid regex: {exc}")
        else:
            check(
                rule.match(sample) is not None,
                f"[worktree] branch_template renders {sample!r}, which the "
                f"repo push rule {config.worktree.branch_rule!r} would REJECT",
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
    check(config.budgets.max_cost_usd > 0, "[budgets] max_cost_usd must be > 0")
    check(config.budgets.max_files_touched >= 1, "[budgets] max_files_touched must be >= 1")

    check(bool(config.delivery.target_branch.strip()), "[delivery] target_branch is required")
    check(bool(config.delivery.reviewers), "[delivery] reviewers must list at least one human")
    check(config.delivery.draft, "[delivery] draft must stay true: ADORE never opens ready MRs")

    check(
        config.review.trigger in ("label", "comment-marker", "auto"),
        f"[review] trigger must be label/comment-marker/auto: {config.review.trigger!r}",
    )
    check(config.review.max_review_rounds >= 1, "[review] max_review_rounds must be >= 1")

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

    if config.metrics.enabled:
        check(bool(config.metrics.db_path.strip()), "[metrics] db_path is required when enabled")

    return issues


# END OF FILE
