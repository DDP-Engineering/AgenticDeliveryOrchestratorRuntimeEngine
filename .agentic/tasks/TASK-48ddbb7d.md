<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-48ddbb7d - Projects table and per-row controls

stage: build
type: feature
path: full
interaction: autopilot
requirements: REQ-UX-3b7dd34e
parent:
branch: task/adore-web-interface
base: 0d27b8233512a2a2093039318f4147012056a825
opened: 2026-10-01

## Done checklist (current stage)

- [x] Frame and specify the table behavior.
- [x] Build and verify the table and row actions.
- [ ] Resolve removal semantics and implement that action.
- [ ] Validate, deploy and report the DCP result.

## Frame

Problem: Projects uses a redundant top-bar selector, search/filter controls, cards and a separate selected-project action panel.
Desired outcome: A single sortable and paginated project table with controls on each row.
Actors: Administrator; project-scoped developer.
Primary scenario: Open Projects, sort by a column, inspect a row and use its authorized action.
Examples: Nilo sorts first by descending job count; an administrator resumes pickup for a paused project from its row.
Counterexamples: A developer sees only authorized projects and no mutating row actions; a malformed project cannot bypass server checks.
In scope: Projects view layout, sorting, pagination, per-row pickup/archive/detail controls, and a removal action after its scope is clarified.
Out of scope: Editing repository integration files unless explicitly selected by the owner.
Constraints: Existing API authorization and operational gates; preserve history and the human merge boundary; four languages and responsive layout.
Success signals: No Projects top-bar selector or old cards/filters; sorting and pages work; actions target their own row.
Evidence: STATED in user request and screenshot; OBSERVED in App.tsx, scoped operations, archive and profile-store behavior.
Assumptions: Sorting is client-side over the already authorized project list; missing activity sorts last.
Unknowns: Meaning of “remove ADORE from project” and whether repository files or only installation membership are affected.
Decision-blocking questions: Removal semantics requested asynchronously; the table work can proceed independently.
Proposed behaviors: The project table keeps the existing server-owned pickup/archive checks.
Path and reason: Full path for new UI behavior; autopilot reflects the user's standing no-interruption preference.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Project table | Authorized rows, sorting, paging and row actions | REQ-UX-3b7dd34e | Sort Nilo by jobs and open its detail | Developer sees no mutators; empty list remains empty | Manual browser inspection | Reuse PagedTable and current API operations |
| Removal | Pending owner choice | Pending | Pending | Existing CLI delete destroys profile/state | Pending | Do not implement destructive semantics by assumption |

## Design

Render one table from the authorized `GET /projects` list. Sort by a single column with reversible direction and a stable project-name tie break; use the shared `PagedTable`. Pass each row's immutable project ID directly to existing operation/archive endpoints. Hide the top-bar selector only on Projects, retaining it on details, Jobs, Metrics and Settings. Resolve removal separately before extending API or row menu.

## Log

- 2026-10-01 frame/specify/design: Projects table behavior accepted from explicit user request and linked to REQ-UX-3b7dd34e. Removal is separated because `adore profile delete --force` irreversibly deletes state, while repository integration-file removal is a different action.
- 2026-10-01 build correction: Live DCP inspection found the nine-column table pushed action controls off-screen even at 1920px. Reduced the directory to five sortable data columns plus Actions; forge, runtime and executor remain on Project details.
- 2026-10-01 build proof: TypeScript/Vite passed after the layout correction. A local 12-project browser fixture verified 10/25/50/All controls, Next, descending numeric job sorting and reset to page one; mocked row pickup/archive requests used the clicked project ID, and a developer saw only View. Live DCP showed all six real projects, Nilo sorting first by job count, actions visible without desktop horizontal scrolling, and no page-wide overflow at 360px. HTTPS health, ready, UI and the compiled asset returned 200. The full offline suite and Ruff passed before the column-only correction; no backend behavior changed.
- 2026-10-01 build partial delivery: Hash-verified UI assets switched on DCP with separate rollback directories; real project settings, run state and repositories were unchanged. The removal action remains pending the owner's meaning of “remove ADORE from project.”
- 2026-10-01 build pause: Commit `93765f7` records the tested table. The removal action awaits the owner choice between detaching this ADORE profile with history preserved and changing integration files in the repository; the existing destructive profile-delete command is not used.

## Rulings


## Handoff


current: build
status: waiting
next: resolve removal meaning, then implement and verify its action
must_read: 04_Software/web/src/App.tsx, 05_SoftwareDocu/Component_Web_Frontend.md
blockers: removal scope pending; table portion is deployed

## Stage report

stage: build
result: paused
current: build
changed: sortable Projects table, row controls, bundled UI and documentation
evidence: local 12-project browser fixture, real DCP browser at desktop/360px, TypeScript/Vite, full offline suite/Ruff, HTTPS health/ready/assets 200
issues: removal semantics pending; no live pickup/archive mutation was performed
next: implement removal after owner clarification
needs_user: yes
spec_compliance:
implementation_quality:
review_round:
