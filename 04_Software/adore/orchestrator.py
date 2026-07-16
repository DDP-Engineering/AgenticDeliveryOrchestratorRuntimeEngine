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
         (worktree + container), drive the executor gate-by-gate with
         verification in between, park on clarification questions and resume
         on human answers, enforce run budgets, and escalate instead of
         thrashing. Never merges; delivery (draft MR) is phase 4. No LLM runs
         here - every decision is an `if` on exit codes, file presence,
         labels, and timestamps. All collaborators are injected so the whole
         machine is unit-testable offline.
@author Eng. Dan Dumitru Pasare
@date 2026-07-06
@version 0.6.0
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable
import contextlib
from functools import partial
import json
import os
from pathlib import Path
import random
import re
import shutil
import time

from adore import gates, metrics
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

GATES = ("intake", "alignment", "requirement", "check", "implementation",
         "validation")

_AGENTIC_CURRENT_RUN = ".agentic/current_run"
_AGENTIC_FAILURE_CONTEXT_LIMIT = 5000
_AGENTIC_FAILURE_ITEMS_LIMIT = 5

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

_GATE_GOALS = {
    "intake": (
        "Run the INTAKE gate: classify the request, start the agentic workflow "
        "run for this ticket (agentic-development skill / .agentic CLI), analyze "
        "impact, and confirm you understand the scope."
    ),
    "alignment": (
        "Run the ALIGNMENT gate: record the intent alignment (.agentic CLI "
        "alignment command) BEFORE any spec or code work - state what you "
        "understood, what is in and out of scope, your assumptions, the "
        "acceptance target, the implementation areas you expect to touch, and "
        "the proceed/pause decision. If the honest decision is pause, write "
        "your blocking questions to the questions file and stop."
    ),
    "requirement": (
        "Run the REQUIREMENT gate: create durable requirement rows for this "
        "ticket (add-spec; requirements enter as Planned) and run invariants."
    ),
    "check": (
        "Run the CHECK gate: add checks citing the spec ids, write the failing "
        "tests, and record red evidence (record-evidence --result fail). "
        "Red-before-green is mandatory."
    ),
    "implementation": (
        "Run the IMPLEMENTATION gate: edit only source roots to make the checks "
        "pass, record green evidence, record-change, activate requirements whose "
        "linked checks are green, and update component documentation."
    ),
    "validation": (
        "Run the VALIDATION gate: run invariants, audit traceability, audit "
        "coverage, impact, and gates run; inspect the diff for scope creep, "
        "weakened assertions, and secrets."
    ),
    "revise": (
        "A human reviewer requested changes on the draft merge request (the "
        "review thread is above). Make exactly the requested changes - no "
        "more - update tests and workflow evidence accordingly, re-run the "
        "gates, and commit everything."
    ),
}

