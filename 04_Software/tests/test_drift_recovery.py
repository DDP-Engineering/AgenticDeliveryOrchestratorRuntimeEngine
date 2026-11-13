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
@file    test_drift_recovery.py
@brief   Confirmed abandonment, owned cleanup and fresh restart.
@details Offline ownership, drift, lease, revision and CLI refusal contracts.
"""

# IMPORTS
from hashlib import sha256
import json

from adore.isolation import IsolationError
from adore.local_execution import LocalBackend
from adore.local_process import LocalExecutionError
import pytest

from tests.test_retry_revalidation import retry_fixture, upgrade

# PUBLIC CONTRACT TESTS


def prepare(tmp_path, monkeypatch):
    """@brief Bind fixture names to actual deterministic resource ownership."""
    engine, run, context, controller, binary, work, executor = retry_fixture(tmp_path, monkeypatch)
    engine.store.delete_run("github-owner-repo-7")  # Original synthetic fixture identity.
    engine.worktrees.create = lambda *args, **kwargs: work
    engine.config.metrics.db_path = str(tmp_path / "metrics.sqlite")
    engine.config.metrics.export_jsonl = str(tmp_path / "metrics.jsonl")
    run.branch = engine.identity.branch(run.run_id)
    run.container = engine.identity.container_name(run.run_id)
    run.execution["resource"]["name"] = run.container
    receipt = engine.store.run_dir(run.run_id) / "local-control/runtime.json"
    record = json.loads(receipt.read_text())
    record["resource"] = run.execution["resource"]
    receipt.write_text(json.dumps(record))
    run.worktree = str(work)
    run.checkpoint_remote_commit = "a" * 40
    engine.store.save(run)
    engine.worktrees.verify_removal = lambda *args: None
    return engine, run, context, controller, binary, work, executor


def test_owned_delete_releases_drift_then_removes_state(tmp_path, monkeypatch):
    """@brief Explicit ownership cleanup bypasses volatile policy only, never scope control."""
    engine, run, context, controller, binary, work, _ = prepare(tmp_path, monkeypatch)
    upgrade(engine, context, controller, binary)
    calls = []
    engine.worktrees.remove_remote_branch = lambda *args, **kwargs: calls.append(args)
    with pytest.raises(LocalExecutionError):
        engine.delete(run.run_id)
    assert engine.store.exists(run.run_id)
    engine.delete(run.run_id, owned_resources=True)
    assert not engine.store.exists(run.run_id)
    assert calls == [(run.branch, "a" * 40, engine.config.delivery.target_branch)]
    assert engine.worktrees.removed == [run.run_id]
    assert controller.controlled
    assert binary.exists() and (work / "progress.txt").exists()


@pytest.mark.parametrize(
    "bad", ["receipt", "host", "account", "worktree", "io", "branch", "human", "scope", "remote"]
)
def test_owned_delete_refuses_foreign_or_unconfirmed_resources(tmp_path, monkeypatch, bad):
    """@brief Every ownership boundary fails closed and keeps the job and worktree."""
    engine, run, context, controller, binary, work, _ = prepare(tmp_path, monkeypatch)
    upgrade(engine, context, controller, binary)
    if bad == "receipt":
        (engine.store.run_dir(run.run_id) / "local-control/runtime.json").write_text("{}")
    elif bad in {"host", "account"}:
        context[bad] = "foreign"
        engine.backend = LocalBackend(engine.config, context=context, controller=controller)
    elif bad in {"worktree", "io"}:
        run.execution["resource"][bad] = str(tmp_path / "foreign")
        engine.store.save(run)
    elif bad == "branch":
        run.branch = "human/branch"
        engine.store.save(run)
    elif bad == "human":
        run.lifecycle = "handed-off"
        engine.store.save(run)
    elif bad == "scope":

        def refuse(*args):
            raise LocalExecutionError("unconfirmed process scope")

        controller.recover = refuse
    elif bad == "remote":

        def refuse(*args, **kwargs):
            raise IsolationError("remote run branch changed outside ADORE")

        engine.worktrees.remove_remote_branch = refuse
    with pytest.raises((LocalExecutionError, IsolationError)):
        engine.delete(run.run_id, owned_resources=True)
    assert engine.store.exists(run.run_id)
    assert not engine.worktrees.removed
    assert (work / "progress.txt").exists()


def test_restart_checks_revision_and_preserves_paused_manual_admission(tmp_path, monkeypatch):
    """@brief Only the confirmed failed incarnation is deleted before fresh admission."""
    engine, run, *_ = prepare(tmp_path, monkeypatch)
    engine.store.pause()
    revision = sha256((engine.store.run_dir(run.run_id) / "state.json").read_bytes()).hexdigest()
    calls = []

    def poll(**kwargs):
        assert not engine.store.exists(run.run_id)
        assert engine.store.is_paused()
        calls.append(kwargs)
        return {"picked": run.ticket_iid}

    engine.poll_once = poll
    with pytest.raises(IsolationError, match="changed"):
        engine.restart(run.run_id, "0" * 64)
    assert engine.store.exists(run.run_id) and not calls
    assert engine.restart(run.run_id, revision)["picked"] == run.ticket_iid
    assert calls == [{"ticket_iid": run.ticket_iid, "reconcile": False}]


@pytest.mark.parametrize("fault", ["native", "state", "git", "lock"])
def test_cli_delete_refuses_cleanly_with_guidance(tmp_path, monkeypatch, capsys, fault):
    """@brief Native/Git/state failures and live worker locks never traceback."""
    from adore.cli import main
    from adore.state import StateError

    from tests.test_smoke import _config_file

    engine, run, *_ = prepare(tmp_path, monkeypatch)
    config = _config_file(tmp_path)
    monkeypatch.setattr("adore.cli._engine", lambda args: (engine.config, engine))
    monkeypatch.setattr("adore.cli._store", lambda cfg: engine.store)
    if fault == "lock":
        from adore.state import StateStore
        held = StateStore(engine.store.root).run_lock(run.run_id)
        held.__enter__()
    else:

        def refuse(*args, **kwargs):
            raise {"native": LocalExecutionError, "state": StateError, "git": IsolationError}[
                fault
            ]("private raw evidence")

        engine.delete = refuse
    try:
        assert main(["-c", config, "delete", run.run_id, "--force"]) == 1
    finally:
        if fault == "lock":
            held.__exit__(None, None, None)
    output = capsys.readouterr().out
    assert "error:" in output and "private raw evidence" not in output
    if fault == "lock":
        assert "owned by another conductor" in output
    else:
        assert "inspect" in output.lower() or "restore" in output.lower()
    assert engine.store.exists(run.run_id)


def test_web_restart_requires_confirmation_revision_and_rechecks_worker(tmp_path):
    """@brief Queue binds confirmed state and worker refuses a later incarnation."""
    from adore.profiles import ProfileStore
    from adore.state import RunState, StateStore
    from adore.web.app import create_app
    from adore.web.commands import CommandWorker
    from adore.web.store import WebStore
    from fastapi.testclient import TestClient

    profiles = ProfileStore(tmp_path / "home")
    item = profiles.create("alpha")
    state = StateStore(item.store_root or profiles.default_store_root("alpha"))
    run = RunState(run_id="run-1", ticket_iid=42, lifecycle="failed")
    state.save(run)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        detail = client.get(f"/api/v1/jobs/{item.project_id}/run-1").json()["job"]
        revision = detail["state_revision"]
        body = {"run_id": "run-1", "idempotency_key": "restart-once", "state_revision": revision}
        headers = {"X-CSRF-Token": csrf}
        url = f"/api/v1/projects/{item.project_id}/operations/restart"
        assert client.post(url, json=body, headers=headers).status_code == 400
        body["confirmed"] = True
        stale = {**body, "state_revision": "0" * 64}
        assert client.post(url, json=stale, headers=headers).status_code == 409
        accepted = client.post(url, json=body, headers=headers)
        assert accepted.status_code == 200
        assert client.post(url, json=body, headers=headers).json() == accepted.json()
        web = WebStore(profiles.home / "web.db")
        calls = []
        worker = CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0)
        run.outcome = "Changed after confirmation"
        state.save(run)
        assert worker.run_pending() == 1
        assert not calls
        assert web.operation(accepted.json()["id"])["status"] == "failed"


def test_git_owned_worktree_and_remote_absence_contracts(tmp_path):
    """@brief Dedicated worktree linkage and absent unpublished branches are checked offline."""
    from adore.isolation import WorktreeManager

    from tests.test_isolation import FakeRunner, _ok

    root, repo = tmp_path / "work", tmp_path / "repo"
    work = root / "run-1"
    work.mkdir(parents=True)
    (work / ".git").write_text("gitdir: controlled-pointer")
    common = str(repo / ".git")
    runner = FakeRunner(_ok(common), _ok(common), _ok("refs/heads/adore/run-1"), _ok(str(work)))
    WorktreeManager(repo, root, runner=runner).verify_removal("run-1", "adore/run-1")
    runner = FakeRunner(_ok(common), _ok(common), _ok("refs/heads/human"), _ok(str(work)))
    with pytest.raises(IsolationError):
        WorktreeManager(repo, root, runner=runner).verify_removal("run-1", "adore/run-1")
    runner = FakeRunner(_ok(), _ok())
    manager = WorktreeManager(repo, root, runner=runner)
    manager.remove_remote_branch("adore/run-1", "", "main", allow_absent=True)
    assert not any("push" in call for call in runner.calls)
    runner = FakeRunner(_ok(), _ok("a" * 40 + "\trefs/heads/adore/run-1"))
    with pytest.raises(IsolationError):
        WorktreeManager(repo, root, runner=runner).remove_remote_branch(
            "adore/run-1", "", "main", allow_absent=True
        )
    assert not any("push" in call for call in runner.calls)


@pytest.mark.parametrize("revoked", [False, True])
@pytest.mark.parametrize("retained", [False, True])
def test_restart_worker_uses_fixed_bound_argv_and_rechecks_grants(tmp_path, revoked, retained):
    """@brief Authorized restart reaches only fixed CLI argv; revoked access never invokes it."""
    from adore.profiles import ProfileStore
    from adore.state import RunState, StateStore
    from adore.web.commands import CommandOutcome, CommandWorker
    from adore.web.store import WebStore

    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha")
    state = StateStore(profile.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="one", ticket_iid=42, lifecycle="failed"))
    revision = sha256((state.run_dir("one") / "state.json").read_bytes()).hexdigest()
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "long-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    operation = web.enqueue(user["id"], "alpha", "restart", "one." + revision, "restart-bound")
    if revoked:
        web.set_memberships(user["id"], [])
    calls = []
    assert (
        CommandWorker(
            profiles,
            web,
            runner=lambda argv, env: (
                calls.append(argv)
                or CommandOutcome(
                    0, "ADORE_RESTART_RESULT " + json.dumps({"schema": 1, "run_id": "one",
                        "revision": revision, "exit_code": 0, "reason": "restarted",
                        "picked": 42, "retained": retained})
                )
            ),
        ).run_pending()
        == 1
    )
    if revoked:
        assert not calls
        assert web.operation(operation["id"])["status"] == "failed"
    else:
        assert calls[0][-5:] == ["restart", "one", "--force", "--expected-revision", revision]
        assert web.operation(operation["id"])["status"] == "succeeded"
        assert web.operation(operation["id"])["result"] == (
            "restart:retained" if retained else "completed"
        )


@pytest.mark.parametrize("current_backend", ["local", "container"])
def test_owned_native_cleanup_does_not_require_current_tools_or_backend(
    tmp_path, monkeypatch, current_backend
):
    """@brief Saved native ownership survives missing executables and backend reconfiguration."""
    from adore.execution import ContainerBackend

    engine, run, context, controller, binary, work, _ = prepare(tmp_path, monkeypatch)
    binary.unlink()
    engine.config.execution.backend = current_backend
    engine.backend = (
        LocalBackend.for_cleanup(engine.config)
        if current_backend == "local"
        else ContainerBackend(engine.containers)
    )
    engine.delete(run.run_id, owned_resources=True)
    assert not engine.store.exists(run.run_id)
    assert engine.worktrees.removed == [run.run_id]
    assert (work / "progress.txt").exists()


@pytest.mark.parametrize("runtime", ["docker", "podman", "wsl -d Test -- docker"])
@pytest.mark.parametrize("fault", ["none", "foreign-mount", "foreign-member", "appeared"])
def test_container_release_uses_actual_owned_ids_independently_of_egress(tmp_path, runtime, fault):
    """@brief Old proxy policy and resource-name races never authorize foreign destruction."""
    from adore.branding import CONTAINER_IO_MOUNT, CONTAINER_REPO_MOUNT, CONTAINER_WORKTREE_MOUNT
    from adore.isolation import ContainerManager
    from adore.util import CommandResult

    repo, work, io = (tmp_path / part for part in ("repo", "work", "io"))
    name, proxy_name = "adore-run-one", "adore-run-one-egress-proxy"
    manager = ContainerManager(runtime, "new-image", "uv", "npm")

    def mount(source, destination):
        return {"Type": "bind", "Source": manager._mount_source(source), "Destination": destination}

    containers = {
        name: {
            "Id": "a" * 64,
            "Name": "/" + name,
            "Image": "b" * 64,
            "Mounts": [
                mount(repo, CONTAINER_REPO_MOUNT),
                mount(work, CONTAINER_WORKTREE_MOUNT),
                mount(io, CONTAINER_IO_MOUNT),
            ],
        },
        proxy_name: {
            "Id": "c" * 64,
            "Name": "/" + proxy_name,
            "Mounts": [mount(io / "egress-proxy/squid.conf", "/etc/squid/squid.conf")],
        },
    }
    if fault == "foreign-mount":
        containers[proxy_name]["Mounts"][0]["Source"] = "foreign"
    if fault == "appeared":
        containers.clear()
    network = {"Id": "d" * 64, "Name": "old-prefix-" + name, "Internal": True}
    removed = []

    def runner(argv, **kwargs):
        args = argv[len(manager.runtime_argv) :]
        if args[0] == "inspect":
            selected = next((r for n, r in containers.items() if args[1] in (n, r["Id"])), None)
            return (
                CommandResult(stdout=json.dumps([selected]))
                if selected
                else CommandResult(exit_code=1, stderr="No such container: " + args[1])
            )
        if args[:2] == ["network", "ls"]:
            if fault == "appeared":
                containers[name] = {"Id": "f" * 64, "Name": "/" + name}
                return CommandResult(stdout="")
            return CommandResult(stdout=network["Name"] if network else "")
        if args[:2] == ["network", "inspect"]:
            if not network:
                return CommandResult(exit_code=1, stderr="No such network")
            record = (
                dict(id=network["Id"], name=network["Name"], internal=True)
                if runtime == "podman"
                else network
            )
            return CommandResult(stdout=json.dumps([record]))
        if args[0] == "ps":
            members = {r["Id"] for r in containers.values()}
            if fault == "foreign-member":
                members.add("f" * 64)
            return CommandResult(stdout="\n".join(sorted(members)))
        if args[0] == "rm":
            target = args[-1]
            assert len(target) == 64
            removed.append(target)
            selected = next(n for n, r in containers.items() if r["Id"] == target)
            del containers[selected]
            return CommandResult()
        if args[:2] == ["network", "rm"]:
            assert args[-1] == "d" * 64
            removed.append(args[-1])
            network.clear()
            return CommandResult()
        raise AssertionError(args)

    manager.runner = runner
    if fault == "none":
        manager.release_owned(name, repo, work, io)
        assert removed == ["a" * 64, "c" * 64, "d" * 64]
    else:
        with pytest.raises(IsolationError):
            manager.release_owned(name, repo, work, io)
        assert not removed


@pytest.mark.parametrize("unexpected_control", [False, True])
def test_unprovisioned_native_run_requires_no_unrecorded_control(
    tmp_path, monkeypatch, unexpected_control
):
    """@brief Early failed provisioning may release proven absence, never unseen control files."""
    engine, run, *_ = prepare(tmp_path, monkeypatch)
    control = engine.store.run_dir(run.run_id) / "local-control"
    if not unexpected_control:
        (control / "runtime.json").unlink()
        control.rmdir()
    run.execution["resource"] = {}
    engine.store.save(run)
    if unexpected_control:
        with pytest.raises(IsolationError):
            engine.delete(run.run_id, owned_resources=True)
        assert engine.store.exists(run.run_id)
    else:
        engine.delete(run.run_id, owned_resources=True)
        assert not engine.store.exists(run.run_id)


@pytest.mark.parametrize("foreign", [False, True])
def test_saved_container_can_be_abandoned_after_switch_to_native(tmp_path, monkeypatch, foreign):
    """@brief Cleanup uses saved container ownership after switching to native execution."""
    from tests.test_orchestrator import make_engine, make_run

    engine, _, trees, containers, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = "failed"
    engine.store.save(run)
    engine.config.execution.backend = "local"
    trees.verify_removal = lambda *args: None
    trees.remove_remote_branch = lambda *args, **kwargs: None
    calls = []

    def release(*args, **kwargs):
        if foreign:
            raise IsolationError("foreign container mount")
        calls.append(args)

    containers.release_owned = release
    if foreign:
        with pytest.raises(IsolationError):
            engine.delete(run.run_id, owned_resources=True)
        assert engine.store.exists(run.run_id) and not trees.removed
    else:
        engine.delete(run.run_id, owned_resources=True)
        assert calls and not engine.store.exists(run.run_id)


def test_deleted_identity_gets_fresh_usage_and_terminal_metrics(tmp_path, monkeypatch):
    """@brief A real manual admission after cleanup cannot inherit old usage cursors/summaries."""
    from adore import metrics
    from adore.executor.base import GateRun
    from adore.web.store import WebStore, WebStoreError

    from tests.test_orchestrator import FakeAegis, task

    engine, run, *_ = prepare(tmp_path, monkeypatch)
    # Bind the fixture to the actual deterministic ticket identity used by poll_once.
    run.checkpoint_remote_commit = ""
    engine.store.save(run)
    generated = run.branch + "-g" + "a" * 12
    engine.worktrees.remote_branch_head = lambda branch: "b" * 40
    engine.worktrees.fresh_branch = lambda base, **kwargs: generated
    original = run.run_id
    current = engine._run_id(run.ticket_iid)
    assert current != original
    engine._run_id = lambda iid: original
    web = WebStore(tmp_path / "web.db")
    project_id = "1" * 32
    engine.store.journal(
        run.run_id,
        "usage",
        event_id=f"{run.run_id}:1",
        attempt=1,
        tokens_in=10,
        tokens_out=2,
        cost_usd=0.1,
        context="build",
        executor="pi",
        model="model",
        review_round=0,
        cost_reported=True,
    )
    old_events = engine.store.read_journal(run.run_id)
    web.reconcile_usage(project_id, run.run_id, old_events)
    metrics.record_summary(
        engine.config.metrics.db_path,
        metrics.RunSummary(run_id=run.run_id, lifecycle="failed", tokens_in=10),
    )
    engine.on_delete = lambda run_id, remove_source: web.forget_run_usage(
        project_id,
        run_id,
        remove_source=remove_source,
    )
    from dataclasses import replace

    stage = task("frame")
    stage = replace(stage, header={**stage.header, "branch": generated})
    client = FakeAegis([stage])
    from types import SimpleNamespace

    client.probe = lambda: SimpleNamespace(version="0.15.0", schema=1)
    client.create_task = lambda *args: task("build").task_id
    monkeypatch.setattr("adore.orchestrator.AegisClient", lambda *args: client)
    # Exercise actual manual admission with injected native resources and executor.
    engine.executor.results.clear()
    engine.executor.results.append(GateRun(exit_code=0, has_questions=True, questions="What next?"))
    engine.worktrees.remove = lambda *args, **kwargs: None
    engine.store.pause()
    engine.config.readiness.require_priority_label = False
    revision = sha256((engine.store.run_dir(run.run_id) / "state.json").read_bytes()).hexdigest()
    result = engine.restart(run.run_id, revision)
    assert result["picked"] == run.ticket_iid, json.dumps(result)
    fresh = engine.store.load(run.run_id)
    assert fresh.lifecycle != "failed", fresh.outcome
    assert fresh.branch == generated and result["unproven_branch_retained"] is True
    assert engine.store.is_paused()
    assert metrics.load_summaries(engine.config.metrics.db_path) == []
    events = engine.store.read_journal(run.run_id)
    with pytest.raises(WebStoreError, match="source changed"):
        web.reconcile_usage(project_id, run.run_id, old_events, current_source=lambda: events)
    assert web.reconcile_usage(project_id, run.run_id, events) == []


def test_deleted_source_and_projection_reset_share_transaction(tmp_path):
    """@brief A reader arriving during source deletion cannot restore a deleted cursor."""
    from threading import Event, Thread

    from adore.state import StateStore
    from adore.web.store import WebStore, WebStoreError

    from tests.usage_events import versioned_usage

    state = StateStore(tmp_path / "state")
    state.journal(
        "one",
        "usage",
        **{
            key: value
            for key, value in versioned_usage("one", 1, executor="pi").items()
            if key not in {"event", "ts"}
        },
    )
    old = state.read_journal("one")
    web = WebStore(tmp_path / "web.db")
    project_id = "a" * 32
    web.reconcile_usage(project_id, "one", old)
    started = Event()
    errors = []

    def read_old():
        started.set()
        try:
            web.reconcile_usage(
                project_id, "one", old, current_source=lambda: state.read_journal("one")
            )
        except WebStoreError as exc:
            errors.append(str(exc))

    reader = Thread(target=read_old)

    def remove_source():
        reader.start()
        assert started.wait(2)
        state.delete_run("one")

    web.forget_run_usage(project_id, "one", remove_source=remove_source)
    reader.join(timeout=3)
    assert not reader.is_alive()
    assert errors == ["usage source changed before projection"]
    assert web.reconcile_usage(project_id, "one", []) == []


def test_projection_reset_rolls_back_when_source_removal_fails(tmp_path):
    """@brief Failed deletion retains the old projections and cannot admit a fresh journal."""
    from adore.web.store import WebStore, WebStoreError

    from tests.usage_events import versioned_usage

    web = WebStore(tmp_path / "web.db")
    project_id = "a" * 32
    old = [
        {"event": "usage", "ts": "2026-11-05T10:00:00Z", **versioned_usage("one", 1, executor="pi")}
    ]
    web.reconcile_usage(project_id, "one", old)

    def refuse():
        raise PermissionError("source retained")

    with pytest.raises(PermissionError):
        web.forget_run_usage(project_id, "one", remove_source=refuse)
    with pytest.raises(WebStoreError, match="absent"):
        web.reconcile_usage(project_id, "one", [])


def test_cli_stats_rebuild_uses_same_conductor_lock(tmp_path, monkeypatch, capsys):
    """@brief An old rebuild cannot overwrite a deleted job's fresh terminal summary."""
    from adore.cli import main
    from adore.state import StateStore

    from tests.test_smoke import _config_file

    config = _config_file(tmp_path)
    store = StateStore(tmp_path / ".adore")
    assert store.acquire_lock()
    try:
        assert main(["-c", config, "stats", "--rebuild"]) == 1
        assert "web worker" in capsys.readouterr().out
    finally:
        store.release_lock()
    assert main(["-c", config, "stats", "--rebuild"]) == 0
    assert store.lock_info() is None


