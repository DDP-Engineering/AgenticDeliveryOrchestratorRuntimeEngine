<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-9bfd8e6a diagrams

## Structure

Map: NativeHelper added; chatgpt, LocalTarget, model_connection and app changed; managed Pi and credential store reused.

```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 app["web.app"]:::changed ==> auth["chatgpt"]:::changed
 auth ==> native["NativeHelper"]:::added
 native ==> pi["managed Pi"]
 auth --> store[("ChatGPT credential store")]
 auth ==> target["LocalTarget"]:::changed
 probe["model_connection"]:::changed ==> auth
 target --> pi
```

## Sequence

```mermaid
sequenceDiagram
 participant O as Operator
 participant A as ADORE
 participant H as Native helper
 participant P as Pi stage
 O->>A: Sign in and submit matching redirect
 A->>H: Managed Node helper login
 H-->>A: Signed in
 A->>H: Token valid for stage plus margin
 H-->>A: Access token
 A->>P: Launch-only environment
 P-->>A: Redacted evidence
```

## State

Not drawn: existing sign-in states and transitions are reused unchanged.
