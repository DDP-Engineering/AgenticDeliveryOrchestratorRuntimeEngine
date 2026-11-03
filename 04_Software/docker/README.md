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
  the generic executor tools: Python 3.11 via uv, Node 22.23.4/npm, git,
  `glab`, `gh`, Pi 1.4.0 (ADORE's only coding agent) with pi-web-access 0.46.0
  under `/opt/pi`, ADORE's Pi guard extension (`pi/adore-guard.ts`, copied to
  `/opt/adore/pi/`), ADORE's ChatGPT helper (`pi/adore-chatgpt.mjs`, copied to
  `/opt/adore/pi/adore-chatgpt.mjs`), the ADORE-owned Pi agent directory
  `/home/adore/.adore-pi-agent`, the non-root `adore` user, fixed mount points,
  caches, HOME pinning, and Git safe-directory setup. ADORE runs the ChatGPT
  helper only in a one-off helper container that mounts the server's ChatGPT
  credential directory (`<ADORE home>/chatgpt`), to sign in with ChatGPT and to
  get each stage's short-lived access token; a run container never mounts that
  directory. `verify-runtime.sh` checks the Node, Pi and pi-web-access versions,
  and its step 14 checks that the ChatGPT helper loads the pinned Pi. Rebuild
  the image after pulling a change to these pins.
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
  # the prerequisites the AEGIS payload needs inside the container
  "python3 --version",
  "node --version",
  "bash --version",
  # plus whatever the runtime project's own gates invoke
  "<project-tool> --version",
]
```

The AEGIS CLI is stdlib-only, so nothing has to be installed for it beyond a
Python 3.11+ resolvable as `python3`. `node` is listed because the executors
are npm packages and cannot start without it.

## Egress proxy image

With `[executor] internet = false` (Internet access for the agent Off, the
default), ADORE creates one internal network and one proxy container for each
container run, for every stage and for **Test AI connection**. The executor joins only the internal network; the proxy has outbound
access and is reachable inside the network as `adore-egress-proxy`. With
`internet = true` the run's network is open and no proxy is created.

Build the proxy image once per container runtime; ADORE never pulls it, and
**Check host prerequisites** reports it missing for an internet-off project:

```bash
docker build -f Dockerfile.egress-proxy -t adore-egress-proxy:1.0.0 .
```

The proxy admits the model provider's hosts, which ADORE derives from
`[executor] provider` (the hosts of Pi's base URLs in `adore/pi_catalog.json`,
the `openai` hosts for `chatgpt`, the endpoint's host for `custom`), plus any
extra hosts the project requires:

```toml
[container.egress]
allowlist = ["pypi.org", "*.pythonhosted.org"]
```

The allowlist accepts exact hostnames and leading wildcards and is empty by
default. The generated `squid.conf` admits host names with a `dstdomain` ACL
and IP addresses (such as an endpoint at `192.168.1.20`) with a `dst` ACL, then
denies everything else. The proxy container receives the `--add-host` options
of `[container] run_args`, so an alias such as `host.docker.internal:host-gateway`
resolves in the proxy too. SSH and other protocols that cannot use an HTTP(S)
proxy are not reachable; `pip install` and `npm install` fail unless their
hosts are in the allowlist.

**An internet-off project needs Podman 4.0 or newer**, with netavark as the
network backend. The executor reaches the proxy by the DNS alias
`adore-egress-proxy` on an `--internal` network, and Podman 3.x with the older
CNI backend both disables DNS on internal networks and cannot attach a running
container to a second network. Ubuntu 22.04 packages Podman 3.4, so check
`podman --version` there, and confirm with:

```bash
EGRESS_MODE=allowlist-proxy RUNTIME=podman ./verify-runtime.sh
```

Docker has no equivalent constraint, and an internet-on project works on every
supported runtime version. `EGRESS_MODE` is a parameter of `verify-runtime.sh`
only; `config.toml` has no egress mode.

## Verify a container runtime

`verify-runtime.sh` checks the operations ADORE performs: image inspect/build,
volume create, mounted execution, egress modes, Git worktrees, parking and
resuming, listing, cleanup, and absence detection. Step 14 runs the ChatGPT
helper's `token` command against an empty directory and expects
`{"status":"not-signed-in"}`, which proves the helper loads the pinned Pi.

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
separately for Docker and Podman because their image stores differ. On Windows-
mounted worktrees, project tools must not force `TMPDIR` into the worktree
because Unix sockets cannot be created there.

## SELinux hosts

On a host with SELinux enforcing, which is the default on Fedora, RHEL, CentOS
Stream, Rocky, and Alma, a bind mount keeps its host file label and the
container process cannot read it. Every stage then fails on permission denied.
Set the relabel mode in the profile:

```toml
[container]
selinux_relabel = "shared"
```

That appends `z` to the mounted clone, worktree, and io directory, and to the
generated egress-proxy config. The named cache volumes are left alone, because
the runtime already creates them with a container-readable label.

ADORE does not offer the private `Z` label. It labels content with a
per-container category, and the repository clone is shared by every run and by
host git, so `Z` would bind the clone to one container and break the next run.

## First-build checks

```bash
docker run --rm adore-executor-base:1.0.0 python --version
docker run --rm adore-executor-base:1.0.0 uv --version
docker run --rm adore-executor-base:1.0.0 node --version
docker run --rm adore-executor-base:1.0.0 git --version
docker run --rm adore-executor-base:1.0.0 pi --version
docker run --rm adore-executor-base:1.0.0 glab --version
docker run --rm adore-executor-base:1.0.0 gh --version
docker run --rm adore-executor-base:1.0.0 whoami

docker run --rm adore-executor-<project>:<tag> <project-tool> --version
```

Do not bake secrets into either image. ADORE injects only the configured
executor environment keys at `run` or `exec` time. See
`../../01_Documentation/Security_And_Credentials.md` for the credential
boundary.

## Recipe execution requirements

Selected preparation images must already exist locally and include `python3`, `sh`, the executor and configured image tool checks. Dependency setup runs later in the same run container/worktree, under existing egress and bounds. See [Container preparation](../../01_Documentation/Container_Preparation.md).