def test_delete_refuses_mismatched_saved_directory_identity(tmp_path, monkeypatch):
    """@brief A corrupt state identity cannot grant cleanup authority to another job."""
    engine, run, *_ = prepare(tmp_path, monkeypatch)
    state = engine.store.run_dir(run.run_id) / "state.json"
    value = json.loads(state.read_text())
    value["run_id"] = "foreign"
    state.write_text(json.dumps(value))
    with pytest.raises(IsolationError):
        engine.delete(run.run_id, owned_resources=True)
    assert engine.store.exists(run.run_id) and not engine.worktrees.removed


@pytest.mark.parametrize("occupied", ["local", "remote"])
def test_fresh_branch_avoids_unproven_remote_and_local_refs(tmp_path, occupied):
    """@brief New admission preserves occupied refs and validates a bounded fresh generation."""
    from adore.isolation import WorktreeManager
    from adore.util import CommandResult

    calls = []
    base = "feature/ticket-7"

    def runner(argv, **kwargs):
        calls.append(argv)
        if "ls-remote" in argv:
            ref = argv[-1]
            return CommandResult(
                stdout=("a" * 40 + "\t" + ref) if ref == "refs/heads/" + base else ""
            )
        if "show-ref" in argv:
            return CommandResult(
                exit_code=0 if occupied == "local" and argv[-1] == "refs/heads/" + base else 1
            )
        return CommandResult()

    manager = WorktreeManager(tmp_path, tmp_path / "work", runner=runner)
    selected = manager.fresh_branch(base, validate=lambda name: name.startswith(base))
    assert selected.startswith(base + "-g") and len(selected) == len(base) + 14
    assert not any("push" in argv or "branch" in argv for argv in calls)
    with pytest.raises(IsolationError):
        manager.fresh_branch(base, validate=lambda name: name == base)


