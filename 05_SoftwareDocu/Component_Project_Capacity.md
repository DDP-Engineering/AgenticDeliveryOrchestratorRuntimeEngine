<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project Capacity and Worker Status

## 1. Purpose

Expose project capacity and durable operation feedback without treating a busy project as a server outage. One canonical field, `polling.max_concurrent_runs`, defaults to one.

## 2. Responsibilities

`adore/capacity.py:admission_limit` rereads saved N and a current reviewed candidate. A staged lower N immediately fences new Start/Retry/resume reservations; staged increases wait for safe application. Already-running executors retain exact active configuration bytes and continue; pending reservations wait for current execution-start capacity without losing dispatch authority. Explicit discard removes the staged ceiling. The conductor and project dispatcher share this reader.

`adore/web/status.py` projects distinct occupied reservations, queued requests, admitted runs awaiting dispatch and role observations. Parked settled waits do not reserve places; live execution locks and unsettled cleanup do. Worker heartbeat freshness, activity and admission availability are separate facts.

## 3. Implementation Overview

`GET /api/v1/projects/{name}/capacity` resolves immutable project identity and grants before reading. The read combines state, configuration, unfinished requests, current workers and latest own request per action. It performs no forge, model or runtime check and changes no state.

`GET /api/v1/system/workers` is administrator-only and names server/project roles plus active run/control workers. `GET /api/v1/ready` requires recent supervisor and server configuration-worker observations; 503 names missing server components. Missing project workers remain local to their project.

## 4. Dependencies

Typed config, schema-1 state, existing schema-1 pending settings and the current WebStore operation/owner store. React components reuse visible polling, localized errors and existing help. No operational global setting or process option is added.

## 5. Inputs And Outputs

Capacity returns `project_id`, effective `limit`, `active_limit`, `occupied`, `free`, `waiting_jobs`, `available`, `worker`, `queue`, `waiting_runs`, `staged_change`, `staged_limit` and `recent_operations`. Queue reasons are `project_limit`, `worker_unavailable`, `same_job`, `staged_change` and `dispatching`. Queued jobs count submitted execution requests and admitted pending dispatch, not unrequested forge tickets. Cancel is not held by a full project.

Role observations contain role, project/run scope, `heartbeat` (recent/stale/missing), observed `activity` (busy/idle/unknown) and last timestamp. Public status carries no PID, owner capability or credential. Own configuration outcome errors are reduced to their public code.

## 6. Data Contracts

A staged candidate must match the current source base/candidate hash and contain a positive integer N. Corrupt, stale, linked or oversized evidence fails closed with StateError and explicit pending-record deletion guidance; HTTP returns `project_capacity_unavailable`. A reduced N below occupancy retains the active file/candidate and returns `capacity_below_occupancy`; the lower admission ceiling already applies. A stale candidate never becomes a silent default.

Browser drafts store only bounded editable strings, base revision and editor keys in per-account/immutable-project `sessionStorage`. Full config and credentials are excluded. Navigation/reload retains drafts; explicit save/discard and logout remove them. Changed revisions block Save, and damaged storage requires explicit Discard. Storage failure keeps in-memory edits and asks the operator to retain the page or discard.

## 7. Workflow Integration

Project Summary/Settings/Jobs keep capacity and latest own results visible. Global Jobs names each project's card. Accepted/pending/running operations remain distinct from confirmed success; revisiting reads server evidence without resubmitting. Settings choices remain per project; System status is informational.

## 9. Validation And Tests

`tests/test_web_project_status.py` covers scope/grants, corrupt evidence, missing/stale workers, settings/portable defaults, independent saves and occupancy 2 -> staged N=1 -> occupancy 1 refusal -> occupancy 0 admission. Existing admissions continue against unchanged bytes.

`web/tests/projectStatus.test.mjs` covers transport/storage boundaries. `web/e2e/projectCapacity.spec.ts` covers real draft navigation/reload/staleness, localized capacity/result restoration and separate role presentation with screenshots. Targeted worker, settings and concurrency regressions complement these contracts. Live forge/model/runtime acceptance is separate.

Worker reads select relevant role/project rows before decoding heartbeat records: corrupt project A observations refuse A but leave B and server readiness readable. Initial working/execution_pending reservations retain their queued authority but wait for the current execution-start ceiling. Started execution/cleanup slots are counted separately from pending reservations, preventing both an unlimited start bypass and a pending-reservation deadlock. Staged copy is neutral for increases/unrelated changes and names an effective lower ceiling only when staged N < active N. Connection drafts pass the closed validConnection transport before persistence, so invalid credential-bearing endpoints stay in memory with retention warning.


REQ-FUNC-3b737a5c: queued initial starts share the reduced ceiling through supervisor dispatch and atomic conductor activation. Pending reservations do not count as started executors; existing running execution/cleanup does. Capacity deferral leaves execution_pending and queued dispatch unchanged until an actual slot is available.

Initial activation retries brief local admission-lock contention at most 25 times with 20 ms waits outside the project lock. Exhaustion keeps queued dispatch unchanged for a later attempt. Real process-pool overlap and explicit operator-lock refusal/recovery are targeted public regressions.

Handoff-pending cleanup always occupies an initial-start slot, including a job whose executor has not yet started. The pending flag never grants permission to bypass unsafe cleanup.
