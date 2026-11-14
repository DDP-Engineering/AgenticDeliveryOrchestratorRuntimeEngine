<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-4f256bac - LA-02 #93 Live agent activity for running jobs

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-fe8ecf4c, REQ-FUNC-20e2ffe7, REQ-REL-725d3e4a, REQ-UX-236cf3e2, REQ-UX-acc17615, REQ-FUNC-98358471, REQ-SEC-3e1a4ea4, REQ-SEC-97e45ffb, REQ-FUNC-116450ef, REQ-FUNC-c405688e, REQ-FUNC-a71d617b, REQ-SEC-0fb2bba3, REQ-SEC-f7b9111e
parent:
branch: master
base: dfa0f2cd99aa2fe36aaaaaf19daad6f3079796be
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

Problem: STATED (#93): authorized job readers need current Pi activity while a launch runs.
Desired outcome: STATED (#91/#93): bounded completed session items update every three seconds in Agent sessions, with unfinished tool/thinking status and safe archive/new-launch handoff.
Actors: STATED: admins and project-granted developers; structured costs remain admin-only.
Primary scenario: STATED: open working job, select Agent sessions, follow live append, then next launch; choose history without refresh stealing selection.
Examples: STATED: a partial last line appears only once complete; replacement or truncation signals session_ended.
Counterexamples: STATED: hidden tab/view and non-working jobs stop live polling; deltas/system messages never render.
In scope: STATED: shared reader/API, live UI/model/copy, launch identity evidence, offline tests, requirements/knowledge/component docs, help/releases and production assets.
Out of scope: STATED: #94 instructions, Projects/navigation redesign, migrations, real Pi/provider/container checks, remote Git/issue writes, deployment.
Constraints: STATED: same existing master checkout; local commit only; 90 minutes, 70 tracked files, three repair rounds per failing targeted check; AEGIS autopilot; integrated/full suites deferred to parent after #94.
Success signals: STATED: issue Done-when items including grow/partial/replace/truncate boundaries, preserved history, explicit working/visibility polling gates and authenticated no-store role-limited reads.
Evidence: OBSERVED: clean master dfa0f2cd99aa2fe36aaaaaf19daad6f3079796be; Gitea GET #91/#93 current descriptions; completed approved TASK-ae44ba07. launcher.py PiExecutor.run_gate owns RPC/archive lifecycle; pi_rpc._Evidence opens wb; old output remains between sessions.
Assumptions: INFERRED: a launch-owned ephemeral marker plus prefix-bound cursor evidence can establish continuity without using changing mtime as session identity.
Unknowns: UNKNOWN: real host/account readability acceptance is owner-owned; no live acceptance run authorized.
Decision-blocking questions: none; implementation can read the existing host-owned io folder.
Proposed behaviors: none outside accepted scope.
Path and reason: full; new externally visible polling and live transport.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | STATED live updates |
| no new interface or data format | no | INFERRED live response and marker |
| no new dependency | yes | OBSERVED stdlib/React suffice |
| existing requirement covers behavior | no | OBSERVED history only |
| no security or data handling change | yes | STATED same #92 boundaries |

## Requirement coverage

| Behavior | Requirement | Design | Proof |
|---|---|---|---|
| List active launch before archived sessions | REQ-FUNC-fe8ecf4c | Shared reader and live view | Targeted offline API/model/browser |
| Poll completed live session records | REQ-FUNC-20e2ffe7 | Shared reader and live view | Targeted offline API/model/browser |
| End changed live session cursors | REQ-REL-725d3e4a | Shared reader and live view | Targeted offline API/model/browser |
| Gate live polling and preserve history selection | REQ-UX-236cf3e2 | Shared reader and live view | Targeted offline API/model/browser |
| Show unfinished agent work without text deltas | REQ-UX-acc17615 | Shared reader and live view | Targeted offline API/model/browser |
| RPC/package/native retention policy reconciliation | REQ-FUNC-116450ef, REQ-FUNC-c405688e, REQ-FUNC-a71d617b, REQ-SEC-0fb2bba3, REQ-SEC-f7b9111e | Owner #91 raw sessions; sanitized operations | Public producer-to-live/archive API and RPC tests |
| Existing grouped item and security contracts | REQ-FUNC-98358471, REQ-SEC-3e1a4ea4, REQ-SEC-97e45ffb | unchanged projection/authorization | retained API tests |


## Design

### Approach
REQ-FUNC-fe8ecf4c: extend PiExecutor RPC/archive scope with a random launch-owned marker and existing crash-released StateStore kernel lock, created only after stale output is cleared; finally cleanup covers faults and abandoned markers fail liveness. Planned exact archive id maps live handoff. This necessary launcher seam distinguishes active execution from retained files between sessions.
REQ-FUNC-20e2ffe7: extend the one existing bounded reader to live sources; retain grouped source parts, limits and byte cursors. Live EOF retains complete-line offset for later append. Normal appends do not invalidate reads.
### Interfaces and data
REQ-REL-725d3e4a: launch UUID plus file identity and prefix digest fences replace/truncate/regrow; ended responses carry archive id. Marker and run ownership are rechecked before accepting a page. No schema migration or compatibility reader.
REQ-SEC-97e45ffb (owner #91): persist bounded RPC stdout literally while retaining sanitized operational tails/stderr/questions/diagnostics. Package launches copy this same raw session file into archives rather than rewriting it to a sanitized tail; the copy preserves regular-file identity and recording byte bounds. Existing stored recordings remain untouched.
REQ-UX-acc17615: expose bounded thinking start/end hint; tool start/end uses existing completed items. No text deltas. SessionModel tracks unfinished tools and thinking across pages.
### Files and test seams
Shared executor_session/app, launcher/RPC immediate record persistence and lifecycle tests, SessionView/sessionModel/JobDetails and four-locale copy/help. Keep SessionView mounted once visited, pass active-view and saved lifecycle so hidden tabs preserve state and stop polling. API/model/browser tests exercise trust boundaries; update Web Jobs/Frontend/Launcher docs and web-interface/executor-launcher knowledge.
REQ-UX-236cf3e2: three-second timer only for active visible working live selection; list reconciliation retains explicit archive selection. Live end reloads archive completely or follows new live so unseen final records survive.
### Risks and open decisions
Existing #92 authentication/no-store/system exclusion/cost rules unchanged. Prefix hashing is bounded by 64 MiB; parse scan stays bounded by 4 MiB. No real runtime acceptance; parent owns integrated suite. No blocking product decisions.
### Requirement map
Each of the five coverage requirements maps to its named paragraph and targeted tests; existing REQ-FUNC-98358471 and security requirements retain the projection and guards.
Diagrams: [diagram_TASK-4f256bac.md](diagram_TASK-4f256bac.md)


## Log

- 2026-11-14 frame: journal opened
- 2026-11-14 frame: DEVIATION validate: Full integrated suites and --run deferred to parent after #94 by explicit user instruction; targeted proof and independent review retained.
- 2026-11-14 frame: completed; next specify
- 2026-11-14 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-14 design: completed; next build
- 2026-11-14 build: red: uv run --frozen --extra web python -m pytest -q tests/test_web_executor_session.py -k live exit 1; eight expected failures: live source/list/cursor unsupported (REQ-FUNC-fe8ecf4c, REQ-FUNC-20e2ffe7, REQ-REL-725d3e4a)
- 2026-11-14 build: red: pytest tests/test_pi_rpc.py -k live_launch exit 1; two expected missing launch marker failures (REQ-FUNC-fe8ecf4c)
- 2026-11-14 build: green: targeted live reader tests exit 0, 8 passed; red: node --test tests/sessions.test.mjs exit 1, missing live polling/activity exports (REQ-UX-236cf3e2, REQ-UX-acc17615)
- 2026-11-14 build: Live ownership now reuses StateStore crash-released kernel locks; abandoned marker does not establish liveness. Continuity comparison precedes newline validation for valid rewritten cursors.
- 2026-11-14 build: release-notes: added
- 2026-11-14 build: help: updated
- 2026-11-14 build: green: targeted Python session/jobs/RPC files 224 passed, 4 Windows symlink skips; added mid-read rewrite and live parts/roles proof 3 passed; session/help model tests 18 passed; Ruff scoped checks exit 0.
- 2026-11-14 build: Browser repair round 1: live append/hidden/history, handoff and compact header passed; retained real archive read exposed initial empty-selection generation invalidating its list response. Skip the empty-selection effect before any selection.
- 2026-11-14 build: DEVIATION build: Additional mid-read race, role projection and browser regression assertions were added after implementation; initial public API and polling/activity model red evidence preceded implementation.
- 2026-11-14 build: completed; next validate
- 2026-11-14 validate: returned to build - Independent review: flush persisted RPC records; verify continuity without buffered cache; terminate EOF loops on concurrent truncation
- 2026-11-14 build: red review-round1: short RPC record remains buffered before close; two-record limit-one rewrite accepts stale read-ahead; mid-record truncation loops on empty read (3 targeted failures reproduced). Browser stale/history/terminal repair passed.
- 2026-11-14 build: green review-round1: producer visibility, two-record limit-one fresh-descriptor rewrite, and finite mid-record truncation tests 3 passed; scoped Ruff passed; model/help18 passed. Added direct persisted-record flush in pi_rpc; bounded reader no-progress guards and independent descriptor proof.
- 2026-11-14 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-14 validate: Independent specification and quality reviewers approved current candidate in round2; quality reviewer public rewrite/truncation/marker subset 7passed. Production and isolated frontend builds passed (index-BeD5Yafd.js). Final proof is targeted only under explicit parent deferral.
- 2026-11-14 validate: DEVIATION validate: Parent boundary review found pre-existing producer masking conflicts with owner-approved #91 exact session visibility. Reconcile raw bounded RPC stdout/live/archive only; operational tails, stderr, questions, diagnostics and forge evidence remain sanitized. No old recordings rewritten.
- 2026-11-14 validate: returned to build - Owner-backed producer-to-reader no-redaction reconciliation; invalidate prior proof and review for current candidate
- 2026-11-14 build: red producer reconciliation: 3 prior archive/provider-policy assertions and 2 producer-to-live/archive cases fail because persistence masks values or rewrites package stdout; explicit #91 policy is the oracle.
- 2026-11-14 build: green producer reconciliation: five public producer/package/provider cases passed. Added literal live/archive samples for known binding/package credentials and key-hint/Bearer shapes; operational tails/stderr/diagnostics remain sanitized. Owner-backed superseded archive assertion renamed and requirement links reconciled.
- 2026-11-14 build: red raw-archive boundary: public hardlink and over-recording-limit cases fail closed expectation (2 failures); raw copies must preserve the standard recording trust/size boundaries without rewriting.
- 2026-11-14 build: green owner-backed reconciliation: literal RPC live/archive, known package/binding secrets, key-hint/Bearer samples and sanitized operations: 7 passed including hardlink/oversize raw-archive denials; scoped Ruff pass. Prior targeted final proof 234pass4skip and browser5pass is historical before this reconciliation; fresh producer proof required.
- 2026-11-14 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-14 validate: returned to build - Review3: reconcile broad native/subscription retention requirements; fail closed on missing raw output and linked archive destination
- 2026-11-14 build: red review3: missing raw output manufactures a sanitized transcript and linked/reparse archive destination allows redirection (2 public failures reproduced); active native/subscription broad retention promises reconciled with owner #91.
- 2026-11-14 build: green review3 repair: 9 producer/archive-policy cases pass, including missing recording rejection, hardlink/oversize denial and real Windows junction destination denial without external writes. Native/subscription active requirements now distinguish literal job-session recordings from sanitized operational/model-check evidence.
- 2026-11-14 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-14 validate: Recovery: human owner explicitly continued same checkout with up to60 additional minutes after runtime usage error; preserve existing #93 candidate, targeted-only proof and local master commit. Existing review agents retried for round4; no implementation restart.
- 2026-11-14 validate: Independent spec and quality review4 approved current candidate after requirement and archive-boundary repairs. Quality reviewer raw-archive public subset4passed including actual Windows junction. Native/subscription14 targeted checks passed. Final targeted proof follows, without full suites or --run.
- 2026-11-14 validate: Final focused quality follow-up confirmed archive resume state defect: non-null cursor auto-loads history; EOF reloads page1 and discards loaded pages. Preserve accepted archive state; resume only live or unaccepted initial read. Backend proof remains current; frontend proof will be refreshed.
- 2026-11-14 validate: returned to build - Preserve archived pagination across hidden session/browser tab views; track initial page acceptance separately from EOF
- 2026-11-14 build: green current backend final proof: 325 passed, 4 Windows symlink privilege skips across session/jobs/RPC/executor/system-packages files; native/subscription14passed. Backend files remain unchanged during the final frontend-only pagination repair.
- 2026-11-14 build: red retained-pagination regression: hidden-view partial archive auto-pages; EOF resets history (two browser cases, expected missing preservation). Added explicit accepted-initial-page tracking; only live or unaccepted initial reads resume.
- 2026-11-14 build: green retained-pagination: 4 focused browser cases passed (partial archive, EOF with loaded pages, in-flight initial read, failed initial read). Production/build:e2e pass for index-CGLuBZGu.js; backend325pass4skip and native14pass remain valid with unchanged Python bytes.
- 2026-11-14 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-14 validate: returned to build - Clear stale loading state when a hidden accepted archive's Load more request is invalidated; preserve explicit retry at its cursor
- 2026-11-14 build: red review5: held archived Load more remains disabled after hidden-view invalidation; public browser test reproduces stale loading flag. Clear loading on generation invalidation without changing accepted pages/cursor.
- 2026-11-14 build: green review5 repair: five archive-state browser cases pass, including interrupted Load more explicit retry with old cursor and no duplicate items. Production/build:e2e rebuilt index-B4Uo99ly.js; release-note validator and diff whitespace checks pass. Only UI loading invalidation changed; backend proof remains current.
- 2026-11-14 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-14 validate: Independent specification and quality reviews6 approved final candidate; no remaining actionable findings. Final frontend/diff/assets/strict proof follows last UI edit. Existing current Python component325pass4skip and native/subscription14pass evidence retained because Python bytes have not changed.
- 2026-11-14 validate: final: cwd=04_Software; uv run --frozen --extra web python -m pytest -q tests/test_web_executor_session.py tests/test_web_jobs.py tests/test_pi_rpc.py tests/test_executor.py tests/test_system_packages.py; exit 0; 325 passed, 4 Windows symlink-privilege skips; backend bytes unchanged by subsequent UI-only repairs
- 2026-11-14 validate: final: cwd=04_Software; uv run --frozen --extra web python -m pytest -q tests/test_local_execution.py::test_native_gate_uses_managed_rpc_and_ignores_hostile_personal_pi tests/test_local_execution.py::test_local_environment_ignores_personal_auth_and_forge_credentials tests/test_local_execution.py::test_local_environment_keeps_windows_system_names tests/test_local_execution.py::test_native_launch_records_ownership_before_release_and_redacts tests/test_native_chatgpt.py::test_native_stage_token_is_explicit_and_redacted tests/test_native_chatgpt.py::test_native_model_probe_uses_subscription_source tests/test_chatgpt_stage.py::test_the_stage_token_reaches_only_this_gate_and_is_redacted; exit 0; 14 passed; native/subscription filtering, operational masking and model-check protection
- 2026-11-14 validate: final: cwd=04_Software/web; node --test tests/sessions.test.mjs tests/help.test.mjs; exit 0; 18 passed
- 2026-11-14 validate: final: cwd=04_Software/web; npm run typecheck; exit 0; application and e2e TypeScript checks passed
- 2026-11-14 validate: final: cwd=04_Software/web; npm run build; exit 0; final production asset index-B4Uo99ly.js stamped; existing Vite chunk-size warning accepted
- 2026-11-14 validate: final: cwd=04_Software/web; npm run build:e2e; exit 0; isolated production-equivalent asset index-B4Uo99ly.js and typechecks passed
- 2026-11-14 validate: final: cwd=04_Software/web; npx playwright test e2e/jobs.spec.ts --grep 'LA-02|LA-01 compact|LA-01 finished' --max-failures=3; exit 0; 10 passed after final UI edit and review6; live append/visibility/handoff, stale reads, history selection/pagination/initial errors/interrupted Load more, compact shell and real archived fixture
- 2026-11-14 validate: final: cwd=repository root; uv run --project 04_Software --frozen ruff check 04_Software/adore/web/executor_session.py 04_Software/adore/web/app.py 04_Software/adore/executor/launcher.py 04_Software/adore/executor/pi_rpc.py 04_Software/tests/test_web_executor_session.py 04_Software/tests/test_pi_rpc.py; exit 0; all scoped Ruff checks passed
- 2026-11-14 validate: final: cwd=repository root; python 02_Tools/internal/check_release_notes.py --since dfa0f2cd99aa2fe36aaaaaf19daad6f3079796be; exit 0; release notes contract passed
- 2026-11-14 validate: final: cwd=repository root; python 02_Tools/internal/check_release_consistency.py; exit 0; release identity, fingerprints and independent fresh-build comparison passed
- 2026-11-14 validate: final: cwd=repository root; git diff --check; exit 0; no whitespace errors
- 2026-11-14 validate: final: cwd=repository root; python .agentic/aegis.py check --task TASK-4f256bac --strict; exit 0; errors=0 warnings=72 notes=28; strict ok; --run deliberately not invoked
- 2026-11-14 validate: Final limits/inspection: 53 changed paths before staging, within70; explicit recovery60-minute extension honored; no full suites/--run, actual Pi/provider/container work, remote Git/forge mutation, deployment or #94. Full integrated proof and Linux symlink acceptance remain parent-owned. Existing Starlette/Vite warnings and 70 existing AEGIS requirement/path/header warnings remain; additional scanner warnings concern synthetic Bearer test text and generated minified asset (verified by fresh-build comparison), not real credentials. Four independent review repair cycles ended with both approvals in review6. Compact shell/global navigation preserved by diff inspection and retained browser proof.
- 2026-11-14 validate: completed; next done

## Rulings

- RULING-001 | date=2026-11-14 | decision=Apply #91 no-masking policy at RPC session persistence and package-job archival; preserve sanitized operational evidence | reason=Owner-backed parent clarification during final proof identifies masking before shared reader; existing epic decision authorizes literal recorded values | source=user | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-4f256bac.md
changed: Implemented #93 live sessions, preserved history and raw-session/operational boundaries; docs/help/releases and production assets current
evidence: 325 component Python +14 native cases passed;4 Windows link skips;18 model/help +10 browser passed; Ruff/typecheck/build/assets/releases/strict passed; reviews6 approved
issues: Full integrated suites/--run deferred to parent after #94; Linux links and real Pi/provider/container acceptance remain owner checks
spec_compliance: approved
implementation_quality: approved
review_round: 6

## Delivery report (2026-11-14)

- stage: validate; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-fe8ecf4c - List active launch before archived sessions
  - REQ-FUNC-20e2ffe7 - Poll completed live session records
  - REQ-REL-725d3e4a - End changed live session cursors
  - REQ-UX-236cf3e2 - Gate live polling and preserve history selection
  - REQ-UX-acc17615 - Show unfinished agent work without text deltas
  - REQ-FUNC-98358471 - Read bounded recorded session pages
  - REQ-SEC-3e1a4ea4 - Confine session file reads
  - REQ-SEC-97e45ffb - Expose bounded operational executor evidence
  - REQ-FUNC-116450ef - Run a container Pi stage through one RPC process
  - REQ-FUNC-c405688e - Direct agent package installation
  - REQ-FUNC-a71d617b - Drive native Pi stages through RPC
  - REQ-SEC-0fb2bba3 - Each ChatGPT stage receives only a short-lived access token
  - REQ-SEC-f7b9111e - Inject approved native provider credentials
- deviations: 3 recorded
  - validate: Full integrated suites and --run deferred to parent after #94 by explicit user instruction; targeted proof and independent review retained.
  - build: Additional mid-read race, role projection and browser regression assertions were added after implementation; initial public API and polling/activity model red evidence preceded implementation.
  - validate: Parent boundary review found pre-existing producer masking conflicts with owner-approved #91 exact session visibility. Reconcile raw bounded RPC stdout/live/archive only; operational tails, stderr, questions, diagnostics and forge evidence remain sanitized. No old recordings rewritten.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=6
- diff vs task base dfa0f2c: 53 file(s) changed, 1789 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=72 notes=28
- checklist: 8/9 done; open: `report` appended

## Delivery report (2026-11-14)

- stage: done; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-fe8ecf4c - List active launch before archived sessions
  - REQ-FUNC-20e2ffe7 - Poll completed live session records
  - REQ-REL-725d3e4a - End changed live session cursors
  - REQ-UX-236cf3e2 - Gate live polling and preserve history selection
  - REQ-UX-acc17615 - Show unfinished agent work without text deltas
  - REQ-FUNC-98358471 - Read bounded recorded session pages
  - REQ-SEC-3e1a4ea4 - Confine session file reads
  - REQ-SEC-97e45ffb - Expose bounded operational executor evidence
  - REQ-FUNC-116450ef - Run a container Pi stage through one RPC process
  - REQ-FUNC-c405688e - Direct agent package installation
  - REQ-FUNC-a71d617b - Drive native Pi stages through RPC
  - REQ-SEC-0fb2bba3 - Each ChatGPT stage receives only a short-lived access token
  - REQ-SEC-f7b9111e - Inject approved native provider credentials
- deviations: 3 recorded
  - validate: Full integrated suites and --run deferred to parent after #94 by explicit user instruction; targeted proof and independent review retained.
  - build: Additional mid-read race, role projection and browser regression assertions were added after implementation; initial public API and polling/activity model red evidence preceded implementation.
  - validate: Parent boundary review found pre-existing producer masking conflicts with owner-approved #91 exact session visibility. Reconcile raw bounded RPC stdout/live/archive only; operational tails, stderr, questions, diagnostics and forge evidence remain sanitized. No old recordings rewritten.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=6
- diff vs task base dfa0f2c: 53 file(s) changed, 1816 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=72 notes=28
- checklist: 9/9 done
