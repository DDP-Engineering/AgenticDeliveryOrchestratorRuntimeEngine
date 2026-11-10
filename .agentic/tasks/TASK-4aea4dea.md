<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-4aea4dea - Isolate incompatible job state in Overview

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-UX-7556495e, REQ-DATA-f304fd2e, REQ-FUNC-ff3e4560, REQ-REL-94e653aa, REQ-UX-2bea4ff1, REQ-UX-163a1c99, REQ-FUNC-44463fc9, REQ-UX-58401aa1, REQ-UX-42f35d04, REQ-UX-b781c764, REQ-UX-d05fdf6d, REQ-FUNC-f47164f2, REQ-FUNC-41265a32
parent:
branch: task/direct-workflow
base: fef14c634ba650aaaa88160234fc53ca1226ea11
opened: 2026-11-10

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [x] diff reviewed against scope, requirements, design, error paths,
      portability, security and unrequested work
- [x] knowledge pages of changed components current with the reviewed code
- [x] project and environment context reconciled with the candidate
- [x] requirements re-read: status, prose, verification, paths and links true
- [x] manual or inspection verification recorded where applicable
- [x] explicit review approved, when enabled
- [x] final `check --strict --run` result logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem: OBSERVED On DCP Server the incompatible historical Nilo job caused the all-project job read to fail with `run_state_corrupt`.
Desired outcome: STATED Overview keeps healthy projects visible and shows the error only for the affected project.
Actors: OBSERVED Administrators and developers with project membership use the same Overview.
Primary scenario: INFERRED A user opens All projects or switches to one project while one authorized project's job state is unreadable.
Examples: OBSERVED Nilo job #26 had an extra field from an older build. STATED The other projects should still display.
Counterexamples: INFERRED Selecting a healthy project should show no Nilo error. An unreadable project must not appear as having zero verified jobs.
In scope: STATED Overview and its project scope, including the shared project Summary job panel. RULING-001 adds the five reproduced validation failures.
Out of scope: STATED No push. Repository data rules rule out migrations and automatic stored-state repair. Job history and detail retain strict reads.
Constraints: STATED Use AEGIS. OBSERVED The current branch is task/direct-workflow. Read only authorized projects and preserve pagination and source revision checks.
Success signals: INFERRED Healthy rows remain visible, a localized warning names only the affected project, scoped selection suppresses unrelated warnings, and authorization and existing strict reads continue to apply.
Evidence: OBSERVED DCP Server read_jobs returned run_state_corrupt globally and succeeded when Nilo was excluded. App jobs_page serves both Overview tables. The state parser rejects unknown fields.
Assumptions: INFERRED A named warning in Needs attention gives the project context on the combined view.
Unknowns: None material.
Decision-blocking questions: None.
Proposed behaviors: Covered by the requested isolation and existing authorization and data rules.
Path and reason: Full, because Overview adds observable error isolation.

| Criterion | Holds? | Evidence |
|---|---|---|
| No new externally observable behavior | No | A named project warning accompanies healthy data. |
| No new interface or data format | No | Overview requests identify their read mode and receive optional coverage evidence. |
| No new dependency | Yes | Existing API and state readers suffice. |
| An existing requirement already covers the behavior | No | REQ-UX-d030ae26 covers Overview, but does not specify per-project error isolation. |
| No security or data-handling change | Yes | Authorization and strict on-disk validation remain in force. |

## Requirement coverage

| Trigger and response | Requirement | Design | Evidence |
|---|---|---|---|
| Overview marks an unreadable project while keeping verified authorized job data visible. | REQ-UX-7556495e | Overview-only projection and named warning | API regression, frontend parser and Chromium scope tests |
| A host check keeps current model evidence while checking all required prerequisites. | REQ-DATA-f304fd2e | Include the network proxy result in the offline fixture. | Model evidence API test |
| A cancel request requires confirmation. | REQ-FUNC-ff3e4560 | Confirm the handoff test requests so they reach the ownership check. | Cancel boundary and handoff tests |
| Handoff blocks automated cancellation. | REQ-REL-94e653aa | Assert that confirmed cancellation is refused at both handoff lifecycles. | Handoff API test |
| Settings have a complete catalog and localized descriptions. | REQ-UX-2bea4ff1 | Include Pi reasoning effort and describe the native account and PATH. | Python and Node catalog tests |
| Gitea sign-in errors guide the user through Repository access. | REQ-UX-163a1c99 | Match the existing localized trigger and submit labels. | Four-locale error tests |
| Reviewed connection edits preserve the selected or default Pi reasoning level. | REQ-FUNC-44463fc9 | Keep reasoning effort in the validated connection wire and reject an overlapping scalar. | Settings Save Node regression and Chromium connection reviews |
| Wide ticket source has a local scroll region. | REQ-UX-58401aa1 | Apply the existing themed scroll styling to raw source. | Desktop and mobile ticket mode test |
| Browser checks exercise notifications, readiness, dirty Settings and folder choice. | REQ-UX-42f35d04, REQ-UX-b781c764, REQ-UX-d05fdf6d, REQ-FUNC-f47164f2 | Scope notification assertions, supply current readiness evidence, tick background polling and create an isolated home. | Targeted Chromium cases |
| Saving profile metadata keeps the last complete file visible during brief Windows sharing errors. | REQ-FUNC-41265a32 | Use one owned temporary file and bounded replacement retries for Windows sharing errors. | Injected profile-store tests and repeated Chromium Settings writes |
| A folder listing preserves an address typed while it loads. | REQ-FUNC-f47164f2 | Canonicalize the address only if it still equals the requested path. | Delayed Chromium folder read followed by actual invalid-path rejection and cancel |

