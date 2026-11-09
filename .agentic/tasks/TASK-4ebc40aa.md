<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-4ebc40aa - Paginate selected ticket timeline on Jobs

stage: done
type: change
path: quick
interaction: autopilot
requirements: REQ-UX-749d37c8
parent:
branch: task/adore-web-interface
base: 5749b9e2ab22bbb34d91257204dba284e6d7ede7
opened: 2026-10-01

## Done checklist (current stage)

- [x] Reuse the existing paged table for ticket history and update documentation.
- [x] Verify row choices, page boundaries, ticket switching and responsive layouts.
- [x] Review candidate and run canonical final proof.
- [x] Deploy static assets to DCP and verify the live ticket table.
- [x] Record verified delivery and include the candidate in its close-out commit.

## Frame

Problem: STATED selected-ticket history makes the Jobs page too long. OBSERVED open DCP Nilo ticket #26 has an unpaged Timeline list; the job directory already offers the requested paging.
Desired outcome: Selected-ticket history is a compact paged table.
Actors: Administrators and assigned developers reading a job.
Primary scenario: Open View for a ticket and browse its Date/Event/Stage history.
Examples: More than fifty events can be viewed ten at a time or with 25/50/All.
Counterexamples: Ten or fewer events need no navigation; empty history must show a clear empty state; switching tickets must return to the first page.
In scope: Replace Timeline list with the existing PagedTable, localized event header, remove obsolete list styles, current documentation and static deployment.
Out of scope: Nilo job execution/recovery, API/RBAC changes, altered event order or journal data.
Constraints: Existing event allowlist and authorization remain; retain chronological order and scoped run controls. Work bounded to this component, at most 20 candidate files and 30 minutes; no model calls.
Success signals: Default ten rows, 10/25/50/All choices, Previous/Next boundaries, full retained history, no document overflow at desktop and phone widths.
Evidence: OBSERVED App.tsx detail-panel maps every event into ol.timeline; PagedTable already provides all requested choices and clamps page bounds. Live browser confirms the long list.
Assumptions: INFERRED listing for the ticket means its open Timeline; live page confirms this interpretation. Standing uninterrupted implementation/commit/DCP deployment authority applies.
Unknowns: None blocking.
Decision-blocking questions: None.
Proposed behaviors: Use shared PagedTable keyed by project/run, with Date, Event and Stage columns and empty-state handling.
Path and reason: Quick path; existing REQ-UX-749d37c8 already requires paging for tables exceeding ten records. A presentation wiring change reuses established paging logic without adding a data or security contract.

## Requirement coverage

REQ-UX-749d37c8: manually verify ticket history uses existing page controls, finite boundaries, All, empty/short histories, ticket reset and responsive rendering. Existing offline API tests continue to prove authorization and invalid paging input rejection.

## Design

Reuse PagedTable around a semantic timeline table. Preserve journal order and event text. Key by selected project and run identity so another ticket starts at ten rows/page one. Localize the Event column in EN/FR/DE/RO, reuse Date/Stage and existing translations. React escapes journal text. Keep empty history explicit; shared table scrolling handles narrow widths. Remove obsolete timeline-list styles. No new dependency, API, persistence, permission or job lifecycle changes.

## Log

- 2026-10-01 frame: Scope accepted under standing autonomous instructions; quick path reuses the existing long-table requirement and shared pagination. Current branch is the established user implementation branch; no additional branch is needed for this incremental change. Manual presentation verification is appropriate for this reversible reuse of existing logic; no mirrored JSX/CSS test.
- 2026-10-01 build: Production build exit 0. Isolated real API/React QA fixtures contain 0, 10, 11 and 62 events. Default shows ordered events 001–010; Next shows 011–020. Sizes 25/50/All show 25/50/62 rows and reset page one. Last page at size 50 shows twelve rows ending event 062, Next disabled and Previous enabled. Ten events have no controls; eleven show navigation; zero shows Nothing to show. Switching tickets resets ten rows/page one. Desktop 1920px and phone 390px have document width 1905/375 respectively with internal table scrolling on phone; screenshot inspected, controls wrap visibly. Added Event labels in all four catalogs. Manual verification covers reversible presentation wiring to established PagedTable; no new paging algorithm or trust boundary.
- 2026-10-01 validate: Complete journal/requirement and source/documentation diff reviewed. Evolution matches the intended frontend/static/docs scope; whitespace check passes. `python .agentic/aegis.py check --task TASK-4ebc40aa --strict --run` exit 0: offline tests 51.0s, lint 0.1s, frontend tests 0.2s, errors=0 warnings=4. Advisories cover intentionally manual presentation wiring, generated minified asset scan limits, and unrelated existing tracked sidecars/legacy ruling metadata. No material deviation.
- 2026-10-01 deliver: Standing implementation/commit/DCP deployment authorization applies. Deploy only the verified static bundle; retain old static directory for rollback and keep API/worker running. Archive SHA-256 170ae241c3f994a1349c4e05f02ec1ab44472b1992906c3b942f57f0dd9c3415. Product candidate is unchanged after final proof.
- 2026-10-01 deliver: Archive hash verified; static assets installed on DCP with rollback static.pre-ticket-timeline-20261001. UI, JS/CSS, health and readiness HTTP 200; API/worker both active without restart. Live Nilo #26 history has Date/Event/Stage headers, 188 retained events, ten displayed and choices 10/25/50/All. Next shows 11–20 and Previous restores 1–10. Screenshot saved C:/Users/dpasare/AppData/Local/Temp/adore-ticket-timeline-dcp-20261001.png. No job operations initiated. QA tabs closed, viewport reset and isolated server stopped. Deployment complete before the close-out commit; unchanged verified product candidate is included.

## Rulings


## Handoff


current: done
status: ready
next: None; implementation and verified static deployment complete.
must_read: 04_Software/web/src/App.tsx, .agentic/requirements/ux/REQ-UX-749d37c8.toml
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Selected-ticket timeline table, localized Event column and current documentation.
evidence: Build, manual boundary/responsive checks and canonical offline checks pass; live DCP ten-row history, Next/Previous and all row choices verified; assets/health/readiness HTTP 200.
issues: Four explained advisories; no material deviation.
next: None.
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

## Delivery report (2026-10-01)

- stage: done; type: change; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-UX-749d37c8 - Localized responsive web interface
- deviations: none recorded
- explicit review: disabled; existing validation remains required
- diff vs task base 5749b9e: 14 file(s) changed, 120 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=4 notes=16
- checklist: 5/5 done
