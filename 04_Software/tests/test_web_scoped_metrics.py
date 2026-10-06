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
@file    test_web_scoped_metrics.py
@brief   Analytical fixtures for consistent scoped web metrics.
@details Hand-calculated local-midnight, lifecycle and consumption boundaries;
         all sources and authorization are local and offline.
"""

# IMPORTS
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import sqlite3

from adore import metrics
from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest


# PUBLIC API
@pytest.mark.parametrize(
    ("day", "start", "end", "hours"),
    [
        ("2026-03-29", "2026-03-28T22:00:00Z", "2026-03-29T21:00:00Z", 23),
        ("2026-10-25", "2026-10-24T21:00:00Z", "2026-10-25T22:00:00Z", 25),
    ],
)
def test_scope_uses_half_open_local_midnights_and_own_events(tmp_path, day, start, end, hours):
    """@brief Both DST days include their lower boundary and exclude their upper."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="cross", ticket_iid=1, lifecycle="failed"))
    state.journal("cross", "picked", ts="2026-01-01T00:00:00Z")
    state.journal("cross", "usage", ts=start, tokens_in=7, tokens_out=2)
    state.journal("cross", "stage-failed", ts=start)
    state.journal("cross", "usage", ts=end, tokens_in=11, tokens_out=3)
    state.journal("cross", "checkpoint-pushed", ts=end)
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        suffix = f"?day_from={day}&day_to={day}&timezone=Europe/Bucharest"
        body = client.get("/api/v1/projects/alpha/metrics" + suffix).json()
        assert body["totals"]["tokens_in"] == 7
        assert body["totals"]["started"] == 0
        assert body["totals"]["completed"] == body["totals"]["failed"] == 1
        assert body["scope"]["from"] == start.replace("Z", "+00:00")
        assert body["scope"]["to"] == end.replace("Z", "+00:00")
        assert body["scope"]["interval_seconds"] == hours * 3600
        assert body["current_stock"]["active_now"] == 0
        assert body["period"]["tokens_in"] == 7
        assert body["jobs"][0]["coverage"]["period_usage_events"] == 1
        assert body["daily"][0]["tokens_in"] == 7
        usage = client.get("/api/v1/projects/alpha/usage" + suffix).json()
        assert usage["totals"]["tokens_in"] == 7
        assert usage["scope"] == body["scope"]
        export = client.get("/api/v1/projects/alpha/metrics.csv" + suffix)
        rows = list(csv.DictReader(StringIO(export.text)))
        assert [int(row["tokens_in"]) for row in rows] == [7]


