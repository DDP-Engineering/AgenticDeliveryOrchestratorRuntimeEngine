<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web frontend

ADORE guides agents and observes their recorded workflow. AEGIS completion is
read from the task journal; Direct completion comes from the implementation
session and its summary. Tests and their local/CI selection belong to the agent.
ADORE does not invoke `check --strict --run` or run a separately configured test
command. Candidate fingerprints, target freshness and fresh human approval remain
required before publication. Old `workflow.verify_command` values are ignored
without rewriting profiles and cannot be edited through the API.

Guided enrollment and raw-file import call the reviewed shared-environment
preparation route automatically on confirmation. `EnvironmentProgress` shows the
current stage and an indeterminate progress indicator in four locales; the user
can retry preparation failures with the reviewed answers/file retained. Saving
waits for a strictly validated ready response with the same operation ID. Navigation
guards remain active throughout preparation and publication. Closed views stop
polling and never proceed to publication; shared server preparation can finish
and be reused. Long builds refresh previously measured readiness before saving.
`environment.test.mjs` covers transport/state boundaries; browser journeys cover
visible progress, publication order and failed-build retry.

Both own-password change forms mask all three fields by default, offer independent eye-icon reveal controls with accessible labels, display the eight-character minimum and require matching confirmation before sending only current and replacement values.

The authenticated factory administrator sees a persistent localized password reminder linking to My account. While applicable, one strict 30s owned session read uses the existing 15s visible cadence and coalesces visible-return/timer triggers. Hidden tabs start no reads. Validated password-required, account, role, CSRF or grant changes end the old application context; failed or malformed session reads do not preserve its authority. The existing password form revokes sessions on success.

## Authenticated request boundary

`request.ts` owns App's JSON transport and `createRequestScope`. Injected child
JSON requests, including Settings prices, ProjectAccess and SettingsList explicit
actions, use one application-lifetime AbortController combined with any resource
signal. RawConfiguration retains its separate explicit raw-TOML text fetch and
preview/download lifecycle. Fetch
transport failures remain positively typed; invalid JSON/media and HTTP application
errors never acquire informational stale eligibility. Successful transport is not
resource validation. Disposal aborts browser work, refuses new requests and rejects
late successes/errors even if a transport ignores abort. It never implies server
mutation rollback. Sign-out's separate DELETE uses raw JSON transport after disposal.

App retains one `AppView` instance for ordinary updates. A detected authenticated
HTTP 401/403 disposes its request scope and replaces that instance, removing all old
private snapshots, reviews, callbacks and action authority. Authentication/CSRF loss
returns to sign-in. Other denials permit a validated `/me` correction only if the
principal actually changed or a password change is required; unchanged identity
stops at explicit sign-in, preventing an automatic denial loop. Missing-resource
404 stays resource-local and is not guessed to mean whole-account loss.

Sign-out invalidates locally before waiting for DELETE, so held reads and scheduling
cannot retain private views. A localized signing-out screen withholds a new login
until DELETE settles (30s browser bound), avoiding a late old-session cookie response
racing a new sign-in. Successful own-password change similarly replaces the context.
The boundary supports development StrictMode effect replay without reviving obsolete
requests. `tests/request.test.mjs` and `e2e/sessionRefresh.spec.ts` prove transport,
late denial/success, five-view immediate sign-out, HTTP/session correction, price
ownership, account replacement, bounded session reads and hidden/coalesced polling.

Job and ticket cancellation require confirmation and explain attempted cleanup and retained evidence. Monitoring refreshes after the actual operation result. System status separates worker activity from heartbeat, and explains serialized commands and cancel signals. Empty project views offer enrollment and raw import to administrators. Deleting the last project returns to Projects, which omits the empty table panel. The delete dialog keeps the clone choice and exact-name instruction without the introductory paragraphs.

## Access, Settings and App result ownership

ProjectAccess has a strict 30-second `createReadController` keyed by immutable
project identity under the principal-bound parent key, with 15-second visible
polling. Refresh signals invoke the existing owner, not a refresh-counter key.
Pending reads retain rows/review/focus. Reviews bind developer ID/name/grant/disabled
and live project ID/name/archive; changed or failed evidence latches submission
invalid until correction. An unchanged valid review stays mounted. Current project
metadata must be ready and nonarchived at render and submit. A grant write cancels
pre-write work, serializes against periodic reads and keeps controls disabled until
strict post-write validation settles. Failure hides grants rather than retaining
optimistic permission evidence. Context exit aborts the read and scheduler; late
write results cannot publish into another owner.

App's configuration owner no longer depends on `viewRefresh`. Operation-result
signals cancel older configuration/price work, then reread only through existing
visible/clean/blocker/mutation guards. Dirty drafts and valid confirmations remain.
Own confirmed Save or explicit stale discard instead awaits post-write validation
before the editor's barrier is released, retaining open groups. Unrelated result
signals check the mutation guard before cancellation/token invalidation, so a held
own-Save validation cannot be cancelled or mistaken for a completed Save. Existing config
revision, pending-candidate and price-write guards and 30s/15s request bounds remain;
this is not a change to settings mutation authority or sign-in lifecycle.

App monitoring/archive/restore/delete submissions serialize against other current
project actions and recheck ready live identity/name/archive/pickup state. A
principal/project/view or relevant metadata change cancels the browser submission
and revokes all result/error/notice callbacks before replacement rendering; this
never rolls back a server-accepted command. Operation notices/tracking render only
in their origin's current project context. Archive/restore responses validate the
expected immutable ID, name and archive boolean before announcing success. Delete
confirmation preserves unchanged drafts/focus, but changed or failed project
authority latches submission invalid until dismiss/reopen. Removed selected
projects use the existing unavailable-directory route, never silent substitution.
`e2e/operationRefresh.spec.ts` proves these boundaries; lifecycle/notification
fixtures in jobs/dashboard tests now return the actual archive identity contract.

App pending operations use a strict 30-second owner keyed by principal/project/ID,
not pending versus running, with 2-second visible cadence. Leaving the project
context cancels tracking; returning resumes observation of an unresolved operation.
Read failure/deadline reports an error, never successful completion. An observed
terminal result cancels pre-result directory reads before revalidation and sends
non-remounting reread signals to displayed owners. Jobs/audit invalidate their
pre-result attempts before paint while keeping mounted presentation. Jobs advances
its evidence generation (but never releases an owned pending-command barrier),
requiring new list and detail before dependent commands. Reporting's `revalidate()`
cancels the old proposal without removing its committed report, then requests both
members in a fresh generation, never pinning pre-result inputs. Late old values or
errors cannot publish. `tests/statistics.test.mjs` and the operation refresh browser
suite prove full-member cancellation, retained History/Jobs/report nodes and CSV
disclosure, including independent completion. Integrated held-detail cases require
both post-result list and detail generations before reenabling commands, and prove
that an external result cannot release a concurrently pending job command's read
barrier. Removed Overview/Summary/Jobs identities lose their selector/actions;
archived Jobs retain readable detail with disabled operational controls.
Administration worker/storage
owners keep 5s/30s cadence, 30s bounds and strict error/unavailable/unknown semantics;
successful pending reads retain values, while failed/invalid reads do not retain a
healthy status. Readiness validates ready/worker/activity, storage validates its
numeric, boolean and volume fields before display. `e2e/accessRefresh.spec.ts`
proves these seams, including changed/archived review authority, post-write failure,
deadline/late completion, cancellation, hidden pause, pending-to-running continuity
and clean/dirty Settings after App results, including an unrelated result racing
held own-Save validation. `e2e/settingsRefresh.spec.ts` also holds unrelated App
results through an impact confirmation, credential and price drafts, owned price
post-write validation and a pending ChatGPT sign-in. The sign-in keeps its pasted
address and serialized 1s status read, expires after 900 seconds (also while hidden)
and stops polling after expiry. No forge/model/credential operation is executed by
these route fixtures. Authenticated denial/session uses the shared boundary above.

## Ticket live scope and response ownership

`TicketWorkspace` receives App's principal/role/grant key and current authorized
projects. A per-project authority epoch binds principal/CSRF, immutable ID, profile
name and archive state. Equivalent metadata leaves owners, bodies, reviews, paging
and focus intact; unrelated project changes do not restart an operation. Rendering
uses current project metadata rather than the project object captured by a forge
read. Removed/renamed identities are synchronously withheld and permanently pruned;
a restored identity cannot resurrect its old body. Archive alone can retain readable
bodies, but invalidates command/review authority until an explicit successful read.
Start/Retry/Stop recheck current row, project and authority at submission. An unchanged
review remains valid; changed authority latches it invalid with localized correction
feedback, even after restore. Pickup state has a separate monotonic Start epoch:
a detected pause/resume invalidates the prior Start snapshot/review, including if
the old state returns. Both render and submit require the current Start epoch and
matching live pickup state. Captured in-flight ticket reads cannot acquire a newer
epoch on completion. Stop authority/reviews, readable bodies and operation tracking
remain independent of pickup changes. Read tickets obtains a fresh action snapshot;
a fresh eligible manual Start still works while monitoring stays paused. It never
runs automatically in response to metadata, operation or visibility updates.

Explicit ticket/comment reads use strict 30s read owners with cancellation on context
exit and finite slot release. A synchronous batch guard coalesces duplicate reads;
opening a still-loading comment again joins it. A new explicit list read supersedes
older comments. Writes are not retried or given a client deadline; context exit aborts
the browser request and ignores its result without claiming the server rolled back.
Only a live result may publish notices/queued state or notify metadata. Operation
tracking binds the originating project authority, not the full project array. Errors
and success feedback cannot appear under another principal/project. Shared detected
HTTP-denial/session invalidation uses App's shared request boundary above.
`e2e/ticketRefresh.spec.ts` proves unchanged/changed reviews, removed identities,
late read/write refusal, explicit deadline/recovery, request counts, no forge polling
and keyboard-accessible four-locale/two-theme narrow feedback; existing ticket tests
cover paging, Markdown/source, preferences and real Start/Stop controls.

## Owned informational read primitive

`polling.ts::createReadController<T>` provides a framework-independent, memory-only
read owner. It captures one immutable context `key`, a finite `deadlineMs`, a
`read(signal)` that validates its entire result, and a `publish` callback. The
callback receives `{key, status, data, refreshing, error, completedAt}`. Status is
initial `loading`, validated `ready`, explicitly retained `stale`, or closed
`error`; `refreshing` is independent of an already displayed snapshot. Successful
completion, including unchanged or empty data, records the injected clock's epoch
milliseconds. Starting, failing, cancelling or ignoring a read never renews that
time. Closed failure clears both evidence and its success time.

`refresh()` joins one active promise with no queued backlog or deadline extension.
A deadline settles callers and aborts the signal even if the transport ignores
cancellation. Failed aggregate validation also aborts remaining sibling work.
`invalidate()` ends publication authority and clears evidence for an invalidated
context. `cancel()` also settles/aborts old work but retains displayed evidence and
its original success time; an intervening write must independently revoke action
authority before cancellation and explicitly reread afterward. `dispose()` aborts and
settles work without publication and prevents later reads. Late success/failure
cannot change a replacement owner's data, error or time. Owners must separately
stop their scheduler on cleanup and gate rendering by the captured context key
before effects run; the primitive does not authorize, cache across contexts, retry
writes or validate wire data on the caller's behalf. Existing view readers retain
their own policies unless explicitly wired to this controller.

The default policy is strict: every failed completed read removes evidence.
`policy: "informational"` permits stale retention only for the client-owned
`ReadTransportError` and `ReadDeadlineError` from `errors.ts`, after a validated
success. A stale retry remains stale until complete validated success. Ordinary
`ApiError("network_error")`, HTTP failures, parser/validator exceptions and unknown
errors are not transport exemptions. Both internal failure types use existing
four-locale network guidance. Authority-dependent actions must independently
require current evidence; opting into informational display is not action authority.

`startVisiblePolling` preserves its supplied interval, stops while hidden and
revalidates once on a hidden-to-visible transition. Repeated visible events do
nothing; already queued periodic callbacks check visibility and stopped ownership.
Its callback receives `interval` or `visible`, allowing due-member masks versus
full visible-return revalidation. The scheduler does not itself serialize asynchronous readers. The browser-test
helper `e2e/polling.ts::revalidateVisiblePage` exercises hidden/visible transitions
and restores the document's original property; it does not substitute duplicate
visible events for elapsed polling. `tests/polling.test.mjs` uses deferred reads and
an injected deadline clock for overlap, success time, transport recovery,
fail-closed failures, ignored aborts, invalidation and disposal; `errors.test.mjs`
checks positive error classification and localized guidance.

## Settings confirmation authority

Each Save captures the current principal/project view and semantic project
ID/name/archive/pickup binding in addition to existing config-request/revision
guards. Changed or failed metadata, navigation or loss of editable authority
latches that Save invalid, including while preview or pending writes are awaited.
Confirmation keeps its reviewed project label and draft visible with localized
correction feedback and disabled submission; reverting metadata cannot revive it.
Keep editing and a fresh Save obtain a new review. The continuation checks the
binding again before preparing or applying a candidate. Identical metadata and
unrelated results preserve the valid confirmation, focused node and draft.
`e2e/settingsRefresh.spec.ts` covers rename/archive/pickup and restoration, held
preview/pending boundaries, zero subsequent writes and unchanged-review controls.

## Coordinated Statistics refresh

`statistics.ts::createReportingRefresh` coordinates one context's immutable-ID
metrics/usage maps through `createReadController` with one 30-second proposal
bound. Transports return exactly the captured project ID set; complete existing
metrics/usage validators enforce the copied selection and role before staging.
Matching canonical scope fields (excluding each member's separately validated
project identity) are checked across every project and both resource maps before
publication. Metrics and usage pooled results are computed inside that same owned
validation boundary and stored on the report; rendering never repeats aggregate
work. Validation checks safe-integer token directions and known input-plus-output
totals for raw and pooled period/total/day evidence, usage/cache buckets and job
amounts before publication. A missing direction keeps the combined total unknown;
known overflow is invalid, not an unknown or approximate number. Cross-project
interval disagreement or aggregate failure withholds the report,
exports and success time with explicit error/Retry, rather than throwing in render. App uses this owner for both global and
project Statistics. Its render key captures the session principal/role, authorized
immutable ID/name mapping, selected/all-project mode and reporting query; tab,
export disclosure, sort and pagination do not recreate the reader. Global responses
are checked against captured names and mapped to immutable IDs before validation.
Selected reports read only their selected metrics/usage endpoints, including for
administrators; irrelevant all-project reads cannot block readiness.

`refresh()` requests both inputs. `refresh({metrics: true})` or the usage mask
can pin a not-due member only from the committed baseline, retaining its original
`metricsAt`/`usageAt`; `fullReportAt` advances only when both were requested and
validated. A full/due trigger during a pending proposal promotes a pin without
duplicate reads, a queued generation or extending the fixed deadline. Empty masks
after a healthy commit do not publish or fabricate a completion time. Failures
discard staged values, abort siblings and require the failed proposal's requested
inputs on recovery. Strict failures clear the baseline; positively typed transport/
deadline failures retain only the prior complete report as stale. Invalidation and
disposal cancel both members, and late success/error cannot publish. No backend
atomic instant, new API/storage format or authorization is implied.

App's single visible schedule keeps selected metrics at 15 seconds, adding usage
when due at 30 seconds; all-project metrics and usage run at 30 seconds. Initial,
manual Refresh/retry and visible return request both. Metadata with an unchanged
identity/scope and equivalent session-notice reads do not restart the owner.
Context exit disposes/aborts both members. Only committed data drives cards,
tables and exports. Context changes synchronously hide the preceding report;
initial and closed failures retain the existing DataFeedback boundary.

Usage rows use the same JSON-encoded date/executor/model tuple as analytical
aggregation, without their current display index. `readConsumption` rejects
duplicate source buckets before publication (null and empty names remain distinct).
`e2e/statistics.spec.ts` proves a surviving row retains its DOM identity when a
changed amount moves it within the selected sort, and duplicate evidence hides the
report and export; `tests/statistics.test.mjs` covers accepted and duplicate tuples.

`Presentation.tsx::RefreshFeedback` keeps Refresh focusable with `aria-disabled`
and a guarded handler while pending; progress and full/member success times are
non-live. Stale/closed failure status is announced separately. Statistics records
Last refreshed from `fullReportAt` and labels Metrics updated/Usage updated with
their own times, so a pinned usage input never appears newly read. Transport/deadline
failures retain only explicitly marked informational evidence; a retained report's
CSV links read current server data, not a guaranteed export of that screen.
App's request transport positively types fetch failures, preserves owned aborts,
and refuses invalid JSON/media evidence; arbitrary HTTP codes are not transport.
The four-locale feedback wraps using shared theme tokens.

`tests/statistics.test.mjs` uses validated fixtures and deferred member reads for
both completion orders, pins/source times, promotion, partial failure/recovery,
malformed/foreign/missing maps, independently valid but canonically different
intervals, empty masks, deadline and invalidated/disposed completions.
`e2e/reportingRefresh.spec.ts` exercises both global and selected-project members
through initial and post-success 30s deadlines, late refusal and retry; selected
15s metrics-only updates preserve usage/full-report times, 30s reads advance the
proper times, hidden intervals start nothing and visible return coalesces. HTTP
application failures (even a server-supplied network-error code), wrong media,
foreign identity and mismatched scope withhold both report members and exports.
Deadline fixtures drain actual supporting session/directory IO before virtual
jumps, without stubbing authorization or relaxing the resource deadline.

## Direct Jobs presentation

`jobModel.ts` requires saved `workflow: aegis | direct` on list and detail reads.
Missing, nontext or unknown values reject the response, never choose a default.
`JobWorkspace` identifies Workflow inside the existing Status cell and current-state
card without adding a table column. `workflowStageLabel` keeps all AEGIS labels and
observed-only timeline behavior; Direct uses Implementation/build, Validation/validate
and Done, without an AEGIS task or quick-path explanation. The failed publication
reset pointer and historical publication reset event retain the Publishing label.
They are administrative recovery evidence, never an executor launch stage. Lifecycle/action,
consumption, budgets and operational executor-output controls retain their meanings.

A direct detail requires a closed `direct` attempt/latest-independent-verification
object (see Component_Web_Jobs.md). AEGIS details refuse this object. Positive safe
attempts or explicit absence, closed status/result shapes, canonical decimal-text
exit codes, outcome agreement, finite nonnegative seconds and normalized bounded
Unicode tails are validated before any display. Direct current/non-null timeline
stages outside build/validate/done fail closed, except for that failed pointer and
`reset` event. Nonempty saved commands retain exact spaces and tabs, matching the
configuration and conductor domain. Empty configured-result commands remain invalid.
List error/incomplete/source-change and detail failures hide stale detail evidence;
request/composite/session guards remain unchanged.

The localized `directCopy` and i18n stage keys cover English, French, German and
Romanian. The independent-verification panel shows the saved attempt, command before
result, elapsed seconds and a focusable literal `pre` tail, or explicit empty output.
Passed, Failed, Timed out, Not configured: unverified and unavailable evidence are
distinct. There is no command action or HTML/Markdown evaluation. Settings changes
cannot substitute today's command for saved evidence. Direct working/timeline copy
makes no AEGIS or synthetic progress claim. Help and inline timeout guidance map
build to direct agent implementation with the general timeout fallback; validate only records the candidate.

`tests/jobs.test.mjs` exercises workflow/evidence/stage trust boundaries and valid
controls; `e2e/jobs.spec.ts` uses opt-in persisted direct fixtures while retaining the
default AEGIS cohort and assertions. Browser proof covers mixed global/project lists,
all outcomes/absence, switching, post-success corruption, four locales, desktop/mobile,
both themes and keyboard output access. Help model/browser tests cover terms, mapping,
structure and navigation. The committed production bundle includes these inputs.

## Host-check response ordering

App owns project metadata through a strict `createReadController`, keyed by
principal/session, role, assigned IDs and whether Overview isolation is eligible.
Equivalent Session objects and initial `projectsLoaded` publication do not recreate
it. Initial, 15-second periodic, visible-return and explicit reads join one bounded
30-second attempt. Existing content remains while a same-principal read is pending;
completed failures withhold the directory/context and dependent views. A synchronous
principal gate hides old items before effect cleanup. The read validates the full
directory and uses the existing Overview-only corrupt-run fallback with the same
abort signal. Cleanup stops the scheduler and disposes the owner.

After a validated explicit host-check result passes current view/request guards,
`App::checkProjectReadiness` invalidates the metadata owner before updating the
verification fact. Every project-list read already in flight is cancelled and
superseded: an older snapshot cannot replace the newly saved result. Later polls
still update verification, including staleness after configuration changes. No
backend probe policy changes. `e2e/jobs.spec.ts` proves initial/session/visibility
coalescing, obsolete-request cancellation, old-result exclusion, fresh-poll
publication and corrupt-refresh withholding/recovery; the real offline API journey
retains its failed-verification assertion.

## Forge Markdown rendering primitive

`src/forgeMarkdown.ts` exports `ForgeMarkdown`, a synchronous React-only renderer
separate from the help parser. Its inputs are the untouched forge `source` string
and localized `imageLabel`, `codeLabel` and `tableLabel` strings. The renderer
returns semantic GFM elements through pinned `react-markdown` 10.1.0 and
`remark-gfm` 4.0.1. It does not own acquisition, account preferences or the mode
control. The detail header places Body display and its selector inline at the
right edge, wrapping when space is limited. `TicketWorkspace` mounts it for
descriptions and comments in Rendered mode; Markdown source uses a focusable
`pre` containing the untouched API string.
An empty description uses the existing localized fallback before rendering.
Ticket actions reserve 26rem on desktop, keeping Start/Retry, Stop and
Details/Hide details together on one line across the four interface languages.
The Actions header and button group align to the right; the last button keeps
the same right edge when details open or close.
At 1100px and below, whole buttons may wrap; at 720px and below the column uses
8rem and labels wrap at spaces. Expansion does not change desktop button-row layout.

`App` owns the shared mode for both project and global Tickets workspaces.
`ticketPreferences.ts::readPreferences` validates nullable language/theme and the
closed `ticket_body_mode` response (`rendered`, `source`, or null). Malformed
responses raise `ApiError("unexpected_response")`; only null means no saved mode
and selects Rendered. Account initialization/sign-in reads preferences before
the shell appears. Session generations guard reads and writes, and session clear
resets mode/confirmed mode/pending guard. One synchronous ref admits a single
mode PATCH per session; all detail selectors remain mounted and focusable with
`aria-disabled` while saving. Success confirms only the mode, not stale language
or theme. Failure restores the last confirmed mode and uses localized error
feedback; another explicit selection retries. Account storage supplies reload,
project and browser persistence, read at sign-in/reload rather than live tab sync.
`ticketCopy` owns four-locale controls and renderer labels. Scoped theme-token
CSS wraps prose/metadata and contains source, code and wide tables in local
scroll regions without expanding the outer page.

Raw HTML is retained as escaped React text; no raw-HTML plugin or HTML insertion
API is used. Custom anchors accept only explicit absolute HTTP, HTTPS or mailto
URLs validated with `URL`; controls, whitespace, relative URLs and other schemes
remain readable non-link labels. Allowed anchors have controlled attributes,
`target="_blank"` and `rel="noopener noreferrer"`. Parser props are not spread
onto links. Images always become localized inert placeholders, never resource
elements or automatic requests. Task checkboxes are disabled. Code and tables
expose named, focusable `forge-scroll` regions for local overflow styling.

`tests/forgeMarkdown.test.mjs` exercises the public React render using static
markup: the requested nested GFM subset, malformed syntax, literal HTML,
inline/reference links, scheme obfuscations, image placeholders and escaped
labels. `tests/ticketPreferences.test.mjs` proves the closed response boundary.
`e2e/tickets.spec.ts` covers shared exact source, delayed comments, keyboard/focus,
HTML/link/image DOM and request safety, account/session persistence and save
failure/retry, four-locale labels/help, and both themes at desktop/360px. Dependency
licenses are MIT except the ISC structured-clone dependency. Vite's built-in
`build.license` emits `BUNDLED_LICENSES.json` with full license metadata for the
bundled graph in each build; the static notice inventory names that companion
file. Asset stamping keeps the existing project license/notice copy behavior.

Technical details displays Durable job state folder (`state.store_root`), Workflow Python command (`workflow.aegis_python`), Existing local repository path (`worktree.repo_path`) and Job working folders (`worktree.root`) as informational installation values. Operators configure them in the project TOML on the ADORE server; generic web mutations are refused. The localized guidance explains that changing a path does not relocate existing job state, repositories or working folders.

Project Settings follows **Repository → Tickets → Implementation → PR/MR and review → Statistics → Agent and model**, followed by closed **Technical details**. Repository owns platform/author identity and the single integration-branch editor; PR/MR shows its value and a link that opens/focuses that row. Tickets owns eligibility, polling, priority/type and pickup/status labels; hold/exclude affect pickup, not already-started jobs. Implementation owns capacity, budgets and progress commits, with closed Clarifications, Recovery after errors and Advanced stage time limits. Statistics owns recording/token switches and the informational database file inside closed Advanced statistics paths. Technical details and worktree paths are read-only; Repository branch naming uses reviewed edits and a server-checked example; runtime installation stays external and Agent and model groups executor settings in Settings. Inactive reserved controls are omitted without changing CLI configuration. All categories start closed, retain reviewed Admin edits and Dev redaction, and have four-locale names.

`settingPurpose` routes exact effect overrides before section fallbacks; `settingVisible` suppresses inactive/external fields and admits only four known informational worktree fields; `settingSubgroup` owns native topic disclosures. Technical/unknown and worktree rows cannot acquire editors from catalog metadata. The target reference opens its containing disclosure and focuses the single row.

Implementation uses shared four-locale names for reviewed settings, including **Active job limit**, **Maximum executor launches per job** and **Active work time limit (seconds)** names in rows, editors and candidate review. Help describes serial capacity with parked jobs excluded, lifetime launch counts, cumulative active time excluding waits and between-attempt time/cost checks. Reported USD accounting depends on captured token usage; cost-only reports do not count. File guidance describes distinct committed/pending/new product and AEGIS paths, the unfinished-merge exception and continuation when Git counting is unavailable. Per-attempt timeout help preserves configured recovery and strict-check semantics; progress publication is enabled by default with local commits retained when disabled, and the quick label is an optional framing hint. Configuration keys, runtime enforcement and role/redaction contracts retain their current behavior.

`review.max_review_rounds` and other review policies map to PR/MR and review; pickup gates map to Tickets. Localized help explains the shared additional-round budget and distinct exhaustion outcomes. Portable mapping validation derives its exact size from `portableFields`, whose readiness map contains two booleans.

`lifecycleCopy` names pickup/status/answer labels consistently in rows, editors and candidate review. `STATUS_LABEL_KEYS` partitions six rows (including answered) into a native initially closed Status labels disclosure inside Tickets. `HIDDEN_SETTING_KEYS` omits CLI-only startup mode (`polling.mode`) and inactive reserved controls; effective config/catalog and scalar transport still carry those keys. Status edits retain existing administrator/revision/idle authority; Dev remains read-only. The disclosure uses the existing responsive row layout.

`labels.control.exclude` uses `excludeLabelCopy` for the settings row, editor and candidate review in all four locales. Help describes its configured name, presence-based pickup exclusion, removal under remaining eligibility gates and already-started job boundary. The scalar editing and conductor contracts remain unchanged.

`delivery.target_branch` uses `targetBranchCopy` for the row, editor and candidate review in four locales. Help describes the remote starting branch, PR/MR destination, short branch-name format and human merge boundary. The scalar key, active/default values and reviewed editing contract retain their existing authority.

Settings names `delivery.draft` as PR/MR state at publication and displays localized Draft/Ready for review labels for active/default values, options and candidate review. Boolean wire values use the existing reviewed apply flow. The in-review lifecycle represents human review for either forge state.

Project details groups its three metadata rows with a 4px gap and separates
the action row by 18px; long values wrap within the panel.

Secondary text uses contrasting light/dark theme colours. Project metadata,
configuration values, type/domain hints and field help use 0.875rem text with
1.5 line height; long identifiers and guidance wrap within their panels.
On narrow screens, setting labels, values and help stack vertically.


The header link **How ADORE works**, beside About (and Refresh where shown), opens the
help center route `/help[/<topic>]` (`HelpCenter.tsx`). Topics are bundled
Markdown files `src/help/content/<locale>/<topic>.md` loaded with
`import.meta.glob` (`src/help/content.ts`) and parsed by `src/help/markdown.ts`
into blocks rendered as React elements (headings with explicit ids, paragraphs,
lists, tables, notes, code, bold, code spans and internal links; no HTML).
The page lists topics with an accent- and case-insensitive search, shows the
article with an On this page outline of `##` sections, routes internal links in
the app and scrolls to `#id` sections. `HelpLink` renders the contextual **?**
link (Tickets toolbar, Enroll new project step heading, project Settings heading) that
opens its topic in a new tab. `tests/help.test.mjs` checks the Markdown subset,
locale parity of structure and links, link and route targets, contextual
targets and the glossary terms. Full job history is reached through the sidebar Jobs link; Overview
keeps job-specific Details links.

Implementation settings support reviewed edits for human-answer waiting time (positive integer plus seconds/minutes/hours/days), positive question-round count, a nonempty retry schedule (one nonnegative integer per line), and the complete stage-timeout map. The five stage rows (frame, specify, design, build, validate) choose either the general attempt limit or a positive custom limit in seconds; choosing general removes the override. Retry and timeout collections accept only safe integers and their declared keys; other lists/maps remain read-only except the existing reviewer list. Admins prepare, inspect active/proposed values and apply only at the existing idle boundary; developers remain read-only. Names, help and controls share four locales. The answer deadline is independent of the reserved reminder; reminder format is still checked and no reminder is sent.

`implementationSettings.ts` owns closed duration/collection draft validation and localized editor terminology. `settings.ts` retains typed map values when reopening the editor and validates exact canonical candidate collections. `SettingsList` renders duration amount/unit, six-line retry schedule and all five stage choices within the responsive setting row. Invalid complete drafts cannot prepare. Typed groups occupy the whole editor width above their action row, and nested controls explicitly reset the generic horizontal flex basis to retain normal control height. Focused proof: `web/tests/settings.test.mjs` and the typed Implementation, locale and Dev/browser scenarios in `web/e2e/settings.spec.ts`.

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
`state.channel` is removed: it is not in the setting catalog, and config
validation refuses it as an unknown key.

**Project → Settings → Agent and model** configures Pi, ADORE's only coding agent; there is no agent choice. It shows Test AI connection, the agent connection (Provider, Model, and for an OpenAI-compatible endpoint Endpoint base URL and Endpoint API type; one reviewed candidate, `executor.connection`), the launch command (`executor.command`; a container project may choose only the one Pi preset, a local project uses fixed managed Pi RPC), Internet access for the agent (`executor.internet`, On/Off, default Off), Web search (`executor.web.search`: Exa (no key), Brave (key needed), Tavily (key needed), None), additional credential variables (`executor.env_keys`), the provider API key, the execution environment (`execution.backend`, the container runtime and image, and the current account and optional project tools PATH for local projects, with external container guidance) and estimated prices. A new model ID must be supplied explicitly. Credential names are added through a dropdown and remain visible as individually removable selections. Connection, command, internet access, web search, backend, runtime and image edits go only through the reviewed flow (prepare candidate, review, apply). While internet access is On, or the editor or the candidate review proposes On, an alert says a malicious web page could try to make the agent send its API key or ChatGPT token out and recommends limited, short-lived keys; a local-backend project shows instead the note "Not enforced: this project runs Pi installed on the server, which reaches whatever the server reaches." While the image row is edited it offers the same server image suggestions. Installed agents and runtime preparation remain external. The old `/executor` URL redirects to Settings. Developers read non-secret settings/results without mutation actions.

The names-only selector for additional credential variables offers the known provider key variables and retained custom names; it defaults to empty (`env_keys = []`) because the provider's key variable is always passed. Applying names does not delete saved `.env` values. Provider API key offers private Save/Disconnect for the variables the server names (the configured provider's credential variable, then `BRAVE_API_KEY` or `TAVILY_API_KEY` while internet is On with Brave or Tavily search) and shows their sources only; key changes require paused pickup and idle/pending-free state. For a ChatGPT subscription the Authentication slot shows the ChatGPT sign-in panel (`ChatGptSignIn.tsx`) instead, followed by the key panel only when a search key is needed (`searchKeyNeeded`). Explicit Test AI connection remains the evidence of model access and may incur provider charges.

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

Jobs/History list (including the Overview attention/active aggregate), detail and
lifetime consumption each use a 30-second `createReadController` owner. The optional
read AbortSignal reaches the shared transport. List/detail retain the 15-second
cadence, consumption 30 seconds; context exit cancels requests and timers, and
same-context automatic/manual/visible/parent reread triggers join owned work.
Render keys include principal/session, role, authorized IDs, project/run and list
query/paging context before effect cleanup. Refresh counters are triggers, not
owner identity. Jobs/History/detail/consumption expose scoped, localized
RefreshFeedback with non-live progress and validated completion times. Pending
reads retain existing rows, amounts and detail. Positively typed transport/deadline
failures retain only marked old informational evidence; malformed, incomplete,
denied and other application failures hide affected evidence. Compact Overview
keeps its existing closed failure policy without adding a reporting toolbar.
A rejected continuation stops rereads until explicit Reload first page, which
clears the snapshot/offset; an ordinary retry never silently rebases that page.

Surviving composite rows, local filters/sort/page size/page, detail disclosures,
clarification/output selection and scrolling remain mounted. Timeline keys use
original saved position plus immutable event fields, not the reversed display
index. Executor output stays manual and preserves the existing composite and
state_revision remount boundary and closed diagnostic validator; unrelated title
updates do not fetch or reset output. Current ready list AND detail plus live
nonarchived project authority are required at render and submit for Retry/Cancel/
Restart. Informational consumption alone is not action authority. Offline
`e2e/jobRefresh.spec.ts` covers held and changed/unchanged reads in all three list
scopes, failure classification, stale-action separation, deadline recovery,
query/unmount cancellation, hidden/visible joins, output binding and narrow
four-locale/two-theme keyboard retry.

Job command submission increments an evidence generation, cancels pre-write
list/detail/consumption work without clearing presentation, and blocks their
periodic/manual readers until the queued result is observed. Terminal results
(including failure/uncertainty), or submission failure, trigger fresh reads on the
existing owners rather than incrementing a remount counter. List/detail snapshots
carry their validated generation; commands require both to match the current
generation, so a retained pre-write detail never becomes post-write authority.
Run/principal/scope changes cancel command ownership and synchronously hide old
operation evidence, then revalidate the current context. Existing continuation
conflicts still require explicit zero-page reload.

Job worker readiness and pending-operation readers also use strict 30-second
owners, preserving 5s/2s visible cadence. Pending-to-running status does not
recreate the polling owner; terminal status stops it. Readiness validates the
ready/worker/activity domain before publication. Failed/expired operation reads
keep completion explicitly unknown, while worker errors remain distinct from
unavailable heartbeat; visible return retries without duplicate requests. Exit
cancels owned reads/timers and late completions cannot publish. The Jobs refresh
suite covers these boundaries, post-result failure/authority, preserved pager,
detail/output/focus and same-project run navigation. Cross-view authenticated
denial, App/Tickets operation ownership and Access/config revalidation remain
separate responsibilities.

Loading and failed requests have separate status/error panels. Numeric
cards and data tables render after successful scoped responses. Statistics keeps
its complete report during same-context reads and marked transport/deadline
failure; closed failures withhold prior totals. Other readers keep their
resource-specific error policies. A successful
empty project card uses equal spacing for its title, guidance and any enrollment
action. Its guidance explains enrollment for administrators or access requests
for Dev users. Pending detail responses
are checked against both project identity and request revision. Session
generation guards prevent the previous account from refilling data.

The keyboard skip link focuses content. Primary links mark the current page;
navigation and disclosure controls have visible focus. Route changes move
focus to content. The Glossary topic of the localized help center defines job,
enrolled project, pickup stopped, waiting for clarification, waiting for approval
and draft review. Stopping pickup affects new issues; active jobs continue.
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
operation correlation and revision evidence in a full-width `audit-detail-row` under
the event (fixed table layout; 12-character ids with the full value as title;
revisions only when recorded). Missing values say Before
value not recorded; candidate preparation and uncertain application attempts are
labeled separately from applied results. `auditCopy.ts` supplies four locales.
Strict transport/value checks withhold malformed, mismatched, unauthorized and
other nontransport failed evidence and counts. `createReadController<Page>` owns
one query-bound read with the existing 10-second deadline. Pending rereads retain
the validated page; only positively typed transport/deadline failures retain it
as marked stale information. `RefreshFeedback` supplies localized non-live progress,
validated completion time and Refresh/retry in both scopes. Same-query triggers
coalesce; query changes synchronously gate out preceding evidence and cancel its
owner. Principal/role/project-scope keys, not refresh counters, own panel identity;
the project reader mounts only after stable identity resolves. Applied/draft
filters, paging, surviving event disclosures, focus and scroll persist during
revalidation. Successful removal prunes vanished event disclosures.
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
verified authorized active response. Both compact tables show title/project/ticket,
status and Details; App places one Project selector in DashboardShell's optional
header-controls slot, before selected context and job tables. The sidebar Jobs link retains
scope; the primary Overview URL/action resets it to all authorized projects.
Explicit scoped deep links remain supported. Overview's visible15s job polling
retains validated same-render-key rows until a successful replacement; failures,
incomplete evidence and scope/access changes still hide them. Its refresh timestamp
is omitted. The header Refresh and stamp render only on Users.

Users has its own strict `createReadController<AccountUser[]>`, keyed by current
session/role/grants and active Users view with a 30s deadline. It has no periodic
or visible-return scheduler; header Refresh joins the existing read, exposes
non-live localized progress and records validated completion in a semantic time
node. Metadata/operation refresh counters do not own or remount this reader.
Pending rereads preserve account row/disclosure/editor identity and dialogs;
completed failures hide account evidence/authority and its success stamp, not
unrelated credential drafts. Reset submission requires the current target's
identity, role and disabled state; creation checks current live project choices
again at final submit. AccountAccessEditor keys use immutable account ID, not
its grants array. Its review binds semantic account/grant and selected-project
name/archive preconditions; relevant changes latch submission invalid until a
new review, preserving the local selection for correction. Unchanged reads do
not refocus reviews. `sendUsers` serializes writes, calls the read owner's
`cancel()` before mutation and requires a strict post-write reread before
reenabling actions. Cancellation retains only presentation and original success
time; it never renews authority. Old responses cannot publish after that write.
`e2e/usersRefresh.spec.ts`, `e2e/users.spec.ts` and `tests/polling.test.mjs` cover
manual/held continuity, time/no-auto behavior, failure/removed-target guards,
changed reviews, pre-write cancellation, deadlines/retry and navigation.
Settings, Access, global Change history and project History use visible 15-second reads and
retain validated data while the response is pending. The Settings draft barrier
tracks configuration, pricing and authentication independently and invalidates
reads that overlap edits or writes. Price reads have a separate lifecycle and
validate the rate list before rendering. Access invalidates older reads
at the start of a grant change. The audit read stays bound to the applied
filters and page, and keeps evidence open for the same event IDs. The audit
panel's manual Refresh is available in both global Change history and project
History. `viewRefresh` is a reread signal, not part of the panel key or query-owner
effect. Audit requests have a 10-second deadline and cancel when the query or view
changes; deadline expiry releases the read slot even if the transport ignores abort.
`e2e/audit.spec.ts` covers held manual/periodic second-page reads, unchanged/changed
row identity, focus/scroll/draft retention, transport/deadline stale recovery,
malformed/denied refusals, query/unmount cancellation, hidden/visible scheduling
and four-locale/two-theme narrow keyboard retry.
Overview skips consumption reads and reporting/date/technical prose. Worker
faults appear above the job tables. When both Overview responses identify the
same unreadable projects, Needs attention names them and both tables show jobs
from verified projects. The affected Project Summary leaves its job counts
unavailable. Overview and Project Summary retry the project directory in
Overview mode if invalid job activity prevents the strict directory read.
Details retains the existing composite Jobs route
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
The Tickets table assigns a compact width to the number header at desktop and
narrow widths. The other flexible columns share the space. The style targets
the outer table header, so details can span all columns and nested tables size
independently.
Manual start goes through Tickets Start. Archived projects retain history and hide
start. Retry is available for failed current jobs; cancel excludes terminal and
pending/completed human handoffs. Effects stay visible beside each control.
An immediate submission lock prevents duplicate commands; existing operation
status polling distinguishes queued/running/completed/failed/uncertain results.
An unavailable operation read explicitly leaves completion unknown. The API and
worker recheck authority and lifecycle; the browser does not claim job success
from command acceptance.

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
with prerequisite-specific remediation. Undetected WSL
checks remain explicitly unverified. Review is the canonical response paired with
the unchanged draft. setup-create submits its frozen revision and uses an immediate
ref lock to prevent double clicks; failure requires a deliberate new review.
Completion displays stopped pickup and separate activation guidance, then offers
Open project. A current server-issued check token transfers the measured checks to the created project; absent or expired evidence requires a fresh host check.
About displays, on request, the project license text and the bundled third-party notices.
Projects show archived state and let administrators archive or restore a
quiescent project. Archived jobs and metrics stay visible, while job and pickup
controls are hidden until restore.
**Import raw configuration** opens a native dialog on Projects. Selecting a file
accepts UTF-8 TOML (512 KiB) or the current complete project ZIP (18 MiB) and
automatically calls its preview endpoint for the exact bytes and suggested
identity. ZIPs use base64 on the wire and require a separate bundle revision.
Their configuration and recipe are published together without extra source
controls or image building. Replacing the file or closing the dialog aborts validation
and invalidates its result. Import rereads the selected file and sends the exact
reviewed identity and revision to locked publication. The synchronous submission
guard blocks duplicates and prevents leaving during publication. Success closes
the dialog, restores focus and refreshes Projects. Former standalone import and
clone links resolve to Projects.
Long page titles wrap in the shared top bar, including at 390px.
The Projects directory lists authorized projects in a sortable, paged table
with project, repository path, Repo forge provider (Gitea/GitHub/GitLab),
Monitoring, job count and saved last activity. Project-name links open the hub.
The dedicated hub has one identity/navigation band: name, repository path,
Summary, Settings, Jobs, Statistics, History, Access, all tabs. Access is
Admin-only. The Jobs tab has Tickets and Jobs sub-tabs (`/projects/<id>/jobs`,
`?view=jobs`, `?run=`). Tickets (`TicketWorkspace.tsx`, copy in `ticketCopy.ts`)
reads open tickets only when Read tickets is pressed, validates the response,
pages more than 10 rows on the client (10/25/50/All, range, page X of Y,
Previous/Next; a new read resets to the first page),
shows eligibility, the blocking rule or job state with Start (confirming and
choosing a priority when it must add labels), Retry for a failed job, confirmed Stop
and Details (description plus comments loaded on first expand), and starts work only
from the table (disabled actions are visibly dimmed). Start and Stop confirmations
open as one row directly under their ticket, and the Start message names the
selected priority label; a `pickup_paused` blocker shows Monitoring paused plus a
per-project explanation, also used for a 409 `pickup_paused`. The followed
operation shows its `reason` as a localized sentence (`operationReason.ts`, shared
with `JobWorkspace` and the project status line), its `detail` lines in a bounded
`pre`, and for a refused Start the labels it left on the ticket. Forge metadata
remains inert React text with http(s)-only ticket-title navigation; description
and comment bodies use the isolated ForgeMarkdown policy documented above.

Ticket operation tracking uses a strict `createReadController<Operation>` with a
30-second bound and unchanged 2-second visible cadence. The key binds session CSRF,
authorized project ID/name set, originating project and operation ID, not its
pending/running status; status changes do not restart it. Tick/visible triggers join
one read with no backlog. The optional AbortSignal reaches App's transport; exit or
context replacement cancels it. Invalid identity, malformed evidence and expired/
failed reads leave completion explicitly unknown, never promote success. A validated
terminal result (including an immediately settled Start/Retry or synchronous Stop)
notifies App through `onOperationComplete(projectId)`. App cancels pre-result
metadata then revalidates it without invoking ticket/comment reads or remounting
bodies, controls or paging. `e2e/ticketRefresh.spec.ts` covers both scopes, pending/
running/result counts, hidden/visible joins, deadline/late completion, cancellation,
identity rejection and immediate-result paths. Live ticket review/action authority
and shared authenticated denial are separate boundaries, not proven by this seam.

The Jobs sub-tab renders `JobWorkspace` in jobs mode with a fixed scope, no start
form and the hub's `onOpen`, so job detail stays in the tab; Statistics renders the
shared `statisticsView(true)` without the project selector or the cross-project tab.
`statisticsView` lays the reporting period out as one `.metrics-period-row` (project
selector on the global page, From, Through, Group by, All time, Export CSV) with no
time zone control (UTC unless the URL supplies one), and `StatisticsEvidence` shows no
current-stock panel.
Summary holds Monitoring Active/Paused status, runtime and explicit
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
project configuration and estimated-price changes there, while
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
labels WSL runtime results as unverified when they cannot
be established from the API host, and never treats static config validity as
live readiness.
Administration polls `/api/v1/ready` every five seconds and shows whether the
control worker is ready, unavailable or could not be checked. Its explanation
keeps forge, executor and model readiness separate.
It polls the administrator-only storage check every 30 seconds and groups ADORE
home and project state roots by `volume_id`: one line for a shared disk, a table for
several. Worker and storage appear as one row of `readiness` indicators, and the
audit limits as `Chips` (Unlimited when absent). Less than 1 GiB is marked low;
a failed measurement is shown as an error.
The Jobs view starts at ten rows from complete authorized history. Search and
secondary filters run before slicing; counts/groups retain the searched scope
before secondary selection. Continuations pass the returned optimistic snapshot.
Scope/filter/session generations suppress superseded responses. Status and stage
labels and all action guidance are available in EN/FR/DE/RO.
The About dialog traps keyboard focus, cycling Tab through its buttons and
license regions, moves focus to What's new or Back when the view switches, and
returns focus to the opening button on close. A compact top-bar Sign out control remains available when the sidebar
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
Statistics reads reconcile retained usage journals; administrators can also call
`POST /api/v1/usage/rebuild` (no UI button).
Settings presents six purpose categories plus closed Technical details with frequent rows first in each,
source badges, visible localized purpose/units/consequence help, Active value and
ADORE default. Server catalog type/choices/numeric bounds continue to constrain editors; permanent descriptions provide guidance. Browser controls use server metadata; malformed catalog/candidate
transport fails closed. English labels clarify catalog keys; other locales retain
localized common labels and localized setting guidance for remaining headings.
`settingsCopy.ts` supplies four-locale category, effect and recovery copy.

