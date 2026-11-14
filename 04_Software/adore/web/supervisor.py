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
@file    supervisor.py
@brief   Single-home supervisor, independent project schedulers and run processes.
@details Event loops only inspect/dispatch children. Each conductor builds its
         own collaborators and is bound to one immutable project/run and config
         revision. Shared database locks never span a process wait.
"""

from __future__ import annotations

# IMPORTS
import argparse
from contextlib import contextmanager, suppress
from dataclasses import asdict
from hashlib import sha256
import json
import logging
import os
from pathlib import Path
import re
import signal
import sys
from threading import Event, Thread
import time

from adore.capacity import admission_limit
from adore.config import load_config, validate_config
from adore.polling import PollCadence
from adore.profiles import ProfileError, ProfileStore
from adore.state import StateError, StateStore
from adore.util import in_quiet_hours, strict_json_loads
from adore.web.commands import CommandWorker, _run
from adore.web.ownership import OwnershipError, WorkerOwner
from adore.web.processes import ProcessTree, assert_ancestry, stop_trees
from adore.web.store import WebStore

# CONSTANTS
LOG = logging.getLogger(__name__)
_EXECUTION = ("start", "retry", "restart", "cancel")
_CONFIGURATION = ("pause", "resume", "delete")
_OWNER = "ADORE_PROJECT_COMMAND_OWNER"


# LOCAL HELPERS
def _environment(profiles: ProfileStore) -> dict[str, str]:
    """@brief Build noninteractive UTF-8 worker environment for this home."""
    result = {**os.environ, "ADORE_HOME": str(profiles.home), "PYTHONUNBUFFERED": "1",
              "PYTHONIOENCODING": "utf-8"}
    result.pop("ADORE_WORKER_CONTEXT", None)
    result.pop(_OWNER, None)
    return result


def _argv(role: str, home: Path, *extra: str) -> list[str]:
    return [sys.executable, "-m", "adore.web.supervisor", "--role", role,
            "--home", str(home), *extra]


@contextmanager
def _heartbeat(web: WebStore, owner: WorkerOwner):
    """@brief Keep a blocking command/run's identity visible and fail closed on errors."""
    done = Event()
    failed = Event()

    def beat() -> None:
        """@brief Heartbeat only this role; unknown parent/storage state stops authority."""
        while not done.wait(1):
            try:
                assert_ancestry()
                web.touch_worker(owner)
            except (OSError, RuntimeError):
                failed.set()
                return

    thread = Thread(target=beat, daemon=True)
    thread.start()
    try:
        yield failed
    finally:
        done.set()
        thread.join(timeout=2)


# PUBLIC API
class Supervisor:
    """@brief Discover and supervise immutable project IDs without waiting on jobs."""

    def __init__(self, profiles: ProfileStore, web: WebStore, *, spawn=ProcessTree,
                 clock=time.monotonic) -> None:
        self.profiles, self.web, self.spawn, self.clock = profiles, web, spawn, clock
        self.children: dict[str, ProcessTree] = {}
        self.names: dict[str, str] = {}
        self.retry_at: dict[str, float] = {}
        self.failures: dict[str, int] = {}
        self.retiring: dict[str, tuple[ProcessTree, float]] = {}
        self.owner: WorkerOwner | None = None

    def tick(self) -> None:
        """@brief Reconcile child exits/discovery with no blocking process waits.
        @note Child failure backs off only that scope. Configuration is independent.
        """
        assert_ancestry()
        now = self.clock()
        listed = self.profiles.list_profiles()
        if len({p.project_id for p in listed}) != len(listed):
            raise ProfileError("duplicate project identities prevent safe supervision")
        profiles = {p.project_id: p for p in listed if not p.archived}
        wanted = {identity: p.name for identity, p in profiles.items()}
        wanted["configuration"] = ""
        for identity, child in list(self.children.items()):
            if identity not in wanted or self.names.get(identity) != wanted[identity]:
                child.request_stop()
                self.retiring[identity] = (child, now + 2)
                del self.children[identity]
            elif child.poll() is not None:
                try:
                    child.kill()
                    child.close()
                except (OSError, RuntimeError):
                    self.retiring[identity] = (child, now + 5)
                    LOG.exception("worker cleanup retained for %s", identity)
                del self.children[identity]
                count = min(self.failures.get(identity, 0) + 1, 6)
                self.failures[identity] = count
                self.retry_at[identity] = now + min(2 ** (count - 1), 60)
                self.web.recover_interrupted(
                    project_id=None if identity == "configuration" else identity,
                    role="configuration" if identity == "configuration" else "project")
        for identity, (child, deadline) in list(self.retiring.items()):
            if now < deadline:
                continue
            try:
                child.kill()
                if child.poll() is None:
                    continue
                child.close()
            except (OSError, RuntimeError):
                self.retiring[identity] = (child, now + 5)
                LOG.exception("worker cleanup retained for %s", identity)
                continue
            del self.retiring[identity]
        for identity, name in wanted.items():
            if (identity in self.children or identity in self.retiring
                    or now < self.retry_at.get(identity, 0)):
                continue
            try:
                role = "configuration" if identity == "configuration" else "project"
                extra = () if role == "configuration" else ("--project-id", identity)
                self.children[identity] = self.spawn(
                    _argv(role, self.profiles.home, *extra), _environment(self.profiles))
                self.names[identity] = name
            except (OSError, RuntimeError):
                self.retry_at[identity] = now + 5
                LOG.exception("worker launch refused for %s", identity)

    def run_forever(self, *, stop: Event | None = None, interval: float = 0.2) -> None:
        """@brief Own one home and bound shutdown of every owned child scope."""
        stop = stop or Event()
        lock = StateStore(self.profiles.home / "web-control", "adore-web")
        if not lock.acquire_lock():
            raise OwnershipError("another web supervisor is active in this ADORE home")
        try:
            self.web.recover_interrupted(role="supervisor")
            self.owner = self.web.register_worker("supervisor")
            while not stop.is_set():
                self.web.touch_worker(self.owner)
                self.tick()
                rows = self.web.worker_heartbeats()
                busy = any(row["ready"] and row["activity"] == "busy"
                           for row in rows if row["role"] != "supervisor")
                self.web.set_worker_activity(self.owner, "busy" if busy else "idle")
                stop.wait(interval)
        finally:
            try:
                stop_trees([*self.children.values(),
                            *(child for child, _ in self.retiring.values())])
                self.web.recover_interrupted()
                if self.owner is not None:
                    with suppress(OwnershipError):
                        self.web.clear_worker(self.owner)
            finally:
                lock.release_lock()


