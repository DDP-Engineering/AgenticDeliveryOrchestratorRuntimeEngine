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
  models, internet, web_search, thinking, prompts)` returns a `PiExecutor`; Pi is the only executor implementation.
  Optional `prompts` shares the conductor-owned `PromptCatalog`; standalone
  construction eagerly loads all resources and refuses bad files with `PromptError`.
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
before a run. Job gates start a bounded process in the exact job-owned Pi conversation;
non-job probes remain ephemeral. The launcher never guesses retries from text.
Complete Pi token records mark token coverage even when their counts are zero;
missing or partial records do not claim coverage.
The file-only test adapter counts completed `turn_end` JSON events, including cache-read and
cache-write input tokens; streaming and message-end copies are ignored. Invalid
usage values are skipped. Pi's embedded monetary value is an executor estimate,
so the launcher leaves billed cost unavailable for administrator price rules.

Container job Pi runs `node /opt/pi/.../cli.js --mode rpc --session
/adore/io/pi-conversation/session.jsonl --session-dir /adore/io/pi-conversation
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
`--append-system-prompt <offline notice>` from `system/internet-off.md`. `pi_rpc_argv(model, provider, *,
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
assistant `message_end` (input includes cache read/write), cross-checked against the final `get_session_stats` minus its pre-prompt baseline; an unreadable assistant record makes tokens
unavailable; cost is never reported. The guard blocks `git push` and
`gh`/`glab`/`tea` in bash/powershell and refuses project trust.
The failure classes, matched in this order, are `subscription`
(`subscription_sharing_user_not_eligible`), `sign-in`, `model`, `credential`,
`rate-limit`, `network`, else `provider`.

For `provider = "chatgpt"`, `Orchestrator._launch_stage` requests an access
token for the stage limit plus 300 seconds through `helper_for`. Native
projects use `NativeHelper` with verified managed Node/Pi and the packaged
OAuth helper; container projects retain their helper container with only the
credential directory mounted. Pi refreshes the shared ADORE-owned store under
its lock. No refresh credential enters a run container or fresh native agent
directory. Native execution retains the host account's file permissions.

`LocalBackend.bind` and `ContainerBackend.bind` accept explicit launch secrets.
The temporary token reaches only the bound gate as OPENAI_API_KEY and is
included in evidence redaction. Local targets ignore ambient subscription
keys. A failed token request returns the existing typed ChatGPT cause without
launching Pi, and normal bounded recovery applies. Stage limits remain 3000 s.

- The file protocol decouples prompts and results from host/container argument
  quoting; the caller owns stage policy.

## Key behaviors

- `REQ-FUNC-1f56bfac`, `REQ-FUNC-e8d63a5c`, `REQ-FUNC-14872c0d`: system
  notices render from the shared shipped catalog. Native RPC always uses
  `system/server-internet.md`; container RPC uses `system/internet-off.md`
  only with internet off, and internet-on containers append no notice.
  Selection and transport preserve original bytes. Loading/rendering contracts
  belong to `prompts.md`; the executor-neutral gate interface stays unchanged.

- REQ-FUNC-c405688e: optional package_secrets keeps operational tails, stderr and questions sanitized and bounded. Bounded RPC stdout sessions persist literal values and archive without post-gate rewriting; complete usage remains independent. The non-RPC file protocol retains its existing sanitized stream policy.

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: Native Pi lends owned pipes to the shared RPC client and retains one job conversation, questions, per-attempt usage and archives. gate.sh is a legal-header native launch description. Native operational evidence and conductor questions are contained bounded UTF-8 and sanitized; RPC job-session recordings retain literal bounded events.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.

- `REQ-FUNC-e397f7f6`: Bound targets supply shell/worktree/IO paths and verified resource identity; plain injected callables retain the container defaults. Prompts/scripts remain file transported and quoted.

- `REQ-FUNC-f1b71231` - internet on: pi-web-access and web-search.json.
- `REQ-FUNC-95778891` - a failed web-search.json copy fails the gate.
- `REQ-FUNC-53fd0c28` - internet off: no web tools and a system-prompt notice.

## Files

- `04_Software/tests/test_system_packages.py`: package authority, independent egress, recovery and reviewed settings contracts.

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
- `04_Software/tests/test_prompts.py` - original notice bytes through native/container branches and shared construction-time reads.

The non-RPC file protocol encodes sanitized retained stdout/stderr directly as UTF-8 bytes without host newline expansion. RPC session archives copy the literal bounded stdout recording; sanitized stderr and returned tails retain their limits. Complete original usage remains independent of text retention.

Package-enabled Pi RPC gates combine cancellation with `package_secrets`: complete turn usage is kept; returned operational tails, stderr and questions stay sanitized and bounded. Live/archive stdout preserves literal bounded events, including known credentials, without a post-gate rewrite. Native RPC shares this policy. A timed-out gate settles the bound container before another command; unconfirmed interruption raises `ExecutionRecoveryError`. The non-RPC file protocol retains its existing sanitized retention.

RPC clarification questions apply the binding credential redactor before publication. Package-enabled questions also use the shared regular-file/identity checks, known-secret redaction and 64 KiB UTF-8 retention cap; linked question files fail closed.

## Operational diagnostics

Pi RPC captures bounded canonical diagnostics from protocol error fields, failed tool-result text and stderr after the binding credential redactor. Assistant content, reasoning, prompts and tool arguments are excluded. Concrete ModuleNotFoundError module identifiers and pytest numeric result counts survive; other known failures use categories and arbitrary content is withheld. The diagnostic ring retains at most 500 rows within 64 KiB per stream. GateRun carries the optional streams without changing lifecycle, timeout or usage decisions. executor/diagnostics.py owns normalization, canonical validation and unique host-owned snapshot persistence. Public fake-RPC and Retry tests exercise capture and journal binding without a model.

Recognized token-shaped module identifiers are withheld even when they satisfy Python identifier syntax. Diagnostic ring mutation and result snapshots share the evidence lock, including readers that outlive a bounded join.

Pi stage argv includes --thinking when configured; blank leaves Pi default. Both native and container paths use the same level.

## Live launch ownership

REQ-FUNC-fe8ecf4c: PiExecutor with a stage-attempt archive stem clears old output,
acquires StateStore(io_dir).run_lock("agent-session"), then atomically publishes
schema-1 live.json with UUID id, planned collision-safe archive id and start timestamp.
The ExitStack holds this crash-released kernel ownership until RPC/archive handling
finishes, then removes the marker on normal or exceptional exit. A crashed owner leaves
no held lock, so a retained marker cannot label an abandoned session live. Targets and
probes without a stage-attempt stem do not publish a job session. Existing archive
layout and one-RPC-per-stage behavior remain. Completed persisted RPC records flush
immediately for live readers. Offline lifetime/fault/producer visibility proof is in
`test_pi_rpc.py`; web projections and cursor continuity route to web-interface.md.

## Literal session persistence boundary

REQ-SEC-97e45ffb: completed RPC stdout records are persisted literally within the
existing per-record and 32 MiB total bounds; deltas remain omitted and oversized
records remain stubs. _Evidence keeps separate sanitized operational tail bytes.
Known binding/package credentials, key-hint and Bearer masking apply only to these
operational tails, stderr, questions, error messages and normalized diagnostics.
Package jobs never rewrite the raw session file before archiving. The shared authenticated
reader excludes system messages and restricts structured costs. Public fake-producer
live/archive tests prove literal secret-shaped samples and continued operational
masking; no old recordings are rewritten.

Raw archive source absence fails closed instead of substituting an operational tail.
Archive destination parents reject symlink/reparse redirection before writes; raw
outputs are exclusively created. Public missing-source and real junction/symlink
fixtures cover these boundaries through run_gate.

## Acknowledged instruction handoff

REQ-FUNC-84b2d01e / REQ-REL-c6354595 / REQ-FUNC-5942c3b1: the optional
InstructionDelivery run_gate handoff reaches run_pi_rpc on native/container targets.
Only the existing stdin queue writes; after initial prompt started success, each
tick sends new now/after records as steer/follow_up once per session, next to cancel.
Abort/timeout takes priority. Matching command/id success saves receipt; false, wrong
or missing ack leaves Queued. A matching initial prompt acknowledgement consumes only
its captured fallback; spawn/render/rejection never does. The existing stats grace
can receive late instruction responses. File-only doubles leave records queued.
The launch-owned marker, kernel liveness and literal bounded stdout archive stay intact.
Proof: instruction/fallback/cancel cases in test_pi_rpc.py; storage routes to instructions.md.

Native and executor-image guard sources are byte-identical, including the explanation
that ADORE manages publication under the project policy. The publication-blocking
patterns and project-trust refusal remain shared. Guard parity is enforced by
test_pi_installation.py::test_managed_pi_ships_the_reviewed_guard alongside the existing
fake-RPC guard command fixture (REQ-SEC-a6d32441).

## Exact private job conversation

REQ-FUNC-de494e23 / REQ-SEC-397b4a89: executor/conversation.py owns the small
schema-1 private binding, not a transcript implementation. Canonical job stems
select io/pi-conversation/session.jsonl through explicit --session/--session-dir.
Pi owns persistence and compaction. Disposable probes keep --no-session.
The existing verified target and job lock fence ownership; strict regular-file,
ancestry, header/version, JSONL chain, host IO, cwd and Pi ID checks refuse
missing/corrupt/foreign required evidence with ExecutionRecoveryError.
Compaction entries require a string summary, finite nonnegative tokensBefore
and an ancestor/self firstKeptEntryId before resume. Native temporary settings
and per-attempt credentials stay separate.

The launcher checks RPC get_state identity and a cumulative statistics baseline
before prompting. Only new assistant events enter usage and attempt recordings;
final cross-check totals subtract the baseline. Prompt acknowledgement makes
history required and persists context_key, the current ticket fingerprint.
REQ-FUNC-22de3595: the conductor uses that acknowledged fingerprint to include
changed ticket content again while omitting unchanged context on continuation.
Independent reviews remain governed by installed AEGIS policy.

Focused proof: existing test_pi_rpc.py launch parametrization covers restart,
per-attempt accounting, exact identity, corruption, hardlinks and reparse paths;
test_local_execution.py covers separate temporary settings and persistent paths
on Windows/Linux; test_prompts.py covers incremental stage instructions.

## Current contract

Both execution targets launch Pi through the current RPC process contract. Gate outcomes, cancellation, questions and archives use the owned launcher flow; REQ-FUNC-116450ef and REQ-FUNC-a71d617b cover container and native launch.
