<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Process log

## Routing

Use for stdout mirroring, admission diagnostics, per-run conductor logs and rotation.
Start at `04_Software/adore/process_log.py`; verify with smoke log cases and
`04_Software/tests/test_shared_resources.py`. Executor evidence belongs to executor-launcher.md.

## Purpose and boundaries

`04_Software/adore/process_log.py` preserves ADORE's own unattended `run`
output in a small rotating log while retaining the normal stdout stream. It is
the scheduler-facing record when Task Scheduler, systemd, or a short
`run --once` invocation does not keep console history.

## Public interface

`process_log_path(store_root)` fixes the location at `<store_root>/adore.log`.
`ProcessLogger.emit()` prints then appends a UTC timestamped UTF-8 record;
`append()` rotates before exceeding the current-file limit. Rotation keeps the
current log plus five numbered backups and has no separate configuration
surface. Each write opens/closes the file, which makes short commands durable
without a flush lifecycle.

Logging failure is visible: ADORE must not claim an unattended audit record was
written when its state root is unavailable. This component does not own executor
streams, stage journals, or OS scheduler logs.

## Key behaviors

- `REQ-FUNC-d9453193` - stdout-preserving bounded process-log rotation.

## Verification

The CLI wraps `run --loop`, `run --once`, and `run --dry-run` with this logger.
`04_Software/tests/test_smoke.py` covers stdout preservation, log creation,
size rotation, and backup retention.


## Diagnostic and lifecycle boundaries

Concurrent append/rotation uses the shared resource lock. `adore conduct` has its
own `<run-dir>/adore.log`, so diagnostics stay attributed to the owned run.
Focused proof: `tests/test_shared_resources.py` plus smoke process-log tests.
The component documentation is `05_SoftwareDocu/Component_Process_Log.md`.


## Invariants

Each line and its rotation serialize together. Lock failure remains visible as
OSError; process logs do not replace authoritative per-run journals.

## Files

- `04_Software/adore/process_log.py`: bounded log and rotation ownership.
- `04_Software/adore/cli.py`: project admission/per-run conductor routing.
- `04_Software/tests/test_smoke.py`: existing log contracts.
- `04_Software/tests/test_shared_resources.py`: concurrent rotation and attribution.
