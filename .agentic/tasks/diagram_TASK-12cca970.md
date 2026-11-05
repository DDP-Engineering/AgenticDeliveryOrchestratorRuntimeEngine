<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-12cca970 diagrams

Design in TASK-12cca970.md is authoritative.

## Structure

Node map: JobWorkspace, CommandWorker, CLI, Orchestrator, LocalBackend and WorktreeManager changed; StateStore reused.

```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 ui["JobWorkspace"]:::changed ==> worker["CommandWorker"]:::changed
 worker ==> cli["CLI"]:::changed
 cli ==> engine["Orchestrator"]:::changed
 engine ==> native["LocalBackend"]:::changed
 engine ==> git["WorktreeManager"]:::changed
 engine --> state["StateStore"]
```

## Sequence

```mermaid
sequenceDiagram
 participant UI as JobWorkspace
 participant W as CommandWorker
 participant C as CLI
 participant E as Orchestrator
 UI->>W: confirmed revision-bound restart
 W->>C: restart with expected revision
 C->>E: locked owned cleanup
 E-->>C: verified cleanup or typed refusal
 C->>E: fresh manual admission on success
 C-->>W: bounded command outcome
 W-->>UI: persisted result
```

## State

```mermaid
stateDiagram-v2
 failed --> failed: cleanup refused, retain evidence
 failed --> Removed: verified owned cleanup
 Removed --> working: eligible manual start
 Removed --> Refused: fresh admission rejected
```
