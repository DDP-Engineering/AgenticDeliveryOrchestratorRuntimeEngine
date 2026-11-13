# TASK-0067fee1 - Configure human approval before PR per project (#76)

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-751a55a1, REQ-REL-d3060dfd, REQ-UX-76628bfa, REQ-FUNC-ff7dad34, REQ-REL-94e653aa
parent:
branch: master
base: 80aa8b48b460a19b432ddc4fa80b3eebfcd8cd57
opened: 2026-11-12

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

Problem: OBSERVED issue #76 and orchestrator.py require human publication approval for every validated candidate.
Desired outcome: STATED project administrators can enable or disable the pre-PR approval gate; default enabled.
Actors: STATED project administrators, ticket operators and ADORE.
Primary scenario: STATED project policy disabled, validated candidate passes freshness checks and is published without waiting for label.
Examples: STATED default enabled requires freshly added agent-approved; disabled continues automatically.
Counterexamples: STATED PR merge remains human, validation and target freshness remain required.
In scope: STATED project setting, web UI, safe publication/recovery, both backends, tests and documentation.
Out of scope: STATED automatic merge or implementation of planned direct workflow.
Constraints: STATED no stored schema migrations, offline tests; OBSERVED current branch master; preserve unrelated TASK-b8a190d4. Bound: 150 minutes, 85 files (extended for documentation), five correction cycles, no paid calls.
Success signals: INFERRED selected policy governs approved and automatic publication without stale candidates or cross-project effects.
Evidence: OBSERVED issue #76; config.py DeliveryConfig; orchestrator.py approval and retry paths; web settings.
Assumptions: INFERRED apply current persisted setting on next reconciliation, with idle edit gate; fail closed on invalid policy.
Unknowns: UNKNOWN future direct-workflow implementation.
Decision-blocking questions: none.
Proposed behaviors: STATED enabled by default, automatic publication only after validation and fresh identity checks.
Path and reason:
| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | STATED automatic publication |
| no new interface or data format | no | STATED project setting |
| no new dependency | yes | INFERRED existing stack |
| existing requirement already covers behavior | no | OBSERVED approval required |
| no security or data-handling change | no | INFERRED approval policy |
Full path; autopilot in project configuration.

## Requirement coverage

| Behavior | Requirement | Design/test |
|---|---|---|
| project policy default and modes | REQ-FUNC-751a55a1 | typed config and orchestration tests |
| freshness and failure closure | REQ-REL-d3060dfd | fake Git and recovery tests |
| reviewed project UI | REQ-UX-76628bfa | web settings and locale tests |


## Design

Approach: REQ-FUNC-751a55a1 adds `delivery.require_human_approval` boolean, default true. The shared conductor chooses approval presentation or publication after verification. REQ-REL-d3060dfd extracts candidate/target freshness from approval-label checks and applies it immediately before every automatic publication and recovery.
Interfaces and data: policy changes use existing admin reviewed configuration save and busy-project safety. Current policy applies at the next safe reconciliation; existing jobs already in review remain there. Automatic mode verifies the saved validation evidence, task binding, target and fingerprint and revalidates drift; errors fail closed. No state schema changes or merge behavior changes.
Files and test seams: config.py, orchestrator.py, web settings labels/help, operator and component docs; injected forge/worktree fake tests, config and web tests, translated help tests.
Risks and open decisions: remote target can change after the final fetch; existing guarded branch publication and later integration boundaries remain. Direct workflow is not yet implemented.
Requirement map: REQ-FUNC-751a55a1 config and branching; REQ-REL-d3060dfd shared freshness and recovery; REQ-UX-76628bfa existing typed settings editor and localized descriptions.
Diagrams: [diagram_TASK-0067fee1.md](diagram_TASK-0067fee1.md)


## Log

