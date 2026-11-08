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
cancellations across projects, rechecks account and project grants, and writes a
durable cancellation marker for a pending valid request. It
has a six-hour subprocess timeout. On restart, previously running operations
are marked `uncertain` for reconciliation rather than replayed. The worker
uses `ADORE_HOME` for child CLI processes.
A separate heartbeat thread refreshes the web store while an engine subprocess
blocks. The worker clears readiness on graceful shutdown; after an abrupt stop,
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
orchestrator still owns state locks, approval and human-approved draft or ready publication.

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
