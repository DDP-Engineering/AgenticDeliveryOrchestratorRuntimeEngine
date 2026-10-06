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
@file    analytics.py
@brief   Shared strict sources, instant scope and measured web consumption.
@details Reads preserve operational schema and recovery behavior. Legacy absent
         date attribution is explicit; malformed versioned evidence fails closed.
"""

# IMPORTS
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
import json
import math
import re
from statistics import median
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from adore import metrics
from adore.state import RunState, StateError, StateStore

# CONSTANTS
TERMINAL = {
    "done": {"done"},
    "failed": {"failed", "immediate-failure", "stage-failed", "notification-blocked"},
    "cancelled": {"cancelled"},
    "handed-off": {"handed-off"},
}
AMOUNTS = ("tokens_in", "tokens_out", "cache_read_tokens", "cache_write_tokens")
MONEY = ("reported_cost_usd", "estimated_cost_usd")


# DATA MODELS / TYPEDEFINITIONS
class AnalyticsError(ValueError):
    """@brief Safe typed analytical failure without raw persisted values."""

    def __init__(self, code: str, status: int = 503):
        """@brief Retain public error code and HTTP status."""
        super().__init__(code)
        self.code, self.status = code, status


@dataclass(frozen=True)
class Scope:
    """@brief One half-open instant scope derived from inclusive local dates."""

    zone: ZoneInfo
    granularity: str
    start: datetime | None
    end: datetime | None

    @classmethod
    def create(cls, day_from: date | None, day_to: date | None, timezone: str, granularity: str):
        """
        @brief Resolve local midnights independently across offset changes.
        @param[in] day_from Inclusive local first date or unbounded.
        @param[in] day_to Inclusive local last date or unbounded.
        @param[in] timezone IANA timezone name.
        @param[in] granularity Day, Monday-week or month.
        @return Validated instant scope.
        @exception AnalyticsError Invalid range, timezone or grouping.
        """
        if day_from and day_to and day_from > day_to:
            raise AnalyticsError("invalid_date_range", 422)
        if (
            not isinstance(timezone, str)
            or len(timezone) > 64
            or not re.fullmatch(r"[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*", timezone)
        ):
            raise AnalyticsError("invalid_reporting_timezone", 422)
        try:
            zone = ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise AnalyticsError("invalid_reporting_timezone", 422) from exc
        if granularity not in ("day", "week", "month"):
            raise AnalyticsError("invalid_granularity", 422)
        try:
            start = datetime.combine(day_from, time(), zone).astimezone(UTC) if day_from else None
            end = (
                datetime.combine(day_to + timedelta(days=1), time(), zone).astimezone(UTC)
                if day_to
                else None
            )
        except (ValueError, OverflowError) as exc:
            raise AnalyticsError("invalid_date_range", 422) from exc
        return cls(zone, granularity, start, end)

    def includes(self, stamp: datetime | None) -> bool:
        """@brief Match only observed instants, including the lower endpoint."""
        return (
            stamp is not None
            and (self.start is None or stamp >= self.start)
            and (self.end is None or stamp < self.end)
        )

    def local_day(self, stamp: datetime) -> date:
        """
        @brief Resolve observed dates with typed local-calendar overflow handling.
        @param[in] stamp Validated aware UTC instant.
        @return Its actual local calendar date, independently of grouping.
        @exception AnalyticsError Instant is outside the local calendar range.
        """
        try:
            return stamp.astimezone(self.zone).date()
        except (ValueError, OverflowError) as exc:
            raise AnalyticsError("metrics_corrupt") from exc

    def bucket(self, stamp: datetime) -> str:
        """@brief Group an observed instant by local day, Monday-week or month."""
        day = self.local_day(stamp)
        if self.granularity == "week":
            day -= timedelta(days=day.weekday())
        elif self.granularity == "month":
            day = day.replace(day=1)
        return day.isoformat()

    def public(self, project_id: str) -> dict:
        """@brief Describe the immutable project and canonical interval."""
        return {
            "project_ids": [project_id],
            "mode": "all_time" if not self.start and not self.end else "interval",
            "interval": "[from,to)",
            "from": self.start.isoformat() if self.start else None,
            "to": self.end.isoformat() if self.end else None,
            "timezone": self.zone.key,
            "granularity": self.granularity,
            "interval_seconds": int((self.end - self.start).total_seconds())
            if self.start and self.end
            else None,
        }


# LOCAL HELPERS
def instant(value: object) -> datetime | None:
    """
    @brief Return an aware observed instant; unparseable legacy date is unallocated.
    @param[in] value Saved timestamp or missing value.
    @return UTC instant or None; date-only and naive values have no instant.
    """
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise AnalyticsError("metrics_corrupt")
    try:
        stamp = datetime.fromisoformat(value)
        return stamp.astimezone(UTC) if stamp.utcoffset() is not None else None
    except (ValueError, OverflowError):
        return None


def _object(raw: bytes, code: str) -> dict:
    """
    @brief Decode strict objects, rejecting duplicate keys and nonfinite JSON.
    @param[in] raw Persisted UTF-8 JSON bytes.
    @param[in] code Safe public failure code.
    @return One unambiguous object.
    @exception AnalyticsError Invalid encoding, object shape or JSON.
    """

    def unique(pairs):
        """@brief Reject ambiguous duplicate persisted keys."""
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError
        return result

    def invalid(_value):
        """@brief Reject nonfinite JSON constants."""
        raise ValueError

    try:
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AnalyticsError(code) from exc


def _validate_event(event: dict) -> None:
    """
    @brief Validate relevant fields before any period or identity filtering.
    @param[in] event Persisted journal object.
    @exception AnalyticsError Unsupported schema or corrupt field evidence.
    """
    if not isinstance(event.get("event"), str) or not event["event"]:
        raise AnalyticsError("metrics_corrupt")
    if "schema" in event and (type(event["schema"]) is not int or event["schema"] != 1):
        raise AnalyticsError("metrics_corrupt")
    if "ts" in event:
        instant(event["ts"])
    if event["event"] == "strict-verification" and type(event.get("passed")) is not bool:
        raise AnalyticsError("metrics_corrupt")
    if event["event"] == "usage" and "event_id" in event and instant(event.get("ts")) is None:
        raise AnalyticsError("usage_corrupt")
    if event["event"] != "usage":
        return
    for field in ("executor", "model"):
        value = event.get(field)
        if value is not None and (
            not isinstance(value, str) or not value.strip() or len(value) > 200 or "\x00" in value
        ):
            raise AnalyticsError("usage_corrupt")
    for field in AMOUNTS:
        value = event.get(field)
        if value is not None and (type(value) is not int or value < 0):
            raise AnalyticsError("usage_corrupt")
    money = event.get("cost_usd")
    try:
        valid_money = money is None or (
            type(money) in (int, float) and money >= 0 and math.isfinite(money)
        )
    except OverflowError:
        valid_money = False
    if not valid_money:
        raise AnalyticsError("usage_corrupt")
    if "cost_reported" in event and type(event["cost_reported"]) is not bool:
        raise AnalyticsError("usage_corrupt")
    if event.get("cost_reported") is True and money is None:
        raise AnalyticsError("usage_corrupt")
    if any(event.get(key) is not None for key in AMOUNTS[2:]) and (
        event.get("input_includes_cache") is not True or event.get("tokens_in") is None
    ):
        raise AnalyticsError("usage_corrupt")


def _historical_sources(sources: list[tuple], summaries: list) -> list[tuple]:
    """
    @brief Include historical summary facts without fabricating runtime state.
    @param[in] sources Actual runtime records and validated journals.
    @param[in] summaries Persisted historical rows.
    @return Actual records plus summary-only records with empty journals.
    """
    identities = {run.run_id for run, _ in sources}
    return [*sources, *((row, []) for row in summaries if row.run_id not in identities)]


# PUBLIC API
def read_sources(store: StateStore) -> list[tuple[RunState, list[dict]]]:
    """
    @brief Read complete state and JSONL without the tolerant operational reader.
    @param[in] store Runtime store to inspect without mutation.
    @return Run and validated journal pairs in stable order.
    @exception AnalyticsError Unsupported schema, corrupt/unreadable or linked source.
    """
    root = store.runs_root
    if not root.exists():
        return []
    result = []
    try:
        if not root.is_dir() or root.is_symlink():
            raise AnalyticsError("run_state_corrupt")
        for entry in sorted(root.iterdir()):
            if (
                not entry.is_dir()
                or entry.is_symlink()
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", entry.name)
            ):
                raise AnalyticsError("run_state_corrupt")
            state_path = entry / "state.json"
            if state_path.is_symlink():
                raise AnalyticsError("run_state_corrupt")
            raw = _object(state_path.read_bytes(), "run_state_corrupt")
            try:
                run = RunState.from_dict(raw)
            except (StateError, TypeError, ValueError) as exc:
                raise AnalyticsError("run_state_corrupt") from exc
            if run.run_id != entry.name:
                raise AnalyticsError("run_state_corrupt")
            path = entry / "journal.jsonl"
            if path.is_symlink():
                raise AnalyticsError("metrics_corrupt")
            try:
                journal = path.read_bytes()
            except FileNotFoundError:
                journal = b""
            events = [
                _object(line, "metrics_corrupt") for line in journal.splitlines() if line.strip()
            ]
            for event in events:
                _validate_event(event)
            try:
                metrics.unique_usage_events(events, run.run_id)
                seen = {}
                usage_stamps = {}
                for event in events:
                    if event["event"] == "usage" and "event_id" in event:
                        key = event["event_id"]
                        if key in usage_stamps and usage_stamps[key] != event.get("ts"):
                            raise metrics.MetricsError("conflicting consumption timestamp")
                        usage_stamps[key] = event.get("ts")
                    if event["event"] == "usage-observation":
                        identity = metrics.validate_usage_observation(event, run.run_id)
                        value = (identity, event.get("ts"))
                        if identity[0] in seen and seen[identity[0]] != value:
                            raise metrics.MetricsError("conflicting coverage replay")
                        seen[identity[0]] = value
            except metrics.MetricsError as exc:
                raise AnalyticsError("metrics_corrupt") from exc
            result.append((run, events))
    except (OSError, UnicodeError) as exc:
        raise AnalyticsError("metrics_corrupt") from exc
    return result


def empty_amounts(admin: bool) -> dict:
    """
    @brief Initialize measured amounts as unavailable, counters as zero.
    @param[in] admin Whether to include authorized financial fields.
    @return Mutable empty measurement projection.
    """
    return {"events": 0, **dict.fromkeys(AMOUNTS + (MONEY if admin else ()))}


def add_amounts(target: dict, source: dict) -> None:
    """
    @brief Sum available measurements, preserving unknown and measured zero.
    @param[in,out] target Nullable accumulated fields.
    @param[in] source Validated measurements and event count.
    @exception AnalyticsError Monetary accumulation is nonfinite.
    """
    for key, value in source.items():
        if key not in target or value is None:
            continue
        combined = (target[key] or 0) + value
        if isinstance(combined, float) and not math.isfinite(combined):
            raise AnalyticsError("usage_corrupt")
        target[key] = combined


def measured(event: dict, prices: list[dict], admin: bool) -> dict:
    """
    @brief Project numeric evidence with UTC-effective reported/estimated money.
    @param[in] event Validated numeric usage event.
    @param[in] prices Immutable ordered project price history.
    @param[in] admin Whether financial fields are authorized.
    @return Nullable measured amounts; no duplicate reported/estimated billing.
    """
    value = {"events": 1, **{key: event.get(key) for key in AMOUNTS}}
    if not admin:
        return value
    value.update(dict.fromkeys(MONEY))
    money = event.get("cost_usd")
    if event.get("cost_reported") is True or (money is not None and money > 0):
        value["reported_cost_usd"] = money
    elif value["tokens_in"] is not None and value["tokens_out"] is not None:
        stamp = instant(event.get("ts"))
        matching = [
            p
            for p in prices
            if stamp is not None
            and p["executor"] == event.get("executor")
            and p["model"] == event.get("model")
            and p["effective_from"] <= stamp.date().isoformat()
        ]
        if matching:
            price = matching[-1]
            value["estimated_cost_usd"] = float(
                (
                    Decimal(value["tokens_in"]) * Decimal(price["input_usd_per_million"])
                    + Decimal(value["tokens_out"]) * Decimal(price["output_usd_per_million"])
                )
                / Decimal(1_000_000)
            )
    if any(value[key] is not None and not math.isfinite(value[key]) for key in MONEY):
        raise AnalyticsError("usage_corrupt")
    return value


def lifecycle_times(run: RunState, events: list[dict], summary=None) -> tuple:
    """
    @brief Select own lifecycle evidence, with recorded summary-only fallback.
    @param[in] run Actual runtime or historical summary identity/lifecycle.
    @param[in] events Strict ordered journal records.
    @param[in] summary Recorded fallback dates when journal events are absent.
    @return Nullable aware start and terminal instants.
    """
    picked = next((e for e in events if e["event"] == "picked"), None)
    terminal = next(
        (
            e
            for e in reversed(events)
            if e["event"] in TERMINAL.get(run.lifecycle, set())
            or (
                run.lifecycle == "failed"
                and e["event"] == "cancelled"
                and e.get("outcome") == "failed"
            )
        ),
        None,
    )
    start = instant(picked.get("ts")) if picked else None
    end = instant(terminal.get("ts")) if terminal else None
    if summary:
        if not picked:
            start = instant(summary.started_at)
        if not terminal and run.lifecycle in TERMINAL:
            end = instant(summary.ended_at)
    return start, end


def usage_report(
    sources: list[tuple],
    project_id: str,
    scope: Scope,
    prices: list[dict],
    admin: bool,
    executor=None,
    model=None,
    summaries: list | None = None,
) -> dict:
    """
    @brief Build one filtered daily/per-job consumption contract.
    @param[in] sources Strict run/event pairs.
    @param[in] project_id Authorized immutable project identity.
    @param[in] scope Validated reporting interval and grouping.
    @param[in] prices Authorized immutable prices.
    @param[in] admin Financial permission.
    @param[in] executor Exact observed executor filter or None.
    @param[in] model Exact observed model filter or None.
    @param[in] summaries Validated legacy summary evidence without dated attribution.
    @return Scoped aggregate, composite jobs, explicit lifetime and unallocated evidence.
    @exception AnalyticsError Invalid filter.
    """
    for key, value in (("executor", executor), ("model", model)):
        if value is not None and (
            not value.strip()
            or value != value.strip()
            or len(value) > 200
            or any(ord(c) < 32 for c in value)
        ):
            raise AnalyticsError(f"invalid_{key}_filter", 422)
    sources = _historical_sources(sources, summaries or [])
    buckets, jobs = {}, []
    totals, lifetime, unallocated = [empty_amounts(admin) for _ in range(3)]
    coverage = {
        "runs_with_usage": 0,
        "usage_events_unallocated": 0,
        "runs_without_usage": 0,
        "usage_events_with_tokens": 0,
        "usage_events_without_tokens": 0,
        "summary_only_runs": 0,
        **{f"usage_events_with_{key}": 0 for key in AMOUNTS},
    }
    summary_by_id = {row.run_id: row for row in summaries or []}
    if admin:
        coverage["usage_events_unpriced"] = 0
    for run, events in sources:
        job_lifetime, job_period, job_unallocated = [empty_amounts(admin) for _ in range(3)]
        for event in metrics.unique_usage_events(events, run.run_id):
            if (
                event["event"] != "usage"
                or (executor is not None and event.get("executor") != executor)
                or (model is not None and event.get("model") != model)
            ):
                continue
            value = measured(event, prices, admin)
            stamp = instant(event.get("ts"))
            add_amounts(job_lifetime, value)
            if stamp is None:
                add_amounts(job_unallocated, value)
            elif scope.includes(stamp):
                add_amounts(job_period, value)
                key = (scope.bucket(stamp), event.get("executor"), event.get("model"))
                row = buckets.setdefault(
                    key,
                    {"date": key[0], "executor": key[1], "model": key[2], **empty_amounts(admin)},
                )
                add_amounts(row, value)
                coverage[
                    "usage_events_with_tokens"
                    if value["tokens_in"] is not None and value["tokens_out"] is not None
                    else "usage_events_without_tokens"
                ] += 1
                for field in AMOUNTS:
                    coverage[f"usage_events_with_{field}"] += value[field] is not None
                if (
                    admin
                    and value["reported_cost_usd"] is None
                    and value["estimated_cost_usd"] is None
                ):
                    coverage["usage_events_unpriced"] += 1
        summary = summary_by_id.get(run.run_id)
        source = "journal" if job_lifetime["events"] else "unavailable"
        if (
            summary
            and not job_lifetime["events"]
            and executor is None
            and model is None
            and (summary.tokens_in or summary.tokens_out)
        ):
            for key in ("tokens_in", "tokens_out"):
                job_lifetime[key] = job_unallocated[key] = getattr(summary, key) or None
            coverage["summary_only_runs"] += 1
            source = "summary"
        start, end = lifecycle_times(run, events, summary)
        selected = (
            (not scope.start and not scope.end)
            or job_period["events"]
            or (scope.includes(start) or scope.includes(end))
        )
        add_amounts(lifetime, job_lifetime)
        add_amounts(unallocated, job_unallocated)
        add_amounts(totals, job_period)
        coverage["usage_events_unallocated"] += job_unallocated["events"]
        if selected:
            coverage["runs_with_usage"] += bool(job_period["events"])
            coverage["runs_without_usage"] += not bool(job_lifetime["events"])
            jobs.append(
                {
                    "project_id": project_id,
                    "run_id": run.run_id,
                    "lifetime": job_lifetime,
                    "in_period": job_period,
                    "unallocated": job_unallocated,
                    "source": source,
                    "coverage": {
                        "lifetime_usage_events": job_lifetime["events"],
                        "period_usage_events": job_period["events"],
                        "unallocated_usage_events": job_unallocated["events"],
                    },
                }
            )
    rows = [buckets[k] for k in sorted(buckets, key=lambda k: (k[0], k[1] or "", k[2] or ""))]
    if admin:
        totals["unpriced_events"] = coverage["usage_events_unpriced"]
    return {
        "scope": scope.public(project_id),
        "daily": rows,
        "totals": totals,
        "lifetime": lifetime,
        "unallocated": unallocated,
        "jobs": jobs,
        "coverage": coverage,
        "timezone": scope.zone.key,
        "granularity": scope.granularity,
    }


def duration_report(summaries: list, scope: Scope) -> dict:
    """
    @brief Select validated terminal elapsed samples on the server.
    @param[in] summaries Read-only persisted terminal summaries.
    @param[in] scope Completion instant cohort.
    @return Count, nullable mean/median, sum and exact sorted pooling samples.
    @exception AnalyticsError Malformed or inconsistent observed span.
    """
    spans = []
    for row in summaries:
        if row.lifecycle not in TERMINAL:
            continue
        if type(row.span_seconds) is not int or row.span_seconds < 0:
            raise AnalyticsError("metrics_corrupt")
        if not row.started_at and not row.ended_at and row.span_seconds == 0:
            continue
        start, end = instant(row.started_at), instant(row.ended_at)
        if (
            start is None
            or end is None
            or end < start
            or int((end - start).total_seconds()) != row.span_seconds
        ):
            raise AnalyticsError("metrics_corrupt")
        if scope.includes(end):
            spans.append(row.span_seconds)
    spans.sort()
    return {
        "sampled_runs": len(spans),
        "avg_span_seconds": math.floor(sum(spans) / len(spans) + 0.5) if spans else None,
        "median_span_seconds": median(spans) if spans else None,
        "sum_span_seconds": sum(spans),
        "samples_seconds": spans,
        "basis": "terminal_summary_end_in_scope_including_wait",
    }


def metric_report(
    sources: list[tuple],
    summaries: list,
    project_id: str,
    scope: Scope,
    prices: list[dict],
    admin: bool,
) -> dict:
    """
    @brief Derive compatible metric consumers from one scoped consumption view.
    @param[in] sources Strict run/journal pairs.
    @param[in] summaries Read-only summary evidence.
    @param[in] project_id Authorized immutable project.
    @param[in] scope Validated reporting scope.
    @param[in] prices Authorized UTC-effective price history.
    @param[in] admin Financial permission.
    @return Scoped totals, daily lifecycle/usage, cohorts, samples and current stock.
    """
    from dataclasses import asdict

    usage = usage_report(sources, project_id, scope, prices, admin, summaries=summaries)
    summary_by_id = {s.run_id: s for s in summaries}
    if len(summary_by_id) != len(summaries):
        raise AnalyticsError("metrics_corrupt")
    current_ids = {run.run_id for run, _ in sources}
    sources = _historical_sources(sources, summaries)
    days, rows, revisions = {}, [], []
    selected_ids = {j["run_id"] for j in usage["jobs"]}
    period_jobs = {j["run_id"]: j for j in usage["jobs"]}
    counters = dict.fromkeys(
        ("started", "completed", "failed", "merged", "mr_revisions", "pipeline_repairs"), 0
    )
    coverage = {
        **usage["coverage"],
        "lifecycle_started_unallocated": 0,
        "lifecycle_completed_unallocated": 0,
        "revision_events_unclassified": 0,
        "launches_with_reported_tokens": 0,
        "launches_with_unavailable_tokens": 0,
        "launches_capture_disabled": 0,
    }
    stock = {
        "active_now": 0,
        "waiting_now": 0,
        "review_now": 0,
        "terminal_now": 0,
        "jobs_now": len(current_ids),
        "basis": "current_state",
    }
    quality = dict.fromkeys(
        (
            "reviewed_jobs",
            "reworked_jobs",
            "open_review_jobs",
            "validated_jobs",
            "first_pass_validations",
            "human_merged_jobs",
            "first_pass_merges",
            "stage_failures",
            "operator_retries",
        ),
        0,
    )
    efficiency = {
        k: []
        for k in (
            "reported_per_completed",
            "estimated_per_completed",
            "reported_per_human_merged",
            "estimated_per_human_merged",
        )
    }
    if admin:
        coverage.update(
            dict.fromkeys(
                (
                    "launches_with_reported_cost",
                    "launches_with_unavailable_cost",
                    "runs_with_reported_cost",
                    "runs_with_estimated_cost",
                ),
                0,
            )
        )

    def bucket(stamp):
        """@brief Initialize one consistently nullable grouped metric row."""
        key = scope.bucket(stamp)
        return days.setdefault(
            key,
            {
                "date": key,
                **dict.fromkeys(counters, 0),
                "tokens_in": None,
                "tokens_out": None,
                **({"cost_usd": None, "estimated_cost_usd": None} if admin else {}),
            },
        )

    for row in usage["daily"]:
        # Usage already selected exact instants; period keys need no second date filter.
        key = row["date"]
        target = days.setdefault(
            key,
            {
                "date": key,
                **dict.fromkeys(counters, 0),
                "tokens_in": None,
                "tokens_out": None,
                **({"cost_usd": None, "estimated_cost_usd": None} if admin else {}),
            },
        )
        add_amounts(
            target,
            {
                "tokens_in": row["tokens_in"],
                "tokens_out": row["tokens_out"],
                **(
                    {
                        "cost_usd": row["reported_cost_usd"],
                        "estimated_cost_usd": row["estimated_cost_usd"],
                    }
                    if admin
                    else {}
                ),
            },
        )
    all_jobs = {
        j["run_id"]: j
        for j in usage_report(
            sources,
            project_id,
            Scope.create(None, None, scope.zone.key, scope.granularity),
            prices,
            admin,
            summaries=summaries,
        )["jobs"]
    }
    for run, events in sources:
        summary = summary_by_id.get(run.run_id)
        start, end = lifecycle_times(run, events, summary)
        if run.run_id in current_ids:
            stock["active_now"] += run.lifecycle in ("working", "publishing")
            stock["review_now"] += run.lifecycle == "in-review"
            stock["terminal_now"] += run.lifecycle in TERMINAL or run.lifecycle == "stale"
            stock["waiting_now"] += run.lifecycle in (
                "parked-clarification",
                "awaiting-approval",
                "handoff-pending",
            )
        coverage["lifecycle_started_unallocated"] += start is None
        coverage["lifecycle_completed_unallocated"] += run.lifecycle in TERMINAL and end is None
        for name, stamp in (("started", start), ("completed", end)):
            if scope.includes(stamp):
                selected_ids.add(run.run_id)
                bucket(stamp)[name] += 1
                counters[name] += 1
        if run.lifecycle == "failed" and scope.includes(end):
            bucket(end)["failed"] += 1
            counters["failed"] += 1
        if run.lifecycle == "done" and run.outcome.startswith("merged") and scope.includes(end):
            bucket(end)["merged"] += 1
            counters["merged"] += 1
        first_review = next((e for e in events if e["event"] in ("mr-opened", "mr-adopted")), None)
        first_check = next((e for e in events if e["event"] == "strict-verification"), None)
        reworked = any(
            e["event"] == "revision-started" and e.get("trigger") == "revise-label" for e in events
        )
        if first_review and run.lifecycle not in TERMINAL:
            quality["open_review_jobs"] += 1  # Named current stock compatibility alias.
        if first_review and scope.includes(instant(first_review.get("ts"))):
            quality["reviewed_jobs"] += 1
            quality["reworked_jobs"] += reworked
        if first_check and scope.includes(instant(first_check.get("ts"))):
            quality["validated_jobs"] += 1
            quality["first_pass_validations"] += first_check["passed"]
        human_merge = bool(
            first_review
            and run.lifecycle == "done"
            and run.outcome == "merged by human"
            and scope.includes(end)
        )
        if human_merge:
            quality["human_merged_jobs"] += 1
            quality["first_pass_merges"] += not reworked
        active_revision, revision_number, observations = None, 0, set()
        for event in metrics.unique_usage_events(events, run.run_id):
            stamp = instant(event.get("ts"))
            selected = scope.includes(stamp)
            name = event["event"]
            if selected and name in ("mr-opened", "mr-adopted", "strict-verification",
                                      "revision-started", "stage-failed", "operator-retry"):
                selected_ids.add(run.run_id)
            if name == "usage-observation" and event["event_id"] not in observations:
                observations.add(event["event_id"])
                if selected:
                    coverage["launches_with_reported_tokens"] += event["token_status"] == "reported"
                    coverage["launches_with_unavailable_tokens"] += (
                        event["token_status"] == "unavailable"
                    )
                    coverage["launches_capture_disabled"] += event["token_status"] == "disabled"
                    if admin:
                        coverage["launches_with_reported_cost"] += (
                            event["cost_status"] == "reported"
                        )
                        coverage["launches_with_unavailable_cost"] += (
                            event["cost_status"] == "unavailable"
                        )
            if selected and name in ("stage-failed", "operator-retry"):
                quality["stage_failures" if name == "stage-failed" else "operator_retries"] += 1
            if name == "revision-started":
                revision_number += 1
                trigger = event.get("trigger")
                active_revision = {
                    "project_id": project_id,
                    "run_id": run.run_id,
                    "revision": revision_number,
                    "trigger": trigger
                    if trigger in ("revise-label", "pipeline-failed")
                    else "unclassified",
                    "date": scope.local_day(stamp).isoformat() if stamp else None,
                    "tokens_in": None,
                    "tokens_out": None,
                    "reported_cost_usd": None,
                    "estimated_cost_usd": None,
                }
                if selected or stamp is None:
                    coverage["revision_events_unclassified"] += stamp is None or trigger not in (
                        "revise-label",
                        "pipeline-failed",
                    )
                if selected and trigger in ("revise-label", "pipeline-failed"):
                    key = "mr_revisions" if trigger == "revise-label" else "pipeline_repairs"
                    counters[key] += 1
                    bucket(stamp)[key] += 1
                if admin and selected:
                    revisions.append(active_revision)
            if name == "usage" and selected and active_revision is not None and admin:
                if active_revision not in revisions:
                    revisions.append(active_revision)
                add_amounts(active_revision, measured(event, prices, True))
        period_job = period_jobs.get(run.run_id)
        period_amount = period_job["in_period"] if period_job else empty_amounts(admin)
        if admin:
            coverage["runs_with_reported_cost"] += period_amount["reported_cost_usd"] is not None
            coverage["runs_with_estimated_cost"] += period_amount["estimated_cost_usd"] is not None
            if run.lifecycle == "done" and scope.includes(end):
                for kind in ("reported", "estimated"):
                    value = period_amount[f"{kind}_cost_usd"]
                    if value is not None:
                        efficiency[f"{kind}_per_completed"].append(value)
                        if human_merge:
                            efficiency[f"{kind}_per_human_merged"].append(value)
        if run.run_id in selected_ids:
            row = (
                asdict(summary)
                if summary
                else {
                    "run_id": run.run_id,
                    "lifecycle": run.lifecycle,
                    "outcome": run.outcome,
                    "started_at": "",
                    "ended_at": "",
                    "span_seconds": 0,
                }
            )
            row.update(
                {
                    "project_id": project_id,
                    "tokens_in": period_amount["tokens_in"],
                    "tokens_out": period_amount["tokens_out"],
                    "review_rounds": sum(
                        e["event"] == "revision-started" and scope.includes(instant(e.get("ts")))
                        for e in events
                    ),
                }
            )
            if admin:
                row.update(
                    {
                        "cost_usd": period_amount["reported_cost_usd"],
                        "estimated_cost_usd": period_amount["estimated_cost_usd"],
                    }
                )
            else:
                row.pop("cost_usd", None)
            rows.append(row)
    duration = duration_report(summaries, scope)
    for rate, numerator, denominator in (
        ("review_rework_rate", "reworked_jobs", "reviewed_jobs"),
        ("first_validation_rate", "first_pass_validations", "validated_jobs"),
        ("first_pass_merge_rate", "first_pass_merges", "human_merged_jobs"),
    ):
        quality[rate] = quality[numerator] / quality[denominator] if quality[denominator] else None
    if admin:
        quality["cost_efficiency"] = {
            key: {
                "jobs_with_evidence": len(values),
                "usd_per_job": sum(values) / len(values) if values else None,
            }
            for key, values in efficiency.items()
        }
    totals = {
        "runs": len(selected_ids),
        **counters,
        "tokens_in": usage["totals"]["tokens_in"],
        "tokens_out": usage["totals"]["tokens_out"],
    }
    if admin:
        totals.update(
            {
                "cost_usd": usage["totals"]["reported_cost_usd"],
                "estimated_cost_usd": usage["totals"]["estimated_cost_usd"],
            }
        )
    period = {
        "from": scope.start.isoformat() if scope.start else None,
        "to": scope.end.isoformat() if scope.end else None,
        "basis": "dated_events",
        **totals,
        "duration": duration,
    }
    return {
        "scope": scope.public(project_id),
        "totals": totals,
        "period": period,
        "daily": [days[k] for k in sorted(days)],
        "runs": rows,
        "duration": duration,
        "quality": quality,
        "coverage": coverage,
        "current_stock": stock,
        "lifetime": usage["lifetime"],
        "unallocated": usage["unallocated"],
        "jobs": [
            all_jobs[run_id]
            | {
                "in_period": period_jobs.get(run_id, {}).get("in_period", empty_amounts(admin)),
                "coverage": {
                    **all_jobs[run_id]["coverage"],
                    "period_usage_events": period_jobs.get(run_id, {}).get(
                        "in_period", {"events": 0})["events"],
                },
            }
            for run_id in sorted(selected_ids)
        ],
        "timezone": scope.zone.key,
        "granularity": scope.granularity,
        **({"revisions": revisions} if admin else {}),
    }


# END OF FILE
