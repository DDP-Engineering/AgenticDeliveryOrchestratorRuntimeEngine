<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-7ce1d8ce - Explain local readiness failures and repair OpenCode connection checks

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-FUNC-ab8c90b6, REQ-FUNC-a8865e64, REQ-UX-4d08dee5
parent:
branch: task/adore-web-interface
base: 7a588905de14d68503d47a6321b0e9c3b1114d32
opened: 2026-10-22

## Done checklist (current stage)

- [x] Diff, scope, requirements and trust boundaries reviewed
- [x] Component knowledge, context and architecture current
- [x] Final focused proof and full-suite substitution recorded
- [x] Evolution and advisory findings reconciled
- [x] Independent specification/quality verdicts recorded
- [x] Local source outcome delivered without packaging or process control

## Frame

Problem: Native readiness swallows its failure cause; the UI repeats one notice three times and shows container advice for local model errors.
Desired outcome: Accurate bounded local/executor/model verification and useful single explanations.
Actors: Administrator, selected installed executor, current Windows/Linux account, model provider.
Primary scenario: Host version/auth check or model challenge -> retain measured cause -> show localized remediation in Summary/Settings.
Examples: Version on stderr; missing executable; OpenCode zero-exit JSON error; completed nonce text with timestamp but no step_finish.
Counterexamples: Unknown/malformed/tool-bearing output never becomes success; failed cleanup overrides success; no raw provider diagnostics/tokens released.
In scope: local_execution, web model/probe/persistence and frontend readiness/model presentation, targeted offline tests, component/operator/help/notes.
Out of scope: Packages, restarts, active ticket control, paid/live model calls, global credentials/tool upgrades and other workflows.
Constraints: User targeted tests only, no rebuild; preserve existing dirty files; 45s model inference and existing native ownership/cleanup; at most five review correction cycles.
Success signals: Offline Windows/Linux native behavior, closed causes survive reload, correct four-locale no-container guidance, complete nonce acceptance and malformed fail-closed.
Evidence: STATED request. OBSERVED ReadinessEvidence duplicates localCopy.notice, _probe_setup swallows errors, _native_response collapses provider error to invalid-response, real saved model reason invalid-response. OBSERVED installed executable/auth file exist; no actual failing command output retained. INFERRED missing stream finish can explain false failures; upstream issue documents completed-text truncation. UNKNOWN actual earlier provider cause; no live model request will be inferred or made.
Assumptions: Configured native command remains authoritative; completion timestamps plus clean exit and exact nonce prove this short connectivity challenge, not job/tool acceptance.
Decision-blocking questions: none.
Proposed behaviors: Add optional executor_probe ready/reason/exit_code to schema-1 readiness; retain legacy evidence. Distinguish subprocess/auth/provision/cleanup failures. Preserve strict provider/nonce boundaries and make local advice explicit.
Path and reason: full; new optional evidence contract and failure presentation. Quick criteria: unchanged observable behavior=no; unchanged data/interface=no; dependency=yes; exact existing requirement=no; security boundaries retained=yes.

## Requirement coverage

| Outcome | Requirement | Positive | Boundary | Design |
| --- | --- | --- | --- | --- |
| Local cause | REQ-FUNC-ab8c90b6 | version on either stream, saved result roundtrip | corrupt/contradictory/unknown cause, auth/cleanup | Closed optional executor_probe |
| Native model | REQ-FUNC-a8865e64 | exact completed nonce | missing completion/tool/wrong nonce/error JSON | Strict event parser and safe reason classifier |
| Clear copy | REQ-UX-4d08dee5 | single local description and actual remedy | legacy unknown cause, provider output never echoed | Pure four-locale diagnostic copy reused by views |

## Design

