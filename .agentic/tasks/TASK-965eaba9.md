<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-965eaba9 - W15 structured redacted change evidence and useful audit history

stage: deliver
type: feature
path: full
interaction: autopilot
requirements: REQ-DATA-34ed1530, REQ-SEC-9415d21d, REQ-REL-1dc9b68c, REQ-DATA-196dcd48, REQ-UX-0ae52a96, REQ-FUNC-a6d68c4a
parent:
branch: task/adore-web-interface
base: dd83612259daa0a34828f026093a19e90276ea76
opened: 2026-10-06

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged
- [x] validation evidence, inventory, exclusions and intended outcome presented
- [x] coordinator delivery acceptance recorded
- [x] journal and report prepared for approved delivery
- [ ] approved commit/push/issue-close outcome delivered
- [ ] close-out recorded after successful delivery

## Frame

Problem: STATED live W15 #19 compact audit cannot explain changes or prepared/applied results.
Desired outcome: Structured redacted evidence and useful authorized server-paged history.
Actors: Administrator; assigned developer; API; single command worker.
Primary scenario: reviewed config -> prepare evidence -> guarded apply -> truthful revision-bound diff.
Examples: user creation commits account/grants/evidence together; pickup submission stays prepared until confirmed completion.
Counterexamples: a worker crash cannot claim applied; old name-only rows cannot grant a Dev access.
In scope: exact eight live criteria, API/store/worker, audit UI, affected docs and tests.
Out of scope: #16/#17/#20, exports, runtime state migration, releases, merge/deployment/live acceptance.
Constraints: four hours from 2026-10-06 session start; three corrective review cycles; twenty authored product/test/doc paths; zero paid executors/APIs/subagents/reviewers. Existing branch preserved.
Success signals: eight criteria mapped to offline assertions and final full proof; frozen candidate for coordinator.
Evidence: OBSERVED live #19 open P2; #6/#10/#13/#18 closed; epic #3 open. Clean local/remote dd83612259daa0a34828f026093a19e90276ea76. OBSERVED store schema13 and separate filesystem mutation/audit writes. References: .agentic/knowledge/web-interface.md, web/store.py, app.py, commands.py, App.tsx, approved DESIGN_BRIEF.md and parent PUBLICATION.md.
Assumptions: INFERRED cross-filesystem/SQLite crash requires an explicit uncertain durable attempt, not fictitious distributed atomicity.
Unknowns: human novice/live acceptance remains operator work.
Decision-blocking questions: none.
Proposed behaviors: closed server evidence; atomic SQLite mutations; durable uncertain filesystem attempts; idempotent worker evidence; legacy unknowns; filtered authorized reads; admin settings retention.
Path and reason: full. Quick criteria: externally observable behavior=no; unchanged format=no; new dependency=yes (none); existing requirement=no; unchanged security/data=no. No child tasks authorized.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| W15 | REQ-DATA-34ed1530 contract | REQ-DATA-34ed1530 | success | bad input/crash/access | test_web_audit_evidence.py and audit.spec.ts | schema14 closed evidence / transactional or uncertain attempt |
| W15 | REQ-SEC-9415d21d contract | REQ-SEC-9415d21d | success | bad input/crash/access | test_web_audit_evidence.py and audit.spec.ts | schema14 closed evidence / transactional or uncertain attempt |
| W15 | REQ-REL-1dc9b68c contract | REQ-REL-1dc9b68c | success | bad input/crash/access | test_web_audit_evidence.py and audit.spec.ts | schema14 closed evidence / transactional or uncertain attempt |
| W15 | REQ-DATA-196dcd48 contract | REQ-DATA-196dcd48 | success | bad input/crash/access | test_web_audit_evidence.py and audit.spec.ts | schema14 closed evidence / transactional or uncertain attempt |
| W15 | REQ-UX-0ae52a96 contract | REQ-UX-0ae52a96 | success | bad input/crash/access | test_web_audit_evidence.py and audit.spec.ts | schema14 closed evidence / transactional or uncertain attempt |
| W15 | REQ-FUNC-a6d68c4a contract | REQ-FUNC-a6d68c4a | success | bad input/crash/access | test_web_audit_evidence.py and audit.spec.ts | schema14 closed evidence / transactional or uncertain attempt |

