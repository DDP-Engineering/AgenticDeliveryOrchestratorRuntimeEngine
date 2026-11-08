<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-c2099967 diagrams

Structure node map: wizard, API, catalog and launcher changed; Pi reused.

## Structure
```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 wizard["EnrollmentWizard"]:::changed ==> api["web app"]:::changed
 api ==> catalog["Pi catalog"]:::changed
 catalog ==> launcher["Pi launcher"]:::changed
 launcher --> pi["Pi RPC"]
```
## Sequence
```mermaid
sequenceDiagram
 participant W as EnrollmentWizard
 participant A as web app
 participant P as ProfileStore
 W->>A: Check reviewed draft
 A-->>W: Measured checks and opaque token
 W->>A: Create reviewed draft and token
 A->>P: Publish project and bound evidence
 A-->>W: Created project
```
## State
```mermaid
stateDiagram-v2
 [*] --> Unverified
 Unverified --> Partial: incomplete checks
 Unverified --> Verified: all checks pass
 Unverified --> Failed: check fails
 Partial --> Stale: configuration changes
 Verified --> Stale: configuration changes
 Failed --> Stale: configuration changes
```
