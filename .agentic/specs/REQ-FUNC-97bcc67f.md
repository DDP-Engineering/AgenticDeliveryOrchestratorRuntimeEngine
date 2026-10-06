<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Reviewed user access contract

## Authority and evidence

STATED: Issue #18 and standing authority define the scope. OBSERVED: existing
roles are admin/developer, SQLite schema 13 and profile immutable IDs; Admin
already has global role-based access. INFERRED: additive endpoint preserves
existing clients. UNKNOWN: live human acceptance; not claimed by this proof.

## Atomic operation

Admin/CSRF POST /api/v1/users/with-access takes username, password, explicit
role, project_ids (distinct 32 lowercase hexadecimal IDs), allow_no_projects
(boolean, false by default). All fields except acknowledgement are required;
extra fields and coercion are rejected. Dev zero grants requires acknowledgement;
Admin requires zero explicit grants and receives global/system access by role.
Returns existing public account fields plus project_ids; never password/hash.
GET /users adds project_ids alongside compatible name-based projects.

The store validates input, captures current visible project identities, obtains
BEGIN IMMEDIATE, inserts user and memberships, then rechecks selected project
identity/creation/name/archive state before commit. Any error rolls back both.
Stable ID/creation binding prevents later deletion/replacement from inheriting
access. Concurrent archive within this API app is serialized by config_lock;
external profile changes detected before commit abort; a change after commit
is a subsequent lifecycle event and retains existing identity-based filtering.
No claim of a distributed filesystem/SQLite transaction is made.

Failures use value-free typed WebStoreError/HTTP errors. No success audit is
emitted when creation fails. Existing /users and name-based assignments retain
compatibility. Argon2id hashing, session/reset, role/CSRF and last-admin safeguards
remain authoritative. Password exists only in transient credential memory/input
and outgoing create request; review renders no password value or hash.

## Browser interaction

Identity -> access -> review, with focus on each stage heading and retained
memory-only corrections. Review freezes username/role/ID selection. Selected
projects show human display plus immutable ID. Admin shows all-project/system
and money/administration access; Dev is limited to selected projects with no
money/admin access. Zero-project Dev needs an explicit checkbox. One ref-guarded
submission; success clears credentials and refreshes accounts. Unmount clears
the draft and ignores old async results. Failed responses preserve correction.

Account assignment and per-project access edits display before/after and result.
Compatibility assignment API remains name-based; UI maps known stable IDs to
current names only at that existing boundary. New creation always sends IDs.
No invitation/email/audit-history redesign or later-ticket behavior is added.

## Verification

Public API/store transaction and rollback tests; existing authentication, RBAC,
CSRF, disabled, last-admin and reset suite; browser Admin/Dev/zero/correction/
error/double-submit/grant edit cases. Full offline strict proof and production
build. Human live/novice/full-WCAG/infrastructure acceptance remain outside scope.
