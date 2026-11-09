<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-1d4c0adf - Fix flaky jobs e2e route race

stage: done
type: fix
path: quick
interaction: autopilot
requirements: REQ-UX-b758d2b7
parent:
branch: task/adore-web-interface
base: 3daf8ef3c98fe45a019c811f87bf789c5195d5cf
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

Problem: the e2e test "incomplete corrupt and failed job reads hide totals and stale details" (04_Software/web/e2e/jobs.spec.ts) fails intermittently with `route.fulfill: Route is already handled!` and then a missing "Could not load data" heading when it runs with other specs; it passes alone (OBSERVED in TASK-140be4c6 and TASK-135b0a50 runs: 4/4 alone, 1 failure in combined runs). STATED: "Do this task here: Fix flaky jobs e2e route race".
Desired outcome: the test is race-free in combined runs without weakening its assertions.
Actors: developers running the e2e suite.
Primary scenario: Overview polls jobs-page in the background; the test swaps the incomplete-response handler for the malformed-response handler with unroute/route while a poll is still inside the first handler (awaiting route.fetch), so the old handler's fulfill hits an already-handled route.
Examples: combined `npx playwright test e2e/jobs.spec.ts e2e/tickets.spec.ts e2e/dashboard.spec.ts e2e/shell.spec.ts`.
Counterexamples: assertions (incomplete heading, malformed failure, corrupt server fixture, no secret) unchanged; product code unchanged.
In scope: the one test in jobs.spec.ts and this journal.
Out of scope: product code; full suite (STATED: at the end).
Constraints: keep REQ-UX-b758d2b7 coverage (incomplete/malformed/corrupt reads hide totals).
Success signals: repeated combined runs pass.
Evidence: OBSERVED test body uses page.route -> page.unroute -> page.route -> page.unroute around background polling.
Assumptions: a single persistent handler that switches mode removes the race (INFERRED from the Playwright semantics of removing a handler mid-flight).
Unknowns: none blocking. Decision-blocking questions: none.
Proposed behaviors: test-only change; no requirement change.
Path and reason: quick - a test-only fix with no observable product change.

## Design

- One `page.route` handler for jobs-page for the whole test with `mode` = incomplete | malformed | server; malformed answers without awaiting, server uses `route.fallback()`; no unroute while a poll can be inside the handler.

## Log

- 2026-10-12 frame: scope accepted (fix the route race in one jobs e2e test); quick path because it is a test-only change with no product behavior change; autopilot; full suite deferred by user.
- 2026-10-12 build red: REQ-UX-b758d2b7 evidence=intermittent failure `route.fulfill: Route is already handled!` in combined e2e runs (recorded in TASK-140be4c6 and TASK-135b0a50: 59/60 and 70/72-class runs), 4/4 passes in isolation; cause=handler swap with unroute during a background poll.
- 2026-10-12 build green: e2e typecheck clean; combined jobs+tickets+dashboard+shell run twice with fresh servers: 61 passed both times, no route errors; with --repeat-each 3 the fixed test passed all 3 repeats (6 failures elsewhere were repeat artifacts of state-mutating tests at repeats 2-3: dashboard CSRF, shell Dev without grants, tickets label edits - not run-order flakes).
- 2026-10-12 validate review round 1: spec-compliance PASS (no assertion removed); implementation-quality PASS (optional unrouteAll at the end not applied).
- 2026-10-12 validate final: `python .agentic/aegis.py check --task TASK-1d4c0adf --strict` errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by the e2e typecheck and two fresh combined jobs+tickets+dashboard+shell runs (61/61 each).
- 2026-10-12 deliver: user approved a local commit ("e ok, commite local") on task/adore-web-interface (no push, no PR); test-only, no deployment.
- 2026-10-12 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-1d4c0adf.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: jobs e2e "incomplete corrupt and failed job reads..." uses one persistent jobs-page route handler with a mode switch instead of unroute/route swaps that raced with background polls
evidence: e2e typecheck clean; combined jobs+tickets+dashboard+shell 61/61 twice; review round 1 PASS/PASS
issues: DEVIATION full suite deferred by user; the started suggestion-card session may duplicate this fix
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-12)

- stage: deliver; type: fix; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-UX-b758d2b7 - present complete authorized scoped current-state
- deviations: 1 recorded
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by the e2e typecheck and two fresh combined jobs+tickets+dashboard+shell runs (61/61 each).
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 3daf8ef: 2 file(s) changed, 94 line(s) added
- checks: errors=0 warnings=11 notes=22
- checklist: 6/6 done
