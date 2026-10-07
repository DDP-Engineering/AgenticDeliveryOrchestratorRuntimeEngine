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

Only the container adapter is enabled. Local execution (#21) supplies backend-native
transport; image building (#22) supplies separate verified image/build identity.
Recipes are the published subset, not general Actions compatibility. Interrupted
setup needs operator inspection and explicit bounded replay, with retained
worktree partial effects and no exactly-once guarantee.

Preparation transport checks owned directory containment and linked parents before creating files, and checks result ownership before retaining evidence.
