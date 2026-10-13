<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-6bbe2138 - Polish the Delete project dialog layout

stage: done
type: change
path: quick
interaction: autopilot
requirements:
parent:
branch: task/adore-web-interface
base: 7489bce0857cb55e177d4ad5895ef85ec337317f
opened: 2026-10-13

## Done checklist (current stage)

- [x] failing e2e layout assertions first (red recorded)
- [x] layout fixed, tests green, screenshots checked (light desktop, dark 390px)
- [x] two review verdicts recorded

## Frame

Problem: in the Delete project dialog the "Also remove the local clone" checkbox sits on its own line above a bold block of label and path, and the confirmation label "Type <name> to confirm" is uniformly bold, so the name to type does not stand out. STATED (with a DCP screenshot): "Trebuie aranjat acest popup - eventual mesajul Type - sa nu fie bolduit - apoi sa urmeze ce trebuie scris - bolduit - sau enhanced ... Asa, totul e uniform si e greu vizibil pentru user. Iar Also remove the local clone --- trebuie aranjat textul (eventual pe o linie - also remove the local clone - si dedesupt - ce clona.... Cumva checkbox-ul sa fie lipit de eticheta."
Desired outcome: the checkbox sits beside "Also remove the local clone" on one line with the clone path below in a lighter style; the confirmation label is normal weight with only the project name emphasized (bold, monospace, tinted chip).
Actors: administrators deleting an archived project.
Primary scenario: open Delete project for an ADORE-made clone -> checkbox beside its title, path below -> "Type [alpha] to confirm".
Examples: the DCP project 2026_virtual_embedded_rig_assistant with a long clone path.
Counterexamples: no wording change; no behavior change.
In scope: DeleteCloneOption.tsx markup, App.tsx confirmation label, styles.css, e2e jobs.spec lifecycle layout assertions.
Out of scope: other dialogs; full suite (STATED earlier: at the end).
Constraints: the global `label` rule is a column flexbox; keep the checkbox accessible name.
Success signals: e2e layout assertions; screenshots in light and dark at desktop and 390px.
Evidence: OBSERVED styles.css `label { display: flex; flex-direction: column; font-weight: 650 }` overrides `.delete-clone` (no flex-direction), so the checkbox stacked above the text.
Assumptions: none. Unknowns: none.
Decision-blocking questions: none.
Proposed behaviors: layout only; existing REQ-FUNC-c0644d76 and delete confirmation behavior unchanged.
Path and reason: quick - presentation-only change in one dialog.

## Requirement coverage

No requirement change: presentation polish of the existing delete dialog (REQ-FUNC-c0644d76 and the exact-name confirmation are unchanged); covered by e2e layout assertions.

## Design

Not applicable (quick path).

## Log

- 2026-10-13 frame: scope from the user's request with screenshot (STATED); quick path (presentation only); autopilot as in this session; full suite deferred by the user. The uncommitted TASK-1e34116f candidate (Tickets pager) shares no files with this task except e2e/jobs.spec.ts (different test).
- 2026-10-13 build red: command=`npx playwright test e2e/jobs.spec.ts -g "lifecycle actions" --retries=0` fail=1 (no .delete-clone-title element: checkbox not beside a title); expected missing behavior=checkbox beside its title with the path below, emphasized name in the confirmation label.
- 2026-10-13 build green: DeleteCloneOption renders title and path in a column beside the checkbox (`.delete-clone` now `flex-direction: row`), the confirmation label is normal weight with the name in a bold monospace tinted chip (`.delete-confirm-name`, split around {project} so all four locales keep their word order); e2e lifecycle 1/1; node 96/96; tsc clean; screenshots light 1280px and dark 390px checked.
- 2026-10-13 help: none (no wording or workflow change).
- 2026-10-13 release-notes: none (layout polish of the unreleased delete-clone option already covered by its CHANGELOG and release note).
- 2026-10-13 validate review round 1: spec-compliance PASS (request met, no wording or behavior change, help/release-notes none justified); implementation-quality PASS (split correct in four locales and no longer exposed to replace() patterns; chip contrast 13.7:1 light, 11.1:1 dark; specificity, wrapping and bounding-box stability checked). Low applied: a space between the title and path spans keeps the checkbox's accessible name readable. e2e lifecycle 1/1 (--retries=0); node 96/96; tsc clean; DCP 6bbb. DEVIATION validate: full suite not run - deferred by the user to the end of the refinements.
- 2026-10-13 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-13 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-6bbe2138.md
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: Delete project dialog: checkbox beside "Also remove the local clone" with the clone path in a lighter line below; confirmation label at normal weight with only the project name emphasized (bold monospace chip), split around {project} for all four locales
evidence: e2e lifecycle layout assertions 1/1 (red first, --retries=0); node 96/96; tsc clean; screenshots light 1280px and dark 390px; DCP 6bbb
issues: DEVIATION full suite deferred by user
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-13)

- stage: deliver; type: change; path: quick; branch: task/adore-web-interface
- requirements: none linked
- deviations: 1 recorded
  - validate: full suite not run - deferred by the user to the end of the refinements.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 7489bce: 22 file(s) changed, 458 line(s) added
- checks: errors=0 warnings=27 notes=23
- checklist: 3/3 done
