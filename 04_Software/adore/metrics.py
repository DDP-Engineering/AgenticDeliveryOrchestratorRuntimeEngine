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
@file metrics.py
@brief Statistics capture and query for ADORE (design 13; stdlib only).
@details The per-run journal.jsonl stays the append-only raw truth; at each
         run's terminal state a flat RunSummary is computed from journal +
         state + ticket and upserted into a SQLite database, mirrored to a
         JSONL export. Access is CLI-first (stats/report/export) plus an
         optional self-contained static HTML file - no server, no exporter.
         This data is the crawl -> walk -> run promotion signal. The final
         The final AEGIS strict-check outcome (`ok` or `failed`) remains a
         separate column from the ADORE lifecycle outcome.
"""

from __future__ import annotations

# IMPORTS
import csv
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime, timedelta
import html
import io
import json
import math
from pathlib import Path
import sqlite3
from typing import Any

from adore.branding import PRODUCT_ACRONYM
from adore.state import StateStore
from adore.util import iso_to_datetime

# CONSTANTS

_TABLE = "run_summaries"
VALIDATION_EVENTS = frozenset({"strict-verification", "validation-accepted"})


class MetricsError(ValueError):
    """@brief Persisted metrics evidence violates its versioned contract."""

# DATA MODELS / TYPEDEFINITIONS


@dataclass
class RunSummary:
    """
    @brief   One run's flat metrics record (a SQLite row / JSONL line).
    """

    run_id: str
    ticket_iid: int = 0
    workflow: str = "aegis"
    title: str = ""
    priority: str = ""
    lifecycle: str = ""
    outcome: str = ""
    governance_outcome: str = ""
    started_at: str = ""
    ended_at: str = ""
    span_seconds: int = 0
    parked_wait_seconds: int = 0
    time_to_mr_seconds: int = 0
    gates_passed: int = 0
    gate_failures: int = 0
    invariant_failures: int = 0
    executor_launches: int = 0
    clarification_rounds: int = 0
    review_rounds: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    files_changed: int = 0
    mr_url: str = ""

    def __post_init__(self) -> None:
        """
        @brief Refuse unknown workflow identities at summary construction and load.
        @exception MetricsError For any value other than aegis or direct.
        """
        if not isinstance(self.workflow, str) or self.workflow not in {"aegis", "direct"}:
            raise MetricsError("metrics summary carries unknown workflow")


# HELPER FUNCTIONS


def _seconds_between(start: str, end: str) -> int:
    """
    @brief      Whole seconds between two ISO timestamps (0 on parse gaps).
    @param[in]  start Earlier timestamp.
    @param[in]  end Later timestamp.
    @return     Non-negative seconds.
    """
    a = iso_to_datetime(start)
    b = iso_to_datetime(end)
    if not a or not b:
        return 0
    return max(0, int((b - a).total_seconds()))


def _connect(db_path: str | Path) -> sqlite3.Connection:
    """
    @brief      Open (creating on demand) the metrics database.
    @details    There are no migrations while ADORE is in development: a table
                whose columns differ from RunSummary is refused, not extended.
    @param[in]  db_path SQLite file path.
    @return     Connection with the schema ensured.
    @exception  MetricsError When the database was written by another build.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    columns = ", ".join(
        f"{f.name} {'REAL' if f.type == 'float' else 'INTEGER' if f.type == 'int' else 'TEXT'}"
        + (" PRIMARY KEY" if f.name == "run_id" else "")
        for f in fields(RunSummary)
    )
    connection.execute(f"CREATE TABLE IF NOT EXISTS {_TABLE} ({columns})")
    existing = {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({_TABLE})").fetchall()
    }
    if existing != {item.name for item in fields(RunSummary)}:
        connection.close()
        raise MetricsError(
            f"metrics database {path} was written by another ADORE build; "
            "delete it to start fresh"
        )
    return connection


# PUBLIC API


