<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Executor Launcher (`ador/executor/`)

> Component documentation per `component_documentation_template.md`.
> Sources: `04_Software/ador/executor/{base,launcher}.py` - file versions 0.1.1.
> Design: Orchestrator_Design_And_Decisions.md sections 6 and 7a;
> Prerequisites_Check_Report.md sections 5-6 and 12-13.

## 1. Purpose

Launch the configured executor (opencode in v1; pi/codex behind the same
factory later) headless inside the run's container, one gate per launch, and
read every result back deterministically. All code reasoning lives in the
executor; the launcher only composes commands and collects outcomes.

## 2. Responsibilities

- `Executor` (ABC in `base.py`) + `ExecTarget` protocol (the container exec
  seam, bound by the orchestrator to the run's container) + `GateRun` (the
  conductor's decision inputs: exit code, questions, session id, raw output).
- `OpencodeExecutor` (`launcher.py`): template substitution, the file-based
  gate protocol (section 3), session continuation (`--session <id>`),
  questions-file detection, and the `--auto` refusal.
- `build_executor(kind, command_template, model, questions_file)` - factory
  from `[executor]` config.

Explicitly not owned: *which* gate to run and what to do with the outcome
(orchestrator, design 7a), container lifecycle (isolation), posting anything
to the Git platform (forge; the executor never touches the remote).

## 3. Implementation Overview

**The file-based gate protocol** - every byte crosses process boundaries in
files, never argv or live stdout, because of two verified findings:
`wsl.exe` splits argv elements containing spaces (prereq 12), and opencode
buffers stdout so live streaming looks hung (prereq 9).

1. Delete a stale questions file from the worktree - its presence after the
   gate must mean it was written by THIS gate.
2. Render the command from the `[executor.<name>]` template: `{prompt}` ->
   shell-quoted prompt text, `{model}` -> quoted model, `{worktree}` ->
   `/ador/work` (the container-side mount). A continuing session appends
   `--session <id>`.
3. Write `gate.sh` (LF endings; Windows CRLF would break `sh`) into the
   run's io dir: `cd /ador/work`, then the command with stdout redirected to
   `output.jsonl` and stderr to `stderr.log`, both in `/ador/io`. No `exec`
   prefix - templates may be compound commands.
4. Run `["sh", "/ador/io/gate.sh"]` through the exec seam - two space-free
   tokens, immune to WSL argv splitting. The script's exit status is the
   executor's.
5. Read back from the HOST filesystem: the event stream and stderr from the
   io dir, questions from `<worktree>/<questions_file>`. Extract the session
   id from the event stream by key name (`sessionID`/`session_id`, regex,
   nesting-tolerant). A missing output file is NOT an error - the exit code
   carries the failure and the conductor decides.
- Gate artifacts (`gate.sh`, `output.jsonl`, `stderr.log`) persist in
  `.ador/runs/<run-id>/io/` for audit; being outside the worktree, the
  executor can never `git add` them.
- **Safety:** `--auto` anywhere in the template raises `ValueError` at
  construction, and `validate_config` reports it before any run starts - it
  would auto-approve the push/pr/merge permissions that keep the executor
  off the remote (prereq report section 6).

## 4. Dependencies

- Internal: `ador.isolation` (mount constants; `ContainerManager.exec` is
  the usual `ExecTarget`), `ador.util.CommandResult`; `[executor]` config.
- External: the executor CLI inside the `ador-executor` image; the target
  repo's `opencode.json` (permissions) arrives with the worktree.

## 5. Inputs And Outputs

- Inputs: gate prompt, host worktree path, host io-dir path, optional
  session id and timeout (run budgets).
- Outputs: a `GateRun`; persisted gate artifacts in the io dir; whatever the
  executor itself did to the worktree (edits, local commits).

## 6. Data Contracts

- io-dir filenames: `gate.sh`, `output.jsonl`, `stderr.log` (module
  constants shared with tests).
- `GateRun.ok` = exit code 0; necessary but not sufficient to advance - the
  conductor still checks `has_questions` and runs `invariants`.
- `GateRun.session_id` falls back to the passed-in session when the output
  stream yields none, so continuation is never lost to a parse gap.
- **Dead-session self-heal** (live finding 2026-07-04): a launch failing
  with "Session not found" (the session died with its container or was
  pruned) relaunches once with a fresh session instead of failing the gate.
- The questions-file convention (design 6): executor writes
  `ADOR_QUESTIONS.md` (configurable) in the worktree and stops; presence
  after the gate = park.

## 7. Workflow Integration

The conductor loop (phase 3) calls `run_gate` once per gate with the gate's
prompt, passing the session id from the previous `GateRun` so opencode keeps
its context, then branches on the result: questions -> park; failure/budget
-> retry or escalate; clean -> verify invariants and advance (design 7a).

## 8. Usage

```python
from functools import partial
from ador.executor.launcher import build_executor

executor = build_executor("opencode",
                          "opencode run --dir {worktree} -m {model} --format json {prompt}",
                          "openai/gpt-5.4-fast")
execute = partial(containers.exec, "ador-run-<run-id>")
run = executor.run_gate(execute, worktree_path, io_path, intake_prompt,
                        timeout=3600)
if run.has_questions:
    park(run.questions)
elif run.ok:
    advance(session=run.session_id)
```

## 9. Validation And Tests

- `tests/test_executor.py` (offline, fake exec seam): WSL-safe script
  protocol (two-token argv, LF-only script, quoted prompt, redirections),
  session continuation and fallback, questions detection, stale-questions
  clearing, failure/timeout as data, `--auto` rejection, factory wiring.
- `tests/test_config.py`: `--auto` flagged by `validate_config`.
- **Live verification done 2026-07-03** (real container, Docker in WSL2,
  8/8 steps; prereq report section 13): a hostile prompt (quotes, `$`,
  backticks, `%`, newline) round-trips byte-exact through the WSL boundary;
  questions detection, stale clearing, exit-code passthrough, artifact
  persistence.
- **Mutating opencode spike done 2026-07-03** (prereq report section 14,
  real gpt-5.5 session on a scratch worktree of the real repo): opencode
  executed the `.agentic` CLI non-interactively, loaded the
  `agentic-development` skill unprompted, committed evidence under the bot
  identity, and the push attempt was auto-rejected headless - all three
  design assertions proven through this launcher.
- Minimum validation after a change: `uv run --group dev pytest tests/test_executor.py`.

## 10. Limitations And Future Work

- Only opencode is implemented; pi/codex need their own session-continuation
  idioms behind the same factory.
- Observed event schema (live, 2026-07-03): NDJSON with `step_start` /
  `tool_use` / `step_finish` events, top-level `sessionID`, full tool
  inputs/outputs/exit codes; `step_finish` carries `tokens`
  (input/output/reasoning/cache) and `cost` - the metrics phase reads usage
  straight from the persisted `output.jsonl`.
- **An auto-rejected permission ends the opencode run at that point** (spike
  finding). The conductor must treat a rejection as end-of-gate and never
  sequence required work after an expected rejection.
- No mid-gate progress visibility: results are read at exit. If gates prove
  too long to run blind, add tailing of `output.jsonl` (it grows during the
  run) without changing the protocol.
