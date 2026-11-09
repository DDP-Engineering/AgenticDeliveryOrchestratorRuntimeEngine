<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-c9cb9476 diagrams

Design is authoritative. Nodes: WebStore changed; app changed; App changed.

## Structure
```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 store["WebStore"]:::changed --> api["app"]:::changed --> ui["App"]:::changed
```
## Sequence
```mermaid
sequenceDiagram
 participant UI as App
 participant API as app
 participant Store as WebStore
 UI->>API: session or me
 API->>Store: current account status
 Store-->>API: boolean
 API-->>UI: session status
```
## State
```mermaid
stateDiagram-v2
 FactoryPassword --> ChangedPassword: change or reset
```
