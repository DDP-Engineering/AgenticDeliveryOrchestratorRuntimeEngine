# TASK-e3102c4d - Save project settings together with impact confirmation and full-width rows

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-7ed447e2, REQ-FUNC-19b7d492, REQ-REL-006d6813, REQ-REL-b4e596fc, REQ-UX-84025a2c, REQ-UX-1f5bc86b, REQ-UX-d05fdf6d, REQ-UX-8cc03dd0, REQ-UX-34ca5d39
parent:
branch: task/adore-web-interface
base: 834d292272bd407ff59f77015ff627a171a75801
opened: 2026-11-04

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
- [x] final `check --strict --run` result logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

Problem: STATED the project settings flow is complicated and wastes the right-hand screen area. OBSERVED the supplied pending-configuration screenshot repeats a comparison and exposes prepare/apply technical details; the supplied Tickets screenshot leaves the controls near the middle of a wide row.
Desired outcome: STATED one Save for all changed project settings, enabled after edits, with a short notification/confirmation for important effects. STATED labels and descriptions on the left, values and controls on the right using available width.
Actors: administrator editing a project; developers retain scoped read-only access.
Primary scenario: edit several settings in different groups, click Save once, confirm important effects when present, and observe all accepted values saved together.
Examples: STATED system-package permission false to true warrants a clear effect notice; ticket interval remains readable in a full-width two-column row.
Counterexamples: stale configuration, invalid values or busy runtime must not produce a partial save or lose the user's drafts; unchanged values do not enable Save.
In scope: project Settings draft/edit/save flow, batch-safe configuration candidate validation, concise impact confirmation, recovery and responsive row layout; four-locale copy/help and related component docs/tests.
Out of scope: STATED no push and the running application remains for the user's own testing. Repository rules keep secrets, installation paths and forge publication at their existing ownership boundaries. No changes to enrollment, credential/password flows or executor implementation are needed for this request.
Constraints: STATED autopilot=true persists. Keep current branch and no push. Preserve Admin/CSRF, exact-revision checks, active-work/monitoring gates and fail-closed corrupt-state behavior. No stored-format migrations. Bound work to 5 hours, 140 files, 6 review rounds and offline test suites plus read-only visual verification; do not restart the user's current instance.
Success signals: one visible Save for the settings draft, disabled while unchanged; editing multiple fields remains possible; complete validated save with no partial publication; concise important-effect confirmation; broad desktop columns and narrow-screen stacking without overflow.
Evidence: OBSERVED App.tsx SettingsList/PendingReview and stageSetting/applyPendingConfig, web/app.py config pending/apply routes, styles.css setting-row rules; two user-provided screenshots were opened and inspected. Product Design preflight found no saved context.
Assumptions: INFERRED one Save means one project-scoped draft spanning editable setting categories. Existing backend governance is retained behind the simpler interface. The current visual design/components remain the target.
Unknowns: exact implementation seam for validating multiple interdependent edits and retaining retry evidence will be resolved from existing code in design. Screenshot evidence alone does not establish keyboard/accessibility compliance.
Decision-blocking questions: none; user explicitly selected one Save for all modifications and requested the two-column layout.
Proposed behaviors: none pending.
Path and reason:
| Criterion | Holds | Evidence |
| --- | --- | --- |
| no new externally observable behavior | no | one multi-setting Save replaces the prepare/apply UI |
| no new interface or data format | no | batch edits need an explicit validated contract |
| no new dependency | yes | existing React/Python components suffice |
| an existing requirement fully covers behavior | no | existing single-candidate review requirements need deliberate revision |
| no security/data-handling change | no | preserve review and atomic publication through a changed editing flow |
Full path selected; one coherent task.

## Requirement coverage

| Behavior | Requirement | Design | Proof |
| --- | --- | --- | --- |
| Preview important changes without a stored draft | REQ-FUNC-7ed447e2 | shared canonical preview | API no-write and Chromium cancel tests |
| Prepare one validated batch of project setting edits | REQ-FUNC-19b7d492 | batch candidate and shared Save workspace | API, frontend and browser contract tests |
| Reject malformed or unauthorized batch members without publication | REQ-REL-006d6813 | batch candidate and shared Save workspace | API, frontend and browser contract tests |
| Bind replacement settings drafts to the inspected pending revision | REQ-REL-b4e596fc | batch candidate and shared Save workspace | API, frontend and browser contract tests |
| Save all project setting edits with one action | REQ-UX-84025a2c | batch candidate and shared Save workspace | API, frontend and browser contract tests |
| Confirm important setting effects before saving | REQ-UX-1f5bc86b | batch candidate and shared Save workspace | API, frontend and browser contract tests |
| Retain project setting drafts across failures and guard abandonment | REQ-UX-d05fdf6d | batch candidate and shared Save workspace | API, frontend and browser contract tests |
| Use available width for project settings rows | REQ-UX-8cc03dd0 | batch candidate and shared Save workspace | API, frontend and browser contract tests |
| Compact project settings with raw actions | REQ-UX-34ca5d39 | batch candidate and shared Save workspace | API, frontend and browser contract tests |

## Design

### Approach
Use one multi-row local draft and one Save bar in SettingsList (REQ-UX-84025a2c). Reuse pending/apply internally so validated authority, audit replay and atomic publication stay in one implementation. Important effects use a no-write canonical preview and compact native dialog before preparing any new stored candidate, instead of PendingReview (REQ-UX-1f5bc86b).
### Interfaces and data
A new admin/CSRF POST config/preview uses the same candidate builder as preparation without persisting or replacing pending evidence. On confirmation, preparation must return the previewed candidate hash and execution plan before exact apply; cancellation creates no new server draft (REQ-FUNC-7ed447e2).
Add reserved settings.batch to the current candidate edit vocabulary: a bounded JSON array of unique editable key/wire-value pairs. A small settings_batch.py parses structure and overlapping targets; app.py retains actual edit authority and final TOML validation (REQ-FUNC-19b7d492, REQ-REL-006d6813).
The pending schema stays 1 with existing fields. Read/public/audit meaning checks support one safe typed mapping for a batch and recompute complete candidate meaning. Restart authority is the union of member keys. Optional pending_revision on preparation binds an intentional candidate replacement; missing/stale hashes preserve prior evidence (REQ-REL-b4e596fc).
React settingsSave.ts owns canonical draft normalization, meaningful comparisons and important-effect classification. SettingsList keeps raw drafts across editors and passes a normalized batch on Save. App coordinates preparation, optional confirmation and exact apply; success clears drafts, failure preserves them. A revision change never silently rebases dirty edits, and the existing navigation guard covers explicit abandonment (REQ-UX-d05fdf6d).
Desktop rows put descriptions left and a stretched value/control area right, with actions aligned to the far edge; editors retain full column width. Narrow rows stack. Groups retain category order and disclosure behavior (REQ-UX-8cc03dd0). Raw configuration actions remain available (REQ-UX-34ca5d39).
### Files and test seams
Backend: web/settings_batch.py, web/app.py; public API tests in tests/test_web_settings_batch.py plus existing config/pending/typed/connection suites.
Frontend: App.tsx, settings.ts, settingsSave.ts, styles.css and localized copy; public helper Node tests and revised Settings/executor/dashboard Chromium journeys. Avoid modifying setup scripts or the running test home's configuration.
Docs: settings/executors/help topics in four locales, Web_Interface.md, Configuration_Reference.md where relevant and Web_API/Web_Frontend component docs, knowledge and release notes.
### Risks and open decisions
Keep secret/path/role boundaries and full atomic replacement. Reject partial batch or cross-key collateral changes, stale active/pending revisions and invalid runtime plans. Existing active-work, conductor lock and pause guards stay authoritative. No stored-data migration or compatibility adapter. The current user's service stays running; verification uses isolated offline fixtures. Review refinement: pending records with API-only/hidden keys use read-only exact-candidate confirmation/apply after a fresh bound GET, while ordinary recovered edits use batch replacement. The replacement boundary validates the previous complete candidate against active bytes before writing.
### Requirement map
REQ-FUNC-7ed447e2: shared pure preview before important-change confirmation, bound recheck after preparation.
REQ-FUNC-19b7d492: final-document batch validation and shared atomic apply.
REQ-REL-006d6813: closed parser and per-member authority/type checks before writes.
REQ-REL-b4e596fc: exact pending revision replacement under the config lock.
REQ-UX-84025a2c: one dirty-aware Save, no permanent preparation panel.
REQ-UX-1f5bc86b: exact important-change dialog; ordinary saves apply directly.
REQ-UX-d05fdf6d: scoped drafts, retry preservation and abandonment guard.
REQ-UX-8cc03dd0: full-width right controls and responsive stacking.
REQ-UX-34ca5d39: preserve raw actions while removing duplicate technical review.
Diagrams: [diagram_TASK-e3102c4d.md](diagram_TASK-e3102c4d.md)

## Log

- 2026-11-04 frame: journal opened
- 2026-11-04 frame: completed; next specify - User selected one Save for all edits and requested full-width two-column rows; recorded in autopilot (7 Done checklist item(s) left unticked)
- 2026-11-04 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-04 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-04 build: red: focused batch API pytest exit 1, two cases return setting_not_editable because no multi-setting candidate exists (REQ-FUNC-19b7d492, REQ-REL-b4e596fc)
- 2026-11-04 build: red trust boundary: direct batch PUT test reproduces an unhandled parser failure because direct writes lack the batch candidate guard; retain 409 pending_config_required for this new vocabulary
- 2026-11-04 build: red frontend: Node settings Save protocol test rejects a valid bound batch because validPendingConfig supports only single-setting values (REQ-UX-84025a2c)
- 2026-11-04 build: green backend: 83 batch/existing pending API cases passed; valid final combined edits, bound replacement, malformed-member refusal and atomic apply verified offline. Additional direct-write boundary test reproduced the missing candidate-only guard and is corrected. red GUI: focused Chromium Save journey fails because no global settings Save bar exists.
- 2026-11-04 build: green frontend increment: 30 Node contracts and two Chromium ordinary/important multi-setting Save journeys passed. Design refinement: cancellation should not leave a newly prepared server draft; add a read-only canonical preview before confirmation and stage only after acceptance, retaining existing pending recovery.
- 2026-11-04 build: returned to specify - Important-change cancellation needs a no-write canonical preview before preparation
- 2026-11-04 specify: DEVIATION design: add a no-write canonical preview before important-change confirmation - cancellation must not create a stored draft; one extra route and shared candidate builder preserve exact plan/hash authority without a new stored format
- 2026-11-04 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-04 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-04 build: red preview: important-change Chromium cancellation leaves a stored pending record; public preview API tests require no-write behavior and the route is absent (REQ-FUNC-7ed447e2)
- 2026-11-04 build: release-notes: added (one Save, important-effect confirmation and full-width Settings rows in four locales)
- 2026-11-04 build: help: updated (Settings editing and executor/network/package workflows in en/fr/de/ro; help parity/link tests exit 0)
- 2026-11-04 build: release-notes: updated (merged the existing Settings note to retain the ten-entry limit; checker exit 0)
- 2026-11-04 build: red: Chromium dirty settings navigation test exit 1 - project tab selection bypasses the abandonment guard (REQ-UX-d05fdf6d)
- 2026-11-04 build: Release-note checker correction: the first merged French note still exceeded 100 characters; shortened it and reran the checker successfully (exit 0). Earlier exit-0 wording was premature.
- 2026-11-04 build: red: recovered pending Chromium test exit 1 - recovered batch values are not visible in editors; corrupt pending recovery also exposes a second discard control rather than the single draft bar (REQ-UX-84025a2c, REQ-UX-d05fdf6d)
- 2026-11-04 build: red recovery: corrupt pending transport with no server record cannot clear via Discard (server confirms pending_config_not_found); acknowledge that explicit absence without treating other errors as success
- 2026-11-04 build: green: focused API config/batch/pending/executor suites exit 0 (151 passed); Ruff exit 0; Node settings/save/help exit 0 (40 passed). Chromium ordinary/multi Save, recovered values, corrupt-preview refusal, dirty tab/Refresh guards and stale/corrupt discard now pass; existing focused journeys continue.
- 2026-11-04 build: Build evolution reviewed: 29 product/test/documentation paths implement the planned settings batch/preview, Save/draft UI, full-width rows and four-locale help/release notes; no runtime/enrollment/setup scripts or user home modified. Advisory check returns 0 errors and the same 33 pre-existing stale-reference/journal warnings; unrelated records remain out of scope.
- 2026-11-04 build: completed; next validate
- 2026-11-04 validate: green: focused Chromium settings-save/settings/executor-config/system-packages/dashboard exit 0; all 65 journeys passed, including recovery, important Cancel without pending writes, stale failure, two-column/mobile geometry, typed controls and four locales.
- 2026-11-04 validate: Review round1 findings: (1) bound replacement must check previous complete meaning against active bytes and preserve corrupt evidence; (2) exact Save recovery must support valid API-only scalar candidates without making technical rows editable. Visual inspection additionally shows the Settings heading squeezed beside raw actions at390px; fix header stacking and prove geometry.
- 2026-11-04 validate: returned to build - Fix the two independent review recovery findings and observed mobile header squeezing
- 2026-11-04 build: red review-fix round1: API collateral replacement returns200 instead of503; API-only scalar browser recovery exposes unusable controls/disabled Save; mobile heading width50px instead of readable150px; corrupt-active bound replacement raises untyped UnicodeDecodeError. Tests reproduce review and visual findings before their fixes.
- 2026-11-04 build: green review-fix round1: focused batch API27 passed and Ruff exit0; Chromium API-only candidate saved/stale/corrupt and mobile header4 passed. Ordinary/recovered/dirty/mismatched-preview/stale flows also passed in the preceding targeted run. Mobile title uses its natural121px single-line width, with actions below it (initial150px test threshold corrected; original squeezed50px still fails).
- 2026-11-04 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-04 validate: Review round2: spec approved; quality found browser Back during read-only exact-candidate confirmation can leave an unresolved mutation because dirty=false. Guard the complete saving interval and prove Back/Cancel/retry without an apply.
- 2026-11-04 validate: returned to build - Guard browser navigation during exact-candidate Save confirmation and prove retry
- 2026-11-04 build: red round2: exact-recovery Chromium Back regression exit1 - Back leaves Settings while its confirmation is unresolved; no apply was sent.
- 2026-11-04 build: Manual visual verification: CUA on isolated offline localhost18765 confirmed full-width Tickets rows with descriptions left/values+Edit at the far right on desktop;390px screenshot confirms stacked readable Settings heading/raw actions and one Save bar. Temporary viewport reset; user's18769 service untouched. Captures retained in OS temp adore-settings-visual-AJR6eU.
- 2026-11-04 build: green round2 fix: Chromium settings-save suite exit0, all9 journeys passed. Exact API recovery now rejects browser Back during confirmation, sends no apply before a decision, cancels cleanly and can Save again. Typecheck and isolated build exit0.
- 2026-11-04 build: completed; next validate
- 2026-11-04 validate: Validated current candidate scope, all9 requirement contracts/status/paths/test links, source diff, docs/context and desktop/mobile observations. Both independent round3 reviews approved. Advisory warnings remain33 pre-existing stale-reference/journal records; existing Vite large-chunk and Starlette deprecation notices do not affect this behavior. Final proof follows with no further candidate edits.
- 2026-11-04 validate: final: python .agentic/aegis.py check --task TASK-e3102c4d --strict --run exit0; full Python suite passed568.7s, Ruff passed0.1s, npm web validate (Node contracts, typecheck, isolated build and full Chromium suite) passed700.4s. Strict ok, 0 errors; same33 pre-existing repository reference/journal warnings and23 manual notes accepted/out of scope. No candidate edits after proof.
- 2026-11-04 validate: completed; next done

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-e3102c4d.md
changed: One Save for all settings, important-effect confirmation, preserved drafts and full-width responsive rows
evidence: Full strict check exit0: Python, Ruff and complete web validation passed; both reviews approved
issues: 33 pre-existing repository warnings accepted; running test instance unchanged
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-11-04)

