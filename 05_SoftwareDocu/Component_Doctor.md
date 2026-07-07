<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Environment Doctor (`ador/doctor.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/ador/doctor.py` - file version 0.1.1.
> Plan: `00_Planning/Assisted_Config_And_Profiles_Plan.md` (task 2 of 8).
> Scope note: the **detection + guidance data/text layer**. The `ador init`
> wizard (task 3) consumes it to decide what to ask and what to print; a future
> `ador doctor` command can render the same aggregate. No prompting lives here.

## 1. Purpose

Answer two questions the assisted-setup flow needs, without doing any prompting
itself: **"is prerequisite X installed / authenticated on this host?"** and
**"what are the exact, OS-specific steps to fix it?"** It probes the tools ADOR
depends on and supplies the install/setup instructions from the plan's Phase A.

## 2. Responsibilities

- **Detection** (all through the injectable `CommandRunner`, so tests run
  offline): `detect_os()`, `detect_git()`, `detect_runtimes()` (docker/podman
  + WSL distros on Windows), `detect_platform_cli(kind)`, `auth_status(kind)`,
  `detect_executor()`, and `detect_all(kind)` (one probe of each -> an
  `EnvironmentReport`).
- **Guidance** (curated data): `guidance_for(component, os_key)` returns the
  Windows/Ubuntu install/setup text; `auth_component_for_kind(kind)` maps a
  platform kind to its token/login guidance key.
- Typed results: `ToolStatus`, `AuthStatus`, `RuntimeDetection`,
  `EnvironmentReport`.

Explicitly not owned: prompting/wizard flow (task 3), CLI wiring, writing config.

## 3. Implementation Overview

- **Probe convention:** `_probe` runs `<tool> --version` through the runner and
  reads `run_command`'s exit-code contract - `127` = binary missing (absent),
  `0` = present (first stdout line is the version), other non-zero = present but
  erroring. No raw subprocess calls here.
- **Auth:** `auth_status` runs `glab auth status` / `gh auth status`; `127` =
  CLI missing, `0` = authenticated, else present-but-not-authenticated.
- **WSL distros:** `wsl -l -q` emits UTF-16 on some hosts; the decoded output is
  scrubbed of null bytes / BOM and blank lines before returning names. WSL is
  probed only when `os_key == "windows"`.
- **Guidance shape:** `GUIDANCE[component]` is either OS-keyed (`windows` /
  `linux`, non-Windows OSes fall back to Linux) or a single `"*"` entry for
  OS-independent steps (token creation, opencode). Unknown components return a
  graceful fallback, never a `KeyError`.
- **OS key** is derived by the pure `_os_key(system_name)` (Windows/Linux/macOS/
  other), mirroring task 1's "pure function, no global patching" approach.

## 4. Dependencies

- Internal: `ador.util` (`CommandRunner`, `run_command`, `CommandResult`).
- External: Python standard library only (`platform`, `dataclasses`).

## 5. Inputs And Outputs

- Inputs: a platform `kind` (`gitlab`/`github`), an injectable runner, optional
  `os_key`.
- Outputs: typed detection results and guidance strings. No files, no side
  effects, no network of its own (only the probe commands the runner executes).

## 6. Data Contracts

- The guidance components (`GIT`, `DOCKER`, `PODMAN`, `WSL`, `GLAB`, `GH`,
  `GLAB_AUTH`, `GH_AUTH`, `OPENCODE`) are stable keys the wizard references.
- Token guidance never asks for or echoes a secret value - it states the format
  (e.g. `glpat-` + 20 chars) and says the wizard records the key NAME only
  (design D5).

## 7. Workflow Integration

`ador init` (task 3): for each phase-A prerequisite, call the matching
`detect_*`; if absent/unauthenticated, print `guidance_for(component, os_key)`
and let the user fix it before continuing. `detect_all` + guidance also back a
future read-only `ador doctor` command.

## 8. Usage

```python
from ador import doctor

report = doctor.detect_all("gitlab")
if not report.auth.authenticated:
    print(doctor.guidance_for(doctor.auth_component_for_kind("gitlab"),
                              report.os_key))
```

## 9. Validation And Tests

- `tests/test_doctor.py` (offline, fake runner keyed by argv prefix): OS-key
  mapping; git/executor present-vs-absent; `detect_platform_cli` kind mapping +
  unknown-kind `ValueError`; auth authenticated / present-not-authenticated /
  missing; runtimes with WSL distro parsing (incl. null-byte scrub) on Windows
  and WSL-skipped on Linux; `detect_all` aggregate; guidance OS-specificity, the
  shared token text (asserts `glpat-` + "never the value"), and the graceful
  unknown-component fallback.
- Minimum validation after a change:
  `uv run --group dev pytest tests/test_doctor.py` + `ruff check .`.

## 10. Limitations And Future Work

- Detection reports presence/auth, not tool VERSIONS-vs-requirements; a
  `required_tools`-style version check (backlog) would extend `_probe`.
- WSL-internal runtime probing (docker/podman INSIDE a distro) is left to the
  wizard/E2E task; `detect_runtimes` reports host runtimes + distro names.
- Install commands are curated text; task 7 (cross-platform E2E) verifies they
  are current on Windows and Ubuntu.
