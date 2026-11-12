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
@brief ADORE conductor for AEGIS and unverified direct implementation workflows.
@details ADORE owns forge, isolation, budgets, recovery, approval and remote
         publication. The executor owns every AEGIS task-journal transition;
         direct completion uses conductor-owned durable evidence instead.
         Executor sessions are always fresh, never resumed. Required problem notifications use a
         persisted outbox and a failed write stops code work. ADORE can open
         and update a draft MR/PR but deliberately has no merge operation.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable, Iterator
import contextlib
from copy import deepcopy
from datetime import timedelta
import json
import math
import os
from pathlib import Path
import re
from threading import Event, Thread
import time
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit
from uuid import uuid4

from adore import chatgpt, metrics
from adore.aegis import (
    FULL_STAGES,
    AegisCheck,
    AegisClient,
    AegisError,
    AegisProtocolError,
    AegisTask,
    AegisTaskError,
    AegisTimeoutError,
    allowed_transition,
    evidenced_transition,
    logged_stages,
)
from adore.branding import (
    DEFAULT_QUESTIONS_FILE,
    EXECUTOR_BASE_IMAGE,
    EXECUTOR_NAME,
)
from adore.config import Config, branch_naming_preview, egress_policy, load_config, validate_budgets
from adore.execution import (
    ContainerBackend,
    ExecutionBackend,
    ExecutionRecoveryError,
    PreparationResultError,
    run_preparation_step,
)
from adore.executor.base import Executor, GateRun
from adore.executor.diagnostics import record_diagnostics
from adore.executor.launcher import build_executor
from adore.forge import Comment, Forge, ForgeError, Ticket, build_forge
from adore.identity import AgentIdentity
from adore.isolation import (
    CheckpointConflictError,
    CheckpointProtocolError,
    ContainerManager,
    IsolationError,
    WorktreeManager,
    build_container_env,
)
from adore.local_process import LocalExecutionError, atomic_record, read_record
from adore.pi_providers import CHATGPT, ENDPOINT_KEY_VARIABLE, models_json, secret_names
from adore.polling import PollCadence
from adore.preparation import PreparationError, execution_policy, resolve_plan, validate_plan
from adore.prompts import PromptCatalog
from adore.repository_auth import project_runner
from adore.selection import ineligibility
from adore.state import (
    RunState,
    StateError,
    StateStore,
    content_hash,
    derive_run_id,
    run_id_pattern,
)
from adore.util import (
    ANSI_ESCAPE,
    CommandResult,
    force_rmtree,
    in_quiet_hours,
    iso_to_datetime,
    load_env_file,
    output_tail,
    run_command,
    strict_json_loads,
    utc_now_iso,
)

# CONSTANTS

WORKING_STAGES = tuple(stage for stage in FULL_STAGES if stage != "done")
RESETTABLE_STAGES = (*WORKING_STAGES, "publishing")
ACTIVE_LIFECYCLES = {
    "working", "parked-clarification", "awaiting-approval", "publishing", "in-review",
}
_REDACTIONS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*)(\S+)"),
    re.compile(r"(?i)(token\s*[:=]\s*)(\S+)"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)(\S+)"),
)
_MAX_EVIDENCE = 6000
# Executor stderr shown with NO_STAGE_PROGRESS: the decisive line is usually the last.
_STDERR_TAIL_LINES = 20
_STDERR_TAIL_CHARS = 2000
# Valid only while the single-conductor lock prevents another process from
# reconciling a legitimately long-running stage as abandoned.
_STALE_WORKING_GRACE_SECONDS = 60


class _CheckpointHalted(IsolationError):
    """@brief A checkpoint already recorded a terminal ownership/signaling failure."""


# HELPER FUNCTIONS


def _sanitize(value: Any, limit: int | None = _MAX_EVIDENCE) -> str:
    """@brief Render evidence with common credential forms redacted, keeping its end.
    @param[in] limit Characters kept from the end, or None to keep the whole text.
    """
    text = str(value).replace("\x00", "")
    for pattern in _REDACTIONS:
        text = pattern.sub(r"\1[REDACTED]", text)
    return text if limit is None else text[-limit:]


def _stderr_tail(stderr: str) -> str:
    """@brief Last executor stderr lines without ANSI escapes, bounded for evidence.
    @param[in] stderr Gate stderr as read from the run's io directory.
    @return The last 20 lines within 2000 characters, or "" when stderr is blank.
    """
    return output_tail(stderr, lambda text: _sanitize(text, None),
                       lines=_STDERR_TAIL_LINES, chars=_STDERR_TAIL_CHARS)


