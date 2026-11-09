<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web API

Login and `/api/v1/me` return `factory_password` only for the authenticated account, reflecting current factory-password verification. Credential corruption returns 503; no hash or other account credential is returned.

Cancellation and ticket Stop require strict explicit confirmation before any queue or forge effects. Readiness includes advisory busy/idle/unknown activity gated by the worker heartbeat; operation outcomes remain authoritative.

Technical details displays Durable job state folder (`state.store_root`), Workflow Python command (`workflow.aegis_python`), Existing local repository path (`worktree.repo_path`) and Job working folders (`worktree.root`) as informational installation values. Operators configure them in the project TOML on the ADORE server; generic web mutations are refused. The localized guidance explains that changing a path does not relocate existing job state, repositories or working folders.

The settings catalog advertises `delivery.draft` choices `[true, false]`. Reviewed prepare/apply validates the exact boolean with the shared configuration validator and retains administrator, CSRF, revision, idle and locking gates.

The catalog and effective configuration use the shared enabled default for
`delivery.publish_checkpoints`; explicit project false remains effective and
is reported with project source and default true. Reading settings preserves
the saved configuration bytes.

Implementation settings support reviewed edits for human-answer waiting time (positive integer plus seconds/minutes/hours/days), positive question-round count, a nonempty retry schedule (one nonnegative integer per line), and the complete stage-timeout map. The five stage rows (frame, specify, design, build, validate) choose either the general attempt limit or a positive custom limit in seconds; choosing general removes the override. Retry and timeout collections accept only safe integers and their declared keys; other lists/maps remain read-only except the existing reviewer list. Admins edit several settings, choose Save, confirm important effects and save only at the existing idle boundary; developers remain read-only. Names, help and controls share four locales. The answer deadline is independent of the reserved reminder; reminder format is still checked and no reminder is sent.

`implementation_settings.py` supplies narrow collection validation and single-value TOML replacement. JSON strings reject duplicate keys, booleans/fractions, unknown stages, empty schedules and unsafe integer magnitudes. Complete stage maps may be empty. The writer supports missing/inline/nested tables, quoted keys and multiline lists, preserves original line endings, and verifies full parsed configuration equality against the requested edit. Unsupported spellings fail explicitly. Pending read/apply bind the claimed collection and reject unrelated candidate changes against an unchanged active base. Metadata emits one map row even when populated; nested values have project source. Focused proof: `test_web_pending_config.py` and `test_web_config.py`.

## Branch naming preview and edit authority

`POST /api/v1/projects/{name}/config/branch-preview` accepts the closed strict body `{template, rule, revision}` (512-character text bounds, SHA-256 revision). Scoped users supply CSRF; the shared config lock coordinates preview reads with application, and project grants and before/after revision checks precede evidence release. The route returns the shared config preview plus inspected revision and performs no writes or Git operations. Corrupt source returns `config_corrupt`, stale input returns `stale_config_revision`, and malformed transport fails request validation. Scoped developer reads hide inaccessible project identity with the existing 404 policy.

Only `worktree.branch_template` and `worktree.branch_rule` (text) and the administrator-chosen `execution.backend`, `container.runtime`, `container.image`, `container.system_packages` and `local.path` are exceptions to the external environment edit restriction. They advertise editability/restart and retain administrator, validated single-setting candidate, lock, revision, paused/idle and replay integrity gates. A direct PUT of the chosen environment keys returns 409 `pending_config_required`. Every other worktree/container/execution/local setting (for example `execution.preparation`, `container.uv_cache_volume`, `container.run_args`, egress, SELinux, `worktree.*` roots) keeps external ownership and returns 400 `environment_managed_externally`. The retired image-build routes
(`/api/v1/projects/{name}/image-build`, its `/export`, `/operations`,
`/operations/{id}` and `/operations/{id}/cancel`) are removed and answer 404. Focused proof: `tests/test_web_branch_naming.py`, `tests/test_web_config.py`, `tests/test_web_pending_config.py`.

## 1. Purpose

Statistics displays **Statistics database file** as an informational row with
four-locale guidance. Server `config.toml` owns `metrics.db_path`,
`metrics.export_jsonl` and `metrics.html_out`; web candidate preparation rejects
all three. JSONL and static HTML paths remain available through TOML/CLI and
are omitted from Project Settings controls. Project/global statistics, usage
and their CSV exports read summaries from the configured database with the
same relative-path semantics as CLI. Missing databases contribute no summaries
and remain absent; malformed configuration or database evidence returns the
existing typed 503 response. Metadata-only profiles retain their state-root
summary history until a configuration file exists. Analytical reads preserve
SQLite bytes, authorization, scope and financial redaction.

`adore.web.app.create_app` exposes the same-origin `/api/v1` API and serves
the bundled React build. `adore.web.server` runs it on loopback by default.
The server refuses non-loopback binds and trusts forwarded scheme/client
headers only from local proxy addresses. HTTPS login responses set Secure,
HttpOnly and SameSite session cookies; direct HTTP remains local-only.


The authorized `delivery.reviewers` candidate uses a dedicated account-list editor in Project settings. Admins submit a JSON string array through existing prepare/review/apply endpoints; metadata reports list type and editability. A complete single/multiline TOML array writer preserves adjacent configuration and CRLF. Candidate readback verifies the exact list against claimed wire value, and malformed input fails closed. Admin, CSRF, revision, idle and integrity checks apply to lists as to scalar edits.

## 2. Responsibilities

