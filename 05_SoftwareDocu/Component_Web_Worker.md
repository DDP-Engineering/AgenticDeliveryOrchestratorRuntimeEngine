<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web control worker

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

Queued historical image-build actions are marked failed without runtime execution.
On startup, interrupted image requests reconcile verified owned resources through
ImageBuildService before ordinary operations become uncertain. See
Component_Project_Images.md and test_web_image_build.py.

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
