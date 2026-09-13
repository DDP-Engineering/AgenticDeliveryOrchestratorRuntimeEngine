<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

<!--
Task journal. One file per task, at .agentic/tasks/TASK-<id>.md, kept
after delivery as the task's historical record.

The header is the block of "key: value" lines directly under the title.
Keep it exactly in that form — one key per line, no blank lines inside
the block, no comments between the lines — so it stays machine-readable.

  stage         frame | specify | design | build | validate | deliver | done
                (adoption journals: survey | components | close | done)
  type          feature | fix | change | adopt
  path          full | quick
  requirements  comma-separated requirement IDs, empty until specify
  branch        the branch this task is delivered on
  base          the commit this task started from, filled in at creation;
                the delivery report and `check --task` measure the diff
                against it, so leave it alone once it is written. Empty
                when the repository had no history yet.
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.
-->

# TASK-9aebe1f3 — Surface recorded AEGIS deviations at the delivery approval gate

stage: done
type: feature
path: full
requirements: REQ-FUNC-ab65704b
branch: master
base: b622849f56fb268f357808939ada0fb1193f3155
opened: 2026-08-21

## Done checklist (current stage)

- [x] scope and exclusions written in the log
- [x] path chosen (`full` or `quick`) with its reason logged
- [ ] task branch established; `branch:` header matches the checkout
- [x] task journal created with a complete header
- [x] expected requirements listed
- [ ] scope confirmed (checkpoint mode) or logged (autopilot)
- [ ] `stage:` advanced

## Log

- 2026-08-21 frame: Scope: ADORE's delivery/approval flow must surface the deviations a task journal records (`DEVIATION <stage>:` lines, per AEGIS 0.6+) to the human approver at the approval gate, before fingerprint-bound approval is given — count plus full text, sourced from the journal/report ADORE already reads; AEGIS 0.7 leads its delivery report with them for the same reason.
- 2026-08-21 frame: Motivation: ADORE currently gates approval on check totals and diff size only; `04_Software/` has no notion of deviations, so judgement calls made on the approver's behalf are invisible at the one moment a human is guaranteed to be reading.
- 2026-08-21 frame: Exclusions: no parsing-contract change to `AegisClient`'s schema-1 JSON surface beyond what deviations need; no auto-blocking on deviations (they inform, never approve or veto); no changes to AEGIS itself.
- 2026-08-21 frame: Expected requirements: one functional requirement for deviation extraction and typed exposure through `AegisClient`, one for presentation at the approval gate; exact IDs assigned at specify.
- 2026-08-21 frame: Path: full — new behavior crossing aegis-client, orchestrator/state, and operator-facing approval output warrants specify and design.
- 2026-08-21 frame: DEVIATION frame: task branch not created and scope not yet confirmed — journal opened ahead of work at operator request; establish the branch and confirm scope when work begins, then advance `stage:`.
- 2026-09-13 build: implemented directly at the user's instruction, outside the checkpoint flow: `AegisTask.deviations` harvests `DEVIATION <stage>` log entries with AEGIS's own marker rule, strict verification copies them into the validation evidence, and the approval presentation leads with their count and full text; REQ-FUNC-ab65704b links the tests.
- 2026-09-13 validate: full offline suite and ruff green; deviations inform and never block, as scoped; no AEGIS payload change.
- 2026-09-13 done: delivered on master; task closed.

## Stage report

stage: deliver
result: completed
current: done
changed: 04_Software/adore/aegis.py, 04_Software/adore/orchestrator.py, 04_Software/tests/test_aegis.py, 04_Software/tests/test_orchestrator.py, documentation and knowledge pages
evidence: pytest full suite and ruff check green on 2026-09-13; release checker consistent
issues: none
next: none
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:
