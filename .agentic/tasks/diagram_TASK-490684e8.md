<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-490684e8 diagrams

Illustrates the Design in TASK-490684e8.md; that text is authoritative.

## Structure

Classification: CLI, Orchestrator, StateStore and WorkerContext are changed;
WebStore ownership authorization is changed to include the exact run action.

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    cli["cli._cmd_conduct"]:::changed ==> engine["Orchestrator.conduct_run"]:::changed
    engine ==> state["StateStore.run_lock and dispatch"]:::changed
    engine ==> context["WorkerContext.run_scope"]:::changed
    context ==> web["WebStore ownership"]:::changed
    engine --> executor["Executor"]
```

## Sequence

```mermaid
sequenceDiagram
    participant P as Project poller
    participant S as StateStore
    participant R as Run process
    participant E as Executor
    P->>S: Take exact run lock
    P->>S: Short admission: check capacity and reserve execution slot
    P->>S: Release admission lock
    P->>S: Allocate pinned worktree, save workflow and queued dispatch
    P->>S: Release run and execution locks after queued save
    P-->>R: run_id and exact config revision
    R->>S: Validate ownership, revision and queued dispatch
    R->>S: Atomically mark dispatch started
    R->>E: Conduct only this run
    E-->>R: Bounded result
    R->>S: Save lifecycle and finish cleanup
    R->>S: Release run and execution locks
```

## State

```mermaid
stateDiagram-v2
    [*] --> Reserved: short admission and kernel execution slot
    Reserved --> Queued: pinned workflow and dispatch saved
    Queued --> Started: exact owner and configuration validated
    Started --> Waiting: clarification, approval or review
    Waiting --> Started: atomic capacity reservation before executor resume
    Started --> Failed: failure or uncertain interrupted work
    Failed --> Started: explicit Retry and capacity reservation
    Started --> Cancelled: owner confirms cleanup
    Waiting --> Cancelled: exclusive idle cancellation
```
