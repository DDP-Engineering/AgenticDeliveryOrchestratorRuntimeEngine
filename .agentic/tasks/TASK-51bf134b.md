<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-51bf134b - [Direct] Suggest the verification command from repository files

stage: design
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-8676b7b9, REQ-FUNC-b360529b, REQ-FUNC-d10b9f52, REQ-FUNC-0a0f15f3, REQ-FUNC-43c92cd6, REQ-FUNC-614738d0, REQ-FUNC-1bd6056c, REQ-FUNC-9ed60681, REQ-REL-cbc3b8e1, REQ-FUNC-1ab66bb2, REQ-SEC-95dddb65, REQ-SEC-ecafbce6, REQ-FUNC-4581cf7c, REQ-FUNC-08a75f14, REQ-FUNC-45ca2605, REQ-NFR-6badc5b8, REQ-FUNC-d50a408d, REQ-FUNC-2bf3e808, REQ-FUNC-357ae298, REQ-UX-92197baa, REQ-UX-dd21046e, REQ-UX-cca17b80, REQ-FUNC-702b0fce, REQ-FUNC-a6e265cd, REQ-FUNC-f753863b, REQ-UX-7f47b773, REQ-FUNC-65db4fd5, REQ-FUNC-b0f69285, REQ-FUNC-6c82ad42, REQ-FUNC-5771eecc, REQ-DATA-c1c4d1c3, REQ-FUNC-51f29b04, REQ-REL-60015e50
parent:
branch: adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-65
base: 76bd110f2fac4716936bb51caa9226d1b0195f21
opened: 2026-11-12

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [ ] design note written under the five headings, or its skip justified
- [ ] each decision cites a requirement ID or a named technical constraint
- [ ] every requirement maps to a decision and test seam, or no design impact
- [ ] risks and open decisions recorded
- [ ] `affected_paths` match the expected files
- [ ] knowledge pages unchanged

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

Authority for accepted behavior rows: STATED ticket #65 Goal, Decisions and
Done when; STATED plan sections 1 and 4.5. Rows marked retained reuse the
inspected existing contract without changing it. The last column is reserved
for the next, design-only session.

| Frame outcome | Atomic behavior | Requirement | Verification | Design decision or no impact |
|---|---|---|---|---|
| Ordered matching, row 1 | Real root scripts.test supplies the JavaScript command/source with the listed lockfile variants | REQ-FUNC-8676b7b9 | Public-helper table fixtures: npm/pnpm/yarn pair or missing-script miss; root and row precedence | |
| Ordered matching, row 2 | First matching Python row supplies pytest command/source with uv variant | REQ-FUNC-b360529b | Each Python filename with/without uv.lock; earlier JavaScript wins and later Go loses | |
| Ordered matching, row 3 | First matching Go row supplies go test ./... and source | REQ-FUNC-d10b9f52 | go.mod pair; Python precedence and child suppression | |
| Ordered matching, row 4 | First matching Cargo row supplies cargo test and source | REQ-FUNC-0a0f15f3 | Cargo pair; Go precedence and child suppression | |
| Ordered matching, row 5 | First matching Maven row supplies mvn -q test and source | REQ-FUNC-43c92cd6 | pom.xml pair; Cargo precedence and child suppression | |
| Ordered matching, row 6 | First matching Gradle row supplies wrapper/plain command and source | REQ-FUNC-614738d0 | Both filenames with/without wrapper; Maven precedence | |
| Ordered matching, row 7 | First matching dotnet row supplies dotnet test and source | REQ-FUNC-1bd6056c | Solution/project pair; Gradle precedence | |
| Ordered matching, row 8 | First matching Make test target supplies make test and source | REQ-FUNC-9ed60681 | Makefile with/without test target; dotnet precedence | |
| Malformed npm boundary | Bad JSON/structure supplies no JavaScript match and no error | REQ-REL-cbc3b8e1 | Malformed/non-object/nontext package fixtures return nothing; real script control | |
| Placeholder boundary | npm's no-test-specified placeholder supplies no JavaScript match | REQ-FUNC-1ab66bb2 | Standard placeholder-only fixture returns nothing; real script control | |
| Clone containment | Outside-linked manifest, command-selection file or directory is ignored unread | REQ-SEC-95dddb65 | External manifest/lockfile/child links with read guards; contained-file control | |
| Bounded file reading | Files over 1048576 bytes are ignored without content reading | REQ-SEC-ecafbce6 | At-limit/one-over manifest fixtures with oversized read guard | |
| Unique child fallback | One matching first-level directory supplies cd-prefixed command/source | REQ-FUNC-4581cf7c | All eight table rows in a child; root and deeper-only boundaries | |
| Ambiguous children | Several matching first-level directories supply no suggestion | REQ-FUNC-08a75f14 | Two matching children in either creation order; single-child and root controls | |
| No match | No eligible root/immediate-child row supplies no suggestion | REQ-FUNC-45ca2605 | Empty/unrelated/deeper-only evidence; qualifying-root control | |
| Pure helper | Root-path discovery is file-read-only and returns pair or nothing | REQ-NFR-6badc5b8 | Match/no-match repeatability, no process/network calls, unchanged file snapshots | |
| Direct preview | Inspected direct clone exposes helper command/source separately from submitted review text | REQ-FUNC-d50a408d | API matching clone pair; explicit empty/edit preserved, no-match control | |
| AEGIS exclusion, web | Present aegis.py suppresses enrollment suggestions | REQ-FUNC-2bf3e808 | API/browser AEGIS-plus-manifest fixture; direct control and broken/presence-only AEGIS | |
| Absent clone boundary | Not-inspected enrollment supplies no suggestion | REQ-FUNC-357ae298 | URL preview with absent destination: no hint/clone/probe; existing direct control | |
| Localized enrollment default | Untouched optional command field uses available direct hint, otherwise empty | REQ-UX-92197baa | Four-locale matching/no-match/uncreated fixtures and canonical review; AEGIS note control | |
| Visible web provenance | Suggested command identifies its source in four locales | REQ-UX-dd21046e | Root/child source guidance; no AEGIS or no-match source claim | |
| Human edit/clear authority | Repeated discovery preserves exact human draft edits or empty choice | REQ-UX-cca17b80 | Edit/clear after prefill; re-preview/check/back navigation and exact chosen Create value | |
| Human-only persistence, retained | Preview returns review/findings without profile publication or tool probes | REQ-FUNC-702b0fce | Existing offline API no-probe preview; add manifest fixture and inspect no profile bytes | |
| Exact enrollment save, retained | Explicit confirmed Create saves exact reviewed command | REQ-FUNC-a6e265cd | Accept/edit/clear hint then compare loaded TOML; stale command revision publishes nothing | |
| Shared CLI default | Direct init prompt defaults to helper suggestion or empty | REQ-FUNC-f753863b | Capture FieldSpec for matching/no-match clone and accept default with fake runner | |
| Visible CLI provenance | Init identifies the source behind its suggested default | REQ-UX-7f47b773 | Capture root/child source guidance; no-match and AEGIS show no claimed source | |
| AEGIS exclusion, CLI | Present aegis.py suppresses init repository suggestions | REQ-FUNC-65db4fd5 | Manifest plus present AEGIS, including unavailable interpreter; direct control | |
| Human CLI choice | Confirmed init saves kept, edited or explicitly cleared command | REQ-FUNC-b0f69285 | Interactive/scripted keep/edit/clear and loaded TOML; cancellation/invalid input no publication | |
| Invalid CLI input, retained | Invalid/unconfirmed answers reprompt or fail fast without profile creation | REQ-FUNC-6c82ad42 | Invalid command answer and cancelled confirmation through existing wizard fakes | |
| Validated CLI publication, retained | Generated config validates before profile writes | REQ-FUNC-5771eecc | Valid chosen command profile and invalid candidate leave-before-write oracle | |
| Saved Settings authority | Saved empty/custom command is never replaced by discovery | REQ-DATA-c1c4d1c3 | Matching clone in Settings; load/unrelated save preserves exact saved value | |
| Exact Settings Save, retained | Human reviewed Save applies exact chosen command under existing guards | REQ-FUNC-51f29b04 | Existing empty/nonempty review/apply and rejected stale/denied/write-failure cases | |
| Preview response trust boundary | Malformed command/source evidence is refused without applying it | REQ-REL-60015e50 | Corrupt suggestion member types/pair/multiline command: visible failure and unchanged draft; valid pair control | |

### Specify analysis and challenge

- OBSERVED (`explain` for wizard.py, web/app.py, EnrollmentWizard.tsx and the
  new helper path; wizard/web knowledge and source/test definitions): no
  existing requirement governs repository-file hint matching. The helper
  path does not yet exist; these are draft contracts, not implemented facts.
- OBSERVED (REQ-UX-92197baa): DW-04 explicitly specified initially empty
  enrollment with no automatic suggestion. STATED (ticket #65 Goal/Decisions)
  now authorizes changing that default. Deliberately revise that requirement
  in place, mark it draft and clear its test links until build updates proof;
  preserve the optional localized field and the AEGIS note. This is the
  requested behavior change, not an unrequested contract rewrite.
- OBSERVED (REQ-FUNC-702b0fce, a6e265cd, 6c82ad42, 5771eecc and 51f29b04):
  preview, exact enrollment persistence, invalid answers, generated-config
  validation and reviewed Settings saves already have matching contracts;
  reuse those five unchanged. REQ-DATA-71366af6 continues to protect generic
  serialization; no change is needed to it or the stored configuration schema.
- INFERRED (ticket human authority plus observed review.verify_command exact
  comparison and candidate digests): preview suggestion evidence must be
  separate from candidate review text; accepting a hint in the browser needs
  a new canonical preview of the resulting human-reviewable draft rather
  than silently modifying the server candidate. Exact transport/state flow
  remains for design.
- STATED (AGENTS.md trust boundaries) / INFERRED (new preview members):
  malformed suggestion response rejection needs its own negative contract;
  it does not authorize another repository-matching rule.
- STATED (ticket malformed-package decision): malformed optional package
  evidence is a hint miss without an exception, unlike persisted-state or
  human-configuration corruption. Record that explicit exception without
  weakening the repository's fail-closed stored-data contracts.
- STATED / OBSERVED (ticket Goal and ConsoleAsker.read): source provenance
  applies to the repository-derived default, and a human must be able to
  clear it even though Enter currently accepts a default. No generic prompt
  semantic change is authorized; exact clearing presentation stays in design.
- INFERRED (coverage audit): eight parameterized root outcomes, ordered/unique
  child fallback, explicit missing/error boundaries, both UI integrations,
  provenance and human persistence together cover the accepted Frame without
  adding toolchain validation, command execution, network lookup or another
  ecosystem. A single shared algorithm spec is justified for root precedence,
  immediate-child counting and exact command strings; the other requirements
  are buildable without separate specs.
- UNKNOWN (retained explicitly in specs/REQ-FUNC-8676b7b9.md): same-row source
  ties, simultaneous JavaScript lockfiles, directory command representation
  and filesystem failures beyond specified cases. No added matching/error
  policy is chosen in specify. These do not prevent recording the stated
  table; if design/build needs an extra rule, use ADORE_QUESTIONS.md and pause
  blocked as instructed. Helper/API names and CLI presentation remain design
  choices; no product test has been run or claimed.
- STATED (ticket scope and repository rules): build must update Projects help
  in en/fr/de/ro, Web_Interface.md, Configuration_Reference.md, affected
  component contracts/knowledge, CHANGELOG and a four-locale release note,
  rebuild committed web assets, and log `release-notes: added` and
  `help: updated`. These are same-change delivery obligations, not additional
  matcher behavior; they remain uncompleted until build/validate evidence.
- INFERRED specify execution bound: at most 45 minutes and 35 task-scoped
  artifact files, all under .agentic/, no product edits or product test runs.
  OBSERVED current branch still equals the journal branch; interaction was
  already autopilot and remains so. End this session at the specify-to-design
  boundary; do not enter design.

## Design


## Log

- 2026-11-12 frame: journal opened
- 2026-11-12 frame: Frame scope recorded under conductor-authorized autopilot. Full path retained: new externally visible repository-derived defaults/provenance, additive preview/CLI interface and untrusted file-reading boundary fail quick criteria. Plan sections 1/4 and existing DW-04 enrollment/command surfaces inspected; no framing blocker established. Preserve explicit human save/edit/clear authority, absent-clone not-inspected behavior, saved Settings and AEGIS isolation. Frame changes only this journal; no product tests run.
- 2026-11-12 frame: completed; next specify
- 2026-11-12 specify: Specify complete: 27 new draft requirements, one deliberate draft revision of REQ-UX-92197baa for ticket-authorized prefill, five existing contracts reused unchanged, 33 one-to-one coverage rows/header IDs and one shared ordered-matching spec. Table-order audit parsed all linked TOML and confirmed one shall and one coverage row per ID (exit 0). check exited 0 with errors=0; task-scoped full check exited 0 with errors=0, warnings=53, notes=29; git diff --check exited 0. Source/test definitions inspected, no product tests run. Same-row ties, simultaneous lockfiles and unspecified filesystem/command representation details remain explicitly recorded without new rules; needed policy beyond the ticket must block with questions. Build retains four-locale help/release-note and documentation obligations.
- 2026-11-12 specify: DEVIATION specify: advisory check warnings retained at this stage - prospective verification_hint.py paths do not exist until build and unrelated historical stale-path/journal warnings are outside this pinned task; no format errors, no weakened final strict gate and no product implementation performed.
- 2026-11-12 specify: completed; next design

## Rulings


## State

status: ready
reported: specify - completed
next: start design: read .agentic/steps/3_design.md
must_read: .agentic/tasks/TASK-51bf134b.md, .agentic/steps/3_design.md
changed: Specify completed: 27 new draft requirements, one revised enrollment-default requirement, five unchanged reused contracts, 33 coverage rows and one ordered-matching spec; all seven specify checklist items met.
evidence: Advisory check and task-scoped full check exited 0 with zero errors; TOML/coverage/one-shall audit exited 0 for all 33 IDs; git diff --check exited 0. No product tests run in specify.
issues: Expected prospective-helper and unrelated historical advisory warnings retained and logged. Additional matching rules remain unauthorized; recorded edge-policy unknowns require questions if needed in design/build. Product implementation and validation not started.
spec_compliance:
implementation_quality:
review_round:
