<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Preparation planning

## Purpose and source ownership

`04_Software/adore/preparation.py` resolves one reviewed execution plan before
project execution. It owns selection/recipe parsing, image precedence, closed
policy validation and non-secret plan fingerprints. The backend executes the
plan; the conductor owns recovery and authorization to replay it.

## Public contract and processing

`parse_selection`, `parse_recipe`, `resolve_plan`, `validate_plan`, `preview_plan`,
`public_plan` and `effective_probe_config` share the same normalized authority.
Resolution follows typed configuration → exact regular Git blob where selected
→ complete grammar validation → fingerprinted plan. Preview performs no install,
fetch, model call or image pull.

Every job receives a plan. Containers can select the published bounded recipe
subset or no recipe; local plans use backend=local, image_source=local and empty
image/selection/steps. Preparation commands execute only in containers. A local
backend being available does not make container recipe steps native commands.

The closed version-1 grammar, limits and source/image precedence are specified in
[Container preparation](../01_Documentation/Container_Preparation.md).
Unsupported syntax, changed source, invalid image identity, unknown keys or
corrupt persisted evidence raise `PreparationError`/the caller's typed refusal.
No earlier-plan reader or automatic rewriting is supplied.

## Policy and persisted evidence

The plan binds complete non-secret execution policy: backend, selected image and
source, provider/model/endpoint, thinking, internet/search, command preset and
additional credential names, plus backend-specific native identity where relevant.
Secret values never enter policy/fingerprints. Changes to pinned authority require
a fresh job rather than a silent Retry update.

Enabled container system-package policy carries canonical system_packages=true;
disabled policy omits that field. Unknown or noncanonical values are refused.
Recipe selection and package-install permission are separate operations.
See [Package permissions](Component_Package_Permissions.md).

The closed run execution record includes the validated plan even when preparation
is disabled. Not-required status has zero attempts and empty step/history evidence.
Resource identity is recorded after provisioning. Resume verifies the original
plan, image/container IDs and immutable receipts. A corrupt record is refused with
explicit affected-store removal guidance, never completed with defaults.

## Integration and limits

CLI `config plan`, configuration review/apply, readiness and the conductor share
the resolver. Provision/tool checks/auth staging precede setup; successful setup
precedes agent work. Host/model diagnostics normalize the selected image without
executing project preparation. Explicit `retry --reprepare` is the bounded replay
authorization; ordinary Retry cannot repeat partially applied steps.

Project recipes cover the documented subset, not a general CI workflow engine.
Interrupted steps can leave retained worktree effects and require operator
inspection. Project-specific image building is external; shared runtime prerequisite
preparation remains separate. See [Execution](Component_Execution.md) and
[Project images](Component_Project_Images.md).

## Dependencies and validation coverage

The planner uses standard-library parsing/hashing, typed configuration and injected
Git command execution. Existing `04_Software/tests/test_preparation.py`,
`test_preparation_lifecycle.py` and `test_local_execution.py` cover the public
planning and replay boundaries offline.
