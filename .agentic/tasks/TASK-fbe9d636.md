# TASK-fbe9d636 - Explain the container-only ChatGPT sign-in when native execution is selected

stage: done
type: fix
path: quick
interaction: autopilot
requirements: REQ-FUNC-a5d65a57, REQ-FUNC-5de75419
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
In scope: STATED — explain that ADORE ChatGPT sign-in is available only for container projects, with a regression assertion and current component documentation. OBSERVED during resumed proof — wait for persisted preference responses in the existing four-locale repository connection journey before full navigation.
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
- REQ-FUNC-5de75419 — the existing four-locale repository dialog journey retains its keyboard and narrow-layout assertions and waits for successful preference writes before navigation.

## Design

Replace only the stale cause sentence in the native ChatGPT diagnostic. Reuse
the public configuration test for the regression. Reconcile the config component
and knowledge page with the managed native runtime and helper-only ChatGPT flow.
The resumed browser proof repairs only the test's locale/theme save ordering.
Product locale handling and repository connection behavior are unchanged.

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
- 2026-11-04 done: returned to validate - Owner authorized a new bounded segment to finish only outstanding frontend checks without repeating Python
- 2026-11-04 validate: Owner authorized proof-only resume in a new segment bounded to 20 minutes. Product bytes are unchanged from the independently reviewed candidate. Earlier Python, Ruff, frontend Node helpers, TypeScript and isolated build passed. Chromium cases 1-105 completed without failure artifacts, case 106 was interrupted by browser termination, and cases 107-215 were unexecuted.
- 2026-11-04 validate: returned to build - Proof resume exposed a browser-test navigation race: PATCH locale save aborted before document navigation, causing cascading English sign-in assertions
- 2026-11-04 build: Validation scope correction: retain REQ-FUNC-a5d65a57 and add the existing repository connection contract REQ-FUNC-5de75419 solely for the browser proof repair. Read web-interface routing and repository dialog source. Red: resumed jobs.spec.ts:862 failed waiting for the Romanian dialog trigger after the third preferences PATCH was cancelled by navigation (trace status -1), followed by four locale-state cascade failures. Runtime product behavior is unchanged.
- 2026-11-04 build: DEVIATION build: scope includes a test-only preference persistence wait in the existing four-locale repository journey - accepted to finish the mandatory browser proof after an observed cancelled PATCH, without changing runtime product behavior.
- 2026-11-04 build: Resumed build proof: npm --prefix 04_Software/web run typecheck exit 0. Runtime code is unchanged, so the previous full Python and Ruff proof remains applicable. No release-note or Help change is required for this internal test correction.
- 2026-11-04 build: green: corrected Chromium jobs.spec.ts:862 four-locale keyboard/layout journey passed in 22.9 seconds. TypeScript app/e2e validation exited 0 (REQ-FUNC-5de75419). Both independent reviewers approved the unchanged reviewed correction after this focused proof.
- 2026-11-04 build: completed; next validate
- 2026-11-04 validate: green: remaining Chromium batch completed 105 passes and five locale-state failures; rerun of only those five after the test ordering correction passed all five in 83.1 seconds. Together with the original 105 completed cases, all 215 browser cases now have passing proof. TypeScript passed. Independent spec and quality reviews approved round 2.
- 2026-11-04 validate: final: check --task TASK-fbe9d636 --strict exit 0 after the last candidate edit, 0 errors and 34 unpromoted existing record/path/coverage warnings. Per owner instruction Python was not repeated. Its earlier full pass, Ruff pass, Node helper/type/build proof and completed 215-case Chromium proof cover the integrated candidate. The interrupted full invocation remains recorded truthfully as exit 1.
- 2026-11-04 validate: completed; next done

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-fbe9d636.md
changed: Accurate native ChatGPT refusal and deterministic locale browser proof; live acceptance evidence reconciled
evidence: Full Python, Ruff, Node helpers, TypeScript/build and all 215 Chromium cases passed; strict static exit 0; two reviews approved round 2
issues: 34 unpromoted pre-existing advisory warnings; validation composed across bounded segments
spec_compliance: approved
implementation_quality: approved
review_round: 2

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

## Delivery report (2026-11-04)

- stage: validate; type: fix; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-a5d65a57 - Refuse ChatGPT for a local run or a stage limit beyond the token life
  - REQ-FUNC-5de75419 - Connect and verify a project repository account
- deviations: 3 recorded
  - validate: correction work bound increased from 35 to 45 minutes within the original 90-minute acceptance session - the full Python suite took 1505 seconds and passed, while the required frontend proof is still running. No additional live job or scope is added.
  - validate: bounded full check stopped during Chromium to retain the original session limit. Python suite passed in 1505.3 s and Ruff passed in 2.7 s. The frontend reached serial browser tests after its helper/type/build checks, but full browser regression remains unproven.
  - build: scope includes a test-only preference persistence wait in the existing four-locale repository journey - accepted to finish the mandatory browser proof after an observed cancelled PATCH, without changing runtime product behavior.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 5086910: 13 file(s) changed, 337 line(s) added
- checks: errors=0 warnings=34 notes=23
- checklist: 9/9 done
