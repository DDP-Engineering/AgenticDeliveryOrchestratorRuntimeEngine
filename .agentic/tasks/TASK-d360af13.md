<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-d360af13 - Gitea #26: agent-led dependency and system package installation inside containers

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-c405688e, REQ-SEC-c5d56d9f, REQ-REL-6922cfe5, REQ-UX-812acd4b
parent:
branch: ddp/26-agent-system-packages
base: 7a588905de14d68503d47a6321b0e9c3b1114d32
opened: 2026-10-30

Before editing this journal, read `.agentic/templates/task.md` for record syntax
and pause/report rules. Reuse its guidance if already read in this intact session.

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: STATED user requests Gitea #26; OBSERVED standard executor image ends as non-root adore without sudo authorization; container configuration has no dedicated package permission.
Desired outcome: STATED agent directly installs project libraries and system packages, interprets failures and adapts installation while network access remains separately configured.
Actors: STATED operator, ADORE conductor, coding executor in its job container; OBSERVED Docker/Podman with optional WSL transport.
Primary scenario: STATED opted-in job starts -> agent discovers and directly installs missing dependencies -> observes exit/output, corrects failures and runs project checks within existing budgets.
Examples: STATED #26 missing compiler/native library discovered during installation; agent installs the prerequisite then retries. INFERRED a Python wheel build can need a compiler.
Counterexamples: STATED enabling package rights cannot enable network, grant host installation, expose forge credentials or authorize publication/merge; a new container cannot inherit an assumed successful installation.
In scope: STATED opt-in container package authority, direct noninteractive agent execution, independent egress, CLI/GUI configuration, stage prompts, bounded results, pinned recovery, docs/help/release notes and offline contract tests.
Out of scope: STATED mandatory dependency scanner, deterministic installation broker, replacement of recipes, native-host installation, automatic GUI image builds, automatic monitoring/publication; no release assignment requested.
Constraints: OBSERVED repository rules require offline tests, Doxygen/legal headers, setup scripts under 02_Tools, four-locale help, component docs, standard-library core and preserved unrelated changes. STATED existing profiles receive no implicit elevation.
Success signals: STATED permitted agent commands can install system packages and observe results; all three egress modes retain their configured boundary; unavailable privileges and corrupt recovery evidence fail explicitly; worktree ownership stays usable by host Git.
Evidence: OBSERVED tea issue 26 is open with no comments; config.py ContainerConfig/ContainerEgressConfig, isolation.py provision/exec, execution.py ContainerBackend, preparation.py execution_policy/validate_plan, state.py validate_execution_record, orchestrator.py _provision/_stage_prompt; inspected egress/config test assertions, not executed tests.
Assumptions: INFERRED standard image can supply a noninteractive sudo facility; exact package-manager command support needs design. Existing custom-image privileges remain operator-owned.
Unknowns: Exact configuration name, sudo policy, bootstrap/readiness transport and durable binding are design choices; no live Docker/Podman or provider acceptance has been performed.
Decision-blocking questions: None for the agreed outcome; implementation choices will be resolved and recorded at design.
Proposed behaviors: Opt-in permission separate from egress; preserve non-root agent/worktree identity while authorizing direct package-manager elevation; pin policy and resource using existing execution evidence.
Path and reason: full; new configuration and privilege boundary require specification and design. One tightly coupled task, no implementation children. Retain current non-default task/adore-web-interface branch per frame rule, preserving existing dirty checkout.

| Quick-path criterion | Answer | Evidence |
|---|---|---|
| no new externally observable behavior | no | #26 adds package installation authority |
| no new interface or data format | no | explicit CLI/GUI permission |
| no new dependency | unknown | sudo provision depends on design |
| existing requirement already covers the behavior | no | inspected preparation contract describes pre-agent recipes |
| no security- or data-handling behavior changes | no | administrative permission inside container |

Execution bounds: at most 4 hours, 80 task-owned files, 5 review/fix rounds, no paid model calls or live installations; offline verification uses repository commands. Existing dirty files are baseline, not this task's changes.

### Newly authorized live acceptance and correction phase

