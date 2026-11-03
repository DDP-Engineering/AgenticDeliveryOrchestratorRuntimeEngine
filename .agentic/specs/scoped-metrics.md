<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Scoped web metrics

## Contract

STATED: Live W10/#14 criteria are authoritative. Date controls retain inclusive calendar day_from/day_to; scope exposes UTC aware instants [from,to) where to is midnight after day_to in the chosen IANA timezone. Independent local-midnight conversion handles 23/25-hour DST days. Missing bounds mean unbounded ends; both absent is explicit all_time. Invalid ranges/timezones/granularity/identity filters return typed 422; malformed query types use FastAPI validation detail.

All metric totals, period, daily rows, quality cohorts and duration refer to the requested interval. lifetime and per-job lifetime are explicitly separate. current_stock records actual current lifecycle counts, independent of period. Global mapping retains authorized immutable project identity in every response/job; Dev reads only granted projects and all money fields/coverage remain Admin-only. CSV carries scope/project identity and empty nullable cells.

Started uses earliest picked; terminal completed means one terminal job (done/failed/cancelled/handed-off), failed its own final failure event. Completion uses the latest event matching final lifecycle, including stage-failed/immediate-failure/notification-blocked for failed and cancelled(outcome=failed); later checkpoint/update timestamps never substitute. Summary-only start/end timestamps are recorded fallback only when journal lifecycle evidence is absent. No update time or first unrelated journal event becomes lifecycle evidence. Current active stock is working/publishing; waiting/review and terminal are separately named.

Consumption uses unique numeric usage records by actual aware event timestamp. Identical versioned replay (including timestamp) counts once; conflicting identity fails. Every usage record carries the versioned identity event_id = "<run_id>:<attempt>" and the full current fields; a record without an event ID is refused. A naive, date-only or unparseable usage timestamp is metrics_corrupt; observation timestamps/schema remain strict and invalid evidence fails. The retired delivery-fix and revise-start events are not counted as launches. Unsupported explicit event schema, malformed JSON/object/fields/amounts/identity/verdict and state schema fail typed 503. Validation happens before date/filter exclusion. Journal corruption is never silently skipped. Read queries preserve runtime state and existing schema.

Each token measurement requires its explicit numeric field; an absent input or output remains null independently. Versioned launch records retain their complete paired field contract. Zero explicit measurement is zero. Partial aggregate values are sums of known observations with coverage; never claim a complete bill. Summary-only nonzero amounts (a run known only from metrics.db, for example a deleted one) appear in per-job lifetime/unallocated evidence with source summary; a summary table whose columns differ from the current summary fails closed (503). Period values never infer summary consumption dates. Admin reported cost is explicit cost_reported or historical positive money; estimates use immutable matching executor/model prices effective on UTC consumption day and never price an event twice. Zero token observations with an applicable price yield measured zero estimate. Unallocated events cannot select a price date.

Per-job projections carry (project_id,run_id), lifetime, in_period and unallocated amounts, source/coverage; selected usage jobs include lifecycle or consumption evidence in interval; metric job rows additionally include own-time review/validation/revision/failure/retry activity (all_time includes unknown jobs). Exact executor/model filters scope both period/lifetime measured usage, not job identities or message counts.

Review denominator: distinct jobs whose first mr-opened/adopted event is in scope; reworked numerator: cohort jobs with revise-label evidence. Validation denominator: first strict-verification in scope, numerator passed first verdict. Human merge denominator: reviewed jobs whose done event is in scope and recorded outcome is merged by human; first-pass numerator has no revise-label evidence. Open reviews are current stock, explicitly separate from ratios. Event counters stage-failed/operator-retry/revisions use own times. Cost efficiency uses period usage for done-event cohort jobs, separate known reported/estimated samples. Duration samples are validated terminal-summary elapsed spans (including waits) whose recorded end instant lies in scope; count/sum/sorted sample values are returned so browser pooling uses server-selected samples, with nearest-integer mean and exact median. Zero duration is valid when start=end; absent pair excluded; malformed/inconsistent pair fails.

## Compatibility and ownership

OBSERVED existing consumers expect totals/runs/daily/period/quality/coverage and usage daily/totals; keep shapes, add scope/current_stock/lifetime/jobs/sample metadata. Correct scoped totals and nullable token fields in consumers and update documented labels without #15 layout work. Preserve CLI summary/export semantics. Existing broad REQ-FUNC-448cbde7 is explicitly revised for authorized scope; independent job, strict input and analytical sample behaviors get dedicated requirements.

## Verification

Hand-calculated API fixtures cover cross-period starts/ends/usage, both interval endpoints, March/October Europe/Bucharest DST, invalid/missing dates, unknown/zero/unallocated, summary-only evidence, identity collisions, exact filtered CSV, replay conflicts, corrupt source JSON/schema/amounts/timezone/range, Dev denial and price history. Existing API/pricing/metrics tests plus frontend aggregation tests and complete offline suites apply. Live evidence remains human acceptance.
