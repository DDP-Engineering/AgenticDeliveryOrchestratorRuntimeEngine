<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-3809ee8f - Project executor configuration and durable model connectivity

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-4e9e7ecc, REQ-SEC-1c210f3f, REQ-DATA-f304fd2e
parent:
branch: task/adore-web-interface
base: a790851b460506dd152151e8b8f5b2e488922853
opened: 2026-10-06

## Done checklist (current stage)

- [x] unchanged validated candidate confirmed
- [x] validation, diff, exclusions and outcome presented under standing human authority
- [x] explicit direct human commit/push/deploy authority recorded
- [x] journal and report included in delivery candidate
- [x] agreed normal push and DCP deployment completed
- [x] truthful close-out recorded for this documentation-only followup commit

## Frame

Problem: STATED: model/executor settings are scattered and a successful explicit AI test is shown as not checked by host prerequisites.
Desired outcome: one Executor configuration tab and consistent saved, scoped connectivity evidence.
Actors: administrator configures/tests; authorized developer reads non-secret model/settings/evidence.
Primary scenario: open project Executor configuration -> prepare/apply executor/model candidate -> save provider key -> explicitly test -> revisit Summary/host checks -> observe the same current result.
Examples: Pi openai-codex/gpt-6-sol existing subscription authentication continues; all four supported executor model fields remain editable.
Counterexamples: saving a key is not successful provider authentication; successful nonce response is not full tool/job readiness; stale/foreign/corrupt evidence never passes.
In scope: single-owned executor settings, existing OpenCode endpoint editor, API-key connect/disconnect using project .env, guidance for external subscription logins, persisted model test evidence.
Out of scope: new OAuth brokers, dynamic provider/model inventories without installed-version evidence, changing shared CLI auth, paid live tests, full suite, new executor types, active job reconfiguration.
Constraints: STATED standing scope/stage/commit/push/deploy authority; one checkout owner; English artifacts/Romanian discussion; offline targeted tests only; four hours/three correction cycles/twenty authored files (workflow/generated separately).
Success signals: new tab; no duplicate executor editor in Settings; current evidence survives navigation and host recheck; credentials excluded from responses/audit and persisted privately.
Evidence: OBSERVED App.tsx owns SettingsList/local endpoint/ModelConnection; app.py model test does not persist; util.load_env_file plus executor.env_keys is reused by actual jobs and probes.
Assumptions: manual model IDs are preferable to a fabricated provider list. Existing configured command tables constrain executor choices.
Unknowns: image-specific interactive OAuth extensions; explicitly keep server login guidance rather than claim generic GUI OAuth support.
Decision-blocking questions: none for this bounded configuration/API-key workspace.
Proposed behaviors: below.
Path and reason: full; new UI/interface and secret/evidence lifecycle. Quick criteria: new behavior=yes, new interface=yes, dependency=no, existing requirement sufficient=no, security/data change=yes. No children.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary/failure | Verification | Design |
|---|---|---|---|---|---|---|
| One configuration workspace | Scoped executor tab/ownership | REQ-FUNC-4e9e7ecc | model candidate apply | Dev read-only/stale candidate | Chromium and API tests | reuse candidate contract |
| Credentials | Project provider key lifecycle | REQ-SEC-1c210f3f | save/delete allowlisted key | CSRF/role/active/config/env corruption | offline API tests | atomic private .env editing |
| Consistent evidence | Persist and invalidate test | REQ-DATA-f304fd2e | explicit success reload/host view | revision/key drift/corrupt/foreign record | offline API and Chromium | separate model-connection.json |

## Design

