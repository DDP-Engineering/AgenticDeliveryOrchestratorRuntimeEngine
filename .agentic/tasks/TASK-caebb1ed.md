<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-caebb1ed - Simplify and sort the Jobs table

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-77d3aa97, REQ-FUNC-dd0820ea, REQ-UX-c65b3022
parent:
branch: task/adore-web-interface
base: c21691f88ea30dc12bdeeace94f0cc7ff517961c
opened: 2026-10-12

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: the Jobs table presents information badly - the consumption column repeats project ID and run ID while the ticket column already names the project, lifetime and "selected period" token blocks carry measurement labels, the run ID sits under each title, a "Selected period: All time -> All time · UTC · day" line links to Statistics, and the columns cannot be sorted (STATED: "the information is not presented well ... User is interested in project name. Also - what is the selected period here? Please review and rearrange ... remove the Selected period ... The jobs page - show you the jobs, statuses - from the table you can sort them via column sorting .. thats the main goal").
Desired outcome: a compact table - Ticket (#n · title) | Project (name) | Status (badge, stage, next action) | Last activity | Consumption (lifetime input/output tokens) - sortable by Ticket, Project, Status and Last activity on the server; no reporting period anywhere in Jobs; identifiers only in job details.
Actors: administrators and developers on the global Jobs page and the hub Jobs/History tabs.
Primary scenario: open Jobs -> rows newest activity first -> click Project -> server returns the list sorted by project (ascending, then descending on a second click) -> open a job -> details with lifetime tokens.
Examples: nilo #26 row (Project ID/Run ID in consumption, Lifetime and Selected period blocks).
Counterexamples: search, status filter, paging, snapshot conflicts and detail evidence stay; unknown tokens stay a dash, measured zero stays 0; Overview compact table unchanged.
In scope: jobs-page sort/order, JobWorkspace table/detail consumption, JobAmounts lifetime-only, shared SortHeader, removal of reporting props from JobWorkspace, copy cleanup, tests, requirements, docs.
Out of scope: Statistics and metrics APIs; full suite (STATED: at the end).
Constraints: REQ-UX-c65b3022 keeps collision-free identity (now in details) and unknown/zero semantics; jobs-page snapshot paging must stay consistent under a sort.
Success signals: pytest and e2e show server sorting and the compact columns; DCP shows them.
Evidence: OBSERVED JobWorkspace table() (statistics-job-scope line, run_id hint, reason text, activity age, consumptionView with JobAmounts), consumption effect reading selected-period and all-time usage; jobs.py read_jobs orders by last activity only; app.py jobs_page has no sort.
Assumptions: sorting by tokens is not offered because consumption comes from a separate usage read (INFERRED; the four sortable columns cover the stated goal); outcome text stays in job details.
Unknowns: none blocking. Decision-blocking questions: none.
Proposed behaviors: B1 compact columns without identifiers/period (REQ-UX-77d3aa97); B2 server sort before paging (REQ-FUNC-dd0820ea); B3 lifetime-only consumption in rows and details (REQ-UX-c65b3022 revised).
Path and reason: full - backend API addition and observable UI change.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| readable rows | B1 five compact columns | REQ-UX-77d3aa97 (new) | nilo-like rows show name, status, time, tokens | unknown tokens dash | e2e jobs.spec | D3 |
| sort by column | B2 server sort/order | REQ-FUNC-dd0820ea (new) | project asc/desc, status, ticket, activity | invalid values 422; paging keeps order | pytest test_web_jobs; e2e | D1, D2 |
| no period confusion | B3 lifetime-only consumption | REQ-UX-c65b3022 (revised) | lifetime tokens in row and detail | missing job evidence unavailable | e2e jobs/statistics | D4 |

## Design

- D1 jobs.py `sort_jobs(rows, key, descending)`: stable base order by project_id/run_id, then the chosen key (activity instant, ticket iid+title, project display name, status group order then lifecycle) with unknown values last in both directions; jobs_page accepts `sort` (activity|ticket|project|status, default activity) and `order` (asc|desc, default desc for activity, asc otherwise) and sorts before counting/paging.
- D2 SortHeader moves to `src/SortHeader.tsx` (shared with the Projects table); JobWorkspace filters gain sort/descending, the query sends sort/order, and a header click toggles direction or selects the column with its default direction (resetting the offset).
- D3 JobWorkspace table: Ticket link "#n · title" (no run ID), Project name (+archived), Status badge + stage + next action link (outcome text only in details), Last activity time (age hint only in details), Consumption = lifetime input/output tokens; the Selected period line is removed.
- D4 consumption reads only all-time usage per visible project; JobAmounts shows lifetime tokens (and in details total, Admin reported/estimated, observations) with plain values or a dash; JobWorkspace drops the reporting/reportingQuery props; unused statistics copy removed.
- Test seams: tests/test_web_jobs.py (sort, invalid values), e2e/jobs.spec.ts (columns, sort, detail), e2e/statistics.spec.ts job-list test (lifetime only).

## Log

- 2026-10-12 frame: scope accepted from the user request (rearrange the Jobs table, remove the selected period, sortable columns as the main goal); autopilot as in prior refinements; full path; full suite deferred by user.
- 2026-10-12 specify: 2 created (REQ-UX-77d3aa97, REQ-FUNC-dd0820ea), 1 revised (REQ-UX-c65b3022 lifetime only); 0 retired.
- 2026-10-12 design: see ## Design D1-D4.
- 2026-10-12 build red: REQ-FUNC-dd0820ea, REQ-UX-77d3aa97, REQ-UX-c65b3022 command=`pytest -q tests/test_web_jobs.py` exit=1 (3 failed: sort test, sort=bogus and order=up accepted) and `npx playwright test e2e/jobs.spec.ts e2e/statistics.spec.ts -g "compact columns|lifetime consumption without|missing evidence and stale"` exit=1 (3 failed); expected missing behavior=no server sort, Selected period line, identifiers and measurement labels in rows, selected-period consumption in details.
- 2026-10-12 build green: pytest tests/test_web_jobs.py 79 passed; ruff clean; `npx tsc -b` + e2e typecheck clean; unit 82; e2e jobs+statistics+shell+dashboard+tickets 72/73 at first (the collision test matched run IDs in consumption text; now uses data-identity), then that test passed (REQ-FUNC-dd0820ea, REQ-UX-77d3aa97, REQ-UX-c65b3022). sort_jobs + jobs_page sort/order; shared SortHeader.tsx; compact table; lifetime-only JobAmounts and consumption read; reporting props removed from JobWorkspace; 10 statistics copy keys removed; docs/specs/CHANGELOG updated.
- 2026-10-12 validate review round 1: implementation-quality - dead statistics copy key source and .job-amount CSS (removed; vestigial Technical details click and day_from mock branch also removed); spec-compliance FAIL - REQ-UX-c65b3022 title and verification still described selected-period labels - fixed; the e2e now also asserts lifetime tokens in the row (minor note).
- 2026-10-12 validate review round 2: spec-compliance PASS (reproduced pytest 79); implementation-quality PASS.
- 2026-10-12 validate final: `python .agentic/aegis.py check --task TASK-caebb1ed --strict` errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by pytest test_web_jobs 79, ruff, tsc (src + e2e), unit 82 and e2e jobs+statistics 47 (73 across jobs/statistics/shell/dashboard/tickets before the review fixes). Backend+frontend deployed to DCP via deploy-backend.sh (ready 200, UI 200, services active; backup adore.pre-cae-20261012095242), frontend refreshed after the review fixes.
- 2026-10-12 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-12 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-caebb1ed.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Jobs table shows Ticket, Project, Status, Last activity and lifetime token Consumption, sortable on the server by Ticket/Project/Status/Last activity (jobs-page sort/order); Selected period line, selected-period consumption, identifiers, outcome text and activity-age hints removed from rows; job details show lifetime consumption
evidence: pytest test_web_jobs 79; ruff clean; tsc clean; unit 82; e2e jobs+statistics 47; review round 2 PASS/PASS; deployed to DCP (backend+frontend)
issues: DEVIATION full suite deferred by user; consumption column not sortable (separate usage read)
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-12)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-77d3aa97 - Show the Jobs table as compact sortable columns
  - REQ-FUNC-dd0820ea - Sort the job list on the server before paging
  - REQ-UX-c65b3022 - Present composite job lifetime consumption
- deviations: 1 recorded
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by pytest test_web_jobs 79, ruff, tsc (src + e2e), unit 82 and e2e jobs+statistics 47 (73 across jobs/statistics/shell/dashboard/tickets before the review fixes). Backend+frontend deployed to DCP via deploy-backend.sh (ready 200, UI 200, services active; backup adore.pre-cae-20261012095242), frontend refreshed after the review fixes.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base c21691f: 22 file(s) changed, 350 line(s) added
- checks: errors=0 warnings=10 notes=22
- checklist: 6/6 done
