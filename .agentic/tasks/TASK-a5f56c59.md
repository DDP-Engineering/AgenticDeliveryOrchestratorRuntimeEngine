<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-a5f56c59 - Jobs page project selection and ticket guidance

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-51b770d7
parent:
branch: task/adore-web-interface
base: 1d378b97de3db3418f2e1afad3f64fc183942d8c
opened: 2026-10-01

## Done checklist (current stage)

- [x] Implement Jobs-local project selection and localized ticket help.
- [x] Reconcile frontend, user and component documentation.
- [x] Verify valid and invalid inputs, switching, archived state and responsive layout.
- [x] Run full offline verification and deploy/commit the validated bundle.

## Frame

Problem: Jobs displays a project picker in the top-center header and an unexplained ticket field.
Desired outcome: Clear header and contextual project/ticket controls with guidance.
Actors: Administrators and assigned developers.
Primary scenario: Open Jobs, choose an authorized project beside the ticket field, read Help, enter its existing issue number and request a job.
Examples: Issue URL ending in /issues/42 uses integer 42, without # or the full URL.
Counterexamples: Zero, fractional or empty input must not submit. Archived projects remain selectable for history without a Start form.
In scope: Frontend layout, ticket guidance, draft clearing on project change, docs and static DCP delivery.
Out of scope: Cross-project aggregation, job operation API changes, actual execution on existing repos.
Constraints: Authorized project scope, existing readiness/hold/exclude rules, unchanged human publication gate.
Success signals: No header project picker on Jobs; localized Help is accessible; page controls wrap without overlap.
Evidence: STATED header removal and ticket help; OBSERVED App.tsx jobs scoped by selected and operations start integer validation in app.py; INFERRED move picker beside ticket to preserve explicit project targeting.
Assumptions: Standing commit/deploy and uninterrupted implementation authorization continues.
Unknowns: None blocking.
Decision-blocking questions: None.
Proposed behaviors: Page-local picker persists on archived profiles; ticket draft clears on changing it. Reuse GuidedField and native positive integer validation.
Path and reason: Full path; new visible guidance and layout, existing API/data/dependencies/security contracts unchanged. No child tasks needed.

## Requirement coverage

- REQ-UX-51b770d7: Jobs layout, guidance, scoped selection and input boundaries.

## Design

Suppress the header picker only on Jobs. Render authorized-project options in a compact page form beside GuidedField ticket input; keep selector available for archived history while hiding ticket/start. Clear ticket on project switch to avoid submitting a number for another repository. Native required/min/step validation protects the browser form, with API authorization, CSRF and integer checking retained as the trust boundary.

## Log

- 2026-10-01 frame/specify/design: User's header cleanup and guidance request scoped to Jobs. Full path and autopilot; project targeting stays explicit inside content. Existing job APIs and approval contracts preserved.
- 2026-10-01 build: Header picker removed from Jobs, authorized project selection moved beside GuidedField ticket input; localized guidance and responsive form implemented. Project change clears ticket and open details. Documentation reconciled and production build passed.
- 2026-10-01 validate: Browser confirmed header has zero selectors; Help displays in en/fr/de/ro. Native validity accepts 42 and rejects empty, zero and 1.5. Changing project clears ticket; archived profile keeps project selection and hides start controls. One local disposable request queued successfully with no worker running. Desktop, 768px and 390px inspections passed after correcting the initial phone Help clipping; no horizontal overflow, and the expanded Help stays in the viewport. API authorization, CSRF and archive tests cover the unchanged trust boundary.
- 2026-10-01 validate: Evolution records the final 11-path candidate. Final `python .agentic/aegis.py check --task TASK-a5f56c59 --strict --run` exited 0; configured offline tests passed in 49.1s, lint passed and strict check found zero errors. Seven advisory warnings cover manually inspected frontend behavior, generated asset coverage/scan limits and unrelated tracked fingerprints/older journal metadata. Diff reviewed against scope, requirements, authorization and archived-state contracts. No current-task verification failures remain.
- 2026-10-01 deliver: Continuing commit and DCP static deployment under the user's standing authorization; existing repository data, worker configuration and publication gate remain unchanged. Local browser tab closed and QA server stopped.
- 2026-10-01 deliver: DCP static deployment succeeded before close-out commit. Transfer SHA-256 a7f91c62b6f3f6f9c0b0b7b8f02ca3ba9a2de805dd47708a7a7b6399f38176be matched; installed JS index-BdY39rwH.js and CSS index-BXF8XE31.css. UI, both assets, API health and readiness returned HTTP 200, with API/worker services active. Previous frontend retained at `static.pre-jobs-guidance-20261001` alongside installed static files. No real project jobs were submitted.

## Rulings


## Handoff


current: done
status: ready
next: None; implementation and deployment complete.
must_read: 04_Software/web/src/App.tsx, 04_Software/web/src/styles.css, 05_SoftwareDocu/Component_Web_Frontend.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Jobs-local selector, ticket Help, responsive form and docs.
evidence: Build, GUI, suite, lint and strict checks passed; DCP page/assets/health/readiness 200, services active.
issues: None.
next: None.
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

## Delivery report (2026-10-01)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-51b770d7 - Keep Jobs project selection within page with ticket guidance
- deviations: none recorded
- explicit review: disabled; existing validation remains required
- diff vs task base 1d378b9: 14 file(s) changed, 163 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=8 notes=9
- checklist: 3/4 done; open: Run full offline verification and deploy/commit the validated bundle.
