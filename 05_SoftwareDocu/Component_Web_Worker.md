<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web control worker

The worker publishes advisory busy or idle activity around its blocking runner. A recent heartbeat gates this evidence; absent or invalid activity is unknown. The authorized cancellation watcher remains independent of the serialized command queue.

## 1. Purpose

`adore.web.commands.CommandWorker` bridges durable web operations to the
existing ADORE CLI without giving the API process an executor call path.

## 2. Responsibilities

It owns a single-host worker lock, resolves the queued immutable project ID to
the current profile label, rechecks actor membership and project identity,
existence before execution, invokes fixed CLI arguments, records bounded
results, and polls project profiles between queued operations.

## 3. Implementation Overview

`run_pending()` claims one operation atomically. Start uses `run --once
--ticket IID`; retry and cancel use existing run commands. Administrator-only
pause/resume commands control project ticket pickup. A `delete` operation
runs `profile delete <name> --force --remove-resources` (plus `--remove-clone`
when the queued target is `remove-clone`) only when the actor is
an administrator and the project is still archived with the queued identity;
it audits `project-deleted` on success. The default runner
rejects an operation when its project was archived after queueing, and
periodic pickup skips archived profiles. Named and active-profile CLI `run`
also refuse pickup until restore. An explicit standalone `-c` config remains
an operator override outside profile archive control. The default runner
rechecks cancel targets before invoking the CLI; completed, failed and
human-owned runs are
left unchanged when a queued cancel arrives late. A run already cancelled by
the active conductor resolves the queued operation as succeeded. Around
every blocking worker command and project poll, a watcher inspects pending
cancellations across projects, atomically claims each exact execution-domain request,
rechecks account and immutable project grants, and writes a durable cancellation
marker only under the current owner/generation. The operation remains running
until the saved run actually reaches cancelled; a signal alone is not success. It
has a six-hour subprocess timeout. On restart, only operations belonging to demonstrably dead local owner processes
become `uncertain`; live and uninspectable owners remain untouched. Heartbeat age
never grants takeover authority. Recorded process creation identity distinguishes
a reused PID; an attached live CLI child keeps ownership even if its parent dies. The worker
uses `ADORE_HOME` for child CLI processes.
A separate heartbeat thread refreshes the web store while an engine subprocess
blocks. The worker clears its own supervisor readiness on graceful shutdown; after an abrupt stop,
the timestamp becomes stale within ten seconds. If heartbeat storage fails,
readiness fails closed and the worker exits after the current bounded command.

## 4. Dependencies

Python subprocess, `WebStore`, `ProfileStore`, the existing CLI and project
container/forge/executor prerequisites.

## 5. Inputs And Outputs

Inputs are pending SQLite operations and project polling configuration.
Outputs are CLI effects, operation status/result and audit events.

## 6. Data Contracts

Idempotency applies to queue insertion per actor/key. It does not make the
external forge or executor side effect exactly-once. An unknown subprocess
outcome remains `uncertain` and requires an operator to inspect run state.

## 7. Workflow Integration

Run `adore-web-worker` beside `adore-web`. It replaces a separate
`adore run --loop` scheduler for profiles in that home. The existing
orchestrator still owns state locks, the configured approval and draft or ready publication.

## 9. Validation And Tests

`tests/test_web_commands.py` covers fixed command vectors, deduplication,
revoked membership, cross-project signalling during a busy command, and delayed-cancel reconciliation. The full
CLI/orchestrator suite remains a regression gate.

## 10. Limitations And Future Work

The worker executes one engine command at a time. A running executor gate can
be interrupted, while cancellation during other bounded conductor work may
still wait. There is no global parallel job admission
cap or multi-host dispatch in this implementation.

## Project image work

The worker does not handle `image-build` operations and recovers no running
builds on startup; `WebStore.enqueue` accepts only `start`, `retry`, `cancel`,
`pause`, `resume` and `delete`. Images are managed outside ADORE. See
Component_Project_Images.md.

## Automatic polling cadence

Automatic web polling and CLI `run --loop` use `PollCadence`: after a round
finishes, wait `poll_interval_seconds * multiplier + uniform(0, poll_jitter_seconds)`.
With `poll_backoff = true`, failures double the multiplier from 1 to 2/4/8,
cap at 8, and success resets it to 1. Disabled backoff uses 1. Quiet rounds retain
the multiplier and defer automatic work using the same wait. Quiet windows use
server-local time; explicit web commands remain available.
The web worker keeps independent in-memory cadence/deadlines per immutable
project identity and treats nonzero, timed-out, malformed or exceptional CLI
outcomes as failed checks. Invalid configuration gets a 60-second recheck with
no engine invocation. Restart resets cadence; serial work on another project
may delay a due round. `polling.mode` governs standalone CLI startup; the web
service schedules repeated `run --once` rounds independently of that value.

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
