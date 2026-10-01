<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web interface

## Routing

Use this page for `adore-web`, `adore-web-worker`, `/api/v1`, web login/RBAC,
React views, the web queue, or offline web media. Start at
`04_Software/adore/web/app.py` for API behavior and
`04_Software/web/src/App.tsx` for UI behavior. Focused tests are
`04_Software/tests/test_web_*.py`. Engine internals belong to `orchestrator.md`.

## Purpose and boundaries

The optional web package gives one ADORE host an authenticated dashboard and
durable control queue. The API reads existing profiles and run state and never
launches an executor directly. The separate worker executes fixed CLI commands;
the orchestrator still owns readiness, locks, approvals and draft publication.

## Public interface

- `create_app(home, probe_runner=...)` mounts `/api/v1` and bundled static
  assets. The runner is injectable for explicit host-readiness probes.
- `adore-web --home ...` binds loopback; remote traffic uses a TLS proxy.
  Uvicorn accepts forwarded context only from loopback proxy peers, and HTTPS
  login emits a Secure session cookie.
- `adore-web-worker --home ...` polls profiles and queued operations.
- `WebStore(home / "web.db")` owns accounts, sessions, grants, audit and queue.
- `02_Tools/package_web_offline.py` creates a host-matched delivery directory;
  `install_web_offline.py` installs from local wheels only.

## Invariants

- Fresh identity stores bootstrap `admin` / `admin` once with an Argon2id hash.
  A corrupt or deleted initialized store does not recreate the default login.
- Schema 6 stores optional per-account language and theme. Authenticated
  preference reads and CSRF-protected partial updates remain account-scoped;
  null values use the browser fallback and corrupt rows fail closed.
- Developer routes check membership before reading a project and omit all
  financial fields. Project configuration reads return redacted effective
  settings to assigned developers; other project identities return 404.
  Configuration mutations, account management and global metrics require admin.
- Schema 7 binds grants to immutable profile IDs. Older creation-stamped grants
  migrate only while they still match the original profile; name-only grants
  are cleared. Schema 9 binds rates to project IDs, retaining older rates
  without applying them if their profile ownership cannot be proven. Schema 8
  binds queued operations to project IDs and marks
  unprovable legacy pending work uncertain. Renames retain grants and queued
  targets, while a reused name cannot inherit either.
- Mutations require CSRF; sessions are opaque, expiring and revocable.
- Administrator password reset revokes target sessions. Config reads omit
  credential-looking fields; journal views use a role-aware field allowlist.
- Web config edits use a SHA-256 revision and the same per-directory process
  lock as CLI `config set`; direct host file changes do not use that lock.
- The administrator UI stages one validated config candidate per project,
  reviews its revision and applies it only with no active run, conductor or
  queued operation. Identity/runtime edits require paused pickup. Retrying an
  interrupted apply reconciles exact candidate bytes and profile labels.
- Explicit administrator readiness checks use bounded doctor probes from the
  API host and return booleans only. AEGIS file presence is checked without
  executing repository code. A configured local OpenCode model is tested from
  a disposable executor container with the project egress policy and a
  redacted reason. WSL runtime detection remains unverified; CLI output and
  credentials are never returned.
- The OpenCode local-endpoint form saves `provider/model`, URL, and an optional
  allowlisted credential environment reference atomically;
  its compatible provider override, bounded timeout and optional HTTPS CA path
  are generated in the same config revision. Pending review exposes only these
  non-secret endpoint fields.
- Project creation and shared config validation permit ADORE-managed host-auth
  staging only for OpenCode and Codex. Pi and Qwen use the non-staged choice;
  Pi can authenticate through an operator-provided, protected credential mount
  while `stage_host_auth` remains false.
- Web-created profiles use an absolute, project-specific worktree root under
  ADORE home. ADORE uses the configured agent identity for host-side checkpoint
  commits, even when the fresh clone has no local Git identity.
- The audit trail is available only on the administrator API and page.
- The Jobs UI uses `/projects/{name}/runs-page` with a 25-item response and
  exact lifecycle/stage/observed-executor, inclusive UTC last-update date, and bounded outcome
  text filters; grants and corrupt-state checks precede data. Malformed or reversed date inputs fail;
  corrupt persisted update timestamps fail closed when date filtering is used.
  The overview requests seven recent runs plus unfiltered lifecycle counts.
  Its summary cards expand into a project table or a selected-project job table;
  expanded job tables request authorized full run history and paginate locally.
  The project selector is inside the Projects expansion on Overview. The
  Projects page itself uses sortable, paged authorized rows and per-row
  administrator pickup/archive actions with scoped details for all roles.
  Administrators open Add project as a separate page with localized field help.
  The clone path refers to an existing Git clone on the ADORE host. Editable
  image suggestions are examples, not a local-image inventory. Success opens
  project details; Back and Cancel return to Projects without a mutation.
  Pending and completed human handoffs have localized lifecycle labels and
  filters. Cancel is unavailable during and after human ownership transfer.
- The React session switch clears private caches and increments a generation
  guard so in-flight responses from the previous account are ignored.
- Project daily CSV exports follow the same financial filter as metrics JSON;
  the global daily CSV is administrator-only and includes project/repository
  provenance with spreadsheet-safe repository labels.
- Project/global metrics JSON and CSV share inclusive local-date `day_from`/`day_to`
  filters, an IANA timezone and day/week/month grouping. UTC/day is the default.
  The `period` object sums selected dated journal buckets; `totals`,
  coverage, run rows and revision attribution remain all-time. Summary-only
  usage is not fabricated into daily buckets, and developers receive no money.
  Completed-job trends use terminal lifecycle evidence rather than a later
  recovery checkpoint event; legacy journals fall back to stored run update time.
- Project/global metrics expose terminal elapsed-time sample count, average
  and median separately from event-based throughput. The period duration
  sample uses local completion day. Missing timestamps are excluded; corrupt
  persisted spans fail closed. Elapsed time includes human waiting.
- All-time quality cohorts count one job per review, first validation and
  human merge. Reviewer rework requires a `revise-label` revision after an
  observed MR/PR opening/adoption; pipeline repair remains separate. Null rates
  represent empty denominators, and malformed validation verdicts fail closed.
- Stage failures and operator retries are distinct quality counts.
  Administrator cost-efficiency averages use reported and estimated money in
  separate completed and human-merged evidence cohorts; developer responses
  contain no monetary efficiency fields.
- Project/global attributed usage JSON and CSV group journal events by the
  selected local day/week/month,
  executor and model with exact identity filters. Job counts remain separate;
  missing identity stays unknown, developer exports omit money, and CSV labels
  are spreadsheet-safe. Corrupt persisted identity fails closed.
- Schema-11 SQLite usage and launch-coverage projections are reconciled against retained journals
  before attributed reads. An administrator can explicitly replay archived and
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
- Offline installation verifies the manifest and runs `pip --no-index`.
- About exposes bundled project license text and versioned third-party notices.
- Below 760px, primary navigation opens from a labeled collapsible menu and
  closes after page selection. Narrow panels wrap text while data tables keep
  their own horizontal scrolling.

## Change map

| Change requested | Start with | Focused verification |
|---|---|---|
| Accounts, sessions, queue | `adore/web/store.py` | `test_web_auth.py`, `test_web_commands.py` |
| API permissions/config/metrics | `adore/web/app.py` | `test_web_rbac.py`, `test_web_config.py`, `test_web_pending_config.py`, `test_web_readiness.py`, `test_web_metrics.py` |
| Worker execution | `adore/web/commands.py` | `test_web_commands.py` |
| Language, theme, views | `web/src/App.tsx`, `web/src/i18n.ts` | `npm run build`, browser check |
| Offline media | `02_Tools/*web*.py` | `test_web_package.py`, installed HTTP smoke |

## Key behaviors