`settingsSave.ts` normalizes a project-scoped raw draft into a bounded batch, with structural equality (object key order ignored; array order significant), typed controls and explicit important-effect classification. The connection wire carries the chosen or default reasoning effort with provider, model and endpoint. `SettingsList` retains multiple editors and raw invalid inputs. One Save bar owns Save/Discard, dirty and invalid state, recovered candidates and stale-revision feedback. Navigation and browser reload guard abandonment.

`SettingsImpactDialog` is a native modal for important saves only. It compares the server's no-write preview to the active snapshot and shows changed values and concise effects. Connection edits expand to the changed provider, model, reasoning effort and endpoint fields. Initial focus is Keep editing; Escape cancels and focus returns to Save. Cancellation creates no new persistent candidate. Ordinary saves proceed without a dialog. App prepares and applies the exact confirmed batch, comparing preview/prepared hashes and runtime plans. Scoped mutation identities prevent duplicate submissions and late cross-project completions. Failed saves retain editable inputs; corrupt pending reads disable editing with explicit discard recovery. The server's idle/lock/pause/revision checks remain decisive. Developers see read-only settings with financial/secret values omitted.

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

`EnrollmentWizard.tsx` runs guided setup with the setup preview, check and
create endpoints. Entering Verification automatically previews the current draft
and then checks server prerequisites. One Recheck environment action repeats both
checks; navigation or edits discard late responses. Normal inline helper paragraphs
are omitted in favor of the contextual help link, with separate spacing for optional
credentials. Portable transfer has its own API contract, exercised by
`tests/test_web_transfer.py`.


`RawConfiguration.tsx` owns four-locale Admin raw actions, bounded fetch, exact-byte download and native dialog with Escape/Close/focus restoration. Abort and pending-ref guards discard late results on unmount. Errors use localized safe codes; TOML is escaped text and never stored in browser storage. `e2e/portable.spec.ts` covers bytes, failures, role denial, late responses and four locales at 390px.

Administrators use **Preview raw configuration** or **Export raw configuration** beside Project settings. Preview opens a closable dialog. Export preserves the exact saved `config.toml` bytes, including comments, formatting and inline secrets. Pending changes, resolved defaults, separate `.env` files and external credentials are excluded. Preview is memory-only and cleared on dismissal or project/session change. Developers retain redacted read-only settings. Candidate review/apply/discard remains inside Settings.

The toolbar keeps two equally sized actions. Export directly opens the optional
browser save picker in click activation, then validates the complete container ZIP
or native TOML before writing exact bytes. Unsupported browsers retain ordinary
Blob downloads. Picker cancellation makes no request; errors show a closable dialog.
Write failures abort the writable and never silently download a fallback. A ref-based
single flight and generation guards invalidate late picker/fetch/write results on
project/account unmount. No inline export options or source-upload wizard exists.

A separate `RawConfiguration definitionOnly` instance is mounted inside closed
Technical details for administrator container projects. It retains the existing
recipe validation, explicit Save recipe, replacement, CAS and CSRF safeguards.
Dismissal restores focus; a recipe mutation cannot be dismissed mid-save.
Four locales cover controls, save errors and help; no bytes enter browser storage.


`DashboardShell.tsx` owns the authenticated frame, real navigation links,
branding, responsive menu, header and content focus. `Presentation.tsx` owns
`DataFeedback`, `ProjectEmpty`, `StatusBadge` and `DeliveryGlossary`.
`App.tsx` owns session, project hubs, SettingsList/SettingsImpactDialog, configuration/statistics mutations and route/history flow.
`settings.ts` owns purpose grouping and strict catalog/candidate transport validation
(input kind `connection` for rows whose `edit_key` is `executor.connection`,
`connectionRowVisible` hiding the endpoint rows unless the provider is `custom`, and
`validPendingConfig` accepting the connection JSON);
`agentConnection.ts` owns the connection types, `validConnection`, `connectionOf`, the
provider catalog read (`readProviderCatalog`; `validProviderCatalog` requires
`chatgpt.models` to be a string list), `providerModels` (Pi's models of an API-key provider, or `chatgpt.models`
for `chatgpt`), four-locale `connectionCopy` and `credentialNote`;
`AgentConnectionEditor.tsx` edits the connection (provider select with
OpenAI-compatible endpoint, ChatGPT subscription and an optgroup of API-key providers;
model input with `providerModels` as a datalist; endpoint URL and API select only for
`custom`, with help that the address is as seen from the container and that
`host.docker.internal` works only on Docker Desktop; a note naming the credential
variable, or for `chatgpt` that the server signs in to one ChatGPT Plus or Pro account
shared by every ChatGPT project and that stages get a short-lived access token);
Settings preserves native single-line heights for provider, model, reasoning
and conditional endpoint inputs. Multiline editors keep their own sizing.
`ChatGptSignIn.tsx` is the server's ChatGPT sign-in panel, shown to Admins of a
non-archived `chatgpt` project in the Agent and model Authentication slot in place of
the Provider API key form: status (`signed-in`, `not-signed-in`, `sign-in-again`, with
guidance for the last), **Sign in with ChatGPT** / **Sign in again**, **Disconnect
ChatGPT** (disabled while not signed in), and while a sign-in waits a two-step form
(open OpenAI's link in a new tab with `noopener noreferrer`; paste the full address of
the 127.0.0.1:1455 error page), a 15-minute validity note, **Complete sign-in** and
**Cancel**. The link and the pasted address live only in component memory, and the
address field is cleared on every attempt; after every action the panel rereads the
status. `chatgptCopy.ts` holds its four-locale copy and the strict transport parsers
`readChatGptView` (exactly `{status, pending}`) and `readChatGptStart` (exactly
`{authorize_url, expires_in}`, a link starting with `https://auth.openai.com/` of at
most 8192 characters); the `chatgpt_*` error sentences are in `errors.ts`;
`settingsCopy.ts` owns clear labels and localized setting guidance.
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
asks only for effective date and rates, submits executor `pi` and the applied
`executor.model` as hidden fields, shows set-a-model guidance when that model
is empty, and remounts per project and configuration revision. A successful empty Statistics response shows the measured zero lifecycle counts and explicit unavailable consumption; Quality and Trends show localized empty feedback. Initial/context loading and closed failures withhold numeric cards and CSV actions; same-context pending reads and explicitly marked transport/deadline failures retain the complete report.
An account whose password an administrator reset signs in to a dedicated
change-password card with the reason, language, theme and Sign out controls;
the dashboard and its polling stay inactive until the change succeeds, after
which the sign-in card confirms the change.
`errors.ts` turns API error codes into EN/FR/DE/RO sentences, appending any
diagnostic `message`; an unknown code shows a localized generic sentence that
names it, and network failures have their own message. The banner keeps the
raw failure and localizes it when rendered, so a language switch updates it.
Each user action and each view change clears the previous error banner;
background refreshes do not. EnrollmentWizard validates stable lowercase profile
IDs. RawImportDialog uses the server-validated suggested identity. Primary buttons use the `--on-accent` token, which
is dark text on the light accent in both system-dark and explicit Dark themes.


### Reviewed account and project access

The Users list opens one native `AccountActionDialog.tsx` for Add user or a
named account's reset. The dialog contains the creation wizard or reset form.
Both use `NewPasswordFields` and the same matching validation. Dismissal
discards the form and restores focus. During submission the dialog blocks
dismissal and repeat requests. Reset sends only the replacement to the selected
account's existing endpoint and acknowledges success only on `ok: true`.

`UserCreation.tsx` and `userCopy.ts` provide four-locale identity/credentials,
role/projects and review stages. The identity form uses the shared
`PasswordField.tsx` control for independently masked password entries. The repeat
entry stays in the identity form, must match before advancing and is discarded
when leaving that step. Only the original password is sent at creation. Admin explicitly receives all current/future
projects, system and cost access; Dev selects immutable IDs and receives project
access only. A deliberate checkbox confirms Dev without grants. Review shows
username, role and display labels with forge/repository plus stable IDs (choices are
`access-choice` rows with a muted `access-repo` line, without IDs, disambiguated by
unique name), with correction controls and
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

The API serves the build from its own process. Developers can start, retry and
cancel assigned jobs; job details show retry for failed runs and cancel for
nonterminal runs still owned by ADORE. Pending and completed human handoffs
have localized status labels; neither shows Cancel. Only administrators see
cost and account/config screens.

## 9. Validation And Tests

The statistics browser journey covering four locales and both themes has a
60-second case budget; its existing assertions remain unchanged. The file's
afterEach hook restores the authenticated account's English/light preferences,
including after a failed or timed-out assertion, before subsequent journeys.
The suite-wide and ordinary case budgets remain unchanged.

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


`e2e/import.spec.ts` covers modal selection and automatic validation, exact
stopped import, duplicate-submit protection, invalid or stale evidence, a changed
disk file, Dev denial, keyboard focus and four locales at 390px.

`tests/shell.test.mjs` checks glossary/catalog parity across EN/FR/DE/RO
and exact approved logo bytes, dimensions and PNG alpha format.

