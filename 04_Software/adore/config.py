"""Load and validate ADORE configuration from config.toml."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
import json
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
    PRODUCT_ACRONYM,
    PRODUCT_SLUG,
    UV_CACHE_VOLUME,
)
from adore.build_bundle import BuildBundleError, definition_parts
from adore.pi_providers import (
    CUSTOM,
    DEFAULT_ENDPOINT_API,
    ENDPOINT_APIS,
    MODEL_ID_RE,
    WEB_SEARCH_CHOICES,
    CatalogError,
    provider_hosts,
    provider_ids,
    thinking_levels,
    valid_endpoint_url,
)
from adore.setting_rules import (
    MAX_REVIEWERS,
    numeric_default,
    numeric_domain,
    numeric_issues,
    valid_collection,
    valid_label,
    valid_numeric,
)
from adore.util import (
    automatic_environment,
    background_process_options,
    parse_duration,
)

# 24:00 stays valid as "until midnight"; 99:99 never named a time.
_QUIET_TIME = r"(?:(?:[01]\d|2[0-3]):[0-5]\d|24:00)"
_QUIET_HOURS_RE = re.compile(rf"^{_QUIET_TIME}-{_QUIET_TIME}$")
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
#: Every variable a forge CLI reads a credential from. One list serves both the
#: `env_keys` refusal here and the scrubbing of forge CLI environments, so a
#: name known to one cannot be missing from the other.
FORGE_CREDENTIAL_ENV = frozenset({
    "AZURE_DEVOPS_EXT_PAT", "AZURE_DEVOPS_EXT_PAT_VAR", "AZURE_CONFIG_DIR",
    "GITHUB_TOKEN", "GH_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN",
    "GITLAB_TOKEN", "GLAB_TOKEN", "GITLAB_ACCESS_TOKEN", "OAUTH_TOKEN",
    "GITEA_TOKEN", "TEA_TOKEN",
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
        "metrics",
    }
)


@dataclass
class AgentConfig:
    """
    [agent] - bot identity; the slug derives every local name.
    email is the git commit author email used inside the executor
             container (Security_And_Credentials.md); derived from the
             slug when empty.
    """

    name: str = PRODUCT_ACRONYM
    slug: str = ""
    email: str = ""


@dataclass
class PlatformConfig:
    """
    [platform] - which Git-platform adapter and repository to use.
    `login` names the tea login (`tea logins list`) for kind
             "gitea", where one CLI can hold several instance/account logins;
             empty uses tea's default login. Meaningless for glab/gh (their
             auth binds to the host), so validation rejects it there.
    """

    kind: str = "gitlab"
    repo: str = ""
    login: str = ""
    organization: str = ""
    project: str = ""
    area_path: str = ""
    work_item_types: list[str] = field(default_factory=lambda: [
        "Bug", "Task", "Issue", "User Story", "Product Backlog Item", "Requirement"])
    closed_states: list[str] = field(default_factory=lambda: ["Closed", "Done", "Removed"])


@dataclass
class StateConfig:
    """
    [state] - where run state lives.
    The status comment is always one comment edited in place, with the
             lifecycle labels; there is no per-change mode.
    """

    store_root: str = ""


@dataclass
class PollingConfig:
    """[polling] - poll loop cadence and concurrency."""

    mode: str = "loop"
    poll_interval_seconds: int = numeric_default("polling.poll_interval_seconds")
    poll_jitter_seconds: int = numeric_default("polling.poll_jitter_seconds")
    poll_backoff: bool = True
    max_concurrent_runs: int = numeric_default("polling.max_concurrent_runs")
    quiet_hours: list[str] = field(default_factory=list)


@dataclass
class ReadinessConfig:
    """[readiness] - selection filter applied after eligibility."""

    require_acceptance_criteria: bool = False
    require_priority_label: bool = True


@dataclass
class LifecycleLabels:
    """[labels.lifecycle] - orchestrator-managed run-state labels."""

    ready: str = "agent-ready"
    working: str = "agent-working"
    clarify: str = "agent-clarify"
    answered: str = "agent-answered"
    review: str = "agent-mr"
    failed: str = "agent-failed"
    done: str = "agent-done"


@dataclass
class SelectionLabels:
    """[labels.selection] - human-managed priority/type labels."""

    priority_high: str = "P1"
    priority_medium: str = "P2"
    priority_low: str = "P3"
    type_feature: str = "feature"
    type_bug: str = "bug"
    type_epic: str = "epic"

    def priority_order(self) -> list[str]:
        """
        Priority labels from highest to lowest.
        Returns: Ordered label list used for queue ranking.
        """
        return [self.priority_high, self.priority_medium, self.priority_low]


@dataclass
class ControlLabels:
    """[labels.control] - human overrides checked before eligibility."""

    hold: str = "agent-hold"
    exclude: str = "no-agent"


@dataclass
class LabelsConfig:
    """[labels.*] - all label categories; roles, never hard-coded strings."""

    lifecycle: LifecycleLabels = field(default_factory=LifecycleLabels)
    selection: SelectionLabels = field(default_factory=SelectionLabels)
    control: ControlLabels = field(default_factory=ControlLabels)


@dataclass
class ExecutorEndpointConfig:
    """
    [executor.endpoint] - an OpenAI-compatible endpoint for `provider = "custom"`.
    `base_url` is the address as seen from where Pi runs (inside the
             container); `api` is the Pi API type the endpoint speaks. Its
             optional key is a credential (ADORE_ENDPOINT_API_KEY), never a
             value here.
    """

    base_url: str = ""
    api: str = DEFAULT_ENDPOINT_API


@dataclass
class ExecutorWebConfig:
    """
    [executor.web] - the web search Pi uses while internet access is on.
    `search` is exa (no key), brave or tavily (key in the project's
             credential store as BRAVE_API_KEY or TAVILY_API_KEY) or none (no
             web tools; downloads through bash still work).
    """

    search: str = "exa"


@dataclass
class ExecutorConfig:
    """
    [executor] - how ADORE launches Pi, its only coding agent.
    `provider` is a Pi API-key provider id, `chatgpt` or `custom`
             (an OpenAI-compatible endpoint described by [executor.endpoint]);
             `model` is the model id within that provider. `internet` is the
             project's "Internet access for the agent": false limits a
             container run to the model provider's hosts, true opens the
             network and loads Pi's web tools ([executor.web]). Native runs use managed
             Pi RPC. Container runs use the image's pinned Pi. The provider's key
             variable always reaches Pi; env_keys names additional secrets
             injected into the executor (from the environment / .env); only
             these keys ever reach it (design 12b: scope minimally).
    """

    provider: str = ""
    model: str = ""
    thinking: str = ""
    internet: bool = False
    endpoint: ExecutorEndpointConfig = field(default_factory=ExecutorEndpointConfig)
    web: ExecutorWebConfig = field(default_factory=ExecutorWebConfig)
    questions_file: str = ""
    env_keys: list[str] = field(default_factory=list)


@dataclass
class ContainerEgressConfig:
    """
    [container.egress] - the proxy behind which an internet-off run sits.
    `[executor] internet` decides the run's network access
             (`egress_policy`); this section holds the per-run proxy's image,
             port and network prefix, the hosts reached without the proxy and
             `allowlist`, extra hosts an internet-off run may reach besides
             the model provider (exact names or `*.` wildcards).
    """

    allowlist: list[str] = field(default_factory=list)
    no_proxy: list[str] = field(default_factory=lambda: ["localhost", "127.0.0.1", "::1"])
    proxy_image: str = EGRESS_PROXY_IMAGE
    proxy_port: int = numeric_default("container.egress.proxy_port")
    network_prefix: str = EGRESS_NETWORK_PREFIX


@dataclass
class EgressPolicy:
    """
    The network access of one run's executor container.
    Derived from the configuration by `egress_policy`, never read
             from a file. open: unrestricted; allowlist-proxy: HTTP/HTTPS only
             through a per-run proxy that admits `allowlist`; none: no network.
    """

    mode: str = "open"
    allowlist: list[str] = field(default_factory=list)
    no_proxy: list[str] = field(default_factory=lambda: ["localhost", "127.0.0.1", "::1"])
    proxy_image: str = EGRESS_PROXY_IMAGE
    proxy_port: int = 3128
    network_prefix: str = EGRESS_NETWORK_PREFIX


@dataclass
class ClarificationConfig:
    """[clarification] - park/resume bounds and timeouts."""

    max_rounds: int = numeric_default("clarification.max_rounds")
    answer_timeout: str = numeric_default("clarification.answer_timeout")

    def answer_timeout_seconds(self) -> int:
        """
        The hard answer timeout parsed to seconds.
        Returns: Seconds after parked_at before the run is released.
        """
        return parse_duration(self.answer_timeout)


@dataclass
class ExecutionConfig:
    """
    [execution] - shared backend and reviewed container preparation.
    Preparation is path#job@full-commit; empty disables preparation.
             Bounds apply to setup independently of the total run budget.
    """

    backend: str = "container"
    preparation: str = ""
    preparation_step_timeout_seconds: int = numeric_default(
        "execution.preparation_step_timeout_seconds"
    )
    preparation_total_timeout_seconds: int = numeric_default(
        "execution.preparation_total_timeout_seconds"
    )
    preparation_max_attempts: int = numeric_default("execution.preparation_max_attempts")


@dataclass
class LocalConfig:
    """
    [local] - managed Pi under the current server account.
    Optionally overrides PATH for project tools. Scope delegation is
             configured by the server operator.
    """

    path: str = ""


@dataclass
class ContainerConfig:
    """
    [container] - execution isolation and retained parked containers.
    run_args are extra option tokens for `<runtime> run` (e.g.
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
    """

    runtime: str = "docker"
    image: str = EXECUTOR_BASE_IMAGE
    build_definition: str = ""
    system_packages: bool = False
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
    [worktree] - local clone of the target repo and worktree root.
    repo_path is the local clone that per-run worktrees are created
             from; only its .git directory is mounted alongside the worktree
             in the executor container. Required for the isolation layer. branch_template
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
    [workflow] - new-job default and AEGIS task label mapping.
    `mode` selects auto detection or Direct; manual choices take precedence.
             `kind_labels` maps a ticket label to an AEGIS task type; fix/bug
             labels win over change, then configured feature labels, with
             `default_kind` used when none match. `stage_timeout_overrides`
             raises or lowers the
             per-executor-launch bound for individual stages; anything absent
             uses [budgets] per_gate_timeout_seconds.
    """

    mode: str = "auto"
    default_kind: str = "feature"
    kind_labels: dict[str, str] = field(
        default_factory=lambda: {"bug": "fix", "fix": "fix", "change": "change"}
    )
    aegis_python: str = "python"
    stage_timeout_overrides: dict[str, int] = field(default_factory=dict)


@dataclass
class RecoveryConfig:
    """[recovery] - bounded stage and transient failure handling."""

    max_stage_failures: int = numeric_default("recovery.max_stage_failures")
    max_transient_retries: int = numeric_default("recovery.max_transient_retries")
    retry_backoff_seconds: list[int] = field(default_factory=lambda: [5, 30, 120])


@dataclass
class BudgetsConfig:
    """
    [budgets] - hard bounds so a run can never thrash forever.
    `per_gate_timeout_seconds` bounds ONE executor launch (the
             wall-clock a single gate/fix relaunch may take);
             `max_wall_clock_seconds` bounds cumulative active work, excluding waits. They
             are independent knobs - a generous per-gate limit no longer forces
             an equally generous total, and a tight total no longer throttles
             every individual gate.
    """

    max_iterations: int = numeric_default("budgets.max_iterations")
    max_wall_clock_seconds: int = numeric_default("budgets.max_wall_clock_seconds")
    per_gate_timeout_seconds: int = numeric_default("budgets.per_gate_timeout_seconds")
    max_cost_usd: float = numeric_default("budgets.max_cost_usd")
    # AEGIS task journals, step files, anchors, evolution records and reports
    # count alongside product changes. Keep the run bounded while leaving
    # honest headroom for governance evidence and the product diff.
    max_files_touched: int = numeric_default("budgets.max_files_touched")


@dataclass
class DeliveryConfig:
    """[delivery] - draft MR/PR boundary; never merges."""

    target_branch: str = "develop"
    draft: bool = True
    reviewers: list[str] = field(default_factory=list)
    remove_source_branch: bool = True
    approval_label: str = "agent-approved"
    require_human_approval: bool = True
    publish_checkpoints: bool = True


@dataclass
class ReviewConfig:
    """
    [review] - post-MR revise loop triggers and bounds.
    `on_pipeline_failure` decides what a red forge pipeline on the
             published draft does. "revise" starts a governed repair round on
             the SAME bounded path the revise label uses, so the repair still
             follows the project publication approval policy;
             "notify" posts one comment and waits for a human; "ignore" skips
             the pipeline read entirely. Every mode obeys `max_review_rounds`.
    """

    revise_label: str = "agent-revise"
    max_review_rounds: int = numeric_default("review.max_review_rounds")
    on_pipeline_failure: str = "revise"


@dataclass
class MetricsConfig:
    """[metrics] - stdlib-only statistics capture."""

    enabled: bool = True
    db_path: str = ""
    export_jsonl: str = ""
    capture_tokens: bool = True
    html_out: str = ""


@dataclass
class Config:
    """
    Parsed, typed ADORE configuration (one attribute per section).
    Derived defaults (store_root, questions_file, metrics paths) are
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
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    raw: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        """
        Resolved configuration as a plain nested mapping.
        Returns: Mapping suitable for JSON output (`adore config show`).
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
                        "metrics",
            )
        }
        return result


