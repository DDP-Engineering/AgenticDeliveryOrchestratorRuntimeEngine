<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-4d1d734a - LA-03 #94 Send instructions to the running agent

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-6bfce004, REQ-SEC-a076c292, REQ-DATA-1d84dc79, REQ-FUNC-d25eb15e, REQ-DATA-2777f139, REQ-REL-6dd5a689, REQ-FUNC-84b2d01e, REQ-REL-c6354595, REQ-FUNC-5942c3b1, REQ-DATA-2df9e8ef, REQ-REL-73d642d7, REQ-UX-bf7c7916
parent:
branch: master
base: 4dde8feb8b219b1c9f08307c59014753a9665b7f
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

Problem: STATED (#94): operators cannot send an extra instruction from Agent sessions.
Desired outcome: STATED: authorized working-job instructions are durably queued, acknowledged by existing Pi RPC, recorded and copied once to the ticket.
Actors: STATED: users allowed to stop the job, web API, per-run conductor and Pi.
Primary scenario: STATED: Send now queues steer after tools; Send when finished queues follow_up. Between sessions the next prompt includes pending text after the human thread.
Examples: STATED: an operator asks for a smaller change while Pi is working; Pi success marks Delivered.
Counterexamples: STATED: success:false, session end and restart leave unacknowledged text Queued; malformed files are reported and never sent.
In scope: STATED: #94 API/inbox/RPC/conductor/composer, four locales, help/release notes, component documentation, requirements/knowledge/context, production assets and targeted offline proof.
Out of scope: STATED (delegation): navigation redesign, other tickets, full suites, real agents/providers/forges/containers, migrations, branch/worktree creation, push, PR, merge, labels, closure and deployment.
Constraints: STATED: same master checkout; clean base 4dde8feb8b219b1c9f08307c59014753a9665b7f; autopilot; 120 minutes, 100 tracked files, three repair rounds per failing targeted check. Local commit authorized. Preserve #92/#93 compact header, scoping, polling, archive and literal-session contracts. No second Pi stdin writer or agent loop. Existing cancel behavior stays authoritative.
Success signals: STATED: fake now/after commands carry literal wrapped data; only positive acknowledgements mark Delivered; prompt fallback survives failures/restart; one journal event and durable ticket comment per delivery; API permission/input/lifecycle failures; fenced queued/delivered composer below live/empty sessions; required docs/copy/assets.
Evidence: OBSERVED: clean git status, master and exact HEAD verified before edits. GET /api/v1/repos/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/{91,94} read current open descriptions. Existing _Launch owns one stdin queue, run_pi_rpc polls cancel; _required_comment/_retry_outbox provide durable forge replay; PromptCatalog is shipped loader; instruction resource is not yet present.
Assumptions: INFERRED: bounded inbox implementation limits may be chosen within explicit bounded-run requirement; no new setting needed.
Unknowns: UNKNOWN: real Pi/provider/forge acceptance and Linux symlink proof; explicitly parent/operator-owned.
Decision-blocking questions: none established; pinned protocol verification occurs before delivery implementation.
Proposed behaviors: none beyond accepted issue contracts.
Path and reason:
| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | STATED: new instruction delivery |
| no new interface or data format | no | STATED: POST and durable inbox |
| no new dependency | yes | INFERRED: existing Python/React seams suffice |
| existing requirement already covers behavior | no | OBSERVED: no instruction implementation |
| no security or data-handling change | no | STATED: new authenticated literal-text write |
Full path; scope accepted through explicit user delegation with autopilot.

## Requirement coverage

| Behavior | Requirement | Design | Verification |
|---|---|---|---|
| Queue working job instructions | REQ-FUNC-6bfce004 | protocol spec and Design | linked component and LA-03 checks |
| Refuse unauthorized job instructions | REQ-SEC-a076c292 | protocol spec and Design | linked component and LA-03 checks |
| Refuse invalid instruction requests | REQ-DATA-1d84dc79 | protocol spec and Design | linked component and LA-03 checks |
| Refuse instructions outside working jobs | REQ-FUNC-d25eb15e | protocol spec and Design | linked component and LA-03 checks |
| Retain bounded atomic instruction records | REQ-DATA-2777f139 | protocol spec and Design | linked component and LA-03 checks |
| Skip corrupt queued instruction files | REQ-REL-6dd5a689 | protocol spec and Design | linked component and LA-03 checks |
| Deliver queued instructions through acknowledged Pi commands | REQ-FUNC-84b2d01e | protocol spec and Design | linked component and LA-03 checks |
| Keep unacknowledged instructions queued | REQ-REL-c6354595 | protocol spec and Design | linked component and LA-03 checks |
| Carry pending instructions into the next session prompt | REQ-FUNC-5942c3b1 | protocol spec and Design | linked component and LA-03 checks |
| Journal acknowledged instruction delivery once | REQ-DATA-2df9e8ef | protocol spec and Design | linked component and LA-03 checks |
| Replay instruction ticket comments independently | REQ-REL-73d642d7 | protocol spec and Design | linked component and LA-03 checks |
| Compose instructions below the agent session | REQ-UX-bf7c7916 | protocol spec and Design | linked component and LA-03 checks |


## Design

### Approach

STATED: implement only the accepted #94 flow. OBSERVED: run_pi_rpc owns one writer
queue; add polling and matching acknowledgement handling there, never another loop.
A small instructions.py owns bounded atomic inbox validation and delivery receipts.
An executor-neutral optional InstructionDelivery handoff snapshots pending records,
renders wrappers through PromptCatalog and receives real Pi acknowledgements.
The conductor inserts that snapshot after the human thread in both prompt paths.
It reconciles receipts to deterministic outbox records and journal events; forge
I/O stays after the Pi loop, using existing marker replay and backoff.

### Interfaces and data

REQ-FUNC-6bfce004 / REQ-SEC-a076c292 / REQ-DATA-1d84dc79 / REQ-FUNC-d25eb15e:
POST and GET share authorized job identities; principal/CSRF/project grants and
saved lifecycle guard the write. Responses carry exact project/run identities.
REQ-DATA-2777f139 / REQ-REL-6dd5a689: current-schema UUID records, 256 per run,
32 KiB each, exclusive temporary+fsync+replace, separate short kernel inbox lock;
malformed/linked input is preserved, skipped and reported with value-free notices.
REQ-FUNC-84b2d01e / REQ-REL-c6354595: now->steer, after->follow_up, once per session;
matching command/id success only marks delivery. Cancel/timeout takes precedence.
REQ-FUNC-5942c3b1: prompt composition never acknowledges; prompt started success does.
Failed spawn, rejection or early session end retains pending data across restart.
REQ-DATA-2df9e8ef / REQ-REL-73d642d7: durable receipt precedes outbox save, which precedes
one instruction-delivered event. Stable notification identity recovers partial host
work and suppresses duplicate ticket comments. Forge outage never fails Pi delivery.
REQ-UX-bf7c7916: separate keyed composer follows SessionView in the existing sessions
slot; visible for empty working sessions, read-only terminal history, literal text,
localized status meaning and tool-wait note; request generations/identities fence reads.

### Files and test seams

New instructions.py, instruction prompt, composer/model/copy and focused tests;
base/launcher/RPC optional handoff; conductor prompt/receipt/outbox integration;
app route; existing jobs browser test, help/copy/release notes and production bundle.
Trust boundaries use fake Pi subprocess replay, fake forge and isolated profile roots.

### Risks and open decisions

No product decision is open. OBSERVED: Pi success means accepted, not executed; UI
states that meaning. A remote ack/local persistence crash cannot be transactional;
queued recovery retains text and may retry rather than invent delivery. No old store
readers, migrations or transcript rewrite. Explicit parent-owned integrated and Linux
acceptance remains deferred. Independent review required before final targeted proof.

### Requirement map

All 12 coverage rows map to the decisions above and named source/test seams.
Diagrams: [diagram_TASK-4d1d734a.md](diagram_TASK-4d1d734a.md)


## Log

- 2026-11-14 frame: journal opened
- 2026-11-14 frame: completed; next specify
- 2026-11-14 specify: completed; next design
- 2026-11-14 design: completed; next build
- 2026-11-14 build: red: uv run --project 04_Software --frozen --extra web python -m pytest -q 04_Software/tests/test_instructions.py -x exit 1 - durable instruction inbox missing (REQ-DATA-2777f139, REQ-DATA-1d84dc79, REQ-REL-6dd5a689, REQ-REL-c6354595)
- 2026-11-14 build: green: targeted test_instructions.py exit 0 - 14 passed (inbox, corruption, capacity, ack snapshot contracts)
- 2026-11-14 build: red: targeted test_web_jobs.py -k instruction -x exit 1 - POST missing (405), authorized literal enqueue expected (REQ-FUNC-6bfce004, REQ-SEC-a076c292, REQ-DATA-1d84dc79, REQ-FUNC-d25eb15e)
- 2026-11-14 build: green: targeted test_web_jobs.py -k instruction exit 0 - 12 passed, 150 deselected
- 2026-11-14 build: red: targeted test_pi_rpc.py -k instruction_rpc/fallback_receipt exit 1 - existing RPC loop has no instruction polling/ack handoff (REQ-FUNC-84b2d01e, REQ-REL-c6354595, REQ-FUNC-5942c3b1)
- 2026-11-14 build: green: targeted instructions and RPC instruction/fallback tests exit 0 - 24 passed, 51 deselected; negative author-surrogate and duplicate-key proofs added after parent review
- 2026-11-14 build: red: test_orchestrator.py -k instruction -x exit 1 - conductor instruction handoff missing (REQ-FUNC-5942c3b1, REQ-DATA-2df9e8ef, REQ-REL-73d642d7)
- 2026-11-14 build: green: test_orchestrator.py -k instruction exit 0 - 4 passed, 316 deselected; direct fallback, stable journal/comment, outage and response-lost replay
- 2026-11-14 build: red: node --test web/tests/instructions.test.mjs exit 1 - instruction transport missing (REQ-UX-bf7c7916)
- 2026-11-14 build: green: targeted Python instruction/session selection exit 0 - 71 passed, 4 Windows link skips, 632 deselected; inbox final profile path case 22 passed separately. LA-03 browser repair completed: 6 passed; retained LA-01/02 11 passed in initial combined selection. Node instruction/session/help 19 passed; release notes checker passed.
- 2026-11-14 build: release-notes: added
- 2026-11-14 build: help: updated
- 2026-11-14 build: Broad component regression selection: 220 passed, 4 skipped, 2 failed in test_prompts inventory/placeholder oracles due to the new live wrapper. Preserved captured baseline fixtures; extended explicit allowed inventory and live placeholder/body oracle instead of regenerating historical captures.
- 2026-11-14 build: green: targeted test_prompts.py exit 0 - 88 passed after live resource inventory extension; no captured baseline fixtures changed. Changed-file Ruff passes. Production npm run build exits 0; existing Vite chunk-size warning retained. Evolution reviewed: implementation, tests, docs and assets remain #94 only.
- 2026-11-14 build: completed; next validate
- 2026-11-14 validate: DEVIATION validate: strict --run and full-suite execution are intentionally deferred - explicit child delegation reserves integrated proof for the parent; only targeted component/HTTP/model/help/browser checks run here. Linux symlink and real Pi/provider/forge/runtime acceptance also remain operator-owned.
- 2026-11-14 validate: Independent review1: spec approved; quality P2 InstructionComposer working-to-terminal in-flight GET can leave pre-ack Queued visible after polling stops. Add trailing refresh and delayed-read/terminal browser proof; no other blocking findings.
- 2026-11-14 validate: returned to build - Review1 P2: retain a trailing instruction refresh across working-to-terminal in-flight read
- 2026-11-14 build: red: LA-03 terminal transition browser regression exit 1 - delayed pre-ack GET leaves Queued with no terminal refresh, reproducing independent review1 P2
- 2026-11-14 build: green: LA-03 browser repair proof exit 0 - 7 passed including delayed pre-ack GET through terminal transition; source queues one trailing fresh read and then stops polling. Typecheck/E2E build and production rebuild pass. Component/knowledge documentation updated for this lifecycle boundary.
- 2026-11-14 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-14 validate: CORRECTION: the preceding repair green line/advance evidence was emitted before inspecting the completed browser result and is incorrect. Actual combined LA-03 repair selection exit 1: 6 passed including terminal-transition regression, 1 Romanian locale navigation timeout. Investigating that fixture timing; no final all-green proof is claimed.
- 2026-11-14 validate: Romanian fixture inspection: locale selection navigated before its preferences PATCH completed. The fixture now awaits successful persistence both when selecting its locale and when restoring English; the product language behavior is unchanged. Two accidental no-edit browser launches were interrupted after a corrected working-directory tool error; they are not green proof.
- 2026-11-14 validate: Corrected focused repair proof: playwright jobs.spec.ts --grep LA-03-localized/terminal exit 0 - 4 passed, including all three non-English locales and the terminal in-flight-read regression. Earlier 6/7 failure remains explicitly recorded; final complete targeted proof will follow review2. Production/E2E assets include the trailing-refresh repair.
- 2026-11-14 validate: Independent review2: spec approved and quality approved for the repaired current candidate; no further blocking findings. Final targeted proof begins now with no subsequent product/test/doc edits planned.
- 2026-11-14 validate: final: cwd=04_Software; uv run --frozen --extra web python -m pytest -q tests/test_instructions.py tests/test_pi_rpc.py tests/test_executor.py tests/test_prompts.py tests/test_web_executor_session.py; exit 0; 226 passed, 4 skipped (Windows symlink privilege), existing Starlette deprecation warning.
- 2026-11-14 validate: final: cwd=04_Software; uv run --frozen --extra web python -m pytest -q tests/test_orchestrator.py tests/test_web_jobs.py -k instruction; exit 0; 16 passed, 466 deselected, existing Starlette deprecation warning.
- 2026-11-14 validate: final: cwd=04_Software/web; node --test tests/instructions.test.mjs tests/sessions.test.mjs tests/help.test.mjs; exit 0; 19 passed.
- 2026-11-14 validate: final: cwd=04_Software/web; npm run build:e2e; exit 0; UI/E2E TypeScript and stamped isolated build pass; existing Vite chunk-size warning.
- 2026-11-14 validate: final: cwd=repository root; uv run --project 04_Software --frozen ruff check 04_Software/adore/instructions.py 04_Software/adore/executor/base.py 04_Software/adore/executor/launcher.py 04_Software/adore/executor/pi_rpc.py 04_Software/adore/orchestrator.py 04_Software/adore/prompts.py 04_Software/adore/web/app.py 04_Software/tests/test_instructions.py 04_Software/tests/test_pi_rpc.py 04_Software/tests/test_orchestrator.py 04_Software/tests/test_web_jobs.py 04_Software/tests/test_prompts.py --output-format concise; exit 0.
- 2026-11-14 validate: final: cwd=repository root; python 02_Tools/internal/check_release_notes.py --since 4dde8feb8b219b1c9f08307c59014753a9665b7f; exit 0; four-locale release notes contract passed. git diff --check exit 0.
- 2026-11-14 validate: final: cwd=repository root; python 02_Tools/internal/check_release_consistency.py; exit 0; release identity, source/output fingerprint and independent fresh web build comparison passed.
- 2026-11-14 validate: Remaining advisory warnings inspected: 70 unchanged legacy requirement/path/journal warnings; five new secret-pattern hits are explicit password=SYNTHETIC trust-boundary fixtures, and the sixth is the generated minified JS line omitted by scanner size limits. No actual credentials were used. Independent fresh-build byte comparison passed. Existing Starlette deprecation and Vite chunk-size warnings remain outside this scoped feature.
- 2026-11-14 validate: final: cwd=04_Software/web; ./node_modules/.bin/playwright test e2e/jobs.spec.ts --grep LA-01/LA-02/LA-03 --global-timeout 600000 (regex alternation LA-01|LA-02|LA-03); exit 0; all 18 selected Chromium journeys passed, including terminal trailing refresh and awaited locale persistence.
- 2026-11-14 validate: final: python .agentic/aegis.py check --task TASK-4d1d734a --strict --json; exit 0; errors=0, warnings=77, notes=28; strict passed. --run deliberately not invoked per parent-owned integrated validation. All warnings inspected and justified above.
- 2026-11-14 validate: Final strict snapshot after report/checklist completion: exit 0, errors=0 warnings=76 notes=28, strict passed; the preceding77 included only the then-open report checklist item. No product/test/doc edits occurred after review2 or final proof. Full integrated/--run and Linux/live acceptance remain explicitly deferred.
- 2026-11-14 validate: Final limits/inspection: 61 changed paths before staging, within100. No branch/worktree, full pytest/frontend suite, npm run validate, AEGIS --run, paid provider/Pi/container run, actual instruction/forge comment, remote Git mutation, deployment or another ticket. Initial master/base retained until the authorized local commit. One independent-review repair ended with both approvals in review2. Exact targeted commands/outcomes and corrected earlier failed claims are retained above.
- 2026-11-14 validate: completed; next done
- 2026-11-14 done: Correction to warning-count explanation: the actual final strict result is 77 warnings, not76. The additional hit is this journal's quoted synthetic fixture explanation; it is not an open checklist warning. All77 are advisory: 70 unchanged legacy warnings, five deliberate synthetic fixture hits, one identical synthetic-proof hit in this journal, and one minified-bundle scan limit. Strict exits0 with errors0 and notes28.

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-4d1d734a.md
changed: Implemented #94 with four-locale UI/help/notes, durable acknowledged delivery and production assets
evidence: 242 targeted Python passed, 4 Windows link skips; 19 Node and 18 browser passed; changed-file Ruff, typecheck/build/assets/release checks and strict passed; review2 approved
issues: Full integrated suite/AEGIS --run and Linux/live acceptance remain parent-owned; no push or deployment performed
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-14)

