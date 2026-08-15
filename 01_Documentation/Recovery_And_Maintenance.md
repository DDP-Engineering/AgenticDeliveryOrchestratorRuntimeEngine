<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Recovery and Maintenance

## Recovery Invariants

- ADORE 0.5 reads only state schema 4. It never migrates ADORE 3.x state.
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
already failed the run, answer first and then explicitly retry.

## Review Recovery

Apply `agent-revise` only when a bounded review round should begin. Every round
creates a new task journal. If the review limit fails the run, a human must
decide whether to raise the configured limit and retry or continue manually.

## State Surgery and Cleanup

`reset --to <stage> --force` changes ADORE state only. The active AEGIS journal
remains executor-owned and will be reread; therefore reset cannot falsify a
journal transition. Use it only after understanding the mismatch, then run
`retry`.

`cleanup` clears a stale lock and removes orphan resources. It reports corrupt
state and never auto-deletes it. `delete --force` is irreversible and should be
used only after separately preserving required evidence.
