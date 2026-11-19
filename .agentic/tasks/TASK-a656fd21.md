# TASK-a656fd21 - Filter and paginate Statistics project comparison

stage: done
type: feature
interaction: autopilot
requirements: REQ-UX-03252cba
parent:
branch: master
base: 11aed9d4422c91da8c74a5d761749f1214e0bceb
opened: 2026-11-19

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [ ] diff reviewed against scope, requirements, design, error paths,
      portability, security and unrequested work
- [ ] knowledge pages of changed components current with the reviewed code
- [ ] project and environment context reconciled with the candidate
- [ ] requirements re-read: status, prose, verification, paths and links true
- [ ] manual or inspection verification recorded where applicable
- [ ] explicit review approved, when enabled
- [ ] final `check --strict --run` result logged truthfully after the last edit
- [ ] remaining warnings and pre-existing failures explained
- [ ] `report` appended

## Frame

Problem: OBSERVED Project comparison hides pagination controls for small lists and has plain column headings.
Desired outcome: STATED Show rows per page, pagination and per-column filters in Statistics project comparison.
Actors: OBSERVED Authorized users of the all-project Statistics view.
Primary scenario: STATED A user narrows a large project list and pages through the results.
Examples: OBSERVED The screenshot shows the Summary project comparison table.
Counterexamples: INFERRED Single-project statistics and exports keep their current contracts.
In scope: STATED Statistics controls, check Pi model support and update catalog if confirmed, deploy on DCP.
Out of scope: INFERRED Metrics API and persistence changes.
Constraints: STATED Use AEGIS and preserve active jobs. OBSERVED Checkout is master.
Success signals: INFERRED Combined filters and column sorting apply before pagination; controls remain visible with few rows.
Evidence: OBSERVED App.tsx renders both comparisons with PagedTable; Pi 1.5.2 npm data lacks this model in openai and openai-codex.
Assumptions: INFERRED Use the existing rows-per-page choices and table headings.
Unknowns: UNKNOWN Whether a dynamic model catalog supports this model in ADORE's subscription transport.
Decision-blocking questions: None.
Proposed behaviors: None.

## Requirement coverage

- REQ-UX-03252cba covers sorting, combined filters and pagination in the two comparison tables.

## Design

Reuse SortHeader and PagedTable. Compare numeric values numerically and place unavailable values last. Match filters against displayed column values and include repository in project search. Reset the page on filter and sort changes while keeping page size. The browser fixture exercises a list longer than the default page. Deploy the frontend through the web service without restarting the worker.

## Log

- 2026-11-19 frame: journal opened
- 2026-11-19 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-19 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-19 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-19 build: Red: Playwright Statistics comparison exits 1 at missing Started jobs sort button after passing pagination checks.
- 2026-11-19 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-19 validate: returned to build - Document Project comparison in the frontend component and preserve localized Quality counts
- 2026-11-19 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-19 validate: DEVIATION validate: focused Chromium, TypeScript and help proof in place of the complete suite, which the user reserved for final verification.
- 2026-11-19 validate: completed; next done (9 Done checklist item(s) left unticked)

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-a656fd21.md
changed:
evidence: 3 focused Chromium scenarios, typecheck, build, 19 frontend checks and release-note check passed; localized help rebuilt and rechecked.
issues:
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-11-19)

- stage: validate; type: feature; branch: master
- requirements:
  - REQ-UX-03252cba - Filter and paginate Statistics project comparison
- deviations: 1 recorded
  - validate: focused Chromium, TypeScript and help proof in place of the complete suite, which the user reserved for final verification.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 11aed9d: 48 file(s) changed, 641 line(s) added; 4 file(s) not content-scanned
- checks: errors=155 warnings=63 notes=14
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
