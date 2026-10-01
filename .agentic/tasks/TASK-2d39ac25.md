<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-2d39ac25 - Remove unrelated project picker from platform administration

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-2c85559e
parent:
branch: task/adore-web-interface
base: 3194ca7eec38d0d65ed20f2075f50d060477e9c3
opened: 2026-10-01

## Done checklist (current stage)

- [x] Scope and manual verification requirement recorded.
- [x] Restrict header picker and reconcile documentation.
- [x] Browser/admin workflow, build and canonical final verification pass.
- [x] Commit and deploy; verify DCP.

## Frame

Problem: Header picker implies a project scope on platform-wide administration pages.
Desired outcome: System status, Users, Audit and Settings have no unrelated project picker.
Actors: Administrators and developers opening their account settings.
Primary scenario: Navigate to administration pages; content and actions remain platform/account scoped.
Examples: Storage lists all profiles; user membership checkboxes select assigned projects independently.
Counterexamples: Project details retains its useful header selector; Jobs/Metrics retain page-local scope.
In scope: Header predicate, docs, static build, deployment.
Out of scope: Platform settings behavior, RBAC, project membership API or data changes.
Constraints: Preserve project details, authorized membership controls and per-user preferences.
Success signals: Zero project pickers on platform/account pages; unchanged project-detail navigation.
Evidence: STATED remove header project on admin pages; OBSERVED App.tsx settings uses language/theme/password and Users uses membership checkboxes independently of selected.
Assumptions: Standing commit/deploy/autopilot authority applies.
Unknowns: None blocking.
Decision-blocking questions: None.
Proposed behaviors: Header picker appears only on Project details.
Path and reason: Full path for observable UI change; no new data/interface/dependency/security handling. Manual verification, no mirrored plumbing test.

## Requirement coverage

- REQ-UX-2c85559e: Picker relevance and retained workflows.

## Design

Allow the header project selector only on projectDetails, rather than maintaining a growing exclusion list. Platform pages own all-project, user-membership or per-account controls; their behavior does not depend on the selector. Update current frontend/user/knowledge contracts. Inspect each page and the retained project-details selector at desktop/phone sizes; run existing offline checks.

## Log

- 2026-10-01 frame/specify/design: Scoped the picker to Project details under standing autonomous implementation/deployment authority. All platform/account screens use their own controls; no data/API change. Manual verification covers the branch-free layout predicate.
- 2026-10-01 build/validate: Production build passed. Browser navigation confirmed zero header project selectors on System status, Users, Audit and Settings, with expected status/storage, user creation/accounts, audit policy/table and appearance/password controls intact. Settings at 390px has no page overflow or overlapping text. Project details retains exactly one authorized header selector. Developer settings follows the same page predicate; existing offline RBAC tests cover API privacy. Documentation and changelog reconciled; final one-predicate diff reviewed. Local QA tab closed and viewport reset.
- 2026-10-01 validate: Final evolution reviewed; `check --task TASK-2d39ac25 --strict --run` exited 0: offline suite 49.2s, lint 0.3s, frontend five tests 0.2s, zero strict errors. Six advisory warnings cover manually verified layout without mirrored tests, generated assets/secret-scan limitations and unrelated tracked fingerprint/old ruling metadata. No material deviation. Source/API/security behavior unchanged except requested selector visibility.
- 2026-10-01 deliver: Candidate presented as one header predicate, current frontend/user/knowledge docs, changelog, requirement/journal and bundled static assets. Standing authority covers local commit and DCP deployment. Archive SHA-256 c76de01125679ba6d1314ec090476d8cd730aaf3c5359312b9c52e0e25e7c98e. Local server stopped.
- 2026-10-01 deliver: DCP archive digest verified and frontend installed with rollback `static.pre-admin-picker-20261001`. UI, JS, health and readiness HTTP 200; web and worker active. Live browser verified zero header project selectors and retained expected controls on all four Administration pages. Local screenshot saved for acceptance evidence; tabs closed. Deployment succeeded before delivery close-out commit; no settings/accounts/repository contents changed.

## Rulings


## Handoff


current: done
status: ready
next: None; completed and deployed.
must_read: 04_Software/web/src/App.tsx, 05_SoftwareDocu/Component_Web_Frontend.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Header project picker restricted to Project details; docs and DCP assets updated.
evidence: Build, offline suite, lint, frontend tests and strict validation passed; GUI and live endpoint checks passed.
issues: Six explained advisory warnings; no material deviation.
next: None.
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

## Delivery report (2026-10-01)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-2c85559e - Keep platform administration independent of project selection
- deviations: none recorded
- explicit review: disabled; existing validation remains required
- diff vs task base 3194ca7: 10 file(s) changed, 129 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=7 notes=13
- checklist: 3/4 done; open: Commit and deploy; verify DCP.
