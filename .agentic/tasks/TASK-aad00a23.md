<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-aad00a23 - [Direct] Show direct jobs clearly in Jobs

stage: specify
type: feature
path: full
interaction: autopilot
requirements:
parent:
branch: adore/gitea-dpasare-AgenticDeliveryOrchestratorRuntimeEngine-66
base: fc943f9b82c93967dc22bf76e1e5cccf34b242d5
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


## Design


## Log

- 2026-11-12 frame: journal opened
- 2026-11-12 frame: Frame scope recorded under conductor-authorized autopilot. Full path retained: new Jobs workflow/evidence UI and read-only evidence projection require specify/design; existing state records required data, with no blocking plan conflict identified. Implementation, setup and tests deferred to their supervised stages.
- 2026-11-12 frame: completed; next specify - Frame complete; scope recorded under conductor-authorized autopilot, full path justified, no decision-blocking questions identified

## Rulings


## State

status: ready
reported: frame - completed
next: Specify atomic Jobs workflow, direct evidence and fail-closed behaviors with requirement coverage
must_read: .agentic/tasks/TASK-aad00a23.md, .agentic/steps/2_specify.md
changed: Completed the evidence-labelled Frame, scope, constraints, success signals and full-path criteria in .agentic/tasks/TASK-aad00a23.md; all seven frame checklist items satisfied; no product changes
evidence: AEGIS status/brief/components and git branch --show-current exited 0; inspected plan sections 1/4, Jobs source/tests and persisted direct evidence contracts; git diff --check exited 0; no tests run in frame
issues: No blocking questions; exact evidence transport and attempt projection remain for specify/design; dependency availability and test outcomes not yet verified
spec_compliance:
implementation_quality:
review_round:
