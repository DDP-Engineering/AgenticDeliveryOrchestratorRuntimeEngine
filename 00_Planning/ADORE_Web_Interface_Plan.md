<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE web interface plan

Date: 2026-09-29
Status: Implementation in progress; owner decisions updated 2026-09-29.
Scope: Approved implementation plan. Publication remains governed by the
repository's AEGIS delivery workflow.

## 1. Recommendation

Add a React/TypeScript web application and an optional FastAPI service around
ADORE's existing Python engine. Keep the CLI useful and preserve the existing
forge adapters, executor launchers, run state, and human merge boundary.
Resolve the separate pre-publication approval policy explicitly before changing it.
Introduce the web interface incrementally: authenticated visibility first,
configuration and controlled operations next, then reliable usage analytics.

Simple local username/password accounts are sufficient for the initial scope.
Store salted password hashes, preferably Argon2id, rather than plaintext or
reversibly encrypted passwords. Users still have an ordinary password login;
the application has no reason to recover their original password. Forge and AI
credentials are a separate problem because the runtime must use those secrets.

The main engineering work is coordinating web/CLI/runtime writes, enforcing
project access throughout the API, and collecting trustworthy usage data.
The dashboard itself is only one part of the change.

## 2. Requested scope and working assumptions

**STATED by the user:** easy configuration; status and statistics; React as a
candidate frontend with FastAPI; minimal login and user management; platform
administrator and developer access; project-scoped visibility; repository,
job, token, cost, and MR retry analytics over time; English, French, German,
and Romanian; light/dark/system themes; an About dialog with version and
license; self-contained deployment; usable small and large displays.

**CONFIRMED follow-up decisions (2026-09-29):**

- A fresh installation creates the platform administrator with username `admin`
  and initial password `admin`.
- Developers can start, retry, and cancel jobs in their assigned projects.
- Developers do not see project costs. Financial data is administrator-only.
- Installation should require no Internet downloads.
- Preserve existing executor choices and subscription-based testing, including
  the current ChatGPT/Codex host-auth path; support API keys and local endpoints.
- ADORE creates draft MRs/PRs automatically; humans perform review and merge.
  The existing separate pre-publication approval stays in place.
- Support Windows and Ubuntu as deployment targets.
- Administrators can configure dated prices to estimate costs when a provider
  reports token usage without monetary cost. Estimated and reported amounts
  remain separate.

**PROPOSED defaults, not confirmed decisions:**

- One organization and one execution host initially, with multiple project
  profiles and an internal HTTPS deployment.
- Platform administrators manage installation settings, users, project
  memberships, profiles, and runtime operations. Developers have assigned-project
  visibility and start/retry/cancel controls. Configuration and project-wide
  pickup pause/resume remain administrator-only unless expanded explicitly.
- Existing candidate-bound publication approval remains the runtime contract.
- One UI project maps to one ADORE profile. A repository can have several
  profiles; repository totals deduplicate repository identity.
- Offline installation media contains the built UI and application dependencies;
  host prerequisites must be preinstalled or supplied in an offline prerequisite
  pack. Node.js is needed to build the frontend, not to run the delivered bundle.
- USD remains the initial cost accounting unit, with localized formatting.
- Basic lifecycle/retry metrics arrive early. The first complete release also
  includes usage coverage, daily project/repository totals, and cost trends.

**UNKNOWN:** deployment exposure and offline host prerequisite scope. Windows and
Ubuntu, a first-release target of up to 10 users and 20 projects,
OpenAI-compatible HTTP as the first local endpoint, indefinite retention with
manual backup, offline installation, and the retained pre-publication approval
are confirmed. Fully offline operation has not been requested. See section 12.

## 3. Current implementation and gaps

These are repository observations, not claims of implemented web support.

