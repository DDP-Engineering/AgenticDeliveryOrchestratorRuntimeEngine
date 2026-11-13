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
@file    test_web_ownership.py
@brief   Scoped durable ownership contract tests.
@details Barriers and injected process births keep every effect offline.
"""

# IMPORTS
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
from threading import Barrier, Event, Thread, local
from types import SimpleNamespace

from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.commands import CommandWorker
from adore.web.store import WebStore, WebStoreError
from adore.web.worker_context import WorkerContext
import pytest


# HELPER FUNCTIONS
def setup_store(tmp_path):
    """@brief Create independent project identities and a fake process probe."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = profiles.create("alpha")
    beta = profiles.create("beta")
    web = WebStore(profiles.home / "web.db", process_probe=lambda pid: "birth")
    return profiles, web, web.authenticate("admin", "admin"), alpha, beta


# PUBLIC API
def test_atomic_claim_single_winner_and_independent_projects(tmp_path):
    """@brief Independent connections racing for one element have one winner."""
    _, web, admin, alpha, beta = setup_store(tmp_path)
    first = web.enqueue(admin["id"], "alpha", "start", "42", "first")
    second = web.enqueue(admin["id"], "beta", "start", "43", "second")
    owner = web.register_worker("project", project_id=alpha.project_id)
    other = web.register_worker("project", project_id=beta.project_id)
    barrier = Barrier(2)

    def claim(_):
        """@brief Synchronize independent claim transactions."""
        store = WebStore(web.path, process_probe=lambda pid: "birth")
        barrier.wait(timeout=3)
        return store.claim_next(owner, domain="execution")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, range(2)))
    assert [row["id"] for row in results if row] == [first["id"]]
    assert web.claim_next(other, domain="execution")["id"] == second["id"]
    assert web.operation(first["id"])["owner_id"] != web.operation(second["id"])["owner_id"]


def test_configuration_and_execution_domains_do_not_cross(tmp_path):
    """@brief Configuration requires the correct explicit owner and scope."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    execution = web.enqueue(admin["id"], "alpha", "start", "42", "job")
    config = web.enqueue(admin["id"], "alpha", "pause", "", "setting")
    worker = web.register_worker("project", project_id=alpha.project_id)
    settings = web.register_worker("configuration", project_id=alpha.project_id)
    global_settings = web.register_worker("configuration")
    assert web.claim_next(global_settings, domain="configuration_global") is None
    with pytest.raises(WebStoreError):
        web.claim_next(worker, domain="configuration_project")
    assert web.claim_next(settings, domain="configuration_project")["id"] == config["id"]
    assert web.claim_next(worker, domain="execution")["id"] == execution["id"]
    with pytest.raises(WebStoreError):
        web.enqueue(admin["id"], "", "pause", "", "implicit")


def test_recovery_requires_dead_owner_and_fences_old_generation(tmp_path):
    """@brief Recovery of A preserves live B and refuses old A's completion."""
    _, web, admin, alpha, beta = setup_store(tmp_path)
    one = web.register_worker("project", project_id=alpha.project_id)
    two = web.register_worker("project", project_id=beta.project_id)
    a = web.enqueue(admin["id"], "alpha", "start", "42", "a")
    b = web.enqueue(admin["id"], "beta", "start", "43", "b")
    claimed = web.claim_next(one, domain="execution")
    web.claim_next(two, domain="execution")
    assert web.recover_interrupted() == 0
    with web._connect() as connection:
        connection.execute("UPDATE worker_processes SET birth='old' WHERE owner_id=?", (one.id,))
    assert web.recover_interrupted() == 1
    assert web.operation(a["id"])["status"] == "uncertain"
    assert web.operation(b["id"])["status"] == "running"
    with pytest.raises(WebStoreError, match="ownership"):
        web.finish(a["id"], "succeeded", "completed", owner=one,
                   generation=claimed["generation"])
    with pytest.raises(WebStoreError, match="ownership"):
        web.touch_worker(one)
    replacement = web.register_worker("project", project_id=alpha.project_id)
    assert replacement.generation > one.generation
    assert replacement.id != one.id


def test_revoke_between_claim_and_effect_fails_closed(tmp_path):
    """@brief A formerly authorized claim cannot perform an effect after revocation."""
    _, web, _, alpha, _ = setup_store(tmp_path)
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    operation = web.enqueue(dev["id"], "alpha", "start", "42", "revoke")
    owner = web.register_worker("project", project_id=alpha.project_id)
    claim = web.claim_next(owner, domain="execution")
    assert web.authorize_effect(operation["id"], owner=owner, generation=claim["generation"])
    web.set_memberships(dev["id"], [])
    with pytest.raises(WebStoreError, match="permission_revoked"):
        web.authorize_effect(operation["id"], owner=owner, generation=claim["generation"])


def test_cancel_exit_zero_without_actual_stop_is_unconfirmed(tmp_path):
    """@brief An accepted signal or CLI exit zero alone cannot confirm Cancel."""
    profiles, web, admin, _, _ = setup_store(tmp_path)
    state = StateStore(profiles.default_store_root("alpha"))
    state.save(RunState("run-1", 42, lifecycle="working"))
    operation = web.enqueue(admin["id"], "alpha", "cancel", "run-1", "cancel")
    worker = CommandWorker(profiles, web, runner=lambda argv, env: 0)
    assert worker.run_pending() == 1
    assert web.operation(operation["id"])["status"] == "uncertain"
    assert web.operation(operation["id"])["reason"] == "cancel_unconfirmed"


def test_start_acknowledges_durable_admission_while_job_continues(tmp_path):
    """@brief Admission succeeds before a later independent job failure."""
    profiles, web, admin, _, _ = setup_store(tmp_path)
    operation = web.enqueue(admin["id"], "alpha", "start", "42", "start")
    state = StateStore(profiles.default_store_root("alpha"))

    def runner(argv, env):
        """@brief Admit, observe acknowledgement, then fail the separate job."""
        context = json.loads(env["ADORE_WORKER_CONTEXT"])
        from adore.web.ownership import WorkerOwner

        owner = WorkerOwner(context["owner_id"], context["owner_generation"], context["role"],
                            context["project_id"], context["run_id"])
        state.save(RunState("run-42", 42, lifecycle="working"))
        state.save_ticket("run-42", {"iid": 42})
        state.journal("run-42", "picked", ticket=42)
        run_owner = web.register_worker("run", project_id=owner.project_id, run_id="run-42")
        web.acknowledge_start(operation["id"], owner=owner,
                              generation=context["generation"], run_id="run-42",
                              run_owner=run_owner)
        assert web.operation(operation["id"])["status"] == "succeeded"
        assert state.load("run-42").lifecycle == "working"
        state.save(RunState("run-42", 42, lifecycle="failed"))
        return 1

    assert CommandWorker(profiles, web, runner=runner).run_pending() == 1
    assert web.operation(operation["id"])["status"] == "succeeded"
    assert web.operation(operation["id"])["admitted_run_id"] == "run-42"


def test_start_cannot_acknowledge_queue_or_another_ticket(tmp_path):
    """@brief Claim alone or a mismatched stored run cannot establish admission."""
    profiles, web, admin, alpha, _ = setup_store(tmp_path)
    operation = web.enqueue(admin["id"], "alpha", "start", "42", "start")
    owner = web.register_worker("project", project_id=alpha.project_id)
    claim = web.claim_next(owner, domain="execution")
    state = StateStore(profiles.default_store_root("alpha"))
    state.save(RunState("other", 43, lifecycle="working"))
    run_owner = web.register_worker("run", project_id=owner.project_id, run_id="other")
    with pytest.raises(WebStoreError):
        web.acknowledge_start(operation["id"], owner=owner,
                              generation=claim["generation"], run_id="other", run_owner=run_owner)
    assert web.operation(operation["id"])["status"] == "running"


def test_start_exit_zero_alone_cannot_confirm_admission(tmp_path):
    """@brief Engine exit success alone is weaker than durable admission evidence."""
    profiles, web, admin, _, _ = setup_store(tmp_path)
    operation = web.enqueue(admin["id"], "alpha", "start", "42", "one")
    assert CommandWorker(profiles, web, runner=lambda *_: 0).run_pending() == 1
    assert web.operation(operation["id"])["status"] == "uncertain"


def test_global_and_project_configuration_references_are_isolated(tmp_path):
    """@brief Explicit global references never enter a project's command queue."""
    profiles, web, admin, alpha, _ = setup_store(tmp_path)
    global_op = web.enqueue_configuration(admin["id"], "a" * 32, "global", project_id=None)
    project_op = web.enqueue_configuration(
        admin["id"], "b" * 32, "project", project_id=alpha.project_id)
    assert web.enqueue_configuration(
        admin["id"], "a" * 32, "global", project_id=None)["id"] == global_op["id"]
    with pytest.raises(WebStoreError):
        web.enqueue_configuration(admin["id"], "a" * 32, "global", project_id=alpha.project_id)
    command_worker = CommandWorker(
        profiles, web, runner=lambda *_: pytest.fail("unexpected effect"))
    assert command_worker.run_pending() == 0
    global_owner = web.register_worker("configuration")
    project_owner = web.register_worker("configuration", project_id=alpha.project_id)
    global_claim = web.claim_next(global_owner, domain="configuration_global")
    assert global_claim["id"] == global_op["id"]
    assert global_claim["project"] == global_claim["project_id"] == ""
    assert web.claim_next(project_owner, domain="configuration_project")["id"] == project_op["id"]
    web.authorize_effect(global_op["id"], owner=global_owner, generation=global_claim["generation"])
    web.finish(global_op["id"], "succeeded", "completed", owner=global_owner,
               generation=global_claim["generation"])
    developer = web.create_user("developer", "longer-password", "developer")
    with pytest.raises(WebStoreError):
        web.enqueue_configuration(developer["id"], "c" * 32, "denied", project_id=None)
    with pytest.raises(WebStoreError):
        web.enqueue_configuration(admin["id"], "secret=not-a-reference", "bad", project_id=None)


