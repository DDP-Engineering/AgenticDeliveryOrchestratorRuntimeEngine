<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-74eebc5c - Issue 8 exact server TOML enrollment

stage: deliver
type: feature
path: full
interaction: autopilot
requirements: REQ-UX-3b5b2257, REQ-FUNC-c987bc4a, REQ-REL-39c1b197, REQ-DATA-71853fbc, REQ-FUNC-7ce5b17a
parent:
branch: task/adore-web-interface
base: 2c8dd9d49d7758de59892f171789bf6360ba7255
opened: 2026-10-05

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] coordinator verification and delivery instructions received under standing human authority
- [x] journal and report included in the delivery commit
- [ ] agreed scoped commit/normal push and issue 8 closure delivered; epic remains open
- [ ] journal-only close-out committed after the outcome succeeded

## Frame

Problem: Exact import hides server assumptions and offers insufficient review.
Desired outcome: Understandable, exact, revision-safe administrator enrollment with stopped pickup.
Actors: Administrator; Dev denied by API; ADORE server owns paths/state/probes.
Primary scenario: Select existing UTF-8 TOML -> declare profile identity -> inspect paths -> validate -> explicitly probe or retain unverified -> review -> enroll exact bytes stopped.
Examples: A CRLF TOML with absolute server paths and existing terminal history remains byte-identical and retains that history.
Counterexamples: Browser-relative paths, secrets, changed identity/file, concurrent ownership, active/corrupt state or locks cannot enroll.
In scope: #8 only; six-step memory wizard, consequential safe review, structured corrections, additive explicit import-check, strengthened candidate binding and offline boundary tests/docs.
Out of scope: Portability/cloning, presets, migration, other tickets, planning edits, dependency/tool setup, releases, live probes/acceptance, PR/merge/deployment.
Constraints: Four hours; three corrective/review cycles; twenty authored product/doc files; workflow/generated separate; additional executor USD 0; no subagents/executors. Existing locales/themes/branding and enrollment contracts preserved.
Success signals: Visible explanations and guarded exact review; offline tests for every listed boundary; required fresh final full proof.
Evidence: STATED delegation/current #8 and human direct-AEGIS clarification; OBSERVED clean task/adore-web-interface HEAD and origin 2c8dd9d, authenticated #8 open and native dependency #7 closed, app.py import inspection/publication and tests; INFERRED reuse _probe_setup is minimal; UNKNOWN live novice/server acceptance remains human.
Assumptions: UTF-8 exact file is host-specific; browser owns only memory draft; underlying history is server-resident.
Unknowns: Live prerequisite health and novice usability, excluded from automated claims.
Decision-blocking questions: None under standing human authority.
Proposed behaviors: Explain source/effects; canonical review; explicit revision-bound probe; retained correction invalidates preview; locked fail-closed confirmation.
Path and reason: full. Criterion | yes/no | evidence: unchanged observable behavior=no (wizard); no new interface=no (import-check/review); no dependency=yes; existing complete requirement=no (candidate identity binding); no security/data change=no (stronger binding). Single tightly coupled task, no children.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Understanding | Explanatory steps and review | REQ-UX-3b5b2257 | Complete visible review | Invalid review withheld | import browser suite | ImportWizard/importCopy |
| Explicit checks | Ephemeral bounded import probe | REQ-FUNC-c987bc4a | Bound evidence | Stale/invalid/Dev/CSRF/timeout | test_web_import.py | reuse _probe_setup |
| Safety | Exact stopped candidate publication | REQ-REL-39c1b197 | Exact bytes and retained history | All path/state/lock/ownership/input failures | test_web_import.py | locked reinspection |
| Correction | Memory draft and invalidation/loss | REQ-DATA-71853fbc | Back retains draft | Stale response/file, failed submit, leaving | import browser suite | mounted state and generations |
| Existing boundary | Legacy import validation/permissions | REQ-FUNC-7ce5b17a | Existing copy/pause | Existing trust boundaries | existing import tests | preserve public import routes |


## Design

