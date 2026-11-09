<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-e3102c4d diagrams

Illustrates Design in TASK-e3102c4d.md. Node map: SettingsList/App and config routes changed; settingsSave.ts/settings_batch.py added; StateStore and atomic file replacement reused unchanged.

## Structure
```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 ui["SettingsList / App"]:::changed ==> draft["settingsSave.ts"]:::added
 ui ==> api["config preview/pending/apply routes"]:::changed
 api ==> batch["settings_batch.py"]:::added
 api --> state["StateStore"]
 api --> file["Atomic config replacement"]
```

## Sequence
```mermaid
sequenceDiagram
 actor Operator
 participant UI as SettingsList / App
 participant API as config routes
 participant File as Config and candidate
 Operator->>UI: Edit several settings and Save
 opt Important effects
 UI->>API: Preview batch without writes
 API->>File: Read exact base and validate final document/plan
 API-->>UI: Bound safe preview
 UI->>Operator: Confirm project, changed values and effects
 Operator->>UI: Save changes (or return with drafts retained)
 end
 UI->>API: Prepare batch with base and optional pending revision
 API->>File: Revalidate source, batch and plan
 API-->>UI: Bound safe candidate
 UI->>UI: Require exact preview hash/plan when confirmed
 UI->>API: Apply exact candidate/base
 API->>File: Locked idle/pause checks and atomic replace
 API-->>UI: Saved revision
 UI-->>Operator: Saved values and clean draft
```

## State
```mermaid
stateDiagram-v2
 [*] --> Clean
 [*] --> Recovery: API-only pending candidate
 Recovery --> Confirming: Save and reread exact candidate
 Confirming --> Applying: Confirm exact persisted candidate
 Clean --> Dirty: Edit changes value
 Dirty --> Preparing: Save
 Dirty --> Previewing: Important Save
 Previewing --> Confirming: Valid exact preview
 Previewing --> Dirty: Invalid or failed preview
 Confirming --> Preparing: Confirm
 Preparing --> Applying: Ordinary effects
 Preparing --> Applying: Prepared exact preview
 Confirming --> Dirty: Cancel
 Preparing --> Dirty: Validation or revision error
 Applying --> Dirty: Rejected or failed write
 Applying --> Clean: Saved
 Dirty --> Clean: Explicit discard
 Dirty --> Stale: Active revision changes
 Stale --> Clean: Explicit discard and reload
```
