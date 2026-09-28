<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Recovery and Maintenance

## Recovery Invariants

- ADORE reads only run-state schema 1. It migrates no earlier state shape.
- AEGIS task journals, not executor sessions, decide resume stage/path.
- Failed runs stop their container, release capacity, preserve worktree/state,
  and require explicit `adore retry`.
- Retry resets the active stage counter and active-work clock, but preserves
  failure history, task history and audit events.
- Retry is refused while a required notification is pending.
- ADORE never edits an AEGIS journal to recover it and never merges.

## Standard Recovery

1. Read the terminal ticket/MR comment and local log.
2. Inspect the active AEGIS task without editing it:

   ```text
   python .agentic/aegis.py status TASK-<id> --json
   ```

3. Repair the external cause: payload, repository, container image, forge
   transport, target conflict, budget/scope, or human answer.
4. Confirm the required notification outbox has delivered through a poll.
5. Run:

   ```text
   adore --profile <name> retry <run-id>
   ```

The first retry attempt is a fresh model session and re-reads durable artifacts.
An interrupted publication retry also rechecks fresh approval. If the label was
removed, ADORE returns to validation/presentation instead of publishing. Work a
failed publication attempt left in the worktree is committed before the retry
proceeds, so a half-finished bookkeeping attempt does not block the next one;
the candidate-mutation guard still compares against the state the human
approved.

## When Retry Cannot Help

`adore retry` re-runs the same decision against the same durable state. One
failure is therefore immune to it: `FORBIDDEN_STAGE_TRANSITION`, raised when the
journal reports a stage ADORE cannot legally reach from the one it recorded, and
the stages in between carry no Log entry of their own. Retrying replays the
identical refusal.

Read the journal, decide which stage the work genuinely reached, then move
ADORE's own record to a stage the journal's stage is reachable from, and retry:

```text
adore --profile <name> reset <run-id> --to validate --force
adore --profile <name> retry <run-id>
```

The terminal comment for this failure names that command. Reset changes only
ADORE's record; the AEGIS journal stays untouched, and the run re-verifies from
the stage you chose rather than trusting the executor's claim.

## Stage-Failure Accounting

With the default threshold of three, the third failed attempt aborts. One
executor nonzero/timeout, no-progress outcome, repairable journal failure,
strict-check invocation, unresolved conflict, or post-validation mutation is
one attempt regardless of the number of findings it contains.

Successful unfinished stage work can continue without spending or resetting the
failure count. ADORE requires changed authored candidate content plus a strict,
nonempty append to the task Log, creates a local checkpoint and records
`stage-continuation`. The next session reads the durable Handoff and remaining
work; the stage stays unchanged until completed. Each continuation consumes the
existing iteration, active-time, cost and file budgets.

`NO_STAGE_PROGRESS` counts as a stage failure when either progress signal is
missing or the existing Log was rewritten. Journal-only updates and generated
cache changes do not establish candidate progress. A nonzero/timeout gate still
counts as a failure even when it changed files. `WORKTREE_PROGRESS` stops the run
immediately when Git or content reads fail; restore reliable worktree observation
before retrying. Use `logs <run-id>` to distinguish continuation from failure.

Questions do not count. Temporary container, fetch or forge transport failures
use the independent transient counter.

## Reported-Cost Stops with Subscription Executors

When a failed run reports `BUDGET_EXHAUSTED: cost budget reached`, inspect its
profile's `max_cost_usd` and executor authentication. The cost field is executor
telemetry; it does not establish a provider charge. For subscription/local
execution, set `[budgets] max_cost_usd = 0`, validate the profile, and use the
standard recovery procedure to retry the preserved run. Historical usage remains
in the journal and metrics. Other run bounds and provider usage quotas still
apply. A positive cap continues enforcing its threshold against cumulative usage,
so a retry with the same positive cap and accumulated cost can immediately stop.

## Notification Outage

Do not restart code work manually. Restore host CLI authentication/network,
then run a normal poll. Pending notifications replay without using an execution
slot. Once the outbox is empty, explicit retry is permitted.

## Candidate or Target Drift

ADORE removes stale approval and routes back to integration/validation. Review
the new presentation and freshly add the approval label again. Never reuse the
old approval based on a visually similar diff.

## Clarification Recovery

Answer on the source ticket and add `agent-answered`. A normal poll supplies
the bounded human thread to a fresh executor. If the timeout or round limit has
already failed the run, explicitly retry only after deciding how to provide the
missing direction again: terminal retry starts a fresh stage session but does
not replay ticket comments posted after the run left `parked-clarification`.
The questions handoff file is removed after its text is posted and journaled.
If the ticket title/body changed, the snapshot is refreshed and the resume
thread records `ticket content changed since pickup`.

## Review Recovery

Apply `agent-revise` only when a bounded review round should begin. A newly
failed forge pipeline starts the same kind of round on its own when
`[review] on_pipeline_failure` is `revise`, the default; the draft carries a
comment saying so, and the journal records the trigger. Set the key to `notify`
if you would rather be asked first, or `ignore` for a repository with no CI.
Repairs and requested revisions share `max_review_rounds`, so a permanently red
pipeline cannot loop: when the budget is spent the run waits in review with a
comment rather than failing. Every round creates a new task journal. If the review limit fails the run, a human must
decide whether to raise the configured limit and retry or continue manually.
Task creation happens before ADORE removes the revise label. When label removal
fails, the run fails closed and the label remains. Because AEGIS has no
idempotency key, inspect `revision-task-created` for a possible orphan task
after a crash in the narrow create/remove/state-save boundary.

If publication created an MR/PR but failed to persist its identity, retry adopts
the existing open branch MR/PR. If the AEGIS task is already done, recovery
still checkpoints and pushes close-out changes before returning to review.

## State Surgery and Cleanup

`reset --to <stage> --force` changes ADORE state only. The active AEGIS journal
remains executor-owned and will be reread; therefore reset cannot falsify a
journal transition. Use it only after understanding the mismatch, then run
`retry`.

`cleanup` clears only a readable local lock whose recorded PID is provably gone,
then removes orphan executor/proxy containers, egress networks and worktree
husks. Active and failed runs are protected: a failed run's container
companions, worktree and evidence remain available for `retry`. Release those
resources explicitly with `cancel <run-id>` while retaining audit state, or
with irreversible `delete <run-id> --force` after separately preserving any
required evidence. A live, different-host, unreadable, or otherwise unknown
lock remains present and is reported as `lock_held_by`; never remove it until
ownership is verified. Cleanup reports corrupt state and never auto-deletes it.

Stop the service poller before `retry`, `cancel`, `delete`, or `reset`; these
commands acquire the same single-conductor lock and refuse a live/unknown
holder. `pause` prevents new pickup but does not stop the poller or release its
lock. `logs` is read-only and remains available during conduction.

## Human takeover and remote recovery

Enable `delivery.publish_checkpoints=true` to keep committed WIP checkpoints
available on the ticket branch. Visibility does not mean delivery approval.
Inspect the last verified remote commit and any stale-upload error in ticket
status; local work remains authoritative after a failed upload.

Request exclusive human ownership using the public operator command:

```bash
adore --profile nilo handoff RUN_ID
adore --profile nilo runs
```

A live conductor keeps its lock and completes the current bounded executor
session. The command returns `queued`; do not edit the worktree yet. At the safe
boundary, ADORE saves `handoff-pending`, stops the container, attempts a final
local commit and guarded remote push, and then saves `handed-off`. Stop failure
leaves transfer pending and never announces that editing is safe. Interrupted
pending transfers resume before another executor can launch.

`handed-off` means the conductor has finished Git mutations and automatic
execution is disabled. Notification failure retains this ownership and replays
through the outbox. Worktree, state and container evidence remain preserved.
`retry` and `reset` refuse human-owned or pending transfers; cleanup protects them.
Explicit `cancel` or `delete --force` releases resources and can destroy this work.

Read `AGENTS.md`, the full AEGIS task journal, Stage report and Handoff before
continuing. If the remote checkpoint is current, another developer can fetch:

```bash
git fetch origin
git switch --track origin/adore/pi-26
```

If committing or pushing failed, use the recorded local worktree. Git bundles
carry committed history only; uncommitted changes and untracked files require
separate preservation. The handoff notice identifies these recovery limitations.
Automatic hand-back to ADORE is intentionally unsupported; assign future work
explicitly. A handoff creates no PR and grants no delivery approval.
