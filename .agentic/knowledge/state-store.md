<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# State store

## Routing

Use this page for schema-1 run state, journals, admission and run locks, outbox and
cancellation and handoff markers. Start at `04_Software/adore/state.py`; verify with
`04_Software/tests/test_state.py`. Web queue state belongs to
`web-interface.md`.

## Purpose and boundaries

Persists schema-1 `RunState` records, append-only JSONL audit events, pending
notification outbox records, pause state, and short admission and per-run lifecycle locks.

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
pointer `publishing` for AEGIS. Required `workflow` is exactly `aegis` or
`direct`; missing/unknown/nontext values are refused without default filling.
Direct stages are build/validate/done or the publishing control pointer, with
null active task and empty task history. AEGIS-only direct stages and task
bindings fail with StateError. Any other stage, including `deliver`, is unknown. `published_fingerprint` records the
candidate fingerprint of the last publication that reached review.

The durable store preserves recovery evidence and refuses corrupt or uncertain
ownership instead of resetting it. `list_runs()` and `invalid_runs()` omit state
removed between enumeration and file open. Corrupt state remains visible through
`invalid_runs()`, unrelated I/O errors propagate, and direct `load()` still raises
`FileNotFoundError` for missing state. Deterministic public listing tests inject
file/directory deletion at open without retries or automatic recreation.

## Key behaviors

- `REQ-DATA-6a1eb88f`, `REQ-DATA-5987cbe2`, `REQ-DATA-18956e56`,
  `REQ-DATA-9e8e1a73`: current-shape workflow/task/stage validation refuses
  corrupt state unchanged, naming the run directory to delete. Constructor
  defaults apply only to new in-memory callers, never older stored shapes.
- `REQ-DATA-153dcce1`, `REQ-DATA-3e54b751`: the conductor selects workflow
  before the first durable claim and retains it on resume/Retry/reset/revision.
  Existing validation_evidence holds direct summary/completion/not-configured
  evidence; no extra summary field or strict pass is implied. Completion and
  validate share one state save; isolation receipts are transient only.

- REQ-DATA-0c65db9f: `RunState.active_work_seconds(now)` computes working time from the durable effective active-start anchor; inactive rows freeze at updated_at. `StateStore.save` shifts the anchor over each inactive interval, including repeated saves and resume, preserving consumed work. Disk load requires a nonempty aware active timestamp; invalid clocks/iteration counters raise StateError without reinitialization. Stored fields and schema remain unchanged. Proof: test_state.py and public conductor resume/retry/review tests.

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

The parked-poll counter must be a nonnegative integer. A positive value records completion of parked cleanup; corrupt values are refused at load. Proof: test_parked_poll_counter_rejects_corrupt_state.

## Optional writer fencing

StateStore.before_write is an optional injected authority callback. JSON writes check it
before writing and again before replacement; journal appends and pause/resume, cancellation,
handoff and deletion mutations check before effects. The web-bound CLI installs current
worker/operation authority. Standalone CLI leaves it unset; run-state schema stays 1.
A lost worker cannot overwrite a run or append evidence. Tests include state/CLI regressions
and test_web_ownership.py::test_cli_attaches_and_fences_state_and_external_effects.

## Concurrent lifecycle storage

`run_lock` gives independent stores/processes exclusive kernel ownership on a
stable per-run file. Thread nesting is allowed only within the same StateStore.
Normal `admission_lock` capacity sections contain only local reservations;
project destruction retains the explicit full barrier through authorized cleanup.
`execution_slot` keeps initialization/cleanup visible before/after active state.
Locks release on process death and their files are never unlinked during normal
operation. A held lock, not its file's age, proves a live conductor.

`save_dispatch` and `load_dispatch` own a separate closed schema-1
`dispatch.json`: schema, exact SHA-256 config_revision, queued/started status.
Missing, linked, oversized, unknown-key, other-schema or malformed records fail
with StateError and file-named operator guidance. Started launch authority never
reappears from a missing audit line. State schema remains 1 with no migration.
Terminal metric and state deletion publish together under short admission.
Proof: test_run_concurrency.py and existing state-store tests.

Current state requires `execution_pending` as a strict boolean. A newly admitted
job sets it true with zero executor/task progress, so every state reader reports
zero active time until dispatch. StateStore treats that interval as inactive on
all saves, including Cancel. Activation clears and saves the flag/clock before
consuming dispatch authority or performing a forge/provisioning effect. A true
flag with executor/task progress is corrupt; a missing field is refused with the
run directory to delete, without repair or conversion.


## Concurrent resource ownership

`project_barrier()` excludes admission and acquires every known lifecycle and
execution scope before yielding. This includes reservations whose run state is
terminal or already removed. Profile-contained state places stable kernel files under the server home
identified by its path, in `resource-locks/state/<canonical-state-root-hash>/`.
External state keeps `<state root>/locks`. Windows profile deletion therefore
cannot unlink held kernel inodes. Do not
remove these files while the server/runs are active. Admission reentrancy covers
its entire kernel and operator scope. JSON publication uses unique temporary
files and fencing immediately before replacement. Journals remain in each run's
own directory and each live conductor holds that run's lifecycle lock.

Focused proof: `04_Software/tests/test_shared_resources.py`. Shared primitive and inventory: `05_SoftwareDocu/Component_Resource_Locks.md`.


Kernel lock placement depends only on the canonical state-root path. Profile-contained
state uses the server home identified by the `profiles/<profile>/...` path layout,
with locks outside the deletable profile. External state keeps `<state root>/locks`.
Changing ambient ADORE home cannot split ownership. A clone containing retained state
is kept during optional clone removal.

REQ-REL-83b9fc8c: load and atomic JSON publication bound Windows sharing conflicts
(winerror 5/32/33 or Windows CRT EACCES without winerror) to six attempts with 250 ms total scheduled waits. Persistent
sharing denial raises StateStorageError (StateError subtype) with the exact path,
preserving prior evidence and propagating through list_runs/invalid_runs;
other I/O errors still propagate. Publication rechecks before_write on every
attempt. Focused public proof: tests/test_state.py state_sharing tests.
