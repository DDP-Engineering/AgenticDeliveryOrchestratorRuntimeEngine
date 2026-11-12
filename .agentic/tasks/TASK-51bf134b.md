<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-51bf134b - [Direct] Suggest the verification command from repository files

stage: specify
type: feature
path: full
interaction: autopilot
requirements:
parent:
branch: adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-65
base: 76bd110f2fac4716936bb51caa9226d1b0195f21
opened: 2026-11-12

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [ ] every accepted behavior is one coverage row with exactly one requirement
- [ ] each error or failure response has its own requirement
- [ ] each requirement is one self-contained "shall" sentence
- [ ] verification names setup, trigger, oracle and a boundary or failure
- [ ] specs written only where the requirement cannot carry the detail
- [ ] conflicts, assumptions and unknowns resolved or recorded
- [ ] every ID on the journal's `requirements:` line; `check` shows no
      format errors

## Frame

Problem:
- STATED (ticket #65, Goal): operators enrolling a repository without AEGIS
  should not have to discover its verification command unaided.
- OBSERVED (`04_Software/adore/web/app.py`, `_prepare_project`;
  `04_Software/web/src/EnrollmentWizard.tsx`, `initial`/`runPreview`): web
  enrollment accepts an optional exact command, initially empty, but its
  preview currently returns no repository-derived suggestion or provenance.
- OBSERVED (`04_Software/adore/wizard.py`, `run_wizard`/`_assemble_sections`):
  CLI init has clone discovery and informational AEGIS reporting, but no
  verification-command prompt or suggestion.

Desired outcome:
- STATED (ticket #65): for a repository without AEGIS, enrollment pre-fills
  Verification command from repository files and identifies its source;
  `adore init` offers the same suggestion as the default answer. A human
  keeps, edits or clears it. A suggestion is not execution or verification.
- STATED (ticket #65, Web): AEGIS repositories get no suggestion; Settings
  never overwrites a saved command with a suggestion; human Create or Save
  remains the persistence boundary.

Actors:
- STATED (ticket #65): the human enrolling/configuring the repository, the
  web enrollment interface/API, and the CLI init wizard.
- INFERRED (ticket's pure-function boundary): clone files are untrusted
  evidence, not an actor authorized to choose or execute a command.

Primary scenario:
1. STATED (ticket #65): an operator enrolls a clone without AEGIS or runs
   `adore init` against it.
2. STATED (ticket #65, Decisions): one pure reader examines repository-root
   file names and relevant manifest contents, applying the ordered table.
   Only if the root has no match does it examine first-level directories;
   exactly one matching directory yields `cd <dir> && <command>`.
3. STATED (ticket #65): the web field receives the suggestion and shows
   `Suggested from <file>`; CLI init uses the same command as its default.
4. STATED (ticket #65): the operator keeps, changes or clears the command,
   then explicitly creates/saves the profile. No suggestion runs here.

Examples:
- STATED (ticket #65 table): root `package.json` with a real `scripts.test`
  and no specified alternative lockfile suggests `npm test`, sourced from
  `package.json`.
- STATED (ticket #65 table): root `pyproject.toml` with `uv.lock` suggests
  `uv run pytest -q`; without `uv.lock`, `python -m pytest -q`.
- INFERRED (ticket's first-level rule): no root match and only `service/`
  containing `go.mod` yields `cd service && go test ./...`, sourced from
  `service/go.mod`.
- INFERRED (ticket's ordered-root rule): a matching root JavaScript manifest
  wins over a matching root Python manifest and matching child projects.

Counterexamples:
- STATED (ticket #65): malformed `package.json` gives no suggestion and no
  error; npm's no-test-specified placeholder is not a real test script.
- STATED (ticket #65): ignore an external-target manifest symlink and files
  over 1 MiB; two matching first-level directories give no suggestion.
- STATED (ticket #65): a repository with AEGIS gets no suggestion, and an
  existing saved setting is not replaced by repository discovery.

In scope:
- STATED (ticket #65): a pure helper in `04_Software/adore/verification_hint.py`
  (or an existing suitable module), returning `(command, source file)` or
  nothing, reading file names/manifest contents only.
- STATED (ticket #65): these ordered root matches, with child fallback only
  after no root match:

  | Found | Suggested command |
  |---|---|
  | `package.json` with a real `scripts.test` | `npm test`; `pnpm test` with `pnpm-lock.yaml`; `yarn test` with `yarn.lock` |
  | `pyproject.toml`, `pytest.ini` or `tox.ini` | `uv run pytest -q` with `uv.lock`, otherwise `python -m pytest -q` |
  | `go.mod` | `go test ./...` |
  | `Cargo.toml` | `cargo test` |
  | `pom.xml` | `mvn -q test` |
  | `build.gradle` or `build.gradle.kts` | `./gradlew test` with `gradlew`, otherwise `gradle test` |
  | `*.sln` or `*.csproj` | `dotnet test` |
  | `Makefile` with a `test:` target | `make test` |

- STATED (ticket #65): enrollment preview in `adore/web/app.py`, CLI wizard,
  `EnrollmentWizard.tsx` and four-locale copy; offline helper, API, wizard,
  browser and relevant boundary tests.
- STATED (ticket #65 and AGENTS.md): Projects help in en/fr/de/ro,
  `01_Documentation/Web_Interface.md`, `Configuration_Reference.md`, owning
  component documentation in `05_SoftwareDocu/`, root CHANGELOG, and a
  four-locale release note. Build logs must say `release-notes: added` and
  `help: updated`.
- STATED (AEGIS guidance and repository component rules): task-scoped
  requirements/coverage and component knowledge are maintained in the
  appropriate later stages; frontend source/help changes require the
  committed production static bundle to be rebuilt.

Out of scope:
- STATED (ticket #65): running or validating a suggested command.
- STATED (plan sections 1 and 4.7): installing/upgrading/editing target AEGIS,
  changing workflow selection, direct execution/recovery, ticket selection,
  isolation, budgets, approval, publication or the review loop.
- STATED (AGENTS.md): stored-data migrations, legacy-format readers or
  compatibility paths; no deployment/setup-script tests.
- STATED (executor authority): no commits, pushes, PR creation/merge,
  credential access, AEGIS payload edits or child task journals.
- STATED (current-session instruction): specify, design, implementation and
  validation are not performed during this frame session.

Constraints:
- STATED (ticket #65): suggestion discovery never executes commands, uses
  the network or follows links outside the clone; it ignores files larger
  than 1 MiB and does not add matching rules beyond the supplied table.
- STATED (ticket #65): if another rule becomes necessary, or a conflict with
  the plan/code prevents the requested decisions fitting, ask in
  `ADORE_QUESTIONS.md` and pause blocked rather than invent behavior.
- OBSERVED (plan sections 1 and 4): ticket #65 agrees with the direct-workflow
  decision and section 4.5's pure-reader, ordered-match, child-fallback and
  human-save boundaries; no scope conflict found.
- OBSERVED (`_prepare_project` and existing enrollment workflow test): a new
  URL destination may not exist until Create; its observation is
  `not-inspected`. Preview does not clone. Existing matching clones can be
  inspected. Suggestions must not introduce cloning/network into preview.
- OBSERVED (`runPreview`): review command equality and config/draft digests
  currently bind the exact submitted command. Suggestion presentation must
  preserve explicit human edits/clearing and canonical reviewed persistence.
- OBSERVED (`ConsoleAsker.read`): Enter currently accepts a prompt default;
  CLI implementation must preserve the requested ability to clear a
  suggestion without silently redefining all existing prompt semantics.
- STATED (AGENTS.md / Code_Style.md): standard-library portable Python,
  minimal maintainable changes, licensed/Doxygen-documented files, LF text,
  no new product dependency required by the ticket.
- STATED (ticket #65 testing rules): offline existing fakes; targeted runs
  during build, full suite once in validate via the strict AEGIS gate.
- OBSERVED (`git branch --show-current`): checkout equals journal branch
  `adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-65`.
- STATED (conductor instruction): autopilot is already recorded; exactly one
  stage in this session. INFERRED execution bound for frame: at most 30
  minutes, one journal file changed, no product edits or test runs; the
  conductor's external limits remain authoritative.

Success signals:
- STATED (ticket #65 Done when): table-driven proof of every matching row,
  including first-level `cd <dir> && ` behavior; negative proof for malformed
  and placeholder npm scripts, external manifest links, ambiguous matching
  children and a manifest over 1 MiB that is not read.
- STATED (ticket #65): API and e2e demonstrate direct enrollment suggestion
  plus source, no AEGIS suggestion, and human-only saving; wizard tests
  demonstrate the same suggestion as the default answer.
- STATED (ticket #65 / AGENTS.md): protect saved settings and explicit edits
  or clearing; prove public happy paths and negative trust boundaries without
  live external tools or network.
- STATED (ticket #65): four Projects help locales, operator/component docs,
  CHANGELOG and four-locale release note agree with implemented behavior.
- STATED (ticket #65 Validation): later stages run targeted Python tests,
  Ruff, npm tests/typecheck/build:e2e, enrollment/help Playwright journeys,
  release-note check against task base, and final strict AEGIS validation.

Evidence:
- STATED: user ticket #65 (Goal, Decisions, Scope, Done when, Validation,
  Working rules) is the requested behavior and authority; dependency is #64.
- OBSERVED: `00_Planning/2026-11-10_Direct_Workflow_Without_AEGIS/PLAN.md`
  sections 1 and 4 establish compatible workflow/suggestion boundaries.
- OBSERVED: `.agentic/context/project.md`, `environment.md`,
  `.agentic/knowledge/wizard.md` Routing and web-interface.md Routing/Change
  map locate the existing CLI, API, browser and offline proof surfaces.
- OBSERVED: `04_Software/tests/test_web_enrollment.py` has exact command
  review/save and direct/aegis/not-inspected preview/check/create fixtures;
  `tests/test_wizard.py` covers default workflow omission and missing/present
  AEGIS guidance. These test definitions were inspected, not executed.
- OBSERVED: `04_Software/web/e2e/enrollment.spec.ts` already has four-locale
  direct/AEGIS enrollment and edited/cleared-command journeys, suitable for
  extending with repository suggestions.
- OBSERVED: `04_Software/web/src/i18n.ts` owns existing four-locale command
  names/help; enrollmentCopy.ts owns enrollment guidance. Both are potential
  copy integration points rather than a forced new localization mechanism.
- OBSERVED: existing REQ-DATA-71366af6 protects command serialization and
  REQ-FUNC-51f29b04 protects exact reviewed settings saves; neither establishes
  repository-derived hints.
- OBSERVED: `brief TASK-51bf134b`, `components` and branch inspection exited
  0. Initial working tree was clean. No product validation has run at frame.

Assumptions:
- INFERRED (ticket scope and current CLI/API): reuse the existing optional
  `workflow.verify_command` and human-reviewed save machinery, not a new
  stored setting or alternate workflow selector.
- INFERRED (cross-layer scope): one integrated full task suffices; no child
  task is needed or authorized.

Unknowns:
- UNKNOWN: exact helper name, preview suggestion field shape and transient
  client-state implementation; choose in design without expanding the
  accepted command table or persistence boundary.
- UNKNOWN: detailed CLI presentation for retaining/editing/clearing the
  default; design must honor both the ticket and the observed prompt contract.
- UNKNOWN: targeted and full-suite outcomes, installed build/browser
  dependencies and native-platform acceptance; no success is claimed from
  reading test definitions.
- UNKNOWN: forge completion metadata for #64 was not accessed; its relevant
  enrollment and exact-command surfaces are present in this checkout.

Decision-blocking questions:
- INFERRED (request, plan and inspected integration points): none established
  for framing this scope. Any necessary extra matching rule or unresolved
  behavioral conflict discovered later must use the ticket's questions-file
  and blocked-pause procedure, not an implicit default.

Proposed behaviors:
- STATED (ticket #65; accepted task scope, not additional proposals): the
  bounded pure matcher supports useful defaults; direct-only enrollment
  provenance supports informed human choice; CLI uses the same helper;
  explicit save/edit/clear authority and saved-setting protection prevent
  discovery from becoming autonomous configuration or execution.
- INFERRED: no additional product behaviors proposed at frame. Internal API
  shape and presentation choices remain for design, not accepted new rules.

Path and reason:
- STATED (AEGIS frame criteria): choose full if any quick criterion is no or
  unknown.

  | Quick criterion | Holds? | Evidence |
  |---|---|---|
  | no new externally observable behavior | no | STATED ticket #65 adds repository-derived defaults and visible provenance |
  | no new interface or data format | no | STATED ticket #65 adds preview suggestion output and a CLI default prompt |
  | no new dependency | yes | INFERRED manifest/file reading can use the established Python standard library |
  | an existing requirement already covers the behavior | unknown | OBSERVED related serialization/save requirements do not establish hints; precise coverage belongs to specify |
  | no security or data-handling change | no | STATED ticket #65 adds bounded reading of untrusted clone manifests and link containment |

- INFERRED: full path is required for this cross-layer new behavior and trust
  boundary, even though the implementation should remain small. Retain
  `path: full` and `interaction: autopilot`. Scope is recorded under the
  conductor's explicit autopilot authority; stop immediately after advancing
  frame to specify.

## Requirement coverage


## Design


## Log

- 2026-11-12 frame: journal opened
- 2026-11-12 frame: Frame scope recorded under conductor-authorized autopilot. Full path retained: new externally visible repository-derived defaults/provenance, additive preview/CLI interface and untrusted file-reading boundary fail quick criteria. Plan sections 1/4 and existing DW-04 enrollment/command surfaces inspected; no framing blocker established. Preserve explicit human save/edit/clear authority, absent-clone not-inspected behavior, saved Settings and AEGIS isolation. Frame changes only this journal; no product tests run.
- 2026-11-12 frame: completed; next specify

## Rulings


## State

status: ready
reported: frame - completed
next: start specify: read .agentic/steps/2_specify.md
must_read: .agentic/tasks/TASK-51bf134b.md, .agentic/steps/2_specify.md
changed: Completed the evidence-labelled Frame, matching table, scope/exclusions, constraints, success signals and full-path criteria; all frame checklist items met; only the pinned journal changed.
evidence: brief TASK-51bf134b, components and git branch --show-current exited 0; git diff --check exited 0; source/test definitions inspected, no product tests run in frame.
issues: No framing blockers established; helper/API shape, CLI presentation and test outcomes remain for later stages.
spec_compliance:
implementation_quality:
review_round:
