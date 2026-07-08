<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Monitoring And Steering

Applies to ADOR 0.5.1.

Use this when ADOR is running, you need to understand its current state, or you
need to pause and resume ticket pickup safely.

![ADOR monitoring map](assets/monitoring-recovery-map.svg)

## First Three Commands

```powershell
.\.venv\Scripts\ador.exe --profile <profile-name> status
.\.venv\Scripts\ador.exe --profile <profile-name> runs
.\.venv\Scripts\ador.exe --profile <profile-name> logs <run-id>
```

```bash
./.venv/bin/ador --profile <profile-name> status
./.venv/bin/ador --profile <profile-name> runs
./.venv/bin/ador --profile <profile-name> logs <run-id>
```

| Command | Use it for |
| --- | --- |
| `status` | Config health, store path, pause flag, lock state, and run counts. |
| `runs` | Run id, ticket id, stage, lifecycle, and last update time. |
| `logs <run-id>` | Per-run journal events with structured details. |

If `status` reports corrupt run state, ADOR skips it. Inspect it manually before
deleting anything.

## Pause And Resume

Pause stops new ticket pickup. It does not kill in-flight runs.

```powershell
.\.venv\Scripts\ador.exe --profile <profile-name> pause
.\.venv\Scripts\ador.exe --profile <profile-name> resume
```

```bash
./.venv/bin/ador --profile <profile-name> pause
./.venv/bin/ador --profile <profile-name> resume
```

Use pause before maintenance windows, label cleanups, profile edits, or human
triage. Resume only after `config validate` is clean.

## Metrics Commands

```powershell
.\.venv\Scripts\ador.exe --profile <profile-name> stats
.\.venv\Scripts\ador.exe --profile <profile-name> stats --by priority
.\.venv\Scripts\ador.exe --profile <profile-name> stats --html
.\.venv\Scripts\ador.exe --profile <profile-name> report <run-id>
.\.venv\Scripts\ador.exe --profile <profile-name> export --csv
```

```bash
./.venv/bin/ador --profile <profile-name> stats
./.venv/bin/ador --profile <profile-name> stats --by outcome
./.venv/bin/ador --profile <profile-name> stats --html
./.venv/bin/ador --profile <profile-name> report <run-id>
./.venv/bin/ador --profile <profile-name> export --csv
```

| Command | Output |
| --- | --- |
| `stats` | Aggregated runs, outcomes, span, launches, tokens, and cost. |
| `stats --since 30d` | Same summary over a time window. |
| `stats --by priority` | Grouped by priority. |
| `stats --by outcome` | Grouped by outcome. |
| `stats --html` | Self-contained static dashboard at configured `html_out`. |
| `report <run-id>` | JSON summary for one run. |
| `export --csv` | CSV for external reporting. |

If metrics were added after older terminal runs, rebuild summaries once:

```powershell
.\.venv\Scripts\ador.exe --profile <profile-name> stats --rebuild
```

```bash
./.venv/bin/ador --profile <profile-name> stats --rebuild
```

## Safe Operating Modes

| Mode | Command | When to use |
| --- | --- | --- |
| Dry run | `ador run --dry-run` | Before the first real pickup or after config edits. |
| One poll | `ador run --once` | Supervised validation and scheduled polling. |
| Loop | `ador run --loop` | Service-style operation after validation. |

For a new project, keep using `--once` until ticket labels, images, credentials,
and MR/PR delivery have all been proven.