def test_stale_heartbeat_and_shutdown_do_not_steal_live_work(tmp_path):
    """@brief Heartbeat age and attempted shutdown never surrender active work."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    owner = web.register_worker("project", project_id=alpha.project_id)
    op = web.enqueue(admin["id"], "alpha", "start", "42", "one")
    claim = web.claim_next(owner, domain="execution")
    with web._connect() as connection:
        connection.execute("UPDATE worker_owners SET updated_at='2020-01-01T00:00:00+00:00'")
    assert web.worker_heartbeats(project_id=alpha.project_id)[0]["ready"] is False
    assert web.recover_interrupted() == 0
    with pytest.raises(WebStoreError):
        web.register_worker("project", project_id=alpha.project_id)
    with pytest.raises(WebStoreError):
        web.clear_worker(owner)
    web._process_probe = lambda pid: (_ for _ in ()).throw(OSError("uninspectable"))
    assert web.recover_interrupted() == 0
    web._process_probe = lambda pid: "birth"
    web.finish(op["id"], "failed", "refused", owner=owner, generation=claim["generation"])
    web.clear_worker(owner)


def test_child_participation_preserves_job_after_parent_death(tmp_path, monkeypatch):
    """@brief Recovery cannot steal a still-live child's effects or acknowledged job."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    pid = [100]
    births = {100: "parent", 200: "child"}
    monkeypatch.setattr("adore.web.store.os", SimpleNamespace(getpid=lambda: pid[0]))
    web._process_probe = births.get
    owner = web.register_worker("project", project_id=alpha.project_id)
    operation = web.enqueue(admin["id"], "alpha", "start", "42", "one")
    web.claim_next(owner, domain="execution")
    pid[0] = 200
    web.attach_worker(owner)
    births.pop(100)
    assert web.recover_interrupted() == 0
    assert web.operation(operation["id"])["status"] == "running"
    pid[0] = 100
    with pytest.raises(WebStoreError, match="live participants"):
        web.clear_worker(owner)
    births.pop(200)
    assert web.recover_interrupted() == 1


def test_recovery_rechecks_participants_after_liveness_probe(tmp_path, monkeypatch):
    """@brief A child attached during recovery invalidates the dead-owner snapshot."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    pid = [100]
    monkeypatch.setattr("adore.web.store.os", SimpleNamespace(getpid=lambda: pid[0]))
    web._process_probe = lambda pid: "parent" if pid == 100 else "child"
    owner = web.register_worker("project", project_id=alpha.project_id)
    operation = web.enqueue(admin["id"], "alpha", "start", "42", "one")
    web.claim_next(owner, domain="execution")
    entered, release = Event(), Event()

    def probe(probed_pid):
        """@brief Hold only recovery's parent probe while the child attaches."""
        if probed_pid == 100:
            entered.set()
            assert release.wait(timeout=3)
            return None
        return "child"

    web._process_probe = probe
    with ThreadPoolExecutor(max_workers=1) as pool:
        recovering = pool.submit(web.recover_interrupted)
        assert entered.wait(timeout=3)
        pid[0] = 200
        web.attach_worker(owner)
        release.set()
        assert recovering.result(timeout=3) == 0
    assert web.operation(operation["id"])["status"] == "running"


def test_revocation_at_claim_has_no_runner_effect(tmp_path):
    """@brief The atomic claim records a closed refusal for revoked access."""
    profiles, web, _, _, _ = setup_store(tmp_path)
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    op = web.enqueue(dev["id"], "alpha", "start", "42", "one")
    web.set_memberships(dev["id"], [])
    assert CommandWorker(profiles, web, runner=lambda *_: pytest.fail("effect")).run_pending() == 1
    assert web.operation(op["id"])["reason"] == "permission_revoked"


def test_cancel_success_requires_observed_cancelled_state(tmp_path):
    """@brief A real saved cancelled outcome permits a truthful acknowledgement."""
    profiles, web, admin, _, _ = setup_store(tmp_path)
    state = StateStore(profiles.default_store_root("alpha"))
    state.save(RunState("run-1", 42, lifecycle="working"))
    op = web.enqueue(admin["id"], "alpha", "cancel", "run-1", "cancel")

    def runner(argv, env):
        """@brief Queue/claim remains unconfirmed until the fake engine stops."""
        assert web.operation(op["id"])["status"] == "running"
        state.save(RunState("run-1", 42, lifecycle="cancelled"))
        return 0

    assert CommandWorker(profiles, web, runner=runner).run_pending() == 1
    assert web.operation(op["id"])["status"] == "succeeded"