## Design

REQ-DATA-34ed1530: add nullable structured JSON evidence and unique server event key to schema14 audit. Preserve compact columns/API compatibility. Snapshot actor username with numeric ID; project immutable ID where observed; resource typed account/config/project/operation ID.
REQ-SEC-9415d21d: audit.py owns a closed evidence schema and recursive redaction. Never persist request credentials, environment, arbitrary errors or caller idempotency strings. Hash server correlations. Known scalar nonsecret configuration diffs only; arbitrary string/compound settings explicitly redacted.
REQ-REL-1dc9b68c: SQLite-owned account/access/queue/policy mutations and evidence share BEGIN IMMEDIATE. Filesystem-owned config/enrollment uses a durable initially uncertain attempt, finalized after owning mutation, before removing pending config. Crash leaves uncertain; replay uses server key, retaining original before. Precondition rejections produce no applied event. Interrupted command becomes uncertain; completion update/evidence share transaction, terminal replay is exact or rejected.
REQ-DATA-196dcd48: upgrade 13->14 inside existing initialization transaction. Validate audit rows before upgrade/commit; null evidence marks legacy, before/after/revisions/result unrecorded. Legacy project name never fabricates stable identity or Dev visibility. No runtime state migration.
REQ-UX-0ae52a96: admin global audit-page accepts actor_id/project_id/action/from/to; Dev only exact assigned project_id. WHERE selection before COUNT/LIMIT in one snapshot. Strict UTC half-open period. Project History adds change evidence alongside existing job history. No export.
REQ-FUNC-a6d68c4a: policy lives in System status administrative settings; independent nullable bounds retain existing maxima. Return deleted count and stored-text impact. Audit policy update evidence shares its transaction.
Architecture: audit.py -> store.py (SQLite) <- API and worker; AuditHistory -> authorized audit-page. API retains RBAC/CSRF and current locks.
Expected files: audit.py, store.py, app.py, commands.py, App.tsx, AuditHistory.tsx, auditCopy.ts, styles.css; test_web_audit_evidence.py, audit.spec.ts; Web_Identity/API/Frontend contracts, Web_Interface.md, CHANGELOG.md. Workflow/knowledge/context and generated static inventoried separately.
Risks: SQLite and filesystem cannot commit atomically; conservative uncertainty is required. Arbitrary historic details require redacted projections rather than fabricated diff. No new dependencies. Open decisions: none.

## Log

- 2026-10-06 frame: live authority/scope and full path accepted under standing human continuation; clean matching branch verified.
- 2026-10-06 specify: six atomic contracts with shared detailed evidence spec; eight criteria inventoried.
- 2026-10-06 design: schema14, closed redaction, SQLite atomic ownership and conservative filesystem crash semantics audited; advance build.

- 2026-10-06 frame: <scope agreed, exclusions, chosen path and why>

- 2026-10-06 build red: command=`04_Software/.venv/Scripts/python.exe -m pytest -q 04_Software/tests/test_web_audit_evidence.py`; exit=1; REQ-DATA-34ed1530/196dcd48, REQ-REL-1dc9b68c expected missing phase/result, schema14 and operation completion audit.

- 2026-10-06 build red: command=`04_Software/.venv/Scripts/python.exe -m pytest -q 04_Software/tests/test_web_audit_evidence.py -k "filters or config or access"`; exit=1; REQ-UX-0ae52a96/REL-1dc9b68c/DATA-34ed1530 expected missing scoped Dev API and access before/after (config fixture corrected separately before its red proof).

- 2026-10-06 build red: command=`04_Software/.venv/Scripts/python.exe -m pytest -q 04_Software/tests/test_web_audit_evidence.py -k config`; exit=1; REQ-DATA-34ed1530 expected config staging incorrectly projected as applied.

- 2026-10-06 build red: REQ-SEC-9415d21d/FUNC-a6d68c4a command=`04_Software/.venv/Scripts/python.exe -m pytest -q 04_Software/tests/test_web_audit_evidence.py -k "nested or retention"`; exit=1; arbitrary compact detail remained and pruning removed an active attempt. REQ-UX-0ae52a96 command=`npm --prefix 04_Software/web run test:e2e -- audit.spec.ts`; exit=1; missing actor/type controls.

- 2026-10-06 build red: REQ-UX-0ae52a96 command=`04_Software/.venv/Scripts/python.exe -m pytest -q 04_Software/tests/test_web_audit_evidence.py`; exit=1; Dev project count included administrator price metadata. Closed project-action selection added before count/paging.

- 2026-10-06 build red: REQ-REL-1dc9b68c command=`04_Software/.venv/Scripts/python.exe -m pytest -q 04_Software/tests/test_web_audit_evidence.py -k "filesystem or executor"`; exit=1; malformed command exit float0 could claim application; all four malformed result cases lacked uncertain outcome. Durable filesystem crash/restart proof passed.

- 2026-10-06 build red: REQ-UX-0ae52a96/SEC-9415d21d `pytest -q tests/test_web_audit_evidence.py -k dev_project` exit1 exposed financial config values in Dev count; exclude financial config at SQL boundary. REQ-UX-0ae52a96 `npm run test:e2e -- audit.spec.ts -g scannable` exit1 exposed inherited nowrap on evidence; wrap audit cells.

- 2026-10-06 build green: `pytest -q tests/test_web_audit_evidence.py` exit0, 31 cases; `ruff check .` from 04_Software exit0; `npm run build` exit0; `npm run test:e2e -- audit.spec.ts` exit0, five cases. Supplemental proof covers policy rollback/pruning and failed enrollment uncertainty. Browser screenshots inspected: desktop light and Romanian 390px dark; evidence wraps, controls remain visible, table scrolling remains available. Corrected fixture synchronization, retained unrelated API documentation, and carried source revision into clone/import apply. Full test suite reserved for final strict check. Environment context remains correct and unchanged. Six contracts activated/linked.

- 2026-10-06 validate review round1: specification compliance=approved and implementation quality=approved for the same current candidate after semantic corrections. These are two distinct same-agent lenses authorized by RULING-002, NOT independent reviewer assessments. Compliance checked all eight live #19 criteria, exclusion of #16/#17/#20/planning, current contracts and exact path ownership. Quality checked transaction/rollback boundaries, conservative filesystem uncertainty, replay/retention separation, typed corrupt-input failures, SQL scope/counts, recursive redaction, strict UI transport, locale/mobile proof, portability and documentation. No unresolved in-scope finding; zero corrective explicit-review cycles used. Final full proof follows; failed proof invalidates these verdicts.

- 2026-10-06 validate round1 binding refreshed after final UTF-8 portability and documentation wording correction: both same-agent verdicts approved for this unchanged executable/docs/requirements tree; relevant paths re-inspected and Ruff rechecked.

- 2026-10-06 validate final proof FAILED: `check --task TASK-965eaba9 --strict --run` exit1; Python 4failed/1140passed/1skipped, lint0, frontend1. Round1 quality=changes_required; both bound verdicts cleared, return build corrective cycle1/3. Findings: test fault injector omitted newly optional actor kwarg; exact paging row assertion omitted structured fields; pricing fixtures relabelled schema14 as pre14 without restoring legacy audit shape; two newly introduced error codes lacked four-locale catalog entries. Fix only these findings; reuse established translated generic invalid-request/project-not-found responses at filter/access boundaries. Three additional authored test paths bring total to20/20. Final candidate must be re-inventoried/reviewed and full proof rerun.

- 2026-10-06 build corrective cycle1 green: four exact failed Python selectors now exit0; `npm test` exit0, all51 helper/catalog cases; whole04 Ruff exit0. Existing fault injector accepts actor kwarg, legacy pricing restores genuine old audit shape, paging asserts complete new projection, API uses established translated invalid_request/project_not_found codes. Requirements linked to three additional changed tests. Same scope and authored cap20 retained.
- 2026-10-06 validate round2: after re-reading validate/full journal and focused green, two same-agent lenses re-reviewed all final changes and prior criteria map. Specification compliance=approved; implementation quality=approved. One corrective cycle used, two remain. No unresolved recorded finding; successful renewed full proof still required. Generated static unchanged because corrections affect API/test fixtures only; current source and bundle bytes remain aligned.

