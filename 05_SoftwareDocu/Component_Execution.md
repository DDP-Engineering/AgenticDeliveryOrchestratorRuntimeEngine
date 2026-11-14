<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Execution component

## 1. Purpose

Provide the shared backend contract and container preparation file runner.

## 2. Responsibilities

`ExecutionBackend` supplies paths/shell, executor homes/auth destinations, provision/tool checks, resource/image identity, bound commands and owned stop/interrupt/remove. `ContainerBackend` implements existing ContainerManager semantics. `BoundTarget` verifies pinned identity before each command. `run_preparation_step` transmits file scripts, validates receipts and preserves typed incomplete results; standalone `preparation_runner.py` drains bounded redacted streams and enforces process-group timeouts. The conductor owns order, budgets, recovery and publication.

## 3. Implementation Overview

Conductor → ContainerBackend → ContainerManager. BoundTarget → preparation file runner or existing AEGIS/executor transport; all reuse the same target paths and resource.

## 4. Dependencies

Python standard library; typed configuration, injectable command runner and
container isolation. The execution runner requires Python 3 and POSIX sh in the
selected locally available image. Core package dependencies remain empty.

## 5. Inputs And Outputs

Typed profile, exact tracked source selection, pinned plan and owned target.
Outputs are normalized plans or bounded timestamped step results. Secret values
remain in memory/environment and are excluded from plan policy/fingerprints.

## 6. Data Contracts

The closed version-1 grammar, profile limits, source/image precedence and schema-1
additive recovery record are defined in
[Container preparation](../01_Documentation/Container_Preparation.md).
Malformed external source, JSON, identity, receipts or persisted evidence fails
closed. Successful resume requires the original plan, image/container IDs and
intact immutable receipts; ordinary retry cannot replay partial setup.

## Direct verification integration

Configured direct verification reuses the bound container argv operation as
`["sh", "-c", command]` from the container worktree; immutable resource admission
and verified timeout recovery are unchanged. Native direct verification uses the
separate `LocalTarget.run_verification` operation, never ordinary native shell
argv. The conductor supplies the validate override/general timeout and owns the
sanitized durable result and bounded fix accounting. AEGIS never uses this
command. See `Component_Local_Execution.md` for the verification-only native
shell authority and opt-in true-tail capture; other transports keep prefix mode.

## 7. Workflow Integration

Plan resolution precedes worktree creation and setup. Provision/tool checks/auth
staging precede setup; setup precedes every AEGIS/AI gate. CLI/GUI use the same
plan resolver. Host and explicit model checks normalize the image without running
project preparation. Owned cancel/delete boundaries preserve shared caches/images.

## 8. Usage

See `config plan`, reviewed `execution.preparation` selection and explicit
`retry --reprepare` in [Container preparation](../01_Documentation/Container_Preparation.md).

## 9. Validation And Tests

Focused offline contract proof: `tests/test_execution.py and tests/test_preparation_lifecycle.py`. Source and runtime boundaries are
injected; no real Git/container/model/forge acceptance runs in these tests.

## 10. Limitations And Future Work

Container and native local adapters are enabled. ADORE builds no images:
container images are managed outside it.
Recipes are the published subset, not general Actions compatibility. Interrupted
setup needs operator inspection and explicit bounded replay, with retained
worktree partial effects and no exactly-once guarantee.

Preparation transport checks owned directory containment and linked parents before creating files, and checks result ownership before retaining evidence.

## Native execution contract

ExecutionBackend has ContainerBackend and LocalBackend implementations. Native targets use run_files and native worktree/IO paths. Container controls refuse native identities before any manager call; native controls verify pinned runtime/launch scope. Preparation remains container-only.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused native proof:
`04_Software/tests/test_local_execution.py`.

Native AEGIS stdout preserves the established 4 MiB JSON exchange bound; gate
stdout, stderr and questions remain bounded at 64 KiB. Native stream decoding
rejects invalid UTF-8; truncated JSON cannot become successful AEGIS evidence.
The shared drain retains container defaults. Saved local readiness checks reuse
approved profile .env values in memory through the same native environment.

## Agent-controlled system packages

ContainerBackend.authorize_system_packages verifies pinned container/image identity, then addresses the immutable container ID. The package authorization path is container-only and distinct from recipe execution. See [Package permissions](Component_Package_Permissions.md) and the operator dependency-installation guide.

## Verified container timeout recovery

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


The Pi launcher forwards a validated explicit thinking level to both native and container RPC processes; blank leaves Pi default.


## Concurrent resource ownership

Every run process owns a fresh mutable backend/executor. Bound container targets
copy their environment and identity pins, so later caller mutations do not affect
another launch. Stop/interrupt/removal address observed immutable container IDs
and reject changed saved pins. Full executor/proxy/network cleanup is the
conductor's path-bound `release_owned` operation; backend-only executor removal
does not infer egress ownership from a name. Native targets retain run-owned
receipts and isolated Pi temporary settings.

Focused proof: `04_Software/tests/test_shared_resources.py` and the component’s existing offline contracts.