def test_cli_attaches_and_fences_state_and_external_effects(tmp_path, monkeypatch):
    """@brief A child checks the same claim before state overwrite and publication commands."""
    from adore.cli import main
    from adore.web.worker_context import current_context

    profiles, web, admin, alpha, _ = setup_store(tmp_path)
    op = web.enqueue(admin["id"], "alpha", "start", "42", "one")
    owner = web.register_worker("project", project_id=alpha.project_id)
    claim = web.claim_next(owner, domain="execution")
    context = {"owner_id": owner.id, "owner_generation": owner.generation, "role": owner.role,
               "project_id": owner.project_id, "run_id": "", "operation_id": op["id"],
               "generation": claim["generation"]}
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    monkeypatch.setenv("ADORE_WORKER_CONTEXT", json.dumps(context))
    calls = []
    state = StateStore(profiles.default_store_root("alpha"))

    def command(args):
        """@brief Exercise the public child dispatch with entirely fake collaborators."""
        engine = SimpleNamespace(
            store=state, forge=SimpleNamespace(runner=lambda *a, **k: calls.append("forge")),
            worktrees=SimpleNamespace(runner=lambda *a, **k: calls.append("git")),
            containers=SimpleNamespace(runner=lambda *a, **k: calls.append("runtime")))
        context = current_context()
        context.bind_engine(engine)
        context.validate_configuration(profiles.config_path("alpha"))
        with pytest.raises(WebStoreError):
            context.validate_configuration(profiles.config_path("beta"))
        engine.forge.runner(["fake"])
        state.save(RunState("run-42", 42))
        state.save_ticket("run-42", {"iid": 42})
        state.journal("run-42", "picked", ticket=42)
        engine.on_admitted(state.load("run-42"))
        assert web.operation(op["id"])["status"] == "succeeded"
        rows = web.worker_heartbeats(role="run", run_id="run-42")
        assert len(rows) == 1 and rows[0]["ready"]
        context.heartbeat()
        before = (state.run_dir("run-42") / "state.json").read_bytes()
        with web._connect() as connection:
            connection.execute("UPDATE worker_owners SET status='dead' WHERE id=?", (owner.id,))
        for effect in (lambda: engine.forge.runner(["fake"]),
                       lambda: engine.worktrees.runner(["fake"]),
                       lambda: state.save(RunState("run-42", 42, lifecycle="failed")),
                       lambda: state.journal("run-42", "forbidden"), engine.before_effect):
            with pytest.raises(WebStoreError, match="ownership"):
                effect()
        assert (state.run_dir("run-42") / "state.json").read_bytes() == before
        return 0

    monkeypatch.setattr("adore.cli._cmd_run", command)
    assert main(["--profile", "alpha", "run", "--once", "--ticket", "42"]) == 0
    assert calls == ["forge"]
    assert current_context() is None
    assert web.worker_heartbeats(role="run", run_id="run-42") == []


@pytest.mark.parametrize("change", [{"ticket": "43"}, {"project": "beta"}, {"raw": "{}"}])
def test_cli_refuses_mismatched_or_corrupt_claim_transport(tmp_path, monkeypatch, change):
    """@brief Untrusted child context cannot retarget an operation or invoke the engine."""
    from adore.cli import main

    profiles, web, admin, alpha, _ = setup_store(tmp_path)
    op = web.enqueue(admin["id"], "alpha", "start", "42", "one")
    owner = web.register_worker("project", project_id=alpha.project_id)
    claim = web.claim_next(owner, domain="execution")
    context = {"owner_id": owner.id, "owner_generation": owner.generation, "role": owner.role,
               "project_id": owner.project_id, "run_id": "", "operation_id": op["id"],
               "generation": claim["generation"]}
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    monkeypatch.setenv("ADORE_WORKER_CONTEXT", change.get("raw", json.dumps(context)))
    monkeypatch.setattr("adore.cli._cmd_run", lambda *_: pytest.fail("unauthorized effect"))
    assert main(["--profile", change.get("project", "alpha"), "run", "--once", "--ticket",
                 change.get("ticket", "42")]) == 1


def test_retry_and_restart_cannot_claim_same_job_concurrently(tmp_path):
    """@brief Distinct operation keys/actions cannot duplicate a job's execution."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    web.enqueue(admin["id"], "alpha", "retry", "job-42", "retry")
    web.enqueue(admin["id"], "alpha", "restart", "job-42." + "a" * 64, "restart")
    owner = web.register_worker("project", project_id=alpha.project_id)
    assert web.claim_next(owner, domain="execution")["action"] == "retry"
    assert web.claim_next(owner, domain="execution") is None


def test_revocation_at_effect_barrier_refuses_without_crashing_worker(tmp_path, monkeypatch):
    """@brief Rights revoked after claim but before dispatch produce a closed refusal."""
    profiles, web, _, _, _ = setup_store(tmp_path)
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    operation = web.enqueue(dev["id"], "alpha", "start", "42", "one")
    entered, release = Event(), Event()
    authorize = web.authorize_effect

    def barrier(*args, **kwargs):
        """@brief Stop at the last ownership check before the external effect."""
        entered.set()
        assert release.wait(timeout=3)
        return authorize(*args, **kwargs)

    monkeypatch.setattr(web, "authorize_effect", barrier)
    worker = CommandWorker(profiles, web, runner=lambda *_: pytest.fail("revoked effect"))
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(worker.run_pending)
        assert entered.wait(timeout=3)
        web.set_memberships(dev["id"], [])
        release.set()
        assert result.result(timeout=3) == 1
    assert web.operation(operation["id"])["status"] == "failed"
    assert web.operation(operation["id"])["reason"] == "permission_revoked"


def test_distinct_owners_racing_one_job_have_one_winner(tmp_path):
    """@brief Different permitted scopes cannot execute one queued job twice."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    operation = web.enqueue(admin["id"], "alpha", "retry", "job-42", "one")
    owners = (web.register_worker("project", project_id=alpha.project_id),
              web.register_worker("run", project_id=alpha.project_id, run_id="job-42"))
    barrier = Barrier(2)

    def claim(owner):
        """@brief Race two distinct owner handles at the same SQLite boundary."""
        store = WebStore(web.path, process_probe=lambda pid: "birth")
        barrier.wait(timeout=3)
        return store.claim_next(owner, domain="execution")

    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = [row for row in pool.map(claim, owners) if row]
    assert len(claims) == 1 and claims[0]["id"] == operation["id"]
    loser = next(owner for owner in owners if owner.id != claims[0]["owner_id"])
    with pytest.raises(WebStoreError, match="ownership"):
        web.finish(operation["id"], "succeeded", "completed", owner=loser,
                   generation=claims[0]["generation"])


def test_heartbeats_and_shutdown_are_scoped_by_role_project_and_run(tmp_path):
    """@brief Supervisor shutdown cannot erase another role's heartbeat."""
    _, web, _, alpha, _ = setup_store(tmp_path)
    supervisor = web.register_worker("supervisor")
    run = web.register_worker("run", project_id=alpha.project_id, run_id="job-42")
    web.touch_worker(run)
    web.clear_worker(supervisor)
    assert web.worker_ready() is False
    rows = web.worker_heartbeats(role="run", project_id=alpha.project_id, run_id="job-42")
    assert len(rows) == 1 and rows[0]["ready"]
    assert web.worker_heartbeats(role="run", run_id="other") == []


@pytest.mark.parametrize("action,target", [
    ("start", "0"), ("start", "token=private"), ("start", None),
    ("retry", "../other"), ("restart", "job.unbound"),
    ("cancel", ""), ("pause", "other"), ("delete", "private-path"),
])
def test_queue_refuses_malformed_targets_without_retaining_them(tmp_path, action, target):
    """@brief Untrusted command targets cannot turn the queue into arbitrary data storage."""
    _, web, admin, _, _ = setup_store(tmp_path)
    with pytest.raises(WebStoreError):
        web.enqueue(admin["id"], "alpha", action, target, "invalid")
    assert web.operation_for_key(admin["id"], "invalid") is None


def test_corrupt_persisted_resource_binding_fails_closed(tmp_path):
    """@brief Corrupt resource keys cannot bypass the single-job claim fence."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    operation = web.enqueue(admin["id"], "alpha", "retry", "job-42", "one")
    owner = web.register_worker("project", project_id=alpha.project_id)
    with web._connect() as connection:
        connection.execute("UPDATE operations SET resource_key='other' WHERE id=?",
                           (operation["id"],))
    with pytest.raises(WebStoreError, match="corrupt"):
        web.claim_next(owner, domain="execution")
    with web._connect() as connection:
        assert connection.execute("SELECT status FROM operations WHERE id=?",
                                  (operation["id"],)).fetchone()[0] == "pending"


def test_corrupt_configuration_domain_cannot_be_consumed_as_execution(tmp_path):
    """@brief Persisted domain corruption cannot send a protected candidate to a job owner."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    operation = web.enqueue_configuration(
        admin["id"], "a" * 32, "one", project_id=alpha.project_id)
    with web._connect() as connection:
        connection.execute("UPDATE operations SET domain='execution' WHERE id=?",
                           (operation["id"],))
    owner = web.register_worker("project", project_id=alpha.project_id)
    with pytest.raises(WebStoreError, match="corrupt"):
        web.claim_next(owner, domain="execution")
    with web._connect() as connection:
        assert connection.execute("SELECT status FROM operations WHERE id=?",
                                  (operation["id"],)).fetchone()[0] == "pending"


def test_run_command_reuses_its_owner_through_scope_cleanup_and_completion(tmp_path):
    """@brief A run-role command retains its original fence until terminal completion."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    operation = web.enqueue(admin["id"], "alpha", "retry", "job-42", "one")
    owner = web.register_worker("run", project_id=alpha.project_id, run_id="job-42")
    claim = web.claim_next(owner, domain="execution")
    context = WorkerContext(web, owner, operation["id"], claim["generation"])
    with context.run_scope("job-42"):
        context.authorize()
        context.heartbeat()
        assert len(web.worker_heartbeats(role="run", run_id="job-42")) == 1
    context.close()
    web.finish(operation["id"], "succeeded", "completed", owner=owner,
               generation=claim["generation"])
    web.clear_worker(owner)


def test_recovery_participant_comparison_is_independent_of_pid_allocation_order(
    tmp_path, monkeypatch,
):
    """@brief A lower child PID cannot prevent recovery after all incarnations died."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    pid = [200]
    births = {200: "parent", 100: "child"}
    monkeypatch.setattr("adore.web.store.os", SimpleNamespace(getpid=lambda: pid[0]))
    web._process_probe = births.get
    owner = web.register_worker("project", project_id=alpha.project_id)
    operation = web.enqueue(admin["id"], "alpha", "start", "42", "one")
    web.claim_next(owner, domain="execution")
    pid[0] = 100
    web.attach_worker(owner)
    births.clear()
    assert web.recover_interrupted() == 1
    assert web.operation(operation["id"])["status"] == "uncertain"


def test_run_owner_claims_revision_bound_restart_but_not_another_run(tmp_path):
    """@brief Canonical run identity selects Restart without dropping its revision."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    web.enqueue(admin["id"], "alpha", "restart", "other." + "b" * 64, "other")
    operation = web.enqueue(admin["id"], "alpha", "restart", "job-42." + "a" * 64, "one")
    owner = web.register_worker("run", project_id=alpha.project_id, run_id="job-42")
    claim = web.claim_next(owner, domain="execution")
    assert claim is not None and claim["id"] == operation["id"]
    assert claim["run_id"] == "job-42." + "a" * 64


def test_restart_authorizes_its_exact_command_owner_while_reconciling_another_job(tmp_path):
    """@brief Multiple owned scopes cannot hide the canonical Restart command fence."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    operation = web.enqueue(admin["id"], "alpha", "restart", "job-42." + "a" * 64, "one")
    owner = web.register_worker("project", project_id=alpha.project_id)
    claim = web.claim_next(owner, domain="execution")
    context = WorkerContext(web, owner, operation["id"], claim["generation"])
    with context.run_scope("job-42"):
        with context.run_scope("other-job"):
            assert context.authorize()["id"] == operation["id"]
            assert len(web.worker_heartbeats(role="run", project_id=alpha.project_id)) == 2
        context.authorize()
    context.close()


def test_operation_cannot_retarget_another_project_under_claimed_owner(tmp_path):
    """@brief A valid-looking persisted project change cannot reuse another project's fence."""
    _, web, admin, alpha, beta = setup_store(tmp_path)
    operation = web.enqueue(admin["id"], "alpha", "retry", "job-42", "one")
    owner = web.register_worker("project", project_id=alpha.project_id)
    claim = web.claim_next(owner, domain="execution")
    with web._connect() as connection:
        connection.execute("UPDATE operations SET project='beta',project_id=? WHERE id=?",
                           (beta.project_id, operation["id"]))
    with pytest.raises(WebStoreError, match="ownership"):
        web.authorize_effect(operation["id"], owner=owner, generation=claim["generation"])


def test_child_pins_immutable_request_fields_across_effects(tmp_path):
    """@brief Valid-looking persisted target changes cannot retarget an attached command."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    operation = web.enqueue(admin["id"], "alpha", "retry", "job-42", "one")
    owner = web.register_worker("project", project_id=alpha.project_id)
    claim = web.claim_next(owner, domain="execution")
    context = WorkerContext(web, owner, operation["id"], claim["generation"])
    context.authorize()
    with web._connect() as connection:
        connection.execute(
            "UPDATE operations SET run_id='other',resource_key='job:other' WHERE id=?",
            (operation["id"],))
    with pytest.raises(WebStoreError, match="identity changed"):
        context.authorize()


def test_sqlite_heartbeat_failure_is_typed_and_blocks_child_effects(tmp_path):
    """@brief Storage failure sets explicit failure evidence instead of killing the beat thread."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    operation = web.enqueue(admin["id"], "alpha", "retry", "job-42", "one")
    owner = web.register_worker("project", project_id=alpha.project_id)
    claim = web.claim_next(owner, domain="execution")
    with web._connect() as connection:
        connection.execute("CREATE TRIGGER reject_heartbeat BEFORE UPDATE ON worker_owners "
                           "BEGIN SELECT RAISE(ABORT,'private database detail'); END")
    with pytest.raises(WebStoreError):
        web.touch_worker(owner)
    context = WorkerContext(web, owner, operation["id"], claim["generation"])
    context.heartbeat()
    assert context.heartbeat_failed.is_set()
    with pytest.raises(WebStoreError, match="heartbeat"):
        context.authorize()


def test_parent_worker_observes_heartbeat_storage_failure(tmp_path, monkeypatch):
    """@brief A failing parent heartbeat terminates the worker after the bounded command."""
    profiles, web, admin, _, _ = setup_store(tmp_path)
    web.enqueue(admin["id"], "alpha", "start", "42", "one")
    entered, release, failed = Event(), Event(), Event()
    errors = []
    touch = web.touch_worker

    def monitored_touch(owner):
        """@brief Observe the actual storage fault at its typed boundary."""
        try:
            touch(owner)
        except WebStoreError:
            failed.set()
            raise

    def runner(*args):
        """@brief Hold a bounded fake engine while its parent heartbeat fails."""
        entered.set()
        assert release.wait(timeout=3)
        return 0

    worker = CommandWorker(profiles, web, runner=runner)
    monkeypatch.setattr(web, "touch_worker", monitored_touch)

    def run():
        """@brief Retain the public worker's observed failure for assertion."""
        try:
            worker.run_forever(interval=0.01, heartbeat_interval=0.01)
        except RuntimeError as exc:
            errors.append(str(exc))

    thread = Thread(target=run)
    thread.start()
    try:
        assert entered.wait(timeout=3)
        with web._connect() as connection:
            connection.execute("CREATE TRIGGER reject_parent_heartbeat "
                               "BEFORE UPDATE ON worker_owners "
                               "BEGIN SELECT RAISE(ABORT,'private database detail'); END")
        assert failed.wait(timeout=3)
        with web._connect() as connection:
            connection.execute("DROP TRIGGER reject_parent_heartbeat")
    finally:
        release.set()
        thread.join(timeout=3)
    assert not thread.is_alive()
    assert errors == ["web control worker heartbeat failed"]


@pytest.mark.parametrize("validation", ["audit", "owner-history"])
def test_historical_validation_does_not_hold_shared_writer_transaction(
    tmp_path, monkeypatch, validation,
):
    """@brief Another role's heartbeat commits while historical projection is held at a barrier."""
    _, web, _, alpha, _ = setup_store(tmp_path)
    supervisor = web.register_worker("supervisor")
    previous = web.register_worker("project", project_id=alpha.project_id)
    web.clear_worker(previous)
    web.audit(1, "ownership-proof", "alpha")
    entered, release, written = Event(), Event(), Event()
    if validation == "audit":
        original = WebStore._audit_projection

        def project(row):
            """@brief Hold Python audit validation after the SELECT has completed."""
            entered.set()
            assert release.wait(timeout=5)
            return original(row)

        monkeypatch.setattr(WebStore, "_audit_projection", staticmethod(project))
        def action():
            """@brief Reopen the existing store without taking a writer transaction."""
            return WebStore(web.path, process_probe=lambda pid: "birth")
    else:
        original = web._worker_record

        def record(row):
            """@brief Hold only historical owner validation, not the independent writer."""
            if row["id"] == previous.id:
                entered.set()
                assert release.wait(timeout=5)
            return original(row)

        monkeypatch.setattr(web, "_worker_record", record)
        def action():
            """@brief Validate historical owners before the generation CAS transaction."""
            return web.register_worker("project", project_id=alpha.project_id)

    def write():
        """@brief Commit an independent real SQLite heartbeat while validation is held."""
        web.touch_worker(supervisor)
        written.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        projecting = pool.submit(action)
        try:
            assert entered.wait(timeout=3)
            writer = pool.submit(write)
            assert written.wait(timeout=3), "historical validation blocked an unrelated writer"
            writer.result(timeout=3)
        finally:
            release.set()
        projecting.result(timeout=3)


