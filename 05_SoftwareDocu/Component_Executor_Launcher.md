<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Executor Launcher (`adore/executor/`)

> Component documentation per `component_documentation_template.md`.
> Sources: `04_Software/adore/executor/base.py`,
> `04_Software/adore/executor/launcher.py`,
> `04_Software/adore/executor/pi_rpc.py`; Pi guard:
> `04_Software/docker/pi/adore-guard.ts`.
> Design context: `00_Planning/ADORE_System_Overview.md`;
> Runtime-image and credential contracts: `04_Software/docker/README.md` and
> `01_Documentation/Security_And_Credentials.md`.

## 1. Purpose

Launch Pi (`@earendil-works/pi-coding-agent`), ADORE's only coding agent,
headless for one gate per launch - over RPC inside the run's container, or
with the configured `[executor] command` for a local (native) run - and read
every result back deterministically. All code reasoning lives in the
executor; the launcher only composes commands and collects outcomes.

## 2. Responsibilities

- `Executor` (ABC in `base.py`) + `ExecTarget` protocol (the container exec
  seam, bound by the orchestrator to the run's container) + `GateRun` (the
  conductor's decision inputs: exit code, questions, raw output, immutable
  artifact archive directories). There is deliberately no session id.
- `FileProtocolExecutor` (`launcher.py`): the file-based gate protocol of a
  native run (section 3), template substitution, questions-file detection,
  and per-launch archiving. The subclass supplies only the usage parser.
- Every launch is a FRESH executor session. The durable AEGIS journal is the
  resume authority, so nothing is continued and no session id is tracked. The
  `--session` continuation, the dead-session self-heal relaunch, and the
  per-executor `_extract_session_id` hooks were removed: the orchestrator
  always launched with an empty session and never stored one back, so none of
  that machinery could ever run.
- `PiExecutor`: the only implementation of the `Executor` interface. On a
  container target (one with a `spawn` seam) every gate is one `pi --mode rpc`
  process driven by `pi_rpc` (section "Pi RPC launch") using the image's
  pinned Pi; the configured `[executor] command` is not used there. A native
  target keeps the file protocol with the configured command, where
  final `turn_end` events report input/output and cache read/write tokens.
  Pi's embedded cost is an executor estimate, so ADORE leaves reported cost
  unavailable on both paths.
- `pi_rpc.run_pi_rpc(...)`: the Pi RPC client - prompt over stdin, bounded
  event reading, completion on `agent_settled`, `abort` on the stage timeout
  or a cancel, termination after a grace period, failure classification and
  usage summed per turn; returns a `PiRpcResult`.
- `build_executor(command_template, model, questions_file, *, provider,
  models)` - the config selection point; returns a `PiExecutor`.
  `command_template` is the native `[executor] command` (default
  `pi -p --mode json --model {model} {prompt}`, `branding.PI_NATIVE_COMMAND`);
  `model` is the model ID within the provider; `provider` is the
  `[executor] provider` value, turned into Pi's provider id by
  `pi_providers.pi_provider` (`openai` for `chatgpt`, `adore-endpoint` for
  `custom`, else the id); `models` is the endpoint `models.json` document
  (`pi_providers.models_json`) for `custom`, else None.

Explicitly not owned: *which* gate to run and what to do with the outcome
(orchestrator, design 7a), container lifecycle (isolation), posting anything
to the Git platform (forge; the executor never touches the remote).

## 3. Implementation Overview

**The file-based gate protocol** (native Pi runs) - every byte crosses
process boundaries in files, never argv or live stdout, because of two
verified findings: `wsl.exe` splits argv elements containing spaces, and a
headless CLI may buffer stdout so live streaming looks hung.

1. Delete a stale questions file from the worktree - its presence after the
   gate must mean it was written by THIS gate.
