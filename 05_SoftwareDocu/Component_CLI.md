<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: CLI (`adore/cli.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/cli.py`.
> Design context: `00_Planning/ADORE_System_Overview.md`.

## 1. Purpose

The single user-facing entry point: the `adore` command. CLI-first over a
library core - the command surface is thin argparse wiring that delegates to
the `adore` package. An optional web API also exposes selected controls.

## 2. Responsibilities

- Define the full command surface (lifecycle, operations, statistics, config)
  with stdlib `argparse` only.
- Wire the phase-1 commands:
  - `adore config show` - resolved configuration as JSON;
  - `adore config validate` - all validation issues, exit 1 when any;
  - `adore config set <section.key> <value>` - edit one scalar in the resolved
    config file (comments preserved, type inferred), refusing secret-looking
    keys (except ADORE's own non-secret boolean `metrics.capture_tokens`) and writing
    only when the whole result still validates (atomic);
  - `adore status` - config health, store root, pause flag, lock holder, run
    counts by lifecycle, corrupt-run warning;
  - `adore runs` - table of persisted runs (corrupt ones shown as `CORRUPT`);
  - `adore pause` / `adore resume` - toggle the global pickup flag.
- Wire the phase-3 engine commands (all refuse to start on an invalid
  config): `adore run --loop|--once|--dry-run` (default mode from
  `[polling] mode`; `--once` prints the poll summary as JSON; all `run`
  modes also mirror their output to `<store_root>/adore.log`),
  `adore cancel <run-id>`, `adore retry <run-id>`, `adore handoff <run-id>`,
  `adore logs <run-id>`
  (journal, including executor archive paths when present), and
  `adore delete <run-id> --force` (destructive; refuses without `--force`,
  design 8c guardrail). Retry, cancel, delete, and reset acquire the
  single-conductor lock for their entire mutation; logs remain unlocked.
  Handoff queues an exact durable request when that lock is held, then the
  conductor stops at a safe boundary and preserves human-owned work. With an
  idle lock, the CLI completes the transfer directly.
- Wire the metrics commands (phase 5): `adore stats [--since 30d] [--by
  priority|outcome] [--html] [--rebuild]`, `adore report <run-id>` (live
  journal summary as JSON), `adore export --csv` (all summaries to stdout).
  Report and rebuild return an explicit error on malformed or conflicting
  versioned usage. Rebuild validates every terminal run before writing any
  refreshed summary.
- Wire the operator commands:
  - `adore reset <run-id> --to <stage> --force` - state surgery; refuses
    without `--force` (resetting may repeat orchestration work: executor cost,
    ticket churn), then tells the operator to `adore retry`. It moves only
    ADORE's pointer; AEGIS still owns the governed stage;
  - `adore profile delete <name> --force --remove-resources` - under the
    conductor lock, refuses unfinished or corrupt runs, removes the containers,
    egress resources and worktrees recorded for the project's own runs except
    human-owned ones, then
    deletes the profile and prints a JSON report (an external state root is
    kept and reported);
  - `adore cleanup` - reclaims a provably stale local instance lock and removes
    the selected project's finished and orphaned containers, proxies, networks
    and worktree directories and leaves other projects' resources in place;
    prints a JSON report.
    Corrupt runs are reported and keep their state and resources (deleting them
    is `adore delete <run-id> --force`'s explicit job).
- Wire assisted-config + profiles:
  - `adore init [name] [--force] [--answers FILE]` - the setup wizard
    (delegates to `adore.wizard`); writes a validated runtime-project profile.
  - `adore profile list|show|use|rename|delete|path` - manage profiles
    (`delete` needs `--force`; `list` shows platform/repo/runtime plus run
    stats RUNS/MERGED and last-used/uses, active marked `*`; `show` adds the
    full stats block - runs/merged/failed/success-rate/launches/tokens/
    avg-span/last-run - from the profile's metrics DB, zeros when empty).
  - global `--profile NAME` - resolve any command's config from a profile.
- **Config resolution (`_load`):** explicit `-c FILE` >
  `--profile NAME` > the active profile pointer > `./config.toml`. The
  resolved path is shown in messages, and resolving a profile records a use
  (use_count / last_used_at). Single-config users (no profile) are
  unaffected. Engine commands prefer `.env` beside that resolved config and
  fall back to cwd `.env`; process environment precedence remains in the
  orchestrator constructor.
  `run` refuses an archived named or active profile before constructing the
  engine. Explicit `-c FILE` is an independent operator config override.

Explicitly not owned: any engine behavior; the handlers are thin views over
`config`, `state`, and the orchestrator.

## 3. Implementation Overview

- Exit-code contract: `0` success, `1` error (bad/missing config, validation
  issues, refused edit).
- `_load` converts a missing config file or invalid TOML into a readable
  one-line error with a hint (copy `config.example.toml`), never a traceback.
- A held instance lock on `run --once` raises the dedicated `LockHeldError` and
  prints lock-specific guidance. Other runtime failures keep their own error
  text and never receive lock-removal advice. Cleanup only reclaims a lock whose
  local PID is provably gone; a live or unknown holder remains in place.
- `_operator_lock` protects retry/cancel/delete/reset and always releases a lock
  it acquired, including unsuccessful mutations. A live or unknown holder
  refuses the command clearly; read-only logs do not acquire the lock.
- `config set` holds the shared per-directory `config_edit_lock` through read,
  validation and replacement. A concurrent CLI or web edit fails clearly.
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

- The command surface is stable; the argument shapes fixed in
  phase 1 (`retry <run-id>`, `reset <run-id> --to <stage>`, `stats --since
  --by --html`, ...) were kept unchanged when the commands were wired.
- `cleanup` prints its report as JSON (`lock_cleared`, `lock_held_by`,
  `containers_removed`, `proxy_containers_removed`,
  `egress_networks_removed`, `worktrees_removed`, `corrupt_runs`) so wrappers
  can parse resource GC and whether a live/unknown holder was preserved.
  Active and failed run resources are protected; cancel or delete is the
  explicit release boundary for a failed run.
- Exit codes are stable and script-safe (cron / Task Scheduler wrappers can
  rely on them).

## 7. Workflow Integration

The operator's control plane: `run --loop` /
`--once` drives the engine (service mode via systemd on Ubuntu 22 or Task
Scheduler on Windows 11); `cancel`/`retry`/`reset`/`delete` are the manual
overrides; `cleanup` is the recovery tool after crashes or the WSL
bind-mount teardown race; `stats`/`report`/`export` read the metrics store.
The intervention commands mutate ADORE-owned state only: they do not edit
AEGIS payload files or executor-owned task journals. Stop the service poller
before an intervention command; `pause` stops pickup but does not release the
process lock.

## 8. Usage

```bash
adore --version
adore -c config.toml config validate   # run before starting the loop
adore config show
adore status
adore runs
adore pause && adore resume
adore reset adore-gitlab-g-p-14 --to validate --force  # then: adore retry <run-id>
adore cleanup                                       # after a crash / husk dirs

adore init <profile-name>              # assisted setup -> a profile
adore profile list                     # profiles with dates + use counts
adore profile use <profile-name>       # make it the active profile
adore --profile <profile-name> run --dry-run   # any command against a profile
```

## 9. Validation And Tests

- `tests/test_smoke.py` drives `main()` end-to-end against real config files
  in a tmp dir: validate OK / with issues, missing config file, invalid TOML,
  status/pause/resume/runs together, corrupt runs surfaced, stats/export on
  an empty store, reset refusing without `--force` and failing cleanly on an
  unknown run, cleanup printing its JSON report, `run --once` writing
  `<store_root>/adore.log`, process-log rotation, and `config set`
  (existing-key edit with comment preservation, missing-section append,
  invalid-result refusal, secret-key rejection, bad-key/missing-value).
- `tests/test_smoke.py` also proves every operator mutation refuses a live lock,
  acquires/releases a free lock, leaves logs unlocked, and limits stale-lock
  advice to `LockHeldError` rather than unrelated runtime failures.
- `tests/test_orchestrator.py` covers the engine side of `reset` (stage set +
  journaled, invalid stage/run refused, retry continues from the reset
  stage) and `cleanup` (stale lock cleared, this project's orphans removed,
  other projects' resources kept, active, failed, human-owned and corrupt runs
  protected).
- Minimum validation after a change: `uv run --group dev pytest tests/test_smoke.py`
  and `uv run adore -c config.example.toml config validate`.

## 10. Limitations And Future Work

- `adore run --once --ticket IID` requests one specific ready ticket. The
  normal hold/exclude/readiness checks still apply; a missing or ineligible
  ticket returns an error. The web worker uses this entry point for Start.

- `adore config set` edits one scalar at a time and infers the value type from
  the text; it does not set arrays/tables or change a value's declared type on
  purpose. Comments on the edited line are kept via a quote-aware heuristic.
- No `--json` output mode for `status`/`runs` yet; add when scripting needs
  it.
