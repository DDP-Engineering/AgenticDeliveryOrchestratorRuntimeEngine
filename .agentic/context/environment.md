<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Environment guide

Offline web control proof uses isolated temporary homes and fake external runners. Worker activity evidence is advisory and requires a current heartbeat.

Portable user delivery is built natively with `python 02_Tools/create_package.py`
with automatic frontend compilation/licensing. It includes managed CPython and locked
web dependencies; uv and network access are needed only on the build host.
Windows ZIP/Linux TAR.GZ output goes to repository-relative `07_Delivery/`.
Run `python 02_Tools/verify_package.py <archive>` on each matching host; it uses
an isolated home and empty host PATH, and removes temporary data on exit; results go to the console only.
User startup uses Start-ADORE.cmd/start-adore.sh with no host Python setup.

## Toolchain

Python 3.11 or later with `uv`; the runtime itself uses only the standard
library. Verification uses pytest and Ruff from the `dev` dependency group in
`04_Software/pyproject.toml`. Git is required. Live operation additionally
needs Docker or rootless Podman, natively or as Docker Engine inside WSL2 on
Windows, and an authenticated `glab`, `gh` or `tea`. Node.js runs Pi in container images
(the base image pins Node 22.23.4, Pi 1.4.0 and pi-web-access 0.46.0) or an
installed Pi under the native local service account.
The optional web extra uses FastAPI, Uvicorn and Argon2id. Node.js/npm are
also needed on the web **build** machine for `04_Software/web/npm run build`;
the installed web runtime serves local assets without Node.js.

## Setup

Native Python children receive managed UTF-8 standard-stream settings, independent
of ambient Python flags or the Windows account code page. Native evidence
decoding remains strict. Explicit Retry revalidates the effective environment
fingerprint and existing process ownership.

Run `python 02_Tools/setup_environment.py` to prepare the source environment
without tests or service installation. From `04_Software`, `uv sync` creates `.venv` with the locked dependencies and
the `dev` group and installs the `adore` command in editable mode. Operator
installation on a host follows `01_Documentation/Getting_Started.md`;
unattended installation follows `02_Tools/deploy/README.md`.
Frontend calculation tests use Node.js 22.18 or later for native TypeScript loading.
For web development use `uv sync --extra web --group dev` from `04_Software`,
then `npm ci` and `npx playwright install chromium` in `04_Software/web`.
`npm run validate` runs helper tests, UI/E2E TypeScript checks, an isolated
Vite build and offline Chromium journeys with a temporary API/worker home and
simulated external commands. The build uses `.e2e-dist`; failure screenshots,
traces and the HTML report are Git-ignored. `npm run build` produces the
deployable build. Every Vite build emits `BUNDLED_LICENSES.json` with the full
licenses for bundled dependencies, including the isolated forge GFM renderer;
retain it alongside the copied third-party notice inventory. See `01_Documentation/Web_Interface.md` for test isolation,
timeouts and diagnostic commands. Direct validation requires no AEGIS task.
The Overview isolation checks use incompatible job state in temporary profiles,
with API fixtures and the existing Chromium test server.
Complete project ZIP import uses isolated source catalogs and temporary profile
roots with injected failures; no Docker, forge or network command is required.
Browser import fixtures create current ZIPs through the public Python exporter.

## Configuration and services

Runtime configuration is `config.toml`, started from
`04_Software/config.example.toml` and documented in
`01_Documentation/Configuration_Reference.md`. `adore init <profile>` creates
it under the profile home, `%APPDATA%\adore` on Windows or `~/.config/adore`
on Linux, unless `ADORE_HOME` overrides the location. The executor provider key
(the variable Pi reads for `[executor].provider`) and any additional secrets
named by `[executor].env_keys` live only in a gitignored `.env` beside the
configuration or in the process environment; forge authentication belongs to
the host CLI. Run state, the conductor lock and metrics live under the
configured `store_root`, `.adore/` by default.

## Readiness checks

`adore --profile <name> config validate` proves the configuration. Guided setup
(`adore init`) probes host tools and the target repository's AEGIS payload
only when present. Absence reports `No AEGIS found: tickets run in the direct
workflow` as INFO, with no AEGIS command. Present payloads must meet the
client-declared supported range and schema-1 `status --all --json`; broken or
unsupported entries never enable fallback. After confirmation/validation init
uses the effective `workflow.aegis_python` (default `python`) for both probes;
a missing interpreter is named with informational CHECK. The same two commands
verify a present target payload by hand. Web enrollment accepts either workflow
without installing or modifying AEGIS. Direct CLI init and existing-clone web
setup-preview share `suggest_verification_command`: bounded local-file discovery
with source provenance, no command/network/probe or toolchain prerequisite.
Uncreated enrollment destinations remain not-inspected with no suggestion; saved
Settings never infer one. The selected command is editable/clearable and saved
only after human confirmation. Offline proof is `test_verification_hint.py`,
`test_wizard.py`, `test_web_enrollment.py` and enrollment/settings browser journeys.
`adore --profile <name> run --dry-run` shows ticket selection without side effects.