STATED the user now requests rebuilding the executor image, real execution of project/ticket #25, and generic ADORE corrections that work across repositories. This explicitly extends the earlier offline-only scope and permits the existing selected model/account to perform that live job. Keep repository-specific names/paths in operator configuration, never in reusable product logic. Existing draft/publication/human-merge boundaries remain.

OBSERVED Docker in Ubuntu/WSL builds the new image; non-root sudo authorization preserves network none, and a separate bridge container installs jq while retaining UID 1000. The selected live job has passed frame into specify. OBSERVED its retained frame archive is 65538 bytes despite the documented 65536-byte maximum; common archive write_text uses Windows newline conversion. INFERRED redaction/UTF-8 replacement expansion also needs final encoded-size enforcement; prove this through public gate tests before changing implementation.

Execution bounds for this newly authorized phase: four hours of controller correction/verification, the same 80 final task-owned files, and five review/fix rounds for the expanded scope. The live job retains its explicit 12 iterations, 5400 seconds, USD 5 and 120-file budget. This supersedes the earlier no-live/no-paid limitation only for this requested acceptance run. Preserve all old failure/history and unrelated dirty work.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| functional | When container.system_packages is explicitly enabled, ADORE shall authorize the non-root job agent to execute supported system package managers directly and noninteractively inside its container, retaining command results for adaptive dependency preparation within existing run limits. | REQ-FUNC-c405688e | Enabled owned container | Invalid input/resource or unavailable privilege | Offline runner tests observe authorization before AI and a non-root direct sudo package-manager invocation; missing sudo, root agent identity, malformed output and unsuccessful authorization fail closed. | See Design and shared spec |
| security | When administrative package installation is enabled for a container, ADORE shall preserve its separately configured open, none or allowlist-proxy egress and host/forge credential boundaries. | REQ-SEC-c5d56d9f | Enabled owned container | Invalid input/resource or unavailable privilege | Offline Docker, Podman and WSL argv tests cover all three egress modes with package authorization; unsafe container overrides and local-backend elevation are refused. | See Design and shared spec |
| reliability | When a package-enabled job is resumed, ADORE shall bind installation authority to its persisted policy and exact container/image identities, failing explicitly on drift or resource loss rather than assuming the prior installed environment exists. | REQ-REL-6922cfe5 | Enabled owned container | Invalid input/resource or unavailable privilege | Offline conductor and persisted-state tests cover same-container resume, policy changes, replaced/missing resources and corrupt package permission fields, while legacy disabled policy plans remain readable. | See Design and shared spec |
| ux | When an administrator configures a container project, ADORE shall expose a separately reviewed boolean permission for agent system package installation, defaulting to disabled without changing network settings. | REQ-UX-812acd4b | Enabled owned container | Invalid input/resource or unavailable privilege | Offline API tests inspect metadata, stage/apply an exact boolean candidate with paused idle guards, and reject malformed/unauthorized/stale requests; frontend tests verify localized container-only visibility. | See Design and shared spec |


## Design

- REQ-FUNC-c405688e: `container.system_packages: bool = false`; base image supplies sudo, never default authorization. A bounded root runtime exec configures sudoers for the measured non-root numeric UID; agent directly invokes `sudo -n` package managers and observes its own output. No ADORE installation broker.
- REQ-SEC-c5d56d9f: authorization command injects no additional provider secrets and changes no network; sudo retains only proxy variables. Refuse elevated host-oriented run_args in opted-in mode. Root package scripts are effectively container-root authority, not a restricted sandbox; shared repo/worktree/IO/cache remain shared surfaces.
- REQ-REL-6922cfe5: use existing execution plan/resource record even without a recipe; new policy field appears only when true to preserve disabled legacy fingerprints. Validate its exact boolean type; persist actual resource IDs. Missing/replaced containers and changed settings require a fresh run; no replay of assumed installed packages. Recipes retain existing recovery.
- REQ-UX-812acd4b: generic reviewed boolean settings row under Agent and model, four-locale label/help; existing admin/CSRF/pause/idle/revision guards. No egress mutation or image build from the GUI.
- Interfaces: `ContainerManager.authorize_system_packages(name)` and container-only conductor authorization; image must contain python3, sudo/visudo and supported package-manager executables. False leaves externally managed images untouched and grants no ADORE sudo permission.
- Ordering: resolve/persist policy -> provision -> bind resource identity -> authorize -> tool checks/auth/preparation -> agent. The root script clears its subprocess environment; container-wide credentials remain within container-root authority; no new dependency on host packages.
- Recovery: bounded authorization can repeat on the same verified resource; nonzero/timeout/malformed identity fail typed. Per-agent installation runs inside existing gate budget/cancel lifecycle. Prompt states current network, scope and reinstall-on-fresh-container behavior.
- Alternatives: whole-agent root risks root-owned worktree files; deterministic broker loses agent control; neither selected. Direct package-manager sudo retains normal user ownership for code and library installs.
- Expected files: linked requirement source paths, Dockerfile.executor-base, config.example.toml, offline focused tests, four-locale help, component and operator docs, changelog/release notes. Setup scripts, if introduced, belong under 02_Tools; runtime permission code is product code and installs no packages.
- Risks: root package scripts can alter the entire container; image/version compatibility and executor sandbox settings must support noninteractive sudo. Live container acceptance remains unperformed and will be reported separately from offline proof.
- Retained-output decision (REQ-FUNC-c405688e): optional launcher package_secrets argument caps live and archived stdout/stderr at 64 KiB each after the gate, redacts known credentials, and streams complete original usage before truncation. Extend executor launcher/base and focused public gate tests; no native/legacy behavior change.
- Open decisions: none blocking implementation; enabled mode supports the standard sudo-capable Linux image and fails explicitly on incompatible custom images.
- Diagrams: [diagram_TASK-d360af13.md](diagram_TASK-d360af13.md).


## Log

- 2026-10-30 frame: full path for #26 privilege/configuration behavior; scoped outcome accepted from implementation request and explicit session autopilot. Existing unrelated dirty files retained; no product changes yet.

- 2026-10-30 specify: four new draft atomic requirements and shared spec cover authority, independent egress, pinned recovery and reviewed settings; reused recipe contracts remain unchanged.

- 2026-10-30 design: authorization, independent network, pinned recovery and reviewed boolean decisions saved in Design/spec and diagrams; advisory check errors=0, existing baseline warnings retained.

- 2026-10-30 build red: REQ-FUNC-c405688e, REQ-SEC-c5d56d9f, REQ-REL-6922cfe5; command=`04_Software/.venv/Scripts/python.exe -m pytest -q tests/test_system_packages.py` (cwd 04_Software); exit=1; 40 failed, 4 passed; expected missing config/authorization/pinned resource behavior.

- 2026-10-30 build red: REQ-UX-812acd4b; commands=`.venv/Scripts/python.exe -m pytest -q tests/test_system_packages.py -k package_setting` (04_Software) and `node --test tests/systemPackages.test.mjs` (web); both exit=1; missing editable setting and localized container-only row.

- 2026-10-30 build red: REQ-FUNC-c405688e executor compatibility; command=`.venv/Scripts/python.exe -m pytest -q tests/test_system_packages.py -k codex_workspace`; exit=1; workspace sandbox was accepted despite preventing administrative installation.

- 2026-10-30 build red: REQ-FUNC-c405688e retained-output contract; command=`.venv/Scripts/python.exe -m pytest -q tests/test_system_packages.py -k package_gate`; exit=1; launcher lacks package-output retention policy. Existing container launcher archives unbounded raw output, so opted-in mode needs a bounded/redacted retention path; native/legacy mode remains unchanged.

- 2026-10-30 build green: focused Python command covering system_packages, config, execution, preparation/lifecycle, isolation, executor, orchestrator and web executor configuration: exit=0; 422 passed, 1 skipped (existing platform condition). Node focused systemPackages/settings/help: exit=0; 32 passed.
- 2026-10-30 release-notes: updated (merged agent installation into existing Executors entry to preserve the ten-entry category bound).
- 2026-10-30 help: updated (executors and settings in en/fr/de/ro with aligned system-packages sections).

- 2026-10-30 build: implementation, operator/component docs, four-locale help and release notes complete; evolution reviewed, 47 product/doc files all within scope. Advance to validate for integrated review and final proof.

