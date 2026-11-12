<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-0067fee1 diagrams

Illustrates the design in TASK-0067fee1.md.

## Structure

Changed: config, web settings, conductor. Reused: forge.

```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 web["Web settings"]:::changed ==> config["DeliveryConfig"]:::changed
 config ==> conductor["Orchestrator"]:::changed
 conductor --> forge["Forge adapter"]
```

## Sequence

```mermaid
sequenceDiagram
 participant Admin
 participant Settings
 participant Orchestrator
 participant Forge
 Admin->>Settings: Save project policy
 Settings->>Orchestrator: Provide policy
 Orchestrator->>Orchestrator: Validate and check freshness
 Orchestrator->>Forge: Present for approval or publish
```

## State

```mermaid
stateDiagram-v2
 working --> awaiting_approval: policy enabled
 working --> publishing: policy disabled and fresh
 awaiting_approval --> publishing: approved or policy disabled and fresh
 publishing --> in_review: published
```
