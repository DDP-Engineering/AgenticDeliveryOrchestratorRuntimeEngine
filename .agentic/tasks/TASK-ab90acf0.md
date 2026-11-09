<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-ab90acf0 - Fix mojibake in German handoff status labels

stage: done
type: fix
path: quick
interaction: autopilot
requirements:
parent:
branch: task/adore-web-interface
base: 220d0c0b3a52a0aa0b383d7186496c0479a112a0
opened: 2026-10-13

## Done checklist (current stage)

- [x] failing regression test first (red recorded)
- [x] labels fixed, tests green
- [x] two review verdicts recorded

## Frame

Problem: German handoff status labels show "?" in place of letters ("?bergabe l?uft", "?bergeben"); the same lossy round trip damaged French "Transf?r?" and Romanian "Predare ?n curs" on the same catalog lines. STATED: "Do this task here: “Fix mojibake in German handoff status labels”".
Desired outcome: the five labels read "Übergabe läuft", "Übergeben", "Transféré", "Predare în curs" (and the unchanged "Transfert en cours"/"Predat"), and a test prevents such "?" replacements in any value of the i18n.ts message catalogs (the other copy files and help were swept by hand and are clean).
Actors: users of the German, French and Romanian interface.
Primary scenario: a job handed to a person shows its status label in German with umlauts.
Examples: de handoffPendingStatus "Übergabe läuft".
Counterexamples: intentional "?" such as the "? Nicht feststellbar" readiness marker or question marks at the end of sentences.
In scope: 04_Software/web/src/i18n.ts handoff status labels (de, fr, ro), a node regression test, CHANGELOG, release note.
Out of scope: other copy files (a sweep found no other damaged strings in web/src or adore/web).
Constraints: write UTF-8 bytes with LF.
Success signals: node tests green, including the new guard.
Evidence: OBSERVED literal "?" (0x3F) in src/i18n.ts lines 117, 198, 279 (introduced in 0669199); the guard regex matches exactly these four values across all catalogs.
Assumptions: none. Unknowns: none.
Decision-blocking questions: none.
Proposed behaviors: restore the labels; guard all catalog values.
Path and reason: quick - copy-only fix with no behavior or contract change; French and Romanian fixed too because they share the cause and the line (in scope of "mojibake" though the title names German).

## Requirement coverage

No requirement: a copy defect fix restoring the intended translations; covered by the node regression test in tests/shell.test.mjs.

## Design

Not applicable (quick path).

## Log

- 2026-10-13 frame: scope from the user's task (STATED); quick path (copy-only fix); French and Romanian handoff labels with the same damage included; autopilot as in this session; full suite deferred by the user.
- 2026-10-13 build red: command=`node --test tests/shell.test.mjs` fail=1 ("localized labels keep their accented letters": fr handedOffStatus "Transf?r?"); expected missing behavior=accented handoff labels in de/fr/ro.
- 2026-10-13 build green: four values in src/i18n.ts restored (de Übergabe läuft / Übergeben, fr Transféré, ro Predare în curs); node 95/95; tsc clean; LF kept.
- 2026-10-13 help: none (labels only; help topics do not quote these statuses).
- 2026-10-13 release-notes: added (Fixed / Jobs entry, four locales; CHANGELOG Fixed entry); `python 02_Tools/check_release_notes.py --since 220d0c0` ok.
- 2026-10-13 build -> validate. Note: the working tree also holds the uncommitted TASK-a11eef15 candidate (it also edits src/i18n.ts, deleteProjectKeeps); this fix is kept to separate hunks so it can be committed on its own.
- 2026-10-13 deployed to DCP as a11b (with the TASK-a11eef15 candidate; health ok).
- 2026-10-13 correction to the help line above: help/content/<locale>/interface.md:55-56 does quote these statuses, already with the correct accented labels, so help stays none (reason corrected, not the decision).
- 2026-10-13 validate review round 1: spec-compliance PASS (labels correct, sweep of every copy file and help clean, release note and CHANGELOG match); implementation-quality PASS (UTF-8/LF verified; minor applied: the U+FFFD guard is written as String.fromCharCode(0xfffd) instead of a literal character; accepted: a word whose only damaged letter is the last one is indistinguishable from a question). node 96/96; tsc clean. DEVIATION validate: full suite not run - deferred by the user to the end of the refinements.
- 2026-10-13 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-13 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-ab90acf0.md
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: German, French and Romanian handoff status labels restored (Übergabe läuft / Übergeben, Transféré, Predare în curs); node guard against "?" replacing letters in the i18n catalogs; CHANGELOG Fixed entry and four-locale release note
evidence: node 96/96 (red first), tsc clean, release-notes check ok, UTF-8/LF verified by review; DCP a11b
issues: DEVIATION full suite deferred by user
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-13)

- stage: deliver; type: fix; path: quick; branch: task/adore-web-interface
- requirements: none linked
- deviations: 1 recorded
  - validate: full suite not run - deferred by the user to the end of the refinements.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 220d0c0: 32 file(s) changed, 1271 line(s) added
- checks: errors=0 warnings=30 notes=23
- checklist: 3/3 done
