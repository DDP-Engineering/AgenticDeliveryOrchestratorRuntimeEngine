# TASK-fbe9d636 - Explain the container-only ChatGPT sign-in when native execution is selected

stage: done
type: fix
path: quick
interaction: autopilot
requirements: REQ-FUNC-a5d65a57
parent:
branch: task/adore-web-interface
base: 5086910b3e944fac7cd995c2881c0048e61d73e7
opened: 2026-11-04

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

Problem: OBSERVED — PI-08 native validation says there is no managed native Pi, although PI-07 introduced managed native Pi.
Desired outcome: STATED — keep acceptance diagnostics accurate through small generic corrections authorized under #58.
Actors: STATED — the operator checking ChatGPT on Windows or Linux.
Primary scenario: OBSERVED — a native ChatGPT configuration is refused before a run starts.
Examples: OBSERVED — Windows and WSL2 both return the stale managed-Pi explanation.
Counterexamples: OBSERVED — container ChatGPT is accepted and its live model probe succeeds.
In scope: STATED — explain that ADORE ChatGPT sign-in is available only for container projects, with a regression assertion and current component documentation.
Out of scope: STATED — native ChatGPT support, API-key jobs, migrations, pushes and publication remain outside the narrowed acceptance.
Constraints: STATED — autopilot, current branch, offline product tests. At most 20 files, 35 minutes and two review rounds for this correction. Live acceptance records remain separate planning work already in progress.
Success signals: OBSERVED — the existing public validation test retains its positive container case and boundary refusals and asserts the accurate container-only sign-in cause.
Evidence: OBSERVED — config.py::_chatgpt_issues and REQ-FUNC-a5d65a57 define the refusal. Both native validation commands produced the stale text during #58.
Assumptions: INFERRED — correcting the reason within the established refusal requires no new interface or data format.
Unknowns: none affecting the message correction.
Decision-blocking questions: none.
Proposed behaviors: none beyond the existing container-only contract.
Path and reason: quick, with all criteria met below.

| Criterion | Holds | Evidence |
| --- | --- | --- |
| No new externally observable behavior | yes | Correct the explanation of the existing refusal |
| No new interface or data format | yes | Same configuration key and validation result |
| No new dependency | yes | String, assertion and documentation changes |
| Existing requirement covers the behavior | yes | REQ-FUNC-a5d65a57 |
| No security or data handling change | yes | Backend and credential policy stay enforced |

## Requirement coverage

- REQ-FUNC-a5d65a57 — public provider tests cover the accepted container configuration and native/stage-limit refusals.

## Design

Replace only the stale cause sentence in the native ChatGPT diagnostic. Reuse
the public configuration test for the regression. Reconcile the config component
and knowledge page with the managed native runtime and helper-only ChatGPT flow.

## Log

- 2026-11-04 frame: journal opened
- 2026-11-04 frame: completed; next build - Quick correction scoped from live acceptance, autopilot explicitly requested (7 Done checklist item(s) left unticked)
- 2026-11-04 build: red: pytest test_pi_providers.py::test_chatgpt_is_refused_for_a_local_run_and_stage_limits_beyond_the_token exit 1 - native refusal still claims managed Pi is absent (REQ-FUNC-a5d65a57)
- 2026-11-04 build: green: pytest tests/test_pi_providers.py tests/test_config.py exit 0, 97 passed (REQ-FUNC-a5d65a57)
- 2026-11-04 build: release-notes: updated (Agent and model note merged within the category cap)
- 2026-11-04 build: help: none (four locales already describe ChatGPT as container-only)
- 2026-11-04 build: Build audit: same-component docs also correct stale native command and custom-endpoint descriptions. Context pages already describe container-only ChatGPT. Advisory check has 0 errors and 34 existing record/path warnings.
- 2026-11-04 build: completed; next validate
- 2026-11-04 validate: Independent spec and quality reviewers approved round 1 without findings. Project/environment context already matches container-only ChatGPT and managed native Pi.
- 2026-11-04 validate: Manual: native Windows and WSL2 adore -c <isolated config> config validate each exited 1 with the corrected container-only ChatGPT sign-in explanation.
- 2026-11-04 validate: DEVIATION validate: correction work bound increased from 35 to 45 minutes within the original 90-minute acceptance session - the full Python suite took 1505 seconds and passed, while the required frontend proof is still running. No additional live job or scope is added.
- 2026-11-04 validate: DEVIATION validate: bounded full check stopped during Chromium to retain the original session limit. Python suite passed in 1505.3 s and Ruff passed in 2.7 s. The frontend reached serial browser tests after its helper/type/build checks, but full browser regression remains unproven.
- 2026-11-04 validate: final: check --task TASK-fbe9d636 --strict exit 0, 0 errors and 34 unpromoted existing path/record/release-note coverage warnings. Runtime correction has 97 focused passing tests, full Python and Ruff proof, two independent approvals and native Windows/WSL2 CLI refusal checks. The --strict --run invocation was interrupted during browser proof, never reported as green.
- 2026-11-04 validate: completed; next done

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-fbe9d636.md
changed: Corrected native ChatGPT diagnostic and documentation; live evidence kept separately in ACCEPTANCE.md
evidence: 97 focused tests, full Python and Ruff passed; strict static check exit 0; independent reviews approved
issues: Full Chromium regression unproven after bounded stop; 34 unpromoted pre-existing advisory warnings
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-11-04)

- stage: validate; type: fix; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-a5d65a57 - Refuse ChatGPT for a local run or a stage limit beyond the token life
- deviations: 2 recorded
  - validate: correction work bound increased from 35 to 45 minutes within the original 90-minute acceptance session - the full Python suite took 1505 seconds and passed, while the required frontend proof is still running. No additional live job or scope is added.
  - validate: bounded full check stopped during Chromium to retain the original session limit. Python suite passed in 1505.3 s and Ruff passed in 2.7 s. The frontend reached serial browser tests after its helper/type/build checks, but full browser regression remains unproven.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 5086910: 9 file(s) changed, 262 line(s) added
- checks: errors=0 warnings=34 notes=23
- checklist: 9/9 done
