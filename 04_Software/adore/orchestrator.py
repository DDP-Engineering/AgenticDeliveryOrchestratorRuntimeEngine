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
@file orchestrator.py
@brief The ADORE thick-conductor engine (library core; design doc 5a/7a/8/9).
@details Deterministic state machine: poll for ready tickets, isolate work
         (worktree + container), drive the executor stage-by-stage through the
         AEGIS 3.x workflow with objective verification in between, park on
         clarification questions and resume on human answers, enforce run
         budgets, and escalate instead of thrashing. Never merges; publication
         (draft MR) belongs to ADORE alone. No LLM runs here - every decision
         is an `if` on exit codes, envelope fields, file presence, labels, and
         timestamps. All collaborators are injected so the whole machine is
         unit-testable offline.
@details Conduction is status-driven and context-bootstrapped: AEGIS owns the
         stage pointer, ADORE validates pinned `run status` on every boundary,
         and every fresh live-stage launch receives bounded schema-1 `run
         context`. Applied-ready restart state is verified/closed without
         executor replay. ADORE is the explicitly identified delegated
         approver; real human approval stays at draft MR review.
@details The WSL2 bind-mount teardown-race retry (`_TEARDOWN_RACE_MARKERS`,
         `_is_teardown_race`) moved to `WorktreeManager.remove` in
         isolation.py (ADORE-ARCH-009): platform-specific glue belongs to the
         isolation layer, not the core loop. `_teardown` now makes one call
         and logs a husk message if it still fails.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable, Iterator
import contextlib
from dataclasses import asdict, dataclass
from functools import partial
import json
import os
from pathlib import Path, PurePosixPath
import random
import re
import shutil
import time

from adore import metrics
from adore.aegis import (
    CONTEXT_BOOTSTRAP_LIMIT_BYTES,
    INTEGRITY_CODES,
    QUICK_KINDS,
    RUN_RESOLUTION_CODES,
    AegisArtifactError,
    AegisClient,
    AegisContext,
    AegisError,
    AegisProtocolError,
    AegisResponse,
)
from adore.branding import (
    CONTAINER_CODEX_HOME,
    CONTAINER_IO_MOUNT,
    CONTAINER_OPENCODE_AUTH_DIR,
    DEFAULT_QUESTIONS_FILE,
)
from adore.config import Config
from adore.executor.base import Executor
from adore.executor.launcher import build_executor
from adore.forge import Comment, Forge, ForgeError, MergeRequest, Ticket, build_forge
from adore.identity import AgentIdentity
from adore.isolation import (
    ContainerManager,
    IsolationError,
    WorktreeManager,
    build_container_env,
)
from adore.state import RunState, StateError, StateStore, content_hash, derive_run_id
from adore.util import (
    force_rmtree,
    in_quiet_hours,
    iso_to_datetime,
    load_env_file,
    utc_now_iso,
)

# CONSTANTS

# The AEGIS 3.x executable stage sequences (contract notes section 4). These
# are an ALLOWLIST, not the conductor's idea of truth: AEGIS owns the stage
# pointer and ADORE reads it from `run status`. Any stage outside the tuple
# for the run's profile - or a backwards move, which only an approved
# `route_to` can produce - is a contract break and escalates.
STANDARD_STAGES = ("intake", "alignment", "requirement", "design", "check",
                   "implementation", "validation", "delivery")
QUICK_STAGES = ("intake", "implementation", "validation", "delivery")

# Stable truthful identity written into every AEGIS stage-close journal entry.
# This is explicit delegated automation, never a Git user or implied human.
DELEGATED_APPROVER = "ADORE 3.0 delegated conductor"

# ADORE's own post-AEGIS phase. AEGIS `delivery` closes the governed run;
# publication (integrate, verify, push, draft MR) is ADORE's alone and never
# re-enters the stage loop, so it needs a stage name AEGIS cannot produce.
PUBLICATION_STAGE = "publication"

# Stages `adore reset <run-id> --to <stage>` accepts.
RESETTABLE_STAGES = (*STANDARD_STAGES, PUBLICATION_STAGE)

_AEGIS_RUN_DIR = ".agentic/runs"
_AGENTIC_FAILURE_CONTEXT_LIMIT = 5000
_AGENTIC_FAILURE_ITEMS_LIMIT = 5
_AGENTIC_ORIENTATION_LIMIT = 3000
_AEGIS_ARTIFACT_LIMIT_BYTES = 4 * 1024 * 1024

_GRAPH_REQUIRED_KEYS = {
    "run_id", "stage", "intent", "schema_version", "access_mode",
    "complete", "alignment", "design", "spec_items", "checks", "evidence",
    "change_units", "decisions", "stage_records",
}
_GRAPH_OPTIONAL_KEYS = {"profile", "red_green_policy", "waivers", "outcome"}
_GATE_STATUSES = {"passed", "failed", "waived", "not-enforced", "not-run"}
_VERIFICATION_STATUSES = {"ok", "waived", "failed"}

# classify_block outcomes.
BLOCK_PARK = "park"
BLOCK_RETRY = "retry"
BLOCK_ESCALATE = "escalate"

# A live AEGIS persistence lock clears in seconds (its own wait is 15 s), so
# exactly one bounded re-attempt is warranted before a human is involved.
LOCK_TIMEOUT_CODE = "PERSISTENCE-LOCK-TIMEOUT"
_LOCK_RETRY_DELAY = 20.0
_MAX_LOCK_RETRIES = 1

# When the forge refuses the clarification comment, the journal becomes the
# only copy of the questions. Keep enough to act on without turning one
# journal line into a log-flooding dump of executor output.
_PARK_JOURNAL_LIMIT = 2000

# An in-review MR that reads back as not-found is usually a real deletion, but
# a single 404 can also be a transient platform blip. Tolerate a few before
# ending the run, so an in-review run whose MR truly vanished cannot re-poll
# (and re-log) forever, while a momentary blip is ridden out.
_MR_MISSING_GRACE_POLLS = 3

# stage_host_auth OAuth-bridge paths per executor: (host path under ~, container
# dir). Codex is staged into an ADORE-owned CODEX_HOME so host plugin/config
# state cannot bleed into a run while auth.json still comes from ~/.codex.
_HOST_AUTH_PATHS = {
    "opencode": (".local/share/opencode/auth.json", CONTAINER_OPENCODE_AUTH_DIR),
    "codex": (".codex/auth.json", CONTAINER_CODEX_HOME),
}

_EXECUTOR_CONTAINER_ENV = {
    "codex": {"CODEX_HOME": CONTAINER_CODEX_HOME},
}

_STAGE_GOALS = {
    stage: (
        f"Work only the current AEGIS {stage.upper()} stage. The validated "
        "context above is authoritative: read exactly its `required_reads`, "
        "follow the generated form checklist and current-stage artifact, and "
        "stop before the declared human gate. AEGIS's generated guidance - "
        "not this prompt - owns the stage completion mechanics."
    )
    for stage in STANDARD_STAGES
}
_STAGE_GOALS.update({
    "revise": (
        "A human reviewer requested changes on the draft merge request (the "
        "review thread is above). Make exactly the requested changes - no "
        "more - update tests and evidence accordingly, re-run `aegis verify "
        "run`, and commit everything."
    ),
})

# Quick runs remain evidence-driven. These additions state only the control
# contract ADORE must prevent an executor from weakening; generated forms own
# the stage mechanics.
_QUICK_STAGE_GOALS = {
    "intake": (
        "This is a QUICK fix/change run. Do not begin implementation during "
        "intake; capture the bounded intent through the generated checklist."
    ),
    "implementation": (
        "This is the implementation stage of a new QUICK run. Before changing "
        "the implementation, use `aegis check create`, complete its generated "
        "definition, and `aegis check register`. Execute it to obtain a genuine "
        "RED result, preserve that red witness, then make the fix and execute "
        "again for genuine GREEN evidence. Link the active green evidence in "
        "`linked_check_evidence`. Manual evidence is not a substitute for an "
        "executed check. An executed failing `aegis check run` still exits 0: "
        "read `execution_status` and every `evidence[].result` instead of the "
        "process/envelope success. `nothing-ran` is failed execution and cannot "
        "satisfy readiness."
    ),
    "validation": (
        "This is QUICK validation. INV-3 applies and requires real active "
        "red/green check evidence. Only INV-1, INV-2, INV-8, INV-10, "
        "traceability, and coverage tied to intentionally absent stages may "
        "be not applicable. `nothing-ran` and any executed "
        "`evidence[].result: fail` remain failures; `status: ok` or exit 0 "
        "cannot turn them green."
    ),
    "delivery": (
        "This is QUICK delivery. Preserve the truthful quick evidence and "
        "scope already recorded; do not reinterpret not-applicable results."
    ),
}

# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True)
class BlockDecision:
    """
    @brief   What ADORE does about one blocked AEGIS response.
    @details Three actions only, all deterministic: `park` hands the run to a
             human through the existing clarification machinery, `retry` is the
             single bounded re-attempt a live persistence lock deserves, and
             `escalate` ends the run with the AEGIS error and, where one
             exists, the exact command a human would run.
    """

    action: str
    reason: str
    hint: str = ""


# HELPER FUNCTIONS


def classify_block(
    response: AegisResponse,
    stage_record: dict | None = None,
) -> BlockDecision:
    """
    @brief      Decide park / retry / escalate for a blocked AEGIS response.
    @details    In order of precedence:
                - a live persistence lock (`PERSISTENCE-LOCK-TIMEOUT`) is the
                  only transient failure AEGIS has: another process holds the
                  lock, so ONE bounded retry after a short delay is correct;
                - the rest of the non-waivable integrity floor
                  (`GRAPH-STALE-UPDATE`, `REQUIREMENT-STALE-UPDATE`, schema
                  corruption) and every run-resolution error escalate - they
                  need state repair, which ADORE never performs;
                - human-attention state recorded in the stage: unresolved
                  questions, an alignment `pause`, a `repo-wide` access
                  request, or a `route_to` request all park;
                - anything else escalates. A waivable blocker escalates too:
                  waiving is a human decision (design decision 3), so the
                  ticket carries the hint, never an automatic waiver.
    @param[in]  response The blocked or failed AEGIS response.
    @param[in]  stage_record The graph's `stage_records[<stage>]` mapping when
                             ADORE could read it, else None.
    @return     The BlockDecision.
    """
    code = response.code
    if code == LOCK_TIMEOUT_CODE:
        return BlockDecision(
            BLOCK_RETRY,
            "AEGIS persistence lock is held by another process",
        )
    if code in INTEGRITY_CODES or code in RUN_RESOLUTION_CODES:
        return BlockDecision(
            BLOCK_ESCALATE,
            f"AEGIS integrity failure ({code}); state repair is a human task",
            hint=response.remediation,
        )
    record = stage_record if isinstance(stage_record, dict) else {}
    questions = [
        str(item).strip()
        for item in (record.get("unresolved_questions") or [])
        if str(item).strip()
    ]
    if questions:
        return BlockDecision(BLOCK_PARK, "the stage records unresolved questions")
    if str(record.get("decision", "")).strip() == "pause":
        return BlockDecision(BLOCK_PARK, "alignment decided to pause")
    if str(record.get("requested_access_mode", "")).strip():
        return BlockDecision(
            BLOCK_PARK,
            "the stage requests the access mode "
            f"{record['requested_access_mode']!r}",
        )
    if str(record.get("route_to", "")).strip():
        return BlockDecision(
            BLOCK_PARK,
            f"the stage requests routing back to {record['route_to']!r}",
        )
    return BlockDecision(
        BLOCK_ESCALATE,
        response.error or f"AEGIS reported status {response.status}",
        hint=response.remediation,
    )


# PUBLIC API


