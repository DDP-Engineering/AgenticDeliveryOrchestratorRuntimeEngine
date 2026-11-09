<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-e51f205c - Refresh Settings, Access and Change history automatically

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-9aea4d22, REQ-UX-1df0b1ce, REQ-UX-d64b7511, REQ-UX-183b80f6
parent:
branch: task/adore-web-interface
base: bb3141c9afb6bf286379c5449835e98da9bf5256
opened: 2026-11-09

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
- [x] final targeted proof and deviation logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem: OBSERVED Settings, Access and global Change history depend on explicit reloads.
Desired outcome: STATED Automatically update these views and suspend Settings updates while it has unsaved changes.
Actors: STATED web users viewing project settings, and authorized administrators viewing Access or Change history.
Primary scenario: STATED Watch a view reflect server data while it remains visible.
Examples: STATED Draft Settings edits stop automatic updates until they are saved or discarded.
Counterexamples: INFERRED A response begun before an edit must not overwrite the resulting draft.
In scope: STATED The three named views; INFERRED their header control, existing read validation and affected help.
Out of scope: STATED UI data refresh only, so no monitoring cadence, new requests to the forge or agent, or change to the separate project History view.
Constraints: STATED AEGIS, autopilot and focused verification from this session. OBSERVED Preserve existing local changes and use the current branch. Bound work to two hours, 30 task files and five review cycles. No live model, forge or job runs.
Success signals: STATED Visible views refresh without manual action, Settings protects unsaved input, and refresh resumes once edits are resolved.
Evidence: OBSERVED App.tsx manualRefresh, SettingsList draft lifecycle and ProjectAccess; AuditHistory.tsx, polling.ts, REQ-UX-183b80f6.
Assumptions: INFERRED Reuse the existing 15-second interval and visibility behavior for ordinary reads.
Unknowns: None material.
Decision-blocking questions: None.
Proposed behaviors: INFERRED Quiet reads retain the current view until results arrive; current role/scope and errors retain existing protections.
Path and reason: Full path because the request changes observable behavior.

| Criterion | Holds? | Evidence |
| --- | --- | --- |
| no new externally observable behavior | no | STATED Automatic reads in three views |
| no new interface or data format | yes | OBSERVED Existing endpoints and forms |
| no new dependency | yes | OBSERVED Existing visibility polling helper |
| an existing requirement already covers the behavior | no | OBSERVED Header policy exists, but excludes these views |
| no security or data-handling change | yes | INFERRED Preserve existing scope, validation and mutation contracts |

## Requirement coverage

| Behavior | Requirement | Observable evidence |
| --- | --- | --- |
| Refresh Settings only while clean | REQ-UX-9aea4d22 | A held read cannot erase a draft, and reads resume after discard |
| Refresh selected project Access | REQ-UX-1df0b1ce | Grants refresh and a confirmed mutation supersedes older reads |
| Refresh Change history | REQ-UX-d64b7511 | Filtered events refresh without resetting the view |
| Limit manual header controls | REQ-UX-183b80f6 | Header Refresh only on the specified manual views |


## Design

### Approach
OBSERVED startVisiblePolling already suspends timers when the document is hidden. Reuse it at 15 seconds for Settings, Access and global Change history. INFERRED Settings protects independent configuration, pricing and authentication drafts or writes with a synchronous barrier and a revision check at response time (REQ-UX-9aea4d22). Price reads settle independently and validate their response before publishing it.
INFERRED Access polls its selected project only and invalidates older reads when an access mutation starts (REQ-UX-1df0b1ce). Audit refresh retains filters, pagination and expanded evidence (REQ-UX-d64b7511). Header Refresh stays on Users and project History (REQ-UX-183b80f6).

### Interfaces and data
Existing same-origin GET endpoints and response validation. Background reads retain validated data while pending and show the existing failure state for a current failed read. No persisted data or permissions change.

### Files and test seams
App.tsx and AuditHistory.tsx, existing serial Chromium settings, shell and audit specs. Exercise timers, draft races, stale access, malformed audit data and the header. Update help and production bundle.

### Risks and open decisions
A draft may begin and end before an old response settles. A barrier revision invalidates that read even after the form becomes clean. Scope and session changes discard older results. No decision remains open.

### Requirement map
The four decisions above map one-to-one to the requirement table and browser assertions.

Diagrams: [diagram_TASK-e51f205c.md](diagram_TASK-e51f205c.md)


## Log

- 2026-11-09 frame: journal opened
- 2026-11-09 frame: completed; next specify
- 2026-11-09 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-09 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-09 build: Baseline includes prior uncommitted enrollment and empty-state fixes; preserve them and distinguish their diff from this task.
- 2026-11-09 build: red: focused Chromium baseline exited 1. Settings and Access did not issue background reads; the header still showed Refresh on global Change history. The audit fixture failed on an accessible-name selector, now corrected.
- 2026-11-09 build: green: npm run build:e2e and Chromium settings/shell/audit specs filtered by background, header, stale Save and transport failures exited 0 (7 tests); node help/polling tests passed (15 tests).
- 2026-11-09 build: release-notes: updated (visible automatic refresh and pause).
- 2026-11-09 build: help: updated (interface, settings and administration in en/fr/de/ro).
- 2026-11-09 build: Build check: 0 errors, advisory repository findings for test-file classification and coverage, pre-existing paths, journals and ticket references. Generated JS exceeds the automatic added-line scan threshold. No other source or schema was changed by this task.
- 2026-11-09 build: completed; next validate
- 2026-11-09 validate: Review 1: protect tariff and authentication forms, uncouple and validate tariff reads, reconcile a newly saved revision with a newly prepared candidate, and correct the four-locale Settings guidance. Strengthen interval/resume proof.
- 2026-11-09 validate: returned to build - Resolve review findings on unsaved forms, independent price reads, candidate recovery, and outdated help.
- 2026-11-09 build: Review fix red: focused Chromium exit 1 (2/2 regressions reproduced: a held price read prevented Settings from opening, and a new revision erased the concurrently recovered edit).
- 2026-11-09 build: Review fix green: build:e2e and 12 targeted Chromium cases exit 0; after adding price-write invalidation, npm run build and build:e2e exit 0 and all three Settings background regressions pass. The first rerun had a Windows worker exit 3221226505; a clean rerun passed 3/3.
- 2026-11-09 build: Inspection: checked changes since the anchor (27 paths), all four locales, the live static asset (HTTP 200), and release consistency (0.13.0). Bundle inspection detected no private key, AWS or OpenAI key patterns; AEGIS automated added-line scan skips the large generated asset.
- 2026-11-09 build: completed; next validate
- 2026-11-09 validate: DEVIATION validate: focused Chromium and help/polling tests plus static strict check replace the full --strict --run, per the user's standing targeted-test instruction. Full Python, Ruff and frontend suites are outside this proof.
- 2026-11-09 validate: final: check --strict --json, check_release_notes.py --since bb3141c, git diff --check, node help/polling (15) and Chromium targeted settings/shell/audit/executor-config (12) exit 0. Static check: 0 errors, 67 advisory warnings. Repository-wide paths, journals and ticket references are unrelated; E2E specs are classified as source by the configured globs, and the large generated JS exceeded the added-line scan (direct key-pattern inspection recorded).
- 2026-11-09 validate: completed; next done

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-e51f205c.md
changed: Visible refresh, protected settings, price and authentication drafts, and updated help
evidence: Strict static check, 12 focused Chromium tests, 15 help/polling tests and release checks exit 0
issues: Targeted validation; advisory findings and generated asset scan limit recorded in the journal.
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-09)

- stage: validate; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-9aea4d22 - Refresh clean project settings while visible
  - REQ-UX-1df0b1ce - Refresh project access while visible
  - REQ-UX-d64b7511 - Refresh global change history while visible
  - REQ-UX-183b80f6 - Show the header Refresh only on pages without automatic updates
- deviations: 1 recorded
  - validate: focused Chromium and help/polling tests plus static strict check replace the full --strict --run, per the user's standing targeted-test instruction. Full Python, Ruff and frontend suites are outside this proof.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base bb3141c: 53 file(s) changed, 971 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=67 notes=24
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
