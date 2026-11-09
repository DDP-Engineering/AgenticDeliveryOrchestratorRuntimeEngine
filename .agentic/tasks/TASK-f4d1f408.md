<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-f4d1f408 - Enable progress commit publication by default in CLI and GUI

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-FUNC-64174b8b, REQ-REL-94e653aa
parent:
branch: task/adore-web-interface
base: 24ed432c3d45aba6f002ae934b98b6d05d0998fe
opened: 2026-10-08

## Done checklist (current stage)

- [x] Validated candidate unchanged
- [x] Evidence, diff and authorized outcome presented
- [x] Standing local commit and DCP test deployment authorization retained
- [x] Journal/report included in source commit
- [x] DCP replacement and live verification
- [x] Close-out

## Frame

Problem: STATED user wants progress publication enabled by default in ADORE and GUI.
Desired outcome: Missing configuration resolves to true; GUI displays the same default.
Actors: CLI operators and web administrators.
Primary scenario: Omitted delivery.publish_checkpoints -> shared model true -> guarded progress publication and GUI default true.
Examples: New profile and partial TOML inherit true.
Counterexamples: Explicit false remains false; malformed values fail validation.
In scope: Shared default, example, config/API tests and directly affected documentation.
Out of scope: Existing explicit values, cadence, checkpoint transport, approval policy, state migrations, UI renaming.
Constraints: Offline verification; retain remote leases and fresh human approval; no merge.
Success signals: Config and authenticated GUI API agree on true; false and malformed boundaries proven.
Evidence: STATED user request; OBSERVED config.py DeliveryConfig and web/app.py settings metadata use shared default_config().
Assumptions: Standing autonomous workflow authority from preceding implementation persists.
Unknowns: None affecting implementation.
Decision-blocking questions: None.
Proposed behaviors: One shared enabled default with explicit overrides retained.
Path and reason: Full; changing automatic remote publication default is externally observable. Existing boolean interface/format/dependency unchanged; remote side-effect policy changes.
Bound: 60 minutes, at most 25 candidate files, one build increment and at most two review correction cycles.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary | Verification | Design |
| --- | --- | --- | --- | --- | --- | --- |
| Shared enabled default | Omitted key inherits true in CLI and GUI | REQ-FUNC-64174b8b | Minimal TOML and API metadata true | Explicit false retained; invalid scalar rejected | Config/default and API tests | Shared DeliveryConfig |
| Preserve checkpoint semantics | Guarded publication and approval boundary | REQ-REL-94e653aa | Existing checkpoint suite | Remote conflict, invalid bool, missing approval | Existing offline checkpoint suite | Transport unchanged |

## Design

REQ-FUNC-64174b8b: Change DeliveryConfig.publish_checkpoints to True and bundled example to true. Web metadata derives default and effective value from the shared model; no second GUI default is needed. Keep persisted explicit false unchanged. Test public TOML loading and authenticated API, including exact override/bad-input boundaries. Existing generic conductor fixtures can explicitly disable checkpoints to preserve the behavior each test selects; checkpoint-specific tests cover publication. REQ-REL-94e653aa: Revise default wording only, preserve lease/ownership/approval semantics; align the adjacent MR/PR wording with the already delivered draft/ready contract. No new interface, dependency, schema, or architecture. Risk: profiles omitting the field begin remote WIP publication; document this requested default. No open decisions.

## Log

- 2026-10-08 frame: Full path accepted from explicit user instruction; reuse existing branch and standing autonomous authority; no children.
- 2026-10-08 specify: One new shared-default contract and one revised checkpoint contract; direct tests cover omitted/explicit/invalid inputs.
- 2026-10-08 design: Shared model supplies CLI and GUI; boolean overrides, transport and approval preserved.

- 2026-10-08 build red: command=`.\04_Software\.venv\Scripts\python.exe -m pytest -q 04_Software/tests/test_checkpoint_handoff.py::test_checkpoint_handoff_configuration_default_on 04_Software/tests/test_web_config.py::test_config_view_reports_each_settings_source_and_editability`; exit=1; 2 failed because omitted key is false in CLI and authenticated API.

- 2026-10-08 build green: 203 focused Python tests passed (checkpoint/config/conductor/web config); added authenticated explicit-false preservation case for final proof. Generic conductor fixture explicitly selects checkpoint-disabled policy.

- 2026-10-08 validate review: Independently assessed specification compliance and implementation quality; both approved, round 1. Only shared default/example change at runtime; explicit false GUI read preserves bytes; original checkpoint conflict/approval tests retained. Current component/context docs reconciled. Ten accepted catalog warnings are nine historical findings plus existing config.example outside-layout classification. Bound extended to 60 minutes before final proof based on prior full-suite duration.

- 2026-10-08 validate correction: First full Python run found one missing remote-transport fake in the native retry scenario (1521 passed, 2 failed, 3 pre-existing Windows symlink skips). Explicitly select checkpoint-disabled policy for that existing local retry test; no runtime transport change. Release consistency failure came from the previous task's ignored mixed-encoding proof log; preserved exact original bytes as draft-full-verification.raw.bin and normalized its parsed JSON to UTF-8. Two focused regressions rerun. Both specification and quality reviews approved against corrected candidate, round 2; final fresh complete Python proof required. Existing frontend proof still running against unchanged runtime/frontend sources.

- 2026-10-08 validate partial proof: Initial configured full check exit=1: 1521 Python passed / 2 failed / 3 symlink skips, Ruff passed, frontend passed (618.9s). Both failures corrected and focused rerun 2 passed. DEVIATION validate: preserve complete successful frontend proof because no frontend/runtime source changed after its start; combine with fresh complete Python/Ruff and strict catalog rather than rerunning successful browser coverage. Scope/confidence preserved, avoiding duplicate complete frontend run within 60-minute bound.

- 2026-10-08 validate prose reconciliation: Replaced one stale opt-in test docstring with selected-policy wording. Test behavior and runtime are unchanged; validate step 8 permits semantic/traceability review without repeating proof for prose only. Both verdicts reaffirmed approved, round 3.

- 2026-10-08 authority: User explicitly requests targeted tests only and full suite at the final settings-review stage. Cancelled running complete Python rerun via Ctrl-C; verified its process tree exited; no successful result claimed. Standing verification policy for subsequent setting changes is targeted offline tests only until user requests final suite.
- 2026-10-08 DEVIATION validate: Full verification deferred by explicit user instruction; final evidence is focused config/checkpoint/web/local tests plus already completed browser proof. Initial full gate remains exit=1 and its corrected failures are covered by focused tests; cancelled Python rerun proves nothing. Fixed this task's Handoff status to ready; remaining ten catalog warnings are historical/layout findings.

- 2026-10-08 validate final: Focused command=`.\04_Software\.venv\Scripts\python.exe -m pytest -q 04_Software/tests/test_config.py 04_Software/tests/test_checkpoint_handoff.py 04_Software/tests/test_web_config.py 04_Software/tests/test_local_execution.py::test_local_conductor_pins_target_parks_retries_and_never_lists_containers 04_Software/tests/test_release_consistency.py::test_repository_release_identity_is_consistent`; exit=0; 101 passed. Ruff on changed Python files exit=0. Strict catalog exit=0, 0 errors / 10 historical-layout warnings / 25 unrelated manual notes. Previously completed frontend 151 Chromium tests passed. Frozen 19 candidate files plus journal; no source drift. Full Python suite deferred by user; initial full gate failed on two now-corrected cases, interrupted rerun proves nothing.
- 2026-10-08 deliver: Reuse explicit standing authorization for local commit and replacement of the DCP test installation. Preserve configuration/state/TLS; no push or PR. Candidate consists of shared enabled default/example, tests and directly affected documentation/requirements; no existing explicit boolean rewrite. Verification substitution and deferred full suite remain explicit.

- 2026-10-08 delivery outcome: Source commit f2bad6eddca66a2ef3fd6809e4ed70d95af81c21 installed at /home/dpasare/apps/adore/dcp-progress-f4d1f408/04_Software; rollback backup /home/dpasare/apps/adore/backups/dcp-progress-f4d1f408-20261008T175132Z. Package SHA256 b3a945203b8507a0e575773f7ce6642d9685503f7ffe4bd8b5015811c6377671; fresh validated asset index-CjVWR5Es.js retains hash b668f13b62da178c63c1f8b2056a0bcfdc66e7a4ce4ea2e08462dcad605c38f8. Services active, worker ready, LAN health/pages 200 and protected API 401; existing certificate pinned unchanged. Before/after inventories identical (schema 14, users 1, audit 105, 18 completed operations, six config/state hashes and pause flags retained). Remote shared default and all six effective profiles true. Reloaded authenticated live GUI confirms active/default true; no config writes; screenshot dcp-progress-view.png saved. SSH and both SCP sessions exited. No Git push or PR. Full suite remains deferred by explicit user instruction; subsequent settings changes use targeted verification until final review.

## Rulings


## Handoff

current: done
status: ready
next: Continue settings analysis; targeted tests only until user requests final full suite
must_read: .agentic/tasks/TASK-f4d1f408.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Enabled shared CLI/GUI progress publication default; committed and installed on DCP
evidence: 101 focused tests and changed-file Ruff passed; live GUI/default and six profiles true; services/worker ready; config/state preserved
issues: Full suite deferred at user request; cancelled rerun proves nothing; ten historical/layout catalog warnings
next: Continue settings analysis with targeted verification
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-10-08)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-64174b8b - Share enabled progress publication defaults across CLI and GUI
  - REQ-REL-94e653aa - Preserve DCP checkpoint, handoff, and subscription budget semantics
- deviations: 2 recorded
  - validate: preserve complete successful frontend proof because no frontend/runtime source changed after its start; combine with fresh complete Python/Ruff and strict catalog rather than rerunning successful browser coverage. Scope/confidence preserved, avoiding duplicate complete frontend run within 60-minute bound.
  - validate: Full verification deferred by explicit user instruction; final evidence is focused config/checkpoint/web/local tests plus already completed browser proof. Initial full gate remains exit=1 and its corrected failures are covered by focused tests; cancelled Python rerun proves nothing. Fixed this task's Handoff status to ready; remaining ten catalog warnings are historical/layout findings.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 24ed432: 20 file(s) changed, 213 line(s) added
- checks: errors=0 warnings=11 notes=25
- checklist: 3/6 done; open: Journal/report included in source commit; DCP replacement and live verification; Close-out
