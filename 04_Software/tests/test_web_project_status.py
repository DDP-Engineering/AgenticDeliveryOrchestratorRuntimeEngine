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
@file       test_web_project_status.py
@brief      Project capacity, worker diagnostics and durable feedback contracts.
@details    Uses isolated current stores and offline configuration consumers.
"""

# IMPORTS
from pathlib import Path

from adore.config import load_config
from adore.portable_settings import export_settings, parse_settings
from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from fastapi.testclient import TestClient as HttpClient
import pytest

from tests.configuration_client import TestClient


@pytest.fixture
def setup(tmp_path):
    """@brief Create two independently configured project stores and an authenticated API."""
    profiles = ProfileStore(tmp_path / "home")
    example = (Path(__file__).parents[1] / "config.example.toml").read_text(encoding="utf-8")
    states = {}
    for name in ("alpha", "beta"):
        root = tmp_path / name
        profiles.create(name, store_root=str(root))
        profiles.config_path(name).write_text(
            example.replace('store_root = ".adore"', f'store_root = "{root.as_posix()}"'),
            encoding="utf-8",
        )
        states[name] = StateStore(root)
        states[name].pause()
    app = create_app(profiles.home)
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        yield profiles, states, app.state.web_store, client, {"X-CSRF-Token": login.json()["csrf"]}


def test_capacity_queue_and_feedback_are_project_scoped(setup):
    """@brief A full project queues work while B retains its free slot and feedback."""
    profiles, states, web, client, headers = setup
    aid, bid = (profiles.load(name).project_id for name in ("alpha", "beta"))
    web.register_worker("supervisor")
    web.register_worker("configuration")
    worker_a = web.register_worker("project", project_id=aid)
    web.register_worker("project", project_id=bid)
    states["alpha"].save(RunState("busy", 1, lifecycle="working"))
    start = web.enqueue(1, "alpha", "start", "2", "a-start")
    response = client.get(f"/api/v1/projects/{aid}/capacity")
    assert response.status_code == 200, response.text
    data = response.json()
    assert (
        data["project_id"],
        data["limit"],
        data["occupied"],
        data["free"],
        data["waiting_jobs"],
    ) == (aid, 1, 1, 0, 1)
    assert data["queue"] == [{"id": start["id"], "action": "start", "reason": "project_limit"}]
    b = client.get(f"/api/v1/projects/{bid}/capacity").json()
    assert (b["limit"], b["occupied"], b["free"], b["waiting_jobs"], b["available"]) == (
        1,
        0,
        1,
        0,
        True,
    )
    assert b["recent_operations"] == []
    assert data["recent_operations"][0]["id"] == start["id"]
    states["alpha"].save(RunState("busy", 1, lifecycle="failed"))
    web.register_worker("run", project_id=aid, run_id="busy")
    retry = web.enqueue(1, "alpha", "retry", "busy", "a-retry")
    data = client.get(f"/api/v1/projects/{aid}/capacity").json()
    assert next(row for row in data["queue"] if row["id"] == retry["id"])["reason"] == "same_job"
    web.clear_worker(worker_a)
    data = client.get(f"/api/v1/projects/{aid}/capacity").json()
    assert data["worker"]["heartbeat"] == "missing" and not data["available"]
    assert (
        next(row for row in data["queue"] if row["id"] == start["id"])["reason"]
        == "worker_unavailable"
    )
    assert client.get(f"/api/v1/projects/{bid}/capacity").json()["available"]
    assert client.get("/api/v1/ready").status_code == 200
    started_b = client.post(
        f"/api/v1/projects/{bid}/operations/start",
        headers=headers,
        json={"ticket_iid": 3, "idempotency_key": "independent-b"},
    )
    assert started_b.status_code == 200 and started_b.json()["status"] == "pending"
    b_status = client.get(f"/api/v1/projects/{bid}/capacity").json()
    assert b_status["waiting_jobs"] == 1
    assert b_status["queue"][0]["reason"] == "dispatching"


def test_roles_readiness_and_corrupt_heartbeat(setup):
    """@brief Server readiness names configuration loss and project loss stays local."""
    _profiles, _states, web, client, _headers = setup
    supervisor = web.register_worker("supervisor")
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["detail"]["components"] == ["configuration"]
    configuration = web.register_worker("configuration")
    web.set_worker_activity(configuration, "busy")
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["components"]["configuration"]["activity"] == "busy"
    workers = client.get("/api/v1/system/workers")
    assert workers.status_code == 200, workers.text
    assert {row["role"] for row in workers.json()["workers"]} == {
        "supervisor",
        "configuration",
        "project",
    }
    assert len([row for row in workers.json()["workers"] if row["role"] == "project"]) == 2
    assert all("pid" not in row and "generation" not in row for row in workers.json()["workers"])
    with web._connect() as connection:
        connection.execute(
            "UPDATE worker_owners SET updated_at='2000-01-01T00:00:00+00:00' WHERE id=?",
            (configuration.id,),
        )
    assert client.get("/api/v1/ready").json()["detail"]["components"] == ["configuration"]
    with web._connect() as connection:
        connection.execute(
            "UPDATE worker_owners SET updated_at='broken' WHERE id=?", (supervisor.id,)
        )
    assert client.get("/api/v1/system/workers").status_code == 503


@pytest.mark.parametrize("role", ["project", "run", "command"])
def test_corrupt_project_heartbeat_does_not_break_other_projects_or_server(setup, role):
    """@brief Only A refuses capacity when its own project worker timestamp is damaged."""
    profiles, _states, web, client, _headers = setup
    web.register_worker("supervisor")
    web.register_worker("configuration")
    aid, bid = (profiles.load(name).project_id for name in ("alpha", "beta"))
    owner = web.register_worker(role, project_id=aid, run_id="busy" if role == "run" else "")
    web.register_worker("project", project_id=bid)
    with web._connect() as connection:
        connection.execute("UPDATE worker_owners SET updated_at='broken' WHERE id=?", (owner.id,))
    assert client.get(f"/api/v1/projects/{aid}/capacity").status_code == 503
    assert client.get(f"/api/v1/projects/{bid}/capacity").status_code == 200
    assert client.get("/api/v1/ready").status_code == 200


@pytest.mark.parametrize("already_started", [False, True])
def test_reduced_limit_preserves_reservations_and_bounds_actual_executor_starts(
    tmp_path, already_started
):
    """@brief Queued reservations start one at a time at N=1; two started jobs continue."""
    from hashlib import sha256

    from adore.web.processes import stop_trees

    from tests.test_web_supervisor import eventually, project, reserve, start_project

    profiles = ProfileStore(tmp_path / "home")
    profile = project(profiles, "alpha", limit=2)
    first, second = reserve(profiles, "alpha", 7), reserve(profiles, "alpha", 8)
    app = create_app(profiles.home)
    web = app.state.web_store
    web.register_worker("supervisor")
    worker = start_project(profiles, web, profile)
    results = [first, second]
    markers = [
        profiles.home / "barriers" / (profile.project_id + "-" + row["run_id"]) for row in results
    ]
    state = StateStore(profile.store_root)
    try:
        if already_started:
            assert worker.tick()
            eventually(lambda: worker.tick() and all(marker.exists() for marker in markers))
            assert all(not state.load(row["run_id"]).execution_pending for row in results)
        with TestClient(app) as client:
            csrf = client.post(
                "/api/v1/session", json={"username": "admin", "password": "admin"}
            ).json()["csrf"]
            revision = sha256(profiles.config_path("alpha").read_bytes()).hexdigest()
            response = client.post(
                "/api/v1/projects/alpha/config/pending",
                headers={"X-CSRF-Token": csrf},
                json={"key": "polling.max_concurrent_runs", "value": "1", "revision": revision},
            )
            assert response.status_code == 200, response.text
        assert reserve(profiles, "alpha", 9)["at_capacity"]
        assert worker.tick()
        if already_started:
            assert len(worker.children) == 2
            assert all(child.poll() is None for child in worker.children.values())
            assert not any(marker.with_suffix(".ended").exists() for marker in markers)
            for marker in markers:
                marker.with_suffix(".release").touch()
            eventually(lambda: all(child.poll() is not None for child in worker.children.values()))
            assert all(child.poll() == 0 for child in worker.children.values())
        else:
            eventually(lambda: markers[0].exists())
            assert len(worker.children) == 1
            assert not markers[1].exists()
            assert state.load(second["run_id"]).execution_pending
            assert worker.tick()
            assert len(worker.children) == 1 and not markers[1].exists()
            with TestClient(app) as status_client:
                status_client.post(
                    "/api/v1/session", json={"username": "admin", "password": "admin"}
                )
                status = status_client.get("/api/v1/projects/alpha/capacity").json()
                assert status["waiting_runs"] == [{"ticket_iid": 8, "reason": "staged_change"}]
            markers[0].with_suffix(".release").touch()
            child = worker.children["run:" + first["run_id"]]
            eventually(lambda: child.poll() is not None)
            assert child.poll() == 0, child.tail()
            assert worker.tick()
            eventually(lambda: markers[1].exists())
            assert len(worker.children) == 1
            assert not state.load(second["run_id"]).execution_pending
            markers[1].with_suffix(".release").touch()
            child = worker.children["run:" + second["run_id"]]
            eventually(lambda: child.poll() is not None)
            assert child.poll() == 0, child.tail()
        assert all(state.load(row["run_id"]).lifecycle == "awaiting-approval" for row in results)
    finally:
        stop_trees(list(worker.children.values()))


def test_corrupt_inputs_and_unauthorized_scope_fail_closed(setup):
    """@brief Corrupt config/queue never invents a free slot or leaks a foreign project."""
    profiles, _states, web, client, _headers = setup
    with HttpClient(create_app(profiles.home)) as anonymous:
        assert anonymous.get("/api/v1/projects/alpha/capacity").status_code == 401
    dev = web.create_user("dev", "test-password", "developer")
    web.set_memberships(dev["id"], ["beta"])
    with HttpClient(create_app(profiles.home)) as developer:
        developer.post("/api/v1/session", json={"username": "dev", "password": "test-password"})
        assert developer.get("/api/v1/projects/alpha/capacity").status_code == 404
        assert developer.get("/api/v1/system/workers").status_code == 403
    path = profiles.config_path("alpha")
    saved = path.read_bytes()
    path.write_text("[broken", encoding="utf-8")
    assert client.get("/api/v1/projects/alpha/capacity").status_code == 503
    assert client.get("/api/v1/projects/beta/capacity").status_code == 200
    path.write_bytes(saved)
    operation = web.enqueue(1, "alpha", "start", "2", "corrupt")
    with web._connect() as connection:
        connection.execute(
            "UPDATE operations SET resource_key='invalid' WHERE id=?", (operation["id"],)
        )
    assert client.get("/api/v1/projects/alpha/capacity").status_code == 503
    assert client.get("/api/v1/projects/beta/capacity").status_code == 200


def test_invalid_limit_reduction_staging_and_independent_save(setup):
    """@brief Invalid/reduced N preserves A while idle B saves its canonical N."""
    profiles, states, _web, client, headers = setup
    path = profiles.config_path("alpha")
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "max_concurrent_runs = 1", "max_concurrent_runs = 3"
        ),
        encoding="utf-8",
    )
    states["alpha"].save(RunState("busy-one", 1, lifecycle="working"))
    states["alpha"].save(RunState("busy-two", 2, lifecycle="working"))
    original = path.read_bytes()
    revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
    for value in ("0", "-1", "1.5", "true", "no"):
        response = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={"key": "polling.max_concurrent_runs", "value": value, "revision": revision},
        )
        assert response.status_code == 400, response.text
    response = client.post(
        "/api/v1/projects/alpha/config/pending",
        headers=headers,
        json={"key": "polling.max_concurrent_runs", "value": "1", "revision": revision},
    )
    assert response.status_code == 200, response.text
    pending = response.json()
    result = client.post(
        "/api/v1/projects/alpha/config/apply",
        headers=headers,
        json={"base_revision": revision, "candidate_revision": pending["candidate_revision"]},
    )
    assert (
        result.status_code == 409 and result.json()["detail"]["code"] == "capacity_below_occupancy"
    ), result.text
    assert path.read_bytes() == original
    capacity = client.get("/api/v1/projects/alpha/capacity").json()
    assert capacity["staged_change"] and capacity["staged_limit"] == 1
    assert capacity["limit"] == 1 and capacity["active_limit"] == 3 and capacity["free"] == 0
    assert capacity["recent_operations"][0]["status"] == "failed"
    assert capacity["recent_operations"][0]["reason"] == "capacity_below_occupancy"
    revision_b = client.get("/api/v1/projects/beta/config").json()["revision"]
    staged_b = client.post(
        "/api/v1/projects/beta/config/pending",
        headers=headers,
        json={"key": "polling.max_concurrent_runs", "value": "2", "revision": revision_b},
    ).json()
    applied = client.post(
        "/api/v1/projects/beta/config/apply",
        headers=headers,
        json={"base_revision": revision_b, "candidate_revision": staged_b["candidate_revision"]},
    )
    assert applied.status_code == 200, applied.text
    assert client.get("/api/v1/projects/beta/capacity").json()["limit"] == 2
    assert client.get("/api/v1/projects/alpha/capacity").json()["limit"] == 1
    assert (
        parse_settings(export_settings(profiles.config_path("beta").read_bytes()))["polling"][
            "max_concurrent_runs"
        ]
        == 2
    )


def test_staged_reduction_fences_admission_and_preserves_existing_jobs(tmp_path, monkeypatch):
    """@brief Occupancy two and staged N=1 blocks new admission until both jobs settle."""
    from dataclasses import replace

    from tests.supervisor_helper import offline_engine
    from tests.test_web_supervisor import project, reserve

    profiles = ProfileStore(tmp_path / "home")
    project(profiles, "alpha", limit=2)
    first = reserve(profiles, "alpha", 7)
    second = reserve(profiles, "alpha", 8)
    source = profiles.config_path("alpha")
    original = source.read_bytes()
    with TestClient(create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        staged = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers={"X-CSRF-Token": csrf},
            json={"key": "polling.max_concurrent_runs", "value": "1", "revision": revision},
        )
        assert staged.status_code == 200, staged.text
        waiting = client.get("/api/v1/projects/alpha/capacity").json()
        assert waiting["waiting_jobs"] == 2 and waiting["free"] == 0
        assert {item["ticket_iid"] for item in waiting["waiting_runs"]} == {7, 8}
        assert all(item["reason"] == "worker_unavailable" for item in waiting["waiting_runs"])
        engine, forge, *_ = offline_engine(profiles, "alpha")
        forge.ticket = replace(forge.ticket, iid=9)
        assert engine.poll_once(ticket_iid=9, admit_only=True)["at_capacity"]
        continued = []
        monkeypatch.setattr(engine, "_conduct", lambda run, ticket: continued.append(run.run_id))
        assert engine.conduct_run(first["run_id"])
        assert not engine.conduct_run(second["run_id"])
        assert engine.store.load(second["run_id"]).execution_pending
        assert continued == [first["run_id"]]
        cleanup = engine.store.load(first["run_id"])
        cleanup.lifecycle, cleanup.execution_pending = "handoff-pending", True
        engine.store.save(cleanup)
        assert not engine.conduct_run(second["run_id"])
        assert engine.store.load(second["run_id"]).execution_pending
        forge.ticket = replace(forge.ticket, iid=9, labels=["P1", "agent-ready"])
        run = engine.store.load(first["run_id"])
        run.lifecycle = "done"
        run.execution_pending = False
        engine.store.save(run)
        assert engine.poll_once(ticket_iid=9, admit_only=True)["at_capacity"]
        assert engine.conduct_run(second["run_id"])
        assert continued == [first["run_id"], second["run_id"]]
        web = client.app.state.web_store
        web.register_worker("supervisor")
        web.register_worker("project", project_id=profiles.load("alpha").project_id)
        queued = web.enqueue(1, "alpha", "start", "9", "wait-lower-limit")
        status = client.get("/api/v1/projects/alpha/capacity").json()
        assert (
            next(row for row in status["queue"] if row["id"] == queued["id"])["reason"]
            == "staged_change"
        )
        run = engine.store.load(second["run_id"])
        run.lifecycle = "done"
        engine.store.save(run)
        forge.ticket = replace(forge.ticket, iid=9, labels=["P1", "agent-ready"])
        assert engine.poll_once(ticket_iid=9, admit_only=True)["picked"] == 9
        assert source.read_bytes() == original
        assert load_config(source).polling.max_concurrent_runs == 2


def test_omitted_limit_has_same_default_in_api_and_portable_import(setup):
    """@brief The only canonical field defaults to one across saved and portable configuration."""
    profiles, _states, _web, client, _headers = setup
    path = profiles.config_path("beta")
    path.write_text(
        path.read_text(encoding="utf-8").replace("max_concurrent_runs = 1", ""), encoding="utf-8"
    )
    assert client.get("/api/v1/projects/beta/capacity").json()["limit"] == 1
    assert parse_settings(export_settings(path.read_bytes()))["polling"]["max_concurrent_runs"] == 1


def test_busy_initial_start_keeps_dispatch_until_operator_lock_released(tmp_path, monkeypatch):
    """@brief Bounded initial-start contention retains authority for later execution."""
    from tests.supervisor_helper import offline_engine
    from tests.test_web_supervisor import project, reserve

    profiles = ProfileStore(tmp_path / "home")
    profile = project(profiles, "alpha")
    reserved = reserve(profiles, "alpha", 7)
    engine, *_ = offline_engine(profiles, "alpha")
    peer = StateStore(profile.store_root)
    assert peer.acquire_lock()
    try:
        assert not engine.conduct_run(reserved["run_id"])
        assert engine.store.load(reserved["run_id"]).execution_pending
        assert engine.store.load_dispatch(reserved["run_id"])["status"] == "queued"
    finally:
        peer.release_lock()
    continued = []
    monkeypatch.setattr(engine, "_conduct", lambda run, ticket: continued.append(run.run_id))
    assert engine.conduct_run(reserved["run_id"])
    assert continued == [reserved["run_id"]]


@pytest.mark.parametrize("damage", ["invalid-json", "wrong-hash", "wrong-base", "boolean-limit"])
def test_staged_capacity_corruption_blocks_only_its_project(setup, damage):
    """@brief Corrupt staged admission evidence is refused without guessing active capacity."""
    from hashlib import sha256
    import json

    profiles, _states, _web, client, headers = setup
    revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
    response = client.post(
        "/api/v1/projects/alpha/config/pending",
        headers=headers,
        json={"key": "polling.max_concurrent_runs", "value": "1", "revision": revision},
    )
    assert response.status_code == 200, response.text
    path = profiles.profile_dir("alpha") / "pending_config.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if damage == "wrong-hash":
        value["candidate_revision"] = "0" * 64
    elif damage == "wrong-base":
        value["base_revision"] = "0" * 64
        value["candidate_text"] += "\n# different bytes\n"
        value["candidate_revision"] = sha256(value["candidate_text"].encode()).hexdigest()
    elif damage == "boolean-limit":
        value["candidate_text"] = value["candidate_text"].replace(
            "max_concurrent_runs = 1", "max_concurrent_runs = true"
        )
        value["candidate_revision"] = sha256(value["candidate_text"].encode()).hexdigest()
    path.write_text("{" if damage == "invalid-json" else json.dumps(value), encoding="utf-8")
    assert client.get("/api/v1/projects/alpha/capacity").status_code == 503
    from adore.state import StateError

    from tests.supervisor_helper import offline_engine

    engine, *_ = offline_engine(profiles, "alpha")
    with pytest.raises(StateError, match="capacity"):
        engine.poll_once(ticket_iid=7, admit_only=True)
    assert engine.store.list_runs() == []
    assert client.get("/api/v1/projects/beta/capacity").status_code == 200
    assert (
        client.delete("/api/v1/projects/alpha/config/pending", headers=headers).status_code == 200
    )
    assert client.get("/api/v1/projects/alpha/capacity").status_code == 200


# END OF FILE
