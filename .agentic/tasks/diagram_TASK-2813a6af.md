<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-2813a6af diagrams

Illustrates the Design in TASK-2813a6af.md.

## Structure

Map: pi_installation added; cli, LocalTarget and LocalProcessController changed;
pi_rpc reused.

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    cli["cli"]:::changed ==> installer["pi_installation"]:::added
    target["LocalTarget"]:::changed ==> installer
    target ==> scope["LocalProcessController"]:::changed
    target ==> rpc["pi_rpc"]
```

## Sequence

```mermaid
sequenceDiagram
    participant T as LocalTarget
    participant C as LocalProcessController
    participant R as pi_rpc
    participant P as Pi
    T->>C: Create scope and persist ownership
    C->>P: Release pinned Node and Pi
    T->>R: Lend owned pipes
    R->>P: Send prompt and request usage
    P-->>R: Settled event and usage
    T->>C: Drain scope and clear lease
```

## State

```mermaid
stateDiagram-v2
    [*] --> Missing
    Missing --> Candidate: Install
    Candidate --> Missing: Install or verification fails
    Candidate --> Ready: Verify and publish
    Ready --> Missing: Build pin changes
```