def _build_section(cls: type, data: Any) -> Any:
    """
    Build one section dataclass from a raw mapping.
    Unknown keys are left out here and refused by validate_config;
                known keys override the documented defaults.
    cls: The section dataclass type.
    data: Raw mapping from tomllib (or anything else -> defaults).
    Returns: A populated section instance.
    """
    if not isinstance(data, dict):
        return cls()
    known = {f.name for f in fields(cls)}
    kwargs = {key: value for key, value in data.items() if key in known}
    return cls(**kwargs)


def _build_labels(data: Any) -> LabelsConfig:
    """
    Build the nested [labels.*] categories.
    data: Raw [labels] mapping.
    Returns: A populated LabelsConfig.
    """
    if not isinstance(data, dict):
        return LabelsConfig()
    return LabelsConfig(
        lifecycle=_build_section(LifecycleLabels, data.get("lifecycle")),
        selection=_build_section(SelectionLabels, data.get("selection")),
        control=_build_section(ControlLabels, data.get("control")),
    )


def _build_executor(data: Any) -> ExecutorConfig:
    """
    Build [executor] including [executor.endpoint] and [executor.web].
    A non-table endpoint or web value is left at its defaults and
                refused by validate_config.
    data: Raw [executor] mapping.
    Returns: A populated ExecutorConfig.
    """
    if not isinstance(data, dict):
        return ExecutorConfig()
    section = _build_section(ExecutorConfig, {key: value for key, value in data.items()
                                              if key not in ("endpoint", "web")})
    section.endpoint = _build_section(ExecutorEndpointConfig, data.get("endpoint"))
    section.web = _build_section(ExecutorWebConfig, data.get("web"))
    return section


