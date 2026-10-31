<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-f6de6c0b - Quiesce timed-out container commands before retry without losing dependencies

stage: deliver
type: fix
path: full
interaction: autopilot
requirements: REQ-FUNC-bff135e2, REQ-REL-ea593cbb, REQ-REL-d8e08cca, REQ-DATA-62052e16
parent:
branch: task/adore-web-interface
base: 7a588905de14d68503d47a6321b0e9c3b1114d32
opened: 2026-10-30

Before editing this journal, read `.agentic/templates/task.md` for record syntax
and pause/report rules. Reuse its guidance if already read in this intact session.

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [ ] validation evidence, diff, exclusions, and outcome presented
- [ ] delivery confirmed by the human
- [ ] journal and report included in the delivery commit
- [ ] agreed outcome delivered, normally a PR
- [ ] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: OBSERVED: issue25 build exceeded its 3600-second gate deadline; subsequent attempts 17/18 failed opening /adore/io/output.jsonl. The after terminal stop/start, manual retry could write IO and kept installed packages. OBSERVED: execution.py BoundTarget returns the runtime timeout result without an explicit quiescence step. INFERRED: a timed-out runtime client can leave container descendants holding exchange files. UNKNOWN: exact file-handle mechanism until controlled acceptance.
Desired outcome: STATED: generic ADORE corrections and saved-progress continuation with agent-installed dependencies preserved; INFERRED restoration of repository bounded-run rule: timed-out bound execution must not leave active writers competing with recovery.
Actors: Coding executor, common container backend, runtime, conductor and operator.
Primary scenario: An owned command reaches its deadline -> common backend settles the timed-out execution before output retention/retry -> timeout evidence remains truthful and the same owned container filesystem is reusable.
Examples: OBSERVED live issue25 timeout then Directory nonexistent; INFERRED controlled fixture: timed-out shell has a child writer, after recovery it cannot append and the same container keeps its dependency marker.
Counterexamples: A replaced/foreign container must not be stopped; failed cleanup must not be presented as successful execution or admit an unsafe next command.
In scope: Shared container timeout recovery, identity/runtime trust boundaries, offline public contract tests, controlled disposable container acceptance and directly affected operator/component documentation.
Out of scope: STATED delivery boundary: no merge or unauthorized publication. INFERRED from user preserved-progress request: no automatic container replacement or dependency erasure. Other implementation belongs to issue25 and the already-reviewed native Git task.
Constraints: STATED portable Python, forge/executor agnostic core, offline fake CLI unit proof, typed failure at external boundaries, autopilot=true, separate network authority and bounded autonomous work.
Success signals: Timeout remains a timeout; no original command process remains when a retry is admitted; original resource/image/files/dependencies survive; wrong identity or failed runtime cleanup raises a typed recovery error.
Evidence: OBSERVED StateStore events19:29:34 timeout,19:29:54/19:30:32 output-open failures, same-ID retry19:36 and dpkg/UID/IO readiness checks19:37; source execution.py BoundTarget and ContainerBackend lifecycle; knowledge/execution.md. STATED user asks correct ADORE generically and finish #25.
Assumptions: INFERRED dedicated run containers permit reversible interruption of their processes; verify actual runtime behavior during design.
Unknowns: Exact quiescence mechanism and its bounded failure response, legacy unpinned binding treatment, confirmation ordering and whether a new API is needed; settle against existing contracts before implementation.
Decision-blocking questions: None for the stated bounded-recovery restoration; technical mechanism and fail-closed design remain specify/design work.
Proposed behaviors: Proposed, not yet accepted mechanism: verified stop/start of the same owned container to settle descendant writers without new image dependencies; evaluate with a disposable fixture.
Path and reason: full; timeout lifecycle and trust boundaries need explicit outcomes/design and existing requirements do not yet establish this exact response.

Bound: at most 8 implementation increments, 3 hours of active timeout-correction work and 30 scoped files; any disposable runtime fixture is bounded to 180 seconds and removed. Preserve the active issue25 resource and the immutable native Git candidate. Product implementation starts after that candidate is proved/frozen.

| Quick-path criterion | Result | Evidence |
|---|---|---|
| no new externally observable behavior | unknown | bounded behavior is established, exact recovery outcome needs specification |
| no new interface or data format | unknown | settle backend recovery mechanism before build |
| no new dependency | unknown | verify runtime lifecycle suffices |
| existing requirement covers behavior | no | existing cancel/preparation clauses do not specify this command timeout recovery |
| no security/data-handling change | no | ownership and mutable output recovery require explicit admission |

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary/failure | Verification | Design |
|---|---|---|---|---|---|---|
| Safe next attempt | Settle a reported timeout before next dispatch | REQ-FUNC-bff135e2 | timed-out writer gone | normal exit control | public fake lifecycle + Docker | D1 |
| Fail closed | Refuse unconfirmed recovery | REQ-REL-ea593cbb | exact evidence admitted | identity/status/control failure | public negative lifecycle tests | D3 |
| Retain dependencies | Preserve owned resource and authority | REQ-REL-d8e08cca | same ID/image/files/network/user | no replacement/policy mutation | fake lifecycle + Docker marker | D2 |
| Truthful evidence | Preserve original command result | REQ-DATA-62052e16 | timeout fields unchanged | normal exit124 not timeout | public result comparison | D4 |

