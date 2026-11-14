<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-ce36f131 - Isolate branch-settings browser restoration and cleanup

stage: done
type: fix
path: quick
interaction: autopilot
requirements: REQ-UX-7b47e30e
parent:
branch: master
base: 67f4f2809bcbac5a5099d30b252a260b9a89f388
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

Problem: OBSERVED preserved Chromium traces show the branch journey exhausting its 30-second body during its fourth reviewed Save; a late pending write outlives cleanup and the next case cancels a recovered editor through an unnamed button.
Desired outcome: STATED retain every branch behavior assertion while bounding the four-save journey at 90 seconds and reliably settling/restoring only this fixture's configuration work before the next case.
Actors: STATED offline Chromium fixture administrator and read-only developer.
Primary scenario: OBSERVED serial settings branch edit/review/apply/restoration followed by corrupt/late-preview negatives in the same temporary server home.
Examples: OBSERVED preview314 finished after timeout and staged316 after cleanup315; the next case recovered that draft and clicked Cancel.
Counterexamples: STATED API-only Save operation293's project_not_found remains a genuine product finding, not a fixture assertion to mask.
In scope: STATED browser fixture repair in settings.spec.ts (settings-save.spec.ts only if needed), focused cleanup proof and scoped documentation/evidence.
Out of scope: STATED Windows ProfileStore production fix, missing wizard field help, API-only saved assertions, product/Python/assets/package/build changes, full suites, push and deployment.
Constraints: STATED same master checkout; base67f4f280; 30 minutes, at most15 tracked paths, at most3 repair/review rounds; serial offline18765 fixture only, no live providers/forges/DCP. Parent owns integrated validation/delivery.
Success signals: STATED two affected branch journeys and owned-cleanup regression pass; TypeScript, whitespace and scoped strict checks; independent spec/quality approval; local clean commit.
Evidence: OBSERVED prior traces and real temporary-store Windows probe: io.open PermissionError errno13/winerrorNone during replacement becomes a silently skipped profile in immutable lookup; direct subsequent read succeeds. This separate production issue and missing wizard help stay outside this task.
Assumptions: INFERRED clean pending baseline plus recorded accepted configuration candidate identities establish ownership of fixture cleanup.
Unknowns: UNKNOWN human decision on broader production scope; no permission inferred from silence.
Decision-blocking questions: None for the explicitly authorized fixture scope.
Proposed behaviors: None; retain existing product contracts and behavior assertions.
Path and reason:
| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | yes | Fixture-only restoration of existing reviewed branch contract. |
| no new interface or data format | yes | No product files changed. |
| no new dependency | yes | Existing Playwright/API helper only. |
| an existing requirement covers behavior | yes | REQ-UX-7b47e30e. |
| no security or data-handling change | yes | Temporary fixture data only, owned candidate cleanup. |

## Requirement coverage

REQ-UX-7b47e30e: retain successful reviewed edits, invalid/corrupt/late preview refusal and Dev read-only assertions; add owned-cleanup interruption proof.


## Design

Keep all four successful reviewed UI saves, with a local90-second case budget. A branch-only wrapper requires an empty pending baseline and records accepted preview/stage/apply responses through a pass-through route. Register cleanup before running the body; afterEach has its own30-second teardown allowance. In cleanup, stop new browser writes, leave the app, await in-flight requests and terminal accepted operations, then remove only a matching owned pending candidate. Restore changed branch fields through confirmed API stage/apply as failure cleanup; successful-body restoration still exercises both reviewed UI saves. Generic afterEach skips pending deletion for owned branch cases. The following preview case uses the exact Edit name. An interrupted-save regression proves terminal drainage, baseline restoration and empty pending state. Product error responses remain assertions, never retried/masked by fixtures.


## Log