- stage: validate; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-7ed447e2 - Preview important setting effects without creating a stored draft
  - REQ-FUNC-19b7d492 - Prepare one validated batch of project setting edits
  - REQ-REL-006d6813 - Reject malformed or unauthorized batch members without publication
  - REQ-REL-b4e596fc - Bind replacement settings drafts to the inspected pending revision
  - REQ-UX-84025a2c - Save all project setting edits with one action
  - REQ-UX-1f5bc86b - Confirm important setting effects before saving
  - REQ-UX-d05fdf6d - Retain project setting drafts across failures and guard abandonment
  - REQ-UX-8cc03dd0 - Use available width for project settings rows
  - REQ-UX-34ca5d39 - Compact project settings with raw actions
- deviations: 1 recorded
  - design: add a no-write canonical preview before important-change confirmation - cancellation must not create a stored draft; one extra route and shared candidate builder preserve exact plan/hash authority without a new stored format
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 834d292: 45 file(s) changed, 1959 line(s) added
- checks: errors=0 warnings=33 notes=23
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended

## Delivery report (2026-11-04)

- stage: validate; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-7ed447e2 - Preview important setting effects without creating a stored draft
  - REQ-FUNC-19b7d492 - Prepare one validated batch of project setting edits
  - REQ-REL-006d6813 - Reject malformed or unauthorized batch members without publication
  - REQ-REL-b4e596fc - Bind replacement settings drafts to the inspected pending revision
  - REQ-UX-84025a2c - Save all project setting edits with one action
  - REQ-UX-1f5bc86b - Confirm important setting effects before saving
  - REQ-UX-d05fdf6d - Retain project setting drafts across failures and guard abandonment
  - REQ-UX-8cc03dd0 - Use available width for project settings rows
  - REQ-UX-34ca5d39 - Compact project settings with raw actions
- deviations: 1 recorded
  - design: add a no-write canonical preview before important-change confirmation - cancellation must not create a stored draft; one extra route and shared candidate builder preserve exact plan/hash authority without a new stored format
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 834d292: 45 file(s) changed, 1979 line(s) added
- checks: errors=0 warnings=33 notes=23
- checklist: 9/9 done
