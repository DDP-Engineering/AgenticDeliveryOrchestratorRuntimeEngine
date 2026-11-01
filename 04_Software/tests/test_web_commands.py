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

from datetime import datetime
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from threading import Event, Thread
import time

from adore.config import PollingConfig, load_config, validate_config
from adore.polling import PollCadence
from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.util import in_quiet_hours
from adore.web.app import create_app
from adore.web.commands import CommandOutcome, CommandWorker, _run
from adore.web.store import WebStore, WebStoreError
from fastapi.testclient import TestClient
import pytest


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


def test_queued_cancel_cannot_reclaim_human_handoff(tmp_path):
    """@brief A stale queued cancel never invokes the engine after ownership transfer."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    state = StateStore(profiles.default_store_root("alpha"))
    state.save(RunState("run-1", 1, lifecycle="handed-off"))
    web = WebStore(profiles.home / "web.db")
    admin = web.authenticate("admin", "admin")
    queued = web.enqueue(admin["id"], "alpha", "cancel", "run-1", "stale")
    calls = []
    worker = CommandWorker(profiles, web,
                           runner=lambda argv, env: calls.append(argv) or 0)
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


@pytest.mark.parametrize("backoff, outcomes, expected", [
    (True, [0, 1, 1, 1, 1, 0, 0], [12, 22, 42, 82, 82, 12]),
    (False, [1, 1, 0], [12, 12]),
    (True, [124, None, True, "0", RuntimeError("transport"), 0], [22, 42, 82, 82, 82]),
])
def test_automatic_polling_uses_loop_wait_after_completion(
    tmp_path, monkeypatch, backoff, outcomes, expected,
):
    """@brief Observe configured waits and failures across actual worker rounds."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    source = example.read_text(encoding="utf-8")
    source = source.replace('mode = "loop"', 'mode = "once"')
    source = source.replace("poll_interval_seconds = 60", "poll_interval_seconds = 10")
    source = source.replace("poll_jitter_seconds = 5", "poll_jitter_seconds = 2")
    source = source.replace("poll_backoff = true", f"poll_backoff = {str(backoff).lower()}")
    profiles.config_path("alpha").write_text(source, encoding="utf-8")
    load_config(profiles.config_path("alpha"))
    web = WebStore(profiles.home / "web.db")
    clock = [0.0]
    starts = []
    stop = Event()
    # Both implementations draw from Python's shared random module.
    monkeypatch.setattr("random.uniform", lambda low, high: high)
    monkeypatch.setattr("adore.web.commands.time.monotonic", lambda: clock[0])

    def advance(seconds):
        """@brief Advance logical time while keeping heartbeat threading real."""
        clock[0] += seconds
        assert clock[0] < 2000, "worker failed to finish bounded fake rounds"
        return stop.is_set()

    monkeypatch.setattr(stop, "wait", advance)

    def runner(argv, _env):
        """@brief Simulate a seven-second pass and return external outcomes."""
        assert argv[-2:] == ["run", "--once"]
        starts.append(clock[0])
        outcome = outcomes[len(starts) - 1]
        clock[0] += 7
        if len(starts) == len(outcomes):
            stop.set()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    CommandWorker(profiles, web, runner=runner).run_forever(interval=1, stop=stop)
    waits = [later - earlier - 7 for earlier, later in zip(starts, starts[1:], strict=False)]
    assert waits == expected
    assert not web.worker_ready()