- 2026-10-30 validate: runtime permission script exercised with offline identities/processes and linked-output refusal tests; focused system_packages suite 60 passed. Production frontend build passed; only the existing large-chunk advisory remains. Current authorization uses immutable container IDs, not replaceable names.

- 2026-10-30 validate review round 1: both independent verdicts changes_required on candidate a86a532c00ae5ce7f6854f68f9ec1c39becd53f43117a3be73db3c474ed15a32 (hashes unchanged before/after). Findings: retention truncation loses authoritative usage/cost and weakens budget; package redaction omits staged subscription auth values. Return to build to fix these findings, then re-review both roles.

- 2026-10-30 build red (review corrections): command=`.venv/Scripts/python.exe -m pytest -q tests/test_system_packages.py -k "complete_original_usage or subscription_auth_snapshot"`; exit=1; four expected failures show lost late OpenCode/Codex/Pi telemetry and missing staged subscription token in redaction.

- 2026-10-30 build correction green: complete original usage is streamed separately from retained text; exact staged subscription snapshot values are kept in memory for redaction. Focused system_packages + executor command exit=0: 93 passed. Includes late OpenCode/Codex/Pi telemetry and auth-file rotation cases.

- 2026-10-30 validate: corrected package suite 70 passed, including bounded/duplicate/depth subscription-auth failures. Ruff passed; round 2 reviews requested for the refreshed candidate before full proof.

- 2026-10-30 validate review round 2: specification compliance approved and implementation quality approved on binding 1d469cbfe83a3842232d136239f555dfbd73e27e2e8765ea361ee0d60f9afd31; each reviewer confirmed all 69 hashes before/after. Both round-1 findings resolved; quality independently ran 9 focused tests successfully. Final strict full proof is next.

- 2026-10-30 validate full proof: `python .agentic/aegis.py check --task TASK-d360af13 --strict --run`; exit=1 after 714.5s. Python: 2148 passed, 8 skipped, 2 failed; lint passed; frontend unit stage failed on missing legacy error translations. Missing new settingKeys entry is task-owned; stale _probe_setup fixture and missing host/local-identity error translations were unchanged from build anchor.
- 2026-10-30 DEVIATION validate: include minimal repair of pre-existing test fixture signature and two four-locale error messages in two additional files, required to complete mandatory integrated proof; no host/container/provider actions. Both repairs will be independently reviewed.

- 2026-10-30 build correction: register system_packages in settingKeys and all settingHelp locales; restore legacy probe-fixture keyword compatibility and localized folder/account errors as announced. Focused previously failing Python tests: 2 passed; frontend catalog/help integration then verified by npm test.

- 2026-10-30 build correction green: previously failing Python cases 2 passed; complete frontend unit suite 115 passed; Ruff passed. Rebuilt production assets include catalog/help/error corrections. Round 3 review required before rerunning full strict proof.

- 2026-10-30 validate review round 3: both independent reviewers approved binding c91b470b472e1c6e584198da3e88bf56c306e4c02fbfabcf3dba8a20967283f0, verifying all 74 paths before/after. Catalog/help complete; two minimal baseline repairs accepted as documented; no open findings. Final full strict proof follows.

- 2026-10-30 validate final proof attempt 2: same full strict command exit=1 after 921.3s; backend passed (483.6s), lint passed (0.1s). Frontend interrupted after observed enrollment locale contamination (436.1s), so browser suite is unproven. A localized branch-marker test leaves shared account language at ro; subsequent English Overview assertions fail. Unit frontend was green before this attempt. Catalog: 169 pre-existing warnings, 22 notes, one failed-command error.
- 2026-10-30 DEVIATION validate: repair pre-existing enrollment test preference restoration in one additional E2E file; no product behavior change. Save/restore language on both localization loops even when an assertion fails, then re-review.