- stage: validate; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-6bfce004 - Queue working job instructions
  - REQ-SEC-a076c292 - Refuse unauthorized job instructions
  - REQ-DATA-1d84dc79 - Refuse invalid instruction requests
  - REQ-FUNC-d25eb15e - Refuse instructions outside working jobs
  - REQ-DATA-2777f139 - Retain bounded atomic instruction records
  - REQ-REL-6dd5a689 - Skip corrupt queued instruction files
  - REQ-FUNC-84b2d01e - Deliver queued instructions through acknowledged Pi commands
  - REQ-REL-c6354595 - Keep unacknowledged instructions queued
  - REQ-FUNC-5942c3b1 - Carry pending instructions into the next session prompt
  - REQ-DATA-2df9e8ef - Journal acknowledged instruction delivery once
  - REQ-REL-73d642d7 - Replay instruction ticket comments independently
  - REQ-UX-bf7c7916 - Compose instructions below the agent session
- deviations: 1 recorded
  - validate: strict --run and full-suite execution are intentionally deferred - explicit child delegation reserves integrated proof for the parent; only targeted component/HTTP/model/help/browser checks run here. Linux symlink and real Pi/provider/forge/runtime acceptance also remain operator-owned.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 4dde8fe: 61 file(s) changed, 2426 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=77 notes=28
- checklist: 8/9 done; open: `report` appended

## Delivery report (2026-11-14)

- stage: validate; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-6bfce004 - Queue working job instructions
  - REQ-SEC-a076c292 - Refuse unauthorized job instructions
  - REQ-DATA-1d84dc79 - Refuse invalid instruction requests
  - REQ-FUNC-d25eb15e - Refuse instructions outside working jobs
  - REQ-DATA-2777f139 - Retain bounded atomic instruction records
  - REQ-REL-6dd5a689 - Skip corrupt queued instruction files
  - REQ-FUNC-84b2d01e - Deliver queued instructions through acknowledged Pi commands
  - REQ-REL-c6354595 - Keep unacknowledged instructions queued
  - REQ-FUNC-5942c3b1 - Carry pending instructions into the next session prompt
  - REQ-DATA-2df9e8ef - Journal acknowledged instruction delivery once
  - REQ-REL-73d642d7 - Replay instruction ticket comments independently
  - REQ-UX-bf7c7916 - Compose instructions below the agent session
- deviations: 1 recorded
  - validate: strict --run and full-suite execution are intentionally deferred - explicit child delegation reserves integrated proof for the parent; only targeted component/HTTP/model/help/browser checks run here. Linux symlink and real Pi/provider/forge/runtime acceptance also remain operator-owned.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 4dde8fe: 61 file(s) changed, 2451 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=77 notes=28
