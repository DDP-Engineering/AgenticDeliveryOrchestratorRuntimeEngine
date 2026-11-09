<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-2919fbc1 - Standalone Import project page

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-UX-5c1f6078, REQ-DATA-71853fbc
parent:
branch: task/adore-web-interface
base: 04ea19586ee139aca94ef138475f9ba69783a67d
opened: 2026-10-01

## Done checklist (current stage)

- [x] Review import API and frontend navigation contracts.
- [x] Implement the standalone page, field guidance and draft clearing.
- [x] Update component, user and knowledge documentation.
- [x] Run final build, offline validation and responsive inspection.
- [x] Commit and deploy the validated static bundle.

## Frame

Problem: Import project expands inside the Projects directory.
Desired outcome: A dedicated import page consistent with Add project.
Actors: Platform administrator importing an existing ADORE configuration.
Primary scenario: Open Import project, choose a config and new name, review validation, confirm the exact revision, then open project details.
Examples: Import a host-compatible config.toml with absolute paths and pickup paused.
Counterexamples: Leaving an unconfirmed draft must not retain its file contents or stale preview.
In scope: React navigation, localized field help, draft clearing, docs, static delivery.
Out of scope: Import API or profile-storage contract changes.
Constraints: Admin-only import, exact-revision preview, original file unchanged, existing offline validation.
Success signals: No project selector or directory table on the import page; Back and Cancel return; preview API tests pass.
Evidence: STATED separate-page request; OBSERVED App.tsx inline import form and test_web_import.py happy/negative API coverage; INFERRED reuse Add project styling and details navigation.
Assumptions: The user's standing continuous-implementation and DCP delivery preference applies.
Unknowns: Browser extension file-upload automation requires file-URL permission unavailable in this session.
Decision-blocking questions: None.
Proposed behaviors: Dedicated importProject page with three Help disclosures; clear drafts and invalidate reads/previews when leaving; details navigation after import.
Path and reason: Full path because navigation and browser-memory lifecycle visibly change. Autopilot follows the user's standing no-interruption instruction.

## Requirement coverage

- REQ-UX-5c1f6078: separate page, localized field guidance and successful-import navigation.
- REQ-DATA-71853fbc: draft clearing and late file/preview invalidation.

## Design

Use the existing preview/import endpoints and their revision contract. Replace the inline toggle with a page state, keep Projects highlighted and suppress the project selector. Reuse GuidedField and responsive form styles. On page exit, clear browser-held draft values and increment file-read and preview request counters so late results are ignored.

## Log

- 2026-10-01 frame: Full path; user requested a separate import page and no decision-blocking questions remain.
- 2026-10-01 specify/design: Two requirements cover standalone navigation and draft lifecycle; existing import API is preserved.
- 2026-10-01 build: Separate import page, three localized Help disclosures, draft clearing and docs implemented; production build passed.
- 2026-10-01 validate: Browser confirmed desktop/390px layout, three Help disclosures, disabled preview with no file, and Cancel clearing the entered draft name. Existing import API tests cover exact revision, invalid/secret/relative/stale input, roles/CSRF, state ownership and active-state locks.
- 2026-10-01 DEVIATION validate: Browser file-upload automation could not run because the Chrome extension lacks file-URL access; the available in-app browser is also unavailable. Existing offline import API tests and source review cover the preserved contract; live GUI upload confirmation remains untested in this session.
- 2026-10-01 validate: Final `python .agentic/aegis.py check --task TASK-2919fbc1 --strict --run` exited 0: configured offline tests and lint passed, strict check passed with zero errors and six advisory warnings. Manual frontend coverage and generated-asset coverage/scan notes are accepted; unrelated tracked fingerprint and older journal warnings remain out of scope. Semantic review confirmed the import API, admin-only navigation, exact-preview contract and localized help remain consistent with the requirements.
- 2026-10-01 DEVIATION validate: No pre-edit anchor was recorded, so evolution reporting is unavailable. The final Git diff was reviewed directly and the final tree passed full verification; no retrospective anchor was fabricated.
- 2026-10-01 deliver: Standing user authorization covers continued implementation, commit and DCP deployment without further prompts. Only frontend static assets are deployed; existing repositories and profile configuration are unchanged.
- 2026-10-01 deliver: DCP static bundle deployed successfully; UI, new JS asset and API health returned HTTP 200, and web/worker services remained active. Archive SHA-256 c1321d3f9e60c3e5d397c40d27c4911dc94a00a4038c5e80d77d459a03402989 matched after transfer. Rollback is the `static.pre-import-page-20261001` directory alongside the installed static files. Deployment succeeded before this close-out commit.

## Rulings


## Handoff


current: done
status: ready
next: None; implementation and deployment complete.
must_read: 04_Software/web/src/App.tsx, 04_Software/tests/test_web_import.py, 05_SoftwareDocu/Component_Web_Frontend.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Standalone import page, localized field help, draft clearing, docs and static bundle.
evidence: Build, suite, lint, strict check and responsive checks passed; DCP UI/asset/health 200, services active.
issues: GUI upload automation blocked by extension permission; pre-edit fingerprint absent. Both recorded as accepted verification limits.
next: None.
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

## Delivery report (2026-10-01)

- stage: deliver; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-5c1f6078 - Open project import on a separate page
  - REQ-DATA-71853fbc - Clear import draft when leaving the page
- deviations: 2 recorded
  - validate: Browser file-upload automation could not run because the Chrome extension lacks file-URL access; the available in-app browser is also unavailable. Existing offline import API tests and source review cover the preserved contract; live GUI upload confirmation remains untested in this session.
  - validate: No pre-edit anchor was recorded, so evolution reporting is unavailable. The final Git diff was reviewed directly and the final tree passed full verification; no retrospective anchor was fabricated.
- explicit review: disabled; existing validation remains required
- diff vs task base 04ea195: 12 file(s) changed, 211 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=7 notes=9
- checklist: 4/5 done; open: Commit and deploy the validated static bundle.
