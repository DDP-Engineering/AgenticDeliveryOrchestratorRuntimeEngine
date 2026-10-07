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

Questions do not count. Temporary container, fetch or forge transport failures
use the independent transient counter.

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
then removes the selected project's orphaned executor/proxy containers,
egress networks and worktree directories: those of its done, cancelled and
stale runs and of its run IDs (`<platform>-<repo>-<ticket>`) that have no
state. Other projects on the host keep their resources even when they share
the slug, egress network prefix or worktree root, and a proxy or network that
any other existing executor container still uses stays. A proxy or network
whose run has no state, worktree or executor container left stays too. Remove
such leftovers, and those of a project that no longer has a profile, by hand
after checking their owner. Active, failed
and human-owned runs are protected: a failed run's container
companions, worktree and evidence remain available for `retry`. Release those
resources explicitly with `cancel <run-id>` while retaining audit state, or
with irreversible `delete <run-id> --force` after separately preserving any
required evidence. A live, different-host, unreadable, or otherwise unknown
lock remains present and is reported as `lock_held_by`; never remove it until
ownership is verified. Cleanup reports corrupt runs and keeps their state,
worktree and containers.

In `allowlist-proxy` egress mode every run has its own proxy container and
egress network. A name that would exceed the runtime length limit keeps its
start and ends in a short digest of the full executor name. Releases before
per-run names cut long names instead, so long-named runs could share a proxy.
Before upgrading from such a release, finish or cancel parked
`allowlist-proxy` runs whose executor container name is longer than 48
characters, or remove their executor container so the next pass provisions it
again; a restarted old executor stays on its old network without a reachable
proxy. `cleanup` later removes the old proxies and networks once no existing
executor uses them.

Stop the service poller before `retry`, `cancel`, `delete`, or `reset`; these
commands acquire the same single-conductor lock and refuse a live/unknown
holder. `pause` prevents new pickup but does not stop the poller or release its
lock. `logs` is read-only and remains available during conduction.

## Container preparation

Recipe preparation failure/interruption is durable and never implicitly replayed. Inspect `execution-plan.json`, `state.json` execution fields, and `preparation/attempt-N/step-M.json`; ordinary retry retains the failure. `retry <run-id> --reprepare` explicitly acknowledges full replay in a fresh owned container with retained partial worktree effects. IDs, image, policy and immutable evidence must match on normal resume. See [Container preparation](Container_Preparation.md).

## Native local execution

Native recovery requires pinned backend/account/environment and intact runtime/lease/launch identity. Reused PIDs, drift, corruption or unconfirmed descendants refuse cleanup and preserve worktrees. Container profiles protect persisted native runs; restore the pinned profile.

See [Local execution](Local_Execution.md) for platform prerequisites, configuration,
authentication, process ownership and acceptance coverage.
