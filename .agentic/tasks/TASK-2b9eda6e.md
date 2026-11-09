<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-2b9eda6e - Show default vs project-set and editable settings in Configuration

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-FUNC-49b766fe, REQ-UX-9a625fc5, REQ-UX-a62e69a9
parent:
branch: task/adore-web-interface
base: b117025e66eb6782b43c5017d0374d12caaaa774
opened: 2026-10-04

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: Project details > Configuration lists about 101 effective settings
  in 17 sections with no sign of which ones the project's config.toml sets and
  which are ADORE defaults, which an administrator can change in the browser,
  and which need a restart; editing happens in separate forms (a guided form
  for 10 common settings and an advanced key/value form), not on the setting.
  The user read the list as "settings I could not set when creating the
  project" and asked whether they are global.
Desired outcome: each setting shows whether it is set for this project or a
  default, whether it can be edited in the browser (and whether a change needs
  a restart), and administrators edit a setting on its own row.
Actors: administrator (edits); project-scoped developer (reads only).
Primary scenario: administrator opens a project's Configuration -> each row
  shows its value with "Set for this project" or "Default", and editable rows
  an Edit control -> the administrator edits `budgets.max_iterations` on its
  row -> the change is staged as today and applied with the existing pending
  flow -> the row then shows "Set for this project".
Examples: a project created in the web UI shows `platform.repo` as set and
  `budgets.max_iterations` = 20 as a default; `container.egress.allowlist`
  (a list) shows as not editable in the browser; `container.runtime` shows
  that applying a change needs a restart; a developer sees the badges but no
  Edit control.
Counterexamples: secret-like keys stay hidden/redacted and not editable;
  executor `command` entries, `state.*` and `clarification.*` stay not
  editable; lists and tables stay not editable in the browser.
In scope: config view API metadata per setting (source, editable, restart,
  edit key), the Configuration settings list (badges, inline edit, a filter
  for project-set settings), localized texts, tests, docs.
Out of scope: making lists/tables editable, Add project changes, templates,
  global settings, changing which keys are editable or how edits are
  validated, staged and applied.
Constraints: one source of truth for the editability rule (today inline in
  `config_update` and `_candidate_config_edit` in
  `04_Software/adore/web/app.py`); existing pending/apply flow, revision checks,
  CLI/web lock and RBAC unchanged; four locales; responsive layout.
Success signals: API tests show source/editable/restart per key, including the
  executor command mapping and a list value; browser check shows badges, the
  filter, inline staging for admins and none for developers.
Evidence:
  - STATED: "these are not settable - why are not when i create a new project?
    Are not per project - are globally?"; user chose "Default vs set,
    editable" from the offered improvements.
  - OBSERVED: `04_Software/adore/web/app.py` `config_view` returns
    `config.to_dict()` redacted (effective values only) plus revision/issues;
    `config_update` and `_candidate_config_edit` allow only keys whose first
    part is in 15 sections, not secret-like, not `.command`;
    `_restart_required` marks agent/platform/worktree/container/executor;
    `adore/cli.py` `_set_toml_scalar` edits scalars only.
  - OBSERVED: `04_Software/web/src/App.tsx` `ProjectConfigReadOnly` flattens
    the effective config into collapsible sections with a type label;
    `GuidedConfigForm` covers `commonSettings` (10 keys); an Advanced
    key/value form stages any key; one pending change at a time.
  - OBSERVED: effective keys equal TOML keys except executor commands
    (`executor.commands.<name>.<field>` vs `executor.<name>.<field>`).
  - OBSERVED: the web Add project form and `adore init` write only answers
    and non-default values (`adore/wizard.py`); all project settings live in
    the profile's config.toml.
  - INFERRED: "set for this project" = the key exists in the project's TOML
    file (after the executor mapping), whatever its value.
Assumptions: a value written explicitly equal to the default still counts as
  set for this project.
Unknowns: none blocking.
Decision-blocking questions:
  - Q1: keep the guided form and the advanced key/value form next to the new
    row editing, or let row editing replace both (common settings first, with
    their existing help and choice lists)?
Proposed behaviors:
  1. The config view API returns, per effective setting, its source (set for
     this project / default), whether the browser can edit it, the key used to
     edit it, and whether applying a change needs a restart, using the same
     editability rule that guards edits.
  2. Configuration shows a "Set for this project" or "Default" badge on every
     row and, for administrators, an Edit control on editable rows that stages
     the change through the existing pending flow; non-editable rows say how
     they can be changed (TOML import or CLI).
  3. A filter shows only the settings set for this project.
  4. Per Q1, the separate guided and advanced forms stay or are replaced.
