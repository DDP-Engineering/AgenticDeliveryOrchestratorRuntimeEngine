<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-8f369d55 - Prove a shell tool call in the local Test AI connection

Also governs REQ-FUNC-0b728218 (tool-call-failed).

## Behavior

Applies to native local profiles, which run the installed Pi.
Every container profile keeps the no-tool challenge.

1. ADORE creates two independent nonces: `ADORE_TOOL_<32 hex>` and `ADORE_OK_<32 hex>`.
2. It runs one managed Pi RPC challenge through `local_probe` with the
   prompt: `Connection test. Run this shell command exactly once: echo <tool nonce>.
   Then reply with exactly: <reply nonce>`. The gate timeout is 90 seconds.
3. The result reason is decided in this order:
   - gate timed out -> `timeout`;
   - executor exit code non-zero -> `connection-failed`;
   - output not parseable as Pi's JSON event stream -> `invalid-response`;
   - no successful shell call carrying the tool nonce (see below) -> `tool-call-failed`;
   - final reply not exactly the reply nonce, or the run not completed -> `invalid-response`;
   - otherwise `ready`.

## Data / interface

Successful shell call and completed reply in Pi's JSON event stream (bounded,
redacted stdout, one JSON object per line), decided by
`_native_tool_response(output, tool_nonce, nonce)`:

| Successful shell call | Completed final reply |
|---|---|
| `type=tool_execution_end`, `toolName=bash`, `isError=false`, the text of `result.content[]` contains the tool nonce | the last `type=message_end` whose `message.role=assistant` has `stopReason=stop` and its text parts joined and stripped equal the reply nonce |

Any other tool events (reads, extra commands) do not fail the result. A tool event
with `isError=true` is not a successful shell call.

## Edge cases

- The tool nonce appearing only in the reply text is not a shell call.
- Shell output may end with `\n` or `\r\n` (PowerShell on Windows).
- An intermediate assistant message before the tool call is ignored; only the
  last assistant message is the reply.
- Evidence keeps the closed record `{executor, model, ready, reason, ...}`; the new
  reason value is `tool-call-failed`.
