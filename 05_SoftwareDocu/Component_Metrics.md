<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Metrics (`adore/metrics.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/metrics.py`.
> Design context: `00_Planning/ADORE_System_Overview.md`.

## 1. Purpose

Statistics capture and query, standard library only: the promotion signal
for crawl -> walk -> run and the honest answer to "is this actually
helping?". No server, no Prometheus, no exporter - CLI-first plus an
optional self-contained static HTML file.

## 2. Responsibilities

- `summarize_run(store, run_id, files_changed)` - compute one flat
  `RunSummary` from the run's journal (the append-only truth), state, and
  ticket snapshot: outcome, final AEGIS strict-check outcome (`ok` or
  `failed`), priority, span / parked-wait / time-to-MR
  seconds, gate passes/failures, invariant failures, executor launches,
  clarification/review rounds, token totals and cost (from journal `usage`
  events), files changed, MR URL.
- `record_summary(db_path, summary, export_jsonl)` - INSERT OR REPLACE into
  SQLite keyed by run_id (re-records never duplicate) and rewrite the JSONL
  mirror from the database.
- Query/rendering: `load_summaries` (optional since-window on ended_at),
  `aggregate` (grouped by priority/outcome), `export_csv`, `render_html`
  (script-free, HTML-escaped, opens directly in a browser).
- `profile_stats(db_path)` - one project's headline figures (runs, merged,
  failed, success_rate, avg_span_s, launches, tokens, cost, last_run) for the
  `adore profile list`/`show` commands; a missing DB yields zeros.
- `is_terminal(lifecycle)` - only runtime-emitted terminal states are
  recordable: `done`, `failed`, `cancelled`, and `handed-off`. Historical phantom names such
  as `ticket-closed`, `deleted`, and `stale` are not accepted.

Explicitly not owned: when to record (orchestrator, at terminal
transitions), token extraction (executor launcher), resource probing
(`capture_resource` is config intent, pending).

## 3. Implementation Overview

- **Usage flows through the journal**, not the io stream: `output.jsonl` is
  overwritten per gate, so the launcher extracts token/cost totals per
  launch (`GateRun.tokens_in/out/cost_usd` and cache counts from Pi's usage
  records; Pi reports no billed cost) and the orchestrator journals a
  `usage` event per launch (gated by `[metrics] capture_tokens`). Metrics
  sums those events. Every usage event carries a run/attempt ID; identical
  replay is counted once in terminal summaries and web views, while a
  conflicting or malformed replay raises `MetricsError`, and so does a usage
  event without an event ID.
- Executor launches count `stage-launch` events only; the retired
  `delivery-fix` and `revise-start` events are not counted.
- The orchestrator records terminal ADORE lifecycle outcomes; metrics failures
  are logged and never mask the governed run result.
- Human merge completion is stored as `merged by human`; aggregate and profile
  success metrics count outcomes beginning with `merged`.
- Parked wait = sum of parked->resumed gaps; span = first->last journal
  timestamp (includes waits, deliberately - it is the human-visible
  latency); time-to-MR = first event -> `mr-opened`.

### Web analytical projection

`adore/web/analytics.py` owns strict read-only sources, shared Scope, measured
usage/job projections and scoped lifecycle/cohort/duration calculations.
`load_analytical_summaries` reads existing SQLite in mode=ro and requires
exactly the current summary columns: a table with missing or extra columns, or
corrupt/unsupported rows, fail closed (503) without migration.

Reporting scope is the authorized immutable project set, a half-open UTC
instant interval `[from,to)`, the selected IANA timezone and day/week/month
granularity. Inclusive date controls resolve each local midnight independently;
the upper bound is midnight after `day_to`, including 23/25-hour DST days.
Omitted bounds are unbounded; both omitted explicitly select `all_time`.
All scoped totals, cards, tables, daily rows, cohorts and exports use this scope.

Started uses the first `picked` event; completed/failed uses the latest event
matching the final lifecycle. Checkpoints and state update times do not supply
these dates. Recorded summary start/end is fallback only without lifecycle
journal evidence. `current_stock` separately names jobs/active/waiting/review/
terminal now, including only actual retained runtime state.

Unique usage is attributed at its own consumption instant. `jobs` uses
`(project_id,run_id)` with separate `lifetime`, `in_period`, `unallocated`,
source and coverage. Recorded summaries survive runtime-state removal;
positive summary-only measurements (a run known only from `metrics.db`, for
example a deleted one) belong to lifetime/unallocated, never a fabricated
period. Missing individual token fields stay null; explicit measured zero stays
zero. Zero summary amounts are unknown. A usage event without an event ID is
refused, and a naive, date-only or unparseable usage timestamp is
`metrics_corrupt`. Financial fields and financial coverage are Admin-only in every nested
projection and export. Reported and estimated costs remain separate; matching
immutable prices use the consumption UTC day, and never price reported money
again. Coverage identifies partial evidence rather than asserting a full bill.

Review cohorts use first MR opening/adoption in scope; validation cohorts use
first strict verdict in scope. Human merge uses reviewed jobs with actual done
in scope and `merged by human`. Rework requires reviewer-requested revision;
pipeline repair is separate. Each rate exposes numerator/denominator; empty is
null. Open reviews are labeled current state. Monetary efficiency uses only
period consumption for the completed/human-merged cohort and separate known
reported/estimated samples.

