<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web frontend

Technical details displays Durable job state folder (`state.store_root`), Workflow Python command (`workflow.aegis_python`), Existing local repository path (`worktree.repo_path`) and Job working folders (`worktree.root`) as informational installation values. Operators configure them in the project TOML on the ADORE server; generic web mutations are refused. The localized guidance explains that changing a path does not relocate existing job state, repositories or working folders.

Project Settings follows **Repository → Tickets → Implementation → PR/MR and review → Statistics → Agent and model**, followed by closed **Technical details**. Repository owns platform/author identity and the single integration-branch editor; PR/MR shows its value and a link that opens/focuses that row. Tickets owns eligibility, polling, priority/type and pickup/status labels; hold/exclude affect pickup, not already-started jobs. Implementation owns capacity, budgets and progress commits, with closed Clarifications, Recovery after errors and Advanced stage time limits. Statistics owns recording/token switches and the informational database file inside closed Advanced statistics paths. Technical details and worktree paths are read-only; Repository branch naming uses reviewed edits and a server-checked example; runtime installation stays external and Agent and model groups executor settings in Settings. Inactive reserved controls are omitted without changing CLI configuration. All categories start closed, retain reviewed Admin edits and Dev redaction, and have four-locale names.

`settingPurpose` routes exact effect overrides before section fallbacks; `settingVisible` suppresses inactive/external fields and admits only four known informational worktree fields; `settingSubgroup` owns native topic disclosures. Technical/unknown and worktree rows cannot acquire editors from catalog metadata. The target reference opens its containing disclosure and focuses the single row.

Implementation uses shared four-locale names for reviewed settings, including **Active job limit**, **Maximum executor launches per job** and **Active work time limit (seconds)** names in rows, editors and candidate review. Help describes serial capacity with parked jobs excluded, lifetime launch counts, resettable active periods and between-attempt time/cost checks. Reported USD accounting depends on captured token usage; cost-only reports do not count. File guidance describes distinct committed/pending/new product and AEGIS paths, the unfinished-merge exception and continuation when Git counting is unavailable. Per-attempt timeout help preserves configured recovery and strict-check semantics; progress publication is enabled by default with local commits retained when disabled, and the quick label is an optional framing hint. Configuration keys, runtime enforcement and role/redaction contracts retain their current behavior.

`review.max_review_rounds` and other review policies map to PR/MR and review; pickup gates map to Tickets. Localized help explains the shared additional-round budget and distinct exhaustion outcomes. Portable mapping validation derives its exact size from `portableFields`, whose readiness map contains two booleans.

`lifecycleCopy` names pickup/status/answer labels consistently in rows, editors and candidate review. `STATUS_LABEL_KEYS` partitions six rows (including answered) into a native initially closed Status labels disclosure inside Tickets. `HIDDEN_SETTING_KEYS` omits CLI-only startup mode (`polling.mode`) and inactive reserved controls; effective config/catalog and scalar transport retain those keys for compatibility. Status edits retain existing administrator/revision/idle authority; Dev remains read-only. The disclosure uses the existing responsive row layout.

`labels.control.exclude` uses `excludeLabelCopy` for the settings row, editor and candidate review in all four locales. Help describes its configured name, presence-based pickup exclusion, removal under remaining eligibility gates and already-started job boundary. The scalar editing and conductor contracts remain unchanged.

`delivery.target_branch` uses `targetBranchCopy` for the row, editor and candidate review in four locales. Help describes the remote starting branch, PR/MR destination, short branch-name format and human merge boundary. The scalar key, active/default values and reviewed editing contract retain their existing authority.

Settings names `delivery.draft` as PR/MR state at publication and displays localized Draft/Ready for review labels for active/default values, options and candidate review. Boolean wire values use the existing reviewed apply flow. The in-review lifecycle represents human review for either forge state.

Project details groups its three metadata rows with a 4px gap and separates
the action row by 18px; long values wrap within the panel.

Secondary text uses contrasting light/dark theme colours. Project metadata,
configuration values, type/domain hints and field help use 0.875rem text with
1.5 line height; long identifiers and guidance wrap within their panels.
On narrow screens, setting labels, values and help stack vertically.


The header help button **How ADORE works**, beside Refresh and About, opens
the localized delivery glossary. Activate it again, press Escape or click outside
to close it. Full job history is reached through the sidebar Jobs link; Overview
keeps job-specific Details links.

Implementation settings support reviewed edits for human-answer waiting time (positive integer plus seconds/minutes/hours/days), positive question-round count, a nonempty retry schedule (one nonnegative integer per line), and the complete stage-timeout map. The six stage rows choose either the general attempt limit or a positive custom limit in seconds; choosing general removes the override. Retry and timeout collections accept only safe integers and their declared keys; other lists/maps remain read-only except the existing reviewer list. Admins prepare, inspect active/proposed values and apply only at the existing idle boundary; developers remain read-only. Names, help and controls share four locales. The answer deadline is independent of the reserved reminder; reminder format is still checked and no reminder is sent.

`implementationSettings.ts` owns closed duration/collection draft validation and localized editor terminology. `settings.ts` retains typed map values when reopening the editor and validates exact canonical candidate collections. `SettingsList` renders duration amount/unit, six-line retry schedule and all six stage choices within the responsive setting row. Invalid complete drafts cannot prepare. Typed groups occupy the whole editor width above their action row, and nested controls explicitly reset the generic horizontal flex basis to retain normal control height. Focused proof: `web/tests/settings.test.mjs` and the typed Implementation, locale and Dev/browser scenarios in `web/e2e/settings.spec.ts`.

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

`04_Software/web` is the React/TypeScript source for the responsive ADORE
dashboard. Vite compiles it into `adore/web/static` for same-origin serving.


The Remove branch after human merge help describes the shared GitHub/GitLab/Gitea behavior in all four locales: exact published commit protection, retained-branch warnings and an independent repository auto-delete policy. The boolean choice feeds the same conductor configuration used by CLI.


Request review from has a localized label and six-line resizable account editor, one forge username per line. It serializes names into the reviewer-only candidate list, displays active/proposed lists in the existing review, and applies through the reviewed configuration flow. Pending array authority is accepted only for delivery.reviewers with exact canonical list/value agreement. Other list settings retain their own read-only contract.

## 2. Responsibilities

Project Settings retains the effective durable state folder as a read-only row.
The shared SettingsList filters the reserved `state.channel` compatibility key
before grouping for both Admin and Dev. Server metadata and raw TOML retain it;
existing API read-only rules continue to reject edits.

