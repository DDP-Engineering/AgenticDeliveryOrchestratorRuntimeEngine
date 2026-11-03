<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Executor configuration

## Routing

Project executor/model/key configuration starts at `04_Software/adore/web/executor_configuration.py`, reviewed candidate routes and `web/src/ExecutorSelectionEditor.tsx` / `CredentialNamesEditor.tsx`; private key storage starts at `04_Software/adore/web/executor_settings.py`, app.py executor credential/model routes and `web/src/ExecutorCredentials.tsx`. Probe execution belongs to model-connection.md; generic candidate apply to web-interface.md.

## Purpose and boundaries

One project-owned workspace; protected provider variable edits and durable model evidence. Launcher reads existing .env; config candidates own TOML application; installed CLI owns subscription login.

## Public interface

GET/PUT/DELETE executor-credentials (Admin), config GET model_connection, model test POST persistence. See Component_Executor_Configuration.md for exact schemas/error/status contracts.


credential_values exposes the existing strict bounded private dotenv read. No
values are exported. Corruption fails closed; missing input is empty. It has no
caller since the image-build subsystem was removed.

## Invariants

CSRF/admin/immutable identity/config and conductor locks/pause/idle/pending guards. Private bounded atomic dotenv edits; secret-free API/audit; strict duplicate/corrupt evidence rejection before stale filtering. Current public result binds model/revision and internal credential digest. Key changes delete old evidence. Real model testing remains explicit.

## Key behaviors

- REQ-UX-812acd4b: container.system_packages is a separate reviewed boolean, with four-locale container-only labels/help and existing admin/pause/idle/revision authority.

- REQ-UX-b75e1df8: Local installed native argv is editable through validated reviewed candidates. Container editors retain standard presets. Subscription login stays external; local stores are reused in place. Protected provider edits/current model evidence keep project-bound contracts.

REQ-UX-ec09a60a: installed launch choices display the actual process account.
Command/manual path editors and saved local environment/assertion rows use closed
Advanced disclosures. Existing candidate selection and apply authority persist.

Native control/auth route to local-execution.md. Focused proof:
`04_Software/tests/test_local_execution.py`.


**Project → Settings → Agent and model** owns the default coding agent, the selected agent's launch command/model, AI connection testing, `execution.backend`, the container runtime and image (and the local account, home, PATH and cgroup root for local projects) and external container guidance. Its **Authentication** disclosure groups allowed credential variable names, host sign-in reuse and **Provider API keys**. The agent editor offers OpenCode, Pi, Codex and Qwen Code even when their command tables are absent. Selecting an agent loads its saved command/model or the documented command preset; a new model ID must be supplied explicitly. Prepare reviews changed fields above the settings, with all three agent/command/model values available in the complete Technical details comparison. Apply writes one complete paused/idle candidate; unchanged simple candidates show a notice with disabled Apply. The generic launch-command/model labels follow the selected agent. Edit keeps agent, command and model controls inside their existing description/value rows; the default-agent row owns Prepare/Cancel for the complete draft, beside its dropdown using the shared editor layout and normal responsive wrapping. Grouped-edit guidance stays in the description column. Validation occupies its own line after the controls, keeping selector/actions aligned when the selected agent needs a model; Prepare remains disabled until the complete draft is valid. Credential names are added through a dropdown and remain visible as individually removable selections. Backend, runtime and image edits go only through the reviewed flow (prepare candidate, review, apply). While the image row is edited it offers the same server image suggestions. Installed agents and runtime preparation remain external. The old `/executor` URL redirects to Settings. Developers read non-secret settings/results without mutation actions.

The names-only credential selector offers known provider names and retained custom names, independently of coding agent. Empty lists support existing server sign-in, including in API-key mode when the image or the installed executor signs in by itself (`env_keys = []`). Applying names does not delete saved `.env` values. Provider API keys offers private Save/Disconnect for known allowed variables and shows sources only; key changes require paused pickup and idle/pending-free state. Explicit Test AI connection remains the evidence of model access and may incur provider charges. Subscription login retains the installed CLI's external service-account workflow.

REQ-FUNC-c829c366 owns atomic supported-agent enrollment; REQ-FUNC-08cc2676 owns reviewed names-only lists. executor_configuration.py validates exact selection and full TOML meaning. implementation_settings.py retains scoped collection writes; app.py reconstructs selection/list pending records against their base before use. Direct PUT requires candidate review.


## Change map

Atomic agent/names-only selection: executor_configuration.py, implementation_settings.py, app.py, test_web_executor_configuration.py and settings helper tests. Credential persistence/binding: executor_settings.py, test_executor_settings.py. HTTP permissions/locks: app.py and same tests. GUI ownership: App/routes/ExecutorSelectionEditor/CredentialNamesEditor/ExecutorCredentials/ReadinessEvidence/ModelConnection, executor-config/model-connection/settings Chromium journeys.

## Files

- `04_Software/tests/test_system_packages.py`: package authority, independent egress, recovery and reviewed settings contracts.

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


Source/tests above; detailed component contract `05_SoftwareDocu/Component_Executor_Configuration.md`; operator web/security/configuration references. No SQLite migration.

## External environment guidance

REQ-UX-01d189b8 / REQ-FUNC-6b8494a7: ExecutorEnvironment.tsx reads the validated
config executor_environment object. Container profiles show effective image and
one external Dockerfile/build/profile disclosure; local profiles omit it. The
resolved profile path is Admin-only. The notice makes no mutation requests; the
Dockerfile and build stay on the server. Administrators choose execution.backend,
container.runtime, container.image and local.account/home/path/cgroup_root at
enrollment step 2 and in Settings (reviewed flow only; direct PUT 409
pending_config_required). GET /api/v1/executor-images?runtime=docker|podman (Admin,
read-only, 15 s timeout, drops `<none>`) returns {runtime, available, images} for
image suggestions (serverImages.ts); choosing an executor proposes a
`<executor>-*` tag, never over a typed value. API-key mode allows empty
env_keys. All other container/execution/local/worktree keys stay refused (400
environment_managed_externally). A pending candidate with an `image_build`
binding or for an operator-owned key, which only an earlier build could stage,
is 503 `pending_config_corrupt` on view and apply; an administrator can still
discard it (DELETE /api/v1/projects/{name}/config/pending). ADORE web has no
image definition or build routes. Existing dedicated AI endpoint and
executor/model/credential operations remain. Focused proof:
test_executor_environment_choice.py, test_web_pending_config.py and images.spec.ts.

## Installed executor suggestions

Local enrollment and launch-command editing use the admin-only filesystem
discovery and manual path picker described in [Installed executor discovery](executor-discovery.md).
Existing saved/manual commands retain authority; selected paths are revalidated
by native policy and applied through the existing reviewed configuration flow.
