<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-e1e7c2b5 - Keep agent actions aligned when selection becomes incomplete

stage: done
type: fix
path: quick
interaction: autopilot
requirements: REQ-UX-646e81fb
parent:
branch: task/adore-web-interface
base: 4d8aaa0
opened: 2026-10-09

## Done checklist (current stage)

- [x] red selection/invalid-draft alignment proof and anchor recorded
- [x] common controls/validation order corrected; focused proof green
- [x] current docs and scope/quality review completed
- [x] final scoped check/evolution recorded
- [x] DCP live selection proof and closeout complete

## Frame

Problem: STATED selecting another agent moves actions below the selector after initial Edit alignment correction.
Outcome: stable selector/action row through valid and incomplete draft states.
Actors: Admin edits supported coding agent, completes model or Cancels; Dev stays read-only.
Scenario: Edit -> select each supported agent -> incomplete model shows error without relocating actions -> valid model allows existing complete candidate review.
Evidence: OBSERVED App.tsx renders validation paragraph before action row, interrupting shared flex layout; previous browser test only measured initial Edit geometry.
Scope: shared editor validation after controls, dedicated full-width error line, all4selection/empty-model geometry and mobile/locale regression, docs and established DCP delivery.
Exclusions: backend, candidate/security/config contracts, credential edits, runtime setup.
Constraints: targeted tests only; preserve profiles/secrets/state/TLS, no push/PR/merge.
Unknowns: none blocking. Quick path: small presentation/error-layout repair to existing UX contract.

## Design

Keep selector and actions adjacent in DOM, render validation after actions and give it a full flex line. Use common setting-editor rule to preserve uniform control presentation. Error still announces and disables Prepare. Test each agent and explicitly clear model to exercise invalid trust boundary and cancellation.

## Log

- 2026-10-09 frame: requested correction accepted, quick path/autopilot; previous verification gap acknowledged in commentary; standing local commit/DCP delivery and targeted-test authorization retained.

- 2026-10-09 build red REQ-UX-646e81fb: npx playwright test executor-config.spec.ts --grep "inline executor editors"; exit1; incomplete Pi draft pushes actions x890 below select ending1438, expected invalid-state layout failure.

- 2026-10-09 review round1: specification compliance approved separately against user-requested stable actions after selection, unchanged responsive/shared contract, updated UX verification and existing APIs; implementation quality approved against generic JSX/CSS error-order repair, accessible alert retained, invalid draft remains blocked, no secret/backend change and4agent geometry/mobile/locale regression. Docs/knowledge reconciled; project/environment/architecture unchanged and checked. No children.
- 2026-10-09 DEVIATION validate: full suite deferred per standing user instruction; scoped build/typecheck and affected Chromium tests substitute for repository-wide proof. Existing Vite chunk warning remains accepted.

- 2026-10-09 final validation: npm build:e2e/typecheck exit0; focused executor Chromium3passed14.2s covering all4incomplete-model selections with disabled Prepare/visible alert and stable action geometry plus candidate/mobile/locale checks; npx playwright test settings.spec.ts --grep "typed Implementation controls review and apply" exit0=1passed10.7s. Strict scoped catalog exit0 errors0/warnings11/notes25:10existing findings plus Playwright test-glob heuristic, actual e2e test changed and passed. Evolution refreshed19:57:43Z, six post-anchor paths in scope; red browser test edit is pre-anchor and retained in Git diff. git diff --check exit0. Round1 compliance/quality approved final candidate, no children/backend changes.
- 2026-10-09 deliver: concrete minimal validation-order and flex-line correction, regression and current docs presented; standing authorized local commit and DCP deployment retained, no push/PR/merge. Fullsuite remains deferred under user instruction.

- 2026-10-09 delivered: product6fc3563a25160e3bb1d7c87c83f30c9e64d7ad8a installed at /home/dpasare/apps/adore/dcp-validation-e1e7c2b5/04_Software; exact package71b9c3d17da1423b74eac46a817e3c5f5359b8fc8dadb1bccece3ce24a8afe5c and fresh JS28a4ced498f7127e6d247834664bd577038d21962c94353f09d0b7c1a9eafb4d/CSS06db9ee078b1a89fb3f27f586f5b3e1b607388ac2bee623a49f5847db610b5cd verified DCP/LAN. Both services active, worker ready, schema14/users1/audit108/operations2failed16succeeded preserved; all6profile config/pause/run-state hashes identical. Existing TLS pin and protected401 preserved. Live aegis user tab: select opencode/pi/qwen/codex, all4selectRight1191.8/actionsLeft1199.8/centers342identical. OpenCode/Qwen/Codex missing-model alerts and disabled Prepare remain below controls; Pi existing valid draft retains same placement. No Prepare/Apply/model-call mutation; Cancel restored activePi. live-selection-proof.json and live-after-select.png saved and image inspected; tab retained. Own backup safely removed after path/service/receipt checks, backups directory empty. SSH/SCP closed. Local ignored receipts in07_Delivery/adore-polling-a224af5d/validation-e1e7c2b5.
- 2026-10-09 closeout: requested stable actions after selection and authorized DCP deployment completed. Fullsuite remains deferred. Report warning12 included then-unfinished deployment checklist; final precommit strict11warnings already explained.

## Rulings

- RULING-001 | date=2026-10-09 | decision=Correct stable actions across incomplete selection and redeploy DCP | reason=User reports reproducible regression after selecting agent; prior delivery scope persists | source=user | supersedes=none

## Handoff

current: done
status: ready
next: none; deployment verified
must_read: task journal; REQ-UX-646e81fb; executor-configuration/web-interface knowledge
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: validation follows control/actions on a dedicated flex line; all4selection regression
evidence: 4focused Chromium tests, build/typecheck/strict catalog; DCP/LAN receipts and live4selection stable geometry in Log
issues: full suite deferred by user; pre-existing Vite/catalog findings accepted
next: none; closeout complete
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-09)

- stage: deliver; type: fix; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-UX-646e81fb - Unified executor configuration workspace
- deviations: 1 recorded
  - validate: full suite deferred per standing user instruction; scoped build/typecheck and affected Chromium tests substitute for repository-wide proof. Existing Vite chunk warning remains accepted.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 4d8aaa0: 11 file(s) changed, 106 line(s) added
- checks: errors=0 warnings=12 notes=25
- checklist: 4/5 done; open: DCP live selection proof and closeout complete
