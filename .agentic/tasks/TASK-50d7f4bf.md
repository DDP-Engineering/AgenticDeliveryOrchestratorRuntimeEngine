# TASK-50d7f4bf - WK-07 integrated worker acceptance and operator evidence

stage: validate
type: change
path: quick
interaction: autopilot
requirements: REQ-DATA-c4bcaba7, REQ-REL-c2971f45, REQ-REL-67679bff, REQ-REL-83b9fc8c, REQ-FUNC-43e2f999, REQ-REL-c240007b, REQ-REL-af360022, REQ-FUNC-80b5347e, REQ-FUNC-bee68a72, REQ-FUNC-3b737a5c
parent:
branch: master
base: e0a62729cf0391ea5d1fb9ad56d064ec3fd3b636
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

Problem: STATED (#90/WK-07): integrated acceptance of #83 must demonstrate independent projects, bounded per-project run pools, scoped configuration and safe recovery without a redundant global suite.
Desired outcome: STATED: exact criterion-to-executed-proof inventory, focused offline regressions for remaining integration gaps and truthful operator/help/component documentation.
Actors: STATED: operator/admin, supervisor, project/configuration/run workers, controlled forge/executor transports.
Primary scenario: STATED: A/B N=1 overlap, A N=2 with third waiting; B/global settings respond while A is blocked; cancellation, capacity reduction, pause and crash preserve ownership/effects.
Examples: STATED: two started jobs may continue above reduced N; pending initial reservations start only within current N.
Counterexamples: STATED: two working labels are not concurrency evidence; an unavailable Linux host is not native Linux acceptance.
In scope: STATED: offline integrated contracts, bounded temporary process smoke, acceptance matrix, relevant operator/component/help reconciliation and relevant integration defects.
Out of scope: STATED: no commit/push/merge, Gitea/DCP operations, target-repository suites, migrations, planning changes, package rebuilds or deployment/setup automated tests.
Constraints: STATED: shared master (explicit user choice), version 0.15.0; autopilot; maximum 12 edit/verify cycles, 120 minutes and 120 files per batch. Final full validation activated at f3aa538; each whole suite once, collect all outcomes, then only focused repair proof. No silently excluded baseline failures.
Success signals: STATED: controlled executor entry plus independent process birth evidence, current scoped outcomes, no duplicated uncertain effects and exact platform limitations.
Evidence: OBSERVED: clean master at e0a62729; test_web_supervisor.py has real-process barriers, run concurrency/configuration/ownership/resource contracts exist; Configuration_Reference.md, Portable_Project_Settings.md and Component_Config.md still claim serial-only operation.
Assumptions: INFERRED: reusing strong existing contracts plus focused integration gaps avoids a redundant acceptance suite.
Unknowns: UNKNOWN: available native Linux/WSL/package runtime and final full-suite result; inspect without treating adapter fakes as native acceptance.
Decision-blocking questions: None; explicit activation authorizes implementation and targeted proof.
Proposed behaviors: None; existing product contracts are authoritative.
Path and reason:

| Criterion | Holds? | Evidence |
| --- | --- | --- |
| no new externally observable behavior | yes | Acceptance/tests/docs of delivered #84-#89 contracts |
| no new interface or data format | yes | Existing public worker/configuration/admission APIs |
| no new dependency | yes | pytest + standard-library process helpers |
| existing requirement covers behavior | yes | Requirement coverage below |
| no security or data-handling change | yes | Existing fail-closed fencing/isolation contracts |

## Requirement coverage

| Behavior | Requirement | Design / proof seam |
| --- | --- | --- |
| Independent projects and N run processes | REQ-FUNC-43e2f999 | Real-process file barriers; integrated settings during blocked executor |
| Home/ancestry fencing | REQ-REL-c240007b | Existing owner/corrupt/unknown probes |
| Bounded shutdown and uncertain outcomes | REQ-REL-af360022 | Real process death/restart and no replay |
| Durable scoped configuration | REQ-FUNC-80b5347e | Real blocked A + HTTP/worker B/global result |
| Immediate control outside long/run capacity | REQ-FUNC-bee68a72 | Pause/Cancel contracts with full pools |
| Reduced N controls queued initial starts | REQ-FUNC-3b737a5c | Existing actual-process capacity regressions |
| Transient sharing conflicts retain state and writer fencing | REQ-REL-83b9fc8c | Bounded local I/O retries; typed persistent denial |
| Typed optional field presence retained | REQ-DATA-c4bcaba7 | Queue serialization excludes unset fields; explicit-null refusal |
| Declared handler success status retained | REQ-REL-c2971f45 | Bound registered handler status200/202; environment acceptance proof |
| Submission storage refusal before admission | REQ-REL-67679bff | Protected mkdir/write boundary sanitized503, no queue/publication |

## Design

Quick path: reuse the real-process supervisor helper, add only missing integrated assertions and scenarios. External forge/Git/runtime/executor collaborators remain simulated; no target tests run. Document exact commands and oracles in an operator acceptance matrix. Existing requirements remain unchanged unless coverage linkage needs extension. No new product interface, schema or dependency. Discovered Windows sharing contention uses the same six-attempt, 250 ms scheduled retry bound as reviewed settings; authority is rechecked on each publish attempt, persistent failure remains a distinct StateStorageError subtype and preserves prior bytes; listings/admission propagate it rather than omitting a reservation as corrupt.

Post-commit final remediation keeps the existing durable queue and stored schema:
preserve typed field presence, retain registered handler200/202 success status,
and sanitize protected request mkdir/write denial before enqueue. Domain fixtures
consume actual completion, bind canonical run/worktree identities and real per-run
locks, and isolate ambient statistics paths. The Chromium fixture uses one owner
per consumer; existing seed/reset clears only terminal simulated Start trials under
their own locks, refusing unfinished/active ownership. Browser interceptors mutate
completed evidence, and stale-response barriers release the server resource before
holding old delivery. Current retained drafts, technical-detail tabs and capacity
panels keep their original functional/fail-closed oracles.


Acceptance inventory: [Worker_Acceptance.md](../../01_Documentation/Worker_Acceptance.md)
records each exact executed criterion/test, commands/results and platform limits.

## Log

- 2026-11-14 frame: journal opened
- 2026-11-14 frame: completed; next build - Existing worker contracts; quick acceptance and documentation change, scope authorized
- 2026-11-14 build: Scope discovery: real N=2 Windows acceptance exposed PermissionError during concurrent state reads/replacement; extend state-store requirement/proof and documentation without changing stored schema.
- 2026-11-14 build: red: uv run --frozen --extra web python -m pytest -q tests/test_state.py -k state_sharing exit 1; 5 failures show missing bounded sharing retries and writer refencing (REQ-REL-83b9fc8c).
- 2026-11-14 build: green: test_state.py exit 0, 80 passed; integrated seven-module worker acceptance exit 0, 234 passed in 110.68s (one existing FastAPI/httpx deprecation); WSL adapter 4, native/auth boundary 12 and forge adapter 12 selected tests passed. No global suites run.
- 2026-11-14 build: help: updated (all four Jobs locales explain pending reservations after lower N, continuing started jobs and independent configuration); restricted help grammar forbids HTML/legal comments so existing comment-free format retained.
- 2026-11-14 build: release-notes: added (Windows sharing contention repair is visible to jobs; test/doc acceptance needs no additional note). Version remains 0.15.0.
- 2026-11-14 build: Manual operational observation: one-off Python stdin driver staged current application/launcher in auto-cleaned extracted bundled Windows and Linux runtimes, recomputed temporary inventory, launched two paused profiles on a free loopback port, replaced configuration without changing project PIDs, killed supervisor and observed old tree death/new service readiness, then portable Stop exit 0/all identities dead. Windows native and Ubuntu/WSL Linux both PASS; original archive SHA256 unchanged. Initial Windows staging retained obsolete assets and was corrected by replacing only disposable app directory. No deployment/setup automated tests or final archive rebuilds.
- 2026-11-14 build: DEVIATION validate: complete umbrella proof deferred until post-commit explicit activation - user requires exactly one final full run; present pass uses targeted contracts and static checks only. Linux smoke is Ubuntu under WSL, not bare-metal/service-manager acceptance; real Pi/forge/runtime/cgroup jobs remain operator-owned.
- 2026-11-14 build: completed; next validate
- 2026-11-14 validate: Review round 1: specification P2 full-pool Cancel test bypassed ProjectWorker dispatch; quality P2 exhausted sharing StateError could be swallowed as corruption by list_runs after a successful invalid_runs scan, permitting capacity omission. Fix scheduler-driven Cancel proof and distinct propagating storage error with a public admission regression.
- 2026-11-14 validate: returned to build - Review round 1: preserve storage-unavailable propagation through capacity; prove Cancel dispatch at full pool
- 2026-11-14 build: red review fix: state listing sharing denial tests exit 1 (2 failed); public admission storage-loss-between-scans test exit 1 (1 failed), proving the capacity omission. Beginning second bounded batch for review fixes, max 12 cycles/120 min/120 files; first batch stayed below limits.
- 2026-11-14 build: Review-fix recheck: 182 passed, 2 failed in changed scoped 184-test command; real Windows CRT file opens expose errno EACCES without winerror. Added CRT-shaped read/write boundary cases; red: test_state.py -k 'state_sharing_contention and crt' exit 1, four expected failures. Extend only Windows EACCES classification; unrelated I/O remains unchanged.
- 2026-11-14 build: green review fixes: targeted affected final command (test_state.py plus scheduler Cancel, scan-loss admission and both real-process lower-N cases) exit 0, 90 passed in 13.16s including all 86 state cases. Additional Start-idempotency and unaffected scope passed in preceding 184-test run (182 passed; two CRT failures now corrected). Focused Ruff exit 0. StateStorageError propagates through listing/admission; Windows CRT EACCES is bounded like explicit winerror.
- 2026-11-14 build: completed; next validate
- 2026-11-14 validate: Final documentation reconciliation removed remaining stale independent verification-command claims from project context and Operations Guide; agent-owned repository checks remain unchanged. No software/test changes after round-2 review.
- 2026-11-14 validate: Review round 2: independent spec and quality reviewers approved current code/tests and reconfirmed final documentation-only reconciliation. No remaining actionable findings. Unchanged scoped green proofs retained per user instruction, complete final umbrella proof not started.
- 2026-11-14 validate: final targeted substitute: python .agentic/aegis.py check --task TASK-50d7f4bf --strict exit 0 (strict ok; errors=0, warnings=71, notes=28); release-notes check --since e0a62729 exit 0; git diff --check exit 0. No --run/global suite executed. Historical stale-path/test-link/journal advisories are outside this task; large generated JS secret scan skip is accepted for the rebuilt fingerprinted bundle sourced from reviewed tracked inputs, not credentials. Review approvals current; targeted green evidence and platform limitations recorded in Worker_Acceptance.md.
- 2026-11-14 validate: completed; next done
- 2026-11-14 done: returned to validate - Explicit final umbrella validation activation after WK-07 commit
- 2026-11-14 validate: Final umbrella pass begins at f3aa5384936c53cd864bb13b7375c27c552b4498 on clean master. Separate canonical commands collect every result despite failures (npm validate uses &&). Full pytest has no excluded Pi-guard test; inspected collection has no deployment/setup script execution. Batch bounded to 120 minutes/12 edit-verification cycles/120 files; no repeated operational smoke unless affected.
- 2026-11-14 validate: Complete pass partial results: Ruff adore/tests exit 0; npm test exit 0 (181 passed,0 failed/skipped/cancelled); release consistency --require-artifacts exit 0. Release-note comparison retried with verified umbrella base 50ac624 after invalid abbreviated ref 310ae0b could not compare; full Python continues without exclusions.
- 2026-11-14 validate: Complete frontend build gate: npm run build:e2e exit 0 (UI and E2E TypeScript checks, isolated Vite bundle and fingerprint; existing chunk-size advisory). Correct release-note comparison --since 50ac624 exit 0. Full Python still progressing; Chromium will run once after Python to avoid concurrent process-test load.
- 2026-11-14 validate: Complete Python pass: uv run --frozen --extra web python -m pytest -q -ra --tb=short --durations=15 exit 1; 3502 passed,111 failed,15 skipped,0 deselected,1 Starlette/httpx warning in 1555.89s. All failures collected, Pi guard included; its test/native/container files unchanged since umbrella base50ac624. Chromium full315 started once after Python.
- 2026-11-14 validate: returned to build - Final full validation exposed configuration transport field-presence bug and unconverted contract fixtures; repair targeted regressions
- 2026-11-14 build: Targeted repairs: 62 import/typed-input/credential-write cases passed after exclude_unset transport and sanitized submission-storage refusal. Follow-up domain batch 126 passed,2 platform skips,1 failed: durable worker success lost the existing environment HTTP202 status. Preserve declared handler success status rather than loosening the assertion. CLI ownership fixture8 cases now pass after modeling per-run scope and pending Cancel.
- 2026-11-14 build: Baseline classification: isolated temporary 50ac624 snapshot reproduces unsorted setting catalog; guard sources/test unchanged across umbrella and corrected snapshot probe includes both guard files. Blank-path metrics passed in fresh baseline cwd: failure was environmental, current tests read legacy workspace .adore/metrics.db (schema0, created Nov4, bytes last written Nov11). Preserved all existing data; isolate metrics test cwd and real-process helper metrics paths instead.
- 2026-11-14 build: Fixture corrections retain trust-boundary assertions: raw HTTP tests now consume durable completion except explicit acceptance cases; audit domain evidence selected independently from operation-finished; web schema18 asserted; canonical run/container identities supplied to native retry; saved clone worktree paths explicit; real per-run CLI fake locks retain unchanged live bytes and queue Cancel. Native readiness fixture now provisions fake native identity for the new cached plan publication boundary.
- 2026-11-14 build: Further targeted proof: 35 passed covering retained HTTP202 environment outcome, role-revocation409 with no target publication, nine isolated metrics paths, explicit-null import refusal and existing configuration-worker contracts. Eight native/container workflow-readiness variants pass with fake native installation/context. New request-directory failure test red (OSError escaped), then expanded sanitized submission-storage boundary to include directory creation.
- 2026-11-14 build: release-notes: added (configuration dispatch fidelity and honest setup outcomes are user-visible); help: none (post-commit repairs restore existing workflows/status meaning, labels and user steps unchanged). Added atomic transport/status/storage requirements and component/API knowledge; no migration or schema reader added.
- 2026-11-14 build: Begin bounded remediation batch 2 (12 edit/verification cycles,120 minutes,120 files). Batch1 full Python and focused backend repairs complete; full Chromium remains its single initial pass. New browser repairs only fixture ownership and explicit durable-result consumers; no target-repository verification or operational smoke rerun.
- 2026-11-14 build: Initial complete Chromium pass exit1: 175 passed,24 failed,116 did not run;315 selected,0 excluded; two global errors from configured1800s suite/teardown deadline. Diagnosed duplicate fixture project ownership, stale synchronous transport consumers and capacity-induced layout measurement assumptions. Follow-up will use --last-failed, which includes failed and not-run IDs, retaining all175 green cases without repetition.
- 2026-11-14 build: Browser focused repairs: real fixture command consumers now own the exact registered project handles; dashboard Start/negative exit, credential, runtime Save and import flows pass in140-case selection. Consume completed domain evidence before intercepting it; hold completed old preview rather than an unsubmitted request (new draft otherwise correctly409 while enrollment resourcebusy). Updated invalid-draft navigation expectation to current retained-draft contract; kept background-read/invalid-input assertions. Same-frame toolbar and scrolled panel bounds preserve layout constraints.
- 2026-11-14 build: Additional baseline observed in previously unrun Chromium: shell.spec.ts glossary/essential enrollment help fails missing #enrollment-help-url. Independent spec review verified identical test blobeee8588c at50ac624 and current; first-step render region identical (SHA2567da58849c668a269cf963b8739dcd27d789b58db59627fcd2943e84649e73748). Existing REQ-UX-072cf049/REQ-UX-2761363b and Web_Interface guidance still expect it. Preserve the failing assertion; no unrelated UI copy/requirements weakening. This is a baseline code/test/docs discrepancy, classified by identical source, not a separately executed baseline browser run.
- 2026-11-14 build: Chromium --last-failed selection completed exit1:128 passed,12 failed,0 unrun in18.8m (24 initial failures plus116 previously unrun,175 initial green not repeated). Remaining12 include baseline essential-help assertion,11 corrected fixtures/consumers/temporary encoding issues. Next explicit13-case proof covers those11 plus changed malformed-workflow interceptor and shared-fixture Start44->reset->Start44 isolation; baseline shell failure remains reported, no repeat requested for it.
- 2026-11-14 build: Follow-up explicit browser selection collected12 (blankline204 did not select malformed-workflow test205):11 passed,1 audit-selector failure in1.9m. Resolved all stale preview/import/queued Start/layout/retained-invalid/localization/statistics cases. Audit role text includes project name before role; retain two-project count using unanchored role match. Final2-case run covers that selector and previously changed malformed-workflow interceptor. Fixture cleanup uses existing seed/reset lifecycle only; removed proposed extra reset endpoint/consumer as unnecessary.
- 2026-11-14 build: green final browser focus: explicit12-case selection11 passed/1 auditselector failure, then corrected audit+changed malformed-workflow interceptor2 passed in33.0s. All315 original Chromium scenarios executed across bounded passes:314 unique green evidence,1 unchanged baseline enrollment-help failure,0 unrun. No full green suite rerun; temporary UTF8 fixture corruption was restored and fr/de/ro cases each re-proven. No proposed reset endpoint retained; existing seed/reset provides perproject terminal-trial cleanup with actual locks.
- 2026-11-14 build: Final backend focused proof:9 passed80.45s for request-directory refusal, integrated Direct/AEGIS independent settings, full-pool Cancel, storage-scan loss, actual pool overlap and actual reduced-limit reservation starts. Changed-file Ruff passed; E2E TypeScript passed after fixture corrections. release-notes: added (dispatch fidelity/setup outcome); help: none (restored contracts only; baseline missing enrollment help remains unmodified and reported).
- 2026-11-14 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-14 validate: Review round3: independent spec and quality reviewers approved final current candidate and complete evidence inventory. No actionable findings. DEVIATION validate: final --strict --run replaced with strict static plus already-executed full component results and focused repairs - explicit user requires each full suite once and prohibits redundant green reruns; nonzero baseline results remain failures, not green waivers.
- 2026-11-14 validate: final: strict static check exit0 (errors0,warnings79,notes28); release-notes --since taskbase e0a62729 exit0; git diff --check exit0; protected-path diff vsf3aa538 exit0 confirms frontend fingerprint inputs/committed bundle,07_Delivery,00_Planning,version declarations and stamp tooling unchanged. Full check --run intentionally not repeated. Advisory warnings are historical stale requirement/test paths and journal headers plus9 E2E fixtures classified as source by broad web layout; these are executed test contracts, not uncovered runtime paths. Manual/operator notes remain explicit limitations. No new actionable review findings.
- 2026-11-14 validate: Validation disposition: full Python exit1 is not overwritten green (3502pass111fail15skip0deselect,109 relevant failures focused-green,2 reproduced baseline failures); Chromium initial timeout plus all remaining selections gives314 unique green/1 source-confirmed baseline failure/0 unrun. Overall acceptance remains non-green. Version0.15.0,master HEADf3aa538,37 uncommitted changed/new files; no commit/push/merge,07_Delivery/DCP/planning/other-task-journal change. Fixture18765 listener gone. Original manual Windows and Ubuntu/WSL smoke retained; no unnecessary smoke repeat or claim of bare-metal/livePi/forge/container/cgroup acceptance.

## Rulings

- RULING-001 | date=2026-11-14 | decision=Targeted validation only before WK-07 commit; complete umbrella validation only after separate explicit activation | reason=Current user instruction via coordinator; autopilot, no routine confirmations; max 12 cycles/120 min/120 files per batch | source=user | supersedes=none
- RULING-002 | date=2026-11-14 | decision=Run the complete umbrella validation now, once per full suite; repair relevant regressions and rerun only affected checks | reason=Explicit post-commit activation at f3aa5384936c53cd864bb13b7375c27c552b4498; collect Python, Ruff, frontend unit/help, Chromium and artifact checks even if one fails; no live/DCP/deployment-script tests | source=user | supersedes=RULING-001


## State

status: blocked
reported: validate - blocked
next: Coordinator disposition of three pre-existing failures before final acceptance
must_read: .agentic/tasks/TASK-50d7f4bf.md, .agentic/steps/5_validate.md
changed: Post-commit configuration fidelity/status/storage repairs, domain/ownership/browser fixtures and final acceptance evidence;37 uncommitted files on master f3aa538,version0.15.0
evidence: Full suites collected once;109 relevant Python failures focused-green; Chromium314 unique green/1 baseline/0 unrun; Ruff,181 frontend/help,build,artifact checks and strictstatic green;round3 both approved
issues: Baseline: Pi guard mismatch; catalog ordering; missing enrollment help.15 Windows skips; platform/live acceptance limits in Worker_Acceptance.md.
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-11-14)

- stage: validate; type: change; path: quick; branch: master
- requirements:
  - REQ-REL-83b9fc8c - Bound transient run-state sharing contention without losing valid evidence
  - REQ-FUNC-43e2f999 - Supervise independent project workers and per-project run pools
  - REQ-REL-c240007b - Refuse duplicate supervisors and fence children after parent death
  - REQ-REL-af360022 - Stop owned worker trees within a bounded shutdown
  - REQ-FUNC-80b5347e - Durable scoped configuration results
  - REQ-FUNC-bee68a72 - Admission control bypasses long configuration work
  - REQ-FUNC-3b737a5c - Queue initial dispatch under current project capacity
- deviations: 1 recorded
  - validate: complete umbrella proof deferred until post-commit explicit activation - user requires exactly one final full run; present pass uses targeted contracts and static checks only. Linux smoke is Ubuntu under WSL, not bare-metal/service-manager acceptance; real Pi/forge/runtime/cgroup jobs remain operator-owned.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base e0a6272: 31 file(s) changed, 861 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=71 notes=28
- checklist: 9/9 done

## Delivery report (2026-11-14)

- stage: validate; type: change; path: quick; branch: master
- requirements:
  - REQ-DATA-c4bcaba7 - Preserve omitted and explicit optional fields across configuration dispatch
  - REQ-REL-c2971f45 - Retain declared handler success status in configuration outcomes
  - REQ-REL-67679bff - Refuse unavailable private configuration request storage before admission
  - REQ-REL-83b9fc8c - Bound transient run-state sharing contention without losing valid evidence
  - REQ-FUNC-43e2f999 - Supervise independent project workers and per-project run pools
  - REQ-REL-c240007b - Refuse duplicate supervisors and fence children after parent death
  - REQ-REL-af360022 - Stop owned worker trees within a bounded shutdown
  - REQ-FUNC-80b5347e - Durable scoped configuration results
  - REQ-FUNC-bee68a72 - Admission control bypasses long configuration work
  - REQ-FUNC-3b737a5c - Queue initial dispatch under current project capacity
- deviations: 2 recorded
  - validate: complete umbrella proof deferred until post-commit explicit activation - user requires exactly one final full run; present pass uses targeted contracts and static checks only. Linux smoke is Ubuntu under WSL, not bare-metal/service-manager acceptance; real Pi/forge/runtime/cgroup jobs remain operator-owned.
  - validate: final --strict --run replaced with strict static plus already-executed full component results and focused repairs - explicit user requires each full suite once and prohibits redundant green reruns; nonzero baseline results remain failures, not green waivers.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base e0a6272: 62 file(s) changed, 1493 line(s) added
- checks: errors=0 warnings=79 notes=28
- checklist: 9/9 done
