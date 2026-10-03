<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-SEC-676d284c — Require a new password after an administrator reset

## Behavior

- An administrator password reset stores the new password hash, marks the
  target account as requiring a password change, and revokes the target's
  sessions. Resetting one's own account through the administrator endpoint
  marks one's own account the same way.
- A successful own password change stores the new hash, clears the mark and
  revokes the account's sessions. A rejected change (wrong current password or
  a replacement shorter than 8 characters) leaves the mark set.
- Sign-in with a marked account succeeds and returns the account with the mark,
  so the interface can request the change.
- While the session's account is marked, authenticated routes return 403
  `password_change_required`, except:
  `GET /api/v1/me`, `GET /api/v1/me/preferences`,
  `PATCH /api/v1/me/preferences`, `POST /api/v1/me/password`,
  `DELETE /api/v1/session`.
- Check order for a protected route: missing/expired session -> 401
  `authentication_required`; marked account -> 403
  `password_change_required`; missing CSRF on a mutation -> 403
  `csrf_required`; non-administrator on an admin route -> 403
  `admin_required`.
- The bootstrap `admin` account of a fresh store is created unmarked, and
  accounts that exist when a store upgrades to schema 13 start unmarked.
- Unauthenticated routes (`/health`, `/ready`, `/about`, `POST /session`) are
  unaffected.

## Data / interface

- SQLite `users` gains `password_change_required INTEGER NOT NULL DEFAULT 0`.
- `PRAGMA user_version` becomes 13. A fresh store is created at 13. Stores at
  versions 1-12 upgrade forward by adding the column with default 0. A store
  at version 13 whose `users` table lacks the column raises `WebStoreError`
  ("web database missing password policy"), which the API reports as 503
  `web_store_corrupt`. Versions above 13 remain unsupported.
- Account dictionaries returned by the store and API (`POST /session`,
  `GET /me`, `GET /users`) include `password_change_required: bool`.

## Examples

- Admin resets developer `dev` to `Recovery-123`; `dev` signs in ->
  `{"user": {..., "password_change_required": true}, "csrf": ...}`;
  `GET /api/v1/projects` -> 403 `{"detail": {"code": "password_change_required"}}`;
  `GET /api/v1/me` -> 200.
- `dev` posts `{"current": "wrong", "replacement": "Newpass-123"}` -> 400
  `current_password_incorrect`; still marked.
- `dev` posts the right current password -> 200; session revoked; next sign-in
  returns `password_change_required: false` and `GET /api/v1/projects` -> 200.
- Fresh store: `admin`/`admin` sign-in -> `password_change_required: false`.

## Acceptance

- Store tests: fresh store version 13 with unmarked admin; schema-12 store
  upgrades to 13 with unmarked accounts; reset marks; successful change clears;
  failed change keeps; mark persists after reopening the store; version-13
  store without the column fails closed.
- API tests: gating and allowlist above, check order 401 before 403, CSRF still
  required on allowlisted mutations.

## Assumptions and open decisions

- The bootstrap `admin`/`admin` credential is intentionally not marked during
  the development phase (task ruling); hardening it is separate future work.
