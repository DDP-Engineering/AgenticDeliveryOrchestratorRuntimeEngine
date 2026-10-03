<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-87ebb7d6 - Web review items 6-13: URLs, project page tabs, form clarity, account menu, mobile tables, polling

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-4200375b, REQ-UX-d88d3d7f, REQ-UX-66e6f3f5, REQ-UX-3dda4965, REQ-UX-02f35869, REQ-UX-749d37c8, REQ-UX-5b0fa167, REQ-UX-48d6a55d, REQ-NFR-da638732, REQ-FUNC-a83c4cd3, REQ-NFR-46c98d6c
parent:
branch: task/adore-web-interface
base: f2a5775e6efc86d08b296ac80eef80d28d27fc18
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

Problem: The 2026-10-03 browser review listed eight "should fix" items (6-13)
that the user now asks to fix (STATED: "now fix items 6-13 from the review"):
6. The address bar always shows `/`: refresh returns to Overview, Back leaves
   the app, and no view can be linked or bookmarked.
7. Project details shows Jobs / Metrics / Settings / Assigned projects as
   identical tab-like buttons with different behaviors (navigate, navigate,
   scroll, open admin Users); "Assigned projects" opens account management.
8. Project details is one ~2,300px column (desktop) mixing overview, host
   checks, recent jobs, endpoint form, prices and three separate
   configuration editors.
9. Example placeholders (`pi`, `EXECUTOR_TIMEOUT`, `owner/repository`, `42`)
   are styled like entered values, so filters look already applied.
10. Required fields are unmarked (Add project has 8 required of 12) and the
    8-character password minimum is not shown on password forms.
11. Administrators find their own language/theme/password as "Settings" inside
    Administration, while developers see the same page as "My account".
12. On phones, table horizontal scrolling has no affordance (Projects actions
    are off-screen) and Jobs filters fill the first screen before results.
13. Data views keep polling every 5-30 s while the browser tab is hidden, and
    Overview job tables and Audit fetch every row (`limit=all`) on each load
    or poll.

Desired outcome: Every view has a stable URL that survives refresh and
browser Back/Forward; project details is organized into clearly labelled
tabs with consistent navigation; forms distinguish examples from values and
show required fields and password rules; personal settings sit in one
"My account" place for both roles; phone tables and Jobs filters are usable;
background traffic stops while hidden and large tables are paged by the
server.

Actors: administrator and developer using a desktop or phone browser;
operator sharing links; DCP host serving the API.

Primary scenario: user opens a shared link `/projects/<id>/configuration`
-> signs in if needed -> lands on that project's Configuration tab -> uses
browser Back to return to the previous view; refresh keeps the same view.

Examples:
- 6: `/jobs?project=<id>` refresh keeps Jobs and the project; Back from
  project details returns to Projects.
- 7/8: project details tabs Overview | Configuration | Prices (admin);
  Jobs and Metrics open those pages scoped to the project as links.
- 9: Outcome contains shows a lighter, clearly-example placeholder
  ("e.g. EXECUTOR_TIMEOUT").
- 10: Add project labels show a required marker with a legend; password
  fields show "At least 8 characters" and enforce minLength.
- 11: both roles see "My account" in the main navigation; Administration
  lists System status, Users, Audit.
- 12: a phone Projects table shows a scroll hint/shadow; Jobs results appear
  first with a "Filters" toggle showing the active-filter count.
- 13: switching tabs away stops requests; returning refreshes immediately;
  Audit page 2 requests only 25 rows.

Counterexamples: no visual redesign of unrelated pages; no change to API
authorization, metrics content or job operations; TASK-48ddbb7d's pending
project-removal action is not touched.

In scope: items 6-13 above in `04_Software/web/` (App.tsx, styles.css,
i18n.ts, new pure modules), an audit paging API in `adore/web/app.py`/`store.py`
if needed for item 13, tests, rebuilt bundle, docs, knowledge, changelog,
DCP deployment after validation (as in TASK-e40727eb).

Out of scope: review polish list (chevron glyph, sign-out icon, heading
spacing, prices default executor, metrics empty state); default admin/admin
hardening (TASK-e40727eb RULING-002); TASK-48ddbb7d removal semantics.