def test_another_active_run_owner_defers_job_claim_and_refuses_late_effect(tmp_path):
    """@brief A project command cannot reset or delete another live run owner's job."""
    _, web, admin, alpha, _ = setup_store(tmp_path)
    operation = web.enqueue(admin["id"], "alpha", "retry", "job-42", "one")
    project = web.register_worker("project", project_id=alpha.project_id)
    run = web.register_worker("run", project_id=alpha.project_id, run_id="job-42")
    assert web.claim_next(project, domain="execution") is None
    web.clear_worker(run)
    claim = web.claim_next(project, domain="execution")
    other = web.register_worker("run", project_id=alpha.project_id, run_id="job-42")
    with pytest.raises(WebStoreError, match="ownership"):
        web.authorize_effect(operation["id"], owner=project, generation=claim["generation"])
    assert web.worker_heartbeats(role="run", run_id="job-42")[0]["generation"] == other.generation


@pytest.mark.parametrize("generation", [0, -1, 1.5, "corrupt"])
def test_corrupt_historical_owner_generation_refuses_successor(tmp_path, generation):
    """@brief Invalid durable generations never create a fresh owner or raise raw type errors."""
    _, web, _, alpha, _ = setup_store(tmp_path)
    owner = web.register_worker("project", project_id=alpha.project_id)
    web.clear_worker(owner)
    with web._connect() as connection:
        connection.execute("UPDATE worker_owners SET generation=? WHERE id=?",
                           (generation, owner.id))
    with pytest.raises(WebStoreError):
        web.register_worker("project", project_id=alpha.project_id)
    with web._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM worker_owners").fetchone()[0] == 1


@pytest.mark.parametrize("index", [
    "worker_scope", "worker_generations", "active_operation_resource",
])
def test_existing_store_refuses_missing_ownership_indexes(tmp_path, index):
    """@brief Missing current ownership constraints never become a permissive store."""
    _, web, _, _, _ = setup_store(tmp_path)
    with web._connect() as connection:
        connection.execute(f"DROP INDEX {index}")
    with pytest.raises(WebStoreError, match="ownership indexes are corrupt"):
        WebStore(web.path)


def test_delayed_fresh_opener_does_not_lock_an_already_initialized_store(tmp_path, monkeypatch):
    """@brief A stale new-file observation never authorizes locked historical validation."""
    path = tmp_path / "web.db"
    observed, resume, projecting, release, written = (Event() for _ in range(5))
    delayed = [None]
    connect = WebStore._connect
    projection = WebStore._audit_projection

    @contextmanager
    def delayed_connect(store):
        """@brief Pause one opener after its new-file check but before SQLite opens."""
        if delayed[0] is None:
            delayed[0] = store
            observed.set()
            assert resume.wait(timeout=5)
        with connect(store) as connection:
            yield connection

    def hold_projection(row):
        """@brief Hold the delayed opener after another initializer committed history."""
        projecting.set()
        assert release.wait(timeout=5)
        return projection(row)

    monkeypatch.setattr(WebStore, "_connect", delayed_connect)
    with ThreadPoolExecutor(max_workers=2) as pool:
        opening = pool.submit(WebStore, path, process_probe=lambda pid: "birth")
        try:
            assert observed.wait(timeout=3)
            active = WebStore(path, process_probe=lambda pid: "birth")
            active.audit(1, "ownership-proof")
            owner = active.register_worker("supervisor")
            monkeypatch.setattr(WebStore, "_audit_projection", staticmethod(hold_projection))
            resume.set()
            assert projecting.wait(timeout=3)

            def write():
                """@brief Prove heartbeat progress before the delayed projection is released."""
                active.touch_worker(owner)
                written.set()

            writer = pool.submit(write)
            assert written.wait(timeout=3), "stale fresh opener kept a writer lock"
            writer.result(timeout=3)
        finally:
            resume.set()
            release.set()
        opening.result(timeout=3)


