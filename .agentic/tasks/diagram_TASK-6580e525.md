<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-6580e525 diagrams

Illustrates Design in TASK-6580e525.md. Design is authoritative.

## Structure
Map: status projection and ProjectCapacity added; app/store/SettingsList changed; supervisor reused.
```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 UI["ProjectCapacity"]:::added ==> API["app.py"]:::changed
 API ==> Status["status.py"]:::added
 Status ==> Store["WebStore"]:::changed
 Status ==> State["StateStore"]
 Draft["SettingsList"]:::changed ==> Session["sessionStorage"]
 Supervisor["Supervisor"] --> Store
```

## Sequence
```mermaid
sequenceDiagram
 participant UI as ProjectCapacity
 participant API as app.py
 participant DB as WebStore
 UI->>API: GET scoped capacity and latest own operations
 API->>DB: read validated role and operation evidence
 DB-->>API: scoped snapshot
 API-->>UI: slots, queue causes, actual outcomes
```

## State
Not drawn: lifecycle and operation transitions are unchanged.
