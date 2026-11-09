<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-a70e310f diagrams

Illustrates the journal Design, which is authoritative.

## Structure

Map: Config, Orchestrator, StateStore, web apply and Job details changed; config file reused unchanged.

```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 config["Config"]:::changed ==> conductor["Orchestrator"]:::changed
 file["config.toml"] ==> config
 conductor --> state["StateStore"]:::changed
 apply["web apply_config"]:::changed --> file
 state ==> jobs["Job details"]:::changed
 config ==> jobs
```

## Sequence

```mermaid
sequenceDiagram
 participant Admin
 participant API as apply_config
 participant File as config.toml
 participant Engine as Orchestrator
 Admin->>API: review and apply budget-only candidate
 API->>API: revision, ownership, lock and parked checks
 API->>File: publish exact reviewed bytes
 Engine->>File: reread at next attempt boundary
 Engine->>Engine: validate, retain progress and consumed work
```

## State

Per-detail budget classification; the run lifecycle is unchanged.

```mermaid
stateDiagram-v2
    [*] --> observed: Valid state and current limits
    [*] --> unavailable: Valid state, missing or corrupt limits
    observed --> [*]
    unavailable --> [*]
    note right of unavailable
      Saved evidence and recovery remain visible.
    end note
```
