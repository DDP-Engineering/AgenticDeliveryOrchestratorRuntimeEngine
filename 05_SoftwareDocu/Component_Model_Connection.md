<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Model connection diagnostic

## 1. Component Overview

Explicit administrator AI connection testing for all implemented executors: OpenCode, Pi, Codex and Qwen. The saved model is called once through a backend-specific CLI command in an empty temporary workspace.

## 2. Responsibilities

Bound execution, require a completed nonce response, redact output and clean resources. Host readiness retains its separate automatic OpenCode endpoint/tool-call contract. This diagnostic changes no job or configuration.

## 3. Public Interfaces

`probe_model_connection(config, runner, env_file)` returns executor/model/ready/reason. POST `/api/v1/projects/{identity}/model-connection-test` requires administrator session/CSRF, nonarchived idle project, valid state and no pending configuration/operations. Configuration/conductor locks and snapshot rechecks bind evidence to immutable project identity and configuration revision. Monitoring need not be paused.

## 4. Dependencies

ContainerManager uses the project's local image, runtime, cache volumes, operator run arguments and egress. The image must contain Python and the configured agent. Images are inspected locally and never pulled.

## 5. Inputs And Outputs

Executor secrets use selected profile `.env` plus ambient environment precedence, with the configured env-key allowlist. Optional OpenCode/Codex host-auth staging matches production. Core repo/work/io mounts contain temporary empty directories; trusted operator run arguments retain their configured semantics. Forge connection tokens are not staged.

## 6. Data Contracts

API evidence adds project_id, SHA-256 revision and UTC checked_at. GUI accepts exact current project/executor/model/revision. Reasons: ready, timeout, image-missing, cli-missing, credential-invalid, model-unavailable, connection-failed, invalid-response, runtime-error. Duplicate fields, malformed output, wrong nonce, missing completion or observed tool calls fail closed. Raw stdout/stderr is never returned.

## 7. Workflow Integration

Executor configuration offers Test AI connection at the panel heading right, alongside the settings and embedded Provider credentials; Summary shows the current saved model result only inside expanded host-check details. Each explicit click can incur provider charges. Inference is capped at 45 seconds and container combined output at 1 MiB (local streams at 64 KiB each); setup/inference share a 90-second deadline, followed by cleanup commands capped at 8 seconds each. Cleanup failures become API errors.

## 8. Usage

Save executor/model credentials as for normal execution, ensure its local image is available, then click Test AI connection. Fixed diagnostic flags deny OpenCode tools; disable Pi tools/extensions/skills/templates; use Codex ephemeral/read-only sessions without plugins; restrict Qwen core tools and use plan approval. Compatible installed CLI versions are required; container custom project command templates are not used. Local diagnostics use configured native argv/account environment.

## 9. Validation And Tests

`tests/test_model_connection.py` fakes external runtime/subprocess boundaries while executing all four actual diagnostic scripts. It covers happy response, malformed output, nonce/tool violations, timeout/cleanup, CSRF/role/lock/corrupt/stale configuration. Browser proof: `web/e2e/model-connection.spec.ts` explicit invocation, cost notice and stale evidence rejection. Existing host-readiness tests prove separation.

## 10. Limitations

A model response proves no tool capability, Git push permission, AEGIS execution or complete job. Current results are persisted in model-connection.json by executor_settings.py, validated against immutable identity/configuration/credential inputs, and reused by Summary and host-check access presentation. Stale results are suppressed and corrupt results rejected. See Component_Executor_Configuration.md for storage/auth contracts. Full regression is deferred during iterative GUI work; real paid provider checks remain operator-triggered acceptance.

## Effective preparation image

Explicit model connection resolves the selected Git recipe through its bounded runner and uses the normalized effective image. Stale/corrupt source yields a failed result before any container setup. No project recipe command runs in the disposable connectivity workspace.

## Native execution contract

Native nonce challenges use local_probe and the same configured argv/account/environment as gates, with 45-second inference and verified scope cleanup. Incomplete/malformed/wrong-nonce/tool-bearing events fail closed. No login or complete-job/tool-acceptance claim; container diagnostics keep fixed commands.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused native proof:
`04_Software/tests/test_local_execution.py`.

## Native completion and failure classification

The configured native command/account/environment remains authoritative. A
completed exact OpenCode nonce text part with finite positive `time.end` and
optional finite nonnegative `time.start <= end`, followed by clean process exit,
proves the short access challenge even if `step_finish` was omitted. Plain text
without completion evidence, wrong nonce, duplicate/invalid JSON, invalid parts,
error events and tool events or a tool-calls finish never become success.
Typed OpenCode provider/model errors and HTTP authentication failures are mapped
to `credential-invalid`, `model-unavailable` or `connection-failed`, including
structured error events emitted with exit zero. Output stays bounded/redacted;
no raw provider response enters the saved result. Missing native executable and
corrupt auth are classified explicitly. Container probe behavior is retained.