**Project → Settings → Agent and model** owns the default coding agent, the selected agent's launch command/model, AI connection testing and external container guidance. Its **Authentication** disclosure groups allowed credential variable names, host sign-in reuse and **Provider API keys**. The agent editor offers OpenCode, Pi, Codex and Qwen Code even when their command tables are absent. Selecting an agent loads its saved command/model or the documented command preset; a new model ID must be supplied explicitly. Prepare reviews agent, command and model together, then Apply writes one complete paused/idle candidate. The generic launch-command/model labels follow the selected agent. Edit keeps agent, command and model controls inside their existing description/value rows; the default-agent row owns Prepare/Cancel for the complete draft, beside its dropdown using the shared editor layout and normal responsive wrapping. Grouped-edit guidance stays in the description column. Validation occupies its own line after the controls, keeping selector/actions aligned when the selected agent needs a model; Prepare remains disabled until the complete draft is valid. Credential names are added through a dropdown and remain visible as individually removable selections. Installed agents and runtime preparation remain external. The old `/executor` URL redirects to Settings. Developers read non-secret settings/results without mutation actions.

The names-only credential selector offers known provider names and retained custom names, independently of coding agent. Empty lists support existing server sign-in. Applying names does not delete saved `.env` values. Provider API keys offers private Save/Disconnect for known allowed variables and shows sources only; key changes require paused pickup and idle/pending-free state. Explicit Test AI connection remains the evidence of model access and may incur provider charges. Subscription login retains the installed CLI's external service-account workflow.

The shared shell presents Overview, Projects, Jobs and Statistics as semantic
links, with My account for each authenticated user and administrator-only
System status, Users and Change history. The approved DDP Engineering sage
PNG is displayed on the dark navigation panel at its original 630:300 ratio,
separately from ADORE. Source SHA-256:
`4957da4edf9aebf02dcb0e24823ff5f8d5ee524622773f4285c9e2261903c481`.
The binary inherits the provenance documented in the published design bundle.

The project hub band shows the authorized project's display name, repository and
section tabs; it appears only on Project details. Overview and Jobs default to all
authorized current and archived projects and offer an explicit project selector,
which is their only scope indicator.
`JobWorkspace` reads the complete global jobs API; scope and composite job identity
remain independent of the Statistics selector. Statistics retains `/metrics`,
existing exports and query parameters.

Loading and failed requests have separate status/error panels. Numeric
cards and data tables render after successful scoped responses. A failed
refresh withholds prior totals; Refresh retries current reads. A successful
empty project list explains enrollment for administrators and access requests
for Dev users, while My account remains available. Pending detail responses
are checked against both project identity and request revision. Session
generation guards prevent the previous account from refilling data.

The keyboard skip link focuses content. Primary links mark the current page;
navigation and disclosure controls have visible focus. Route changes move
focus to content. A localized How ADORE works disclosure defines job, enrolled
project, pickup stopped, waiting for clarification, waiting for approval and
draft review. Stopping pickup affects new issues; active jobs continue.
Publication approval occurs on the forge; merge remains a human decision.
Essential guided-field instructions stay visible and are associated through
`aria-describedby`; settings and the glossary retain progressive disclosure.

It provides login, project and job views, role-appropriate metrics,
administrator project/account setup, settings, four language catalogs,
an administrator audit trail, light/dark/system themes and an About dialog.
Administration expands into System status, Users and Change history in the sidebar.
Both roles see a top-level My account entry for their own preferences and
password.
System status contains administrative audit-retention settings with day and MiB
controls populated from saved policy, a separate-bound/deletion impact summary
and an actual deleted-event count after saving. Change history contains evidence
and filters. Project History includes assigned-project change evidence alongside
its job history. `AuditHistory.tsx` requests exact actor/project/action/half-open
UTC filters, matched counts and 10/25/50/All pages from `/audit-page`. Filters reset
the offset. The view shows Who/What/When/Result and expandable known before/after,
operation correlation and revision evidence. Missing legacy values say Before
value not recorded; candidate preparation and uncertain application attempts are
labeled separately from applied results. `auditCopy.ts` supplies four locales.
Strict transport/value checks withhold malformed, mismatched or failed evidence
and counts. Principal/project keyed instances and cancelled requests suppress
stale completion; the project reader mounts only after stable identity resolves.
There is no audit export. Browser tests in `e2e/audit.spec.ts` own empty/error,
filter/paging, privacy, role, locale/theme and 390px behavior.

Unlimited retention limits display zero; zero or blank saves as null in the API. Days are
whole numbers through 36500, sizes are finite MiB through 1024 and round to
positive whole bytes. Fractional MiB preserves policies below one MiB. Invalid
values are rejected before a request with localized guidance. Successful saves
restore the canonical saved/default display, including zero for unlimited.
`src/auditPolicy.ts` owns conversion; offline `tests/auditPolicy.test.mjs`
covers saved/default values and rejected input.
Tables with more than ten rows offer 10, 25, 50 and All choices with
Previous/Next for finite pages. Audit counts and pages its complete filtered
authorized retained history on the server;
Jobs delegates page size, complete filtering and source-revision checks to the global API. Other tables
paginate their rendered rows and reset to the first page when size changes.
Selected-ticket history uses the shared paged table with Date, Event and Stage
columns in reverse journal order, with latest events first. A reversed copy
preserves the received event array. It starts at ten events per page, offers 10/25/50/All
for longer histories, and resets on project/run identity changes. Empty history
shows an explicit unknown-evidence message; event text remains escaped by React.
The top bar supplies the single page title and common actions on every page.
Project details uses the identity opened from Projects; platform administration and account settings
use their own status, membership and preference controls. Jobs and Statistics
keep their project selectors in page content. Overview leads with Needs attention:
clarification, candidate approval, draft review, failed, stale and pending handoff
jobs. A separate Active jobs table shows actual working/publishing rows from a
complete authorized active response. Both compact tables show title/project/ticket,
status and Details; App places one Project selector in DashboardShell's optional
header-controls slot, before selected context and job tables. The sidebar Jobs link retains
scope; the primary Overview URL/action resets it to all authorized projects.
Explicit scoped deep links remain supported. Overview's visible15s job polling
retains validated same-render-key rows until a successful replacement; failures,
incomplete evidence and scope/access changes still hide them. Its refresh timestamp
is omitted; manual Refresh retains its loading feedback.
Overview skips consumption reads and reporting/date/technical prose. Only worker
faults appear above the job tables. Details retains the existing composite Jobs route
and browser-local timestamp formatting. Source errors or
incomplete responses hide rows and totals; a changed continuation offers explicit
Reload first page. Jobs filters by search, project and status group only.
Selected detail precedes the job list and explains current lifecycle, exact saved
stage, observed reason, who acts, where and what conditionally follows. Safe saved
question/candidate/MR links locate the action; named people, duration and consumption
remain unknown when the projection does not provide them. Old recorded activity is
separate from the control worker heartbeat. Completed never implies human merge.
The observed timeline marks only actual events, including quick paths.