Behavior inventory: the bound backend observes actual timeout, settles process
lifetime, admits only proven recovery and retains original result data. Resource
preservation, failure response and result semantics can vary independently and
therefore have distinct contracts. Existing shared routing, recipe recovery and
operator-cancel requirements remain unchanged; none specifies this exact timeout
settlement outcome.

## Design

- D1 / REQ-FUNC-bff135e2: BoundTarget captures an authoritative running resource
  snapshot before dispatch and addresses its immutable ID. After a reported
  timeout, ContainerBackend verifies that same resource, interrupts it through
  the existing runtime API and verifies the same ID/image in exited state before
  returning. Output retention therefore follows process quiescence.
- D2 / REQ-REL-d8e08cca: retain the stopped resource as a private pending-resume
  entry. The next bound command or normal provision verifies that stopped ID,
  starts the same container and verifies running identity before dispatch. No
  create/remove, image pull, permission or egress mutation occurs.
- D3 / REQ-REL-ea593cbb: unconfirmed ownership/status, failed stop/start or corrupt
  runtime evidence leaves the active backend admission blocked with
  ExecutionRecoveryError. The conductor handles this typed failure as an explicit
  terminal infrastructure failure; pending user cancellation keeps precedence.
  It does not spend the normal executor retry loop on unsafe recovery.
- D4 / REQ-DATA-62052e16: return the original CommandResult after confirmed stop;
  do not replace its exit, timeout, output, stderr or accounting fields with
  lifecycle-control results. A normal exit124 without timed_out does not recover.
- Boundaries: execution.py owns admission and pending/blocked recovery state;
  ContainerManager retains existing bounded inspect/interrupt/start operations;
  orchestrator.py owns terminal lifecycle and the existing failure message code.
  Native targets, recipe replay rules and executor adapters retain their APIs.
- Identity admission: validate supplied pins before runtime effects, observe a
  complete running identity for legacy unpinned commands, and compare captured
  ID/image on every recovery control. Changed names/IDs/images fail before
  signalling or restarting a replacement. The runtime strict parser remains
  authoritative; no permissive JSON/exit-code interpretation is added.
- Recovery state: pending/blocked records are private to the active backend.
  Confirmed stopped container state and installed files persist in the runtime.
  A fresh controller uses existing owned provisioning; pre-result controller
  crashes remain under existing interrupted-run policy. No run-state schema or
  profile migration is introduced. Explicit stop/interrupt/remove clears a
  pending automatic resume so operator lifecycle control remains authoritative.
- Concurrency: the conductor serializes one run; the cancel watcher remains an
  independent stop request. Restart is deferred to a later admitted command so
  the conductor can honor cancellation before another executor launch.
- Limits: use current bounded runtime APIs (inspect30s, interrupt20s, ordinary
  start at the established command bound). Cleanup is separate from the expired
  executor budget; no unbounded wait or automatic replacement is permitted.
- Tests: new public bound-target runtime-double cases cover normal/timeout/
  exit124, immutable-ID dispatch, stopped receipt, same-resource pending resume,
  drift/corrupt/failed controls and blocked later commands. A conductor failure
  test proves terminal state and no new executor attempt. Existing execution,
  preparation, native, package and orchestration cases provide regression seams.
- Alternatives: killing only the host runtime client leaves writers; selecting
  process groups can miss detached executor descendants; replacing the container
  discards dependencies; an in-image timeout helper adds another runtime
  protocol/dependency. Same-container interruption uses existing authority.
- Expected files: execution.py, orchestrator.py, focused timeout/conductor
  tests, owning component/knowledge pages, operations guidance, current context,
  four job-help locales and release/changelog records. Design estimation reserves
  28 scoped files rather than the provisional24; scope outcomes are unchanged.
- Risks: all run-owned container helper processes stop on timeout. This is
  intentional containment of the expired dedicated run, with filesystem state
  retained. A failed runtime control requires explicit operator recovery.
- Open decisions: none before build. Product edits wait for TASK-95ab438a's
  ongoing final proof and immutable candidate freeze.
- Diagrams: [diagram_TASK-f6de6c0b.md](diagram_TASK-f6de6c0b.md).

## Log

- 2026-10-30 frame: full-path generic bounded-container recovery restoration accepted under existing user authority and autopilot=true. Runtime/file ownership and preserved dependency state need explicit specify/design. Existing native Git correction remains a separate frozen candidate; no product edit starts during its final proof.

- 2026-10-30 specify: four new atomic draft contracts, no revisions/reuse/retirements, and one shared recovery protocol cover timeout settlement, unsafe admission, retained resource authority and truthful result data. Existing routing, recipe replay and operator-cancel contracts stay unchanged. Exact stop/start ordering and failure propagation remain design decisions.

- 2026-10-30 design acceptance: controlled cached-image/network-none fixture reproduced a reported timeout with one remaining writer; deleting its open IO file caused the same Directory nonexistent on the next write. Verified stop/start preserved container/image/dependency marker, removed the writer and restored IO. Disposable fixture removed; live issue25 untouched. An earlier two-second transport probe expired before a writer started and is not causal evidence.

- 2026-10-30 design: verified same-container interruption plus deferred owned restart selected; identity failure blocks active admission and the conductor records terminal infrastructure failure. The four contracts map to D1-D4 and saved structure/sequence/state diagrams. Runtime public APIs remain unchanged; implementation and first red await the native Git candidate freeze. Scoped file estimate refined from 24 to 28 before implementation; outcomes and 3-hour active work bound remain unchanged.

- 2026-10-30 build red: shared public seam for REQ-FUNC-bff135e2, REQ-REL-ea593cbb, REQ-REL-d8e08cca and REQ-DATA-62052e16; command=`.\.venv\Scripts\python.exe -m pytest -q tests/test_container_timeout.py --tb=line` from04_Software exits1: 15 expected failures and8 controls pass, exposing missing quiescence, immutable dispatch and fail-closed restart. Before conductor changes, `tests/test_container_timeout.py::test_unconfirmed_recovery_is_terminal_without_another_executor_attempt --tb=short` exits1 with unhandled ExecutionRecoveryError. No product implementation edit preceded either observation. Native Git candidate is proved and frozen at tree4738b97109a8c1400f43918cff9a4e99d6955436; it excludes this task.

- 2026-10-30 DEVIATION build: extend scoped file bound28 to30 before updating two existing runtime doubles for the strengthened authoritative identity/quiescence contract. The512-case focused run found only a missing fake identity API and a fake that always reported running after interruption; product admission is not weakened.

- 2026-10-30 build red / REQ-REL-ea593cbb: `.\.venv\Scripts\python.exe -m pytest -q tests/test_container_timeout.py -k changed_caller --tb=line` exits1 (one failing local-kind ownership case, three rejection controls pass). Pending restart must validate the complete caller identity before any start effect.

- 2026-10-30 build red / REQ-REL-ea593cbb: `.\.venv\Scripts\python.exe -m pytest -q tests/test_container_timeout.py -k explicit_owned_release --tb=line` exits1: successful explicit owned removal leaves stale active-backend quarantine and rejects a separately operator-recreated resource. Clear only after successful explicit release; normal unsafe retries remain blocked.

- 2026-10-30 build: owning execution/conductor docs and knowledge, contexts, operator recovery and all four job-help locales reconciled. release-notes: updated (merge related Jobs progress/retry/timeout notes within the ten-entry cap). help: updated (container timeout and fail-closed recovery, all locales).

- 2026-10-30 build red / REQ-REL-ea593cbb: `.\.venv\Scripts\python.exe -m pytest -q tests/test_container_timeout.py -k untrusted_initial --tb=line` exits1 with three expected failures: an initial untrusted identity was rejected only for one call, then silently readmitted when the injected receipt changed. Keep the active target blocked until explicit recovery.

- 2026-10-30 build red / REQ-REL-ea593cbb: `.\.venv\Scripts\python.exe -m pytest -q tests/test_container_timeout.py -k interrupt_during_restart --tb=line` exits1: operator interruption delivered during runtime start was overwritten and another executor command ran. Honor operator parking before and after deferred start, quiescing any concurrently restarted resource before raising.

- 2026-10-30 design refinement before review: retain the original active-backend quarantine contract after unconfirmed recovery, including after explicit release. The provisional same-backend reopening exercised by the prior release-red records is not required by accepted scope and would need a separate absence-confirmation protocol. Do not add it. Updated public proof requires continued refusal in that backend and allows an explicitly inspected/recreated resource only through a fresh controller, as existing operator recovery already does. Successful timeout recovery and ordinary preparation replay remain unchanged.

- 2026-10-30 build green: final focused isolation/execution/preparation/package/native/conductor proof exits0: 520 passed,1 existing skip,1 upstream Starlette/httpx warning; all32 timeout cases pass. Ruff,10 help tests, production build and release-note checker pass. Final controlled network-none Docker proof confirms original timeout data, stopped writer, same-ID/image deferred restart, retained dependency marker and writable IO after unlink; user adore and network none unchanged. Disposable fixture removed; live issue25 unchanged. All four delivered requirements are active with root-relative linked tests.

- 2026-10-30 validate preparation: final focused command `.\.venv\Scripts\python.exe -m pytest -q tests/test_container_timeout.py tests/test_execution.py tests/test_isolation.py tests/test_container_git.py tests/test_system_packages.py tests/test_preparation.py tests/test_preparation_lifecycle.py tests/test_local_execution.py tests/test_orchestrator.py --tb=short` exits0 (520 passed,1 skip,1 upstream warning,61.51s). Hunk review, all four active requirements, owning knowledge/context and error/cancel paths reconciled; final evolution20:36 covers17 non-agentic changes. Generated help bundle derives from reviewed locale content; legacy unrelated advisory debt remains out of scope. Independent reviews precede the one final strict full proof.

- 2026-10-30 validate review round1: specification compliance approved; implementation quality approved, no actionable findings. Both independent before/after observations and coordinator pre-proof verification match all27 path hashes and canonical binding c6f5f0b5308283c92d2df57b9781d3c51241485fadde2b0053147b4874a5b5af. Quality independently observed32 timeout cases passed. No candidate edit follows these verdicts; final configured strict full proof starts now.

- 2026-10-30 additional manual acceptance: disposable cached-image container with network none and normal UID1000 installed a self-contained local Debian package through the authorized apt manager. An unrelated sudo id was denied. After a real timed-out writer, the bound path kept the same container/image and installed root-owned package payload, removed the writer and restored IO after unlink; deferred restart retained network none/user adore. Fixture/container/cache volumes removed, active issue25 untouched. No source or bound candidate changed.

- 2026-10-30 validate complete: final `python .agentic/aegis.py check --task TASK-f6de6c0b --strict --run --json` exits0 in1349.85s after both round1 approvals: 2239 Python passed,8 existing skips,1 upstream Starlette/httpx deprecation; Ruff passed; all226 Chromium passed. Strict errors0,warnings182,notes22,promoted warnings0. Remaining findings describe established unrelated layout/coverage/journal debt, pending delivery records and bounded scan limits for reviewed derived assets, not an unresolved new behavior failure. All27 raw hashes and canonical binding c6f5f0b5308283c92d2df57b9781d3c51241485fadde2b0053147b4874a5b5af remain unchanged after proof.

- 2026-10-30 deliver preparation: reread delivery step after validation, retain both approved verdicts and freeze the scoped candidate against the preceding validated Git tree. Only journal/manifest/delivery records change after proof. Newly discovered timeout correction awaits explicit local commit approval; no commit, push, PR or merge is performed. Continue independently authorized issue25 implementation/validation.

- 2026-10-30 DEVIATION validate (discovered during delivery inspection): the configured legacy full suite also executed setup/deployment-script tests despite the current user instruction excluding them. This was an unrequested verification-scope expansion, not a new product defect or skipped product proof. The observed all-green counts remain factual and include those legacy cases; no host installation was performed by their injected doubles. Do not repeat those tests. Future verification selects permitted product tests, with setup scripts inspected manually. No source, test, requirement or specification is changed here; the bound source and current review verdicts remain intact.

- 2026-10-30 correction to preceding deviation record: direct source inspection disproves the inference about this checkout. Its test_web_package.py contains only third-party notice consistency, with no installer behavior; references to release/asset metadata checkers likewise are not setup execution. The installer tests were observed in the older AppData issue25 checkout, not in this validated root suite. Withdraw the incorrectly attributed root verification-scope deviation; factual full-proof counts and source bindings remain unchanged. The issue25 operator handoff will align that separate checkout with the current explicit user rules before its final verification.

## Rulings

- RULING-001 | date=2026-10-30 | decision=Use autopilot and retain human publication approval | reason=User explicitly requested autopilot=true and generic corrections during real issue25 acceptance | source=user | supersedes=none

## Handoff

current: deliver
status: waiting
next: Approve a local commit of the frozen timeout correction
must_read: .agentic/tasks/TASK-f6de6c0b.md, .agentic/tasks/delivery_TASK-f6de6c0b.md, .agentic/tasks/TASK-f6de6c0b.candidate.json, .agentic/steps/6_deliver.md
blockers: Explicit approval for this newly discovered local delivery

## Stage report

stage: deliver
result: paused
current: deliver
changed: Generic timeout settlement, same-container restart, typed terminal handling and owning tests/docs/help
evidence: 2239 Python passed,8 skips; Ruff passed;226 Chromium passed; strict exit0; both round1 approvals;27 hashes intact
issues: 182 nonpromoted advisories,22 notes,1 upstream warning; failed admission needs operator inspection/fresh controller
next: Approve a local commit of the frozen timeout correction
needs_user: yes
spec_compliance: approved
implementation_quality: approved
review_round: 1
