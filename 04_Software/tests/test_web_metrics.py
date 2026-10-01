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
@file test_web_metrics.py
@brief Daily web metrics and role-specific cost tests.
@details Uses local journal and summary evidence without any external service.
"""

import sqlite3

from adore import metrics
from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from adore.web.store import WebStoreError
from fastapi.testclient import TestClient
import pytest


def test_daily_usage_and_financial_privacy(tmp_path):
    """@brief Usage is bucketed by event day; developer gets no money fields."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    run = RunState(run_id="run-1", ticket_iid=42, lifecycle="done")
    state.save(run)
    state.journal(run.run_id, "picked")
    state.journal(run.run_id, "usage", tokens_in=12, tokens_out=3, cost_usd=0.1)
    metrics.record_summary(state.root / "metrics.db", metrics.summarize_run(state, run.run_id))
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])

    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "dev", "password": "longer-password"})
        response = client.get("/api/v1/projects/alpha/metrics")
        assert response.status_code == 200
        body = response.json()
        assert body["totals"]["tokens_in"] == 12
        assert body["daily"][0]["tokens_in"] == 12
        assert "cost" not in str(body).lower()
        assert client.get("/api/v1/metrics").status_code == 403

    with TestClient(app) as admin:
        admin.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        body = admin.get("/api/v1/projects/alpha/metrics").json()
        assert body["totals"]["cost_usd"] == 0.1
        assert body["daily"][0]["cost_usd"] == 0.1


def test_terminal_daily_count_ignores_later_checkpoint_activity(tmp_path):
    """@brief A recovery checkpoint cannot turn an old failure into today's completion."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    run = RunState(run_id="run-1", ticket_iid=42, lifecycle="failed",
                   updated_at="2026-09-28T15:26:39Z")
    state.save(run)
    state.journal(run.run_id, "picked", ts="2026-09-28T12:00:00Z")
    state.journal(run.run_id, "stage-failed", ts="2026-09-28T15:26:39Z")
    state.journal(run.run_id, "checkpoint-pushed", ts="2026-10-01T05:48:26Z",
                  commit="d" * 40)
    metrics.record_summary(state.root / "metrics.db", metrics.summarize_run(state, run.run_id))
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/metrics")
        assert response.status_code == 200, response.text
        assert [(row["date"], row["completed"]) for row in response.json()["daily"]] == [
            ("2026-09-28", 1)
        ]


def test_usage_projection_replay_and_missing_source_fail_closed(tmp_path):
    """@brief Web usage reads backfill once and reject lost source evidence."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="working"))
    state.journal("run-1", "usage", ts="2026-01-01T12:00:00Z",
                  executor="opencode", model="local/test", tokens_in=5,
                  tokens_out=1, cost_usd=0)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        for _ in range(2):
            response = client.get("/api/v1/projects/alpha/usage")
            assert response.status_code == 200, response.text
            assert response.json()["totals"]["tokens_in"] == 5
        with sqlite3.connect(app.state.web_store.path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM usage_projection WHERE project_id=?",
                (profile.project_id,),
            ).fetchone()[0] == 1
        state.journal("run-1", "usage", ts="2026-01-02T12:00:00Z",
                      executor="opencode", model="local/test", tokens_in=7,
                      tokens_out=2, cost_usd=0)
        response = client.get("/api/v1/projects/alpha/usage")
        assert response.status_code == 200, response.text
        assert response.json()["totals"]["tokens_in"] == 12
        with sqlite3.connect(app.state.web_store.path) as connection:
            assert connection.execute("SELECT COUNT(*) FROM usage_projection").fetchone()[0] == 2
    with sqlite3.connect(app.state.web_store.path) as connection:
        connection.execute("UPDATE usage_projection SET event_json='{}' "
                           "WHERE source_id='legacy:0'")
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/usage")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "usage_corrupt"
    try:
        app.state.web_store.reconcile_usage(profile.project_id, "run-1", [])
    except WebStoreError as exc:
        assert "absent" in str(exc)
    else:
        raise AssertionError("missing source did not fail closed")


def test_cache_usage_is_a_subset_of_input_and_bad_overlap_fails(tmp_path):
    """@brief Cache categories are visible without inflating input totals."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="working"))
    event = dict(event_id="run-1:1", attempt=1, context="build",
                 executor="pi", model="local/qwen", review_round=0,
                 tokens_in=190, tokens_out=25, cost_usd=0,
                 cost_reported=False, cache_read_tokens=50,
                 cache_write_tokens=10, input_includes_cache=True)
    state.journal("run-1", "usage", **event)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/usage")
        assert response.status_code == 200, response.text
        totals = response.json()["totals"]
        assert totals["tokens_in"] == 190
        assert (totals["cache_read_tokens"], totals["cache_write_tokens"]) == (50, 10)
        assert "cache_read_tokens" in client.get(
            "/api/v1/projects/alpha/usage.csv").text

    bad = dict(event)
    bad["event_id"] = "run-1:2"
    bad["attempt"] = 2
    bad["input_includes_cache"] = False
    state.journal("run-1", "usage", **bad)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        assert client.get("/api/v1/projects/alpha/usage").status_code == 503


def test_coverage_projection_cursor_replays_append_only_journal(tmp_path):
    """@brief Coverage and cursor persist, replay, and reject source mutation."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="working"))
    state.journal("run-1", "usage-observation", schema=1,
                  event_id="run-1:1", attempt=1, stage="build",
                  review_round=0, executor="pi", model="local/qwen",
                  token_status="reported", cost_status="unavailable",
                  tokens_in=0, tokens_out=0, cost_usd=None)
    web = create_app(profiles.home).state.web_store
    journal = state.read_journal("run-1")
    for _ in range(2):
        assert web.reconcile_usage(profile.project_id, "run-1", journal) == []
    with sqlite3.connect(web.path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM usage_observation_projection").fetchone()[0] == 1
        assert connection.execute(
            "SELECT journal_length FROM usage_cursor").fetchone()[0] == 1
    state.journal("run-1", "usage", event_id="run-1:1", attempt=1,
                  context="build", executor="pi", model="local/qwen",
                  review_round=0, tokens_in=5, tokens_out=1,
                  cost_usd=0, cost_reported=False)
    journal = state.read_journal("run-1")
    assert len(web.reconcile_usage(profile.project_id, "run-1", journal)) == 1
    with sqlite3.connect(web.path) as connection:
        assert connection.execute(
            "SELECT journal_length FROM usage_cursor").fetchone()[0] == 2
    changed = [dict(event) for event in journal]
    changed[0]["model"] = "local/other"
    with pytest.raises(WebStoreError, match="changed before cursor"):
        web.reconcile_usage(profile.project_id, "run-1", changed)
    for invalid_stamp in ("2026-09-30", "2026-09-30T12:00:00+02:00"):
        changed[0]["ts"] = invalid_stamp
        with pytest.raises(WebStoreError, match="journal is corrupt"):
            web.reconcile_usage(profile.project_id, "run-1", changed)


def test_admin_rebuilds_archived_usage_without_changing_run_state(tmp_path):
    """@brief Explicit replay is idempotent and limited to administrators."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    profile.archived = True
    profiles.save(profile)
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="done"))
    state.journal("run-1", "usage-observation", schema=1,
                  event_id="run-1:1", attempt=1, stage="build",
                  review_round=0, executor="opencode", model="local/test",
                  token_status="reported", cost_status="unavailable",
                  tokens_in=5, tokens_out=1, cost_usd=None)
    state.journal("run-1", "usage", ts="2026-01-01T12:00:00Z",
                  executor="opencode", model="local/test", tokens_in=5,
                  tokens_out=1, cost_usd=0)
    before = state.load("run-1").to_dict()
    app = create_app(profiles.home)
    dev = app.state.web_store.create_user("dev", "longer-password", "developer")
    app.state.web_store.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        dev_csrf = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"}).json()["csrf"]
        assert client.post("/api/v1/usage/rebuild",
                           headers={"X-CSRF-Token": dev_csrf}).status_code == 403
        client.delete("/api/v1/session", headers={"X-CSRF-Token": dev_csrf})
        admin_csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        assert client.post("/api/v1/usage/rebuild").status_code == 403
        for _ in range(2):
            response = client.post("/api/v1/usage/rebuild",
                                   headers={"X-CSRF-Token": admin_csrf})
            assert response.status_code == 200, response.text
            assert response.json() == {"projects": 1, "runs": 1, "usage_events": 1}
    with sqlite3.connect(app.state.web_store.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM usage_projection").fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM usage_observation_projection"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT journal_length FROM usage_cursor"
        ).fetchone()[0] == 2
    assert state.load("run-1").to_dict() == before


def test_reporting_timezone_and_weekly_monthly_buckets(tmp_path):
    """@brief UTC evidence crosses DST and week/month boundaries by local day."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="working"))
    state.journal("run-1", "usage", ts="2026-03-28T22:30:00Z",
                  tokens_in=3, tokens_out=1, cost_usd=0)
    state.journal("run-1", "usage", ts="2026-03-29T21:30:00Z",
                  tokens_in=7, tokens_out=2, cost_usd=0)
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        utc = client.get("/api/v1/projects/alpha/metrics")
        assert [row["date"] for row in utc.json()["daily"]] == [
            "2026-03-28", "2026-03-29"]
        query = "?timezone=Europe%2FBucharest&granularity=week"
        weekly = client.get("/api/v1/projects/alpha/metrics" + query)
        assert weekly.status_code == 200, weekly.text
        assert weekly.json()["timezone"] == "Europe/Bucharest"
        assert weekly.json()["granularity"] == "week"
        assert [(row["date"], row["tokens_in"]) for row in weekly.json()["daily"]] == [
            ("2026-03-23", 3), ("2026-03-30", 7)]
        monthly = client.get("/api/v1/projects/alpha/metrics?"
                             "timezone=Europe%2FBucharest&granularity=month")
        assert [(row["date"], row["tokens_in"]) for row in monthly.json()["daily"]] == [
            ("2026-03-01", 10)]
        selected = client.get("/api/v1/projects/alpha/metrics?"
                              "timezone=Europe%2FBucharest&granularity=week&"
                              "day_from=2026-03-29&day_to=2026-03-29")
        assert selected.json()["period"]["tokens_in"] == 3
        assert selected.json()["totals"]["tokens_in"] == 10
        assert "2026-03-23,1,0,3,1" in client.get(
            "/api/v1/projects/alpha/metrics.csv" + query).text
        attributed = client.get("/api/v1/projects/alpha/usage" + query)
        assert [(row["date"], row["tokens_in"]) for row in attributed.json()["daily"]] == [
            ("2026-03-23", 3), ("2026-03-30", 7)]
        assert "2026-03-23,,,1,3,1" in client.get(
            "/api/v1/projects/alpha/usage.csv" + query).text
        assert client.get("/api/v1/projects/alpha/metrics?"
                          "timezone=No%2FSuch_Zone").status_code == 422
        assert client.get("/api/v1/projects/alpha/metrics?"
                          "granularity=year").status_code == 422


def test_launch_coverage_is_idempotent_and_cost_status_is_admin_only(tmp_path):
    """@brief Replayed observations count once without duplicating usage."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="working"))
    observation = {
        "schema": 1, "event_id": "run-1:1", "attempt": 1,
        "stage": "build", "review_round": 0, "executor": "codex",
        "model": "example", "token_status": "reported",
        "cost_status": "unavailable", "tokens_in": 10,
        "tokens_out": 2, "cost_usd": None,
    }
    state.journal("run-1", "usage-observation", **observation)
    state.journal("run-1", "usage-observation", **observation)
    state.journal("run-1", "usage", tokens_in=10, tokens_out=2,
                  cost_usd=0, executor="codex", model="example")
    state.journal("run-1", "usage-observation", schema=1,
                  event_id="run-1:2", attempt=2, stage="validate",
                  review_round=0, executor="codex", model="example",
                  token_status="unavailable", cost_status="unavailable",
                  tokens_in=None, tokens_out=None, cost_usd=None)
    state.journal("run-1", "usage-observation", schema=1,
                  event_id="run-1:3", attempt=3, stage="deliver",
                  review_round=0, executor="codex", model="example",
                  token_status="disabled", cost_status="disabled",
                  tokens_in=None, tokens_out=None, cost_usd=None)
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "dev",
                                             "password": "longer-password"})
        response = client.get("/api/v1/projects/alpha/metrics")
        assert response.status_code == 200
        coverage = response.json()["coverage"]
        assert coverage["launches_with_reported_tokens"] == 1
        assert coverage["launches_with_unavailable_tokens"] == 1
        assert coverage["launches_capture_disabled"] == 1
        assert "cost" not in response.text.lower()
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin",
                                             "password": "admin"})
        body = client.get("/api/v1/projects/alpha/metrics").json()
        assert body["coverage"]["launches_with_unavailable_cost"] == 2
        assert body["coverage"]["launches_with_reported_cost"] == 0
        assert body["totals"]["tokens_in"] == 10


def test_conflicting_launch_observation_fails_closed(tmp_path):
    """@brief A conflicting replay cannot silently change coverage."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="working"))
    for status in ("reported", "unavailable"):
        state.journal("run-1", "usage-observation", schema=1,
                      event_id="run-1:1", attempt=1, stage="build",
                      review_round=0, executor="codex", model=None,
                      token_status=status, cost_status="unavailable",
                      tokens_in=1 if status == "reported" else None,
                      tokens_out=0 if status == "reported" else None,
                      cost_usd=None)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin",
                                             "password": "admin"})
        response = client.get("/api/v1/projects/alpha/metrics")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "metrics_corrupt"


def test_malformed_launch_observation_fails_closed(tmp_path):
    """@brief Missing reported token values cannot masquerade as coverage."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="working"))
    state.journal("run-1", "usage-observation", schema=1,
                  event_id="run-1:1", attempt=1, stage="build",
                  review_round=0, executor="codex", model=None,
                  token_status="reported", cost_status="unavailable",
                  tokens_in=None, tokens_out=0, cost_usd=None)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin",
                                             "password": "admin"})
        response = client.get("/api/v1/projects/alpha/metrics")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "metrics_corrupt"


def test_versioned_usage_replay_is_idempotent_in_views(tmp_path):
    """@brief Daily and attributed views count a replayed launch only once."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="working"))
    usage = {"event_id": "run-1:1", "attempt": 1, "context": "build",
             "executor": "codex", "model": "example", "review_round": 0,
             "tokens_in": 10, "tokens_out": 2, "cost_usd": 0.5,
             "cost_reported": True}
    state.journal("run-1", "usage", **usage)
    state.journal("run-1", "usage", **usage)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin",
                                             "password": "admin"})
        daily = client.get("/api/v1/projects/alpha/metrics")
        attributed = client.get("/api/v1/projects/alpha/usage")
        assert daily.status_code == 200 and attributed.status_code == 200
        assert daily.json()["totals"]["tokens_in"] == 10
        assert daily.json()["totals"]["cost_usd"] == 0.5
        assert attributed.json()["totals"]["events"] == 1
        assert attributed.json()["totals"]["tokens_in"] == 10
    state.journal("run-1", "usage", **{**usage, "cost_usd": 0.6})
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin",
                                             "password": "admin"})
        daily = client.get("/api/v1/projects/alpha/metrics")
        attributed = client.get("/api/v1/projects/alpha/usage")
        assert daily.status_code == attributed.status_code == 503
        assert daily.json()["detail"]["code"] == "metrics_corrupt"
        assert attributed.json()["detail"]["code"] == "usage_corrupt"


def test_token_only_legacy_event_has_unknown_cost(tmp_path):
    """@brief A legacy zero default never proves a zero-dollar charge."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    run = RunState(run_id="run-1", ticket_iid=42, lifecycle="done")
    state.save(run)
    state.journal(run.run_id, "picked")
    state.journal(run.run_id, "usage", tokens_in=12, tokens_out=3, cost_usd=0.0)
    metrics.record_summary(state.root / "metrics.db", metrics.summarize_run(state, run.run_id))
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        body = client.get("/api/v1/projects/alpha/metrics").json()
        assert body["totals"]["cost_usd"] is None
        assert body["runs"][0]["cost_usd"] is None
        assert body["daily"][0]["cost_usd"] is None


def test_corrupt_metrics_store_is_explicit_error(tmp_path):
    """@brief A corrupt projection is not silently treated as zero activity."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    (state.root / "metrics.db").parent.mkdir(parents=True, exist_ok=True)
    (state.root / "metrics.db").write_bytes(b"not sqlite")
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/metrics")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "metrics_corrupt"


def test_scoped_daily_csv_omits_developer_cost(tmp_path):
    """@brief CSV export uses the same project and financial boundaries."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="done"))
    state.journal("run-1", "picked")
    state.journal("run-1", "usage", tokens_in=4, tokens_out=2,
                  cost_usd=0.02, cost_reported=True)
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        text = client.get("/api/v1/projects/alpha/metrics.csv").text
        assert "tokens_in" in text and ",4,2" in text
        assert "cost" not in text.lower() and "0.02" not in text
        assert client.get("/api/v1/projects/beta/metrics.csv").status_code == 404
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        text = client.get("/api/v1/projects/alpha/metrics.csv").text
        assert "reported_cost_usd" in text and "0.02" in text


def test_csv_ignores_invalid_journal_dates(tmp_path):
    """@brief Persisted malformed dates cannot become spreadsheet formulas."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="done"))
    state.journal("run-1", "usage", ts="=1+1,,,,,,", tokens_in=4,
                  tokens_out=2, cost_usd=0.02)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        text = client.get("/api/v1/projects/alpha/metrics.csv").text
        assert "=1+1" not in text


def test_daily_usage_converts_timestamp_offsets_to_utc(tmp_path):
    """@brief Offset-midnight events share the correct UTC reporting day."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="working"))
    state.journal("run-1", "usage", ts="2026-03-30T00:15:00+02:00",
                  tokens_in=5, tokens_out=1)
    state.journal("run-1", "usage", ts="2026-03-29T22:30:00Z",
                  tokens_in=7, tokens_out=2)
    state.journal("run-1", "usage", ts="2026-03-30garbage",
                  tokens_in=1000, tokens_out=1000)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        body = client.get("/api/v1/projects/alpha/metrics").json()
        assert [day["date"] for day in body["daily"]] == ["2026-03-29"]
        assert body["daily"][0]["tokens_in"] == 12
        assert body["totals"]["tokens_in"] == 12


def test_metric_period_preserves_all_time_totals_and_filters_exports(tmp_path):
    """@brief A UTC period scopes daily evidence and CSV, never all-time totals."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = profiles.create("alpha", store_root=str(tmp_path / "alpha-state"))
    beta = profiles.create("beta", store_root=str(tmp_path / "beta-state"))
    alpha_state = StateStore(alpha.store_root)
    beta_state = StateStore(beta.store_root)
    alpha_state.save(RunState(run_id="alpha-1", ticket_iid=1, lifecycle="working"))
    beta_state.save(RunState(run_id="beta-1", ticket_iid=2, lifecycle="working"))
    alpha_state.journal("alpha-1", "usage", ts="2026-01-01T12:00:00Z",
                        tokens_in=3, tokens_out=1, cost_usd=0.2,
                        cost_reported=True)
    alpha_state.journal("alpha-1", "usage", ts="2026-01-01T23:30:00-02:00",
                        executor="codex", model="local-1", tokens_in=7,
                        tokens_out=2, cost_usd=0, cost_reported=False)
    beta_state.journal("beta-1", "usage", ts="2026-01-02T12:00:00Z",
                       tokens_in=11, tokens_out=4, cost_usd=0.4,
                       cost_reported=True)
    app = create_app(profiles.home)
    web = app.state.web_store
    web.add_price("alpha", "codex", "local-1", "2026-01-01", "2", "4", 1)
    developer = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(developer["id"], ["alpha"])
    period = "?day_from=2026-01-02&day_to=2026-01-02"
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        response = client.get("/api/v1/projects/alpha/metrics" + period)
        assert response.status_code == 200
        scoped = response.json()
        assert scoped["totals"]["tokens_in"] == 10
        assert [day["date"] for day in scoped["daily"]] == ["2026-01-02"]
        assert scoped["period"]["tokens_in"] == 7
        assert "cost" not in str(scoped).lower()
        export = client.get("/api/v1/projects/alpha/metrics.csv" + period)
        assert export.status_code == 200
        assert "2026-01-02" in export.text and "2026-01-01" not in export.text
        assert "cost" not in export.text.lower()
        assert client.get("/api/v1/metrics" + period).status_code == 403
        assert client.get("/api/v1/metrics.csv" + period).status_code == 403
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        scoped = client.get("/api/v1/projects/alpha/metrics" + period).json()
        assert scoped["totals"]["cost_usd"] == 0.2
        assert scoped["period"]["cost_usd"] is None
        assert scoped["period"]["estimated_cost_usd"] == 0.000022
        assert scoped["period"]["basis"] == "dated_events"
        before = client.get(
            "/api/v1/projects/alpha/metrics?day_to=2026-01-01").json()
        assert before["period"]["cost_usd"] == 0.2
        assert before["period"]["estimated_cost_usd"] is None
        empty = client.get(
            "/api/v1/projects/alpha/metrics?day_from=2026-02-01").json()
        assert empty["daily"] == []
        assert empty["period"]["tokens_in"] == 0
        assert empty["period"]["cost_usd"] is None
        assert empty["totals"]["tokens_in"] == 10
        global_view = client.get("/api/v1/metrics" + period).json()
        assert global_view["beta"]["period"]["tokens_in"] == 11
        assert global_view["beta"]["period"]["cost_usd"] == 0.4
        export = client.get("/api/v1/metrics.csv" + period)
        assert export.status_code == 200
        assert "2026-01-02" in export.text and "2026-01-01" not in export.text
        assert client.get(
            "/api/v1/projects/alpha/metrics?day_from=2026-01-03&day_to=2026-01-02"
        ).status_code == 422
        assert client.get(
            "/api/v1/projects/alpha/metrics.csv?day_from=invalid"
        ).status_code == 422
        assert client.get(
            "/api/v1/metrics.csv?day_from=2026-01-03&day_to=2026-01-02"
        ).status_code == 422
        assert client.get("/api/v1/metrics?day_from=invalid").status_code == 422


def test_period_does_not_assign_legacy_summary_usage_to_a_day(tmp_path):
    """@brief Summary-only usage stays all-time rather than fabricating a date."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="legacy", ticket_iid=3, lifecycle="done"))
    metrics.record_summary(state.root / "metrics.db", metrics.RunSummary(
        run_id="legacy", tokens_in=9, tokens_out=2))
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        response = client.get(
            "/api/v1/projects/alpha/metrics?day_from=2026-01-01&day_to=2026-01-31")
        assert response.status_code == 200
        body = response.json()
        assert body["totals"]["tokens_in"] == 9
        assert body["period"]["tokens_in"] == 0
        assert body["daily"] == []


def test_terminal_duration_uses_utc_completion_and_reports_coverage(tmp_path):
    """@brief Elapsed-time samples exclude undated history and respect UTC days."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    examples = (
        ("first", "2026-01-01T23:58:00+00:00", "2026-01-02T00:00:00+00:00", 120),
        ("second", "2026-01-03T00:00:00+02:00", "2026-01-03T00:03:00+02:00", 180),
        ("third", "2026-01-03T00:00:00+00:00", "2026-01-03T00:05:00+00:00", 300),
    )
    for run_id, started, ended, span in examples:
        state.save(RunState(run_id=run_id, ticket_iid=1, lifecycle="done"))
        metrics.record_summary(state.root / "metrics.db", metrics.RunSummary(
            run_id=run_id, lifecycle="done", started_at=started,
            ended_at=ended, span_seconds=span))
    state.save(RunState(run_id="legacy", ticket_iid=2, lifecycle="done"))
    metrics.record_summary(state.root / "metrics.db", metrics.RunSummary(
        run_id="legacy", lifecycle="done"))
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        body = client.get(
            "/api/v1/projects/alpha/metrics?day_from=2026-01-02&day_to=2026-01-02"
        ).json()
        assert body["duration"] == {"sampled_runs": 3, "avg_span_seconds": 200,
                                    "median_span_seconds": 180}
        assert body["period"]["duration"] == {"sampled_runs": 2,
                                                 "avg_span_seconds": 150,
                                                 "median_span_seconds": 150}
        assert "cost" not in str(body).lower()
        assert client.get("/api/v1/metrics").status_code == 403
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        global_view = client.get("/api/v1/metrics?day_from=2026-01-03").json()
        assert global_view["alpha"]["period"]["duration"] == {
            "sampled_runs": 1, "avg_span_seconds": 300,
            "median_span_seconds": 300}


