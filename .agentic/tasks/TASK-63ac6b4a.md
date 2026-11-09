<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-63ac6b4a - Align ADORE with the rebuilt AEGIS companion workflow

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-FUNC-16237c6d, REQ-FUNC-8adb68f9
parent:
branch: task/adore-web-interface
base: 7a588905de14d68503d47a6321b0e9c3b1114d32
opened: 2026-10-22

## Done checklist (current stage)

- [x] Semantic and independent spec/quality reviews complete
- [x] Requirements, component docs/knowledge and context reconciled
- [x] Final targeted proof and advisory catalog recorded
- [x] Local source handoff without package or payload deployment

## Frame

Problem: STATED a rebuilt AEGIS delivery needs compatibility analysis and necessary ADORE updates. OBSERVED local AEGIS 0.14.0 rebuilt 2026-10-22; the installed payload also says 0.14.0 but differs in prompts and optional tools.
Desired outcome: Consume the new AEGIS companion contract and preserve its journal authoring semantics without broadening ADORE authority.
Actors: conductor, every supported executor, target repository's installed AEGIS.
Primary scenario: ADORE probes/creates/reads a new AEGIS journal, hands one stage to an executor with its installed authoring instructions, validates schema-1 evidence and reports under existing limits.
Examples: OBSERVED new templates retain a visible authoring-guide link and require preservation of original legal prologue, existing journal identity and append-only history. Optional design diagrams do not gate checks.
Counterexamples: unknown major/schema, corrupt or wrong task/check data remain refused; an AEGIS update never authorizes autonomous publication or child journals.
In scope: analyze immutable release/source hashes and used CLI surfaces; small generic prompt alignment; replay captured new-version CLI output with injected commands; compatibility/component docs and release notes.
Out of scope: copying/replacing managed payloads in projects, removing CodeGraph, changing target repositories/host installations, model requests, package rebuilding, Git publication, full suites.
Constraints: 45 minutes, 20 authored non-payload paths, five correction cycles; preserve dirty work; targeted offline tests only; standing autopilot to local source handoff.
Success signals: new release command/status/check/report/evolution output accepted through existing client; corrupt evidence rejected; every stage prompt names installed authoring guide and preserves journal identity/legal/history without weakening one-stage, no-push or approval boundaries.
Evidence: release-manifest/delivery-manifest under sibling AEGIS 07_Delivery; source commit 9e3d870cd1fe834a93e785008c69506bda954359; archive dist/aegis-0.14.0-windows.zip; cmd_task/cmd_status/cmd_check/cmd_evolution/cmd_report are unchanged between installed and new CLI. New config adds optional diagrams; removed optional CodeGraph commands are outside ADORE's called API. Source/archive hashes will bind recorded fixtures.
Assumptions: new local 0.14.0 delivery is the user's intended release; forge's published release still lists 0.13.0. No ADORE release version was requested.
Unknowns: live model/executor and package acceptance excluded; local instructions do not guarantee model compliance.
Decision-blocking questions: none.
Path and reason: full; introduce explicit executor authoring contract and capture compatibility evidence without a new CLI/state schema.

## Requirement coverage

| Outcome | Requirement | Positive case | Boundary | Decision |
|---|---|---|---|---|
| Read new companion output | REQ-FUNC-16237c6d | captured schema-1 new journal/check and all called commands | malformed/wrong identity/schema/contradiction | existing typed client unchanged unless proof exposes a gap |
| Preserve installed journal rules | REQ-FUNC-8adb68f9 | all stage prompts name installed authoring guide | existing no-push/no-child/one-stage limits retained | short shared prompt addition, no payload edits |

## Design

Use the existing AegisClient API and shared conductor prompt, without compatibility fallbacks or extra execution gates. Capture actual CLI output from a temporary isolated copy of the new official Windows archive with Git and verification boundaries injected. Store portable golden JSON evidence with source hashes; unit tests replay it through FakeExec, exercise native/file exchange where already supported, and mutate only trust-boundary fields for negative cases. No unit test depends on sibling checkout, network, real Git or containers.

Add a short unconditional journal-edit instruction referencing .agentic/templates/task.md (present throughout supported AEGIS releases): preserve legal prologue and existing guide link, append-only Log/Rulings and the same task ID during edit recovery. Existing installed step files continue to own review/proof ordering and optional diagrams; ADORE adds no diagram gate. Do not replace the repository's managed AEGIS payload: its enabled CodeGraph extension is independent and not used by the application. Report verified compatibility independently of ADORE's SemVer release identity.

## Log

- 2026-10-22 frame: user requests analysis and applicable compatibility implementation; standing local autopilot, targeted tests and no packages retained. Existing dirty files preserved.
- 2026-10-22 specify: reuse companion task/check requirement; add atomic executor journal-authoring guidance requirement. Full path chosen; no new schema, user setting or dependency.
- 2026-10-22 design: called CLI functions are identical; prompt/template changes require explicit authoring guidance and new-release fixtures. Keep optional CodeGraph installation intact and avoid unrelated tool migration.

