<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Deployment (`04_Software/deploy/`)

> Component documentation per `component_documentation_template.md`.
> Sources: `deploy/install-ubuntu.sh` (0.2.0), `deploy/install-windows.ps1`
> (0.2.0), `deploy/ador.service` (template).
> Design: Orchestrator_Design_And_Decisions.md sections 12, 12a, 12b.

## 1. Purpose

The "keep it running" glue for the two supported hosts: **Ubuntu 22+**
(production - systemd service) and **Windows 11** (first tests - Task
Scheduler). The orchestrator itself is portable Python with no OS-specific
code in the core loop (a repository rule); everything OS-specific lives in
this one directory as scripts, not code.

## 2. Responsibilities

- `install-ubuntu.sh` - prerequisite checks (uv, git, glab/gh; docker unless
  `--skip-image`), `uv sync --frozen`, `ador config validate`, executor-base
  image build when absent, and with `--service` the systemd unit install/enable/
  start (template rendering via `sed`, sudo only for the unit step);
  `--uninstall` removes the unit and keeps all state.
- `install-windows.ps1` (Windows PowerShell 5.1 compatible) - the same
  prepare steps, executor-image **verification** for the configured
  `-Runtime` (including WSL-wrapped, e.g. `"wsl -d Ubuntu-24.04 -- docker"`),
  and registration of the **"ADOR Orchestrator"** scheduled task: `-Mode
  loop` (default, `run --loop` at logon, no execution time limit) or `-Mode
  once -IntervalMinutes N` (repeating single pass); `-Uninstall` removes the
  task and keeps all state.
- `ador.service` - the systemd unit template: `__ADOR_DIR__` /
  `__ADOR_USER__` placeholders, `WorkingDirectory` at the checkout (so
  `config.toml` and `.env` resolve), optional `EnvironmentFile=-<dir>/.env`,
  `Restart=on-failure` + 30 s backoff, `NoNewPrivileges` / `PrivateTmp`.
- `deploy/README.md` - the operator-facing deployment procedure.

Explicitly not owned: installing prerequisites (checks fail closed with the
install hint - deterministic, no surprise system changes), secret contents
(placement only; design 12b), and native OS packaging (single-file exe / deb
are separate backlog items). The lightweight runtime bundle is owned by
`02_Tools/package_runtime.*`.

## 3. Implementation Overview

- Both scripts are **fail-fast** (`set -euo pipefail` /
  `$ErrorActionPreference = "Stop"` + explicit `$LASTEXITCODE` checks),
  **idempotent**, and **re-runnable** (a re-run after `git pull` refreshes
  the environment; an existing image or task is reused/replaced cleanly).
- Config is validated during deployment - a typo stops the install where the
  operator is watching, not the service start at 3 a.m. (the engine
  re-validates at startup anyway; design 12a).
- Secrets never appear in argv and are never echoed; the scripts only point
  at `.env` (gitignored, documented by `.env.example`) or the unit's
  `EnvironmentFile`.
- Double-poller protection is layered: the OS layer
  (`MultipleInstances IgnoreNew` / single systemd unit) plus ADOR's own
  `.ador/ador.lock`.
- The image is **built** on Ubuntu (native docker, absent-only) but only
  **verified** on Windows: building through a WSL-wrapped runtime needs
  mount-path translation, and the canonical commands live in
  `docker/README.md` - the script prints them and fails closed.
- Unattended egress fails closed: `--service` / Task Scheduler registration
  refuse `[container.egress] mode = "open"` unless the operator passes
  `--allow-open-egress` / `-AllowOpenEgress`. `allowlist-proxy` verifies the
  proxy image; Ubuntu may build it, Windows prints the exact build command if
  it is absent.
- Uninstall on both platforms removes only the service/task; `.ador/` state,
  worktrees, and containers are `ador cleanup` / `ador delete` territory.

## 4. Dependencies

- Internal: the `ador` console script in `.venv` (created by `uv sync`),
  `config.toml`, optional `.env`, `docker/Dockerfile.executor-base`, and any
  runtime-project Dockerfile such as `docker/Dockerfile.executor-project`.
- External: `uv`, `git`, `glab` or `gh`, a container runtime; `systemd`
  (Ubuntu) or Task Scheduler + the `ScheduledTasks` PowerShell module
  (Windows, in-box).

## 5. Inputs And Outputs

- Inputs: flags (`--service`, `--skip-image`, `--allow-open-egress`,
  `--uninstall` /
  `-Mode`, `-IntervalMinutes`, `-Runtime`, `-SkipImageCheck`, `-NoTask`,
  `-AllowOpenEgress`, `-Uninstall`), the `ADOR_USER` override (Ubuntu), the
  checkout location (derived from the script's own path - run from anywhere).
- Outputs: a synced `.venv`, the `ador-executor-base:0.2.0` image (Ubuntu),
  `/etc/systemd/system/ador.service` or the "ADOR Orchestrator" scheduled
  task, and human-readable progress notes.

## 7. Workflow Integration

Deployment is the last step of the setup chain: prerequisites
(`Setup_And_Credentials.md`, `Prerequisites_Check_Report.md`) -> config ->
image -> **this** -> the poller runs `ador run --loop`/`--once` unattended.
Operations afterwards go through the CLI (`status`, `pause`, `cleanup`,
`stats --html`) - there is no other control plane by design (12a).

## 8. Usage

```bash
# Ubuntu
./deploy/install-ubuntu.sh --service          # full: env, config, image, unit
./deploy/install-ubuntu.sh --allow-open-egress --service
journalctl -u ador -f                          # logs
./deploy/install-ubuntu.sh --uninstall         # remove the unit, keep state
```

```powershell
# Windows
.\deploy\install-windows.ps1 -Runtime "wsl -d Ubuntu-24.04 -- docker"
.\deploy\install-windows.ps1 -AllowOpenEgress
Start-ScheduledTask -TaskName "ADOR Orchestrator"
.\deploy\install-windows.ps1 -Uninstall
```

## 9. Validation And Tests

- Scripts are not unit-tested (no Python surface); validation is static +
  behavioral: `bash -n` and **shellcheck clean** for the Ubuntu script; the
  Windows script executed end-to-end in `-Uninstall` mode (parses, runs,
  reports, exits 0) on Windows PowerShell 5.1.
- Minimum validation after a change: re-run `bash -n` + `shellcheck` /
  the `-Uninstall` smoke, and one full prepare pass (`--skip-image` /
  `-SkipImageCheck -NoTask`) on the matching platform.

## 10. Limitations And Future Work

- The Ubuntu service runs as a normal user with docker access; a dedicated
  service account is on the organizational checklist (prereq report).
- Egress proxy is HTTP/HTTPS proxy based; SSH and other non-proxy-aware
  protocols remain outside v1.
- Native packaging (Windows exe / Ubuntu deb) is separate future work; the
  implemented handoff artifact is the runtime bundle from `02_Tools/`.
- The Windows loop task starts at logon (not boot); running as a service
  account at boot needs NSSM or a `-User/-Password` registration - add when
  a dedicated runner machine exists.