The API authenticates users, checks CSRF on mutations, enforces admin/project
RBAC, creates project profiles, reads run state, enqueues developer job
operations, administrator pause/resume pickup, administrator audit history and
retention policy, and
role-filtered metrics and administrator-managed estimated prices. It never invokes an executor
from an HTTP request.
Project creation uses the shared wizard validator, so an invalid executor
setting (for example an auth mode other than API keys for a container
project) fails before a profile is saved.
It supplies an absolute, project-specific worktree root under the web home;
the worker can then run from any process working directory without changing
the path used by a retry.
Administrators can archive or restore projects without deleting their profiles,
run state, metrics, prices or audit history. `POST /api/v1/projects/{name}/delete`
(administrator, CSRF, `{"confirm_name", "idempotency_key", "remove_clone"}`) queues a worker
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
`GET /api/v1/projects/{name}/delete-preview` (administrator, archived project) returns
`{"clone": {"path", "removable", "reason"}}` from `adore/clone_cleanup.py`; reasons are
`outside-repos`, `missing`, `not-a-clone`, `origin-mismatch`, `shared`, `worktrees` (including a
handed-off run's worktree that deletion keeps), `uncommitted` and `unknown`. `remove_clone: true`
rechecks it (409 `clone_not_removable`) and queues the delete with target `remove-clone`.

## 3. Implementation Overview

The action workspace uses complete authorized `/jobs-page` and composite
`/jobs/{project_id}/{run_id}` reads. Global search and bounded attention,
lifecycle/stage/executor/outcome/UTC date selection precede pagination. Counts
cover searched scope before secondary filters; snapshot continuations detect
source/access changes. Strict captured JSONL provides the safe observed detail
timeline. See `Component_Web_Jobs.md` for exact trust boundaries and fields.
Project list summaries refuse a run whose `updated_at` is empty, malformed or
naive with 503 `run_state_corrupt`, because every save stamps it.
Existing run endpoints and queued mutation contracts retain their behavior.


Every project route validates the profile name then loads it through
`ProfileStore`. Developer memberships are checked before state is read. Run
events are allowlisted for both roles, with reported money fields restricted
to administrators, and
MR/PR links accept only HTTP(S). Config reads drop credential-looking fields.
The container launch command exposes the Pi preset as its only catalog choice. ADORE validates it at staged/direct edits and pending review/apply. Server execution uses fixed managed Pi RPC.
Config edits validate a SHA-256 revision,
write a unique candidate file, load and validate the candidate, then replace
the original. A process-local lock serializes web threads; the shared
`config_edit_lock` coordinates CLI and web edits across ADORE processes.
The staged API stores one bounded candidate per project without modifying live
TOML. Review returns its base and candidate revisions, changed scalar or approved collection and
whether a controlled restart is required. Apply rechecks the base revision,
conductor lock, run state and queued operations. Identity and runtime edits
also require pickup to be paused. The older direct PUT endpoint observes the
same safe boundary and refuses to bypass a pending candidate. A corrupt
pending record fails closed; an administrator can discard it explicitly.
If a process stops after replacing TOML but before updating profile labels,
retrying Apply with the same candidate revision reconciles the labels and
clears the pending record. Candidate bytes and revision remain identical on
Windows and Linux.
An OpenAI-compatible endpoint is edited only through the reviewed
`executor.connection` candidate (section "Reviewed executor configuration").
The separate readiness route checks the Pi binary in the configured image with
a no-network, no-pull container; it has no model endpoint check.

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


### Reviewed user creation

Admin/CSRF `POST /api/v1/users/with-access` requires `username`, `password`,
explicit `role` (`admin` or `developer`) and distinct immutable `project_ids`.
Optional strict boolean `allow_no_projects` defaults to false. Extra fields,
coercible types, invalid/duplicate usernames, passwords outside 8–1024 characters,
invalid roles/IDs and implicit empty Dev access reject before persistence.
Admin submits an empty grant list and receives all-project/system access by role;
Dev receives exactly the selected current, visible, unarchived projects.

The store commits account/grants and the existing secret-free success audit in
one SQLite transaction. The API serializes archive changes with `config_lock`;
selected metadata is rechecked before commit, with 409 `project_changed` for
observed lifecycle races. Invalid grants return 400 `invalid_request`, archived
projects 400 `project_archived`, corrupt metadata 503 `project_corrupt` and
storage faults 503 `request_rejected`. Existing coded username/role/password
failures and Admin/session/CSRF denial remain supported. Errors omit input values.
Responses contain public account fields and `project_ids`, never password/hash.
`GET /users` adds live `project_ids` alongside compatible name-based `projects`.
`POST /users` and supported authentication/reset/assignment APIs retain their
contracts. `test_web_user_creation.py` and existing auth/access/RBAC tests own proof.

## 5. Inputs And Outputs

### Portable new-project transfer

Admin/CSRF `POST /api/v1/projects/transfer-source` accepts exactly one of
`{method: "file", file_text}` or `{method: "project", source_id}`. Project source
uses immutable identity; exact active config bytes are exported/parsed with the
unchanged conservative portable contract. File bytes use the strict parser.
The response contains only `source_revision` and complete `settings`.
Source SHA-256 binds exact file bytes, or immutable ID plus exact config digest;
a comment-only source edit invalidates confirmation.

`transfer-preview` adds `target: ProjectInput`, `source_revision` and required
`references_confirmed: true`; response includes canonical target review,
config/candidate revisions and 16 `mapping` rows (`key`, `source_value`,
`server_value`, `effect: "copy-rule"`). Server values are installed defaults.
All portable rules override target defaults; target identity, repository, runtime,
provider, model, endpoint, references, labels and reviewers are supplied
afresh. Credential references are excluded from sources. Provider setup uses
the target provider and model and supported auth.

`transfer-check` and `transfer-create` add reviewed `revision`. Check uses the
existing bounded explicit ephemeral probes and rechecks source afterwards.
Creation holds the source config lock when copying, plus existing home enrollment
and target conductor locks; authorization, exact source and target ownership are
rechecked before writes and profile visibility, and again before audit/result.
New random stable profile identity, state under its profile, worktrees under
home/worktrees/ID and derived metrics are independent. Allocated paths are visible
in review. Source identity/state/access/pending/secrets/history stay untouched.
Exact TOML enrollment retains its byte-copy/state-location contract.

Missing source is 404; invalid/incompatible package is typed 400; unreadable or
corrupt source/ownership is 503; changed source/candidate is 409
`portable_settings_changed` with re-review; occupied, aliased or overlapping
repository/state/worktree/metrics ownership is 409 `project_import_conflict`.
Reference confirmation and target findings block creation. Rollback removes new
profile visibility and owned config/state; duplicate/replay rejects the existing
identity without replacement. Direct unmanaged host edits must still respect
operator ownership; rechecks detect observed races rather than creating a global
filesystem transaction. No repository cloning or automatic activation occurs.

Tests: `test_web_transfer.py` proves both complete roundtrips, exclusions,
independent/stopped ownership, exact-source/target conflicts, parser/role/CSRF
negatives, late ownership, ephemeral checks and rollback/replay.


Administrator-only `GET /api/v1/projects/{name}/config/portable-settings` validates
one bounded active TOML snapshot through `adore.portable_settings` and returns
canonical `adore-project-settings` schema-1 JSON. Authentication/Admin checks
precede project/config lookup; Dev gets 403 without existence metadata.
`download=true` adds fixed `adore-project-settings.json` attachment; optional
portable `checksum` binding conflicts with 409 `portable_settings_changed` when
included rules/source differ. Invalid/unreadable/unknown-field source returns
value-free 503 `portable_settings_invalid`. Project ownership is rechecked after
export; changed identity returns typed conflict instead of a stale project result.
Responses are no-store. Pending,
state, metrics and readiness records are not read and no probe/write occurs.
All credential/endpoint references and identity/host/access data are omitted.
Exact version compatibility and the complete allowlist are defined in
[Portable settings](Component_Portable_Settings.md). Exact TOML enrollment and
metrics CSV retain their distinct existing contracts. Tests:
`test_web_portable_settings.py` and `test_portable_settings.py`.


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
`GET /api/v1/pi-providers` (any signed-in user) returns the shipped Pi
provider catalog as `{pi_version, providers: [{id, name, variable, models}],
chatgpt: {id, models}, custom: {id, variable, apis}}` (`chatgpt.models` holds the
models a ChatGPT subscription serves, the catalog's `chatgpt_models`) from
`pi_providers.public_catalog()`; an unreadable catalog returns 503
`provider_catalog_unavailable`.
`/api/v1/about` also returns the bundled third-party component notices, compiled from the
locked web dependencies, and `release_notes` from the packaged
`adore/release_notes.toml` (empty when unreadable). About remains available
before login.
`/api/v1/health` reports HTTP liveness; `/api/v1/ready` requires a recent
worker heartbeat and returns 503 when it is missing or stale. Neither endpoint
returns account or project data.
Administrator-only `GET /api/v1/system/storage` measures the local volumes
holding ADORE home and each registered project's run-state root. A root that
does not yet exist is measured at its nearest existing parent. The response
identifies home or project, total/free bytes, a low-space flag and a `volume_id`
(the filesystem device number) so the browser can group entries on one disk; it does
not return host paths. Less than 1 GiB free raises a warning in Administration.
The check is read-only and does not prune indefinite history. Disk measurement
or corrupt project metadata returns a typed 503 rather than a healthy result.
Administrator-only `GET /api/v1/audit-policy` returns nullable day and UTF-8
audit-text byte limits. Admin/CSRF `PUT` replaces both independently and returns
`retention_days`, `max_bytes` and `deleted_events` from the owning atomic policy/
evidence/pruning transaction. Limits keep the established 1–36500 day and
1–1073741824 byte bounds; null means unlimited. Structured JSON and correlations
count toward stored-text bytes; file allocation, job journals, identity,
operations and filesystem replay receipts are separate.

`GET /api/v1/audit-page?limit=<1-100|all>&offset=<n>` returns
`items`, `total`, canonical `limit` (null for All) and `offset`. Optional exact
`actor_id`, immutable `project_id`, action-code `action`, inclusive UTC `from`
and exclusive UTC `to` select all matched evidence before counts and paging.
Actor IDs and offsets stay within SQLite signed 64-bit bounds.
Invalid selectors/periods return 422 `invalid_request`, limits return
`invalid_audit_limit`, and negative offsets retain `invalid_request`.
Global history requires Admin. Dev must supply one currently granted immutable
project ID and receives project-safe config/enrollment/lifecycle/operation rows;
account/access/policy/price/usage/auth and financial configuration are excluded
before count/paging. Missing, malformed or unassigned Dev scope returns 403.
Revocation and replacement cannot inherit history visibility.

Each row exposes recorded actor ID/name/time, action, known stable project and
resource identity, phase/result, operation ID/opaque correlation, known revisions
and closed redacted before/after. Every audit row carries structured evidence;
the store rejects a row without it, and any other corrupt persisted evidence, as
corrupt; errors omit sensitive values. `GET /api/v1/audit`
retains its Admin-only recent/All contract with the same server projection.
No audit export is exposed.

Config staging records `prepare/prepared`; guarded apply records
`apply/applied` only on confirmed completion and discard records
`discard/discarded` for a removed pending resource. A corrupt pending candidate
remains explicitly discardable without inventing its diff. Durable uncertain
filesystem attempts preserve crash evidence; config replay uses the same receipt
and original before value. Guided/TOML/portable/clone previews are prepared
server events. Creation records the actual stable target, config revision and
stopped pickup, with distinct import/clone actions. Browser-local account review,
correction and abandoned memory drafts remain local; they neither apply server
state nor manufacture persisted preparation/discard events. Account/grant and
queue changes own their SQLite evidence transaction. Precondition rejection
records no successful application; worker failure/timeout/restart records
rejected or uncertain outcome. See `Component_Web_Identity.md` for receipt,
redaction, schema and replay details.

The project
runs page accepts `lifecycle` more than once and returns runs in any listed
lifecycle.
Authenticated `GET /api/v1/me/preferences` returns the current account's
nullable `language`, `theme` and `ticket_body_mode`. Ticket mode values are
`rendered` or `source`; null on read means no saved selection. CSRF-protected
`PATCH` updates only supplied fields, preserving every omitted preference.
An explicitly null or non-enum ticket mode, malformed input or unknown field
returns 422 `invalid_request` before writes. Existing language/theme semantics
are unchanged. Corrupt persisted preferences return 503 `preferences_corrupt`,
including on partial writes; no corrupt value is repaired. A different account's
preferences are never addressed through this route. Store/API round-trip,
CSRF, account-isolation and corrupt-row tests are in `test_web_auth.py` and
`test_web_rbac.py`.
`POST /api/v1/projects/{name}/archive` requires administrator CSRF and rejects
projects with a nonterminal or corrupt run, or queued/running web operation.
It takes the project conductor lock while checking and saving, so an active
poll also blocks archive.
`POST /api/v1/projects/{name}/restore` re-enables pickup. Both return the project
view, including `archived`; archived projects remain in project, job and metrics
reads. New job and pickup operations return 409 while archived.
`POST /api/v1/projects/import-preview` accepts bounded UTF-8 `config_text`
and optional profile ID, display name and description. With the ID omitted,
the server suggests an available ID from the declared repository name. The
response returns the resolved identity and separate `config_revision`
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
Project views include static config validity, the executor (`pi`), UTC last run
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
and authentication, the Pi CLI, AEGIS file presence in the
configured repository, and a directly selected Docker/Podman runtime; a project
with provider `chatgpt` also gets `executor_sign_in`, true when the server's
ChatGPT credential files report `signed-in` (read without starting Pi).
`_internet_checks` adds `egress_proxy` for a container project with
`[executor] internet` off (`<runtime> image inspect <proxy_image>` succeeds; never
pulled) and `web_search_key` for a project with internet on searching with Brave
or Tavily (the key is set in the server environment or the project's credential
store; the value is never returned). The image probe runs under the derived
`egress_policy`. Enrollment's environment check returns the same two keys. It does
not execute repository code from the API process and does not test the model;
model access is proven only by the explicit AI connection test. WSL-wrapped
runtime detection remains unverified.
Captured command output and
credentials never enter the response. Corrupt configuration returns 503, while
a syntactically valid but invalid configuration returns 409. Unit tests inject
the command runner and never invoke external tools.
`GET /api/v1/projects/{name}/config` returns redacted effective configuration
to administrators and developers assigned to that project. Other project
identities return 404. The read response excludes credential-looking keys
(except ADORE's own non-secret `metrics.capture_tokens` while it holds a boolean) and
the value of any `container.runtime_env` or `local.environment` variable named for a removed coding agent (`OPENCODE_`, `CODEX_`, `QWEN_`); every configuration mutation remains administrator-only.
Its `settings` list holds, per effective setting sorted by key, `key`,
`edit_key` (the file key, equal to `key`), `source` (`project` when the project's
TOML file contains the edit key, else `default`), `editable` (the same key rule
the edit routes enforce, and a single string, number or boolean value) and
`restart` (applying needs paused pickup and no active work) and `default`
(the value at that key in `default_config()` - ADORE's built-in
configuration with slug-derived names - after redaction, a whole built-in map
for a map the project emptied, or null when it has no such key).
Catalog rows additionally supply `type` (boolean/integer/number/text/list/map),
`choices`, inclusive `minimum` and `maximum` (null when unbounded). Types derive
from built-in configuration model defaults; `executor.command` offers the Pi launch
preset (container projects only), `executor.provider` the provider ids and
`executor.endpoint.api` the endpoint API types, and scalar domains project the
existing validator. The rows `executor.provider`, `executor.model`,
`executor.endpoint.base_url` and `executor.endpoint.api` report `edit_key`
`executor.connection`. Whole-config
validation remains decisive for dependent rules. Corrupt declared scalar types
return 503 `config_corrupt`. Dev configuration omits `budgets.max_cost_usd` before
row/default generation. Credential-bearing URLs are redacted in effective reads.

`GET /api/v1/projects/{name}/config/raw` is administrator-only. It returns original saved UTF-8 TOML bytes, including inline secrets, as `text/plain`, with `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. `?download=true` adds a fixed `config.toml` attachment. Authorization precedes lookup. Empty, malformed, unreadable, symlinked or oversized sources return value-free 503 `config_corrupt`; changed bytes or immutable project identity return 409 `stale_config_revision`. Reads are bounded to 524288 bytes; no environment resolution, `.env`, pending changes or mutation.

`POST /api/v1/projects/{name}/config/preview` builds the same validated candidate as preparation, without writing active settings, pending evidence or audit events. `GET/POST/DELETE /api/v1/projects/{name}/config/pending` read, prepare and discard one candidate. Preparation verifies the previous complete candidate against active bytes and replaces it only with its exact `pending_revision` and unchanged base; missing or stale replacement bindings return 409. Preview and preparation share `_prepare_config_candidate` and its final-document/plan checks.

`settings.batch` is a virtual edit key whose wire value is strict JSON: 1–100 unique `{key,value}` objects with string fields. `settings_batch.py` rejects malformed, duplicate, overlapping or nested targets and connection aliases. Each member passes existing authority/type/secret checks, then the final combined TOML is validated. `proposed_value` is a safe typed map. Public read/apply recompute full candidate meaning against the unchanged active base, rejecting hidden collateral changes. Restart requirements are the union of member keys. Direct PUT refuses this vocabulary with `pending_config_required`.

`POST /api/v1/projects/{name}/config/apply` requires both exact `candidate_revision` and `base_revision`. It retains atomic replacement, audit replay, config/conductor locks, nonterminal/corrupt run and unfinished-operation checks, plus paused pickup for identity/runtime changes. Invalid member or plan evidence fails closed without publication. All preview/pending/apply routes are administrator-only and mutations require CSRF. Pending schema remains 1. Corrupt evidence returns `pending_config_corrupt` and can be explicitly discarded. Focused contract proof: `test_web_settings_batch.py`, `test_web_pending_config.py`.

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
monetary fields.

Reporting scope is the authorized immutable project set, a half-open UTC
instant interval `[from,to)`, the selected IANA timezone and day/week/month
granularity. Inclusive date controls resolve each local midnight independently;
the upper bound is midnight after `day_to`, including 23/25-hour DST days.
Omitted bounds are unbounded; both omitted explicitly select `all_time`.
All scoped totals, cards, tables, daily rows, cohorts and exports use this scope.

Started uses the first `picked` event; completed/failed uses the latest event
matching the final lifecycle. Checkpoints and state update times do not supply
these dates. Recorded summary start/end is fallback only without lifecycle
journal evidence. `current_stock` separately names jobs/active/waiting/review/
terminal now, including only actual retained runtime state.

Unique usage is attributed at its own consumption instant. `jobs` uses
`(project_id,run_id)` with separate `lifetime`, `in_period`, `unallocated`,
source and coverage. Recorded summaries survive runtime-state removal;
positive summary-only measurements (a run known only from `metrics.db`, for
example a deleted one) belong to lifetime/unallocated, never a fabricated
period. Missing individual token fields stay null; explicit measured zero stays
zero. Zero summary amounts are unknown. Every usage event carries its versioned
`event_id` and an aware timestamp: a usage event without an event ID is refused,
and a naive, date-only or unparseable usage timestamp is `metrics_corrupt`.
Financial fields and financial coverage are Admin-only in every nested
projection and export. Reported and estimated costs remain separate; matching
immutable prices use the consumption UTC day, and never price reported money
again. Coverage identifies partial evidence rather than asserting a full bill.

Review cohorts use first MR opening/adoption in scope; validation cohorts use
first strict verdict in scope. Human merge uses reviewed jobs with actual done
in scope and `merged by human`. Rework requires reviewer-requested revision;
pipeline repair is separate. Each rate exposes numerator/denominator; empty is
null. Open reviews are labeled current state. Monetary efficiency uses only
period consumption for the completed/human-merged cohort and separate known
reported/estimated samples.

Duration is terminal-summary elapsed wall time including waits, selected by
recorded end instant in scope. Count, sum and sorted exact `samples_seconds`
support pooled mean/median without browser date approximation. Recorded zero
is valid; absent pairs are excluded and inconsistent pairs fail.

Raw state/JSONL and read-only summary rows are validated before filters.
Malformed JSON, duplicate keys, unsupported schema, a summary table with missing
or extra columns, invalid fields, conflicting versioned identity/timestamp,
numeric overflow and invalid timestamps fail typed 503 without source rewriting.
Invalid scope/identity filters return 422. Analytical summary reads neither
initialize nor migrate runtime data.
CSV includes scope/project provenance, empty unavailable cells and spreadsheet
escaping; `X-ADORE-Scope`/`X-ADORE-Coverage` describe empty exports too.
Project `/api/v1/projects/{name}/jobs-usage.csv` and Admin global
`/api/v1/jobs-usage.csv` share usage date/timezone/group/executor/model filters.

Offline proof: `test_web_scoped_metrics.py`, `test_web_metrics.py`,
`test_web_pricing.py`, and `web/tests/metrics.test.mjs`, followed by native
Python/Ruff and frontend validation. CLI summary/export semantics are preserved.


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
`test_web_chatgpt.py` covers the ChatGPT sign-in routes with a fake helper
(`tests/fake_chatgpt_helper.py`), their roles, CSRF, error codes and audit details, and the
`executor_sign_in` readiness check; `test_readiness_reflects_the_internet_switch`
covers `egress_proxy` and `web_search_key`.
The RBAC suite includes ten accounts and twenty projects with five concurrent
viewer requests; it is a functional scope check, not a throughput guarantee.

## 10. Limitations And Future Work

The web editor covers single-value settings, edited on their rows;
administrators can also import a TOML profile. Direct host file
edits outside ADORE do not use the shared lock, but revision checks reject a
stale browser edit. Multi-host API deployment and a shell-style log viewer are
not provided.

## Stable identity and paused enrollment contracts

All routes below require administrator authorization and mutation CSRF:

| Route | Input | Result |
| --- | --- | --- |
| `POST /api/v1/projects/id-availability` | `name` | Advisory `available` plus structured `issues`; never reserves an ID |
| `GET /api/v1/executor-images?runtime=docker\|podman` | `runtime` | Read-only; runs `<runtime> images --format {{.Repository}}:{{.Tag}}` with a 15 s timeout, drops `<none>` entries and returns `{runtime, available, images}` for image suggestions |
| `POST /api/v1/projects/{name}/labels/ensure` | none | Reads the repository's labels once and creates only the project's missing ADORE labels (colour and description); returns `{created, existing, failed[{name, reason}]}` and audits `labels-ensured`; 503 `forge_read_failed` (or the repository-auth code) when the labels cannot be read |
| `POST /api/v1/projects/repository-source` | `url` | Detected `kind` (or null), `login`, `repo`, `default_branch`, validated sorted `branches`, derived `name`, `display_name`, `repo_path` (`<home>/repos/<name>`) and `clone` (`new`/`existing`); `repository_url_invalid` 400, `repository_unreachable` / `repository_branches_invalid` 502; no writes |
| `POST /api/v1/projects/setup-preview` | Existing guided fields, optional `display_name` and `clone_url` | Local `structural_valid`, findings, `pickup: stopped-on-create`, unverified environment; no writes/probes |
| `POST /api/v1/projects` | Same guided fields | Complete profile with pickup already stopped |
| `POST /api/v1/projects/import-preview` | Exact TOML and optional identity | Resolved identity, candidate revision, config digest, structural findings and safe review |
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

`ProjectInput` adds typed bounded run budgets, ready/approval labels, `provider`,
`model`, `endpoint_base_url` and `endpoint_api` (the endpoint fields only for
provider `custom`) and optional additional credential environment names; omitted
fields keep their defaults. Enrollment takes no secret value. Unknown fields are
forbidden. Enrollment accepts only `auth_mode` `api-key`; malformed or duplicate API-key names are rejected and an empty API-key list is allowed
with value-free findings. Server clones are absolute existing Git roots.
Preparation uses the existing wizard in prepare-only mode and its configuration validator.
The generated comment is deterministic for web setup, so identical drafts yield identical
config bytes across requests. No external commands or profile writes occur during preview.

`setup-preview` returns `revision`, `config_revision`, canonical `review` and `defaults` (every
editable setting whose effective value equals ADORE's built-in default, as `[{key, value}]`,
shown read-only on Review and create) for a valid
candidate. The draft SHA-256 binds exact config bytes, profile name, display name and
description. Review includes complete setup, resolved env-key names, `provider`, `model`,
`endpoint_base_url` and `endpoint_api` (empty unless `custom`),
`credential_variable` (the variable to save after creation; null for
`chatgpt`) and absolute config, state and worktree paths. Invalid candidates keep null review/digests and structured findings.

`ReviewedProjectInput` requires a 64-hex revision for the additive Admin/CSRF routes:

- `POST /api/v1/projects/setup-check`: rebuild, compare draft revision, run shared
  bounded `_probe_setup`, return redacted checks/model evidence with both revisions,
  UTC time and status. Failed checks yield failed; unprobed model or WSL yields partial.
  Gitea auth uses the selected tea login. No draft, readiness record or profile persists.
- `POST /api/v1/projects/setup-create`: rebuild, compare revision, publish the exact
  candidate using the existing locked stopped-pickup boundary. With `clone_url` and no
  clone yet, it first clones (`repository_source.clone`), requires the AEGIS files and
  `origin/<target_branch>` (`repository_aegis_missing` / `repository_branch_missing` 409,
  `repository_clone_failed` 502) and removes the fresh clone if anything fails; the
  same applies to `transfer-create` and `POST /projects`. `clone_url` is part of the
  draft revision; preview requires an absolute `repo_path` outside ADORE home or under
  `<home>/repos` (proposed `<home>/repos/<name>`) and a matching repository, refuses an
  occupied location (`clone_path_occupied`), reserves the folder with an exclusive mkdir
  and a sibling `.<name>.adore-cloning` marker (an in-progress clone is never treated as
  reusable or removed by another request; parents are created only under `<home>/repos`,
  elsewhere they must exist; `repo_path` is used as typed, without `~`), and runs the wizard
  with `pending_clone`; checks report `aegis_files: "not-checked"` until the clone exists. Duplicate IDs are
  rechecked under its lock; stale drafts return 409 before publication.

Existing `POST projects` retains its request/publication contract; exact import revisions bind complete identity and inspected ownership/state.
A current, server-issued one-use check token transfers its measured checks to the created profile. Tokens are bound to the administrator, exact draft and config revisions, expire after 15 minutes, and cannot be replayed; absent tokens leave the profile unverified. A pending clone keeps AEGIS files not checked, so partial evidence is not promoted. The shared probe helper also serves the persisted project readiness
route, whose storage/schema and mid-probe revision protection remain intact.
`test_web_enrollment.py` covers canonical fields/bytes across clock changes, stale and
duplicate publication, explicit ephemeral failed/partial checks, selected Gitea login,
secret-reference redaction and Admin/Dev/CSRF rejection; `test_web_readiness.py` covers
the persisted route regression.

### Persisted project readiness

`POST /api/v1/projects/{name}/readiness-check` retains bounded explicit probes and
atomically writes profile-owned `readiness.json`, independent of runtime schema.
Schema 2 contains immutable `project_id`, private machine/account and authentication-context bindings, exact config-byte SHA-256 `revision`, UTC
`checked_at`, API-host context and typed prerequisite checks.
Checks cover git, forge CLI/auth, runtime, the Pi CLI and AEGIS files; there is no
model endpoint check (model access comes only from the explicit AI connection test).
A `chatgpt` project's record also carries the boolean `executor_sign_in` (the server's
ChatGPT sign-in), and the internet switch adds the boolean `egress_proxy` or
`web_search_key` (`_INTERNET_CHECKS`); the reader accepts these optional keys in
addition to the six required ones, and a false value makes the record `failed`.
Commands/output/credentials are never persisted. Schema, keys, types,
identity, digest, time, required configuration-specific checks and redacted values are validated on read; a changed machine/account or relevant authentication input makes it stale; corrupt evidence
fails closed with `readiness_corrupt` (HTTP category `readiness_probe_failed`).

Absent evidence is `unverified`; differing config bytes are `stale`; matching evidence
is `failed` if any check fails, `partial` for undetected WSL runtime or uninspected AEGIS files, otherwise
`verified`. Freshness is revision-based, not age-based. Display edits do not stale
verification. Invalid configuration is separate from stale/absent evidence. A config
change during probes returns `stale_config_revision` without replacing evidence.
Storage failures return a safe `readiness_store_failed` finding.

Offline contract proof is in `test_web_enrollment.py` and `test_web_errors.py`,
including concurrency, worker discovery, rollback, stable project identity, secret handling,
RBAC/CSRF, revision races and corrupt persisted evidence.

## Project repository authentication

Admin/CSRF POST /api/v1/projects/{id}/repository-connection accepts server,
token and explicit allow_http. API owns config/conductor locks, idle/pending/
archive checks and identity/digest recheck. repository_auth verifies bounded
CLI account/repository evidence and returns safe identity. begin_change records
uncertain filesystem publication before atomic token replacement; confirmation
marks completion. No request secret enters audit. Readiness and connection
serialize through config_lock so an old credential check cannot overwrite fresh
invalidation. Errors use stable value-free codes. See Component_Repository_Auth.md
and tests/test_repository_connection.py.

The Gitea host sign-in check uses bounded tea api GET user with the configured
login. Authentication requires a successful HTTP status and a valid, unique JSON
login identity. This supports tea versions whose whoami command has no login flag.


## Project tickets

Ticket reads happen only on explicit requests from the project Jobs tab.
`GET /api/v1/projects/{name}/tickets` (any user with project access) reads up
to 500 open forge issues through the project's scoped credentials within a
60-second request deadline (30 s per CLI call) and returns `read_at`,
`truncated`, `ready_label` and tickets with number, title, description,
labels, author, web link, update time, `startable`/`reason` from the shared
eligibility rules, `can_start`/`blocked_by`/`adds_ready_label`/`needs_priority`
(what an explicit Start may add, or the rule labels cannot fix), any existing
run's `run_id` and `lifecycle`, and the configured `priority_labels`.
`POST /api/v1/projects/{name}/tickets/{iid}/start` (CSRF, idempotency key,
optional `priority`; 409 `project_archived`) re-reads the ticket, adds the
missing ready label and the chosen configured priority label, then queues the
`start` operation and audits `ticket-start-prepared`; it returns
`operation_id`, `status` and `labels_added`. Rules labels cannot fix return
409 `ticket_not_startable` with the rule as message, a missing priority choice
400 `priority_required`, and a failed label write 503 `forge_write_failed`
with nothing queued (audited `uncertain`). Replaying the same idempotency key
returns the original start operation; a malformed ticket record returns 502
`forge_response_invalid`. Manual Start can queue the selected ticket while automatic monitoring remains paused; eligibility, locks, capacity and approval gates still apply.
`GET /api/v1/operations/{id}` returns `id`, `project`, `action`, `status`,
`result`, `reason`, `detail` and the timestamps. The worker runs the CLI with
stderr joined to stdout; a non-zero exit or timeout stores in `detail` the last
20 lines (at most 2000 characters) with NUL/ANSI removed and credentials
redacted (`jobs.redact_text`) before the cut, and a refused start stores the
code of the CLI's `error: ticket #N not started: <code>` line for its own
ticket in `reason` (`pickup_paused`, `at_capacity`, `aegis_probe_failed`,
`not_eligible`, `conductor_busy`). Both live only on the operation row, never in
the audit evidence. The web database has one schema (16); a database in any
other version is refused with a message naming the files to delete, never
migrated.
`GET /api/v1/projects/{name}/tickets/{iid}/comments` returns human comments
in forge order without system notes, or 404 `ticket_not_found`.
`POST /api/v1/projects/{name}/tickets/{iid}/stop` (CSRF, idempotency key;
409 `project_archived`) queues `cancel` for the ticket's unfinished run first,
then removes the configured ready label when present, audits
`ticket-stopped` (result `uncertain` when the label write failed) and returns
`cancel_operation_id`, `ready_label` (`removed`/`absent`/`failed`) and
`ready_label_error` (`forge_write_failed`, `forge_response_invalid` or a
repository-auth code; the forge is built only after the cancel is queued).
Forge CLI failures map to 503 `forge_read_failed`, credential problems to their
repository-auth code, malformed forge output to 502 `forge_response_invalid`
and an unreadable run to 503 `run_state_corrupt`; no partial list is returned. Implementation:
`adore/web/tickets.py`; tests: `tests/test_web_tickets.py`.

## Explicit AI connection test

Administrators use **Settings → Agent and model → Test AI connection** for the configured Pi provider and model. Each explicit click sends one short request over Pi's RPC mode in a temporary container, or in a temporary folder for Pi installed on the server, and may incur provider charges. The project must be idle with valid saved settings and no pending configuration/operations; a container project's installed image must contain the pinned Pi.

Only a valid completed challenge response reports connected: one completed shell command printing a nonce, then the exact reply (a failed shell call reports **tool-call-failed** with permission guidance). A container project whose provider needs a key with none saved or set reports **credential-missing** without starting a container. A `chatgpt` project first gets an access token from the server's ChatGPT sign-in (valid for the 90 s probe plus 300 s) and reports **sign-in-required** when the server is not signed in or must sign in again, **subscription-refused** when OpenAI refuses the account's plan, **connection-failed** when OpenAI cannot be reached and **usage-limit** when Pi reports the subscription's rate limit. Failures provide redacted guidance for a missing or invalid credential, model availability, rate limits, provider errors, image, CLI version or network. The action reuses executor credentials and the derived egress (`egress_policy`), never loads web tools and starts no job. Evidence is durably saved, bound to current project/model/configuration and credential inputs. Summary and host-check details reuse the current access result. Host-check time/version are internally validated and hidden from Summary/check details. See Component_Model_Connection.md.

## Project executor configuration

**Project → Settings → Agent and model** configures Pi, ADORE's only coding agent; there is no agent choice. It shows Test AI connection, the agent connection (Provider, Model, and for an OpenAI-compatible endpoint Endpoint base URL and Endpoint API type), the launch command (`executor.command`; only the Pi preset for container projects, fixed managed Pi RPC for local projects), Internet access for the agent (`executor.internet`, boolean, default false), Web search (`executor.web.search`, choices `exa`, `brave`, `tavily`, `none` in the setting catalog), additional credential variables (`executor.env_keys`), the provider API key, the execution environment and estimated prices. The connection, the command, internet access and web search are settings saved together with important-effect confirmation and existing paused/idle authority. Installed agents and runtime preparation remain external. The old `/executor` URL redirects to Settings. Developers read non-secret settings/results without mutation actions.

The names-only selector for additional credential variables offers the known provider key variables and retained custom names; it defaults to empty because the provider's key variable is always passed. Applying names does not delete saved `.env` values. Provider API key offers private Save/Disconnect for the variables of `pi_providers.credential_variables` only (the configured provider's credential variable, then `BRAVE_API_KEY` or `TAVILY_API_KEY` while internet is on with Brave or Tavily search) and shows their sources only; key changes require paused pickup and idle/pending-free state. A `chatgpt` project has no provider credential variable (only the search key, when needed); it uses the server's ChatGPT sign-in (next section). Explicit Test AI connection remains the evidence of model access and may incur provider charges. Config GET returns `model_connection: null` for a `chatgpt` project while the server is not signed in. See [Executor configuration](../05_SoftwareDocu/Component_Executor_Configuration.md) for the exact API/storage contracts.

### ChatGPT sign-in

The server holds one ChatGPT sign-in in `<ADORE home>/chatgpt` and at most one pending sign-in in memory, both under one lock; `adore/chatgpt.py` does the work (see [ChatGPT sign-in](Component_ChatGPT_Sign_In.md)). All routes are Admin-only; changes also need CSRF.

- `GET /api/v1/chatgpt-sign-in` returns `{status, pending}`: `status` is `signed-in`, `not-signed-in` or `sign-in-again`, read from files without starting Pi; an existing pending helper is polled for automatic callback completion and audited once. `pending` says whether a sign-in waits for its redirect address. A sign-in older than 15 minutes is ended and reported as not pending.
- `POST /api/v1/projects/{name}/chatgpt-sign-in` starts Sign in with ChatGPT through that project's selected helper (the image's Pi for containers or managed native Node/Pi for local projects) and returns `{authorize_url, expires_in}` with `expires_in` 900. It ends a previous pending sign-in first. It returns 409 `project_archived`, 503 `config_corrupt`, 409 `invalid_config` for an invalid configuration. It does not require paused pickup or an idle project.
- `PUT /api/v1/chatgpt-sign-in` takes exactly `{redirect_url}` (1-8192 characters) and returns `{status, pending}` after Pi stored the credential. A malformed address (400 `chatgpt_redirect_invalid`) or one from another attempt (400 `chatgpt_state_mismatch`) leaves the sign-in pending; any other failure ends it. Without a pending sign-in it returns 409 `chatgpt_sign_in_not_pending`.
- `DELETE /api/v1/chatgpt-sign-in/pending` ends a waiting sign-in and keeps the stored credential; it returns `{status, pending}`.
- `DELETE /api/v1/chatgpt-sign-in` (Disconnect) ends a waiting sign-in, deletes `auth.json` and the sign-in-again mark, keeps the installation id and returns `{status, pending}`; a file that cannot be removed returns 503 `chatgpt_credential_unreadable`.

Sign-in failures map to value-free codes: 409 `chatgpt_credential_unreadable`, 502 `chatgpt_not_eligible` (the account's plan cannot share the subscription with Pi), 502 `chatgpt_access_denied`, 502 `chatgpt_code_rejected`, 502 `chatgpt_sign_in_refused`, 503 `chatgpt_sign_in_unavailable` (OpenAI not reachable, or no link within 60 s) and 503 `chatgpt_helper_failed` (the selected native installation or image cannot run ADORE's helper). Audit actions are `chatgpt-sign-in-started` (with the project name), `chatgpt-sign-in-failed` (with the project name when the start failed), `chatgpt-sign-in-completed`, `chatgpt-sign-in-cancelled` and `chatgpt-disconnected`; the stored detail of `chatgpt-sign-in-failed` is only the `chatgpt_<code>` error code, and redirect-invalid, state-mismatch and not-pending are not audited. Audit rows and error responses never carry a token, authorization code, link or redirect address; the link appears only in the start response's `authorize_url`. `create_app(chatgpt_popen=...)` injects the helper's process factory for tests. Proof: `tests/test_web_chatgpt.py`.

## Preparation review and apply

The setting catalog exposes closed execution settings with server limits. Recipe candidates retain the complete plan and public image/source/commands; Apply re-resolves exact source/configuration and refuses stale plans. Direct execution-setting writes require pending review. Host readiness and explicit model tests normalize the effective image without running setup. Existing grants, CSRF, config/conductor locks, pause/quiescence and portable allowlists continue to apply. Focused proof: `tests/test_web_pending_config.py`, `tests/test_model_connection.py`.

## Native execution contract

Native project setup accepts the current account and optional tools PATH; reviewed edits refuse a native launch override. Host readiness probes managed Node/Pi, the native scope and the selected credential, returning closed diagnostic evidence on explicit checks. Saved readiness keeps its existing boolean contract.

## Project images

Container images are managed outside ADORE. The retired image-build routes are
removed (they answer 404) and `ConfigEdit` has no `image_build_id`; the
administrator chooses an installed image for `container.image` through the
reviewed environment candidate. See Component_Project_Images.md.

## Reviewed executor configuration

`executor.connection` is a virtual candidate key whose value is strict JSON `{provider, model, thinking, base_url, api}` (endpoint fields empty unless the provider is `custom`); it is staged through `POST config/pending`, applied like other candidates, and rewrites `[executor] provider`/`model` and removes or adds `[executor.endpoint]` while preserving unrelated TOML (verified by re-parse). Its review value is that object. `executor.provider`, `executor.model`, `executor.thinking`, `executor.endpoint.base_url` and `executor.endpoint.api` cannot be staged individually (400 `setting_not_editable`). `executor.command` is a container-only single-key candidate with the Pi preset. `executor.env_keys` owns a complete names-only list. All require pending review and existing paused/idle apply guards. Public pending values and persisted scope are closed and checked against the unchanged base. Source-only private credential APIs retain their contracts. See [Executor configuration and credentials](Component_Executor_Configuration.md) and test_web_executor_configuration.py.

## Confirmed failed-job restart

`POST /api/v1/projects/{project}/operations/restart` requires the existing mutation grant/CSRF checks plus `run_id`, `confirmed: true`, exact `state_revision` (64 lowercase hexadecimal characters) and idempotency key. It accepts only a nonarchived project's failed job at that revision. Confirmation/revision format errors are 400 `invalid_operation`; changed state is 409 `job_snapshot_changed`. Replays bind project, action and original revision even after state cleanup. No stored schema changes are required. Read and queue phases perform no resource mutation.

## Reviewed budgets for parked clarification jobs

The reviewed `POST config/apply` path permits `parked-clarification` alongside
terminal states only when every scalar/batch member is one of the five `[budgets]`
settings. Current and candidate TOML must equal the exact reviewed edit, preventing
unrelated scalar payload changes even with recomputed hashes. Base/candidate
revision, Admin/CSRF, managed state root, conductor/configuration locks, valid
state and no unfinished operations remain mandatory. Working, approval, review
and human-ownership lifecycles block apply. Mixed batches and direct config PUT
retain their existing idle requirements. Applying writes no job state or approval;
current limits take effect on resume through the existing conductor.

`GET /api/v1/jobs/{project_id}/{run_id}` adds the non-financial `budget` observation
from `jobs.read_job_budget`, after scoped authorization and with another profile
recheck. Offline positive/refusal proof is in `test_web_settings_batch.py` and
`test_web_jobs.py`.

Current limit faults preserve valid Job details and recovery. The budget observation
uses `availability=unavailable`, a closed missing/corrupt reason and null limit/revision
fields, while keeping trustworthy consumed launches and active seconds. The interface
shows — for limits and a localized notice. Corrupt saved job evidence still rejects
the detail read. Metadata-only profile history retains its existing recovery behavior.

## Job diagnostics and concurrent usage

The scoped executor-output GET delegates to the strict job snapshot and host-captured evidence reader. It returns only project/run identity, availability, normalized stdout/stderr and exit/timeout facts; source paths, argv and raw IO are never returned. Latest entries without a capture reference return missing, not an older output.

Usage projection accepts an older request snapshot after another request advanced the cursor only when a fresh strict selected-run journal confirms both the incoming prefix and the saved cursor digest. It validates every returned projected event, retains the newer cursor and preserves the older request's real snapshot. Changed or truncated sources still fail closed; no automatic retry or fabricated totals are used. `test_web_metrics.py` includes a controlled HTTP interleaving and persistent-cursor checks.


History projects verified ticket and job target identities independently of operation IDs. It exposes prepared, applied, rejected, failed and uncertain outcomes and refuses mismatched operation/project bindings. Project visibility remains bound to immutable authorized project IDs.

Readiness checks bind private hashes of relevant owned and external CLI authentication inputs. Draft tokens and project checks recheck the binding before publication; changed credentials make old evidence stale. Corrupt or old readiness records are refused before any replacement. Responses declare required checks, and the browser verifies their presence before displaying a verdict.

A successful external CLI sign-in is not a bound identity and keeps the overall result partial. Only a validated project-scoped repository credential binds the forge identity; the project list separately reports the check keys derived from current config. Probe values are validated before replacing evidence.
