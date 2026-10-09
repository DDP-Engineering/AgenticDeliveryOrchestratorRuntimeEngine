<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-ba26a6bc - Clarify failed CI action and align integration branch reference

stage: deliver
type: fix
path: quick
interaction: autopilot
requirements: REQ-UX-d8745013
parent:
branch: task/adore-web-interface
base: 67edab628f73374491c35e0000aea2e13b940745
opened: 2026-10-09

## Done checklist (current stage)

- [x] presentation implemented; 18 helper and 4 offline browser journeys passed
- [x] documentation and requirement links reconciled
- [x] anchor/evolution reviewed
- [x] diff and two independent review questions assessed
- [x] final strict catalog: 0 errors, 10 existing warnings, 25 historical notes
- [ ] deployment verified and own backup removed

## Frame

Problem: STATED: failed pipeline wording is technical and the integration branch reference is visually inconsistent.
Desired outcome: clear localized CI action names and the usual responsive label/value row layout.
Actors: authorized Admin and scoped Dev.
Primary scenario: opening PR/MR settings shows the reference and action; Admin reviews edits using the same names.
Examples: master appears under Active value; revise appears as Automatic repair.
Counterexamples: the reference supplies no second editor; wire values remain revise/notify/ignore.
In scope: frontend copy, option/value/review formatting, branch reference markup/style, focused tests and documentation.
Out of scope: pipeline detection, repair limits, config schema, permissions and conductor behavior.
Constraints: targeted tests only per user; existing deployment authorization and preservation rules apply.
Success signals: desktop value columns align; mobile wraps; reference opens and focuses the sole Repository row; exact names survive edit/review.
Evidence: STATED user approval of rename/alignment; OBSERVED App.tsx SettingsList/PendingReview, settingsCopy.ts, styles.css and settings.spec.ts.
Assumptions: use the previously recommended action and option names in all four supported locales.
Unknowns: none blocking.
Decision-blocking questions: none.
Proposed behaviors: presentation-only correction using existing setting-row grid and link navigation.
Path and reason: quick; existing REQ-UX-d8745013 covers presentation. No new behavior/interface/format/dependency or security/data contract.

## Requirement coverage


## Design


## Log

- 2026-10-09 frame: quick path accepted under direct implementation request; continue autonomously under session authorization. Existing branch retained.
- 2026-10-09 build red: node --test --test-name-pattern 'failed CI action' tests/settings.test.mjs; exit=1; expected new localized pipeline action exports are absent.


- 2026-10-09 build/validate: 18 settings helper tests passed; typecheck and isolated Vite build exit=0; four selected settings browser journeys passed (locale, Admin/Dev reference navigation/layout, exact candidate CI names). Screenshot inspected: equal value typography, desktop columns and wrapped mobile rows. Five pipeline conductor tests passed, 102 deselected. Build retains the existing chunk-size advisory.
- 2026-10-09 validate review round 1: specification compliance approved against REQ-UX-d8745013 and user rename/alignment request; implementation quality approved after exact-value negative cases, Admin/Dev navigation and unchanged-revision checks, desktop/mobile geometry, localized values/editor/review inspection and unchanged wire contract. No current-scope findings.
- 2026-10-09 DEVIATION validate: full configured suite is deferred under the user's targeted-only instruction. Substitute is focused helper/browser/conductor tests, TypeScript and isolated build plus strict catalog without --run; broader suite coverage is not asserted.

- 2026-10-09 final validate: strict catalog exit=0 (without --run), errors=0/warnings=10/notes=25; all warnings pre-existing. Diff check clean. Two reviews approved for unchanged source; no dependencies, runtime or authority changes. Proceed with authorized local commit and DCP replacement.

## Rulings

- RULING-001 | date=2026-10-09 | decision=Implement rename/alignment and continue existing local/DCP delivery with targeted tests | reason=Direct user request and standing session authorization | source=user | supersedes=none


## Handoff


current: deliver
status: ready
next: strict catalog and authorized delivery
must_read: .agentic/requirements/ux/REQ-UX-d8745013.toml
blockers: none

## Stage report


stage: validate
result: completed
current: deliver
changed: localized CI action presentation and responsive integration branch reference; docs and tests
evidence: 18 helper, 4 browser and 5 conductor tests pass; typecheck/build pass; screenshot inspected
issues: full suite deferred by user; existing Vite chunk-size advisory
next: local commit and authorized DCP deployment
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-09)

- stage: deliver; type: fix; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-UX-d8745013 - Project settings follow Git delivery flow
- deviations: 1 recorded
  - validate: full configured suite is deferred under the user's targeted-only instruction. Substitute is focused helper/browser/conductor tests, TypeScript and isolated build plus strict catalog without --run; broader suite coverage is not asserted.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 67edab6: 12 file(s) changed, 219 line(s) added
- checks: errors=0 warnings=11 notes=25
- checklist: 5/6 done; open: deployment verified and own backup removed
