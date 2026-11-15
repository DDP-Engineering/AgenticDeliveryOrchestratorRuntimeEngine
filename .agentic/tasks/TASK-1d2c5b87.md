<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-1d2c5b87 - One Pi conversation per job

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-de494e23, REQ-SEC-397b4a89, REQ-FUNC-22de3595, REQ-FUNC-116450ef, REQ-FUNC-7caa53e1
parent:
branch: master
base: c7208e9cdb5cc976e78429035498c759d0d5813b
opened: 2026-11-15

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
- [x] final proof logged truthfully after the last edit (strict metadata + targeted checks; full --run excluded by user)
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem: STATED: Job implementation loses Pi conversation context between bounded stage processes; OBSERVED: launcher passes --no-session and native settings are temporary.
Desired outcome: STATED: One exact job-owned Pi implementation conversation across stages, continuations and corrections, using Pi persistence/compaction.
Actors: STATED: ADORE operator, Pi executor, existing independent AEGIS reviewers.
Primary scenario: STATED: Build restarts RPC after a checkpoint, resumes the same conversation and proceeds to Validate with prior context.
Examples: STATED: A fact supplied in Frame is available after process restart in Build; Validate corrections return to the main conversation.
Counterexamples: STATED: Another job, independent reviewer or connectivity probe must not select this conversation.
In scope: STATED: explicit private session binding, native/container paths, continuation prompts, per-attempt accounting, existing instruction/cancel/recovery behavior, current docs/help/notes and local commit.
Out of scope: STATED: convergence controls, new retry/review settings, custom memory/viewer, migrations, AEGIS payload/policy edits, live model calls, delivery archives, deployment and push.
Constraints: STATED: same checkout/master; include pre-existing plan/README edits, exclude four delivery deletions; no new tests/full suite; initial 90 minutes and 45 changed files; no new branch/worktree. OBSERVED: base c7208e9c; review enabled with existing max_fix_cycles=5.
Success signals: STATED: exact conversation continuity and job isolation; clear missing/corrupt-state refusal; no historical usage/evidence duplication; current bounded lifecycle and token renewal; current documentation and offline focused proof.
Evidence: OBSERVED: implementation plan 00_Planning/2026-11-15_Pi_Job_Conversation_Implementation_Plan.md; launcher.py --no-session; local_execution.py pi_session; pi_rpc.py cumulative session statistics; Pi v1.5.2 session/RPC documentation.
Assumptions: INFERRED: retaining context reduces repeated orientation; no guaranteed completion speed.
Unknowns: Exact persistent-path and launch-statistics seams are resolved by source inspection during design; no product decision pending.
Decision-blocking questions: None; user authorized implementation and commit with autopilot.
Proposed behaviors: None outside accepted plan.
Path and reason:

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | durable job conversation |
| no new interface or data format | no | explicit Pi session binding |
| no new dependency | yes | pinned Pi persistence |
| an existing requirement already covers the behavior | no | ephemeral requirements require deliberate revision |
| no security or data-handling change | no | private durable conversation |

Full path. No child tasks; independent reviews follow existing AEGIS policy.

## Requirement coverage

| Behavior | Requirement | Design | Proof seam |
|---|---|---|---|
| Exact job conversation across processes/backends | REQ-FUNC-de494e23 | explicit session binding | existing launcher/native tests |
| Refuse unsafe/missing/corrupt binding | REQ-SEC-397b4a89 | private paths, strict file validation and RPC identity | existing unsafe-evidence parametrization |
| Incremental continuation and unchanged stage/review policy | REQ-FUNC-22de3595 | initial versus continuation prompt | existing prompt/conductor tests |
| Bounded RPC lifecycle | REQ-FUNC-116450ef | existing process and cancellation | existing RPC tests |
| Current-attempt usage only | REQ-FUNC-7caa53e1 | pre-prompt statistics baseline | existing usage replay |


## Design

### Approach

REQ-FUNC-de494e23: retain bounded processes and stage checkpoints; select an exact Pi --session file in private job IO, outside Git. Pi owns transcript writing and compaction. Connectivity probes remain ephemeral. Native temporary settings remain separate.
REQ-SEC-397b4a89: a small binding receipt pins host IO, backend cwd and Pi session id. Validate regular-file ancestry, current Pi header/JSONL and RPC identity before prompting. A required missing conversation refuses explicitly; no old history import.
REQ-FUNC-22de3595: first prompt contains ticket/context; continuation supplies current task/stage, existing procedure and only new recovery/thread/inbox material. Partial continuation points at the journal without replaying Log text.

### Interfaces and data

Use PiConversation in executor/conversation.py, prepared before launch counters and inside the existing verified target boundary. Launcher recognizes existing job stage-attempt archive stems; probes without them keep --no-session. The common executor interface adds only optional context_key (the current ticket fingerprint); no session-mode setting or new backend.
Receipt schema 1 lives beside session.jsonl under io/pi-conversation; exact host root and backend cwd pin identity. Pi session id is bound from get_state before prompt; accepted prompt marks history required. Crash before acknowledgement can resume an existing validated file. Unsafe or changed data raises IsolationError with delete-job guidance.
REQ-FUNC-7caa53e1: request cumulative statistics before prompt and subtract them only for cross-checking current streamed assistant usage. Never replay get_messages into attempt archives. Missing stats cannot make historical usage count as current.
REQ-FUNC-116450ef: retain abort/settled/shutdown, stage/attempt evidence, instruction acknowledgements and per-attempt ChatGPT tokens. Review contexts remain separate under installed AEGIS policy.

### Files and test seams

executor/conversation.py, launcher.py, pi_rpc.py, orchestrator.py, executor/base.py documentation, prompt catalog and affected Markdown. Native argv appends exact session flags through launcher without changing native process scopes or temporary settings.
Adapt existing test_pi_rpc.py, fake_pi_rpc.py, test_local_execution.py, test_prompts.py and affected orchestrator assertions. No new test functions. Update current user/component docs, four help locales, release notes, CHANGELOG and requested planning status.

### Risks and open decisions

Host/container cwd differs; validate the backend path rather than host spelling. WSL uses the existing IO mount. Raw Pi histories are private and may contain sensitive job data, unlike redacted operational tails. Missing/corrupt required history refuses; no automatic recreation. No unresolved product decisions.
User prohibits full proof and live model calls: focused offline fake processes and existing help/release checks only. Initial 45-file estimate may require reassessment for AEGIS records and localization.

### Requirement map

All five requirements map to the decisions and existing proof seams above; no new workflow/review limits or settings.
Diagrams: [diagram_TASK-1d2c5b87.md](diagram_TASK-1d2c5b87.md)


## Log

