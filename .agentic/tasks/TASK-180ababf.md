<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-180ababf - Show the default settings in Review and create

stage: done
type: change
path: quick
interaction: autopilot
requirements: REQ-UX-f5791525
parent:
branch: task/adore-web-interface
base: 8862febd1bf503311690d647085f6325bae2fa0c
opened: 2026-10-13

## Done checklist (current stage)

- [x] failing test first (red recorded)
- [x] defaults list green, screenshot checked
- [x] two review verdicts recorded

## Frame

Problem: the wizard asks only the essential settings; about 50 others silently keep ADORE's defaults, so the administrator does not see what the new project will use. STATED: asked whether every setting could be in the wizard, the user chose "simple version (defaults visible in Review) be enough for now".
Desired outcome: Review and create shows a closed, read-only list of every editable setting still at its default, grouped like Settings with the Settings names and value formatting, and says they can be changed in Settings after creation.
Actors: administrators enrolling or cloning a project.
Primary scenario: Review and create -> open "Settings left at their defaults (53)" -> Tickets: Ticket check interval (seconds) 60 ... -> create.
Examples: polling interval 60, lifecycle labels, limits not changed in step 3.
Counterexamples: no editing in the wizard; values changed in the wizard (for example a limit) are not listed; nothing new is written to the project.
In scope: preview `defaults` in adore/web/app.py, DefaultSettings in EnrollmentWizard.tsx, the shared `settingDisplayLabel` (settingLabels.ts, Settings uses it too), copy in four locales, help projects.md row, docs, tests.
Out of scope: editable advanced settings (STATED: simple version for now); full suite (STATED: tests only at the end).
Constraints: names identical to Settings; read-only.
Success signals: targeted pytest and e2e green; screenshot.
Evidence: OBSERVED `_setting_metadata` gives each setting's built-in default and editability; Settings' label chain lived inside App.tsx.
Assumptions: none. Unknowns: none. Decision-blocking questions: answered.
Proposed behaviors: B1 defaults list on Review and create (REQ-UX-f5791525).
Path and reason: quick - read-only list from existing metadata, one small refactor that keeps Settings' behavior.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Defaults visible before creation | B1 | REQ-UX-f5791525 (new) | default settings listed with Settings names | changed values excluded; read-only | pytest preview defaults, e2e URL enrollment | quick path |

## Design

Not applicable (quick path): preview `defaults` = editable settings whose effective value equals the built-in default (`_setting_metadata`); the frontend groups them by `settingPurpose` and names them with `settingDisplayLabel`, moved unchanged from App.tsx into settingLabels.ts.

## Log

- 2026-10-13 frame: scope from the user's choice (STATED "simple version (defaults visible in Review) be enough for now"); quick path; autopilot as in this session; targeted tests only, full suite at the end (STATED).
- 2026-10-13 specify: 1 created (REQ-UX-f5791525).
- 2026-10-13 build red: REQ-UX-f5791525 command=`.venv/Scripts/python.exe -m pytest -q tests/test_web_enrollment.py -k defaults` fail=1 (KeyError 'defaults'); expected missing behavior=defaults in the preview.
- 2026-10-13 build green: preview `defaults` (editable, equal to the built-in default); DefaultSettings on Review and create grouped like Settings with Settings names (settingDisplayLabel moved from App.tsx to settingLabels.ts, App uses it unchanged) and Settings value formatting (publication state, CI failure action); copy in four locales. pytest test_web_enrollment 72/72; node 96/96; tsc clean; e2e "reads a repository URL" and the Settings layout test 2/2; screenshot checked.
- 2026-10-13 help: updated (projects.md Review and create row, four locales; parity ok).
- 2026-10-13 release-notes: none (read-only addition to the unreleased enrollment wizard; no CHANGELOG entry).
- 2026-10-13 validate review round 1: spec-compliance FAIL - Clone project config listed copied rules as defaults (computed before the source rules were copied) and release-notes none was not an accepted reason -> `_preview_defaults` runs again on the final transfer document (test_clone_preview_defaults_reflect_the_copied_rules, red then green); release-notes: added (Improved / Projects, four locales; the two Administration notes merged to stay under the cap) with a CHANGELOG entry. implementation-quality FAIL (medium: visibility ignored the project's backend and agent) -> DefaultSettings filters with settingVisible(key, false, agent, backend) like Settings; lows applied: lists formatted as JSON like Settings, the defaults computation is guarded and computes each value once, the pytest uses max_cost_usd 2.5 vs the written 5.0 and sits before the END OF FILE marker. Accepted: values chosen in the wizard that equal the built-in default stay listed (the requirement is by value). Targeted checks: pytest defaults tests 3/3; ruff clean.
- 2026-10-13 validate review round 2: spec-compliance PASS (clone defaults recomputed, visibility like Settings, release note added). Notes applied: an invalid clone preview returns no defaults list; the transfer test sits before END OF FILE. DEVIATION validate: test_transfer_target_boundaries[reference] was broken by commit df86340 (empty credential lists became valid) and missed by that task's targeted runs; it failed identically on HEAD and now uses a malformed variable name (test-only). pytest test_web_transfer + test_web_enrollment green.
- 2026-10-13 validate review round 2 (quality): implementation-quality PASS (visibility, formatting, guarded computation and the clone recompute verified; the clone test discriminates). Its two notes were already applied above. Targeted checks: pytest test_web_transfer + test_web_enrollment 109/109; tsc and ruff clean; DCP 180c. DEVIATION validate: full suite and broad e2e not run - user instruction to run tests only at the end.
- 2026-10-13 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-13 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.
- 2026-10-13 docs: Web_Interface, Component_Web_API (preview defaults), Component_Web_Frontend (DefaultSettings, settingLabels.ts).

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-180ababf.md
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: Review and create (Enroll new project and Clone project config) lists, closed and read-only, every editable setting still at ADORE's default, grouped and named as in Settings (settingDisplayLabel shared with Settings) and formatted like Settings, with a note to change them in Settings after creation; clone previews recompute it after the copied rules; help (four locales), docs, CHANGELOG, release note; requirement REQ-UX-f5791525
evidence: pytest defaults tests red then green, test_web_transfer + test_web_enrollment 109/109; e2e "reads a repository URL" and the Settings layout test 2/2; node 96/96; tsc and ruff clean; release-notes check and help parity ok; DCP 180c
issues: DEVIATION full suite and broad e2e deferred by user; DEVIATION test_transfer_target_boundaries[reference] fixed (broken by df86340, test-only)
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-13)

- stage: deliver; type: change; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-UX-f5791525 - Show the settings that keep their defaults before creating a project
- deviations: 2 recorded
  - validate: test_transfer_target_boundaries[reference] was broken by commit df86340 (empty credential lists became valid) and missed by that task's targeted runs; it failed identically on HEAD and now uses a malformed variable name (test-only). pytest test_web_transfer + test_web_enrollment green.
  - validate: full suite and broad e2e not run - user instruction to run tests only at the end.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 8862feb: 20 file(s) changed, 280 line(s) added
- checks: errors=0 warnings=15 notes=23
- checklist: 3/3 done