2. Render the command from the `[executor] command` template: `{prompt}` ->
   shell-quoted prompt text, `{model}` -> quoted `<pi provider>/<model id>`, `{worktree}` ->
   `/adore/work` (the container-side mount). No other placeholder is
   supplied. Nothing is appended for continuation: each gate is a fresh session.
3. Write `gate.sh` (LF endings; Windows CRLF would break `sh`) into the
   run's io dir: `cd /adore/work`, then the command wrapped in a `{ ...; }`
   group with stdout redirected to `output.jsonl` and stderr to `stderr.log`,
   both in `/adore/io`. No `exec` prefix - templates may be compound commands,
   and the group makes the redirection cover the WHOLE compound (e.g. `a && b`),
   not just its last stage.
4. Run the backend shell and native IO script path through the bound command
   seam (container default `["sh", "/adore/io/gate.sh"]`). Paths remain single argv tokens;
   script paths are quoted and support spaces. The script's exit status is the
   executor's.
5. Read back from the HOST filesystem: the event stream and stderr from the
   io dir, questions from `<worktree>/<questions_file>`. Token usage is parsed
   per executor. A missing output file is NOT an error - the exit code carries
   the failure and the conductor decides.
6. When the orchestrator supplies `archive_stem`, copy the just-finished
   launch into `io/archive/<stem>-attempt1/` with `gate.sh`, `output.jsonl`,
   `stderr.log`, and `meta.json`. One launch per gate, so the suffix is
   constant; a reused stem is disambiguated with a numeric suffix.

Steps 1-5 live in `FileProtocolExecutor`; `PiExecutor` customizes only stream
parsing. Pi reads the repo's
`AGENTS.md` gate contract natively and gets its push/merge guardrails from
the repo adapter plus container isolation - there are no remote credentials in
the container, so the executor cannot push regardless.
- The live exchange files (`gate.sh`, `output.jsonl`, `stderr.log`) remain in
  `.adore/runs/<run-id>/io/` and are overwritten by the next launch. Immutable
  per-launch archives persist under `io/archive/`; being outside the worktree,
  the executor can never `git add` them.
- **Safety:** `validate_config` refuses `--auto` in the native
  `[executor] command` before any run starts - it would auto-approve the
  push/pr/merge permissions that keep the executor off the remote (prereq
  report section 6). The command must also contain `{prompt}`. This is a
  safety belt, not the boundary (no forge credential in the run is).

## 3a. Pi RPC launch (container targets)

