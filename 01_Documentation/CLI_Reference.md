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
process environment take precedence. Only the configured provider's key
variable and the names listed in `executor.env_keys` are passed into the
executor container, and forge authentication remains the
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
| `adore profile delete <profile-name> --force --remove-resources` | Also remove the project's executor containers, egress proxies/networks and worktrees, keeping those of handed-off or handoff-pending runs and any state folder outside ADORE home; refuses unfinished runs, a held lock or an invalid configuration; prints a JSON report. |
| `adore profile delete <profile-name> --force --remove-resources --remove-clone` | Also remove the local clone after the profile, only when it lies under `<ADORE home>/repos` (not through a symlink), is a git clone of the project's repository, is not another project's clone and has no linked worktree that deletion keeps (ADORE's own job worktrees are removed first) and no uncommitted changes; otherwise nothing is deleted and the reason is printed. A clone that becomes unsafe during the resource sweep, or cannot be removed, is kept and reported as `clone_retained`; a removed one as `clone_removed`. |
| `adore profile path [<profile-name>]` | Print the profile's `config.toml` path; without a name, use the active profile. |

Profile homes are `%APPDATA%\adore` on Windows and `~/.config/adore` on Linux,
unless `ADORE_HOME` overrides the location.

## Configuration Commands

| Command | Purpose |
| --- | --- |
| `adore [selector] config show` | Print the resolved configuration as JSON. |
| `adore [selector] config validate` | Validate the resolved configuration and report any issues. |
| `adore [selector] config set <section.key> <value>` | Set one scalar key in the resolved config file (e.g. `budgets.max_iterations 12`). Comments and the file's line endings (CR LF or LF) are preserved and the value type is inferred; the write is refused unless the whole resulting config still validates. Secret-looking keys are rejected - put secrets in `.env`; ADORE's own `metrics.capture_tokens` is not treated as one (it must be true or false). CLI and web edits share a local process lock; a concurrent edit is refused. |

In this table, `[selector]` means `-c <config.toml>` or `--profile
<profile-name>` where appropriate.
`delivery.publish_checkpoints` is on by default in CLI and web and accepts only
a TOML boolean. It publishes guarded ticket-branch progress commits without
creating an MR/PR before approval. Set it to false to keep intermediate
checkpoints local; explicit project values are preserved. `budgets.max_cost_usd = 0` disables the
reported-cost cap; iteration, wall-clock and file bounds still apply.

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
| `adore [selector] handoff <run-id>` | Transfer a run to a human at the next safe boundary, preserving its worktree and checkpoint evidence. If the conductor lock is held, the command queues the request; wait for `handed-off` before editing. This does not approve publication. |
| `adore [selector] reset <run-id> --to <stage> --force` | Deliberately move ADORE's own pointer to `frame`, `specify`, `design`, `build`, `validate`, or `publishing`; any other target is refused and the run stays unchanged. After `publishing`, `retry` returns an already published candidate to review, publishes an approved unpublished one, and otherwise conducts the run from `done`. It never edits the AEGIS task journal; conduction rereads that journal. `--force` is required. Run `retry` afterwards. |
| `adore [selector] delete <run-id> --force` | Irreversibly remove run state. |
| `adore [selector] cleanup` | Reclaim a provably stale local lock and remove the selected project's finished and orphaned run resources: the executor/proxy containers, egress networks and worktree directories of its done, cancelled, stale and state-less runs. Other projects' resources stay, even with a shared slug, egress network prefix or worktree root. Active, failed, human-owned and corrupt runs are protected; a live/unknown lock remains held and is reported. |

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
usage record has no event ID, is malformed or conflicts with another record for
the same launch. Rebuild validates all terminal runs before refreshing summaries.
A metrics database whose summary table has other columns than the current
summary is refused with `metrics database <path> was written by another ADORE
build; delete it to start fresh`; ADORE does not alter the table.

## Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | Command completed successfully. |
| `1` | Configuration, operational, or validation error (including a refused `config set`). |
| `2` | Command-line usage error reported by the argument parser, such as an unknown option or missing required argument. |

## Container preparation

Use `adore --profile <name> config plan` to review the effective image and exact preparation commands without executing them. Select through `config set execution.preparation <path.yml#job@full-commit>`. After inspecting a failed setup, `retry <run-id> --reprepare` explicitly replays every step in a fresh owned container with retained worktree, within the configured attempt cap. See [Container preparation](Container_Preparation.md).

## Native local execution

Run `adore pi install` and `adore pi verify` as the ADORE service account to manage the pinned Pi. See [Local execution](Local_Execution.md) for Node and Linux delegation.

`config validate` checks local profiles; config plan reviews pinned native policy without project commands. Existing run/retry/cancel/handoff/cleanup commands keep verified conductor ownership.

See [Local execution](Local_Execution.md) for platform prerequisites, configuration,
authentication, process ownership and acceptance coverage.

## Manual start with paused monitoring

`adore --profile NAME run --once --ticket IID` starts only the named eligible
ticket, even with monitoring paused, and leaves monitoring paused. Capacity,
workflow, lock and approval gates still apply. Non-preview manual commands end
with a secret-free `ADORE_START_RESULT ` JSON record (schema 1, ticket, exit_code,
reason); exit zero means admitted and nonzero names a closed failure reason.
Existing human-readable logs remain before the terminal record.


Explicit native `retry` accepts installed executor and inherited environment updates
on the same machine/account while retaining task, worktree, branch, history and
cumulative budgets. It runs the bounded version prerequisite before AEGIS. A failed
rearm returns exit 1, including when the conductor accepted Retry but provisioning
failed. The final `ADORE_RETRY_RESULT` line binds schema, run ID, exit and a closed
reason; the web worker shows the saved job cause rather than raw process logs.

## Direct agent dependency installation

`adore --profile <name> config set container.system_packages true` opts a container project into direct agent package-manager sudo. Use false to stop granting that permission for future jobs. Network remains independently configured through `container.egress`. Existing managed jobs retain pinned authority and reject policy drift. See [Agent dependency installation](Agent_Dependency_Installation.md).
