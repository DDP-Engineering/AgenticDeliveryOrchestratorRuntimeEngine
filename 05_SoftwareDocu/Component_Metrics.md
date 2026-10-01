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
  recordable: `done`, `failed`, and `cancelled`. Historical phantom names such
  as `ticket-closed`, `deleted`, and `stale` are not accepted.

Explicitly not owned: when to record (orchestrator, at terminal
transitions), token extraction (executor launcher), resource probing
(`capture_resource` is config intent, pending).

## 3. Implementation Overview

- **Usage flows through the journal**, not the io stream: `output.jsonl` is
  overwritten per gate, so the launcher extracts token/cost totals per
  launch (`GateRun.tokens_in/out/cost_usd` from opencode `step_finish`
  events - schema pinned live 2026-07-03) and the orchestrator journals a
  `usage` event per launch (gated by `[metrics] capture_tokens`). Metrics
  sums those events. New events carry a run/attempt ID; identical replay is
  counted once in terminal summaries and web views, while a conflicting or
  malformed versioned replay raises `MetricsError`. Older events without IDs
  retain their historical behavior.
- The orchestrator records terminal ADORE lifecycle outcomes; metrics failures
  are logged and never mask the governed run result.
- Human merge completion is stored as `merged by human`; aggregate and profile
  success metrics count outcomes beginning with `merged`, preserving both the
  operator-visible wording and older `merged` summary rows.
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
- `_connect` adds newly introduced summary columns with neutral defaults. The
  `governance_outcome` value comes only from schema-1 `strict-verification`
  journal events and is `ok` or `failed`.
- Journal `usage` event shape: `{event: "usage", event_id: "<run>:<attempt>",
  attempt, context: <gate|phase>, executor, model, review_round, tokens_in,
  tokens_out, cost_usd, cost_reported}` for new launches. Legacy events may
  omit identity fields.

## 7. Workflow Integration

Pi versioned usage records carry nullable `cache_read_tokens` and
`cache_write_tokens` with `input_includes_cache=true`; duplicate identity
comparison checks these fields. The web daily usage projection exposes them as
nullable subsets of input and exports both columns. Legacy and other-executor
records have unknown cache categories, not an inferred zero.
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
do not add those events to legacy summary totals a second time. An
administrator can replay all retained journals through the web rebuild action;
missing legacy usage remains
unknown rather than being assigned to an invented day.

## 9. Validation And Tests

- `tests/test_metrics.py`: full catalog computation from a schema-1 journal,
  including failed and successful strict checks; duplicate-free SQLite
  round-trip + mirror; in-place legacy table extension; since-window filtering
  (unparseable timestamps excluded), grouped aggregation, CSV/HTML outputs
  (escaping, no scripts), merged-by-human aggregation/profile statistics, and
  terminal classification.
- `tests/test_executor.py`: usage extraction (summed, malformed-tolerant).
- `tests/test_orchestrator.py`: merged run records one row with summed usage;
  `enabled=false` records nothing.
- Minimum validation after a change: `uv run --group dev pytest tests/test_metrics.py`.

## 10. Limitations And Future Work

- The web API groups journal usage by UTC event date and includes live-run
  usage in headline totals, with terminal-summary token fallback for legacy
  runs without usable journal usage. It removes all cost fields for developers and returns null
  cost to admins when no explicit cost was reported (or when an old event has
  the default zero without coverage). This does not turn the
  existing summary's zero defaults into a complete billing ledger.

- `capture_resource` (docker stats / disk probes) is config intent, pending.
- Code-size lines (+/-) not captured yet (files-changed count only).
- Runs before 2026-07-04 have no `usage` events, so token/cost read 0 for
  them (the pilot run included).
- Time-per-gate breakdown exists in the journal but is not yet a summary
  column; add when the dashboard needs it.
