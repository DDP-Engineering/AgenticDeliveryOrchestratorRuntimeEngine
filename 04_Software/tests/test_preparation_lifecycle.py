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
@file    test_preparation_lifecycle.py
@brief   Public preparation failure, replay and resource recovery contracts.
@details Every source/runtime/gate boundary is injected; tests remain offline.
"""

# IMPORTS
import json
from types import SimpleNamespace

from adore import orchestrator as module
from adore.executor.base import GateRun
from adore.isolation import IsolationError
from adore.util import CommandResult
import pytest

from tests.test_orchestrator import TASK_ID, FakeAegis, FakeExecutor, make_engine, make_run, task
from tests.test_preparation import SourceRunner

# LOCAL HELPERS


def recipe_engine(tmp_path, monkeypatch, failure="exit"):
    """@brief Build an injected public conductor with controllable setup outcomes."""
    engine, _, worktrees, containers, _ = make_engine(
        tmp_path,
        executor=FakeExecutor(
            GateRun(exit_code=0, has_questions=True, questions="Operator question")
        ),
    )
    engine.config.execution.preparation = "prepare.yml#setup@" + "a" * 40
    engine.config.worktree.repo_path = str(tmp_path)
    worktrees.repo_path = tmp_path
    worktrees.create = lambda *args: tmp_path
    worktrees.path_for = lambda _: tmp_path
    worktrees.runner = SourceRunner()
    control = {"failure": failure, "cid": "d" * 64, "calls": [], "gates": 0}

    def identity(_):
        """@brief Return authoritative current IDs or a missing resource failure."""
        if control["cid"] is None:
            raise IsolationError("missing")
        return {
            "container_id": control["cid"],
            "image_id": "sha256:" + "e" * 64,
            "status": containers.status_value,
        }

    containers.resource_identity = identity
    containers.image_identity = lambda _: "sha256:" + "e" * 64
    containers.status = lambda _: "running" if control["cid"] else "absent"

    def remove(name):
        """@brief Explicit removal releases only the owned fake container."""
        containers.removed.append(name)
        control["cid"] = "f" * 64

    containers.remove = remove

    def execute(name, argv, **kwargs):
        """@brief Write bounded runner evidence without any subprocess."""
        if argv[0] != "python3":
            return CommandResult()
        control["calls"].append(argv)
        directory = (
            engine.store.run_dir("github-owner-repo-7") / "io" / argv[3].split("/adore/io/")[1]
        )
        (directory / "stdout.txt").write_text("")
        (directory / "stderr.txt").write_text("")
        mode = control["failure"]
        if mode == "streams":
            (directory / "stdout.txt").unlink()
        code = 1 if mode == "exit" else 124 if mode in {"timeout", "exit124"} else 0
        if mode == "cancel":
            engine.store.request_cancel("github-owner-repo-7")
        if mode not in {"missing", "timeout", "cancel"}:
            receipt = json.dumps({"exit_code": code, "timed_out": False})
            if mode == "duplicate":
                receipt = '{"exit_code":1,"exit_code":0,"timed_out":false}'
            (directory / "result.json").write_text(receipt)
        return CommandResult(exit_code=code, timed_out=mode == "timeout")

    containers.exec = execute

    class Client(FakeAegis):
        """@brief Count downstream probes only after verified setup succeeds."""

        def __init__(self, *args):
            super().__init__([task("frame")])

        def probe(self):
            control["gates"] += 1
            return SimpleNamespace(version="0.5.0", schema=1)

        def create_task(self, *args):
            return TASK_ID

    monkeypatch.setattr(module, "AegisClient", Client)
    run = make_run(engine)
    run.active_task_id, run.task_ids, run.lifecycle = None, [], "failed"
    engine.store.save(run)
    return engine, run.run_id, control, containers


# PUBLIC API / TESTS


@pytest.mark.parametrize(
    "mode,status",
    [
        ("exit", "failed"),
        ("exit124", "failed"),
        ("timeout", "failed"),
        ("missing", "interrupted"),
        ("duplicate", "interrupted"),
        ("streams", "interrupted"),
        ("cancel", "cancelled"),
    ],
)
def test_setup_failure_retains_outcome_and_never_reaches_ai(tmp_path, monkeypatch, mode, status):
    """@brief Exit, timeout, cancellation and corrupt receipts fail before AI."""
    engine, run_id, control, _ = recipe_engine(tmp_path, monkeypatch, mode)
    assert engine.retry(run_id)
    saved = engine.store.load(run_id)
    assert saved.execution["status"] == status
    assert len(saved.execution["steps"]) == 1
    assert saved.lifecycle == ("cancelled" if mode == "cancel" else "failed")
    assert control["gates"] == 0 and len(control["calls"]) == 1
    evidence = engine.store.run_dir(run_id) / "preparation/attempt-1/step-1.json"
    assert evidence.is_file()
    if mode != "cancel":
        assert engine.retry(run_id)
        assert len(control["calls"]) == 1, "ordinary retry replayed partial setup"


def test_explicit_reprepare_recreates_owned_container_and_caps_replay(tmp_path, monkeypatch):
    """@brief Only explicit bounded replay creates a fresh setup attempt."""
    engine, run_id, control, containers = recipe_engine(tmp_path, monkeypatch)
    assert engine.retry(run_id)
    control["failure"] = "success"
    assert engine.retry(run_id, reprepare=True)
    saved = engine.store.load(run_id)
    assert saved.execution["status"] == "success" and saved.execution["attempts"] == 2
    assert saved.execution["history"][0]["status"] == "failed"
    assert saved.execution["resource"]["container_id"] == "f" * 64
    assert containers.removed == ["d" * 64]
    assert len(control["calls"]) == 3 and control["gates"] == 1
    saved.lifecycle = "failed"
    engine.store.save(saved)
    assert not engine.retry(run_id, reprepare=True)
    assert len(control["calls"]) == 3


@pytest.mark.parametrize(
    "change", ["missing", "replacement", "policy", "plan-file", "step-file", "clone"]
)
def test_success_cannot_authorize_drifted_resources_or_configuration(tmp_path, monkeypatch, change):
    """@brief Saved success never guesses readiness after identity/profile drift."""
    engine, run_id, control, _ = recipe_engine(tmp_path, monkeypatch, "success")
    assert engine.retry(run_id)
    saved = engine.store.load(run_id)
    saved.lifecycle = "failed"
    engine.store.save(saved)
    if change == "missing":
        control["cid"] = None
    elif change == "replacement":
        control["cid"] = "b" * 64
    elif change == "policy":
        engine.config.container.runtime_env["PATH"] = "/different"
    elif change == "clone":
        engine.config.worktree.repo_path = str(tmp_path / "other-clone")
    elif change == "plan-file":
        (engine.store.run_dir(run_id) / "execution-plan.json").write_text("{}")
    else:
        (engine.store.run_dir(run_id) / "preparation/attempt-1/step-1.json").write_text("{}")
    assert engine.retry(run_id)
    assert engine.store.load(run_id).lifecycle == "failed"
    assert len(control["calls"]) == 2 and control["gates"] == 1


def test_crashed_preparation_becomes_explicit_interrupted_evidence(tmp_path, monkeypatch):
    """@brief Stale conductor reconciliation marks unfinished setup interrupted."""
    engine, run_id, control, _ = recipe_engine(tmp_path, monkeypatch)
    assert engine.retry(run_id)
    saved = engine.store.load(run_id)
    saved.lifecycle, saved.execution["status"] = "working", "running"
    engine.store.save(saved)
    state_path = engine.store.run_dir(run_id) / "state.json"
    data = json.loads(state_path.read_text())
    data["updated_at"] = "2026-01-01T00:00:00Z"
    state_path.write_text(json.dumps(data))
    engine.store.pause()
    assert engine.poll_once()["paused"]
    recovered = engine.store.load(run_id)
    assert recovered.lifecycle == "failed"
    assert recovered.execution["status"] == "interrupted"
    assert len(control["calls"]) == 1 and control["gates"] == 0


def test_legacy_retry_keeps_existing_profile_update_contract(tmp_path, monkeypatch):
    """@brief Profiles without recipes retain ordinary recovery and config updates."""
    engine, run_id, control, _ = recipe_engine(tmp_path, monkeypatch, "success")
    engine.config.execution.preparation = ""
    engine.executor.results.append(
        GateRun(exit_code=0, has_questions=True, questions="Operator question")
    )
    assert engine.retry(run_id)
    saved = engine.store.load(run_id)
    saved.lifecycle = "failed"
    engine.store.save(saved)
    engine.config.container.runtime_env["PATH"] = "/updated/operator/path"
    assert engine.retry(run_id)
    recovered = engine.store.load(run_id)
    assert recovered.lifecycle == "parked-clarification"
    assert recovered.execution == {}
    assert control["gates"] == 2 and control["calls"] == []


# END OF FILE