Constraints: preserve established contracts unless the user authorizes a
change (OBSERVED: REQ-UX-749d37c8 requires "Administration shall show
separate System status, Users, Audit and Settings sidebar entries;
developers retain My account" - item 11 changes this and needs explicit
approval; REQ-UX-66e6f3f5 requires configuration, endpoint and price editing
"on the same page" - tabs within project details keep that); keep
10/25/50/All paging (REQ-UX-749d37c8); keep Jobs filter Help/placeholders
(REQ-UX-e96a5dd4); tests offline; LF line endings; docs in the same change.

Success signals: deep links, refresh and Back/Forward work for every view
(browser-driven checks); tabs and links behave consistently; no placeholder
indistinguishable from a value; required markers and password hints in all
four locales; phone checks at 390px show actions reachable and results
first; no requests while hidden (network observation); audit/overview page
requests bounded; full suite, Ruff, Node tests and strict check green.

Evidence:
- OBSERVED: `type Page` union with 11 values and 16 `setPage(` calls, no
  `pushState`/`popstate` (`04_Software/web/src/App.tsx:26`).
- OBSERVED: SPA fallback serves `index.html` for non-API paths and assets are
  absolute `/assets/...` (`adore/web/app.py` frontend route,
  `adore/web/static/index.html`) - path URLs need no server change (INFERRED).
- OBSERVED: project-detail buttons at App.tsx (Settings scrolls to
  `#project-settings`, Assigned projects -> `setPage("adminUsers")`).
- OBSERVED: placeholders `pi`, `EXECUTOR_TIMEOUT`, `42`, `owner/repository`,
  `provider/model` in App.tsx; `input::placeholder { color: var(--muted) }`
  (`styles.css:50`), muted = #475b52 (7.3:1).
- OBSERVED: `Field` component and 6 password inputs without minLength
  (App.tsx); store enforces 8 chars (`store.py`).
- OBSERVED: nine `setInterval` pollers (5-30 s) with no `visibilitychange`
  handling; `runs-page?limit=all` (Overview, App.tsx:400) and
  `audit?limit=all` (App.tsx:446, 685, 1111); `/api/v1/audit` accepts
  limit 1-500 or `all` without offset (`app.py` audit_history).
- OBSERVED: `.table-scroll { overflow-x: auto }` without scroll cue.
- OBSERVED: TASK-48ddbb7d (open, build) also edits App.tsx Projects table.
- STATED: user asked to use AEGIS for this repository's work.

Assumptions: path-based URLs (`/projects/<id>/<tab>`) rather than `#/` hashes
(pending Q1); the DCP TLS launcher serves all paths through the same app.

Unknowns: whether any external link or bookmark relies on `/` only (none
known); exact tab set wording (pending Q2).

Decision-blocking questions:
- Q1 URL style: path URLs such as `/projects/<id>/configuration`
  [recommended; server already supports them] or hash URLs `/#/projects/...`.
- Q2 Project details tabs: Overview (summary, host checks, recent jobs) |
  Configuration (settings sections, endpoint, change a setting, raw) |
  Prices (admins); Jobs and Metrics as links to those pages
  [recommended], or keep one page with an in-page section menu.
- Q3 Item 11: move administrators' personal settings to a "My account" entry
  outside Administration, revising REQ-UX-749d37c8 [recommended], or keep it
  under Administration renamed "My account".

Proposed behaviors:
- B6 URL routing with deep links, refresh and history -> signal 1.
- B7 consistent project-detail navigation, "Manage access" label -> signal 2.
- B8 project-detail tabs -> signal 2.
- B9 distinguishable example placeholders -> signal 3.
- B10 required markers and password rules -> signal 4.
- B11 single "My account" location -> signal (navigation check).
- B12 phone scroll cue and collapsible Jobs filters -> signal 5.
- B13 hidden-tab pause/resume and server-paged Audit/Overview -> signal 6.

Path and reason: full path.
criterion | yes | no | evidence
no new externally observable behavior | | no | URLs, tabs, menus change
no new interface or data format | | no | URL scheme; audit paging API
no new dependency | yes | | none planned (no router library)
existing requirement covers behavior | | no | REQ-UX-749d37c8 must change for item 11
no security/data-handling change | yes | | display/navigation only; auth unchanged

