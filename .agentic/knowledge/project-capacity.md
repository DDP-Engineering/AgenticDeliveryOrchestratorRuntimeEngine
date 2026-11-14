<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project capacity and worker status

## Routing

Use for effective project concurrency, staged lower admission limits, queue causes, role diagnostics, retained settings drafts and durable own-operation feedback. Start at `adore/capacity.py`, `adore/web/status.py`, project `/capacity` and system `/workers` routes in app.py, and frontend ProjectCapacity/settingsDrafts. Admission execution remains in orchestrator.md and process ownership in web-supervisor.md.

## Purpose and boundaries

Read-only projections explain each project's slots, requests and worker observations. The core admission reader accepts a current reviewed lower N while preserving admitted jobs' active configuration revision. Server status exposes role observations; ownership recovery remains in WebStore.

## Public interface

`admission_limit(config)`, `capacity_status`, `occupied_slots`, `worker_status`; authorized `/projects/{id}/capacity`, administrator `/system/workers`, public component-named `/ready`; `WebStore.project_operation_status`; frontend `ProjectCapacity`, `WorkerStatus`, `readCapacity/readWorkers`, bounded draft read/write/clear.

## Invariants

One canonical polling.max_concurrent_runs defaults to one. Effective admission is min(saved N, valid current staged N); increases wait for safe application. Corrupt/stale/linked/oversized staged evidence raises StateError with explicit record-discard guidance. Stage publication shares the short admission boundary. Existing admitted runs continue against unchanged bytes; queued requests and settled waits hold no executor.

Project authorization precedes reads. Public projections exclude capabilities, PIDs, credentials and other actors' completed outcomes. Heartbeat, activity and free slots remain distinct. Only supervisor/configuration determine server readiness; project absence remains local. Browser drafts store bounded editable strings/base revision per account/project/tab, never full config/credentials; stale/corrupt evidence blocks Save. Save/discard/logout clear retention. Durable server results survive navigation without resubmission.

## Change map

| Change | Entry | Proof |
|---|---|---|
| staged lower ceiling / corrupt evidence | admission_limit, stage_config | test_web_project_status.py, selected test_run_concurrency.py |
| slots/queue/results/grants | capacity_status, project_capacity, project_operation_status | test_web_project_status.py |
| role readiness | worker_status, ready, system_workers | test_web_server.py, test_web_project_status.py |
| retained drafts and localized UI | SettingsList, settingsDrafts.ts, ProjectCapacity.tsx | projectStatus.test.mjs, projectCapacity.spec.ts, help.test.mjs |

## Key behaviors

REQ-FUNC-42643886: per-project slots and request causes.
REQ-REL-329421d1: separate role/heartbeat/activity/readiness.
REQ-UX-0f6e2c63: bounded revision-bound account/project draft retention.
REQ-UX-5243a55c: restored truthful own-operation feedback.
REQ-FUNC-ed8e4793: retained unsafe apply with immediately effective lower ceiling.

## Files

`04_Software/adore/capacity.py`, `web/status.py`, scoped app/store/supervisor/orchestrator seams; `web/src/ProjectCapacity.tsx`, `projectStatus.ts`, `settingsDrafts.ts`, App and ticket/workspace integration; targeted Python/frontend/browser tests above; `05_SoftwareDocu/Component_Project_Capacity.md`.

Scoped SQL selection precedes heartbeat decoding; corrupt A observations do not break B or server readiness. Existing initial reservations wait under the reduced dispatch ceiling without cancellation or loss of authority. Staged notices distinguish lower limits from increases/unrelated edits. Retained connection drafts require validConnection, preventing invalid credential-bearing URLs from entering tab storage.


REQ-FUNC-3b737a5c: queued initial starts share the reduced ceiling through supervisor dispatch and atomic conductor activation. Pending reservations do not count as started executors; existing running execution/cleanup does. Capacity deferral leaves execution_pending and queued dispatch unchanged until an actual slot is available.

Initial activation retries brief local admission-lock contention at most 25 times with 20 ms waits outside the project lock. Exhaustion keeps queued dispatch unchanged for a later attempt. Real process-pool overlap and explicit operator-lock refusal/recovery are targeted public regressions.

Handoff-pending cleanup always occupies an initial-start slot, including a job whose executor has not yet started. The pending flag never grants permission to bypass unsafe cleanup.
