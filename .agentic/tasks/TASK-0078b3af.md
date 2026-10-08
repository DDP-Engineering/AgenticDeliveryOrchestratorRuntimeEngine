<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-0078b3af - Clarify target branch setting labels and guidance

stage: deliver
type: change
path: quick
interaction: autopilot
requirements: REQ-UX-2bea4ff1
parent:
branch: task/adore-web-interface
base: 144b49dff9af314075ebb948ecbce563aa059eac
opened: 2026-10-08

## Done checklist (current stage)

- [x] Validated candidate unchanged and delivery scope presented
- [x] Standing human authority for local commit/DCP replacement recorded
- [ ] Source commit and delivery report
- [ ] DCP replacement and live inspection
- [ ] Close-out

## Frame

Problem: STATED user accepts clearer target branch label; OBSERVED English label says Human review target branch while it controls worktree base and PR/MR target.
Desired outcome: Display Target branch / Ramura de integrare consistently in row, editor and candidate preview, with explicit plain branch-name guidance.
Actors: Project operator, read-only developer, web settings.
Primary scenario: Operator opens Rules and approvals -> sees Target branch and its dual purpose -> edits through existing reviewed scalar flow.
Examples: main -> start from origin/main, PR/MR into main; Romanian label Ramura de integrare.
Counterexamples: UI wording does not change configured branch, existing PRs, forge behavior or human merge authority.
In scope: Four-locale labels/help and directly affected user/component documentation.
Out of scope: Runtime behavior, validation, persisted state/config changes, new tests for low-impact copy.
Constraints: 40 minutes, 15 tracked files; targeted verification only; standing autonomous local commit/DCP test replacement authority, no push/PR or children.
Success signals: Consistent localized labels, help names both effects and short branch format; preserved runtime configuration on DCP.
Evidence: STATED recommendation approved; OBSERVED App.tsx settings/candidate labels, settingsCopy.ts, settingHelp.ts; orchestrator.py new-run base_ref and open_merge_request target.
Assumptions: INFERRED simple wording fits existing text input/layout.
Unknowns: Remote branch existence remains runtime/forge owned.
Decision-blocking questions: None.
Proposed behaviors: Presentation only, preserve delivery.target_branch contract.
Path and reason: Quick. Criteria all yes: existing settings requirement covers understandable copy; no new executable behavior, interface/data format, dependency or security/data behavior. No children.

## Requirement coverage

REQ-UX-2bea4ff1: existing purpose-based understandable labels/help; Inspection: four-locale copy, row/editor/candidate wiring and live displayed target/value. Existing settings helper tests cover unchanged editing boundaries.

## Design

Localized targetBranchCopy follows existing reviewer/publication copy pattern; same label used in settings row and review. Existing scalar editor, key, defaults and conductor unchanged. Architecture/context unchanged.

## Log

- 2026-10-08 validate final: Node settings.test.mjs exit=0 (11 passed); npm run build:e2e exit=0 (TypeScript/UI/E2E and isolated Vite build); focused Chromium settings -g "purpose guidance and single-setting flow preserve four locales|purpose guidance, correction" exit=0 (2 passed). git diff --check clean. Strict catalog exit=0, 0 errors/10 warnings/25 notes: 9 historical warnings plus source-no-test-changes for intentionally low-impact copy; existing tests and inspection used under developer instruction against redundant new tests. Existing chunk-size warning retained. Evolution accounts for seven product/doc files; AEGIS knowledge/requirement/task records additionally reviewed. Full suite deferred.
- 2026-10-08 deliver: Concrete candidate is three frontend presentation files, four direct docs/changelog files, existing UX requirement/knowledge updates and one task journal. Human approved recommendation and standing commit/DCP test replacement; no runtime/config values or existing PRs change, no push/PR. Both current review verdicts approved.

- 2026-10-08 build: Anchor at base recorded before edits. Inspection: four labels/help entries and shared row/editor/review label wiring describe the existing target contract. Existing settings helper tests 11 passed; TypeScript and isolated Vite build passed. Documentation and existing requirement path links updated; no runtime/config schema changes.
- 2026-10-08 DEVIATION validate: Full suite deferred by standing user instruction; substitute existing targeted helper/browser tests, TypeScript/build, presentation inspection and strict catalog. Full engine integration suite remains unexecuted for this copy change.
- 2026-10-08 validate review: Specification compliance approved: exact accepted labels and dual-purpose help, no scope expansion. Implementation quality independently assessed and approved round 1: established locale-copy pattern, same label in three surfaces, scalar contract unchanged. Architecture and project/environment responsibilities unchanged.

- 2026-10-08 frame: User approved recommendation; quick path for copy only under existing REQ-UX-2bea4ff1. Standing autonomous commit/DCP deployment and targeted-only verification retained. No new tests for low-impact wording; inspect presentation and run existing focused checks.

## Rulings

## Handoff

current: deliver
status: ready
next: Commit and replace DCP test instance
must_read: .agentic/requirements/ux/REQ-UX-2bea4ff1.toml
blockers: none

## Stage report

stage: validate
result: completed
current: deliver
changed: Four-locale target branch labels/help and direct docs
evidence: 11 settings helper tests, 2 Chromium journeys, TypeScript/build and strict catalog passed
issues: Full suite deferred by user; nine historical catalog warnings and copy-only no-test-change warning
next: Commit and replace DCP test instance
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-08)

- stage: deliver; type: change; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-UX-2bea4ff1 - Purpose-based catalog settings presentation
- deviations: 1 recorded
  - validate: Full suite deferred by standing user instruction; substitute existing targeted helper/browser tests, TypeScript/build, presentation inspection and strict catalog. Full engine integration suite remains unexecuted for this copy change.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 144b49d: 10 file(s) changed, 118 line(s) added
- checks: errors=0 warnings=11 notes=25
- checklist: 2/5 done; open: Source commit and delivery report; DCP replacement and live inspection; Close-out
