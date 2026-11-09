<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-63cb3a30 - Simplify raw TOML project export and import

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-3b5b2257, REQ-UX-1cd0e743, REQ-DATA-71853fbc, REQ-UX-34ca5d39
parent:
branch: task/adore-web-interface
base: bb3141c9afb6bf286379c5449835e98da9bf5256
opened: 2026-11-09

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
- [x] final targeted proof and deviation logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem: STATED Import project config is more complicated than the inverse of Download raw configuration. OBSERVED The form separates six screens and demands identity values manually.
Desired outcome: STATED Export raw configuration and Import raw configuration as paired actions, with input consistency checks.
Actors: OBSERVED Administrators authorized for raw TOML export and project enrollment.
Primary scenario: INFERRED Export a saved TOML, select the same bytes in Projects, validate the file and import it with monitoring paused.
Examples: INFERRED A compatible file with available paths/identity can import without typing identity. A conflicting state folder displays a finding and blocks import.
Counterexamples: INFERRED An invalid, changed or stale file must not create a project. A new enrollment must not replace an existing project.
In scope: STATED Exact TOML import/export action labels and simpler import. INFERRED One page, a suggested name derived from the declared repository, optional identity overrides and existing revision-bound consistency checks.
Out of scope: OBSERVED Existing action enrolls a project; preserve that boundary. No changes to guided enrollment, clone, activation, other project data or stored formats.
Constraints: OBSERVED AEGIS autopilot, same branch, focused offline verification. Bound work to 90 minutes, 45 paths and five review cycles. No live import or external command probes.
Success signals: INFERRED The happy path needs file selection, validation and confirmation on one page. Invalid TOML, unowned-path conflicts, embedded secrets and changes after validation cannot publish.
Evidence: OBSERVED ImportWizard, importCopy, RawConfiguration and existing import-preview/import-check/import endpoint contracts.
Assumptions: INFERRED The screenshot's Projects import is a new enrollment, and its exact copy validation is still wanted.
Unknowns: None material.
Decision-blocking questions: None.
Proposed behaviors: INFERRED Keep a concise validation result and optional technical detail on the same page. Reuse the existing manual environment verification inside details and after import in project Summary.
Path and reason: Full because the web flow and preview inputs change.

| Criterion | Holds | Evidence |
| --- | --- | --- |
| no new externally observable behavior | no | One page and automatic identity suggestion |
| no new interface or data format | no | Preview may omit an explicit ID |
| no new dependency | yes | Existing TOML parser and identity helper |
| an existing requirement already covers the behavior | no | Existing contract specifies six steps |
| no security or data-handling change | yes | Existing raw bytes, Admin/CSRF and publication guards |

## Requirement coverage

| Behavior | Requirement | Verification |
| --- | --- | --- |
| One page for exact import | REQ-UX-3b5b2257 | Valid file enables import, invalid files show findings |
| Automatic default identity | REQ-UX-1cd0e743 | No ID supplied, exact reviewed identity imports |
| Draft and response protection | REQ-DATA-71853fbc | Edits invalidate proof, changed source and stale results fail closed |
| Exact export action | REQ-UX-34ca5d39 | Settings export downloads original bytes |

## Design

### Approach

Keep the exact import API and raw download. Relabel the UI actions as an import/export pair and render file, validation and confirmation together (REQ-UX-3b5b2257, REQ-UX-34ca5d39). Put identity overrides, safe configuration review and optional environment check in disclosures.

### Interfaces and data

Only import-preview may omit identity. Read the declared repository leaf locally to derive an available name using the existing profile ID helper (REQ-UX-1cd0e743). Preview supplies the resolved identity and bound digest. Check and import send that explicit identity with the same reviewed bytes; publication retains its locked validation. Edits and navigation retain the existing memory/generation/source-change guards (REQ-DATA-71853fbc).

### Files and test seams

app.py and test_web_import.py for omitted ID, current authority and exact bytes. ImportWizard.tsx, importCopy.ts, RawConfiguration.tsx, i18n.ts and focused import, shell and portable browser specs. Update four locale help pages, documentation and release notes.

