#!/usr/bin/env python3
# -*- coding: utf-8 -*-  # noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_metrics.py
@brief Tests for statistics capture and query (journal -> summary -> SQLite).
"""

from __future__ import annotations

# IMPORTS
from dataclasses import fields
import json
from pathlib import Path
import sqlite3

from adore.metrics import (
    MetricsError,
    RunSummary,
    aggregate,
    export_csv,
    is_terminal,
    load_analytical_summaries,
    load_summaries,
    profile_stats,
    record_summary,
    render_html,
    summarize_run,
    unique_usage_events,
)
from adore.state import RunState, StateError, StateStore
import pytest

from tests.usage_events import versioned_usage

# HELPER FUNCTIONS


def _seed_run(tmp_path: Path) -> StateStore:
    """
    @brief      A store with one finished run: journal, state, ticket.
    @param[in]  tmp_path pytest tmp dir.
    @return     The StateStore with run "r-45".
    """
    store = StateStore(tmp_path / ".adore")
    store.save(RunState(
        run_id="r-45", ticket_iid=45, lifecycle="done", outcome="merged",
        clarification_rounds=2, review_rounds=1, mr_url="https://x/mr/29",
    ))
    store.save_ticket("r-45", {"iid": 45, "title": "PILOT ticket",
                               "labels": ["agent-ready", "P1"]})
    timeline = [
        ("2026-07-04T10:00:00Z", "picked", {}),
        ("2026-07-04T10:00:01Z", "stage-launch", {"stage": "frame"}),
        ("2026-07-04T10:03:00Z", "usage",
         versioned_usage("r-45", 1, context="frame", tokens_in=1000,
                         tokens_out=50, cost_usd=0.02)),
        ("2026-07-04T10:03:01Z", "stage-advanced", {"stage": "frame"}),
        ("2026-07-04T10:03:02Z", "stage-launch", {"stage": "specify"}),
        ("2026-07-04T10:05:00Z", "stage-failed", {"stage": "specify"}),
        ("2026-07-04T10:05:01Z", "stage-launch", {"stage": "specify"}),
        ("2026-07-04T10:08:00Z", "strict-verification", {"passed": False}),
        ("2026-07-04T10:08:01Z", "parked", {"round": 1}),
        ("2026-07-04T11:08:01Z", "resumed", {}),
        ("2026-07-04T11:08:02Z", "stage-launch", {"stage": "specify"}),
        ("2026-07-04T11:10:00Z", "usage",
         versioned_usage("r-45", 2, context="specify", tokens_in=2000,
                         tokens_out=150, cost_usd=0.03)),
        ("2026-07-04T11:10:01Z", "stage-advanced", {"stage": "specify"}),
        ("2026-07-04T11:19:59Z", "validation-accepted", {"passed": True}),
        ("2026-07-04T11:20:00Z", "mr-opened", {"url": "https://x/mr/29"}),
        ("2026-07-04T12:00:00Z", "merged", {"mr": "https://x/mr/29"}),
    ]
    import json as _json
    journal = store.run_dir("r-45") / "journal.jsonl"
    with journal.open("w", encoding="utf-8") as handle:
        for ts, event, extra in timeline:
            handle.write(_json.dumps({"ts": ts, "event": event, **extra}) + "\n")
    return store


# PUBLIC API / TESTS


def test_summarize_run_computes_the_catalog(tmp_path: Path) -> None:
    """
    @brief   The summary derives every catalog field from the journal: gate
             outcomes, launches, usage totals, park wait, time-to-MR, span.
    """
    store = _seed_run(tmp_path)
    summary = summarize_run(store, "r-45", files_changed=3)
    assert summary.ticket_iid == 45
    assert summary.priority == "P1"
    assert summary.outcome == "merged"
    assert summary.governance_outcome == "ok"
    assert summary.gates_passed == 2
    assert summary.gate_failures == 1
    assert summary.invariant_failures == 1
    assert summary.executor_launches == 4
    assert summary.tokens_in == 3000 and summary.tokens_out == 200
    assert summary.cost_usd == 0.05
    assert summary.parked_wait_seconds == 3600
    assert summary.time_to_mr_seconds == 4800   # 10:00 -> 11:20
    assert summary.span_seconds == 7200         # 10:00 -> 12:00
    assert summary.files_changed == 3
    assert summary.clarification_rounds == 2 and summary.review_rounds == 1


@pytest.mark.parametrize("workflow", ["aegis", "direct"])
def test_summary_serializes_recorded_workflow(tmp_path: Path, workflow: str) -> None:
    """@brief Workflow survives summaries and exports without inventing a strict pass."""
    store = StateStore(tmp_path / "state")
    run = RunState(run_id="workflow-1", ticket_iid=1, workflow=workflow,
                   stage="done", lifecycle="done",
                   validation_evidence={"verification": "not configured"})
    store.save(run)
    summary = summarize_run(store, run.run_id)
    assert getattr(summary, "workflow", None) == workflow
    assert summary.governance_outcome == ""
    db, mirror = tmp_path / "metrics.db", tmp_path / "runs.jsonl"
    record_summary(db, summary, mirror)
    assert load_summaries(db)[0].workflow == workflow
    assert load_analytical_summaries(db)[0].workflow == workflow
    assert json.loads(mirror.read_text(encoding="utf-8"))["workflow"] == workflow
    assert "workflow" in export_csv([summary]).splitlines()[0]
    output = render_html([summary], tmp_path / "report.html").read_text(encoding="utf-8")
    assert "<th>workflow</th>" in output and f"<td>{workflow}</td>" in output
    data = run.to_dict()
    data["workflow"] = "unknown"
    path = store.run_dir(run.run_id) / "state.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(StateError, match="unknown workflow"):
        summarize_run(store, run.run_id)


@pytest.mark.parametrize("loader", [load_summaries, load_analytical_summaries])
@pytest.mark.parametrize("workflow", ["unknown", "", None, 1])
def test_summary_unknown_workflow_is_refused(tmp_path: Path, loader, workflow: object) -> None:
    """@brief Corrupt summary workflow cannot be inferred from task or governance data."""
    db = tmp_path / "metrics.db"
    record_summary(db, RunSummary(run_id="workflow-1"))
    assert "workflow" in {item.name for item in fields(RunSummary)}
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE run_summaries SET workflow = ?", (workflow,))
    before = db.read_bytes()
    with pytest.raises(MetricsError):
        loader(db)
    assert db.read_bytes() == before


@pytest.mark.parametrize("loader", [load_summaries, load_analytical_summaries])
def test_summary_missing_workflow_column_is_refused(tmp_path: Path, loader) -> None:
    """@brief A previous table shape is refused unchanged rather than extended."""
    db = tmp_path / "metrics.db"
    record_summary(db, RunSummary(run_id="workflow-1"))
    assert "workflow" in {item.name for item in fields(RunSummary)}
    with sqlite3.connect(db) as connection:
        connection.execute("ALTER TABLE run_summaries DROP COLUMN workflow")
    before = db.read_bytes()
    with pytest.raises(MetricsError):
        loader(db)
    assert db.read_bytes() == before


def test_versioned_usage_replay_counts_once_and_conflict_fails(tmp_path: Path) -> None:
    """@brief Replayed launch usage cannot inflate a terminal summary."""
    store = StateStore(tmp_path / "state")
    store.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="done"))
    usage = {"event_id": "run-1:1", "attempt": 1, "context": "build",
             "executor": "codex", "model": "example", "review_round": 0,
             "tokens_in": 10, "tokens_out": 2, "cost_usd": 0.5,
             "cost_reported": True}
    store.journal("run-1", "usage", **usage)
    store.journal("run-1", "usage", **usage)
    summary = summarize_run(store, "run-1")
    assert (summary.tokens_in, summary.tokens_out, summary.cost_usd) == (10, 2, 0.5)
    store.journal("run-1", "usage", **{**usage, "tokens_in": 11})
    with pytest.raises(MetricsError, match="conflicting"):
        summarize_run(store, "run-1")


@pytest.mark.parametrize("stamp", [None, ""])
def test_usage_event_without_timestamp_is_refused(stamp) -> None:
    """@brief The journal stamps every event, so an undated usage record is older data."""
    event = {"event": "usage", **versioned_usage("run-1", 1, tokens_in=1)}
    if stamp is not None:
        event["ts"] = stamp
    with pytest.raises(MetricsError, match="malformed versioned usage"):
        unique_usage_events([event], "run-1")


def test_record_load_roundtrip_is_duplicate_free(tmp_path: Path) -> None:
    """
    @brief   INSERT OR REPLACE by run_id: re-recording updates, never
             duplicates; the JSONL mirror matches the database.
    """
    db = tmp_path / "m.db"
    mirror = tmp_path / "runs.jsonl"
    record_summary(db, RunSummary(run_id="a", outcome="failed"), mirror)
    record_summary(db, RunSummary(run_id="a", outcome="merged"), mirror)
    record_summary(db, RunSummary(run_id="b", outcome="merged"), mirror)
    rows = load_summaries(db)
    assert len(rows) == 2
    assert {r.run_id: r.outcome for r in rows} == {"a": "merged", "b": "merged"}
    assert len(mirror.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_metrics_database_of_another_build_is_refused_untouched(tmp_path: Path) -> None:
    """
    @brief   No migration: a summary table with other columns stops recording and
             names the file to delete.
    """
    db = tmp_path / "metrics.db"
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE run_summaries (run_id TEXT PRIMARY KEY, outcome TEXT)")
        connection.execute("INSERT INTO run_summaries VALUES ('old', 'merged')")
    before = db.read_bytes()

    with pytest.raises(MetricsError, match="written by another ADORE build") as refused:
        record_summary(db, RunSummary(run_id="new"))

    assert str(db) in str(refused.value)
    assert db.read_bytes() == before


def test_since_window_filters_by_ended_at(tmp_path: Path) -> None:
    """
    @brief   --since keeps only runs ending inside the window; unparseable
             ended_at rows are excluded rather than guessed.
    """
    from datetime import UTC, datetime, timedelta

    db = tmp_path / "m.db"
    recent = (datetime.now(UTC) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    record_summary(db, RunSummary(run_id="old", ended_at="2020-01-01T00:00:00Z"))
    record_summary(db, RunSummary(run_id="new", ended_at=recent))
    record_summary(db, RunSummary(run_id="bad", ended_at="garbage"))
    kept = load_summaries(db, since_seconds=86400)
    assert [s.run_id for s in kept] == ["new"]
    assert len(load_summaries(db)) == 3  # no filter keeps all


def test_aggregate_groups_and_totals(tmp_path: Path) -> None:
    """
    @brief   Grouping by priority yields per-group counts and totals.
    """
    rows = [
        RunSummary(run_id="1", priority="P1", outcome="merged",
                   lifecycle="done", span_seconds=100, tokens_in=10,
                   executor_launches=5, cost_usd=0.5),
        RunSummary(run_id="2", priority="P1", outcome="answer-timeout",
                   lifecycle="failed", span_seconds=300),
        RunSummary(run_id="3", priority="P2", outcome="merged",
                   lifecycle="done", span_seconds=200),
    ]
    groups = aggregate(rows, by="priority")
    assert groups["P1"]["runs"] == 2
    assert groups["P1"]["merged"] == 1 and groups["P1"]["failed"] == 1
    assert groups["P1"]["avg_span_s"] == 200
    assert groups["P1"]["cost_usd"] == 0.5
    assert groups["P2"]["runs"] == 1
    assert aggregate(rows)["all"]["runs"] == 3


def test_csv_and_html_outputs(tmp_path: Path) -> None:
    """
    @brief   CSV carries a header + one line per run; the HTML file is
             self-contained and escapes content.
    """
    rows = [RunSummary(run_id="r<1>", title='He said "hi" & left',
                       outcome="merged")]
    csv_text = export_csv(rows)
    assert csv_text.splitlines()[0].startswith("run_id,")
    assert len(csv_text.strip().splitlines()) == 2
    out = render_html(rows, tmp_path / "stats.html")
    document = out.read_text(encoding="utf-8")
    assert "<script" not in document
    assert "r&lt;1&gt;" in document
    assert "&quot;hi&quot;" in document


def test_profile_stats_empty_and_seeded(tmp_path: Path) -> None:
    """
    @brief   profile_stats yields zeros for a missing DB and headline figures
             (runs/merged/failed/success_rate/last_run) for a seeded one.
    """
    db = tmp_path / "metrics.db"
    empty = profile_stats(db)
    assert empty["runs"] == 0 and empty["merged"] == 0
    assert empty["success_rate"] == 0.0 and empty["last_run"] == ""

    record_summary(db, RunSummary(run_id="1", outcome="merged", lifecycle="done",
                                  span_seconds=100, tokens_in=10, executor_launches=5,
                                  ended_at="2026-07-01T00:00:00Z"))
    record_summary(db, RunSummary(run_id="2", outcome="failed", lifecycle="failed",
                                  span_seconds=300, ended_at="2026-07-02T00:00:00Z"))
    stats = profile_stats(db)
    assert stats["runs"] == 2 and stats["merged"] == 1 and stats["failed"] == 1
    assert stats["success_rate"] == 50.0
    assert stats["avg_span_s"] == 200 and stats["launches"] == 5
    assert stats["last_run"] == "2026-07-02T00:00:00Z"   # newest by ended_at


def test_is_terminal_classification() -> None:
    """
    @brief   Only true end states are recordable.
    """
    for lifecycle in ("done", "failed", "cancelled"):
        assert is_terminal(lifecycle)
    for lifecycle in (
        "working", "parked", "in-review", "validated", "stale",
        "ticket-closed", "deleted",
    ):
        assert not is_terminal(lifecycle)


# END OF FILE
