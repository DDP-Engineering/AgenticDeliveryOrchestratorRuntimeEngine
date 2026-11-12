<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-51bf134b - [Direct] Suggest the verification command from repository files

stage: build
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

- [ ] each automated increment has a red line before its implementation and a
      green line after; each manual one a logged observation
- [ ] anchor recorded before implementation; evolution reviewed after
- [ ] focused tests green, with the command and its scope logged
- [ ] `affected_paths`, `linked_tests` and `status = "active"` current on every
      requirement, or `retired` with its reason
- [ ] affected docstrings, usage examples and setup instructions updated
- [ ] `check` clean, or each remaining warning explained in the Log

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
inspected existing contract without changing it. Design cells map to D1–D6
below; source paths identify contract owners, not a promise to edit every owner.
STATED owner clarification is recorded in RULING-001 through RULING-004.

| Frame outcome | Atomic behavior | Requirement | Verification | Design decision or no impact |
|---|---|---|---|---|
| Ordered matching, row 1 | Real root scripts.test supplies the JavaScript command/source with the listed lockfile variants | REQ-FUNC-8676b7b9 | Public-helper table fixtures: npm/pnpm/yarn pair or missing-script miss; both lockfiles choose pnpm; root and row precedence | D1/D2: ordered JavaScript row and pnpm/yarn/npm priority, helper tests |
| Ordered matching, row 2 | First matching Python row supplies pytest command/source with uv variant | REQ-FUNC-b360529b | Each Python filename with/without uv.lock; same-row listed source order; earlier JavaScript wins and later Go loses | D1/D2: listed Python source order and uv variant, helper tests |
| Ordered matching, row 3 | First matching Go row supplies go test ./... and source | REQ-FUNC-d10b9f52 | go.mod pair; Python precedence and child suppression | D1/D2: third row, helper tests |
| Ordered matching, row 4 | First matching Cargo row supplies cargo test and source | REQ-FUNC-0a0f15f3 | Cargo pair; Go precedence and child suppression | D1/D2: fourth row, helper tests |
| Ordered matching, row 5 | First matching Maven row supplies mvn -q test and source | REQ-FUNC-43c92cd6 | pom.xml pair; Cargo precedence and child suppression | D1/D2: fifth row, helper tests |
| Ordered matching, row 6 | First matching Gradle row supplies wrapper/plain command and source | REQ-FUNC-614738d0 | Both filenames with/without wrapper; same-row listed source order; Maven precedence | D1/D2: Gradle source order and wrapper variant, helper tests |
| Ordered matching, row 7 | First matching dotnet row supplies dotnet test and source | REQ-FUNC-1bd6056c | Solution/project pair; solution-first lexical source ties; Gradle precedence | D1/D2: dotnet patterns and lexical provenance, helper tests |
| Ordered matching, row 8 | First matching Make test target supplies make test and source | REQ-FUNC-9ed60681 | Makefile with/without test target; dotnet precedence | D1/D2: eighth row, read target only, helper tests |
| Malformed npm boundary | Bad JSON/structure supplies no JavaScript match and no error | REQ-REL-cbc3b8e1 | Malformed/non-object/nontext package fixtures return nothing; real script control | D1: JSON structure miss without error, helper tests |
| Placeholder boundary | npm's no-test-specified placeholder supplies no JavaScript match | REQ-FUNC-1ab66bb2 | Standard placeholder-only fixture returns nothing; real script control | D1: exclude stated npm placeholder, helper tests |
| Clone containment | Outside-linked manifest, command-selection file or directory is ignored unread | REQ-SEC-95dddb65 | External manifest/lockfile/child links with read guards; contained-file control | D1: resolved containment before evidence access, helper tests |
| Bounded file reading | Files over 1048576 bytes are ignored without content reading | REQ-SEC-ecafbce6 | At-limit/one-over manifest fixtures with oversized read guard | D1: stat size and bounded content reads, helper tests |
| Unique child fallback | One matching first-level directory supplies cd-prefixed command/source | REQ-FUNC-4581cf7c | All eight table rows in a child; safe/unsupported names; root and deeper-only boundaries | D2: count children then fullmatch sole name, helper tests |
| Ambiguous children | Several matching first-level directories supply no suggestion | REQ-FUNC-08a75f14 | Two matching children in either creation order, including safe plus unsupported name; single-child and root controls | D2: ambiguity before name restriction, helper tests |
| No match | No eligible root/immediate-child row supplies no suggestion | REQ-FUNC-45ca2605 | Empty/unrelated/deeper-only evidence; qualifying-root control | D2: no recursive or extra ecosystem inference, helper tests |
| Pure helper | Root-path discovery is file-read-only and returns pair or nothing | REQ-NFR-6badc5b8 | Match/no-match repeatability, no process/network calls, unchanged file snapshots | D1: standard-library read-only API, helper tests |
| Direct preview | Inspected direct clone exposes helper command/source separately from submitted review text | REQ-FUNC-d50a408d | API matching clone pair; explicit empty/edit preserved, no-match control | D3: separate transient verification_hint, test_web_enrollment.py |
| AEGIS exclusion, web | Present aegis.py suppresses enrollment suggestions | REQ-FUNC-2bf3e808 | API/browser AEGIS-plus-manifest fixture; direct control and broken/presence-only AEGIS | D3/D4: existing workflow observation gates hints, API/e2e |
| Absent clone boundary | Not-inspected enrollment supplies no suggestion | REQ-FUNC-357ae298 | URL preview with absent destination: no hint/clone/probe; existing direct control | D3: no materialization to discover hints, API/e2e |
| Localized enrollment default | Untouched optional command field uses available direct hint, otherwise empty | REQ-UX-92197baa | Four-locale matching/no-match/uncreated fixtures and canonical review; AEGIS note control | D4: entry preview and bounded canonical re-preview, enrollment e2e |
| Visible web provenance | Suggested command identifies its source in four locales | REQ-UX-dd21046e | Root/child source guidance; no AEGIS or no-match source claim | D4: enrollmentCopy four locales and associated hint text, e2e |
| Human edit/clear authority | Repeated discovery preserves exact human draft edits or empty choice | REQ-UX-cca17b80 | Edit/clear after prefill; re-preview/check/back navigation and exact chosen Create value | D4: sticky memory-only human edit flag, e2e including delayed results |
| Human-only persistence, retained | Preview returns review/findings without profile publication or tool probes | REQ-FUNC-702b0fce | Existing offline API no-probe preview; add manifest fixture and inspect no profile bytes | Retained boundary; D3 consumes without modifying candidate, API regression |
| Exact enrollment save, retained | Explicit confirmed Create saves exact reviewed command | REQ-FUNC-a6e265cd | Accept/edit/clear hint then compare loaded TOML; stale command revision publishes nothing | Retained boundary; D3/D4 bind submitted text, API/e2e regression |
| Shared CLI default | Direct init prompt defaults to helper suggestion or empty | REQ-FUNC-f753863b | Capture action/command FieldSpecs for matching/no-match clone and accept default with fake runner | D5: use-suggestion default displays shared command; enter-another default equals it, wizard tests |
| Visible CLI provenance | Init identifies the source behind its suggested default | REQ-UX-7f47b773 | Capture root/child source guidance; no-match and AEGIS show no claimed source | D5: source in prompt guidance, wizard tests |
| AEGIS exclusion, CLI | Present aegis.py suppresses init repository suggestions | REQ-FUNC-65db4fd5 | Manifest plus present AEGIS, including unavailable interpreter; direct control | D5: presence gating before suggestion, wizard tests |
| Human CLI choice | Confirmed init saves kept, edited or explicitly cleared command | REQ-FUNC-b0f69285 | Interactive/scripted use/another/none including Enter default and loaded TOML; cancellation/invalid input no publication | D5: explicit action choices, field-local exact text, wizard tests |
| Invalid CLI input, retained | Invalid/unconfirmed answers reprompt or fail fast without profile creation | REQ-FUNC-6c82ad42 | Invalid command answer and cancelled confirmation through existing wizard fakes | Retained boundary; D5 uses existing ask validation and confirmation, wizard regression |
| Validated CLI publication, retained | Generated config validates before profile writes | REQ-FUNC-5771eecc | Valid chosen command profile and invalid candidate leave-before-write oracle | Retained boundary; D5 assembles before existing validation/publication, wizard regression |
| Saved Settings authority | Saved empty/custom command is never replaced by discovery | REQ-DATA-c1c4d1c3 | Matching clone in Settings; load/unrelated save preserves exact saved value | D6: no discovery path added to Settings, API/browser regression |
| Exact Settings Save, retained | Human reviewed Save applies exact chosen command under existing guards | REQ-FUNC-51f29b04 | Existing empty/nonempty review/apply and rejected stale/denied/write-failure cases | No design impact: existing Settings guards unchanged, API/browser regression |
| Preview response trust boundary | Malformed command/source evidence is refused without applying it | REQ-REL-60015e50 | Corrupt suggestion member types/pair/multiline command: visible failure and unchanged draft; valid pair control | D4: validate full pair/workflow before any state application, e2e route mutation |

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

**Approach**
- INFERRED (ticket #65 pure-function boundary; inspected `_prepare_project`,
  `run_wizard` and `runPreview`): D1 introduces one standard-library reader,
  `suggest_verification_command(root: Path) -> tuple[str, str] | None`, in
  `adore/verification_hint.py`. Both entry points reuse it; no subprocess,
  network, writes, toolchain validation or dependency additions. This avoids
  divergent CLI/web heuristics (REQ-NFR-6badc5b8).
- STATED (eight matching requirements below): D2 applies the specified ordered
  rows at root, then the same scan to immediate children only; root success
  suppresses children, one matching child prefixes its command, zero/multiple
  matching children return None. STATED owner clarification (RULING-001/002)
  resolves variants: eligible pnpm lock before yarn before npm; Python sources
  pyproject.toml/pytest.ini/tox.ini, Gradle build.gradle/build.gradle.kts, dotnet
  *.sln before *.csproj and lexical filenames within each pattern. D2 counts
  children before requiring the sole child's name to fully match
  `[A-Za-z0-9_][A-Za-z0-9._-]*`; unsupported sole names return None and safe plus
  unsupported matching names remain ambiguous (RULING-003;
  REQ-FUNC-4581cf7c/08a75f14). No quoting/backend parameter is introduced.
- INFERRED (REQ-FUNC-d50a408d; retained REQ-FUNC-702b0fce/a6e265cd): D3 adds
  suggestion evidence to preview, not to its canonical configuration. Reject
  silently replacing server candidate text: it would break exact reviewed saves.

**Interfaces and data**
- INFERRED (REQ-SEC-95dddb65/ecafbce6): D1 resolves each evidence path against
  the resolved clone boundary and checks regular-file size before content access;
  only package.json and Makefile need contents. Read contents with the 1 MiB
  bound, including open-time size/containment reinspection; never open an already
  oversized or external manifest for content. Apply eligibility to lockfiles,
  gradlew and directory links too. Source is an actual eligible clone-relative
  forward-slash manifest path, including its child, not a lockfile/wrapper
  (RULING-002). Malformed package structure is a miss (REQ-REL-cbc3b8e1);
  npm's stated placeholder is a miss (REQ-FUNC-1ab66bb2).
- INFERRED (AGENTS.md fail-closed input rule; existing WizardError and
  project_setup_unavailable): D1 does not turn unrelated OSError/UnicodeError
  into an empty repository or continue with a partial scan. Propagate access
  failures to caller boundaries: CLI gives field-addressed WizardError, web
  maps them to its existing setup-unavailable rejection, with no publication.
  This is error containment, not another matching rule; malformed package
  parsing retains its explicit no-error exception. Add injected access-failure
  proof to helper/entry-point tests; no claim of concurrent snapshot isolation.
- INFERRED (REQ-FUNC-d50a408d/2bf3e808/357ae298): D3 returns a transient
  `verification_hint: {command: string, source: string} | null` alongside the
  existing preview. Populate only for a structurally valid inspected direct
  clone; AEGIS, unavailable clones and no match return null. Never clone/probe
  to obtain a hint; never include this evidence in candidate/review digests.
  Initialize null for invalid previews too. Discovery belongs in the preview
  route after `_prepare_project`, not in Settings or shared Create preparation,
  so recomputation during Create never installs an unreviewed discovered default.
- INFERRED (REQ-UX-92197baa/dd21046e/cca17b80; REQ-REL-60015e50): D4 validates
  the full preview and hint before applying anything: null or a complete pair,
  nonempty command in the existing single-line domain, nonempty relative
  forward-slash source without traversal or an absolute path, and direct
  workflow when a pair exists. Render source as React text, never HTML.
  Keep a memory-only sticky human-edited flag, including explicit clearing;
  no repeated preview, Check, Back or repository reread can reset that flag
  in the mounted wizard (RULING-004). Associate localized provenance with
  the field, show it only for the current automatic suggestion, and remove
  any claim that an edited/cleared command came from the file.
- INFERRED (exact-review technical constraint): D4 requests an offline preview
  on entry to Verification, never a host probe. If an untouched draft receives
  a changed suggested default, invalidate old candidate/check/review evidence,
  apply that default and request a canonical preview for the resulting draft.
  Bound this flow to two preview requests per invocation: only the first may
  apply a default; the second validates the submitted text and cannot reapply
  another hint. Keep the applied command/source together even if file evidence
  changes during re-preview; this is editable provenance, not a live binding.
  Existing generation/alive and operation guards cover both requests; typing
  during either wins and prevents late overwrite. On failure keep the draft,
  disable Check/Continue/Create and allow explicit Validate setup retry.
  No effect loop keyed on command text and no recursive resuggestion.
- INFERRED (REQ-FUNC-f753863b/65db4fd5/b0f69285; REQ-UX-7f47b773): D5 offers
  direct-only field-local choices after clone selection and before summary:
  `verification_choice` offers `use suggestion`, `enter another command`,
  `no verification` with use-suggestion default when a hint exists. Show its
  command and source in guidance. With no hint, offer enter-another/none and
  default none. The enter-another branch asks `verify_command`, defaulting
  to the hint command (or empty), validating the existing command domain;
  the none branch assigns empty without asking a defaulted command question.
  Enter can therefore keep the suggestion, while choosing none always clears
  it. ScriptedAsker uses the same action/command keys; invalid choice or CR/LF/NUL
  follows existing reprompt/fail-fast behavior (RULING-004).
- INFERRED (ConsoleAsker.read strips all input, exact command technical
  constraint): D5 reads command text verbatim only for the field key
  `verify_command`, retaining None for genuinely empty Enter. All other fields'
  stripping/default semantics and general ask() remain unchanged. Prove literal
  whitespace, quotes, operators and Unicode are saved as answered. Include
  verify_command in the minimal workflow section only when nonempty, then use
  existing summary/confirmation/config validation before writes. Skip both
  discovery and these new prompts for AEGIS or `prepare_only`; the web continues
  to serialize only body.verify_command and never accepts a CLI-derived default.
- STATED (REQ-DATA-c1c4d1c3; REQ-FUNC-51f29b04): D6 leaves Settings discovery
  absent; saved empty/custom values and existing reviewed Save remain authoritative.
  No stored format, migration, run-state, readiness or workflow-selection change.

**Files and test seams**
- INFERRED (D1/D2): new `04_Software/adore/verification_hint.py` and
  `tests/test_verification_hint.py`: parameterize all eight rows at root and
  single child, variants/precedence, malformed/placeholder input, no/deep match,
  two children, external-link and size/read guards, and no-process/network/write
  guards. Include both-lockfile precedence, all same-row source ties, safe-name
  boundary cases and safe-plus-unsupported ambiguity before filtering. All source
  assertions compare actual root/child repository-relative paths (RULING-001–003).
- OBSERVED (`_prepare_project`, `preview_project_setup`, test definitions in
  `tests/test_web_enrollment.py`): D3 attaches here; extend direct/AEGIS/pending
  fixtures, exact submitted command/digest controls and no-publication/probe proof.
  Put D3 hint enrichment in `preview_project_setup` after shared preparation;
  preserve review.verify_command equality and existing candidate digests.
- OBSERVED (`EnrollmentWizard.tsx` `runPreview`/`change`, `enrollment.spec.ts`):
  D4 attaches here, with four-locale provenance in `enrollmentCopy.ts`; browser
  fixtures cover accept/edit/clear, repeat preview/check/Back, corrupt pairs and
  AEGIS exclusion, delayed responses after edits/clearing and canonical second
  preview failures. OBSERVED `web/e2e/server.py` builds `workflow_clones` used
  by `/__e2e__/enrollment` and `/__e2e__/settings-workflow`; add matching manifest
  fixtures there for both workflows, plus an isolated child-source case.
  D6 extends `tests/test_web_config.py` and `web/e2e/settings.spec.ts` with
  manifest controls for saved empty/custom values and unrelated Save, without
  new Settings discovery code. D4 validation stays local to EnrollmentWizard;
  no new frontend module or i18n.ts edit is needed.
- OBSERVED (`wizard.py` `ask`/`ConsoleAsker`/assembly; `test_wizard.py`): D5
  attaches to captured FieldSpec/default/source and kept/edited/cleared saved
  config, action choices/Enter, exact field-local input, invalid/cancelled answers,
  injected access failures and prepare-only isolation. Preserve minimal
  omission when empty so existing default workflow-section proof remains valid.
- STATED (ticket scope / repository documentation rules): build updates
  Projects help en/fr/de/ro, Web_Interface.md, Configuration_Reference.md,
  Component_Wizard.md, Component_Web_API.md, Component_Web_Frontend.md and a new
  helper page `05_SoftwareDocu/Component_Verification_Hint.md` and its README.md
  index entry; CHANGELOG plus `adore/release_notes.toml` Unreleased four-locale
  note, committed `adore/web/static/` rebuild and required help/release-notes
  log lines. The retained guided-enrollment spec now marks the authorized
  prefill extension as draft; build completes implementation/proof and validate
  updates knowledge pages.
- INFERRED (source-owner affected_paths convention, inspected requirements):
  D1/D2 own verification_hint.py; D3 app.py/helper plus browser exclusion;
  D4 EnrollmentWizard.tsx/enrollmentCopy.ts; D5 wizard.py/helper. Remove
  speculative i18n.ts ownership from the two hint-copy requirements. D6 and the
  five retained contracts keep their existing source-owner lists because their
  boundaries are unchanged; no edit to those sources is implied by the audit.
  Tests/help/docs/generated assets above are expected change artifacts, not
  additional runtime owners. All 33 requirement paths have been checked against
  these seams. No product implementation occurs in design.

**Risks and open decisions**
- STATED owner clarification resolves Q1–Q3 and CLI clearing; RULING-001–004
  are the authority. No remaining product decision blocks design. The safe-name
  rule avoids portable-shell interpolation ambiguity; it does not prove selected
  tools are installed or the command will pass. Do not inspect packageManager,
  extend the table or change backend shells. No suggestion is executed here.
- INFERRED (REQ-SEC-95dddb65 plus untrusted filesystem): containment/size checks
  need careful open-time handling; concurrent replacement and unusual file
  access failures remain unproven. Do not claim a static resolve/stat check
  proves resistance to a concurrently hostile filesystem or promise such proof.
- INFERRED (existing exact review digests): automatic prefill invalidates the
  candidate; stale evidence must never enable creation. No Settings inference,
  command execution, saved schema or dependency change is needed.
- INFERRED stage bound: at most 45 minutes, at most 15 task-scoped files under
  .agentic/ (journal, matching spec, affected requirements and diagrams), no product
  tests or installations. Required diagrams illustrate component calls, preview
  ordering and transient browser draft transitions only, not a new run lifecycle.
  Knowledge pages remain unchanged; no build-stage work is performed.
- UNKNOWN: product test results and live platform/concurrent hostile-filesystem
  acceptance remain unproven. Build uses focused offline tests; validate alone
  runs the final full strict gate. Existing spec REQ-DATA-e1eaf583 has historical
  no-prefill wording deliberately superseded for enrollment by ticket #65 and
  revised REQ-UX-92197baa; its draft extension is now recorded explicitly, not
  a reason to weaken exact review/save invariants.

**Requirement map**
The 33 coverage rows remain the per-requirement test seams. D1/D2 own
REQ-FUNC-8676b7b9, REQ-FUNC-b360529b, REQ-FUNC-d10b9f52,
REQ-FUNC-0a0f15f3, REQ-FUNC-43c92cd6, REQ-FUNC-614738d0,
REQ-FUNC-1bd6056c, REQ-FUNC-9ed60681, REQ-REL-cbc3b8e1,
REQ-FUNC-1ab66bb2, REQ-SEC-95dddb65, REQ-SEC-ecafbce6,
REQ-FUNC-4581cf7c, REQ-FUNC-08a75f14, REQ-FUNC-45ca2605 and
REQ-NFR-6badc5b8; RULING-001–003 settle D2's exact source/command/name oracles.
D3 owns
REQ-FUNC-d50a408d, REQ-FUNC-2bf3e808 and REQ-FUNC-357ae298.
D4 owns REQ-UX-92197baa, REQ-UX-dd21046e, REQ-UX-cca17b80 and
REQ-REL-60015e50. D5 owns REQ-FUNC-f753863b, REQ-UX-7f47b773,
REQ-FUNC-65db4fd5 and REQ-FUNC-b0f69285; RULING-004 is realized with field-local
use/another/none choices and a command-only exact reader. D6 owns
REQ-DATA-c1c4d1c3. No contract change for
REQ-FUNC-702b0fce, REQ-FUNC-a6e265cd, REQ-FUNC-6c82ad42,
REQ-FUNC-5771eecc or REQ-FUNC-51f29b04: retain their existing boundaries
and regression seams. All 33 coverage design cells now name a decision and test
seam, including retained contracts. Required matching and clarification negatives
are mapped without new heuristic rules. Build owns implementation/red-green proof,
help/release notes/docs/assets; validate owns current-state knowledge and final proof.

Diagrams: [diagram_TASK-51bf134b.md](diagram_TASK-51bf134b.md)

## Log

- 2026-11-12 frame: journal opened
- 2026-11-12 frame: Frame scope recorded under conductor-authorized autopilot. Full path retained: new externally visible repository-derived defaults/provenance, additive preview/CLI interface and untrusted file-reading boundary fail quick criteria. Plan sections 1/4 and existing DW-04 enrollment/command surfaces inspected; no framing blocker established. Preserve explicit human save/edit/clear authority, absent-clone not-inspected behavior, saved Settings and AEGIS isolation. Frame changes only this journal; no product tests run.
- 2026-11-12 frame: completed; next specify
- 2026-11-12 specify: Specify complete: 27 new draft requirements, one deliberate draft revision of REQ-UX-92197baa for ticket-authorized prefill, five existing contracts reused unchanged, 33 one-to-one coverage rows/header IDs and one shared ordered-matching spec. Table-order audit parsed all linked TOML and confirmed one shall and one coverage row per ID (exit 0). check exited 0 with errors=0; task-scoped full check exited 0 with errors=0, warnings=53, notes=29; git diff --check exited 0. Source/test definitions inspected, no product tests run. Same-row ties, simultaneous lockfiles and unspecified filesystem/command representation details remain explicitly recorded without new rules; needed policy beyond the ticket must block with questions. Build retains four-locale help/release-note and documentation obligations.
- 2026-11-12 specify: DEVIATION specify: advisory check warnings retained at this stage - prospective verification_hint.py paths do not exist until build and unrelated historical stale-path/journal warnings are outside this pinned task; no format errors, no weakened final strict gate and no product implementation performed.
- 2026-11-12 specify: completed; next design
- 2026-11-12 design: Design partially recorded under five headings after inspecting all 33 requirements, their two referenced specs, plan sections 1/4, component knowledge and CLI/API/browser test seams. Shared helper, transient preview evidence, canonical re-preview and saved-Settings boundaries are mapped; no product code changed. Blocking Q1-Q3 in ADORE_QUESTIONS.md propose but do not adopt simultaneous-lockfile priority, same-row source selection and portable child-directory representation; ticket requires questions for rules beyond its table. Remaining: resolve those policies, finalize CLI clear interaction, fill coverage design cells/affected_paths, draw configured diagrams, recheck and only then advance. Advisory check exit 0: errors=0 warnings=175 notes=28 (prospective-helper and existing repository findings retained); git diff --check exit 0. No product tests run; knowledge pages and AEGIS payload unchanged.
- 2026-11-12 design: Design complete after owner clarification: RULING-001 through RULING-004 settle pnpm/yarn/npm priority, deterministic eligible source paths, count-before-safe-name child fallback and explicit CLI use/another/none plus sticky web edit/clear authority. D1-D6 now define pure helper, separate preview hint, bounded canonical re-preview, field-local exact CLI input and unchanged Settings/save boundaries. All 33 coverage rows have decisions/test seams; source-owner affected_paths audited, two speculative i18n owners removed, matching and guided-enrollment specs aligned as draft extensions. Structure/sequence/state diagrams saved in .agentic/tasks/diagram_TASK-51bf134b.md. Artifact audit exit 0: 33 unique parseable one-shall requirements/coverage rows, all spec references and expected source-owner paths, 14 scoped files, legal prologue/log history retained; knowledge and payload unchanged. No product code, tests or installations performed; build still owes implementation, focused proof, four-locale help/release notes/docs/assets and required log lines.
- 2026-11-12 design: DEVIATION design: advisory warnings retained - global check exit 0 reports errors=0 warnings=174 notes=28; task-scoped check and JSON check exit 0 report errors=0 warnings=53 notes=29. Prospective verification_hint.py is intentionally absent until build; other historical stale-path/ticket/journal findings are outside this pinned task. No format errors or weakened final strict validation; no product tests run. git diff --check exit 0.
- 2026-11-12 design: completed; next build

## Rulings

- RULING-001 | date=2026-11-12 | decision=Q1 resolved: eligible pnpm-lock.yaml selects pnpm test, otherwise eligible yarn.lock selects yarn test, otherwise npm test; pnpm wins when both exist. No packageManager, executable or network detection. | reason=STATED owner clarification on ticket #65 authorizes deterministic editable heuristic only, not command execution or proof of installed tools. | source=user | supersedes=none
- RULING-002 | date=2026-11-12 | decision=Q2 resolved: Python source order pyproject.toml, pytest.ini, tox.ini; Gradle build.gradle, build.gradle.kts; dotnet *.sln then *.csproj, lexical filenames within each pattern. Return actual eligible repository-relative source including child path. | reason=STATED owner clarification on ticket #65 confirms proposed source contract while retaining size and repository-containment limits. | source=user | supersedes=none
- RULING-003 | date=2026-11-12 | decision=Q3 resolved: count matching first-level directories before name filtering; only a sole matching child whose name fully matches [A-Za-z0-9_][A-Za-z0-9._-]* gets a cd prefix, otherwise no suggestion. Root suggestions unchanged; no shell/backend changes. | reason=STATED owner clarification on ticket #65 authorizes conservative portable-name restriction without suggesting only part of an ambiguous repository. | source=user | supersedes=none
- RULING-004 | date=2026-11-12 | decision=CLI must offer use suggestion, enter another command or no verification with Enter optionally choosing suggestion, without changing general empty-input semantics. Web repeated previews preserve explicit edits and clearing, Settings saved values stay authoritative, AEGIS gets no suggestion; save only reviewed submitted text. | reason=STATED owner clarification on ticket #65 resolves field-local clearing and reaffirms human-only persistence and suggestion-only authority. | source=user | supersedes=none


## State

status: ready
reported: design - completed
next: start build: read .agentic/steps/4_build.md
must_read: .agentic/tasks/TASK-51bf134b.md, .agentic/steps/4_build.md
changed: Completed D1-D6 design, all 33 coverage mappings and affected_paths audit; recorded four owner rulings and aligned two specs/ten requirements. Added .agentic/tasks/diagram_TASK-51bf134b.md with structure, sequence and state diagrams. No product changes.
evidence: Design artifact audit exit 0; global advisory check exit 0 (0 errors, 174 warnings, 28 notes); task-scoped advisory/JSON checks exit 0 (0 errors, 53 warnings, 29 notes); git diff --check exit 0. No product tests run.
issues: No unresolved design blocker. Prospective-helper and unrelated historical advisory warnings retained with logged justification. Implementation, focused tests, localized help/release notes/docs/assets and final strict proof remain for later stages.
spec_compliance:
implementation_quality:
review_round:
