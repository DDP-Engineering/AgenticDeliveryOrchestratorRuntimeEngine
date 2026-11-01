# TASK-a68cdaa7 - Include the executor stderr tail in NO_STAGE_PROGRESS evidence

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-FUNC-93bd3c8e
parent:
branch: task/adore-web-interface
base: d5a5946f3aed60052e94664ddc3680861a31da39
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

Problem: When an executor exits 0 but AEGIS did not advance, the stage failure
`NO_STAGE_PROGRESS` records only "executor exited zero but AEGIS remained at <stage>"
(OBSERVED: `04_Software/adore/orchestrator.py:1080-1084`); the gate's stderr is
discarded, although the GateRun carries it (OBSERVED: `adore/executor/base.py:76`).
In the 2026-10-31 operator review the real cause was one stderr line, "permission
requested: bash (...); auto-rejecting", visible only in `io/stderr.log` on the server
(STATED: Gitea #28; review report B3).
Desired outcome: `NO_STAGE_PROGRESS` evidence (journal `stage-failed`, the ticket
incident comment, the terminal-failure comment and the run outcome shown in Job
details) contains the last lines of the gate's stderr, redacted and bounded, after
the existing sentence.
Actors: the operator reading the ticket comment or Job details (STATED: #28).
Primary scenario: an executor whose tool calls are auto-rejected exits 0; the
incident comment shows the explanatory sentence and the stderr line naming the
rejection.
Examples: OBSERVED review stderr: "\x1b[93m\x1b[1m! \x1b[0mpermission requested:
bash (git status --short, ...); auto-rejecting" (contains ANSI colour codes).
Counterexamples: empty stderr keeps today's evidence unchanged. EXECUTOR_EXIT and
EXECUTOR_TIMEOUT already use stderr (OBSERVED: `orchestrator.py:1036`) and are unchanged.
In scope: NO_STAGE_PROGRESS evidence text; tests; CHANGELOG, release notes, docs/help
that describe incident evidence.
Out of scope: the prompt context for the next attempt; other failure codes; the
token-usage truncation (#34).
Constraints: `_sanitize` redacts common credential forms and keeps the LAST
`_MAX_EVIDENCE` (6000) characters (OBSERVED: `orchestrator.py:113-137`), so the tail
must be bounded before the sentence is combined or the sentence can be cut. Local
gate stderr is already redacted for known account/provider secrets by
`LocalTarget.read_output` (OBSERVED: TASK-c6b3c54f reading); container stderr gets
only `_sanitize`'s patterns (INFERRED from the same code path). Branch
`task/adore-web-interface`; commit here (STATED earlier).
Success signals: offline tests: sentence plus redacted tail in journal and incident;
empty stderr unchanged; huge stderr bounded with the sentence intact; ANSI removed
(RULING-002).
Evidence: see Problem and Constraints.
Assumptions: none beyond the above.
Unknowns: none blocking.
Decision-blocking questions: answered 2026-11-01 as RULING-001..003; none open.
Q1. Bound of the tail: last 20 lines and at most 2000 characters? (limit)
Q2. Strip ANSI escape sequences from the tail? (format)
Q3. Autopilot through commit and close Gitea #28 when done? (interaction)
Proposed behaviors (P1-P3 accepted as RULING-001..003):
- P1: 20 lines / 2000 characters, combined as "<sentence>\nExecutor stderr (last
  lines):\n<tail>" before `_sanitize`.
- P2: yes, strip ANSI CSI/OSC sequences.
- P3: yes.
Path and reason: full.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | incident/journal evidence text changes |
| no new interface or data format | yes | same evidence field |
| no new dependency | yes | standard library |
| an existing requirement already covers the behavior | no | REQ-FUNC-83133b5e covers attempt accounting, not evidence content |
| no security or data-handling change | no | more process output reaches the forge (redacted) |

## Requirement coverage

| Behavior (Frame / ruling) | Requirement | Design |
|---|---|---|
| Sentence + last 20 lines / 2000 chars of stderr, ANSI removed, redacted (RULING-001/002) | REQ-FUNC-93bd3c8e | skipped: one function in orchestrator.py |
| Blank stderr keeps today's evidence; long stderr keeps the sentence | REQ-FUNC-93bd3c8e (verification boundaries) | same |


## Design

Skipped: the change stays in one function path of `04_Software/adore/orchestrator.py`
with no new interface, data format or dependency. A private helper builds the bounded,
ANSI-free tail from `GateRun.stderr` and is appended to the existing sentence before
`_stage_failure` (which applies `_sanitize`); tests attach in
`04_Software/tests/test_orchestrator.py` through `make_engine` and the fake executor.

## Log

- 2026-11-01 frame: journal opened
- 2026-11-01 frame: interaction set to autopilot by the user (RULING-003)
- 2026-11-01 frame: completed; next specify - scope accepted
- 2026-11-01 specify: completed; next design
- 2026-11-01 design: skipped; next build - one function path in orchestrator.py, no new interface, format or dependency
- 2026-11-01 build: red: .venv/Scripts/python.exe -m pytest -q tests/test_orchestrator.py -k no_stage_progress_evidence exit 1, 3 failed (blank passes) - stderr absent from NO_STAGE_PROGRESS evidence (REQ-FUNC-93bd3c8e)
- 2026-11-01 build: green: .venv/Scripts/python.exe -m pytest -q tests/test_orchestrator.py exit 0 (137 passed); ruff exit 0; manual: _stderr_tail strips CSI colour and OSC title sequences from an OpenCode-style permission line (REQ-FUNC-93bd3c8e)
- 2026-11-01 build: release-notes: updated (merged into the Unreleased fixed/Messages note: 'a stalled agent shows its last error lines'; fixed holds 10 entries); check_release_notes exit 0
- 2026-11-01 build: help: updated (jobs.md incident paragraph in en/fr/de/ro); node --test tests/help.test.mjs exit 0
- 2026-11-01 build: docs: Operations_Guide.md error-code table gains NO_STAGE_PROGRESS; CHANGELOG Unreleased Fixed entry
- 2026-11-01 build: completed; next validate
- 2026-11-01 validate: review round 1 findings: (1) security - the 2000-char/20-line cut happens before redaction, so a cut inside 'token=' or a dropped 'token:' line leaks the value (reproduced); (2) run.outcome (Job details) keeps the LAST 2000 chars of 'stage X failed on attempt n/N: <evidence>' and loses the sentence when the tail is long; (3) tests never reach the 2000-char bound, OSC stripping or outcome/terminal comment; (4) ANSI regex misses ESC ( B, ESC 7/8, ESC =, DCS payloads
- 2026-11-01 validate: returned to build - review round 1: redact before cutting, keep the sentence in run.outcome, stronger tests, broader escape stripping
- 2026-11-01 build: red: pytest -q tests/test_orchestrator.py -k no_stage_progress_evidence exit 1, 4 failed - OSC/ESC ( B residue, token value leaks after the char cut and the line cut, run.outcome loses the sentence for long tails (REQ-FUNC-93bd3c8e)
- 2026-11-01 build: green: pytest -q tests/test_orchestrator.py tests/test_checkpoint_handoff.py exit 0, 179 passed; ruff check adore tests exit 0 (REQ-FUNC-93bd3c8e)
- 2026-11-01 build: mutation: 7 mutants (no char bound, no line bound, redact after cut, outcome keeps tail only, no generic ESC form, no OSC form, no ANSI strip) all caught by test_no_stage_progress_evidence_carries_the_stderr_tail
- 2026-11-01 build: scope: _terminal_failure now bounds run.outcome with _head_and_tail, so every failure code whose sanitized evidence exceeds 2000 characters keeps its first line in Job details; shorter evidence is unchanged
- 2026-11-01 build: docs: REQ-FUNC-93bd3c8e prose and verification, Component_Orchestrator.md, knowledge/orchestrator.md and CHANGELOG synced to redact-before-cut and the outcome first line; check_release_notes --since d5a5946 ok; node --test tests/help.test.mjs 10 passed
- 2026-11-01 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-01 validate: review round 2 findings: round-1 findings confirmed resolved; (1) run.outcome is cut to the last 6000 chars by _sanitize before _head_and_tail, so EXECUTOR_EXIT/TIMEOUT evidence over ~6000 chars still loses the sentence while CHANGELOG and component doc claim every code keeps it; (2) unterminated OSC/DCS payload classes cross newlines and swallow the decisive last lines; (3) _stderr_tail redacts before removing NUL, so tok<NUL>en: escapes redaction and the line cut leaks the value; (4) tests miss the permission line in the terminal comment and the run.outcome length bound; (5) the all-codes outcome change is out of the Frame scope and must be a DEVIATION
- 2026-11-01 validate: returned to build - review round 2: outcome head before the 6000 cut, newline-bounded OSC/DCS, NUL before redaction, terminal/outcome-bound assertions, record the all-codes outcome DEVIATION
- 2026-11-01 build: round-2 fixes - _sanitize(limit=None) keeps the whole redacted text; _terminal_failure bounds run.outcome with _head_and_tail over _sanitize(evidence, None); OSC/DCS payload classes exclude newline; _stderr_tail removes NUL before the ANSI strip and redacts through _sanitize(text, None); tests: osc-open and token-nul cases, permission line in the terminal comment, outcome length bound, new test_terminal_outcome_keeps_the_failure_sentence_of_long_evidence (EXECUTOR_EXIT, 200x100-char stderr)
- 2026-11-01 build: red: written after the code this round, so red is shown by reverting each round-2 fix: outcome after 6000 cut, outcome unbounded, OSC crosses newline, DCS crosses newline, both NUL strips removed - each fails the targeted tests (1-2 failed); round-1 mutants (redact after cut, outcome keeps tail only, no char/line bound, no generic ESC, no OSC, no ANSI strip) still caught
- 2026-11-01 build: green: pytest -q tests/test_orchestrator.py tests/test_checkpoint_handoff.py exit 0, 182 passed; ruff check adore tests exit 0 (REQ-FUNC-93bd3c8e)
- 2026-11-01 build: DEVIATION build: run.outcome now keeps the evidence's first line for every failure code over 2000 characters, not only NO_STAGE_PROGRESS (Frame excluded other codes) - kept because the bound lives in the shared _terminal_failure and a per-code branch would be worse; cost: Job details text changes for long EXECUTOR_EXIT/TIMEOUT and other failures, covered by test_terminal_outcome_keeps_the_failure_sentence_of_long_evidence and stated in CHANGELOG
- 2026-11-01 build: accepted non-blocking review notes: _head_and_tail is only called with limit 2000 (no small-limit guard); C1 8-bit CSI not stripped; _REDACTIONS gaps (Bearer second word, JSON "token": values, quoted values with spaces) are pre-existing and shared with EXECUTOR_EXIT evidence - follow-up outside this task
- 2026-11-01 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-01 validate: review round 3 approved by both roles (targeted 11 passed). Accepted non-blocking: a lone or malformed ESC directly before a key (ESC token=X, ESC [token=X) loses the key's first letter to the escape strip and escapes redaction - no known accidental source, real SGR output ends with its final byte before the key; an OSC split by a newline can leave a stray BEL; the huge case's 0010 assertion is redundant with the char bound
- 2026-11-01 validate: final: .venv/Scripts/python.exe -m pytest -q exit 0 (1973 passed, 5 skipped, full offline suite; 1 third-party StarletteDeprecationWarning from fastapi.testclient); .venv/Scripts/ruff.exe check adore tests exit 0; node --test tests/help.test.mjs exit 0 (10); python 02_Tools/check_release_notes.py --since d5a5946 exit 0; python .agentic/aegis.py check --task TASK-a68cdaa7 --strict exit 0 (errors=0, warnings=14: older journals' header records, a stale path in REQ-FUNC-5de75419, release_notes.toml and help jobs.md not owned by requirements - all pre-existing kinds)
- 2026-11-01 validate: DEVIATION validate: check --strict --run not run as one command - its frontend entry (npm run validate) includes the Playwright e2e suite, which the user defers to the end of all refinements; covered by the full offline pytest suite, ruff, help test and the catalog-only strict check; web change is help text only (no TS/TSX)
- 2026-11-01 validate: diff reviewed hunk by hunk (3 explicit review rounds); knowledge/orchestrator.md current; context/project.md and environment.md make no claim about failure evidence - unchanged; REQ-FUNC-93bd3c8e re-read: active, prose and verification match the built behaviour, path and linked test current; no Manual/Inspection verification on this requirement; remaining check warnings explained in the final line
- 2026-11-01 validate: completed; next done

## Rulings

- RULING-001 | date=2026-11-01 | decision=Q1: the stderr tail is the last 20 lines, at most 2000 characters, combined before _sanitize | reason=the decisive line fits; comments stay short | source=user | supersedes=none
- RULING-002 | date=2026-11-01 | decision=Q2: ANSI escape sequences are removed from the stderr tail | reason=colour codes are noise in forge comments and Job details | source=user | supersedes=none
- RULING-003 | date=2026-11-01 | decision=Q3: autopilot through commit; then comment and close Gitea #28 and tick it in epic #48 | reason=user request | source=user | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-a68cdaa7.md
changed: orchestrator.py _stderr_tail + NO_STAGE_PROGRESS evidence; test; docs/help/CHANGELOG/release note; component doc; knowledge
evidence: pytest -q exit 0 (1973 passed, 5 skipped); ruff exit 0; check --strict exit 0
issues: none
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-11-01)

- stage: validate; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-93bd3c8e - Show the executor stderr tail in NO_STAGE_PROGRESS evidence
- deviations: 2 recorded
  - build: run.outcome now keeps the evidence's first line for every failure code over 2000 characters, not only NO_STAGE_PROGRESS (Frame excluded other codes) - kept because the bound lives in the shared _terminal_failure and a per-code branch would be worse; cost: Job details text changes for long EXECUTOR_EXIT/TIMEOUT and other failures, covered by test_terminal_outcome_keeps_the_failure_sentence_of_long_evidence and stated in CHANGELOG
  - validate: check --strict --run not run as one command - its frontend entry (npm run validate) includes the Playwright e2e suite, which the user defers to the end of all refinements; covered by the full offline pytest suite, ruff, help test and the catalog-only strict check; web change is help text only (no TS/TSX)
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base d5a5946: 13 file(s) changed, 320 line(s) added
- checks: errors=0 warnings=14 notes=22
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
