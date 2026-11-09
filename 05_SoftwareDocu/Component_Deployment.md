<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Deployment (`02_Tools/deploy/`)

> Component documentation per `component_documentation_template.md`.
> Sources: `02_Tools/deploy/install-ubuntu.sh`, `02_Tools/deploy/install-windows.ps1`,
> `02_Tools/deploy/adore.service` (template).
> Design context: `00_Planning/ADORE_System_Overview.md`.

## 1. Purpose

The "keep it running" glue for the two supported hosts: **Ubuntu 22+**
(production - systemd service) and **Windows 11** (first tests - Task
Scheduler). The orchestrator itself is portable Python with no OS-specific
code in the core loop (a repository rule); everything OS-specific lives in
this one directory as scripts, not code.

## 2. Responsibilities

- `install-ubuntu.sh` - prerequisite checks (uv, git, glab/gh/tea; docker unless
  `--skip-image`), `uv sync --frozen`, `adore config validate`, executor-base
  image build when absent, and with `--service` the systemd unit install/enable/
  start (template rendering via `sed`, sudo only for the unit step);
  `--uninstall` removes the unit and keeps all state.
- `install-windows.ps1` (Windows PowerShell 5.1 compatible) - the same
  prepare steps, executor-image **verification** for the configured
  `-Runtime` (including WSL-wrapped, e.g. `"wsl -d Ubuntu-24.04 -- docker"`),
  and registration of the **"ADORE Orchestrator & Runtime Engine"** scheduled task: `-Mode
  loop` (default, `run --loop` at logon, no execution time limit) or `-Mode
  once -IntervalMinutes N` (repeating single pass); `-Uninstall` removes the
  task and keeps all state.
- `adore.service` - the systemd unit template: `__ADORE_DIR__` /
  `__ADORE_USER__` placeholders, `WorkingDirectory` at the checkout (so
  `config.toml` and `.env` resolve), optional `EnvironmentFile=-<dir>/.env`,
  `Restart=on-failure` + 30 s backoff, `NoNewPrivileges` / `PrivateTmp`.
- `02_Tools/deploy/README.md` - the operator-facing deployment procedure.

Explicitly not owned: installing prerequisites (checks fail closed with the
install hint - deterministic, no surprise system changes), secret contents
(placement only; design 12b), and native OS packaging (single-file exe / deb
are separate backlog items). The complete portable user distribution is owned by
`02_Tools/create_package.py`; service setup is separate.

## 3. Implementation Overview

- Scripts and the service template live in `02_Tools/deploy/`. In a source
  checkout they resolve the sibling `04_Software/` as the runtime. Packagers
  do not copy service setup into ordinary user archives.
  Configuration, `.env`, `.venv`, Docker build contexts and scheduler working
  directories all use that runtime path, even when invoked from another directory.
  Missing `pyproject.toml` or `adore/` stops installation before environment setup.
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
  (`MultipleInstances IgnoreNew` / single systemd unit) plus ADORE's own
  `.adore/adore.lock`.
- The image is **built** on Ubuntu (native docker, absent-only) but only
  **verified** on Windows: building through a WSL-wrapped runtime needs
  mount-path translation, and the canonical commands live in
  `docker/README.md` - the script prints them and fails closed.
- Unattended egress fails closed: both scripts read `executor.internet` from
  `adore config show`, and `--service` / Task Scheduler registration refuse
  `[executor] internet = true` (open egress) unless the operator passes
  `--allow-open-egress` / `-AllowOpenEgress`. With `internet = false` the run
  sits behind the per-run proxy, so the scripts verify the
  `[container.egress] proxy_image`; Ubuntu may build it, Windows prints the
  exact build command if it is absent.
- Uninstall on both platforms removes only the service/task; `.adore/` state,
  worktrees, and containers are `adore cleanup` / `adore delete` territory.

## 4. Dependencies

- Internal: the `adore` console script in `.venv` (created by `uv sync`),
  `config.toml`, optional `.env`, `docker/Dockerfile.executor-base`, and any
  runtime-project Dockerfile such as `docker/Dockerfile.executor-project`.
- External: `uv`, `git`, `glab`/`gh`/`tea`, a container runtime; `systemd`
  (Ubuntu) or Task Scheduler + the `ScheduledTasks` PowerShell module
  (Windows, in-box).

## 5. Inputs And Outputs

- Inputs: flags (`--service`, `--skip-image`, `--allow-open-egress`,
  `--uninstall` /
  `-Mode`, `-IntervalMinutes`, `-Runtime`, `-SkipImageCheck`, `-NoTask`,
  `-AllowOpenEgress`, `-Uninstall`), the `ADORE_USER` override (Ubuntu), the
  checkout location (derived from the script's own path - run from anywhere).
- Outputs: a synced `.venv`, the `adore-executor-base:1.0.0` image (Ubuntu),
  `/etc/systemd/system/adore.service` or the "ADORE Orchestrator & Runtime Engine" scheduled
  task, human-readable progress notes, and ADORE-owned run logs under
  `<store_root>/adore.log` once the installed service/task starts polling.

## 7. Workflow Integration

Deployment is the last step of the setup chain: prerequisites and credentials
(`01_Documentation/Getting_Started.md`,
`01_Documentation/Security_And_Credentials.md`) -> config -> image -> **this**
-> the poller runs `adore run --loop`/`--once` unattended.
Operations afterwards go through the CLI (`status`, `pause`, `cleanup`,
`stats --html`) - there is no other control plane by design (12a).

## 8. Usage

```bash
# Ubuntu
bash 02_Tools/deploy/install-ubuntu.sh --service          # full: env, config, image, unit
bash 02_Tools/deploy/install-ubuntu.sh --allow-open-egress --service
journalctl -u adore -f                          # host service logs
tail -f 04_Software/.adore/adore.log                         # ADORE-owned run log
bash 02_Tools/deploy/install-ubuntu.sh --uninstall         # remove the unit, keep state
```

```powershell
# Windows
.\02_Tools\deploy\install-windows.ps1 -Runtime "wsl -d Ubuntu-24.04 -- docker"
.\02_Tools\deploy\install-windows.ps1 -AllowOpenEgress
Start-ScheduledTask -TaskName "ADORE Orchestrator & Runtime Engine"
.\02_Tools\deploy\install-windows.ps1 -Uninstall
```

## 9. Verification

Do not add or run automated tests for deployment or environment setup scripts.
Review script changes directly; verify actual user application archives separately.

## 10. Limitations And Future Work

- The Ubuntu service runs as a normal user with docker access; a dedicated
  service account is on the organizational checklist.
- Egress proxy is HTTP/HTTPS proxy based; SSH and other non-proxy-aware
  protocols remain outside v1. Package caches and adaptive dependency
  installation are out of scope (#26): with internet off, `pip install` and
  `npm install` in a run fail unless the operator adds the package hosts to
  `[container.egress] allowlist`.
- Native packaging (Windows exe / Ubuntu deb) is separate future work; the
  implemented user handoff is the complete portable ZIP/TAR.GZ.
- The Windows loop task starts at logon (not boot); running as a service
  account at boot needs NSSM or a `-User/-Password` registration - add when
  a dedicated runner machine exists.