- 2026-10-30 build correction green: enrollment.spec.ts was identical to build anchor before repair; both locale loops now restore shared English preferences in finally and assert successful cleanup. Focused Chromium sequence (four branch markers, next ordinary scenarios, four guidance locales) passed all 10 cases in 16.7s. Product source unchanged.
- 2026-10-30 validate advisory disposition: 169 warnings = 93 uncovered-source, 40 outside-layout, 16 stale-paths, 11 legacy journal-header, 8 secret-in-diff and 1 tracked fingerprint. These belong to existing catalog/history/archives or generated assets. Full generated-JS built-in-pattern scan found no key/token patterns; password heuristic requires UI/computed-field classification. Existing fake test passwords and archived binary scan gaps are outside this task.

- 2026-10-30 validate warning disposition completed: full generated JS scan matches only password-field boolean/computed references, localized labels (including whitespace-truncated Mot de passe) and empty inputs; no key/token/private-key patterns. Remaining binary gaps and test-password warnings are pre-existing/outside task; legacy catalog warnings do not weaken the focused boundary coverage or required full suite.
- 2026-10-30 validate review round 4: both independent verdicts approved binding 6673e38ea191d5d78a3deaed8eb7f82545269711f0c71a6c20cc1f3fd1d97b74; 75 paths verified unchanged before/after each review. Localized assertion coverage preserved; final full proof follows.

- 2026-10-30 validate full proof attempt 3: backend passed in 512.7s, lint passed in 0.1s; complete frontend exited 1 in 1008.5s with exactly two browser failures. images test hardcodes old Agent and model (9), invalidated by the new tenth setting; Jobs test expects superseded hint text and was identical to the build anchor. Return to build for two focused test-contract repairs.
- 2026-10-30 DEVIATION validate: include the minimal baseline Jobs notice-text expectation correction in one additional E2E file, retaining queued/failed/not-finished assertions. Images selector repair is required integration coverage for this feature.

- 2026-10-30 build correction green: image disclosure now uses its existing semantic executor-purpose selector; Jobs notice expects current single-ticket/other-checks wording with queued/failed/not-finished assertions retained. Both focused Chromium tests passed in 10.8s. Product behavior/source unchanged.

- 2026-10-30 validate candidate accounting: 76 final bound paths plus journal/anchor/evolution/manifest = 80 task-owned files. Drop absent intermediate Co3jBfsL bundle from candidate binding: it was generated during this task, never existed at build anchor and is not part of the final change. Original removed BkffVkY1 bundle remains bound.

- 2026-10-30 validate review round 5: both independent verdicts approved binding 6012ded2c44546611ee0d70e58f03524b64d759aa5cfea90dc65a3c5ee8e9ed1, verifying all 76 hashes before/after. No open findings; no product edits since round 3. Final full proof next, using UTF-8 JSON transport for complete successful-command evidence.

- 2026-10-30 DEVIATION validate: accept uncovered-source catalog warnings on images.spec.ts and jobs.spec.ts; these are existing browser tests executed by configured frontend validation, not untested new product behavior. Focused two-case proof is green and original functional assertions remain. No source/catalog contract is changed merely to silence the warnings.

- 2026-10-30 validate FINAL PROOF: `python .agentic/aegis.py check --task TASK-d360af13 --strict --run --json`; exit=0; 1334.3s total. Configured test: 2150 passed, 8 existing platform skips, 1 upstream test-client deprecation warning (588.2s); lint: passed (0.1s); frontend npm validate: unit suite, typecheck/build and all 226 Chromium scenarios passed (744.4s). Strict: 0 errors, 170 advisory warnings, 22 notes, 0 promoted warnings. No required checks omitted and no remaining test failures. Release-notes check previously passed on unchanged notes; production assets already rebuilt from unchanged reviewed frontend source.
- 2026-10-30 validate warning disposition: final catalog has 94 uncovered-source, 40 outside-layout, 16 stale-paths, 11 legacy journal-header, 8 secret-in-diff and 1 tracked-fingerprint warnings. Existing catalog/history/archive findings remain outside task; browser-test path warnings are covered by focused and complete configured frontend execution. Generated JS was fully scanned with built-in secret patterns; remaining password matches are localized labels, empty input and computed/boolean fields. The upstream test-client warning changes no assertions. Existing eight skips cover platform conditions, not the new package contracts.
- 2026-10-30 deliver inspection: current binding equals final-proof/review binding 6012ded2c44546611ee0d70e58f03524b64d759aa5cfea90dc65a3c5ee8e9ed1 on all 76 tracked/untracked/deleted paths; no post-proof candidate edits. Final task-relative evolution: 58 files (6 added, 51 modified, 1 removed), plus AEGIS requirements/spec/knowledge and records. No child task journals; parent full proof integrates all changes. Git remains on task/adore-web-interface with an empty index and pre-existing unrelated dirty work preserved.
- 2026-10-30 deliver approval pause: propose a repository-local #26 commit with requirement IDs, implementation, tests, docs/help, release notes and announced baseline repairs; exclude unrelated pre-existing changes. No commit, push, PR, image build, live package installation or issue update performed. Operator image rebuild and live Docker/Podman acceptance remain unperformed. Human delivery choice is required by step 6 even in autopilot.