- 2026-10-06 validate round2 final gate FAILED exit1: full Python ok226s and lint0; frontend reached its240s global bound after cascading English-title failures (9passed/84notrun). Observed first dashboard failure context in Romanian following audit locale test. Quality=changes_required; both verdicts cleared. Return build corrective cycle2/3, solely restore original saved preferences in the audit locale fixture even on failure. No product behavior or verification weakening; renewed focused ordering proof and full gate required.

- 2026-10-06 corrective cycle2 green: `npm --prefix 04_Software/web run test:e2e -- audit.spec.ts dashboard.spec.ts` exit0, all13 journeys in22.8s, including consecutive English dashboard journeys after all locale/theme combinations. Finally restores explicit original preferences or established en/system effective fallbacks; API does not support saving null defaults.
- 2026-10-06 validate round3: validate instructions re-read after build, material tree and traceability reviewed under both distinct same-agent lenses. Specification compliance=approved; implementation quality=approved. Two corrective cycles used (max3); no unresolved recorded finding. New test-only cleanup retains assertions and global timeout. Knowledge/project/environment and material documentation remain aligned. Final full JSON proof follows for exact current tree.

- 2026-10-06 round3 configured full proof exit0: Python/lint/frontend all succeeded. Supplemental public API boundary inspection observed actor_id=2**80 raises untyped OverflowError. This new quality finding invalidates both round3 verdicts despite the green suite. Return build corrective cycle3/3: bound audit actor/offset inputs to SQLite signed64-bit range and prove typed422/typed store rejection. Record a failing negative selector before implementation, then final round4 re-review/full proof. No widening of file count/scope or weakened verification.

- 2026-10-06 build cycle3 red: REQ-UX-0ae52a96 `pytest -q tests/test_web_audit_evidence.py -k admin_filters --tb=short` exit1, expected typed422 for actor_id=2**80 instead raised untyped SQLite OverflowError. Include oversized offset at the same numeric binding boundary.

- 2026-10-06 build cycle3 green: `pytest -q tests/test_web_audit_evidence.py --tb=short` exit0, all31 dedicated cases, including oversized actor/offset public422 and direct typed WebStoreError; whole04 Ruff exit0. API/storage bounds, component docs, active spec and component knowledge reconciled.
- 2026-10-06 validate final round4: two distinct same-agent lenses re-reviewed the integrated current candidate, prior scope/criteria matrix, final numeric trust boundaries and focused proof. Specification compliance=approved; implementation quality=approved. Three corrective cycles used (max3); no unresolved recorded finding. Full final verification required for current candidate. Round3 successful proof is retained in round3-verification.json as earlier evidence only. Inventory identity uses rows sorted by repository-relative path, then category|path|hash in that order, exactly as the table displays.

- 2026-10-06 round4 full proof exit1: full Python ok285.1s and lint0; frontend exhausted existing global240s after89passed/21notrun. Statistics route/teardown errors appeared during disposal. Candidate bytes unchanged; no new implementation finding or correction is accepted. Preserve round4-timeout.json, diagnose isolated interrupted statistics seam, then repeat the unchanged strict full proof within standing wall-clock bound. This is a verification retry, not a fourth corrective review cycle. Round4 bound verdicts remain conditional on successful final proof.

- 2026-10-06 unchanged proof retry: isolated interrupted statistics selector `npm --prefix 04_Software/web run test:e2e -- statistics.spec.ts -g "job list and direct detail share"` exit0, 1passed8.6s. All36 material inventory records unchanged at SHA256824dac1d87f820813d7f0292a4fa37a026a55a8a7563ca914b22e19a36f09fca. No source/test/spec/config correction; repeat exact full strict proof, keeping round4 and all original limits.

