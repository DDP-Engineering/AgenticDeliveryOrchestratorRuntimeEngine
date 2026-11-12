<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Orchestrator Component

Shared ticket eligibility excludes the configured epic type label from automatic pickup and manual admission; eligible manual Start remains available with monitoring paused.

## 1. Purpose

`adore/orchestrator.py` is the deterministic ADORE conductor around the
agent-driven AEGIS and direct workflows. It prevents silent stalls and keeps
review publication human-approved with configurable draft or ready state.
An absent payload selects direct; a present unusable payload is never bypassed.


After observing a human merge, the shared CLI/web conductor honors `delivery.remove_source_branch` on GitHub, GitLab and Gitea. It checks review/run-branch ownership and performs bounded host-Git deletion with the last published commit lease. Every approved publication pins that commit even when progress commits are disabled. An absent branch succeeds; an unverified deletion leaves the job done with a branch-retained warning and keeps its local worktree for remediation. Closed unmerged reviews keep their remote branch.

## 2. Responsibilities

- select/claim forge tickets with the shared `adore.selection.ineligibility`
  rules (open, ready label, no hold/exclude, no existing run, priority and
  acceptance-criteria readiness) and provision worktree/container isolation;
- allocate the pinned worktree before the first claim save, recording immutable
  `workflow` from its payload presence; resolve preparation authority in memory
  first, but execute preparation only after durable claim;
- create and bind active/historical tasks only for AEGIS runs;
- load every application-owned agent fragment eagerly through `PromptCatalog`
  at construction; `from_config` shares that one catalog with the Pi launcher;
- dispatch after provisioning to the AEGIS stage loop or `_conduct_direct`,
  without a shared workflow interface;
- launch fresh executor sessions through the same `_launch_stage` supervision,
  backend, egress, credential isolation, budgets and timeouts;
- journal a versioned telemetry observation for every executor launch, including
  unavailable and administrator-disabled capture; keep the existing numeric
  `usage` event only when capture produced values, linked to the observation
  by the run/attempt event ID; an explicit complete zero-token report remains
  `reported`, while partial or absent token evidence is `unavailable`;
- compose each stage prompt as an explicit autopilot instruction that has the
  executor record `interaction: autopilot` in the journal, finish the stage
  with `advance`, record unfinished work with `log` and `pause` (`pause
  --blocked` for questions), and forbids commit, push, MR/PR creation, merge,
  and child task journals; a continuation names `brief` and the journal State;
- validate full/quick progression to done, accept returns to earlier stages
  on the selected path and the governed done-to-validate route; persist the
  accepted stage before checkpoint work so Jobs shows the authoritative stage;
- create an unpushed local checkpoint commit after every successful stage,
  using the configured agent identity even when the host clone has no
  repository or global Git identity;
- publish owned ticket-branch progress checkpoints by default (explicit false
  keeps them local) under a remote
  lease, and stop on foreign branch ownership without weakening approval;
- reconcile an unpublished failed-run checkpoint once, leaving already verified
  failed-run state and its historical update time unchanged on later polls;
- transfer a run to a human at an operator-requested boundary, preserving its
  worktree and remote/local recovery evidence;
- distinguish clarification, stage failures, transient infrastructure failures
  and immediate integrity/policy/budget failures;
- persist and deliver mandatory incident/terminal/approval notifications; a
  `NO_STAGE_PROGRESS` incident appends the gate's last stderr lines (`_stderr_tail`:
  NUL and ANSI escapes removed, an unterminated OSC/DCS string ending at its line,
  and credentials redacted on the whole stderr, then the last 20 lines within 2000
  characters), and a terminal failure's `run.outcome` keeps the evidence's first
  line when it bounds long evidence (`_head_and_tail` on the unbounded redacted
  evidence, so the 6000-character evidence cut cannot drop it);
- integrate the target, run independent strict verification and fingerprint the
  candidate/target/commit series;
- require a fresh approval-label transition after presentation;
- push the approved candidate once and open or update the configured draft or
  ready MR/PR, with no executor session and no AEGIS command after approval;
- adopt an existing open branch MR/PR before attempting draft creation;
- create a new AEGIS task for governed revisions or restart direct build without
  a task before consuming each bounded review request;
- reconcile parked, approval, review, stale-working and outbox states;
- garbage-collect only this project's resources: those of done, cancelled,
  stale and state-less runs of its run-ID form, including allowlist proxy
  containers and egress networks, while active, failed, human-owned and corrupt
  runs, other projects' resources, and any proxy or network another existing
  executor still uses stay; without the executor listing no proxy or network
  is removed.

The component never edits AEGIS journals, gives forge credentials to an
executor, or merges.

Stage, recovery and review text comes from the licensed Markdown files under
`adore/prompts/`; `_stage_prompt` and its callers still own all conditional
selection, ordering, sanitization and joins. `description.strip()`, `_sanitize`,
`author: body` thread rendering and existing whitespace remain unchanged.
Construction refuses missing/unreadable or malformed resources with a file-named
`PromptError`; missing render values also fail closed. The leading legal comment
never reaches Pi. There is no alternate-path setting or render-time file read.
See [Prompts](Component_Prompts.md) for the resource/template contract and the
pre-extraction byte-oracle tests in `tests/test_prompts.py`.

## 3. State Machine

Lifecycle states are `working`, `parked-clarification`, `awaiting-approval`,
`publishing`, `in-review`, `failed`, `done`, `cancelled`, `handoff-pending`,
and `handed-off`. Workflow stage is tracked separately. AEGIS uses the
full/quick stage set; direct uses `build`, conductor-owned `validate`, then
`done`, with no active/historical task ids. The shared `publishing` reset pointer
is not an executor stage. Reset refuses AEGIS-only stages for direct runs.

`handoff-pending` is durable before stopping the container or writing Git.
`handed-off` disables further autonomous work, while cleanup protects the
human-owned worktree. When handoff and web cancellation are both pending at a
boundary, handoff takes precedence. Checkpoint publication never creates a
draft MR/PR; candidate-bound approval still gates that step.

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
failure posts a terminal comment, requests the selected backend to stop and preserves the
worktree. Routine cleanup works only on this project's run IDs (runs in its
state store, corrupt run directories, and worktree directories or executor
containers named in its `<platform>-<repo>-<ticket>` form) and protects failed
worktrees, container companions and evidence until explicit retry, cancel or
delete. `purge_resources()` serves
project deletion: it releases only the containers and worktrees recorded for
this project's own runs, keeps human-owned (handed-off and handoff-pending)
runs' resources and reports their worktrees as retained, and never sweeps by
name prefix or worktree root, which other projects may share. Multiple AEGIS findings in
one invocation count once. An accepted
stage transition resets the counter. Backward routes start fresh sessions and
consume the existing cumulative run budgets. A fresh stage clears obsolete
remediation context while the failure history remains saved. Questions do not
consume attempts.
A stage checkpoint Git failure records `CHECKPOINT_FAILED` at the newly observed
stage, stops execution and preserves the worktree. Remote checkpoint ownership
failures keep their existing codes; genuinely orphaned working runs remain
`STALE_WORKING`.
Active work remains cumulative when clarification resumes, a review revision
begins, approval is invalidated or an operator retries; waiting time is excluded.
Iteration, cost, and file budgets also remain cumulative.
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

### Direct completion and evidence

`_conduct_direct` accepts a settled successful attempt only when no questions
file remains and the product progress fingerprint changes. Both progress
observations pass literal exclusions for root `ADORE_SUMMARY.md` and the
configured questions file; path ownership/collision checks remain isolation's
responsibility. Empty questions files park too. `NO_CHANGES` retains the summary
and fails immediately; typed executor timeout/exit errors use existing build
failure counters. Live budget rereads and cumulative work apply normally. The
last authorized successful launch may complete; completion never authorizes
another launch when the launch limit is exhausted.

