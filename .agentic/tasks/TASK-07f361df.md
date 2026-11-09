<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-07f361df - Choose detected container runtimes in project settings

stage: validate
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-72081f3b, REQ-UX-40f6b75a, REQ-SEC-548f27ce, REQ-FUNC-ec8e382f
parent:
branch: task/adore-web-interface
base: 94b205a6e75863ca069304f1532ee369b6b52678
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
- [x] final `check --strict --run` result logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem: OBSERVED Settings edits the container runtime as a text field, so the administrator must know the host command.
Desired outcome: STATED Offer a dropdown of server-detected commands including Docker in WSL2 and keep manual entry.
Actors: OBSERVED Project Settings runtime changes require administrator access.
Primary scenario: STATED An administrator edits Container runtime command and chooses the host's Docker in Ubuntu.
Examples: OBSERVED On the current Windows host `docker` fails and `wsl -d Ubuntu -- docker` has a working engine.
Counterexamples: INFERRED A distro without a working runtime CLI should not be presented as detected; a saved command outside detection stays editable manually.
In scope: STATED Project Settings selector and manual command. INFERRED The existing image selector can list images for the standard WSL commands offered here.
Out of scope: INFERRED Installation, project configuration edits on the live service, and new runtime or project persistence formats are unnecessary for the requested picker.
Constraints: STATED Repository requires offline tests. INFERRED Limit work to 30 minutes, 32 files, no model calls, one build/validation cycle plus up to two corrective cycles.
Success signals: STATED A detected WSL Docker command can be selected and a custom command can still be entered. OBSERVED Existing reviewed Save is the persistence boundary.
Evidence: OBSERVED App.tsx renders the field as a text input; doctor.py lists WSL distros; executor-images currently accepts native Docker and Podman only.
Assumptions: INFERRED Detection establishes that the CLI responds to its version probe; existing prerequisites verify engine and image readiness separately.
Unknowns: UNKNOWN Available runtime commands differ across hosts.
Decision-blocking questions: None.
Proposed behaviors: INFERRED On unavailable discovery, preserve the active value and manual editor; report only successful bounded probes.
Path and reason: Full path.

| Criterion | Holds? | Evidence |
| --- | --- | --- |
| No new observable behavior | No | STATED New selector |
| No new interface or data format | No | INFERRED Read-only runtime inventory API |
| No new dependency | Yes | OBSERVED Existing command runner and React |
| Existing requirement covers behavior | No | OBSERVED Current settings contract offers a command edit only |
| No security or data-handling change | No | INFERRED New administrator-only host probe boundary |

## Requirement coverage

| Requirement | Behavior | Design | Verification |
| --- | --- | --- | --- |
| REQ-FUNC-72081f3b | Discover native and WSL commands | Fixed server probes | Offline API tests |
| REQ-UX-40f6b75a | Select or enter manually | Settings field editor | Chromium Settings test |
| REQ-SEC-548f27ce | Restrict inventory probes | Admin dependency and fixed argv | Offline negative API tests |
| REQ-FUNC-ec8e382f | Resolve WSL image suggestions | Validated inventory prefix | Offline API and Chromium tests |

## Design

### Approach

Use the existing doctor WSL enumeration and a new fixed-argument discovery probe.
Settings requests the inventory once on Edit and uses the existing draft/save flow.

### Interfaces and data

Admin GET /api/v1/executor-runtimes returns a commands list with failed probes omitted.
Bound the number and elapsed time of probes and send no raw subprocess output.
Existing image inventory accepts native commands and the standard WSL forms.
Manual commands keep the existing validator and persistence format.

### Files and test seams

doctor.py owns discovery and inventory argv validation. app.py exposes the routes.
ContainerRuntimePicker.tsx owns discovery and the manual editor. App.tsx supplies
the draft and accessible description. serverImages.ts encodes the selected command.
Test fake runtime boundaries in test_executor_environment_choice.py and settings
interaction in images.spec.ts. Update the API and frontend component docs.

### Risks and open decisions

Never dispatch shell strings or user-supplied options from inventory queries.
Reject invalid distro output and bound enumeration. Starting a WSL distro is
possible during explicit editing. Availability is CLI detection, not readiness.

### Requirement map

