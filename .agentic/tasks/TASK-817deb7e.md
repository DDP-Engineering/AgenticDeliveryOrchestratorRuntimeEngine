<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-817deb7e - Manage portable executor recipes and complete project exports

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-e5c8a96f, REQ-FUNC-c2cbfa1b, REQ-SEC-409d6c82, REQ-UX-3534628b, REQ-FUNC-4404d38b, REQ-REL-0f5a1e11, REQ-REL-aa0c1685, REQ-DATA-65ebe5f6, REQ-SEC-c3a134af, REQ-NFR-5e0f55d9
parent:
branch: master
base: be69854ab09bb4e52e8cbe26e59b1ecf9dd62f1a
opened: 2026-11-11

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [x] diff reviewed against scope, requirements, design, error paths,
      portability, security and unrequested work
- [x] knowledge pages of changed components current with the reviewed code
- [x] project and environment context reconciled with the candidate
- [x] requirements re-read: status, prose, verification, paths and links true
- [x] manual or inspection verification recorded where applicable
- [x] explicit review approved, when enabled
- [x] final `check --strict --run` result logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem:
OBSERVED: build_bundle.py exports a Git-registered recipe only; selecting an image does not retain its sources. The previous turn added a source-only recipe for ADORE, not generic recipe management.
Desired outcome:
STATED: manage recipes for every monitored project and export saved configuration plus the complete executor image definition through a simple interface.
Actors:
STATED: administrators managing monitored projects; developers retain their existing read-only scope.
Primary scenario:
INFERRED from the accepted request: an administrator uploads one Dockerfile or context ZIP for an external image; ADORE retains it by image, reuses it across projects, and exports the definition and local-base definitions with configuration.
Examples:
OBSERVED: the standard ADORE base has known source files; the synthetic ADORE recipe starts at Ubuntu; another project can extend an ADORE base and require its definition in the same export.
Counterexamples:
OBSERVED: an image tag alone cannot establish the original Dockerfile/context; an unavailable local base must not yield a supposedly complete export.
In scope:
STATED: generic recipe retention/association, dependency-complete exports, simple UI. INFERRED: immutable bounded recipe snapshots, automatic built-in base recipe, image-shared reuse, plain Dockerfile/ZIP attachment, missing-base recovery, structural validation and trust-boundary tests, and documentation in four locales.
Out of scope:
STATED: no push. User requested a definition rather than image binaries. Repository rules exclude migrations. Existing environment ownership keeps actual image building outside the web worker. No server deployment or modification of running/parked jobs is requested.
Constraints:
OBSERVED: master is the current/default branch; keep it. Preserve pre-existing working changes (synthetic recipe/docs and TASK-b8a190d4). Metadata attachment must not rewrite project configuration, pending edits, execution policy, credentials or job state. Offline tests use injected Git/runtime seams. Bound work to 8 hours, 80 task-owned files and five review/fix cycles; no autonomous model/forge jobs.
Success signals:
INFERRED: two projects using one image resolve the same retained recipe; an export reconstructs the declared image chain without preinstalled local bases; missing/corrupt inputs fail closed; the built-in base exports without manual registration; native projects export their TOML; a concise dialog attaches/updates definitions without Git hashes; existing raw previews remain available.
Evidence:
OBSERVED: 04_Software/adore/build_bundle.py, web/app.py raw config route, web/src/RawConfiguration.tsx, Project_Executor_Images.md, .agentic/knowledge/project-images.md, current Git status and AEGIS status.
Assumptions:
INFERRED: a shared association by exact image tag is appropriate because projects selecting that image share its build definition. Replacements require the observed recipe digest to avoid overwriting a concurrent update.
Unknowns:
UNKNOWN: original recipes for external images on DCP. Source archives can be supplied through the generic interface; no synthetic reconstruction is claimed automatically.
Decision-blocking questions:
None; the user accepted the preceding proposal and autopilot=true remains active.
Proposed behaviors:
Accepted for implementation under autopilot: retain uploaded sources independently of jobs; automatically resolve known built-in/local-base sources; report missing bases and let the same attachment dialog add them; default container exports to the complete bundle, retaining an explicit TOML-only choice. Preserve authorization, CSRF, bounds and typed failures from existing export/config APIs.
Path and reason:
Full path: new public management interfaces and stored recipe records are required.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | shared retained definitions and default complete export |
| no new interface or data format | no | recipe attachment API and current-schema snapshot store |
| no new dependency | yes | standard library plus existing FastAPI/React tooling |
| existing requirement already covers behavior | no | aegis explain reports no requirement for build_bundle.py |
| no security or data-handling change | no | uploaded archives and retained build inputs |

## Requirement coverage

| Requirement | Behavior / verification | Design |
|---|---|---|
| REQ-FUNC-e5c8a96f | When an administrator saves a validated executor recipe, ADORE shall retain its source snapshot associated with the exact image tag for reuse by projects selecting that image. | recipe store, resolution/export, API or dialog as applicable |
| REQ-FUNC-c2cbfa1b | When an administrator requests a container project's complete configuration export, ADORE shall return saved configuration and all declared executor and locally built base-image definitions in a portable source ZIP. | recipe store, resolution/export, API or dialog as applicable |
| REQ-SEC-409d6c82 | If uploaded executor recipe input violates the bounded source-archive contract, ADORE shall reject it with a typed validation error before retaining any source or association. | recipe store, resolution/export, API or dialog as applicable |
| REQ-UX-3534628b | When an administrator opens project configuration export, the interface shall offer complete container export and recipe attachment or replacement within its compact dialog. | recipe store, resolution/export, API or dialog as applicable |
| REQ-FUNC-4404d38b | When a recipe references ADORE's standard executor base image, ADORE shall resolve its bundled build definition automatically. | recipe store, resolution/export, API or dialog as applicable |
| REQ-REL-0f5a1e11 | If a recipe association changes after an administrator previews a replacement, ADORE shall refuse the stale replacement with HTTP 409. | recipe store, resolution/export, API or dialog as applicable |
| REQ-REL-aa0c1685 | If a complete export requires an unavailable local image definition, ADORE shall refuse the export with a typed missing-image error identifying the required image. | recipe store, resolution/export, API or dialog as applicable |
| REQ-DATA-65ebe5f6 | If retained executor recipe data is corrupt or uses an unsupported schema, ADORE shall refuse that recipe with a typed error naming the stored data to delete without rewriting it. | recipe store, resolution/export, API or dialog as applicable |
| REQ-SEC-c3a134af | When a caller requests executor recipe management, ADORE shall enforce administrator authorization and same-origin CSRF mutation checks before reading or writing recipe sources. | recipe store, resolution/export, API or dialog as applicable |
| REQ-NFR-5e0f55d9 | When an administrator manages executor recipes, ADORE shall preserve project configuration, pending settings, credentials and job state unchanged. | recipe store, resolution/export, API or dialog as applicable |


## Design

### Approach

REQ-FUNC-e5c8a96f: a standard-library recipe module owns bounded upload parsing,
immutable source snapshots and exact-image bindings. Metadata lives outside
project config/job stores, preserving REQ-NFR-5e0f55d9. A retained definition
can be incomplete only because local bases are missing; export remains closed.
REQ-FUNC-c2cbfa1b / REQ-REL-aa0c1685: resolve a bounded graph from embedded,
retained, immutable Git and built-in definitions. Compose additional_contexts
link local images to their build services without changing Dockerfile bytes.
Docker's named-context image override and Compose service contexts are confirmed
by the official Docker build-context and dependent-images documentation.

### Interfaces and data

The specification defines one current source format and schema-1 image binding.
REQ-SEC-409d6c82: archive/path/size/credential/graph validation precedes retention.
REQ-DATA-65ebe5f6: selected corrupt bindings/objects fail closed with a recovery
path; no fallback hides corruption. REQ-REL-0f5a1e11: atomic association under a
catalog lock uses the observed binding digest; config revision binds the project.
REQ-FUNC-4404d38b: ship the existing base Dockerfile and Pi inputs as wheel assets
using hatch force-include; development reads the same canonical source files.
No copied setup script source is introduced under the product package.

### Files and test seams

executor_recipes.py contains source/store/graph contracts; build_bundle.py keeps
the existing injectable Git reader and packages resolved recipes. app.py adds
three scoped endpoints and uses the same resolver for complete export. The
RawConfiguration dialog loads availability, attaches/replaces sources and selects
complete export by default; existing App wiring supplies CSRF and container mode.
REQ-SEC-c3a134af: existing auth/CSRF dependencies guard all metadata and sources.
Tests: test_executor_recipes.py, test_web_executor_recipes.py, existing raw export
contracts and portable.spec.ts. REQ-UX-3534628b: all four locales/help and mobile
dialog behavior are checked; production assets rebuild with source changes.

### Risks and open decisions

Archive inputs and Dockerfile references are untrusted, never executed. Static
checks establish declared source completeness, not successful package downloads
or a byte-identical image. Public registries remain explicit prerequisites.
Stored recipes are image-shared; a concise dialog note explains replacement scope.
Previous source-only work remains untouched except documentation integrated with
the new behavior. No deploy, migration, remote write, image build or job resume.

### Requirement map

All ten coverage rows map to the approach/interfaces/test seams above. No open
product decision remains; image binaries and runtime job snapshots are excluded
by the user's source-export request and the accepted Frame.

### Design diagrams

Diagrams: [diagram_TASK-817deb7e.md](diagram_TASK-817deb7e.md)


## Log

- 2026-11-11 frame: journal opened
- 2026-11-11 frame: completed; next specify (7 Done checklist item(s) left unticked)
- 2026-11-11 specify: completed; next design
- 2026-11-11 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-11 build: red: uv run --frozen --extra web python -m pytest -q tests/test_web_executor_recipes.py::test_recipe_status_and_shared_attachment_preserve_project_state exit 1; recipe GET is absent (404), proving the missing public management path before implementation (REQ-FUNC-e5c8a96f, REQ-NFR-5e0f55d9).
- 2026-11-11 build: green: uv run --frozen --extra web python -m pytest -q tests/test_web_executor_recipes.py tests/test_executor_recipes.py tests/test_web_config_raw.py exit 0; 38 passed, one Windows symlink-permission skip. Image sharing, immutable inputs, dependency closure, CAS, permissions and project-state preservation proved.
- 2026-11-11 build: red: npm run build:e2e exit 0; npx playwright test e2e/portable.spec.ts -g 'attach an executor definition' --reporter=line exit 1; the export dialog has no Definition file attachment control (REQ-UX-3534628b).
- 2026-11-11 build: green: focused backend recipe/raw-export proof exit 0; 54 passed without skips. Includes malformed/oversized/unsafe archives, corruption recovery, local graphs, builtin sources, embedded-base reuse, explicit replacement/CAS, Admin/CSRF and byte-preserved configuration/pending/credentials/parked RunState.
- 2026-11-11 build: red/green: additional focused cases first failed for public-looking retained bases, export metadata bounds, long paths, corrupt deflate, effective preparation selection, unsupported instructions/secret defaults, embedded-base sharing and lock I/O. Each was corrected and passes in the 54-test proof; the earlier symlink skip now uses an injected filesystem boundary and passes on Windows.
- 2026-11-11 build: red/green: stage ARG shadowing and loopback-registry cases initially omitted required local bases (2 failed); FROM now uses global arguments and loopback registries require recipes (2 passed).
- 2026-11-11 build: green: npm run typecheck and npx playwright test e2e/portable.spec.ts --reporter=line exit 0; 12 passed. Covers attach/save, rejected/malformed/stale evidence, explicit TOML-only, complete export, focus/Escape, symmetric toolbar, Dev redaction and mobile attachment controls in four locales.
- 2026-11-11 build: Manual: isolated uv wheel build and resource inspection in auto-cleaned temporary storage confirmed canonical Dockerfile, Pi guard/helper and license. An isolated Python import of the extracted wheel resolved all four builtin sources without a checkout. First verification script used the wrong constant import; corrected verification passed without product changes.
- 2026-11-11 build: release-notes: updated (Executors complete-source export, all four locales); check_release_notes.py --since be69854ab09bb4e52e8cbe26e59b1ecf9dd62f1a exit 0.
- 2026-11-11 build: help: updated (Settings export/attachment, Projects ZIP reuse, Interface summary; en/fr/de/ro); help/settings helper proof 35 passed. Production npm run build exit 0; existing Vite chunk-size advisory remains.
- 2026-11-11 build: DEVIATION design: diagram blocks were initially inline without the required sibling file - corrected to diagram_TASK-817deb7e.md with node/edge classification before review; no product decision changed.
- 2026-11-11 build: Inspection: evolution reviewed against design; source/store/API/dialog, tests, four-locale help and product packaging assets match scope. Pre-existing TASK-b8a190d4 and 02_Tools/containers/adore-executor work remain untouched. No live operations, image builds, deployment, commit or push.
- 2026-11-11 build: check: errors=0, warnings=40, notes=24. Remaining warnings concern pre-existing historical requirements/journals/stale hashed assets and the unrelated synthetic recipe, one intentionally fake PEM rejection fixture and generated minified JS not exhaustively scanned. Reviewed source contains no credential material. No task requirement has uncovered source paths.
- 2026-11-11 build: completed; next validate
- 2026-11-11 validate: Review round 1: spec requires validating default-context RUN bind source/src; quality requires stage ENV/ARG-correct COPY/ADD expansion and bounded typed final config rereads on GET/preview/PUT. Public reproductions accept missing context inputs or escape FileNotFoundError. Correct only these trust-boundary findings, then re-review both roles.
- 2026-11-11 validate: returned to build - Review round 1: RUN bind context completeness, stage variable scope and final config read fault boundaries
- 2026-11-11 build: red: review regressions exit 1; 12 failed/3 passed. Missing RUN bind source/src and ENV-selected COPY were accepted; missing config raised FileNotFoundError, oversized source returned wrong status and linked source was accepted. All GET/preview/PUT boundaries exercised.
- 2026-11-11 build: green: review corrections focused backend command exit 0; 69 passed. RUN context binds validate source/src; stage-local ARG/ENV scopes preserve precedence/inheritance and global FROM values; GET/preview/PUT final snapshots are bounded, link-checked and translated to typed config errors. Relevant spec/user/component/knowledge guidance reconciled. Ruff exit 0; frontend unchanged since 12 passing journeys and production build.
- 2026-11-11 build: completed; next validate
- 2026-11-11 validate: Review round 2: both independent reviewers approved. Spec reviewer independently passed3source regressions; quality reviewer independently passed15source/config-race regressions and whitespace inspection. No remaining blocking findings. Evolution refreshed and reviewed, requirements/spec/knowledge/context/manual source-asset inspection reconciled.
- 2026-11-11 validate: final: python .agentic/aegis.py check --task TASK-817deb7e --strict --run exit 1. Python passed882.6s, Ruffpassed0.2s; frontend helpers/type/build passed, Chromium258passed/1failed22.9m. Solefailure unchanged jobs.spec.ts:614 fixture teardown 'Route is already handled' line619. Independentquality review traced pending route.fetch callbacks through unrouteAll fallback to context continue; not a recipe product defect. No other failure or promoted warning. Correct fixture without weakening assertions, then review and prove fresh.
- 2026-11-11 validate: returned to build - Final proof exposed existing lifecycle HTTP fixture teardown race; replace async proxy with validated authenticated snapshot, preserving every assertion
- 2026-11-11 build: red: strict full proof exit1, Chromium258passed/1failed; independent review confirms existing lifecycle fixture proxy race. Test-only correction snapshots one authenticated validated project catalog, fulfills archive-state polls locally and retains every original lifecycle/CSRF/clone/exact-name assertion; no product code or browser deadline changed.
- 2026-11-11 build: release-notes: none (additional correction is test-fixture maintenance; existing feature entry remains updated). help: none (no additional user behavior change). Component/knowledge validation guidance updated; evolution reviewed and release-note checker passed again.
- 2026-11-11 build: green: npm run typecheck exit0; npx playwright test e2e/jobs.spec.ts -g 'project hub lifecycle actions' --repeat-each=3 --reporter=line exit0, 3passed16.9s. All lifecycle/CSRF/confirmation/clone/deletion assertions preserved.
- 2026-11-11 build: completed; next validate
- 2026-11-11 validate: Review round3: both independent reviewers approved integrated candidate and test-only fixture correction. Authentication/array validation added; every original lifecycle/CSRF/clone/exact-name assertion and deadline preserved. No remaining blocking findings; focused3repeats passed.
- 2026-11-11 validate: final: second strict proof interrupted for newly confirmed recipe recovery defect; Pythonpassed710.9s and Ruffpassed0.3s, frontend incomplete and proves no full outcome. Public temp-store inspection showed deleting the named corrupt object leaves dangling associations and repeats the same error. Independent quality assessment recommends explicit whole-catalog recovery for missing/corrupt source objects and collisions; binding-only corruption retains binding recovery. No automatic deletion, all project/job/credential stores preserved.
- 2026-11-11 validate: returned to build - Recovery instruction must actually start fresh: source-object failures name catalog reset; add delete-exactly-reported-data and reattach regression
- 2026-11-11 build: red: three object recovery regressions failed (missing/corrupt/collision) because the reported object deletion leaves associations; one browser negative case failed because catalog-wide reset impact was not explained. Core recovery now names the whole recipe catalog for object faults, while bad bindings keep targeted recovery; deletion remains an explicit operator action.
- 2026-11-11 build: green: 72 focused backend tests passed30.06s; the three recovery regressions delete exactly the reported catalog, observe unregistered state and attach original sources again. Ruffpassed. All12portable browser journeys passed37.2s, including catalog-reset scope warning. Help11tests passed; TypeScript and production build passed.
- 2026-11-11 build: release-notes: updated feature entry remains sufficient; no extra entry for the correction, release-note checker passed. help: updated (all4Settings locales explain explicit catalog reset, all-project recipe scope and preserved configuration/credentials/jobs). Spec, user/component/knowledge contracts now distinguish targeted binding recovery from complete catalog recovery.
- 2026-11-11 build: completed; next validate
- 2026-11-11 validate: Review round4: both independent reviewers approved actionable recovery and integrated candidate. Spec independently passed3recovery tests; quality independently passed7recovery/corruption tests. All-project scope is explicit in4locale UI/help; data deletion is operator-only and project/auth/job stores remain separate. Evolution reviewed after final build; no remaining blocking findings.
- 2026-11-11 validate: final: python .agentic/aegis.py check --task TASK-817deb7e --strict --run exit0 after round4 approvals and last candidate edit. Full Python passed708.4s, Ruffpassed0.2s, full frontend helper/type/build/Chromium command passed1019.9s. Catalog errors0/warnings40/notes24, no promoted warnings. Existing historical journal/requirement/stale-path warnings and unrelated synthetic recipe remain; fake PEM rejection fixture is not a secret, generated minified asset scanner omission is covered by source review and rebuilt/fingerprinted assets. No blocking limitations; no live image/model/forge acceptance or deployment performed.
- 2026-11-11 validate: completed; next done

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-817deb7e.md
changed: Shared executor recipes, complete configuration and image-source export, compact localized dialog, documentation and tests
evidence: Final strict full validation exit 0: Python, Ruff and frontend passed; both independent reviews approved (round 4)
issues: No blockers; 40 advisory warnings documented; live image builds not run
spec_compliance: approved
implementation_quality: approved
review_round: 4

## Delivery report (2026-11-11)

- stage: validate; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-e5c8a96f - Retain shared executor image recipe snapshots
  - REQ-FUNC-c2cbfa1b - Export complete executor image dependency definitions
  - REQ-SEC-409d6c82 - Reject unsafe executor recipe input and corrupt recipe storage
  - REQ-UX-3534628b - Manage executor recipes through a compact project dialog
  - REQ-FUNC-4404d38b - Resolve the bundled ADORE executor base definition automatically
  - REQ-REL-0f5a1e11 - Refuse executor recipe replacement after a concurrent update
  - REQ-REL-aa0c1685 - Keep incomplete local image chains out of project exports
  - REQ-DATA-65ebe5f6 - Refuse corrupt managed recipe records without rewriting them
  - REQ-SEC-c3a134af - Authorize executor recipe management before reading or writing sources
  - REQ-NFR-5e0f55d9 - Keep recipe management independent of project job state
- deviations: 1 recorded
  - design: diagram blocks were initially inline without the required sibling file - corrected to diagram_TASK-817deb7e.md with node/edge classification before review; no product decision changed.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=4
- diff vs task base be69854: 70 file(s) changed, 4026 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=40 notes=24
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended

## Delivery report (2026-11-11)

- stage: validate; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-e5c8a96f - Retain shared executor image recipe snapshots
  - REQ-FUNC-c2cbfa1b - Export complete executor image dependency definitions
  - REQ-SEC-409d6c82 - Reject unsafe executor recipe input and corrupt recipe storage
  - REQ-UX-3534628b - Manage executor recipes through a compact project dialog
  - REQ-FUNC-4404d38b - Resolve the bundled ADORE executor base definition automatically
  - REQ-REL-0f5a1e11 - Refuse executor recipe replacement after a concurrent update
  - REQ-REL-aa0c1685 - Keep incomplete local image chains out of project exports
  - REQ-DATA-65ebe5f6 - Refuse corrupt managed recipe records without rewriting them
  - REQ-SEC-c3a134af - Authorize executor recipe management before reading or writing sources
  - REQ-NFR-5e0f55d9 - Keep recipe management independent of project job state
- deviations: 1 recorded
  - design: diagram blocks were initially inline without the required sibling file - corrected to diagram_TASK-817deb7e.md with node/edge classification before review; no product decision changed.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=4
- diff vs task base be69854: 70 file(s) changed, 4047 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=40 notes=24
- checklist: 9/9 done
