<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-20a14bfc - Confirm and reveal passwords in Add user

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-UX-53f09c54, REQ-FUNC-5b20007f
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

Problem: STATED Add user needs repeat password and eye buttons, as shown by the existing My account experience.
Desired outcome: STATED Both Add user password fields are independently revealable and a matching repeat is required.
Actors and example: STATED An administrator enters a new user's credentials on the first Add user step.
Counterexample: INFERRED A mismatch cannot enter role and access or send an account request.
Scope: Add user identity form, shared password UI, targeted browser proof, four-language help, docs and bundle.
Constraints: OBSERVED Existing pending changes are preserved. Existing eight-character minimum, reviewed creation API and transient credential boundaries apply. Bound to 30 paths, 90 minutes and two independent review rounds. Local changes only.
Evidence: OBSERVED UserCreation renders one masked password and immediately advances after native form checks.
Unknowns and decision-blocking questions: None.
Path and reason: Full, new visible behavior and field. No new dependency, server/storage format or existing requirement for confirmation.

## Requirement coverage

| Behavior | Requirement | Design and proof |
| --- | --- | --- |
| Independent reveal and mask | REQ-UX-53f09c54 | Shared field; targeted browser |
| Require matching confirmation | REQ-FUNC-5b20007f | Identity form gate; targeted browser |


## Design

### Approach
Extract the existing password field and eye icon for reuse by Add user and My account (REQ-UX-53f09c54). Check the repeated password in the identity submit handler (REQ-FUNC-5b20007f).

### Interfaces and data
The confirmation lives only in the identity form. Advancing unmounts it; correcting identity requires entering the confirmation again. Original password remains in the existing transient draft. Eye states reset on unmount. The review and API contract are unchanged.

### Files and test seams
PasswordField, UserCreation and App, existing localized labels, users browser tests and regression of both own-password flows.

### Risks and open decisions
React field IDs must be unique. Keep the original password limits and focus the invalid confirmation after mismatch. No open decisions.

### Requirement map
REQ-UX-53f09c54: independent toggles and remasking. REQ-FUNC-5b20007f: mismatch boundary, correction, review secrecy and unchanged payload.


Diagrams: [diagram_TASK-20a14bfc.md](diagram_TASK-20a14bfc.md)

## Log

- 2026-11-09 frame: journal opened
- 2026-11-09 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-09 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-09 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-09 build: red: Playwright Add user password confirmation exit 1; the confirmation field is absent.
- 2026-11-09 build: release-notes: updated (combined Add user and own-password controls in the existing note)
- 2026-11-09 build: help: updated (Add user instructions in all four locales)
- 2026-11-09 build: green: npm run build:e2e and Playwright users/passwordChange 15 passed; help 11 passed and production build exit 0 (REQ-UX-53f09c54, REQ-FUNC-5b20007f)
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: Review round 1: disable browser spelling, correction and capitalization when either credential is revealed.
- 2026-11-09 validate: returned to build - Protect revealed credentials from ordinary text assistance
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: DEVIATION validate: full strict run omitted under established targeted offline scope; final proof covers Add user and shared password controls.
- 2026-11-09 validate: final: serial Chromium two Add user cases passed (including four locales and narrow display); help 11 passed; release consistency, release notes and diff check exit 0. Static AEGIS WARN: 0 errors, 57 warnings, 24 notes; no finding points at this task or its two requirements. Local URL serves rebuilt bundle and is ready.
- 2026-11-09 validate: completed; next done (1 Done checklist item(s) left unticked)

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-20a14bfc.md
changed: Shared eye control, Add user confirmation, localized help and bundled assets
evidence: Two final Chromium scenarios, 11 help checks, production bundle, release checks passed; static check WARN
issues: Full strict run omitted under targeted scope; static check has 57 repository warnings and zero errors
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-09)

- stage: validate; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-53f09c54 - Reveal Add user passwords independently
  - REQ-FUNC-5b20007f - Require matching Add user password confirmation
- deviations: 1 recorded
  - validate: full strict run omitted under established targeted offline scope; final proof covers Add user and shared password controls.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base a6b0fc6: 38 file(s) changed, 905 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=57 notes=24
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
