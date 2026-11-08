<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-d7bb41ca - Gitea #37: clarify web actions and worker status

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-FUNC-ff3e4560, REQ-FUNC-0d77a111, REQ-UX-1141c28f, REQ-UX-c90fece3, REQ-UX-97054d74, REQ-UX-c000471e
parent:
branch: task/adore-web-interface
base: 5cfc05815f2963cf66d8de6914c40e4a0d294189
opened: 2026-11-08

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

Problem: STATED #37 reports unconfirmed cancel, stale monitoring, misleading worker readiness and wait, ticket layout/epics, and empty project/overview presentation.
Desired outcome: STATED clarify and safely enforce actions and actual worker status, and verify or fix each layout criterion.
Actors: STATED authorized administrators and project developers.
Primary scenario: STATED operate jobs and monitoring while another project uses the single worker.
Examples: STATED cancel requests confirmation and explains attempted worktree cleanup; activation updates the tile after observed success.
Counterexamples: STATED manual Start remains available with monitoring paused; no new implicit deletion merely to match old wording; existing cancellation cleanup is retained.
In scope: STATED backend trust boundaries, four-locale frontend/help, component and operator docs, bundled assets and focused offline validation.
Out of scope: STATED scheduling redesign, real jobs, forge writes, push, migrations and unrelated journal.
Constraints: STATED same checkout/branch, zero model cost, isolated fixtures; targeted tests only. Bound work to 120 files, 8 implementation/review cycles, 8 hours wall time, zero model calls.
Success signals: STATED all #37 criteria covered with honest execution results and public-boundary evidence; signed-off local commit.
Evidence: OBSERVED tea issues 37 and git status at base 5cfc058; .agentic/knowledge/web-interface.md identifies ownership.
Assumptions: INFERRED existing taxonomy and operation queue must be inspected before design.
Unknowns: UNKNOWN historical cause and which layout criteria already hold.
Decision-blocking questions: None identified.
Proposed behaviors: STATED follow issue and user's explicit preservation and verification constraints.
Path and reason:
| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | STATED confirmation and status visibility |
| no new interface or data format | no | STATED interface changes |
| no new dependency | yes | INFERRED existing stack |
| existing requirement covers behavior | unknown | inspect in specify |
| no security or data-handling change | no | STATED confirmation trust boundary |
Full path; autopilot authorized by user.

## Requirement coverage

| Behavior | Requirement | Design |
|---|---|---|
| When an operator requests cancellation, the web API shall reject the request unless explicit confirmation is true. | REQ-FUNC-ff3e4560 | See approach and test seams |
| When a ticket has the configured epic type label, ADORE shall refuse its manual start. | REQ-FUNC-0d77a111 | See approach and test seams |
| When a monitoring operation finishes, the web interface shall refresh the displayed project state from the observed result. | REQ-UX-1141c28f | See approach and test seams |
| While the control worker is processing work, the interface shall explain worker readiness and that queued commands can wait. | REQ-UX-c90fece3 | See approach and test seams |
| At desktop and mobile widths the tickets view shall keep ticket actions reachable. | REQ-UX-97054d74 | See approach and test seams |
| When there are no projects, the interface shall offer administrators project enrollment without an empty table panel. | REQ-UX-c000471e | See approach and test seams |


## Design

### Approach
REQ-FUNC-ff3e4560: require explicit strict confirmation at both cancellation HTTP boundaries and show localized warning covering retained worktree; retain worker reauthorization and cancel watcher.
REQ-FUNC-0d77a111: add a configurable epic label to selection and refuse that label through shared eligibility, including direct engine start. No title heuristics.
REQ-UX-1141c28f: poll actual operation and refresh project list on terminal outcome, including immediately terminal response; retain failures.
REQ-UX-c90fece3: report heartbeat separately from transient busy/idle evidence, explain serialized work and cancellation signals; never infer success from the signal.
REQ-UX-97054d74: verify existing responsive table; repair only remaining overflow.
REQ-UX-c000471e: remove empty projects panel and provide admin enrollment action on empty overview.

### Interfaces and data
The worker publishes ephemeral activity evidence, read only with a recent heartbeat; missing or corrupt evidence is unknown. No stored database schema change. Existing operation persistence owns actual outcomes. Cancellation requires boolean confirmation at public HTTP entrypoints. Configured type label extends current config defaults, no stored data conversion.

### Files and test seams
Selection/config, web app/store/worker and React workspace/ticket/shell; targeted public API and worker tests, localized browser cases, help and component/operator documentation. Build bundle with existing local Vite and verify index fingerprints.

### Risks and open decisions
Activity evidence can race process termination; stale heartbeat must prevent claiming availability and missing activity is unknown. Ticket labels are forge-normalized, not inferred from title. No scheduler changes or live data access.

### Requirement map
Each requirement maps to the corresponding approach above and its public API or browser test seam.
Diagrams: [diagram_TASK-d7bb41ca.md](diagram_TASK-d7bb41ca.md)


