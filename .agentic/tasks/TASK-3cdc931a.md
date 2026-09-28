<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-3cdc931a - Account for Pi executor token usage and cost

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-FUNC-28f0cd82
parent:
branch: ddp/pi-usage-accounting
base: a4d0e20b0046fc07d4e29bb688e0e5e383fbaac0
opened: 2026-09-28

## Done checklist (current stage)

- [x] Validated candidate confirmed unchanged except revalidated changelog correction
- [x] Validation evidence, diff, exclusions and local commit outcome presented
- [x] Local commit and task closure approved by the human
- [x] Journal and delivery report included in commit candidate
- [x] Approved repository-local commit prepared
- [x] Close-out carried by successful local delivery commit

## Frame

Problem: Pi emits assistant usage but the launcher returns zero usage, bypassing the USD budget.
Desired outcome: Correct every reported NIL blocker with reproducible, validated changes.
Actors: Owner, DCPServer operator, ADORE, Pi executor, Gitea.
Primary scenario: Authorized repair -> setup/launcher correction -> evidence of ready paused NIL deployment.
Examples: A valid assistant response contributes its usage exactly once; the server runs the owner's supplied NIL commit.
Counterexamples: Invalid credentials or failed validation leave pickup paused; duplicate summary events never double-charge usage.
In scope: 04_Software/adore/executor/launcher.py; verification, current operator/component docs, governed journals.
Out of scope: Git commits, pushes, ticket pickup, merges, unrelated project work.
Constraints: No secrets in repository/output; host mutations use numbered script; preserve existing profile/run state and other services.
Success signals: Run public run_gate tests for multiple assistant messages, repeated agent_end, cached input, malformed and invalid usage; verify real Pi stream yields 1077 input, 5 output and USD 0.002204.
Evidence: STATED: repair reported NIL cost blocker; OBSERVED: server pi-smoke.jsonl has message_end assistant usage and repeats it in agent_end; launcher PiExecutor inherits zero extraction.
Assumptions: Existing Pi OAuth is reusable; local archive provides the pinned toolchain.
Unknowns: Results of current project validation and environment import until executed.
Decision-blocking questions: Resolved by user authorization to update checkout, create branches and use autopilot through validation.
Proposed behaviors: Sum valid assistant message_end input, cacheRead/cacheWrite and output tokens plus cost.total; ignore agent_end duplicates and malformed/non-finite/negative usage records. Preserve unmetered streams as zero for compatibility.
Path and reason: full; credentials/environment setup introduces interfaces and dependency integration; usage handling adds observable budget behavior.
Quick-path assessment: no new behavior=no; no new interface=no for setup/yes for launcher; no new dependency=no for setup/yes for launcher; existing requirement=unknown; no security/data change=no for setup/yes for launcher. Full path follows.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design |
|---|---|---|---|---|---|---|
| Correct deployment readiness | Collect Pi usage once per assistant response | REQ-FUNC-28f0cd82 | Valid setup/stream | Failed prerequisite/invalid record | Run public run_gate tests for multiple assistant messages, repeated agent_end, cached input, malformed and invalid usage; verify real Pi stream yields 1077 input, 5 output and USD 0.002204. | Sum valid assistant message_end input, cacheRead/cacheWrite and output tokens plus cost.total; ignore agent_end duplicates and malformed/non-finite/negative usage records. Preserve unmetered streams as zero for compatibility. |

## Design

Sum valid assistant message_end input, cacheRead/cacheWrite and output tokens plus cost.total; ignore agent_end duplicates and malformed/non-finite/negative usage records. Preserve unmetered streams as zero for compatibility.

OBSERVED boundaries: credentials remain host-only; the existing model and thinking selection remain GPT-6 Sol/medium; Pi emits cumulative assistant usage only at message_end.
Audit: preserve draft-only publication and pause; use offline project checks and source hashes.

## Log

- 2026-09-28 frame: Full path; scope authorized by user; autopilot through validation, no commits/pushes/resume.
- 2026-09-28 specify: Atomic requirement and positive/failure observations written; no unresolved scope decisions.
- 2026-09-28 design: Existing public seams and staged host script selected; build begins.

- 2026-09-28 build red: command=`PYTHONPATH=04_Software python -m pytest -q 04_Software/tests/test_executor.py -k "pi_collects or pi_ignores"`; exit=1; nine cases return zero instead of observed assistant usage. Local project venv trampoline is unavailable; native Python has required test tools.

- 2026-09-28 build green: `PYTHONPATH=04_Software python -m pytest -q tests/test_executor.py` from 04_Software: 31 passed; launcher and tests pass Ruff. Locked dev environment restored with `uv sync --python D:/Programms/Python_3_13/python.exe`; canonical verification can run.

- 2026-09-28 validate: `python .agentic/aegis.py check --task TASK-3cdc931a --strict --run` exit=0; full configured test and lint commands pass, errors=0. The fingerprints-tracked warning refers to two pre-existing tracked sidecars outside this task; no new tracked fingerprint files. Evolution contains exactly launcher, tests, component doc and changelog.

- 2026-09-28 host validation: numbered server setup applied the checksum-gated launcher patch with an original backup; public PiExecutor replay of the observed Pi stream reports 1077 input tokens, 5 output tokens and USD 0.002204. No new inference or ticket pickup. Candidate executable tree unchanged since final local proof.

- 2026-09-28 delivery approval: user says "ok, close task and commit changes". Approved outcome is one local integrated commit in each repair repository and closure of these completed repair journals; remote push/PR/merge and NILO ticket closure are outside this outcome. Final candidate scope includes source/tests/current documentation, governance records and requested same-version packages; DCP excludes the unrelated WireGuard archive and .claude settings.

- 2026-09-28 local delivery close-out: approved integrated local commit carries this done journal and report. Report-time advisory counts are scoped to each journal: earlier ADORE tasks do not claim later feature coverage; TASK-4f1d55b2 provides the integrated final proof. Remaining close-out checklist warnings resolve with this journal update; prior accounted repository findings remain. Commit-only outcome has no subsequent push/PR/deployment gate. NILO ticket #26 is not closed or handed off.

## Rulings

- RULING-001 | date=2026-09-28 | decision=Autopilot through validation; update server checkout and create repair branches; leave commits, pushes and pickup paused | reason=Explicit user reply | source=user | supersedes=none

- RULING-002 | date=2026-09-28 | decision=Close completed repair journals and commit integrated changes locally | reason=Current explicit user approval | source=user | supersedes=none

## Handoff

current: done
status: ready
next: None; approved local commit is the delivery outcome
must_read: .agentic/tasks/TASK-3cdc931a.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Pi usage accounting; local commit and task closure
evidence: Canonical ADORE full tests/Ruff/strict exit0;282 Linux component cases; equal63-file archives
issues: Accepted advisory findings recorded; NILO #26 remains stopped at validate
next: None; local commit only
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

## Delivery report (2026-09-28)

- stage: deliver; type: fix; path: full; branch: ddp/pi-usage-accounting
- requirements:
  - REQ-FUNC-28f0cd82 - Collect Pi assistant token and cost usage
- deviations: none recorded
- explicit review: disabled; existing validation remains required
- diff vs task base a4d0e20: 56 file(s) changed, 2582 line(s) added
- checks: errors=0 warnings=15 notes=1
- checklist: 5/6 done; open: Close-out carried by successful local delivery commit