Path and reason: full - new API fields and new UI behavior.

## Requirement coverage

Behavior inventory (spec `specs/REQ-FUNC-49b766fe.md`):

| Frame outcome | Actor/system | Trigger or state | Response | Positive case | Boundary or failure | Observable result |
|---|---|---|---|---|---|---|
| Source and editability known | web API | GET project config | per-setting source/editable/edit_key/restart | set vs default key, executor mapping | lists, commands, secrets, other sections not editable; developer gets metadata | JSON `settings` |
| Badges and row editing | browser | open Configuration | badge per row; admin edit on editable rows | stage + apply flips default to set | non-editable note; developer no controls; pending change disables edits | rows and pending panel |
| Fewer rows | browser | filter on | only project-set rows | handful of rows | empty sections hidden | list |

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Source and editability (behavior 1) | API metadata per setting with shared edit rule | REQ-FUNC-49b766fe | set/default, mapping, restart | non-editable kinds; shared key rule, sampled staging checks | pytest | `_editable_setting_key` shared helper + `_setting_metadata` |
| Badges, row editing, common first (behaviors 2, 4) | rows labelled; admin edits on row via pending flow; forms replaced | REQ-UX-9a625fc5 | edit default and set rows | non-editable note; developer read-only | node tests + manual browser | `settings.ts` row model; `SettingsList` component |
| Project-set filter (behavior 3) | filter rows to source project | REQ-UX-a62e69a9 | handful shown | empty sections hidden | node tests + manual browser | `settings.ts` filter |

## Design

Behavior and API shape live in `specs/REQ-FUNC-49b766fe.md`.

- **Shared edit rule (REQ-FUNC-49b766fe; technical: one source of truth).**
  `04_Software/adore/web/app.py` gets `_editable_setting_key(key) -> bool`
  holding today's inline condition (key regex, editable sections, not
  secret-like, not `.command`); `config_update` and `_candidate_config_edit`
  call it (the OpenAI endpoint special key keeps its own branch).
  `_setting_metadata(config_dict, raw_toml)` walks leaves, maps
  `executor.commands.<n>.<f>` to `executor.<n>.<f>`, compares with the raw
  TOML leaves (tomllib on the bytes already read), and sets
  `editable = _editable_setting_key(edit_key) and value is str/int/float/bool`
  and `restart = _restart_required(edit_key)`. `config_view` returns it as
  `settings`. No change to staging, validation, locks or RBAC.
- **Row model (REQ-UX-9a625fc5, REQ-UX-a62e69a9).** New
  `04_Software/web/src/settings.ts`: `settingRows(config, settings)` builds
  rows (section, key, value, source, editKey, restart, input kind:
  `boolean`/`number`/`choice`/`text`/`none`), puts the common settings (moved
  from App.tsx `commonSettings`, with label/help/choice metadata) into a first
  "common" group, and `settingGroups(rows, projectOnly)` filters and drops
  empty groups. Pure functions, tested with `node --test`
  (`web/tests/settings.test.mjs`).
- **UI (REQ-UX-9a625fc5, RULING-002).** `ProjectConfigReadOnly` becomes
  `SettingsList`: collapsible groups (common group open), each row shows label,
  key, type, value, a `Set for this project`/`Default` badge, and for
  administrators a restart hint on editable rows and an Edit button opening an inline
  editor (select for booleans and choices, number input, text input) with
  Stage/Cancel; staging posts `{key: editKey, value, revision}` to the existing
  `/config/pending` and reuses the pending panel (Apply/Discard). Edits are
  disabled while a change is pending. For administrators, non-editable rows
  show a short note (change it in the project's config.toml on the ADORE host). `GuidedConfigForm` and the Advanced key/value form are removed; the
  OpenCode local-endpoint panel, revision, issues and raw redacted JSON stay.
  A "Only settings set for this project" checkbox drives the filter.
- **Texts.** New i18n keys in EN/FR/DE/RO (badges, edit/stage/cancel, restart
  hint, non-editable note, filter label, common group title); unused keys of
  the removed forms are deleted.
- **Compatibility.** API change is additive; no data or config change.
- **Test seams.** `tests/test_web_config.py` (metadata cases, sampled
  staging checks); `web/tests/settings.test.mjs` (rows, kinds, common-first,
  filter); manual browser check with a local web instance (Playwright).
- **Alternatives rejected.** Deciding editability in the browser (would drift
  from the server rule); comparing values with defaults to decide "set" (hides
  explicit choices equal to the default).
- **Risks / open decisions.** None open. No component structure change beyond
  a new frontend helper module; no architecture drawing owed.
- **Expected files.** `04_Software/adore/web/app.py`,
  `04_Software/tests/test_web_config.py`, `04_Software/web/src/{App.tsx,
  settings.ts,i18n.ts,styles.css}`, `04_Software/web/tests/settings.test.mjs`,
  built `04_Software/adore/web/static/`, `01_Documentation/Web_Interface.md`,
  `05_SoftwareDocu/Component_Web_API.md`, `05_SoftwareDocu/Component_Web_Frontend.md`,
  `.agentic/knowledge/web-interface.md`, `CHANGELOG.md`.


## Log

- 2026-10-04 frame: full path (new config-view API fields and Configuration UI behavior). Checkpoint mode; scope and Q1 (keep or replace the separate edit forms) presented.
- 2026-10-04 frame accepted: user chose Q1 "Replace both" and "Autopilot to validate"; scope as framed with behavior 4 = row editing replaces the guided and advanced forms (common settings first, OpenCode local-endpoint panel kept); interaction set to autopilot; stop before deliver.
- 2026-10-04 specify: 3 requirements created (REQ-FUNC-49b766fe, REQ-UX-9a625fc5, REQ-UX-a62e69a9, draft; spec `specs/REQ-FUNC-49b766fe.md`), 0 revised, 0 reused, 0 retired. REQ-UX-66e6f3f5 (grouped values, type, help; admin editing in Project details; developers no controls) and REQ-FUNC-7ce5b17a (validated persisted edits) stay true unchanged.
- 2026-10-04 design: note in `## Design` (shared `_editable_setting_key`, `settings` metadata in config_view, `settings.ts` row model, `SettingsList` with inline editing replacing the two forms, project-set filter); advanced to build (autopilot).
- 2026-10-04 build red: REQ-FUNC-49b766fe, REQ-UX-9a625fc5, REQ-UX-a62e69a9; commands=`.venv/Scripts/python.exe -m pytest -q tests/test_web_config.py::test_config_view_reports_each_settings_source_and_editability` (from 04_Software; exit=1, KeyError 'settings': config view returns no per-setting metadata) and `node --test tests/settings.test.mjs` (from 04_Software/web; exit=1, module src/settings.ts missing: no row model, common grouping or project-set filter).
- 2026-10-04 build green: REQ-FUNC-49b766fe, REQ-UX-9a625fc5, REQ-UX-a62e69a9; `.venv/Scripts/python.exe -m pytest -q tests/test_web_config.py tests/test_web_pending_config.py tests/test_web_rbac.py tests/test_web_import.py tests/test_web_projects.py tests/test_release_consistency.py` (from 04_Software) exit=0 (49 passed); ruff exit=0; `node --test tests/*.test.mjs` (from 04_Software/web) exit=0 (27 passed); `npx tsc -b` exit=0; `npm run build` exit=0, assets normalized to LF. app.py: shared `_editable_setting_key` (both edit endpoints), `_toml_leaves`, `_setting_metadata`, config_view `settings`; web: `settings.ts` row model, `SettingsList` (badges, notes, inline editor, filter) replacing ProjectConfigReadOnly, GuidedConfigForm and the advanced form; 11 i18n keys added and 4 unused removed in EN/FR/DE/RO; styles. The new API test writes its config as LF bytes: with a CRLF file on Windows, staging a key whose table is absent fails (pre-existing write_text CR doubling in _candidate_config_edit; Linux hosts unaffected) - offered as a separate task, not in this scope.
- 2026-10-04 build manual observation: REQ-UX-9a625fc5, REQ-UX-a62e69a9; method=Playwright (Chrome) against a local `python -m adore.web.server` on a seeded home (web-created project alpha, developer with membership); action=admin opened Configuration, checked badges/common-first/notes, edited polling.poll_interval_seconds on its row (60 -> 90), staged, applied, toggled the project-set filter, resized to 390px; developer opened the same page; result=15/15 checks passed (badges, restart and not-editable notes, forms removed, editor prefilled, pending panel, edits disabled while pending, row flips to Set after apply, filter shows only project-set rows, no horizontal overflow at 390px, developer badges without controls). Two UI fixes found during the check: common group title exempt from capitalize, filter checkbox laid out in a row.
- 2026-10-04 validate review round 1: spec_compliance=changes_required (MEDIUM: Web_Interface.md:314 still mentions the removed guided form; MEDIUM: the non-editable note (4 locales, Web_Interface, Component_Web_Frontend) points to Import, which only creates new projects (409 project_exists); MEDIUM: REQ-FUNC-49b766fe verification and spec claim staging accepts exactly the metadata-editable keys, while they share the key rule and lists are excluded only by the metadata (staging of lists is pre-existing); LOW: Design names visibleGroups, REQ-UX-9a625fc5 notes are administrator-only, its manual wording names a set-setting edit, step=any on whole-number editors); implementation_quality=changes_required (MEDIUM: step=any lets whole-number settings take fractions that the server stages; MEDIUM: no test fails if booleans stop being editable; LOW: no lowercase secret-key refusal test, sampled agreement, float shown as integer (pre-existing), Romanian "renunțată", other number rows accept fractions (not a regression)). Routed to build for fix cycle 1 of 4.
- 2026-10-04 build fix cycle 1 red: REQ-UX-9a625fc5; command=`node --test tests/settings.test.mjs` (from 04_Software/web); exit=1; expected missing behavior=rows carry no step, so whole-number editors accept fractions (step=any). The new boolean editable and lowercase secret-key refusal assertions in test_web_config.py pass (regression guards for REQ-FUNC-49b766fe).
- 2026-10-04 build fix cycle 1: rows carry a number step (1 for whole-number common settings, any otherwise) used by the editor; non-editable note in 4 locales, Web_Interface and Component_Web_Frontend points only to the project's config.toml on the host (no Import); Web_Interface run_args sentence no longer mentions the removed guided form; RO configEditHint wording; REQ-FUNC-49b766fe verification and spec Acceptance/interface text state the shared key rule plus the single-value condition and the sampled staging checks; spec example corrected (the wizard writes budgets.max_iterations); REQ-UX-9a625fc5 notes are for administrators and its manual wording matches the observation; Design names settingGroups; tests: step assertions, boolean editable, lowercase secret-key refusal. `pytest -q tests/test_web_config.py tests/test_web_pending_config.py tests/test_web_rbac.py tests/test_web_import.py tests/test_web_projects.py tests/test_release_consistency.py` exit=0 (49 passed); ruff exit=0; `node --test tests/*.test.mjs` exit=0 (27 passed); tsc exit=0; rebuilt assets (LF). Returned to validate for review round 2.
- 2026-10-04 validate review round 2: spec_compliance=changes_required (MEDIUM: Component_Web_Frontend.md:208 says whole-number settings use step 1, but only the common ones do; LOW: Design sentence still names Import for non-editable rows; LOW notes: coverage/test-seam shorthand "staging agreement", pre-existing Web_Interface "use the CLI for other complex settings" (out of scope)); implementation_quality=approved (mutations of booleans, secret rule, .command rule, section allowlist, endpoint exemption, key mapping and step all caught; full suite 729 passed/1 skipped; LOW notes accepted: delivery.draft offers false which validation refuses, server stages 2.5 for whole-number keys (step guard is browser-side), text editors not required, restart(key) vs (edit_key) equivalent). Routed to build for fix cycle 2 of 4 (text only).
- 2026-10-04 build fix cycle 2: Component_Web_Frontend step sentence states the common-settings scope and server validation; Design note names the config.toml route; coverage and test-seam wording say shared key rule and sampled staging checks. No code, test or asset change. Returned to validate for review round 3.
- 2026-10-04 validate review round 3: spec_compliance=approved; implementation_quality=approved (full suite 729 passed/1 skipped; rebuilt assets match source). Cheap recorded LOW notes fixed in fix cycle 3 of 4 (text only): an earlier Unreleased CHANGELOG line still advertised the advanced key editor; the Design did not say the restart and non-editable notes are administrator-only; REQ-UX-a62e69a9 affected_paths lacked styles.css. Accepted LOW notes: staging accepts some list values for keys the shared rule allows (pre-existing endpoint behavior; the UI offers no such edit); delivery.draft offers false which validation refuses; browser-side whole-number step; text editors not required; a choice select showing the first option when the current value is not listed (as before); pre-existing Web_Interface.md:301 CLI wording. Returned to validate for review round 4.
- 2026-10-04 validate review round 4: spec_compliance=approved; implementation_quality=approved (full suite 729 passed/1 skipped; served assets equal a fresh build plus the license stamp). Fix cycle 4 of 4 (text only) for recorded LOW notes: knowledge web-interface.md Change map, Key behaviors and Files now name settings.ts, settings.test.mjs and the three requirements (validate knowledge-reconciliation duty); spec Data example uses polling.poll_interval_seconds as the default; Web_Interface says "a drop-down for choices". Accepted LOW notes: the manual record does not separately mention that developers see no notes (gated by canEdit, verified by code review); the historical Frame example; pre-existing Web_Interface.md:301 CLI wording; the round-3/4 quality notes. Returned to validate for review round 5 (final allowed).
- 2026-10-04 validate review round 5: spec_compliance=approved; implementation_quality=approved (full suite 729 passed/1 skipped; ruff, tsc and 27 frontend tests clean; served assets equal a fresh build plus the license stamp). Accepted LOW notes: knowledge line "guided settings" for REQ-UX-66e6f3f5 means help-guided display; the Web_Interface not-editable list is illustrative (uppercase environment keys not named); developers see no notes (code-gated); staging accepts some list values (pre-existing endpoint behavior, never sent by the UI); delivery.draft offers false which validation refuses; browser-side whole-number step; text editors not required; choice select shows the first option for an unlisted value; pre-existing Web_Interface.md:301 CLI wording.
- 2026-10-04 validate final: command=`python .agentic/aegis.py check --task TASK-2b9eda6e --strict --run`; exit=0; test ok 46.2s, lint ok, frontend ok; errors=0, warnings=4: secret-in-diff for the minified bundle index-BRh-d5kc.js (not scannable, as in earlier web tasks) and 3 pre-existing (tracked fingerprint sidecars; TASK-5e99ee1d Handoff status; TASK-c765e6b4 ruling record). Knowledge web-interface reconciled; requirements re-read; manual browser observation recorded in build; evolution refreshed after the last candidate edit. Validate complete; advanced to deliver; stopping for delivery approval (RULING-003).
- 2026-10-04 deliver: validation evidence, verdicts, accepted notes, diff (13 modified, 9 new files), exclusions and outcome presented; no deviations recorded. User approved "Deploy to DCP, then commit": outcome = DCP deployment of the validated candidate (adore/web/app.py and the static UI), then one repository-local commit (no push/PR).
- 2026-10-04 deliver DCP: archive SHA-256 39d50dea917786b2fb2d674fa20cf96c5400cc34cb5f3e620bb9bd82f80e2768 verified on host; live web/app.py matched base b117025; schema 13; 0 running operations; backups suffix .pre-settings-20261004093603 (app.py, static, web.db); services restarted and active; helpers probe (editable budgets.max_iterations, not executor.opencode.command) -> True False; index serves index-BRh-d5kc.js containing the new settings text; health/ready/UI 200; read-only metadata over the six live profiles: 100 settings each, 34-37 set for the project, 83 editable.
- 2026-10-04 deliver close-out: DCP deployment succeeded; stage done; this repository-local commit carries the candidate, requirements, spec, journal and report (no push or PR requested).

## Rulings

- RULING-001 | date=2026-10-04 | decision=work continues on task/adore-web-interface | reason=continuation of the web interface work on the same branch as the preceding tasks | source=technical | supersedes=none
- RULING-002 | date=2026-10-04 | decision=row editing replaces the guided common-setting form and the advanced key/value form; a Common settings group comes first with the existing help texts and choice lists; the OpenCode local-endpoint panel stays | reason=user answered Q1 "Replace both" | source=user | supersedes=none
- RULING-003 | date=2026-10-04 | decision=autopilot through specify, design, build and validate with explicit review, then stop before deliver | reason=user chose "Autopilot to validate" at the frame checkpoint | source=user | supersedes=none

## Handoff


current: done
status: ready
next: none - delivered; DCP runs the candidate and the local commit records it
must_read: .agentic/tasks/TASK-2b9eda6e.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: validated candidate deployed to DCP and committed locally on task/adore-web-interface
evidence: check --strict --run exit=0; review round 5 approved/approved; DCP deploy verified (helpers probe, served bundle text, health/ready 200, live profile metadata)
issues: accepted LOW review notes (see log); Windows CRLF staging bug offered as a separate task
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 5

## Delivery report (2026-10-04)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-49b766fe - Report each project setting's source, editability and restart need
  - REQ-UX-9a625fc5 - Mark and edit each project setting on its row
  - REQ-UX-a62e69a9 - Filter Configuration to settings set for the project
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=5
- diff vs task base b117025: 22 file(s) changed, 933 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=5 notes=31
- checklist: 4/6 done; open: agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
