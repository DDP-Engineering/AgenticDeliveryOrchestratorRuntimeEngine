<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-fec704e8 - Simplify host folder selection to an OS-style chooser

stage: build
type: change
path: full
interaction: autopilot
requirements: REQ-FUNC-f47164f2, REQ-UX-ec09a60a
parent:
branch: task/adore-web-interface
base: 7a588905de14d68503d47a6321b0e9c3b1114d32
opened: 2026-10-16

## Done checklist (current stage)

- [x] Test-first missing-behavior observations and anchor recorded.
- [x] Compact chooser and balanced Agent/model source implementation complete.
- [x] Four-locale help/release notes and component/user documentation updated.
- [x] Targeted source verification completed before user's deferral.
- [x] Package build jobs stopped and pre-existing static assets restored.
- [ ] Final validation and portable package rebuild deferred at the user's request.

## Frame

Problem: STATED — The host folder chooser is too complex; the user wants a simple OS-style selection experience.
Desired outcome: A compact familiar folder chooser with address/navigation, a directory list and Select folder/Cancel.
Actors: OBSERVED — Enrollment administrator using a browser connected to a local or remote ADORE host.
Primary scenario: Custom clone location -> Choose folder -> browse/select a host directory -> Select folder -> the main form shows the selected path.
Examples: Selecting D:\Projects returns D:\Projects; selecting /srv/repos returns /srv/repos. The main clone path field can be edited to propose a new destination.
Counterexamples: A failed or cancelled read must not replace the draft, select stale data, create directories, open a browser-local upload flow or invoke OS dialogs on a remote server.
In scope: HostFolderPicker.tsx, setupCopy.ts and styles; required enrollment/test changes; EN/RO/FR/DE labels/help/release notes; component documentation; native final portable archive refresh after verified implementation.
Out of scope: Native desktop shell/bridge, new browser permissions/dependencies, backend filesystem/authorization policy changes, unrelated pre-existing work, setup/deploy tests, persistent delivery reports/logs.
Constraints: Windows/Linux paths; existing administrator-only read-only bounded host API; manual clone entry, automatic reset, keyboard/focus/cancellation/stale-response safety, narrow-screen layout; delivery only archives and adjacent optional hashes.
Success signals: One primary directory list; compact conventional navigation; no child-name/destination-summary form inside the picker; precise selected path visible in main form; happy and boundary UI cases green in all locales; current portable packages verified natively.
Evidence: STATED user screenshot/request; OBSERVED HostFolderPicker.tsx currently exposes editable path, root button row, oversized folder buttons, child-name input and computed destination; hostFolders.ts validates host metadata; host-folders.spec.ts covers current authorization/navigation/draft rules.
Assumptions: INFERRED — “similar to OS open path” requests familiar interactions within the web app rather than a native desktop integration.
Unknowns: Whether the user specifically requires a literal native OS dialog; no native client bridge exists in the inspected web delivery.
Decision-blocking questions: Resolved by explicit user approval to implement and verify through final packages without intermediate AEGIS stops.
Proposed behaviors: Compact address/up controls and starting locations; conventional directory rows with visible selection and keyboard access; Select folder returns the exact chosen existing directory; new destination paths remain editable in the enrollment form.
Path and reason: full — observable picker interaction/selection contract changes and localized help are required; no backend/API format, dependency, authorization or filesystem-write change.
Path criteria: no new observable behavior | no | picker controls and selection result change; no new interface/data format | yes | existing host API unchanged; no new dependency | yes; existing requirement covers behavior | yes | REQ-FUNC-f47164f2 needs UI contract revision; no security/data-handling change | yes | host read-only boundaries remain.
Run limits: One task, at most 40 source/documentation/test files, 60 minutes implementation/verification per run, at most three focused repair cycles before reassessment; no model/provider calls, no publication.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision |
|---|---|---|---|---|---|---|
| Compact Agent and model | Independent field stacks with automatic detection and optional Advanced refresh | REQ-UX-ec09a60a | Enter local mode and switch executor without pressing Detect | Late/failed detection and manual overrides remain safe | Local executor browser tests and visual layout checks | Two vertical groups; retain mount discovery |
| Familiar compact directory choice | Select an existing host directory through one bounded read-only interaction | REQ-FUNC-f47164f2 | Single click selects, double-click/Enter opens, Select confirms exact folder | Failed/stale/cancelled reads preserve draft; selection unavailable while pending or invalid | Existing offline API/domain tests plus revised four-locale Windows/Linux browser journeys and visual checks | Retain API; simplify modal layout and interactions |

