<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web interface

The web cancellation and ticket Stop endpoints require explicit confirmation. The interface describes attempted runtime/worktree cleanup and retained job evidence. Readiness reports worker activity separately from its heartbeat; the CLI bridge schedules commands and polls serially, with explicitly owned cancellation signals reaching active work. Monitoring refreshes after actual results; admins can enroll from an empty Overview.

The production static bundle is committed with every frontend build-input change. The existing asset stamper records input and output fingerprints; release consistency rejects drift and compares an isolated fresh build before packaging.

Statistics browser fixtures restore the authenticated account's English/light
preferences in afterEach so a failed localized journey cannot leak its locale
to later files. The four-locale/two-theme statistics journey has a60-second
case budget, with unchanged assertions and suite-wide limits.
The malformed-consumption fixture selects a seeded nonempty job cohort rather
than the first project, so legitimately empty newly enrolled projects cannot
prevent injection. Running enrollment.spec.ts followed by statistics.spec.ts in
one offline fixture home proves the integration with unchanged error,
hidden-evidence and unavailable-export assertions.

Technical details displays Durable job state folder (`state.store_root`), Workflow Python command (`workflow.aegis_python`), Existing local repository path (`worktree.repo_path`) and Job working folders (`worktree.root`) as informational installation values. Operators configure them in the project TOML on the ADORE server; generic web mutations are refused. The localized guidance explains that changing a path does not relocate existing job state, repositories or working folders.

Project Settings follows **Repository → Tickets → Implementation → PR/MR and review → Statistics → Agent and model**, followed by closed **Technical details**. Repository owns platform/author identity and the single integration-branch editor; PR/MR shows its value and a link that opens/focuses that row. Tickets owns eligibility, polling, priority/type and pickup/status labels; hold/exclude affect pickup, not already-started jobs. Implementation owns capacity, budgets and progress commits, with closed Clarifications, Recovery after errors and Advanced stage time limits. Statistics owns recording/token switches and the informational database file inside closed Advanced statistics paths. Technical details and worktree paths are read-only; Repository branch naming uses reviewed edits and a server-checked example; runtime installation stays external and Agent and model groups executor settings in Settings. Interval, jitter and backoff remain visible; standalone CLI startup mode (`polling.mode`) stays in TOML/raw configuration and the effective catalog. Inactive reserved controls are omitted without changing CLI configuration. All categories start closed, retain reviewed Admin edits and Dev redaction, and have four-locale names.

Implementation uses shared four-locale names for reviewed settings, including **Active job limit**, **Maximum executor launches per job** and **Active work time limit (seconds)** names in rows, editors and candidate review. Help describes serial capacity with parked jobs excluded, lifetime launch counts, cumulative active time excluding waits and between-attempt time/cost checks. Reported USD accounting depends on captured token usage; cost-only reports do not count. File guidance describes distinct committed/pending/new product and AEGIS paths, the unfinished-merge exception and continuation when Git counting is unavailable. Per-attempt timeout help preserves configured recovery and strict-check semantics; progress publication is enabled by default with local commits retained when disabled, and the quick label is an optional framing hint. Configuration keys, runtime enforcement and role/redaction contracts retain their current behavior.

The revision-round limit belongs to PR/MR and review, with shared default five and localized combined-budget/exhaustion guidance. Acceptance checking defaults false; explicit values remain authoritative. Portable enrollment validates mapping size against the fifteen recognized rule keys.

Project settings keeps ready visible in Tickets and places answered/clarify/done/failed/review/working names in a native initially closed Status labels disclosure. Four-locale row/editor/review names explain actual lifecycle semantics. Inactive executor prefix and scope hint are omitted from controls while technical config/catalog values persist; admin reviewed edits and Dev read-only access retain existing authority.

`labels.control.exclude` has a shared four-locale Exclude from pickup label name in row/editor/candidate review. Help identifies the label-name setting and reversible presence-based pickup gate; already-started jobs continue.

`delivery.target_branch` has a shared four-locale Target branch label (Romanian: Ramura de integrare) in the row/editor/candidate review; help identifies the new-job remote base and PR/MR destination, short name without origin/, and human merge boundary.

`delivery.draft` is presented as localized PR/MR state at publication with Draft/Ready for review choices, using the administrator Save and important-effect confirmation and boolean wire contract. Active/default/proposed values carry the same names; in-review covers both forge states.

Secondary text uses contrasting light/dark theme colours. Project metadata,
configuration values, type/domain hints and field help use 0.875rem text with
1.5 line height; long identifiers and guidance wrap within their panels.
On narrow screens, setting labels, values and help stack vertically.


About shows the DDP Engineering logo band, ADORE and its version, and What's
new / License / Third-party notices buttons; licenses stay folded until pressed.
What's new renders `release_notes` from `/api/v1/about` (packaged
`adore/release_notes.toml`, four locales, English fallback, `Unreleased` as In
development); agents maintain it under AGENTS.md "Release notes rules" and
`02_Tools/internal/check_release_notes.py` checks it.

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
The Tickets table reserves a compact number column in both scopes and uses
the other flexible columns for content. A narrower mobile width keeps the
number and full-width details usable at 360 px (REQ-UX-5c5c19cd).

Implementation settings support reviewed edits for human-answer waiting time (positive integer plus seconds/minutes/hours/days), positive question-round count, a nonempty retry schedule (one nonnegative integer per line), and the complete stage-timeout map. The five stage rows choose either the general attempt limit or a positive custom limit in seconds; choosing general removes the override. Retry and timeout collections accept only safe integers and their declared keys; other lists/maps remain read-only except the existing reviewer list. Admins edit several settings, choose Save, confirm important effects and save only at the existing idle boundary; developers remain read-only. Names, help and controls share four locales. The answer deadline is independent of the reserved reminder; reminder format is still checked and no reminder is sent.

`REQ-FUNC-d67a1d33` / `REQ-UX-66547cbf`: `web/implementation_settings.py` validates only retry delays and the complete six-stage map and verifies a single semantic TOML edit. `web/src/implementationSettings.ts` supplies safe draft serialization and editor copy. Typed groups fill the editor width with normal-height nested controls and action buttons below the stack. Metadata emits one parent stage-map row for empty or populated maps; reviewed values and unchanged-base candidate meaning are checked again before apply. `test_web_pending_config.py`, `web/tests/settings.test.mjs` and typed Implementation/locale/Dev journeys in `web/e2e/settings.spec.ts` prove this seam.

## Branch naming presentation

PR/MR settings names the CI response **Action when PR/MR CI checks fail**.
Active/default values, option labels and candidate review use **Automatic repair**,
**Notify only** and **Ignore**, localized in English, French, German and Romanian.
The configured values remain `revise`, `notify` and `ignore`. Help explains the
shared revision-round limit and the configured approval policy before repair publication.
The read-only Integration branch reference uses the standard responsive setting
row: description and Repository link in the label column, Active value and the
branch in the value column, with the same value typography as other settings.
Its link opens Repository and focuses the single target-branch setting.

`SettingsList` owns reactive revision/draft-bound preview requests, cancellation of stale completions and closed `validBranchPreview` transport checks. Repository offers two text editors using shared four-locale row/editor/candidate names and help. Preview shows the effective/proposed pair and fixed example inputs; malformed, mismatching, stale or unavailable evidence cannot prepare a branch candidate. Developer preview is read-only and respects the project grant; runtime paths remain informational. The preview card wraps in narrow layouts and announces updates through a polite live region. Focused proof: `web/tests/settings.test.mjs`, `web/e2e/settings.spec.ts` branch-naming and locale journeys.

## Branch naming preview and edit authority

`POST /api/v1/projects/{name}/config/branch-preview` accepts the closed strict body `{template, rule, revision}` (512-character text bounds, SHA-256 revision). Scoped users supply CSRF; the shared config lock coordinates preview reads with application, and project grants and before/after revision checks precede evidence release. The route returns the shared config preview plus inspected revision and performs no writes or Git operations. Corrupt source returns `config_corrupt`, stale input returns `stale_config_revision`, and malformed transport fails request validation. Scoped developer reads hide inaccessible project identity with the existing 404 policy.

Only `worktree.branch_template`, `worktree.branch_rule` and the administrator-chosen `execution.backend`, `container.runtime`, `container.image` and `local.account/home/path/cgroup_root` are exceptions to the external environment edit restriction. They advertise editability/restart and retain administrator, validated candidate, lock, revision, paused/idle and replay integrity gates (direct PUT of the chosen keys returns 409 `pending_config_required`). Every other worktree/container/execution/local setting keeps external ownership. Focused proof: `tests/test_web_branch_naming.py`, `tests/test_web_config.py`, `tests/test_web_pending_config.py`.

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

`setup-preview` returns transient `verification_hint: {command, source} | null`
only for structurally valid inspected direct clones, using the pure shared
`adore/verification_hint.py` reader (see wizard.md). It never clones or runs the
command. AEGIS, absent clones and misses yield null; access/encoding failures
return redacted setup-unavailable/repo_path findings. Hints are outside canonical
review/digests and absent from Create/shared preparation and Settings.
EnrollmentWizard previews on Verification entry, validates the full response,
and fills only an untouched command with localized accessible source provenance.
A changed default permits one canonical re-preview; malformed/failed evidence
blocks progression, and generation guards preserve edits during requests. Edits
or clearing remain authoritative through Back, preview and Check; repository
changes clear only untouched defaults. Only explicit Create persists reviewed
text. Saved Settings never infer defaults. Proof: test_web_enrollment.py,
test_web_config.py, web/e2e/enrollment.spec.ts and settings.spec.ts; Projects help
and enrollmentCopy.ts carry the four-locale source guidance.

`REQ-DATA-71366af6`: workflow.verify_command is an exact-string editable API
setting; resolved reads, Admin exact raw TOML and unrelated reviewed edits preserve
it under existing validation, authorization and redaction. Guided API enrollment
accepts strict optional verify_command text, default empty, bound to canonical review.
Nontext and CR/LF/NUL return field-identifying 422 invalid_request. Scalar/batch
settings review refuses CR/LF/NUL with value-free command-field 400 invalid_config
without replacing active/pending bytes. implementation_settings.py serializes a
literal string, escaping DEL (U+007F) for TOML while retaining literal non-BMP
Unicode, and checks exact unrelated TOML meaning; pending reads/apply repeat
typed-domain, claimed-text and unchanged-base semantic checks. Existing Admin/CSRF,
revision, idle and locking gates remain. Invalid saved values retain key-named
issues or typed corrupt-config refusal. Enrollment Verification and Settings
Implementation expose the exact optional command through one-row textareas, with
shared four-locale names/help/invalid-input feedback. The browser refuses CR/LF/NUL
before preview or Save and validates scalar/batch pending values before recovery.
An inspected AEGIS enrollment replaces the control with its repository-test-command
note; the draft string is not erased. Jobs uses the saved run workflow and independent verification evidence described below. Proof includes
web/tests/readiness.test.mjs, settings.test.mjs, settingsSave.test.mjs,
localDiagnostics.test.mjs and web/e2e/enrollment.spec.ts/settings.spec.ts, alongside
test_web_enrollment.py,
test_web_config.py, test_web_config_raw.py, test_web_pending_config.py and
test_web_settings_batch.py. Browser coverage includes both actual clone workflows,
all four locales, Admin/Dev authority, multiline clipboard refusal, exact nonempty
and empty reviewed saves, and narrow light/dark layouts. Projects, Settings,
Glossary and Tickets help describes both workflows, optional command and live
pre-pick authority; help.test.mjs and help.spec.ts prove content and navigation
contracts in all four locales.

The settings help catalog includes Pi reasoning effort and describes the native
service account and optional tools PATH in all four locales.

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
  stale sources, rollback and replay fail closed. API tests are in
  `test_web_transfer.py`. Exact TOML import uses a separate endpoint contract.

- Admin-only `/projects/{name}/config/portable-settings` validates a bounded
  active snapshot through `portable-settings.md`; canonical no-store JSON and
  optional fixed attachment omit pending/identity/host/access/credential data.
  Authorization precedes lookup, invalid sources return value-free 503, and
  optional preview checksum conflicts return 409. Project ownership is rechecked
  after snapshot export; changed identity rejects. Exact TOML/CSV contracts retain
  their behavior. Portable parser/API tests remain offline.
