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

Explicit model access testing for all four executor CLIs. ContainerManager owns isolation; executor-configuration.md owns private credential/evidence persistence; host readiness owns prerequisite and OpenCode tool-stream evidence.

## Public interface

`probe_model_connection(config, runner, env_file)` and POST `/api/v1/projects/{identity}/model-connection-test`; closed executor/model/ready/reason evidence plus project/revision/time.

## Invariants

Admin/CSRF and idle configuration/conductor locks precede execution. Saved model, allowlisted secrets and egress are reused; core repo/work mounts are empty. Fixed shell-free commands require completed nonce responses; malformed data/tool invocation fails closed. Raw output is redacted and cleanup is bounded.

## Key behaviors

- `REQ-UX-94a97e70`: Explicit disposable model checks resolve the same effective preparation image through bounded Git reads, refuse stale source and never execute recipe commands.

- REQ-FUNC-de028c15: OpenCode/Pi/Codex/Qwen explicit connectivity; 45-second inference/90-second setup deadline, 1 MiB capture, 8-second cleanup commands.
- Executor configuration heading action, integrated credential/settings panel, cost notice, duplicate suppression and exact project/configuration binding; executor_settings.py durably saves and validates credential-bound evidence used in Summary/host access.

## Architecture

```mermaid
flowchart TD
    GUI([ModelConnection]) --> API[model_connection_test]
    API --> Locks[Configuration and conductor locks]
    Locks --> Probe[probe_model_connection]
    Probe --> Runtime[ContainerManager]
    Runtime --> Script[Disposable container probe.py]
    Script --> CLI([OpenCode / Pi / Codex / Qwen])
    CLI --> Envelope[Closed redacted result]
    Envelope --> API
    API --> GUI
    Probe --> Cleanup[Container and temporary files cleanup]
```

Only model connectivity is tested; full job/tool acceptance remains separate.

## Files

- `04_Software/adore/web/model_connection.py`, `web/app.py`: probe/API.
- `04_Software/web/src/ModelConnection.tsx`, `App.tsx`, `styles.css`: GUI.
- `04_Software/tests/test_model_connection.py`, `web/e2e/model-connection.spec.ts`: offline proof.
- `05_SoftwareDocu/Component_Model_Connection.md`: detailed contract.