## Design

- REQ-FUNC-f47164f2: HostFolderDialog remains a browser modal over the authenticated read-only host API; no native shell integration, dependency or API format change.
- Layout: compact title; one address/navigation toolbar; starting locations in a narrow sidebar; conventional left-aligned directory rows; Select folder and Cancel footer.
- Single click highlights a folder without navigating or changing the clone draft. Double-click or Enter opens a folder. Arrow/Home/End keys select/focus rows. Up and successful-location Back navigation are explicit.
- Confirm returns the selected existing directory, or the currently displayed directory when no child row is highlighted. It does not append a repository name. The final clone-path input remains editable for a new destination outside the picker.
- Initial browse remains the current ADORE account home. Loading/failed reads disable confirmation; typed address changes also disable confirmation until an exact successful read.
- Requests retain AbortController/generation protection; cancelled or superseded results cannot commit listing/history or draft changes. History includes successful locations only and is kept in component memory.
- Escape/Cancel restore the trigger focus and preserve manual draft text. Modal remains keyboard accessible and responsive; visual rows use existing theme tokens.
- Main state ownership is unchanged: browsing has no filesystem writes and the existing enrollment review/create step owns clone validation and creation.
- Windows and Linux roots/directories use the existing validated metadata. Starting-root navigation and manual path recovery remain available after errors.
- Remove the child-name input and destination summary from the modal; all four locales/help explain exact existing-folder selection and main-form manual new destinations.
- No architecture drawing is required: component/API boundaries and data flow remain unchanged. Backend code, authorization, scan bounds and path/link/network restrictions are retained.
- Test seams: e2e/host-folders.spec.ts for interaction/draft/cancellation/stale responses/focus/locales/mobile; existing hostFolders tests and backend API tests for unchanged trust boundaries.
- Files: HostFolderPicker.tsx, EnrollmentWizard.tsx, setupCopy.ts, styles.css, host-folders.spec.ts, four projects help files, release_notes.toml, user/component/knowledge docs, changelog and compiled frontend assets.
- Risk: OS-style single click is selection while double click opens; tests and short pointer/keyboard affordances must make the distinction visible. Remote browser/server separation is retained by host-specific labels.
- Alternative rejected: a server-native OS dialog would target the server session, and browser-local directory selection is not the existing host API. The accepted web chooser preserves current host operation.
- Open decisions: none after the user's accepted proposal. No setup/deploy tests and no persistent delivery reports/logs.

- REQ-UX-ec09a60a: Agent/model step uses two independent vertical field stacks rather than row-coupled grid heights: executor/run-location/authentication on the left, model and relevant runtime/installed-executor controls on the right; mobile stacks both groups.
- REQ-UX-ec09a60a: Discovery remains automatic on local-picker mount; agent changes use the validated full listing. Re-detection is available inside Advanced alongside manual overrides; unavailable/missing discovery retains visible status and manual fallback.
- Targeted validation only, by explicit user instruction: host-folder and local-executor browser tests, affected enrollment regression, help/domain contracts, unchanged backend host/executor trust-boundary cases and native package acceptance. Full repository-suite evidence is not claimed.

## Log

- 2026-10-16 frame: Inspected the screenshot, host picker/source/API contracts and existing UI tests; selected the full path for a simpler familiar web folder chooser. Scope and task-specific autopilot continuation were requested; checkpoint mode remains in force pending the user's response.

- 2026-10-16 frame: User explicitly approved implementation and full verification through final packages without intermediate stage stops; task interaction is autopilot.
- 2026-10-16 specify: Revised one existing requirement and retained its read-only/authorization/manual-reset boundaries; no new or retired requirements. Proposed named-child input is replaced by exact existing-folder selection plus the already editable main clone path.
- 2026-10-16 design: Accepted compact modal/navigation design recorded above; no backend/API/dependency or component-architecture change. Transitioned to build.

- 2026-10-16 build red: REQ-FUNC-f47164f2; command=`npx playwright test e2e/host-folders.spec.ts -g 'compact chooser selects the exact' --reporter=line` (04_Software/web); exit=1; expected missing behavior=old dialog has two inputs instead of one compact address field.
- 2026-10-16 scope: User added compact independent Agent and model columns and automatic executor detection clarification; existing LocalExecutorPicker already discovers on mount and selects agents from its full detected listing. Move the manual refresh control to Advanced; retain manual/saved authority and error recovery.

