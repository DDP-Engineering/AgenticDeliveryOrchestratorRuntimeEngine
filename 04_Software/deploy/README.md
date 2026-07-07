<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADOR Deployment

Deployment scripts for the two supported hosts (design doc 12/12a):
**Ubuntu 22+** (production: systemd service) and **Windows 11** (first
tests: Task Scheduler). Same artifact both places - the orchestrator is
portable Python; only the "keep it running" glue differs per OS, and it
lives entirely in this directory.

Both scripts are **fail-fast, idempotent, and re-runnable**: they check
prerequisites with a clear hint instead of auto-installing, sync the locked
Python environment, validate `config.toml` (a bad config stops deployment,
not the 3 a.m. service start), and verify/build the configured executor base
or runtime-project image.
Re-running after a `git pull` updates the environment in place.

## Before either script

1. Clone the repository and `cd 04_Software`.
2. `cp config.example.toml config.toml` and adjust it (repo, `repo_path`,
   `runtime`, budgets - see `00_Planning/Configuration_Reference.md`).
3. Authenticate `glab` (or `gh`) on the host, or provide tokens via `.env`
   (`cp .env.example .env`; the file is gitignored). Secrets never go in
   `config.toml` and never appear on command lines (design 12b).
4. Build the generic executor base image and any runtime-project image required
   by the profile; for Cockpit-GCP, build `ador-executor-cockpit-gcp:latest`
   from `docker/README.md`.
5. Have a container runtime: native Docker Engine on Ubuntu; on Windows
   either native or Docker Engine inside WSL2
   (`runtime = "wsl -d Ubuntu-24.04 -- docker"`, see `docker/README.md`).

## Ubuntu 22+ (systemd)

```bash
./deploy/install-ubuntu.sh              # prepare only (env, config, base image)
./deploy/install-ubuntu.sh --service    # + install/enable/start ador.service
./deploy/install-ubuntu.sh --allow-open-egress --service  # supervised pilot override
./deploy/install-ubuntu.sh --uninstall  # stop/remove the unit (state kept)
```

- The unit template is `deploy/ador.service`; the installer substitutes the
  checkout path and the service user (`ADOR_USER=<name>` to override,
  default: the invoking user) and installs to
  `/etc/systemd/system/ador.service` (sudo only for this step).
- `ExecStart` runs `.venv/bin/ador -c config.toml run --loop` with
  `WorkingDirectory` at the checkout, `Restart=on-failure` + 30 s backoff,
  and an optional `EnvironmentFile=<checkout>/.env` (the design-preferred
  OS-level secret path on a server).
- Logs: `journalctl -u ador -f`. Control: `systemctl {status,stop,restart} ador`.
- `--skip-image` skips the image check/build (e.g. remote daemon).
- Service install refuses `[container.egress] mode = "open"` unless
  `--allow-open-egress` is passed. Use `allowlist-proxy` or `none` for
  unattended operation. In `allowlist-proxy` mode the installer verifies, and
  if needed builds, the proxy image from `docker/Dockerfile.egress-proxy`.

## Windows 11 (Task Scheduler)

```powershell
.\deploy\install-windows.ps1                              # loop at logon
.\deploy\install-windows.ps1 -Mode once -IntervalMinutes 10  # repeating single pass
.\deploy\install-windows.ps1 -Runtime "wsl -d Ubuntu-24.04 -- docker"  # WSL2 docker
.\deploy\install-windows.ps1 -AllowOpenEgress          # supervised pilot override
.\deploy\install-windows.ps1 -NoTask                      # prepare only
.\deploy\install-windows.ps1 -Uninstall                   # remove the task (state kept)
```

- Registers the task **"ADOR Orchestrator"** running
  `.venv\Scripts\ador.exe` with the working directory at the checkout (so
  `config.toml` and `.env` resolve), no execution time limit, and
  `MultipleInstances IgnoreNew` (plus ADOR's own `.ador/ador.lock` - two
  pollers on one store are impossible).
- `-Mode loop` (default): starts `run --loop` at logon.
  `-Mode once`: runs `run --once` every `-IntervalMinutes` (design 12a's
  cron-style alternative; each pass exits, auditable per run).
- The image is only **verified** on Windows (building through a WSL-wrapped
  runtime needs path translation); use `-ImageTag ador-executor-cockpit-gcp:latest`
  when the profile points at the Cockpit-GCP image. Exact build commands are in
  `docker/README.md`.
- Task registration refuses `[container.egress] mode = "open"` unless
  `-AllowOpenEgress` is passed. In `allowlist-proxy` mode the proxy image is
  verified through the configured runtime; if absent, the script prints the
  exact `docker build -f Dockerfile.egress-proxy ...` command and exits.

## What deployment deliberately does NOT do

- **No merge rights, no auto-merge** - nothing here changes the delivery
  boundary; the service only opens draft MRs.
- **No secret handling beyond placement** - scripts never read, print, or
  pass secrets; they only point at `.env` / `EnvironmentFile`.
- **No silent open egress for unattended installs** - service/task installers
  fail when `[container.egress] mode = "open"` unless the operator passes the
  explicit supervised-pilot override.
- **Uninstall keeps all state** - `.ador/`, worktrees, and containers
  survive; use `ador cleanup` / `ador delete <run-id> --force` for those.

## Operational quick reference

```bash
ador status            # health, lock, run counts
ador runs              # per-run table
ador pause / resume    # gate ticket pickup (in-flight runs continue)
ador cleanup           # after a crash: stale lock, orphans, husk dirs
ador stats --html      # static dashboard (.ador/metrics/report.html)
```
