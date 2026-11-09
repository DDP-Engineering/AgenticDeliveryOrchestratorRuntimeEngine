<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web identity and command store

The new identity store announces its factory administrator credentials on creation. The authenticated factory administrator’s password status is derived by verifying the public initial password against the current hash, with no new stored field. Missing or corrupt credential evidence fails closed. Password changes and resets retain session revocation.

## 1. Purpose

`adore.web.store.WebStore` owns local web accounts, sessions, project grants,
audit events, and the durable operation queue. It is separate from ADORE's run
state and uses one SQLite database in `ADORE_HOME/web.db`.

## 2. Responsibilities

It bootstraps `admin` / `admin` exactly once, stores Argon2id password hashes,
checks and revokes opaque sessions, supports administrator password reset that
requires the account to choose a new password before further use,
protects the last active admin, limits
failed logins, and claims queued commands transactionally. A sidecar marker
prevents recreating the default login after the identity database is deleted.
The store does not authorize project operations by itself; the API and worker
both check current membership.

## 3. Implementation Overview

Each method opens a short-lived SQLite connection with foreign keys and a ten
second busy timeout. The store has one schema (`_SCHEMA_VERSION`, 16): a new
file gets it, and a database in any other version is refused with a message
naming `web.db` and `web.db.initialized` to delete. There are no migrations
while ADORE is in development (AGENTS.md "Stored data during development").
Audit rows carry schema-1 structured evidence, opaque unique event
correlations and an `audit_attempts` receipt ledger; an audit row without
structured evidence is corrupt. Unknown or damaged audit schemas, missing columns/uniqueness, invalid dates,
ambiguous JSON and nonredacted persisted values raise `WebStoreError` on open
and audit reads/writes. Runtime run-state schemas retain their separate contract.

`adore.web.audit` owns the closed evidence schema and recursive value projection.
Account/access/config/project/operation/policy resources record actor ID plus
known snapshotted name, UTC recording time, known immutable project/resource IDs,
phase/result, opaque correlation, operation ID and known SHA-256 revisions.
Known `before`/`after` values include public account grants/flags, scalar numeric
or boolean settings, pickup result and project existence. Arbitrary string or
compound settings are redacted; credentials, environment values, raw exceptions
and caller idempotency strings are excluded. Recognized compact detail is kept;
arbitrary detail is projected as `[redacted]`.

SQLite account creation, compatible account mutations, project access, password
replacement, queue submission/completion/recovery and retention mutation record
their evidence in the same owning transaction. Precondition rejection creates
no successful event. A command submission is `prepare/prepared`; claimed work
finishes as `apply/applied`, `apply/rejected` or `apply/uncertain`. Completion
replay of the same terminal status creates no additional event; conflicting
terminal status rejects. Malformed command exit values become uncertain.

Filesystem-owned configuration/enrollment publishes a durable `uncertain`
attempt before changing files, then confirms only after the owning mutation.
Failure/crash leaves `after` unrecorded. Reviewed config replay identifies the
same server project/staging-time/candidate receipt, preserves original `before`
and confirms once before pending-file removal. Enrollment rolls back its visible
profile on failure, retaining uncertain evidence rather than claiming application.
Confirmation records its current UTC time. Completed receipts discard value
payloads and retain only deduplication metadata. Unresolved receipts preserve
redacted attempted evidence for host reconciliation. Receipts and durable
operations are separate from visible audit retention; deleting visible events
never permits completion duplication or prevents a valid operation from finishing.

Every audit write carries structured evidence. A stored row without it is
corrupt: opening the store and audit reads raise `WebStoreError` rather than
projecting unknowns.

`users.password_change_required` is set by an administrator reset and cleared
by a successful own password change; the bootstrap `admin` starts unmarked.
An audit-policy singleton holds two nullable bounds that default to
unlimited; pruning runs transactionally on policy changes, audit writes and
audit reads. The byte sum includes structured JSON and correlation text.
The policy PUT reports the number of deleted visible events. Events older than the day bound or beyond the stored UTF-8 text
byte bound are deleted oldest first. The byte bound does not cap SQLite file
allocation. Corrupt policy values or timestamps fail closed. Price versions are
bound to immutable profile IDs.
A numeric usage projection is keyed by immutable project ID, run ID and journal
source ID, with launch-coverage projection rows and a per-run journal cursor
holding source length and SHA-256 digest. `reconcile_usage`
validates and inserts source events transactionally; exact replay is idempotent,
changed, truncated or vanished source evidence fails closed, and attributed
usage is read back from SQLite. An
administrator can rebuild it from retained journals without changing run state.
Projection source IDs are the usage events' versioned `event_id` values.
Renames retain bound rates, and replacement profiles cannot inherit them.
Queued commands are bound to immutable profile IDs. Developer grants are bound
to immutable profile IDs and stamped with the profile's creation time, so a
profile replaced under the same name does not inherit them; renames retain
them. Each account stores optional language, theme and ticket body mode preferences, the single
control worker records a heartbeat, prices are immutable dated rows and login
failures are counted in windows. A finished operation keeps a stable refusal
`reason` and a bounded, redacted `detail` of the engine's last output lines.
An interrupted `running` operation becomes `uncertain` on worker startup and
is never automatically replayed.
The archive guard queries queued and running operations for a project before
profile metadata changes; database errors fail closed. The worker separately
rechecks archived state when it claims a pending command.
Pending cancellations can be listed for one or every project. The worker's
watcher sees them during any blocking command or poll, and they are claimed
ahead of other pending commands after that command returns. The watcher
does not change operation status; the normal worker claim reconciles the result.


### Reviewed account creation

