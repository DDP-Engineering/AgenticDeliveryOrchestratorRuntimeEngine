<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-28f31a9f - Restart cancelled jobs with retained history

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-2f57e5c6, REQ-REL-239792b2, REQ-UX-2b07baf2, REQ-UX-b2b63001
parent:
branch: master
base: 00f9d220dd7437b354e237a68136302e25bdfeea
opened: 2026-11-16

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [ ] diff reviewed against scope, requirements, design, error paths,
      portability, security and unrequested work
- [ ] knowledge pages of changed components current with the reviewed code
- [ ] project and environment context reconciled with the candidate
- [ ] requirements re-read: status, prose, verification, paths and links true
- [ ] manual or inspection verification recorded where applicable
- [ ] explicit review approved, when enabled
- [ ] final `check --strict --run` result logged truthfully after the last edit
- [ ] remaining warnings and pre-existing failures explained
- [ ] `report` appended

## Frame

Problem: OBSERVED: cancelled jobs block ticket Start and cannot use failed-only restart.
Desired outcome: STATED: implement applicable Gitea #95 behavior, preserving cancelled evidence and starting fresh; also group Storage status and its value (user follow-up).
Actors: STATED: administrators and assigned developers managing an authorized project.
Primary scenario: STATED: confirm Restart job with the chosen workflow for an open ticket whose latest job was cancelled; retain the old detail and admit a new execution.
Examples: STATED: cancelled ticket #25 may be restarted without recreating its previous Pi conversation.
Counterexamples: OBSERVED: Retry continues a failed job and must not resume a torn-down cancelled session.
In scope: STATED: fresh generation, history navigation, normal admission and ownership checks, Jobs/Tickets actions, four locales/help/docs; compact Storage grouping.
Out of scope: STATED: full test suite, commits and pushes remain outside this implementation request; OBSERVED: pre-release data migrations are forbidden.
Constraints: STATED: work on master and preserve existing uncommitted Python-test optimizations; targeted checks only. OBSERVED: current UI uses three tabs and explicit AEGIS/Direct restart actions.
Success signals: STATED: old cancellation and session evidence remain readable; new resources/budgets are independent; stale/unauthorized/concurrent/unsafe restart cannot create duplicate work; Storage value is adjacent to its status.
Evidence: OBSERVED: issue #95; orchestrator.restart/_restart_owned/delete; StateStore/run_id_pattern; web operation confirmation and worker context; jobModel.commandAllowed; App.tsx system-status-row.
Assumptions: INFERRED: generation suffixes and existing admission/operation protocols can provide the requested history without introducing another schema or migration.
Unknowns: Implementation-specific test selectors will be established while building; no user decision is missing.
Decision-blocking questions: None; the user authorized implementation and adaptation to current behavior.
Proposed behaviors: None awaiting acceptance.
Path and reason:
| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | cancelled Restart is new |
| no new interface or data format | no | fresh generation and navigation |
| no new dependency | yes | reuse existing application interfaces |
| existing requirement fully covers behavior | no | failed-only destructive restart |
| no security or data-handling change | no | retain cancelled history and fence fresh admission |
Full path; autopilot scope recorded from the user's implementation authorization.

## Requirement coverage

- REQ-FUNC-2f57e5c6: Restart cancelled jobs with preserved history
- REQ-REL-239792b2: Refuse unproven cancelled restart
- REQ-UX-2b07baf2: Restart cancelled jobs from Jobs and Tickets
- REQ-UX-b2b63001: Keep storage status and available capacity together

## Design

### Approach
Use a monotonic `-rN` suffix for fresh cancelled-job executions. Keep the original
run directory and archived IO in place. Resolve a ticket's current job to its
highest validated generation; normal Start still refuses an existing family.
Only the latest cancelled generation may restart (REQ-FUNC-2f57e5c6).

### Interfaces and data
Extend existing Restart rather than introducing another operation type. Exact
state confirmation, project authorization, CSRF, command ownership and existing
admission locks remain in force. Cancelled cleanup retains state/metrics;
failed-job abandonment stays destructive. Independent generation resources avoid
old cancellation markers and Pi context. Record predecessor/successor links in
the existing journal and expose read-only navigation (REQ-REL-239792b2).
Use existing workflow selection and four-locale copy in Jobs/Tickets. Restart
acknowledges durable admission and links the new run (REQ-UX-2b07baf2).
Place Storage label/status/capacity in a shared block (REQ-UX-b2b63001).

### Files and test seams
State family lookup/pattern; conductor restart/admission; CLI and worker command
result/ownership; Jobs/Tickets read models and UI; App/storage CSS. Target state,
drift-recovery, web-command/RBAC and existing frontend/E2E contracts only.

### Risks and open decisions
Generation lookup must refuse corrupt family members. Duplicate/stale history
restart must not admit another child. Preserve exact retained IO paths. Update
all four help locales. No stored schema migration or compatibility reader.
Existing uncommitted test-performance work is unrelated and remains intact.

### Requirement map
REQ-FUNC-2f57e5c6: retained cancelled history and fresh generation admission.
REQ-REL-239792b2: exact-state/latest-family/cleanup and admission fences.
REQ-UX-2b07baf2: workflow-aware confirmed actions and history links.
REQ-UX-b2b63001: adjacent storage block using existing localized strings.


## Log

- 2026-11-16 frame: journal opened
- 2026-11-16 frame: completed; next specify - User authorized implementation; current issue remains applicable with three-tab UI and explicit workflow choices (7 Done checklist item(s) left unticked)
- 2026-11-16 specify: completed; next design - Current requirements recorded; existing CSRF, ownership, idempotency and admission contracts remain authoritative (7 Done checklist item(s) left unticked)
- 2026-11-16 design: completed; next build - Generation design recorded without changing stored schema; current UI and ownership protocols reused (6 Done checklist item(s) left unticked)
- 2026-11-16 build: red: focused state generation contract exit 1; latest_run_id is absent (REQ-FUNC-2f57e5c6, REQ-REL-239792b2)
- 2026-11-16 build: green: focused StateStore generation/pattern tests exit 0 (3 cases); red: cancelled restart public conductor contract exit 1, failed-only lifecycle guard (REQ-FUNC-2f57e5c6)
- 2026-11-16 build: Integrated remote master by fast-forward to 76821f48 (Azure PR 96), reapplied all local work, resolved CHANGELOG only. Original anchor is retained; evolution includes upstream Azure and pre-existing test-performance work. Candidate review uses git diff 76821f48 and excludes those unrelated changes.
- 2026-11-16 build: red: pending cancellation notification contract exit 1; green: cancelled conductor success/revision/capacity/notification/cleanup cases exit 0 (5). Existing state/API/worker/history and UI targeted cases passed; helper/help checks exit 0 (29).
- 2026-11-16 build: help: updated (Jobs/Tickets restart history and System status storage grouping in en/fr/de/ro). release-notes: added (Restart job and grouped Storage in all four locales). Inspection: current three-tab UI retained; shared/multi-volume content is nested in the same Storage block; no automatic job-history deletion or format migrations.
- 2026-11-16 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-16 validate: returned to build - Review round 1: preserve failed generation admission target when cancelled predecessors exist; open immediate successful Tickets admission.
- 2026-11-16 build: Review round 1: quality found failed r1 abandonment fell back to retained cancelled base after deletion (red focused regression exit 1); pinned all restart admissions and restored retained predecessor links (green conductor+failed restart exit 0, 6 cases). Both roles found Tickets immediate-success navigation gap by inspection; handled terminal POST response and added immediate/queued browser cases.
- 2026-11-16 build: completed; next validate - Round 1 findings fixed with targeted regression; production and isolated frontend assets rebuilt. (6 Done checklist item(s) left unticked)
- 2026-11-16 validate: DEVIATION validate: user deferred full suite until the end; final proof is focused Python contracts, Node Jobs/help and five browser cases, plus lint/typecheck/build. Whole-repository regression coverage remains unproven. Advisory check reports existing retired requirement references in historical journals and unrelated old UX warnings; this task retains history and does not rewrite unrelated registry entries.
- 2026-11-16 validate: final: selected pytest contracts exit 0 (31 passed, 9.53s); node --test tests/jobs.test.mjs tests/help.test.mjs exit 0 (29 passed); targeted Playwright grep across jobs/tickets/shell exit 0 (5 passed, 19.7s). Last candidate lint, TypeScript, production/e2e builds, release-notes check and git diff --check passed. Existing Starlette/httpx deprecation and Vite large-chunk warnings accepted; full suite and archive checks not run.
- 2026-11-16 validate: completed; next done (9 Done checklist item(s) left unticked)

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-28f31a9f.md
changed: Master integrat; Restart job cu istoric păstrat; Storage grupat.
evidence: 31 Python + 29 Node + 5 E2E trecute; build și lint OK.
issues: Suita completă amânată; avertismente istorice AEGIS documentate.
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-16)

- stage: validate; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-2f57e5c6 - Restart cancelled jobs with preserved history
  - REQ-REL-239792b2 - Refuse unproven cancelled restart
  - REQ-UX-2b07baf2 - Restart cancelled jobs from Jobs and Tickets
  - REQ-UX-b2b63001 - Keep storage status and available capacity together
- deviations: 1 recorded
  - validate: user deferred full suite until the end; final proof is focused Python contracts, Node Jobs/help and five browser cases, plus lint/typecheck/build. Whole-repository regression coverage remains unproven. Advisory check reports existing retired requirement references in historical journals and unrelated old UX warnings; this task retains history and does not rewrite unrelated registry entries.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 00f9d22: 136 file(s) changed, 4229 line(s) added; 1 file(s) not content-scanned
- checks: errors=155 warnings=89 notes=14
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
