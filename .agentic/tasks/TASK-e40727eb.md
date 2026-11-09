<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-e40727eb - Web review fixes: first-login password, localized errors, name pattern, stale errors, system-dark contrast

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-SEC-676d284c, REQ-UX-309a6b3f, REQ-FUNC-9c1f728e, REQ-UX-e6ed7168, REQ-UX-359f8cbf, REQ-UX-94dc4e69, REQ-UX-1a34d639
parent:
branch: task/adore-web-interface
base: a714d1803d8818ea7186313b932e0c8f57142366
opened: 2026-10-03

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: A browser review of the web interface on this branch (local instance
of commit a714d18, 2026-10-03) found five defects the user asked to fix
(STATED: "fix 1-5, on the same branch"):
1. A fresh store bootstraps `admin`/`admin` and nothing ever requires it to be
   changed; an operator can run indefinitely on a publicly known password.
2. The UI displays raw API error codes (`invalid_project_name`) and, for store
   failures, English sentences passed through as `detail.code`; none are
   localized.
3. The project-name `pattern` on Add/Import project is ignored by Chrome, so
   invalid names reach the server.
4. An error banner survives a later successful action (seen after creating a
   project).
5. With theme `system` on a dark OS, primary buttons render white text on the
   light accent (2.0:1 contrast).

Desired outcome: The default credential cannot be used beyond changing it;
every error a user sees is a localized sentence; invalid project names are
caught in the browser; error banners reflect only the latest action; primary
buttons meet WCAG AA contrast in every theme path.

Actors: Administrator (first login, account management, project creation);
developer (sees errors, changes own password); operator upgrading an existing
deployment whose `admin` still has the default password.

Primary scenario (accepted, RULING-003): administrator resets a developer's
password -> developer signs in with it -> API marks the account as
password-change-required and the UI shows only a change-password screen ->
developer sets a new password (>= 8 chars) -> signs in again and the full
dashboard is available. Fresh `admin`/`admin` sign-in is unchanged
(RULING-002).

Examples:
- 1: GET /api/v1/projects with a must-change session -> 403
  `password_change_required`; GET /api/v1/me still works.
- 2: create project named `My Project` -> banner reads a localized sentence
  ("Use 1-64 lowercase letters, digits, dots, underscores or hyphens...")
  instead of `invalid_project_name`; short password -> `password_too_short`
  code, localized sentence.
- 3: typing `My Project` and pressing Save shows the browser's own pattern
  validation message and sends no request.
- 4: failed create, then successful create -> no error banner on the project
  page.
- 5: OS dark + theme System -> primary button text uses the dark-theme
  foreground, matching explicit Dark.

Counterexamples:
- An administrator-created developer account with a chosen password is not
  forced to change it (out of scope unless decided otherwise, see questions).
- Errors from unauthenticated health/ready probes are not UI-visible; no change.

In scope:
- Store schema 13: per-user "password change required" flag, set by an
  administrator password reset and cleared by a successful own password
  change (RULING-003). The bootstrap `admin`/`admin` account stays usable
  without a forced change (RULING-002); upgraded rows start unflagged.
- API: protected routes reject must-change sessions with 403
  `password_change_required`, except `GET /me`, `GET/PATCH /me/preferences`,
  `POST /me/password`, `DELETE /session`; `/me` and login expose the flag.
- UI: forced change-password view for flagged sessions.
- API: store failures surfaced to clients map to stable snake_case codes.
- UI: localized message table (en/fr/de/ro) for every client-visible code,
  with a localized generic fallback that still shows the unknown code.
- UI: escape `-` in both project-name patterns.
- UI: clear the error banner when an action succeeds and on navigation.
- CSS: apply the dark primary-button foreground under the system-dark media
  rule as well as explicit Dark.
- Tests, rebuilt bundle, component docs (`05_SoftwareDocu/`), operator docs
  (`01_Documentation/Web_Interface.md`), knowledge page, CHANGELOG.

Out of scope: review items 6-13 and polish (routing, project page layout,
placeholders, required markers, menu labels, mobile tables, polling);
TASK-48ddbb7d (projects table removal action) stays separate and untouched.

Constraints: Preserve REQ-SEC-9ee171c9's fresh-install `admin`/`admin` login
(the user authorized hardening, not removing it); corrupt or unknown schemas
fail closed; migrations are forward-only like versions 1-12; tests offline;
Code_Style prologues; license headers; docs updated in the same change.

Success signals: new failing-then-passing tests for the flag (fresh, upgrade,
clear, route gating) and error-code mapping; full offline suite, Ruff,
TypeScript/Vite build green; browser check of forced-change flow, localized
error, pattern rejection, banner clearing and system-dark contrast.

Evidence:
- OBSERVED: bootstrap insert `("admin", _HASHER.hash("admin"), "admin", ...)`
  and `PRAGMA user_version=12` in `04_Software/adore/web/store.py:230-239`.
- OBSERVED: `principal()` only checks session presence,
  `04_Software/adore/web/app.py:212-216`.
- OBSERVED: `_error(4xx, str(exc))` at app.py lines 1390, 1427, 1443, 1452,
  1461, 1471, 1523, 2115, 2295 forwards store/wizard sentences as codes.
- OBSERVED: `request()` throws `detail.code` verbatim and views call
  `setError(cause.message)`, `04_Software/web/src/App.tsx:66` and 26 sites.
- OBSERVED: `pattern="[a-z0-9][a-z0-9._-]{0,63}"`, App.tsx:873 and 892; in
  Chrome `new RegExp(..., 'v')` throws "Invalid character in character class".
- OBSERVED: `:root[data-theme="dark"] .primary { color: #09251b; }` only,
  `04_Software/web/src/styles.css:62`; system-dark tokens at lines 29-32.
- OBSERVED: contrast #fff on #67c9a5 = 2.0:1; #09251b on #67c9a5 = 8.1:1.
- OBSERVED: REQ-SEC-9ee171c9 requires the fresh `admin`/`admin` login;
  `.agentic/knowledge/web-interface.md` records it as an invariant.
- OBSERVED: no `[interaction]` table in `.agentic/aegis.toml` -> checkpoint.
- STATED: user asked to fix items 1-5 on branch `task/adore-web-interface`
  and then asked to use AEGIS.
- INFERRED: the user's live server (192.168.1.15) may still use admin/admin,
  so the upgrade migration matters as much as the fresh path.

Assumptions: French, German and Romanian error strings may be agent-authored
like the existing i18n entries. Changing English sentence `detail.code`
values to snake_case is acceptable because the bundled UI is the only client
(OBSERVED: no API tests assert those sentences; only a store-level test
matches "user not found").

Unknowns: whether an administrator password reset should also force the
target to change it at next login (see questions).

Decision-blocking questions:
- Q1. First-login hardening: (a) keep admin/admin, force a password change
  before any other use, and apply the same to upgraded stores whose admin
  still has the default [recommended]; or (b) replace admin/admin with a
  random one-time password printed by the server on first start.
- Q2. Should an administrator's password reset also force the target user to
  choose a new password at next login? [recommended: yes, small and consistent]

Proposed behaviors:
- B1 forced change for default credential (fresh + upgraded) -> signal 1.
- B2 stable codes + localized messages with fallback -> signal 2.
- B3 working browser pattern -> signal 3.
- B4 banner cleared on success/navigation -> signal 4.
- B5 system-dark primary foreground -> signal 5.

Path and reason: full path.
criterion | yes | no | evidence
no new externally observable behavior | | no | forced change view, new 403 code
no new interface or data format | | no | schema 13 column, error codes
no new dependency | yes | | none needed
existing requirement covers behavior | | no | REQ-SEC-9ee171c9 lacks forced change
no security/data-handling change | | no | credential policy changes

## Requirement coverage

Behavior inventory:

Frame outcome | Actor/system | Trigger or state | Response | Positive case | Boundary or failure | Observable result
---|---|---|---|---|---|---
1 reset forces change | API/store | admin reset of account | mark account; gate routes | protected route 403 `password_change_required`, allowlist 200 | wrong current keeps mark; restart keeps mark; bootstrap/upgraded unmarked; missing column fails closed | API status + code
1 reset forces change | browser | marked session | change-password-only view | form, reason, language, theme, sign out | wrong current shows error, form stays; success -> sign-in | rendered view
2 stable codes | API | any rejected request | `detail.code` snake_case, optional `message` | store/wizard/validation/framework cases mapped | unmapped -> `request_rejected` | JSON body, unchanged status
2 localized messages | browser | failed request | localized sentence + diagnostic | known code in 4 locales | unknown code -> generic message naming code | banner text
3 name pattern | browser | Add/Import project submit | block invalid name | valid names accepted | `My Project`, leading `-`, empty, 65 chars rejected; no request | browser validation message
4 latest error only | browser | later success or view change | clear prior error | success after failure shows no banner | later failure replaces error | banner absence
5 system-dark contrast | browser | OS dark + theme System | dark primary foreground | 8.1:1 like explicit Dark | light theme unchanged (5.9:1) | computed colour

Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact
---|---|---|---|---|---|---
1 | API/store gating after administrator reset | REQ-SEC-676d284c (new) | marked session limited to allowlist | wrong current, restart, upgrade, corrupt column | automated store + API tests | schema 13 column; dependency split
1 | change-password-only view for marked session | REQ-UX-309a6b3f (new) | only form + reason + controls | wrong current; success -> sign-in | manual browser | session flag drives view
2 | stable API error codes | REQ-FUNC-9c1f728e (new) | mapped codes, `message` diagnostics | unmapped -> `request_rejected`; 422/404 shapes | automated API tests | central mapping + handlers
2 | localized error display | REQ-UX-e6ed7168 (new) | code -> localized sentence | unknown code fallback | automated node test + manual | `errors.ts` pure module
3 | browser name validation | REQ-UX-359f8cbf (new) | valid names submit | invalid names blocked pre-request | automated node test (v flag) + manual | shared pattern constant
4 | clear stale error | REQ-UX-94dc4e69 (new) | success/navigation clears | later failure replaces | manual browser | central clearing points
5 | system-dark primary contrast | REQ-UX-1a34d639 (reused, unchanged) | system-dark = explicit dark foreground | light theme unaffected | manual inspection per existing verification | CSS media rule only

## Design

Requirements coverage and decisions:
- REQ-SEC-676d284c: `users.password_change_required` column (schema 13, spec).
  `WebStore.reset_password` sets it, `change_password` clears it on success,
  `_user()` exposes it. In `create_app`, split auth dependencies:
  `account_principal` (session only) and `account_mutation` (+CSRF) serve the
  five allowlisted routes; `principal` = `account_principal` + 403
  `password_change_required`, so every existing `mutation`/`administrator`/
  `admin_mutation` route inherits the gate and the spec's check order.
- REQ-UX-309a6b3f: frontend keeps a marked account in separate
  `passwordSession` state, leaving `session` null so every existing
  session-gated effect and poller stays idle (named constraint: 12 effects key
  on `session`; gating each would be invasive). Render order: loading ->
  `passwordSession` forced view (change form, reason, language, theme, Sign
  out) -> login -> shell. Success clears both states and shows sign-in.
- REQ-FUNC-9c1f728e: `_error(status, code, message=None)`; module
  `_STORE_ERROR_CODES` map + `_store_error(status, exc)` replace the nine
  `str(exc)` sites; project creation uses `project_setup_invalid` + message.
  Handlers: `RequestValidationError` -> 422 `invalid_request` (locations and
  reasons only); Starlette `HTTPException` with non-dict detail ->
  `not_found`/`method_not_allowed`/`request_failed`. SPA fallback returns 404
  `not_found` for `api/...` paths instead of `index.html`.
- REQ-UX-e6ed7168: new pure `web/src/errors.ts`: `ApiError(code, detail)`,
  per-locale `errorMessages`, `describeError(locale, failure)`; client-only
  codes `network_error`, `unexpected_response`, `request_failed`. `request()`
  throws `ApiError`; error state stores the raw failure (`unknown`) and both
  banners render `describeError`, so a language switch re-renders the text.
  Already-localized strings pass through unchanged.
- REQ-UX-359f8cbf: new pure `web/src/projectName.ts` exports the pattern with
  `-` escaped (`[a-z0-9][a-z0-9._\-]{0,63}`), used by Add and Import.
- REQ-UX-94dc4e69: `setError("")` at the start of every user action handler
  (15 lack it today) plus one `useEffect([page])` clear. Background pollers
  do not clear, so a user-visible error is only removed by a user action.
- REQ-UX-1a34d639: add `.primary { color: #09251b; }` inside the existing
  `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])` path.