- 2026-10-22 build red: REQ-FUNC-8adb68f9; command=python -m pytest -q 04_Software/tests/test_aegis_014_compatibility.py 04_Software/tests/test_orchestrator.py -k 'rebuilt_aegis_014 or journal_authoring_contract'; exit=1; six stage prompts omit the installed authoring guide. Six actual-release client/rejection cases already pass, proving no wire-contract change is needed.
- 2026-10-22 analysis: captured actual CLI output and generated journal from the official ZIP in automatically cleaned temporary storage. Git and configured verification are injected, so captured run evidence proves serialization, not a real product test execution. Source CLI SHA-256 87f87d0743555bdf49b2ac90a899e4c47f28383c34de411aa9ff25c126b777f6; capture metadata pins the archive hash and source commit.

- 2026-10-22 build green: python -m pytest -q 04_Software/tests/test_aegis_014_compatibility.py 04_Software/tests/test_orchestrator.py -k 'rebuilt_aegis_014 or journal_authoring_contract or executor_prompt'; exit=0, 16 passed. Extended focused companion/prompt/return regression selection: 85 passed, 117 deselected. Touched Python Ruff and release-notes checker pass.
- 2026-10-22 release-notes: updated (merged Jobs compatibility wording in all four locales).
- 2026-10-22 help: none (no interface names, steps, settings or user workflow changed; internal journal-authoring guidance is documented in the compatibility and component references).
- 2026-10-22 validate: source edit is a short shared prompt addition; client parser/version/schema policy remains unchanged. New fixture and red prompt tests were authored before the anchor; evolution therefore reports only later modified paths. Review includes those test artifacts explicitly. Context confirms independent ADORE release identity and unchanged environment setup; existing component diagrams remain accurate because component interfaces/dependencies are unchanged.

- 2026-10-22 review round 1 / specification compliance: approved. New-release source/archive analysis covers all called public commands; installed parser policy remains applicable. The shared prompt implements journal-authoring preservation on every stage, with no payload deployment, diagram gate, dependency, schema or publication-authority change. Requirements and documented exclusions match the candidate.
- 2026-10-22 review round 1 / implementation quality: approved. Separate source/test review confirms the prompt permits legitimate current-stage/header edits, protects append-only history and same-ID repair, and keeps existing one-stage/no-child/no-publication instructions. Golden fixture provenance pins the archive/CLI and declares injected Git/verification; corruption tests preserve typed refusal. Existing component diagrams and environment instructions remain accurate.
- 2026-10-22 DEVIATION validate: final verification uses targeted companion/prompt/return tests instead of check --strict --run/full suites, following the user's standing instruction. Live model/native OS and delivery acceptance remain unperformed; packages are not rebuilt.
- 2026-10-22 validate final: python -m pytest -q 04_Software/tests/test_aegis.py 04_Software/tests/test_aegis_014_compatibility.py 04_Software/tests/test_orchestrator.py -k 'not test_orchestrator or executor_prompt or journal_authoring_contract or retry_continues_design_return or retry_backward_routes' --tb=short --no-header: exit=0, 85 passed / 117 deselected in 1.61s. Ruff on touched source/tests, check_release_notes.py --since 7a588905de14d68503d47a6321b0e9c3b1114d32 and scoped git diff --check: exit=0. Final evolution lists nine post-anchor paths plus the pre-anchor fixture/prompt test additions explicitly reviewed. Advisory strict catalog: exit=0, zero errors; its accumulated dirty-baseline warnings are out of scope, with this task's review-state warning resolved by the recorded verdicts. No full suite was run.
- 2026-10-22 deliver: user-authorized local source handoff only; no commit, push, package build or installed target/project mutation. Both current verdicts apply to the proved candidate.

- 2026-10-22 close-out: local implementation, documented analysis and targeted compatibility proof completed. Source changes and golden fixture tests are handed off in the shared checkout; earlier dirty work and delivery archives remain intact. No Git or package publication.

## Rulings

- RULING-001 | date=2026-10-22 | decision=Local implementation and targeted proof only, no full suites or package rebuild | reason=direct and standing user scope | source=user | supersedes=none

## Handoff

current: done
status: completed
next: Package/live acceptance only if separately requested.
must_read: .agentic/tasks/TASK-63ac6b4a.md; .agentic/requirements/functional/REQ-FUNC-8adb68f9.toml
blockers:

## Stage report

stage: done
result: completed
current: done
changed: ADORE executor guidance aligned with rebuilt AEGIS 0.14.0; companion contract replay added.
evidence: 85 targeted tests, touched Ruff, release notes and diff checks passed.
issues: Full suite, models and package acceptance not run; target payload/CodeGraph retained.
next: Package/live acceptance only if separately requested.
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-22)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-16237c6d - Validate AEGIS tasks and strict check evidence
  - REQ-FUNC-8adb68f9 - Guide executor journal edits with the installed AEGIS authoring contract
- deviations: 1 recorded
  - validate: final verification uses targeted companion/prompt/return tests instead of check --strict --run/full suites, following the user's standing instruction. Live model/native OS and delivery acceptance remain unperformed; packages are not rebuilt.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 7a58890: 262 file(s) changed, 13942 line(s) added; 6 file(s) not content-scanned
- checks: errors=0 warnings=168 notes=22
- checklist: 4/4 done