class ProjectWorker:
    """@brief Schedule one project's admission, commands and N owned run processes."""

    def __init__(self, profiles: ProfileStore, web: WebStore, project_id: str, *,
                 spawn=ProcessTree, clock=time.monotonic) -> None:
        self.profiles, self.web, self.project_id = profiles, web, project_id
        self.spawn, self.clock = spawn, clock
        self.owner: WorkerOwner | None = None
        self.children: dict[str, ProcessTree] = {}
        self.started: dict[str, float] = {}
        self.next_run: dict[str, float] = {}
        self.next_poll = 0.0
        self.cadence = PollCadence()
        self.config = None
        self.revision = ""
        self.name = ""

    def tick(self) -> bool:
        """@brief Dispatch only this identity; return False if archived/deleted/renamed.
        @exception StateError Corrupt state blocks dispatch instead of granting capacity.
        """
        assert_ancestry()
        profile = self.profiles.find_by_id(self.project_id)
        if profile is None or profile.archived or self.name and profile.name != self.name:
            return False
        self.web.authorize_worker(self.owner)
        self.web.recover_interrupted(project_id=self.project_id, role="command")
        self.name = profile.name
        source = self.profiles.config_path(profile.name)
        revision = sha256(source.read_bytes()).hexdigest()
        if revision != self.revision:
            config = load_config(source)
            if validate_config(config):
                raise StateError("invalid project configuration; dispatch refused")
            PollCadence.validate(config.polling)
            self.config, self.revision = config, revision
        config = self.config
        state = StateStore(profile.store_root or self.profiles.default_store_root(profile.name))
        now = self.clock()
        for key, child in list(self.children.items()):
            code = child.poll()
            if code is None:
                # A blocked admission/command has a finite independent budget;
                # it cannot hold polling or progress in another project.
                if now - self.started[key] > 21600:
                    child.request_stop()
                    child.kill()
                continue
            child.kill()
            child.close()
            del self.children[key]
            self.next_run[key] = now + config.polling.poll_interval_seconds
            if key == "poll":
                self.next_poll = now + self.cadence.next_delay(config.polling, failed=code != 0)
        self.web.recover_interrupted(project_id=self.project_id, role="run")
        if state.invalid_runs():
            raise StateError("corrupt run state prevents project dispatch")
        runs = state.list_runs()
        limit = admission_limit(config)
        occupied = state.execution_slots() | {
            run.run_id for run in runs if run.lifecycle in ("working", "handoff-pending")
            or run.lifecycle == "parked-clarification" and run.parked_polls == 0}
        capacity = len(occupied) < limit
        environment = _environment(self.profiles)
        environment[_OWNER] = json.dumps(asdict(self.owner))
        if "command" not in self.children:
            actions = _EXECUTION if capacity else ("cancel",)
            if any(domain == "execution" and identity == self.project_id
                   for domain, identity in self.web.pending_domains(actions=actions)):
                self._launch("command", _argv("command", self.profiles.home,
                    "--project-id", self.project_id, "--actions", ",".join(actions)), environment)
        active_owners = {row["run_id"] for row in self.web.worker_heartbeats(
            role="run", project_id=self.project_id)}
        active = sum(key.startswith("run:") for key in self.children)
        # Initial reservations take precedence over periodic parked/review checks.
        for run in sorted(runs, key=lambda item: (item.lifecycle != "working",
                          self.next_run.get("run:" + item.run_id, 0), item.run_id)):
            key = "run:" + run.run_id
            if (active >= limit or key in self.children or run.run_id in active_owners
                    or self.next_run.get(key, 0) > now
                    or run.lifecycle in ("done", "failed", "cancelled", "handed-off")
                    and not run.notification_outbox):
                continue
            run_revision = revision
            if run.lifecycle == "working" and run.execution_pending:
                dispatch = state.load_dispatch(run.run_id)
                run_revision = dispatch["config_revision"]
            self._launch(key, _argv("run", self.profiles.home, "--project-id", self.project_id,
                         "--run-id", run.run_id, "--revision", run_revision), environment)
            active += 1
        if "poll" not in self.children and now >= self.next_poll:
            if in_quiet_hours(config.polling.quiet_hours):
                self.next_poll = now + self.cadence.next_delay(config.polling, failed=None)
            elif not state.is_paused() and capacity:
                self._launch("poll", _argv("poll", self.profiles.home,
                             "--project-id", self.project_id), environment)
        self.web.set_worker_activity(self.owner, "busy" if self.children else "idle")
        self.web.touch_worker(self.owner)
        return True

    def _launch(self, key: str, argv: list[str], environment: dict[str, str]) -> None:
        """@brief Track process ownership before considering more work next tick."""
        self.children[key] = self.spawn(argv, environment)
        self.started[key] = self.clock()

    def run_forever(self, *, stop: Event | None = None, interval: float = 0.2) -> None:
        """@brief Recover only this project's dead owner and run an independent loop."""
        stop = stop or Event()
        self.web.recover_interrupted(project_id=self.project_id, role="project")
        self.owner = self.web.register_worker("project", project_id=self.project_id)
        try:
            while not stop.is_set():
                try:
                    if not self.tick():
                        break
                except OwnershipError:
                    raise
                except (StateError, ProfileError, OSError, ValueError, TypeError):
                    LOG.exception("project dispatch refused for %s", self.project_id)
                    stop.wait(2)
                stop.wait(interval)
        finally:
            stop_trees(list(self.children.values()))
            self.web.recover_interrupted(project_id=self.project_id, role="run")
            with suppress(OwnershipError):
                self.web.clear_worker(self.owner)