The global Jobs page renders its own compact `#jobs-project` selector and the hub's
shared `jobsSubtabs` (Tickets via `TicketWorkspace`, Jobs via `JobWorkspace`);
`routes.ts` carries `view=jobs`. `TicketWorkspace` takes `projects`: for All
projects it reads each active project with `Promise.allSettled`, keys rows by
project and ticket, adds a Project column and reports read failures per project. `JobWorkspace` has no
scope panel or ticket-number form and shows worker status only as an alert.
Manual start goes through Tickets Start. Archived projects retain history and hide
start. Retry is available for failed current jobs; cancel excludes terminal and
pending/completed human handoffs. Effects stay visible beside each control.
An immediate submission lock prevents duplicate commands; existing operation
status polling distinguishes queued/running/completed/failed/uncertain results.
An unavailable operation read explicitly leaves completion unknown. The API and
worker recheck authority and lifecycle; the browser does not claim job success
from command acceptance.

Administration's account section is labelled Users in every locale.
The About dialog constrains its width and height to the viewport, with internal
scrolling for the license and notice content and an accessible Close button.
Add project opens the administrator-only `EnrollmentWizard` from Projects.
It presents six ordered steps with shared visible, associated guidance for method,
repository/identity, environment, eligibility/reviewers/limits, verification and
review/create. `enrollmentCopy.ts` supplies complete EN/FR/DE/RO catalogs.
The local clone belongs to the ADORE server and already contains Git/AEGIS.
Actual provider/model and local image values are entered explicitly; host-auth
is supported for OpenCode/Codex, while Pi/Qwen require API-key references.
The separate human display name and stable profile ID are reviewed with forge
identity, target branch, selected Gitea tea login, credential environment names,
ready/approval labels, reviewers, four run limits and canonical server paths.

Wizard state lives in the mounted component. Back and Change retain values;
each changed answer invalidates preview, verification and frozen review and
increments a generation guard. Late responses cannot refill a changed/unmounted
draft. Dirty shell/context/history/cancel/sign-out navigation confirms loss;
beforeunload uses the browser warning. Only existing language/theme storage remains.
Local validation and server findings produce an alert summary with corrective-step
buttons. The alert, matching input or step heading receives keyboard focus.
Required guidance is associated with controls through aria-describedby.

setup-preview is structural and never probes. Explicit setup-check explains effects
first and displays revision/time-bound failed/partial/unverified/current evidence
with prerequisite-specific remediation. The model endpoint and undetected WSL
checks remain explicitly unverified. Review is the canonical response paired with
the unchanged draft. setup-create submits its frozen revision and uses an immediate
ref lock to prevent double clicks; failure requires a deliberate new review.
Completion displays stopped pickup and separate activation guidance, then offers
Open project. Draft probe evidence is ephemeral; persisted project readiness
starts unverified and is checked separately.
About displays the project license text and the bundled third-party notices.
Projects show archived state and let administrators archive or restore a
quiescent project. Archived jobs and metrics stay visible, while job and pickup
controls are hidden until restore.
Enroll an existing configuration for this ADORE server opens the administrator
`ImportWizard` from Projects. `importCopy.ts` supplies EN/FR/DE/RO source,
unchanged-copy, server-path and existing-data-only history guidance. Ordered steps
cover file, declared identity/paths, structural validation, explicit environment
checks, canonical review/enrollment and stopped completion. Recognized settings
and all consequential declared/resolved server paths are reviewed without raw TOML or secrets.
The selected File and draft stay in memory. Fatal UTF-8 decoding preserves bytes
and rejects empty/oversized/invalid encoding. Each request rereads the File;
changed or unreadable disk bytes require reselection. Internal Back/Change retains
values but invalidates preview/probe/review; leaving or refreshing warns about
loss, and unmount/session change discards the draft and ignores late responses.
Structured findings point to form fields or source keys/server locations and move
focus to correction. Failed/partial/unverified probe results remain explicit in
review. Confirmation submits a frozen candidate with an immediate ref lock;
failure invalidates review and never displays completion. Success clears file
contents, confirms stopped pickup and offers Open project. Activation is separate.
Long page titles wrap in the shared top bar, including at 390px.
The Projects directory lists authorized projects in a sortable, paged table
with project, repository path, Repo forge provider (Gitea/GitHub/GitLab),
Monitoring, job count and saved last activity. Project-name links open the hub.
The dedicated hub has one identity/navigation band: name, repository path,
Summary, Settings, Jobs, Statistics, History, Access, all tabs. Access is
Admin-only. The Jobs tab has Tickets and Jobs sub-tabs (`/projects/<id>/jobs`,
`?view=jobs`, `?run=`). Tickets (`TicketWorkspace.tsx`, copy in `ticketCopy.ts`)
reads open tickets only when Read tickets is pressed, validates the response,
shows eligibility, the blocking rule or job state with Start (confirming and
choosing a priority when it must add labels), Retry for a failed job, confirmed Stop
and Details (description plus comments loaded on first expand), and starts work only
from the table (disabled actions are visibly dimmed); forge text is
rendered as React text and only http(s) links open, with `noopener noreferrer`.
The Jobs sub-tab renders `JobWorkspace` in jobs mode with a fixed scope, no start
form and the hub's `onOpen`, so job detail stays in the tab; Statistics renders the
shared `statisticsView(true)` without the project selector or the cross-project tab.
`statisticsView` lays the reporting period out as one `.metrics-period-row` (project
selector on the global page, From, Through, Group by, All time, Export CSV) with no
time zone control (UTC unless the URL supplies one), and `StatisticsEvidence` shows no
current-stock panel.
Summary holds Monitoring Active/Paused status, runtime/executor and explicit
revision-bound verification evidence. Administrators use Summary to pause or
activate monitoring, archive/restore, and delete archived idle projects using
exact-name confirmation. Deletion intent clears on page or selected-ID changes;
the submit handler checks current project, administrator and confirmation again.
The API owns archived/idle preconditions, authorization and CSRF enforcement.
Verification shows structural invalidity or persisted unverified/stale/failed/
partial/verified evidence; static validity does not establish live readiness.
Assigned developers can inspect the redacted effective configuration in
collapsible Git-flow categories, with frequent settings first within each. Each row shows its value,
a Default badge for inherited values, its type and contextual help; common
settings also describe their valid domain. `web/src/settings.ts` builds, filters and groups the rows. Each row's visible guidance shows the setting's own text in the selected language
from `web/src/settingHelp.ts` (keyed by the catalog `web/src/settingKeys.json`,
with `*` for project-chosen names) and its ADORE default. Administrators can stage and apply
project configuration, local endpoint and estimated-price changes there, while
a developer's projects are edited together under Users, and one project's
developers on its Access tab. My account holds account
appearance and password controls. Project details groups this content into
Summary (pickup, host verification and project jobs), Settings (read-only settings
and administrator editors), Jobs (start, filter and inspect project jobs), Statistics
(project reporting), History (terminal jobs), and the administrator-only Access tab with
keyboard tab navigation. Access
(`ProjectAccess` in `App.tsx`) lists the project's developers from
`GET /projects/{name}/access` and grants or removes one with
`PUT /projects/{name}/access/{user_id}`; a developer's `/access` route falls
back to Overview.
Administrators can explicitly run a host-prerequisite check there. The view
labels model-endpoint and WSL runtime results as unverified when they cannot
be established from the API host, and never treats static config validity as
live readiness.
Administration polls `/api/v1/ready` every five seconds and shows whether the
control worker is ready, unavailable or could not be checked. Its explanation
keeps forge, executor and model readiness separate.
It polls the administrator-only storage check every 30 seconds and shows free
space for ADORE home and project state roots. Less than 1 GiB is marked low;
a failed measurement is shown as an error.
The Jobs view starts at ten rows from complete authorized history. Search and
secondary filters run before slicing; counts/groups retain the searched scope
before secondary selection. Continuations pass the returned optimistic snapshot.
Scope/filter/session generations suppress superseded responses. Status and stage
labels and all action guidance are available in EN/FR/DE/RO.
The About dialog traps keyboard focus and returns it to the opening button on
close. A compact top-bar Sign out control remains available when the sidebar
account controls are hidden on narrow screens.
Project selection and project API routes use the immutable profile ID, so a
profile rename preserves the selected project and does not retarget actions to
a different profile that later uses the old name. Settings also presents administrator price versions; Statistics separates reported
and estimated USD values, shows unpriced usage events among the Usage totals,
keeps per-project estimated cost in the All projects Usage table and links to
administrator global CSV.
The Statistics page keeps its authorized project selector, inclusive date range,
day/week/month grouping, All time and CSV export menu in one row above four category tabs: Summary,
Usage, Quality and Trends. Administrators initially see All projects, with pooled
headline totals and one per-project table per family (`projectCell` adds the
repository hint) in Summary, Usage and Quality, starting with a paginated project breakdown
in Summary. Selecting one project scopes every category, project/repository
comparison and export to that project. Project details opens Statistics for that
project. Developers select assigned projects and receive operational data only.
The export menu offers metrics, usage and composite job-consumption CSV files for the current scope;
global choices appear only in administrator All projects scope. Arrow keys, Home and End switch tabs,
and the shared controls retain their values when categories change. On compact
screens the heading spans a full row and the project, date and grouping controls
wrap below it. Switching projects retains the category and reporting parameters;
selected-project metric/usage requests and CSV links use the new project ID.
The filters are shared by the scoped tables and CSV links.
The same selected interval supplies headlines, project/repository breakdowns,
trends, quality and duration. Blank bounds explicitly select All-time. Unknown
individual token values remain unavailable; measured zero renders zero.
Coverage distinguishes unallocated usage and missing launch telemetry.
Review still open counts reviews open now, independent of the period. Usage has no identity filters;
`usageSort.ts` sorts its table by any column (unknown values last) through the
shared generic `SortHeader`, and `.usage-totals` chips combine usage totals with
job elapsed time. Requests discard stale responses after scope
or session changes. CSV links retain identical reporting options.