## Log

- 2026-11-08 frame: journal opened
- 2026-11-08 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-08 specify: DEVIATION validate: full strict --run proof is excluded by user instruction; targeted offline evidence and static check are required instead.
- 2026-11-08 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-08 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-08 build: red: targeted pytest cancellation and configured epic tests exit 1 - unconfirmed cancel admitted and epic setting unsupported (REQ-FUNC-ff3e4560, REQ-FUNC-0d77a111)
- 2026-11-08 build: green: targeted pytest cancellation and configured epic tests exit 0 (REQ-FUNC-ff3e4560, REQ-FUNC-0d77a111)
- 2026-11-08 build: red: targeted worker heartbeat tests exit 1 - activity evidence absent (REQ-UX-c90fece3)
- 2026-11-08 build: green: targeted worker heartbeat tests exit 0 (REQ-UX-c90fece3); teardown inspection shows worktree removal is attempted and may fail, so warnings describe both outcomes.
- 2026-11-08 build: release-notes: added (visible cancellation, worker and ticket changes)
- 2026-11-08 build: help: updated (cancellation, worker queue and epic selection in four locales)
- 2026-11-08 build: release-notes: updated (merged ticket controls into existing entry to respect category limit)
- 2026-11-08 build: DEVIATION build: frontend increment preceded its browser red proof; focused browser verification will test observed outcomes, with less test-first evidence.
- 2026-11-08 build: Review findings: stale/malformed operation responses, disappearing failures, missing queued guidance and stale activity binding require correction; help and journal wording need alignment.
- 2026-11-08 build: green: targeted pytest 30 passed; node help/settings 34 passed; serial Playwright issue37 4 passed in en/fr/de/ro at 1366 and 390; focused Ruff exit 0.
- 2026-11-08 build: Quality review: serialize monitoring and delete operation submission so no accepted outcome is discarded; retain current result until terminal.
- 2026-11-08 build: Review: ticket operation polling now reports invalid/failed reads, prevents replacing a pending operation, and explains start:epic; browser evidence extended for worker and waiting states.
- 2026-11-08 build: green: serial Playwright e2e/issue37.spec.ts 6 passed; node manualStart/help/settings 42 passed; configured epic and stale lock tests passed.
- 2026-11-08 build: Review: bind serialized operation POST completions to session generation so logout discards stale responses.
- 2026-11-08 build: Static check reports pre-existing stale paths/journals plus advisory generated-bundle/layout/coverage warnings. Bundled minified assets are scanned as generated data; source is reviewed and release consistency verifies output.
- 2026-11-08 build: green: serial playwright e2e/issue37.spec.ts exit 0, 7 passed (including four locales, desktop/mobile, session isolation and invalid outcomes).
- 2026-11-08 build: completed; next validate (1 Done checklist item(s) left unticked)
- 2026-11-08 validate: DEVIATION validate: full strict --run excluded by user; focused offline proof misses unrelated suite regressions and live acceptance.
- 2026-11-08 validate: final: targeted pytest exit 0 (32 passed); node manualStart/help/settings exit 0 (42 passed); serial Playwright issue37 exit 0 (7 passed); focused Ruff exit 0; npm build exit 0; release consistency and index fingerprint exit 0; static check exit 0 WARN (41 warnings, 24 notes; existing records and generated/layout coverage).
- 2026-11-08 validate: completed; next done (1 Done checklist item(s) left unticked)

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-d7bb41ca.md
changed: Validated and reviewed ticket 37 candidate
evidence: 32 Python, 42 Node, 7 serial browser tests; focused Ruff, production build, release consistency and index fingerprint passed
issues: Full strict --run and live acceptance excluded by user; static advisory warnings remain
spec_compliance: approved
implementation_quality: approved
review_round: 4

## Delivery report (2026-11-08)

- stage: validate; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-ff3e4560 - Require explicit confirmation for cancellation
  - REQ-FUNC-0d77a111 - Reject start of epic tickets
  - REQ-UX-1141c28f - Show observed monitoring operation results
  - REQ-UX-c90fece3 - Explain worker availability and queue waits
  - REQ-UX-97054d74 - Keep ticket actions accessible at narrow widths
  - REQ-UX-c000471e - Offer useful project empty states
- deviations: 3 recorded
  - validate: full strict --run proof is excluded by user instruction; targeted offline evidence and static check are required instead.
  - build: frontend increment preceded its browser red proof; focused browser verification will test observed outcomes, with less test-first evidence.
  - validate: full strict --run excluded by user; focused offline proof misses unrelated suite regressions and live acceptance.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=4
- diff vs task base 5cfc058: 64 file(s) changed, 3963 line(s) added
- checks: errors=0 warnings=41 notes=24
- checklist: 7/9 done; open: final `check --strict --run` result logged truthfully after the last edit; `report` appended
