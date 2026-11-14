<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Persisted Web Job Reads

## 1. Purpose

`adore/web/jobs.py` builds a complete, authorized global job projection for
the HTTP API from retained local run sources. It supplies job evidence for
administrator and project-assigned developer clients.

## 2. Responsibilities

The API owns principal and project-grant resolution. The projection owns strict
source validation, composite identity, actual evidence, UTC ordering and an
optimistic source revision. It reads current and archived profile history.
The existing conductor owns lifecycle, state updates and operational recovery;
statistics owns usage measurement. Job reads invoke no external command.

## 3. Implementation Overview

`read_jobs(profiles, items)` receives already authorized profiles and captures
the profile metadata, complete run-directory inventory and exact state, ticket
and journal bytes. It validates all selected records, reinspects sources and
returns ordered rows plus a SHA-256 revision. The API rechecks selected profiles
and grants before returning any results. A failed selected project aborts the
whole read. The projection does not call the forgiving `StateStore.list_runs`
or operational `read_journal` reader.

## 4. Dependencies

Standard-library JSON, datetimes, URL parsing and hashing; existing `Profile`,
`ProfileStore` and `RunState.from_dict`. HTTP authentication and errors are
provided by `app.py`. There is no new runtime dependency or persisted schema.

## 5. Inputs And Outputs

`GET /api/v1/jobs-page` accepts `project_id`, `q`, `status_group`, `attention`, `overview`,
`limit`, `offset`, `snapshot`, `sort` (`activity`, `ticket`, `project`, `status`;
default `activity`) and `order` (`asc`/`desc`; default newest activity first,
otherwise ascending); every matched job is sorted before paging, unknown values
last, and other `sort`/`order` values return 422. Other query parameters are ignored. `project_id` is an immutable 32-hex
identity. `q` is a trimmed case-insensitive substring of 1–80 characters;
search covers project name/display name, run ID, ticket number/actual title,
lifecycle, stage and outcome. `limit` is 1–100 or `all`, default 25; offset
is nonnegative. `attention=true` selects clarification, approval, in-review,
failed, stale and handoff-pending. Whitespace-only search text returns 422.

The response contains `items`, matching `total`, `counts`, `groups`, `limit`,
`offset`, `complete: true`, `snapshot` and
`snapshot_semantics: "optimistic-source-revision"`. Counts and groups describe
the authorized, project-filtered, searched population before status-group and
attention selection. Archived jobs are included and each row carries `project_archived`.

With `overview=true`, each authorized project is validated independently.
Projects with `run_state_corrupt` contribute no rows or counts. Their IDs appear
in `unreadable_projects` when present, and paging applies to the combined verified
rows. The revision binds readable project revisions and unreadable IDs. A change
in coverage invalidates continuations. A second capture rechecks the complete
scope for changes during the read. Other errors still fail the request.

`GET /api/v1/jobs/{project_id}/{run_id}` returns
`{job, complete: true, snapshot}` for the composite identity. Its strict read
validates the selected project's retained history. An unassigned or absent
project returns 404 `project_not_found`; an absent run returns 404 `run_not_found`.
Existing `/projects/{name}/runs`, `runs-page` and run-detail contracts continue
to serve existing clients.

## 6. Data Contracts

Each list job exposes `project_id`, project labels/archive flag, `run_id`, ticket
number/actual title/URL, MR URL, exact `lifecycle`, `stage`, `workflow`, `outcome`,
stage/review counters, `created_at`, `updated_at`, `last_activity_at`, `waiting`,
`evidence_url`, `coverage` and `consumption`. Empty outcomes remain empty.
No stage implies completion, waiting, a reviewer or a next action.

`last_activity_at` is the latest valid persisted state update or journal event
timestamp, normalized to UTC. Missing timestamps are null. Ordering is that
instant descending, missing values last, then project ID and run ID ascending.
Thus equal instants with different original timezone offsets tie deterministically.

`waiting` contains availability, reason, next_action, responsible_role,
responsible_person, evidence_url and source. Real parked questions provide the
reason when its journal timestamp is at or after the current `parked_at`;
missing correlation and older questions stay unknown. A saved comment ID and ticket URL support `answer_question_on_ticket`.
Saved candidate digests, presentation time and approval comment ID support
`review_candidate_on_ticket`. `in-review` with a saved MR URL supports
`review_draft_on_forge`. Roles are human_responder, human_approver or
human_reviewer respectively, supported by these observed references. Named
responsibility is null: existing snapshots do not identify an assigned person.
Other waiting evidence stays unknown. GitLab comment links use `#note_ID`;
GitHub/Gitea use `#issuecomment-ID`; unknown platforms retain the actual ticket URL.
Source markers identify the saved state field or parked journal event.

Coverage distinguishes missing/present ticket and journal files and unknown/observed
title and last activity. Empty titles are unknown. Consumption is
`{availability: "unknown"}`; absence is never a zero measurement. The composite
API detail URL locates the safe local evidence view without disclosing host paths.

Strict composite detail additionally exposes `timeline`: saved events in append
order with only normalized UTC `ts` (or null), redacted `event`, and validated
persisted `stage` (or null). Missing stages remain unknown. The timeline is not
added to list rows. Malformed recorded stage/executor identities in a journal,
including an event naming the removed `deliver` stage, fail closed
(`run_journal_corrupt`) before any result is returned.

HTTP(S) source links require valid host/port and exclude credentials, query/fragment,
controls and backslashes, including percent-decoded forms. Free text redacts
common token/password/secret/API-key/authorization assignments and Basic/Bearer
credentials. Descriptions, authors, arbitrary journal values, financial payloads,
outbox bodies, worktree paths and general validation payloads are excluded. The
projection below contains only the recorded agent attempt.

`workflow` is the recorded `aegis` or `direct` value in authorized list and detail
reads. Missing/unknown/nontext workflows and direct AEGIS task bindings return
503 `run_state_corrupt`, never an inferred value. Jobs uses that saved value for
workflow labels and direct-stage presentation; repository readiness cannot replace it.

Direct details expose only the closed `direct = {attempt}` object. The attempt
comes from the last recorded stage launch, never from budget or failure counters.
Old independent-verification fields in retained state are not projected or executed.
The UI displays agent attempts without command/result/output verification panels.

`_direct_evidence` consumes the same captured run/events as `_view`, before filters,
counts or paging. `jobs_page` strips `direct` along with timeline from list rows.
AEGIS details omit `direct`. Direct execution stages are build/validate/done.
The failed `publishing` recovery pointer is also readable, and a `reset` event may
record `publishing` even after Retry has completed. Other events cannot introduce
that execution stage. Malformed saved state/result produces `run_state_corrupt`,
malformed attempts/events produce `run_journal_corrupt`. No source is repaired,
engine helper invoked, stored field added or execution behavior changed.

Schema-1 state is validated without adding fields or writing defaults. Ticket
and journal files may be absent; malformed files, duplicate JSON keys,
non-finite constants, parser depth failures, invalid Unicode scalars, torn JSONL records, invalid projected types, mismatched
ticket/run identity and nonempty malformed timestamps fail closed. An empty
`created_at` or `updated_at` is `run_state_corrupt`, because every save stamps
both. Operational
journal recovery retains its existing tolerance for torn lines.

Typed `JobReadError` exposes only a code: 503 `run_state_corrupt`,
`run_journal_corrupt`, `job_evidence_corrupt` or profile integrity codes;
409 `job_snapshot_changed` for observed source changes. Errors contain no
source bytes or partial totals. Invalid query bounds return 422.

## 7. Workflow Integration

Global pages sort and page an in-memory projection of verified rows. Clients
pass the returned `snapshot` on continuations. A change to included sources or
profile metadata, or a change in authorization or Overview coverage, invalidates
the continuation. Restart at offset zero. Search and page parameters share the
same source revision. Project-scoped revisions cover the selected profile.
A deleted profile is unavailable; an archived profile retains history. An absent
runs root is an empty collection; unreadable sources and orphan run folders
are integrity errors. No source is repaired or reset by reading.

## 8. Usage

After session authentication, request `/api/v1/jobs-page?limit=25&q=build`.
For the next slice, send `offset=25&snapshot=<returned digest>` with the same
filters. A 409 indicates that the local sources changed; reload the first slice.
Use `project_id=<immutable ID>` for the same model within a single authorized project.

## 9. Validation And Tests

`tests/test_web_jobs.py` verifies multi-project paging/search, totals, grants and
direct routes, recorded workflows for Admin and scoped Developer reads,
corrupt workflow/task refusal without source changes, direct attempt and all verification
outcomes/absence, exact large exits, redaction, Unicode bounds, malformed selected
evidence, absent current config, colliding run IDs, timezone ties, source/grant mutations,
archived/missing metadata, wait evidence, forge anchors, unsafe URLs, corrupt
state/tickets/journals, secret filtering, IO failures and zero subprocess calls.
Advanced-filter/timeline tests prove matching, bounds, corruption/redaction and
attention selection. `test_project_summary_refuses_a_run_without_an_aware_activity_time`
proves the project list answers 503 `run_state_corrupt` for an empty, malformed
or naive update time.
`test_web_paging.py`, `test_web_rbac.py` and `test_state.py` preserve adjacent
API and recovery contracts. Final verification uses repository strict validation.

## 10. Limitations And Future Work

The revision is optimistic and content-based, not a durable frozen snapshot or
a multi-file transaction. A host write after final reinspection appears on the
next read. Each request scans all authorized selected history twice; memory and
IO scale with retained sources. Read-time file absence cannot recover deleted
history. Named responsibility and usage remain unknown until actual persisted
contracts supply that evidence. The action workspace consumes this projection; Statistics supplies separate
measured duration and usage contracts.

## Preparation projection

Authorized job reads validate `RunState.execution` then expose only preparation status, attempt count, image, fingerprint and ordered timestamp/exit/timeout/cancel summaries. Jobs without a recipe selection (including the empty no-recipe record) carry null. Source scripts, policy and raw streams remain outside the job projection. Existing composite identity, authorization and optimistic snapshots are preserved.

## Confirmed restart evidence

Every job exposes `state_revision`, SHA-256 of its validated state bytes. Failed jobs offer Abandon and start again with destructive confirmation, including loss of unpublished work and preservation of monitoring pause. Stable execution-profile/settings drift explains why Retry cannot help and hides that button; volatile native environment changes remain eligible for explicit Retry, including processor variables after VM resizing. Restart binds confirmation to this revision; malformed/missing revision disables the action. Four-locale browser proof: `web/e2e/driftRecovery.spec.ts`; model proof: `web/tests/jobs.test.mjs`.

An older occupied ref without a saved checkpoint is retained during confirmed restart, which chooses a fresh generation under the repository naming rule. Known changed checkpoints still refuse. The successful result explains retained old branches; normal owned branch reuse remains available under strict rules.

## Detail budget observation

`read_job_budget(profiles, item, run_id, state_revision)` adds `budget` only to the
composite job-detail response: `launches`, `max_launches`, `active_seconds`,
`max_active_seconds`, `config_revision`, `availability`, `reason`. It binds saved state bytes to the earlier
projection and rechecks both configuration and state bytes after reading. Limits
are current project settings, applied by the conductor at its next boundary.
The budget allowlist, positive safe-integer bounds and finite cost validation run
locally; no branch matcher, forge, model or runtime command is launched. No financial
value is returned to either role. Corrupt saved state returns a typed read failure;
concurrent source replacement returns 409 `job_snapshot_changed`. Missing/corrupt
current limit configuration raises a classified internal read error, represented as
availability=unavailable with reason=config_missing/config_corrupt and null limits
and config_revision. Valid saved counters, history and recovery stay available;
no default is invented. Derivation type errors are classified, including AttributeError.

Public HTTP proof: `test_web_jobs.py` checks counters/frozen elapsed time, roles,
source corruption and authorized identity. Statistics consumption remains separate.

## Operational executor evidence

Job cards explain normal Working, parked-clarification and Failed lifecycles in four locales and surface current-stage failed-attempt counts. Clarification reasons use the shared safe ForgeMarkdown renderer. Times include seconds; the event projection uses explicit stage, usage/artifact stage context and stage-transition current destination, never today's run stage for unrelated past events.

`GET /api/v1/jobs/{project_id}/{run_id}/executor-output` authorizes before reads and rechecks grants after them. The last executor-artifacts event must carry a host-generated diagnostics reference (`file`, SHA-256, cumulative `attempt`). `executor_evidence.read_executor_output` reads only the run-owned executor-diagnostics snapshot, checks stable regular unlinked files, exact schema/identity/context/digest and normalized stream content. It never opens raw executor archives. Missing provenance/files return availability missing; corruption is a typed 503 and a changing snapshot is 409. Both roles get the same operational facts, without financial text.

The response projects the attempt, known stage and UTC time from the bound
event. A later launch marker on a working job indicates that the completed
output belongs to an earlier launch. The UI keeps the last verified response
for the current job while refreshing, labels stale results and provides inline
retry for 409. Nonempty streams use independent, scrollable disclosures.

Snapshots are capped at 150 KiB JSON, with at most 500 diagnostic records and 64 KiB per stream. Run/journal reads are bounded. Public HTTP tests cover concrete missing-module/test-count diagnostics, scoped/revoked grants, unsafe references, malformed/oversized/linked files and explicit missing provenance.

## Job detail consumer

`web/src/JobDetails.tsx` consumes this existing projection without changing the
API or stored formats. Its current-action card and tabs keep active clarification
separate from historical events. Outside the parked lifecycle the API does not
supply historical question text; the frontend never reconstructs it from event
names. Presentation, safe question rendering and command delegation are described
in [Component Web Frontend](Component_Web_Frontend.md#job-details-presentation).


## Recorded agent sessions and global navigation

Global `/jobs` opens the existing job list with search, status filters, server sorting,
pagination, refresh and selectable all-authorized-project/single-project scope.
Global `/tickets` opens the existing ticket workspace, automatically reading its scope
on entry and scope changes; Read tickets remains available. Generation and synchronous
pending guards prevent duplicate pending reads and stale completions. Project listing,
hub tabs and project-specific Tickets/Jobs/Capacity controls retain their existing layout.

Job details place Activity / Agent sessions / Artifacts / Technical information tabs,
Show ticket and right-aligned Close above the ticket title. The status line uses saved
status, stage and workflow. Actions, budgets, consumption, clarification, approval and
review remain available; closing restores the originating list state.

`adore/web/executor_session.py` supplies `list_sessions(run)` and
`read_session(run, attempt_id, cursor=0, limit=200, include_cost=False)`. Authenticated
GET `/api/v1/jobs/{project_id}/{run_id}/sessions` and its `/{attempt_id}` child resolve
ownership through the strict existing job snapshot and recheck grants before release.
Both return Cache-Control: no-store. Only the run's own exact archive folders are read,
with regular-file, hardlink, symlink/reparse and parent identity checks. No migration
or alternative stored format is introduced. Start time is null because current metadata
records only archive completion; exit code and timeout describe the physical launch.

The JSONL reader accepts complete LF lines, emits prompt/assistant/readable reasoning,
tool call/result, turn, usage and notice items, ignores system/delta/agent_end messages,
and retains literal recorded text including secrets. Each text is at most 16 KiB with
an explicit truncation marker; records above 256 KiB become notices. Files above 64 MiB
produce a notice without scanning them. A normal page scans up to 4 MiB between records;
skipping one oversized line is bounded by the 64 MiB source ceiling. Byte cursors name
line starts. The requested limit strictly caps source items at at most 200; an assistant
source item can group up to three bounded typed text/reasoning/usage parts. A pending partial
line is never projected. Structured usage costs are administrator-only; literal agent
text is not redacted. Existing normalized latest executor output stays independent.

`SessionView.tsx` and `sessionModel.ts` own on-demand attempt selection, validated
transport, stale-response guards, collapsed reasoning and expandable tools plus cursor
Load more. Live polling uses the launch protocol below; instruction transport is absent. Focused proof lives in
`test_web_executor_session.py`, retained `test_web_jobs.py`, frontend session/routes/job
model tests and jobs/tickets browser journeys. Real-provider and Linux link acceptance
remain operator checks; Windows hosts without symlink privilege skip those cases.

## Live agent sessions

The shared reader also serves `io/output.jsonl` for the first listed live attempt.
PiExecutor publishes schema-1 `io/live.json` only after clearing stale output and
holds the existing crash-released StateStore kernel lock for `agent-session` around
RPC and archival. A working lifecycle, exact marker and held lock are all required;
an abandoned marker or retained old output cannot advertise an active launch. The
marker records a random launch id, exact planned archive id and start timestamp,
and is removed on success or exception after archive handling.

Live GET pages use the existing numeric complete-line cursor and item bounds plus
`continuity`, a digest of stable file/launch identity and the consumed byte prefix.
The returned digest is built from exactly the bytes parsed, then verified against
the file. Normal appends are allowed; replacement, truncation, equal-length rewrite
or marker/lifecycle change returns `session_ended` with `archive_id` and no items.
Partial tails retain their starting cursor. No older-format reader is provided.
The live route accepts the retained archive id for handoff after marker removal.
Source files above the size bound return one notice and stop transcript reads.

SessionView polls accepted live cursors every three seconds only while working,
visible and selected in Agent sessions. Hidden views fence in-flight completions
and preserve accepted state. Bounded thinking hints and completed tool start/end
items maintain unfinished work without streaming text. Ended sessions reload the
final archive from zero or follow the next live launch. While following between
launches, the list discovers the next launch every three seconds; explicit history
selection stops following and survives ordinary detail/visibility refreshes.
Agent sessions remains mounted after its first visit so tab changes retain choice.
Saved lifecycle status and compact job header remain independent of transcript data.
No instruction transport is implemented. Focused contracts: live cases in
`test_web_executor_session.py`, marker lifetime cases in `test_pi_rpc.py`, session
model/helper tests and LA-02 browser journeys in `e2e/jobs.spec.ts`.

Live continuity verification uses a fresh unbuffered descriptor, independent of parser
read-ahead. EOF before the captured size ends the changed session without retry loops.

RPC session persistence also retains known credential values literally; its bounded
raw file is copied unchanged for package jobs. Operational tails, stderr, questions
and diagnostics retain masking. Archive copies reject links and oversize/change races.

Accepted archived pages and EOF retain their exact pagination across hidden views.
Only live cursors or an initial history read not yet accepted resume automatically;
failed/interrupted initial history remains retryable.