`StatisticsEvidence.tsx` renders the Summary measure cards only: started/completed/
failed events and known input/output/total token subtotals, without heading or
explanatory text; job elapsed time appears among the Usage totals. Null is Not
available, explicit zero is Measured zero, and known amounts with missing
observations are labeled partial. Reported and estimated Admin money have
separate labels.
`TrendEvidence` renders one `table.trend-table` (named Trend data) with a row
per server bucket; count cells carry aria-hidden bars scaled to the largest count
and token/money cells show plain values or a dash. `statisticsCopy.ts` holds the four-locale labels.

`statistics.ts` validates scope, immutable project/run IDs, nullable amounts,
financial absence for Dev, quality counts and exact server duration samples.
Request/render keys include current project authorization; scope changes,
reordered polling responses, revoked grants and route transitions hide earlier
values. Current metric and usage scopes must agree before presentation/export.
The `/metrics` and `/jobs` URLs retain selected `from`, `through`, `timezone`
and `granularity`; blank dates and the explicit All time button select all-time.

Jobs list/detail (not Statistics) key consumption by `(project_id,run_id)` and
show lifetime amounts only: `JobWorkspace` reads all-time usage once per visible
authorized project, and `JobAmounts` renders plain values (dash for unknown). The
Jobs table sorts through `jobs-page` `sort`/`order` with the shared `SortHeader`
(Ticket, Project, Status, Last activity). Observation
counts identify source coverage without claiming complete measurements. Actual
server filters and boundaries remain authoritative; browser aggregation uses
server-selected evidence. Existing job/state persistence and API remain intact.

`src/metrics.ts` pools the server-selected exact duration sample arrays and their
count/sum, including measured zero. It computes mean/median from these samples;
it does not parse run dates or approximate interval selection. Rates pool their
numerators/denominators; monetary averages weight known sample counts. Nullable
consumption sums remain null when no observation is available. Financial fields
remain absent when pooling developer responses. Failed/merged counters retain
server scope. Invalid numeric/duration/scope evidence raises `RangeError`.
`web/tests/metrics.test.mjs` proves these contracts offline.

Signing out and signing in as another role returns to Overview, so an
administrator-only view cannot remain selected for a developer. Config staging
keeps its form reference until the request completes, allowing the form to reset
after a successful response. User creation owns its staged
transient draft and clears credentials after confirmed creation.
Administrators can trigger a replay of retained usage journals from Statistics;
the button reports the reconciled event count and refreshes attributed views.
The local endpoint form is shown for OpenCode profiles. It saves model ID and
URL in one request and explains the required provider package in the executor
image. An optional allowlisted environment-variable name references an API
key without collecting its value in the browser. The form exposes the supported
chat-completions protocol, bounded request timeout, and HTTPS custom-CA file
path inside the executor image. Its pending-change panel shows the resulting
endpoint fields before Apply.
Settings presents six purpose categories plus closed Technical details with frequent rows first in each,
source badges, visible localized purpose/units/consequence help, Active value and
ADORE default. Server catalog type/choices/numeric bounds continue to constrain editors; permanent descriptions provide guidance. Browser controls use server metadata; malformed catalog/candidate
transport fails closed. English labels clarify catalog keys; other locales retain
localized common labels and localized setting guidance for remaining headings.
`settingsCopy.ts` supplies four-locale category, effect and recovery copy.

