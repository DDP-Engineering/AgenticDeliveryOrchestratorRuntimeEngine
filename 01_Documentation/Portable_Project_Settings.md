<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Portable project settings

An administrator can open a project's **Settings → Export portable settings**,
read the included/excluded data, choose **Preview active rules**, then
**Download portable JSON**. The server validates the active configuration before
exporting. Pending configuration changes stay outside the download. A changed
portable preview requires a fresh preview; a failed read disables download.
Developers and invalid sessions cannot export or discover project metadata
through this endpoint. No live forge, container or credential check runs.

The package transfers working rules as defaults for a **new project** on a
compatible ADORE installation. On Projects, choose **Clone project config**, then
**From a portable settings file** for a JSON file or **From a project on this
server** for an authorized source project. Review recognized rules and exclusions, then **Set up new target**.
Supply a new display name/stable ID, repository identifier and existing server
clone, runtime/image/model, reviewers/labels and target credential environment
names or supported host authentication. Reconfirm the target environment,
credential references and endpoint setup explicitly. Standard provider connections
use the selected model; custom target endpoints are a separate Settings action
while pickup remains stopped. All source references are excluded.

Validate setup to see **Source value / This server value / Effect** for all 15
rules. This server value is the installed default; the source rule becomes the
new project's rule. Copied budget controls are read-only. Review includes
independent allocated config/state/worktree/metrics locations. Confirm **Create
project with pickup stopped**, then open the new project. Checks and activation
remain explicit separate actions. No repository is cloned and no existing project
is replaced. Jobs/history, access, audit, pending changes, secrets and source
ownership stay at the source.

Changing target answers invalidates review/checks; Back retains corrections.
Source/file revision changes block confirmation with a typed conflict and
**Review source again**. Selected files are reread before target operations.
Returning to source or changing method discards target corrections after the loss
warning. Missing/corrupt/incompatible sources, unresolved references, occupied or
overlapping ownership and duplicate confirmation create no partial profile.
SHA-256 revision binding detects changes and does not authenticate a file.

## Exact format and allowed values

The JSON envelope has exactly `kind`, `schema_version`, `source`, `settings`,
`checksum`. Kind is `adore-project-settings`; schema_version is integer `1`.
Source has exactly `product: "ADORE"`, `contract: "portable-rules-v1"` and
`version`, read from the running package's `adore.__version__`. Compatibility
requires the **exact same installed ADORE version** and contract. Future or older
sources are rejected; unsupported fields are never silently discarded.

Settings has exactly these sections and all fields below, including resolved
defaults when active TOML omits them:

| Section | Complete allowed fields |
| --- | --- |
| polling | `mode` (`loop`/`once`), `poll_interval_seconds` (positive integer), `poll_jitter_seconds` (nonnegative integer), `poll_backoff` (boolean), `max_concurrent_runs` (positive integer) |
| readiness | `require_acceptance_criteria`, `require_priority_label` (booleans) |
| recovery | `max_stage_failures`, `max_transient_retries` (positive integers), `retry_backoff_seconds` (1–100 nonnegative integer entries) |
| budgets | `max_iterations`, `max_wall_clock_seconds`, `per_gate_timeout_seconds`, `max_files_touched` (positive integers), `max_cost_usd` (finite nonnegative JSON number) |

Every integer and the USD cap are at most 1,000,000,000. Boolean values cannot
stand in for numbers; fractional values cannot stand in for integer limits.
`max_cost_usd = 0` disables reported-cost enforcement while other bounds remain.
Concurrency is a ceiling; the current serial conductor does not gain parallel
execution by importing a higher value.

Only this list is portable. Exclusions include agent/profile/display identity;
forge, repository, login and branch ownership; all state/worktree/metrics paths;
labels, free-text scope hints, quiet hours and timezone assumptions; commands,
models, environment, all credential values/references and endpoints, images,
mounts and container/network policy; clarification, workflow, delivery, review,
reconcile and metric settings; jobs/history, users/grants/audit, pending revisions
and financial price history. The cost cap is a job limit, not financial history.
No exported reference implies credentials or endpoints are valid on a target host.

## Integrity and strict rejection

SHA-256 detects changes and **does not authenticate** an untrusted file: anybody
can change content and recompute it. Treat the package as untrusted input and
review its rules before enrollment. The digest covers the envelope
without `checksum`, encoded with sorted keys, ASCII JSON escapes, compact `,`/`:`
separators, finite numbers and no newline. The completed envelope uses that same
encoding followed by one LF. Equal effective values and source produce identical
bytes; no timestamp or project/host identifier is embedded. See the
[exact specification](../.agentic/specs/REQ-DATA-9528fad6.md) for the complete contract.

The parser accepts UTF-8 JSON up to 64 KiB and rejects missing/unknown keys,
duplicates at any depth, unsupported source/schema/type, invalid limits,
malformed nested values, nonfinite numbers, encoding/depth failures and checksum
mismatches with `PortableSettingsError`. It returns no partial values.
Export accepts active UTF-8 TOML up to 512 KiB, validates recognized declared
structure and the existing configuration contract, then projects the allowlist.
Unknown declared source fields also fail closed even if the legacy loader would
ignore them. Correct the active file on the ADORE host and preview again;
configuration values and host paths never appear in export errors.

## API and other formats

`GET /api/v1/projects/{name-or-id}/config/portable-settings` requires Admin and
returns the canonical envelope with `Cache-Control: no-store`. `download=true`
adds fixed attachment filename `adore-project-settings.json`. Optional `checksum`
binds a request to portable preview values; a mismatch returns HTTP 409
`portable_settings_changed`. Invalid/unreadable sources return 503
`portable_settings_invalid`. Authentication/role denial occurs before lookup.
The read rechecks project ownership after snapshot export and rejects a replaced
identity. It performs no state mutation or runtime migration.

Admin/CSRF `POST /api/v1/projects/transfer-source` returns strict rules and exact
source revision. `transfer-preview` adds fresh target answers and mandatory
reconfirmation; `transfer-check`/`transfer-create` bind the reviewed revision.
Source role/session, immutable identity, exact configuration and current target
ownership are rechecked during confirmation. See
[Web API](../05_SoftwareDocu/Component_Web_API.md) for fields and typed errors.

**Exact server TOML enrollment** retains host locations and its existing guarded
byte-exact review/import contract. **Statistics CSV** contains measurement rows
and retains its existing authorization/filter contract. Neither is a portable
working-rules package. Live acceptance, novice participants and a comprehensive
accessibility audit remain separate from offline automated verification.

## Container preparation

Preparation selection, execution backend/bounds, recipe files, images, environment and credentials are outside portable rule packages. Configure/review them independently on the target host; the existing narrow rule allowlist remains unchanged.

## Native local execution

Backend, native account/home/PATH/environment/cgroup and runtime identity are excluded from portable working rules. Prepare each destination account independently.

See [Local execution](Local_Execution.md) for platform prerequisites, configuration,
authentication, process ownership and acceptance coverage.
