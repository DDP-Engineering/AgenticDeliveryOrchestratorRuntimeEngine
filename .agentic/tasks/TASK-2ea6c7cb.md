<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-2ea6c7cb - Manage project access on Project details

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-SEC-3ce206e4, REQ-UX-7ca5687c
parent:
branch: task/adore-web-interface
base: c78739ab10378e99724a3615ba42b7026de19a75
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

Problem: Project details shows administrators a "Manage access" link that
  opens Administration > Users - every account, not filtered to the project.
  Nothing on Project details says who can access the project, and granting a
  developer this project means finding them in the list and ticking it in
  their per-user "Assigned projects" editor.
Desired outcome: administrators see, on the project's own details, which
  developers can access it, and grant or revoke that access there; the link to
  the global Users page goes away.
Actors: administrator (sees and changes access); developers (gain or lose the
  project; they see no access controls); the Users page per-user editor
  (stays).
Primary scenario: administrator opens Project details for aegis -> sees the
  developers who can access it and that administrators always can -> grants
  access to developer dev1 -> dev1 now sees aegis in Projects; revoking it
  removes the project from dev1's views.
Examples: a project with no assigned developers shows an empty state that
  points to Administration > Users for creating accounts; a disabled developer
  is shown as disabled.
Counterexamples: developers see neither the access controls nor the link;
  other projects' grants of the same developer are untouched by a change here.
In scope: an administrator-only API to read and change one project's
  developer grants (CSRF, audit, atomic per project); the Project details
  access UI in EN/FR/DE/RO; removing the "Manage access" link; tests; docs.
Out of scope: creating users, changing roles or passwords from the project;
  the Users page editor (unchanged); rules for archived projects beyond the
  existing ones.
Constraints: developer authorization rules unchanged (REQ-SEC-59d97c68);
  administrators keep global access; every change audited like
  "membership-changed"; concurrent edits of different users' grants or other
  projects must not be lost.
Success signals: tests show an administrator reading and changing a project's
  developers through the new API, the developer's access following it, other
  grants unchanged, and developers refused; a browser check shows the panel
  and no Manage access link.
Evidence:
  - STATED: user asked why Project details shows "management access" and chose
    "Access panel in the project (Recommended)".
  - OBSERVED: 04_Software/web/src/App.tsx:1069 renders the link only for
    administrators, to the adminUsers route; App.tsx:1240 renders each
    developer's "Assigned projects" checkbox editor on the Users page.
  - OBSERVED: 04_Software/adore/web/app.py:1586 GET /api/v1/users returns
    accounts with their projects; app.py:1638-1652 PUT
    /api/v1/users/{user_id}/projects replaces one developer's grants and audits
    "membership-changed"; store.py:867 `set_memberships` replaces per user.
  - INFERRED: a per-project change made of per-user replace calls is
    read-modify-write and can drop a grant changed meanwhile elsewhere; a
    per-project store operation avoids that.
Assumptions: administrators are not listed as grantable (they always have
  access); the panel lists all developers with a granted/not-granted state.
Unknowns: none.
Decision-blocking questions:
  - Q1 (answered): an administrator-only Access tab next to Overview,
    Configuration and Prices (RULING-002).
Proposed behaviors:
  1. Administrators see on Project details which developers can access the
     project (and that administrators always can).
  2. Administrators grant or revoke a developer's access there; the change
     applies at once, is audited, and leaves the developer's other grants
     alone.
  3. The "Manage access" link is gone; developers see no access controls.
Path and reason: full - new API and UI.

| quick-path criterion | met | evidence |
|---|---|---|
| no new externally observable behavior | no | new access controls on Project details |
| no new interface or data format | no | new per-project API |
| no new dependency | yes | none |
| existing requirement covers it | no | REQ-SEC-59d97c68 states who may read; not where grants are edited |
| no security or data-handling change | no | authorization grants change through a new path |

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| see and change a project's developers (behaviors 1, 2: server side) | list developers with access; grant or remove one developer's access to one project, audited, other grants intact | REQ-SEC-3ce206e4 | grant then remove dev1 on alpha; dev1's other project kept | developer 403, missing CSRF 403, unknown project/account 404, admin account 400 | pytest | GET and PUT `/api/v1/projects/{name}/access[/{user_id}]`; store `project_members` and `set_membership` |
| Access tab replaces the link (behaviors 1-3: UI) | administrator-only Access tab with grant/remove, administrators-always note, empty state; no Manage access link | REQ-UX-7ca5687c | tab lists developers and toggles access | developer route falls back to overview; empty state | node routes test, manual browser check | `ProjectTab` gains `access`; App.tsx Access panel; i18n EN/FR/DE/RO |

## Behavior inventory

