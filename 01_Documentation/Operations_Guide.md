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
| `handoff-pending` | Ownership transfer is unfinished; local editing waits. | Finish the current bounded session and verify stop/checkpoint work. |
| `handed-off` | A human owns the preserved worktree and branch. | Human continues; automatic retry/reset/cleanup preserve ownership. |
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

## Stage Completion and Continuation

Each fresh executor session is instructed to complete its current AEGIS stage.
The durable task journal determines whether that stage advanced or legally
routed backward. An executor may leave the stage unfinished after useful work;
ADORE observes both the candidate and the work Log before deciding what follows.

A successful gate that leaves the same stage continues automatically when:

- authored candidate content changed during the session; task journals and
  generated caches are excluded from this observation;
- the task Log retains its existing entries and appends nonempty work evidence.

ADORE creates a local checkpoint, publishes it when `delivery.publish_checkpoints`
is enabled, and records `stage-continuation` in
`journal.jsonl`. It starts a fresh session with the recent work evidence and
instructions to read the journal, Handoff and Stage report and finish the
remaining work. The run remains `working` at the same stage. No operator action
is needed for an evidenced continuation.

Continuation preserves the stage failure count. Every launch still consumes
`max_iterations`, active-work time and reported cost, and the file budget remains
in force. A legal stage transition resets the failure count. Strict validation
and fresh human approval still precede publication.

## Failure Interpretation

| Signal | Meaning | Operator response |
| --- | --- | --- |
| Incident attempt `1/3` or `2/3` | Recoverable stage attempt failed. | Observe the fresh remediation attempt; intervene if evidence shows a policy/resource issue. |
| Incident attempt `3/3` plus terminal comment | Stage limit reached. | Inspect local/MR evidence and explicitly retry only after correcting the cause. |
| `stage-continuation` journal event | Candidate changes and appended work evidence justify another session at the same stage. | Observe the fresh session; an unchanged stage alone is expected here. |
| `NO_STAGE_PROGRESS` | A successful same-stage gate lacks candidate changes or a nonempty append-only work Log. | Read the task Log, Handoff and candidate diff; the configured stage recovery limit applies. |
| `WORKTREE_PROGRESS` | Git or file reads could not produce a trustworthy progress observation. | Restore worktree access and inspect Git/path errors before retrying. |
| `AEGIS_PROTOCOL` | Wrong version/schema, malformed CLI output, identity/path violation. | Repair the target payload/journal; do not repeatedly launch an executor. |
| `AEGIS_TIMEOUT` / `EXECUTOR_TIMEOUT` | The bounded command runner reports that it killed an AEGIS or executor process. | Inspect resource pressure and the configured bound; stderr wording and exit code alone do not produce this classification. |
| `NOTIFICATION_DELIVERY` | Required ticket/MR write failed. | Restore forge transport. Polling replays the outbox without an execution slot. |
| `BUDGET_EXHAUSTED` | Iteration/time/enabled cost/file cap reached. | Inspect the specific cap; subscription/local profiles may set `max_cost_usd = 0` to disable dollar enforcement, then retry. |
| `STALE_WORKING` | A conductor died or lost ownership. | Inspect evidence, reconcile the worktree, then retry. |
| `CLARIFICATION_TIMEOUT` / `REVIEW_LIMIT` | Human/review bound exhausted. | Decide manually; retry only with a new explicit intent. |

Evidence is sanitized before comments. Local JSONL remains the durable audit
record. ADORE treats required problem notification as part of correctness, not
best-effort telemetry.

## Approval Operations

The approval presentation leads with the deviations the AEGIS journal
recorded, as a count and in full, then lists strict evidence, warnings,
commands, diff size, exact commits, candidate fingerprint and target commit.
Deviations inform the approver; they never block. Do not pre-apply
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

On GitLab the revision thread comes from the MR notes endpoint, which already
includes diff notes. On GitHub and Gitea ADORE additionally reads the submitted
reviews and their inline comments, so feedback left through "Review changes"
reaches the executor and not only conversation-tab comments.

### Pipeline failures

While a run is `in-review`, each poll reads the forge pipeline verdict for the
draft and normalizes it to `success`, `failed`, `running`, `none` or `unknown`.
Only a *change* in that verdict is a signal, so a run that waits days is neither
nagged nor repaired twice for one failure. `[review] on_pipeline_failure`
decides what a new `failed` verdict does:

| Mode | Behavior |
| --- | --- |
| `revise` (default) | Start a governed repair round automatically. |
| `notify` | Post one comment on the draft and wait for a human. |
| `ignore` | Skip the pipeline read entirely. |

A repair round is the same bounded path the revise label uses: a new AEGIS task
on the same branch, the prior journals preserved, and the executor told that a
green pipeline is part of this round's acceptance criteria. It therefore ends
where every other round ends, at strict validation and a **fresh human approval**
before delivery publication. ADORE still never merges.

`max_review_rounds` bounds repairs and human-requested revisions together, so a
permanently red pipeline cannot loop. When the budget is spent, ADORE posts a
comment saying so and leaves the run in review rather than failing it.

A pipeline that is unreadable, or a `gh` too old to report check status, reads
as `unknown` and is silent. It never blocks the poll and never triggers a
repair.

ADORE also verifies `check --strict --run` inside the container, which covers
only the commands the target repository configures for AEGIS. Keep those aligned
with the pipeline if you want local validation to predict the pipeline result
and avoid spending repair rounds on failures the container could have caught.

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
