<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE Deployment

Deployment scripts for the two supported hosts (design doc 12/12a):
**Ubuntu 22+** (production: systemd service) and **Windows 11** (first
tests: Task Scheduler). Same artifact both places - the orchestrator is
portable Python; only the "keep it running" glue differs per OS, and it
lives entirely in this directory.

In the repository these files live in `02_Tools/deploy/`; the Python project,
configuration, virtual environment and Dockerfiles remain in `04_Software/`.
Ordinary portable user archives use their own launchers; service administration
is separate from the three public repository environment/packaging commands.
Both installers resolve the runtime from their own location, independently
of the caller's working directory, and refuse an incomplete installation.

Both scripts are **fail-fast, idempotent, and re-runnable**: they check
prerequisites with a clear hint instead of auto-installing, sync the locked
Python environment, validate `config.toml` (a bad config stops deployment,
not the 3 a.m. service start), and verify/build the configured executor base
or runtime-project image.
Re-running after a `git pull` updates the environment in place.

## Web supervisor service

The installers below configure the standalone CLI poller. For web operation,
run the API and exactly one `adore-web-worker --home <absolute-home>` under the
same service account and home. The worker command is a local process supervisor:
it discovers project workers and creates run processes up to each project's
`polling.max_concurrent_runs`. Monitoring pause leaves explicit Start available.
A separate configuration consumer handles existing control operations. There is
no Redis/Celery dependency or per-project service/task installation.

On Linux, a web-worker service uses `ExecStart=<venv>/bin/adore-web-worker --home
<absolute-home>`, `KillMode=control-group`, `TimeoutStopSec=20` and
`Restart=on-failure`. Stop the single supervisor unit to stop its project/run
trees. Keep the API's ordinary service configuration separate. Do not run the
standalone CLI poller for the same managed profiles.

On Windows, register one long-running `adore-web-worker.exe --home <absolute-home>`
task beside the API, not a task per project. Its children use gated kill-on-close
Jobs; a killed supervisor cannot leave conductors with writing authority.
The portable application's Start/Stop scripts own both services and their
children as one application on Windows and Linux. No script installation is
required for newly created or restored projects.

Each supervisor boundary requests Stop for all children together, allows two
seconds of grace, then forces owned scopes and waits at most five seconds for
roots. OS Job drain verification can add at most five seconds per scope on
Windows. Unconfirmed scopes retain durable ownership. Recovery requires proven
process death and never treats an uncertain publication as permission to repeat
it. A stuck/crashed project worker is replaced independently with bounded
backoff; other projects and configuration keep their own processes.

## Before either script

1. Clone the repository and `cd 04_Software`, or enter an unpacked runtime
   bundle root. Create the configuration here; the installers keep using
   this runtime directory after relocation.
2. `cp config.example.toml config.toml` and adjust it (repo, `repo_path`,
   `runtime`, budgets - see `../../01_Documentation/Configuration_Reference.md`).
3. Authenticate `glab`, `gh` or `tea` on the host. Put only executor provider API
   keys required by `env_keys` in the gitignored `.env` file
   (`cp .env.example .env`); see
   `../../01_Documentation/Security_And_Credentials.md`.
   Secrets never go in `config.toml` or on command lines (design 12b).
4. Build the generic executor base image and any runtime-project image required
   by the profile; use the generic project-image pattern in
   [docker/README.md](../../04_Software/docker/README.md).
5. Have a container runtime: native Docker Engine on Ubuntu; on Windows
   either native or Docker Engine inside WSL2
   (`runtime = "wsl -d Ubuntu-24.04 -- docker"`, see `docker/README.md`).

## Ubuntu 22+ (systemd)

From the repository root:

```bash
bash 02_Tools/deploy/install-ubuntu.sh              # prepare only (env, config, base image)
bash 02_Tools/deploy/install-ubuntu.sh --service    # + install/enable/start adore.service
bash 02_Tools/deploy/install-ubuntu.sh --allow-open-egress --service  # supervised pilot override
bash 02_Tools/deploy/install-ubuntu.sh --uninstall  # stop/remove the unit (state kept)
```

From an unpacked runtime bundle, use `bash deploy/install-ubuntu.sh` with
the same flags. From `04_Software/` in a checkout, use
`bash ../02_Tools/deploy/install-ubuntu.sh`.

