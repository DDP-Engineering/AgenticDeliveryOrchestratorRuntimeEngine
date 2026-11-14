<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-4f256bac diagrams

Illustrates the journal Design. Classification: PiExecutor, executor_session, SessionView and sessionModel changed; authenticated API route changed.

## Structure

```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 launcher["PiExecutor"]:::changed ==> reader["executor_session"]:::changed
 reader ==> api["app.job_session"]:::changed
 api ==> view["SessionView"]:::changed
 view ==> model["sessionModel"]:::changed
```

## Sequence

```mermaid
sequenceDiagram
 participant PiExecutor
 participant reader as executor_session
 participant view as SessionView
 PiExecutor->>PiExecutor: Clear output and publish live marker
 view->>reader: List and read live cursor
 reader-->>view: Completed items and continuity
 loop Every 3 seconds while visible and working
 view->>reader: Cursor and continuity
 reader-->>view: Completed items or session_ended
 end
 PiExecutor->>PiExecutor: Archive then remove marker
 view->>reader: Refresh attempts and select archive or new live
```

## State

```mermaid
stateDiagram-v2
 [*] --> History
 History --> Following: Select live
 Following --> Suspended: Hidden or not working
 Suspended --> Following: Visible working live
 Following --> Following: Append / safe cursor
 Following --> History: Ended without next live
 Following --> Following: Ended / next live
 Following --> History: User selects archive
```
