<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-5742dd1b - Guided standalone Add project page

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-UX-b3116a07, REQ-UX-2761363b
parent:
branch: task/adore-web-interface
base: ad3559a87ec1cbb91a9834374d632f74c998a10e
opened: 2026-10-01

## Done checklist (current stage)

- [x] Inspect the existing project creation contract and UI.
- [x] Implement the dedicated page and localized field help.
- [x] Update the frontend component and user documentation.
- [x] Validate the final build, responsive page and offline suite.
- [x] Deliver the validated candidate.

## Frame

Problem: The Add project form expands above the Projects table and offers little field guidance.
Desired outcome: A focused creation page with help for each field and an editable image selector.
Actors: Platform administrator creating a project; developer browsing assigned projects.
Primary scenario: Admin opens Add project, reads field help, enters a host clone path and image tag, saves, and reaches project details.
Examples: /home/adore/projects/example is a host clone path; adore-executor-base:1.0.0 is a suggested image tag.
Counterexamples: A browser-machine path is not a valid host clone; suggested image tags are not proof of local availability.
In scope: React navigation, help text in en/fr/de/ro, editable image suggestions, responsive layout, docs.
Out of scope: New image-discovery API, changes to profile creation or existing project configuration, project import redesign.
Constraints: Keep admin-only creation, existing backend validation, offline install and no image download.
Success signals: Projects table stays separate; each creation field has help; Back and Cancel do not mutate; build and suite pass.
Evidence: STATED user request and screenshot; OBSERVED App.tsx inline form and wizard.py host-path/image contract; INFERRED editable datalist fits host-specific tags.
Assumptions: Known image names are examples and may not be installed; installation supports manual image preparation.
Unknowns: Exact host-specific image inventory varies by deployment.
Decision-blocking questions: None.
Proposed behaviors: Dedicated admin page; localized field help; editable image suggestions; details navigation on save.
Path and reason: Full path because the UI workflow and visible interface change. Autopilot follows the user's standing no-interruption preference.

## Requirement coverage

- REQ-UX-b3116a07: dedicated creation navigation and return behavior.
- REQ-UX-2761363b: localized guidance and editable image choices.


## Design

Reuse the existing POST /projects contract. A createProject page state renders a focused form and suppresses the project picker. GuidedField binds a visible label to each control and provides a Help disclosure. Native datalist suggestions keep image tags editable without a server image-list API. Keep import on the Projects page, unchanged.


## Log

- 2026-10-01 frame: Full path for a visible admin workflow change; no blocking questions. User's standing preference authorizes continuous implementation.
- 2026-10-01 specify/design: Two UX requirements cover page navigation and field guidance; existing project POST and import contracts are preserved.
- 2026-10-01 build: React page, localized help, image suggestions and documentation updated; production frontend build passed.
- 2026-10-01 validate: 689 offline tests passed, one skipped; lint and strict check commands passed. Browser tested creation, Cancel, editable image tag, executor auth, all four locale catalogs and widths 390, 800 and desktop with no horizontal overflow. Strict check reported non-blocking generated-asset/source-test warnings plus pre-existing repository notes.
- 2026-10-01 deliver: Static bundle SHA-256 90d27257c579ebed027dc2dd82c9805c7385ad5f1429e3c8a2cd21d1bd613fe2 verified on DCP. Existing static retained as static.pre-guided-create-20261001; live UI, JavaScript asset and health returned HTTP 200. API, worker, profiles and repositories were not changed.

## Rulings


## Handoff


current: done
status: ready
next: none
must_read: 04_Software/web/src/App.tsx, 04_Software/web/src/i18n.ts, 05_SoftwareDocu/Component_Web_Frontend.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: React page, help catalogs/styles, documentation and UX requirements.
evidence: Frontend build passed; 689 offline tests passed and one skipped; lint and strict check passed. Browser confirmed responsive layout, field help and successful local project creation. DCP static hash verified and live UI, asset and health returned HTTP 200.
issues: Non-blocking check warnings on generated assets, no new test file and pre-existing repository records.
next: none
needs_user: no
spec_compliance:
implementation_quality:
review_round:

## Delivery report (2026-10-01)

- stage: deliver; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-b3116a07 - Open project creation on a separate page
  - REQ-UX-2761363b - Explain every project creation field
- deviations: none recorded
- explicit review: disabled; existing validation remains required
- diff vs task base ad3559a: 15 file(s) changed, 235 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=8 notes=7
- checklist: 4/5 done; open: Deliver the validated candidate.