def test_jobs_keep_lifetime_period_unallocated_and_composite_identity(tmp_path):
    """@brief Cross-period job evidence is separate from undated legacy summaries."""
    profiles = ProfileStore(tmp_path / "home")
    identities = []
    for name, amount in (("alpha", 5), ("beta", 13)):
        profile = profiles.create(name, store_root=str(tmp_path / name))
        identities.append(profile.project_id)
        state = StateStore(profile.store_root)
        state.save(RunState(run_id="same", ticket_iid=1, lifecycle="working"))
        for stamp, count in (
            ("2026-01-01T12:00:00Z", 3),
            ("2026-01-02T12:00:00Z", amount),
            ("invalid", 7),
        ):
            state.journal(
                "same",
                "usage",
                ts=stamp,
                tokens_in=count,
                tokens_out=0,
                executor="codex",
                model="m",
                cost_usd=0,
                cost_reported=True,
            )
        state.save(RunState(run_id="unknown", ticket_iid=2, lifecycle="working"))
        state.save(RunState(run_id="zero", ticket_iid=3, lifecycle="working"))
        state.journal(
            "zero",
            "usage",
            ts="2026-01-02T00:00:00Z",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0,
            cost_reported=True,
        )
        state.save(RunState(run_id="summary", ticket_iid=4, lifecycle="done"))
        metrics.record_summary(
            state.root / "metrics.db",
            metrics.RunSummary(run_id="summary", tokens_in=19, tokens_out=2),
        )
    app = create_app(profiles.home)
    dev = app.state.web_store.create_user("dev", "longer-password", "developer")
    app.state.web_store.set_memberships(dev["id"], ["alpha"])
    suffix = "?day_from=2026-01-02&day_to=2026-01-02"
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        body = client.get("/api/v1/metrics" + suffix).json()
        for index, (name, amount) in enumerate((("alpha", 5), ("beta", 13))):
            job = next(j for j in body[name]["jobs"] if j["run_id"] == "same")
            assert job["project_id"] == identities[index]
            assert job["lifetime"]["tokens_in"] == 10 + amount
            assert job["in_period"]["tokens_in"] == amount
            assert job["unallocated"]["tokens_in"] == 7
            usage = client.get(f"/api/v1/projects/{name}/usage" + suffix).json()
            assert usage["unallocated"]["tokens_in"] == 26  # undated 7 + summary 19
            assert usage["totals"]["tokens_in"] == amount
            assert usage["coverage"]["summary_only_runs"] == 1
        all_time = client.get("/api/v1/projects/alpha/metrics").json()
        assert all_time["scope"]["mode"] == "all_time"
        jobs = {j["run_id"]: j for j in all_time["jobs"]}
        assert jobs["unknown"]["lifetime"]["tokens_in"] is None
        assert jobs["zero"]["in_period"]["tokens_in"] == 0
        assert jobs["zero"]["in_period"]["reported_cost_usd"] == 0
        assert jobs["summary"]["source"] == "summary"
        assert jobs["summary"]["in_period"]["tokens_in"] is None
        client.cookies.clear()
        client.post("/api/v1/session", json={"username": "dev", "password": "longer-password"})
        for route in ("metrics", "usage", "metrics.csv", "usage.csv", "jobs-usage.csv"):
            response = client.get("/api/v1/projects/alpha/" + route + suffix)
            assert response.status_code == 200
            assert "cost" not in response.text.lower() and "usd" not in response.text.lower()
            assert client.get("/api/v1/projects/beta/" + route).status_code == 404
        assert client.get("/api/v1/jobs-usage.csv").status_code == 403


@pytest.mark.parametrize(
    "raw",
    [
        b'{"event":"usage",',
        b"[]\n",
        b'{"event":"usage","tokens_in":NaN}\n',
        b'{"event":"picked","schema":2}\n',
        b'{"event":"picked","ts":123}\n',
        b'{"event":"usage","tokens_in":-1,"tokens_out":0}\n',
        b'{"event":"usage","tokens_in":1,"tokens_out":0,"cost_usd":"NaN"}\n',
        b'{"event":"picked","event":"done"}\n',
    ],
)
def test_corrupt_sources_fail_before_filtering_and_preserve_bytes(tmp_path, raw):
    """@brief Unselected malformed evidence never hides behind an empty interval."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="r", ticket_iid=1, lifecycle="working"))
    journal = state.run_dir("r") / "journal.jsonl"
    journal.write_bytes(raw)
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        for route in ("metrics", "usage", "metrics.csv", "usage.csv"):
            response = client.get(f"/api/v1/projects/alpha/{route}?day_from=2099-01-01")
            assert response.status_code == 503
            assert response.json()["detail"]["code"] in ("metrics_corrupt", "usage_corrupt")
        assert journal.read_bytes() == raw


@pytest.mark.parametrize(
    "query",
    [
        "day_from=invalid",
        "day_from=2026-02-02&day_to=2026-01-01",
        "timezone=Unknown/Zone",
        "timezone=../UTC",
        "day_to=9999-12-31",
        "granularity=year",
        "executor=%20",
        "model=%0A",
    ],
)
def test_invalid_scope_and_filters_return_typed_errors(tmp_path, query):
    """@brief Scope validation is independent of whether a project has jobs."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        for route in ("usage", "usage.csv"):
            response = client.get(f"/api/v1/projects/alpha/{route}?{query}")
            assert response.status_code == 422
            assert response.json()["detail"]
        response = client.get("/api/v1/usage?" + query)
        assert response.status_code == 422


