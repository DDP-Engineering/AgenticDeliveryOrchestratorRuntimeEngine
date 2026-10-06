<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-ec36da10 - Project monitoring labels and concise rows

stage: done
type: change
path: quick
interaction: autopilot
requirements: REQ-UX-78923e00
parent:
branch: task/adore-web-interface
base: d1811f528c9fc2619508c7489fc136af110c2d8e
opened: 2026-10-06

## Done checklist (current stage)

- [x] Targeted red/green and docs
- [x] Review and substituted final proof
- [x] Authorized publication/deploy/smoke

## Frame

Problem: STATED Pickup is unclear and repeated active-job guidance clutters Projects.
Desired outcome: localized Monitoring column, Active/Paused states and Pause/Activate monitoring actions; concise rows and summary.
Actors: administrator/operator and assigned developer.
Primary scenario: inspect Projects -> distinguish automatic new-ticket monitoring and environment verification; administrator uses existing Actions.
Examples: supplied screenshot has repeated guidance and offscreen Actions.
Counterexamples: Monitoring active must not claim executor/worker readiness; pause must retain existing active job behavior.
In scope: copy labels EN/FR/DE/RO, remove repeated pickupHelp rendering in Projects/summary, focused browser assertion and docs.
Out of scope: change lifecycle/action visibility/layout, readiness probes, real project mutations, backend, epic continuation.
Constraints:4h/3cycles/20authored files; no agents; targeted tests/fullsuite deferred; existing DCP deploy under standing authority.
Success signals: Monitoring header and Paused/Active honest states; repeated prose absent; existing administrator actions still present.
Evidence: OBSERVED App.tsx table/actions and Summary; jobCopy.ts four locales; app.py archive refuses active work, restore retains pause state, delete requires archive/confirmation; current request STATED.
Assumptions: existing Help retains explanation of pause semantics; labels change only, API keys remain pickup.
Unknowns: live visual acceptance after deploy.
Decision-blocking questions: none.
Proposed behaviors: presentation-only rename and redundant prose removal.
Path and reason: quick; existing requirement covers same monitoring vs verification behavior, no new interface/data/dependency/security behavior.

## Design

Only change jobCopy display labels/action names and two App guidance render sites. Preserve internal pickup keys/state, operation types, role/CSRF guards and real readiness evidence. Existing header glossary explains pickup semantics.

## Log

- 2026-10-06 frame: interactive copy cleanup accepted; existing requirement and focused hub test; same branch, no children, no extra agents.

- 2026-10-06 build red: npx playwright test e2e/jobs.spec.ts -g "hub separates", exit1, Monitoring column absent. Anchor313files at d1811f5. Four-locale presentation labels and two repeated prose sites changed; preserved pickup keys/operation types and Help semantics.

- 2026-10-06 validate: UI/E2E TypeScript+isolated build exit0, four selected offline browser journeys4passed37.8s (monitoring vs verification/absence of repeated guidance/existing Admin actions,390px/themes/fourlocales,Help semantics,Dev role navigation); production build exit0, git diff --check exit0. No backend/operation/probe changes. Component docs/knowledge/spec and requirement reconciled; source inspection confirms status derives unchanged paused/archived booleans. Existing architecture/context/environment semantics retained; no extra agents or children.
- 2026-10-06 reviews: spec compliance approved and implementation quality approved, separate same-agent lenses/round1, candidate SHA256 b48f53165051dcbac76991f0eea287c770d6c2c3241e10fdb73a51581e2d8034, 12 scoped candidate paths plus journal. The copy describes new-ticket monitoring independently of job execution/readiness; command mappings and authorization unchanged. Full legal headers retained; generated bundle derives reviewed sources.
- 2026-10-06 final proof: evolution8nonworkflow changes10:39:19Z (red tests already in anchor), catalog-only check --strict --json exit0/0errors7warnings27notes/strictpassed/run[]. Baseline fingerprint/legacyjournal warnings; configured tests glob excludes changed e2e; generated large JS scanning supplemented by source review. Existing Vite bundle size advisory accepted. DEVIATION validate: required full suite/check--run deferred by human; narrow proof does not establish complete regression coverage.
- 2026-10-06 deliver: presented Monitoring Active/Paused labels and concise rows/summary, four-locale actions, docs/tests/assets; user questions answered from actual backend/source. Standing scoped authority covers normal commit/push and existing DCP deployment. No new functions/PR/version/epic work or live project mutations.

- 2026-10-06 delivered: exact85438002e7bd3045cc933f3a498953c06794eb3c pushed and remote ref verified; deployed /home/dpasare/apps/adore/web-ux-8543800 with archiveSHA25693aa0c596b981f9f059f0ae7dc7628c9004ed7a773b4d698b45ed0faea07e04e. Backup /home/dpasare/apps/adore/backups/web-ux-8543800-20261006134134. API/worker active/exactPYTHONPATH; served JS/CSS byte-identical; root200newindex,health200alive,ready200workerready,projects401unauthenticated. schema14/integrityok/audit45 retained. No project pause/archive/delete/probe commands executed. Human visual acceptance/fullsuite deferred; epic remains paused.

## Rulings

- RULING-001 | date=2026-10-06 | decision=Scoped copy implementation with targeted-only checks, normal commit/push and existing DCP deployment | reason=Direct user request and standing live-iteration authority; full suite explicitly deferred | source=user | supersedes=none

## Handoff

current: done
status: ready
next: human live visual testing
must_read: .agentic/steps/4_build.md, .agentic/knowledge/web-interface.md
blockers: none

## Stage report

stage: done
result: completed
current: done
changed: monitoring copy and concise project rows
evidence: production/typecheck build exit0;4focused browser journeys passed; catalog strict exit0 run[]
issues: full suite deferred by human
next: human live testing
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-06)

- stage: deliver; type: change; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-UX-78923e00 - distinguish new-ticket Monitoring Active/Paused state from revision-bound environment verification
- deviations: 1 recorded
  - validate: required full suite/check--run deferred by human; narrow proof does not establish complete regression coverage.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base d1811f5: 13 file(s) changed, 128 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=8 notes=27
- checklist: 2/3 done; open: Authorized publication/deploy/smoke
