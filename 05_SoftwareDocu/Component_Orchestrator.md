<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Orchestrator Component

ADORE guides agents and observes their recorded workflow. AEGIS completion is
read from the task journal; Direct completion comes from the implementation
session and its summary. Tests and their local/CI selection belong to the agent.
ADORE does not invoke `check --strict --run` or run a separately configured test
command. Candidate fingerprints, target freshness and fresh human approval remain
required before publication. Old `workflow.verify_command` values are ignored
without rewriting profiles and cannot be edited through the API.

Shared ticket eligibility excludes the configured epic type label from automatic pickup and manual admission; eligible manual Start remains available with monitoring paused.

## 1. Purpose

`adore/orchestrator.py` is the deterministic ADORE conductor around the
agent-driven AEGIS and direct workflows. It prevents silent stalls and keeps
review publication human-approved with configurable draft or ready state.
An absent payload selects direct; a present unusable payload is never bypassed.


After observing a human merge, the shared CLI/web conductor honors `delivery.remove_source_branch` on GitHub, GitLab and Gitea. It checks review/run-branch ownership and performs bounded host-Git deletion with the last published commit lease. Every publication pins that commit even when progress commits are disabled. An absent branch succeeds; an unverified deletion leaves the job done with a branch-retained warning and keeps its local worktree for remediation. Closed unmerged reviews keep their remote branch.

## 2. Responsibilities

- select/claim forge tickets with the shared `adore.selection.ineligibility`
  rules (open, ready label, no hold/exclude, no existing run, priority and
  acceptance-criteria readiness) and provision worktree/container isolation;
- create and bind active/historical AEGIS tasks;
- launch a fresh executor session for each stage attempt;
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
- integrate the target, record executor validation and fingerprint the
  candidate/target/commit series;
- require a fresh approval-label transition after presentation when configured;
- push the validated candidate once and open or update the configured draft or
  ready MR/PR, with no executor session and no AEGIS command during publication;
- adopt an existing open branch MR/PR before attempting draft creation;
- create a new AEGIS task before consuming each bounded review request;
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
draft MR/PR; the configured candidate-bound approval policy governs that step.

Every nonterminal state has a poll action. Clarification has a timeout;
`awaiting-approval` and `in-review` intentionally do not because they are
human-paced states. A stale `working` state with no live conductor becomes a
loud failure rather than occupying capacity.
An authorized web cancellation creates a per-run marker after worker-side
grant recheck. Before more stage work, the conductor handles that marker with
normal `cancel()` teardown. Executor gates and direct verification share a watcher
that uses the bound backend's bounded interrupt call. Executor abort grace applies
only to gates. Direct verification rechecks cancellation before dispatch and after
execution, stopping conduction rather than scheduling remediation, checkpointing
or presenting approval. The marker is cleared after normal cancellation teardown.
The stale grace is applied only after exclusive run ownership is obtained;
a live or uncertain foreign owner is preserved regardless of timestamp age.
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

`_conduct_direct` launches bounded fresh implementation sessions. A successful
session must change product files and leave no blocking questions. ADORE retains
the sanitized agent summary, removes transient exchange files and checkpoints
before target integration. Evidence contains `summary`, `implementation = completed`
and `changed_files`, bound to the clean candidate and target fingerprints.
The agent selects repository checks; ADORE executes no standalone test command.
Retry can finish durable completion without another launch. Conflicts return to
implementation; target/candidate drift clears publication authority and requires
a fresh candidate binding. Direct jobs retain no AEGIS task.

### Observed AEGIS completion

`_record_aegis_completion` records the agent's done journal, task ID, deviations
and a bounded log tail with clean candidate and target fingerprints. ADORE does
not launch a strict check or require the full repository suite locally. A drift
marker routes the journal back to Validate through a fresh agent session.
The project approval policy applies equally to direct and AEGIS completion.
Automatic publication checks complete, workflow-specific evidence and freshness;
manual approval binds the exact candidate to a fresh human label.

### AEGIS verification

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
the project approval policy before review publication. Repository checks are
owned by the agent for either workflow.

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
[Polling cadence](Component_Polling.md). It uses independent run scopes, typed
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

`delete(run_id, owned_resources=False)` requires the selected run lock and verifies derived names (including configured branch templates), dedicated paths and Git ownership. Native drift acknowledgement uses the saved validated plan and immutable receipt without execution authority. An early unprovisioned native plan may release only proven absence of any unrecorded control directory. All containers prove dedicated repository/worktree/IO mounts; proxies prove the saved IO config bind. Actual internal networks must contain only verified executor/proxy IDs. Cleanup ignores current egress/backend choices and removes only observed immutable IDs, with verified absence. The remote branch is deleted only at its recorded checkpoint commit using an exact lease; an unpublished branch must already be absent. Local cleanup and state deletion follow verified resource cleanup; any failure prevents fresh admission and retains remaining state/evidence. Human-owned runs are refused. `restart(run_id, expected_revision)` accepts only the confirmed SHA-256 failed incarnation and an open ticket, completes owned deletion, restores ready eligibility and invokes normal manual ticket admission under the same run ownership. Monitoring pause remains set. Current hold/exclusion/capacity/approval checks retain authority. Offline proof: `tests/test_drift_recovery.py`.

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

## Project publication approval policy

`delivery.require_human_approval` defaults to true. The conductor retains the
fresh label-bound approval path when enabled. When disabled it checks saved
validation, task identity, fetched target and candidate fingerprint before
automatic publication; mismatch routes to validation and Git failures fail
closed. Retry and waiting-job reconciliation use the active policy; jobs
already in review remain there. Publication remains guarded and never merges.

## Durable admission and worker fencing

on_admitted runs after run state, ticket snapshot and picked journal evidence are saved, before forge claim labels or conduction. The web-bound CLI uses it to acknowledge Start independently of the later job lifecycle. before_effect checks worker authority before conduction and publication; bound state and command collaborators check again before writes and Git/forge commands. No admission callback is installed for automatic polling or Retry/Restart. Per-run locks, short admission reservations, validation and human merge boundaries retain authority.


Actual conductor and publication scopes acquire a unique run-role owner for the
immutable project/run, with child-process creation evidence and an independent child
heartbeat. Manual Start admission persists the exact run-owner ID/generation on its
operation before acknowledging. The child verifies both command/project and active
run owners before effects; completed scopes relinquish only their own run role.
Retry/Restart and automatic conduction/publication use the same run-scope hook.
A child heartbeat failure refuses subsequent effects; missing heartbeat never permits
another process to steal the run. Invalid child transport cannot create a missing store.


An attached command pins its immutable request fields once and selects the run proof
by the canonical command run ID, including during nested Restart reconciliation.
A run-role command binds engine.owned_run_id so reconciliation skips unrelated runs
before handoff/cancel/outbox effects. Project-owned reconciliation stays unchanged;
capacity always counts all working jobs in that project. Completion verifies owner
project/domain/run scope and validates the persisted operation again.

## Concurrent admission and run ownership

`poll_once(..., admit_only=False)` probes/selects outside admission, then takes
the selected run lock and a short admission lock to recheck pause, ticket
uniqueness and canonical project capacity. It acquires an execution-slot kernel
lock inside that transaction, releases admission, then allocates the pinned
worktree and saves the actual workflow before acknowledging Start. No Git,
forge or executor call holds admission. `admit_only=True` leaves a closed queued
dispatch for a separate process; ordinary polls conduct synchronously.

`conduct_run(run_id, config_revision=...)` advances only that run. It validates
loaded/configuration bytes and atomic `dispatch.json`, consumes initial launch
authority before labels/executor effects and starts the active clock after the
queue wait. Uncertain started dispatch requires explicit Retry. Nonworking runs
receive only their own reconciliation action. Each fresh CLI invocation owns its
conductor, executor, backend and configuration object.

Run lifecycle changes, journals, reconciliation, publication and operator actions
share a reentrant kernel run lock plus WK-01 durable run ownership/fencing.
Foreign live/uncertain owners are skipped before cancellation, outbox or stale
handling. The same project's other run continues independently. Interrupted
publication becomes `STALE_PUBLISHING`; automatic replay never opens another MR.

Capacity is the union of working reservations, handoff-pending, unsettled parked
cleanup and held execution-slot locks. The latter cover initialization before
state exists, Restart teardown and cleanup after lifecycle becomes inactive.
Settled approval/clarification/review waits consume no executor. Retry, Restart,
clarification resume, review revision and approval invalidation reserve capacity
before executing; a decrease never cancels existing jobs. Before each new
reservation the current source supplies `polling.max_concurrent_runs`; active
budget refresh permits this operational limit to change independently.

Proof: `tests/test_run_concurrency.py`, conductor admission/budget regressions,
`tests/test_web_ownership.py`, native retry and drift-recovery tests.

Ordinary cleanup takes exclusive ownership of every eligible run and reloads its
lifecycle before selecting resources, retaining those locks throughout the bulk
cleanup calls. Busy/foreign/corrupt runs remain protected. Profile resource purge
also rechecks the selected run under ownership before any removal. This prevents
cleanup from racing initialization, reconciliation or explicit Reset/Retry.

An uncertain STALE_PUBLISHING outcome also excludes automatic failed-run
checkpoint pushes on later polls; only explicit operator recovery can rearm
external publication effects.

Admission-only skips all reconciliation, so it cannot resume an existing answered
or review job. The required `execution_pending` state flag freezes the queue
clock in every reader and through pre-dispatch cancellation; activation persists
the clock before effects. Explicit recovery of a pending job consumes its queued
dispatch authority once. A run-bound Cancel refuses foreign targets before its
busy-owner marker fallback.

Cancel of an admitted native job whose pinned plan has no resource receipt
proves absence of its exact local-control directory before removing the worktree.
Any unrecorded control entry blocks cleanup and preserves state; no process is
assumed absent merely from missing saved resource identity.


## Concurrent resource ownership

Each production conductor owns its configuration, backend, executor, secrets,
IO and diagnostics. Resource branch/worktree/container identities include a stable
project suffix, so two profiles targeting the same repository/ticket remain distinct.
A branch template using only the ticket number receives the same suffix.
Checkpoint, publication, handoff, provisioning and teardown verify the derived
branch/container, saved worktree and native IO ownership before effects. Cleanup
retains stateless, corrupt, foreign, active and human-owned resources; verified
terminal resources use path-bound immutable release. It never force-deletes an
unproven husk. A human merge remains done if cleanup is refused, with a saved
resource-cleanup-retained diagnostic. ADORE never merges or repeats target tests.

Focused proof: `04_Software/tests/test_shared_resources.py` and the component’s existing offline contracts.


## Diagnostic and lifecycle boundaries

The profile-bound admission guard runs inside short admission transactions and
before queued execution. It rejects archived, deleted or replaced profiles while
leaving monitoring pause independent. Full cleanup uses path-bound companion
release; backend-only executor removal cannot infer proxy/network ownership.