- 2026-11-12 frame: journal opened
- 2026-11-12 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-12 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-12 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-12 build: red: targeted disabled_approval pytest exit 1; waiting candidate does not publish automatically or revalidate drift.
- 2026-11-12 build: green: disabled approval conductor tests exit 0, 3 passed; shared configuration and reviewed settings control added.
- 2026-11-12 build: release-notes: updated (project approval setting is user-visible)
- 2026-11-12 build: help: updated (publication, settings, overview and glossary in four locales)
- 2026-11-12 build: green: targeted config, web and orchestrator policy tests exit 0, 18 passed; candidate drift, bad config, Git errors, retry and both backend selections covered.
- 2026-11-12 build: red: independent review regression tests exit 1: stale or missing source tickets and partial or unbound validation evidence allowed automatic publication.
- 2026-11-12 build: green: review fixes: source ticket state, complete bound validation evidence, policy re-enable and idle edit boundary; targeted tests exit 0; setting-help catalog tests exit 0.
- 2026-11-12 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-12 validate: DEVIATION validate: extend self-selected file bound from 60 to 70 paths to include required localized help, refreshed bundle and review corrections; no user-set numeric cap.
- 2026-11-12 validate: review round 1: retry must check closed source before settlement or progress push; remaining operator/component approval wording is unconditional.
- 2026-11-12 validate: returned to build - Check closed ticket before retry settlement and reconcile documentation
- 2026-11-12 build: green: review correction pytest exit 0, 15 passed; retry checks closed ticket before dirty worktree settlement, and docs describe configured approval.
- 2026-11-12 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-12 validate: review round 2: validate nonempty corrupt evidence before retry settlement; correct remaining unconditional approval wording.
- 2026-11-12 validate: returned to build - Refuse corrupt retry evidence before progress publication and reconcile help
- 2026-11-12 build: DEVIATION build: extend self-selected file bound from 70 to 85 paths to reconcile existing operator/component knowledge and four-locale help with optional approval; no user-set numeric cap.
- 2026-11-12 build: green: retry rejects corrupt validation evidence before dirty checkpoint settlement; targeted pytest exit 0, 15 passed.
- 2026-11-12 build: green: review correction; 410 targeted Python tests, 48 Node tests, one isolated Chromium settings journey, Ruff, release notes and release consistency all passed; bundle rebuilt.
- 2026-11-12 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-12 validate: Independent review round 3: specification compliance and implementation quality approved.
- 2026-11-12 validate: DEVIATION validate: full strict --run and full suites are omitted under the existing targeted-offline verification instruction; unrelated behavior is not proven.
- 2026-11-12 validate: final: targeted Python tests exit 0, 410 passed (one Starlette deprecation warning); 48 Node tests exit 0; isolated Chromium settings journey exit 0; Ruff, release-notes, release-consistency and git diff --check exit 0; AEGIS static strict exit 0, 0 errors, 68 warnings, 24 notes, including existing catalog warnings and uncovered-source metadata. Full strict --run omitted by user testing constraint.
- 2026-11-12 validate: completed; next done (1 Done checklist item(s) left unticked)

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-0067fee1.md
changed: Implemented and reviewed per-project publication approval policy
evidence: 410 Python tests, 48 Node tests and one Chromium journey passed; Ruff, release notes and release consistency exit 0
issues: Full strict --run omitted under targeted-offline instruction; static strict reports 68 warnings and 24 notes
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-11-12)

- stage: validate; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-751a55a1 - Configure human approval before publication per project
  - REQ-REL-d3060dfd - Verify candidate before automatic publication
  - REQ-UX-76628bfa - Review per-project publication approval policy
  - REQ-FUNC-ff7dad34 - Conduct governed ticket delivery
  - REQ-REL-94e653aa - Preserve DCP checkpoint, handoff, and subscription budget semantics
- deviations: 3 recorded
  - validate: extend self-selected file bound from 60 to 70 paths to include required localized help, refreshed bundle and review corrections; no user-set numeric cap.
  - build: extend self-selected file bound from 70 to 85 paths to reconcile existing operator/component knowledge and four-locale help with optional approval; no user-set numeric cap.
  - validate: full strict --run and full suites are omitted under the existing targeted-offline verification instruction; unrelated behavior is not proven.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 80aa8b4: 74 file(s) changed, 1039 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=68 notes=24
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