Children: none - items share App.tsx and the navigation model; build will
work them as separate increments.

## Requirement coverage

Behavior inventory:

Frame outcome | Actor/system | Trigger or state | Response | Positive case | Boundary or failure | Observable result
---|---|---|---|---|---|---
6 URLs | browser | view change, reload, Back/Forward, deep link | path URL per view; history entries | reload/Back show same view | unknown path, developer on admin path, unauthorized project -> fallback with replace; signed-out deep link -> sign-in then target | address bar + rendered view
7/8 tabs | browser | open project details | Overview/Configuration/Prices tabs; Jobs/Metrics/Manage access links | tab switch changes content only | developer: no Prices/Manage access, no edit controls | selected tab, URL
9 placeholders | browser | empty field | example marker + distinct style | typed value looks different | contrast >= 4.5:1 in all themes | rendered field
10 required/password | browser | form display/submit | required indicator + legend; 8-char rule shown and enforced | valid submit | 7-char password blocked pre-request | form + validation message
11 account | browser | navigation | top-level My account for both roles; Administration = status/users/audit | admin opens My account | `/account` for both; no Settings under Administration | sidebar
12a tables | browser | table wider than container | edge cue on hidden side | cue at right, gone at edge | no overflow -> no cue | rendered cue
12b Jobs filters | browser | width < 760px | collapsed Filters control with active count | results in first screen | expand shows unchanged filters; desktop unaffected | layout
13a polling | browser | page hidden/visible | no periodic requests while hidden; immediate refresh on return | resume interval | rapid toggles do not double-poll | network log
13b paging API | API | audit-page / multi-lifecycle runs-page | slice + total; any-of lifecycle | page 2 of 60 | bad limit/offset 422, developer 403, offset past end empty | JSON
13c paging UI | browser | page through Audit / Overview tables | request only displayed page; All requests all | page change -> one bounded request | All -> one limit=all request | network log

Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact
---|---|---|---|---|---|---
6 | path URL routing with history and deep links | REQ-UX-4200375b (new, spec) | every route round-trips | fallbacks replace history | routes.ts unit tests + manual browser | routes.ts + state/URL sync; routes.test.mjs
7/8 | project-detail tabs and links | REQ-UX-d88d3d7f (new) | tabs switch content | developer role limits | manual browser | projectTab tablist; link row
7/8 | editing remains within Project details | REQ-UX-66e6f3f5 (revised: "on the same page" -> "within Project details") | admin edits on Configuration/Prices tabs | developers no edit controls | existing manual verification | Configuration/Prices tabs hold editors
9 | distinguishable placeholders | REQ-UX-3dda4965 (new) | example marker + style | contrast >= 4.5:1 | inspection | --placeholder token + examplePrefix
10 | required markers + password rule | REQ-UX-02f35869 (new) | indicator + legend | 7-char blocked | manual browser | required-mark, FormLegend, minLength + passwordRule
11 | top-level My account | REQ-UX-749d37c8 (revised clause per RULING-004) | both roles reach My account | Administration has 3 entries | existing manual verification | nav: My account top level; admin group 3 entries
12 | table scroll cue | REQ-UX-5b0fa167 (new) | cue while hidden columns | no cue without overflow | manual browser | CSS scroll shadows on .table-scroll
12 | Jobs filters collapse on phones | REQ-UX-48d6a55d (new) | results first | desktop unchanged | manual browser | Filters (n) toggle below 760px
13 | hidden-page polling pause | REQ-NFR-da638732 (new) | no requests while hidden | immediate refresh on return | polling.ts unit test + manual | polling.ts startVisiblePolling; polling.test.mjs
13 | paged audit + multi-lifecycle runs API | REQ-FUNC-a83c4cd3 (new, spec) | slice + total | bounds/roles | pytest | store.audit_page + /audit-page; list lifecycle; test_web_paging.py
13 | UI requests one page at a time | REQ-NFR-46c98d6c (new) | bounded requests | All -> limit=all | manual network log | ServerPager for Jobs/Audit/Overview job tables

## Design

