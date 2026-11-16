<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-1d2c5b87 diagrams

Illustrates the task Design, which is authoritative.

## Structure

Node map: PiConversation added; Orchestrator, PiExecutor and run_pi_rpc changed; Pi and LocalTarget reused unchanged.

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    o["Orchestrator"]:::changed ==> c["PiConversation"]:::added
    o --> e["PiExecutor"]:::changed
    e ==> c
    e --> r["run_pi_rpc"]:::changed
    r ==> c
    r --> p["Pi"]
    e --> l["LocalTarget"]
```

## Sequence

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant C as PiConversation
    participant R as run_pi_rpc
    participant P as Pi
    O->>C: Validate private binding and history
    O->>R: Current stage prompt
    R->>P: Start explicit session path
    R->>P: get_state and initial statistics
    P-->>R: Exact identity and baseline
    R->>C: Pin identity
    R->>P: prompt
    P-->>R: Accepted, new events, settled
    R->>C: Require saved history
    R->>P: Final statistics and shutdown
    R-->>O: Current-attempt evidence and usage
```

## State

Not drawn: existing job/workflow lifecycle states and transitions are unchanged.
