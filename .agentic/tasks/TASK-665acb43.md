<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-665acb43 - Keep executor editors in their rows and select credential names from a dropdown

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-UX-646e81fb, REQ-FUNC-c829c366, REQ-FUNC-08cc2676
parent:
branch: task/adore-web-interface
base: 1ce557fedb0e10ea37dd035874f6d2cc8aec8d69
opened: 2026-10-09

## Done checklist (current stage)

- [x] semantic scope/design/security review; component/context/requirements reconciled
- [x] stable columns, atomic candidate, cancel, dropdown/roles/locales/mobile inspected through browser tests
- [x] final evolution and strict scoped catalog recorded
- [x] delivery evidence and unchanged candidate confirmed
- [x] authorized DCP deployment verified and closeout recorded

## Frame

Problem: STATED Edit default agent changes the entire visible layout; credential checkbox grid is confusing.
Desired outcome: Preserve existing two-column rows during complete agent editing; use a compact multi-value dropdown.
Actors: Admin editor; Dev informational view; external administrator owns runtime setup.
Primary scenario: Edit default agent -> fields become controls inside their own rows -> prepare complete existing candidate -> review/apply or cancel.
Examples: selecting Codex changes values in the current command/model rows, not their placement; add/remove OpenRouter through the credential dropdown.
Counterexamples: incomplete model disables Prepare; cancelling restores active values; a Dev sees no controls.
In scope: inline grouped editor, dropdown plus removable chosen names, four locales, scoped browser proof, docs and established DCP delivery.
Out of scope: backend/config API changes, automatic runtime/agent setup or bringing local/container controls back to GUI.
Constraints: existing atomic review, presets/custom/native behavior and private values preserved; targeted tests only.
Success signals: row column geometry stable before/during Edit; no duplicated fields or checkbox grid; complete review and safe cancel.
Evidence: STATED user corrections; OBSERVED App.tsx combined default editor and styles.css full-row override, ExecutorSelectionEditor and credential name JSON contract.
Assumptions: dropdown adds multiple names individually and chosen names remain visible/removable.
Unknowns: none decision-blocking.
Decision-blocking questions: none.
Path and reason: full; observable editor interactions change, no new API/schema/dependency/security behavior. Layout change=no-new-behavior(no); new-data-format=no(yes); no-new-dependency=yes; existing-requirement=yes; data/security-contract-change=no(yes).

## Requirement coverage

REQ-UX-646e81fb: stable category/inline row layout and compact credential dropdown, role/locale/mobile browser proof.
REQ-FUNC-c829c366 / REQ-FUNC-08cc2676: existing complete candidate and names-only authority retained; scoped regression reused.

## Design

ExecutorSelectionEditor renders one field specified by agent/command/model. SettingsList keeps one complete JSON draft and displays the command/model draft controls inside their existing selected-agent rows while the default row owns Prepare/Cancel. Columns and labels retain normal layout; candidate continues to be executor.selection. CredentialNamesEditor uses native select with already-chosen options disabled and removable chosen-name list. Existing validCredentialNames and server metadata remain authoritative. No backend changes. External execution backend remains server TOML as requested previously. No child agents. BMAD renderer and sibling setup skill remain absent; repository AEGIS fallback retained.

## Log

- 2026-10-09 frame: user correction accepted; GUI-only scope, unchanged external execution backend and reviewed APIs.

- 2026-10-09 frame/specify/design: correction scope accepted, existing UX requirement extended; full path/autopilot and unchanged external backend ownership recorded.

- 2026-10-09 build red: command=npx playwright test executor-config.spec.ts --grep "inline executor editors"; exit1; expected row geometry failure: default-agent editor moves458px left because it spans both columns.


- 2026-10-09 validate review round1: specification compliance approved (requested layout/dropdown, external backend exclusion, atomic/name-only requirements); implementation quality approved (normal two-column CSS, complete shared draft, custom presets, strict guards, no secrets/backend changes, role/locale/mobile/cancel checks). Architecture retains existing config candidate and private credential boundaries; new dropdown component changes only field rendering.
- 2026-10-09 DEVIATION validate: user defers full suite until overall settings review ends; scoped frontend build/typecheck, executor Chromium scenarios and settings/routes contracts substitute. No Python backend change; repository-wide integration is not re-proven here.