@pytest.mark.parametrize("source", [
    "[polling]\npoll_interval_seconds = -1\n",
    "[polling]\npoll_interval_seconds = true\n",
    "[polling]\npoll_backoff = \"yes\"\n",
    "[polling]\npoll_jitter_seconds = -1\n",
    "[polling]\npoll_interval_seconds = \"bad\"\n",
    "[polling",
])
def test_bad_polling_config_skips_invocation_and_rechecks(tmp_path, monkeypatch, source):
    """@brief Corrupt/invalid typed configuration never enters the engine."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    valid = example.read_text(encoding="utf-8")
    path.write_text(valid, encoding="utf-8")
    assert validate_config(load_config(path)) == []
    if source != "[polling":
        assignment = source.splitlines()[1]
        key = assignment.split("=", 1)[0].strip()
        source = re.sub(rf"^{key} = .*?$", assignment, valid, flags=re.MULTILINE)
    path.write_text(source, encoding="utf-8")
    web = WebStore(profiles.home / "web.db")
    clock = [0.0]
    calls = []
    stop = Event()
    monkeypatch.setattr("adore.web.commands.time.monotonic", lambda: clock[0])

    def advance(seconds):
        """@brief Bound the simulation past two invalid configuration checks."""
        clock[0] += seconds
        if clock[0] >= 61:
            stop.set()
        return stop.is_set()

    monkeypatch.setattr(stop, "wait", advance)
    CommandWorker(profiles, web, runner=lambda argv, env: calls.append(argv) or 0).run_forever(
        interval=1, stop=stop,
    )
    assert calls == []


@pytest.mark.parametrize("quiet", [False, True])
@pytest.mark.parametrize("tick", [0.1, 2])
def test_project_polling_is_independent_and_quiet_hours_keep_queue_available(
    tmp_path, monkeypatch, quiet, tick,
):
    """@brief One failing/quiet project cannot suppress healthy rounds or queued pause."""
    profiles = ProfileStore(tmp_path / "home")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    source = example.read_text(encoding="utf-8").replace(
        "poll_interval_seconds = 60", "poll_interval_seconds = 1",
    ).replace("poll_jitter_seconds = 5", "poll_jitter_seconds = 0")
    for name in ("alpha", "beta"):
        profiles.create(name)
        text = (source.replace('quiet_hours = []', 'quiet_hours = ["22:00-06:00"]')
                if name == "alpha" else source)
        profiles.config_path(name).write_text(text, encoding="utf-8")
    web = WebStore(profiles.home / "web.db")
    admin = web.authenticate("admin", "admin")
    queued = web.enqueue(admin["id"], "alpha", "pause", "", "pause-while-quiet")
    clock = [0.0]
    stop = Event()
    calls = []
    monkeypatch.setattr("adore.web.commands.time.monotonic", lambda: clock[0])
    monkeypatch.setattr(
        "adore.web.commands.in_quiet_hours", lambda windows: quiet and bool(windows),
    )

    def advance(seconds):
        """@brief Run a bounded ten-second logical scheduling window."""
        clock[0] += seconds
        if clock[0] >= 10:
            stop.set()
        return stop.is_set()

    monkeypatch.setattr(stop, "wait", advance)

    def runner(argv, _env):
        """@brief Fail alpha automatic rounds while beta and explicit pause succeed."""
        calls.append((argv[4], argv[-1], clock[0]))
        return 1 if argv[4] == "alpha" and argv[-1] == "--once" else 0

    CommandWorker(profiles, web, runner=runner).run_forever(interval=tick, stop=stop)
    alpha = [when for name, action, when in calls if name == "alpha" and action == "--once"]
    beta = [when for name, action, when in calls if name == "beta" and action == "--once"]
    assert len(beta) >= 8  # interval1 remains below the old forced5-second minimum.
    if quiet:
        assert alpha == []
    else:
        assert len(alpha) == 3
        assert alpha[1] - alpha[0] == pytest.approx(2, abs=0.11)
        assert alpha[2] - alpha[1] == pytest.approx(4, abs=0.11)
    assert web.operation(queued["id"])["status"] == "succeeded"
    assert not web.worker_ready()


@pytest.mark.parametrize("sample", [0, 3])
def test_shared_cadence_retains_errors_through_quiet_rounds_and_resets(sample, monkeypatch):
    """@brief Observe positive jitter endpoints and unchanged quiet-round error wait."""
    monkeypatch.setattr("random.uniform", lambda low, high: sample)
    config = PollingConfig(poll_interval_seconds=10, poll_jitter_seconds=3)
    cadence = PollCadence()
    assert cadence.next_delay(config, failed=True) == 20 + sample
    assert cadence.next_delay(config, failed=None) == 20 + sample
    assert cadence.next_delay(config, failed=False) == 10 + sample
    assert cadence.next_delay(config, failed=True) == 20 + sample
    config.poll_backoff = False
    assert cadence.next_delay(config, failed=None) == 10 + sample
    for hour, expected in [(21, False), (22, True), (0, True), (5, True), (6, False)]:
        assert in_quiet_hours(["22:00-06:00"], datetime(2026, 10, 8, hour)) is expected


def test_worker_resumes_automatic_polling_after_quiet_window(tmp_path, monkeypatch):
    """@brief The worker resumes scheduled rounds after host-local quiet hours end."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    source = example.read_text(encoding="utf-8").replace(
        "poll_interval_seconds = 60", "poll_interval_seconds = 1",
    ).replace("poll_jitter_seconds = 5", "poll_jitter_seconds = 0")
    profiles.config_path("alpha").write_text(source, encoding="utf-8")
    web = WebStore(profiles.home / "web.db")
    clock = [0.0]
    stop = Event()
    starts = []
    monkeypatch.setattr("adore.web.commands.time.monotonic", lambda: clock[0])
    monkeypatch.setattr("adore.web.commands.in_quiet_hours", lambda windows: clock[0] < 3)

    def advance(seconds):
        """@brief Advance across a bounded quiet-to-active transition."""
        clock[0] += seconds
        assert clock[0] < 10
        return stop.is_set()

    monkeypatch.setattr(stop, "wait", advance)

    def runner(_argv, _env):
        """@brief Stop after the first post-window automatic pass."""
        starts.append(clock[0])
        stop.set()
        return 0

    CommandWorker(profiles, web, runner=runner).run_forever(interval=1, stop=stop)
    assert starts == [3]


