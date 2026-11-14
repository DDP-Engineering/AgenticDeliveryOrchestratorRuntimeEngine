<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web supervisor and worker processes

## 1. Purpose

The `adore-web-worker` entry owns one local supervisor per home. Independent
project workers own admission and their N-place run pools; a separate process
consumes durable scoped configuration tasks and immediate admission controls. The API never conducts jobs.

## 2. Responsibilities

`Supervisor` discovers profiles by immutable project_id, independently restarts
failed workers with per-scope backoff, and stops owned trees. `ProjectWorker`
keeps its own polling, quiet hours, backoff, commands and run deadlines. It
uses the canonical atomic project admission limit for Start/Retry/resumptions.
`CommandWorker` validates one scoped request/result through fixed CLI arguments.
Its synchronous scheduling helper remains available for in-process callers;
production startup routes through the process supervisor.

## 3. Implementation Overview

The supervisor's `tick` only inspects and dispatches; no job duration is awaited.
Each active profile receives a project process even when monitoring is paused.
Admission invokes `run --once --admit-only`; accepted queued runs are dispatched
to `conduct RUN --config-revision SHA256` in separate processes. Existing durable
run owners and kernel locks prevent duplicate execution. Consumed working and
publishing states use the conductor's refusal/recovery path, never a fresh agent
or repeated publication. Initial queued dispatch authority remains explicit.

One separately owned command child per project executes Start/Retry/Restart/Cancel independently
of the polling and run processes. Starts/Retry/Restart wait in the durable queue
at capacity; Cancel keeps its control path. Configuration tasks use independent bounded fast/long/shared-auth lanes; Pause/Resume
use the immediate control pass and Delete uses its existing confirmed CLI path.
See [Configuration worker](Component_Configuration_Worker.md) for revision/authority,
private records, staging, environment preparation and durable outcome contracts. No global single-job ceiling exists.

## 4. Dependencies

Portable Python stdlib, ProfileStore, WebStore, StateStore, PollCadence,
WorkerContext and the existing conductor CLI. Process containment reuses the
WindowsJobs adapter; Linux uses owned process sessions.

## 5. Inputs And Outputs

Inputs: current profile/config bytes, durable operations, dispatch records and
run state. Outputs: scoped child trees, heartbeats/activity, command outcomes,
audit records and conductor-owned run changes. Output capture is continuously drained into a fixed 64 KiB memory tail; wrappers report bounded exit codes separately from logs.

## 6. Data Contracts

Web schema 18 includes a separate command owner role. Ownership generations and process births remain
canonical; strict bounded `ADORE_WORKER_ANCESTRY` transports distinct PID/birth
pairs. Every child waits for a launch gate after Windows Job assignment or Linux
session creation. Child effect authorization rejects dead, reused or unknown
ancestors with OwnershipError. Heartbeat age never proves death.

## 7. Workflow Integration

Start one API and one supervisor per home. The portable launcher owns both;
new/restored projects need no service setup. Rename retires only the old process
for the same immutable ID; archive/delete removes that process. Other IDs keep
their existing processes. The launcher identity is also an ancestor fence.

## 8. Usage

`adore-web-worker --home <absolute-home>`; portable Start/Stop remains the one
application control. Internal fixed-role entries live in `web.supervisor`.
Automatic checks use PollCadence after completion; quiet skips retain backoff.
Invalid config/state blocks dispatch and is rechecked after a bounded delay.
A failing project never delays another project's polling cadence.

## 9. Validation And Tests

`tests/test_web_supervisor.py` proves real conductor/executor overlap through
injected offline forge/Git/backend collaborators, N+1 deferral, separate actual
project/configuration PIDs, blocked A with completed B, parent crash/descendant
death, uncertain claims, malformed evidence and identity discovery. Existing
command/ownership/run concurrency tests cover CLI result and permission seams.
Portable tools are inspected and smoke-checked without deployment script tests.

## 10. Limits And Recovery

Stop requests all children together, allows two seconds grace and five seconds
forced root drain per boundary. Windows Job drain adds at most five seconds per
scope; unknown drain keeps ownership records. Commands have a six-hour ceiling,
while conductors enforce each project's own configured execution budgets.
A crashed owner is recovered only after all exact participant births are dead.
Queued requests and recovery evidence remain durable; uncertain effects are never
replayed automatically. Configuration-candidate execution is owned by its separate
consumer contract. There is no multi-host dispatch.

## Manual admission results

Start targets one ticket while retaining paused automatic monitoring. The default
runner returns captured `CommandResult`; injected integer runners remain
compatible. For Start, the worker validates only the final terminal CLI record
through `start_result.py`: at most 1024 characters, duplicate-free JSON with
exact schema/ticket/exit/reason fields, bound to the selected IID and observed
exit code. Unknown codes, extra fields and mismatched identities/outcomes reject.
A successful exit with invalid evidence remains uncertain; a failed exit stays
failed with `start:invalid_result`. Valid failures store `start:<closed reason>`.
Arbitrary process output and credentials never enter the operation result.
Automatic polling extracts the exit code from CommandResult without reading
manual result evidence. Timeout remains uncertain and is never replayed.

## Background engine launch

The production runner applies the shared child-only pager environment and
Windows no-console options, closes stdin, and retains the existing captured
UTF-8 streams, six-hour timeout and manual-result validation. The selected
`ADORE_HOME` and other worker environment values remain available to the child.
Focused proof: `test_default_worker_runner_carries_manual_outcome`.

## Explicit Retry feedback

The production worker validates the final bounded ADORE_RETRY_RESULT evidence
against the requested run and observed CLI exit, rejecting duplicate fields,
unknown reasons and malformed or mismatched output. retry_failed reads only that
project/run's persisted failed outcome, already public in Jobs, into bounded
retry:failed feedback. Other refusals use closed retry reasons. Missing failure
state is reported as state_unavailable; a timeout remains uncertain. Raw stdout
logs and stderr never become user-facing diagnostic text. Focused offline proof:
tests/test_retry_revalidation.py; existing queue authorization remains unchanged.

## Revision-bound restart

The durable `restart` action stores `<run-id>.<state-sha256>` in the existing operation target. The worker rechecks current actor/project grants, immutable project identity, failed lifecycle and exact state bytes before launching fixed CLI argv `restart <run-id> --force --expected-revision <sha256>`. The CLI checks again under the conductor lock. Changed incarnations are `restart:job_changed`; unsuccessful invocation is localized as incomplete/refused recovery, with bounded redacted diagnostics. In-flight worker loss remains uncertain and is never replayed automatically. Offline proof: `tests/test_drift_recovery.py`.

Confirmed deletion clears the owning profile/job usage projections while holding their SQLite write transaction across source removal; old reporting readers cannot restore a discarded cursor. The CLI binds this callback only to the registered profile matching its exact resolved config path. No account, grant, audit or other project projection is reset.

A successful CLI restart summary with `unproven_branch_retained: true` becomes localized `restart:retained` success evidence. This reports an older unproven ref retained while a fresh branch is used; it grants no cleanup or publication authority.


Start and Retry consume bound terminal evidence. Restart exit zero requires a JSON summary naming the original ticket; malformed, absent or mismatched evidence remains uncertain. The History projection distinguishes observed failure from refusal.

Restart terminal evidence binds job, revision, exit and selected ticket; unbound output is uncertain and cannot establish a refusal or success.

## Durable ownership and queue domains

`WebStore.register_worker(role, project_id=..., run_id=...)` issues a `WorkerOwner`
with a random owner ID and monotonically increasing scoped generation. Roles are
supervisor (global), project (explicit immutable project), run (explicit project/run)
and configuration (explicit project or global). `claim_next(owner, domain=...)`
checks the matching execution, configuration_project or configuration_global domain;
actor/grant/identity revocation produces a closed failed result without invoking an effect.
A unique running-resource index serializes the same job across Retry and Restart,
while different projects retain independent owners. Cancel has its own control resource.

`enqueue_configuration(..., project_id=...)` queues only an opaque protected-candidate
reference; `None` explicitly means global configuration. No configuration or credential
payload enters the queue. The command bridge consumes only its declared CLI actions;
protected configuration references remain for their dedicated consumer. Existing
reviewed configuration HTTP saves keep their existing apply path in this step.

