<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-3ca87e3e - Make complete project export a single save action

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-3534628b, REQ-UX-41c99cc5, REQ-REL-aa0c1685
parent:
branch: master
base: 1886c5cdfc2660ae77ef993adef04cf8848b3161
opened: 2026-11-11

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
- [x] final `check --strict --run` result logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem: STATED export currently requires technical choices and recipe uploads (user screenshot); OBSERVED RawConfiguration.tsx mixes export and recipe administration.
Desired outcome: STATED press Export, select destination and save the complete configuration/image-definition package.
Actors: OBSERVED authorized project administrator; developer access remains refused.
Primary scenario: STATED container export always includes the complete image sources; native export preserves exact TOML.
Examples: STATED missing base definition in the screenshot must not become a file-upload wizard during export.
Counterexamples: OBSERVED unavailable sources must not be guessed or an incomplete archive reported as complete (REQ-REL-aa0c1685).
In scope: INFERRED direct save action, native save picker where supported, ordinary browser download fallback, concise error dialog; preserve existing recipe management separately under closed Technical details.
Out of scope: OBSERVED backend source graph, security/storage schema and builds remain governed by existing contracts. Deployment/operational registration follows repository operations, outside this software task.
Constraints: STATED autopilot=true, no push; OBSERVED master is the current default branch; preserve existing uncommitted ticket alignment edits and unrelated task journal.
Success signals: INFERRED complete export needs one toolbar click plus browser destination selection; no app export wizard, checkbox or recipe-upload control; cancellation saves nothing; bad transports create no output; separate recipe management remains accessible.
Evidence: OBSERVED RawConfiguration.tsx, portable.spec.ts, project-images knowledge and REQ-UX-3534628b.
Assumptions: INFERRED existing browser download behavior remains fallback on browsers without a native save picker.
Unknowns: UNKNOWN arbitrary external image provenance remains unavailable unless registered; current DCP build sources found in its retained staging directory, requiring operator verification.
Decision-blocking questions: None; existing fail-closed and authorization contracts settle failure behavior.
Proposed behaviors: None outstanding.
Path and reason: Full: externally visible export flow changes; no new dependency or stored format; existing export/authorization contracts retained.

## Requirement coverage

| Requirement | Behavior | Design | Proof |
|---|---|---|---|
| REQ-UX-3534628b | Direct complete save, cancellation/failure boundaries | Native picker or download, no export wizard | portable browser suite |
| REQ-UX-41c99cc5 | Retain separate recipe management | Closed Technical details entry | portable recipe cases |
| REQ-REL-aa0c1685 | Missing sources refuse complete export | Existing backend unchanged; show error dialog | existing backend negatives + browser |

## Design

### Approach
REQ-UX-3534628b: keep RawConfiguration's two toolbar buttons; Export starts a save directly.
REQ-UX-41c99cc5: reuse the validated recipe dialog in a definitionOnly instance under closed Technical details.
### Interfaces and data
Export uses showSaveFilePicker in its click activation when supported, then the existing raw endpoint with include_build=true for containers. Otherwise use the existing Blob/download transport. Native projects save exact TOML. No new backend or persisted format.
Canceling a destination stops before fetch. Ref-based single-flight and generation guards protect pending picker/fetch/write results against duplicate clicks and account/project unmount. Abort an opened writable on error. Do not silently retry with a fallback after a picker error. REQ-REL-aa0c1685 remains authoritative: missing sources open an error dialog and produce no incomplete archive.
### Files and test seams
RawConfiguration.tsx handles browser save/preview and separate recipe mode; App.tsx mounts management in Technical details. portable.spec.ts covers both native-picker and download paths, cancellation, errors and management. Four-locale help/docs/notes explain one-click export and technical administration.
### Risks and open decisions
Browser save picker is optional; fallback uses the browser download preferences. No sources are inferred from image tags. Existing uncommitted ticket alignment is preserved and validated together, outside this task's implementation scope. No unresolved decision.
### Requirement map
REQ-UX-3534628b: direct picker/download, no app choices.
REQ-UX-41c99cc5: separate management entry using existing API and guards.
REQ-REL-aa0c1685: existing backend fail-closed errors; no change to source resolution.
Diagrams: [diagram_TASK-3ca87e3e.md](diagram_TASK-3ca87e3e.md)

## Log

- 2026-11-11 frame: journal opened
- 2026-11-11 frame: completed; next specify - User requests direct complete export; autopilot scope recorded (7 Done checklist item(s) left unticked)
- 2026-11-11 specify: completed; next design
- 2026-11-11 design: completed; next build
- 2026-11-11 build: red: Chromium one-click export test failed because the old app opens an export wizard instead of invoking the browser destination picker (REQ-UX-3534628b)
- 2026-11-11 build: release-notes: updated (direct complete export and separate technical definition management in four locales)
- 2026-11-11 build: help: updated (Settings export and separate source management in all four locales)
- 2026-11-11 build: green: Chromium portable and ticket layout focused tests exit 0, 23 passed; backend recipe/raw contracts exit 0, 72 passed; help 11 passed (REQ-UX-3534628b, REQ-UX-41c99cc5, REQ-REL-aa0c1685)
- 2026-11-11 build: Operational acceptance outside product workflow: registered exact DCP b73dae3 base sources after byte comparison with original Git revision; VERA complete export contains config plus Dockerfile, license, Pi guard/helper and Compose; all profile config hashes unchanged.
- 2026-11-11 build: Build warnings reviewed: source-no-test-changes is a layout heuristic excluding web/e2e; portable.spec.ts and tickets.spec.ts are exercised. Existing stale-path/ticket-ref metadata and minified asset findings remain advisory; no product behavior or validation weakened.
- 2026-11-11 build: completed; next validate
- 2026-11-11 validate: Final strict proof bounded to one run and 45 minutes wall time; candidate files frozen after independent round-1 approvals. Existing ticket right-alignment changes are included in integration proof; unrelated TASK-b8a190d4 remains untouched.
- 2026-11-11 validate: Full strict run exit 1: Python passed (782.3s), Ruff passed (0.2s), frontend unit checks ran and Chromium finished 268 passed / 1 failed (1235.4s). Only failure is existing Overview corrupt-state case with net::ERR_NO_BUFFER_SPACE in browser trace; current RAM/TCP checks normal, no orphan headless processes. Candidate unchanged; rerunning both corrupt-state variants three times in fresh workers to verify transient host/browser failure.
- 2026-11-11 validate: DEVIATION validate: final proof is segmented after one transient Chromium ERR_NO_BUFFER_SPACE in the full invocation. Full Python and Ruff passed; 268 other Chromium cases passed; both affected Overview variants passed three repeats each (6/6) in fresh workers, exit 0. No source/test changes, no retries enabled or assertions weakened; all configured behavior coverage retained. Original strict --run remains truthfully exit 1.
- 2026-11-11 validate: final: segmented proof on frozen reviewed candidate: full Python exit0 (782.3s), Ruff exit0 (0.2s), frontend full run 268 passed/one Chromium resource failure, exact affected Overview variants rerun6/6 exit0 (35.3s), final static strict check exit0. Focused export/layout23 and recipe72 also exit0. The original full strict invocation exit1 is retained; 38 advisory metadata/layout/minified-scan warnings and24 notes remain, unrelated to product correctness.
- 2026-11-11 validate: completed; next done

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-3ca87e3e.md
changed: Direct complete export, separate technical recipe management, localized save failures and help
evidence: Segmented final proof: full Python/Ruff passed; 268 web cases plus affected case repeated6/6; static strict exit0
issues: Original full strict run exit1 from transient Chromium buffer error; resolved by isolated reruns, recorded deviation
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-11-11)

- stage: validate; type: change; path: full; branch: master
- requirements:
  - REQ-UX-3534628b - Manage executor recipes through a compact project dialog
  - REQ-UX-41c99cc5 - Keep recipe administration outside project export
  - REQ-REL-aa0c1685 - Keep incomplete local image chains out of project exports
- deviations: 1 recorded
  - validate: final proof is segmented after one transient Chromium ERR_NO_BUFFER_SPACE in the full invocation. Full Python and Ruff passed; 268 other Chromium cases passed; both affected Overview variants passed three repeats each (6/6) in fresh workers, exit 0. No source/test changes, no retries enabled or assertions weakened; all configured behavior coverage retained. Original strict --run remains truthfully exit 1.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 1886c5c: 36 file(s) changed, 658 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=38 notes=24
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