`PendingReview` compares safe active values to typed server-derived proposed values,
names the affected display project. Pending configuration appears above the settings categories. The main comparison shows changed values only, with adjacent Apply/Discard actions. A candidate with unchanged simple values displays a clear notice and disables Apply; image/plan binding candidates retain their review. Closed Technical details contains the complete safe comparison, effect, preparation time, revisions and Copy safe review. Blocking pause/stale notices remain visible. Object property order is ignored when comparing values; list order is significant. The comparison wraps into labeled value cells on narrow screens. Preparation focuses the review heading; discard returns keyboard
focus to the edited row or endpoint field. Endpoint review includes URL, model, protocol, credential variable,
timeout and CA; unobserved active connection fields stay unknown. Safe clipboard
copy uses only review values and full revisions. A single mutation ref lock and
captured session/request/view identities suppress duplicate submission and late
cross-project completions. Editing waits for the pending read and freezes while a
candidate exists. The endpoint fields share those guards.

Apply sends both candidate/base revisions; stale base or required unpaused pickup
disables the browser action. Server idle/lock/pause checks remain decisive and a
blocked result retains review. Discard removes only the candidate. A failed pending
read offers explicit refresh/discard and prevents edits or Apply. Assigned Dev sees
read-only groups with financial/secret fields omitted. Existing jobs retain their
configuration; the UI explicitly describes the one-setting candidate contract.
Statistics also shows reviewer-requested MR/PR revisions and automatic pipeline
repairs as distinct counts; unknown revision triggers appear as an Unclassified
revisions value. Quality panels use the shared `Chips` (`.metric-chips`) row: the
Delivery quality panel shows reviewer-rework, first-validation, and
first-pass human-merge rates with visible numerators and denominators, plus a
still-open review count; the daily revision table lists only days with a revision
or repair. Empty cohorts display unavailable instead of zero.
It shows stage failures and operator retries separately. Administrators also
see reported and estimated USD per completed and human-merged job, each with
the count of jobs carrying that kind of cost evidence.
These cohorts use first review/validation or human done event in the selected interval. The
administrator project comparison includes each project's reviewer-rework rate.
For the selected project, administrators also see token usage and separate
reported/estimated USD amounts attributed to each revision. Missing monetary
evidence appears as unavailable, including revisions with no usage.
Server responses determine
authorization; hidden controls alone are not a security boundary.
Signing out or changing accounts clears cached runs, metrics, prices, account
rows and details. Requests started under the previous session cannot refill
those views after the switch.

## 3. Implementation Overview

`TransferWizard.tsx` presents guided creation, portable file import, settings copy
and the separately worded advanced unchanged server TOML copy. File/source selection
reviews all 15 recognized rules and explicit exclusions before target setup.
`EnrollmentWizard` receives optional memory-only source context and uses the same
identity/repository/environment/eligibility/verification/review steps. Copied
budget controls are read-only; canonical review shows every source rule, installed
server default and effect, with independent allocated config/state/worktree/metrics
paths. Target reference/environment reconfirmation is required and invalidated by
identity/environment edits. Custom endpoints remain explicit separate target setup
while pickup is stopped; source references never seed that setup.

Target/source edits invalidate reviews and checks; ref/generation guards prevent
repeated submits and superseded responses. Selected files are reread before review
and every target operation; changed/unreadable bytes block action and expose source
re-review. Back/Change retains target corrections; returning to source or switching
method warns and resets the target draft. Sources/drafts stay in memory and are
cleared on leaving. `transferCopy.ts` supplies EN/FR/DE/RO explanations. Completion
confirms stopped pickup and separate activation. Existing exact TOML and export
panel boundaries retain their distinct wording/behavior.

`e2e/transfer.spec.ts` covers both real-API methods, required reconfirmation,
visible mapping/exclusions/paths, stopped success/double click, correction/back,
actual source/file changes, failed/late transport, role denial, four locales and
keyboard/390px themes. External commands remain faked; participant/live/full-WCAG
acceptance remains human work.


`RawConfiguration.tsx` owns four-locale Admin raw actions, bounded fetch, exact-byte download and native dialog with Escape/Close/focus restoration. Abort and pending-ref guards discard late results on unmount. Errors use localized safe codes; TOML is escaped text and never stored in browser storage. `e2e/portable.spec.ts` covers bytes, failures, role denial, late responses and four locales at 390px.

Administrators use **Preview raw configuration** or **Download raw configuration** beside Project settings. Preview opens a closable dialog; download preserves original saved `config.toml` bytes including comments, formatting and inline secrets. Pending changes, resolved defaults, separate `.env` files and external credentials are excluded. Preview is memory-only and cleared on dismissal or project/session change. Developers retain redacted read-only settings and cannot access raw configuration. Candidate review/apply/discard remains inside Settings.


`DashboardShell.tsx` owns the authenticated frame, real navigation links,
branding, responsive menu, header and content focus. `Presentation.tsx` owns
`DataFeedback`, `ProjectEmpty`, `StatusBadge` and `DeliveryGlossary`.
`App.tsx` owns session, project hubs, SettingsList/PendingReview, configuration/statistics mutations and route/history flow.
`settings.ts` owns purpose grouping and strict catalog/candidate transport validation;
`settingsCopy.ts` owns clear labels and localized single-candidate guidance.
`JobWorkspace.tsx` owns scoped jobs/attention/detail, visible polling and command
feedback. `jobModel.ts` validates complete counts, composite identity, saved
links and observed events; `jobCopy.ts` supplies four-locale action guidance. Request completion retains session-generation guards
and selected-project/request-revision checks; malformed data at the changed
presentation seams is converted into explicit feedback.