All completion and effect calls carry the exact owner and operation generation.
Exact terminal replay is idempotent; changed replay or a stale handle is refused.
Recovery inspects PID creation evidence outside SQLite writer transactions and
rechecks the complete owner/participant snapshot inside a short transaction.
Unknown probes, stale heartbeat and shutdown requests cannot take live ownership.
Role/project/run heartbeats are independently queryable; web readiness uses the supervisor.

The CLI attaches to the internal bound claim before dispatch. It checks the exact
command/profile/target and resolved configuration path, fences state writes, Git/forge
commands and publication/conduct boundaries. Automatic project polls carry explicit
project ownership too. A live attached child prevents recovery stealing the work.
Owner IDs remain internal and are excluded from the public operation projection.

Start succeeds at the admission callback after saved run identity, ticket snapshot
and picked journal evidence, before conduction. `admitted_run_id` links the admission
to its job; later job failure cannot rewrite this success. Exit zero without admission
remains uncertain. Cancel exit zero also requires a saved cancelled lifecycle;
otherwise `cancel_unconfirmed` is uncertain. Neither queue insertion nor claim proves
an applied action. Offline contracts are in `tests/test_web_ownership.py`, worker,
audit, readiness, CLI and state tests, plus four-locale operation-reason tests.


Actual conductor and publication scopes acquire a unique run-role owner for the
immutable project/run, with child-process creation evidence and an independent child
heartbeat. Manual Start admission persists the exact run-owner ID/generation on its
operation before acknowledging. The child verifies both command/project and active
run owners before effects; completed scopes relinquish only their own run role.
Retry/Restart and automatic conduction/publication use the same run-scope hook.
A child heartbeat failure refuses subsequent effects; missing heartbeat never permits
another process to steal the run. Invalid child transport cannot create a missing store.


Retry/Restart acquire their canonical run role before the CLI handler, covering
validation, reset and resource teardown as well as conduction/publication. A command
already owned by that exact run handle reuses it and retains it through fenced
completion. Claims defer another active run owner; effect authorization requires
explicit proof of any separate run handle held by the child. Historical owner
records and configuration-domain identity validate before mutation. SQLite faults
become typed ownership-store errors; parent and child heartbeat failure is explicit.
Linux missing boot or masked-live-process evidence is unknown, preserving ownership.
Recovery compares process snapshots in canonical PID/birth order.


An attached command pins its immutable request fields once and selects the run proof
by the canonical command run ID, including during nested Restart reconciliation.
A run-role command binds engine.owned_run_id so reconciliation skips unrelated runs
before handoff/cancel/outbox effects. Project-owned reconciliation stays unchanged;
capacity always counts all working jobs in that project. Completion verifies owner
project/domain/run scope and validates the persisted operation again.


Existing-store schema/audit checks use autocommit reads; only fresh initialization
(or waiting to recheck a schema-0 store being initialized) takes the initialization
writer lock. Corrupt existing history remains refused. Owner history is read and
validated outside the writer transaction; registration compares its latest validated
snapshot through an indexed generation lookup before inserting the successor.
The current unique owner/resource indexes are validated at open. Deterministic
held-projection tests prove another role can commit a heartbeat before validation
is released, without replacing real SQLite writes with mocks.

## Per-run engine scope

`WorkerContext.run_available` recovers only provably dead run owners, then
protects any active foreign owner regardless of heartbeat age. Engine run
control combines that evidence with a kernel lifecycle lock before effects.
A run-role context without an operation claim authorizes only `conduct` for its
exact project/run; it cannot poll, reconcile another run or claim another ticket.
`WebStore.authorize_worker` exposes this exact run action in addition to the
existing project polling action. Process supervision remains separate from the
conductor's admission and single-run interfaces.


Transient execution commands have their own project-scoped command role, so a
live project scheduler cannot retain a dead command claim. The command process
drains up to 32 watcher-claimed cancellation follow-ups before exit; any
unconfirmed remainder is recovered as uncertain after demonstrated process death.
