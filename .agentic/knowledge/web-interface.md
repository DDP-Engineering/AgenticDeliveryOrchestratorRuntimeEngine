<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web interface

Technical details displays Durable job state folder (`state.store_root`), Workflow Python command (`workflow.aegis_python`), Existing local repository path (`worktree.repo_path`) and Job working folders (`worktree.root`) as informational installation values. Operators configure them in the project TOML on the ADORE server; generic web mutations are refused. The localized guidance explains that changing a path does not relocate existing job state, repositories or working folders.

Project Settings follows **Repository → Tickets → Implementation → PR/MR and review → Statistics → Agent and model**, followed by closed **Technical details**. Repository owns platform/author identity and the single integration-branch editor; PR/MR shows its value and a link that opens/focuses that row. Tickets owns eligibility, polling, priority/type and pickup/status labels; hold/exclude affect pickup, not already-started jobs. Implementation owns capacity, budgets and progress commits, with closed Clarifications, Recovery after errors and Advanced stage time limits. Statistics owns recording/token switches and the informational database file inside closed Advanced statistics paths. Technical details and worktree paths are read-only; Repository branch naming uses reviewed edits and a server-checked example; runtime installation stays external and Agent and model groups executor settings in Settings. Interval, jitter and backoff remain visible; standalone CLI startup mode (`polling.mode`) stays in TOML/raw configuration and the effective catalog. Inactive reserved controls are omitted without changing CLI configuration. All categories start closed, retain reviewed Admin edits and Dev redaction, and have four-locale names.

Implementation uses shared four-locale names for reviewed settings, including **Active job limit**, **Maximum executor launches per job** and **Active work time limit (seconds)** names in rows, editors and candidate review. Help describes serial capacity with parked jobs excluded, lifetime launch counts, resettable active periods and between-attempt time/cost checks. Reported USD accounting depends on captured token usage; cost-only reports do not count. File guidance describes distinct committed/pending/new product and AEGIS paths, the unfinished-merge exception and continuation when Git counting is unavailable. Per-attempt timeout help preserves configured recovery and strict-check semantics; progress publication is enabled by default with local commits retained when disabled, and the quick label is an optional framing hint. Configuration keys, runtime enforcement and role/redaction contracts retain their current behavior.

The revision-round limit belongs to PR/MR and review, with shared default five and localized combined-budget/exhaustion guidance. Acceptance checking defaults false; explicit values remain authoritative. Portable enrollment validates mapping size against the fifteen recognized rule keys.

Project settings keeps ready visible in Tickets and places answered/clarify/done/failed/review/working names in a native initially closed Status labels disclosure. Four-locale row/editor/review names explain actual lifecycle semantics. Inactive executor prefix and scope hint are omitted from controls while technical config/catalog values persist; admin reviewed edits and Dev read-only access retain existing authority.

`labels.control.exclude` has a shared four-locale Exclude from pickup label name in row/editor/candidate review. Help identifies the label-name setting and reversible presence-based pickup gate; already-started jobs continue.

`delivery.target_branch` has a shared four-locale Target branch label (Romanian: Ramura de integrare) in the row/editor/candidate review; help identifies the new-job remote base and PR/MR destination, short name without origin/, and human merge boundary.

`delivery.draft` is presented as localized PR/MR state at publication with Draft/Ready for review choices, using the existing administrator reviewed prepare/apply flow and boolean wire contract. Active/default/proposed values carry the same names; in-review covers both forge states.

Secondary text uses contrasting light/dark theme colours. Project metadata,
configuration values, type/domain hints and field help use 0.875rem text with
1.5 line height; long identifiers and guidance wrap within their panels.
On narrow screens, setting labels, values and help stack vertically.


About shows the DDP Engineering logo band, ADORE and its version, and What's
new / License / Third-party notices buttons; licenses stay folded until pressed.
What's new renders `release_notes` from `/api/v1/about` (packaged
`adore/release_notes.toml`, four locales, English fallback, `Unreleased` as In
development); agents maintain it under AGENTS.md "Release notes rules" and
`02_Tools/check_release_notes.py` checks it.

**How ADORE works** opens the in-app help center (`/help`, `/help/<topic>`):
ten bundled Markdown topics per locale under `src/help/content/`, parsed by
`src/help/markdown.ts` (subset, explicit heading ids, no HTML), with search, an
outline and contextual **?** links (`HelpLink`) on the Tickets view, the Add
project wizard and project Settings. Agents keep it current under AGENTS.md
"Help content rules"; `tests/help.test.mjs` enforces parity and links. The
glossary is the Glossary topic. Full job history is reached through the sidebar Jobs link; Overview
keeps job-specific Details links.


Projects labels new-ticket pickup as **Monitoring**, with Active/Paused states.
The directory shows project, repository path, Repo (Gitea/GitHub/GitLab),
Monitoring, jobs and last activity. Open the project to use Summary actions
for pause/activate monitoring and archive/restore;
delete is available for an archived idle project after exact-name confirmation;
an unticked option also removes the ADORE-owned local clone (delete-preview says why
a clone stays).
Environment verification records explicit checks against the saved configuration
revision; Unverified means no current evidence, not an observed failure. Use
Project details â†’ Summary â†’ Check host prerequisites for the administrator check.
Pause semantics are available in header help instead of repeated row guidance.
The dedicated header combines name/repository and Summary, Settings, Jobs, Statistics, History, Access tabs; Access is Admin-only.
Jobs and Statistics render inside the hub; the identity band appears only there.
The Jobs tab opens on a Tickets sub-tab (read on request, Start that can add the
ready/priority labels, Retry, Stop and Details per ticket; more than 10 tickets are paged 10/25/50/All with page X of Y) beside a Jobs sub-tab with the job table and detail. Administrators record estimated prices in Settings > Agent and model. Deletion confirmation clears on page or project changes.

Implementation settings support reviewed edits for human-answer waiting time (positive integer plus seconds/minutes/hours/days), positive question-round count, a nonempty retry schedule (one nonnegative integer per line), and the complete stage-timeout map. The five stage rows (frame, specify, design, build, validate) choose either the general attempt limit or a positive custom limit in seconds; choosing general removes the override. Retry and timeout collections accept only safe integers and their declared keys; other lists/maps remain read-only except the existing reviewer list. Admins prepare, inspect active/proposed values and apply only at the existing idle boundary; developers remain read-only. Names, help and controls share four locales. The answer deadline is independent of the reserved reminder; reminder format is still checked and no reminder is sent.

`REQ-FUNC-d67a1d33` / `REQ-UX-66547cbf`: `web/implementation_settings.py` validates only retry delays and the complete five-stage map and verifies a single semantic TOML edit. `web/src/implementationSettings.ts` supplies safe draft serialization and editor copy. Typed groups fill the editor width with normal-height nested controls and action buttons below the stack. Metadata emits one parent stage-map row for empty or populated maps; reviewed values and unchanged-base candidate meaning are checked again before apply. `test_web_pending_config.py`, `web/tests/settings.test.mjs` and typed Implementation/locale/Dev journeys in `web/e2e/settings.spec.ts` prove this seam.

## Branch naming presentation

PR/MR settings names the CI response **Action when PR/MR CI checks fail**.
Active/default values, option labels and candidate review use **Automatic repair**,
**Notify only** and **Ignore**, localized in English, French, German and Romanian.
The configured values remain `revise`, `notify` and `ignore`. Help explains the
shared revision-round limit and fresh human approval before repair publication.
The read-only Integration branch reference uses the standard responsive setting
row: description and Repository link in the label column, Active value and the
branch in the value column, with the same value typography as other settings.
Its link opens Repository and focuses the single target-branch setting.

`SettingsList` owns reactive revision/draft-bound preview requests, cancellation of stale completions and closed `validBranchPreview` transport checks. Repository offers two text editors using shared four-locale row/editor/candidate names and help. Preview shows the effective/proposed pair and fixed example inputs; malformed, mismatching, stale or unavailable evidence cannot prepare a branch candidate. Developer preview is read-only and respects the project grant; runtime paths remain informational. The preview card wraps in narrow layouts and announces updates through a polite live region. Focused proof: `web/tests/settings.test.mjs`, `web/e2e/settings.spec.ts` branch-naming and locale journeys.

## Branch naming preview and edit authority

`POST /api/v1/projects/{name}/config/branch-preview` accepts the closed strict body `{template, rule, revision}` (512-character text bounds, SHA-256 revision). Scoped users supply CSRF; the shared config lock coordinates preview reads with application, and project grants and before/after revision checks precede evidence release. The route returns the shared config preview plus inspected revision and performs no writes or Git operations. Corrupt source returns `config_corrupt`, stale input returns `stale_config_revision`, and malformed transport fails request validation. Scoped developer reads hide inaccessible project identity with the existing 404 policy.

Only `worktree.branch_template`, `worktree.branch_rule` and the administrator-chosen `execution.backend`, `container.runtime`, `container.image` and `local.account/home/path/cgroup_root` are exceptions to the external environment edit restriction. They advertise editability/restart and retain administrator, validated single-setting candidate, lock, revision, paused/idle and replay integrity gates (direct PUT of the chosen keys returns 409 `pending_config_required`). Every other worktree/container/execution/local setting keeps external ownership. Focused proof: `tests/test_web_branch_naming.py`, `tests/test_web_config.py`, `tests/test_web_pending_config.py`.

## Routing

Use this page for `adore-web`, `adore-web-worker`, `/api/v1`, web login/RBAC,
React action workspaces/project hubs, the web queue, or offline web media. Start at
`04_Software/adore/web/app.py` for API behavior and
`04_Software/web/src/App.tsx` for shell/project behavior and `JobWorkspace.tsx`
for attention/global jobs/details; `web/e2e/jobs.spec.ts` verifies those views. Focused tests are
`04_Software/tests/test_web_*.py`. Engine internals belong to `orchestrator.md`.


`REQ-UX-34718dd6`: Admin Project settings exposes Request review from as a reviewer-only six-line list editor. Typed exact candidate authority and complete TOML array replacement retain existing revision/access/idle/apply checks. Developers retain read-only settings; retry schedules use their own integer editor; other arrays stay outside generic editing.

## Purpose and boundaries

The optional web package gives one ADORE host an authenticated dashboard and
durable control queue. The API reads existing profiles and run state and never
launches an executor directly. The separate worker executes fixed CLI commands;
the orchestrator still owns readiness, locks, approvals and draft publication.

## Public interface

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

- Project settings report `delivery.publish_checkpoints` with shared default
  true; an explicit false remains effective with source `project`.

- `/audit-page` selects actor ID, stable project ID, exact action and half-open
  UTC instants before counts/server paging. Actor IDs and offsets reject values
  outside SQLite signed64-bit bounds. Admin global history includes closed
  structured evidence; Dev sees only a currently assigned project and operational
  actions, excluding admin/access/price/financial-config/name-only rows. `AuditHistory.tsx` renders
  who/what/when/result and known redacted diff/revision/correlation; failed or
  malformed reads hide data and counts. Project History retains job history and
  adds this evidence. Retention editing lives under System status with separate
  day/text-byte limits and actual deleted-event impact.


- Admin/CSRF `/users/with-access` commits explicit role, immutable project IDs,
  account and existing secret-free audit atomically through `create_user_with_access`.
  Dev empty selection requires acknowledgement; Admin role grants global access.
  Invalid intent, stale/archived/deleted projects and storage faults leave no
  partial user/grants. Final metadata inspection detects concurrent lifecycle
  change; replacements cannot inherit ID/creation-bound grants. `/users` adds
  live `project_ids` beside compatible names. `UserCreation` owns four-locale
  memory-only identity/access/secret-free review, corrections, focus and one-submit
  guards; `AccountAccessEditor`/`ProjectAccess` review before/after and show actual
  results. Tests: `test_web_user_creation.py`, existing auth/access/RBAC and
  `web/e2e/users.spec.ts`; project choices are named checkbox rows in columns and the account editor opens
  full width below its row.

- Admin/CSRF `transfer-source/preview/check/create` create fresh stopped projects
  from strict portable files or immutable authorized source identities. Exact source
  bytes/ID and target revision are bound; source/session/ownership are rechecked
  during existing locked atomic publication. All 15 rules transfer, while target
  identity/repository/environment/references are supplied anew. Allocated state,
  worktrees and derived metrics remain independent; corrupt/overlapping ownership,
  stale sources, rollback and replay fail closed. `TransferWizard` reviews the
  selected source; optional `EnrollmentWizard` mode shows complete source/default/
  effect mapping, required reconfirmation and retained memory-only correction.
  Selected files are reread at target boundaries. Tests: `test_web_transfer.py`
  and `web/e2e/transfer.spec.ts`; exact TOML/export remain separate contracts.

- Admin-only `/projects/{name}/config/portable-settings` validates a bounded
  active snapshot through `portable-settings.md`; canonical no-store JSON and
  optional fixed attachment omit pending/identity/host/access/credential data.
  Authorization precedes lookup, invalid sources return value-free 503, and
  optional preview checksum conflicts return 409. Project ownership is rechecked
  after snapshot export; changed identity rejects. Exact TOML/CSV contracts retain
  their behavior. Portable parser/API tests remain offline.
- `GET /api/v1/projects/{name}/config/raw` is administrator-only. It returns original saved UTF-8 TOML bytes, including inline secrets, as `text/plain`, with `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. `?download=true` adds a fixed `config.toml` attachment. Authorization precedes lookup. Empty, malformed, unreadable, symlinked or oversized sources return value-free 503 `config_corrupt`; changed bytes or immutable project identity return 409 `stale_config_revision`. Reads are bounded to 524288 bytes; no environment resolution, `.env`, pending changes or mutation.
- Administrators use **Preview raw configuration** or **Download raw configuration** beside Project settings. Preview opens a closable dialog; download preserves original saved `config.toml` bytes including comments, formatting and inline secrets. Pending changes, resolved defaults, separate `.env` files and external credentials are excluded. Preview is memory-only and cleared on dismissal or project/session change. Developers retain redacted read-only settings and cannot access raw configuration. Candidate review/apply/discard remains inside Settings.


- `/api/v1/jobs-page` provides complete globally ordered authorized current and
  archived job history, optional project/search/attention/status filters and optimistic
  content revisions. `/api/v1/jobs/{project_id}/{run_id}` uses composite identity.
  `adore/web/jobs.py` strictly validates schema-1 state, saved ticket metadata and
  JSONL bytes without altering operational journal recovery. See
  `05_SoftwareDocu/Component_Web_Jobs.md` for exact fields and source semantics.

- Exact Admin/CSRF import-preview returns config/candidate revisions, structured
  local findings and allowlisted review. import-check reuses bounded probes with
  ephemeral revision/time-bound status; import confirms unchanged bytes after
  full identity/ownership/state reinspection within enrollment/conductor locks.

- `create_app(home, probe_runner=...)` mounts `/api/v1` and bundled static
  assets. The runner is injectable for explicit host-readiness and image runtime commands.
- Guided `setup-preview` returns canonical secret-free setup/paths and a digest
  binding exact deterministic config, ID, display and description. Additive
  `setup-check` returns ephemeral revision/time-bound evidence; `setup-create`
  compares the reviewed revision before existing atomic stopped publication.
  All require Admin/CSRF. Setup includes supported labels, run limits and credential
  environment names. Gitea probes honor the selected tea login.
- `EnrollmentWizard` owns five-step memory state (starting at repository/identity), localized visible guidance,
  corrective findings/focus, generation invalidation, loss guards and frozen review.
  The immediate creation ref lock prevents double submit. Completion explains
  stopped pickup and separate activation; persistent project readiness is checked
  separately. `enrollmentCopy.ts` preserves EN/FR/DE/RO and existing themes/branding.
- `adore-web --home ...` binds loopback; remote traffic uses a TLS proxy.
  Uvicorn accepts forwarded context only from loopback proxy peers, and HTTPS
  login emits a Secure session cookie.
- `adore-web-worker --home ...` polls profiles and queued operations.
- `WebStore(home / "web.db")` owns accounts, sessions, grants, audit and queue.
- `02_Tools/package_web_offline.py` creates a host-matched delivery directory;
  `install_web_offline.py` installs from local wheels only.

## Invariants

- Global job reads authorize selected profiles before state IO and recheck
  grants/profile metadata after complete source validation. Failed authorized
  reads return typed errors without partial totals. Source revisions reject
  changed continuations; ordering uses UTC activity then composite identity.
  Actual persisted questions/comment/candidate/MR references support actions;
  missing titles, timestamps, named responsibility and usage stay unknown.
  Strict links and selected redacted fields protect source secrets; reads
  execute no external commands and write no state.

- Web enrollment publishes metadata only after config and stopped pickup, under
  enrollment/conductor locks; failure removes visibility before rollback/unlock.
  Existing completed server history is retained at its declared state location. Display edits preserve all operational identity.
- Local setup preview and ID availability never probe tools or publish profiles.
  Findings carry safe code/field/remediation; exact backend detail codes appear
  under existing localized HTTP error categories. Secret literals fail closed.
- Read models distinguish structural validation, pickup and explicit verification.
  Profile-owned readiness.json validates identity/digest/UTC time/schema/redacted
  checks; absent evidence is unverified and changed config is stale. Mid-probe
  config changes cannot publish current evidence. See Component_Web_API.md.

- `DashboardShell` renders authorized semantic links, approved transparent
  DDP Engineering branding at its original aspect ratio on dark navigation,
  a skip link and visible keyboard focus. Main views are Overview, Projects,
  Jobs and Statistics; stable URL paths remain owned by `routes.ts`.
- `Presentation` supplies localized text/icon statuses, delivery definitions,
  distinct pending/error feedback and role-specific empty project guidance.
  Essential field instructions remain visible and associated with controls.
- App keys data by project/filter and guards completions by request/session
  identity. Numeric totals render from successful reads; failed reads hide
  stale totals until the next automatic update. Closing a job clears its
  URL identity. Jobs/Overview default to complete all-authorized current/archived
  history or an explicit selected project. JobWorkspace guards render keys and
  composite detail identity; changed continuations hide totals/detail and require
  explicit restart. Validated jobModel checks safe links, counts/groups and stages.

- Fresh identity stores bootstrap `admin` / `admin` once with an Argon2id hash.
  A corrupt or deleted initialized store does not recreate the default login.
- Accounts store optional language and theme. Authenticated
  preference reads and CSRF-protected partial updates remain account-scoped;
  null values use the browser fallback and corrupt rows fail closed.
- Developer routes check membership before reading a project and omit all
  financial fields. Project configuration reads return redacted effective
  settings to assigned developers, with per-setting source, editability (the
  same rule as edits), declared type/domain/default and restart metadata.
  Dev reads omit the financial cap; credential-bearing URLs are redacted before
  row/default/review generation. Other project identities return
  404.
  Configuration mutations, account management and global metrics require admin.
- Grants, rates and queued operations are bound to immutable profile IDs.
  Renames retain grants and queued targets, while a reused name cannot inherit
  either. The web store has one schema (15); a database in another version is
  refused with a message naming `web.db` and `web.db.initialized` to delete,
  never migrated (AGENTS.md "Stored data during development").
- Mutations require CSRF; sessions are opaque, expiring and revocable.
- Administrator password reset revokes target sessions and sets the reset
  marker; until the account changes its own password, only `/me`,
  `/me/preferences`, `/me/password` and sign-out answer, and other
  authenticated routes return 403 `password_change_required`. The bootstrap
  `admin` starts unmarked.
- Every API error body is `{"detail": {"code", "message"?, "issues"?}}` with a stable
  snake_case code; store sentences map to fixed codes, unknown text becomes
  `request_rejected`, validation is 422 `invalid_request`, and unknown
  `/api/...` paths return 404 `not_found`. `web/src/errors.ts` holds an
  EN/FR/DE/RO sentence for every code `app.py` can emit.
- Config reads omit
  credential-looking fields; journal views use a role-aware field allowlist.
  The same name rule (`_is_secret_key` in `adore/cli.py`) also refuses web edits
  and CLI `config set`; ADORE's own boolean `metrics.capture_tokens` is exempt
  while its value is a boolean (`REQ-SEC-63767e17`).
- Web config edits use a SHA-256 revision and the same per-directory process
  lock as CLI `config set`; direct host file changes do not use that lock.
  Staged, applied and direct edits write bytes and keep the
  file's CR LF or LF line endings (`REQ-PLAT-722173c8`).
- The administrator UI prepares one validated config candidate per project,
  reviews changed safe values above categories with adjacent Apply/Discard; complete comparison, effect, observed time and full base/candidate revisions are disclosed in Technical details and applies it only with no active run, conductor or
  queued operation. Identity/runtime edits require paused pickup. Retrying an
  interrupted apply reconciles exact candidate bytes and profile labels.
- Explicit administrator readiness checks use bounded doctor probes from the
  API host and persist typed revision/time-bound evidence. AEGIS file presence is checked without
  executing repository code. The stored checks are exactly `git`, `forge_cli`,
  `forge_auth`, `container_runtime`, `executor_cli` and `aegis_files`; model
  access is proved only by the explicit Test AI connection. WSL runtime
  detection remains unverified; CLI output and credentials are never returned.
- Provider/model/endpoint, launch command and credential-name edits use the
  reviewed candidate flow in Settings → Agent and model
  (executor-configuration.md). Provider, model and the OpenAI-compatible
  endpoint are one virtual candidate key, `executor.connection` (strict JSON
  `{provider, model, base_url, api}`), edited by `AgentConnectionEditor.tsx`;
  the rows `executor.provider`, `executor.model`, `executor.endpoint.base_url`
  and `executor.endpoint.api` report that `edit_key` and cannot be staged
  individually (400 `setting_not_editable`). `PendingReview` shows the
  candidate as four rows (Provider, Model, Endpoint base URL, Endpoint API
  type); `settings.ts` input kind `connection`, `connectionRowVisible` hides
  the endpoint rows unless the provider is `custom`.
- `GET /api/v1/pi-providers` (any signed-in user; 503
  `provider_catalog_unavailable` when the shipped catalog is unreadable)
  returns `{pi_version, providers[{id, name, variable, models}], chatgpt:{id},
  custom:{id, variable, apis}}`; `agentConnection.ts` reads it
  (`readProviderCatalog`) for the provider select and the model datalist.
- Project creation offers no coding-agent choice: Pi is the only agent, and
  `ProjectInput` has no `executor_cli` field (422 when sent). `auth_mode` is
  `api-key` or `existing` (the local account's own Pi sign-in, with empty
  `env_keys`); any other value, such as `host-auth`, is 422. A container project
  uses api-key. `ProjectInput` takes `provider`, `model`, `endpoint_base_url`
  and `endpoint_api` (endpoint only for `custom`) and no secret; the setup
  preview review returns `provider`, `model`, `endpoint_base_url`,
  `endpoint_api` and `credential_variable` (the variable to save after
  creation). The project view reports `executor` = `pi`, and import review
  shows `executor` = {provider, model, endpoint_base_url (empty unless custom), env_keys}.
- Web-created profiles use an absolute, project-specific worktree root under
  ADORE home. ADORE uses the configured agent identity for host-side checkpoint
  commits, even when the fresh clone has no local Git identity.
- The audit trail is available only on the administrator API and page.
- JobWorkspace reads `/jobs-page` for complete authorized attention/jobs/history
  and composite `/jobs/{project_id}/{run_id}` for detail. Overview leads with
  human-action/failure/handoff attention and actual working/publishing rows in
  compact title/project/ticket, status and Details tables. App supplies one header
  Project selector through DashboardShell's optional controls slot, before selected
  context and tables. Primary Overview href/action defaults all authorized projects;
  explicit scoped reload/Back retain URL identity. Visible15s background polling
  retains validated same-scope rows while pending and clears them on failed reads;
  the header Refresh and stamp appear only on non-polled pages (Users, Change history,
  project Settings/Access/History). Strict complete active reads and scope/render guards withhold
  invalid data; Overview performs no usage reads. Worker faults are visible and
  Details opens the existing composite Jobs route; browser-local dates and
  reporting/technical evidence belong to dedicated views.
  Jobs keeps search/project/status group visible and advanced exact filters
  disclosed. Ten-row server pages carry source revisions on continuation.
  Detail leads with lifecycle, actual stage, reason, role/location and conditional
  following action. Missing names/duration/consumption remain unknown. Old saved
  activity and the separately polled control-worker heartbeat express different
  evidence. Timeline contains only redacted saved events, locally reverse-paged
  at 10/25/50/All without inferring unvisited stages.
- Global Jobs mirrors the hub: compact project selector and Tickets/Jobs sub-tabs
  (`view=jobs`); All projects Tickets reads every active project into one table with
  a Project column and per-project errors; manual start goes through Tickets Start. Retry/cancel mirror conservative existing lifecycle guards, excluding
  pending/completed handoff cancellation. A ref lock prevents repeated submission;
  the existing queue is polled for pending/running/succeeded/failed/uncertain.
  Unreadable status leaves completion unknown; server/worker authority remains
  decisive. Scope changes discard ticket drafts and superseded command results.
- Projects show display labels, independent pickup and explicit revision/time-bound
  verification, counts/activity and scoped actions. Summary includes the same
  evidence; Jobs and Statistics are hub tabs; Settings stays read-only for Dev, Access is
  Admin-only, and History selects terminal jobs. Legacy configuration, executor
  and prices routes open Settings. Every save stamps a run's created_at and
  updated_at; a project summary over a run whose updated_at is empty or corrupt
  fails closed with 503 `run_state_corrupt`.
  Enroll new project (and Clone project config) start from a repository URL: Read
  repository (`/api/v1/projects/repository-source`, `adore/web/repository_source.py`)
  fills forge, repository, login, branch and the derived ID and prefills an editable
  clone path `<home>/repos/<ID>`; Continue waits for a successful read; the clone is
  made only at creation (exclusive folder, reused if its origin matches, removed on failure);
  no existing-clone mode (a matching clone at the path is reused); no Stable project ID field;
  reviewers are optional (empty list = no review request) in the wizard and Settings.
  Projects offers Enroll new project, Import project config and Clone project config
  as separate pages (/projects/new, /projects/import, /projects/clone).
  Administrators open Enroll new project as a five-step guided page with visible localized
  instructions. Clone paths identify existing Git clones on the ADORE host;
  step 2 asks Provider, Model (with Pi's models as a datalist) and, for an
  OpenAI-compatible endpoint, Endpoint base URL and Endpoint API type, and names
  the credential variable to save after creation; review lists them plus
  "Credential to save after creation"; environment setup is external. Back retains
  the memory draft, Cancel warns about loss, and completion confirms stopped pickup
  before the explicit Open project action.
  Exact configuration enrollment mounts ImportWizard with four-locale visible file
  source, unchanged-copy and server-history guidance. Six ordered steps show all
  consequential locations and recognized settings; internal Back/Change retains
  memory drafts and invalidates old checks/review. File requests reread fatal UTF-8
  bytes, changed disk files fail closed, leaving warns and unmount clears drafts.
  Frozen confirmation uses a ref lock; failures preserve corrections and success
  confirms stopped pickup with a separate Open project action.
  Pending and completed human handoffs have localized lifecycle labels and
  filters. Cancel is unavailable during and after human ownership transfer.
- The React session switch clears private caches and increments a generation
  guard so in-flight responses from the previous account are ignored.
- Project daily CSV exports follow the same financial filter as metrics JSON;
  the global daily CSV is administrator-only and includes project/repository
  provenance with spreadsheet-safe repository labels.
- Shared analytical scope and contracts:

Reporting scope is the authorized immutable project set, a half-open UTC
instant interval `[from,to)`, the reporting IANA timezone (UTC unless the URL
supplies one; there is no time zone control) and day/week/month
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
source and coverage. Summaries survive runtime-state removal; positive
summary-only measurements (a run known only from metrics.db, for example a
deleted one) belong to lifetime/unallocated, never a fabricated period.
Missing individual token fields stay null; explicit measured zero stays zero.
Every usage event carries its versioned event ID and current fields; a naive,
date-only or unparseable usage timestamp is `metrics_corrupt`, and a summary
table with missing or extra columns fails closed (503). Financial fields and financial coverage are Admin-only in every nested
projection and export. Reported and estimated costs remain separate; matching
immutable prices use the consumption UTC day, and never price reported money
again. Coverage identifies partial evidence rather than asserting a full bill.

Review cohorts use first MR opening/adoption in scope; validation cohorts use
first strict verdict in scope. Human merge uses reviewed jobs with actual done
in scope and `merged by human`. Rework requires reviewer-requested revision;
pipeline repair is separate. Each rate exposes numerator/denominator; empty is
null. Review still open counts reviews open now, independent of the period. Monetary efficiency uses only
period consumption for the completed/human-merged cohort and separate known
reported/estimated samples.

Duration is terminal-summary elapsed wall time including waits, selected by
recorded end instant in scope. Count, sum and sorted exact `samples_seconds`
support pooled mean/median without browser date approximation. Recorded zero
is valid; absent pairs are excluded and inconsistent pairs fail.

Raw state/JSONL and read-only summary rows are validated before filters.
Malformed JSON, duplicate keys, unsupported schema, invalid fields, conflicting
versioned identity/timestamp, numeric overflow and invalid versioned timestamps
fail typed 503 without source rewriting. Invalid scope/identity filters return
422. Analytical summary reads neither initialize nor migrate runtime data.
CSV includes scope/project provenance, empty unavailable cells and spreadsheet
escaping; `X-ADORE-Scope`/`X-ADORE-Coverage` describe empty exports too.
Project `/api/v1/projects/{name}/jobs-usage.csv` and Admin global
`/api/v1/jobs-usage.csv` share usage date/timezone/group/executor/model filters.

The browser validates scoped metrics/usage before presenting evidence. Captured
project/date/timezone/group and authorized-project keys suppress stale reads;
metric and usage canonical scopes must agree before cards or CSV links appear.
Summary shows only measure cards (lifecycle events, measured zero, unavailable and
partial token subtotals, reported/estimated money); job elapsed time is in Usage
and per-job consumption only in Jobs. Server buckets feed one Trends table whose
count cells carry bars, in all four locales/themes; Admin unpriced events are a
Usage total and estimated cost per project is in the All projects Usage table.
Composite job consumption exposes lifetime, selected-period and unallocated amounts;
Jobs/detail show lifetime only (one all-time read per visible project) and the Jobs
table sorts on the server (`jobs-page` sort/order). Statistics deep links retain selection.

Offline proof: `test_web_scoped_metrics.py`, `test_web_metrics.py`,
`test_web_pricing.py`, and `web/tests/metrics.test.mjs`, followed by native
Python/Ruff and frontend validation. CLI summary/export semantics are preserved.

- SQLite usage and launch-coverage projections are reconciled against retained journals
  before attributed reads; usage projection source IDs are the usage event IDs. An administrator can explicitly replay archived and
  current projects; a per-run cursor prevents repeated events adding rows, and changed or vanished
  source evidence fails closed without changing run state.
- Administrators add immutable effective-dated rates for exact
  project/executor/model combinations; estimates apply only to usage events
  without reported cost and remain separate from reported totals.
- Worker authorization is rechecked after queueing. Interrupted operations
  become `uncertain`, never blindly replayed.
  A queued Cancel is rejected if the run became human-owned before execution.
- During every blocking worker command or project poll, a watcher rechecks
  pending cancel grants across projects and
  writes a per-run marker. The conductor interrupts the matching working gate
  and performs normal teardown; a revoked grant creates no marker.
- Selected-ticket starts retain the conductor's readiness and approval gates.
  The web layer never merges.
- Stopped pickup refuses a ticket Start with 409 `ticket_not_startable`
  (`pickup_paused`) right after the idempotency replay and before any forge
  call; the ticket view reports `blocked_by: pickup_paused` with nothing to add
  and unchanged eligibility (REQ-FUNC-4e5e56ed, REQ-FUNC-ef5a60d0).
- The worker runs the CLI with stderr joined to stdout (`CommandOutcome`; a
  runner may still return a bare exit code). A non-zero exit or timeout keeps a
  `detail` tail from `util.output_tail` with `jobs.redact_text` (redacted before
  the 20-line/2000-character cut), and a refused start keeps the CLI's
  not-started code for its own ticket as `reason` (REQ-FUNC-fbb6448c,
  REQ-FUNC-6055f2c6). Both stay on the operation row (schema 15), never in audit
  evidence. The UI localizes `reason` through `operationReason.ts` in Tickets,
  Jobs and the project status, names a refused Start's kept labels only for a
  failure with a known reason, and opens Start/Stop confirmations as a row under their
  ticket (REQ-UX-3cafa0cc, REQ-UX-5fb31254, REQ-UX-21f0f5a5, REQ-UX-61a21b3d,
  REQ-UX-c18f6fec).
- Offline installation verifies the manifest and runs `pip --no-index`.
- About exposes bundled project license text and versioned third-party notices.
- Below 760px, primary navigation opens from a labeled collapsible menu and
  closes after page selection. Narrow panels wrap text while data tables keep
  their own horizontal scrolling.

One web worker owns command ordering for one home. During any blocking engine
command or project poll, the worker watches queued cancellations across projects and
signals the active conductor after rechecking grants. Other queued operations
wait for the current engine command. Administrator metrics attribute usage and
reported/estimated cost to the most recent revision-started event in each run;
initial work remains in run totals and developers receive no financial rows.
API liveness at `/api/v1/health` is separate from readiness at `/api/v1/ready`.
The worker refreshes a schema-5 SQLite heartbeat even while an engine command
blocks; a stopped, stale or corrupt heartbeat does not claim readiness.
Administration expands into System status, Users and Change history sidebar pages;
both roles reach a top-level My account page. Every view has a path URL
(`web/src/routes.ts`) kept in sync with view state; project details uses
Summary/Settings/Access/Jobs/Statistics/History tabs (`/projects/<id>/jobs?run=`, `/projects/<id>/statistics?tab=&from=`). Project details shows effective
configuration in six purpose categories plus closed Technical details with frequent settings first within each,
with a Default badge for inherited values, field type, domain and permanent purpose guidance; administrators edit settings on their rows and stage
changes there. The Agent and model group also holds the Admin-only estimated-price form, which asks for the
effective date and input/output rates and records them for Pi and the applied model in `executor.model`
(guidance replaces the form while no model is set), and the project's price table. The
settings response is scoped to the current project identity so switching
projects cannot briefly show another project's values. Audit policy defaults to unlimited
and its System status form displays saved day/MiB limits, representing unlimited as zero.
Zero or blank maps to API null; bounded values convert to integer days/bytes
through `04_Software/web/src/auditPolicy.ts`, covered by offline Node tests.
Administrators can set day and stored-text byte limits. The store validates
closed evidence and prunes oldest visible events with structured JSON included
in bytes. SQLite mutations and evidence
share transactions. Filesystem mutations start uncertain and confirm after
completion; pending config replay preserves original before and finalizes once.
Separate receipts keep deduplication after audit retention removes visible rows;
completed receipts clear value payloads. Interrupted commands remain uncertain,
malformed exit codes cannot claim success and terminal replay creates no event.
`audit.py` excludes nested credentials/environment/raw errors/arbitrary metadata.
Browser-local correction/abandonment is not a persisted server mutation.
Audit and other long tables provide 10/25/50/All paging; Jobs uses
the complete revision-bound global API for the same choices. API fetches bypass browser cache
so a newly deployed endpoint cannot be masked by stale HTML.
The Administration System status page polls readiness every five seconds and labels worker
status separately from forge, executor and model reachability.
It also polls administrator-only storage status every 30 seconds. The API reads
free space for home and each project state root with a `volume_id` (the UI groups
one line per physical volume), warns below 1 GiB and returns
an explicit service error if measurement fails, without exposing host paths.
The React About dialog makes the surrounding shell inert, keeps keyboard focus
on its Close button, and restores focus to About when closed. Narrow layouts
expose Sign out in the top bar while the sidebar account row is hidden.
The top bar supplies the sole page title and common actions on every page.
Project details keeps the identity opened through authorized Projects rows.
Its metadata rows use 4px gaps and 18px separation before actions. Platform
administration/account pages use their own controls. Responsive rows
keep these controls visible while content begins with page data. Metric hints,
usage actions and account rows wrap on narrow screens.
Statistics keeps its authorized project selector with the common reporting range,
grouping, All time and CSV menu in one row above keyboard-operable Summary, Usage, Quality,
Trends tabs (old ?tab=projects links land on Summary). Administrators use All projects
scope for pooled totals and one per-project table per family in Summary, Usage and Quality.
Every category and CSV menu follows that scope; single-project mode limits
comparison rows and developer mode exposes assigned-project operational data.
Summary includes a paginated project breakdown in All projects scope.
`04_Software/web/src/metrics.ts` pools counters, nullable evidence, quality cohorts and
terminal duration samples; `04_Software/web/tests/metrics.test.mjs` verifies it offline.
Developer export choices remain project-scoped and omit money. The Usage tab
has no executor/model filters (the API parameters remain); its table sorts by
column and its totals row includes job elapsed time. Compact layouts put
the shared reporting controls in two rows.
Session clearing also returns the shell to Overview, preventing a blank
administrator-only page after a developer signs in. Successful asynchronous
config staging resets its form without a false error; UserCreation clears its
transient credentials after confirmed creation.
A signed-in account with a pending required password change is held outside
the shell session, so only the change-password card renders and no dashboard
polling starts. The error banner stores the raw failure; `web/src/errors.ts`
renders it in the active locale, and each user action or view change clears
it. `web/src/projectName.ts` supplies the `v`-flag-safe project-name pattern
for Add and Import project. Primary buttons take their text colour from the
`--on-accent` theme token.

## Change map

| Change requested | Start with | Focused verification |
|---|---|---|
| Atomic reviewed accounts and access edits | `UserCreation.tsx`, `userCopy.ts`, `create_user_with_access`, `/users/with-access` | `test_web_user_creation.py`, auth/access/RBAC suites, `web/e2e/users.spec.ts` |
| Authorized global job evidence, paging, revisions | `adore/web/jobs.py`, `jobs_page` and `job_detail` in `app.py` | `test_web_jobs.py`, `test_web_paging.py`, `test_web_rbac.py` |
| Portable new-project file/copy, mapping and source revision | `TransferWizard.tsx`, `EnrollmentWizard.tsx`, `_prepare_transfer`, `transfer_source` | `test_web_transfer.py`, `web/e2e/transfer.spec.ts` |
| Enrollment, display identity, readiness evidence | `adore/profiles.py`, `adore/wizard.py`, `adore/web/app.py` | `test_web_enrollment.py`, `test_web_errors.py` |
| Exact TOML enrollment, safe review and probe | `web/src/ImportWizard.tsx`, `importCopy.ts`, `_inspect_project_import` | `test_web_import.py`, `web/e2e/import.spec.ts` |
| Guided enrollment steps, correction, draft loss and review | `web/src/EnrollmentWizard.tsx`, `web/src/enrollmentCopy.ts`, `App.tsx` | `web/e2e/enrollment.spec.ts` |
| Accounts, sessions, queue | `adore/web/store.py` | `test_web_auth.py`, `test_web_commands.py` |
| Statistics evidence, selection, exports and job consumption | `web/src/statistics.ts`, `StatisticsEvidence.tsx`, `App.tsx`, `JobWorkspace.tsx` | `web/tests/statistics.test.mjs`, `web/e2e/statistics.spec.ts` |
| API permissions/config/metrics | `adore/web/app.py` | `test_web_rbac.py`, `test_web_config.py`, `test_web_pending_config.py`, `test_web_readiness.py`, `test_web_metrics.py` |
| Worker execution | `adore/web/commands.py` | `test_web_commands.py` |
| Action workspace, next action and observed history | `web/src/JobWorkspace.tsx`, `jobModel.ts`, `jobCopy.ts` | `web/tests/jobs.test.mjs`, `web/e2e/jobs.spec.ts`, `test_web_jobs.py` |
| Language, theme, views | `web/src/App.tsx`, `web/src/i18n.ts` | `npm run validate`, isolated Chromium journeys |
| Shell, branding, scope, request feedback | `web/src/DashboardShell.tsx`, `web/src/Presentation.tsx`, `web/src/App.tsx` | `web/e2e/shell.spec.ts`, `web/tests/shell.test.mjs` |
| URLs, tabs, navigation | `web/src/routes.ts`, `web/src/App.tsx` | `npm test` (`routes.test.mjs`), browser check |
| Background refresh and paging | `web/src/polling.ts`, `JobWorkspace`, `ServerPager` in `App.tsx`, `/api/v1/audit-page` | `npm test` (`polling.test.mjs`), `test_web_paging.py` |
| Error codes and messages | `adore/web/app.py` (`_error`, `_STORE_ERROR_CODES`), `web/src/errors.ts` | `test_web_errors.py`, `npm test` (`errors.test.mjs`) |
| Project developer access | `/api/v1/projects/{name}/access` routes in `adore/web/app.py`, `project_members` and `set_membership` in `adore/web/store.py`, `ProjectAccess` in `App.tsx`, `web/src/routes.ts` | `test_web_project_access.py`, `npm test` (`routes.test.mjs`), browser check |
| Project settings list and row editing | `_setting_metadata` in `adore/web/app.py`, `web/src/settings.ts`, `SettingsList` in `App.tsx` | `test_web_config.py`, `npm test` (`settings.test.mjs`), browser check |
| Setting help texts and catalog | `web/src/settingHelp.ts`, `web/src/settingKeys.json`, `default_config()` in `adore/config.py` | `test_web_setting_catalog.py`, `npm test` (`settingHelp.test.mjs`), browser check |
| Offline media | `02_Tools/*web*.py` | `test_web_package.py`, installed HTTP smoke |

## Key behaviors

- REQ-UX-b75e1df8: ProjectInput accepts execution_backend and local account/home/path/cgroup/native argv. Review/config show actual machine/account/system; metadata reports runtime=local. Reviewed candidates recheck pinned native plans. Host checks avoid container detection.

Native control/auth route to local-execution.md. Focused proof:
`04_Software/tests/test_local_execution.py`.


- `REQ-UX-94a97e70`: CLI validates external execution selections and previews complete image/source/commands. Web reads expose effective image and retained preparation evidence; environment mutations are refused. Host/model probes normalize image without setup; jobs project validated timestamp/exit/timeout/cancel evidence. Portable rule allowlists stay unchanged.

- `REQ-DATA-5a620f4e` / `REQ-REL-6564a3b2` / `REQ-FUNC-83da8d95` - composite measured job consumption, strict sources and server-selected analytical samples.


- `REQ-FUNC-20010f79`, `REQ-SEC-934b2dca`, `REQ-UX-7d0b71c3`: isolated stopped portable enrollment, exact authorized source binding and explanatory mapping/reconfirmation.

- `REQ-SEC-f96d80d4`: authoritative portable transfer API with no enrollment writes.
- `REQ-UX-34ca5d39` / `REQ-SEC-3cf6cde4`: compact Settings and Admin original TOML reads, memory-only preview and exact download.

- `REQ-UX-b758d2b7`, `REQ-UX-78923e00`, `REQ-UX-a7969a9d`,
  `REQ-FUNC-25dc0271` â€” complete authorized action workspace, pickup/verification
  project hubs, observed safe timeline and actual queued outcomes.


- `REQ-FUNC-e8455ab6`, `REQ-DATA-0ba9e469`, `REQ-SEC-5d0f86e7` â€” complete
  authorized job pages, actual persisted evidence/unknowns and strict trusted sources.

- `REQ-UX-3b5b2257`, `REQ-FUNC-c987bc4a`, `REQ-REL-39c1b197`, `REQ-DATA-71853fbc` - explanatory exact enrollment, explicit ephemeral checks, locked candidate publication and memory correction/loss guards.

- `REQ-UX-072cf049`, `REQ-UX-3609c9ed`, `REQ-UX-002cbd25`, `REQ-UX-7f8fde2c` - guided supported steps, memory correction/loss protection, field focus and stopped completion.
- `REQ-FUNC-702b0fce`, `REQ-FUNC-49e89542`, `REQ-DATA-e1eaf583`, `REQ-SEC-dc4bd0c3` - complete canonical preview, explicit ephemeral probe, exact guarded creation and reference-only Admin/CSRF draft boundaries.

- `REQ-DATA-d893df33`, `REQ-FUNC-e8e0e304` - stable display identity and portable advisory ID checks.
- `REQ-REL-c598b075`, `REQ-FUNC-3d8f6f5e` - metadata-last stopped enrollment and offline findings.
- `REQ-DATA-70e5e3bb`, `REQ-SEC-61fb8552` - revision-bound evidence and guarded secret-free setup.

- `REQ-UX-955615bd` / `REQ-UX-aa5e358e` - authorized accessible shell and approved branding.
- `REQ-UX-8031b8eb` / `REQ-UX-0713852d` - localized delivery vocabulary and explicit project context.
- `REQ-UX-257ab3f0` / `REQ-UX-9a8b409d` - scoped request feedback and role-specific empty access guidance.

- `REQ-SEC-9ee171c9` - local accounts and durable, fail-closed sessions.
- `REQ-SEC-59d97c68` - project scope and developer financial privacy.
- `REQ-FUNC-7ce5b17a` - project setup, config and status.
- `REQ-FUNC-f9946b6b` - durable selected-ticket operations and admin pickup.
- `REQ-FUNC-448cbde7` - observed usage, reported/estimated costs and coverage.
- `REQ-UX-749d37c8` - four locales, themes and responsive UI.
- `REQ-SEC-676d284c` / `REQ-UX-309a6b3f` - administrator reset requires a new
  password; the browser shows only the change-password card meanwhile.
- `REQ-FUNC-9c1f728e` / `REQ-UX-e6ed7168` - stable API error codes and their
  localized banner text.
- `REQ-UX-359f8cbf` - browser-side project-name validation.
- `REQ-UX-94dc4e69` - error banners reflect only the latest user action.
- `REQ-UX-4200375b` - every view has a stable path URL with history support.
- `REQ-UX-d88d3d7f` - project details tabs and project links.
- `REQ-UX-3dda4965` / `REQ-UX-02f35869` - example placeholders, required
  markers and the stated password rule.
- `REQ-UX-5b0fa167` / `REQ-UX-48d6a55d` - phone table scroll cue and Jobs
  filter toggle.
- `REQ-SEC-a514d0b2` / `REQ-UX-772cb418` / `REQ-FUNC-bcaf01be` - delete
  an archived, idle project after typed-name confirmation; the worker runs the
  resource-removing CLI delete and human-owned worktrees are kept.
- `REQ-UX-205e5379` / `REQ-UX-deb101f5` / `REQ-UX-48fb199d` /
  `REQ-UX-0c03fc93` / `REQ-UX-d93fab0f` / `REQ-UX-7fdffe77` - name and ticket
  links, scoped card hints, SVG icons, heading spacing, project-executor price
  default and the empty-metrics message.
- `REQ-NFR-da638732` / `REQ-NFR-46c98d6c` / `REQ-FUNC-a83c4cd3` - no polling
  while hidden and server-paged Audit/Overview tables.
- `REQ-UX-2bea4ff1` / `REQ-UX-84025a2c` - purpose categories, visible setting
  guidance, catalog control domains and exact single-candidate safe review, with
  explicit apply/discard, recorded evidence fallbacks and scoped request guards.
- `REQ-UX-66e6f3f5` - project details presents collapsible, guided settings with administrator editing.
- `REQ-FUNC-49b766fe` / `REQ-UX-9a625fc5` / `REQ-UX-a62e69a9` - per-setting source, editability and
  restart metadata; Default badges for inherited values, row editing and permanent per-row descriptions.
- `REQ-UX-b0e9a434` / `REQ-FUNC-c6c71dbd` - every setting's help text in EN/FR/DE/RO and
  its ADORE default; the catalog test keeps texts in step with the configuration keys.
- `REQ-SEC-3ce206e4` / `REQ-UX-7ca5687c` - administrators grant or remove one developer's access to one
  project from its Access tab; other grants stay; developers see no tab.
- `REQ-SEC-c2298428` - redacted project configuration reads follow grants; edits remain administrator-only.
- `REQ-PLAT-a1b60ff9` - host-specific offline installation.
- `REQ-REL-94e653aa` - checkpoint-bearing state and handoff lifecycles are
  loaded and protected.

## Files

- `04_Software/adore/web/implementation_settings.py`: strict retry/map domain and semantic single-setting TOML writer.
- `04_Software/web/src/implementationSettings.ts`: typed Implementation drafts and localized editor terminology.

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


- `adore/web/audit.py`, `web/src/AuditHistory.tsx`, `auditCopy.ts`,
  `tests/test_web_audit_evidence.py` and `web/e2e/audit.spec.ts` own closed structured
  evidence, authorized reads and browser proof with storage/API/worker integration.

- `web/src/UserCreation.tsx`, `userCopy.ts`, `web/e2e/users.spec.ts` and
  `tests/test_web_user_creation.py` own reviewed accounts/access and negative proof.

- `04_Software/web/src/statistics.ts` - strict analytical scope/amount/job boundary.
- `04_Software/web/src/StatisticsEvidence.tsx` - honest measures, consumption and trends.
- `04_Software/web/src/statisticsCopy.ts` - EN/FR/DE/RO measurement definitions.
- `04_Software/web/tests/statistics.test.mjs` and `web/e2e/statistics.spec.ts` -
  deterministic analytical values, stale/grant/export/mobile and locale proof.

- `web/src/TransferWizard.tsx`, `transferCopy.ts`, optional `EnrollmentWizard` transfer mode and `tests/test_web_transfer.py`, `web/e2e/transfer.spec.ts` own portable new-project enrollment.

- `04_Software/web/src/JobWorkspace.tsx` â€” scoped attention/jobs/detail, observed
  paging and queued command feedback; `jobModel.ts` validates transport evidence,
  `jobCopy.ts` localizes conditional actions.
- `04_Software/web/tests/jobs.test.mjs`, `04_Software/web/e2e/jobs.spec.ts` â€” public
  evidence/route boundaries and offline real API/worker/browser journeys.


- `04_Software/adore/web/jobs.py`
- `04_Software/tests/test_web_jobs.py`
- `05_SoftwareDocu/Component_Web_Jobs.md`

- `04_Software/web/src/ImportWizard.tsx`, `importCopy.ts` and `web/e2e/import.spec.ts` - exact enrollment flow, localized guidance and offline browser boundaries.

- `04_Software/web/src/EnrollmentWizard.tsx` and `enrollmentCopy.ts` - memory-only
  guided setup and supported locale copy; `web/e2e/enrollment.spec.ts` - real API
  offline success/failure/roles/draft/focus/locales/390px journeys.

- `04_Software/adore/web/{app,store,commands,server}.py` - API, SQLite store,
  worker and listener.
- `04_Software/adore/web/static/` - bundled local UI and license.
- `04_Software/web/src/{DashboardShell,Presentation}.tsx` - shared authenticated
  frame and localized request/status/header help glossary presentation; approved logo in `src/assets/`.
- `04_Software/web/e2e/shell.spec.ts` - offline role, scope, error, branding and responsive journeys.
- `04_Software/web/` - React source and build configuration;
  `web/src/errors.ts` (error localization), `web/src/projectName.ts`
  (shared name pattern), `web/src/routes.ts` (URL scheme) and
  `web/src/polling.ts` (visibility-aware refresh) and `web/src/settings.ts`
  (configuration rows and grouping) and `web/src/settingHelp.ts` (per-setting
  help texts for the `web/src/settingKeys.json` catalog) are pure modules tested by
  `web/tests/*.test.mjs`.
- `02_Tools/{package_web_offline,install_web_offline,launch_web,stamp_web_assets}.py`
  - offline media and static asset preparation.
- `04_Software/tests/test_web_*.py` - focused API, pricing, worker and packaging tests.

### Settings edit and review seam

Start at `App.tsx` SettingsList/PendingReview and `settings.ts` for grouped controls
and strict transport; `settingsCopy.ts` and the existing settingHelp catalog supply
four-locale guidance. Server `_setting_metadata`, `_public_pending_config` and
pending routes own safe domains and candidate values; the browser supplies both
reviewed revisions. Focused proof: `tests/test_web_pending_config.py`,
`tests/test_web_config.py`, `web/tests/settings.test.mjs`, `web/e2e/settings.spec.ts`.
Malformed reads disable actions; ref locking and captured session/view/request
identity prevent duplicate or stale completion. The existing configuration/conductor
locks remain the final authority for every apply.

Restored endpoint CA paths are revalidated before review/apply against the same HTTPS, absolute executor path, bounded length and no traversal/control-character domain as preparation; malformed paths return `pending_config_corrupt`.

Discard focus restoration runs in a post-render effect after the mutation busy guard clears, with the original captured scope checked before focusing the enabled edit control.

- `04_Software/adore/web/analytics.py` - shared scope, strict sources and analytical reports.
- `04_Software/tests/test_web_scoped_metrics.py` - scoped analytical boundary proof.

Persisted audit project names reject unsafe names with a redacted typed storage error on initialization and public reads; empty names preserve global scope. Every audit write carries structured evidence; a row without it is corrupt, and so is an operation without a project ID.


Project Summary uses two panels beneath the shared project header. The first
shows separated label/value tiles for Container type, Executor, Monitoring,
environment verification and actual scoped Active jobs, Waiting, Draft review
and Failed jobs counts. Unavailable/corrupt job evidence shows unknown counts
and withholds job rows. The second groups compact Needs attention and Active
jobs tables; Details opens the full scoped job view. Usage/reporting belongs
to Jobs/Statistics. Worker faults stay visible.
Administrator monitoring/archive/restore/delete and Check host prerequisites
buttons live in the information panel. Explicit host-check results appear there.
`ReadinessEvidence.tsx` owns four-locale explanatory rows; `readiness.ts` owns
scoped response validation and performed-check classification. Focused proof is
`web/tests/readiness.test.mjs` and `web/e2e/jobs.spec.ts` readiness journeys.
Explicit host checks retain internally validated check time and configuration revision.
Check host prerequisites opens the details panel immediately and shows Checking while the request runs. Duplicate checks are blocked. Results or localized failure guidance appear inside the panel; Close details hides it without cancelling a running check, and completion respects the closed state. The check button exposes the disclosure state and regains focus on close. Project/account/page changes discard stale responses; project-tab navigation retains current evidence. Model/executor
access evidence appears only inside these details on Summary. There is no separate
connected-model output or overall performed-check banner, keeping the following jobs panel visible. Configuration/time metadata remains internal; configuration changes require fresh evidence. An Admin can configure repository sign-in through Connect repository in Summary,
or externally under the ADORE service account. Browser sign-in is separate.
Git supplies isolated working copies; the repository command tool reads issues and
publishes draft reviews; repository sign-in tests configured host authentication.
The container engine starts isolation; agent availability proves executable presence
in the local image (or, for a local project, that the installed Pi has a
sign-in or approved key); workflow availability checks the two configured AEGIS files.
An AI model connection row follows the six checks and shows the saved Test AI
connection evidence (passed or failed, with executor and model), or Not checked
with guidance to run Test AI connection when none is saved. A project whose
runtime is `local` hides the container runtime row and shows local-agent copy
for the agent row. Unknown container detection is incomplete;
any failed check requires intervention with a targeted corrective instruction.
These checks do not prove a complete job, Git push permission or AEGIS execution.
Fresh browser evidence validates the API status contract, selected project identity, revision, UTC
check time and the exact six check keys/types before display;
invalid results produce a localized error and withhold the new check rows.

Deletion uses a native modal with exact-name confirmation, Escape/cancel,
focus containment and trigger focus restoration; navigation clears intent.
Deletion remains subject to archived/idle project preconditions.


## Project repository connection

Summary â†’ **Connect repository** opens an Admin-only modal token form beside Check host prerequisites for the saved
provider/repository. Enter a server origin and an access token created on that
forge. HTTP requires explicit acknowledgement; GitHub requires HTTPS. Embedded
credentials, paths, queries and fragments reject. The project must be idle,
nonarchived and free of pending configuration/operations. **Verify and connect**
checks account identity and exact repository read access with two eight-second
CLI limits. This does not prove issue-write, draft-review, Git clone/push or
complete-job permissions. Run **Check host prerequisites** for fresh results.

The browser clears its memory-only token on submission, Close, Cancel or Escape and discards it
on project/session/navigation changes. Results contain account/server/repository,
never token. Failed authentication preserves previous credentials; an unconfirmed
request may have reached the server, so inspect readiness before retrying.

The worker and GUI host check use the same isolated CLI binding. Protected
repository-auth.json beside config binds immutable project identity and current
provider/repository/login. Other projects/shared logins remain unchanged. Missing
records preserve external auth; corrupt/stale records fail closed. Reconnect after
provider/repository/login changes. Structured config/portable exports and audit exclude tokens; raw TOML is an explicit Admin-only exception.
executors receive none. POSIX files use 0600; Windows profile ACLs and server-home
backups require service-account restrictions. See Component_Repository_Auth.md.

Proof: tests/test_repository_connection.py, existing readiness tests and
web/e2e/jobs.spec.ts repository-connection journeys with keyboard, four locales,
narrow/dark layout, token clearing and wrong-scope rejection.

Gitea readiness verifies configured-login tea API user evidence, requiring 2xx
HTTP and a valid unique JSON login. CLI exit zero alone does not authenticate.


## Explicit AI connection test

Administrators use **Settings → Agent and model → Test AI connection** for the configured Pi provider and model. Each explicit click sends one short request over Pi's RPC mode in a temporary container, or in a temporary folder for a Pi installed on the server, and may incur provider charges. The project must be idle with valid saved settings and no pending configuration/operations; a container project's installed image must contain the pinned Pi.

Only a valid completed challenge response reports connected: one completed shell command printing a nonce, then the exact reply (a failed shell call reports **tool-call-failed** with permission guidance). Failures provide redacted guidance (`modelEvidence.ts`) for a missing key (**credential-missing**, no container starts), an invalid key, model availability, rate limits, provider errors, image, CLI version or network. The action reuses executor credentials and egress and starts no job. Persisted evidence is bound to current project/model/configuration/credentials and presented consistently in Summary and host verification. Host-check time/version are internally validated and hidden from Summary/check details. See Component_Model_Connection.md and Component_Executor_Configuration.md.


## Project setting scope and guidance

Project Settings displays the selected project's effective configuration controls and inherited defaults. Provider, model, endpoint, launch command and credential fields belong to Settings → Agent and model; the backend, container runtime and image are reviewed edits there, while other environment setup is externally managed. The durable job state folder remains a read-only row. config.toml has no `state.channel` key; validation refuses it as unknown, and SettingsList shows no such row. Descriptions remain permanently below each label and provide the editor's accessible description. There is no per-row Help disclosure or override-only filter. The default/source marker describes value origin, not ADORE-wide scope. Polling intervals, per-project concurrency, executor and recovery settings remain per-project. Global capacity and audit retention belong to Administration. No project setting is promoted into a global policy by this presentation.

Proof: web/e2e/settings.spec.ts project settings keep defaults and single guidance (administrator/developer), plus existing candidate edit/discard journey.

Offline Playwright verification runs serially with a ten-minute global deadline,
thirty-second tests, ten-second assertions and no retries. A global timeout does
not establish complete proof even when every executed test passed.
Shell locale journeys await the exact successful language-save response before
closing a context, preserving the shared fixture's restored English preference.

### Transient application notifications

The application shows one dismissible notification for ordinary feedback or the current operation. Operation status replaces the queued confirmation. Pending/running operations stay visible until completion or dismissal; terminal results and ordinary notices disappear after five seconds. Closing the banner keeps worker polling and final project refresh active. Replacement/unmount cancels earlier dismissal timers; persisted outcomes remain available in History. Error alerts retain their existing presentation.

Editable settings place **Edit** beside **Active value** in the value column, including narrow screens. Administrators retain candidate review/apply/discard and disabled-state safeguards; developers have read-only rows.

Project Settings purpose categories are collapsed on entry. Opening a category shows equal-width description and active-value columns separated by24px; below640px they stack at full width. Native disclosures retain keyboard operation. Agent and model groups AI connection, the Pi provider, model, endpoint and launch command, closed Authentication (additional credential variables and Provider API key) and external environment guidance. Its inline field editors retain the existing row columns and stack using the normal mobile layout; the credential-name dropdown and removable selections wrap within the value column.

## External executor environment seam

ExecutorEnvironment.tsx supplies a compact conditional container notice with four-locale external Dockerfile/build/profile instructions. Config GET returns the effective image and Admin-only resolved config path. Enrollment step 2 and Settings → Agent and model offer Runs in (container | local), Container runtime and Executor image with suggestions from `GET /api/v1/executor-images` (Admin, read-only; serverImages.ts) and local account fields; additional credential names are optional. They omit image definition and build controls. Mutation guards for the other environment keys precede all config writes and staging/application; the dedicated existing AI connection test is retained. The image-build routes are removed and answer 404. A pending candidate with an `image_build` binding or for an operator-owned key is 503 `pending_config_corrupt` on view and apply, and an administrator can still discard it. Focused proof: test_executor_environment_choice.py, test_web_pending_config.py, images.spec.ts, enrollment.spec.ts. Detailed ownership: project-images.md.

External ownership and preparation/model/credential errors have localized corrective messages in errors.ts; errors.test.mjs checks server-code coverage and diagnostic/generic fallback.

## Automatic polling cadence

Automatic web polling and CLI `run --loop` use `PollCadence`: after a round
finishes, wait `poll_interval_seconds * multiplier + uniform(0, poll_jitter_seconds)`.
With `poll_backoff = true`, failures double the multiplier from 1 to 2/4/8,
cap at 8, and success resets it to 1. Disabled backoff uses 1. Quiet rounds retain
the multiplier and defer automatic work using the same wait. Quiet windows use
server-local time; explicit web commands remain available.
The web worker keeps independent in-memory cadence/deadlines per immutable
project identity and treats nonzero, timed-out, malformed or exceptional CLI
outcomes as failed checks. Invalid configuration gets a 60-second recheck with
no engine invocation. Restart resets cadence; serial work on another project
may delay a due round. `polling.mode` governs standalone CLI startup; the web
service schedules repeated `run --once` rounds independently of that value.

Connection and launch-command editing uses the ordinary setting-editor flex layout: Prepare/Cancel follow the control on wide screens, with shared responsive wrapping.

Inline editor validation follows the controls/actions on its own flex line. Incomplete model or command edits keep the same control/action placement and disabled Prepare, while responsive wrapping remains shared.
