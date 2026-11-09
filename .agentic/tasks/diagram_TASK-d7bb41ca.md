<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-d7bb41ca diagrams

Illustrates the journal Design. Node map: UI, API, selection and worker changed; operation store reused.

## Structure
```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 ui["React UI"]:::changed --> api["web app"]:::changed
 api --> selection["selection"]:::changed
 api --> store["operation store"]
 worker["CommandWorker"]:::changed --> store
 worker ==> api
```

## Sequence
```mermaid
sequenceDiagram
 participant UI as React UI
 participant API as web app
 participant Store as operation store
 participant Worker as CommandWorker
 UI->>API: confirmed request
 API->>Store: enqueue
 Worker->>Store: claim and finish actual outcome
 UI->>API: poll and refresh
```

## State
Not drawn: operation lifecycle remains unchanged; activity is transient evidence.
