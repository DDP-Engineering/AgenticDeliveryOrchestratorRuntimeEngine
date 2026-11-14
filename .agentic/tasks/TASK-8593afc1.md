<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-8593afc1 - WK-05 scoped asynchronous configuration control

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-80b5347e, REQ-FUNC-5afa4cd1, REQ-SEC-13dc5428, REQ-SEC-ec87820f, REQ-REL-4c269cd5, REQ-FUNC-bee68a72
parent:
branch: master
base: 886fd48298bb099c217184bebabb5c8d1d85483f
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
- [ ] final `check --strict --run` result logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem: OBSERVED app.py holds one config_lock across model/host probes and settings work in HTTP requests; WK-04 configuration_loop consumes only pause/resume/delete.
Desired outcome: STATED WK-05 requires durable independent configuration/control, explicit project/global domains, revision/access fencing and bounded independent long work.
Actors: STATED administrator, project-scoped operator, configuration worker, independent run workers.
Primary scenario: STATED long execution/provision in A while B saves and an allowed global administration operation completes.
Examples: STATED container edit in B preserves A; incompatible A edit stays staged with explicit conflict.
Counterexamples: STATED missing scope, stale revision, revoked authority and concurrent stale saves fail closed.
In scope: STATED existing settings/probe/control HTTP paths, durable configuration dispatch/results, short project writes and protected credentials; documentation and focused proof.
Out of scope: STATED no Gitea/DCP, commits/push, version changes, target-repository retesting, migrations, other journals, 00_Planning or final umbrella suite.
Constraints: STATED master/exclusive shared checkout; autopilot; 12 edit/verification cycles, 120 minutes, 120 files per batch; targeted validation only. Version 0.15.0.
Success signals: STATED all four issue acceptance criteria and control independent of execution/configuration slots; HTTP accepted is never applied.
Evidence: OBSERVED web/store.py already owns explicit configuration domains, generation/authority fencing and opaque configure references. OBSERVED config_edit.py supplies per-profile kernel edit lock; app.py already stages reviewed candidates and refuses unsafe application.
Assumptions: INFERRED existing short global account/audit writes can stay synchronous because they hold no execution locks; existing status/error codes remain authoritative inside durable outcomes.
Unknowns: none decision-blocking; live provider/runtime acceptance excluded by explicit instruction.
Decision-blocking questions: none; user authorized complete implementation and routine choices.
Proposed behaviors: accepted under autopilot: long existing routes return 202 identity/status, admin reads exact redacted outcome; browser waits for actual completion. Separate bounded long and fast configuration lanes preserve B responsiveness.
Path and reason:
| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | durable asynchronous response |
| no new interface/data format | no | protected work/result envelope |
| no new dependency | yes | Python standard library |
| existing requirement fully covers | no | WK-05 |
| no security/data change | no | execution-time authority |
Full path.

## Requirement coverage

| Requirement | Behavior | Design | Proof |
|---|---|---|---|
| REQ-FUNC-80b5347e | return HTTP 202 with its durable explicit scoped operation identity before executing it. | Scoped dispatcher | tests/test_web_configuration_worker.py |
| REQ-FUNC-5afa4cd1 | provide independently bounded fast-project and global control progress outside executor capacity. | Scoped dispatcher | tests/test_web_configuration_worker.py |
| REQ-SEC-13dc5428 | enforce its immutable project identity, inspected configuration revision and current administrator authority. | Scoped dispatcher | tests/test_web_configuration_worker.py |
| REQ-SEC-ec87820f | retain secret data only in existing protected-record storage while exposing opaque references and redacted outcomes in operations and history. | Scoped dispatcher | tests/test_web_configuration_worker.py |
| REQ-REL-4c269cd5 | retain the candidate and report an explicit conflict without changing the running configuration. | Scoped dispatcher | tests/test_web_configuration_worker.py |
| REQ-FUNC-bee68a72 | process the control independently of long configuration tasks and free executor slots. | Scoped dispatcher | tests/test_web_configuration_worker.py |

## Design