def test_replay_includes_timestamp_and_schema_is_strict(tmp_path):
    """@brief Replayed versioned consumption cannot move into another period."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="r", ticket_iid=1, lifecycle="working"))
    usage = dict(
        event_id="r:1",
        attempt=1,
        context="build",
        executor="codex",
        model="m",
        review_round=0,
        tokens_in=2,
        tokens_out=0,
        cost_usd=0,
        cost_reported=True,
        ts="2026-01-01T00:00:00Z",
    )
    state.journal("r", "usage", **usage)
    state.journal("r", "usage", **usage)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        for _ in range(2):
            assert client.get("/api/v1/projects/alpha/metrics").json()["totals"]["tokens_in"] == 2
        state.journal("r", "usage", **{**usage, "ts": "2026-01-02T00:00:00Z"})
        for route in ("metrics", "usage"):
            assert client.get("/api/v1/projects/alpha/" + route).status_code == 503
        journal = state.run_dir("r") / "journal.jsonl"
        journal.unlink()
        saved = state.run_dir("r") / "state.json"
        value = json.loads(saved.read_text())
        value["schema_version"] = 999
        saved.write_text(json.dumps(value))
        assert client.get("/api/v1/projects/alpha/metrics").status_code == 503
        assert json.loads(saved.read_text())["schema_version"] == 999


def test_server_samples_and_quality_cohorts_are_scoped(tmp_path):
    """@brief Hand-calculated first-event cohorts and terminal spans agree."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    for name, first_day, passed, seconds in (("old", "01", False, 120), ("new", "02", True, 0)):
        state.save(RunState(run_id=name, ticket_iid=1, lifecycle="done", outcome="merged by human"))
        state.journal(name, "picked", ts=f"2026-01-{first_day}T00:00:00Z")
        state.journal(
            name, "strict-verification", passed=passed, ts=f"2026-01-{first_day}T00:01:00Z"
        )
        state.journal(name, "mr-opened", ts=f"2026-01-{first_day}T00:02:00Z")
        if name == "old":
            state.journal(
                name, "revision-started", trigger="revise-label", ts="2026-01-02T00:03:00Z"
            )
        state.journal(name, "done", ts="2026-01-02T01:00:00Z")
        metrics.record_summary(
            state.root / "metrics.db",
            metrics.RunSummary(
                run_id=name,
                lifecycle="done",
                started_at="2026-01-02T00:00:00Z",
                ended_at=f"2026-01-02T00:{seconds // 60:02d}:00Z",
                span_seconds=seconds,
            ),
        )
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        body = client.get(
            "/api/v1/projects/alpha/metrics?day_from=2026-01-02&day_to=2026-01-02"
        ).json()
        assert body["quality"]["reviewed_jobs"] == body["quality"]["validated_jobs"] == 1
        assert body["quality"]["review_rework_rate"] == 0
        assert body["quality"]["first_validation_rate"] == 1
        assert body["quality"]["human_merged_jobs"] == 2
        assert body["quality"]["first_pass_merge_rate"] == 0.5
        assert body["duration"]["samples_seconds"] == [0, 120]
        assert body["duration"]["avg_span_seconds"] == body["duration"]["median_span_seconds"] == 60
        assert body["period"]["duration"] == body["duration"]