- 2026-10-30 proof clarification: final output reports 8 skipped tests but does not enumerate their reasons; platform-only wording above is not established by that output. The new focused package suite passed all 70 cases without skips. Final skip count remains 8 and no new contract is claimed tested through a skipped case.

- 2026-10-30 build resumed for explicit expanded user scope (live #25 acceptance plus repository-agnostic corrections). Current candidate reviews/proof are historical; clear both verdicts and begin a new bounded review loop under the stage-5 explicit scope-change rule. Live archive 65538 bytes reproduces a 64 KiB contract violation on Windows; correct common retention/archive encoding, not repository logic.

- 2026-10-30 live correction red: public gate test parametrization for multiline, redaction expansion and malformed UTF-8; `pytest -q tests/test_system_packages.py -k retention_bounds_encoded --tb=short`; 1 failed, 2 passed. Windows archive grows to 78632 bytes through newline translation; existing shared redactor already correctly bounds the other two cases. Fix only archive UTF-8 serialization.
- 2026-10-30 release-notes: updated (merge archive byte-bound correction into existing Executors fixed note in four locales).
- 2026-10-30 help: none (setting/workflow unchanged; operator/component documentation clarifies existing byte limit).

- 2026-10-30 build correction green: common archive stdout/stderr now use direct UTF-8 byte writes, with no platform/repository/executor-specific branch. Existing redaction byte bounding is retained unchanged. Public tests reproduce Windows multiline expansion and preserve redaction/malformed-UTF-8 bounds; focused package+executor suite: 101 passed, Ruff passed, release-notes check passed. Live issue 25 continues independently in specify.

- 2026-10-30 validate expanded-scope review round 1: specification compliance and implementation quality both approved binding 20555e32f5063b2b243ecd804b1cbaf47f8bd24ddd4cfcd4344aba610bfa1d93; each confirmed all 76 hashes before/after. Common archive encoding fix matches the byte-bound contract; no blocking findings. RULING-003 preserves the actual user scope and corrects the prior descriptive supersedes value without editing append-only history. Full strict proof follows.

- 2026-10-30 live corrected-archive proof: a separate disposable Docker container with only a temporary Windows IO mount produced multiline Romanian UTF-8 stdout/stderr through the real manager exec seam and current shared gate launcher. Each live and immutable archived stream matched the returned UTF-8 bytes exactly at 65530 bytes, below 65536. No model/provider call was made for this stream check; container and OS temporary directory were removed. Ongoing issue 25 uses its already-started controller; this separate check verifies the corrected code without restarting or altering that job.

- 2026-10-30 expanded-scope FINAL PROOF: `python .agentic/aegis.py check --task TASK-d360af13 --strict --run --json`; exit=0 after 1646.7s on binding 20555e32f5063b2b243ecd804b1cbaf47f8bd24ddd4cfcd4344aba610bfa1d93. Python 2153 passed, 8 skipped, 1 upstream warning (803.7s); Ruff passed (0.1s); full frontend passed including 226 Chromium scenarios (841.3s). Strict catalog: 0 errors, 172 advisory warnings, 22 notes, no promoted warnings. Existing catalog dispositions remain; journal-only historical ruling metadata was corrected append-only without changing user authority. No required verification omitted. All 76 current hashes match the reviewed/proved candidate. Live issue25 acceptance continues separately in build.

- 2026-10-30 live acceptance detail: rebuilt adore-executor-base:1.0.0 and system-packages-20261030 in WSL Docker (image sha256:2b5d5cc01daab089eb81cbe33a2e992aa183e91acdf85b63819291abac8889c0); all four bundled executor CLIs run. Disposable network-none container authorized package managers without changing network or UID 1000; separate bridge container installed jq 1.6 with sudo apt-get and retained UID 1000. Both containers removed. Real issue25 model separately executed uv sync --locked --extra web --group dev; no model-issued OS package install observed yet. Active job, original failed run and collision-attempt evidence remain preserved.
- 2026-10-30 advisory clarification: append-only RULING-002 contains invalid supersedes metadata and RULING-003 consequently references an unparsed predecessor; both historical warnings remain in the final count of 172 (170 catalog/history warnings plus these 2 journal warnings). Earlier wording about correction records intent, not a clean parser result. Actual user authorization in this conversation and Frame independently establishes live scope. No source or requirement changed after final proof.

- 2026-10-30 live budget clarification: active clock started 12:43:59Z; configured 5400s threshold is 14:13:59Z. Configuration_Reference explicitly defines time/cost checks between attempts and permits an in-flight attempt to exceed a cap up to its own timeout. Current Build session started 13:55:20Z with the unchanged 1800s gate timeout (upper end about 14:25:20Z plus bounded cleanup). Earlier commentary described 90 minutes too strictly; clarified this documented contract to the user. No runtime budget or product behavior changed; continue observing the bounded current attempt and terminal outcome.

- 2026-10-30 live acceptance terminal: real issue25 executed six OpenCode sessions in the rebuilt Docker/WSL container, progressed frame/specify/design and three Build sessions with two successful durable Build continuations. Model installed project Python dependencies using uv sync, interpreted the 120000ms shell-test timeout, retried with 300000ms and achieved 961 passed/1 upstream warning in 171.65s. No final Azure completion is claimed. Manual read-only probes inside this exact job container confirmed UID 1000, sudo -n apt-get availability and unchanged bridge/open network; OS installation itself was verified separately with jq in the disposable bridge container.
- 2026-10-30 live terminal boundary: session6 hit EXECUTOR_TIMEOUT at 14:25:21Z after 1800s; the next loop check recorded BUDGET_EXHAUSTED at 14:25:22Z (active clock 12:43:59Z, configured threshold 5400s). This matches documented between-attempt checks; no budgets reset or extended. Container is stopped and CLI exited. Latest 20 modified/new paths, including Azure adapter/tests, remain preserved locally, uncommitted; preceding WIP checkpoint 3b36d3639879a44134b987921e6744a4db3d806d is pushed to ddp/adore-container/25. Full issue25 implementation, GUI/help remainder and final validation remain unfinished. No final PR or merge occurred.
- 2026-10-30 post-run recovery inspection: installed AEGIS status exits 0, emits schema1 and reads TASK-a9d1007b at Build after timeout. Both profiles remain paused; both have no pending/running web operations. Restarted source worker and API on corrected code; health and ready both return 200. Existing accounts, original failed run backup, worktree and retry evidence preserved.
- 2026-10-30 deliver inspection: all 76 tracked/untracked/deleted path hashes equal reviewed/final-proof binding 20555e32f5063b2b243ecd804b1cbaf47f8bd24ddd4cfcd4344aba610bfa1d93; both current review verdicts approved, no post-proof candidate edits. Exact task-relative delta: 58 product/test/doc/asset paths (6 added, 51 modified, 1 removed), 18 AEGIS paths and four journal/evidence records, total80. No AEGIS child tasks. Root checkout has 276 dirty paths including pre-existing work; index remains empty on task/adore-web-interface. This is not an instruction to commit the entire checkout.
- 2026-10-30 deliver approval pause: software correction and requested image/live acceptance work are complete locally; issue25 has an honest bounded incomplete outcome. Propose a repository-local #26 delivery containing only the task-relative feature/correction, tests, docs/help/release notes, AEGIS records and the already announced minimal baseline repairs; preserve unrelated pre-existing work and the separate live issue25 worktree. No root commit/push/PR approved or performed. Retain all announced deviation dispositions: probe fixture/error translations, enrollment locale cleanup, Jobs notice expectation, and advisory catalog gaps for existing E2E paths. Await human delivery choice as required by step6, including in autopilot.

- 2026-10-30 human delivery approval: user explicitly approves the repository-local #26 and generic archive correction commit, raises the live issue25 budget and requests resume through implementation/validation with autopilot retained. Binding remains unchanged on all76 paths; both independent approvals and final full proof remain current. Prepare a local baseline snapshot of pre-existing Git-visible work and a separate ddp/26-agent-system-packages delivery commit whose diff contains only the task; original checkout/index remain untouched. Baseline parent is local context, not authorized remote publication.

- 2026-10-30 local delivery close-out: user-approved outcome is the local commit itself. Baseline 9ffd87545612b30e227103eaea240fb45483debd preserves pre-existing Git-visible work under refs/adore/local-baselines/TASK-d360af13; delivery branch ddp/26-agent-system-packages carries only the approved task diff over that context. Original checkout and real index stay unchanged. Anchor/evolution remain machine-local by managed ignore policy; candidate manifest and journal/report are included. Report-time advisory snapshot is 0 errors/173 warnings/22 notes over the entire dirty checkout, not a new proof; final 76-path binding and full-test evidence remain unchanged. Close-out is included before the atomic local branch creation as required for a commit-only outcome.

## Rulings

- RULING-001 | date=2026-10-30 | decision=Use autopilot for this task without editing repository-wide interaction settings | reason=User explicitly requested autopilot=true for this session | source=user | supersedes=none

- RULING-002 | date=2026-10-30 | decision=Extend work to a rebuilt container image, real execution of selected project/ticket 25 and generic ADORE corrections discovered during it | reason=User explicitly requested real testing and corrections that work across repositories | source=user | supersedes=offline-only acceptance scope

- RULING-003 | date=2026-10-30 | decision=Retain the user-requested expanded scope of live ticket 25 execution and repository-agnostic ADORE corrections | reason=Administrative correction of RULING-002 supersedes metadata; the human instruction and authority are unchanged, and no extra scope is granted | source=user | supersedes=RULING-002

## Handoff

current: done
status: complete
next: Local delivery complete; issue25 continuation is separate operator work
must_read: .agentic/tasks/TASK-d360af13.md
blockers:

## Stage report

stage: done
result: completed
current: done
changed: Approved #26 feature and generic UTF-8 archive correction delivered locally
evidence: Unchanged approved binding; 2153 Python and 226 browser tests passed; live acceptance recorded
issues: Report-time advisory warnings retained; issue25 continuation remains separate
next: Continue the authorized issue25 implementation and validation
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-30)

