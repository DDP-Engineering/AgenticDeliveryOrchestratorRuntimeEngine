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
@file    test_retry_revalidation.py
@brief   Explicit native Retry revalidation and honest CLI/worker outcomes.
@details Uses injected process, forge and executor boundaries; never runs host tools.
"""

# IMPORTS
from dataclasses import replace
import json

from adore.executor.base import GateRun
from adore.local_execution import LocalBackend
from adore.preparation import resolve_plan
from adore.state import RunState, StateStore
from adore.util import CommandResult
import pytest

from tests.test_local_execution import local_fixture
from tests.test_orchestrator import FakeAegis, FakeExecutor, make_engine, make_run, task

# LOCAL HELPERS


def retry_fixture(tmp_path, monkeypatch, system="Windows", agent="pi", iid=7):
    """@brief Persist a failed native job with real receipts and injected execution."""
    config, context, _, controller, work = local_fixture(tmp_path, monkeypatch)
    context["system"] = system
    from adore.pi_installation import managed_pi

    binary = managed_pi().node
    config.executor.provider = "openai"
    config.executor.model = "model"
    config.delivery.publish_checkpoints = False
    engine, forge, trees, _, executor = make_engine(
        tmp_path,
        executor=FakeExecutor(
            GateRun(exit_code=0, has_questions=True, questions="Next stage question")
        ),
    )
    config.state.store_root = str(engine.store.root)
    engine.config = config
    engine.backend = LocalBackend(config, context=context, controller=controller)
    trees.repo_path = work
    trees.path_for = lambda _: work
    trees.create = lambda *args: work
    forge.ticket = replace(forge.ticket, iid=iid)
    run = make_run(engine)
    run.run_id = f"{agent}-job-{iid}"
    run.ticket_iid = iid
    run.branch = f"adore/{agent}-{iid}"
    run.worktree = str(work)
    run.lifecycle, run.stage = "failed", "design"
    run.iterations = 3
    io = engine.store.run_dir(run.run_id) / "io"
    engine.backend.provision(run.container, work, work, io, {})
    plan = resolve_plan(config)
    run.execution = {
        "plan": plan,
        "resource": engine.backend.resource_identity(run.container),
        "status": "not-required",
        "attempts": 0,
        "steps": [],
        "history": [],
        "reprepare": False,
    }
    engine.store.save(run)
    engine.store.save_ticket(run.run_id, {"title": "Existing work", "labels": []})
    (io.parent / "execution-plan.json").write_text(
        json.dumps(plan, sort_keys=True, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    before = work / "progress.txt"
    before.write_text("Keep existing implementation", encoding="utf-8")
    resumed = replace(task("specify"), header={**task("specify").header, "branch": run.branch})
    client = FakeAegis([resumed])
    client.probe = lambda: None
    monkeypatch.setattr("adore.orchestrator.AegisClient", lambda *args: client)
    return engine, run, context, controller, binary, work, executor


def upgrade(engine, context, controller, binary):
    """@brief Simulate an ordinary installed CLI update and inherited PATH change."""
    binary.write_bytes(b"updated installed executor binary")
    binary.chmod(0o755)
    context["path"] += (";" if context["system"] == "Windows" else ":") + str(binary.parent / "new")
    engine.backend = LocalBackend(engine.config, context=context, controller=controller)


# PUBLIC CONTRACT TESTS


@pytest.mark.parametrize("system", ["Windows", "Linux"])
@pytest.mark.parametrize("agent,iid", [("pi", 7), ("pi", 91)])
def test_explicit_retry_refreshes_native_tools_without_losing_job(
    tmp_path, monkeypatch, system, agent, iid
):
    """@brief Every supported agent/job can refresh native environment on both OS paths."""
    engine, run, context, controller, binary, work, executor = retry_fixture(
        tmp_path, monkeypatch, system, agent, iid
    )
    previous = run.execution["plan"]["fingerprint"]
    resource = dict(run.execution["resource"])
    upgrade(engine, context, controller, binary)

    engine.store.pause()
    assert engine.retry(run.run_id)
    assert engine.store.is_paused()

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "parked-clarification"
    assert saved.stage == "specify"
    assert saved.active_task_id == run.active_task_id
    assert saved.branch == run.branch and saved.worktree == str(work)
    assert saved.execution["resource"] == resource
    assert saved.iterations == 4
    assert saved.execution["plan"]["fingerprint"] != previous
    assert (work / "progress.txt").read_text() == "Keep existing implementation"
    assert len(executor.prompts) == 1
    assert sum("--version" in argv for argv, _ in controller.calls) == 1
    assert any(
        e["event"] == "native-environment-revalidated"
        for e in engine.store.read_journal(run.run_id)
    )


@pytest.mark.parametrize(
    "change",
    ["account", "host", "target", "receipt", "plan", "missing", "version", "exit", "timeout"],
)
def test_retry_revalidation_refuses_real_failures_without_losing_work(
    tmp_path, monkeypatch, change
):
    """@brief Scope corruption and unavailable executors keep the job/work and actual cause."""
    engine, run, context, controller, binary, work, executor = retry_fixture(tmp_path, monkeypatch)
    upgrade(engine, context, controller, binary)
    if change in {"account", "host"}:
        context[change] = "other-account-or-machine"
        engine.backend = LocalBackend(engine.config, context=context, controller=controller)
    elif change == "target":
        engine.config.delivery.target_branch = "different-target"
    elif change == "receipt":
        (engine.store.run_dir(run.run_id) / "local-control/runtime.json").write_text("{}")
    elif change == "plan":
        (engine.store.run_dir(run.run_id) / "execution-plan.json").write_text("{}")
    elif change == "missing":
        binary.unlink()
    elif change in {"version", "exit", "timeout"}:

        def invalid_version(argv, **_kwargs):
            """@brief Refuse invalid Pi output without launching a tool."""
            return CommandResult(
                stdout="v22.23.4" if len(argv) == 2 else "PRIVATE invalid output",
                exit_code=0 if len(argv) == 2 else 2 if change == "exit" else
                124 if change == "timeout" else 0,
                timed_out=len(argv) != 2 and change == "timeout",
            )

        monkeypatch.setattr("adore.pi_installation.run_command", invalid_version)

    assert engine.retry(run.run_id)

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "failed"
    assert saved.stage == "design"
    assert saved.outcome.startswith(
        "RETRY_REVALIDATION_FAILED:"
        if change not in {"version", "exit", "timeout"}
        else "INFRASTRUCTURE_EXHAUSTED:"
    )
    if change in {"version", "exit", "timeout"}:
        assert {"version": "wrong version", "exit": "exit 2", "timeout": "timed out"}[
            change
        ] in saved.outcome
    if change == "missing":
        assert "Node 22.23.4" in saved.outcome
    assert not executor.prompts
    assert saved.active_task_id == run.active_task_id
    assert (work / "progress.txt").is_file()
    assert "PRIVATE" not in saved.outcome


def test_automatic_poll_does_not_refresh_failed_native_jobs(tmp_path, monkeypatch):
    """@brief Revalidation is an explicit Retry action rather than an automatic bypass."""
    engine, run, context, controller, binary, _, executor = retry_fixture(tmp_path, monkeypatch)
    upgrade(engine, context, controller, binary)
    snapshot = engine.store.run_dir(run.run_id) / "state.json"
    before = snapshot.read_bytes()
    engine.store.pause()
    engine.poll_once()
    assert snapshot.read_bytes() == before
    assert not executor.prompts


def test_retry_cli_returns_failure_when_rearming_immediately_fails(tmp_path, monkeypatch, capsys):
    """@brief Accepted retry is not reported as success when provisioning fails."""
    from adore.cli import main

    from tests.test_smoke import _config_file

    config = _config_file(tmp_path)
    store = StateStore(tmp_path / ".adore")
    store.save(RunState(run_id="job-9", ticket_iid=9, lifecycle="failed", outcome="old failure"))

    class Engine:
        """@brief Simulate a newly persisted measured provisioning failure."""

        def retry(self, run_id):
            """@brief Persist a measured terminal failure after accepting Retry."""
            current = store.load(run_id)
            current.outcome = "INFRASTRUCTURE_EXHAUSTED: measured version-invalid"
            store.save(current)
            return True

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", lambda *args, **kwargs: Engine())
    assert main(["-c", config, "retry", "job-9"]) == 1
    assert '"reason": "retry_failed"' in capsys.readouterr().out


@pytest.mark.parametrize(
    "change",
    [
        "failed",
        "retried",
        "wrong-job",
        "oversized",
        "schema",
        "extra",
        "boolean-exit",
        "trailing",
        "exit",
        "unknown",
        "duplicate",
        "missing",
        "timeout",
        "state",
    ],
)
def test_retry_worker_reports_bound_outcome(tmp_path, change):
    """@brief Retry binds process evidence and reads only the requested persisted cause."""
    from adore.profiles import ProfileStore
    from adore.web.commands import CommandWorker
    from adore.web.store import WebStore

    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    web = WebStore(profiles.home / "web.db")
    actor = web.authenticate("admin", "admin")
    operation = web.enqueue(actor["id"], "alpha", "retry", "job-9", "retry-proof")
    store = StateStore(profiles.default_store_root("alpha"))
    if change != "state":
        store.save(
            RunState(
                run_id="job-9",
                ticket_iid=9,
                lifecycle="failed",
                outcome="INFRASTRUCTURE_EXHAUSTED: version-invalid",
            )
        )
    code = 0 if change == "retried" else 124 if change == "timeout" else 1
    payload = {
        "schema": 1,
        "run_id": "wrong" if change == "wrong-job" else "job-9",
        "exit_code": 0 if change == "exit" else code,
        "reason": "retried"
        if change == "retried"
        else "PRIVATE"
        if change == "unknown"
        else "retry_failed",
    }
    if change == "schema":
        payload["schema"] = True
    elif change == "extra":
        payload["extra"] = "PRIVATE"
    elif change == "boolean-exit":
        payload["exit_code"] = True
    evidence = json.dumps(payload)
    if change == "oversized":
        evidence = " " * 1100 + evidence
    elif change == "trailing":
        evidence += "\nPRIVATE trailing output"
    if change == "duplicate":
        evidence = evidence.replace('"schema": 1', '"schema": 1, "schema": 1')

    def runner(argv, env):
        """@brief Supply bound or corrupt terminal evidence without external commands."""
        return CommandResult(
            exit_code=code,
            stdout=(
                "PRIVATE log\nADORE_RETRY_RESULT " + ("{}" if change == "missing" else evidence)
            ),
            stderr="PRIVATE stderr",
        )

    assert CommandWorker(profiles, web, runner=runner).run_pending() == 1
    result = web.operation(operation["id"])
    assert result["status"] == (
        "succeeded" if change == "retried" else "uncertain" if change == "timeout" else "failed"
    )
    assert result["result"] == (
        "completed"
        if change == "retried"
        else "outcome uncertain"
        if change == "timeout"
        else "retry:failed:INFRASTRUCTURE_EXHAUSTED: version-invalid"
        if change == "failed"
        else "retry:state_unavailable"
        if change == "state"
        else "retry:invalid_result"
    )
    assert "PRIVATE" not in result["result"]


def test_explicit_retry_can_repeat_interrupted_environment_refresh(tmp_path, monkeypatch):
    """@brief A receipt refresh interrupted before plan replacement can be retried safely."""
    engine, run, context, controller, binary, work, executor = retry_fixture(tmp_path, monkeypatch)
    upgrade(engine, context, controller, binary)
    from adore.local_process import atomic_record

    def interrupted(path, value):
        """@brief Interrupt the plan write after the owned receipt was refreshed."""
        raise OSError("interrupted plan replacement")

    monkeypatch.setattr("adore.orchestrator.atomic_record", interrupted)
    assert engine.retry(run.run_id)
    assert engine.store.load(run.run_id).lifecycle == "failed"
    monkeypatch.setattr("adore.orchestrator.atomic_record", atomic_record)
    assert engine.retry(run.run_id)
    assert engine.store.load(run.run_id).lifecycle == "parked-clarification"
    assert (work / "progress.txt").is_file() and len(executor.prompts) == 1


@pytest.mark.parametrize(
    "cause,reason",
    [
        ("selected local executable is unavailable", "executable_missing"),
        ("local account differs from the ADORE process account", "account_mismatch"),
        ("permission", "permission_denied"),
    ],
)
def test_retry_cli_reports_native_setup_cause(tmp_path, monkeypatch, capsys, cause, reason):
    """@brief Missing native prerequisites are classified even before engine construction."""
    from adore.cli import main
    from adore.local_process import LocalExecutionError

    from tests.test_smoke import _config_file

    config = _config_file(tmp_path)

    def unavailable(*args, **kwargs):
        """@brief Raise a known native setup boundary error without host tools."""
        if cause == "permission":
            raise PermissionError("PRIVATE path")
        raise LocalExecutionError(cause)

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", unavailable)
    assert main(["-c", config, "retry", "job-9"]) == 1
    output = capsys.readouterr().out
    assert json.loads(output.split("ADORE_RETRY_RESULT ")[1])["reason"] == reason
    assert "PRIVATE" not in output

# END OF FILE
