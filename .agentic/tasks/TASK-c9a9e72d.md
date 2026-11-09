# TASK-c9a9e72d - Isolate local OpenCode runs from the account's personal configuration

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-SEC-eaad89c3, REQ-SEC-617a95f5, REQ-FUNC-17d58879, REQ-REL-23ce3d34
parent:
branch: task/adore-web-interface
base: f5a0075670679e34fc8a8be6e947db5ab828bb41
opened: 2026-10-31

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

Problem: A native local OpenCode run uses the ADORE account's personal OpenCode
configuration. When that configuration sets `bash`/`edit` to `ask` (globally or on
the default `build` agent), non-interactive `opencode run` auto-rejects every tool
call, the executor exits 0 without progress and the stage fails `NO_STAGE_PROGRESS`
(OBSERVED: 2026-10-31 operator review, `D:/Temp/ADORE_Operator_Review_2026-10-31.md`
B3; run stderr "permission requested: bash (...); auto-rejecting"). Personal agents,
prompts, MCP servers, plugins, `small_model` and `~/.claude` skills also enter ADORE
jobs, so results depend on the operator's desktop setup (OBSERVED: `opencode debug
config` / `debug agent build` with the account's config: build agent carries a
personal description/prompt, mcp=context7, 8 `.claude` skill rules).
Desired outcome: A native local OpenCode run resolves an ADORE-managed configuration
instead of the account's personal one, so tool calls inside the worktree work
non-interactively, personal agents/prompts/MCP/plugins/skills stay out, the
repository's own project configuration still applies, and auth is still reused in
place.
Actors: the operator running ADORE natively (STATED: review B3); the OpenCode
executor, readiness probes and strict verification launched through
`local_environment` (OBSERVED: `04_Software/adore/local_execution.py:226,320,678`).
Primary scenario: OBSERVED in the review on VERA #46: three frame attempts failed in
30 s with 45 output tokens each; the account config `~/.config/opencode/opencode.jsonc`
sets `permission.bash."*" = "ask"`, `edit = "ask"` and the same on `agent.build`.
Examples: OBSERVED with `debug agent build` in an empty folder (scratch probe
`oc_isolation_probe.py`): baseline -> bash ask, edit ask; `OPENCODE_CONFIG_CONTENT`
or `OPENCODE_PERMISSION` alone -> still ask (agent-level personal rules win);
`XDG_CONFIG_HOME`=empty dir -> bash allow, edit allow, default agent, no mcp/plugins;
plus `OPENCODE_PERMISSION` `{"bash":{"*":"allow","git push*":"deny"}}` -> push deny;
plus `OPENCODE_DISABLE_CLAUDE_CODE=1` -> 0 `.claude` skill rules. A real
`opencode run -m openai/gpt-6.1-sol` under that isolation completed a `bash` tool
call (`git --version`) with exit 0 and no stderr.
Counterexamples: A container profile is unchanged (its image has no personal config).
Codex, Pi and Qwen local profiles are not covered (no defect observed for them).
In scope: managed OpenCode configuration isolation for native local profiles whose
default executor is OpenCode; its permission policy; operator documentation.
Out of scope (STATED: RULING-001): a readiness check that exercises a tool call (review B3 second part); stderr
evidence in `NO_STAGE_PROGRESS` (review B3 third part); other executors' personal
configuration; container execution.
Constraints: REQ-SEC-f7b9111e — explicit allowlist, auth reused in place without
copies, forge credentials excluded (STATED). Auth lives under `XDG_DATA_HOME`, which
this change must not move (OBSERVED: `01_Documentation/Local_Execution.md:99`).
`--auto` stays forbidden (OBSERVED: `launcher.py:379`). The effective environment is
pinned (`environment_sha256`), so a new managed variable makes in-flight local runs
drift (OBSERVED: TASK-f2692b34, RULING-002 precedent). A worktree is not a host
sandbox; deny rules are a safety belt, not a boundary (STATED:
`01_Documentation/Local_Execution.md`). Current branch `task/adore-web-interface`;
the user asked to commit here (STATED).
Success signals: offline tests show the managed variables in the local OpenCode
environment, the operator's explicit values winning (RULING-008, superseding RULING-004) and no
change for other executors/containers; a native probe on this host resolves
bash/edit allow and git push deny with the account's personal config present.
Evidence: see Examples; `opencode` 1.19.4 recognizes `OPENCODE_PERMISSION`,
`OPENCODE_DISABLE_CLAUDE_CODE`, `OPENCODE_CONFIG_DIR`, `OPENCODE_PURE` (OBSERVED:
strings of the installed binary); `OPENCODE_CONFIG_DIR`=empty does not remove the
personal config (OBSERVED: probe).
Assumptions: INFERRED — OpenCode may write plugin/package files into its config
directory, so the managed directory must be writable and outside worktree/IO.
Unknowns: effect of a relocated `XDG_CONFIG_HOME` on project tools that read
`$XDG_CONFIG_HOME` (mostly Linux; on Windows most tools use APPDATA) (UNKNOWN);
whether future OpenCode releases keep these variable names (UNKNOWN).
Decision-blocking questions: all answered by the user on 2026-10-31 as
RULING-001..005; none remains open.
Q1. Split: this task covers only the configuration isolation; the tool-call readiness
check and the stderr evidence become two later tasks? (scope)
Q2. Mechanism and effect: a managed empty `XDG_CONFIG_HOME` per profile plus
`OPENCODE_DISABLE_CLAUDE_CODE=1`, applied to every local command of an OpenCode
profile (executor, probes, strict verification). Personal agents, prompts, MCP,
plugins, skills and `small_model` stop applying; the repository's own
`opencode.json`/AGENTS.md still apply. (behavior)
Q3. Permission policy via `OPENCODE_PERMISSION`: bash/edit allow; deny `git push*`,
`tea *`, `gh *`, `glab *`; other permissions keep OpenCode defaults
(`external_directory` stays ask, which non-interactive runs reject). (security)
Q4. Explicit `[local].environment` values for `XDG_CONFIG_HOME` or
`OPENCODE_PERMISSION` override the managed ones (operator opt-out)? (compatibility)
Q5. In-flight local runs drift at upgrade, as in RULING-002 of TASK-f2692b34; accept
and document? (existing state)
Proposed behaviors (P1-P5 accepted as RULING-001..005):
- P1 (Q1): yes, split into three tasks.
- P2 (Q2): as stated; the managed directory is `<state.store_root>/executor-config`
  created by ADORE, empty, outside worktree and run IO.
- P3 (Q3): as stated.
- P4 (Q4): explicit operator values win.
- P5 (Q5): accept; CHANGELOG, release notes and Local_Execution.md say finish or
  cancel local runs before upgrading.
Path and reason: full.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | executor config resolution and permissions change |
| no new interface or data format | no | managed directory and environment entries |
| no new dependency | yes | standard library only |
| an existing requirement already covers the behavior | no | REQ-SEC-f7b9111e covers allowlist/auth, not executor config isolation |
| no security or data-handling change | no | new permission policy for executor tool calls |

## Requirement coverage

| Behavior (Frame / ruling) | Requirement | Design decision |
|---|---|---|
| Managed XDG_CONFIG_HOME + OPENCODE_DISABLE_CLAUDE_CODE for OpenCode local commands; auth stays (RULING-002) | REQ-SEC-eaad89c3 | managed entries in local_environment |
| Permission policy via OPENCODE_PERMISSION (RULING-003) | REQ-SEC-617a95f5 | OPENCODE_PERMISSION_POLICY serialized |
| Explicit [local].environment values win (RULING-008, superseding RULING-004) | REQ-FUNC-17d58879 | entry order; no dir when overridden |
| Managed directory unavailable -> refuse before launch (failure case of RULING-002) | REQ-REL-23ce3d34 | dir check in LocalBackend.__init__ |
| Upgrade drift of in-flight runs (RULING-005) | no new requirement: existing pinned-environment contract (REQ-FUNC-ffb9ed29); disclosed in docs | docs only |
| Counterexample: containers and other executors unchanged | covered by the negative cases in REQ-SEC-eaad89c3 / REQ-SEC-617a95f5 verification | condition on executor.default |

## Design

**Approach.** Extend the single environment builder `local_environment`
(`04_Software/adore/local_execution.py`), which already feeds the pinned policy,
gates, probes and strict verification (TASK-f2692b34 lesson: one environment for
all local commands). When `config.executor.default == "opencode"` it adds three
managed entries after the system allowlist and before `[local].environment`, so
explicit operator values replace them by dict order, and on Windows a differently
cased explicit name in `MANAGED_OPENCODE_ENV_KEYS` replaces the managed entry
(REQ-FUNC-17d58879, RULING-008 superseding RULING-004):
`XDG_CONFIG_HOME=<resolved state root>/executor-config`,
`OPENCODE_DISABLE_CLAUDE_CODE=1` (REQ-SEC-eaad89c3) and `OPENCODE_PERMISSION` =
compact JSON of the policy (REQ-SEC-617a95f5). The managed values also replace an
inherited process `XDG_CONFIG_HOME` (personal), because only `[local].environment`
counts as an explicit operator choice. Rejected: `OPENCODE_CONFIG_CONTENT` /
`OPENCODE_PERMISSION` alone (probe: agent-level personal rules still win) and
`OPENCODE_CONFIG_DIR` (adds a directory, keeps the personal one).

**Interfaces and data.** New module constants `OPENCODE_PERMISSION_POLICY` (dict)
and helper `managed_opencode_config(config) -> Path | None` (path when the profile's
default executor is OpenCode, else None). `local_environment` stays pure: it only
computes the path, because `local_policy` also serves `config plan`
(`preparation.py:395`), which must not write. `LocalBackend.__init__` - the
preparation step every real command and probe passes (`orchestrator.py:199`,
`local_probe`) - creates the directory (`mkdir(parents=True, exist_ok=True)`) when
the environment's `XDG_CONFIG_HOME` is the managed path, and raises
`LocalExecutionError("managed executor configuration directory is unavailable")`
on OSError or a non-directory (REQ-REL-23ce3d34). With an explicit operator
`XDG_CONFIG_HOME` the managed directory is neither created nor checked
(REQ-FUNC-17d58879). Probes use their temporary state root, so they get a fresh
empty managed directory, which is equivalent.

**Files and test seams.** `local_execution.py` (constants, helper, builder, backend
init); `04_Software/tests/test_local_execution.py`: environment tests through
`local_fixture` (OpenCode), the same with `config.executor.default = "codex"` (no
managed entries), explicit-override test, and a backend-init test with a regular
file at `<state>/executor-config` asserting `LocalExecutionError` and no controller
call. Native evidence: `opencode debug agent build` under the built environment.
Docs: `01_Documentation/Local_Execution.md`, `05_SoftwareDocu/Component_Local_Execution.md`,
CHANGELOG, release notes; help only if a topic describes local OpenCode config.

**Risks and open decisions.** Security: deny rules are a safety belt (RULING-003).
Compatibility: environment digest changes, in-flight local runs drift (RULING-005).
Project tools that read `$XDG_CONFIG_HOME` see the managed directory (Frame unknown,
mainly Linux); the operator can opt out (REQ-FUNC-17d58879). Future OpenCode
releases may rename these variables (Frame unknown).

Diagrams: [diagram_TASK-c9a9e72d.md](diagram_TASK-c9a9e72d.md)

**Requirement map.**
- REQ-SEC-eaad89c3: managed XDG_CONFIG_HOME + OPENCODE_DISABLE_CLAUDE_CODE in `local_environment`.
- REQ-SEC-617a95f5: `OPENCODE_PERMISSION_POLICY` serialized into `OPENCODE_PERMISSION`.
- REQ-FUNC-17d58879: entry order (managed before `[local].environment`); on Windows the
  `MANAGED_OPENCODE_ENV_KEYS` match case-insensitively; no dir when overridden.
- REQ-REL-23ce3d34: directory creation/check in `LocalBackend.__init__`, before any launch.

## Log

- 2026-10-31 frame: journal opened
- 2026-10-31 frame: completed; next specify - scope accepted
- 2026-10-31 specify: interaction changed to autopilot by the user for the rest of this task (through commit)
- 2026-10-31 specify: completed; next design
- 2026-10-31 design: completed; next build
- 2026-10-31 build: red: .venv/Scripts/python.exe -m pytest -q tests/test_local_execution.py::test_local_opencode_environment_isolates_personal_configuration exit 1 - XDG_CONFIG_HOME stays personal, no OPENCODE_DISABLE_CLAUDE_CODE (REQ-SEC-eaad89c3)
- 2026-10-31 build: red: .venv/Scripts/python.exe -m pytest -q tests/test_local_execution.py::test_local_opencode_environment_applies_permission_policy exit 1 - OPENCODE_PERMISSION absent (REQ-SEC-617a95f5)
- 2026-10-31 build: red: .venv/Scripts/python.exe -m pytest -q tests/test_local_execution.py::test_local_environment_values_override_managed_opencode_settings exit 1 - managed OPENCODE_DISABLE_CLAUDE_CODE absent beside explicit values (REQ-FUNC-17d58879)
- 2026-10-31 build: red: .venv/Scripts/python.exe -m pytest -q tests/test_local_execution.py::test_local_backend_refuses_unavailable_managed_opencode_directory exit 1 - managed executor-config directory never created or checked (REQ-REL-23ce3d34)
- 2026-10-31 build: green: .venv/Scripts/python.exe -m pytest -q tests/test_local_execution.py exit 0, 71 passed (REQ-SEC-eaad89c3, REQ-SEC-617a95f5, REQ-FUNC-17d58879, REQ-REL-23ce3d34); two existing conductor/cleanup tests now rebuild LocalBackend after moving state.store_root, because the managed path is part of the pinned environment
- 2026-10-31 build: manual: on this Windows host with the personal opencode.jsonc present, opencode debug agent build under the ADORE process env resolved bash/edit/git push/tea = ask, personal agent, 8 .claude skill rules; under local_environment it resolved bash allow, edit allow, git push deny, tea deny, default agent, 0 skill rules (REQ-SEC-eaad89c3, REQ-SEC-617a95f5)
- 2026-10-31 build: scope note: local Test AI connection runs through local_probe, so it now resolves the same managed config; its no-tool-call oracle is unchanged (tool-call readiness stays for the later task, RULING-001)
- 2026-10-31 build: release-notes: added (fixed/Executors: local OpenCode jobs use ADORE's own agent settings); finish-or-cancel upgrade advice is already in the Unreleased Executors note from TASK-f2692b34 (RULING-005); python 02_Tools/check_release_notes.py --since f5a0075 exit 0; Unreleased fixed entries now 10 (the limit)
- 2026-10-31 build: help: updated (executors.md Where jobs run: new Agent settings row in en/fr/de/ro); node --test tests/help.test.mjs exit 0, 10 passed
- 2026-10-31 build: docs: Local_Execution.md managed OpenCode configuration paragraph (policy, opt-out, XDG side effect, upgrade note); Component_Local_Execution.md; CHANGELOG Unreleased Fixed entry
- 2026-10-31 build: check: errors=0 warnings=21; uncovered-source for help executors.md (4 locales) and release_notes.toml - help/notes files are not owned by requirements; stale-paths REQ-FUNC-5de75419 names old web/static bundle files - pre-existing, unrelated; journal-header warnings in older journals, untracked .vera/ and the uncommitted operator-review web/static rebuild are outside this task
- 2026-10-31 build: completed; next validate
- 2026-10-31 validate: REQ-REL-23ce3d34 prose made precise - the check applies while the managed directory is the effective XDG_CONFIG_HOME (design decision under REQ-FUNC-17d58879; no contract weakened, requirement is new in this task)
- 2026-10-31 validate: review round 1 findings: (1) OpenCode still reads <home>/.opencode (config/agents/plugins) and <home>/.agents/skills, so isolation claims overstate and a personal ~/.opencode build-agent ask rule would bring NO_STAGE_PROGRESS back; (2) personal providers/model overrides (e.g. lm-studio) stop applying, undocumented, not covered by RULING-002; (3) OPENCODE_DISABLE_CLAUDE_CODE also drops the repository CLAUDE.md fallback and repository .claude/skills; (4) help Container cell 'Only what the image provides' ignores container.runtime_env OPENCODE_CONFIG_CONTENT; (5) REQ-SEC-617a95f5 verification claims a container assertion no test makes; (6) REQ-FUNC-17d58879 also lets OPENCODE_DISABLE_CLAUDE_CODE win, beyond RULING-004's two names, untested; (7) REQ-REL-23ce3d34 says 'command' while the check runs once per LocalBackend; (8) on Windows a lowercase explicit name duplicates the managed key; (9) refusal test lacks match= and has a vacuous controller assertion
- 2026-10-31 validate: probe: OPENCODE_DISABLE_EXTERNAL_SKILLS=1 removes ~/.agents skills; OPENCODE_TEST_HOME=<managed> moves OpenCode home (no ~/.opencode lookup) and keeps auth under XDG_DATA_HOME, but is an undocumented test-named variable and alone does not stop ~/.agents skills
- 2026-11-01 validate: returned to build - review round 1: narrow isolation claims (RULING-006..008), fix help container cell, REQ-SEC-617a95f5 verification, REQ-REL-23ce3d34 wording, Windows case-insensitive explicit override, refusal test precision, test third override
- 2026-11-01 build: red: .venv/Scripts/python.exe -m pytest -q tests/test_local_execution.py::test_local_environment_values_override_managed_opencode_settings exit 1 - Windows keeps managed XDG_CONFIG_HOME beside explicit lowercase xdg_config_home (REQ-FUNC-17d58879, review finding 8)
- 2026-11-01 build: correction to RULING-007 wording: the local endpoint setting serves container projects only (help executors.md#local-endpoint); docs name OPENCODE_CONFIG_CONTENT in [local].environment and an explicit XDG_CONFIG_HOME as the way out for personal providers
- 2026-11-01 build: green: .venv/Scripts/python.exe -m pytest -q tests/test_local_execution.py exit 0 (71 passed); ruff exit 0; node --test tests/help.test.mjs exit 0 - round-1 fixes: Windows case-insensitive explicit override, third override tested, refusal test match=, requirement wording (eaad89c3 scope, 617a95f5 container inspection, 17d58879 case, 23ce3d34 backend), docs/help/CHANGELOG/release note narrowed per RULING-006..008 (REQ-SEC-eaad89c3, REQ-SEC-617a95f5, REQ-FUNC-17d58879, REQ-REL-23ce3d34)
- 2026-11-01 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-01 validate: review round 2 findings: spec (1) Windows case filter applied to every name and executor beyond RULING-008 - limit to MANAGED_OPENCODE_ENV_KEYS on OpenCode profiles; (2) REQ-SEC-eaad89c3 title still claimed full isolation. Quality approved; low notes: help row omitted ~/.agents/skills; CODEX_HOME/PI_CODING_AGENT_DIR case note resolved by limiting the filter; pre-existing: config.py:1142 validates inline OPENCODE_CONFIG_CONTENT with exact-case lookup, so a lowercase opencode_config_content with a literal key passes validation on Windows (follow-up, outside this task)
- 2026-11-01 validate: returned to build - review round 2: limit Windows case filter to managed OpenCode names, fix REQ-SEC-eaad89c3 title, help names ~/.agents/skills
- 2026-11-01 build: green: .venv/Scripts/python.exe -m pytest -q tests/test_local_execution.py exit 0 (71 passed); ruff exit 0; node --test tests/help.test.mjs exit 0 - Windows case filter limited to MANAGED_OPENCODE_ENV_KEYS, LANG keeps exact-name behavior (REQ-FUNC-17d58879)
- 2026-11-01 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-01 validate: post-approval hardening from round-3 quality notes: override test now asserts Linux keeps managed XDG_CONFIG_HOME beside lowercase xdg_config_home and a codex profile keeps the inherited XDG_CONFIG_HOME; mutation check removing either guard of the Windows filter now fails the test (both caught); comment says configuration home; pytest tests/test_local_execution.py exit 0 (71), ruff exit 0. Candidate changed after round 3, so review round 4 follows
- 2026-11-01 validate: DEVIATION validate: final proof ran without check --run's frontend command (npm --prefix web run validate: typecheck, build, Playwright e2e) - standing user instruction to avoid broad e2e runs; the only web change is help Markdown, covered by node --test tests/help.test.mjs
- 2026-11-01 validate: final: .venv/Scripts/python.exe -m pytest -q exit 0 (1912 passed, 5 skipped, full offline suite); .venv/Scripts/ruff.exe check adore tests exit 0; node --test tests/help.test.mjs exit 0 (10); python 02_Tools/check_release_notes.py --since f5a0075 exit 0; python .agentic/aegis.py check --task TASK-c9a9e72d --strict exit 0 (warnings: help/release-notes files unowned by requirements, pre-existing stale paths in REQ-FUNC-5de75419, older journal headers, untracked .vera/, uncommitted operator-review web/static rebuild)
- 2026-11-01 validate: completed; next done

## Rulings

- RULING-001 | date=2026-10-31 | decision=Q1: this task covers only the local OpenCode configuration isolation; the tool-call readiness check and stderr evidence in NO_STAGE_PROGRESS become two later tasks | reason=one fix per task | source=user | supersedes=none
- RULING-002 | date=2026-10-31 | decision=Q2: for native local profiles whose default executor is OpenCode, ADORE sets an empty managed XDG_CONFIG_HOME under <state.store_root>/executor-config and OPENCODE_DISABLE_CLAUDE_CODE=1 for every local command (executor, probes, strict verification); personal agents, prompts, MCP, plugins, skills and small_model stop applying; repository opencode.json/AGENTS.md and XDG_DATA_HOME auth stay | reason=probes showed inline overrides cannot beat agent-level personal rules; relocation does | source=user | supersedes=none
- RULING-003 | date=2026-10-31 | decision=Q3: OPENCODE_PERMISSION allows bash and edit and denies git push*, tea *, gh *, glab *; other permissions keep OpenCode defaults (external_directory ask, rejected non-interactively); deny rules are a safety belt, not a boundary | reason=local account holds forge credentials | source=user | supersedes=none
- RULING-004 | date=2026-10-31 | decision=Q4: explicit [local].environment values for XDG_CONFIG_HOME or OPENCODE_PERMISSION override the managed ones | reason=operator opt-out | source=user | supersedes=none
- RULING-005 | date=2026-10-31 | decision=Q5: local runs in flight at upgrade are treated as drifted; CHANGELOG, release notes and Local_Execution.md tell operators to finish or cancel local runs before upgrading | reason=same contract as TASK-f2692b34 RULING-002 | source=user | supersedes=none
- RULING-006 | date=2026-11-01 | decision=D1: keep the managed XDG_CONFIG_HOME mechanism; OpenCode's home-level <home>/.opencode (config, agents, plugins) and <home>/.agents/skills still apply and are documented as known gaps; requirement and docs claim isolation only for the configuration home | reason=user chose documentation over OPENCODE_TEST_HOME or a refusal check | source=user | supersedes=none
- RULING-007 | date=2026-11-01 | decision=D2: personal OpenCode providers and model overrides from the configuration home no longer apply; docs and CHANGELOG say so and name the way out: OPENCODE_CONFIG_CONTENT in [local].environment, the local endpoint setting, or an explicit XDG_CONFIG_HOME | reason=no copying from the personal configuration | source=user | supersedes=none
- RULING-008 | date=2026-11-01 | decision=D3/D4: accept that OPENCODE_DISABLE_CLAUDE_CODE also drops the repository CLAUDE.md fallback and repository .claude/skills (documented); explicit [local].environment values win for XDG_CONFIG_HOME, OPENCODE_PERMISSION and OPENCODE_DISABLE_CLAUDE_CODE, with a test | reason=AGENTS.md carries AEGIS instructions; one override rule for all managed names | source=user | supersedes=RULING-004


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-c9a9e72d.md
changed: round-2 fixes: MANAGED_OPENCODE_ENV_KEYS filter, test, REQ-SEC-eaad89c3 title, requirement dates, docs/help wording
evidence: .venv/Scripts/python.exe -m pytest -q exit 0 (1912 passed, 5 skipped); ruff exit 0; help test exit 0; aegis check --strict exit 0
issues: frontend validate (Playwright) not run - deviation logged; follow-ups: Qwen/Pi/Codex personal-config isolation, config.py:1142 exact-case OPENCODE_CONFIG_CONTENT validation, tool-call readiness check, NO_STAGE_PROGRESS stderr evidence
spec_compliance: approved
implementation_quality: approved
review_round: 4

## Delivery report (2026-11-01)

- stage: validate; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-SEC-eaad89c3 - Isolate local OpenCode commands from the account's personal OpenCode configuration home
  - REQ-SEC-617a95f5 - Apply the ADORE permission policy to local OpenCode commands
  - REQ-FUNC-17d58879 - Let explicit local environment values override managed OpenCode settings
  - REQ-REL-23ce3d34 - Refuse local OpenCode commands when the managed configuration directory is unavailable
- deviations: 1 recorded
  - validate: final proof ran without check --run's frontend command (npm --prefix web run validate: typecheck, build, Playwright e2e) - standing user instruction to avoid broad e2e runs; the only web change is help Markdown, covered by node --test tests/help.test.mjs
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=4
- diff vs task base f5a0075: 26 file(s) changed, 639 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=21 notes=22
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
