<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-f37d70bc - Respect configured statistics database and simplify GUI storage settings

stage: deliver
type: fix
path: full
interaction: autopilot
requirements: REQ-FUNC-b6a46511, REQ-UX-d8745013
parent:
branch: task/adore-web-interface
base: aec26c6d00a21ae3b4e590fb177acb676816c22b
opened: 2026-10-09

## Done checklist (current stage)

- [x] implemented configured-path and storage-presentation requirements
- [x] targeted proof and documentation complete
- [ ] final review/catalog and authorized deployment complete

## Frame

Problem: STATED approved settings review; OBSERVED both analytical views read hardcoded state-root metrics.db and paths have generic web write authority.
Desired outcome: configured database used consistently; database path informational; JSONL/HTML paths configured externally.
Actors: Admin and authorized Dev reporting readers; server operator for TOML.
Primary scenario: project/global JSON/CSV reads configured summary file; Statistics shows the localized file name without edit; exports remain CLI/TOML.
Examples: custom/stats.db contains historical jobs; wrong default database contributes no jobs.
Counterexamples: corrupt configured evidence fails closed; missing configured database remains absent and contributes no summaries.
In scope: two analytical readers, storage setting authority/visibility/copy, offline API/helper/browser tests and documentation; authorized local/DCP delivery.
Out of scope: metrics.enabled naming/default, CLI recording/export/HTML behavior, state migration and financial semantics.
Constraints: targeted proof only; preserve DCP profiles/TLS/state; no merge/push/PR.
Success signals: configured absolute/relative paths drive project/global/CSV; no fallback to default; read-only bytes; Admin/Dev authority preserved.
Evidence: STATED user implementation/deploy instruction; OBSERVED app.py _usage_view/_metric_view/_editable_setting_key and settings.ts/Copy/Help.
Assumptions: relative paths use the process working folder like CLI; legacy metadata-only profiles keep existing state-root reporting until config is supplied.
Unknowns: none blocking.
Decision-blocking questions: none.
Proposed behaviors: typed metrics error for malformed/unreadable configuration, configured file loaded through existing read-only analytical reader.
Path and reason: full because storage-settings authority is externally visible; no schema/dependency change.

## Requirement coverage

REQ-FUNC-b6a46511: configured-path API reporting and fail-closed/read-only boundaries.
REQ-UX-d8745013: informational database file and omitted external export controls.

## Design

One helper selects the summary database from the existing profile config, then delegates to metrics.load_analytical_summaries. Existing metadata-only profiles use their historical store-root database; present corrupt config never falls back. Parse failures and invalid db_path types become MetricsError, translated through existing metrics/usage 503 envelopes. Relative paths retain CLI Path semantics. Both reporting views use the helper, covering global/CSV through their existing call graph. Database/export/HTML paths have no web preparation authority; export/HTML controls are hidden and database copy is localized. No writes, migrations, new dependency or conductor changes. Preserve existing scope/role/financial checks. Alternatives rejected: continue hardcoded path or silently fall back on corruption.

## Log

- 2026-10-09 frame/specify/design: approved user scope captured; full path with small helper design; new functional and existing UX requirement govern implementation. Autonomous stages and local/DCP delivery authorized by explicit request.
- 2026-10-09 build red: .venv/Scripts/python.exe -m pytest -q tests/test_web_scoped_metrics.py tests/test_web_config.py -k "configured_statistics_database or statistics_storage_settings" --tb=short; exit=1; nine failures show configured path ignored, corrupt evidence ignored and web storage edits permitted.

- 2026-10-09 build: configured summary helper added to both existing analytical views; selected storage types/syntax and SQLite corruption fail closed. Absolute/relative custom history, decoy rejection, absent-file read-only and Admin/Dev routes prove source selection; storage candidate edits reject all three keys. Frontend retains only a localized informational database row. CLI recording, mirrors and HTML unchanged. Documentation/context/requirements reconciled.
- 2026-10-09 validation review round 1: specification compliance approved against approved three setting changes, exclusion of metrics.enabled rename and two requirements; implementation quality approved after scope/source/read-only/role/CSV diff review and explicit negative boundaries. Component architecture/call graph retained; no children, migration, dependency or product path outside scope.
- 2026-10-09 DEVIATION validate: full configured suite deferred under standing user targeted-only instruction. Substitute scoped API/config/metrics, helper and browser tests, TypeScript/build/Ruff and strict catalog without --run. Broader integration coverage remains unverified.

- 2026-10-09 final validate: all candidate checks exit=0. 104 tests across test_web_scoped_metrics.py/test_web_metrics.py/test_web_config.py passed; final configured/storage selection passed 12 (61 deselected) after formatting and added null-byte boundary. 18 settings helper tests and three browser journeys passed (four locales, Admin and Dev), TypeScript and isolated build/stamp passed, focused Ruff and diff check passed. Strict catalog without --run: 0 errors, 10 existing warnings, 25 historical notes. Existing Starlette/color/chunk advisories accepted; full suite remains deferred. No new scope findings; source-selection and external storage claims reviewed against final diff. Authorized delivery is local commit and DCP replacement.

## Rulings

- RULING-001 | date=2026-10-09 | decision=Implement approved statistics changes and deploy DCP using targeted tests only | reason=Explicit user request and standing test instruction | source=user | supersedes=none


## Handoff


current: deliver
status: ready
next: local commit and DCP deployment
must_read: .agentic/requirements/functional/REQ-FUNC-b6a46511.toml
blockers: none

## Stage report


stage: validate
result: completed
current: deliver
changed: configured statistics source and external storage settings
evidence: 104 API/config/metrics passed, 18 helpers and 3 browser journeys; typecheck/build/Ruff
issues: full suite deferred; existing dependency/build advisories
next: local commit and DCP deployment
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-09)

- stage: deliver; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-b6a46511 - Web statistics reads the configured summary database
  - REQ-UX-d8745013 - Project settings follow Git delivery flow
- deviations: 1 recorded
  - validate: full configured suite deferred under standing user targeted-only instruction. Substitute scoped API/config/metrics, helper and browser tests, TypeScript/build/Ruff and strict catalog without --run. Broader integration coverage remains unverified.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base aec26c6: 19 file(s) changed, 360 line(s) added
- checks: errors=0 warnings=11 notes=25
- checklist: 2/3 done; open: final review/catalog and authorized deployment complete