Requirements coverage and decisions:
- REQ-UX-4200375b (spec): new pure `web/src/routes.ts` with `Route` type,
  `parseRoute(pathname, search)`, `formatRoute(route)` and
  `normalizeRoute(route, {isAdmin})`. App keeps its existing view state
  (`page`, `selected`, new `projectTab`, `metricsTab`, `details`) as the
  source of truth and synchronizes it with the URL (named constraint: 16
  `setPage` call sites; a state-to-URL sync avoids rewriting each one):
  1. apply: on first authenticated render and on `popstate`, parse the URL
     and set view state, guarded by an `applyingRoute` ref;
  2. publish: an effect formats the route from state; a different pathname
     uses `pushState`, query-only changes use `replaceState`; nothing is
     written while applying or while signed out.
  Sign-in keeps the requested URL (clearPrivateView no longer decides the
  view; the apply step does). Sign-out pushes `/`. Authorization
  normalization: admin-only routes for developers and unknown paths use
  `replaceState('/')`; a routed project ID absent from the loaded authorized
  list uses `replaceState('/projects')` plus `ApiError('project_not_found')`,
  and the existing "select first project" fallback must not override a
  routed ID before the list has loaded.
- REQ-UX-d88d3d7f / REQ-UX-66e6f3f5: `projectTab` state with a WAI-ARIA tab
  list (role=tablist/tab/tabpanel, arrow/Home/End keys, as Metrics tabs).
  Overview tab: host prerequisites (admin), recent jobs. Configuration tab:
  read-only settings sections (both roles) + admin editors (pending change,
  endpoint, common setting, advanced key, raw). Prices tab: estimated prices
  (admin only; developers routed there fall back to Overview). Summary card
  keeps metadata and a link row: Jobs (`/jobs?project=`), Metrics
  (`/metrics?project=`), Manage access (`/admin/users`, admin) rendered as
  `<a href>` with click handlers, so middle-click opens a new tab. The
  scroll-to-`#project-settings` button is removed; REQ-UX-7434a8cd 16px
  separation is kept between metadata and the link row.
- REQ-UX-3dda4965: `--placeholder` token (#617169 light 5.15:1 on #fff,
  #8fa197 dark 5.6:1 on #1b2826, both theme paths) and italic
  `::placeholder`; i18n `examplePrefix` (en "e.g.", fr "ex.", de "z. B.",
  ro "ex.") prepended to every example placeholder (7 sites).
- REQ-UX-02f35869: `Field` and `GuidedField` gain `required` rendering of
  `<span class="required-mark" aria-hidden="true">*</span>` (the input keeps
  `required`, which assistive tech announces); a `FormLegend` line with
  i18n `requiredLegend` on every form containing a required field (sign-in,
  forced change, My account, add user, reset password, Add/Import project,
  start job, config/endpoint/price forms). Password-setting inputs get
  `minLength={8}` and i18n `passwordRule` hint text (add user, reset, My
  account, forced change).
- REQ-UX-749d37c8 (revised): nav = Overview, Projects, Jobs, Metrics,
  My account for both roles; admin group = System status, Users, Audit.
  Page value `settings` keeps its content, route `/account`.
- REQ-UX-5b0fa167: CSS-only scroll shadows on `.table-scroll` (background
  gradients with `background-attachment: local, scroll`), so the cue shows
  only on edges with hidden columns and vanishes at each end; no JS.
- REQ-UX-48d6a55d: a `Filters (n)` toggle button rendered on Jobs, shown
  only below 760px by CSS; filter panel hidden below 760px unless
  `jobFiltersOpen`. `n` counts non-empty status, stage, from, through,
  executor and outcome. Desktop layout unchanged.
- REQ-NFR-da638732: new pure `web/src/polling.ts`
  `startVisiblePolling(tick, intervalMs, env = {document, setInterval,
  clearInterval})` returning `stop()`: interval only while
  `document.visibilityState === "visible"`, immediate `tick()` on becoming
  visible, cleanup removes the listener. All nine `window.setInterval`
  pollers in App.tsx switch to it.
- REQ-FUNC-a83c4cd3 (spec): store `audit_page(limit|None, offset)` returning
  `(rows, total)` after pruning, same corruption checks as `recent_audit`;
  API `GET /api/v1/audit-page` (administrator dependency, so the
  password-change gate and 401/403 order apply). runs-page `lifecycle`
  becomes `list[Literal[...]] | None` via `Query()`; matching uses
  membership; single value unchanged.
- REQ-NFR-46c98d6c: extract Jobs' pager into `ServerPager` (size select
  10/25/50/All, previous/next, range) used by Jobs, Audit and Overview job
  tables. Audit state `auditPageSize/auditOffset/auditPage` loads
  `/audit-page`; Overview job tables call runs-page with the card's
  lifecycle values and limit/offset (active: working; review:
  awaiting-approval + in-review; failed: failed). Overview Projects table
  keeps client paging (projects are already fully loaded).

Interfaces/data: URL scheme (spec); new `/api/v1/audit-page`; repeatable
`lifecycle`; no schema or persisted-data change.
Compatibility: `/api/v1/audit` unchanged; old bundles still work against the
new API; existing `/` bookmarks land on Overview.
Security: no auth change; audit-page is administrator-only; routes only
choose views, the API still authorizes every request; URL never carries
secrets or form data.
Concurrency/ordering: route apply vs. async project load handled by
deferring project normalization until the list loads (viewGeneration guards
remain).
Observability: none new.
Test seams: `web/tests/routes.test.mjs` (REQ-UX-4200375b),
`web/tests/polling.test.mjs` (REQ-NFR-da638732), `tests/test_web_paging.py`
(REQ-FUNC-a83c4cd3); browser-driven manual checks for the UX requirements
and network observation for REQ-NFR-46c98d6c/REQ-NFR-da638732.
Alternatives: react-router (rejected: new dependency for a single-shell app;
offline bundle policy); hash URLs (rejected by RULING-002); JS scroll
indicators (rejected: CSS scroll shadows need no listeners); changing
`/audit` to a paged shape (rejected: breaks existing callers).
Expected files: web/src/{App.tsx,i18n.ts,styles.css,routes.ts,polling.ts},
web/tests/{routes,polling}.test.mjs, adore/web/{app.py,store.py},
tests/test_web_paging.py, rebuilt adore/web/static/, 05_SoftwareDocu
Component_Web_Frontend/API, 01_Documentation/Web_Interface.md, knowledge
page, CHANGELOG.md.
Risks: URL/state sync loops (mitigated by comparing formatted URLs and the
apply guard); TASK-48ddbb7d also edits App.tsx (no functional overlap; its
removal action remains pending); App.tsx size grows (pure modules keep logic
testable).
Open decisions: none. No architecture drawing owed: component boundaries
unchanged (two pure frontend modules and one API route within existing
components).

## Log

- 2026-10-03 frame: full path (URL scheme, navigation and audit paging interface changes; REQ-UX-749d37c8 revision for item 11); scope = review items 6-13; paused for scope acceptance and Q1-Q3.
- 2026-10-03 frame: scope accepted (items 6-13); Q1 path URLs (RULING-002), Q2 tabs + links (RULING-003), Q3 top-level My account revising REQ-UX-749d37c8 (RULING-004); interaction stays checkpoint; advanced to specify. stage-zone WARNs at frame cover earlier branch commits vs master (merge-base diff), not edits in this stage.
- 2026-10-03 design: user chose "Autopilot to validate" (RULING-005); interaction autopilot; advanced to build.
- 2026-10-03 build red: REQ-FUNC-a83c4cd3; command=`.venv\Scripts\python.exe -m pytest -q tests/test_web_paging.py`; exit=1; expected missing behavior=/api/v1/audit-page absent (404 not_found) and runs-page honours only the last lifecycle value.
- 2026-10-03 build green: REQ-FUNC-a83c4cd3; command=`.venv\Scripts\python.exe -m pytest -q tests/test_web_*.py`; exit=0; 172 passed (3 new paging tests; one test expectation corrected for newest-first ordering before green).
- 2026-10-03 build red: REQ-NFR-da638732; command=`node --test tests/polling.test.mjs` (in 04_Software/web); exit=1; expected missing behavior=interval keeps firing while hidden and no immediate refresh on becoming visible (polling.ts stub reproduces current setInterval behaviour).
- 2026-10-03 build green: REQ-NFR-da638732 (automated part); command=`node --test tests/polling.test.mjs`; exit=0; 4 passed; all 9 App.tsx pollers use startVisiblePolling; `npx tsc -b` exit=0. Manual network observation pending.
- 2026-10-03 build red: REQ-UX-4200375b; command=`node --test tests/routes.test.mjs` (in 04_Software/web); exit=1; expected missing behavior=no URL routing - stub maps every path to Overview and every view to "/" (5/5 fail).
- 2026-10-03 build green: REQ-UX-4200375b (automated part); command=`node --test tests/routes.test.mjs`; exit=0; 5 passed (one test corrected to the API run-ID alphabet before green). Frontend total `node --test tests/*.test.mjs` exit=0 (23 passed); `npx tsc -b` exit=0; `npm run build` exit=0.
- 2026-10-03 build manual observation: REQ-UX-4200375b, REQ-UX-d88d3d7f, REQ-UX-66e6f3f5, REQ-UX-749d37c8, REQ-UX-3dda4965, REQ-UX-02f35869, REQ-UX-5b0fa167, REQ-UX-48d6a55d, REQ-NFR-46c98d6c, REQ-NFR-da638732; method=Playwright-driven Chrome against a seeded local server (2 projects, 40 runs, 70 audit rows, developer on one project; scratch verify_ui2.py + locales2.py). First pass 37/41 exposed 3 candidate defects, fixed before green: GuidedField missed required children beside datalist/hint siblings; pager size change fetched once with the stale offset; auto-selection fetched another project before the unknown-project fallback. Final: 41/41 - deep link after sign-in, reload, Back/Forward, every route, job/metrics-tab deep links, unknown path and unknown/unassigned project fallbacks with localized not-found; tabs, keyboard, real link hrefs, Manage access; sidebar My account for both roles; placeholders 5.15:1 light, 5.60:1 system and explicit dark, italic with en/fr/de/ro prefixes; 8/8 required markers + legend, add-user 7-char tooShort with rule text in 4 locales; Audit requests limit=10 offsets then one limit=all; Overview failed/review tables request bounded pages with combined lifecycles; 0 API requests during 20 s hidden, immediate refresh on return; 390px scroll shadow both edges, Jobs Filters (0)/(2) with results at 542px; desktop unchanged.
- 2026-10-03 build: docs updated (Web_Interface.md URLs/tabs/My account/phone/forms; Component_Web_Frontend/API; knowledge page; CHANGELOG); `ruff check adore tests` exit=0; rebuilt assets written CRLF by 02_Tools/stamp_web_assets.py were normalized to LF (out-of-scope tooling issue offered as a separate task). Evolution: 19 files (6 added, 11 modified, 2 removed superseded bundle hashes), all in the design expected list. Check: errors=0; WARNs = merge-base stage-zone/secret-in-diff false positives (password-named keys, generated bundle), pre-existing journal/layout findings, and this journal Handoff (refreshed now). Build complete; advancing to validate under autopilot (RULING-005).
- 2026-10-03 validate: review disabled ([review] absent). Semantic diff review against scope/requirements/design: backend matches spec (audit-page bounds, admin guard, repeatable lifecycle); frontend matches design (state/URL sync, tabs, links, nav, ServerPager, polling, forms, CSS). Review fixes: store offset error text "invalid audit offset"; removed RunTable paged option left without callers; rebuilt bundle (assets LF-normalized). Requirements re-read: 11 active, prose/verification/paths/links current; REQ-UX-749d37c8 and REQ-UX-66e6f3f5 revisions per RULING-003/004. Knowledge page, Frontend/API contracts, operator guide and changelog reconciled; project.md/environment.md unchanged and accurate.
- 2026-10-03 validate manual observation (final bundle): reseeded local server; verify_ui2.py 41/41 and locales2.py ALL OK (en/fr/de/ro prefixes, legends, password rule; explicit dark placeholder 5.6:1).
- 2026-10-03 validate final: command=`python .agentic/aegis.py check --task TASK-87ebb7d6 --strict --run`; exit=0; test (full offline pytest) ok 45.4s, lint (ruff) ok, frontend (node --test web/tests/*.test.mjs) ok; errors=0, warnings=4: generated index-D5AdO2Y8.js not content-scanned; TASK-86c3ea11 tracked sidecars and TASK-5e99ee1d/TASK-c765e6b4 journal headers predate this task. Evolution refreshed after the last candidate edit (19 files). Validate complete; advanced to deliver; stopping before publication (RULING-005).
- 2026-10-03 deliver: validation evidence, diff, exclusions and outcome presented; user approved "Deploy to DCP, then commit": outcome = DCP deployment of the validated candidate, then one repository-local commit (no push/PR).
- 2026-10-03 deliver DCP: archive SHA-256 2c59a860431625e6f720a30040342dbd158a8d49bbe904d5ac64abb81d7ae7bd verified on host; pre-flight live app.py/store.py matched base f2a5775, schema 13, 0 running operations; backups suffix .pre-items-6-13-20261003221753 (app.py, store.py, static, web.db); web then worker restarted; /api/v1/audit-page signed-out -> authentication_required; both services active. Live checks from 192.168.1.117: /, /projects, /projects/<id>/configuration, /jobs?project&run, /admin/audit, /account -> 200 text/html; index serves index-D5AdO2Y8.js/index-e4LmLMxb.css; CSS --placeholder #617169/#8fa197; health/ready 200.
- 2026-10-03 deliver close-out: DCP deployment succeeded; stage done; this repository-local commit carries the candidate, requirements, specs, journal and report (no push or PR requested).

## Rulings

- RULING-001 | date=2026-10-03 | decision=work stays on task/adore-web-interface; TASK-48ddbb7d is not modified | reason=continuation of the web review on the same branch | source=user | supersedes=none
- RULING-002 | date=2026-10-03 | decision=use path URLs (e.g. /projects/<id>/configuration, /jobs?project=<id>) for every view | reason=user answered Q1 | source=user | supersedes=none
- RULING-003 | date=2026-10-03 | decision=Project details uses tabs Overview, Configuration and Prices (admins); Jobs and Metrics are links to those pages; Assigned projects becomes Manage access for admins | reason=user answered Q2 | source=user | supersedes=none
- RULING-004 | date=2026-10-03 | decision=both roles use a top-level My account entry; Administration keeps System status, Users and Audit; this revises REQ-UX-749d37c8 | reason=user answered Q3 | source=user | supersedes=none
- RULING-005 | date=2026-10-03 | decision=autopilot through build and validate, then stop before deliver (DCP deploy + local commit) | reason=user chose "Autopilot to validate" at the design checkpoint | source=user | supersedes=none

## Handoff


current: done
status: ready
next: none - delivered; DCP runs the candidate and the local commit records it
must_read: .agentic/tasks/TASK-87ebb7d6.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: validated candidate deployed to DCP and committed locally on task/adore-web-interface
evidence: check --strict --run exit=0; DCP deploy verified (path URLs 200, new assets, audit-page live, health/ready 200, services active)
issues: none open
next: none
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

## Delivery report (2026-10-03)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-4200375b - Address every web view by a stable URL
  - REQ-UX-d88d3d7f - Organize project details into tabs with consistent navigation
  - REQ-UX-66e6f3f5 - Project details show guided configuration to assigned developers
  - REQ-UX-3dda4965 - Distinguish example placeholders from entered values
  - REQ-UX-02f35869 - Mark required fields and state password rules
  - REQ-UX-749d37c8 - Localized responsive web interface
  - REQ-UX-5b0fa167 - Signal horizontal table scrolling on narrow screens
  - REQ-UX-48d6a55d - Show Jobs results before filters on phones
  - REQ-NFR-da638732 - Pause background refresh while the page is hidden
  - REQ-FUNC-a83c4cd3 - Serve audit and job history one page at a time
  - REQ-NFR-46c98d6c - Request one table page at a time for Overview and Audit
- deviations: none recorded
- explicit review: disabled; existing validation remains required
- diff vs task base f2a5775: 34 file(s) changed, 1530 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=5 notes=24
- checklist: 5/6 done; open: close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