### Approach
STATED/OBSERVED: reuse WebStore configuration domains/ownership, existing reviewed handlers and protected atomic file primitives. Decorate affected existing routes at registration, so no old mutation/probe path bypasses durable dispatch (REQ-FUNC-80b5347e).
Use one independent configuration process with bounded fast and long pools, at most one mutating configure request per project in flight; global short account/audit writes stay in their existing independent SQLite domain (REQ-FUNC-5afa4cd1).
Pause/resume use a separate immediate control pass sharing the scoped owner, regardless of pool saturation; cancel stays on independent project command/watcher path (REQ-FUNC-bee68a72).
### Interfaces and data
202 returns id/status/domain/project_id; existing GET operation adds exact public response and HTTP outcome only after confirmed completion. Queue stores opaque salted content references only; protected input/output files reuse existing private-record primitives and strict bounded JSON (REQ-SEC-ec87820f).
Bind project ID, actor, handler and source SHA at submission; rehydrate only declared Pydantic bodies and a tiny method/private-session-header Request. Reauthorize before runners and publication; stale inputs fail with established codes. Crash leaves uncertain operations without replay (REQ-SEC-13dc5428).
Release project edit/admission locks around model, host and plan probes, then reacquire and recheck revision/rights to publish. Unsafe apply leaves existing pending candidate and terminal project_has_active_work conflict (REQ-REL-4c269cd5).
### Files and test seams
New web/configuration.py dispatcher and tests/test_web_configuration_worker.py; app.py existing route registration and short publication guards; supervisor.configuration_loop integration; store unfinished-operation exclusion and result scope; existing browser request helper awaits durable response. Update shared test client only where needed to consume asynchronous contract honestly.
### Additional reviewed decisions
OBSERVED: all reviewed onboarding/check/create/environment routes dispatch through existing server-administration authority, with explicit prospective targets and independent per-resource scheduling. Claims bind exact inspected operation IDs. Native/preparation settings use long capacity; ordinary saves retain fast capacity.
OBSERVED: settings GET reads only strict current execution-plan cache; explicit host checks/reviewed apply refresh it. An owned disposable model probe retains worker/ancestry-only cleanup after actor revocation/deadline, with eight-second cleanup commands; result publication remains denied. Profiles retry only transient Windows replacement-sharing reads, at most five attempts/185 ms delay, preserving corrupt-data refusal.

### Risks and open decisions
Secrets must never enter SQLite result/audit or public envelope; corrupted/missing work files fail closed. Bounded queue and work lifetimes; explicit operation ownership persists during blocking work. Existing schema 18 is reused unchanged, no migrations or readers for other versions. No live runtime/model acceptance.
### Requirement map
All six requirements map to the dispatcher, existing route safety guards and focused deterministic HTTP/worker tests above.
Diagrams: [diagram_TASK-8593afc1.md](diagram_TASK-8593afc1.md)


## Log

