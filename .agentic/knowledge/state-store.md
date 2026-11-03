<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# State store

## Routing

Use this page for schema-1 run state, journals, conductor locks, outbox and
cancellation and handoff markers. Start at `04_Software/adore/state.py`; verify with
`04_Software/tests/test_state.py`. Web queue state belongs to
`web-interface.md`.

## Purpose and boundaries

Persists schema-1 `RunState` records, append-only JSONL audit events, pending
notification outbox records, pause state, and the single-conductor lock.

## Public interface

`derive_run_id` builds a ticket's stable run ID and `run_id_pattern` matches
exactly one project's run IDs. `StateStore` creates, loads, updates, lists, and
deletes explicitly selected runs; appends durable journal events;
queues/replays notifications; reads the global pause flag; and acquires the
instance lock. `StateError` and lock errors
make invalid state/ownership visible to CLI and orchestrator recovery paths.

## Invariants

Corrupt or unknown state never resets itself. Locks are reclaimed only when a
readable same-host owner PID is provably dead; unknown ownership stays locked.
Run updates and journal writes are atomic enough to preserve recovery evidence,
and failed runs are retained until an operator performs an explicit action.
Cancellation markers identify one run and are consumed by the active conductor;
the web worker cannot write an arbitrary terminal lifecycle into run state.
Run state is schema 1 with one current shape: unknown or missing keys mean
another ADORE build wrote it, and it is refused (there are no migrations while
ADORE is in development). Every refusal from `StateStore.load` ends with
`(run '<id>'; delete <run dir> to remove it)`. Malformed remote commit
identities fail closed. A pending or completed handoff refuses new cancellation;
the human-owned worktree remains protected from routine cleanup. A run's stage
is `frame`, `specify`, `design`, `build`, `validate`, `done` or the reset
pointer `publishing`; any other stage, the removed AEGIS `deliver` stage
included, fails closed as an unknown stage. `published_fingerprint` records the
candidate fingerprint of the last publication that reached review.

The durable store preserves recovery evidence and refuses corrupt or uncertain
ownership instead of resetting it.

## Key behaviors

- REQ-REL-6922cfe5: not-required recipe evidence may contain exact resource IDs for an explicitly package-enabled plan; it does not assert installed dependencies. Corrupt identity and unexpected resource authority remain errors.

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: Schema-1 execution state accepts the closed native resource with not-required status, zero attempts and empty preparation evidence. PIDs/scopes remain separate authoritative control records. Corrupt/unknown native fields fail closed; container-mode records stay valid.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


- `REQ-REL-d8fd134e`: The closed `execution` schema-1 record (empty in legacy container mode) validates plan/policy, resource IDs, attempts/history and complete ordered success. An empty record does not claim preparation success; state JSON rejects duplicates/non-finite constants.

- `REQ-FUNC-0bdb23d5` - schema-1 state corruption fails closed.
- `REQ-FUNC-51f9c365` - lock reclamation requires a provably dead local owner.
- `REQ-FUNC-1a2c56fe` - append-only journal persistence and torn-tail recovery.
- `REQ-FUNC-f9946b6b` - authorized cancellation signals an active run through
  a bounded marker.
- `REQ-REL-94e653aa` - checkpoint evidence and exact handoff requests survive
  restart without treating foreign state as a valid run.

## Files

- `04_Software/tests/test_system_packages.py`: package authority, independent egress, recovery and reviewed settings contracts.

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


- `04_Software/adore/state.py`
- `04_Software/tests/test_state.py`
- `04_Software/tests/test_checkpoint_handoff.py`
