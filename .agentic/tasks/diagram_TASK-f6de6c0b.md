<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-f6de6c0b diagrams

Illustrates Design in TASK-f6de6c0b.md; the Design text is authoritative.
Node map: BoundTarget, ContainerBackend and Orchestrator are changed;
ContainerManager, runtime and original CommandResult are reused unchanged.

## Structure

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    conductor["Orchestrator"]:::changed --> bound["BoundTarget"]:::changed
    bound ==> backend["ContainerBackend timeout admission"]:::changed
    backend ==> manager["ContainerManager identity / interrupt / start"]
    manager --> runtime["Docker / Podman / WSL runtime"]
    bound --> result["Original CommandResult"]
```

## Sequence

```mermaid
sequenceDiagram
    participant C as Orchestrator
    participant B as BoundTarget
    participant E as ContainerBackend
    participant R as ContainerManager / runtime
    C->>B: command and deadline
    B->>R: verify running identity; execute immutable ID
    R-->>B: original timed-out result
    B->>E: settle timeout for captured identity
    E->>R: verify; interrupt exact ID; verify exited
    E-->>B: retain pending resume
    B-->>C: original timed-out result unchanged
    C->>B: later admitted command
    B->>E: resume pending original resource
    E->>R: verify exited; start same ID; verify running
    E-->>B: verified running identity
    B->>R: execute command on immutable ID
```

## State

```mermaid
stateDiagram-v2
    [*] --> Running
    Running --> Running: ordinary result
    Running --> Quiescing: reported timeout
    Quiescing --> Parked: verified same-resource exit
    Quiescing --> Blocked: unconfirmed or failed control
    Parked --> Resuming: later admitted command
    Resuming --> Running: verified same-resource start
    Resuming --> Blocked: ownership or runtime failure
    Parked --> Stopped: operator lifecycle control
    Blocked --> [*]: terminal recovery failure
```
