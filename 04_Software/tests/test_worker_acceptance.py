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
@file    test_worker_acceptance.py
@brief   Integrated worker contracts at real controlled executor barriers.
@details Reuses focused supervisor/configuration fixtures; only forge, Git and
         executor boundaries are simulated. No target repository checks run.
"""

# IMPORTS
from adore.config import load_config
from adore.profiles import ProfileStore
from adore.state import StateError, StateStore
from adore.web.app import create_app
from adore.web.commands import CommandWorker
from adore.web.configuration import ConfigurationWorker
from adore.web.ownership import process_birth
from adore.web.processes import stop_trees
from fastapi.testclient import TestClient
import pytest

from tests.supervisor_helper import OfflineAegis, offline_engine
from tests.test_web_configuration_worker import _settle
from tests.test_web_pending_config import _headers
from tests.test_web_supervisor import eventually, project, reserve, start_project


# PUBLIC API / TESTS
@pytest.mark.parametrize("workflow", ["direct", "aegis"])
def test_blocked_executor_keeps_scoped_settings_and_peer_execution_independent(
    tmp_path, monkeypatch, workflow,
):
    """@brief Real A/B executors overlap while B/global apply and A stages safely."""
    import json

    profiles = ProfileStore(tmp_path / "home")
    alpha, beta = project(profiles, "alpha"), project(profiles, "beta")
    if workflow == "aegis":
        clone = load_config(profiles.config_path("alpha")).worktree.repo_path
        from pathlib import Path

        payload = Path(clone) / ".agentic/aegis.py"
        payload.parent.mkdir()
        payload.write_text("# offline governed fixture\n")
        monkeypatch.setattr("adore.orchestrator.AegisClient", OfflineAegis)
    app = create_app(profiles.home)
    web = app.state.web_store
    workers = [start_project(profiles, web, p) for p in (alpha, beta)]
    picked_a = reserve(profiles, "alpha", 7)
    marker_a = profiles.home / "barriers" / (alpha.project_id + "-" + picked_a["run_id"])
    before_a = profiles.config_path("alpha").read_bytes()
    control = ConfigurationWorker(app.state.configuration_tasks)
    try:
        assert workers[0].tick()
        eventually(marker_a.exists)
        birth_a = json.loads(marker_a.read_text())
        with TestClient(app) as client:
            headers = _headers(client)
            revision_b = client.get("/api/v1/projects/beta/config").json()["revision"]
            saved = client.put("/api/v1/projects/beta/config", headers=headers, json={
                "key": "budgets.max_iterations", "value": "17", "revision": revision_b,
            })
            assert saved.status_code == 202, saved.text
            accepted = saved.json()
            assert accepted["project_id"] == beta.project_id
            assert _settle(control, accepted)["status"] == "succeeded"
            outcome = client.get(f"/api/v1/operations/{accepted['id']}").json()["outcome"]
            assert outcome["status_code"] == 200
            assert outcome["body"]["revision"] != revision_b
            assert load_config(profiles.config_path("beta")).budgets.max_iterations == 17
            assert profiles.config_path("alpha").read_bytes() == before_a
            policy = client.put("/api/v1/audit-policy", headers=headers, json={
                "retention_days": 30, "max_bytes": None,
            })
            assert policy.status_code == 200, policy.text
            assert web.audit_policy() == {"retention_days": 30, "max_bytes": None}

            revision_a = client.get("/api/v1/projects/alpha/config").json()["revision"]
            staged = client.post("/api/v1/projects/alpha/config/pending", headers=headers, json={
                "key": "container.image", "value": "acceptance:1", "revision": revision_a,
            })
            assert staged.status_code == 202, staged.text
            assert _settle(control, staged.json())["status"] == "succeeded"
            candidate = control.tasks.outcome(web.operation(staged.json()["id"]))["body"]
            apply = client.post("/api/v1/projects/alpha/config/apply", headers=headers, json={
                "base_revision": revision_a, "candidate_revision": candidate["candidate_revision"],
            })
            assert apply.status_code == 202, apply.text
            refused = _settle(control, apply.json())
            assert refused["status"] == "failed" and refused["reason"] == "project_has_active_work"
            assert control.tasks.outcome(refused)["status_code"] == 409
            assert profiles.config_path("alpha").read_bytes() == before_a
            assert (profiles.profile_dir("alpha") / "pending_config.json").is_file()

        picked_b = reserve(profiles, "beta", 7)
        marker_b = profiles.home / "barriers" / (beta.project_id + "-" + picked_b["run_id"])
        assert workers[1].tick()
        eventually(marker_b.exists)
        birth_b = json.loads(marker_b.read_text())
        assert birth_a["pid"] != birth_b["pid"]
        assert all(process_birth(row["pid"]) == row["birth"] for row in (birth_a, birth_b))
        assert not marker_a.with_suffix(".ended").exists()
        # B finishes with its new settings while A remains inside the first executor.
        marker_b.with_suffix(".release").touch()
        child_b = workers[1].children["run:" + picked_b["run_id"]]
        eventually(lambda: child_b.poll() is not None)
        assert child_b.poll() == 0, child_b.tail()
        assert StateStore(beta.store_root).load(picked_b["run_id"]).lifecycle == "awaiting-approval"
        assert process_birth(birth_a["pid"]) == birth_a["birth"]
        assert not marker_a.with_suffix(".ended").exists()
        marker_a.with_suffix(".release").touch()
        child_a = workers[0].children["run:" + picked_a["run_id"]]
        eventually(lambda: child_a.poll() is not None)
        assert child_a.poll() == 0, child_a.tail()
        state = StateStore(alpha.store_root)
        run = state.load(picked_a["run_id"])
        assert run.lifecycle == "awaiting-approval" and run.workflow == workflow
        assert run.iterations == (3 if workflow == "aegis" else 1)
        if workflow == "aegis":
            assert run.validation_evidence["source"] == "agent-aegis-journal"
        else:
            assert run.validation_evidence["implementation"] == "completed"
        assert [row["event"] for row in state.read_journal(run.run_id)].count("picked") == 1
    finally:
        control.close()
        for worker in workers:
            stop_trees(list(worker.children.values()))


def test_cancel_at_full_real_pool_preserves_peer_and_deduplicates_request(tmp_path):
    """@brief Cancel needs no free executor and one request cannot stop its peer."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = project(profiles, "alpha", limit=2)
    app = create_app(profiles.home)
    web = app.state.web_store
    worker = start_project(profiles, web, alpha)
    runs = [reserve(profiles, "alpha", iid)["run_id"] for iid in (7, 8)]
    markers = [profiles.home / "barriers" / (alpha.project_id + "-" + run) for run in runs]
    state = StateStore(alpha.store_root)
    try:
        assert worker.tick()
        eventually(lambda: worker.tick() and all(marker.exists() for marker in markers))
        assert reserve(profiles, "alpha", 9)["at_capacity"]
        admin = web.authenticate("admin", "admin")
        request = web.enqueue(admin["id"], "alpha", "cancel", runs[0], "cancel-once")
        duplicate = web.enqueue(admin["id"], "alpha", "cancel", runs[0], "cancel-once")
        assert duplicate["id"] == request["id"]
        queued = web.enqueue(admin["id"], "alpha", "start", "9", "wait-for-slot")

        def cancel(argv, environment):
            """@brief Simulate only CLI transport; use the real cross-process cancel API."""
            peer, *_ = offline_engine(profiles, "alpha")
            assert peer.cancel(runs[0])
            eventually(lambda: state.load(runs[0]).lifecycle == "cancelled")
            return 0

        launches = []

        def command_transport(argv, environment):
            """@brief Keep the scheduler decision real, injecting only child/CLI transport."""
            from types import SimpleNamespace

            launches.append(argv)
            assert argv[argv.index("--role") + 1] == "command"
            assert argv[argv.index("--actions") + 1] == "cancel"
            control = CommandWorker(profiles, web, project_id=alpha.project_id,
                                    domains=("execution",), execution_owner=worker.owner,
                                    actions=("cancel",), runner=cancel)
            assert control.run_pending() == 1
            assert control.run_pending() == 0
            return SimpleNamespace(poll=lambda: 0, request_stop=lambda: None,
                                   kill=lambda: None, close=lambda: None,
                                   process=SimpleNamespace(wait=lambda **_: 0))

        worker.spawn = command_transport
        assert worker.tick()
        assert len(launches) == 1
        eventually(lambda: state.load(runs[0]).lifecycle == "cancelled")
        assert web.operation(queued["id"])["status"] == "pending"
        assert web.operation(request["id"])["status"] == "succeeded"
        assert state.load(runs[1]).lifecycle == "working"
        assert not markers[1].with_suffix(".ended").exists()
        assert worker.children["run:" + runs[1]].poll() is None
        assert state.read_journal(runs[0])[-1]["event"] == "cancelled"
        markers[1].with_suffix(".release").touch()
        peer = worker.children["run:" + runs[1]]
        eventually(lambda: peer.poll() is not None)
        assert peer.poll() == 0, peer.tail()
        assert state.load(runs[1]).lifecycle == "awaiting-approval"
        assert all(state.load(run).iterations == 1 for run in runs)
    finally:
        stop_trees(list(worker.children.values()))


def test_admission_refuses_storage_loss_between_capacity_scans(tmp_path, monkeypatch):
    """@brief A pending slot unavailable only on the second scan still fences N+1."""
    from dataclasses import replace
    from pathlib import Path

    profiles = ProfileStore(tmp_path / "home")
    profile = project(profiles, "alpha")
    reserved = reserve(profiles, "alpha", 7)
    engine, forge, *_ = offline_engine(profiles, "alpha")
    forge.ticket = replace(forge.ticket, iid=8)
    path = StateStore(profile.store_root).run_dir(reserved["run_id"]) / "state.json"
    before = path.read_bytes()
    original, reads = Path.read_text, []

    def denied_after_valid_scan(target, *args, **kwargs):
        if target == path:
            reads.append(target)
            if len(reads) > 1:
                error = PermissionError("sharing violation")
                error.winerror = 32
                raise error
        return original(target, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied_after_valid_scan)
    monkeypatch.setattr("adore.state.time.sleep", lambda _: None)
    with pytest.raises(StateError, match="storage unavailable"):
        engine.poll_once(ticket_iid=8, admit_only=True)
    assert len(reads) == 7
    assert not engine.store.exists(engine._run_id(8))
    assert path.read_bytes() == before


# END OF FILE
