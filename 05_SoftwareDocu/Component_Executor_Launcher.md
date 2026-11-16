# Component: Executor launcher

## Purpose and sources

`04_Software/adore/executor/base.py` defines `Executor`, `ExecTarget` and
`GateRun`. `launcher.py` implements Pi launch/archival; `pi_rpc.py` owns the
bounded RPC client; `conversation.py` checks exact private Pi session bindings. Pi is the only executor implementation. The conductor chooses
the stage and handles its result; the backend owns resource/process lifetime.

## Launch contract

`run_gate` receives the bound target, host worktree and IO paths, prompt, timeout,
archive stem and optional cancellation/instruction/secret context. It returns a
`GateRun` with authoritative exit/timeout, questions, operational output, token
availability and archive references. Job gates resume one private Pi conversation
through bounded processes. Durable workflow state remains stage authority.
The optional `context_key` pins acknowledged ticket context; a changed ticket
is supplied again until Pi acknowledges the corresponding prompt.

Both production backends use Pi RPC: container `BoundTarget.spawn` and native
`LocalTarget.pi_session`. The latter uses verified managed Node/Pi and fresh
run-owned settings. The container path uses the image's pinned Pi. Prompt text
goes over stdin, never argv. Provider/model and explicit thinking level form
validated argv; custom endpoints use generated non-secret model configuration.

`PiExecutor` directly implements `Executor`. A target must provide container
spawn or a native pi_session; callable-only targets return a failed GateRun before
file writes or command execution. There is no shell/template launch or second
JSONL usage parser. The RPC client owns completion and token accounting.

Before launch, stale output and questions are removed. A descriptive `gate.sh`
records RPC argv without executing a shell or embedding prompt/secret values.
Target paths come from `ExecutionPaths`; bound identity is checked before effects.
See [Execution](Component_Execution.md) and
[Local execution](Component_Local_Execution.md).

## Private conversation contract

Canonical stage-attempt archive stems select `io/pi-conversation/session.jsonl`
with `--session` and its explicit `--session-dir`. Non-job probes retain
`--no-session`; no launch uses personal recent-session selection. The job-owned
binding receipt pins schema 1, host IO, backend cwd, Pi session ID, required-history
status and acknowledged ticket fingerprint. It contains no credentials.

`PiConversation` validates regular files and ancestry, rejects hardlinks and
reparse/symlink redirection, and streams strict current Pi schema-3 JSONL before
resume. Compaction requires a summary, finite nonnegative prior token count and
a kept-entry reference to an ancestor or to the compaction itself. It never
repairs or imports histories. Missing binding for an already
launched job, missing required history, foreign identity and corrupt records raise
`ExecutionRecoveryError` with explicit inspect/delete-job guidance. POSIX storage is private;
Windows inherits the existing account-owned job directory controls.

RPC checks `get_state` identity and a usage baseline before sending the prompt.
Prompt acceptance makes history mandatory and saves the ticket fingerprint. Pi
owns transcript persistence and compaction; temporary native settings remain
separate and container/WSL targets use the existing IO bind mount.

## RPC completion, cancellation and usage

`run_pi_rpc` owns one process and one serialized stdin queue. It sends the initial
prompt, reads bounded complete events and completes on Pi's `agent_settled`.
Timeout/cancel sends abort, allows a bounded grace and then terminates the owned
process if necessary. The backend confirms process/container settlement before
another command. Exit 124 without the authoritative timeout flag is not a timeout.
Malformed protocol, invalid UTF-8, rejected commands or incomplete completion
cannot be treated as success.

Usage includes only new complete assistant turn reports from the current RPC
process. The final cumulative statistics cross-check subtracts the pre-prompt
baseline, so earlier stages are never re-counted. History is not requested or
replayed into attempt recordings. Usage includes input, output and
cache read/write tokens. Missing/partial evidence remains unavailable; an explicit
complete zero report remains reported. Pi's embedded costs are estimates, not
provider-reported billing, so `GateRun.cost_reported` remains false. The conductor
journals telemetry availability separately from numeric measurements.

The optional instruction handoff shares the existing queue and cancellation tick.
Live steer/follow_up is sent after initial prompt start. Matching command IDs and
successful acknowledgements confirm delivery; captured fallback instructions need
the matching prompt-start acknowledgement. Spawn, composition or outgoing
recording alone cannot mark an instruction delivered. Abort/timeout wins over
new delivery. See [Instructions](Component_Instructions.md).

