<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: CLI (`adore/cli.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/cli.py` - file version 0.5.0.
> Design: Orchestrator_Design_And_Decisions.md section 12a;
> Assisted_Config_And_Profiles_Plan.md (init / profile / --profile).

## 1. Purpose

The single user-facing entry point: the `adore` command. CLI-first over a
library core - the command surface is thin argparse wiring that delegates to
the `adore` package; no REST API or web UI exists in v1 by design.

## 2. Responsibilities

- Define the full command surface (lifecycle, operations, statistics, config)
  with stdlib `argparse` only.
- Wire the phase-1 commands:
  - `adore config show` - resolved configuration as JSON;
  - `adore config validate` - all validation issues, exit 1 when any;
  - `adore status` - config health, store root, pause flag, lock holder, run
    counts by lifecycle, corrupt-run warning;
  - `adore runs` - table of persisted runs (corrupt ones shown as `CORRUPT`);
  - `adore pause` / `adore resume` - toggle the global pickup flag.
- Wire the phase-3 engine commands (all refuse to start on an invalid
  config): `adore run --loop|--once|--dry-run` (default mode from
  `[polling] mode`; `--once` prints the poll summary as JSON; all `run`
  modes also mirror their output to `<store_root>/adore.log`),
  `adore cancel <run-id>`, `adore retry <run-id>`, `adore logs <run-id>`
  (journal, including executor archive paths when present), and
  `adore delete <run-id> --force` (destructive; refuses without `--force`,
  design 8c guardrail).
- Wire the metrics commands (phase 5): `adore stats [--since 30d] [--by
  priority|outcome] [--html] [--rebuild]`, `adore report <run-id>` (live
  journal summary as JSON), `adore export --csv` (all summaries to stdout).
- Wire the operator commands (design 8c):
  - `adore reset <run-id> --to <stage> --force` - state surgery; refuses
    without `--force` (resetting re-runs completed gates: executor cost,
    ticket churn), then tells the operator to `adore retry`;
  - `adore cleanup` - sweeps the stale instance lock, orphaned containers,
    and orphaned/husk worktree directories; prints a JSON report. Corrupt
    run state is reported but never auto-deleted (that is `adore delete
    <run-id> --force`'s explicit job).
- Wire assisted-config + profiles (Assisted_Config_And_Profiles_Plan):
  - `adore init [name] [--force] [--answers FILE]` - the setup wizard
    (delegates to `adore.wizard`); writes a validated runtime-project profile.
  - `adore profile list|show|use|rename|delete|path` - manage profiles
    (`delete` needs `--force`; `list` shows platform/repo/runtime plus run
    stats RUNS/MERGED and last-used/uses, active marked `*`; `show` adds the
    full stats block - runs/merged/failed/success-rate/launches/tokens/
    avg-span/last-run - from the profile's metrics DB, zeros when empty).
  - global `--profile NAME` - resolve any command's config from a profile.
- **Config resolution (`_load`, decision D3):** explicit `-c FILE` >
  `--profile NAME` > the active profile pointer > `./config.toml`. The
  resolved path is shown in messages, and resolving a profile records a use
  (use_count / last_used_at). Single-config users (no profile) are
  unaffected.

Explicitly not owned: any engine behavior; the handlers are thin views over
`config`, `state`, and the orchestrator.

## 3. Implementation Overview

- Exit-code contract: `0` success, `1` error (bad/missing config, validation
  issues), `2` not implemented.
- `_load` converts a missing config file or invalid TOML into a readable
  one-line error with a hint (copy `config.example.toml`), never a traceback.
- A held/stale instance lock on `run --once` prints the lock path and a
  removal hint instead of a traceback; `adore cleanup` clears it (invoking
  cleanup asserts no poller is running).
- `_cmd_run` wraps the engine logger with `ProcessLogger`, so engine log
  lines and the final `--once` / `--dry-run` JSON summary are both printed to
  stdout and appended to `<store_root>/adore.log`. Other commands remain
  stdout-only.
- `_store` builds the `StateStore` from `[state] store_root` + `[agent] slug`.
- Corrupt runs (from `StateStore.invalid_runs()`) are surfaced in both
  `status` and `runs` so damaged state is visible, not hidden.
- Entry points: the `adore` console script (`pyproject.toml`) and
  `python -m adore` (`__main__.py`), both calling `cli.main`.

## 4. Dependencies

- Internal: `adore.config` (load/validate), `adore.state` (`StateStore`),
  `adore.orchestrator` (engine commands), `adore.process_log` (run command
  tee + rotation), `adore.metrics` (stats/report/export), `adore.profiles`
  (`ProfileStore`, `resolve_config_path`), `adore.wizard` (`run_wizard`,
  askers), `adore.util` (`parse_duration`), `adore.__version__`.
- External: Python standard library only (`argparse`, `json`, `tomllib`,
  `dataclasses`, `contextlib`).

## 5. Inputs And Outputs

- Inputs: argv; `-c/--config` (default resolves to `./config.toml`);
  `--profile NAME`; the active-profile pointer under the ADORE config home.
- Outputs: stdout text (human-oriented; `config show` prints JSON), the
  process exit code, `run` command process-log lines under `<store_root>`,
  pause-flag changes, and profile creation/edits under the ADORE config home.

## 6. Data Contracts

- The command surface matches design doc 12a; the argument shapes fixed in
  phase 1 (`retry <run-id>`, `reset <run-id> --to <gate>`, `stats --since
  --by --html`, ...) were kept unchanged when the commands were wired.
- `cleanup` prints its report as JSON (`lock_cleared`, `containers_removed`,
  `worktrees_removed`, `corrupt_runs`) so wrappers can parse it.
- Exit codes are stable and script-safe (cron / Task Scheduler wrappers can
  rely on them).

## 7. Workflow Integration

The operator's control plane (design 8c), now complete: `run --loop` /
`--once` drives the engine (service mode via systemd on Ubuntu 22 or Task
Scheduler on Windows 11); `cancel`/`retry`/`reset`/`delete` are the manual
overrides; `cleanup` is the recovery tool after crashes or the WSL
bind-mount teardown race; `stats`/`report`/`export` read the metrics store.

## 8. Usage

```bash
adore --version
adore -c config.toml config validate   # run before starting the loop
adore config show
adore status
adore runs
adore pause && adore resume
adore reset adore-gitlab-g-p-14 --to check --force   # then: adore retry <run-id>
adore cleanup                                       # after a crash / husk dirs

adore init sample-project              # assisted setup -> a profile
adore profile list                     # profiles with dates + use counts
adore profile use sample-project       # make it the active profile
adore --profile sample-project run --dry-run   # any command against a profile
```

## 9. Validation And Tests

- `tests/test_smoke.py` drives `main()` end-to-end against real config files
  in a tmp dir: validate OK / with issues, missing config file, invalid TOML,
  status/pause/resume/runs together, corrupt runs surfaced, stats/export on
  an empty store, reset refusing without `--force` and failing cleanly on an
  unknown run, cleanup printing its JSON report, `run --once` writing
  `<store_root>/adore.log`, process-log rotation, and the one remaining stub
  (`config set`) exiting 2.
- `tests/test_orchestrator.py` covers the engine side of `reset` (stage set +
  journaled, invalid stage/run refused, retry continues from the reset
  stage) and `cleanup` (stale lock cleared, orphans swept, active runs and
  corrupt state untouched).
- Minimum validation after a change: `uv run --group dev pytest tests/test_smoke.py`
  and `uv run adore -c config.example.toml config validate`.

## 10. Limitations And Future Work

- `adore config set` is not implemented (edit `config.toml` directly) - the
  only remaining stub.
- No `--json` output mode for `status`/`runs` yet; add when scripting needs
  it.
