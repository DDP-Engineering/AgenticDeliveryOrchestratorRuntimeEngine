<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# Password form diagrams

The design is authoritative. Changed nodes: App, translations; API is unchanged.

## Structure
```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 app["App"]:::changed --> api["Password API"]
 app --> copy["translations"]:::changed
```
## Sequence
```mermaid
sequenceDiagram
 participant User
 participant App
 participant API
 User->>App: Enter and confirm password
 App->>API: Matching current and new values
```
## State
Not drawn: the change adds no durable lifecycle state.
