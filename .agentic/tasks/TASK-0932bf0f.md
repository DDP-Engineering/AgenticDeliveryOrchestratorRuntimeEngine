<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-0932bf0f - Remove project details header picker and separate metadata actions

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-2c85559e, REQ-UX-7434a8cd
parent:
branch: task/adore-web-interface
base: 2f06df6
opened: 2026-10-01

## Done checklist (current stage)

- [x] Requirements, candidate, manual evidence and docs complete.
- [x] Canonical final proof complete.
- [x] Deploy and verify DCP.
- [x] Delivery close-out commit includes verified candidate; installed revision recorded on DCP.

## Frame

Problem: STATED unwanted top-center project selector and compressed Last activity/action spacing in Project details screenshot.
Desired outcome: Project details has a simple common header and readable separation between metadata and action buttons.
Actors: Administrators and assigned developers.
Primary scenario: Open a project from Projects; see its identity and metadata, then select Jobs, Metrics or Settings for that project.
Examples: Last activity currently touches Jobs button; screenshot's aegis project selector is unwanted.
Counterexamples: Removing selection must not lose selected-project context or page-local Jobs/Metrics scope; narrow wrapping must not overlap metadata/buttons.
In scope: Final header picker removal, project summary metadata container/spacing, current docs/requirements and frontend deployment.
Out of scope: Nilo recovery, configuration/RBAC/backend changes, moving a new selector into details.
Constraints: Selected identity retained; navigate through Projects to open another project; retain compact space-efficient layout and previous readability.
Success signals: No header project selector on any page; project metadata rows visibly separated; at least 16px between Last activity and buttons at desktop/phone widths.
Evidence: STATED screenshot and user request; OBSERVED App.tsx header still renders projectDetails picker and three adjacent metadata divs before button-row; CSS metadata line-height 21px but no action separation.
Assumptions: Existing autonomous implementation/commit/DCP deployment authority applies.
Unknowns: None blocking; screenshot resolves page name as Project details.
Decision-blocking questions: None.
Proposed behaviors: Remove header picker entirely; group metadata with 4px row gaps and 18px bottom margin; preserve scoped buttons.
Path and reason: Full path for changed selector requirement/new spacing outcome; interfaces, dependencies, data and security unchanged. No child tasks needed.

## Requirement coverage

| Outcome | Requirement | Positive case | Boundary | Verification | Design |
|---|---|---|---|---|---|
| Header contains only common controls | REQ-UX-2c85559e revised | Project details has zero header selectors | Jobs/Metrics keep local project scope | Manual DOM/UI inspection | Remove final JSX picker and unused styles |
| Metadata/action separation | REQ-UX-7434a8cd | Last activity has clear gap before actions | Long metadata and wrapped buttons on phones | Manual computed geometry/screenshots | Grid metadata container, 4px row gap, 18px bottom margin |

## Design

Frontend owns presentation only. REQ-UX-2c85559e removes the final conditional header picker and its unused CSS, including mobile override. Project opening remains through authorized Projects rows; selected identity and action callbacks stay intact. REQ-UX-7434a8cd adds a project-metadata wrapper around existing three rows, with 4px grid gap and 18px bottom margin. Existing 14px/21px text and overflow wrapping remain. No dependency, API, persistence, lifecycle, permission or architecture change. Expected files: App.tsx/styles.css, bundled assets, user/component/knowledge docs and changelog. Risk is accidental loss of project context; inspect navigating details to Jobs/Metrics and selecting another project through Projects. Desktop and 390px manual layout checks prove presentation; canonical offline suite remains final proof. Static-only deploy retains prior assets for rollback.

## Log

- 2026-10-01 frame: Scope accepted under standing autonomous instruction; screenshot identifies Project details. Full path selected for explicit navigation/spacing requirement revision; no existing repository/job mutation authorized or needed.
- 2026-10-01 specify/design: Revise header requirement to common-controls-only on every page, add separate spacing requirement. Manual presentation evidence is appropriate; details buttons retain selected identity. Design recorded above; no blocking decisions.

- 2026-10-01 build: Manual presentation requirements; no mirrored CSS tests. Removed final header selector and unused picker styles, grouped metadata with 4px row gap/18px bottom separation. Production build exit 0. Desktop 1920px and phone 390px DOM measure zero header selectors and 18px Last activity/action separation; screenshots inspected, wrapped buttons remain within panel and page scrollWidth 375<=390. Jobs retains guided-qa; opening jobs-qa-second through Projects then Metrics selects jobs-qa-second. Viewport reset, QA tab closed; docs/current requirements/changelog reconciled.

- 2026-10-01 validate: Full journal, revised/new requirements, docs and final source/static diff reviewed; evolution matches scope and whitespace check passes. `check --task TASK-0932bf0f --strict --run` exited 0: offline test 44.7s, lint 0.3s, seven frontend tests 0.2s; zero errors. Seven advisories cover intentionally manual UI verification/no mirrored tests, generated asset coverage/scanning and unrelated pre-existing sidecar/ruling metadata. No material deviation.
- 2026-10-01 deliver: Standing authorization covers frontend commit and deployment; preserve prior static assets for rollback. Archive SHA-256 37db3a0db30f1ac0c7c17b8462a75960af9ddd0660a077b06f4078dd3ddf7447. No live project/run mutation is required.

- 2026-10-01 deliver: DCP archive hash verified and frontend installed; rollback retained as static.pre-project-summary-20261001. UI, CSS/JS and health/readiness HTTP 200; API/worker active. Live aegis details confirms zero header selectors and 18px metadata/action separation. Screenshot saved C:/Users/dpasare/AppData/Local/Temp/adore-project-summary-dcp-20261001.png; QA tabs closed and temporary viewport reset. Existing live profiles/configuration/jobs unchanged. Verified delivery close-out commit follows.

## Rulings

## Handoff

current: done
status: ready
next: None; implementation and deployment complete.
must_read: 04_Software/web/src/App.tsx, 04_Software/web/src/styles.css
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Common header, scoped metadata spacing and documentation.
evidence: Build, desktop/phone, navigation and canonical checks pass; DCP UI/assets/health/readiness HTTP 200, services active, zero header selectors and 18px spacing.
issues: Seven explained advisory findings; no material deviation.
next: None.
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

## Delivery report (2026-10-01)

- stage: done; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-2c85559e - Keep platform administration independent of project selection
  - REQ-UX-7434a8cd - Separate project details metadata from action controls
- deviations: none recorded
- explicit review: disabled; existing validation remains required
- diff vs task base 2f06df6: 14 file(s) changed, 159 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=7 notes=16
- checklist: 4/4 done