`App.tsx` manages session, selection and requests. `i18n.ts` contains EN/FR/DE/RO
strings. `styles.css` defines responsive layouts and themes. Session cookies
remain HttpOnly; only the CSRF token is held in application memory. Language
and theme preference are kept in browser local storage.
Before login those browser values are the fallback. After login, saved account
preferences load before the authenticated shell appears; Settings writes a
changed language or theme to that account. A failed save restores the previous
choice. The login screen offers both language and theme controls.
`routes.ts` maps every view to a path URL and back (see the URL table in
`01_Documentation/Web_Interface.md`). The app keeps its view state and
synchronizes it with the address bar: a new path adds a history entry, a
changed project or job in the same view replaces it, `popstate` re-applies the
URL, and role or unknown-path fallbacks replace the entry. A routed project ID
is checked against the authorized project list before any project is chosen
automatically. `polling.ts` runs every periodic refresh only while the page is
visible and refreshes immediately when it becomes visible. `JobWorkspace` owns
revision-bound server paging and locally paged observed timelines; `ServerPager`
continues to serve Audit. Common guided forms keep required markers and localized
examples. `.table-scroll` keeps wide data within its own scroll container.
Project names and ticket numbers are semantic links with owning-project URLs.
Project tabs support arrow keys, Home and End; `/configuration` is Settings and
the older `/executor` and `/prices` paths open it, while `/history` selects
terminal jobs in the same authorized hub. The Admin-only estimated-price form sits
in the Agent and model settings group (`executorAfter` slot of `SettingsList`),
asks only for effective date and rates, submits the applied `executor.default` and
its configured model as hidden fields, shows set-a-model guidance when that model
is empty, and remounts per project and configuration revision. A successful empty Statistics response shows the measured zero lifecycle counts and explicit unavailable consumption; Quality and Trends show localized empty feedback. Loading or failed reads withhold numeric cards and CSV actions.
An account whose password an administrator reset signs in to a dedicated
change-password card with the reason, language, theme and Sign out controls;
the dashboard and its polling stay inactive until the change succeeds, after
which the sign-in card confirms the change.
`errors.ts` turns API error codes into EN/FR/DE/RO sentences, appending any
diagnostic `message`; an unknown code shows a localized generic sentence that
names it, and network failures have their own message. The banner keeps the
raw failure and localizes it when rendered, so a language switch updates it.
Each user action and each view change clears the previous error banner;
background refreshes do not. EnrollmentWizard and ImportWizard validate stable lowercase
profile IDs before sending requests; the server remains authoritative for reserved
IDs and ownership conflicts. Primary buttons use the `--on-accent` token, which
is dark text on the light accent in both system-dark and explicit Dark themes.


### Reviewed account and project access

`UserCreation.tsx` and `userCopy.ts` provide four-locale identity/credentials,
role/projects and review stages. Admin explicitly receives all current/future
projects, system and cost access; Dev selects immutable IDs and receives project
access only. A deliberate checkbox confirms Dev without grants. Review shows
username, role and display labels plus stable IDs, with correction controls and
focused stage headings. The password remains in transient credential state and
is absent from the review model/render, browser storage and result. Unmount and
successful creation clear the draft; failed creation retains correction.
A synchronous ref guard permits one submission. Strict result parsing checks
identity/role and exact reviewed grants before showing actual success; account
refresh runs separately from the successful mutation.

`AccountAccessEditor` reviews whole-account grants before compatible name-based
assignment, resolving selected IDs through current loaded project records.
`ProjectAccess` reviews one developer's current/proposed project grant before
its existing mutation. Both show actual response results, retain correction on
failure and guard duplicate/stale completion. Invalid project/account/developer
reads withhold actions. The `.user-access` layout wraps IDs and action groups
at narrow widths. `e2e/users.spec.ts` verifies review/correction, explicit roles
and empty choice, secrets, duplicate submission, failures/malformed reads,
late navigation, access edits, keyboard focus, themes and four-locale reflow.

## 4. Dependencies

React is bundled locally. Node.js and npm are build-time only; the deployed
browser assets do not fetch fonts, scripts or translations from a CDN.
Playwright Test and Node type declarations are development dependencies for
the isolated Chromium verification suite; they are not bundled in the runtime.

## 5. Inputs And Outputs

The UI consumes `/api/v1` JSON and emits authorized form requests. Build
output is a versioned static `index.html`, JavaScript and CSS with the project
license banner, plus the bundled `LICENSE.txt`.

## 7. Workflow Integration

The usage table displays reported cache-read and cache-write counts; a dash
marks unavailable categories. These counts are already part of input tokens.
The endpoint form submits an empty CA path explicitly so an administrator can
remove a previous custom trust reference during a staged edit.

The API serves the build from its own process. Developers can start, retry and
cancel assigned jobs; job details show retry for failed runs and cancel for
nonterminal runs still owned by ADORE. Pending and completed human handoffs
have localized status labels; neither shows Cancel. Only administrators see
cost and account/config screens.

## 9. Validation And Tests

`tests/statistics.test.mjs`, `tests/metrics.test.mjs`, `tests/routes.test.mjs` and
`e2e/statistics.spec.ts` cover strict analytical transport, scope/exports/stale
responses and grant revocation, per-job collision/null/zero/partial values,
canonical mismatches, four locales/themes, keyboard and trend table values and bars at
390px. The browser server uses disposable profiles and fake command boundaries.


`tests/jobs.test.mjs` validates complete/unknown evidence, malformed or contradictory
counts/groups, unauthorized/composite identity, unsafe URLs, command guards and
route compatibility. `e2e/jobs.spec.ts` uses real local state/API plus a fake worker
for every lifecycle, actual question/candidate/draft references, missing/stale
metadata, complete global filters, source changes, collisions, role/CSRF denial,
queued and failed commands, observed timeline paging, unsafe action URLs and
keyboard/390px/both themes/four locales. Retained screenshots support bounded
visual inspection. These checks do not establish live or novice acceptance.


`e2e/import.spec.ts` covers explanatory exact enrollment, full safe review,
stopped success, duplicate-submit protection, invalid file/encoding/response,
failed/stale verification, source disk mutation, correction/invalidation,
late responses, loss/navigation/refresh, Dev denial, four locales and keyboard
focus. Desktop/390px screenshots cover both themes; this is bounded visual
inspection, with novice/live acceptance and full accessibility audits separate.

`tests/shell.test.mjs` checks glossary/catalog parity across EN/FR/DE/RO
and exact approved logo bytes, dimensions and PNG alpha format.

`e2e/enrollment.spec.ts` covers guided success and exact submitted draft, duplicate
clicks, malformed fields, ID collisions, invalid server clone/runtime, stale/failed/
corrupt checks, retained Back/review corrections, pending-response invalidation,
Dev denial, refresh/history/shell loss, failed creation, supported locale guidance,
keyboard focus and both themes at 390px. It retains representative screenshots;
external commands use the injected fixture runner. Automated evidence establishes
neither novice-user acceptance nor full WCAG conformance.

