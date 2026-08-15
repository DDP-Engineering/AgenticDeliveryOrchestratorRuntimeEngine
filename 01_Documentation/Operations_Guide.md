<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Operations Guide

## Runtime States

| State | Meaning | Next action |
| --- | --- | --- |
| `working` | A fresh stage attempt may run. | Advance, park, or fail within budgets. |
| `parked-clarification` | A human answer is required. | Comment plus `agent-answered`, or timeout. |
| `awaiting-approval` | Validated candidate is presented. | Freshly add the approval label, or candidate/target drift invalidates it. |
| `publishing` | Approved delivery bookkeeping and remote publication. | Reach draft MR/PR or fail loudly. |
| `in-review` | Draft MR/PR awaits human action. | Merge, close, or request a bounded revision. |
| `failed` | Execution stopped with preserved evidence. | Fix cause, clear pending notification, then explicit retry. |
| `done` | A human merged the draft. | Cleanup is complete/auditable. |
| `cancelled` | An operator or closed source ticket ended the run. | Audit state remains; delete explicitly if no longer needed. |

AEGIS stage is recorded separately as `frame`, `specify`, `design`, `build`,
`validate`, `deliver`, or `done`. Quick tasks omit specify/design.
If the source ticket is closed while a run is parked for clarification,
awaiting approval, or still has an open MR/PR in review, the next poll cancels
it with outcome `ticket closed` and releases its resources. A merged MR/PR takes
precedence even when the source ticket has also closed; a closed-unmerged MR/PR
retains the `MR_CLOSED` outcome.

`awaiting-approval` and `in-review` have no timers by design. These are
human-paced states: after closed/deleted-ticket reconciliation, an open ticket
may wait indefinitely for approval or review action without generating a
reminder or timeout.

## Normal Operator Loop

```text
adore --profile <name> status
adore --profile <name> run --dry-run
adore --profile <name> run --once
adore --profile <name> runs
adore --profile <name> logs <run-id>
```

Continuous service mode uses `run --loop`. Every executor launch, transition,
failure, question, notification delivery, approval and publication event is
appended to `journal.jsonl` under the profile state root.

## Failure Interpretation

| Signal | Meaning | Operator response |
| --- | --- | --- |
| Incident attempt `1/3` or `2/3` | Recoverable stage attempt failed. | Observe the fresh remediation attempt; intervene if evidence shows a policy/resource issue. |
| Incident attempt `3/3` plus terminal comment | Stage limit reached. | Inspect local/MR evidence and explicitly retry only after correcting the cause. |
| `AEGIS_PROTOCOL` | Wrong version/schema, malformed CLI output, identity/path violation. | Repair the target payload/journal; do not repeatedly launch an executor. |
| `AEGIS_TIMEOUT` / `EXECUTOR_TIMEOUT` | The bounded command runner reports that it killed an AEGIS or executor process. | Inspect resource pressure and the configured bound; stderr wording and exit code alone do not produce this classification. |
| `NOTIFICATION_DELIVERY` | Required ticket/MR write failed. | Restore forge transport. Polling replays the outbox without an execution slot. |
| `BUDGET_EXHAUSTED` | Iteration/time/cost/file cap reached. | Adjust scope/config deliberately, then retry. |
| `STALE_WORKING` | A conductor died or lost ownership. | Inspect evidence, reconcile the worktree, then retry. |
| `CLARIFICATION_TIMEOUT` / `REVIEW_LIMIT` | Human/review bound exhausted. | Decide manually; retry only with a new explicit intent. |

Evidence is sanitized before comments. Local JSONL remains the durable audit
record. ADORE treats required problem notification as part of correctness, not
best-effort telemetry.

## Approval Operations

The approval presentation lists strict evidence, warnings, commands, diff
size, exact commits, candidate fingerprint and target commit. Do not pre-apply
`agent-approved`; ADORE removes and verifies it absent before presentation.

After reviewing the presentation, add `agent-approved`. The next poll fetches
the target and recomputes the fingerprint. Drift removes the label and returns
the run to integration/validation. Approval is never reused for a revision.
Retrying interrupted publication rechecks the label and candidate before any
push. A missing approval returns to normal validation/presentation. Ticket
title/body edits are separately recorded as `ticket content changed since
pickup` and refresh the local snapshot; they are visibility, not automatic
candidate invalidation.

## Review Operations

ADORE opens only a draft. Apply `agent-revise` to the MR/PR to request a
governed revision. The next poll creates a new AEGIS task on the same branch,
preserves earlier journals, and repeats the path. The configured review-round
limit ends visibly on both active surfaces.

The revise label is removed only after provisioning, payload probing, and task
creation succeed. Failures before that point leave the request visible for a
later retry. A crash in the narrow create/remove/state-save boundary can leave
a duplicate or orphan AEGIS task because AEGIS has no idempotency key; inspect
the `revision-task-created` journal event before manual recovery.

During publication ADORE first adopts an existing open MR/PR for the task
branch, avoiding duplicate creation after a crash or failed read-back. Recovery
from an already-done task still checkpoints and pushes close-out changes before
entering `in-review`.

ADORE has no merge operation. The human review/merge path remains protected by
forge permissions and branch rules.

## Notification Outbox

An outbox record is stored before every required problem/approval comment. A
failed transport stops code work. Polling retries due records using capped
backoff without provisioning a container. If a draft MR/PR is confirmed
deleted, delivery falls back to the source ticket. If the source ticket is also
deleted, the notification is marked undeliverable in the audit log.

`adore retry` refuses a run while its outbox is nonempty.
If only the final status write of an already terminal run fails, the replay is
queued without changing its terminal lifecycle or outcome.

## Stopping and Cleanup

`cancel` removes active resources and retains audit state. Failed runs keep
their worktree, container companions, and local evidence for explicit retry;
routine `cleanup` protects them along with active valid runs. To release a
failed run, use `cancel <run-id>` (keep audit state) or `delete <run-id>
--force` (irreversible state removal). Cleanup sweeps orphan executor/proxy
containers, egress networks, and worktree husks, and reports corrupt state
without deleting it. It reclaims only a provably stale local lock; a
live/unknown holder is reported and left in place. Stop the service poller
before retry/cancel/reset/delete because those mutations use the same
single-conductor lock.
