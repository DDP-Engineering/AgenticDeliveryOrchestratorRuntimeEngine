<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-74c348fe - Remove advanced job filters and reorder project hub tabs

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-FUNC-25dc0271, REQ-UX-e96a5dd4, REQ-UX-3dda4965, REQ-UX-48d6a55d, REQ-UX-d88d3d7f, REQ-UX-78923e00, REQ-UX-b758d2b7
parent:
branch: task/adore-web-interface
base: bcd57bfe7b5bd893a47be24dc5d0844029a86638
opened: 2026-10-11

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: The Jobs list offers granular "Advanced filters" (exact status, stage, observed executor, outcome text, update dates) the user does not need; few tickets exist and a person follows them (STATED). The hub tab order should end with Access (STATED: "summary, settings, jobs, statistics, history, access").
Desired outcome: Jobs keeps only search and the status group filter; the advanced UI and its API parameters/validation are removed; hub tabs read Summary, Settings, Jobs, Statistics, History, Access.
Actors: administrator and developer using the Jobs list (global page and hub Jobs sub-tab); API clients of /api/v1/jobs-page.
Primary scenario: user opens Jobs -> sees search + Status only; no Advanced filters button; project hub shows tabs in the new order.
Examples: hub admin tabs Summary, Settings, Jobs, Statistics, History, Access; developer tabs without Access.
Counterexamples: History still shows only terminal jobs; Overview attention list unchanged; the legacy /projects/{name}/runs-page endpoint keeps its own filters (not used by the web UI).
In scope: JobWorkspace advanced panel/state/query keys, copy keys and CSS used only there; jobs-page lifecycle/stage/executor/outcome/updated_from/updated_to parameters, validation, clauses and the observed_executors projection; tests; requirement retirement/revision; docs; App.tsx tab order.
Out of scope: runs-page filters (separate legacy API, OBSERVED unused by the web app); journal executor validation (integrity); full suite (STATED: at the end of refinements).
Constraints: keep q, status_group, attention, pagination, History terminal filter (OBSERVED JobWorkspace.tsx:36, app.py:3880-3884).
Success signals: no Advanced filters in UI; jobs-page ignores removed parameters; focused tests green; tab order in e2e; DCP shows it.
Evidence: OBSERVED Explore report (JobWorkspace.tsx:35-36,59,138-139,265-272; app.py:3822-3893,3896,3920; jobs.py:362-363; tests test_web_jobs.py:72-98,109,151,256-257; e2e jobs.spec.ts:222,242-246; REQ-FUNC-25dc0271, REQ-UX-e96a5dd4).
Assumptions: unknown query parameters are ignored by FastAPI, so old clients get unfiltered results rather than errors.
Unknowns: none blocking. Decision-blocking questions: none.
Proposed behaviors: B1 Jobs filters = search + status group (REQ-UX-e96a5dd4 retired, REQ-FUNC-25dc0271 revised to timeline only, spec b758d2b7); B2 hub tab order (REQ-UX-d88d3d7f, REQ-UX-78923e00, spec b758d2b7).
Path and reason: full - removal of observable UI/API behavior and requirement retirement.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| simpler Jobs | B1 no advanced filters; timeline detail kept | REQ-FUNC-25dc0271 (revised), REQ-UX-e96a5dd4 (retired), REQ-UX-3dda4965/48d6a55d (verification text) | search + status filter results | removed params ignored; History terminal kept | pytest test_web_jobs + e2e jobs.spec | D1 |
| tab order | B2 Summary, Settings, Jobs, Statistics, History, Access | REQ-UX-d88d3d7f, REQ-UX-78923e00, spec REQ-UX-b758d2b7 | admin order | developer without Access | e2e jobs.spec hub | D2 |

## Design

- D1: delete the advanced panel, `advanced` state, six Filters fields and their query keys in JobWorkspace.tsx; drop advanced-only copy keys (jobCopy `advanced`; i18n observedExecutor/observedExecutorHelp/outcomeContainsHelp/updatedFrom/updatedTo/outcomeContains) and `.job-text-filters` CSS; in app.py jobs-page remove the six parameters, their validation and filter clauses and the observed_executors stripping; in jobs.py remove the observed_executors projection. Keep errors.ts codes still raised by runs-page/analytics.
- D2: App.tsx projectTabs admin order overview, configuration, jobs, statistics, history, access.
- Test seams: tests/test_web_jobs.py (remove filter assertions, keep timeline/redaction; add a test that removed parameters no longer filter), e2e/jobs.spec.ts (no Advanced filters button; hub order).
- Expected files: web/src/{JobWorkspace.tsx,App.tsx,jobCopy.ts,i18n.ts,styles.css}, adore/web/{app.py,jobs.py}, tests/test_web_jobs.py, web/e2e/jobs.spec.ts, docs.

## Log

- 2026-10-11 frame: <scope agreed, exclusions, chosen path and why>
- 2026-10-11 build red: REQ-FUNC-25dc0271/REQ-UX-e96a5dd4 command=`.venv/Scripts/python.exe -m pytest -q tests/test_web_jobs.py` exit=1 (removed parameters still filter); REQ-UX-d88d3d7f/REQ-UX-78923e00 and advanced panel command=`npx playwright test e2e/jobs.spec.ts -g "basic filters|hub separates"` after build:e2e exit=1; expected missing behavior=Advanced filters button present and Access before Jobs in the hub.
- 2026-10-11 build green: ruff clean; `.venv/Scripts/python.exe -m pytest -q tests/test_web_jobs.py tests/test_web_rbac.py tests/test_web_paging.py tests/test_web_archive.py tests/test_web_tickets.py` 137 passed; `npx tsc -b` clean; `node --test tests/*.test.mjs` 79 pass; e2e jobs+shell+tickets+dashboard+statistics 67 passed with the keyboard End test then updated (End now reaches Access for administrators), jobs.spec rerun 33 passed (REQ-FUNC-25dc0271, REQ-UX-d88d3d7f, REQ-UX-78923e00; REQ-UX-e96a5dd4 retired). Removed: advanced panel/state/query keys, six copy keys x4 locales, `advanced` jobCopy key, .job-text-filters CSS, jobs-page lifecycle/stage/executor/outcome/updated_from/updated_to parameters/validation/clauses and the observed_executors projection; docs and spec reconciled.
- 2026-10-11 validate review round 1: implementation-quality PASS (applied: two-column basic filter grid; active-filter detection compares q/status group with the mode default instead of counting page size); spec-compliance FAIL on stale spec lines 21/31 in REQ-UX-b758d2b7, the renamed test link in REQ-FUNC-25dc0271 and trailing spaces in i18n.ts - all fixed. Proof: tsc clean; e2e jobs+shell+tickets 47 passed; pytest test_web_jobs 76 passed.
- 2026-10-11 validate review round 2: spec-compliance PASS, implementation-quality PASS (an empty History tab now says "No jobs yet" instead of the no-match message, as intended by the active-filter fix).
- 2026-10-11 validate final: `python .agentic/aegis.py check --task TASK-74c348fe --strict` (catalog only) errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by ruff, pytest (test_web_jobs/rbac/paging/archive/tickets 137, then test_web_jobs 76), tsc, unit 79 and e2e jobs/shell/tickets/dashboard/statistics. Deployed to DCP: backend+frontend package then frontend-only update; ready 200, UI 200, services active.
- 2026-10-11 deliver: user tested on DCP ("e ok") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-11 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-74c348fe.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Jobs advanced filters removed (UI, copy, CSS, jobs-page parameters/validation/clauses, observed_executors projection); hub tabs ordered Summary, Settings, Jobs, Statistics, History, Access; REQ-UX-e96a5dd4 retired; docs/specs reconciled
evidence: ruff clean; pytest 137 then 76 passed; tsc clean; unit 79; e2e jobs+shell+tickets 47 passed; review round 2 PASS/PASS; deployed to DCP
issues: DEVIATION full suite deferred by user; legacy /projects/{name}/runs-page keeps its own filters (out of scope)
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-11)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-25dc0271 - Return a validated redacted observed timeline in job detail
  - REQ-UX-e96a5dd4 - Explain and align Jobs text filters
  - REQ-UX-3dda4965 - Distinguish example placeholders from entered values
  - REQ-UX-48d6a55d - Show Jobs results before filters on phones
  - REQ-UX-d88d3d7f - Organize project details into tabs with consistent navigation
  - REQ-UX-78923e00 - Concise project directory and role-appropriate project hub
  - REQ-UX-b758d2b7 - present complete authorized scoped current-state
- deviations: 1 recorded
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by ruff, pytest (test_web_jobs/rbac/paging/archive/tickets 137, then test_web_jobs 76), tsc, unit 79 and e2e jobs/shell/tickets/dashboard/statistics. Deployed to DCP: backend+frontend package then frontend-only update; ready 200, UI 200, services active.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base bcd57bf: 22 file(s) changed, 184 line(s) added
- checks: errors=0 warnings=11 notes=22
- checklist: 3/6 done; open: journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
