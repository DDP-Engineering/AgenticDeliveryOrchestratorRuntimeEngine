<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Util (`adore/util.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/util.py` - file version 0.2.0.

## 1. Purpose

Shared low-level helpers every other ADORE component builds on: running
external commands safely, parsing human-readable durations, and producing
consistent UTC timestamps. It exists so that shelling out (glab, gh, git,
docker, the executor CLI) happens in exactly one place with one error model.

## 2. Responsibilities

- Run external commands without a shell, capturing all output
  (`run_command`).
- Define the injectable `CommandRunner` protocol so every consumer can be
  unit-tested offline with a fake runner.
- Parse duration strings ("90s", "30m", "24h", "7d", bare seconds) to
  seconds (`parse_duration`).
- Produce compact UTC ISO-8601 timestamps (`utc_now_iso`) and parse them
  back to aware datetimes (`iso_to_datetime`).
- Evaluate `[polling] quiet_hours` windows, including windows crossing
  midnight (`in_quiet_hours`).
- Load dotenv-style secret files (`load_env_file`; missing file = `{}`).
- Remove directory trees that contain read-only entries
  (`force_rmtree` - Windows git objects are read-only and plain
  `shutil.rmtree` fails on them; missing paths are fine, so teardown and
  `adore cleanup` stay idempotent).

Explicitly not owned: interpreting command output (each caller parses its own
JSON/URLs) and retry/backoff policy (the orchestrator's concern).

## 3. Implementation Overview

- `CommandResult` (dataclass): argv, exit_code, stdout, stderr, `ok` property.
- `CommandRunner` (Protocol): the callable contract; `run_command` is the
  concrete default, tests inject fakes.
- `run_command` never raises for command failure - errors are reported
  through the exit code so callers decide deterministically:
  - `127` - executable not found,
  - `124` - wall-clock timeout (subprocess killed),
  - otherwise the command's own exit code.
- Output is always **captured**, never streamed: the prerequisites check
  showed opencode buffers stdout, so naive streaming looks "hung"
  Output is decoded as UTF-8 with
  replacement to survive Windows console encodings.
- Default command timeout: 600 s (`DEFAULT_COMMAND_TIMEOUT`).

## 4. Dependencies

- Internal: none (lowest layer).
- External: Python standard library only (`subprocess`, `re`, `datetime`).

## 5. Inputs And Outputs

- Inputs: an argv list (no shell), optional cwd/timeout/env; duration strings.
- Outputs: `CommandResult` values; integer seconds; timestamp strings like
  `2026-07-02T14:02:33Z`.

## 6. Data Contracts

- Exit-code convention (127 missing binary / 124 timeout / native otherwise)
  is relied upon by the forge adapters and, later, the executor launcher and
  isolation helpers.
- `parse_duration` raises `ValueError` on anything unparseable; config
  validation depends on that.

## 7. Workflow Integration

Bottom of the dependency graph: `config` uses `parse_duration`; `state` uses
`utc_now_iso`; the forge adapters (and later the executor launcher and
isolation) run everything through a `CommandRunner`.

## 8. Usage

```python
from adore.util import run_command, parse_duration

result = run_command(["glab", "issue", "list", "--output", "json"])
if result.ok:
    ...
seconds = parse_duration("24h")  # 86400
```

## 9. Validation And Tests

- `tests/test_util.py`: duration units and garbage rejection, output capture,
  missing binary -> 127, hung command -> 124, timestamp shape.
- Minimum validation after a change: `uv run --group dev pytest tests/test_util.py`.

## 10. Limitations And Future Work

- No retry/backoff wrapper yet; the poll loop will add it where needed.
- No streaming mode; if a later phase needs live progress, add an explicit
  file-tail mechanism rather than reading process stdout.
