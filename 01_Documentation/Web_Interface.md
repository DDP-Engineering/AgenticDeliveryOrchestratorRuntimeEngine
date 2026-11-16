# Web interface

The web application uses the same profiles, configuration and job state as the
CLI. The API handles authenticated requests; one local supervisor runs independent
project and configuration processes. See [Getting started](Getting_Started.md)
for startup and [Operations](Operations_Guide.md) for workflow/recovery rules.

## Sign-in, roles and preferences

Only a newly created identity store receives the initial admin/admin account.
Change its password from My account. Existing stores keep their accounts.
Administrators manage accounts, project grants, service controls and protected
credentials. Developers see and operate only authorized projects; the server
rechecks rights for requests and queued operations.

The interface supports English, French, German and Romanian, and light, dark or
system themes. Account presentation preferences are separate from project settings.
How ADORE works opens the help center; About shows the release, license and notes.

## Navigation and scope

| Page | Purpose |
|---|---|
| Overview | Cross-project work and attention summary. |
| Projects | Enroll, open, archive/restore and administer projects. |
| Jobs | Follow admitted jobs, with all-project or selected-project scope. |
| Tickets | Read eligible/ineligible source tickets with independent project scope. |
| Statistics | Consumption, quality and trends for the selected reporting scope. |
| Administration | System status, users and change history, subject to role. |
| My account | Password and account preferences. |

Project pages have Summary, Settings, Jobs, Tickets, Statistics, History and
administrator Access tabs. Project Jobs and Tickets have a fixed owning-project
scope. Capacity is shown in Summary rather than a separate project tab.

## Enrollment

Azure DevOps Services enrollment recognizes Azure Repos cloud URLs and exposes
organization, project and exact repository-owned Work Item Area Path. Repository
settings include allowed Work Item types and terminal states as reviewed lists.
The usual Admin/Developer, pause/idle, preview/apply and worker polling rules
remain unchanged. Azure sign-in is external to normal GUI forms; no token is
stored in browser settings. Label helpers verify attachment readiness rather
than creating a repository label catalog. See [Azure DevOps Services](Azure_DevOps_Services.md).

Start from Projects. Supply the repository address and use Read repository to
resolve the forge, target branch and project identity. Review the server clone
location, selected execution environment, provider/model and credential references.
ADORE owns new clones it creates; existing clones must identify the same repository.

Repositories may have AEGIS or use Direct. File inspection is not proof that an
installed payload is supported; the live job probe validates that contract.
ADORE does not install AEGIS in the target repository.

Structural validation, Check host prerequisites and Test AI connection are
separate operations. Model testing sends a bounded request and can incur provider
charges. Version/credential presence alone does not prove model access. Container
images and host tools must be prepared for the selected environment.

Review the exact project/settings summary before Create. Back or Change allows
correction; edits invalidate the prior verification. A creation failure is not
automatically resubmitted. Check Projects if the result was uncertain.

## Summary and project access

Summary shows project identity, monitoring, current capacity and attention state.
Administrators can connect a project-scoped repository token, inspect prerequisite
results and administer access. Repository read verification is separate from host
Git clone/push authentication. See [Security](Security_And_Credentials.md).

Access grants use the project identity and are rechecked at effect time. Archive
stops pickup and keeps retained information; destructive deletion has its own
confirmation and ownership checks.

## Tickets

Opening Tickets reads its selected scope automatically. Read tickets remains
available for an explicit refresh. Global Tickets can select all authorized
projects or one project; the project tab always uses its own project.

Use the column headings to sort number, project where shown, title, labels and
status across the loaded results before pagination. Start/Retry/Stop/Details
availability follows recorded eligibility and job state. Manual Start remains
available while monitoring is paused, but cannot bypass readiness or capacity.

Manual Start opens a compact row with Workflow, Priority when required,
Add labels and start, and Cancel. Wide screens keep them together; narrow
screens wrap the controls. Start no longer repeats explanatory paragraphs.

## Jobs and History

Jobs keeps search, lifecycle filters, sortable columns, pagination and project
scope. Each row shows the saved status, Workflow, current Stage and consumption.
History shows the selected project's terminal jobs. Opening a job preserves its
project/run identity; automatic refresh must not reset the selected view.

Stage and lifecycle are distinct. Done can mean the engineering stages finished
while approval or human review is still pending. Old activity timestamps are
recorded evidence age, not proof that an executor stopped.

## Job details

