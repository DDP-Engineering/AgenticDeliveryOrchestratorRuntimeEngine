<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: CLI (`ador/cli.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/ador/cli.py` - file version 0.1.0.
> Design: Orchestrator_Design_And_Decisions.md section 12a.

## 1. Purpose

The single user-facing entry point: the `ador` command. CLI-first over a
library core - the command surface is thin argparse wiring that delegates to
the `ador` package; no REST API or web UI exists in v1 by design.

## 2. Responsibilities

- Define the full command surface (lifecycle, operations, statistics, config)
  with stdlib `argparse` only.
- Wire the phase-1 commands:
  - `ador config show` - resolved configuration as JSON;
  - `ador config validate` - all validation issues, exit 1 when any;
  - `ador status` - config health, store root, pause flag, lock holder, run
    counts by lifecycle, corrupt-run warning;
  - `ador runs` - table of persisted runs (corrupt ones shown as `CORRUPT`);
  - `ador pause` / `ador resume` - toggle the global pickup flag.
- Wire the phase-3 engine commands (all refuse to start on an invalid
  config): `ador run --loop|--once|--dry-run` (default mode from
  `[polling] mode`; `--once` prints the poll summary as JSON),
  `ador cancel <run-id>`, `ador retry <run-id>`, `ador logs <run-id>`
  (journal), and `ador delete <run-id> --force` (destructive; refuses
  without `--force`, design 8c guardrail).
- Report the remaining phase-4 commands (`reset`, `stats`, `report`,
  `export`, `cleanup`) with a clear message and exit code 2 - never a
  traceback.

Explicitly not owned: any engine behavior; the handlers are thin views over
`config`, `state`, and the orchestrator.

## 3. Implementation Overview

- Exit-code contract: `0` success, `1` error (bad/missing config, validation
  issues), `2` not implemented.
- `_load` converts a missing config file or invalid TOML into a readable
  one-line error with a hint (copy `config.example.toml`), never a traceback.
- A held/stale instance lock on `run --once` prints the lock path and a
  removal hint instead of a traceback (automatic stale-lock cleanup belongs
  to the pending `ador cleanup`).
- `_store` builds the `StateStore` from `[state] store_root` + `[agent] slug`.
- Corrupt runs (from `StateStore.invalid_runs()`) are surfaced in both
  `status` and `runs` so damaged state is visible, not hidden.
- Entry points: the `ador` console script (`pyproject.toml`) and
  `python -m ador` (`__main__.py`), both calling `cli.main`.

## 4. Dependencies

- Internal: `ador.config` (load/validate), `ador.state` (`StateStore`),
  `ador.__version__`.
- External: Python standard library only (`argparse`, `json`, `tomllib`).

## 5. Inputs And Outputs

- Inputs: argv; `-c/--config` (default `config.toml`).
- Outputs: stdout text (human-oriented; `config show` prints JSON), the
  process exit code, and pause-flag changes in the state store.

## 6. Data Contracts

- The command surface matches design doc 12a; engine commands keep their
  final argument shapes now (`retry <run-id>`, `reset <run-id> --to <gate>`,
  `stats --since --by --html`, ...) so wiring them later changes no UX.
- Exit codes are stable and script-safe (cron / Task Scheduler wrappers can
  rely on them).

## 7. Workflow Integration

The operator's control plane (design 8c): today it inspects and pauses; the
later phases plug the orchestrator into `run --loop` / `--once` (service mode
via systemd on Ubuntu 22 or Task Scheduler on Windows 11) and the manual
override commands into the same handlers.

## 8. Usage

```bash
ador --version
ador -c config.toml config validate   # run before starting the loop
ador config show
ador status
ador runs
ador pause && ador resume
```

## 9. Validation And Tests

- `tests/test_smoke.py` drives `main()` end-to-end against real config files
  in a tmp dir: validate OK / with issues, missing config file, invalid TOML,
  status/pause/resume/runs together, corrupt runs surfaced, engine commands
  exiting 2.
- Minimum validation after a change: `uv run --group dev pytest tests/test_smoke.py`
  and `uv run ador -c config.example.toml config validate`.

## 10. Limitations And Future Work

- `ador config set` is not implemented (edit `config.toml` directly).
- Engine commands are placeholders until their phases land.
- No `--json` output mode for `status`/`runs` yet; add when scripting needs
  it.