`create_user_with_access(username, password, role, project_ids,
allow_no_projects, actor_id)` validates explicit Admin/Dev intent and current
project IDs, then uses `BEGIN IMMEDIATE` for the active-Admin check, Argon2id
account, complete grant set and existing `user-created` audit event. Final
selected ID/name/creation/archive reinspection precedes commit. Invalid input,
duplicate name, stale/deleted/replaced project, audit or storage failure rolls
back the account and every grant. Success returns public account fields and
sorted immutable `project_ids`; `membership_ids` reads live ID-bound grants.
Admin receives global access by role with no explicit membership rows. Dev
zero-project creation requires `allow_no_projects=true`. Existing `create_user`
and name-based assignment methods retain their supported contracts.

Profile metadata remains filesystem-owned. API-thread archive changes serialize
with creation; external lifecycle changes are detected at final reinspection.
A change after commit is a subsequent lifecycle event: identity/creation-bound
grants cannot transfer to a replacement. This single-host operation uses no
new database schema or distributed filesystem transaction. Public tests in
`tests/test_web_user_creation.py` verify exact recipient access, input negatives,
hash-time and post-write lifecycle races, transactional faults, durable rename/
replacement binding, role/CSRF/disabled denial and existing API compatibility.

## 4. Dependencies

Python SQLite and `argon2-cffi` are required by the optional `web` extra.

## 5. Inputs And Outputs

The inputs are credentials, user/project grants, session tokens and command
metadata. The database, marker and audit rows are durable outputs. The session
cookie contains an opaque random value; only its SHA-256 digest is stored.
`recent_audit(limit)` returns up to 500 newest projected rows, or all rows when
`limit=None`. `audit_page` selects actor ID, immutable project ID, exact action
and half-open UTC instants before its count/LIMIT/OFFSET in one SQLite snapshot.
Actor IDs and offsets reject values outside the SQLite signed 64-bit domain.
Persisted audit project names use the same safe grammar as new writes; an empty
name denotes global scope. Corrupt names raise a redacted
`WebStoreError` on initialization and public reads rather than exposing URLs.
The API constrains Dev selection to one granted project and project-safe actions.
`audit`, `begin_change` and `confirm_change` own committed and filesystem-attempt
evidence; browser-local drafts do not create server mutations.
`audit_policy` and `set_audit_policy` read and change administrator audit
retention limits.
`add_price` and `list_prices` store immutable-project/executor/model rate
versions as bounded decimal strings with an effective date and actor.
`touch_worker`, `clear_worker`, and `worker_ready` maintain readiness. A
missing or old heartbeat is unavailable; malformed persisted timestamps raise
`WebStoreError` rather than claiming readiness.
`preferences` returns nullable `language`, `theme` and `ticket_body_mode` values.
Ticket body mode is `rendered` or `source`, with null meaning no saved selection.
`set_preferences` validates supplied fields and updates them atomically, preserving
omitted preferences. Explicit null is not a valid write value. Reads and partial
writes validate all saved preferences first; a corrupt mode raises `WebStoreError`
without repair, even when the caller supplies a valid replacement. Values are
account-scoped and survive reopening the store.

## 6. Data Contracts

Roles are `admin` and `developer`. Operations are `start`, `retry`, `cancel`,
`pause`, `resume` and `delete` with `pending`, `running`, `succeeded`, `failed`,
or `uncertain` status. Every operation carries an immutable project ID; one
without it is corrupt.
`(actor_id, idempotency_key)` is unique. Login failures are keyed by hashed
username/client identity and windowed to five in ten minutes.

## 7. Workflow Integration

The API creates and reads sessions, accounts, memberships and operations. The
worker claims an operation, resolves its immutable project ID to the current
profile name, and rechecks actor authorization and profile identity before
invoking the CLI. With API and worker stopped, backups must include `web.db` and
`web.db.initialized` together with profiles and all project state roots.

## 9. Validation And Tests

`tests/test_web_audit_evidence.py` covers structured account/access/config/import/
clone/pickup evidence, nested secrets, transactional faults, filesystem crash/
replay, corrupt schema/JSON, authorized filters/counts/pages,
periods, administrative exclusions and retention/receipt separation.
`tests/test_web_auth.py` covers bootstrap, hashing, restart, corruption,
deletion, rate limit, password reset, session revocation, disablement, and
manual stopped-service restore of the default home. Ticket mode tests cover
absent/valid account round trips, partial-update preservation, invalid writes,
unchanged corrupt rows and schema/column refusal without rewriting the database.
`tests/test_web_rbac.py` proves the same API boundaries with session/CSRF checks
and isolated accounts.

## 10. Limitations And Future Work

This is a single-host store. There is no email password recovery or
multi-host dispatch. The account lockout key uses the direct client address;
a reverse proxy should preserve a stable trusted address policy.

## Deleted-job usage projection boundary

`forget_run_usage(project_id, run_id, remove_source=...)` acquires the SQLite write transaction, removes only the caller-verified job source, clears that composite identity's usage/observation/cursor rows and commits. Source removal failure rolls back the projection reset. Production `reconcile_usage` calls validate their captured journal against the current source prefix under the same transaction, permitting append progress while refusing stale deleted/replaced evidence. This keeps deterministic-ID fresh admissions independent of prior usage without a schema change. Proof: tests/test_drift_recovery.py interleaving, rollback and real-admission integration cases.


Change history imports local CLI deletion receipts with a transactional attached SQLite ledger. Import validates schema, identities, state and durable journal modes, binds updates to the original event, and keeps an opaque completion receipt after importing applied evidence. Interrupted cleanup remains uncertain. Audit retention applies to the imported event.