## Build and run

The package has no build step: run `adore` from the synced `.venv`
(`.venv\Scripts\adore.exe` on Windows, `.venv/bin/adore` on Linux) with
`run --dry-run`, `run --once` or `run --loop`. Executor images are built from
`04_Software/docker/` as its README documents: the generic
`adore-executor-base:1.0.0`, `adore-egress-proxy:1.0.0` (needed by every container project with
`[executor] internet = false`, the default), and one
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
Offline model fakes need provider credentials absent from the parent test
process (for example `env -u OPENAI_API_KEY`), not copied into fixtures. Native
machine/account checks require an initialized container/host machine identity;
Linux uses a nonempty `/etc/machine-id`. Playwright uses its matching installed
Chromium, including `PLAYWRIGHT_BROWSERS_PATH` when image-provided.
The final proof for a governed task is
`python .agentic/aegis.py check --task TASK-<id> --strict --run`. A release
additionally passes `python 02_Tools/internal/check_release_consistency.py
--require-artifacts`. Outcomes belong in task evidence, not here.

## Platform details

Development and packaging run on Windows 11 with PowerShell and Git Bash, and
on Ubuntu 22+. `.gitattributes` normalizes text to LF in the index except
`.ps1`, `.cmd` and `.bat`, which are CRLF; a Windows working copy may hold
either, so scripted edits should preserve each file's existing line endings.
The `[commands]` entries in `aegis.toml` use portable `uv run --frozen`
commands for Python tests and Ruff, and npm for frontend validation. WSL-wrapped container
runtimes receive mount-path translation and `WSLENV` propagation from ADORE.

## Authoritative references

- `.agentic/aegis.toml` - executable verification commands, layout and check
  configuration.
- `01_Documentation/Getting_Started.md` - prerequisites, installation and the
  first poll.
- `01_Documentation/Security_And_Credentials.md` - where every credential
  lives.
- `02_Tools/deploy/README.md` - systemd and Task Scheduler installation.
- `04_Software/docker/README.md` - executor and proxy image build commands.
- `02_Tools/README.md` - release check and packaging scripts.
- `01_Documentation/Web_Interface.md` - optional web setup and offline media.

Admin Project Summary Connect repository provides scoped Gitea/GitHub/GitLab
authentication. See repository-auth.md knowledge and Security_And_Credentials.md.
Protected per-profile tokens are used only by forge CLI commands and explicit
web host checks, with external CLI auth as the missing-record default. Corrupt
or mismatched scoped records fail closed.

Explicit administrator model connectivity uses Pi through a bounded backend-native disposable workspace; see knowledge/model-connection.md. Real provider acceptance is operator-triggered and may incur cost.

Project Settings → Agent and model owns the Pi model setting, reviewed backend-specific launch command and approved provider key save/remove within one panel, with a credential-name dropdown, plus Test AI connection; strict durable credential-bound model access evidence is reused in Summary/host presentation. See knowledge/executor-configuration.md. Native Pi uses a managed installation and injected provider credentials. Subscription sign-in is for containers.

## Reviewed container preparation

Selected preparation profiles use `execution.preparation = "path.yml#job@full-commit"`; preview with `adore --profile <name> config plan`. The locally available effective image supplies `python3`, `sh`, executor and declared image-tool checks. Project dependencies use existing egress/cache/env; expose installed tools through explicit runtime PATH. Source/limits/recovery are documented in `01_Documentation/Container_Preparation.md`. Offline focused recipe/source/recovery tests use injected runners; live container/model/forge acceptance is operator-authorized.

## Native local prerequisites

Native child environments preserve the account's PATH and inherited PATHEXT so
Windows shells resolve installed executable names. Forge credential variables
remain filtered; project tools are still installed by the operator.

Configured direct verification uses the validate timeout override or general gate
limit from the worktree root: containers use sh -c, native Linux /bin/sh -c and
native Windows the bound SystemRoot/System32/cmd.exe /d /s /c. Configure the exact
single-line command in server TOML or through the guided/reviewed configuration
APIs; empty stays unverified and AEGIS ignores it.
Native verification output must be UTF-8 and its owned scope must drain; the
shell has service-account permissions without container/host isolation. Ordinary
native shell argv remains refused. Offline tests inject controllers/Jobs/cgroups
and the Windows child/CreateProcess boundary; live platform acceptance remains
operator-owned.

Local profiles require independently installed CLI/native Python under the ADORE
service account. Windows needs executable entrypoints (or installed Node/JS argv)
and Jobs; Linux needs delegated cgroup v2 with kill. Local execution skips images/
preparation, reuses auth, rejects a container egress allowlist and is not restricted by
`[executor] internet`. Tools remain
independently prepared. See 01_Documentation/Local_Execution.md.

## Project image build clients

The server administrator builds and verifies executor images externally with the installed Docker/Podman runtime, then selects it in enrollment or the reviewed Settings flow, or updates the existing profile. The GUI supplies a Dockerfile/profile guide and image suggestions from the server's
local images. Technical details retains validated source definitions by image tag;
Export directly saves configuration with the complete declared local source chain,
without building or application export choices. The browser destination picker is
optional, with ordinary browser download as fallback. The wheel includes the canonical executor-base Dockerfile, Pi inputs and
license. Build/export require registry/package access separately; sources live in
ADORE_HOME/executor-recipes independently of job state. Existing native owned process scopes and delegated Linux `ADORE_BUILD_CGROUP_ROOT` remain available for retained interrupted build cleanup; queued requests are refused. See `01_Documentation/Project_Executor_Images.md`. Full run/model/forge acceptance has separate authority.

Local enrollment and Agent and model command editing detect installed native
executors and known npm entrypoints on the actual Windows/Linux ADORE host,
with explicit manual executable paths. Discovery reads files without executing
CLIs; existing auth/model checks and native isolation remain separate. See
`01_Documentation/Local_Execution.md` and knowledge/executor-discovery.md.

Native enrollment uses a read-only detected account with automatic home/PATH.
Full commands and environment overrides stay under Advanced. Clone destinations
have automatic/custom selection and an administrator host folder navigator;
selection is read-only and actual clone publication retains its existing checks.
The offline browser suite delays the initial folder read to verify that the
typed address survives the response before submitting it to the host API.
See knowledge/host-folders.md and 01_Documentation/Web_Interface.md.

Reviewed web configuration saves preserve the active file and unsaved settings on write errors; brief Windows replacement contention uses six attempts with at most 250ms total scheduled delay and explicit localized failure.

## Automatic command presentation

ADORE applies GIT_PAGER=cat/PAGER=cat per automatic child process, including
native executors and container exec. Windows host/supervisor/executor launches
use CREATE_NO_WINDOW. No global Git settings are required. The defaults affect
new launches; existing services/jobs retain the version and environment already
loaded. Ordinary children inherit the environment; explicitly requested GUI or
new-console windows are controlled by the tool that creates them.
Focused offline proof: test_automatic_processes.py and runner/native/worker/
container environment tests. See 01_Documentation/Local_Execution.md.

## Portable repository authentication

Gitea CLI auth belongs to the account running ADORE on each machine. Standard
XDG/account configuration discovery is shared by runtime, web probes and
enrollment. Existing project connections retain priority; no private application
cache paths or credentials belong in delivery archives. Missing/ambiguous auth
uses Project Summary -> Connect repository -> Repository server / Access token ->
Verify and connect -> Check host prerequisites. See Security_And_Credentials.md.
Focused tests: test_gitea_auth.py and repository connection/source cases.

## Native check diagnostics

Check host prerequisites uses the same managed Pi, account and provider credential and accepts
version output on stdout or stderr. Closed diagnostic causes include native
permission/scope/cleanup boundaries. Test AI connection reuses saved native argv
in an empty temporary folder and reports model/provider errors without raw output.
Targeted tests inject native/process/CLI boundaries and do not contact a model.

Windows no-console executor launch needs explicit stdout/stderr bindings from
the supervisor to its child. The native helper closes stdin and retains the
existing parent capture pipes; no global terminal/Git/Pi settings are needed.

## Agent package image readiness

Opted-in container.system_packages jobs require a rebuilt compatible Linux image with root-owned OS Python/id, sudo/visudo and a supported package manager. ADORE configures sudo permission but installs no bootstrap tools on job start. Native execution rejects the permission. Agent package downloads obey container.egress. See 01_Documentation/Agent_Dependency_Installation.md; live package acceptance is separate from offline injected tests.


## Container Git context

Fresh repository containers use a read-only container-native Git pointer while
the host keeps its own pointer. Git selects independent and nested repositories
normally; managed repository-selection environment fields are provisioning
metadata. Warm containers preserve their creation-time binding and installed
contents. WSL container commands use direct argument execution; custom wrappers
identify their command boundary explicitly. See knowledge/isolation.md and
01_Documentation/Operations_Guide.md for ownership and recovery contracts.

## Container timeout recovery

Shared container commands address observed immutable IDs. Actual timeouts require
verified same-resource interruption before output retention, with deferred verified
restart at the next command/provision. Dependencies/files/user/egress are retained.
Unconfirmed recovery blocks active admission and becomes terminal infrastructure
failure; cancellation and explicit owned release keep authority. No new runtime
package or state schema is required. See knowledge/execution.md and Operations_Guide.

