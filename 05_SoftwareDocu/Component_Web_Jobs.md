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

`GET /api/v1/jobs-page` accepts `project_id`, `q`, `status_group`, `lifecycle`,
`stage`, `attention`, `executor`, `outcome`, `updated_from`, `updated_to`,
`limit`, `offset` and `snapshot`. `project_id` is an immutable 32-hex
identity. `q` is a trimmed case-insensitive substring of 1–80 characters;
search covers project name/display name, run ID, ticket number/actual title,
lifecycle, stage and outcome. `limit` is 1–100 or `all`, default 25; offset
is nonnegative. Lifecycle and stage filters accept exact persisted vocabulary,
including `stale`, `done` and the legacy `publishing` stage.
`attention=true` selects clarification, approval, in-review, failed, stale and
handoff-pending. Executor is an exact case-sensitive journal identity (1–200
characters); outcome is a trimmed case-insensitive fragment (1–80).
Update dates are inclusive UTC stored-update days; missing timestamps do not
match. Reversed dates or whitespace-only text filters return 422.

The response contains `items`, matching `total`, `counts`, `groups`, `limit`,
`offset`, `complete: true`, `snapshot` and
`snapshot_semantics: "optimistic-source-revision"`. Counts and groups describe
the authorized, project-filtered, searched population before lifecycle/stage/group
selection and before attention/executor/outcome/date filters. Archived jobs are included and each row carries `project_archived`.

`GET /api/v1/jobs/{project_id}/{run_id}` returns
`{job, complete: true, snapshot}` for the composite identity. Its strict read
validates the selected project's retained history. An unassigned or absent
project returns 404 `project_not_found`; an absent run returns 404 `run_not_found`.
Existing `/projects/{name}/runs`, `runs-page` and run-detail contracts continue
to serve existing clients.

## 6. Data Contracts

Each list job exposes `project_id`, project labels/archive flag, `run_id`, ticket
number/actual title/URL, MR URL, exact `lifecycle`, `stage`, `outcome`,
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
persisted `stage` (or null). Missing stages remain unknown. Internal observed
executor identities are used only for matching; neither those identities nor
the timeline are added to list rows. Malformed recorded stage/executor identities
fail closed before any filter, including an unrelated filter.

HTTP(S) source links require valid host/port and exclude credentials, query/fragment,
controls and backslashes, including percent-decoded forms. Free text redacts
common token/password/secret/API-key/authorization assignments and Basic/Bearer
credentials. Descriptions, authors, arbitrary journal values, financial payloads,
outbox bodies, worktree paths and validation command output are excluded.

Schema-1 state is validated without adding fields or writing defaults. Optional
legacy ticket/journal files may be absent; malformed files, duplicate JSON keys,
non-finite constants, parser depth failures, invalid Unicode scalars, torn JSONL records, invalid projected types, mismatched
ticket/run identity and nonempty malformed timestamps fail closed. Operational
journal recovery retains its existing tolerance for torn lines.

Typed `JobReadError` exposes only a code: 503 `run_state_corrupt`,
`run_journal_corrupt`, `job_evidence_corrupt` or profile integrity codes;
409 `job_snapshot_changed` for observed source changes. Errors contain no
source bytes or partial totals. Invalid query bounds return 422.

## 7. Workflow Integration

Global pages use a complete in-memory projection, never concatenated per-project
pages. Clients pass the returned `snapshot` on continuations. Any selected-source
addition/deletion, evidence change, profile rename/archive or authorization change
invalidates the continuation; restart at offset zero. Search/page parameters do
not alter a source revision. Project-scoped revisions cover that selected profile.
A deleted profile is unavailable; an archived profile retains history. An absent
legacy runs root is an empty collection; unreadable sources and orphan run folders
are integrity errors. No source is repaired or reset by reading.

## 8. Usage

After session authentication, request `/api/v1/jobs-page?limit=25&q=build`.
For the next slice, send `offset=25&snapshot=<returned digest>` with the same
filters. A 409 indicates that the local sources changed; reload the first slice.
Use `project_id=<immutable ID>` for the same model within a single authorized project.

## 9. Validation And Tests

`tests/test_web_jobs.py` verifies multi-project paging/search, totals, grants and
direct routes, colliding run IDs, timezone ties, source/grant mutations,
archived/missing metadata, wait evidence, forge anchors, unsafe URLs, corrupt
state/tickets/journals, secret filtering, IO failures and zero subprocess calls.
Advanced-filter/timeline tests prove matching, bounds, corruption/redaction and
attention selection. The project-summary regression treats absent legacy update
times as unknown while rejecting malformed nonempty times.
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