- stage: deliver; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-c405688e - Direct agent package installation
  - REQ-SEC-c5d56d9f - Independent package and network authority
  - REQ-REL-6922cfe5 - Pinned package-enabled execution recovery
  - REQ-UX-812acd4b - Reviewed package installation permission
- deviations: 4 recorded
  - validate: include minimal repair of pre-existing test fixture signature and two four-locale error messages in two additional files, required to complete mandatory integrated proof; no host/container/provider actions. Both repairs will be independently reviewed.
  - validate: repair pre-existing enrollment test preference restoration in one additional E2E file; no product behavior change. Save/restore language on both localization loops even when an assertion fails, then re-review.
  - validate: include the minimal baseline Jobs notice-text expectation correction in one additional E2E file, retaining queued/failed/not-finished assertions. Images selector repair is required integration coverage for this feature.
  - validate: accept uncovered-source catalog warnings on images.spec.ts and jobs.spec.ts; these are existing browser tests executed by configured frontend validation, not untested new product behavior. Focused two-case proof is green and original functional assertions remain. No source/catalog contract is changed merely to silence the warnings.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 7a58890: 316 file(s) changed, 16809 line(s) added; 6 file(s) not content-scanned
- checks: errors=0 warnings=173 notes=22
- checklist: 5/6 done; open: close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
