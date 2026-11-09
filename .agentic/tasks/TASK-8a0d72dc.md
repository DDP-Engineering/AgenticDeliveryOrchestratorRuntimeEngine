<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-8a0d72dc - Offer Enroll, Import and Clone project actions on Projects

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-664b7fa0, REQ-UX-b3116a07, REQ-UX-7d0b71c3, REQ-UX-77d9307c, REQ-UX-072cf049
parent:
branch: task/adore-web-interface
base: 89c611dcb9b4259c607f4ec9d245fd321630a535
opened: 2026-10-12

## Done checklist (current stage)

- [x] red records, anchor, implementation, focused green, links, docs, check clean
- [x] `stage: validate`

## Frame

Problem: Projects shows Add project and Enroll an existing configuration for this ADORE server, and Add project again offers Guided new project, Import portable settings, Copy project settings and Advanced: unchanged server TOML copy; the last one and the Projects button lead to the same page, so the choices look redundant (OBSERVED in code: TransferWizard onExact -> importProject). STATED: "As vrea operatii simple: enroll new project, import project config, clone project config"; "In fereastra projects, vreau sa am butoanele, separat: Enroll new project, import project config (as fi preferat sa pot incarca un fisier config.toml existent - pe care poate l-am salvat anterior cu export din projects) si clone project config. Si cu implementare acum."
Desired outcome: three separate Projects actions, each opening its own page: Enroll new project (guided), Import project config (upload a config.toml, e.g. saved with Download raw configuration), Clone project config (rules from a project here or a portable file).
Actors: administrators.
Primary scenario: Projects -> Enroll new project -> guided wizard step 1 directly; Import project config -> config.toml upload page; Clone project config -> choose source (project / portable file) -> review rules -> set up new target.
Examples: user's real enrollment test (paused for this change).
Counterexamples: backend import, transfer and enrollment contracts unchanged (import already uploads a config.toml, detects existing IDs and owned state folders); Dev still cannot see or call these actions.
In scope: Projects buttons, routes (/projects/clone), TransferWizard modes, labels in four locales, blocked-Back URL restore, help topics (four locales), e2e/node tests, docs, requirements wording, release notes.
Out of scope: backend changes; full suite (STATED: at the end).
Constraints: help content parity (AGENTS.md Help content rules); release notes rule.
Success signals: focused tests green; DCP shows three buttons; the user's enrollment test continues.
Evidence: OBSERVED App.tsx Projects section-actions, TransferWizard method buttons and onExact, ImportWizard file input (accept .toml), app.py _inspect_project_import findings project_exists/state_root_already_owned.
Assumptions: none. Unknowns: none. Decision-blocking questions: answered.
Proposed behaviors: B1 three actions and pages (REQ-UX-664b7fa0 new); wording revisions of REQ-UX-02f35869, 2761363b, 359f8cbf, 94dc4e69, b3116a07, 77d9307c.
Path and reason: full - observable UI change with a new requirement and help/doc updates.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Three actions | B1 | REQ-UX-664b7fa0 (new) | each button opens its page | Dev denied; no method chooser on /projects/new | e2e shell/transfer, node routes | D1-D3 |
| Clone sources | B1 | REQ-UX-7d0b71c3 (revised: exact copy now Import project config) | project and file sources | review/target invalidation as before | e2e transfer | D2 |
| Help names | help | REQ-UX-77d9307c (wording) | ? link on the enroll wizard | none | e2e help | D4 |

## Design

- D1 Projects: buttons Enroll new project (primary), Import project config, Clone project config (ghost); labels createProject/importProject renamed and cloneProject added in four locales; noEnrolledProjectsHelp names the three actions.
- D2 TransferWizard gets `mode: "enroll" | "clone"`: enroll renders the guided EnrollmentWizard directly; clone shows the source choice (From a project on this server / From a portable settings file, default project) then the existing review and target flow; the exact-copy button and onExact are removed.
- D3 Routes/App: PlainView cloneProject at /projects/clone (admin-only), page title, Projects nav active; a blocked browser Back restores the current page URL (ref of the last synced URL) instead of always /projects/new.
- D4 Help topics projects.md (Enroll new project, Import project config incl. re-importing a downloaded config, new Clone project config section) and interface.md/settings.md mentions, all four locales; docs, CHANGELOG, release note.

## Log

- 2026-10-12 frame: scope accepted (three separate Projects actions, implemented now; user's enrollment test paused); autopilot; full path; full suite deferred by the user.
- 2026-10-12 specify: 1 created (REQ-UX-664b7fa0), 7 revised (REQ-UX-7d0b71c3 exact copy moved to Import project config, found in review) + 6 in wording (REQ-UX-02f35869, 2761363b, 359f8cbf, 94dc4e69, b3116a07, 77d9307c: Add project -> Enroll new project, Import project -> Import project config); 0 retired.
- 2026-10-12 design: see ## Design D1-D4.
- 2026-10-12 build red: REQ-UX-664b7fa0 command=`node --test tests/routes.test.mjs` exit=1 (2 failed: /projects/clone route, admin-only cloneProject); command=`npx playwright test e2e/shell.spec.ts -g "separate Enroll"` exit=1 (Projects shows 2 buttons, expected Enroll new project, Import project config, Clone project config); expected missing behavior=three separate actions and the clone page.
- 2026-10-12 build green: node 94/94 (routes /projects/clone, admin-only); tsc clean; e2e shell+transfer+import+enrollment+help 58/58, then shell+transfer 29/29 after the clone-source styling (visible Clone from label, pressed state) and removal of the unused method copy. Projects shows Enroll new project, Import project config, Clone project config; TransferWizard mode enroll|clone without the exact-copy button; /projects/clone route; refused Back restores the shown URL; import hint covers downloaded configs and inline secrets (the import review rejects secret_value findings, OBSERVED app.py _config_findings) (REQ-UX-664b7fa0, REQ-UX-7d0b71c3, REQ-UX-77d9307c, REQ-UX-b3116a07).
- 2026-10-12 help: updated (projects.md Enroll/Import/new Clone section, interface.md Projects row, settings.md re-import note; four locales, parity ok).
- 2026-10-12 release-notes: added (Improved / Projects); `python 02_Tools/check_release_notes.py --since 89c611d` ok.
- 2026-10-12 deployed to DCP as 8a0a (backend + static).
- 2026-10-12 validate review round 1: implementation-quality PASS with findings -> pressing the active source no longer resets (select returns early); initial selection follows the mode; heading focus only on entry and target switches; e2e asserts the refused-Back URL on import and clone and the active-source re-press. Spec-compliance FAIL -> REQ-UX-7d0b71c3 still named the in-wizard exact TOML option: revised (exact copy offered separately as Import project config); route spec REQ-UX-4200375b updated with Enroll/Import/Clone names, /projects/clone and the /help routes (the latter missed in TASK-90b4e1b9). tsc clean; e2e shell+transfer+import+enrollment 55/55.
- 2026-10-12 validate review round 2: spec-compliance PASS (REQ-UX-7d0b71c3 and the route spec current); implementation-quality PASS with one low test finding -> the re-press assertion now records any loss prompt (accepting it would reset the form); red with the early return removed (Source project emptied), green with it; e2e shell+transfer 29/29.
- 2026-10-12 validate final: `python .agentic/aegis.py check --task TASK-8a0d72dc --strict` errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by node 94/94, tsc (src + e2e), e2e shell+transfer+import+enrollment+help 58/58 then 55/55 and 29/29 after review fixes, help parity and release-notes checks. DCP 8a0b (the last change is test-only).
- 2026-10-12 scope extended at the user's request during the enrollment test (STATED, with a screenshot of the first step: "pagina atasata trebuie modificata sau eliminata - dupa ce apas enroll a new project - trebuie sa incep cu repository si identity"): the Enrollment method step is removed; the wizard starts at Repository and identity with five numbered steps (internal step numbers unchanged, labels 0-based), no Back on the first guided step, a missing finding field falls back to step 1; intro/method copy removed in four locales (the clone requirement stays as the clone-path help). REQ-UX-072cf049 revised (five ordered steps starting at repository and identity); spec REQ-DATA-e1eaf583, help projects.md (four locales), Web_Interface.md, Component_Web_Frontend.md, knowledge and CHANGELOG updated. e2e enrollment+shell+transfer+import+help 58/58; node 94/94; tsc clean; help parity ok; DCP 8a0c. Back to validate for re-review.
- 2026-10-12 validate review round 3: spec-compliance FAIL - REQ-UX-072cf049 title still said six steps -> retitled "Five-step supported enrollment guidance".
- 2026-10-12 validate review round 4: spec-compliance PASS (title fixed); implementation-quality PASS (round 3, no findings on the five-step wizard). `python .agentic/aegis.py check --task TASK-8a0d72dc --strict` errors=0. DEVIATION validate: full suite still deferred by the user; covered by e2e enrollment+shell+transfer+import+help 58/58, node 94/94, tsc, help parity. DCP 8a0c.
- 2026-10-12 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-12 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-8a0d72dc.md
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: Projects offers Enroll new project, Import project config and Clone project config as separate pages (/projects/new guided from Repository and identity in five steps, /projects/import config.toml upload with downloaded-config and inline-secret guidance, /projects/clone from a project or a portable file); in-wizard method buttons and the duplicate import button removed; refused Back keeps the current page; help (four locales), docs, route spec, requirements, CHANGELOG, release note
evidence: node 94/94, tsc clean, e2e 58/58 (final, incl. the five-step wizard), help parity ok, release-notes check ok; DCP 8a0c
issues: DEVIATION full suite deferred by user
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 4

## Delivery report (2026-10-12)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-664b7fa0 - Offer Enroll, Import and Clone project actions on Projects
  - REQ-UX-b3116a07 - Open project creation on a separate page
  - REQ-UX-7d0b71c3 - Explain portable new-project mapping and reconfirmation
  - REQ-UX-77d9307c - Link key pages to their help topic
  - REQ-UX-072cf049 - Five-step supported enrollment guidance
- deviations: 2 recorded
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by node 94/94, tsc (src + e2e), e2e shell+transfer+import+enrollment+help 58/58 then 55/55 and 29/29 after review fixes, help parity and release-notes checks. DCP 8a0b (the last change is test-only).
  - validate: full suite still deferred by the user; covered by e2e enrollment+shell+transfer+import+help 58/58, node 94/94, tsc, help parity. DCP 8a0c.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=4
- diff vs task base 89c611d: 45 file(s) changed, 376 line(s) added
- checks: errors=0 warnings=14 notes=22
- checklist: 2/2 done