- `GET /api/v1/projects/{name}/config/raw` is administrator-only. It returns original saved UTF-8 TOML bytes, including inline secrets, as `text/plain`, with `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. `?download=true` adds a fixed `config.toml` attachment. Authorization precedes lookup. Empty, malformed, unreadable, symlinked or oversized sources return value-free 503 `config_corrupt`; changed bytes or immutable project identity return 409 `stale_config_revision`. Reads are bounded to 524288 bytes; no environment resolution, `.env`, pending changes or mutation.
- Administrators use **Preview raw configuration** or **Export raw configuration** beside Project settings. Preview opens a closable dialog. Export preserves original saved `config.toml` bytes including comments, formatting and inline secrets. Pending changes, resolved defaults, separate `.env` files and external credentials are excluded. Preview is memory-only and cleared on dismissal or project/session change. Developers retain redacted read-only settings. Candidate review/apply/discard remains inside Settings.


- `/api/v1/jobs-page` provides globally ordered authorized current and
  archived job history, optional project/search/attention/status filters and optimistic
  content revisions. Overview requests `overview=true` to report authorized
  `unreadable_projects` with verified rows and counts from the remaining projects.
  Its metadata fallback `/api/v1/projects?overview=true` excludes runs with
  invalid activity timestamps while keeping authorized project identities.
  `/api/v1/jobs/{project_id}/{run_id}` uses composite identity.
  `adore/web/jobs.py` strictly validates schema-1 state, saved ticket metadata and
  JSONL bytes without altering operational journal recovery. Authorized list/detail
  responses carry recorded `workflow` as aegis/direct (REQ-DATA-18b26c84).
  Missing/unknown/nontext workflows and direct task bindings return typed
  run_state_corrupt without repair. Direct details additionally expose the closed
  `direct = {attempt, verification}` projection from captured state/journal bytes;
  list rows omit it. The last recorded positive safe-integer stage-launch attempt
  is distinct from cumulative launches and failed attempts; missing launches stay
  null. Saved configured results retain the redacted command, canonical decimal-text
  exit, finite nonnegative seconds, boolean timeout and normalized bounded output.
  Absent verification is unavailable; explicit not configured is unverified.
  Current configuration never substitutes for saved evidence. See
  `05_SoftwareDocu/Component_Web_Jobs.md` for exact fields and source semantics.

- Exact Admin/CSRF import-preview suggests an available ID when omitted and
  returns the resolved identity, config/candidate revisions, local findings and
  allowlisted review. import-check reuses bounded probes with
  ephemeral revision/time-bound status; import confirms unchanged bytes after
  full identity/ownership/state reinspection within enrollment/conductor locks.
  The same popup accepts a complete exported ZIP (18 MiB) or TOML (512 KiB).
  Bundle-preview/bundle routes under `/projects/import` bind exact ZIP bytes,
  ordinary config revision and observed source associations. Source retention and
  paused publication are coordinated under the recipe lock. Different root
  recipes reject rather than replace. Failure rolls back new bindings/profile;
  final project/enrollment unlocks precede applied audit confirmation. See project-images.md.

- `create_app(home, probe_runner=...)` mounts `/api/v1` and bundled static
  assets. The runner is injectable for explicit host-readiness and image runtime commands.
- Guided `setup-preview` returns canonical secret-free setup/paths and a digest
  binding exact deterministic config, ID, display and description. Additive
  `setup-check` retains bounded, administrator and revision-bound evidence and returns a one-use token; `setup-create` validates it and publishes measured checks with the exact stopped configuration.
  All require Admin/CSRF. Setup includes supported labels, run limits and credential
  environment names. Gitea probes honor the selected tea login.
- `EnrollmentWizard` owns five-step memory state (starting at repository/identity), localized visible guidance,
  corrective findings/focus, generation invalidation, loss guards and frozen review.
  The immediate creation ref lock prevents double submit. Completion explains
  stopped pickup and separate activation; persistent readiness retains current server-issued draft evidence or is checked
  separately. `enrollmentCopy.ts` preserves EN/FR/DE/RO and existing themes/branding.
- `adore-web --home ...` binds loopback; remote traffic uses a TLS proxy.
  Uvicorn accepts forwarded context only from loopback proxy peers, and HTTPS
  login emits a Secure session cookie.
- `adore-web-worker --home ...` polls profiles and queued operations.
- `WebStore(home / "web.db")` owns accounts, sessions, grants, audit and queue.
- `02_Tools/create_package.py` creates a complete native portable archive;
  `verify_package.py` checks it using automatically cleaned temporary data.

Admin container export defaults to the complete source ZIP. RawConfiguration keeps
missing-base attachment, replacement, errors and recovery inside one compact dialog;
file selection previews automatically, Save recipe is explicit and stale/invalid
responses never enable a complete export. All four locales use the same mobile
layout. Admin/CSRF/config-revision/digest checks guard source retention independently
of job admission; no pending or active configuration/job state is rewritten.
See project-images.md, test_web_executor_recipes.py and portable.spec.ts.

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
  checks; browser readers validate the closed workflow/check domain and prerequisite
  verdict agreement, and render Workflow outside pass/fail rows in four locales.
  Absent evidence is unverified and changed config is stale. Mid-probe
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
- Accounts store optional language, theme and `ticket_body_mode`. Authenticated
  `/me/preferences` reads and CSRF-protected partial updates remain account-scoped.
  Language/theme nulls use browser fallback; ticket mode null selects Rendered.
  Explicit null or unsupported ticket mode updates return 422 `invalid_request`.
  Corrupt saved preferences fail with `WebStoreError`/503 `preferences_corrupt`
  on reads and partial writes, without repair.
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
  either. The web store has one schema (16); a database in another version is
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
- The administrator UI edits multiple settings and uses one dirty-aware Save. Important effects receive a no-write canonical preview and native modal; cancellation retains inputs without a new stored draft. Confirmed preparation/apply binds exact hashes and plans. Ordinary changes save directly. Drafts survive errors and stale revisions. Navigation and browser reload guard abandonment. Apply retains atomic idle/lock/pause authority and interrupted-apply reconciliation.
- Explicit administrator readiness checks use bounded doctor probes from the
  API host and persist typed revision/time-bound evidence. Required `workflow` information
  is `aegis` from `.agentic/aegis.py` alone, `direct` otherwise in an available clone,
  or `not-inspected` when unavailable; read-only inspection runs no repository code.
  The stored base checks are exactly `git`, `forge_cli`, `forge_auth`,
  `container_runtime` and `executor_cli`, plus the
  boolean `executor_sign_in` for a project with provider `chatgpt` only (true
  when `chatgpt.status` of the server's credential directory is `signed-in`;
  read from the files without starting Pi; false makes the evidence `failed`).
  The stored-record reader accepts that one extra key. Model
  access is proved only by the explicit Test AI connection. WSL runtime
  detection remains unverified; CLI output and credentials are never returned.
- Provider/model/endpoint, launch command and credential-name edits use the
  reviewed candidate flow in Settings → Agent and model
  (executor-configuration.md). Provider, model and the OpenAI-compatible
  endpoint are one virtual candidate key, `executor.connection` (strict JSON
  `{provider, model, base_url, api}`), edited by `AgentConnectionEditor.tsx`;
  the rows `executor.provider`, `executor.model`, `executor.endpoint.base_url`
  and `executor.endpoint.api` report that `edit_key` and cannot be staged
  individually (400 `setting_not_editable`). `SettingsImpactDialog` shows changed connection fields (Provider, Model, Endpoint base URL, Endpoint API type); `settings.ts` input kind `connection`, `connectionRowVisible` hides
  the endpoint rows unless the provider is `custom`.
- `GET /api/v1/pi-providers` (any signed-in user; 503
  `provider_catalog_unavailable` when the shipped catalog is unreadable)
  returns `{pi_version, providers[{id, name, variable, models}], chatgpt:{id,
  models}, custom:{id, variable, apis}}`; `chatgpt.models` is the catalog's
  `chatgpt_models`. `agentConnection.ts` reads it (`readProviderCatalog`) for
  the provider select and the model datalist (`providerModels`: Pi's models of
  an API-key provider, `chatgpt.models` for `chatgpt`). The enrollment wizard's
  model datalist offers only API-key provider models.
- The server's one ChatGPT sign-in (`adore/chatgpt.py`, credential directory
  `<ADORE home>/chatgpt`) has Admin-only routes; changes need CSRF. At most one
  pending sign-in lives in the web server's memory under one lock.
  `GET /api/v1/chatgpt-sign-in` returns `{status, pending}` (`signed-in`,
  `not-signed-in` or `sign-in-again`); a pending sign-in older than 900 s is
  cancelled and reported as not pending. While pending, a status read observes
  queued native callback completion or refusal, reaps the helper and audits the
  verified outcome once. The visible panel polls once per second only while
  pending, with a 15-minute bound; manual redirect remains the remote fallback.
  `POST /api/v1/projects/{name}/chatgpt-sign-in` cancels any previous pending
  sign-in, starts Pi's `login` through the selected native helper or project
  helper container, and returns `{authorize_url, expires_in: 900}`; it returns
  409 `project_archived`, 503 `config_corrupt` and 409
  `invalid_config`, and needs neither paused pickup nor an idle project.
  `PUT /api/v1/chatgpt-sign-in` takes exactly `{redirect_url}` (at most 8192
  characters) and returns `{status, pending}`; 400 `chatgpt_redirect_invalid`
  and 400 `chatgpt_state_mismatch` keep the sign-in pending, 409
  `chatgpt_sign_in_not_pending` means none waits, and every other failure ends
  it. `DELETE /api/v1/chatgpt-sign-in/pending` cancels and keeps the stored
  credential. `DELETE /api/v1/chatgpt-sign-in` cancels, deletes `auth.json` and
  the `sign-in-again` mark, keeps `device-id`, and returns 503
  `chatgpt_credential_unreadable` when a file cannot be removed. Failure codes:
  409 `chatgpt_credential_unreadable`, 502 `chatgpt_not_eligible`, 502
  `chatgpt_access_denied`, 502 `chatgpt_code_rejected`, 502
  `chatgpt_sign_in_refused`, 503 `chatgpt_sign_in_unavailable`, 503
  `chatgpt_helper_failed`. Audit actions are `chatgpt-sign-in-started`,
  `chatgpt-sign-in-completed`, `chatgpt-sign-in-failed`,
  `chatgpt-sign-in-cancelled` and `chatgpt-disconnected`; `WebStore._safe_detail`
  keeps a `chatgpt-sign-in-failed` detail only when it matches
  `chatgpt_<code>`, else `[redacted]`. Redirect-invalid, state-mismatch and
  not-pending failures are not audited. `create_app(chatgpt_popen=...)` injects
  the helper's process factory.
- Config GET returns `model_connection: null` for a `chatgpt` project while the
  server's ChatGPT status is not `signed-in`.
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
- JobWorkspace reads `/jobs-page` for authorized attention/jobs/history
  and composite `/jobs/{project_id}/{run_id}` for detail. Overview leads with
  human-action/failure/handoff attention and actual working/publishing rows in
  compact title/project/ticket, status and Details tables. App supplies one header
  Project selector through DashboardShell's optional controls slot, before selected
  context and tables. Primary Overview href/action defaults all authorized projects;
  explicit scoped reload/Back retain URL identity. Visible15s background polling
  retains validated same-scope rows while pending and clears them on failed reads;
  the header Refresh and stamp appear on Users.
  Settings, Access, global Change history and project History also use 15-second visible polling.
  Settings suspends reads for configuration, pricing and authentication drafts
  or writes. Price reads are validated and independent of configuration reads. Access protects
  confirmed changes from older reads, and audit refresh preserves filters and
  open evidence. Both Overview tables validate scope and agree on unreadable
  project IDs before displaying verified rows. Needs attention names the
  affected projects. Their Summary job counters are unavailable. Overview
  performs no usage reads. Worker faults are visible and
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
  Enroll new project starts from a repository URL: Read
  repository (`/api/v1/projects/repository-source`, `adore/web/repository_source.py`)
  fills forge, repository, login, branch and the derived ID and prefills an editable
  clone path `<home>/repos/<ID>`; Continue waits for a successful read; the clone is
  made only at creation (exclusive folder, reused if its origin matches, removed on failure);
  neither AEGIS file is an enrollment prerequisite and no files are added to the clone;
  no existing-clone mode (a matching clone at the path is reused); no Stable project ID field;
  reviewers are optional (empty list = no review request) in the wizard and Settings.
  Projects offers Enroll new project at `/projects/new` and Import raw
  configuration in a dialog. Former import and clone URLs resolve to Projects.
  Administrators open Enroll new project as a five-step guided page with visible localized
  instructions. Clone paths identify existing Git clones on the ADORE host;
  step 2 asks Provider, Model (with Pi's models as a datalist) and, for an
  OpenAI-compatible endpoint, Endpoint base URL and Endpoint API type, and names
  the credential variable to save after creation; review lists them plus
  "Credential to save after creation"; environment setup is external. Back retains
  the memory draft, Cancel warns about loss, and completion confirms stopped pickup
  before the explicit Open project action.
  RawImportDialog validates each selected file and enables Import for its
  current reviewed identity and bytes. Replacement and dismissal abort validation.
  Confirmation rereads the file, rejects changed bytes and serializes publication.
  Success closes the dialog and refreshes Projects with stopped pickup.
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
- Manual Start remains available with monitoring paused; it leaves automatic pickup paused and preserves eligibility, capacity, locks and approval gates.
- The worker runs the CLI with stderr joined to stdout (`CommandOutcome`; a
  runner may still return a bare exit code). A non-zero exit or timeout keeps a
  `detail` tail from `util.output_tail` with `jobs.redact_text` (redacted before
  the 20-line/2000-character cut), and a refused start keeps the CLI's
  not-started code for its own ticket as `reason` (REQ-FUNC-fbb6448c,
  REQ-FUNC-6055f2c6). Both stay on the operation row (schema 17), never in audit
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

The legacy CLI bridge schedules command ordering for one home while scoped owners
provide independent execution/configuration claim boundaries. During any blocking engine
command or project poll, the worker watches queued cancellations across projects and
claims the cancel operation and signals the active conductor only after rechecking
current ownership, grants and immutable project identity. Other queued operations
wait for the current engine command. Administrator metrics attribute usage and
reported/estimated cost to the most recent revision-started event in each run;
initial work remains in run totals and developers receive no financial rows.
API liveness at `/api/v1/health` is separate from readiness at `/api/v1/ready`.
The worker refreshes its SQLite heartbeat even while an engine command
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
| One settings Save, draft recovery, important effects, responsive rows | `App.tsx` SettingsList/SettingsImpactDialog/saveSettings, `settingsSave.ts`, `web/settings_batch.py`, config preview/pending/apply | `test_web_settings_batch.py`, `settingsSave.test.mjs`, `settings-save.spec.ts`, `settings.spec.ts` |
| Atomic reviewed accounts and access edits | `UserCreation.tsx`, `userCopy.ts`, `create_user_with_access`, `/users/with-access` | `test_web_user_creation.py`, auth/access/RBAC suites, `web/e2e/users.spec.ts` |
| Authorized global job evidence, paging, revisions | `adore/web/jobs.py`, `jobs_page` and `job_detail` in `app.py` | `test_web_jobs.py`, `test_web_paging.py`, `test_web_rbac.py` |
| Portable new-project file/copy API and source revision | `_prepare_transfer`, `transfer_source` | `test_web_transfer.py` |
| Enrollment, display identity, readiness evidence | `adore/profiles.py`, `adore/wizard.py`, `adore/web/app.py` | `test_web_enrollment.py`, `test_web_errors.py` |
| Both-workflow enrollment and informational Workflow evidence | `_workflow_observation`, `_probe_setup`, `readiness.ts`, `ReadinessEvidence.tsx` | `test_repository_source.py`, `test_web_readiness.py`, `readiness.test.mjs`, `enrollment.spec.ts` |
| Exact TOML enrollment and automatic validation | `web/src/RawImportDialog.tsx`, `importCopy.ts`, `_inspect_project_import` | `test_web_import.py`, `web/e2e/import.spec.ts` |
| Guided enrollment steps, correction, draft loss and review | `web/src/EnrollmentWizard.tsx`, `web/src/enrollmentCopy.ts`, `App.tsx` | `web/e2e/enrollment.spec.ts` |
| Ticket rich text, exact source and account mode | `web/src/forgeMarkdown.ts`, `ticketPreferences.ts`, `TicketWorkspace.tsx`, `App.tsx`; preference routes and store | `web/tests/forgeMarkdown.test.mjs`, `ticketPreferences.test.mjs`, `web/e2e/tickets.spec.ts`, `test_web_auth.py`, `test_web_rbac.py` |
| Accounts, sessions, queue | `adore/web/store.py` | `test_web_auth.py`, `test_web_commands.py` |
| Statistics evidence, selection, exports and job consumption | `web/src/statistics.ts`, `StatisticsEvidence.tsx`, `App.tsx`, `JobWorkspace.tsx` | `web/tests/statistics.test.mjs`, `web/e2e/statistics.spec.ts` |
| API permissions/config/metrics | `adore/web/app.py` | `test_web_rbac.py`, `test_web_config.py`, `test_web_pending_config.py`, `test_web_readiness.py`, `test_web_metrics.py` |
| Worker execution | `adore/web/commands.py` | `test_web_commands.py` |
| Action workspace, next action and observed history | `web/src/JobWorkspace.tsx`, `jobModel.ts`, `jobCopy.ts` | `web/tests/jobs.test.mjs`, `web/e2e/jobs.spec.ts`, `test_web_jobs.py` |
| Saved workflow labels, direct attempts/results and trust-boundary errors | `jobs.py::_direct_evidence`, `jobModel.ts::readJobDetail`, `JobWorkspace.tsx::DirectEvidenceView`, `jobCopy.ts::workflowStageLabel` | `test_web_jobs.py` direct evidence cases, `web/tests/jobs.test.mjs`, `web/e2e/jobs.spec.ts` Direct job evidence |
| Direct stage-limit guidance and localized Jobs help | `web/src/settingHelp.ts`, `web/src/help/content/{en,fr,de,ro}/{jobs,settings}.md` | `web/tests/settingHelp.test.mjs`, `web/tests/help.test.mjs`, `web/e2e/help.spec.ts` |
| Language, theme, views | `web/src/App.tsx`, `web/src/i18n.ts` | `npm run validate`, isolated Chromium journeys |
| Shell, branding, scope, request feedback | `web/src/DashboardShell.tsx`, `web/src/Presentation.tsx`, `web/src/App.tsx` | `web/e2e/shell.spec.ts`, `web/tests/shell.test.mjs` |
| URLs, tabs, navigation | `web/src/routes.ts`, `web/src/App.tsx` | `npm test` (`routes.test.mjs`), browser check |
| Background refresh and paging | `web/src/polling.ts`, `JobWorkspace`, `ServerPager` in `App.tsx`, `/api/v1/audit-page` | `npm test` (`polling.test.mjs`), `test_web_paging.py` |
| Settings, Access and Change history refresh | `settingsPoll` and `ProjectAccess` in `App.tsx`, `AuditHistory.tsx` | `e2e/settings.spec.ts`, `e2e/shell.spec.ts`, `e2e/audit.spec.ts` |
| Error codes and messages | `adore/web/app.py` (`_error`, `_STORE_ERROR_CODES`), `web/src/errors.ts` | `test_web_errors.py`, `npm test` (`errors.test.mjs`) |
| ChatGPT sign-in routes, panel and readiness | `adore/chatgpt.py`, sign-in routes and `_probe_setup` in `adore/web/app.py`, `web/src/ChatGptSignIn.tsx`, `chatgptCopy.ts`, `readiness.ts` | `test_chatgpt.py`, `test_web_chatgpt.py`, `npm test` (`chatgpt.test.mjs`, `readiness.test.mjs`), `web/e2e/executor-config.spec.ts` |
| Project developer access | `/api/v1/projects/{name}/access` routes in `adore/web/app.py`, `project_members` and `set_membership` in `adore/web/store.py`, `ProjectAccess` in `App.tsx`, `web/src/routes.ts` | `test_web_project_access.py`, `npm test` (`routes.test.mjs`), browser check |
| Project settings list and row editing | `_setting_metadata` in `adore/web/app.py`, `web/src/settings.ts`, `SettingsList` in `App.tsx` | `test_web_config.py`, `npm test` (`settings.test.mjs`), browser check |
| Setting help texts and catalog | `web/src/settingHelp.ts`, `web/src/settingKeys.json`, `default_config()` in `adore/config.py` | `test_web_setting_catalog.py`, `npm test` (`settingHelp.test.mjs`), browser check |
| Offline media | `02_Tools/*web*.py` | `test_web_package.py`, installed HTTP smoke |

## Key behaviors

- REQ-DATA-08ed925c / REQ-SEC-5d0f86e7: authorized read-only direct evidence is
  validated before filters/counts/paging, redacted for both roles and released
  only after source/profile/grant reinspection. Malformed saved attempts/results
  fail with typed secret-free errors; no repair or external command runs.
- REQ-UX-4123c97c / REQ-UX-029d0525 / REQ-UX-ad37f7e7 / REQ-UX-5cf762f8:
  Jobs identifies the saved workflow; direct current/timeline stages are localized
  Implementation, Validation and Done only, without an AEGIS task. AEGIS labels,
  actions and observed-only timeline semantics retain their existing meanings.
- REQ-UX-ef06a3c7 / REQ-UX-1b6f2a83 / REQ-UX-16f751b7 / REQ-UX-f6c6e946 /
  REQ-UX-7e9792e9 / REQ-UX-647b1549 / REQ-UX-631835f9 / REQ-UX-009b4cb9 /
  REQ-UX-9cdaa57b / REQ-UX-7fab3dcb: the direct panel shows the saved attempt,
  command before outcome, duration and focusable literal tail, distinguishing
  passed, failed, timed out, explicit unverified and unavailable evidence.
- REQ-UX-b105b854 / REQ-UX-46c09118 / REQ-UX-a8c7ea48: missing/nontext/unknown
  workflow, malformed direct detail or forbidden direct stages reject browser
  reads; list error/incomplete/source-change and detail failure hide stale panels.
- REQ-UX-c77f7335 / REQ-UX-558518e7: four-locale Jobs/Settings help and inline
  guidance explain direct evidence and build/validate limits with general fallback.

- REQ-FUNC-d50a408d / REQ-FUNC-2bf3e808 / REQ-FUNC-357ae298: offline preview
  returns a separate command/source hint only for inspected direct clones; AEGIS,
  absent clones and misses receive null, and access/encoding errors refuse setup.
- REQ-UX-92197baa / REQ-UX-dd21046e / REQ-UX-cca17b80 /
  REQ-REL-60015e50: enrollment validates the full hint response, prefills only
  untouched drafts, identifies the source in four locales and canonically
  re-previews at most once. Human edits/clearing win over delayed responses.
- REQ-DATA-c1c4d1c3: saved Settings never infer over an empty/custom command;
  explicit reviewed Create/Save is the persistence authority.

- REQ-FUNC-e3cf5dfd / REQ-SEC-74753f08: reviewed scalar/batch apply permits parked-clarification jobs only for the five budget keys, with exact candidate reconstruction, Admin/CSRF, source/state-root/lock/revision and unfinished-operation checks retained. Mixed batches, direct edits and other lifecycles keep the existing idle boundary. No job state or approval is written by budget apply.
- REQ-UX-1054b9b6: composite Job details adds non-financial `budget` counters (launches and cumulative active seconds), current limits and config_revision, bound to unchanged source bytes. The frontend rejects invalid/missing detail budget evidence, shows a 90%/exhausted status notice and an Admin project Settings link, with four-locale timing/help. Statistics remain independent. Proof: test_web_jobs.py, test_web_settings_batch.py, jobs.test.mjs and jobs/enrollment browser journeys.

- `REQ-UX-95f72cce`, `REQ-UX-a393abfe`, `REQ-UX-a371d306`: descriptions and
  comments default to semantic GFM; a shared Description-side selector shows exact
  API strings in source mode. Empty descriptions retain the localized fallback.
- `REQ-SEC-29fc8db7`, `REQ-SEC-777ae52c`, `REQ-SEC-fc07c123`,
  `REQ-SEC-a0ea8c6d`, `REQ-SEC-f29221e6`: forge bodies use React-only rendering,
  literal HTML, absolute HTTP/HTTPS/mailto anchors with opener protection and inert
  image placeholders; metadata stays plain text with HTTP(S)-only title links.
  Task checkboxes are disabled. The help parser remains separate.
- `REQ-DATA-8532e8f2`, `REQ-DATA-529c5e6e`, `REQ-DATA-a493390d`,
  `REQ-REL-5bb00e92`: account mode persists across projects/reloads/browsers, read
  on sign-in/reload. App validates responses, allows one optimistic save per
  session, confirms only that field, rolls back failures with localized feedback
  and ignores old-session completions. Session clear resets mode and pending guard.
- `REQ-UX-f79c7d6e`, `REQ-UX-a560ba57`, `REQ-UX-58401aa1`,
  `REQ-UX-34ee3996`: native focusable mode selectors, four-locale copy/help and
  theme-token styling contain wide code/source/tables in keyboard-focusable local
  scroll regions at desktop and narrow widths.

- `REQ-REL-2e67fc6d`: historical Deliver records stay readable and labelled; new
  jobs show Done during approval, publication and human review.
- `REQ-DATA-eebc4f88`: the stage-timeout editor accepts only the five executor stages.

- REQ-UX-812acd4b: reviewed configuration admits the container-only system-package boolean. The generic settings row explains direct agent installation, sudo-capable images, fresh jobs and independent network access.

REQ-FUNC-f9946b6b: The worker validates Retry terminal evidence against the
requested job and actual exit. A bound retry_failed result reads only that job's
saved failed outcome, already public in Jobs. Corrupt or missing results use closed
fallbacks, successful exits without valid evidence remain uncertain, and timeouts
remain uncertain. operationResultText localizes retry reasons and displays saved
terminal causes in all four locales. No raw CLI/forge/executor output is forwarded.
Focused proof: tests/test_retry_revalidation.py and web/tests/manualStart.test.mjs.


- REQ-UX-b75e1df8: ProjectInput accepts execution_backend and the current account and optional local PATH. Review/config show actual machine/account/system; metadata reports runtime=local. Reviewed candidates recheck pinned native plans. Host checks avoid container detection.

Native control/auth route to local-execution.md. Focused proof:
`04_Software/tests/test_local_execution.py`.


- `REQ-UX-94a97e70`: CLI validates external execution selections and previews complete image/source/commands. Web reads expose effective image and retained preparation evidence; environment mutations are refused. Host/model probes normalize image without setup; jobs project validated timestamp/exit/timeout/cancel evidence. Portable rule allowlists stay unchanged.
- ChatGPT sign-in: `REQ-FUNC-4efa960e` status, `REQ-FUNC-09ac930a` start from a native or container
  project, `REQ-FUNC-055f8047` complete with the pasted address, `REQ-FUNC-74d90036` refuse
  another callback, `REQ-FUNC-0e27781c` localized refusal, `REQ-FUNC-f0076585` Disconnect,
  `REQ-FUNC-11308471` readiness row, `REQ-FUNC-4388b030` ChatGPT Test AI connection,
  `REQ-SEC-2689e1f5` Admin/CSRF/value-free audit, `REQ-UX-0d58a662` four-locale panel.

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
- `REQ-FUNC-702b0fce`, `REQ-FUNC-49e89542`, `REQ-DATA-e1eaf583`, `REQ-SEC-dc4bd0c3` - complete canonical preview, explicit bound probe, exact guarded creation and reference-only Admin/CSRF draft boundaries.

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
  guidance, catalog control domains and exact multi-setting save confirmation, with
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

- `04_Software/adore/web/ownership.py`: typed owner handles and conservative local process birth evidence.
- `04_Software/adore/web/worker_context.py`: child attachment, exact command binding, actual run scopes, scoped heartbeat and effect fences.
- `04_Software/tests/test_web_ownership.py`: deterministic concurrent claims, recovery, corruption, process and authorization contracts.
- `04_Software/web/src/forgeMarkdown.ts`: pinned react-markdown/remark-gfm React
  renderer with controlled anchors, inert images and named overflow regions.
- `04_Software/web/src/ticketPreferences.ts`: closed account preference response reader.
- `04_Software/web/src/TicketWorkspace.tsx`, `ticketCopy.ts`, `styles.css`:
  shared mode controls, untouched source and four-locale themed presentation.
- `04_Software/web/tests/forgeMarkdown.test.mjs`, `ticketPreferences.test.mjs`,
  `04_Software/web/e2e/tickets.spec.ts`: renderer/security, preference boundary and
  offline switching/persistence/session/keyboard/theme/width/locale proof.
- `04_Software/web/vite.config.ts`, `THIRD_PARTY_NOTICES.md`: emit and identify
  `BUNDLED_LICENSES.json` with full bundled dependency licenses in each build.

- `04_Software/tests/test_system_packages.py`: package authority, independent egress, recovery and reviewed settings contracts.

- `04_Software/tests/test_retry_revalidation.py`: explicit Retry and bound outcome proof.

- `04_Software/adore/web/settings_batch.py`: closed batch parsing; authority and final configuration validation remain in app.py.
- `04_Software/web/src/settingsSave.ts`: typed local drafts, meaningful equality, recovery, preview binding and four-locale Save copy.
- `04_Software/adore/web/implementation_settings.py`: exact command text, strict retry/map domain and semantic single-setting TOML writers.
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

- `tests/test_web_transfer.py` covers the portable new-project enrollment API.

- `04_Software/web/src/JobWorkspace.tsx` â€” scoped attention/jobs/detail, observed
  paging and queued command feedback; `jobModel.ts` validates transport evidence,
  `jobCopy.ts` localizes conditional actions.
- `04_Software/web/tests/jobs.test.mjs`, `04_Software/web/e2e/jobs.spec.ts` â€” public
  evidence/route boundaries and offline real API/worker/browser journeys.


- `04_Software/adore/web/jobs.py`
- `04_Software/tests/test_web_jobs.py`
- `05_SoftwareDocu/Component_Web_Jobs.md`

- `04_Software/web/src/RawImportDialog.tsx`, `importCopy.ts` and `web/e2e/import.spec.ts` - modal exact enrollment, localized guidance and offline browser boundaries.

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
- `02_Tools/create_package.py`, `verify_package.py` and
  `internal/stamp_web_assets.py` - portable media and static asset preparation.
- `04_Software/tests/test_web_*.py` - focused API, pricing, worker and packaging tests.
- `04_Software/web/src/ChatGptSignIn.tsx`, `chatgptCopy.ts` - the server's ChatGPT
  sign-in panel, its four-locale copy and the strict `{status, pending}` and
  `{authorize_url, expires_in}` parsers; `web/tests/chatgpt.test.mjs` and
  `tests/test_web_chatgpt.py` (with `tests/fake_chatgpt_helper.py`) prove them.

### Settings edit and review seam

Start at `App.tsx` SettingsList/SettingsImpactDialog and `settings.ts` for grouped controls
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
A validated current host-check completion supersedes in-flight project-list reads
before publishing its result (`App::checkProjectReadiness`, `projectsRequest`).
Older snapshots cannot overwrite that result; subsequent fresh polls retain update
authority. The held-snapshot/fresh-poll journey in `web/e2e/jobs.spec.ts` proves
both sides of this response-order boundary under `REQ-UX-78923e00`.
Check host prerequisites opens the details panel immediately and shows Checking while the request runs. Duplicate checks are blocked. Results or localized failure guidance appear inside the panel; Close details hides it without cancelling a running check, and completion respects the closed state. The check button exposes the disclosure state and regains focus on close. Project/account/page changes discard stale responses; project-tab navigation retains current evidence. Model/executor
access evidence appears only inside these details on Summary. There is no separate
connected-model output or overall performed-check banner, keeping the following jobs panel visible. Configuration/time metadata remains internal; configuration changes require fresh evidence. An Admin can configure repository sign-in through Connect repository in Summary,
or externally under the ADORE service account. Browser sign-in is separate.
Git supplies isolated working copies; the repository command tool reads issues and
publishes draft reviews; repository sign-in tests configured host authentication.
The container engine starts isolation; agent availability proves executable presence
in the local image (or, for a local project, that the installed Pi has a
sign-in or approved key). A separate informational Workflow row reports AEGIS
from `.agentic/aegis.py` alone, Direct when absent in an available clone, or
not-inspected when the clone is unavailable; it never gates readiness.
An AI model connection row follows the five base checks and shows the saved Test AI
connection evidence (passed or failed, with executor and model), or Not checked
with guidance to run Test AI connection when none is saved. A project whose
runtime is `local` hides the container runtime row and shows local-agent copy
for the agent row. A `chatgpt` project shows a **ChatGPT sign-in** row between the
base checks and the AI model connection row; when it fails, its fix points to
Sign in with ChatGPT in Settings → Agent and model. Unknown container detection is incomplete;
any failed check requires intervention with a targeted corrective instruction.
These checks do not prove a complete job, Git push permission or AEGIS execution.
Fresh browser evidence validates the API status contract, selected project identity, revision, UTC
check time, closed workflow enum and exact configured prerequisite keys/types,
including the five base checks and applicable boolean `executor_sign_in`,
`egress_proxy` and `web_search_key` (`readiness.ts`), before display;
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


## Internet access for the agent

Settings -> Agent and model shows `executor.internet` (generic boolean row
shown On/Off through `executorSettings.agentValue`) and `executor.web.search`
(choice row from the server's `WEB_SEARCH_CHOICES`), both reviewed edits with a
restart note. While the active value is On or the editor or a pending
candidate proposes On, `internetCopy.internetWarning` says a malicious page
could make the agent send its API key or ChatGPT token out; a local-backend
project shows `internetCopy.internetLocal` (not enforced) instead. The
credential panel lists `credential_variables` (provider key, then
BRAVE_API_KEY/TAVILY_API_KEY for an internet-on Brave/Tavily project) and is
also shown beside the ChatGPT sign-in when `searchKeyNeeded`. `_probe_setup`
adds `_internet_checks`: `egress_proxy` (container + internet off: `image
inspect` of the proxy image) and `web_search_key`; `readinessChecksShape`
accepts them as optional booleans and `ReadinessEvidence` labels them in four
locales. Requirements: `REQ-UX-e340fc1e`, `REQ-FUNC-aaa37a72`,
`REQ-SEC-b6a4a434`.

## Explicit AI connection test

Administrators use **Settings → Agent and model → Test AI connection** for the configured Pi provider and model. Each explicit click sends one short request over Pi's RPC mode in a temporary container, or in a temporary folder for a Pi installed on the server, and may incur provider charges. The project must be idle with valid saved settings and no pending configuration/operations; a container project's installed image must contain the pinned Pi.

Only a valid completed challenge response reports connected: one completed shell command printing a nonce, then the exact reply (a failed shell call reports **tool-call-failed** with permission guidance). Failures provide redacted guidance (`modelEvidence.ts`) for a missing key (**credential-missing**, no container starts), an invalid key, model availability, rate limits, provider errors, image, CLI version or network. A `chatgpt` project first gets an access token from the server's sign-in for 90 s plus 300 s and reports **sign-in-required** (not signed in, or sign in again), **subscription-refused** (OpenAI refuses the plan), **connection-failed** (OpenAI not reachable) or **usage-limit** (Pi's rate limit on a subscription); the token reaches Pi only in the launch environment and is redacted from the evidence. The action reuses executor credentials and egress and starts no job. Persisted evidence is bound to current project/model/configuration/credentials and presented consistently in Summary and host verification. Host-check time/version are internally validated and hidden from Summary/check details. See Component_Model_Connection.md and Component_Executor_Configuration.md.


## Project setting scope and guidance

Project Settings displays the selected project's effective configuration controls and inherited defaults. Provider, model, endpoint, launch command and credential fields belong to Settings → Agent and model; the backend, container runtime and image are reviewed edits there, while other environment setup is externally managed. The durable job state folder remains a read-only row. config.toml has no `state.channel` key; validation refuses it as unknown, and SettingsList shows no such row. Descriptions remain permanently below each label and provide the editor's accessible description. There is no per-row Help disclosure or override-only filter. The default/source marker describes value origin, not ADORE-wide scope. Polling intervals, per-project concurrency, executor and recovery settings remain per-project. Global capacity and audit retention belong to Administration. No project setting is promoted into a global policy by this presentation.

Proof: web/e2e/settings.spec.ts project settings keep defaults and single guidance (administrator/developer), plus existing candidate edit/discard journey.

Offline Playwright verification runs serially with a thirty-minute global deadline,
default thirty-second tests, an explicit sixty-second statistics locale/theme
journey, ten-second assertions and no retries. A global timeout does
not establish complete proof even when every executed test passed.
Shell locale journeys await the exact successful language-save response before
closing a context, preserving the shared fixture's restored English preference.

### Transient application notifications

The application shows one dismissible notification for ordinary feedback or the current operation. Operation status replaces the queued confirmation. Pending/running operations stay visible until completion or dismissal; successful results and ordinary notices disappear after five seconds; failed and uncertain results remain until dismissed. Closing the banner keeps worker polling and final project refresh active. Replacement/unmount cancels earlier dismissal timers; persisted outcomes remain available in History. Error alerts retain their existing presentation.

Editable settings place **Edit** beside **Active value** in the value column, including narrow screens. Administrators retain candidate review/apply/discard and disabled-state safeguards; developers have read-only rows.

Project Settings purpose categories are collapsed on entry. Opening a category shows desktop description and control columns in a 3:2 ratio separated by 32px, with values/actions aligned to the right; below 640px they stack at full width. Native disclosures retain keyboard operation. Agent and model groups AI connection, the Pi provider, model, endpoint and launch command, closed Authentication (additional credential variables and Provider API key, or for a `chatgpt` project the ChatGPT sign-in panel `ChatGptSignIn.tsx` shown to Admins of a non-archived project) and external environment guidance. The panel shows the status, Sign in with ChatGPT (Sign in again unless not signed in), Disconnect ChatGPT (disabled while not signed in) and, while a sign-in waits, the OpenAI link (new tab, `noopener noreferrer`), a 15-minute validity note, the redirect address field, Complete sign-in and Cancel. The link and the address live only in component memory; the field is cleared on every attempt, and the panel rereads the status after every action. Its inline field editors retain the existing row columns and stack using the normal mobile layout; the credential-name dropdown and removable selections wrap within the value column.

## External executor environment seam

Settings uses `ContainerRuntimePicker.tsx` to list detected native and WSL
commands from the administrator-only `GET /api/v1/executor-runtimes` and to edit
the same draft manually on demand or when discovery is unavailable. Standard
WSL commands also resolve image suggestions. The reviewed Save flow owns all
configuration writes. Proof: `test_executor_environment_choice.py` and
`images.spec.ts`.

ExecutorEnvironment.tsx supplies a compact conditional container notice with four-locale external Dockerfile/build/profile instructions. Config GET returns the effective image and Admin-only resolved config path. Enrollment step 2 and Settings → Agent and model offer Runs in (container | local), Container runtime and Executor image with suggestions from `GET /api/v1/executor-images` (Admin, read-only; serverImages.ts) and local account fields; additional credential names are optional. Image building remains external; recipe attachment belongs to the export dialog. Mutation guards for the other environment keys precede all config writes and staging/application; the dedicated existing AI connection test is retained. The image-build routes are removed and answer 404. A pending candidate with an `image_build` binding or for an operator-owned key is 503 `pending_config_corrupt` on view and apply, and an administrator can still discard it. Focused proof: test_executor_environment_choice.py, test_web_pending_config.py, images.spec.ts, enrollment.spec.ts. Detailed ownership: project-images.md.

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

Connection and launch-command editing retain the right-hand control column, with row Cancel and one project Save bar.

Inline editor validation follows the controls/actions on its own flex line. Incomplete model or command edits keep the same control/action placement and disabled Save, while responsive wrapping remains shared.

Explicit native readiness returns closed Node/Pi diagnostic evidence; persisted
readiness keeps the boolean check contract. The local Settings UI exposes only
the current account and project tools PATH for native setup.

The four-locale repository connection browser journey waits for successful
language and theme preference writes before full document navigation. This
keeps the keyboard and narrow-layout proof independent of request timing.


### Exact API-candidate recovery

A valid pending candidate containing an API-only or hidden setting remains read-only in the row UI. Navigation is guarded throughout saving and confirmation, including read-only recovery with no local dirty fields. The one Save action rereads and compares the complete pending envelope, confirms its safe values and applies the exact existing candidate/base pair without preparing a replacement. Stale or corrupt evidence blocks Save and remains explicitly discardable. GUI-editable pending batches recover into visible editors and use bound replacement. Focused proof: `settings-save.spec.ts` API-only success/stale/corrupt cases and `test_web_settings_batch.py` collateral replacement preservation.

## Confirmed drift recovery

Job views expose SHA-256 state_revision. JobWorkspace offers four-locale confirmed Abandon and start again for failed jobs and suppresses Retry for stable execution-profile/settings drift, while volatile native Retry remains available. REST restart requires true confirmation, exact revision and existing grant/CSRF/idempotency boundaries. The existing queue target binds run ID plus state hash; CommandWorker rechecks actor/project identity, grants, failed lifecycle and revision before fixed CLI restart argv. CLI rechecks under lock. Changed incarnations are restart:job_changed; failures are localized with redacted bounded diagnostics. Proof: tests/test_drift_recovery.py, web/tests/jobs.test.mjs and web/e2e/driftRecovery.spec.ts. No stored schema change.

`forget_run_usage` serializes source deletion with composite usage/observation/cursor reset in one SQLite write transaction. Production projection calls recheck the current journal prefix inside their transaction, allowing appends and refusing stale sources. The CLI binds the deletion callback to the exact registered profile/config identity. Source-removal failure rolls back projection changes; other projects/users/audit are untouched. Proof includes a deterministic reader interleaving and fresh admission after projected old usage.

The worker maps successful restart summaries reporting a retained unproven older branch to four-locale success evidence. Help explains bounded fresh generations and naming-rule refusal, while known changed checkpoints continue to block cleanup.


REQ-REL-f206c815: missing/corrupt current budget limits never erase valid job evidence,
recovery controls or saved usage. Detail budgets report availability=unavailable,
closed config_missing/config_corrupt reasons and null limits/revision; the UI shows
— and localized guidance. Corrupt run evidence still fails closed. Metadata-only recovery is covered by
test_web_restart_requires_confirmation_revision_and_rechecks_worker. Limit derivation
AttributeError is classified without an untyped server error.

## Job operational evidence

JobWorkspace explains Working, parked-clarification and Failed states in all four locales, shows saved current-stage failures, and uses seconds in job times. Event stage projection reads explicit stage, stage context on usage/artifact events, or current destination on stage transitions. Unrelated events stay unassigned. Observed questions use ForgeMarkdown and shared local code/table scrolling.

The lazy authorized executor-output endpoint reads the last executor-artifacts host capture reference, never raw IO. executor_evidence.py validates exact run/attempt/context/digest/schema, bounded regular unlinked stable files and canonical diagnostics. Missing provenance/files are explicit; corrupt data is refused. No private/financial transcript content is returned to either role. Consumption errors offer an actual refresh action. Strict selected-run rereads avoid rescanning project history inside each projection transaction. Out-of-order usage projection snapshots are accepted only against verified fresh source/cursor prefixes without rolling back durable cursors. Relevant proof: test_web_jobs.py, test_web_metrics.py, test_pi_rpc.py, web/tests/jobs.test.mjs and focused issue35 browser journeys.


History projects ticket/job targets separately from queue IDs and reports actual terminal outcomes. Local CLI deletion receipts import once into the authorized audit view with crash uncertainty, immutable identity validation and explicit SQLite journal-mode checks. Completed import receipts retain only opaque keys.

Guided and portable enrollment check tokens expire after 15 minutes, are single-use
and bind administrator, draft and configuration. They retain measured workflow/checks
unchanged at creation, including not-inspected for a pending clone; only a later explicit
host check inspects the new clone. Pi thinking choices are validated against the bundled
pinned-model capabilities and applied to stages and model checks.

Readiness schema 3 includes a private machine/account binding, configuration-specific
prerequisite check set and required closed workflow enum. No aegis_files check is allowed.
Invalid schema/workflow or corrupt values fail closed even when stale and instruct the
operator to delete the profile readiness.json; bytes are never repaired or replaced. Managed credential changes invalidate prior evidence. The project list validates evidence before showing its verdict, and Repository access is neutral because CLI sign-in alone does not establish repository access.

A private authentication-context fingerprint binds managed, environment and CLI credential inputs; changes stale previous evidence. Probes recheck it under publication locks and reject old or corrupt readiness before replacing records. Public check sets declare required keys and the browser validates them.

Unobservable external CLI identity remains partial even if its probe passed; a validated
project-scoped credential is required for verified. Workflow never changes the verdict.
Guided, portable, exact-import and saved-project probes validate workflow and prerequisites
before evidence release or writes; malformed workflow returns readiness_probe_failed.
List requirements are independently derived from active config. Focused proof:
test_web_readiness.py, test_web_enrollment.py, test_repository_source.py,
test_web_transfer.py and test_web_import.py.

Factory administrator guidance: store initialization announces the initial credentials once; login and own-session reads derive a boolean from the current factory password hash. The authenticated shell shows a four-locale reminder with a link to My account until the password changes. Password changes and resets revoke sessions; the reminder periodically rechecks the current session while visible. Corrupt credential evidence fails closed. No schema changes.

Both own-password change forms mask current, replacement and confirmation by default, provide independent reveal buttons and explain the eight-character minimum. Mismatched confirmation stays in the form with a localized error and never reaches the API.

Add user and own-password change share the localized eye control. Add user
validates the confirmation on its identity step, discards it when advancing and
sends only the original password after review. Correct identity remasks the
password and requires repeating the confirmation.

The Users list opens one native dialog for Add user or Reset password. The
selected account is named in reset; both actions share password confirmation.
The reset result is acknowledged only after a valid response.

The project lifecycle browser fixture takes one authenticated, validated project
catalog snapshot and fulfills its local archive flag without an upstream proxy.
This keeps polling handlers deterministic when unrouteAll removes routing; all
CSRF, clone ownership and exact-name deletion assertions remain active.

Project Settings exports directly through the optional browser destination picker or ordinary download: complete container ZIP or exact native TOML. Recipe administration is separate under closed Technical details; cancellation and scope changes invalidate pending saves, and write errors abort before commit with localized feedback.

## Per-project publication approval

The PR/MR and review settings include the localized boolean **Require human
approval before PR/MR**. The existing Admin reviewed-save and idle-job rules
apply; the default requires approval and disabling it permits automatic
publication only after validation and freshness checks.

## Durable worker ownership

WK-01 queue ownership uses web schema 17 with explicit execution, configuration_project
and configuration_global domains, canonical resource keys, operation/owner generations
and role/project/run process participants. Register/claim/effect/finish calls require
explicit handles. Revoked actors or immutable project identity fail closed at claim and
before effects. Protected configuration candidates are queued only as opaque references
with explicit project ID or explicit global None; the existing CLI bridge cannot consume
them. Existing reviewed HTTP configuration application remains synchronous in this step.

Recovery inspects process creation identity outside writer transactions, then rechecks
owner/participant snapshots. Stale heartbeat, unknown liveness and shutdown requests do
not surrender live work; a live attached CLI child keeps a dead parent's claim protected.
Scoped registration retries re-inspect a previously retained owner, so eventual child
exit can be recovered without restarting the new supervisor. Finish/replay and state/Git/
forge effects reject old generations. Public operation transport excludes owner handles.

Start admission is confirmed only after saved state, ticket snapshot and picked evidence,
through the conductor admission callback before conduction; the job lifecycle remains
independent. Queue/claim/exit-zero alone are unconfirmed. Cancel succeeds only from saved
cancelled state. Six ownership/refusal codes have four-locale interface explanations.
Tests: test_web_ownership.py (barriers, independent connections, child death, revocation,
scoped configuration and CLI fencing), worker/audit/server/state/smoke/orchestrator tests,
and web/tests/operationReason.test.mjs plus help.test.mjs.



Actual conductor and publication scopes acquire a unique run-role owner for the
immutable project/run, with child-process creation evidence and an independent child
heartbeat. Manual Start admission persists the exact run-owner ID/generation on its
operation before acknowledging. The child verifies both command/project and active
run owners before effects; completed scopes relinquish only their own run role.
Retry/Restart and automatic conduction/publication use the same run-scope hook.
A child heartbeat failure refuses subsequent effects; missing heartbeat never permits
another process to steal the run. Invalid child transport cannot create a missing store.


Retry/Restart acquire their canonical run role before the CLI handler, covering
validation, reset and resource teardown as well as conduction/publication. A command
already owned by that exact run handle reuses it and retains it through fenced
completion. Claims defer another active run owner; effect authorization requires
explicit proof of any separate run handle held by the child. Historical owner
records and configuration-domain identity validate before mutation. SQLite faults
become typed ownership-store errors; parent and child heartbeat failure is explicit.
Linux missing boot or masked-live-process evidence is unknown, preserving ownership.
Recovery compares process snapshots in canonical PID/birth order.


An attached command pins its immutable request fields once and selects the run proof
by the canonical command run ID, including during nested Restart reconciliation.
A run-role command binds engine.owned_run_id so reconciliation skips unrelated runs
before handoff/cancel/outbox effects. Project-owned reconciliation stays unchanged;
capacity always counts all working jobs in that project. Completion verifies owner
project/domain/run scope and validates the persisted operation again.


Existing-store schema/audit checks use autocommit reads; only fresh initialization
(or waiting to recheck a schema-0 store being initialized) takes the initialization
writer lock. Corrupt existing history remains refused. Owner history is read and
validated outside the writer transaction; registration compares its latest validated
snapshot through an indexed generation lookup before inserting the successor.
The current unique owner/resource indexes are validated at open. Deterministic
held-projection tests prove another role can commit a heartbeat before validation
is released, without replacing real SQLite writes with mocks.


Delayed fresh-file observations and schema-zero waiters re-read under the initialization
lock and release it immediately once another initializer has committed a nonzero schema.
They then validate existing history without writer ownership. An existing schema-zero
store is refused without rebuilding, changing bytes or recreating accounts.

## Run-scoped engine authorization

WorkerContext binds the engine's run_available check to durable process
ownership and retains live/uncertain foreign owners even when a run lock is free.
A run-role context with no operation claim authorizes only conduct for its exact
project/run. Project-role autonomous polling remains separate. Public proof is
in test_web_ownership.py and test_run_concurrency.py; supervision dispatch uses
the conductor's admission-only and single-run interfaces independently.