- The unit template is `adore.service` beside the installer; it substitutes the
  checkout path and the service user (`ADORE_USER=<name>` to override,
  default: the invoking user) and installs to
  `/etc/systemd/system/adore.service` (sudo only for this step).
- `ExecStart` runs `.venv/bin/adore -c config.toml run --loop` with
  `WorkingDirectory` at the checkout, `Restart=on-failure` + 30 s backoff,
  and an optional `EnvironmentFile=<checkout>/.env` (the design-preferred
  OS-level secret path on a server).
- Logs: `journalctl -u adore -f`. ADORE also mirrors `run` output to
  `<store_root>/adore.log`. Control: `systemctl {status,stop,restart} adore`.
- `--skip-image` skips the image check/build (e.g. remote daemon).
- The installer reads `executor.internet` from `adore config show`. Service
  install of a container project refuses `[executor] internet = true` (Internet access for the agent
  On, open egress) unless `--allow-open-egress` is passed; keep it `false` for
  unattended operation. For a container project with `internet = false` the
  installer verifies, and if needed builds, the proxy image from `docker/Dockerfile.egress-proxy`.

## Windows 11 (Task Scheduler)

From the repository root:

```powershell
.\02_Tools\deploy\install-windows.ps1                              # loop at logon
.\02_Tools\deploy\install-windows.ps1 -Mode once -IntervalMinutes 10  # repeating single pass
.\02_Tools\deploy\install-windows.ps1 -Runtime "wsl -d Ubuntu-24.04 -- docker"  # WSL2 docker
.\02_Tools\deploy\install-windows.ps1 -AllowOpenEgress          # supervised pilot override
.\02_Tools\deploy\install-windows.ps1 -NoTask                      # prepare only
.\02_Tools\deploy\install-windows.ps1 -Uninstall                   # remove the task (state kept)
```

From an unpacked runtime bundle, use `.\deploy\install-windows.ps1` with
the same flags. From `04_Software\` in a checkout, use
`..\02_Tools\deploy\install-windows.ps1`.

- Registers the task **"ADORE Orchestrator & Runtime Engine"** running
  `.venv\Scripts\adore.exe` with the working directory at the checkout (so
  `config.toml` and `.env` resolve), no execution time limit, and
  `MultipleInstances IgnoreNew` (plus ADORE's own `.adore/adore.lock` - two
  pollers on one store are impossible).
- `-Mode loop` (default): starts `run --loop` at logon.
  `-Mode once`: runs `run --once` every `-IntervalMinutes` (design 12a's
  cron-style alternative; each pass exits, auditable per run).
- ADORE mirrors `run --loop`, `run --once`, and `run --dry-run` output to the
  rotating `<store_root>\adore.log`, which is the first place to inspect
  Task Scheduler runs after `adore status` / `adore runs`.
- The image is only **verified** on Windows (building through a WSL-wrapped
  runtime needs path translation); pass the profile's image tag, for example
  `-ImageTag adore-executor-<project>:<tag>`. Exact generic build commands are
  in `docker/README.md`.
- Task registration of a container project refuses `[executor] internet = true` unless
  `-AllowOpenEgress` is passed. For a container project with `internet = false`
  the proxy image is
  verified through the configured runtime; if absent, the script prints the
  exact `docker build -f Dockerfile.egress-proxy ...` command and exits.

## What deployment deliberately does NOT do

- **No merge rights, no auto-merge** - nothing here changes the delivery
  boundary; the service only opens draft MRs.
- **No secret handling beyond placement** - scripts never read, print, or
  pass secrets; they only point at `.env` / `EnvironmentFile`.
- **No silent open egress for unattended installs** - service/task installers
  fail when `[executor] internet = true` unless the operator passes the
  explicit supervised-pilot override.
- **Uninstall keeps all state** - `.adore/`, worktrees, and containers
  survive; use `adore cleanup` / `adore delete <run-id> --force` for those.

## Operational quick reference

```bash
adore status            # health, lock, run counts
adore runs              # per-run table
adore pause / resume    # gate ticket pickup (in-flight runs continue)
adore cleanup           # after a crash: stale lock, orphans, husk dirs
adore stats --html      # static dashboard (.adore/metrics/report.html)
```
