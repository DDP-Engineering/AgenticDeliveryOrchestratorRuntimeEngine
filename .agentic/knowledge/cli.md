<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# CLI

## Routing

Use this page for `adore` commands, argparse, profile/config precedence and
selected-ticket invocation. Start at `04_Software/adore/cli.py`; verify with
`04_Software/tests/test_smoke.py`. The HTTP API is in `web-interface.md`.

## Purpose and boundaries

`04_Software/adore/cli.py` is ADORE's operator control plane. The `adore`
console script and `python -m adore` are deliberately thin argparse adapters
over typed components. The optional web worker invokes this CLI for operations;
its HTTP routes live in `web-interface.md`.

## Command groups

The CLI exposes configuration (`show`, `validate`, guarded scalar `set`),
runtime lifecycle (`run`, `status`, `runs`, pause/resume, cancel/retry/handoff/logs,
reset/delete/cleanup), metrics (`stats`, `report`, `export`), and profile setup
and management (`init`, `profile`, global `--profile`). Its configuration path
precedence is explicit `-c`, named profile, active profile, then local
`config.toml`.
`run --once --ticket IID` selects one eligible ticket for a web Start request;
it returns nonzero if that ticket cannot be picked; a completed pass that
does not pick it, or a held lock, first prints the stable line
`error: ticket #IID not started: <code>` (`pickup_paused`, `at_capacity`,
`aegis_probe_failed`, `not_eligible`, `conductor_busy` for a held lock), which
the web worker parses as the operation reason (REQ-FUNC-6c87ec5b).
Payload absence admits CLI/configured direct work normally; only a present failed
probe returns engine workflow_unavailable/payload_error and the existing
`aegis_probe_failed` CLI reason. No workflow selector or verification setting is
added. Direct reset accepts build/validate/publishing; other targets refuse
before mutation. `init` reports missing AEGIS as INFO; web enrollment is separate.

## Public interface

The `adore` console command and `python -m adore` expose configuration,
profiles, operator controls, run execution and metrics. `run --once --ticket`
accepts a positive forge ticket IID with normal selection checks.

## Invariants

Explicit `-c`, named profile, active profile and local `config.toml` define
configuration precedence. Invalid config returns nonzero. Engine mutations
respect the conductor lock; force is required for destructive state changes.
`config set` shares a per-directory edit lock with the web API; contention
returns a nonzero result without changing the config file. It reads and
writes the file as bytes and keeps its CR LF or LF line endings; added lines
take the file's ending.
`handoff` queues a validated request when a conductor holds the lock and
completes the transfer under the lock when idle. The terminal state preserves
the worktree for human ownership and grants no publication approval.
The CLI never merges or edits AEGIS journals directly.
`report` and `stats --rebuild` return a typed metrics-evidence error for
conflicting versioned usage. Rebuild computes all summaries before writing so
a late corrupt run cannot partially refresh the projection.

## Operator safeguards

Invalid/missing configuration produces a clear nonzero result rather than a
traceback. Destructive state operations require `--force`; mutations acquire
the single-conductor lock; `profile delete --remove-resources` releases the
containers and worktrees recorded for the project's own runs, except human-owned
ones, before deleting the profile; `--remove-clone` also removes an ADORE-owned
clone under <home>/repos after the profile (checked before and after the sweep);
cleanup removes only a provably stale local lock and the selected project's
own finished and orphaned run resources, and reports corrupt runs while keeping
their resources. `run` additionally tees output to
the rotating ADORE process log. All intervention commands change ADORE-owned
state only: they do not edit AEGIS journals or cause a merge.

## Key behaviors

REQ-FUNC-f9946b6b: Retry emits a final bounded ADORE_RETRY_RESULT containing
schema=1, requested run_id, actual exit_code and closed reason. An accepted Retry
ending failed exits 1/retry_failed and prints the saved outcome. Successful rearming
exits 0/retried. Setup/lock/state/repository refusals and known native executable,
account and permission problems are closed causes. The worker ignores raw logs.
Focused proof: tests/test_retry_revalidation.py and smoke mutation-lock selectors.


- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: config validate accepts local profiles; config plan resolves pinned native policy without project commands. Local config set resolves the same plan before writing. Existing run/retry/cancel/handoff/cleanup commands retain conductor ownership.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


- `REQ-UX-94a97e70`: `config plan` previews exact reviewed image/commands; selected source is checked by validate/set. `retry --reprepare` explicitly authorizes capped replay.

- `REQ-FUNC-39697089` - explicit force and live-lock protection for mutations.
- `REQ-FUNC-3557ecdf` - profile resolution, use tracking, and visible corrupt run state.
- `REQ-FUNC-f9946b6b` - selected-ticket web operations retain CLI boundaries.
- `REQ-REL-94e653aa` - operator handoff uses the conductor's safe boundary.
- `REQ-PLAT-722173c8` - configuration edits keep the file's line endings on every OS.
- `REQ-SEC-63767e17` - `config set` refuses secret-looking keys except ADORE's own `metrics.capture_tokens`.

## Files

- `04_Software/tests/test_retry_revalidation.py`: explicit Retry and bound outcome proof.

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


- `04_Software/adore/cli.py` - command parsing and routing.
- `04_Software/tests/test_smoke.py` - CLI behavior and failure contracts.
- `04_Software/tests/test_orchestrator.py` - selected-ticket selection checks.
- `04_Software/tests/test_checkpoint_handoff.py` - handoff command boundaries.

Manual `run --once --ticket IID` retains paused monitoring and appends a bounded,
versioned secret-free terminal result through adore/start_result.py. The worker
validates selected IID, exit code and allowlisted reason; see Component_CLI.md.

Native Pi lifecycle: `adore pi install` and `adore pi verify` work without a project.

## Confirmed destructive recovery

The CLI adds delete --owned-resources for failed/cancelled jobs and restart --force --expected-revision for one confirmed failed incarnation. Both hold the conductor lock; cleanup errors are clean/nonzero and preserve remaining evidence. Native cleanup-only construction does not resolve current tools. Live-lock guidance names the web worker, Project Summary pause and waiting for the bounded job, plus stopping a standalone CLI loop. Proof: tests/test_drift_recovery.py and mutation tests in test_smoke.py.


CLI delete records an uncertain local receipt outside the job before cleanup and confirms only afterward. It refuses corrupt/unavailable audit storage and reports post-delete confirmation failure as uncertain. A standalone CLI deletion never bootstraps web authentication.

Restart emits a closed terminal result bound to the job, confirmed revision, process exit and selected ticket. The worker refuses missing or mismatched evidence; untrusted text cannot establish a refusal.

## Bound worker child context

main attaches an internal closed ADORE_WORKER_CONTEXT before dispatch. Exact owner/operation
generations, command, immutable profile target and resolved config path are checked before
effects; automatic polling carries explicit project ownership with no manual operation.
The attached CLI child prevents recovery stealing work after parent death. Bound engines
install admission/state/command/publication fences; invalid context returns a value-free
ownership error. Standalone dispatch does not load optional web storage. Offline child
context tests use fake engines/runners and isolated profile homes.



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
