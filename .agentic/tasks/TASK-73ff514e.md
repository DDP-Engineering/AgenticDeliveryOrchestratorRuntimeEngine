<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-73ff514e - Host check opens results immediately and closes internally
stage: done
type: fix
path: quick
interaction: autopilot
requirements: REQ-UX-0109a142
parent:
branch: task/adore-web-interface
base: 1727d1d64b5b69785c1c7ef16b2b04c6c7c59e40
opened: 2026-10-07

## Done checklist (current stage)
- [x] Candidate reviewed against scope, exclusions and contracts.
- [x] Docs, requirements, knowledge and scoped proof complete.
- [x] Delivery presented under standing human authority.
- [x] Report/journal prepared.
- [x] Scoped commit/push/deploy verified.
- [x] Close-out committed after outcome.

## Frame
Problem: Check clears/hides results; separate chevron required, so user sees no progress.
Desired outcome: Click opens checking/details; internal Close details hides without cancelling.
Actors: Admin; Dev remains without check action.
Primary scenario: Click, see checking, receive validated results, close details to see jobs.
In scope: Summary disclosure/busy/error/scoped response state, four-locale Close details label, focused tests/docs/assets and scoped delivery.
Out of scope: Backend checks, model/provider capabilities, full suite and epic.
Constraints: Four hours/three fix cycles/twenty authored files; no agents. Standing scoped commit/push/deploy authority; full suite only at final iteration.
Path and reason: quick existing action/disclosure correction, no API/data contract changes.
Questions: none; human allows representative name Close details.

## Design
Open before await; state/ref busy guard prevents duplicates. Separate per-panel safe error/loading; keep validated reader and scope guards. Close only disclosure and restores focus to check button; completion respects close. Reset pending state on page/project/account change; retain evidence across project tabs. Check aria-controls/expanded/busy; no external chevron.

## Log
- 2026-10-07 frame: direct user scope accepted; autopilot under standing delivery authority.
- 2026-10-07 build red: `npx playwright test e2e/jobs.spec.ts --grep "host check opens immediately" --project=chromium` exit1; expected missing behavior=panel remains hidden during held request.

- 2026-10-07 bounded correction1: Model-evidence regression identified that resetting on project-tab changes removed existing Summary evidence. Removed tab dependency, retaining project/account/page guards and cross-tab evidence. Corrected directly affected tests to immediate opening.

- 2026-10-07 validate: Final build/E2E build/typecheck exit0; `npx playwright test e2e/jobs.spec.ts e2e/executor-config.spec.ts --grep "host check|host prerequisite|current model evidence" --project=chromium` exit0,11 passed. Held request/immediate loading, close while busy, no completion reopen, repeat check, failure clears stale evidence, malformed/foreign evidence, real offline API and four locales/narrow dark layout validated. Model evidence coherent across tabs.
- 2026-10-07 final reviews: Separate same-agent specification and implementation-quality lenses approved, round2 after bounded correction1. Reviewed ref duplicate guard, pending scope/revision cleanup, aria-disabled focus restoration, request errors, validated reader and Dev action boundary. No backend changes; component ownership/architecture unchanged. Same-change docs/knowledge/Unreleased reconciled; previous chevron requirement retired by explicit human replacement. Context/environment unchanged; inventory within authored-file bound; workflow/generated separate; no agents.
- DEVIATION validate: Full suite deferred until final iteration under direct user instruction. Focused proof covers current disclosure/model presentation and error boundaries, not repository-wide regression. Historical unrelated failures remain outside scope. Existing Vite/NO_COLOR and strict historical/generated-asset advisories accepted; authored source reviewed and bundle rebuilt.
- 2026-10-07 delivery presentation: Summary check opens immediately, internal Close details hides without cancellation; no external chevron. Build11 focused tests passed; deferred full proof disclosed. Scoped source/tests/docs/assets and journal will be committed/pushed/deployed under standing human authority; no PR/merge/version or live provider acceptance.

- 2026-10-07 outcome: 3b6a121b9f0f22bbbcb8af30203061206eec17b3 pushed with remote ref verified; deployed /home/dpasare/apps/adore/web-ux-3b6a121. Backup /home/dpasare/apps/adore/backups/web-ux-3b6a121-20261007100035. Known SSH host key verified; upload hashes and served JS/CSS byte match; web/worker active; health alive, ready/worker ready; projects401 unauthenticated; SQLite schema14/integrity ok/audit84. Strict advisory0 errors11 historical/generated warnings/passed, no full suite run. No live forge/model acceptance performed.

## Rulings
- RULING-001 | date=2026-10-07 | decision=Implement immediate disclosure/internal Close details and scoped commit/push/deploy with focused proof | reason=Direct user request and standing delivery/testing authority | source=user | supersedes=none

## Handoff
current: done
status: ready
next: Human live iteration; full suite at final iteration
must_read: .agentic/tasks/TASK-73ff514e.md; .agentic/steps/5_validate.md
blockers: none

## Stage report
stage: done
result: completed
current: done
changed: Immediate checking panel with internal localized Close details
evidence: Build/typecheck passed; final focused Chromium11 passed
issues: Full suite deferred until final iteration by user
next: Human live iteration; full suite at final iteration
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-07)

- stage: done; type: fix; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-UX-0109a142 - Host check immediate disclosure and internal close
- deviations: 1 recorded
  - validate: Full suite deferred until final iteration under direct user instruction. Focused proof covers current disclosure/model presentation and error boundaries, not repository-wide regression. Historical unrelated failures remain outside scope. Existing Vite/NO_COLOR and strict historical/generated-asset advisories accepted; authored source reviewed and bundle rebuilt.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 1727d1d: 14 file(s) changed, 157 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=11 notes=25
- checklist: 4/6 done; open: Scoped commit/push/deploy verified.; Close-out committed after outcome.
