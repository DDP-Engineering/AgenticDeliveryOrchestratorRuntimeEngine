<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE CLI Reference

The ADORE command-line interface is available as `adore` after installation or
as `python -m adore` in a Python environment that contains the package.

```text
adore [--version] [-c FILE | --profile NAME] <command> [options]
```

Use `adore --help` or `adore <command> --help` for parser-provided help.

## Configuration Selection

Commands that operate on a runtime project resolve configuration in this order:

1. `-c FILE` or `--config FILE`;
2. `--profile NAME`;
3. the active profile selected by `adore profile use <profile-name>`;
4. `./config.toml` in the current working directory.

Use `--profile` in automation and first-run commands. It is unambiguous and
does not rely on the shell's working directory or a previous active-profile
choice.
An archived named or active profile refuses `run` pickup until restored in
the web Projects page. An explicit `-c FILE` is outside profile archive
control and remains an operator override.

For engine commands (`run`, `retry`, `cancel`, `delete`, `reset`, and
`cleanup`), ADORE loads `.env` beside the resolved `config.toml` when it
exists; otherwise it falls back to `./.env`. Values already present in the
process environment take precedence. Only names listed in `executor.env_keys`
are passed into the executor container, and forge authentication remains the
responsibility of the host `gh`, `glab`, or `tea` CLI.

## Setup and Profiles

| Command | Purpose |
| --- | --- |
| `adore init [<profile-name>] [--force] [--answers <answers.toml>]` | Run guided setup for a runtime-project profile. `--force` replaces an existing profile. `--answers` enables non-interactive setup. |
| `adore profile list` | List profiles and identify the active one. |
| `adore profile show <profile-name>` | Show profile metadata, configuration path, and profile metrics summary. |
| `adore profile use <profile-name>` | Make a profile the interactive default. |
| `adore profile rename <old-name> <new-name>` | Rename a profile and update the active pointer when necessary. |
| `adore profile delete <profile-name> --force` | Irreversibly delete a profile and its state. |
| `adore profile path [<profile-name>]` | Print the profile's `config.toml` path; without a name, use the active profile. |

Profile homes are `%APPDATA%\adore` on Windows and `~/.config/adore` on Linux,
unless `ADORE_HOME` overrides the location.

## Configuration Commands

| Command | Purpose |
| --- | --- |
| `adore [selector] config show` | Print the resolved configuration as JSON. |
| `adore [selector] config validate` | Validate the resolved configuration and report any issues. |
| `adore [selector] config set <section.key> <value>` | Set one scalar key in the resolved config file (e.g. `budgets.max_iterations 12`). Comments are preserved and the value type is inferred; the write is refused unless the whole resulting config still validates. Secret-looking keys are rejected - put secrets in `.env`. CLI and web edits share a local process lock; a concurrent edit is refused. |

In this table, `[selector]` means `-c <config.toml>` or `--profile
<profile-name>` where appropriate.

## Running and Monitoring

| Command | Purpose |
| --- | --- |
| `adore [selector] run --dry-run` | Show ticket selection and intended actions without delivery side effects. |
| `adore [selector] run --once` | Run one poll pass. |
| `adore [selector] run --loop` | Run continuously until interrupted. |
| `adore [selector] status` | Show configuration, pause, lock, and run-state summary. |
| `adore [selector] runs` | List active, parked, and review runs. |
| `adore [selector] logs <run-id>` | Show a run's structured journal. |
| `adore [selector] pause` | Stop new ticket pickup without cancelling in-flight runs. |
| `adore [selector] resume` | Allow new ticket pickup again. |

When no run-mode flag is supplied, the runtime uses `[polling] mode` from the
resolved configuration.

## Run Intervention and Cleanup

| Command | Purpose |
| --- | --- |
| `adore [selector] retry <run-id>` | Re-arm a retryable run. |
| `adore [selector] cancel <run-id>` | Cancel a run gracefully. |
| `adore [selector] reset <run-id> --to <stage> --force` | Deliberately move ADORE's own pointer to `frame`, `specify`, `design`, `build`, `validate`, `deliver`, or `publishing`. It never edits the AEGIS task journal; conduction rereads that journal. `--force` is required. Run `retry` afterwards. |
| `adore [selector] delete <run-id> --force` | Irreversibly remove run state. |
| `adore [selector] cleanup` | Reclaim a provably stale local lock and sweep orphan executor/proxy containers, egress networks, and worktree husks. Active and failed runs are protected; a live/unknown lock remains held and is reported. |

Read [Recovery_And_Maintenance.md](Recovery_And_Maintenance.md) before using a
destructive command.

These intervention commands mutate ADORE-owned state only. None edits an AEGIS
task journal. `retry` resets the current stage counter and active-work clock but
preserves task/failure history, and refuses to run while a required notification
remains pending.

Failed-run resources are released only by explicit `cancel <run-id>` (audit
state retained) or `delete <run-id> --force` (state removed irreversibly), not
by routine cleanup.

`retry`, `cancel`, `delete`, and `reset` hold the single-conductor lock for the
entire mutation and refuse when a live or unknown holder owns it. Stop the
service poller first; `pause` does not release its process lock. Read-only
`logs` remains available while the lock is held. `run --once` prints lock
guidance only for actual lock contention; other runtime errors retain their own
diagnostic.

## Metrics and Reports

| Command | Purpose |
| --- | --- |
| `adore [selector] stats [--since <duration>] [--by priority|outcome]` | Summarize terminal-run metrics. |
| `adore [selector] stats --html` | Write the configured static HTML dashboard. |
| `adore [selector] stats --rebuild` | Re-summarize terminal runs into the metrics database. Re-running is idempotent and leaves run state and journals unchanged. |
| `adore [selector] report <run-id>` | Print a JSON summary for one run, including the governance outcome. |
| `adore [selector] export --csv` | Export metrics, including governance outcome, as CSV. |

`report` and `stats --rebuild` fail with a metrics-evidence error when a
versioned usage record is malformed or conflicts with another record for the
same launch. Rebuild validates all terminal runs before refreshing summaries.

## Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | Command completed successfully. |
| `1` | Configuration, operational, or validation error (including a refused `config set`). |
| `2` | Command-line usage error reported by the argument parser, such as an unknown option or missing required argument. |