- 2026-10-09 final validation: npm build:e2e/typecheck exit0; initial7 Chromium scenarios passed22.7s; strengthened multiple-name test initially selected an already-present Anthropic option (correctly disabled); corrected fixture choice to Gemini, final affected scenario passed6.3s and unchanged other6passed. Node settings/routes28passed; git diff --check exit0. Evolution refreshed17:38:59Z includes all10non-agentic paths; semantic/traceability review and both independent round1 verdicts refreshed after final fixture edit. Strict catalog exit0 errors0/warnings11/notes25:10existing catalog/journal/fingerprint findings plus source-no-test heuristic because Playwright files are outside configured test globs; actual browser tests changed and ran. Existing Vite large-chunk warning accepted, no bundling change. Fullsuite substitution recorded above.
- 2026-10-09 deliver: concrete requested UI corrections, scoped proof and preserved config outcome presented; standing user authorization for implementation/local commits/DCP deployment retained. No push/PR/merge.


- 2026-10-09 delivered: product commit48f71bb55ddb899cbec1244cf668ed84a59eee8f installed at /home/dpasare/apps/adore/dcp-inline-665acb43/04_Software; package81116f64265306a6f8817e42c16a0007257703756df45a4cd6207280a63af944 and fresh JSfd034741f0c497e6367263d4a6f13f99b4a913f957572707e75e043af565071c/CSS07db7c7c397bd2fdcd52fe77b4da5d294a3e9a36b54e70a6c3a22f0ff732027c verified DCP and LAN. Server/worker active and ready; schema14/users1/audit106/operations2failed16succeeded preserved, all6config/pause/run-state inventories identical. Existing TLS certificate pin and protected401 routes preserved. Live user aegis Settings: default-agent value/editor geometry exactly x890.400,width548.800 before/after; Pi command/model preserved in own rows. Authentication names-only dropdown add/remove OpenRouter verified then Cancel, active list remains[]; no API-key/model-test/config mutation. Screenshots live-agent-edit.png and live-dropdown.png saved and visually inspected; user tab retained. Own temporary backup removed after exact receipt/service/path checks; backups directory empty. SSH/SCP closed. Ignored receipts in07_Delivery/adore-polling-a224af5d/inline-665acb43/{package-summary,deployment-result,lan-smoke,backup-cleanup}.json.
- 2026-10-09 closeout: authorized UI correction and test-server deployment complete. Delivery-report warning12 included unfinished deployment checklist then in progress; final scoped catalog before commit had11warnings, with10pre-existing plus Playwright test-glob heuristic explained above. Fullsuite remains deferred by user.

## Rulings


- RULING-001 | date=2026-10-09 | decision=Implement requested UI corrections through existing reviewed contracts and established DCP delivery | reason=User requested layout and dropdown correction in deployed GUI; earlier explicit deployment authorization persists | source=user | supersedes=none

## Handoff


current: done
status: ready
next: none; authorized DCP deployment verified
must_read: task journal, linked requirements, executor-configuration/web-interface knowledge
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: normal row editors; dropdown/removable names; four-locale copy, browser tests and docs
evidence: targeted7Chromium/28Node, build/typecheck, strict scoped catalog, exact DCP/LAN assets and live browser proof; preserved6profiles and backup cleanup receipts in Log
issues: full suite deferred per user; existing catalog findings and Vite chunk warning
next: none; closeout complete
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-09)

- stage: deliver; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-646e81fb - Unified executor configuration workspace
  - REQ-FUNC-c829c366 - Reviewed coding agent selection includes command and model atomically
  - REQ-FUNC-08cc2676 - Reviewed provider variable selection preserves private credentials
- deviations: 1 recorded
  - validate: user defers full suite until overall settings review ends; scoped frontend build/typecheck, executor Chromium scenarios and settings/routes contracts substitute. No Python backend change; repository-wide integration is not re-proven here.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 1ce557f: 17 file(s) changed, 240 line(s) added
- checks: errors=0 warnings=12 notes=25
- checklist: 4/5 done; open: authorized DCP deployment verified and closeout recorded
