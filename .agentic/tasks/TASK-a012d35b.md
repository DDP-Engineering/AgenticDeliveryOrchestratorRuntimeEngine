<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-a012d35b - [Direct] adore init probes AEGIS with the configured Python

stage: design
type: fix
path: full
interaction: autopilot
requirements: REQ-FUNC-f47c612e, REQ-FUNC-a1603c88, REQ-FUNC-7081a87e, REQ-FUNC-fe08018c, REQ-FUNC-d04bc2e0, REQ-FUNC-c9e616d4, REQ-FUNC-9b2bb293, REQ-FUNC-69bfe896
parent:
branch: adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-61
base: f651cd23e3a98a6ae0fd5c0145ec6dc1a5677874
opened: 2026-11-10

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [ ] design note written under the five headings, or its skip justified
- [ ] each decision cites a requirement ID or a named technical constraint
- [ ] every requirement maps to a decision and test seam, or no design impact
- [ ] risks and open decisions recorded
- [ ] `affected_paths` match the expected files
- [ ] knowledge pages unchanged

## Frame

Problem:
- STATED (ticket #61): init can report Python unavailable on a host configured to use python3 even though runs use that interpreter.
- OBSERVED (`04_Software/adore/doctor.py:509-570`): both AEGIS commands hard-code python, including the version-probe exit-127 diagnostic. `adore/orchestrator.py:1089` instead uses config.workflow.aegis_python.
Desired outcome:
- STATED (ticket Decisions): detect_aegis receives the interpreter; callers pass config.workflow.aegis_python (default python). Both probes use it, and exit-127 guidance names it. Readiness remains informational in init.
Actors:
- STATED (ticket Goal/Context): operator running adore init against a local target repository.
- OBSERVED (doctor/wizard source): wizard orchestrates setup, doctor probes through an injected CommandRunner, and the target's AEGIS returns version/status output.
Primary scenario:
- STATED (ticket Done when): for a target with AEGIS and configured python3, init probes --version and status --all --json using python3 as argv[0] and reports readiness without blocking setup.
Examples:
- STATED (ticket Happy test): fake runner observes [python3, .agentic/aegis.py, --version] and [python3, .agentic/aegis.py, status, --all, --json].
- STATED (ticket Decisions): the default interpreter remains python.
Counterexamples:
- STATED (ticket Negative tests): exit 127 names the configured interpreter; unsupported version and malformed status JSON remain not-ready as before.
- OBSERVED (`tests/test_wizard.py::test_wizard_reports_a_missing_aegis_payload`): missing payload prints CHECK/guidance but still saves the profile; do not turn this fix into a readiness gate.
In scope:
- STATED (ticket Scope): doctor interpreter parameter and both probe argv lists/exit-127 message; wizard caller plumbing; offline doctor/wizard tests; Component_Doctor.md and relevant Component_Wizard.md text; CHANGELOG Fixed entry and four-locale fixed release note.
- STATED (repository AGENTS.md and AEGIS workflow): task-scoped governed requirements/knowledge updates alongside implementation as needed; preserve installed payload.
Out of scope:
- STATED (ticket Scope and plan sections 1/4): repositories without AEGIS/direct-workflow behavior (DW-02), workflow selection, runtime execution changes, AEGIS installation/upgrades.
- STATED (user Working rules): commits, pushes, PR/MR creation/merges, forge credentials, child tasks, AEGIS payload edits and administrative package installation.
Constraints:
- STATED (user session instruction): autopilot; exactly frame this session and stop immediately after advance. One pinned task; no child tasks.
- OBSERVED (git branch --show-current): current branch matches the journal, adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-61. Initial git status --short is clean.
- STATED (repository rules and ticket): portable Python, LF, legal headers/style, offline injected-runner tests, no migrations or compatibility paths; no changes outside doctor/wizard interpreter handling without a blocking question.
- STATED (ticket): targeted doctor/wizard tests and Ruff during build; release-note checker against journal base before validate; full test/lint/frontend proof once at validate through AEGIS strict check.
- INFERRED (small scoped fix and repository bounded-run rule): bound this frame to one journal edit, no product changes or test execution, and one stage transition; later stages retain conductor limits.
Success signals:
- STATED (ticket Done when): python3 is argv[0] for both fake-runner probes; default python preserved; exit-127 detail names configured interpreter; unsupported-version and malformed-JSON behavior unchanged; wizard probe remains informational.
- STATED (ticket Done when): component docs, CHANGELOG Fixed and four-locale fixed note updated; build Log records release-notes: added and help: none (no interface change).
- STATED (ticket Validation): targeted pytest, Ruff, release-note checker and final strict test/lint/frontend pass with actual results recorded at their stages.
Evidence:
- OBSERVED: `.agentic/knowledge/doctor.md` routes to doctor.py/test_doctor.py and REQ-FUNC-69bfe896; wizard.md routes to wizard.py/test_wizard.py.
- OBSERVED: REQ-FUNC-69bfe896 governs supported version/schema readiness, but does not establish interpreter selection; REQ-FUNC-15adfbb0 makes workflow.aegis_python informational in web settings, not an init interpreter contract.
- OBSERVED: `adore/config.py:486` defines aegis_python = python; `doctor.py:529,544` hard-code it; `wizard.py:481,790` calls the report helper then detect_aegis without configuration.
- OBSERVED: doctor tests cover successful schema-1 status, missing payload, blocked/non-JSON status, unsupported version and wrong schema; wizard missing-payload test proves no-block reporting. Source/test inspection only, no tests run in frame.
- OBSERVED: `05_SoftwareDocu/Component_Doctor.md` describes both probes and missing-Python diagnostics; Component_Wizard.md describes informational detection and configuration validation.
- OBSERVED: plan sections 1 and 4 reserve direct workflow for separate tickets and leave AEGIS workflow unchanged; no conflict with this scoped fix identified.
Assumptions:
- INFERRED (ticket Decisions and existing config validation): reuse the validated single executable token without shell parsing or new interpreter discovery.
Unknowns:
- UNKNOWN: concrete wizard plumbing to obtain effective workflow configuration before its current early probe. OBSERVED (`wizard.py:481,944-954`): probe currently precedes assembled-profile loading. Specify/design must resolve this within doctor/wizard, without adding a new setting or changing unrelated interfaces; ask if broader changes prove necessary.
- UNKNOWN: actual availability of validation dependencies/browser in this fresh container; inspect at build/validate, no provisioning needed for frame.
Decision-blocking questions:
- INFERRED (ticket decisions, inspected source and plan): none established at frame. Existing wizard ordering is an implementation-design concern, not grounds to invent new behavior.
Proposed behaviors:
- STATED (accepted ticket Decisions, not new proposals): configured interpreter controls both probe commands and missing-executable diagnostic; informational readiness and existing version/status acceptance rules remain unchanged. These directly serve the success signals above.
- INFERRED (scope audit): no additional behavior is proposed; future unresolved behavior must not be implemented by convention.
Path and reason:
- INFERRED: choose full. Although small, the existing inspected readiness requirement does not cover interpreter selection and detect_aegis gains an interpreter input, so not every quick-path criterion holds. Specify should establish atomic coverage; design can judge whether a substantive note is necessary. No independently scoped child work is needed or authorized.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | STATED: configured interpreter affects successful probing and exit-127 message (ticket Decisions). |
| no new interface or data format | no | STATED: detect_aegis receives an interpreter; no stored format change requested. |
| no new dependency | yes | INFERRED: existing config value and injected runner suffice. |
| an existing requirement already covers the behavior | unknown | OBSERVED: REQ-FUNC-69bfe896 covers version/schema, not interpreter selection; no matching interpreter-selection requirement established. |
| no security or data-handling change | yes | INFERRED: only executable selection from existing validated config; no new storage, credentials or authority. |

- STATED (conductor instruction): scope recorded in autopilot; no human checkpoint requested. Next session performs specify, not this session.

## Requirement coverage

Evidence labels: STATED refers to ticket #61 Decisions/Done when and the accepted Frame; OBSERVED refers to the source/tests named below. Requirements describe the accepted contract, not a claim that new behavior is implemented.

| Frame outcome | Atomic behavior | Requirement | Verification | Design decision or no impact |
|---|---|---|---|---|
| STATED: configured Python controls version probing | Invoke the version probe with the supplied interpreter | REQ-FUNC-f47c612e | Fake wrapper/runner; python3 version argv and cwd; repeat with python | Pending design |
| STATED: configured Python controls status probing | After a supported version, invoke status with the same interpreter | REQ-FUNC-a1603c88 | Fake supported version/schema-1 status; python3 status argv/cwd and ready; python boundary and no status after version rejection | Pending design |
| STATED: exit 127 names configured interpreter | Return not-ready with the supplied executable in the unavailable diagnostic | REQ-FUNC-7081a87e | Fake version exit 127; python3/python diagnostics; no status command | Pending design |
| STATED: unsupported version still reported as before | Return not-ready with the existing bounded version diagnostic | REQ-FUNC-fe08018c | Fake older/wrong-major versions under python3; preserved detail/no status; stderr/empty boundaries | Pending design |
| STATED: malformed status JSON still reported as before | Return not-ready with the existing bounded status diagnostic | REQ-FUNC-d04bc2e0 | Fake supported version then malformed JSON at exit zero; stderr/stdout/empty diagnostic boundaries and existing nonzero regression | Pending design |
| STATED: caller uses effective workflow configuration, default python | Pass workflow.aegis_python into detect_aegis from init | REQ-FUNC-c9e616d4 | Offline run_wizard with scripted answers/fake runner; effective python3 propagation and omitted-value python default | Pending design |
| STATED: readiness remains informational | Report CHECK/detail/guidance and still create an otherwise valid confirmed profile | REQ-FUNC-9b2bb293 | Offline wizard missing payload and version exit 127; inspect output and validate saved profile | Pending design |
| STATED: existing readiness rules unchanged | Accept only a supported AEGIS version with schema-1 status | REQ-FUNC-69bfe896 (reuse unchanged) | Existing doctor happy schema-1, missing payload, blocked/unreadable status, wrong-schema/version and shared-client-gate regressions | No new version/schema policy |

Specify analysis and challenge:
- OBSERVED (`doctor.py::detect_aegis`, `tests/test_doctor.py:345-456`): version/status use hard-coded python today; exit 127 has a dedicated version-probe diagnostic. Unsupported-version and JSON decoding failures already return typed AegisStatus evidence, not exceptions. New error requirements preserve those responses; no new status-exit-127 special case is introduced.
- OBSERVED (`.agentic/requirements/functional/REQ-FUNC-69bfe896.toml`): the existing requirement governs the overall supported-version/schema acceptance gate. Reuse it unchanged for that acceptance behavior; the narrower diagnostic-response rows above do not change its policy. Other doctor/wizard governing requirements listed by explain concern independent tooling, configuration validation or enrollment and do not match interpreter selection.
- OBSERVED (`wizard.py:481,712-727,944-954`): the current early report has no effective loaded configuration, while candidate validation later loads the assembled document. INFERRED: interpreter provenance/plumbing belongs to design within doctor/wizard; no new prompt, answer key or configuration setting is authorized by this specification. The test seam for effective python3 must follow that design, not manufacture a new public interface.
- STATED (ticket Decisions and Scope): default remains python; missing payload, supported version range, schema acceptance, nonzero/blocked/unreadable status handling and prepare-only no-probe behavior are unchanged. OBSERVED: existing doctor/wizard tests establish these regressions. No new input validation, shell parsing, interpreter discovery, direct workflow or stored-format behavior is specified.
- INFERRED (the self-contained requirement sentences and existing status contract): no separate spec is needed; there is no new protocol, format, state machine or detailed error policy to define.
- INFERRED (table audit against Frame): every accepted product behavior maps to one row; independently observable requested error responses each have their own requirement. Command-specific rows deliberately separate version and status, and wizard propagation is a distinct caller contract. There are seven new draft requirements and one unchanged active acceptance requirement; new linked_tests remain empty until build.
- STATED (ticket and repository process): build must also update Component_Doctor.md and relevant Component_Wizard.md, component knowledge as needed, CHANGELOG Fixed, and a four-locale fixed release note; record `release-notes: added` and `help: none (no interface change)`. These are delivery obligations, not additional runtime behaviors requiring product requirements.
- UNKNOWN: exact wizard configuration/test seam awaits design; validation dependency availability awaits build/validate. Neither changes the specified observable contract. No decision-blocking conflict with plan sections 1/4 or ticket scope was found.
- INFERRED (bounded specify session): edits are limited to this journal and seven requirement files; no product code, tests, planning documents or installed AEGIS payload are changed; no product tests run in specify.


## Design


## Log

- 2026-11-10 frame: journal opened
- 2026-11-10 frame: completed; next specify - Frame scope recorded in autopilot; full path because interpreter input/diagnostic contract lacks established requirement coverage
- 2026-11-10 specify: Specify audit: seven draft atomic requirements plus unchanged REQ-FUNC-69bfe896 cover configured version/status argv, exit-127 interpreter diagnostic, preserved unsupported-version/malformed-JSON responses, wizard propagation/default and informational reporting. No separate spec needed. check and check --full exited 0 with errors=0, warnings=83, notes=24; no findings name this task or its new requirements. Existing unrelated warnings remain outside scope. Wizard configuration provenance/test seam remains a design concern within doctor/wizard; no product tests run.
- 2026-11-10 specify: completed; next design

## Rulings


## State

status: ready
reported: specify - completed
next: start design: read .agentic/steps/3_design.md
must_read: .agentic/tasks/TASK-a012d35b.md, .agentic/steps/3_design.md
changed: Created seven draft functional requirements and eight coverage rows; reused readiness requirement unchanged; completed specify checklist; no product changes
evidence: brief, explain for doctor/wizard, components, check and check --full exited 0; check reports errors=0 warnings=83 notes=24 with no task/new-requirement findings; branch matches; git status shows only journal and seven new requirement files; source/test inspection only, no product tests run
issues: Unrelated existing advisory warnings remain; design must resolve effective wizard configuration plumbing/test seam within doctor/wizard; dependency availability not yet verified
spec_compliance:
implementation_quality:
review_round:
