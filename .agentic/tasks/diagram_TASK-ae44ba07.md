<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-ae44ba07 diagrams

Illustrates the journal Design; Design is authoritative.

## Structure

Map: App/JobDetails/TicketWorkspace/app routes changed; executor_session/sessionModel/SessionView added; archives and executor_evidence identity guard reused unchanged.

```mermaid
flowchart LR
classDef added fill:#e1f5ee,stroke:#0f6e56
classDef changed fill:#faeeda,stroke:#854f0b
classDef removed stroke-dasharray:4 3
app["web.app sessions routes"]:::changed ==> reader["executor_session"]:::added
reader ==> archive["run io/archive"]
reader ==> guards["executor_evidence identity checks"]
ui["JobDetails"]:::changed ==> session["SessionView / sessionModel"]:::added
session ==> app
nav["App routes"]:::changed ==> tickets["TicketWorkspace"]:::changed
```

## Sequence

```mermaid
sequenceDiagram
participant User
participant SessionView
participant API
participant Reader
User->>SessionView: Select Agent sessions and attempt
SessionView->>API: GET archived session page
API->>API: Authenticate and authorize saved job
API->>Reader: Read bounded complete lines
Reader-->>API: Items and next byte cursor
API-->>SessionView: no-store response
```

## State

Not drawn: no product lifecycle or stored status transition changes.