def test_restart_retains_only_an_unpublished_unproven_old_ref(tmp_path, monkeypatch):
    """@brief The reported old-orphan case reaches a generation without deleting unknown history."""
    engine, run, *_ = prepare(tmp_path, monkeypatch)
    run.checkpoint_remote_commit = ""
    engine.store.save(run)
    generated = run.branch + "-g" + "a" * 12
    engine.worktrees.fresh_branch = lambda base, **kwargs: generated
    engine.worktrees.remote_branch_head = lambda branch: "b" * 40
    removed = []
    engine.worktrees.remove_remote_branch = lambda *args, **kwargs: removed.append(args)
    engine.poll_once = lambda **kwargs: {"picked": run.ticket_iid}
    revision = sha256((engine.store.run_dir(run.run_id) / "state.json").read_bytes()).hexdigest()
    result = engine.restart(run.run_id, revision)
    assert result["unproven_branch_retained"] is True
    assert not removed and not engine.store.exists(run.run_id)


def test_restart_naming_rule_failure_precedes_destructive_cleanup(tmp_path, monkeypatch):
    """@brief A strict custom rule that forbids generations preserves the entire failed job."""
    from adore.isolation import WorktreeManager
    from adore.util import CommandResult

    engine, run, *_ = prepare(tmp_path, monkeypatch)
    run.checkpoint_remote_commit = ""
    engine.store.save(run)
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        if "show-ref" in argv:
            return CommandResult(exit_code=1)
        if "ls-remote" in argv:
            return CommandResult(stdout="a" * 40 + "\t" + argv[-1])
        return CommandResult()

    manager = WorktreeManager(tmp_path, tmp_path / "trees", runner=runner)
    engine.worktrees.fresh_branch = manager.fresh_branch
    engine.worktrees.remote_branch_head = manager.remote_branch_head
    engine.config.worktree.branch_rule = "^" + run.branch + "$"
    revision = sha256((engine.store.run_dir(run.run_id) / "state.json").read_bytes()).hexdigest()
    with pytest.raises(IsolationError, match="naming rule"):
        engine.restart(run.run_id, revision)
    assert engine.store.exists(run.run_id)
    assert (engine.store.run_dir(run.run_id) / "local-control/runtime.json").exists()
    assert not engine.worktrees.removed


@pytest.mark.parametrize("kind", ["github", "gitlab", "gitea"])
@pytest.mark.parametrize("suffix", ["-g" + "a" * 12, "-gbad"])
def test_generated_branch_cleanup_keeps_exact_ownership_and_lease(tmp_path, kind, suffix):
    """@brief Human-merged cleanup recognizes only exact derived generations on every forge."""
    from tests.test_orchestrator import make_engine, make_run

    engine, forge, trees, _, _ = make_engine(tmp_path)
    engine.config.platform.kind = kind
    engine.config.delivery.remove_source_branch = True
    run = make_run(engine)
    run.branch += suffix
    run.lifecycle, run.stage, run.mr_iid = "in-review", "done", 9
    run.checkpoint_remote_commit = "c" * 40
    engine.store.save(run)
    engine.store.pause()
    forge.mr.state = "merged"
    removed = []
    trees.remove_remote_branch = lambda *args: removed.append(args)
    assert engine.poll_once()["done"] == 1
    if suffix == "-gbad":
        assert not removed
        assert "branch retained" in engine.store.load(run.run_id).outcome
    else:
        assert removed == [(run.branch, "c" * 40, "main")]


@pytest.mark.parametrize("bad", ["local-exit", "local-timeout", "remote-output", "remote-exit"])
def test_fresh_branch_refuses_untrusted_availability_evidence(tmp_path, bad):
    """@brief Missing Git evidence never becomes permission to use an occupied branch."""
    from adore.isolation import WorktreeManager
    from adore.util import CommandResult

    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        if "show-ref" in argv:
            return CommandResult(
                exit_code=128 if bad == "local-exit" else 1, timed_out=bad == "local-timeout"
            )
        if "ls-remote" in argv:
            return CommandResult(
                exit_code=1 if bad == "remote-exit" else 0, stdout="not-a-remote-ref"
            )
        return CommandResult()

    with pytest.raises(IsolationError):
        WorktreeManager(tmp_path, tmp_path / "work", runner=runner).fresh_branch(
            "adore/one", validate=lambda name: True
        )
    assert not any("push" in call or "branch" in call for call in calls)


