<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web frontend

Project details groups its three metadata rows with a 4px gap and separates
the action row by 18px; long values wrap within the panel.

Secondary text uses contrasting light/dark theme colours. Project metadata,
configuration values, type/domain hints and field help use 0.875rem text with
1.5 line height; long identifiers and guidance wrap within their panels.
On narrow screens, setting labels, values and help stack vertically.

## 1. Purpose

`04_Software/web` is the React/TypeScript source for the responsive ADORE
dashboard. Vite compiles it into `adore/web/static` for same-origin serving.

## 2. Responsibilities

The shared shell presents Overview, Projects, Jobs and Statistics as semantic
links, with My account for each authenticated user and administrator-only
System status, Users and Change history. The approved DDP Engineering sage
PNG is displayed on the dark navigation panel at its original 630:300 ratio,
separately from ADORE. Source SHA-256:
`4957da4edf9aebf02dcb0e24823ff5f8d5ee524622773f4285c9e2261903c481`.
The binary inherits the provenance documented in the published design bundle.

Project context shows the authorized project's name and repository with links
to its details, jobs and statistics. Overview also offers a project selector
and distinguishes the all-authorized-project count from selected-project job
counts. Jobs reads the selected project's existing endpoint. Administrator
all-project Statistics labels that scope explicitly. The Statistics page keeps
the established `/metrics` route, exports and query parameters.

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
Audit has administrator day and MiB retention controls populated from saved policy.
Unlimited limits display zero; zero or blank saves as null in the API. Days are
whole numbers through 36500, sizes are finite MiB through 1024 and round to
positive whole bytes. Fractional MiB preserves policies below one MiB. Invalid
values are rejected before a request with localized guidance. Successful saves
restore the canonical saved/default display, including zero for unlimited.
`src/auditPolicy.ts` owns conversion; offline `tests/auditPolicy.test.mjs`
covers saved/default values and rejected input.
Tables with more than ten rows offer 10, 25, 50 and All choices with
Previous/Next for finite pages. Audit fetches the full authorized history;
Jobs delegates the page size and filtering to the scoped API. Other tables
paginate their rendered rows and reset to the first page when size changes.
Selected-ticket history uses the shared paged table with Date, Event and Stage
columns in reverse journal order, with latest events first. A reversed copy
preserves the received event array. It starts at ten events per page, offers 10/25/50/All
for longer histories, and resets on project/run identity changes. Empty history
uses the standard empty state; event text remains escaped by React.
The top bar supplies the single page title and common actions on every page.
Project details uses the identity opened from Projects; platform administration and account settings
use their own status, membership and preference controls. Jobs and Statistics
keep their project selectors in page content. On Overview, four expandable summary cards select the scope:
Projects opens a table of authorized projects where a row selects the project,
and Active jobs, Awaiting review and Failed jobs open paged run tables for the
selected project. Closing a card restores Recent jobs. Opening a run navigates
to its Jobs detail; opening a project navigates to Project details. Content
starts directly with the page's controls and data; at narrow widths the title
and actions wrap into separate rows. Statistic hints and user rows wrap
instead of clipping or colliding on small screens.
Jobs places its authorized project selector in page content beside the ticket
and Start job controls. Visible ticket instructions explain the existing repository issue
number, positive integer format, example and eligibility checks in each locale.
Switching that selector clears the ticket draft. Archived projects retain the
selector for history while hiding ticket and Start controls. The form wraps at
narrow widths; the header contains the page title and common actions.
Administration's account section is labelled Users in every locale.
Jobs aligns Observed executor and Outcome contains in two equal-width fields
below the basic filters, stacking them at narrow widths. Each has visible localized
instructions and an example placeholder. Executor matches the exact case-sensitive
name recorded in the ADORE job journal; jobs with no recorded name are excluded
by that filter. Outcome matches a case-insensitive fragment of ADORE's saved
result or error explanation, which may contain AEGIS error details. These
fields search recorded ADORE data rather than full AEGIS/executor logs.
Inputs retain the 200-character executor and 80-character outcome bounds;
blank values omit that filter.
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
with project, repository, static config status, job
count and last activity columns. Administrators can pause/resume pickup and
archive/restore directly on each row; developers can open details but see no
mutating actions. A valid configuration is labelled as such, not as a live
forge or model readiness check.
Selecting a project opens a scoped detail view with status, repository,
runtime, executor, last activity and recent jobs. Its actions open the Jobs and
Statistics views for that selection, and jump to project settings on the same page.
Assigned developers can inspect the redacted effective configuration in
collapsible sections, with the common settings first. Each row shows its value,
a Set for this project / Default badge, its type and contextual help; common
settings also describe their valid domain. A checkbox limits the list to
settings set for the project (`web/src/settings.ts` builds and groups the
rows). Each row's Help shows the setting's own text in the selected language
from `web/src/settingHelp.ts` (keyed by the catalog `web/src/settingKeys.json`,
with `*` for project-chosen names) and its ADORE default. Administrators can stage and apply
project configuration, local endpoint and estimated-price changes there, while
a developer's projects are edited together under Users, and one project's
developers on its Access tab. My account holds account
appearance and password controls. Project details groups this content into
Overview (host prerequisites, recent jobs), Configuration (read-only settings
and administrator editors) and administrator-only Prices and Access tabs with
keyboard tab navigation; Jobs and Statistics are real links. Access
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
The Jobs view retrieves ten runs initially for the selected project, with
lifecycle, AEGIS-stage, UTC last-update date and outcome-text filters. The overview retrieves seven recent runs
and full lifecycle counts. Status and stage labels use the selected language.
An observed-executor filter further narrows the Jobs page using recorded run
evidence; older runs without that identity do not match it.
The About dialog traps keyboard focus and returns it to the opening button on
close. A compact top-bar Sign out control remains available when the sidebar
account controls are hidden on narrow screens.
Project selection and project API routes use the immutable profile ID, so a
profile rename preserves the selected project and does not retarget actions to
a different profile that later uses the old name. Settings also presents administrator price versions; Statistics separates reported
and estimated USD values, displays unpriced-event coverage, groups project
totals by non-empty repository label, shows global reported/estimated daily
amounts separately, adds a combined daily view for the selected repository,
and links to administrator global CSV.
The Statistics page keeps its authorized project selector, inclusive date range, IANA reporting timezone,
day/week/month grouping and CSV export menu above five category tabs: Summary,
Usage, Quality, Trends and administrator-only Projects. Administrators initially
see All projects, with pooled headline totals and a paginated project breakdown
in Summary. Selecting one project scopes every category, project/repository
comparison and export to that project. Project details opens Statistics for that
project. Developers select assigned projects and receive operational data only.
The export menu offers metrics and usage CSV files for the current scope;
global choices appear only in administrator All projects scope. Arrow keys, Home and End switch tabs,
and the shared controls retain their values when categories change. On compact
screens project selection spans a full row above the four period controls in
two rows. Switching projects retains the category and reporting parameters;
selected-project metric/usage requests and CSV links use the new project ID.
The filters are shared by the scoped tables and CSV links.
It displays period totals separately from
all-time headline totals; period sums use dated journal events and may omit
legacy summary-only usage. Range changes discard stale metric responses.
The all-time launch coverage panel counts reported-token, unavailable-token,
and disabled-capture launches from versioned observations; cost-status counts
are visible only to administrators. It explains that older launches have no
classification and unavailable does not mean zero.
Statistics shows terminal job elapsed-time sample count, average and median. The
selected local-date range also scopes a separate duration sample by completion day.
Missing timestamp evidence appears as unavailable rather than a zero-second
average; the explanation notes that elapsed time includes human waiting.
The administrator project comparison table includes sample count and average
per project; it does not average the per-project averages into a global value.
The attributed-usage tab uses the same timezone, grouping and date range plus exact
executor/model text filters. It displays observed usage-event and token totals,
scoped trend rows, and administrator All projects breakdown rows with
reported/estimated amounts. Its CSV options carry the same filters. Main job
counts and all-time headline metrics stay independent of usage identity.
Session changes and filter changes discard stale usage responses.
`src/metrics.ts` pools validated project responses: additive counts, nullable
cost/cache evidence, and date/executor/model buckets. Quality rates use pooled
numerators and denominators; USD per job uses evidence-weighted cohort totals.
Elapsed-time averages and medians use individual terminal spans, including
zero-second samples. Period duration selects completion days in the chosen
timezone, independently of week/month bucket labels. Missing evidence remains
unavailable. Invalid numeric/duration evidence raises a RangeError.
Offline `npm test` (Node.js 22.18 or later) covers these calculation contracts,
empty cohorts, timezone boundaries and corrupt evidence; the canonical AEGIS
verification includes this frontend test command.
Signing out and signing in as another role returns to Overview, so an
administrator-only view cannot remain selected for a developer. Asynchronous
user creation and config staging keep their form reference until the request
completes, allowing the form to reset after a successful response.
Administrators can trigger a replay of retained usage journals from Statistics;
the button reports the reconciled event count and refreshes attributed views.
The local endpoint form is shown for OpenCode profiles. It saves model ID and
URL in one request and explains the required provider package in the executor
image. An optional allowlisted environment-variable name references an API
key without collecting its value in the browser. The form exposes the supported
chat-completions protocol, bounded request timeout, and HTTPS custom-CA file
path inside the executor image. Its pending-change panel shows the resulting
endpoint fields before Apply.
Settings stages scalar and local-endpoint changes for administrator review.
The panel shows the changed value, candidate revision and pause guidance for
identity/runtime edits. Apply commits the candidate at a quiescent boundary;
Discard removes it. The UI reloads the live revision after either action.
Administrators edit an editable setting on its row (select for choices and
booleans, number or text input) and stage it into that panel; rows note when
applying needs paused pickup, and non-editable rows say to change the
project's config.toml on the ADORE host. The whole-number common settings use a
step and minimum of 1; other number rows accept any number and the server
validates the value.
Statistics also shows reviewer-requested MR/PR revisions and automatic pipeline
repairs as distinct counts; unknown revision triggers appear in coverage.
The Delivery quality panel shows reviewer-rework, first-validation, and
first-pass human-merge rates with visible numerators and denominators, plus a
still-open review count. Empty cohorts display unavailable instead of zero.
It shows stage failures and operator retries separately. Administrators also
see reported and estimated USD per completed and human-merged job, each with
the count of jobs carrying that kind of cost evidence.
These are all-time job cohorts, independent of the UTC daily range. The
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

