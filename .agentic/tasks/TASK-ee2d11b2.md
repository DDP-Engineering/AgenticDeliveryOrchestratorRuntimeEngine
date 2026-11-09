<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-ee2d11b2 - Redesign About with What's new and agent-maintained release notes

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-2cace5dd, REQ-UX-93f1ccd5, REQ-REL-982702d6, REQ-UX-749d37c8
parent:
branch: task/adore-web-interface
base: cdebff51ca3f6a70ab82057b95c0f2ee18419bb7
opened: 2026-10-12

## Done checklist (current stage)

- [x] red records, anchor, implementation, focused green, links, docs, check clean
- [x] `stage: validate`

## Frame

Problem: About is a plain dialog with a letter mark, a small version line and both license texts always expanded; users have no place to see what changed in a release, and nothing makes developers write user-facing release notes (STATED: "inglobezi sigla DDP Engineering ... versiunea sa fie mai vizibila si 2 butoane initial colapsate ... o ferastra - what's new ... un mecanism simplu, mentenabil, verificabil si destul de automatizat ... totul sa se faca automat - de catre agent"; proposal approved: "Yes, as proposed").
Desired outcome: About with the DDP Engineering logo band, prominent ADORE version, What's new / License / Third-party notices buttons with licenses collapsed; What's new lists release notes per release in the user's language; release notes kept in one four-locale TOML file checked automatically and maintained by agents through the AGENTS.md rule.
Actors: every signed-in user (About, What's new); developers and agents (release notes).
Primary scenario: open About -> logo, "ADORE", "Version 0.13.0"; press License -> license text; What's new -> In development and 0.13.0 notes grouped New/Improved/Fixed by topic; Back -> About.
Examples: Cockpit Release Notes Contract (d:/2026_Agentic_Delivery_Platform/04_Software/AGENTS.md): user-visible only, New/Improved/Fixed, topic headings, max 10 per category, max 100 characters, no file names/endpoints/ids/components, same change, shape checker.
Counterexamples: CHANGELOG stays the canonical engineering record; release versioning rules unchanged; no release cut; About focus restore unchanged.
In scope: About/What's new UI, /api/v1/about release_notes, adore/release_notes.py + release_notes.toml, 02_Tools/check_release_notes.py, pytest/node/e2e tests, AGENTS.md + CLAUDE.md rule, docs, initial notes for Unreleased and 0.13.0.
Out of scope: release cut; translating CHANGELOG; full suite (STATED: at the end).
Constraints: four locales (en, fr, de, ro) per entry; package data shipped inside adore/ so the runtime bundle and wheel carry it; only the dark logo exists, so it sits on a dark band.
Success signals: focused tests green; DCP About shows the new layout and notes.
Evidence: OBSERVED App.tsx About modal (~1053), /api/v1/about in app.py, CHANGELOG [Unreleased] and [0.13.0] - 2026-09-12, single logo asset DDP_Engineering_logo_dark.png, hatch wheel packages adore/.
Assumptions: none. Unknowns: none. Decision-blocking questions: answered (proposal approved).
Proposed behaviors: B1 About layout (REQ-UX-2cace5dd); B2 What's new (REQ-UX-93f1ccd5); B3 checked release notes contract (REQ-REL-982702d6).
Path and reason: full - new user-visible behavior, a new component and a new repository rule.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| About redesign | B1 | REQ-UX-2cace5dd (new) | logo, version, buttons | licenses hidden until pressed; focus cycles | e2e shell.spec | D4 |
| What's new | B2 | REQ-UX-93f1ccd5 (new) | releases grouped by category/topic in locale | missing locale falls back to English; no notes message | pytest about, node releaseNotes, e2e | D2, D3, D4 |
| Release notes mechanism | B3 | REQ-REL-982702d6 (new) | repository notes pass | each contract failure; --since warning | pytest test_release_notes | D1, D2, D5 |
| About focus/restore kept | existing | REQ-UX-749d37c8 | Escape restores focus to About | none | e2e shell.spec | D4 |

## Design

- D1 `04_Software/adore/release_notes.toml` (schema 1): `[[release]]` version ("Unreleased" first, then released versions newest first with `date`), `[[release.entry]]` category new|improved|fixed, `topic` and `text` tables with en/fr/de/ro.
- D2 `adore/release_notes.py`: `parse_release_notes(text)` (shape, raises ReleaseNotesError), `load_release_notes()` for the packaged file, `contract_issues(releases)` (locales, length <= 100, forbidden file names/paths/endpoints/backticks/snake_case/REQ-TASK ids/CamelCase identifiers except product names, <= 10 per category, Unreleased first, versions descending). `/api/v1/about` adds `release_notes` (empty list when the file is unreadable, so About never fails).
- D3 `02_Tools/check_release_notes.py [--repo-root] [--since REF]`: shape + contract issues, released versions must match a dated CHANGELOG heading, the current `__version__` must have a release section (this replaces the proposed check_release_consistency hook: same guarantee at release cut, without touching its fixtures); `--since` warns when CHANGELOG.md changed and release_notes.toml did not. Exit 1 on issues, 0 with warnings.
- D4 Web: `src/releaseNotes.ts` (types, `localText` with English fallback, `groupRelease` ordered New/Improved/Fixed and topics by first appearance). About dialog: dark logo band with Close, `ADORE` and `Version x` large, license name, buttons What's new / License / Third-party notices (aria-expanded, texts hidden by default, focusable scroll regions); What's new view in the same dialog (wider) with Back, release headings (In development / Version x, date), category and topic headings; Tab cycles through the dialog's focusable elements.
- D5 Rule: AGENTS.md "Release notes rules" (same change as a user-visible CHANGELOG entry, four locales, journal line `release-notes: added | updated | none (<reason>)`, run the checker with `--since <task base>` before validate, roll Unreleased at release cut); CLAUDE.md adapter line; component doc `05_SoftwareDocu/Component_Release_Notes.md`; 02_Tools/README.md entry.

## Log

- 2026-10-12 frame: scope accepted (About redesign, What's new and checked agent-maintained release notes; user approved the proposal); autopilot; full path; full suite deferred by the user.
- 2026-10-12 specify: 3 created (REQ-UX-2cace5dd, REQ-UX-93f1ccd5, REQ-REL-982702d6); 0 revised; 0 retired.
- 2026-10-12 design: see ## Design D1-D5.
- 2026-10-12 build red: REQ-REL-982702d6, REQ-UX-93f1ccd5 command=`.venv/Scripts/python.exe -m pytest -q tests/test_release_notes.py` exit=2 (collection error: no adore.release_notes, no checker); REQ-UX-93f1ccd5 command=`node --test tests/releaseNotes.test.mjs` exit=1 (ERR_MODULE_NOT_FOUND src/releaseNotes.ts); REQ-UX-2cace5dd, REQ-UX-93f1ccd5, REQ-UX-749d37c8 command=`npx playwright test e2e/shell.spec.ts -g "About shows"` exit=1 (no dialog named ADORE with the logo); expected missing behavior=release notes, checker and redesigned About absent.
- 2026-10-12 build green: pytest test_release_notes + test_web_server + test_release_consistency 29/29 (incl. the new untracked-notes --since case, red with the untracked line disabled); node 84/84; tsc + e2e typecheck clean; e2e shell+settings 41/41 (a first run had one unrelated Settings Implementation test pass on retry, then 41/41 clean); ruff clean (REQ-UX-2cace5dd, REQ-UX-93f1ccd5, REQ-REL-982702d6, REQ-UX-749d37c8). Built adore/release_notes.py + release_notes.toml (Unreleased 23 entries, 0.13.0 2), 02_Tools/check_release_notes.py, /api/v1/about release_notes, src/releaseNotes.ts, About/What's new dialog with focus cycling and view-switch focus, four-locale labels, styles; AGENTS.md Release notes rules, CLAUDE.md line, Component_Release_Notes.md, docs and CHANGELOG. The checker caught one German note over 100 characters and its own --since gap for untracked files, both fixed.
- 2026-10-12 release-notes: added (What's new entry under New and About redesign under Improved, plus the initial Unreleased and 0.13.0 notes); `python 02_Tools/check_release_notes.py --since cdebff5` ok, no warning.
- 2026-10-12 deployed to DCP as ee2a (backend + static, health ready=1; live /api/v1/about returns Unreleased 23 and 0.13.0 2 notes).
- 2026-10-12 validate review round 1: spec-compliance PASS (D3 placement judged not material); implementation-quality PASS with findings -> test release date derived from CHANGELOG; fail-soft About logs an adore.web warning and has a test; banner focus ring #b8d1c4; dead aboutClose ref removed; e2e asserts focus on Back/What's new after view switches; fixtures added for backticks, snake_case, UPPER_SNAKE, multi-segment paths, URLs, topic >40, unknown locale, dated Unreleased, repeated and non-x.y.z versions; regex adds URLs, UPPER_SNAKE, csv/log/ini/cfg/env and product names JavaScript/PowerShell/macOS; schema must be an int (not bool); --since uses --end-of-options and handles missing git; releases without entries hidden. Not applied: adding adore/release_notes.toml to REQUIRED_BUNDLE_FILES - it fails against the tracked released 0.13.0 artifacts, and rebuilding them is a release operation out of scope; recorded instead as a release-cut step in AGENTS.md and in Component_Release_Notes.md. Raw ISO release dates and focusing the view heading left as low nits. pytest release_notes+web_server+release_consistency 40/40; node 84/84; tsc clean; e2e shell 15/15; ruff clean; DCP ee2b.
- 2026-10-12 validate review round 2: implementation-quality PASS (low notes applied: logger comment, clear assert when CHANGELOG lacks the dated heading; pytest test_release_notes 29/29); spec-compliance FAIL - REQ-UX-93f1ccd5 said every release is listed while What's new hides releases without notes -> requirement revised to "each release that has notes".
- 2026-10-12 validate review round 3: spec-compliance PASS (REQ-UX-93f1ccd5 revised wording matches the code); implementation-quality PASS (round 2; later edits are a comment and a test assert).
- 2026-10-12 validate final: `python .agentic/aegis.py check --task TASK-ee2d11b2 --strict` errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by pytest release_notes+web_server+release_consistency 40/40 (release_notes 29/29 after the last edits), node 84/84, tsc (src + e2e), e2e shell 15/15 and shell+settings 41/41, ruff clean. DCP ee2b (the later edits are a code comment and a test assert, no redeploy needed).
- 2026-10-12 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-12 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-ee2d11b2.md
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: About with the DDP Engineering logo band, prominent version and folded License/Third-party notices; What's new from four-locale release notes; adore/release_notes.py + release_notes.toml, 02_Tools/check_release_notes.py, /api/v1/about release_notes; AGENTS.md Release notes rules, CLAUDE.md line; REQ-UX-2cace5dd, REQ-UX-93f1ccd5, REQ-REL-982702d6; docs, knowledge, CHANGELOG
evidence: pytest 40/40, node 84/84, tsc clean, e2e shell 15/15 and shell+settings 41/41, ruff clean, check_release_notes --since cdebff5 ok; DCP ee2b
issues: DEVIATION full suite deferred by user; bundle-list entry for release_notes.toml deferred to the next release cut (released 0.13.0 artifacts predate it)
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-10-12)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-2cace5dd - Show a compact About window with collapsed licenses
  - REQ-UX-93f1ccd5 - Show localized release notes in a What's new window
  - REQ-REL-982702d6 - Keep agent-maintained checked release notes beside the changelog
  - REQ-UX-749d37c8 - Localized responsive web interface
- deviations: 1 recorded
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by pytest release_notes+web_server+release_consistency 40/40 (release_notes 29/29 after the last edits), node 84/84, tsc (src + e2e), e2e shell 15/15 and shell+settings 41/41, ruff clean. DCP ee2b (the later edits are a code comment and a test assert, no redeploy needed).
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base cdebff5: 26 file(s) changed, 1244 line(s) added
- checks: errors=0 warnings=12 notes=22
- checklist: 2/2 done