`PiExecutor.run_gate` on a target with `spawn` (the container `BoundTarget`,
which verifies the pinned container identity, then calls
`ContainerManager.spawn`: `<runtime> exec -i` with `exec`'s environment rules):

1. Clear the stale questions file, `output.jsonl` and `stderr.log`. For an
   OpenAI-compatible endpoint (`models` set), write the document to the io dir
   as `pi-models.json` (`MODELS_FILE`) and run
   `cp /adore/io/pi-models.json /home/adore/.adore-pi-agent/models.json`
   through the exec seam, every gate, so a kept-warm container always has the
   current file; a failed copy returns a failed `GateRun` (the copy's exit
   code, or 1) with stderr `Pi models.json could not be placed in the agent
   directory: ...` and Pi is not started. The document holds no key: `apiKey`
   is `$ADORE_ENDPOINT_API_KEY` when that secret is set, else the literal
   `adore-no-key`. Then write a descriptive `gate.sh` with the argv and
   environment (no shell runs; the prompt never enters it).
2. Start `node /opt/pi/lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js
   --mode rpc --no-session --no-approve --no-skills --no-extensions
   --no-prompt-templates --no-themes --no-mcp -e /opt/adore/pi/adore-guard.ts
   --provider <pi provider> --model <model id>` (`pi_rpc_argv(model,
   provider)`) with `PI_CODING_AGENT_DIR=/home/adore/.adore-pi-agent`,
   `PI_OFFLINE=1`, `PI_TELEMETRY=0`, `PI_SKIP_VERSION_CHECK=1` (inline
   `--env` values; the provider key keeps the bare-key rule). Nothing comes
   from the personal `~/.pi`, `~/.agents/skills` or the project's `.pi`; the
   project's `AGENTS.md` context file stays on.
3. Send `{"type":"prompt"}` and keep stdin open. Reader threads split stdout
   on LF, hold at most one record of 16 MiB, reduce it to small facts (usage,
   stop reason, bounded error text, tool status, `agent_settled`) and persist
   a bounded copy; the main loop polls every 0.2 s against the deadline and
   the cancel check.
4. Done = `agent_settled`. After a clean settle, `get_session_stats` is asked
   once (5 s) to cross-check the per-turn usage; a mismatch is a note in the
   evidence. Then stdin is closed (Pi's shutdown request); after 5 s the
   process is terminated, after 5 more killed.
5. Deadline or cancel: send `abort`, wait up to 10 s for `agent_settled`,
   then step 4's shutdown.
6. Archive as in the file protocol; `output.jsonl` is copied from the
   bounded persisted file.

**ChatGPT subscription stages.** For `provider = "chatgpt"` the orchestrator's
`_launch_stage` first asks its `chatgpt_token` source (by default
`chatgpt.bearer_token` with the project's `ContainerManager` and the server's
credential directory `<ADORE home>/chatgpt`) for an access token valid for the
stage limit plus `chatgpt.TOKEN_MARGIN_SECONDS` (300 s). That runs ADORE's helper
script `/opt/adore/pi/adore-chatgpt.mjs` in a one-off helper container
(`ContainerManager.helper_command`: `<runtime> run --rm` with exactly one bind
mount, the credential directory at `/adore/chatgpt`); the run container never
mounts it, so the refresh token never enters a run. The token then joins only
this gate's target: `ContainerBackend.bind(name, {..., OPENAI_API_KEY: <access
token>}, ..., secrets=(token,))`, and `BoundTarget.redact` replaces the token with
`[REDACTED]` in Pi's persisted evidence (`pi_rpc` receives it as `redact`); the
descriptive `gate.sh` lists only Pi's fixed RPC environment. Pi starts with `--provider openai`. When no token can be had, the stage
attempt returns a failed `GateRun` (exit 1, stderr `ChatGPT sign-in: <sentence>`)
without starting Pi, the conductor logs only the cause code, and the ordinary
retry policy applies. See [ChatGPT sign-in](Component_ChatGPT_Sign_In.md).

The guard extension blocks `git push` and `gh`/`glab`/`tea` in the `bash` and
`powershell` tools (`tool_call` handler returning a block; Pi reports a
failed tool result starting with "ADORE blocks") and answers `project_trust`
with "no". It is loaded with `-e`, so it needs no project trust. It is defence
in depth: the boundary stays that no forge credential is in the container.

## 4. Dependencies

- Internal: `adore.isolation` (mount constants; `ContainerManager.exec` is
  the usual `ExecTarget`, `ContainerManager.spawn` the Pi RPC seam),
  `adore.execution.BoundTarget`, `adore.branding` (Pi paths in the image),
  `adore.util.CommandResult`; `[executor]` config.
- Executor image: Node 22.23.4, Pi 1.4.0 and pi-web-access 0.46.0 under
  `/opt/pi`, the guard at `/opt/adore/pi/adore-guard.ts`, ADORE's ChatGPT
  helper at `/opt/adore/pi/adore-chatgpt.mjs` and the agent
  directory `/home/adore/.adore-pi-agent` (`docker/Dockerfile.executor-base`;
  `docker/verify-runtime.sh` checks the versions and that the helper loads the
  pinned Pi). `adore.chatgpt` supplies a ChatGPT stage's access token. pi-web-access is
  installed but not loaded.
- External: Pi inside the `adore-executor` image (container runs) or on the
  host (native runs only); the target repo's `AGENTS.md` arrives with the
  worktree (its `.pi` directory is not loaded by a container RPC run).

## 5. Inputs And Outputs

- Inputs: gate prompt, host worktree path, host io-dir path, timeout (run
  budgets), and archive stem. No session id: every launch is a fresh session.
- Outputs: a `GateRun`; live exchange files in the io dir; immutable archive
  directories when requested; whatever the executor itself did to the
  worktree (edits, local commits).

## 6. Data Contracts

- io-dir filenames: `gate.sh`, `output.jsonl`, `stderr.log`, and
  `pi-models.json` for an endpoint; archive root: `archive/` (module constants
  shared with tests).
- Archive directory shape: `<stem>-attempt<N>` with a numeric suffix on rare
  collisions so archives are never overwritten. Missing output/stderr becomes
  an empty archive file with presence flags in `meta.json`.
- Archive write failure is returned as a failed `GateRun`, not silently
  ignored.
- `GateRun.ok` = exit code 0; necessary but not sufficient to advance - the
  conductor still checks `has_questions` and runs `invariants`.
- `GateRun.timed_out` copies `CommandResult.timed_out` from the physical launch;
  it is never inferred from exit code or stderr. Archive-error returns preserve
  it and archive metadata records it.
- The questions-file convention: executor writes
  `ADORE_QUESTIONS.md` (configurable) in the worktree and stops; presence
  after the gate = park.
- Pi RPC `GateRun`: exit 0 completed (settled, not aborted, last assistant
  stopReason not `error`, whatever the process exit code); 1 failed, with
  `stderr` starting `Pi run failed (<class>): <message>` where the class is
  subscription (`subscription_sharing_user_not_eligible`, matched first),
  sign-in, model, credential, rate-limit, network or provider and masked key
  hints are redacted; 124 + `timed_out` at the stage timeout; 130 on cancel;
  the process code (or 1) for a protocol failure (exit before settling,
  malformed stdout record, unreadable last assistant record, rejected command), 127/126 when Pi cannot start.
  The orchestrator maps these to `EXECUTOR_TIMEOUT` / `EXECUTOR_EXIT`.
- Pi RPC usage: `tokens_in` = input + cache-read + cache-write and
  `tokens_out` = output, summed over every assistant `message_end`; cache
  categories separate; `cost_usd` 0 and `cost_reported` False. A skipped or
  invalid assistant record makes `tokens_reported` False. The orchestrator's
  existing versioned `usage` event (one per launch) carries it.
- Pi RPC evidence: streaming `message_update` deltas are never persisted,
  records over 64 KiB are persisted as `{"type", "adore_omitted_bytes"}`
  stubs, `output.jsonl` stops at 32 MiB and `stderr.log` at 1 MiB; `GateRun`
  keeps 64 KiB tails.

## 7. Workflow Integration

The conductor loop (phase 3) calls `run_gate` once per gate with the gate's
prompt, then branches on the result: questions -> park; failure/budget
-> retry or escalate; clean -> verify invariants and advance.

Cancellation: `Executor.cancel_grace_seconds(execute)` is None by default and
the conductor stops the container when the cancel marker appears. `PiExecutor`
on a container target returns its abort-and-exit grace (25 s); the conductor
then passes a `cancel` check to `run_gate` and stops the container only if the
gate is still running that long after the marker was seen.

## 8. Usage

```python
from functools import partial
from adore.executor.launcher import build_executor

