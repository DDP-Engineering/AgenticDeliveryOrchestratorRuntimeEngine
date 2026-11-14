<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Shared resource locks

## 1. Purpose

Serialize bounded mutations of shared host resources while independent run processes
continue executing. Implementation: `04_Software/adore/resource_lock.py`.

## 2. Responsibilities

`resource_lock(path, timeout=10)` owns a stable kernel lock file. Windows uses
`msvcrt.locking`; Linux uses `fcntl.flock`. Files remain present after release and
process death releases ownership. The caller bounds the operation itself.
`atomic_write(path, text)` publishes UTF-8 from a unique, fsynced sibling temporary
file and removes the temporary file after failure.

## 3. Implementation Overview

Locks are reentrant in the current thread, including nested calls from another
manager using the same normalized path. Other threads/processes retry acquisition
at most every 25 ms until the supplied deadline. A zero bound attempts once.
Symlink/reparse lock storage and nonregular or multiply linked lock files fail
with `ResourceLockError`; callers translate that into their component's typed error.

## 4. Dependencies

Python standard library and native Windows/Linux kernel file locks. No agent,
forge, container runtime or external dependency is needed for locking itself.

## 5. Inputs And Outputs

Inputs are an application-owned stable lock filename and a nonnegative wait bound.
Lock acquisition yields an owned scope or raises `ResourceLockError`. Atomic output
requires the caller's mutation authority; replacement failure preserves the previous
file and raises `OSError`.

## 6. Data Contracts

Lock-file existence and age grant no authority. Do not unlink lock files while the
server or any run may still use them. Atomic output files and lock files are
separate inodes, so replacing a report cannot invalidate its writer lock.

## 7. Workflow Integration

| Resource | Lock scope | Work outside the lock |
|---|---|---|
| Git worktree registry, checkpoints and config repair | Resolved common repository directory | Agent execution, remote publication |
| Git fetch | Dedicated common-repository fetch key | Other local worktree operations |
| Metrics database and JSONL mirror | Database writer key plus mirror key | Agent execution and short committed SQLite reads |
| Managed Pi installation | Versioned tools root `.install.lock` | Verification/use of published immutable packages |
| ChatGPT refresh and disconnect | Credential directory `refresh.lock` | Already launched stages and per-run credentials |
| ChatGPT device identity | Credential directory `device.lock` | Other credential readers after atomic publication |

The existing reviewed image preparation uses its dedicated cross-process image
lock and temporary build contexts; retained recipe publication uses its catalog
lock and atomic files. Job preparation only modifies its run's container.

## 9. Validation And Tests

`tests/test_shared_resources.py` covers contention, reentrancy, release after
failure, concurrent provisioning/checkpoints/termination, atomic metrics snapshots,
SQLite contention, concurrent refresh and Pi installation. External commands are
injected and no target repository check or live service is invoked.


Kernel lock placement depends only on the canonical state-root path. Profile-contained
state uses the server home identified by the `profiles/<profile>/...` path layout,
with locks outside the deletable profile. External state keeps `<state root>/locks`.
Changing ambient ADORE home cannot split ownership. A clone containing retained state
is kept during optional clone removal.
