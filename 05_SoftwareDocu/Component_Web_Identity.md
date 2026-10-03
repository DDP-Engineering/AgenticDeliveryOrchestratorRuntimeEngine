<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web identity and command store

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
second busy timeout. Schema 13 adds `users.password_change_required`: an
administrator reset sets it, a successful own password change clears it, and
the bootstrap `admin` plus accounts upgraded from earlier schemas start
unmarked. A schema-13 store without the column fails closed.
Schema 12 adds an audit-policy singleton; upgrades leave
existing users and audit rows intact. Its two nullable bounds default to
unlimited and pruning runs transactionally on policy changes, audit writes and
audit reads. Events older than the day bound or beyond the stored UTF-8 text
byte bound are deleted oldest first. The byte bound does not cap SQLite file
allocation. Corrupt policy values or timestamps fail closed. Schema 9 binds
price versions to immutable profile IDs.
Schema 10 adds a numeric usage projection keyed by immutable project ID, run ID
and journal source ID. Schema 11 adds launch-coverage projection rows and a
per-run journal cursor with source length and SHA-256 digest. `reconcile_usage`
validates and inserts source events transactionally; exact replay is idempotent,
changed, truncated or vanished source evidence fails closed, and attributed
usage is read back from SQLite. An
administrator can rebuild it from retained journals without changing run state.
Legacy price rows are retained but not used when their creation predates the
current profile's creation; the administrator must reconcile those rates.
Renames retain bound rates, and replacement profiles cannot inherit them.
Schema 8 binds queued commands to immutable profile IDs;
upgrading name-only pending/running commands marks them `uncertain` for operator
reconciliation. Schema 7 binds developer grants to immutable profile IDs and
migrates only rows whose stored name and creation stamp still match a profile.
Renames retain those grants; deleted or replaced profiles cannot inherit them.
Schema 6 stores optional language and theme preferences
per account; upgrading from schema 5 preserves accounts and prior data.
Schema 5 stores the single control worker heartbeat;
upgrading from schema 4 keeps users, sessions, grants and prices. Schema 4 stamps each developer grant with the profile's
creation time, so replacing a profile under the same name does not inherit its
grants. Upgrading from schemas 1-3 clears name-only grants; administrators must
reassign them. Accounts and prices are retained. Schema 3 added immutable dated
price rows, and schema 2 added login-failure windows.
An interrupted `running` operation becomes `uncertain` on worker startup and
is never automatically replayed.
The archive guard queries queued and running operations for a project before
profile metadata changes; database errors fail closed. The worker separately
rechecks archived state when it claims a pending command.
Pending cancellations can be listed for one or every project. The worker's
watcher sees them during any blocking command or poll, and they are claimed
ahead of other pending commands after that command returns. The watcher
does not change operation status; the normal worker claim reconciles the result.

## 4. Dependencies

Python SQLite and `argon2-cffi` are required by the optional `web` extra.

## 5. Inputs And Outputs

The inputs are credentials, user/project grants, session tokens and command
metadata. The database, marker and audit rows are durable outputs. The session
cookie contains an opaque random value; only its SHA-256 digest is stored.
`recent_audit(limit)` returns up to 500 newest audit rows with actor names, or
all rows when `limit=None`; the API exposes the latter for the All table choice.
`audit_policy` and `set_audit_policy` read and change administrator audit
retention limits.
`add_price` and `list_prices` store immutable-project/executor/model rate
versions as bounded decimal strings with an effective date and actor.
`touch_worker`, `clear_worker`, and `worker_ready` maintain readiness. A
missing or old heartbeat is unavailable; malformed persisted timestamps raise
`WebStoreError` rather than claiming readiness.
`preferences` returns nullable language/theme values for browser fallback;
`set_preferences` validates and updates supplied fields atomically. Unsupported
or corrupt persisted values fail closed.

## 6. Data Contracts

Roles are `admin` and `developer`. Operations are `start`, `retry`, `cancel`
with `pending`, `running`, `succeeded`, `failed`, or `uncertain` status.
`(actor_id, idempotency_key)` is unique. Login failures are keyed by hashed
username/client identity and windowed to five in ten minutes.

## 7. Workflow Integration

The API creates and reads sessions, accounts, memberships and operations. The
worker claims an operation, resolves its immutable project ID to the current
profile name, and rechecks actor authorization and profile identity before
invoking the CLI. With API and worker stopped, backups must include `web.db` and
`web.db.initialized` together with profiles and all project state roots.

## 9. Validation And Tests

`tests/test_web_auth.py` covers bootstrap, hashing, restart, corruption,
deletion, rate limit, password reset, session revocation, disablement, and
manual stopped-service restore of the default home.

## 10. Limitations And Future Work

This is a single-host store. There is no email password recovery or
multi-host dispatch. The account lockout key uses the direct client address;
a reverse proxy should preserve a stable trusted address policy.