`_direct_prompt` uses `direct/implementation.md` plus literal ticket,
recovery/thread fragments and the same byte-preserved permission/network notice
as `_stage_prompt`. It requests repository instructions, complete implementation
and tests, blocking questions and a short change/check summary; Pi receives no
Git publication or forge-credential authority.

`validation_evidence` carries `summary`, `implementation = completed`,
`verification = not configured` and `changed_files`. Summary is bounded by
`_MAX_EVIDENCE` and sanitized, saved before isolation removes its transient
receipt-owned file. Each attempt starts with no old summary/completion evidence.
An absent summary is allowed; unsafe present artifacts stop before checkpoint
or approval. No direct strict-verification event or synthetic passed result is
written. Summary alone cannot authorize approval.

On success the conductor saves completion and the validate stage atomically in
one state write, then checkpoints product changes **before** target integration,
records clean candidate/target fingerprints and presents at done/awaiting-approval.
After interruption, orphan reconciliation and explicit Retry can finish that
completion even when its successful attempt used the last permitted launch.
Checkpoint failure retains
the validate stage and completion marker; Retry can finish without another Pi
session. Missing completion evidence at validate/done returns to build. Candidate
or target drift preserves completed implementation and summary but clears the
candidate binding, integrates/checkpoints again and requires fresh presentation
and approval. Integration conflicts return to fresh bounded build work.

All direct checkpoint entry points, including normal progress, Retry settlement,
review and human handoff, retain/remove summary first and pass literal exchange
exclusions. Isolation unstages exchange additions and rechecks the full staged
set. Direct settlement refusal is not suppressed into publication. Direct
handoff instructions do not name an AEGIS task. Approval/MR bodies show summary,
changed-file count and exactly "Verification: not configured. This candidate is
unverified." They omit AEGIS task lines. This build runs no direct verification
command. Fresh candidate-bound human approval, publication and merge authority
remain shared with the AEGIS path.

When adopting an existing review or publishing a newly approved revision, direct
publication replaces the MR/PR description with the current approved summary,
count, unverified notice and candidate/target binding through
`Forge.update_merge_request_body`. It changes no review settings. A failed or
timed-out update retains `MR_CREATE_FAILED` and cannot enter in-review or mark
the new candidate published. Explicit Retry repeats the description write
without another Pi session; a lost response is safe to retry with the same body.
AEGIS publication does not call this description-update operation.

### AEGIS verification

For AEGIS runs the conductor integrates `origin/<target>` and runs the validation executor,
whose session closes the AEGIS task with its own final strict check, `report`
and `advance` to done. On that validate -> done advance the conductor calls
`check --task <id> --strict --run --json` itself. It requires at least one
executed successful verification command and a task at done. The deviations
that journal recorded are copied into the validation evidence and lead the
approval presentation; they inform the approver and never block. Approval is
bound to the candidate fingerprint and target commit. Any candidate or target
drift invalidates approval. A done task the conductor holds no verification
evidence for (an invalidated approval, a run-ahead session) gets one fresh
session that returns it with `advance --to validate`; a failed independent
check counts one validate failure and a remediation session returns the task
from done to validate, build, design or specify. The run keeps the stage done
while it awaits approval, publishes and is in review.
On clarification resume and approval observation, title/body drift refreshes
the persisted ticket snapshot and content hash and records `ticket content
changed since pickup`; the observation alone does not invalidate the candidate.
Publication retry, from stage done or after `reset --to publishing`, rechecks
approval freshness and publishes the same candidate; without a fresh approval
it conducts the run from done. A run whose candidate already reached review
(its fingerprint equals the recorded `published_fingerprint`) returns to
review on retry. Publication refuses a run outside stage done or publishing
with `PUBLICATION_STAGE`; a run saved at the removed `deliver` stage is
refused when its state loads, so reset never reaches it. Existing open branch
MRs are adopted before creation.

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
saying so. Every round still ends at workflow-appropriate evidence and fresh
human approval before review publication: strict validation for AEGIS, explicit
unverified evidence for direct. Automatic repair never bypasses the human gate.

For AEGIS runs the revise label remains present through provisioning, probe
and task creation, and is removed only after the new task exists, immediately
before the run-state transition. Direct revisions provision but create no task;
the label is removed after successful provisioning. Without an AEGIS idempotency
key, a crash in the governed create/remove/save boundary can leave a duplicate/orphan task; the pre-removal task-created
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
refresh, MR fallback/adoption, approval retry freshness, publication without
an executor session or AEGIS command, the return from done to validate,
revise-label ordering, AEGIS timeout handling, typed executor-timeout
classification, clarification duration forms, live-lock-safe cleanup,
failed-resource preservation, egress companion GC, configured task-kind
fallback, one-read cost checks, environment precedence, human-merge metrics,
prompt restrictions and the absence of a merge capability. Direct public poll,
Retry/reset and revision cases also prove clone/worktree disagreement, first-save
identity, one-session approval/publication, summary retention and exclusions,
NO_CHANGES, empty questions, fresh thread resume, error/timeout/budget boundaries,
unsafe artifacts, Git/checkpoint recovery, evidence/drift invalidation and
workflow retention after later AEGIS adoption. `test_checkpoint_handoff.py`
proves exchange hygiene at the independent human-handoff checkpoint. Existing
AEGIS assertions and captured prompt bytes remain intact.

`poll_once(ticket_iid=IID)` filters ticket selection to one ready ticket while
preserving the same eligibility and publication gates. This is the web worker's
selected-ticket start path; the existing polling path is unchanged.


## Scoped repository credentials

Orchestrator.from_config passes a project-scoped runner to build_forge using the
directory containing the selected profile env file. repository_auth.project_runner
binds saved credentials to immutable profile identity and provider/repository/login,
or preserves external CLI behavior when missing. Only matching forge commands
receive tokens; worktrees, containers and executor secrets retain their own runner/
environment contracts. Corrupt/stale records raise RepositoryAuthError (ForgeError)
before fallback. tests/test_repository_connection.py proves all three engine
bindings and absence from executor secrets.

## Prepared backend target

Recipe runs resolve/persist the plan before worktree effects, pins the reviewed base commit, verifies actual image/container identity, provisions through `ExecutionBackend`, checks image tools/stages auth, then executes bounded preparation before AEGIS/AI. It saves running state before project effects and immutable timestamped redacted step receipts after execution. Failure/cancel/corrupt receipts never authorize gates. Resume verifies immutable evidence and IDs; only explicit bounded `--reprepare` recreates the owned container and retains history/worktree. Backend paths and executor homes/auth destinations govern commands. Tests: `tests/test_preparation_lifecycle.py`, `tests/test_orchestrator.py`.

## Native execution contract

The conductor selects the shared native backend and pins plan/resource, retaining the same AEGIS/executor/approval loop. Native provisioning skips images/setup/auth copies. Retry/parking preserve identity; local cleanup removes worktrees only after verified control. Container cleanup protects persisted native runs after backend drift.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused native proof:
`04_Software/tests/test_local_execution.py`.

## Automatic loop cadence

`run_loop()` uses the shared `adore.polling.PollCadence` policy documented in
[Polling cadence](Component_Polling.md). It retains the conductor lock, typed
forge/unexpected-error logging, local quiet windows and interrupt cleanup.
Success resets backoff; a quiet round preserves it. Each wait begins after the
round completes. Offline regression: `test_loop_polling_cadence_matches_web_errors_and_success`.

## Manual ticket admission

`poll_once(ticket_iid=IID)` validates a positive integer and admits only that
freshly read forge ticket while preserving the monitoring pause marker. Existing
reconciliation, conductor lock, capacity, present-payload compatibility, shared ticket eligibility
and publication approval boundaries remain active. Untargeted polling retains
the pause gate. Refused manual admission adds a closed `start_reason` code to
the summary; no ticket text or credential enters that code.

## Explicit native Retry

retry() revalidates only the native plan's environment_sha256, executable and
executable_sha256. All other policy settings, machine/account and resource
ownership stay fixed. It preserves task, worktree, branch, history and cumulative
iteration/cost/file budgets. After receipt/plan refresh, normal provisioning runs
the bounded executor version check before rereading the durable AEGIS task.
RETRY_REVALIDATION_FAILED records the actual recovery refusal; prerequisite
failures retain their existing typed cause. Automatic polls cannot authorize this
refresh. The bool return reports accepted operation; CLI checks the resulting
lifecycle before reporting success. All jobs, native executors and forge adapters
share this path. Focused proof: tests/test_retry_revalidation.py.


## Installed AEGIS journal authoring guidance

The shared stage prompt directs every executor to the target repository's
.agentic/templates/task.md before journal edits. It names preservation of the
original legal prologue, any retained authoring-guide link, the same task ID,
append-only Log/Rulings and the current checklist. Stage transitions and State
updates use the installed companion CLI writers. Failed edits repair the same
journal. Existing installed step files own the procedure, optional diagrams and
review/proof order; ADORE retains one-stage sessions, budgets and publication
approval. No payload, plugin, target repository or schema is rewritten.
Focused proof: test_stage_prompt_preserves_aegis_journal_authoring_contract and
existing executor_prompt tests.

## Agent-controlled system packages

Opted-in system-package jobs persist policy/resource plans even without recipes, authorize before agent work and fail closed on policy, container or image drift. The stage prompt reports package rights and independent network mode. Direct installations run within existing gate budgets; no broker selects or installs packages. See [Package permissions](Component_Package_Permissions.md) and the operator dependency-installation guide.

## Container timeout recovery

The shared bound backend settles timed-out container descendants before retaining
output or admitting another command. It parks and later resumes the same verified
resource, preserving installed dependencies and the independent egress policy.
Unconfirmed recovery raises ExecutionRecoveryError; active conduction persists the
existing INFRASTRUCTURE_EXHAUSTED terminal outcome without spending another
executor attempt. A pending operator cancellation takes precedence. Successful
timeout recovery preserves the original typed timeout classification and existing
bounded stage-failure policy. Preparation replay rules remain unchanged.

Contracts: REQ-FUNC-bff135e2, REQ-REL-ea593cbb, REQ-REL-d8e08cca and
REQ-DATA-62052e16. Offline coverage is tests/test_container_timeout.py, including
public retry persistence, plus preparation/native/conductor regressions.

## Native ChatGPT subscription


Native ChatGPT projects use `chatgpt.helper_for` with verified managed
Node/Pi. They share the ADORE-owned sign-in with container projects on that
home. Only a temporary access token reaches the bound Pi stage or model
probe, with explicit secret redaction. No refresh credential is placed in the
fresh executor agent directory. Native readiness reads stored sign-in status
without calling a model. Stage limits remain at most 3000 seconds.
WSL2 uses the Linux backend and delegated cgroup v2. Host networking remains
separate from the container internet switch. See
[ChatGPT sign-in](Component_ChatGPT_Sign_In.md).

## Owned abandonment and restart

`delete(run_id, owned_resources=False)` requires the conductor lock and verifies derived names (including configured branch templates), dedicated paths and Git ownership. Native drift acknowledgement uses the saved validated plan and immutable receipt without execution authority. An early unprovisioned native plan may release only proven absence of any unrecorded control directory. All containers prove dedicated repository/worktree/IO mounts; proxies prove the saved IO config bind. Actual internal networks must contain only verified executor/proxy IDs. Cleanup ignores current egress/backend choices and removes only observed immutable IDs, with verified absence. The remote branch is deleted only at its recorded checkpoint commit using an exact lease; an unpublished branch must already be absent. Local cleanup and state deletion follow verified resource cleanup; any failure prevents fresh admission and retains remaining state/evidence. Human-owned runs are refused. `restart(run_id, expected_revision)` accepts only the confirmed SHA-256 failed incarnation and an open ticket, completes owned deletion, restores ready eligibility and invokes normal manual ticket admission under the same lock. Monitoring pause remains set. Current hold/exclusion/capacity/approval checks retain authority. Offline proof: `tests/test_drift_recovery.py`.

Completed deletion also clears the old terminal summary. For registered web profiles, the injected deletion boundary holds the usage-projection transaction across local source removal and cursor reset; normal CLI-only state deletion remains independent of optional web dependencies. A stale reporting reader cannot reproject the old journal into the new job.

## Recovery from previously orphaned branches

Restart reuses its verified owned branch when the remote is absent or equals the saved checkpoint and the current naming rule admits it. A known checkpoint changed outside ADORE refuses before cleanup. If no checkpoint was ever recorded and an older occupied remote ref has unproven ownership, restart preserves it and preflights a valid fresh generation before destructive cleanup; normal delete still refuses to delete that ref. New admissions choose an empty derived base or generation and atomically create the local branch/worktree. A run without established worktree ownership never force-deletes an unproven local ref. Both delete and human-merged cleanup recognize only the configured base or one exact twelve-hex generation. The CLI result reports retention and the web result explains it in four languages. No storage schema or migration is introduced.

## Budget reread boundary

Before provisioning and each executor-attempt boundary, `_refresh_budgets` rereads
`Config.source_path`, validates the closed budget table and provider stage-timeout cap, then compares
all parsed and resolved non-budget settings with the startup-validated configuration. Only budgets are rebound. Missing/invalid source or
non-budget drift becomes terminal `BUDGET_CONFIG_INVALID` before another launch,
with task, counters, branch and resources retained. Injected configurations without
a source continue to use their explicit values. An already running attempt retains
its timeout; the next boundary checks reduced limits against accumulated usage.
The same cumulative active-time calculation bounds preparation steps.

Proof: public Retry with injected forge/executor/Aegis collaborators verifies
between-attempt raise, exhausted limits, missing/corrupt source and identity drift.

Non-budget binding preserves scalar types as well as values: boolean false and numeric zero are distinct. Canonical typed JSON comparison launches no probes.

## Journal-bound executor diagnostics

When a gate returns archives and host-normalized diagnostics, the conductor writes a unique schema-1 executor-diagnostics snapshot outside writable executor IO and records its exact SHA-256, cumulative launch number and filename on executor-artifacts. The snapshot binds run identity, launch context, exit/timeout and canonical streams. Gates without captured diagnostics retain explicit unavailability. This evidence adds no execution, retry or publication authority and changes no run-state schema. Invalid diagnostics or linked snapshot locations fail closed. A public Retry regression proves capture persistence and journal binding without live resources.

Every completed executor attempt records the latest evidence marker, including attempts with no archive or captured diagnostics, so earlier output is never substituted as the latest attempt.

Status comments identify the pinned execution backend, or configured backend before a plan exists. Terminal failure comments name the backend and offer web Retry and the CLI retry command. A status outbox replay edits the current lifecycle status and reconciles its labels before it acknowledges delivery; a failed comment or label operation remains pending, with notification markers preserving comment identity across replay.

On parked recovery the conductor verifies a backend stop and removes the question handoff again; failure becomes `PARK_CLEANUP_FAILED` rather than resuming work. Quoted notification markers never authorize adoption or editing of a human comment.


The orchestrator passes the configured Pi thinking level into the executor factory for each stage.
