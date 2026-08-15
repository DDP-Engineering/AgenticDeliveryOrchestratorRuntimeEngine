<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Utilities

## Purpose

Provides injectable, shell-free command execution, duration parsing, UTC
timestamps, bounded output helpers, and reparse-point-safe cleanup support.

## Public contract

`run_command()` takes an argv sequence and returns `CommandResult`, preserving
stdout, stderr, exit code, duration, and the authoritative timeout flag.
Helpers parse configuration durations, normalize UTC timestamps, bound external
text/bytes, and remove only an explicitly selected tree without following
Windows reparse points.

## Key behaviors

- `CommandResult.timed_out` is set only when ADORE's wrapper kills a process.
- Callers must not infer timeout from exit code or stderr wording.
- External command failures return data so higher layers choose recovery.
- Boundary helpers reject malformed or oversized external data rather than
  silently truncating decision values.

## Requirement coverage

- `REQ-FUNC-1aa7a007` - authoritative typed timeout result.
- `REQ-FUNC-2613bf7d` - shell-free command execution and duration parsing.

## Files

- `04_Software/adore/util.py`
- `04_Software/tests/test_util.py`
