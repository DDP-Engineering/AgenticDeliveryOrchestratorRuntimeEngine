<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Executor configuration and credentials

## 1. Purpose

Provide a single project executor/model workspace and protected provider key lifecycle. Persist current model access evidence independently of host/tool readiness.

## 2. Responsibilities

`web/executor_settings.py` validates private profile inputs, edits one approved .env variable atomically, and binds/loads model evidence. `web/app.py` owns roles, CSRF, immutable project selection, configuration/conductor locks and audit attempts/confirmations. The existing config candidate and launcher own applied TOML changes and actual job injection.

## 3. Implementation Overview

The settings panel embeds Provider credentials beneath its categories. ModelConnection supplies the Executor configuration heading with Test AI connection aligned right, and scoped result/cost guidance below. The native heading layout wraps on narrow screens. Default coding agent Edit uses configured executor choices. Launch-command Edit selects exact documented standard OpenCode/Pi/Codex/Qwen presets for existing command tables; a custom current command stays visible as a disabled current option until a preset is selected. Prepare stays disabled for values outside the catalog. app.py validates command presets at staged/direct edits and persisted review/apply, retaining administrator/CSRF/revision/idle/pause/locking safety. Container custom commands and new table enrollment belong to host TOML. Local existing command tables accept validated installed argv through reviewed candidates.

The Executor configuration route selects executor settings, model identifiers and the applicable OpenCode endpoint form. Administrator edits use the existing Prepare candidate / Apply / Discard workflow. Configured command tables determine the selectable executors; model IDs are entered manually. Developers read non-secret settings/results.

Save API key / Disconnect project API key operate on the selected profile's `.env`. `executor.env_keys` is the authoritative existing allowlist; the form offers known provider API names already in it. Ambient variables (including explicitly empty values) take precedence and are managed externally. Source indicators distinguish missing, project and environment. Saving is not authentication success; explicit Test AI connection provides that evidence.

## 4. Dependencies

Standard library filesystem/JSON/hash functions; existing ProfileStore, StateStore/config edit guards, WebStore audit, ContainerManager/model diagnostic, React and same-origin API. No new dependency or SQLite schema.

## 5. Inputs And Outputs

GET `/api/v1/projects/{identity}/executor-credentials` (Admin) returns `{project_id, revision, variables:[{name, source}]}`.
PUT takes exact `{revision, variable, token}`; DELETE exact `{revision, variable}`. Monitoring must be paused, state valid and idle, with no pending configuration/operations. Archived projects reject mutations. Return values contain no key or credential digest. Authentication errors have stable value-free codes.

Config GET includes `model_connection`, a current public result or null. Model test POST stores and returns the same closed result. Summary displays current access only in expanded host-check details; host-check AI access uses that result when present. A separately performed OpenCode endpoint/tool-stream check remains separately identified and retains its verdict.

## 6. Data Contracts

Provider keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY, DASHSCOPE_API_KEY, AZURE_OPENAI_API_KEY, MISTRAL_API_KEY, XAI_API_KEY, GROQ_API_KEY. Membership also requires the project's executor allowlist. Variable names do not promise provider/model availability in an installed CLI.

Dotenv reads are bounded to 64 KiB, reject symlinks, duplicate names, malformed lines, invalid UTF-8/control characters and unbalanced surrounding quotes. Atomic same-directory replacement preserves other lines; generated files have legal headers, POSIX mode 0600 and fsync before rename. The existing launcher consumes this same profile environment with ambient precedence; active job environments remain unchanged.

`model-connection.json` is schema 1: exact public fields project_id/revision/checked_at/executor/model/ready/reason plus internal schema/binding. The 64-character SHA256 binding covers effective allowlisted secrets and recognized OpenCode/Codex host-auth / Pi/Qwen volume auth files. Exact field sets, types, identity, UTC time, model grammar and ready/reason consistency are checked before staleness. Duplicate/foreign/corrupt evidence produces 503. Config/credential drift returns null. GUI credential mutations remove previous model evidence, preventing revival after a key is removed/restored. Test rechecks identity/config/binding after execution and validates output before atomic evidence publication.

## 7. Workflow Integration

New jobs load applied executor/model settings. Existing jobs retain their durable configuration; web guards reject applying changes during active work. Browser credentials remain in component memory and clear on mutation attempt/unmount. Audit records the attempt before a filesystem change and confirmation afterward; no secret values are recorded. Interrupted changes retain uncertainty rather than invented success.

## 8. Usage

Open Project → Executor configuration. Prepare/apply the model/default executor change, pause monitoring for credential changes, choose an allowed API variable and Save API key. Test AI connection explicitly, then inspect Summary/check details. A provider key can use separate API billing from a subscription.

Subscription login remains the installed CLI's real interactive service-account flow: OpenCode `opencode auth login`, Codex `codex login`, Pi `/login`, Qwen `/auth`. Container OpenCode/Codex use the configured host-auth bridge; container Pi/Qwen need the protected auth directory/file bind available to actual containers. CLI version and provider determine the login flow. The GUI key removal changes only that project variable; it leaves ambient credentials and subscription sessions intact.

Official provider references: [Pi](https://pi.dev/docs/latest/providers), [Qwen](https://qwenlm.github.io/qwen-code-docs/en/users/configuration/auth/), [OpenCode](https://opencode.ai/docs/providers/), [Codex](https://developers.openai.com/codex/auth).

## 9. Validation And Tests

`tests/test_web_launch_presets.py`: four-executor candidate apply, arbitrary/missing/unknown command, stale/CSRF/role/pause and tampered-pending rejection. `tests/test_executor_settings.py`: all-executor private save/remove, preserved unrelated bytes, CSRF/role/lock/pending/pause/ambient/config/env/evidence negatives, persisted result across host check and credential drift, corrupt/foreign/duplicate evidence. `test_model_connection.py` retains real offline diagnostic contracts. `web/e2e/executor-config.spec.ts` owns tab/credential/candidate/Settings separation; model-connection and settings journeys prove scoped results/defaults. Real provider/whole-job acceptance is operator-triggered.

## 10. Limitations

Model lists, new command-table enrollment and a universal browser OAuth broker are outside this workspace. API-variable allowlists/custom providers are configured in the project profile. Only recognized auth mounts are fingerprinted; opaque external credential sources still require an explicit fresh test. Connectivity does not prove tool support, Git publication or a complete job. Full regression remains deferred during the user's iterative live changes.

## Native execution contract

Local installed native argv is editable through validated reviewed candidates. Container editors retain standard presets. Subscription login stays external; local stores are reused in place. Protected provider edits/current model evidence keep project-bound contracts.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused proof:
`04_Software/tests/test_local_execution.py`.