REQ-FUNC-ab8c90b6: Local execution owns probe_local_executor and a small closed result {ready, reason, exit_code}. A typed prerequisite exception retains version command status; other known native errors map to closed account/executable/auth/permission/scope/cleanup causes. Check a clean version on stdout or stderr; auth remains presence/strict-safe file check. Web stores optional executor_probe, validates exact keys/types/reason/status consistency on load, and accepts legacy absence. Frontend mirrors strict validation. Ownership/scope cleanup stays authoritative.
REQ-FUNC-a8865e64: Native configured argv/account/environment remain unchanged. Classify bounded strict OpenCode error events by typed name/status before collapsing to generic failure; no raw message persistence. Completed exact text with a finite valid end timestamp and clean exit may prove the short challenge when no finish event was emitted. Incomplete/textless/tool/error/duplicate malformed streams remain failures; no second paid request or session continuation. All four native parsers keep their contracts.
REQ-UX-4d08dee5: localDiagnostics.ts contains pure localized prerequisite/model explanations. Readiness displays concise local purpose once, one cause/remedy, numeric exit where known; missing legacy cause is explicit. ModelConnection help switches between local and container; Summary uses the explicit model reason instead of generic container text. Update all four help locales, notes and component docs. No architecture split beyond shared diagnostic copy/helper.
Expected files: local_execution.py, web/app.py, web/model_connection.py; readiness.ts, localDiagnostics.ts, ReadinessEvidence.tsx, ModelConnection.tsx, App.tsx; related Python/Node tests, docs/help/notes/context.
Risks: The older live failure cannot be reconstructed from its boolean record; new checks will provide cause. No live provider acceptance claimed. Optional additive diagnostic field needs rejection tests and legacy compatibility.

## Log

- 2026-10-22 frame/specify/design: full path accepted from explicit request and standing local autopilot authorization. Three atomic requirements created; no package, service or live model work. Existing component contracts reviewed; optional evidence and completed short-challenge policy specified above.

- 2026-10-22 build red REQ-FUNC-ab8c90b6 / REQ-FUNC-a8865e64: `pytest -q 04_Software/tests/test_local_execution.py -k "local_prerequisite_retains or native_opencode_completion" --tb=line --no-header --basetemp 04_Software/.pytest_cache/local-diagnostics-red`; exit=1, 13 expected failures/1 pass: missing executor_probe, stderr version rejection, completed-text rejection and provider error causes collapsed. External CLI/processes are injected.

- 2026-10-22 build UX red: `node --test tests/localDiagnostics.test.mjs` exit=1 before the new localized diagnostic surface existed. Build green increment: 33 targeted native tests passed (47 deselected), covering all executors plus completed OpenCode text, safe provider causes and native prerequisite errors.

- 2026-10-22 build: closed optional native diagnostics, strict persisted roundtrip, version stdout/stderr handling, OpenCode completed-text/provider classification and four-locale Summary/model presentation implemented. Native regression increment passed 42 cases (47 deselected); API/model modules passed 52; Node readiness/source-render/help passed 16; TypeScript, touched Python Ruff and release-note checks passed before final review refinements.
- 2026-10-22 build documentation: release-notes: added (Executor local diagnostic/model fix); related older Delivery fixes merged into one entry to stay within the category limit. help: updated (Executors topic in all four locales). Component docs/knowledge and local setup guide updated with the optional wire contract and legacy behavior. No installation/service/package scripts changed.
- 2026-10-22 build -> validate: requirements active with native/API/Node links and optional-evidence spec. OpenCode completed-text compatibility supported by upstream issue https://github.com/anomalyco/opencode/issues/26855; this is not claimed as the proven cause of the older live failure.

- 2026-10-22 validation review: reconciled the 23 evolution paths and three requirement contracts; no package/tool/service/job-control changes. Reviewed strict optional evidence, legacy compatibility, raw-secret exclusion, actual cause precedence, timestamp/duplicate/tool boundaries and configured native argv authority. Added a bounded overflow rejection for hostile completion timestamps during review, with a focused negative case.
- 2026-10-22 independent specification verdict round 1: approved. The three requirements and optional-evidence spec match native diagnostics, completed short challenge/provider causes and four-locale Summary/Settings copy; no full-job/real-provider proof is claimed.
- 2026-10-22 independent implementation-quality verdict round 1: approved. Typed command status, safe known failure classification, strict persisted frontend/backend boundary, cleanup failure and old-record behavior are covered. Version stderr/prefix/style and timestamps have closed negative boundaries; no raw provider diagnostic is returned. Architecture/context/documentation agree with the reviewed candidate.
- 2026-10-22 DEVIATION validate: required full check --strict --run replaced with narrowly selected native tests, the API/model modules, Node diagnostic/readiness/help source-render tests, TypeScript noEmit and touched-file Ruff under the user's explicit targeted-only instruction. Other components, real host/provider acceptance and packaged-app behavior are outside this proof. No package rebuild or running-instance mutation.

- 2026-10-22 final proof: exact six native test nodes plus test_web_readiness.py and test_model_connection.py via pytest exit=0, 98 passed in 19.16s; native/model/process boundaries injected, no live requests. `node --test tests/localDiagnostics.test.mjs tests/readiness.test.mjs tests/help.test.mjs` exit=0, 16 passed, including actual source-rendered Summary and ModelConnection in four locales. `tsc -p tsconfig.json --noEmit`, touched Python Ruff, release notes --since task base and diff --check all exit=0. Existing Starlette/httpx deprecation remains dependency maintenance outside this scope.
- 2026-10-22 final advisory: exit=0, errors=0/warnings=139/notes=22 before final traceability reconciliation. The new localized test path was added to its requirement affected_paths to resolve its uncovered-source warning. Other baseline warnings concern old moved-tool/generated paths, legacy journals/tracked fingerprints, branch-wide uncovered files and existing delivery/binary material. No strict/full-suite pass is claimed.
- 2026-10-22 independent final round 2 review after traceability reconciliation: spec_compliance=approved and implementation_quality=approved. Requirements/test links, optional strict evidence and legacy behavior still match the unchanged executable candidate; final test scope covers the candidate and the known full-suite/live-provider exclusion remains explicit. No unresolved in-scope defect found.

- 2026-10-22 local delivery completed: authorized source changes and targeted proof are present in the working tree. No commit/push/PR or package rebuild; the Windows archive retains its 11:41 timestamp. No ADORE service, job, global configuration or credential store was changed. The executable candidate remains unchanged since final proof. The delivery report includes prior branch work; task evolution isolates one added source module and 22 modified non-AEGIS paths. Earlier diagnostics remain readable but require a fresh host check to obtain causes.

## Rulings

- RULING-001 | date=2026-10-22 | decision=Local source implementation and targeted offline tests only; no packages/restart/job control/publication | reason=explicit user constraints | source=user | supersedes=none
- RULING-002 | date=2026-10-22 | decision=Autopilot through local source handoff | reason=standing user authorization | source=user | supersedes=none

## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-7ce1d8ce.md
blockers:

## Stage report

stage: deliver
result: completed
current: done
changed: Cauze locale pastrate, mesaje concise si verificare OpenCode corectata.
evidence: 98 teste Python + 16 Node; TypeScript, lint, note si diff OK.
issues: Suita completa si modelul real neapelate; avertismente anterioare pastrate.
next: Implementarea este in surse; arhivele raman neschimbate.
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-22)

- stage: deliver; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-ab8c90b6 - Report local executor prerequisite failure causes
  - REQ-FUNC-a8865e64 - Classify native OpenCode model responses accurately
  - REQ-UX-4d08dee5 - Present concise native readiness and model guidance
- deviations: 1 recorded
  - validate: required full check --strict --run replaced with narrowly selected native tests, the API/model modules, Node diagnostic/readiness/help source-render tests, TypeScript noEmit and touched-file Ruff under the user's explicit targeted-only instruction. Other components, real host/provider acceptance and packaged-app behavior are outside this proof. No package rebuild or running-instance mutation.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 7a58890: 238 file(s) changed, 11969 line(s) added; 6 file(s) not content-scanned
- checks: errors=0 warnings=139 notes=22
- checklist: 5/6 done; open: Local source outcome delivered without packaging or process control
