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

`web/executor_configuration.py` holds the reviewed Pi launch-command preset (`LAUNCH_PRESETS`); `web/implementation_settings.py` validates names-only lists. `web/executor_settings.py` validates private profile inputs, edits one approved .env variable atomically, and binds/loads model evidence. `web/app.py` owns roles, CSRF, immutable project selection, configuration/conductor locks and audit attempts/confirmations. The existing config candidate and launcher own applied TOML changes and actual job injection.

## 3. Implementation Overview

**Project → Settings → Agent and model** configures Pi, ADORE's only coding agent; there is no agent choice. It shows Test AI connection, the model (`executor.model`, an ordinary reviewed setting), the launch command (`executor.command`; a container project may choose only the one Pi preset, a local project edits validated native argv), allowed credential variables (`executor.env_keys`), project API keys, the execution environment (`execution.backend`, the container runtime and image, and the local account, home, PATH and cgroup root for local projects, with external container guidance) and estimated prices. Model, command, backend, runtime and image edits go only through the reviewed flow (prepare candidate, review, apply); a new model ID must be supplied explicitly. Credential names are added through a dropdown and remain visible as individually removable selections. While the image row is edited it offers the same server image suggestions. Installed agents and runtime preparation remain external. The old `/executor` URL redirects to Settings. Developers read non-secret settings/results without mutation actions.

The names-only credential selector offers known provider names and retained custom names. An empty list (`env_keys = []`) suits a local project that uses the account's own Pi sign-in. Applying names does not delete saved `.env` values. Project API keys offers private Save/Disconnect for known allowed variables and shows sources only; key changes require paused pickup and idle/pending-free state. Explicit Test AI connection remains the evidence of model access and may incur provider charges.

Save API key / Disconnect project API key operate on the selected profile's `.env`. `executor.env_keys` is the authoritative existing allowlist; the form offers known provider API names already in it. Ambient variables (including explicitly empty values) take precedence and are managed externally. Source indicators distinguish missing, project and environment. Saving is not authentication success; explicit Test AI connection provides that evidence.

## 4. Dependencies

Standard library filesystem/JSON/hash functions; existing ProfileStore, StateStore/config edit guards, WebStore audit, ContainerManager/model diagnostic, React and same-origin API. No new dependency or SQLite schema.

## 5. Inputs And Outputs

GET `/api/v1/projects/{identity}/executor-credentials` (Admin) returns `{project_id, revision, variables:[{name, source}]}`.
PUT takes exact `{revision, variable, token}`; DELETE exact `{revision, variable}`. Monitoring must be paused, state valid and idle, with no pending configuration/operations. Archived projects reject mutations. Return values contain no key or credential digest. Authentication errors have stable value-free codes.

Config GET includes `model_connection`, a current public result or null. Model test POST stores and returns the same closed result. Summary displays current access only in expanded host-check details; host-check AI access uses that result when present. Readiness has no separate model endpoint check.

## 6. Data Contracts

Provider keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY, DASHSCOPE_API_KEY, AZURE_OPENAI_API_KEY, MISTRAL_API_KEY, XAI_API_KEY, GROQ_API_KEY. Membership also requires the project's executor allowlist. Variable names do not promise provider/model availability in an installed CLI.

Dotenv reads are bounded to 64 KiB, reject symlinks, duplicate names, malformed lines, invalid UTF-8/control characters and unbalanced surrounding quotes. Atomic same-directory replacement preserves other lines; generated files have legal headers, POSIX mode 0600 and fsync before rename. The existing launcher consumes this same profile environment with ambient precedence; active job environments remain unchanged.

`model-connection.json` is schema 1: exact public fields project_id/revision/checked_at/executor/model/ready/reason plus internal schema/binding. The 64-character SHA256 binding covers the effective values of the allowlisted provider keys. Exact field sets, types, identity, UTC time, model grammar and ready/reason consistency are checked before staleness. Duplicate/foreign/corrupt evidence produces 503. Config/credential drift returns null. GUI credential mutations remove previous model evidence, preventing revival after a key is removed/restored. Test rechecks identity/config/binding after execution and validates output before atomic evidence publication.

## 7. Workflow Integration

New jobs load applied executor/model settings. Existing jobs retain their durable configuration; web guards reject applying changes during active work. Browser credentials remain in component memory and clear on mutation attempt/unmount. Audit records the attempt before a filesystem change and confirmation afterward; no secret values are recorded. Interrupted changes retain uncertainty rather than invented success.

## 8. Usage

Open Project → Settings → Agent and model for credentials. Prepare/apply the model change, pause monitoring for credential changes, choose an allowed API variable and Save API key. Test AI connection explicitly, then inspect Summary/check details.

Container projects use API keys. A local project may instead reuse the account's own Pi sign-in at `PI_CODING_AGENT_DIR` (default `~/.pi/agent/auth.json`), created outside ADORE. Host sign-in staging into containers is not supported. The GUI key removal changes only that project variable; it leaves ambient credentials and the account's Pi sign-in intact.

Official provider reference: [Pi](https://pi.dev/docs/latest/providers).

## 9. Validation And Tests

`tests/test_web_launch_presets.py`: Pi preset candidate apply, arbitrary/missing/unknown command, stale/CSRF/role/pause and tampered-pending rejection. `tests/test_executor_settings.py`: private save/remove, preserved unrelated bytes, CSRF/role/lock/pending/pause/ambient/config/env/evidence negatives, persisted result across host check and credential drift, corrupt/foreign/duplicate evidence. `test_model_connection.py` retains real offline diagnostic contracts. `test_web_executor_configuration.py` covers model/command review/apply, names-only lists, preserved private files and malformed/role/revision/pause/corrupt persistence boundaries. `web/e2e/executor-config.spec.ts` owns Settings/category/credential/candidate continuity; model-connection and settings journeys prove scoped results/defaults. Real provider/whole-job acceptance is operator-triggered.

## 10. Limitations

Model catalogs, executor installation and a browser OAuth broker remain external. Local OpenAI-compatible endpoints (such as LM Studio) are not configurable in this version, and ChatGPT subscription sign-in comes later. New custom provider names require external TOML configuration; retained custom names can be selected or removed. Opaque external credential sources (such as the account's Pi sign-in) are not fingerprinted and require an explicit fresh test. Connectivity proves one shell call only for native Pi; it does not prove Git publication or a complete job. Full regression remains deferred during the user's iterative live changes.

## Native execution contract

Local installed native argv is editable through validated reviewed candidates. Container editors offer only the Pi preset. Pi sign-in stays external; the account's Pi store is reused in place. Protected provider edits/current model evidence keep project-bound contracts.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused proof:
`04_Software/tests/test_local_execution.py`.

## Credential value reads

credential_values returns nonempty values from the existing strict bounded
private dotenv parser solely for in-memory rejection/redaction; it never
forwards or exports them. Missing .env is empty; corrupt stored bytes fail
closed. Existing provider credential tests cover the shared parser.

## Environment selection and external guidance

Administrators choose `execution.backend` (container | local), `container.runtime`,
`container.image` and, for local projects, `local.account`, `local.home`, `local.path`
and `local.cgroup_root` at enrollment (step 2) and in Settings → Agent and model. Settings
edits use only the reviewed flow (prepare candidate, review, apply); a direct PUT of
these keys returns 409 `pending_config_required`. Every other environment key
(`execution.preparation`, `container.uv_cache_volume`, `container.run_args`, egress,
SELinux, `worktree.*` roots) stays refused from the web with 400
`environment_managed_externally`. The `_CHOSEN_ENVIRONMENT_KEYS` set in
`web/app.py` and `CHOSEN_ENVIRONMENT_KEYS` in `settings.ts` name the chosen keys.

`GET /api/v1/executor-images?runtime=docker|podman` (Admin, read-only) runs
`<runtime> images --format {{.Repository}}:{{.Tag}}` with a 15 s timeout, drops
`<none>` entries and returns `{runtime, available, images}`; a runtime that cannot be
queried yields `available: false` with no images. The image fields in enrollment and
Settings offer these as suggestions (`serverImages.ts`) and show a notice when the typed
image is not on the server or the list cannot be read.

Credential variable names are optional in API-key mode: leave them empty when the image
or the installed executor signs in by itself (`env_keys = []`).

`ExecutorEnvironment.tsx` is a read-only four-locale notice in Settings → Agent and model,
rendered only for container profiles. Config GET `executor_environment` has
`backend`, `image` and `config_path`. Image comes from the validated preparation
plan when configured; invalid plan selection yields null, with operator-attention
text. Otherwise it is container.image. Only Admin receives the resolved profile
path; Dev receives null and contact guidance. A native details disclosure explains
executor/Dockerfile, executor/README.md, non-root structure, external build/check
and server config fields. It neither reads repository Dockerfiles nor issues
mutation requests. The image itself (Dockerfile and build) stays prepared on the server
by the administrator. Settings/enrollment omit controls for image definition and build.
A pending candidate for an operator-owned environment key, or one carrying an
`image_build` binding, could only be staged by an earlier build: it is 503
`pending_config_corrupt` on view and on apply, and Discard remains. API guards preserve the
existing dedicated AI endpoint exception. Proof:
`test_pending_candidate_for_an_external_key_is_corrupt_but_discardable` in
test_web_pending_config.py, `test_pending_image_build_binding_is_corrupt_but_discardable`
in test_executor_environment_choice.py and web/e2e/images.spec.ts; operator steps:
Project_Executor_Images.md.

## Reviewed selection and variable-name contracts

`executor.model` and `executor.command` are ordinary single-key candidates of `POST config/pending`; there is no agent selection key. `executor.model` must match the bounded `provider/model` grammar. A container project's `executor.command` must equal the Pi preset in `LAUNCH_PRESETS` (`branding.PI_NATIVE_COMMAND`); a local project accepts any nonempty validated native argv.

`executor.env_keys` candidates accept a complete distinct uppercase name list, bounded to32 entries; known provider names or retained existing custom names only. Forge variables and credential values fail closed. Direct PUT of either selection or variable names refuses with `pending_config_required`. Pending reads/apply reconstruct these candidates against the active base and reject unrelated persisted changes, even with a recomputed candidate hash. Existing role, CSRF, revision, idle and configuration locks remain authoritative.
