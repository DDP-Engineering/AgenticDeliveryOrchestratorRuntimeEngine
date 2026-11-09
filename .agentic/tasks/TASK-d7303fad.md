<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-d7303fad - Compact the statistics Quality tab

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-5eed5d88
parent:
branch: task/adore-web-interface
base: 6e8436f8e102a37c2ebd8d4992ed085a05a40390
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

Problem: the Quality tab needs scrolling: six large cards with hints, an explanatory paragraph and an "All-time totals" label, a cost section with its own paragraph and USD label, and a daily MR/PR revisions table listing every bucket even when nothing happened (STATED: "in fereastra de quality vreau o rearanjare ca in fereastra de usage. Delivery quality sa fie mai mult ca usage total ... La fel - mai compactate Cost per job evidence si MR/PR revisions").
Desired outcome: Quality uses the Usage-style compact chips: delivery quality values, cost per job (Admin) and revision/repair totals as label + bold value rows; daily revisions only for active days.
Actors: administrators and developers viewing project or global Statistics.
Primary scenario: open Statistics > Quality -> three compact panels: Delivery quality chips; Cost per job with evidence chips (Admin); MR/PR revisions / pipeline repairs chips plus a short table of active days.
Examples: nilo project screenshot (rates "—" with 0/0, stage failures 27, operator retries 10).
Counterexamples: rates keep numerator/denominator; Dev still sees no money; empty cohort still shows "—"; all-project revisions table and revision cost table unchanged.
In scope: App.tsx Quality markup, shared chip CSS, unused i18n keys, e2e, requirement, docs.
Out of scope: metrics API/semantics, Projects and Trends tabs; full suite (STATED: at the end).
Constraints: keep the existing empty-state feedback (REQ-UX-7fdffe77) and financial boundary (REQ-FUNC-930e3ae0).
Success signals: e2e shows chips and absences; DCP shows the compact tab.
Evidence: OBSERVED App.tsx Quality section (Stat cards, qualityHelp, costEvidenceHelp, daily revisions table, coverage-note); no existing e2e covers Quality markup.
Assumptions: hiding zero-activity days from the daily revision table is acceptable because the totals chips keep the period sums (INFERRED from "mai compactate").
Unknowns: none blocking. Decision-blocking questions: none.
Proposed behaviors: B1 compact quality/cost/revision chips without paragraphs or side labels; B2 daily revision table lists only active days (REQ-UX-5eed5d88).
Path and reason: full - observable UI change with a new requirement.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Usage-like Quality | B1 chips for quality, cost, revisions | REQ-UX-5eed5d88 (new) | analytical fixture values | Dev without cost chips; empty cohort "—" | e2e statistics.spec | D1, D2 |
| less scrolling | B2 active-day revision rows | REQ-UX-5eed5d88 | one active day of two | no active day -> no table | e2e statistics.spec | D3 |

## Design

- D1 rename the Usage chip style to a shared `.metric-chips` (Usage keeps `usage-totals` as an extra class); `dd small` shows a muted numerator/denominator.
- D2 Quality: Delivery quality panel = h2 + chips (rework, first validation, merged without revision with n/d; open reviews; stage failures; operator retries), no qualityHelp or totals label; Admin cost panel = h2 + four chips with "n jobs" context, no costEvidenceHelp or USD label.
- D3 Revisions panel: h2 + chips (MR/PR revisions, pipeline repairs, unclassified from totals/coverage) and the daily table filtered to days with a revision or repair; no time zone label; coverage-note paragraph replaced by the unclassified chip.
- Test seams: e2e/statistics.spec.ts new Quality test with routed analytical metrics.

## Log

- 2026-10-11 frame: scope accepted from the user request (Quality like Usage: compact delivery quality, cost per job and MR/PR revisions); autopilot as in prior refinements; full path; full suite deferred by user.
- 2026-10-11 specify: 1 created (REQ-UX-5eed5d88); 0 revised; 0 retired.
- 2026-10-11 design: see ## Design D1-D3.
- 2026-10-11 build red: REQ-UX-5eed5d88 command=`npx playwright test e2e/statistics.spec.ts -g "quality shows compact"` (bundle from build:e2e); exit=1 (1 failed); expected missing behavior=Quality still renders Stat cards, explanatory paragraphs, totals label and every daily revision bucket; no .metric-chips.
- 2026-10-11 build green: `npx tsc -b` + e2e typecheck clean; unit 81 pass; e2e statistics+shell+jobs 56 passed then 1 failed (shell asserted the removed "Current state" hint; updated to the chip) - shell+statistics 24 passed, statistics 11 passed after adding the Dev no-cost check (REQ-UX-5eed5d88). Shared `Chips` component and `.metric-chips` CSS; unused `Stat` removed; i18n qualityHelp/costEvidenceHelp/allTimeTotals/periodTotals/currentState removed (4 locales); docs and CHANGELOG updated.
- 2026-10-11 validate review round 1: implementation-quality - reviewedJobs/validatedJobs/humanMergedJobs left unused, fixed by labelling the rate contexts ("n/d reviewed jobs"); spec-compliance FAIL - three docs still said open reviews are labelled current state, and the e2e checked labels but not values - fixed (docs reworded; e2e asserts n/d reviewed jobs, jobs with evidence, revisions 2 and repairs 1). tsc clean; e2e statistics+shell 24 passed.
- 2026-10-11 validate review round 2: spec-compliance PASS; implementation-quality PASS.
- 2026-10-11 validate final: `python .agentic/aegis.py check --task TASK-d7303fad --strict` errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by tsc (src + e2e), unit 81 and e2e statistics+shell 24 (statistics+shell+jobs 56 before the shell assertion update). Frontend deployed to DCP (assets 200).
- 2026-10-11 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-11 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-d7303fad.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Statistics Quality uses compact Usage-style values: delivery quality (rates with labelled n/d), Admin cost per job with evidence counts, MR/PR revision/pipeline repair/unclassified totals; explanatory paragraphs and side labels removed; daily revision table lists only active days; shared Chips component
evidence: tsc clean; unit 81; e2e statistics+shell 24 passed; review round 2 PASS/PASS; deployed to DCP
issues: DEVIATION full suite deferred by user
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-11)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-5eed5d88 - Show Statistics quality as compact values
- deviations: 1 recorded
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by tsc (src + e2e), unit 81 and e2e statistics+shell 24 (statistics+shell+jobs 56 before the shell assertion update). Frontend deployed to DCP (assets 200).
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 6e8436f: 11 file(s) changed, 218 line(s) added
- checks: errors=0 warnings=13 notes=22
- checklist: 6/6 done
