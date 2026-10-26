<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-6e8cc2e7 - Adapt ADORE to AEGIS 0.15.0

stage: done
type: change
path: full
interaction: checkpoint
requirements: REQ-FUNC-9246f8cc, REQ-FUNC-faab24b2, REQ-FUNC-67469d47, REQ-FUNC-67bd56c8, REQ-FUNC-ff7dad34, REQ-FUNC-ab65704b, REQ-FUNC-8472a560, REQ-FUNC-69bfe896, REQ-FUNC-16237c6d, REQ-FUNC-fbc3fca5, REQ-REL-94e653aa, REQ-DATA-eebc4f88, REQ-FUNC-d67a1d33, REQ-UX-66547cbf, REQ-FUNC-f9bdb5d2, REQ-REL-2e67fc6d, REQ-FUNC-d8d1b95b, REQ-FUNC-40057219
parent:
branch: task/adore-web-interface
base: 9bb9661fd1a1d285bf8d5c044e0e8fcc0b41c906
opened: 2026-10-25

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

Problem:
- ADORE conducts the AEGIS flow that ended in a deliver stage. It waits for the
  executor to advance validate -> deliver, runs its strict check there, and
  after approval launches two executor sessions at deliver (bookkeeping, then
  deliver -> done with the MR/PR link). OBSERVED: `04_Software/adore/aegis.py`
  62-75 and 248-265; `adore/orchestrator.py` 908-978, 1066-1072, 1412-1427,
  1512-1535, 1692-1845.
- AEGIS 0.15.0 has no deliver stage: validate ends with `check --strict --run`,
  `report` and `advance` to done, and commit/push/PR belong to the developer.
  OBSERVED: `.agentic/steps/5_validate.md` steps 9-11 and Finish;
  `.agentic/aegis.py` 1599-1601 (PATH_STAGES).
- On a 0.15.0 target, an executor's validate session advances to done. ADORE's
  `allowed_transition("validate", "done")` is false (done sits two places after
  validate in FULL_STAGES) and `evidenced_transition` needs a deliver Log line,
  so the run fails with FORBIDDEN_STAGE_TRANSITION. INFERRED from
  `adore/aegis.py` 248-318 and `adore/orchestrator.py` 1066-1121.
- A journal still at deliver now reports `step_file: 5_validate.md`; ADORE
  expects `6_deliver.md` and raises AegisTaskError. OBSERVED:
  `.agentic/aegis.py` 2491-2495 against `adore/aegis.py` 73 and 652-657.
- Executor prompts tell sessions to write the Log, Handoff and Stage report;
  0.15.0 replaced Handoff and Stage report with a CLI-written `## State` block
  written by `advance` and `pause`. OBSERVED: `adore/orchestrator.py` 695,
  1044-1050, 1229-1234; `.agentic/CLI.md` "Journal state commands".
Desired outcome:
- STATED (brief): an ADORE run on AEGIS 0.15.0 goes frame -> ... -> validate ->
  done and its push and draft MR/PR close-out still works; no ADORE code,
  prompt, UI copy, test or component doc depends on deliver, `6_deliver.md`,
  Handoff or Stage report, except explicit compatibility with old journals.
- STATED (brief): Python and web suites pass; CHANGELOG, release notes and help
  follow ADORE's rules; this journal closes with validate evidence.
Actors:
- OBSERVED (`.agentic/context/project.md`): the operator running the conductor;
  reviewers who approve on the forge and merge; the executors (OpenCode, Pi,
  Codex, Qwen Code) that run AEGIS stages; web admins and developers.
Primary scenario:
- A ticket is picked, the executor frames and chooses full or quick, one fresh
  session runs each stage, and the validate session ends with the final strict
  check, `report` and `advance` to done. ADORE then runs its own strict check,
  presents the candidate, a human adds `agent-approved`, and ADORE pushes and
  opens the draft MR/PR; the run waits in human review. INFERRED from the brief
  and `5_validate.md`; the exact mapping is decision-blocking question 1.
Examples:
- Quick fix: frame -> build -> validate -> done, approval, draft PR. STATED.
- Target-branch drift after presentation voids the approval; the task returns
  to validate and is revalidated before a new approval. OBSERVED today
  (`orchestrator.py` 1640-1690); its 0.15.0 form depends on question 1.
Counterexamples:
- `[delivery]` settings, the "Delivery quality" statistics, `adore handoff` and
  the handoff-pending/handed-off lifecycles are ADORE concepts, not the AEGIS
  deliver stage or Handoff section, and stay unchanged. OBSERVED by grep.
- ADORE still never merges and executors still never commit or push. OBSERVED:
  root `AGENTS.md` Repository Rules.
In scope:
- `adore/aegis.py` stage tables, transition rules, probe floor and decoding.
- `adore/orchestrator.py` conduct loop, verification trigger, revalidation
  route, remediation, publication, retry/reset stage lists and prompts.
- Stage vocabularies in `config.py`, `state.py`, `cli.py`, `web/app.py`,
  `web/jobs.py`, `web/implementation_settings.py` and the frontend
  (`jobModel.ts`, `JobWorkspace.tsx`, `i18n.ts`, `implementationSettings.ts`,
  `settingHelp.ts`).
- Help topics in four locales, release notes, CHANGELOG, `01_Documentation/`,
  `05_SoftwareDocu/`, `.agentic/knowledge/`, `.agentic/context/`, requirements,
  and the Python and web tests.
- Added at the user's request during build and validate (RULING-005):
  `.agentic/aegis.toml` `[diagrams]` with structure, sequence and state, and its
  `[zones]` comment aligned with the AEGIS 0.15.0 default.
Out of scope:
- The AEGIS payload and the deploy commit 9bb9661. STATED.
- The dated evidence folders under `00_Planning/`. STATED.
- Assigning or cutting an ADORE version. OBSERVED: root `AGENTS.md` (only when
  the user asks).
- Live forge/container/model acceptance. OBSERVED: root `AGENTS.md` Status
  (operator-authorized).
Constraints:
- STATED: do not revert or edit the deploy; tests first for behavior changes;
  basic flow without overengineering; commit or push only on request, never
  with a Co-Authored-By trailer; stop at every stage checkpoint.
- OBSERVED (root `AGENTS.md`): license headers and Doxygen prologues, offline
  tests with negative cases at trust boundaries, fail closed on corrupt input,
  docs in the same change, four-locale release notes and help with their Log
  lines, `02_Tools/check_release_notes.py --since <base>` before validate.
- OBSERVED (`.agentic/context/project.md`): run state is schema 1 with no
  migration, so persisted runs and run journals that name deliver must still
  load; otherwise `invalid_runs()` turns a project's whole web history into
  `run_state_corrupt` (`web/app.py` 4237).
- OBSERVED: branch `task/adore-web-interface` is not the default branch.
Success signals:
- Offline conductor tests drive the full and quick paths through validate ->
  done to awaiting approval, and an approved candidate publishes a draft and a
  ready MR/PR.
- `python .agentic/aegis.py check --task TASK-6e8cc2e7 --strict --run` exits 0
  with test, lint and frontend executed.
- ADORE's decoder accepts real 0.15.0 `status --json` and `check --json`
  documents.
- `git grep` for `6_deliver`, `Stage report`, Handoff-section wording and the
  deliver stage finds only explicit compatibility code, history and changelog.
Evidence:
- OBSERVED: `python .agentic/aegis.py --version` printed `aegis 0.15.0`.
- OBSERVED: `status --all --json` keys command, hidden_done, schema=1, tasks
  (id, title, file, stage, type, branch), unreadable=[] over 122 done journals.
- OBSERVED: `status TASK-0078b3af --json` task keys checklist, components,
  done, file, header (stage, type, path, interaction, requirements, parent,
  branch, base, opened), id, log, stage, step_file (None for done), title. The
  State block is not in the JSON.
- OBSERVED: `check --json` and `check --strict --json` exit 0 with keys
  command, dry_run, findings (check, level, message, path), result, run,
  schema, strict ({enabled, promoted_warnings, passed} under --strict), summary,
  task. `--run` entries keep name, status (ok, failed, stopped, skipped), exit,
  seconds (`.agentic/aegis.py` 3555-3590).
- OBSERVED: `task` prints one path and refuses a bare task ID as title
  (`.agentic/aegis.py` 1123-1183); `report` still prints `report appended to`
  (4605); `advance --to validate` from done is a return because done ends the
  path order (1874-1883, 2049-2120).
- OBSERVED: each run executes the `.agentic/aegis.py` inside its own worktree
  (`adore/aegis.py` 453-454, 510-513), so a run keeps the AEGIS version of its
  base until ADORE merges the target at validate (`orchestrator.py` 988).
Assumptions:
- INFERRED: target projects upgrade their AEGIS payload independently of ADORE,
  as this repository just did.
Unknowns:
- UNKNOWN: whether any host has ADORE runs at stage deliver or awaiting
  approval at deliver right now.
- UNKNOWN: whether any profile sets `[workflow] stage_timeout_overrides.deliver`.
- UNKNOWN: how live executors follow the new prompts; offline tests cannot show
  it.
Decision-blocking questions:
1. Close-out mapping: answered, AEGIS closes before approval (RULING-001).
2. Runs begun before the upgrade: answered, no compatibility with the
   pre-0.15.0 flow; ADORE requires AEGIS 0.15.0 or newer (RULING-002).
3. Existing `stage_timeout_overrides.deliver`: answered, rejected like any
   unknown stage (RULING-003). ADORE's own history stays readable
   (RULING-004).
Proposed behaviors:
- Accepted by the user at the frame checkpoint (RULING-001 to RULING-004):
  - The executor's validate -> done advance triggers ADORE's independent
    strict check and the candidate-bound approval presentation.
  - After approval ADORE only pushes, opens or adopts the MR/PR and enters
    review: no executor session and no AEGIS command.
  - A done journal without current ADORE verification evidence goes back
    with `advance --to validate` before ADORE verifies again.
  - The probe refuses AEGIS older than 0.15.0 with an upgrade message.
  - Executor prompts name `advance`, `pause` and the State block instead of
    Handoff and Stage report.
  - Stage-timeout overrides and reset targets accept the current stages only;
    no conduct, reset or setting path accepts deliver. ADORE's persisted runs,
    run journals and job-history reads that name deliver stay readable and
    display as Deliver (RULING-004).
Path and reason:

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | the stage flow, prompts, publication steps and UI stage lists change |
| no new interface or data format | no | the accepted stage vocabulary and timeout keys change |
| no new dependency | yes | standard library and existing web stack only |
| an existing requirement already covers the behavior | no | REQ-FUNC-16237c6d and REQ-FUNC-ff7dad34 describe the deliver-based flow and need updating |
| no security or data-handling change | yes | no credential or data-handling change; persisted state stays schema 1 |

Full path: the change alters conducted behavior and contracts, so specify and
design apply. No child tasks: one integrated change.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Verification | Design decision or no impact |
|---|---|---|---|---|
| A run reaches done on AEGIS 0.15.0 | The executor's validate -> done advance triggers ADORE's strict check, and only a passing check leads to the approval presentation | REQ-FUNC-9246f8cc (new) | Full and quick conductor paths to awaiting approval at stage done; a failing check presents nothing | FULL/QUICK_STAGES end validate -> done; the post-launch check runs on validate -> done; `_strict_verification` expects done |
| Revalidation after a stale approval | A done task without ADORE verification evidence gets one session that returns it with `advance --to validate`; leaving it at done is a validate failure | REQ-FUNC-faab24b2 (new) | Target-drift invalidation and evidenced run-ahead route tests; REVALIDATION_ROUTE_MISSING case | Existing revalidation route moves from deliver to done; `allowed_transition` swaps deliver -> validate for done -> validate |
| Failed independent verification | A failing strict check counts a validate failure and one session returns the task from done to an earlier stage | REQ-FUNC-67469d47 (new) | Strict-failure remediation test | `_validation_failure` keeps its shape with a done-stage task view and a return-from-done context |
| Push and MR/PR close-out still work | After approval ADORE pushes and opens or adopts the MR/PR with no executor session and no AEGIS command | REQ-FUNC-67bd56c8 (new) | Draft and ready publication tests with no post-approval prompt or AEGIS call; push failure keeps approval for retry | `_publish_impl` keeps only push, MR/PR open or adopt and `_enter_review`; sessions, report, evolution, mutation guard, second push and `_recover_done_publication` go |
| Publication stays candidate-bound | Strict verification and fresh candidate-bound approval precede draft or ready creation | REQ-FUNC-ff7dad34 (prose unchanged; linked tests move off deliver) | Approval drift, retry freshness, draft and ready publication tests | No design impact beyond the trigger move; tests re-pointed to done |
| Deviations stay visible at approval | Recorded deviations are copied into the evidence and lead the approval comment after the check at done | REQ-FUNC-ab65704b (prose unchanged; linked tests move off deliver) | Deviation harvest and approval presentation tests | Deviation marker keeps AEGIS's own stage set; harvest at done |
| No compatibility with the pre-0.15.0 flow | The probe refuses AEGIS outside major 0 or older than 0.15.0, naming 0.15.0 | REQ-FUNC-8472a560 (new) | Probe accept/refuse tests | `MINIMUM_SERIES = (0, 15)`; probe message names 0.15.0 |
| Readiness agrees with the conductor | Doctor accepts only AEGIS 0.15.0 or later within major 0 with schema 1 | REQ-FUNC-69bfe896 (revised) | Doctor probe tests | Doctor reads the same constants; tests move to 0.15.0 |
| Task documents follow 0.15.0 | The decoder accepts frame to done with the 0.15.0 step files and refuses a task at deliver | REQ-FUNC-16237c6d (revised verification) | AEGIS client decode and transition tests | Decode limited to conducted stages; status lists accept AEGIS 0.15.0's own vocabulary |
| Prompts name the 0.15.0 journal writers | Stage prompts direct `advance`, `log` and `pause`; continuation context names `brief` and the State | REQ-FUNC-fbc3fca5 (new) | Prompt tests for every stage and the continuation context | `_stage_prompt` and the continuation context rewritten to advance, log, pause and brief |
| Human handoff comment names the 0.15.0 resume view | The handoff comment tells the human to run `brief` and read the journal instead of the Handoff section | REQ-REL-94e653aa (prose unchanged) | Existing handoff comment test | Handoff comment wording only |
| A stale deliver timeout is refused | A stage-timeout key outside the five stages fails configuration validation | REQ-DATA-eebc4f88 (new) | Config validation tests | `config.AEGIS_STAGES` holds the five stages |
| Settings edits the five-stage map | Reviewed web edits accept only the five-stage timeout map | REQ-FUNC-d67a1d33 (revised) | Web pending-config tests | `implementation_settings.STAGES` holds the five stages |
| Settings shows five stage rows | The Implementation editor offers five stage timeout choices | REQ-UX-66547cbf (revised) | Settings helper and browser tests | `executionStages`, editor labels and help copy list five stages |
| Reset uses the current stages | Reset refuses targets other than frame to validate and publishing, and every target for a run recorded at deliver | REQ-FUNC-f9bdb5d2 (new) | Engine and CLI reset tests | `RESETTABLE_STAGES` derives from the new FULL_STAGES plus publishing |
| ADORE history stays readable | Persisted runs and run-journal events at deliver load and display as Deliver; unknown stages still fail closed | REQ-REL-2e67fc6d (new) | State store, web job API and job view tests | `state._STAGES`, the web job reader, `jobModel.stages` and the Deliver label keep deliver for history |
| Retry after publication keeps review (review round 1) | Retry returns a published candidate to review, resumes an approved unpublished one, and conducts any other run from done | REQ-FUNC-d8d1b95b (new) | Retry after publication with drift or a removed label, failed-push retry, retry after reset --to publishing, publication of a review-round candidate, retry of a run unverified at done and of a published run reset to validate | `retry`, `_published`, `RunState.published_fingerprint` set by `_enter_review` |
| History stays history on publication (review round 1) | A run outside stage done or publishing is refused at publication | REQ-FUNC-40057219 (new) | Approved run at the removed deliver stage fails with PUBLICATION_STAGE | Guard at the top of `_publish_impl` |

## Design

**Approach**
- ADORE takes the AEGIS 0.15.0 path tables: full frame -> specify -> design ->
  build -> validate -> done, quick frame -> build -> validate -> done, with no
  step file for done (REQ-FUNC-16237c6d). The executor's validate session
  closes the task; the conduct loop treats that validate -> done advance as
  the old validate -> deliver trigger: strict check, checkpoint, fingerprint,
  approval presentation (REQ-FUNC-9246f8cc, RULING-001).
- A done journal without ADORE verification evidence gets the existing revalidation
  route, moved from deliver to done: one session runs `advance --to validate`
  (REQ-FUNC-faab24b2). The failed-check remediation keeps its shape with a
  done-stage task view (REQ-FUNC-67469d47).
- Publication becomes Git and forge only: push, open or adopt the MR/PR, enter
  review (REQ-FUNC-67bd56c8). The bookkeeping session, the `report` and
  `evolution` calls, the product-mutation guard, the close-out session, the
  second push and `_recover_done_publication` go. `_approval_ready` already
  fetches and re-checks target and fingerprint just before every
  `_publish` call, so the pre-push fetch, drift and dirty checks go too.
- Rejected: ADORE running `report` after its own check (RULING-001 excludes
  AEGIS commands after approval, and validate already runs it); a deliver
  alias for legacy journals (RULING-002).

**Interfaces and data**
- `MINIMUM_SERIES = (0, 15)`: probe and doctor refuse older releases with a
  message naming 0.15.0 (REQ-FUNC-8472a560, REQ-FUNC-69bfe896).
  `AegisClient.report()` and `.evolution()` are removed: no caller remains.
- Status lists and the deviation marker accept AEGIS 0.15.0's own stage
  vocabulary, which still reports a legacy deliver journal (KNOWN_STAGES in
  `.agentic/aegis.py`); only the pinned task decode is limited to the
  conducted stages. Technical constraint: refusing a listed deliver journal
  would fail every probe of that project (REQ-FUNC-16237c6d, REQ-FUNC-ab65704b).
- Run state: `stage` stays done from validate -> done through approval,
  publishing and review, so `_enter_review` records the published candidate in
  the additive `RunState.published_fingerprint`. `retry` returns a run whose
  candidate equals it to review, resumes publication of an approved unpublished
  candidate from done or publishing (was deliver), and conducts any other run
  from done (REQ-FUNC-d8d1b95b, review round 1). Publication refuses a run
  outside done or publishing with PUBLICATION_STAGE (REQ-FUNC-40057219, the
  publication half of RULING-004); reset refuses every target for a run recorded
  at deliver (REQ-FUNC-f9bdb5d2, review rounds 2 and 3). `RunState.approved_product` stays a readable
  schema-1 field and is no longer written. `state._STAGES` and the web job reader keep deliver
  for history (REQ-REL-2e67fc6d); `RESETTABLE_STAGES` derives frame to validate
  plus publishing (REQ-FUNC-f9bdb5d2). The runs-page stage filter is a history
  read and keeps deliver.
- `config.AEGIS_STAGES` and `web/implementation_settings.STAGES` hold the five
  stages (REQ-DATA-eebc4f88, REQ-FUNC-d67a1d33); the frontend editor and help
  copy list five (REQ-UX-66547cbf).
- Prompts say autopilot, finish with `advance`, stop with `log` and `pause`,
  and record questions with `pause --blocked`; the continuation context names
  `brief` and the journal State, and the human handoff comment names `brief`
  and the full task journal (REQ-FUNC-fbc3fca5, REQ-REL-94e653aa).

**Files and test seams**
- `adore/aegis.py` -> `tests/test_aegis.py`; `adore/doctor.py` (constants) ->
  `tests/test_doctor.py`.
- `adore/orchestrator.py` -> `tests/test_orchestrator.py`,
  `tests/test_checkpoint_handoff.py`.
- `adore/isolation.py` (drop `product_diff_fingerprint`, used only by the
  removed guard) -> `tests/test_isolation.py`.
- `adore/config.py` -> `tests/test_config.py`;
  `adore/web/implementation_settings.py` -> `tests/test_web_pending_config.py`,
  `tests/test_web_config.py`; `adore/state.py` -> `tests/test_state.py`;
  `adore/web/jobs.py` -> `tests/test_web_jobs.py`.
- Frontend `implementationSettings.ts`, `settingHelp.ts` ->
  `web/tests/settings.test.mjs`, `web/e2e/settings.spec.ts`; job fixtures
  `web/e2e/server.py`, `web/e2e/jobs.spec.ts`; help topics in four locales ->
  `web/tests/help.test.mjs`.
- Docs (`01_Documentation/`, `05_SoftwareDocu/`), CHANGELOG, release notes,
  `config.example.toml`, knowledge and context pages follow in build and
  validate.

**Risks and open decisions**
- The journal is done before a human approves; an approval invalidated later
  reopens it, which AEGIS 0.15.0 records as a return. How live executors
  follow the new prompts stays unproven offline.
- Configs with a deliver override stop validating (RULING-003); runs begun
  before 0.15.0 are not carried over (RULING-002).

**Requirement map**
- Each requirement's decision is in the coverage table's last column.

Diagrams: [diagram_TASK-6e8cc2e7.md](diagram_TASK-6e8cc2e7.md)

## Log

- 2026-10-25 frame: journal opened
- 2026-10-25 frame: deploy committed separately as 9bb9661 before the task opened, at the user's choice; the task base excludes the AEGIS 0.15.0 payload
- 2026-10-25 frame: completed; next specify - scope accepted; RULING-001 to RULING-004 answer the blocking questions
- 2026-10-25 specify: Frame proposed-behavior line narrowed to RULING-004 wording (conduct, reset and setting paths); the runs-page stage filter is a history read and keeps deliver
- 2026-10-25 specify: completed; next design - requirements accepted by the user
- 2026-10-25 design: completed; next build - design accepted by the user
- 2026-10-25 build: aegis.toml [diagrams] enabled with structure, sequence and state at the user's request (repository configuration outside this task's requirements); diagram_TASK-6e8cc2e7.md drawn from the accepted Design before build's first code edit
- 2026-10-25 build: red: pytest -q tests/test_aegis.py exit 1 (12 failed) - probe still accepts 0.5 to 0.14 and names 0.5.0, the transition table lacks validate -> done and done -> validate and still conducts deliver, the decoder expects 6_deliver.md for deliver (REQ-FUNC-8472a560, REQ-FUNC-16237c6d)
- 2026-10-25 build: green: pytest -q tests/test_aegis.py exit 0 (69 passed) (REQ-FUNC-8472a560, REQ-FUNC-16237c6d, REQ-FUNC-ab65704b marker)
- 2026-10-25 build: red: pytest -q tests/test_doctor.py exit 1 (4 failed) - doctor shares the client's MINIMUM_SERIES, so after the floor moved its 0.5 acceptance expectations failed; the doctor has no code of its own to change (REQ-FUNC-69bfe896)
- 2026-10-25 build: green: pytest -q tests/test_doctor.py exit 0 (23 passed) after the tests moved to 0.15.x acceptance and 0.14.9 and 0.5.0 refusal (REQ-FUNC-69bfe896)
- 2026-10-25 build: red: pytest -q tests/test_orchestrator.py tests/test_checkpoint_handoff.py tests/test_isolation.py tests/test_smoke.py exit 1 (31 failed) - the conductor reads a done journal as PREMATURE_DONE instead of verifying and presenting it, publication still launches two sessions and pushes twice, prompts still name autopilot-to-deliver, Handoff and Stage report, and the human handoff note names the Handoff section (REQ-FUNC-9246f8cc, REQ-FUNC-faab24b2, REQ-FUNC-67469d47, REQ-FUNC-67bd56c8, REQ-FUNC-ff7dad34, REQ-FUNC-ab65704b, REQ-FUNC-fbc3fca5, REQ-REL-94e653aa); the reset-target tests already pass because RESETTABLE_STAGES derives from the client's new FULL_STAGES (REQ-FUNC-f9bdb5d2)
- 2026-10-25 build: green: pytest -q tests/test_orchestrator.py tests/test_checkpoint_handoff.py tests/test_isolation.py tests/test_smoke.py tests/test_aegis.py tests/test_doctor.py exit 0 (346 passed, 1 skipped); ruff check adore tests exit 0 (REQ-FUNC-9246f8cc, REQ-FUNC-faab24b2, REQ-FUNC-67469d47, REQ-FUNC-67bd56c8, REQ-FUNC-ff7dad34, REQ-FUNC-ab65704b, REQ-FUNC-fbc3fca5, REQ-REL-94e653aa, REQ-FUNC-f9bdb5d2)
- 2026-10-25 build: red: pytest -q tests/test_config.py -k stage_timeout exit 1 (1 failed) - a deliver override still validates and the message lists six stages (REQ-DATA-eebc4f88)
- 2026-10-25 build: green: pytest -q tests/test_config.py tests/test_web_config.py tests/test_web_pending_config.py tests/test_wizard.py exit 0 (168 passed) after AEGIS_STAGES dropped deliver (REQ-DATA-eebc4f88); the HTTP prepare already refused a deliver map through config validation
- 2026-10-25 build: red: pytest -q tests/test_web_pending_config.py -k stored_deliver exit 1 (1 failed) - Settings still offers a stored deliver override map as editable (REQ-FUNC-d67a1d33)
- 2026-10-25 build: green: pytest -q tests/test_web_pending_config.py tests/test_web_config.py tests/test_config.py exit 0 (150 passed) (REQ-FUNC-d67a1d33)
- 2026-10-25 build: green: pytest -q tests/test_state.py tests/test_web_jobs.py exit 0 (113 passed) - history guards for a run saved at deliver and deliver journal events pass with no implementation change; state._STAGES and the web journal reader keep deliver by RULING-004, now commented as history (REQ-REL-2e67fc6d)
- 2026-10-25 build: red: node --test tests/settings.test.mjs exit 1 (2 failed) - executionStages and the four locale editor labels still hold deliver, a deliver draft serializes, and the stage-timeout help names deliver (REQ-UX-66547cbf)
- 2026-10-25 build: green: node --test tests/settings.test.mjs exit 0 (22 passed); e2e/settings.spec.ts now expects five stage comboboxes and runs with npm run validate (REQ-UX-66547cbf)
- 2026-10-25 build: release-notes: added (fixed Jobs: jobs on AEGIS 0.15.0 projects, now the minimum, reach approval again) and updated (improved Settings now names the five stage limits; the improved category already holds 10 entries)
- 2026-10-25 build: help: updated (jobs, overview and glossary in en, fr, de and ro: no Deliver stage, Validate closes the AEGIS task with its report, the job shows the stage Done while it waits for approval, is published and is in review)
- 2026-10-25 build: green: node --test tests/*.test.mjs exit 0 (98 passed, incl. the deliver-history guard and help tests); npm run build:e2e exit 0; npx playwright test e2e/settings.spec.ts e2e/jobs.spec.ts e2e/help.spec.ts exit 1 (65 passed, 1 failed: the layout check still named the removed Delivery row), then e2e/settings.spec.ts exit 0 (28 passed) after it names Validation (REQ-UX-66547cbf, REQ-REL-2e67fc6d)
- 2026-10-25 build: DEVIATION build: 26 check warnings accepted - 16 uncovered-source on the help topics, release notes, e2e fixtures and a web unit test this task changed, which are documentation, user notes and test fixtures no requirement claims as product source (as on earlier tasks); 10 pre-existing: 7 journal-header on historical journals, 2 stale-paths on REQ-FUNC-5de75419, 1 outside-layout on config.example.toml; none limits the candidate or its verification
- 2026-10-25 build: ruff check adore tests exit 0; evolution --task TASK-6e8cc2e7 reviewed: 56 modified files, all named by the design or required docs, none added or removed outside .agentic
- 2026-10-26 build: completed; next validate - build accepted by the user
- 2026-10-26 validate: requirement re-read found REQ-FUNC-8472a560 promises that a major-mismatch refusal names 0.15.0, which the 1.0.0 message did not; red: pytest -q tests/test_aegis.py -k different_major exit 1 (2 failed); fixed the message to name the 0.x line from 0.15.0; green: pytest -q tests/test_aegis.py tests/test_doctor.py exit 0
- 2026-10-26 validate: diff reviewed hunk by hunk against the Frame, RULING-001 to RULING-004 and the design; knowledge pages aegis-client, doctor, orchestrator, config, state-store and web-interface updated and migrated off Architecture; project.md reconciled; requirements re-read (REQ-REL-2e67fc6d verification narrowed to its tests, REQ-FUNC-8472a560 message fixed); no Manual or Inspection verification applies; two independent reviewers briefed for round 1
- 2026-10-26 validate: aegis.toml [zones] comment aligned with the AEGIS 0.15.0 default (build and validate are the unlisted stages; no deliver) at the user's prompting; comment-only repository configuration change
- 2026-10-26 validate: review round 1 - spec changes_required: (blocking) Component_Web_Frontend.md still says six stage choices; (minor) REQ-FUNC-faab24b2 prose wider than the empty-evidence route, faab24b2/9246f8cc verification texts claim drift and quick-path strict counts no test asserts, CHANGELOG/Design say the handoff note names the State, fr/de/ro release-note texts drop meaning, a legacy run approved at deliver still publishes, aegis.toml scope additions unrecorded, check_release_notes.py --since not logged. quality changes_required: (blocking) retry of a run that failed after publication resumes publication or reopens the task instead of returning to review; (minor) retry after reset --to publishing without approval fails as FORBIDDEN_STAGE_TRANSITION, no test drives remediation to conducting again, stale docstrings and a dead except in _publish; (pre-existing, kept) stage_failures resets on validate -> done before the strict check
- 2026-10-26 validate: returned to build - review round 1 findings: retry after publication, publishing-pointer retry, legacy deliver publication guard, remediation continuation test, stale docs, requirement wording and verification, translations
- 2026-10-26 build: red: pytest -q tests/test_orchestrator.py -k (round 1 tests) exit 1 - retry after publication reopens the task or calls AEGIS instead of returning to review, retry after reset --to publishing conducts from the publishing pointer, and a run approved at deliver is published (REQ-FUNC-d8d1b95b, REQ-FUNC-40057219); the drift-to-revalidation, remediation-continuation and quick-path strict-count tests pass without code change (REQ-FUNC-faab24b2, REQ-FUNC-67469d47, REQ-FUNC-9246f8cc); one batch run hit a transient Windows PermissionError on os.replace that three reruns did not reproduce
- 2026-10-26 build: green: pytest -q tests/test_orchestrator.py tests/test_checkpoint_handoff.py tests/test_state.py tests/test_isolation.py tests/test_smoke.py exit 0 (293 passed, 1 skipped) and tests/test_web_jobs.py tests/test_web_archive.py tests/test_web_metrics.py tests/test_web_commands.py tests/test_metrics.py tests/test_aegis.py tests/test_doctor.py exit 0 (256 passed); ruff check adore tests exit 0 - retry returns a published candidate to review via RunState.published_fingerprint, the publishing pointer conducts from done without a fresh approval, publication refuses a run outside done or publishing (REQ-FUNC-d8d1b95b, REQ-FUNC-40057219)
- 2026-10-26 build: review round 1 docs fixed (Component_Web_Frontend five stage choices, CHANGELOG and Design handoff wording, retry and publication docs, fr/de/ro release-note meaning); python 02_Tools/check_release_notes.py --since 9bb9661 exit 0 (release notes: ok)
- 2026-10-26 build: completed; next validate - review round 1 findings fixed; back to validate for review round 2 at the user's standing instruction to continue validation (6 Done checklist item(s) left unticked)
- 2026-10-26 validate: review round 2 - quality approved with minors (legacy in-review runs lack published_fingerprint, accepted under RULING-002; no test for the review-round candidate or the new field's validation and default; CLI_Reference retry-after-publishing wording; CRLF working copy of test_doctor.py). spec changes_required: (blocking) Component_Isolation.md still describes the removed report/commit-before-push delivery test, Recovery_And_Maintenance.md still counts post-validation mutation; (minor) journal coverage rows carry a doubled pipe, docs omit the publishing pointer from the publication guard and say a failed check routes the same way, REQ-FUNC-faab24b2 prose overlaps remediation, reset --to publishing can still publish a legacy deliver run, no published_fingerprint state tests, French release note wording
- 2026-10-26 validate: returned to build - review round 2 findings: stale isolation and recovery docs, coverage-table pipes, publication and retry wording, faab24b2 prose, legacy publishing reset, published_fingerprint tests, French release note
- 2026-10-26 build: red: pytest -q tests/test_orchestrator.py -k recorded_at_deliver exit 1 (1 failed) - reset still points a run recorded at deliver at publishing (REQ-FUNC-f9bdb5d2); the review-round retry and published_fingerprint state tests pass without code change (REQ-FUNC-d8d1b95b)
- 2026-10-26 build: green: pytest -q on the 11 changed or affected Python suites exit 0 (619 passed, 1 skipped); ruff check adore tests exit 0; check_release_notes.py --since 9bb9661 exit 0 - reset refuses publishing for a deliver run; round 2 docs fixed (isolation test note, recovery accounting, publication guard and retry wording, failed-check routing, legacy in-review runs not carried over), coverage-table pipes fixed, REQ-FUNC-faab24b2 prose matched to the route, French note reworded, test_doctor.py and doctor.md working copies back to LF
- 2026-10-26 build: completed; next validate - review round 2 findings fixed; back to validate for review round 3 at the user's standing instruction (6 Done checklist item(s) left unticked)
- 2026-10-26 validate: review round 3 - spec approved and quality approved, both with minors: a deliver run can still be published through two forced resets (validate, then publishing), contradicting the reset comment and REQ-FUNC-40057219's rationale; no test loads a non-empty approved_product; REQ-FUNC-faab24b2 prose literally overlaps REQ-FUNC-9246f8cc and REQ-FUNC-67469d47; French release notes drop 'désormais', 'à nouveau' and 'suivent'; REQ-FUNC-f9bdb5d2 updated date stale; a transient Windows PermissionError on os.replace in unchanged code. The minors are fixed before the final proof, which invalidates the round 3 verdicts and needs review round 4
- 2026-10-26 validate: returned to build - review round 3 minors: refuse every reset of a deliver run, approved_product load test, REQ-FUNC-faab24b2 trigger wording, French notes, f9bdb5d2 date
- 2026-10-26 build: red: pytest -q tests/test_orchestrator.py tests/test_state.py -k 'recorded_at_deliver or removed_deliver_stage' exit 1 (5 failed, 2 passed) - reset still accepts frame, specify, design, build and validate for a run recorded at deliver, so reset to validate then publishing would publish its old approval (REQ-FUNC-f9bdb5d2); the extended deliver history load with a non-empty approved_product passes without code change, covering existing behavior (REQ-REL-2e67fc6d)
- 2026-10-26 build: green: pytest -q tests/test_orchestrator.py tests/test_state.py tests/test_smoke.py exit 0 (206 passed); ruff check on orchestrator.py and the two test files exit 0; python 02_Tools/check_release_notes.py exit 0 - reset refuses every target for a run recorded at deliver, linked as test_reset_refuses_every_target_for_a_run_recorded_at_deliver (REQ-FUNC-f9bdb5d2, updated 2026-10-26); the deliver history load keeps a non-empty approved_product (REQ-REL-2e67fc6d verification extended); REQ-FUNC-faab24b2 now triggers on a conduct step that starts at done; French Settings and Jobs notes keep 'suivent', 'désormais' and 'à nouveau'; CHANGELOG, CLI_Reference, Component_CLI, Component_Orchestrator, the orchestrator knowledge page, the journal Design and coverage row describe the wider reset refusal; the diagram adds the review-round retry, _published, _enter_review and published_fingerprint nodes and marks reset changed, matching the Design
- 2026-10-26 build: evolution --task TASK-6e8cc2e7 reviewed: 57 modified paths, 0 added, 0 removed, the same set as review round 2 (round 3 touched only paths already in it); check --task TASK-6e8cc2e7 errors=0 warnings=26, the same 26 accepted in the build DEVIATION; the unscoped check shows 34 because it diffs the branch against master (merge base a4d0e20), adding secret-in-diff on earlier commits' test fixtures and outside-layout on the deploy's .gitignore and claude.md, none from this task; the Pyright notes on orchestrator.py lines 849, 1228 and 2830 predate the base 9bb9661
- 2026-10-26 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-10-26 validate: review round 4 briefed to two independent reviewers (specification compliance, implementation quality) on the whole candidate, with the round 3 minors to confirm: every reset of a deliver run refused, approved_product history load, REQ-FUNC-faab24b2 trigger, French notes, f9bdb5d2 date
- 2026-10-26 validate: review round 4 - spec approved and quality approved, both with minors. Spec: the diagram misclassifies _launch_stage and RunState.from_dict as unchanged, lacks the retry -> _enter_review and retry -> conduct edges and the remediation returns from done; the State changed: line still names the round 2 fixes; log line 352 names check_release_notes.py without --since (the reviewer reran --since 9bb9661: ok). Quality: no negative test for the non-empty candidate_fingerprint check in _published or for retry's done/publishing limit on the review shortcut (mutations survive); the _conduct_task_impl docstring and Component_Orchestrator.md say 'no current evidence' while the route runs only on empty evidence (stale evidence is strictly verified again at done); retry still accepts a run recorded at deliver, which fails closed with no publication but misleading guidance. Fixed in review round 5: the two negative tests, the evidence wording wherever it states the general rule, the diagram and the journal records. Accepted: retry of a deliver run - RULING-002 does not carry such runs over, nothing is published, and reset's refusal names cancel or delete
- 2026-10-26 validate: correction to the round 3 green line - python 02_Tools/check_release_notes.py --since 9bb9661 also exited 0 (release notes: ok) before the advance that named it as evidence
- 2026-10-26 validate: returned to build - review round 4 minors: negative retry tests for the published-candidate guards, verification-evidence wording, diagram accuracy
- 2026-10-26 build: red (mutation, tests for existing behavior): with the non-empty candidate check removed from _published in memory, pytest -q tests/test_orchestrator.py -k 'failed_at_done_before_verification or reset_to_an_earlier_stage' exit 1 (test_retry_of_a_run_failed_at_done_before_verification_conducts_from_done fails); with retry's done/publishing limit removed, exit 1 (test_retry_conducts_a_published_run_reset_to_an_earlier_stage fails); both pass on the real code, which needs no change (REQ-FUNC-d8d1b95b)
- 2026-10-26 build: green: pytest -q tests/test_orchestrator.py tests/test_state.py tests/test_smoke.py tests/test_checkpoint_handoff.py exit 0 (246 passed); ruff check adore tests exit 0; python 02_Tools/check_release_notes.py --since 9bb9661 exit 0 - REQ-FUNC-d8d1b95b verification and links name the two negative retry tests; the _conduct_task_impl docstring, Component_Orchestrator.md, Integrating_A_Runtime_Project.md, CHANGELOG, the orchestrator knowledge page, the journal Design and coverage row say 'no verification evidence' (the Frame keeps the wording the user accepted); the diagram table and conductor flowchart now follow the code's function-level changes and call edges (AST comparison against 9bb9661), mark _launch_stage, _handoff_notice, _publish, _invalidate_approval, _reconcile_review, STATUS_STAGES and RunState.from_dict changed, and the state diagram adds the remediation returns from done
- 2026-10-26 build: evolution --task TASK-6e8cc2e7 reviewed: 57 modified paths, 0 added, 0 removed, unchanged since review round 3; check --task TASK-6e8cc2e7 errors=0 warnings=26, the 26 accepted in the build DEVIATION
- 2026-10-26 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-10-26 validate: review round 5 briefed to two independent reviewers on the whole candidate, with the round 4 minors to confirm
- 2026-10-26 validate: review round 5 - spec approved and quality approved, both with minors. Spec: the conductor flowchart draws the probe from _conduct_task_impl (it is called from _conduct and _reconcile_review) and draws the new retry, _published and _enter_review edges as unchanged (-->) instead of added (==>); the REQ-FUNC-d8d1b95b coverage row names only the round 1 retry tests; config.py, Component_Config.md, the config knowledge page and config.example.toml call the five timeout keys the stages that launch an executor, while the done route session also launches one and uses budgets.per_gate_timeout_seconds; one transient failure of a new retry test in over 80 runs, cause not captured. Quality: no test for the publishing half of retry's return to review (narrowing it to done survives the suites); no test for the STRICT_STAGE_MISMATCH guard in _strict_verification (none before this task either). Both reviewers confirm the round 4 items resolved
- 2026-10-26 validate: round 5 minors accepted without a further fix round (as announced to the user after round 4): the two untested guards behave correctly and every other publication and reset guard has a test that fails on its mutant; the timeout wording matches RULING-003's behavior and only omits the done route session's fallback; the transient failure is watched in the final proof. Corrected as records outside review: the diagram edges (diagrams.md: nothing checks the file and no review reads it) and the REQ-FUNC-d8d1b95b coverage row, which now names the tests its requirement links
- 2026-10-26 validate: records corrected after the round 5 verdicts, outside review: the diagram's conductor flowchart is split into 'Conducting a task' (15 nodes) and 'Approval, publication and retry' (18 nodes) per diagrams.md's size rule, the probe hangs off _conduct, allowed_transition is reached through _transition_accepted, and the edges new in this change (retry to _published and _enter_review, the published_fingerprint write and read) are drawn as added; the REQ-FUNC-d8d1b95b coverage row names the review-round, unverified-at-done and reset-to-validate retry tests
- 2026-10-26 validate: final: python .agentic/aegis.py check --task TASK-6e8cc2e7 --strict --run exit 0; test (.venv pytest -q, full suite) ok in 199.2s, lint (ruff check adore tests) ok in 0.4s, frontend (npm --prefix web run validate: node tests and the Playwright e2e suite) ok in 232.6s; strict: ok; errors=0 warnings=26 notes=22. The 26 warnings are the ones accepted in the build DEVIATION: 16 uncovered-source on the help topics, release notes, e2e fixtures and a web unit test, 7 journal-header on historical journals, 2 stale-paths on REQ-FUNC-5de75419, 1 outside-layout on config.example.toml; none limits the candidate or its verification. The 22 notes are manual-verification reminders on requirements outside this task. The transient Windows PermissionError seen in review did not occur. No candidate file changed after the round 5 verdicts; only the journal and the diagram did
- 2026-10-26 validate: note - the build-stage Done checklists were left unticked at each advance (the advance lines record it); the Log carries each item's evidence: red and green lines, the anchor, evolution and check reviews. The validate checklist is ticked 9/9 and the report appended
- 2026-10-26 validate: completed; next done

## Rulings

- RULING-001 | date=2026-10-25 | decision=AEGIS closes before approval: the executor's validate session ends with check --strict --run, report and advance to done; that advance triggers ADORE's independent strict check and candidate-bound approval; after approval ADORE only pushes and opens or adopts the MR/PR, with no executor session and no AEGIS command; an invalidated approval reopens the task with advance --to validate | reason=user answer at the frame checkpoint | source=user | supersedes=none
- RULING-002 | date=2026-10-25 | decision=No compatibility with the pre-0.15.0 AEGIS flow: ADORE requires AEGIS 0.15.0 or newer and conducts no deliver stage, 6_deliver.md, Handoff or Stage report; runs begun before the upgrade are not carried over | reason=user answer: ADORE is in development and only the current implementation matters | source=user | supersedes=none
- RULING-003 | date=2026-10-25 | decision=stage_timeout_overrides accepts only frame, specify, design, build and validate; a deliver key fails configuration validation like any unknown stage | reason=user answer: no compatibility with the old version is needed | source=user | supersedes=none
- RULING-004 | date=2026-10-25 | decision=ADORE's own persisted run state and run journals that name deliver stay readable for history display only; no conduct, reset or setting path accepts deliver | reason=frame constraint accepted with the scope: dropping it would turn existing web job history into run_state_corrupt and run_journal_corrupt | source=user | supersedes=none
- RULING-005 | date=2026-10-26 | decision=Scope adds the .agentic/aegis.toml [diagrams] table with structure, sequence and state and the [zones] comment aligned with the AEGIS 0.15.0 default | reason=user requests during build and validate; repository configuration, no product change | source=user | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-6e8cc2e7.md
changed: ADORE conducts AEGIS 0.15.0: validate closes the task, ADORE verifies the validate -> done advance and presents, publication is push plus MR/PR only, done-stage revalidation and remediation routes, AEGIS >= 0.15.0, five stage-timeout keys, retry and reset routing with published_fingerprint, deliver history readable; docs, help, release notes, CHANGELOG, knowledge and requirements updated
evidence: python .agentic/aegis.py check --task TASK-6e8cc2e7 --strict --run exit 0
issues: accepted minors: retry of a run recorded at deliver fails closed with misleading guidance (RULING-002); no test for the publishing half of retry's return to review or for STRICT_STAGE_MISMATCH; the timeout wording omits the done route session's per-gate fallback; live acceptance on a real runtime project not run
spec_compliance: approved
implementation_quality: approved
review_round: 5

## Delivery report (2026-10-26)

- stage: validate; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-9246f8cc - Verify the candidate when validate closes the task
  - REQ-FUNC-faab24b2 - Return an unverified done task to validate
  - REQ-FUNC-67469d47 - Return the task after failed independent verification
  - REQ-FUNC-67bd56c8 - Publish an approved candidate without an executor session
  - REQ-FUNC-ff7dad34 - Conduct governed ticket delivery
  - REQ-FUNC-ab65704b - Surface recorded AEGIS deviations at the approval gate
  - REQ-FUNC-8472a560 - Refuse AEGIS releases older than 0.15.0
  - REQ-FUNC-69bfe896 - Detect runtime environment readiness
  - REQ-FUNC-16237c6d - Validate AEGIS tasks and strict check evidence
  - REQ-FUNC-fbc3fca5 - Direct stage sessions to the AEGIS journal writers
  - REQ-REL-94e653aa - Preserve DCP checkpoint, handoff, and subscription budget semantics
  - REQ-DATA-eebc4f88 - Reject stage-timeout overrides outside the current stages
  - REQ-FUNC-d67a1d33 - Reviewed clarification and recovery collection settings
  - REQ-UX-66547cbf - Human duration retry schedule and five-stage timeout editors
  - REQ-FUNC-f9bdb5d2 - Limit reset targets to current stages and publishing
  - REQ-REL-2e67fc6d - Read run history that names the removed deliver stage
  - REQ-FUNC-d8d1b95b - Route a retry at the publication boundary
  - REQ-FUNC-40057219 - Refuse to publish a run outside the done stage
- deviations: 1 recorded
  - build: 26 check warnings accepted - 16 uncovered-source on the help topics, release notes, e2e fixtures and a web unit test this task changed, which are documentation, user notes and test fixtures no requirement claims as product source (as on earlier tasks); 10 pre-existing: 7 journal-header on historical journals, 2 stale-paths on REQ-FUNC-5de75419, 1 outside-layout on config.example.toml; none limits the candidate or its verification
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=5
- diff vs task base 9bb9661: 87 file(s) changed, 2388 line(s) added
- checks: errors=0 warnings=26 notes=22
- checklist: 9/9 done
