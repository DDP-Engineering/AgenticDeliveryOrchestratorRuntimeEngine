<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-ab986d26 - Reconcile retained E2E ticket navigation after LA integration

stage: done
type: change
path: quick
interaction: autopilot
requirements: REQ-UX-b359952f, REQ-UX-7cc76f30, REQ-UX-8c280c24, REQ-UX-97054d74, REQ-UX-1141c28f, REQ-UX-c000471e, REQ-UX-c90fece3, REQ-FUNC-ff3e4560, REQ-REL-329421d1
parent:
branch: master
base: b8fa9171942f66048166d66bfbbf2c8cc167314c
opened: 2026-11-14

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [x] diff reviewed against scope, requirements, design, error paths,
      portability, security and unrequested work
- [x] knowledge pages of changed components current with the reviewed code
- [x] project and environment context reconciled with the candidate
- [x] requirements re-read: status, prose, verification, paths and links true
- [x] manual or inspection verification recorded where applicable
- [x] explicit review approved, when enabled
- [x] final `check --strict --run` result logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem: STATED (parent follow-up): integrated Chromium runs still find retained E2E flows using the old global combined Jobs/Tickets interface. OBSERVED: dashboard.spec.ts:168 enters global Jobs then requests Read tickets; shell.spec.ts:377 expects Tickets as a global Jobs sub-tab.
Desired outcome: STATED: minimal test/fixture corrections follow the implemented interface while preserving functional, authorization, worker, evidence and Projects assertions.
Actors: STATED: parent coordinator controls the source freeze/full validation; this child prepares and later performs bounded targeted repairs/review/local commit.
Primary scenario: STATED: collect every current integrated result, release the edit hold, repair confirmed stale test navigation/selectors once, run only affected cases, independently review and commit on master.
Examples: OBSERVED: developer worker Start44 still asserts HTTP200, durable operation success, invalid-ticket400, engine-rejected failure and idempotent replay. These assertions must remain.
Counterexamples: STATED: a project hub's /projects/<id>/jobs Tickets sub-tab remains correct; global Jobs history/capacity navigation remains correct. No product or Projects redesign is permitted.
In scope: STATED: read-only inventory now; own AEGIS frame preparation. After explicit hold release: confirmed test/fixture-only repairs, targeted checks, required review, local commit and scoped traceability records.
Out of scope: STATED: changes to product/frontend/production assets during the hold; changes to correct product behavior, full suites, active-server interference, push/deploy. Do not weaken assertions. STATED (parent clarification): if all failures are retained browser fixtures, keep repairs in those fixtures and AEGIS evidence so fresh full Python and native-runtime proof remains applicable to unchanged product/Python inputs.
Constraints: STATED: fresh released-edit budget45minutes,30tracked files,3repair rounds per failing targeted check; existing master checkout only. OBSERVED: clean master at b8fa9171942f66048166d66bfbbf2c8cc167314c before journal creation. Parent full Python and339-Chromium runs own all current verification and the active fixture server.
Success signals: STATED: all confirmed stale selectors corrected after collected outcomes; original assertions retained; affected targeted cases pass; independent review and local commit leave clean master.
Evidence: OBSERVED: comprehensive rg over all web/e2e TypeScript routes, sidebar labels, project selectors, ticket tables/read buttons and legacy detail-tab selectors; source App.tsx and current requirements inspected. No test or service command ran during hold.
Assumptions: INFERRED: existing requirements already establish the correct behavior, so this is quick-path test repair, not a new product contract.
Unknowns: UNKNOWN: final full Python result (parent-owned). STATED: diagnostic browser run was interrupted/failed, not a completed proof. Parent released the edit hold with confirmed dashboard/issue37/jobDetails failures and the read-only inventory. STATED (parent clarification): use the actual shared #jobs-project on global Tickets; the proposed #tickets-project name was an assumption and no product selector rename is authorized. OBSERVED: current App.tsx:1494 shares #jobs-project across both pages. Reinspect the released checkout before edits.
Decision-blocking questions: none. STATED: parent released the browser-fixture edit hold, stopped the owned listener/runner and authorized only affected E2E fixtures and AEGIS evidence; Python/product/web/src/assets/packaging remain frozen.
Proposed behaviors: none; no product behavior changes accepted or proposed.
Path and reason: quick, existing requirements cover test-only reconciliation.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | yes | STATED tests/fixtures only |
| no new interface or data format | yes | OBSERVED existing global pages and compact detail |
| no new dependency | yes | INFERRED existing Playwright seams suffice |
| an existing requirement covers behavior | yes | OBSERVED REQ-UX-b359952f/7cc76f30/8c280c24 |
| no security or data-handling change | yes | STATED auth/worker assertions and product stay intact |

### Read-only inventory and proposed repair map

1. dashboard.spec.ts:163 worker processes queued requests: change ONLY its ticket-workflow sidebar target Jobs to Tickets; keep the actual scope selector, explicit Read tickets and wait for read completion before choosing Start44. Preserve all operation/validation/engine-rejection/idempotency assertions. The earlier Jobs route/back test at140 is valid and stays.
2. shell.spec.ts:362 localized assigned developer: keep global Jobs scope/role/overflow/theme assertions, replace the invalid global Tickets sub-tab expectation with the actual Jobs/Capacity tabs, and exercise the separate Tickets entry with the same assigned/all scope restrictions. Reuse mobile-menu behavior. Final parent failures decide the smallest assertion/fixture correction; no auth assertion is removed.
3. Adjacent confirmed legacy detail selectors awaiting parent result: jobDetails.spec.ts:39/42/44 uses Agent question/Technical details tab names;72/101 uses removed .job-state;102 incorrectly treats disappearance of the old Agent question tab as resumed-question removal. Use Artifacts/Technical information, saved .job-detail-meta .status, and verify actual active-question content/action disappearance while retaining history, source/HTML safety, focus/keyboard and close-state checks. No product change.
4. statistics.spec.ts:328-329 uses Technical details for the job-detail tab/panel; use Technical information while retaining its consumption/diagnostic assertions.
5. issue37.spec.ts:9 (parent-reported primary timeout): retain the existing four locales x two viewports, monitoring activation/pause, epic Start-disabled, readable Details and overflow assertions. OBSERVED: one test currently shares the global30s body budget, and its finally block restores English by browser navigation inside that same expired budget. There is no file-level cleanup hook. The later52/78/103 English-locator failures are STATED parent-observed locale contamination, not established product regressions.
   Proposed minimal repair after release: a finite90s per-test budget for this eight-scenario matrix, leaving the global suite, action, navigation and assertion limits unchanged; move authoritative locale cleanup to a file-scoped afterEach hook using authenticated API GET /me and CSRF PATCH /me/preferences to en/light, with bounded requests and checked results. Keep UI locale-selection assertions in the test. Existing statistics.spec.ts:22-31 and projectCapacity.spec.ts:29-33 establish the local API cleanup pattern. Playwright's official timeout contract (https://playwright.dev/docs/test-timeouts, inspected2026-11-14) gives afterEach/fixture teardown a separate timeout budget after the test body, unlike the current finally navigation.
   Isolation verification after release: run the entire issue37 file in order so every formerly cascading English case executes after the complete matrix; inspect the account preference through the fixture only during authorized targeted proof. Consider a narrowly controlled failure/timeout cleanup experiment if needed to establish the teardown boundary, without committing a deliberately failing test. Do not translate or weaken the downstream English expectations, drop matrix cases, or modify product/Python inputs.


Retained valid flows: help/issue37/tickets project-hub Reads and Jobs tabs; global Jobs history/capacity/deep links in jobs/shell/statistics/driftRecovery; Settings/portable Technical details refer to configuration, not job-detail tabs. Do not bulk-replace labels.
Coverage gaps rather than failures: shell navigation/empty-grants page arrays currently omit the new separate Tickets entry; add only if included in the released minimal repair scope, retaining their existing assertions.

### Proposed bounded proof after hold release

Run only parent-confirmed affected Playwright cases in dashboard/shell/jobDetails/statistics/issue37, with the existing offline fixture and after confirming the parent's server is stopped. Include typecheck for changed TS test syntax if needed. No build or production fingerprint regeneration is needed when only E2E files change. Keep issue37 cleanup local to the fixture rather than change shared production locale behavior or suite-wide timeouts. Use two independent AEGIS reviewers, report every remaining failure, and commit locally only after targeted proof/review.

