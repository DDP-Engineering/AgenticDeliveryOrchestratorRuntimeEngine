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
@file    supervisor_helper.py
@brief   Offline real-process conductor helper with injected forge/Git/executor.
@details Exercises product admission, conduction, durable ownership and locks;
         its fake executor waits at an explicit file barrier for at most 30 s.
"""

from __future__ import annotations

# IMPORTS
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import time

from adore.config import load_config
from adore.orchestrator import Orchestrator
from adore.profiles import ProfileStore
from adore.state import StateStore
from adore.web.ownership import process_birth
from adore.web.processes import assert_ancestry
from adore.web.store import WebStore
from adore.web.worker_context import WorkerContext

from tests.test_orchestrator import (
    DirectExecutor,
    FakeContainers,
    FakeForge,
    FakeWorktrees,
    direct_edit,
)


# PUBLIC API
def offline_engine(profiles: ProfileStore, name: str):
    """@brief Construct real product behavior with offline external collaborators."""
    config = load_config(profiles.config_path(name))
    forge, trees, executor = FakeForge(), FakeWorktrees(), DirectExecutor()
    forge.ticket.labels = [config.labels.lifecycle.ready, "P1"]
    trees.repo_path = Path(config.worktree.repo_path)

    def path_for(run_id):
        """@brief Give concurrent fake Git worktrees distinct real exchange directories."""
        path = Path(config.worktree.root) / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    trees.path_for = path_for
    engine = Orchestrator(config, forge, StateStore(config.state.store_root), trees,
                          FakeContainers(), executor, sleep=lambda _: None, log=lambda _: None)
    return engine, forge, trees, executor


def main() -> int:
    """@brief Conduct one real reserved job through a bounded observable fake executor."""
    if sys.argv[1] == "command":
        return command_main()
    home, project_id, run_id, revision = sys.argv[1:]
    profiles = ProfileStore(home)
    profile = profiles.find_by_id(project_id)
    engine, forge, trees, executor = offline_engine(profiles, profile.name)
    web = WebStore(profiles.home / "web.db")
    owner = web.register_worker("run", project_id=project_id, run_id=run_id)
    context = WorkerContext(web, owner, 0, 0)
    context.bind_engine(engine)
    run = engine.store.load(run_id)
    forge.ticket = replace(forge.ticket, iid=run.ticket_iid)
    records = profiles.home / "barriers"
    records.mkdir(exist_ok=True)

    def blocked(root):
        """@brief Actual independently scheduled executor overlap is externally observable."""
        marker = records / (project_id + "-" + run_id)
        marker.write_text(json.dumps({"pid": os.getpid(), "birth": process_birth(os.getpid()),
                                      "entered": time.monotonic()}), encoding="utf-8")
        deadline = time.monotonic() + 30
        while not marker.with_suffix(".release").exists():
            assert_ancestry()
            if time.monotonic() >= deadline:
                raise RuntimeError("offline executor barrier timed out")
            time.sleep(0.02)
        result = direct_edit(trees)(root)
        marker.with_suffix(".ended").write_text(str(time.monotonic()), encoding="ascii")
        return result

    executor.attempts.append(blocked)
    try:
        return 0 if engine.conduct_run(run_id, config_revision=revision) else 1
    finally:
        context.close()
        web.clear_worker(owner)


def command_main() -> int:
    """@brief Run the production transient command lifetime with a fake blocking engine."""
    from adore.web.commands import CommandOutcome, CommandWorker
    import adore.web.supervisor as module

    _, _, home, project_id, release_path, entered_path = sys.argv
    profiles = ProfileStore(home)
    profile = profiles.find_by_id(project_id)

    def runner(argv, environment):
        """@brief Block Retry until Cancel was claimed by the real watcher thread."""
        state = StateStore(profile.store_root)
        run = state.load("job-42")
        run.lifecycle = "working"
        state.save(run)
        Path(entered_path).touch()
        deadline = time.monotonic() + 30
        while not Path(release_path).exists():
            assert_ancestry()
            if time.monotonic() >= deadline:
                raise RuntimeError("command barrier timed out")
            time.sleep(0.02)
        run = state.load("job-42")
        run.lifecycle = "cancelled"
        state.save(run)
        return CommandOutcome(1, "fake retry stopped")

    def factory(profiles, web, **kwargs):
        return CommandWorker(profiles, web, runner=runner, **kwargs)

    module.CommandWorker = factory
    sys.argv = ["owned-command", "--home", home, "--role", "command",
                "--project-id", project_id]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())

# END OF FILE