Duration is terminal-summary elapsed wall time including waits, selected by
recorded end instant in scope. Count, sum and sorted exact `samples_seconds`
support pooled mean/median without browser date approximation. Recorded zero
is valid; absent pairs are excluded and inconsistent pairs fail.

Raw state/JSONL and read-only summary rows are validated before filters.
Malformed JSON, duplicate keys, unsupported schema, a summary table with missing
or extra columns, invalid fields, conflicting versioned identity/timestamp,
numeric overflow and invalid timestamps fail typed 503 without source rewriting.
Invalid scope/identity filters return 422. Analytical summary reads neither
initialize nor migrate runtime data.
CSV includes scope/project provenance, empty unavailable cells and spreadsheet
escaping; `X-ADORE-Scope`/`X-ADORE-Coverage` describe empty exports too.
Project `/api/v1/projects/{name}/jobs-usage.csv` and Admin global
`/api/v1/jobs-usage.csv` share usage date/timezone/group/executor/model filters.

Offline proof: `test_web_scoped_metrics.py`, `test_web_metrics.py`,
`test_web_pricing.py`, and `web/tests/metrics.test.mjs`, followed by native
Python/Ruff and frontend validation. CLI summary/export semantics are preserved.

## 4. Dependencies

- Internal: `adore.state.StateStore` (journal/state/ticket),
  `adore.util.iso_to_datetime`.
- External: stdlib only (`sqlite3`, `csv`, `json`, `html`).

## 5. Inputs And Outputs

- Inputs: per-run journal/state/ticket; `[metrics]` config paths.
- Outputs: `<store>/metrics.db`, the `runs.jsonl` mirror, CSV text, the
  static `stats.html`.

## 6. Data Contracts

- One SQLite row per run (`run_summaries`, PK run_id), columns = the
  `RunSummary` fields; the JSONL mirror always equals the table.
- `_connect` never alters the table: a `run_summaries` table whose columns
  differ from the current `RunSummary` is refused with `metrics database <path>
  was written by another ADORE build; delete it to start fresh`. The
  `governance_outcome` value comes only from schema-1 `strict-verification`
  journal events and is `ok` or `failed`.
- Journal `usage` event shape: `{event: "usage", event_id: "<run>:<attempt>",
  attempt, context: <gate|phase>, executor, model, review_round, tokens_in,
  tokens_out, cost_usd, cost_reported}`. Every usage event carries the
  versioned identity and the full current fields. New events record executor
  `pi`; stored rows keep whatever executor name they were written with.

## 7. Workflow Integration

Pi versioned usage records carry nullable `cache_read_tokens` and
`cache_write_tokens` with `input_includes_cache=true`; duplicate identity
comparison checks these fields. The web daily usage projection exposes them as
nullable subsets of input and exports both columns. Other-executor records
have unknown cache categories, not an inferred zero.
Web analytics projects versioned launch observations alongside numeric usage,
with a per-run journal cursor. An unchanged journal replay adds no rows;
append-only attempts advance the cursor, and altered earlier evidence fails
closed. Observation timestamps must be UTC and timezone-aware.

`adore stats [--since 30d] [--by priority|outcome] [--html] [--rebuild]`,
`adore report <run-id>` (live compute from the journal - works for any run,
recorded or not), `adore export --csv`. `--rebuild` re-summarizes all
terminal runs in the store. The summary key is the run ID, so repeated rebuilds
retain one row per run; the run state and journals remain unchanged. Web usage
views reconcile versioned source identities into the web SQLite projection and
do not add those events to summary totals a second time. An
administrator can replay all retained journals through the web rebuild action;
summary-only usage remains unallocated rather than being assigned to an
invented day.

## 9. Validation And Tests

- `tests/test_metrics.py`: full catalog computation from a schema-1 journal,
  including failed and successful strict checks; duplicate-free SQLite
  round-trip + mirror; refusal of a metrics database of another build
  (`test_metrics_database_of_another_build_is_refused_untouched`); since-window filtering
  (unparseable timestamps excluded), grouped aggregation, CSV/HTML outputs
  (escaping, no scripts), merged-by-human aggregation/profile statistics, and
  terminal classification.
- `tests/test_executor.py`: usage extraction (summed, malformed-tolerant).
- `tests/test_orchestrator.py`: merged run records one row with summed usage;
  `enabled=false` records nothing.
- Minimum validation after a change: `uv run --group dev pytest tests/test_metrics.py`.

## 10. Limitations And Future Work

- `capture_resource` (docker stats / disk probes) is config intent, pending.
- Code-size lines (+/-) not captured yet (files-changed count only).
- Time-per-gate breakdown exists in the journal but is not yet a summary
  column; add when the dashboard needs it.

## Explicit deleted-job summary cleanup

`delete_summary(db_path, run_id, export_jsonl)` removes exactly the verified deleted job's terminal row and refreshes its optional mirror before a fresh journal can reuse that run ID. Absent/disabled stores stay absent. CLI `stats --rebuild` holds the same conductor lock across its entire compute/write batch, preventing an old snapshot from restoring a deleted summary. Proof: `tests/test_drift_recovery.py` integration and rebuild-lock cases.