class Orchestrator:
    """
    @brief   Coordinates polling, isolation, gate conducting, and clarification.
    @details Owns everything deterministic and every remote (Git-platform)
             operation; the executor owns code reasoning. Authoritative state
             lives in the local StateStore; ticket comments/labels only
             reflect it (design 5c).
    """

    def __init__(
        self,
        config: Config,
        forge: Forge,
        store: StateStore,
        worktrees: WorktreeManager,
        containers: ContainerManager,
        executor: Executor,
        *,
        secrets: dict[str, str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        log: Callable[[str], None] = print,
    ) -> None:
        """
        @brief      Wire the engine from its collaborators (all injectable).
        @param[in]  config Validated configuration.
        @param[in]  forge Git-platform adapter.
        @param[in]  store Local authoritative state store.
        @param[in]  worktrees Worktree manager (code isolation).
        @param[in]  containers Container manager (execution isolation).
        @param[in]  executor Executor launcher.
        @param[in]  secrets Executor secret subset (KEY -> value).
        @param[in]  sleep Sleep function (test override).
        @param[in]  log Line logger (stdout by default; journald in service).
        """
        self.config = config
        self.forge = forge
        self.store = store
        self.worktrees = worktrees
        self.containers = containers
        self.executor = executor
        self.secrets = secrets or {}
        self.sleep = sleep
        self.log = log
        self.identity = AgentIdentity(name=config.agent.name, slug=config.agent.slug)
        self.questions_file = config.executor.questions_file or DEFAULT_QUESTIONS_FILE
        # OAuth-bridge (stage_host_auth) source + container dir, per executor.
        # Codex reads host ~/.codex/auth.json but runs with ADORE-owned
        # CODEX_HOME inside the container, not the host desktop config dir.
        host_src, container_dir = _HOST_AUTH_PATHS.get(
            config.executor.default, _HOST_AUTH_PATHS["opencode"]
        )
        self.host_auth_path = Path.home() / host_src
        self.host_auth_container_dir = container_dir
        # The run this process is driving right now, if any. Stale-`working`
        # detection uses it to tell "a live conductor is on this" from "the
        # conductor died and left the run behind" (see _stale_working).
        self._in_flight_run_id = ""

    @classmethod
    def from_config(cls, config: Config, env_file: str = ".env") -> Orchestrator:
        """
        @brief      Build the engine with production collaborators.
        @param[in]  config Validated configuration.
        @param[in]  env_file Dotenv file holding the executor secrets.
        @return     A ready Orchestrator.
        """
        entry = config.executor.commands[config.executor.default]
        env = {**load_env_file(env_file), **os.environ}
        secrets = {key: env[key] for key in config.executor.env_keys if env.get(key)}
        return cls(
            config=config,
            forge=build_forge(config.platform.kind, config.platform.repo,
                              login=config.platform.login),
            store=StateStore(config.state.store_root, config.agent.slug),
            worktrees=WorktreeManager(config.worktree.repo_path, config.worktree.root),
            containers=ContainerManager(
                config.container.runtime,
                config.container.image,
                config.container.uv_cache_volume,
                config.container.npm_cache_volume,
                run_args=config.container.run_args,
                egress=config.container.egress,
            ),
            executor=build_executor(
                config.executor.default,
                entry.command,
                entry.model,
                config.executor.questions_file,
            ),
            secrets=secrets,
        )

    # -- main entries ---------------------------------------------------------

    def run_loop(self) -> int:
        """
        @brief   The long-running poller (design 5a): poll, sleep, repeat.
        @details Takes the single-instance lock, honors quiet hours and the
                 pause flag, applies jitter and error backoff, and releases
                 the lock on exit (including Ctrl+C).
        @return  Process exit code.
        """
        if not self.store.acquire_lock():
            self.log(
                "error: another instance holds the lock "
                f"({self.store.lock_path}); remove it if stale"
            )
            return 1
        backoff = 1
        try:
            while True:
                if in_quiet_hours(self.config.polling.quiet_hours):
                    self.log("quiet hours: polling paused")
                else:
                    try:
                        self.poll_once(locked=True)
                        backoff = 1
                    except ForgeError as exc:
                        self.log(f"poll error (platform): {exc}")
                        if self.config.polling.poll_backoff:
                            backoff = min(backoff * 2, 8)
                interval = self.config.polling.poll_interval_seconds * backoff
                interval += random.uniform(0, self.config.polling.poll_jitter_seconds)
                self.sleep(interval)
        except KeyboardInterrupt:
            self.log("interrupted; shutting down cleanly")
            return 0
        finally:
            self.store.release_lock()

    def poll_once(self, *, dry_run: bool = False, locked: bool = False) -> dict:
        """
        @brief      One poll pass: reconcile parked runs, then pick new work.
        @details    Order (design 5a/9): first give parked runs their answer /
                    TTL / timeout checks, then - unless paused or at the
                    concurrency limit - select and conduct the top eligible
                    ticket. Dry-run reports what would happen, touching
                    nothing.
        @param[in]  dry_run Report only; no side effects.
        @param[in]  locked True when run_loop already holds the lock.
        @return     Summary mapping (picked/resumed/reaped/timed_out, flags).
        @exception  ForgeError When the platform is unreachable (loop backs off).
        """
        own_lock = False
        if not dry_run and not locked:
            if not self.store.acquire_lock():
                raise RuntimeError("another instance holds the lock")
            own_lock = True
        try:
            summary: dict = {"resumed": 0, "reaped": 0, "timed_out": 0,
                             "done": 0, "mr_closed": 0, "revised": 0,
                             "picked": None}
            if not dry_run:
                self._reconcile_parked(summary)
            if self.store.is_paused():
                summary["paused"] = True
                return summary
            working = [r for r in self.store.list_runs() if r.lifecycle == "working"]
            if len(working) >= self.config.polling.max_concurrent_runs:
                summary["at_capacity"] = True
                return summary
            ticket = self._pick_ticket()
            if ticket is None:
                return summary
            summary["picked"] = ticket.iid
            if dry_run:
                self.log(f"dry-run: would pick #{ticket.iid} '{ticket.title}'")
                return summary
            self._claim_and_conduct(ticket)
            return summary
        finally:
            if own_lock:
                self.store.release_lock()

    def cancel(self, run_id: str, *, outcome: str = "cancelled") -> bool:
        """
        @brief      Graceful stop (design 8c): tear down, keep state, mark.
        @param[in]  run_id Stable run identifier.
        @param[in]  outcome Terminal outcome recorded in state.
        @return     True when the run existed and was cancelled.
        """
        try:
            run = self.store.load(run_id)
        except (FileNotFoundError, StateError):
            return False
        self._teardown(run, remove_worktree=True)
        run.lifecycle = "failed" if outcome == "failed" else outcome
        run.outcome = outcome
        self.store.save(run)
        self.store.journal(run_id, "cancelled", outcome=outcome)
        self._try_mark(run, outcome, run.stage)
        self._record_metrics(run)
        self.log(f"{run_id}: cancelled ({outcome})")
        return True

    def retry(self, run_id: str) -> bool:
        """
        @brief      Re-arm a failed/cancelled run and conduct it again from
                    the stage where it stopped (design 8c).
        @param[in]  run_id Stable run identifier.
        @return     True when the run existed and a ticket still backs it.
        """
        try:
            run = self.store.load(run_id)
        except (FileNotFoundError, StateError):
            return False
        ticket = self.forge.get_ticket(run.ticket_iid)
        if ticket is None:
            self.log(f"retry {run_id}: ticket #{run.ticket_iid} no longer exists")
            return False
        run.lifecycle = "working"
        run.outcome = ""
        run.iterations = 0
        run.created_at = ""  # restart the wall clock; save() re-stamps
        self.store.save(run)
        self.store.journal(run_id, "retry", stage=run.stage)
        if run.stage == PUBLICATION_STAGE:
            # never re-enter the AEGIS stage loop: the governed run is closed
            self._deliver(run, ticket)
        else:
            self._conduct(run, ticket)
        return True

    def reset(self, run_id: str, stage: str) -> bool:
        """
        @brief      State surgery (design 8c): force a run back to a stage.
        @details    Sets ADORE's stage pointer and leaves the run retry-able
                    (`adore retry` then re-arms budgets and conducts from
                    there). Destructive by nature - the CLI requires --force.
                    It never touches AEGIS state: the governed run's own stage
                    is AEGIS's to own, and `_conduct` re-reads it from
                    `run status` anyway. Only `publication` changes where
                    `retry` re-enters, by skipping the stage loop.
        @param[in]  run_id Stable run identifier.
        @param[in]  stage Target stage (an AEGIS stage or "publication").
        @return     True when the run existed and the stage is valid.
        """
        if stage not in RESETTABLE_STAGES:
            self.log(f"invalid stage {stage!r}; valid: "
                     f"{', '.join(RESETTABLE_STAGES)}")
            return False
        try:
            run = self.store.load(run_id)
        except (FileNotFoundError, StateError):
            return False
        run.stage = stage
        run.lifecycle = "failed"
        run.outcome = f"reset to {stage}"
        self.store.save(run)
        self.store.journal(run_id, "reset", stage=stage)
        self.log(f"{run_id}: reset to stage {stage}; run `adore retry {run_id}` "
                 "to continue")
        return True

    def cleanup(self) -> dict:
        """
        @brief      Garbage-collect leftovers (design 8c): stale lock,
                    orphaned containers, orphaned/husk worktrees.
        @details    Anything belonging to an ACTIVE run (working / parked /
                    in-review / validated) is never touched. Corrupt run
                    state is reported, never deleted (fail closed - that is
                    `adore delete`'s explicit job). Invoking cleanup asserts
                    no poller is running, so a leftover lock is cleared.
        @return     Report: lock_cleared, containers_removed,
                    worktrees_removed, corrupt_runs.
        """
        report: dict = {"lock_cleared": False, "containers_removed": [],
                        "proxy_containers_removed": [], "egress_networks_removed": [],
                        "worktrees_removed": [], "corrupt_runs": []}
        if self.store.lock_info() is not None:
            self.store.release_lock()
            report["lock_cleared"] = True
        active = {
            run.run_id for run in self.store.list_runs()
            if run.lifecycle in ("working", "parked", "in-review", "validated")
        }
        prefix = f"{self.identity.slug}-run-"
        with contextlib.suppress(IsolationError):
            for name in self.containers.list_containers(prefix):
                if name.endswith("-egress-proxy"):
                    continue
                run_id = name[len(prefix):]
                if run_id and run_id not in active:
                    with contextlib.suppress(IsolationError):
                        self.containers.remove(name)
                        report["containers_removed"].append(name)
            if self.config.container.egress.mode == "allowlist-proxy":
                for name in self.containers.list_containers(prefix):
                    if not name.endswith("-egress-proxy"):
                        continue
                    run_id = name[len(prefix):-len("-egress-proxy")]
                    if run_id and run_id not in active:
                        with contextlib.suppress(IsolationError):
                            self.containers.remove_egress(f"{prefix}{run_id}")
                            report["proxy_containers_removed"].append(name)
        if self.config.container.egress.mode == "allowlist-proxy":
            with contextlib.suppress(IsolationError):
                network_prefix = self.config.container.egress.network_prefix
                full_prefix = f"{network_prefix}-{prefix}"
                for name in self.containers.list_egress_networks(network_prefix):
                    if not name.startswith(full_prefix):
                        continue
                    run_id = name[len(full_prefix):]
                    if run_id and run_id not in active:
                        with contextlib.suppress(IsolationError):
                            self.containers.remove_egress(f"{prefix}{run_id}")
                            report["egress_networks_removed"].append(name)
        for path in self.worktrees.list_dirs():
            run_id = path.name
            if run_id in active:
                continue
            with contextlib.suppress(IsolationError):
                self.worktrees.remove(run_id)
            force_rmtree(path)  # husks survive deregistration (WSL race)
            report["worktrees_removed"].append(run_id)
        report["corrupt_runs"] = self.store.invalid_runs()
        return report

    # -- selection --------------------------------------------------------------

    def _pick_ticket(self) -> Ticket | None:
        """
        @brief   Select the top eligible ticket (design 5/5b).
        @details list_ready -> drop control-labelled (hold/exclude always
                 win) -> drop tickets with existing runs -> readiness filter
                 -> order by priority label then lowest iid.
        @return  The ticket to conduct, or None.
        """
        labels = self.config.labels
        candidates = []
        for ticket in self.forge.list_ready(labels.lifecycle.ready):
            if labels.control.hold in ticket.labels:
                continue
            if labels.control.exclude in ticket.labels:
                continue
            if self.store.exists(self._run_id(ticket.iid)):
                continue
            if not self._ready(ticket):
                continue
            candidates.append(ticket)
        if not candidates:
            return None
        order = self.config.labels.selection.priority_order()

        def rank(ticket: Ticket) -> tuple[int, int]:
            for index, label in enumerate(order):
                if label in ticket.labels:
                    return (index, ticket.iid)
            return (len(order), ticket.iid)

        return sorted(candidates, key=rank)[0]

    def _ready(self, ticket: Ticket) -> bool:
        """
        @brief      The readiness filter (design 5): reject under-specified
                    tickets up front; clarification handles the rest mid-run.
        @details    Enforced today: priority label and acceptance criteria
                    (heading or task-list heuristic). known_component and
                    scope_hint remain config intent, not yet enforced.
        @param[in]  ticket Candidate ticket.
        @return     True when the ticket may be conducted.
        """
        readiness = self.config.readiness
        if readiness.require_priority_label:
            order = self.config.labels.selection.priority_order()
            if not any(label in ticket.labels for label in order):
                return False
        if readiness.require_acceptance_criteria:
            text = ticket.description.lower()
            if "acceptance criteria" not in text and "- [ ]" not in ticket.description:
                return False
        return True

    # -- claim and conduct ---------------------------------------------------------

    def _claim_and_conduct(self, ticket: Ticket) -> None:
        """
        @brief      Claim a ticket (local snapshot = the lock) and conduct it.
        @details    Design 8a: snapshot ticket.json + content hash, create the
                    RunState, then run the gate loop.
        @param[in]  ticket The selected ticket.
        """
        run_id = self._run_id(ticket.iid)
        run = RunState(
            run_id=run_id,
            ticket_iid=ticket.iid,
            stage="intake",
            lifecycle="working",
            content_hash=content_hash(ticket.title, ticket.description),
            branch=self._branch_name(run_id, ticket.iid),
            base_ref=f"origin/{self.config.delivery.target_branch}",
            container=self.identity.container_name(run_id),
        )
        comments = self.forge.list_comments(ticket.iid)
        run.last_seen_comment_id = max((c.id for c in comments), default=None)
        self.store.save(run)
        self.store.save_ticket(run_id, {
            "iid": ticket.iid,
            "title": ticket.title,
            "description": ticket.description,
            "labels": ticket.labels,
            "author": ticket.author,
            "web_url": ticket.web_url,
            "snapshotted_at": utc_now_iso(),
        })
        self.store.journal(run_id, "picked", ticket=ticket.iid, title=ticket.title)
        self.log(f"picked #{ticket.iid} '{ticket.title}' -> {run_id}")
        self._conduct(run, ticket)

    def _conduct(self, run: RunState, ticket: Ticket, thread: str = "") -> None:
        """
        @brief      Provision the run and drive the AEGIS stage loop.
        @details    Wraps `_conduct_stages` so every typed AEGIS failure -
                    unparseable envelope, unsupported exit code, unknown or
                    regressing stage, timeout - ends in one deterministic
                    escalation instead of leaking out of the poll pass.
        @param[in]  run The run.
        @param[in]  ticket Current ticket (for prompts).
        @param[in]  thread Rendered clarification thread ("" outside resume).
        """
        if run.stage == PUBLICATION_STAGE:
            # fail closed: silently restarting the stage loop regressed a
            # publishing run once (live finding 2026-07-04)
            self._escalate(run, f"internal: conduct called with stage {run.stage!r}")
            return
        with self._conducting(run.run_id):
            try:
                self._provision(run)
            except IsolationError as exc:
                self._escalate(run, f"isolation failed: {exc}")
                return
            execute = partial(self.containers.exec, run.container,
                              env=self._container_env(run))
            client = AegisClient(execute, run_id=run.aegis_run_id or "")
            try:
                self._conduct_stages(run, ticket, client, thread)
            except AegisError as exc:
                self._escalate_aegis(run, exc)

    @contextlib.contextmanager
    def _conducting(self, run_id: str) -> Iterator[None]:
        """
        @brief      Mark a run as driven by THIS process for its duration.
        @details    Stale-`working` detection cannot tell a crashed conductor
                    from a live one by state alone - both leave
                    `lifecycle = "working"` on disk. This marker is the
                    difference. It nests (publication runs inside conduction)
                    by saving and restoring the previous value rather than
                    clearing it, and unwinds on any exception, so a failure
                    mid-conduct never leaves a run permanently exempt from the
                    staleness sweep.
        @param[in]  run_id The run being conducted.
        """
        previous = self._in_flight_run_id
        self._in_flight_run_id = run_id
        try:
            yield
        finally:
            self._in_flight_run_id = previous

    def _conduct_stages(
        self,
        run: RunState,
        ticket: Ticket,
        client: AegisClient,
        thread: str = "",
    ) -> None:
        """
        @brief      The `next`-driven AEGIS stage loop (plan WP3).
        @details    AEGIS owns the stage pointer; ADORE reads it from
                    `run status` every iteration and checks it against the
                    static allowlist for the run's profile. Per stage: launch
                    the executor to fill and apply the stage forms, then
                    verify objectively (`stage show` readiness, plus
                    `verify run` for validation and delivery) and issue
                    `stage close` as the delegated approver. Questions park,
                    failures retry the same stage within budgets, blocks
                    escalate. When AEGIS reports the run complete, ADORE's own
                    publication phase takes over.
        @param[in]  run The run.
        @param[in]  ticket Current ticket (for prompts and label mapping).
        @param[in]  thread Rendered clarification thread ("" outside resume).
        @exception  AegisError Propagated to `_conduct` for escalation.
        """
        if not self._ensure_aegis_run(run, ticket, client):
            return
        failure_context = ""
        run_kind, quick = self._run_kind(ticket)
        expected_profile = "quick" if quick else "full"
        closed_index = -1
        lock_retries = 0
        while True:
            budget_reason = self._budget_exceeded(run)
            if budget_reason:
                self._escalate(run, budget_reason)
                return
            status = client.run_status()
            if not status.ok:
                if not self._retryable(run, status, "run status", client,
                                       lock_retries):
                    return
                lock_retries += 1
                continue
            terminal_outcome = status.terminal_outcome
            if terminal_outcome is not None:
                graph = self._load_aegis_graph(run)
                assert graph is not None
                graph_outcome = (
                    "abandoned" if graph.get("outcome") == "abandoned" else "normal"
                )
                if graph["complete"] is not True or graph_outcome != terminal_outcome:
                    raise AegisArtifactError(
                        "AEGIS terminal status disagrees with graph.json "
                        f"(status={terminal_outcome!r}, graph={graph_outcome!r}, "
                        f"complete={graph['complete']!r})"
                    )
            if terminal_outcome == "normal":
                self.store.journal(run.run_id, "aegis-run-complete",
                                   aegis_run=client.run_id)
                break
            if terminal_outcome == "abandoned":
                self._end_abandoned(run)
                return
            stage = self._checked_stage(
                status, closed_index, expected_profile=expected_profile
            )
            run.stage = stage
            self._mark(run, "working", stage)

            context = self._stage_context(
                run,
                client,
                status,
                expected_profile=expected_profile,
                expected_kind=run_kind,
                lock_retries=lock_retries,
            )
            if context is None:
                return
            if isinstance(context, AegisResponse):
                lock_retries += 1
                continue

            shown = self._validated_stage_show(client, stage)
            if not shown.ok:
                if not self._retryable(
                    run, shown, f"stage show ({stage})", client, lock_retries
                ):
                    return
                lock_retries += 1
                continue
            state = shown.detail("state")
            unavailable = context.unavailable_current_artifact
            if unavailable is not None:
                recovery = unavailable.recovery_command
                if recovery == "aegis stage prepare":
                    if state != "not-prepared":
                        raise AegisProtocolError(
                            "AEGIS context requested stage prepare for a stage "
                            f"reported as {state!r}"
                        )
                    prepared = client.stage_prepare()
                    if not prepared.ok:
                        if not self._retryable(
                            run,
                            prepared,
                            f"stage prepare ({stage})",
                            client,
                            lock_retries,
                        ):
                            return
                        lock_retries += 1
                        continue
                    self.store.journal(run.run_id, "stage-recovered",
                                       stage=stage, recovery=recovery)
                    lock_retries = 0
                    continue
                if recovery != "aegis stage show":
                    raise AegisProtocolError(
                        f"unsupported AEGIS context recovery {recovery!r}"
                    )
                self.store.journal(run.run_id, "stage-recovered",
                                   stage=stage, recovery=recovery)
                if state == "prepared":
                    raise AegisProtocolError(
                        f"AEGIS {stage} stage is prepared but its required form "
                        "is unavailable after the prescribed stage-show recovery"
                    )

            questions = self._stage_questions(run, stage)
            if questions:
                if not thread:
                    self.store.journal(run.run_id, "stage-questions", stage=stage)
                    self._park(run, questions)
                    return
                if not failure_context:
                    failure_context = self._failure_context(
                        run,
                        "The human supplied a clarification thread for these "
                        "previously recorded stage questions. Reconcile the "
                        "answer into the current applied form, clear only the "
                        "questions it resolves, and apply again:\n"
                        f"{questions}",
                    )

            if (
                state == "applied"
                and shown.detail("ready") is True
                and not failure_context
            ):
                self.store.journal(
                    run.run_id, "stage-restart-ready", stage=stage,
                    action="skip-executor",
                )
                verdict, evidence = self._verify_stage(
                    run, client, stage, shown=shown
                )
                if verdict:
                    failure_context = self._failure_context(
                        run, verdict, evidence
                    )
                else:
                    if not self._close_stage(
                        run, client, stage, run_kind, status, lock_retries
                    ):
                        return
                    failure_context = ""
                    lock_retries = 0
                    closed_index = self._expected_stages(
                        status, expected_profile=expected_profile
                    ).index(stage)
                continue

            if state == "applied":
                if not failure_context:
                    blockers = list(shown.detail("blockers") or [])
                    listed = "\n".join(f"- {item}" for item in blockers)
                    failure_context = self._failure_context(
                        run,
                        f"The applied {stage} stage is not objectively ready after "
                        "restart. Resolve its blockers without preparing or "
                        f"regenerating the stage form:\n"
                        f"{listed or '- (none reported)'}",
                        shown,
                    )
            elif state != "prepared":
                raise AegisProtocolError(
                    f"AEGIS current stage {stage!r} has unexpected state {state!r}"
                )

            orientation = self._validated_bootstrap(run, context)
            run.iterations += 1
            self.store.save(run)
            self.store.journal(run.run_id, "stage-launch", stage=stage,
                               iteration=run.iterations,
                               next=status.next_command)
            result = self.executor.run_gate(
                execute=client.execute,
                worktree=self.worktrees.path_for(run.run_id),
                io_dir=self._io_dir(run.run_id),
                prompt=self._gate_prompt(stage, ticket, failure_context, thread,
                                         orientation, status,
                                         client.run_id),
                session=run.executor_session,
                timeout=self._stage_timeout(stage),
                archive_stem=f"{run.iterations:03d}-{stage}",
            )
            run.executor_session = result.session_id or run.executor_session
            self.store.save(run)
            self._journal_artifacts(run, stage, result)
            self._journal_usage(run, stage, result)
            if result.has_questions:
                self._park(run, result.questions)
                return
            if not result.ok:
                failure_context = self._failure_context(
                    run,
                    f"The previous attempt of the {stage} stage failed "
                    f"(exit {result.exit_code}). stderr tail:\n"
                    + self._tail_lines(result.stderr, 1500),
                )
                self.store.journal(run.run_id, "stage-failed", stage=stage,
                                   exit_code=result.exit_code)
                continue  # retry the same stage, bounded by budgets
            questions = self._stage_questions(run, stage)
            if questions:
                self.store.journal(run.run_id, "stage-questions", stage=stage)
                self._park(run, questions)
                return
            verdict, evidence = self._verify_stage(run, client, stage)
            if verdict:
                failure_context = self._failure_context(run, verdict, evidence)
                continue  # relaunch the same stage with what is still missing
            if not self._close_stage(
                run, client, stage, run_kind, status, lock_retries
            ):
                return
            failure_context = ""
            lock_retries = 0  # a closed stage is real progress
            closed_index = self._expected_stages(
                status, expected_profile=expected_profile
            ).index(stage)
        self._deliver(run, ticket, thread)

    def _ensure_aegis_run(
        self,
        run: RunState,
        ticket: Ticket,
        client: AegisClient,
    ) -> bool:
        """
        @brief      Start the AEGIS run once, persisting its id immediately.
        @details    A run that already carries `aegis_run_id` is resumed, never
                    restarted. The kind and profile come from the ticket labels
                    via `[workflow]`; the minted id is saved before anything
                    else happens so a crash right after `run start` cannot
                    orphan a governed run. A blocked start goes through the
                    same iterative `_retryable` loop the stage loop uses, so a
                    persistence lock that is still held on the second attempt
                    escalates through the exhausted-lock path instead of
                    leaving the run stranded in `working`.
        @param[in]  run The run.
        @param[in]  ticket Current ticket (label source).
        @param[in,out] client Client that captures the run id.
        @return     True when a run id is available; False when the start was
                    blocked and the run has already been parked/escalated.
        @exception  AegisError When the CLI contract is violated.
        """
        if client.run_id:
            return True
        kind, quick = self._run_kind(ticket)
        context = f"run start {kind}"
        lock_retries = 0
        response = client.run_start(kind, quick)
        while not response.ok:
            if not self._retryable(run, response, context, None, lock_retries):
                return False
            lock_retries += 1
            response = client.run_start(kind, quick)
        run.aegis_run_id = client.run_id
        run.stage = response.stage or STANDARD_STAGES[0]
        self.store.save(run)
        self.store.journal(run.run_id, "aegis-run-started",
                           aegis_run=client.run_id, kind=kind, quick=quick)
        for warning in response.warnings:
            self.store.journal(run.run_id, "aegis-run-warning", warning=warning)
            self.log(f"{run.run_id}: AEGIS warning: {warning}")
        self.log(f"{run.run_id}: AEGIS run {client.run_id} started "
                 f"({kind}{', quick' if quick else ''})")
        return True

    def _run_kind(self, ticket: Ticket) -> tuple[str, bool]:
        """
        @brief      Map ticket labels to an AEGIS run kind and profile.
        @details    Design decision 6: the quick profile is label-driven.
                    `[workflow] kind_labels` maps a label to a kind (first
                    match in configuration order wins, so overlapping labels
                    stay deterministic); anything unmapped is `feature`. The
                    quick label only applies to the kinds AEGIS permits, which
                    config validation also enforces up front.
        @param[in]  ticket The ticket being conducted.
        @return     (kind, quick) for `aegis run start`.
        """
        workflow = self.config.workflow
        labels = set(ticket.labels)
        kind = workflow.default_kind
        for label, mapped in workflow.kind_labels.items():
            if label in labels:
                kind = mapped
                break
        quick = bool(workflow.quick_label) and workflow.quick_label in labels
        return kind, quick and kind in QUICK_KINDS

    def _stage_context(
        self,
        run: RunState,
        client: AegisClient,
        status: AegisResponse,
        *,
        expected_profile: str,
        expected_kind: str,
        lock_retries: int,
    ) -> AegisContext | AegisResponse | None:
        """@brief Obtain the validated fresh-session context for one launch."""
        context = client.run_context(
            expected_profile=expected_profile,
            expected_stage=status.stage,
            expected_kind=expected_kind,
        )
        if isinstance(context, AegisContext):
            return context
        if not self._retryable(
            run, context, f"run context ({status.stage})", client, lock_retries
        ):
            return None
        return context

    def _validated_bootstrap(self, run: RunState, context: AegisContext) -> str:
        """
        @brief      Validate and render the complete named executor bootstrap.
        @details    Every required read must resolve to a regular file inside
                    the worktree. Context wire bytes plus file bytes may not
                    exceed the AEGIS 30 KiB fresh-session aggregate bound.
        @return     Bounded context JSON and read-only instructions.
        @exception  AegisProtocolError For invalid bootstrap input.
        """
        worktree = self.worktrees.path_for(run.run_id).resolve()
        total = context.wire_size_bytes
        for relative in context.required_reads:
            candidate = (worktree / relative).resolve()
            if not candidate.is_relative_to(worktree) or not candidate.is_file():
                raise AegisProtocolError(
                    f"AEGIS context required read {relative!r} is unavailable "
                    "or outside the worktree"
                )
            try:
                total += len(candidate.read_bytes())
            except OSError as exc:
                raise AegisProtocolError(
                    f"cannot read AEGIS context bootstrap file {relative!r}: {exc}"
                ) from exc
            if total > CONTEXT_BOOTSTRAP_LIMIT_BYTES:
                raise AegisProtocolError(
                    "AEGIS context bootstrap exceeds the 30720-byte aggregate bound"
                )
        payload = asdict(context)
        payload.pop("wire_size_bytes", None)
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        return self._redact_failure_context(
            "Validated AEGIS fresh-session context (schema data; do not execute "
            "`next_commands` blindly):\n```json\n"
            + rendered
            + "\n```\nRead exactly the listed `required_reads` before working the "
            "current stage. Follow only a recovery operation explicitly handled "
            "by the orchestrator."
        )

    @staticmethod
    def _validated_stage_show(
        client: AegisClient,
        expected_stage: str,
    ) -> AegisResponse:
        """@brief Read and validate the objective current-stage snapshot."""
        shown = client.stage_show()
        if not shown.ok:
            return shown
        if shown.detail("run_id") != client.run_id or shown.stage != expected_stage:
            raise AegisProtocolError(
                "AEGIS stage-show snapshot disagrees with the pinned run/stage"
            )
        state = shown.detail("state")
        if state not in {"not-prepared", "prepared", "applied", "closed"}:
            raise AegisProtocolError(
                f"AEGIS stage-show snapshot has invalid state {state!r}"
            )
        ready = shown.detail("ready")
        blockers = shown.detail("blockers")
        files = shown.detail("files")
        warnings = shown.detail("warnings")
        if not isinstance(ready, bool):
            raise AegisProtocolError("AEGIS stage-show ready must be boolean")
        for key, value in (
            ("blockers", blockers), ("files", files), ("warnings", warnings)
        ):
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise AegisProtocolError(
                    f"AEGIS stage-show {key} must be a string list"
                )
        if ready == bool(blockers):
            raise AegisProtocolError(
                "AEGIS stage-show readiness contradicts its blocker list"
            )
        return shown

    def _close_stage(
        self,
        run: RunState,
        client: AegisClient,
        stage: str,
        run_kind: str,
        status: AegisResponse,
        lock_retries: int,
    ) -> bool:
        """@brief Close one verified stage with truthful delegated identity."""
        closed = client.stage_close(DELEGATED_APPROVER, run_kind=run_kind)
        retries = lock_retries
        while not closed.ok:
            if not self._retryable(
                run, closed, f"stage close ({stage})", client, retries
            ):
                return False
            retries += 1
            closed = client.stage_close(DELEGATED_APPROVER, run_kind=run_kind)
        for advisory in closed.advisories:
            self.store.journal(
                run.run_id,
                "aegis-advisory",
                stage=stage,
                code=advisory.code,
                status=advisory.status,
                message=advisory.message,
                restart_command=advisory.restart_command,
            )
            self.log(
                f"{run.run_id}: {advisory.code}: {advisory.message} "
                f"({advisory.restart_command})"
            )
        self.store.journal(
            run.run_id,
            "stage-closed",
            stage=stage,
            complete=closed.complete,
            approver=DELEGATED_APPROVER,
            profile=(status.detail("run_profile") or "full"),
        )
        return True

    def _end_abandoned(self, run: RunState) -> None:
        """@brief Record an externally abandoned AEGIS run without publishing."""
        run.lifecycle = "failed"
        run.outcome = "aegis-abandoned"
        self.store.save(run)
        self.store.journal(
            run.run_id, "aegis-run-abandoned", aegis_run=run.aegis_run_id
        )
        self._mark(run, "failed", run.stage)
        self._record_metrics(run)
        with contextlib.suppress(IsolationError):
            self.containers.stop(run.container)
        self.log(f"{run.run_id}: AEGIS run was abandoned; publication skipped")

    def _stage_timeout(self, stage: str) -> int:
        """
        @brief      The wall-clock bound for ONE executor launch at a stage.
        @details    `[budgets] per_gate_timeout_seconds` is the default;
                    `[workflow] stage_timeout_overrides` raises or lowers it for
                    individual stages, because implementation and validation
                    routinely need far more room than intake.
        @param[in]  stage AEGIS stage name.
        @return     Seconds.
        """
        override = self.config.workflow.stage_timeout_overrides.get(stage)
        if isinstance(override, int) and not isinstance(override, bool) \
                and override > 0:
            return override
        return self.config.budgets.per_gate_timeout_seconds

    @staticmethod
    def _expected_stages(
        status: AegisResponse,
        *,
        expected_profile: str | None = None,
    ) -> tuple[str, ...]:
        """
        @brief      The stage allowlist for the run's AEGIS profile.
        @details    AEGIS reports `run_profile` only for quick runs; its
                    absence means the full eight-stage sequence.
        @param[in]  status A `run status` response.
        @return     STANDARD_STAGES or QUICK_STAGES.
        """
        reported = status.detail("run_profile")
        if reported not in {None, "quick"}:
            raise AegisProtocolError(
                f"AEGIS status reported unknown run profile {reported!r}"
            )
        actual = "quick" if reported == "quick" else "full"
        if expected_profile is not None and actual != expected_profile:
            raise AegisProtocolError(
                f"AEGIS status profile {actual!r} disagrees with configured "
                f"profile {expected_profile!r}"
            )
        return QUICK_STAGES if actual == "quick" else STANDARD_STAGES

    def _checked_stage(
        self,
        status: AegisResponse,
        closed_index: int,
        *,
        expected_profile: str | None = None,
    ) -> str:
        """
        @brief      Validate the reported stage against the allowlist.
        @details    Two guards, both fail-loud. A stage outside the profile's
                    sequence means the contract moved under ADORE. A stage at
                    or before the last one ADORE already closed means the run
                    was routed backwards - what an approved `route_to`
                    produces - which is explicitly out of scope for 3.0.0, so
                    a human decides. Re-running a stage that is not yet closed
                    is a normal retry and passes both guards. At the sequence
                    boundary - the last stage re-reported after ADORE already
                    closed it, without `complete` being set - there is no
                    "next" stage to name, so the regression is stated
                    generically; it still fails loud as the same typed error
                    rather than an `IndexError` nothing catches.
        @param[in]  status A `run status` response.
        @param[in]  closed_index Index of the last stage ADORE closed (-1 when
                                 it has closed none yet).
        @return     The validated stage name.
        @exception  AegisProtocolError When the stage is unknown or regressed.
        """
        expected = self._expected_stages(
            status, expected_profile=expected_profile
        )
        stage = status.stage
        if stage not in expected:
            raise AegisProtocolError(
                f"AEGIS reported stage {stage!r}, which is not in the expected "
                f"sequence for this run ({', '.join(expected)})"
            )
        if expected.index(stage) <= closed_index:
            if closed_index + 1 < len(expected):
                moved = (f"AEGIS routed the run back from "
                         f"{expected[closed_index + 1]!r} to {stage!r}")
            else:
                moved = (f"AEGIS re-reported the already closed final stage "
                         f"{stage!r} without completing the run")
            raise AegisProtocolError(
                f"{moved}; a stage regression is a human decision in this "
                "ADORE version"
            )
        return stage

    def _verify_stage(
        self,
        run: RunState,
        client: AegisClient,
        stage: str,
        *,
        shown: AegisResponse | None = None,
    ) -> tuple[str, AegisResponse | None]:
        """
        @brief      ADORE's objective check before it closes a stage.
        @details    The conductor never takes the executor's word: `stage show`
                    must report `ready` with no blockers, validation must first
                    have committed work (a clean tree with commits over the
                    base), and the validation and delivery stages must then
                    survive a full `verify run`. The cleanliness check precedes
                    verification because AEGIS itself persists verification
                    evidence; treating those fresh artifacts as executor dirt
                    causes an endless validation relaunch loop.
        @param[in]  run The run.
        @param[in]  client The run's AEGIS client.
        @param[in]  stage Stage just applied by the executor.
        @param[in]  shown Optional already-validated restart snapshot.
        @return     ("", None) when the stage may be closed, else the relaunch
                    reason and the response that produced it (so the caller can
                    attach the response's own evidence).
        @exception  AegisError When the CLI contract is violated.
        """
        shown = shown or self._validated_stage_show(client, stage)
        if not shown.ok:
            return (
                f"AEGIS refused to report the {stage} stage "
                f"(status {shown.status}).",
                shown,
            )
        blockers = [str(item) for item in shown.detail("blockers", []) or []]
        if shown.detail("ready") is not True or blockers:
            self.store.journal(run.run_id, "stage-not-ready", stage=stage,
                               blockers=blockers[:_AGENTIC_FAILURE_ITEMS_LIMIT])
            listed = "\n".join(f"- {item}" for item in blockers) or "- (none reported)"
            return (
                f"The {stage} stage is applied but AEGIS does not consider it "
                f"ready to close. Resolve these blockers, then apply the stage "
                f"again:\n{listed}",
                shown,
            )
        if stage == "validation":
            committed = self._work_committed(run)
            if committed:
                self.store.journal(run.run_id, "work-uncommitted")
                return committed, None
        if stage in ("validation", "delivery"):
            verified = client.verify_run()
            if verified.blocked:
                self.store.journal(run.run_id, "verify-failed", stage=stage,
                                   exit_code=verified.exit_code)
                return (
                    f"`aegis verify run` was blocked at the {stage} stage "
                    f"(exit {verified.exit_code}). Fix every blocking finding "
                    "and re-run it until it passes.",
                    verified,
                )
            summary = self._validated_verification(run, verified)
            verdict = summary["status"]
            if verdict == "failed":
                self.store.journal(run.run_id, "verify-failed", stage=stage,
                                   exit_code=verified.exit_code)
                return (
                    f"`aegis verify run` failed at the {stage} stage "
                    f"(exit {verified.exit_code}). Fix every blocking finding "
                    "and re-run it until it passes.",
                    verified,
                )
            facts = self._verification_facts(summary)
            self.store.journal(
                run.run_id,
                "verify-result",
                stage=stage,
                status=verdict,
                **facts,
            )
            self.log(
                f"{run.run_id}: AEGIS verification at {stage}: {verdict}"
            )
        return "", None

    @staticmethod
    def _verification_facts(summary: dict) -> dict[str, list[str]]:
        """
        @brief      Extract truthful non-pass governance outcomes for surfaces.
        @return     Stable waived, not-enforced, and not-applicable labels.
        """
        waived = [
            f"gate:{name}" for name, item in summary["gates"].items()
            if item["status"] == "waived"
        ]
        not_enforced = [
            name for name, item in summary["gates"].items()
            if item["status"] == "not-enforced"
        ]
        not_applicable = [
            f"invariant:{item['id']}" for item in summary["invariants"]
            if item.get("status") == "not-applicable"
        ]
        for name in ("traceability", "coverage"):
            if any(
                item.get("status") == "not-applicable"
                for item in summary[name]
            ):
                not_applicable.append(name)
        waived.extend(
            f"invariant:{item['id']}" for item in summary["invariants"]
            if item.get("waived") is True
        )
        return {
            "waived": sorted(waived),
            "not_enforced": sorted(not_enforced),
            "not_applicable": sorted(not_applicable),
        }

    def _handle_block(
        self,
        run: RunState,
        response: AegisResponse,
        context: str,
        client: AegisClient | None = None,
    ) -> str:
        """
        @brief      Act on a blocked/failed AEGIS response.
        @details    `classify_block` decides; this method carries the decision
                    out. Park routes into the existing clarification machinery
                    with the recorded questions or request. Escalate ends the
                    run with the exact AEGIS error, its remediation, and - when
                    a waivable blocker is eligible - the exact
                    `aegis waive add` command a human would run. ADORE never
                    waives, routes, or repairs AEGIS state itself.
        @param[in]  run The run.
        @param[in]  response The blocked or failed response.
        @param[in]  context Human-readable command description.
        @param[in]  client The run's client, used only to look up the waive
                           hint; omitted when no run exists yet.
        @return     The action taken: BLOCK_PARK, BLOCK_RETRY, or
                    BLOCK_ESCALATE.
        """
        decision = classify_block(response, self._stage_record(run, response.stage))
        self.store.journal(run.run_id, "aegis-blocked", context=context,
                           status=response.status, code=response.code,
                           action=decision.action)
        if decision.action == BLOCK_RETRY:
            self.log(f"{run.run_id}: {decision.reason}; retrying `{context}`")
            return BLOCK_RETRY
        if decision.action == BLOCK_PARK:
            questions = self._stage_questions(run, response.stage) or (
                f"AEGIS paused the {response.stage} stage: {decision.reason}.\n"
                f"{response.error or ''}".strip()
            )
            self._park(run, self._redact_failure_context(questions))
            return BLOCK_PARK
        reason = f"AEGIS blocked `{context}`: {decision.reason}"
        if decision.hint:
            reason += f" | remediation: {decision.hint}"
        waive_hint = self._waive_hint(client)
        if waive_hint:
            reason += f" | {waive_hint}"
        self._escalate(run, self._redact_failure_context(reason))
        return BLOCK_ESCALATE

    def _retryable(
        self,
        run: RunState,
        response: AegisResponse,
        context: str,
        client: AegisClient | None,
        attempts: int,
    ) -> bool:
        """
        @brief      Handle a block and report whether the caller may retry.
        @details    Only a live persistence lock is retryable, and only
                    `_MAX_LOCK_RETRIES` times in a row: after that the lock is
                    not transient and a human has to look. Any other action
                    (park or escalate) has already ended the run.
        @param[in]  run The run.
        @param[in]  response The blocked or failed response.
        @param[in]  context Human-readable command description.
        @param[in]  client The run's client (for the waive hint).
        @param[in]  attempts Consecutive retries already spent.
        @return     True when the caller should sleep and re-issue the command.
        """
        action = self._handle_block(run, response, context, client)
        if action != BLOCK_RETRY:
            return False
        if attempts >= _MAX_LOCK_RETRIES:
            self._escalate(
                run,
                self._redact_failure_context(
                    f"AEGIS blocked `{context}`: the persistence lock is still "
                    f"held after {attempts + 1} attempts; another AEGIS process "
                    "is running against this repository"
                ),
            )
            return False
        self.sleep(_LOCK_RETRY_DELAY)
        return True

    def _waive_hint(self, client: AegisClient | None) -> str:
        """
        @brief      The exact `aegis waive add` command a human could run.
        @details    Design decision 3: ADORE never waives, but an escalation
                    that names the eligible blocker IDs saves the human a round
                    trip. The hint is advisory only - if `waive list` itself is
                    unavailable the escalation still carries the original AEGIS
                    error, which is the part that must never be lost.
        @param[in]  client The run's client, or None when no run exists.
        @return     The hint text, or "" when there is nothing waivable.
        """
        if client is None or not client.run_id:
            return ""
        try:
            listed = client.waive_list()
        except AegisError:
            return ""
        if not listed.ok:
            return ""
        ids = [
            str(item.get("id"))
            for item in (listed.detail("eligible_blockers") or [])
            if isinstance(item, dict) and item.get("id")
        ][:_AGENTIC_FAILURE_ITEMS_LIMIT]
        if not ids:
            return ""
        commands = "; ".join(
            f'aegis waive add {blocker} --reason "<why>"' for blocker in ids
        )
        return (
            "a human may waive one of these after deciding it is acceptable: "
            + commands
        )

    def _stage_record(self, run: RunState, stage: str) -> dict | None:
        """
        @brief      The graph's stage record for one stage, when readable.
        @param[in]  run The ADORE run.
        @param[in]  stage Stage name.
        @return     The `stage_records[<stage>]` mapping, or None.
        """
        run_dir = self._aegis_run_dir(run)
        if run_dir is None or not stage or stage == "none":
            return None
        graph = self._load_aegis_graph(run)
        assert graph is not None
        records = graph["stage_records"]
        record = records.get(stage) if isinstance(records, dict) else None
        return record if isinstance(record, dict) else None

    def _escalate_aegis(self, run: RunState, exc: AegisError) -> None:
        """
        @brief      Escalate a typed AEGIS contract failure.
        @details    These never mean "the executor needs another try": the
                    payload is unsupported, the command was malformed, or the
                    CLI did not answer in time. Tagging the reason tells the
                    operator to look at ADORE or the payload, not the ticket.
        @param[in]  run The run.
        @param[in]  exc The raised AegisError.
        """
        kind = type(exc).__name__
        self.store.journal(run.run_id, "aegis-contract-failure", kind=kind)
        self._escalate(
            run,
            self._redact_failure_context(f"AEGIS contract failure ({kind}): {exc}"),
        )

    def _work_committed(self, run: RunState) -> str:
        """
        @brief      Deterministic pre-delivery check: is the work committed?
        @details    Pilot finding 2026-07-03: a run validated with a dirty
                    tree and zero commits - work that could never reach an
                    MR. A dirty tree or an empty branch relaunches the
                    validation gate with this as context (budget-bounded).
        @param[in]  run The run after a passing validation gate.
        @return     Failure context for the relaunch, or "" when committed.
        """
        try:
            if self.worktrees.is_dirty(run.run_id):
                return ("The gates passed but the worktree has UNCOMMITTED "
                        "changes. Commit ALL your work locally (including the "
                        ".agentic records and new files) with a descriptive "
                        "message, then re-run the validation checks.")
            if run.base_ref and self.worktrees.commits_ahead(run.run_id,
                                                             run.base_ref) == 0:
                return ("The gates passed but the branch has NO commits over "
                        "its base. Commit your work locally with a "
                        "descriptive message, then re-run validation.")
        except IsolationError as exc:
            return f"Could not verify the committed state: {exc}"
        return ""

    # -- delivery (design 11a) -------------------------------------------------

    def _deliver(self, run: RunState, ticket: Ticket, thread: str = "",
                 revise: bool = False) -> None:
        """
        @brief      The publication sequence: integrate, verify, push, open the
                    DRAFT MR (design 11a - exact order).
        @details    Runs after AEGIS reported the governed run complete. The
                    orchestrator owns all git plumbing and the remote; the
                    executor is relaunched only for code reasoning (conflict
                    resolution, fixing what `aegis verify run` reports), bounded
                    by run budgets. An already-open MR for the branch is
                    adopted, never duplicated (idempotent recovery). Never
                    merges.
        @param[in]  run The run whose AEGIS run is complete.
        @param[in]  ticket Current ticket.
        @param[in]  thread Rendered clarification/review thread.
        @param[in]  revise True inside the revise cycle: skip MR adoption and
                    update the existing MR instead of creating one.
        """
        with self._conducting(run.run_id):
            run.stage = PUBLICATION_STAGE
            run.lifecycle = "working"
            self.store.save(run)
            self._mark(run, "working", PUBLICATION_STAGE)
            self.store.journal(run.run_id, "delivery-start")
            try:
                self._provision(run)
                self.worktrees.fetch()
            except IsolationError as exc:
                self._escalate(run, f"delivery isolation failed: {exc}")
                return
            execute = partial(self.containers.exec, run.container,
                              env=self._container_env(run))
            client = AegisClient(execute, run_id=run.aegis_run_id or "")
            try:
                self._publish(run, ticket, client, thread, revise)
            except AegisError as exc:
                self._escalate_aegis(run, exc)

    def _publish(self, run: RunState, ticket: Ticket, client: AegisClient,
                 thread: str, revise: bool) -> None:
        """
        @brief      The publication steps proper (design 11a steps 2-8).
        @details    Split out of `_deliver` so every typed AEGIS failure raised
                    by the final verification or the delivery report ends in the
                    same deterministic escalation.
        @param[in]  run The run.
        @param[in]  ticket Current ticket.
        @param[in]  client The run's AEGIS client.
        @param[in]  thread Rendered clarification/review thread.
        @param[in]  revise True inside the revise cycle.
        @exception  AegisError Propagated to `_deliver` for escalation.
        """
        if not revise:
            # idempotent recovery: adopt an MR already open for this branch
            with contextlib.suppress(ForgeError):
                existing = self.forge.get_merge_request(run.mr_iid or run.branch)
                if existing and existing.state == "opened":
                    existing_summary = self._load_validation_summary(
                        run, required=False
                    )
                    self._enter_review(
                        run,
                        existing,
                        self._governance_note(existing_summary)
                        if existing_summary else "",
                    )
                    return
        # 2. integrate the target branch (conflicts -> executor resolves)
        while True:
            if not self.worktrees.merge_in_progress(run.run_id):
                merge = self.worktrees.merge(run.run_id, run.base_ref)
                if merge.ok and not self.worktrees.is_dirty(run.run_id):
                    break
                conflict_tail = (merge.stdout + merge.stderr)[-1500:]
            else:
                conflict_tail = "a previous merge is still unresolved"
            context = (
                f"Integrating {run.base_ref} produced merge conflicts. Resolve "
                "ALL conflicts, complete the merge commit, make sure the tests "
                "still pass, and leave a clean tree.\n" + conflict_tail
            )
            if not self._delivery_fix(run, ticket, client, context, thread):
                return
        self.store.journal(run.run_id, "target-merged", base=run.base_ref)
        # 3./4. one authoritative post-merge verification: integrating the
        # target branch can break a change that passed in isolation. In AEGIS
        # 3.x `verify run` IS the gate run plus the invariant, traceability,
        # coverage and working-tree audits, so it replaces both 1.x steps.
        while True:
            verified = client.verify_run()
            verification_summary = None
            if not verified.blocked:
                verification_summary = self._validated_verification(run, verified)
                if verification_summary["status"] in {"ok", "waived"}:
                    facts = self._verification_facts(verification_summary)
                    self.store.journal(
                        run.run_id,
                        "verify-run-result",
                        status=verification_summary["status"],
                        **facts,
                    )
                    self.log(
                        f"{run.run_id}: post-merge AEGIS verification: "
                        f"{verification_summary['status']}"
                    )
                    break
            context = self._failure_context(
                run,
                f"`aegis verify run` failed (exit {verified.exit_code}) after "
                f"merging {run.base_ref}. Fix every blocking finding, commit "
                "your changes, and leave a clean tree.",
                verified,
            )
            if not self._delivery_fix(run, ticket, client, context, thread):
                return
        # Compose the MR body before pushing: the report command generates
        # `.agentic` artifacts that must be committed with the delivered branch.
        assert verification_summary is not None
        title = f"Resolve #{ticket.iid}: {ticket.title}"
        body = "" if revise and run.mr_iid else self._mr_description(
            run, ticket, client, verification_summary
        )
        try:
            if self.worktrees.commit_all_if_dirty(
                run.run_id, f"Record delivery verification for ticket {ticket.iid}"
            ):
                self.store.journal(run.run_id, "delivery-artifacts-committed")
        except IsolationError as exc:
            self._escalate(run, f"delivery artifact commit failed: {exc}")
            return
        # 5. push (the only remote-writing git call; executor cannot push)
        push = self.worktrees.push(run.run_id, run.branch)
        if not push.ok:
            self._escalate(run, f"push failed: {(push.stderr or push.stdout)[-300:]}")
            return
        self.store.journal(run.run_id, "pushed", branch=run.branch)
        if revise and run.mr_iid:
            # the same branch backs the MR: the push updated it in place and
            # it stays a draft; just re-enter review with an update comment
            self.store.journal(run.run_id, "mr-updated", mr=run.mr_url)
            self._enter_review(
                run, None, self._governance_note(verification_summary)
            )
            return
        # 6. open the DRAFT MR - never a merge flag, never merge
        try:
            url = self.forge.open_merge_request(
                run.branch,
                self.config.delivery.target_branch,
                title,
                body,
                draft=True,
                reviewers=self.config.delivery.reviewers,
                remove_source_branch=self.config.delivery.remove_source_branch,
                cwd=str(self.worktrees.path_for(run.run_id)),
            )
        except ForgeError as exc:
            self._escalate(run, f"MR creation failed: {exc}")
            return
        run.mr_url = url
        run.mr_iid = self._parse_mr_iid(url)
        self.store.save(run)
        self.store.journal(run.run_id, "mr-opened", url=url)
        self._enter_review(
            run, None, self._governance_note(verification_summary)
        )

    def _delivery_fix(
        self,
        run: RunState,
        ticket: Ticket,
        client: AegisClient,
        context: str,
        thread: str = "",
    ) -> bool:
        """
        @brief      One budget-bounded executor relaunch during publication.
        @param[in]  run The run.
        @param[in]  ticket Current ticket.
        @param[in]  client The run's AEGIS client (exec seam + orientation).
        @param[in]  context What failed and what to do.
        @param[in]  thread Rendered clarification/review thread.
        @return     True to re-check; False when the run ended (escalated or
                    parked).
        @exception  AegisError When the CLI contract is violated.
        """
        reason = self._budget_exceeded(run)
        if reason:
            self._escalate(run, reason)
            return False
        run.iterations += 1
        self.store.save(run)
        self.store.journal(run.run_id, "delivery-fix", iteration=run.iterations)
        orientation = self._workflow_orientation(client)
        result = self.executor.run_gate(
            client.execute,
            self.worktrees.path_for(run.run_id),
            self._io_dir(run.run_id),
            self._gate_prompt("validation", ticket, context, thread,
                              orientation, None, client.run_id),
            session=run.executor_session,
            timeout=self.config.budgets.per_gate_timeout_seconds,
            archive_stem=f"{run.iterations:03d}-delivery-fix",
        )
        run.executor_session = result.session_id or run.executor_session
        self.store.save(run)
        self._journal_artifacts(run, "delivery-fix", result)
        self._journal_usage(run, "delivery-fix", result)
        if result.has_questions:
            self._park(run, result.questions)
            return False
        return True

    def _enter_review(
        self,
        run: RunState,
        adopted: MergeRequest | None,
        governance_note: str = "",
    ) -> None:
        """
        @brief      Hand off to human review, keeping the environment alive.
        @details    Design 11a step 8: container stopped (not removed),
                    worktree kept, so review feedback can resume without
                    re-provisioning. Status -> review; kind=delivery comment
                    carries the MR link.
        @param[in]  run The run.
        @param[in]  adopted An already-open MR when adopting, else None.
        @param[in]  governance_note Truthful verification outcome summary.
        """
        if adopted is not None:
            run.mr_iid = adopted.iid
            run.mr_url = adopted.web_url or run.mr_url
        run.lifecycle = "in-review"
        self.store.save(run)
        self._mark(run, "review", "delivery")
        note_line = f"Governance: {governance_note}\n" if governance_note else ""
        with contextlib.suppress(ForgeError):
            self.forge.post_comment(run.ticket_iid, (
                f"{self.identity.tag} Draft MR ready for review: {run.mr_url}\n"
                f"{note_line}"
                "Review and merge stay human decisions; this MR was opened as "
                "a draft and will never be merged by the agent.\n"
                f"{self.identity.make_marker(run.run_id, 'delivery')}"
            ))
        with contextlib.suppress(IsolationError):
            self.containers.stop(run.container)
        self.store.journal(run.run_id, "in-review", mr=run.mr_url)
        self.log(f"{run.run_id}: draft MR open, awaiting human review ({run.mr_url})")

    def _check_review(self, run: RunState, summary: dict) -> None:
        """
        @brief      Post-MR poll (design 11b).
        @details    Open + revise label -> the revise cycle; merged -> done +
                    full teardown (state kept for audit); closed without
                    merge -> failed + teardown. A plain comment without the
                    label never triggers anything (11b: no auto-react).
        @param[in]  run The in-review run.
        @param[in,out] summary Poll summary counters.
        """
        try:
            mr = self.forge.get_merge_request(run.mr_iid or run.branch)
        except ForgeError as exc:
            self.log(f"{run.run_id}: MR check failed: {exc}")
            return
        if mr is None:
            # a real deletion, not a transient forge error (those raise above
            # and are retried). Ride out a few blips, then end the run so it
            # cannot stay in-review and re-log "not found" on every poll.
            run.mr_missing_polls += 1
            self.store.save(run)
            self.store.journal(run.run_id, "mr-missing",
                               polls=run.mr_missing_polls)
            self.log(f"{run.run_id}: MR {run.mr_iid or run.branch} not found "
                     f"({run.mr_missing_polls}/{_MR_MISSING_GRACE_POLLS})")
            if run.mr_missing_polls >= _MR_MISSING_GRACE_POLLS:
                self._escalate(
                    run, f"MR {run.mr_iid or run.branch} no longer exists"
                )
            return
        if run.mr_missing_polls:
            run.mr_missing_polls = 0  # MR is back; clear the blip counter
            self.store.save(run)
        if mr.state == "opened":
            # design 11b: never auto-react to mere comments; the explicit
            # revise label is the trigger (trigger modes other than "label"
            # are treated as "label" until implemented)
            if self.config.review.revise_label in mr.labels:
                self._revise(run, mr, summary)
            return
        if mr.state == "merged":
            run.lifecycle = "done"
            run.outcome = "merged"
            self.store.save(run)
            self.store.journal(run.run_id, "merged", mr=run.mr_url)
            self._mark(run, "done", "delivery")
            self._record_metrics(run)
            self._teardown(run, remove_worktree=True)
            summary["done"] += 1
            self.log(f"{run.run_id}: MR merged by a human; run done")
        elif mr.state == "closed":
            run.lifecycle = "failed"
            run.outcome = "mr-closed"
            self.store.save(run)
            self.store.journal(run.run_id, "mr-closed", mr=run.mr_url)
            self._mark(run, "failed", "delivery")
            self._record_metrics(run)
            self._teardown(run, remove_worktree=True)
            summary["mr_closed"] += 1
            self.log(f"{run.run_id}: MR closed without merge; run ended")

    def _revise(self, run: RunState, mr: MergeRequest, summary: dict) -> None:
        """
        @brief      The revise cycle (design 11b): reviewer asked for changes.
        @details    Exact order: 1. rounds cap (exceeded -> failed); 2. clear
                    the trigger label FIRST (a re-applied label re-triggers
                    the next poll, never loops this one); 3. restart the
                    retained environment; 4. launch the executor with the MR
                    review thread; 5. re-run the delivery tail (merge, gates,
                    preflight, push to the SAME branch - the MR updates and
                    stays draft) and post the kind=delivery update comment.
        @param[in]  run The in-review run.
        @param[in]  mr The open MR carrying the revise label.
        @param[in,out] summary Poll summary counters.
        """
        run.review_rounds += 1
        if run.review_rounds > self.config.review.max_review_rounds:
            self._escalate(run, "review rounds exhausted")
            return
        ticket = self.forge.get_ticket(run.ticket_iid)
        if ticket is None:
            self._teardown(run, remove_worktree=True)
            run.lifecycle = "failed"
            run.outcome = "orphaned"
            self.store.save(run)
            self.store.journal(run.run_id, "orphaned")
            self._record_metrics(run)
            return
        with contextlib.suppress(ForgeError):
            self.forge.remove_mr_labels(mr.iid, [self.config.review.revise_label])
        run.lifecycle = "working"
        run.created_at = ""  # review wait is not work time; save() re-stamps
        run.iterations = 0
        self.store.save(run)
        self.store.journal(run.run_id, "revise-start", round=run.review_rounds)
        self._mark(run, "working", "revise")
        self.log(f"{run.run_id}: reviewer requested changes "
                 f"(round {run.review_rounds}); revising")
        try:
            self._provision(run)
        except IsolationError as exc:
            self._escalate(run, f"revise isolation failed: {exc}")
            return
        thread = self._render_thread(self.forge.list_mr_comments(mr.iid))
        execute = partial(self.containers.exec, run.container, env=self._container_env(run))
        client = AegisClient(execute, run_id=run.aegis_run_id or "")
        try:
            orientation = self._workflow_orientation(client)
        except AegisError as exc:
            self._escalate_aegis(run, exc)
            return
        run.iterations += 1
        self.store.save(run)
        result = self.executor.run_gate(
            execute,
            self.worktrees.path_for(run.run_id),
            self._io_dir(run.run_id),
            self._gate_prompt("revise", ticket, "", thread, orientation,
                              None, client.run_id),
            session=run.executor_session,
            timeout=self.config.budgets.per_gate_timeout_seconds,
            archive_stem=f"{run.iterations:03d}-revise",
        )
        run.executor_session = result.session_id or run.executor_session
        self.store.save(run)
        self._journal_artifacts(run, "revise", result)
        self._journal_usage(run, "revise", result)
        if result.has_questions:
            self._park(run, result.questions)
            return
        summary["revised"] += 1
        # re-run the full delivery tail; the existing MR is updated, not
        # recreated (run.mr_iid is set), and stays a draft
        self._deliver(run, ticket, thread, revise=True)

    def _mr_description(
        self,
        run: RunState,
        ticket: Ticket,
        client: AegisClient,
        verification_summary: dict,
    ) -> str:
        """
        @brief      Compose the draft MR description (design 11).
        @details    "Related to #N", never an auto-close keyword - closure is
                    the human's call. `aegis delivery report` renders the
                    run's report; its content is embedded bounded, together
                    with the AEGIS run id and the hidden ADORE marker.
        @param[in]  run The run.
        @param[in]  ticket Current ticket.
        @param[in]  client The run's AEGIS client.
        @param[in]  verification_summary Validated post-merge AEGIS result.
        @return     The MR body.
        @exception  AegisError When the CLI contract is violated.
        """
        report = client.delivery_report()
        if not report.ok:
            raise AegisProtocolError(
                f"AEGIS `delivery report` reported {report.status}: "
                f"{report.error or 'no detail'}"
            )
        expected = f"{_AEGIS_RUN_DIR}/{client.run_id}/report.md"
        if report.detail("report") != expected or report.artifact != expected:
            raise AegisArtifactError(
                "AEGIS delivery report response did not name the pinned "
                f"run's report.md ({expected})"
            )
        body = self._read_aegis_artifact(
            run, expected, label="report.md", required=True
        )
        heading = f"# AEGIS Report: {client.run_id}"
        if not body.strip() or body.splitlines()[0].strip() != heading:
            raise AegisArtifactError(
                "AEGIS report.md is empty or does not identify the pinned run"
            )
        note = self._governance_note(verification_summary)
        parts = [
            f"Related to #{ticket.iid}: {ticket.title}",
            f"Produced by {self.identity.name} (run `{run.run_id}`, AEGIS run "
            f"`{client.run_id}`). After integrating `{run.base_ref}`, "
            f"`aegis verify run` reported `{verification_summary['status']}`. "
            f"{note} Opened as a DRAFT - review and merge are human decisions.",
        ]
        parts.append("### AEGIS delivery report\n```\n"
                     + self._tail_lines(body, 2500) + "\n```")
        parts.append(self.identity.make_marker(run.run_id, "delivery"))
        return self._redact_failure_context("\n\n".join(parts))

    def _governance_note(self, summary: dict | None) -> str:
        """
        @brief      Render accepted governance truth for tickets and MRs.
        @return     One sentence naming waived, not-enforced, and N/A results.
        """
        if summary is None:
            return ""
        facts = self._verification_facts(summary)
        parts = [f"Verification outcome: `{summary['status']}`."]
        if facts["waived"]:
            parts.append(
                "Explicit human waivers accepted failed results: "
                + ", ".join(f"`{item}`" for item in facts["waived"])
                + ". These are not passes."
            )
        if facts["not_enforced"]:
            parts.append(
                "Gate groups not enforced: "
                + ", ".join(f"`{item}`" for item in facts["not_enforced"])
                + "."
            )
        if facts["not_applicable"]:
            parts.append(
                "Not applicable: "
                + ", ".join(f"`{item}`" for item in facts["not_applicable"])
                + "."
            )
        return " ".join(parts)

    def _read_aegis_artifact(
        self,
        run: RunState,
        relative: object,
        *,
        label: str,
        required: bool = True,
    ) -> str:
        """
        @brief      The single typed boundary for direct AEGIS file reads.
        @details    AEGIS returns repository-relative POSIX paths. The value,
                    containment, regular-file existence, size, and strict UTF-8
                    encoding are validated before data crosses into ADORE.
                    Optional means only that a valid contained path may be
                    absent; malformed paths and unreadable files still fail.
        @param[in]  run The run whose worktree holds the artifact.
        @param[in]  relative The `artifact`/`report` value from an envelope.
        @param[in]  label Operator-facing artifact name for errors.
        @param[in]  required Whether absence is a contract failure.
        @return     Strict UTF-8 content, or "" for an absent optional file.
        @exception  AegisArtifactError On an invalid path or file boundary.
        """
        if (
            not isinstance(relative, str)
            or not relative
            or relative == "none"
            or "\\" in relative
        ):
            raise AegisArtifactError(
                f"AEGIS {label} path must be a non-empty repository-relative "
                "POSIX path"
            )
        posix = PurePosixPath(relative)
        if posix.is_absolute() or any(part in ("", ".", "..") for part in posix.parts):
            raise AegisArtifactError(
                f"AEGIS {label} path escapes its repository contract: {relative!r}"
            )
        worktree = self.worktrees.path_for(run.run_id).resolve()
        try:
            candidate = (worktree / Path(*posix.parts)).resolve()
        except OSError as exc:
            raise AegisArtifactError(
                f"cannot resolve AEGIS {label} path {relative!r}: {exc}"
            ) from exc
        if not candidate.is_relative_to(worktree):
            raise AegisArtifactError(
                f"AEGIS {label} path escapes the worktree: {relative!r}"
            )
        if not candidate.exists():
            if required:
                raise AegisArtifactError(
                    f"AEGIS {label} is missing: {relative}"
                )
            return ""
        if not candidate.is_file():
            raise AegisArtifactError(
                f"AEGIS {label} is not a regular file: {relative}"
            )
        try:
            size = candidate.stat().st_size
            if size > _AEGIS_ARTIFACT_LIMIT_BYTES:
                raise AegisArtifactError(
                    f"AEGIS {label} exceeds {_AEGIS_ARTIFACT_LIMIT_BYTES} bytes: "
                    f"{relative}"
                )
            return candidate.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeError) as exc:
            raise AegisArtifactError(
                f"cannot read AEGIS {label} {relative}: {exc}"
            ) from exc

    def _read_aegis_json(
        self,
        run: RunState,
        relative: str,
        *,
        label: str,
        required: bool = True,
    ) -> dict | None:
        """
        @brief      Read one AEGIS JSON object through the typed file boundary.
        @return     Decoded mapping, or None for an absent optional file.
        @exception  AegisArtifactError On file, JSON, or root-shape failure.
        """
        text = self._read_aegis_artifact(
            run, relative, label=label, required=required
        )
        if not text and not required:
            return None
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AegisArtifactError(
                f"AEGIS {label} contains malformed JSON: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise AegisArtifactError(f"AEGIS {label} root must be an object")
        return value

    def _workflow_orientation(self, client: AegisClient) -> str:
        """
        @brief      Compose the run-orientation brief for a fresh session.
        @details    A freshly launched executor session - a retry, a delivery
                    fix, a revise round, or a run resumed mid-workflow after a
                    restart - starts without the prior chat context. AEGIS 3.x
                    answers `run resume` with the authoritative run state
                    rather than prose (contract notes 11.1), so ADORE renders
                    the brief itself: run id, stage, the exact next command,
                    readiness and its blockers, and the most recent evidence.
                    A run that has not started yet yields no brief; once a run
                    exists, a blocked resume is a real failure and escalates
                    through the caller's AegisError handling. Secret values are
                    redacted before the text enters a prompt.
        @param[in]  client The run's AEGIS client.
        @return     A bounded orientation block, or "" when no run exists yet.
        @exception  AegisError When the CLI contract is violated.
        """
        if not client.run_id:
            return ""
        brief = client.run_resume()
        if not brief.ok:
            raise AegisProtocolError(
                f"AEGIS `run resume` for {client.run_id} reported "
                f"{brief.status}: {brief.error or 'no detail'}"
            )
        lines = [
            "Current AEGIS run orientation (read-only, from `aegis run resume`):",
            f"- run: {brief.detail('run_id', client.run_id)}",
            f"- stage: {brief.stage}",
            f"- exact next command: {brief.next_command}",
        ]
        profile = brief.detail("run_profile")
        if profile:
            bypassed = brief.detail("bypassed_stages") or []
            lines.append(
                f"- profile: {profile}"
                + (f" (bypassed: {', '.join(str(x) for x in bypassed)})"
                   if bypassed else "")
            )
        readiness = brief.detail("readiness") or {}
        if isinstance(readiness, dict) and readiness:
            lines.append(f"- stage state: {readiness.get('state', 'unknown')}"
                         f", ready: {readiness.get('ready')}")
            for blocker in list(readiness.get("blockers") or [])[
                :_AGENTIC_FAILURE_ITEMS_LIMIT
            ]:
                lines.append(f"  - blocker: {blocker}")
        evidence = brief.detail("evidence") or []
        if isinstance(evidence, list) and evidence:
            lines.append("- recent evidence:")
            for item in evidence[-_AGENTIC_FAILURE_ITEMS_LIMIT:]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"  - {item.get('id')} {item.get('kind')} "
                    f"{item.get('result')} ({item.get('status')})"
                )
        block = self._tail_lines("\n".join(lines), _AGENTIC_ORIENTATION_LIMIT)
        return self._redact_failure_context(block)

    def _failure_context(
        self,
        run: RunState,
        base: str,
        response: AegisResponse | None = None,
    ) -> str:
        """
        @brief      Add read-only AEGIS failure evidence to a fix prompt.
        @details    Sources in order, each bounded: the blocked/failed AEGIS
                    response itself (error, remediation, stage blockers), then
                    `validation-summary.json` (failing gates and invariants),
                    then the schema-3 `graph.json` `evidence[]` rows, then the
                    tail of `report.md` when it exists. This keeps ADORE
                    deterministic: it only reads files the run already wrote,
                    never invokes extra AEGIS commands, and redacts configured
                    executor secret values from the final prompt context.
        @param[in]  run ADORE run whose worktree holds the AEGIS artifacts.
        @param[in]  base The original exit-code/stderr failure summary.
        @param[in]  response The blocked/failed response, when one caused this.
        @return     Bounded prompt context for the executor retry.
        @exception  AegisArtifactError When a persisted artifact is missing,
                    malformed, or disagrees with the pinned run.
        """
        parts = [base.strip()]
        if response is not None:
            parts.extend(self._response_evidence(run, response))
        evidence = self._aegis_failure_evidence(run)
        if evidence:
            parts.append(evidence)
        return self._redact_failure_context(
            "\n\n".join(part for part in parts if part)
        )

    def _response_evidence(
        self,
        run: RunState,
        response: AegisResponse,
    ) -> list[str]:
        """
        @brief      Render the blocked/failed response as prompt context.
        @param[in]  run The ADORE run (for the stage record).
        @param[in]  response The blocked or failed response.
        @return     Zero or more prompt blocks.
        """
        lines: list[str] = []
        if response.error:
            lines.append(f"AEGIS reported: {self._tail_lines(response.error, 900)}")
        if response.remediation:
            lines.append(f"AEGIS remediation: "
                         f"{self._tail_lines(response.remediation, 500)}")
        blockers = [
            str(item)
            for item in (response.detail("blockers") or [])
        ][:_AGENTIC_FAILURE_ITEMS_LIMIT]
        if blockers:
            lines.append("Stage blockers:\n"
                         + "\n".join(f"- {item}" for item in blockers))
        if response.next_command and response.next_command != "none":
            lines.append(f"AEGIS says the exact next command is "
                         f"`{response.next_command}`.")
        return lines

    def _aegis_run_dir(self, run: RunState) -> Path | None:
        """
        @brief      The run-local `.agentic/runs/<id>/` directory, if any.
        @details    Addressed by the run id ADORE persisted at `run start`, not
                    by the worktree's `current_run` pointer - the fragile seam
                    that already broke once (design decision 4). The id was
                    validated against the AEGIS run-id pattern when it was
                    captured, so it is safe as a single path segment.
        @param[in]  run The ADORE run.
        @return     The directory path, or None when no AEGIS run exists yet.
        """
        if not run.aegis_run_id:
            return None
        worktree = self.worktrees.path_for(run.run_id)
        return worktree / ".agentic" / "runs" / run.aegis_run_id

    def _stage_questions(self, run: RunState, stage: str) -> str:
        """
        @brief      Read the stage's unresolved questions from the run graph.
        @details    AEGIS folds unresolved questions into `stage show`'s
                    human-readable `blockers[]`; the structured list lives in
                    `graph.json` under `stage_records[<stage>]`
                    (contract notes 11.2). This is the primary clarification
                    channel in 3.x - the executor's questions file remains a
                    secondary one, and the conductor honors whichever fires.
        @param[in]  run The ADORE run.
        @param[in]  stage The stage just applied.
        @return     A rendered question block, or "" when there are none.
        @exception  AegisArtifactError When graph question state is invalid.
        """
        run_dir = self._aegis_run_dir(run)
        if run_dir is None:
            raise AegisProtocolError(
                "cannot read AEGIS question state without a pinned run"
            )
        graph = self._load_aegis_graph(run)
        assert graph is not None
        records = graph["stage_records"]
        record = records.get(stage)
        if not isinstance(record, dict):
            raise AegisArtifactError(
                f"AEGIS graph has no valid stage record for {stage!r}"
            )
        raw_questions = record.get("unresolved_questions")
        if not isinstance(raw_questions, list) or not all(
            isinstance(item, str) for item in raw_questions
        ):
            raise AegisArtifactError(
                "AEGIS unresolved_questions must be a string list"
            )
        questions = [item.strip() for item in raw_questions if item.strip()]
        if not questions:
            return ""
        listed = "\n".join(f"{index}. {text}"
                           for index, text in enumerate(questions, start=1))
        return (
            f"The executor recorded unresolved questions in the AEGIS {stage} "
            f"stage form:\n\n{listed}"
        )

    def _load_aegis_graph(
        self, run: RunState, *, required: bool = True
    ) -> dict | None:
        """
        @brief      Load and validate the pinned schema-3 AEGIS run graph.
        @param[in]  run ADORE run naming the only acceptable graph run id.
        @param[in]  required Whether an absent graph is an error.
        @return     Validated graph mapping, or None when optional and absent.
        @exception  AegisArtifactError On file, schema, run, or shape failure.
        """
        if not run.aegis_run_id:
            if required:
                raise AegisArtifactError(
                    "cannot read graph.json without a pinned AEGIS run"
                )
            return None
        relative = f"{_AEGIS_RUN_DIR}/{run.aegis_run_id}/graph.json"
        graph = self._read_aegis_json(
            run, relative, label="graph.json", required=required
        )
        if graph is None:
            return None
        self._validate_aegis_graph(run, graph)
        return graph

    @staticmethod
    def _validate_aegis_graph(run: RunState, graph: dict) -> None:
        """
        @brief      Enforce AEGIS's closed schema-3 graph boundary.
        @details    The documented omissions are accepted: `profile` for full,
                    `waivers` when empty, `outcome` for normal completion, and
                    historical quick `red_green_policy` (interpreted only as
                    `legacy-not-applicable`). Container and discriminator
                    values used by ADORE are otherwise validated fail-closed.
        @exception  AegisArtifactError On any unsupported graph shape.
        """
        keys = set(graph)
        missing = sorted(_GRAPH_REQUIRED_KEYS - keys)
        unknown = sorted(keys - _GRAPH_REQUIRED_KEYS - _GRAPH_OPTIONAL_KEYS)
        if missing or unknown:
            raise AegisArtifactError(
                "AEGIS graph.json has an invalid closed schema-3 shape; "
                f"missing={missing}, unknown={unknown}"
            )
        if type(graph["schema_version"]) is not int or graph["schema_version"] != 3:
            raise AegisArtifactError("AEGIS graph.json requires schema_version 3")
        if graph["run_id"] != run.aegis_run_id:
            raise AegisArtifactError(
                f"AEGIS graph run id {graph['run_id']!r} disagrees with pinned "
                f"run {run.aegis_run_id!r}"
            )
        stage = graph["stage"]
        if not isinstance(stage, str) or stage not in STANDARD_STAGES:
            raise AegisArtifactError(
                f"AEGIS graph has unsupported stage {stage!r}"
            )
        if graph["access_mode"] not in {"standard", "repo-wide"}:
            raise AegisArtifactError("AEGIS graph has invalid access_mode")
        if not isinstance(graph["complete"], bool):
            raise AegisArtifactError("AEGIS graph complete must be boolean")
        profile = graph.get("profile", "full")
        if profile not in {"full", "quick"}:
            raise AegisArtifactError("AEGIS graph profile must be full or quick")
        red_green = graph.get(
            "red_green_policy",
            "legacy-not-applicable" if profile == "quick" else "required",
        )
        if red_green not in {"required", "legacy-not-applicable"}:
            raise AegisArtifactError("AEGIS graph has invalid red_green_policy")
        if profile == "full" and red_green != "required":
            raise AegisArtifactError(
                "AEGIS full graph requires red_green_policy required"
            )
        outcome = graph.get("outcome", "")
        if outcome not in {"", "abandoned"}:
            raise AegisArtifactError(
                f"AEGIS graph has unknown terminal outcome {outcome!r}"
            )
        if outcome and graph["complete"] is not True:
            raise AegisArtifactError(
                "AEGIS graph reports an outcome before completion"
            )
        intent = graph["intent"]
        if not isinstance(intent, dict) or intent.get("kind") not in {
            "feature", "fix", "change"
        }:
            raise AegisArtifactError("AEGIS graph intent must name a development kind")
        if not isinstance(intent.get("id"), str) or not isinstance(
            intent.get("statement"), str
        ):
            raise AegisArtifactError("AEGIS graph intent has invalid identity/content")
        if graph["alignment"] is not None and not isinstance(graph["alignment"], dict):
            raise AegisArtifactError("AEGIS graph alignment must be object or null")
        if graph["design"] is not None and not isinstance(graph["design"], dict):
            raise AegisArtifactError("AEGIS graph design must be object or null")
        for name in (
            "spec_items", "checks", "evidence", "change_units", "decisions"
        ):
            value = graph[name]
            if not isinstance(value, list) or not all(
                isinstance(item, dict) for item in value
            ):
                raise AegisArtifactError(
                    f"AEGIS graph {name} must be a list of objects"
                )
        for index, check in enumerate(graph["checks"]):
            if (
                not isinstance(check.get("id"), str)
                or check.get("state") not in {"red", "green", "unknown"}
                or any(
                    value is not None and not isinstance(value, str)
                    for value in (
                        check.get("red_evidence"), check.get("green_evidence")
                    )
                )
            ):
                raise AegisArtifactError(
                    f"AEGIS graph checks[{index}] has invalid evidence state"
                )
        for index, evidence in enumerate(graph["evidence"]):
            if (
                not isinstance(evidence.get("id"), str)
                or evidence.get("kind") not in {
                    "test-run", "diff", "scan", "gate", "decision", "note"
                }
                or evidence.get("result") not in {"pass", "fail", "info"}
                or evidence.get("status") not in {"active", "superseded"}
                or not isinstance(evidence.get("summary"), str)
            ):
                raise AegisArtifactError(
                    f"AEGIS graph evidence[{index}] has invalid result shape"
                )
        records = graph["stage_records"]
        if not isinstance(records, dict):
            raise AegisArtifactError("AEGIS graph stage_records must be an object")
        for name, record in records.items():
            questions = record.get("unresolved_questions") if isinstance(
                record, dict
            ) else None
            if not isinstance(questions, list) or not all(
                isinstance(item, str) for item in questions
            ):
                raise AegisArtifactError(
                    "AEGIS unresolved_questions must be a string list"
                )
            if (
                name not in STANDARD_STAGES
                or not isinstance(record, dict)
                or record.get("stage") != name
                or record.get("status") not in {"prepared", "applied", "closed"}
            ):
                raise AegisArtifactError(
                    f"AEGIS graph stage_records[{name!r}] has invalid shape"
                )
        waivers = graph.get("waivers", [])
        if not isinstance(waivers, list):
            raise AegisArtifactError("AEGIS graph waivers must be a list")
        for index, waiver in enumerate(waivers):
            if (
                not isinstance(waiver, dict)
                or waiver.get("approver") != "human"
                or not isinstance(waiver.get("id"), str)
                or not isinstance(waiver.get("blocker_id"), str)
                or not isinstance(waiver.get("reason"), str)
                or not isinstance(waiver.get("state_digests"), dict)
            ):
                raise AegisArtifactError(
                    f"AEGIS graph waivers[{index}] has invalid human approval"
                )

    def _load_validation_summary(
        self, run: RunState, *, required: bool = True
    ) -> dict | None:
        """
        @brief      Load the pinned schema-3 validation summary fail-closed.
        @return     Validated summary, or None when optional and absent.
        @exception  AegisArtifactError On file, schema, run, or truth failure.
        """
        if not run.aegis_run_id:
            if required:
                raise AegisArtifactError(
                    "cannot read validation-summary.json without a pinned run"
                )
            return None
        relative = (
            f"{_AEGIS_RUN_DIR}/{run.aegis_run_id}/validation-summary.json"
        )
        summary = self._read_aegis_json(
            run, relative, label="validation-summary.json", required=required
        )
        if summary is None:
            return None
        self._validate_validation_summary(run, summary)
        return summary

    @staticmethod
    def _contains_execution_status(value: object, status: str) -> bool:
        """@brief Recursively find one structured execution-status value."""
        if isinstance(value, dict):
            if value.get("execution_status") == status:
                return True
            return any(
                Orchestrator._contains_execution_status(item, status)
                for item in value.values()
            )
        if isinstance(value, list):
            return any(
                Orchestrator._contains_execution_status(item, status)
                for item in value
            )
        return False

    @staticmethod
    def _validate_validation_summary(run: RunState, summary: dict) -> None:
        """
        @brief      Validate AEGIS verification vocabulary and consistency.
        @details    `not-enforced` and `not-applicable` are neutral but never
                    passes. `waived` remains a visible accepted failure.
                    `not-run` and nested `nothing-ran` are failures even if an
                    enclosing command returned exit zero.
        @exception  AegisArtifactError On malformed or contradictory truth.
        """
        required = {
            "schema_version", "run_id", "status", "gates", "invariants",
            "traceability", "coverage", "working_tree",
        }
        missing = sorted(required - set(summary))
        if missing:
            raise AegisArtifactError(
                f"AEGIS validation-summary.json is missing keys {missing}"
            )
        if type(summary["schema_version"]) is not int or summary["schema_version"] != 3:
            raise AegisArtifactError(
                "AEGIS validation-summary.json requires schema_version 3"
            )
        if summary["run_id"] != run.aegis_run_id:
            raise AegisArtifactError(
                "AEGIS validation summary run id disagrees with the pinned run"
            )
        verdict = summary["status"]
        if verdict not in _VERIFICATION_STATUSES:
            raise AegisArtifactError(
                f"AEGIS validation summary has unknown status {verdict!r}"
            )
        if "waived" in summary and not isinstance(summary["waived"], bool):
            raise AegisArtifactError(
                "AEGIS validation summary waived marker must be boolean"
            )
        gates = summary["gates"]
        if not isinstance(gates, dict):
            raise AegisArtifactError("AEGIS validation gates must be an object")
        gate_statuses: list[str] = []
        for name, gate in gates.items():
            if not isinstance(name, str) or not isinstance(gate, dict):
                raise AegisArtifactError("AEGIS validation gate rows must be objects")
            status = gate.get("status")
            commands = gate.get("commands")
            if status not in _GATE_STATUSES:
                raise AegisArtifactError(
                    f"AEGIS gate {name!r} has unknown status {status!r}"
                )
            if not isinstance(commands, list) or not all(
                isinstance(item, str) for item in commands
            ):
                raise AegisArtifactError(
                    f"AEGIS gate {name!r} commands must be a string list"
                )
            if status == "waived" and gate.get("waived") is not True:
                raise AegisArtifactError(
                    f"AEGIS gate {name!r} waived status lacks waiver metadata"
                )
            gate_statuses.append(status)
        invariants = summary["invariants"]
        if not isinstance(invariants, list):
            raise AegisArtifactError("AEGIS invariants must be a list")
        invariant_failed = False
        invariant_waived = False
        for index, item in enumerate(invariants):
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("id"), str)
                or not isinstance(item.get("message"), str)
                or (
                    item.get("holds") is not None
                    and not isinstance(item.get("holds"), bool)
                )
            ):
                raise AegisArtifactError(
                    f"AEGIS invariant[{index}] has invalid result shape"
                )
            status = item.get("status")
            policy = item.get("policy")
            if policy not in {
                "blocking", "non-waivable", "advisory", "not-applicable"
            }:
                raise AegisArtifactError(
                    f"AEGIS invariant[{index}] has unknown policy {policy!r}"
                )
            if status is not None and status != "not-applicable":
                raise AegisArtifactError(
                    f"AEGIS invariant[{index}] has unknown status {status!r}"
                )
            if status == "not-applicable" and item.get("holds") is not None:
                raise AegisArtifactError(
                    "AEGIS not-applicable invariant must have holds: null"
                )
            if item.get("holds") is False:
                if item.get("waived") is True:
                    invariant_waived = True
                elif policy in {"blocking", "non-waivable"}:
                    invariant_failed = True
        audit_failed = False
        audit_waived = False
        for name in ("traceability", "coverage"):
            rows = summary[name]
            if not isinstance(rows, list) or not all(
                isinstance(item, dict) for item in rows
            ):
                raise AegisArtifactError(
                    f"AEGIS validation {name} must be a list of objects"
                )
            for item in rows:
                if item.get("status") is not None and item.get("status") not in {
                    "failed", "waived", "not-applicable"
                }:
                    raise AegisArtifactError(
                        f"AEGIS validation {name} has unknown status "
                        f"{item.get('status')!r}"
                    )
                if item.get("status") == "not-applicable":
                    continue
                if item.get("status") == "waived" or item.get("waived") is True:
                    audit_waived = True
                else:
                    audit_failed = True
        working_tree = summary["working_tree"]
        if not isinstance(working_tree, dict) or not isinstance(
            working_tree.get("blocking_findings"), list
        ):
            raise AegisArtifactError(
                "AEGIS validation working_tree requires blocking_findings[]"
            )
        working_failed = any(
            isinstance(item, dict) and item.get("waived") is not True
            for item in working_tree["blocking_findings"]
        )
        working_waived = any(
            isinstance(item, dict) and item.get("waived") is True
            for item in working_tree["blocking_findings"]
        )
        if not all(
            isinstance(item, dict)
            for item in working_tree["blocking_findings"]
        ):
            raise AegisArtifactError(
                "AEGIS working-tree blocking findings must be objects"
            )
        nothing_ran = Orchestrator._contains_execution_status(
            summary, "nothing-ran"
        )
        unwaived_failure = (
            any(status in {"failed", "not-run"} for status in gate_statuses)
            or invariant_failed
            or audit_failed
            or working_failed
            or nothing_ran
        )
        waived_failure = (
            any(status == "waived" for status in gate_statuses)
            or invariant_waived
            or audit_waived
            or working_waived
            or summary.get("waived") is True
        )
        if verdict == "ok" and (unwaived_failure or waived_failure):
            raise AegisArtifactError(
                "AEGIS validation summary labels failed/waived evidence as ok"
            )
        if verdict == "waived" and (unwaived_failure or not waived_failure):
            raise AegisArtifactError(
                "AEGIS validation summary has a contradictory waived verdict"
            )
        if verdict == "failed" and not unwaived_failure:
            raise AegisArtifactError(
                "AEGIS validation summary says failed without a failing result"
            )

    def _validated_verification(
        self, run: RunState, response: AegisResponse
    ) -> dict:
        """
        @brief      Cross-check a verify envelope against its durable artifact.
        @return     Validated validation-summary mapping.
        @exception  AegisArtifactError On path, payload, or evidence mismatch.
        """
        expected = f"{_AEGIS_RUN_DIR}/{run.aegis_run_id}/validation-summary.json"
        if response.artifact != expected:
            raise AegisArtifactError(
                f"AEGIS verify response named {response.artifact!r}, expected "
                f"{expected!r}"
            )
        summary = self._load_validation_summary(run)
        assert summary is not None
        if response.detail("verification") != summary:
            raise AegisArtifactError(
                "AEGIS verify response disagrees with validation-summary.json"
            )
        if response.verification_status != summary["status"]:
            raise AegisArtifactError(
                "AEGIS verification status disagrees with its durable summary"
            )
        graph = self._load_aegis_graph(run)
        assert graph is not None
        self._validate_evidence_truth(graph, summary)
        return summary

    @staticmethod
    def _validate_evidence_truth(graph: dict, summary: dict) -> None:
        """
        @brief      Cross-check gate/check claims against executed evidence.
        @details    Exit zero never supplies truth: active `evidence[].result`
                    rows do. Linked red evidence must fail and linked green
                    evidence must pass. A passing gate needs active passing
                    gate evidence and cannot hide an active failing row.
        @exception  AegisArtifactError On missing or contradictory evidence.
        """
        active = {
            item["id"]: item
            for item in graph["evidence"]
            if item["status"] == "active"
        }
        if (
            graph.get("profile", "full") == "quick"
            and graph.get("red_green_policy", "legacy-not-applicable") == "required"
        ):
            if not graph["checks"]:
                raise AegisArtifactError(
                    "AEGIS required quick red/green policy has no checks"
                )
            if any(
                not check.get("red_evidence") or not check.get("green_evidence")
                for check in graph["checks"]
            ):
                raise AegisArtifactError(
                    "AEGIS required quick check lacks red/green evidence links"
                )
        for check in graph["checks"]:
            for key, expected in (("red_evidence", "fail"), ("green_evidence", "pass")):
                evidence_id = check.get(key)
                if evidence_id is None:
                    continue
                item = active.get(evidence_id)
                if item is None or item.get("result") != expected:
                    raise AegisArtifactError(
                        f"AEGIS check {check['id']} {key} does not link active "
                        f"{expected} evidence"
                    )
        for name, gate in summary["gates"].items():
            rows = [
                item for item in active.values()
                if item.get("kind") == "gate" and item.get("gate_name") == name
            ]
            if gate["status"] == "passed" and (
                not rows
                or any(item["result"] == "fail" for item in rows)
                or not any(item["result"] == "pass" for item in rows)
            ):
                raise AegisArtifactError(
                    f"AEGIS gate {name!r} passed without active passing evidence"
                )
            if gate["status"] in {"failed", "waived"} and (
                not rows or not any(item["result"] == "fail" for item in rows)
            ):
                raise AegisArtifactError(
                    f"AEGIS gate {name!r} {gate['status']} without active "
                    "failing evidence"
                )

    def _aegis_failure_evidence(self, run: RunState) -> str:
        """
        @brief      Read prompt-safe failure evidence from the AEGIS run.
        @details    Uses the AEGIS file contract under
                    `.agentic/runs/<aegis-run-id>/`, addressed by the run id
                    ADORE persisted rather than by the retired worktree
                    pointer: `validation-summary.json` first (the authoritative
                    verification result), then the schema-3 `graph.json`
                    evidence rows, then `report.md` when it exists. Every read
                    crosses the typed artifact boundary; malformed state is a
                    conductor escalation, never retry context for the executor.
                    A STARTED run always has `graph.json`, so its absence fails
                    loud.
        @param[in]  run ADORE run whose worktree is inspected.
        @return     Markdown-ish evidence block, or "" when no evidence exists.
        @exception  AegisArtifactError When any artifact contract is broken.
        """
        run_dir = self._aegis_run_dir(run)
        if run_dir is None:
            return ""
        graph = self._load_aegis_graph(run)
        assert graph is not None
        summary = self._load_validation_summary(run, required=False)
        report_relative = f"{_AEGIS_RUN_DIR}/{run.aegis_run_id}/report.md"
        report = self._read_aegis_artifact(
            run, report_relative, label="report.md", required=False
        )
        sections = [
            f"AEGIS failure evidence from `{_AEGIS_RUN_DIR}/{run.aegis_run_id}`:"
        ]
        sections.extend(self._summary_failure_evidence(summary))
        sections.extend(self._graph_failure_evidence(graph))
        sections.extend(self._report_failure_evidence(report))
        if len(sections) == 1:
            return ""
        rendered = "\n".join(sections)
        return self._tail_lines(rendered, _AGENTIC_FAILURE_CONTEXT_LIMIT)

    def _summary_failure_evidence(self, summary: dict | None) -> list[str]:
        """
        @brief      Extract failing gates and invariants from the summary.
        @details    `validation-summary.json` is what `aegis verify run`
                    writes, so it is the authoritative account of WHY
                    verification failed. Waived and not-enforced gates are
                    reported verbatim - AEGIS never renders either as passed,
                    and neither does this prompt.
        @param[in]  summary Validated summary, or None before verification.
        @return     Lines to append to the retry prompt.
        """
        if summary is None:
            return []
        lines: list[str] = []
        gates = summary.get("gates")
        if isinstance(gates, dict):
            failing = [
                f"{name} ({value.get('status')})"
                for name, value in sorted(gates.items())
                if isinstance(value, dict)
                and value.get("status") in {"failed", "not-run"}
            ][:_AGENTIC_FAILURE_ITEMS_LIMIT]
            if failing:
                lines.append("- Failing gate groups: " + ", ".join(failing))
            waived = [
                name for name, value in sorted(gates.items())
                if isinstance(value, dict) and value.get("status") == "waived"
            ][:_AGENTIC_FAILURE_ITEMS_LIMIT]
            if waived:
                lines.append(
                    "- Waived gate groups (accepted failure, not pass): "
                    + ", ".join(waived)
                )
            not_enforced = [
                name for name, value in sorted(gates.items())
                if isinstance(value, dict)
                and value.get("status") == "not-enforced"
            ][:_AGENTIC_FAILURE_ITEMS_LIMIT]
            if not_enforced:
                lines.append(
                    "- Not-enforced gate groups (not pass): "
                    + ", ".join(not_enforced)
                )
        invariants = summary.get("invariants")
        if isinstance(invariants, list):
            broken = [
                item for item in invariants
                if isinstance(item, dict) and item.get("holds") is False
            ][:_AGENTIC_FAILURE_ITEMS_LIMIT]
            if broken:
                lines.append("- Invariants that do not hold:")
                for item in broken:
                    lines.append(
                        f"  - {item.get('id')} ({item.get('policy')}): "
                        f"{self._tail_lines(str(item.get('message') or ''), 300)}"
                    )
        for key, label in (("traceability", "Traceability findings"),
                           ("coverage", "Coverage findings")):
            issues = summary.get(key)
            if not isinstance(issues, list):
                continue
            texts = [
                str(item.get("message"))
                for item in issues
                if isinstance(item, dict)
                and item.get("message")
                and item.get("status") != "not-applicable"
            ][:_AGENTIC_FAILURE_ITEMS_LIMIT]
            if texts:
                lines.append(f"- {label}: " + "; ".join(texts))
        working_tree = summary.get("working_tree")
        if isinstance(working_tree, dict):
            findings = [
                f"{item.get('code')} {item.get('path')}: {item.get('message')}"
                for item in (working_tree.get("blocking_findings") or [])
                if isinstance(item, dict)
            ][:_AGENTIC_FAILURE_ITEMS_LIMIT]
            if findings:
                lines.append("- Working-tree findings: " + "; ".join(findings))
        return lines

    def _graph_failure_evidence(self, graph: dict) -> list[str]:
        """
        @brief      Extract active failing evidence rows from graph.json.
        @details    Schema-3 `evidence[]` rows with `result: "fail"` that were
                    not superseded, rendered with the fields the executor needs
                    to act: id, kind, stage, summary, command, failure kind.
        @param[in]  graph Validated AEGIS run graph.
        @return     Lines to append to the retry prompt.
        """
        failing = [
            item for item in graph["evidence"]
            if isinstance(item, dict)
            and item.get("result") == "fail"
            and item.get("status", "active") != "superseded"
        ][-_AGENTIC_FAILURE_ITEMS_LIMIT:]
        if not failing:
            return []
        lines = ["- Active failing evidence:"]
        for item in failing:
            label = " ".join(
                part for part in (
                    str(item.get("id") or "evidence"),
                    str(item.get("kind") or ""),
                    f"stage={item.get('stage')}" if item.get("stage") else "",
                )
                if part
            )
            summary = str(item.get("summary") or "").strip()
            lines.append(f"  - {label}: {self._tail_lines(summary, 500)}")
            if item.get("command"):
                lines.append(f"    command: {self._tail_lines(str(item['command']), 500)}")
            if item.get("failure_kind"):
                lines.append(f"    failure kind: {item['failure_kind']}")
        return lines

    def _report_failure_evidence(self, report: str) -> list[str]:
        """
        @brief      Extract short report.md excerpts around failure markers.
        @param[in]  report Validated optional workflow-report text.
        @return     Lines to append to the retry prompt.
        """
        if not report:
            return []
        lines = report.splitlines()
        markers = ("fail", "failed", "failure", "blocking", "error", "issue")
        excerpts: list[str] = []
        last_end = -1
        for index, line in enumerate(lines):
            if len(excerpts) >= 2:
                break
            if not any(marker in line.lower() for marker in markers):
                continue
            start = max(0, index - 2)
            end = min(len(lines), index + 3)
            if start <= last_end:
                continue
            excerpts.append("\n".join(lines[start:end]))
            last_end = end
        if not excerpts:
            return []
        rendered = "\n\n---\n".join(self._tail_lines(excerpt, 900) for excerpt in excerpts)
        return ["- Report excerpts around failure markers:\n" + rendered]

    def _redact_failure_context(self, text: str) -> str:
        """
        @brief      Redact configured executor secret values from prompt context.
        @param[in]  text Candidate prompt context.
        @return     Redacted text.
        """
        redacted = text
        values = sorted(
            {value for value in self.secrets.values() if len(value) >= 4},
            key=len,
            reverse=True,
        )
        for value in values:
            redacted = redacted.replace(value, "[REDACTED]")
        return redacted

    @staticmethod
    def _tail_lines(text: str, limit: int) -> str:
        """
        @brief      Tail-truncate on a LINE boundary, never mid-line.
        @details    Character slicing left the MR description starting with
                    dangling fragments like `g",` (pilot review finding
                    2026-07-04); dropping the partial first line keeps the
                    embedded evidence readable.
        @param[in]  text Full text.
        @param[in]  limit Approximate character budget for the tail.
        @return     The last <= limit characters, starting at a full line,
                    with a truncation marker when clipped.
        """
        text = text.strip()
        if len(text) <= limit:
            return text
        clipped = text[-limit:]
        _, separator, rest = clipped.partition("\n")
        body = rest if separator else clipped
        return "[... truncated ...]\n" + body.strip()

    @staticmethod
    def _parse_mr_iid(url: str) -> int | None:
        """
        @brief      Extract the MR iid / PR number from its web URL.
        @details    Covers all three URL shapes: GitLab `/-/merge_requests/N`,
                    GitHub `/pull/N`, Gitea `/pulls/N`.
        @param[in]  url MR/PR web URL.
        @return     The number, or None when unparseable.
        """
        match = re.search(r"/(?:merge_requests|pulls?)/(\d+)", url)
        return int(match.group(1)) if match else None

    # -- clarification: park / resume (design 9) -----------------------------------

    def _park(self, run: RunState, questions: str) -> None:
        """
        @brief      Park a run on executor questions - exact design-9 order.
        @details    1. post the questions comment FIRST (a later crash still
                    leaves them on the ticket) and record its id; 2. update
                    the status marking; 3. round counter vs max_rounds
                    (exceeded -> failed instead of parking); 4. record
                    parked_at; 5. stop (or remove) the container; 6. return
                    to polling.

                    Posting first is a crash-ordering choice, but a forge
                    failure is not a crash: the run would stay `working` with
                    nobody asked and nothing waiting. So a `ForgeError` on the
                    post journals the questions (they are the only copy) and
                    escalates - a run cannot wait for an answer to a question
                    that was never delivered.
        @param[in]  run The run to park.
        @param[in]  questions Questions text from the worktree file.
        """
        run.clarification_rounds += 1
        if run.clarification_rounds > self.config.clarification.max_rounds:
            self._escalate(run, "clarification rounds exhausted")
            return
        body = (
            f"{self.identity.tag} Clarification needed for this ticket "
            f"(round {run.clarification_rounds}/"
            f"{self.config.clarification.max_rounds}). "
            "Reply in a normal comment to resume the run.\n\n"
            f"{questions.strip()}\n"
            f"{self.identity.make_marker(run.run_id, 'question')}"
        )
        try:
            question_id = self.forge.post_comment(run.ticket_iid, body)
        except ForgeError as exc:
            self.store.journal(run.run_id, "park-post-failed",
                               questions=questions[:_PARK_JOURNAL_LIMIT])
            self._escalate(
                run,
                self._redact_failure_context(
                    f"failed to post the clarification comment: {exc}; "
                    "questions preserved in the journal"
                ),
            )
            return
        run.question_comment_id = question_id
        run.last_seen_comment_id = question_id
        run.lifecycle = "parked"
        run.parked_at = utc_now_iso()
        run.parked_polls = 0
        run.reminder_sent = False
        self.store.save(run)
        self._mark(run, "parked", run.stage)
        self.store.journal(run.run_id, "parked", round=run.clarification_rounds,
                           question_comment=question_id)
        try:
            if self.config.container.keep_parked:
                self.containers.stop(run.container)
            else:
                self.containers.remove(run.container)
        except IsolationError as exc:
            self.log(f"{run.run_id}: park container handling failed: {exc}")
        self.log(f"{run.run_id}: parked for clarification "
                 f"(round {run.clarification_rounds})")

    def _stale_working(self, run: RunState) -> bool:
        """
        @brief      Is this `working` run abandoned rather than in flight?
        @details    A `working` run counts against `max_concurrent_runs`, so a
                    conductor that died mid-run (power loss, SIGKILL, systemd
                    restart) silently stops all future pickup - with the
                    default `max_concurrent_runs = 1`, one crash stops the
                    orchestrator entirely, and the only trace is
                    `"at_capacity": true` in the poll summary.

                    Two conditions separate that from normal work. The run
                    must not be the one THIS process is driving
                    (`_conducting`), and its last state write must be older
                    than any legitimate gap between writes: the run's whole
                    wall-clock budget plus one more full gate timeout. Both
                    come from the operator's own budgets, so a deployment that
                    allows long runs automatically gets a long threshold.
                    A run with no parseable `updated_at` is never reaped -
                    fail closed toward leaving it for a human.
        @param[in]  run A run whose lifecycle is `working`.
        @return     True when the run should be escalated as abandoned.
        """
        if run.run_id == self._in_flight_run_id:
            return False
        updated = iso_to_datetime(run.updated_at)
        now = iso_to_datetime(utc_now_iso())
        if not updated or not now:
            return False
        budgets = self.config.budgets
        threshold = budgets.max_wall_clock_seconds + budgets.per_gate_timeout_seconds
        return (now - updated).total_seconds() > threshold

    def _escalate_stale(self, run: RunState, summary: dict) -> None:
        """
        @brief      End an abandoned `working` run and free its slot.
        @details    Escalation (not silent cleanup) is the point: the operator
                    gets the same failed state, ticket comment, and metrics
                    row as any other terminal outcome, and `adore retry`
                    re-arms the run from the stage where it stopped.
        @param[in]  run The stale run.
        @param[in,out] summary Poll summary counters to update.
        """
        self.store.journal(run.run_id, "stale-working-detected",
                           stage=run.stage, updated_at=run.updated_at)
        summary["stale"] = summary.get("stale", 0) + 1
        self._escalate(
            run,
            f"run found in state 'working' with no live conductor (last "
            f"update {run.updated_at}); the orchestrator likely crashed "
            f"mid-run - inspect and `adore retry {run.run_id}`",
        )

    def _reconcile_parked(self, summary: dict) -> None:
        """
        @brief      Per poll: stale `working` runs, parked runs (answers, TTL,
                    timeouts), in-review runs (merge/close detection), and
                    legacy validated runs (deliver them) - design 8b/8c/9/11b.
        @details    Runs first in the poll pass, before the capacity check, so
                    a stale run escalated here frees its slot for a new ticket
                    in the same pass.
        @param[in,out] summary Poll summary counters to update.
        """
        for run in self.store.list_runs():
            if run.lifecycle == "in-review":
                self._check_review(run, summary)
                continue
            if run.lifecycle == "validated":
                # pre-phase-4 runs that stopped at validated-delivery-pending
                ticket = self.forge.get_ticket(run.ticket_iid)
                if ticket is not None:
                    self._deliver(run, ticket)
                continue
            if run.lifecycle == "working":
                if self._stale_working(run):
                    self._escalate_stale(run, summary)
                continue
            if run.lifecycle != "parked":
                continue
            ticket = self.forge.get_ticket(run.ticket_iid)
            if ticket is None:
                self._teardown(run, remove_worktree=True)
                run.lifecycle = "failed"
                run.outcome = "orphaned"
                self.store.save(run)
                self.store.journal(run.run_id, "orphaned")
                self._record_metrics(run)
                self.log(f"{run.run_id}: ticket deleted; run orphaned")
                continue
            if ticket.state != "opened":
                self.cancel(run.run_id, outcome="ticket-closed")
                continue
            if self._answer_arrived(run, ticket):
                self._resume(run, ticket)
                summary["resumed"] += 1
                continue
            self._age_parked(run, ticket, summary)

    def _answer_arrived(self, run: RunState, ticket: Ticket) -> bool:
        """
        @brief      Resume detection (design 9): a human comment newer than
                    our question, or the manual answered-label override.
        @details    "Human" = lacks the agent marker and is not a system
                    note; the human just replies normally, no re-labelling.
        @param[in]  run The parked run.
        @param[in]  ticket Fresh ticket (labels checked for the override).
        @return     True when the run should resume.
        """
        if self.config.labels.lifecycle.answered in ticket.labels:
            return True
        threshold = run.question_comment_id or run.last_seen_comment_id or 0
        for comment in self.forge.list_comments(run.ticket_iid):
            if comment.id <= threshold:
                continue
            if comment.system:
                continue
            if self.identity.is_own_comment(comment.body):
                continue
            return True
        return False

    def _resume(self, run: RunState, ticket: Ticket) -> None:
        """
        @brief      Resume a parked run - exact design-9 order.
        @details    1. record the newest seen comment; 2. the container comes
                    back inside _conduct (start if warm, recreate if reaped;
                    same worktree by run-id); 3. mark working and reset the
                    answer-wait clock; 4. relaunch at the parked stage with
                    the full thread; 5. the executor re-decides (may re-park).
        @param[in]  run The parked run.
        @param[in]  ticket Fresh ticket.
        """
        comments = self.forge.list_comments(run.ticket_iid)
        run.last_seen_comment_id = max(
            (c.id for c in comments), default=run.last_seen_comment_id
        )
        run.lifecycle = "working"
        run.parked_at = ""
        run.parked_polls = 0
        run.reminder_sent = False
        # parked time is answer-wait, not work: restart the active-work
        # budgets (live finding 2026-07-04: an 8h park tripped the wall clock)
        run.created_at = ""
        run.iterations = 0
        self.store.save(run)
        self.store.journal(run.run_id, "resumed")
        if self.config.labels.lifecycle.answered in ticket.labels:
            self._try_labels(run.ticket_iid,
                             remove=[self.config.labels.lifecycle.answered])
        self.log(f"{run.run_id}: human answered; resuming at stage {run.stage}")
        thread = self._render_thread(comments)
        if run.stage == PUBLICATION_STAGE:
            self._deliver(run, ticket, thread)  # never re-enter the stage loop
        else:
            self._conduct(run, ticket, thread=thread)

    def _age_parked(self, run: RunState, ticket: Ticket, summary: dict) -> None:
        """
        @brief      TTL and answer-wait handling for a still-unanswered run.
        @details    Container reap (by polls or seconds) never ends the run;
                    the reminder posts once; the hard answer timeout releases
                    the ticket back to humans, keeping state for audit
                    (design 8b/9).
        @param[in]  run The parked run.
        @param[in]  ticket Fresh ticket.
        @param[in,out] summary Poll summary counters.
        """
        clar = self.config.clarification
        container_cfg = self.config.container
        run.parked_polls += 1
        parked_at = iso_to_datetime(run.parked_at)
        now = iso_to_datetime(utc_now_iso())
        waited = (now - parked_at).total_seconds() if parked_at and now else 0.0
        # container reap (resource bound; the run stays parked and answerable)
        reap = (
            run.parked_polls >= container_cfg.parked_ttl_polls
            if container_cfg.parked_ttl_mode == "polls"
            else waited >= container_cfg.parked_ttl_seconds
        )
        if reap and self.containers.status(run.container) != "absent":
            self.containers.remove(run.container)
            self.store.journal(run.run_id, "container-reaped")
            summary["reaped"] += 1
        # single soft reminder
        if not run.reminder_sent and waited >= clar.reminder_after_seconds():
            author = f"@{ticket.author} " if ticket.author else ""
            self.forge.post_comment(run.ticket_iid, (
                f"{self.identity.tag} {author}reminder: this run is parked "
                "waiting for an answer to the clarification questions above.\n"
                f"{self.identity.make_marker(run.run_id, 'status', state='reminder')}"
            ))
            run.reminder_sent = True
            self.store.journal(run.run_id, "reminder-posted")
        # hard timeout: release the ticket back to humans (ticket stays open)
        if waited >= clar.answer_timeout_seconds():
            self.forge.post_comment(run.ticket_iid, (
                f"{self.identity.tag} No answer within the configured window; "
                "releasing this ticket. Re-apply the ready label to restart.\n"
                f"{self.identity.make_marker(run.run_id, 'status', state='timeout')}"
            ))
            self._teardown(run, remove_worktree=True)
            run.lifecycle = clar.timeout_state
            run.outcome = "answer-timeout"
            self._mark(run, clar.timeout_state, run.stage)
            self.store.journal(run.run_id, "answer-timeout")
            self._record_metrics(run)
            summary["timed_out"] += 1
            self.log(f"{run.run_id}: answer timeout; ticket released")
        self.store.save(run)

    # -- shared internals --------------------------------------------------------

    def _run_id(self, iid: int) -> str:
        """
        @brief      The deterministic run-id for a ticket (design 8a).
        @param[in]  iid Ticket id.
        @return     Stable run identifier.
        """
        return derive_run_id(self.config.platform.kind, self.config.platform.repo, iid)

    def _branch_name(self, run_id: str, iid: int) -> str:
        """
        @brief      Render the run branch name from [worktree] branch_template.
        @details    Repo conventions (e.g. a mandatory "feature/" prefix) are
                    a config change; the stored run.branch stays authoritative
                    for the run's lifetime, so template changes never orphan
                    existing branches.
        @param[in]  run_id Stable run identifier.
        @param[in]  iid Ticket id.
        @return     The branch name.
        """
        return self.config.worktree.branch_template.format(
            slug=self.identity.slug, run_id=run_id, iid=iid
        )

    def _io_dir(self, run_id: str):
        """
        @brief      The run's io exchange dir under the state store.
        @param[in]  run_id Stable run identifier.
        @return     Path to `<store>/runs/<run-id>/io`.
        """
        return self.store.run_dir(run_id) / "io"

    def _provision(self, run: RunState) -> None:
        """
        @brief      Bring up (or back) the run's worktree and container.
        @details    Idempotent by run-id: restart and resume reuse the same
                    resources (design 8a/8b). Secrets = the configured env
                    subset only (design 12b), project-image tool checks, plus
                    the optional host-auth staging for OAuth pilots.
        @param[in]  run The run.
        @exception  IsolationError When git or the container runtime fails.
        """
        if not self.worktrees.exists(run.run_id):
            # first creation: refresh the base ref so the run branches from an
            # up-to-date target rather than a stale local ref. Best-effort - an
            # offline/transient fetch failure must not block provisioning, and
            # delivery fetches + integrates the target again regardless.
            with contextlib.suppress(IsolationError):
                self.worktrees.fetch()
        worktree = self.worktrees.create(run.run_id, run.branch,
                                         run.base_ref or "HEAD")
        run.worktree = str(worktree)
        env = self._container_env(run)
        self.containers.ensure_volumes()
        action = self.containers.provision(
            run.container, self.worktrees.repo_path, worktree,
            self._io_dir(run.run_id), env,
        )
        if action == "created" and run.executor_session:
            # executor sessions live inside the container; a fresh container
            # means the stored session is gone (live finding 2026-07-03)
            run.executor_session = ""
            self.store.journal(run.run_id, "session-reset", cause="container-recreated")
        self.containers.verify_required_tools(
            run.container,
            self.config.container.required_tool_checks,
            env=env,
        )
        if self.config.executor.stage_host_auth:
            self._stage_host_auth(run)
        self.store.save(run)

    def _container_env(self, run: RunState) -> dict[str, str]:
        """
        @brief      Compose the selected executor's container and exec env.
        @details    Used both when the container is created and when commands
                    are launched via `docker/podman exec`, because wrapped
                    runtimes may not inherit create-time env during exec. The
                    `[container] runtime_env` map is intentionally non-secret
                    and lets a project tune portable runtime behavior such as
                    uv link mode without code changes.
        @param[in]  run The run whose worktree admin dir is mounted.
        @return     Git env, configured executor secrets, and selected
                    executor/runtime env.
        """
        env = build_container_env(
            self.worktrees.admin_dir_name(run.run_id),
            self.config.agent.name,
            self.config.agent.email,
        )
        env.update(self.config.container.runtime_env)
        env.update(self.secrets)
        env.update(_EXECUTOR_CONTAINER_ENV.get(self.config.executor.default, {}))
        return env

    def _stage_host_auth(self, run: RunState) -> None:
        """
        @brief      Copy the host's executor auth.json into the container.
        @details    Pilot-only bridge for OAuth (ChatGPT-account) sessions
                    that have no API key (Security_And_Credentials.md). Source
                    and container destination are per-executor
                    (_HOST_AUTH_PATHS): opencode's
                    `~/.local/share/opencode/auth.json` or codex's host
                    `~/.codex/auth.json` staged into ADORE's container-only
                    `CODEX_HOME`. The file travels through the io mount and is
                    deleted from it immediately - the secret never stays on
                    disk outside the container. A missing host file only logs:
                    the executor will fail visibly with an auth error.
        @param[in]  run The provisioned run.
        """
        if not self.host_auth_path.is_file():
            self.log(f"{run.run_id}: stage_host_auth on, but {self.host_auth_path} "
                     "is missing; the executor will lack credentials")
            return
        io_dir = self._io_dir(run.run_id)
        io_dir.mkdir(parents=True, exist_ok=True)
        staged = io_dir / "host-auth.json"
        shutil.copy2(self.host_auth_path, staged)
        # The source auth.json is typically mode 0600; copy2 preserves that, so
        # the container user cannot read it through the io mount when its UID
        # does not match the host (a hand-built image without --build-arg
        # USER_UID). Widen the transient staged copy to 0644 so staging works
        # regardless of UID alignment; it lives only in this run's io dir and is
        # deleted immediately below.
        with contextlib.suppress(OSError):
            staged.chmod(0o644)
        try:
            execute = partial(self.containers.exec, run.container, env=self._container_env(run))
            execute(["mkdir", "-p", self.host_auth_container_dir])
            result = execute([
                "cp", f"{CONTAINER_IO_MOUNT}/host-auth.json",
                f"{self.host_auth_container_dir}/auth.json",
            ])
            if not result.ok:
                self.log(f"{run.run_id}: auth staging failed: {result.stderr}")
            else:
                self.store.journal(run.run_id, "host-auth-staged")
        finally:
            staged.unlink(missing_ok=True)

    def _gate_prompt(
        self,
        stage: str,
        ticket: Ticket,
        failure_context: str,
        thread: str,
        orientation: str = "",
        status: AegisResponse | None = None,
        aegis_run_id: str = "",
    ) -> str:
        """
        @brief      Compose the bounded, stage-specific executor instruction.
        @details    The executor owns content and AEGIS's generated context,
                    reference, skill, and form checklist own procedure. The
                    prompt keeps only conductor policy and forbids reserved
                    actions:
                    `aegis stage close` (ADORE is the delegated approver) and
                    `aegis waive add` (a human decision). Quick policy locks
                    executable red-before-green evidence, INV-3, and
                    nothing-ran semantics without duplicating stage mechanics.
                    The run id is pinned explicitly and changing runs is
                    prohibited.
        @param[in]  stage AEGIS stage name, or "revise".
        @param[in]  ticket Ticket for context.
        @param[in]  failure_context Previous-attempt failure summary ("" on
                                    first attempt).
        @param[in]  thread Rendered clarification thread ("" outside resume).
        @param[in]  orientation Read-only AEGIS run brief ("" when a fresh
                                session already carries the run context).
        @param[in]  status The `run status` response driving this stage, when
                           the conductor has one (selects the quick variant).
        @param[in]  aegis_run_id The run id to pin ("" when none exists yet).
        @return     The prompt text (never enters argv; file protocol).
        """
        quick = status is not None and status.detail("run_profile") == "quick"
        goals = _STAGE_GOALS
        if quick and stage in _QUICK_STAGE_GOALS:
            goals = {**_STAGE_GOALS, **_QUICK_STAGE_GOALS}
        parts = [
            "You are the executor for one stage of the AEGIS governed "
            "workflow, launched headless by the ADORE orchestrator in an "
            "isolated git worktree.",
            f"Ticket #{ticket.iid}: {ticket.title}",
            "Ticket description:\n" + ticket.description.strip(),
        ]
        if thread:
            parts.append("Clarification thread so far (newest last):\n" + thread)
        if orientation:
            parts.append(orientation)
        if failure_context:
            parts.append(failure_context)
        parts.append(goals[stage])
        pin = (
            f"Pin every AEGIS command to this run with `--run {aegis_run_id}`; "
            "never start, select, abandon, or substitute another run. "
            if aegis_run_id else ""
        )
        parts.append(
            "Rules: remain within the current stage and work only inside this "
            "worktree. Run the AEGIS CLI with canonical global options as "
            "`bash .agentic/tools/run.sh --run <run-id> --json <group> "
            "<action>`; content goes into generated forms, never CLI flags. "
            f"{pin}Obey the orchestrator's iteration, time, cost, and file "
            "budgets. NEVER run "
            "`aegis stage close` (the orchestrator is the delegated approver "
            "and closes stages itself after verifying) and NEVER run "
            "`aegis waive add` (waiving a blocker is a human decision - report "
            "it instead). COMMIT all governed changes locally before finishing "
            "(including `.agentic` run records and new files) - a stage is "
            "not complete with a dirty working tree. NEVER push, open "
            "merge/pull requests, or merge - the orchestrator owns the remote. "
            "If you hit blocking questions, record them in the stage form's "
            f"`control.unresolved_questions`, or write them to "
            f"{self.questions_file} in the worktree root, and stop. Stop at "
            "the end of this stage and summarize what you did."
        )
        return "\n\n".join(parts)

    @staticmethod
    def _render_thread(comments: list[Comment], limit: int = 20) -> str:
        """
        @brief      Render the ticket comment thread for a resume prompt.
        @param[in]  comments All ticket comments (oldest first).
        @param[in]  limit Keep only the newest N non-system comments.
        @return     "author: body" blocks, oldest first.
        """
        kept = [c for c in comments if not c.system][-limit:]
        return "\n\n".join(f"{c.author}: {c.body.strip()}" for c in kept)

    def _cost_spent(self, run: RunState) -> float:
        """
        @brief      Total USD the executor reported for this run so far.
        @details    Sums `cost_usd` across the run's journaled `usage` events.
                    The journal is the append-only truth (the io event stream
                    is overwritten every launch), so this survives restarts
                    and covers stage launches, delivery fixes, and revise
                    rounds alike. Non-numeric or missing values are ignored
                    rather than raising: a torn journal line must not be able
                    to stop a run, and the enclosing budget check fails open
                    to "keep going" for exactly one more iteration, where the
                    other budgets still apply.
        @param[in]  run The run.
        @return     Reported spend in USD (0.0 when nothing was reported).
        """
        total = 0.0
        for event in self.store.read_journal(run.run_id):
            if event.get("event") != "usage":
                continue
            cost = event.get("cost_usd")
            if isinstance(cost, (int, float)) and not isinstance(cost, bool):
                total += float(cost)
        return total

    def _budget_exceeded(self, run: RunState) -> str:
        """
        @brief      Check the run budgets (design 10); empty string = fine.
        @details    Iterations (executor launches), wall clock since pickup,
                    cost, and files touched vs the base ref - cheapest check
                    first, so a run that blew its iteration count never pays
                    for a journal read or a git call.

                    Cost is summed from the run's journaled `usage` events,
                    the append-only record `_journal_usage` writes after every
                    launch. That makes the cap only as good as what the
                    executor reports: an executor that reports no usage
                    (or `[metrics] capture_tokens = false`) journals no
                    events, sums to zero, and never trips - documented in
                    Configuration_Reference.md rather than guessed at here.
        @param[in]  run The run.
        @return     Human-readable reason, or "".
        """
        budgets = self.config.budgets
        if run.iterations >= budgets.max_iterations:
            return f"budget exceeded: {run.iterations} executor iterations"
        started = iso_to_datetime(run.created_at)
        now = iso_to_datetime(utc_now_iso())
        if started and now:
            elapsed = (now - started).total_seconds()
            if elapsed > budgets.max_wall_clock_seconds:
                return f"budget exceeded: wall clock {int(elapsed)}s"
        spent = self._cost_spent(run)
        if spent > budgets.max_cost_usd:
            return f"budget exceeded: cost ${spent:.2f}"
        if run.base_ref and self.worktrees.exists(run.run_id):
            try:
                # an in-progress target merge stages upstream files; that is
                # integration noise, not the run's scope (live finding
                # 2026-07-03: 13 staged upstream files tripped the budget)
                if not self.worktrees.merge_in_progress(run.run_id):
                    touched = self.worktrees.changed_files(run.run_id, run.base_ref)
                    if touched > budgets.max_files_touched:
                        return f"budget exceeded: {touched} files touched"
            except IsolationError:
                pass
        return ""

    def _escalate(self, run: RunState, reason: str) -> None:
        """
        @brief      Terminal failure: mark failed, keep everything auditable.
        @details    Worktree and state are kept for a human; the container is
                    stopped. `adore retry` can re-arm the run.

                    The reason also goes ON THE TICKET, in its own comment.
                    The edited status line only ever says "failed", so an
                    operator watching the forge - the normal remote-team
                    posture - otherwise saw a run stop with no actionable
                    information, and the composed `aegis waive add` hint was
                    invisible to anyone without host access. The post is
                    best-effort: the local state is authoritative, so a forge
                    outage must not stop a run from reaching its terminal
                    state. Callers redact the reason before passing it.
        @param[in]  run The run.
        @param[in]  reason Human-readable escalation reason (already redacted).
        """
        run.lifecycle = "failed"
        run.outcome = reason
        self.store.save(run)
        self.store.journal(run.run_id, "escalated", reason=reason)
        self._mark(run, "failed", run.stage)
        with contextlib.suppress(ForgeError):
            self.forge.post_comment(run.ticket_iid, (
                f"{self.identity.tag} Run escalated to failed at stage "
                f"{run.stage}.\n\n"
                f"Reason: {reason}\n\n"
                f"Inspect with `adore logs {run.run_id}`; continue with "
                f"`adore retry {run.run_id}` after resolving.\n"
                f"{self.identity.make_marker(run.run_id, 'escalation')}"
            ))
        with contextlib.suppress(IsolationError):
            self.containers.stop(run.container)
        self._record_metrics(run)
        self.log(f"{run.run_id}: escalated to failed ({reason})")

    def _teardown(self, run: RunState, *, remove_worktree: bool) -> None:
        """
        @brief      Remove the run's container (and optionally worktree).
        @details    `<store>/runs/<run-id>` state always survives for audit.
                    Worktree removal retries past the WSL bind-mount teardown
                    race inside `WorktreeManager.remove` itself (isolation
                    layer, ADORE-ARCH-009); this only leaves a husk for
                    `adore cleanup` if that retry is exhausted.
        @param[in]  run The run.
        @param[in]  remove_worktree Also remove worktree + branch.
        """
        try:
            self.containers.remove(run.container)
        except IsolationError as exc:
            self.log(f"{run.run_id}: container removal failed: {exc}")
        if remove_worktree:
            try:
                self.worktrees.remove(run.run_id, delete_branch=run.branch)
            except IsolationError as exc:
                self.log(f"{run.run_id}: worktree removal failed: {exc} "
                         "(husk left for `adore cleanup`)")

    def _journal_usage(self, run: RunState, context: str, result) -> None:
        """
        @brief      Journal one executor launch's token usage (design 13).
        @details    The io event stream is overwritten per gate, so usage is
                    captured incrementally into the journal - the append-only
                    truth metrics are computed from. Gated by
                    [metrics] capture_tokens.
        @param[in]  run The run.
        @param[in]  context Gate name or fix phase.
        @param[in]  result The GateRun carrying the extracted totals.
        """
        if not self.config.metrics.capture_tokens:
            return
        if result.tokens_in or result.tokens_out or result.cost_usd:
            self.store.journal(
                run.run_id, "usage", context=context,
                tokens_in=result.tokens_in, tokens_out=result.tokens_out,
                cost_usd=result.cost_usd,
            )

    def _journal_artifacts(self, run: RunState, context: str, result) -> None:
        """
        @brief      Journal immutable executor archive directories for a launch.
        @details    The raw live exchange files stay under io/, but each launch
                    may now also produce immutable archives. Journaling the
                    paths makes `adore logs <run-id>` point operators at the
                    exact raw evidence for Task Scheduler and unattended runs.
        @param[in]  run The run.
        @param[in]  context Gate name or fix phase.
        @param[in]  result The GateRun carrying archive paths.
        """
        if result.artifact_dirs:
            self.store.journal(
                run.run_id, "executor-artifacts",
                context=context,
                artifacts=result.artifact_dirs,
            )

    def _record_metrics(self, run: RunState) -> None:
        """
        @brief      Persist the run summary at a terminal state (design 13).
        @details    Best-effort by contract: metrics failures are logged and
                    never break a run. Called BEFORE teardown on merge/close
                    so files-changed is still measurable; INSERT OR REPLACE
                    keeps re-records (retry -> fail again) duplicate-free.
        @param[in]  run The run at a terminal state.
        """
        if not self.config.metrics.enabled:
            return
        try:
            files = 0
            if run.base_ref and self.worktrees.exists(run.run_id):
                with contextlib.suppress(IsolationError):
                    files = self.worktrees.changed_files(run.run_id, run.base_ref)
            summary = metrics.summarize_run(self.store, run.run_id, files)
            metrics.record_summary(
                self.config.metrics.db_path, summary,
                self.config.metrics.export_jsonl,
            )
        except Exception as exc:  # noqa: BLE001 - metrics never break a run
            self.log(f"{run.run_id}: metrics recording failed: {exc}")

    def _mark(self, run: RunState, state: str, stage: str) -> None:
        """
        @brief      Reflect run state on the ticket (design 5d).
        @param[in]  run The run.
        @param[in]  state Human-facing state (working/parked/failed/...).
        @param[in]  stage Current gate.
        """
        self._try_mark(run, state, stage)

    def _try_mark(self, run: RunState, state: str, stage: str) -> None:
        """
        @brief      Best-effort ticket signaling (comments and/or labels).
        @details    Comments channel: ONE status comment edited in place (id
                    recorded in state.json). Labels channel: lifecycle label
                    transitions. Signaling failures never break the run -
                    local state is authoritative (design 5c).
        @param[in]  run The run.
        @param[in]  state Human-facing state.
        @param[in]  stage Current gate.
        """
        channel = self.config.state.channel
        try:
            if channel in ("comments", "both"):
                body = self.identity.status_comment(
                    run.run_id, state, stage, utc_now_iso()
                )
                if run.status_comment_id is None:
                    run.status_comment_id = self.forge.post_comment(
                        run.ticket_iid, body
                    )
                    self.store.save(run)
                else:
                    self.forge.edit_comment(
                        run.ticket_iid, run.status_comment_id, body
                    )
            if channel in ("labels", "both"):
                self._apply_lifecycle_labels(run.ticket_iid, state)
        except ForgeError as exc:
            self.log(f"{run.run_id}: status marking failed: {exc}")

    def _apply_lifecycle_labels(self, iid: int, state: str) -> None:
        """
        @brief      Label-channel transitions for a state (design 5b).
        @param[in]  iid Ticket id.
        @param[in]  state Human-facing state.
        """
        lifecycle = self.config.labels.lifecycle
        transitions: dict[str, tuple[list[str], list[str]]] = {
            "working": ([lifecycle.working],
                        [lifecycle.ready, lifecycle.clarify, lifecycle.answered]),
            "validated": ([lifecycle.working], [lifecycle.clarify]),
            "parked": ([lifecycle.clarify], [lifecycle.working]),
            "review": ([lifecycle.review],
                       [lifecycle.working, lifecycle.clarify]),
            "done": ([lifecycle.done], [lifecycle.review, lifecycle.working]),
            "failed": ([lifecycle.failed],
                       [lifecycle.working, lifecycle.clarify, lifecycle.review]),
            "stale": ([lifecycle.failed],
                      [lifecycle.working, lifecycle.clarify]),
            "cancelled": ([], [lifecycle.working, lifecycle.clarify]),
            "ticket-closed": ([], [lifecycle.working, lifecycle.clarify]),
        }
        add, remove = transitions.get(state, ([], []))
        self._try_labels(iid, add=add, remove=remove)

    def _try_labels(
        self,
        iid: int,
        *,
        add: list[str] | None = None,
        remove: list[str] | None = None,
    ) -> None:
        """
        @brief      Best-effort label add/remove.
        @param[in]  iid Ticket id.
        @param[in]  add Labels to add.
        @param[in]  remove Labels to remove.
        """
        try:
            if add:
                self.forge.add_labels(iid, add)
            if remove:
                self.forge.remove_labels(iid, remove)
        except ForgeError as exc:
            self.log(f"label update failed on #{iid}: {exc}")


# END OF FILE