- REQ-FUNC-4e9e7ecc: add executor route/tab for both roles; reuse SettingsList with ownership filter (executor.*, OpenCode endpoint fields). Existing guarded single-candidate apply remains authoritative and refuses active work. Manual model IDs; existing configured executor choices. Existing endpoint form moves intact. Subscription login remains service-account CLI flow with executor-specific documented paths; GUI keys are not declared authenticated until explicit test.
- REQ-SEC-1c210f3f: new executor_settings module owns strict private .env reads/atomic edits and redacted presence/source views. PUT/DELETE executor-credentials input is exact variable/token/revision; only known provider API variables already in executor.env_keys accepted. Preserve unrelated environment lines; reject malformed/duplicate/symlink/oversized input. Ambient precedence is explicit and immutable from GUI. Guard config/StateStore locks, paused/idle/pending protection, actor audit attempt then confirmation without key/token values. Actual jobs and diagnostics already read the same .env: no launcher protocol change.
- REQ-DATA-f304fd2e: separate model-connection.json schema1 stores closed result, stable identity, config revision, UTC check time, internal SHA256 credential binding. Binding covers effective allowlisted environment and known host/bind auth files; stale returns null, malformed/foreign record raises safe typed error. Validate complete record before staleness comparison. Config read includes current redacted result; explicit test verifies unchanged binding before save. Host UI uses current explicit model result for model-access row, while OpenCode tool-stream endpoint result stays separately described.
- Flow: read config/result -> UI edits -> candidate review/apply -> private credential mutation -> explicit billed test -> durable evidence -> config refresh. Writes atomic; interrupted secret writes preserve original .env; evidence failure never reports a durable success. No web SQLite schema change, old installations missing evidence are untested. Rollback only release pointer; additive evidence retained.
- Security: secrets transient browser password input, erased after save/unmount; no localStorage/query/args/audit/export, 0600 .env; filesystem operations under profile lock. Unknown provider methods remain external; disconnect removes only selected project API key, not ambient/shared subscription sessions.
- Tests: API happy/negative for all4, scope/roles/CSRF/locks/config drift/.env corruption/evidence tampering; real existing offline diagnostic regression; Chromium workspace/candidate/credential/result and stale suppression.
- Expected files: executor_settings.py, app.py, test_executor_settings.py, test_model_connection.py; App.tsx, routes.ts, ExecutorCredentials.tsx, ModelConnection.tsx, ReadinessEvidence.tsx; executor-config.spec.ts/settings.spec.ts/model-connection.spec.ts; component/web/security/config docs and CHANGELOG. Legal generated assets/workflow separately. No new dependencies.
- Risks: subscription login cannot be universally embedded safely; local .env changes fail closed when malformed, and external auth changes invalidate known bindings. Full regression and real provider acceptance deferred by user.
- Architecture: Executor configuration -> existing guarded config candidate; API credentials -> project .env -> existing launcher/probe; explicit probe -> bound model-connection.json -> config read -> Summary/readiness/tab.

## Log

- 2026-10-06 frame: full path accepted under standing human authority; bounded project configuration/API-key flow and coherent model evidence; no new OAuth broker.
- 2026-10-06 specify: three atomic requirements created with offline positive/negative verification.
- 2026-10-06 design: reuse candidate/launcher contracts, new strict private credential/evidence module; see Design.

- 2026-10-06 build red: REQ-SEC-1c210f3f/REQ-DATA-f304fd2e command=`.venv/Scripts/python.exe -m pytest -q tests/test_executor_settings.py -k "survives_reload or private_scoped"` (04_Software); exit=1; five expected failures: credential route absent (405), successful explicit evidence absent from config.

- 2026-10-06 build red: REQ-FUNC-4e9e7ecc command=`npx playwright test e2e/executor-config.spec.ts --project=chromium`; exit=1 against pre-change .e2e-dist; expected missing Executor configuration tab/route. Backend initial increment: twenty credential/evidence tests pass offline.

- 2026-10-06 build complete: twenty authored paths plus generated/workflow paths; production typecheck/build and scoped Ruff passed. Targeted Python test_executor_settings/test_model_connection/test_web_readiness: exit=0, 67 passed; test_web_config: exit=0, 10 passed. No provider/container live tests run.
- 2026-10-06 validate semantic inspection: reviewed all credential/evidence routes, source/presence-only responses, private atomic writes, actual launcher .env compatibility, paused/idle/CSRF/revision guards, evidence identity/schema/credential binding and tab ownership. Configuration output is validated before derived-field reads; locale remediation targets Executor configuration. Existing subscription mounts remain external and preserved. Requirements, operator/component/current knowledge and architecture were reconciled.
- 2026-10-06 validate specification review (separate same-agent lens, not independent reviewers): approved, round=1; current candidate implements the three active requirements and excludes a universal OAuth broker, fetched model inventory and paid automatic probes. Existing config API proof verifies apply/revision/role contracts; Chromium verifies tab, staged/discarded candidate and settings separation. No children.
- 2026-10-06 validate implementation-quality review (separate same-agent lens, not independent reviewers): approved, round=1; current candidate fails closed on secret/evidence corruption, unauthorized/stale/active mutations and concurrent credential drift; secrets absent from UI responses/audit; atomic failure preserves source bytes. Known external auth binding limits are documented.
- 2026-10-06 DEVIATION validate: full check --strict --run is prohibited by the human’s iterative-testing instruction. Substitute targeted Python/Chromium tests, production typecheck/build, scoped Ruff, diff whitespace and strict catalog advisory without --run; full regression and actual provider/job acceptance remain deferred.

