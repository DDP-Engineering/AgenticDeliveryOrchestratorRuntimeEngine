<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-4aea4dea diagrams

Illustrates Design in TASK-4aea4dea.md.

## Structure

App, list_projects, JobWorkspace and jobs_page change. read_overview_jobs is added. _sources is reused.

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    app["App"]:::changed --> projects["list_projects"]:::changed
    app ==>|Overview metadata fallback| projects
    workspace["JobWorkspace"]:::changed --> api["jobs_page"]:::changed
    api ==> overview["read_overview_jobs"]:::added
    overview ==> sources["_sources"]
```

## Sequence

```mermaid
sequenceDiagram
    participant UI as JobWorkspace
    participant API as jobs_page
    participant Jobs as read_overview_jobs
    UI->>API: Request an Overview page
    API->>Jobs: Read authorized project scope
    loop Each authorized project
        Jobs->>Jobs: Capture and validate saved job evidence
    end
    Jobs->>Jobs: Recheck the complete captured scope
    Jobs-->>API: Verified rows, revision and unreadable project IDs
    API-->>UI: Verified page and unreadable project IDs
```

## State

Not drawn because no job lifecycle or state transition changes.