`tests/chatgpt.test.mjs` checks that the ChatGPT sign-in panel and every `chatgpt_*`
error code have non-empty copy in all four locales and that the status and start
transports are exact. The `e2e/executor-config.spec.ts` journey "an administrator
signs the server in with ChatGPT and disconnects it" drives the panel against the
offline server.

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
`playwright.config.ts` bounds the complete browser suite to 1800 seconds, with
default 30-second test and 10-second assertion limits, one worker and no retries;
the eight-way statistics locale/theme journey has a 60-second test budget.
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
duplicate/late requests, four locales and keyboard/
390px/light/dark views. Screenshot inspection complements automated checks; live
infrastructure, full accessibility and participant acceptance remain human work.

Discard focus restoration runs in a post-render effect after the mutation busy guard clears, with the original captured scope checked before focusing the enabled edit control.


Project Summary uses two panels beneath the shared project header. Its seven facts use one compact row on wide screens and wrap on smaller screens; the redundant Pi executor tile is omitted. Panel, empty-state and table spacing is reduced without hiding job evidence. The first
shows compact label/value tiles for Container type, Monitoring,
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
in the local image. **Workflow** is neutral file information: AEGIS from
`.agentic/aegis.py` alone, Direct otherwise in an available clone, or not inspected
when no clone is available. It names no version and has no failure/remediation icon.
There is no model endpoint check. Current saved explicit model-access evidence is shown when present; when no current result exists, model access remains untested. Unknown container detection is incomplete;
any failed check requires intervention with a targeted corrective instruction.
These checks do not prove a complete job, Git push permission or AEGIS execution.
Fresh browser evidence validates the API status contract, selected project identity, revision, UTC
check time and exact check keys/types before display (`readiness.ts`
`readinessChecksShape`: the five prerequisite keys plus, at most, the booleans of
`optionalReadinessKeys`: `executor_sign_in`, `egress_proxy` and `web_search_key`);
The closed workflow enum and prerequisite verdict agreement are validated separately;
invalid results produce a localized error and withhold the new check rows.
For a ChatGPT project `ReadinessEvidence.tsx` adds a **ChatGPT sign-in** row (passed
when the server is signed in; otherwise the fix points to Sign in with ChatGPT in
Settings → Agent and model). The internet switch adds **Network proxy image**
(`egress_proxy`, internet Off; the fix says to build `docker/Dockerfile.egress-proxy`
on the server) or **Web search key** (`web_search_key`, internet On with Brave or
Tavily; the fix points to Settings → Agent and model). The enrollment environment
check shows the same two keys with `enrollmentCopy.ts` fixes.

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

Administrators use **Settings → Agent and model → Test AI connection** for the configured Pi provider and model. Each explicit click sends one short request over Pi's RPC mode in a temporary container, or in a temporary folder for Pi installed on the server, and may incur provider charges. The project must be idle with valid saved settings and no pending configuration/operations; a container project's installed image must contain the pinned Pi.

Only a valid completed challenge response reports connected: one completed shell command printing a nonce, then the exact reply (a failed shell call reports **tool-call-failed** with permission guidance). `modelEvidence.ts` gives four-locale guidance for every reason, including **credential-missing** (no key saved or set; no container starts), **credential-invalid**, **connection-failed**, **model-unavailable**, **rate-limited**, **provider-error** and, for a ChatGPT subscription, **sign-in-required**, **subscription-refused** and **usage-limit**. The action reuses executor credentials and egress and starts no job. Evidence is durably saved, bound to current project/model/configuration and credential inputs. Summary and host-check details reuse the current access result. Host-check time/version are internally validated and hidden from Summary/check details. See Component_Model_Connection.md.


## Project setting scope and guidance

Project Settings displays the selected project's operational settings, including inherited defaults. Executor/model/authentication settings belong to Settings → Agent and model. Descriptions remain permanently below each label and provide the editor's accessible description. There is no per-row Help disclosure or override-only filter. The default/source marker describes value origin, not ADORE-wide scope. Polling intervals, per-project concurrency, executor and recovery settings remain per-project within Settings; the backend, container runtime and image are reviewed edits there, while other environment setup is externally managed. Global capacity and audit retention belong to Administration. No project setting is promoted into a global policy by this presentation.

Proof: web/e2e/settings.spec.ts project settings keep defaults and single guidance (administrator/developer), plus existing candidate edit/discard journey.

## Project executor configuration

**Project → Settings → Agent and model** configures Pi, ADORE's only coding agent; there is no agent choice. It shows Test AI connection, the agent connection (Provider, Model, and for an OpenAI-compatible endpoint Endpoint base URL and Endpoint API type; one reviewed candidate, `executor.connection`), the launch command (`executor.command`; a container project may choose only the one Pi preset, a local project uses fixed managed Pi RPC), Internet access for the agent (`executor.internet`, On/Off, default Off), Web search (`executor.web.search`: Exa (no key), Brave (key needed), Tavily (key needed), None), additional credential variables (`executor.env_keys`), the provider API key, the execution environment (`execution.backend`, the container runtime and image, and the current account and optional project tools PATH for local projects, with external container guidance) and estimated prices. A new model ID must be supplied explicitly. Credential names are added through a dropdown and remain visible as individually removable selections. Connection, command, internet access, web search, backend, runtime and image edits go only through the reviewed flow (prepare candidate, review, apply). While internet access is On, or the editor or the candidate review proposes On, an alert says a malicious web page could try to make the agent send its API key or ChatGPT token out and recommends limited, short-lived keys; a local-backend project shows instead the note "Not enforced: this project runs Pi installed on the server, which reaches whatever the server reaches." While the image row is edited it offers the same server image suggestions. Installed agents and runtime preparation remain external. The old `/executor` URL redirects to Settings. Developers read non-secret settings/results without mutation actions.

The names-only selector for additional credential variables offers the known provider key variables and retained custom names; it defaults to empty (`env_keys = []`) because the provider's key variable is always passed. Applying names does not delete saved `.env` values. Provider API key offers private Save/Disconnect for the variables the server names (the configured provider's credential variable, then `BRAVE_API_KEY` or `TAVILY_API_KEY` while internet is On with Brave or Tavily search) and shows their sources only; key changes require paused pickup and idle/pending-free state. A ChatGPT subscription has no provider credential variable; its Admins see the ChatGPT sign-in panel there instead, plus the key panel when a search key is needed. Explicit Test AI connection remains the evidence of model access and may incur provider charges. See [Executor configuration](../05_SoftwareDocu/Component_Executor_Configuration.md) for the exact API/storage contracts.

### Transient application notifications

The application shows one dismissible notification for ordinary feedback or the current operation. Operation status replaces the queued confirmation. Pending/running operations stay visible until completion or dismissal; successful results and ordinary notices disappear after five seconds; failed and uncertain results remain until dismissed. Closing the banner keeps worker polling and final project refresh active. Replacement/unmount cancels earlier dismissal timers; persisted outcomes remain available in History. Error alerts retain their existing presentation.

Editable settings place **Edit** beside **Active value** in the value column, including narrow screens. Administrators retain candidate review/apply/discard and disabled-state safeguards; developers have read-only rows.

Project Settings purpose categories are collapsed on entry. Opening a category shows desktop description and control columns in a 3:2 ratio separated by 32px, with values/actions aligned to the right; below 640px they stack at full width. Native disclosures retain keyboard operation. Agent and model groups AI connection, the Pi model and launch command, closed Authentication and external environment guidance. Its inline field editors retain the existing row columns and stack using the normal mobile layout; the credential-name dropdown and removable selections wrap within the value column.

## Preparation review and outcomes

`executionPlan.ts` validates closed public plan/outcome envelopes. `ExecutionPlanReview.tsx` renders image authority, source/job/revision, hashes and all commands in retained candidate reviews, with four-locale guidance. `PreparationResults` renders persisted attempts and step outcomes in job details and explicit CLI replay guidance on failure. Incomplete/forged evidence cannot display preparation success or enable an unbound recipe Apply. Focused tests: `web/tests/executionPlan.test.mjs` and external ownership journeys in `web/e2e/settings.spec.ts`.

## Native execution contract

Native execution is selected with **Runs in → Installed on the server** at enrollment or in the reviewed Settings flow, in the server profile, or through server TOML enrollment. Existing native executor/model and explicit host checks use that prepared environment. The container notice is omitted for local projects. See [Local execution](../01_Documentation/Local_Execution.md) for machine/account, authentication and process ownership.

## Project image workspace

`ContainerRuntimePicker.tsx` loads administrator runtime suggestions when the Settings editor opens. The select and manual input share the active draft, including on unavailable discovery. `serverImages.ts` sends the selected runtime as a URL query value for image suggestions. The reviewed Save path remains the persistence boundary. `images.spec.ts` covers WSL selection, image lookup, cancel and manual save.

Settings → Agent and model shows a compact container notice with the effective image and one expandable instruction disclosure. It identifies standard `executor/Dockerfile`, optional `executor/README.md`, a non-root example, external Docker/Podman build and verification, and the existing profile fields. Only administrators see the actual resolved server `config.toml` path. No controls define or build an image; **Executor image** (enrollment step 2 and Settings) selects one that the administrator prepared on the server. Specialized profiles use server TOML enrollment. The retired image-build routes are removed and answer 404. See [Project executor images](../01_Documentation/Project_Executor_Images.md).