def test_fresh_worktree_refuses_local_ref_that_appears_after_selection(tmp_path):
    """@brief Atomic initial Git creation refuses a raced-in branch instead of adopting it."""
    from adore.isolation import WorktreeManager
    from adore.util import CommandResult

    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        if "show-ref" in argv:
            return CommandResult(exit_code=1)
        if "ls-remote" in argv:
            return CommandResult(stdout="")
        if "worktree" in argv:
            assert "-b" in argv
            return CommandResult(exit_code=128, stderr="branch already exists")
        return CommandResult()

    manager = WorktreeManager(tmp_path, tmp_path / "work", runner=runner)
    selected = manager.fresh_branch("adore/one", validate=lambda name: True)
    with pytest.raises(IsolationError):
        manager.create("one", selected, "origin/main", new_branch=True)
    assert not any("branch" in argv or "-D" in argv for argv in calls)


def test_restart_reuses_verified_own_branch_under_strict_rule(tmp_path, monkeypatch):
    """@brief Normal known-owned recovery does not require a generation its rule forbids."""
    engine, run, *_ = prepare(tmp_path, monkeypatch)
    engine.config.worktree.branch_rule = "^" + run.branch + "$"
    engine.worktrees.remote_branch_head = lambda branch: run.checkpoint_remote_commit

    def forbidden(*args, **kwargs):
        pytest.fail("normal owned cleanup must permit the exact saved branch")

    engine.worktrees.fresh_branch = forbidden
    engine.poll_once = lambda **kwargs: {"picked": run.ticket_iid}
    revision = sha256((engine.store.run_dir(run.run_id) / "state.json").read_bytes()).hexdigest()
    assert engine.restart(run.run_id, revision)["picked"] == run.ticket_iid


