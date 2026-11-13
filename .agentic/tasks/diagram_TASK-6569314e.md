<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-6569314e diagrams

Illustrates the journal Design; it is authoritative.

## Structure

Added: project_bundle. Changed: RawImportDialog, bundle routes, RecipeStore.
Unchanged: parse_recipe, existing paused project publication.

```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 ui["RawImportDialog"]:::changed ==> api["bundle import routes"]:::changed
 api ==> bundle["project_bundle"]:::added
 bundle ==> parser["parse_recipe"]
 api ==> store["RecipeStore"]:::changed
 store ==> publish["_publish_paused"]
```

## Sequence

```mermaid
sequenceDiagram
 participant User
 participant Dialog as RawImportDialog
 participant API as Bundle routes
 participant Sources as RecipeStore
 participant Profile as Paused publisher
 User->>Dialog: Choose exported ZIP
 Dialog->>API: Preview exact source
 API->>Sources: Validate and snapshot associations
 API-->>Dialog: Valid bound preview
 User->>Dialog: Import
 Dialog->>API: Same bytes and revision
 API->>Sources: Lock and recheck associations
 Sources->>Sources: Retain absent bindings
 Sources->>Profile: Publish paused project with native rechecks
 alt Success
 Profile-->>User: Imported
 else Publication failure
 Sources->>Sources: Remove only own new bindings
 API-->>Dialog: Typed error
 end
```

## State

```mermaid
stateDiagram-v2
 [*] --> Empty
 Empty --> Validating: Select TOML or ZIP
 Validating --> Ready: Valid exact preview
 Validating --> Invalid: Rejected
 Ready --> Importing: Import
 Ready --> Validating: Select another file
 Importing --> Complete: Published
 Importing --> Invalid: Stale or failed
```