- 2026-10-06 validate final proof: same candidate production build/typecheck exit0 (index-BZ4YgyAl.js), build:e2e/typecheck exit0 and scoped Chromium six tests exit0 (18.8s). Python targeted67 + config10 exit0; scoped Ruff exit0; diff --check exit0. Final evolution at18:17:17Z reviewed all23 non-workflow paths: twenty authored plus three generated asset/index changes; removed bundle replaced by deterministic build. Strict advisory without --run exit0: zero errors, nine unpromoted warnings,25 notes. Unrelated historical asset paths/two tracked sidecars/journal syntax retained; initial malformed ruling is append-only and clarified by valid RULING-002. Minified generated bundle unscannable by heuristic, source and offline fixtures reviewed; no real secrets. Existing Starlette deprecation, bundle size and terminal-color warnings accepted as out-of-scope tooling/presentation. No full suite or paid live acceptance claimed.
- 2026-10-06 deliver presentation: new Executor configuration tab, current model access across Summary/host verification and protected project API credential lifecycle; twenty authored paths and generated UI assets plus workflow evidence will be committed. Excludes GUI subscription OAuth, fetched model lists, active-work changes, original epic continuation, release/PR/merge and real provider acceptance. Human directly authorized implementation and ongoing normal commit/push/DCP deployment; RULING-002 applies without repeated permission. DEVIATION validate repeated: full suite deferred by explicit user instruction; scoped proof above substitutes for this iterative deployment.

- 2026-10-06 deliver completed: implementation commit f2c3e05b8d56202abe249a727dcf54ce2cff6cfb normally pushed and exact remote branch hash verified. DCP HTTPS18443 deployed from archived committed04_Software/LICENSE to /home/dpasare/apps/adore/web-ux-f2c3e05; backup=/home/dpasare/apps/adore/backups/web-ux-f2c3e05-20261006211958. Both services active, selected PYTHONPATH points to release; served JS/CSS match archived build byte-for-byte; DB schema14/integrity ok. Actual /api/v1/health JSON alive and /api/v1/ready JSON ready/worker-ready; root/assets200, unauthenticated projects401. Existing profiles/auth/jobs preserved. No automatic provider test or complete-job acceptance run. Closeout changes journal only; no second deployment required.

## Rulings

- RULING-1 | 2026-10-06 | Human explicitly authorized implementation, routine checkpoints, validation, commit/push and deployment in this iterative session; user requests targeted verification only and full suite at end. Scope checkpoints continue unattended; validation is still required. Four-hour/three-fix-cycle/twenty-authored-file bound; no subagents.


- RULING-002 | date=2026-10-06 | decision=Human authorizes routine stage continuation, implementation, targeted validation, commit/push and deployment; full suite deferred during iterative live changes. | reason=Restates explicit direct human instructions in valid journal syntax; preserves previous ruling history. Four hours, three fix cycles, twenty authored files; no subagents. | source=user | supersedes=none

## Handoff


current: done
status: ready
next: human refresh and explicit configured model connection test; full regression at end
must_read: .agentic/tasks/TASK-3809ee8f.md, .agentic/steps/6_deliver.md
blockers: none

## Stage report


stage: done
result: completed
current: done
changed: twenty authored files; workflow and generated assets separately
evidence: 77 targeted Python tests, six Chromium journeys, Ruff/build/advisory; pushed f2c3e05 and verified DCP services/assets/health/ready
issues: full suite deferred by explicit user instruction; existing Starlette deprecation and bundle-size warning
next: human live model test; full regression at end
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-06)

- stage: deliver; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-4e9e7ecc - Project executor configuration workspace
  - REQ-SEC-1c210f3f - Project provider API credential lifecycle
  - REQ-DATA-f304fd2e - Revision-bound model connection evidence
- deviations: 1 recorded
  - validate: full check --strict --run is prohibited by the human’s iterative-testing instruction. Substitute targeted Python/Chromium tests, production typecheck/build, scoped Ruff, diff whitespace and strict catalog advisory without --run; full regression and actual provider/job acceptance remain deferred.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base a790851: 32 file(s) changed, 1251 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=10 notes=25
- checklist: 4/6 done; open: agreed normal push and DCP deployment completed; truthful close-out committed after deployment