def _head_and_tail(text: str, limit: int) -> str:
    """@brief Bound text but keep its first line, which carries the failure sentence.
    @param[in] text Sanitized evidence.
    @param[in] limit Maximum length of the result.
    @return The text when it fits, otherwise its first line, "...", and its end.
    """
    if len(text) <= limit:
        return text
    head = text.split("\n", 1)[0][: limit // 2]
    marker = "\n...\n"
    return head + marker + text[-(limit - len(head) - len(marker)):]


def _valid_direct_duration(seconds: Any) -> bool:
    """@brief Check duration integrity without overflowing on arbitrary JSON integers.
    @param[in] seconds Untrusted execution or saved duration.
    @return True for a nonnegative finite number safe for float-based presentation.
    """
    if type(seconds) not in {int, float}:
        return False
    try:
        return math.isfinite(seconds) and seconds >= 0
    except OverflowError:
        # JSON integers may exceed the float range used by isfinite and formatting.
        return False


def _task_type(ticket: Ticket, config: Config) -> str:
    """@brief Map configured ticket labels to the AEGIS type vocabulary."""
    labels = set(ticket.labels)
    mappings = config.workflow.kind_labels
    fix_labels = {
        label for label, kind in mappings.items() if kind == "fix"
    } | {"bug", "fix", config.labels.selection.type_bug}
    change_labels = {
        label for label, kind in mappings.items() if kind == "change"
    } | {"change"}
    feature_labels = {
        label for label, kind in mappings.items() if kind == "feature"
    }
    if labels & fix_labels:
        return "fix"
    if labels & change_labels:
        return "change"
    if labels & feature_labels:
        return "feature"
    return config.workflow.default_kind


# PUBLIC API


class LockHeldError(RuntimeError):
    """@brief A live or unknown holder owns the single-conductor lock."""


class Orchestrator:
    """
    @brief Deterministic ADORE conductor.
    @details All collaborators are injectable, keeping driver, failure,
             notification, approval and publication behavior testable offline.
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
        backend: ExecutionBackend | None = None,
        chatgpt_token: Callable[[int], str] | None = None,
        on_delete: Callable[[str, Callable[[], None]], None] | None = None,
        prompts: PromptCatalog | None = None,
    ) -> None:
        """
        @brief Wire the conductor from production or fake collaborators.
        @param[in] chatgpt_token Source of a ChatGPT access token valid for the
                   given seconds; by default Pi in a helper container of this
                   project's image refreshes the server's sign-in.
        @param[in] on_delete Optional serialized projection/source deletion boundary.
        @param[in] prompts Shared eager prompt catalog; defaults to loading all resources.
        @exception PromptError A required prompt resource cannot be loaded or validated.
        """
        self.prompts = prompts if prompts is not None else PromptCatalog()
        self.config = config
        self.forge = forge
        self.store = store
        self.worktrees = worktrees
        self.containers = containers
        if backend is None and config.execution.backend == "local":
            from adore.local_execution import LocalBackend

            backend = LocalBackend(config)
        self.backend = backend or ContainerBackend(containers)
        self.executor = executor
        self.secrets = secrets or {}
        self.sleep = sleep
        self.log = log
        self.identity = AgentIdentity(name=config.agent.name, slug=config.agent.slug)
        self.on_delete = on_delete
        self._admission_branches: dict[int, str] = {}
        self.questions_file = config.executor.questions_file or DEFAULT_QUESTIONS_FILE
        self._in_flight_run_id = ""
        self.chatgpt_token = chatgpt_token or (
            lambda seconds: chatgpt.bearer_token(
                chatgpt.helper_for(self.config, self.containers),
                chatgpt.credential_dir(), seconds))

    @classmethod
    def from_config(
        cls,
        config: Config,
        env_file: str | Path = ".env",
        *, cleanup_only: bool = False,
    ) -> Orchestrator:
        """
        @brief      Build the conductor with configured production collaborators.
        @param[in]  config Validated runtime configuration.
        @param[in]  env_file Secret file; direct callers default to cwd `.env`.
        @param[in]  cleanup_only Native controls without current execution/tool identity.
        @return     Production-wired orchestrator.
        """
        prompts = PromptCatalog()
        env = {**load_env_file(env_file), **os.environ}
        secrets = {key: env[key] for key in secret_names(config.executor, config.execution.backend)
                   if env.get(key)}
        backend = None
        if cleanup_only and config.execution.backend == "local":
            from adore.local_execution import LocalBackend

            backend = LocalBackend.for_cleanup(config)
        return cls(
            config=config,
            forge=build_forge(
                config.platform.kind, config.platform.repo,
                runner=project_runner(Path(env_file).parent, config), login=config.platform.login
            ),
            store=StateStore(config.state.store_root, config.agent.slug),
            worktrees=WorktreeManager(
                config.worktree.repo_path, config.worktree.root,
                git_name=config.agent.name, git_email=config.agent.email,
            ),
            containers=ContainerManager(
                config.container.runtime,
                config.container.image,
                config.container.uv_cache_volume,
                config.container.npm_cache_volume,
                run_args=config.container.run_args,
                egress=egress_policy(config),
                selinux_relabel=config.container.selinux_relabel,
            ),
            executor=build_executor(
                config.executor.command,
                config.executor.model,
                config.executor.questions_file,
                provider=config.executor.provider,
                thinking=config.executor.thinking,
                models=models_json(config.executor, ENDPOINT_KEY_VARIABLE in secrets),
                internet=config.executor.internet,
                web_search=config.executor.web.search,
                prompts=prompts,
            ),
            secrets=secrets,
            backend=backend,
            prompts=prompts,
        )

    # Main entries

    def run_loop(self) -> int:
        """@brief Poll forever with the existing lock, jitter and forge backoff."""
        if not self.store.acquire_lock():
            self.log(f"error: another instance holds the lock ({self.store.lock_path})")
            return 1
        cadence = PollCadence()
        try:
            while True:
                failed = None
                if in_quiet_hours(self.config.polling.quiet_hours):
                    self.log("quiet hours: polling paused")
                else:
                    try:
                        self.poll_once(locked=True)
                        failed = False
                    except ForgeError as exc:
                        self.log(f"poll error (platform): {exc}")
                        failed = True
                    except Exception as exc:  # noqa: BLE001 - the loop outlives one pass
                        # One run's unexpected failure must not end the daemon
                        # and strand every other run. An IsolationError from a
                        # checkpoint commit, or a KeyError from an executor
                        # command template carrying an unsupported brace, used
                        # to escape here and kill the process; the next start
                        # then failed the in-flight run as STALE_WORKING.
                        # KeyboardInterrupt is a BaseException and still stops
                        # the loop through the handler below.
                        self.log(f"poll error (unexpected): {_sanitize(exc)}")
                        failed = True
                self.sleep(cadence.next_delay(self.config.polling, failed=failed))
        except KeyboardInterrupt:
            self.log("interrupted; shutting down cleanly")
            return 0
        finally:
            self.store.release_lock()

    def poll_once(self, *, dry_run: bool = False, locked: bool = False,
                  ticket_iid: int | None = None) -> dict[str, Any]:
        """@brief Reconcile work and admit one ticket; explicit admission preserves pause.
        @param[in] ticket_iid Positive manual ticket identity, independent of monitoring.
        @exception ValueError A manual identity is not a positive integer.
        """
        if ticket_iid is not None and (type(ticket_iid) is not int or ticket_iid < 1):
            raise ValueError("manual ticket identity must be a positive integer")
        own_lock = False
        if not dry_run and not locked:
            if not self.store.acquire_lock():
                raise LockHeldError("another instance holds the lock")
            own_lock = True
        summary: dict[str, Any] = {
            "resumed": 0,
            "timed_out": 0,
            "notifications": 0,
            "approved": 0,
            "revised": 0,
            "done": 0,
            "picked": None,
        }
        try:
            if not dry_run:
                self._reconcile_runs(summary)
            if self.store.is_paused() and ticket_iid is None:
                summary["paused"] = True
                return summary
            active = [r for r in self.store.list_runs()
                      if r.lifecycle in {"working", "handoff-pending"}]
            if len(active) >= self.config.polling.max_concurrent_runs:
                summary["at_capacity"] = True
                if ticket_iid is not None:
                    summary["start_reason"] = "at_capacity"
                return summary
            if not dry_run:
                try:
                    self._probe_repository_payload()
                except AegisError as exc:
                    summary["payload_error"] = _sanitize(exc)
                    if ticket_iid is not None:
                        summary["start_reason"] = "workflow_unavailable"
                    self.log(f"AEGIS pre-pick probe failed: {_sanitize(exc)}")
                    return summary
            if ticket_iid is not None:
                ticket = self.forge.get_ticket(ticket_iid)
                if ticket is None or ticket.iid != ticket_iid:
                    summary["start_reason"] = "ticket_unavailable"
                    return summary
                reason = ineligibility(ticket, self.config,
                                       has_run=self.store.exists(self._run_id(ticket.iid)))
                if reason is not None:
                    summary["start_reason"] = reason
                    return summary
            else:
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
        """@brief Stop a run, remove resources, and retain its audit state."""
        try:
            run = self.store.load(run_id)
        except (FileNotFoundError, StateError):
            return False
        self.store.cancel_requested(run_id)
        self._teardown(run, remove_worktree=True)
        run.lifecycle = "failed" if outcome == "failed" else "cancelled"
        run.outcome = outcome
        self.store.save(run)
        self.store.clear_cancel_request(run_id)
        self.store.journal(run_id, "cancelled", outcome=outcome)
        self.store.clear_handoff_request(run_id)
        self._status(run)
        self._record_metrics(run)
        return True

    def delete(self, run_id: str, *, owned_resources: bool = False,
               retain_unpublished: bool = False) -> bool:
        """@brief Delete verified run resources and state; caller holds conductor lock.
        @param[in] run_id Selected stored run.
        @param[in] owned_resources Explicit cleanup authority despite native policy drift.
        @param[in] retain_unpublished Restart-only retention of an unproven occupied old ref.
        @return Whether an unproven remote ref was retained for a fresh generation.
        @exception IsolationError Ownership or cleanup cannot be confirmed; state is retained.
        """
        run = self.store.load(run_id)
        directory = self.store.run_dir(run_id)
        worktree = self.worktrees.path_for(run_id)
        if (run.run_id != run_id or run.lifecycle in {"handed-off", "handoff-pending"}
                or not self._owned_branch(run)
                or run.container != self.identity.container_name(run_id)
                or directory.resolve() != directory.absolute()
                or (run.worktree and Path(run.worktree).resolve() != worktree.resolve())
                or (not run.worktree and worktree.exists())
                or (owned_resources and run.lifecycle not in {"failed", "cancelled"})):
            raise IsolationError("cleanup requires the job's own resources and stopped ownership")
        self.worktrees.verify_removal(run_id, run.branch)
        native = run.execution.get("plan", {}).get("backend") == "local"
        if native:
            resource = run.execution["resource"]
            if not resource:
                control = directory / "local-control"
                if control.exists() or control.is_symlink():
                    raise IsolationError("unrecorded native ownership must be inspected")
            elif (resource["worktree"] != run.worktree
                    or Path(resource["io"]) != self.store.run_dir(run_id) / "io"):
                raise IsolationError("native cleanup paths differ from the saved job")
            elif owned_resources:
                from adore.local_execution import LocalBackend

                backend = (self.backend if isinstance(self.backend, LocalBackend)
                           else LocalBackend.for_cleanup(self.config))
                plan = validate_plan(run.execution["plan"])
                backend.remove_owned(run.container, resource, plan["policy"]["local"])
            else:
                self.backend.remove(run.container, expected=resource)
        else:
            self.containers.release_owned(
                run.container, self.worktrees.repo_path, worktree, directory / "io",
                expected=run.execution.get("resource") or None,
            )
        # No checkpoint is authority to delete a present remote branch.
        retained = False
        if run.checkpoint_remote_commit:
            self.worktrees.remove_remote_branch(
                run.branch, run.checkpoint_remote_commit, self.config.delivery.target_branch
            )
        elif retain_unpublished and self.worktrees.remote_branch_head(run.branch):
            retained = True
        else:
            self.worktrees.remove_remote_branch(
                run.branch, "", self.config.delivery.target_branch, allow_absent=True
            )
        self.worktrees.remove(run_id, delete_branch=run.branch if run.worktree else None)
        metrics.delete_summary(self.config.metrics.db_path, run_id,
                               self.config.metrics.export_jsonl)
        if self.on_delete is not None:
            self.on_delete(run_id, lambda: self.store.delete_run(run_id))
        else:
            self.store.delete_run(run_id)
        return retained

    def restart(self, run_id: str, expected_revision: str) -> dict[str, Any]:
        """@brief Abandon a confirmed failed incarnation and manually admit its ticket.
        @param[in] run_id Stored failed job.
        @param[in] expected_revision SHA-256 of the exact confirmed state bytes.
        @return Normal selected-ticket poll result; caller holds conductor lock.
        @exception IsolationError Changed/nonfailed state or unconfirmed cleanup.
        """
        from hashlib import sha256

        raw = (self.store.run_dir(run_id) / "state.json").read_bytes()
        run = self.store.load(run_id)
        if (not expected_revision or sha256(raw).hexdigest() != expected_revision
                or run.lifecycle != "failed"):
            raise IsolationError("confirmed job changed; refresh Job details before restarting")
        ticket = self.forge.get_ticket(run.ticket_iid)
        if ticket is None or ticket.state != "opened":
            raise IsolationError("restart requires an open ticket")
        base = self._branch_name(run_id, run.ticket_iid)
        if not self._owned_branch(run):
            raise IsolationError("run branch ownership changed")
        head = self.worktrees.remote_branch_head(run.branch)
        if head and run.checkpoint_remote_commit and head != run.checkpoint_remote_commit:
            raise IsolationError("remote run branch changed outside ADORE")
        if (run.worktree and (not head or run.checkpoint_remote_commit)
                and self._valid_admission_branch(run.branch)):
            selected = run.branch
        else:
            selected = self.worktrees.fresh_branch(base, validate=self._valid_admission_branch)
        retained = self.delete(run_id, owned_resources=True, retain_unpublished=True)
        lifecycle = self.config.labels.lifecycle
        self.forge.remove_labels(run.ticket_iid, [lifecycle.failed, lifecycle.working])
        self.forge.add_labels(run.ticket_iid, [lifecycle.ready])
        self._admission_branches[run.ticket_iid] = selected
        try:
            result = self.poll_once(locked=True, ticket_iid=run.ticket_iid)
            if retained:
                result["unproven_branch_retained"] = True
            return result
        finally:
            self._admission_branches.pop(run.ticket_iid, None)

    def retry(self, run_id: str, *, reprepare: bool = False) -> bool:
        """@brief Explicitly re-arm a failed run without erasing history."""
        try:
            run = self.store.load(run_id)
        except (FileNotFoundError, StateError):
            return False
        if run.notification_outbox:
            self.log(f"retry {run_id}: required notification is still pending")
            return False
        if run.lifecycle != "failed":
            self.log(f"retry {run_id}: lifecycle is {run.lifecycle}, not failed")
            return False
        if reprepare:
            record = run.execution
            if (not record or not record["plan"]["selection"]
                    or record["attempts"] >= self.config.execution.preparation_max_attempts):
                self.log(f"retry {run_id}: no recipe or preparation replay limit reached")
                return False
            record["reprepare"] = True
            self.store.journal(
                run_id,
                "operator-reprepare-authorized",
                attempts=record["attempts"],
                note="All steps replay; retained worktree may contain partial effects",
            )
        ticket = self.forge.get_ticket(run.ticket_iid)
        if ticket is None:
            self.log(f"retry {run_id}: ticket #{run.ticket_iid} no longer exists")
            return False
        try:
            self._revalidate_native_retry(run)
        except (IsolationError, PreparationError, OSError, ValueError) as exc:
            self._fail_immediately(run, "RETRY_REVALIDATION_FAILED", exc)
            return True
        if run.stage in {"done", "publishing"} and self._published(run):
            # The candidate already reached review: a later failure returns
            # there with no new validation, approval or AEGIS command.
            run.outcome = ""
            self.store.journal(run_id, "operator-retry", stage="done")
            self._enter_review(run)
            return True
        # An approved candidate waits at done; `reset --to publishing` points
        # retry at the same publication.
        resume_publication = (
            run.stage in {"done", "publishing"}
            and bool(run.validation_evidence)
            and bool(run.approval_presented_at)
        )
        if resume_publication:
            # EVERY fingerprint refuses a dirty tree, including the freshness
            # check just below, so leftover work is committed first.
            try:
                self._settle_worktree(run, "retry")
            except _CheckpointHalted:
                return True
            except IsolationError as exc:
                self._fail_immediately(run, "CHECKPOINT_FAILED", exc)
                return True
            approval_absent = (
                not run.approval_label_removed
                or self.config.delivery.approval_label not in ticket.labels
            )
            approval_ready = self._approval_ready(run, ticket)
            if not approval_ready and not approval_absent:
                # Freshness errors and candidate drift already fail or re-conduct.
                return True
            resume_publication = approval_ready
        run.lifecycle = "working"
        run.outcome = ""
        run.stage_failures = 0
        if not resume_publication:
            run.approval_presented_at = ""
            run.approval_label_removed = False
            if run.stage == "publishing":
                # The pointer has no AEGIS stage: conduct from the closed task.
                run.stage = "done"
        self.store.save(run)
        self.store.journal(run_id, "operator-retry", stage=run.stage)
        if resume_publication:
            self._publish(run, ticket)
        else:
            self._conduct(run, ticket)
        return True

    def _revalidate_native_retry(self, run: RunState) -> None:
        """@brief Reconcile volatile native identity only on an explicit Retry.
        @param[in,out] run Failed job; task, resource, worktree and budgets are retained.
        @exception ExecutionRecoveryError Stable configuration or saved plan changed.
        """
        if self.config.execution.backend != "local" or not run.execution:
            return
        previous = validate_plan(run.execution["plan"])
        try:
            current = resolve_plan(self.config)
        except PreparationError as exc:
            if isinstance(exc.__cause__, LocalExecutionError):
                raise ExecutionRecoveryError(str(exc.__cause__)) from exc
            raise
        policy = deepcopy(previous["policy"])
        if previous["backend"] != "local":
            raise ExecutionRecoveryError("Retry cannot change the job execution backend")
        for key in ("environment_sha256", "executable", "executable_sha256"):
            policy["local"][key] = current["policy"]["local"][key]
        if policy != current["policy"]:
            changed = sorted(key for key in policy if policy[key] != current["policy"].get(key))
            raise ExecutionRecoveryError(
                "Retry execution settings changed: " + ", ".join(changed)
                + "; restore the saved host/account and settings"
            )
        plan_file = self.store.run_dir(run.run_id) / "execution-plan.json"
        saved = validate_plan(read_record(plan_file))
        if saved not in (previous, current):
            raise ExecutionRecoveryError("saved execution plan differs from the job")
        resource = run.execution["resource"]
        if resource:
            self.backend.revalidate_for_retry(run.container, resource, previous["policy"]["local"])
        atomic_record(plan_file, current)
        run.execution["plan"] = current
        self.store.save(run)
        self.store.journal(run.run_id, "native-environment-revalidated",
                           previous=previous["fingerprint"], current=current["fingerprint"],
                           executor=EXECUTOR_NAME)

    def reset(self, run_id: str, stage: str) -> bool:
        """@brief Reset ADORE state only; the executor still owns the journal."""
        if stage not in RESETTABLE_STAGES:
            self.log(f"invalid stage {stage!r}; valid: {', '.join(RESETTABLE_STAGES)}")
            return False
        try:
            run = self.store.load(run_id)
        except (FileNotFoundError, StateError):
            return False
        if run.lifecycle in {"handed-off", "handoff-pending"}:
            self.log("human-owned run cannot be reset for automatic execution")
            return False
        if run.workflow == "direct" and stage not in {"build", "validate", "publishing"}:
            self.log("direct runs can reset only to build, validate or publishing")
            return False
        run.stage = stage
        run.lifecycle = "failed"
        run.stage_failures = 0
        run.outcome = f"reset to {stage}"
        self.store.save(run)
        self.store.journal(run_id, "reset", stage=stage)
        return True

    def cleanup(self) -> dict[str, Any]:
        """
        @brief   Remove this project's resources that no kept run still needs.
        @details Works only on run IDs this project owns (see
                 `_cleanup_run_ids`), so containers, proxies, networks and
                 worktrees of other projects stay even when they share the
                 slug, egress network prefix or worktree root. Active, failed,
                 human-owned and corrupt runs keep their resources, and a
                 proxy or network any other existing executor still derives
                 stays. Without the executor
                 listing no proxy or network is removed.
        @return  Lock outcome, removed resources (sorted) and corrupt run IDs.
        """
        corrupt = self.store.invalid_runs()
        report: dict[str, Any] = {
            "lock_cleared": False,
            "lock_held_by": None,
            "containers_removed": [],
            "proxy_containers_removed": [],
            "egress_networks_removed": [],
            "worktrees_removed": [],
            "corrupt_runs": corrupt,
        }
        if self.store.reclaim_stale_lock():
            report["lock_cleared"] = True
        else:
            lock = self.store.lock_info()
            if lock is not None:
                report["lock_held_by"] = lock.get("pid", "unknown")
        prefix = f"{self.identity.slug}-run-"
        if self.config.execution.backend == "local":
            eligible, _, runs = self._cleanup_run_ids(prefix, set(corrupt), set())
            for run_id in sorted(eligible):
                run = runs.get(run_id)
                if run is None or not run.execution.get("resource"):
                    continue  # Unrecorded native ownership cannot authorize cleanup.
                try:
                    self.backend.remove(run.container, expected=run.execution["resource"])
                    self.worktrees.remove(run_id)
                except IsolationError as exc:
                    self.log(f"{run_id}: local cleanup retained: {_sanitize(exc)}")
                    continue
                report["worktrees_removed"].append(run_id)
            return report
        listed: set[str] | None = None
        with contextlib.suppress(IsolationError):
            listed = set(self.containers.list_executors(prefix))
        eligible, protected, runs = self._cleanup_run_ids(
            prefix, set(corrupt), listed or set()
        )
        native = {run_id for run_id, run in runs.items()
                  if run.execution.get("plan", {}).get("backend") == "local"}
        eligible -= native
        protected |= native

        def executors(run_ids: set[str]) -> set[str]:
            names = {self.identity.container_name(run_id) for run_id in run_ids}
            return names | {
                runs[run_id].container
                for run_id in run_ids
                if run_id in runs and runs[run_id].container
            }

        targets, retained = executors(eligible), executors(protected)
        with contextlib.suppress(IsolationError):
            report["containers_removed"] = sorted(
                self.containers.cleanup_orphan_containers(prefix, targets, retained)
            )
        if listed is not None:
            in_use = retained | (listed - targets)
            with contextlib.suppress(IsolationError):
                report["proxy_containers_removed"] = sorted(
                    self.containers.cleanup_egress_proxies(targets, in_use)
                )
            with contextlib.suppress(IsolationError):
                report["egress_networks_removed"] = sorted(
                    self.containers.cleanup_egress_networks(targets, in_use)
                )
        for run_id in sorted(eligible):
            path = self.worktrees.path_for(run_id)
            if not path.is_dir():
                continue
            with contextlib.suppress(IsolationError):
                self.worktrees.remove(run_id)
            force_rmtree(path)
            if not path.exists():
                report["worktrees_removed"].append(run_id)
        return report

    def _cleanup_run_ids(
        self,
        prefix: str,
        corrupt: set[str],
        executors: set[str],
    ) -> tuple[set[str], set[str], dict[str, RunState]]:
        """
        @brief      Split this project's run IDs into removable and kept ones.
        @details    Owned run IDs are the runs in this project's state store,
                    its corrupt run directories, and names of this project's
                    run-ID form (`run_id_pattern`) found as worktree-root
                    directories or executor containers. Protected ones are
                    active, failed, handed-off, handoff-pending and corrupt
                    runs; every other owned run ID is eligible.
        @param[in]  prefix Executor-container prefix ("<slug>-run-").
        @param[in]  corrupt Run IDs whose persisted state fails to load.
        @param[in]  executors Listed executor container names under `prefix`.
        @return     (eligible run IDs, protected run IDs, loadable runs by ID).
        """
        runs = {run.run_id: run for run in self.store.list_runs()}
        protected = corrupt | {
            run_id for run_id, run in runs.items()
            if run.lifecycle in ACTIVE_LIFECYCLES
            or run.lifecycle in {"failed", "handed-off", "handoff-pending"}
        }
        own_form = run_id_pattern(self.config.platform.kind, self.config.platform.repo)
        owned = set(runs) | corrupt | {
            path.name for path in self.worktrees.list_dirs()
            if own_form.fullmatch(path.name)
        } | {
            name[len(prefix):] for name in executors
            if own_form.fullmatch(name[len(prefix):])
        }
        return owned - protected, protected, runs

    def purge_resources(self) -> dict[str, Any]:
        """
        @brief  Release this project's own run resources before profile deletion.
        @details Touches only resources recorded for runs in this project's
                state store - never a name prefix or the shared worktree root,
                which other projects on the host may use. Human-owned
                (handed-off, handoff-pending) runs keep their container and
                worktree. The caller holds the conductor lock and has checked
                that no run is unfinished.
        @return Report with `containers_removed` (executor containers, each
                with its egress proxy and network), `worktrees_removed` and
                `worktrees_retained`.
        """
        report: dict[str, list[str]] = {
            "containers_removed": [], "worktrees_removed": [], "worktrees_retained": [],
        }
        for run in self.store.list_runs():
            path = self.worktrees.path_for(run.run_id)
            if run.lifecycle in {"handed-off", "handoff-pending"}:
                if path.is_dir():
                    report["worktrees_retained"].append(run.run_id)
                continue
            if (self.config.execution.backend != "local"
                    and run.execution.get("plan", {}).get("backend") == "local"):
                report["worktrees_retained"].append(run.run_id)
                continue
            if self.config.execution.backend == "local":
                try:
                    resource = run.execution.get("resource")
                    if not resource:
                        raise ExecutionRecoveryError("local cleanup identity missing")
                    self.backend.remove(run.container, expected=resource)
                    if path.is_dir():
                        self.worktrees.remove(run.run_id)
                        report["worktrees_removed"].append(run.run_id)
                except IsolationError:
                    report["worktrees_retained"].append(run.run_id)
                continue
            names = {self.identity.container_name(run.run_id)}
            if run.container:
                names.add(run.container)
            for name in sorted(names):
                try:
                    self.backend.remove(name, expected=run.execution.get("resource") or None)
                except IsolationError:
                    continue
                report["containers_removed"].append(name)
            if path.is_dir():
                with contextlib.suppress(IsolationError):
                    self.worktrees.remove(run.run_id)
                force_rmtree(path)
                report["worktrees_removed"].append(run.run_id)
        report["worktrees_retained"].sort()
        return report

    def handoff(self, run_id: str) -> bool:
        """
        @brief Stop at an operator-owned safe boundary and preserve human-owned work.
        @param[in] run_id Existing run selected explicitly by the operator.
        @return True when durable ownership was transferred; False when unsafe.
        @note The caller must hold the conductor lock. Active CLI requests are queued.
        """
        try:
            run = self.store.load(run_id)
        except (FileNotFoundError, StateError):
            return False
        if run.lifecycle == "handed-off":
            if self.store.handoff_requested(run_id):
                self._handoff_notice(run)
            self.store.clear_handoff_request(run_id)
            return True
        if run.lifecycle in {"done", "cancelled"}:
            return False
        self.store.request_handoff(run_id)
        # Pending is durable before stop/checkpoint work. Human ownership is announced
        # only after the container has stopped and every Git mutation has finished.
        run.lifecycle = "handoff-pending"
        run.outcome = "handoff pending; wait before editing local work"
        run.approval_presented_at = ""
        run.approval_label_removed = False
        self.store.save(run)
        try:
            if run.container:
                self.backend.stop(run.container, expected=run.execution.get("resource") or None)
        except IsolationError as exc:
            self.log(f"handoff pending; container stop not verified: {_sanitize(exc)}")
            self.store.journal(run_id, "handoff-pending", evidence=_sanitize(exc))
            return False
        try:
            if not run.worktree or not self.worktrees.exists(run_id):
                raise IsolationError("local worktree unavailable; inspect preserved state")
            if run.workflow == "direct":
                self._consume_summary(run)
            created = self.worktrees.commit_all_if_dirty(
                run_id, f"WIP ADORE human handoff {run.active_task_id or run_id}",
                **({"exclude_paths": self._direct_exchanges()} if run.workflow == "direct" else {}),
            )
            self.store.journal(run_id, "checkpoint", created=created, reason="human handoff")
            self._push_checkpoint(run, handoff=True)
        except IsolationError as exc:
            run.checkpoint_error = _sanitize(exc, 2000)
            self.store.save(run)
        run.lifecycle = "handed-off"
        run.outcome = "human ownership; automatic execution disabled"
        self.store.save(run)
        self.store.journal(run_id, "handed-off", branch=run.branch, worktree=run.worktree,
                           task=run.active_task_id, remote=run.checkpoint_remote_commit,
                           error=run.checkpoint_error)
        self._handoff_notice(run)
        self.store.clear_handoff_request(run_id)
        self._status(run)
        self._record_metrics(run)
        return True

    def _handoff_notice(self, run: RunState) -> None:
        """@brief Persist the takeover instructions without duplicating recovery notifications."""
        if any(item.get("kind") == "human-handoff" for item in run.notification_outbox):
            return
        if any(event.get("event") == "notification-delivered"
               and event.get("kind") == "human-handoff"
               for event in self.store.read_journal(run.run_id)):
            return
        instructions = (
            "This run uses the direct workflow. Read the repository's own instructions "
            "and the retained summary and questions before continuing. "
            if run.workflow == "direct" else
            f"AEGIS task: `{run.active_task_id or 'not created'}`\n\n"
            "Read AGENTS.md, run `python .agentic/aegis.py brief "
            f"{run.active_task_id or 'TASK-<id>'}` and read the full task journal before "
            "continuing. "
        )
        body = (
            f"{self.identity.tag} Human handoff complete. Automatic execution is disabled.\n\n"
            f"Work in progress; delivery is not approved by this handoff.\n\n"
            f"Branch: {self._checkpoint_branch_link(run)}\n"
            f"Remote checkpoint: `{run.checkpoint_remote_commit or 'not verified'}`\n"
            f"Local worktree: `{run.worktree}`\n"
            + instructions
            + "Fetch the branch only when the remote checkpoint is current; local files "
            "and uncommitted changes remain authoritative when publication failed.\n"
            + (f"Recovery limitation: {_sanitize(run.checkpoint_error)}\n"
               if run.checkpoint_error else "")
        )
        self._required_comment(run, "human-handoff", body, force_ticket=True)

    def _handoff_at_boundary(self, run: RunState) -> bool:
        """@brief Consume an exact durable request before any further autonomous work."""
        try:
            requested = self.store.handoff_requested(run.run_id)
        except StateError as exc:
            self._fail_immediately(run, "HANDOFF_REQUEST_INVALID", exc)
            return True
        if requested:
            self.handoff(run.run_id)
        return requested

    # Selection and startup

    @staticmethod
    def _has_payload(root: str | Path) -> bool:
        """@brief Treat every present payload entry as governed, including broken links.
        @exception AegisError Payload presence cannot be observed reliably.
        """
        try:
            (Path(root) / ".agentic/aegis.py").lstat()
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise AegisError(f"cannot inspect AEGIS payload: {exc}") from exc
        return True

    def _probe_repository_payload(self) -> None:
        """@brief Probe present governance only; absence enables the direct workflow."""
        if not self._has_payload(self.config.worktree.repo_path):
            return

        def execute(argv, *, timeout=None):
            return run_command(
                argv,
                cwd=self.config.worktree.repo_path,
                timeout=timeout,
            )

        AegisClient(execute, self.config.workflow.aegis_python).probe()

    def _pick_ticket(self, *, ticket_iid: int | None = None) -> Ticket | None:
        """
        @brief      Select the highest-priority ticket that satisfies readiness.
        @details    The eligibility label is re-checked HERE rather than trusted
                    from the adapter's query. A server that silently drops an
                    unrecognised `labels=` filter answers with its whole open
                    backlog, and this is the boundary where ADORE decides what
                    to act on autonomously - a typo in `[labels.lifecycle]
                    ready` must select nothing, never everything. Gitea 1.25.4
                    was observed doing exactly that (live finding 2026-07-29);
                    GitHub was verified to filter correctly (2026-09-18) and
                    GitLab is unverified, which is precisely why the guard lives
                    here instead of in each adapter.
        @return     The selected ticket, or None when none is eligible.
        """
        labels = self.config.labels
        candidates: list[Ticket] = []
        for ticket in self.forge.list_ready(labels.lifecycle.ready):
            if ticket_iid is not None and ticket.iid != ticket_iid:
                continue
            # The shared rules also confirm the open state, the ready label and
            # the hold/exclude controls the forge filter cannot be trusted with.
            has_run = self.store.exists(self._run_id(ticket.iid))
            if ineligibility(ticket, self.config, has_run=has_run) is not None:
                continue
            candidates.append(ticket)
        order = labels.selection.priority_order()

        def rank(ticket: Ticket) -> tuple[int, int]:
            priority = next(
                (index for index, label in enumerate(order) if label in ticket.labels),
                len(order),
            )
            return priority, ticket.iid

        return min(candidates, key=rank) if candidates else None

    @staticmethod
    def _ticket_snapshot(ticket: Ticket) -> dict[str, Any]:
        """@brief Build the normalized durable ticket snapshot."""
        return {
            "iid": ticket.iid,
            "title": ticket.title,
            "description": ticket.description,
            "labels": ticket.labels,
            "author": ticket.author,
            "web_url": ticket.web_url,
            "snapshotted_at": utc_now_iso(),
        }

    def _refresh_ticket_snapshot(
        self, run: RunState, ticket: Ticket, *, context: str
    ) -> bool:
        """
        @brief      Refresh a changed ticket snapshot and surface the drift.
        @param[in]  run Persisted run whose source ticket was freshly observed.
        @param[in]  ticket Fresh normalized forge ticket.
        @param[in]  context Reconciliation point that observed the change.
        @return     True when title or description changed since the last snapshot.
        """
        fresh_hash = content_hash(ticket.title, ticket.description)
        if fresh_hash == run.content_hash:
            return False
        # Snapshot first: a crash can cause a harmless repeated observation, never
        # a new hash that points at stale ticket content.
        self.store.save_ticket(run.run_id, self._ticket_snapshot(ticket))
        run.content_hash = fresh_hash
        self.store.save(run)
        self.store.journal(
            run.run_id,
            "ticket-content-refreshed",
            context=context,
            note=self.prompts.render("review/ticket-content-changed.md"),
        )
        return True

    def _claim_and_conduct(self, ticket: Ticket) -> None:
        """@brief Persist ticket identity before any isolated code work starts."""
        run_id = self._run_id(ticket.iid)
        branch = self._admission_branches.pop(ticket.iid, None)
        if branch is None:
            branch = self.worktrees.fresh_branch(
                self._branch_name(run_id, ticket.iid), validate=self._valid_admission_branch,
            )
        run = RunState(
            run_id=run_id,
            ticket_iid=ticket.iid,
            stage="frame",
            lifecycle="working",
            content_hash=content_hash(ticket.title, ticket.description),
            aegis_type=_task_type(ticket, self.config),
            branch=branch,
            base_ref=f"origin/{self.config.delivery.target_branch}",
            container=self.identity.container_name(run_id),
        )
        comments = self.forge.list_comments(ticket.iid)
        run.last_seen_comment_id = max((item.id for item in comments), default=None)
        self._allocate_worktree(run)
        run.workflow = "aegis" if self._has_payload(run.worktree) else "direct"
        run.stage = "frame" if run.workflow == "aegis" else "build"
        self.store.save(run)
        self.store.save_ticket(run_id, self._ticket_snapshot(ticket))
        self.store.journal(run_id, "picked", ticket=ticket.iid, title=ticket.title)
        try:
            self.forge.remove_labels(ticket.iid, [self.config.labels.lifecycle.ready])
            self.forge.add_labels(ticket.iid, [self.config.labels.lifecycle.working])
        except ForgeError as exc:
            self._fail_without_notification(run, "FORGE_CLAIM", exc)
            return
        self._conduct(run, ticket)

    @contextlib.contextmanager
    def _conducting(self, run_id: str) -> Iterator[None]:
        """@brief Mark the run driven by this process for stale-run detection."""
        previous = self._in_flight_run_id
        self._in_flight_run_id = run_id
        try:
            yield
        finally:
            self._in_flight_run_id = previous

    def _conduct(self, run: RunState, ticket: Ticket, thread: str = "") -> None:
        """@brief Provision and dispatch the recorded workflow to candidate approval."""
        with self._conducting(run.run_id):
            if not self._refresh_budgets(run):
                return
            try:
                self._transient(run, "provision", lambda: self._provision(run))
            except (IsolationError, ForgeError) as exc:
                if self._cancel_if_requested(run):
                    return
                self._fail_immediately(run, "INFRASTRUCTURE_EXHAUSTED", exc)
                return
            if run.workflow == "direct":
                self._conduct_direct(run, ticket, thread)
                return
            execute = self._execute(run)
            client = AegisClient(
                execute,
                self.config.workflow.aegis_python,
                self._io_dir(run.run_id),
            )
            while run.lifecycle == "working":
                if self._handoff_at_boundary(run) or self._cancel_if_requested(run):
                    return
                try:
                    if run.active_task_id is None:
                        # Probe before task creation: unsupported payloads never consume tickets.
                        probe = client.probe()
                        task_id = client.create_task(ticket.title.strip(), run.aegis_type)
                        run.active_task_id = task_id
                        run.task_ids.append(task_id)
                        self.store.save(run)
                        self.store.journal(
                            run.run_id,
                            "aegis-task-created",
                            task=task_id,
                            version=probe.version,
                            schema=probe.schema,
                        )
                        self._checkpoint(run, f"ADORE create {task_id}")
                    else:
                        client.probe()
                    self._conduct_task(run, ticket, client, thread)
                    return
                except ExecutionRecoveryError as exc:
                    if self._cancel_if_requested(run):
                        return
                    self._fail_immediately(run, "INFRASTRUCTURE_EXHAUSTED", exc)
                    return
                except AegisProtocolError as exc:
                    # Protocol/version/schema/path violations are trust-boundary failures.
                    self._fail_immediately(run, "AEGIS_PROTOCOL", exc)
                    return
                except _CheckpointHalted:
                    return
                except AegisTaskError as exc:
                    self._fail_immediately(run, "AEGIS_FATAL", exc)
                    return
                except AegisTimeoutError as exc:
                    if not self._stage_failure(run, "AEGIS_TIMEOUT", exc):
                        return

    def _direct_exchanges(self) -> tuple[str, ...]:
        """@brief Literal direct-only root summary and configured question paths."""
        return ("ADORE_SUMMARY.md", self.questions_file)

    def _consume_summary(self, run: RunState) -> None:
        """@brief Durably retain sanitized summary text before authorizing owned removal.
        @exception IsolationError A present executor artifact cannot be consumed safely.
        """
        artifact = self.worktrees.read_summary(run.run_id, max_chars=_MAX_EVIDENCE)
        if artifact is not None:
            run.validation_evidence["summary"] = _sanitize(artifact.text)
            self.store.save(run)
            self.worktrees.remove_summary(run.run_id, artifact)

    @staticmethod
    def _direct_completed(run: RunState) -> bool:
        """@brief Only conductor-recorded implementation completion authorizes validate."""
        return run.validation_evidence.get("implementation") == "completed"

    def _conduct_direct(self, run: RunState, ticket: Ticket, thread: str = "") -> None:
        """@brief Conduct fresh bounded implementation attempts, with no AEGIS command.
        @details Validate runs optional independent verification, with bounded fresh
                 fixes; a retained completion marker permits recovery without Pi.
        @param[in,out] run Durable direct run with no AEGIS task bindings.
        @param[in] ticket Current source ticket.
        @param[in] thread Human clarification or review discussion for the next fresh attempt.
        """
        failure_context = ""
        try:
            while run.lifecycle == "working":
                if self._handoff_at_boundary(run) or self._cancel_if_requested(run):
                    return
                if not self._refresh_budgets(run):
                    return
                if (run.stage_failures >= self.config.recovery.max_stage_failures
                        and run.failure_history
                        and run.failure_history[-1]["code"] == "VERIFICATION_FAILED"):
                    self._fail_immediately(run, "VERIFICATION_FAILED",
                                           "verification attempts exhausted")
                    return
                completed = self._direct_completed(run) and run.stage != "build"
                budget = self._budget_exceeded(run, include_launch=not completed)
                if budget:
                    self._fail_immediately(run, "BUDGET_EXHAUSTED", budget)
                    return
                if not completed:
                    run.stage = "build"
                    run.validation_evidence = {
                        key: value for key, value in run.validation_evidence.items()
                        if key in {"summary", "verification", "verification_result"}
                    }
                    run.validation_evidence.setdefault("summary", "")
                    run.candidate_fingerprint = ""
                    run.candidate_base_ref = ""
                    self.store.save(run)
                    self._status(run)
                    if run.lifecycle != "working":
                        return
                    try:
                        before = self.worktrees.worktree_progress_fingerprint(
                            run.run_id, exclude_paths=self._direct_exchanges(),
                        )
                    except IsolationError as exc:
                        self._fail_immediately(run, "WORKTREE_PROGRESS", exc)
                        return
                    result = self._launch_stage(run, ticket, None,
                                                failure_context=failure_context, thread=thread)
                    thread = ""
                    if self._cancel_if_requested(run):
                        return
                    # Recheck exchange path ownership even if a file asks to park.
                    try:
                        after = self.worktrees.worktree_progress_fingerprint(
                            run.run_id, exclude_paths=self._direct_exchanges(),
                        )
                        self._consume_summary(run)
                    except IsolationError as exc:
                        self._fail_immediately(run, "CHECKPOINT_FAILED", exc)
                        return
                    questions_path = Path(run.worktree) / self.questions_file
                    if result.has_questions or questions_path.exists():
                        questions = result.questions or self._read_questions(run)
                        self._park(run, questions)
                        return
                    if not result.ok or result.timed_out:
                        code = "EXECUTOR_TIMEOUT" if result.timed_out else "EXECUTOR_EXIT"
                        evidence = result.stderr or result.output or f"exit {result.exit_code}"
                        if not self._stage_failure(run, code, evidence):
                            return
                        failure_context = _sanitize(evidence)
                        continue
                    if before == after:
                        self._fail_immediately(
                            run, "NO_CHANGES",
                            "Session made no product changes.\n"
                            + run.validation_evidence["summary"],
                        )
                        return
                    budget = self._budget_exceeded(run, include_launch=False)
                    if budget:
                        self._fail_immediately(run, "BUDGET_EXHAUSTED", budget)
                        return
                    run.validation_evidence["implementation"] = "completed"
                    # Persist completion and its recovery stage in one state write:
                    # Retry must not spend another launch after durable success.
                    if self.config.workflow.verify_command:
                        self.store.journal(run.run_id, "stage-advanced", previous="build",
                                           current="validate", stage="validate",
                                           failed_attempts=run.stage_failures)
                        run.stage = "validate"
                        self.store.save(run)
                    else:
                        self._successful_transition(run, "build", "validate")
                self._checkpoint(run, "ADORE direct implementation")
                if not self._integrate_target(run):
                    if run.lifecycle != "working":
                        return
                    run.stage = "build"
                    run.validation_evidence.pop("implementation", None)
                    self.store.save(run)
                    failure_context = self.prompts.render("recovery/integration-conflict.md")
                    continue
                budget = self._budget_exceeded(run, include_launch=False)
                if budget:
                    self._fail_immediately(run, "BUDGET_EXHAUSTED", budget)
                    return
                verified_target = self.worktrees.ref_head(run.base_ref)
                if self.config.workflow.verify_command:
                    if not self._verify_direct(run):
                        if run.lifecycle != "working":
                            return
                        continue
                    budget = self._budget_exceeded(run, include_launch=False)
                    if budget:
                        self._fail_immediately(run, "BUDGET_EXHAUSTED", budget)
                        return
                    self._checkpoint(run, "ADORE direct verification passed")
                else:
                    run.validation_evidence["verification"] = "not configured"
                try:
                    if self.worktrees.ref_head(run.base_ref) != verified_target:
                        raise IsolationError("target changed during direct verification")
                    changed = self.worktrees.changed_files(run.run_id, run.base_ref)
                    if type(changed) is not int or changed < 0:
                        raise IsolationError("invalid changed-file count")
                    run.candidate_fingerprint = self.worktrees.candidate_fingerprint(
                        run.run_id, run.base_ref,
                    )
                    run.candidate_base_ref = self.worktrees.ref_head(run.base_ref)
                except IsolationError as exc:
                    self._fail_immediately(run, "CANDIDATE_FINGERPRINT", exc)
                    return
                run.validation_evidence["changed_files"] = changed
                self._successful_transition(run, run.stage, "done")
                self._present_for_approval(run, ticket)
                return
        except _CheckpointHalted:
            return
        except ExecutionRecoveryError as exc:
            if not self._cancel_if_requested(run):
                self._fail_immediately(run, "INFRASTRUCTURE_EXHAUSTED", exc)
        except StateError as exc:
            self._fail_immediately(run, "VERIFICATION_EVIDENCE", exc)
        except IsolationError as exc:
            self._fail_immediately(run, "CHECKPOINT_FAILED", exc)

    @staticmethod
    def _check_direct_result(result: CommandResult, seconds: float) -> None:
        """@brief Refuse malformed external execution evidence without coercing a pass.
        @param[in] result Untrusted bound backend outcome.
        @param[in] seconds Measured monotonic elapsed time.
        @exception IsolationError Exit, timeout, streams or duration violate the contract.
        """
        if (type(result.exit_code) is not int or type(result.timed_out) is not bool
                or not isinstance(result.stdout, str) or not isinstance(result.stderr, str)
                or not _valid_direct_duration(seconds)):
            raise IsolationError("malformed direct verification execution result")

    def _verify_direct(self, run: RunState) -> bool:
        """@brief Run one bounded independent check and atomically route a failed attempt.
        @param[in,out] run Completed direct implementation at validate.
        @return True only for a strictly typed exit-zero, non-timeout result.
        @exception ExecutionRecoveryError Owned execution or cleanup cannot be confirmed.
        """
        command = self.config.workflow.verify_command
        target = self._execute(run)
        limit = self.config.workflow.stage_timeout_overrides.get(
            "validate", self.config.budgets.per_gate_timeout_seconds,
        )
        started = time.monotonic()
        result = (target.run_verification(command, timeout=limit)
                  if self.config.execution.backend == "local"
                  else target(["sh", "-c", command], timeout=limit))
        seconds = time.monotonic() - started
        try:
            self._check_direct_result(result, seconds)
        except IsolationError as exc:
            self._fail_immediately(run, "VERIFICATION_RESULT", exc)
            return False
        separator = ("\n" if result.stdout and result.stderr
                     and not result.stdout.endswith("\n") else "")
        output = result.stdout + separator + result.stderr
        redact = getattr(target, "redact", lambda text: text)
        status = ("timed out" if result.timed_out else
                  "passed" if result.exit_code == 0 else "failed")
        run.validation_evidence.update(
            verification=status,
            verification_result={
                "command": _sanitize(command), "exit_code": result.exit_code,
                "seconds": seconds, "timed_out": result.timed_out,
                "output": output_tail(output, lambda text: _sanitize(redact(text), None),
                                      lines=200, chars=_MAX_EVIDENCE),
            },
        )
        if status == "passed":
            self.store.save(run)
            return True
        # The next build and retained failure must be one durable write with its count.
        run.stage = "build"
        run.validation_evidence.pop("implementation", None)
        run.candidate_fingerprint = run.candidate_base_ref = ""
        self._stage_failure(run, "VERIFICATION_FAILED", self._direct_failure_context(run),
                            stage="validate")
        return False

    def _conduct_task(
        self, run: RunState, ticket: Ticket, client: AegisClient, thread: str,
    ) -> None:
        """@brief Supervise task work, stopping when checkpoint ownership is lost."""
        try:
            self._conduct_task_impl(run, ticket, client, thread)
        except _CheckpointHalted:
            return

    def _conduct_task_impl(
        self,
        run: RunState,
        ticket: Ticket,
        client: AegisClient,
        thread: str,
    ) -> None:
        """
        @brief      Run fresh, journal-authoritative stage attempts until approval.
        @details    Validate closes the AEGIS task by advancing to done. ADORE
                    verifies that advance itself and presents the candidate. A
                    step that finds the task at done without verification
                    evidence sends it back to validate through one fresh session
                    first; evidence that no longer matches the candidate is
                    checked again with the strict check at done.
        """
        failure_context = ""
        while run.lifecycle == "working":
            if self._handoff_at_boundary(run) or self._cancel_if_requested(run):
                return
            if not self._refresh_budgets(run):
                return
            budget = self._budget_exceeded(run)
            if budget:
                self._fail_immediately(run, "BUDGET_EXHAUSTED", budget)
                return
            try:
                task = self._task(client, run)
            except AegisTaskError as exc:
                if not self._stage_failure(run, "JOURNAL_INVALID", exc):
                    return
                failure_context = _sanitize(exc)
                continue
            run.aegis_path = task.path
            previous = run.stage
            if not self._transition_accepted(run, previous, task):
                return
            if task.stage != previous:
                self._successful_transition(run, previous, task.stage)
                failure_context = ""
            run.stage = task.stage
            self.store.save(run)
            self._status(run)
            if run.lifecycle != "working":
                return
            if task.done:
                if not run.validation_evidence:
                    result = self._launch_stage(
                        run,
                        ticket,
                        task,
                        failure_context=self.prompts.render(
                            "recovery/revalidation-route.md", task_id=task.task_id,
                        ),
                        thread=thread,
                    )
                    thread = ""
                    if self._cancel_if_requested(run):
                        return
                    if result.has_questions:
                        self._park(run, result.questions)
                        return
                    if not result.ok:
                        if not self._stage_failure(
                            run,
                            "REVALIDATION_ROUTE_EXIT",
                            result.stderr or result.output,
                            stage="validate",
                        ):
                            return
                        continue
                    routed = self._task(client, run)
                    if routed.stage != "validate":
                        if not self._stage_failure(
                            run,
                            "REVALIDATION_ROUTE_MISSING",
                            f"task remained at {routed.stage}; expected validate",
                            stage="validate",
                        ):
                            return
                        continue
                    self._checkpoint(
                        run, f"ADORE route {run.active_task_id} to validation"
                    )
                    self._successful_transition(run, "done", "validate")
                    continue
                if self._already_verified(run):
                    self._refresh_deviations(run, task)
                elif not self._strict_verification(run, client):
                    return
                if self._cancel_if_requested(run):
                    return
                self._present_for_approval(run, ticket)
                return
            if task.stage == "validate" and not self._integrate_target(run):
                failure_context = self.prompts.render("recovery/integration-conflict.md")
            try:
                progress_before = self.worktrees.worktree_progress_fingerprint(run.run_id)
            except IsolationError as exc:
                self._fail_immediately(run, "WORKTREE_PROGRESS", exc)
                return
            result = self._launch_stage(
                run,
                ticket,
                task,
                failure_context=failure_context,
                thread=thread,
            )
            thread = ""
            if self._cancel_if_requested(run):
                return
            if result.has_questions:
                self._park(run, result.questions)
                return
            if not result.ok:
                code = "EXECUTOR_TIMEOUT" if result.timed_out else "EXECUTOR_EXIT"
                evidence = result.stderr or result.output or f"exit {result.exit_code}"
                if not self._stage_failure(run, code, evidence):
                    return
                failure_context = _sanitize(evidence)
                continue
            try:
                updated = self._task(client, run)
            except AegisError as exc:
                if not self._stage_failure(run, "JOURNAL_INVALID", exc):
                    return
                failure_context = _sanitize(exc)
                continue
            if updated.stage == task.stage:
                questions = self._read_questions(run)
                if questions:
                    self._park(run, questions)
                    return
                try:
                    progress_after = self.worktrees.worktree_progress_fingerprint(run.run_id)
                except IsolationError as exc:
                    self._fail_immediately(run, "WORKTREE_PROGRESS", exc)
                    return
                added = updated.log[len(task.log):]
                if (progress_before != progress_after and added
                        and updated.log[:len(task.log)] == task.log
                        and all(entry.strip() for entry in added)):
                    self._checkpoint(
                        run, f"ADORE continue {run.active_task_id} {task.stage}"
                    )
                    self.store.journal(
                        run.run_id, "stage-continuation", stage=task.stage,
                        iteration=run.iterations, failed_attempts=run.stage_failures,
                        evidence=_sanitize("\n".join(added)),
                    )
                    failure_context = self.prompts.render(
                        "recovery/continuation.md", task_id=task.task_id,
                        evidence=_sanitize("\n".join(added)),
                    )
                    continue
                evidence = f"executor exited zero but AEGIS remained at {task.stage}"
                tail = _stderr_tail(result.stderr)
                if tail:
                    evidence += "\nExecutor stderr (last lines):\n" + tail
                if not self._stage_failure(run, "NO_STAGE_PROGRESS", evidence):
                    return
                failure_context = self.prompts.render("recovery/no-progress.md")
                continue
            if not self._transition_accepted(run, task.stage, updated):
                return
            # A validated journal transition is authoritative before Git work:
            # reads and any checkpoint failure must show the stage actually reached.
            run.aegis_path = updated.path
            self._successful_transition(run, task.stage, updated.stage)
            failure_context = ""
            try:
                self._checkpoint(run, f"ADORE checkpoint {run.active_task_id} {task.stage}")
            except _CheckpointHalted:
                return
            except IsolationError as exc:
                self._fail_immediately(run, "CHECKPOINT_FAILED", exc)
                return
            if (
                task.stage == "validate"
                and updated.done
                and not self._strict_verification(run, client)
            ):
                return

    def _transition_accepted(
        self, run: RunState, previous: str, task: AegisTask
    ) -> bool:
        """
        @brief      Rule on one executor-authored stage transition.
        @details    A documented transition passes. A forward JUMP is accepted
                    only when the durable journal carries a Log entry for every
                    stage it crossed, which separates an executor that ran the
                    whole task in one session - a contract deviation, with the
                    work actually done - from one that skipped stages, which
                    stays refused. Refusing both discarded completed, correct
                    work and produced a run `adore retry` could not clear,
                    because it replayed the same refusal (live finding
                    2026-09-18, GitHub pilot).

                    The deviation is recorded, never silently accepted, and the
                    terminal message for a genuine skip names the reset command
                    that clears it, since retry cannot.
        @param[in]  run The run being conducted.
        @param[in]  previous The stage ADORE last recorded.
        @param[in]  task The task document the journal now reports.
        @return     True when conduction may continue.
        """
        if allowed_transition(previous, task.stage, task.path):
            return True
        if evidenced_transition(previous, task.stage, task.path, task.log):
            self.store.journal(
                run.run_id,
                "stages-run-ahead",
                previous=previous,
                current=task.stage,
                path=task.path,
                crossed=sorted(logged_stages(task.log)),
            )
            self.log(
                f"{run.run_id}: executor ran {previous} -> {task.stage} in one "
                "session; the journal evidences every stage it crossed"
            )
            return True
        self._fail_immediately(
            run,
            "FORBIDDEN_STAGE_TRANSITION",
            f"AEGIS moved {previous} -> {task.stage} on {task.path} without a "
            f"journal entry for every stage crossed. `adore retry` will repeat "
            f"this refusal; inspect the journal, then clear it with "
            f"`adore reset {run.run_id} --to <stage> --force`.",
        )
        return False

    def _task(self, client: AegisClient, run: RunState) -> AegisTask:
        """@brief Read and bind the active AEGIS task to immutable run identity."""
        if run.active_task_id is None:
            raise AegisProtocolError("run has no active AEGIS task")
        task = client.task_status(run.active_task_id)
        if task.branch != run.branch:
            raise AegisProtocolError(
                f"AEGIS task branch {task.branch!r} does not match {run.branch!r}"
            )
        if task.task_type != run.aegis_type:
            raise AegisProtocolError(
                f"AEGIS task type {task.task_type!r} does not match {run.aegis_type!r}"
            )
        return task

    def _launch_stage(
        self,
        run: RunState,
        ticket: Ticket,
        task: AegisTask | None,
        *,
        failure_context: str = "",
        thread: str = "",
    ) -> GateRun:
        """@brief Launch exactly one fresh executor session for one attempt."""
        if self._handoff_at_boundary(run):
            raise _CheckpointHalted("human handoff requested")
        run.iterations += 1
        self.store.save(run)
        self.store.journal(
            run.run_id,
            "stage-launch",
            stage=run.stage,
            attempt=run.stage_failures + 1,
            task=run.active_task_id,
        )
        timeout = self.config.workflow.stage_timeout_overrides.get(
            run.stage, self.config.budgets.per_gate_timeout_seconds
        )
        execute = self._execute(run)
        if self.config.executor.provider == CHATGPT:
            # The server's ChatGPT sign-in never enters the container: this gate
            # alone receives an access token that outlives the stage limit.
            try:
                token = self.chatgpt_token(timeout + chatgpt.TOKEN_MARGIN_SECONDS)
            except chatgpt.ChatGptError as exc:
                self.log(f"{run.run_id}: ChatGPT token unavailable ({exc.code})")
                return GateRun(exit_code=1, stderr=f"ChatGPT sign-in: {exc.sentence()}")
            execute = self.backend.bind(
                run.container, {**self._container_env(run), chatgpt.TOKEN_VARIABLE: token},
                run.execution.get("resource") or None, secrets=(token,))
        # An executor that watches the cancel marker itself (Pi over RPC sends
        # `abort`) gets that grace before the container is stopped underneath it.
        grace_of = getattr(self.executor, "cancel_grace_seconds", None)
        cancel_grace = grace_of(execute) if grace_of is not None else None
        watch_done = Event()
        watcher: Thread | None = None
        if run.lifecycle == "working":
            def interrupt_on_cancel() -> None:
                """@brief Stop only this run's gate when its marker appears."""
                while not watch_done.wait(0.2):
                    try:
                        if not self.store.cancel_requested(run.run_id):
                            continue
                        if cancel_grace is not None and watch_done.wait(cancel_grace):
                            return
                        self.backend.interrupt(
                            run.container, expected=run.execution.get("resource") or None
                        )
                    except (StateError, IsolationError) as exc:
                        self.log(f"cancel interruption failed: {_sanitize(exc)}")
                    return

            watcher = Thread(target=interrupt_on_cancel, daemon=True)
            watcher.start()
        options = {} if cancel_grace is None else {"cancel": self._cancel_check(run)}
        try:
            result = self.executor.run_gate(
                execute,
                run.worktree,
                self._io_dir(run.run_id),
                (self._direct_prompt(run, ticket, failure_context, thread) if task is None
                 else self._stage_prompt(run, ticket, task, failure_context, thread)),
                timeout=timeout,
                archive_stem=f"{run.stage}-attempt-{run.stage_failures + 1}",
                **({"package_secrets": {**self.secrets,
                                        **({chatgpt.TOKEN_VARIABLE: token}
                                           if self.config.executor.provider == CHATGPT else {})}}
                   if self.config.container.system_packages else {}),
                **options,
            )
        finally:
            watch_done.set()
            if watcher is not None:
                watcher.join(timeout=21)
        self._journal_usage(run, run.stage, result)
        self._journal_artifacts(run, run.stage, result)
        if self._handoff_at_boundary(run):
            # The executor has exited, so no container writer can race human ownership.
            raise _CheckpointHalted("human handoff requested")
        return result

    def _cancel_check(self, run: RunState) -> Callable[[], bool]:
        """
        @brief      Build the cancel check an executor polls during its gate.
        @details    Same rule as the interrupt watcher: an unreadable marker is
                    logged once and then no longer consulted; the conductor's
                    own check after the gate decides how to proceed.
        @param[in]  run The running run.
        @return     A callable returning True once a cancel was requested.
        """
        broken = Event()

        def requested() -> bool:
            if broken.is_set():
                return False
            try:
                return self.store.cancel_requested(run.run_id)
            except StateError as exc:
                broken.set()
                self.log(f"cancel check failed: {_sanitize(exc)}")
                return False

        return requested

    def _stage_prompt(
        self,
        run: RunState,
        ticket: Ticket,
        task: AegisTask,
        failure_context: str,
        thread: str,
    ) -> str:
        """@brief Compose a stage-bounded prompt without duplicating AEGIS procedure."""
        aegis = "python .agentic/aegis.py"
        parts = [
            self.prompts.render("stage/intro.md"),
            self.prompts.render("stage/ticket.md", iid=str(ticket.iid),
                                title=ticket.title, description=ticket.description.strip()),
            self.prompts.render("stage/active-task.md", task_id=task.task_id,
                                stage=task.stage, path=task.path),
            self.prompts.render("stage/instructions.md"),
            self.prompts.render("stage/journal.md"),
            self.prompts.render("stage/autopilot.md"),
            self.prompts.render("stage/completion.md", aegis=aegis, task_id=task.task_id),
            self.prompts.render("stage/single-stage.md"),
        ]
        if task.stage == "frame":
            parts.append(self.prompts.render("stage/frame.md"))
            if self.config.workflow.quick_label in ticket.labels:
                parts.append(self.prompts.render(
                    "stage/quick-label.md", quick_label=self.config.workflow.quick_label,
                ))
        if failure_context:
            parts.append(self.prompts.render(
                "stage/recovery-context.md", context=_sanitize(failure_context),
            ))
        if thread:
            parts.append(self.prompts.render("stage/human-thread.md", thread=thread))
        parts.extend(self._execution_notices())
        parts.append(self.prompts.render(
            "stage/closing.md", questions_file=self.questions_file,
            aegis=aegis, task_id=task.task_id,
        ))
        return "\n\n".join(parts)

    def _execution_notices(self) -> list[str]:
        """@brief Preserve the shared container permission/network paragraph byte-for-byte."""
        if self.config.execution.backend != "container":
            return []
        permission = self.prompts.render(
            "stage/packages-enabled.md" if self.config.container.system_packages
            else "stage/packages-disabled.md",
        )
        return [permission + self.prompts.render(
            "stage/network.md", mode=egress_policy(self.config).mode,
        )]

    def _direct_prompt(
        self, run: RunState, ticket: Ticket, failure_context: str, thread: str,
    ) -> str:
        """@brief Compose a complete direct implementation request using literal ticket data.
        @param[in] run Run identity retained at the shared launch boundary.
        @param[in] ticket Ticket title and description, never parsed as templates.
        @param[in] failure_context Sanitized evidence from the preceding failed attempt.
        @param[in] thread Human discussion passed to this fresh session.
        @return The implementation request and applicable execution notices.
        """
        parts = [
            self.prompts.render("direct/implementation.md", questions_file=self.questions_file),
            self.prompts.render("stage/ticket.md", iid=str(ticket.iid), title=ticket.title,
                                description=ticket.description.strip()),
        ]
        if self.config.workflow.verify_command:
            parts.append(self.prompts.render("direct/verification.md",
                                             command=self.config.workflow.verify_command))
            previous = self._direct_result(run)
            if previous and run.validation_evidence["verification"] != "passed":
                parts.append(self._direct_failure_context(run))
        if failure_context:
            parts.append(self.prompts.render("stage/recovery-context.md",
                                             context=_sanitize(failure_context)))
        if thread:
            parts.append(self.prompts.render("stage/human-thread.md", thread=thread))
        parts.extend(self._execution_notices())
        return "\n\n".join(parts)

    def _successful_transition(self, run: RunState, previous: str, current: str) -> None:
        """@brief Reset the per-stage counter only after durable stage progress."""
        self.store.journal(
            run.run_id,
            "stage-advanced",
            previous=previous,
            current=current,
            stage=current,
            failed_attempts=run.stage_failures,
        )
        run.stage_failures = 0
        run.stage = current
        self.store.save(run)

    def _checkpoint(self, run: RunState, message: str) -> None:
        """@brief Create a durable local checkpoint and optionally publish WIP progress."""
        progress = self.config.delivery.publish_checkpoints and run.lifecycle != "publishing"
        if run.workflow == "direct":
            self._consume_summary(run)
        created = self.worktrees.commit_all_if_dirty(
            run.run_id, f"WIP {message}" if progress else message,
            **({"exclude_paths": self._direct_exchanges()} if run.workflow == "direct" else {}),
        )
        self.store.journal(run.run_id, "checkpoint", message=message, created=created)
        if progress:
            self._push_checkpoint(run)

    def _checkpoint_branch_link(self, run: RunState) -> str:
        """@brief Render an adapter-neutral branch link from the trusted ticket snapshot."""
        try:
            snapshot = self.store.load_ticket(run.run_id)
        except (OSError, StateError):
            return f"`{run.branch}`"
        url = str(snapshot.get("web_url", ""))
        parsed = urlsplit(url)
        separator = "/-/issues/" if self.config.platform.kind == "gitlab" else "/issues/"
        if (parsed.scheme in {"http", "https"} and parsed.netloc
                and not parsed.username and not parsed.password and separator in parsed.path):
            project = parsed.path.split(separator, 1)[0]
            route = {"gitlab": "/-/tree/", "github": "/tree/", "gitea": "/src/branch/"}
            link = urlunsplit((parsed.scheme, parsed.netloc,
                              project + route[self.config.platform.kind]
                              + quote(run.branch, safe=""),
                              "", ""))
            return f"[{run.branch}]({link})"
        return f"`{run.branch}`"

    def _push_checkpoint(self, run: RunState, *, handoff: bool = False) -> None:
        """@brief Publish bounded WIP progress; stop on remote ownership loss."""
        if not run.branch or run.branch == self.config.delivery.target_branch:
            error = "checkpoint branch must differ from target"
            if handoff:
                raise CheckpointConflictError(error)
            self._fail_immediately(run, "REMOTE_CHECKPOINT_CONFLICT", error)
            raise _CheckpointHalted(error)
        attempts = self.config.recovery.max_transient_retries
        last = ""
        for index in range(attempts):
            try:
                head = self.worktrees.push_checkpoint(
                    run.run_id, run.branch, run.checkpoint_remote_commit
                )
                run.checkpoint_remote_commit = head
                run.checkpoint_error = ""
                self.store.save(run)
                self.store.journal(run.run_id, "checkpoint-pushed", branch=run.branch,
                                   commit=head, work_in_progress=True)
                return
            except (CheckpointConflictError, CheckpointProtocolError) as exc:
                run.checkpoint_error = _sanitize(exc, 2000)
                self.store.save(run)
                if handoff:
                    raise
                code = ("REMOTE_CHECKPOINT_CONFLICT" if isinstance(exc, CheckpointConflictError)
                        else "REMOTE_CHECKPOINT_PROTOCOL")
                self._fail_immediately(run, code, exc)
                raise _CheckpointHalted("remote checkpoint ownership lost") from exc
            except IsolationError as exc:
                last = _sanitize(exc, 2000)
                if index + 1 < attempts:
                    delays = self.config.recovery.retry_backoff_seconds
                    self.sleep(delays[min(index, len(delays) - 1)])
        changed = run.checkpoint_error != last
        run.checkpoint_error = last
        self.store.save(run)
        self.store.journal(run.run_id, "checkpoint-push-failed", branch=run.branch,
                           remote=run.checkpoint_remote_commit, evidence=last)
        if handoff:
            return
        if changed:
            self._required_comment(run, "checkpoint-push-failed",
                f"{self.identity.tag} Work in progress: remote checkpoint is stale. "
                "Local commits and evidence are preserved. "
                f"Branch: {self._checkpoint_branch_link(run)}. "
                f"Last verified remote commit: `{run.checkpoint_remote_commit or 'none'}`. "
                f"Bounded push attempts failed: {last}", force_ticket=True)
            if run.lifecycle == "failed":
                raise _CheckpointHalted("checkpoint notification failed")

    # Integration, validation, approval and publication

    def _integrate_target(self, run: RunState) -> bool:
        """@brief Fetch and integrate the target before each final validation."""
        try:
            self._transient(run, "git-fetch", self.worktrees.fetch)
            result = self.worktrees.merge(run.run_id, run.base_ref)
        except _CheckpointHalted:
            return False
        except IsolationError as exc:
            self._fail_immediately(run, "GIT_INTEGRATION", exc)
            return False
        if result.ok:
            self._checkpoint(run, f"ADORE integrate {run.base_ref}")
            return True
        evidence = result.stderr or result.stdout or "target merge reported conflicts"
        if not self._stage_failure(run, "INTEGRATION_CONFLICT", evidence):
            return False
        return False

    def _strict_verification(self, run: RunState, client: AegisClient) -> bool:
        """@brief Independently execute and interpret the strict AEGIS verification."""
        try:
            check = client.check(
                run.active_task_id,
                strict=True,
                run=True,
                timeout=self.config.budgets.per_gate_timeout_seconds,
            )
        except AegisProtocolError:
            raise
        except AegisError as exc:
            return self._validation_failure(run, "STRICT_CHECK_INVOCATION", exc)
        executed = check.executed_runs
        valid = (
            check.exit_code == 0
            and check.passed
            and check.errors == 0
            and check.promoted_warnings == 0
            and bool(executed)
            and all(item.status == "ok" and item.exit_code == 0 for item in executed)
        )
        evidence = self._validation_payload(check)
        self.store.journal(run.run_id, "strict-verification", **evidence)
        if not valid:
            return self._validation_failure(run, "STRICT_VERIFICATION_FAILED", evidence)
        try:
            task = self._task(client, run)
        except AegisTaskError as exc:
            return self._validation_failure(run, "JOURNAL_INVALID", exc)
        if not task.done:
            return self._validation_failure(
                run, "STRICT_STAGE_MISMATCH", f"strict pass left task at {task.stage}"
            )
        evidence["deviations"] = list(task.deviations)
        self._checkpoint(run, f"ADORE verified {run.active_task_id}")
        try:
            fingerprint = self.worktrees.candidate_fingerprint(run.run_id, run.base_ref)
            target = self.worktrees.ref_head(run.base_ref)
        except IsolationError as exc:
            self._fail_immediately(run, "CANDIDATE_FINGERPRINT", exc)
            return False
        run.validation_evidence = evidence
        run.candidate_fingerprint = fingerprint
        run.candidate_base_ref = target
        run.stage = "done"
        self.store.save(run)
        return True

    def _refresh_deviations(self, run: RunState, task: AegisTask) -> None:
        """
        @brief      Re-harvest recorded deviations into the stored evidence.
        @details    The conduct loop reads the task again before it presents the
                    candidate, so the approval presentation shows what the
                    journal records at that moment rather than what it recorded
                    when the strict check ran. It costs nothing: the task is
                    already read.
        @param[in]  run The run about to be presented for approval.
        @param[in]  task The task document the conduct loop just read.
        """
        run.validation_evidence["deviations"] = list(task.deviations)
        self.store.save(run)

    def _already_verified(self, run: RunState) -> bool:
        """
        @brief      Whether the exact candidate on disk was already verified.
        @details    The validate -> done transition verifies, and the next pass
                    of the conduct loop reads the task back at done and would
                    verify again. That ran the whole strict catalogue AND every
                    configured command a SECOND time on every successful run -
                    six seconds on a toy repository, a doubled test suite on a
                    real one (live finding 2026-09-18).

                    Re-verification is skipped only when the candidate hashes
                    identically to the one the stored evidence describes, so a
                    tree that moved for any reason is verified again. A
                    fingerprint failure, including a dirty worktree, answers
                    "not verified" and the full check runs.
        @param[in]  run The run sitting at the done stage.
        @return     True when the stored evidence still describes this exact
                    candidate.
        """
        if not run.validation_evidence or not run.candidate_fingerprint:
            return False
        try:
            current = self.worktrees.candidate_fingerprint(run.run_id, run.base_ref)
        except IsolationError:
            return False
        return current == run.candidate_fingerprint

    @staticmethod
    def _validation_payload(check: AegisCheck) -> dict[str, Any]:
        """@brief Persist bounded objective evidence without raw unbounded output."""
        return {
            "exit_code": check.exit_code,
            "passed": check.passed,
            "errors": check.errors,
            "warnings": check.warnings,
            "promoted_warnings": check.promoted_warnings,
            "commands": [
                {
                    "name": item.name,
                    "status": item.status,
                    "exit_code": item.exit_code,
                    "seconds": item.seconds,
                }
                for item in check.runs
            ],
            "findings": [
                {
                    "level": item.level,
                    "check": item.check,
                    "path": item.path,
                    "message": _sanitize(item.message, 1000),
                }
                for item in check.findings[:20]
            ],
        }

    def _validation_failure(self, run: RunState, code: str, evidence: Any) -> bool:
        """@brief Count one strict invocation, regardless of finding count."""
        if not self._stage_failure(run, code, evidence, stage="validate"):
            return False
        run.stage = "validate"
        run.validation_evidence = {}
        run.candidate_fingerprint = ""
        self.store.save(run)
        # The journal may still say done. A fresh remediation launch must
        # return it legally before another validation can pass.
        ticket = self._ticket_from_snapshot(run)
        task_id = run.active_task_id or "TASK-unknown"
        task = AegisTask(
            task_id=task_id,
            title=ticket.title,
            file=f".agentic/tasks/{run.active_task_id}.md",
            header={
                "stage": "done", "type": run.aegis_type, "path": run.aegis_path,
                "requirements": "", "branch": run.branch, "base": "", "opened": "",
            },
            stage="done",
            step_file=None,
            done=True,
            checklist=(),
            log=(),
        )
        result = self._launch_stage(
            run,
            ticket,
            task,
            failure_context=self.prompts.render(
                "recovery/strict-verification.md", task_id=task_id,
                evidence=_sanitize(evidence),
            ),
        )
        if self._cancel_if_requested(run):
            return False
        if result.has_questions:
            self._park(run, result.questions)
            return False
        if not result.ok:
            self._stage_failure(run, "VALIDATION_REMEDIATION_EXIT", result.stderr or result.output)
            return False
        if run.lifecycle == "working":
            execute = self._execute(run)
            self._conduct_task(
                run,
                ticket,
                AegisClient(
                    execute,
                    self.config.workflow.aegis_python,
                    self._io_dir(run.run_id),
                ),
                "",
            )
        return False

    def _present_for_approval(self, run: RunState, ticket: Ticket) -> None:
        """@brief Remove stale approval, present evidence, and release execution capacity."""
        label = self.config.delivery.approval_label
        try:
            self.forge.remove_labels(ticket.iid, [label])
            refreshed = self.forge.get_ticket(ticket.iid)
        except ForgeError as exc:
            self._notification_transport_failure(run, "APPROVAL_LABEL_REMOVE", exc)
            return
        if refreshed is None:
            self._fail_immediately(run, "TICKET_DELETED", "ticket deleted before approval")
            return
        if label in refreshed.labels:
            self._notification_transport_failure(
                run, "APPROVAL_LABEL_STALE", "approval label could not be removed"
            )
            return
        run.approval_label_removed = True
        run.approval_presented_at = utc_now_iso()
        body = self._approval_body(run, ticket)
        comment_id = self._required_comment(run, "approval", body, force_ticket=True)
        if comment_id is None:
            return
        run.approval_comment_id = comment_id
        run.lifecycle = "awaiting-approval"
        self.store.save(run)
        self.store.journal(
            run.run_id,
            "approval-presented",
            fingerprint=run.candidate_fingerprint,
            target=run.candidate_base_ref,
            deviations=len(run.validation_evidence.get("deviations", [])),
        )
        with contextlib.suppress(IsolationError):
            self.backend.stop(run.container, expected=run.execution.get("resource") or None)
        self._status(run)

    def _approval_body(self, run: RunState, ticket: Ticket) -> str:
        """@brief Build the candidate presentation bound to one fingerprint."""
        evidence = run.validation_evidence
        if run.workflow == "direct":
            return (
                (f"{self.identity.tag} Candidate validated for ticket #{ticket.iid}.\n\n"
                 if self._direct_result(run, required=True) else
                 f"{self.identity.tag} Unverified candidate for ticket #{ticket.iid}.\n\n")
                + self._direct_candidate_body(run)
                + "\n\nADORE will never merge it. To approve this exact candidate, freshly add "
                f"`{self.config.delivery.approval_label}` after this presentation. New reviews "
                f"open as {'draft' if self.config.delivery.draft else 'ready for review'}.\n"
                + self.identity.make_marker(run.run_id, "approval",
                                            fingerprint=run.candidate_fingerprint)
            )
        marker = self.identity.make_marker(
            run.run_id, "approval", fingerprint=run.candidate_fingerprint
        )
        commands = evidence.get("commands", [])
        command_lines = "\n".join(
            f"- `{item.get('name')}`: {item.get('status')} (exit {item.get('exit_code')})"
            for item in commands
        ) or "- No command evidence (approval is invalid)."
        try:
            commits = self._commit_list(run)
            diff_files = self.worktrees.changed_files(run.run_id, run.base_ref)
        except IsolationError as exc:
            commits = [f"unavailable: {_sanitize(exc, 500)}"]
            diff_files = -1
        commit_lines = "\n".join(f"- `{item}`" for item in commits) or "- none"
        warnings = int(evidence.get("warnings", 0) or 0)
        deviations = [str(item) for item in evidence.get("deviations", [])]
        deviation_lines = "\n".join(
            f"- {_sanitize(item, 1000)}" for item in deviations
        ) or "- none recorded"
        return (
            f"{self.identity.tag} Candidate validated for ticket #{ticket.iid}.\n\n"
            f"- AEGIS task: `{run.active_task_id}`\n"
            f"- Path: `{run.aegis_path}`\n"
            f"- Strict errors: {evidence.get('errors', '?')}\n"
            f"- Warnings: {warnings}; promoted warnings: "
            f"{evidence.get('promoted_warnings', '?')}\n"
            f"- Changed files: {diff_files}\n"
            f"- Deviations recorded: {len(deviations)}\n"
            f"- Candidate fingerprint: `{run.candidate_fingerprint}`\n"
            f"- Target commit: `{run.candidate_base_ref}`\n\n"
            f"Recorded deviations:\n{deviation_lines}\n\n"
            f"Verification commands:\n{command_lines}\n\n"
            f"Local commit series:\n{commit_lines}\n\n"
            "Intended outcome: push this exact candidate and open/update an MR/PR; "
            f"new reviews open as {'draft' if self.config.delivery.draft else 'ready for review'}. "
            "ADORE will never merge it. To approve, freshly add the "
            f"`{self.config.delivery.approval_label}` label after this presentation.\n"
            f"{marker}"
        )

    def _approval_ready(self, run: RunState, ticket: Ticket) -> bool:
        """@brief Accept only a post-presentation label bound to an unchanged candidate."""
        label = self.config.delivery.approval_label
        if not run.approval_label_removed or not run.approval_presented_at:
            return False
        if label not in ticket.labels:
            return False
        if run.workflow == "direct":
            try:
                ready = self._direct_evidence_ready(run)
            except StateError as exc:
                self._fail_immediately(run, "VERIFICATION_EVIDENCE", exc)
                return False
            if not ready:
                self._invalidate_approval(run, ticket, "direct candidate evidence is incomplete")
                return False
        try:
            self._transient(run, "approval-fetch", self.worktrees.fetch)
            target = self.worktrees.ref_head(run.base_ref)
            fingerprint = self.worktrees.candidate_fingerprint(run.run_id, run.base_ref)
        except IsolationError as exc:
            self._fail_immediately(run, "APPROVAL_FRESHNESS", exc)
            return False
        if target != run.candidate_base_ref or fingerprint != run.candidate_fingerprint:
            self._invalidate_approval(run, ticket, "candidate or target changed after validation")
            return False
        return True

    def _invalidate_approval(self, run: RunState, ticket: Ticket, reason: str) -> None:
        """@brief Clear stale approval and require integration, validation and presentation."""
        try:
            self.forge.remove_labels(ticket.iid, [self.config.delivery.approval_label])
        except ForgeError as exc:
            self._notification_transport_failure(run, "APPROVAL_INVALIDATION", exc)
            return
        run.lifecycle = "working"
        run.stage = "validate"
        run.validation_evidence = (
            {key: value for key, value in run.validation_evidence.items()
             if key in {"summary", "implementation"}}
            if run.workflow == "direct" else {}
        )
        run.candidate_fingerprint = ""
        run.candidate_base_ref = ""
        run.approval_presented_at = ""
        run.approval_label_removed = False
        run.stage_failures = 0
        self.store.save(run)
        self.store.journal(run.run_id, "approval-invalidated", reason=reason)
        self._required_comment(
            run,
            "approval-invalidated",
            f"{self.identity.tag} Approval invalidated: {_sanitize(reason)}. "
            "The target will be integrated and the candidate revalidated before a fresh "
            f"`{self.config.delivery.approval_label}` approval is accepted.\n"
            f"{self.identity.make_marker(run.run_id, 'approval-invalidated')}",
        )
        if run.lifecycle == "working":
            self._conduct(run, ticket)

    def _publish(self, run: RunState, ticket: Ticket) -> None:
        """@brief Publish approved delivery while honoring safe ownership transfer."""
        if self._handoff_at_boundary(run):
            return
        self._publish_impl(run, ticket)

    def _publish_impl(self, run: RunState, ticket: Ticket) -> None:
        """
        @brief      Push the approved candidate and open or adopt its MR/PR.
        @details    Direct adoption/revision refreshes the description before review;
                    a failed write retains publication retry authority, not success.
                    AEGIS 0.15.0 closes the task in validate, so publication is
                    Git and forge work only: no executor session and no AEGIS
                    command runs after the human approved. `_approval_ready`
                    fetched and re-checked the target commit and the candidate
                    fingerprint just before every call, so the pushed branch is
                    exactly the candidate the approval names.
        @param[in]  run The approved run at stage done.
        @param[in]  ticket The source ticket, for the MR/PR title.
        """
        if self._cancel_if_requested(run):
            return
        if run.stage not in {"done", "publishing"}:
            self._fail_immediately(
                run, "PUBLICATION_STAGE",
                f"publication starts from stage done; this run is at {run.stage}",
            )
            return
        if run.workflow == "direct":
            try:
                if not self._direct_evidence_ready(run):
                    raise StateError("direct publication evidence is incomplete")
            except StateError as exc:
                self._fail_immediately(run, "VERIFICATION_EVIDENCE", exc)
                return
        run.lifecycle = "publishing"
        self.store.save(run)
        self._status(run)
        try:
            push = self._push_branch(run)
            if not push.ok:
                self._fail_immediately(run, "PUSH_FAILED", push.stderr or push.stdout)
                return
            existing_review = run.mr_iid is not None
            if run.mr_iid is None:
                mr = self.forge.get_merge_request(run.branch)
                existing_review = mr is not None and mr.state == "opened"
                mr_event = "mr-adopted"
                if mr is not None and mr.state == "opened" and (
                    mr.iid < 1 or not mr.web_url.strip()
                ):
                    raise ForgeError(
                        "existing open MR/PR is missing its iid or URL"
                    )
                if mr is None or mr.state != "opened":
                    self.forge.open_merge_request(
                        run.branch,
                        self.config.delivery.target_branch,
                        ticket.title,
                        self._mr_body(run, ticket),
                        draft=self.config.delivery.draft,
                        reviewers=self.config.delivery.reviewers,
                        remove_source_branch=self.config.delivery.remove_source_branch,
                        cwd=run.worktree,
                    )
                    mr = self.forge.get_merge_request(run.branch)
                    mr_event = "mr-opened"
                if (
                    mr is None
                    or mr.state != "opened"
                    or mr.iid < 1
                    or not mr.web_url.strip()
                ):
                    raise ForgeError("MR/PR was created but could not be read back")
                run.mr_iid = mr.iid
                run.mr_url = mr.web_url
                self.store.journal(
                    run.run_id, mr_event, url=run.mr_url, iid=run.mr_iid
                )
            if run.workflow == "direct" and existing_review:
                # Adoption, revision and interrupted publication all need the
                # current approved evidence, not the branch's previous summary.
                self.forge.update_merge_request_body(run.mr_iid, self._mr_body(run, ticket))
            self.store.save(run)
        except ForgeError as exc:
            self._fail_immediately(run, "MR_CREATE_FAILED", exc)
            return
        except IsolationError as exc:
            self._fail_immediately(run, "PUBLICATION_FAILED", exc)
            return
        self._enter_review(run)

    def _settle_worktree(self, run: RunState, reason: str) -> None:
        """
        @brief      Commit leftover work before a retry fingerprints the candidate.
        @details    EVERY fingerprint refuses a dirty tree, by design: a
                    candidate cannot be hashed mid-edit. `retry` checks approval
                    freshness by fingerprint before it publishes again, and a
                    tree left dirty there once failed terminally on a condition
                    it could have cleared (live finding 2026-09-18, GitHub
                    pilot). Committed leftover work changes the fingerprint, so
                    the freshness check invalidates the approval and the
                    candidate is validated again: settling can never launder an
                    unapproved change into publication.
        @param[in]  run The run whose worktree may carry leftover work.
        @param[in]  reason Short phrase naming the path, used in the message.
        """
        if not run.worktree or not self.worktrees.exists(run.run_id):
            return
        guard = (contextlib.nullcontext() if run.workflow == "direct"
                 else contextlib.suppress(IsolationError))
        with guard:
            if self.worktrees.is_dirty(run.run_id):
                self._checkpoint(
                    run, f"ADORE settle {reason} {run.active_task_id}"
                )

    @staticmethod
    def _published(run: RunState) -> bool:
        """
        @brief      Whether the run's current candidate already reached review.
        @param[in]  run The run being retried.
        @return     True when the verified candidate is the one last published.
        """
        return bool(run.candidate_fingerprint) and (
            run.published_fingerprint == run.candidate_fingerprint
        )

    def _enter_review(self, run: RunState) -> None:
        """@brief Persist the post-publication review state and release execution."""
        run.lifecycle = "in-review"
        run.stage = "done"
        run.stage_failures = 0
        run.published_fingerprint = run.candidate_fingerprint
        self.store.save(run)
        self._status(run)
        with contextlib.suppress(IsolationError):
            self.backend.stop(run.container, expected=run.execution.get("resource") or None)

    def _mr_body(self, run: RunState, ticket: Ticket) -> str:
        """@brief Render a traceable human-review MR/PR description."""
        if run.workflow == "direct":
            return (
                f"Delivery for ticket #{ticket.iid}.\n\n" + self._direct_candidate_body(run)
                + "\n\nThis MR/PR was opened by ADORE "
                "and must be reviewed and merged by a human.\n\n"
                + self.identity.make_marker(run.run_id, "delivery")
            )
        return (
            f"Delivery for ticket #{ticket.iid}.\n\n"
            f"AEGIS task: `{run.active_task_id}`\n\n"
            f"Candidate fingerprint: `{run.candidate_fingerprint}`\n\n"
            "This MR/PR was opened by ADORE and must be reviewed and merged by a human.\n\n"
            f"{self.identity.make_marker(run.run_id, 'delivery')}"
        )

    def _direct_result(self, run: RunState, *, required: bool = False) -> dict | None:
        """@brief Strictly read the one current direct verification evidence shape.
        @param[in] run Saved run whose result may cross into prompts or human approval.
        @param[in] required Require a completed configured or explicit unconfigured result.
        @return Valid configured result, or None for absent/unconfigured evidence.
        @exception StateError Corrupt, mismatched, unbounded or inconsistent saved evidence.
        @note Duration checks refuse integers outside the float range used for display.
              Output sanitation and bounds are checked without trimming: the writer's
              final character cut can expose leading whitespace in a valid retained tail.
        """
        evidence = run.validation_evidence
        result = evidence.get("verification_result")
        command = self.config.workflow.verify_command
        if result is None:
            if required and command:
                raise StateError("direct verification evidence is missing")
            return None
        if (not command or not isinstance(result, dict)
                or set(result) != {"command", "exit_code", "seconds", "timed_out", "output"}
                or not isinstance(result["command"], str) or result["command"] != _sanitize(command)
                or type(result["exit_code"]) is not int or type(result["timed_out"]) is not bool
                or not _valid_direct_duration(result["seconds"])
                or not isinstance(result["output"], str)
                or len(result["output"]) > _MAX_EVIDENCE
                or len(result["output"].splitlines()) > 200
                or "\n".join(result["output"].splitlines()) != result["output"]
                or _sanitize(ANSI_ESCAPE.sub("", result["output"]), None) != result["output"]):
            raise StateError("direct verification evidence is corrupt or mismatched")
        status = ("timed out" if result["timed_out"] else
                  "passed" if result["exit_code"] == 0 else "failed")
        if evidence.get("verification") != status:
            raise StateError("direct verification status disagrees with its result")
        return result

    def _direct_failure_context(self, run: RunState) -> str:
        """@brief Reconstruct fresh-session failure context from the retained typed result."""
        result = self._direct_result(run, required=True)
        if result is None:
            raise StateError("configured verification failure result is missing")
        return self.prompts.render(
            "direct/verification-failure.md", command=result["command"],
            exit_code=str(result["exit_code"]), status=run.validation_evidence["verification"],
            output=result["output"],
        )

    def _direct_evidence_ready(self, run: RunState) -> bool:
        """@brief Summary alone is not completion and can never authorize publication."""
        evidence = run.validation_evidence
        result = self._direct_result(run, required=True)
        return (
            evidence.get("implementation") == "completed"
            and (evidence.get("verification") == "not configured" if result is None
                 else evidence["verification"] == "passed")
            and type(evidence.get("changed_files")) is int and evidence["changed_files"] >= 0
            and bool(run.candidate_fingerprint) and bool(run.candidate_base_ref)
        )

    def _direct_candidate_body(self, run: RunState) -> str:
        """@brief Render typed independent evidence separately from agent-reported checks."""
        evidence = run.validation_evidence
        result = self._direct_result(run, required=True)
        verification = "Verification: not configured. This candidate is unverified."
        if result is not None:
            # Indentation is a literal Markdown block even for embedded backtick fences.
            command = "\n".join("    " + line for line in result["command"].splitlines())
            output = "\n".join("    " + line for line in result["output"].splitlines())
            verification = (f"Verification: {evidence['verification']} "
                            f"(exit {result['exit_code']}, {result['seconds']:.3f} seconds).\n\n"
                            f"Command:\n\n{command}\n\nOutput tail:\n\n{output}")
        return (
            f"Agent summary (including its own checks):\n{evidence.get('summary', '')}\n\n"
            f"Changed files: {evidence.get('changed_files', '?')}\n\n"
            f"{verification}\n\n"
            f"Candidate fingerprint: `{run.candidate_fingerprint}`\n\n"
            f"Target commit: `{run.candidate_base_ref}`"
        )

    def _commit_list(self, run: RunState) -> list[str]:
        """@brief Return the exact ordered local commit series for presentation."""
        return self.worktrees.commit_series(run.run_id, run.base_ref)

    # Fail-loud recovery and required notification outbox

    def _stage_failure(
        self,
        run: RunState,
        code: str,
        evidence: Any,
        *,
        stage: str | None = None,
    ) -> bool:
        """
        @brief Atomically count one failed attempt and publish its incident.
        @return True only when a fresh remediation attempt remains permitted.
        """
        failed_stage = stage or run.stage
        limit = self.config.recovery.max_stage_failures
        run.stage_failures += 1
        attempt = run.stage_failures
        event = {
            "ts": utc_now_iso(),
            "stage": failed_stage,
            "attempt": attempt,
            "limit": limit,
            "code": code,
            "evidence": _sanitize(evidence),
        }
        run.failure_history.append(event)
        self.store.save(run)
        self.store.journal(run.run_id, "stage-failed", **event)
        retry = attempt < limit
        intended = (
            "A fresh executor remediation attempt will be launched."
            if retry else
            "The configured attempt limit is reached; no fourth launch will occur."
        )
        body = (
            f"{self.identity.tag} Problem in stage `{failed_stage}` - attempt "
            f"{attempt}/{limit}.\n\n"
            f"Stable error code: `{code}`\n\n"
            f"Evidence:\n```text\n{_sanitize(evidence)}\n```\n\n"
            f"Next action: {intended}\n"
            f"{self.identity.make_marker(run.run_id, 'incident', stage=failed_stage)}"
        )
        if self._required_incident(run, body) is None:
            return False
        if retry:
            return True
        self._terminal_failure(
            run,
            code,
            f"stage {failed_stage} failed on attempt {attempt}/{limit}: {_sanitize(evidence)}",
        )
        return False

    def _fail_immediately(self, run: RunState, code: str, evidence: Any) -> None:
        """@brief Fail without stage retries for integrity, policy or budget breaches."""
        self.store.journal(
            run.run_id,
            "immediate-failure",
            code=code,
            evidence=_sanitize(evidence),
        )
        self._terminal_failure(run, code, _sanitize(evidence))

    def _terminal_failure(self, run: RunState, code: str, evidence: str) -> None:
        """@brief Enter failed, stop execution, preserve worktree and post separately."""
        run.lifecycle = "failed"
        # Unbounded first: the 6000-character cut would drop the sentence at the start.
        run.outcome = f"{code}: {_head_and_tail(_sanitize(evidence, None), 2000)}"
        self.store.save(run)
        with contextlib.suppress(IsolationError):
            self.backend.stop(run.container, expected=run.execution.get("resource") or None)
        backend = run.execution.get("plan", {}).get("backend", self.config.execution.backend)
        stopped = ("A stop was requested for local execution" if backend == "local"
                   else "A stop was requested for the container")
        body = (
            f"{self.identity.tag} Run `{run.run_id}` failed loudly at stage "
            f"`{run.stage}`.\n\n"
            f"Terminal error code: `{code}`\n\n"
            f"{_sanitize(evidence)}\n\n"
            f"{stopped}, the worktree and evidence are preserved, and the "
            f"execution slot is released. After remediation use Retry in the web interface "
            f"or `adore retry {run.run_id}`.\n"
            f"{self.identity.make_marker(run.run_id, 'terminal-failure', code=code)}"
        )
        self._required_comment(run, "terminal-failure", body)
        self._status(run)
        self._record_metrics(run)
        self.log(f"{run.run_id}: failed loudly ({code})")

    def _fail_without_notification(self, run: RunState, code: str, evidence: Any) -> None:
        """
        @brief Record a failure when the forge was unavailable before claim.
        @details No comment can be posted here - the forge write is what
                 failed - so the run would otherwise fail in silence and the
                 ticket would just sit there still wearing its ready label.
                 The most common cause is a lifecycle label that does not
                 exist in the repository yet, which GitHub and Gitea reject by
                 name, so the reason is logged to stdout and `adore.log`
                 instead of only to the run journal.
        """
        run.lifecycle = "failed"
        run.outcome = f"{code}: {_sanitize(evidence)}"
        self.store.save(run)
        self.store.journal(run.run_id, "failed", code=code, evidence=_sanitize(evidence))
        self.log(
            f"{run.run_id}: failed before claim ({code}); no ticket comment was "
            f"possible: {_sanitize(evidence, 500)}"
        )

    def _notification_transport_failure(
        self, run: RunState, code: str, evidence: Any
    ) -> None:
        """@brief Stop code work when a required forge signaling operation fails."""
        if run.lifecycle not in {"handed-off", "handoff-pending"}:
            run.lifecycle = "failed"
            run.outcome = f"{code}: {_sanitize(evidence)}"
        self.store.save(run)
        self.store.journal(
            run.run_id,
            "notification-blocked",
            code=code,
            evidence=_sanitize(evidence),
        )
        with contextlib.suppress(IsolationError):
            self.backend.stop(run.container, expected=run.execution.get("resource") or None)
        self._record_metrics(run)

    def _required_incident(self, run: RunState, body: str) -> int | None:
        """@brief Create or edit the one marker-owned incident on the active surface."""
        target = "mr" if run.mr_iid is not None else "ticket"
        if run.incident_comment_id is not None and run.incident_target == target:
            return self._required_comment(
                run,
                "incident",
                body,
                edit_id=run.incident_comment_id,
                target=target,
            )
        comment_id = self._required_comment(run, "incident", body, target=target)
        if comment_id is not None:
            run.incident_comment_id = comment_id
            run.incident_target = target
            self.store.save(run)
        return comment_id

    def _required_comment(
        self,
        run: RunState,
        kind: str,
        body: str,
        *,
        edit_id: int | None = None,
        target: str | None = None,
        force_ticket: bool = False,
    ) -> int | None:
        """@brief Persist before write, deliver idempotently, and stop on failure."""
        surface = "ticket" if force_ticket else target or (
            "mr" if run.mr_iid is not None else "ticket"
        )
        resource = run.ticket_iid if surface == "ticket" else run.mr_iid
        if resource is None:
            surface = "ticket"
            resource = run.ticket_iid
        notification_id = uuid4().hex
        marker = self.identity.make_marker(
            run.run_id, kind, notification=notification_id
        )
        if marker not in body:
            body = f"{body.rstrip()}\n{marker}"
        record: dict[str, Any] = {
            "id": notification_id,
            "kind": kind,
            "surface": surface,
            "resource": resource,
            "edit_id": edit_id,
            "body": body,
            "attempts": 0,
            "next_attempt_at": utc_now_iso(),
            "last_error": "",
        }
        run.notification_outbox.append(record)
        self.store.save(run)
        try:
            comment_id = self._deliver_outbox_record(run, record)
        except ForgeError as exc:
            if record.get("undeliverable"):
                run.notification_outbox = [
                    item for item in run.notification_outbox
                    if item.get("id") != record["id"]
                ]
                self.store.save(run)
                self._notification_transport_failure(
                    run, "NOTIFICATION_UNDELIVERABLE", exc
                )
                return None
            record["attempts"] = 1
            record["last_error"] = _sanitize(exc)
            record["next_attempt_at"] = self._next_retry_time(1)
            self.store.save(run)
            self._notification_transport_failure(run, "NOTIFICATION_DELIVERY", exc)
            return None
        if kind == "question":
            run.question_comment_id = comment_id
        run.notification_outbox = [
            item for item in run.notification_outbox if item.get("id") != record["id"]
        ]
        self.store.save(run)
        self.store.journal(
            run.run_id,
            "notification-delivered",
            kind=kind,
            surface=record["surface"],
            resource=record["resource"],
            comment_id=comment_id,
        )
        return comment_id

    def _deliver_outbox_record(self, run: RunState, record: dict[str, Any]) -> int:
        """@brief Execute one already-persisted forge write."""
        surface = record["surface"]
        resource = int(record["resource"])
        edit_id = record.get("edit_id")
        body = str(record["body"])
        if surface == "mr":
            mr = self.forge.get_merge_request(resource)
            if mr is None:
                ticket = self.forge.get_ticket(run.ticket_iid)
                if ticket is None:
                    record["undeliverable"] = True
                    self.store.journal(
                        run.run_id,
                        "notification-undeliverable",
                        notification=record["id"],
                        reason="MR and source ticket are deleted",
                    )
                    raise ForgeError("MR and source ticket are deleted")
                record["surface"] = "ticket"
                record["resource"] = run.ticket_iid
                record["edit_id"] = None
                surface = "ticket"
                resource = run.ticket_iid
                edit_id = None
        if edit_id is None:
            comments = (
                self.forge.list_mr_comments(resource)
                if surface == "mr" else self.forge.list_comments(resource)
            )
            kind = "status-replay" if record["kind"] == "status" else record["kind"]
            marker = self.identity.make_marker(run.run_id, kind, notification=record["id"])
            for comment in comments:
                if any(marker in line for line in comment.body.splitlines()
                       if not line.lstrip().startswith(">")):
                    return comment.id
        if surface == "mr":
            if edit_id is not None:
                self.forge.edit_mr_comment(resource, int(edit_id), body)
                return int(edit_id)
            return self.forge.post_mr_comment(resource, body)
        if edit_id is not None:
            self.forge.edit_comment(resource, int(edit_id), body)
            return int(edit_id)
        return self.forge.post_comment(resource, body)

    def _retry_outbox(self, run: RunState) -> int:
        """@brief Retry due notifications without provisioning or occupying a slot."""
        delivered = 0
        parked_replayed = False
        remaining: list[dict[str, Any]] = []
        for record in run.notification_outbox:
            due = iso_to_datetime(str(record.get("next_attempt_at", "")))
            now = iso_to_datetime(utc_now_iso())
            if due and now and due > now:
                remaining.append(record)
                continue
            try:
                if record.get("kind") == "status":
                    comment_id = self._deliver_status(run, record)
                else:
                    comment_id = self._deliver_outbox_record(run, record)
                if (record.get("kind") == "question" and run.parked_at
                        and (run.lifecycle == "parked-clarification" or
                             (run.lifecycle == "failed" and
                              run.outcome.startswith("NOTIFICATION_DELIVERY:")))):
                    run.question_comment_id = comment_id
                    run.lifecycle = "parked-clarification"
                    run.outcome = ""
                    parked_replayed = True
            except ForgeError as exc:
                if record.get("undeliverable"):
                    continue
                record["attempts"] = int(record.get("attempts", 0)) + 1
                record["last_error"] = _sanitize(exc)
                record["next_attempt_at"] = self._next_retry_time(record["attempts"])
                remaining.append(record)
                continue
            delivered += 1
            self.store.journal(
                run.run_id,
                "notification-replayed",
                notification=record["id"],
                comment_id=comment_id,
            )
        run.notification_outbox = remaining
        self.store.save(run)
        if parked_replayed and self._settle_parked(run):
            self._status(run)
        return delivered

    def _next_retry_time(self, attempt: int) -> str:
        """@brief Calculate capped exponential outbox retry time as ISO UTC."""
        schedule = self.config.recovery.retry_backoff_seconds
        seconds = schedule[min(max(attempt - 1, 0), len(schedule) - 1)]
        now = iso_to_datetime(utc_now_iso())
        if now is None:
            return utc_now_iso()
        return (now + timedelta(seconds=seconds)).isoformat()

    def _push_branch(self, run: RunState) -> CommandResult:
        """
        @brief      Push the run branch, retrying a transient remote failure.
        @details    The push is the most expensive moment in a run to lose: every
                    engineering stage has been paid for and a human has already
                    approved this exact candidate, which a terminal failure
                    discards along with the approval. Every fetch around it
                    already retries through `_transient`; the push did not, so a
                    single "Failed to authenticate user" from a credential
                    refresh ended a fully validated run (live finding
                    2026-09-18, Gitea pilot).

                    Retrying is safe because a push is idempotent in effect: the
                    same refs produce the same remote state. A genuine refusal -
                    a protected branch, a non-fast-forward - fails every attempt
                    and still ends the run loudly, only later. `push` returns its
                    outcome as DATA rather than raising, which is why this cannot
                    reuse `_transient`.
        @param[in]  run The run whose branch to push.
        @return     The last CommandResult, successful or not.
        """
        attempts = max(self.config.recovery.max_transient_retries, 1)
        schedule = self.config.recovery.retry_backoff_seconds
        result = self.worktrees.push(run.run_id, run.branch)
        attempt = 1
        while not result.ok and attempt < attempts:
            self.store.journal(
                run.run_id,
                "transient-failure",
                operation="push",
                attempt=attempt,
                limit=attempts,
                evidence=_sanitize(result.stderr or result.stdout),
            )
            self.sleep(schedule[min(attempt - 1, len(schedule) - 1)])
            result = self.worktrees.push(run.run_id, run.branch)
            attempt += 1
        if result.ok:
            run.checkpoint_remote_commit = self.worktrees.ref_head(run.branch)
            run.checkpoint_error = ""
            self.store.save(run)
        return result

    def _transient(self, run: RunState, operation: str, call: Callable[[], Any]) -> Any:
        """@brief Retry infrastructure independently from the stage-failure counter."""
        attempts = self.config.recovery.max_transient_retries
        schedule = self.config.recovery.retry_backoff_seconds
        last: Exception | None = None
        for index in range(attempts):
            try:
                return call()
            except ExecutionRecoveryError:
                raise
            except (IsolationError, ForgeError) as exc:
                last = exc
                self.store.journal(
                    run.run_id,
                    "transient-failure",
                    operation=operation,
                    attempt=index + 1,
                    limit=attempts,
                    evidence=_sanitize(exc),
                )
                if index + 1 < attempts:
                    self.sleep(schedule[min(index, len(schedule) - 1)])
        if last is None:  # pragma: no cover - validated attempts are positive
            raise RuntimeError(f"transient operation {operation} did not execute")
        raise last

    # Poll reconciliation, clarification and review

    def _reconcile_runs(self, summary: dict[str, Any]) -> None:
        """@brief Give every nonterminal state one bounded next action."""
        for run in self.store.list_runs():
            if self._handoff_at_boundary(run):
                continue
            if run.lifecycle != "publishing" and self._cancel_if_requested(run):
                continue
            if run.lifecycle == "parked-clarification" and not self._settle_parked(run):
                continue
            if run.notification_outbox:
                summary["notifications"] += self._retry_outbox(run)
                run = self.store.load(run.run_id)
                if run.notification_outbox:
                    continue
                if run.lifecycle == "parked-clarification" and not self._settle_parked(run):
                    continue
            if run.lifecycle == "parked-clarification":
                self._reconcile_clarification(run, summary)
            elif run.lifecycle == "awaiting-approval":
                self._reconcile_approval(run, summary)
            elif run.lifecycle == "in-review":
                self._reconcile_review(run, summary)
            elif run.lifecycle == "publishing":
                self._fail_immediately(
                    run,
                    "STALE_PUBLISHING",
                    "publication lost its conductor; inspect remote state before retry",
                )
            elif run.lifecycle == "working" and run.run_id != self._in_flight_run_id:
                self._reconcile_stale_working(run)
            elif (run.lifecycle == "failed" and self.config.delivery.publish_checkpoints
                  and not run.notification_outbox and self.worktrees.exists(run.run_id)
                  and not run.outcome.startswith(("REMOTE_CHECKPOINT_CONFLICT:",
                                                  "REMOTE_CHECKPOINT_PROTOCOL:"))):
                # A rollout or an earlier transport failure may leave committed recovery
                # work local. Publish it without starting an executor or committing dirty files.
                if run.branch and run.checkpoint_remote_commit and not run.checkpoint_error:
                    try:
                        local_head = self.worktrees.ref_head(run.branch)
                    except IsolationError as exc:
                        self.log(f"failed-run checkpoint identity unavailable: {_sanitize(exc)}")
                        continue
                    if local_head == run.checkpoint_remote_commit:
                        continue
                with contextlib.suppress(_CheckpointHalted):
                    self._push_checkpoint(run)
                self._status(run)

    def _cancel_if_requested(self, run: RunState) -> bool:
        """@brief Honor an authorized durable cancellation before more work."""
        if run.lifecycle in ("done", "failed", "cancelled",
                            "handoff-pending", "handed-off"):
            if self.store.cancel_requested(run.run_id):
                self.store.clear_cancel_request(run.run_id)
            return False
        if self.store.cancel_requested(run.run_id):
            self.cancel(run.run_id)
            return True
        return False

    def _reconcile_stale_working(self, run: RunState) -> None:
        """@brief Convert a crashed conductor's stale slot into a visible failure."""
        updated = iso_to_datetime(run.updated_at)
        now = iso_to_datetime(utc_now_iso())
        if updated and now and (now - updated).total_seconds() < _STALE_WORKING_GRACE_SECONDS:
            return
        if run.execution.get("status") == "running":
            run.execution["status"] = "interrupted"
        self._fail_immediately(
            run,
            "STALE_WORKING",
            "working state had no live conductor; explicit retry is required",
        )

    def _cancel_if_ticket_closed(self, run: RunState, ticket: Ticket) -> bool:
        """@brief Cancel through the normal teardown path when the source closes."""
        if ticket.state == "opened":
            return False
        self.cancel(run.run_id, outcome="ticket closed")
        return True

    def _reconcile_approval(self, run: RunState, summary: dict[str, Any]) -> None:
        """@brief Observe fresh approval or deleted resources without using a slot."""
        ticket = self.forge.get_ticket(run.ticket_iid)
        if ticket is None:
            self._fail_immediately(run, "TICKET_DELETED", "ticket deleted during approval")
            return
        if self._cancel_if_ticket_closed(run, ticket):
            return
        self._refresh_ticket_snapshot(run, ticket, context="approval")
        if not self._approval_ready(run, ticket):
            return
        summary["approved"] += 1
        self.store.journal(
            run.run_id,
            "approval-observed",
            label=self.config.delivery.approval_label,
            fingerprint=run.candidate_fingerprint,
        )
        self._publish(run, ticket)

    def _park(self, run: RunState, questions: str) -> None:
        """@brief Post questions, park without consuming the stage counter, and stop."""
        clean = _sanitize(questions)
        run.clarification_rounds += 1
        if run.clarification_rounds > self.config.clarification.max_rounds:
            self._fail_immediately(
                run,
                "CLARIFICATION_LIMIT",
                f"clarification rounds exceeded {self.config.clarification.max_rounds}",
            )
            return
        marker = self.identity.make_marker(
            run.run_id, "question", round=str(run.clarification_rounds)
        )
        body = (
            f"{self.identity.tag} Clarification required for stage `{run.stage}`.\n\n"
            f"{clean}\n\n"
            f"Reply on this ticket and add `{self.config.labels.lifecycle.answered}`. "
            "This question does not consume the stage error budget.\n"
            f"{marker}"
        )
        run.lifecycle = "parked-clarification"
        run.parked_at = utc_now_iso()
        run.parked_polls = 0
        comment_id = self._required_comment(run, "question", body, force_ticket=True)
        if comment_id is None:
            return
        self.store.save(run)
        self.store.journal(run.run_id, "parked", questions=clean)
        if self._settle_parked(run):
            self._status(run)

    def _settle_parked(self, run: RunState) -> bool:
        """@brief Idempotently stop a parked backend and remove its question handoff."""
        # Zero means parking has not yet settled; positive values are persisted
        # only after cleanup, before the regular clarification poll increments.
        if run.parked_polls > 0:
            return True
        try:
            self.backend.stop(run.container, expected=run.execution.get("resource") or None)
            (Path(run.worktree) / self.questions_file).unlink(missing_ok=True)
        except (IsolationError, OSError) as exc:
            run.notification_outbox = [
                item for item in run.notification_outbox if item.get("kind") != "question"
            ]
            self._fail_immediately(
                run, "PARK_CLEANUP_FAILED",
                f"{exc}; clarification is inactive until the run is retried",
            )
            return False
        run.parked_polls = 1
        self.store.save(run)
        return True

    def _reconcile_clarification(self, run: RunState, summary: dict[str, Any]) -> None:
        """@brief Resume from a human answer or fail visibly at its configured timeout."""
        ticket = self.forge.get_ticket(run.ticket_iid)
        if ticket is None:
            self._fail_immediately(run, "TICKET_DELETED", "ticket deleted while parked")
            return
        if self._cancel_if_ticket_closed(run, ticket):
            return
        if self.config.labels.lifecycle.clarify not in ticket.labels:
            self._status(run)
            if run.lifecycle != "parked-clarification":
                return
        comments = self.forge.list_comments(run.ticket_iid)
        answers = [
            item for item in comments
            if not item.system
            and item.id > (run.last_seen_comment_id or 0)
            and not self.identity.is_own_comment(item.body)
        ]
        answered = self.config.labels.lifecycle.answered in ticket.labels
        if answers and answered:
            content_changed = self._refresh_ticket_snapshot(
                run, ticket, context="clarification-resume"
            )
            run.last_seen_comment_id = max(item.id for item in comments)
            run.lifecycle = "working"
            run.parked_at = ""
            run.parked_polls = 0
            self.store.save(run)
            self.store.journal(run.run_id, "resumed")
            with contextlib.suppress(ForgeError):
                self.forge.remove_labels(
                    run.ticket_iid,
                    [self.config.labels.lifecycle.answered, self.config.labels.lifecycle.clarify],
                )
            summary["resumed"] += 1
            thread = self._render_thread(comments)
            if content_changed:
                note = self.prompts.render("review/ticket-content-changed.md")
                thread = f"{thread}\n\n{note}".strip()
            self._conduct(run, ticket, thread)
            return
        run.parked_polls += 1
        parked = iso_to_datetime(run.parked_at)
        now = iso_to_datetime(utc_now_iso())
        timeout_seconds = self.config.clarification.answer_timeout_seconds()
        expired = bool(parked and now and (now - parked).total_seconds() >= timeout_seconds)
        if expired:
            summary["timed_out"] += 1
            self._fail_immediately(
                run,
                "CLARIFICATION_TIMEOUT",
                f"no answer within {self.config.clarification.answer_timeout}",
            )
            return
        self.store.save(run)

    def _reconcile_review(self, run: RunState, summary: dict[str, Any]) -> None:
        """@brief Observe human merge/close or begin one bounded new-task revision."""
        if run.mr_iid is None:
            self._fail_immediately(run, "MR_ID_MISSING", "in-review run has no MR id")
            return
        mr = self.forge.get_merge_request(run.mr_iid)
        if mr is None:
            run.mr_missing_polls += 1
            self.store.save(run)
            if run.mr_missing_polls >= self.config.recovery.max_transient_retries:
                self._fail_immediately(run, "MR_DELETED", "MR/PR was deleted")
            return
        run.mr_missing_polls = 0
        if mr.state == "merged":
            cleanup_error = ""
            if self.config.delivery.remove_source_branch:
                try:
                    if (mr.iid != run.mr_iid
                            or not self._owned_branch(run)):
                        raise IsolationError("run branch or review ownership changed")
                    self._transient(run, "remove-source-branch", lambda: (
                        self.worktrees.remove_remote_branch(
                            run.branch, run.checkpoint_remote_commit,
                            self.config.delivery.target_branch,
                        )
                    ))
                    self.store.journal(run.run_id, "source-branch-removed", branch=run.branch)
                except IsolationError as exc:
                    cleanup_error = _sanitize(exc, 2000)
                    self.store.journal(
                        run.run_id, "source-branch-retained", branch=run.branch,
                        evidence=cleanup_error,
                    )
            run.lifecycle = "done"
            run.outcome = "merged by human"
            if cleanup_error:
                run.outcome += f"; branch retained: {cleanup_error}"
            self.store.save(run)
            self.store.journal(run.run_id, "done", outcome=run.outcome)
            self._status(run)
            self._record_metrics(run)
            self._teardown(run, remove_worktree=not cleanup_error)
            summary["done"] += 1
            return
        if mr.state == "closed":
            self._fail_immediately(run, "MR_CLOSED", "MR/PR closed without merge")
            return
        ticket = self.forge.get_ticket(run.ticket_iid)
        if ticket is None:
            self._fail_immediately(run, "TICKET_DELETED", "source ticket deleted in review")
            return
        if self._cancel_if_ticket_closed(run, ticket):
            return
        # Two triggers feed ONE governed revision path. An explicit human
        # request wins over an inferred one, so the label is checked first.
        requested = self.config.review.revise_label in mr.labels
        observed = self._observe_pipeline(run)
        pipeline_failed = observed == "failed"
        auto_repair = (
            pipeline_failed
            and not requested
            and self.config.review.on_pipeline_failure == "revise"
            and run.review_rounds < self.config.review.max_review_rounds
        )
        if pipeline_failed and not auto_repair and not requested:
            # Either the mode is notify/ignore, or the round budget is spent:
            # say so on the MR and leave the run for a human.
            self._notify_pipeline_failure(run)
            self.store.save(run)
            return
        if not requested and not auto_repair:
            self.store.save(run)
            return
        if run.review_rounds >= self.config.review.max_review_rounds:
            self._fail_immediately(
                run,
                "REVIEW_LIMIT",
                f"review rounds exceeded {self.config.review.max_review_rounds}",
            )
            return
        try:
            comments = self.forge.list_mr_comments(run.mr_iid)
            self._transient(run, "revision-provision", lambda: self._provision(run))
            task_id = None
            if run.workflow == "aegis":
                execute = self._execute(run)
                client = AegisClient(
                    execute,
                    self.config.workflow.aegis_python,
                    self._io_dir(run.run_id),
                )
                client.probe()
                task_id = client.create_task(
                    f"Review round {run.review_rounds + 1}: {ticket.title}", "change"
                )
        except (ForgeError, IsolationError, AegisError) as exc:
            self._fail_immediately(run, "REVIEW_START_FAILED", exc)
            return
        self.store.journal(
            run.run_id,
            "revision-task-created",
            round=run.review_rounds + 1,
            task=task_id,
        )
        if requested:
            try:
                self.forge.remove_mr_labels(
                    run.mr_iid, [self.config.review.revise_label]
                )
            except ForgeError as exc:
                self._notification_transport_failure(run, "REVISE_LABEL_REMOVE", exc)
                return
        run.review_rounds += 1
        run.active_task_id = task_id
        if task_id is not None:
            run.task_ids.append(task_id)
            run.aegis_type = "change"
            run.aegis_path = "full"
        run.stage = "build" if run.workflow == "direct" else "frame"
        run.stage_failures = 0
        run.validation_evidence = {}
        run.candidate_fingerprint = ""
        run.candidate_base_ref = ""
        run.approval_presented_at = ""
        run.approval_label_removed = False
        run.lifecycle = "working"
        # Clear the surfaced verdict: this revision produces new commits and so
        # a new pipeline run, whose result must be observed afresh.
        run.pipeline_reported = ""
        self.store.save(run)
        self.store.journal(
            run.run_id,
            "revision-started",
            round=run.review_rounds,
            task=task_id,
            trigger="revise-label" if requested else "pipeline-failed",
        )
        self._checkpoint(run, f"ADORE create revision {task_id}")
        summary["revised"] += 1
        thread = self._render_thread(comments)
        if auto_repair:
            thread = "\n\n".join(part for part in (self._pipeline_brief(), thread) if part)
            self._announce_pipeline_repair(run)
        self._conduct(run, ticket, thread)

    def _announce_pipeline_repair(self, run: RunState) -> None:
        """
        @brief      Say on the draft that an automatic repair round has begun.
        @details    Nobody asked for this round, so without a notice a reviewer
                    watching the MR/PR sees commits arrive with no explanation.
                    The ticket's status comment moves back to `working`, but
                    that is the wrong surface for someone following the draft.
                    Best-effort: losing the notice must not stop the repair.
        @param[in]  run The run whose repair round is starting.
        """
        if run.mr_iid is None:
            return
        rounds = self.config.review.max_review_rounds
        marker = self.identity.make_marker(
            run.run_id, "pipeline-repair", round=str(run.review_rounds)
        )
        body = (
            f"{self.identity.tag} The forge pipeline reported `failed`, so ADORE "
            f"started an automatic repair round ({run.review_rounds}/{rounds}).\n\n"
            "New commits will appear on this branch once the work passes strict "
            "validation and a human re-approves the candidate on the source "
            "ticket. ADORE still never merges. Set "
            "`[review] on_pipeline_failure = \"notify\"` to be asked first "
            f"instead.\n{marker}"
        )
        with contextlib.suppress(ForgeError):
            self.forge.post_mr_comment(run.mr_iid, body)

    def _pipeline_brief(self) -> str:
        """
        @brief   The instruction handed to an executor revising a red pipeline.
        @details ADORE cannot read job logs through the platform CLIs it wraps,
                 so the executor is pointed at the repository's own CI
                 definition and told to reproduce the failure in the container
                 rather than being handed a summary that might be stale.
        @return  Thread text prepended to the review discussion.
        """
        return self.prompts.render("review/pipeline.md")

    def _observe_pipeline(self, run: RunState) -> str:
        """
        @brief      Read the draft's pipeline verdict, reporting only a CHANGE.
        @details    Returns "" unless the verdict is new, because a run can sit
                    in review for days: acting on the current value every poll
                    would nag the reviewer, and would restart a repair round on
                    a failure already being repaired. The read is best-effort -
                    an in-review run is doing no code work, so a forge hiccup
                    on advisory information must not disturb it - and "unknown"
                    or "none" never become a signal.

                    `[review] on_pipeline_failure = "ignore"` skips the read
                    entirely, so a repository with no CI pays nothing.
        @param[in]  run The in-review run whose MR/PR to inspect.
        @return     The newly observed PIPELINE_STATES value, or "" when the
                    verdict is unchanged, unreadable, or not applicable.
        """
        if run.mr_iid is None or self.config.review.on_pipeline_failure == "ignore":
            return ""
        try:
            status = self.forge.pipeline_status(run.mr_iid)
        except ForgeError as exc:  # an adapter is contracted not to raise here
            self.log(f"{run.run_id}: pipeline status unavailable: {_sanitize(exc, 300)}")
            return ""
        if status in {"unknown", "none"} or status == run.pipeline_reported:
            return ""
        run.pipeline_reported = status
        self.store.save(run)
        self.store.journal(
            run.run_id, "pipeline-observed", status=status, mr=run.mr_iid
        )
        return status

    def _notify_pipeline_failure(self, run: RunState) -> None:
        """
        @brief      Post the one-time red-pipeline notice and take no action.
        @details    Used when automatic repair is off, or when the review-round
                    budget is already spent. ADORE never merges, so the run
                    simply stays in review for a human. Best-effort: losing an
                    advisory comment must not fail a run that is doing no work.
        @param[in]  run The in-review run whose MR/PR reported failure.
        """
        if run.mr_iid is None:
            return
        rounds = self.config.review.max_review_rounds
        exhausted = run.review_rounds >= rounds
        next_step = (
            f"The review-round budget is spent ({run.review_rounds}/{rounds}), so "
            "no further automatic repair will run."
            if exhausted else
            "Automatic repair is off for this profile "
            f"(`[review] on_pipeline_failure`). To request a governed revision, "
            f"add `{self.config.review.revise_label}`."
        )
        body = (
            f"{self.identity.tag} The forge pipeline on this MR/PR reports "
            f"`failed`.\n\n{next_step} ADORE never merges, so this run stays in "
            "review until a human merges it, closes it, or closes the source "
            "ticket.\n"
            f"{self.identity.make_marker(run.run_id, 'pipeline', status='failed')}"
        )
        with contextlib.suppress(ForgeError):
            self.forge.post_mr_comment(run.mr_iid, body)

    @staticmethod
    def _render_thread(comments: list[Comment], limit: int = 20) -> str:
        """@brief Render the newest bounded non-system forge discussion."""
        kept = [item for item in comments if not item.system][-limit:]
        return "\n\n".join(f"{item.author}: {item.body.strip()}" for item in kept)

    def _read_questions(self, run: RunState) -> str:
        """@brief Read and remove the executor question handoff file."""
        path = Path(run.worktree) / self.questions_file
        if not path.is_file():
            return ""
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            return f"Unable to read questions file: {exc}"
        path.unlink(missing_ok=True)
        return text.strip()

    # Shared isolation, budget, status and metrics internals

    def _run_id(self, iid: int) -> str:
        """@brief Derive the stable ticket-bound run identifier."""
        return derive_run_id(self.config.platform.kind, self.config.platform.repo, iid)

    def _branch_name(self, run_id: str, iid: int) -> str:
        """@brief Render the configured task branch template."""
        return self.config.worktree.branch_template.format(
            slug=self.identity.slug, run_id=run_id, iid=iid
        )

    def _valid_admission_branch(self, name: str) -> bool:
        """@brief Apply bounded existing Git-name and Python-rule validation to actual names."""
        return branch_naming_preview(
            "{run_id}", self.config.worktree.branch_rule, self.identity.slug, run_id=name,
        )["valid"]

    def _owned_branch(self, run: RunState) -> bool:
        """@brief Recognize only the configured base or one exact derived generation."""
        base = self._branch_name(run.run_id, run.ticket_iid)
        return re.fullmatch(re.escape(base) + r"(?:-g[0-9a-f]{12})?", run.branch) is not None

    def _io_dir(self, run_id: str) -> Path:
        """@brief Return the host-side executor exchange directory."""
        return self.store.run_dir(run_id) / "io"

    def _plan_execution(self, run: RunState) -> None:
        """@brief Resolve initial execution authority in memory before allocating a snapshot.
        @details The caller persists only after it can select the worktree's workflow.
                 Existing runs keep their pinned plan; provisioning verifies its receipts.
        @exception ExecutionRecoveryError Initial execution authority cannot be resolved.
        """
        recipe = bool(self.config.execution.preparation)
        local = self.config.execution.backend == "local"
        packages = self.config.container.system_packages is True
        if packages and local:
            raise ExecutionRecoveryError("system_packages is available only in containers")
        if run.execution or not (recipe or local or packages):
            return
        try:
            if run.active_task_id:
                raise PreparationError("active legacy run requires an explicit fresh execution run")
            if recipe and not self.worktrees.exists(run.run_id):
                self.worktrees.fetch()
            plan = resolve_plan(
                self.config,
                runner=getattr(self.worktrees, "runner", run_command),
                expected_revision=self.worktrees.ref_head(run.base_ref) if recipe else None,
            )
            if recipe:
                run.base_ref = plan["selection"].rsplit("@", 1)[1]
            run.execution = {
                "plan": plan, "resource": {}, "status": "pending" if recipe else "not-required",
                "attempts": 0, "steps": [], "history": [], "reprepare": False,
            }
        except (PreparationError, OSError, TypeError, ValueError) as exc:
            raise ExecutionRecoveryError(str(exc)) from exc

    def _allocate_worktree(self, run: RunState) -> Path:
        """@brief Allocate the exact pinned snapshot without saving a provisional workflow."""
        self._plan_execution(run)
        if not self.config.execution.preparation and not self.worktrees.exists(run.run_id):
            self.worktrees.fetch()
        worktree = self.worktrees.create(
            run.run_id, run.branch, run.base_ref or "HEAD",
            **({"new_branch": True} if not run.worktree else {}),
        )
        run.worktree = str(worktree)
        return worktree

    def _provision(self, run: RunState) -> None:
        """@brief Provision the pinned target and prepare once per verified resource."""
        recipe = bool(self.config.execution.preparation)
        local = self.config.execution.backend == "local"
        packages = self.config.container.system_packages is True
        managed_container = recipe or packages
        if packages and local:
            raise ExecutionRecoveryError("system_packages is available only in containers")
        record = run.execution
        plan = {}
        if managed_container or local or record:
            try:
                if not run.execution:
                    self._plan_execution(run)
                    self.store.save(run)
                record = run.execution
                plan = record["plan"]
                if (
                    plan["policy"] != execution_policy(self.config)
                    or plan["selection"] != self.config.execution.preparation
                    or not recipe and not local
                    and plan["image"] != self.config.container.image
                ):
                    raise PreparationError(
                        "execution profile drift; restore pinned settings or start a fresh run"
                    )
                if (
                    recipe
                    and self.config.container.image
                    and (
                        "image" in self.config.raw.get("container", {})
                        or self.config.container.image != EXECUTOR_BASE_IMAGE
                    )
                    and self.config.container.image != plan["image"]
                ):
                    raise PreparationError("container.image conflicts with pinned preparation")
                plan_file = self.store.run_dir(run.run_id) / "execution-plan.json"
                serialized = json.dumps(plan, sort_keys=True, ensure_ascii=False, indent=2).encode()
                if plan_file.exists():
                    if plan_file.is_symlink():
                        raise PreparationError("execution plan is linked")
                    differs = (read_record(plan_file) != plan if local
                               else plan_file.read_bytes() != serialized)
                    if differs:
                        raise PreparationError("immutable execution plan differs from state")
                else:
                    with plan_file.open("xb") as handle:
                        handle.write(serialized)
            except (PreparationError, OSError, TypeError, ValueError) as exc:
                raise ExecutionRecoveryError(str(exc)) from exc
        if recipe:
            for attempt in [
                *record["history"],
                {"attempt": record["attempts"], "steps": record["steps"]},
            ]:
                for step in attempt["steps"]:
                    evidence = (
                        self.store.run_dir(run.run_id)
                        / "preparation"
                        / f"attempt-{attempt['attempt']}"
                        / f"step-{step['index'] + 1}.json"
                    )
                    try:
                        if evidence.is_symlink() or evidence.stat().st_size > 1_000_000:
                            raise ValueError
                        stored = strict_json_loads(evidence.read_text(encoding="utf-8"))
                        if (
                            not isinstance(stored, dict)
                            or set(stored) != set(step) | {"stdout", "stderr"}
                            or any(stored[key] != value for key, value in step.items())
                            or any(
                                not isinstance(stored[key], str)
                                or len(stored[key].encode()) > 65536
                                for key in ("stdout", "stderr")
                            )
                        ):
                            raise ValueError
                    except (OSError, ValueError, TypeError) as exc:
                        raise ExecutionRecoveryError(
                            "immutable preparation evidence missing or corrupt"
                        ) from exc
            if record["reprepare"]:
                self.backend.remove(run.container, expected=record["resource"] or None)
                if record["attempts"]:
                    record["history"].append(
                        {
                            "attempt": record["attempts"],
                            "status": record["status"],
                            "resource": record["resource"],
                            "steps": record["steps"],
                        }
                    )
                record.update(resource={}, steps=[], status="pending", reprepare=False)
                self.store.save(run)
            elif record["status"] in {"running", "failed", "interrupted", "cancelled"}:
                raise ExecutionRecoveryError(
                    "preparation incomplete; inspect evidence then retry --reprepare"
                )
            elif record["resource"]:
                observed = self.backend.resource_identity(run.container)
                if any(
                    observed[key] != record["resource"][key] for key in ("container_id", "image_id")
                ):
                    raise ExecutionRecoveryError(
                        "prepared resource changed; explicit recovery required"
                    )
            image_id = self.backend.image_identity(plan["image"])
            if record["resource"] and image_id != record["resource"]["image_id"]:
                raise ExecutionRecoveryError(
                    "prepared image identity changed; explicit recovery required"
                )
        if packages and not recipe:
            image_id = self.backend.image_identity(plan["image"])
            if record["resource"]:
                observed = self.backend.resource_identity(run.container)
                if (any(observed[key] != record["resource"][key]
                        for key in ("container_id", "image_id"))
                        or image_id != record["resource"]["image_id"]):
                    raise ExecutionRecoveryError(
                        "package-enabled environment changed; start a fresh run to reinstall")
        worktree = self._allocate_worktree(run)
        env = self._container_env(run)
        if local and record["resource"]:
            self.backend.bind(run.container, env, record["resource"])
        provisioned = self.backend.provision(
            run.container,
            self.worktrees.repo_path,
            worktree,
            self._io_dir(run.run_id),
            env,
            image=plan["image"] if managed_container else None,
        )
        if managed_container:
            observed = self.backend.resource_identity(run.container)
            resource = {key: observed[key] for key in ("container_id", "image_id")}
            if (observed["status"] != "running" or resource["image_id"] != image_id
                    or record["resource"] and resource != record["resource"]
                    or not record["resource"] and provisioned != "created"):
                raise ExecutionRecoveryError("provisioned target identity cannot be trusted")
            record["resource"] = resource
            self.store.save(run)
        elif local:
            resource = self.backend.resource_identity(run.container)
            if record["resource"] and resource != record["resource"]:
                raise ExecutionRecoveryError("local native target identity changed")
            record["resource"] = resource
            self.store.save(run)
        if packages:
            self.backend.authorize_system_packages(run.container, expected=record["resource"])
            self.store.journal(run.run_id, "system-package-permission",
                               container_id=record["resource"]["container_id"], enabled=True)
        self.backend.verify_required_tools(
            run.container, self.config.container.required_tool_checks, env=env
        )
        if recipe and record["status"] != "success":
            self._prepare_execution(run)
        self.store.save(run)

    def _execute(self, run: RunState):
        """@brief Bind gates and AEGIS commands to verified backend-native paths."""
        return self.backend.bind(
            run.container, self._container_env(run), run.execution.get("resource") or None
        )

    def _prepare_execution(self, run: RunState) -> None:
        """@brief Execute sequential bounded setup, with durable fail-closed evidence."""
        record = run.execution
        if record["attempts"] >= self.config.execution.preparation_max_attempts:
            raise ExecutionRecoveryError("preparation attempt limit reached")
        record["attempts"] += 1
        record.update(status="running", steps=[])
        self.store.save(run)  # Durable before the first project side effect.
        started = time.monotonic()
        finished = Event()

        def interrupt_on_cancel() -> None:
            """@brief Stop only the verified recipe target after a durable cancel."""
            while not finished.wait(0.2):
                try:
                    if not self.store.cancel_requested(run.run_id):
                        continue
                    self.backend.interrupt(run.container, expected=record["resource"])
                except (StateError, IsolationError) as exc:
                    self.log(f"preparation cancellation failed: {_sanitize(exc)}")
                return

        watcher = Thread(target=interrupt_on_cancel, daemon=True)
        watcher.start()
        try:
            for index, step in enumerate(record["plan"]["steps"]):
                if self.store.cancel_requested(run.run_id):
                    record["status"] = "cancelled"
                    raise ExecutionRecoveryError("preparation cancelled")
                elapsed = run.active_work_seconds(utc_now_iso())
                remaining = min(
                    self.config.execution.preparation_total_timeout_seconds
                    - (time.monotonic() - started),
                    self.config.budgets.max_wall_clock_seconds - elapsed,
                    self.config.execution.preparation_step_timeout_seconds,
                )
                if remaining <= 0 or self._budget_exceeded(run):
                    raise ExecutionRecoveryError("preparation run budget exhausted")
                self.store.journal(
                    run.run_id,
                    "preparation-step-started",
                    index=index,
                    name=step["name"],
                    attempt=record["attempts"],
                )
                protocol_error = None
                try:
                    outcome = run_preparation_step(
                        self._execute(run),
                        self._io_dir(run.run_id),
                        record["attempts"],
                        index,
                        step,
                        timeout=remaining,
                        secrets=self.secrets,
                    )
                except PreparationResultError as exc:
                    outcome, protocol_error = exc.outcome, exc

                outcome["cancelled"] = self.store.cancel_requested(run.run_id)
                archive = (
                    self.store.run_dir(run.run_id) / "preparation" / f"attempt-{record['attempts']}"
                )
                archive.mkdir(parents=True, exist_ok=True)
                with (archive / f"step-{index + 1}.json").open("x", encoding="utf-8") as handle:
                    json.dump(outcome, handle, ensure_ascii=False, indent=2)
                record["steps"].append(
                    {k: v for k, v in outcome.items() if k not in {"stdout", "stderr"}}
                )
                self.store.save(run)
                self.store.journal(
                    run.run_id,
                    "preparation-step-finished",
                    index=index,
                    exit_code=outcome["exit_code"],
                    timed_out=outcome["timed_out"],
                    cancelled=outcome["cancelled"],
                    attempt=record["attempts"],
                )
                if protocol_error:
                    record["status"] = "cancelled" if outcome["cancelled"] else "interrupted"
                    raise protocol_error
                if outcome["exit_code"] or outcome["timed_out"] or outcome["cancelled"]:
                    record["status"] = "cancelled" if outcome["cancelled"] else "failed"
                    raise ExecutionRecoveryError(
                        "preparation step failed; inspect evidence then retry --reprepare"
                    )
            record["status"] = "success"
            self.store.save(run)
            self.store.journal(
                run.run_id,
                "preparation-succeeded",
                fingerprint=record["plan"]["fingerprint"],
                attempt=record["attempts"],
            )
        except (IsolationError, OSError) as exc:
            if record["status"] == "running":
                record["status"] = (
                    "cancelled" if self.store.cancel_requested(run.run_id) else "interrupted"
                )
            self.store.save(run)
            with contextlib.suppress(IsolationError):
                self.backend.interrupt(run.container, expected=record["resource"])
            raise ExecutionRecoveryError(str(exc)) from exc
        finally:
            finished.set()
            watcher.join(timeout=21)

    def _container_env(self, run: RunState) -> dict[str, str]:
        """@brief Compose the constrained executor environment."""
        if self.config.execution.backend == "local":
            env = self.backend.executor_environment()
            env.update({key: value for key, value in self.secrets.items()
                        if key in secret_names(self.config.executor,
                                               self.config.execution.backend)})
            return env
        env = build_container_env(
            self.worktrees.admin_dir_name(run.run_id),
            self.config.agent.name,
            self.config.agent.email,
        )
        env.update(self.config.container.runtime_env)
        env.update(self.secrets)
        env.update(self.backend.executor_environment())
        return env

    def _cost_spent(self, run: RunState) -> float:
        """@brief Sum durable per-launch executor cost records."""
        return sum(
            float(event.get("cost_usd", 0) or 0)
            for event in self.store.read_journal(run.run_id)
            if event.get("event") == "usage"
            and isinstance(event.get("cost_usd", 0), (int, float))
        )

    def _refresh_budgets(self, run: RunState) -> bool:
        """
        @brief Reread only budgets at an execution boundary, retaining all job evidence.
        @param[in,out] run Current job to fail closed on unavailable or changed input.
        @return True when the selected source remains valid and only budgets changed.
        """
        if self.config.source_path is None:
            return True  # Directly injected configurations have no on-disk source.
        try:
            current = load_config(self.config.source_path)
            if validate_budgets(current):
                raise ValueError("invalid budgets")
            before, after = self.config.to_dict(), current.to_dict()
            before.pop("budgets")
            after.pop("budgets")
            raw_before, raw_after = dict(self.config.raw), dict(current.raw)
            raw_before.pop("budgets", None)
            raw_after.pop("budgets", None)
            # JSON preserves scalar types where Python equality conflates
            # False with 0 or True with 1. Raw binding also rejects unknown keys.
            if any(json.dumps(left, sort_keys=True, allow_nan=False)
                   != json.dumps(right, sort_keys=True, allow_nan=False)
                   for left, right in ((before, after), (raw_before, raw_after))):
                raise ValueError("non-budget configuration changed")
        except (OSError, ValueError, TypeError, AttributeError, OverflowError, RecursionError):
            self._fail_immediately(
                run, "BUDGET_CONFIG_INVALID",
                "Cannot refresh budgets: restore a valid configuration with unchanged "
                "non-budget settings before retrying this job.",
            )
            return False
        self.config.budgets = current.budgets
        return True

    def _budget_exceeded(self, run: RunState, *, include_launch: bool = True) -> str:
        """@brief Return an exhausted budget; completion does not authorize another launch."""
        budgets = self.config.budgets
        if include_launch and run.iterations >= budgets.max_iterations:
            return f"iteration budget reached ({run.iterations}/{budgets.max_iterations})"
        if run.active_work_seconds(utc_now_iso()) >= budgets.max_wall_clock_seconds:
            return f"active work clock reached {budgets.max_wall_clock_seconds}s"
        if budgets.max_cost_usd > 0:
            cost_spent = self._cost_spent(run)
            if cost_spent >= budgets.max_cost_usd:
                return f"cost budget reached (${cost_spent:.2f})"
        if run.base_ref and self.worktrees.exists(run.run_id):
            try:
                if not self.worktrees.merge_in_progress(run.run_id):
                    touched = self.worktrees.changed_files(run.run_id, run.base_ref)
                    if touched > budgets.max_files_touched:
                        return f"file budget exceeded ({touched}/{budgets.max_files_touched})"
            except IsolationError:
                pass
        return ""

    def _ticket_from_snapshot(self, run: RunState) -> Ticket:
        """@brief Rebuild prompt context from the latest persisted ticket snapshot."""
        data = self.store.load_ticket(run.run_id)
        return Ticket(
            iid=run.ticket_iid,
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            labels=list(data.get("labels", [])),
            author=str(data.get("author", "")),
            web_url=str(data.get("web_url", "")),
        )

    def _status_body(self, run: RunState) -> str:
        """@brief Render current lifecycle and checkpoint evidence for the ticket."""
        body = self.identity.status_comment(
            run.run_id, run.lifecycle, run.stage, utc_now_iso()
        )
        backend = run.execution.get("plan", {}).get("backend", self.config.execution.backend)
        body += f"\nExecution backend: {backend}"
        if (self.config.delivery.publish_checkpoints or run.checkpoint_remote_commit
                or run.checkpoint_error):
            body += (
                f"\n\nWork in progress; checkpoint visibility does not approve delivery.\n"
                f"Branch: {self._checkpoint_branch_link(run)}\n"
                f"Last verified remote checkpoint: `{run.checkpoint_remote_commit or 'none'}`\n"
                + (f"Remote checkpoint stale: {_sanitize(run.checkpoint_error)}\n"
                   if run.checkpoint_error else "")
            )
        return body

    def _deliver_status(self, run: RunState, record: dict[str, Any]) -> int:
        """@brief Deliver current status and labels, retaining identity before label writes."""
        comment_id = self._deliver_outbox_record(run, record)
        marker = self.identity.make_marker(
            run.run_id, "status-replay", notification=record["id"]
        )
        self.forge.edit_comment(
            run.ticket_iid, comment_id, f"{marker}\n{self._status_body(run)}"
        )
        run.status_comment_id = comment_id
        record["edit_id"] = comment_id
        self.store.save(run)
        self._status_labels(run)
        return comment_id

    def _status(self, run: RunState) -> None:
        """@brief Persist and deliver lifecycle status and labels idempotently."""
        notification_id = uuid4().hex
        marker = self.identity.make_marker(
            run.run_id, "status-replay", notification=notification_id
        )
        record = {
            "id": notification_id,
            "kind": "status",
            "surface": "ticket",
            "resource": run.ticket_iid,
            "edit_id": run.status_comment_id,
            "body": f"{marker}\n{self._status_body(run)}",
            "attempts": 0,
            "next_attempt_at": utc_now_iso(),
            "last_error": "",
        }
        run.notification_outbox.append(record)
        self.store.save(run)
        try:
            self._deliver_status(run, record)
        except ForgeError as exc:
            record["attempts"] = 1
            record["last_error"] = _sanitize(exc)
            record["next_attempt_at"] = self._next_retry_time(1)
            if run.lifecycle in {"cancelled", "done", "failed", "handed-off", "handoff-pending"}:
                self.store.save(run)
                self.store.journal(
                    run.run_id, "notification-blocked", code="STATUS_NOTIFICATION",
                    evidence=_sanitize(exc), terminal_lifecycle=run.lifecycle,
                )
                return
            self._notification_transport_failure(run, "STATUS_NOTIFICATION", exc)
            return
        run.notification_outbox = [
            item for item in run.notification_outbox if item.get("id") != notification_id
        ]
        self.store.save(run)

    def _status_labels(self, run: RunState) -> None:
        """@brief Map schema-1 lifecycle to existing ticket labels."""
        lifecycle = self.config.labels.lifecycle
        known = [
            lifecycle.ready,
            lifecycle.working,
            lifecycle.clarify,
            lifecycle.review,
            lifecycle.failed,
            lifecycle.done,
        ]
        selected = {
            "working": lifecycle.working,
            "publishing": lifecycle.working,
            "parked-clarification": lifecycle.clarify,
            "awaiting-approval": lifecycle.working,
            "in-review": lifecycle.review,
            "failed": lifecycle.failed,
            "done": lifecycle.done,
        }.get(run.lifecycle)
        if selected:
            self.forge.add_labels(run.ticket_iid, [selected])
        self.forge.remove_labels(
            run.ticket_iid, [item for item in known if item != selected]
        )

    def _teardown(self, run: RunState, *, remove_worktree: bool) -> None:
        """@brief Remove execution resources while retaining local state evidence."""
        if (self.config.execution.backend == "local"
                or run.execution.get("plan", {}).get("backend") == "local"):
            self.backend.remove(run.container, expected=run.execution.get("resource") or None)
        else:
            with contextlib.suppress(IsolationError):
                self.backend.remove(run.container, expected=run.execution.get("resource") or None)
        if remove_worktree:
            try:
                self.worktrees.remove(run.run_id, delete_branch=run.branch)
            except IsolationError as exc:
                self.log(f"{run.run_id}: worktree husk retained for cleanup: {exc}")

    def _journal_usage(self, run: RunState, context: str, result: GateRun) -> None:
        """@brief Persist one launch's telemetry status plus observed usage."""
        captured = self.config.metrics.capture_tokens
        observed_tokens = (result.tokens_reported
                           if result.tokens_reported is not None
                           else bool(result.tokens_in or result.tokens_out))
        observed_cost = result.cost_reported or result.cost_usd > 0
        model = self.config.executor.model or None
        self.store.journal(
            run.run_id,
            "usage-observation",
            schema=1,
            event_id=f"{run.run_id}:{run.iterations}",
            attempt=run.iterations,
            stage=context,
            review_round=run.review_rounds,
            executor=EXECUTOR_NAME,
            model=model,
            token_status=("disabled" if not captured else
                          "reported" if observed_tokens else "unavailable"),
            cost_status=("disabled" if not captured else
                         "reported" if observed_cost else "unavailable"),
            tokens_in=result.tokens_in if captured and observed_tokens else None,
            tokens_out=result.tokens_out if captured and observed_tokens else None,
              cache_read_tokens=(result.cache_read_tokens
                                 if captured and observed_tokens else None),
              cache_write_tokens=(result.cache_write_tokens
                                  if captured and observed_tokens else None),
              input_includes_cache=True,
            cost_usd=result.cost_usd if captured and observed_cost else None,
        )
        if self.config.metrics.capture_tokens and observed_tokens and (
            result.tokens_in or result.tokens_out or result.cost_usd
        ):
            self.store.journal(
                run.run_id,
                "usage",
                event_id=f"{run.run_id}:{run.iterations}",
                attempt=run.iterations,
                context=context,
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                  cache_read_tokens=result.cache_read_tokens,
                  cache_write_tokens=result.cache_write_tokens,
                  input_includes_cache=True,
                cost_usd=result.cost_usd,
                cost_reported=result.cost_reported or result.cost_usd > 0,
                executor=EXECUTOR_NAME,
                model=model,
                review_round=run.review_rounds,
            )

    def _journal_artifacts(self, run: RunState, context: str, result: GateRun) -> None:
        """@brief Link immutable per-launch executor evidence into the audit log."""
        # Every completed attempt supersedes earlier output, including unavailable capture.
        self.store.journal(
            run.run_id,
            "executor-artifacts",
            context=context,
            artifacts=result.artifact_dirs,
            diagnostics=record_diagnostics(self.store.run_dir(run.run_id), run.run_id,
                                           run.iterations, context, result),
        )

    def _record_metrics(self, run: RunState) -> None:
        """@brief Record terminal metrics without letting metrics break a run."""
        if not self.config.metrics.enabled:
            return
        try:
            files = 0
            if run.base_ref and self.worktrees.exists(run.run_id):
                with contextlib.suppress(IsolationError):
                    files = self.worktrees.changed_files(run.run_id, run.base_ref)
            summary = metrics.summarize_run(self.store, run.run_id, files)
            metrics.record_summary(
                self.config.metrics.db_path,
                summary,
                self.config.metrics.export_jsonl,
            )
        except Exception as exc:  # noqa: BLE001 - metrics are explicitly best-effort
            self.log(f"{run.run_id}: metrics recording failed: {exc}")


# END OF FILE
