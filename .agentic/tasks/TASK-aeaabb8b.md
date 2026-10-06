<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-aeaabb8b - Clean settings and original raw configuration

stage: deliver
type: change
path: full
interaction: autopilot
requirements: REQ-UX-34ca5d39 REQ-SEC-3cf6cde4
parent:
branch: task/adore-web-interface
base: 8d372f5573e3c23f34a2e580ae9360d3f6f0f07b
opened: 2026-10-06

## Done checklist (current stage)

- [x] Validated candidate confirmed unchanged.
- [x] Evidence, scope and outcome presented under standing authority.
- [x] Scoped commit/push/deploy authorized by human.
- [x] Journal/report included.
- [ ] Commit/push and deployed outcome verified.
- [ ] Close-out committed after outcome succeeds.

## Frame

Problem: STATED Settings contains technical export prose, duplicated instruction/source badges and a separate Configuration panel.
Desired outcome: Compact project-only Settings with Preview raw configuration / Download raw configuration.
Actors: Administrator; developers retain redacted read-only settings.
Primary scenario: Admin opens Settings -> previews original TOML in a closable dialog or downloads exact saved bytes.
Examples: Inline private TOML values remain visible; comments, order and CRLF retained in download.
Counterexamples: Anonymous/Dev must never read raw bytes; invalid files or late responses must not expose a stale preview.
In scope: Remove portable export panel from Settings, project-source badge/single-edit instruction and standalone Configuration panel; preserve candidate review/apply/discard inside Settings. Add Admin raw endpoint/actions.
Out of scope: .env and external credentials (explicit human answer), resolving environment values, portable transfer API/removing its rules, unrelated seven prior regression failures, epic work.
Constraints: Existing branch; four hours, three fix cycles, twenty authored files; no agents; scoped commit/push/deploy standing authority. Full suites deferred until the final iteration per latest human instruction.
Success signals: Clean Settings, exact unredacted TOML, no Dev actions/bytes, modal focus/close and no storage.
Evidence: OBSERVED App.tsx Settings uses PortableSettings and project-config-editor; app.py config route redacts values. STATED human selects original TOML only.
Assumptions: Raw file is the saved active config, not pending/effective defaults.
Unknowns: none.
Decision-blocking questions: resolved: TOML only, without masking.
Proposed behaviors: Two actions beside heading; raw preview modal; generic errors; candidate remains reviewable.
Path and reason: full; new public read interface and authorized secret exposure. No new dependency; security/data format/interface criteria exclude quick path.

## Requirement coverage

REQ-UX-34ca5d39: compact Settings; browser rendering/keyboard/download and denied-role coverage.
REQ-SEC-3cf6cde4: Admin GET raw bytes; HTTP happy/denied/corrupt/changed-source coverage.

## Design

App owns candidate lifecycle; SettingsList receives heading actions and review content. RawConfiguration owns memory-only fetch/preview/modal and aborts on scope unmount; exact download uses response Blob, independent of preview. Raw GET uses administrator then project authorization, reads bounded saved config bytes, validates UTF-8/TOML, checks immutable project/config snapshot, returns text/plain no-store/nosniff with fixed config.toml attachment. No secret values in audit/error text, no storage or external reads. Portable transfer API stays supported; previous Settings export UI requirement retired in favor of raw UI. No schema/dependency/migration; restore previous artifact for rollback. No architecture structure changes outside existing App/API ownership.
Expected product/doc files: app.py, test_web_config_raw.py, App.tsx, RawConfiguration.tsx, portable.spec.ts, API/frontend component docs, Web_Interface.md, CHANGELOG.md; workflow separately.
Risks: Administrator explicitly sees secrets in original TOML; only authenticated Admin endpoint renders them, browser state cleared on dismissal/unmount. Full regression has seven known failures outside this scope.
Open decisions: none.

## Log

- 2026-10-06 build red: test_admin_raw_configuration_preserves_original_bytes exit1: new public raw endpoint404 instead of200. Anchor recorded after expected red, before product edits.

- 2026-10-06 frame/specify/design: Direct GUI correction and explicit TOML-only answer resolve scope. Full path for authorized unredacted endpoint; design/test seams above. Autopilot under standing human authority, no agents; full suites after deployment.

- 2026-10-06 user ruling: do not run all tests now; full suite deferred until the final iteration. Focused proof only for this candidate.

- 2026-10-06 build/validate: Focused Python raw/config tests17 passed (7.61s); Ruff passed; production/E2E builds passed. Chromium focused10 passed plus final Romanian locale rerun1 passed: exact download/modal/focus, text escaping/late cleanup, malformed transport, denied developer, four 390px locales and preserved candidate apply/default rows. Corrected test assertions for removed badge and locale preference isolation; Romanian test text encoding corrected. No product findings remain.
- 2026-10-06 reviews: Separate same-agent specification and implementation-quality lenses both approved, round1; no subagents. Reviewed endpoint RBAC-before-read, bounded parse/read, snapshot/identity, secret-safe errors, modal memory/abort/focus, exact download and preservation of candidate lifecycle. Docs/knowledge/current context reconciled; GUI portable requirement retired by explicit replacement, transfer API retained. Inventory within twenty authored files; generated assets/workflow separate.
- DEVIATION validate: Required full suite deferred until final iteration by latest direct human instruction. Narrow proof covers current interface/security contracts, not repository-wide regression. Previous seven baseline failures remain outside scope. Strict advisory warnings for historical journals, sidecars and generated minified bundle scanning remain accepted; reviewed authored source and rebuilt bundle.
- 2026-10-06 delivery presentation: Candidate consists of API/read tests, raw dialog, App Settings layout, two browser test files, rebuilt assets and same-change operator/component/knowledge/requirement/changelog records. TOML only, no .env/external credential export; no epic/later ticket/PR/release. Standing human authority authorizes scoped commit/push/deploy without repeated permission.

## Rulings

- RULING-001 | date=2026-10-06 | decision=Implement original unredacted TOML preview/download for Admin; simplify Settings and preserve candidate review; scoped commit/push/deploy authorized, full suite after deploy | reason=Direct user request and explicit TOML-only answer plus standing delivery authority | source=user | supersedes=none


## Handoff


current: deliver
status: ready
next: Commit/push then deploy with backup and service/bundle verification
must_read: .agentic/tasks/TASK-aeaabb8b.md; .agentic/steps/6_deliver.md
blockers: none

## Stage report


stage: deliver
result: completed
current: deliver
changed: Compact Settings and Admin original TOML actions/dialog/endpoint
evidence: Python17 passed; Chromium11 passed across focused run and Romanian correction rerun; Ruff/build passed
issues: Full regression deferred by user; previous unrelated regressions remain reported
next: Commit/push/deploy and verify actual outcome
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-06)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-34ca5d39 - Compact project settings with raw actions
  - REQ-SEC-3cf6cde4 - Administrator original configuration read
- deviations: 1 recorded
  - validate: Required full suite deferred until final iteration by latest direct human instruction. Narrow proof covers current interface/security contracts, not repository-wide regression. Previous seven baseline failures remain outside scope. Strict advisory warnings for historical journals, sidecars and generated minified bundle scanning remain accepted; reviewed authored source and rebuilt bundle.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 8d372f5: 19 file(s) changed, 531 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=10 notes=25
- checklist: 4/6 done; open: Commit/push and deployed outcome verified.; Close-out committed after outcome succeeds.