def test_schema_zero_waiter_releases_writer_after_initializer_commits(tmp_path, monkeypatch):
    """@brief A waiter observing completed initialization switches to unlocked validation."""
    path = tmp_path / "web.db"
    hashing, finish_hash, waiting, projecting, release, written = (Event() for _ in range(6))
    first = [None]
    lane = local()
    connect, audit_storage = WebStore._connect, WebStore._audit_storage
    from adore.web import store as store_module

    hasher = store_module._HASHER

    def hash_password(password):
        """@brief Hold the initializer while its uncommitted store reports schema zero."""
        hashing.set()
        assert finish_hash.wait(timeout=5)
        return hasher.hash(password)

    @contextmanager
    def traced_connect(store):
        """@brief Observe the second opener waiting for its real SQLite writer lock."""
        if first[0] is None:
            first[0] = store
        previous = getattr(lane, "waiter", False)
        lane.waiter = store is not first[0]
        try:
            with connect(store) as connection:
                if lane.waiter:
                    connection.set_trace_callback(
                        lambda sql: waiting.set() if sql == "BEGIN IMMEDIATE" else None)
                yield connection
        finally:
            lane.waiter = previous

    def hold_validation(connection):
        """@brief Hold only the waiter, after it has re-read the committed schema."""
        audit_storage(connection)
        if getattr(lane, "waiter", False):
            projecting.set()
            assert release.wait(timeout=5)

    monkeypatch.setattr(store_module, "_HASHER", SimpleNamespace(hash=hash_password))
    monkeypatch.setattr(WebStore, "_connect", traced_connect)
    monkeypatch.setattr(WebStore, "_audit_storage", staticmethod(hold_validation))
    with ThreadPoolExecutor(max_workers=3) as pool:
        initializing = pool.submit(WebStore, path, process_probe=lambda pid: "birth")
        try:
            assert hashing.wait(timeout=3)
            opening = pool.submit(WebStore, path, process_probe=lambda pid: "birth")
            assert waiting.wait(timeout=3)
            finish_hash.set()
            active = initializing.result(timeout=3)
            assert projecting.wait(timeout=3)

            def write():
                """@brief Prove another role can register while the waiter validates history."""
                active.register_worker("supervisor")
                written.set()

            writer = pool.submit(write)
            assert written.wait(timeout=3), "schema-zero waiter kept the initialization writer lock"
            writer.result(timeout=3)
        finally:
            finish_hash.set()
            release.set()
        opening.result(timeout=3)


@pytest.mark.parametrize("role", ["project", "run"])
@pytest.mark.parametrize("action", ["retry", "restart"])
def test_bound_job_command_owns_run_before_handler_and_preserves_main_owner(
    tmp_path, monkeypatch, role, action,
):
    """@brief Reset/teardown cannot begin before exclusive run ownership is held."""
    from adore.cli import main
    from adore.web.worker_context import current_context

    profiles, web, admin, alpha, _ = setup_store(tmp_path)
    target = "job-42" + ("." + "a" * 64 if action == "restart" else "")
    operation = web.enqueue(admin["id"], "alpha", action, target, "one")
    owner = web.register_worker(role, project_id=alpha.project_id,
                                run_id="job-42" if role == "run" else "")
    claim = web.claim_next(owner, domain="execution")
    context = {"owner_id": owner.id, "owner_generation": owner.generation, "role": owner.role,
               "project_id": owner.project_id, "run_id": owner.run_id,
               "operation_id": operation["id"], "generation": claim["generation"]}
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    monkeypatch.setenv("ADORE_WORKER_CONTEXT", json.dumps(context))

    def handler(args):
        """@brief Observe authority before the fake handler could reset/delete anything."""
        attached = current_context()
        assert attached.authorize()["id"] == operation["id"]
        rows = web.worker_heartbeats(role="run", project_id=alpha.project_id, run_id="job-42")
        assert len(rows) == 1 and rows[0]["ready"]
        with attached.run_scope("job-42"):
            attached.authorize()
        return 0

    monkeypatch.setattr("adore.cli._cmd_run_op", handler)
    argv = ["--profile", "alpha", action, "job-42"]
    if action == "restart":
        argv += ["--force", "--expected-revision", "a" * 64]
    assert main(argv) == 0
    assert bool(web.worker_heartbeats(role="run", run_id="job-42")) == (role == "run")
    web.finish(operation["id"], "succeeded", "completed", owner=owner,
               generation=claim["generation"])
    web.clear_worker(owner)


@pytest.mark.parametrize("missing,alive,expected", [
    ("boot", True, "unknown"), ("pid", True, "unknown"), ("pid", False, None),
    (None, True, "birth"),
])
def test_linux_process_evidence_never_confuses_unknown_and_dead(
    monkeypatch, missing, alive, expected,
):
    """@brief Missing boot or masked live PID evidence cannot justify owner recovery."""
    from adore.web.ownership import process_birth

    boot = "12345678-1234-1234-1234-123456789abc"

    def path(name):
        """@brief Supply Linux pseudo-files without touching host process state."""
        def read_text(**kwargs):
            """@brief Simulate independently missing boot and process evidence."""
            if ((name.endswith("boot_id") and missing == "boot")
                    or (name.endswith("/stat") and missing == "pid")):
                raise FileNotFoundError(name)
            return boot if name.endswith("boot_id") else "123 (process) S " + "0 " * 18 + "42"
        return SimpleNamespace(read_text=read_text)

    monkeypatch.setattr("adore.web.ownership.os", SimpleNamespace(name="posix"))
    monkeypatch.setattr("adore.web.ownership.platform.system", lambda: "Linux")
    monkeypatch.setattr("adore.web.ownership.Path", path)
    monkeypatch.setattr("adore.util.process_alive", lambda pid: alive)
    if expected == "unknown":
        with pytest.raises(WebStoreError):
            process_birth(123)
    else:
        assert process_birth(123) == (boot + ":42" if expected == "birth" else None)


# END OF FILE
