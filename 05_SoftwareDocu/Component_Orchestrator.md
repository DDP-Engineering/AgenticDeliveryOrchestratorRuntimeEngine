<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Orchestrator Component

## 1. Purpose

`adore/orchestrator.py` is the deterministic ADORE conductor around the
agent-driven AEGIS workflow. It prevents silent stalls and keeps remote
publication human-approved and draft-only.

## 2. Responsibilities

- select/claim forge tickets and provision worktree/container isolation;
- create and bind active/historical AEGIS tasks;
- launch a fresh executor session for each stage attempt;
- journal a versioned telemetry observation for every executor launch, including
  unavailable and administrator-disabled capture; keep the existing numeric
  `usage` event only when capture produced values, linked to the observation
  by the run/attempt event ID; an explicit complete zero-token report remains
  `reported`, while partial or absent token evidence is `unavailable`;
- compose each stage prompt as an explicit autopilot-to-deliver instruction
  that has the executor record `interaction: autopilot` in the journal and
  forbids commit, push, MR/PR creation, merge, and child task journals;
- validate full/quick progression and documented validation rollback;
- create an unpushed local checkpoint commit after every successful stage,
  using the configured agent identity even when the host clone has no
  repository or global Git identity;
- distinguish clarification, stage failures, transient infrastructure failures
  and immediate integrity/policy/budget failures;
- persist and deliver mandatory incident/terminal/approval notifications;
- integrate the target, run independent strict verification and fingerprint the
  candidate/target/commit series;
- require a fresh approval-label transition after presentation;
- push and open/update a draft MR/PR, then require journal close-out at done;
- adopt an existing open branch MR/PR before attempting draft creation;
- create a new AEGIS task before consuming each bounded review request;
- reconcile parked, approval, review, stale-working and outbox states;
- garbage-collect only resources not owned by active or failed runs, including
  orphan allowlist proxy containers and egress networks.

The component never edits AEGIS journals, gives forge credentials to an
executor, or merges.

## 3. State Machine

Lifecycle states are `working`, `parked-clarification`, `awaiting-approval`,
`publishing`, `in-review`, `failed`, `done`, and `cancelled`. AEGIS stage is tracked
separately.

Every nonterminal state has a poll action. Clarification has a timeout;
`awaiting-approval` and `in-review` intentionally do not because they are
human-paced states. A stale `working` state with no live conductor becomes a
loud failure rather than occupying capacity.
An authorized web cancellation creates a per-run marker after worker-side
grant recheck. Before more stage work, the conductor handles that marker with
normal `cancel()` teardown. A watcher during a working executor gate uses the
container's bounded interrupt call, then the conductor marks the run cancelled
instead of counting an executor failure. The marker is cleared after teardown.
The 60-second grace is valid only under the single-conductor lock invariant:
operator mutations and poll conduction cannot run concurrently.
Closing the source ticket while clarification or approval is waiting, or while
an MR/PR remains open in review, cancels through the normal teardown path with
outcome `ticket closed`. A merged or closed-unmerged MR/PR is authoritative and
is reconciled before the source ticket state.

## 4. Recovery Contract

`max_stage_failures` counts attempts for the current stage. The default third
failure posts a terminal comment, stops the container and preserves the
worktree. Routine cleanup protects failed worktrees, container companions and
evidence until explicit retry, cancel or delete. Multiple AEGIS findings in
one invocation count once. A successful
stage transition resets the counter. Questions do not consume it.
The active wall-clock budget restarts when clarification resumes, a review
revision begins, approval is invalidated for re-conduction, or an operator
explicitly retries. Iteration, cost, and file budgets remain cumulative.
Revision and approval invalidation reset the stage-failure counter for their
new work phase; clarification resume preserves failures already recorded for
the current stage.
An AEGIS invocation timeout is recorded as `AEGIS_TIMEOUT` through this same
stage-attempt path instead of escaping and terminating the poller. When an
attempt remains, conduction retries immediately inside the same locked
conductor; the configured limit remains terminal. Clarification expiry uses the
validated configuration duration parser, including numeric and uppercase-unit
forms.
All container-bound AEGIS clients receive the run's mounted io directory;
pre-pick repository compatibility probing remains a direct host subprocess.
Executor failure classification uses `GateRun.timed_out` exclusively:
timeout-like stderr without the flag is `EXECUTOR_EXIT`, while a true wrapper
timeout remains `EXECUTOR_TIMEOUT` regardless of its stderr wording.

