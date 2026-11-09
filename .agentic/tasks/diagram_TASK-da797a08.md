<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-da797a08 diagrams

Illustrates Design in TASK-da797a08.md. Design is authoritative.

## Structure

Map: JobWorkspace, app, analytics/store, Pi RPC/launcher and orchestrator changed; diagnostics, executor_evidence and the host snapshot added; ForgeMarkdown reused unchanged.

```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 rpc["pi_rpc / launcher"]:::changed ==> normalize["diagnostics"]:::added
 normalize ==> conductor["orchestrator"]:::changed
 conductor ==> snapshot[("host snapshot and journal")]:::added
 ui["JobWorkspace"]:::changed ==> md["ForgeMarkdown"]
 ui ==> api["app.job_executor_output"]:::changed
 api ==> evidence["executor_evidence"]:::added
 evidence ==> snapshot
 api --> usage["analytics / store"]:::changed
```

## Sequence

```mermaid
sequenceDiagram
 participant Pi as pi_rpc
 participant Engine as orchestrator
 participant UI as JobWorkspace
 participant API as app / executor_evidence
 Pi->>Pi: credential redaction and canonical diagnostics
 Pi-->>Engine: GateRun with optional diagnostics
 Engine->>Engine: snapshot outside IO and journal digest, or missing marker
 UI->>API: request latest output
 API->>API: authorize, strict selected snapshot, identity/digest/grammar checks
 API->>API: recheck project grant
 API-->>UI: concrete operational facts or safe unavailable/error
```

## State

Not drawn: lifecycle and stage transitions remain unchanged.