def _build_container(data: Any) -> ContainerConfig:
    """
    Build [container] including the nested [container.egress].
    data: Raw [container] mapping.
    Returns: A populated ContainerConfig.
    """
    if not isinstance(data, dict):
        return ContainerConfig()
    scalars = {key: value for key, value in data.items() if key != "egress"}
    section = _build_section(ContainerConfig, scalars)
    section.egress = _build_section(ContainerEgressConfig, data.get("egress"))
    return section


def _valid_hostname_pattern(value: str) -> bool:
    """
    Check an egress allowlist hostname or leading wildcard.
    value: Hostname pattern, optionally starting with "*.".
    Returns: True when the pattern is syntactically safe.
    """
    host = value[2:] if value.startswith("*.") else value
    if not host or len(host) > 253 or host.endswith(".") or "." not in host:
        return False
    return all(_HOST_LABEL_RE.match(label) for label in host.split("."))


def _valid_no_proxy_entry(value: str) -> bool:
    """
    Check a NO_PROXY entry accepted by ADORE config validation.
    value: Hostname, leading wildcard, localhost, or loopback IP.
    Returns: True when the value is syntactically safe.
    """
    if value in ("localhost", "127.0.0.1", "::1"):
        return True
    return _valid_hostname_pattern(value)


def _derive_names(config: Config) -> None:
    """
    Resolve slug-derived defaults left empty in the file.
    slug <- lowercase agent name; email <- "<slug>-bot@local";
                store_root <- ".<slug>"; questions_file <-
                "<SLUG>_QUESTIONS.md"; metrics paths under the store root.
                Explicit values are never overridden.
    config: The configuration to complete in place.
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


def requested_workflow(default: str, override: str | None = None) -> str:
    """
    Resolve a new job's trusted request before inspecting AEGIS.
    default: Project mode: auto or direct.
    override: Optional manual selection: aegis or direct.
    Returns: The requested mode; auto still needs repository observation.
    Raises ValueError: Invalid project mode or manual selection.
    """
    if default not in ("auto", "direct") or override not in (None, "aegis", "direct"):
        raise ValueError("invalid requested workflow")
    return override if override is not None else default


def default_config() -> Config:
    """
    ADORE's built-in configuration, as a file that sets nothing gets it.
    Name-derived defaults are resolved from the default agent name
             (slug `adore`, `.adore` state root and the paths under it).
    Returns: A new default configuration.
    """
    config = Config()
    _derive_names(config)
    return config


def load_config(path: str | Path) -> Config:
    """
    Load configuration from a TOML file into typed sections.
    Missing keys take the documented defaults and unknown keys
                are left out, so `adore config validate` reports every problem,
                unknown keys included, in one pass instead of dying on the first.
    path: Path to config.toml.
    Returns: Config with runtime-only absolute source_path metadata.
    Raises FileNotFoundError: When the file does not exist.
    Raises tomllib.TOMLDecodeError: When the file is not valid TOML.
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
        metrics=_build_section(MetricsConfig, raw.get("metrics")),
        raw=raw,
        source_path=Path(path).resolve(),
    )
    _derive_names(config)
    return config