def configuration_loop(profiles: ProfileStore, web: WebStore, stop: Event) -> None:
    """@brief Run bounded configuration lanes and immediate admission control independently."""
    from concurrent.futures import ThreadPoolExecutor

    from adore.web.app import create_app
    from adore.web.configuration import ConfigurationWorker

    web.recover_interrupted(role="configuration")
    owner = web.register_worker("configuration")
    app = create_app(profiles.home)
    worker = ConfigurationWorker(app.state.configuration_tasks, owner=owner)
    deletion = CommandWorker(profiles, web, domains=("configuration_project",), actions=("delete",))
    deletion._supervisor = owner
    pool = ThreadPoolExecutor(1)
    future = None
    try:
        with _heartbeat(web, owner) as failed:
            while not stop.is_set():
                assert_ancestry()
                if failed.is_set():
                    raise OwnershipError("configuration worker heartbeat failed")
                worker.tick()
                if future is None or future.done():
                    if future is not None:
                        future.result()
                    future = pool.submit(deletion.run_pending)
                stop.wait(0.05)
    finally:
        pool.shutdown(wait=True)
        worker.close()
        for scoped in deletion._owners.values():
            with suppress(OwnershipError):
                web.clear_worker(scoped)


def main() -> int:
    """@brief Internal fixed-role entry; runs attach before constructing any engine."""
    parser = argparse.ArgumentParser(description="ADORE owned worker process")
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--role", choices=("project", "configuration", "command", "poll", "run"),
                        required=True)
    parser.add_argument("--project-id", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--revision", default="")
    parser.add_argument("--actions", default=",".join(_EXECUTION))
    args = parser.parse_args()
    assert_ancestry()
    profiles = ProfileStore(args.home)
    web = WebStore(profiles.home / "web.db")
    stop = Event()
    for name in ("SIGTERM", "SIGINT", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: stop.set())
    if args.role == "configuration":
        configuration_loop(profiles, web, stop)
        return 0
    if not re.fullmatch(r"[a-f0-9]{32}", args.project_id):
        raise OwnershipError("invalid project worker identity")
    if args.role == "project":
        ProjectWorker(profiles, web, args.project_id).run_forever(stop=stop)
        return 0
    profile = profiles.find_by_id(args.project_id)
    if profile is None or profile.archived:
        raise OwnershipError("project worker target unavailable")
    if args.role == "run":
        if not re.fullmatch(r"[a-f0-9]{64}", args.revision):
            raise OwnershipError("invalid run configuration revision")
        web.recover_interrupted(project_id=args.project_id, role="run")
        owner = web.register_worker("run", project_id=args.project_id, run_id=args.run_id)
    elif args.role == "command":
        web.recover_interrupted(project_id=args.project_id, role="command")
        owner = web.register_worker("command", project_id=args.project_id)
    else:
        try:
            owner = WorkerOwner(**strict_json_loads(os.environ[_OWNER]))
        except (KeyError, ValueError, TypeError) as exc:
            raise OwnershipError("invalid project command ownership") from exc
        if owner.role != "project" or owner.project_id != args.project_id:
            raise OwnershipError("project command ownership mismatch")
        web.attach_worker(owner)
    try:
        with _heartbeat(web, owner) as failed:
            if args.role == "command":
                actions = tuple(args.actions.split(","))
                if not actions or any(action not in _EXECUTION for action in actions):
                    raise OwnershipError("invalid project command actions")
                worker = CommandWorker(profiles, web, project_id=args.project_id,
                    domains=("execution",), actions=actions, execution_owner=owner, admit_only=True)
                worker.run_pending()
                # A cancellation claimed by the watcher belongs to this process,
                # not the long-lived project scheduler. Settle bounded follow-up
                # claims before exit; anything left becomes uncertain after death.
                for _ in range(32):
                    if not worker._cancel_claims:
                        break
                    worker.run_pending()
                return 1 if failed.is_set() else 0
            context = json.dumps({"owner_id": owner.id, "owner_generation": owner.generation,
                "role": owner.role, "project_id": owner.project_id, "run_id": owner.run_id,
                "operation_id": 0, "generation": 0})
            env = _environment(profiles)
            env["ADORE_WORKER_CONTEXT"] = context
            argv = [sys.executable, "-m", "adore", "--profile", profile.name]
            argv.extend(["conduct", args.run_id, "--config-revision", args.revision]
                        if args.role == "run" else ["run", "--once", "--admit-only"])
            outcome = _run(argv, env)
            return 1 if failed.is_set() else outcome.code
    finally:
        if args.role in ("run", "command"):
            with suppress(OwnershipError):
                web.clear_worker(owner)


if __name__ == "__main__":
    raise SystemExit(main())

# END OF FILE
