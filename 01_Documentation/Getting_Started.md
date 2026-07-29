<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Getting Started With ADORE

Use this guide to prepare a host, install ADORE, create the first
runtime-project profile, and prove a safe poll. It is intentionally generic:
use one profile per target project and substitute the placeholders shown below.

## The Operating Model

ADORE runs from one host installation and can manage multiple target projects.
Each target project has a named **profile** containing its non-secret
configuration, state location, metrics, and selected container image.

An operator should establish this sequence before enabling unattended polling:

1. Prepare the host, runtime project clone, and project image.
2. Authenticate the forge CLI and provide executor credentials.
3. Create and validate a profile.
4. Run a dry run, then one supervised real poll.
5. Enable scheduled or loop operation only after the first delivery cycle is
   understood.

## 1. Prepare the Run-As Account

Install and operate ADORE under the same ordinary user account that will run the
scheduled task or service. That account needs access to:

- Git and a local clone of `<runtime-project>`;
- Python 3.11 or newer and `uv`;
- Docker or Podman;
- `glab` for GitLab, `gh` for GitHub, or `tea` (>= 0.15) for Gitea;
- the chosen executor's credentials; and
- the container runtime socket or rootless runtime environment.

On Windows, ADORE can use Docker Desktop, a native Docker engine, or a Docker
engine exposed through WSL. For a WSL-backed engine, configure the runtime
command in the profile, for example `wsl -d <distribution> -- docker`.

Verify the tools from the run-as account:

```powershell
git --version
python --version
uv --version
glab auth status
docker version
```

```bash
git --version
python3 --version
uv --version
gh auth status
docker version
```

For Gitea, the auth check is `tea whoami` (tea has no `auth status`
subcommand). Use the CLI appropriate to the selected forge; the commands above
show the options, not a requirement to install them all.

## 2. Install the Runtime Bundle

Unpack the ADORE runtime bundle into a directory owned by the run-as account.
Replace `<version>` with the release being installed.

```powershell
Expand-Archive -LiteralPath C:\Downloads\adore-runtime-<version>.zip `
  -DestinationPath D:\Tools\ADORE
Set-Location D:\Tools\ADORE\adore-runtime-<version>
uv sync --frozen
.\.venv\Scripts\adore.exe --version
```

```bash
mkdir -p ~/tools/adore
tar -xzf ~/Downloads/adore-runtime-<version>.tar.gz -C ~/tools/adore
cd ~/tools/adore/adore-runtime-<version>
uv sync --frozen
./.venv/bin/adore --version
```

The command should report the installed release, for example `adore 1.2.0`.
Keep the runtime directory available: deployed services and scheduled tasks use
it as their working directory.

## 3. Build the Execution Images

ADORE supplies a reusable base image. Each target project should provide or
adopt an image that adds the project-specific build and verification tools.

Build the base image from the unpacked runtime directory:

```bash
docker build \
  --build-arg USER_UID=$(id -u) \
  --build-arg USER_GID=$(id -g) \
  -f docker/Dockerfile.executor-base \
  -t adore-executor-base:1.0.0 \
  docker
```

Build the project image using its own Dockerfile and context:

```bash
docker build \
  -f <project-dockerfile> \
  -t adore-executor-<runtime-project>:<tag> \
  <project-build-context>
```

For Podman, use `podman` in place of `docker`. Rootless Podman profiles should
normally include `run_args = ["--userns=keep-id"]`; see
[Configuration_Reference.md](Configuration_Reference.md).

## 4. Establish Credentials Before Running Work

Authenticate `glab`, `gh` or `tea` under the run-as account, then configure
the selected executor's model-provider credential. Do this before creating the
first real run.

Read [Security_And_Credentials.md](Security_And_Credentials.md) before placing
any secret. In particular, executor secrets may be loaded from `.env` in the
ADORE runtime working directory, while forge authentication is normally handled
by the forge CLI's authenticated host session or a real process environment.

## 5. Create a Runtime-Project Profile

Run the guided setup from the ADORE runtime directory:

```powershell
.\.venv\Scripts\adore.exe init <profile-name>
```

```bash
./.venv/bin/adore init <profile-name>
```

During the wizard, choose:

| Area | Decision |
| --- | --- |
| Profile | A short, distinct name for the target project. |
| Forge | The forge matching the authenticated CLI. |
| Runtime project | The local clone path and repository identifier. |
| State | Profile-owned state unless the team deliberately needs it beside the clone. |
| Runtime | The Docker or Podman command verified on this host. |
| Image | The target project's image, not merely the generic base image. |
| Executor | An executor and model approved for the target project. |
| Auth | `api-key` for provider keys; `host-auth` only where supported by the selected executor. |
| Run mode | `once` while the project is being proven. |

The wizard writes no secret values to the profile. For non-interactive setup,
use `adore init <profile-name> --answers <answers.toml>`.

## 6. Select, Validate, and Prove the Profile

Make the new profile active for interactive use, but keep `--profile` in
automation and first-run commands:

```powershell
.\.venv\Scripts\adore.exe profile use <profile-name>
.\.venv\Scripts\adore.exe --profile <profile-name> config validate
.\.venv\Scripts\adore.exe --profile <profile-name> run --dry-run
.\.venv\Scripts\adore.exe --profile <profile-name> run --once
```

```bash
./.venv/bin/adore profile use <profile-name>
./.venv/bin/adore --profile <profile-name> config validate
./.venv/bin/adore --profile <profile-name> run --dry-run
./.venv/bin/adore --profile <profile-name> run --once
```

Do not enable a background runner until validation is clean, the dry run shows
the intended ticket selection, and the supervised poll behaves as expected.

## Next Steps

- Configure the target project completely in
  [Integrating_A_Runtime_Project.md](Integrating_A_Runtime_Project.md).
- Learn normal monitoring, review, and scheduling in
  [Operations_Guide.md](Operations_Guide.md).
- Use [Recovery_And_Maintenance.md](Recovery_And_Maintenance.md) when a run
  needs intervention.
- Use the deployment scripts in `04_Software/deploy/` only after completing the
  safe first-run sequence above.
