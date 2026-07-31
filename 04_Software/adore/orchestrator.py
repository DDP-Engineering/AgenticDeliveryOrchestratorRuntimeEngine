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
         AEGIS 2.x workflow with objective verification in between, park on
         clarification questions and resume on human answers, enforce run
         budgets, and escalate instead of thrashing. Never merges; publication
         (draft MR) belongs to ADORE alone. No LLM runs here - every decision
         is an `if` on exit codes, envelope fields, file presence, labels, and
         timestamps. All collaborators are injected so the whole machine is
         unit-testable offline.
@details Conduction is `next`-driven: AEGIS owns the stage pointer and ADORE
         asks `run status` for it on every iteration, guarded by a static
         allowlist per run profile. ADORE is the delegated approver - the
         executor fills forms and applies them, ADORE verifies objectively and
         issues `stage close` itself - while the real human approval stays at
         the draft MR review.
@author Eng. Dan Dumitru Pasare
@date 2026-08-01
@version 0.8.0
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable
import contextlib
from dataclasses import dataclass
from functools import partial
import json
import os
from pathlib import Path
import random
import re
import shutil
import time

from adore import metrics
from adore.aegis import (
    INTEGRITY_CODES,
    QUICK_KINDS,
    RUN_RESOLUTION_CODES,
    AegisClient,
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

# The AEGIS 2.x executable stage sequences (contract notes section 4). These
# are an ALLOWLIST, not the conductor's idea of truth: AEGIS owns the stage
# pointer and ADORE reads it from `run status`. Any stage outside the tuple
# for the run's profile - or a backwards move, which only an approved
# `route_to` can produce - is a contract break and escalates.
STANDARD_STAGES = ("intake", "alignment", "requirement", "design", "check",
                   "implementation", "validation", "delivery")
QUICK_STAGES = ("intake", "implementation", "validation", "delivery")

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

# classify_block outcomes.
BLOCK_PARK = "park"
BLOCK_RETRY = "retry"
BLOCK_ESCALATE = "escalate"

# A live AEGIS persistence lock clears in seconds (its own wait is 15 s), so
# exactly one bounded re-attempt is warranted before a human is involved.
LOCK_TIMEOUT_CODE = "PERSISTENCE-LOCK-TIMEOUT"
_LOCK_RETRY_DELAY = 20.0
_MAX_LOCK_RETRIES = 1

# An in-review MR that reads back as not-found is usually a real deletion, but
# a single 404 can also be a transient platform blip. Tolerate a few before
# ending the run, so an in-review run whose MR truly vanished cannot re-poll
# (and re-log) forever, while a momentary blip is ridden out.
_MR_MISSING_GRACE_POLLS = 3

# Worktree removal right after container removal can transiently fail on WSL2:
# `docker/podman rm` returns before the kernel releases the container's
# 9P/drvfs bind mount on the worktree, so git's delete hits these errors until
# the mount clears (a few seconds). Retrying past them avoids leaving a husk
# for `adore cleanup` (live finding 2026-07-04/05).
_TEARDOWN_RACE_MARKERS = (
    "function not implemented",   # ENOSYS - the observed WSL signature
    "device or resource busy",    # EBUSY  - mount still attached
    "resource busy",
    "directory not empty",        # ENOTEMPTY - files not yet released
)
_TEARDOWN_RETRY_DELAYS = (1.0, 2.0, 4.0)  # ~7s ceiling; the race clears in seconds

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
    "intake": (
        "Work the AEGIS INTAKE stage: run `aegis stage prepare`, fill the "
        "generated intake form with the statement, scope hints, and access "
        "mode, then `aegis stage apply`."
    ),
    "alignment": (
        "Work the AEGIS ALIGNMENT stage: fill the alignment form BEFORE any "
        "spec or code work - what you understood, what is in and out of "
        "scope, your assumptions, the acceptance target, the implementation "
        "areas you expect to touch, and the proceed/pause decision - then "
        "`aegis stage apply`. If the honest decision is pause, record your "
        "blocking questions in the form's control table and stop."
    ),
    "requirement": (
        "Work the AEGIS REQUIREMENT stage: create one form per durable "
        "requirement with `aegis stage add`, fill them, and `aegis stage "
        "apply`. AEGIS mints the requirement IDs; requirements enter as "
        "Planned."
    ),
    "design": (
        "Work the AEGIS DESIGN stage: write the authoritative design at "
        "`.agentic/runs/<run-id>/design.md`, cite the requirements it "
        "satisfies in the stage form, and `aegis stage apply`."
    ),
    "check": (
        "Work the AEGIS CHECK stage: add one form per check with `aegis stage "
        "add` citing the requirement IDs, apply the stage, then produce RED "
        "evidence for every check - `aegis check run` in managed mode, or "
        "`aegis check prepare` / complete `evidence.toml` / `aegis check "
        "record` in external mode. Red-before-green is mandatory."
    ),
    "implementation": (
        "Work the AEGIS IMPLEMENTATION stage: edit only source roots to make "
        "the checks pass, produce GREEN evidence for every check the same way "
        "you produced the red evidence, fill the implementation form with the "
        "changed paths, and `aegis stage apply`."
    ),
    "validation": (
        "Work the AEGIS VALIDATION stage: run `aegis verify run` and fix "
        "everything it reports, inspect the diff for scope creep, weakened "
        "assertions, and secrets, fill the validation form, and `aegis stage "
        "apply`."
    ),
    "delivery": (
        "Work the AEGIS DELIVERY stage: fill the delivery form summarizing "
        "what shipped and the residual risk, and `aegis stage apply`. Do NOT "
        "push, open a merge/pull request, or merge - the orchestrator "
        "publishes."
    ),
    "revise": (
        "A human reviewer requested changes on the draft merge request (the "
        "review thread is above). Make exactly the requested changes - no "
        "more - update tests and evidence accordingly, re-run `aegis verify "
        "run`, and commit everything."
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
    @author  Eng. Dan Dumitru Pasare
    @date    2026-08-01
    @version 0.1.0
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-08-01
    @version    0.1.0
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


def _is_teardown_race(exc: IsolationError) -> bool:
    """
    @brief      Whether a worktree-removal failure is the transient WSL
                bind-mount teardown race (worth retrying) vs a real error.
    @param[in]  exc The IsolationError raised by worktree removal.
    @return     True when the stderr matches a known mount-release signature.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    text = (getattr(exc, "stderr", "") or str(exc)).lower()
    return any(marker in text for marker in _TEARDOWN_RACE_MARKERS)


# PUBLIC API


class Orchestrator:
    """
    @brief   Coordinates polling, isolation, gate conducting, and clarification.
    @details Owns everything deterministic and every remote (Git-platform)
             operation; the executor owns code reasoning. Authoritative state
             lives in the local StateStore; ticket comments/labels only
             reflect it (design 5c).
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-05
        @version    0.1.2
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

    @classmethod
    def from_config(cls, config: Config, env_file: str = ".env") -> Orchestrator:
        """
        @brief      Build the engine with production collaborators.
        @param[in]  config Validated configuration.
        @param[in]  env_file Dotenv file holding the executor secrets.
        @return     A ready Orchestrator.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-29
        @version    0.1.2
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
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-03
        @version 0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.2.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.2.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-07
        @version    0.2.1
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
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-03
        @version 0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.3.0
        """
        if run.stage == PUBLICATION_STAGE:
            # fail closed: silently restarting the stage loop regressed a
            # publishing run once (live finding 2026-07-04)
            self._escalate(run, f"internal: conduct called with stage {run.stage!r}")
            return
        try:
            self._provision(run)
        except IsolationError as exc:
            self._escalate(run, f"isolation failed: {exc}")
            return
        execute = partial(self.containers.exec, run.container, env=self._container_env(run))
        client = AegisClient(execute, run_id=run.aegis_run_id or "")
        try:
            self._conduct_stages(run, ticket, client, thread)
        except AegisError as exc:
            self._escalate_aegis(run, exc)

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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        if not self._ensure_aegis_run(run, ticket, client):
            return
        failure_context = ""
        # A run picked up mid-workflow (after a restart) launches a fresh
        # executor session with no prior context; orient its first launch.
        # Retries orient too - they already carry a failure_context.
        need_orientation = run.stage != STANDARD_STAGES[0]
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
            if status.complete:
                self.store.journal(run.run_id, "aegis-run-complete",
                                   aegis_run=client.run_id)
                break
            stage = self._checked_stage(status, closed_index)
            run.stage = stage
            self._mark(run, "working", stage)
            run.iterations += 1
            self.store.save(run)
            self.store.journal(run.run_id, "stage-launch", stage=stage,
                               iteration=run.iterations,
                               next=status.next_command)
            orientation = (
                self._workflow_orientation(client)
                if (failure_context or need_orientation) else ""
            )
            need_orientation = False
            result = self.executor.run_gate(
                execute=client.execute,
                worktree=self.worktrees.path_for(run.run_id),
                io_dir=self._io_dir(run.run_id),
                prompt=self._gate_prompt(stage, ticket, failure_context, thread,
                                         orientation, status),
                session=run.executor_session,
                timeout=self.config.budgets.per_gate_timeout_seconds,
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
            closed = client.stage_close()
            while not closed.ok:
                # retry the close itself, not the whole iteration: the stage is
                # already applied, so relaunching the executor would be waste
                if not self._retryable(run, closed, f"stage close ({stage})",
                                       client, lock_retries):
                    return
                lock_retries += 1
                closed = client.stage_close()
            failure_context = ""
            lock_retries = 0  # a closed stage is real progress
            closed_index = self._expected_stages(status).index(stage)
            self.store.journal(run.run_id, "stage-closed", stage=stage,
                               complete=closed.complete)
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
                    orphan a governed run.
        @param[in]  run The run.
        @param[in]  ticket Current ticket (label source).
        @param[in,out] client Client that captures the run id.
        @return     True when a run id is available; False when the start was
                    blocked and the run has already been parked/escalated.
        @exception  AegisError When the CLI contract is violated.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        if client.run_id:
            return True
        kind, quick = self._run_kind(ticket)
        response = client.run_start(kind, quick)
        if not response.ok and self._retryable(
            run, response, f"run start {kind}", None, 0
        ):
            response = client.run_start(kind, quick)
            if not response.ok:
                self._handle_block(run, response, f"run start {kind}", None)
                return False
        if not response.ok:
            return False
        run.aegis_run_id = client.run_id
        run.stage = response.stage or STANDARD_STAGES[0]
        self.store.save(run)
        self.store.journal(run.run_id, "aegis-run-started",
                           aegis_run=client.run_id, kind=kind, quick=quick)
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
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

    @staticmethod
    def _expected_stages(status: AegisResponse) -> tuple[str, ...]:
        """
        @brief      The stage allowlist for the run's AEGIS profile.
        @details    AEGIS reports `run_profile` only for quick runs; its
                    absence means the full eight-stage sequence.
        @param[in]  status A `run status` response.
        @return     STANDARD_STAGES or QUICK_STAGES.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        return (
            QUICK_STAGES
            if status.detail("run_profile") == "quick"
            else STANDARD_STAGES
        )

    def _checked_stage(self, status: AegisResponse, closed_index: int) -> str:
        """
        @brief      Validate the reported stage against the allowlist.
        @details    Two guards, both fail-loud. A stage outside the profile's
                    sequence means the contract moved under ADORE. A stage at
                    or before the last one ADORE already closed means the run
                    was routed backwards - what an approved `route_to`
                    produces - which is explicitly out of scope for 2.0.0, so
                    a human decides. Re-running a stage that is not yet closed
                    is a normal retry and passes both guards.
        @param[in]  status A `run status` response.
        @param[in]  closed_index Index of the last stage ADORE closed (-1 when
                                 it has closed none yet).
        @return     The validated stage name.
        @exception  AegisProtocolError When the stage is unknown or regressed.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.2.0
        """
        expected = self._expected_stages(status)
        stage = status.stage
        if stage not in expected:
            raise AegisProtocolError(
                f"AEGIS reported stage {stage!r}, which is not in the expected "
                f"sequence for this run ({', '.join(expected)})"
            )
        if expected.index(stage) <= closed_index:
            raise AegisProtocolError(
                f"AEGIS routed the run back from {expected[closed_index + 1]!r} "
                f"to {stage!r}; a stage regression is a human decision in this "
                "ADORE version"
            )
        return stage

    def _verify_stage(
        self,
        run: RunState,
        client: AegisClient,
        stage: str,
    ) -> tuple[str, AegisResponse | None]:
        """
        @brief      ADORE's objective check before it closes a stage.
        @details    The conductor never takes the executor's word: `stage show`
                    must report `ready` with no blockers, the validation and
                    delivery stages must additionally survive a full
                    `verify run`, and the validation stage must leave committed
                    work behind (a clean tree with commits over the base).
        @param[in]  run The run.
        @param[in]  client The run's AEGIS client.
        @param[in]  stage Stage just applied by the executor.
        @return     ("", None) when the stage may be closed, else the relaunch
                    reason and the response that produced it (so the caller can
                    attach the response's own evidence).
        @exception  AegisError When the CLI contract is violated.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.2.0
        """
        shown = client.stage_show()
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
        if stage in ("validation", "delivery"):
            verified = client.verify_run()
            if not verified.ok:
                self.store.journal(run.run_id, "verify-failed", stage=stage,
                                   exit_code=verified.exit_code)
                return (
                    f"`aegis verify run` failed at the {stage} stage "
                    f"(exit {verified.exit_code}). Fix every blocking finding "
                    "and re-run it until it passes.",
                    verified,
                )
            self.store.journal(run.run_id, "verify-passed", stage=stage)
        if stage == "validation":
            committed = self._work_committed(run)
            if committed:
                self.store.journal(run.run_id, "work-uncommitted")
                return committed, None
        return "", None

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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.2.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        run_dir = self._aegis_run_dir(run)
        if run_dir is None or not stage or stage == "none":
            return None
        graph = self._load_aegis_graph(run_dir / "graph.json")
        records = graph.get("stage_records") if isinstance(graph, dict) else None
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.2.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.3.0
        """
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
        execute = partial(self.containers.exec, run.container, env=self._container_env(run))
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        execute = client.execute
        if not revise:
            # idempotent recovery: adopt an MR already open for this branch
            with contextlib.suppress(ForgeError):
                existing = self.forge.get_merge_request(run.mr_iid or run.branch)
                if existing and existing.state == "opened":
                    self._enter_review(run, existing)
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
        # 2.x `verify run` IS the gate run plus the invariant, traceability,
        # coverage and working-tree audits, so it replaces both 1.x steps.
        while True:
            verified = client.verify_run()
            if verified.ok:
                self.store.journal(run.run_id, "verify-run-passed")
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
        title = f"Resolve #{ticket.iid}: {ticket.title}"
        body = "" if revise and run.mr_iid else self._mr_description(
            run, ticket, client
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
            self._enter_review(run, None)
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
        self._enter_review(run, None)

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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.3.0
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
            self._gate_prompt("validation", ticket, context, thread, orientation),
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

    def _enter_review(self, run: RunState, adopted: MergeRequest | None) -> None:
        """
        @brief      Hand off to human review, keeping the environment alive.
        @details    Design 11a step 8: container stopped (not removed),
                    worktree kept, so review feedback can resume without
                    re-provisioning. Status -> review; kind=delivery comment
                    carries the MR link.
        @param[in]  run The run.
        @param[in]  adopted An already-open MR when adopting, else None.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.2.0
        """
        if adopted is not None:
            run.mr_iid = adopted.iid
            run.mr_url = adopted.web_url or run.mr_url
        run.lifecycle = "in-review"
        self.store.save(run)
        self._mark(run, "review", "delivery")
        with contextlib.suppress(ForgeError):
            self.forge.post_comment(run.ticket_iid, (
                f"{self.identity.tag} Draft MR ready for review: {run.mr_url}\n"
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-24
        @version    0.1.3
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-24
        @version    0.1.2
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
            self._gate_prompt("revise", ticket, "", thread, orientation),
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

    def _mr_description(self, run: RunState, ticket: Ticket,
                        client: AegisClient) -> str:
        """
        @brief      Compose the draft MR description (design 11).
        @details    "Related to #N", never an auto-close keyword - closure is
                    the human's call. `aegis delivery report` renders the
                    run's report; its content is embedded bounded, together
                    with the AEGIS run id and the hidden ADORE marker.
        @param[in]  run The run.
        @param[in]  ticket Current ticket.
        @param[in]  client The run's AEGIS client.
        @return     The MR body.
        @exception  AegisError When the CLI contract is violated.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.2.0
        """
        report = client.delivery_report()
        parts = [
            f"Related to #{ticket.iid}: {ticket.title}",
            f"Produced by {self.identity.name} (run `{run.run_id}`, AEGIS run "
            f"`{client.run_id}`); every AEGIS stage passed its approval and "
            "`aegis verify run` passed after integrating "
            f"`{run.base_ref}`. Opened as a DRAFT - review and merge are human "
            "decisions.",
        ]
        body = self._read_aegis_artifact(run, report.detail("report"))
        if body.strip():
            parts.append("### AEGIS delivery report\n```\n"
                         + self._tail_lines(body, 2500) + "\n```")
        parts.append(self.identity.make_marker(run.run_id, "delivery"))
        return self._redact_failure_context("\n\n".join(parts))

    def _read_aegis_artifact(self, run: RunState, relative: object) -> str:
        """
        @brief      Read a repository-relative artifact AEGIS just wrote.
        @details    AEGIS returns repository-relative POSIX paths. Only paths
                    that stay inside the run's worktree are read, so a
                    surprising value can never pull an unrelated host file into
                    a merge request body or a prompt.
        @param[in]  run The run whose worktree holds the artifact.
        @param[in]  relative The `artifact`/`report` value from an envelope.
        @return     The file content, or "" when the value is unusable.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        if not isinstance(relative, str) or not relative or relative == "none":
            return ""
        worktree = self.worktrees.path_for(run.run_id).resolve()
        candidate = (worktree / relative).resolve()
        if not candidate.is_relative_to(worktree) or not candidate.is_file():
            return ""
        return self._read_text(candidate)

    def _workflow_orientation(self, client: AegisClient) -> str:
        """
        @brief      Compose the run-orientation brief for a fresh session.
        @details    A freshly launched executor session - a retry, a delivery
                    fix, a revise round, or a run resumed mid-workflow after a
                    restart - starts without the prior chat context. AEGIS 2.x
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.2.0
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
        @exception  AegisProtocolError When the run exists but its graph does
                    not - a started run always has one, so its absence is a
                    broken record, not an empty one.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.2.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
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
                    channel in 2.x - the executor's questions file remains a
                    secondary one, and the conductor honors whichever fires.
        @param[in]  run The ADORE run.
        @param[in]  stage The stage just applied.
        @return     A rendered question block, or "" when there are none.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        run_dir = self._aegis_run_dir(run)
        if run_dir is None:
            return ""
        graph = self._load_aegis_graph(run_dir / "graph.json")
        if not isinstance(graph, dict):
            return ""
        records = graph.get("stage_records")
        record = records.get(stage) if isinstance(records, dict) else None
        if not isinstance(record, dict):
            return ""
        questions = [
            str(item).strip()
            for item in (record.get("unresolved_questions") or [])
            if str(item).strip()
        ]
        if not questions:
            return ""
        listed = "\n".join(f"{index}. {text}"
                           for index, text in enumerate(questions, start=1))
        return (
            f"The executor recorded unresolved questions in the AEGIS {stage} "
            f"stage form:\n\n{listed}"
        )

    def _load_aegis_graph(self, path: Path) -> dict | None:
        """
        @brief      Load the AEGIS run graph, or None when it is unusable.
        @param[in]  path Path to `graph.json`.
        @return     The decoded graph mapping, or None.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        if not path.is_file():
            return None
        try:
            graph = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return graph if isinstance(graph, dict) else None

    def _aegis_failure_evidence(self, run: RunState) -> str:
        """
        @brief      Read prompt-safe failure evidence from the AEGIS run.
        @details    Uses the AEGIS file contract under
                    `.agentic/runs/<aegis-run-id>/`, addressed by the run id
                    ADORE persisted rather than by the retired worktree
                    pointer: `validation-summary.json` first (the authoritative
                    verification result), then the schema-3 `graph.json`
                    evidence rows, then `report.md` when it exists. Malformed
                    files are reported in the prompt so the executor
                    understands that evidence was present but damaged. A
                    STARTED run always has a `graph.json`, so its absence is a
                    broken record and fails loud.
        @param[in]  run ADORE run whose worktree is inspected.
        @return     Markdown-ish evidence block, or "" when no evidence exists.
        @exception  AegisProtocolError When the run's graph.json is missing.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.3.0
        """
        run_dir = self._aegis_run_dir(run)
        if run_dir is None:
            return ""
        graph_path = run_dir / "graph.json"
        if not graph_path.is_file():
            raise AegisProtocolError(
                f"AEGIS run {run.aegis_run_id} has no "
                f"{_AEGIS_RUN_DIR}/{run.aegis_run_id}/graph.json; the run "
                "record is missing or was removed from the worktree"
            )
        sections = [
            f"AEGIS failure evidence from `{_AEGIS_RUN_DIR}/{run.aegis_run_id}`:"
        ]
        sections.extend(
            self._summary_failure_evidence(run_dir / "validation-summary.json")
        )
        sections.extend(self._graph_failure_evidence(graph_path))
        sections.extend(self._report_failure_evidence(run_dir / "report.md"))
        if len(sections) == 1:
            return ""
        rendered = "\n".join(sections)
        return self._tail_lines(rendered, _AGENTIC_FAILURE_CONTEXT_LIMIT)

    def _summary_failure_evidence(self, path: Path) -> list[str]:
        """
        @brief      Extract failing gates and invariants from the summary.
        @details    `validation-summary.json` is what `aegis verify run`
                    writes, so it is the authoritative account of WHY
                    verification failed. Disabled and waived gates are reported
                    verbatim - AEGIS never renders either as passed, and
                    neither does this prompt.
        @param[in]  path Path to `validation-summary.json`.
        @return     Lines to append to the retry prompt.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        if not path.is_file():
            return []
        try:
            summary = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return [f"- validation-summary.json: could not parse ({exc})."]
        if not isinstance(summary, dict):
            return ["- validation-summary.json: malformed payload."]
        lines: list[str] = []
        gates = summary.get("gates")
        if isinstance(gates, dict):
            failing = [
                f"{name} ({value.get('status')})"
                for name, value in sorted(gates.items())
                if isinstance(value, dict)
                and value.get("status") not in ("passed", "disabled")
            ][:_AGENTIC_FAILURE_ITEMS_LIMIT]
            if failing:
                lines.append("- Failing gate groups: " + ", ".join(failing))
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

    def _graph_failure_evidence(self, path: Path) -> list[str]:
        """
        @brief      Extract active failing evidence rows from graph.json.
        @details    Schema-3 `evidence[]` rows with `result: "fail"` that were
                    not superseded, rendered with the fields the executor needs
                    to act: id, kind, stage, summary, command, failure kind.
        @param[in]  path Path to the AEGIS run graph.
        @return     Lines to append to the retry prompt.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.2.0
        """
        if not path.is_file():
            return []
        try:
            graph = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return [f"- graph.json: could not parse failure evidence ({exc})."]
        if not isinstance(graph, dict) or not isinstance(graph.get("evidence"), list):
            return ["- graph.json: malformed evidence payload."]
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

    def _report_failure_evidence(self, path: Path) -> list[str]:
        """
        @brief      Extract short report.md excerpts around failure markers.
        @param[in]  path Path to the workflow report.
        @return     Lines to append to the retry prompt.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-08
        @version    0.1.0
        """
        if not path.is_file():
            return []
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            return [f"- report.md: could not read report excerpts ({exc})."]
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

    @staticmethod
    def _read_text(path: Path) -> str:
        """
        @brief      Read a text file, returning "" when it is absent/unreadable.
        @param[in]  path Path to read.
        @return     File content or "".
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-08
        @version    0.1.0
        """
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def _redact_failure_context(self, text: str) -> str:
        """
        @brief      Redact configured executor secret values from prompt context.
        @param[in]  text Candidate prompt context.
        @return     Redacted text.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-08
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-04
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-29
        @version    0.1.1
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
        @param[in]  run The run to park.
        @param[in]  questions Questions text from the worktree file.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        question_id = self.forge.post_comment(run.ticket_iid, body)
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

    def _reconcile_parked(self, summary: dict) -> None:
        """
        @brief      Per poll: parked runs (answers, TTL, timeouts), in-review
                    runs (merge/close detection), and legacy validated runs
                    (deliver them) - design 8b/8c/9/11b.
        @param[in,out] summary Poll summary counters to update.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-06
        @version    0.1.3
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        return self.config.worktree.branch_template.format(
            slug=self.identity.slug, run_id=run_id, iid=iid
        )

    def _io_dir(self, run_id: str):
        """
        @brief      The run's io exchange dir under the state store.
        @param[in]  run_id Stable run identifier.
        @return     Path to `<store>/runs/<run-id>/io`.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-24
        @version    0.1.3
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-06
        @version    0.2.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-25
        @version    0.2.3
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
    ) -> str:
        """
        @brief      Compose the bounded, stage-specific executor instruction.
        @details    The executor owns content, the conductor owns control: the
                    prompt tells it how to fill and apply the stage forms and
                    forbids the two actions ADORE and humans reserve -
                    `aegis stage close` (ADORE is the delegated approver) and
                    `aegis waive add` (a human decision).
        @param[in]  stage AEGIS stage name, or "revise".
        @param[in]  ticket Ticket for context.
        @param[in]  failure_context Previous-attempt failure summary ("" on
                                    first attempt).
        @param[in]  thread Rendered clarification thread ("" outside resume).
        @param[in]  orientation Read-only AEGIS run brief ("" when a fresh
                                session already carries the run context).
        @param[in]  status The `run status` response driving this stage, when
                           the conductor has one (adds the exact next command).
        @return     The prompt text (never enters argv; file protocol).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.2.0
        """
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
        parts.append(_STAGE_GOALS[stage])
        if status is not None and status.next_command:
            parts.append(
                f"AEGIS says the exact next command is `{status.next_command}`."
                + (f" The current stage form is at `{status.artifact}`."
                   if status.artifact and status.artifact != "none" else "")
            )
        parts.append(
            "Rules: work only inside this worktree. Run the AEGIS CLI as "
            "`bash .agentic/tools/run.sh <group> <action>`; content goes into "
            "the generated forms, never into CLI flags. NEVER run "
            "`aegis stage close` (the orchestrator is the delegated approver "
            "and closes stages itself after verifying) and NEVER run "
            "`aegis waive add` (waiving a blocker is a human decision - report "
            "it instead). COMMIT all your changes locally before finishing "
            "(including the `.agentic` run records and new files) - a stage is "
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        kept = [c for c in comments if not c.system][-limit:]
        return "\n\n".join(f"{c.author}: {c.body.strip()}" for c in kept)

    def _budget_exceeded(self, run: RunState) -> str:
        """
        @brief      Check the run budgets (design 10); empty string = fine.
        @details    Iterations (executor launches), wall clock since pickup,
                    and files touched vs the base ref. Cost joins with the
                    metrics phase (token usage is in the event stream).
        @param[in]  run The run.
        @return     Human-readable reason, or "".
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @param[in]  run The run.
        @param[in]  reason Human-readable escalation reason.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.1
        """
        run.lifecycle = "failed"
        run.outcome = reason
        self.store.save(run)
        self.store.journal(run.run_id, "escalated", reason=reason)
        self._mark(run, "failed", run.stage)
        with contextlib.suppress(IsolationError):
            self.containers.stop(run.container)
        self._record_metrics(run)
        self.log(f"{run.run_id}: escalated to failed ({reason})")

    def _teardown(self, run: RunState, *, remove_worktree: bool) -> None:
        """
        @brief      Remove the run's container (and optionally worktree).
        @details    `<store>/runs/<run-id>` state always survives for audit.
                    Worktree removal is retried past the WSL bind-mount
                    teardown race (see _remove_worktree).
        @param[in]  run The run.
        @param[in]  remove_worktree Also remove worktree + branch.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-05
        @version    0.2.0
        """
        try:
            self.containers.remove(run.container)
        except IsolationError as exc:
            self.log(f"{run.run_id}: container removal failed: {exc}")
        if remove_worktree:
            self._remove_worktree(run)

    def _remove_worktree(self, run: RunState) -> None:
        """
        @brief      Remove the run's worktree, retrying the WSL teardown race.
        @details    On WSL2 the container's 9P/drvfs bind mount is released
                    asynchronously after `rm`, so an immediate git worktree
                    remove can fail with ENOSYS/EBUSY until it clears. Retry
                    with backoff ONLY on those transient signatures; a real
                    error is not retried. If it still fails, log and leave the
                    husk - `adore cleanup` sweeps it (no regression). Native
                    docker/Linux succeeds on the first try (no sleeps).
        @param[in]  run The run whose worktree + branch to remove.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-05
        @version    0.1.1
        """
        last: IsolationError | None = None
        for attempt, delay in enumerate((0.0, *_TEARDOWN_RETRY_DELAYS)):
            if delay:
                self.sleep(delay)
            try:
                self.worktrees.remove(run.run_id, delete_branch=run.branch)
                if attempt:
                    self.log(f"{run.run_id}: worktree removed after "
                             f"{attempt} retr{'y' if attempt == 1 else 'ies'}")
                return
            except IsolationError as exc:
                last = exc
                if not _is_teardown_race(exc):
                    break  # a real failure - do not burn retries masking it
        self.log(f"{run.run_id}: worktree removal failed: {last} "
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-04
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-07
        @version    0.1.1
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-04
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        try:
            if add:
                self.forge.add_labels(iid, add)
            if remove:
                self.forge.remove_labels(iid, remove)
        except ForgeError as exc:
            self.log(f"label update failed on #{iid}: {exc}")


# END OF FILE