Interfaces/data: schema 13 additive column; API adds `password_change_required`
to account objects and `detail.message`; status codes unchanged.
Compatibility/migration: forward-only ALTER from 1-12, default 0 (RULING-002);
rollback to an older build fails closed on version 13 (existing rule).
Security: gate sits in the shared dependency, so new routes are gated by
default; allowlist is explicit. Messages carry no secrets or input values for
validation errors; wizard diagnostics echo only the admin's own answers.
Concurrency: none new (single UPDATE per call inside existing connections).
Observability: audit actions unchanged (`password-reset`, `password-changed`).
Test seams: `tests/test_web_auth.py` (store flag, migration, gating, check
order); new `tests/test_web_errors.py` (code table, 422/404/405, project
setup, regex); `web/tests/errors.test.mjs` (every code emitted by
`adore/web/app.py` has 4-locale messages, fallback); `web/tests/
projectName.test.mjs` (pattern under `v` flag). Manual browser pass for
forced view, banners, pattern and system-dark contrast.
Alternatives: per-route gating (rejected: easy to miss new routes); message
translation keyed on English sentences (rejected: unstable, untestable);
storing translated text in error state (rejected: stale on language switch).
Expected files: adore/web/store.py, adore/web/app.py, web/src/App.tsx,
web/src/errors.ts, web/src/projectName.ts, web/src/styles.css, web/tests/
errors.test.mjs, web/tests/projectName.test.mjs, tests/test_web_auth.py,
tests/test_web_errors.py, rebuilt adore/web/static/, 05_SoftwareDocu
Component_Web_API/Identity/Frontend, 01_Documentation/Web_Interface.md,
.agentic/knowledge/web-interface.md, CHANGELOG.md.
Risks: hidden callers of `setError(string)` assumptions (TS will flag type
use); FR/DE/RO wording quality (agent-authored, as existing strings).
Open decisions: none. No architecture drawing owed: no component structure
change (two pure frontend modules follow the existing auditPolicy.ts pattern).

## Log

- 2026-10-03 frame: full path (security behavior, schema and API error-contract changes); scope = review items 1-5 only; paused for scope acceptance and Q1/Q2.
- 2026-10-03 frame: scope accepted by user; Q1 -> default credential hardening deferred (RULING-002); Q2 -> reset forces change (RULING-003); advanced to specify.
- 2026-10-03 specify: 6 requirements created (draft) with 2 specs, 1 reused unchanged (REQ-UX-1a34d639 contrast), 0 revised, 0 retired; paused for checkpoint.
- 2026-10-03 specify: user chose continue; advanced to design.
- 2026-10-03 design: note recorded in ## Design (dependency split, error mapping, errors.ts/projectName.ts, forced-view state); paused for checkpoint.
- 2026-10-03 design: user chose continue; advanced to build.
- 2026-10-03 build red: REQ-SEC-676d284c; command=`.venv\Scripts\python.exe -m pytest -q tests/test_web_auth.py -k "reset_password_requires or bootstrap_admin_and_schema or thirteen_missing or limits_api"`; exit=1; expected missing behavior=no password_change_required account field or schema-13 column (KeyError / no such column).
- 2026-10-03 build green: REQ-SEC-676d284c; command=`.venv\Scripts\python.exe -m pytest -q tests/test_web_*.py`; exit=0; 163 passed (5 new auth tests; schema-9/10 tests updated from current version 12 to 13; migration made idempotent for downgraded-fixture stores).
- 2026-10-03 build red: REQ-FUNC-9c1f728e; command=`.venv\Scripts\python.exe -m pytest -q tests/test_web_errors.py`; exit=1; expected missing behavior=store sentences used as detail.code, list-shaped 422 detail, unknown GET /api path served index.html with 200.
- 2026-10-03 build green: REQ-FUNC-9c1f728e; command=`.venv\Scripts\python.exe -m pytest -q tests/test_web_*.py`; exit=0; 169 passed (6 new error-contract tests).
- 2026-10-03 build: user instruction "continue up to validation" - interaction switched to autopilot through validate; stop before deliver (RULING-004). User also requests a live deployment on the DCP server after validation.
- 2026-10-03 build red: REQ-UX-359f8cbf; command=`node --test tests/projectName.test.mjs` (in 04_Software/web); exit=1; expected missing behavior=pattern [a-z0-9][a-z0-9._-]{0,63} throws "Invalid character in character class" under the v flag browsers use (pattern extracted unchanged into projectName.ts first).
- 2026-10-03 build green: REQ-UX-359f8cbf; command=`node --test tests/projectName.test.mjs`; exit=0; 2 passed; Add/Import inputs use PROJECT_NAME_PATTERN (String.raw keeps the escaped hyphen).
- 2026-10-03 build red: REQ-UX-e6ed7168; command=`node --test tests/errors.test.mjs` (in 04_Software/web); exit=1; expected missing behavior=no localized messages for API/client codes, raw code shown, no generic fallback (errors.ts stub reproduces current raw display).
- 2026-10-03 build green: REQ-UX-e6ed7168; command=`node --test tests/errors.test.mjs`; exit=0; 5 passed (76 API + 2 client codes x 4 locales); App.tsx request() throws ApiError, banners render describeError; `npx tsc -b` exit=0.
- 2026-10-03 build manual observation: REQ-UX-309a6b3f, REQ-UX-94dc4e69, REQ-UX-e6ed7168 (manual part), REQ-UX-359f8cbf (manual part), REQ-UX-1a34d639 (system-dark contrast); method=Playwright-driven Chrome against a fresh local server built from the candidate (scratch verify_ui.py); observed 17/17: bootstrap admin not forced; reset developer sees only change form with reason, language, theme, Sign out (390px); FR heading/error localized; wrong current keeps form; success returns to sign-in with notice; new password reaches dashboard; Add/Import block "My Project" with no request; server rejection banner shows localized sentence; successful create and sidebar navigation clear the banner; system dark primary text rgb(9,37,27), system light rgb(255,255,255). Frontend: `node --test tests/*.test.mjs` exit=0 (14 passed); `npm run build` exit=0.
- 2026-10-03 build: docs updated (05_SoftwareDocu Web API/Identity/Frontend, 01_Documentation/Web_Interface.md, knowledge page, CHANGELOG); scripted edits had written CRLF on Windows - 21 working files normalized to LF (repo .gitattributes eol=lf), then `pytest -q tests/test_web_*.py` exit=0 (169 passed) and `node --test tests/*.test.mjs` exit=0 (14 passed); `ruff check adore tests` exit=0. Evolution: 21 files (7 added, 12 modified, 2 removed superseded bundle hashes), all in the design expected list. Check: errors=0; secret-in-diff WARNs are false positives (password-named i18n keys, error-code strings; minified bundle not scanned); fingerprints-tracked (TASK-86c3ea11 sidecars), TASK-5e99ee1d/TASK-c765e6b4 journal-header and .gitignore/config.example.toml outside-layout WARNs predate this task.
- 2026-10-03 build: all build checklist items met (red/green per automated increment, anchor + evolution, manual observation, links, status active, check reviewed); advanced to validate under autopilot (RULING-004).
- 2026-10-03 validate: review disabled ([review] absent) - semantic diff review done hunk by hunk: backend matches spec/design (gate in shared principal, allowlist via account_principal/account_mutation, error mapping, handlers, api/ 404); 422 messages verified not to echo input (probed bad JSON, wrong types); frontend matches design; small supporting additions within REQ-UX-309a6b3f scope (sign-in confirmation notice, minLength=8 on forced form); no portability or secret concerns. Knowledge page Architecture/Files/Invariants/Change map/Key behaviors reconciled; project.md and environment.md unchanged (still accurate).
- 2026-10-03 validate manual observation: REQ-UX-309a6b3f and REQ-UX-e6ed7168 "each locale" clauses; method=Playwright-driven Chrome, fresh local server from the candidate (scratch verify_locales.py); observed en/fr/de/ro: forced card heading, reason and Sign out localized with no sidebar; wrong current password shows the locale sentence; Add project server rejection shows the locale invalid_project_name sentence without the raw code. Result: ALL LOCALES OK.
- 2026-10-03 validate final: command=`python .agentic/aegis.py check --task TASK-e40727eb --strict --run`; exit=0; ran test (full offline pytest, ok 55.8s), lint (ruff, ok), frontend (node --test web/tests/*.test.mjs, ok); errors=0, warnings=5: index-DXLkOFto.js minified bundle not scanned (generated asset); fingerprints-tracked TASK-86c3ea11 sidecars and TASK-5e99ee1d/TASK-c765e6b4 journal-header predate this task; this journal Handoff status corrected to a valid value after the run (journal-only, candidate unchanged). Evolution last refreshed 18:12 after the final candidate edit; later edits were .agentic-only.
- 2026-10-03 validate: complete; advanced to deliver under RULING-004; stopping before publication. Deployment to DCP is a delivery operation outside AEGIS (repository procedure) and needs host access the agent does not hold (no authorized SSH key; password use is the user's).
- 2026-10-03 deliver: validated candidate confirmed unchanged since proof (later edits .agentic-only). DCP deployment bundle prepared outside the repository at D:\Temp\adore-dcp-review-fixes.tar.gz (SHA-256 af9083d962d37c564a1274ad086dd418b17ac29ac1146248883580e69d911256): candidate app.py, store.py and static bundle with per-file SHA256SUMS and deploy.sh (discovers runtime from adore-web.service, refuses live files differing from base a714d18 unless FORCE=1, refuses while a web operation runs, backs up app.py/store.py/static and web.db, restarts web then worker, verifies health/ready/schema 13/coded 404, auto-rolls back on failure). Agent SSH key auth to DCP is not authorized; the user runs the deployment. Paused for delivery approval.
- 2026-10-03 deliver: user approved "deploy it and commit after": outcome = DCP deployment of the validated candidate, then one repository-local commit on task/adore-web-interface (no push/PR). User authorized a dedicated agent deploy key (from 192.168.1.117 only) and a sudoers rule limited to start/stop of adore-web/adore-web-worker.
- 2026-10-03 deliver DCP attempt 1: user-run deploy.sh stopped in pre-flight - live app.py was base content with CRLF endings (sha256 7856f03c... = CRLF of ad3559a/a714d18); nothing changed. Script made line-ending-insensitive.
- 2026-10-03 deliver DCP attempt 2 (agent key): installed, but the health probe used http://127.0.0.1:8765 while DCP runs run-web-tls.py on https://192.168.1.15:18443; the new build started and served 200s, the probe failed, and deploy.sh rolled back automatically (verified afterwards: base app/store hashes, old assets, web.db schema 12, services active, health/ready 200). Script now reads host/port/TLS/home from the launcher and cross-checks the worker --home.
- 2026-10-03 deliver DCP attempt 3: archive SHA-256 cf3ccd50bd26d0da5dc2e607234a5b875b643b1a21ccf8740f2d2cbc0b4f7484 verified; backups suffix .pre-review-fixes-20261003213828 (app.py, store.py, static, web.db); web.db migrated 12->13; unknown API route returns {"code":"not_found"}; adore-web and adore-web-worker active. Live checks from 192.168.1.117: index serves index-DXLkOFto.js/index-Bub6BicY.css, CSS has --on-accent #ffffff/#09251b, JS contains forced-change strings, POST /session {} -> 422 invalid_request, GET /projects -> 401 authentication_required, health/ready 200.
- 2026-10-03 deliver close-out: DCP deployment succeeded (attempt 3); stage done; this repository-local commit carries the candidate, requirements, specs, journal and report (no push or PR requested).

## Rulings

- RULING-001 | date=2026-10-03 | decision=work stays on task/adore-web-interface; TASK-48ddbb7d on the same branch is not modified | reason=user instruction "on the same branch" | source=user | supersedes=none
- RULING-002 | date=2026-10-03 | decision=keep admin/admin usable without forced change and without an upgrade migration; default-credential hardening is out of scope | reason=user: permit admin/admin during development, change before pre-release | source=user | supersedes=none
- RULING-003 | date=2026-10-03 | decision=an administrator password reset requires the target user to set a new password at next sign-in | reason=user answered Q2 yes | source=user | supersedes=none
- RULING-004 | date=2026-10-03 | decision=flow without checkpoint stops through build and validate, then stop before deliver; deploy the validated candidate to the DCP server for live inspection | reason=user: "continue up to validation. But i want to deploy also on DCP server to see it live" | source=user | supersedes=none

## Handoff


current: done
status: ready
next: none - delivered; DCP runs the candidate and the local commit records it
must_read: .agentic/tasks/TASK-e40727eb.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: validated candidate deployed to DCP and committed locally on task/adore-web-interface
evidence: check --strict --run exit=0; DCP deploy verified (schema 13, coded 404/422/401, new assets, health/ready 200, services active)
issues: none open; default admin/admin hardening deferred by RULING-002
next: none
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

## Delivery report (2026-10-03)

- stage: deliver; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-SEC-676d284c - Require a new password after an administrator reset
  - REQ-UX-309a6b3f - Show only password change while a new password is required
  - REQ-FUNC-9c1f728e - Return stable web API error codes
  - REQ-UX-e6ed7168 - Display localized web error messages
  - REQ-UX-359f8cbf - Validate project names in the browser
  - REQ-UX-94dc4e69 - Show only the latest action's error
  - REQ-UX-1a34d639 - Accessible responsive web journeys
- deviations: none recorded
- explicit review: disabled; existing validation remains required
- diff vs task base a714d18: 31 file(s) changed, 1729 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=5 notes=18
- checklist: 5/6 done; open: close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
