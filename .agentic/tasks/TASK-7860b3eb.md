<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-7860b3eb - Web review polish: clickable names, card hints, icons, spacing, price default, metrics empty state

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-205e5379, REQ-UX-deb101f5, REQ-UX-48fb199d, REQ-UX-0c03fc93, REQ-UX-d93fab0f, REQ-UX-7fdffe77, REQ-UX-e6ed7168
parent:
branch: task/adore-web-interface
base: f1a80186f2e4cd75163513b585f053ff23a3e8fe
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

Problem: The 2026-10-03 review listed six polish items the user now asks to
fix (STATED: "now fix the polish items from the review"):
P1. Things that look clickable do nothing: project names in the Projects and
    Overview project tables; Overview card hints show a bare project name
    ("demo") and the Projects card repeats "Projects".
P2. The `⌄`/`⌃` chevron characters render like a lowercase "v".
P3. The sidebar sign-out control is a `↗` glyph, the same arrow used for
    external links.
P4. Card headings sit directly on the first form label (Add user,
    Appearance, Audit retention, Change password) and the sign-in Language and
    Theme controls touch.
P5. The Prices form defaults the executor to `codex` even for an `opencode`
    project.
P6. Metrics with no jobs in scope shows about 17 cards of zeros.

Desired outcome: links where users expect them, card hints that explain
their number, unambiguous icons, consistent spacing, a sensible price
default and a single helpful message when metrics have nothing to show.

Actors: administrator and developer, desktop and phone.

Primary scenario: administrator opens Metrics for a new project -> sees one
localized "no jobs yet" message instead of zero cards -> starts a job ->
returns to Metrics and sees the usual cards.

Examples:
- P1 clicking "alpha" in Projects opens `/projects/<id>`; middle-click opens
  a new tab; Overview "Active jobs 3 / Project: alpha".
- P5 Prices on an opencode project preselects opencode.
- P6 empty scope -> one message with a pointer to Jobs; any job -> cards.

Counterexamples: no layout redesign; View actions stay (REQ-UX-3b7dd34e);
Metrics period/export controls stay visible; "unknown is not zero"
semantics unchanged.

In scope: P1-P6 in `04_Software/web/src` (App.tsx, i18n.ts, styles.css),
rebuilt bundle, docs, knowledge, changelog, DCP deployment after validation.

Out of scope: TASK-48ddbb7d removal semantics; default admin/admin
hardening; `02_Tools/stamp_web_assets.py` line endings (separate suggested
task); API changes (none needed - INFERRED).

Constraints: REQ-UX-3b7dd34e keeps per-row actions (names add a second way
in); REQ-UX-15ad4473 keeps card expansion; REQ-FUNC-448cbde7 keeps unknown
values distinct (empty state only when the scope has no jobs at all);
offline bundle (icons inline, no icon font/CDN); 4 locales; LF writes.
Review policy now enabled in `.agentic/aegis.toml` (OBSERVED: `[review]
enabled = true`, `max_fix_cycles = 4`, changed outside this session) -
validate records two verdicts.

Success signals: browser checks for each item in light/dark and 390/1440
widths; frontend tests and full strict check green; DCP live.

Evidence:
- OBSERVED: card hints `hint={t("projects")}` / `hint={selectedProject?.name}`
  (App.tsx OverviewCard calls); chevrons `"⌄"`/`"⌃"`/`"›"`, sign-out `>↗<`
  (App.tsx); price `<select name="executor">` first option codex; `h2
  { margin: 0 }` and `.login-preferences` without inner gap (styles.css);
  Metrics Summary renders Stat grids unconditionally (App.tsx ~1115-1146).
- OBSERVED: REQ-FUNC-448cbde7 requires distinct unknown values and null
  ratios; it does not require cards for an empty scope.
- STATED: user asked to fix the polish items.

Assumptions: inline SVG icons drawn with `currentColor` suit both themes.

Unknowns: none blocking beyond the questions below.

Decision-blocking questions:
- Q1 Overview card hints: "Projects you can access" on the Projects card and
  "Project: <name>" on job cards [recommended], or remove the hints.
- Q2 Clickable items: project names (Projects + Overview) and ticket numbers
  in job tables become links [recommended], or project names only.
- Q3 Metrics empty state: one message on Summary, Quality and Trends when the
  scope has no jobs [recommended], or Summary only.

Proposed behaviors:
- B1 project-name and ticket links; scoped card hints -> P1.
- B2 SVG chevron and sign-out icon -> P2/P3.
- B3 heading and preference spacing -> P4.
- B4 price executor defaults to the project's executor -> P5.
- B5 metrics empty state -> P6.

Path and reason: full path.
criterion | yes | no | evidence
no new externally observable behavior | | no | new links, empty state, defaults
no new interface or data format | yes | | UI only
no new dependency | yes | | inline SVG
existing requirement covers behavior | | no | no requirement for these details
no security/data-handling change | yes | | display only

Children: none - six small changes in the same files.

## Requirement coverage

Behavior inventory (positive | boundary/failure): P1 links open details/jobs and URLs | Overview name still selects, modified click new tab; P1 hints | no project -> dash; P2/P3 icons flip with state, exit icon named Sign out | external arrow only on external links; P4 >= 12px gaps | 390px; P5 project executor preselected | unknown executor -> first option, project switch resets; P6 single message | scope with jobs shows cards and dashes for unknown.

Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact
---|---|---|---|---|---|---
P1 | names/tickets/View open details or job | REQ-UX-205e5379 (new) | link + in-app navigation | modified click new tab; Overview name selects | manual browser | RouteLink in Projects/RunTable; RunTable opens via Jobs
P1 | card hints explain counts | REQ-UX-deb101f5 (new) | localized hints | no project -> dash | manual browser | i18n hint keys
P2/P3 | drawn chevrons and exit icon | REQ-UX-48fb199d (new) | icons flip with state | no external arrow for sign-out | inspection | inline SVG Icon component
P4 | heading/preference spacing | REQ-UX-0c03fc93 (new) | >= 12px | 390px | inspection | CSS margins/gap
P5 | price executor default | REQ-UX-d93fab0f (new) | project executor | missing executor; project switch | manual browser | keyed form defaultValue
P6 | metrics empty state | REQ-UX-7fdffe77 (new) | single message | scope with jobs unaffected | manual browser | hasJobs guard per tab

## Design

Requirements coverage and decisions (all in `04_Software/web/src`):
- REQ-UX-205e5379: Projects-table name cell renders `RouteLink` to
  `formatRoute({view: "projectDetails"})` with `openProject`. `RunTable` gains
  a `project` prop; its ticket cell becomes a `RouteLink` to
  `formatRoute({view: "jobs", project, run})` and both the ticket link and View
  call one `openJob(runId)` = `openRun` + `setPage("jobs")`, used by Overview,
  Project details Recent jobs and Jobs (on Jobs the page is already Jobs).
  Overview projects-table names keep their selection button (REQ-UX-15ad4473).
- REQ-UX-deb101f5: i18n `projectsYouCanAccess` and `projectHint`
  ("Project: {project}"); job-card hint uses the selected project name or "—".
- REQ-UX-48fb199d: one `Icon` component with inline SVG paths (`chevron`,
  `signOut`) using `currentColor`, `aria-hidden`; Overview cards and the
  Administration toggle render the chevron with a rotate class bound to the
  expanded state; the sidebar sign-out button renders the exit icon and gets
  `aria-label={t("logout")}` beside the existing title. The external-link
  arrow remains only on the MR/PR draft link.
- REQ-UX-0c03fc93: CSS `.panel > h2 { margin-bottom: 14px; }` (panels whose
  h2 sits in `.panel-heading` already have 16px) and `.login-preferences`
  becomes a 12px-gap grid.
- REQ-UX-d93fab0f: price form gets `key={selected}` and
  `defaultValue={selectedProject?.executor in options ? executor : first}` so
  React remounts it per project.
- REQ-UX-7fdffe77: `metricsEmpty = metrics !== null && !(metrics.totals.runs > 0)`
  (scope loaded, no jobs). Summary, Quality and Trends render one
  `<section className="panel"><Empty label={t("metricsNoJobs")} /></section>`
  instead of their stat/table content; controls, Usage and Projects tabs
  unchanged. A scope with jobs keeps dashes for unknown values.

Interfaces/data/security/concurrency/migration: none (display only, no API
change). Compatibility: URLs from TASK-87ebb7d6 reused. Test seams: no pure
logic worth a unit module (`metricsEmpty` is a one-line guard); verification
is browser-driven per requirement, plus existing Node/pytest suites in the
strict check. Alternatives: icon font or library (rejected: offline bundle,
new dependency); hiding hints (rejected by RULING-002). Expected files:
web/src/{App.tsx,i18n.ts,styles.css}, rebuilt adore/web/static/,
05_SoftwareDocu/Component_Web_Frontend.md, knowledge page, CHANGELOG.md.
Risks: RunTable callers must all pass `project`. Open decisions: none. No
architecture drawing owed.

## Log

- 2026-10-03 frame: full path (new links, empty state and defaults are observable behavior); scope = review polish items P1-P6; review policy enabled in aegis.toml (changed outside this session); paused for scope acceptance and Q1-Q3.
- 2026-10-03 frame: scope accepted (P1-P6); Q1 scope hints, Q2 names + tickets, Q3 Summary/Quality/Trends (RULING-002); autopilot to validate (RULING-003); advanced to specify.
- 2026-10-03 specify: 6 requirements created (draft), 0 revised, 0 retired, no spec needed (simple display contracts); P1 scope refined from evidence: Overview projects-table names keep selecting (REQ-UX-15ad4473) and Project details Recent jobs View, which had no visible effect, now opens the job in Jobs; advanced to design (autopilot).
- 2026-10-03 design: note recorded in ## Design (RouteLink names/tickets + openJob, i18n hints, inline SVG Icon, CSS spacing, keyed price form, metricsEmpty guard); no spec or architecture change; advanced to build (autopilot). Build verification is manual/inspection for all six display requirements (no automatable pure logic) - recorded as manual observations.
- 2026-10-03 build deviation: DEVIATION build: aligned job terminology in 18 fr/de/ro error messages from TASK-e40727eb (tâche/Auftrag/lucrare, matching the UI) and in the new metricsNoJobs text - unrequested but a defect introduced earlier; text only; errors.test.mjs still guards coverage.
- 2026-10-03 build manual observation: REQ-UX-205e5379, REQ-UX-deb101f5, REQ-UX-48fb199d, REQ-UX-0c03fc93, REQ-UX-d93fab0f, REQ-UX-7fdffe77; method=Playwright-driven Chrome against a seeded local server (alpha opencode with 15 jobs, gamma codex with none, beta without config; scratch verify_polish.py); result 25/25 after two check-script selector fixes (no candidate change): gaps 14px under 5 headings and 12px sign-in controls at 1440/390; Projects name link + click; Recent jobs View, Jobs ticket and Overview ticket open Jobs details with run URL; Overview names still select; hints in en/fr/de/ro; SVG chevrons flip, sign-out exit icon with localized name; price default opencode/codex/codex and per-project reset; Summary/Quality/Trends single message for empty scope, Usage unchanged, cards for alpha. Frontend `node --test tests/*.test.mjs` exit=0 (23 passed); `npx tsc -b` exit=0; `npm run build` exit=0 (assets LF-normalized).
- 2026-10-03 build: docs updated (Component_Web_Frontend, Web_Interface, knowledge, CHANGELOG); evolution 12 files (2 added, 8 modified, 2 removed superseded assets) = design list plus the declared errors.ts deviation; check errors=0 (stage-zone/merge-base and pre-existing WARNs; Handoff refreshed now). Build complete; advanced to validate (autopilot); explicit review enabled (aegis.toml [review] enabled=true, max_fix_cycles=4) - review_round 1.
- 2026-10-03 validate review round 1 (candidate = working tree vs f1a8018, unchanged since): spec_compliance=approved (independent judge agent; all six requirement clauses traced to code, REQ-UX-15ad4473/3b7dd34e/448cbde7 respected, only the declared deviation as extra); implementation_quality=approved (independent judge agent; low notes accepted: metricsEmpty keys on job count so a hypothetical usage-without-jobs scope would show the message, new display logic has browser not unit coverage, name/ticket links add one tab stop per row beside View, chevron SVG doubly aria-hidden). No fix cycle needed.
- 2026-10-03 validate: semantic review done via the two verdicts plus own diff read; knowledge page, Frontend contract, operator guide and changelog reconciled; requirements re-read (6 active, prose/verification/paths current); manual observations recorded in build; evolution refreshed after the last candidate edit.
- 2026-10-03 validate: first strict run (exit=0, test ok 48.4s, lint ok, frontend ok) flagged journal-only issues - Stage report verdict fields not in the parser vocabulary and errors.ts (deviation) not traced; fixed by recording spec_compliance=approved, implementation_quality=approved, review_round=1 and adding REQ-UX-e6ed7168 (reused, unchanged; governs errors.ts) to requirements; candidate unchanged. source-no-test-changes WARN accepted: all six requirements declare manual/inspection verification, recorded in build. Advanced to deliver; stopping before publication (RULING-003).
- 2026-10-04 deliver: validation evidence, verdicts, deviation, diff, exclusions and outcome presented; user approved "Deploy to DCP, then commit": outcome = DCP deployment of the validated candidate, then one repository-local commit (no push/PR).
- 2026-10-04 deliver DCP: archive SHA-256 7b59a74f8758c7a27442a5a4b6d3e9def1706a3839d92342732dded765619f79 verified on host; live app.py/store.py matched base f1a8018; schema 13; 0 running operations; backups suffix .pre-polish-20261004054556; services restarted and active; index serves index-Dq-Xa24C.js/index-BgSqTs8B.css with new strings (Projects you can access, metricsNoJobs, Aufträge wording) and CSS (.icon.flip, .panel>h2 14px); health/ready 200.
- 2026-10-04 deliver close-out: DCP deployment succeeded; stage done; this repository-local commit carries the candidate, requirements, journal and report (no push or PR requested).

## Rulings

- RULING-001 | date=2026-10-03 | decision=work stays on task/adore-web-interface; TASK-48ddbb7d is not modified | reason=continuation of the web review on the same branch | source=user | supersedes=none
- RULING-002 | date=2026-10-03 | decision=card hints "Projects you can access" and "Project: <name>"; project names and ticket numbers become links; metrics empty state on Summary, Quality and Trends | reason=user answered Q1-Q3 | source=user | supersedes=none
- RULING-003 | date=2026-10-03 | decision=autopilot through specify, design, build and validate (with explicit review), then stop before deliver (DCP deploy + local commit) | reason=user chose "Autopilot to validate" at the frame checkpoint | source=user | supersedes=none

## Handoff


current: done
status: ready
next: none - delivered; DCP runs the candidate and the local commit records it
must_read: .agentic/tasks/TASK-7860b3eb.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: validated candidate deployed to DCP and committed locally on task/adore-web-interface
evidence: check --strict --run exit=0; review round 1 approved/approved; DCP deploy verified (new bundle, strings and CSS live, health/ready 200, services active)
issues: none open
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-04)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-205e5379 - Open projects and jobs from their names
  - REQ-UX-deb101f5 - Explain the number on each Overview card
  - REQ-UX-48fb199d - Use icons that match their action
  - REQ-UX-0c03fc93 - Separate headings and preference controls from fields
  - REQ-UX-d93fab0f - Default the price executor to the project's executor
  - REQ-UX-7fdffe77 - Show one message when metrics have no jobs
  - REQ-UX-e6ed7168 - Display localized web error messages
- deviations: 1 recorded
  - build: aligned job terminology in 18 fr/de/ro error messages from TASK-e40727eb (tâche/Auftrag/lucrare, matching the UI) and in the new metricsNoJobs text - unrequested but a defect introduced earlier; text only; errors.test.mjs still guards coverage.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base f1a8018: 21 file(s) changed, 521 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=6 notes=30
- checklist: 5/6 done; open: close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