| Frame outcome | Actor/system | Trigger or state | Response | Positive case | Boundary or failure | Observable result |
|---|---|---|---|---|---|---|
| see access | administrator | open the Access tab | every developer listed with granted or not, disabled marked | dev1 granted, dev2 not | no developers: empty state with a pointer to Users | rows |
| grant | administrator | Grant access on dev2 | dev2 gains this project only | dev2 sees the project | dev2's other grants unchanged | row state, audit entry |
| revoke | administrator | Remove access on dev1 | dev1 loses this project only | dev1 no longer sees it | other developers unchanged | row state, audit entry |
| refuse | developer, forged request | call the access API | refused | - | 403 role or CSRF; 404 unknown project or account; 400 user_not_developer | status codes |
| link gone | administrator, developer | open Project details | no Manage access link; developers see no Access tab | - | developer access route falls back to overview | UI |

## Design

- **Store (REQ-SEC-3ce206e4).** `adore/web/store.py` gains
  `project_members(project) -> set[int]` (user IDs whose grant row carries the
  project's current identity, so rows of a deleted and recreated project do
  not count, matching `memberships`) and `set_membership(user_id, project,
  granted)`, which inserts or replaces, or deletes, exactly that one
  `(user_id, project)` row in one transaction. `set_memberships` stays for the
  Users page.
- **API (REQ-SEC-3ce206e4).** In `adore/web/app.py`, administrator-only:
  - `GET /api/v1/projects/{name}/access` -> `{"developers": [{"id",
    "username", "disabled", "granted"}]}` for every developer account,
    sorted by username.
  - `PUT /api/v1/projects/{name}/access/{user_id}` with `{"granted": bool}`
    (CSRF via `admin_mutation`) -> `{"id", "granted"}`; 404
    `project_not_found` / `user_not_found`, 400 `user_not_developer` for an
    administrator account; audit `membership-changed` with the project and
    `user <id> granted|removed`.
  The project resolves through the existing `project()` helper (name or ID).
  A per-row change cannot overwrite a grant changed elsewhere, unlike a
  whole-list replace (Frame constraint).
- **Errors.** `user_not_developer` gets EN/FR/DE/RO sentences in
  `web/src/errors.ts`, as every code app.py emits does.
- **UI (REQ-UX-7ca5687c).** `routes.ts`: `ProjectTab` gains `access`;
  `normalizeRoute` sends a developer's `access` tab to `overview`, like
  `prices`. `App.tsx`: administrators get the tab after Prices; the panel
  loads the list when the tab opens, shows each developer with a Has access /
  No access state, Disabled when disabled, and a Grant access or Remove access
  button that calls PUT and refreshes; a note says administrators always have
  access; the empty state points to Administration > Users. The Manage access
  link and its i18n key are removed. New i18n keys in all four languages.
- **Tests.** pytest `tests/test_web_project_access.py` (list, grant, revoke,
  isolation of other grants, audit, refusals). node `routes.test.mjs`
  (access tab admin-only). Manual Playwright check of the tab, the link's
  absence and a developer's view.
- **Compatibility.** Additive API; the Users page and its whole-list endpoint
  are unchanged; no data migration (same table).
- **Alternatives.** A whole-list per-project replace was rejected because a
  stale page would drop grants made meanwhile; a client-side composition of
  per-user replaces has the same problem.

## Log

- 2026-10-04 frame: full path (new API and UI). Checkpoint mode; scope and Q1 (placement) presented; runs after TASK-a4fec466 because both change web/app.py and CHANGELOG.md.
- 2026-10-04 frame accepted: user chose an Access tab and "Autopilot to validate"; waits for TASK-a4fec466 to be delivered, then resumes at specify.
- 2026-10-04 resumed after TASK-a4fec466 was delivered; base moved to c78739a (no file of this task had been changed).
- 2026-10-04 specify: 2 requirements created (draft; no separate spec - the two endpoints' shapes are in the Design), 0 revised, 0 reused, 0 retired. REQ-SEC-59d97c68 (developer project restriction) and REQ-UX-2c85559e stay true; the Users page editor is unchanged.
- 2026-10-04 design: note in `## Design` (store per-row grant, two administrator endpoints, access tab, link removed); advanced to build (autopilot).
- 2026-10-04 build red: REQ-SEC-3ce206e4; `.venv/Scripts/python.exe -m pytest -q tests/test_web_project_access.py` (from 04_Software; exit=1, 2 failed: GET /api/v1/projects/alpha/access answered 404 not_found and PUT .../access/{id} 405 - no such endpoints). REQ-UX-7ca5687c; `node --test tests/routes.test.mjs` (from 04_Software/web; exit=1, 2 failed: /projects/<id>/access does not parse and a developer's access tab is not sent to overview).
- 2026-10-04 build green: REQ-SEC-3ce206e4, REQ-UX-7ca5687c; store `project_members` and `set_membership`; GET and PUT `/api/v1/projects/{name}/access[/{user_id}]`; `user_not_developer` in errors.ts (EN/FR/DE/RO); `access` project tab (admin-only via `ADMIN_PROJECT_TABS`); `ProjectAccess` panel reusing the Users row styles plus a phone rule for the status badge; Manage access link and its i18n key removed; 10 new i18n keys per language; bundle rebuilt as index-DQFFP2rr.js / index-CDZ3eQGu.css (LF). `.venv/Scripts/python.exe -m pytest -q tests/test_web_project_access.py tests/test_web_rbac.py tests/test_web_auth.py tests/test_web_config.py tests/test_web_delete.py tests/test_web_paging.py tests/test_secret_setting_names.py tests/test_web_pending_config.py tests/test_web_readiness.py` (from 04_Software) all passed; `node --test tests/*.test.mjs` 32 passed; tsc and ruff clean. Docs: Web_Interface, Component_Web_Frontend, Component_Web_API, knowledge web-interface.md, CHANGELOG Added; both requirements active with linked tests.
- 2026-10-04 build manual observation: REQ-UX-7ca5687c; method=Playwright (Chrome) on a local `python -m adore.web.server` with a seeded project, developer dev (granted) and dev2 (not granted); checks=no Manage access link, administrator tabs Overview/Configuration/Prices/Access, /access URL, help text, row state and action, grant flips dev2 and shows Access granted, dev2's project list follows, a developer's /access URL falls back to Overview with no Access tab or controls, removal takes the project away, French texts, no horizontal scroll at 375 px; result=13 effective checks passed (the script printed 14 PASS; one was a placeholder that is always true and is covered by the row check); screenshots looked right on desktop and phone.
- 2026-10-04 validate review round 1: spec_compliance=changes_required (HIGH: after a rename, removing access deleted by the current name, matched nothing and still answered 200 with a "removed" audit entry; MEDIUM: granting a new project that reuses a renamed project's old name replaced that row, so the developer silently lost the renamed project; LOW: Component_Web_Frontend still said membership management remains under Users; LOW: no assertion that another developer's grant survives a grant); implementation_quality=changes_required (HIGH: same rename defects; MEDIUM: ProjectAccess had no key, so after switching projects an in-flight change could write project A's list under B; LOW: buttons lacked per-row labels; LOW: no loading state; LOW, not this task: the Users page whole-list replace can still undo a change made here after that page loaded). Both reproduced the rename defects in a temp home. Routed to build for fix cycle 1 of 4.
- 2026-10-04 build fix cycle 1 red: REQ-SEC-3ce206e4; `.venv/Scripts/python.exe -m pytest -q tests/test_web_project_access.py` (from 04_Software; exit=1, 1 failed: after rename and reuse of the name, granting the new alpha left memberships {'alpha', 'beta'} - the renamed project's grant was lost).
- 2026-10-04 build fix cycle 1 green: `set_membership` runs in one BEGIN IMMEDIATE transaction, reads the account's rows, keeps the grants that still match a live project (re-labelled to its current name, as `set_memberships` stores them), drops or adds the target by identity and rewrites the account's rows; `memberships` and `set_membership` share `_projects_by_id` and `_granted_projects`. Test covers rename then remove and reuse then grant, plus the other developer's grant after a grant. UI: `key={selected}` on ProjectAccess, per-row aria-labels, a loading line (new key in 4 languages); frontend doc sentence fixed; bundle rebuilt as index-8sF3OhEo.js (LF). 91 backend tests (access, rbac, auth, config, delete, paging, secret names, pending config, readiness, errors) passed; node 32 passed; tsc and ruff clean.
- 2026-10-04 build fix cycle 1 manual observation: REQ-UX-7ca5687c; same Playwright check on a fresh seeded home, with the placeholder replaced by a check of the per-row button names; result=14/14 passed. Returned to validate for review round 2.
- 2026-10-04 validate review round 2: spec_compliance=approved (no findings; rename repro clean); implementation_quality=approved (concurrency probe: 24 threads x 5 rounds and mixed whole-list writers lost no grant; LOW: a switched-away panel could still post its notice; LOW: a failed load kept showing the loading line; LOW: a rename landing between the project snapshot and the write raised a raw IntegrityError, a 500; Users page whole-list replace remains out of scope). Taken as fix cycle 2 of 4.
- 2026-10-04 build fix cycle 2 red: REQ-SEC-3ce206e4; `.venv/Scripts/python.exe -m pytest -q tests/test_web_project_access.py -k racing` (from 04_Software; exit=1: sqlite3.IntegrityError UNIQUE constraint failed instead of a store error).
- 2026-10-04 build fix cycle 2 green: `set_membership` turns that IntegrityError into WebStoreError "project changed during the update" (rolled back), mapped to 409 `project_changed` with EN/FR/DE/RO sentences; the panel ignores late results after unmount (guard set on every mount, as StrictMode remounts) and shows "Nothing to show" when the first load fails. Bundle rebuilt as index-DS4ntODd.js (LF). 119 backend tests (adds commands, pricing, errors) and 32 node tests passed; tsc and ruff clean; Playwright 14/14 on the final bundle. Returned to validate for review round 3.
- 2026-10-04 validate review round 3: spec_compliance=approved (LOW: the API doc did not list the 409 project_changed reply); implementation_quality=approved (LOW: the 409 was tested only at the store level; LOW: if the reload after a successful change failed, the row kept its old state). Taken as fix cycle 3 of 4.
- 2026-10-04 build fix cycle 3: Component_Web_API lists the 409; a route-level test asserts 409 project_changed, unchanged grants and no audit entry (it guards the behavior added in fix cycle 2, so it passed at once); the panel updates the changed row and shows the notice as soon as the change succeeds, then reloads. Bundle rebuilt as index-eXaOMm5B.js (LF). 120 backend and 32 node tests passed; tsc and ruff clean; Playwright 14/14. Returned to validate for review round 4.
- 2026-10-04 validate review round 4: spec_compliance=approved, implementation_quality=approved, no findings (rename, concurrency and 409 probes rerun; the route test fails when the 409 mapping is removed; bundle equals a fresh build). Out of scope and recorded only: the Users page whole-list replace can still undo an Access-tab change made after that page loaded (pre-existing).
- 2026-10-04 validate final: command=`python .agentic/aegis.py check --task TASK-2ea6c7cb --strict --run`; exit=0; test ok 49.3s, lint ok, frontend ok; errors=0, warnings=4: secret-in-diff on the minified bundle (too large to scan, built from reviewed sources and equal to a fresh build) and 3 from before this task (tracked sidecars; TASK-5e99ee1d and TASK-c765e6b4 journal headers). Knowledge web-interface.md updated (change map, key behaviors, tabs); both requirements re-read active with paths and linked tests true; manual browser check recorded (14/14 on the final bundle); evolution refreshed after the last edit. Advanced to deliver; stopped for delivery approval (RULING-003).
- 2026-10-04 deliver: validation evidence, verdicts, diff (15 modified/deleted, 6 new files), exclusions (none) and outcome presented; no deviations recorded. User approved "Deploy to DCP, then commit (Recommended)": outcome = DCP deployment of adore/web/app.py, adore/web/store.py and the static UI, then one repository-local commit (no push/PR).
- 2026-10-04 deliver DCP: archive SHA-256 7de8658b862078b5a90aad33cdd0b3e7e4be3f9789315cfa440db8b9a691d475 verified on host; live files matched base c78739a; schema 13; 0 running operations; backups suffix .pre-access-20261004190003 (app.py, store.py, static, web.db); services restarted and active; probe (store methods, project_changed code) -> True True; index serves index-eXaOMm5B.js containing the Access tab text; unauthenticated access route 401; health/ready/UI 200; read-only state: 1 account (the administrator), 0 developers, so the tab shows its empty state.
- 2026-10-04 deliver close-out: DCP deployment succeeded; stage done; this repository-local commit carries the candidate, requirements, journal and report (no push or PR requested). The pre-existing Users page whole-list replace concern is offered as a separate task.

## Rulings

- RULING-001 | date=2026-10-04 | decision=work stays on task/adore-web-interface and runs after TASK-a4fec466 | reason=user chose "Access panel in the project (Recommended)"; both change web/app.py and CHANGELOG.md | source=user | supersedes=none
- RULING-002 | date=2026-10-04 | decision=the access controls live in an administrator-only Access tab next to Overview, Configuration and Prices; the Manage access link is removed | reason=user answered Q1 "Access tab (Recommended)" | source=user | supersedes=none
- RULING-003 | date=2026-10-04 | decision=autopilot through specify, design, build and validate with explicit review, then stop before deliver | reason=user chose "Autopilot to validate (Recommended)" | source=user | supersedes=none

## Handoff


current: done
status: ready
next: none - delivered; DCP runs the candidate and the local commit records it
must_read: .agentic/tasks/TASK-2ea6c7cb.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: validated candidate deployed to DCP and committed locally on task/adore-web-interface
evidence: check --strict --run exit=0; review round 4 approved/approved; DCP deploy verified (probe, served bundle, access route 401, health/ready 200)
issues: none
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 4

## Delivery report (2026-10-04)

- stage: done; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-SEC-3ce206e4 - Change one developer's access to one project
  - REQ-UX-7ca5687c - Manage project access from an Access tab
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=4
- diff vs task base c78739a: 22 file(s) changed, 670 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=4 notes=31
- checklist: 6/6 done
