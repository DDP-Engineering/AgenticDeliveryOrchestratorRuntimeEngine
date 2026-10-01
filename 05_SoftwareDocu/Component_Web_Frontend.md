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

It provides login, project and job views, role-appropriate metrics,
administrator project/account setup, settings, four language catalogs,
an administrator audit trail, light/dark/system themes and an About dialog.
Administration expands into System status, Users, Audit and Settings in the
sidebar. Developers see My account for their own preferences and password.
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
use their own status, membership and preference controls. Jobs and Metrics
keep their project selectors in page content. On Overview, four expandable summary cards select the scope:
Projects opens a table of authorized projects where a row selects the project,
and Active jobs, Awaiting review and Failed jobs open paged run tables for the
selected project. Closing a card restores Recent jobs. Opening a run navigates
to its Jobs detail; opening a project navigates to Project details. Content
starts directly with the page's controls and data; at narrow widths the title
and actions wrap into separate rows. Statistic hints and user rows wrap
instead of clipping or colliding on small screens.
Jobs places its authorized project selector in page content beside the ticket
and Start job controls. Ticket Help explains the existing repository issue
number, positive integer format, example and eligibility checks in each locale.
Switching that selector clears the ticket draft. Archived projects retain the
selector for history while hiding ticket and Start controls. The form wraps at
narrow widths; the header contains the page title and common actions.
Administration's account section is labelled Users in every locale.
Jobs aligns Observed executor and Outcome contains in two equal-width fields
below the basic filters, stacking them at narrow widths. Each has localized
Help and an example placeholder. Executor matches the exact case-sensitive
name recorded in the ADORE job journal; jobs with no recorded name are excluded
by that filter. Outcome matches a case-insensitive fragment of ADORE's saved
result or error explanation, which may contain AEGIS error details. These
fields search recorded ADORE data rather than full AEGIS/executor logs.
Inputs retain the 200-character executor and 80-character outcome bounds;
blank values omit that filter.
The About dialog constrains its width and height to the viewport, with internal
scrolling for the license and notice content and an accessible Close button.
Add project opens a separate administrator page from Projects. The form gives
each field a localized Help disclosure with expected values and purpose. The
clone path hint identifies the ADORE host and requires an existing local clone.
The executor image field accepts either a suggested image tag or a custom tag;
suggestions are examples, not an inventory of installed images. The image must
already be present on the host. The form offers host-auth only for OpenCode and
Codex; selecting Pi or Qwen limits authentication to API-key mode, matching
server validation. Successful creation opens the new project's details; a
Back to projects or Cancel action returns without creating a project.
About displays the project license text and the bundled third-party notices.
Projects show archived state and let administrators archive or restore a
quiescent project. Archived jobs and metrics stay visible, while job and pickup
controls are hidden until restore.
Import project opens a separate administrator page from Projects. Its name,
description and file fields have localized Help disclosures. An administrator
selects an existing `config.toml`, reviews its validated identity, state path
and issues, then imports that exact revision. The form explains that paths
must be absolute on the ADORE host, the file remains unchanged and pickup
starts paused. The file text stays in browser memory for the two requests;
it is not displayed in the preview and is cleared on leaving the page.
Successful import opens the new project's details; Back to projects and Cancel
return to the Projects directory without importing.
The Projects directory lists authorized projects in a sortable, paged table
with project, repository, static config status, job
count and last activity columns. Administrators can pause/resume pickup and
archive/restore directly on each row; developers can open details but see no
mutating actions. A valid configuration is labelled as such, not as a live
forge or model readiness check.
Selecting a project opens a scoped detail view with status, repository,
runtime, executor, last activity and recent jobs. Its actions open the Jobs and
Metrics views for that selection, and jump to project settings on the same page.
Assigned developers can inspect the redacted effective configuration in
collapsible sections. Each field shows its type and contextual help; common
settings also describe their valid domain. Administrators can stage and apply
project configuration, local endpoint and estimated-price changes there, while
membership management remains under Users. Administration/Settings holds
account appearance and password controls.
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
a different profile that later uses the old name. Settings also presents administrator price versions; Metrics separates reported
and estimated USD values, displays unpriced-event coverage, groups project
totals by non-empty repository label, shows global reported/estimated daily
amounts separately, adds a combined daily view for the selected repository,
and links to administrator global CSV.
The Metrics page keeps its authorized project selector, inclusive date range, IANA reporting timezone,
day/week/month grouping and CSV export menu above five category tabs: Summary,
Usage, Quality, Trends and administrator-only Projects. Administrators initially
see All projects, with pooled headline totals and a paginated project breakdown
in Summary. Selecting one project scopes every category, project/repository
comparison and export to that project. Project details opens Metrics for that
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
Metrics shows terminal job elapsed-time sample count, average and median. The
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
Administrators can trigger a replay of retained usage journals from Metrics;
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
The guided form offers labelled repository, forge, runtime, executor, polling
and run-limit settings with their current values. An expandable advanced form
accepts other validated scalar keys.
Metrics also shows reviewer-requested MR/PR revisions and automatic pipeline
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

`App.tsx` manages session, selection and requests. `i18n.ts` contains EN/FR/DE/RO
strings. `styles.css` defines responsive layouts and themes. Session cookies
remain HttpOnly; only the CSRF token is held in application memory. Language
and theme preference are kept in browser local storage.
Before login those browser values are the fallback. After login, saved account
preferences load before the authenticated shell appears; Settings writes a
changed language or theme to that account. A failed save restores the previous
choice. The login screen offers both language and theme controls.

## 4. Dependencies

React is bundled locally. Node.js and npm are build-time only; the deployed
browser assets do not fetch fonts, scripts or translations from a CDN.

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

`npm run build` performs TypeScript and Vite checks. Backend tests prove RBAC
and cost omission. Chrome checks covered 360px and 1920px layouts, all four
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
document-level horizontal overflow on Metrics at 360, 768, 1024, 1366, 1920,
and 2560px. A 180px effective-width check, representing 200% zoom on a 360px
display, also remained within the document width. French, German and Romanian
Settings views retained document language and had no 360px overflow.

## 10. Limitations And Future Work

There is no dedicated frontend automated journey suite or live log streaming.
