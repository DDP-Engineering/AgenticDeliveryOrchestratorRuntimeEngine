<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-919afe4e - Open shared password forms from Users

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-UX-66a271a7, REQ-FUNC-f470a75b
parent:
branch: task/adore-web-interface
base: a6b0fc675dbfec9dc15d40cc551172d8a9691903
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
- [ ] final `check --strict --run` result logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem: STATED the Users page shows a permanent Add user form and a separate cramped reset form.
Desired outcome: STATED start Add user and Reset password from the list and reuse the password/confirmation control.
Actors and example: STATED administrator starts Reset password for one named account or Add user from the list header.
Counterexample: INFERRED a mismatch, cancellation or invalid request cannot be reported as success.
Scope: browser Users workflows, localized copy and help, targeted tests and bundle.
Constraints: OBSERVED existing reviewed role/access and password-reset API; preserve pending edits and live test data. Bound work to 30 paths, 90 minutes and two review rounds. Local only.
Evidence: OBSERVED screenshot, App Users view, UserCreation and current API contract.
Unknowns: None material. Decision-blocking questions: none.
Path and reason: full. Adds visible dialogs and reset confirmation, with no dependency or stored format change.

## Requirement coverage

| Behavior | Requirement | Design |
| --- | --- | --- |
| One action dialog opens from the list and starts clean | REQ-UX-66a271a7 | Native dialog, shared password pair, dismissal |
| Reset is for the selected account and needs matching confirmation | REQ-FUNC-f470a75b | Scoped reset form and existing endpoint |



## Design

### Approach
Use the Users list as the starting point. A native dialog hosts the existing Add user wizard or the account-specific reset form. Both use shared NewPasswordFields and matching validation. Keep the existing access review and reset endpoint.

### Interfaces and data
The dialog binds reset to the selected account, displays the account name and session effects, and closes on success or dismissal when idle. Each mount starts a clean draft. Confirmations stay in browser form memory and do not enter API requests. Server errors remain in the reset dialog and malformed success fails closed.

### Files and test seams
App, UserCreation, PasswordField, locale strings and dialog styling. Browser scenarios cover list entry, close/reopen, mismatch, failure, scoped success, narrow width and creation regression.

### Risks and open decisions
Focus returns on dismissal. Duplicate submits and dismissal are blocked during writes. Navigation or session change discards the dialog draft.

### Requirement map
REQ-UX-66a271a7 maps to the common dialog and pair. REQ-FUNC-f470a75b maps to the scoped reset handler and request verification.

Diagrams: [diagram_TASK-919afe4e.md](diagram_TASK-919afe4e.md)



## Log

- 2026-11-09 frame: journal opened
- 2026-11-09 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-09 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-09 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-09 build: red: Users opens a single fresh dialog exit 1; Add user button absent in baseline.
- 2026-11-09 build: release-notes: updated (Users dialogs and reset confirmation)
- 2026-11-09 build: help: updated (Users entry points and reset steps in four locales)
- 2026-11-09 build: green: Users and passwordChange Chromium 17 passed (modal, scoped actual reset fixture, rejection, duplicate guard and four locales), help 11, production and e2e builds passed
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: Review round 1: prove populated reset draft disposal; keep complete Unicode reset password and defer reset length bounds to existing server validation.
- 2026-11-09 validate: returned to build - Cover reset cancellation and preserve existing Unicode input contract
- 2026-11-09 build: Review fixes verified: reset discards populated draft and sends all Unicode characters, six targeted Chromium passed and both builds exit 0.
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: DEVIATION validate: full strict run omitted under established targeted offline scope; final proof covers Users dialogs and reset.
- 2026-11-09 validate: final: 2 serial Chromium Users dialog cases and 11 help checks passed. Production and E2E builds, release consistency, release notes and diff check passed. Static AEGIS WARN: zero errors, 57 warnings, 24 notes, no finding for this task or its requirements. Manual local URL serves final bundle and is ready.
- 2026-11-09 validate: completed; next done (1 Done checklist item(s) left unticked)

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-919afe4e.md
changed: Users list and shared credential dialog with localized guidance
evidence: Final Chromium 2, help 11, builds and release checks passed; static check WARN
issues: Full strict run omitted under targeted scope; static check has 57 repository warnings and zero errors
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-09)

- stage: validate; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-66a271a7 - Open Add user and Reset password from the user list
  - REQ-FUNC-f470a75b - Confirm an administrator password reset for the selected account
- deviations: 1 recorded
  - validate: full strict run omitted under established targeted offline scope; final proof covers Users dialogs and reset.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base a6b0fc6: 43 file(s) changed, 1430 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=57 notes=24
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
