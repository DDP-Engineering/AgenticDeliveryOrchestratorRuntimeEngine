<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-97525d02 diagrams

Projects, raw import and enrollment change. TransferWizard is removed. The API is reused.

## Structure

```mermaid
flowchart LR
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    Projects:::changed --> ImportDialog:::changed
    Projects --> EnrollmentWizard:::changed
    ImportDialog --> ImportAPI
    TransferWizard:::removed
```

## Sequence

```mermaid
sequenceDiagram
    participant Admin
    participant Dialog
    participant API
    Admin->>Dialog: Select TOML
    Dialog->>API: Validate exact file
    API-->>Dialog: Findings or bound preview
    Admin->>Dialog: Confirm valid file
    Dialog->>API: Publish stopped project
```

## State

```mermaid
stateDiagram-v2
    [*] --> Empty
    Empty --> Validating: Select file
    Validating --> Ready: Valid preview
    Validating --> Failed: Invalid preview
    Ready --> Validating: Select replacement
    Failed --> Validating: Select replacement
    Ready --> Importing: Confirm
    Importing --> Failed: Rejected
    Importing --> [*]: Published
```
