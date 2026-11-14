# TASK-50d7f4bf - WK-07 integrated worker acceptance and operator evidence

stage: done
type: change
path: quick
interaction: autopilot
requirements: REQ-REL-83b9fc8c, REQ-FUNC-43e2f999, REQ-REL-c240007b, REQ-REL-af360022, REQ-FUNC-80b5347e, REQ-FUNC-bee68a72, REQ-FUNC-3b737a5c
parent:
branch: master
base: e0a62729cf0391ea5d1fb9ad56d064ec3fd3b636
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

Problem: STATED (#90/WK-07): integrated acceptance of #83 must demonstrate independent projects, bounded per-project run pools, scoped configuration and safe recovery without a redundant global suite.
Desired outcome: STATED: exact criterion-to-executed-proof inventory, focused offline regressions for remaining integration gaps and truthful operator/help/component documentation.
Actors: STATED: operator/admin, supervisor, project/configuration/run workers, controlled forge/executor transports.
Primary scenario: STATED: A/B N=1 overlap, A N=2 with third waiting; B/global settings respond while A is blocked; cancellation, capacity reduction, pause and crash preserve ownership/effects.
Examples: STATED: two started jobs may continue above reduced N; pending initial reservations start only within current N.
Counterexamples: STATED: two working labels are not concurrency evidence; an unavailable Linux host is not native Linux acceptance.
In scope: STATED: offline integrated contracts, bounded temporary process smoke, acceptance matrix, relevant operator/component/help reconciliation and relevant integration defects.
Out of scope: STATED: no commit/push/merge, Gitea/DCP operations, target-repository suites, migrations, planning changes, package rebuilds or deployment/setup automated tests.
Constraints: STATED: shared master (explicit user choice), version 0.15.0; autopilot; maximum 12 edit/verify cycles, 120 minutes and 120 files per batch. Only targeted validation now; one complete final umbrella validation after coordinator commit and explicit activation.
Success signals: STATED: controlled executor entry plus independent process birth evidence, current scoped outcomes, no duplicated uncertain effects and exact platform limitations.
Evidence: OBSERVED: clean master at e0a62729; test_web_supervisor.py has real-process barriers, run concurrency/configuration/ownership/resource contracts exist; Configuration_Reference.md, Portable_Project_Settings.md and Component_Config.md still claim serial-only operation.
Assumptions: INFERRED: reusing strong existing contracts plus focused integration gaps avoids a redundant acceptance suite.
Unknowns: UNKNOWN: available native Linux/WSL/package runtime and final full-suite result; inspect without treating adapter fakes as native acceptance.
Decision-blocking questions: None; explicit activation authorizes implementation and targeted proof.
Proposed behaviors: None; existing product contracts are authoritative.
Path and reason:

| Criterion | Holds? | Evidence |
| --- | --- | --- |
| no new externally observable behavior | yes | Acceptance/tests/docs of delivered #84-#89 contracts |
| no new interface or data format | yes | Existing public worker/configuration/admission APIs |
| no new dependency | yes | pytest + standard-library process helpers |
| existing requirement covers behavior | yes | Requirement coverage below |
| no security or data-handling change | yes | Existing fail-closed fencing/isolation contracts |

## Requirement coverage

| Behavior | Requirement | Design / proof seam |
| --- | --- | --- |
| Independent projects and N run processes | REQ-FUNC-43e2f999 | Real-process file barriers; integrated settings during blocked executor |
| Home/ancestry fencing | REQ-REL-c240007b | Existing owner/corrupt/unknown probes |
| Bounded shutdown and uncertain outcomes | REQ-REL-af360022 | Real process death/restart and no replay |
| Durable scoped configuration | REQ-FUNC-80b5347e | Real blocked A + HTTP/worker B/global result |
| Immediate control outside long/run capacity | REQ-FUNC-bee68a72 | Pause/Cancel contracts with full pools |
| Reduced N controls queued initial starts | REQ-FUNC-3b737a5c | Existing actual-process capacity regressions |
| Transient sharing conflicts retain state and writer fencing | REQ-REL-83b9fc8c | Bounded local I/O retries; typed persistent denial |

## Design

Quick path: reuse the real-process supervisor helper, add only missing integrated assertions and scenarios. External forge/Git/runtime/executor collaborators remain simulated; no target tests run. Document exact commands and oracles in an operator acceptance matrix. Existing requirements remain unchanged unless coverage linkage needs extension. No new product interface, schema or dependency. Discovered Windows sharing contention uses the same six-attempt, 250 ms scheduled retry bound as reviewed settings; authority is rechecked on each publish attempt, persistent failure remains a distinct StateStorageError subtype and preserves prior bytes; listings/admission propagate it rather than omitting a reservation as corrupt.


Acceptance inventory: [Worker_Acceptance.md](../../01_Documentation/Worker_Acceptance.md)
records each exact executed criterion/test, commands/results and platform limits.

## Log

- 2026-11-14 frame: journal opened
- 2026-11-14 frame: completed; next build - Existing worker contracts; quick acceptance and documentation change, scope authorized
- 2026-11-14 build: Scope discovery: real N=2 Windows acceptance exposed PermissionError during concurrent state reads/replacement; extend state-store requirement/proof and documentation without changing stored schema.
- 2026-11-14 build: red: uv run --frozen --extra web python -m pytest -q tests/test_state.py -k state_sharing exit 1; 5 failures show missing bounded sharing retries and writer refencing (REQ-REL-83b9fc8c).
- 2026-11-14 build: green: test_state.py exit 0, 80 passed; integrated seven-module worker acceptance exit 0, 234 passed in 110.68s (one existing FastAPI/httpx deprecation); WSL adapter 4, native/auth boundary 12 and forge adapter 12 selected tests passed. No global suites run.
- 2026-11-14 build: help: updated (all four Jobs locales explain pending reservations after lower N, continuing started jobs and independent configuration); restricted help grammar forbids HTML/legal comments so existing comment-free format retained.
- 2026-11-14 build: release-notes: added (Windows sharing contention repair is visible to jobs; test/doc acceptance needs no additional note). Version remains 0.15.0.
- 2026-11-14 build: Manual operational observation: one-off Python stdin driver staged current application/launcher in auto-cleaned extracted bundled Windows and Linux runtimes, recomputed temporary inventory, launched two paused profiles on a free loopback port, replaced configuration without changing project PIDs, killed supervisor and observed old tree death/new service readiness, then portable Stop exit 0/all identities dead. Windows native and Ubuntu/WSL Linux both PASS; original archive SHA256 unchanged. Initial Windows staging retained obsolete assets and was corrected by replacing only disposable app directory. No deployment/setup automated tests or final archive rebuilds.
- 2026-11-14 build: DEVIATION validate: complete umbrella proof deferred until post-commit explicit activation - user requires exactly one final full run; present pass uses targeted contracts and static checks only. Linux smoke is Ubuntu under WSL, not bare-metal/service-manager acceptance; real Pi/forge/runtime/cgroup jobs remain operator-owned.
- 2026-11-14 build: completed; next validate
- 2026-11-14 validate: Review round 1: specification P2 full-pool Cancel test bypassed ProjectWorker dispatch; quality P2 exhausted sharing StateError could be swallowed as corruption by list_runs after a successful invalid_runs scan, permitting capacity omission. Fix scheduler-driven Cancel proof and distinct propagating storage error with a public admission regression.
- 2026-11-14 validate: returned to build - Review round 1: preserve storage-unavailable propagation through capacity; prove Cancel dispatch at full pool
- 2026-11-14 build: red review fix: state listing sharing denial tests exit 1 (2 failed); public admission storage-loss-between-scans test exit 1 (1 failed), proving the capacity omission. Beginning second bounded batch for review fixes, max 12 cycles/120 min/120 files; first batch stayed below limits.
- 2026-11-14 build: Review-fix recheck: 182 passed, 2 failed in changed scoped 184-test command; real Windows CRT file opens expose errno EACCES without winerror. Added CRT-shaped read/write boundary cases; red: test_state.py -k 'state_sharing_contention and crt' exit 1, four expected failures. Extend only Windows EACCES classification; unrelated I/O remains unchanged.
- 2026-11-14 build: green review fixes: targeted affected final command (test_state.py plus scheduler Cancel, scan-loss admission and both real-process lower-N cases) exit 0, 90 passed in 13.16s including all 86 state cases. Additional Start-idempotency and unaffected scope passed in preceding 184-test run (182 passed; two CRT failures now corrected). Focused Ruff exit 0. StateStorageError propagates through listing/admission; Windows CRT EACCES is bounded like explicit winerror.
- 2026-11-14 build: completed; next validate
- 2026-11-14 validate: Final documentation reconciliation removed remaining stale independent verification-command claims from project context and Operations Guide; agent-owned repository checks remain unchanged. No software/test changes after round-2 review.
- 2026-11-14 validate: Review round 2: independent spec and quality reviewers approved current code/tests and reconfirmed final documentation-only reconciliation. No remaining actionable findings. Unchanged scoped green proofs retained per user instruction, complete final umbrella proof not started.
- 2026-11-14 validate: final targeted substitute: python .agentic/aegis.py check --task TASK-50d7f4bf --strict exit 0 (strict ok; errors=0, warnings=71, notes=28); release-notes check --since e0a62729 exit 0; git diff --check exit 0. No --run/global suite executed. Historical stale-path/test-link/journal advisories are outside this task; large generated JS secret scan skip is accepted for the rebuilt fingerprinted bundle sourced from reviewed tracked inputs, not credentials. Review approvals current; targeted green evidence and platform limitations recorded in Worker_Acceptance.md.
- 2026-11-14 validate: completed; next done

## Rulings

- RULING-001 | date=2026-11-14 | decision=Targeted validation only before WK-07 commit; complete umbrella validation only after separate explicit activation | reason=Current user instruction via coordinator; autopilot, no routine confirmations; max 12 cycles/120 min/120 files per batch | source=user | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-50d7f4bf.md
changed: WK-07 integrated contracts, bounded Windows storage fix, reconciled docs/help and rebuilt bundle ready for coordinator commit
evidence: Targeted Python/help proofs and Windows/Linux temporary portable smoke passed; round-2 spec/quality approved; final strict static/release-notes/diff checks exit 0
issues: Complete umbrella pytest/frontend/Chromium/--strict --run deferred by explicit instruction until post-commit activation; Linux smoke Ubuntu/WSL; live forge/model/runtime/native cgroup acceptance and final archive publication not performed
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-14)

- stage: validate; type: change; path: quick; branch: master
- requirements:
  - REQ-REL-83b9fc8c - Bound transient run-state sharing contention without losing valid evidence
  - REQ-FUNC-43e2f999 - Supervise independent project workers and per-project run pools
  - REQ-REL-c240007b - Refuse duplicate supervisors and fence children after parent death
  - REQ-REL-af360022 - Stop owned worker trees within a bounded shutdown
  - REQ-FUNC-80b5347e - Durable scoped configuration results
  - REQ-FUNC-bee68a72 - Admission control bypasses long configuration work
  - REQ-FUNC-3b737a5c - Queue initial dispatch under current project capacity
- deviations: 1 recorded
  - validate: complete umbrella proof deferred until post-commit explicit activation - user requires exactly one final full run; present pass uses targeted contracts and static checks only. Linux smoke is Ubuntu under WSL, not bare-metal/service-manager acceptance; real Pi/forge/runtime/cgroup jobs remain operator-owned.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base e0a6272: 31 file(s) changed, 861 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=71 notes=28
- checklist: 9/9 done
