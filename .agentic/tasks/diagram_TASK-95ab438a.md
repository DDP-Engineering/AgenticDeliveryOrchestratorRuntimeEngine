<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-95ab438a diagrams

Illustrates the task journal Design, which is authoritative.

Node map: ContainerManager changed (provision/exec binding responsibility);
container.git added (IO binding data); native Git, host pointer, runtime and
managed linked worktree reused unchanged.

## Structure

```mermaid
flowchart LR
  classDef added fill:#e1f5ee,stroke:#0f6e56
  classDef changed fill:#faeeda,stroke:#854f0b
  classDef removed stroke-dasharray:4 3
  manager["ContainerManager"]:::changed ==> pointer["IO container.git"]:::added
  manager --> runtime["Docker or Podman"]
  pointer ==> worktree["Linked worktree .git overlay"]
  worktree ==> git["Native Git discovery"]
  host["Host .git pointer"] --> worktree
```

## Sequence

```mermaid
sequenceDiagram
  participant M as ContainerManager
  participant F as IO pointer file
  participant R as Container runtime
  participant G as Native Git
  M->>F: Admit exact pointer bytes
  M->>R: Create labelled container with read-only overlay
  M->>R: Check selection environment and pointer
  R->>G: Resolve main linked worktree
  G-->>R: Native paths
  R-->>M: Exact acknowledgement
```

## State

```mermaid
stateDiagram-v2
  [*] --> Absent
  [*] --> Legacy: observed existing empty mode
  Absent --> PointerV1: fresh valid binding
  Legacy --> Legacy: retain or start same resource
  PointerV1 --> PointerV1: valid warm evidence
  PointerV1 --> Rejected: corrupt evidence
  Absent --> Rejected: invalid metadata
  [*] --> Rejected: unknown mode
```
