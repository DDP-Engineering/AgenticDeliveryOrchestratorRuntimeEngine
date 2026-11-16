# Component: Web API

## Purpose and source ownership

`04_Software/adore/web/app.py` creates the same-origin FastAPI application.
The optional `web` extra supplies FastAPI/Uvicorn. The API serves compiled web
assets, authenticates users, authorizes project reads and queues bounded worker
operations. It calls the existing configuration, profile, forge and conductor
services rather than implementing a second orchestration engine.

The application's generated OpenAPI contract is the route/parameter reference.
This document records ownership and trust boundaries; specialized contracts live
in the linked component documents.

## Authentication and authorization

`/api/v1/session`, `/me` and account routes use the local identity store.
Cookie-authenticated mutations require CSRF. Administrators manage accounts,
projects, configuration and credentials. Developers read and operate only within
their granted project scope and the action's required role.

Immutable project IDs bind grants and composite job identities. Name-based
project routes resolve and verify that identity. Profile/grant changes during
sensitive reads or mutations invalidate the operation; a rename or replacement
cannot inherit authority from a reused display name.

Reviewed user creation validates explicit role and project IDs before one
transaction publishes the account and grants. Developer creation without project
access requires explicit acknowledgement. Password values/hashes, credential
values and raw rejected input are excluded from responses and audit evidence.
See [Web identity](Component_Web_Identity.md) and
[Profiles](Component_Profiles.md).

## Project enrollment and configuration

Azure Services extends guided project input and repository-source detection with
organization/project/Area Path, all validated through the shared wizard and
factory. Repository identity comparisons retain organization and project.
`platform.work_item_types` and `platform.closed_states` are bounded, complete
reviewed collections using existing revision, role, pause and idle-job fences.
Azure auth checks are scope-bound; public origin/token credential connection is
not supported for this provider. The label helper returns
`mode=azure_on_attachment`, verified names and empty provisioning lists. See
[Azure DevOps component](Component_Azure_DevOps.md) and `test_web_azure_devops.py`.

Guided setup and raw TOML/source-bundle import use staged preview/check/create
flows. Candidates bind exact source bytes, project identity, configuration and
observed prerequisites. Source reads and previews do not authorize unrelated
runtime effects. Environment preparation has its own bounded operation/status.
Creation rechecks the reviewed candidate and project-name availability.
Repository access, model access and runtime readiness are distinct observations.

Configuration edits validate their expected SHA-256 revision, create and validate
a candidate, then atomically replace live TOML. The shared configuration-edit
lock coordinates CLI and web writers. Pending changes retain one bounded current
candidate per project; review exposes changed approved values, not secrets.
Apply rechecks live revision, current run/operation ownership and the edit's
required safe boundary. Identity/runtime changes also require paused pickup.
Direct PUT follows the same safety rules and cannot bypass a pending candidate.

A crash after TOML publication but before profile-label completion is reconciled
only for the same already-published candidate. This is recovery of the current
operation, not conversion of an earlier stored format. Invalid pending records
are refused and can be explicitly discarded. Unknown configuration sections and
keys are errors, including the removed independent verification-command key.
See [Configuration edits](Component_Config_Edit.md) and
[Configuration](Component_Config.md).

Reviewed executor changes cover connection, thinking, network/search, command,
credential names, backend and the supported environment-selection fields.
Provider key writes are private, require the safe paused/idle boundary and never
return saved values. Raw TOML export is exact and administrator-only; secret-like
content is refused before export. Portable-settings JSON remains an administrator
API contract with exact current schema/source version; it has no browser panel.
See [Portable settings](Component_Portable_Settings.md),
[Executor configuration](Component_Executor_Configuration.md) and
[Executor recipes](Component_Executor_Recipes.md).

Project archive/restore/delete, identity edits, access grants and history retain
separate lifecycle checks. Delete preview binds the confirmed current project
and reports retained human-owned worktrees. It does not sweep shared filesystem
roots or release active work on the basis of a name alone.

## Jobs, tickets and agent sessions

`GET /api/v1/jobs-page` filters, sorts and pages the complete authorized job
projection. Composite detail is `/api/v1/jobs/{project_id}/{run_id}`. Project
`/runs` and `/runs-page` routes also serve current project views. Reads validate
selected persisted sources, recheck grants and expose optimistic revisions.
Continuation after a changed source receives 409 rather than partial totals.
See [Web jobs](Component_Web_Jobs.md) for exact bounds, errors and evidence.

Project ticket reads use the forge adapter and shared readiness rules. Start/Stop
routes queue worker operations after project/action authorization; the worker
rechecks the current grant, configuration and ticket. Start is explicit manual
admission and can run while automatic pickup is paused. An accepted request is
not proof that the conductor has started or stopped a process.

