<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Model connection

## Routing

Test AI connection and executor model diagnostic start at `04_Software/adore/web/model_connection.py`; focused proof: `04_Software/tests/test_model_connection.py`. Host prerequisites belong to web-interface.md/endpoint_probe.py.

## Purpose and boundaries

Explicit model access testing for all four executor CLIs; for native OpenCode, Pi and Codex it also proves one shell tool call. Complete-job acceptance stays separate. ContainerManager owns isolation; executor-configuration.md owns private credential/evidence persistence; host readiness owns prerequisite and OpenCode tool-stream evidence.

## Public interface

`probe_model_connection(config, runner, env_file)` and POST `/api/v1/projects/{identity}/model-connection-test`; closed executor/model/ready/reason evidence plus project/revision/time.

## Invariants

Admin/CSRF and idle configuration/conductor locks precede execution. Saved model, allowlisted secrets and egress are reused; core repo/work mounts are empty. Container diagnostics use fixed shell-free commands and require completed nonce responses; malformed data/tool invocation fails closed there and for native Qwen. Native OpenCode/Pi/Codex require the executor's successful shell event carrying an `ADORE_TOOL_` nonce, then the exact reply (`.agentic/specs/REQ-FUNC-8f369d55.md`). Raw output is redacted and cleanup is bounded.

## Key behaviors

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: Native challenges use local_probe and the same configured argv/account/environment as gates, with verified scope cleanup. No login or complete-job claim; container diagnostics keep fixed commands.
- REQ-FUNC-8f369d55: native OpenCode/Pi/Codex ready only with a completed shell call printing the tool nonce and the exact reply.
- REQ-FUNC-0b728218: missing/rejected/failed shell call -> `tool-call-failed`.
- REQ-UX-923bc788: `web/src/modelEvidence.ts` accepts the reason and shows four-locale guidance.
- REQ-NFR-ac3e9541: native gate bounded at 90 seconds.
- REQ-NFR-f4b171f4: the native test raises its target's `output_limit` to 1 MiB (Pi streams ~300 KB); job gates keep 64 KiB.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


- `REQ-UX-94a97e70`: Explicit disposable model checks resolve the same effective preparation image through bounded Git reads, refuse stale source and never execute recipe commands.

- REQ-FUNC-de028c15: OpenCode/Pi/Codex/Qwen explicit connectivity; container 45-second inference/90-second setup deadline, 1 MiB capture, 8-second cleanup commands.
- Settings → Agent and model heading action, integrated credential/settings panel, cost notice, duplicate suppression and exact project/configuration binding; executor_settings.py durably saves and validates credential-bound evidence used in Summary/host access.

## Files

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


- `04_Software/adore/web/model_connection.py`, `web/app.py`: probe/API.
- `04_Software/web/src/ModelConnection.tsx`, `App.tsx`, `styles.css`: GUI; `web/src/modelEvidence.ts`: reasons, evidence validation, copy and guidance (`web/tests/modelEvidence.test.mjs`).
- `04_Software/tests/test_model_connection.py`, `web/e2e/model-connection.spec.ts`: offline proof.
- `05_SoftwareDocu/Component_Model_Connection.md`: detailed contract.
