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

`web/executor_configuration.py` holds the reviewed Pi launch-command preset (`LAUNCH_PRESETS`) and the atomic agent connection edit (`CONNECTION_KEY = "executor.connection"`, `valid_connection`, `connection_value`, `set_connection`); `web/implementation_settings.py` validates names-only lists. `adore/pi_providers.py` owns the shipped Pi provider catalog and the provider rules (credential variable, Pi provider id, secret names, endpoint `models.json`). `web/executor_settings.py` validates private profile inputs, edits one approved .env variable atomically, and binds/loads model evidence. `adore/chatgpt.py` owns the server's one ChatGPT sign-in, which a `chatgpt` project uses instead of a provider key (see [ChatGPT sign-in](Component_ChatGPT_Sign_In.md)). `web/app.py` owns roles, CSRF, immutable project selection, configuration/conductor locks and audit attempts/confirmations. The existing config candidate and launcher own applied TOML changes and actual job injection.

## 3. Implementation Overview

**Project → Settings → Agent and model** configures Pi, ADORE's only coding agent; there is no agent choice. It shows Test AI connection, the agent connection (Provider, Model, and for an OpenAI-compatible endpoint Endpoint base URL and Endpoint API type, reviewed and applied together as `executor.connection`), the launch command (`executor.command`; a container project may choose only the one Pi preset, a local project edits validated native argv), Internet access for the agent (`executor.internet`) and Web search (`executor.web.search`), additional credential variables (`executor.env_keys`), the provider API key, the execution environment (`execution.backend`, the container runtime and image, and the local account, home, PATH and cgroup root for local projects, with external container guidance) and estimated prices. Connection, command, internet access, web search, backend, runtime and image edits go only through the reviewed flow (prepare candidate, review, apply); a new model ID must be supplied explicitly (the Model field suggests Pi's models for the provider and accepts any typed ID). Credential names are added through a dropdown and remain visible as individually removable selections. While the image row is edited it offers the same server image suggestions. Installed agents and runtime preparation remain external. The old `/executor` URL redirects to Settings. Developers read non-secret settings/results without mutation actions.

The names-only selector for additional credential variables offers the known provider key variables and retained custom names; it defaults to empty (`env_keys = []`) because the provider's own key variable is always passed. Applying names does not delete saved `.env` values. Provider API key offers private Save/Disconnect for the variable Pi reads the configured provider's key from (`ADORE_ENDPOINT_API_KEY`, optional, for an endpoint) and, while internet access is on with Brave or Tavily search, `BRAVE_API_KEY` or `TAVILY_API_KEY` after it, and shows their sources only; key changes require paused pickup and idle/pending-free state. Explicit Test AI connection remains the evidence of model access and may incur provider charges.

For a ChatGPT subscription (`provider = "chatgpt"`) the Authentication slot shows **ChatGPT sign-in** (`ChatGptSignIn.tsx`) to Admins instead of the Provider API key form: the status of the server's one sign-in (Signed in, Not signed in, Sign in again), Sign in with ChatGPT, the pasted redirect address, Cancel and Disconnect ChatGPT. The sign-in belongs to the ADORE server, not to the project, so it needs neither paused pickup nor an idle project; every `chatgpt` project of the server shares it. The model field suggests the ChatGPT models of the catalog (`chatgpt.models`). When such a project needs a Brave or Tavily search key, the key form follows the sign-in panel for that key alone.

