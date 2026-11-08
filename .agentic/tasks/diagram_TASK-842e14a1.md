<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-842e14a1 diagrams

Illustrates the Design in the task journal. The Design text is authoritative.

## Structure

Node map: cli, web store and History changed; ledger added.

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    cli["cli"]:::changed ==> ledger["deletion ledger"]:::added
    ledger ==> store["WebStore"]:::changed
    store --> history["AuditHistory"]:::changed
```

## Sequence

```mermaid
sequenceDiagram
    participant CLI as CLI
    participant Ledger as Deletion ledger
    participant Engine as Orchestrator
    participant Web as WebStore
    CLI->>Ledger: Record uncertain attempt
    CLI->>Engine: Delete job
    Engine-->>CLI: Outcome
    CLI->>Ledger: Confirm success
    Web->>Ledger: Import evidence once
```

## State

```mermaid
stateDiagram-v2
    [*] --> uncertain: begin
    uncertain --> applied: confirmed deletion
    uncertain --> uncertain: interrupted
```
