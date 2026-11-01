# TASK-c6b3c54f - Make Test AI connection prove a shell tool call for local OpenCode

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-FUNC-8f369d55, REQ-FUNC-0b728218, REQ-UX-923bc788, REQ-NFR-ac3e9541, REQ-NFR-f4b171f4
parent:
branch: task/adore-web-interface
base: 1bae6dec93fde53d06e8806e70c071472a0dd19c
opened: 2026-11-01

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

Problem: **Test AI connection** cannot detect an executor that answers but cannot
run tools. Both of its paths ask for a nonce reply and reject any tool call
(OBSERVED: `04_Software/adore/web/model_connection.py:55,166-216,240-246`); its own
help says it "checks model access, not a complete job or tool support" (OBSERVED:
`04_Software/web/src/ModelConnection.tsx` copy). In the 2026-10-31 operator review the
test reported "AI model connected" while every job attempt failed because the local
OpenCode configuration auto-rejected shell calls (STATED: review
`D:/Temp/ADORE_Operator_Review_2026-10-31.md` B3; OBSERVED then). TASK-c9a9e72d fixed
the configuration cause; this task makes the readiness signal catch the class.
Desired outcome: For a native local OpenCode, Pi or Codex profile (STATED: RULING-002, RULING-004), a passing Test AI connection
means the configured agent, under the job's own command and environment, completed a
shell tool call and answered; a rejected or failed tool call gives a distinct failed
result with guidance.
Actors: the administrator who runs Test AI connection (Settings -> Agent and model) and
reads the result there and in Check host prerequisites (OBSERVED: review session).
Primary scenario: admin clicks Test AI connection on a local OpenCode project whose
agent cannot run shell commands -> the test fails with a tool-specific reason instead
of "AI model connected".
Examples: OBSERVED 2026-10-31 under the managed environment: `opencode run -m
openai/gpt-6.1-sol --format json "Run the shell command: git --version ..."` emitted a
`tool_use` event with `tool=bash`, `state.status=completed`; under the personal config
the same request emitted `state.status=error` with "The user rejected permission to use
this specific tool call." (OBSERVED: run io/output.jsonl in the review).
Counterexamples: a container profile keeps today's no-tool test; a Qwen local profile
keeps today's no-tool test (STATED: RULING-004, Qwen support to be removed later).
In scope: local OpenCode, Pi and Codex Test AI connection challenge, its oracle, a new failure
reason, its UI guidance in four locales, help/operator docs.
Out of scope: container probe; Qwen (RULING-004); the NO_STAGE_PROGRESS
stderr evidence (separate task, TASK-c9a9e72d RULING-001); Qwen/Pi/Codex isolation.
Constraints: evidence is a closed record `{executor, model, ready, reason, project_id,
revision, checked_at}` validated by the UI with an exact key set (OBSERVED:
`ModelConnection.tsx` `validModelEvidence`) and the server checks `reason in REASONS`
(OBSERVED: `model_connection.py:35-45,340`); a new reason must be added on both sides.
The local test uses `local_probe` and the configured executor command (OBSERVED:
`model_connection.py:238-246`). The model call may incur provider cost (STATED: UI help).
On Windows OpenCode's shell tool ran PowerShell syntax in the review (OBSERVED:
`Get-Command ...` completed), so the command must work in PowerShell and POSIX shells.
The operator guide states "Only a completed matching response without observed tool
calls reports ready" (OBSERVED: `01_Documentation/Local_Execution.md:166`), enforced
for every local executor by `test_local_model_response_contract_all_executors`
(OBSERVED: `04_Software/tests/test_local_execution.py:1007`); REQ-FUNC-de028c15 itself
only requires "a valid completed challenge response" (OBSERVED). Q3 therefore changes
an established documented contract for local OpenCode. Branch
`task/adore-web-interface`; commit here (STATED earlier).
Success signals: offline tests show ready only with a completed shell tool call whose
output contains the tool nonce plus the exact reply; a rejected/failed tool call yields
the new reason; other executors unchanged; a native run on this host passes.
Evidence: see Examples and Constraints.
Assumptions: INFERRED - `echo <token>` prints the token in PowerShell, cmd and POSIX
shells (premise: standard echo semantics).
Evidence (2026-11-01 live probes, scratch folder, prompt "Run this shell command exactly
once: echo ADORE_TOOL_7f3a. Then reply with exactly: ADORE_OK_9c2e", all exit 0):
OpenCode (managed env) - `tool_use` tool=bash state.status=completed state.output
"ADORE_TOOL_7f3a
", then `text` "ADORE_OK_9c2e", `step_finish` reason=stop; Pi
(`--model openai-codex/gpt-6.1-sol`) - `tool_execution_end` toolName=bash isError=false
result.content[0].text "ADORE_TOOL_7f3a
", final assistant `message_end` stopReason=stop
text "ADORE_OK_9c2e"; Codex (ADORE flags) - `item.completed` type=command_execution
status=completed exit_code=0 aggregated_output "ADORE_TOOL_7f3a
" (PowerShell), an
earlier agent_message "I'll run the command once.", last agent_message "ADORE_OK_9c2e",
`turn.completed`. Pi hangs in -p mode with an open stdin; ADORE launches native gates
with stdin=DEVNULL (OBSERVED: `local_process.py:652`).
Unknowns: event shape of a rejected tool call for Pi and Codex (UNKNOWN; OpenCode's is
`state.status=error`, OBSERVED in the review); Qwen's tool events (not needed, RULING-004).
Decision-blocking questions: answered 2026-11-01 as RULING-001..004 (RULING-004
supersedes RULING-001); none remains open.
Q1. Scope: local OpenCode only in this task; Pi/Codex/Qwen and containers keep the
no-tool test (follow-ups with each executor's isolation task)? (scope)
Q2. Form: extend the existing Test AI connection (same button, one request asking for
the shell call and then the reply) with a new reason `tool-call-failed`, rather than a
new button? (UX)
Q3. Oracle: the shell command is `echo <tool nonce>`; ready requires a completed shell
tool event whose output contains the tool nonce and the exact reply nonce; a tool event
with error/rejection or no tool event gives `tool-call-failed`. This replaces the
documented "without observed tool calls" rule for local OpenCode only.
(behavior, contract change)
Q4. Timeout for the local OpenCode test raised from 45 s to 90 s for the two model
turns? (limit)
Proposed behaviors (P2-P4 accepted; P1 replaced by RULING-002/004 - OpenCode, Pi, Codex):
- P1 (Q1): yes. P2 (Q2): yes, guidance "The agent answered but could not run a shell
  command; check its permission settings" in four locales; help text updated.
- P3 (Q3): as stated. P4 (Q4): 90 s.
Path and reason: full.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | new reason and stricter ready |
| no new interface or data format | no | new reason value in the closed evidence |
| no new dependency | yes | none |
| an existing requirement already covers the behavior | no | REQ-FUNC-de028c15/REQ-UX-b75e1df8 cover a completed challenge, not a tool oracle |
| no security or data-handling change | yes | same environment and cost class |

## Requirement coverage

| Behavior (Frame / ruling) | Requirement | Design |
|---|---|---|
| Local OpenCode/Pi/Codex challenge: echo tool nonce, then reply; ready only with both (RULING-002/004) | REQ-FUNC-8f369d55 (spec) | tool prompt + _native_tool_response |
| Missing, rejected or failed shell call -> tool-call-failed (RULING-002) | REQ-FUNC-0b728218 (spec) | reason order in _native_tool_response |
| UI accepts the reason and shows guidance in four locales (RULING-002) | REQ-UX-923bc788 | modelEvidence.ts |
| Local test bounded at 90 s (RULING-003) | REQ-NFR-ac3e9541 | gate timeout=90 |
| Native test keeps up to 1 MiB of stdout; job gates 64 KiB (RULING-005) | REQ-NFR-f4b171f4 | LocalTarget.output_limit set by local_probe |
| Qwen local and container tests unchanged (RULING-004) | negative cases in REQ-FUNC-8f369d55 verification | qwen branch unchanged |
| Documented "without observed tool calls" rule replaced for local OpenCode/Pi/Codex | docs only (Local_Execution.md, help) | docs |

## Design

**Approach.** Keep `probe_model_connection`'s local branch and its `local_probe` gate
(same command and environment as jobs). For `kind in TOOL_KINDS = {opencode, pi, codex}`
it builds two nonces and the prompt "Connection test. Run this shell command exactly
once: echo <tool nonce>. Then reply with exactly: <reply nonce>" (reply nonce last, as
today), runs the gate with `timeout=90` (REQ-NFR-ac3e9541, applied to every local test)
and decides the reason with a new pure `_native_tool_response(kind, output, tool_nonce,
nonce) -> str` that follows the spec table and order (REQ-FUNC-8f369d55,
REQ-FUNC-0b728218). Qwen keeps the no-tool prompt and `_native_response` (RULING-004);
the container `_RUNNER` is untouched. Rejected: a second button and a second evidence
record (RULING-002).

**Interfaces and data.** `REASONS` gains `tool-call-failed`; the evidence record keeps its
seven keys. Parsing uses `strict_json_loads` per line; a malformed stream is
`invalid-response`. Frontend: new pure module `04_Software/web/src/modelEvidence.ts`
holding the reason set, `validModelEvidence`, the four-locale copy and a
`modelGuidance(reason, locale)` helper; `ModelConnection.tsx` imports them and keeps only
rendering (REQ-UX-923bc788). Copy: new `tool` guidance; the help text and the readiness
"AI model connection" purpose (`ReadinessEvidence.tsx`) stop saying tools are not
checked and say that installed agents also run a shell command.

**Files and test seams.** `adore/web/model_connection.py`;
`04_Software/tests/test_local_execution.py`: the existing
`test_local_model_response_contract_all_executors` and
`test_local_model_challenge_uses_configured_native_cli_and_rejects_incomplete_response`
are updated so OpenCode/Pi/Codex streams carry the recorded shell events; new
parametrized test for tool-call-failed variants and the 90 s gate timeout.
`web/src/modelEvidence.ts`, `web/src/ModelConnection.tsx`,
`web/src/ReadinessEvidence.tsx`; new `web/tests/modelEvidence.test.mjs` (node --test).
Docs: `01_Documentation/Local_Execution.md` (the "without observed tool calls" sentence and
45 s), help topic(s) that describe Test AI connection, CHANGELOG, release notes.
The bundled `adore/web/static` is not rebuilt in this change (repository practice since
f3d37a4: web/src commits leave the bundle to packaging).

**Risks and open decisions.** Cost: two model turns per test (accepted, RULING-002).
A model that refuses or skips the command yields `tool-call-failed` although the
permissions are fine; guidance says to check permissions and the agent. Event formats
were recorded from OpenCode 1.19.4, Pi 1.4.0 and Codex 0.159.3; a later CLI format
change shows as `tool-call-failed`/`invalid-response`, not a false ready.

Diagrams: [diagram_TASK-c6b3c54f.md](diagram_TASK-c6b3c54f.md)

**Persisted evidence (review round 1).** `adore/web/executor_settings.py` validates saved
evidence; its `REASONS` now imports `model_connection.REASONS`, so the API persists
`tool-call-failed` (test: `tests/test_executor_settings.py::test_model_evidence_saves_and_returns_a_tool_call_failure`).

**Output bound (RULING-005, added in validate).** `LocalTarget.output_limit` (default
65536) replaces the hard-coded 64 KiB for non-AEGIS native stdout in `run_files` and
`read_output`; `probe_model_connection` sets it to `LOCAL_OUTPUT_BYTES = 1048576` on its
probe target only, so readiness/endpoint probes and job gates keep 64 KiB
(REQ-NFR-f4b171f4).

**Requirement map.**
- REQ-FUNC-8f369d55: tool prompt + `_native_tool_response` ready rule per executor.
- REQ-FUNC-0b728218: `_native_tool_response` returns `tool-call-failed` before reply checks.
- REQ-UX-923bc788: `modelEvidence.ts` reason set, guidance, copy; component renders it.
- REQ-NFR-ac3e9541: local gate `timeout=90`.
- REQ-NFR-f4b171f4: probe target `output_limit = 1 MiB`.

## Log

- 2026-11-01 frame: journal opened
- 2026-11-01 frame: completed; next specify - scope accepted through RULING-002..004
- 2026-11-01 specify: interaction changed to autopilot by the user for the rest of this task (through commit)
- 2026-11-01 specify: completed; next design
- 2026-11-01 design: completed; next build
- 2026-11-01 build: red: .venv/Scripts/python.exe -m pytest -q tests/test_local_execution.py -k 'model_challenge or model_response_contract' exit 1, 25 failed - local OpenCode/Pi/Codex prompt has no shell nonce, no tool-call oracle, gate timeout 45 (REQ-FUNC-8f369d55, REQ-FUNC-0b728218, REQ-NFR-ac3e9541)
- 2026-11-01 build: green: .venv/Scripts/python.exe -m pytest -q tests/test_local_execution.py -k 'model_challenge or model_response_contract' exit 0, 39 passed (REQ-FUNC-8f369d55, REQ-FUNC-0b728218, REQ-NFR-ac3e9541)
- 2026-11-01 build: red: node --test tests/modelEvidence.test.mjs exit 1 - modelConnection module with tool-call-failed reason and guidance absent (REQ-UX-923bc788)
- 2026-11-01 build: green: node --test tests/modelEvidence.test.mjs exit 0 (2); npm run typecheck exit 0; npm test exit 0 (100 passed) (REQ-UX-923bc788). Design note: the pure module is web/src/modelEvidence.ts, not modelConnection.ts - on case-insensitive Windows './ModelConnection' resolved to modelConnection.ts (tsc TS1261/TS2724)
- 2026-11-01 build: release-notes: updated (merged into the Unreleased fixed/Executors note from TASK-c9a9e72d: 'Local OpenCode uses ADORE's settings; the AI test checks local agents can run a command.' - improved and fixed already hold 10 entries each); python 02_Tools/check_release_notes.py --since 1bae6de exit 0
- 2026-11-01 build: help: updated (executors.md #test-connection in en/fr/de/ro: local temporary folder, shell command check, new guidance); node --test tests/help.test.mjs exit 0
- 2026-11-01 build: docs: Local_Execution.md (tool challenge, Qwen exception, 90 s), Web_Interface.md, Component_Model_Connection.md, CHANGELOG Unreleased Changed entry
- 2026-11-01 build: green: .venv/Scripts/python.exe -m pytest -q tests/test_model_connection.py tests/test_executor_settings.py tests/test_local_execution.py exit 0; ruff exit 0; aegis check errors=0 (warnings: help/release-notes/web src files unowned or known pre-existing items)
- 2026-11-01 build: completed; next validate
- 2026-11-01 validate: manual: ADORE's probe_model_connection run natively on this Windows host (local Job, live models): opencode ready (8 s), codex ready (7 s), pi invalid-response (13 s) (REQ-FUNC-8f369d55)
- 2026-11-01 validate: finding (pre-existing): Pi --mode json emits ~295 KB for the challenge (message_start/message_end/agent_end ~95 KB each, carrying the whole conversation); the native gate keeps the first 64 KiB of stdout (local_execution.py:686, preparation_runner.py:59), so Pi's final assistant message is always cut and the local Pi test cannot pass, with or without tools; container probes keep 1 MiB
- 2026-11-01 validate: returned to build - RULING-005: native Test AI connection keeps up to 1 MiB of stdout so Pi's final reply is retained
- 2026-11-01 build: red: .venv/Scripts/python.exe -m pytest -q tests/test_local_execution.py::test_local_model_test_keeps_large_pi_streams_while_gates_keep_64_kib exit 1 - ~300 KB Pi stream gives runtime-error and stdout_limit 65536 (REQ-NFR-f4b171f4)
- 2026-11-01 build: green: .venv/Scripts/python.exe -m pytest -q tests/test_local_execution.py tests/test_model_connection.py tests/test_executor_settings.py exit 0 (153 passed); ruff exit 0 (REQ-NFR-f4b171f4)
- 2026-11-01 build: manual: ADORE's probe_model_connection run natively on this Windows host with live models after the 1 MiB bound: opencode ready 7 s, pi ready 12 s, codex ready 6 s; opencode with [local].environment OPENCODE_PERMISSION bash deny -> tool-call-failed 11 s (REQ-FUNC-8f369d55, REQ-FUNC-0b728218, REQ-NFR-f4b171f4)
- 2026-11-01 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-01 validate: review round 1 findings: (1) blocker - executor_settings.REASONS (third reason set, executor_settings.py:40-52) rejects tool-call-failed when the API saves evidence -> 503 model_test_failed; untested path; (2) docs still say the test proves no tool capability: Component_Web_API.md:711, Component_Web_Frontend.md:805, knowledge/web-interface.md:790, Component_Executor_Configuration.md:63, Component_Model_Connection.md:32; (3) tests lack shell-ok + wrong/missing reply and incomplete-run cases for Pi/Codex/OpenCode, Codex completed+exit 1, container test not linked; (4) provider error events with exit 0 map to tool-call-failed while the guidance claims 'the agent replied'; (5) REQ-FUNC-8f369d55 has two 'shall'; release note overstates (Qwen excluded); stale comments in model_connection.py docstring and local_execution.py output_limit comment
- 2026-11-01 validate: returned to build - review round 1: shared reason set incl. executor_settings, docs, reply/incomplete tests, guidance wording, requirement wording, release note, comments
- 2026-11-01 build: red: .venv/Scripts/python.exe -m pytest -q tests/test_executor_settings.py::test_model_evidence_saves_and_returns_a_tool_call_failure exit 1 - API returns 503 because executor_settings.REASONS rejects tool-call-failed (REQ-FUNC-0b728218, REQ-UX-923bc788)
- 2026-11-01 build: green: pytest tests/test_local_execution.py tests/test_model_connection.py tests/test_executor_settings.py exit 0 (161 passed); ruff exit 0; npm test exit 0 (100); npm run typecheck exit 0 - executor_settings.REASONS now imports model_connection.REASONS; endpoint persists tool-call-failed; wrong-reply/unfinished/codex shell-exit tests; mutation check: pi/codex/opencode reply-ignoring and codex exit_code-ignoring mutants all caught (REQ-FUNC-8f369d55, REQ-FUNC-0b728218, REQ-UX-923bc788)
- 2026-11-01 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-01 validate: review round 2 findings: spec (1) no test for shell ok + no final reply; (2) release note not limited to local agents; (3) REQ-FUNC-0b728218 lacks the parseable-stream precondition. Quality approved; low notes adopted: realistic intermediate Pi/OpenCode events (catches final[0]), non-shell tool carrying the nonce, Codex early-nonce then different final reply, Pi result:null guard
- 2026-11-01 validate: returned to build - review round 2: no-reply test, realistic streams, other-tool and early-reply cases, Pi result guard, release note wording, REQ-FUNC-0b728218 precondition
- 2026-11-01 build: red: pytest -q tests/test_local_execution.py -k 'model_challenge or ...' exit 1, 9 failed - realistic Pi stream with an intermediate tool_execution_end result:null makes the whole Pi test invalid-response (REQ-FUNC-8f369d55); one OpenCode test sliced the stream at fixed positions
- 2026-11-01 build: green: pytest tests/test_local_execution.py tests/test_model_connection.py tests/test_executor_settings.py exit 0 (169 passed); ruff exit 0; check_release_notes exit 0 - realistic Pi/OpenCode intermediate events, no-reply, other-tool and early-reply cases, Pi result guard; mutants (pi first message, codex any message, non-shell tool per executor) all caught (REQ-FUNC-8f369d55, REQ-FUNC-0b728218)
- 2026-11-01 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-01 validate: review round 3 findings: (1) both - no test asserts invalid-response for an unparseable OpenCode/Pi/Codex stream (mutant mapping parse errors to tool-call-failed survives); (2) Component_Local_Execution.md 64 KiB paragraph lacks the 1 MiB test exception; low: Pi intermediate result:null event is synthetic but labelled recorded; Codex status-only failure untested; extra failed tool before a good shell call untested for OpenCode/Codex; Web_Interface.md and copies still say every click runs in a temporary container
- 2026-11-01 validate: returned to build - review round 3: bad-json reason assertion, codex status-only, extra failed tool, synthetic label, component doc, temporary-folder wording
- 2026-11-01 build: green: pytest tests/test_local_execution.py tests/test_model_connection.py tests/test_executor_settings.py exit 0; ruff exit 0 - bad-json and non-object variants assert invalid-response; codex shell-status and shell-exit; extra failed tool before a good shell call is ready; Pi synthetic event labelled; mutants parse-error->tool-call-failed, non-dict->tool-call-failed, codex status-drop all caught; docs: Component_Local_Execution.md 1 MiB note, temporary-folder wording in Web_Interface.md and three copies (REQ-FUNC-0b728218, REQ-FUNC-8f369d55, REQ-NFR-f4b171f4)
- 2026-11-01 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-01 validate: review round 4: spec approved, quality approved; low notes left open: extra-tool case only places the failed tool before the shell call; codex test docstring mentions only exit code; Web_Interface.md and help still say the image needs Python and the agent (container-only condition, pre-existing)
- 2026-11-01 validate: post-approval notes from Gitea #27: extra-tool-after variant (failed other tool after a good shell call -> ready, all three executors); codex test docstring names status and exit code; 'image must contain Python and the agent' scoped to container projects in Web_Interface.md, three copies and help (4 locales); pytest -k 'model_challenge or codex_shell' exit 0 (48), ruff exit 0, help test exit 0. Candidate changed after round 4, so review round 5 follows
- 2026-11-01 validate: review round 5: spec approved, quality approved (extra-tool-after kills the last-tool-event mutant; 181 focused tests pass). Remaining optional note moved to Gitea #41: Component_Model_Connection.md section 8 'ensure its local image is available' is container-only
- 2026-11-01 validate: DEVIATION validate: final proof ran without the browser part of check --run's frontend command (npm --prefix web run validate: Playwright e2e) - standing user instruction to avoid broad e2e runs; npm test (100) and npm run typecheck cover the changed frontend module, copy and help
- 2026-11-01 validate: final: .venv/Scripts/python.exe -m pytest -q exit 0 (1962 passed, 5 skipped, full offline suite); .venv/Scripts/ruff.exe check adore tests exit 0; npm test exit 0 (100); npm run typecheck exit 0; python 02_Tools/check_release_notes.py --since 1bae6de exit 0; python .agentic/aegis.py check --task TASK-c6b3c54f --strict exit 0 (warnings: unowned help/notes/web src files, pre-existing stale paths, older journal headers, untracked .vera/, uncommitted operator-review web/static rebuild)
- 2026-11-01 validate: completed; next done

## Rulings

- RULING-001 | date=2026-11-01 | decision=Q1: every native local executor (OpenCode, Pi, Codex, Qwen) gets the tool-call challenge; container profiles keep today's no-tool test | reason=user chose all local executors | source=user | supersedes=none
- RULING-002 | date=2026-11-01 | decision=Q2/Q3: extend the existing Test AI connection (same button, one request): the agent runs echo <tool nonce> in its shell tool and then replies with the reply nonce; ready only with a completed shell tool call whose output contains the tool nonce and the exact reply; otherwise reason tool-call-failed with guidance in four locales; this replaces the documented no-tool-call rule for local executors | reason=readiness must catch agents that cannot run tools | source=user | supersedes=none
- RULING-003 | date=2026-11-01 | decision=Q4: the local Test AI connection timeout rises from 45 s to 90 s | reason=two model turns | source=user | supersedes=none
- RULING-004 | date=2026-11-01 | decision=Q1 narrowed: the tool-call challenge covers native local OpenCode, Pi and Codex; Qwen keeps today's no-tool test unchanged, because Qwen support is planned for removal in a later task | reason=user: ignore Qwen, its support will be removed later | source=user | supersedes=RULING-001
- RULING-005 | date=2026-11-01 | decision=Fix in this task: the native Test AI connection retains up to 1 MiB of executor stdout (container probe parity); job gates keep 64 KiB | reason=Pi's challenge stream is ~295 KB, so the 64 KiB bound always cut its final reply | source=user | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-c6b3c54f.md
changed: round-3 fixes: tests, docs
evidence: .venv/Scripts/python.exe -m pytest -q exit 0 (1962 passed, 5 skipped); ruff exit 0; npm test exit 0; typecheck exit 0; aegis check --strict exit 0
issues: Playwright e2e not run - deviation logged; static bundle not rebuilt (Gitea #42)
spec_compliance: approved
implementation_quality: approved
review_round: 5

## Delivery report (2026-11-01)

- stage: validate; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-8f369d55 - Prove a shell tool call in the local Test AI connection
  - REQ-FUNC-0b728218 - Report tool-call-failed when the local agent cannot complete its shell call
  - REQ-UX-923bc788 - Explain a tool-call-failed AI connection result
  - REQ-NFR-ac3e9541 - Bound the local Test AI connection at 90 seconds
  - REQ-NFR-f4b171f4 - Retain up to 1 MiB of native Test AI connection output
- deviations: 1 recorded
  - validate: final proof ran without the browser part of check --run's frontend command (npm --prefix web run validate: Playwright e2e) - standing user instruction to avoid broad e2e runs; npm test (100) and npm run typecheck cover the changed frontend module, copy and help
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=5
- diff vs task base 1bae6de: 41 file(s) changed, 947 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=22 notes=22
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
