<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Portable new-project enrollment

## Behavior

Admin selects supported UTF-8 JSON or an authorized active source profile. Only PORTABLE_FIELDS (complete 16-field polling/readiness/recovery/budgets) transfer; #9 source compatibility/parser/export remain authoritative. Source fields never seed target identity, clone, runtime, credentials, endpoints, labels, delivery, users, grants, audit, pending data, history or state. Target setup is supplied afresh through guided fields, with explicit environment/reference reconfirmation. All portable fields override target rule defaults; target budget controls display copied values read-only. State/config live beneath new profile; worktrees beneath home/worktrees/target; metrics derive beneath new state. Existing repository clone must be supplied, no clone operation occurs.

## Data / interface

All POST routes require Admin + CSRF. `transfer-source` takes `{method: "file"|"project", file_text?: string, source_id?: string}` with exactly one selected input. File bounded 64KiB and retained exact UTF-8 bytes. Project source_id is immutable 32-hex; active bytes bounded 512KiB are exported strictly. Result `{source_revision, settings}`; source_revision SHA-256 binds exact file bytes or source project ID + exact config digest, never portable checksum alone. Project rechecks authoritative current role/session and source identity/access. No writes/probes.

`transfer-preview` adds `{target: ProjectInput, source_revision, references_confirmed: bool}`. Builds target via existing `_prepare_project`, projects all portable rules into TOML using generated complete allowlisted TOML tables, validates config again, checks allocated paths and existing profile ownership. Returns existing preview shape plus source_revision, mapping `[ {key, source_value, server_value, effect} ]`, review including metrics paths. Revision binds source and target document/identity/display/description; confirmation flag mandatory for structurally valid preview. Mapping effect is `copy-rule`; allocated paths and excluded fields are separately explained.

`transfer-check`/`transfer-create` add `revision` (64-hex). Rebuild exact candidate and reject changed source/candidate; check explicitly uses existing bounded ephemeral probes and rereads source afterwards. Create acquires source config lock when copying; existing home enrollment/conductor lock guards publication. Fresh authorization/source/target ownership is rechecked before writes and visibility; source mutation fails closed. Failure rolls back newly allocated profile; replay/double confirmation rejects occupied identity without replacing it. No existing history is adopted. Verification remains independent and does not automatically activate pickup.

## Errors and boundaries

`portable_settings_invalid`/`portable_settings_incompatible` 400 for file parsing/export format; unreadable source 503; missing identity 404; `portable_settings_changed` 409 for any exact source/candidate mismatch with explicit re-review. `project_import_conflict` 409 for occupied/overlapping/ambiguous state/worktree/metrics/repository ownership; unreadable/corrupt existing profile/config fails closed 503. Invalid target/references return `project_setup_invalid` with safe findings. Existing auth/CSRF/project/rollback errors retain stable code. No exception echoes source content/secrets.

## Acceptance

Public API tests compare all settings for both methods, independent IDs/paths, stopped pickup and omitted data, unchanged source, exact source/file byte binding, missing/replaced/corrupt/unknown/version/duplicates/secrets, source permissions/session/CSRF, invalid reference/clone, target collisions, injected rollback and replay. Browser tests cover visible source/mapping/exclusions, target steps/reconfirmation, review/back/change, conflict/re-review, double submit, Dev denial, malformed/late transport and memory scope, four locales, keyboard/390px themes. Existing exact TOML byte-copy regression remains required.
