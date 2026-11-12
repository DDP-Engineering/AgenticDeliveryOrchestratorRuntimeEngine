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

The contract below is implemented and covered by focused offline API,
frontend reader/render and enrollment/settings browser tests in TASK-988d986a
build. The other sections retain their existing scope; final strict validation
remains outstanding.

The /readiness-check response carries context/checks/checked_at plus revision,
project_id, status, required_checks, auth_bound and a separate workflow enum.
Workflow is exactly `aegis`, `direct` or `not-inspected`: read-only inspection of
an available clone identifies AEGIS from `.agentic/aegis.py` alone; its absence
identifies Direct. An unavailable or not-yet-created clone stays not-inspected.
This is an observation, never a workflow setting or executable/version approval.
The explicit pre-pick live probe retains runtime authority. No repository code
runs and no files are added or changed for workflow identification.

Persist only schema-3 readiness.json separately from runtime state, using atomic
unique-temp replacement. Its exact keys are schema, project_id, revision,
checked_at, context, checks, host, binding, auth_bound and workflow. Bind immutable
profile identity, exact configuration SHA-256, UTC check time, private host and
configuration/authentication context fingerprints. Required base checks are git,
forge_cli, forge_auth, container_runtime and executor_cli; each is boolean except
container_runtime may be null when unverified. Configuration requires boolean
executor_sign_in for ChatGPT, egress_proxy for container allowlist-proxy operation
and web_search_key when the selected search provider requires it. No aegis_files
key belongs to checks or required_checks. Only these configured keys are allowed.

Workflow never changes the verdict: a false prerequisite yields failed; otherwise
unbound authentication or an unverified runtime yields partial; otherwise verified.
Missing/unknown/nontext workflow or malformed live check output returns typed
503 readiness_probe_failed before evidence publication. Capture the configuration
snapshot before probes; afterward re-read identity/config/host/auth binding under
the config edit lock and reject drift with stale_config_revision. Preserve saved
evidence on rejection. Server-issued draft tokens retain workflow and measured
checks unchanged through creation; not-inspected is not promoted after cloning.
A later explicit host check can establish the created repository's workflow.

Project reads add validation={structural_valid,issues},
pickup_state=stopped|active|archived and verification={status,revision,checked_at,...}.
Absence yields the unverified object with null revision/time and no workflow claim;
a changed revision or host/authentication binding yields stale. Invalid configuration
is separately structural_valid=false, not fabricated verification failure. Validate
stored schema/identity/exact keys/check and workflow types/revision/time before
rendering even stale evidence. Any other schema or corruption yields the existing
typed readiness_corrupt detail naming the affected profile's readiness.json to
delete before a fresh check; never migrate, repair, rewrite or delete it
implicitly. No age-based expiration is inferred for persisted evidence. Display-only
edits do not stale it; WSL runtime may remain unverified; model access is proved
only by the separate Test AI connection. Browser readers validate the same closed
workflow/check domain and verdict agreement before displaying evidence.

## Verification and ownership

All external commands are fake. Tests observe public stores/API/worker contracts, deterministic races, rollback and secret/permission boundaries. Current issue #5 frontend/assets/tests/journal stay unchanged. Shared docs preserve initial content via separately recorded appended contract sections; record issue #6 patch and exact inventory before delivery. Final production build must use isolated output or verify identical existing asset hashes; no issue #5 byte overwrite. Runtime schema stays 1, no release bump or new dependency.

## Error envelope compatibility

Existing localized detail.code values remain the HTTP categories. Structured detail.issues carries precise backend code/field/remediation (reserved_project_name, invalid_display_name, project_creation_failed, project_rollback_failed, readiness_corrupt). ID syntax/reservation maps to invalid_project_name; display input maps to invalid_request; enrollment storage maps to project_setup_invalid; readiness evidence/storage maps to readiness_probe_failed; state-root conflicts map to project_import_conflict. This preserves the established frontend catalog without changing frontend source or generated assets. Setup-related schema failures add issues; other error envelopes retain their previous shape. UTC timestamps more than five seconds in the future are corrupt evidence. Explicit null display input is invalid; omission alone uses fallback.
