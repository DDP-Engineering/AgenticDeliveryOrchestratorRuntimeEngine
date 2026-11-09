# TASK-9bfd8e6a - Support managed native Pi with the ChatGPT subscription on Windows and WSL2

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-a5d65a57, REQ-FUNC-09ac930a, REQ-SEC-0fb2bba3, REQ-FUNC-a1b69eda, REQ-FUNC-4388b030, REQ-FUNC-5607e5cb
parent:
branch: task/adore-web-interface
base: 858865ea88cc4cd5c2fe0786b53dd03a12a7ccbd
opened: 2026-11-04

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

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

Problem: STATED the owner wants the ChatGPT subscription on native Windows and WSL2. OBSERVED configuration and web sign-in currently reject local projects, the credential helper is container-only, and LocalBackend.bind cannot accept gate secrets.
Desired outcome: STATED native Pi uses the ADORE-owned ChatGPT sign-in without a container dependency, through the existing GUI, explicit model probe and stage loop.
Actors: operator, ADORE service account, managed Pi, OpenAI OAuth.
Primary scenario: sign in from a native project, test model plus shell, run a bounded stage with an ephemeral access token.
Examples: Windows Node executable and Linux Node in WSL2 use the same pinned helper protocol.
Counterexamples: missing managed Pi, rejected refresh, malformed helper output, cancellation or an excessive stage timeout must fail closed.
In scope: native helper transport, config/API/UI/probe/stage wiring, isolated credential handling and redaction, offline contract tests, current documentation and four-locale Help.
Out of scope: STATED no push. Repository rules prohibit migrations. Production and #25 stay stopped. No Windows-to-WSL process wrapper is added to the portable core.
Constraints: STATED autopilot=true and local commits. Existing 3000-second token lifetime ceiling remains. One current stored format, managed Pi only, no personal credentials. Bound implementation to 3 hours, 120 changed files, at most 6 review rounds, and live probes to 90 seconds each. No financial cap per the owner's standing instruction.
Success signals: native configuration accepted with existing timeout limits, native sign-in needs no Docker, model and stage receive only a temporary token with redacted evidence, errors stay typed, API-key/container regressions pass.
Evidence: OBSERVED chatgpt.py SignIn/bearer_token use ContainerManager, web/app.py rejects local at sign-in, web/model_connection.py returns early for local, orchestrator.py injects via bind(secrets=...), local_execution.py lacks that keyword and drops ChatGPT tokens.
Assumptions: INFERRED WSL2 means ADORE running as Linux inside the distribution, using its own account/home, matching existing local backend ownership.
Unknowns: live native Node prerequisites and authentication availability will be measured without exposing secrets.
Decision-blocking questions: none, desired contract explicitly changes the native refusal.
Proposed behaviors: none pending. Reuse the established sign-in and stage token protocol on both transports.
Path and reason:
| Criterion | Holds | Evidence |
| --- | --- | --- |
| no new observable behavior | no | native subscription becomes usable |
| no new interface or data format | yes | provider and credential schema retained |
| no new dependency | yes | pinned Pi and Node reused |
| existing requirement covers behavior | no | native refusal must be revised |
| no data handling change | no | trusted native helper handles credential store |
Full path selected.

## Requirement coverage

| Behavior | Requirement | Design | Proof |
| --- | --- | --- | --- |
| Accept native ChatGPT with token lifetime ceiling | REQ-FUNC-a5d65a57 | shared limits | provider config tests |
| Start the shared sign-in from either backend | REQ-FUNC-09ac930a | helper selection | web API role/state tests |
| Launch-only token and redacted native evidence | REQ-SEC-0fb2bba3 | explicit target secrets | stage and native model tests |
| Native callback completion and visible bounded polling | REQ-FUNC-5607e5cb | shared completion observer and pending GUI polling | automatic API and Chromium tests |
| Native subscription usage diagnostics | REQ-FUNC-4388b030 | shared subscription classifier | native usage-limit probe test |
| Trusted native helper and closed failures | REQ-FUNC-a1b69eda | managed Node/Pi filtered process | helper protocol tests |


