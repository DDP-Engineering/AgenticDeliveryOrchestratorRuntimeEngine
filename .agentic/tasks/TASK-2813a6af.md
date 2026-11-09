# TASK-2813a6af - PI-07: Install and run ADORE-managed Pi on the server

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-548f6855, REQ-REL-ebc48378, REQ-PLAT-3c0e0b9a, REQ-SEC-51d9f79b, REQ-FUNC-a71d617b, REQ-UX-c35b7aa5, REQ-SEC-f7b9111e, REQ-UX-b75e1df8, REQ-UX-23a72bde, REQ-FUNC-78b0ad95, REQ-FUNC-6b8494a7, REQ-FUNC-f60cd4e1, REQ-FUNC-5e2fe079, REQ-UX-3ce12a1a, REQ-UX-ec09a60a, REQ-NFR-f4b171f4, REQ-FUNC-8f369d55, REQ-FUNC-7ab1a48e, REQ-FUNC-ae57faed
parent:
branch: task/adore-web-interface
base: 98ff071830f56fe74cc14b58073e94e90d286b24
opened: 2026-11-03

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

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

Problem: OBSERVED — native execution resolves a configured command and uses the account's Pi settings; container Pi already uses RPC.
Desired outcome: STATED — #57 requires an isolated ADORE-managed pinned Pi on Linux and Windows.
Actors: STATED — the ADORE operator and the service account; Pi executes AEGIS stages.
Primary scenario: STATED — the operator installs/verifies Pi and selects server execution with optional project-tool PATH.
Examples: STATED — missing or old Node and missing Pi produce actionable readiness failures.
Counterexamples: STATED — a global Pi, personal extensions and a project-selected launcher are never used.
In scope: STATED — CLI install/verify/upgrade, Windows Node and PowerShell, local RPC, readiness/settings/help and tests.
Out of scope: STATED — container changes, local network enforcement, migrations, #58, pushes and real AI calls.
Constraints: STATED — offline tests, current account, keep scope ownership and preserve prior fixes. One task; at most 180 minutes, 5 review rounds, 120 touched files, no paid external calls.
Success signals: STATED — fake npm verifies installation lifecycle, hostile Pi settings are ignored, native stages use RPC and readiness distinguishes prerequisites.
Evidence: OBSERVED — clean 98ff071 on task/adore-web-interface; live Gitea #57 and #50; PLAN §4.5 and SPIKE_FINDINGS §§4–5, 9; current local execution and Pi launcher.
Assumptions: INFERRED — keep Linux delegation as server configuration rather than project settings.
Unknowns: UNKNOWN — live service-account permissions and behavior on each real OS; no live acceptance claimed.
Decision-blocking questions: None found in the ticket and spike.
Proposed behaviors: STATED — use the spike's native Node/Pi launch and isolation flags.
Path and reason: Full.

| Criterion | Holds? | Evidence |
| --- | --- | --- |
| no new externally observable behavior | no | install and verify commands |
| no new interface or data format | no | local configuration and CLI |
| no new dependency | no | pinned npm packages on the server |
| an existing requirement already covers the behavior | no | managed install is new |
| no security or data-handling change | no | fresh agent directory and resource trust |

## Requirement coverage

| Behavior | Requirement | Design |
| --- | --- | --- |
| Install pinned Pi for the current account | REQ-FUNC-548f6855 | adore/pi_installation.py |
| Refuse an unverified Pi installation | REQ-REL-ebc48378 | adore/pi_installation.py |
| Diagnose native Pi prerequisites | REQ-PLAT-3c0e0b9a | adore/local_execution.py |
| Ignore personal and project Pi resources | REQ-SEC-51d9f79b | adore/local_execution.py |
| Drive native Pi stages through RPC | REQ-FUNC-a71d617b | adore/executor/launcher.py |
| Offer only current account and optional tools PATH | REQ-UX-c35b7aa5 | adore/config.py |

## Design

### Approach

OBSERVED: the Pi launcher has a shared RPC client and bounded evidence path.
INFERRED (REQ-FUNC-a71d617b): adapt the native process controller to lend the same
owned pipes to RPC, retaining its release barrier, lease and final scope drain.
Use one native RPC session for stages and the model connection test.

### Interfaces and data

STATED (REQ-FUNC-548f6855, REQ-REL-ebc48378, REQ-PLAT-3c0e0b9a): expose
`adore pi install` and `adore pi verify`. Resolve a compatible Node 22
from the service environment (absolute `ADORE_NODE` or host PATH), run
npm via that Node, validate the installed manifests and Pi version, and publish
the verified versioned prefix from a sibling temporary directory. Existing pins
stay intact; runtime selects only the current build pin.
STATED (REQ-SEC-51d9f79b): fresh agent directory outside the worktree, no personal or
project resources, explicit ADORE guard, Windows PowerShell and exact Node argv.
STATED (REQ-UX-c35b7aa5): retain current account and optional project-tool PATH;
Linux delegation remains host-owned. Refuse removed local TOML fields.

### Files and test seams

Add pi_installation.py and a packaged guard; change CLI, local execution and
scope transport, launcher/model test, config and enrollment/settings/readiness.
Use fake npm and subprocess boundaries, real fake-Pi RPC streams, and
the existing native/AEGIS and frontend offline suites.

### Risks and open decisions

Node major 22 excludes the Windows exit failure observed in the spike.
Unverified or linked paths fail closed. Native Pi runs as the service account
and can use its filesystem/network permissions. Live host acceptance is unknown.

### Requirement map

- REQ-FUNC-548f6855: pin and publish / fake npm
- REQ-REL-ebc48378: reject failed candidate / fake npm
- REQ-PLAT-3c0e0b9a: classify prerequisites / readiness test
- REQ-SEC-51d9f79b: fresh directory and flags / hostile fixture
- REQ-FUNC-a71d617b: owned stdin/stdout / local RPC test
- REQ-UX-c35b7aa5: reduce local fields / validation and frontend test

Diagrams: [diagram_TASK-2813a6af.md](diagram_TASK-2813a6af.md)

## Log

- 2026-11-03 frame: journal opened
- 2026-11-03 frame: completed; next specify
- 2026-11-03 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-03 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-03 build: red: uv run --no-sync pytest -q tests/test_pi_installation.py exit 1 - managed Pi CLI absent (REQ-PLAT-3c0e0b9a)
- 2026-11-03 build: green: uv run --no-sync pytest -xq --tb=short (7 focused files) exit 0; 244 passed, including pinned install, hostile settings, native RPC, tool readiness and Retry
- 2026-11-03 build: DEVIATION build: retired REQ-UX-3ce12a1a and REQ-UX-ec09a60a; the managed runtime replaces native executable discovery and custom launch in Settings
- 2026-11-03 build: release-notes: updated (managed native Pi replaces the previous executor note within the category cap)
- 2026-11-03 build: help: updated (managed install, current account, PATH, credentials and readiness in en/fr/de/ro)
- 2026-11-03 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-03 validate: Round 1: guard artifact contains trailing non-TypeScript; revise obsolete native help, model guidance, requirements and browser assertions
- 2026-11-03 validate: returned to build - Round 1 findings: repair packaged guard and obsolete native contract surfaces
- 2026-11-03 build: Round 2 correction proof: guard parity, owned native RPC pipes, hostile personal settings, large RPC reply, and keyless endpoint passed; broad pre-review affected suite passed 483; the round-2 focused run reported 203 passed and one unrelated one-second branch-rule evaluation timeout
- 2026-11-03 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-03 validate: final: python .agentic/aegis.py check --task TASK-2813a6af --strict --run exit 0; full offline Python, Ruff, frontend helpers, TypeScript and Chromium passed; 0 errors, 45 advisory warnings (older records/paths and task coverage/layout/generated bundle scan limits), none promoted
- 2026-11-03 validate: DEVIATION validate: no live Windows/Linux service-account npm or model acceptance - offline-only delegated scope; no real ADORE start or credentials used
- 2026-11-03 validate: completed; next done

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-2813a6af.md
changed: Managed native Pi install, scope and RPC; settings, help and release notes
evidence: AEGIS check --task TASK-2813a6af --strict --run exit 0; full Python, Ruff and frontend/Chromium
issues: 45 unpromoted advisory warnings; live Windows/Linux acceptance remains separate
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-03)

- stage: validate; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-548f6855 - Install pinned Pi for the current account
  - REQ-REL-ebc48378 - Refuse an unverified Pi installation
  - REQ-PLAT-3c0e0b9a - Diagnose native Pi prerequisites
  - REQ-SEC-51d9f79b - Ignore personal and project Pi resources
  - REQ-FUNC-a71d617b - Drive native Pi stages through RPC
  - REQ-UX-c35b7aa5 - Offer only current account and optional tools PATH
  - REQ-SEC-f7b9111e - Inject approved native provider credentials
  - REQ-UX-b75e1df8 - Configure and check local execution with user-owned tooling notice
  - REQ-UX-23a72bde - Choose where the executor runs when enrolling a project
  - REQ-FUNC-78b0ad95 - Refuse configuration that names a removed coding agent
  - REQ-FUNC-6b8494a7 - Keep executor environment mutations outside the web application
  - REQ-FUNC-f60cd4e1 - Select the Pi provider and model on every launch
  - REQ-FUNC-5e2fe079 - Preserve native local gate and AEGIS file evidence
  - REQ-UX-3ce12a1a - Prefilled and manually selected local executors
  - REQ-UX-ec09a60a - Automatic local setup with advanced overrides
  - REQ-NFR-f4b171f4 - Retain up to 1 MiB of native Test AI connection output
  - REQ-FUNC-8f369d55 - Prove a shell tool call in the local Test AI connection
  - REQ-FUNC-7ab1a48e - Refuse an OpenAI-compatible endpoint for a local run
  - REQ-FUNC-ae57faed - Write Pi's models.json for an OpenAI-compatible endpoint
- deviations: 2 recorded
  - build: retired REQ-UX-3ce12a1a and REQ-UX-ec09a60a; the managed runtime replaces native executable discovery and custom launch in Settings
  - validate: no live Windows/Linux service-account npm or model acceptance - offline-only delegated scope; no real ADORE start or credentials used
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 98ff071: 114 file(s) changed, 4518 line(s) added
- checks: errors=0 warnings=45 notes=23
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
