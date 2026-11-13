<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-3ca87e3e diagrams

Illustrates Design in TASK-3ca87e3e.md.

## Structure

Changed: RawConfiguration, SettingsList. Unchanged: raw API, recipe API, browser.

```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 settings["SettingsList"]:::changed ==> dialog["RawConfiguration definitionOnly"]:::changed
 export["RawConfiguration read"]:::changed ==> browser["Browser destination picker"]
 export --> raw["config/raw API"]
 dialog --> recipes["executor-recipe API"]
```

## Sequence

```mermaid
sequenceDiagram
 participant User
 participant RawConfiguration
 participant Browser
 participant API
 User->>RawConfiguration: Export
 RawConfiguration->>Browser: Select destination (when supported)
 Browser-->>RawConfiguration: File handle
 RawConfiguration->>API: Complete container export or native TOML
 API-->>RawConfiguration: Validated bytes
 RawConfiguration->>Browser: Save bytes
```

## State

```mermaid
stateDiagram-v2
 [*] --> Idle
 Idle --> Saving: Export
 Saving --> Idle: Cancel or save
 Saving --> Error: Read or write failure
 Error --> Idle: Close
```
