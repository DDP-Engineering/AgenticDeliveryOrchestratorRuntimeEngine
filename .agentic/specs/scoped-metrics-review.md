<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Candidate review — TASK-97d530c5

Historical round 1 (superseded by round 2 below), initially zero corrective review cycles. Candidate SHA-256: `0b783a7feb6dca018f00733fee4bd324e4f4a188ec7ecf8f79f6692b95687329`.
Bound inventory: `.agentic/tasks/TASK-97d530c5.candidate.json`.
Two separate passes by the primary agent; no second person, subagent, executor
or paid API reviewer was used. Verdicts apply to the same candidate. Any
candidate change invalidates both and requires re-review.

## Specification compliance: approved

Independently re-read the live eight criteria, Frame exclusions, four active
requirements, scoped-metrics spec and design. Traced each criterion to the
verification matrix and implementation/public tests. Shared local-midnight
scope governs totals/daily/CSV; own events govern lifecycle and consumption;
composite job period/lifetime/unallocated and coverage agree; nullable unknown
and observed zero are distinct; all financial fields remain Admin-only.
Rate cohort counts and terminal sample basis are documented and browser pooling
uses server samples. Current stock is named separately. No #15 redesign,
message telemetry, runtime reset/migration, dependency/version or delivery work.
All 17 authored product/test/doc paths and three generated static paths belong
to this scope. Workflow artifacts are separate. No unresolved specification
finding. Final strict proof remains mandatory.

## Implementation quality: approved

Separately inspected touched source/test hunks, the new analytics module and
source/error paths against correctness, portability and trust boundaries.
Raw JSONL rejects malformed/duplicate keys/schema; validation precedes filters;
versioned replays/cursors reject altered evidence. Read-only summary SQLite
preserves source bytes and historical records without current runtime stock.
Nullable sums preserve explicit zero, cache semantics and exclusive reported/
estimated UTC-price evidence; overflow fails typed. Per-job coverage uses the
actual selected period. Own lifecycle/review/strict/revision dates preserve
cross-period activity. Duration samples include valid zero and measured waits.
RBAC occurs before source access; nested JSON, CSV and frontend pooling omit
Dev money. CSV escaping and empty export scope metadata are retained.
Python core is portable with no new dependency. Legal/Doxygen headers and
component/operator/knowledge docs are current. Focused unit/Node/Chromium
proof is green; final Python/Ruff/frontend strict run remains mandatory.
No unresolved implementation-quality finding.

## Recorded design refinement

DEVIATION design: cohort and duration calculations were centralized in
analytics.py alongside scope and consumption — accepted to keep one interval
rule across all projections; scope and authorization remain unchanged.
The proposed diagram remains in the journal; current diagrams show analytical
reports, read-only summaries and authorized API/CSV routing.

## Advisory classification

Existing fingerprint sidecars and unrelated TASK-5e99ee1d/TASK-c765e6b4 journal
format warnings are outside this task. Global manual-verification notes belong
to other requirements; this task's analytical and browser checks are automated.
Secret-in-diff catalog warnings describe untracked generated proof/bundle lines
that the catalog does not scan. Explicit inspection found only test credentials,
public product strings and local evidence; no real credential was introduced.
Vite's existing >500 kB chunk advisory remains; no layout/code-splitting scope
was added. Existing TestClient deprecation and optional skipped test are
reported as observed, without changing dependencies or weakening verification.
These advisories do not remove any required issue-14 proof.

## Current round 2: both verdicts approved

Candidate SHA-256: `e9ff78685f8606de38a23a72781ad4729b3e5d689a94c63e62bcfbc37120f3fe`. Corrective cycles used: 1 of maximum 3.
All 29 bound paths rechecked; 17 authored plus 3 generated product paths remain.

Specification compliance: approved. Separate primary-agent re-read of the four
active requirements, live eight criteria, scoped contract and exclusion/design
records confirms both corrections preserve the same contract. Exact browser
response identity strengthens criterion 1/5; typed revision calendar failures
strengthen criterion 6. No assertion, scope, authorization or source attribution
was weakened. Component/knowledge/project guidance already describes this
strict conversion and requires no semantic change; environment unchanged.

Implementation quality: approved. Separate primary-agent review of the changed
hunks confirms `Scope.local_day` is shared by usage buckets and actual revision
calendar dates without week/month bucketing a revision date. Its local range
errors become AnalyticsError and safe HTTP 503. The new parameterized revision
negative reproduced the previous unhandled overflow and now passes. Exact
immutable project path in Playwright rejects simultaneous global responses;
all DST/CSV/current-state/null assertions remain. Focused API/metrics/pricing
71 passed, targeted Chromium 1 passed, Ruff passed. Production static content
is unchanged by these Python/test corrections. Fresh strict proof is required.

Round-1 post-proof quality verdict was changes_required; both earlier verdicts
were invalidated before edits. The first failed proof is preserved in
TASK-97d530c5.round-1-check.json; the old candidate in round-1-candidate.json.
