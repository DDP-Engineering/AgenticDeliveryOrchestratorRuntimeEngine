<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-5a699c9f - Refresh project History automatically and remove its Refresh buttons

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-d64b7511, REQ-UX-183b80f6, REQ-UX-3184cc48
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
- [x] final focused proof and deviation logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem: STATED The project History screenshot shows Refresh in the header and in Change evidence.
Desired outcome: STATED Remove the manual Refresh control from project History if straightforward.
Actors: OBSERVED Users with access to the project History tab.
Primary scenario: INFERRED While viewing project History, change evidence refreshes as in global Change history.
Examples: INFERRED New scoped evidence appears without using a Refresh button.
Counterexamples: INFERRED Refreshing must not clear filters or reveal evidence from another project.
In scope: INFERRED The two controls shown in the screenshot and the existing visible audit polling for project History.
Out of scope: OBSERVED Users and the separate global Change history panel have their own controls.
Constraints: OBSERVED Repository AEGIS with autopilot and current branch. STATED Prefer a small change. Bound work to 30 minutes, 25 paths and two review rounds. Focused offline proof.
Success signals: INFERRED The project history view updates every 15 seconds while visible and neither pictured button appears.
Evidence: OBSERVED App.tsx manualRefresh and scoped AuditHistory call, AuditHistory.tsx visibility polling and project validation.
Assumptions: INFERRED Both buttons in the pictured History view are the intended scope.
Unknowns: None material.
Decision-blocking questions: None.
Proposed behaviors: INFERRED Reuse the existing update cycle, scope, filtering and failure display.
Path and reason: Full because the view's refresh behavior changes.

| Criterion | Holds | Evidence |
| --- | --- | --- |
| no new externally observable behavior | no | History updates without manual action |
| no new interface or data format | yes | Existing API and controls |
| no new dependency | yes | Reuse visibility polling |
| an existing requirement already covers the behavior | no | Prior polling requirement is global only |
| no security or data-handling change | yes | Keep project checks and read-only access |

## Requirement coverage

| Behavior | Requirement | Verification |
| --- | --- | --- |
| Automatic scoped evidence with existing validation | REQ-UX-d64b7511 | Chromium advances the timer, preserves the filter and expanded evidence, rejects out-of-scope rows |
| Header Refresh on Users | REQ-UX-183b80f6 | Chromium checks Users and automatic pages |
| Manual audit Refresh on global view | REQ-UX-3184cc48 | Chromium exercises the global fallback and verifies no button in project History |

## Design

### Approach

Always run the existing visibility-aware timer in AuditHistory (REQ-UX-d64b7511). Use the existing fixed project identity to decide whether the panel has a manual Refresh (REQ-UX-3184cc48). Render the shell's manual control only on Users (REQ-UX-183b80f6).

### Interfaces and data

Keep the existing query, project scope checks, filter, page and open evidence state. A 10-second deadline bounds each read. Failures withhold rows and the timer retries. No endpoint or stored data change.

### Files and test seams

App.tsx and AuditHistory.tsx, with focused Chromium tests in audit.spec.ts and shell.spec.ts. Update help, release notes, user and component documentation and bundle.

### Risks and open decisions

Reuse the existing response scope and cleanup guards. The shared audit panel is still responsible for validating every scoped response.

### Requirement map

The timer and scoped response assertions prove REQ-UX-d64b7511. Panel control assertions prove REQ-UX-3184cc48. Shell control assertions prove REQ-UX-183b80f6.

Diagrams: [diagram_TASK-5a699c9f.md](diagram_TASK-5a699c9f.md)

## Log

- 2026-11-09 frame: journal opened
- 2026-11-09 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-09 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-09 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-09 build: red: focused Chromium shell test exit 1: History still has header Refresh; scoped audit test exit 1: a 15-second tick did not load the changed row. The existing panel also rendered its manual Refresh.
- 2026-11-09 build: green: npm run build and build:e2e exit 0; 4 targeted Chromium audit and shell tests exit 0. Node help/polling tests (15), release notes and git diff --check passed.
- 2026-11-09 build: release-notes: updated (both history views refresh automatically).
- 2026-11-09 build: help: updated (interface and administration in all four locales).
- 2026-11-09 build: Build check: no errors. Advisory findings are repository-wide legacy journal/path references, configured source classification of E2E tests and the size-limited scan of the generated JS. The 20-path evolution excludes earlier local changes.
- 2026-11-09 build: completed; next validate
- 2026-11-09 validate: Inspection: reviewed the 20-path evolution against the task. Live local ADORE returned HTTP 200 for the page and the newly built JavaScript. Direct bundle inspection found no private-key, AWS or OpenAI key patterns. Verified the help describes the two history views and limits the manual audit control to global Change history.
- 2026-11-09 validate: Review 1: a hung audit fetch can block later automatic retries after removing the manual control. Give the request a finite deadline and cancel on scope changes.
- 2026-11-09 validate: returned to build - Bound audit read time to preserve automatic recovery.
- 2026-11-09 build: Review fix red: stalled audit read regression exited 1 because the view never entered its recoverable error state.
- 2026-11-09 build: Review fix green: npm run build and build:e2e exit 0. Six Chromium History and shell regressions exit 0 including a stalled read followed by automatic retry, and Dev project scope.
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: DEVIATION validate: focused Chromium and help/polling tests replace the full project suites per the user's standing preference.
- 2026-11-09 validate: final: strict static check, release notes, git diff --check, 15 help/polling and 6 targeted Chromium tests exit 0. Static 0 errors, 69 advisory warnings. Repo-wide references, E2E path classification and generated JS scan limit are recorded.
- 2026-11-09 validate: completed; next done

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-5a699c9f.md
changed: Both History Refresh controls removed; scoped automatic reads retry after failure or timeout
evidence: 6 focused Chromium, 15 help/polling tests, strict static and release-note checks exit 0
issues: Targeted validation; advisory warnings recorded.
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-09)

- stage: validate; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-d64b7511 - Refresh change history while visible
  - REQ-UX-183b80f6 - Show header Refresh on Administration Users
  - REQ-UX-3184cc48 - Keep the Change evidence Refresh control on the global view
- deviations: 1 recorded
  - validate: focused Chromium and help/polling tests replace the full project suites per the user's standing preference.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base bb3141c: 63 file(s) changed, 1434 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=69 notes=24
- checklist: 8/9 done; open: `report` appended