- REQ-FUNC-72081f3b maps to bounded host and distro version probes.
- REQ-UX-40f6b75a maps to the selector, manual input and existing reviewed Save.
- REQ-SEC-548f27ce maps to the administrator dependency and fixed argv.
- REQ-FUNC-ec8e382f maps to validated WSL image lookup and soft failure.

Diagrams: [diagram_TASK-07f361df.md](diagram_TASK-07f361df.md)

## Log

- 2026-11-09 frame: journal opened
- 2026-11-09 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-09 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-09 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-09 build: red: pytest executor environment inventory selectors exit 1; runtime endpoint absent and WSL images rejected (REQ-FUNC-72081f3b, REQ-SEC-548f27ce, REQ-FUNC-ec8e382f)
- 2026-11-09 build: red: npm run test:e2e -- images.spec.ts -g container runtime dropdown --workers=1 exit 1; Settings has no runtime dropdown (REQ-UX-40f6b75a)
- 2026-11-09 build: release-notes: updated (runtime and image selection)
- 2026-11-09 build: help: updated (executors topic in all four locales)
- 2026-11-09 build: green: pytest test_executor_environment_choice.py test_doctor.py exit 0 (53 passed, REQ-FUNC-72081f3b, REQ-SEC-548f27ce, REQ-FUNC-ec8e382f)
- 2026-11-09 build: green: runtime dropdown Chromium journey passed, with WSL image suggestions and manual saved command (REQ-UX-40f6b75a)
- 2026-11-09 build: Advisory check has no errors; repository-wide stale path, ticket reference and manual verification warnings are outside this feature.
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: returned to build - Correct WSL readiness guidance and give WSL cold-start probes a longer bounded timeout after live detection intermittently returned an empty list.
- 2026-11-09 build: red: pytest runtime inventory timeout assertions exit 1; WSL did not receive a cold-start allowance (REQ-FUNC-72081f3b)
- 2026-11-09 build: green: 53 targeted pytest tests and Ruff exit 0 after cold WSL timeout adjustment
- 2026-11-09 build: Live read-only acceptance in isolated data: Windows API discovered wsl -d Ubuntu -- docker and listed adore-executor-base:1.0.0. No model requests.
- 2026-11-09 build: help: updated (all locales accurately describe the Pi image startup check)
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: returned to build - Document that the host check runs a temporary container to locate Pi, without invoking Pi itself.
- 2026-11-09 build: green: node --test 04_Software/web/tests/help.test.mjs exit 0 (11 tests); release notes check and production build also passed after documentation clarification
- 2026-11-09 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-09 validate: final: check --task TASK-07f361df --strict --run exit 1. Python 2713 passed, 6 skipped, 3 failed; Ruff 1 failure; Node 2 failures. Each failure reproduced against isolated base 94b205a. Focused Python, Chromium, live WSL API and production build passed.
- 2026-11-09 validate: DEVIATION validate: repository-wide proof remains red on the baseline. The focused proof covers selector behavior, the new endpoint and WSL image lookup. Artifact and fixed fixture password scanner warnings are generated bundle and test data, respectively.

## Rulings


## State

status: blocked
reported: validate - blocked
next: Repeat strict validation when the base branch suite passes
must_read: .agentic/tasks/TASK-07f361df.md, .agentic/steps/5_validate.md
changed: Runtime picker, WSL inventory, reviewed manual entry, help and production assets
evidence: 53 focused Python and 6 Chromium tests passed; Windows API found WSL Docker and its image; strict exit 1
issues: Three Python failures, two Node failures and one Ruff failure reproduced on base 94b205a.
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-11-09)

- stage: validate; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-72081f3b - Detect container runtime commands on the server
  - REQ-UX-40f6b75a - Choose a detected runtime or enter a manual command
  - REQ-SEC-548f27ce - Restrict runtime inventory to authorized fixed probes
  - REQ-FUNC-ec8e382f - List local images for standard WSL runtime commands
- deviations: 1 recorded
  - validate: repository-wide proof remains red on the baseline. The focused proof covers selector behavior, the new endpoint and WSL image lookup. Artifact and fixed fixture password scanner warnings are generated bundle and test data, respectively.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 94b205a: 32 file(s) changed, 706 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=45 notes=24
- checklist: 6/9 done; open: final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
