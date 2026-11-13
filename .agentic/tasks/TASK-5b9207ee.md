<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-5b9207ee - Keep automatic page refresh unobtrusive and preserve view state across the web interface

stage: specify
type: feature
path: full
interaction: autopilot
requirements:
parent:
branch: adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-77
base: bafae7e55bbcfda18451ee621368204af9dd864b
opened: 2026-11-13

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [ ] every accepted behavior is one coverage row with exactly one requirement
- [ ] each error or failure response has its own requirement
- [ ] each requirement is one self-contained "shall" sentence
- [ ] verification names setup, trigger, oracle and a boundary or failure
- [ ] specs written only where the requirement cannot carry the detail
- [ ] conflicts, assumptions and unknowns resolved or recorded
- [ ] every ID on the journal's `requirements:` line; `check` shows no
      format errors

## Frame

### Problem

- STATED (ticket #77, Problem/root cause): automatic refresh interrupts reading,
  notably Statistics, by replacing displayed data with loading panels and resetting
  tables/disclosures. The investigation on `030e47f8` was source analysis, not a
  deployed visual reproduction.
- OBSERVED (current `04_Software/web/src/App.tsx:395-409,550-609,723-739,1273-1283`):
  selected/global metrics and usage set loading on every request; combined reporting
  readiness then removes content and CSV disclosure. `PagedTable` owns local page
  size/page (`App.tsx:1523-1550`), so unmounting loses those controls.
- OBSERVED (`JobWorkspace.tsx:113-205`): non-overview list polling sets loading,
  consumption polling clears amounts, and detail polling ALSO clears detail and sets
  loading. The ticket's assertion that detail already retains content does not hold
  in this checkout; detail continuity is an implementation obligation, not merely
  an already-passing regression assumption.
- OBSERVED (`AuditHistory.tsx:72-110`; `App.tsx:611-623,1321-1322`): periodic audit
  reads retain rows while pending, but manual same-query refresh clears them; Users
  rereads set loading and the header timestamp is set before successful completion.

### Desired outcome

- STATED (#77 requirements 1-9): initial/different-context loading remains visible;
  same-context revalidation keeps a validated rendered snapshot and stable view
  controls until a validated replacement is available. Changed values update in
  place; unchanged successful responses do not collapse content or repeatedly
  announce loading. Explicit Refresh/retry supplements, rather than replaces,
  automatic updates and records successful completion time.
- STATED (#77 requirements 2,3,6,7): data stays bound to current principal/role/grants,
  immutable project/run, reporting scope and filters/paging snapshot. Coherent
  Statistics replacements cannot mix unrelated generations. Reads are bounded and
  serialized/coalesced, stale completions are ignored, and navigation/sign-out
  cannot expose another context's data. Informational transport failures may retain
  validated evidence only with stale/failed-refresh status, last success and retry;
  auth/access, malformed/integrity and paging failures remain fail-closed.

### Actors

- STATED (#77 inventory/acceptance): administrators viewing all-project or scoped
  data and managing Users/Settings/Access; project-scoped developers viewing only
  authorized nonfinancial evidence; operators reading active jobs and history.
- OBSERVED (`.agentic/context/project.md`, web-interface knowledge): the API/worker
  owns action authority; browser polling is presentation/read behavior, not permission
  to approve, execute or merge anything.

### Primary scenario

- STATED (#77 acceptance): open global or project Statistics, choose any of Summary,
  Usage, Quality or Trends, open CSV export, and keep reading while the 15-second
  metrics or 30-second usage/global metrics response is held. Content/export stays
  mounted; independent metrics/usage completion order yields only coherent evidence.
  Resolve unchanged then changed validated data without resetting the selected view.

### Examples

- STATED (#77 acceptance): Usage has multiple pages; choose a non-default page size,
  page and sort, focus a control, then tick/hold/resolve background requests. Controls,
  disclosure, focus and scroll remain stable while the same context/item exists.
- STATED (#77 inventory/acceptance): global/project Jobs and project job History keep
  rows, pager, open job and amounts through slow/unchanged reads; audit and Users
  manual Refresh keep same-query data and unrelated valid drafts while pending.
- STATED (#77 requirements 6-8): overlapping ticks and repeated Refresh clicks share
  bounded work; hidden tabs send no periodic reads and visible return revalidates
  without a burst. A transient informational transport failure is distinguishable
  from a successful current snapshot and can recover through the same read path.

### Counterexamples

- STATED (#77 requirements 2,7): changing account, authorized scope, project, run,
  reporting period/timezone/granularity, filter or paging context must not reuse an
  old context under the new heading. Revoked access removes protected data immediately
  when detected; visual continuity is never an authorization exception.
- STATED (#77 requirements 4,7): a removed item or expired server page snapshot uses
  an explicit existing transition/reload, not silent snapshot mixing. Corrupt or
  malformed evidence cannot be rendered as merely stale.
- STATED (#77 inventory): a valid unchanged Settings/Access review survives unrelated
  successful reads, but changed underlying revision/authority invalidates it. Old
  informational evidence must not enable a privileged or operational action.

### In scope

- STATED (#77 inventory/primary code): focused frontend changes in `App.tsx`,
  `JobWorkspace.tsx`, `AuditHistory.tsx`, `polling.ts`, shared feedback and localized
  copy/styles as required, retaining component identity and stable row keys.
- STATED (#77 inventory) with OBSERVED detail correction above: repair Statistics
  globally (all-project/comparison and one-project filter) and project-scoped across
  all four tabs; Jobs lists/history, detail and consumption; audit same-query manual
  rereads and Users manual rereads. Avoid irrelevant administrator all-project usage
  requests controlling project Statistics readiness.
- STATED (#77 inventory): regression-check Overview/project Summary, Projects/context
  selector, removed/archived/access-changed projects, Settings/prices/credentials/model
  drafts and reviews, Access, System status, ticket bodies/confirmations, executor
  output, finite ChatGPT sign-in, operation trackers and factory-password/session
  transitions. Fix refresh-triggered state loss within these established boundaries,
  without a general data-fetching rewrite.
- STATED (#77 acceptance; repository AGENTS.md): offline helper/browser coverage,
  component documentation (`05_SoftwareDocu/Component_Web_Frontend.md` and any other
  changed component), `01_Documentation/Web_Interface.md`, root CHANGELOG,
  EN/FR/DE/RO release notes and affected four-locale help (notably interface,
  statistics, jobs, overview, administration/settings where described).
- OBSERVED (web-interface knowledge, environment guide, package scripts): frontend
  build inputs require rebuilding/verifying committed `04_Software/adore/web/static/`
  and its existing asset stamp at build/validate; no packaging/release operation is
  required for this task. Governed requirements/specs/knowledge are updated in their
  proper later stages, not represented as implemented behavior during frame.

### Out of scope

- STATED (#77 scope/requirements 9): no backend forge/executor behavior changes,
  stored-data migration, AEGIS payload changes, WebSocket/SSE, global polling removal
  or interval increases as a substitute for fixing presentation.
- STATED (#77 inventory): no new periodic ticket/comment/forge reads; enrollment,
  connectivity checks, raw/portable configuration, account/About/Help and other
  explicit actions keep their existing feedback and edit lifecycle.
- STATED (#77 coordination): no independent executor-output conflict/provenance
  redesign (#71) or direct-workflow presentation redesign (#66). Preserve the
  integrated implementation and coordinate only refresh/identity interactions.
- STATED (session instructions, repository AGENTS.md): no child tasks, commits,
  pushes, MR/PR or merge, credentials, planning-folder edits, or payload edits.

### Constraints

- STATED (conductor instructions): exactly frame in this session; interaction is
  autopilot (already set), choose and justify full/quick; advance only a finished
  stage and stop immediately at its boundary. Task identity/history and CLI-owned
  Log/Rulings/State must survive all edits.
- OBSERVED (`git branch --show-current`, `git rev-parse HEAD`): checkout is
  `adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-77`, matching the
  journal, not default `origin/master`; HEAD inspected is
  `153032f331d00e23df7b97230596d960411c9063`. Journal base remains its original
  `bafae7e55bbcfda18451ee621368204af9dd864b`; do not replace it with investigation HEAD.
- STATED (#77 inventory): preserve current cadence (15s lists/selected metrics/
  metadata/settings/access/audit, 30s usage/global metrics/storage, 5s worker,
  2s active operations, 1s pending finite sign-in) and hidden/visible behavior;
  successful reads must not change dirty-form, mutation, candidate/revision or
  server snapshot authority. No measured reason for interval changes is established.
- STATED (repository rules): offline happy and negative trust-boundary tests;
  no network or real external CLI/runtime/model operations, no setup-script tests,
  no migrations/compatibility readers, legal headers on generated files, maintain
  four locales/both themes and simple focused code.
- INFERRED (ticket scope and repository simplicity rule): no product dependency is
  presently justified; existing React, Node test runner and Playwright support the
  required proof. Any later dependency proposal needs explicit scope justification
  and lockfile discipline, not an incidental tooling fix.
- STATED (this executor's bounded frame plan under repository run limits): at most
  one journal file edited, no product/test/dependency edits or implementation test
  runs, one frame-completion advance, and a 45-minute wall-clock ceiling; earlier
  exhaustion would be logged and paused, not advanced unfinished.

### Success signals

- STATED (#77 acceptance): held and unchanged/changed background reads keep content,
  export disclosure and view controls for global/project Statistics in every tab,
  Jobs/History/detail/amounts, including independent reporting completion order.
- STATED (#77 acceptance): meaningful offline browser tests assert non-default
  pagination/sort, expansion, focused DOM control, scroll/selection continuity and
  stable job links, not private hook or timer implementation details.
- STATED (#77 acceptance): same-query audit/Users manual rereads and operation-triggered
  revalidation preserve unrelated valid state; smooth surfaces stay smooth; changed
  authority invalidates reviews and no stale privileged action becomes enabled.
- STATED (#77 negative acceptance): context switch in flight, old completion,
  overlapping reads, unmount/navigation, sign-out/account change, access revocation,
  malformed/incomplete evidence, initial failure, transient failure/recovery and
  server snapshot conflict fail or retain information according to their trust
  boundary, with visible successful-completion time and non-destructive retry.
- STATED (#77 acceptance/repository rules): hidden-tab requests stay paused; visible
  return is bounded/coalesced; existing offline suites, localization/help contracts,
  release-note check and production asset consistency remain required later proof.

### Evidence

- OBSERVED: `.agentic/knowledge/web-interface.md` Routing names App/JobWorkspace and
  `web/e2e/jobs.spec.ts`; frontend owns this task. `.agentic/knowledge/polling.md`
  instead routes to the Python conductor cadence, not browser polling; its scheduling
  behavior is not a target. Project/environment context was read.
- OBSERVED: `App.tsx:395-409,550-739,760-779,1321-1322,1432-1457,1496-1508`
  shows independent report readers, settings polling guards, operation completion
  calling broad refresh, and audit/access keys containing `viewRefresh`.
  `ProjectAccess` (`App.tsx:1565-1627`) serializes reads against mutations and keeps
  a review only if the selected account's relevant authority remains unchanged.
- OBSERVED: `polling.ts` controls visibility/timers but takes a synchronous tick and
  does not serialize async work. `tests/polling.test.mjs` checks timers/listeners;
  repeated visible events currently invoke tick again, so one timer is not proof
  of one in-flight request. Resource/context coalescing needs explicit verification.
- OBSERVED: `App.tsx:101-121` maps fetch failures to `network_error`, non-OK typed
  responses to their code, invalid media type to `unexpected_response`; JSON parse
  failure can reject separately. Treating every exception as transient would erase
  integrity/authorization distinctions.
- OBSERVED: `JobWorkspace.tsx:346-374` executor output is on demand and currently
  clears its previous snapshot during load; its parent key includes state revision.
  Context prose describes richer output handling than this source. #71's integration
  status is UNKNOWN; never assume its future implementation is present here.
- OBSERVED: `ChatGptSignIn.tsx` serializes pending status reads against actions and
  bounds expiry; `TicketWorkspace.tsx` reads tickets/comments explicitly and uses
  2s polling only for active operations. No reason to add ticket polling was found.
- OBSERVED: `e2e/jobs.spec.ts:694-714` already uses a fake clock and held route to
  prove Overview stays visible then rejects malformed evidence. `e2e/statistics.spec.ts`
  provides analytical fixtures, sort, role, localization and themed checks;
  `e2e/audit.spec.ts:91-131` proves background filter/open-row retention and corrupt
  evidence hiding; `e2e/users.spec.ts:311-333` withholds grant editors after malformed
  initial/post-mutation reads. `e2e/settings-save.spec.ts` and `settings.spec.ts`
  cover guarded drafts/reviews. These tests were inspected, NOT executed.
- OBSERVED: active `REQ-UX-a24db609` governs Statistics evidence presentation;
  `REQ-UX-aa9f0f6c` governs compact period/export controls;
  `REQ-UX-b5485c02` governs Overview selector layout (its verification also names
  quiet polling but its normative clause is narrower);
  `REQ-UX-2eef4e79` governs authorized Overview navigation;
  `REQ-UX-9aea4d22` governs clean-only 15s Settings reads;
  `REQ-UX-42f35d04` governs notification lifecycle. None establishes the entire
  requested cross-view refresh contract. Specify must map atomic behaviors and
  preserve these existing contracts rather than broaden unrelated requirements.
- OBSERVED: `git status --short` was clean at entry; AEGIS status/brief/components
  succeeded. No visual reproduction, implementation test, live acceptance or timing
  measurement was performed. `rg` was unavailable (exit 127); ordinary grep/read
  supplied the inspection instead, without environment or repository changes.

### Assumptions

- INFERRED (#77's source-investigation caveat and current source findings): the
  defect is sufficiently grounded to frame implementation, but no deployed-browser
  reproduction or performance claim follows from reading code.
- INFERRED (#77 requirement 7 and existing authority guards): informational stale
  display is separable from action authority. It cannot be applied mechanically
  to Users grants, Access, configuration, approvals or operational job controls.

### Unknowns

- UNKNOWN: deployed visual reproduction, measured latency, and accessibility/scroll
  outcomes until offline behavioral proof is added and run at build/validate.
- UNKNOWN: complete atomic requirement mapping, any conflicting normative stale-read
  clause elsewhere in the register, and exact existing error taxonomy needed for
  transient handling; specify must inspect and resolve against #77's explicit
  authorization to change informational failure behavior, preserving other guards.
- UNKNOWN: exact timeout/cancellation mechanism, freshness aggregation for a coherent
  multi-resource report, DOM placement/copy and accessibility announcement strategy;
  resolve in specify/design within stated requirements, not by inventing API/schema
  behavior in frame. Initial/malformed/auth failures remain explicitly constrained.
- UNKNOWN: #71/#66 branch contents and integration order. Reinspect relevant source
  before implementation; do not rewrite executor-output internals or infer features
  from knowledge prose alone. Current direct evidence presentation is already present
  in JobWorkspace and must be preserved.
- UNKNOWN: installed build/browser dependencies in the fresh build session; inspect
  and provision normally then. No installation is needed for frame.

### Decision-blocking questions

- INFERRED (explicit #77 requirements, repository rules and conductor authority):
  none at frame. The user has authorized the desired scope, failure boundaries and
  autopilot decision mode. Remaining implementation/verification details belong to
  later stages; no human choice or child task is required to frame this work.

### Proposed behaviors

- INFERRED, NOT ACCEPTED as implementation decisions: a narrow shared refresh/read
  lifecycle may serve the continuity, freshness, cancellation and coalescing success
  signals without replacing all fetching. Alternatively resource-local guarded
  readers may suffice. Design chooses after atomic requirements are specified.
- INFERRED, NOT ACCEPTED as an error-policy decision: retaining only positively
  classified transport failures for informational reads is a conservative candidate
  for #77 requirement 7; unclassified/malformed/auth/snapshot errors would fail closed.
  Specify/design must define the public behavior and prove action guards separately.
  No new HTTP status, timeout number, format or stale-approval rule is selected here.

### Path and reason

STATED (conductor): use exactly one pinned task and stop after frame. INFERRED
(from the criterion evidence below): choose **full**, retaining `path: full`;
quick would skip necessary reporting-coherence, failure and authority contracts.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | STATED #77 requirements 7-8 add informational stale/freshness/retry behavior and explicit Refresh on affected informational views. |
| no new interface or data format | no | STATED #77 requirement 8 adds visible Refresh/retry and completion-time feedback; no stored/API format change is requested. |
| no new dependency | yes | INFERRED from existing React/Node/Playwright tooling and focused scope; none is proposed or needed for frame. |
| an existing requirement already covers the behavior | unknown | OBSERVED inspected contracts cover reporting/Overview/Settings subsets, not the complete cross-view lifecycle. Atomic mapping belongs to specify. |
| no security or data-handling change | no | STATED #77 permits narrowly retained informational snapshots after transport failure while requiring immediate authority invalidation and coherent reporting replacements. |

STATED (conductor): no child journal is permitted. INFERRED (shared cross-view
lifecycle/authority invariants): this remains one integrated feature task, with
incremental implementation and offline proof rather than independently delivered
subtasks. Scope/path are recorded under explicit autopilot authority; frame makes
no implementation-completion or test-pass claim.

## Requirement coverage


## Design


## Log

- 2026-11-13 frame: journal opened
- 2026-11-13 frame: Frame records ticket #77 scope under conductor autopilot; full path selected for new Refresh/freshness behavior, coherent reporting and authority boundaries. Current checkout also clears periodic job detail (JobWorkspace.tsx:178-195), contrary to the historical inventory; include detail continuity within the requested scope. Executor-output source differs from richer context prose, so #71 integration remains unestablished and must be rechecked without redesigning it.
- 2026-11-13 frame: completed; next specify - Frame complete under explicit conductor autopilot: scope recorded, no blocking question, full path justified; stop at this stage boundary.

## Rulings


## State

status: ready
reported: frame - completed
next: start specify: read .agentic/steps/2_specify.md
must_read: .agentic/tasks/TASK-5b9207ee.md, .agentic/steps/2_specify.md
changed: Only .agentic/tasks/TASK-5b9207ee.md: legal prologue, evidence-labelled frame, complete scope/limits/unknowns, full-path criteria and completed frame checklist; product unchanged.
evidence: status/brief/components exit 0; current branch matches journal; check --task TASK-5b9207ee --full exit 0 (0 errors, 35 warnings, 29 notes); git diff --check exit 0; implementation tests not run in frame.
issues: Repository-wide advisory warnings remain outside this change; task has only the expected pre-build no-anchor note. Job detail also blanks in this checkout; #71 integration is unknown and must be rechecked. No frame blocker.
spec_compliance:
implementation_quality:
review_round:
