<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Environment guide

## Toolchain

Python 3.11 or later with `uv`; the runtime itself uses only the standard
library. Verification uses pytest and Ruff from the `dev` dependency group in
`04_Software/pyproject.toml`. Git is required. Live operation additionally
needs Docker or rootless Podman, natively or as Docker Engine inside WSL2 on
Windows, and an authenticated `glab`, `gh` or `tea`. Node.js supports npm-based installed executors in container images or under
the native local service account.
The optional web extra uses FastAPI, Uvicorn and Argon2id. Node.js/npm are
also needed on the web **build** machine for `04_Software/web/npm run build`;
the installed web runtime serves local assets without Node.js.

## Setup

From `04_Software`, `uv sync` creates `.venv` with the locked dependencies and
the `dev` group and installs the `adore` command in editable mode. Operator
installation on a host follows `01_Documentation/Getting_Started.md`;
unattended installation follows `04_Software/deploy/README.md`.
Frontend calculation tests use Node.js 22.18 or later for native TypeScript loading.
For web development use `uv sync --extra web --group dev` from `04_Software`,
then `npm ci` and `npx playwright install chromium` in `04_Software/web`.
`npm run validate` runs helper tests, UI/E2E TypeScript checks, an isolated
Vite build and offline Chromium journeys with a temporary API/worker home and
simulated external commands. The build uses `.e2e-dist`; failure screenshots,
traces and the HTML report are Git-ignored. `npm run build` produces the
deployable build. See `01_Documentation/Web_Interface.md` for test isolation,
timeouts and diagnostic commands. Direct validation requires no AEGIS task.

## Configuration and services

Runtime configuration is `config.toml`, started from
`04_Software/config.example.toml` and documented in
`01_Documentation/Configuration_Reference.md`. `adore init <profile>` creates
it under the profile home, `%APPDATA%\adore` on Windows or `~/.config/adore`
on Linux, unless `ADORE_HOME` overrides the location. Executor provider keys
named by `[executor].env_keys` live only in a gitignored `.env` beside the
configuration or in the process environment; forge authentication belongs to
the host CLI. Run state, the conductor lock and metrics live under the
configured `store_root`, `.adore/` by default.

## Readiness checks

`adore --profile <name> config validate` proves the configuration. Guided setup
(`adore init`) probes the host tools and the target repository's AEGIS
payload, which must provide `.agentic/aegis.py` at a supported version and
schema-1 `status --all --json`; the same two commands verify a target clone by
hand. `adore --profile <name> run --dry-run` shows ticket selection without
side effects.

## Build and run

The package has no build step: run `adore` from the synced `.venv`
(`.venv\Scripts\adore.exe` on Windows, `.venv/bin/adore` on Linux) with
`run --dry-run`, `run --once` or `run --loop`. Executor images are built from
`04_Software/docker/` as its README documents: the generic
`adore-executor-base:1.0.0`, the optional `adore-egress-proxy:1.0.0`, and one
project image per runtime project. Runtime bundles are produced by
`02_Tools/package_runtime.ps1` or `package_runtime.sh` into `07_Delivery/`.
The optional host-specific offline web media comes from
`02_Tools/package_web_offline.py`; its installer uses local locked wheels with
`pip --no-index`, and its launcher starts API and worker processes.
For web service monitoring, `/api/v1/health` checks the API listener and
`/api/v1/ready` requires a recent heartbeat from the separate control worker.

## Verification

`.agentic/aegis.toml` `[commands]` owns the canonical `test` and `lint`
commands, run from `workdir = "04_Software"`; the suite is fully offline.
Focused work runs `pytest -q tests/test_<component>.py` from `04_Software`.
The final proof for a governed task is
`python .agentic/aegis.py check --task TASK-<id> --strict --run`. A release
additionally passes `python 02_Tools/check_release_consistency.py
--require-artifacts`. Outcomes belong in task evidence, not here.

## Platform details

Development and packaging run on Windows 11 with PowerShell and Git Bash, and
on Ubuntu 22+. `.gitattributes` normalizes text to LF in the index except
`.ps1`, `.cmd` and `.bat`, which are CRLF; a Windows working copy may hold
either, so scripted edits should preserve each file's existing line endings.
The `[commands]` entries in `aegis.toml` name the Windows `.venv\Scripts`
executables; use the `.venv/bin` equivalents on Linux. WSL-wrapped container
runtimes receive mount-path translation and `WSLENV` propagation from ADORE.

## Authoritative references

- `.agentic/aegis.toml` - executable verification commands, layout and check
  configuration.
- `01_Documentation/Getting_Started.md` - prerequisites, installation and the
  first poll.
- `01_Documentation/Security_And_Credentials.md` - where every credential
  lives.
- `04_Software/deploy/README.md` - systemd and Task Scheduler installation.
- `04_Software/docker/README.md` - executor and proxy image build commands.
- `02_Tools/README.md` - release check and packaging scripts.
- `01_Documentation/Web_Interface.md` - optional web setup and offline media.

Admin Project Summary Connect repository provides scoped Gitea/GitHub/GitLab
authentication. See repository-auth.md knowledge and Security_And_Credentials.md.
Protected per-profile tokens are used only by forge CLI commands and explicit
web host checks, with external CLI auth as the missing-record default. Corrupt
or mismatched scoped records fail closed.

Explicit administrator model connectivity uses the selected OpenCode/Pi/Codex/Qwen CLI through a bounded backend-native disposable workspace; see knowledge/model-connection.md. Real provider acceptance is operator-triggered and may incur cost.

Project Executor configuration owns agent/model settings, reviewed backend-specific launch configuration and approved provider key save/remove within one panel, with heading Test AI connection; strict durable credential-bound model access evidence is reused in Summary/host presentation. See knowledge/executor-configuration.md. Subscription login remains the installed CLI service-account flow.

## Reviewed container preparation

Selected preparation profiles use `execution.preparation = "path.yml#job@full-commit"`; preview with `adore --profile <name> config plan`. The locally available effective image supplies `python3`, `sh`, executor and declared image-tool checks. Project dependencies use existing egress/cache/env; expose installed tools through explicit runtime PATH. Source/limits/recovery are documented in `01_Documentation/Container_Preparation.md`. Offline focused recipe/source/recovery tests use injected runners; live container/model/forge acceptance is operator-authorized.

## Native local prerequisites

Local profiles require independently installed CLI/native Python under the ADORE
service account. Windows needs executable entrypoints (or installed Node/JS argv)
and Jobs; Linux needs delegated cgroup v2 with kill. Local execution skips images/
preparation, reuses auth and rejects container egress restrictions. Tools remain
independently prepared. See 01_Documentation/Local_Execution.md.

## Project image build clients

The server administrator builds and verifies executor images externally with the installed Docker/Podman runtime, then updates the existing profile. The GUI supplies a read-only Dockerfile/profile guide. Existing native owned process scopes and delegated Linux `ADORE_BUILD_CGROUP_ROOT` remain available for retained interrupted build cleanup; queued requests are refused. See `01_Documentation/Project_Executor_Images.md`. Full run/model/forge acceptance has separate authority.
