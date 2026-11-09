<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-fa033d20 - Edit clarification recovery and stage timeouts in Implementation

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-d67a1d33, REQ-FUNC-c6c694cc, REQ-UX-66547cbf
parent:
branch: task/adore-web-interface
base: eb9a5ae19b1d1625ddfe783f37b9bd421421c82b
opened: 2026-10-09

## Done checklist (current stage)

- [x] Final candidate verified and reviewed; standing delivery approval recorded
- [x] Delivery report and local candidate commit
- [x] DCP services/TLS/assets/profile preservation verified
- [x] Own temporary backup cleanup and close-out commit

## Frame

Problem: STATED useful Implementation settings are read-only because clarification is excluded and lists/maps have no editor.
Desired outcome: STATED implement the recommended editors and independent answer duration; preserve existing recovery semantics.
Actors: Admin and scoped Dev, four supported locales, CLI operators.
Primary scenario: Expand topic -> edit typed setting -> prepare exact candidate -> review -> apply at idle boundary.
Examples: 12h answer timeout; delays 5/30/120; build 5400 with other stages using general timeout; remove build override.
Counterexamples: Broad map/list edit authority, malformed JSON, changing unrelated config, hidden reserved controls becoming editable.
In scope: Two clarification controls, retry list and complete stage map, independent positive duration validation, localized UX/docs, targeted tests, local commit and standing DCP test delivery.
Out of scope: Cost/file enforcement, recovery counts/defaults changes, full suite, dependencies, push/PR/merge, reminder implementation.
Constraints: 90 minutes, 32 tracked files, no children; preserve DCP profiles/state/TLS; only own temporary backup cleanup.
Success signals: Four supported controls edit/review/apply; malformed values fail closed; config unrelated values retained; Dev remains read-only; 12h accepted.
Evidence: OBSERVED app.py scalar catalog/edit contract excludes clarification; settings.ts limits editors to scalar/reviewer types; config.py compares reserved reminder with answer duration; orchestrator uses existing values.
Assumptions: INFERRED six-row map editor should review one complete timeout mapping to allow both adding and removing overrides.
Unknowns: Unsupported human TOML spellings fail explicitly after semantic preservation checks.
Decision-blocking questions: none.
Proposed behaviors: Add narrow typed collection authority and localized controls under current review gates; remove reserved reminder ordering only.
Path and reason: Full; new typed collection editing and duration validation behavior. Existing branch reused; prior BMAD build renderer was unavailable and repository AEGIS fallback remains authorized.

## Requirement coverage

| Outcome | Requirement | Positive | Boundary | Design |
|---|---|---|---|---|
| Exact reviewed API edits | REQ-FUNC-d67a1d33 | Scalars/list/map prepare/apply | Types, corrupt pending, unrelated fields, roles | Narrow validators and exact collection writer |
| Independent duration | REQ-FUNC-c6c694cc | 12h under reserved 24h | Zero or malformed duration | Positive answer check; reminder format retained |
| Usable localized editors | REQ-UX-66547cbf | Duration/unit, delay lines, six-stage choices | Bad draft/pending, Dev, review/cancel | Existing single-editor state and candidate flow |

## Design

REQ-FUNC-d67a1d33: API allow only two active clarification keys; typed collection exceptions only recovery.retry_backoff_seconds and workflow.stage_timeout_overrides. JSON wire values remain strings; strict parsing rejects duplicates, booleans-as-integers, invalid stage names, empty schedule, negative delays and nonpositive overrides. Stage mapping may be empty. Metadata emits one parent timeout-map row even when nonempty; retain legacy scalar stage readers. Writer handles missing, inline and nested table settings, multiline list/quoted keys; compare parsed full configuration to expected single-value update, fail closed on unsupported spellings. Preserve line endings and unrelated lines. Pending review serializes arrays/maps as canonical JSON and binds exact value. Existing locks/CSRF/role/revision/idle rules remain.
REQ-FUNC-c6c694cc: Remove reminder ordering, retain duration-format checks and positive answer timeout. Executor/recovery code unchanged.
REQ-UX-66547cbf: Shared helper/copy parses duration value/unit and integer retry lines, validates exact collection transport and supplies six stages. Extend existing editor input kinds with duration, retry-delays, stage-timeouts; all six timeout rows have general/custom choices. Existing prepare/apply/discard keeps one candidate. Four-locale names/help explain runtime effects. Numeric stage inputs wrap on mobile. No architecture boundary or new dependency.
Tests: Public config/API positive and trust-negative cases first; helper contract tests then browser journey, existing stage/clarification and config regressions targeted only.

