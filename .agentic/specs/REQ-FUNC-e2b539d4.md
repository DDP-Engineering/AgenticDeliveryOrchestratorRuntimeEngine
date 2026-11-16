<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Resolve reviewed container preparation plans

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-FUNC-e2b539d4](../requirements/functional/REQ-FUNC-e2b539d4.toml) — Resolve reviewed container preparation plans

When an operator selects a repository recipe path, job and exact reviewed Git revision, ADORE shall resolve a complete immutable container execution plan using the closed version-1 preparation syntax and reject unsupported, ambiguous, unsafe, stale or conflicting input before executing project commands.

Verification scope: Offline plan tests observe normalized multiline steps/image/fingerprints from injected Git output and typed failures for unsupported YAML, traversal/symlink, stale revision, invalid CLI output and image conflict.

### [REQ-FUNC-e397f7f6](../requirements/functional/REQ-FUNC-e397f7f6.toml) — Route executor lifecycle through a shared execution backend

ADORE shall route container and native execution paths, provisioning, command/RPC launch, interruption and owned-resource removal through the shared execution-backend contract and the current pinned execution plan, preserving configured credentials, egress and candidate approval boundaries.

Verification scope: Offline backend/conductor/launcher cases observe current pinned-plan provisioning, RPC execution, parking, cancellation and owned cleanup with Docker, Podman and WSL runners.

### [REQ-FUNC-e5419c07](../requirements/functional/REQ-FUNC-e5419c07.toml) — Execute bounded preparation before executor gates

For a recipe-based container run, ADORE shall execute the pinned preparation steps sequentially in the gate container and worktree before the first executor launch, bounded by step and total run limits with fail-fast, redacted immutable outcome evidence.

Verification scope: Injected backend tests observe ordered setup and gate execution, multiline file transport, bounded output and time, and suppressed gates after exit failure, timeout or cancellation.

### [REQ-REL-d8fd134e](../requirements/reliability/REQ-REL-d8fd134e.toml) — Bind preparation recovery to immutable runtime identity

When recovering a recipe-based run, ADORE shall reuse successful preparation only for its exact plan, container and image identities, fail closed on interrupted or changed resources, and permit bounded full-step replay only after explicit operator acknowledgement while retaining earlier evidence.

Verification scope: Persist/load and injected runtime tests observe same-resource reuse, refusal on drift/corrupt/incomplete state and explicit bounded replay with prior attempts retained.

### [REQ-UX-94a97e70](../requirements/ux/REQ-UX-94a97e70.toml) — Review execution plans through project configuration

When an authorized operator previews or applies an execution selection through external server profile configuration or CLI, ADORE shall show the normalized effective image/source and preparation plan through CLI preview and read-only web metadata with side-effect-free readiness and visible run preparation evidence.

Verification scope: Offline CLI/web/frontend tests observe CLI plan preview/effective image/run evidence and reject unauthorized web environment mutations and invalid source; readiness executes no setup.

## Implementation

- `04_Software/adore/aegis.py`
- `04_Software/adore/cli.py`
- `04_Software/adore/config.py`
- `04_Software/adore/execution.py`
- `04_Software/adore/executor/base.py`
- `04_Software/adore/executor/launcher.py`
- `04_Software/adore/isolation.py`
- `04_Software/adore/orchestrator.py`
- `04_Software/adore/preparation.py`
- `04_Software/adore/preparation_runner.py`
- `04_Software/adore/state.py`
- `04_Software/adore/util.py`
- `04_Software/adore/web/app.py`
- `04_Software/adore/web/jobs.py`
- `04_Software/adore/web/model_connection.py`
- `04_Software/config.example.toml`
- `04_Software/web/e2e/server.py`
- `04_Software/web/e2e/settings.spec.ts`
- `04_Software/web/src/App.tsx`
- `04_Software/web/src/ExecutionPlanReview.tsx`
- `04_Software/web/src/JobWorkspace.tsx`
- `04_Software/web/src/executionPlan.ts`
- `04_Software/web/src/jobModel.ts`
- `04_Software/web/src/settingHelp.ts`
- `04_Software/web/src/settingKeys.json`
- `04_Software/web/src/settings.ts`
- `04_Software/web/src/settingsCopy.ts`
- `04_Software/web/tests/executionPlan.test.mjs`
- `04_Software/web/tests/settings.test.mjs`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_aegis.py::test_backend_paths_control_aegis_file_transport`
- `04_Software/tests/test_execution.py::test_container_identity_rejects_corrupt_or_foreign_resources`
- `04_Software/tests/test_execution.py::test_container_identity_reports_actual_container_and_image_ids`
- `04_Software/tests/test_execution.py::test_standalone_preparation_runner_bounds_output_and_process_lifetime`
- `04_Software/tests/test_execution.py::test_transport_rejects_linked_parents_before_creating_files`
- `04_Software/tests/test_orchestrator.py::test_recipe_preparation_precedes_ai_and_is_not_replayed_on_resume`
- `04_Software/tests/test_preparation.py::test_plan_pins_exact_source_image_and_policy_without_installing`
- `04_Software/tests/test_preparation.py::test_plan_rejects_corrupt_git_output`
- `04_Software/tests/test_preparation.py::test_readiness_uses_reviewed_effective_image_without_setup`
- `04_Software/tests/test_preparation.py::test_recipe_rejects_unsupported_ambiguous_and_excessive_input`
- `04_Software/tests/test_preparation_lifecycle.py::test_crashed_preparation_becomes_explicit_interrupted_evidence`
- `04_Software/tests/test_preparation_lifecycle.py::test_explicit_reprepare_recreates_owned_container_and_caps_replay`
- `04_Software/tests/test_preparation_lifecycle.py::test_setup_failure_retains_outcome_and_never_reaches_ai`
- `04_Software/tests/test_preparation_lifecycle.py::test_success_cannot_authorize_drifted_resources_or_configuration`
- `04_Software/tests/test_profile_cli.py::test_cli_previews_reviewed_plan_without_setup`
- `04_Software/tests/test_state.py::test_execution_state_is_required_and_closed`
- `04_Software/tests/test_util.py::test_command_preserves_crlf_bytes`
- `04_Software/tests/test_web_jobs.py::test_job_preparation_projection_is_closed_and_rejects_false_success`
- `04_Software/tests/test_web_pending_config.py::test_execution_setting_direct_write_requires_review`
- `04_Software/tests/test_web_pending_config.py::test_pending_candidate_for_an_external_key_is_corrupt_but_discardable`
