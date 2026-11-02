<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Executor launcher

## Routing

Use this page for executor selection, gate script transport, output parsing,
session handling, the Pi RPC launch and usage/cost telemetry. Start at
`04_Software/adore/executor/launcher.py` (Pi RPC client:
`04_Software/adore/executor/pi_rpc.py`); verify with
`04_Software/tests/test_executor.py` and `04_Software/tests/test_pi_rpc.py`.
Stage decisions belong to `orchestrator.md`; the executor image to
`isolation.md`.

## Purpose and boundaries

`04_Software/adore/executor/` launches one bounded executor gate inside an
already-provisioned container or native target. It is an executor-neutral transport and result
collector; the orchestrator decides which stage to run and what an outcome
means.

## Public interface

- `build_executor(kind, command_template, model, questions_file)` selects the
  `opencode`, `pi`, `codex`, or `qwen` implementation.
- `FileProtocolExecutor.run_gate(...)` accepts an injected backend command seam,
  worktree/io paths, prompt, timeout, archive stem and an optional `cancel`
  check; it returns a typed `GateRun`.
- `Executor.cancel_grace_seconds(execute)` is None by default; a number means
  the gate takes the `cancel` check and ends itself, and the conductor stops
  the container only if the gate still runs that long after the cancel.
- `PiExecutor.run_gate` on a target with `spawn` runs Pi through
  `pi_rpc.run_pi_rpc(spawn, argv, env, prompt, ...) -> PiRpcResult` with the
  fixed `pi_rpc_argv(model)` and `PI_RPC_ENV`; other targets keep the file
  protocol.
- `GateRun` reports exit status, typed `timed_out`, questions, bounded output,
  usage, explicit token/cost coverage, and archive information.

## Invariants

The launcher writes LF-only `gate.sh` into the run IO directory and invokes
the backend shell and native IO path (container default `sh /adore/io/gate.sh`); prompts and models are shell-quoted before they
enter that script. Results cross the container boundary through `output.jsonl`,
`stderr.log`, and the configured questions file rather than fragile host/WSL
argv or streamed output. A timeout is taken solely from `CommandResult.timed_out`,
not guessed from exit text. Each requested archive is immutable under
`io/archive/`, so a retry cannot destroy prior evidence.

The executor receives no forge credentials and cannot publish. Unsafe
auto-approval flags are rejected by configuration validation. The launcher
starts a fresh session for each gate and never guesses a retry from timeout text.
OpenCode and Codex mark cost as reported only when their event stream has an
explicit cost field; token-only usage does not prove a zero-dollar cost.
Complete OpenCode, Pi and Codex token records mark token coverage even when
their counts are zero; missing or partial records do not claim coverage.
Pi counts only completed `turn_end` JSON events, including cache-read and
cache-write input tokens; streaming and message-end copies are ignored. Invalid
usage values are skipped. Pi's embedded monetary value is an executor estimate,
so the launcher leaves billed cost unavailable for administrator price rules.

Container Pi runs `node /opt/pi/.../cli.js --mode rpc --no-session
--no-approve --no-skills --no-extensions --no-prompt-templates --no-themes
--no-mcp -e /opt/adore/pi/adore-guard.ts --model <model>` with
`PI_CODING_AGENT_DIR=/home/adore/.adore-pi-agent`, `PI_OFFLINE=1`,
`PI_TELEMETRY=0`, `PI_SKIP_VERSION_CHECK=1`; the prompt goes over stdin and the
configured `[executor.pi]` command is not used. A launch is complete only on
`agent_settled` that is not aborted with a last assistant stopReason other
than `error`; the exit code is not the result. Timeout or cancel sends `abort`,
waits 10 s for settling, closes stdin, terminates after 5 s and kills after 5
more (exit 124 + `timed_out`, or 130). A rejected prompt or an error stop is
exit 1 with `Pi run failed (<class>): <redacted message>`; an early exit, a
malformed or too deeply nested stdout record, an unreadable last assistant
record or a rejected command is a protocol failure (process
code or 1; 127/126 when Pi cannot start). At most one 16 MiB stdout record is
in memory; deltas are not persisted, records over 64 KiB persist as stubs,
`output.jsonl` stops at 32 MiB, tails keep 64 KiB. Usage is summed over every
assistant `message_end` (input includes cache read/write), cross-checked once
with `get_session_stats`; an unreadable assistant record makes tokens
unavailable; cost is never reported. The guard blocks `git push` and
`gh`/`glab`/`tea` in bash/powershell and refuses project trust.

## Key behaviors

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: Native run_files receives argv tokenized before prompt replacement, preserving fresh sessions, questions, usage and archives. gate.sh is a legal-header native launch description. Native files are contained bounded UTF-8 and redacted before retention, including the conductor questions file.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


- `REQ-FUNC-e397f7f6`: Bound targets supply shell/worktree/IO paths and verified resource identity; plain injected callables retain the container defaults. Prompts/scripts remain file transported and quoted.

- `REQ-FUNC-59ccdb74` - WSL-safe file transport and typed timeout propagation
  for every container executor except Pi.
- `REQ-FUNC-116450ef` - container Pi stage through one RPC process.
- `REQ-FUNC-7caa53e1` - Pi usage summed over turns, no billed cost.
- `REQ-REL-0859d96e` / `REQ-REL-2d48ea39` - abort on timeout / cancel, then end.
- `REQ-FUNC-1cb4bcc0` - classified, redacted Pi failure evidence.
- `REQ-REL-12b7dee2` - Pi protocol failures fail closed.
- `REQ-NFR-7a10768a` - bounded Pi streaming memory and evidence.
- `REQ-SEC-a6d32441` - Pi isolation flags, agent directory and guard.
- `REQ-PLAT-1a1960b2` - pinned Node/Pi/pi-web-access and guard in the image.
- `REQ-FUNC-c6e5282d` - questions parking and immutable launch archives.
- `REQ-FUNC-448cbde7` - usage and cost coverage for web metrics.

## Architecture

```mermaid
flowchart LR
    conductor([Orchestrator]) --> factory[build_executor]
    factory --> gate[FileProtocolExecutor.run_gate]
    gate --> io[(Run IO files)]
    gate --> container([ExecTarget])
    container --> output[(output.jsonl and stderr)]
    output --> gate
    gate --> result[GateRun]
    result --> conductor
```

The file protocol decouples prompts and results from host/container argument
quoting; the caller owns stage policy.

## Files

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


- `04_Software/adore/executor/base.py` - typed gate result and common helpers.
- `04_Software/adore/executor/launcher.py` - file protocol, parsers and the
  Pi RPC launch.
- `04_Software/adore/executor/pi_rpc.py` - Pi RPC client.
- `04_Software/docker/pi/adore-guard.ts` - Pi guard extension (image).
- `04_Software/tests/test_pi_rpc.py`, `tests/fake_pi_rpc.py`,
  `tests/fixtures/pi_rpc/` - offline replay of the PI-01 recordings.
- `04_Software/tests/test_executor.py` - launch, timeout and usage contracts.
