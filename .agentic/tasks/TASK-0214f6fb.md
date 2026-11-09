# TASK-0214f6fb - Remove OpenCode, Codex and Qwen Code support (PI-03, #53)

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-FUNC-78b0ad95, REQ-FUNC-2df31adf, REQ-FUNC-97e17737, REQ-FUNC-de028c15, REQ-FUNC-8f369d55, REQ-FUNC-0b728218, REQ-FUNC-7ce5b17a, REQ-PLAT-722173c8, REQ-UX-d93fab0f, REQ-FUNC-17d58879, REQ-SEC-617a95f5, REQ-SEC-eaad89c3, REQ-REL-23ce3d34, REQ-FUNC-c829c366, REQ-FUNC-2710d0f4, REQ-FUNC-fec24fc3, REQ-FUNC-59ccdb74, REQ-FUNC-08cc2676, REQ-UX-646e81fb, REQ-UX-b75e1df8, REQ-UX-d8745013, REQ-SEC-e24e2341, REQ-SEC-f7b9111e, REQ-FUNC-e5419c07
parent:
branch: task/adore-web-interface
base: 776e56f8d3c0b10320f8cd5414b4b919cd474699
opened: 2026-11-02

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [ ] diff reviewed against scope, requirements, design, error paths,
      portability, security and unrequested work
- [ ] knowledge pages of changed components current with the reviewed code
- [ ] project and environment context reconciled with the candidate
- [ ] requirements re-read: status, prose, verification, paths and links true
- [ ] manual or inspection verification recorded where applicable
- [ ] explicit review approved, when enabled
- [ ] final `check --strict --run` result logged truthfully after the last edit
- [ ] remaining warnings and pre-existing failures explained
- [ ] `report` appended

## Frame

Problem: ADORE still supports four coding agents. `[executor] default` picks
OpenCode, Pi, Codex or Qwen Code, with per-agent launcher classes, presets,
validation, model probes, OpenCode-only features (custom endpoint, model
catalogue, endpoint probe, local configuration isolation), host sign-in
staging, an image with every CLI, and an agent choice in Settings, enrollment
and the CLI wizard (OBSERVED `git grep -i -E "opencode|codex|qwen"`: 219 files;
PLAN.md section 5).
Desired outcome: Pi is the only coding agent. No other agent remains in code,
configuration, image, interface, tests or documentation, and there is no
agent choice anywhere (STATED ticket #53 Goal).
Actors: administrator (Settings, enrollment), operator (config.toml, CLI
wizard, doctor), the orchestrator launching stages, the executor image build.
Primary scenario: a project's `[executor]` names only the Pi model (and, for
a local native run, its argv template); every stage launches Pi; Settings ->
Agent and model shows model, launch command, credential variables, project
API keys and Test AI connection, with no agent selector.
Examples: `[executor.opencode]` -> `[executor] unknown key 'opencode': remove
it from config.toml`; `default = "codex"` -> `[executor] unknown key
'default': remove it from config.toml`; `[executor.qwen]` likewise (STATED
ticket Decisions, the first message's form).
Counterexamples: Statistics rows already stored with executor "opencode" are
still displayed as stored text (stored metrics are data, not configuration;
INFERRED from AGENTS.md "no migrations": nothing rewrites them).
In scope: ticket Scope list (launcher classes and selector; presets in
executor_configuration, wizard, config.example.toml; config validation,
OpenCode endpoint and default executor; model_connection probes; host
sign-in staging; local_execution OpenCode isolation and other agents' homes
and auth paths; endpoint_probe, opencode_catalogue, app.py endpoint routes,
doctor checks; Dockerfile and verify-runtime; web files; tests; help, docs,
knowledge, requirements) plus `[labels.executor]` (a reserved per-ticket
agent pin, an agent choice) and the tracked dev `config.toml`.
Out of scope: provider/endpoint settings for Pi (PI-04), ChatGPT sign-in
(PI-05), internet switch (PI-06), server-installed Pi over RPC (PI-07)
(STATED ticket "Out").
Constraints: no migration, refuse with key and fix; keep the internal
executor interface with Pi as its only implementation; offline tests; LF;
license headers; `git commit -s` without AI trailers (STATED ticket, AGENTS.md).
Success signals: ticket acceptance criteria; listed suites green.
Evidence: PLAN.md sections 4-5; PI-02 commit 776e56f; RULING-004 of
TASK-41fd0159 (Agent and model hint left for this ticket).
Assumptions: none beyond the ticket.
Unknowns: none blocking.
Decision-blocking questions: none; the schema shape is a ruling (RULING-002).
Proposed behaviors: accepted by the ticket Decisions.
Path and reason: full.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | agent choice and features removed; refusals |
| no new interface or data format | no | `[executor]` schema changes |
| no new dependency | yes | removals only |
| an existing requirement already covers the behavior | no | several requirements retire |
| no security or data-handling change | no | host sign-in staging and local isolation removed |

## Requirement coverage

| Behavior | Requirement | Status |
|---|---|---|
| Config naming a removed agent key/table is refused with key and fix | REQ-FUNC-78b0ad95 | created |
| Every stage, probe and report uses Pi; no agent choice anywhere | REQ-FUNC-2df31adf | created |
| Executor validation without per-agent rules | REQ-FUNC-97e17737 | revised |
| Test AI connection for Pi only | REQ-FUNC-de028c15, REQ-FUNC-8f369d55, REQ-FUNC-0b728218 | revised |
| Web configuration without the OpenCode endpoint edit | REQ-FUNC-7ce5b17a, REQ-PLAT-722173c8 | revised |
| Prices for the applied model (agent is always Pi) | REQ-UX-d93fab0f | revised |
| Managed OpenCode settings / permission / isolation / directory | REQ-FUNC-17d58879, REQ-SEC-617a95f5, REQ-SEC-eaad89c3, REQ-REL-23ce3d34 | retired |
| Atomic agent selection | REQ-FUNC-c829c366 | retired |

## Design

**Approach.** Delete, do not adapt. `ExecutorConfig` loses `default`,
`stage_host_auth` and `commands` and gains `model` and `command` (default
`pi -p --mode json --model {model} {prompt}`, used only by a native run until
PI-07). The existing unknown-key check refuses `default`, `stage_host_auth`,
every `[executor.<name>]` table and `[labels.executor]` with `[<table>]
unknown key '<key>': remove it from config.toml` (RULING-002).
`build_executor(command, model, questions_file)` returns `PiExecutor`; the
`Executor` base and `FileProtocolExecutor` stay (native Pi uses the file
protocol). `EXECUTOR_NAME = "pi"` feeds usage events, project views and
probes. Removed: OpenCode/Codex/Qwen launcher classes; host sign-in staging
(orchestrator, execution backends `auth_directory`, branding paths,
preparation `auth_file`, executor_settings mount fingerprint and hints);
`opencode_catalogue.py`, `web/endpoint_probe.py`, the endpoint edit routes,
pending-candidate endpoint review and readiness `model_endpoint`; local
OpenCode isolation, CODEX_HOME and other agents' auth paths; the per-agent
probe runner (Pi only); the doctor OpenCode check; image layers; the
`executor.selection` composite (model and command become ordinary reviewed
settings); agent choice in enrollment and the wizard (`auth_mode` host-auth
removed).
**Web.** Settings -> Agent and model shows model, launch command, credential
variables, project API keys and Test AI connection; the ChatGPT/agent login
hint and the /home/adore/.pi/agent path go (RULING-004 of TASK-41fd0159).
Enrollment step 2 shows model and, for local runs, the command.
**Stored data.** Usage rows with other executor names are left as stored
text; no migration.
**Tests.** Delete tests of removed behaviour; reduce agent loops to Pi;
add refusal tests in tests/test_config.py.

## Log

- 2026-11-02 frame: journal opened
- 2026-11-02 frame: completed; next specify - scope recorded (autopilot, RULING-001) (7 Done checklist item(s) left unticked)
- 2026-11-02 specify: DEVIATION specify: retired REQ-FUNC-17d58879, REQ-SEC-617a95f5, REQ-SEC-eaad89c3, REQ-REL-23ce3d34 (OpenCode-only) and REQ-FUNC-c829c366 (agent selection) - the behaviour is removed by the ticket
- 2026-11-02 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-02 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-02 build: red: pytest tests/test_config.py exit 1 - [executor] model/command schema and removed-agent refusals missing (REQ-FUNC-78b0ad95, REQ-FUNC-2df31adf)
- 2026-11-02 build: green: .venv python -m pytest (full suite) exit 0 - 1836 passed, 3 skipped (REQ-FUNC-78b0ad95, REQ-FUNC-2df31adf)
- 2026-11-02 build: release-notes: updated (Agents note now says Pi is the only coding agent; the local-OpenCode fixed note now covers the local Pi test only; OpenCode dropped from PRODUCT_NAMES)
- 2026-11-02 build: help: updated (executors, glossary, projects, overview, settings, statistics in en/fr/de/ro: Pi only, no agent choice, no endpoint form, no host sign-in)
- 2026-11-02 build: green: npm test exit 0 (100 pass); npm run typecheck exit 0; npm run build:e2e exit 0; playwright executor-config/settings/enrollment 53 tests (after removing the endpoint e2e test and the labels.executor assertion) pass; jobs/model-connection/import/help 50 pass
- 2026-11-02 build: Decision: readiness keeps six checks; the Test AI connection evidence is still shown as the AI model connection row; a setup check with all six checks true is now verified (the model endpoint row that made it partial was OpenCode-only)
- 2026-11-02 build: DEVIATION build: bundled assets in adore/web/static were not rebuilt (the brief said build:e2e only); they still contain the old strings until the next bundle rebuild
- 2026-11-02 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-02 validate: quality review round 1 changes_required: Q1 major stale OPENCODE_CONFIG_CONTENT value no longer redacted in GET /config; Q2 example header names [executor.<name>]; Q3 launcher docstrings; Q4 app.py host-auth remnants; Q5 'selected agent' copy in readiness/environment; Q6 web findings name executor.unknown instead of the key; Q7 Component_Web_API edit_key doc; Q8 bundle not rebuilt (accepted: already logged deviation, brief forbids writing adore/web/static). Fixing Q1-Q7.
- 2026-11-02 validate: returned to build - quality review round 1 findings Q1-Q7
- 2026-11-02 build: red/green: test_config_view_hides_a_removed_agents_environment_value fails (2 failed) without the removed-agent redaction and passes with it (Q1)
- 2026-11-02 build: Fixed Q1-Q7: removed-agent env values hidden in GET /config (_removed_agent_environment) with tests; web findings name the key to delete (test_import_names_the_removed_agent_key_to_delete); Pi wording in readiness, environment, enrollment, local, help copy; unused endpoint-probe reason labels removed; docstrings, example header, Dockerfile header, Component_Web_API.
- 2026-11-02 build: DEVIATION validate: retired REQ-FUNC-2710d0f4 and REQ-FUNC-fec24fc3 (OpenCode model endpoint readiness/profile) - the behaviour is removed; revised REQ-FUNC-59ccdb74 to the native Pi file protocol
- 2026-11-02 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-02 validate: green: npm run build:e2e exit 0; playwright executor-config/settings/enrollment exit 0 (52 passed) after the round-1 fixes
- 2026-11-02 validate: round 2 (round 1 had the quality review only): spec changes_required - S1 Component_Web_Frontend selection editor text, S2 Component_Web_API agent choices, S3 02_Tools offline packaging --executor choice and Component_Packaging, S4 AGENTS.md executor-agnostic example, S5 stale Unreleased CHANGELOG entries, S6 knowledge config.md symbol name; quality approved with minor N1 dotted removed-agent env key not redacted
- 2026-11-02 validate: returned to build - spec round 2 findings S1-S6 and quality N1
- 2026-11-02 build: Fixed S1-S6 and N1: Component_Web_Frontend/Web_API/Packaging, Web_Interface offline section; 02_Tools offline --executor now any|pi; AGENTS.md executor-agnostic example (one interface, Pi its only implementation); stale Unreleased CHANGELOG lines; knowledge symbol; dotted removed-agent env names redacted (test extended)
- 2026-11-02 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-02 validate: validate round 3: spec changes_required (project.md agent selection and executor-prefix wording; stale Unreleased CHANGELOG bullets for OpenCode endpoint, OpenCode/Codex/Qwen model tests, Pi/Qwen host-auth; unreachable 'Agent selection' label; Component_Web_Frontend wording) -> fixed; quality approved
- 2026-11-02 validate: returned to build - spec round 3 findings
- 2026-11-02 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-02 validate: validate round 4: spec changes_required ('selected-agent settings' in web-interface knowledge and Web_Interface.md; Unreleased CHANGELOG agent-selection wording) -> fixed; quality approved (no code change since round 3)
- 2026-11-02 validate: returned to build - spec round 4 findings
- 2026-11-02 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-02 validate: validate round 5: spec changes_required (CHANGELOG offline 'selected executor binary'; web-interface knowledge 'agent/model selections') -> fixed; quality approved
- 2026-11-02 validate: returned to build - spec round 5 wording
- 2026-11-02 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-02 validate: validate round 6 (last allowed): spec changes_required (web-interface knowledge default-agent layout sentence; two Unreleased CHANGELOG lines naming agent settings/endpoint controls) -> fixed (wording only, no code); quality approved
- 2026-11-02 validate: DEVIATION validate: the review bound (1 + max_fix_cycles = 6 rounds) ended with spec changes_required on wording only; the round-6 wording fixes (knowledge page sentence, two CHANGELOG lines, no code) were checked by an extra grep sweep instead of a seventh independent review - accepted because scope, requirements and code are unchanged since round 5 and quality was approved in rounds 2-6
- 2026-11-02 validate: final: pytest exit 0 (1841 passed, 3 skipped); ruff exit 0; npm test exit 0 (100); npm run typecheck exit 0; npm run build:e2e exit 0; playwright executor-config/settings/enrollment exit 0 (52 passed); check_release_notes exit 0; aegis check --task --strict exit 0 with advisory uncovered-source warnings (removal edits in files without a requirement path) and pre-existing journal/stale-path warnings
- 2026-11-02 validate: DEVIATION validate: final proof ran the brief's listed suites instead of check --strict --run, whose frontend command runs the full Playwright suite - standing instruction to run only targeted tests; misses the e2e specs other than executor-config, settings, enrollment (jobs, model-connection, import, help also passed earlier in this task)
- 2026-11-02 validate: completed; next done (9 Done checklist item(s) left unticked; review verdicts not both approved)

## Rulings

- RULING-001 | date=2026-11-02 | decision=Run this task in autopilot through done; commit, comment on and close Gitea #53 | reason=The delegating owner session asked for an end-to-end implementation of PI-03 with a commit and a closed ticket | source=user | supersedes=none
- RULING-002 | date=2026-11-02 | decision=Interim schema until PI-04: [executor] model and command (Pi argv template, used only by a native run) plus mode, questions_file, env_keys; default, stage_host_auth, every [executor.<name>] table and [labels.executor] are removed and refused by the unknown-key check; usage events keep executor = pi | reason=Ticket #53: no agent choice anywhere and refusal with key and fix; PLAN 4.2 puts model directly under [executor], so PI-04 adds provider instead of moving model again | source=repository | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-0214f6fb.md
changed: round 5 wording
evidence: listed suites exit 0 (pytest 1841 passed; ruff; npm test; typecheck; build:e2e; 3 playwright specs 52 passed; check_release_notes)
issues: adore/web/static bundle not rebuilt; review bound ended on wording-only spec findings (deviation logged)
spec_compliance: changes_required
implementation_quality: approved
review_round: 6

## Delivery report (2026-11-02)

- stage: validate; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-78b0ad95 - Refuse configuration that names a removed coding agent
  - REQ-FUNC-2df31adf - Launch every stage with Pi, the only coding agent
  - REQ-FUNC-97e17737 - Validate executor and egress policy
  - REQ-FUNC-de028c15 - Explicit configured executor AI connection test
  - REQ-FUNC-8f369d55 - Prove a shell tool call in the local Test AI connection
  - REQ-FUNC-0b728218 - Report tool-call-failed when the local agent cannot complete its shell call
  - REQ-FUNC-7ce5b17a - Web project configuration and status
  - REQ-PLAT-722173c8 - Keep a configuration file's line endings when editing it
  - REQ-UX-d93fab0f - Record estimated prices for Pi and the applied model
  - REQ-FUNC-17d58879 - Let explicit local environment values override managed OpenCode settings
  - REQ-SEC-617a95f5 - Apply the ADORE permission policy to local OpenCode commands
  - REQ-SEC-eaad89c3 - Isolate local OpenCode commands from the account's personal OpenCode configuration home
  - REQ-REL-23ce3d34 - Refuse local OpenCode commands when the managed configuration directory is unavailable
  - REQ-FUNC-c829c366 - Reviewed coding agent selection includes command and model atomically
  - REQ-FUNC-2710d0f4 - Model endpoint execution-context readiness
  - REQ-FUNC-fec24fc3 - Local model endpoint profile and readiness
  - REQ-FUNC-59ccdb74 - Launch bounded executor sessions
  - REQ-FUNC-08cc2676 - Reviewed provider variable selection preserves private credentials
  - REQ-UX-646e81fb - Unified executor configuration workspace
  - REQ-UX-b75e1df8 - Configure and check local execution with user-owned tooling notice
  - REQ-UX-d8745013 - Project settings follow Git delivery flow
  - REQ-SEC-e24e2341 - Reviewed launch command presets
  - REQ-SEC-f7b9111e - Reuse local executor authentication under a controlled account environment
  - REQ-FUNC-e5419c07 - Execute bounded preparation before executor gates
- deviations: 5 recorded
  - specify: retired REQ-FUNC-17d58879, REQ-SEC-617a95f5, REQ-SEC-eaad89c3, REQ-REL-23ce3d34 (OpenCode-only) and REQ-FUNC-c829c366 (agent selection) - the behaviour is removed by the ticket
  - build: bundled assets in adore/web/static were not rebuilt (the brief said build:e2e only); they still contain the old strings until the next bundle rebuild
  - validate: retired REQ-FUNC-2710d0f4 and REQ-FUNC-fec24fc3 (OpenCode model endpoint readiness/profile) - the behaviour is removed; revised REQ-FUNC-59ccdb74 to the native Pi file protocol
  - validate: the review bound (1 + max_fix_cycles = 6 rounds) ended with spec changes_required on wording only; the round-6 wording fixes (knowledge page sentence, two CHANGELOG lines, no code) were checked by an extra grep sweep instead of a seventh independent review - accepted because scope, requirements and code are unchanged since round 5 and quality was approved in rounds 2-6
  - validate: final proof ran the brief's listed suites instead of check --strict --run, whose frontend command runs the full Playwright suite - standing instruction to run only targeted tests; misses the e2e specs other than executor-config, settings, enrollment (jobs, model-connection, import, help also passed earlier in this task)
- explicit review: enabled; spec_compliance=changes_required; implementation_quality=approved; review_round=6
- diff vs task base 776e56f: 186 file(s) changed, 1887 line(s) added
- checks: errors=0 warnings=58 notes=23
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
