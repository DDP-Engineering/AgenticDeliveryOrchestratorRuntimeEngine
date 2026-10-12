<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-f2982ae9 - Tidy the user project access lists

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-4b0b0d5f, REQ-UX-79c7e862, REQ-UX-69f84f19
parent:
branch: task/adore-web-interface
base: 5bd4fad29c06a24523c9ef7a56bd09469e886455
opened: 2026-10-12

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: on Administration > Users the expanded Assigned projects list is messy - every checkbox sits above its label (global label column layout), each project shows its 32-hex identifier, and the list opens in the middle of the account row between the name and the buttons (STATED: "cand expandez assigned projects - proiectele listate nu sunt formatate ok. Interfata pare messy").
Desired outcome: one compact row per project (checkbox + name, disambiguated by the unique name when display names repeat) in columns, the editor full-width below the account row; reviews and results keep the immutable IDs (spec REQ-FUNC-97bcc67f).
Actors: administrators.
Primary scenario: Users -> developer row -> Assigned projects -> grid of named checkboxes under the row -> Save -> before/after review with names.
Examples: DCP screenshot with six projects and identifiers.
Counterexamples: review/apply/correction flows and grant semantics unchanged (REQ-UX-69f84f19, REQ-UX-79c7e862); names are still mapped to the server by the same logic.
In scope: UserCreation.tsx choice markup and labels, styles, e2e, requirement.
Out of scope: APIs; full suite (STATED: at the end).
Constraints: spec REQ-FUNC-97bcc67f requires review to show display plus immutable ID; display names may repeat, project names are unique.
Success signals: e2e alignment/placement/no-id checks; DCP shows the tidy list.
Evidence: OBSERVED UserCreation.tsx labels() "name · id", choices `name · <code>id</code>`; styles.css global `label { flex-direction: column }`; `.user-row` flex places the details between name and buttons.
Assumptions: none. Unknowns: none. Decision-blocking questions: none.
Proposed behaviors: B1 compact named choice rows in columns; B2 full-width editor below the row; B3 reviews/results keep display plus ID (REQ-UX-4b0b0d5f).
Path and reason: full - observable UI change with a new requirement.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| tidy list | B1-B3 | REQ-UX-4b0b0d5f (new) | aligned rows, editor below, names only | narrow screens keep one column | e2e users.spec | D1-D2 |

## Design

- D1 UserCreation: choices render `div.access-choices` of `label.access-choice` (checkbox + `choiceName`: display name, plus the unique name on collision); `labels()` keeps `name · id` for reviews/results; creation fieldset uses the same markup.
- D2 CSS: `.access-choices` auto-fill grid (min 200px), `.access-choice` row layout (overrides the global column label); `.user-row > .membership-editor` takes the full row below (order last, flex-basis 100%, indented under the name).
- D3 (RULING-001) each choice shows a muted `forge · repository` line under the name (`platform` and `repo` from the project list); reviews/results read `name (forge repository) · id`.
- Test seams: e2e/users.spec.ts new layout test and the creation review assertion (names, no identifier).

## Log

- 2026-10-12 frame: scope accepted from the user request (tidy Assigned projects list); autopilot; full path; full suite deferred by user.
- 2026-10-12 specify: 1 created (REQ-UX-4b0b0d5f); 0 revised; 0 retired.
- 2026-10-12 design: see ## Design D1-D2.
- 2026-10-12 build red: REQ-UX-4b0b0d5f command=`npx playwright test e2e/users.spec.ts -g "aligned named rows|commits exact stable grants"` exit=1 (2 failed); expected missing behavior=checkbox above label, editor between name and buttons, identifiers in choices and review.
- 2026-10-12 build green: `npx tsc -b` clean; e2e users+settings 37 passed (REQ-UX-4b0b0d5f, REQ-UX-79c7e862, REQ-UX-69f84f19). access-choices grid of access-choice rows, names only in labels(), editor full width below the row; docs/CHANGELOG updated.
- 2026-10-12 validate review round 1: spec-compliance FAIL - spec REQ-FUNC-97bcc67f requires the review to show display plus immutable ID, and display names may repeat -> reviews/results keep `name · id`, choices use choiceName (display name, unique name added on collision), requirement/docs/CHANGELOG/Frame/Design aligned, creation test again expects the ID in the review; implementation-quality - duplicate-name ambiguity and React keys by label (fixed: keys by id), dead .membership-editor form/label and .user-access code CSS (removed), checkbox min-height reset and spacing for the no-projects choice.
- 2026-10-12 validate review round 2: spec-compliance PASS; implementation-quality - the no-projects spacing rule lost to the access-choice margin reset (specificity) -> selector raised to `.user-access .access-choices + label.access-choice`; e2e users 11 passed.
- 2026-10-12 validate review round 3: implementation-quality PASS; spec-compliance PASS from round 2 stands (the later edit only raised one CSS selector's specificity).
- 2026-10-12 validate final: `python .agentic/aegis.py check --task TASK-f2982ae9 --strict` errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by tsc and e2e users+settings 37 then users 11 after the fixes. Frontend deployed to DCP (assets 200).
- 2026-10-12 build reopened: user asked to add forge and repository path beside project names (RULING-001, D3); REQ-UX-4b0b0d5f revised.
- 2026-10-12 build red (round 2): REQ-UX-4b0b0d5f command=`npx playwright test e2e/users.spec.ts -g "aligned named rows|commits exact stable grants"` exit=1 (2 failed); expected missing behavior=no forge/repository line in choices and no repository in the review.
- 2026-10-12 build green (round 2): `npx tsc -b` + e2e typecheck clean; e2e users+settings 37 passed (REQ-UX-4b0b0d5f). ChoiceText with a muted access-repo line (platform · repo); labels() name (forge repository) · id; docs/CHANGELOG updated.
- 2026-10-12 validate review round 4: spec-compliance PASS; implementation-quality PASS (one optional nit left: repository() computed twice in ChoiceText).
- 2026-10-12 validate final (round 2 request): `python .agentic/aegis.py check --task TASK-f2982ae9 --strict` errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by tsc (src + e2e) and e2e users+settings 37. Frontend deployed to DCP (assets 200).
- 2026-10-12 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-12 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings

- RULING-001 | date=2026-10-12 | decision=Show each project's forge and repository path beside its name in the access choices and in reviews/results | reason=User after DCP test: a bare project name next to a user is not representative or safe for an administrator; add path and forge, e.g. gitea / dpasare/2026_Networked_Intelligent_Lab_Orchestrator | source=user | supersedes=none

## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-f2982ae9.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Users project access: Assigned projects opens full width below the account; each project is one checkbox row with its name and a forge · repository line, in columns (unique name added when display names repeat); creation choices use the same rows; reviews and results show name (forge · repository) · stable ID
evidence: tsc clean; e2e users+settings 37; review round 4 PASS/PASS; deployed to DCP
issues: DEVIATION full suite deferred by user; forge host link not shown (not in the project list)
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 4

## Delivery report (2026-10-12)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-4b0b0d5f - Show user project access choices as compact named rows
  - REQ-UX-79c7e862 - Review account identity and explicit access before creation
  - REQ-UX-69f84f19 - Review access edits with before after and applied result
- deviations: 2 recorded
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by tsc and e2e users+settings 37 then users 11 after the fixes. Frontend deployed to DCP (assets 200).
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by tsc (src + e2e) and e2e users+settings 37. Frontend deployed to DCP (assets 200).
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=4
- diff vs task base 5bd4fad: 9 file(s) changed, 194 line(s) added
- checks: errors=0 warnings=11 notes=22
- checklist: 6/6 done