## Requirement coverage

| Existing behavior | Requirement | Candidate test seams |
|---|---|---|
| Separate global Jobs/Tickets with authorized scope | REQ-UX-b359952f | dashboard/shell |
| Automatic and manual ticket reads with retained actions | REQ-UX-7cc76f30 | dashboard/shell |
| Four compact detail tabs, saved status and retained evidence | REQ-UX-8c280c24 | jobDetails/statistics |
| Responsive epic actions and monitoring | REQ-UX-97054d74 / REQ-UX-1141c28f | complete issue37 matrix |
| Existing empty-state, queue, confirmation and worker contracts remain isolated | REQ-UX-c000471e / REQ-UX-c90fece3 / REQ-FUNC-ff3e4560 / REQ-REL-329421d1 | subsequent issue37 cases |


## Design

No new interface or runtime design. Proposed changes attach existing assertions to current navigation and evidence seams; test edits are released; product/Python/assets remain frozen. Scope is five E2E fixture files plus AEGIS evidence; no production asset rebuild.


## Log

- 2026-11-14 frame: journal opened
- 2026-11-14 frame: Read-only inventory: confirmed stale dashboard global Jobs-to-Read-tickets flow and shell global Tickets-subtab assertion; adjacent legacy jobDetails/statistics detail selectors identified. Current App shares #jobs-project across global pages; no #tickets-project exists. No source edits, suite/test runs, server interaction or Git publication performed.
- 2026-11-14 frame: Parent diagnostic: issue37 four-locale/two-viewport matrix times out at30s and its same-budget finally cleanup is cancelled, leaving ro and cascading English-locator failures. Source confirms no afterEach hook; existing statistics/projectCapacity fixtures use authenticated API cleanup. Proposed finite per-test90s plus local afterEach API preference reset; preserve every functional assertion. Official Playwright timeout docs confirm separate afterEach teardown budget. No tests/server/source edits performed.
- 2026-11-14 frame: completed; next build
- 2026-11-14 build: red: parent interrupted full Chromium run found dashboard Read tickets missing under Jobs, jobDetails Agent question tab/.job-state missing, issue37 matrix timed out30s leaving ro; failure artifacts read before repairs. Shell global Tickets-subtab and statistics Technical details are independently observed stale oracles. No passing full-run claim.
- 2026-11-14 build: green: targeted Playwright dashboard:163 shell:362 jobDetails issue37 statistics:315 exit0;13 passed across all affected journeys, every issue37 English case after full four-locale/two-width matrix. Initial typecheck exit0.
- 2026-11-14 build: Isolation experiment: temporary cleanupProbe imported actual issue37 afterEach; saved and observed ro/dark, deliberately exhausted8s body budget (expected exit1), then separate test confirmed en/light through UI and GET preferences (passed). Teardown succeeded after timeout. Temporary spec removed; diagnostic is NOT a green suite claim.
- 2026-11-14 build: release-notes: none (test-only fixture corrections; no product, CLI, settings or user behavior change)
- 2026-11-14 build: help: none (test-only fixture corrections; existing product/help contracts unchanged)
- 2026-11-14 build: Inspection: retained working title/meta alignment assertions verbatim. Preserved original Jobs overflow/screenshots and added separate Tickets scope/overflow/screenshots. Only5 E2E fixtures plus AEGIS traceability/knowledge/journal differ from base; Python, web/src, assets and packaging inputs unchanged.
- 2026-11-14 build: green: Playwright jobDetails:27 shell:362 exit0;2 passed after preserving the original meta geometry and Jobs overflow/screenshot assertions; added Tickets coverage retains assigned/all-authorized scope and both themes/widths. No failed targeted repair rounds.
- 2026-11-14 build: completed; next validate
- 2026-11-14 validate: Validation inspection: every requirement diff changes only affected_paths/linked_tests/updated; all existing contract prose and active status retained. Web-interface knowledge records fixture navigation and timeout isolation; project/environment guidance and 01/05 component docs require no change because runtime/interfaces/commands are unchanged. Scope assertion confirms only5 E2E fixture files plus AEGIS evidence.
- 2026-11-14 validate: Advisory check exit0:0errors/71warnings/28notes.70 existing repository findings remain outside fixture scope; one source-no-test-changes heuristic classifies web/e2e as source because configured tests roots cover web/tests, despite5 actual Playwright specs changed. No product or test-coverage defect follows from that classification.
- 2026-11-14 validate: DEVIATION validate: omit check --strict --run and full suites per parent standing instruction; prove this fixture-only candidate with13 affected offline Chromium journeys,typecheck,diff/style and strict AEGIS metadata check. Does not prove339-browser/full-Python suites; parent owns those outcomes.
- 2026-11-14 validate: Independent review round1 approved in both roles by spec_review and quality_review; no findings. Both inspected current fixture/AEGIS diff and preserved contracts; neither ran tests or servers. Final proof follows approvals.
- 2026-11-14 validate: final: playwright test e2e/dashboard.spec.ts:163 e2e/shell.spec.ts:362 e2e/jobDetails.spec.ts e2e/issue37.spec.ts e2e/statistics.spec.ts:315 exit0,13passed in2.0m after both review approvals; npm --prefix 04_Software/web run typecheck exit0; git diff --check exit0; python .agentic/aegis.py check --task TASK-ab986d26 --strict exit0,0errors/71warnings/28notes,strictok. Warnings:70 existing repository findings plus e2e-as-source heuristic; no candidate defect. Full --run deliberately omitted per parent; no product/Python/assets change and no full339 claim.
- 2026-11-14 validate: completed; next done