`DashboardShell.tsx` owns the authenticated frame, real navigation links,
branding, responsive menu, header and content focus. `Presentation.tsx` owns
`DataFeedback`, `ProjectEmpty`, `StatusBadge` and `DeliveryGlossary`.
`App.tsx` owns session, supported mutations, existing route/history flow and
scoped request states. Request completion retains session-generation guards
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
visible and refreshes immediately when it becomes visible. `ServerPager`
drives the Jobs, Audit and Overview job tables, requesting one bounded page
(`limit`/`offset`) per view and every row only for All. Example placeholders
use the `--placeholder` token (at least 4.5:1 in each theme) with a localized
"e.g." prefix; `Field`/`GuidedField` add a required marker and each form with
a required control shows a localized legend. `.table-scroll` uses CSS scroll
shadows, and the Jobs filters collapse behind a counted toggle below 760px.
Project names in the Projects table and ticket numbers in every job table are
links; a job's ticket or View opens it in Jobs. Overview card hints state the
scope ("Projects you can access", "Project: <name>"). Expand/collapse
indicators and sign-out use inline SVG icons (`Icon`) drawn in `currentColor`.
The Prices form preselects the project's configured executor and remounts per
project. When the Statistics scope has no jobs, Summary, Quality and Trends show
one localized message instead of zero-valued cards.
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
`playwright.config.ts` owns browser timeouts, one-worker execution, failure
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
