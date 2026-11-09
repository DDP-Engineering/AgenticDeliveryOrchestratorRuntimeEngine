<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-e51f205c diagrams

The task journal's Design is authoritative. The polling helper and API are unchanged.

## Structure

```mermaid
flowchart LR
    classDef changed fill:#faeeda,stroke:#854f0b
    polling["startVisiblePolling"] --> app["App"]:::changed
    polling --> access["ProjectAccess"]:::changed
    polling --> audit["AuditHistory"]:::changed
    settings["SettingsList"]:::changed --> app
    credentials["API key and ChatGPT sign-in"]:::changed --> app
    app --> api["Existing API reads"]
    access --> api
    audit --> api
```

## Sequence

```mermaid
sequenceDiagram
    participant Poll as startVisiblePolling
    participant View as App
    participant API as Existing configuration API
    Poll->>View: Visible interval
    View->>API: Read saved settings while clean
    Note over View: An edit or write in any Settings form invalidates the read
    API-->>View: Saved configuration
    Note over View: Discard superseded result
```

## State

```mermaid
stateDiagram-v2
    [*] --> Clean
    Clean --> Protected: Edit or begin write
    Protected --> Clean: Resolve edits and finish write
    Clean --> Clean: Visible refresh
```
