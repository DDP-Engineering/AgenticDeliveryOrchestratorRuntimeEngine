<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web API

## 1. Purpose

`adore.web.app.create_app` exposes the same-origin `/api/v1` API and serves
the bundled React build. `adore.web.server` runs it on loopback by default.
The server refuses non-loopback binds and trusts forwarded scheme/client
headers only from local proxy addresses. HTTPS login responses set Secure,
HttpOnly and SameSite session cookies; direct HTTP remains local-only.

## 2. Responsibilities

The API authenticates users, checks CSRF on mutations, enforces admin/project
RBAC, creates project profiles, reads run state, enqueues developer job
operations, administrator pause/resume pickup, administrator audit history and
retention policy, and
role-filtered metrics and administrator-managed estimated prices. It never invokes an executor
from an HTTP request.
Project creation uses the shared wizard validator, so an unsupported Pi/Qwen
host-auth request fails before a profile is saved.
It supplies an absolute, project-specific worktree root under the web home;
the worker can then run from any process working directory without changing
the path used by a retry.
Administrators can archive or restore projects without deleting their profiles,
run state, metrics, prices or audit history. `POST /api/v1/projects/{name}/delete`
(administrator, CSRF, `{"confirm_name", "idempotency_key"}`) queues a worker
`delete` operation only for an archived project whose exact name is confirmed
and that has no queued, running or unfinished work; otherwise it returns
409 `project_not_archived`, 422 `delete_confirmation_mismatch`, 409
`project_has_active_work` or 503 `run_state_corrupt`. Administrators can read a finished delete
operation's status after its project is gone.
Administrators can also preview and import an existing TOML configuration
without rewriting comments or unknown keys. The imported project starts with
ticket pickup paused.
Run pages accept `handoff-pending` and `handed-off` as lifecycle filters.
Pending handoff blocks cancellation and archive while ownership is moving;
completed handoff remains readable and is terminal for cancellation and
archive checks. Human-owned worktrees remain protected by conductor cleanup.

## 3. Implementation Overview

The action workspace uses complete authorized `/jobs-page` and composite
`/jobs/{project_id}/{run_id}` reads. Global search and bounded attention,
lifecycle/stage/executor/outcome/UTC date selection precede pagination. Counts
cover searched scope before secondary filters; snapshot continuations detect
source/access changes. Strict captured JSONL provides the safe observed detail
timeline. See `Component_Web_Jobs.md` for exact trust boundaries and fields.
Project list summaries preserve absent legacy update times as unknown so valid
jobs remain navigable; a nonempty malformed timestamp still returns a typed error.
Existing run endpoints and queued mutation contracts retain their behavior.


Every project route validates the profile name then loads it through
`ProfileStore`. Developer memberships are checked before state is read. Run
events are allowlisted for both roles, with reported money fields restricted
to administrators, and
MR/PR links accept only HTTP(S). Config reads drop credential-looking fields.
Config edits validate a SHA-256 revision,
write a unique candidate file, load and validate the candidate, then replace
the original. A process-local lock serializes web threads; the shared
`config_edit_lock` coordinates CLI and web edits across ADORE processes.
The staged API stores one bounded candidate per project without modifying live
TOML. Review returns its base and candidate revisions, changed scalar and
whether a controlled restart is required. Apply rechecks the base revision,
conductor lock, run state and queued operations. Identity and runtime edits
also require pickup to be paused. The older direct PUT endpoint observes the
same safe boundary and refuses to bypass a pending candidate. A corrupt
pending record fails closed; an administrator can discard it explicitly.
If a process stops after replacing TOML but before updating profile labels,
retrying Apply with the same candidate revision reconciles the labels and
clears the pending record. Candidate bytes and revision remain identical on
Windows and Linux.
For an OpenCode profile, one local endpoint edit can update the selected
`provider/model` and URL atomically, then writes its compatible provider
override into `OPENCODE_CONFIG_CONTENT`;
an optional API-key reference must name an allowlisted executor environment
variable. The service stores OpenCode's `{env:KEY}` reference, not the secret,
and omits the inline provider JSON from configuration read responses. The edit
accepts only the OpenAI chat-completions protocol, a 1–600 second OpenCode
request timeout, and an optional absolute custom-CA path for HTTPS inside the
executor image. The safe pending-config response includes the resulting model,
protocol, timeout, auth reference and CA path for review. Other executors
reject that edit. The separate readiness route checks the selected executor
binary in the configured image with a no-network, no-pull container, then
probes a configured local model from the runtime container context.

## 4. Dependencies

The optional `web` extra provides FastAPI and Uvicorn. Internal dependencies
include profiles, config, state, wizard, metrics and `WebStore`.

Administrator-only `GET /api/v1/projects/{name}/access` returns
`{"developers": [{"id", "username", "disabled", "granted"}]}` for every
developer account, sorted by username; `granted` counts only grants carrying
the project's current identity. `PUT /api/v1/projects/{name}/access/{user_id}`
with `{"granted": true|false}` (CSRF) grants or removes that one developer's
access to that one project, leaving every other grant unchanged, audits
`membership-changed`, and returns `{"id", "granted"}`; an unknown project or
account returns 404, an administrator account 400 `user_not_developer`, and a
rename landing during the update 409 `project_changed` with nothing changed.

## 5. Inputs And Outputs

Global persisted job reads use `/api/v1/jobs-page` and composite
`/api/v1/jobs/{project_id}/{run_id}`. Grants are resolved before reading run
sources; all selected projects must validate for complete totals. Current and
archived projects share deterministic global pagination/search and lifecycle
groups. Source revisions reject changed continuations with 409. Existing
project run clients retain their contracts. See
[Persisted Web Job Reads](Component_Web_Jobs.md) for the exact evidence,
unknown, strict-source and optimistic snapshot contracts.