executor = build_executor("pi -p --mode json --model {model} {prompt}",
                          "gpt-5.5", provider="openai")
# A container target is the orchestrator's BoundTarget (it has `spawn`, so
# the gate runs over Pi RPC); a native target uses the command above.
run = executor.run_gate(target, worktree_path, io_path, intake_prompt,
                        timeout=3600, archive_stem="001-intake")
if run.has_questions:
    park(run.questions)
elif run.ok:
    advance()
```

## 9. Validation And Tests

- `tests/test_executor.py` (offline, fake exec seam): WSL-safe script
  protocol (two-token argv, LF-only script, quoted prompt, redirections),
  questions detection, stale-questions clearing, failure/timeout as data,
  normal/missing-output/nonzero archive behavior, archive-write failure as
  data, Pi `turn_end` usage parsing, and factory wiring (`build_executor`
  returns a `PiExecutor`).
- `tests/test_config.py`: `--auto` in the native command and a command
  without `{prompt}` are flagged by `validate_config`; removed `[executor]`
  keys and `[executor.<name>]` tables are refused as unknown keys.
- **Live verification done 2026-07-03** (real container, Docker in WSL2,
  8/8 steps): a hostile prompt (quotes, `$`,
  backticks, `%`, newline) round-trips byte-exact through the WSL boundary;
  questions detection, stale clearing, exit-code passthrough, artifact
  persistence.
- `tests/test_pi_rpc.py` (offline): a fake Pi (`tests/fake_pi_rpc.py`)
  replays the PI-01 spike recordings in `tests/fixtures/pi_rpc/` over real
  pipes - tool-call run and per-turn usage, exit code after settling, timeout
  abort and kill, cancel abort, six provider failure classes with key-hint
  redaction, crash before settling, malformed record, start failure, large
  output and an over-limit record, the guard run, the isolation argv and
  environment, the usage event through `_journal_usage`, the conductor's
  cancel grace, `--provider`/`--model` on RPC and `<pi provider>/<model id>`
  in the native template, and the endpoint `models.json` placed before Pi
  starts (a failed copy fails the stage). `tests/test_isolation.py` covers
  `ContainerManager.spawn`; `tests/test_pi_providers.py` covers the provider
  rules and `models_json`.
- `tests/test_chatgpt_stage.py` (offline): a ChatGPT stage's token reaches only
  that gate as `OPENAI_API_KEY` and is redacted, a stage override sets the
  requested token life, a missing token fails the attempt without starting Pi,
  and an API-key project gets no token.
- Live check 2026-11-02 (image built from this Dockerfile in WSL Docker, a
  fake chat-completions endpoint in the container, no key): see the TASK-41fd0159
  journal for the recorded guard and isolation result.
- Minimum validation after a change: `uv run --group dev pytest tests/test_executor.py tests/test_pi_rpc.py tests/test_pi_providers.py`.

## 10. Limitations And Future Work

- Pi final-turn usage records cache-read and cache-write token counts on
  `GateRun`. `tokens_in` includes these categories, so reports expose them as
  subsets rather than adding them to input again.

- `GateRun.cost_reported` distinguishes an explicitly emitted cost (including
  zero) from the default zero used when the executor has no cost telemetry.
  `GateRun.tokens_reported` similarly distinguishes a complete zero-token
  report from absent or partial usage. File-protocol launchers set this flag
  from valid final executor events; older injected results may leave it unset.
  Pi has no billed-cost telemetry, so `cost_reported` stays False. The
  orchestrator journals this coverage along with executor, model and
  review-round identifiers.

- Pi RPC runs only in containers; a native (local) Pi keeps the file
  protocol and the configured command. Killing the `docker exec` client closes
  Pi's stdin but sends no signal inside the container; on cancel the
  conductor's container stop remains the backstop.

- No mid-gate progress visibility for a native run: results are read at exit. If gates prove
  too long to run blind, add tailing of `output.jsonl` (it grows during the
  run) without changing the protocol.

## Backend-native gate paths

Bound targets supply worktree, IO and shell paths through `ExecutionPaths`. The existing container defaults preserve legacy injected callables. Preparation and all later gates use the same bound resource/environment; launcher parsing/approval remains unchanged.

## Native execution contract

Native run_files receives argv tokenized before prompt replacement, preserving fresh sessions, questions, usage and archives. gate.sh is a legal-header native launch description. Native files are contained bounded UTF-8 and redacted before retention, including the conductor questions file.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused native proof:
`04_Software/tests/test_local_execution.py`.
