<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-d360af13 diagrams

Illustrates Design in TASK-d360af13.md. Changed nodes: Config, Orchestrator, ContainerManager, Settings. Added node: package_permissions. Agent and runtime are reused unchanged.

## Structure

```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 settings["Settings"]:::changed ==> config["Config"]:::changed
 config ==> conductor["Orchestrator"]:::changed
 conductor ==> manager["ContainerManager"]:::changed
 manager ==> auth["package_permissions"]:::added
 manager --> runtime["Docker or Podman"]
 runtime --> agent["Agent"]
 agent ==> sudo["sudo package manager"]:::added
```

## Sequence

```mermaid
sequenceDiagram
 participant C as Orchestrator
 participant R as Container runtime
 participant A as Agent
 C->>R: Provision and verify owned identity
 C->>R: Configure sudo authorization when opted in
 R-->>C: Bounded authorization result
 C->>A: Run stage with permission and network context
 A->>R: Direct sudo package command
 R-->>A: Output and exit status
 A->>R: Adapt and retry within job bounds
```

## State

Not drawn: existing job lifecycle and recipe statuses are retained.
