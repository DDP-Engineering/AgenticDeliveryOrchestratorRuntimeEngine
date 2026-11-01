<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Statistics presentation contract

STATED: live #15 eight criteria; current #14 scoped-metrics.md remains authoritative for server definitions. No backend change is planned.

## Behavior inventory and verification

Scope selection: Admin all authorized projects or one project; Dev one authorized project. Inclusive From/Through calendar days, an explicit All-time action, IANA zone and day/week/month grouping. Existing URL project/tab compatibility remains; selected date/zone/group serialize in the statistics URL and survive reload/Back. The server computes the canonical [from,to) interval (including DST 23/25-hour days); the browser never calculates date attribution and does not display the interval or boundary explanations.

Response binding: each statistics request captures project identity, calendar/zone/group and current authorization set. Render keys hide old data immediately; effect invalidation and per-refresh sequence suppress reordered and unmounted completions. Validate required scope/job/stock/amount/sample fields and project identity before state becomes ready. Malformed/error/loading hides numeric presentations and CSV actions. Export anchors use the captured current query; server RBAC remains final authority. No client aggregate decides source filtering.

Presentation: Summary shows only measure cards: started/completed/failed and known input/output/total tokens (plus Admin money); no heading, scope line, explanatory paragraphs, coverage counters or Messages. Job elapsed time (samples/mean/median) is in the Usage tab. Per-job consumption is shown only in Jobs (list column and detail) and the Job consumption CSV. Total tokens is available only when both known input/output are available; known partial subtotals keep explicit coverage. Null shows an em dash with Not available, explicit zero says measured zero, known values with missing events say partial. Unallocated observations cannot enter a period bucket. Duration sample definition is terminal summaries with valid elapsed span (waits included) whose end lies in scope, including zero; absent pairs excluded. Financial values are Admin-only, reported and estimated separately named. Launch counts never substitute for messages.

Trends: server buckets render once, as rows of one labeled table whose started/completed/failed cells carry proportional bars; token and money cells show plain values or a dash; no separate chart, time zone label or estimated-cost section. Empty/error/pending remain explicit. Quality/recovery remains secondary in existing tabs. Project breakdown retains authorized project ID as well as display name.

Jobs integration: consume strict project usage/metrics JSON once per visible project rather than one request per row. Show lifetime consumption under immutable identity in list and detail; Jobs has no reporting period. Missing job evidence remains unavailable, never reconstructed from defaults. Route/unmount/grant/query changes invalidate displayed consumption. Existing runtime/job persistence and commands remain untouched.

## Deterministic proof

Setup: offline API/browser fixture with two projects, same run identity; known input/output zero, unknown and partial fields, reported/estimated separate, zero and positive duration samples. Action: switch project/dates/zone/group and delay/abort an earlier read. Oracle: actual captured queries/identities, hand-calculated values, CSV X-ADORE-Scope and captured interval seconds, table labels/values. Negative: malformed scope/jobs/amounts, revoked grant, loading/error, foreign direct route/export, out-of-order responses. Keyboard, trend table values and bars, four locales/themes and width 390 asserted in Chromium; source-safe fixtures only. Live/novice acceptance remains an external gate.
