<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-8f369d55 - Prove a shell tool call in the local Test AI connection

Also governs REQ-FUNC-0b728218 (tool-call-failed).

## Behavior

Applies to native local profiles whose default executor is `opencode`, `pi` or `codex`.
Qwen local profiles and every container profile keep the no-tool challenge.

1. ADORE creates two independent nonces: `ADORE_TOOL_<32 hex>` and `ADORE_OK_<32 hex>`.
2. It runs one executor gate through `local_probe` with the configured command and the
   prompt: `Connection test. Run this shell command exactly once: echo <tool nonce>.
   Then reply with exactly: <reply nonce>`. The gate timeout is 90 seconds.
3. The result reason is decided in this order:
   - gate timed out -> `timeout`;
   - executor exit code non-zero -> `connection-failed`;
   - output not parseable as the executor's JSON event stream -> `invalid-response`;
   - no successful shell call carrying the tool nonce (see below) -> `tool-call-failed`;
   - final reply not exactly the reply nonce, or the run not completed -> `invalid-response`;
   - otherwise `ready`.

## Data / interface

Successful shell call and completed reply, per executor (bounded, redacted stdout,
one JSON object per line):

| Executor | Successful shell call | Completed final reply |
|---|---|---|
| OpenCode | `type=tool_use`, `part.tool=bash`, `part.state.status=completed`, `part.state.output` contains the tool nonce | a `type=text` event whose `part.text` stripped equals the reply nonce, and a `type=step_finish` with `part.reason=stop` |
| Pi | `type=tool_execution_end`, `toolName=bash`, `isError=false`, the text of `result.content[]` contains the tool nonce | the last `type=message_end` whose `message.role=assistant` has `stopReason=stop` and its text parts joined and stripped equal the reply nonce |
| Codex | `type=item.completed`, `item.type=command_execution`, `item.status=completed`, `item.exit_code=0`, `item.aggregated_output` contains the tool nonce | the last `item.completed` with `item.type=agent_message` has `item.text` stripped equal to the reply nonce, and a `type=turn.completed` event exists |

Any other tool events (reads, extra commands) do not fail the result. A tool event
whose status is error or rejected, `isError=true`, a failed status or a non-zero exit
code is not a successful shell call.

## Edge cases

- The tool nonce appearing only in the reply text is not a shell call.
- Shell output may end with `\n` or `\r\n` (PowerShell on Windows).
- An intermediate assistant message before the tool call (Codex) is ignored; only the
  last agent message is the reply.
- Evidence keeps the closed record `{executor, model, ready, reason, ...}`; the new
  reason value is `tool-call-failed`.
