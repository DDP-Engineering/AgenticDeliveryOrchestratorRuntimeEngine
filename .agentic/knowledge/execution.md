<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Execution

## Routing

Start at `04_Software/adore/execution.py` for execution contracts.
Focused verification: `04_Software/tests/test_execution.py` and `04_Software/tests/test_preparation_lifecycle.py`. Conductor ordering/recovery belongs
to `orchestrator.md`; CLI/GUI selection belongs to `cli.md`/`web-interface.md`.

## Purpose and boundaries

Provide the shared backend contract and container preparation file runner. `ExecutionBackend` supplies paths/shell, the executor environment (`executor_environment()`, no argument: `{}` for a container, the native account environment for local), provision/tool checks, resource/image identity, bound commands and owned stop/interrupt/remove. `ContainerBackend` implements existing ContainerManager semantics. `BoundTarget` verifies pinned identity before each command. `run_preparation_step` transmits file scripts, validates receipts and preserves typed incomplete results; standalone `preparation_runner.py` drains bounded redacted streams and enforces process-group timeouts. The conductor owns order, budgets, recovery and publication.

## Public interface

`ExecutionBackend` supplies paths/shell, the executor environment (`executor_environment()`, no argument: `{}` for a container, the native account environment for local), provision/tool checks, resource/image identity, bound commands and owned stop/interrupt/remove. `ContainerBackend` implements existing ContainerManager semantics. `BoundTarget` verifies pinned identity before each command. `run_preparation_step` transmits file scripts, validates receipts and preserves typed incomplete results; standalone `preparation_runner.py` drains bounded redacted streams and enforces process-group timeouts. The conductor owns order, budgets, recovery and publication.

## Invariants

Exact source/configuration authority; closed input grammar and recovery records;
bounded scripts/time/output/replay; unchanged egress/credential scope; immutable
source/image/resource evidence; setup finishes before AI. Explicit replay retains
worktree effects and prior attempt receipts. No publication or merging authority.

## Change map

| Change requested | Start with | Focused verification |
|---|---|---|
| Backend selection and paths | `ExecutionBackend`, `ContainerBackend`; see `local-execution.md` | `test_execution.py`, `test_local_execution.py` |
| Bound container commands and timeout recovery | `BoundTarget` | `test_container_timeout.py`, `test_execution.py` |
| Direct verification command integration | bound argv and `LocalTarget.run_verification`; see `orchestrator.md` | configured direct tests in `test_orchestrator.py`, native verification in `test_local_execution.py` |
| Preparation file transport and receipts | `run_preparation_step`, `preparation_runner.py` | `test_preparation_lifecycle.py`, `test_preparation_runner.py` |

## Key behaviors

- `REQ-PLAT-125bc4c1`, `REQ-PLAT-a39ffa22`: configured direct validation reuses
  bound container argv as `sh -c` in the worktree, preserving immutable identity
  and timeout recovery. Native verification uses `LocalTarget.run_verification`,
  not ordinary native shell argv; see `local-execution.md`. The conductor owns
  validate timeout selection, durable evidence and bounded fixes. AEGIS commands
  keep their own transport and accounting. Offline proof: `test_execution.py`,
  `test_container_timeout.py` and direct/native tests in `test_orchestrator.py`
  and `test_local_execution.py`.

- REQ-FUNC-c405688e: ContainerBackend.authorize_system_packages verifies the pinned running resource, then uses its immutable container ID for authorization. It adds no local installation authority.

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: ExecutionBackend has ContainerBackend and LocalBackend implementations. Native targets use run_files and native worktree/IO paths. Container controls refuse native identities before any manager call; native controls verify pinned runtime/launch scope. Preparation remains container-only.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


- `REQ-FUNC-e2b539d4`: immutable exact-source reviewed image/command plan.
- `REQ-FUNC-e5419c07`: bounded same-container setup before AEGIS/AI.
- `REQ-REL-d8fd134e`: fail-closed pinned recovery and explicit capped replay.
- `REQ-FUNC-e397f7f6`: shared backend lifecycle/transport contract.


## Files

- `04_Software/tests/test_system_packages.py`: package authority, independent egress, recovery and reviewed settings contracts.

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


- `04_Software/adore/execution.py`: public component and contracts.
- `04_Software/adore/preparation_runner.py`: standalone bounded step runner.
- `04_Software/tests/test_execution.py` and `04_Software/tests/test_preparation_lifecycle.py`: injected contract proof.
- `05_SoftwareDocu/Component_Execution.md`: detailed component documentation.
- `01_Documentation/Container_Preparation.md`: operator contract.

Preparation transport checks owned directory containment and linked parents before creating files, and checks result ownership before retaining evidence.

Native AEGIS stdout preserves the established 4 MiB JSON exchange bound; gate
stdout, stderr and questions remain bounded at 64 KiB. Native stream decoding
rejects invalid UTF-8; truncated JSON cannot become successful AEGIS evidence.
The shared drain retains container defaults. Saved local readiness checks reuse
approved profile .env values in memory through the same native environment.

## Timeout admission and recovery

Bound commands inspect authoritative ownership and address the immutable container
ID, including legacy invocations without durable pins. On an actual runtime
timeout, the backend rechecks that identity, uses bounded interruption and requires
the same ID/image in exited state before returning the original CommandResult.
The original exit, timeout flag and captured streams remain unchanged; an ordinary
exit124 does not trigger recovery.

The next bound command or normal provision verifies the stopped original, starts
that same ID and verifies running identity. The container filesystem, installed
dependencies, configured user and egress remain intact. There is no automatic
replacement or image pull. Native targets retain their existing behavior.

Unconfirmed stop/start, corrupt evidence or identity drift raises
ExecutionRecoveryError and blocks further commands in the active backend.
The conductor records INFRASTRUCTURE_EXHAUSTED without another executor attempt;
pending cancellation wins. Operator stop/interrupt/remove cancels pending automatic
restart. Failed active admission remains quarantined even after explicit removal;
operator inspection and a fresh controller are required for recovery. Existing preparation replay
and interrupted-controller recovery rules remain authoritative.

Pending/blocked admission is private in-memory backend state; confirmed stopped
runtime state and files persist. No profile/state schema, dependency or permission
is added. All helper processes in the dedicated container stop with the expired
command; filesystem state survives, while in-memory processes do not.

Offline proof: tests/test_container_timeout.py plus execution, preparation,
container-isolation, package, native and conductor regressions. Disposable real
Docker acceptance verified writer removal, same-ID/image deferred restart,
dependency marker retention and writable IO with network none/user adore. This
marker check is separate from live agent package-installation acceptance.

`BoundTarget.spawn` admits or resumes the verified container and addresses its immutable ID. `settle_timeout` quiesces RPC descendants and records same-resource restart eligibility; failed confirmation blocks further commands and spawns.


## Concurrent resource ownership

Every run process owns a fresh mutable backend/executor. Bound container targets
copy their environment and identity pins, so later caller mutations do not affect
another launch. Stop/interrupt/removal address observed immutable container IDs
and reject changed saved pins. Full executor/proxy/network cleanup is the
conductor's path-bound `release_owned` operation; backend-only executor removal
does not infer egress ownership from a name. Native targets retain run-owned
receipts and isolated Pi temporary settings.

Focused proof: `04_Software/tests/test_shared_resources.py`. Shared primitive and inventory: `05_SoftwareDocu/Component_Resource_Locks.md`.