- `REQ-SEC-9ee171c9` - local accounts and durable, fail-closed sessions.
- `REQ-SEC-59d97c68` - project scope and developer financial privacy.
- `REQ-FUNC-7ce5b17a` - project setup, config and status.
- `REQ-FUNC-f9946b6b` - durable selected-ticket operations and admin pickup.
- `REQ-FUNC-448cbde7` - observed usage, reported/estimated costs and coverage.
- `REQ-UX-749d37c8` - four locales, themes and responsive UI.
- `REQ-UX-66e6f3f5` - project details presents collapsible, guided settings with administrator editing.
- `REQ-SEC-c2298428` - redacted project configuration reads follow grants; edits remain administrator-only.
- `REQ-PLAT-a1b60ff9` - host-specific offline installation.
- `REQ-REL-94e653aa` - checkpoint-bearing state and handoff lifecycles remain
  readable and protected after replacement of the DCP runtime.

## Architecture

```mermaid
flowchart LR
    browser([Browser]) --> api[create_app]
    api --> identity[(web.db)]
    api --> profiles[(ProfileStore)]
    api --> state[(StateStore)]
    api --> assets[(Bundled React assets)]
    worker[CommandWorker] --> identity
    worker --> cli([ADORE CLI])
    cli --> conductor[Orchestrator]
    conductor --> state
```

One web worker owns command ordering for one home. During any blocking engine
command or project poll, the worker watches queued cancellations across projects and
signals the active conductor after rechecking grants. Other queued operations
wait for the current engine command. Administrator metrics attribute usage and
reported/estimated cost to the most recent revision-started event in each run;
initial work remains in run totals and developers receive no financial rows.
API liveness at `/api/v1/health` is separate from readiness at `/api/v1/ready`.
The worker refreshes a schema-5 SQLite heartbeat even while an engine command
blocks; a stopped, stale or corrupt heartbeat does not claim readiness.
Administration expands into System status, Users, Audit and Settings sidebar
pages; developers keep a My account page. Project details shows effective
configuration in compact sections with field type, domain and purpose help;
administrators stage configuration, endpoint and price changes there. The
settings response is scoped to the current project identity so switching
projects cannot briefly show another project's values. Audit policy defaults to unlimited
and allows administrators to set day and stored-text byte limits. Schema 12
prunes oldest events transactionally when configured while preserving other
history. Audit and other long tables provide 10/25/50/All paging; Jobs uses
the scoped run-page API for the same choices. API fetches bypass browser cache
so a newly deployed endpoint cannot be masked by stale HTML.
The Administration System status page polls readiness every five seconds and labels worker
status separately from forge, executor and model reachability.
It also polls administrator-only storage status every 30 seconds. The API reads
free space for home and each project state root, warns below 1 GiB and returns
an explicit service error if measurement fails, without exposing host paths.
The React About dialog makes the surrounding shell inert, keeps keyboard focus
on its Close button, and restores focus to About when closed. Narrow layouts
expose Sign out in the top bar while the sidebar account row is hidden.
The top bar supplies the sole page title and the project selector on scoped
pages outside Overview and Projects; responsive rows
keep these controls visible while content begins with page data. Metric hints,
usage actions and account rows wrap on narrow screens.
Metrics keeps the common reporting range, timezone, grouping and CSV menu above
keyboard-operable Summary, Usage, Quality, Trends and administrator-only Projects
tabs. Developer export choices remain project-scoped and omit money; usage
exports also carry the Usage tab's executor/model filters. Compact layouts put
the shared reporting controls in two rows.
Session clearing also returns the shell to Overview, preventing a blank
administrator-only page after a developer signs in. Successful asynchronous
user creation and config staging reset their forms without a false error.

## Files

- `04_Software/adore/web/{app,store,commands,server}.py` - API, SQLite store,
  worker and listener.
- `04_Software/adore/web/static/` - bundled local UI and license.
- `04_Software/web/` - React source and build configuration.
- `02_Tools/{package_web_offline,install_web_offline,launch_web,stamp_web_assets}.py`
  - offline media and static asset preparation.
- `04_Software/tests/test_web_*.py` - focused API, pricing, worker and packaging tests.
