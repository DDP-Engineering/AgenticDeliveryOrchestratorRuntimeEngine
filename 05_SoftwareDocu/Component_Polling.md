<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Polling cadence

## 1. Purpose

`adore.polling.PollCadence` owns common interval, error backoff and jitter
calculation for `Orchestrator.run_loop` and `CommandWorker.run_forever`.

## 2. Responsibilities and contract

`validate(PollingConfig)` rejects non-integer/boolean intervals or jitter,
nonpositive intervals, negative jitter and non-boolean backoff with ValueError.
`next_delay(config, failed=...)` returns seconds. True doubles the error
multiplier to at most 8; False resets it to 1; None retains it for a quiet round.
Disabling backoff immediately resets 1. Uniform 0..jitter is added after
multiplication. Invalid outcomes raise ValueError. Configuration keys/defaults
and persisted state are owned by existing components.

## 3. Dependencies and integration

Standard-library random and config.PollingConfig. Each CLI loop owns one instance;
the web worker owns one per immutable project identity. Callers evaluate quiet
hours and wait only after completion; policy performs no I/O, sleeps or execution.
No persistence or migration; restart begins with multiplier 1.

## 9. Validation

Offline worker/CLI tests in test_web_commands.py and test_orchestrator.py observe
actual scheduled invocations, bounded/disabled backoff, jitter endpoints, quiet
retention, malformed configuration/outcomes, independent projects and slow passes.