The command row contains Activity, Agent sessions and Job details, with Show
ticket and Close on the right. The ticket title follows, then a compact row with
job status, stage, workflow and project. Applicable job actions use their own menu.
The right-hand panel contains Job budgets and Consumption.

### Activity

Activity is the single recorded-event table, with a visible-row limit and page
navigation. Events show their time, event name and recorded stage. Open conversation
appears only when retained launch evidence uniquely identifies the session. It
selects that conversation in Agent sessions; no session is guessed from proximity.

### Agent sessions

Session, its selector and live activity share a compact row above the conversation.
Select the current or a completed attempt. Live appears once in the selector;
the adjacent indicator describes observed thinking/tool activity.

The transcript shows retained prompts, agent/user messages and expandable reasoning
and tool calls/results. Message text uses the retained recording; missing historical
content is not reconstructed. The conversation has a bounded viewport and internal
scroll. It follows new messages while at the bottom; New messages returns there
after reading earlier content.

Maximize fills the page with the conversation. Restore or Escape returns to the
normal layout without replacing the selected session or composer draft.

For working jobs, enter Message to the agent. Send now submits at the next safe
agent boundary; Queue message waits for current work to finish. Buttons sit beside
the message box on wide screens and below it on narrow ones. Between sessions,
queueing remains available for a working job; historical conversations are read-only.
A queued/received/failed status describes delivery, not completed implementation.
Empty messages disable sending. Invalid input is explained when submitting.

