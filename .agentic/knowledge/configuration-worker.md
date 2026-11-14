<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Scoped configuration control

## Routing

Use for long settings/host/model/image work, durable control results, revision/access
fencing, per-project isolation, shared ChatGPT and worker-owned enrollment. Start at
`04_Software/adore/web/configuration.py`, its route decorators in `web/app.py` and
`supervisor.configuration_loop`; focused proof is `tests/test_web_configuration_worker.py`.
Run/process containment belongs to web-supervisor.md; ordinary queue/identity to web-interface.md.

## Purpose and boundaries

A separate configuration process invokes the existing typed API handlers using
bounded fast/long/shared-auth lanes and short scoped publication. Project/run workers
own admission/execution; immediate Pause/Resume and existing Cancel signalling stay
independent of every long-work pool. Server enrollment retains an explicit prospective
target; operational settings always publish only to their own project.

## Public interface

`ConfigurationTasks.route/read/outcome`, `ConfigurationWorker.tick/execute/close`,
`effect_guard`, `probe_timeout`, private record read/write helpers and
`EnvironmentPreparation.prepare`. Existing long mutation/probe routes return 202
`{id,status,domain,project_id}`; administrator operation reads expose confirmed
`outcome:{status_code,body}`. `completedConfiguration` is the browser bridge.

## Invariants

No active-profile fallback. Resolve name and immutable ID together and refuse
ambiguity. One configure task per project; resource-specific global serialization.
Four fast/four long/one auth slots plus a deletion lane; 256 pending/running requests,
32 MiB records and a 3600-second total task budget. Native/preparation plans and
recipe/model/readiness/environment work use long capacity. Queued inputs are salted
content-bound protected references; no secret values enter SQLite/history/status.
Rights/config/credential fingerprints and source/pending revisions are checked at
execution and immediately before publication. Long probes/builds hold no edit or
admission locks. Unknown/conflicting outcomes refuse; post-effect confirmation
failure is uncertain. Interrupted claims never replay. Corrupt/foreign records
remain refused with explicit deletion guidance. Runtime shared-image reservations
use short locked PID/birth/token claims and demonstrated-death recovery.

## Change map

| Change | Entry | Focused proof |
|---|---|---|
| HTTP acceptance/result/security | ConfigurationTasks, app decorators | test_web_configuration_worker.py |
| pool/scope/control | ConfigurationWorker.tick | barrier and native-plan tests |
| real process integration | configuration_loop | actual_configuration_process test |
| managed images | EnvironmentPreparation.prepare/_reservation | managed_image_build test, test_web_environment.py |
| browser wait | configurationTasks.ts | configurationTasks.test.mjs |

## Key behaviors

- REQ-FUNC-80b5347e: durable explicit acceptance and confirmed outcome.
- REQ-FUNC-5afa4cd1: bounded independent configuration lanes.
- REQ-SEC-13dc5428: current authority, revision and identity fences.
- REQ-SEC-ec87820f: protected credentials and opaque queue references.
- REQ-REL-4c269cd5: unsafe changes retain staged candidates with explicit conflict.
- REQ-FUNC-bee68a72: immediate admission controls outside long/executor capacity.

## Files

`web/configuration.py`, `web/environment.py`, `web/app.py`, `web/store.py`,
`web/executor_settings.py`, `web/supervisor.py`, `web/src/configurationTasks.ts`,
its App/recipe/enrollment/import callers, `tests/configuration_client.py`,
`tests/test_web_configuration_worker.py`, and
`05_SoftwareDocu/Component_Configuration_Worker.md`.

Settings GET performs no live execution-plan probe: it reads strict current
`execution-plan.json` evidence refreshed by explicit host check or reviewed apply,
with null for absent/stale evidence and deletion guidance for corrupt/foreign data.
Exact inspected operation IDs bind each claim to its chosen lane/resource. Final
authority/deadline refusal after handler completion is uncertain. Owned disposable
model cleanup retains only worker/ancestry authority with bounded eight-second commands.
