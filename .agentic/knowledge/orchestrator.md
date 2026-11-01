<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Orchestrator

## Routing

Use this page for ticket selection, run lifecycle, stage gates, approval,
publication and recovery. Start at `04_Software/adore/orchestrator.py` and
verify with `04_Software/tests/test_orchestrator.py`. Web queueing belongs to
`web-interface.md`; CLI argument parsing belongs to `cli.md`.


`REQ-FUNC-93bd42af`: Human-merged reviews trigger configured, leased remote run-branch cleanup on every forge. Final publication persists its commit independently of progress-publication policy. Bounded cleanup failure completes the merge with a branch-retained warning and preserves local evidence. Closed unmerged reviews authorize no remote deletion.

## Purpose and boundaries

The orchestrator conducts one agent-operated AEGIS task through isolation,
bounded stage execution, validation and configured draft or ready publication. AEGIS owns its task
journal and closes it in validate, the executor performs code work, and forge
adapters perform remote operations. ADORE verifies the validate -> done advance
itself, presents the candidate and publishes with Git and forge operations only.
ADORE never merges or gives forge credentials to an executor.

## Public interface

`poll_once(ticket_iid=None)` selects an eligible ticket and conducts its run;
`run_loop()`, `retry(run_id)`, `cancel(run_id)`, `handoff(run_id)` and
`reset(run_id, stage)` expose bounded operations; reset accepts `frame`,
`specify`, `design`, `build`, `validate` or `publishing`.
`Orchestrator.from_config()` constructs the conductor from validated settings
and binds project-scoped forge credentials through repository-auth.md using
the env-file directory. Worktree/container/executor credentials stay separate.

## Invariants

The conductor owns ticket claiming, worktrees/containers, budgets, retries,
clarification parking, outbox replay, candidate fingerprinting and human-approved
MR/PR publication. One AEGIS task is pinned to each run. The executor's
validate -> done advance triggers ADORE's own strict verification; strict
verification and fresh candidate-bound approval precede the push and draft or
ready creation, and no executor session or AEGIS command runs after approval.
A done task without verification evidence returns to validate through
one fresh session first, and a failed check is routed back from done. A run
keeps the stage done while it awaits approval, publishes and is in review;
guarded progress checkpoints default to enabled and stay on the owned ticket branch and do
not open an MR/PR. Drift forces re-conduction. Failed and handed-off resources
remain available for recovery. Cleanup works only on this project's run IDs and
keeps active, failed, human-owned and corrupt runs' resources. Selected-ticket
requests retain readiness, hold and exclude checks. Pickup eligibility is the
shared `adore.selection.ineligibility` rule set, which the web ticket browser
also reports, so a ticket shown as startable is one the conductor selects.
Worker-authorized cancellation markers interrupt a working executor gate;
the conductor alone finalizes cancellation and clears the marker.
At a safe boundary, a requested handoff stops autonomous work, preserves the
worktree and wins over a concurrent cancellation request. A foreign remote
checkpoint commit stops execution instead of replacing human work.
An idle poll republishes failed-run recovery commits only when the local branch
has advanced or a recorded transport error remains; a verified checkpoint
does not refresh historical run timestamps. Stage prompts declare autopilot,
have the executor finish with `advance` and stop with `log` and `pause`, and
never name a deliver stage. The conductor is the only stage owner; API
requests do not conduct in the HTTP process.

## Change map

| Change requested | Start with | Focused verification |
|---|---|---|
| Stage flow, verification trigger, return to validate | `_conduct_task_impl`, `_strict_verification`, `_validation_failure` | `test_orchestrator.py` path, route and remediation tests |
| Approval and publication | `_present_for_approval`, `_approval_ready`, `_publish_impl` | `test_orchestrator.py` publication tests, `test_checkpoint_handoff.py` |
| Executor prompts | `_stage_prompt` | `test_orchestrator.py` prompt tests |
| Retry and reset | `retry`, `_published`, `reset`, `RESETTABLE_STAGES` | `test_orchestrator.py` reset tests, `test_smoke.py` |
| Checkpoints and human handoff | `_checkpoint`, `_push_checkpoint`, `handoff` | `test_checkpoint_handoff.py` |
| Cleanup | `cleanup`, `purge_resources` | `test_orchestrator.py` cleanup tests |

## Key behaviors

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: The conductor selects the shared native backend and pins plan/resource, retaining the same AEGIS/executor/approval loop. Native provisioning skips images/setup/auth copies. Retry/parking preserve identity; local cleanup removes worktrees only after verified control. Container cleanup protects persisted native runs after backend drift.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


Container profiles without recipes retain the existing recovery/profile-update contract and empty execution record; immutable preparation policy applies to recipe runs.

- `REQ-FUNC-e5419c07`: Resolve/persist plan, pin base commit, bind identity, provision/check/stage auth, then execute bounded preparation before AEGIS/AI. Immutable receipts and policy/resource IDs guard resume; explicit replay recreates the owned container and retains worktree/history.

- `REQ-FUNC-ff7dad34` - candidate-bound approval and human-approved draft or ready publication.
- `REQ-FUNC-9246f8cc` - the validate -> done advance triggers the strict check before presentation.
- `REQ-FUNC-faab24b2` - a conduct step that starts at done without verification evidence
  returns the task to validate first.
- `REQ-FUNC-67469d47` - a failed independent check is routed back from done.
- `REQ-FUNC-67bd56c8` - publication pushes and opens or adopts the MR/PR with no executor session or AEGIS command.
- `REQ-FUNC-fbc3fca5` - prompts name `advance`, `log` and `pause`; continuations name `brief` and the State.
- `REQ-FUNC-f9bdb5d2` - reset accepts only the conducted stages and publishing,
  and refuses every target for a run recorded at deliver.
- `REQ-FUNC-d8d1b95b` - retry returns a published candidate to review, resumes an
  approved unpublished one and conducts any other run from done.
- `REQ-FUNC-40057219` - publication refuses a run outside stage done or publishing.
- `REQ-FUNC-ab65704b` - recorded deviations lead the approval presentation.
- `REQ-FUNC-83133b5e` - deterministic stage failure and timeout recovery.
- `REQ-FUNC-93bd3c8e` - NO_STAGE_PROGRESS evidence carries the gate's stderr tail
  after its sentence: NUL and ANSI stripped (an open OSC/DCS string stops at its
  line) and redacted on the whole stderr before the 20-line/2000-character cut, so
  a cut never splits a key from its secret; the terminal `run.outcome` keeps the
  sentence through `_head_and_tail` over `_sanitize(evidence, None)`, for every code.
  The strip-redact-cut is the shared `util.output_tail`, also used by the web
  worker's operation detail with its own redaction.
- `REQ-FUNC-1ec4a21d` - durable notification outbox replay.
- `REQ-FUNC-f9946b6b` - selected-ticket web start uses the normal conductor.
- `REQ-FUNC-448cbde7` - usage events carry executor/model/review-round context
  and explicit token/cost coverage for web analytics. Complete zero-token
  reports remain known zero; partial records do not create numeric usage.
- `REQ-REL-94e653aa` - configurable remote checkpoints and durable human handoff
  preserve DCP recovery evidence and the fresh approval boundary.

## Files

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


- `04_Software/adore/orchestrator.py` - lifecycle and gate logic.
- `04_Software/tests/test_orchestrator.py` - selection, recovery and delivery.
- `04_Software/tests/test_checkpoint_handoff.py` - checkpoint and handoff edges.

## Automatic loop cadence

`run_loop()` uses the shared `adore.polling.PollCadence` policy documented in
[Polling cadence](polling.md). It retains the conductor lock, typed
forge/unexpected-error logging, local quiet windows and interrupt cleanup.
Success resets backoff; a quiet round preserves it. Each wait begins after the
round completes. Offline regression: `test_loop_polling_cadence_matches_web_errors_and_success`.