def test_restart_known_changed_checkpoint_refuses_before_cleanup(tmp_path, monkeypatch):
    """@brief An unproven-orphan exception never applies to a known checkpoint that changed."""
    engine, run, _, controller, *_ = prepare(tmp_path, monkeypatch)
    controller.controlled.clear()
    engine.worktrees.remote_branch_head = lambda branch: "f" * 40
    state = engine.store.run_dir(run.run_id) / "state.json"
    raw = state.read_bytes()
    with pytest.raises(IsolationError, match="changed outside"):
        engine.restart(run.run_id, sha256(raw).hexdigest())
    assert state.read_bytes() == raw
    assert not controller.controlled and not engine.worktrees.removed


def test_actual_branch_rule_uses_selected_identity_and_rejects_invalid_values():
    """@brief Actual-name policy checks preserve defaults and refuse invalid identities."""
    from adore.config import branch_naming_preview

    name = "feature/ticket-7-g" + "a" * 12
    assert branch_naming_preview("{run_id}", "^" + name + "$", "adore", run_id=name, iid=7)["valid"]
    assert not branch_naming_preview("{run_id}", "", "adore", run_id=None)["valid"]
    assert not branch_naming_preview("{run_id}", "", "adore", iid=True)["valid"]


def test_delete_without_worktree_ownership_keeps_unproven_local_branch(tmp_path):
    """@brief An early failed admission cannot force-delete a branch it never established."""
    from tests.test_orchestrator import make_engine, make_run

    engine, _, trees, containers, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle, run.worktree = "failed", ""
    engine.store.save(run)
    trees.path_for = lambda run_id: tmp_path / "absent"
    trees.verify_removal = lambda *args: None
    trees.remove_remote_branch = lambda *args, **kwargs: None
    containers.release_owned = lambda *args, **kwargs: None
    removed = []
    trees.remove = lambda run_id, **kwargs: removed.append(kwargs)
    engine.delete(run.run_id, owned_resources=True)
    assert removed == [{"delete_branch": None}]




@pytest.mark.parametrize(
    "output", ["", "{}", '{"picked":null}', '{"picked":43}', '{"picked":true}']
)
def test_restart_zero_exit_requires_matching_admission(tmp_path, output):
    """@brief Exit zero without the bound ticket is never reported as applied."""
    from adore.profiles import ProfileStore
    from adore.state import RunState, StateStore
    from adore.web.commands import CommandOutcome, CommandWorker
    from adore.web.store import WebStore

    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha")
    state = StateStore(profile.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="one", ticket_iid=42, lifecycle="failed"))
    revision = sha256((state.run_dir("one") / "state.json").read_bytes()).hexdigest()
    web = WebStore(profiles.home / "web.db")
    op = web.enqueue(1, "alpha", "restart", "one." + revision, "restart-proof")
    assert (
        CommandWorker(
            profiles, web, runner=lambda argv, env: CommandOutcome(0, output)
        ).run_pending()
        == 1
    )
    assert web.operation(op["id"])["status"] == "uncertain"
    assert (
        next(row for row in web.recent_audit(None) if row["action"] == "operation-finished")[
            "result"
        ]
        == "uncertain"
    )


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("error: cleanup refused: IsolationError; restore settings", "rejected"),
        ("error: cleanup incomplete (StateError); inspect retained job state", "failed"),
    ],
)
def test_restart_history_distinguishes_refusal_and_failure(tmp_path, output, expected):
    """@brief A checkpoint refusal and a failed cleanup have distinct outcomes."""
    from adore.profiles import ProfileStore
    from adore.state import RunState, StateStore
    from adore.web.commands import CommandOutcome, CommandWorker
    from adore.web.store import WebStore

    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha")
    state = StateStore(profile.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="one", ticket_iid=42, lifecycle="failed"))
    revision = sha256((state.run_dir("one") / "state.json").read_bytes()).hexdigest()
    web = WebStore(profiles.home / "web.db")
    op = web.enqueue(1, "alpha", "restart", "one." + revision, "restart-outcome")
    reason = "cleanup_refused" if expected == "rejected" else "cleanup_failed"
    payload = {
        "schema": 1,
        "run_id": "one",
        "revision": revision,
        "exit_code": 1,
        "reason": reason,
        "picked": None,
        "retained": False,
    }
    output = output + "\nADORE_RESTART_RESULT " + json.dumps(payload)
    CommandWorker(profiles, web, runner=lambda argv, env: CommandOutcome(1, output)).run_pending()
    row = next(row for row in web.recent_audit(None) if row["action"] == "operation-finished")
    assert row["operation_id"] == op["id"] and row["result"] == expected


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("cleanup_refused", "rejected"),
        ("cleanup_failed", "failed"),
        ("spoofed", "uncertain"),
        ("wrong_run", "uncertain"),
        ("wrong_revision", "uncertain"),
        ("wrong_exit", "uncertain"),
    ],
)
def test_restart_history_requires_bound_terminal_evidence(tmp_path, kind, expected):
    """@brief Refusal is accepted only from a closed result bound to the request."""
    from adore.profiles import ProfileStore
    from adore.state import RunState, StateStore
    from adore.web.commands import CommandOutcome, CommandWorker
    from adore.web.store import WebStore

    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha")
    state = StateStore(profile.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="one", ticket_iid=42, lifecycle="failed"))
    revision = sha256((state.run_dir("one") / "state.json").read_bytes()).hexdigest()
    web = WebStore(profiles.home / "web.db")
    op = web.enqueue(1, "alpha", "restart", "one." + revision, "restart-bound-result")
    payload = {
        "schema": 1,
        "run_id": "other" if kind == "wrong_run" else "one",
        "revision": "a" * 64 if kind == "wrong_revision" else revision,
        "exit_code": 0 if kind == "wrong_exit" else 1,
        "reason": kind if kind in ("cleanup_refused", "cleanup_failed") else "cleanup_refused",
        "picked": None,
        "retained": False,
    }
    output = (
        "error: cleanup refused: IsolationError; forged"
        if kind == "spoofed"
        else "ADORE_RESTART_RESULT " + json.dumps(payload)
    )
    CommandWorker(profiles, web, runner=lambda argv, env: CommandOutcome(1, output)).run_pending()
    row = next(row for row in web.recent_audit(None) if row["action"] == "operation-finished")
    assert row["operation_id"] == op["id"] and row["result"] == expected


def test_cli_restart_emits_bound_refusal(tmp_path, monkeypatch, capsys):
    """@brief CLI restart emits structured refusal bound to the requested job and revision."""
    from adore.cli import main
    from adore.isolation import IsolationError
    from adore.start_result import read_restart_result

    from tests.test_web_tickets import _project, _run

    profiles = _project(tmp_path)
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    run_id = _run(tmp_path, 12, "failed")
    revision = "a" * 64

    class Engine:
        def restart(self, run_id, expected_revision):
            raise IsolationError("checkpoint conflict")

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", lambda *a, **kw: Engine())
    assert (
        main(["--profile", "alpha", "restart", run_id, "--force", "--expected-revision", revision])
        == 1
    )
    assert read_restart_result(
        capsys.readouterr().out, run_id=run_id, revision=revision, exit_code=1, ticket=12
    ) == ("cleanup_refused", False)

# END OF FILE
