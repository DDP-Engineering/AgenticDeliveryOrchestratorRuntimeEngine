<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Select native local execution with pinned machine account policy

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-FUNC-5e2fe079](../requirements/functional/REQ-FUNC-5e2fe079.toml) — Preserve native local gate and AEGIS file evidence

For each local gate ADORE shall launch the managed Pi as a fresh native RPC process in the dedicated worktree and retain existing questions/results, authoritative exit/timeout, usage coverage, immutable archives and AEGIS journal/approval contracts.

Verification scope: Offline launcher/AEGIS tests observe paths and prompts with spaces, questions, usage and archives and negative nonzero, timeout and corrupt output boundaries; Windows background children explicitly forward both parent-owned streams, including nonzero exit and pre-release cancel cases. Native Python producers retain Unicode with authoritative UTF-8 settings on Windows/Linux despite ambient encoding overrides; invalid evidence remains refused.

### [REQ-FUNC-ffb9ed29](../requirements/functional/REQ-FUNC-ffb9ed29.toml) — Select native local execution with pinned machine account policy

For an explicit local profile ADORE shall provision only a dedicated worktree/native target, pin backend and machine/account/environment identity, preserve default container behavior and reject incompatible recipes, a container egress allowlist or drift before executing host project commands.

Verification scope: Offline config/plan and conductor tests observe explicit local selection with no container calls and refusal on incompatible settings or identity drift.

### [REQ-REL-50474528](../requirements/reliability/REQ-REL-50474528.toml) — Control only verified local process trees during recovery

When local commands time out, cancel, park or recover, ADORE shall control only a verified run-owned native process scope with durable machine/run/PID-birth/scope identity, fail closed on corrupt or reused evidence and preserve archives/worktrees until explicit cleanup.

Verification scope: Injected Windows/Linux process-control tests observe full owned-scope termination and typed refusal for reused PID, scope drift, malformed lease and failed control.

### [REQ-SEC-f7b9111e](../requirements/security/REQ-SEC-f7b9111e.toml) — Inject approved native provider credentials

For native execution ADORE shall pass the current account environment through an explicit allowlist and inject the configured provider credentials, exclude forge credential variables and redact known secrets before operational evidence while retaining literal bounded job-session recordings without copying credentials or initiating login.

Verification scope: Offline environment/auth tests observe allowlisted native account/home and approved credential injection, reject a forged account or unsupported executable, and prove secret absence from operational outputs and presence in literal bounded session recordings when printed.

### [REQ-UX-b75e1df8](../requirements/ux/REQ-UX-b75e1df8.toml) — Configure and check local execution with user-owned tooling notice

When configuring or checking a local project ADORE shall use the selected native backend for basic executor/auth and explicit model checks, state its actual machine/account and user-owned tooling/host security responsibility, and omit machine/backend/environment identity from portable working rules.

Verification scope: Offline CLI/setup/web/frontend checks observe backend-specific selection/notices and same-environment probes without container/tool-install calls, with unauthorized/invalid/stale inputs refused.

## Implementation

- `04_Software/adore/aegis.py`
- `04_Software/adore/cli.py`
- `04_Software/adore/config.py`
- `04_Software/adore/execution.py`
- `04_Software/adore/executor/launcher.py`
- `04_Software/adore/local_child.py`
- `04_Software/adore/local_execution.py`
- `04_Software/adore/local_process.py`
- `04_Software/adore/orchestrator.py`
- `04_Software/adore/portable_settings.py`
- `04_Software/adore/preparation.py`
- `04_Software/adore/preparation_runner.py`
- `04_Software/adore/state.py`
- `04_Software/adore/web/app.py`
- `04_Software/adore/web/model_connection.py`
- `04_Software/adore/wizard.py`
- `04_Software/web/e2e/enrollment.spec.ts`
- `04_Software/web/src/App.tsx`
- `04_Software/web/src/EnrollmentWizard.tsx`
- `04_Software/web/src/ExecutionPlanReview.tsx`
- `04_Software/web/src/ReadinessEvidence.tsx`
- `04_Software/web/src/executionPlan.ts`
- `04_Software/web/src/localExecution.ts`
- `04_Software/web/src/readiness.ts`
- `04_Software/web/src/settingHelp.ts`
- `04_Software/web/src/settingKeys.json`
- `04_Software/web/src/settings.ts`
- `04_Software/web/tests/executionPlan.test.mjs`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_local_execution.py::test_container_adapter_refuses_local_identity_before_cli`
- `04_Software/tests/test_local_execution.py::test_linux_control_checks_delegated_scope_identity_before_kill`
- `04_Software/tests/test_local_execution.py::test_local_aegis_file_transport_uses_native_argv`
- `04_Software/tests/test_local_execution.py::test_local_aegis_preserves_the_existing_json_exchange_bound`
- `04_Software/tests/test_local_execution.py::test_local_child_release_barrier_and_cancel_are_native`
- `04_Software/tests/test_local_execution.py::test_local_conductor_pins_target_parks_retries_and_never_lists_containers`
- `04_Software/tests/test_local_execution.py::test_local_environment_ignores_personal_auth_and_forge_credentials`
- `04_Software/tests/test_local_execution.py::test_local_environment_keeps_windows_system_names`
- `04_Software/tests/test_local_execution.py::test_local_model_challenge_uses_the_managed_rpc_installation`
- `04_Software/tests/test_local_execution.py::test_local_native_settings_accept_tools_path_and_refuse_launch_overrides`
- `04_Software/tests/test_local_execution.py::test_local_node_entrypoint_drift_refuses_execution`
- `04_Software/tests/test_local_execution.py::test_local_output_refuses_corrupt_retained_evidence`
- `04_Software/tests/test_local_execution.py::test_local_portable_export_excludes_all_native_settings`
- `04_Software/tests/test_local_execution.py::test_local_readiness_never_invokes_container_tools`
- `04_Software/tests/test_local_execution.py::test_local_review_apply_rechecks_native_identity_and_permissions`
- `04_Software/tests/test_local_execution.py::test_local_scope_control_refuses_reused_process_identity`
- `04_Software/tests/test_local_execution.py::test_local_selection_is_explicit_and_rejects_container_contracts`
- `04_Software/tests/test_local_execution.py::test_native_gate_uses_managed_rpc_and_ignores_hostile_personal_pi`
- `04_Software/tests/test_local_execution.py::test_native_python_utf8_overrides_ambient_encoding`
- `04_Software/tests/test_local_execution.py::test_native_unicode_python_evidence_survives_capture`
- `04_Software/tests/test_retry_revalidation.py`
- `04_Software/tests/test_web_executor_session.py::test_rpc_producer_keeps_literal_live_and_archive_but_masks_operations`
- `04_Software/web/e2e/enrollment.spec.ts`
- `04_Software/web/tests/executionPlan.test.mjs`
