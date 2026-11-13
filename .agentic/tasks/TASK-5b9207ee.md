<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-5b9207ee - Keep automatic page refresh unobtrusive and preserve view state across the web interface

stage: design
type: feature
path: full
interaction: autopilot
requirements: REQ-UX-257ab3f0, REQ-UX-b0b59a64, REQ-UX-1b17b3d6, REQ-UX-aabda516, REQ-UX-cefdebe1, REQ-UX-f88b9ce5, REQ-UX-046922f1, REQ-UX-013bb10e, REQ-UX-9f1ec9fa, REQ-DATA-d535499a, REQ-REL-30db8e42, REQ-UX-b6f7f1ad, REQ-UX-ba04c883, REQ-UX-0acb39f1, REQ-SEC-7ee58549, REQ-SEC-15563e41, REQ-UX-0bd9d921, REQ-REL-066eb19a, REQ-REL-f3164557, REQ-REL-207a1588, REQ-REL-94454aa2, REQ-REL-7802903f, REQ-REL-9e0b2628, REQ-NFR-da638732, REQ-REL-76ed3e49, REQ-NFR-86b6abde, REQ-UX-25f45e27, REQ-UX-3184cc48, REQ-UX-183b80f6, REQ-UX-cbca5fd9, REQ-SEC-b6a74dea, REQ-UX-9aea4d22, REQ-UX-1df0b1ce, REQ-UX-d64b7511, REQ-UX-6f7688d6, REQ-SEC-6d0b0125, REQ-UX-1141c28f, REQ-FUNC-fbf7b13f, REQ-UX-aba6daa0, REQ-UX-06c5535b, REQ-REL-12a357a9, REQ-REL-a5c94449
parent:
branch: adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-77
base: bafae7e55bbcfda18451ee621368204af9dd864b
opened: 2026-11-13

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [ ] design note written under the five headings, or its skip justified
- [ ] each decision cites a requirement ID or a named technical constraint
- [ ] every requirement maps to a decision and test seam, or no design impact
- [ ] risks and open decisions recorded
- [ ] `affected_paths` match the expected files
- [ ] knowledge pages unchanged

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

### Specify bounds and evidence

- STATED (current conductor instruction): this session performs **specify only**,
  under existing `interaction: autopilot`; advance once when complete and stop at
  the stage boundary. The Frame's frame-only limits above describe its past session,
  not permission to start design/build here.
- STATED (this executor's run bounds): at most 45 ticket-scoped `.agentic/` files
  edited, at most 35 new requirement records, two spec files, no product/dependency/test
  edits or implementation test runs, and a 45-minute wall-clock ceiling. Exhaustion
  before completion means log and pause the same task, never advance unfinished.
- OBSERVED (resume): branch matches the unchanged journal header; entry worktree is
  clean. Read installed task/requirement/spec authoring guides, project context,
  full web-interface knowledge, and `explain` for App, JobWorkspace, AuditHistory
  and browser polling. `polling.md` describes the Python conductor, not this seam.
- OBSERVED (source): `App.tsx` request wrapper and reporting readers, Users/config
  effect and operation completion, audit/access parent keys and ProjectAccess;
  `JobWorkspace.tsx` list/detail/consumption/output readers and keys;
  `AuditHistory.tsx` validated page reader and manual effect dependency;
  `polling.ts` timer/visibility behavior; TicketWorkspace explicit read versus
  operation polling; ChatGptSignIn pending-status/edit guards were inspected.
- OBSERVED (tests, not executed): Statistics scope/order/corruption and revoked-grant
  journeys, Jobs held Overview/background failure/snapshot cases, audit filtered
  expanded-row/stalled/corrupt cases, Users malformed initial/post-mutation reads,
  Settings dirty draft/revision/review cases and shell Access refresh were inspected.
  They establish existing patterns, not candidate behavior or successful execution.
- STATED (#77 requirements and accepted Frame): the rows below are proposed contracts
  and verification obligations. New and deliberately revised records are **draft**;
  reused records remain active. INFERRED: sharing one cross-view contract per atomic
  behavior is sufficient; duplicating one requirement per timer/screen is unnecessary.
  Verification names representative cross-view fixtures and negative boundaries,
  with the surface matrix below preventing accidental omission.

### Atomic behavior mapping

Each row has exactly one requirement. The final column is reserved for design;
no design decision or implementation completion is claimed in this stage.

| Frame outcome | Atomic behavior | Requirement | Verification | Design decision or no impact |
|---|---|---|---|---|
| Initial/context loading | Pending read without a validated current-context snapshot shows scoped loading, not previous-context evidence. | REQ-UX-257ab3f0 (revised draft) | Hold first/context reads; assert loading and absent old totals/exports; same-context control retains content. | Pending design |
| Honest empty state | Validated no-record/no-match success shows explicit empty feedback. | REQ-UX-b0b59a64 (new draft) | Return empty after initial and populated reads; malformed/failed controls never become empty success. | Pending design |
| Quiet pending refresh | A same-context reread keeps the validated rendered snapshot while in flight. | REQ-UX-1b17b3d6 (revised draft) | Hold automatic/manual/operation reads across affected views, including every Statistics tab and Users. | Pending design |
| Refresh progress distinct | A same-context reread exposes nonblocking progress without initial-loading replacement or automatic announcement churn. | REQ-UX-aabda516 (new draft) | Hold automatic/manual rereads, inspect localized accessible progress with content retained; resolve unchanged and distinguish first loading. | Pending design |
| Actual changes visible | A changed validated replacement updates surviving values in place. | REQ-UX-cefdebe1 (new draft) | Resolve changed fixtures; assert intended values change without whole-view loading or lost row identity. | Pending design |
| Unchanged success quiet | An unchanged success causes no loading/collapse or repeated loading announcement. | REQ-UX-f88b9ce5 (new draft) | Held unchanged fixtures and DOM/live-region observation; changed-value control remains observable. | Pending design |
| View state stable | Same-context revalidation preserves table controls, valid paging, open job/disclosures/export. | REQ-UX-046922f1 (new draft) | Nondefault Usage/Jobs/History page size/page/sort and open sections survive ticks, Refresh and operation completion; real context change is distinct. | Pending design |
| Reading uninterrupted | Surviving focus, selection and scroll remain continuous. | REQ-UX-013bb10e (new draft) | Capture focused DOM control, clarification/output selection and page/local offsets through held/unchanged/changed reads. | Pending design |
| Scope never mislabeled | A reporting-context change displays only evidence and exports bound to the selected authorized server scope. | REQ-UX-9f1ec9fa (reused active) | Switch project/dates/URL timezone/group/authorization in flight; old scope never appears under new controls. | Pending design |
| Coherent Statistics | Publish only a complete validated coordinated metrics/usage reporting generation. | REQ-DATA-d535499a (new draft) | All tabs/global modes/project hub, independent arrival orders and malformed/mismatched/generation rejection; see linked spec. | Pending design |
| Irrelevant reads isolated | Selected-project readiness does not depend on unrelated all-project requests. | REQ-REL-30db8e42 (new draft) | As Admin hold/fail unrelated global usage while valid selected inputs complete; selected failure still prevents ready. | Pending design |
| Initial failure explicit | First/context read failure exposes error without old evidence or false zero. | REQ-UX-b6f7f1ad (new draft) | Fail initial and changed-context resource reads, inspect absent old totals/exports/success time, retry valid. | Pending design |
| Transport failure informative | A positively classified same-context transport/deadline failure retains only a marked stale snapshot with last success and retry. | REQ-UX-ba04c883 (new draft) | Abort/expire after success; retained information is visibly stale; initial/auth/corrupt/snapshot failures do not qualify. | Pending design |
| Recovery explicit | Successful complete recovery returns the informational view to ready without resetting controls. | REQ-UX-0acb39f1 (new draft) | Retry/tick after stale failure; unchanged/changed valid success clears stale, partial or repeated failure does not. | Pending design |
| Invalid evidence refused | Malformed/corrupt/integrity or scope-invalid informational evidence hides affected evidence and dependent exports/actions. | REQ-SEC-7ee58549 (new draft) | Inject JSON/media/type/foreign-scope/provenance/corrupt errors after good data; observe fail closed, not stale retention. | Pending design |
| Authorization never retained | Detected session/account/role/grant loss removes no-longer-authorized evidence and actions immediately. | REQ-SEC-15563e41 (new draft) | Hold privileged reads across sign-out/account switch/revocation/password transition; old completions reveal nothing. | Pending design |
| Removed item explicit | A legitimately vanished identity uses explicit unavailable/removal/safe navigation rather than silent substitution. | REQ-UX-0bd9d921 (new draft) | Remove selected project/job/account/expanded row; archive control retains historical identity with restricted actions. | Pending design |
| Incomplete jobs fail closed | Incomplete jobs evidence outside validated Overview isolation hides affected list/totals/detail and offers existing reload. | REQ-REL-066eb19a (new draft) | Complete-to-incomplete fixture rejects; validated Overview unreadable-project isolation remains intact. | Pending design |
| Paging integrity retained | Snapshot conflict hides the conflicting jobs page and requires explicit reload from zero. | REQ-REL-f3164557 (new draft) | Hold nonfirst-page continuation, return snapshot conflict, inspect reload then offset-zero request. | Pending design |
| No old completion wins | Superseded read completion cannot modify data, feedback or success time. | REQ-REL-207a1588 (new draft) | Release older success/error after new scope, mutation, timeout/retry, account or unmount. | Pending design |
| Bounded overlap | Same-resource/context triggers share serialized/coalesced work. | REQ-REL-94454aa2 (new draft) | Hold read through ticks, duplicate Refresh, visibility and operation completion; max one concurrent read and no release burst. | Pending design |
| Slow reads end | Finite read deadline releases the slot into the appropriate failure state. | REQ-REL-7802903f (new draft) | Hold beyond declared deadline, inspect initial-error versus stale, then successful retry; late response cannot publish. | Pending design |
| Ownership ends on exit | Navigation/context invalidation/sign-out/unmount cancels owned reads and scheduling. | REQ-REL-9e0b2628 (new draft) | Observe abort/stop, advance clocks/release old response, assert no obsolete read/publication/focus side effect. | Pending design |
| Hidden tab quiet | Hidden page starts no periodic refresh request. | REQ-NFR-da638732 (revised draft) | Hide loaded polling views across intervals; count zero new periodic requests, distinguish already-in-flight completion. | Pending design |
| Visible return bounded | Visible return requests one immediate eligible coalesced revalidation and normal cadence. | REQ-REL-76ed3e49 (new draft) | Hide/show plus repeated events/held reads; one request/resource, dirty Settings/mutation guards still hold. | Pending design |
| Cadence preserved | Existing nominal resource intervals and finite operation/sign-in eligibility remain unchanged. | REQ-NFR-86b6abde (new draft) | Fake-clock counts at interval boundaries; completed operation/sign-in stops, no ticket reads, slow work coalesces. | Pending design |
| Explicit informational refresh | Statistics/Jobs/History/detail/consumption controls use the same non-remounting read path. | REQ-UX-25f45e27 (new draft) | Held manual Refresh/retry and duplicate clicks retain state; initial retry works and invalid result fails closed. | Pending design |
| Audit manual refresh | Both change-evidence scopes offer same-query non-remounting Refresh/retry. | REQ-UX-3184cc48 (revised draft) | Hold manual reread with filters/page/disclosure/draft/focus; one current-query request, corrupt completion hides table. | Pending design |
| Users remains manual | Header Refresh and its time remain exclusive to Administration Users. | REQ-UX-183b80f6 (reused active) | Shell header control/time exists on Users and not automatic-view headers; informational in-view controls are separate. | Pending design |
| Honest success time | Freshness time records successful validated completion, never request start/failure/partial/ignored result. | REQ-UX-cbca5fd9 (new draft) | Controlled clock around held/failing/unchanged/recovery reads; report time cannot precede complete required success. | Pending design |
| Stale is not action authority | Retained informational snapshots cannot enable/confirm/submit evidence-dependent privileged or operational mutations. | REQ-SEC-b6a74dea (new draft) | Stale actionable detail blocks dependent mutations until current authority, without conflating independent usage with action evidence. | Pending design |
| Settings guards preserved | Visible Settings reads every 15s only while clean, ignoring reads superseded by edits. | REQ-UX-9aea4d22 (reused active) | Hold old config/prices through setting/credential/model/sign-in drafts and mutation; draft wins and clean polling resumes. | Pending design |
| Access mutation serialization | Access reads every 15s cannot replace confirmed updates with older reads. | REQ-UX-1df0b1ce (reused active) | Hold old list through a grant mutation; confirmed result survives and fresh later read still updates. | Pending design |
| Audit cadence/state preserved | Current audit page rereads every 15s while preserving filters and expanded evidence. | REQ-UX-d64b7511 (reused active) | Global/project filtered expanded rows survive background update; stalled/cross-project/malformed controls reject safely. | Pending design |
| Valid reviews survive | Unchanged/unrelated successful refresh preserves still-valid Settings/Access/Users/ticket forms, dialogs, reviews and drafts. | REQ-UX-6f7688d6 (new draft) | Hold confirmation/dialog through unchanged relevant and unrelated operation/metadata reads; no close or overwrite. | Pending design |
| Changed review authority invalid | Changed identity/grant/state/revision/action precondition prevents old review submission. | REQ-SEC-6d0b0125 (new draft) | Alter relevant authority under open review, assert no old submit; unchanged control persists, older read cannot restore invalid authority. | Pending design |
| Operation completion revalidates | Finished monitoring operation rereads displayed project state from its observed result. | REQ-UX-1141c28f (reused active) | Successful/failed queued outcomes update affected state without using progress as success; unrelated valid views remain preserved by the continuity rows. | Pending design |
| Tickets stay on demand | Metadata and queued-operation polls do not fetch forge ticket/comment bodies. | REQ-FUNC-fbf7b13f (new draft) | Explicitly open ticket/comments then tick metadata/operations/visibility; no extra forge reads or lost bodies/confirmations. | Pending design |
| Output remains manual/stable | Valid bound output survives parent refresh without new output reads or changed integrity handling. | REQ-UX-aba6daa0 (new draft) | Open/focus/scroll manual output, refresh parent; no output request/reset; changed binding still uses established conflict/unavailable behavior. | Pending design |
| Localized/themed feedback | New refresh/freshness states and controls work in four locales and both themes. | REQ-UX-06c5535b (new draft) | Copy contracts and desktop/390px keyboard browser states for ready/refresh/stale/retry without repeated loading announcement. | Pending design |
| Noninformational failure remains closed | Failed authority-bearing reads withhold affected evidence and dependent mutations. | REQ-REL-12a357a9 (new draft) | Initial/manual/post-mutation Users/Access/config failures withhold evidence/authority while preserving unrelated drafts. | Pending design |
| Other informational failures closed | Nontransport application/unclassified failures outside the specific error cases hide affected evidence rather than guessing transient retention. | REQ-REL-a5c94449 (new draft) | Return typed nontransport, unknown HTTP code and unclassified errors after success; affected totals/exports disappear, transport control is distinctly stale. | Pending design |

### Refresh inventory to verification routing

STATED (#77 inventory/acceptance): every listed surface is covered, including
already-smooth behavior. OBSERVED paths below are the existing fixture locations;
build may add a focused shared refresh suite instead of redundant tests per timer.
All proof stays offline. This matrix refines the rows above, not extra requirements.

| Surface and context | Contracts emphasized | Existing offline proof entry points / added scenario obligation |
|---|---|---|
| Global Statistics all-project comparison, global one-project filter, Project Statistics; Summary/Usage/Quality/Trends | Report coherence, context, pending/unchanged/changed/stale/recovery, view/focus/time | `web/e2e/statistics.spec.ts`, `web/tests/statistics.test.mjs`, `metrics.test.mjs`; all tabs, independent response order, multi-page sort/page-size/page, export disclosure, irrelevant global hold. |
| Global/project Jobs and project job History | Pending/changed, controls/focus, consumption, paging/incomplete, authority/time | `web/e2e/jobs.spec.ts`, `statistics.spec.ts`, `web/tests/jobs.test.mjs`; held list/usage, active detail/sections, snapshot conflict with explicit zero-page reload. |
| Job detail, clarification, timeline, executor output | Detail continuity, focus/scroll/selection, manual output, stale/action separation | `jobs.spec.ts` and `shell.spec.ts` detail/operational cases; correct the observed detail clearing, retain saved workflow/direct evidence; reinspect output binding before build. |
| Overview, Project Summary, directory/shared selector | Pending/unchanged/changed, context, removal/archival/grants, bounded reads | `jobs.spec.ts` Overview/Summary/host-check ordering and `shell.spec.ts`; rows/links and disclosures remain stable, inaccessible identities disappear, valid unreadable-project isolation stays intact. |
| Global Change history and project audit evidence | Audit periodic/manual, controls/focus, stale/error/time | `audit.spec.ts`; hold same-query manual read with expanded row, unapplied draft, nonfirst page/size and focus; both scopes now supplement auto with local Refresh. |
| Settings including prices/credentials/model | Clean-only reads, draft/review preservation, authority errors/revision invalidation | `settings.spec.ts`, `settings-save.spec.ts`, executor-config journeys; old polls and operation completion cannot overwrite edits or close a valid confirmation; stale/corrupt candidates cannot submit. |
| Project Access | Serialized mutation, pending/unchanged review, invalidation/fail-closed | `shell.spec.ts` Access journey and `users.spec.ts` review cases; held reads cannot overwrite writes, unchanged reviewed authority/focus persists, changed grant/disabled state invalidates. |
| Administration System status | Pending/in-place success, cadence/hidden, explicit unavailable/error | `shell.spec.ts` plus existing readiness/storage tests; hold healthy reads without blanking the screen, retain worker-unavailable/storage-error semantics rather than applying blanket informational stale retention. |
| Administration Users | Manual header, pending/state/focus/time, authority failures/reviews | `users.spec.ts`, `shell.spec.ts`; same-context manual list hold preserves unrelated form/dialog, success time is completion-bound, failed/malformed list cannot enable grants. No Users periodic polling is added. |
| Global/project Tickets and operation tracker | Explicit forge reads, stable body/confirmation, operation cadence/context/authority | `tickets.spec.ts`, `jobs.spec.ts` queue cases; project/operation polls do not reread forge, unchanged reviews survive, changed authority invalidates, completion revalidates only affected data. |
| ChatGPT pending sign-in | Cadence eligibility, coalescing, draft/review and authority boundaries | `executor-config.spec.ts`, `chatgpt.test.mjs`; retain one serialized status read, pasted-address/mutation guards and finite 900-second expiry, with no page-wide remount/replacement. |
| App/Jobs/Tickets active operations and session/factory notice | Cadence/overlap, operation result, context/authority removal | Existing jobs/tickets/shell/account journeys; 2s tracking continues without blanket resets; applicable 15s session reads cannot retain previous account/reset data. |
| Explicit-only enrollment/import/connectivity/raw/portable/account/About/Help | No new polling; context ownership and unrelated draft guards | Existing respective suites plus request counts during shared-helper changes; keep action-specific loading and lifecycle. No new automatic reads merely for consistency. |

### Conflict review and challenge

- OBSERVED: `REQ-UX-257ab3f0` previously bundled pending/empty/failure and prohibited
  all stale totals. `REQ-UX-1b17b3d6` bundled pending/success with withholding on
  every failure. STATED (#77 requirements 1,7): revise these in place as draft
  atomic initial-loading and same-context-pending contracts; empty, success,
  transient failure/recovery and fail-closed errors now have separate rows/IDs.
  No historical requirement is retired or deleted.
- OBSERVED: `REQ-NFR-da638732` contained two shall clauses. The hidden clause is
  retained as a revised draft; visible return is its own new requirement with
  coalescing and guard constraints. This is atomic separation, not weaker cadence.
- OBSERVED: `REQ-UX-3184cc48` forbade project audit Refresh and existing tests assert
  its absence. STATED (#77 requirement 8): deliberately revise to offer local
  non-destructive Refresh/retry in both change-evidence scopes. Existing absence
  assertions must change in build; unrelated header placement remains governed by
  reused `REQ-UX-183b80f6` and is not broadened.
- OBSERVED: Statistics presentation spec universally hid evidence on loading/error.
  A clearly marked draft response-binding amendment now distinguishes initial/
  different-context, pending same-context, eligible transport failure and closed
  boundaries. Existing measurement/CSV/backend contracts are not changed.
- INFERRED (unequal stated cadence + coordinated-publication requirement): a
  reporting generation may explicitly pin a validated not-due committed input,
  never a due/pending/failed/incompatible input or opportunistic unrelated success.
  The new report spec spells out this protocol so retaining cadence cannot be
  misread as permission to mix unrelated request completions or fake source times.
- STATED (#77 requirement 7): informational transport retention is adopted for
  Statistics, Jobs/detail/consumption and audit, not mechanically extended to
  authority-bearing Users/Access/configuration/approvals or System status errors.
  INFERRED (request wrapper observed): only positively classified transport/owned
  deadline qualifies; arbitrary HTTP 5xx, parser exception or unclassified error
  fails closed. A navigation abort is cancellation, not a stale notice.
- INFERRED (row-by-row audit): pending retention, nonblocking progress, changed
  publication, unchanged quietness, control state, reading continuity and review
  validity are independent outcomes. Their shared test scenarios are not duplicate requirements. Scope
  binding differs from coherent multi-resource publication; hidden suppression
  differs from visible revalidation; action authority differs from stale display.
- OBSERVED: `AccountAccessEditor` is defined in `App.tsx`, not its own source file;
  affected paths name the actual source. No inferred new file is listed as existing.

### Assumptions, unknowns and handoff

- STATED: no scope expansion beyond the accepted Frame; no backend/API/stored
  schema, migration, forge/executor or payload change. Four-locale release notes,
  help, CHANGELOG, user/component documentation and committed asset rebuild remain
  build/validate obligations, not claims made by this stage.
- UNKNOWN until design: concrete resource ownership/coalescing and reporting
  generation implementation, deadline numbers outside existing bounded reads,
  freshness aggregation/placement and accessibility announcement mechanism. The
  spec constrains their observable behavior, including carried-input times;
  design must resolve these before build without weakening negative boundaries.
- UNKNOWN: output-conflict work from #71/#66 on other branches; this checkout's
  source remains authority. Preserve the established manual output/provenance
  behavior and avoid independent redesign; recheck before implementation.
- UNKNOWN: actual visual performance/accessibility and test results; no deployed
  reproduction or implementation test run is claimed. Installed build/browser
  dependencies are for a later fresh session to inspect.
- INFERRED (complete Frame-to-row and inventory audit): no decision-blocking
  question remains for specify. Design can proceed under conductor autopilot;
  shared UX/authority constraints justify one integrated task, not child journals.

## Design


## Log

- 2026-11-13 frame: journal opened
- 2026-11-13 frame: Frame records ticket #77 scope under conductor autopilot; full path selected for new Refresh/freshness behavior, coherent reporting and authority boundaries. Current checkout also clears periodic job detail (JobWorkspace.tsx:178-195), contrary to the historical inventory; include detail continuity within the requested scope. Executor-output source differs from richer context prose, so #71 integration remains unestablished and must be rechecked without redesigning it.
- 2026-11-13 frame: completed; next specify - Frame complete under explicit conductor autopilot: scope recorded, no blocking question, full path justified; stop at this stage boundary.
- 2026-11-13 specify: Specify completed: 42 ordered atomic coverage rows map to 32 new draft requirements, 4 deliberately revised draft contracts and 6 reused active contracts. The new reporting protocol and draft Statistics response-binding amendment distinguish pinned not-due inputs from unrelated generations while preserving 15/30-second cadence. Initial, transport-stale/recovery, invalid evidence, authorization, missing identity, incomplete, paging conflict, nontransport/unclassified and authority-bearing failure boundaries are separate. Project audit local Refresh deliberately replaces its prior prohibition; Users-only header placement remains unchanged. Complete inventory/regression routing and design unknowns recorded; no blocking question or product change.
- 2026-11-13 specify: completed; next design

## Rulings


## State

status: ready
reported: specify - completed
next: start design: read .agentic/steps/3_design.md
must_read: .agentic/tasks/TASK-5b9207ee.md, .agentic/steps/3_design.md
changed: Specify only: 32 new draft requirements, 4 deliberately revised draft contracts, 6 reused active contracts; 42 atomic coverage rows and full refresh-inventory verification routing; one reporting-generation spec and one draft Statistics response-binding amendment. All 39 changed files are task-scoped .agentic artifacts; product untouched.
evidence: check --task TASK-5b9207ee --json exit 0: 0 errors, 35 inherited warnings, 29 notes, no new findings; final inline Python artifact audit exit 0: 42 unique ordered IDs/rows, one shall each, valid paths/specs/legal headers and completed checklist; git diff --check exit 0. Implementation tests not run in specify.
issues: No specify blocker. Existing repository advisory findings unchanged. Design must settle concrete generation/coalescing ownership, finite deadlines and truthful localized freshness/progress placement; recheck executor-output integration before build. Stop at design boundary as instructed.
spec_compliance:
implementation_quality:
review_round:
