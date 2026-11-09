<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-63cb3a30 diagrams

Changed nodes are raw actions, import page and import preview. The exact configuration store is reused.

## Structure

```mermaid
flowchart LR
    classDef changed fill:#faeeda,stroke:#854f0b
    Store["Saved configuration"] --> Export["Raw export"]:::changed
    Export --> File["TOML file"]
    File --> Import["Import page"]:::changed
    Import --> Preview["Import preview"]:::changed
    Import --> Publish["Locked stopped enrollment"]
```

## Sequence

```mermaid
sequenceDiagram
    participant Operator as Administrator
    participant Form as Import form
    participant API as Existing project API
    Operator->>Form: Select file and validate
    Form->>API: Exact bytes and optional identity
    API-->>Form: Validated identity and bound preview
    Operator->>Form: Confirm import
    Form->>API: Reviewed bytes, resolved identity and revision
    API-->>Form: Created project with monitoring paused
```

## State

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Validated: Successful validation
    Validated --> Draft: Edit source or identity
    Validated --> Imported: Confirm exact current candidate
    Validated --> Draft: Failed confirmation
```