- 2026-11-14 frame: journal opened
- 2026-11-14 frame: User instruction: targeted validation only; no global pytest/frontend/Chromium or strict --run. Full umbrella proof deferred. Autopilot, master, no commit/push, max 12 cycles/120 minutes/120 files per batch.
- 2026-11-14 frame: completed; next specify - WK-05 full scope recorded under explicit autopilot (7 Done checklist item(s) left unticked)
- 2026-11-14 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-14 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-14 build: red: uv run --frozen --extra web python -m pytest -q tests/test_web_configuration_worker.py exit 1: existing Save returns 200 and applies before durable acceptance (REQ-FUNC-80b5347e).
- 2026-11-14 build: Batch 1 closed after initial dispatcher, focused contracts and independent review. Batch 2: same explicit limits, max 12 edit/verification cycles, 120 minutes and 120 files; resolve review findings, onboarding/environment durability and final documentation/targeted proof. No global suite.
- 2026-11-14 build: Review corrections: detect ambiguous 32-hex names; fence immediately before publication; normalize corrupt private outcomes and enforce status/code consistency; preserve uncertainty after confirmation failures; dispatch onboarding and managed image preparation outside API; choose long settings lane for plan probes.
- 2026-11-14 build: release-notes: added (Settings stays responsive during independent project work and tool preparation; en/fr/de/ro).
- 2026-11-14 build: help: updated (project/global ownership, confirmed saves and independent controls; Settings en/fr/de/ro).
- 2026-11-14 build: Scope evidence: targeted concurrent configuration test exposed transient Windows metadata read sharing during atomic profile save (operation project identity read refused). Read profiles knowledge/source. Add bounded sharing-only read retries without weakening corrupt/missing schema refusal.
- 2026-11-14 build: red: pytest tests/test_profiles.py::test_profile_read_bounds_windows_sharing_contention exit 1 (2 failures): transient sharing denial rejects first read, persistent denial stops after 1 rather than bounded 5 attempts.
- 2026-11-14 build: Targeted component run: 249 passed, 3 failures out of 252 selected settings/model/repository/executor/ChatGPT contracts; missing-config, corrupt-active UTF-8 and tampered-candidate regressions corrected and their focused reruns passed. No global suite ran.
- 2026-11-14 build: Targeted final integration increment: 29 passed, 1 transient Windows profile metadata sharing failure; isolated rerun passed and deterministic sharing happy/persistent-denial red/green tests now prove bounded correction (4 selected checks passed).
- 2026-11-14 build: green: durable worker/process, scoped staging/revisions, mid-flight revocation, private corruption, model-owned cleanup, deadline outcome, managed-image independence, settings cache, exact lane claims, and focused existing integrations; commands and final selected totals recorded at validate.
- 2026-11-14 build: DEVIATION build: several review-added boundary regressions followed implementation rather than an initial red run; accepted with actual targeted green assertions and repeated independent reviews, leaving no before-change red evidence for those cases.
- 2026-11-14 build: Batch 2 closed: all review corrections implemented; 80 or fewer changed paths outside generated task evidence, no 00_Planning/other task journal edits. Final batch is bounded targeted proof/static review/closure only (max 12 cycles, 120 minutes, 120 files).
- 2026-11-14 build: Independent read-only reviews approved current runtime candidate. Final native staged-apply cache regression observed red then green: preflight refusal preserves config/pending/foreign cache, explicit deletion then reviewed retry succeeds. Global/project configuration history red/green also proves strict redacted projection.
- 2026-11-14 build: AEGIS static has zero errors; remaining warnings concern pre-existing stale requirements/historical journal records outside this task. Own source and generated static bundle traceability now mapped.
- 2026-11-14 build: completed; next validate (1 Done checklist item(s) left unticked)
- 2026-11-14 validate: Validation formatting correction: the first final scoped Ruff invocation found 5 formatting-only findings; all corrected before final proof. Earlier Ruff successes remain historical, not a claim about that failed invocation.
- 2026-11-14 validate: DEVIATION validate: strict --run/global pytest/frontend/Chromium replaced by the narrow final configuration/control contracts because the user explicitly reserves full validation for the final umbrella pass. Live provider/runtime/forge and manual checks excluded by instruction.
- 2026-11-14 validate: Final proof scope: rerun the new configuration worker contracts after the central profile-sharing and cache-publication corrections, plus precisely affected stored profile/environment, stage/apply, transfer, ownership and full-capacity scheduler integrations. No unchanged global suite repeated.
- 2026-11-14 validate: final: from 04_Software, uv run --frozen --extra web python -m pytest -q tests/test_web_configuration_worker.py tests/test_profiles.py::test_profile_read_bounds_windows_sharing_contention tests/test_profiles.py::test_corrupt_profile_json_fails_closed tests/test_web_environment.py::test_worker_owned_preparation_persists_progress_for_another_api_instance tests/test_web_pending_config.py::test_stage_review_apply_and_discard_config tests/test_web_transfer.py::test_transfer_roundtrip_independent_stopped_and_replay tests/test_web_ownership.py::test_global_and_project_configuration_references_are_isolated tests/test_web_supervisor.py::test_project_paused_start_admits_only_and_full_pool_defers_queue - exit 0, 32 passed in 36.01s; only existing Starlette TestClient deprecation warning.
- 2026-11-14 validate: final: scoped Ruff over every changed/new Python file exit 0; node --test web/tests/configurationTasks.test.mjs exit 0 (4 passed); prior targeted configuration/help contracts exit 0 (17 total); npm --prefix web run typecheck exit 0 and production build exit 0 (existing large-chunk warning only); release notes --since 886fd48 exit 0.
- 2026-11-14 validate: final: canonical stamp_web_assets.fingerprint matches committed-source working-tree production bundle; first handwritten raw-byte checker lacked CRLF normalization and was replaced by this canonical check. EOF-only whitespace corrected; git diff --check exit 0. No runtime or AST change after targeted proof; both reviewers reconfirmed approval.
- 2026-11-14 validate: final: AEGIS static check --task TASK-8593afc1 --full exit 0, errors=0 warnings=70 notes=28, all remaining warnings historical/out-of-scope. No own uncovered source or incomplete review warning. No strict --run, global pytest/frontend/Chromium, live acceptance, Gitea/DCP operation, commit, push or version change performed.
- 2026-11-14 validate: completed; next done (1 Done checklist item(s) left unticked)

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-8593afc1.md
changed: WK-05 complete: durable scoped configuration worker, independent lanes/control, guarded publication and cleanup, checked-plan cache, browser bridge, docs/help/release notes
evidence: Targeted pytest 32 passed; JS 4 passed; help contracts passed; changed-Python Ruff, typecheck/build, release notes, canonical bundle fingerprints and diff check exit 0; AEGIS static 0 errors
issues: Full umbrella/Chromium validation and live checks deferred by instruction; 70 historical static warnings and test-first history deviation recorded; no known scoped defect
spec_compliance: approved
implementation_quality: approved
review_round: 6

## Delivery report (2026-11-14)

- stage: validate; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-80b5347e - Durable scoped configuration results
  - REQ-FUNC-5afa4cd1 - Independent bounded configuration lanes
  - REQ-SEC-13dc5428 - Configuration execution authority and revision fencing
  - REQ-SEC-ec87820f - Protected configuration references
  - REQ-REL-4c269cd5 - Unsafe changes retain explicit staged conflict
  - REQ-FUNC-bee68a72 - Admission control bypasses long configuration work
- deviations: 2 recorded
  - build: several review-added boundary regressions followed implementation rather than an initial red run; accepted with actual targeted green assertions and repeated independent reviews, leaving no before-change red evidence for those cases.
  - validate: strict --run/global pytest/frontend/Chromium replaced by the narrow final configuration/control contracts because the user explicitly reserves full validation for the final umbrella pass. Live provider/runtime/forge and manual checks excluded by instruction.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=6
- diff vs task base 886fd48: 81 file(s) changed, 3565 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=70 notes=28
- checklist: 8/9 done; open: final `check --strict --run` result logged truthfully after the last edit