def _queued_start(tmp_path, ticket="42"):
    """@brief One member's start operation for project alpha."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(user["id"], ["alpha"])
    return profiles, web, web.enqueue(user["id"], "alpha", "start", ticket, "start-key")


@pytest.mark.parametrize("case", ["ansi-token", "long", "timeout", "success", "bare-int"])
def test_failed_engine_operation_keeps_bounded_redacted_detail(tmp_path, case):
    """@brief A failed engine command leaves its last output lines, redacted, on the operation."""
    outcome = {
        "ansi-token": CommandOutcome(1, "starting\n\x1b[31mERROR\x1b[0m token=abc123secret\n"
                                        "last line\n"),
        "long": CommandOutcome(1, "\n".join(f"line {index}" for index in range(500))),
        "timeout": CommandOutcome(124, "partial output\n"),
        "success": CommandOutcome(0, "all fine\n"),
        "bare-int": 1,
    }[case]
    profiles, web, queued = _queued_start(tmp_path)

    assert CommandWorker(profiles, web, runner=lambda _argv, _env: outcome).run_pending() == 1

    saved = web.operation(queued["id"])
    detail = saved["detail"]
    assert saved["reason"] == ""
    if case == "ansi-token":
        assert saved["status"] == "failed" and detail.endswith("last line")
        assert "\x1b" not in detail and "abc123secret" not in detail
        assert "token=[REDACTED]" in detail
    elif case == "long":
        assert detail.splitlines() == [f"line {index}" for index in range(480, 500)]
    elif case == "timeout":
        assert saved["status"] == "uncertain" and detail == "partial output"
    elif case == "success":
        assert saved["status"] == "succeeded" and detail == ""
    else:
        assert saved["status"] == "failed" and detail == ""


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        *[(f"error: ticket #42 not started: {code}", code) for code in (
            "pickup_paused", "at_capacity", "aegis_probe_failed", "not_eligible",
            "conductor_busy")],
        ("error: ticket #43 not started: at_capacity", ""),
        ("error: ticket #42 not started: something_else", ""),
        ("error: unexpected fault", ""),
    ],
)
def test_refused_start_records_the_engine_reason(tmp_path, line, reason):
    """@brief A refused start keeps the CLI's stable code for its own ticket only."""
    profiles, web, queued = _queued_start(tmp_path)
    output = '{"picked": null}\n' + line + "\n"

    CommandWorker(profiles, web, runner=lambda _argv, _env: CommandOutcome(1, output)).run_pending()

    saved = web.operation(queued["id"])
    assert saved["status"] == "failed"
    assert saved["reason"] == reason
    assert saved["detail"].endswith(line)


def test_engine_runner_keeps_stdout_and_stderr_in_one_output():
    """@brief The real runner returns the exit code and both streams for the detail."""
    script = ("import sys; print('to stdout', flush=True); "
              "print('to stderr', file=sys.stderr); sys.exit(3)")

    outcome = _run([sys.executable, "-c", script], dict(os.environ))

    assert outcome.code == 3
    assert "to stdout" in outcome.output and "to stderr" in outcome.output


def test_worker_environment_keeps_engine_output_ordered_and_utf8(tmp_path):
    """@brief The CLI child writes unbuffered UTF-8, so the detail keeps print order and text."""
    profiles = ProfileStore(tmp_path / "home")
    worker = CommandWorker(profiles, WebStore(profiles.home / "web.db"))
    script = ("import sys; print('stdout first'); print('Ștefan ș'); "
              "print('stderr last', file=sys.stderr); sys.exit(3)")

    outcome = _run([sys.executable, "-c", script], worker.environment)

    assert outcome.code == 3
    assert outcome.output.splitlines() == ["stdout first", "Ștefan ș", "stderr last"]


@pytest.mark.parametrize("partial", [b"partial line\n", "partial line\n", None])
def test_engine_runner_timeout_keeps_partial_output(monkeypatch, partial):
    """@brief A timed-out engine command keeps what it printed, as bytes or text."""
    def expire(argv, **_kwargs):
        raise subprocess.TimeoutExpired(argv, 21600, output=partial)

    monkeypatch.setattr("adore.web.commands.subprocess.run", expire)

    assert _run(["adore"], {}) == CommandOutcome(124, "partial line\n" if partial else "")


def test_project_poll_returns_the_exit_code_of_a_full_outcome(tmp_path):
    """@brief Automatic polling still reads only the exit code of a runner outcome."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    worker = CommandWorker(profiles, WebStore(profiles.home / "web.db"),
                           runner=lambda _argv, _env: CommandOutcome(7, "polled"))

    assert worker.poll_project("alpha") == 7


def test_operation_api_returns_reason_and_detail(tmp_path):
    """@brief GET /api/v1/operations/{id} exposes the stored reason and detail."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    app = create_app(profiles.home)
    web = app.state.web_store
    admin = web.authenticate("admin", "admin")
    queued = web.enqueue(admin["id"], "alpha", "start", "42", "api-key")
    output = "error: ticket #42 not started: pickup_paused\n"
    CommandWorker(profiles, web, runner=lambda _argv, _env: CommandOutcome(1, output)).run_pending()

    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        body = client.get(f"/api/v1/operations/{queued['id']}").json()
    assert body["status"] == "failed"
    assert body["reason"] == "pickup_paused"
    assert body["detail"] == "error: ticket #42 not started: pickup_paused"


@pytest.mark.parametrize("version", [14, 16])
def test_web_database_of_another_schema_is_refused_untouched(tmp_path, version):
    """@brief No migration: another schema version stops startup and names what to delete."""
    profiles, web, _queued = _queued_start(tmp_path)
    with sqlite3.connect(web.path) as connection:
        connection.execute(f"PRAGMA user_version={version}")
    before = web.path.read_bytes()

    with pytest.raises(WebStoreError) as refused:
        WebStore(web.path)

    message = str(refused.value)
    assert f"schema {version}" in message and "not supported" in message
    assert str(web.path) in message and "web.db.initialized" in message
    assert web.path.read_bytes() == before
