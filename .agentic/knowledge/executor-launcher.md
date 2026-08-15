<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Executor launcher

## Purpose

`04_Software/adore/executor/` launches one bounded executor gate inside an
already-provisioned container. It is an executor-neutral transport and result
collector; the orchestrator decides which stage to run and what an outcome
means.

## Public interface

- `build_executor(kind, command_template, model, questions_file)` selects the
  `opencode`, `pi`, `codex`, or `qwen` implementation.
- `FileProtocolExecutor.run_gate(...)` accepts an injected container-exec seam,
  worktree/io paths, prompt, timeout, optional session, and archive stem; it
  returns a typed `GateRun`.
- `GateRun` reports exit status, typed `timed_out`, session id, questions,
  bounded output, usage, and archive information.

## Contract and safety boundary

The launcher writes LF-only `gate.sh` into the run IO directory and invokes
only `sh /adore/io/gate.sh`; prompts and models are shell-quoted before they
enter that script. Results cross the container boundary through `output.jsonl`,
`stderr.log`, and the configured questions file rather than fragile host/WSL
argv or streamed output. A timeout is taken solely from `CommandResult.timed_out`,
not guessed from exit text. Each requested archive is immutable under
`io/archive/`, so a retry cannot destroy prior evidence.

The executor receives no forge credentials and cannot publish. Unsafe
auto-approval flags are rejected by configuration validation. The launcher
may retry a known dead session once, but never after a typed timeout.

## Requirement coverage

- `REQ-FUNC-59ccdb74` - WSL-safe file transport and typed timeout propagation.
- `REQ-FUNC-c6e5282d` - questions parking and immutable launch archives.

## Dependencies and verification

It depends on the container `ExecTarget`, `adore.util.CommandResult`, executor
configuration, and mount paths supplied by isolation/branding. Offline
coverage is in `04_Software/tests/test_executor.py`, including hostile prompt
quoting, session continuation, questions, archives, missing output, rejected
flags, and timeout propagation.
