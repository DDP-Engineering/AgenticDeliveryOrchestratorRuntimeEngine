<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-140be4c6 - Compact the statistics Trends tab

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-8f024140, REQ-UX-a24db609
parent:
branch: task/adore-web-interface
base: d55d704df6eb08bda7f761c8053b40154422f8eb
opened: 2026-10-11

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: Trends repeats itself: a UTC side label and a "Job trend chart · UTC · day" caption, a bar chart with three rows per bucket followed by a table of the same buckets ("accessible equivalent") whose every value carries a "Known measurement" label, a coverage paragraph, and an Admin Estimated cost section that repeats the estimated column day by day, a one-row per-project table in a project hub and a price help paragraph (STATED: "La fel trebuie facut si cu pagina trends. In primul rand, scoase etichetele UTC. Apoi - estimated cost parca apare de 2 ori ... Chiar sunt necesare toate acestea?").
Desired outcome: one compact trend table: each bucket once with inline proportional bars for started/completed/failed and plain token/money values; coverage as compact values; no UTC labels; no separate chart or estimated-cost section. Unique information moves: Admin unpriced usage events to the Usage totals; estimated cost per project to the global Projects comparison.
Actors: administrators and developers viewing project or global Statistics.
Primary scenario: open Statistics > Trends -> heading (Daily/Weekly/Monthly activity), coverage values, one table: Date | Started (bar) | Completed (bar) | Failed (bar) | Input | Output | Reported/Estimated (Admin).
Examples: nilo screenshot (two daily buckets; estimated cost visible in the table and again below).
Counterexamples: estimated cost total stays in Summary and Usage; the table keeps exact numbers for every bucket; Dev still sees no money.
In scope: TrendEvidence, Trends markup, Usage unpriced chip, Projects estimated column, copy/i18n keys, CSS, e2e, requirements/spec/docs.
Out of scope: metrics API and buckets; full suite (STATED: at the end).
Constraints: REQ-UX-a24db609 accessible trends (the table itself is the accessible presentation); REQ-FUNC-930e3ae0 financial boundary.
Success signals: e2e shows the single table and moved values; DCP shows the compact tab.
Evidence: OBSERVED App.tsx Trends section (metricTimezone label, coverage-note, Admin estimated panel with priceHelp, per-project and daily tables) and StatisticsEvidence.tsx TrendEvidence (figure + table with Measurement labels).
Assumptions: merging chart and table into one table with inline bars keeps the visual trend while removing the duplicate (INFERRED from "Chiar sunt necesare toate acestea?").
Unknowns: none blocking. Decision-blocking questions: none.
Proposed behaviors: B1 single trend table with bars and plain values, no UTC/chart; B2 coverage as compact values; B3 no estimated section, unpriced in Usage, estimated per project in Projects (REQ-UX-8f024140; REQ-UX-a24db609 revised).
Path and reason: full - observable UI change with requirement changes.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| no duplicate trend | B1 one table with bars | REQ-UX-8f024140 (new), REQ-UX-a24db609 (revised) | four locales exact counts and bars | empty scope keeps empty feedback | e2e statistics.spec | D1 |
| less text | B2 coverage chips, no UTC | REQ-UX-8f024140 | coverage values visible | no UTC text | e2e statistics.spec | D2 |
| estimated once | B3 moved Admin values | REQ-UX-8f024140 | Usage unpriced chip; Projects estimated column | Dev without money | e2e statistics.spec | D3 |

## Design

- D1 TrendEvidence renders one `table.trend-table` (aria-label copy.table, now "Trend data") with started/completed/failed cells holding the number plus an aria-hidden bar scaled to the largest count, and token/money cells as plain formatted values or a dash; the figure and Measurement labels go.
- D2 Trends panel: h2 trend title, `Chips` with usage coverage (runs with usage / jobs) and undated usage; no metricTimezone label or coverage-note paragraph.
- D3 remove the Admin Estimated cost section; add Admin "Unpriced usage events" to usageTotals and an Admin Estimated cost column (with total) to the Projects comparison.
- Test seams: e2e/statistics.spec.ts four-locale test (table, bars, no figure/UTC/measurement labels) and a new Admin test (no estimated section, unpriced chip, Projects column).

## Log

- 2026-10-11 frame: scope accepted from the user request (Trends like Usage/Quality: no UTC labels, no duplicated estimated cost, only what is needed); autopilot as in prior refinements; full path; full suite deferred by user.
- 2026-10-11 specify: 1 created (REQ-UX-8f024140), 1 revised (REQ-UX-a24db609); 0 retired.
- 2026-10-11 design: see ## Design D1-D3.
- 2026-10-11 build red: REQ-UX-8f024140, REQ-UX-a24db609 command=`npx playwright test e2e/statistics.spec.ts` (current bundle); exit=1 (2 failed, 10 passed); expected missing behavior=Trends still renders the figure, Measurement labels, UTC labels, coverage paragraph and Estimated cost section; Usage lacks the unpriced chip and Projects lacks the estimated column.
- 2026-10-11 build green: `npx tsc -b` + e2e typecheck clean; unit 81 pass; e2e statistics+shell+jobs 54/56 at first (new test used the wrong labels "Estimated cost" vs "Estimated cost (USD)" and /metrics?tab=projects normalizes to Summary; jobs "Route is already handled" flake passed on rerun), then statistics+jobs 44 and statistics+shell 25 passed (REQ-UX-8f024140, REQ-UX-a24db609). TrendEvidence is one table with bars; chart, UTC labels, coverage paragraph and Estimated cost section removed; unpriced chip in Usage; estimated column in Projects; copy trend key removed and table label shortened; docs/spec/CHANGELOG updated.
- 2026-10-11 validate review round 1: implementation-quality - All projects Usage showed unpriced events as a dash because aggregateUsage dropped the field, and .coverage-note CSS was dead; spec-compliance FAIL on the same unpriced value (per-project unpriced lost in All projects) and two docs still claiming chart/table parity tests - fixed: aggregateUsage sums unpriced_events (unit test), All projects Usage table gains an Unpriced usage events column, e2e asserts the pooled chip value and column, dead CSS and vacuous assertion removed, spec/doc wording updated. tsc clean; unit 82; e2e statistics+shell 25 passed.
- 2026-10-11 validate review round 2: spec-compliance PASS; implementation-quality PASS.
- 2026-10-11 validate final: `python .agentic/aegis.py check --task TASK-140be4c6 --strict` errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by tsc (src + e2e), unit 82 and e2e statistics+shell 25 (statistics+jobs 44 earlier; one jobs flake passed on rerun). Frontend deployed to DCP (assets 200).
- 2026-10-12 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-12 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-140be4c6.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Trends is one table with a row per bucket and inline count bars; UTC/measurement labels, chart, coverage paragraph and Estimated cost section removed; coverage as compact values; Admin unpriced usage events in Usage totals (pooled correctly) and an All projects Usage column; estimated cost per project in Projects
evidence: tsc clean; unit 82; e2e statistics+shell 25 passed; review round 2 PASS/PASS; deployed to DCP
issues: DEVIATION full suite deferred by user
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-12)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-8f024140 - Show Statistics trends as one compact table
  - REQ-UX-a24db609 - Explain measured statistics and accessible trends
- deviations: 1 recorded
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by tsc (src + e2e), unit 82 and e2e statistics+shell 25 (statistics+jobs 44 earlier; one jobs flake passed on rerun). Frontend deployed to DCP (assets 200).
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base d55d704: 15 file(s) changed, 212 line(s) added
- checks: errors=0 warnings=10 notes=22
- checklist: 6/6 done
