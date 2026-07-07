<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Process Log (`ador/process_log.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/ador/process_log.py` - file version 0.1.0.
> Design: unattended run auditability for `ador run`.

## 1. Purpose

Persist ADOR's own `run` command output to a rotating process log while
preserving the existing stdout behavior. This gives Task Scheduler,
systemd, and repeated `run --once` invocations an ADOR-owned audit trail even
when the host scheduler does not retain console output.

## 2. Responsibilities

- Provide the fixed process-log location: `<store_root>/ador.log`.
- Append timestamped UTF-8 lines with size-based rotation.
- Keep rotation defaults fixed in code: 1 MiB current log, five backups.
- Tee `ador run` messages to stdout and disk through `ProcessLogger.emit`.

Explicitly not owned: executor event streams, per-gate artifacts, structured
run journal events, OS scheduler logging, or any new configuration surface.

## 3. Implementation Overview

- `process_log_path(store_root)` resolves the log path from the configured
  state store root.
- `ProcessLogger.emit(line)` prints the line and then appends the same line
  to disk.
- `ProcessLogger.append(line)` writes a timestamped line and rotates before
  appending when the current log plus the incoming record would exceed the
  configured byte limit.
- Rotation keeps the newest backup at `ador.log.1`, shifts older backups up,
  and removes anything beyond the backup count.

The logger opens and closes the file per line so short-lived `run --once`
processes do not need an explicit flush or close lifecycle.

## 4. Dependencies

- Internal: `ador.util.utc_now_iso`.
- External: Python standard library only (`pathlib`).

## 5. Inputs And Outputs

- Inputs: a store root, log path, and text lines from the CLI or tests.
- Outputs: timestamped records in `<store_root>/ador.log`; rotated backups
  named `ador.log.1` through `ador.log.5`.

## 6. Data Contracts

- Current log file: `ador.log`.
- Maximum current log size: `1_048_576` bytes.
- Retained backups: `5`.
- Encoding: UTF-8.
- Record format: `<utc-timestamp> <line>\n`.

Append failures are ordinary filesystem exceptions. For `ador run`, that
means the command fails visibly instead of pretending unattended logs were
persisted when the store root cannot be written.

## 7. Workflow Integration

`ador.cli._cmd_run` wraps the orchestrator logger with `ProcessLogger.emit`
for `run --loop`, `run --once`, and `run --dry-run`. Other CLI commands keep
their previous stdout-only behavior.

## 8. Usage

```python
from ador.process_log import ProcessLogger, process_log_path

logger = ProcessLogger(process_log_path(".ador"))
logger.emit('{"picked": 0}')
```

## 9. Validation And Tests

- `tests/test_smoke.py` proves `ador run --once` writes `<store_root>/ador.log`
  while preserving stdout.
- `tests/test_smoke.py` also covers size-based rotation and backup retention.
- Minimum validation after a change: `uv run --group dev pytest tests/test_smoke.py`.

## 10. Limitations And Future Work

- There is intentionally no config section for process-log size, path, or
  backup count. Add configuration only if operators need different retention
  after real unattended use.
