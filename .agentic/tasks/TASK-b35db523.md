<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-b35db523 - Overview expandable summary cards

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-UX-15ad4473
parent:
branch: task/adore-web-interface
base: 8f3d897f898b4188b2618bfc4a6a3c64c0f56011
opened: 2026-10-01

## Done checklist (current stage)

- [x] Implement the authorized Overview interaction and update its contract.
- [x] Verify browser behavior, integrated checks and DCP deployment.

## Frame

Problem: Overview repeats a project selector in the top bar and its cards cannot show their underlying records.
Desired outcome: Expand one summary card into a matching table beneath it, with project selection in Projects.
Actors: Administrators and project-scoped developers.
Primary scenario: Open Overview, select Projects, choose a project, then expand a job category to inspect its runs.
Examples: Six projects appear in the Projects table; a selected project's failed runs appear under Failed jobs.
Counterexamples: A developer cannot inspect an unassigned project; empty categories display an empty state.
In scope: Four card interactions, existing Recent jobs fallback, project selection, table paging and navigation.
Out of scope: New API routes or global cross-project job views.
Constraints: Existing server authorization and run lifecycle counts; responsive layout; four languages through existing labels.
Success signals: No Overview top-bar selector; cards toggle; project and job tables match selected scope; links open detail pages.
Evidence: STATED in user request; OBSERVED in 04_Software/web/src/App.tsx and existing scoped runs-page API.
Assumptions: Only one expanded card at a time; deselection restores Recent jobs.
Unknowns: None blocking.
Decision-blocking questions: None; user explicitly authorized implementation and DCP deployment.
Proposed behaviors: Existing authorized endpoint supplies complete scoped run history only while a job card is expanded.
Path and reason: Full path; new visible UI behavior. Interaction is autopilot under user's no-interruption instruction.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Expand overview cards | One selected card controls the table, project scope and fallback | REQ-UX-15ad4473 | Select project and inspect filtered runs | Unassigned project is unavailable; empty table shows no jobs | Manual browser inspection | Reuse authorized runs-page and local table paging |

## Design

Keep the Overview card selection in React state. The Projects card renders the already authorized profile list and changes the same project ID used by Jobs and Metrics. Job card expansion requests complete runs through the existing scoped endpoint, filters by the card lifecycle set and paginates locally. The existing seven-run Overview fetch remains the collapsed view. The top bar omits its picker only on Overview.

## Log

- 2026-10-01 frame/specify/design: Full-path Overview behavior linked to REQ-UX-15ad4473; user authorization includes deployment and no intermediate prompts.
- 2026-10-01 build: React card state, scoped expanded tables, local paging and responsive card styling compiled with TypeScript/Vite; source and component/user documentation updated. Verification is manual for this interaction.
- 2026-10-01 validate: Full offline suite and Ruff passed through strict AEGIS check (zero errors); TypeScript/Vite, release consistency and diff whitespace passed. Chrome verified four card states, six-project selection, Nilo failed-run filter and detail navigation at desktop, 360px and 260px with no page overflow. Other categories on DCP were empty, so their positive populated-row behavior relies on the existing lifecycle filter and table contract.
- 2026-10-01 deliver: Hash-verified compiled UI files were staged and switched into the real DCP runtime with the prior static directory retained for rollback. HTTPS health, ready, UI and JS returned 200; the API and worker remained active. No project configuration, run state or repository was changed.

## Rulings


## Handoff


current: done
status: ready
next: none
must_read: 04_Software/web/src/App.tsx, 05_SoftwareDocu/Component_Web_Frontend.md
blockers: none

## Stage report

stage: done
result: completed
current: done
changed: React Overview, CSS, bundled static UI and documentation
evidence: npm build, full offline suite/Ruff, strict AEGIS, desktop/360px/260px Chrome checks, HTTPS health/ready/UI/assets 200
issues: DCP had only one failed run; populated active/review and pagination cases were not live-tested
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1