def valid_reviewers(value: object) -> bool:
    """
    Validate a list of forge account names before CLI submission; empty requests no review.
    value: Human-authored reviewer list.
    Returns: True for bounded names without whitespace, controls or option prefixes.
    """
    return isinstance(value, list) and len(value) <= MAX_REVIEWERS and all(
        isinstance(name, str) and 1 <= len(name) <= 255 and not name.startswith("-")
        and not any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in name)
        for name in value
    )


def branch_naming_preview(template: str, rule: str, slug: str, *,
                          run_id: str = "sample-run-1", iid: int = 1) -> dict[str, Any]:
    """
    Render an example or actual job branch and check the optional Python regex.
    template: Branch template using only slug, run_id and iid fields.
    rule: Optional repository naming regex; empty disables this check.
    slug: Effective agent slug from the selected configuration.
    run_id: Actual identity for bounded admission checks; defaults to the example.
    iid: Actual positive ticket identity; defaults to the example.
    Returns: Explicit sample identity, name, match result and closed issue codes.
    Note: An example proves this identity only; it creates no branch or config.
          Regex execution is isolated and bounded to one second, failing closed.
    """
    result: dict[str, Any] = {"template": template, "rule": rule, "slug": slug,
                              "iid": iid, "run_id": run_id, "name": None,
                              "valid": False, "rule_matches": None, "issues": []}
    issues = result["issues"]
    if (not isinstance(template, str) or not isinstance(slug, str)
            or not isinstance(run_id, str) or type(iid) is not int or iid < 1):
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
                                     text=True, timeout=1,
                                     env=automatic_environment(), **background_process_options())
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
    Name every config.toml key this build does not read.
    There is no compatibility while ADORE is in development: a key
                left by an earlier build is refused, not silently ignored.
                [local] and [execution] are checked by their own validators.
    raw: Parsed config.toml mapping.
    Returns: One issue per unknown key, naming the key to remove.
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
        ("delivery", DeliveryConfig),
        ("review", ReviewConfig),
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
    if isinstance(raw.get("executor"), dict):
        check("executor.endpoint", raw["executor"].get("endpoint"), ExecutorEndpointConfig)
        check("executor.web", raw["executor"].get("web"), ExecutorWebConfig)
    container = raw.get("container")
    if isinstance(container, dict):
        check("container", {key: value for key, value in container.items()
                            if key != "egress"}, ContainerConfig)
        egress = container.get("egress")
        if isinstance(egress, dict) and "mode" in egress:
            issues.append("[container.egress] unknown key 'mode': remove it from config.toml; "
                          "[executor] internet decides the agent's network access")
            egress = {key: value for key, value in egress.items() if key != "mode"}
        check("container.egress", egress, ContainerEgressConfig)
    return issues