def validate_usage_observation(event: dict, run_id: str) -> tuple:
    """
    @brief Validate one versioned launch coverage record for replay.
    @param[in] event Persisted usage-observation journal object.
    @param[in] run_id Owning run identity.
    @return Stable replay identity and validated usage/coverage fields.
    @exception MetricsError On malformed or non-UTC evidence.
    """
    attempt = event.get("attempt")
    token_status = event.get("token_status")
    cost_status = event.get("cost_status")
    incoming = event.get("tokens_in")
    outgoing = event.get("tokens_out")
    money = event.get("cost_usd")
    cache_read = event.get("cache_read_tokens")
    cache_write = event.get("cache_write_tokens")
    includes_cache = event.get("input_includes_cache")
    stamp = event.get("ts")
    try:
        observed_at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise MetricsError("malformed usage observation timestamp") from exc
    if observed_at.utcoffset() != timedelta(0):
        raise MetricsError("non-UTC usage observation timestamp")
    if (type(event.get("schema")) is not int or event["schema"] != 1
            or type(attempt) is not int or attempt < 1
            or event.get("event_id") != f"{run_id}:{attempt}"
            or type(event.get("stage")) is not str
            or not 0 < len(event["stage"]) <= 80
            or type(event.get("review_round")) is not int
            or event["review_round"] < 0
            or type(event.get("executor")) is not str
            or not 0 < len(event["executor"]) <= 200
            or (event.get("model") is not None and (
                type(event["model"]) is not str or len(event["model"]) > 200))
            or token_status not in ("reported", "unavailable", "disabled")
            or cost_status not in ("reported", "unavailable", "disabled")
            or (token_status == "disabled") != (cost_status == "disabled")):
        raise MetricsError("malformed usage observation")
    if token_status == "reported":
        if (type(incoming) is not int or incoming < 0
                or type(outgoing) is not int or outgoing < 0):
            raise MetricsError("malformed usage observation")
    elif incoming is not None or outgoing is not None:
        raise MetricsError("malformed usage observation")
    if ((cache_read is not None and
         (type(cache_read) is not int or cache_read < 0))
            or (cache_write is not None and
                (type(cache_write) is not int or cache_write < 0))
            or (includes_cache is not None and type(includes_cache) is not bool)
            or ((cache_read is not None or cache_write is not None)
                and (token_status != "reported" or includes_cache is not True))):
        raise MetricsError("malformed usage observation")
    if cost_status == "reported":
        if (type(money) not in (int, float) or money < 0
                or not math.isfinite(money)):
            raise MetricsError("malformed usage observation")
    elif money is not None:
        raise MetricsError("malformed usage observation")
    return (event["event_id"], attempt, event["stage"], event["review_round"],
            event["executor"], event.get("model"), token_status, cost_status,
            incoming, outgoing, money, cache_read, cache_write, includes_cache)


def unique_usage_events(events: list[dict], run_id: str) -> list[dict]:
    """@brief Keep one numeric usage event per versioned launch identity.

    @param[in] events Run journal records in persisted order.
    @param[in] run_id Run owning those records.
    @return Journal records with identical versioned usage replays removed.
    @exception MetricsError Malformed or conflicting versioned evidence.
    """
    seen: dict[str, tuple] = {}
    result: list[dict] = []
    for event in events:
        if not isinstance(event, dict):
            raise MetricsError("non-object journal record")
        if event.get("event") != "usage":
            result.append(event)
            continue
        if "event_id" not in event:
            raise MetricsError("usage event without an event ID")
        attempt = event.get("attempt")
        incoming = event.get("tokens_in")
        outgoing = event.get("tokens_out")
        money = event.get("cost_usd")
        context = event.get("context")
        executor = event.get("executor")
        model = event.get("model")
        review_round = event.get("review_round")
        reported = event.get("cost_reported")
        cache_read = event.get("cache_read_tokens")
        cache_write = event.get("cache_write_tokens")
        includes_cache = event.get("input_includes_cache")
        if (type(attempt) is not int or attempt < 1
                or event.get("event_id") != f"{run_id}:{attempt}"
                or type(event.get("ts")) is not str or not event["ts"]
                or type(context) is not str or not 0 < len(context) <= 80
                or type(executor) is not str or not 0 < len(executor) <= 200
                or (model is not None and (type(model) is not str or len(model) > 200))
                or type(review_round) is not int or review_round < 0
                or type(incoming) is not int or incoming < 0
                or type(outgoing) is not int or outgoing < 0
                or type(money) not in (int, float) or money < 0
                or not math.isfinite(money) or type(reported) is not bool):
            raise MetricsError("malformed versioned usage")
        if ((cache_read is not None and
             (type(cache_read) is not int or cache_read < 0))
                or (cache_write is not None and
                    (type(cache_write) is not int or cache_write < 0))
                or (includes_cache is not None and type(includes_cache) is not bool)
                or ((cache_read is not None or cache_write is not None)
                    and includes_cache is not True)):
            raise MetricsError("malformed versioned cache usage")
        identity = event["event_id"]
        value = (context, executor, model, review_round, incoming,
                 outgoing, money, reported, cache_read, cache_write,
                 includes_cache)
        if identity in seen:
            if seen[identity] != value:
                raise MetricsError("conflicting versioned usage")
            continue
        seen[identity] = value
        result.append(event)
    return result