`e2e/shell.spec.ts` exercises semantic/keyboard navigation, deep links,
Back/reload, scope, Admin/Dev/no-grants access, light/dark at 1440px and 390px,
visible guidance, pending/empty/HTTP/corrupt-data feedback, recovery and stale
project-detail response rejection. It records representative screenshots;
automated journeys establish neither full WCAG conformance nor novice-user
acceptance. API and external command boundaries remain simulated offline.

`npm run validate` runs the Node helper suite, UI/E2E TypeScript checks,
an isolated Vite build in `.e2e-dist` and the Playwright Chromium journeys.
`playwright.config.ts` bounds the complete browser suite to 600 seconds, with
30-second test and 10-second assertion limits, one worker and no retries.
Locale journeys await the successful preference-save response so their final
English restore persists before the disposable browser context closes.
It owns failure
screenshots/traces and the private fixture server. `e2e/server.py` creates
temporary profiles, identity/state stores and a real API/worker with simulated
external command boundaries. Browser traffic stays on its loopback origin.
It covers authentication, role/project scope, CSRF, Stage/Apply and stale
revisions, reload/Back, the 390px menu/editor, and worker outcomes/idempotency.
`e2e/teardown.ts` shuts the fixture down normally on Windows and Linux.
Provision Chromium with `npx playwright install chromium` before offline runs.
See `01_Documentation/Web_Interface.md` for commands and retained diagnostics.

`npm run build` performs TypeScript and Vite checks. `npm test` runs the Node
unit tests, including `errors.test.mjs`, which requires a message in every
locale for each code `adore/web/app.py` can return, and
`projectName.test.mjs`, which compiles the shared pattern with the `v` flag,
`routes.test.mjs` for the URL scheme and `polling.test.mjs` for hidden-page
polling.
Backend tests prove RBAC and cost omission. Chrome checks covered 360px and 1920px layouts, all four
language controls, dark/system themes and the About dialog's keyboard close.
At 360px, browser QA verified Tab/Shift-Tab remain on the dialog's Close button,
Escape restores focus to About, the background is inert, the mobile Sign out
button returns to login, and the page does not overflow horizontally.
An administrator-to-developer browser switch was checked with 20 synthetic
projects: only the developer's three assigned projects and operational metrics
remained visible.
Browser QA also observed the Administration status change from unavailable to
ready and back as the test-home worker heartbeat was set and cleared.
The compact navigation is a labeled collapsible menu below 760px; choosing a
page closes it. A 360px Chrome run exercised this interaction and verified no
document-level horizontal overflow on Statistics at 360, 768, 1024, 1366, 1920,
and 2560px. A 180px effective-width check, representing 200% zoom on a 360px
display, also remained within the document width. French, German and Romanian
Settings views retained document language and had no 360px overflow.

## 10. Limitations And Future Work

The initial automated journey suite uses Chromium. Additional browser engines,
automated accessibility audits and live log streaming are future work.

### Settings validation

`web/tests/settings.test.mjs` verifies complete grouping, server control domains,
read-only malformed metadata, labels and strict candidate transport. Offline
`web/e2e/settings.spec.ts` covers correction, safe before/after/copy, unchanged
active revision, exact apply payload, blocked/pause/stale/malformed review, discard,
duplicate/late requests, endpoint connection review, four locales and keyboard/
390px/light/dark views. Screenshot inspection complements automated checks; live
infrastructure, full accessibility and participant acceptance remain human work.

Discard focus restoration runs in a post-render effect after the mutation busy guard clears, with the original captured scope checked before focusing the enabled edit control.


Project Summary uses two panels beneath the shared project header. The first
shows separated label/value tiles for Container type, Executor, Monitoring,
environment verification and actual scoped Active jobs, Waiting, Draft review
and Failed jobs counts. Unavailable/corrupt job evidence shows unknown counts
and withholds job rows. The second groups compact Needs attention and Active
jobs tables; Details opens the full scoped job view. Usage/reporting belongs
to Jobs/Statistics. Worker faults stay visible.
Administrator monitoring/archive/restore/delete and Check host prerequisites
buttons live in the information panel. Explicit host-check results appear there.
Explicit host checks retain internally validated check time and configuration revision.
Check host prerequisites opens the details panel immediately and shows Checking while the request runs. Duplicate checks are blocked. Results or localized failure guidance appear inside the panel; Close details hides it without cancelling a running check, and completion respects the closed state. The check button exposes the disclosure state and regains focus on close. Project/account/page changes discard stale responses; project-tab navigation retains current evidence. Model/executor
access evidence appears only inside these details on Summary. There is no separate
connected-model output or overall performed-check banner, keeping the following jobs panel visible. Configuration/time metadata remains internal; configuration changes require fresh evidence. An Admin can configure repository sign-in through Connect repository in Summary,
or externally under the ADORE service account. Browser sign-in is separate.
Git supplies isolated working copies; the repository command tool reads issues and
publishes draft reviews; repository sign-in tests configured host authentication.
The container engine starts isolation; agent availability proves executable presence
in the local image; workflow availability checks the two configured AEGIS files.
A compatible configured OpenCode endpoint receives a temporary-container streamed
model/tool-call check. Current saved explicit model-access evidence is shown for every executor. When no current result exists, model access remains untested. OpenCode endpoint/tool compatibility is identified separately when it was performed. Unknown container detection is incomplete;
any failed check requires intervention with a targeted corrective instruction.
These checks do not prove a complete job, Git push permission or AEGIS execution.
Fresh browser evidence validates the API status contract, selected project identity, revision, UTC
check time, exact check keys/types and consistent model-probe results before display;
invalid results produce a localized error and withhold the new check rows.

Deletion uses a native modal with exact-name confirmation, Escape/cancel,
focus containment and trigger focus restoration; navigation clears intent.
Deletion remains subject to archived/idle project preconditions.


## Project repository connection

Summary → **Connect repository** opens an Admin-only modal token form beside Check host prerequisites for the saved
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


## Explicit AI connection test

Administrators use **Settings → Agent and model → Test AI connection** for the configured OpenCode, Pi, Codex or Qwen model. Each explicit click sends one short request in a temporary container and may incur provider charges. The project must be idle with valid saved settings and no pending configuration/operations; its installed image must contain Python and the agent.

Only a valid completed challenge response reports connected. Failures provide redacted guidance for credentials, model availability, image, CLI version or network. The action reuses executor credentials and egress; it starts no job and proves no tool capability. Evidence is durably saved, bound to current project/model/configuration and credential inputs. Summary and host-check details reuse the current access result; endpoint/tool compatibility remains separate. Host-check time/version are internally validated and hidden from Summary/check details. See Component_Model_Connection.md.


## Project setting scope and guidance

Project Settings displays the selected project's operational settings, including inherited defaults. Executor/model/authentication settings and the applicable OpenCode endpoint form belong to Settings → Agent and model. Descriptions remain permanently below each label and provide the editor's accessible description. There is no per-row Help disclosure or override-only filter. The default/source marker describes value origin, not ADORE-wide scope. Polling intervals, per-project concurrency, executor and recovery settings remain per-project within Settings; environment setup is externally managed. Global capacity and audit retention belong to Administration. No project setting is promoted into a global policy by this presentation.

Proof: web/e2e/settings.spec.ts project settings keep defaults and single guidance (administrator/developer), plus existing candidate edit/discard journey.

## Project executor configuration

**Project → Settings → Agent and model** owns the default coding agent, the selected agent's launch command/model, AI connection testing and external container guidance. Its **Authentication** disclosure groups allowed credential variable names, host sign-in reuse and **Provider API keys**. The agent editor offers OpenCode, Pi, Codex and Qwen Code even when their command tables are absent. Selecting an agent loads its saved command/model or the documented command preset; a new model ID must be supplied explicitly. Prepare reviews agent, command and model together, then Apply writes one complete paused/idle candidate. The generic launch-command/model labels follow the selected agent. Edit keeps agent, command and model controls inside their existing description/value rows; the default-agent row owns Prepare/Cancel for the complete draft, beside its dropdown using the shared editor layout and normal responsive wrapping. Grouped-edit guidance stays in the description column. Validation occupies its own line after the controls, keeping selector/actions aligned when the selected agent needs a model; Prepare remains disabled until the complete draft is valid. Credential names are added through a dropdown and remain visible as individually removable selections. Installed agents and runtime preparation remain external. The old `/executor` URL redirects to Settings. Developers read non-secret settings/results without mutation actions.

The names-only credential selector offers known provider names and retained custom names, independently of coding agent. Empty lists support existing server sign-in. Applying names does not delete saved `.env` values. Provider API keys offers private Save/Disconnect for known allowed variables and shows sources only; key changes require paused pickup and idle/pending-free state. Explicit Test AI connection remains the evidence of model access and may incur provider charges. Subscription login retains the installed CLI's external service-account workflow. See [Executor configuration](../05_SoftwareDocu/Component_Executor_Configuration.md) for the exact API/storage contracts.

### Transient application notifications

The application shows one dismissible notification for ordinary feedback or the current operation. Operation status replaces the queued confirmation. Pending/running operations stay visible until completion or dismissal; terminal results and ordinary notices disappear after five seconds. Closing the banner keeps worker polling and final project refresh active. Replacement/unmount cancels earlier dismissal timers; persisted outcomes remain available in History. Error alerts retain their existing presentation.

Editable settings place **Edit** beside **Active value** in the value column, including narrow screens. Administrators retain candidate review/apply/discard and disabled-state safeguards; developers have read-only rows.

Project Settings purpose categories are collapsed on entry. Opening a category shows equal-width description and active-value columns separated by24px; below640px they stack at full width. Native disclosures retain keyboard operation. Agent and model groups AI connection, selected-agent settings, closed Authentication and external environment guidance. Its inline field editors retain the existing row columns and stack using the normal mobile layout; the credential-name dropdown and removable selections wrap within the value column.

## Preparation review and outcomes

`executionPlan.ts` validates closed public plan/outcome envelopes. `ExecutionPlanReview.tsx` renders image authority, source/job/revision, hashes and all commands in retained candidate reviews, with four-locale guidance. `PreparationResults` renders persisted attempts and step outcomes in job details and explicit CLI replay guidance on failure. Incomplete/forged evidence cannot display preparation success or enable an unbound recipe Apply. Focused tests: `web/tests/executionPlan.test.mjs` and external ownership journeys in `web/e2e/settings.spec.ts`.

## Native execution contract

Native execution is selected externally in the server profile or through server TOML enrollment. Existing native executor/model and explicit host checks use that prepared environment. The container notice is omitted for local projects. See [Local execution](../01_Documentation/Local_Execution.md) for machine/account, authentication and process ownership.

## Project image workspace

Settings → Agent and model shows a compact container notice with the effective image and one expandable instruction disclosure. It identifies standard `executor/Dockerfile`, optional `executor/README.md`, a non-root example, external Docker/Podman build and verification, and the existing profile fields. Only administrators see the actual resolved server `config.toml` path. No controls define, build or select an environment. Guided creation configures agent/model with the standard container defaults; specialized container/local profiles use server TOML enrollment. Historical records remain readable/exportable/cancellable; old pending candidates can be discarded, and queued image-build requests fail without runtime execution. See [Project executor images](../01_Documentation/Project_Executor_Images.md).

`ExecutorEnvironment.tsx` renders read-only four-locale content from the config response. `App.tsx` filters container/execution/local/worktree settings from both settings lists. Legacy environment candidates show disabled Apply and retain Discard. `images.spec.ts` proves the disclosure, Admin/Dev scoping, local suppression and mobile wrapping; `test_web_image_build.py` proves typed API/worker refusals.

External environment refusals and preparation/model/credential failures have four-locale corrective messages in errors.ts; errors.test.mjs verifies complete server-code coverage and preserved diagnostic/generic fallback.

## Polling settings guidance

The shared settings list retains Ticket checking mode, Ticket check interval,
Wait longer after ticket service errors and Random check delay. Localized help
in English, French, German and Romanian states that interval, error backoff,
random delay and quiet hours apply to automatic web polling and CLI loop.
Ticket checking mode governs standalone CLI startup; the web worker owns its
repeated rounds. Editing/review/apply permissions and configuration keys remain
owned by the existing settings API. See Component_Web_Worker.md and
Component_Polling.md for runtime scheduling contracts. Existing settings/catalog
browser and helper tests verify the shared presentation surface.

## Agent selection editor

executorSettings.ts supplies four-locale generic labels, exact selection/list guards and existing-value drafts; ExecutorSelectionEditor.tsx renders one draft field in each existing row, choosing saved commands/models or server presets and requiring an explicit model for a new agent. CredentialNamesEditor.tsx adds distinct names from a native dropdown and shows removable selected names; duplicates are disabled and malformed drafts cannot enable preparation. SettingsList hides other agents' command/model rows, groups private API keys inside Authentication, and PendingReview displays changed selection fields and discloses all three in the complete comparison. routes.ts redirects old /executor links to /configuration for both roles. The field editors and selected-name list wrap at390px without horizontal overflow. Offline executor/settings/images/model-connection browser journeys cover migration, role boundaries, four locales and narrow layout.