def _provider_issues(config: Config) -> list[str]:
    """
    Validate [executor] provider, model and [executor.endpoint].
    The provider is a Pi API-key provider from the shipped catalog,
                `chatgpt` or `custom`; [executor.endpoint] is present exactly
                for `custom`, with an http(s) base URL that carries no user
                info, query or fragment (a key is a credential, never a URL
                part) and a supported Pi API type. A local run cannot use an
                endpoint: it has no ADORE-owned agent directory for models.json.
    config: Loaded configuration (with its raw mapping).
    Returns: One issue per problem, naming the key.
    """
    executor = config.executor
    issues: list[str] = []
    try:
        known = provider_ids()
    except CatalogError as exc:
        return [f"[executor] provider cannot be checked: {exc}"]
    if not isinstance(executor.provider, str) or not executor.provider.strip():
        issues.append('[executor] provider is required: a Pi API-key provider id, '
                      '"chatgpt" or "custom"')
    elif executor.provider not in known:
        issues.append(f"[executor] provider {executor.provider!r} is not a Pi API-key provider, "
                      '"chatgpt" or "custom"')
    if not isinstance(executor.model, str) or not executor.model.strip():
        issues.append("[executor] model is required")
    elif not MODEL_ID_RE.fullmatch(executor.model):
        issues.append(f"[executor] model {executor.model!r} must be one model id without "
                      "spaces, quotes or control characters (at most 200 characters)")
    if not isinstance(executor.thinking, str) or (executor.thinking and
            executor.thinking not in thinking_levels(executor.provider, executor.model)):
        issues.append("[executor] thinking is unsupported for this provider and model")
    if type(executor.internet) is not bool:
        issues.append(f"[executor] internet must be true or false: {executor.internet!r}")
    raw_executor = config.raw.get("executor")
    raw_web = raw_executor.get("web") if isinstance(raw_executor, dict) else None
    if raw_web is not None and not isinstance(raw_web, dict):
        issues.append("[executor.web] must be a table")
    if executor.web.search not in WEB_SEARCH_CHOICES:
        issues.append(f"[executor.web] search must be one of {', '.join(WEB_SEARCH_CHOICES)}: "
                      f"{executor.web.search!r}")
    raw_endpoint = raw_executor.get("endpoint") if isinstance(raw_executor, dict) else None
    if executor.provider != CUSTOM:
        if raw_endpoint is not None:
            issues.append('[executor.endpoint] is used only with provider = "custom": '
                          "remove it from config.toml")
        return issues
    if not isinstance(raw_endpoint, dict):
        issues.append('[executor.endpoint] base_url is required for provider = "custom"')
        return issues
    base_url = executor.endpoint.base_url
    if not valid_endpoint_url(base_url):
        issues.append("[executor.endpoint] base_url must be an http(s) address with a host and "
                      "no user name, password, query, fragment, spaces or quotes (the address "
                      f"as seen from Pi): {base_url!r}")
    if executor.endpoint.api not in ENDPOINT_APIS:
        issues.append(f"[executor.endpoint] api must be one of {', '.join(ENDPOINT_APIS)}: "
                      f"{executor.endpoint.api!r}")
    return issues


