<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADOR Executor Images

ADOR uses a two-layer image contract:

- `Dockerfile.executor-base` builds `ador-executor-base:0.2.0`, the generic
  ADOR executor environment. It contains only the tools needed to run ADOR
  executors: Python 3.11 via uv, Node/npm, git, glab, gh, opencode, pi, codex,
  qwen, the non-root `ador` user, mount points, caches, HOME pinning, and git
  safe-directory setup.
- Runtime-project images extend the base and add that project’s build/test
  dependencies. The current Cockpit-GCP image is
  `Dockerfile.executor-cockpit-gcp` -> `ador-executor-cockpit-gcp:latest`.

`[container].image` selects the runtime-project image per ADOR profile. Use
`ador-executor-base:0.2.0` for executor-only validation, and a project image for
real delivery runs.

## Build

```bash
cd 04_Software/docker
docker build -f Dockerfile.executor-base -t ador-executor-base:0.2.0 .
```

For the current Cockpit-GCP runtime project:

```bash
docker build -f Dockerfile.executor-cockpit-gcp -t ador-executor-cockpit-gcp:latest .
```

With Docker Engine inside WSL2 (no Docker Desktop), build from PowerShell as:

```powershell
wsl -d Ubuntu-24.04 -- docker build `
  -f /mnt/d/TEMP/2026_AgenticDeliveryOrchestrator/04_Software/docker/Dockerfile.executor-base `
  -t ador-executor-base:0.2.0 `
  /mnt/d/TEMP/2026_AgenticDeliveryOrchestrator/04_Software/docker

wsl -d Ubuntu-24.04 -- docker build `
  -f /mnt/d/TEMP/2026_AgenticDeliveryOrchestrator/04_Software/docker/Dockerfile.executor-cockpit-gcp `
  -t ador-executor-cockpit-gcp:latest `
  /mnt/d/TEMP/2026_AgenticDeliveryOrchestrator/04_Software/docker
```

Set `runtime = "wsl -d Ubuntu-24.04 -- docker"` in `config.toml`; ADOR handles
mount-path translation (`D:\x` -> `/mnt/d/x`) and WSLENV env propagation.

## Runtime Project Pattern

Create one Dockerfile per runtime project:

```dockerfile
ARG BASE_IMAGE=ador-executor-base:0.2.0
FROM ${BASE_IMAGE}

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    <project tools> \
    && rm -rf /var/lib/apt/lists/*
USER ador
```

Then set the project profile:

```toml
[container]
image = "ador-executor-cockpit-gcp:latest"
required_tool_checks = [
  "make --version",
  "shellcheck --version",
  "terraform --version",
  "tflint --version",
]
```

The required checks run after container provision and fail closed before any
executor gate starts.

## Runtime Verification

`verify-runtime.sh` proves a container runtime compatible with ADOR before a
profile points at it. It mirrors the runtime CLI calls `ContainerManager` makes:
image inspect/build, volume create, run with mounts/env, exec, git via
GIT_DIR/GIT_WORK_TREE, park/resume, listing, reap, and absence detection.

```bash
# Generic executor-base validation.
RUNTIME=docker ./verify-runtime.sh

# Rootless podman.
RUNTIME=podman RUN_ARGS="--userns=keep-id" ./verify-runtime.sh

# Cockpit-GCP project image validation.
IMAGE=ador-executor-cockpit-gcp:latest \
REQUIRED_TOOL_CHECKS="make --version;shellcheck --version;terraform --version;tflint --version" \
./verify-runtime.sh
```

Podman notes:

- Rootless podman requires `[container] run_args = ["--userns=keep-id"]`.
  Without it, container uid 1000 (`ador`) maps to a subuid that cannot write
  the bind-mounted worktree.
- Install with `sudo apt-get install -y podman uidmap slirp4netns`; images are
  built separately per runtime because podman and docker use different storage.
- On SELinux hosts, bind mounts may additionally need `:z`/`:Z` labels.
- Bind-mounted worktrees on Windows hosts cannot host Unix sockets. Target repos
  must not force `TMPDIR` into the worktree for tools such as tflint.

## First-Build Checks

Base image:

```bash
docker run --rm ador-executor-base:0.2.0 python --version
docker run --rm ador-executor-base:0.2.0 uv --version
docker run --rm ador-executor-base:0.2.0 node --version
docker run --rm ador-executor-base:0.2.0 git --version
docker run --rm ador-executor-base:0.2.0 opencode --version
docker run --rm ador-executor-base:0.2.0 glab --version
docker run --rm ador-executor-base:0.2.0 gh --version
docker run --rm ador-executor-base:0.2.0 whoami
```

Cockpit-GCP image:

```bash
docker run --rm ador-executor-cockpit-gcp:latest make --version
docker run --rm ador-executor-cockpit-gcp:latest shellcheck --version
docker run --rm ador-executor-cockpit-gcp:latest terraform --version
docker run --rm ador-executor-cockpit-gcp:latest tflint --version
```

Secrets are never baked into either image. ADOR injects configured executor env
keys at `docker run` / `docker exec` time.
