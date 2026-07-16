<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE Executor Images

ADORE uses a two-layer image contract:

- `Dockerfile.executor-base` builds `adore-executor-base:1.0.0`, the generic
  ADORE executor environment. It contains only the tools needed to run ADORE
  executors: Python 3.11 via uv, Node/npm, git, glab, gh, opencode, pi, codex,
  qwen, the non-root `adore` user, mount points, caches, HOME pinning, and git
  safe-directory setup.
- Runtime-project images extend the base and add that project’s build/test
  dependencies. The current Cockpit-GCP image is
  `Dockerfile.executor-cockpit-gcp` -> `adore-executor-cockpit-gcp:latest`.
- `Dockerfile.egress-proxy` builds `adore-egress-proxy:1.0.0`, a generic Squid
  proxy image. ADORE mounts a generated per-run allowlist config into it; no
  runtime-project hosts are baked into the image.

`[container].image` selects the runtime-project image per ADORE profile. Use
`adore-executor-base:1.0.0` for executor-only validation, and a project image for
real delivery runs.

## Build

The executor base image must be built with `--build-arg USER_UID=$(id -u)` so
the container's `adore` user matches the host user that runs ADORE. Without this,
files written by the container to bind-mounted volumes (worktree, IO, caches)
are owned by the wrong UID. Podman deployments can skip this and use
`run_args = ["--userns=keep-id"]` instead (see Podman notes below).

```bash
cd 04_Software/docker
docker build --build-arg USER_UID=$(id -u) -f Dockerfile.executor-base -t adore-executor-base:1.0.0 .
docker build -f Dockerfile.egress-proxy -t adore-egress-proxy:1.0.0 .
```

For the current Cockpit-GCP runtime project:

```bash
docker build -f Dockerfile.executor-cockpit-gcp -t adore-executor-cockpit-gcp:latest .
```

With Docker Engine inside WSL2 (no Docker Desktop), build from PowerShell as:

```powershell
wsl -d Ubuntu-24.04 -- docker build --build-arg USER_UID=$(id -u) `
  -f /mnt/d/TEMP/2026_AgenticDeliveryOrchestratorRuntimeEngine/04_Software/docker/Dockerfile.executor-base `
  -t adore-executor-base:1.0.0 `
  /mnt/d/TEMP/2026_AgenticDeliveryOrchestratorRuntimeEngine/04_Software/docker

wsl -d Ubuntu-24.04 -- docker build `
  -f /mnt/d/TEMP/2026_AgenticDeliveryOrchestratorRuntimeEngine/04_Software/docker/Dockerfile.egress-proxy `
  -t adore-egress-proxy:1.0.0 `
  /mnt/d/TEMP/2026_AgenticDeliveryOrchestratorRuntimeEngine/04_Software/docker

wsl -d Ubuntu-24.04 -- docker build `
  -f /mnt/d/TEMP/2026_AgenticDeliveryOrchestratorRuntimeEngine/04_Software/docker/Dockerfile.executor-cockpit-gcp `
  -t adore-executor-cockpit-gcp:latest `
  /mnt/d/TEMP/2026_AgenticDeliveryOrchestratorRuntimeEngine/04_Software/docker
```

Set `runtime = "wsl -d Ubuntu-24.04 -- docker"` in `config.toml`; ADORE handles
mount-path translation (`D:\x` -> `/mnt/d/x`) and WSLENV env propagation.

## Runtime Project Pattern

Create one Dockerfile per runtime project:

```dockerfile
ARG BASE_IMAGE=adore-executor-base:1.0.0
FROM ${BASE_IMAGE}

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    <project tools> \
    && rm -rf /var/lib/apt/lists/*
USER adore
```

Then set the project profile:

```toml
[container]
image = "adore-executor-cockpit-gcp:latest"
required_tool_checks = [
  "make --version",
  "shellcheck --version",
  "terraform --version",
  "tflint --version",
]
```

The required checks run after container provision and fail closed before any
executor gate starts.

## Egress Proxy Image

When `[container.egress] mode = "allowlist-proxy"`, ADORE creates one internal
network and one proxy container per run. The executor container joins only that
internal network. The proxy container keeps normal outbound access and is also
connected to the internal network with alias `adore-egress-proxy`.

Build the generic proxy image once per runtime:

```bash
docker build -f Dockerfile.egress-proxy -t adore-egress-proxy:1.0.0 .
```

Then set only hostnames in project config:

```toml
[container.egress]
mode = "allowlist-proxy"
allowlist = ["gitlab.example.com", "api.openai.com", "*.pythonhosted.org"]
```

The allowlist accepts exact hostnames and leading wildcards only. SSH and other
non-proxy-aware protocols are out of scope for this mode.

## Runtime Verification

`verify-runtime.sh` proves a container runtime compatible with ADORE before a
profile points at it. It mirrors the runtime CLI calls `ContainerManager` makes:
image inspect/build, volume create, run with mounts/env, egress modes, exec,
git via GIT_DIR/GIT_WORK_TREE, park/resume, listing, reap, and absence
detection.

```bash
# Generic executor-base validation.
RUNTIME=docker ./verify-runtime.sh

# Rootless podman.
RUNTIME=podman RUN_ARGS="--userns=keep-id" ./verify-runtime.sh

# Cockpit-GCP project image validation.
IMAGE=adore-executor-cockpit-gcp:latest \
REQUIRED_TOOL_CHECKS="make --version;shellcheck --version;terraform --version;tflint --version" \
./verify-runtime.sh

# No-network executor validation.
EGRESS_MODE=none ./verify-runtime.sh

# Allowlist proxy validation.
EGRESS_MODE=allowlist-proxy \
ALLOWLIST="example.com" \
ALLOWED_URL="https://example.com" \
DENIED_URL="https://github.com" \
./verify-runtime.sh
```

Podman notes:

- Rootless podman requires `[container] run_args = ["--userns=keep-id"]`.
  Without it, container uid 1000 (`adore`) maps to a subuid that cannot write
  the bind-mounted worktree.
- Install with `sudo apt-get install -y podman uidmap slirp4netns`; images are
  built separately per runtime because podman and docker use different storage.
- On SELinux hosts, bind mounts may additionally need `:z`/`:Z` labels.
- Bind-mounted worktrees on Windows hosts cannot host Unix sockets. Target repos
  must not force `TMPDIR` into the worktree for tools such as tflint.

## First-Build Checks

Base image:

```bash
docker run --rm adore-executor-base:1.0.0 python --version
docker run --rm adore-executor-base:1.0.0 uv --version
docker run --rm adore-executor-base:1.0.0 node --version
docker run --rm adore-executor-base:1.0.0 git --version
docker run --rm adore-executor-base:1.0.0 opencode --version
docker run --rm adore-executor-base:1.0.0 glab --version
docker run --rm adore-executor-base:1.0.0 gh --version
docker run --rm adore-executor-base:1.0.0 whoami
```

Cockpit-GCP image:

```bash
docker run --rm adore-executor-cockpit-gcp:latest make --version
docker run --rm adore-executor-cockpit-gcp:latest shellcheck --version
docker run --rm adore-executor-cockpit-gcp:latest terraform --version
docker run --rm adore-executor-cockpit-gcp:latest tflint --version
```

Secrets are never baked into either image. ADORE injects configured executor env
keys at `docker run` / `docker exec` time.