- checklist: 9/9 done

## Delivery report (2026-11-14)

- stage: done; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-6bfce004 - Queue working job instructions
  - REQ-SEC-a076c292 - Refuse unauthorized job instructions
  - REQ-DATA-1d84dc79 - Refuse invalid instruction requests
  - REQ-FUNC-d25eb15e - Refuse instructions outside working jobs
  - REQ-DATA-2777f139 - Retain bounded atomic instruction records
  - REQ-REL-6dd5a689 - Skip corrupt queued instruction files
  - REQ-FUNC-84b2d01e - Deliver queued instructions through acknowledged Pi commands
  - REQ-REL-c6354595 - Keep unacknowledged instructions queued
  - REQ-FUNC-5942c3b1 - Carry pending instructions into the next session prompt
  - REQ-DATA-2df9e8ef - Journal acknowledged instruction delivery once
  - REQ-REL-73d642d7 - Replay instruction ticket comments independently
  - REQ-UX-bf7c7916 - Compose instructions below the agent session
- deviations: 1 recorded
  - validate: strict --run and full-suite execution are intentionally deferred - explicit child delegation reserves integrated proof for the parent; only targeted component/HTTP/model/help/browser checks run here. Linux symlink and real Pi/provider/forge/runtime acceptance also remain operator-owned.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 4dde8fe: 61 file(s) changed, 2476 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=77 notes=28
- checklist: 9/9 done