## Retained files and live ownership

Current exchange lives in the run IO directory. Immutable launches use
`io/archive/<stage>-attempt-<n>-attempt1/`, with a collision suffix when needed.
Each archive retains gate description, `output.jsonl`, `stderr.log` and physical
launch metadata. Reused stems never overwrite accepted history.

For a valid stage-attempt stem, the launcher clears stale output, creates the
output file and publishes current `io/live.json` with random launch ID, planned
archive ID and start time. It holds the IO StateStore's agent-session kernel lock
through RPC and archive completion. The marker is removed on normal/exceptional
exit; a crash releases the lock. Marker presence, PID reuse or file mtime alone
cannot establish a live session. Non-job model/package probes do not advertise
job-session ownership.

Complete persisted records are flushed for live readers. Outgoing prompt,
steer and follow_up commands are recorded as adore_prompt with UTC adore_at and
instruction identity before dispatch. Pi's user echoes are omitted; other retained
complete records receive capture timestamps. These timestamps record observation,
not reconstructed earlier history.

Session stdout is literal bounded conversation evidence, including credentials
printed by an agent. Text/reasoning/tools are retained within the 16 MiB record
parse bound and 32 MiB total producer bound; deltas are omitted and oversized
records become explicit stubs/notices. Authorized web readers exclude system
messages and restrict structured costs by role. No missing earlier text is
recreated. See [Web jobs](Component_Web_Jobs.md).

Operational tails, stderr, questions, errors and normalized diagnostics have a
separate sanitized path. Known binding/package credentials and recognizable key
or Authorization values are masked there. Raw session records never become
operational tail content. Package-job retention does not rewrite the raw transcript.

Archival streams the literal recording with source size and stable file-identity
checks. Symlink/reparse/hardlinked files and unsafe archive parents are refused.
A required recording that disappeared is an archive failure, not permission to
substitute a sanitized tail as a conversation.

## Configuration, credentials and guard

`build_executor` creates `PiExecutor` with the selected provider/model, endpoint,
internet/search and thinking settings and the shared `PromptCatalog`. The native
server notice is always selected for native RPC. The offline notice applies to
internet-off container RPC; internet-on container RPC needs neither notice.
The fixed catalog is validated eagerly. See [Prompts](Component_Prompts.md).

Provider credentials enter only the explicitly bound launch environment.
ChatGPT subscription obtains a temporary access token through the trusted
server helper; refresh credentials never reach the executor's agent directory.
Token failure starts no Pi process and follows bounded conductor recovery.
Forge credentials are not injected. See [ChatGPT sign-in](Component_ChatGPT_Sign_In.md).

The native and image guard sources have identical policy text. The Pi extension
blocks publication commands in bash/PowerShell tools and refuses project trust.
This is defense in depth; native processes still have the service account's host
permissions. Container networking belongs to isolation, not the prompt or guard.

## Dependencies and validation coverage

Offline delivery includes the exact Node/Pi/web dependencies and search tools.
Online delivery omits this payload and uses the managed native installation after
separate host Node/npm setup and `pi install` with registry access.
Native jobs use the verified application-owned payload and bundled executable
directories. Container delivery images include fd/ripgrep in PATH, so an
internet-off Pi does not need a first-use tool download.

Pi 1.5.2, Node and web-extension pins are owned by `pi_installation.py` and the runtime
image assets under `04_Software/docker/`. The image verifier is
`02_Tools/build/verify_container_runtime.sh`. The launcher itself uses the shared
runner, execution target, state lock, prompt and instruction contracts.

Existing `04_Software/tests/test_executor.py`, `test_pi_rpc.py`,
`test_pi_installation.py`, `test_native_chatgpt.py`, `test_web_executor_session.py`
and `test_shared_resources.py` cover injected launch/transport failures, bounded
usage, cancellation, credentials, literal archive safety and ownership. Current
captured RPC fixtures live in `04_Software/tests/fixtures/pi_rpc/` and are shared
with session/browser fixture consumers. They do not depend on planning documents.

## Limitations

Retained evidence is bounded; truncation is explicit. Sessions are not resumed
across stages, and raw conversations may contain sensitive agent output. RPC
acknowledgement proves instruction receipt, not completed implementation. Lifecycle,
publication authority and operator cleanup remain conductor responsibilities.