## Rulings

- RULING-001 | date=2026-11-14 | decision=Keep all source/tests/frontend/assets immutable until parent releases the full-suite edit hold | reason=Parent explicitly authorizes only read-only inspection and own AEGIS frame preparation now; later bounded targeted test/fixture repair and local commit on master follow collected final outcomes | source=user | supersedes=none
- RULING-002 | date=2026-11-14 | decision=Use the existing shared #jobs-project on global Tickets and preserve product/Python inputs during fixture repair | reason=Parent explicitly withdrew the assumed #tickets-project name, forbade product selector/UI changes and retained the read-only hold pending complete suite outcomes | source=user | supersedes=none
- RULING-003 | date=2026-11-14 | decision=Release E2E fixture repair on master while all product/Python/frontend source/assets/packaging inputs stay immutable | reason=Parent stopped the owned failed browser fixture and runner, freed18765 and authorized targeted affected journeys, independent review and local fixture-only commit; fresh45min/30files/3repair-round bounds | source=user | supersedes=RULING-001


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-ab986d26.md
changed: Five E2E fixtures plus AEGIS evidence;product/Python/assets/packaging unchanged
evidence: Final13 affected Chromium cases passed;TypeScript,diff check,strict AEGIS exit0;independent reviews approved round1
issues: Full suites excluded by parent;71 advisory warnings accepted;diagnostic full Chromium run failed/interrupted and proves no full pass
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-11-14)

- stage: validate; type: change; path: quick; branch: master
- requirements:
  - REQ-UX-b359952f - Separate global Jobs and Tickets
  - REQ-UX-7cc76f30 - Read global tickets on entry and scope change
  - REQ-UX-8c280c24 - Keep compact saved job details
  - REQ-UX-97054d74 - Keep ticket actions accessible at narrow widths
  - REQ-UX-1141c28f - Show observed monitoring operation results
  - REQ-UX-c000471e - Offer useful project empty states
  - REQ-UX-c90fece3 - Explain worker availability and queue waits
  - REQ-FUNC-ff3e4560 - Require explicit confirmation for cancellation
  - REQ-REL-329421d1 - Scoped worker readiness diagnostics
- deviations: 1 recorded
  - validate: omit check --strict --run and full suites per parent standing instruction; prove this fixture-only candidate with13 affected offline Chromium journeys,typecheck,diff/style and strict AEGIS metadata check. Does not prove339-browser/full-Python suites; parent owns those outcomes.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base b8fa917: 16 file(s) changed, 210 line(s) added
- checks: errors=0 warnings=71 notes=28
- checklist: 8/9 done; open: `report` appended
