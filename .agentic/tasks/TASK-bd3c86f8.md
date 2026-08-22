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

# TASK-bd3c86f8 — Release ADORE 0.7.0: AEGIS 0.7 line compatibility, verified

stage: done
type: change
path: quick
requirements:
branch: master
base: b622849f56fb268f357808939ada0fb1193f3155
opened: 2026-08-22

## Done checklist (current stage)

- [x] version bumped to 0.7.0 on every pinned surface (pyproject, __init__, uv.lock, checker, README, 07_Delivery/README, tests, cheat sheets, Component_Packaging)
- [x] CHANGELOG carries a [0.7.0] entry dated 2026-08-22
- [x] `.agentic/` refreshed to AEGIS 0.7.2
- [x] AEGIS 0.7.2 contract surfaces re-verified against the live CLI; no ADORE code change required
- [x] superseded delivery archives removed
- [x] both 0.7.0 runtime archives built (zip + tar.gz)
- [x] `check_release_consistency.py --require-artifacts` exits 0
- [x] `test_release_consistency.py` (and impacted tests) green — full suite 390 passed, ruff clean
- [x] closed out

## Log

- 2026-08-22 frame: Scope: patch release 0.6.1 carrying the AEGIS-compatibility doc wording fixes (04_Software/README.md, config.example.toml, knowledge/aegis-client.md) plus a refresh of this repo's .agentic to AEGIS 0.7.0; rebuild both runtime archives and verify release identity.
- 2026-08-22 frame: Exclusions: no runtime code changes; the deviation-surfacing feature stays in TASK-9aebe1f3; the Architecture backfill for knowledge pages is deferred.
- 2026-08-22 frame: Path: quick — release-identity and documentation change with an existing automated verifier (release consistency checker and tests); no new requirements expected.
- 2026-08-22 frame: DEVIATION frame: no dedicated task branch — release performed on master at operator request, matching how 0.6.0 was cut.
- 2026-08-22 build: Red record: with the checker expecting 0.6.1, `check_release_consistency.py` exited 1 with nine identity errors (pyproject, __init__, uv.lock, README, CHANGELOG, 07_Delivery/README, two stale archives) — the exact worklist.
- 2026-08-22 build: Bumped every pinned surface to 0.6.1, added the CHANGELOG entry, refreshed `.agentic/` to AEGIS 0.7.0, git-rm'd the 0.6.0 archives, and built `adore-runtime-0.6.1.zip` (package_runtime.ps1) and `.tar.gz` (package_runtime.sh).
- 2026-08-22 validate: `check_release_consistency.py --require-artifacts` exits 0; `test_release_consistency.py` 5 passed; full suite 390 passed in 7.58s.
- 2026-08-22 validate: DEVIATION validate: accepted 20 `outside-layout` check warnings — release surfaces (README, CHANGELOG, 07_Delivery, uv.lock, docs) legitimately live outside the configured source/tests globs.
- 2026-08-22 validate: DEVIATION validate: accepted 2 `secret-in-diff` warnings on the binary archives — bundle bytes cannot be line-scanned; their content is generated from scanned sources and layout-verified by the release consistency checker.
- 2026-08-22 validate: DEVIATION validate: `## Architecture` sections owed by the AEGIS 0.7.0 workflow are not backfilled on the existing knowledge pages — deferred deliberately; each page gains its diagram when a task next touches that component.
- 2026-08-22 deliver: The 0.6.1 candidate was never committed and its archives never tracked, so it did not ship; AEGIS moved to 0.7.2 first and the operator renumbered the release to 0.7.0, which this journal now carries.
- 2026-08-22 deliver: DEVIATION deliver: retitled this journal from 0.6.1 to 0.7.0 and restated its checklist rather than opening a second journal — the delivered work is the same release renumbered, and AEGIS 0.7.1 now excludes release operations from the workflow, so a fresh journal would have been contract-noise; the `## Log` and the first delivery report below stay untouched and still read 0.6.1.
- 2026-08-22 deliver: Re-verified every AEGIS contract surface ADORE consumes against the live 0.7.2 CLI — version line and major/floor gate, schema 1, the `status` list and task document, the `check` document including `strict` present only under `--strict`, and the `report appended to` confirmation — all unchanged, so `04_Software/adore/aegis.py` needed no edit.
- 2026-08-22 deliver: The 0.7.1/0.7.2 additions sit outside ADORE's parsing boundary: `diagram` and `explain` are never called by the orchestrator, and the reworked `coverage_class` changes which findings `check` emits, not the shape ADORE decodes.
- 2026-08-22 deliver: DEVIATION deliver: AEGIS 0.7.2 tightened the `DEVIATION <stage>:` marker and now leads its delivery report with deviations, but `04_Software/` still has no notion of them, so ADORE's approval gate does not surface them — accepted for this release, which changes no runtime code; the feature stays framed in TASK-9aebe1f3.
- 2026-08-22 deliver: Bumped every pinned surface to 0.7.0, folded the unreleased [0.6.1] changelog entry into [0.7.0] at operator direction, fixed the stale release lock in `05_SoftwareDocu/Component_Packaging.md`, removed the 0.6.1 archives and rebuilt both runtime bundles.
- 2026-08-22 deliver: Verification green — `check_release_consistency.py --require-artifacts` exits 0, full suite 390 passed, `ruff check adore tests` clean.
- 2026-08-22 deliver: DEVIATION deliver: closed out with no delivery commit — the operator asked for the working tree to be left uncommitted and will commit by hand, so the recorded outcome is a verified working tree, not a commit or PR.
- 2026-08-22 done: Release complete and journal closed; `stage: done`.

## Delivery report (2026-08-22)

- stage: deliver; type: change; path: quick; branch: master
- requirements: none linked
- deviations: 4 recorded
  - frame: no dedicated task branch — release performed on master at operator request, matching how 0.6.0 was cut.
  - validate: accepted 20 `outside-layout` check warnings — release surfaces (README, CHANGELOG, 07_Delivery, uv.lock, docs) legitimately live outside the configured source/tests globs.
  - validate: accepted 2 `secret-in-diff` warnings on the binary archives — bundle bytes cannot be line-scanned; their content is generated from scanned sources and layout-verified by the release consistency checker.
  - validate: `## Architecture` sections owed by the AEGIS 0.7.0 workflow are not backfilled on the existing knowledge pages — deferred deliberately; each page gains its diagram when a task next touches that component.
- diff vs task base b622849: 30 file(s) changed, 650 line(s) added; 2 file(s) not content-scanned
- checks: errors=0 warnings=22 notes=2
- checklist: 7/7 done

## Delivery report (2026-08-22)

- stage: deliver; type: change; path: quick; branch: master
- requirements: none linked
- deviations: 7 recorded
  - frame: no dedicated task branch — release performed on master at operator request, matching how 0.6.0 was cut.
  - validate: accepted 20 `outside-layout` check warnings — release surfaces (README, CHANGELOG, 07_Delivery, uv.lock, docs) legitimately live outside the configured source/tests globs.
  - validate: accepted 2 `secret-in-diff` warnings on the binary archives — bundle bytes cannot be line-scanned; their content is generated from scanned sources and layout-verified by the release consistency checker.
  - validate: `## Architecture` sections owed by the AEGIS 0.7.0 workflow are not backfilled on the existing knowledge pages — deferred deliberately; each page gains its diagram when a task next touches that component.
  - deliver: retitled this journal from 0.6.1 to 0.7.0 and restated its checklist rather than opening a second journal — the delivered work is the same release renumbered, and AEGIS 0.7.1 now excludes release operations from the workflow, so a fresh journal would have been contract-noise; the `## Log` and the first delivery report below stay untouched and still read 0.6.1.
  - deliver: AEGIS 0.7.2 tightened the `DEVIATION <stage>:` marker and now leads its delivery report with deviations, but `04_Software/` still has no notion of them, so ADORE's approval gate does not surface them — accepted for this release, which changes no runtime code; the feature stays framed in TASK-9aebe1f3.
  - deliver: closed out with no delivery commit — the operator asked for the working tree to be left uncommitted and will commit by hand, so the recorded outcome is a verified working tree, not a commit or PR.
- diff vs task base b622849: 34 file(s) changed, 824 line(s) added; 2 file(s) not content-scanned
- checks: errors=0 warnings=24 notes=2
- checklist: 9/9 done
