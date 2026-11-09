<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-10a21cc3 - Concise project directory and unified project hub

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-78923e00, REQ-UX-3b7dd34e, REQ-UX-772cb418
parent:
branch: task/adore-web-interface
base: c9f115b83ce0389dbb58f6c50a5a26b74ea7ae9f
opened: 2026-10-06

## Done checklist (current stage)

- [x] Validated candidate unchanged and both reviews approved
- [x] Evidence, diff, exclusions and delivery outcome presented
- [x] Standing human commit/push/deploy authority recorded
- [x] Journal/report committed and scoped branch pushed
- [x] Existing DCP deployment and smoke succeed
- [x] Close-out committed after outcome

## Frame

Problem: STATED project directory exposes redundant columns/actions and project hub repeats identity and Jobs/Statistics navigation.
Desired outcome: directory shows Repo forge type; single project identity/navigation band; actions on dedicated Summary only.
Actors: administrator and assigned developer.
Primary scenario: open Projects -> select project -> Summary or scoped Jobs/Statistics; administrator performs existing project actions.
Examples: supplied screenshot shows three navigation groups and two identity panels.
Counterexamples: developer must not gain administrative actions; delete confirmation must never carry into another project.
In scope: directory presentation, existing hub navigation/action placement, tests/docs/assets and existing DCP deployment.
Out of scope: backend lifecycle changes, live project mutations/probes, epic continuation, full suite.
Constraints: four hours, three fix cycles, twenty authored files; no subagents; English artifacts/Romanian discussion; full suite explicitly deferred by user.
Success signals: requested column and navigation order; one identity; scoped routes and role protections; exact-name archived delete confirmation.
Evidence: OBSERVED App.tsx projectContext, projectDetails, directory/action handlers; routes.ts legacy URLs; jobs.spec.ts role and keyboard journeys; component web-interface.md. STATED current request and standing iteration/deploy authorization.
Assumptions: Repo means forge provider in addition to existing repository path; Summary owns lifecycle actions.
Unknowns: human visual acceptance after deployment.
Decision-blocking questions: none.
Proposed behaviors: consolidate authorized presentation and relocate existing commands without new capabilities.
Path and reason: full; navigation and action placement change observable behavior.

## Requirement coverage

| Requirement | Frame outcome | Design and test seam |
| --- | --- | --- |
| REQ-UX-78923e00 | Unified project hub navigation and Summary actions | App.tsx single identity/nav, Summary actions; jobs.spec.ts directory/hub, role, keyboard and lifecycle boundaries |

| REQ-UX-3b7dd34e | Read-only directory columns | Existing SortHeader/PagedTable; hub and shell journeys |
| REQ-UX-772cb418 | Dedicated exact-name deletion | Current project/archive guards; offline lifecycle/Dev journeys |

## Design

REQ-UX-78923e00, REQ-UX-3b7dd34e, REQ-UX-772cb418: App owns directory, consolidated identity/navigation, and existing administrative handlers. Directory retains repository path and adds explicit forge brand; no mutation controls there.
Use existing project-context header for dedicated-page identity plus existing tab buttons and scoped Jobs/Statistics links ordered Summary, Settings, Prices, Access, Jobs, Statistics, History. Keep five local tabs/keyboard endpoints and existing route URLs. Common context on scoped Jobs/Statistics remains available.
Summary owns concise monitoring/runtime/verification evidence and administrative pause/resume/archive/restore/delete. Existing API owns RBAC, CSRF, archived/idle preconditions and queue semantics. No backend or persistence changes.
Clear deletion target on page OR project changes; render only matching selected ID and administrator; reject stale/mismatched confirmation before POST.
Failure uses existing alerts and operations evidence; no readiness probes during deployment. All checks offline except authorized delivery/service smoke. Existing endpoints preserve rollback compatibility; no architecture boundary changes.
Tests attach to offline browser fixtures: columns/order, single band, action absence/dedicated presence, scoped links, role denial, narrow keyboard, archive/restore and exact-name/mismatched-scope delete.
Alternative separate identity and navigation panels retains clutter, rejected by stated layout. Risks: wrapping long repo paths and role-dependent navigation; test narrow layout and roles. Open decisions: none.
Expected authored files: App.tsx, styles.css, e2e/jobs.spec.ts, Web_Interface.md, Component_Web_Frontend.md, CHANGELOG.md, web-interface knowledge, existing requirement/spec. Generated runtime assets separately.

## Log

- 2026-10-06 frame/specify/design: scope and full path audited; REQ-UX-78923e00 reconciles user-authorized presentation changes; design above preserves API/state/URLs and role boundaries. Standing human authority covers stage continuation, reviewed normal commit/push and existing DCP deployment; full regression deferred, no subagents.

- 2026-10-06 build red: REQ-UX-78923e00; command=`npx playwright test e2e/jobs.spec.ts --grep "hub separates"`; exit=1; expected missing behavior=directory still exposes Environment verification (count1 rather than0).

- 2026-10-06 build green: UI/E2E typecheck+isolated build exit0; `npx playwright test e2e/jobs.spec.ts e2e/shell.spec.ts --grep "hub separates|project hub lifecycle|keyboard 390px|developer search|shell links, project context"` exit0;5passed51.9s. Directory absence/Repo, single ordered hub, scoped routes/Back, keyboard/390px/themes/fourlocales, Dev denial, offline archive/restore/exact-name delete/CSRF/project-change reset covered. No live project mutations.
- 2026-10-06 validate: production `npm --prefix 04_Software/web run build` exit0; assets index-BGYvxp2C.js/index-bsaPN9pm.css. Desktop screenshot inspected: single name/path+seven-control band, Summary lifecycle/status, no duplicated identity/navigation panel. Source/requirement/spec/docs hunk review confirms unchanged API, supported routes, CSRF/role boundaries and authoritative archive/idle preconditions. Project/environment and component architecture responsibilities remain accurate; no context/architecture changes needed. Legal headers preserved. Vite existing bundle-size advisory retained.
- 2026-10-06 reviews: specification compliance approved and implementation quality approved for candidate SHA256 0dbcf5207d4080b8e791a3b9f0dec28790e279718bcdee4eab48b974f30206f7; separate same-agent review lenses, round1, no independent-agent claim. Candidate 9 authored paths plus journal and generated assets; no children/subagents. Deletion intent guarded by current immutable project identity and current archived state.
- 2026-10-06 DEVIATION validate: required full suite/check--run deferred by explicit human instruction; targeted browser/build proof does not establish full backend/frontend regression coverage.

- 2026-10-06 validate reconciliation: user explicitly supersedes prior row-action placement; updated REQ-UX-3b7dd34e directory and REQ-UX-772cb418 delete placement, preserving sorting/paging/queue/API preconditions. Inspection confirms unchanged SortHeader/PagedTable invocation and paging implementation. Prose-only changes require no further runtime tests; final candidate reviews refreshed below.

- 2026-10-06 final reviews/proof: both separate same-agent verdicts approved/round1 for reconciled candidate SHA256 612d9ff244c4acc78fc0c89a3a656c118debccebc74a62728a9769182c78cf30. Eleven authored paths plus journal; generated five-path asset replacement separate. `git diff --check` exit0; final browser5passed51.9s, typecheck/build exit0 unchanged. Catalog-only `check --task TASK-10a21cc3 --strict --json` exit0/0errors7warnings25notes/strictpassed/run[]. Accepted baseline tracked fingerprints and four legacy journal warnings, configured test globs omitting e2e (five real journeys explicitly run), large generated JS scan gap supplemented by exact source review. Full suite deferred per stated deviation.
- 2026-10-06 deliver: concrete candidate and5test/build results presented; standing human authority covers normal commit/push and existing DCP deployment. No PR/version/epic continuation/live project acceptance.

- 2026-10-06 delivered: product af377de962adba5d02411fd755d5f02f478765bd normally pushed/remote ref verified; deployed /home/dpasare/apps/adore/web-ux-af377de, archive SHA25675988dfe8e40c3f957b4b5341e0b9a63340df3d5e7bbf7896d3f1629238094cb. Backup /home/dpasare/apps/adore/backups/web-ux-af377de-20261006135936. Both service PYTHONPATHs point to exact new release; served JS/CSS bytes match. Database schema14/integrityok/audit49 retained. After completed deploy: root200newindex, health200alive, ready200workerready, projects401authentication_required. No live project lifecycle/probe/executor mutations performed. Human visual acceptance/fullsuite deferred; epic remains paused.

## Rulings

- RULING-001 | date=2026-10-06 | decision=Scoped implementation through validation, normal commit/push and existing DCP deployment with targeted checks | reason=Direct request plus standing iteration authority; human expressly defers full suite | source=user | supersedes=none

## Handoff

current: done
status: ready
next: human live visual testing
must_read: 04_Software/web/src/App.tsx, 04_Software/web/e2e/jobs.spec.ts
blockers: none

## Stage report

stage: done
result: completed
current: done
changed: concise directory, unified hub and scoped Summary lifecycle actions
evidence: typecheck/build exit0;5focused journeys passed; exact product pushed/deployed; services/assets/HTTP smoke verified
issues: full suite deferred by human; existing bundle-size advisory
next: human live visual testing
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-06)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-78923e00 - Concise project directory and role-appropriate project hub
  - REQ-UX-3b7dd34e - Sort and page a read-only authorized project directory
  - REQ-UX-772cb418 - Confirm project deletion by typing its name
- deviations: 1 recorded
  - validate: required full suite/check--run deferred by explicit human instruction; targeted browser/build proof does not establish full backend/frontend regression coverage.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base c9f115b: 17 file(s) changed, 285 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=8 notes=25
- checklist: 3/6 done; open: Journal/report committed and scoped branch pushed; Existing DCP deployment and smoke succeed; Close-out committed after outcome