## Design

**Approach.** Overview opts into a project-scoped projection on the existing
paged jobs route. Reuse strict evidence capture and validation per authorized
project and isolate only the typed `run_state_corrupt` failure. Recheck the
whole capture before returning. The existing global sorter orders verified
rows before paging.

**Interfaces and data.** Both Overview tables request `overview=true`.
The API adds optional `unreadable_projects` containing only authorized
project IDs. Totals cover readable projects. The optimistic source revision
binds each verified project revision and the set of unreadable projects.
The browser validates scope and suppresses empty job claims in incomplete
scopes. The named warning uses the existing localized state error. Project
Summary leaves job counters unavailable when that project is unreadable.
If the strict project-directory request fails with `run_state_corrupt`,
Overview and Project Summary retry the directory with `overview=true`. This
bootstrap retains profile identity and excludes invalid activity timestamps
from the project metadata. The ordinary directory still refuses them.

**Files and test seams.** The projection lives in `jobs.py` and `app.py`.
`App.tsx` retries the bootstrap for Overview. `jobModel.ts` validates coverage
and `JobWorkspace.tsx` displays it.
TestClient uses actual incompatible persisted state and Playwright verifies
healthy rows and warning scope. The Node parser test verifies rejected
untrusted coverage. Help, release notes and component knowledge describe the
behavior.

**Risks and open decisions.** The route rechecks profile authorization after
the read. Ambiguous identity, snapshot races and other evidence errors keep
their existing failure paths. State files remain read-only. History and job
detail use the original strict projection.

**Requirement map.** REQ-UX-7556495e maps to the projection, warning and
scope checks above.

**Baseline repairs.** Follow the existing security and readiness contracts.
The cancellation and model readiness fixtures supply the required inputs.
Gitea tests use the current trigger and submit labels. Add localized reasoning
and native execution descriptions to the setting catalog. See RULING-001 and
the coverage rows for the existing contracts.

**Full browser findings.** The first complete Chromium run found baseline
regressions in connection normalization and raw ticket scrolling, and outdated
browser test inputs. Preserve the existing contracts by passing the full
connection shape, reusing the themed scroll rule and updating the fixtures.

**Windows sharing failure.** Full validation and a repeated Chromium run
reproduced WinError 5 when Settings synchronized profile metadata during a
read. ProfileStore now writes to a unique temporary file, bounds retries for
Windows sharing errors, and removes the temporary file on exit.

**Folder address race.** A Chromium trace showed the initial listing replacing
a typed address before Open folder was clicked. The chooser retains the edit
and validates it when navigation is requested. A gated real API read reproduces
the order without timing sleeps.

Diagrams: [diagram_TASK-4aea4dea.md](diagram_TASK-4aea4dea.md)

## Log

- 2026-11-10 frame: journal opened
- 2026-11-10 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-10 specify: completed; next design
- 2026-11-10 design: completed; next build
- 2026-11-10 build: red: pytest -q tests/test_web_jobs.py -k overview_isolates exit 1 (503 for combined Overview); node --test --test-name-pattern 'Overview accepts only' tests/jobs.test.mjs exit 1 (untrusted coverage accepted) (REQ-UX-7556495e)
- 2026-11-10 build: green: pytest tests/test_web_jobs.py exit 0 (116 cases); focused pytest and Ruff after formatting exit 0; Node jobs/help exit 0 (23 cases); Chromium jobs.spec.ts focused exit 0 (4 cases) (REQ-UX-7556495e)
- 2026-11-10 build: release-notes: updated (combined Overview warning with localized error notes; check_release_notes.py --since fef14c6 exit 0)
- 2026-11-10 build: help: updated (Overview in en, fr, de and ro)
- 2026-11-10 build: Build evolution matched the design. AEGIS check has the same repository-wide advisory warning count as before implementation, with no errors.
- 2026-11-10 build: completed; next validate
- 2026-11-10 validate: Review 1: isolate incompatible activity timestamps in Overview project bootstrap while keeping strict directory reads; recheck source bytes across the complete project scope.
- 2026-11-10 validate: returned to build - Review found the strict project-bootstrap boundary and a cross-project source race
- 2026-11-10 build: red review 1: pytest tests/test_web_jobs.py -k 'without_an_aware or previously_read' exit 1 (Overview project metadata rejected three invalid stamps; cross-project mutation returned 200) (REQ-UX-7556495e)
- 2026-11-10 build: green review 1: Ruff configured file scope and pytest tests/test_web_jobs.py -k 'overview or without_an_aware or source_mutation' exit 0 (6 cases); Chromium Overview/Summary exit 0 (5 cases including legacy timestamp bootstrap); npm run build exit 0.
- 2026-11-10 build: completed; next validate
- 2026-11-10 validate: final: check --task TASK-4aea4dea --strict --run exit 1; Python 2715 passed, 6 skipped, 3 failed, Ruff passed, Node 155 passed and 2 failed before full Chromium; isolated HEAD fef14c6 archive reproduces the same 3 Python and 2 Node failures; candidate Overview checks and 5 Chromium tests passed.
- 2026-11-10 validate: DEVIATION validate: the full suite cannot pass on the base checkout - isolated baseline failures are in model readiness, handoff cancellation, setting catalog, Gitea message localization and setting help. Focused API, Node and Chromium cover the fix; the full Chromium stage was skipped by the Node failure.
- 2026-11-10 validate: Advisory warnings concern pre-existing requirement/journal hygiene and the scanner line limit on the regenerated Vite bundle. No task requirement is uncovered.
- 2026-11-10 validate: returned to build - User extended scope to the five reproduced baseline failures before final validation
- 2026-11-10 build: Baseline repair under RULING-001: reproduced the five failures on fef14c6; repaired two request/probe fixtures, localized Gitea navigation expectations, and the reasoning/native settings help catalog.
- 2026-11-10 build: green: focused pytest (37 passed), Node errors/settingHelp/help (21 passed), Ruff and npm run build exit 0.
- 2026-11-10 build: release-notes: updated (settings help, en/fr/de/ro); check_release_notes.py --since fef14c6 exit 0
- 2026-11-10 build: help: updated (native tools PATH in all four Executors topics)
- 2026-11-10 build: completed; next validate
- 2026-11-10 validate: Strict rerun: Python and Ruff passed; frontend Node passed and Chromium reported 239 passes and 15 failures. Browser traces identified omitted thinking wire field, unbounded ticket source, and stale notice/readiness/polling/folder fixtures.
- 2026-11-10 validate: returned to build - Repair additional browser failures before packaging and deployment
- 2026-11-10 build: red: Chromium full run exposed 15 failures; settingsSave.test.mjs confirmed a reasoning-only edit was silently dropped.
- 2026-11-10 build: green: settingsSave Node tests 8 passed. All 15 previously failing Chromium cases passed in targeted reruns after preserving the full connection shape, bounding raw source scrolling, and updating browser fixtures.
- 2026-11-10 build: release-notes: updated (reviewed reasoning effort and local ticket source scrolling); help: none (existing localized help already describes these restored contracts).
- 2026-11-10 build: completed; next validate
- 2026-11-10 validate: returned to build - Round 4 requested operator documentation to distinguish expiring success and persistent failure notifications
- 2026-11-10 build: Aligned operator notification timing and component connection review documentation. Candidate product and focused proof unchanged.
- 2026-11-10 build: completed; next validate
- 2026-11-10 validate: Strict validation: complete Python, Ruff and Node passed; Chromium 253 passed, one test ended with a previous test's unfinished route.fetch.
- 2026-11-10 validate: returned to build - Drain the project lifecycle browser test's in-flight routes before teardown
- 2026-11-10 build: green: jobs Chromium lifecycle and corrupt-summary tests passed 10/10 with --repeat-each=5 after draining in-flight routes; product source unchanged.
- 2026-11-10 build: completed; next validate
- 2026-11-10 validate: Strict run: Python/Ruff/Node passed, Chromium 253/254. Repeated Settings test with pw:webserver diagnostics reproduced PermissionError WinError 5 during profile.json replacement while reading.
- 2026-11-10 validate: returned to build - Handle the reproduced Windows sharing failure during profile save
- 2026-11-10 build: red: three injected ProfileStore sharing/error cases failed against the previous writer. green: all 20 profile tests, Ruff, and the formerly failing Chromium Settings scenario repeated 12/12 passed.
- 2026-11-10 build: release-notes: updated (brief Windows profile file locks); help: none (existing settings workflow and controls).
- 2026-11-10 build: completed; next validate
- 2026-11-10 validate: Strict validation: Python, Ruff and Node passed, Chromium 253/254. The browser trace shows a successful initial folder read replacing text entered before Go, so the second request read an absolute folder instead of rejecting the typed relative path.
- 2026-11-10 validate: returned to build - Preserve the path typed during a pending host-folder read and verify the request ordering
- 2026-11-10 build: red: playwright test e2e/host-folders.spec.ts --grep "failed folder navigation" exit 1; the delayed initial listing replaced relative-folder with the account home (REQ-FUNC-f47164f2).
- 2026-11-10 build: green: all 9 Chromium host-folder cases and 14 Node help/host-folder tests passed. Built the canonical web assets and checked release notes (REQ-FUNC-f47164f2).
- 2026-11-10 build: release-notes: updated (preserve typed folder paths); help: updated (Projects in en/fr/de/ro).
- 2026-11-10 build: Reviewed evolution for the host-folder correction. Remaining advisory warnings are inherited journal/path findings, the generated minified bundle scan limit, and the repository-required delivery files outside product globs.
- 2026-11-10 build: completed; next validate
- 2026-11-10 validate: Re-reviewed the exact corrected candidate with both independent reviewers. Read-only staged DCP copy of the archived Nilo job confirmed the healthy project still displays; package rebuilt after the separate folder correction.
- 2026-11-10 validate: final: python .agentic/aegis.py check --task TASK-4aea4dea --strict --run exit 0; Python, Ruff, Node, TypeScript and all Chromium scenarios passed. The 39 advisory warnings are inherited requirement/journal findings, a minified generated asset scan limit and repository-owned delivery artifacts outside the AEGIS globs.
- 2026-11-10 validate: completed; next done

## Rulings

- RULING-001 | date=2026-11-10 | decision=Fix the five reproduced baseline failures before closing this task; keep the work local. | reason=The user explicitly requested these repairs and a complete validation rerun. | source=user | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-4aea4dea.md
changed: Overview isolation and reproduced suite failures corrected
evidence: AEGIS strict full validation passed (exit 0)
issues: none
spec_compliance: approved
implementation_quality: approved
review_round: 6

## Delivery report (2026-11-10)

- stage: validate; type: fix; path: full; branch: task/direct-workflow
- requirements:
  - REQ-UX-7556495e - Isolate unreadable job state in Overview
- deviations: 1 recorded
  - validate: the full suite cannot pass on the base checkout - isolated baseline failures are in model readiness, handoff cancellation, setting catalog, Gitea message localization and setting help. Focused API, Node and Chromium cover the fix; the full Chromium stage was skipped by the Node failure.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base fef14c6: 30 file(s) changed, 656 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=35 notes=24
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended

## Delivery report (2026-11-10)

- stage: validate; type: fix; path: full; branch: task/direct-workflow
- requirements:
  - REQ-UX-7556495e - Isolate unreadable job state in Overview
  - REQ-DATA-f304fd2e - Revision-bound model connection evidence
  - REQ-FUNC-ff3e4560 - Require explicit confirmation for cancellation
  - REQ-REL-94e653aa - Preserve DCP checkpoint, handoff, and subscription budget semantics
  - REQ-UX-2bea4ff1 - Purpose-based catalog settings presentation
  - REQ-UX-163a1c99 - Guide missing Gitea authentication to Repository access
  - REQ-FUNC-44463fc9 - Configure Pi thinking level
  - REQ-UX-58401aa1 - Contain ticket rich text in themed narrow panels
  - REQ-UX-42f35d04 - Single transient operation notification
  - REQ-UX-b781c764 - Present measured project summary clearly
  - REQ-UX-d05fdf6d - Retain project setting drafts across failures and guard abandonment
  - REQ-FUNC-f47164f2 - Choose clone destinations from host directories
  - REQ-FUNC-41265a32 - Persist isolated profile metadata atomically
- deviations: 1 recorded
  - validate: the full suite cannot pass on the base checkout - isolated baseline failures are in model readiness, handoff cancellation, setting catalog, Gitea message localization and setting help. Focused API, Node and Chromium cover the fix; the full Chromium stage was skipped by the Node failure.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=6
- diff vs task base fef14c6: 71 file(s) changed, 985 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=39 notes=24
- checklist: 9/9 done
