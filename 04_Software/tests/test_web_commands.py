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
@file test_web_commands.py
@brief Durable web operation execution tests.
@details Command runner is injected so no real forge, git, or container runs.
"""

from threading import Event, Thread
import time

from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from adore.web.commands import CommandWorker
from adore.web.store import WebStore
from fastapi.testclient import TestClient


def test_authorized_start_uses_explicit_ticket_and_deduplicates(tmp_path):
    """@brief One authorized command executes once with a fixed CLI argv."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    first = web.enqueue(user["id"], "alpha", "start", "42", "one-request")
    again = web.enqueue(user["id"], "alpha", "start", "42", "one-request")
    calls = []
    worker = CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0)
    assert first["id"] == again["id"]
    assert worker.run_pending() == 1
    assert worker.run_pending() == 0
    assert calls[0][-4:] == ["run", "--once", "--ticket", "42"]
    assert web.operation(first["id"])["status"] == "succeeded"


def test_worker_heartbeats_while_idle_and_clears_on_graceful_stop(tmp_path):
    """@brief Readiness follows the single worker lifecycle."""
    profiles = ProfileStore(tmp_path / "home")
    web = WebStore(profiles.home / "web.db")
    stop = Event()
    worker = CommandWorker(profiles, web, runner=lambda _argv, _env: 0)
    thread = Thread(target=lambda: worker.run_forever(
        interval=0.02, heartbeat_interval=0.02, stop=stop))
    thread.start()
    try:
        for _ in range(100):
            if web.worker_ready():
                break
            time.sleep(0.02)
        assert web.worker_ready()
    finally:
        stop.set()
        thread.join(timeout=3)
    assert not thread.is_alive()
    assert not web.worker_ready()


def test_worker_heartbeats_during_blocking_engine_command(tmp_path):
    """@brief A long project operation does not make a live worker look stale."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    web = WebStore(profiles.home / "web.db")
    admin = web.authenticate("admin", "admin")
    web.enqueue(admin["id"], "alpha", "start", "42", "one-request")
    entered = Event()
    release = Event()
    stop = Event()

    def runner(_argv, _env):
        """@brief Hold the fake engine command until readiness is inspected."""
        entered.set()
        assert release.wait(timeout=3)
        return 0

    worker = CommandWorker(profiles, web, runner=runner)
    thread = Thread(target=lambda: worker.run_forever(
        interval=0.02, heartbeat_interval=0.02, stop=stop))
    thread.start()
    try:
        assert entered.wait(timeout=3)
        time.sleep(0.25)
        assert web.worker_ready(max_age_seconds=0.1)
    finally:
        stop.set()
        release.set()
        thread.join(timeout=3)
    assert not thread.is_alive()
    assert not web.worker_ready()


def test_revoked_membership_fails_closed_before_execution(tmp_path):
    """@brief Queued work cannot execute after project access is revoked."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    queued = web.enqueue(user["id"], "alpha", "start", "42", "one-request")
    web.set_memberships(user["id"], [])
    calls = []
    worker = CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0)
    assert worker.run_pending() == 1
    assert calls == []
    assert web.operation(queued["id"])["status"] == "failed"


def test_replaced_profile_rejects_queued_developer_command(tmp_path):
    """@brief Reused project labels cannot execute old developer commands."""
    profiles = ProfileStore(tmp_path / "home")
    first = profiles.create("alpha")
    first.created_at = "2026-01-01T00:00:00+00:00"
    profiles.save(first)
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    queued = web.enqueue(user["id"], "alpha", "start", "42", "one-request")
    replacement = profiles.create("alpha", overwrite=True)
    replacement.created_at = "2026-02-01T00:00:00+00:00"
    profiles.save(replacement)
    calls = []
    worker = CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0)
    assert worker.run_pending() == 1
    assert calls == []
    assert web.operation(queued["id"])["status"] == "failed"


def test_queued_command_follows_project_id_across_rename(tmp_path):
    """@brief A pending command targets the original project after relabel."""
    profiles = ProfileStore(tmp_path / "home")
    original = profiles.create("alpha")
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    queued = web.enqueue(user["id"], "alpha", "start", "42", "rename-test")
    profiles.rename("alpha", "renamed")
    profiles.create("alpha")
    calls = []
    worker = CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0)
    assert worker.run_pending() == 1
    assert calls and calls[0][calls[0].index("--profile") + 1] == "renamed"
    operation = web.operation(queued["id"])
    assert operation["project_id"] == original.project_id
    assert operation["project"] == "renamed"


def test_admin_command_does_not_follow_recycled_name(tmp_path):
    """@brief Administrator authority cannot retarget a queued old identity."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    web = WebStore(profiles.home / "web.db")
    admin = web.authenticate("admin", "admin")
    queued = web.enqueue(admin["id"], "alpha", "start", "42", "replace-test")
    profiles.create("alpha", overwrite=True)
    calls = []
    worker = CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0)
    assert worker.run_pending() == 1
    assert calls == []
    assert web.operation(queued["id"])["status"] == "failed"


def test_pause_is_admin_only_in_api_and_worker(tmp_path):
    """@brief Project pickup control stays with the platform administrator."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    app = create_app(profiles.home)
    web = app.state.web_store
    developer = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(developer["id"], ["alpha"])
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/session", json={"username": "dev", "password": "longer-password"}
        )
        response = client.post(
            "/api/v1/projects/alpha/operations/pause",
            json={"idempotency_key": "developer-pause"},
            headers={"X-CSRF-Token": login.json()["csrf"]},
        )
        assert response.status_code == 403
        client.delete(
            "/api/v1/session", headers={"X-CSRF-Token": login.json()["csrf"]}
        )
        login = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        )
        response = client.post(
            "/api/v1/projects/alpha/operations/pause",
            json={"idempotency_key": "admin-pause"},
            headers={"X-CSRF-Token": login.json()["csrf"]},
        )
        assert response.status_code == 200
    calls = []
    worker = CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0)
    assert worker.run_pending() == 1
    assert calls[0][-1] == "pause"


def test_cancel_rechecks_lifecycle_before_worker_execution(tmp_path):
    """@brief A delayed cancel cannot rewrite a run that already completed."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha")
    state = StateStore(profile.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="working"))
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    queued = web.enqueue(user["id"], "alpha", "cancel", "run-1", "cancel-one")
    calls = []
    worker = CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0)
    assert worker.run_pending() == 1
    assert calls[0][-2:] == ["cancel", "run-1"]

    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="done"))
    delayed = web.enqueue(user["id"], "alpha", "cancel", "run-1", "cancel-two")
    assert worker.run_pending() == 1
    assert len(calls) == 1
    assert web.operation(delayed["id"])["status"] == "failed"
    assert state.load("run-1").lifecycle == "done"
    assert web.operation(queued["id"])["status"] == "succeeded"


def test_cancel_submission_rejects_finished_run(tmp_path):
    """@brief A user cannot queue cancellation of terminal evidence."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha")
    state = StateStore(profile.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="done"))
    app = create_app(profiles.home)
    with TestClient(app) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        response = client.post("/api/v1/projects/alpha/operations/cancel", json={
            "run_id": "run-1", "idempotency_key": "cancel-finished",
        }, headers={"X-CSRF-Token": csrf})
        assert response.status_code == 409
        assert state.load("run-1").lifecycle == "done"


def test_cancel_submission_waits_for_worker_authorization(tmp_path):
    """@brief API enqueue alone cannot preempt a gate before grant recheck."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha")
    state = StateStore(profile.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="working"))
    app = create_app(profiles.home)
    with TestClient(app) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        response = client.post("/api/v1/projects/alpha/operations/cancel", json={
            "run_id": "run-1", "idempotency_key": "cancel-active",
        }, headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200
        assert not state.cancel_requested("run-1")


def test_worker_reconciles_cancel_completed_by_active_conductor(tmp_path):
    """@brief A preempted gate is a successful queued cancel, not a retry."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha")
    state = StateStore(profile.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="working"))
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    queued = web.enqueue(user["id"], "alpha", "cancel", "run-1", "cancel-active")
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="cancelled"))
    calls = []
    worker = CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0)
    assert worker.run_pending() == 1
    assert calls == []
    assert web.operation(queued["id"])["status"] == "succeeded"


def test_active_poll_signals_authorized_cancel_after_worker_recheck(tmp_path):
    """@brief A busy worker signals a valid developer cancel promptly."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha")
    state = StateStore(profile.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="working"))
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    web.enqueue(user["id"], "alpha", "cancel", "run-1", "cancel-active")

    def poll(argv, env):
        assert argv[-2:] == ["run", "--once"]
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not state.cancel_requested("run-1"):
            time.sleep(0.01)
        assert state.cancel_requested("run-1")
        return 0

    assert CommandWorker(profiles, web, runner=poll).poll_project("alpha") == 0


def test_active_poll_does_not_signal_revoked_developer_cancel(tmp_path):
    """@brief A grant revoked before worker observation stops the signal."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha")
    state = StateStore(profile.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="working"))
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    queued = web.enqueue(user["id"], "alpha", "cancel", "run-1", "cancel-active")
    web.set_memberships(user["id"], [])

    def poll(argv, env):
        time.sleep(0.45)
        assert not state.cancel_requested("run-1")
        return 0

    worker = CommandWorker(profiles, web, runner=poll)
    assert worker.poll_project("alpha") == 0
    assert worker.run_pending() == 1
    assert web.operation(queued["id"])["status"] == "failed"


def test_cancel_is_claimed_before_older_non_cancel_work(tmp_path):
    """@brief Finishing a poll reconciles its cancellation before new starts."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    web.enqueue(user["id"], "alpha", "start", "42", "start-older")
    cancel = web.enqueue(user["id"], "alpha", "cancel", "run-1", "cancel-newer")
    assert web.claim_next()["id"] == cancel["id"]


def test_web_started_job_watches_for_queued_cancel(tmp_path):
    """@brief A long Start command can receive a later authorized cancel."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha")
    state = StateStore(profile.store_root or profiles.default_store_root("alpha"))
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    started = web.enqueue(user["id"], "alpha", "start", "42", "start-first")

    def start(argv, env):
        assert argv[-4:] == ["run", "--once", "--ticket", "42"]
        state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="working"))
        web.enqueue(user["id"], "alpha", "cancel", "run-1", "cancel-later")
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not state.cancel_requested("run-1"):
            time.sleep(0.01)
        assert state.cancel_requested("run-1")
        return 0

    worker = CommandWorker(profiles, web, runner=start)
    assert worker.run_pending() == 1
    assert state.cancel_requested("run-1")
    assert web.operation(started["id"])["status"] == "succeeded"


def test_busy_other_project_signals_authorized_cancel(tmp_path):
    """@brief A busy control worker signals a valid cancel in another project."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = profiles.create("alpha")
    profiles.create("beta")
    state = StateStore(alpha.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="working"))
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])

    def poll(argv, env):
        assert argv[-4:] == ["--profile", "beta", "run", "--once"]
        web.enqueue(user["id"], "alpha", "cancel", "run-1", "cancel-cross-project")
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not state.cancel_requested("run-1"):
            time.sleep(0.01)
        assert state.cancel_requested("run-1")
        return 0

    worker = CommandWorker(profiles, web, runner=poll)
    assert worker.poll_project("beta") == 0


def test_busy_other_project_does_not_signal_revoked_cancel(tmp_path):
    """@brief Cross-project signaling still requires a current project grant."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = profiles.create("alpha")
    profiles.create("beta")
    state = StateStore(alpha.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="working"))
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    queued = web.enqueue(user["id"], "alpha", "cancel", "run-1", "cancel-revoked")
    web.set_memberships(user["id"], [])

    def poll(argv, env):
        time.sleep(0.45)
        assert not state.cancel_requested("run-1")
        return 0

    worker = CommandWorker(profiles, web, runner=poll)
    assert worker.poll_project("beta") == 0
    assert worker.run_pending() == 1
    assert web.operation(queued["id"])["status"] == "failed"


def test_blocking_retry_watches_other_project_cancel(tmp_path):
    """@brief The cancel watcher also covers non-Start CLI commands."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = profiles.create("alpha")
    profiles.create("beta")
    state = StateStore(alpha.store_root or profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=42, lifecycle="working"))
    web = WebStore(profiles.home / "web.db")
    admin = web.authenticate("admin", "admin")
    web.enqueue(admin["id"], "beta", "retry", "old-run", "retry-beta")

    def retry(argv, env):
        assert argv[-4:] == ["--profile", "beta", "retry", "old-run"]
        web.enqueue(admin["id"], "alpha", "cancel", "run-1", "cancel-alpha")
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not state.cancel_requested("run-1"):
            time.sleep(0.01)
        assert state.cancel_requested("run-1")
        return 0

    assert CommandWorker(profiles, web, runner=retry).run_pending() == 1
