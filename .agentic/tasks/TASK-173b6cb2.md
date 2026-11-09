<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-173b6cb2 - Fix two full-suite test failures

stage: done
type: fix
path: quick
interaction: autopilot
requirements: REQ-UX-29d41b39
parent:
branch: task/adore-web-interface
base: 71ebfe7b50c30d80f45e2d5b29471c0c6a3d8ce7
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

Problem: the full suite (`python .agentic/aegis.py check --strict --run`, STATED: "acum e cazul sa rulam toata suita de teste") failed twice: (1) pytest `tests/test_image_build.py::test_image_runtime_rejects_remote_environment_and_linked_storage` raises AttributeError because it monkeypatches `Path.is_junction`, which Python 3.11 (the project venv, requires-python >=3.11) does not have - pre-existing since 8c579e6, product code already uses `getattr(..., lambda: False)`; (2) e2e `jobs.spec.ts` "global Jobs mirrors the project hub..." expected exactly one ticket-read alert, but in the full run earlier specs add projects whose forge reads also fail.
Desired outcome: both tests pass in the full suite with their intent kept.
Actors: developers running the suite.
Primary scenario: full suite green.
Examples: suite log 1 failed/1742 passed (pytest), 1 failed/179 passed (e2e).
Counterexamples: product code unchanged; the image test still proves linked storage is rejected; the jobs test still proves beta's failure is reported alone for beta while alpha's tickets stay.
In scope: the two tests and this journal. Out of scope: product code.
Constraints: REQ-UX-29d41b39 per-project error behaviour stays verified.
Success signals: focused runs pass, then the full suite passes.
Evidence: OBSERVED suite log; Python 3.11.15 in 04_Software/.venv; adore/web/image_build.py:284 getattr fallback.
Assumptions: none. Unknowns: none. Decision-blocking questions: none.
Proposed behaviors: test-only fixes; no requirement change.
Path and reason: quick - two test-only fixes.

## Design

- test_image_build: `monkeypatch.setattr(Path, "is_junction", ..., raising=False)` so Python 3.11 adds the attribute the product reads through getattr.
- jobs.spec: scope alerts and rows to the named projects (an alert starting "beta: ", none starting "alpha: "; after reread none starting "beta: "; beta rows via an exact project cell).

## Log

- 2026-10-12 frame: scope accepted (make the full suite green after the user's full-suite request); quick path because both fixes are test-only; autopilot.
- 2026-10-12 build red: REQ-UX-29d41b39 command=`python .agentic/aegis.py check --strict --run` exit=1 (pytest 1 failed/1742 passed/3 skipped: test_image_build AttributeError Path.is_junction on Python 3.11; e2e 1 failed/179 passed: jobs.spec global Jobs alert count 2 vs 1); ruff ok.
- 2026-10-12 build green: pytest tests/test_image_build.py 61 passed/2 skipped; ruff clean; e2e typecheck clean; jobs.spec "global Jobs mirrors" passed alone; full suite `python .agentic/aegis.py check --strict --run` exit=0 (test ok 188.6s, lint ok, frontend ok 215.2s; errors=0, strict ok).
- 2026-10-12 validate review round 1: spec-compliance PASS (reproduced the targeted pytest pass); implementation-quality PASS with an optional robustness note applied: the remaining alpha/beta row lookups in the same test use the exact-project-cell helper; e2e jobs+tickets+dashboard+shell+enrollment re-run (see next line).
- 2026-10-12 validate final: e2e jobs+tickets+dashboard+shell+enrollment 75 passed after the optional locator change; `python .agentic/aegis.py check --task TASK-173b6cb2 --strict` errors=0; the full suite passed (exit 0) on the reviewed candidate, the later locator-only change was covered by the 75-test related-spec run.
- 2026-10-12 deliver: user approved committing the fixes and force-pushing task/adore-web-interface with a backup branch (answer: "Yes, with a backup branch"); local commit on task/adore-web-interface.
- 2026-10-12 close-out: outcome is a repository commit carried to origin by the user-approved force push; close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-173b6cb2.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: test_image_build monkeypatches Path.is_junction with raising=False (Python 3.11 venv); jobs.spec global Jobs test matches ticket-read alerts and rows per project
evidence: full suite `check --strict --run` exit 0 (test ok, lint ok, frontend ok); related e2e 75 passed after the optional locator change; review round 1 PASS/PASS
issues: none
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-12)

- stage: deliver; type: fix; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-UX-29d41b39 - Show the global Jobs page like the project hub Jobs tab
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 71ebfe7: 3 file(s) changed, 98 line(s) added
- checks: errors=0 warnings=12 notes=22
- checklist: 6/6 done