def test_missing_or_corrupt_duration_evidence_is_explicit(tmp_path):
    """@brief Missing timestamps mean unavailable; corrupt persisted spans fail closed."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="legacy", ticket_iid=1, lifecycle="done"))
    metrics.record_summary(state.root / "metrics.db", metrics.RunSummary(
        run_id="legacy", lifecycle="done"))
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        body = client.get("/api/v1/projects/alpha/metrics").json()
        assert body["duration"] == {"sampled_runs": 0,
                                    "avg_span_seconds": None,
                                    "median_span_seconds": None}
        with sqlite3.connect(state.root / "metrics.db") as connection:
            connection.execute(
                "UPDATE run_summaries SET started_at = ?, ended_at = ?, "
                "span_seconds = ? WHERE run_id = ?",
                ("2026-01-01T00:00:00+00:00", "2026-01-01T00:00:01+00:00",
                 -1, "legacy"),
            )
        response = client.get("/api/v1/projects/alpha/metrics")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "metrics_corrupt"
        with sqlite3.connect(state.root / "metrics.db") as connection:
            connection.execute(
                "UPDATE run_summaries SET ended_at = ?, span_seconds = ? "
                "WHERE run_id = ?", ("not-a-date", 1, "legacy"),
            )
        response = client.get("/api/v1/projects/alpha/metrics")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "metrics_corrupt"


def test_attributed_usage_filters_project_global_and_csv_without_cost_leak(tmp_path):
    """@brief Model/executor filters use dated usage identity and role scope."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = profiles.create("alpha", store_root=str(tmp_path / "alpha-state"))
    beta = profiles.create("beta", store_root=str(tmp_path / "beta-state"))
    first = StateStore(alpha.store_root)
    second = StateStore(beta.store_root)
    first.save(RunState(run_id="first", ticket_iid=1))
    second.save(RunState(run_id="second", ticket_iid=2))
    first.journal("first", "usage", ts="2026-01-01T12:00:00Z",
                  executor="opencode", model="local/a", tokens_in=5,
                  tokens_out=2, cost_usd=0)
    first.journal("first", "usage", ts="2026-01-02T00:30:00+02:00",
                  executor="codex", model="cloud/b", tokens_in=7,
                  tokens_out=3, cost_usd=0.4, cost_reported=True)
    second.journal("second", "usage", ts="2026-01-01T13:00:00Z",
                   executor="opencode", model="local/a", tokens_in=11,
                   tokens_out=4, cost_usd=0)
    app = create_app(profiles.home)
    web = app.state.web_store
    web.add_price("alpha", "opencode", "local/a", "2026-01-01", "2", "4", 1)
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    query = "?executor=opencode&model=local%2Fa&day_from=2026-01-01&day_to=2026-01-01"
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "dev", "password": "longer-password"})
        result = client.get("/api/v1/projects/alpha/usage" + query)
        assert result.status_code == 200
        body = result.json()
        assert body["totals"]["tokens_in"] == 5
        assert body["totals"]["tokens_out"] == 2
        assert body["totals"]["events"] == 1
        assert body["daily"][0]["model"] == "local/a"
        assert "cost" not in result.text.lower()
        assert "price" not in result.text.lower()
        assert client.get("/api/v1/projects/beta/usage").status_code == 404
        assert client.get("/api/v1/usage" + query).status_code == 403
        assert client.get("/api/v1/usage.csv" + query).status_code == 403
        export = client.get("/api/v1/projects/alpha/usage.csv" + query)
        assert export.status_code == 200
        assert "local/a" in export.text and "cloud/b" not in export.text
        assert "cost" not in export.text.lower()
        assert client.get("/api/v1/projects/alpha/usage?model=%20").status_code == 422
        assert client.get(
            "/api/v1/projects/alpha/usage?day_from=2026-01-02&day_to=2026-01-01"
        ).status_code == 422
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        result = client.get("/api/v1/projects/alpha/usage" + query)
        assert result.json()["totals"]["estimated_cost_usd"] == 0.000018
        assert result.json()["totals"]["reported_cost_usd"] is None
        all_alpha = client.get("/api/v1/projects/alpha/usage").json()
        assert all_alpha["totals"]["reported_cost_usd"] == 0.4
        assert [row["date"] for row in all_alpha["daily"]] == ["2026-01-01"] * 2
        global_view = client.get("/api/v1/usage" + query).json()
        assert global_view["alpha"]["totals"]["tokens_in"] == 5
        assert global_view["beta"]["totals"]["tokens_in"] == 11
        export = client.get("/api/v1/usage.csv" + query)
        assert export.status_code == 200
        assert "project,repository,date,executor,model" in export.text
        assert "alpha" in export.text and "beta" in export.text
        assert "cloud/b" not in export.text


def test_attributed_usage_rejects_corrupt_persisted_identity(tmp_path):
    """@brief Non-text executor identity fails closed at the journal boundary."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="first", ticket_iid=1))
    state.journal("first", "usage", ts="2026-01-01T12:00:00Z",
                  executor={"bad": "value"}, model="local/a", tokens_in=5)
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/usage")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "usage_corrupt"
        assert "bad" not in response.text


def test_attributed_usage_csv_escapes_model_formula(tmp_path):
    """@brief A journal model label cannot become a spreadsheet formula."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="first", ticket_iid=1))
    state.journal("first", "usage", ts="2026-01-01T12:00:00Z",
                  executor="opencode", model="=1+1", tokens_in=5)
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        export = client.get("/api/v1/projects/alpha/usage.csv")
        assert export.status_code == 200
        assert ",=1+1," not in export.text
        assert ",'=1+1," in export.text


def test_attributed_usage_rejects_nonobject_journal_record(tmp_path):
    """@brief A parseable but non-object journal record is a typed error."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="first", ticket_iid=1))
    journal = state.run_dir("first") / "journal.jsonl"
    journal.write_text('[]\n', encoding="utf-8")
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/usage")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "usage_corrupt"
        metrics_response = client.get("/api/v1/projects/alpha/metrics")
        assert metrics_response.status_code == 503
        assert metrics_response.json()["detail"]["code"] == "metrics_corrupt"


def test_attributed_usage_rejects_out_of_range_cost(tmp_path):
    """@brief Oversize persisted money is a typed error, not an HTTP crash."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="first", ticket_iid=1))
    state.journal("first", "usage", ts="2026-01-01T12:00:00Z",
                  executor="opencode", model="local/a", tokens_in=5,
                  cost_usd=10**1000)
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/usage")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "usage_corrupt"
        daily = client.get("/api/v1/projects/alpha/metrics")
        assert daily.status_code == 200
        assert daily.json()["coverage"]["runs_with_usage"] == 0


def test_global_daily_csv_is_admin_only_and_identifies_repository(tmp_path):
    """@brief Global export keeps project/repo provenance and finance private."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", repo="=1+1", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="done"))
    state.journal("run-1", "usage", ts="2026-01-05T00:00:00+00:00",
                  tokens_in=4, tokens_out=2, cost_usd=0.02,
                  cost_reported=True)
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        assert client.get("/api/v1/metrics.csv").status_code == 403
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        response = client.get("/api/v1/metrics.csv")
        assert response.status_code == 200
        assert "project,repository,date" in response.text
        assert "alpha,'=1+1,2026-01-05" in response.text
        assert "0.02" in response.text


def test_live_run_usage_is_in_project_totals(tmp_path):
    """@brief Live journal usage reconciles with project/day totals."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="live-1", ticket_iid=8, lifecycle="working"))
    state.journal("live-1", "usage", ts="2026-01-05T00:00:00+00:00",
                  tokens_in=10, tokens_out=4, cost_usd=0.3,
                  cost_reported=True)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        body = client.get("/api/v1/projects/alpha/metrics").json()
        assert body["totals"]["tokens_in"] == 10
        assert body["totals"]["tokens_out"] == 4
        assert body["totals"]["cost_usd"] == 0.3
        assert body["daily"][0]["cost_usd"] == 0.3


def test_human_mr_revisions_and_pipeline_repairs_are_distinct(tmp_path):
    """@brief Quality metrics separate reviewer requests from CI repairs."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="in-review"))
    for stamp, trigger in (
        ("2026-01-05T00:00:00+00:00", "revise-label"),
        ("2026-01-05T12:00:00+00:00", "pipeline-failed"),
        ("2026-01-06T00:00:00+00:00", "unrecognized"),
    ):
        state.journal("run-1", "revision-started", ts=stamp, trigger=trigger)
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        body = client.get("/api/v1/projects/alpha/metrics").json()
        assert body["totals"]["mr_revisions"] == 1
        assert body["totals"]["pipeline_repairs"] == 1
        assert body["daily"][0]["mr_revisions"] == 1
        assert body["daily"][0]["pipeline_repairs"] == 1
        assert body["coverage"]["revision_events_unclassified"] == 1
        exported = client.get("/api/v1/projects/alpha/metrics.csv").text
        assert "mr_revisions,pipeline_repairs" in exported
        assert "cost" not in exported.lower()


def test_revision_cost_attribution_is_admin_only_and_preserves_unknowns(tmp_path):
    """@brief Attribute subsequent usage to each revision without inventing cost."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="in-review"))
    state.journal("run-1", "usage", ts="2026-01-02T00:00:00+00:00",
                  tokens_in=10, tokens_out=2, cost_usd=0.5, cost_reported=True)
    state.journal("run-1", "revision-started", ts="2026-01-03T00:00:00+00:00",
                  trigger="revise-label")
    state.journal("run-1", "usage", ts="2026-01-03T00:01:00+00:00",
                  executor="codex", model="local-1", tokens_in=1_000_000,
                  tokens_out=1_000_000, cost_usd=0.0, cost_reported=False)
    state.journal("run-1", "revision-started", ts="2026-01-04T00:00:00+00:00",
                  trigger="pipeline-failed")
    state.journal("run-1", "usage", ts="2026-01-04T00:01:00+00:00",
                  executor="codex", model="local-1", tokens_in=3,
                  tokens_out=4, cost_usd=0.25, cost_reported=True)
    state.journal("run-1", "revision-started", ts="2026-01-05T00:00:00+00:00",
                  trigger="revise-label")
    state.journal("run-1", "revision-started", ts="2026-01-06T00:00:00+00:00",
                  trigger="<script>untrusted</script>")
    app = create_app(profiles.home)
    web = app.state.web_store
    web.add_price("alpha", "codex", "local-1", "2026-01-01", "2", "4", 1)
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        developer = client.get("/api/v1/projects/alpha/metrics").json()
        assert "revisions" not in developer
        assert "cost" not in str(developer).lower()
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        body = client.get("/api/v1/projects/alpha/metrics").json()
        revisions = body["revisions"]
        assert [(row["revision"], row["trigger"], row["date"])
                for row in revisions] == [
                    (1, "revise-label", "2026-01-03"),
                    (2, "pipeline-failed", "2026-01-04"),
                    (3, "revise-label", "2026-01-05"),
                    (4, "unclassified", "2026-01-06"),
                ]
        assert [(row["tokens_in"], row["tokens_out"]) for row in revisions] == [
            (1_000_000, 1_000_000), (3, 4), (0, 0), (0, 0)]
        assert [row["reported_cost_usd"] for row in revisions] == [
            None, 0.25, None, None]
        assert [row["estimated_cost_usd"] for row in revisions] == [
            6.0, None, None, None]
        assert "<script>" not in str(revisions)
        assert body["totals"]["cost_usd"] == 0.75
        assert body["totals"]["estimated_cost_usd"] == 6.0


def test_quality_rates_use_evidence_cohorts_and_keep_open_reviews_separate(tmp_path):
    """@brief Rates count eligible jobs once, not every revision or launch."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    examples = (
        ("first-pass", "done", "merged by human", [
            ("strict-verification", {"passed": True}), ("mr-opened", {})]),
        ("reworked", "done", "merged by human", [
            ("strict-verification", {"passed": False}),
            ("strict-verification", {"passed": True}),
            ("mr-opened", {}),
            ("revision-started", {"trigger": "revise-label"}),
            ("revision-started", {"trigger": "revise-label"})]),
        ("open", "in-review", "", [
            ("strict-verification", {"passed": True}), ("mr-adopted", {}),
            ("revision-started", {"trigger": "pipeline-failed"})]),
        ("failed-before-review", "failed", "", [
            ("strict-verification", {"passed": False})]),
        ("legacy", "done", "merged by human", []),
    )
    for run_id, lifecycle, outcome, events in examples:
        state.save(RunState(run_id=run_id, ticket_iid=1, lifecycle=lifecycle,
                            outcome=outcome))
        for event, fields in events:
            state.journal(run_id, event, **fields)
    app = create_app(profiles.home)
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    expected = {
        "reviewed_jobs": 3, "reworked_jobs": 1,
        "review_rework_rate": 1 / 3, "open_review_jobs": 1,
        "validated_jobs": 4, "first_pass_validations": 2,
        "first_validation_rate": 0.5,
        "human_merged_jobs": 2, "first_pass_merges": 1,
        "first_pass_merge_rate": 0.5,
        "stage_failures": 0, "operator_retries": 0,
    }
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        response = client.get("/api/v1/projects/alpha/metrics")
        assert response.status_code == 200
        assert response.json()["quality"] == expected
        assert "cost" not in response.text.lower()
        assert client.get("/api/v1/metrics").status_code == 403
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        admin_quality = client.get("/api/v1/metrics").json()["alpha"]["quality"]
        assert {key: value for key, value in admin_quality.items()
                if key != "cost_efficiency"} == expected
        assert admin_quality["cost_efficiency"]["reported_per_completed"] == {
            "jobs_with_evidence": 0, "usd_per_job": None}


def test_quality_cost_per_job_uses_evidence_denominators_and_role_privacy(tmp_path):
    """@brief Reported and estimated USD use separate known-job cohorts."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    for run_id, lifecycle, outcome, cost_reported in (
        ("merged", "done", "merged by human", True),
        ("estimated", "done", "", False),
        ("failed", "failed", "", True),
    ):
        state.save(RunState(run_id=run_id, ticket_iid=1,
                            lifecycle=lifecycle, outcome=outcome))
        state.journal(run_id, "usage", executor="codex", model="local-1",
                      tokens_in=1_000_000, tokens_out=0,
                      cost_usd=4 if cost_reported else 0,
                      cost_reported=cost_reported)
        state.journal(run_id, "stage-failed", stage="build")
        state.journal(run_id, "operator-retry", stage="build")
    app = create_app(profiles.home)
    web = app.state.web_store
    web.add_price("alpha", "codex", "local-1", "2026-01-01", "2", "4", 1)
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        quality = client.get("/api/v1/projects/alpha/metrics").json()["quality"]
        assert quality["stage_failures"] == 3
        assert quality["operator_retries"] == 3
        assert quality["cost_efficiency"]["reported_per_completed"] == {
            "jobs_with_evidence": 1, "usd_per_job": 4.0}
        assert quality["cost_efficiency"]["estimated_per_completed"] == {
            "jobs_with_evidence": 1, "usd_per_job": 2.0}
        assert quality["cost_efficiency"]["reported_per_human_merged"] == {
            "jobs_with_evidence": 1, "usd_per_job": 4.0}
        assert quality["cost_efficiency"]["estimated_per_human_merged"] == {
            "jobs_with_evidence": 0, "usd_per_job": None}
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"})
        body = client.get("/api/v1/projects/alpha/metrics").json()
        assert "cost_efficiency" not in body["quality"]
        assert "usd" not in str(body).lower()


def test_quality_rates_have_nullable_empty_denominators_and_reject_bad_verdict(tmp_path):
    """@brief Unknown cohorts stay unavailable and malformed verdicts fail closed."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="working"))
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"})
        quality = client.get("/api/v1/projects/alpha/metrics").json()["quality"]
        assert quality["review_rework_rate"] is None
        assert quality["first_validation_rate"] is None
        assert quality["first_pass_merge_rate"] is None
        state.journal("run-1", "strict-verification", passed="yes")
        response = client.get("/api/v1/projects/alpha/metrics")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "metrics_corrupt"
