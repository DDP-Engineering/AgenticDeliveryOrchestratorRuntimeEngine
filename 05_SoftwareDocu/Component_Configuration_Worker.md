<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Configuration and control worker

## 1. Purpose

Run configuration/control independently of project admission and executor processes.
Operational choices always belong to one immutable project: monitoring, backend,
container/runtime/image, provider/model, limits, polling and policies. Existing
server administration owns accounts/access, audit, shared ChatGPT sign-in and
service administration. Enrollment is server administration with an explicit
prospective target in the validated body; it publishes independent stopped profiles.

## 2. Responsibilities

`ConfigurationTasks.route` registers the existing typed handlers and replaces their
HTTP invocation with durable acceptance. `ConfigurationWorker.tick` claims scoped
work and dispatches bounded lanes; `execute` invokes the same handler under current
actor, project, configuration and protected-credential fencing. `configuration_loop`
owns these lanes in the separate supervised configuration process.

## 3. Implementation Overview

HTTP validates authentication, CSRF and the Pydantic body, resolves both profile
names and IDs with ambiguity refusal, pins source bytes and privately writes one
request before enqueueing its opaque reference. It returns HTTP 202 with
`id`, `status`, `domain`, `project_id`, Location and no-store headers.
The worker has four fast slots, four long slots, one independent shared-auth slot
and a separate deletion slot. No unbounded executor queue is used. At most one
configuration request runs per project; different enrollment targets have distinct
resource scheduling identities. A second pending/running enrollment for the same
target gets a conflict before publication. Native/preparation stage/apply work and
recipe/model/host/image probes use the long lane. Ordinary container settings use
fast capacity. Pause/Resume run in the immediate control pass outside every pool.
Cancel remains in the independent project command/watcher path, including at capacity.

## 4. Dependencies

Python standard-library futures/contextvars, FastAPI/Pydantic route types,
ProfileStore, WebStore schema 18, existing private credential-file read/write
primitives, config edit/admission locks and the existing probe/handler modules.
No broker, new dependency, schema migration or target-repository test runner.

## 5. Inputs And Outputs

Existing project config PUT, config preview/pending/apply/discard, credentials,
repository connection, model/readiness, recipe and label-ensure routes return
acceptance. Existing setup/import/transfer review/check/create/environment routes
and shared ChatGPT routes use the same durable bridge. Branch preview remains a
short scoped developer-readable request; account/audit/access changes remain short
independent server transactions.
`GET /api/v1/operations/{id}` exposes administrator-only configuration outcomes:
identity/domain/status/reason/times plus `outcome: {status_code, body}` only after
confirmed success/failure; pending/running/uncertain have no outcome.
The browser's `completedConfiguration` waits for this result and reconstructs the
actual response before any caller displays success or publishes an enrollment.

## 6. Data Contracts

SQLite stores opaque request references, actor/project/domain, owner generations
and closed results/reasons. Inputs live under `ADORE_HOME/configuration-tasks/` as
private schema-1 request JSON. A salted content digest binds the 32-hex reference
to exact bytes, handler, target, revision, credentials fingerprint, lane/resource
and typed arguments. Tokens are never copied to SQLite, history or status.
The existing atomic private-record primitive sets mode 0600 and fsyncs before
rename. Consumed requests are removed; corrupt requests remain refused with
explicit file deletion guidance. A crash leaves an uncertain claim without replay.
Public schema-1 result files bind exact operation ID, integer HTTP status and
public body; contradictory terminal states, duplicate/unknown fields, nonregular
records, malformed data and foreign versions fail closed with deletion guidance.
The queue accepts at most 256 pending/running configuration requests, checked in
the enqueue transaction. Records are bounded to 32 MiB to include existing ZIP
wire limits. New work has a 3600-second wall-clock budget; each external command
uses its remaining budget. Exact internally owned disposable cleanup retains
worker/ancestry authority after actor revocation or timeout, with eight seconds per
cleanup command; it cannot publish evidence or start new work. Every lane is independent of executor/run capacity.

## 7. Workflow Integration

Preparation and validation happen without project edit/admission locks. Publication
reacquires the project's lock, checks source/pending revisions and current rights
immediately before writing. Running executor snapshots are unchanged. Unsafe apply
returns `project_has_active_work`, retains the candidate and changes no other project.
After-effect storage/confirmation failures are uncertain rather than falsely rejected.
Shared ChatGPT remains one server session, serialized by its own resource and lock.

`EnvironmentPreparation.prepare` runs inside the durable task, with persisted
schema-1 value-free progress under `ADORE_HOME/environment/jobs/`. Image work uses a
short locked PID/birth/token reservation per canonical runtime; no config/kernel
lock spans an image inspect, build or verification. Only demonstrated death/birth
change permits reclaiming a reservation. Missing default images use bundled assets;
custom images remain inspect-only. Individual builds retain their 1800-second limit.

## 9. Validation And Tests

`tests/test_web_configuration_worker.py` covers HTTP acceptance, actual separate
process consumption, B/global progress during A model and managed-image work,
free edit/admission locks, slow native plan lane selection, Pause/Resume, unsafe
staging, stale/concurrent saves, revoked authority, ambiguous scope, corrupt
protected work/results and uncertain confirmation. Existing domain tests use an
explicit queue-consuming client, preserving their original outcome assertions.
`web/tests/configurationTasks.test.mjs` covers pending/confirmed/conflict/uncertain,
identity/transport corruption and abort boundaries. Existing targeted settings,
model/credentials/enrollment/recipe/environment/supervisor contracts cover integrations.

## 10. Limitations

A browser may stop waiting without cancelling an accepted server operation; use its
durable identity to inspect the result. In-flight configuration after worker death
stays uncertain and is never automatically replayed. An interrupted ChatGPT OAuth
handshake/evidence token remains ephemeral and requires a fresh explicit check.
Live provider/runtime/forge acceptance is separate operator work; no such action is
part of offline verification.

Settings GET reads only validated schema-1 `execution-plan.json` evidence bound to
project ID/config revision, with null for absent/stale evidence. Explicit host checks
and successful reviewed application refresh it; settings reads never resolve host/Git
plans. Corrupt/foreign cached formats fail closed and name the file to delete.
The model-probe cleanup scope retains only current worker/ancestry authority for its
internally owned disposable resources after user revocation; publication still checks
the current actor and source. Post-effect deadline crossings remain uncertain.

Existing plan evidence is validated before active configuration publication; an
unsupported cache stays unchanged with the staged candidate retained. A cache failure
racing after an already applied change becomes uncertain. Project/global operation
history canonicalizes the global empty scope as null and validates opaque references
before projecting redacted Settings evidence.

## Staged project capacity feedback

Staging publishes under the short project admission boundary so a confirmed lower N fences later reservations. Safe apply may return `capacity_below_occupancy`, retaining both active bytes and candidate while the reduced ceiling already holds new work. Project status restores the caller's durable outcome after navigation or reload; a 202 acceptance never becomes a saved-settings notification by itself. See [Project capacity](Component_Project_Capacity.md).
