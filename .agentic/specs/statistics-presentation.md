<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Statistics presentation contract

STATED: live #15 eight criteria; current #14 scoped-metrics.md remains authoritative for server definitions. No backend change is planned.

## Behavior inventory and verification

Scope selection: Admin all authorized projects or one project; Dev one authorized project. Inclusive From/Through calendar days, an explicit All-time action, IANA zone and day/week/month grouping. Existing URL project/tab compatibility remains; selected date/zone/group serialize in the statistics URL and survive reload/Back. The server computes the canonical [from,to) interval (including DST 23/25-hour days); the browser never calculates date attribution and does not display the interval or boundary explanations. The browser verifies response boundaries against captured inclusive local dates using IANA local midnights, with the server's fold=0 behavior for missing/repeated midnight and omitted-bound semantics; agreement between sources on a different requested period is not sufficient.

Response binding — coordinated revalidation: each Statistics read captures principal/role,
authorized immutable project set, calendar/zone/group and selected context. A true
context change immediately hides the preceding context's data and export anchors.
An initial pending read shows loading. A same-context pending read retains the
committed validated report and export disclosure until a coherent replacement is
ready. Reordered, superseded and unmounted completions cannot publish. Validate
required scope/job/stock/amount/sample fields and immutable identity before any
publication. Required nonfinancial metrics total counts must be present safe integers;
a missing run/lifecycle/revision/repair count is invalid evidence, never an implicit
zero or an empty Quality/Trends success. Optional evidence retains its existing
absence/unknown contract. Malformed, scope-mismatched, authorization, integrity and initial
failures hide affected numeric evidence and CSV actions. A positively classified
same-context informational transport/deadline failure may retain the last validated
report only with stale/failed-refresh feedback, last-success time and inline retry;
it grants no action authority. Export anchors stay bound to the selected authorized
query, not to a claim that a later server export equals the retained report.
Server RBAC remains final authority and no client aggregate decides filtering.
The coordinated-generation protocol is specified in
[REQ-DATA-d535499a](REQ-DATA-d535499a.md).

Presentation: Summary shows only measure cards: started/completed/failed and known input/output/total tokens (plus Admin money); no heading, scope line, explanatory paragraphs, coverage counters or Messages. Job elapsed time (samples/mean/median) is in the Usage tab. Per-job consumption is shown only in Jobs (list column and detail) and the Job consumption CSV. Total tokens is available only when both known input/output are available; known partial subtotals keep explicit coverage. Null shows an em dash with Not available, explicit zero says measured zero, known values with missing events say partial. Unallocated observations cannot enter a period bucket. Duration sample definition is terminal summaries with valid elapsed span (waits included) whose end lies in scope, including zero; absent pairs excluded. Financial values are Admin-only, reported and estimated separately named. Launch counts never substitute for messages.

Trends: server buckets render once, as rows of one labeled table whose started/completed/failed cells carry proportional bars; token and money cells show plain values or a dash; no separate chart, time zone label or estimated-cost section. Empty/error/pending remain explicit. Quality/recovery remains secondary in existing tabs. Project breakdown retains authorized project ID as well as display name.

Jobs integration: consume strict project usage/metrics JSON once per visible project rather than one request per row. Show lifetime consumption under immutable identity in list and detail; Jobs has no reporting period. Missing job evidence remains unavailable, never reconstructed from defaults. Route/unmount/grant/query changes invalidate displayed consumption. Existing runtime/job persistence and commands remain untouched.

## Deterministic proof

Setup: offline API/browser fixture with two projects, same run identity; known input/output zero, unknown and partial fields, reported/estimated separate, zero and positive duration samples. Action: switch project/dates/zone/group and delay/abort an earlier read. Oracle: actual captured queries/identities, hand-calculated values, CSV X-ADORE-Scope and captured interval seconds, table labels/values. Negative: malformed scope/jobs/amounts, revoked grant, loading/error, foreign direct route/export, out-of-order responses. Keyboard, trend table values and bars, four locales/themes and width 390 asserted in Chromium; source-safe fixtures only. Live/novice acceptance remains an external gate.