## Log

- 2026-10-09 frame: Approved recommendation and standing autonomous local/DCP delivery, bounded full path; no children, targeted tests only. Prior BMAD renderer fallback reused.
- 2026-10-09 specify: Three atomic requirements cover reviewed API editing, independent duration and localized typed editors, with trust-boundary verification.
- 2026-10-09 design: Narrow list/map contract, single timeout-map review and semantic TOML preservation; existing approval/redaction/idle architecture retained.

- 2026-10-09 build red: REQ-FUNC-d67a1d33 and REQ-FUNC-c6c694cc; command=`python -m pytest -q 04_Software/tests/test_config.py::test_validation_accepts_answer_timeout_independently_of_reserved_reminder 04_Software/tests/test_web_pending_config.py -k "independently_of_reserved_reminder or implementation_settings_review or stage_timeout_map_handles" --tb=short`; exit=1; nine expected failures: clarification blocked, collection metadata/read/apply unsupported and reserved reminder ordering rejects 12h.

- 2026-10-09 build: REQ-FUNC-d67a1d33/c6c694cc focused typed API/config tests passed 24, including corrupt pending and four TOML shapes. Existing recovery execution unchanged.
- 2026-10-09 build red: REQ-UX-66547cbf; command=`node --experimental-strip-types --test 04_Software/web/tests/settings.test.mjs`; exit=1; expected missing behavior=duration/list/map controls resolve as text/none/none instead of the three typed editor kinds. Initial repository anchor precedes this implementation.

- 2026-10-09 build: Backend config/catalog/pending regression files passed 145 (one existing Starlette warning), settings helpers passed 17, targeted conductor clarification/timeout/transient tests passed 8, Ruff passed, frontend typecheck/build passed. Browser first exposed populated-map editor initialization as generic object text; fixed structured editValue and added populated-map contract assertion. Corrected typed Implementation browser journeys passed 2 including 390px add/remove and Dev read-only. Earlier unchanged locale/category/review journeys passed 4. Documentation and active requirement links reconciled.
- 2026-10-09 build complete: Narrow scalar/collection authority, duplicate/type/safe integer/TOML/corrupt-pending/role/revision/CSRF boundaries implemented; unchanged-base collection candidate verifies no unrelated edits. No recovery counter/default/enforcement changes.

- 2026-10-09 validate round 1 specification compliance: approved; exact approved controls, defaults/enforcement exclusions, map add/remove, four locales, reviewed Admin/Dev boundaries match all three active requirements. Requirement/spec paths and linked tests reread; no open decisions or children.
- 2026-10-09 validate round 1 implementation quality: approved; semantic diff review covers typed strict JSON, safe integer domains, unsupported TOML fail-closed, full single-value preservation, persisted unchanged-base binding, role/CSRF/revision/idle authority, populated-map reopen, mobile wrap and offline transport. Existing API/UI architecture boundaries retained; new helpers route through existing SettingsList and config candidate flow. Context/knowledge/docs reconciled; environment/dependencies unchanged.
- 2026-10-09 DEVIATION validate: standing user instruction defers the full suite; substitute scoped config/pending/catalog/conductor/helper/browser proof, typecheck/build/Ruff and strict catalog without --run. Unrelated product paths and full-suite integration remain unverified. Existing Starlette/Node color/chunk-size warnings accepted without dependency/build scope expansion.