# HELPER FUNCTIONS


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
        @date       2026-07-07
        @version    0.1.1
        """
        entry = config.executor.commands[config.executor.default]
        env = {**load_env_file(env_file), **os.environ}
        secrets = {key: env[key] for key in config.executor.env_keys if env.get(key)}
        return cls(
            config=config,
            forge=build_forge(config.platform.kind, config.platform.repo),
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
        if run.stage == "delivery":
            self._deliver(run, ticket)  # never restart the gates from intake
        else:
            self._conduct(run, ticket)
        return True

    def reset(self, run_id: str, stage: str) -> bool:
        """
        @brief      State surgery (design 8c): force a run back to a stage.
        @details    Sets the stage pointer and leaves the run retry-able
                    (`adore retry` then re-arms budgets and conducts from
                    there). Destructive by nature - the CLI requires --force.
        @param[in]  run_id Stable run identifier.
        @param[in]  stage Target stage (a gate name or "delivery").
        @return     True when the run existed and the stage is valid.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-04
        @version    0.1.1
        """
        if stage not in (*GATES, "delivery"):
            self.log(f"invalid stage {stage!r}; valid: {', '.join(GATES)}, delivery")
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
        @brief      The per-gate conductor loop (design 7a).
        @details    For each remaining gate: mark status, launch the executor
                    for only this gate, inspect (questions? exit code?),
                    verify invariants, then advance / retry with failure
                    context / park / escalate - all bounded by run budgets.
        @param[in]  run The run (stage = where to start/resume).
        @param[in]  ticket Current ticket (for prompts).
        @param[in]  thread Rendered clarification thread ("" outside resume).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-08
        @version    0.2.0
        """
        try:
            self._provision(run)
        except IsolationError as exc:
            self._escalate(run, f"isolation failed: {exc}")
            return
        execute = partial(self.containers.exec, run.container, env=self._container_env(run))
        failure_context = ""
        if run.stage not in GATES:
            # fail closed: silently restarting from intake regressed a
            # delivery-stage run once (live finding 2026-07-04)
            self._escalate(run, f"internal: conduct called with stage {run.stage!r}")
            return
        gate_index = GATES.index(run.stage)
        while gate_index < len(GATES):
            gate = GATES[gate_index]
            run.stage = gate
            budget_reason = self._budget_exceeded(run)
            if budget_reason:
                self._escalate(run, budget_reason)
                return
            self._mark(run, "working", gate)
            run.iterations += 1
            self.store.save(run)
            self.store.journal(run.run_id, "gate-launch", gate=gate,
                               iteration=run.iterations)
            prompt = self._gate_prompt(gate, ticket, failure_context, thread)
            result = self.executor.run_gate(
                execute,
                self.worktrees.path_for(run.run_id),
                self._io_dir(run.run_id),
                prompt,
                session=run.executor_session,
                timeout=self.config.budgets.max_wall_clock_seconds,
                archive_stem=f"{run.iterations:03d}-{gate}",
            )
            run.executor_session = result.session_id or run.executor_session
            self.store.save(run)
            self._journal_artifacts(run, gate, result)
            self._journal_usage(run, gate, result)
            if result.has_questions:
                self._park(run, result.questions)
                return
            if not result.ok:
                failure_context = self._failure_context(
                    run,
                    f"The previous attempt of this gate failed "
                    f"(exit {result.exit_code}). stderr tail:\n"
                    + self._tail_lines(result.stderr, 1500),
                )
                self.store.journal(run.run_id, "gate-failed", gate=gate,
                                   exit_code=result.exit_code)
                continue  # retry same gate, bounded by budgets
            verify = gates.invariants(execute)
            if not verify.ok:
                failure_context = self._failure_context(
                    run,
                    "The gate finished but the workflow invariants check "
                    f"failed (exit {verify.exit_code}):\n"
                    + self._tail_lines(verify.output, 1500),
                )
                self.store.journal(run.run_id, "invariants-failed", gate=gate,
                                   exit_code=verify.exit_code)
                continue  # relaunch same gate with the invariant failure
            if gate == "validation":
                committed = self._work_committed(run)
                if committed:
                    failure_context = committed
                    self.store.journal(run.run_id, "work-uncommitted")
                    continue  # relaunch validation until the work is committed
            failure_context = ""
            self.store.journal(run.run_id, "gate-passed", gate=gate)
            gate_index += 1
            if gate_index < len(GATES):
                run.stage = GATES[gate_index]
                self.store.save(run)
        self.store.journal(run.run_id, "validation-complete")
        self._deliver(run, ticket)

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
        @brief      The delivery sequence: integrate, retest, preflight, push,
                    open the DRAFT MR (design 11a - exact order).
        @details    The orchestrator owns all git plumbing and the remote; the
                    executor is relaunched only for code reasoning (conflict
                    resolution, fixing failed checks), bounded by run budgets.
                    An already-open MR for the branch is adopted, never
                    duplicated (idempotent recovery). Never merges.
        @param[in]  run The run with all development gates green.
        @param[in]  ticket Current ticket.
        @param[in]  thread Rendered clarification/review thread.
        @param[in]  revise True inside the revise cycle: skip MR adoption and
                    update the existing MR instead of creating one.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-08
        @version    0.2.0
        """
        run.stage = "delivery"
        run.lifecycle = "working"
        self.store.save(run)
        self._mark(run, "working", "delivery")
        self.store.journal(run.run_id, "delivery-start")
        try:
            self._provision(run)
            self.worktrees.fetch()
        except IsolationError as exc:
            self._escalate(run, f"delivery isolation failed: {exc}")
            return
        execute = partial(self.containers.exec, run.container, env=self._container_env(run))
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
            if not self._delivery_fix(run, ticket, execute, context, thread):
                return
        self.store.journal(run.run_id, "target-merged", base=run.base_ref)
        # 3. re-run the gates, 4. authoritative preflight - fix loops on both
        preflight_output = ""
        for name, check in (
            ("gates-run", lambda: gates.gates_run(execute)),
            ("delivery-preflight", lambda: gates.delivery_preflight(execute)),
        ):
            while True:
                result = check()
                if result.ok:
                    preflight_output = result.output
                    self.store.journal(run.run_id, f"{name}-passed")
                    break
                context = (
                    self._failure_context(
                        run,
                        f"The {name} check failed (exit {result.exit_code}) after "
                        f"merging {run.base_ref}. Fix the issues, commit your "
                        "changes, and leave a clean tree. Output tail:\n"
                        + self._tail_lines(result.output, 1500),
                    )
                )
                if not self._delivery_fix(run, ticket, execute, context, thread):
                    return
        # Compose the MR body before pushing: the report command can generate
        # `.agentic` artifacts that must be committed with the delivered branch.
        title = f"Resolve #{ticket.iid}: {ticket.title}"
        body = "" if revise and run.mr_iid else self._mr_description(
            run, ticket, execute, preflight_output
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
        execute,
        context: str,
        thread: str = "",
    ) -> bool:
        """
        @brief      One budget-bounded executor relaunch during delivery.
        @param[in]  run The run.
        @param[in]  ticket Current ticket.
        @param[in]  execute Exec seam bound to the run's container.
        @param[in]  context What failed and what to do.
        @return     True to re-check; False when the run ended (escalated or
                    parked).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-08
        @version    0.2.0
        """
        reason = self._budget_exceeded(run)
        if reason:
            self._escalate(run, reason)
            return False
        run.iterations += 1
        self.store.save(run)
        self.store.journal(run.run_id, "delivery-fix", iteration=run.iterations)
        result = self.executor.run_gate(
            execute,
            self.worktrees.path_for(run.run_id),
            self._io_dir(run.run_id),
            self._gate_prompt("validation", ticket, context, thread),
            session=run.executor_session,
            timeout=self.config.budgets.max_wall_clock_seconds,
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
        @date       2026-07-06
        @version    0.1.2
        """
        try:
            mr = self.forge.get_merge_request(run.mr_iid or run.branch)
        except ForgeError as exc:
            self.log(f"{run.run_id}: MR check failed: {exc}")
            return
        if mr is None:
            self.log(f"{run.run_id}: MR {run.mr_iid or run.branch} not found")
            return
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
        @date       2026-07-04
        @version    0.1.0
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
        run.iterations += 1
        self.store.save(run)
        result = self.executor.run_gate(
            execute,
            self.worktrees.path_for(run.run_id),
            self._io_dir(run.run_id),
            self._gate_prompt("revise", ticket, "", thread),
            session=run.executor_session,
            timeout=self.config.budgets.max_wall_clock_seconds,
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

    def _mr_description(self, run: RunState, ticket: Ticket, execute,
                        preflight_output: str) -> str:
        """
        @brief      Compose the draft MR description (design 11).
        @details    "Related to #N", never an auto-close keyword - closure is
                    the human's call. Includes the workflow report when the
                    CLI provides one, plus the preflight tail and the hidden
                    marker.
        @param[in]  run The run.
        @param[in]  ticket Current ticket.
        @param[in]  execute Exec seam (for the report command).
        @param[in]  preflight_output Captured delivery-preflight output.
        @return     The MR body.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        report = gates.run_workflow_cli(execute, "report", timeout=600)
        parts = [
            f"Related to #{ticket.iid}: {ticket.title}",
            f"Produced by {self.identity.name} (run `{run.run_id}`); all "
            "development gates, invariants, and delivery-preflight passed. "
            "Opened as a DRAFT - review and merge are human decisions.",
        ]
        if report.ok and report.output.strip():
            parts.append("### Workflow report\n```\n"
                         + self._tail_lines(report.output, 2500) + "\n```")
        if preflight_output.strip():
            parts.append("### delivery-preflight\n```\n"
                         + self._tail_lines(preflight_output, 1500) + "\n```")
        parts.append(self.identity.make_marker(run.run_id, "delivery"))
        return "\n\n".join(parts)

    def _failure_context(self, run: RunState, base: str) -> str:
        """
        @brief      Add read-only `.agentic` failure evidence to a fix prompt.
        @details    The workflow CLI often writes the useful failure payload
                    to graph/journal/report files instead of stdout. This
                    helper keeps ADORE deterministic: it only reads existing
                    files from the active `.agentic` run, never invokes
                    workflow commands, and redacts configured executor secret
                    values from the final prompt context.
        @param[in]  run ADORE run whose worktree holds the workflow artifacts.
        @param[in]  base The original exit-code/stdout/stderr failure summary.
        @return     Bounded prompt context for the executor retry.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-08
        @version    0.1.1
        """
        evidence = self._agentic_failure_evidence(run)
        parts = [base.strip()]
        if evidence:
            parts.append(evidence)
        return self._redact_failure_context("\n\n".join(part for part in parts if part))

    def _agentic_failure_evidence(self, run: RunState) -> str:
        """
        @brief      Read prompt-safe failure evidence from the active workflow run.
        @details    Uses the workflow-template file contract:
                    `.agentic/current_run`,
                    `.agentic/runs/<run-id>/graph.json`,
                    `.agentic/runs/<run-id>/journal.jsonl`, and
                    `.agentic/runs/<run-id>/report.md`. Missing files are
                    skipped; malformed files are reported in the prompt so the
                    executor understands that evidence was present but damaged.
        @param[in]  run ADORE run whose worktree is inspected.
        @return     Markdown-ish evidence block, or "" when no evidence exists.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-08
        @version    0.1.1
        """
        worktree = self.worktrees.path_for(run.run_id)
        agentic_root = worktree / ".agentic"
        current_run = self._read_text(agentic_root / "current_run").strip()
        if not current_run:
            return ""
        if not self._safe_agentic_run_id(current_run):
            return (f"Agentic failure evidence unavailable: invalid "
                    f"{_AGENTIC_CURRENT_RUN} value.")

        run_dir = agentic_root / "runs" / current_run
        sections = [f"Agentic failure evidence from `.agentic/runs/{current_run}`:"]
        sections.extend(self._graph_failure_evidence(run_dir / "graph.json"))
        sections.extend(self._journal_failure_evidence(run_dir / "journal.jsonl"))
        sections.extend(self._report_failure_evidence(run_dir / "report.md"))
        if len(sections) == 1:
            return ""
        rendered = "\n".join(sections)
        return self._tail_lines(rendered, _AGENTIC_FAILURE_CONTEXT_LIMIT)

    @staticmethod
    def _safe_agentic_run_id(value: str) -> bool:
        """
        @brief      Whether `.agentic/current_run` names one path segment.
        @param[in]  value Candidate workflow run id.
        @return     True when it cannot escape `.agentic/runs`.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-08
        @version    0.1.0
        """
        return (
            bool(value)
            and value not in {".", ".."}
            and Path(value).name == value
            and "/" not in value
            and "\\" not in value
        )

    def _graph_failure_evidence(self, path: Path) -> list[str]:
        """
        @brief      Extract active failing evidence rows from graph.json.
        @param[in]  path Path to the workflow graph.
        @return     Lines to append to the retry prompt.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-08
        @version    0.1.0
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

    def _journal_failure_evidence(self, path: Path) -> list[str]:
        """
        @brief      Extract recent failed gate.output records from journal.jsonl.
        @param[in]  path Path to the workflow journal.
        @return     Lines to append to the retry prompt.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-08
        @version    0.1.0
        """
        if not path.is_file():
            return []
        try:
            raw_lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return [f"- journal.jsonl: could not read gate output evidence ({exc})."]
        failed: list[dict] = []
        for raw in raw_lines:
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue  # torn journal tail: authority is still graph/state
            if not isinstance(entry, dict) or entry.get("event") != "gate.output":
                continue
            data = entry.get("data")
            if not isinstance(data, dict):
                continue
            try:
                returncode = int(data.get("returncode", 0) or 0)
            except (TypeError, ValueError):
                continue
            if returncode == 0:
                continue
            failed.append(data)
        if not failed:
            return []
        lines = ["- Recent failed gate output:"]
        for item in failed[-_AGENTIC_FAILURE_ITEMS_LIMIT:]:
            lines.append(
                f"  - {item.get('gate') or 'gate'} exit {item.get('returncode')}: "
                f"{self._tail_lines(str(item.get('command') or ''), 500)}"
            )
            if item.get("stdout_tail"):
                lines.append(f"    stdout tail: {self._tail_lines(str(item['stdout_tail']), 700)}")
            if item.get("stderr_tail"):
                lines.append(f"    stderr tail: {self._tail_lines(str(item['stderr_tail']), 700)}")
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
        @param[in]  url MR/PR web URL.
        @return     The number, or None when unparseable.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        match = re.search(r"/(?:merge_requests|pull)/(\d+)", url)
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
        if run.stage == "delivery":
            self._deliver(run, ticket, thread)  # never restart the gates
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
        @date       2026-07-03
        @version    0.1.2
        """
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
                    that have no API key (Setup_And_Credentials.md 3.1). Source
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
        @date       2026-07-06
        @version    0.2.2
        """
        if not self.host_auth_path.is_file():
            self.log(f"{run.run_id}: stage_host_auth on, but {self.host_auth_path} "
                     "is missing; the executor will lack credentials")
            return
        io_dir = self._io_dir(run.run_id)
        io_dir.mkdir(parents=True, exist_ok=True)
        staged = io_dir / "host-auth.json"
        shutil.copy2(self.host_auth_path, staged)
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
        gate: str,
        ticket: Ticket,
        failure_context: str,
        thread: str,
    ) -> str:
        """
        @brief      Compose the bounded, gate-specific executor instruction.
        @param[in]  gate Gate name.
        @param[in]  ticket Ticket for context.
        @param[in]  failure_context Previous-attempt failure summary ("" on
                                    first attempt).
        @param[in]  thread Rendered clarification thread ("" outside resume).
        @return     The prompt text (never enters argv; file protocol).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.1
        """
        parts = [
            "You are the executor for one gate of the agentic development "
            "workflow, launched headless by the ADORE orchestrator in an "
            "isolated git worktree.",
            f"Ticket #{ticket.iid}: {ticket.title}",
            "Ticket description:\n" + ticket.description.strip(),
        ]
        if thread:
            parts.append("Clarification thread so far (newest last):\n" + thread)
        if failure_context:
            parts.append(failure_context)
        parts.append(_GATE_GOALS[gate])
        parts.append(
            "Rules: work only inside this worktree. COMMIT all your changes "
            "locally before finishing the gate (including .agentic records "
            "and new files) - a gate is not complete with a dirty working "
            "tree. NEVER push, open merge/pull requests, or merge - the "
            "orchestrator owns the remote. If you hit blocking questions, "
            f"write them to {self.questions_file} in the worktree root and "
            "stop. Stop at the end of this gate and summarize what you did."
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