def summarize_run(store: StateStore, run_id: str,
                  files_changed: int = 0) -> RunSummary:
    """
    @brief      Compute a run's summary from its journal, state, and ticket.
    @details    The journal is the source of truth: AEGIS stage outcomes,
                usage events (tokens/cost per launch), park/resume gaps, and
                the time to the MR all come from its timestamps. Malformed
                usage fails closed.
    @param[in]  store The state store holding the run.
    @param[in]  run_id Stable run identifier.
    @param[in]  files_changed Files-touched count when the caller still has a
                              worktree to measure (0 otherwise).
    @return     The RunSummary.
    """
    state = store.load(run_id)
    events = unique_usage_events(store.read_journal(run_id), run_id)
    try:
        ticket = store.load_ticket(run_id)
    except Exception:  # noqa: BLE001 - missing snapshot is fine
        ticket = {}

    summary = RunSummary(
        run_id=run_id,
        ticket_iid=state.ticket_iid,
        workflow=state.workflow,
        title=str(ticket.get("title", ""))[:120],
        lifecycle=state.lifecycle,
        outcome=state.outcome or state.lifecycle,
        clarification_rounds=state.clarification_rounds,
        review_rounds=state.review_rounds,
        mr_url=state.mr_url,
        files_changed=files_changed,
    )
    labels = ticket.get("labels") or []
    summary.priority = next(
        (label for label in labels if len(label) == 2 and label.upper().startswith("P")),
        "",
    )
    if events:
        summary.started_at = events[0].get("ts", "")
        summary.ended_at = events[-1].get("ts", "")
        summary.span_seconds = _seconds_between(summary.started_at,
                                                summary.ended_at)
    parked_since = ""
    for event in events:
        name = event.get("event", "")
        ts = event.get("ts", "")
        if name == "stage-launch":
            summary.executor_launches += 1
        elif name == "stage-advanced":
            summary.gates_passed += 1
        elif name == "stage-failed":
            summary.gate_failures += 1
        elif name in VALIDATION_EVENTS:
            passed = event.get("passed") is True
            summary.governance_outcome = "ok" if passed else "failed"
            if not passed:
                summary.invariant_failures += 1
        elif name == "usage":
            summary.tokens_in += int(event.get("tokens_in", 0) or 0)
            summary.tokens_out += int(event.get("tokens_out", 0) or 0)
            summary.cost_usd += float(event.get("cost_usd", 0) or 0)
        elif name == "parked":
            parked_since = ts
        elif name == "resumed" and parked_since:
            summary.parked_wait_seconds += _seconds_between(parked_since, ts)
            parked_since = ""
        elif name == "mr-opened" and not summary.time_to_mr_seconds:
            summary.time_to_mr_seconds = _seconds_between(summary.started_at, ts)
    summary.cost_usd = round(summary.cost_usd, 4)
    return summary


