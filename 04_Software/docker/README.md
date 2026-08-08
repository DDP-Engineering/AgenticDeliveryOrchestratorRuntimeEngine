<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE Executor Images

ADORE uses a two-layer executor-image contract:

- `Dockerfile.executor-base` builds `adore-executor-base:1.0.0`. It contains
  the generic executor tools: Python 3.11 via uv, Node/npm, git, `glab`, `gh`,
  OpenCode, Pi, Codex, Qwen, the non-root `adore` user, fixed mount points,
  caches, HOME pinning, and Git safe-directory setup.
- Each runtime project supplies a Dockerfile that extends the base with that
  project's build and test tools. Tag the resulting image as
  `adore-executor-<project>:<tag>` and select it in the profile's
  `[container].image` setting.
- `Dockerfile.egress-proxy` builds `adore-egress-proxy:1.0.0`, a generic Squid
  proxy. ADORE mounts a generated per-run allowlist into it; project hosts are
  not baked into the image.

Use the base image for executor-only validation. Use a project image for any
delivery run that needs project-specific tools.

## Build the base and proxy images

On Linux, build from the `04_Software/docker` directory:

```bash
docker build --build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g) \
  -f Dockerfile.executor-base -t adore-executor-base:1.0.0 .
docker build -f Dockerfile.egress-proxy -t adore-egress-proxy:1.0.0 .
```

`USER_UID`/`USER_GID` make the container's `adore` user and group match the
account that runs ADORE. Without them, files written through bind mounts can be
owned by the wrong UID/GID and the host service cannot read or write the shared
per-run directories. With rootless Podman, omit the build arguments and
configure `run_args = ["--userns=keep-id"]` instead.

When Docker runs inside WSL, substitute the Linux-visible path to this
directory and the installed distribution name:

```powershell
wsl -d <distribution> -- docker build --build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g) `
  -f <linux-path-to-docker-dir>/Dockerfile.executor-base `
  -t adore-executor-base:1.0.0 `
  <linux-path-to-docker-dir>

wsl -d <distribution> -- docker build `
  -f <linux-path-to-docker-dir>/Dockerfile.egress-proxy `
  -t adore-egress-proxy:1.0.0 `
  <linux-path-to-docker-dir>
```

Set the profile's `runtime` to the command that invokes that runtime, for
example `wsl -d <distribution> -- docker`. ADORE translates Windows mount paths
and passes the required environment through WSL.

## Create a project image

Create a Dockerfile for the runtime project. It must start from the ADORE base,
install only the tools required by that project, and finish as the non-root
`adore` user.

```dockerfile
ARG BASE_IMAGE=adore-executor-base:1.0.0
FROM ${BASE_IMAGE}

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    <project-tools> \
    && rm -rf /var/lib/apt/lists/*
USER adore
```

Build it from its chosen build context:

```bash
docker build -f <project-dockerfile> -t adore-executor-<project>:<tag> .
```

Configure the profile to select the image and to check the project tools before
any executor stage runs:

```toml
[container]
image = "adore-executor-<project>:<tag>"
required_tool_checks = [
  # the AEGIS 3.x prerequisites the payload needs inside the container
  "python3 --version",
  "node --version",
  "bash --version",
  # plus whatever the runtime project's own gates invoke
  "<project-tool> --version",
]
```

The AEGIS CLI is stdlib-only, so nothing has to be installed for it beyond a
Python 3.11+ resolvable as `python3`. `node` is listed because the AEGIS guard
hooks fail closed without it, and their absence is otherwise silent.

## Egress proxy image

When `[container.egress] mode = "allowlist-proxy"`, ADORE creates one internal
network and one proxy container for each run. The executor joins only the
internal network; the proxy has outbound access and is reachable inside the
network as `adore-egress-proxy`.

Build the proxy image once per container runtime:

```bash
docker build -f Dockerfile.egress-proxy -t adore-egress-proxy:1.0.0 .
```

Allow only the hosts that the project and executor require:

```toml
[container.egress]
mode = "allowlist-proxy"
allowlist = ["gitlab.example.com", "api.openai.com", "*.pythonhosted.org"]
```

The allowlist accepts exact hostnames and leading wildcards. SSH and other
protocols that cannot use an HTTP(S) proxy are outside this mode's scope.

## Verify a container runtime

`verify-runtime.sh` checks the operations ADORE performs: image inspect/build,
volume create, mounted execution, egress modes, Git worktrees, parking and
resuming, listing, cleanup, and absence detection.

```bash
# Generic base-image validation.
RUNTIME=docker ./verify-runtime.sh

# Rootless Podman.
RUNTIME=podman RUN_ARGS="--userns=keep-id" ./verify-runtime.sh

# Project image validation.
IMAGE=adore-executor-<project>:<tag> \
REQUIRED_TOOL_CHECKS="<project-tool> --version" \
./verify-runtime.sh

# No-network executor validation.
EGRESS_MODE=none ./verify-runtime.sh

# Allowlist-proxy validation.
EGRESS_MODE=allowlist-proxy \
ALLOWLIST="example.com" \
ALLOWED_URL="https://example.com" \
DENIED_URL="https://github.com" \
./verify-runtime.sh
```

For rootless Podman, install `podman`, `uidmap`, and `slirp4netns`; build images
separately for Docker and Podman because their image stores differ. On SELinux
hosts, bind mounts can also require `:z` or `:Z` labels. On Windows-mounted
worktrees, project tools must not force `TMPDIR` into the worktree because Unix
sockets cannot be created there.

## First-build checks

```bash
docker run --rm adore-executor-base:1.0.0 python --version
docker run --rm adore-executor-base:1.0.0 uv --version
docker run --rm adore-executor-base:1.0.0 node --version
docker run --rm adore-executor-base:1.0.0 git --version
docker run --rm adore-executor-base:1.0.0 opencode --version
docker run --rm adore-executor-base:1.0.0 glab --version
docker run --rm adore-executor-base:1.0.0 gh --version
docker run --rm adore-executor-base:1.0.0 whoami

docker run --rm adore-executor-<project>:<tag> <project-tool> --version
```

Do not bake secrets into either image. ADORE injects only the configured
executor environment keys at `run` or `exec` time. See
`../../01_Documentation/Security_And_Credentials.md` for the credential
boundary.