REQ-UX-3b5b2257: ImportWizard owns six steps and safe allowlisted review; importCopy localizes visible guidance. App owns mount/session/route context and refresh. Existing accessible enrollment CSS is reused.
REQ-FUNC-c987bc4a: Minimal import-check closes observed no-prepublication-probe gap by reusing _probe_setup and existing errors; no new dependency/service.
REQ-REL-39c1b197: Canonical digest binds file plus declared identity, resolved physical paths and inspected ownership/state; config_revision separately identifies exact bytes. _publish_paused accepts optional reviewed import input and reinspects within shared enrollment then conductor lock before writing. Ordinary guided publication stays unchanged.
REQ-DATA-71853fbc: Internal Back/Change retains draft but invalidates review; file re-read, fatal UTF-8/BOM preservation, generation/ref guards and navigation loss follow existing EnrollmentWizard patterns.
REQ-FUNC-7ce5b17a: Preserve exact bytes, pause before metadata visibility, rollback, state/config locks, typed errors and existing history. Secret-bearing candidate never produces review values; all errors contain safe field pointers.
Compatibility: existing request shape/routes retained; revision is opaque and now binds full candidate; no durable schema/migration. Ephemeral probes remain advisory for stopped enrollment; no claim of live readiness/novice acceptance.
Concurrency: enrollment lock serializes new owners; target conductor lock protects final state read and pause; direct host edits remain outside managed locks and are reinspected as far as the boundary can observe.
Risks: browser file APIs vary; re-read fails closed. Host conditions can change after probe; evidence is honest time-bound snapshot. No architecture boundary expansion; additive route and mounted view only.
Expected files: styles.css (long-title wrapping), app.py, test_web_import.py, ImportWizard.tsx, importCopy.ts, App.tsx, i18n.ts, e2e/import.spec.ts, e2e/server.py, two component docs, Web_Interface.md, CHANGELOG.md, knowledge/context plus workflow and generated assets separately.
Open decisions: none. Rejected alternative: guided-answer reconstruction would rewrite unknown keys/comments/bytes and violate exact mode.


## Log

- 2026-10-05 build red: REQ-REL-39c1b197 `uv run pytest -q tests/test_web_import.py -k malformed_revision`, exit=1 (one Unicode revision comparison TypeError, two passing malformed ASCII cases). Reject non-64-hex input before constant-time comparison to preserve typed fail-closed import/check responses.

- 2026-10-05 build green: Latest focused API import proof exit=0, 38 passed/one existing warning, 15.99s; resolved physical path binding and verified/partial/failed/error evidence covered. Focused integration proof before actual-location refinement: `uv run pytest -q tests/test_web_import.py tests/test_web_enrollment.py tests/test_web_errors.py tests/test_web_readiness.py`, exit=0, 123 passed, 56.95s. Browser `npm run test:e2e -- import.spec.ts`, exit=0, 12 passed, 26.8s before final allowlist/path refinements; final focused browser proof pending. No live commands, executors or subagents.
- 2026-10-05 build: Same-change operator/API/frontend docs, changelog and knowledge/context reconciled. Twelve authored product/doc paths plus workflow, generated assets pending. Internal implementation/testing refinements stay within agreed scope; corrected test navigation waiting semantics and request counting without weakening checks/timeouts.

- 2026-10-05 build red: REQ-REL-39c1b197 actual-location refinement; `uv run pytest -q tests/test_web_import.py::test_import_reviews_all_locations_and_binds_declared_identity` exit=1; resolved_paths absent. Canonical review/digest will include resolved server paths so changed symlink targets cannot confirm an unreviewed physical location; declared TOML remains unchanged.

- 2026-10-05 build green: REQ-FUNC-c987bc4a/REQ-REL-39c1b197 focused `uv run pytest -q tests/test_web_import.py` exit=0, 12 passed/one existing dependency warning, 6.83s. Exact bytes, identity/file binding, all absolute/non-root locations and failed ephemeral probes proven.
- 2026-10-05 build red: REQ-UX-3b5b2257/REQ-DATA-71853fbc `npm run test:e2e -- --grep "exact enrollment explains"` exit=1; missing visible file-source/exact-enrollment explanation is expected failure; typecheck and isolated build passed.

- 2026-10-05 build red: REQ-FUNC-c987bc4a/REQ-REL-39c1b197; command=`uv run pytest -q tests/test_web_import.py -k "reviews_all or explicit_check or each_relative"` from 04_Software; exit=1, 8 expected failures: config_revision/review absent, import-check absent (405), volume-root findings missing or not field-addressed.

- 2026-10-05 specify: Behavior inventory audited; three new atomic requirements, one revised internal Back/loss contract, one existing import boundary reused; exact spec records wire/state/correction semantics.
- 2026-10-05 design: Accepted smallest import-check/review/binding extension; design and spec map every requirement to test seams; no open decisions, children or dependency expansion.

- 2026-10-05 frame: Scope accepted under standing authority; full path chosen for exact enrollment UI and additive probe/binding contracts. Native #7 dependency is closed; remote/local baseline match. Optional BMAD render helper and setup sibling absent; clarified human instruction authorizes direct AEGIS only; no BMAD workflow/install executed.

- 2026-10-05 build completed: Final focused `uv run pytest -q tests/test_web_import.py` exit=0, 41 passed/one existing dependency warning, 17.12s; `ruff check adore/web/app.py tests/test_web_import.py` passed. Latest import browser proof exit=0, 12 passed, 23.0s with typecheck/isolated build. Requirements activated and linked; source/docs evolved within scope. Three historical AEGIS advisories retained (two tracked fingerprint sidecars; old TASK-5e99ee1d Handoff; old TASK-c765e6b4 ruling), no current candidate format error.

- 2026-10-05 validate semantic review: malformed JSON description can reach canonical UTF-8 digest with an unpaired surrogate. Return to build for one value-free typed rejection and public-route negative test; scope unchanged, formal verdicts not yet issued.

- 2026-10-05 build inspection: the suspected description encoding gap is already rejected by Pydantic as HTTP 422 invalid_request with field-addressed description finding. Public-route negative test confirms existing fail-closed behavior on all three routes; no implementation correction required. Initial test expected 400 and was corrected to the observed documented request-validation contract. Return to validate.

- 2026-10-05 validate review: separate primary-agent specification-compliance and implementation-quality verdicts approved, round 1, same stable candidate `a4bcfedaa6777907cefee26ae9b00931f08f02b60d6346f46e34ca8a3182fe9c`; 0 corrective review cycles, no subagents. ISSUE-8-review.md records semantic/architecture/context/requirement and visual/secret inspections. Evolution refreshed: 17 product/generated paths; 12 authored, 5 generated, 7 stable workflow paths; final full proof pending.

- 2026-10-05 validate final gate exit=1: canonical Python test and lint passed; frontend 42 passed/3 failed (FR/DE/RO import guidance). Existing enrollment tests persist account language en, which correctly overrides test localStorage. This exposed an import browser fixture isolation error. Return to build for account-preference setup/reset; both verdicts cleared; corrective cycle 1 of maximum 3. Preserve failing proof in ISSUE-8-final-validation.json until fresh final gate replaces it; counts/outcome retained here.

- 2026-10-05 validate round 2: account preference isolation corrected; focused import Playwright diagnostic status passed/no failedTests, processes completed. Generated asset requirement references reconciled. Renewed independent-question primary-agent spec/quality verdicts approved for `8f4edfd8cfa479840664b8d1674f914044c5a4698dbff76d9d71e22aca18f1ad`; one corrective cycle of three used, 12 authored/5 generated/8 stable workflow paths. Final full proof rerun follows.

