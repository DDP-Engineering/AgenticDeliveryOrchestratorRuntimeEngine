<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-cadbef92 diagrams

## Structure

Map: resource_lock added; WorktreeManager, metrics, ChatGPT refresh, Pi install,
StateStore and archive/delete changed; executor reused unchanged.

```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 git["WorktreeManager"]:::changed ==> lock["resource_lock"]:::added
 metrics["metrics"]:::changed ==> lock
 auth["ChatGPT refresh"]:::changed ==> lock
 pi["Pi install"]:::changed ==> lock
 project["archive/delete"]:::changed ==> state["StateStore barrier"]:::changed
 executor["executor"]
```

## Sequence

```mermaid
sequenceDiagram
 participant A as Run A
 participant L as Repository lock
 participant B as Run B
 A->>L: acquire for worktree mutation
 B->>L: bounded wait
 A->>L: release
 B->>L: acquire and release
 Note over A,B: agents execute independently outside lock
```

## State

Not drawn: no lifecycle or status transition is added.
