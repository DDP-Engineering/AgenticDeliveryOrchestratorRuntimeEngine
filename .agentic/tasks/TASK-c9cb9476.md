<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-c9cb9476 - Indicate unchanged default administrator credentials

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-8136f3ae, REQ-FUNC-fcf29613, REQ-UX-178abcf8
parent:
branch: task/adore-web-interface
base: 4ec497fce2822f6b7a9f998771c220153e5265f6
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

Problem: STATED #40: new installation creates admin/admin without visible sign-in guidance or persistent change reminder.
Desired outcome: STATED show first-start indication and persistent reminder with existing password-change route while factory password remains.
Actors: STATED operator and initial administrator.
Primary scenario: STATED new store, sign in, follow reminder, change password.
Examples: OBSERVED store.py bootstraps admin/admin; passwords through create/reset/change require eight characters.
Counterexamples: STATED customized and reset accounts must not be characterized as new installations.
In scope: STATED localized indication, reminder, tests, documentation and production bundle.
Out of scope: STATED migration, password resets, real data, remote writes and unrelated work.
Constraints: STATED same branch, no push, offline targeted proof, maximum 35 files, 4 hours and 2 review rounds; user authorizes autopilot and commit.
Success signals: STATED initial credentials visible only while unchanged; reminder and path disappear on change; existing reset behavior remains.
Evidence: OBSERVED tea issues 40; store.py bootstrap and password validation; current branch and base verified.
Assumptions: INFERRED validation forbidding short non-bootstrap passwords permits identifying factory password through verification, without stored schema change.
Unknowns: UNKNOWN browser timing and corruption behavior until inspected.
Decision-blocking questions: None.
Proposed behaviors: Accepted as stated above.
Path and reason:
| Criterion | Holds? | Evidence |
| --- | --- | --- |
| no new externally observable behavior | no | STATED new reminder |
| no new interface or data format | no | INFERRED status needed |
| no new dependency | yes | OBSERVED existing password verifier |
| existing requirement covers behavior | no | OBSERVED existing account requirements omit reminder |
| no security or data-handling change | no | INFERRED credential state presentation |
Full path; no independently scoped child tasks.

## Requirement coverage

| Behavior | Requirement | Design |
| --- | --- | --- |
| Session status from current credentials | REQ-FUNC-8136f3ae | Verify factory password for own identity |
| New store console notice | REQ-FUNC-fcf29613 | Announce after committed initialization |
| Persistent localized reminder and route | REQ-UX-178abcf8 | Shell banner to My account |


## Design

### Approach
REQ-FUNC-fcf29613: announce public factory credentials only after new-store creation. REQ-FUNC-8136f3ae: determine own factory-password status from the current admin record by verifying the public factory password; supported password changes and resets require at least eight characters. REQ-UX-178abcf8: show a persistent shell reminder linking to the existing My account form.

### Interfaces and data
Session and me return only a boolean for the authenticated account, derived from the current record; corrupt hash is refused. No schema or parallel policy. Session refresh and successful password change use existing behavior.

### Files and test seams
Store initialization and authenticated API/session projection; App shell and translations; isolated API and browser tests, operator and component docs, four help locales and bundle.

### Risks and open decisions
Concurrent sessions may retain a stale presentation until refreshed; a bounded refresh must update it without reviving a stale session. No stored format changes or other account details exposed.

### Requirement map
REQ-FUNC-fcf29613: isolated bootstrap output. REQ-FUNC-8136f3ae: API status and corruption test. REQ-UX-178abcf8: localized shell and navigation browser proof.

Diagrams: [diagram_TASK-c9cb9476.md](diagram_TASK-c9cb9476.md)


## Log

- 2026-11-09 frame: journal opened
- 2026-11-09 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-09 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-09 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-09 build: red: pytest tests/test_web_auth.py::test_factory_admin_status_and_first_boot_notice exit 1 - bootstrap notice absent (REQ-FUNC-fcf29613, REQ-FUNC-8136f3ae)
- 2026-11-09 build: green: pytest targeted factory, account and reset tests exit 0 (4 passed; REQ-FUNC-8136f3ae, REQ-FUNC-fcf29613)
- 2026-11-09 build: release-notes: added (factory password reminder is user visible)
- 2026-11-09 build: help: updated (account password guidance in all four locales)
- 2026-11-09 build: DEVIATION build: UI browser test was added after implementation rather than red first - API bootstrap test supplied the initial red; targeted browser proof passed.
- 2026-11-09 build: release-notes: updated (merged interface fix with initial password reminder within category limit)
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: Review round 1: bind notice to actual bootstrap transaction; isolate browser password mutation; test delayed session response after logout and refresh after change.
- 2026-11-09 validate: returned to build - Address both independent review findings
- 2026-11-09 build: Review fixes: actual bootstrap flag, isolated browser transition, stale-response guard coverage; targeted pytest 4 passed across two runs and Chromium 2 passed.
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: DEVIATION validate: strict --run and full suites omitted as explicitly instructed; targeted offline API, browser, static checks and release consistency do not prove unrelated behavior or live acceptance.
- 2026-11-09 validate: final: targeted pytest 6 passed; Chromium factoryPassword.spec.ts 2 passed (one worker, 390px/four locales; UI success mocked, real change covered by API); help 11 passed; Ruff, release notes, git diff --check exit 0; static check exit 0 WARN (45 unrelated repository warnings, 24 manual notes); release consistency exit 0. No strict --run or full suite per user.
- 2026-11-09 validate: completed; next done (1 Done checklist item(s) left unticked)

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-c9cb9476.md
changed: Design and diagram_TASK-c9cb9476.md
evidence: targeted pytest 6, Chromium 2, help 11, Ruff, release notes and release consistency exit 0; static check WARN
issues: Full strict run omitted by user; 45 unrelated static warnings; browser change response mocked with actual flow covered in API tests
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-09)

- stage: validate; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-8136f3ae - Indicate unchanged factory administrator credentials
  - REQ-FUNC-fcf29613 - Announce initial account at bootstrap
  - REQ-UX-178abcf8 - Remind initial administrator to change password
- deviations: 2 recorded
  - build: UI browser test was added after implementation rather than red first - API bootstrap test supplied the initial red; targeted browser proof passed.
  - validate: strict --run and full suites omitted as explicitly instructed; targeted offline API, browser, static checks and release consistency do not prove unrelated behavior or live acceptance.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 4ec497f: 30 file(s) changed, 579 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=45 notes=24
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
