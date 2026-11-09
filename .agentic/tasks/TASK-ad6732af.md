<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-ad6732af - Show Refresh only where pages do not update themselves

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-183b80f6, REQ-UX-8031b8eb, REQ-UX-257ab3f0
parent:
branch: task/adore-web-interface
base: 458e3f97506394a674031edecfecf86013e0ef91
opened: 2026-10-12

## Done checklist (current stage)

- [x] red records, anchor, implementation, focused green, links, docs, check clean
- [x] `stage: validate`

## Frame

Problem: the header Refresh (and "Last refreshed" stamp) appears on every page although Overview, Projects, Jobs, Statistics, System status and the project Summary/Jobs/Statistics tabs already refresh themselves every few seconds while visible (STATED: "Avem nevoie de butonul refresh din dreapta sus? Ce anume face?"; choice: "Doar unde e nevoie").
Desired outcome: Refresh + stamp only on Users, Change history and a project's Settings, Access and History tabs, which do not refresh themselves.
Actors: administrators and developers.
Primary scenario: Statistics/Jobs/Overview show no Refresh; Users/Change history/Settings/Access/History show Refresh and the stamp.
Examples: Statistics screenshot with Refresh.
Counterexamples: automatic polling unchanged (REQ-NFR-da638732, REQ-UX-257ab3f0 recovery happens on the next poll); About and glossary stay; Refresh still reloads everything on the pages that keep it.
In scope: App.tsx header actions, e2e tests, requirement, docs.
Out of scope: polling intervals; full suite (run at the end of the refinement round).
Constraints: tests that used Refresh on auto-refreshing pages trigger the poll by dispatching visibilitychange (startVisiblePolling ticks at once).
Success signals: e2e shows the button where needed only; DCP shows it.
Evidence: OBSERVED startVisiblePolling users (App.tsx projects 15s, selected 15s, metrics/usage 15-30s, ready 5s, storage 30s; JobWorkspace pages/details 15s); viewRefresh drives the non-polled loaders (users, audit policy, config, access, audit history).
Assumptions: none. Unknowns: none. Decision-blocking questions: answered.
Proposed behaviors: B1 conditional header Refresh/stamp (REQ-UX-183b80f6); B2 glossary wording (REQ-UX-8031b8eb revised).
Path and reason: full - observable UI change with a new requirement.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Refresh only where needed | B1 | REQ-UX-183b80f6 (new) | users/audit/settings/access/history show it | auto pages hide it | e2e shell.spec | D1 |
| recovery without the button | polling | REQ-UX-257ab3f0 | failed data recovers on the next poll | none | e2e shell.spec | D2 |

## Design

- D1 App: `manualRefresh` = adminUsers, adminAudit, or projectDetails with tab configuration/access/history; the header renders the stamp and Refresh only then; About and the glossary always.
- D2 e2e: `pollNow` dispatches visibilitychange to run the visible-page poll at once where tests used Refresh on auto-refreshing pages (jobs.spec overview and summary, shell.spec overview and jobs, statistics.spec revoked grant).

## Log

- 2026-10-12 frame: scope accepted (header Refresh only on pages without automatic updates; user's choice); autopilot; full path.
- 2026-10-12 specify: 1 created (REQ-UX-183b80f6), 1 revised (REQ-UX-8031b8eb wording); 0 retired.
- 2026-10-12 design: see ## Design D1-D2.
- 2026-10-12 build red: REQ-UX-183b80f6 command=`npx playwright test e2e/shell.spec.ts -g "header Refresh appears only"` exit=1; expected missing behavior=Refresh shown on auto-refreshing pages.
- 2026-10-12 build green: `npx tsc -b` + e2e typecheck clean; e2e shell+jobs+statistics+settings+audit 93/94 at first (the jobs paging test clicked Refresh on /jobs; switched to the poll trigger), then that test passed (REQ-UX-183b80f6, REQ-UX-8031b8eb, REQ-UX-257ab3f0). manualRefresh condition; pollNow (visibilitychange) in jobs/shell/statistics specs; docs/CHANGELOG updated.
- 2026-10-12 validate review round 1: spec-compliance FAIL - three docs still placed the help button beside Refresh and two said Refresh retries totals -> reworded (plus the stale Rebuild usage line in Component_Web_Frontend.md); project History inclusion judged acceptable; implementation-quality - usageRefresh dead and the stamp advanced with every projects poll -> usageRefresh removed, Refresh handler keeps refreshProjects + viewRefresh, the stamp is set when the page loaders run; System status audit policy kept without Refresh per the user's choice.
- 2026-10-12 validate review round 2: implementation-quality PASS; spec-compliance FAIL - on a project's History tab the header Refresh did not re-read the (non-polled) change history -> its AuditHistory is keyed with viewRefresh; shell.spec now counts audit-page reads for the project (red without the key: 1, green: >1); e2e shell+settings 40/40; tsc and e2e typecheck clean.
- 2026-10-12 validate review round 3: spec-compliance PASS (History AuditHistory keyed with viewRefresh; regression test verified at source); implementation-quality PASS (round 2, files unchanged since). Deployed to DCP as ad6c; full suite deferred by the user to the end of the refinement round.
- 2026-10-12 validate final: `python .agentic/aegis.py check --task TASK-ad6732af --strict` errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by tsc (src + e2e), e2e shell+jobs+statistics+settings+audit then shell+settings 40/40 after the History fix. Frontend deployed to DCP as ad6c (assets 200).
- 2026-10-12 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-12 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-ad6732af.md
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: header Refresh and "Last refreshed" only on Users, Change history and a project's Settings, Access and History tabs, each reloading its non-polled data; App.tsx (manualRefresh, usageRefresh removed, stamp set by page loaders, History AuditHistory keyed with viewRefresh); e2e jobs/shell/statistics specs; REQ-UX-183b80f6 (new), REQ-UX-8031b8eb; Web_Interface.md, Component_Web_Frontend.md, knowledge web-interface.md, CHANGELOG
evidence: e2e shell+settings 40/40, earlier shell+jobs+statistics+settings+audit green; tsc and e2e typecheck clean; red/green on the History reread assertion; DCP ad6c assets 200
issues: DEVIATION full suite deferred by user
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-10-12)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-183b80f6 - Show the header Refresh only on pages without automatic updates
  - REQ-UX-8031b8eb - Explain delivery vocabulary in every supported locale
  - REQ-UX-257ab3f0 - Distinguish pending empty and failed dashboard data
- deviations: 1 recorded
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by tsc (src + e2e), e2e shell+jobs+statistics+settings+audit then shell+settings 40/40 after the History fix. Frontend deployed to DCP as ad6c (assets 200).
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 458e3f9: 11 file(s) changed, 184 line(s) added
- checks: errors=0 warnings=12 notes=22
- checklist: 2/2 done