Session access is project-authorized. Retained RPC text can include secrets the
agent printed; it is not rewritten into a sanitized transcript. Structured cost
fields remain administrator-only. See [recorded session visibility](Security_And_Credentials.md#recorded-agent-session-visibility).

### Job details

Job details presents the saved result, branch, last published commit when recorded,
MR/PR link and review rounds. A missing recorded field is shown as unavailable.
Read the question opens a pending clarification; approval/review links remain
available near the status when human action is needed.

Diagnostic starts collapsed and contains internal IDs, current-stage failures,
preparation/direct evidence and the latest normalized executor output. It does
not repeat the Activity table. Normalized operational output and a full session
recording have separate retention/redaction contracts.

### Budgets and actions

Job budgets shows executor launches and active seconds against current limits.
Consumption distinguishes tokens, reported/estimated costs and missing coverage.
Administrators can follow Adjust budgets in project Settings. Limits are not a
percentage of job progress, and waiting time does not consume active work.

Retry, Cancel and both explicit abandon-and-restart actions follow confirmed worker outcomes.
Acceptance/queueing is not completion. Destructive recovery requires confirmation;
see [Operations](Operations_Guide.md#recovery).

Primary actions use the accent background; secondary navigation/actions such as
Queue message and Close use a border. Destructive actions use the danger style.
Disabled actions are visually muted.

## Settings

Settings separates Repository, Tickets, Implementation, Agent and model, and
Statistics concerns. Categories begin collapsed. Administrators edit supported
settings; developers retain authorized non-secret read-only information.

Review/apply binds the proposed values to the current configuration revision.
Important changes require monitoring paused, no conflicting work and confirmed
worker completion. A safe budget-only change can apply at a clarification wait.
Other projects and already-running attempts retain their own snapshots.

Ordinary unsaved settings drafts survive navigation in the same account/project/
browser tab and are bound to their base revision. Save, Discard and sign-out clear
them. Stale/corrupt drafts cannot be saved blindly. Credential editors remain
separate and do not retain their values as ordinary presentation drafts.

Provider/model/endpoint are reviewed together. Pi is the only agent. Local
execution uses managed Pi; container execution selects an externally prepared
image. Image definition/source export is separate from changing the active image.
See [executor images](Project_Executor_Images.md), [local execution](Local_Execution.md)
and [configuration](Configuration_Reference.md).

## Import, export and portable settings

Raw configuration import enrolls a project from server-ready TOML. Raw preview
shows the exact saved TOML; complete export includes configuration and retained
image-definition sources. Separate credential stores and pending changes are not
exported. Inline secrets already present in raw TOML remain part of that exact file;
protect and review it before sharing.

Portable working rules are a separate closed JSON format with their own scope,
source validation and transfer endpoints. See [Portable project settings](Portable_Project_Settings.md).

## Statistics and administration

Statistics uses the selected authorized project scope, period, timezone and
aggregation. Its current tabs are Summary, Usage, Quality and Trends. Missing
measurements remain unavailable rather than zero; cost estimates are distinct
from reported amounts. Cost/price administration is role-protected.

Automatic reads refresh existing content in the background. Statistics keeps the
selected tab, sorting, table page/page size and open CSV menu while both metrics
and usage are revalidated; replacements appear together for the same authorized
reporting scope. Selected metrics is read every 15 seconds, usage and all-project
metrics every 30 seconds. Faster metrics reads wait for the usage counterpart
before the displayed reporting snapshot is replaced. Project Statistics does not
wait for unrelated all-project reads. Jobs and project job History keep rows,
paging, open details and consumption during same-context refreshes. Refresh is
available on these informational views and on both change-history views; Users
keeps its manual header Refresh. Repeated clicks join a pending read.

Refresh/Retry shows the last successful update time. An informational transport
failure may leave the last validated snapshot visible with an explicit warning
that it may be out of date; Retry uses the same background path. A first read or
changed project, reporting period, filter or authorization scope has normal
loading feedback instead. Rejected access, missing identity, corrupt evidence and
server paging conflicts withhold affected data; job paging conflicts keep the
explicit first-page reload. Retained information is not current action authority.
Changes to existing Users accounts wait for the reread; changed authority
invalidates reviews. Settings drafts and valid confirmations are not replaced by
unrelated polls or operation completion. Hidden browser tabs pause periodic reads
and revalidate when visible. Ticket/comment and executor-output reads keep their
existing explicit lifecycle; this does not add forge polling.

Administration exposes worker/system state, accounts, project access and change
history. Queued operations retain their own final outcome and can be inspected
after navigation. A 202 response is an operation reference, not proof of success.
Clients read the returned operation ID to obtain the confirmed status/body.

## Running and maintaining the web service

The API and supervisor use one service account and the same absolute ADORE home.
Run one supervisor per home, without another CLI loop over those profiles. The
portable application's Start/Stop manages the process tree. Service-host setup is
in [deployment tools](../02_Tools/setup/README.md).

Use HTTPS for access beyond a trusted local endpoint. Protect the home, logs,
backups, TLS material and credentials with the service account's permissions.
Do not expose session recordings or raw exports as public files.

The committed frontend bundle supports source launch without rebuilding. Changes
to frontend inputs require `npm run build` in `04_Software/web`; packaging verifies
the bundle fingerprint. See [Getting started](Getting_Started.md) for source startup.

## Workflow choice at Start and Restart

Every manual Start in global Tickets or Projects > Tickets opens a compact **Workflow** selector: **With AEGIS** or **Without AEGIS**. It is prefilled from the project’s **Default workflow** and observed payload presence. Missing AEGIS disables that choice; installed payload usability is checked on admission. Direct remains selectable. Job actions offers separate Abandon and restart with AEGIS / Abandon and restart without AEGIS buttons. Each uses a short browser confirmation naming the chosen workflow and discarding existing work; no additional page panel or selector opens. Missing AEGIS disables the AEGIS action. Retry retains the recorded workflow. Settings > Implementation exposes the auto/direct project default.

The authenticated `/api/v1/projects/{id}/workflow-selection` read returns `default` (`aegis` or `direct`) and `aegis_available` (presence only). Ticket Start and operation Start/Restart accept optional `workflow: "aegis" | "direct"`; other actions refuse an override. The queue stores it in a structured column, includes it in idempotency binding and passes it to the worker CLI. The web database identifier stays fixed at schema 1 throughout pre-release; the current table structure is changed in place and validated when opened. Before using this build, stop ADORE and manually delete `ADORE_HOME/web.db` and `ADORE_HOME/web.db.initialized` to start fresh; this also resets web accounts, memberships and operation history. Profiles and run state are separate. No automatic reset or conversion is performed.

## Cancelled jobs and storage

Restart refusal and an unconfirmed restart are shown separately. If confirmation
fails, refresh Jobs or Tickets and check for the new execution before trying again;
the new job may already exist even though the operation could not be confirmed.

For the latest cancelled job, Jobs offers Restart job with/without AEGIS. Tickets offers Restart job with the compact workflow selector. Confirmation starts from current settings while preserving cancelled history. Durable admission opens the new job; Previous job and New job navigate related executions. Earlier executions that already have a successor cannot create another restart. Failed-job Retry and destructive abandonment remain separate.

System status places the Storage label, availability badge and free/total capacity together below Workers. Job history has no automatic retention policy; audit limits apply only to administrative events. Individual job deletion is an explicit CLI operation.
