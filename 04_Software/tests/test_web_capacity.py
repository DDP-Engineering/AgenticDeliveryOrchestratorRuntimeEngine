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
@file test_web_capacity.py
@brief Bounded first-release dashboard workload with local state only.
@details Exercises the agreed registration and viewer count without a forge.
"""

from concurrent.futures import ThreadPoolExecutor

from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from fastapi.testclient import TestClient


def test_ten_users_twenty_projects_five_viewers(tmp_path):
    """@brief Concurrent viewers see twenty projects and one active job."""
    profiles = ProfileStore(tmp_path / "home")
    for index in range(20):
        profiles.create(f"project-{index:02d}",
                        store_root=str(tmp_path / f"state-{index:02d}"))
    active = profiles.load("project-00")
    StateStore(active.store_root).save(RunState(
        run_id="active-1", ticket_iid=1, lifecycle="working"))
    app = create_app(profiles.home)
    for index in range(9):
        user = app.state.web_store.create_user(
            f"dev{index}", "longer-password", "developer")
        app.state.web_store.set_memberships(
            user["id"], [f"project-{number:02d}" for number in range(20)])

    def view(index: int) -> tuple[int, int, str]:
        """@brief Open one independent session and load list and job detail."""
        with TestClient(app) as client:
            login = client.post("/api/v1/session", json={
                "username": f"dev{index}", "password": "longer-password"})
            assert login.status_code == 200, login.text
            listing = client.get("/api/v1/projects")
            detail = client.get("/api/v1/projects/project-00")
            job = client.get("/api/v1/projects/project-00/runs/active-1")
            assert listing.status_code == 200, listing.text
            assert detail.status_code == 200, detail.text
            assert job.status_code == 200, job.text
            return len(listing.json()), detail.json()["runs"], job.json()["run"]["lifecycle"]

    with ThreadPoolExecutor(max_workers=5) as pool:
        assert list(pool.map(view, range(5))) == [(20, 1, "working")] * 5