- 2026-11-15 frame: journal opened
- 2026-11-15 frame: DEVIATION build: no new tests or full suite; user requires adaptation of existing tests and focused offline checks only.
- 2026-11-15 frame: completed; next specify - Autopilot; accepted implementation plan and explicit user constraints (7 Done checklist item(s) left unticked)
- 2026-11-15 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-15 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-15 build: red: focused existing test_pi_executor_launches_an_isolated_rpc_process exit 1; explicit --session absent (REQ-FUNC-de494e23)
- 2026-11-15 build: green: existing launcher/native targeted cases exit 0; 11 restart/corruption/native Windows/Linux cases; earlier executor/local modules 143 passed (REQ-FUNC-de494e23, REQ-SEC-397b4a89, REQ-FUNC-7caa53e1).
- 2026-11-15 build: release-notes: added (job conversation continuity in all four locales)
- 2026-11-15 build: help: updated (job stage continuity and recorded attempts in en/fr/de/ro)
- 2026-11-15 build: Inspection: managed Pi 1.5.2 is absent locally; no install or live model request attempted. Protocol/path behavior checked against pinned Pi sources and offline fakes.
- 2026-11-15 build: Baseline: test_direct_attempt_rereads_only_budgets_without_resetting_work[lower] fails unchanged HEAD orchestrator as well; its fixture replaces outdated TOML spacing. Excluded from focused final proof, no unrelated fix.
- 2026-11-15 build: Budget reassessment: up to 52 changed files (about 48 expected), including required records/docs/four locales; 90-minute time limit unchanged.
- 2026-11-15 build: DEVIATION build: closely related persistence, prompt and accounting changes share the initial missing-session red; remaining existing assertions were adapted during integration, not separate test-first increments.
- 2026-11-15 build: green: focused launcher/path/native/partial-stage cases exit 0 (20 cases); prompt and ChatGPT-token modules green in broader run. Broader orchestrator fixture failures are isolated from final targeted proof.
- 2026-11-15 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-15 validate: Independent review round 1: spec approved; quality requests actual-ticket launch fingerprint and validation of context-bearing compaction records. Generic binding error guidance will be normalized in the same boundary fix.
- 2026-11-15 validate: returned to build - Round 1 quality findings: current-ticket context fingerprint and corrupt compaction refusal; continue corrections under user-authorized autopilot
- 2026-11-15 build: red: existing partial-stage changed_ticket=True case exit 1; newly fetched ticket context omitted when persisted hash was stale (REQ-FUNC-22de3595).
- 2026-11-15 build: red: existing launcher parametrization bad-compaction exit 1; malformed context-bearing entry was accepted (REQ-SEC-397b4a89).
- 2026-11-15 build: green: corrected current-ticket fingerprint and malformed/valid/self-ID compaction cases; existing launcher/partial-stage parametrizations 22 passed.
- 2026-11-15 build: Focused integration: executor/local/prompts/ChatGPT modules 302 passed; no live services or model. Final proof will rerun after round-2 approvals.
- 2026-11-15 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-15 validate: Round-2 independent spec and quality reviewers approved both corrections. Last knowledge-only correction removes an inaccurate fixed fragment count; reviewers notified before final proof.
- 2026-11-15 validate: DEVIATION validate: canonical check --strict --run includes the prohibited full suite/frontend pipeline; final proof uses strict metadata check plus focused offline modules, selected orchestrator contracts, Ruff, help and release-note checks. Broad baseline fixture failures and absent managed Pi prevent treating the full module run as clean.
- 2026-11-15 validate: Inspection: current diff stays within one job conversation, existing shared backend/ownership and lifecycle; no AEGIS payload/policy, new test functions, models, archive generation/deployment, branches or worktrees. Initial delivery deletions remain excluded.
- 2026-11-15 validate: Both round-2 reviewers reconfirmed the exact final candidate after the last knowledge-only wording correction; candidate frozen before final proof.
- 2026-11-15 validate: Final runtime proof: 308 executor/native/prompt/token cases plus 115 selected orchestrator cases passed; 13 help cases, Ruff, release notes and diff check passed. The only subsequent candidate edit refreshes requirement dates and maps the already checked help/release-note assets, with no source/test/doc changes. Review reconfirmation and strict metadata proof follow.
- 2026-11-15 validate: final: targeted Python proof exit 0 (308 executor/native/prompts/ChatGPT cases and 115 selected orchestrator contracts); node --test web/tests/help.test.mjs exit 0 (13); changed-source/test Ruff exit 0; check_release_notes.py --since c7208e9c exit 0; git diff --check exit 0; final aegis check --task TASK-1d2c5b87 --strict --json exit 0 after metadata-only edits. Strict result: errors=0, warnings=79, notes=28; remaining warnings belong to older requirements/journals and unrelated retained delivery deletions. No full-suite/frontend pipeline, live model/container, archives or deployment. Both independent exact-candidate round-2 approvals retained.
- 2026-11-15 validate: completed; next done

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-1d2c5b87.md
changed: 48 files: exact private Pi job conversation, incremental prompts/accounting, current docs/help/notes and requested planning; four pre-existing delivery deletions excluded
evidence: 423 targeted Python cases + 13 help cases passed; Ruff/release notes/diff check and strict AEGIS metadata exit 0; two independent round-2 approvals
issues: Full suite/frontend pipeline, real model/container acceptance and delivery verification intentionally not run; pre-existing broad-fixture failures documented and excluded
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-15)

- stage: validate; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-de494e23 - Resume one exact Pi implementation conversation per job
  - REQ-SEC-397b4a89 - Refuse unsafe or missing job conversation evidence
  - REQ-FUNC-22de3595 - Send incremental prompts to a continuing Pi job
  - REQ-FUNC-116450ef - Run a container Pi stage through one RPC process
  - REQ-FUNC-7caa53e1 - Sum Pi usage over the turns of a launch
- deviations: 3 recorded
  - build: no new tests or full suite; user requires adaptation of existing tests and focused offline checks only.
  - build: closely related persistence, prompt and accounting changes share the initial missing-session red; remaining existing assertions were adapted during integration, not separate test-first increments.
  - validate: canonical check --strict --run includes the prohibited full suite/frontend pipeline; final proof uses strict metadata check plus focused offline modules, selected orchestrator contracts, Ruff, help and release-note checks. Broad baseline fixture failures and absent managed Pi prevent treating the full module run as clean.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base c7208e9: 52 file(s) changed, 1276 line(s) added
- checks: errors=0 warnings=79 notes=28
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
