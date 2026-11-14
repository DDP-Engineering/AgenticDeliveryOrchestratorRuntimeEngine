<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-1921263d diagrams

Illustrates the authoritative Design. Node map: Supervisor, ProjectWorker, ProcessTree added;
commands.main and WorkerContext changed; StateStore reused unchanged.

## Structure

```mermaid
flowchart TD
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 entry["commands.main"]:::changed ==> supervisor["Supervisor"]:::added
 supervisor ==> project["ProjectWorker"]:::added
 supervisor ==> config["CommandWorker configuration consumer"]:::changed
 project ==> tree["ProcessTree"]:::added
 tree ==> context["WorkerContext"]:::changed
 context ==> state["StateStore"]
```

## Sequence

```mermaid
sequenceDiagram
 participant S as Supervisor
 participant P as ProjectWorker
 participant A as Admission CLI
 participant R as Run CLI
 S->>P: launch by project_id
 P->>A: run --once --admit-only
 A-->>P: durable reservation
 P->>R: conduct run --config-revision
 Note over P,R: polling and other runs continue
 R-->>P: observed exit; durable lifecycle retained
```

## State

```mermaid
stateDiagram-v2
 [*] --> Discovered
 Discovered --> Running: owned gated launch
 Running --> Stopping: Stop or parent loss
 Running --> Discovered: proven child death and bounded backoff
 Stopping --> Stopped: tree drained
 Stopped --> [*]
```
