<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-363f96ed - Repair native image client and simplify live environment workspace

stage: done
type: fix
path: quick
interaction: autopilot
requirements: REQ-REL-2cbd8d83, REQ-UX-1b9b5789
parent:
branch: task/adore-web-interface
base: 631f857c2eb4761972f560f94fe4f07bc6a5751b
opened: 2026-10-07

## Done checklist (current stage)

- [x] validated candidate and focused evidence presented
- [x] continuing human local commit/DCP deployment authorization recorded
- [x] implementation commit delivered
- [x] DCP backup/replacement and actual GUI build verified
- [x] journal close-out committed after external outcome

## Frame

Problem: STATED deployed image workflow does not work, is cramped/misaligned and unclear. OBSERVED live aegis page reports image_runtime_capabilities_unsupported with empty output; retained stderr shows os.execve('docker') FileNotFoundError. Runtime adapter returns a file-based controller result without loading captured streams.
Desired outcome: Existing bounded native build client resolves its executable and returns authoritative captured evidence; environment setup is visibly ordered and readable.
Actors: Admin chooses backend/image and explicitly builds; Dev reads; local operator owns installed host tools.
Primary scenario: Open Settings -> Isolated environment -> execution mode and image controls immediately visible -> edit definition/check/network -> save/build -> actual bounded client output/verification -> existing reviewed selection.
Examples: DCP Docker 29.8.2 reports all required CPU/memory capabilities but cannot currently launch through the adapter. Compiler example requires explicit downloads; native local remains selectable through reviewed backend setting.
Counterexamples: missing executable/invalid or linked/oversized output must fail closed; no shell/PATH fallback, weakened cgroup bounds or forged verified result. Mode switching must preserve drafts. Inspecting UI must not change live config or install tools.
In scope: image_build_runner executable resolution/captured-output contract and public negative tests; SettingsList isolation ordering/inline existing-image editor; ProjectImage aligned fields, explicit download selection, distinct action/status/evidence steps and localized actionable errors; focused proof and docs.
Out of scope: new data/API/config schemas, builder installation, model/forge calls, automatic host tooling, release/branch/planning changes, full suites/aggregate --run, unrelated component changes.
Constraints: same checkout/branch and continuing same #22 corrective task-specific autopilot/local commit/DCP authorization. Bound candidate to 20 files, two review correction rounds and individual test/build commands. Live checks bounded to native Docker info and, if current saved source is a no-download canonical template, one explicit image build; no applying that image or config mutation.
Success signals: adapter receives absolute executable argv and preserves real exit/timeout plus bounded UTF-8 redacted streams; public negative tests reject unsafe output. Backend and image precede advanced settings; editor/controls use consistent spacing, narrow-screen wrapping and visible next actions. Live reload shows corrected layout and real runtime evidence.
Evidence: OBSERVED ProjectImage.tsx, App.tsx, styles.css, image_build_runner.py, local_process.py and local_child.py; signed-in live supplied URL and SSH read-only retained stderr. Docker info under normal and isolated auth home succeeds with required capabilities. STATED user wants actual page checked. INFERRED this is correction of the same deployed #22 contract.
Assumptions: Existing task-local autopilot/focused proof/local commit and human DCP replacement authorization persist. Current monitoring/data/auth preserved. Existing-image apply remains human-controlled.
Unknowns: Base executor/tool content and real legacy-builder availability after client repair; must inspect rather than claim full live acceptance.
Decision-blocking questions: none.
Proposed behaviors: execution backend first; image workspace next with inline reviewed existing-image editor; remaining isolation settings collapsed below. Aligned source/check columns and visible downloads, spaced action/evidence blocks, explicit save-before-build guidance and localized failure diagnosis. Resolve only the native client executable against controlled PATH; read only owned bounded output files.
Path and reason: quick contract repair. No new externally observable contract=yes (existing documented build/presentation behavior restored); no new interface/data format=yes; no dependency=yes; existing requirements cover=yes; security/data handling unchanged=yes (existing ownership/redaction retained). Tightly coupled work, no children.

## Requirement coverage

REQ-REL-2cbd8d83 covers the production bounded client and authoritative output. REQ-UX-1b9b5789 covers compact backend-aware image flow, explicit policy/status/errors and reviewed selection.

## Design

Keep LocalProcessController/local_child unchanged. ImageBuildRunner resolves argv[0] against supplied controlled PATH before ownership launch; after run_files, validate/read owned stdout/stderr <=65536 bytes, strict UTF-8 and existing redaction, preserving actual result status. SettingsList retains one setting editor/candidate path; its image editor is rendered inline by ProjectImage. Backend row and workspace lead the isolation group; other rows remain reachable under advanced details. Downloads stays an explicit saved policy and no example is automatically inserted.

## Log

