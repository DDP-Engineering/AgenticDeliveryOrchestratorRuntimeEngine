# TASK-9ed4581f - Guard checkpoint staging against system cache paths



stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-REL-d31b1a6e
parent:
branch: task/adore-web-interface
base: bd6c52d3b69fa4dbe8eb577ae4534d823f32009e
opened: 2026-11-09

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

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
- [ ] final `check --strict --run` result logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem: STATED #47: a literal Windows environment-variable system cache was checkpointed and published.
Desired outcome: STATED stop a checkpoint with actionable evidence when newly included paths are suspicious, preserving files.
Actors: STATED operator and both executor backends.
Primary scenario: OBSERVED both backends share WorktreeManager checkpoint.
Examples: STATED %SystemDrive%/ProgramData/Microsoft/Windows/Caches/example.db.
Counterexamples: STATED ordinary percent names, generic cache directories, tracked and ignored paths remain governed by Git.
In scope: STATED untracked and already staged additions, robust Git evidence and tests.
Out of scope: STATED general secret scanning, other Git commits, automatic deletion, remote operations.
Constraints: STATED offline targeted tests, no full proof, no push; 120 minutes, 30 authored files, four correction cycles (extended after review); current branch and preexisting journal preserved.
Success signals: INFERRED normal checkpoint remains functional; suspicious path or corrupt Git evidence stops before commit/push with useful error.
Evidence: OBSERVED tea issue 47; TASK-f2692b34 RULING-003 applies to previous task; isolation.py commit_all_if_dirty.
Assumptions: INFERRED narrow system cache signatures and whole environment-variable segments are appropriate.
Unknowns: UNKNOWN exact future OS cache signatures.
Decision-blocking questions: none (STATED user authorizes decision).
Proposed behaviors: STATED fail closed while preserving evidence.
Path and reason:
| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | STATED refusal |
| no new interface or data format | yes | OBSERVED shared checkpoint |
| no new dependency | yes | INFERRED standard library |
| existing requirement covers behavior | no | OBSERVED explain |
| no security or data-handling change | no | STATED preservation guard |
Full path. Autopilot authorized.

## Requirement coverage

| Behavior | Requirement | Design and proof |
|---|---|---|
| Refuse suspect new paths and preserve files | REQ-REL-d31b1a6e | Shared checkpoint, injected Git boundary tests |


## Design

Approach: REQ-REL-d31b1a6e queries Git for untracked unignored files and staged additions before add and staged additions again after add; reject complete environment-variable segments and the Windows system cache suffix, case-insensitively. Existing tracked modifications and ignored files keep Git semantics.
Interfaces and data: NUL-delimited output must be complete, bounded, relative and well formed; invalid evidence raises IsolationError. A distinct subclass identifies a suspicious path. No files are deleted. Git results are never interpolated into commands.
Files and test seams: isolation.py and public WorktreeManager fake-runner tests; shared backend checkpoint entry. Operator and component docs describe remediation.
Risks and open decisions: concurrent index changes after the final inspection remain a race; no broad cache or secret scan. No stored format changes.
Requirement map: REQ-REL-d31b1a6e maps to pre-add evidence, explicit error and offline tests.


## Log

- 2026-11-09 frame: journal opened
- 2026-11-09 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-09 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-09 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-09 build: red: targeted checkpoint_rejects pytest exit 1; current checkpoint lacks refusal (REQ-REL-d31b1a6e)
- 2026-11-09 build: green: targeted checkpoint tests exit 0, 8 passed (REQ-REL-d31b1a6e)
- 2026-11-09 build: release-notes: updated (user-visible checkpoint refusal)
- 2026-11-09 build: help: none (existing help does not describe checkpoint creation or failure)
- 2026-11-09 build: green: targeted isolation and checkpoint handoff pytest exit 0, 106 passed, 1 skipped; release notes check exit 0
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: review round 1: invalid status/add/commit exit evidence; recheck staged additions after add; Unicode fixtures and public flow coverage.
- 2026-11-09 validate: returned to build - Fix independent review findings for Git evidence and post-add race
- 2026-11-09 build: review correction red: targeted invalid status and post-add recheck tests exit 1, missing fail-closed behavior
- 2026-11-09 review correction green: targeted isolation and checkpoint handoff pytest exit 0, 115 passed and 1 skipped; both backend configurations and no push covered
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: review round 2: porcelain type-change status T is valid and requires a public happy-path test.
- 2026-11-09 validate: returned to build - Accept valid Git type-change status and prove normal checkpoint
- 2026-11-09 build: review correction green: targeted pytest exit 0, 119 passed, 1 skipped; ruff exit 0; valid T and corrupt status paths/pairs covered
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: DEVIATION validate: full check --strict --run and full suites are prohibited by user; focused offline tests, changed-file lint and static check do not prove unrelated behavior.
- 2026-11-09 validate: review round 3: Git untracked directory status and valid conflict and worktree rename statuses require coverage; third correction cycle within bound.
- 2026-11-09 validate: returned to build - Preserve complete Git porcelain status behavior
- 2026-11-09 build: review correction green: focused pytest exit 0, 123 passed, 1 skipped; Ruff exit 0; Git porcelain nested, conflict and rename statuses covered.
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: DEVIATION validate: extend self-selected bound from three to four correction cycles; final review found valid embedded-repository directory records requiring coverage. User set no numerical cap; total remains bounded.
- 2026-11-09 validate: returned to build - Accept Git embedded repository directory records
- 2026-11-09 build: review correction green: targeted pytest exit 0, 124 passed, 1 skipped; Ruff exit 0; valid embedded repository record covered.
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: Review round 5: independent specification and implementation quality reviewers approved corrected candidate.
- 2026-11-09 validate: final: targeted pytest exit 0: 124 passed, 1 skipped; Ruff exit 0; release notes check exit 0; git diff --check exit 0; static strict check exit 0, 0 errors, 35 warnings, 24 notes (historical catalog and release-notes metadata). Full --strict --run and full suites omitted by explicit user instruction.
- 2026-11-09 validate: completed; next done (1 Done checklist item(s) left unticked)

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-9ed4581f.md
changed: Validated checkpoint path guard and documentation
evidence: Targeted pytest exit 0: 124 passed, 1 skipped; Ruff, release-notes, diff and static strict checks exit 0
issues: Full strict --run omitted by user; static check has 35 warnings and 24 notes
spec_compliance: approved
implementation_quality: approved
review_round: 5

## Delivery report (2026-11-09)

- stage: validate; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-REL-d31b1a6e - Refuse suspicious new checkpoint paths
- deviations: 2 recorded
  - validate: full check --strict --run and full suites are prohibited by user; focused offline tests, changed-file lint and static check do not prove unrelated behavior.
  - validate: extend self-selected bound from three to four correction cycles; final review found valid embedded-repository directory records requiring coverage. User set no numerical cap; total remains bounded.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=5
- diff vs task base bd6c52d: 11 file(s) changed, 515 line(s) added
- checks: errors=0 warnings=35 notes=24
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
