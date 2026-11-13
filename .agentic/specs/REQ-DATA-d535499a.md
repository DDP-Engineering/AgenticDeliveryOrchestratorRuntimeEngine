<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-DATA-d535499a — Publish coherent Statistics refresh generations

Status: **active**. This describes the coordinated reporting publication
implemented by `App.tsx` and `statistics.ts`. It supplements the response-binding
contract in [Statistics presentation](statistics-presentation.md). It creates no
API, persisted schema, migration or backend atomic-snapshot contract.

## Evidence and boundary

- STATED (operator request, implementation requirements 1–9): keep same-context
  reports mounted, validate every response, keep metrics and usage scope-consistent,
  reject unrelated refresh generations, preserve cadence and distinguish transport
  failure from invalid or unauthorized evidence.
- OBSERVED (`04_Software/web/src/App.tsx`, reporting owner and due-mask schedule):
  selected metrics runs at 15 seconds; usage and global metrics run at 30 seconds.
  One context-bound proposal validates and publishes the complete report, keeping
  the committed report mounted while same-context revalidation is pending.
- OBSERVED (`04_Software/web/src/statistics.ts`, `readStatistics`,
  `readConsumption`; `web/e2e/statistics.spec.ts` scope and corruption journeys):
  validators and canonical server scope already exist. There is no shared backend
  point-in-time transaction token for metrics plus usage.
- INFERRED (these sources): frontend generation coherence means an explicitly
  coordinated, validated publication, not a claim that independent HTTP responses
  describe an atomic backend instant. A server schema or polling-cadence change
  is not needed to establish this presentation boundary.

## Context and evidence binding

A report context captures the current session/account generation and role,
current authorized immutable project set, global all-project versus selected
immutable project identity, inclusive calendar controls resolved by the server,
IANA timezone and day/week/month granularity. The selected category and export
menu are view state, not a reason to discard an otherwise valid report.

Validation covers the existing required metrics/usage structures and role-specific
financial projection. Metrics run collections must be arrays of object rows with
nonnegative safe-integer review-round counts and a safe per-project derived total;
malformed run evidence fails before publication, not inside global Quality rendering.
Optional revisions may be absent or an empty array; present evidence must be an array
of object rows with scoped project/run identity and unique run/revision pairs.
Revision numbers are positive safe integers; triggers are the server's closed string
enum, dates are nullable valid local calendar days, token directions and known combined
totals are safe, and reported/estimated money is nullable finite and nonnegative.
Malformed revision evidence fails before selected-project Admin Quality rendering,
without any report/exports/success time; initial/replacement browser negatives in
both selected scopes assert no pageerror and valid populated/empty recovery.
Each project in a global response maps to the current
immutable identity, not just a reusable name. The response project set equals the
captured authorized set. Corresponding metrics/usage canonical scopes agree on
project IDs, mode, interval, from, to, timezone, granularity and interval seconds.
Across all projects, these same canonical fields agree excluding project IDs,
whose exact membership is validated separately. Both pooled metrics and pooled
usage are computed within owned validation and stored in the committed report;
rendering does not perform potentially throwing aggregate work. Individually valid
members with inconsistent cross-project intervals or overflowing pooled amounts
fail closed with error/Retry, no report/exports or new success time, and no render
exception. Token validation includes safe-integer directions and known combined
input/output totals before publication, for raw and pooled period/total/day evidence,
usage/cache buckets and job amounts. Known overflow fails closed; a missing direction
keeps the combined total unknown. All members and pooled results validate before
any replacement becomes visible. The configured scope and role also bind CSV links; server authorization
remains authoritative.

A principal/role/grant, project identity or reporting-query change invalidates
the old context before rendering under new controls. A previous context's report
cannot be used as an initial-loading fallback, even if its values are identical.

## Coordinated publication protocol

A **committed report** is the last completely validated metrics/usage pair or
all-project maps for one context. Rendering and CSV disclosure use that committed
report until a replacement can publish or a fail-closed boundary invalidates it.

A **generation** is one bounded proposal with a captured context and an explicit
set of participating resource inputs. No resource success independently mutates
the displayed report. There is at most one in-flight read per resource/context;
repeated automatic/manual/visible/operation triggers coalesce rather than stacking
an unbounded sequence of generations.

1. An initial generation requires every metrics and usage input needed for the
   displayed scope. Single-project reports require only that project's inputs;
   unrelated administrator all-project reads are not dependencies.
2. Full explicit Refresh/retry revalidates all resources needed for the displayed
   report. At periodic triggers, resources retain their existing 15/30-second
   nominal cadence. This specification does not require extra usage/global reads
   on every selected-metrics tick.
3. For a resource not due for revalidation, a generation may explicitly pin the
   validated input from the committed same-context baseline. That input retains
   its own success time and provenance. An input already being refreshed, due in
   the coordinated round, failed since that baseline, or invalidated by scope or
   authority cannot be silently substituted with an older baseline input.
4. Each requested input belongs to that proposal and is staged after validation.
   A slower member keeps the preceding report visible; an earlier member cannot
   publish a half-old/half-new report. Metrics-first and usage-first arrival have
   the same publication outcome. A later unrelated generation's result cannot be
   grafted into this proposal merely because its scope fields happen to match.
5. The complete proposal publishes once, after all participating inputs validate
   and their canonical scopes and current context still agree. Changed values
   update existing panels/rows; identical values preserve content identity. A
   metrics-only periodic proposal with an explicitly pinned baseline usage member
   is not described as a newly completed usage/full-report read.
6. Cancellation, timeout, supersession or failure ends the proposal's publication
   authority. Late completions do not update data, errors or successful timestamps.
   Recovery constructs another proposal for the current context. A failed resource
   remains a required recovery dependency, so an unrelated metrics-only success
   cannot clear a usage failure or renew the whole-report freshness claim.

