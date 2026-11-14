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
@file    worker_context.py
@brief   Bound worker-to-CLI ownership context and engine fencing.
@details The context is internal process transport, never a credential/config
         payload. A child attaches before effects and preserves dead-parent safety.
"""

from __future__ import annotations

# IMPORTS
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from threading import Event, RLock, Thread
from typing import Any

from adore.web.ownership import OwnershipError, WorkerOwner

# CONSTANTS
_CURRENT: ContextVar[WorkerContext | None] = ContextVar("adore_worker_context", default=None)


# DATA MODELS / TYPEDEFINITIONS
@dataclass
class WorkerContext:
    """@brief One attached CLI participant and its immutable operation claim."""

    web: Any
    owner: WorkerOwner
    operation_id: int
    generation: int
    runs: dict[str, WorkerOwner] = field(default_factory=dict)
    lock: Any = field(default_factory=RLock)
    heartbeat_failed: Event = field(default_factory=Event)
    command_run_id: str = field(init=False, default="")
    request_identity: dict[str, Any] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        """@brief Pin immutable request fields and the exact canonical command run once."""
        if self.operation_id:
            operation = self.web.operation(self.operation_id)
            if operation is None:
                raise OwnershipError("worker ownership operation is missing")
            self.request_identity = {key: operation[key] for key in (
                "actor_id", "project_id", "domain", "action", "run_id", "resource_key")}
            resource = operation["resource_key"]
            if resource.startswith("job:"):
                self.command_run_id = resource[4:]

    def authorize(self) -> dict:
        """@brief Refuse lost ownership and revoked rights before each effect."""
        from adore.web.processes import assert_ancestry

        assert_ancestry()
        if self.heartbeat_failed.is_set():
            raise OwnershipError("worker ownership heartbeat failed")
        with self.lock:
            for run_owner in self.runs.values():
                self.web.assert_worker(run_owner)
            run_owner = self.runs.get(self.command_run_id)
        if self.operation_id == 0:
            return self.web.authorize_worker(self.owner)
        operation = self.web.authorize_effect(self.operation_id, owner=self.owner,
                                              generation=self.generation, run_owner=run_owner)
        if any(operation[key] != value for key, value in self.request_identity.items()):
            raise OwnershipError("worker ownership request identity changed")
        return operation

    def validate_configuration(self, path: str | Path) -> None:
        """@brief Refuse a recycled profile name resolving to another config file."""
        from adore.profiles import ProfileStore

        operation = self.authorize()
        expected = ProfileStore(self.web.path.parent).config_path(operation["project"])
        if Path(path).resolve() != expected.resolve():
            raise OwnershipError("worker ownership configuration target changed")

    def bind_engine(self, engine) -> None:
        """@brief Fence state writes, external Git/forge commands and job boundaries."""
        self.authorize()
        engine.before_effect = self.authorize
        engine.run_scope = self.run_scope
        engine.run_available = self.run_available
        engine.owned_run_id = self.owner.run_id if self.owner.role == "run" else ""
        engine.store.before_write = self.authorize
        for collaborator in (engine.forge, engine.worktrees, engine.containers):
            original = getattr(collaborator, "runner", None)
            if original is not None:
                collaborator.runner = self._runner(original)
        if self.authorize()["action"] == "start":
            engine.on_admitted = self.admitted

    def run_available(self, run_id: str) -> bool:
        """@brief Protect durable foreign owners even across lock/dispatch gaps.
        @param[in] run_id Exact run identity considered by the conductor.
        @return Whether no foreign durable owner prevents entering the run scope.
        @note Stale heartbeats and unavailable process probes retain ownership.
        """
        self.authorize()
        with self.lock:
            if run_id in self.runs or self.owner.role == "run" and self.owner.run_id == run_id:
                return True
        self.web.recover_interrupted(project_id=self.owner.project_id, role="run")
        return not self.web.worker_heartbeats(role="run", project_id=self.owner.project_id,
                                               run_id=run_id)

    def _own_run(self, run_id: str) -> None:
        """@brief Claim actual execution of a job before acknowledgement or conduction."""
        with self.lock:
            if run_id not in self.runs:
                if self.owner.role == "run":
                    if self.owner.run_id != run_id:
                        raise OwnershipError("worker ownership run target mismatch")
                    self.web.assert_worker(self.owner)
                    self.runs[run_id] = self.owner
                    return
                self.web.recover_interrupted(project_id=self.owner.project_id, role="run")
                self.runs[run_id] = self.web.register_worker(
                    "run", project_id=self.owner.project_id, run_id=run_id)

    def admitted(self, run) -> None:
        """@brief Own the durable admitted job before confirming its Start operation."""
        self.authorize()
        self._own_run(run.run_id)
        self.web.acknowledge_start(self.operation_id, owner=self.owner,
                                   generation=self.generation, run_id=run.run_id,
                                   run_owner=self.runs[run.run_id])

    @contextmanager
    def run_scope(self, run_id: str):
        """@brief Publish explicit ownership during conduction or publication of one run."""
        self.authorize()
        with self.lock:
            already_owned = run_id in self.runs
            self._own_run(run_id)
        try:
            yield
        finally:
            if not already_owned:
                with self.lock:
                    if self.runs[run_id] != self.owner:
                        self.web.clear_worker(self.runs[run_id])
                    del self.runs[run_id]

    def heartbeat(self) -> None:
        """@brief Refresh the attached CLI and every actual run it owns."""
        try:
            with self.lock:
                self.web.touch_worker(self.owner)
                for run_owner in self.runs.values():
                    if run_owner != self.owner:
                        self.web.touch_worker(run_owner)
        except (OSError, RuntimeError):
            self.heartbeat_failed.set()

    def close(self) -> None:
        """@brief Relinquish completed run scopes while retaining the parent command owner."""
        with self.lock:
            for run_owner in self.runs.values():
                if run_owner != self.owner:
                    self.web.clear_worker(run_owner)
            self.runs.clear()

    def validate_command(self, args) -> None:
        """@brief Bind parsed CLI action and target to the immutable queued request."""
        operation = self.authorize()
        action, target = operation["action"], operation["run_id"]
        if action == "conduct":
            if (self.owner.role != "run" or self.operation_id != 0
                    or args.command != "conduct" or args.run_id != self.owner.run_id
                    or getattr(args, "profile", None) != operation["project"]
                    or getattr(args, "config", None)):
                raise OwnershipError("worker ownership run command mismatch")
            return
        command = ("run" if action in ("start", "poll") else
                   "profile" if action == "delete" else action)
        if args.command != command or getattr(args, "config", None):
            raise OwnershipError("worker ownership command mismatch")
        if action == "delete":
            valid = (getattr(args, "profile_action", None) == "delete"
                     and getattr(args, "name", None) == operation["project"]
                     and args.force and args.remove_resources
                     and bool(args.remove_clone) == (target == "remove-clone"))
        else:
            valid = getattr(args, "profile", None) == operation["project"]
        if action == "start":
            valid = (valid and str(getattr(args, "ticket", None)) == target
                     and args.once and not args.loop and not args.dry_run)
        elif action == "poll":
            valid = (valid and getattr(args, "ticket", None) is None
                     and args.once and not args.loop and not args.dry_run)
        elif action in ("cancel", "retry"):
            valid = valid and getattr(args, "run_id", None) == target
        elif action == "restart":
            valid = (valid and target == getattr(args, "run_id", "") + "."
                     + (getattr(args, "expected_revision", "") or ""))
        if not valid:
            raise OwnershipError("worker ownership target mismatch")
        if action in ("retry", "restart"):
            # Own reset/teardown too, before constructing or invoking the engine.
            self._own_run(args.run_id)
            self.authorize()

    def _runner(self, original):
        """@brief Preserve injected command contracts behind current ownership checks."""
        def run(*args, **kwargs):
            """@brief Check authority immediately before dispatching an external command."""
            self.authorize()
            return original(*args, **kwargs)
        return run


# PUBLIC API
def current_context() -> WorkerContext | None:
    """@brief Return the active CLI context; standalone CLI has no web dependency."""
    return _CURRENT.get()


@contextmanager
def attached_context():
    """@brief Attach a strictly parsed internal claim before CLI dispatch.
    @exception OwnershipError Missing, malformed, stale or mismatched process context.
    """
    raw = os.environ.get("ADORE_WORKER_CONTEXT")
    if raw is None:
        yield None
        return
    from adore.util import strict_json_loads
    from adore.web.store import WebStore

    try:
        if len(raw) > 2048 or not os.environ.get("ADORE_HOME"):
            raise ValueError("invalid context")
        value = strict_json_loads(raw)
        if (not isinstance(value, dict) or set(value) != {
                "owner_id", "owner_generation", "role", "project_id", "run_id",
                "operation_id", "generation"}
                or type(value["owner_generation"]) is not int or value["owner_generation"] < 1
                or any(type(value[key]) is not int or value[key] < 0
                       for key in ("operation_id", "generation"))
                or (value["operation_id"] == 0) != (value["generation"] == 0)):
            raise ValueError("invalid context")
        owner = WorkerOwner(value["owner_id"], value["owner_generation"], value["role"],
                            value["project_id"], value["run_id"])
        database = Path(os.environ["ADORE_HOME"]) / "web.db"
        if not database.is_file():
            raise OwnershipError("worker ownership store is missing")
        web = WebStore(database)
        web.attach_worker(owner)
        context = WorkerContext(web, owner, value["operation_id"], value["generation"])
        context.authorize()
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise OwnershipError("invalid worker ownership context") from exc
    token = _CURRENT.set(context)
    done = Event()

    def beat() -> None:
        """@brief Keep scoped child readiness current during blocking executor calls."""
        while not done.wait(2):
            context.heartbeat()
            if context.heartbeat_failed.is_set():
                return

    heartbeat = Thread(target=beat, daemon=True)
    heartbeat.start()
    try:
        yield context
    finally:
        done.set()
        heartbeat.join(timeout=3)
        try:
            context.close()
        finally:
            _CURRENT.reset(token)


# END OF FILE
