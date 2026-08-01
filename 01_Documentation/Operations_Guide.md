<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Operations Guide

This guide covers normal, day-to-day operation after a runtime-project profile
has passed validation and a supervised poll. Use explicit `--profile` in
automation and when more than one target project exists.

## Start Each Operating Session Safely

Confirm the intended profile and configuration before asking ADORE to do work:

```bash
adore profile list
adore --profile <profile-name> config validate
adore --profile <profile-name> status
```

Configuration resolution is explicit `-c FILE`, then `--profile NAME`, then the
active profile, then `./config.toml`. An explicit profile avoids accidentally
operating a different target project.

## Choose the Run Mode

| Mode | Command | Use it when |
| --- | --- | --- |
| Dry run | `adore --profile <profile-name> run --dry-run` | Checking configuration or ticket eligibility without side effects. |
| One poll | `adore --profile <profile-name> run --once` | Supervised work, scheduled polling, or a controlled maintenance window. |
| Loop | `adore --profile <profile-name> run --loop` | A long-running service after the project has proven safe. |

Without a run-mode flag, ADORE uses `[polling] mode`. Keep a new target project
in `once` mode until its ticket rules, image, credentials, and delivery flow are
all proven.

## Monitor Work

Use the following commands before making a state-changing intervention:

```bash
adore --profile <profile-name> status
adore --profile <profile-name> runs
adore --profile <profile-name> logs <run-id>
```

`status` reports configuration health, state location, pause state, lock state,
and run counts. `runs` lists active, parked, and review runs. `logs` shows the
structured journal for one run. Live executor files are held under the run's
`io/` directory; immutable per-launch copies are in `io/archive/`.

## Read an AEGIS Escalation

Every run is governed by the target repository's AEGIS 2.x payload, and every
AEGIS-facing failure ends in one of three deterministic outcomes. The reason
is journaled and posted on the ticket, so `adore runs` plus the ticket
comment tell you which one happened and what it is waiting for.

| What you see | What happened | What to do |
| --- | --- | --- |
| The run is **parked** and the ticket carries a clarification comment | The executor recorded unresolved questions in the AEGIS stage form, alignment decided to pause, or the stage asked for `repo-wide` access or for routing back to an earlier stage. | Answer in a normal ticket comment. The run resumes on the next poll. Routing and access widening are human decisions in this version. |
| `failed` with `AEGIS blocked ...` and a `remediation:` clause | AEGIS refused an action for a governance reason ADORE is not allowed to resolve. | Do what the remediation says in the target clone, then `adore retry <run-id>`. |
| `failed` with `... a human may waive one of these ...` | A blocker AEGIS considers waivable stopped the run. **ADORE never waives.** | Decide whether the exception is acceptable; if it is, run the exact `aegis waive add <blocker-id> --reason "..."` command from the message in the run's worktree, then `adore retry <run-id>`. |
| `failed` with `the persistence lock is still held` | Another AEGIS process is running against the same repository. ADORE already retried once. | Let the other process finish (or find out what is holding the lock). **Never delete a lock file to bypass a live owner.** Then `adore retry <run-id>`. |
| `failed` naming `GRAPH-STALE-UPDATE`, `REQUIREMENT-STALE-UPDATE`, a corrupt schema, or a run-resolution error | AEGIS's integrity floor. ADORE never repairs AEGIS state. | Repair the run state in the target clone by hand, then `adore retry <run-id>`. |
| `failed` with `AEGIS contract failure (...)` | The payload answered outside the supported contract - a usage error, a missing Python runtime, unparseable output, an unknown stage, or a timeout. | Look at ADORE or the payload, not the ticket. Check the payload with `bash .agentic/tools/run.sh config validate --json` in the clone. |

The run's worktree is always kept for a failed run, so the AEGIS run records
under `.agentic/runs/<aegis-run-id>/` are available for inspection.

## Steer Ticket Pickup

The default labels divide control between people and ADORE:

| Intent | Default action |
| --- | --- |
| Permit pickup | Add `agent-ready` and a priority label (`P1`, `P2`, or `P3`). |
| Hold work | Add `agent-hold`, or pause ADORE globally. |
| Exclude work | Add `no-agent`. |
| Pin an executor | Add `agent-exec:<executor-name>`. |
| Answer a clarification | Add a normal comment, then `agent-answered` where label signaling is configured. |
| Request a revision | Apply `agent-revise` to the draft MR/PR, then run another poll. |

ADORE may create a draft MR/PR and update its branch. A human reviews, approves,
and merges it. Do not edit ADORE's hidden status marker lines in ticket
comments.

## Pause Before Changing the Operating Environment

Pause prevents new ticket pickup; it does not terminate in-flight work.

```bash
adore --profile <profile-name> pause
adore --profile <profile-name> resume
```

Pause before profile edits, image changes, label migrations, credential
maintenance, or planned host work. Validate the profile before resuming.

## Adjust Configuration Safely

Change one scalar setting without opening an editor:

```bash
adore --profile <profile-name> config set budgets.max_iterations 12
adore --profile <profile-name> config show
```

`config set` edits the resolved configuration file in place, preserving
comments and every other key, and infers the value type. It refuses the write
unless the whole resulting configuration still validates, so a typo cannot
leave a profile unloadable. Secret-looking keys are rejected: credentials
belong in `.env`, never in `config.toml`.

Edit the file directly for anything `config set` does not cover - tables, lists,
or several related keys at once - and run `config validate` afterwards. Use
`adore profile path <profile-name>` to locate it.

## Review Metrics and Reports

```bash
adore --profile <profile-name> stats
adore --profile <profile-name> stats --since 30d
adore --profile <profile-name> stats --by priority
adore --profile <profile-name> stats --html
adore --profile <profile-name> report <run-id>
adore --profile <profile-name> export --csv
```

`stats --html` writes the configured static dashboard. Use `stats --rebuild`
once if older terminal runs need to be re-summarized into the metrics database.

## Background Operation

Enable a service or scheduled task only after a supervised first run. The
deployment materials under `04_Software/deploy/` use the ADORE runtime directory
as the working directory, so keep its configuration and executor `.env` under
the control of the run-as account.

On Linux, the default service name is `adore.service`:

```bash
systemctl status adore.service
journalctl -u adore.service
```

On Windows, the default scheduled-task name is
`ADORE Orchestrator & Runtime Engine`:

```powershell
Get-ScheduledTask -TaskName 'ADORE Orchestrator & Runtime Engine'
```

Use [Recovery_And_Maintenance.md](Recovery_And_Maintenance.md) for failed,
parked, or unwanted work rather than manually removing state or containers.
