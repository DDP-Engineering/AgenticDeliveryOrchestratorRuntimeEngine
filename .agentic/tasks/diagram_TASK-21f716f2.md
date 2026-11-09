<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-21f716f2 diagrams

The journal Design is authoritative.

## Structure

Node map: orchestrator changed; forge and state store unchanged.

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    orchestrator["Orchestrator"]:::changed --> forge["Forge"]
    orchestrator --> store[("StateStore")]
```

## Sequence

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant S as StateStore
    participant F as Forge
    O->>S: Load pending status
    O->>F: Deliver current status and labels
    O->>S: Remove record only on success
```

## State

Not drawn: no lifecycle transitions are added or changed.
