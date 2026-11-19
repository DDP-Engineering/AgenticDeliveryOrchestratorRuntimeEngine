# TASK-bbbdce61 - Pin admission workflow checks to the fetched remote target

stage: done
type: fix
interaction: autopilot
requirements: REQ-FUNC-2050da54
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

Problem: OBSERVED VERA's local HEAD contains AEGIS 0.13.0 while origin/master contains 0.16.1. The pre-pick gate uses local HEAD.
Desired outcome: STATED Fetch only for eligible admission, verify AEGIS at the fetched commit, and start from that commit. Restart checks the target before cleanup.
Actors: Scheduled pickup and operators starting or restarting a job.
Primary scenario: A stale clone checkout must not block a compatible remote target.
Examples: STATED VERA #318 with agent-ready and P1.
Counterexamples: Empty polls do not fetch for admission; Direct skips AEGIS inspection.
In scope: Remote target selection, workflow admission, Restart and focused deployment.
Out of scope: Re-cloning, moving local branches, or updating active job bases.
Constraints: STATED AEGIS, targeted verification and no interruption to active jobs.
Success signals: No fetch on ineligible pickup; one fetched and validated SHA for admission; failed Restart preflight preserves the older job.
Evidence: OBSERVED DCP project log and origin/master; orchestrator admission and WorktreeManager.
Assumptions: Use existing supported AEGIS version/schema at admission and existing runtime protocol checks.
Unknowns: Future runtime behavior of the fetched script is only proved in its executor boundary.
Decision-blocking questions: None.
Proposed behaviors: None.

## Requirement coverage

REQ-FUNC-2050da54 covers scheduled and manual admission and pre-cleanup Restart.

## Design

Fetch the exact configured branch once, resolve its SHA, and read the committed AEGIS metadata through Git. Never execute a fetched script on the host for admission. Use that SHA when allocating the job and preserve the existing delivery base: the named target for ordinary jobs, and the reviewed SHA for recipe-based jobs. Restart reuses its pre-cleanup admission target. Runtime AEGIS status probing stays inside the executor.

## Log

- 2026-11-19 frame: journal opened
- 2026-11-19 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-19 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-19 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-19 build: Red: targeted pytest exits 1 because eligible automatic admission cannot use the fetched AEGIS commit.
- 2026-11-19 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-19 validate: returned to build - Bound the Git commit output and reconcile companion admission documentation.
- 2026-11-19 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-19 validate: Targeted verification per user; no full suite. Offline admission/restart and Git boundary tests, Ruff, web build, localized help and release note checks green.
- 2026-11-19 validate: completed; next done (9 Done checklist item(s) left unticked)

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-bbbdce61.md
changed: Eligible target fetch, pinned workflow and worktree, pre-cleanup Restart validation, docs and four-locale help.
evidence: Focused pytest selections, Ruff, web build, help and release-note checks exited 0.
issues:
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-19)

- stage: validate; type: fix; branch: master
- requirements:
  - REQ-FUNC-2050da54 - Validate workflow from the same fetched commit used for admission
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 11aed9d: 64 file(s) changed, 1097 line(s) added; 4 file(s) not content-scanned
- checks: errors=155 warnings=70 notes=14
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
