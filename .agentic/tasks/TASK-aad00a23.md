<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-aad00a23 - [Direct] Show direct jobs clearly in Jobs

stage: validate
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
inspection): three matching contracts are reused; twenty new contracts are now
active, with linked tests populated in build. Design decisions map the final column.

| Frame outcome | Atomic behavior | Requirement | Verification | Design decision or no impact |
|---|---|---|---|---|
| Recorded workflow | Authorized job reads serialize the persisted aegis/direct value. | REQ-DATA-18b26c84 | Existing offline API list/detail fixtures for both roles/workflows, corrupt workflow and foreign project refusal. | D1: retain saved workflow serialization and its existing API tests; no engine impact. |
| List identification | Global and project Jobs list identify each job as AEGIS or Direct in four locales. | REQ-UX-4123c97c | Model valid-workflow controls and mixed-workflow browser rows in both scopes; unknown value is not defaulted. | D1/D6: required workflow type/reader, localized inline Status-cell label (no new column); jobs.test.mjs and mixed global/project browser rows. |
| Page identification | Job detail identifies its own recorded workflow in four locales. | REQ-UX-029d0525 | Browser direct/AEGIS composite routes, locale labels and switching without a stale label. | D1/D6: label in the current-state card from validated composite detail; jobs.test.mjs and four-locale switching journeys. |
| Direct steps | Direct stage presentation uses Implementation/build, Validation/validate and Done, showing only recorded stage evidence. | REQ-UX-ad37f7e7 | Model and browser build/validate/done plus saved timeline controls; no early AEGIS stages or invented completion. | D6: workflow-aware stage label used by list/card/ObservedTimeline; direct build/validate/done model controls and browser saved-events assertions. |
| No direct AEGIS task | Direct details contain no AEGIS task presentation. | REQ-UX-5cf762f8 | Browser detail/technical evidence absence; existing corrupt direct task-binding API negative. | D1/D6: retain state binding refusal; expose no task field and render no direct task row; existing API negative plus direct browser technical-details assertions. |
| Direct attempt | Detail shows the latest saved executor stage-launch attempt number. | REQ-UX-ef06a3c7 | API/model/browser known latest attempt distinct from lifetime launches/failures; malformed counter negatives. | D2: direct.attempt is last saved stage-launch ordinal, not budget.launches; API/model known-value and browser attempt assertions. |
| Honest attempt absence | No recorded launch gives an unavailable attempt, not a guessed ordinal. | REQ-UX-1b6f2a83 | API/model/browser absent-journal control with nonzero other counters; malformed present attempt is not absence. | D2: direct.attempt=null only with no launch; API/model absent-journal controls and unavailable browser copy. |
| Verification command | Detail shows the saved redacted command before its result. | REQ-UX-16f751b7 | API/model/browser command ordering and inert operators/markup; changed current config cannot substitute text. | D3/D6: saved command first in inert code text; no config lookup for verification; API redaction/config-independence, model and browser DOM-order proof. |
| Verification passed | A valid saved zero-exit non-timeout pass displays Passed. | REQ-UX-f6c6e946 | Model/browser pass including zero duration/empty output; timeout and status disagreement cannot pass. | D3/D6: agreeing passed result discriminant only; API/model zero-duration/empty-tail controls and localized browser Passed assertions. |
| Verification failed | A valid saved nonzero non-timeout failure displays Failed. | REQ-UX-7e9792e9 | Model/browser retained failure during build and terminal failure; exit 124 without timeout is Failed. | D3/D6: retain latest failed result across build/lifecycle changes; API/model 124 control and browser remediation/terminal fixtures. |
| Verification timed out | A valid saved timeout displays Timed out independently of exit code. | REQ-UX-647b1549 | Model/browser timeout controls including exit zero; invalid timeout type/status disagreement rejected. | D3/D6: timed_out takes priority over exit; API/model true-plus-zero control and browser distinct timeout result. |
| Explicit unverified | An explicit not-configured record displays Not configured: unverified. | REQ-UX-631835f9 | Model/browser unconfigured case with no fabricated measurements; absent status and contradictory result negatives. | D3/D6: explicit not-configured discriminant with null result, never a pass; API/model/browser controls and contradictions. |
| Verification duration | Configured-result detail displays recorded elapsed seconds. | REQ-UX-009b4cb9 | Model/browser zero, fractional, large finite duration controls; boolean, negative, nonfinite and overflow rejected. | D3: finite nonnegative seconds, overflow-safe Python validation; API/model numeric matrix and browser recorded-seconds display. |
| Verification output | Configured-result detail displays bounded redacted inert tail or an empty-output indication. | REQ-UX-9cdaa57b | API/model/browser empty and maximum-tail controls, leading whitespace, inert markup, credential masking and over-bound rejection. | D3/D6: validate source, web-redact then bound tail, preserve whitespace, render focusable pre or empty notice; API/model limits and browser inert-text proof. |
| Honest verification absence | No saved outcome/result displays verification unavailable. | REQ-UX-7fab3dcb | Model/browser pre-verification build distinct from explicit unverified; an outcome missing its result is an error. | D3: absent keys yield unavailable/null, present malformed keys fail; API/model pre-verification control and browser unavailable notice. |
| Read-only direct evidence | Authorized detail projects allowlisted saved attempt and latest independent result with explicit absence. | REQ-DATA-08ed925c | Offline API both roles, all outcomes/absence, saved-vs-current config, source-byte preservation, no commands and forbidden foreign reads. | D2/D3: _view builds direct projection from captured run/events; app strips it from lists only; API role/snapshot/source-preservation tests. |
| Persisted trust-boundary failures | Malformed selected job sources fail with typed secret-free errors and no partial totals or repair. | REQ-SEC-5d0f86e7 | Reuse source-error contract; add direct result/status/type/bounds and stage-launch attempt corruption to offline API coverage. | D4: existing JobReadError codes, strict all-selected-source validation and no repair; test_web_jobs.py malformed attempts/results, grants and races. |
| Unknown workflow error | Missing/nontext/unknown browser workflow rejects the response into the existing error state. | REQ-UX-b105b854 | Model list/detail invalid workflow matrix and browser injection after valid evidence; hide stale totals/detail and guessed labels. | D1/D5: strict workflow enum on both readers; list error/incomplete/changed also gates visibleDetail; model mutation matrix and browser post-success corruption. |
| Direct evidence transport error | Malformed browser direct attempt/verification evidence rejects the detail into the existing error state. | REQ-UX-46c09118 | Model shape/type/status/range/bounds matrix and browser corruption after valid detail; no fabricated pass/unverified result. | D3/D5: closed direct/result objects and status agreement in readJobDetail; model field/type/bound mutations plus browser stale-panel hiding. |
| Invalid direct stage error | Browser direct state/timeline naming a non-direct stage rejects the response. | REQ-UX-a8c7ea48 | Model current/timeline forbidden-stage matrix and browser corrupt-stage fixture; valid AEGIS controls retain their stages. | D4/D5: direct current/timeline domain is build/validate/done; refuse rather than filter; model and browser forbidden-stage controls. |
| AEGIS regression boundary | Existing authorized AEGIS current-state/actions/observed-only timeline rendering remains intact apart from workflow identification. | REQ-UX-b758d2b7 | Retain existing AEGIS model/browser assertions, including quick path, lifecycle/actions, timeline paging, missing evidence and error hiding; no direct panel. | D6: keep AEGIS copy, actions, columns and timeline unchanged; default workflow-aware helper to explicit aegis only at callers; retain existing assertions with additive fixture workflow. |
| Jobs help | Four-locale Jobs help explains direct workflow, attempt and each verification outcome. | REQ-UX-c77f7335 | Content tests plus help browser navigation, matching interface terms and locale structure/link/Markdown negatives. | D7: matching direct-evidence help sections in four jobs.md files; help.test.mjs semantic/parity checks and help.spec.ts navigation. |
| Stage-limit guidance | Four-locale Jobs/Settings help and inline guidance explain direct build/validate limit mapping and general-limit fallback. | REQ-UX-558518e7 | Content/setting-guidance tests and help browser navigation; no AEGIS-only limits attributed to direct jobs. | D7: four-locale jobs/settings help and inline general/map/wildcard guidance; settingHelp.test.mjs/help.test.mjs and help.spec.ts. |

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

### Approach

- INFERRED **D1** (REQ-DATA-18b26c84; REQ-UX-4123c97c, REQ-UX-029d0525, REQ-UX-b105b854): make recorded `workflow: "aegis" | "direct"` mandatory in `Job` and `readJob`; labels use that value, never repository readiness or config. Reuse existing routes, authorization and readers rather than introduce a workflow service.
- INFERRED **D2** (REQ-DATA-08ed925c; REQ-UX-ef06a3c7, REQ-UX-1b6f2a83): a private `jobs.py::_direct_evidence(run, events)` called by `_view` validates all direct `stage-launch` attempts in append order and projects the last, or null with none. It consumes the already captured sources; it does not reread state, infer counters or call the engine.
- INFERRED **D3** (REQ-DATA-08ed925c and shared spec; verification requirements in the map): the same helper projects only the latest saved independent verification. Reject calling `Orchestrator._direct_result`: OBSERVED it binds today's configured command and has execution-layer ownership, whereas saved Jobs evidence must survive changed/missing config. Keep this small read-boundary validator local; no new dependency or shared workflow abstraction.

### Interfaces and data

- INFERRED (D2/D3): detail-only `job.direct = {attempt, verification}`; `attempt` is a positive safe integer or null. `verification` is exactly `{status, result}`: status `unavailable` or `not configured` requires result null; status `passed`, `failed` or `timed out` requires exactly `{command, exit_code, seconds, timed_out, output}`. Missing direct evidence is represented inside this object, never by omitting the object on a direct detail. AEGIS details omit `direct`; list rows omit it for both workflows.
- INFERRED (D3; named technical constraint **JavaScript exact integer transport**): saved exit codes are Python integers without a declared width. Project `exit_code` as canonical decimal text (zero `"0"`, otherwise optional minus and nonzero-leading digits), preserving arbitrary integer values without float rounding; browser status agreement compares that exact text to `"0"`. This is a read transport choice only, not a stored-format change. `seconds` stays a JSON number after overflow-safe finite/nonnegative validation, `timed_out` stays boolean, command/output stay valid Unicode text. Model/API controls include large signed exit integers as well as ordinary exits.
- INFERRED (D3): detect absence by key presence: neither saved status nor result means unavailable; explicit `not configured` without a result means unverified. Explicit null, incomplete/extra result keys, bad types, contradictory status and invalid duration fail. A timeout wins over any exit code; exit 124 alone is failure. Preserve zero seconds and empty output. Validate normalized output (no NUL/ANSI, at most 200 lines/6000 Unicode scalars) before existing `redact_text`; mask both roles before any needed final tail cut, without trimming valid leading whitespace. Browser repeats shape/status/Unicode/bound checks; Python and JS count Unicode scalars and normalized LF lines consistently, not JS UTF-16 units.
- INFERRED **D4** (REQ-SEC-5d0f86e7; REQ-UX-a8c7ea48): validate every selected direct projection before search/counts/paging; invalid attempt/timeline yields `JobReadError("run_journal_corrupt")`, invalid verification/current stage yields `run_state_corrupt`. Current and non-null event stages must be build/validate/done. Keep existing Overview unreadable-project isolation, secret-free envelopes, optimistic revisions, final profile/grant reinspection and no-repair semantics. No engine/state-schema changes.
- INFERRED **D5** (REQ-UX-b105b854, REQ-UX-46c09118, REQ-UX-a8c7ea48): `readJobDetail` requires/validates the closed direct object only for direct jobs and refuses it on AEGIS; invalid responses use existing unexpected-response feedback. Gate `visibleDetail` on list errors/incomplete/source-change as well as detail success so malformed list workflow cannot leave prior direct evidence visible. Existing sequence/composite/session guards remain authoritative; successful refresh is the only recovery.

### Files and test seams

- INFERRED **D6** (REQ-UX-ad37f7e7, REQ-UX-5cf762f8, REQ-UX-b758d2b7 plus mapped display requirements): in `JobWorkspace.tsx`, add Workflow text under the existing Status-cell content and in the current-state card, retaining the five table columns. Add a workflow-aware stage-label helper in `jobCopy.ts`, shared by list/card/ObservedTimeline; direct labels come from new `i18n.ts` keys for Implementation/Validation/Done, AEGIS uses existing labels unchanged. Pass workflow explicitly. Branch direct Working explanation/guidance and observed-timeline copy so it never claims AEGIS or a quick path; keep AEGIS strings/assertions intact. Add a small local direct-evidence view after current-state evidence: latest recorded attempt (or unavailable), then command, localized result, recorded seconds and focusable inert `pre` tail (or empty notice). No synthetic stepper, task row, HTML/Markdown rendering, command action, new polling or verification progress inference.
- OBSERVED/INFERRED (D2/D3; `app.py::jobs_page` currently strips only timeline): change `adore/web/jobs.py` and the list exclusion in `adore/web/app.py`; details inherit direct evidence from the same captured `_view`. Extend `tests/test_web_jobs.py` through public HTTP reads for both roles, all outcomes/absence, latest journal order, malformed selected evidence, unauthorized unread sources, saved-vs-current config, redaction, source preservation and source/grant races. Reads must invoke no external runner.
- INFERRED (D1–D6): extend `web/tests/jobs.test.mjs` through public readers/helper to cover every coverage-row control and negative matrix; add workflow to the existing AEGIS fixture without weakening assertions. Add `web/e2e/jobs.spec.ts` journeys for global/project mixed lists, direct stages/attempt/outcomes, switching and post-success corrupt responses, four locales, desktop/narrow light/dark and keyboard overflow. Extend `web/e2e/server.py` with an opt-in direct fixture mode producing real persisted direct runs/journals; leave the default seed/reset and AEGIS cohort/counts unchanged. Browser interception is for transport-corruption tests, not a replacement for valid API fixtures.
- INFERRED **D7** (REQ-UX-c77f7335, REQ-UX-558518e7): update all four `web/src/help/content/{en,fr,de,ro}/{jobs,settings}.md`, preserving matched structure/links and adding legal headers if absent; explain attempts, four outcomes versus absence, and direct Implementation/build and Validation/validate limits with general fallback. Update `settingHelp.ts` general/map/wildcard guidance and `i18n.ts` shared verification-command guidance where necessary. Add semantic assertions to `web/tests/{help,settingHelp}.test.mjs` and navigation assertions to `web/e2e/help.spec.ts` without changing catalog/schema or runtime settings.
- STATED **D8** (AGENTS.md same-change documentation/bundle rules): build updates `05_SoftwareDocu/Component_Web_Jobs.md`, `Component_Web_Frontend.md`, `01_Documentation/Web_Interface.md`, `CHANGELOG.md`, four-locale `adore/release_notes.toml` and the committed `adore/web/static/` production bundle/fingerprints via `npm run build`. Update the active Jobs read spec's broad validation-output exclusion narrowly when implementation exists. Build logs `release-notes: added` and `help: updated` and runs the base-bound release-note checker. Knowledge/context current-state claims wait until validate, per stage instructions.

### Risks and open decisions

- OBSERVED/INFERRED: saved verification output is not the canonical operational executor-output stream; keep the two panels/contracts separate, apply existing credential masking and render literal text. No authorization, finances, subprocess, storage or publication authority is added (D3/D4/D6).
- OBSERVED (`RunState.from_dict`, `_view`, `_event_stage`): direct current `publishing` is admitted by the generic state vocabulary, but the direct engine retains done during publication; this read boundary will refuse publishing stage (not lifecycle), preserving the ticket/spec domain without changing run behavior (D4). Unrelated timeline stages remain null; do not filter corrupt events or manufacture stages.
- INFERRED: no decision-blocking product question remains; existing sources record the needed data. The transport spelling choices above settle only design unknowns; no migration, compatibility fallback, dependency, planning edit or managed-payload edit is authorized. If build discovers a missing datum or plan conflict, use the required questions-file blocked pause.
- INFERRED (repository bounded-run rule): this design pass is bounded to 30 minutes, one journal, the 23 pinned requirement files, one shared draft spec and one diagram file; no product edits, setup, product tests or external calls. Build runs targeted ticket commands; validate alone runs the full strict gate and review/report. Dependency availability and test outcomes remain UNKNOWN until those stages; missing `rg` was handled with grep/Python, not a product change or verification deviation.

### Requirement map

The 23 coverage rows above each retain a concrete test seam and now name these decisions; no pinned requirement is left without impact/coverage:

- D1: REQ-DATA-18b26c84, REQ-UX-4123c97c, REQ-UX-029d0525, REQ-UX-b105b854.
- D2: REQ-UX-ef06a3c7, REQ-UX-1b6f2a83; D2/D3: REQ-DATA-08ed925c.
- D3/D6: REQ-UX-16f751b7, REQ-UX-f6c6e946, REQ-UX-7e9792e9, REQ-UX-647b1549, REQ-UX-631835f9, REQ-UX-009b4cb9, REQ-UX-9cdaa57b, REQ-UX-7fab3dcb.
- D4: REQ-SEC-5d0f86e7; D4/D5: REQ-UX-a8c7ea48; D3/D5: REQ-UX-46c09118.
- D6: REQ-UX-ad37f7e7, REQ-UX-5cf762f8, REQ-UX-b758d2b7.
- D7: REQ-UX-c77f7335, REQ-UX-558518e7; D8 is a named repository obligation, not a new product requirement.

Diagrams: [diagram_TASK-aad00a23.md](diagram_TASK-aad00a23.md)

## Log

- 2026-11-12 frame: journal opened
- 2026-11-12 frame: Frame scope recorded under conductor-authorized autopilot. Full path retained: new Jobs workflow/evidence UI and read-only evidence projection require specify/design; existing state records required data, with no blocking plan conflict identified. Implementation, setup and tests deferred to their supervised stages.
- 2026-11-12 frame: completed; next specify - Frame complete; scope recorded under conductor-authorized autopilot, full path justified, no decision-blocking questions identified
- 2026-11-12 specify: Specify complete: 23 atomic coverage rows map in order to 20 new draft requirements and 3 unchanged active contracts; one shared draft spec defines recorded attempt, latest verification, honest absence and typed failures. Required evidence is already persisted; no blocking question. Ordered TOML/coverage audit and git diff --check exited 0; check --task TASK-aad00a23 --full/--json exited 0 with errors=0, warnings=35, notes=29. Verified all 35 warning paths exist unchanged at task base; no task format errors, and the no-anchor note is expected before build. Product tests were not run in specify. Transport spelling/placement remains design work; help, release notes, component documentation and bundle remain build work.
- 2026-11-12 specify: completed; next design
- 2026-11-12 design: Design complete under D1-D8: saved workflow remains authoritative; detail-only closed direct attempt/latest-verification projection uses captured sources and existing redaction/errors; exact decimal-text exit codes avoid JavaScript integer loss without changing storage; workflow-aware localized UI retains AEGIS assertions and observed-only timelines. All 23 coverage rows map to decisions/test seams; affected_paths updated; shared draft spec fixes transport; structure/sequence/read-state diagrams saved in .agentic/tasks/diagram_TASK-aad00a23.md. Audit of traceability, existing paths/specs, stage zone, headers and LF exited 0; git diff --check exited 0. check --task TASK-aad00a23 --full and --json exited 0: errors=0, warnings=35, notes=29; every warning-bearing file verified unchanged from task base. No product tests, setup, knowledge/context or product edits; no blocking question. Build owns failing tests first, implementation, four-locale help/release note, component/operator docs and production bundle; validate owns current knowledge and final strict proof.
- 2026-11-12 design: completed; next build
- 2026-11-12 build: red: cd 04_Software && uv run --frozen --extra web python -m pytest -q tests/test_web_jobs.py -k 'direct_saved or direct_absent or direct_corrupt' exit 1: 44 expected failures, missing direct projection and corrupt evidence accepted (REQ-DATA-08ed925c, REQ-SEC-5d0f86e7, REQ-UX-ef06a3c7, REQ-UX-1b6f2a83, REQ-UX-16f751b7, REQ-UX-f6c6e946, REQ-UX-7e9792e9, REQ-UX-647b1549, REQ-UX-631835f9, REQ-UX-009b4cb9, REQ-UX-9cdaa57b, REQ-UX-7fab3dcb, REQ-UX-a8c7ea48). Locked uv/npm setup succeeded; production npm audit reports zero vulnerabilities; two npm-ci high warnings are dev-only and no dependencies changed.
- 2026-11-12 build: green: cd 04_Software && uv run --frozen --extra web python -m pytest -q tests/test_web_jobs.py exit 0 (169 passed); uv run --frozen ruff check adore/web/jobs.py tests/test_web_jobs.py exit 0. API direct attempt/verification increment covers REQ-DATA-08ed925c, REQ-DATA-18b26c84, REQ-SEC-5d0f86e7 and D2-D4 evidence requirements; all existing API tests retained. Upstream Starlette TestClient deprecation is nonblocking; no dependency changes.
- 2026-11-12 build: red: cd 04_Software/web && node --test tests/jobs.test.mjs exit 1 (13 pass, 3 expected failures: missing/unknown workflow, malformed direct evidence and AEGIS-only direct stages accepted). REQ-UX-4123c97c, REQ-UX-029d0525, REQ-UX-b105b854, REQ-UX-46c09118, REQ-UX-a8c7ea48; positive evidence controls also cover D2/D3 attempt, outcome, duration and tail requirements.
- 2026-11-12 build: green: cd 04_Software/web && node --test tests/jobs.test.mjs exit 0 (16 tests). Mandatory workflow, closed direct evidence, exact decimal exits, Unicode-scalar bounds, honest absence and direct-stage transport controls now pass; existing AEGIS assertions retained with additive workflow fixture field (REQ-UX-b105b854, REQ-UX-46c09118, REQ-UX-a8c7ea48 and D1-D3 model coverage).
- 2026-11-12 build: red: npm run build:e2e exit 0; playwright test e2e/jobs.spec.ts --grep 'direct jobs show saved' exit 1: real persisted direct fixtures render legacy Build and lack Workflow: Direct (REQ-UX-4123c97c, REQ-UX-029d0525, REQ-UX-ad37f7e7, REQ-UX-5cf762f8 and D2/D3 presentation requirements). Added isolated opt-in direct fixture mode without changing default AEGIS seeds. Browser/runtime prerequisites verified available.
- 2026-11-12 build: green: npm run build:e2e exit 0; playwright test e2e/jobs.spec.ts --grep 'Direct job evidence' proved five display/locale/layout journeys; after correcting late clock installation in test fixture, playwright test e2e/jobs.spec.ts --grep 'corrupt .* hides previously' exit 0 (4 passed). All nine direct journeys green across those focused runs; full Jobs regression remains before build completion. red: node --test tests/help.test.mjs tests/settingHelp.test.mjs exit 1 (16 pass, 2 expected failures: missing direct-evidence help and direct timeout mapping). REQ-UX-c77f7335, REQ-UX-558518e7.
- 2026-11-12 build: green: node --test tests/help.test.mjs tests/settingHelp.test.mjs in combined focused run now passes all help/guidance assertions. red: combined jobs/help/settingHelp model run exit 1 (32 passed, 2 expected failures): newly added one-element array workflow/status coercion controls reveal String() could accept nontext enums (REQ-UX-b105b854, REQ-UX-46c09118).
- 2026-11-12 build: release-notes: added
- 2026-11-12 build: help: updated
- 2026-11-12 build: green: node --test tests/jobs.test.mjs tests/help.test.mjs tests/settingHelp.test.mjs exit 0 (34); npm test exit 0 (170); npm run build:e2e/typecheck exit 0; uv run --frozen ruff check adore tests exit 0. All new direct Jobs/browser/help cases passed in the ticket run (57/60 overall). Inspection: operator/component docs, current direct read spec and existing allowlist exception now match implemented saved evidence and no-run-behavior boundary; all 23 pinned requirements are active with real linked tests and design affected_paths. Four-locale release note added and merged with related Jobs note to retain the category cap; checker exit 0.
- 2026-11-12 build: DEVIATION build: ticket browser aggregate has three pre-existing host-check failures - accepted for this stage without changing unrelated product behavior: current Jobs/help 57 pass/3 fail, pristine HEAD archived to an automatically isolated temporary tree and baseline Jobs run 41 pass/the identical three failures. Targeted host-check reruns on both baseline and candidate yield 1 pass/2 identical API readiness_probe_failed failures. AEGIS render assertions remain unchanged; new direct/help cases all pass. Validate must report these baseline strict-gate blockers honestly, not waive the final check. npm dev-only audit warnings, upstream TestClient deprecation and existing Vite large-chunk advisory do not affect the direct evidence proof.
- 2026-11-12 build: red: pytest -q tests/test_web_jobs.py -k 'output-trailing-lf or output-separator' exit 1 (2 expected failures) and node --test --test-name-pattern 'malformed direct evidence' tests/jobs.test.mjs exit 1: noncanonical saved output with trailing LF/alternate Unicode separators was accepted despite writer normalization (REQ-SEC-5d0f86e7, REQ-UX-46c09118, REQ-UX-9cdaa57b). Final source review identified the missing normalization check; no execution change.
- 2026-11-12 build: red: node --test --test-name-pattern 'direct stage labels and timeline' tests/jobs.test.mjs exit 1: direct timeline explanatory Done translation differs from the existing locale stage label (REQ-UX-ad37f7e7, REQ-UX-b758d2b7). Public helper regression now asserts all direct names and unchanged AEGIS labels.
- 2026-11-12 build: green: normalized-tail and locale-copy increments proven by final pytest tests/test_web_jobs.py exit 0 (171 passed), Ruff adore/tests exit 0, npm test exit 0 (171), npm run build:e2e/typecheck exit 0, playwright jobs/help focused domain run exit 0 (57 passed excluding the three baseline host-check cases already independently reproduced), and final direct/four-locale-help browser rerun exit 0 (13 passed). Public helper labels, malformed canonical exit text, all direct outcomes and stale-evidence controls remain green. npm run build exit 0 regenerates production assets/fingerprint. No full strict suite run in build.
- 2026-11-12 build: Evolution reviewed: all 31 non-governance changes match D1-D8 (including API tests extended after anchor); generated JS replacement, index and fingerprint are the expected production output. Requirement/test-path audit and asset input/output fingerprint comparison exit 0; release-note checker and git diff --check exit 0. Check exit 0: errors=0 warnings=39 notes=28. All 35 original warning-bearing files remain unchanged at task base (stale paths/ticket refs/older journals/checklists); four candidate warnings are reviewed: generated minified JS is intentionally unscanned, and password literals in API tests, browser tests and server fixtures are synthetic isolated redaction/sign-in inputs, not credentials. No unrelated repairs or managed payload changes. Stage work stays under 60 changed files and 55 minutes, with no paid external operations; full suite/reviews/knowledge updates remain validate responsibilities.
- 2026-11-12 build: DEVIATION build: retained the eight existing help topics' headerless format rather than adding HTML legal comments - the installed help subset requires a title on line 1 and rejects HTML; expanding its parser is outside ticket scope. Existing source/test/doc license prologues are preserved and generated assets are stamped with the project header.
- 2026-11-12 build: completed; next validate
- 2026-11-12 validate: Inspection: reviewed the full base-to-candidate diff against all 23 pinned active requirements, shared direct-evidence and existing Jobs specs, D1-D8, ticket and plan sections 1/4. API projection is captured/read-only, masked for both roles and excludes direct evidence from lists; strict browser workflow/result/stage readers and stale-panel hiding match their actual API/model/browser assertions. No execution/storage/dependency changes or unrelated repairs identified. Current web-interface knowledge routing/interface/invariants/change-map/behavior seams and project context reconciled; environment guide already accurately describes locked setup, matching Chromium, machine identity and strict commands, so needs no edit. No pinned Manual verification remains; inspection covers literal rendering, command-before-outcome, AEGIS label preservation, help terms/structure and no invented evidence. Bundle input/output fingerprint audit, release-note checker against fc943f9b82c93967dc22bf76e1e5cccf34b242d5 and git diff --check exit 0. Validation bounded to one strict full run, two read-only reviewer calls (480s each), at most 50 minutes and three executor-edited repository files; no publication or forge access.
- 2026-11-12 validate: Independent review round 1: two separate ephemeral Pi processes, restricted to read/grep/find/ls with no writes or test runs, reviewed the same final candidate and actual assertions. Specification compliance APPROVED (all 23 requirements, D1-D8, scope/exclusions); implementation quality APPROVED (correctness, typed errors, authorization/redaction, transport, tests and portability); neither reported blocking findings. Verdicts recorded through CLI. Fresh locked uv sync --frozen --extra web and npm ci exit 0; Python verification imports, Playwright 1.63.0 and matching Chromium available. npm audit --omit=dev exit 0 (zero production vulnerabilities); two existing dev-only high advisories remain with unchanged lockfile. Container's empty /etc/machine-id required installing dbus then systemd through authorized apt-get; package setup initialized machine identity successfully, with no repository edits. Preflight check exit 0: 0 errors, 39 warnings, 28 notes; 35 warning-bearing baseline files verified byte-identical to task base, four candidate password-literal warnings are generated UI/public synthetic test inputs, not credentials. Existing help-format, TestClient and Vite advisories remain as documented at build.
- 2026-11-12 validate: final: python .agentic/aegis.py check --task TASK-aad00a23 --strict --run exit 1 after the last candidate edit; Python full suite 5 failed, 3668 passed, 2 skipped (669.2s); Ruff exit 0; complete npm frontend validation exit 0 (934.5s), including helper tests, TypeScript, isolated build and all Chromium journeys. Errors=1 (test command failure), warnings=39, notes=28; advisory warning dispositions are recorded above. The five failures are test_executor_settings.py::{test_model_evidence_survives_reload_and_invalidates_on_credentials,test_private_write_failure_preserves_credentials,test_credentials_changing_during_test_do_not_publish_evidence} and test_local_execution.py::test_local_model_challenge_uses_the_managed_rpc_installation[provider,large]. No full strict pass is claimed. Build's three host-check browser failures did not recur in this full frontend run.
- 2026-11-12 validate: DEVIATION validate: final strict Python proof inherited the executor provider credential - ambient OPENAI_API_KEY is present and defeats isolated fake credential assumptions; the five failing tests and their executor_settings/model_connection/local_execution sources are byte-identical to task base. Narrow diagnostic rerun with env -u OPENAI_API_KEY uv run --frozen --extra web --project 04_Software python -m pytest -q 04_Software/tests/test_executor_settings.py 04_Software/tests/test_local_execution.py -k '<the three credential tests or managed RPC challenge>' exit 0 (6 passed, 196 deselected, 2.18s, including the keyless control). This identifies an environment cause, not a candidate fix or strict pass. No product/test/payload edits, exclusions or suppressions made. Remaining work is a fresh complete strict gate under env -u OPENAI_API_KEY, then updated final evidence/report and advance only if it passes; stop now to retain the recorded one-full-run/session bound.
- 2026-11-12 validate: Diagnostic command exact selector: env -u OPENAI_API_KEY uv run --frozen --extra web --project 04_Software python -m pytest -q 04_Software/tests/test_executor_settings.py 04_Software/tests/test_local_execution.py -k 'test_model_evidence_survives_reload_and_invalidates_on_credentials or test_private_write_failure_preserves_credentials or test_credentials_changing_during_test_do_not_publish_evidence or test_local_model_challenge_uses_the_managed_rpc_installation' exit 0 (6 passed, 196 deselected). Delivery report appended and read: its checks errors=0 is the static advisory report, not the final --run command, which failed and remains the controlling result. All validation record/checklist obligations completed; closure remains blocked on a passing fresh full strict proof. Candidate edits remain limited to project context and web-interface knowledge; original product candidate is preserved.

## Rulings


## State

status: blocked
reported: validate - blocked
next: In a fresh validate session, verify setup/machine identity, then run env -u OPENAI_API_KEY python .agentic/aegis.py check --task TASK-aad00a23 --strict --run against the unchanged reviewed candidate; log its actual result, append/read report and advance only if it passes
must_read: .agentic/tasks/TASK-aad00a23.md, .agentic/steps/5_validate.md
changed: Reviewed candidate and all 23 requirements; reconciled project context and web-interface knowledge; independent spec and quality reviews approved at round 1; preserved all ticket implementation artifacts
evidence: Strict check --strict --run exit 1: Python 3668 passed/5 failed/2 skipped; Ruff and full frontend exit 0. Six affected credential/native cases pass with OPENAI_API_KEY unset. Release-note, bundle fingerprint and diff audits exit 0; report appended
issues: Strict gate is not passed: inherited OPENAI_API_KEY interferes with five unchanged fake-credential tests. Narrow scrubbed-environment diagnostic passes but cannot replace the pending fresh full strict run. Existing 39 advisory warnings/28 notes, dev-only npm advisories and help-format exception remain documented; prior host-check browser failures did not recur
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-11-12)

- stage: validate; type: feature; path: full; branch: adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-66
- requirements:
  - REQ-DATA-18b26c84 - Serialize workflow in authorized job reads
  - REQ-UX-4123c97c - Identify workflow in job lists
  - REQ-UX-029d0525 - Identify workflow on the job page
  - REQ-UX-ad37f7e7 - Present direct workflow stages
  - REQ-UX-5cf762f8 - Keep direct jobs free of AEGIS task presentation
  - REQ-UX-ef06a3c7 - Show the recorded direct attempt number
  - REQ-UX-1b6f2a83 - Keep an unrecorded direct attempt explicitly unavailable
  - REQ-UX-16f751b7 - Show the saved direct verification command
  - REQ-UX-f6c6e946 - Show passed direct verification
  - REQ-UX-7e9792e9 - Show failed direct verification
  - REQ-UX-647b1549 - Show timed out direct verification
  - REQ-UX-631835f9 - Show unconfigured direct verification as unverified
  - REQ-UX-009b4cb9 - Show direct verification duration
  - REQ-UX-9cdaa57b - Show the direct verification output tail
  - REQ-UX-7fab3dcb - Keep absent direct verification explicitly unavailable
  - REQ-DATA-08ed925c - Project recorded direct evidence to authorized job details
  - REQ-SEC-5d0f86e7 - Fail closed on corrupt job read evidence
  - REQ-UX-b105b854 - Reject unrecognized job workflow in the browser
  - REQ-UX-46c09118 - Reject malformed direct evidence in the browser
  - REQ-UX-a8c7ea48 - Reject non-direct stages in direct job responses
  - REQ-UX-b758d2b7 - present complete authorized scoped current-state
  - REQ-UX-c77f7335 - Explain direct Jobs evidence in localized help
  - REQ-UX-558518e7 - Explain direct stage limits in localized guidance
- deviations: 3 recorded
  - build: ticket browser aggregate has three pre-existing host-check failures - accepted for this stage without changing unrelated product behavior: current Jobs/help 57 pass/3 fail, pristine HEAD archived to an automatically isolated temporary tree and baseline Jobs run 41 pass/the identical three failures. Targeted host-check reruns on both baseline and candidate yield 1 pass/2 identical API readiness_probe_failed failures. AEGIS render assertions remain unchanged; new direct/help cases all pass. Validate must report these baseline strict-gate blockers honestly, not waive the final check. npm dev-only audit warnings, upstream TestClient deprecation and existing Vite large-chunk advisory do not affect the direct evidence proof.
  - build: retained the eight existing help topics' headerless format rather than adding HTML legal comments - the installed help subset requires a title on line 1 and rejects HTML; expanding its parser is outside ticket scope. Existing source/test/doc license prologues are preserved and generated assets are stamped with the project header.
  - validate: final strict Python proof inherited the executor provider credential - ambient OPENAI_API_KEY is present and defeats isolated fake credential assumptions; the five failing tests and their executor_settings/model_connection/local_execution sources are byte-identical to task base. Narrow diagnostic rerun with env -u OPENAI_API_KEY uv run --frozen --extra web --project 04_Software python -m pytest -q 04_Software/tests/test_executor_settings.py 04_Software/tests/test_local_execution.py -k '<the three credential tests or managed RPC challenge>' exit 0 (6 passed, 196 deselected, 2.18s, including the keyless control). This identifies an environment cause, not a candidate fix or strict pass. No product/test/payload edits, exclusions or suppressions made. Remaining work is a fresh complete strict gate under env -u OPENAI_API_KEY, then updated final evidence/report and advance only if it passes; stop now to retain the recorded one-full-run/session bound.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base fc943f9: 60 file(s) changed, 5251 line(s) added
- checks: errors=0 warnings=39 notes=28
- checklist: 6/9 done; open: final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
