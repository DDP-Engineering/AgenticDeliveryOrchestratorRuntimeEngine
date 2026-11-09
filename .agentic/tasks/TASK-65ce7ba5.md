<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-65ce7ba5 - Correct closed-ticket and branch-removal docs

stage: done
type: fix
path: quick
interaction: autopilot
requirements:
parent:
branch: task/adore-web-interface
base: 28e1386d80c8e0ccafeee65d824ebc121c1b8e6e
opened: 2026-10-04

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: 01_Documentation/Configuration_Reference.md says reconciliation makes
  "deleted/closed resources fail visibly", but a closed source ticket cancels
  the run, and documents `remove_source_branch = true` without saying that
  only GitLab honors it.
Desired outcome: the reference states the implemented behavior: a closed
  source ticket cancels a run that waits for approval, a clarification answer
  or review (outcome `ticket closed`; container, worktree and local branch
  removed; state history kept); a deleted ticket fails the run
  (`TICKET_DELETED`); a closed-unmerged MR/PR fails it (`MR_CLOSED`);
  `remove_source_branch` deletes the branch on merge only on GitLab, while
  GitHub and Gitea ignore it because branch deletion is a repository setting
  there.
Actors: operators and administrators reading the configuration reference.
Primary scenario: a reader checks what happens when a ticket is closed or
  whether the branch is removed on GitHub -> the reference answers correctly.
Examples: "Ticket closed while awaiting approval" -> cancelled, not failed;
  "remove_source_branch on GitHub" -> no effect.
Counterexamples: Operations_Guide.md lines 25-29 already describe closed-ticket
  cancellation correctly and stay unchanged.
In scope: Configuration_Reference.md reconciliation paragraph and delivery
  section; CHANGELOG Fixed entry.
Out of scope: code and tests; Operations_Guide.md (already correct); setting
  help texts (already correct); `[reconcile]` comments in config.example.toml
  unless the user adds them (Q1).
Constraints: describe current behavior only; positive wording.
Success signals: every reconciliation and remove_source_branch statement in the
  reference matches the cited code.
Evidence:
  - STATED: follow-up offered from TASK-6222d45e review; user: "Do this task
    here".
  - OBSERVED: orchestrator.py:2351-2356 `_cancel_if_ticket_closed` calls
    `cancel(..., outcome="ticket closed")`; call sites 2364 (approval), 2420
    (clarification), 2497 (review); deleted tickets `_fail_immediately(...,
    "TICKET_DELETED", ...)` at 2362, 2418 and 2495; closed-unmerged MR/PR
    `MR_CLOSED` at 2491; teardown deletes the local branch (2924).
  - OBSERVED: forge/gitlab.py:369-370 passes `--remove-source-branch`;
    forge/github.py:396 and forge/gitea.py:390 discard the value.
  - OBSERVED: Configuration_Reference.md:206 and :174; config.example.toml:374
    already says "(GitLab option)"; config.example.toml:419-420 says deleted
    tickets leave parked runs "orphaned", while the code fails them visibly
    with `TICKET_DELETED` (container stopped, worktree kept).
Assumptions: none.
Unknowns: none.
Decision-blocking questions:
  - Q1 (answered): yes, the `[reconcile]` comments in config.example.toml are
    in scope (RULING-002).
Proposed behaviors: documentation only - no product behavior changes.
Path and reason: quick - documentation only; the described behavior is
  implemented and unchanged.

| quick-path criterion | met | evidence |
|---|---|---|
| no new externally observable behavior | yes | documentation only |
| no new interface or data format | yes | none |
| no new dependency | yes | none |
| existing requirement covers it | yes | no product behavior changes; the text is corrected to the implemented code cited above |
| no security or data-handling change | yes | none |

## Requirement coverage


## Design


## Log

- 2026-10-04 frame: quick path (documentation only). Checkpoint mode; scope and Q1 (config.example.toml comments) presented; delivered after TASK-3922c5e8 because both add a CHANGELOG entry.
- 2026-10-04 frame accepted: user included the config.example.toml `[reconcile]` comments and chose "Autopilot to validate"; waits for TASK-3922c5e8 to be delivered, then resumes at build.
- 2026-10-04 resumed after TASK-3922c5e8 was delivered (28e1386); base moved to 28e1386 so the task diff holds only this fix (no file of this task had been changed).
- 2026-10-04 build: documentation only, so no automated red; anchor recorded before the edits. Configuration_Reference.md gains the remove_source_branch GitLab-only paragraph and a reconciliation paragraph naming TICKET_DELETED (fail, container stopped, worktree kept), ticket closed (cancel, container, worktree and local branch removed, state kept), merged-wins and MR_CLOSED; config.example.toml `[reconcile]` comments say waiting runs instead of parked, fail visibly instead of orphaned; CHANGELOG Fixed entry; working copies normalized to LF (index already LF). Inspection: each sentence checked against orchestrator.py (`cancel` 329-345, `_cancel_if_ticket_closed` 2351-2356 with call sites 2364/2420/2497, `_fail_immediately` -> `_terminal_failure` 1975-2000, review reconcile merged/closed order 2480-2497, teardown 2918-2924) and the forge adapters (gitlab.py 369-370, github.py 396, gitea.py 390). Example-config tests (catalog, config, web_pending_config, web_config) 65 passed.
- 2026-10-04 validate review round 1: spec_compliance=changes_required, implementation_quality=changes_required (same MEDIUM: a run in review checks its MR/PR before the ticket - merged completes it, closed fails it with MR_CLOSED, missing for max_transient_retries polls fails it with MR_DELETED - so "a deleted ticket fails the run" and the example's "always" were false for review runs; LOW: the MR_DELETED case was dropped from the reference; the example header still said active/parked; the CHANGELOG "only GitLab deletes the branch" overstated it). Verified at orchestrator.py 2466-2497. Routed to build for fix cycle 1 of 4.
- 2026-10-04 build fix cycle 1: the reference says a run in review checks its MR/PR first (merged, MR_CLOSED, MR_DELETED after max_transient_retries polls) whatever the ticket's state; the example's STATUS block states the same, its NOT ENFORCED lines say "whatever this value" instead of "always", and its header says waiting run; the CHANGELOG says remove_source_branch takes effect only on GitLab. Inspection against the same code lines; example-config tests 65 passed; LF kept. Returned to validate for review round 2.
- 2026-10-04 validate review round 2: spec_compliance=approved (no findings); implementation_quality=approved (LOW: the example STATUS block omitted the missing-MR/PR case that the reference states; LOW: a short wrapped header line). Taken as fix cycle 2 of 4 to keep the example and the reference consistent.
- 2026-10-04 build fix cycle 2: the example STATUS block adds "one that stays missing fails it (MR_DELETED)" and the header is rewrapped; every changed line is 80 columns or less; example-config tests 65 passed. Returned to validate for review round 3.
- 2026-10-04 validate review round 3: spec_compliance=approved, implementation_quality=approved, no findings (the STATUS sentence checked against orchestrator.py 2472-2497; reference and CHANGELOG unchanged since round 2; LF; example config validates).
- 2026-10-04 validate final: command=`python .agentic/aegis.py check --task TASK-65ce7ba5 --strict --run`; exit=0; test ok 49.6s, lint ok, frontend ok; errors=0, warnings=5: scope-drift (a documentation-only quick path links no requirement), outside-layout for 04_Software/config.example.toml (the example configuration lives at the package root), and 3 from before this task (tracked sidecars; TASK-5e99ee1d and TASK-c765e6b4 journal headers). No knowledge page describes this text; no requirement to re-read (quick path, none linked); inspection recorded in build; evolution refreshed after the last edit. Advanced to deliver.
- 2026-10-04 deliver: validation evidence, verdicts, diff (3 files, documentation and example comments only), exclusions (TASK-a4fec466 journal belongs to the next task) and outcome presented; no deviations recorded. User approved "Commit only (Recommended)": outcome = one repository-local commit; nothing deployed (DCP reads neither file at runtime).
- 2026-10-04 deliver close-out: stage done; this repository-local commit carries the documentation, the journal and the report (no push or PR requested).

## Rulings

- RULING-001 | date=2026-10-04 | decision=work stays on task/adore-web-interface and runs after TASK-3922c5e8 | reason=user: "Do this task here"; both add a CHANGELOG entry | source=user | supersedes=none
- RULING-002 | date=2026-10-04 | decision=scope adds the `[reconcile]` comments in 04_Software/config.example.toml | reason=user answered Q1 "Yes, include it (Recommended)" | source=user | supersedes=none
- RULING-003 | date=2026-10-04 | decision=autopilot through build and validate with explicit review, then stop before deliver | reason=user chose "Autopilot to validate (Recommended)" | source=user | supersedes=none

## Handoff


current: done
status: ready
next: none - delivered as a local commit
must_read: .agentic/tasks/TASK-65ce7ba5.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: documentation fix committed locally on task/adore-web-interface
evidence: check --strict --run exit=0; review round 3 approved/approved; inspection against orchestrator.py and forge adapters
issues: none
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-10-04)

- stage: done; type: fix; path: quick; branch: task/adore-web-interface
- requirements: none linked
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 28e1386: 5 file(s) changed, 320 line(s) added
- checks: errors=0 warnings=4 notes=31
- checklist: 6/6 done