def test_price_history_uses_consumption_utc_day_and_filtered_job_csv(tmp_path):
    """@brief Local-day reporting keeps UTC pricing and separate measured zero."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="r", ticket_iid=1, lifecycle="working"))
    for stamp, amount, reported in (
        ("2026-01-01T22:30:00Z", 1_000_000, False),
        ("2026-01-02T00:30:00Z", 0, False),
        ("2026-01-02T01:00:00Z", 1_000_000, True),
    ):
        state.journal(
            "r",
            "usage",
            ts=stamp,
            executor="codex",
            model="m",
            tokens_in=amount,
            tokens_out=0,
            cost_usd=0,
            cost_reported=reported,
        )
    app = create_app(profiles.home)
    app.state.web_store.add_price("alpha", "codex", "m", "2026-01-01", "2", "4", 1)
    app.state.web_store.add_price("alpha", "codex", "m", "2026-01-02", "9", "4", 1)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        query = "?day_from=2026-01-02&day_to=2026-01-02&timezone=Europe/Bucharest"
        body = client.get("/api/v1/projects/alpha/usage" + query).json()
        assert body["totals"]["estimated_cost_usd"] == 2
        assert body["totals"]["reported_cost_usd"] == 0
        response = client.get("/api/v1/projects/alpha/jobs-usage.csv" + query + "&model=m")
        rows = list(csv.DictReader(StringIO(response.text)))
        assert len(rows) == 1
        assert rows[0]["project_id"] == profile.project_id
        assert rows[0]["in_period_tokens_in"] == "2000000"
        assert rows[0]["in_period_reported_cost_usd"] == "0"
        assert rows[0]["in_period_estimated_cost_usd"] == "2.0"
        assert json.loads(response.headers["X-ADORE-Scope"])[0] == body["scope"]
        empty = client.get("/api/v1/projects/alpha/jobs-usage.csv" + query + "&model=other")
        assert list(csv.DictReader(StringIO(empty.text))) == []
        assert json.loads(empty.headers["X-ADORE-Scope"])[0] == body["scope"]


def test_legacy_summary_reads_are_read_only_and_unknown_columns_fail_closed(tmp_path):
    """@brief Old table reads retain bytes and neutral defaults without ALTER TABLE."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="r", ticket_iid=1, lifecycle="done"))
    db = state.root / "metrics.db"
    with sqlite3.connect(db) as connection:
        connection.execute(
            "CREATE TABLE run_summaries (run_id TEXT PRIMARY KEY, tokens_in INTEGER)"
        )
        connection.execute("INSERT INTO run_summaries VALUES ('r',5)")
    before = sha256(db.read_bytes()).hexdigest()
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        body = client.get("/api/v1/projects/alpha/metrics").json()
        assert body["unallocated"]["tokens_in"] == 5
        assert sha256(db.read_bytes()).hexdigest() == before
        with sqlite3.connect(db) as connection:
            connection.execute("ALTER TABLE run_summaries ADD COLUMN future_schema INTEGER")
        before = sha256(db.read_bytes()).hexdigest()
        assert client.get("/api/v1/projects/alpha/metrics").status_code == 503
        assert sha256(db.read_bytes()).hexdigest() == before


def test_missing_dates_partial_usage_and_current_stock_remain_explicit(tmp_path):
    """@brief Unallocated/partial measurements never become period zero or dates."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="r", ticket_iid=1, lifecycle="working"))
    for stamp in (None, "", "2026-01-01", "2026-01-01T00:00:00", "invalid"):
        state.journal("r", "usage", ts=stamp, tokens_in=3)
    state.journal("r", "usage", ts="2026-01-01T00:00:00Z")
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        body = client.get("/api/v1/projects/alpha/metrics?day_from=2026-01-01").json()
        assert body["unallocated"]["tokens_in"] == 15
        assert body["unallocated"]["tokens_out"] is None
        assert body["coverage"]["usage_events_unallocated"] == 5
        assert body["totals"]["tokens_in"] is None
        assert body["totals"]["tokens_out"] is None
        assert body["totals"]["started"] == 0
        assert body["current_stock"]["active_now"] == 1
        assert body["current_stock"]["basis"] == "current_state"
        assert body["scope"]["mode"] == "interval"


# END OF FILE


@pytest.mark.parametrize("fault", ["sum-overflow", "versioned-time", "estimate-overflow"])
def test_numeric_boundaries_fail_before_filtering(tmp_path, fault):
    """@brief Overflow and unsupported dated versioned evidence fail safely."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="r", ticket_iid=1, lifecycle="working"))
    if fault == "sum-overflow":
        for _ in range(2):
            state.journal(
                "r", "usage", ts="2026-01-02T00:00:00Z", cost_usd=1e308, cost_reported=True
            )
    elif fault == "versioned-time":
        state.journal(
            "r",
            "usage",
            ts="invalid",
            event_id="r:1",
            attempt=1,
            context="build",
            executor="codex",
            model="m",
            review_round=0,
            tokens_in=1,
            tokens_out=0,
            cost_usd=0,
            cost_reported=False,
        )
    else:
        state.journal(
            "r",
            "usage",
            ts="2026-01-02T00:00:00Z",
            executor="codex",
            model="m",
            tokens_in=10**400,
            tokens_out=0,
        )
    app = create_app(profiles.home)
    if fault == "estimate-overflow":
        app.state.web_store.add_price("alpha", "codex", "m", "2026-01-01", "1", "1", 1)
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/metrics?day_from=2099-01-01")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "metrics_corrupt"


def test_summary_without_runtime_state_keeps_historical_evidence(tmp_path):
    """@brief Removed runtime jobs retain measured summary history, never current stock."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    metrics.record_summary(
        Path(profile.store_root) / "metrics.db",
        metrics.RunSummary(
            run_id="archived",
            lifecycle="done",
            started_at="2026-01-02T00:00:00Z",
            ended_at="2026-01-02T00:01:00Z",
            span_seconds=60,
            tokens_in=5,
        ),
    )
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        body = client.get(
            "/api/v1/projects/alpha/metrics?day_from=2026-01-02&day_to=2026-01-02"
        ).json()
        assert body["totals"]["started"] == body["totals"]["completed"] == 1
        assert body["current_stock"]["jobs_now"] == 0
        assert body["duration"]["samples_seconds"] == [60]
        assert body["jobs"][0]["lifetime"]["tokens_in"] == 5
        assert body["jobs"][0]["lifetime"]["tokens_out"] is None
        assert body["jobs"][0]["in_period"]["tokens_in"] is None


def test_quality_only_activity_selects_period_job_without_new_start(tmp_path):
    """@brief Earlier jobs entering review in scope retain honest lifecycle counters."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="r", ticket_iid=1, lifecycle="in-review"))
    state.journal("r", "picked", ts="2026-01-01T00:00:00Z")
    state.journal("r", "mr-opened", ts="2026-01-02T00:00:00Z")
    state.journal("r", "strict-verification", ts="2026-01-02T00:01:00Z", passed=True)
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        body = client.get("/api/v1/projects/alpha/metrics?day_from=2026-01-02"
                          "&day_to=2026-01-02").json()
        assert body["totals"]["runs"] == 1
        assert body["totals"]["started"] == body["totals"]["completed"] == 0
        assert body["jobs"][0]["coverage"]["period_usage_events"] == 0
        assert body["quality"]["reviewed_jobs"] == 1
        assert body["quality"]["first_validation_rate"] == 1
        assert body["jobs"][0]["run_id"] == "r"


@pytest.mark.parametrize("event", ["usage", "revision-started"])
def test_unrepresentable_local_event_timestamp_fails_typed(tmp_path, event):
    """@brief Valid ISO extremes cannot overflow silently during local grouping."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    state.save(RunState(run_id="r", ticket_iid=1, lifecycle="working"))
    state.journal("r", event, ts="9999-12-31T23:59:59Z", tokens_in=1, tokens_out=0)
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/projects/alpha/metrics?timezone=Europe/Bucharest")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "metrics_corrupt"


def test_empty_global_csv_still_describes_requested_scope(tmp_path):
    """@brief Empty authorized project sets preserve canonical export parameters."""
    with TestClient(create_app(tmp_path / "home")) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        for route in ("metrics.csv", "usage.csv", "jobs-usage.csv"):
            response = client.get("/api/v1/" + route + "?day_from=2026-10-25"
                                  "&day_to=2026-10-25&timezone=Europe/Bucharest")
            assert response.status_code == 200
            scope = json.loads(response.headers["X-ADORE-Scope"])[0]
            assert scope["project_ids"] == []
            assert scope["interval_seconds"] == 25 * 3600
