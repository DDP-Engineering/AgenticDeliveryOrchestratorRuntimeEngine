<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Environment Doctor (`adore/doctor.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/doctor.py` - file version 0.2.0
> (`auth_status` 0.2.0: kind-dispatched probes incl. gitea/tea).
> Historical design source: `00_Planning/Assisted_Config_And_Profiles_Plan.md`.
> Scope note: the **detection + guidance data/text layer**. The `adore init`
> wizard (task 3) consumes it to decide what to ask and what to print; a future
> `adore doctor` command can render the same aggregate. No prompting lives here.

## 1. Purpose

Answer two questions the assisted-setup flow needs, without doing any prompting
itself: **"is prerequisite X installed / authenticated on this host?"** and
**"what are the exact, OS-specific steps to fix it?"** It probes the tools ADORE
depends on and supplies the install/setup instructions from the plan's Phase A.

## 2. Responsibilities

- **Detection** (all through the injectable `CommandRunner`, so tests run
  offline): `detect_os()`, `detect_git()`, `detect_runtimes()` (docker/podman
  + WSL distros on Windows), `detect_platform_cli(kind)`, `auth_status(kind)`,
  `detect_aegis(repo_path)`,
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
- **Auth:** `auth_status` runs the KIND-SPECIFIC probe (`glab auth status` /
  `gh auth status` / `tea whoami`); `127` = CLI missing, `0` = authenticated,
  else present-but-not-authenticated. The probe argv is per kind because tea
  has no `auth status` subcommand - and tea exits `0` even for unknown
  subcommands ("No help topic"), so a generic `<cli> auth status` would
  falsely report Gitea as authenticated (`tea whoami` actually calls the API
  with the stored token).
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

- Internal: `adore.util` (`CommandRunner`, `run_command`, `CommandResult`).
- External: Python standard library only (`platform`, `dataclasses`).

## 5. Inputs And Outputs

- Inputs: a platform `kind` (`gitlab`/`github`/`gitea`), an injectable runner,
  optional `os_key`.
- Outputs: typed detection results and guidance strings. No files, no side
  effects, no network of its own (only the probe commands the runner executes).

## 6. Data Contracts

- The guidance components (`GIT`, `DOCKER`, `PODMAN`, `WSL`, `GLAB`, `GH`,
  `TEA`, `GLAB_AUTH`, `GH_AUTH`, `TEA_AUTH`, `OPENCODE`) are stable keys the
  wizard references.
- Token guidance never asks for or echoes a secret value - it states the format
  (e.g. `glpat-` + 20 chars) and says the wizard records the key NAME only
  (design D5).

- **AEGIS 3.x target-repository probe** (`detect_aegis`, ADORE 3.0 WP6):
  three facts, all required before a repository can be conducted - the POSIX
  wrapper `.agentic/tools/run.sh` exists, `bash .agentic/tools/run.sh --json
  config validate` answers `status: ok`, and the policy it validated reports
  `schema_version: 3`. The command runs with the repository as its working
  directory, which is where AEGIS discovers its root. Everything crosses a
  trust boundary, so a non-zero exit, unparseable output, a blocked response,
  or a different schema is reported as not-ready with the AEGIS detail
  preserved - never silently accepted. This replaces every AEGIS 1.x verb
  probe; there is no 1.x detection and no migration path.

## 7. Workflow Integration

`adore init`: for each prerequisite, call the matching
`detect_*`; if absent/unauthenticated, print `guidance_for(component, os_key)`
and let the user fix it before continuing. `detect_all` + guidance also back a
future read-only `adore doctor` command.

## 8. Usage

```python
from adore import doctor

report = doctor.detect_all("gitlab")
if not report.auth.authenticated:
    print(doctor.guidance_for(doctor.auth_component_for_kind("gitlab"),
                              report.os_key))
```

## 9. Validation And Tests

- `tests/test_doctor.py` (offline, fake runner keyed by argv prefix): OS-key
  mapping; git/executor present-vs-absent; `detect_platform_cli` kind mapping
  (incl. gitea -> tea) + unknown-kind `ValueError`; auth authenticated /
  present-not-authenticated / missing; a regression pin that the gitea probe
  is `tea whoami` (never `tea auth status`, which tea would answer with exit 0
  and a help-topic message); runtimes with WSL distro parsing (incl. null-byte
  scrub) on Windows and WSL-skipped on Linux; `detect_all` aggregate; guidance
  OS-specificity, the shared token texts (asserts `glpat-` + "never the
  value", `tea login add` + the `[platform] login` alternative), and the
  graceful unknown-component fallback. AEGIS probe: a valid schema-3 payload
  accepted (asserting the exact argv and that it runs in the repository), a
  missing wrapper reported without running any command, a blocked
  `config validate` and an unparseable answer both failing closed with the
  detail preserved, a schema other than 3 rejected, and the guidance naming
  WAEGIS while stating plainly that AEGIS 1.x is unsupported.
- Minimum validation after a change:
  `uv run --group dev pytest tests/test_doctor.py` + `ruff check .`.

## 10. Limitations And Future Work

- Detection reports presence/auth, not tool VERSIONS-vs-requirements; a
  `required_tools`-style version check (backlog) would extend `_probe`.
- WSL-internal runtime probing (docker/podman INSIDE a distro) is left to the
  wizard/E2E task; `detect_runtimes` reports host runtimes + distro names.
- Install commands are curated text and should be re-verified when their
  referenced tools or supported operating systems change.