## Design

### Approach
Use the unchanged Pi OAuth helper protocol through either the existing helper container or a small trusted native transport (REQ-FUNC-a1b69eda). Ship the identical helper with the Python package and verify byte parity offline. Native transport uses verified managed Node/Pi paths and no shell, project PATH or personal Pi settings.
### Interfaces and data
Keep SignIn and bearer_token shared. A helper command builder returns argv plus explicit child cwd/environment for native execution. Native helper cleanup kills and reaps the directly owned trusted Node process, which executes no project code. Container cleanup remains unchanged. Token acquisition and login use the same ADORE credential directory, Pi lock and stable device ID (REQ-FUNC-09ac930a).
Observe the native Pi automatic loopback callback through nonblocking pending-helper polling in the status API. The visible GUI polls only while pending, with a 15-minute bound, and clears temporary addresses on completion. Manual submission first consumes any already completed helper event after validating state. Keep the existing status/error protocol and 3000-second stage ceiling (REQ-FUNC-a5d65a57). Obtain tokens before native model checks and stages. LocalBackend.bind accepts the same explicit secrets argument as ContainerBackend. LocalTarget injects the subscription token only when explicitly bound and adds it to the evidence redactor; ambient API keys never replace subscription authentication (REQ-SEC-0fb2bba3).
No persisted schema changes. Native projects use host network policy, independently of the container internet switch. A native service account can read its own files, so this is not an OS sandbox or a promise to hide same-account files.
### Files and test seams
chatgpt.py, executor/adore-chatgpt.mjs, pi_installation.py, config.py, orchestrator.py, local_execution.py, web/app.py and web/model_connection.py. Inject command runner and Popen. Extend provider, helper, native, stage, model and API tests. Update four-locale interface/help, component/operator docs, knowledge and release notes. No planning edits needed.
### Risks and open decisions
Preserve native process scopes, filtered credential environment and corrupt-input refusals. Fail closed on invalid helper output or nonzero exit. Test native cancellation, failed refresh and token redaction. Live authentication may need the owner again because #58 disconnected the isolated session. Installation/setup is separate from product tests.
### Requirement map
REQ-FUNC-a1b69eda uses trusted native helper command/environment and bounded cleanup.
REQ-FUNC-09ac930a selects the helper from backend while keeping shared admin/CSRF and OAuth state handling.
REQ-SEC-0fb2bba3 uses explicit target binding and shared token lifetime checks.
REQ-FUNC-a5d65a57 removes only native refusal and keeps token ceilings.
Diagrams: [diagram_TASK-9bfd8e6a.md](diagram_TASK-9bfd8e6a.md)


## Log

- 2026-11-04 frame: journal opened
- 2026-11-04 frame: completed; next specify - Explicit native subscription scope recorded in autopilot
- 2026-11-04 specify: completed; next design
- 2026-11-04 design: completed; next build
- 2026-11-04 build: red: provider/native helper focused pytest exit 1, native provider is rejected and native helper transport is absent (REQ-FUNC-a5d65a57, REQ-FUNC-a1b69eda)
- 2026-11-04 build: green: provider configuration, trusted native helper and existing container OAuth tests passed 82 cases (REQ-FUNC-a5d65a57, REQ-FUNC-a1b69eda)
- 2026-11-04 build: red: native stage/model focused tests exit 1, bind rejects explicit secrets and model probe has no subscription source (REQ-SEC-0fb2bba3)
- 2026-11-04 build: red: native web sign-in API pytest exit 1 with chatgpt_sign_in_container_required (REQ-FUNC-09ac930a)
- 2026-11-04 build: red: native helper expiry test exit 1, otherwise valid token accepted with expired lifetime; now require valid numeric expiry at the helper boundary (REQ-SEC-0fb2bba3)
- 2026-11-04 build: green: seven focused Python suites passed 225 cases; Ruff and 20 Help/ChatGPT/connection frontend checks passed. Native Windows helper started the real OAuth flow without a container. Waiting for owner sign-in before model acceptance.
- 2026-11-04 build: release-notes: updated (existing Agent and model note now describes native subscription support in all four locales)
- 2026-11-04 build: help: updated (executor authentication, transport and comparison in all four locales)
- 2026-11-04 build: Build audit: native readiness now reads the ADORE subscription status without model/refresh, independently of ambient API keys. Offline negative and happy tests cover both status and model boundaries. Native Windows and WSL2 managed Pi installations verified; WSL2 lacks a writable delegated cgroup in this environment.
- 2026-11-04 build: completed; next validate
- 2026-11-04 validate: Review round 1: fix native subscription usage-limit classification, reject malformed helper code types and failed sign-in exits, and correct remaining current component/knowledge container-only claims.
- 2026-11-04 validate: returned to build - Independent reviews identified helper protocol failure boundaries and native subscription diagnostic/docs gaps
- 2026-11-04 build: red round 2: public native helper/sign-in/usage tests exit 1, nine failures reproduce malformed code TypeErrors, failed or unstored login acceptance, and wrong usage-limit reason (REQ-FUNC-a1b69eda, REQ-FUNC-4388b030)
- 2026-11-04 build: green round 2: 126 focused native/shared helper, sign-in, web and model tests passed; Ruff passed. Non-string codes are typed failures, login requires clean exit plus readable store, and native subscription quota reports usage-limit.
- 2026-11-04 build: Manual WSL2: managed Node/Pi installed, native OAuth helper returned expected not-signed-in, and actual delegated cgroup Node launch/cleanup returned exit 0 v22.23.4. Readiness then correctly reports credential-missing. Initial environment checks used an unconfigured/nondelegated scope; corrected isolated service placement verified ownership without changing product scope control.
- 2026-11-04 build: completed; next validate
- 2026-11-04 validate: Independent spec and quality review round 2 approved; quality reviewer independently reran 13 malformed-output/login-exit/native-usage regression cases, exit 0. All recorded findings are resolved.
- 2026-11-04 validate: DEVIATION design: pinned Pi loginOpenAIChatGPT races its loopback callback with manual input (installed pi-ai openai-chatgpt.js lines 197-244). Native browser completion can exit the helper before manual submit. Add pending-login completion observation and GUI polling, retaining state-checked manual fallback. Interrupted the in-progress full proof rather than declaring incomplete native login valid.
- 2026-11-04 validate: returned to build - Pinned Pi native OAuth automatic callback completion needs API/UI observation and shared finalization
- 2026-11-04 build: red automatic callback: two native API tests fail, successful helper callback remains pending and provider refusal is not observed without manual submit (REQ-FUNC-09ac930a)
- 2026-11-04 build: red GUI callback: focused Chromium callback-completion test exit 1, status remains Not signed in after callback succeeds because panel never polls pending login
- 2026-11-04 build: green automatic callback: 95 focused Python tests passed, including native automatic success/refusal, manual fallback and helper boundaries; two Chromium ChatGPT journeys passed (manual and automatic without PUT). Ruff and 13 Help/ChatGPT Node checks passed. Read-only installed Pi source established its loopback/manual race; protocol and stored schema are unchanged.
- 2026-11-04 build: completed; next validate
- 2026-11-04 validate: returned to build - Round 3: serialize status reads and manual completion to prevent false conflict after automatic callback
- 2026-11-04 build: red round 3: delayed in-flight callback Chromium test failed before UI coordination; manual PUT was sent after automatic status completion (REQ-FUNC-5607e5cb)
- 2026-11-04 build: green round 3: all three Chromium ChatGPT journeys passed, including delayed status/manual completion race with zero obsolete PUT and no error alert; TypeScript checks passed. Status reads and mutations are serialized.
- 2026-11-04 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-04 validate: Manual live acceptance: owner completed native OAuth without Docker. probe_model_connection with managed Node/Pi and real ChatGPT gpt-5.6-luna returned ready=True/reason=ready on Windows and WSL2, each verifying a successful shell nonce then exact model reply. WSL service ran unprivileged inside its delegated cgroup, using the explicit ADORE sign-in directory; temporary setup corrections affected no product code. No job/forge publication or production restart occurred.
- 2026-11-04 validate: Round 4 independent specification and quality reviews approved the integrated candidate; no remaining findings. Evolution reviewed against scope. Release notes checker passed. Expected static warnings comprise prior repository records and generated asset scan/coverage heuristics; generated bundle corresponds to the reviewed source and is proved through the frontend build/journeys.
- 2026-11-04 validate: Final proof attempt: complete Python test command passed in 965.5s; lint failed exit 1 on the new chatgpt.py module-docstring line length. Stopped the identified proof tree before completing frontend; this attempt is not a passing final proof. Correct the line wrap and repeat review and complete proof.
- 2026-11-04 validate: returned to build - Final lint found one overlong module-docstring line
- 2026-11-04 build: green: Ruff check adore tests exit 0 after wrapping the module-docstring line only; no executable code changed. The interrupted strict attempt reported frontend exit 1 during owned process-tree shutdown, not a completed browser-suite result.
- 2026-11-04 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-04 validate: Round 5 both independent reviews approved the docstring-only correction; no executable behavior changed. Evolution delta inspected. Ruff whole adore/tests exit 0. Repeat complete final proof on this candidate.
- 2026-11-04 validate: final: python .agentic/aegis.py check --task TASK-9bfd8e6a --strict --run exit 0; full offline Python tests passed (862.1s), Ruff passed (0.1s), frontend Node tests/TypeScript/isolated build/complete Chromium suite passed (871.2s). Zero errors, 36 advisory warnings and 23 notes. 33 warnings concern pre-existing requirement/journal records; 3 generated-asset scan/coverage warnings are accepted separately. Windows and WSL2 real subscription model/shell probes both ready. SHA-256 comparison confirms production and tested frontend bundles are byte-identical.
- 2026-11-04 validate: DEVIATION validate: generated frontend assets have no direct requirement mapping and the minified bundle exceeds the automatic secret-scan size limit - reviewed requirement-linked sources, byte-identical production/test bundles and the complete frontend proof cover behavior; retain these three advisory heuristic warnings without changing the frozen candidate.
- 2026-11-04 validate: completed; next done

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-9bfd8e6a.md
changed: ChatGPT subscription support for native Windows and WSL2
evidence: Python, Ruff, frontend and live Windows/WSL2 model-shell probes passed
issues: 36 advisory warnings documented; no failing checks
spec_compliance: approved
implementation_quality: approved
review_round: 5

## Delivery report (2026-11-04)

- stage: validate; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-a5d65a57 - Refuse ChatGPT stage limits beyond the token life
  - REQ-FUNC-09ac930a - Start Sign in with ChatGPT from container and native projects
  - REQ-SEC-0fb2bba3 - Each ChatGPT stage receives only a short-lived access token
  - REQ-FUNC-a1b69eda - Use the managed native Pi helper for the server ChatGPT sign-in
  - REQ-FUNC-4388b030 - Test AI connection signs a ChatGPT project's challenge with a fresh access token
  - REQ-FUNC-5607e5cb - Observe native ChatGPT callback completion without manual submission
- deviations: 2 recorded
  - design: pinned Pi loginOpenAIChatGPT races its loopback callback with manual input (installed pi-ai openai-chatgpt.js lines 197-244). Native browser completion can exit the helper before manual submit. Add pending-login completion observation and GUI polling, retaining state-checked manual fallback. Interrupted the in-progress full proof rather than declaring incomplete native login valid.
  - validate: generated frontend assets have no direct requirement mapping and the minified bundle exceeds the automatic secret-scan size limit - reviewed requirement-linked sources, byte-identical production/test bundles and the complete frontend proof cover behavior; retain these three advisory heuristic warnings without changing the frozen candidate.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=5
- diff vs task base 858865e: 56 file(s) changed, 1567 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=36 notes=23
- checklist: 8/9 done; open: `report` appended
