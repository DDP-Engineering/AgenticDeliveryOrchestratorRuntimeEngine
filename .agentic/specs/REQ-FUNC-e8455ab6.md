<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Authorized persisted job reads

Status: active

## Interface

Add GET /api/v1/jobs-page and /api/v1/jobs/{project_id}/{run_id}.
Global page accepts optional project_id, q (trimmed casefold substring, 1..80),
status_group (active/waiting/review/terminal), lifecycle and stage exact values,
limit (1..100 or all; default 25), offset >= 0 and optional snapshot (64 hex).
Project filtering resolves the same authorized identity rules as existing routes.
The existing project run routes retain their response contracts.

Page contains items, total, counts (lifecycles), groups, limit, offset, complete=true,
snapshot (SHA256 authorized source content), snapshot_semantics=optimistic-source-revision.
Counts/groups describe the searched/project-filtered population before lifecycle/stage/group
selection; total describes matching items. Archived projects are included explicitly.
Order is last_activity_at descending as UTC instant, missing last activity last,
then project_id ascending, run_id ascending. Search covers project name/display label,
run ID, ticket number and actual title, lifecycle, stage and outcome; absent data adds no text.

## Source revision and completeness

Each request reads complete authorized profile and run source bytes into memory,
then reinspects the same paths/membership/profile inventory before returning.
A source change returns 409 job_snapshot_changed; callers restart at offset zero.
The source digest includes project metadata and state/ticket/journal presence/content
and authorization identity, independent of pagination or search. Consecutive pages pass
snapshot to reject additions, deletion, rename, archive, changed evidence or grants.
This is optimistic consistency, not a durable frozen snapshot or a transaction against
uncoordinated host writes; a mutation after final reinspection is visible next request.
No server cache or live forge fetch. Deleted projects have no retained searchable profile;
archived projects retain authorized history. Missing state roots are empty legacy sources;
unreadable roots/files and malformed run folders fail closed.

## Evidence

Exact state values remain independent; stage never implies lifecycle/outcome/action.
last_activity_at is max of valid updated_at and journal ts values; null if absent.
created_at and updated_at are optional legacy timestamps, invalid nonempty values fail.
Ticket title and web_url come from optional ticket.json; iid if present must match state.
Missing ticket/journal files are explicit coverage states, malformed ones are errors.
Wait reason/action use only lifecycle-matching persisted evidence: parked questions plus
question_comment_id and an event timestamp at/after the current parked_at; absent
legacy correlation remains unknown. Awaiting approval comment ID plus presented candidate digests;
in-review MR URL. Role is human_responder/human_approver/human_reviewer only with that
actual evidence; responsible_person remains null because no assignee snapshot exists.
Evidence locations use composite API detail URL and safe forge comment/MR anchors,
with source identifiers; GitLab uses note anchors, GitHub/Gitea issuecomment anchors,
and an unknown forge retains the observed ticket URL; never worktree paths, command outputs, descriptions, outbox bodies or validation payloads.
Unknown evidence yields null values and availability=unknown, with no invented questions.
Consumption is {availability: unknown}; metrics are a later contract.

## Trust and compatibility

Strict JSON parsing rejects duplicate keys, non-finite constants and parser depth
failures; projected strings require valid Unicode scalars. RunState.from_dict validates existing schema 1, with additional read-surface type checks.
Read raw journal JSONL strictly: malformed/torn lines fail this evidence read, while the
operational recovery reader remains unchanged. No state/journal writes, migrations, optional
schema fields or historical reset. Expose only selected fields; redact credential patterns in
free text; URLs must be absolute HTTP(S), valid host/port, without credentials, controls,
backslashes, query or fragments (except locally constructed safe comment anchors).
Failures are typed JobReadError mapped to existing run_state_corrupt/run_journal_corrupt
or new job_evidence_corrupt/job_snapshot_changed codes, with no source text in errors.
