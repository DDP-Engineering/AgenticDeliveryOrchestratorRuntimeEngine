<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-cadbef92 - WK-03 isolate concurrent run resources and shared effects

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-REL-284af472, REQ-SEC-fc949861, REQ-DATA-54868516, REQ-REL-2e8dc2a1, REQ-REL-23c94e15, REQ-FUNC-aae1904f, REQ-FUNC-bcaf01be
parent:
branch: master
base: bf58e2fc9d1ac23df9606e3d37415e7e6d4ab67f
opened: 2026-11-14

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

Problem: STATED (#86/WK-03): concurrent jobs must not mix resources or shared effects.
Desired outcome: STATED: two same-repository runs provision, checkpoint and finish concurrently with retained metrics; stopping one preserves the other.
Actors: STATED: independent per-run conductors, operators, project workers.
Primary scenario: STATED: two admitted runs progress with separate backend/runtime/model environments while brief shared mutations serialize.
Examples: STATED: concurrent Git contention, invalid ownership, report updates and auth refresh require deterministic negative coverage.
Counterexamples: STATED: stopping monitoring does not cancel an already running job; project deletion cannot release another project's resources.
In scope: STATED: inventory isolation/execution/local_execution, executor, preparation, chatgpt, metrics and StateStore; dedicated common-resource locks, atomic writes, ownership guards and project barriers.
Out of scope: STATED: commits/push/merge, Gitea/DCP changes, new sessions/branches/worktrees, migrations, target-repository retesting, setup/deployment tests.
Constraints: STATED: master shared checkout exclusively assigned; version 0.15.0; autopilot; only targeted validation (one global validation after umbrella). Bounded batch: 12 edit/check cycles, 120 minutes, 120 files.
Success signals: STATED: all four ticket acceptance cases covered offline through injected boundaries and deterministic concurrency.
Evidence: OBSERVED: #85 commit bf58e2f supplies admission/run/execution locks and independent conductor processes; metrics.record_summary currently rewrites JSONL after an unlocked reread; WorktreeManager mutates shared Git/config without a common lock.
Assumptions: INFERRED: existing per-run process architecture is retained, based on #85 and user constraints.
Unknowns: UNKNOWN: live host/runtime acceptance; no live operations authorized or required for this batch.
Decision-blocking questions: None; implementation choices follow established typed refusal and bounded retry contracts.
Proposed behaviors: None outside the accepted ticket.
Path and reason:
| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | concurrency guarantees |
| no new interface/data format | unknown | ownership seams require inspection |
| no new dependency | yes | stdlib kernel locks |
| existing requirement covers behavior | no | new shared-resource contracts |
| no security/data handling change | no | ownership and auth serialization |
Full path; no child tasks; no delegation authorized.

## Requirement coverage

| Requirement | Behavior | Design | Proof |
|---|---|---|---|
| REQ-REL-284af472 | When independent runs modify one shared repository, ADORE shall serialize bounded Git mutation sequences outside agent execution. | scoped locks and ownership | deterministic tests |
| REQ-SEC-fc949861 | If run resource paths or branch ownership are unproven, ADORE shall refuse cleanup, checkpoint and publication with a typed error before destructive effects. | scoped locks and ownership | deterministic tests |
| REQ-DATA-54868516 | When terminal summaries change concurrently, ADORE shall preserve committed rows in an atomically replaced JSONL mirror under a bounded store lock. | scoped locks and ownership | deterministic tests |
| REQ-REL-2e8dc2a1 | When common Pi installation or ChatGPT refresh is requested concurrently, ADORE shall serialize each mutation under an independent bounded resource lock. | scoped locks and ownership | deterministic tests |
| REQ-REL-23c94e15 | When a project is archived or deleted, ADORE shall require a project-scoped barrier excluding admission and all run execution or cleanup. | scoped locks and ownership | deterministic tests |


| REQ-FUNC-aae1904f | User #86 narrows cleanup to proven saved resources | exact release | cleanup contracts |
| REQ-FUNC-bcaf01be | User #86 requires a project barrier for both delete modes | lifecycle/execution barrier | CLI/HTTP contracts |

## Design

### Approach
OBSERVED: #85 already constructs per-run backend/executor/configuration; preserve it.
REQ-REL-284af472: portable stable-inode kernel locks serialize host Git mutations
by resolved common repository identity. Locks end before executor work.
REQ-DATA-54868516: serialize database update and atomic mirror publication together;
close SQLite connections and bound contention. Atomic unique temporary files prevent
writers sharing a staging name.
REQ-REL-2e8dc2a1: dedicated Pi-install and ChatGPT-refresh locks, independent of Git,
metrics and execution. Existing Pi packages are immutable after atomic publication.
OBSERVED: preparation installs into a per-run container, never builds/mutates shared
images; retained recipe sources already use a dedicated catalog lock and atomic writes.

### Interfaces and data
Production branch/worktree/container names carry a stable twelve-hex project
suffix derived from canonical state-root identity, including ticket-only branch templates.
Warm container reuse proves all dedicated mounts before starting immutable IDs.
Add resource_lock(path, timeout) with typed busy/storage failures, crash release,
thread reentrancy and refusal of symlink/reparse lock storage. No stored schema change.
State lock placement derives from canonical state-root paths alone. Profile-contained
state uses the server home from the outermost profiles/<profile> path segment;
external state keeps root/locks. Optional clone deletion retains both state and locks.
Admission rechecks bound profile identity/archive state under its short reservation.
REQ-SEC-fc949861: conductor verifies derived branch, container, worktree and IO before
checkpoint, publication and teardown. Container controls address verified immutable IDs.
REQ-REL-23c94e15: project barrier holds admission and all run lifecycle locks, checks
execution reservations including removed state; archive/delete refuse active ownership.
State writes use unique temp files; journals append one serialized run-owned event.

### Files and test seams
isolation.py, execution.py, orchestrator.py, state.py, metrics.py, chatgpt.py,
pi_installation.py, cli.py, web/app.py, clone_cleanup.py, process_log.py and
resource_lock.py; injected Git/runtime/auth
runners and thread Events/Barriers in test_shared_resources.py. No live tools/models.
Existing native/process and executor tests prove their unchanged per-run seams.

### Risks and open decisions
Bound lock waits and short SQLite transactions; no lock spans agent work. Refuse
unknown ownership rather than guessing. Native execution remains account-level access.
No new lifecycle/schema or public setting. No unresolved product decisions.

### Requirement map
All five requirement rows map to the decisions above and targeted public tests.
Diagrams: [diagram_TASK-cadbef92.md](diagram_TASK-cadbef92.md)


## Log

- 2026-11-14 frame: journal opened
- 2026-11-14 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-14 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-14 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-14 build: red: targeted test_shared_resources.py exit 1; concurrent Git/auth overlap, stale metrics mirror, invalid paths accepted, project barrier absent and foreign cancellation/handoff accepted (all task requirements)
- 2026-11-14 build: batch 1 bounded review: resource inventory and isolation implemented; 274 isolation/runtime/shared-resource contracts passed, 6 platform symlink skips. Starting batch 2 for documentation, remaining targeted regressions and review (same bounds: 12 cycles/120 minutes/120 files).
- 2026-11-14 build: release-notes: added (concurrent job isolation and preservation of peer statistics are user-visible)
- 2026-11-14 build: help: updated (Jobs and Projects concurrency, cancellation and lifecycle ownership in en/fr/de/ro)
- 2026-11-14 build: scope: #86 explicitly supersedes name-only/stateless cleanup in REQ-FUNC-aae1904f and requires both profile-delete modes to exclude all run execution/cleanup. Revised existing cleanup/deletion specs; preserved older task journals.
- 2026-11-14 build: scope: inventory also found shared process-log rotation and clone preview path derivation. Read process-log/profiles knowledge; serialize admission log rotation, give conduct-run its own log and use saved namespaced worktree paths in clone preview; targeted contracts added.
- 2026-11-14 build: review finding: repository lock metadata under the clone working root dirtied owned clones and blocked clone deletion; moved it into the canonical common Git metadata directory with an injected clean-working-tree regression contract.
- 2026-11-14 build: review finding: ambient ADORE_HOME could split explicit --home API and CLI kernel ownership; lock location now derives only from canonical state-root layout, remains stable after profile removal and keeps retained state/lock storage outside optional clone deletion. Added differing-home and nested-profile deletion contracts plus concurrent metrics delete/upsert proof.
- 2026-11-14 build: DEVIATION build: late inventory log/clone/admission follow-ups preceded their new tests - accepted as bounded integration corrections; dedicated negative contracts now pass.
- 2026-11-14 build: green: targeted shared-resource proof 47 passed; corrected recipe/native/cleanup integration selection 20 passed; final clone/nested-barrier additions 3 passed; targeted Ruff exit 0; release-notes check exit 0; help tests 13 passed; Vite static help bundle rebuilt and stamped without frontend/Chromium suites.
- 2026-11-14 build: baseline limitation: test_pi_installation::test_managed_pi_ships_the_reviewed_guard fails because native/container guard text differs in HEAD; git show proves both working files equal HEAD and hashes differ. Those files are untouched. Global suites are reserved for the final umbrella pass.
- 2026-11-14 build: completed; next validate (1 Done checklist item(s) left unticked)
- 2026-11-14 validate: independent review: spec and implementation-quality reviewers approved the corrected current candidate; original pre-validation findings and their regression contracts are recorded above. No live tools or reviewer edits were used.
- 2026-11-14 validate: DEVIATION validate: strict --run/global Python/frontend/Chromium proof is omitted - the user reserves that one global pass for the final umbrella; final proof is restricted to directly affected component and concurrency contracts. Untouched guard-copy mismatch is excluded explicitly and remains a baseline limitation.
- 2026-11-14 validate: final: uv run --frozen --no-sync --project 04_Software --extra web python -m pytest -q -p no:cacheprovider --tb=short 04_Software/tests/test_shared_resources.py 04_Software/tests/test_state.py 04_Software/tests/test_metrics.py 04_Software/tests/test_execution.py 04_Software/tests/test_chatgpt.py 04_Software/tests/test_native_chatgpt.py 04_Software/tests/test_pi_installation.py 04_Software/tests/test_preparation_lifecycle.py 04_Software/tests/test_local_execution.py 04_Software/tests/test_run_concurrency.py 04_Software/tests/test_drift_recovery.py 04_Software/tests/test_profile_cli.py 04_Software/tests/test_web_archive.py 04_Software/tests/test_web_delete.py 04_Software/tests/test_web_environment.py 04_Software/tests/test_checkpoint_handoff.py 04_Software/tests/test_container_timeout.py 04_Software/tests/test_isolation.py 04_Software/tests/test_container_git.py -k "not managed_pi_ships_the_reviewed_guard"; exit 0; 799 passed, 6 platform symlink skips, 1 explicit untouched baseline deselection, 1 Starlette/httpx deprecation warning; 79.99s.
- 2026-11-14 validate: final: uv run --frozen --no-sync --project 04_Software --extra web python -m pytest -q -p no:cacheprovider --tb=short 04_Software/tests/test_orchestrator.py; exit 0; 313 passed, 3 platform symlink skips, existing Starlette/httpx warning; 93.52s. Targeted test_smoke.py -k "process_log or logs_remain" exit 0; 3 passed, 51 deselected. Total final targeted Python proof: 1115 passed, 9 skipped, 1 baseline deselection.
- 2026-11-14 validate: final: targeted Ruff over every changed Python source/test exit 0; python .agentic/aegis.py check --task TASK-cadbef92 --strict exit 0 (no --run, errors=0, warnings=82, strict ok); release-notes --since bf58e2f exit 0; git diff --check exit 0. Help contracts 13 passed; npm exec -- vite build and stamp_web_assets.py exit 0; bundle input/output fingerprints match current source and include new help.
- 2026-11-14 validate: accepted warnings: AEGIS historical metadata/stale-path findings are outside this task; derived help/notes/static artifacts have traceability heuristic warnings. The minified generated bundle exceeds the built-in line-scan bound; Vite configuration has no credential defines, frontend input changes are only eight help paragraphs, and complete input/output fingerprints were verified. Vite chunk-size and Starlette/httpx warnings are pre-existing/nonblocking. No target repository checks or live forge/model/runtime/DCP operations were performed.
- 2026-11-14 validate: acceptance: same-clone concurrent provisioning/checkpoint/finish preserves SQLite/JSONL rows; cancel/native release preserves peer worktree/runtime/scope; production construction keeps same-ticket profiles distinct with different backend/runtime/model/environment; injected negative Git/contention/ownership/report/auth tests fail closed; archive/delete barriers include terminal or removed-state execution and explicit-home/nested deletion cases. No task acceptance criterion remains unmet.
- 2026-11-14 validate: completed; next done

## Rulings

- RULING-001 | date=2026-11-14 | decision=Autopilot on master; only targeted validation per session; global validation once after all subtickets | reason=Explicit activation and updated user instruction from coordinator | source=user | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-cadbef92.md
changed: WK-03 resource isolation, short shared locks, ownership barriers and atomic metrics; docs/help/notes updated
evidence: Targeted Python: 1115 passed, 9 skipped, 1 baseline deselection; help 13 passed; Ruff, release notes, Vite/fingerprints, static AEGIS strict and diff check passed
issues: Global validation deferred by user; untouched baseline Pi guard-copy text mismatch remains
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-11-14)

- stage: validate; type: feature; path: full; branch: master
- requirements:
  - REQ-REL-284af472 - Serialize shared repository mutations without holding execution
  - REQ-SEC-fc949861 - Refuse unproven run resource effects
  - REQ-DATA-54868516 - Preserve all concurrent terminal metrics in atomic mirrors
  - REQ-REL-2e8dc2a1 - Serialize common prerequisite and credential mutations independently
  - REQ-REL-23c94e15 - Require a complete project run barrier for archive and deletion
  - REQ-FUNC-aae1904f - Remove only the current project's proven terminal resources
  - REQ-FUNC-bcaf01be - Remove an archived project's ADORE resources on deletion
- deviations: 2 recorded
  - build: late inventory log/clone/admission follow-ups preceded their new tests - accepted as bounded integration corrections; dedicated negative contracts now pass.
  - validate: strict --run/global Python/frontend/Chromium proof is omitted - the user reserves that one global pass for the final umbrella; final proof is restricted to directly affected component and concurrency contracts. Untouched guard-copy mismatch is excluded explicitly and remains a baseline limitation.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base bf58e2f: 71 file(s) changed, 2517 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=82 notes=28
- checklist: 8/9 done; open: `report` appended