### Risks and open decisions

Preview identity is advisory until locked publication. Existing conflicting paths, secrets and invalid documents remain errors. A changed file or reviewed identity cannot publish. Current data formats and privileges are unchanged.

### Requirement map

One-page browser flow proves REQ-UX-3b5b2257 and REQ-DATA-71853fbc. Preview and publish tests prove REQ-UX-1cd0e743. Byte-for-byte browser export proves REQ-UX-34ca5d39.

Diagrams: [diagram_TASK-63cb3a30.md](diagram_TASK-63cb3a30.md)

## Log

- 2026-11-09 frame: journal opened
- 2026-11-09 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-09 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-09 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-09 build: red: pytest derives_identity exit 1 (missing name returned 422); Chromium raw import happy-path exit 1 (old import wizard lacked the raw action and one-page flow).
- 2026-11-09 build: green: pytest derives_identity exit 0; preview resolved the repository identity, rejected changed bytes and saved exact reviewed TOML.
- 2026-11-09 build: red: the suggested-name trust-boundary test reproduced an echo from a credential-bearing repository URL. Limit name derivation to repository identifiers.
- 2026-11-09 build: green: E2E build and 13 Chromium import cases exit 0. Includes exact no-ID import, all four locales, invalid/corrupt file, readiness, draft and privilege boundaries. Two new Python identity/URL cases and targeted Ruff passed.
- 2026-11-09 build: release-notes: updated (paired raw actions and one-page import).
- 2026-11-09 build: help: updated (Projects, Settings and interface in en/fr/de/ro).
- 2026-11-09 build: Build inspection: 30 paths in task evolution including user, API, frontend and four-locale help changes. Static check showed zero errors. Repository-wide historical references, E2E path classification and the large generated JS scan limit remain advisory.
- 2026-11-09 build: completed; next validate
- 2026-11-09 validate: Production frontend built and 9 focused Chromium raw export/Projects navigation tests passed, including four localized layouts and byte-exact download.
- 2026-11-09 validate: Review 1: Settings help should state that exported bytes are an input, while successful enrollment depends on server paths, state ownership and secret checks.
- 2026-11-09 validate: returned to build - Align export help with server validation in all four locales.
- 2026-11-09 build: Review 1 fix: Settings help now explains checks for server paths, state-folder ownership and inline secrets. Eleven help tests and both frontend builds exit 0.
- 2026-11-09 build: Inspection: ADORE served the rebuilt asset at localhost port 18771, with readiness HTTP 200 and OpenAPI optional ID on import-preview. The listener uses the same ADORE home and worker. No live project import was submitted.
- 2026-11-09 build: completed; next validate
- 2026-11-09 validate: DEVIATION validate: use targeted import/export API and Chromium proof, help checks and targeted lint rather than the full repository suites, per the user's standing preference.
- 2026-11-09 validate: final: AEGIS static strict check, release notes, git diff --check, 9 focused API tests, targeted Ruff, 11 help tests and 6 focused Chromium cases exit 0. Static 0 errors and 68 advisory warnings (repository references and journals, E2E file classification and generated asset scan limit). Direct asset key-pattern inspection passed. Pytest emitted the existing TestClient deprecation warning.
- 2026-11-09 validate: completed; next done

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-63cb3a30.md
changed: Paired raw actions and one-page validated import; help documents destination checks
evidence: 9 API, 6 Chromium, 11 help tests, focused lint and strict static checks exit 0
issues: Targeted validation; advisory warnings recorded.
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-09)

- stage: validate; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-3b5b2257 - Explain exact server TOML enrollment and review
  - REQ-UX-1cd0e743 - Suggest raw import identity from the TOML repository
  - REQ-DATA-71853fbc - Clear import draft when leaving the page
  - REQ-UX-34ca5d39 - Compact project settings with raw actions
- deviations: 1 recorded
  - validate: use targeted import/export API and Chromium proof, help checks and targeted lint rather than the full repository suites, per the user's standing preference.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base bb3141c: 71 file(s) changed, 1858 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=68 notes=24
- checklist: 8/9 done; open: `report` appended