| Area | OBSERVED evidence | Planning consequence |
| --- | --- | --- |
| Python package | `04_Software/pyproject.toml` declares Python 3.11+ and an empty runtime dependency list. | Keep web dependencies optional so CLI-only installation remains lightweight. |
| Profiles | `04_Software/adore/profiles.py` stores profile metadata, TOML configuration, and a CLI active-profile pointer. `05_SoftwareDocu/Component_Profiles.md` identifies absent cross-process profile locking. | Reuse validation/storage concepts, add coordinated writes, and address every web request to an explicit immutable project ID. Never use the global active-profile pointer for a user's selection. |
| Run ownership | `04_Software/adore/state.py` and `orchestrator.py` implement durable state/journals and one conductor lock per state root. | HTTP requests must not become competing conductors or edit run JSON directly. |
| Operator commands | `01_Documentation/CLI_Reference.md` describes pause/resume, retry/cancel, reset/delete, cleanup, and lock behavior. | Preserve their semantics. Pause stops new pickup; it does not cancel active work. |
| Metrics | `04_Software/adore/metrics.py` has SQLite terminal-run summaries, journal-based reports, CSV, and static HTML. | Reuse existing facts while adding live projections, cross-project queries, and daily usage records. |
| Usage | `04_Software/adore/executor/launcher.py` parses OpenCode usage and provisional Codex usage; the base parser returns zeros. `orchestrator.py::_journal_usage` writes only enabled, nonzero usage. | A zero today cannot reliably distinguish free work, absent telemetry, disabled capture, or unsupported output. Audit every supported executor and label coverage. |
| Review effort | `RunState.review_rounds`, `revision-started` events, and stage failure events exist. | Distinguish review revisions from execution retries and publication transport retries. |
| Credentials | `01_Documentation/Security_And_Credentials.md` separates host forge credentials, executor keys, and non-secret profile settings. | Web responses must preserve these boundaries; configure secret references initially. |
| Deployment | Existing guidance covers Windows and Linux; runtime supports multiple container runtimes. | Choose the first web packaging target explicitly without introducing OS-specific core-loop logic. |

The current CLI metrics are deliberately best effort. New web analytics must
represent gaps explicitly; changing legacy metric defaults is a separate
compatibility decision, not an incidental frontend refactor.

## 4. Proposed architecture and ownership

| Component | Responsibility | Boundary |
| --- | --- | --- |
| React + TypeScript frontend, built with Vite | Navigation, forms, tables, charts, translations, themes, preferences. | Receives authorized API data; never accesses runtime files or credentials directly. |
| Optional FastAPI application | Authentication, authorization, typed API contracts, validation, queries, command submission, bundled static assets. | Same-origin `/api/v1` and UI; no orchestration loop tied to HTTP request lifetime. |
| Shared Python application services | Reusable config validation, profile operations, status queries, operation contracts. | Thin adapters for CLI/API; core modules do not import FastAPI. |
| Dedicated local control worker | Processes durable authorized commands and supervises project conductors. | Owns runtime privileges; one conductor per state root; independently restartable from the API. |
| Web database, initially SQLite | Users, sessions, memberships, stable project registry, audit records, command queue, preferences, analytics projections. | A local persistent volume; versioned migrations and explicit backup/restore. |
| Existing profile/config/run stores | Authoritative operational configuration and durable execution history. | Web projections do not replace ADORE state or AEGIS journals. |

