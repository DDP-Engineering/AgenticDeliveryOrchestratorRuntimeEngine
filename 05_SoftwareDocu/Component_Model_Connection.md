<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Model connection diagnostic

## 1. Component Overview

Explicit administrator AI connection testing through Pi, ADORE's only coding agent. The saved `executor.model` is called once in an empty temporary workspace: in a temporary container for a container project, or through the installed native Pi for a local project.

## 2. Responsibilities

Bound execution, require a completed nonce response, redact output and clean resources. Readiness has no model endpoint check; this explicit test is the only model-access evidence. This diagnostic changes no job or configuration.

## 3. Public Interfaces

`probe_model_connection(config, runner, env_file)` returns executor/model/ready/reason. POST `/api/v1/projects/{identity}/model-connection-test` requires administrator session/CSRF, nonarchived idle project, valid state and no pending configuration/operations. Configuration/conductor locks and snapshot rechecks bind evidence to immutable project identity and configuration revision. Monitoring need not be paused.

## 4. Dependencies

ContainerManager uses the project's local image, runtime, cache volumes, operator run arguments and egress. The image must contain Python and Pi. Images are inspected locally and never pulled.

## 5. Inputs And Outputs

Executor secrets use selected profile `.env` plus ambient environment precedence, with the configured env-key allowlist. No host sign-in is staged into the container. Core repo/work/io mounts contain temporary empty directories; trusted operator run arguments retain their configured semantics. Forge connection tokens are not staged.

## 6. Data Contracts

API evidence adds project_id, SHA-256 revision and UTC checked_at. GUI accepts exact current project/executor/model/revision. Reasons: ready, timeout, image-missing, cli-missing, credential-invalid, model-unavailable, connection-failed, invalid-response, runtime-error, tool-call-failed. The pure frontend module `web/src/modelEvidence.ts` holds the reason set, `validModelEvidence`, the four-locale copy and `modelGuidance`. Duplicate fields, malformed output, wrong nonce or missing completion fail closed; observed tool calls fail closed in containers, while native Pi must show one successful shell call. `executor_settings.REASONS` is the same set as `model_connection.REASONS`, so persisted evidence accepts every probe reason. Raw stdout/stderr is never returned.

## 7. Workflow Integration

Settings → Agent and model offers Test AI connection at the panel heading right, alongside the settings and project API keys; Summary shows the current saved model result only inside expanded host-check details. Each explicit click can incur provider charges. Container inference is capped at 45 seconds and the native gate at 90 seconds; container combined output is capped at 1 MiB (local stdout also at 1 MiB through `LocalTarget.output_limit`, local stderr at 64 KiB); setup/inference share a 90-second deadline, followed by cleanup commands capped at 8 seconds each. Cleanup failures become API errors.

## 8. Usage

Save executor/model credentials as for normal execution, ensure its local image is available, then click Test AI connection. The container challenge runs `pi -p --mode json --no-session --no-tools --no-extensions --no-skills --no-prompt-templates` and asks for a no-tool nonce reply. Local diagnostics use the configured native `executor.command` and account environment.

## 9. Validation And Tests

`tests/test_model_connection.py` fakes external runtime/subprocess boundaries while executing the actual Pi diagnostic script. It covers happy response, malformed output, nonce/tool violations, timeout/cleanup, CSRF/role/lock/corrupt/stale configuration. Browser proof: `web/e2e/model-connection.spec.ts` explicit invocation, cost notice and stale evidence rejection. Existing host-readiness tests prove separation.

## 10. Limitations

A container response proves no tool capability; a native Pi result proves one shell call. Neither proves Git push permission, AEGIS execution or complete job. Current results are persisted in model-connection.json by executor_settings.py, validated against immutable identity/configuration/credential inputs, and reused by Summary and host-check access presentation. Stale results are suppressed and corrupt results rejected. See Component_Executor_Configuration.md for storage/auth contracts. Full regression is deferred during iterative GUI work; real paid provider checks remain operator-triggered acceptance.

## Effective preparation image

Explicit model connection resolves the selected Git recipe through its bounded runner and uses the normalized effective image. Stale/corrupt source yields a failed result before any container setup. No project recipe command runs in the disposable connectivity workspace.

## Native execution contract

Native challenges use local_probe and the same configured argv/account/environment as gates, with a 90-second gate bound and verified scope cleanup. The prompt asks for `echo <ADORE_TOOL nonce>` and then the exact reply; `_native_tool_response` requires Pi's successful shell event carrying that nonce (otherwise `tool-call-failed`) and then the completed reply (otherwise `invalid-response`), per `.agentic/specs/REQ-FUNC-8f369d55.md`. No login or complete-job claim; container diagnostics keep fixed commands.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused native proof:
`04_Software/tests/test_local_execution.py`.