def record_summary(db_path: str | Path, summary: RunSummary,
                   export_jsonl: str | Path = "") -> None:
    """
    @brief      Upsert a run summary into SQLite and refresh the JSONL mirror.
    @details    INSERT OR REPLACE keyed by run_id: re-recording a run (retry
                after failure, rebuild) never duplicates rows. The mirror is
                rewritten from the database so it always matches.
    @param[in]  db_path SQLite database path.
    @param[in]  summary The summary to persist.
    @param[in]  export_jsonl Mirror path ("" = no mirror).
    """
    names = [f.name for f in fields(RunSummary)]
    with _connect(db_path) as connection:
        connection.execute(
            f"INSERT OR REPLACE INTO {_TABLE} ({', '.join(names)}) "
            f"VALUES ({', '.join('?' * len(names))})",
            [getattr(summary, name) for name in names],
        )
    if export_jsonl:
        mirror = Path(export_jsonl)
        mirror.parent.mkdir(parents=True, exist_ok=True)
        rows = load_summaries(db_path)
        with mirror.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def delete_summary(db_path: str | Path, run_id: str, export_jsonl: str = "") -> None:
    """@brief Remove a deleted job's terminal projection before its identity is reused.
    @param[in] db_path Current metrics store; absent files remain absent.
    @param[in] run_id Exactly the verified deleted job.
    @param[in] export_jsonl Optional current summary mirror.
    @exception MetricsError Unsupported store schema.
    """
    if not db_path or not Path(db_path).exists():
        return
    with _connect(db_path) as connection:
        connection.execute(f"DELETE FROM {_TABLE} WHERE run_id=?", (run_id,))
    if export_jsonl:
        mirror = Path(export_jsonl)
        mirror.parent.mkdir(parents=True, exist_ok=True)
        with mirror.open("w", encoding="utf-8") as handle:
            for row in load_summaries(db_path):
                handle.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def load_summaries(db_path: str | Path,
                   since_seconds: int | None = None) -> list[RunSummary]:
    """
    @brief      Load summaries, optionally only runs ending in a window.
    @param[in]  db_path SQLite database path.
    @param[in]  since_seconds Keep runs whose ended_at is within this many
                              seconds of now (None = all).
    @return     Summaries ordered by ended_at.
    """
    if not Path(db_path).is_file():
        return []
    names = [f.name for f in fields(RunSummary)]
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT {', '.join(names)} FROM {_TABLE} ORDER BY ended_at"
        ).fetchall()
    summaries = [RunSummary(**dict(zip(names, row, strict=True))) for row in rows]
    if since_seconds is not None:
        cutoff = datetime.now(UTC) - timedelta(seconds=since_seconds)
        summaries = [
            s for s in summaries
            if (ended := iso_to_datetime(s.ended_at)) and ended >= cutoff
        ]
    return summaries


def load_analytical_summaries(db_path: str | Path) -> list[RunSummary]:
    """
    @brief Read summary evidence without creating or extending its database.
    @param[in] db_path Existing metrics database; absence is an empty source.
    @return Validated summaries.
    @exception MetricsError Corrupt, unsupported or unreadable summary source.
    """
    path = Path(db_path)
    if not path.exists():
        return []
    try:
        if path.is_symlink() or not path.is_file():
            raise MetricsError("invalid metrics source")
        with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
            names = [str(row[1]) for row in connection.execute(
                f"PRAGMA table_info({_TABLE})").fetchall()]
            fields_by_name = {f.name: f for f in fields(RunSummary)}
            if set(names) != fields_by_name.keys():
                raise MetricsError("unsupported metrics table")
            rows = connection.execute(f"SELECT {', '.join(names)} FROM {_TABLE}").fetchall()
        result = []
        for row in rows:
            values = dict(zip(names, row, strict=True))
            for name, value in values.items():
                kind = fields_by_name[name].type
                valid = (type(value) is str if kind == "str" else
                         type(value) is int and value >= 0 if kind == "int" else
                         type(value) in (int, float) and math.isfinite(value) and value >= 0)
                if not valid:
                    raise MetricsError("malformed metrics row")
            if not values["run_id"]:
                raise MetricsError("missing metrics identity")
            result.append(RunSummary(**values))
        if len({r.run_id for r in result}) != len(result):
            raise MetricsError("duplicate metrics identity")
        return result
    except (OSError, sqlite3.DatabaseError, TypeError, ValueError) as exc:
        raise MetricsError("corrupt metrics source") from exc


def aggregate(summaries: list[RunSummary],
              by: str = "") -> dict[str, dict[str, Any]]:
    """
    @brief      Aggregate summaries, optionally grouped by a field.
    @param[in]  summaries Loaded summaries.
    @param[in]  by Group field ("priority" / "outcome" / "" = one group).
    @return     Group -> {runs, merged, failed, avg_span_s, tokens_in,
                tokens_out, cost_usd, launches}.
    """
    groups: dict[str, list[RunSummary]] = {}
    for summary in summaries:
        key = str(getattr(summary, by, "") or "(none)") if by else "all"
        groups.setdefault(key, []).append(summary)
    result: dict[str, dict[str, Any]] = {}
    for key, members in sorted(groups.items()):
        spans = [m.span_seconds for m in members if m.span_seconds]
        result[key] = {
            "runs": len(members),
            "merged": sum(1 for m in members if m.outcome.startswith("merged")),
            "failed": sum(1 for m in members if m.lifecycle == "failed"),
            "avg_span_s": int(sum(spans) / len(spans)) if spans else 0,
            "launches": sum(m.executor_launches for m in members),
            "tokens_in": sum(m.tokens_in for m in members),
            "tokens_out": sum(m.tokens_out for m in members),
            "cost_usd": round(sum(m.cost_usd for m in members), 4),
        }
    return result


def profile_stats(db_path: str | Path) -> dict[str, Any]:
    """
    @brief      One project's headline run statistics from its metrics DB.
    @details    Reuses aggregate() over all summaries; a missing/empty database
                yields zeros (never an error), so a freshly-created profile
                renders cleanly. success_rate is merged/runs as a percentage.
    @param[in]  db_path SQLite database path (may not exist yet).
    @return     {runs, merged, failed, success_rate, avg_span_s, launches,
                tokens_in, tokens_out, cost_usd, last_run}.
    """
    summaries = load_summaries(db_path) if db_path else []
    row = aggregate(summaries).get("all", {})
    runs = row.get("runs", 0)
    merged = row.get("merged", 0)
    return {
        "runs": runs,
        "merged": merged,
        "failed": row.get("failed", 0),
        "success_rate": round(100.0 * merged / runs, 1) if runs else 0.0,
        "avg_span_s": row.get("avg_span_s", 0),
        "launches": row.get("launches", 0),
        "tokens_in": row.get("tokens_in", 0),
        "tokens_out": row.get("tokens_out", 0),
        "cost_usd": row.get("cost_usd", 0.0),
        "last_run": summaries[-1].ended_at if summaries else "",
    }


def export_csv(summaries: list[RunSummary]) -> str:
    """
    @brief      Render summaries as CSV text (`adore export --csv`).
    @param[in]  summaries Loaded summaries.
    @return     CSV text including the header row.
    """
    names = [f.name for f in fields(RunSummary)]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=names, lineterminator="\n")
    writer.writeheader()
    for summary in summaries:
        writer.writerow(asdict(summary))
    return buffer.getvalue()


def render_html(summaries: list[RunSummary], out_path: str | Path) -> Path:
    """
    @brief      Write the self-contained static dashboard (`stats --html`).
    @details    Stdlib only, no scripts, no server: aggregates on top, one
                table row per run. Open the file directly in a browser.
    @param[in]  summaries Loaded summaries.
    @param[in]  out_path Output HTML path.
    @return     The written path.
    """
    totals = aggregate(summaries).get("all", {})
    head_cells = "".join(
        f"<th>{html.escape(f.name)}</th>" for f in fields(RunSummary)
    )
    body_rows = "".join(
        "<tr>" + "".join(
            f"<td>{html.escape(str(getattr(s, f.name)))}</td>"
            for f in fields(RunSummary)
        ) + "</tr>"
        for s in summaries
    )
    totals_text = html.escape(json.dumps(totals))
    document = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{PRODUCT_ACRONYM} statistics</title><style>"
        "body{font-family:sans-serif;margin:2em}"
        "table{border-collapse:collapse;font-size:0.85em}"
        "th,td{border:1px solid #ccc;padding:4px 8px;text-align:left}"
        "th{background:#eee}</style></head><body>"
        f"<h1>{PRODUCT_ACRONYM} statistics</h1><p>Generated "
        f"{datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} - "
        f"{len(summaries)} run(s)</p>"
        f"<p><code>{totals_text}</code></p>"
        f"<table><thead><tr>{head_cells}</tr></thead>"
        f"<tbody>{body_rows}</tbody></table></body></html>"
    )
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return path


def is_terminal(lifecycle: str) -> bool:
    """
    @brief      Whether a run lifecycle is a terminal (recordable) state.
    @param[in]  lifecycle Run lifecycle value.
    @return     True for actual runtime terminal lifecycles.
    """
    return lifecycle in ("done", "failed", "cancelled", "handed-off")


# END OF FILE
