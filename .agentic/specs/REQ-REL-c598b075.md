<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Backend identity, paused enrollment and readiness contracts

Status: active. Scope: backend contracts only, without enrollment UI.

## Identity

`name` retains the existing directory/profile ID; `id` retains project_id (32 lowercase hex). `display_name` is optional on enrollment and falls back to name when omitted. A profile.json without the display_name key, or with any other missing or unknown key, was written by another ADORE build and is refused; persisted explicit empty/non-string is corruption. Explicit display input must contain 1-120 Unicode characters, be trimmed, and contain no control, surrogate or Unicode format characters. The admin CSRF-protected PUT /api/v1/projects/{identity}/identity accepts only display_name. It reloads under the shared config edit lock and saves metadata only. No directory rename or grant/operation rewrite occurs.

Web profile IDs keep [a-z0-9][a-z0-9._-]{0,63}. Reject trailing dot, Windows device stems (con/prn/aux/nul/com1-9/lpt1-9), endpoint names import/import-preview/setup-preview/id-availability and 32-hex names ambiguous with project IDs. Case-fold filesystem collisions, incomplete existing directories and corrupt metadata block availability. POST /api/v1/projects/id-availability requires admin+CSRF and accepts only name; valid input returns name/available/issues, malformed/reserved input a typed 400. Creation checks again under a cross-process enrollment lock. Existing CLI rename and setup semantics remain intact.

## Setup

POST /api/v1/projects/setup-preview shares ProjectInput with POST /projects, accepts only known non-secret fields plus optional display_name/login, and requires admin+CSRF. It returns structural_valid, issues, name, display_name, pickup=stopped-on-create and verification.status=unverified. No profile writes or external command calls. A wizard prepare-only route assembles the same validated config using explicit/default answers and zero probes. Empty optional model/image use the shared wizard defaults. Wizard findings use stable setup_field_invalid with field key and a value-free remediation; assembled-config errors use config_invalid/config. Exact TOML preview retains existing issues for compatibility and adds validation with structured findings. Safe findings use code/field/remediation, never raw values.

Unknown JSON fields fail schema validation. Embedded TOML secret values fail before validation details reach the caller. Supported environment references are {env:UPPER_CASE_NAME} in provider JSON, environment key-name lists and auth_env variable names. Credential-looking scalar runtime_env values are rejected; provider JSON apiKey accepts only the supported environment reference. Secret-valued provider apiKey and URL userinfo/query secrets fail; provider runtime JSON is parsed and structurally inspected, never echoed. Existing config/status responses remain compatible with additive fields.

## Paused publication and failures

A home-scoped cross-process config_edit_lock serializes web enrollment. Check ID and state ownership again within it; create the target directory exclusively. Guided creation uses its dedicated final state root. Imports retain exact bytes/absolute external state root and completed history. Hold the target conductor lock; check active/corrupt runs and unfinished work as applicable. Write config, pause state, publish metadata last, audit and construct the response before releasing lock. Discovery requires profile.json, so no worker can discover an unpaused intermediate profile. A worker finding metadata still cannot acquire the conductor lock during publication/rollback.

On error remove published metadata before releasing the conductor lock, remove only the owned newly created directory and restore an imported state's previously unpaused marker. Never remove existing imported history. Incomplete crash artifacts fail closed at ID availability; no silent repair/migration. All operational failures return typed project_creation_failed or existing explicit conflict; callers never see secret-bearing exception text. Failure of rollback is a typed escalation with paused state retained rather than a runnable orphan. Existing running projects and CLI enrollment semantics stay unchanged. Pickup resume is the existing explicit authorized queued operation; pause does not interrupt active jobs.

## Readiness

Keep /readiness-check response context/checks/model_probe/checked_at and add revision, project_id and status. SHA-256 hashes exact config bytes. Persist schema-1 readiness.json separately from runtime state, using atomic unique-temp replacement; bind to profile project_id. Store only bounded known booleans/redacted endpoint result. Capture config snapshot before probes; after probing, re-read identity/config under config edit lock and reject changed revision/identity with stale_config_revision. Preserve older evidence on rejected probe; it appears stale after the config changes.

Project reads add validation={structural_valid,issues}, pickup_state=stopped|active|archived and verification={status,revision,checked_at,...}. Absence yields unverified; a changed config revision yields stale; matching evidence is verified when required checks passed, otherwise failed or partial for explicitly unverified checks. No age-based expiration is inferred; time is evidence for the operator. Invalid configuration is separately validation.structural_valid=false and does not convert stale/unverified into invalid. Corrupt schema/identity/check types/revision/time/model evidence raises typed readiness_corrupt. Display-only edit does not stale configuration evidence. WSL and unsupported model checks keep explicitly unverified evidence.

## Verification and ownership

All external commands are fake. Tests observe public stores/API/worker contracts, deterministic races, rollback and secret/permission boundaries. Current issue #5 frontend/assets/tests/journal stay unchanged. Shared docs preserve initial content via separately recorded appended contract sections; record issue #6 patch and exact inventory before delivery. Final production build must use isolated output or verify identical existing asset hashes; no issue #5 byte overwrite. Runtime schema stays 1, no release bump or new dependency.

## Error envelope compatibility

Existing localized detail.code values remain the HTTP categories. Structured detail.issues carries precise backend code/field/remediation (reserved_project_name, invalid_display_name, project_creation_failed, project_rollback_failed, readiness_corrupt). ID syntax/reservation maps to invalid_project_name; display input maps to invalid_request; enrollment storage maps to project_setup_invalid; readiness evidence/storage maps to readiness_probe_failed; state-root conflicts map to project_import_conflict. This preserves the established frontend catalog without changing frontend source or generated assets. Setup-related schema failures add issues; other error envelopes retain their previous shape. Unknown model-probe reasons and UTC timestamps more than five seconds in the future are corrupt evidence. Explicit null display input is invalid; omission alone uses fallback.