- 2026-10-16 build red: REQ-UX-ec09a60a; command=`npx playwright test e2e/local-executors.spec.ts -g 'local enrollment prefills npm launches' --reporter=line` (04_Software/web); exit=1; expected missing behavior=manual Detect button is visible outside closed Advanced.

- 2026-10-16 build: Focused browser candidate reached 18/19 passing; the reordered columns exposed an ambiguous Model versus Model authentication test locator. Replaced that selector with the existing model field ID; no product behavior change was needed.
- 2026-10-16 release-notes: updated (merged compact folder selection and automatic agent detection into existing four-locale improved notes).
- 2026-10-16 help: updated (projects, executors and settings topics in all four locales).

- 2026-10-16 build green: `npm run build:e2e` plus `npx playwright test e2e/host-folders.spec.ts e2e/local-executors.spec.ts e2e/enrollment.spec.ts --reporter=line` (04_Software/web), exit=0, 35 passed. `node --test tests/hostFolders.test.mjs tests/localExecutors.test.mjs tests/help.test.mjs`, exit=0, 16 passed. Targeted backend `pytest test_host_folders.py test_executor_discovery.py -q`, exit=0, 25 passed/3 platform skips. Release-note contract with --since task base passed.
- 2026-10-16 validate: Specification-compliance inspection approved against the accepted folder/executor scope and two requirements; backend API/dependency/auth/no-write boundaries unchanged. Implementation-quality inspection approved after checking request generations/history, pending/error confirmation, focus/keyboard, independent-column/mobile styles and manual-command authority. Separate inspection questions were applied to the same source candidate; targeted UI screenshots confirm compact layout.
- 2026-10-16 DEVIATION validate: Required full `check --strict --run` replaced by targeted affected-area proof plus strict catalog and native archive acceptance under explicit user RULING-003; no full-suite result is claimed.

- 2026-10-16 user steering: Stopped both owned Windows/Linux package build jobs immediately after the user requested implementation only. No new archive was published (both final archives retain their 2026-10-15 timestamps/sizes). The interrupted Windows Vite build had cleared static output; restored the pre-existing static files directly from the existing Windows archive without rebuilding. New source implementation remains in place.

## Rulings

- RULING-001 | date=2026-10-16 | decision=Retain the current branch and all pre-existing unrelated edits; this task covers folder-picker simplification only | reason=Existing checkout carries the user's earlier implementation/tooling work | source=repository | supersedes=none

- RULING-002 | date=2026-10-16 | decision=Use task-specific autopilot through implementation, verification and final local Windows/Linux packages | reason=Explicit answer: Da, implementează și verifică până la pachetele finale | source=user | supersedes=none

- RULING-003 | date=2026-10-16 | decision=Run only targeted tests for affected picker/executor/help behavior and actual Windows/Linux archives, replacing the full canonical suite | reason=Explicit user instruction: ruleaza doar teste targetate - toate testele dureaza prea mult | source=user | supersedes=none
- RULING-004 | date=2026-10-16 | decision=Include balanced independent Agent and model columns and closed-Advanced executor re-detection | reason=User screenshot and request during implementation | source=user | supersedes=none

- RULING-005 | date=2026-10-16 | decision=Stop package reconstruction and defer further testing/packaging until the user requests final validation; complete implementation only | reason=Explicit user instruction: nu mai reconstrui pachetele. Vom testat totul la final. Doar fa implementarile | source=user | supersedes=RULING-002

## Handoff


current: build
status: waiting
next: await the user's final validation/build request; do not run more tests or rebuild packages meanwhile
must_read: .agentic/tasks/TASK-fec704e8.md; 04_Software/web/src/HostFolderPicker.tsx; 04_Software/web/src/LocalExecutorPicker.tsx; 04_Software/web/src/EnrollmentWizard.tsx
blockers: final validation and packaging explicitly deferred by the user; source implementation is complete

## Stage report

stage: build
result: paused
current: build
changed: compact folder chooser, independent Agent/model columns, automatic discovery with optional Advanced refresh
evidence: targeted checks completed before deferral: 35 browser, 16 domain/help, 25 backend/3 platform skips; source/user/component/help/release notes updated
issues: package builds interrupted by user request; previous static assets restored and final archives unchanged; final validation deferred
next: user-requested final testing and packaging later
needs_user: yes
spec_compliance: approved
implementation_quality: approved
review_round: 1
