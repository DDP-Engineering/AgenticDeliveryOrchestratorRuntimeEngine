<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-ebd8ebbd - Keep the ticket number column compact

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-UX-5c5c19cd
parent:
branch: task/adore-web-interface
base: 94b205a6e75863ca069304f1532ee369b6b52678
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

Problem: STATED The first column of the Tickets table is too wide and wastes space.
Desired outcome: STATED Give the ticket number less width and make the saved width available to other columns.
Actors: OBSERVED Any authorized reader of the shared Tickets table.
Primary scenario: STATED Jobs shows tickets across projects on a wide screen.
Examples: OBSERVED The screenshot shows a short ticket number in a column as wide as Project or Title.
Counterexamples: INFERRED A narrow screen or an expanded detail row must remain usable.
In scope: STATED Ticket table column sizing. INFERRED The shared style applies to all scopes.
Out of scope: INFERRED Other tables, workflow controls and installation are outside the visual adjustment.
Constraints: STATED Offline product tests. INFERRED Eight-minute implementation and focused verification budget, no model calls, at most 20 changed files.
Success signals: STATED Number takes a compact share and content columns gain usable width.
Evidence: OBSERVED styles.css uses fixed table layout with width assigned only to Actions. TicketWorkspace uses the same table in both scopes.
Assumptions: INFERRED Use a rem width with a narrower mobile rule, preserve wrapping for unusually long numbers.
Unknowns: UNKNOWN Exact width preference was not specified.
Decision-blocking questions: None.
Proposed behaviors: INFERRED Keep the same table and detail structure with a smaller number track.
Path and reason: Full because the existing requirements cover ticket table roles and details but do not specify a compact number column.

| Criterion | Holds? | Evidence |
| --- | --- | --- |
| No new observable behavior | No | STATED Narrower column |
| No new interface or data format | Yes | OBSERVED CSS sizing only |
| No new dependency | Yes | OBSERVED Existing browser CSS |
| Existing requirement covers behavior | No | OBSERVED No width requirement |
| No security or data-handling change | Yes | INFERRED Style only |

## Requirement coverage

| Requirement | Behavior | Design | Verification |
| --- | --- | --- | --- |
| REQ-UX-5c5c19cd | Compact number column in Tickets | Width on first header of the outer fixed-layout table | Chromium global, scoped and narrow viewport |

## Design

Design note skipped. One CSS rule and its responsive override constrain
the first header of the existing fixed-layout Tickets table. The browser
distributes the space to the remaining flexible columns. Selector scope
excludes the nested Markdown table and full-width detail rows.

## Log

- 2026-11-09 frame: journal opened
- 2026-11-09 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-09 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-09 design: skipped; next build - Single-file CSS sizing change with no new interface, format or dependency.
- 2026-11-09 build: red: npx playwright test tickets.spec.ts -g ticket number column --workers=1 exit 1, first column 186.95 px versus compact limit 90 px
- 2026-11-09 build: green: Chromium ticket number column journey exit 0 in global and project scopes and at 360 px; production web build exit 0.
- 2026-11-09 build: release-notes: updated (existing Tickets entry includes the compact number column)
- 2026-11-09 build: help: updated (Tickets topic in all four locales)
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: DEVIATION validate: use focused Chromium and strict static AEGIS checks because the bounded task does not rerun the repository-wide baseline failures already reproduced on 94b205a.
- 2026-11-09 validate: final: two targeted Chromium tests, 11 help tests, release notes and strict static AEGIS checks exit 0; production web build passed. The existing wide Markdown scrolling test failed identically with the packaged pre-change CSS (12000 px scroll and client width) and candidate CSS.
- 2026-11-09 validate: completed; next done (1 Done checklist item(s) left unticked)

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-ebd8ebbd.md
changed: Compact ticket number column in both scopes
evidence: 2 Chromium and 11 help tests passed; strict static check and web build passed
issues: Focused validation. Existing wide Markdown test fails with both the previous and new styles.
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-11-09)

- stage: validate; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-5c5c19cd - Keep the ticket number column compact
- deviations: 1 recorded
  - validate: use focused Chromium and strict static AEGIS checks because the bounded task does not rerun the repository-wide baseline failures already reproduced on 94b205a.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 94b205a: 44 file(s) changed, 901 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=58 notes=24
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
