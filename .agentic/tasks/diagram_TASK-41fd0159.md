<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-41fd0159 diagrams

Illustrates `## Design` in `TASK-41fd0159.md`. The Design text is authoritative.

Node classes: added = `run_pi_rpc`, `adore_guard`, `fake_pi`; changed =
`launch_stage`, `PiExecutor`, `Executor_run_gate`, `BoundTarget`,
`ContainerManager`, `Dockerfile`; unchanged = `journal_usage`, `pi_process`.

## Structure

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    launch_stage["Orchestrator._launch_stage"]:::changed --> Executor_run_gate["Executor.run_gate(cancel)"]:::changed
    Executor_run_gate --> PiExecutor["PiExecutor.run_gate"]:::changed
    PiExecutor ==> run_pi_rpc["pi_rpc.run_pi_rpc"]:::added
    run_pi_rpc ==> BoundTarget["BoundTarget.spawn"]:::changed
    BoundTarget ==> ContainerManager["ContainerManager.spawn (exec -i)"]:::changed
    ContainerManager ==> pi_process(["node cli.js --mode rpc"])
    Dockerfile["Dockerfile.executor-base"]:::changed ==> adore_guard["pi/adore-guard.ts"]:::added
    pi_process ==> adore_guard
    launch_stage --> journal_usage["Orchestrator._journal_usage"]
    fake_pi["tests/fake_pi_rpc.py"]:::added ==> run_pi_rpc
```

## Sequence

```mermaid
sequenceDiagram
    participant O as Orchestrator._launch_stage
    participant E as PiExecutor
    participant R as pi_rpc.run_pi_rpc
    participant P as Pi (docker exec -i)
    O->>E: run_gate(prompt, timeout, cancel)
    E->>R: argv, env, prompt
    R->>P: spawn; {"type":"prompt"}
    P-->>R: response started; events
    alt deadline or cancel
        R->>P: {"type":"abort"}
        P-->>R: agent_settled aborted
    else normal end
        P-->>R: agent_settled
    end
    R->>P: get_session_stats
    P-->>R: stats (cross-check)
    R->>P: close stdin (terminate after grace)
    R-->>E: PiRpcResult
    E-->>O: GateRun (usage, exit, evidence)
    O->>O: _journal_usage
```

## State

```mermaid
stateDiagram-v2
    [*] --> starting
    starting --> protocol_error: spawn fails
    starting --> running: prompt started
    starting --> failed: prompt rejected
    running --> settled: agent_settled
    running --> aborting: deadline or cancel
    running --> protocol_error: exit before settle / malformed record
    aborting --> stopping: agent_settled or abort grace over
    settled --> stopping: stats answered or grace over
    stopping --> [*]: exited, or terminated after exit grace
```