The sessions list and `sessions/{attempt_id}` routes read only the selected
run's owned live recording or exact immutable archive. Responses are no-store.
Current launch marker, lifecycle and held kernel lock jointly establish live
ownership. Complete-line cursors and continuity prevent replacement/truncation
from mixing attempts. Literal retained prompts/chat can contain agent-printed
secrets; operational executor-output diagnostics use a separate redacted reader.

Instruction GET/POST uses the durable run inbox. Inputs are strict bounded text
and delivery mode; author comes from authentication. Delivery is bound to the
selected current launch, rechecked grants and receipt evidence. Queue acceptance,
Pi acknowledgement and completion are distinct facts.
See [Instructions](Component_Instructions.md) and
[Executor launcher](Component_Executor_Launcher.md).

## Workers and operation lifecycle

Ordinary engine actions are durable operations dispatched by the worker. Slow
configuration/model/readiness jobs use the independent configuration worker so
they do not block running job control. Ownership records, process ancestry,
project/run locks, dispatch fences and stop/delete boundaries are shared with CLI.
The API does not run a model stage inside a request handler.

Operation responses have typed status/reason evidence. Browser retries cannot
reuse a different candidate or project identity. Lost ownership prevents writes
and further child effects. System health/readiness, worker status and storage
observations are separate read surfaces. Storage totals group by observed volume
without exposing arbitrary host paths to developers.
See [Web worker](Component_Web_Worker.md),
[Configuration worker](Component_Configuration_Worker.md),
[Worker processes](Component_Worker_Processes.md) and
[Project capacity](Component_Project_Capacity.md).

## Diagnostics, images and credentials

Administrator host-folder navigation validates server-side path containment and
regular-directory identity. Local executor discovery is a bounded, read-only
inventory, not permission to run a discovered wrapper. Runtime/image suggestions
inspect the selected server environment. Project-specific images are built
externally; registration/source export does not launch a build. Shared runtime
prerequisite preparation retains its separate checked boundary.

Repository connection uses the host's selected forge login and separate Git
credential transport. Executors do not receive forge credentials. Model checks
are explicit calls using the selected provider and backend. Native checks use
owned processes; container checks inspect local images and do not pull them.
ChatGPT sign-in uses the server-owned trusted helper and administrator-only
pending login state. See [Repository authentication](Component_Repository_Auth.md),
[Model connection](Component_Model_Connection.md),
[ChatGPT sign-in](Component_ChatGPT_Sign_In.md),
[Host folders](Component_Host_Folders.md) and
[Project images](Component_Project_Images.md).

## Statistics, audit and presentation metadata

Project/global statistics, usage and CSV exports observe the authorized immutable
scope. Financial values are administrator-only. Missing summaries/measurements
are distinguished from zero. Statistics reads use configured database semantics;
missing stores remain absent, and malformed evidence is a typed refusal.
Metrics output locations are TOML/CLI-owned and excluded from web candidates.
See [Metrics](Component_Metrics.md).

Audit paging/filtering and retention policy use the identity store; secret values
and arbitrary command output are not audit payloads. `/api/v1/about` supplies
release identity and four-locale release notes. Account preferences cover language,
theme and supported presentation choices. In-app help is shipped frontend content.

## Stored formats and error contracts

Every store has one current schema. Other schemas, unknown shapes and corrupt
records are refused with explicit operator deletion guidance; the API does not
migrate, fill defaults into persisted records or silently recreate stores.
Typed domain errors become bounded value-free HTTP codes. Ownership/source
changes normally return 409, missing authorized identities 404, rejected input
400/422 and unavailable/corrupt evidence 503 according to the route contract.
No partial success is substituted for an invalid selected scope.

## Validation coverage and limitations

Existing `04_Software/tests/test_web_*.py` cover authentication/CSRF, reviewed
configuration, enrollment/transfer, grants, strict job/session reads, worker
operations, statistics and failures at external boundaries using injected tools.
Browser journeys are under `04_Software/web/e2e/`. The OpenAPI declaration and
specialized component tests remain authoritative for exact route shapes.

The control plane is single-host and backed by local files/SQLite. Job snapshots
are optimistic source revisions, not a transactional frozen multi-file snapshot.
External forge/model/runtime calls remain separately bounded and fallible.

## Explicit new-job workflow

TicketStartInput and OperationInput accept optional Literal aegis/direct workflow. Non-Start/Restart actions refuse an override. Replay checks project identity, target/action and workflow before returning an existing operation. The authorized workflow-selection read reports project default and read-only payload presence without invoking repository code; admission remains authoritative for usability. Direct-default readiness reports Direct independently of installed AEGIS.

## Cancelled execution restart

The existing project Restart operation accepts cancelled as well as failed state after CSRF, role/project-grant, idempotency and exact state-revision checks. The worker repeats these checks before effects. Cancelled restart acknowledgement binds retained previous state, picked ticket, selected workflow and new run ownership, exposing admitted_run_id for navigation. Job projections expose validated previous_run_id/restarted_run_id journal links. Tickets projects the latest validated generation and includes state_revision for cancelled-job confirmation.
