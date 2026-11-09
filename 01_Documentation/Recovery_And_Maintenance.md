<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Recovery and Maintenance

## Recovery Invariants

- ADORE reads only run-state schema 1. It migrates no earlier state shape: a
  `state.json` with unknown or missing keys or an unknown stage is refused, and
  the message names the run directory to delete.
- AEGIS task journals, not executor sessions, decide resume stage/path.
- Failed runs stop their container, release capacity, preserve worktree/state,
  and require explicit `adore retry`.
- Retry resets the active stage counter, but preserves cumulative active-work time,
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
removed, ADORE returns to validation/presentation instead of publishing. Work
left in the worktree is committed before the freshness check, so it changes
the candidate fingerprint and invalidates the approval instead of failing the
retry; the candidate is then validated again.

## When Retry Cannot Help

`adore retry` re-runs the same decision against the same durable state. One
failure is therefore immune to it: `FORBIDDEN_STAGE_TRANSITION`, raised when the
journal skips forward and the stages in between carry no Log entry of their
own. Backward routes within the selected path continue automatically. Retrying replays the
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

A checkpoint also stops when a newly added path contains a whole literal
`%NAME%` segment or the Windows `ProgramData/Microsoft/Windows/Caches` path.
The error identifies the path. Inspect the preserved worktree and staged changes,
then remove or relocate unintended files before Retry. Git-ignored files and
modifications to already tracked files retain their usual Git behavior. An
invalid Git response also stops the checkpoint; resolve the Git error first.

A failed stage checkpoint reports `CHECKPOINT_FAILED` at the stage recorded by
AEGIS and keeps the worktree. Correct the Git failure before Retry. Existing
failed jobs remain failed until an explicit Retry; updating the application does
not restart them. `STALE_WORKING` means a working run has lost its conductor,
not that AEGIS returned to an earlier stage.

## Stage-Failure Accounting

With the default threshold of three, the third failed attempt aborts. One
executor nonzero/timeout, no-progress outcome, repairable journal failure,
strict-check invocation, or unresolved conflict is one attempt regardless of
the number of findings it contains.

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
the existing open branch MR/PR. The AEGIS task closed in validate, so a retry
after a failed push or MR/PR creation publishes the same approved candidate. A
run that fails after its candidate reached review returns to review on retry,
with no new validation or approval; after `reset --to publishing` without a
fresh approval, retry conducts the run from the closed task.

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

With internet access for the agent Off (`[executor] internet = false`, the
default) every container run has its own proxy container,
`<executor container>-egress-proxy`, and egress network,
`<egress network prefix>-<executor container>`. A name that would exceed the
runtime length limit keeps its start and ends in a short digest of the full
executor name. `cleanup` recognises only these names; see
[Egress Leftovers of Earlier Builds](#egress-leftovers-of-earlier-builds).

Stop the service poller before `retry`, `cancel`, `delete`, or `reset`; these
commands acquire the same single-conductor lock and refuse a live/unknown
holder. `pause` prevents new pickup but does not stop the poller or release its
lock. `logs` is read-only and remains available during conduction.

## Egress Leftovers of Earlier Builds

An earlier ADORE build named the proxy container and egress network of a
long-named executor by cutting the name at the runtime length limit, instead of
ending it in a digest. `cleanup` does not recognise those old cut names, so
remove such leftovers by hand with the container runtime CLI. The commands below use Docker; with
Podman, run the same commands with `podman`.

1. List the project's containers, proxies included, and the egress networks:

   ```text
   docker ps -a --filter name=<slug>-run-
   docker network ls --filter name=<egress network prefix>
   ```

   The egress network prefix is `container.egress.network_prefix`, by default
   `adore-egress`.

2. Check that no current run uses them: a name must not belong to the executor
   container of an active, failed or human-owned run, or to that container's
   proxy or network. `docker ps -a --filter network=<name>` lists the
   containers attached to a network.

3. Remove the containers first, then the networks:

   ```text
   docker rm -f <name>
   docker network rm <name>
   ```

## Container preparation

Recipe preparation failure/interruption is durable and never implicitly replayed. Inspect `execution-plan.json`, `state.json` execution fields, and `preparation/attempt-N/step-M.json`; ordinary retry retains the failure. `retry <run-id> --reprepare` explicitly acknowledges full replay in a fresh owned container with retained partial worktree effects. IDs, image, policy and immutable evidence must match on normal resume. See [Container preparation](Container_Preparation.md).

## Native local execution

Native recovery requires pinned backend/account/environment and intact runtime/lease/launch identity. Reused PIDs, drift, corruption or unconfirmed descendants refuse cleanup and preserve worktrees. Container profiles protect persisted native runs; restore the pinned profile.

See [Local execution](Local_Execution.md) for platform prerequisites, configuration,
authentication, process ownership and acceptance coverage.

## Retrying after an installed executor update

For a failed local job, use Retry in Jobs or `adore --profile <name> retry <run-id>`.
Explicit Retry accepts changes to the inherited environment and installed executor
on the same host/account, checks the executor version and resumes the saved AEGIS
task in its existing worktree. The job's branch, history and cumulative budgets are
kept. Automatic monitoring does not authorize this refresh. Changed execution
settings, another host/account or corrupt recovery evidence require correction.
If rearming fails, the command exits with an error and Jobs shows the saved cause,
including an unavailable executable, invalid version, command exit or timeout.
This rule applies to all supported native executors and projects, with no special
case for a ticket or forge. It does not issue a model request; Test AI connection
remains the explicit provider/model check.

## Abandon and start again after settings drift

In **Jobs**, open a failed job and choose **Abandon and start again**. Confirm only after reviewing the warning: this discards the old job state, worktree (including unpublished work) and its unchanged owned remote branch. ADORE verifies ownership, drains owned processes and deletes the remote branch using its last recorded commit as an exact lease before starting the same ticket with current settings. Monitoring stays paused if already paused. Another host/account, corrupt receipt, changed remote branch or incomplete cleanup blocks the restart and preserves remaining evidence. A job that changes after confirmation must be refreshed and reviewed again.

Stable execution settings or backend drift cannot be repaired by Retry. Restore the saved settings or use confirmed abandonment. Explicit native Retry can revalidate volatile environment and executable identity, including `NUMBER_OF_PROCESSORS` and `PROCESSOR_*` after resizing a VM; it keeps existing work and limits.

CLI: `adore --profile <name> delete <run-id> --force` reports a clean error on drift. For a stopped failed/cancelled job, `--owned-resources` explicitly uses the saved native receipt instead of current environment/executable identity; host/account, dedicated paths and process ownership are still verified. It never deletes foreign resources or overrides a remote lease. If the web worker owns the lock, use **Project Summary -> Pause monitoring** and wait for the current bounded job; a standalone CLI loop must also be stopped. Do not remove a live lock file.

A successful fresh start clears the discarded job's terminal summary and web usage projection so its new journal begins with fresh statistics. Cleanup errors retain remaining evidence. Container cleanup uses the actual owned proxy/network identities even when current execution or internet settings changed; a foreign member or unproven leftover network is retained for operator inspection.

If a previously deleted job left a branch with no recorded ownership checkpoint, confirmed restart preserves that ref and selects an empty branch generation. It checks the base and at most three alternatives against local/remote availability and the repository naming rule. If no valid name is available, it stops before cleanup. A changed known checkpoint is never bypassed. The success message explains a retained older branch. Initial local refs are created atomically, and unowned existing worktree paths are refused.