Save API key / Disconnect project API key operate on the selected profile's `.env` and accept only the project's credential variables (`pi_providers.credential_variables`: the configured provider's variable, then the web search key of an internet-on project searching with Brave or Tavily). Ambient variables (including explicitly empty values) take precedence and are managed externally. Source indicators distinguish missing, project and environment. Saving is not authentication success; explicit Test AI connection provides that evidence.

## 4. Dependencies

Standard library filesystem/JSON/hash functions; existing ProfileStore, StateStore/config edit guards, WebStore audit, ContainerManager/model diagnostic, React and same-origin API. No new dependency or SQLite schema.

## 5. Inputs And Outputs

GET `/api/v1/projects/{identity}/executor-credentials` (Admin) returns `{project_id, revision, variables:[{name, source}]}`; `variables` holds only `credential_variables(executor)`: the configured provider's credential variable (none for `chatgpt`), then `BRAVE_API_KEY` or `TAVILY_API_KEY` when internet is on with that search, each with source environment, project or missing.
PUT takes exact `{revision, variable, token}`; DELETE exact `{revision, variable}`. Monitoring must be paused, state valid and idle, with no pending configuration/operations. Archived projects reject mutations. Return values contain no key or credential digest. Authentication errors have stable value-free codes.

The ChatGPT sign-in routes (Admin) are `GET`/`PUT`/`DELETE /api/v1/chatgpt-sign-in`, `DELETE /api/v1/chatgpt-sign-in/pending` and `POST /api/v1/projects/{name}/chatgpt-sign-in`; [Web API](Component_Web_API.md) holds their contract. `GET /api/v1/pi-providers` returns the ChatGPT models as `chatgpt.models`.

Config GET includes `model_connection`, a current public result or null; for a `chatgpt` project it is null while the server is not signed in with ChatGPT. Model test POST stores and returns the same closed result. Summary displays current access only in expanded host-check details; host-check AI access uses that result when present. Readiness has no separate model endpoint check.

## 6. Data Contracts

Provider keys: `PROVIDER_KEYS = pi_providers.key_variables()`, the key variables of the shipped Pi catalog (OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY and so on) plus ADORE_ENDPOINT_API_KEY; it is the allowlist of `executor.env_keys` names. The credential view and save accept only `credential_variable(provider)`. Variable names do not promise provider/model availability in an installed CLI.

Dotenv reads are bounded to 64 KiB, reject symlinks, duplicate names, malformed lines, invalid UTF-8/control characters and unbalanced surrounding quotes. Atomic same-directory replacement preserves other lines; generated files have legal headers, POSIX mode 0600 and fsync before rename. The existing launcher consumes this same profile environment with ambient precedence; active job environments remain unchanged.

`model-connection.json` is schema 1: exact public fields project_id/revision/checked_at/executor/model/ready/reason plus internal schema/binding. The 64-character SHA256 binding covers the effective values of every secret Pi receives (`pi_providers.secret_names`: `env_keys` plus the provider's credential variable; a `chatgpt` project has no credential variable, and its stage token is never part of the binding). Exact field sets, types, identity, UTC time, model grammar (`MODEL_ID_RE`) and ready/reason consistency are checked before staleness. Duplicate/foreign/corrupt evidence produces 503. Config/credential drift returns null. GUI credential mutations remove previous model evidence, preventing revival after a key is removed/restored. Test rechecks identity/config/binding after execution and validates output before atomic evidence publication.

## 7. Workflow Integration

New jobs load applied executor/model settings. Existing jobs retain their durable configuration; web guards reject applying changes during active work. Browser credentials remain in component memory and clear on mutation attempt/unmount. Audit records the attempt before a filesystem change and confirmation afterward; no secret values are recorded. Interrupted changes retain uncertainty rather than invented success.

## 8. Usage

Open Project → Settings → Agent and model for credentials. Prepare/apply the provider and model change, pause monitoring for credential changes, and Save API key for the variable the provider names. Test AI connection explicitly, then inspect Summary/check details.

Container projects use a provider API key, the server's ChatGPT sign-in (`provider = "chatgpt"`; an Admin signs in once under Settings → Agent and model, and each stage receives only a short-lived access token as `OPENAI_API_KEY`) or an OpenAI-compatible endpoint (whose `models.json` ADORE writes into the ADORE-owned agent directory before every stage). A local project may instead reuse the account's own Pi sign-in at `PI_CODING_AGENT_DIR` (default `~/.pi/agent/auth.json`), created outside ADORE. The account's own Pi sign-in is never staged into containers. The GUI key removal changes only that project variable; it leaves ambient credentials and the account's Pi sign-in intact.

Official provider reference: [Pi](https://pi.dev/docs/latest/providers).

## 9. Validation And Tests

`tests/test_web_launch_presets.py`: Pi preset candidate apply, arbitrary/missing/unknown command, stale/CSRF/role/pause and tampered-pending rejection. `tests/test_executor_settings.py`: private save/remove, preserved unrelated bytes, CSRF/role/lock/pending/pause/ambient/config/env/evidence negatives, persisted result across host check and credential drift, corrupt/foreign/duplicate evidence. `test_model_connection.py` retains real offline diagnostic contracts. `test_web_executor_configuration.py` covers model/command review/apply, names-only lists, preserved private files and malformed/role/revision/pause/corrupt persistence boundaries. `tests/test_web_chatgpt.py` covers the ChatGPT sign-in routes and the `executor_sign_in` readiness check; `test_model_connection.py` covers the ChatGPT probe reasons. `web/e2e/executor-config.spec.ts` owns Settings/category/credential/candidate continuity and the ChatGPT sign-in and Disconnect journey; model-connection and settings journeys prove scoped results/defaults. Real provider/whole-job acceptance is operator-triggered.

## 10. Limitations

The provider catalog is the snapshot shipped with the pinned Pi (`adore/pi_catalog.json`); executor installation remains external. Sign in with ChatGPT has no callback receiver: the administrator pastes the redirect address the browser shows. A ChatGPT subscription and an OpenAI-compatible endpoint need a container run; a ChatGPT project's stage limits are at most 3000 s. New custom additional variable names require external TOML configuration; retained custom names can be selected or removed. Opaque external credential sources (such as the account's Pi sign-in) are not fingerprinted and require an explicit fresh test. Connectivity proves one shell call in a container and for native Pi; it does not prove Git publication or a complete job. Full regression remains deferred during the user's iterative live changes.

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
(`execution.preparation`, `container.uv_cache_volume`, `container.run_args`, `container.egress.*`,
SELinux, `worktree.*` roots) stays refused from the web with 400
`environment_managed_externally`. The `_CHOSEN_ENVIRONMENT_KEYS` set in
`web/app.py` and `CHOSEN_ENVIRONMENT_KEYS` in `settings.ts` name the chosen keys.

`GET /api/v1/executor-images?runtime=docker|podman` (Admin, read-only) runs
`<runtime> images --format {{.Repository}}:{{.Tag}}` with a 15 s timeout, drops
`<none>` entries and returns `{runtime, available, images}`; a runtime that cannot be
queried yields `available: false` with no images. The image fields in enrollment and
Settings offer these as suggestions (`serverImages.ts`) and show a notice when the typed
image is not on the server or the list cannot be read.

Additional credential variable names are optional (`env_keys = []`): the provider's key
variable is always passed, so list only further secrets the executor needs.

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

`executor.connection` is a virtual candidate key of `POST config/pending` whose value is strict JSON `{provider, model, base_url, api}`: a provider from `pi_providers.provider_ids()`, a model matching `MODEL_ID_RE`, and an http(s) `base_url` plus an API type from `ENDPOINT_APIS` exactly when the provider is `custom` (both empty otherwise). `set_connection` rewrites `[executor] provider` and `model` and removes or adds the `[executor.endpoint]` table, preserving unrelated TOML (verified by re-parsing). The configuration rows `executor.provider`, `executor.model`, `executor.endpoint.base_url` and `executor.endpoint.api` map to edit key `executor.connection` and cannot be staged individually (400 `setting_not_editable`). `executor.command` is an ordinary single-key candidate; there is no agent selection key. A container project's `executor.command` must equal the Pi preset in `LAUNCH_PRESETS` (`branding.PI_NATIVE_COMMAND`); a local project accepts any nonempty validated native argv.

`executor.env_keys` candidates accept a complete distinct uppercase name list, bounded to 32 entries; names from `PROVIDER_KEYS` or retained existing custom names only. Forge variables and credential values fail closed. Direct PUT of either selection or variable names refuses with `pending_config_required`. Pending reads/apply reconstruct these candidates against the active base and reject unrelated persisted changes, even with a recomputed candidate hash. Existing role, CSRF, revision, idle and configuration locks remain authoritative.
