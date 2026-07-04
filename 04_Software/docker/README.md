<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADOR Executor Image

`Dockerfile.executor` builds `ador-executor:latest`, the container every run
executes in (design doc 10a). Base tooling is baked in once; project
dependencies resolve at container runtime into the mounted cache volumes,
never into the bind-mounted worktree.

## Build

```bash
cd 04_Software/docker
docker build -f Dockerfile.executor -t ador-executor:latest .
```

With Docker Engine inside WSL2 (no Docker Desktop), build from PowerShell as:

```powershell
wsl -d Ubuntu-24.04 -- docker build `
  -f /mnt/d/TEMP/2026_AgenticDeliveryOrchestrator/04_Software/docker/Dockerfile.executor `
  -t ador-executor:latest `
  /mnt/d/TEMP/2026_AgenticDeliveryOrchestrator/04_Software/docker
```

and set `runtime = "wsl -d Ubuntu-24.04 -- docker"` in `config.toml`; ADOR
handles the mount-path translation (D:\x -> /mnt/d/x) and WSLENV env
propagation itself.

Pinned versions are `ARG`s at the top of the Dockerfile (`NODE_MAJOR=20` to
match the target repo's CI, `GLAB_VERSION`, `OPENCODE_PACKAGE`); override with
`--build-arg` when bumping.

## Contents

| Tool | Why |
|---|---|
| Python 3.11 + `uv` | Target repo tooling / `.agentic` CLI. |
| Node 20 + npm | Pinned to the target repo's `.gitlab-ci.yml`. |
| git (`safe.directory *`) | Executor commits locally; bind mounts show foreign ownership on Docker Desktop. |
| opencode (npm) | The default executor CLI. |
| glab / gh | Optional in-container platform CLI use (setup doc section 6). |
| make, shellcheck, terraform, tflint | The target repo's gate toolchain (`make lint`/`make test`); live pilot findings 2026-07-03/04. |
| user `ador` (uid 1000) | The executor never runs as root. |

## How ADOR uses it

- One container per run: `ador-run-<run-id>`, idling on `sleep infinity`;
  the executor is launched inside via `docker exec` gate by gate.
- Mounts: local repo clone at `/ador/repo`, run worktree at `/ador/work`
  (working dir), the run's io exchange dir at `/ador/io` (gate scripts and
  captured event streams), cache volumes `ador-uv-cache` ->
  `/home/ador/.cache/uv` and `ador-npm-cache` -> `/home/ador/.npm`. ADOR
  creates the volumes itself (`ContainerManager.ensure_volumes`).
- Git inside the container is driven by `GIT_DIR` / `GIT_WORK_TREE` env (set
  by ADOR at provision), because the worktree's `.git` pointer file holds a
  host path that is invalid in the container.
- Secrets (model provider keys) are injected at `docker run` time only -
  never baked into this image, never on the command line (`--env KEY` with
  the value passed through the docker CLI's process environment).

## First-build verification checklist

Run once after building (all read-only):

```bash
docker run --rm ador-executor:latest python --version    # Python 3.11.x
docker run --rm ador-executor:latest uv --version
docker run --rm ador-executor:latest node --version      # v20.x
docker run --rm ador-executor:latest git --version
docker run --rm ador-executor:latest opencode --version
docker run --rm ador-executor:latest glab --version
docker run --rm ador-executor:latest whoami              # ador
```

Notes:

- The `glab` .deb download URL pattern should be confirmed on first build; if
  the release layout changed, adjust the `GLAB_VERSION` ARG / URL in the
  Dockerfile (the adapter itself runs glab on the HOST; in-container glab is
  optional).
- The image deliberately contains no opencode configuration: the target
  repo's `opencode.json` (with push/pr/merge/publish denied) comes in with
  the worktree.
