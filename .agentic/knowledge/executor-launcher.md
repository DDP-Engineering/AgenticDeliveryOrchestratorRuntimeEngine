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

- `build_executor(command_template, model, questions_file, *, provider,
  models, internet, web_search)` returns a `PiExecutor`; Pi is the only executor implementation.
  `model` is the model ID within the provider, `provider` the
  `[executor] provider` (mapped by `pi_providers.pi_provider`: `chatgpt` ->
  `openai`, `custom` -> `adore-endpoint`), `models` the endpoint
  `models.json` for `custom` (else None).
- `FileProtocolExecutor.run_gate(...)` accepts an injected backend command seam,
  worktree/io paths, prompt, timeout, archive stem and an optional `cancel`
  check; it returns a typed `GateRun`.
- `Executor.cancel_grace_seconds(execute)` is None by default; a number means
  the gate takes the `cancel` check and ends itself, and the conductor stops
  the container only if the gate still runs that long after the cancel.
- `PiExecutor.run_gate` on a target with `spawn` runs Pi through
  `pi_rpc.run_pi_rpc(spawn, argv, env, prompt, ...) -> PiRpcResult` with the
  fixed `pi_rpc_argv(model, provider)` and `PI_RPC_ENV`; other targets keep
  the file protocol, where `{model}` is `<pi provider>/<model id>`.
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

The executor receives no forge credentials and cannot publish. The launcher
does not inspect command flags; configuration validation rejects `--auto`
before a run. The launcher starts a fresh session for each gate and never
guesses a retry from timeout text.
Complete Pi token records mark token coverage even when their counts are zero;
missing or partial records do not claim coverage.
A native Pi run counts only completed `turn_end` JSON events, including cache-read and
cache-write input tokens; streaming and message-end copies are ignored. Invalid
usage values are skipped. Pi's embedded monetary value is an executor estimate,
so the launcher leaves billed cost unavailable for administrator price rules.

Container Pi runs `node /opt/pi/.../cli.js --mode rpc --no-session
--no-approve --no-skills --no-extensions --no-prompt-templates --no-themes
--no-mcp -e /opt/adore/pi/adore-guard.ts --provider <pi provider> --model
<model id>` with
`PI_CODING_AGENT_DIR=/home/adore/.adore-pi-agent`, `PI_OFFLINE=1`,
`PI_TELEMETRY=0`, `PI_SKIP_VERSION_CHECK=1`; the prompt goes over stdin and the
configured `[executor] command` is not used. For an OpenAI-compatible
endpoint, before Pi starts each gate, `_place_models` writes the
key-free `models.json` to the io dir as `pi-models.json` (`MODELS_FILE`) and
runs `cp /adore/io/pi-models.json /home/adore/.adore-pi-agent/models.json`
through the exec seam; a failed copy fails the gate (non-zero exit, stderr
`Pi models.json could not be placed in the agent directory: ...`) without
starting Pi. With `internet` on and `web_search` not `none`, the argv adds
`-e /opt/pi/lib/node_modules/pi-web-access` (`CONTAINER_PI_WEB_ACCESS`) and
`_place_file` copies `web_search_json(search)` (`{provider, workflow: "none",
toolActivation: "eager"}`, no key; Brave/Tavily read their key from the
environment) from `pi-web-search.json` to the agent directory's
`web-search.json` first; a failed copy fails the gate with `The web search
configuration could not be placed in Pi's agent directory: ...`. With
`internet` off nothing web-related is loaded and the argv adds
`--append-system-prompt INTERNET_OFF_NOTICE`. `pi_rpc_argv(model, provider, *,
web, notice)` builds the argv; the Test AI connection passes neither. A launch is complete only on
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
The failure classes, matched in this order, are `subscription`
(`subscription_sharing_user_not_eligible`), `sign-in`, `model`, `credential`,
`rate-limit`, `network`, else `provider`.

For `provider = "chatgpt"` the orchestrator's `_launch_stage` asks its
`chatgpt_token` source for an access token valid for the stage limit plus
`chatgpt.TOKEN_MARGIN_SECONDS` (300 s) before `run_gate`. The default source is
`chatgpt.bearer_token(self.containers, chatgpt.credential_dir(), seconds)`: Pi's
`token` command in a one-off helper container from the project's image whose
only bind mount is the server's credential directory `<ADORE home>/chatgpt`.
The run container never mounts that directory, so the refresh token never
enters a run. The token reaches only that gate as `OPENAI_API_KEY`, through
`ContainerBackend.bind(name, env, resource, secrets=(token,))`; the exec passes
it as a bare `--env` name. `BoundTarget.redact` replaces it with `[REDACTED]` in
Pi's evidence (`pi_rpc` gets it as `redact`). Pi runs with `--provider openai`.
When no token can be had (`ChatGptError`), the attempt returns
`GateRun(exit_code=1, stderr="ChatGPT sign-in: <sentence>")` without starting Pi,
the conductor logs `<run id>: ChatGPT token unavailable (<code>)`, and the
ordinary retry policy applies. The token is not refreshed during a stage, so
config validation limits a `chatgpt` stage to 3000 s.
- The file protocol decouples prompts and results from host/container argument
  quoting; the caller owns stage policy.

## Key behaviors

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: Native run_files receives argv tokenized before prompt replacement, preserving fresh sessions, questions, usage and archives. gate.sh is a legal-header native launch description. Native files are contained bounded UTF-8 and redacted before retention, including the conductor questions file.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


- `REQ-FUNC-e397f7f6`: Bound targets supply shell/worktree/IO paths and verified resource identity; plain injected callables retain the container defaults. Prompts/scripts remain file transported and quoted.

- `REQ-FUNC-2df31adf` - every stage launches Pi with `[executor] provider` and `model`.
- `REQ-FUNC-59ccdb74` - WSL-safe file transport and typed timeout propagation
  for file-protocol launches.
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
- `REQ-SEC-0fb2bba3` - each ChatGPT stage receives only a short-lived access token.
- `REQ-FUNC-87f05705` - a ChatGPT stage without an access token fails clearly without starting Pi.

- `REQ-FUNC-f1b71231` - internet on: pi-web-access and web-search.json.
- `REQ-FUNC-95778891` - a failed web-search.json copy fails the gate.
- `REQ-FUNC-53fd0c28` - internet off: no web tools and a system-prompt notice.

## Files

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


- `04_Software/adore/executor/base.py` - typed gate result and common helpers.
- `04_Software/adore/executor/launcher.py` - file protocol, parsers and the
  Pi RPC launch.
- `04_Software/adore/executor/pi_rpc.py` - Pi RPC client.
- `04_Software/docker/pi/adore-guard.ts` - Pi guard extension (image).
- `04_Software/adore/chatgpt.py`, `04_Software/docker/pi/adore-chatgpt.mjs` -
  the server's ChatGPT sign-in and the helper that mints a stage's access token.
- `04_Software/tests/test_chatgpt_stage.py` - a ChatGPT stage's token, its
  redaction, its requested life and the no-token failure.
- `04_Software/tests/test_pi_rpc.py`, `tests/fake_pi_rpc.py`,
  `tests/fixtures/pi_rpc/` - offline replay of the PI-01 recordings.
- `04_Software/tests/test_executor.py` - launch, timeout and usage contracts.
