<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-5a699c9f diagrams

Changed components are App and AuditHistory. The polling helper and API are reused.

## Structure

```mermaid
flowchart LR
    classDef changed fill:#faeeda,stroke:#854f0b
    App["App"]:::changed --> Audit["AuditHistory"]:::changed
    Polling["startVisiblePolling"] --> Audit
    Audit --> API["Audit page API"]
```

## Sequence

```mermaid
sequenceDiagram
    participant Timer as Visible timer
    participant History as Project History
    participant API as Audit page API
    Timer->>History: 15-second tick
    History->>API: Read page for current project and filters
    API-->>History: Page of evidence
    History->>History: Validate scope and update visible rows
```

## State

Not drawn. The existing loading, ready and error states apply to both views.
