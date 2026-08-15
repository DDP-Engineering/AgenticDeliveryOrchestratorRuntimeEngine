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

AEGIS stage is recorded separately as `frame`, `specify`, `design`, `build`,
`validate`, `deliver`, or `done`. Quick tasks omit specify/design.

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

## Review Operations

ADORE opens only a draft. Apply `agent-revise` to the MR/PR to request a
governed revision. The next poll creates a new AEGIS task on the same branch,
preserves earlier journals, and repeats the path. The configured review-round
limit ends visibly on both active surfaces.

ADORE has no merge operation. The human review/merge path remains protected by
forge permissions and branch rules.

## Notification Outbox

An outbox record is stored before every required problem/approval comment. A
failed transport stops code work. Polling retries due records using capped
backoff without provisioning a container. If a draft MR/PR is confirmed
deleted, delivery falls back to the source ticket. If the source ticket is also
deleted, the notification is marked undeliverable in the audit log.

`adore retry` refuses a run while its outbox is nonempty.

## Stopping and Cleanup

`cancel` removes active resources and retains audit state. Failed runs keep the
worktree by design. `cleanup` removes only containers/worktrees not owned by an
active valid run and reports corrupt state without deleting it. `delete
--force` is the explicit irreversible state removal command.