- 2026-10-05 validate completed: `python .agentic/aegis.py check --task TASK-74eebc5c --strict --run --json`, exit=0; configured Python 865 passed/1 skipped/1 existing Starlette deprecation warning (154.65s), Ruff passed, frontend helper/typecheck/isolated build plus 45 Chromium journeys passed (1.2m). Strict passed; catalog result WARN, 0 errors/5 warnings/30 historical manual notes. Supplemental whole-software `uv run ruff check .` and production `npm run build` passed. Earlier final gate failure was corrected and replaced by this full proof.
- 2026-10-05 validate advisories: three historical catalog warnings (two tracked fingerprint sidecars, old TASK-5e99ee1d Handoff, old TASK-c765e6b4 ruling) remain outside scope. Two automatic content-scan gaps were completed manually: full final proof JSON has zero matches for all built-in secret patterns; full generated bundle has only React password input mapping/four localized labels, no credential values. Existing Vite chunk-size and Node color advisories are nonfatal. No required proof omitted/weakened; no live novice/forge/container/model/full-accessibility acceptance claimed.
- 2026-10-05 deliver handoff: confirmed unchanged stable candidate `8f4edfd8cfa479840664b8d1674f914044c5a4698dbff76d9d71e22aca18f1ad`, 12 authored/5 generated/8 stable workflow paths plus four lifecycle/evidence records, review round 2 approved/approved, one corrective cycle of three. HEAD/origin remain 2c8dd9d; no commit, push, PR, merge, tag, release or issue closure. Await coordinator verification/instructions under RULING-001; no new human approval request.

- 2026-10-05 deliver evidence updates: authenticated English final comments #8 id 2038 and epic #3 id 2040 created and read back; line endings normalized for comparison. Acceptance/closure and publication remain pending coordinator gate; epic open.

- 2026-10-05 deliver authorization: coordinator thread 01a10aec-6ac2-79f3-ada3-741950212fb8 reports completed full journal/review/ownership/acceptance/API/whitespace inspection and verifies all 25 stable paths/hashes/deletions plus strict evidence. Under standing human authority it instructs scoped #8 commit/normal push, remote verification, acceptance/closure readback, epic-open English evidence and post-success journal-only closeout; no new issue/PR/merge/release/live acceptance. Primary agent independently reconfirmed unchanged inventory, matching local/remote baseline and empty index before publication.

## Rulings

- RULING-001 | date=2026-10-05 | decision=Autopilot through final validation; scoped commit/normal push/closure only after coordinator verifies stable candidate and instructs delivery | reason=Standing human delegation and follow-up direct-AEGIS clarification | source=user | supersedes=none
- RULING-002 | date=2026-10-05 | decision=Reuse bounded _probe_setup through import-check and add canonical review/identity binding | reason=Observed existing readiness requires guided input or published project, and raw-only hash does not bind display identity/description; no runtime-state migration or dependencies | source=technical | supersedes=none


## Handoff

current: deliver
status: ready
next: Commit and normally push scoped issue 8 candidate, then verify and close issue
must_read: .agentic/steps/6_deliver.md, .agentic/tasks/ISSUE-8-final-ownership.md, .agentic/tasks/ISSUE-8-review.md, .agentic/tasks/ISSUE-8-final-validation.json
blockers: none

## Stage report

stage: deliver
result: in_progress
current: deliver
changed: 12 authored product/doc paths, 5 generated assets, 8 stable workflow paths plus lifecycle evidence
evidence: strict exit 0; Python 865 passed/1 skipped; frontend 45 passed; Ruff/typecheck/production build passed
issues: 3 historical catalog warnings; 2 scan gaps manually completed; live novice/server acceptance excluded
next: Commit and normally push scoped issue 8 candidate, then verify and close issue
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-05)

- stage: deliver; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-3b5b2257 - Explain exact server TOML enrollment and review
  - REQ-FUNC-c987bc4a - Inspect and probe an exact import candidate
  - REQ-REL-39c1b197 - Bind exact enrollment to reviewed identity and safe ownership
  - REQ-DATA-71853fbc - Clear import draft when leaving the page
  - REQ-FUNC-7ce5b17a - Web project configuration and status
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 2c8dd9d: 29 file(s) changed, 1802 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=5 notes=30
- checklist: 4/6 done; open: agreed scoped commit/normal push and issue 8 closure delivered; epic remains open; journal-only close-out committed after the outcome succeeded
