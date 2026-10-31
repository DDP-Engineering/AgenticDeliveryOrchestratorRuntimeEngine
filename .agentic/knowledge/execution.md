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

Provide the shared backend contract and container preparation file runner. `ExecutionBackend` supplies paths/shell, executor homes/auth destinations, provision/tool checks, resource/image identity, bound commands and owned stop/interrupt/remove. `ContainerBackend` implements existing ContainerManager semantics. `BoundTarget` verifies pinned identity before each command. `run_preparation_step` transmits file scripts, validates receipts and preserves typed incomplete results; standalone `preparation_runner.py` drains bounded redacted streams and enforces process-group timeouts. The conductor owns order, budgets, recovery and publication.

## Public interface

`ExecutionBackend` supplies paths/shell, executor homes/auth destinations, provision/tool checks, resource/image identity, bound commands and owned stop/interrupt/remove. `ContainerBackend` implements existing ContainerManager semantics. `BoundTarget` verifies pinned identity before each command. `run_preparation_step` transmits file scripts, validates receipts and preserves typed incomplete results; standalone `preparation_runner.py` drains bounded redacted streams and enforces process-group timeouts. The conductor owns order, budgets, recovery and publication.

## Invariants

Exact source/configuration authority; closed input grammar and recovery records;
bounded scripts/time/output/replay; unchanged egress/credential scope; immutable
source/image/resource evidence; setup finishes before AI. Explicit replay retains
worktree effects and prior attempt receipts. No publication or merging authority.

## Key behaviors

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
