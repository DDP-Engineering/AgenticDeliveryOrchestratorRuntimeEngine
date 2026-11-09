<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-418bc3f2 - Improve project details text readability

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-UX-67a66456
parent:
branch: task/adore-web-interface
base: 2012f2544847bbae01fafbe33ccd35393890582b
opened: 2026-10-01

## Done checklist (current stage)

- [x] Scope, requirement, implementation, visual evidence and docs complete.
- [x] Final candidate review and canonical verification complete.
- [x] Deploy and verify live DCP frontend.
- [x] Delivery close-out commit includes verified candidate; installed revision recorded on DCP.

## Frame

Problem: STATED project details text is not visible/readable in the supplied screenshot.
Desired outcome: Clearly readable metadata, descriptions and expanded settings/help.
Actors: Administrators and assigned developers.
Primary scenario: Open details and expand configuration groups/help; read metadata, domain and values at desktop and phone widths.
Examples: Host prerequisites explanation and project settings description; long repository identifiers.
Counterexamples: Text clipped by a narrow viewport; light text on light surfaces; dark theme regression.
In scope: Shared secondary colour, project metadata and field/settings help typography, wrapping, documentation and DCP frontend deployment.
Out of scope: Configuration data, permissions, live repository/job mutations and layout/navigation redesign.
Constraints: Keep compact collapsible groups; preserve all existing configuration and RBAC contracts.
Success signals: Metadata/help at least 14px at normal root size; stronger contrast in light/dark themes; narrow text wraps.
Evidence: STATED screenshot; OBSERVED styles.css and local computed CSS show 11.84px metadata and #64736d secondary colour; INFERRED small/faint rendering explains the reported issue.
Assumptions: Standing autonomous implementation, commit and DCP deployment authorization applies.
Unknowns: User display scaling; verify normal and narrow effective viewport.
Decision-blocking questions: None.
Proposed behaviors: Darker light-theme secondary text, lighter dark-theme secondary text, metadata/settings hints and values at 0.875rem with 1.5 line height and wrapping.
Path and reason: Full path for explicit readability contract. Existing interface/data/dependency/security contracts remain unchanged; new visible typography/requirement selects full path. Small tightly coupled change needs no child tasks.

## Requirement coverage

- REQ-UX-67a66456: Readable secondary text, metadata, settings values and field help across themes and viewport sizes.

## Design

Use shared muted theme tokens for a consistent secondary colour on all surfaces. Raise project-meta, field-hint, guided-help, setting-row small/code/help and setting-editor-help to 0.875rem, with regular 400 weight and 1.5 line-height for paragraph/metadata guidance. Keep base 16px descriptions and desktop grid behavior; at narrow widths stack labels, values and help so an expanded description cannot squeeze the key column. Add overflow wrapping to metadata/help so long identifiers fit phones. Manual browser validation is appropriate for CSS presentation; existing full offline suite remains required. No data or trust-boundary behavior changes.

## Log

- 2026-10-01 frame/specify/design: Scope follows reported faint text; local computed metadata is 11.84px and descriptions use #64736d. Full path, manual visual requirement and standing autonomous delivery selected. Theme preferences will be exercised only in disposable local QA; live DCP checks are read-only.

- 2026-10-01 build: Manual requirement; no mirrored CSS unit test. Production build passed. Secondary contrast measured 7.28:1 on white, 6.70:1 on light page, 8.86:1 on dark panel and 7.92:1 on dark alternate surface. Metadata and settings key/value/help are 14px with 21px line-height. Desktop expanded help and 390px light/dark settings inspected; long saved state path wraps, expanded help stacks, no selected text overflow or page horizontal overflow. Disposable theme restored to system; browser viewport reset and QA tab closed.

- 2026-10-01 validate: Whole journal/requirement/docs and CSS/static evolution reviewed; diff whitespace check passed. Final `check --task TASK-418bc3f2 --strict --run` exit 0: offline suite 47.7s, lint 0.1s and seven frontend tests 0.2s, zero errors. Seven advisories cover intentionally manual CSS verification/no mirrored tests, generated-asset coverage/scanning and unrelated older sidecars/ruling metadata. No new trust-boundary behavior or accepted material deviation.
- 2026-10-01 deliver: Standing user authorization covers commit and real DCP deployment. Validated static archive SHA-256 202353bc85e41f332775bc086038434b7ddcd535ebb1f44f0247933b45212d8e; candidate is CSS, documentation, bundled assets and task/requirement. Prior installed frontend will be retained for rollback.

- 2026-10-01 deliver: Archive hash verified; DCP static assets installed with rollback `static.pre-text-readability-20261001`. UI, both JS/CSS assets, health/readiness return HTTP 200; API/worker remain active. Read-only live aegis details confirms 14px metadata in #475b52 and stylesheet index-CCqm205-.css. Proof screenshot saved as `C:/Users/dpasare/AppData/Local/Temp/adore-text-readability-dcp-20261001.png`; browser QA tabs closed. Live profiles/configuration/jobs remain unchanged by this deployment. Delivery close-out commit follows verified deployment.

## Rulings

## Handoff

current: done
status: ready
next: None; implementation and deployment complete.
must_read: 04_Software/web/src/styles.css
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Readable theme colours, metadata/settings help, narrow stacking and docs/bundled assets.
evidence: Build, GUI and canonical checks pass; DCP UI/assets/health/readiness HTTP 200, both services active and live 14px metadata verified.
issues: Seven advisory findings explained in Log; no material deviation.
next: None.
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

## Delivery report (2026-10-01)

- stage: done; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-67a66456 - Readable secondary text and project configuration guidance
- deviations: none recorded
- explicit review: disabled; existing validation remains required
- diff vs task base 2012f25: 12 file(s) changed, 162 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=7 notes=15
- checklist: 4/4 done