- 2026-10-06 validate supplemental finding: public recent_audit returned a credential URL in corrupt persisted legacy project metadata. Round4 verdicts invalidated; original three-cycle bound reached. Human directly authorized one additional narrow cycle (RULING-003), retaining all other bounds.
- 2026-10-06 build cycle4 red: REQ-SEC-9415d21d/DATA-196dcd48 `pytest -q tests/test_web_audit_evidence.py -k corrupt_legacy_project --tb=short` exit1: public read did not raise WebStoreError. Existing anchor retained; no counter reset. Safe project-name grammar now applied to persisted projection, preserving empty global scope.
- 2026-10-06 build cycle4 green: same selector exit0; `pytest -q tests/test_web_audit_evidence.py --tb=short` exit0, all32 dedicated cases. Public read, restart initialization and authenticated API reject corruption with redacted typed failure. Earlier unchanged full retry failed existing240s frontend global budget after57passed/54notrun; retained as superseded diagnostic evidence, never current proof.

- 2026-10-06 validate round5: both distinct same-agent review lenses approved for candidate 6c60efdec6021f8b61ae4e7534c092a2a080fe8aea7f4e0d87b0bfc42b5ef45d. Four cycles used, maximum four under direct human RULING-003. All eight live criteria remain covered; persisted project boundary now closed, safe legacy/global rows retained, new test linked and component contract/knowledge reconciled. Final evolution reviewed: same20 authored paths plus5 generated static; no planning/release changes. Full final proof follows after all candidate edits.

- 2026-10-06 round5 final proof exit1: Python1145passed/1existing Windows skip (331.2s), lint0, frontend84passed/27notrun after existing240s global bound (264.0s wrapper). No assertion failure observed before truncation; complete browser proof absent. Bound verdicts invalidated, blocked at authorized four-cycle/20-path cap. Concrete pending proposal: playwright.config.ts globalTimeout240000->480000 only, preserve per-test/assertion limits, one worker/no retries, all111 journeys and strict full gate.

- 2026-10-06 corrective cycle5: Direct human request "can you add this?" approves the previously enumerated480s browser-suite budget, one additional cycle and21 authored paths. Changed only playwright.config.ts globalTimeout240000->480000 plus existing component verification documentation; individual test/assertion/action/navigation limits, all111 journeys, one worker and zero retries retained. Prior full gate retained as round5-timeout.json.

- 2026-10-06 validate round6: both distinct same-agent lenses approved current candidate 23261bfa52caecc009238be067c6dc4917998b42d731159e4ea56cf6aabca155. Fifth cycle under RULING-004 changes only verification budget/config and existing component documentation. Configured AEGIS max_fix_cycles aligned to5 because strict check rejects review_round6 against former maximum5 total rounds. Inventory includes21 authored paths, generated assets and this workflow config. `npx playwright test --list` exit0 finds all111 cases in11 files; no skipped assertion, retry or per-test weakening. Full final proof follows.

- 2026-10-06 validate FINAL: `04_Software/.venv/Scripts/python.exe -X utf8 -u .agentic/aegis.py check --task TASK-965eaba9 --strict --run --json` exit0. Python1145passed/1existing Windows symlink skip (252.1s wrapper); Ruff0; frontend0 (296.1s wrapper), all111 Chromium cases passed4.7min, with Node helper/typecheck/isolated build included in npm validate. Summary0errors/12advisories/29unrelated manual notes. Candidate38 material hashes unchanged; local/remote baseline dd83612259daa0a34828f026093a19e90276ea76.
- 2026-10-06 advisories accepted: original tracked sidecars and unrelated journal warnings preserved; binary screenshots/minified generated bundle/fullproof JSON cannot be scanned by text heuristic, observed offline assets/fixtures reviewed; password literal hits are hashed account SQL and fixture-only credentials. New verification-only playwright config is intentionally outside product requirement affected_paths; direct human approval plus111-case full proof covers it. Prior malformed RULING-003/004 supersedes values are append-only history, not current authority; valid RULING-005 confirms direct human approval without deleting history. Existing Starlette deprecation, bundle-size and terminal-color warnings retained; no product warning or failed assertion accepted. No live acceptance claimed.
- 2026-10-06 deliver presentation: frozen W15 candidate23261bfa52caecc009238be067c6dc4917998b42d731159e4ea56cf6aabca155;21 authored paths (7added14modified),5 generated static paths (2added1modified2removed), workflow records/screenshot evidence separately inventoried. Two same-agent round6 lenses approved; no child/subagent. Scope excludes planning, other issues, release, merge/deployment/export. Original security and numeric findings corrected; authorized five cycles and480s global verification budget stated transparently. Await coordinator acceptance before any commit/push/closure.

- 2026-10-06 presentation count correction:21 authored paths are5added/16modified; the separately inventoried5 static paths are2added/1modified/2removed. Earlier7added included the2 generated assets; frozen scope and bytes unchanged.

- 2026-10-06 delivery ACCEPTED: Coordinator chat01a10aec-6ac2-79f3-ada3-741950212fb8 verified all38 material hashes, candidate23261bfa52caecc009238be067c6dc4917998b42d731159e4ea56cf6aabca155, full journal/spec/issue/review, trust boundaries/tests and desktop/mobile screenshots; found no additional relevant issue. Coordinator verified actual direct human limit-extension messages and confirmed standing HUMAN publication authority conditional on this acceptance. Approved exact frozen candidate plus disclosed inventory/review/validation log/journal/five proof artifacts: normal scoped commit/push on task/adore-web-interface, English criteria/evidence update and closure of#19, then journal-only closeout commit/push. Preserve ignored anchor/evolution; epic#3 stays open; no other issue/PR/merge/release/force-push/live acceptance. Independently rechecked current38 hashes, branch/base before staging.

## Rulings

- RULING-001 | date=2026-10-06 | decision=Standing HUMAN authority relayed by coordinator authorizes autonomous stages through validation, scoped commit/push/closure only after coordinator delivery acceptance; no publication yet. | reason=Explicit task instruction, overrides routine checkpoints; never validation. | source=user | supersedes=none
- RULING-002 | date=2026-10-06 | decision=Use exclusively repository AEGIS; same-agent distinct review lenses, no claim of independent reviewers. | reason=Human selected workflow and prohibited additional paid agents/tools. | source=user | supersedes=none
- RULING-003 | date=2026-10-06 | decision=Authorize one additional corrective cycle, maximum four total; do not reset counter. Keep 20 authored paths and complete verification. | reason=Persisted legacy project credential URL finding at original cycle bound. | source=Direct human reply: Autorizez un ciclu suplimentar | supersedes=three-cycle maximum in Frame only

- RULING-004 | date=2026-10-06 | decision=Authorize fifth corrective cycle and21 authored paths, solely increase suite global timeout to480s and rerun strict full verification. | reason=Repeated incomplete111-case suite at240s despite passing assertions. | source=Direct human reply "can you add this?" to the enumerated proposal | supersedes=RULING-003 cycle/path maxima only

- RULING-005 | date=2026-10-06 | decision=Direct human authorizes five total corrective cycles and21 authored paths, with480s global browser timeout and complete strict proof; no publication authorization added. | reason=Restates the direct approvals in RULING-003/004 in valid machine-readable syntax while preserving their append-only history. | source=user | supersedes=none

## Handoff

current: deliver
status: ready
next: Commit/push accepted candidate, update and close issue19, then journal-only closeout.
must_read: .agentic/specs/audit-candidate-inventory.md, .agentic/specs/audit-candidate-review.md
blockers: none

## Stage report

stage: deliver
result: in_progress
current: deliver
changed: 21 authored paths; 5 generated static paths; workflow and screenshot evidence inventoried separately
evidence: Strict full check exit0; 1145 Python passed/1existing skip; Ruff passed; 111 Chromium passed
issues: 12 explained advisories; no unresolved blocker
next: Deliver accepted candidate and verify remote, issue closure and clean status
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 6

## Delivery report (2026-10-06)

- stage: deliver; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-DATA-34ed1530 - Structured committed redacted audit evidence
  - REQ-SEC-9415d21d - Redacted audit projections
  - REQ-REL-1dc9b68c - Truthful audit rollback and replay
  - REQ-DATA-196dcd48 - Atomic audit schema upgrade and legacy readability
  - REQ-UX-0ae52a96 - Authorized filtered change history and administrative retention
  - REQ-FUNC-a6d68c4a - Administrative independent retention policy
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=6
- diff vs task base dd83612: 47 file(s) changed, 4751 line(s) added; 3 file(s) not content-scanned
- checks: errors=0 warnings=12 notes=29
- checklist: 4/6 done; open: approved commit/push/issue-close outcome delivered; close-out recorded after successful delivery
