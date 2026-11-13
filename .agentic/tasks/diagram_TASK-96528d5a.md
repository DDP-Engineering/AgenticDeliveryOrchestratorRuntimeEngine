<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-96528d5a diagrams

Illustrates the journal Design. Node map: WebStore, CommandWorker, CLI and Orchestrator changed; Owner/process identity added.

## Structure

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    Worker["CommandWorker"]:::changed ==> Store["WebStore"]:::changed
    Store ==> Owner["Owner/process identity"]:::added
    Worker --> CLI["CLI"]:::changed
    CLI ==> Store
    CLI --> Engine["Orchestrator"]:::changed
```

## Sequence

```mermaid
sequenceDiagram
    participant Worker as CommandWorker
    participant Store as WebStore
    participant CLI
    participant Engine as Orchestrator
    Worker->>Store: scoped atomic claim(owner, generation)
    Worker->>CLI: bound operation context
    CLI->>Store: attach process and authorize
    CLI->>Engine: admit requested ticket
    Engine->>Store: acknowledge durable admission
    Engine->>Engine: conduct job
    CLI-->>Worker: terminal job evidence
    Worker->>Store: fenced completion
```

## State

```mermaid
stateDiagram-v2
    [*] --> pending: enqueue explicit scope
    pending --> running: authorized atomic claim
    pending --> failed: revoked request
    running --> succeeded: observed admission or action
    running --> failed: confirmed refusal
    running --> uncertain: demonstrated owner death or unknown outcome
    succeeded --> [*]
    failed --> [*]
    uncertain --> [*]
```
