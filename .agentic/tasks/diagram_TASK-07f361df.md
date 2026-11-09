<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-07f361df diagrams

Illustrates Design in TASK-07f361df.md.

## Structure

Picker added. Settings, inventory API and doctor changed. Runner reused.

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    Settings:::changed --> Picker:::added --> Inventory:::changed --> Doctor:::changed --> Runner
```

## Sequence

```mermaid
sequenceDiagram
    participant Settings
    participant Inventory
    participant Host
    Settings->>Inventory: Edit runtime and request suggestions
    Inventory->>Host: Fixed CLI version probes
    Inventory-->>Settings: Detected commands
    Settings->>Settings: Select or type command in draft
```

## State

```mermaid
stateDiagram-v2
    [*] --> Editing
    Editing --> Detected: Choose detected command
    Editing --> Manual: No match or discovery unavailable
    Detected --> Manual: Choose manual command
    Manual --> Detected: Choose detected command
    Detected --> [*]: Save or cancel
    Manual --> [*]: Save or cancel
```
