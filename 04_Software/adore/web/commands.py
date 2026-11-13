#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file commands.py
@brief Single-host durable web operation worker.
@details Uses the existing CLI as the bounded, locked engine boundary. A
         demonstrably dead owner leaves in-flight commands uncertain instead of replaying
         a possible forge or container side effect.
"""

from __future__ import annotations

# IMPORTS
import argparse
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from threading import Event, Lock, Thread
import time

from adore.config import load_config, validate_config
from adore.polling import PollCadence
from adore.profiles import ProfileError, ProfileStore
from adore.start_result import (
    StartResultError,
    read_restart_result,
    read_retry_result,
    read_start_result,
)
from adore.state import StateError, StateStore
from adore.util import (
    CommandResult,
    automatic_environment,
    background_process_options,
    in_quiet_hours,
    output_tail,
)
from adore.web.jobs import redact_text
from adore.web.ownership import OwnershipError, WorkerOwner
from adore.web.store import WebStore, WebStoreError


# DATA MODELS / TYPEDEFINITIONS
@dataclass(frozen=True)
class CommandOutcome:
    """@brief Exit code and combined stdout/stderr of one engine command."""

    code: int
    output: str = ""


# A runner may return a bare exit code when it has no output to keep.
Runner = Callable[[list[str], dict[str, str]], int | CommandOutcome | CommandResult]


# The line `adore run --once --ticket N` prints when it starts no job.
_NOT_STARTED = re.compile(
    r"^error: ticket #(\d+) not started: "
    r"(pickup_paused|at_capacity|aegis_probe_failed|not_eligible|conductor_busy)$",
    re.MULTILINE,
)
_COMMAND_ACTIONS = ("start", "retry", "restart", "cancel", "pause", "resume", "delete")


# HELPER FUNCTIONS
def _run(argv: list[str], env: dict[str, str]) -> CommandOutcome:
    """@brief Run a fixed CLI argument vector with a finite timeout, keeping its output.
    @details stderr joins stdout so the kept lines stay in the order they were printed.
    """
    try:
        result = subprocess.run(
            argv, env=automatic_environment(env), stdin=subprocess.DEVNULL,
            **background_process_options(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", check=False, timeout=21600,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.output
        if isinstance(output, bytes):
            output = output.decode("utf-8", "replace")
        return CommandOutcome(124, output or "")
    return CommandOutcome(result.returncode, result.stdout or "")


def _refusal_reason(output: str, ticket: str) -> str:
    """@brief Return the stable code the CLI printed for this ticket, or ""."""
    codes = [code for iid, code in _NOT_STARTED.findall(output) if iid == ticket]
    return codes[-1] if codes else ""


# PUBLIC API
class CommandWorker:
    """@brief Execute authorized persisted commands through ADORE's CLI."""

    def __init__(self, profiles: ProfileStore, web: WebStore,
                 runner: Runner = _run) -> None:
        self.profiles = profiles
        self.web = web
        self.runner = runner
        self._owners: dict[tuple[str, str], WorkerOwner] = {}
        self._owners_lock = Lock()
        self._supervisor: WorkerOwner | None = None
        self._cancel_claims: dict[int, tuple[dict, WorkerOwner]] = {}
        # Unbuffered UTF-8 output keeps the engine's lines in order and every character printable.
        self.environment = {**os.environ, "ADORE_HOME": str(profiles.home),
                            "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}

    def run_pending(self) -> int:
        """@brief Execute at most one pending command; return 1 if claimed."""
        owner = None
        operation = None
        if self._cancel_claims:
            operation, owner = self._cancel_claims.pop(next(iter(self._cancel_claims)))
        else:
            for domain, project_id in self.web.pending_domains(actions=_COMMAND_ACTIONS):
                if domain == "configuration_global":
                    continue
                try:
                    owner = self._owner(domain, project_id)
                    operation = self.web.claim_next(
                        owner, domain=domain,
                        actions=_COMMAND_ACTIONS)
                except OwnershipError:
                    continue
                if operation is not None:
                    break
        if operation is None:
            return 0
        if operation["status"] != "running":
            return 1
        def finish(operation_id, status, result, *, reason="", detail=""):
            """@brief Finish this exact claim and release completed configuration ownership."""
            self.web.finish(operation_id, status, result, owner=owner,
                            generation=operation["generation"], reason=reason, detail=detail)
            if owner.role == "configuration":
                with self._owners_lock:
                    try:
                        self.web.clear_worker(owner)
                    except OwnershipError:
                        return
                    self._owners.pop((operation["domain"], owner.project_id), None)
        actor = self.web.user_by_id(operation["actor_id"])
        project = operation["project"]
        try:
            grants = (self.web.memberships(actor["id"])
                      if actor is not None and actor["role"] != "admin" else set())
        except WebStoreError:
            finish(operation["id"], "failed", "project grants are corrupt")
            return 1
        if (actor is None or actor["disabled"] or not self.profiles.exists(project)
                or (actor["role"] != "admin" and project not in grants)):
            finish(operation["id"], "failed", "permission or project revoked")
            return 1
        try:
            profile = self.profiles.load(project)
            if profile.project_id != operation["project_id"]:
                finish(operation["id"], "failed", "project identity changed")
                return 1
            if operation["action"] == "delete":
                if actor["role"] != "admin" or not profile.archived:
                    finish(operation["id"], "failed",
                                    "delete requires an administrator and an archived project")
                    return 1
            elif profile.archived:
                finish(operation["id"], "failed", "project archived")
                return 1
        except ProfileError:
            finish(operation["id"], "failed", "project metadata corrupt")
            return 1
        argv = [sys.executable, "-m", "adore", "--profile", project]
        action = operation["action"]
        target = operation["run_id"]
        if action == "cancel":
            try:
                profile = self.profiles.load(project)
                state = StateStore(
                    profile.store_root or self.profiles.default_store_root(project)
                )
                run = state.load(target)
            except (ProfileError, FileNotFoundError, StateError, OSError):
                finish(operation["id"], "failed", "run is unavailable")
                return 1
            if run.lifecycle == "cancelled":
                finish(operation["id"], "succeeded", "run cancelled")
                return 1
            if run.lifecycle in ("done", "failed", "handoff-pending", "handed-off"):
                finish(operation["id"], "failed", "run already finished")
                return 1
        if action == "delete" and target in ("", "remove-clone"):
            # The delete target carries only the explicit clone-removal choice.
            argv = [sys.executable, "-m", "adore", "profile", "delete", project,
                    "--force", "--remove-resources", *(["--remove-clone"] if target else [])]
        elif action == "start" and target.isdigit() and int(target) > 0:
            argv.extend(["run", "--once", "--ticket", target])
        elif action == "restart":
            match = re.fullmatch(r"([A-Za-z0-9._-]{1,160})\.([a-f0-9]{64})", target)
            try:
                if match is None:
                    raise StateError("invalid confirmed restart")
                run_id, revision = match.groups()
                state = StateStore(profile.store_root or self.profiles.default_store_root(project))
                raw = (state.run_dir(run_id) / "state.json").read_bytes()
                previous = state.load(run_id)
                if (previous.lifecycle != "failed"
                        or sha256(raw).hexdigest() != revision):
                    raise StateError("confirmed job changed")
            except (StateError, OSError):
                finish(operation["id"], "failed", "restart:job_changed")
                return 1
            argv.extend(["restart", run_id, "--force", "--expected-revision", revision])
        elif action in ("retry", "cancel") and target:
            argv.extend([action, target])
        elif action in ("pause", "resume") and actor["role"] == "admin" and not target:
            argv.append(action)
        else:
            finish(operation["id"], "failed", "invalid operation")
            return 1
        try:
            self.web.authorize_effect(operation["id"], owner=owner,
                                      generation=operation["generation"])
            context = json.dumps({"owner_id": owner.id, "owner_generation": owner.generation,
                                  "role": owner.role, "project_id": owner.project_id,
                                  "run_id": owner.run_id, "operation_id": operation["id"],
                                  "generation": operation["generation"]})
            outcome = self._run_with_cancel_watch(argv, context=context)
        except OwnershipError as exc:
            if exc.reason != "ownership_lost":
                finish(operation["id"], "failed", exc.reason, reason=exc.reason)
                return 1
            # Never acknowledge or invoke effects under a stale owner.
            raise
        except Exception:  # noqa: BLE001 - unexpected outcome needs reconciliation
            current = self.web.operation(operation["id"])
            if action == "start" and current["status"] == "succeeded":
                self.web.authorize_effect(operation["id"], owner=owner,
                                          generation=operation["generation"])
                return 1
            finish(operation["id"], "uncertain", "worker invocation failed")
            return 1
        if isinstance(outcome, CommandResult):
            code, output = outcome.exit_code, outcome.stdout + "\n" + outcome.stderr
        elif isinstance(outcome, CommandOutcome):
            code, output = outcome.code, outcome.output
        else:
            code, output = outcome, ""
        if type(code) is not int or type(output) is not str:
            finish(operation["id"], "uncertain", "invalid engine outcome")
            return 1
        status = "uncertain" if code == 124 else "succeeded" if code == 0 else "failed"
        result = (
            "completed" if code == 0 else
            "outcome uncertain" if code == 124 else "engine rejected operation"
        )
        evidence = outcome.stdout if isinstance(outcome, CommandResult) else output
        retry_reason = ""
        if (action == "start" and isinstance(outcome, (CommandResult, CommandOutcome))
                and code != 124):
            try:
                reason = read_start_result(evidence, ticket=int(target), exit_code=code)
            except StartResultError:
                reason = "invalid_result"
                if code == 0:
                    status = "uncertain"
            result = "completed" if reason == "started" else "start:" + reason
        if (action == "retry" and isinstance(outcome, (CommandResult, CommandOutcome))
                and code != 124):
            try:
                reason = read_retry_result(evidence, run_id=target, exit_code=code)
            except StartResultError:
                reason = "invalid_result"
                if code == 0:
                    status = "uncertain"
            retry_reason = reason
            result = "completed" if reason == "retried" else "retry:" + reason
            if reason == "retry_failed":
                try:
                    state = StateStore(
                        profile.store_root or self.profiles.default_store_root(project))
                    failed = state.load(target)
                    if failed.lifecycle != "failed" or not failed.outcome:
                        raise StateError("Retry failure evidence is unavailable")
                    result = "retry:failed:" + failed.outcome[:2200]
                except (FileNotFoundError, StateError, OSError):
                    result = "retry:state_unavailable"
        if action == "restart" and code != 124:
            try:
                restart_reason, retained = read_restart_result(
                    evidence, run_id=run_id, revision=revision, exit_code=code,
                    ticket=previous.ticket_iid,
                )
                if restart_reason == "restarted":
                    result = "restart:retained" if retained else "completed"
                elif restart_reason in ("cleanup_refused", "lock_held", "run_unavailable",
                                         "force_required"):
                    result = "restart:rejected"
                else:
                    result = "restart:failed"
            except StartResultError:
                status, result = "uncertain", "restart:invalid_result"
        detail = output_tail(output, redact_text) if code != 0 else ""
        reason = (_refusal_reason(output, target) if status == "failed" and action == "start"
                  else retry_reason if action == "retry" else "")
        if action == "cancel" and status == "succeeded":
            try:
                state = StateStore(
                    profile.store_root or self.profiles.default_store_root(project))
                observed = state.load(target)
                if observed.lifecycle != "cancelled":
                    status, result, reason = (
                        "uncertain", "cancel not confirmed", "cancel_unconfirmed")
            except (StateError, FileNotFoundError, OSError):
                status, result, reason = "uncertain", "cancel not confirmed", "cancel_unconfirmed"
        current = self.web.operation(operation["id"])
        if action == "start" and current["status"] == "succeeded":
            # Admission is already confirmed; subsequent job failure is separate.
            self.web.authorize_effect(operation["id"], owner=owner,
                                      generation=operation["generation"])
            return 1
        if action == "start" and status == "succeeded":
            status, result, reason = "uncertain", "start:invalid_result", ""
        finish(operation["id"], status, result, reason=reason, detail=detail)
        if action == "delete" and status == "succeeded":
            self.web.audit(actor["id"], "project-deleted", project)
        return 1

    def _owner(self, domain: str, project_id: str) -> WorkerOwner:
        """@brief Reuse only this worker's explicit project/domain owner handle."""
        key = (domain, project_id)
        with self._owners_lock:
            if key not in self._owners:
                role = "project" if domain == "execution" else "configuration"
                try:
                    self._owners[key] = self.web.register_worker(role, project_id=project_id)
                except OwnershipError:
                    # A child retained at startup may have exited since that inspection.
                    self.web.recover_interrupted(project_id=project_id, role=role)
                    self._owners[key] = self.web.register_worker(role, project_id=project_id)
            return self._owners[key]

    def _signal_pending_cancels(self) -> None:
        """@brief Claim and authorize before writing any durable cancel signal."""
        for pending in self.web.pending_cancels():
            try:
                owner = self._owner("execution", pending["project_id"])
                operation = self.web.claim_next(owner, domain="execution", action="cancel")
                if operation is None or operation["status"] != "running":
                    continue
                self._cancel_claims[operation["id"]] = (operation, owner)
                operation = self.web.authorize_effect(operation["id"], owner=owner,
                                                      generation=operation["generation"])
                profile = self.profiles.load(operation["project"])
                state = StateStore(
                    profile.store_root or self.profiles.default_store_root(profile.name))
                state.request_cancel(operation["run_id"])
            except (WebStoreError, ProfileError, FileNotFoundError, StateError, OSError):
                # The claimed command later records the unavailable/refused outcome.
                continue

    def _run_with_cancel_watch(
        self, argv: list[str], *, context: str | None = None,
    ) -> int | CommandOutcome | CommandResult:
        """@brief Watch queued cancellations around one blocking engine command."""
        done = Event()

        def watch() -> None:
            """@brief Deliver pending cancel signals during a blocking CLI poll."""
            while not done.wait(0.2):
                try:
                    self._signal_pending_cancels()
                except WebStoreError:
                    # The main worker still handles queued operations afterward.
                    return

        if self._supervisor is not None:
            self.web.set_worker_activity(self._supervisor, "busy")
        watcher = Thread(target=watch, daemon=True)
        watcher.start()
        try:
            environment = dict(self.environment)
            environment.pop("ADORE_WORKER_CONTEXT", None)
            if context is not None:
                environment["ADORE_WORKER_CONTEXT"] = context
            return self.runner(argv, environment)
        finally:
            done.set()
            watcher.join(timeout=2)
            if self._supervisor is not None:
                self.web.set_worker_activity(self._supervisor, "idle")

    def poll_project(self, project: str) -> int | CommandResult:
        """@brief Poll one project while watching for newly authorized cancels."""
        profile = self.profiles.load(project)
        owner = self._owner("execution", profile.project_id)
        self.web.authorize_worker(owner)
        argv = [sys.executable, "-m", "adore", "--profile", project,
                "run", "--once"]
        context = json.dumps({"owner_id": owner.id, "owner_generation": owner.generation,
                              "role": owner.role, "project_id": owner.project_id,
                              "run_id": owner.run_id, "operation_id": 0, "generation": 0})
        outcome = self._run_with_cancel_watch(argv, context=context)
        return (outcome.code if isinstance(outcome, CommandOutcome) else
                outcome.exit_code if isinstance(outcome, CommandResult) else outcome)

    def run_forever(self, *, interval: float = 2.0,
                    heartbeat_interval: float = 2.0,
                    stop: Event | None = None) -> None:
        """@brief Own the local worker lock, heartbeat and project polling."""
        lock = StateStore(self.profiles.home / "web-control", "adore-web")
        if not lock.acquire_lock():
            raise RuntimeError("another web control worker is active")
        stop = stop or Event()
        heartbeat_done = Event()
        heartbeat_failed = Event()
        heartbeat_thread = None
        heartbeat_started = False

        def beat() -> None:
            """@brief Keep readiness current while a conductor call blocks."""
            while not heartbeat_done.wait(heartbeat_interval):
                try:
                    self.web.touch_worker(self._supervisor)
                    with self._owners_lock:
                        for owner in self._owners.values():
                            self.web.touch_worker(owner)
                except (WebStoreError, OSError):
                    heartbeat_failed.set()
                    return

        next_poll: dict[str, float] = {}
        cadences: dict[str, PollCadence] = {}
        try:
            self.web.recover_interrupted()
            self._supervisor = self.web.register_worker("supervisor")
            self.web.set_worker_activity(self._supervisor, "idle")
            self.web.touch_worker(self._supervisor)
            heartbeat_started = True
            heartbeat_thread = Thread(target=beat, daemon=True)
            heartbeat_thread.start()
            while not stop.is_set():
                if heartbeat_failed.is_set():
                    raise RuntimeError("web control worker heartbeat failed")
                if self.run_pending():
                    continue
                active_profiles = [profile for profile in self.profiles.list_profiles()
                                   if not profile.archived]
                for profile in sorted(active_profiles,
                                      key=lambda item: next_poll.get(item.project_id, 0.0)):
                    identity = profile.project_id
                    if next_poll.get(identity, 0.0) > time.monotonic():
                        continue
                    cadence = cadences.setdefault(identity, PollCadence())
                    try:
                        config = load_config(self.profiles.config_path(profile.name))
                        if validate_config(config):
                            raise ValueError("invalid project configuration")
                        # Validate cadence before invoking external work, without
                        # consuming a jitter sample or changing this project's state.
                        PollCadence.validate(config.polling)
                    except (OSError, ValueError, TypeError, AttributeError):
                        next_poll[identity] = time.monotonic() + 60
                        continue
                    failed = None
                    if not in_quiet_hours(config.polling.quiet_hours):
                        try:
                            outcome = self.poll_project(profile.name)
                            code = (outcome.exit_code if isinstance(outcome, CommandResult)
                                    else outcome)
                            failed = type(code) is not int or code != 0
                        except Exception:  # noqa: BLE001 - a failed pass must not stop scheduling
                            failed = True
                    delay = cadence.next_delay(config.polling, failed=failed)
                    next_poll[identity] = time.monotonic() + delay
                    break
                deadlines = [next_poll.get(item.project_id, 0.0) for item in active_profiles]
                wait = (min(interval, max(0.0, min(deadlines) - time.monotonic()))
                        if deadlines else interval)
                stop.wait(wait)
        finally:
            heartbeat_done.set()
            if heartbeat_thread is not None:
                heartbeat_thread.join(timeout=heartbeat_interval + 1)
            try:
                if heartbeat_started:
                    for owner in list(self._owners.values()):
                        # Running effects retain ownership until demonstrated death.
                        with suppress(OwnershipError):
                            self.web.clear_worker(owner)
                    self.web.clear_worker(self._supervisor)
            finally:
                lock.release_lock()


def main() -> int:
    """@brief Launch the web control worker."""
    parser = argparse.ArgumentParser(description="ADORE web control worker")
    parser.add_argument("--home", type=Path, default=None)
    args = parser.parse_args()
    profiles = ProfileStore(args.home)
    CommandWorker(profiles, WebStore(profiles.home / "web.db")).run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE
