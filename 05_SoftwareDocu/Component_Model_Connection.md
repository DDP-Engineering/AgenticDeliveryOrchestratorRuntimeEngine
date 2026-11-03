<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Model connection diagnostic

## 1. Component Overview

Explicit administrator AI connection testing through Pi, ADORE's only coding agent. The saved `executor.provider` and `executor.model` are called once in an empty temporary workspace: over Pi's RPC mode in a temporary container for a container project, or through the installed native Pi for a local project. Both run the same challenge: one shell command that prints a tool nonce, then an exact reply nonce.

## 2. Responsibilities

Bound execution, require one successful shell call and the exact final reply, redact output and clean resources. Readiness has no model endpoint check; this explicit test is the only model-access evidence. This diagnostic changes no job or configuration.

## 3. Public Interfaces

`probe_model_connection(config, runner, env_file, *, popen=subprocess.Popen)` returns executor/model/ready/reason; `popen` is the process factory of the streaming `exec -i` (tests inject a fake Pi). POST `/api/v1/projects/{identity}/model-connection-test` requires administrator session/CSRF, nonarchived idle project, valid state and no pending configuration/operations. Configuration/conductor locks and snapshot rechecks bind evidence to immutable project identity and configuration revision. Monitoring need not be paused.

## 4. Dependencies

ContainerManager uses the project's local image, runtime, cache volumes, operator run arguments and the run's derived egress (`config.egress_policy`): with `[executor] internet` off the probe sits behind the per-run proxy that admits only the provider's hosts plus `[container.egress] allowlist`, and the proxy image is inspected beside the executor image (missing -> `image-missing`); with it on the network is open. The probe never loads pi-web-access and gets no internet-off system-prompt notice. The image must contain the pinned Pi and ADORE's Pi guard extension (`pi_rpc_argv`). `adore/executor/pi_rpc.run_pi_rpc` drives the RPC session through `ContainerManager.spawn`; `adore/pi_providers.py` supplies the credential variable, the Pi provider id and the endpoint `models.json`. Images are inspected locally and never pulled.

## 5. Inputs And Outputs

Executor secrets use selected profile `.env` plus ambient environment precedence, limited to `pi_providers.secret_names` (the provider's credential variable plus `executor.env_keys`). A provider that needs a credential (`credential_required`: every provider except `custom`) with none saved or set returns `credential-missing` before any container starts. For `provider = "custom"` the probe writes Pi's `models.json` (`apiKey` `$ADORE_ENDPOINT_API_KEY` when that key is set, else the placeholder `adore-no-key`) to the io directory and copies it into `/home/adore/.adore-pi-agent/models.json` inside the container before Pi starts; a failed copy returns `runtime-error`. No host sign-in is staged into the container. Core repo/work/io mounts contain temporary empty directories; trusted operator run arguments retain their configured semantics. Forge connection tokens are not staged.

## 6. Data Contracts

API evidence adds project_id, SHA-256 revision and UTC checked_at. GUI accepts exact current project/executor/model/revision. Reasons: ready, timeout, image-missing, cli-missing, credential-missing, credential-invalid, model-unavailable, connection-failed, rate-limited, provider-error, invalid-response, runtime-error, tool-call-failed. A container RPC outcome maps as follows: completed -> the shell-nonce and exact-reply check (`ready`, `tool-call-failed` or `invalid-response`); a failure of Pi's class credential or sign-in -> `credential-invalid`, model -> `model-unavailable`, network -> `connection-failed`, rate-limit -> `rate-limited`, provider or any other class -> `provider-error`; timed out -> `timeout`; a protocol failure with exit 126/127 -> `cli-missing`, any other protocol failure -> `invalid-response`. The pure frontend module `web/src/modelEvidence.ts` holds the reason set, `validModelEvidence`, the four-locale copy and `modelGuidance`. Duplicate fields, malformed output, wrong nonce or missing completion fail closed; container and native Pi must both show one successful shell call printing the tool nonce. `executor_settings.REASONS` is the same set as `model_connection.REASONS`, so persisted evidence accepts every probe reason. Raw stdout/stderr is never returned.

## 7. Workflow Integration

Settings → Agent and model offers Test AI connection at the panel heading right, alongside the settings and project API keys; Summary shows the current saved model result only inside expanded host-check details. Each explicit click can incur provider charges. The container Pi run is capped at `CONTAINER_TIMEOUT_SECONDS` (60 seconds) and the native gate at 90 seconds; container output keeps `pi_rpc`'s bounded evidence (local stdout is capped at 1 MiB through `LocalTarget.output_limit`, local stderr at 64 KiB); container setup and the Pi run share a 90-second deadline, followed by cleanup commands capped at 8 seconds each. Cleanup failures become API errors.

## 8. Usage

Save executor/model credentials as for normal execution, ensure its local image is available, then click Test AI connection. The container challenge starts the image's Pi with `pi_rpc_argv(model, pi_provider(provider))` (`--mode rpc --no-session`, the guard extension, `--provider <pi provider> --model <model id>`) and sends the prompt "run `echo ADORE_TOOL_<hex>` once, then reply exactly `ADORE_OK_<hex>`". Local diagnostics use managed Pi and the same native RPC scope as stages.

## 9. Validation And Tests

`tests/test_model_connection.py` fakes the external runtime boundary and injects a fake Pi RPC process through `popen` (`tests/fake_pi_rpc.py`). It covers the happy challenge, missing credential, each failure class, malformed output, nonce/tool violations, models.json placement, the derived egress (`test_probe_runs_under_the_internet_switch`), timeout/cleanup, CSRF/role/lock/corrupt/stale configuration. Browser proof: `web/e2e/model-connection.spec.ts` explicit invocation, cost notice and stale evidence rejection. Existing host-readiness tests prove separation.

## 10. Limitations

A container or native Pi result proves one shell call. Neither proves Git push permission, AEGIS execution or complete job. Current results are persisted in model-connection.json by executor_settings.py, validated against immutable identity/configuration/credential inputs, and reused by Summary and host-check access presentation. Stale results are suppressed and corrupt results rejected. See Component_Executor_Configuration.md for storage/auth contracts. Full regression is deferred during iterative GUI work; real paid provider checks remain operator-triggered acceptance.

## Effective preparation image

Explicit model connection resolves the selected Git recipe through its bounded runner and uses the normalized effective image. Stale/corrupt source yields a failed result before any container setup. No project recipe command runs in the disposable connectivity workspace.

## Native execution contract

Native challenges use local_probe and the same fixed Pi argv and account environment as gates, with a 90-second gate bound and verified scope cleanup. The prompt asks for `echo <ADORE_TOOL nonce>` and then the exact reply; `_native_tool_response` requires Pi's successful shell event carrying that nonce (otherwise `tool-call-failed`) and then the completed reply (otherwise `invalid-response`), per `.agentic/specs/REQ-FUNC-8f369d55.md`. No login or complete-job claim; container diagnostics keep the fixed RPC command line.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused native proof:
`04_Software/tests/test_local_execution.py`.

## Native completion and failure classification

The managed native Pi and service account environment remains authoritative. A
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
