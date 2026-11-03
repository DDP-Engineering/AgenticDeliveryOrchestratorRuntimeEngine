<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Model connection

## Routing

Test AI connection and executor model diagnostic start at `04_Software/adore/web/model_connection.py`; focused proof: `04_Software/tests/test_model_connection.py`. Host prerequisites belong to web-interface.md (`_probe_setup` in `web/app.py`).

## Purpose and boundaries

Explicit model access testing through Pi, ADORE's only coding agent; in a container (Pi RPC) and for an installed native Pi it also proves one shell tool call. Complete-job acceptance stays separate. ContainerManager owns isolation; executor-configuration.md owns private credential/evidence persistence; host readiness owns prerequisite evidence.

## Public interface

`probe_model_connection(config, runner, env_file, *, popen=subprocess.Popen)` (`popen` is the test seam of the streaming `exec -i`) and POST `/api/v1/projects/{identity}/model-connection-test`; closed executor (`branding.EXECUTOR_NAME`, `pi`)/model/ready/reason evidence plus project/revision/time. A model outside `pi_providers.MODEL_ID_RE` returns `runtime-error` without running anything.

## Invariants

Admin/CSRF and idle configuration/conductor locks precede execution. Saved provider and model, the secrets of `pi_providers.secret_names` (provider credential variable, web search key of an internet-on Brave/Tavily project, `env_keys`) and the egress of `config.egress_policy` (provider hosts only while `[executor] internet` is off, open while on; the proxy image is inspected like the executor image) are reused; the probe loads no web tools and gets no internet-off notice; core repo/work mounts are empty. In a container, a provider that needs a credential (all but `custom`) with none saved or set is `credential-missing` before any container starts; for `custom` the endpoint `models.json` is written to the io dir and copied to `/home/adore/.adore-pi-agent/models.json` (a failed copy is `runtime-error`). The diagnostic then runs `pi_rpc.run_pi_rpc` through `ContainerManager.spawn` with `pi_rpc_argv(model, pi_provider(provider))`, bounded by `CONTAINER_TIMEOUT_SECONDS` (60) within a 90-second overall deadline, and the prompt asks for `echo ADORE_TOOL_<hex>` once, then exactly `ADORE_OK_<hex>`. Completed -> `_native_tool_response` (`ready`, `tool-call-failed`, `invalid-response`); Pi failure class credential/sign-in -> `credential-invalid`, model -> `model-unavailable`, network -> `connection-failed`, rate-limit -> `rate-limited`, provider or other -> `provider-error`; timed out -> `timeout`; protocol exit 126/127 -> `cli-missing`, other protocol failure -> `invalid-response`. A native Pi uses the fixed managed RPC launcher in an owned process scope and `_native_tool_response(output, tool_nonce, nonce)` requires a successful bash `tool_execution_end` carrying an `ADORE_TOOL_` nonce, then the exact reply in the last assistant message (`.agentic/specs/REQ-FUNC-8f369d55.md`). Raw output is redacted and cleanup is bounded.

## Key behaviors

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: Native challenges use local_probe and the same managed argv and account environment as stages, with verified scope cleanup. No login or complete-job claim; container diagnostics keep the fixed RPC command line.
- REQ-FUNC-8f369d55: a native Pi is ready only with a completed shell call printing the tool nonce and the exact reply.
- REQ-FUNC-0b728218: missing/rejected/failed shell call -> `tool-call-failed`.
- REQ-UX-923bc788: `web/src/modelEvidence.ts` accepts the reason and shows four-locale guidance.
- REQ-NFR-ac3e9541: native gate bounded at 90 seconds.
- REQ-NFR-f4b171f4: the native test retains a 1 MiB RPC output tail in memory; job gates keep 64 KiB.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


- `REQ-UX-94a97e70`: Explicit disposable model checks resolve the same effective preparation image through bounded Git reads, refuse stale source and never execute recipe commands.

- REQ-FUNC-de028c15: explicit Pi connectivity; container 60-second Pi run within a 90-second setup deadline, 8-second cleanup commands; reasons include `credential-missing`, `rate-limited` and `provider-error`.
- Settings → Agent and model heading action, integrated credential/settings panel, cost notice, duplicate suppression and exact project/configuration binding; executor_settings.py durably saves and validates credential-bound evidence used in Summary/host access.

## Files

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


- `04_Software/adore/web/model_connection.py`, `web/app.py`: probe/API.
- `04_Software/web/src/ModelConnection.tsx`, `App.tsx`, `styles.css`: GUI; `web/src/modelEvidence.ts`: reasons, evidence validation, copy and guidance (`web/tests/modelEvidence.test.mjs`).
- `04_Software/tests/test_model_connection.py`, `web/e2e/model-connection.spec.ts`: offline proof.
- `05_SoftwareDocu/Component_Model_Connection.md`: detailed contract.