Native server prerequisite setup uses `adore pi install` and `adore pi verify` under
the ADORE account, with Node 22.23.4+ in the 22.x line. The service sets
`ADORE_NODE` for an explicit executable and `ADORE_LOCAL_CGROUP_ROOT` for Linux.


## Native ChatGPT prerequisites

Native subscription projects use the same verified managed Pi/Node installation
as other native projects. Their trusted helper performs Pi OAuth without Docker,
using the ADORE-owned credential directory and filtered service environment.
Windows requires owned Jobs. Linux/WSL2 requires a delegated cgroup v2
subtree containing the service process, with writable process and kill controls.
The container internet switch does not restrict native host networking.

## Confirmed recovery after drift

Failed-job abandonment uses confirmed state revisions, verified owned native/container/worktree cleanup and leased remote-branch deletion before normal manual admission with monitoring pause preserved. Explicit native cleanup uses saved ownership without resolving current tools; ordinary execution/Retry identity checks remain strict. Proof: tests/test_drift_recovery.py and web/e2e/driftRecovery.spec.ts. No stored schema changes or live resource acceptance are required.

Previously orphaned unproven refs are preserved through bounded fresh branch generations, with actual naming-rule checks and atomic initial local ref creation. Verified own branches remain reusable; known changed checkpoints refuse before cleanup.


## Budget verification boundaries

Budget rereads are pure local parsing/budget validation plus binding to already
validated non-budget settings; no repeated branch-rule/host probe is run. The
one-second real matcher contract remains in test_branch_naming.py; wizard assembly
injects its trusted fixture process. Budget/state/HTTP/browser proof uses isolated
homes and the existing 18765 browser listener, with no live model, forge, runtime
job or user-service acceptance. See orchestrator.md and web-interface.md knowledge.


Focused History and CLI deletion verification uses temporary home/profile stores and fake engines; it performs no live forge, model or runtime operation.

Factory administrator proof uses isolated temporary identity stores and the serial offline browser fixture on port 18765. Production web source or help changes require a rebuilt and verified committed static bundle.


Worker ownership proof uses isolated web schema-18 stores with injectable process births,
independent SQLite connections and deterministic barriers/events. It never starts DCP,
contacts a forge/model or executes a target repository check. Linux /proc and Windows
process creation evidence distinguish PID reuse; unavailable probes retain ownership.
Existing stores in other schemas are refused with explicit database/marker deletion guidance.

Owned-run concurrency proof uses isolated state roots, injected forge/executor/
backend boundaries, deterministic events and an owned spawned helper solely for
kernel-lock death recovery. Targeted tests cover admission, single-run CLI,
capacity resumptions, dispatch corruption, live/unknown durable ownership and
cleanup boundaries; no target repository checks or DCP operations run.


Shared-resource proof uses isolated homes, injected Git/runtime/auth/Node boundaries and deterministic thread barriers. Kernel lock files stay outside deletable profiles. Run targeted component contracts only per umbrella instruction; global validation is deferred to the final umbrella pass.


Supervisor proof uses actual Windows process trees and injected offline forge/Git/
executor collaborators. File barriers prove simultaneous executor entry with
independent PIDs, N+1 admission deferral and completed B while A is blocked. Parent
crash proof observes descendant death and uncertain claims. Only targeted Python/
help checks and the required static bundle build run in WK-04; final umbrella
validation remains separate. Portable tools receive inspection/smoke only.


Scoped configuration proof uses isolated homes, fake model/runtime/forge runners,
protected input/result corruption and deterministic thread barriers, plus a single
owned configuration process for HTTP-to-worker consumption. Managed image build
barriers prove B/global progress and free image edit locks without any real runtime.
Targeted frontend configuration/help tests and the required static build verify the
browser wait contract. Full umbrella validation stays deferred by user instruction.

WK-06 proof uses isolated current profile/state/identity stores and offline conductors/configuration consumers. Targeted HTTP/core/storage/help contracts plus projectCapacity browser journeys cover occupancy 2 -> staged N=1, continuing admitted jobs, occupancy-1 refusal, four locales and narrow layout. Browser screenshots use the disposable 18765 fixture; no DCP, forge/model/runtime acceptance or target-repository checks run. Full integrated validation remains deferred to the umbrella final.

Review-boundary proof additionally covers two reserved initial runs started serially after staged N reduction, corrupt project/run/control heartbeat isolation, credential-bearing endpoint exclusion and truthful staged notices for increases/unrelated edits in all four locales.


REQ-FUNC-3b737a5c: queued initial starts share the reduced ceiling through supervisor dispatch and atomic conductor activation. Pending reservations do not count as started executors; existing running execution/cleanup does. Capacity deferral leaves execution_pending and queued dispatch unchanged until an actual slot is available.
