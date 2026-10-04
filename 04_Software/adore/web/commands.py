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
         stopped worker marks in-flight commands uncertain instead of replaying
         a possible forge or container side effect.
"""

from __future__ import annotations

# IMPORTS
import argparse
from collections.abc import Callable
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread
import time

from adore.config import load_config
from adore.profiles import ProfileError, ProfileStore
from adore.state import StateError, StateStore
from adore.web.store import WebStore, WebStoreError

# DATA MODELS / TYPEDEFINITIONS
Runner = Callable[[list[str], dict[str, str]], int]


# HELPER FUNCTIONS
def _run(argv: list[str], env: dict[str, str]) -> int:
    """@brief Run a fixed CLI argument vector with a finite timeout."""
    try:
        result = subprocess.run(
            argv, env=env, capture_output=True, text=True,
            check=False, timeout=21600,
        )
    except subprocess.TimeoutExpired:
        return 124
    return result.returncode


# PUBLIC API
class CommandWorker:
    """@brief Execute authorized persisted commands through ADORE's CLI."""

    def __init__(self, profiles: ProfileStore, web: WebStore,
                 runner: Runner = _run) -> None:
        self.profiles = profiles
        self.web = web
        self.runner = runner
        self.environment = {**os.environ, "ADORE_HOME": str(profiles.home)}

    def run_pending(self) -> int:
        """@brief Execute at most one pending command; return 1 if claimed."""
        operation = self.web.claim_next()
        if operation is None:
            return 0
        actor = self.web.user_by_id(operation["actor_id"])
        project = operation["project"]
        try:
            grants = (self.web.memberships(actor["id"])
                      if actor is not None and actor["role"] != "admin" else set())
        except WebStoreError:
            self.web.finish(operation["id"], "failed", "project grants are corrupt")
            return 1
        if (actor is None or actor["disabled"] or not self.profiles.exists(project)
                or (actor["role"] != "admin" and project not in grants)):
            self.web.finish(operation["id"], "failed", "permission or project revoked")
            return 1
        try:
            profile = self.profiles.load(project)
            if profile.project_id != operation["project_id"]:
                self.web.finish(operation["id"], "failed", "project identity changed")
                return 1
            if operation["action"] == "delete":
                if actor["role"] != "admin" or not profile.archived:
                    self.web.finish(operation["id"], "failed",
                                    "delete requires an administrator and an archived project")
                    return 1
            elif profile.archived:
                self.web.finish(operation["id"], "failed", "project archived")
                return 1
        except ProfileError:
            self.web.finish(operation["id"], "failed", "project metadata corrupt")
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
                self.web.finish(operation["id"], "failed", "run is unavailable")
                return 1
            if run.lifecycle == "cancelled":
                self.web.finish(operation["id"], "succeeded", "run cancelled")
                self.web.audit(actor["id"], "operation-finished", project,
                               "cancel:succeeded")
                return 1
            if run.lifecycle in ("done", "failed", "handoff-pending", "handed-off"):
                self.web.finish(operation["id"], "failed", "run already finished")
                return 1
        if action == "delete" and not target:
            argv = [sys.executable, "-m", "adore", "profile", "delete", project,
                    "--force", "--remove-resources"]
        elif action == "start" and target.isdigit() and int(target) > 0:
            argv.extend(["run", "--once", "--ticket", target])
        elif action in ("retry", "cancel") and target:
            argv.extend([action, target])
        elif action in ("pause", "resume") and actor["role"] == "admin" and not target:
            argv.append(action)
        else:
            self.web.finish(operation["id"], "failed", "invalid operation")
            return 1
        try:
            code = self._run_with_cancel_watch(argv)
        except Exception:  # noqa: BLE001 - unexpected outcome needs reconciliation
            self.web.finish(operation["id"], "uncertain", "worker invocation failed")
            return 1
        status = "uncertain" if code == 124 else "succeeded" if code == 0 else "failed"
        result = (
            "completed" if code == 0 else
            "outcome uncertain" if code == 124 else "engine rejected operation"
        )
        self.web.finish(operation["id"], status, result)
        self.web.audit(actor["id"], "operation-finished", project,
                       f"{action}:{status}")
        if action == "delete" and status == "succeeded":
            self.web.audit(actor["id"], "project-deleted", project)
        return 1

    def _signal_pending_cancels(self) -> None:
        """@brief Recheck grants before signalling any active conductor."""
        for operation in self.web.pending_cancels():
            project = operation["project"]
            actor = self.web.user_by_id(operation["actor_id"])
            if actor is None or actor["disabled"] or not self.profiles.exists(project):
                continue
            try:
                if actor["role"] != "admin" and project not in self.web.memberships(
                    actor["id"]
                ):
                    continue
                profile = self.profiles.load(project)
                if profile.project_id != operation["project_id"]:
                    continue
                state = StateStore(
                    profile.store_root or self.profiles.default_store_root(project)
                )
                state.request_cancel(operation["run_id"])
            except (WebStoreError, ProfileError, FileNotFoundError, StateError, OSError):
                # The claimed command will report the unavailable run or state.
                continue

    def _run_with_cancel_watch(self, argv: list[str]) -> int:
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

        watcher = Thread(target=watch, daemon=True)
        watcher.start()
        try:
            return self.runner(argv, self.environment)
        finally:
            done.set()
            watcher.join(timeout=2)

    def poll_project(self, project: str) -> int:
        """@brief Poll one project while watching for newly authorized cancels."""
        argv = [sys.executable, "-m", "adore", "--profile", project,
                "run", "--once"]
        return self._run_with_cancel_watch(argv)

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
                    self.web.touch_worker()
                except (WebStoreError, OSError):
                    heartbeat_failed.set()
                    return

        next_poll: dict[str, float] = {}
        try:
            self.web.recover_interrupted()
            self.web.touch_worker()
            heartbeat_started = True
            heartbeat_thread = Thread(target=beat, daemon=True)
            heartbeat_thread.start()
            while not stop.is_set():
                if heartbeat_failed.is_set():
                    raise RuntimeError("web control worker heartbeat failed")
                if self.run_pending():
                    continue
                now = time.monotonic()
                for profile in self.profiles.list_profiles():
                    if profile.archived:
                        continue
                    if next_poll.get(profile.name, 0.0) > now:
                        continue
                    try:
                        config = load_config(self.profiles.config_path(profile.name))
                        cadence = max(5, config.polling.poll_interval_seconds)
                    except (OSError, ValueError):
                        cadence = 60
                    next_poll[profile.name] = now + cadence
                    self.poll_project(profile.name)
                    break
                stop.wait(interval)
        finally:
            heartbeat_done.set()
            if heartbeat_thread is not None:
                heartbeat_thread.join(timeout=heartbeat_interval + 1)
            try:
                if heartbeat_started:
                    self.web.clear_worker()
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