`ExecutorEnvironment.tsx` renders read-only four-locale content from the config response. `serverImages.ts` reads the server's images (`readServerImages`, `validServerImages`) and proposes an image for an executor (`proposeImage`: tag starts with `<executor>-`, preferring `adore-executor-base:`); the enrollment wizard and the Settings image row use it, and an unreadable list is shown as unavailable. `settings.ts` exposes `CHOSEN_ENVIRONMENT_KEYS` (`execution.backend`, `container.runtime`, `container.image`, `local.*` account keys), which Agent and model shows and edits through the reviewed flow. `App.tsx` filters the other container/execution/local/worktree settings from both settings lists. The pending review shows no image-build binding. A candidate with an image-build binding or for an operator-owned environment key could only be staged by an earlier build; the server reports it as `pending_config_corrupt` and the administrator can still discard it. `images.spec.ts` proves the disclosure, Admin/Dev scoping, local suppression and mobile wrapping; `test_web_pending_config.py` and `test_executor_environment_choice.py` prove the corrupt-but-discardable candidates.

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

## Agent and model settings

executorSettings.ts supplies four-locale labels and row help for the Pi settings `executor.provider` ("Provider"), `executor.model` ("Model"), `executor.endpoint.base_url` ("Endpoint base URL"), `executor.endpoint.api` ("Endpoint API type"), `executor.command` and `executor.env_keys` ("Additional credential variables"), and the names-only credential guard; `internetCopy` adds `executor.internet` ("Internet access for the agent", shown On/Off), `executor.web.search` ("Web search", shown Exa (no key) / Brave (key needed) / Tavily (key needed) / None), the On warning and the local not-enforced note, and `searchKeyNeeded(config)` tells whether a Brave or Tavily key is needed; there is no agent choice. The provider, model and endpoint rows open `AgentConnectionEditor` for one `executor.connection` candidate; the launch command is an ordinary reviewed row edited by the generic SettingsList editor: a container project offers only the Pi preset for the command, a local project has no command editor. ExecutorCredentials.tsx ("Provider API key") accepts whichever variable the server names and shows the ChatGPT note when the server names no variable for `chatgpt`; App.tsx renders ChatGptSignIn.tsx instead of it for an Admin of a non-archived `chatgpt` project. CredentialNamesEditor.tsx adds distinct names from a native dropdown and shows removable selected names; duplicates are disabled and malformed drafts cannot enable preparation. SettingsList groups private API keys inside Authentication. routes.ts redirects old /executor links to /configuration for both roles. The field editors and selected-name list wrap at 390px without horizontal overflow. Offline executor/settings/images/model-connection browser journeys cover role boundaries, four locales and narrow layout.

## Managed native Pi

Native enrollment and Settings show the current account and optional project tools PATH. The setting catalog describes the fixed `current` account and service PATH fallback, and includes `executor.thinking` with the Pi default and supported-level constraints in all four locales. The host checks render closed managed Node/Pi causes in all four locales, and local projects explicitly state that network restrictions are unenforced on the server.

The four-locale repository connection browser journey waits for successful
language and theme preference writes before full document navigation. This
keeps the keyboard and narrow-layout proof independent of request timing.


## Native ChatGPT callback completion

ChatGptSignIn observes pending server sign-in once per second while the page
is visible. It stops polling on completion, unmount or the 15-minute bound.
A native Pi callback can complete without a pasted redirect. Verified
completion clears the temporary link and address; failed helper completion
shows the existing localized cause. Manual state-checked completion remains
available when the browser cannot reach Pi's loopback listener.
The callback Chromium journey proves completion without sending a PUT.


### Exact API-candidate recovery

A valid pending candidate containing an API-only or hidden setting remains read-only in the row UI. Navigation is guarded throughout saving and confirmation, including read-only recovery with no local dirty fields. The one Save action rereads and compares the complete pending envelope, confirms its safe values and applies the exact existing candidate/base pair without preparing a replacement. Stale or corrupt evidence blocks Save and remains explicitly discardable. GUI-editable pending batches recover into visible editors and use bound replacement. Focused proof: `settings-save.spec.ts` API-only success/stale/corrupt cases and `test_web_settings_batch.py` collateral replacement preservation.

## Failed-job drift recovery

JobWorkspace uses `recoveryCopy.ts` in English, French, German and Romanian for confirmed Abandon and start again, stable-settings drift guidance and operation failures. Browser confirmation names the ticket and irreversible local/worktree/remote deletion. Cancellation submits nothing. The request carries the captured state revision; stale refusal keeps details visible. `jobModel.stableExecutionDrift` suppresses guaranteed-failing Retry for stable profile/settings drift while preserving native volatile identity revalidation. Proof: `web/tests/jobs.test.mjs`, `web/e2e/driftRecovery.spec.ts`.

`restart:retained` is a localized success warning, explaining that an older branch without ownership evidence was preserved while a fresh branch was used. Browser proof: driftRecovery.spec.ts retained-branch success journey.

## Job budget presentation

Job details displays Executor launches and cumulative Active work (seconds) as
consumed/current-limit pairs, independently of token/cost measurement coverage.
At 90% of either limit it shows a localized status notice; at exhaustion it shows
adjustment guidance. Administrators have a project Settings link; developers see
counters without financial limits or editing authority. Current limits apply at
the next attempt/resume; in-flight attempts retain their timeout. `jobModel.ts`
refuses malformed counters, limits, durations and revision hashes. `jobCopy.ts`,
Settings confirmation and setting help share four-locale timing guidance.

Offline proof: `web/tests/jobs.test.mjs`, public HTTP contracts and the four-locale
budget journey in `web/e2e/jobs.spec.ts`.

Current limit faults preserve valid Job details and recovery. The budget observation
uses `availability=unavailable`, a closed missing/corrupt reason and null limit/revision
fields, while keeping trustworthy consumed launches and active seconds. The interface
shows — for limits and a localized notice. Corrupt saved job evidence still rejects
the detail read. Metadata-only profile history retains its existing recovery behavior.

## Operational Job details

JobWorkspace shows localized normal-state guidance, visible stage failure counts and second-precision times. The active clarification lives in its own tab and uses ForgeMarkdown with inert HTML, permitted navigation, image placeholders and local scrolling; its readable view omits leading comments while its original source remains expandable. Raw ticket source uses the same themed scroll region. Consumption errors include an actual localized refresh button while evidence/recovery stay separate.

ExecutorOutputView fetches only on demand and rejects stale/unmounted or identity-mismatched responses. The viewer displays host-normalized diagnostics and explains omitted private content and unavailable provenance. Browser regressions exercise four locales, safe Markdown, concrete output, refresh and 390px dark-theme local scrolling.


## Production bundle consistency

The production bundle is committed whenever frontend build inputs change.
The existing post-build legal stamper also records SHA-256 hashes of build
inputs and all generated output files in `BUILD_FINGERPRINT.json`. The release
consistency checker compares those hashes before packaging; a missing stamp or
drift requires `npm run build` in `04_Software/web` and committing the result.
The checker also compares against an isolated fresh build, using the installed frontend dependencies.


History renders localized ticket/job identities, a CLI actor for CLI deletion, and failed separately from rejected and uncertain. The interface validates the closed response before rendering.


Enrollment and Agent and model expose supported Pi thinking levels. Enrollment displays localized check names and times and transfers only server-issued current evidence; incomplete checks stay partial. Local execution and repository reconnect actions use descriptive labels.

Project-list readiness is parsed as a closed identity/revision/checks verdict before display. The Repository access action does not infer repository access from CLI authentication.

The project lifecycle browser fixture reads an authenticated initial catalog once
and fulfills its local archive-state view without asynchronous upstream proxies.
This avoids handler-removal races during polling teardown while preserving all
lifecycle, scoped CSRF, clone ownership and exact-name deletion assertions.

Recipe recovery errors name the server data to remove explicitly. A whole-catalog
reset message in all four locales explains that image definitions for all projects
are removed while configurations, credentials and jobs remain untouched.

## Publication approval setting

The PR/MR settings category presents the reviewed per-project human approval
boolean in all four locales. It defaults to enabled and uses the existing
administrator confirmation and idle-project mutation boundary.

## Job details presentation

`JobDetails.tsx` presents the verified detail separately from the job list. The
header combines ticket number and title; Job actions shares the current-stage
metadata row and exposes only commands allowed by the existing command policy.
Retry, cancel and confirmed fresh-run recovery keep worker authorization, CSRF,
revision binding and confirmation behavior. Close restores the existing list filters.

The current lifecycle, responsible actor and Next step precede secondary budgets
and consumption. Missing usage or limits remain explicitly unavailable, never
zero or guessed progress. Activity lists saved events newest first with localized
names for recognized events and the original event code. Unrecognized events use
a neutral title. An older clarification event is historical, not a current action.

Three keyboard-accessible tabs separate Activity, Agent question (only while
clarification is active) or Evidence and artifacts, and Technical details. The
question uses the existing safe Markdown renderer. Leading editorial HTML comments
are omitted from its readable view; an expandable Original question and evidence
retains the exact source. Other HTML stays inert text and images are never loaded.
No historical question content is inferred when the API no longer provides it.
Technical details retains identifiers, on-demand verified executor output, recovery
diagnosis and the paged original timeline. All tabs use the same saved evidence;
none starts an executor or grants candidate approval. Copy and help cover all four
locales. The layout uses the application's light/dark tokens and stacks on narrow
screens. No API, stored format or dependency change is required.

## Compact project and Jobs controls

The global Jobs page places its project scope selector at the right of the Tickets/Jobs tab row. It wraps below the tabs on narrow screens; the project hub retains its fixed scope without that selector. Job search keeps its accessible label, 80-character limit and status filter without a descriptive paragraph.

Project Settings hides the Save/Discard bar when the draft is clean, including when an unchanged editor is open. Unsaved or recovered edits, an in-flight save and failed pending-candidate reads retain the controls and recovery feedback. Successful save/discard hides the bar and returns focus to the settings panel. Invalid and stale drafts remain visible and cannot save.