def egress_policy(config: Config) -> EgressPolicy:
    """
    The network access of the project's executor containers.
    Internet off: the per-run allowlist proxy admitting the
                provider's hosts (`provider_hosts`) and `[container.egress]
                allowlist`, deduplicated and sorted. Internet on: open egress.
                Used for every stage container and the Test AI connection; a
                local run is not restricted by it.
    config: Validated configuration.
    Returns: The derived EgressPolicy.
    """
    egress = config.container.egress
    if config.executor.internet is True:
        return EgressPolicy(mode="open", no_proxy=list(egress.no_proxy),
                            proxy_image=egress.proxy_image, proxy_port=egress.proxy_port,
                            network_prefix=egress.network_prefix)
    hosts = sorted({*provider_hosts(config.executor), *egress.allowlist})
    return EgressPolicy(mode="allowlist-proxy", allowlist=hosts,
                        no_proxy=list(egress.no_proxy), proxy_image=egress.proxy_image,
                        proxy_port=egress.proxy_port, network_prefix=egress.network_prefix)


def validate_budgets(config: Config) -> list[str]:
    """
    Validate only the closed budget table and its provider timeout bound.
    config: Typed configuration; other settings are separately validated/pinned.
    Returns: Human-readable issues, without subprocesses or host/runtime checks.
    """
    issues = []
    raw = config.raw.get("budgets", {})
    allowed = {item.name for item in fields(BudgetsConfig)}
    if not isinstance(raw, dict):
        issues.append("[budgets] must be a table")
    else:
        issues.extend(f"[budgets] unknown key {key!r}: remove it from config.toml"
                      for key in sorted(set(raw) - allowed))
    issues.extend(numeric_issues(config, budgets=True))
    return issues


def validate_config(config: Config) -> list[str]:
    """
    Validate a Config and always answer with issues, never with a traceback.
    A section that is not a TOML table would be read as all defaults, so it
                is reported first and nothing else is judged. A value of the
                wrong TOML type makes a later comparison fail; that failure is
                reported as an issue naming the cause.
    config: The configuration to validate.
    Returns: Empty list when valid; otherwise one message per issue.
    """
    not_tables = sorted(name for name, value in config.raw.items()
                        if name in KNOWN_SECTIONS and not isinstance(value, dict))
    if not_tables:
        return [f"[{name}] must be a table of settings, not a single value"
                for name in not_tables]
    try:
        return _config_issues(config)
    except (TypeError, AttributeError) as exc:
        return ["a setting has the wrong TOML type (text, number, true/false or list): "
                f"{exc}; compare config.toml with the Configuration Reference"]