- 2026-10-07 frame: live user-page and retained server evidence scoped repair of the same #22 runtime/presentation contracts. Quick path under standing task-specific autopilot; branch unchanged, no children. BMAD renderer/setup skill remain unavailable as previously reported; repository AEGIS workflow continues. Product/native adapter source is in scope; packaging/deployment uses repository operations directly.

- 2026-10-07 build red REQ-REL-2cbd8d83: `.venv/Scripts/python.exe -m pytest -q tests/test_image_build.py -k "owned_image_client"` from 04_Software; exit=1, five expected failures expose relative argv, missing bounded stream validation and missing executable dispatch; linked-output case skipped on Windows symlink privilege. REQ-UX-1b9b5789: `npx playwright test e2e/images.spec.ts --grep "environment setup" --workers=1`; exit=1, backend Edit action lies outside the viewport behind the 32-row group.

- 2026-10-07 build green: initial focused backend proof 73 passed/two skipped, 13 helpers, type/build and five offline browser journeys passed; final captured-output redaction and failure-entry/stale-read proof is included in final validation. Reviewed desktop/mobile screenshots show aligned source/check fields, spaced controls and mobile stacking. Source resolves native executable, returns bounded strict UTF-8 redacted files and retains status; UI moves backend/image ahead of advanced rows with inline editor, visible downloads and three explicit steps. Nineteen candidate files within twenty-file bound; final proof follows after review.
- 2026-10-07 DEVIATION build: added six bounded no-network, non-root, read-only tool probes of the observed existing DCP ADORE base/Python images to establish deployment prerequisite compatibility. Base pi-0.87.1 has Python/Pi but no pytest; configured Python/Pi image has all three saved checks. The template's canonical :1.0.0 base tag is absent. No model/forge calls or installation. Native-client errors and missing canonical alias are distinct observed blockers.

- 2026-10-07 validate semantic review: reviewed all nineteen candidate paths against both requirements, current spec and recorded design. Native controller, scope ownership, cancellation, source/config schema, queue/apply and immutable image verification remain shared and unchanged. Adapter resolves only native argv[0], rechecks stream ownership/64 KiB/strict UTF-8 and redaction while preserving real result. UI retains server guards, one candidate editor and draft preservation; automatic evidence reads bind the currently selected operation and discard late old responses. Local/Dev boundaries and four-locale text remain. Architecture diagram still describes actual components; project context, operator/component documentation and current knowledge reconciled before proof. No unrelated paths/dependency/planning changes.
- 2026-10-07 validate explicit review round 1: specification_compliance=approved, separately assessed user live findings, exclusions, current requirements/spec/design, primary controls, responsive layout and real-client semantics. implementation_quality=approved, separately assessed executable resolution, owned bounded files, actual exit/timeout/redaction, no weakening of native scopes, single editor/focus state, current-operation read races, accessible labels and positive/negative test seams. Both independent criteria are assessed by this agent on the same candidate; no separate reviewers or children claimed.
- 2026-10-07 DEVIATION validate: standing same-session #22 focused-proof restriction substitutes image/backend/API tests, image/settings helpers, six browser journeys, application/E2E type/build, targeted Ruff and strict advisory without --run for full suites/aggregate --run. Two Windows symlink cases are skipped under missing symlink privilege; live Linux ownership and actual worker build will supply separate deployment evidence, while full/platform/model/forge acceptance remains deferred.

- 2026-10-07 consolidated final proof: final unchanged nineteen-file candidate, all commands exit=0. `.venv/Scripts/python.exe -m pytest -q tests/test_image_build.py tests/test_web_image_build.py`: 73 passed/two Windows symlink skips/one existing Starlette deprecation warning (33.48 s). Targeted Ruff on image_build_runner.py/test_image_build.py passed. `npm run build:e2e`: application/E2E types and production Vite build passed; `node --test tests/imageBuild.test.mjs tests/settings.test.mjs`: 13 passed. `npx playwright test e2e/images.spec.ts --workers=1`: six passed, including aligned desktop/mobile, define/build/review/apply, local/Dev/paused boundaries, inline focus/draft preservation, automatically loaded actionable failed output, oversized response refusal and delayed-old-operation read rejection. Semantic visual review of desktop/mobile screenshots: aligned fields, separated steps/results, visible downloads and no narrow overflow. Final evolution at 2026-10-07T20:08:46Z lists twelve reviewed non-agentic modifications, zero added/removed product files; total nineteen with governance/journal. `git -c core.safecrlf=false diff --check` passed. Strict advisory without --run: zero errors/eight baseline warnings/25 notes, no current-journal defect. Warnings are two stale catalog paths, one tracked-sidecar finding and five old journal findings. Existing Vite >500 KiB and NO_COLOR advisories accepted. Both criterion verdicts remain approved. Full/platform/model/forge acceptance deferred under the recorded focused scope.
- 2026-10-07 delivery presentation: nineteen source/test/docs/governance paths, both approved criteria, actual focused proof and warnings/exclusions presented. No children, branch/release/dependency changes, push/PR/MR/merge or model/forge actions. Standing human DCP replacement authority remains; manual missing-base alias uses the installed compatible Python/Pi image with successful Python/Pi/pytest probes, preserving existing image names and profile configuration. Planned actual GUI build uses the unchanged saved canonical template, offline network and existing bounds; no image/config apply. External outcome is recorded only after success.

- 2026-10-07 deliver outcome: committed unchanged validated nineteen-file candidate as 8c579e6ddc0eeaf73e37306e953b9749cd949e80. Authorized test replacement succeeded; source /home/dpasare/apps/adore/dcp-fix-8c579e6/04_Software, private root:0700 backup /home/dpasare/apps/adore/backups/dcp-fix-8c579e6-20261007T201551Z with root:0600 165265609-byte home archive. Rollback not needed. Schema 14/one user/98 audit/two failed and fourteen succeeded operations preserved across switch. All six config files subsequently compared byte-for-byte equal to backup. Both services active/running, zero restarts, delegated cgroups checked; independent pinned-certificate LAN smoke confirms ready worker/HTTP200/new exact compiled bytes and protected API401. No full public TLS trust acceptance claimed.
- 2026-10-07 deliver prerequisite and actual proof: additive canonical adore-executor-base:1.0.0 alias points to installed compatible adore-executor-python:pi-0.87.1 immutable sha256:4ed34fa72d5d242739110d29e209d0e2af5d821369c9986a86b1f221571c3fb3; no download/install or existing-tag replacement. Real signed-in GUI built unchanged saved canonical template with network none/600 seconds/1024 MiB; operation 8379ee55011c4403a88dbe3ec4c718a6 Verified, actual Python 3.12.14/Pi 0.87.1/pytest 9.1.1 checks exit successfully. Built image sha256:26881dde6e5fd96622329d6e62eeb9c77655a3216e8afceaa901431d3d39b87c. Real bounded output/technical evidence inspected. Verification container removed, queue idle; expected one succeeded operation/two audit rows added by this build. Use image/config apply not performed. Existing image -> Change opens inline editor, canceled without mutation; source/check layout and result reviewed live, JPEG proofs saved in ignored delivery output. Current profile image and all configs unchanged.
- 2026-10-07 close-out: authorized implementation and DCP outcome completed; journal-only close-out follows observed outcome on the same branch. No children, push/PR/MR/merge or model/forge actions. Report-time ninth warning was the then-open current delivery checklist; baseline eight advisories and focused verification exclusions remain documented. Local deployment report and live screenshots under 07_Delivery/adore-web-dcp-fix-8c579e6. Full suites/platform/model/forge acceptance remains deferred; no pending action in this task.

## Rulings

- RULING-001 | date=2026-10-07 | decision=Continue same-session corrective autopilot, focused validation, local commits and authorized DCP test replacement | reason=User reports deployed #22 outcome still broken and explicitly supplies signed-in live page for inspection; standing human authority persists | source=user | supersedes=none

## Handoff


current: done
status: completed
next: User may review/use the verified image; full acceptance remains deferred.
must_read: .agentic/tasks/TASK-363f96ed.md, .agentic/steps/6_deliver.md
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: native image client and readable environment workflow deployed to DCP
evidence: 73 backend, 13 helpers, six browser journeys; real DCP GUI build Verified; configs preserved
issues: two Windows symlink skips; eight baseline advisories; full acceptance deferred
next: user review of verified image; full acceptance deferred
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-07)

- stage: deliver; type: fix; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-REL-2cbd8d83 - Build project images through bounded durable owned operations
  - REQ-UX-1b9b5789 - Provide compact backend-aware project image flow
- deviations: 2 recorded
  - build: added six bounded no-network, non-root, read-only tool probes of the observed existing DCP ADORE base/Python images to establish deployment prerequisite compatibility. Base pi-0.87.1 has Python/Pi but no pytest; configured Python/Pi image has all three saved checks. The template's canonical :1.0.0 base tag is absent. No model/forge calls or installation. Native-client errors and missing canonical alias are distinct observed blockers.
  - validate: standing same-session #22 focused-proof restriction substitutes image/backend/API tests, image/settings helpers, six browser journeys, application/E2E type/build, targeted Ruff and strict advisory without --run for full suites/aggregate --run. Two Windows symlink cases are skipped under missing symlink privilege; live Linux ownership and actual worker build will supply separate deployment evidence, while full/platform/model/forge acceptance remains deferred.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 631f857: 19 file(s) changed, 461 line(s) added
- checks: errors=0 warnings=9 notes=25
- checklist: 2/5 done; open: implementation commit delivered; DCP backup/replacement and actual GUI build verified; journal close-out committed after external outcome
