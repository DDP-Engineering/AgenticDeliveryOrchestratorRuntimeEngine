<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Setup And First Run

Applies to ADOR 0.5.1.

Use this when you are preparing a host, creating a runtime-project profile, or
validating the first safe ADOR poll against a project.

![ADOR setup flow](assets/operator-flow.svg)

## Operator Goal

End this flow with one validated profile, one dry run, and one supervised poll.
Do not install a background runner until those three checks are clean.

## Before ADOR

Confirm these are available to the same user account that will run ADOR:

- Git.
- Python 3.11 or newer.
- `uv`.
- A container runtime: Docker or Podman.
- A forge CLI: `glab` for GitLab or `gh` for GitHub.
- A local clone of the runtime project.
- Executor credentials supplied through environment variables or `.env`.
- A project image with the runtime project's tools.

Quick checks:

```powershell
git --version
python --version
glab auth status
docker version
```

```bash
git --version
python3 --version
gh auth status
docker version
```

## First Setup Pass

Create or refresh the locked Python environment from the unpacked ADOR runtime:

```powershell
uv sync --frozen
.\.venv\Scripts\ador.exe --version
```

```bash
uv sync --frozen
./.venv/bin/ador --version
```

Expected version:

```text
ador 0.5.1
```

## Create The Profile

The wizard writes a runtime-project profile under the ADOR config home. It does
not store secret values, only the names of environment variables that ADOR may
inject into executor containers.

```powershell
.\.venv\Scripts\ador.exe init <profile-name>
```

```bash
./.venv/bin/ador init <profile-name>
```

Choose:

| Wizard area | Recommended first-run answer |
| --- | --- |
| Profile identity | Short lowercase project name. |
| Forge | Match the authenticated CLI, GitLab or GitHub. |
| Runtime project | Local clone path plus repo name. |
| State location | Profile-owned state. |
| Container runtime | Docker or Podman command that works from this host. |
| Container image | Runtime-project image, not only the generic base image. |
| Executor | `opencode` unless the project has chosen another implemented executor. |
| Run mode | `once` for validation. |

## Validate Before Pickup

```powershell
.\.venv\Scripts\ador.exe --profile <profile-name> config validate
.\.venv\Scripts\ador.exe profile show <profile-name>
```

```bash
./.venv/bin/ador --profile <profile-name> config validate
./.venv/bin/ador profile show <profile-name>
```

Do not continue until validation prints `OK`.

## Dry Run

Dry run checks ticket visibility and selection without starting delivery work.

```powershell
.\.venv\Scripts\ador.exe --profile <profile-name> run --dry-run
```

```bash
./.venv/bin/ador --profile <profile-name> run --dry-run
```

Look for:

- ADOR can load the profile.
- ADOR can read tickets.
- Control labels such as `agent-hold` and `no-agent` are respected.
- Readiness filters explain why a ticket is or is not eligible.

## Supervised First Poll

Run exactly one real poll while watching the terminal and ticket:

```powershell
.\.venv\Scripts\ador.exe --profile <profile-name> run --once
```

```bash
./.venv/bin/ador --profile <profile-name> run --once
```

Then monitor:

```powershell
.\.venv\Scripts\ador.exe --profile <profile-name> status
.\.venv\Scripts\ador.exe --profile <profile-name> runs
```

```bash
./.venv/bin/ador --profile <profile-name> status
./.venv/bin/ador --profile <profile-name> runs
```

## Safe Completion

After ADOR opens a draft MR/PR:

- Review the draft like any human-authored change.
- Request revisions with the configured revise label, normally `agent-revise`.
- Merge manually only when the human review decision is complete.
- Run `ador cleanup` after closed or merged work if you want a resource sweep.