- 2026-11-14 frame: journal opened
- 2026-11-14 frame: completed; next build - Recorded authorized quick fixture scope and existing branch requirement
- 2026-11-14 build: red: parent full Chromium run exit1 (333passed/6failed); preserved branch trace shows30-second timeout during restoration and next-case textbox failure after Cancel. Reuse recorded failure rather than rerun known slow failure; scope REQ-UX-7b47e30e.
- 2026-11-14 build: release-notes: none (browser fixture isolation only; no CHANGELOG/product change).
- 2026-11-14 build: help: none (screen/workflow behavior unchanged; no product source or assets changed).
- 2026-11-14 build: green: npm run typecheck exit0; playwright test e2e/settings.spec.ts --grep branch naming previews|branch preview rejects|branch fixture settles|branch naming is read-only --global-timeout240000 exit0:4passed57.4s. Four-save journey32s; interruption proof9.4s.
- 2026-11-14 build: inspection: evolution has only settings browser fixture and frontend documentation outside.agentic; project context current because no product change. Strict scoped exit0 errors0/warnings71:70 inherited legacy records plus source-no-test-changes because managed layout classifies e2e as source; actual four browser tests ran. No asset/Python/build changes.
- 2026-11-14 build: completed; next validate
- 2026-11-14 validate: review preparation: moved registered cleanup to afterEach with its own30-second allowance so a body timeout cannot prevent teardown; terminal failed operations are recorded while remaining accepted work drains before safe cleanup. Original active-body errors remain test failures.
- 2026-11-14 validate: DEVIATION validate: parent prohibits full suites and AEGIS --run; final proof uses targeted4branch Chromium cases, TypeScript, whitespace and scoped strict. Integrated full proof remains parent-owned.
- 2026-11-14 validate: final: npm run typecheck exit0; final targeted Chromium exit1:3passed1failed84s; savebar assertion atsettings.spec.ts179 retained afterGET/operations/9 returned404project_not_found. Same independently reproduced preexistingWindowsProfileStore issue; no timeout/no leak, allfollowingnegative/interruption/Dev casespassed. Revisedcandidate earlier4passed45.7s. Scopedstrict exit0 errors0 warnings71 notes28 (70legacy+e2e layout source-no-test-changes); git diff --check exit0.
- 2026-11-14 validate: DEVIATION validate: final Chromium proof retains one preexistingProfileStore visibility failure; fixture-onlycandidate remains independently approved with earlier4-casegreen and final3-casegreen/ownedcleanup evidence. Do not mask404 or rerun to claimgreen. Human separately approved the productionfix for the nexttask/commit; parent owns integrated proof.
- 2026-11-14 validate: completed; next done

## Rulings

- RULING-001 | date=2026-11-14 | decision=Limit this task to browser branch fixtures on master; 90-second four-save journey, owned cleanup, local commit only; no production fixes or full suites. | reason=Parent granted the sole write turn after clean67f4f280, with30-minute/15-path/3-round limits; broader human scope remains pending. | source=user | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-ce36f131.md
changed: Fixture-only branch90s journey, separately bounded owned teardown, exact Edit and interruption cleanup proof
evidence: TypeScript/strict/diff exit0; earlier revisedChromium4passed45.7s; finalChromium exit1:3passed1knownproductfailure
issues: Final four-save assertion exposes existing WindowsProfileStore project_not_found; separate human-approved productiontask follows. Parent fullproof pending.
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-11-14)

- stage: validate; type: fix; path: quick; branch: master
- requirements:
  - REQ-UX-7b47e30e - Reviewed branch naming edits in Repository
- deviations: 2 recorded
  - validate: parent prohibits full suites and AEGIS --run; final proof uses targeted4branch Chromium cases, TypeScript, whitespace and scoped strict. Integrated full proof remains parent-owned.
  - validate: final Chromium proof retains one preexistingProfileStore visibility failure; fixture-onlycandidate remains independently approved with earlier4-casegreen and final3-casegreen/ownedcleanup evidence. Do not mask404 or rerun to claimgreen. Human separately approved the productionfix for the nexttask/commit; parent owns integrated proof.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 67f4f28: 6 file(s) changed, 310 line(s) added
- checks: errors=0 warnings=71 notes=28
- checklist: 9/9 done
