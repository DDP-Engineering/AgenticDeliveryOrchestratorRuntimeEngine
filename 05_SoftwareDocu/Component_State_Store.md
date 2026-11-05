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
- report corrupt runs without silently reinitializing them;
- omit state removed between listing enumeration and file open, without
  suppressing unrelated I/O failures or changing direct-load errors.

## 3. Data Contract

Every `state.json` contains `schema_version: 1`. Missing/wrong schema, unknown
keys and missing keys raise `StateError`; there are no migrations, so state of
another ADORE build is refused rather than filled in with defaults.
`StateStore.load` appends `(run '<id>'; delete <run dir> to remove it)` to
every refusal. Outbox/failure/task histories are lists and validation evidence is
an object.
The schema also carries a verified remote checkpoint commit and a checkpoint
error; malformed commit digests fail closed. `handoff-pending` and `handed-off`
are explicit lifecycle states. `handed-off` is terminal for metrics while
cleanup protects its worktree.
The stage is `frame`, `specify`, `design`, `build`, `validate`, `done` or the
reset pointer `publishing`; any other stage, including the removed AEGIS
`deliver` stage, fails closed as unknown.
`published_fingerprint` records the candidate fingerprint of the last
publication that reached review.

Writes use temporary-file replacement. JSONL is append-only; a torn trailing
line may be skipped because `state.json`, not the log, drives decisions.

## 4. Workflow Integration

The conductor saves before every remote notification, after every counter or
lifecycle change, and at every stage boundary. Explicit retry resets only the
active failure counter; active work and history remain cumulative.

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
rejection, corrupt state, refusal of a run at a stage this build does not
conduct (`test_run_at_a_stage_this_build_does_not_conduct_is_refused`) and of
state missing a current key (`test_state_missing_a_current_key_is_refused`),
snapshots, JSONL, locking, public stale reclamation,
unknown-lock fail-closed behavior, pause and cleanup support.
`test_run_listing_tolerates_concurrent_disappearance` deletes an enumerated
state file or run directory at open for both `list_runs()` and `invalid_runs()`:
remaining valid runs stay readable, corrupt runs remain reported and unchanged,
and direct `load()` still raises `FileNotFoundError` for missing state.
`test_run_listing_propagates_unrelated_io_errors` preserves permission errors;
listings do not retry, repair state or treat missing files as corrupt runs.

## Preparation evidence

Schema 1 carries a closed `execution` record. An empty record (the no-recipe mode) claims no recipe success. Plan/policy fingerprints, actual IDs, sequential outcomes, bounded attempt/history records and complete success are validated on load. State JSON rejects duplicate/non-finite fields. Corruption raises `StateError`. Plan and step artifacts are immutable and checked by the conductor on reuse. See `tests/test_state.py` and `tests/test_preparation_lifecycle.py`.

## Native execution contract

Schema-1 execution state accepts the closed native resource with not-required status, zero attempts and empty preparation evidence. PIDs/scopes remain separate authoritative control records. Corrupt/unknown native fields fail closed; container records and the empty no-recipe record keep their own validation.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused native proof:
`04_Software/tests/test_local_execution.py`.

## Agent-controlled system packages

A container execution record with not-required recipe status may bind exact container/image IDs when its plan explicitly carries system_packages=true. It records authority and resource identity, not installed-package success; malformed identities and unauthorized resource fields fail closed. See [Package permissions](Component_Package_Permissions.md) and the operator dependency-installation guide.

## Cumulative active-work contract

`RunState.active_work_seconds(now)` returns cumulative working seconds from the
effective `active_started_at` anchor: working jobs use the supplied aware timestamp,
inactive jobs use `updated_at`. `StateStore.save` rereads existing state and moves
the anchor forward by the inactive interval before subsequent inactive saves or
resume. Thus retries, answers and revisions retain consumed work while excluding
waiting; notification and polling saves do not accumulate inactive time. No stored
field or schema changes. Iterations must be a nonnegative integer; saved clock
fields must be aware ISO timestamps, or `StateError` refuses the state.

Proof: `test_state.py` covers working/parked/repeated-save/retry time and corrupt
clock evidence; conductor tests cover clarification, approval invalidation and
review resumption without resetting consumed time.