`createReportingRefresh` implements this protocol through one bounded owned read
and explicit proposal masks; App supplies validated scope mapping and the existing
visibility schedule. No fetching framework or persistent browser cache is used.

## Reporting state transitions

The following are refinements for reporting publication; shared presentation and
security responses are separately governed in the task's requirement coverage.

| Starting state / event | Report publication outcome |
|---|---|
| No committed report; initial read pending | Initial loading; no numeric report or CSV evidence from another context. |
| Ready report; same-context generation starts | Existing report, selected tab, table controls and open CSV disclosure remain mounted. |
| One required resource succeeds; another pending | Stage success only; keep the previous complete report. |
| Complete matching valid proposal succeeds | Publish the coherent replacement; record successes only after validation. |
| Same-context transport failure or read deadline after success | Preserve the previous complete report only as explicitly stale information, with failed-refresh feedback, last success and inline retry. |
| Retry pending after transport failure | Keep that stale indication until the failed dependency and complete required replacement succeed. |
| Initial failure or failure after a context switch | Explicit failure without old numeric evidence or false zero. |
| Malformed JSON/media type/fields, foreign identity, canonical mismatch or typed corruption/integrity refusal | Withhold affected report and dependent exports; not a transport-stale fallback. |
| Current authorization/session loss | Immediately withhold affected protected data and actions once detected, including at received HTTP 401/403 status before any explanatory body. |
| Typed nontransport or unclassified failure | Fail closed; do not guess that an HTTP 5xx or arbitrary exception is transient. |
| Context switch, navigation or unmount during read | Invalidate/cancel ownership; old success and old error cannot publish. |

For this contract, eligible transport failures are positively identified fetch
transport failures and an owned finite read deadline. A navigation/context abort
is cancellation, not a failed-refresh notice in the replacement view. An HTTP
response carrying a typed denial, corruption, snapshot or application failure is
not converted to transport failure based on its status class. JSON parse and
media-type failures are invalid evidence even if encountered inside a catch.

Informational retention does not grant job/configuration/access/approval authority.
CSV controls remain scope-bound; a download reads current server evidence and is
not represented as an exact export of an older retained screen snapshot. A
fail-closed report never leaves prior numeric/export evidence presented as ready.

## Freshness semantics

Successful time is recorded when the owned input completes and validates, not
when its request starts. A full-report completion is recorded only when its
entire requested coherent replacement is publishable. Per-resource success times
remain available for carried inputs; carrying a previous usage result cannot
advance its time or clear its failure. Failed, partial, cancelled and ignored
reads cannot advance success times. An unchanged successful revalidation may
advance its genuine completion time without a loading announcement.

The shared localized Refresh feedback shows Last refreshed for the complete
report, plus labeled Metrics updated and Usage updated source times. Progress and
successful times are outside live regions; a newly failed stale state is announced
once. No interval increase or new reporting-scope format is used.

## Offline verification

`web/tests/statistics.test.mjs` proves proposal staging, pins, promotion, failure
recovery, canonical scope, deadlines and invalidation. Browser fixtures in
`web/e2e/statistics.spec.ts`, `reportingRefresh.spec.ts`, `operationRefresh.spec.ts`
and `sessionRefresh.spec.ts` assert visible behavior and bounded request counts.
The task journal records the commands and observed outcomes. Coverage includes:

- Parameterize all four tabs across Admin global all-project comparison, global
  one-project filter and Project Statistics. Hold metrics, then usage separately,
  across their normal ticks. Assert content and an open export menu survive.
- Stage distinguishable changed metrics and usage, releasing in both orders.
  Before the required second completion, neither new half is visible; after it,
  the coherent pair appears. Repeat unchanged and verify no loading/live-region
  churn. Reject equal-looking scope from a superseded generation.
- With multi-page Usage, set nondefault page size/page and sort, focus a control,
  open the CSV disclosure and establish scroll/selection. Assert preservation
  while held and after unchanged/changed success for surviving context/items.
- Observe selected-metrics-only periodic updates with pinned, not-due usage;
  usage/global reads stay at 30 seconds. Hold/fail a due usage read and verify a
  later metrics result cannot silently make the report current or renew usage time.
- As Admin, hold/fail all-project usage while selected-project metrics/usage
  succeeds; the project report is independent. A selected-scope failure is not.
- Return wrong canonical interval/project set, malformed field/media/JSON,
  unexpected financial projection or foreign identity after good evidence;
  assert explicit failure and absent affected evidence/exports, not stale success.
- Hold a read while changing date/timezone/granularity/project, revoking a grant,
  signing out/in as another role, navigating away and retrying after a deadline;
  release old successes and failures after the new result and assert no overwrite.
- Fail transport after a valid report, inspect stale feedback/last-success/retry,
  then recover automatically and manually. Initial transport failure has no
  retained report. Duplicate Refresh/visibility/timer triggers do not fan out.

## Boundaries

- STATED: server analytical definitions, financial redaction, authorized scope,
  storage and CSV contracts remain unchanged. No backend atomic snapshot is
  promised by independent response coordination.
- INFERRED: pinned validated inputs are necessary to reconcile complete display
  coherence with the explicitly preserved unequal periodic cadences; tests must
  distinguish deliberate carried input from opportunistically mixed generations.
- OBSERVED: proposals have one 30-second deadline, including any pin promotion.
  Refresh triggers join active work; observed operation results instead cancel
  pre-result proposals and require both members from a new generation.
- This reporting contract does not alter executor-output provenance, revision
  binding, conflict handling or its explicit read lifecycle.
