# Component: Execution backend

## Purpose and sources

`04_Software/adore/execution.py` defines `ExecutionPaths`, `ExecutionTarget`
and `ExecutionBackend`, implements `ContainerBackend`/`BoundTarget` and runs
container preparation steps. Native execution implements the same backend
contract in [Local execution](Component_Local_Execution.md).

The backend owns exact resource identity, bound commands and process settlement.
The conductor owns order, budgets, lifecycle, recovery and publication.

## One pinned execution model

Every admitted container or local job has a validated closed plan and explicit
resource lifecycle. A container without a recipe still resolves its local image
ID, records/verifies the container and image IDs and binds commands to that
identity. Disabled preparation is a complete not-required record with zero
attempts and empty step/history evidence, never an empty execution mapping.

Backend operations include provision, bind, tool checks, identity inspection and
owned stop/interrupt/remove. `BoundTarget` copies environment and identity pins;
caller mutation cannot retarget another launch. Container commands and spawns
address the observed immutable container ID after ownership checks. Backend
controls reject other-backend resource shapes before runtime effects.

Paths/shell and generated executor settings belong to the bound target. Native
AEGIS uses run_files; both native and container Pi use the shared RPC launcher.
Direct and AEGIS share the same owned target. There is no independent Direct
verification operation. See [Preparation](Component_Preparation.md) and
[Executor launcher](Component_Executor_Launcher.md).

## Preparation runner

`run_preparation_step` transmits file scripts and validates bounded receipts.
`preparation_runner.py` drains redacted stdout/stderr and enforces process-group
timeouts. Input/output locations require owned containment and regular unlinked
parents/files before evidence is retained. Unknown schema, corrupt JSON, identity
mismatch or incomplete results raise typed errors rather than implying success.

Provision, tool checks and auth staging precede setup; setup precedes agent stages.
Resume uses the saved execution settings, plan/resource IDs and intact immutable step evidence.
New project defaults do not replace a job backend, model, image or network. Live approval
and forge authority remain current; resource identity drift still fails closed.
Ordinary Retry cannot replay partial setup. Explicit `retry --reprepare` authorizes
bounded replay in a fresh owned container while retaining worktree effects.
See [Container preparation](../01_Documentation/Container_Preparation.md).

Preparation requires Python 3 and POSIX sh in the selected image. Local plans
have no preparation steps. Preview/host/model checks resolve the effective plan
without running project preparation.

## Timeout recovery

Bound container commands use authoritative runner timeout evidence. On an actual
timeout, the backend rechecks identity, interrupts within bounds and requires the
same container/image in exited state before returning the original CommandResult.
An ordinary exit 124 does not trigger recovery.

The next bound command or normal provision starts and verifies that same
resource. Its filesystem, installed dependencies, configured user and egress
remain; in-memory child processes do not. No replacement container or image pull
is an automatic timeout repair. `BoundTarget.spawn` uses the same admission;
`settle_timeout` quiesces RPC descendants before deferred reuse.

Unconfirmed stop/start or changed identity raises `ExecutionRecoveryError` and
blocks further commands/spawns in that backend. The conductor records exhausted
infrastructure without another agent attempt; pending cancellation wins.
Explicit stop/interrupt/remove cancels pending restart. Failed admission requires
operator inspection and a fresh controller, not guessing from resource names.

## Package authority, secrets and cleanup

`authorize_system_packages` is container-only and verifies the pinned container
and image before addressing the immutable ID. Permission does not imply recipe
success or installed-package evidence. See [Package permissions](Component_Package_Permissions.md).

Plans contain non-secret policy and fingerprints; credentials stay in explicitly
bound environment/context. Operational output is masked separately from literal
session recordings. Backend-only executor removal does not infer ownership of
proxy/network companions. Full release is the conductor's path-bound operation;
shared caches/images remain outside per-job deletion.

## Validation coverage and limits

Existing offline tests under `04_Software/tests/` include `test_execution.py`,
`test_preparation_lifecycle.py`, `test_container_timeout.py`,
`test_local_execution.py` and `test_shared_resources.py`. They inject Git/runtime
and process boundaries; no real forge, provider or container is needed.

Project-specific images are prepared externally. Shared base/proxy prerequisite
preparation has a separate checked setup boundary. Interrupted project setup may
leave worktree side effects; there is no exactly-once installation guarantee or
stored-format conversion.