React with a build tool is suitable here because the proposed interface is an
authenticated application backed by an existing Python system; there is no
identified server-rendering or SEO requirement. Routing and data fetching still
need explicit choices. Start with React Router and a query cache library only
where it simplifies refresh/invalidation. See the [React build-tool guidance](https://react.dev/learn/build-a-react-app-from-scratch).

FastAPI supports multiple server processes; consequently, API startup must not
implicitly start a conductor in every process. Keep durable jobs in the control
worker rather than request-scoped background work. This is our architecture
choice, informed by [FastAPI server workers](https://fastapi.tiangolo.com/deployment/server-workers/)
and [background task guidance](https://fastapi.tiangolo.com/tutorial/background-tasks/).

### Commands and concurrent configuration

- A mutating request validates role, project membership, payload, operation
  allowlist, and expected resource version; commits an audited command; then
  returns its operation ID. The browser can safely reconnect and poll it.
- Developer start/retry/cancel applies to any job in an assigned project,
  regardless of who started it; record the actor. Proposed Start semantics:
  enqueue a selected eligible forge ticket through normal claim/readiness and
  capacity checks, with duplicate-active-job prevention. It must not toggle
  project-wide polling, bypass hold/exclude controls, or accept shell commands.
- Commands carry actor/project/run IDs, idempotency key, expected state/version,
  timestamps, and bounded execution/retry limits. The worker rechecks authority
  and preconditions before an unstarted command executes. Revoked users cannot
  leave executable queued commands behind.
- Queue states distinguish pending, running, succeeded, failed, cancelled, and
  uncertain outcome. A crash after an external side effect needs reconciliation
  against durable evidence before retry. Do not promise exactly-once delivery.
- Preserve the conductor lock. Design safe command consumption at bounded
  control points; never delete a live lock to make retry/cancel work. Measure
  cancellation latency and distinguish requested from completed cancellation.
- CLI mutations and web mutations must share coordination. Direct host file
  edits are detected through config revision hashes and require reload review;
  they are not silently overwritten by a stale form.
- Configuration follows validate -> show changes -> save pending revision ->
  apply at a documented safe boundary. A running job retains its effective
  config revision. Identity, paths, and credential changes require a controlled
  restart/reconciliation policy. These guarantees require backend work.
- Preserve TOML as the operational config source. Decide and test the writer's
  treatment of comments and unknown keys; import must show any lossy rewrite.
- UI removal archives a project by default, retaining audit and cost history.
  Destructive state deletion remains a separate explicit administrator action.
- Begin with bounded polling and visible last-refresh time. Add server-sent
  events only if measured refresh needs justify it; reconnect and authorization
  revocation must still work correctly.

### Suggested implementation layout

- `04_Software/adore/web/`: optional API, authentication, RBAC, web persistence.
- `04_Software/adore/services/`: shared use cases where extraction is justified.
- `04_Software/adore/control/`: worker and durable command coordination.
- `04_Software/web/`: frontend source, local assets, locale catalogs, UI tests.
- `04_Software/adore/web/static/`: packaged frontend build output.
- `04_Software/tests/`: offline backend, contract, authorization, and worker tests.
- `04_Software/deploy/`: supported launch/service/container definitions.
- `02_Tools/`: build and packaging automation; `07_Delivery/`: generated bundles.
- `01_Documentation/`: installation, administration, configuration, and user guides.
- `05_SoftwareDocu/`: component contracts based on the existing template.

These are proposed locations, not directories created by this planning task.

## 5. Login, users, and RBAC

Local accounts: administrator creates users, assigns project memberships,
disables accounts, and initiates password resets. Users change their own
password and preferences. Start without public registration, email delivery,
SSO, or an enterprise identity service.

On a fresh installation, create the initial platform administrator with username
`admin` and password `admin`, as requested by the owner. Store a salted password
hash, using the same mechanism as every other account. Initialize this account
once in a transaction; restarts, upgrades, and restores must preserve existing
accounts and changed passwords. A corrupt identity database is an error, never
a reason to recreate the default login. Provide a local audited recovery
procedure and protect against removing the last active admin.

Recommendation: require changing the initial password on first login before
normal administration. This first-login restriction is a proposed safeguard,
not a confirmed owner decision; the initial credentials themselves are confirmed.

Use an established Argon2id implementation with unique salts, bounded login
attempts, generic authentication failures, and password lengths compatible
with passphrases. Password hashing differs from reversible secret storage;
see [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).

Use opaque server-side sessions in HttpOnly, Secure, SameSite cookies, with
CSRF protection for state changes, session rotation, idle/absolute expiry,
and revocation on logout, disablement, or password reset. Do not store browser
bearer tokens in local storage. Keep TLS on every non-loopback login route.
See [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
and [CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

| Capability | Platform administrator | Developer, proposed v1 |
| --- | --- | --- |
| View projects and run state | All projects | Assigned projects only |
| View sanitized job logs and MR/PR links | All projects | Assigned projects only |
| View operational metrics and token counts | Global and per project | Assigned projects only |
| View costs, prices, budgets, or financial exports | Global and per project | No |
| Configure platform, executors, and projects | Yes | No |
| Manage accounts and membership | Yes | No |
| Start/retry/cancel jobs | All projects, through controlled commands | Assigned projects, through controlled commands |
| Pause/resume project pickup; reset/delete/cleanup | Yes, with explicit scope | No |
| Change own password, language, and theme | Yes | Yes |
| Approve before publication | Existing forge authority and candidate-bound gate | Existing forge authority and candidate-bound gate |
| Merge MR/PR | Human action on the forge | Human action on the forge |

Enforce authorization server-side on list, detail, log, chart, count, export,
and operation endpoints. A hidden navigation item is not an access boundary.
Cross-project IDs must not expose even titles or aggregate counts. Cache keys
include authorization scope; membership changes invalidate access immediately.
Map a run to its registered project before opening its storage path.

Financial visibility is a backend policy, not just a hidden chart. Developer
responses, exports, logs, timelines, notifications, and operation errors exclude
monetary amounts, pricing tables, and financial budget values. Supply sanitized
structured log views; raw executor artifacts may contain cost fields and remain
administrator-only unless their filtered representation is proven safe. A budget
failure may expose a generic operational reason without the monetary threshold.
Token counts remain operational metrics; this policy prevents disclosure of
stored financial data, not independent estimates from publicly known prices.

Use stable project IDs independent of renameable profile labels. Prevent two
project registrations from mapping the same state root to different access
policies. Canonicalize and constrain paths and reject traversal/symlink escapes.

Runtime credentials initially remain in existing approved host stores or
environment files. The web UI shows credential reference/readiness, never the
secret value. A later write-only secret-entry UI would require a reviewed
storage/key-rotation/backup design with encryption keys held separately from
ciphertext. Executor transcripts and exports require sanitization; do not
expose arbitrary host files or a shell terminal.

## 6. Pages and user journeys

| Page | Main content and actions |
| --- | --- |
| Login | Username/password; clear session-expired feedback; language/theme choice. |
| Overview | Authorized project count, active/parked/failed/approval-wait jobs, recent activity, usage coverage, actionable failures. Admin sees global health. |
| Projects | Search/filter; project readiness, forge/repository, runtime, executor, last activity; administrator add/import/archive actions. |
| Project details | Status, jobs, settings, membership, project metrics, and forge links; tabs follow permissions. |
| Jobs | Paginated/filterable list by project, lifecycle, AEGIS stage, executor, date, and outcome. Lifecycle and AEGIS stage remain separate. |
| Job details | Durable timeline, current stage, attempts, questions/approval state, sanitized logs, validation outcome, usage, review rounds, MR/PR link, permitted operations. |
| Metrics | Time range, reporting timezone, project/repository/executor/model filters; token trends, throughput, duration, rework, coverage, and scoped CSV export. Costs, prices, budgets, and financial exports are administrator-only. |
| Administration | Users, membership, platform defaults, runtime readiness, pending configuration, retention, and audit history. |
| Preferences / About | Language, light/dark/system theme; runtime/frontend build version, product name, exact project license text and third-party notices. |

Configuration journey: choose/import a project -> identify forge and repository
-> register workspace and existing credential references -> select runtime,
image, executor/model, and egress -> set bounded run limits -> validate -> review
changes -> save -> explicitly enable pickup. Existing config imports start
disabled until readiness is confirmed. No automatic project job starts merely
because a form was saved.

Reuse `config.py` validators and `doctor.py` probes behind application services;
avoid duplicating their rules in JavaScript. Field errors use stable codes and
localized explanations. Network/credential probes are explicit actions with
timeouts; a syntax check does not imply live readiness.

Version and license information comes from release/package metadata and the
repository license file. Keep the Python release declarations aligned and
derive the frontend build version from that release during packaging.

### Automatic draft creation versus human merge

The current implementation follows this sequence: ADORE builds and validates
the candidate -> presents evidence on the source ticket -> a human freshly adds
`agent-approved` -> ADORE pushes and creates the draft MR/PR -> a human reviews
and merges on the forge. Publication approval is that earlier permission to push
and expose the candidate; it is separate from MR approval and merge. See
`01_Documentation/Configuration_Reference.md`, Delivery and Review, and
`04_Software/adore/orchestrator.py::_present_for_approval`.

The owner confirmed the current candidate-bound pre-publication approval gate.
ADORE therefore keeps the existing sequence for initial drafts and revisions;
review and merge remain human actions on the forge.

## 7. Metrics and honest cost accounting

### Definitions before charts

| Metric | Proposed meaning |
| --- | --- |
| Projects / repositories | Project count is registered profiles; repository count is unique canonical forge host + repository identity. Archived history remains queryable. |
| Jobs | ADORE runs, keyed by project + run ID. Stage attempts and review rounds are separate dimensions, not additional jobs. |
| Daily jobs | Count starts and completions separately by their actual timestamps; active jobs are a point-in-time count. |
| Tokens | Input/output and supported cache/reasoning categories with explicit accounting semantics per provider. Missing telemetry is unknown, not zero. |
| Cost | Separate provider-reported cost, estimated cost, unknown cost, and any later reconciled billed amount. Show currency and evidence/coverage. |
| Stage retry effort | Failed attempts and repeated launches per stage; separate infrastructure failures, validation failures, and clarification waits. |
| MR/PR rework | Existing review revision rounds and their trigger, plus attributed tokens/cost/time where available. Publication network retries are separate. |
| Quality indicators | First-pass validation rate, jobs needing review rework, failures, human merge outcome, and lead time; each with a defined eligible population. |

MR retries are an indicator of rework, not a standalone code-quality score.
Compare similar work and show sample sizes. Keep first validation outcome as
an event; the existing final governance outcome cannot prove first-pass success.
Report jobs with at least one revision divided by jobs that reached review;
show still-open cases separately. For an eventual first-pass merge measure,
use completed human-merged jobs with zero review revisions and state that cohort.
ADORE observes human merge results and continues to never merge itself.

### Usage collection and attribution

Introduce a versioned append-only normalized usage event contract containing:

- Event identity, schema version, project/repository/run IDs, launch/attempt ID,
  AEGIS stage, review round, executor, provider/model, and event timestamp.
- Input/output token counts and supported cache/reasoning counts, including
  whether categories overlap. Never blindly add cached tokens twice.
- Nullable reported cost and currency; nullable estimated cost, pricing-version
  reference, and the source of that estimate.
- Coverage/status (`reported`, `estimated`, `unavailable`, `disabled`, `partial`)
  and source evidence reference. Coverage for tokens and money can differ.

Every launch records telemetry status, including zero and unavailable cases.
Define whether each executor emits incremental or cumulative usage and normalize
accordingly. Validate nonnegative finite values, schemas, timestamps, and
provider/model identity. Corrupt data is flagged/quarantined with typed errors;
it must not masquerade as a trustworthy zero or reset runtime state.

Index events incrementally into a central analytics projection. Unique source
event identities, durable ingestion cursors, and reconciliation make replays
idempotent. New execution attempts legitimately add usage; reimporting the same
event does not. Keep legacy summaries separate from their reconstructed source
events so a dashboard cannot sum both and double-count them.

Store timestamps in UTC; apply the selected reporting timezone before daily
bucketing, including daylight-saving boundaries. Attribute usage to its event
time rather than the job's final day. If only a launch total is available,
book it at launch completion and label that granularity; do not invent an
hour-by-hour allocation for a job that crosses midnight.

Pricing is a dated, versioned rate table maintained explicitly, not a live
dependency on scraped public prices. Preserve historical rate versions and
handle missing model prices as unknown. Use decimal/fixed-point money arithmetic.
Provider-reported totals and estimates are alternative valuations of the same
usage, not additive costs. A subscription/OAuth run can have token usage without
known marginal billed cost; show this explicitly rather than calling it free.

Historical backfill reads retained journals and summaries without changing
execution state. It cannot recover unrecorded model identity or usage; show
unknown/partial coverage. Record observation freshness for running jobs since
the existing launcher generally reports totals after a launch completes.

Show daily/weekly/monthly trends, input/output totals, spending by project and
repository, job counts, rework cost, and cost per completed/human-merged job.
Every ratio states its denominator; an empty denominator yields unavailable.
Present token/cost coverage beside totals. Existing runtime limits remain
authoritative; estimates and delayed usage are not a guaranteed hard spending
cap. New global budgets would need a separately specified admission policy.

### Subscription, API-key, and local endpoint access

Keep the executor launcher abstraction: ADORE configures a compatible executor,
which talks to the selected model service. The UI does not call the model from
the browser or silently substitute a different executor/provider.

- **Subscription testing:** preserve the existing Codex host-auth test path.
  Authentication/reauthentication stays with the executor on the host; the web
  application does not collect a ChatGPT password or distribute login artifacts
  to developer browsers. Show token usage where available and label per-job
  billed cost unavailable unless supported evidence supplies it. Subscription
  fees are not automatically allocated as per-token API charges.
- **API key:** keep credential references, provider/model selection, and usage
  capture. Show reported costs or explicitly labeled estimates to administrators.
- **Local/custom endpoint:** add an administrator-managed endpoint profile with
  URL, protocol/API compatibility, model ID, auth reference where required,
  timeout, and TLS/custom-CA settings. Supply this through each executor's
  documented configuration mechanism; test supported combinations explicitly.
  An OpenAI-compatible label alone does not prove tool calling, streaming, or
  required API compatibility. No silent fallback to a cloud endpoint.

Codex supports ChatGPT sign-in for subscription access and API keys for
usage-based access, as described in the [official OpenAI authentication documentation](https://learn.chatgpt.com/docs/auth).
This confirms the distinction, not an entitlement for every deployment/account.

The current repository exposes model/command/env configuration and a Qwen
`OPENAI_BASE_URL` example, but no unified, verified local-endpoint UI contract.
Treat that integration as implementation work. In particular, the Codex launcher
ignores host user config; mounting host auth alone cannot configure a local model.

Endpoint readiness must be checked from the executor's actual container/network
context. Container localhost is not automatically the model server on the host;
configure a reachable address and compatible egress rules. Administrators allow
intended internal addresses; reject unsupported URL schemes and uncontrolled
redirects, and keep endpoint probes bounded. Local service availability and model
weights are explicit prerequisites, with no first-run model auto-download.
Local execution still consumes hardware resources; monetary cost stays unknown
unless an administrator explicitly configures an estimation policy.

## 8. Languages, themes, and responsive behavior

- Ship English (`en`), French (`fr`), German (`de`), and Romanian (`ro`) in the
  first complete release. Introduce message catalogs from the first screen.
- Persist user locale and theme; use browser/system preference before login
  and as fallback. Set document language and localize dates, numbers, plurals,
  validation errors, chart labels, empty states, and accessibility labels.
- Keep stored event/error codes stable and translate their display. Raw logs,
  repository names, task text, and source code retain their original language.
- Light and dark palettes use shared semantic tokens. System theme responds to
  OS changes; manual choices persist. Avoid a wrong-theme flash on startup.
- Use layouts driven by available CSS width rather than physical monitor size
  or pixel density. Small screens use collapsible navigation, stacked cards,
  table column controls, and dedicated details views. Wide screens gain useful
  columns/charts without stretching text into unreadable lines.
- Proposed viewport checks: 360px phone, 768px tablet, 1024x768 compact desktop,
  1366x768 laptop, 1920x1080 desktop, and 2560px/4K with OS scaling. Verify short
  viewport height and 200% browser zoom as well as width.
- Keyboard access, visible focus, explicit form labels, sufficient contrast,
  reduced-motion support, and chart/table alternatives are acceptance criteria.
  Status must never depend only on color. Review long German/French strings
  and Romanian diacritics in actual rendered pages.

## 9. Self-contained deployment and operations

Recommended initial delivery: an optional web-enabled Python package containing
the compiled frontend and an independent worker entry point. Provide a documented
single-host launch/service setup for the selected OS. A Linux container/Compose
distribution can package API and worker as separate services from the same
release image; its support priority depends on the deployment decision.

The browser loads fonts, scripts, icons, styles, and translations locally.
No CDN, hosted database, Redis, or Node.js runtime is required for the proposed
baseline. Self-contained UI does not mean the entire execution environment is
air-gapped: Git, forge CLIs, Docker/Podman/WSL, project images, AEGIS in target
repositories, credentials, and model access still need provisioning.

**Confirmed delivery requirement: installation makes no Internet downloads.**
Prepare a versioned, OS/architecture-specific bundle on a build machine, then
copy it to the deployment host. Include the built UI, backend and pinned Python
dependencies/runtime as appropriate, selected executor and forge tools, local
assets, license notices, and any required prebuilt container images. Never run
an online pip/npm install, image pull, or tool bootstrap in the installer or
defer those downloads to first startup. Missing prerequisites produce a precise
offline error instead of an attempted download.

The prerequisite manifest separates host OS/kernel/container-engine requirements
from application contents. Offer an offline prerequisite pack where supported;
otherwise require the listed versions to be installed beforehand. The exact
Windows/Linux and Docker/Podman prerequisite packaging remains to be selected.
Arbitrary project toolchains and local model weights are supplied separately as
prepared offline artifacts; a general ADORE bundle cannot include every project's
dependencies. Include checksums and verify package integrity before installation.

Acceptance: install and start from the delivery media on a supported clean host
with external network access blocked, including import of bundled images and
first load of every UI asset. This test must detect deferred downloads. Building
the delivery media may use the Internet; installing it may not. Offline upgrades
use the same delivery method. Running cloud AI or reaching a hosted forge still
needs network access. Fully disconnected operation would additionally require
local forge/model services and all project build dependencies to be available.

Keep the API without executor-runtime socket access where practical. The worker
holds execution privileges and required forge credentials. Mount the container
runtime socket only where explicitly required and document that trust boundary;
do not assume a web container alone can safely operate host worktrees. Exercise
path mappings and permissions on the chosen deployment target.

Use local-disk SQLite with transactional writes, busy timeouts, appropriate
concurrency settings, and consistent backups. Multiple execution hosts or
availability replicas would trigger a storage/queue redesign; they are not
silently supported by putting SQLite on a shared network filesystem.

Package health/readiness checks, worker heartbeat, graceful shutdown, bounded
restart/backoff, log rotation, disk-space alerts, migration checks, and a tested
backup/restore procedure. Back up web identity data, config, durable run state,
and audit/usage evidence consistently; projections alone are insufficient.
Sessions should be invalidated after recovery when appropriate. Upgrade and
rollback compatibility must be explicit and tested against supported versions.

Keep raw executor logs, run evidence, usage records, aggregates, commands, and
audit indefinitely unless the operator uses an explicit manual cleanup action.
Preserve history when a project is archived. Keep per-job iteration, wall-clock,
cost, and file-change limits and add
bounded API pagination, query windows, command retries, and global worker capacity.

## 10. Incremental delivery plan

### Capacity planning ranges

The following are illustrative workload bands for choosing acceptance tests,
not measured limits or guaranteed server capacities. Dimensions can vary
independently; many registered users/projects do not imply many active jobs.

| Planning band | Registered users | Simultaneous dashboard users | Registered projects | Simultaneous execution jobs |
| --- | --- | --- | --- | --- |
| Pilot | 1-20 | 1-5 | 1-10 | 1-2 |
| Small team | 20-100 | 5-20 | 10-50 | 2-5 |
| Department | 100-500 | 20-100 | 50-250 | 5-20 |
| Larger deployment | Above those ranges, or several execution hosts | Define measured workload | Define active polling fraction | Define host/model capacity |

Registered users mainly add account/membership records. Active viewers add
requests, log delivery, and chart queries: for example, 20 browsers making one
refresh request every five seconds generate four requests/second before other
actions. Paginated queries and incremental updates keep that load bounded.

Registered projects mainly add metadata; enabled projects generate forge polling
and reconciliation work even without jobs. At 50 enabled projects polled once
per minute, the baseline is 50 poll cycles/minute, each potentially containing
several forge requests. API limits depend on the actual forge/account and should
be measured, not guessed from repository count. Completed jobs, log volume,
retention, and query patterns determine analytics/storage growth.

Running jobs dominate executor CPU, memory, worktree disk and build I/O. Cloud
models add provider/session limits; local models add model-server GPU/RAM and
inference-throughput limits. Do not count a parked or review-waiting job as a
running executor. Several conductors can multiply load across projects; a
global admission cap must complement existing per-project bounds.

Confirmed first-release registration target: up to 10 users and 20 projects.
Validate at least five simultaneous dashboard viewers and one active execution
job on the selected host, then measure higher concurrency before increasing it.
Test UI/queue workloads with fakes independently from real executor throughput.
The current engine's concurrency setting is an admission check, not evidence of
parallel executor throughput; validate scheduling behavior before claiming this
target. The single-host API/SQLite design remains a candidate until measured.

Measure response latency, queue delay, database contention, forge request rate,
log ingestion, CPU/RAM/disk and recovery at the target workload. Set acceptance
budgets once hardware, job size, retention, and refresh cadence are defined.
Choose additional API processes, PostgreSQL, or distributed workers when those
measurements or multi-host requirements justify them, not at an arbitrary user
count. None of these ranges require a different frontend framework.

### Delivery phases

No calendar estimate is committed before deployment and permission decisions.
Each phase is a separately reviewable increment; effort will be concentrated in
phases 1, 3, and 4 because they touch runtime coordination and data contracts.

| Phase | Deliverable | Exit evidence |
| --- | --- | --- |
| 0. Resolve scope and contracts | Decide section 12; inventory reusable APIs; specify role matrix, project identity, usage schema, command semantics, and deployment target. | Reviewed requirements and design; explicit first-release boundaries. Start the normal AEGIS workflow when implementation is requested. |
| 1. Backend foundation and accounts | Optional web package, versioned API, local users/sessions, RBAC, project registry, shared service seams, database migrations. | CLI-only install works; login works; unauthenticated/cross-project/disabled-user access fails closed; backup/restore and empty bootstrap tested. |
| 2. Authenticated visibility | Responsive shell, all locale catalogs, themes, About, projects/jobs/timelines, sanitized logs, initial lifecycle/rework metrics. | Two developers see disjoint projects; admin sees all; browser refresh/reconnect preserves correct status; no mutation permissions leak. This is the internal visibility milestone. |
| 3. Configuration and operations | Import/create/configure projects, endpoint/auth profiles, readiness checks, memberships, durable worker; admin pickup controls and developer/admin start/retry/cancel. | Concurrent edits conflict safely; duplicate submissions do not duplicate effects; project bounds and revocation hold; subscription/API/local endpoint fixtures pass; no silent cloud fallback. |
| 4. Usage and analytics | Executor telemetry coverage, normalized usage events, daily aggregation, versioned pricing, trends, exports, historical backfill. | Known fixture totals reconcile by run/project/repository/day; replay adds nothing; missing usage remains unknown; revision cost and midnight/DST cases are correct. |
| 5. Release readiness | Offline deployment media and prerequisites, upgrades, restore rehearsal, translations, accessibility/layout review, operator/user/component docs. | Network-blocked install/start and upgrade/restore smoke checks; workload checks at agreed scale; full offline suite and strict AEGIS validation. This completes the requested v1 scope. |

Defer SSO/MFA integration, public registration, arbitrary custom roles,
multiple organizations, multi-host dispatch, billing-provider reconciliation,
web-based publication approval, and a shell/terminal interface unless requested.
Local password security, RBAC, complete v1 languages/themes, and honest telemetry
are baseline work, not deferred polish.

## 11. Verification and documentation

Every new public behavior gets a happy-path test and negative tests at its
trust boundaries, following repository rules. Use fake command runners and
fixtures; unit/integration suites stay offline with no real forge/git/container
commands. Live installation/credential acceptance is a separate operator action.

Required coverage includes:

- Login failures, bootstrap races, session expiry/revocation, CSRF, last-admin
  protection, and role escalation attempts.
- Fresh-install `admin` / `admin` login; salted-hash storage; changed credentials
  surviving restart/upgrade/restore; corrupt identity storage failing closed
  without recreating the default account.
- Cross-project list/detail/log/count/chart/export access; forged project/run
  pairings; unknown IDs; corrupt profiles/state; invalid paths and URLs.
- Developer start/retry/cancel within membership, denied outside it; duplicate
  starts and hold/exclude checks; cost-field suppression in every developer
  response, log view, export, notification, cache, and operation failure.
- Config validation, stale revisions, web/CLI contention, interrupted writes,
  unchanged running config, runtime lock contention, and restart recovery.
- Duplicate/replayed commands, actor revocation, expired commands, worker crash
  before/after side effects, and bounded cancel/retry behavior.
- Executor malformed/missing/cumulative usage, partial history, disabled capture,
  unknown rates, zero versus unavailable, double ingestion, timezone boundaries,
  archived projects, distinct profiles of one repository, and scoped exports.
- Escaping hostile ticket/log content, secret redaction, CSV formula injection,
  safe outbound forge links, and bounded payload/query sizes.
- Browser journeys in both roles, all four languages, three theme choices,
  viewport/zoom checks, keyboard use, and stale/disconnected/error states.
- CLI regression suite, optional dependency isolation, package asset/license
  inclusion, matching frontend/backend versions, migrations, and restore.
- Subscription/API/local endpoint configuration; incompatible protocol, auth
  expiry, unreachable endpoint, egress rejection, and disabled cloud fallback.
- Network-blocked install and first startup using only supplied artifacts;
  explicit missing-prerequisite errors; capacity checks at agreed workload.

Update component documentation and AEGIS knowledge with each actual component
change; update user/config/deployment guides with observable behavior, and
accrue notable implementation changes under the root changelog's Unreleased
section. Apply the legal header to generated source/docs using each file's
comment syntax, with the repository's exception for pure data formats.

## 12. Decision register and remaining questions

| ID | Question | Proposed default | Consequence |
| --- | --- | --- | --- |
| D1 | CONFIRMED: Windows and Ubuntu deployment; first-release scale up to 10 users and 20 projects. Exposure remains open. | One internal host; validate five active viewers and one running job before increasing concurrency. | Build and validate host-matched offline media on both operating systems; see section 10 ranges. |
| D2 | CONFIRMED: developer job permissions. | Start/retry/cancel within assigned projects. Configuration and project-wide pause remain admin-only by proposal. | Enforce at API and worker boundaries; define safe selected-ticket Start behavior. |
| D3 | CONFIRMED: no Internet downloads at installation, on Windows and Ubuntu. OPEN: prerequisite pack scope. | Offline media includes application dependencies/assets/tools/images; prerequisites are supplied offline or already installed. | Test with network blocked; offline installation does not require cloud-free operation. |
| D4 | CONFIRMED: developers cannot see costs. | All monetary data, pricing, budgets, and financial exports admin-only; developers retain operational metrics. | Filter at the backend, including logs and operation errors. |
| D5 | CONFIRMED: preserve subscription testing and existing executors; support API keys and local endpoints, testing OpenAI-compatible HTTP first. Administrators configure estimated prices. | Preserve Codex host-auth test route; endpoint configuration through compatible executor; provider-reported and estimated cost remain distinct. | Test endpoint/auth combinations and avoid treating subscription/local usage as known free usage. |
| D6 | CONFIRMED: keep history indefinitely with manual backup. Reporting timezone remains open. | UTC storage and reporting, USD accounting, no automatic pruning. | Operators must size and back up storage; provide a consistent backup/restore procedure. |
| D7 | CONFIRMED: automatic draft MR creation, human review/merge, and retained separate approval before push/draft creation. | Keep the current candidate-bound pre-publication gate. | Draft-only and never-merge remain; no engine approval change is needed. |
| D8 | CONFIRMED: default username/password is `admin` / `admin`. | Initialize once on fresh installation; retain salted-hash storage. First-login password change is recommended. | Restarts/upgrades/restores preserve changed credentials; corrupt storage must not recreate defaults. |

Local password hashing is the recommended interpretation of "simple passwords";
it preserves the requested simple user experience without recoverable password
storage. UI sketches and implementation estimates should follow the deployment,
permissions, and telemetry decisions, before starting component development.
