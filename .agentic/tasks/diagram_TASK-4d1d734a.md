<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-4d1d734a diagrams

Illustrates Design in TASK-4d1d734a.md; Design is authoritative.

## Structure

Map: instructions.py and InstructionComposer added; app.py, orchestrator.py,
PiExecutor and run_pi_rpc changed; StateStore and PromptCatalog reused unchanged.

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    ui["InstructionComposer"]:::added ==> api["app.py"]:::changed
    api ==> inbox["instructions.py"]:::added
    conductor["orchestrator.py"]:::changed ==> inbox
    conductor ==> executor["PiExecutor"]:::changed
    executor ==> rpc["run_pi_rpc"]:::changed
    rpc ==> inbox
    inbox ==> prompts["PromptCatalog"]
    conductor ==> store["StateStore"]
```

## Sequence

```mermaid
sequenceDiagram
    participant Web as app.py
    participant Inbox as instructions.py
    participant RPC as run_pi_rpc
    participant Pi
    participant Conductor as orchestrator.py
    participant Forge
    Web->>Inbox: atomic enqueue
    RPC->>Inbox: pending records
    RPC->>Pi: steer or follow_up
    Pi-->>RPC: matching success acknowledgement
    RPC->>Inbox: atomic delivery receipt
    RPC->>Conductor: reconcile local receipt
    Conductor->>Conductor: durable outbox then journal event
    Conductor->>Forge: after session, stable marker comment
```

## State

```mermaid
stateDiagram-v2
    [*] --> Queued: atomic enqueue
    Queued --> Queued: rejection, no ack, session end or restart
    Queued --> Delivered: matching command or prompt ack persisted
    Delivered --> Delivered: forge replay independent
```