def _config_issues(config: Config) -> list[str]:
    """
    Validate a Config and return a list of human-readable issues.
    Structural and cross-field checks per Configuration_Reference:
                enum values, positive bounds, parseable durations, and a
                Pi model and launch template. Run at startup so typos
                are caught before the poll loop starts.
    config: The configuration to validate.
    Returns: Empty list when valid; otherwise one message per issue.
    """
    issues: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            issues.append(message)

    for section in config.raw:
        check(section in KNOWN_SECTIONS, f"unknown section: [{section}]")
    issues.extend(_unknown_key_issues(config.raw))
    numeric = numeric_issues(config, budgets=False)
    issues.extend(numeric)
    for key in ("executor.env_keys", "recovery.retry_backoff_seconds",
                "platform.work_item_types", "platform.closed_states"):
        section, name = key.split(".", 1)
        value = getattr(getattr(config, section), name)
        if not valid_collection(key, value, config.executor.provider):
            issues.append(f"[{section}] {name} has invalid collection values or bounds")

    try:
        definition_parts(config.container.build_definition)
    except BuildBundleError:
        issues.append("[container] build_definition must be a safe relative "
                      "manifest.json@full-commit")

    check(bool(config.agent.name.strip()), "[agent] name must not be empty")
    check(
        bool(_SLUG_RE.match(config.agent.slug)),
        f"[agent] slug must be lowercase alphanumeric/dash: {config.agent.slug!r}",
    )

    check(
        config.platform.kind in ("gitlab", "github", "gitea", "azure_devops"),
        f'[platform] kind must be "gitlab", "github", "gitea" or "azure_devops": '
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

    if config.platform.kind == "azure_devops":
        from adore.forge.azure_devops import validate_azure_scope

        try:
            validate_azure_scope(config.platform.organization, config.platform.project,
                                 config.platform.repo, config.platform.area_path,
                                 config.platform.work_item_types, config.platform.closed_states)
        except ValueError as exc:
            issues.append(f"[platform] {exc}")
        for spec in (config.labels.lifecycle, config.labels.selection, config.labels.control):
            for name, value in vars(spec).items():
                check(";" not in value, f"[labels] {name} cannot contain semicolons on Azure")
        for value in (config.delivery.approval_label, config.review.revise_label,
                      *config.workflow.kind_labels):
            check(";" not in value, "[labels] Azure tag names cannot contain semicolons")
        for reviewer in config.delivery.reviewers:
            check(bool(re.fullmatch(
                r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", reviewer)),
                  "[delivery] reviewers must be Azure identity GUIDs for azure_devops")
    else:
        for key in ("organization", "project", "area_path"):
            check(not getattr(config.platform, key), f"[platform] {key} is Azure-only")

    check(
        config.polling.mode in ("loop", "once"),
        f"[polling] mode must be loop/once: {config.polling.mode!r}",
    )
    for window in config.polling.quiet_hours:
        check(
            bool(_QUIET_HOURS_RE.match(str(window))),
            f'[polling] quiet_hours entries must look like "22:00-06:00": {window!r}',
        )

    forge_keys = sorted(name for name in config.executor.env_keys
                        if str(name).upper() in FORGE_CREDENTIAL_ENV)
    check(
        not forge_keys,
        f"[executor] env_keys must not expose forge credentials to executors: {forge_keys}",
    )
    issues.extend(_provider_issues(config))
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
    check(type(config.container.system_packages) is bool,
          "[container] system_packages must be a boolean")
    if config.container.system_packages is True:
        check(config.execution.backend == "container",
              "[container] system_packages is unavailable for local execution")
        # This managed mode cannot inherit host exposure from arbitrary runtime
        # overrides. Ordinary resource limits and rootless keep-id remain valid.
        allowed_options = {"--memory", "--memory-swap", "--cpus", "--cpu-shares",
                           "--pids-limit", "--shm-size", "--userns", "--cpuset-cpus"}
        for arg in config.container.run_args:
            check(isinstance(arg, str) and arg.split("=", 1)[0] in allowed_options
                  and (not arg.startswith("--userns") or arg == "--userns=keep-id"),
                  "[container] system_packages refuses unsafe run_args overrides")
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
    check(config.execution.backend in ("container", "local"),
          "[execution] backend must be container/local")
    local = config.local
    if "local" in config.raw:
        declaration = config.raw["local"]
        check(isinstance(declaration, dict), "[local] must be a table")
        if isinstance(declaration, dict):
            for key in set(declaration) - {item.name for item in fields(LocalConfig)}:
                issues.append(f"[local] unknown field: {key}; remove it from config.toml")
    check(isinstance(local.path, str) and not any(ord(c) < 32 for c in local.path),
          "[local] path must be plain text")
    if config.execution.backend == "local":
        check(not config.execution.preparation, "[local] container preparation is unsupported")
        check(not config.container.egress.allowlist,
              "[local] container egress allowlist is unsupported: a local run is not "
              "network-restricted")
        check(not config.container.run_args and not config.container.required_tool_checks
              and config.container.selinux_relabel == "off",
              "[local] container runtime options/tool checks are unsupported")
        check(config.container.runtime_env == ContainerConfig().runtime_env,
              "[local] [container] runtime_env is unsupported")
        check(all(not str(name).upper().startswith(("PI_", "NODE_", "NPM_", "PYTHON", "GIT_",
                                                   "LD_", "DYLD_"))
                  and str(name).upper() not in FORGE_CREDENTIAL_ENV | {
                      "PATH", "HOME", "USERPROFILE", "COMSPEC", "SYSTEMROOT",
                      "BASH_ENV", "ENV", "SSH_AUTH_SOCK", "SSH_AGENT_PID",
                  }
                  for name in config.executor.env_keys),
              "[local] executor env_keys cannot override the managed launch environment")
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
    check(config.execution.backend == "local" or bool(config.container.image.strip())
          or bool(config.execution.preparation),
          "[container] image is required without preparation")
    egress = config.container.egress
    check(
        isinstance(egress.allowlist, list),
        "[container.egress] allowlist must be a list of hostnames",
    )
    if isinstance(egress.allowlist, list):
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
    check(workflow.mode in ("auto", "direct"),
            "[workflow] mode must be auto or direct")
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
            if not valid_label(label):
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
            if not valid_numeric("workflow.stage_timeout_overrides." + stage,
                                 seconds, config.executor.provider):
                domain = numeric_domain("workflow.stage_timeout_overrides." + stage,
                                        config.executor.provider)
                issues.append(f"[workflow] stage_timeout_overrides.{stage} must be an integer "
                              f"in {domain['minimum']}..{domain['maximum']} seconds")

    issues.extend(validate_budgets(config))

    check(bool(config.delivery.target_branch.strip()), "[delivery] target_branch is required")
    check(
        type(config.delivery.publish_checkpoints) is bool,
        "[delivery] publish_checkpoints must be a boolean",
    )
    check(valid_reviewers(config.delivery.reviewers),
          "[delivery] reviewers must list valid human account names (empty requests no review)")
    check(type(config.delivery.require_human_approval) is bool,
          "[delivery] require_human_approval must be a boolean")
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
    check(isinstance(config.labels.selection.type_epic, str) and
          bool(config.labels.selection.type_epic.strip()),
          "[labels.selection] type_epic must be a non-empty label")
    # An empty label matches every ticket on some forges, and one label in
    # two roles makes a state unreadable.
    role_labels = [
        (f"[labels.{section}] {name}", value)
        for section, spec in (("lifecycle", config.labels.lifecycle),
                              ("control", config.labels.control))
        for name, value in asdict(spec).items()
    ]
    for where, value in role_labels:
        check(isinstance(value, str) and bool(value.strip()),
              f"{where} must be a non-empty label")
    named = [value for _, value in role_labels if isinstance(value, str) and value.strip()]
    check(len(set(named)) == len(named),
          "[labels] lifecycle and control labels must be distinct from each other")
    for section, labels in (("lifecycle", config.labels.lifecycle),
                            ("control", config.labels.control),
                            ("selection", config.labels.selection)):
        for name, value in vars(labels).items():
            check(valid_label(value),
                  f"[labels.{section}] {name} must be a trimmed label of 1..120 characters")
    for key, value in (("delivery.approval_label", config.delivery.approval_label),
                       ("review.revise_label", config.review.revise_label)):
        check(valid_label(value), f"{key} must be a trimmed label of 1..120 characters")
    lifecycle_labels = set(asdict(config.labels.lifecycle).values())
    control_labels = set(asdict(config.labels.control).values())
    check(
        config.delivery.approval_label not in lifecycle_labels | control_labels,
        "[delivery] approval_label must be distinct from lifecycle/control labels",
    )

    check(
        config.review.on_pipeline_failure in ("revise", "notify", "ignore"),
        "[review] on_pipeline_failure must be revise/notify/ignore: "
        f"{config.review.on_pipeline_failure!r}",
    )

    check(
        type(config.metrics.capture_tokens) is bool,
        "[metrics] capture_tokens must be a boolean",
    )
    if config.metrics.enabled:
        check(bool(config.metrics.db_path.strip()), "[metrics] db_path is required when enabled")

    return issues
