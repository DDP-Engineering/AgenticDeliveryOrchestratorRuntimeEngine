<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Metrics (`adore/metrics.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/metrics.py` - file version 0.3.0.
> Design: Orchestrator_Design_And_Decisions.md section 13.

## 1. Purpose

Statistics capture and query, standard library only: the promotion signal
for crawl -> walk -> run and the honest answer to "is this actually
helping?". No server, no Prometheus, no exporter - CLI-first plus an
optional self-contained static HTML file.

## 2. Responsibilities

- `summarize_run(store, run_id, files_changed)` - compute one flat
  `RunSummary` from the run's journal (the append-only truth), state, and
  ticket snapshot: outcome, final AEGIS governance outcome (`ok`, `waived`,
  or `failed`), priority, span / parked-wait / time-to-MR
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
- `is_terminal(lifecycle)` - which states are recordable.

Explicitly not owned: when to record (orchestrator, at terminal
transitions), token extraction (executor launcher), resource probing
(`capture_resource` is config intent, pending).

## 3. Implementation Overview

- **Usage flows through the journal**, not the io stream: `output.jsonl` is
  overwritten per gate, so the launcher extracts token/cost totals per
  launch (`GateRun.tokens_in/out/cost_usd` from opencode `step_finish`
  events - schema pinned live 2026-07-03) and the orchestrator journals a
  `usage` event per launch (gated by `[metrics] capture_tokens`). Metrics
  sums those events.
- The orchestrator records at every terminal transition (escalate, cancel,
  answer-timeout, orphaned, merged, mr-closed) - **before** teardown on
  merge/close so files-changed is still measurable - and metrics failures
  are logged, never breaking a run.
- Parked wait = sum of parked->resumed gaps; span = first->last journal
  timestamp (includes waits, deliberately - it is the human-visible
  latency); time-to-MR = first event -> `mr-opened`.

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
- `_connect` adds newly introduced summary columns with neutral defaults, so
  an existing metrics database gains `governance_outcome` without being
  discarded. The value comes from the final `verify-run-result` journal event;
  `waived` therefore remains observable after an MR is eventually merged.
- Journal `usage` event shape: `{event: "usage", context: <gate|phase>,
  tokens_in, tokens_out, cost_usd}`.

## 7. Workflow Integration

`adore stats [--since 30d] [--by priority|outcome] [--html] [--rebuild]`,
`adore report <run-id>` (live compute from the journal - works for any run,
recorded or not), `adore export --csv`. `--rebuild` re-summarizes all
terminal runs in the store (used once to backfill the pilot run).

## 9. Validation And Tests

- `tests/test_metrics.py`: full catalog computation from a crafted journal,
  including a final waived governance outcome; duplicate-free SQLite
  round-trip + mirror; in-place legacy table extension; since-window filtering
  (unparseable timestamps excluded), grouped aggregation, CSV/HTML outputs
  (escaping, no scripts), terminal classification.
- `tests/test_executor.py`: usage extraction (summed, malformed-tolerant).
- `tests/test_orchestrator.py`: merged run records one row with summed usage;
  `enabled=false` records nothing.
- Live: `adore stats --rebuild` backfilled pilot run #45 from its journal
  (merged, 6 gates, 2 clarification rounds, 1 review round, 31 launches).
- Minimum validation after a change: `uv run --group dev pytest tests/test_metrics.py`.

## 10. Limitations And Future Work

- `capture_resource` (docker stats / disk probes) is config intent, pending.
- Code-size lines (+/-) not captured yet (files-changed count only).
- Runs before 2026-07-04 have no `usage` events, so token/cost read 0 for
  them (the pilot run included).
- Time-per-gate breakdown exists in the journal but is not yet a summary
  column; add when the dashboard needs it.
