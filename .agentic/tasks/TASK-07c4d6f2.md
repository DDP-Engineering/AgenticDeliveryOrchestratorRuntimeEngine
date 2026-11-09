<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-07c4d6f2 - Metrics project selector in reporting controls

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-fa9e0efa
parent:
branch: task/adore-web-interface
base: f0a15fa93e9158eac315d4b01a90db4800779eae
opened: 2026-10-01

## Done checklist (current stage)

- [x] Move Metrics project selection into reporting controls and update docs.
- [x] Check scoped metrics/export links and responsive layout.
- [x] Run final verification and deploy/commit.

## Frame

Problem: Metrics project selector remains in the top-center header.
Desired outcome: Project scope selected within the reporting controls on the page.
Actors: Administrators and assigned developers viewing metrics/exporting CSV.
Primary scenario: Open Metrics, select an authorized project in the reporting panel; selected-project data and CSV links use that project.
Examples: Changing between disposable projects updates their Summary and Usage views, while period settings remain.
Counterexamples: An account with no assigned projects has no picker or project export; global admin metrics retain their existing scope.
In scope: Picker location, compact layout, documentation and frontend deployment.
Out of scope: Metric/API/query semantics, RBAC, global aggregation changes.
Constraints: Keep selected state and immutable authorized project IDs; existing financial privacy and CSV scope preserved.
Success signals: No header picker on Metrics; one page-local selector, shared across tabs, responsive without overlap.
Evidence: STATED move selector onto page if functional; OBSERVED App.tsx uses selected for metrics/usage/export routes; INFERRED include it with common reporting controls.
Assumptions: Standing no-interruption, commit and deployment authorization applies.
Unknowns: None blocking.
Decision-blocking questions: None.
Proposed behaviors: Authorized-project select first in reporting filters, full width on phones; no picker without projects.
Path and reason: Full path for visible layout change; API/data/dependencies/security unchanged. No children.

## Requirement coverage

- REQ-UX-fa9e0efa: Metrics-local project selection, shared scope and responsive layout.

## Design

Reuse selected and authorized project options; suppress the header selector on Metrics and add the same binding to the reporting panel. A phone-specific grid span puts project selection above the four period controls, preserving the existing two-column period layout. CSV route construction and tab state remain unchanged.

## Log

- 2026-10-01 frame/specify/design: Confirmed selector controls project metrics and CSV exports. User requested its relocation into page content; scope preserves existing data and RBAC contracts. Autopilot follows standing authorization.
- 2026-10-01 build: Header Metrics picker removed; identical selected/project-ID binding added first in reporting filters. Phone project control spans the row above period filters. Build passed and frontend/user/knowledge/changelog documentation reconciled.
- 2026-10-01 validate: Browser observed zero header selectors and one reporting-panel project picker. Switching from a two-run fixture to an empty fixture updates Summary to zero and changes project metrics/usage CSV routes to the selected immutable ID; global CSV routes remain global. Native date input, timezone, grouping and Usage tab retained when changing projects. Desktop layout and 390px phone layout inspected; project selection spans the phone row with no page overflow. Existing projects-length guard omits picker for zero projects; offline RBAC tests retain authorized data/export boundaries. Local QA tab closed and viewport reset.
- 2026-10-01 validate: Evolution refreshed for the final 10-path product candidate. `python .agentic/aegis.py check --task TASK-07c4d6f2 --strict --run` exited 0: tests passed in 57.0s, lint passed and strict check found zero errors. Seven warnings concern manual frontend verification, generated-asset coverage/scanning and unrelated tracked fingerprint/older journal metadata. Final semantic diff review confirms selected binding, role-scoped options, no-project guard and CSV/global contract unchanged.
- 2026-10-01 deliver: Continuing authorized commit/DCP static deployment without a new prompt; local QA server stopped. No real project jobs or repository changes requested or performed.
- 2026-10-01 deliver: DCP frontend deployment succeeded before close-out commit. Transfer SHA-256 c0e55f3bce5a7b872b20c030f814e976e3b363e0eb153049db1aaaec3f1246c6 matched; installed assets index-CDRRGQlF.js and index-BNj7cSy-.css. UI, assets, API health/readiness returned HTTP 200; web/worker services active. Prior files retained at `static.pre-metrics-selector-20261001` alongside installed static directory for rollback.

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
changed: Metrics-local project selector, phone layout and docs.
evidence: Build, GUI, offline suite, lint and strict check passed; DCP page/assets/health/readiness 200, services active.
issues: None.
next: None.
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

## Delivery report (2026-10-01)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-fa9e0efa - Select metrics project within reporting controls
- deviations: none recorded
- explicit review: disabled; existing validation remains required
- diff vs task base f0a15fa: 13 file(s) changed, 150 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=8 notes=11
- checklist: 2/3 done; open: Run final verification and deploy/commit.
