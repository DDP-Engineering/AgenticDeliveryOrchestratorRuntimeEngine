<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Preparation component

## 1. Purpose

Resolve closed reviewed preparation plans before executable project effects.

## 2. Responsibilities

`parse_selection`, `parse_recipe`, `resolve_plan`, `validate_plan`, `preview_plan`, `public_plan` and `effective_probe_config` validate exact Git source, image precedence, fixed-depth grammar, closed persisted policy and non-secret SHA-256 identity. Every job is validated; unsupported syntax raises `PreparationError`. Configuration apply and the conductor share this authority.

## 3. Implementation Overview

Typed selection → exact regular Git blob → complete grammar validation → normalized fingerprinted plan. No install, fetch, model call or image pull occurs in preview.

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
staging precede setup; setup precedes every AEGIS/AI gate. CLI plan preview and runtime checks use the same
plan resolver. Host and explicit model checks normalize the image without running
project preparation. Owned cancel/delete boundaries preserve shared caches/images.

## 8. Usage

See `config plan`, reviewed `execution.preparation` selection and explicit
`retry --reprepare` in [Container preparation](../01_Documentation/Container_Preparation.md).

## 9. Validation And Tests

Focused offline contract proof: `tests/test_preparation.py`. Source and runtime boundaries are
injected; no real Git/container/model/forge acceptance runs in these tests.

## 10. Limitations And Future Work

Only the container adapter is enabled. Local execution (#21) supplies backend-native
transport; ADORE builds no images, container images are managed outside it.
Recipes are the published subset, not general Actions compatibility. Interrupted
setup needs operator inspection and explicit bounded replay, with retained
worktree partial effects and no exactly-once guarantee.

## Native execution contract

Local plans use backend=local, empty image/selection/steps and image_source=local. Closed local policy fingerprints machine/account/environment/executable without commands. Container policy keys and fingerprints retain their established shape.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused native proof:
`04_Software/tests/test_local_execution.py`.

## Agent-controlled system packages

Enabled container policies carry canonical system_packages=true; disabled policies omit the field, preserving legacy fingerprints. validate_plan rejects noncanonical booleans and unknown fields. Optional recipe parsing and commands retain their contracts. See [Package permissions](Component_Package_Permissions.md) and the operator dependency-installation guide.
