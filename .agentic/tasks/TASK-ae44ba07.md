<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-ae44ba07 - LA-01 #92 Agent session history and retained job navigation

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-fb6236ba, REQ-FUNC-98358471, REQ-REL-4278b8fa, REQ-SEC-3e1a4ea4, REQ-UX-8c280c24, REQ-UX-b359952f, REQ-UX-7cc76f30, REQ-REL-5e4552df, REQ-SEC-97e45ffb
parent:
branch: master
base: 31fd0a0e392f692d8c2fa5019079e1d8347229c8
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

Problem: STATED (#92): job readers cannot inspect completed Pi attempt transcripts.
Desired outcome: STATED (#91/#92): authorized readers browse bounded recorded sessions and retain existing Jobs/Tickets operations in the approved compact layout.
Actors: STATED: administrators and project-granted developers; costs retain existing role restriction.
Primary scenario: STATED: open a finished job or an earlier completed attempt of an active job, select Agent sessions, inspect prompt/tools/usage and load more.
Examples: STATED: a fake key printed by a tool remains visible; readable reasoning starts collapsed.
Counterexamples: STATED: system messages and files outside the run never enter responses; live polling and instruction delivery belong to #93/#94.
In scope: STATED: session reader/routes/timeline, four detail tabs and compact status, global Jobs/Tickets split and automatic scoped ticket reads, targeted offline proof, requirements/help/docs/release notes.
Out of scope: STATED: Projects redesign, live updates, instructions, migrations, real provider/forge/runtime jobs, pushes/PRs/deployment/issue writes.
Constraints: STATED: existing master checkout, local commit; 120 minutes, 120 tracked files, three repair rounds per check; autopilot; full suite deferred to parent. OBSERVED: clean master at 31fd0a0e392f692d8c2fa5019079e1d8347229c8. No branch/worktree change authorized.
Success signals: STATED: #92 Done-when checks, retained list/scope/navigation state, authenticated no-store exact-recorded session responses, offline targeted API/browser proof.
Evidence: OBSERVED: tea issues 91/92 --comments --login ddp returned owner descriptions dated 2026-11-14, no comments; executor_evidence.py supplies path identity guards; launcher.py _archive_launch stores created_at and outcome but no start time.
Assumptions: INFERRED: created_at is archive completion evidence; start time stays unavailable unless recorded in session events. No fabricated timestamps.
Unknowns: UNKNOWN: real-provider acceptance; owner runs this later. No session start timestamp exists in archive metadata.
Decision-blocking questions: none; existing archive layout matches required folder layout, unavailable metadata will be explicit.
Proposed behaviors: none outside accepted issue scope.
Path and reason: full (new visible interface and reader).

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | STATED transcript UI |
| no new interface or data format | no | STATED sessions GET API |
| no new dependency | yes | INFERRED standard library/React suffice |
| existing requirement covers behavior | no | OBSERVED security rule must change |
| no security or data handling change | no | STATED owner permits recorded secrets |

## Requirement coverage

| Behavior | Requirement | Design | Proof |
|---|---|---|---|
| List completed agent attempts | REQ-FUNC-fb6236ba | reader/API or retained React workspace | targeted API/browser |
| Read bounded recorded session pages | REQ-FUNC-98358471 | reader/API or retained React workspace | targeted API/browser |
| Isolate malformed session records | REQ-REL-4278b8fa | reader/API or retained React workspace | targeted API/browser |
| Confine session file reads | REQ-SEC-3e1a4ea4 | reader/API or retained React workspace | targeted API/browser |
| Keep compact saved job details | REQ-UX-8c280c24 | reader/API or retained React workspace | targeted API/browser |
| Separate global Jobs and Tickets | REQ-UX-b359952f | reader/API or retained React workspace | targeted API/browser |
| Read global tickets on entry and scope change | REQ-UX-7cc76f30 | reader/API or retained React workspace | targeted API/browser |
| Fence ticket read completions | REQ-REL-5e4552df | reader/API or retained React workspace | targeted API/browser |
| Recorded visibility and cache policy | REQ-SEC-97e45ffb | separate transcript surface | API role/system/secret tests |


## Design

### Approach
OBSERVED: existing executor_evidence identity/read guards and authenticated job lookup are reusable unchanged. Add executor_session.py as the one reader of archived output, independent of diagnostics. Render it on-demand in Agent sessions with no polling.
REQ-FUNC-fb6236ba/98358471: enumerate exact physical archives, parse bounded complete JSONL lines and use byte cursors; map each source line to one item, grouping assistant text/reasoning/usage parts so every requested maximum is strict.
REQ-REL-4278b8fa: malformed/oversized records produce notices; no raw protocol envelopes leak through serialization.
### Interfaces and data
REQ-SEC-3e1a4ea4/97e45ffb: authenticated job lookup precedes file reads, repeat project grant check before response, no-store headers, existing identity/symlink guards at every parent; system and duplicate/delta records ignored. Costs only in structured usage for admins; user/tool text remains literal.
New list_sessions(run) and read_session(run, attempt_id, cursor, limit) take the verified run directory. Defaults cursor=0, limit=200. Unknown archive returns 404; invalid cursor/limit uses evidence error; no stored format changes.
OBSERVED: meta.json has archive created_at only. End uses it; start remains null. Saved exit_code/timed_out define physical-launch outcome without inferring job completion.
### Files and test seams
REQ-UX-8c280c24: JobDetails gets four tabs above title/status; operations and human controls stay in compact action area, budgets/usage remain available. JobWorkspace supplies session view using a new validated sessionModel and four-locale copy.
REQ-UX-b359952f/7cc76f30: add /tickets route and sidebar entry, retain /jobs filters and project-specific Jobs/Tickets/Capacity tabs unchanged. App owns global scope. Global JobWorkspace remains mounted during its detail; per-view retained filter records and an explicit origin snapshot preserve project/Overview/History close behavior while opening coherently in Jobs.
REQ-REL-5e4552df: TicketWorkspace automatic-read prop applies only globally; scope identity and generation fence stale results; synchronous pending guard prevents repeated reads.
Tests: new offline API reader tests based on spike fixtures; targeted jobs/tickets browser journeys plus model/help checks. Component documentation, Web_Interface, help and release notes updated with implementation.
### Risks and open decisions
STATED: transcripts can contain secrets by owner decision; authenticated no-store is required. No migrations, provider runs, live updates or instruction delivery. UNKNOWN: live acceptance deferred to owner. No blocking decisions.
### Requirement map
All nine coverage rows map to the reader/API, retained detail shell or scope-fenced ticket workspace above; no new dependency or product lifecycle.
Diagrams: [diagram_TASK-ae44ba07.md](diagram_TASK-ae44ba07.md)


## Log

- 2026-11-14 frame: journal opened
- 2026-11-14 frame: DEVIATION validate: Full-suite --run gate deferred to parent after #94 by explicit user instruction; targeted checks and independent review remain required.
- 2026-11-14 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-14 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-14 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-14 build: red: uv run --frozen --extra web python -m pytest -q tests/test_web_executor_session.py -x exit 1; authenticated sessions GET absent (404), after correcting test import path.
- 2026-11-14 build: green: targeted session API contracts exit 0 (12 passed, 4 symlink creation skips on host). red: node --test tests/routes.test.mjs exit 1 missing Tickets route; targeted LA-01 browser case exit 1 missing Jobs search on global entry.
- 2026-11-14 build: Review round 1: fix strict item limit using atomic assistant parts; retain scope-keyed pending reads and scope-fence mutation completion; restore coherent Jobs opening with saved origin/list state; reject huge cost integers; reconcile old guidance. No scope expansion.
- 2026-11-14 build: green: LA-01 focused browser scope/detail/action regressions 6 passed; session API 14 passed and 4 symlink-privilege skips; targeted lint passed. review fixes add strict grouped items, cost bound, scope reuse and delayed-operation fencing.
- 2026-11-14 build: release-notes: added
- 2026-11-14 build: help: updated
- 2026-11-14 build: DEVIATION build: some model, scope and review regression tests were added with or after their implementation instead of observing red first; API and navigation entry red evidence preceded implementation, and focused post-change assertions cover the remaining boundaries.
- 2026-11-14 build: Review round 2: retain the matching optimistic source revision with per-view filters so History page 2 survives detail navigation and Close; add exact public browser round-trip proof.
- 2026-11-14 build: Baseline expectation correction authorized by parent: existing Summary already renders seven operational facts plus three compact capacity facts. Targeted browser assertions now identify those groups without changing Projects rendering; old standalone capacity-panel expectation removed.
- 2026-11-14 build: green: targeted post-review History page2/compact Summary/Capacity browser selection exit 0, 3 passed; real archived Pi fixture read and retained job regressions green in the prior 9-case repair selection (6 passed, 3 then corrected selectors). Production build exit 0 and source/output fingerprint recomputation matched.
- 2026-11-14 build: DEVIATION build: first targeted four-file browser run stopped at eight failures (65 passed, 12 unrun); scope-bound repair selections preserve each observed failure and rerun only failed/new/unrun relevant journeys rather than repeat the complete selection.
- 2026-11-14 build: green: ticket workspace repair selection 17/18 passed; remaining old-account test had a stale global Jobs navigation selector and now opens Tickets. No product behavior changed for that selector correction.
- 2026-11-14 build: AEGIS advisory: strict check exit 0 with 70 pre-existing requirement/journal warnings plus generated minified bundle scan limitation; production input/output fingerprints match. Vite retains its existing large-chunk warning; no new dependency or hand-edited bundle.
- 2026-11-14 build: green: all 86 unique targeted browser journeys in jobs.spec.ts, tickets.spec.ts, projectCapacity.spec.ts and help.spec.ts passed across initial+bounded repair selections. First85-case selection:65pass8fail12unrun; repaired9-case selection:6pass3then-corrected selectors; final History/Summary/Capacity3pass; Tickets17pass1then-corrected stale navigation/read wait; final old-account1pass. No full frontend/E2E suite or --run gate executed.
- 2026-11-14 build: completed; next validate (1 Done checklist item(s) left unticked)
- 2026-11-14 validate: Review round 3 approved independently by spec_review and quality_review; both confirmed generated bundle/traceability fingerprints (138inputs7outputs) and the final test-only Tickets navigation/read-completion correction. All prior findings resolved.
- 2026-11-14 validate: final: from 04_Software: uv run --frozen --extra web python -m pytest -q tests/test_web_executor_session.py tests/test_web_jobs.py exit 0; 168 passed, 4 Windows symlink-creation skips, 1 existing Starlette deprecation warning.
- 2026-11-14 validate: final: from 04_Software/web: node --test tests/sessions.test.mjs tests/routes.test.mjs tests/jobs.test.mjs tests/help.test.mjs exit 0 (44 passed); npm run typecheck exit 0.
- 2026-11-14 validate: final: from 04_Software: uv run --frozen ruff check adore/web/executor_session.py adore/web/app.py tests/test_web_executor_session.py web/e2e/server.py exit 0.
- 2026-11-14 validate: final browser commands from 04_Software/web: playwright.cmd test e2e/jobs.spec.ts e2e/tickets.spec.ts e2e/projectCapacity.spec.ts e2e/help.spec.ts --max-failures=8: 65 passed, 8 failed, 12 unrun; repair selection jobs.spec.ts projectCapacity.spec.ts -g LA-01|hub separates|missing evidence|composite colliding|queued pending|compact summary|Capacity is: 6 passed, 3 failed; final -g History page two|compact summary|Capacity is exit 0 (3 passed); tickets.spec.ts: 17 passed, 1 failed; tickets.spec.ts -g late old-account after explicit read-wait correction exit 0 (1 passed). All86 unique tests now green; --list confirms86 in4files. This is aggregate coverage, not one fresh all-green run.
- 2026-11-14 validate: final: npm --prefix 04_Software/web run build exit 0; npm --prefix 04_Software/web run build:e2e exit 0. Recomputed production stamp: 138 inputs, 7 outputs, root license copy, JS/CSS license headers and license inventory match. Existing Vite large-chunk warning accepted.
- 2026-11-14 validate: final: python 02_Tools/internal/check_release_notes.py --since 31fd0a0e392f692d8c2fa5019079e1d8347229c8 exit 0; git diff --check exit 0; python .agentic/aegis.py check --task TASK-ae44ba07 --strict exit 0 (71 warnings: 70 existing out-of-scope requirement/journal warnings plus generated minified-diff scan limit).
- 2026-11-14 validate: final: explicit user ruling substitutes targeted proof for --strict --run; no full pytest, all frontend unit/E2E suite, npm run validate or live model/forge/container acceptance ran. Parent owns integrated proof after94 and Linux symlink acceptance. Bounds respected; only authorized master checkout edited; no push/PR/merge/deploy/issue writes.
- 2026-11-14 validate: Inspection: opened the generated Agent sessions screenshot; four command tabs precede ticket title, Show ticket and right-aligned Close are present, saved status/stage/workflow follow title, budgets/usage remain, tool text is readable and reasoning starts collapsed. Production fingerprints were independently checked by both reviewers.
- 2026-11-14 validate: completed; next done

## Rulings

- RULING-001 | date=2026-11-14 | decision=Autonomous stages on master with local commit and only targeted validation | reason=User delegation explicitly authorizes autopilot, bounds this run to 120 minutes/120 files/three repair rounds, and defers integrated full suites until after #94 | source=user | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-ae44ba07.md
changed: Implemented #92; documentation, four-locale help/releases, offline tests and production assets current
evidence: Python168pass4skip; frontend44pass; browser86unique green via repairs; typecheck/Ruff/build/assets/releases/strict pass; independent reviews approved round3
issues: Full integrated --run proof deferred to parent after #94; four Windows symlink cases require Linux acceptance
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-11-14)

- stage: validate; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-fb6236ba - List completed agent attempts
  - REQ-FUNC-98358471 - Read bounded recorded session pages
  - REQ-REL-4278b8fa - Isolate malformed session records
  - REQ-SEC-3e1a4ea4 - Confine session file reads
  - REQ-UX-8c280c24 - Keep compact saved job details
  - REQ-UX-b359952f - Separate global Jobs and Tickets
  - REQ-UX-7cc76f30 - Read global tickets on entry and scope change
  - REQ-REL-5e4552df - Fence ticket read completions
  - REQ-SEC-97e45ffb - Expose bounded operational executor evidence
- deviations: 3 recorded
  - validate: Full-suite --run gate deferred to parent after #94 by explicit user instruction; targeted checks and independent review remain required.
  - build: some model, scope and review regression tests were added with or after their implementation instead of observing red first; API and navigation entry red evidence preceded implementation, and focused post-change assertions cover the remaining boundaries.
  - build: first targeted four-file browser run stopped at eight failures (65 passed, 12 unrun); scope-bound repair selections preserve each observed failure and rerun only failed/new/unrun relevant journeys rather than repeat the complete selection.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 31fd0a0: 58 file(s) changed, 1837 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=71 notes=28
- checklist: 9/9 done
