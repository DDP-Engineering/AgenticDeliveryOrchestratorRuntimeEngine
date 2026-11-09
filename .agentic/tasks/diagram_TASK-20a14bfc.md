<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-20a14bfc diagrams

The task design defines the behavior. App and UserCreation change; PasswordField is added.

## Structure

```mermaid
flowchart LR
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef added fill:#e1f5ee,stroke:#0f6e56
    app["App"]:::changed --> user["UserCreation"]:::changed
    app ==> field["PasswordField"]:::added
    user ==> field
```

## Sequence

Not drawn: the confirmation has no new API interaction.

## State

```mermaid
stateDiagram-v2
    Identity --> Identity: Missing or mismatching confirmation
    Identity --> Access: Matching confirmation
    Access --> Identity: Correct identity
    Access --> Review: Review account
    Review --> Identity: Correct identity
```
