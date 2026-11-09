<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-12cca970 - Safe abandon and restart after execution drift (#30)

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-FUNC-e6a17de1, REQ-SEC-df6e3bf2, REQ-REL-1eee76af, REQ-UX-cb0a0637
parent:
branch: task/adore-web-interface
base: 9b7cbcfda02d7c47871dbc1d5d3af573d2dec0fd
opened: 2026-11-05

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

Problem: STATED issue #30: configuration drift prevents recovery, delete can traceback and an owned remote checkpoint can prevent a fresh start.
Desired outcome: STATED operator abandons and restarts a failed job with confirmation in the web UI, with verified owned cleanup and clean CLI errors.
Actors: STATED authorized web operator and CLI administrator.
Primary scenario: STATED stable execution settings changed; Retry cannot preserve the saved job contract; confirm abandon/restart using current settings.
Examples: STATED resized VM changes NUMBER_OF_PROCESSORS/PROCESSOR_*; OBSERVED native Retry already refreshes volatile environment/executable identity.
Counterexamples: STATED foreign native receipts or changed remote branches must remain untouched.
In scope: STATED six issue acceptance criteria; cleanup, bounded worker operation, drift guidance, localized help/notes and offline proof.
Out of scope: STATED no migrations, real jobs, real resource deletion, push, PR, merge, planning edits or service restart.
Constraints: STATED current branch and checkout, Pi only, AEGIS 0.15, manual Start while monitoring paused; autopilot=true. Limits: 120 minutes, 60 changed files, three validation fix rounds, zero paid model/API calls.
Success signals: STATED confirmed web restart cleans only proven owned resources; delete drift has typed actionable errors; remote leases retained; worker lock guidance; useful drift Job details.
Evidence: OBSERVED tea issues 30 --comments --login ddp --repo dpasare/AgenticDeliveryOrchestratorRuntimeEngine; cli._cmd_run_op currently rethrows non-Retry native failures; LocalBackend.verify_identity pins current policy; WorktreeManager.remove_remote_branch already implements exact leases.
Assumptions: INFERRED existing operation roles/idempotency and conductor locks remain authoritative.
Unknowns: UNKNOWN live host acceptance; excluded by explicit instruction.
Decision-blocking questions: None; issue and delegation authorize implementation choices within the cleanup boundaries.
Proposed behaviors: Accepted issue scope above; no additional product features.
Path and reason:
| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | confirmed restart |
| no new interface or data format | no | explicit owned delete option |
| no new dependency | yes | existing Git lease/backend/queue |
| an existing requirement already covers behavior | no | new recovery operation |
| no security or data-handling change | no | owned destructive cleanup |
Full path; no child tasks needed.

## Requirement coverage

| Behavior | Requirement | Design | Proof |
|---|---|---|---|
| functional | REQ-FUNC-e6a17de1 | owned restart flow | offline public contracts |
| security | REQ-SEC-df6e3bf2 | owned restart flow | offline public contracts |
| reliability | REQ-REL-1eee76af | owned restart flow | offline public contracts |
| ux | REQ-UX-cb0a0637 | owned restart flow | offline public contracts |


## Design

### Approach
REQ-FUNC-e6a17de1: queue one restart operation; CLI owns locked cleanup and fresh manual admission. Reuse forge-agnostic Git exact leases. Do not change run IDs or stored schema. Use bounded derived branch generations only when needed to preserve an unproven occupied ref.
REQ-SEC-df6e3bf2: explicit --owned-resources on delete bypasses only current native policy equality; still validate saved plan/receipt, immutable host/account, exact paths and process-scope ownership. Reject human-owned jobs and foreign branches. A dedicated cleanup-only native adapter avoids requiring a now unavailable executable.
### Interfaces and data
Add restart CLI command with --force and --expected-revision, plus delete --owned-resources. REST restart requires confirmation and a state revision from Job details. Persist the revision in the restart queue target, and recheck it under conductor lock before mutation. Partial cleanup retains state; restart never proceeds on failure. Cleanup releases actual container/proxy/network immutable IDs independently of current backend/egress policy, and permits native empty-resource plans only with no unrecorded control. Terminal summaries are cleared under conductor ownership; registered web profiles serialize source deletion and usage-projection reset in one SQLite write transaction with transaction-time source guards on reporting readers. Stats rebuild holds the conductor lock to prevent stale summary writes. Missing remote branches are safe; present branches require saved commit and exact lease. Current configuration and selection checks remain authoritative for new admission, including paused manual Start.
REQ-REL-1eee76af: typed cleanup failures return error with guidance; lock messages name worker and Summary pause.
REQ-UX-cb0a0637: use four-locale native confirmation dialog, drift explanation, and restart control; hide Retry only for stable drift, retain volatile environment retry.
### Files and test seams
cli.py, orchestrator.py, local_execution.py, isolation.py; web app/jobs/commands/store; jobModel, JobWorkspace and localized recovery copy. Dedicated offline recovery tests reuse injected backends/forge/runner; frontend unit and browser journeys prove confirmation and refusal. Update component/operator docs, knowledge, help and notes in same change.
### Risks and open decisions
Retained resources after partial failure remain operator-visible via original state. Remote deletion uses known checkpoint commit only. No weakening of execution/retry identity, no migrations and no real resource checks. No open decisions. Previously orphaned no-checkpoint refs are retained on restart with reported fresh-generation admission; known changed checkpoints refuse. Actual naming rules must permit a fresh name before cleanup. Fresh local branch creation is atomic and rejects existing paths.
### Requirement map
REQ-FUNC-e6a17de1: locked cleanup then manual admission.
REQ-SEC-df6e3bf2: saved ownership plus exact Git lease.
REQ-REL-1eee76af: clean typed failures and worker lock hint.
REQ-UX-cb0a0637: confirmed localized recovery and drift routing.
Diagrams: [diagram_TASK-12cca970.md](diagram_TASK-12cca970.md)


## Log

- 2026-11-05 frame: journal opened
- 2026-11-05 frame: completed; next specify - Issue acceptance scope recorded; user authorized autopilot
- 2026-11-05 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-05 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-05 build: red: pytest -q tests/test_drift_recovery.py exit 1; 11 expected failures for missing delete/restart public APIs (REQ-FUNC-e6a17de1, REQ-SEC-df6e3bf2)
- 2026-11-05 build: red: pytest drift recovery web test exit 1 (missing state_revision); node --test web/tests/jobs.test.mjs exit 1 (missing drift routing export), REQ-FUNC-e6a17de1 and REQ-UX-cb0a0637
- 2026-11-05 build: release-notes: added (confirmed recovery visible in four locales)
- 2026-11-05 build: help: updated (Jobs recovery in en/fr/de/ro)
- 2026-11-05 build: release-notes: updated (merged confirmed recovery into existing Jobs improvement to retain category cap)
- 2026-11-05 build: green: pytest drift recovery + merged branch + smoke selectors exit 0 (62 passed); node jobs/help exit 0 (17 passed); Playwright driftRecovery exit 0 (4 locale journeys); typecheck and release-note check exit 0
- 2026-11-05 build: review round 1: both reviewers requested cross-backend/egress cleanup, native preprovisioned absence, saved identity validation and fresh statistics. Fixed actual ID-only release and serialized source/projection reset; stats rebuild now takes conductor lock.
- 2026-11-05 build: green: pytest -q tests/test_drift_recovery.py exit 0 (42 passed); independent quality reviewer reran 42 passed. Ruff exit 0. Round 2 spec and quality approved.
- 2026-11-05 build: completed; next validate
- 2026-11-05 validate: Final strict proof interrupted before any command result: acceptance audit found pre-existing orphan branches still block restart; no pass/fail evidence claimed for interrupted suite.
- 2026-11-05 validate: returned to build - Cover pre-existing unproven leftover branches with bounded fresh generation, preserving known checkpoint leases
- 2026-11-05 build: red: pytest drift generation selectors exit 1 (2 expected missing behaviors); original final proof was stopped before edits and is not evidence for the changed candidate.
- 2026-11-05 build: Run limit updated to 120 minutes, unchanged 60-file cap and three correction cycles, zero paid external AI calls; complete fresh proof retained after orphan regression fix.
- 2026-11-05 build: green: focused pytest drift/merged/naming/orchestrator exit 0 (281 passed); node jobs/help exit 0 (18 passed); naming and atomic-create regressions covered.
- 2026-11-05 build: Review round 3 findings resolved: verified own branch reuse under strict rules; atomic fresh local ref/path creation; unproven local ref preservation. Latest source independently approved by both reviewers.
- 2026-11-05 build: help: updated (four-locale old-orphan generation, preserved ref warning and strict naming-rule limits)
- 2026-11-05 build: green final focused candidate: 281 pytest tests, 18 Node jobs/help tests, 5 browser journeys, Ruff/typecheck/production+E2E builds/release-note check all exit 0. Final reconciled source/docs approved independently by both reviewers.
- 2026-11-05 build: completed; next validate
- 2026-11-05 validate: final: python .agentic/aegis.py check --task TASK-12cca970 --strict --run exit 0; full Python suite passed (587.3s), Ruff passed (0.1s), complete frontend validate passed (726.2s: helpers, TypeScript, offline Chromium). strict: ok; errors=0 warnings=43 notes=23. Existing unrelated requirement/task metadata warnings retained. New uncovered-source warnings are generated bundle/index, release-note/help assets and linked test files whose owning implementation requirements and proof are explicit in this journal; minified bundle secret-scan warning is a scan-size heuristic, with reviewed source and dependency license build. No live forge/container/model/resource acceptance was run, per user constraint.
- 2026-11-05 validate: completed; next done

## Rulings

- RULING-001 | date=2026-11-05 | decision=Continue build and complete orphan-branch acceptance case, then fresh independent review and one complete proof | reason=Explicit coordination instruction confirms autopilot and same-branch local commit | source=user | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-12cca970.md
changed: Implemented #30: confirmed drift recovery, owned cleanup, safe branch generations, lock guidance and fresh statistics; 58 files
evidence: Final check --strict --run exit 0: full Python, Ruff and complete frontend validate passed; independent reviews approved
issues: 43 advisory metadata/generated-artifact warnings explained in Log; live resource acceptance excluded by user
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-11-05)

- stage: validate; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-e6a17de1 - Confirmed abandonment and fresh restart of failed jobs
  - REQ-SEC-df6e3bf2 - Owned cleanup after native configuration drift
  - REQ-REL-1eee76af - Delete failures and conductor contention are actionable
  - REQ-UX-cb0a0637 - Job details route stable drift to confirmed restart
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 9b7cbcf: 58 file(s) changed, 2087 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=43 notes=23
- checklist: 9/9 done
