<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Statistics presentation contract

STATED: live #15 eight criteria; current #14 scoped-metrics.md remains authoritative for server definitions. No backend change is planned.

## Behavior inventory and verification

Scope selection: Admin all authorized projects or one project; Dev one authorized project. Inclusive From/Through calendar days, an explicit All-time action, IANA zone and day/week/month grouping. Existing URL project/tab compatibility remains; selected date/zone/group serialize in the statistics URL and survive reload/Back. Server canonical [from,to) and actual interval seconds are rendered verbatim; browser never calculates date attribution. Show next-local-midnight exclusivity and DST 23/25-hour possibility in plain language. Partial unbounded intervals are labeled by the actual server scope.

Response binding: each statistics request captures project identity, calendar/zone/group and current authorization set. Render keys hide old data immediately; effect invalidation and per-refresh sequence suppress reordered and unmounted completions. Validate required scope/job/stock/amount/sample fields and project identity before state becomes ready. Malformed/error/loading hides numeric presentations and CSV actions. Export anchors use the captured current query; server RBAC remains final authority. No client aggregate decides source filtering.

Presentation: Summary initial measures started/completed/failed, known input/output/total tokens, samples/mean/median and coverage. Current stock is separately headed Current state, active now. Total tokens is available only when both known input/output are available; known partial subtotals keep explicit coverage. Null shows an em dash with Not available, explicit zero says measured zero, known values with missing events say partial. Unallocated observations are separate with counts/known amounts and cannot enter a period bucket. Duration sample definition is terminal summaries with valid elapsed span (waits included) whose end lies in scope, including zero; absent pairs excluded. Financial values are Admin-only, reported and estimated separately named with price provenance. Messages: Not available, actual sources pending; launch counts never substitute.

Trends: server daily rows give readable date/category/value labels; visual bars share exactly the rows used by an adjacent captioned accessible table. Empty/error/pending remain explicit. Quality/recovery remains secondary in existing tabs. Project breakdown retains authorized project ID as well as display name. Jobs table carries (project_id,run_id), lifetime/in_period/unallocated amounts with token directions and source/coverage; same run ID in two projects never collides.

Jobs integration: consume strict project usage/metrics JSON once per visible project rather than one request per row. Show selected period and lifetime under immutable identity in list and detail. Missing selected job evidence remains unavailable, never reconstructed from defaults. Selection filters reuse statistics query; default all-time is explicit. Route/unmount/grant/query changes invalidate displayed consumption. Existing runtime/job persistence and commands remain untouched.

## Deterministic proof

Setup: offline API/browser fixture with two projects, same run identity; known input/output zero, unknown and partial fields, undated observations, reported/estimated separate, zero and positive duration samples. Action: switch project/dates/zone/group and delay/abort an earlier read. Oracle: actual captured queries/identities, hand-calculated values, CSV X-ADORE-Scope, stock separation, table labels/values. Negative: malformed scope/jobs/amounts, revoked grant, loading/error, foreign direct route/export, out-of-order responses. Keyboard, table/chart parity, four locales/themes and width 390 asserted in Chromium; source-safe fixtures only. Live/novice acceptance remains an external gate.