- 2026-10-09 final validate: All commands exit 0. `python -m pytest -q tests/test_web_pending_config.py tests/test_config.py -k "implementation_setting or implementation_collection or stage_timeout_map or independently_of_reserved_reminder" --tb=short` from repository-adjusted paths: 28 passed/88 deselected. Broader focused regression earlier: pending/config/catalog files 145 passed; conductor clarification/timeout/transient 8 passed/99 deselected. `node --experimental-strip-types --test 04_Software/web/tests/settings.test.mjs`: 17 passed. `npx playwright test e2e/settings.spec.ts --grep "typed Implementation|purpose guidance|Git flow categories"`: 6 passed, including four locales, exact apply/add/remove, mobile and Dev. `npm --prefix 04_Software/web run build:e2e`: typecheck/build/stamp passed. Scoped Ruff: passed. `aegis check --task TASK-fa033d20 --strict` without --run: strict ok, 0 errors/10 unrelated existing warnings/25 historical manual notes. The warnings are old stale paths, tracked fingerprints and old journal headers; new candidate coverage warnings resolved. User-forbidden full-suite proof was not run.
- 2026-10-09 final review: Both verdicts approved for final source/test/requirement/docs candidate after traceability reconciliation. Evolution lists exactly 20 non-agentic files, no removals, all agreed code/tests/docs; 29 total tracked candidate paths within 32-file bound. No new dependencies, executor/conductor enforcement changes, secrets or children.
- 2026-10-09 deliver authorization: User approval and standing session instruction authorize local commit and replacement of DCP test instance; no redundant checkpoint, push, PR or merge. Candidate includes the four typed editors, independent deadline validation, narrow integrity enforcement, focused tests and current docs. Temporary deployment backup is removed after verified success; six profile configs/state/TLS remain unchanged.

- 2026-10-09 delivery inspection: Candidate 5a6054584c4f69a24036cdc53a8c0e394f1b11dc deployed with healthy services, identical six-profile config/state inventory and pinned TLS/asset LAN proof. Live editor screenshot exposed inherited `.setting-editor input/select` flex basis expanding controls vertically inside column labels and placing action buttons beside the stage stack. Own temporary backup cleanup succeeded, backups root empty. Return to build for this in-scope visual defect; add bounded control-height/action-placement regression, scoped CSS correction and repeat DCP delivery. Verdicts cleared pending revalidation.

- 2026-10-09 build red REQ-UX-66547cbf: `npx playwright test e2e/settings.spec.ts --grep "typed Implementation controls review"`; exit=1; expected missing behavior=duration control height is 192px, exceeding normal 60px bound. Added desktop/mobile stage control-height and action-below-stack assertions; original task anchor remains the full-change baseline.

- 2026-10-09 validate round 2: Scoped CSS resets inherited horizontal flex basis for nested column controls, full-width typed groups place actions below the stack; added desktop/mobile height/placement regressions. Component/knowledge/requirement prose reconciled. Spec compliance and implementation quality independently approved for this bounded correction; no other source or runtime behavior changed. Original source/API/conductor/helper proof retained; focused layout browser/typecheck/build and strict catalog cover the new candidate.

- 2026-10-09 final layout validate: `npm --prefix 04_Software/web run build:e2e` exit 0 (typecheck/build/stamp); `npx playwright test e2e/settings.spec.ts --grep "typed Implementation"` exit 0, 2 passed, now asserts duration normal height, all six stage controls <=60px and action below final stage at 1280/390px. Strict catalog exit 0, 0 errors/10 existing warnings/25 historical notes; no full suite. Only scoped CSS/test/prose changed from proven product candidate. Round 2 verdicts approved, final evolution reviewed. Proceed under existing local/DCP authorization.

- 2026-10-09 final delivery outcome: Corrected product commit 8121dd888b24773cb938c33102ae48959a80ec6e deployed to /home/dpasare/apps/adore/dcp-implementation-fa033d20-layout/04_Software. Package SHA256 abc66631edb948de0983f8f71a4e3f856d322e25e8b6a0e9a32025a49ea1642b; index-Meczuws2.js SHA256 ba635139b4fef67802aca0006d7d4a832e6d71105e650edc00cded822099d5dd; index-DteeiVrM.css SHA256 549c178426c056d630ed7a853cb5a92848a7c7d2707374343e0a87b4ac299fd0. LAN JS/CSS bytes match and pinned original TLS certificate is retained; public/health/ready routes 200, protected APIs 401, web/worker ready. Six config/pause/run-state hashes, schema14/user1/audit106/18 terminal operations retained; no config writes.
- 2026-10-09 live visual acceptance: Authenticated aegis Settings/Implementation exposes all four new editors. Duration amount/unit and six-row retry field inspected without prepare/apply on live config; all six stage selectors are 42px high with actions below, full-stage screenshot saved under 07_Delivery/adore-polling-a224af5d/implementation-fa033d20-layout/live-stage-editor.png. Browser remains marked deliverable on unchanged stage draft; offline disposable tests proved exact application. Final deployment-result/backup-cleanup/lan-smoke receipts inspected locally; owned temporary backup removed and backups directory empty. SSH/SCP sessions closed, no push/PR/merge. Journal-only close-out follows; full suite remains deferred.

## Rulings

- RULING-001 | date=2026-10-09 | decision=Implement recommended editors and independent answer duration, targeted proof and standing local/DCP delivery | reason=User approval plus session delivery/test authority | source=user | supersedes=none

## Handoff

current: done
status: ready
next: none
must_read: .agentic/specs/implementation-settings.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Typed Implementation settings and normal-height editors deployed on DCP
evidence: 145 API/config regressions, 8 conductor, 17 helpers, 6 browser plus 2 layout journeys; build/Ruff/strict catalog; JS/CSS LAN match and live screenshot
issues: Full suite deferred by user; existing dependency/build/catalog advisories
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-09)

- stage: deliver; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-d67a1d33 - Reviewed clarification and recovery collection settings
  - REQ-FUNC-c6c694cc - Independent positive clarification answer duration
  - REQ-UX-66547cbf - Human duration retry schedule and six-stage timeout editors
- deviations: 1 recorded
  - validate: standing user instruction defers the full suite; substitute scoped config/pending/catalog/conductor/helper/browser proof, typecheck/build/Ruff and strict catalog without --run. Unrelated product paths and full-suite integration remain unverified. Existing Starlette/Node color/chunk-size warnings accepted without dependency/build scope expansion.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base eb9a5ae: 29 file(s) changed, 810 line(s) added
- checks: errors=0 warnings=11 notes=25
- checklist: 1/4 done; open: Delivery report and local candidate commit; DCP services/TLS/assets/profile preservation verified; Own temporary backup cleanup and close-out commit

## Delivery report (2026-10-09)

- stage: deliver; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-d67a1d33 - Reviewed clarification and recovery collection settings
  - REQ-FUNC-c6c694cc - Independent positive clarification answer duration
  - REQ-UX-66547cbf - Human duration retry schedule and six-stage timeout editors
- deviations: 1 recorded
  - validate: standing user instruction defers the full suite; substitute scoped config/pending/catalog/conductor/helper/browser proof, typecheck/build/Ruff and strict catalog without --run. Unrelated product paths and full-suite integration remain unverified. Existing Starlette/Node color/chunk-size warnings accepted without dependency/build scope expansion.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base eb9a5ae: 29 file(s) changed, 843 line(s) added
- checks: errors=0 warnings=11 notes=25
- checklist: 2/4 done; open: DCP services/TLS/assets/profile preservation verified; Own temporary backup cleanup and close-out commit
