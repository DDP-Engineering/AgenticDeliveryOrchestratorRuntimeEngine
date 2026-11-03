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
@file test_web_pricing.py
@brief Administrator-owned dated estimated price contracts.
@details Verifies migration, role boundaries, immutable dates and separate
         reported/estimated usage valuation with offline journals.
"""

import sqlite3

from adore import metrics
from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from adore.web.store import WebStore
from fastapi.testclient import TestClient

from tests.usage_events import versioned_usage


def test_prices_follow_project_identity_across_rename_and_name_reuse(tmp_path):
    """@brief A rate follows its profile ID and never attaches to a replacement."""
    profiles = ProfileStore(tmp_path)
    profiles.create("alpha")
    web = WebStore(tmp_path / "web.db")
    web.add_price("alpha", "codex", "local-1", "2026-01-01", "2", "4", 1)
    profiles.rename("alpha", "renamed")
    assert web.list_prices("renamed")[0]["input_usd_per_million"] == "2"
    profiles.create("alpha")
    assert web.list_prices("alpha") == []
    web.add_price("alpha", "codex", "local-1", "2026-01-01", "5", "9", 1)
    assert web.list_prices("alpha")[0]["input_usd_per_million"] == "5"
    assert web.list_prices("renamed")[0]["input_usd_per_million"] == "2"


def test_admin_prices_are_immutable_and_developer_cannot_read(tmp_path):
    """@brief Only admins create/read dated rates; bad rates fail closed."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    rate = {"executor": "codex", "model": "local-1",
            "effective_from": "2026-01-01", "input_usd_per_million": "2.00",
            "output_usd_per_million": "4.00"}
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        csrf = login.json()["csrf"]
        assert client.get("/api/v1/projects/alpha/prices").status_code == 403
        assert client.post("/api/v1/projects/alpha/prices", json=rate,
                           headers={"X-CSRF-Token": csrf}).status_code == 403
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        csrf = login.json()["csrf"]
        target = "/api/v1/projects/alpha/prices"
        assert client.post(target, json=rate).status_code == 403
        created = client.post(target, json=rate, headers={"X-CSRF-Token": csrf})
        assert created.status_code == 201, created.text
        assert client.get(target).json()[0]["input_usd_per_million"] == "2.00"
        assert client.post(target, json=rate,
                           headers={"X-CSRF-Token": csrf}).status_code == 409
        for bad in ({**rate, "input_usd_per_million": "-1"},
                    {**rate, "output_usd_per_million": "NaN"},
                    {**rate, "effective_from": "2026-99-99"}):
            assert client.post(target, json=bad,
                               headers={"X-CSRF-Token": csrf}).status_code == 400
        assert client.get("/api/v1/projects/missing/prices").status_code == 404


def test_estimates_use_effective_rate_without_double_counting_reported_cost(tmp_path):
    """@brief Dated token-only estimates and reported money stay separate."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    run = RunState(run_id="run-1", ticket_iid=7, lifecycle="done")
    state.save(run)
    state.journal("run-1", "picked", ts="2026-01-01T00:00:00+00:00")
    for attempt, (stamp, model, reported) in enumerate((
            ("2026-01-20T00:00:00+00:00", "local-1", False),
            ("2026-02-20T00:00:00+00:00", "local-1", False),
            ("2026-02-21T00:00:00+00:00", "local-1", True),
            ("2026-02-22T00:00:00+00:00", "unknown", False)), start=1):
        state.journal("run-1", "usage", **versioned_usage("run-1", attempt,
                                                          ts=stamp, executor="codex", model=model,
                      tokens_in=1_000_000, tokens_out=1_000_000,
                      cost_usd=0.3 if reported else 0.0,
                      cost_reported=reported))
    metrics.record_summary(state.root / "metrics.db", metrics.summarize_run(state, "run-1"))
    app = create_app(profiles.home)
    web = app.state.web_store
    web.add_price("alpha", "codex", "local-1", "2026-01-01", "2", "4", 1)
    web.add_price("alpha", "codex", "local-1", "2026-02-01", "3", "6", 1)
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        body = client.get("/api/v1/projects/alpha/metrics").json()
        assert body["totals"]["cost_usd"] == 0.3
        assert body["totals"]["estimated_cost_usd"] == 15.0
        assert body["coverage"]["usage_events_unpriced"] == 1
        days = {row["date"]: row for row in body["daily"]}
        assert days["2026-01-20"]["estimated_cost_usd"] == 6.0
        assert days["2026-02-20"]["estimated_cost_usd"] == 9.0
        assert days["2026-02-21"]["estimated_cost_usd"] is None
        exported = client.get("/api/v1/projects/alpha/metrics.csv").text
        assert "estimated_cost_usd" in exported
        assert "2026-02-20,0,0,0,1000000,1000000,0,0,,9" in exported
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        body = client.get("/api/v1/projects/alpha/metrics").json()
        assert "cost" not in str(body).lower()
        assert "price" not in str(body).lower()


def test_corrupt_stored_price_fails_closed(tmp_path):
    """@brief A damaged rate is an explicit error, never a made-up estimate."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    app = create_app(profiles.home)
    web = app.state.web_store
    web.add_price("alpha", "codex", "local-1", "2026-01-01", "2", "4", 1)
    with sqlite3.connect(web.path) as connection:
        connection.execute("UPDATE prices SET input_usd_per_million='NaN'")
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        assert client.get("/api/v1/projects/alpha/prices").status_code == 503
        assert client.get("/api/v1/projects/alpha/metrics").status_code == 503
    with sqlite3.connect(web.path) as connection:
        connection.execute(
            "UPDATE prices SET input_usd_per_million='2', model=''"
        )
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        assert client.get("/api/v1/projects/alpha/metrics").status_code == 503
    with sqlite3.connect(web.path) as connection:
        connection.execute(
            "UPDATE prices SET model='local-1', effective_from='2026-99-99'"
        )
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        assert client.get("/api/v1/projects/alpha/prices").status_code == 503


def test_nonfinite_journal_cost_is_not_exposed(tmp_path):
    """@brief A malformed usage event cannot become a monetary total."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="working"))
    state.journal("run-1", "usage", **versioned_usage("run-1", 31, tokens_in=4, tokens_out=2,
                  cost_usd="NaN", cost_reported=True))
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/metrics")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "metrics_corrupt"