Inputs are JSON requests and the existing profile/run files. Outputs are
versioned JSON, an HttpOnly session cookie, audit rows, queued operations and
bundled local static files. Every rejected `/api/v1` request returns
`{"detail": {"code": ..., "message"?: ..., "issues"?: [...]}}` with its route status: `code` is a
stable lowercase snake_case identifier the browser localizes, and the optional
`message` carries English diagnostics. Request validation returns 422
`invalid_request` naming failing fields without echoing their values; account,
membership, price and queue store failures map to fixed codes such as
`password_too_short`, `username_exists`, `last_administrator` and
`idempotency_conflict`, with unrecognized store text returned as
`request_rejected` plus `message`. Project creation failures return
`project_setup_invalid` with value-free remediation in `message` and structured
findings in `issues`. Unknown
`/api/...` paths return 404 `not_found` rather than the browser shell.
An account marked by an administrator password reset can call only
`GET /api/v1/me`, `GET`/`PATCH /api/v1/me/preferences`,
`POST /api/v1/me/password` and `DELETE /api/v1/session`; every other
authenticated route returns 403 `password_change_required` after the 401
session check and before CSRF and role checks. Account objects include
`password_change_required`. `/api/v1/about` reports the running version and
full bundled license text.
It also returns the bundled third-party component notices, compiled from the
locked web dependencies. About remains available before login.
`/api/v1/health` reports HTTP liveness; `/api/v1/ready` requires a recent
worker heartbeat and returns 503 when it is missing or stale. Neither endpoint
returns account or project data.
Administrator-only `GET /api/v1/system/storage` measures the local volumes
holding ADORE home and each registered project's run-state root. A root that
does not yet exist is measured at its nearest existing parent. The response
identifies home or project, total/free bytes and a low-space flag; it does not
return host paths. Less than 1 GiB free raises a warning in Administration.
The check is read-only and does not prune indefinite history. Disk measurement
or corrupt project metadata returns a typed 503 rather than a healthy result.
Administrator-only `GET /api/v1/audit-policy` returns nullable day and UTF-8
audit-text byte limits; CSRF-protected `PUT` replaces both limits and prunes
existing older rows. Invalid or unknown policy fields return 422. Corrupt
persisted policy or event timestamps return 503. Administrator-only
`GET /api/v1/audit-page?limit=<1-100|all>&offset=<n>` returns
`{"items", "total", "limit", "offset"}` for one newest-first slice of the
retained audit trail (`limit` is null for All); bad limits return 422
`invalid_audit_limit` and negative offsets 422 `invalid_request`. The project
runs page accepts `lifecycle` more than once and returns runs in any listed
lifecycle. `GET /api/v1/audit` accepts
a numeric limit of 1–500 or `all`, with the same administrator guard.
Authenticated `GET /api/v1/me/preferences` returns the current account's
nullable language and theme. CSRF-protected `PATCH` updates only the supplied
allowed values; malformed or unknown fields return 422, and corrupt persisted
preferences return 503. A different account's preferences are never addressed
through this route.
`POST /api/v1/projects/{name}/archive` requires administrator CSRF and rejects
projects with a nonterminal or corrupt run, or queued/running web operation.
It takes the project conductor lock while checking and saving, so an active
poll also blocks archive.
`POST /api/v1/projects/{name}/restore` re-enables pickup. Both return the project
view, including `archived`; archived projects remain in project, job and metrics
reads. New job and pickup operations return 409 while archived.
`POST /api/v1/projects/import-preview` accepts bounded UTF-8 `config_text`,
profile ID, display name and description. It returns separate `config_revision`
(raw-byte SHA-256), opaque `revision` binding file/identity/current ownership and
terminal state, structured `validation`, unverified status and an allowlisted
`review`. Review includes config destination, declared and resolved repository/worktree/state and all
metrics paths, forge/repository/branch, agent name/slug/email, executor/model,
credential reference names and runtime/image/egress. Invalid candidates have null
review; secret literals and raw environment/command values are never echoed.
Every consequential location is absolute and below a volume root. State roots
exclude equal, ancestor and descendant ownership; active/corrupt runs or a
conductor lock yield corrective state-location findings.
`POST /api/v1/projects/import-check` requires that revision and explicitly
reuses bounded `_probe_setup`; its ephemeral response includes both revisions,
UTC time, context, checks and failed/partial/verified status. It reinspects after
the probe and persists no profile/readiness record. Unknown model/WSL evidence
stays partial. Command output and credential values remain redacted.
`POST /api/v1/projects/import` confirms the exact reviewed input, reinspecting
under the shared enrollment/config and conductor locks before copying bytes,
stopping pickup and publishing metadata. File/identity/ownership/state changes
reject with a conflict; completed history stays at its existing server location.
All three routes require Admin and valid CSRF. The browser uploads TOML only;
operators supply credential values through protected server stores.
The project list accepts a bounded `q` search over name, description and
repository plus an exact `state` filter. Both apply after project grants.
Project views include static config validity, executor selection, UTC last run
activity and a status of configured, needs-config, paused, archived or
invalid-state. Config validity does not claim live forge/model readiness;
malformed persisted run timestamps return 503 instead of a misleading date.
Project JSON includes an immutable `id`; project-scoped API paths accept that
ID as well as the current profile name. Developer grants are checked against
the resolved project identity, so a renamed project remains accessible and a
reused name cannot inherit its prior grant.
The administrator-only, CSRF-protected
`POST /api/v1/projects/{name}/readiness-check` runs bounded host-side doctor
probes on explicit request. It returns booleans for Git, the selected forge CLI
and authentication, the selected executor CLI, AEGIS file presence in the
configured repository, and a directly selected Docker/Podman runtime. It does
not execute repository code from the API process. A configured local OpenCode
model is additionally checked from a disposable executor container with the
project image and egress policy; the result includes model, context, readiness,
and a redacted reason. WSL-wrapped runtime detection remains unverified.
Captured command output and
credentials never enter the response. Corrupt configuration returns 503, while
a syntactically valid but invalid configuration returns 409. Unit tests inject
the command runner and never invoke external tools.
`GET /api/v1/projects/{name}/config` returns redacted effective configuration
to administrators and developers assigned to that project. Other project
identities return 404. The read response excludes credential-looking keys
(except ADORE's own non-secret `metrics.capture_tokens` while it holds a boolean) and
inline provider JSON; every configuration mutation remains administrator-only.
Its `settings` list holds, per effective setting sorted by key, `key`,
`edit_key` (the file key; `executor.<name>.<field>` for
`executor.commands.<name>.<field>`), `source` (`project` when the project's
TOML file contains the edit key, else `default`), `editable` (the same key rule
the edit routes enforce, and a single string, number or boolean value) and
`restart` (applying needs paused pickup and no active work) and `default`
(the value at that key in `default_config()` - ADORE's built-in
configuration with slug-derived names - after redaction, a whole built-in map
for a map the project emptied, or null when it has no such key).
`GET/POST/DELETE /api/v1/projects/{name}/config/pending` read, stage and
discard the single candidate. `POST /api/v1/projects/{name}/config/apply`
requires its candidate SHA-256 revision. All four routes are administrator-only;
mutations require CSRF. Apply and direct PUT reject nonterminal or corrupt run
state, a live conductor lock, and unfinished web operations. High-impact
`agent`, `platform`, `worktree`, `container` and `executor` edits require
paused pickup; the profile directory's repository/platform/runtime labels are
updated after commit. Host edits to TOML invalidate the staged base revision.
`/api/v1/projects/{name}/runs-page` returns runs ordered by last update, with
`limit` (1-100 or `all`, default 25), nonnegative `offset`, optional exact `lifecycle`
and `stage` filters, an exact observed `executor` filter, inclusive
`updated_from`/`updated_to` UTC dates, and an
`outcome` text filter (case-insensitive substring, at most 80 characters).
It returns filtered `total` and unfiltered lifecycle `counts` for the selected
project. Reversed or malformed date ranges and blank/oversize outcome filters
return 422. It checks membership before reading state and returns 503 for
corrupt run state or an invalid
last-update timestamp used by a date filter. The legacy `/runs` list remains
for existing clients.
The executor filter uses identity recorded in run journals. A run without
observed executor identity does not match; malformed persisted identities or
journal records return 503 rather than guessing from the current project
configuration.

## 6. Data Contracts

The two roles are administrator and developer. Developer APIs contain no
monetary fields. Reporting dates convert timezone-aware journal timestamps to
the selected IANA timezone, defaulting to UTC;
malformed timestamps are excluded. Cost is null when no
run reported it; reported cost and configured estimates are separate values.
Project and administrator-global metrics JSON accept inclusive `day_from` and
`day_to` dates plus `timezone` and `granularity=day|week|month`. `totals`,
`runs`, coverage and revision attribution remain all-time; `daily` contains
selected local-date buckets, grouped by Monday-start week or calendar month
when requested. The separate `period` object adds the selected dated events
before grouping and identifies its `dated_events` basis.
Completed-job buckets use the last lifecycle-matching terminal journal event;
later checkpoint publication is not a new completion. Legacy runs without a
terminal event fall back to their stored update timestamp.
Summary-only historical tokens are not assigned to an invented day. Both
project and global CSV exports accept the same options. Invalid/reversed dates,
unsupported timezones and granularities return 422; developer responses and
exports omit period money fields.
`duration` reports a terminal-summary sample count plus nullable mean and median
wall-clock seconds. It requires valid start/end timestamps and includes human
wait. `period.duration` selects those samples by local completion day, independent
of daily journal completion buckets; undated legacy summaries are excluded.
Corrupt persisted span values or inconsistent timestamps return 503 rather than
publishing a misleading duration. These fields contain no monetary data.
`/api/v1/projects/{name}/usage` and administrator `/api/v1/usage` group
projected journal usage by selected local day/week/month, observed executor and observed model. Exact
`executor` and `model` filters combine with `day_from`/`day_to`; matching CSV
routes export the same scoped rows. These responses count usage events and
tokens, not jobs, and never assign summary-only usage to an executor or model.
Unknown journal identity remains null. Developer JSON and CSV omit all money;
administrator rows distinguish reported and estimated cost, with null for
unavailable amounts. Invalid filters return 422, corrupt persisted identity or
usage numbers and non-object journal records return 503, and CSV escapes
formula-like identity labels. Daily metrics also reject non-object journal
records with a typed `metrics_corrupt` response.
Project headline token and reported-cost totals include live journal events;
terminal summaries only fill token gaps when journal usage is absent.
Version 1 `usage-observation` journal records classify each executor launch as
`reported`, `unavailable`, or `disabled` for tokens and cost. Project/global
coverage counts use the stable run/attempt event ID, ignore identical replay,
and reject malformed or conflicting records as `metrics_corrupt`. Numeric
`usage` events remain the sole source of token and money totals, so an
observation never doubles a total. Older launches without observations remain
unclassified. Developer coverage omits monetary status fields.
Versioned numeric `usage` records use that same run/attempt ID. Identical
replays contribute once to daily, attributed and terminal-summary totals;
conflicting or malformed records return a typed error. Legacy usage without
an ID keeps its historical best-effort behavior.
Each attributed-usage read reconciles the retained journal with schema-11
SQLite numeric and launch-coverage projection rows and a durable per-run
ingestion cursor before returning it. The cursor rejects non-append changes to
previously ingested journal evidence. `POST /api/v1/usage/rebuild`
allows an administrator with CSRF protection to replay all projects, including
archived ones; it reports project/run/event counts, is idempotent, and leaves
run state unchanged. A conflicting or vanished source fails with 503.
Price versions are immutable and selected by exact project/executor/model and
effective date. Present values are not billed amounts.
Journal `revision-started` events with `revise-label` count as reviewer-requested
MR/PR revisions; `pipeline-failed` events count as automatic pipeline repairs.
Unknown triggers remain unclassified rather than inflating either count.
The all-time `quality` object reports reviewed jobs from `mr-opened` or
`mr-adopted` journal events, distinct jobs with a `revise-label` revision,
still-open reviewed jobs, jobs with a strict-verification event and those whose
first verdict passed, and reviewed human-merged jobs with/without reviewer
rework. Each ratio uses its named cohort as denominator and is null when that
cohort is empty. Pipeline repairs do not count as reviewer rework. Invalid
persisted strict-verification verdicts return `metrics_corrupt`.
The quality object also counts stage-failure and operator-retry journal events.
For administrators, `cost_efficiency` reports separate reported and estimated
USD averages for completed and human-merged jobs. Each average divides known
money by jobs with that source of cost evidence; its denominator is explicit
and an empty cohort yields null. Developer responses omit this object.
Administrator metrics include a `revisions` list. Each entry covers usage
after one `revision-started` journal event until the next such event in that
run. Reported and estimated cost remain separate and nullable; initial work
before the first revision remains only in run/day totals. The list is absent
from developer responses.
Mutations require `X-CSRF-Token` from the authenticated `/api/v1/me` response.
Cancellation submission rejects already terminal runs; the worker checks again
because the run can complete while a command waits in the queue.
The project daily CSV export applies the same project grant and financial
filter as the JSON metrics route. The administrator-only global CSV includes
project/repository provenance and escapes spreadsheet formula prefixes in
repository labels.

## 7. Workflow Integration

Attributed usage JSON and CSV include nullable cache-read and cache-write
counts. They are subsets of input tokens for Pi. Malformed category values or
an incompatible overlap declaration fail the usage read with a typed error.
An empty endpoint `ca_file` clears a previous custom-CA reference; a nonempty
path is accepted only for HTTPS and must be an absolute container path.

The UI calls the API, which queues commands for the separate worker. Selected
ticket starts retain the orchestrator's ready/hold/exclude checks. Draft MR/PR
creation follows existing publication policy; a human merges.

## 9. Validation And Tests

`test_web_import.py` proves exact UTF-8/CRLF byte copy, retained terminal history,
all consequential path boundaries, safe review, full candidate binding, explicit
fake probe statuses/errors, input/secret/size/encoding rejection, Admin/CSRF,
state corruption, duplicate/overlapping ownership and publication-lock races.

`test_web_rbac.py`, `test_web_config.py`, `test_web_pending_config.py`,
`test_web_metrics.py`, `test_web_pricing.py`, and
`test_web_commands.py` exercise
project scope, cost privacy, paged/filterable runs, input boundaries and operation behavior offline.
The RBAC suite includes ten accounts and twenty projects with five concurrent
viewer requests; it is a functional scope check, not a throughput guarantee.

## 10. Limitations And Future Work

The web editor covers single-value settings, edited on their rows, and the
compatible OpenCode endpoint; administrators can also import a TOML profile. Direct host file
edits outside ADORE do not use the shared lock, but revision checks reject a
stale browser edit. Multi-host API deployment and a shell-style log viewer are
not provided.

## Stable identity and paused enrollment contracts

All routes below require administrator authorization and mutation CSRF:

| Route | Input | Result |
| --- | --- | --- |
| `POST /api/v1/projects/id-availability` | `name` | Advisory `available` plus structured `issues`; never reserves an ID |
| `POST /api/v1/projects/setup-preview` | Existing guided fields, optional `display_name` | Local `structural_valid`, findings, `pickup: stopped-on-create`, unverified environment; no writes/probes |
| `POST /api/v1/projects` | Same guided fields | Complete profile with pickup already stopped |
| `POST /api/v1/projects/import-preview` | Exact TOML and identity | Full candidate revision, config digest, structured validation and safe review |
| `POST /api/v1/projects/import` | Exact TOML plus preview revision | Stopped complete profile; existing server history retained |
| `PUT /api/v1/projects/{name}/identity` | Only `display_name` | Updated label, unchanged directory, config/state paths, immutable ID, grants and queued operation ownership |

An omitted display label defaults to `name`; explicit null/empty/untrimmed/control
labels fail. Guided input forbids unknown fields. Imports reject literal secrets
recursively, including runtime environment/provider JSON and URL credentials.
Supported provider `{env:UPPERCASE_NAME}` references and environment-name lists
remain accepted. Findings have exactly `code`, `field`, `remediation`; they never
include rejected values. HTTP category codes retain existing browser localization;
precise reserved-ID, label, rollback and readiness findings live in `detail.issues`.

Publication holds a home-wide enrollment guard, rechecks ID/state ownership,
creates the final directory exclusively, locks the conductor, writes config,
pauses pickup, then publishes `profile.json`. Discovery therefore sees either no
profile or a complete stopped profile. Audit/response remain within the lock.
Failure removes metadata before unlocking, removes only the new directory, and
restores a previously unpaused external import root without deleting its history.
Failed rollback is a typed `project_rollback_failed` finding requiring host repair.
Availability does not guarantee a subsequent create succeeds. Stopped pickup does
not interrupt an existing job; start/resume remain explicit operator actions.

Project reads add `display_name`, `validation` (structural validity and findings),
`pickup_state` (`active`, `stopped`, `archived`) and independent `verification`.
Existing identity/status/paused fields remain. No read or setup preview probes tools.

### Guided draft preview, verification and creation

`ProjectInput` adds typed bounded run budgets, ready/approval labels and optional
credential environment names while preserving legacy defaults. Unknown fields are
forbidden; malformed/duplicate/empty API-key names and host-auth references are rejected
with value-free findings. Server clones are absolute existing Git roots.
Preparation uses the existing wizard in prepare-only mode and its configuration validator.
The generated comment is deterministic for web setup, so identical drafts yield identical
config bytes across requests. No external commands or profile writes occur during preview.

`setup-preview` returns `revision`, `config_revision` and canonical `review` for a valid
candidate. The draft SHA-256 binds exact config bytes, profile name, display name and
description. Review includes complete setup, resolved env-key names and absolute config,
state and worktree paths. Invalid candidates keep null review/digests and structured findings.

`ReviewedProjectInput` requires a 64-hex revision for the additive Admin/CSRF routes:

- `POST /api/v1/projects/setup-check`: rebuild, compare draft revision, run shared
  bounded `_probe_setup`, return redacted checks/model evidence with both revisions,
  UTC time and status. Failed checks yield failed; unprobed model or WSL yields partial.
  Gitea auth uses the selected tea login. No draft, readiness record or profile persists.
- `POST /api/v1/projects/setup-create`: rebuild, compare revision, publish the exact
  candidate using the existing locked stopped-pickup boundary. Duplicate IDs are
  rechecked under its lock; stale drafts return 409 before publication.

Existing `POST projects` retains its request/publication contract; exact import revisions bind complete identity and inspected ownership/state.
Newly created profiles have absent persisted readiness evidence, even if their memory
draft was probed. The shared probe helper also serves the persisted project readiness
route, whose storage/schema and mid-probe revision protection remain intact.
`test_web_enrollment.py` covers canonical fields/bytes across clock changes, stale and
duplicate publication, explicit ephemeral failed/partial checks, selected Gitea login,
secret-reference redaction and Admin/Dev/CSRF rejection; `test_web_readiness.py` covers
the persisted route regression.

### Persisted project readiness

`POST /api/v1/projects/{name}/readiness-check` retains bounded explicit probes and
atomically writes profile-owned `readiness.json`, independent of runtime schema.
Schema 1 contains immutable `project_id`, exact config-byte SHA-256 `revision`, UTC
`checked_at`, API-host context, typed prerequisite checks and redacted model probe.
Checks cover git, forge CLI/auth, runtime, executor CLI, AEGIS files and model endpoint.
The model probe records executor-container context, readiness, model and an allowed
reason. Commands/output/credentials are never persisted. Schema, keys, types,
identity, digest, time and redacted values are validated on read; corrupt evidence
fails closed with `readiness_corrupt` (HTTP category `readiness_probe_failed`).

Absent evidence is `unverified`; differing config bytes are `stale`; matching evidence
is `failed` if any check fails, `partial` for undetected WSL runtime, otherwise
`verified`. Freshness is revision-based, not age-based. Display edits do not stale
verification. Invalid configuration is separate from stale/absent evidence. A config
change during probes returns `stale_config_revision` without replacing evidence.
Storage failures return a safe `readiness_store_failed` finding.

Offline contract proof is in `test_web_enrollment.py` and `test_web_errors.py`,
including concurrency, worker discovery, rollback, legacy identity, secret handling,
RBAC/CSRF, revision races and corrupt persisted evidence.
