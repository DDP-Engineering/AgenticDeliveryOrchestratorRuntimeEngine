<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Orchestrator

## Purpose and ownership

`04_Software/adore/orchestrator.py` conducts selected forge tickets through an
agent-driven workflow, bounded recovery and configured review publication.
The conductor owns ticket selection, lifecycle, budgets, checkpoints, approval,
publication and cleanup. The executor owns code reasoning and repository checks.
ADORE never merges. Host Git/forge credentials stay outside executor environments.

`requested_workflow` resolves the project auto/direct default and optional manual
aegis/direct override before admission probes. Direct skips payload inspection and
AEGIS entirely; explicit AEGIS refuses absence, while auto detects presence and
refuses an unusable installed payload. The actual workflow is pinned from the allocated worktree before
the initial claim save and does not change on Retry, resume or review revision.

## Workflow and durable state

Lifecycle is separate from stage: working, parked-clarification,
awaiting-approval, publishing, in-review, failed, done, cancelled,
handoff-pending and handed-off. AEGIS follows the selected full or quick path;
Direct uses build, conductor-owned validate and done, with no AEGIS task IDs.
The publishing reset pointer is not an executor stage.

Each launch restarts a bounded Pi process in the job's exact private conversation.
AEGIS journals and ADORE state remain authoritative for workflow progression;
Pi retains implementation context across stages, partial work and corrections.
The first prompt includes the ticket. Later prompts omit unchanged ticket content
and historical Log replay; changed ticket content is resent until acknowledged.
Existing independent AEGIS reviews retain separate contexts.
The conductor reads validated AEGIS task progression but does not edit journals.
Direct uses retained implementation-completion evidence instead of a journal.
See [State store](Component_State_Store.md),
[AEGIS client](Component_Aegis_Client.md) and
[Executor launcher](Component_Executor_Launcher.md).

Every job has a closed pinned execution plan, including containers with no
preparation recipe. Provision records exact resource identity before binding
commands. Preparation and optional system-package authority are explicit;
ordinary Retry cannot silently change a plan or repeat partial setup.
See [Preparation](Component_Preparation.md) and
[Execution](Component_Execution.md).

## Azure DevOps Services

Azure Services uses this same conductor, passing explicit platform scope to the
forge factory. Before entering review, creation/adoption/retry invokes the
idempotent `Forge.link_ticket` hook; failure preserves publication retry rather
than reporting in-review without the source association. Other adapters keep
the default no-op. Approval, polling, replay, review rounds and human-merge Git
cleanup are unchanged. See [Azure DevOps component](Component_Azure_DevOps.md).

## Admission and concurrency

Shared selection requires an open eligible ticket, ready labels, no hold/exclude,
no conflicting existing run and the configured priority/readiness criteria.
Automatic polling respects pickup pause. Manual Start requests one eligible
ticket even while automatic pickup is paused; it does not bypass other rules.

Selection/probes occur outside the short admission transaction. The selected run
lock plus admission lock recheck identity, uniqueness, pause and capacity and
reserve an execution-slot kernel lock. No Git, forge or executor call holds the
short admission lock. Allocation then pins the worktree/workflow and saves state,
ticket and picked evidence before Start acknowledgement or forge claim effects.

`poll_once(..., admit_only=True)` records a queued dispatch without reconciling
other runs. `conduct_run` validates the exact configuration revision and current
dispatch record, consumes initial authority once and starts the active clock
before execution effects. A queued job's `execution_pending` keeps active time
at zero; uncertain started dispatch requires explicit recovery.

Capacity includes active reservations, handoff-pending, unsettled parked cleanup
and held execution-slot locks, including initialization/Restart boundaries before
state exists. Settled human waits consume no executor slot. Retry, clarification,
review revision and approval invalidation reserve capacity before execution.
A lower configured or valid reviewed pending ceiling blocks new reservations
without cancelling active jobs. Staged increases do not grant capacity.

Each production conductor has its own configuration, backend, executor, secrets,
IO and diagnostics. Run lifecycle scopes also acquire durable worker ownership
when worker-bound. Child identity and heartbeat, command/project authority and
run-owner generation fence writes and external effects. Foreign live or uncertain
owners are preserved before cancellation, stale handling or outbox replay.
See [Resource locks](Component_Resource_Locks.md),
[Worker processes](Component_Worker_Processes.md) and
[Project capacity](Component_Project_Capacity.md).

## Stage execution, evidence and checkpoints

Prompts are composed from the fixed licensed catalog, ticket context, bounded
recovery context and authorized human instructions. AEGIS prompts ask the agent
to finish its stage through AEGIS. Direct asks the agent to implement and select
appropriate repository checks. Neither workflow delegates publication or merging
to Pi. See [Prompts](Component_Prompts.md).

The conductor launches one bounded attempt in the same conversation, records normalized operational
diagnostics, session archives and telemetry availability, then interprets questions,
exit/authoritative timeout, stage progress and integrity checks. Questions park the
job without consuming stage failures. A stage checkpoint uses the configured agent
Git identity even when the host clone has no global identity. Its failure stops
execution at the observed stage and preserves the worktree.

Progress checkpoint publication is independently configurable. It is lease-bound
to the owned ticket branch and never opens a review by itself. Foreign/replaced
refs refuse publication; target branches are never progress-pushed.

Direct success requires product changes and no blocking questions. The conductor
retains a sanitized summary and completed implementation marker, checkpoints and
integrates the target, then binds clean candidate/target evidence. A durable
completion marker can finish recovery without repeating a successful launch.
AEGIS completion records the agent's done journal, task identity, deviations and
bounded log evidence against the clean candidate/target.

ADORE runs no independent repository verification command and does not rerun an
AEGIS strict suite after agent completion. Agent-selected checks and recorded
workflow completion supply the evidence. Candidate/target drift invalidates
publication authority and routes back through fresh workflow-appropriate work.

## Approval, publication and review

When human approval is required, presentation records the exact candidate and
requires a fresh approval-label transition. When disabled, complete workflow
evidence and current candidate/target freshness are still mandatory. Publication
uses host credentials to push the validated candidate and open/update the
configured draft or ready MR/PR. It adopts a matching existing open review before
creating one. No Pi session or AEGIS stage runs during publication.

Human revision labels and configured failed-pipeline revision share the bounded
review-round budget. A human request wins if both occur. AEGIS creates a fresh
task before consuming the label; Direct revises without a task. Every round
returns through completion evidence and the project approval policy. Exhausted
review rounds remain in review with an explicit notification.

Human merge is observed before source-ticket closure. It finishes the job;
configured source-branch deletion uses the last published commit lease and verified
review/branch ownership. Unverified deletion retains the branch/worktree with a
warning. A closed unmerged review keeps its remote branch. Closing the ticket
while waiting otherwise cancels through the normal lifecycle boundary.

## Recovery, cancellation and handoff

Stage failures are bounded independently of transient infrastructure retries.
Accepted stage progress resets the current stage-failure count. Retry preserves
consumed work/history; active work, launches, cost and file budgets remain
cumulative across human waits and revisions. Waiting time is excluded. Current
operational limits are reread at their defined boundaries without changing the
pinned execution identity.

Timeout classification uses the runner's authoritative flag, not stderr wording
or exit 124 alone. Failed identity/timeout recovery blocks further execution.
A stale working owner becomes an explicit failure only after exclusive ownership
is proven. Interrupted publication becomes STALE_PUBLISHING and never causes
automatic duplicate publication or failed-checkpoint pushing.

Mandatory notifications are durable before forge transport. Undelivered comments
block further code work and are replayed within bounded recovery. Terminal status
notification failure does not replace the saved terminal lifecycle/outcome.

Cancellation is a request until the owned conductor handles it and confirms
teardown. Bounded interruption and final resource settlement precede release.
Human handoff is durable before stopping/writing Git; handed-off work remains
protected. Handoff takes precedence over concurrent cancellation at a boundary.
Instruction acknowledgement/outbox replay uses the same run locks and ownership;
see [Instructions](Component_Instructions.md).

Cleanup verifies current lifecycle and exact project/run/path/resource ownership.
Active, failed, corrupt, foreign, stateless-unproven and human-owned resources are
protected. Explicit Cancel/Delete/Restart owns destructive release; Restart
revalidates the confirmation's state revision and preserves unproven remote refs.
Shared caches/images are retained. A refused cleanup after human merge keeps done
with retained-resource evidence rather than claiming removal.
See [Isolation](Component_Isolation.md) and
[Clone cleanup](Component_Clone_Cleanup.md).

## Validation coverage and limits

Existing offline coverage includes `04_Software/tests/test_orchestrator.py`,
`test_run_concurrency.py`, `test_preparation_lifecycle.py`, `test_retry_revalidation.py`,
`test_drift_recovery.py`, `test_web_ownership.py` and `test_shared_resources.py`.
External commands are injected. Specialized components document their trust-boundary
coverage. No deployment/setup tests are required by this component.

External forge/Git effects and local saves are not one transaction. Durable
checkpoints, outbox and ownership evidence bound recovery; uncertain effects need
explicit operator attention. Stored formats have one current schema and are never
converted or automatically recreated.