`max_transient_retries` covers container/fetch/forge transport independently.
Required comments are outboxed before transport. A write failure stops code
work and polling replays it without consuming an execution slot.
Terminal status-write failures retain the existing `cancelled`, `done`, or
`failed` lifecycle and outcome while the status replay remains queued.

Ticket task type resolves fix/bug, change, then configured feature labels;
unmatched tickets use `workflow.default_kind`. Each global budget check reads
durable cost once.

Clarification handoff text is consumed once. After the question is posted and
journaled, `ADORE_QUESTIONS.md` is removed on a fail-safe basis so it cannot be
included in a later integration checkpoint.

## 5. Validation and Approval

The conductor integrates `origin/<target>`, runs the validation executor, then
calls `check --task <id> --strict --run --json`. It requires at least one
executed successful verification command and a task at deliver. The deviations
that journal recorded are copied into the validation evidence and lead the
approval presentation; they inform the approver and never block. Approval is
bound to the candidate fingerprint and target commit. Any drift or product
mutation invalidates approval.
On clarification resume and approval observation, title/body drift refreshes
the persisted ticket snapshot and content hash and records `ticket content
changed since pickup`; the observation alone does not invalidate the candidate.
Publication retry rechecks approval freshness. Existing open branch MRs are
adopted before creation, and a task already at `done` still receives the shared
close-out checkpoint/push recovery before entering review.

Two triggers feed one governed revision path: the revise label a human applies,
and a newly `failed` forge pipeline when `[review] on_pipeline_failure` is
`revise`. An explicit human request wins when both are present. A pipeline
repair applies no label, so none is removed, and the executor's thread is
prefixed with the instruction that a green pipeline is part of this round's
acceptance criteria. Only a CHANGED verdict is a signal, and `pipeline_reported`
is cleared when a revision starts, so the pipeline the revision produces is
judged on its own and one failure cannot restart a round already in flight.
Both triggers share `max_review_rounds`, so a permanently red pipeline cannot
loop; when the budget is spent the run keeps waiting in review with a comment
saying so. Every round still ends at strict validation and a fresh human
approval before a push, so automatic repair never weakens the delivery gate.

The revise label remains present through provisioning, AEGIS probe, and task
creation. It is removed only after the new task exists and immediately before
the run-state transition. Without an AEGIS idempotency key, a crash in that
small boundary can leave a duplicate/orphan task; the pre-removal task-created
journal event provides operator evidence and preserves at-least-once intent for
ordinary failures.

## 6. Dependencies

Internal dependencies: config, state, AEGIS client, executor launcher,
isolation, forge adapters, identity, metrics and utilities. All decision
collaborators are injectable for offline tests.

## 7. Validation and Tests

`tests/test_orchestrator.py` covers full/quick paths, fresh sessions,
checkpointing, two failures then success, exact third-attempt abort,
finding-count semantics, one-time question handoff and cleanup, incident
editing, outbox outage/replay, closed-ticket cancellation, ticket-content
refresh, MR fallback/adoption, approval retry freshness, close-out recovery,
revise-label ordering, AEGIS timeout handling, typed executor-timeout
classification, clarification duration forms, live-lock-safe cleanup,
failed-resource preservation, egress companion GC, configured task-kind
fallback, one-read cost checks, environment precedence, human-merge metrics,
prompt restrictions and the absence of a merge capability.

`poll_once(ticket_iid=IID)` filters ticket selection to one ready ticket while
preserving the same eligibility and publication gates. This is the web worker's
selected-ticket start path; the existing polling path is unchanged.
