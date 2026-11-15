<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Web frontend

## Purpose and source ownership

`04_Software/web/` contains the React/TypeScript interface. Vite produces the
same-origin assets in `04_Software/adore/web/static/`, included in the wheel.
`App.tsx` owns the authenticated shell; `routes.ts` owns route interpretation.
The API remains authoritative for authorization, configuration and job actions.
See [Web API](Component_Web_API.md) for server boundaries and
[Web interface](../01_Documentation/Web_Interface.md) for operating instructions.

## Navigation and scope

The sidebar exposes Overview, Projects, Jobs, Tickets, Statistics, Administration
and My account according to the user's role. The project hub exposes Summary,
Settings, Jobs, Tickets, Statistics, History and Access according to grants.
Project capacity appears in Summary. Global Jobs retains its capacity view.

Jobs and Tickets are separate workspaces, both with all-authorized-project or
single-project scope. Jobs retains search, filters, column sorting and pagination.
Tickets reads automatically on entry and scope changes; Read tickets remains
available for manual refresh. Ticket number, project, title, labels and status
sort before pagination, both globally and in Project → Tickets. Actions is not
a sortable column. Changing a selection fences pending requests for the old scope.

`JobWorkspace.tsx`, `TicketWorkspace.tsx`, `PagedTable.tsx` and `SortHeader.tsx`
own these views. Scope, filters, sorting, page and open detail state survive
ordinary refreshes and returning from a job. Composite job identity is project ID
plus run ID; a run ID alone cannot select a job across projects.

## Job details presentation

`JobDetails.tsx` exposes exactly three tabs: Activity, Agent sessions and Job
details. Tabs, Show ticket and right-aligned Close sit above the ticket title.
The compact status line shows lifecycle, stage, workflow and project. Job actions
remain separate from saved activity. Budgets and consumption form a vertical
right-hand panel; they measure consumed work and do not imply stage progress.

- Activity uses a paged table with a visible-row limit. A session link opens the
  matching Agent sessions attempt only when the saved event identifies it.
- Agent sessions displays retained prompts, assistant replies, readable reasoning
  and tool calls/results. Session label, selector and live status share a compact
  row. A live attempt is labelled once. Historical sessions remain readable.
- Job details combines job/branch identity, counters, retained outcome and collapsed operational diagnostics. Missing source coverage
  appears only when relevant; there is no Usage coverage row. There is no separate Artifacts tab
  and no duplicate Original recorded events table.

### Agent sessions

`SessionView.tsx` and `sessionModel.ts` validate responses, retain attempt
selection and progressively load complete-line cursor pages. Reasoning and tools
can be expanded; messages use a flat layout. Optional message timestamps are
shown only when recorded. The conversation has bounded height and internal
scrolling; appended records do not expand the page indefinitely.

Maximize uses the page area for the session. Restore or Escape returns to normal
layout while retaining the selected attempt, loaded conversation and draft.
The session selector aligns with the conversation area. Live status is separate
from the attempt label and can name the current tool or thinking state.

Live reads poll every three seconds only while the view is selected, visible
and following the live attempt. Hidden views fence in-flight responses and keep
accepted history pages. Explicit history selection stops following. At completion
the view loads the archive or follows the next launch; it never splices bytes
from different attempts into one transcript.

`InstructionComposer.tsx` provides Message to the agent with Send now and Queue
message to its right. Empty drafts and historical selections cannot submit.
Between launches, following the current job keeps Queue message available.
The draft remains local until submission; acknowledgement updates the durable
instruction status. See [Instructions](Component_Instructions.md) for delivery
semantics and crash boundaries. Green primary buttons and outlined secondary
buttons reflect the action's role; disabled controls remain visibly disabled.

## Project enrollment and settings

Guided setup resolves repository source, validates the proposed configuration,
reviews environment/model prerequisites and publishes the checked candidate.
Raw TOML import and source-bundle ZIP import/export remain distinct operations.
There is no browser portable-settings JSON import/export panel; the administrator
API is described in [Portable settings](Component_Portable_Settings.md).

Settings uses per-row editors and a retained proposed-change review. Drafts are
bound to project and session identity. Applying changes rechecks the base revision
and safe execution boundary; navigation cannot apply another project's draft.
The effective state folder is read-only. Statistics database location is
informational; metrics output paths are configured in TOML/CLI.

