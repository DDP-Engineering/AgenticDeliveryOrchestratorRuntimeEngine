<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-aad00a23 - [Direct] Show direct jobs clearly in Jobs

stage: design
type: feature
path: full
interaction: autopilot
requirements: REQ-DATA-18b26c84, REQ-UX-4123c97c, REQ-UX-029d0525, REQ-UX-ad37f7e7, REQ-UX-5cf762f8, REQ-UX-ef06a3c7, REQ-UX-1b6f2a83, REQ-UX-16f751b7, REQ-UX-f6c6e946, REQ-UX-7e9792e9, REQ-UX-647b1549, REQ-UX-631835f9, REQ-UX-009b4cb9, REQ-UX-9cdaa57b, REQ-UX-7fab3dcb, REQ-DATA-08ed925c, REQ-SEC-5d0f86e7, REQ-UX-b105b854, REQ-UX-46c09118, REQ-UX-a8c7ea48, REQ-UX-b758d2b7, REQ-UX-c77f7335, REQ-UX-558518e7
parent:
branch: adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-66
base: fc943f9b82c93967dc22bf76e1e5cccf34b242d5
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
- STATED (ticket #66): users need to distinguish AEGIS and direct jobs at a glance in Jobs and inspect direct attempts and independent verification.
- OBSERVED (`04_Software/web/src/jobModel.ts`, `JobWorkspace.tsx`): the browser Job type/reader does not validate workflow, the workspace has no workflow label or direct verification presentation, and stage labels/timeline presentation are shared.
- OBSERVED (`04_Software/adore/web/jobs.py::_view`): authorized reads already serialize workflow, but omit validation_evidence and attempt details other than existing detail budget launch counts.

Desired outcome:
- STATED (ticket #66): list and page show AEGIS or Direct; direct jobs show only Implementation and Validation, then Done, with no AEGIS task; direct detail shows attempt number, verification command and passed/failed/timed-out/not-configured-unverified result, duration and output tail.
- STATED (ticket #66): AEGIS jobs retain their existing rendering apart from the requested workflow identification; existing AEGIS test expectations remain intact.
- STATED (ticket #66): unknown workflow is an error state, never a guessed workflow; help explains direct use of Implementation and Validation stage limits in all four locales.

Actors:
- STATED (ticket #66 and AGENTS.md): Jobs users, including authorized administrators and project-scoped developers; ADORE remains the owner of execution and publication, and humans own merge decisions.

Primary scenario:
- STATED (ticket #66): a user opens global or project Jobs, identifies a Direct job in the list, opens its detail, sees its actual direct steps and attempt number, then reads independent verification evidence without AEGIS-only stages or a task binding.
- INFERRED (same ticket plus current read-model boundaries): presentation follows the saved run workflow and saved verification evidence, not the repository's current enrollment observation or current command configuration.

Examples:
- STATED (ticket #66): a direct candidate whose command passed shows the command, Passed, duration and output tail; failed and timed-out commands have their distinct outcomes.
- STATED (ticket #66 and plan section 4.4): no configured command is explicitly not configured: unverified, not a verification pass.
- OBSERVED (`orchestrator.py::_verify_direct`): retained verification_result has command, exit_code, seconds, timed_out and output; verification is passed, failed or timed out. The no-command path records verification = not configured.

Counterexamples:
- STATED (ticket #66): an unknown workflow value must not be treated as AEGIS or Direct or display plausible-looking job evidence.
- STATED (ticket #66): a direct job must not acquire Framing, Specification, Design or an AEGIS task through shared UI defaults.
- INFERRED (ticket's four outcomes and repository fail-closed rules): missing or corrupt result evidence must never be converted to Passed or to explicit not configured evidence.

In scope:
- STATED (ticket #66): `04_Software/web/src/jobModel.ts`, `JobWorkspace.tsx`, `jobCopy.ts`, `i18n.ts`, `settingHelp.ts`; four-locale labels and guidance; job model unit tests and `web/e2e/jobs.spec.ts`.
- STATED (ticket #66), OBSERVED (`adore/web/jobs.py::_view`): add the necessary validated, redacted direct evidence projection to `adore/web/jobs.py`, with offline `tests/test_web_jobs.py` trust-boundary coverage; verification evidence is not exposed today.
- STATED (ticket #66): four-locale `web/src/help/content/{en,fr,de,ro}/{jobs,settings}.md`, `05_SoftwareDocu/Component_Web_Jobs.md`, `Component_Web_Frontend.md`, root CHANGELOG and a four-locale Unreleased release note.
- STATED (AGENTS.md and `.agentic/AGENTS.md`): task-scoped requirements/spec/design and current component knowledge updates in their appropriate later stages; update operator guidance if the changed interface makes it inaccurate.
- OBSERVED (`.agentic/knowledge/web-interface.md`, environment guide): frontend build-input changes require a rebuilt committed production bundle and asset fingerprints in build/validate, not only the isolated e2e build.

Out of scope:
- STATED (ticket #66): changes to run behavior.
- STATED (plan sections 1 and 4.7): workflow selection, ticket pickup/labels, isolation, egress, budgets, approval, publication, review loop and Pi executor selection remain unchanged.
- STATED (AGENTS.md and ticket): migrations, compatibility readers, planning edits, AEGIS payload changes, child task journals, commits, pushes and PR/MR operations.

Constraints:
- STATED (conductor instruction): exactly this pinned task and frame stage in this session; interaction is autopilot, already set in the journal; stop immediately after advance. Blocking product decisions go in ADORE_QUESTIONS.md with a blocked pause, not invented behavior.
- OBSERVED (`git branch --show-current`): checkout matches journal branch `adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-66`; base remains fc943f9b82c93967dc22bf76e1e5cccf34b242d5.
- STATED (AGENTS.md): offline tests with injected external boundaries; typed fail-closed corrupt-input errors; preserve authorization, redaction, optimistic revisions and current stored formats without migration.
- STATED (ticket): targeted verification while building; full suite once in validate through AEGIS strict check; final validate also requires report and advance.
- STATED (AGENTS.md): preserve license headers, LF and code style; same-change help/component documentation and user-facing release note. Build logs must include `release-notes: added` and `help: updated`.
- INFERRED (repository bounded-run rule applied to this frame): limit this session to one inspection/framing pass, at most 20 minutes, one edited repository file (this journal), no implementation, test execution, dependency changes or paid/external calls. Later implementation stays bounded by the ticket and conductor budgets.

Success signals:
- STATED (ticket #66): model unit tests and Jobs e2e prove workflow labels, direct steps/attempts, all four verification outcomes and unknown-workflow error; existing AEGIS journeys retain their assertions.
- STATED (AGENTS.md and ticket): API tests prove valid direct evidence plus malformed persisted evidence, authorization and redaction boundaries without writes or external commands; help parity/navigation passes across en/fr/de/ro.
- STATED (ticket validation): from `04_Software`, run `uv run --frozen --extra web python -m pytest -q tests/test_web_jobs.py` and `uv run --frozen ruff check adore tests`; from `04_Software/web`, run `npm test`, `npm run typecheck`, `npm run build:e2e`, and `./node_modules/.bin/playwright test e2e/jobs.spec.ts e2e/help.spec.ts`. Before validate run `python 02_Tools/internal/check_release_notes.py --since fc943f9b82c93967dc22bf76e1e5cccf34b242d5`; final gate is `python .agentic/aegis.py check --task TASK-aad00a23 --strict --run` in validate.

Evidence:
- STATED: ticket #66 and `00_Planning/2026-11-10_Direct_Workflow_Without_AEGIS/PLAN.md` sections 1 and 4 agree on direct build/validate/done, no AEGIS task, optional independent verification and unchanged shared delivery behavior.
- OBSERVED: `.agentic/context/project.md` and `.agentic/knowledge/web-interface.md` route Jobs work to `JobWorkspace.tsx`, `adore/web/jobs.py`, `tests/test_web_jobs.py` and `web/e2e/jobs.spec.ts`; they explicitly describe Jobs presentation as unchanged so far.
- OBSERVED: `.agentic/requirements/data/REQ-DATA-18b26c84.toml` covers authorized workflow serialization only, not this new UI; `REQ-DATA-72e08277` covers latest bounded sanitized verification evidence. Those existing contracts support this task but do not cover all requested new behaviors.
- OBSERVED: `adore/state.py::RunState` stores workflow, iterations, stage_failures and validation_evidence; direct task bindings and AEGIS-only stages are refused. `orchestrator.py::_launch_stage` increments iterations and journals stage-launch with attempt; `_verify_direct` retains independent verification evidence, and `_direct_result` validates its current shape, status agreement and output bounds.
- OBSERVED: `adore/web/jobs.py::read_job_budget` exposes iterations as launches in detail; `_view` omits verification evidence. No required new run-state field has been identified.
- OBSERVED: `tests/test_web_jobs.py` already covers both workflow values for Admin/Developer and corrupt/missing workflow/direct task bindings; `web/tests/jobs.test.mjs` covers strict job transport but its fixture has no workflow field yet. Existing AEGIS scenarios will need additive fixture fields without weakening their assertions.
- OBSERVED: `web/src/help/content/en/jobs.md` describes AEGIS stages only; `settings.md` already describes optional direct verification. `settingHelp.ts` stage-limit help is AEGIS-centric. Help README requires matching locale structure and interface terminology.
- OBSERVED: only inspection/AEGIS status, brief, components and help commands ran in frame; no test outcomes are claimed.

Assumptions:
- INFERRED (ticket scope plus inspected state/engine): the existing persisted launch/attempt and verification evidence is sufficient for the requested read-only presentation; do not add counters or change retry behavior to manufacture UI evidence.

Unknowns:
- UNKNOWN: exact public direct-evidence field names, absence representation before any verification, and attempt projection details are not designed yet. Specify/design must anchor them in the existing iterations/stage-launch evidence, distinguish absent evidence from explicit unverified evidence, and retain actual values without invented counts.
- UNKNOWN: targeted/full validation results and availability of build/browser dependencies in the later fresh build/validate containers. No setup or verification has been performed in frame.

Decision-blocking questions:
- INFERRED (ticket/plan comparison and inspected source): none identified. Required evidence is persisted; conditional API exposure work is authorized. If later inspection finds a genuinely unrecorded required datum or a plan conflict, stop through the prescribed questions-file path.

Proposed behaviors:
- STATED: only the ticket's accepted behaviors are carried forward: workflow identification, direct-only steps and evidence, unchanged AEGIS behavior, strict unknown-workflow refusal and localized help. No additional product behavior proposed at frame.

Path and reason:
- INFERRED (criteria below): full path, retained in header. This is a user-visible capability with a read-model extension, not restoration of an already-covered UI contract; specify and design must define atomic behavior and trust-boundary proof before build.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | STATED ticket adds workflow labels, direct-specific stages and verification detail. |
| no new interface or data format | no | OBSERVED jobs.py omits verification evidence; STATED ticket authorizes exposing it for detail. |
| no new dependency | yes | INFERRED current React/Python/i18n/help/test infrastructure covers the requested presentation without a new package. |
| an existing requirement already covers the behavior | no | OBSERVED REQ-DATA-18b26c84 is API workflow serialization only; REQ-DATA-72e08277 is engine persistence, not Jobs UI. |
| no security or data-handling change | no | INFERRED exposing saved command/output extends the read allowlist and requires existing redaction/access controls and negative tests. |

- STATED (conductor): no child tasks; one supervised pinned task covers this cohesive Jobs change.
- INFERRED (audit of this frame): scope, examples and success signals follow the ticket and plan; unspecified transport details remain unknown for specify/design, not accepted product behavior. Autopilot scope/path are recorded here without a human checkpoint.

## Requirement coverage

STATED (ticket #66, accepted Frame and plan sections 1/4): each row below is
one accepted observable response. OBSERVED (existing requirement/source/test
inspection): three matching contracts are reused unchanged; twenty new contracts
are draft, with empty linked_tests until build. Design owns the final column.

| Frame outcome | Atomic behavior | Requirement | Verification | Design decision or no impact |
|---|---|---|---|---|
| Recorded workflow | Authorized job reads serialize the persisted aegis/direct value. | REQ-DATA-18b26c84 | Existing offline API list/detail fixtures for both roles/workflows, corrupt workflow and foreign project refusal. | Pending design |
| List identification | Global and project Jobs list identify each job as AEGIS or Direct in four locales. | REQ-UX-4123c97c | Model valid-workflow controls and mixed-workflow browser rows in both scopes; unknown value is not defaulted. | Pending design |
| Page identification | Job detail identifies its own recorded workflow in four locales. | REQ-UX-029d0525 | Browser direct/AEGIS composite routes, locale labels and switching without a stale label. | Pending design |
| Direct steps | Direct stage presentation uses Implementation/build, Validation/validate and Done, showing only recorded stage evidence. | REQ-UX-ad37f7e7 | Model and browser build/validate/done plus saved timeline controls; no early AEGIS stages or invented completion. | Pending design |
| No direct AEGIS task | Direct details contain no AEGIS task presentation. | REQ-UX-5cf762f8 | Browser detail/technical evidence absence; existing corrupt direct task-binding API negative. | Pending design |
| Direct attempt | Detail shows the latest saved executor stage-launch attempt number. | REQ-UX-ef06a3c7 | API/model/browser known latest attempt distinct from lifetime launches/failures; malformed counter negatives. | Pending design |
| Honest attempt absence | No recorded launch gives an unavailable attempt, not a guessed ordinal. | REQ-UX-1b6f2a83 | API/model/browser absent-journal control with nonzero other counters; malformed present attempt is not absence. | Pending design |
| Verification command | Detail shows the saved redacted command before its result. | REQ-UX-16f751b7 | API/model/browser command ordering and inert operators/markup; changed current config cannot substitute text. | Pending design |
| Verification passed | A valid saved zero-exit non-timeout pass displays Passed. | REQ-UX-f6c6e946 | Model/browser pass including zero duration/empty output; timeout and status disagreement cannot pass. | Pending design |
| Verification failed | A valid saved nonzero non-timeout failure displays Failed. | REQ-UX-7e9792e9 | Model/browser retained failure during build and terminal failure; exit 124 without timeout is Failed. | Pending design |
| Verification timed out | A valid saved timeout displays Timed out independently of exit code. | REQ-UX-647b1549 | Model/browser timeout controls including exit zero; invalid timeout type/status disagreement rejected. | Pending design |
| Explicit unverified | An explicit not-configured record displays Not configured: unverified. | REQ-UX-631835f9 | Model/browser unconfigured case with no fabricated measurements; absent status and contradictory result negatives. | Pending design |
| Verification duration | Configured-result detail displays recorded elapsed seconds. | REQ-UX-009b4cb9 | Model/browser zero, fractional, large finite duration controls; boolean, negative, nonfinite and overflow rejected. | Pending design |
| Verification output | Configured-result detail displays bounded redacted inert tail or an empty-output indication. | REQ-UX-9cdaa57b | API/model/browser empty and maximum-tail controls, leading whitespace, inert markup, credential masking and over-bound rejection. | Pending design |
| Honest verification absence | No saved outcome/result displays verification unavailable. | REQ-UX-7fab3dcb | Model/browser pre-verification build distinct from explicit unverified; an outcome missing its result is an error. | Pending design |
| Read-only direct evidence | Authorized detail projects allowlisted saved attempt and latest independent result with explicit absence. | REQ-DATA-08ed925c | Offline API both roles, all outcomes/absence, saved-vs-current config, source-byte preservation, no commands and forbidden foreign reads. | Pending design |
| Persisted trust-boundary failures | Malformed selected job sources fail with typed secret-free errors and no partial totals or repair. | REQ-SEC-5d0f86e7 | Reuse source-error contract; add direct result/status/type/bounds and stage-launch attempt corruption to offline API coverage. | Pending design |
| Unknown workflow error | Missing/nontext/unknown browser workflow rejects the response into the existing error state. | REQ-UX-b105b854 | Model list/detail invalid workflow matrix and browser injection after valid evidence; hide stale totals/detail and guessed labels. | Pending design |
| Direct evidence transport error | Malformed browser direct attempt/verification evidence rejects the detail into the existing error state. | REQ-UX-46c09118 | Model shape/type/status/range/bounds matrix and browser corruption after valid detail; no fabricated pass/unverified result. | Pending design |
| Invalid direct stage error | Browser direct state/timeline naming a non-direct stage rejects the response. | REQ-UX-a8c7ea48 | Model current/timeline forbidden-stage matrix and browser corrupt-stage fixture; valid AEGIS controls retain their stages. | Pending design |
| AEGIS regression boundary | Existing authorized AEGIS current-state/actions/observed-only timeline rendering remains intact apart from workflow identification. | REQ-UX-b758d2b7 | Retain existing AEGIS model/browser assertions, including quick path, lifecycle/actions, timeline paging, missing evidence and error hiding; no direct panel. | Pending design |
| Jobs help | Four-locale Jobs help explains direct workflow, attempt and each verification outcome. | REQ-UX-c77f7335 | Content tests plus help browser navigation, matching interface terms and locale structure/link/Markdown negatives. | Pending design |
| Stage-limit guidance | Four-locale Jobs/Settings help and inline guidance explain direct build/validate limit mapping and general-limit fallback. | REQ-UX-558518e7 | Content/setting-guidance tests and help browser navigation; no AEGIS-only limits attributed to direct jobs. | Pending design |

### Specify evidence and challenge

- STATED (conductor): this session completes specify only, under the existing
  autopilot header; advance is the hard stop, not permission to start design.
- INFERRED (repository bounded-run rule applied to this stage): bound this
  specify pass to 30 minutes, the journal, twenty requirement files and one
  shared spec; no product/source/test edits, dependency provisioning, external
  calls or test-suite execution. All edits stay under `.agentic/` outside the
  managed payload.
- OBSERVED (`_launch_stage`): the journal already stores an actual `attempt` on
  each launch. It differs from iterations and can differ from current failures;
  the new requirement reads that evidence and does not introduce a new counter.
  INFERRED (this source plus the accepted honest-unknown contract): missing
  launch evidence stays unavailable rather than inventing the requested number.
- OBSERVED (`_verify_direct`, `_direct_result`, REQ-DATA-72e08277 and its spec):
  the saved five-key result carries the command, exit, seconds, timeout and
  bounded output needed by the page. No required datum is missing. Summary is
  not independent evidence; a fail/timeout can remain visible at build, and
  a later result replaces the earlier one. No run behavior is changed.
- STATED (ticket's API scope): exposing the necessary direct evidence is
  authorized. OBSERVED (`specs/REQ-FUNC-e8455ab6.md`): its current broad exclusion
  of commands/validation payloads describes today's allowlist. INFERRED: this
  is a deliberate narrow allowlist extension, not a ticket/plan conflict; build
  must update that read spec/documentation alongside the new projection while
  leaving unrelated payloads excluded. Existing REQ-DATA-18b26c84 remains
  API-only; no revision or retirement of its contract is necessary.
- OBSERVED (`state.py`): persisted direct task bindings and frame/specify/design
  are refused already. STATED (ticket/plan): direct stage vocabulary is
  build/validate/done; browser negatives prevent shared AEGIS defaults from
  making corrupt direct stages look legitimate. Lifecycle publishing still
  remains independent of stage Done.
- INFERRED (atomic-response audit): the four outcomes, absence, malformed
  workflow, malformed detail and forbidden direct stage each have their own
  requirement; command, duration and tail can fail independently and are split.
  One API projection response owns the allowlisted view; the existing source
  refusal contract owns its persisted-input failure response. Existing AEGIS
  rendering is regression proof, not a new workflow behavior.
- STATED (AGENTS.md/ticket): same-change component pages, production bundle,
  CHANGELOG and four-locale release note remain build obligations, not new
  execution features. Build records `release-notes: added` and `help: updated`,
  updates `Component_Web_Jobs.md`/`Component_Web_Frontend.md` and current component
  knowledge, and runs the release-note check against the journal base before
  validate. The Frame's targeted commands/final strict validate gate remain.
- UNKNOWN, nonblocking design choices: additive evidence field names/nesting,
  closed transport shape and component/helper placement. The shared draft spec
  fixes source, absence, outcome and error semantics; design settles spelling
  before build. No new schema or old-format compatibility is authorized.
- INFERRED (audit against every accepted Frame success signal): all behaviors
  have one coverage row and requirement; the twenty new requirements use one
  self-contained shall sentence each, concrete verification and existing-path
  estimates with no linked tests until build. No decision-blocking question or
  extra product behavior was identified; setup/test results remain unknown.

## Design


## Log

- 2026-11-12 frame: journal opened
- 2026-11-12 frame: Frame scope recorded under conductor-authorized autopilot. Full path retained: new Jobs workflow/evidence UI and read-only evidence projection require specify/design; existing state records required data, with no blocking plan conflict identified. Implementation, setup and tests deferred to their supervised stages.
- 2026-11-12 frame: completed; next specify - Frame complete; scope recorded under conductor-authorized autopilot, full path justified, no decision-blocking questions identified
- 2026-11-12 specify: Specify complete: 23 atomic coverage rows map in order to 20 new draft requirements and 3 unchanged active contracts; one shared draft spec defines recorded attempt, latest verification, honest absence and typed failures. Required evidence is already persisted; no blocking question. Ordered TOML/coverage audit and git diff --check exited 0; check --task TASK-aad00a23 --full/--json exited 0 with errors=0, warnings=35, notes=29. Verified all 35 warning paths exist unchanged at task base; no task format errors, and the no-anchor note is expected before build. Product tests were not run in specify. Transport spelling/placement remains design work; help, release notes, component documentation and bundle remain build work.
- 2026-11-12 specify: completed; next design

## Rulings


## State

status: ready
reported: specify - completed
next: start design: read .agentic/steps/3_design.md
must_read: .agentic/tasks/TASK-aad00a23.md, .agentic/steps/3_design.md
changed: Specified 23 atomic behavior rows: 20 draft requirements created, 3 active contracts reused unchanged, 1 shared evidence/error spec; all seven specify checklist items complete; no product changes
evidence: AEGIS check --task TASK-aad00a23 --full and --json exited 0: errors=0; ordered coverage/TOML audit and warning-path baseline audit exited 0; git diff --check exited 0; no product tests run
issues: 35 pre-existing warnings on unchanged requirement/journal paths; no task format errors or blocking questions; transport field spelling and placement remain for design
spec_compliance:
implementation_quality:
review_round:
