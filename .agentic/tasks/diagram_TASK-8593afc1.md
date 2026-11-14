<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-8593afc1 diagrams
Illustrates the journal Design, which is authoritative.

## Structure
Map: app, WebStore, supervisor, environment, profile reads, model cleanup and browser
callers changed; ConfigurationWorker added. Existing run processes are reused.
```mermaid
flowchart LR
 classDef added fill:#e1f5ee,stroke:#0f6e56
 classDef changed fill:#faeeda,stroke:#854f0b
 classDef removed stroke-dasharray:4 3
 app["app.py existing routes"]:::changed ==> queue["ConfigurationTasks / ConfigurationWorker"]:::added
 supervisor["configuration_loop"]:::changed ==> queue
 queue ==> store["WebStore exact scoped claims"]:::changed
 queue ==> handlers["app.py reviewed handlers"]:::changed
 handlers ==> environment["EnvironmentPreparation.prepare"]:::changed
 handlers --> model["probe_model_connection"]:::changed
 model ==> queue
 queue ==> profiles["ProfileStore bounded reads"]:::changed
 browser["completedConfiguration"]:::changed ==> app
```
## Sequence
```mermaid
sequenceDiagram
 participant Browser
 participant API
 participant Store as WebStore
 participant Worker as ConfigurationWorker
 Browser->>API: reviewed settings request
 API->>Store: opaque scoped request
 API-->>Browser: 202 identity and status
 Worker->>Store: claim and authorize
 Worker->>Worker: probe without edit/admission locks
 Worker->>Store: reauthorize and confirm outcome
 Browser->>API: operation status
 API-->>Browser: durable status and actual outcome
```
## State
```mermaid
stateDiagram-v2
 [*] --> pending
 pending --> running: authorized claim
 pending --> failed: revoked authority
 running --> succeeded: confirmed result
 running --> failed: stale/conflict/refusal
 running --> uncertain: owner dies
```