Agent and model configures Pi, provider/model, an optional OpenAI-compatible
endpoint, thinking level, internet access, web search, credential names and
execution environment. Provider credentials are private Save/Disconnect inputs;
saved values are never returned. The provider's required key is selected
implicitly, while additional variables use an explicit names-only allowlist.
ChatGPT subscription uses `ChatGptSignIn.tsx` and the server-owned sign-in.
Explicit Test AI connection may contact the configured model.

Container projects select a runtime and locally available image. Project-specific
image builds are external; retained recipes support review and source export.
Local projects use managed Pi under the server account and optional project tools
PATH. The interface distinguishes host networking from the container internet
policy. See [Project images](Component_Project_Images.md),
[Local execution](Component_Local_Execution.md) and
[Model connection](Component_Model_Connection.md).

Repository connection, readiness, branch-name preview, pending configuration,
publication approval and reviewer-list editing use the server's reviewed
contracts. Stopping pickup prevents automatic new admissions; it does not stop
active jobs. Start explicitly requests one eligible ticket even when pickup is
paused. Confirmation is required for destructive restart/delete actions.

## Rendering, preferences and request ownership

`forgeMarkdown.ts` renders forge Markdown through the pinned Markdown/GFM
libraries. Source links and images pass their own URL checks; HTML and repository
text do not become executable markup. Plain/Markdown body mode is an account
preference. Project grants determine which data may be requested.

English, French, German and Romanian catalogs supply interface copy.
Light/dark/system theme, language and account preferences remain account-scoped.
`HelpCenter.tsx` renders the matching four-locale Markdown topic catalog;
`help/README.md` defines its format. About reads release identity and translated
release notes from the server. See [Release notes](Component_Release_Notes.md).

Request generations bind responses to the current account, project, scope and
revision. A late response cannot repopulate a previous view. Loading, empty and
failed states are distinct. Refused refreshes withhold unverifiable totals;
selected session history and editor drafts retain their own accepted state.
Transient notifications do not replace persistent errors or confirmation.

Semantic navigation, current-page markers, keyboard focus, labels, associated
field help and error states are maintained with the controls that own them.
Dates are formatted for the selected locale; missing evidence is not rendered as
successful progress or zero consumption. Financial views follow role checks.
Literal authorized session text is distinct from redacted operational output.

## Dependencies and validation coverage

The frontend depends on the checked-in npm lockfile, React, TypeScript, Vite and
the server API. Build automation is in `02_Tools/build/`; application source and
frontend contract/browser tests remain in `04_Software/web/`.

Existing `web/tests/` cover route, job/session, instruction, sorting, preferences,
settings and help contracts. Existing `web/e2e/` journeys cover authentication,
enrollment, project access, Jobs/Tickets, recovery and settings against controlled
local APIs/workers. Test locations are relative to `04_Software/`.
Deployment/environment setup scripts have no product test workflow.

## Limitations

The browser projects retained evidence; it does not recover deleted transcripts
or infer unrecorded stages. Archived conversations are read-only. Live refresh is
bounded polling rather than text-delta streaming. Native execution uses the host
account's permissions; the interface cannot provide a host sandbox.

## Shared workflow choice

WorkflowChoice loads authorized new-job defaults and payload presence, validates the response and waits for it before enabling submission. TicketWorkspace always opens confirmation and sends the selected aegis/direct value in both scopes. JobDetails uses the same validated capability response for two explicit Restart buttons. JobWorkspace uses a short native confirmation, including the selected mode, and sends that mode with the saved state revision; no page-level confirmation panel is rendered. Retry has no selector or workflow override. Four-locale workflowCopy and settingHelp cover labels, defaults, unavailable AEGIS and the Direct instruction boundary.

Ticket Start confirmation uses a wrapping flex row for Workflow, required Priority
and the Start/Cancel actions in both global and project scopes. WorkflowChoice
suppresses its helper paragraphs there; loading/error states and disabled AEGIS
options still apply. Job actions removes Retry/Restart helper paragraphs and keeps
its compact mode buttons together. Label mutations
and the explicit selected-workflow request contract are unchanged.
