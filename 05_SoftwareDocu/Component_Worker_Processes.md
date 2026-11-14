<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Worker process containment

## 1. Purpose

`adore.web.processes` provides bounded, gated process trees for the web supervisor
and its project/run/configuration children. It owns OS containment and ancestry
transport; WebStore owns durable generations and the conductor owns run state.

## 2. Responsibilities

Establish a Job/session before releasing the child, inspect completion without
waiting for job duration, retain bounded output tails, stop whole owned trees,
and refuse effects when an ancestor PID/birth cannot be verified.

## 3. Implementation Overview

`ProcessTree` starts a trusted wrapper with private stdin gate/control and a
bounded stdout exit-report channel. An independent pipe reader retains at most 64 KiB of ordinary child output in memory. Windows attaches the wrapper to a random non-breakaway
kill-on-close Job before writing the gate byte. Linux starts a new session.
The wrapper launches the fixed argv without a shell, watches private-pipe EOF,
Stop and exact ancestor creation identity, and drains its process tree.
On Linux normal completion emits the actual child exit code before killing its
session. The parent uses waitid with WNOWAIT to keep an exited leader unreaped
until its original group is killed, covering a wrapper-only crash without ever
signalling a recycled group. Exit reports are accepted only after cleanup/reap. On Windows the
parent terminates and verifies the Job to remove any residual descendants.

## 4. Dependencies

Python subprocess/threading/tempfile, strict JSON, ownership.process_birth and
local_process.WindowsJobs. No service manager or broker is required.

## 5. Inputs And Outputs

Fixed argv and environment in; nonblocking exit inspection, captured output tail
and explicit Stop/kill/close out. Wrapper status is separate from untrusted child
output. Retained capture is bounded for indefinitely running workers as well as short commands.

## 6. Data Contracts

`ADORE_WORKER_ANCESTRY` is at most 8192 characters and 12 unique positive PID and
nonempty birth pairs. Missing transport denotes standalone use; malformed,
dead, reused or unknown evidence raises OwnershipError. Each spawn appends its
verified parent identity. Web schema 18 adds transient command ownership; ancestry itself is not persisted. No migration is provided.

## 7. Workflow Integration

WorkerContext checks ancestry before conductor state/Git/forge effects.
CommandWorker checks it before claims, cancellation signals and completion.
Supervisor/project loops check it before dispatch; portable services also watch
the launcher's identity. OS containment and durable ownership have distinct jobs:
unknown process evidence retains ownership even after a stop request.

## 8. Usage

`ProcessTree(argv, environment)`, `poll()`, `tail()`, `request_stop()` and
`stop_trees(children, grace=2, timeout=5)`. Stop requests all children before
waiting under shared deadlines; every scope receives kill/wait/close attempts
even if another scope fails, then a typed error reports unconfirmed cleanup; scope drain failure is explicit and retains
records. Windows Job verification is bounded at five seconds per scope.

## 9. Validation And Tests

`tests/test_web_supervisor.py` uses actual process trees and offline conductors,
plus injected Linux launch/kill boundaries. It covers nonzero exits, grandchildren,
parent crash, unavailable/reused/corrupt ancestors and capacity concurrency.
Portable launcher changes are inspected and smoke-checked without script tests.

## 10. Limitations

External container/native execution retains its existing resource ownership and
cleanup receipts. Local process death proves inability to make new conductor
effects; it never proves the outcome of an already dispatched remote action.
Such interrupted work remains uncertain and is not automatically replayed.

## Staged admission reductions and status

ProjectWorker shares `adore.capacity.admission_limit` with the conductor. A current staged lower `polling.max_concurrent_runs` immediately holds new admissions and resumptions until occupancy is below N; existing children are not cancelled. The saved configuration revision is retained for admitted jobs. Staged increases remain inactive until safe apply. Supervisor/configuration readiness is distinct from each project's worker and free slots; see [Project capacity](Component_Project_Capacity.md).

Queued working/execution_pending reservations retain launch authority but wait for the current dispatch ceiling. Real helper-process regressions prove two reservations start serially after N2→N1, while two executors already started before reduction continue together. Later Start remains queued.


REQ-FUNC-3b737a5c: queued initial starts share the reduced ceiling through supervisor dispatch and atomic conductor activation. Pending reservations do not count as started executors; existing running execution/cleanup does. Capacity deferral leaves execution_pending and queued dispatch unchanged until an actual slot is available.

## Integrated acceptance

The existing process contracts plus tests/test_worker_acceptance.py prove
actual Direct/AEGIS executor entry in independent processes, settings B/global
completion while A is blocked, preserved staging in active A, B completion
before releasing A, and deduplicated Cancel at a full real pool. The AEGIS fake
refuses independent test execution. The exact reuse map and platform/runtime
smoke boundaries are in ../01_Documentation/Worker_Acceptance.md. This is
application proof, not automated testing of deployment scripts.
