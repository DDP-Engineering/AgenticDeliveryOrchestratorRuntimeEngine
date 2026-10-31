<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# State Store Component

## 1. Purpose

`adore/state.py` persists the local source of operational truth and append-only
audit log. The closed run-state schema is `1`.

## 2. Responsibilities

- atomically save/load run state and ticket snapshots;
- append/read JSONL events;
- own pause and single-instance lock files;
- own per-run `cancel.request` markers used by the web worker and conductor;
- own validated `handoff-request.json` markers for operator ownership transfer;
- expose fail-closed stale-lock reclamation for cleanup: only a readable local
  lock whose PID is provably gone may be removed;
- derive stable run IDs (`derive_run_id`: `<platform>-<repo with / as ->-<ticket>`)
  and match exactly one project's run IDs (`run_id_pattern`, digits-only ticket
  part) so cleanup can tell its own resources from other projects';
- preserve active/historical task ids, stage/path/type, counters, incidents,
  outbox, validation evidence, candidate fingerprint, approval and MR state;
- report corrupt runs without silently reinitializing them.

## 3. Data Contract

Every `state.json` contains `schema_version: 1`. Missing/wrong schema and unknown
keys raise `StateError`. Any earlier state shape is rejected with a
no-migration diagnostic. Outbox/failure/task histories are lists and validation evidence is
an object.
The schema also carries a verified remote checkpoint commit and a checkpoint
error. Older schema-1 records load with empty defaults; malformed commit
digests fail closed. `handoff-pending` and `handed-off` are explicit lifecycle
states. `handed-off` is terminal for metrics while cleanup protects its worktree.

Writes use temporary-file replacement. JSONL is append-only; a torn trailing
line may be skipped because `state.json`, not the log, drives decisions.

## 4. Workflow Integration

The conductor saves before every remote notification, after every counter or
lifecycle change, and at every stage boundary. Explicit retry resets only the
active counter/clock; history remains.

The ticket snapshot and its `content_hash` are refreshed together when a fresh
clarification-resume or approval observation detects title/body drift. The
journal records the observation; it does not itself invalidate the candidate.

`acquire_lock()` and `reclaim_stale_lock()` never steal live, different-host,
unreadable, or wrong-shape lock records. Those records remain held with unknown
ownership until a human verifies the process and state.

`request_cancel()` creates an idempotent marker only for a nonterminal run.
Pending or completed human handoff refuses new cancellation requests.
Invalid run IDs and nonempty, symlinked or otherwise malformed markers raise
`StateError`. The conductor clears
the marker after normal cancellation; the marker never changes `state.json`
without that conductor decision.
`request_handoff()` writes an exact run identity and timestamp atomically.
Malformed or foreign handoff markers raise `StateError`; the conductor clears
the marker after durable ownership transfer.

## 5. Validation and Tests

`tests/test_state.py` covers schema-1 round trips, task history, refusal
rejection, corrupt state, snapshots, JSONL, locking, public stale reclamation,
unknown-lock fail-closed behavior, pause and cleanup support.

## Preparation evidence

Schema 1 accepts an optional closed `execution` record. Legacy absent/empty records load without claiming recipe success. Plan/policy fingerprints, actual IDs, sequential outcomes, bounded attempt/history records and complete success are validated on load. State JSON rejects duplicate/non-finite fields. Corruption raises `StateError`. Plan and step artifacts are immutable and checked by the conductor on reuse. See `tests/test_state.py` and `tests/test_preparation_lifecycle.py`.

## Native execution contract

Schema-1 execution state accepts the closed native resource with not-required status, zero attempts and empty preparation evidence. PIDs/scopes remain separate authoritative control records. Corrupt/unknown native fields fail closed; legacy container records keep compatibility.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused native proof:
`04_Software/tests/test_local_execution.py`.

## Agent-controlled system packages

A container execution record with not-required recipe status may bind exact container/image IDs when its plan explicitly carries system_packages=true. It records authority and resource identity, not installed-package success; malformed identities and unauthorized resource fields fail closed. See [Package permissions](Component_Package_Permissions.md) and the operator dependency-installation guide.
