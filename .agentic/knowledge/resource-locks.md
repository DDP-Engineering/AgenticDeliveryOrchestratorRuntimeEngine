<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Shared resource locks

## Routing

Use for bounded common Git, metrics, process-log, native Pi and ChatGPT mutations.
Start at `04_Software/adore/resource_lock.py`; prove with
`04_Software/tests/test_shared_resources.py`. Project barriers belong to `state-store.md`.

## Purpose and boundaries

Stable kernel exclusion and atomic text publication without owning agent execution.

## Public interface

`resource_lock(path, timeout=10)` yields thread-reentrant ownership or raises
`ResourceLockError`; `atomic_write(path, data)` publishes a unique fsynced sibling.

## Invariants

Windows/Linux kernel locks release on crash. Never unlink stable files during
operation. Linked/nonregular/multiply linked storage and invalid/unbounded waits
are refused. Separate keys permit independent runs. Replacement failure preserves
old output. State lifecycle locations depend only on canonical state-root paths.

## Key behaviors

REQ-REL-284af472, REQ-DATA-54868516 and REQ-REL-2e8dc2a1 bound common effects.

## Files

- `04_Software/adore/resource_lock.py`: locking and atomic output.
- `04_Software/tests/test_shared_resources.py`: injected boundary/concurrency proof.
- `05_SoftwareDocu/Component_Resource_Locks.md`: complete resource inventory.
