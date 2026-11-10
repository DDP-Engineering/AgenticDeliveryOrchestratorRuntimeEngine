<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-a012d35b - [Direct] adore init probes AEGIS with the configured Python

stage: specify
type: fix
path: full
interaction: autopilot
requirements:
parent:
branch: adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-61
base: f651cd23e3a98a6ae0fd5c0145ec6dc1a5677874
opened: 2026-11-10

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [ ] every accepted behavior is one coverage row with exactly one requirement
- [ ] each error or failure response has its own requirement
- [ ] each requirement is one self-contained "shall" sentence
- [ ] verification names setup, trigger, oracle and a boundary or failure
- [ ] specs written only where the requirement cannot carry the detail
- [ ] conflicts, assumptions and unknowns resolved or recorded
- [ ] every ID on the journal's `requirements:` line; `check` shows no
      format errors

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


## Design


## Log

- 2026-11-10 frame: journal opened
- 2026-11-10 frame: completed; next specify - Frame scope recorded in autopilot; full path because interpreter input/diagnostic contract lacks established requirement coverage

## Rulings


## State

status: ready
reported: frame - completed
next: start specify: read .agentic/steps/2_specify.md
must_read: .agentic/tasks/TASK-a012d35b.md, .agentic/steps/2_specify.md
changed: Completed Frame and criteria table; preserved autopilot/full; no product changes
evidence: brief and components exited 0; git branch --show-current and git status --short exited 0 with matching branch and initially clean checkout; inspected doctor/wizard source, tests, requirements and plan sections 1/4; no tests run (frame only)
issues: No blocking questions; wizard probes before assembled config loading, so specify/design must resolve effective interpreter plumbing within ticket scope
spec_compliance:
implementation_quality:
review_round:
