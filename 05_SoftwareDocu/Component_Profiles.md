<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Runtime-Project Profiles (`ador/profiles.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/ador/profiles.py` - file version 0.1.0.
> Plan: `00_Planning/Assisted_Config_And_Profiles_Plan.md` (task 1 of 8; all
> tasks complete).
> Scope note: this component is the **persistence foundation**. The pieces built
> on it are documented separately: the `ador init` wizard in Component_Wizard.md;
> environment detection/guidance in Component_Doctor.md; the `ador profile`
> commands + `--profile` resolution + per-profile statistics in Component_CLI.md;
> the operator/onboarding guide in `00_Planning/Onboarding_New_Project.md`.

## 1. Purpose

Let one ADOR install serve many target projects. A **runtime-project profile**
is a named `config.toml` plus a `profile.json` metadata sidecar, stored under a
global, cross-platform ADOR config home. This module owns the store: resolving
the home, CRUD over profiles, the active-profile pointer, and the config-path
resolution order that lets every command target a chosen profile.

## 2. Responsibilities

- `ador_home()` - resolve the global config home (delegates to the pure
  `_home_for(os_name, environ)`): `ADOR_HOME` override, else Windows
  `%APPDATA%`/`%LOCALAPPDATA%`\\ador, else POSIX `$XDG_CONFIG_HOME`/`~/.config`
  /ador.
- `Profile` - the `profile.json` metadata (name, description, created/updated/
  last-used timestamps, use_count, platform/host/repo/runtime/host_os,
  ador_version, config_path, store_root). **No secret values ever** (design D5).
- `ProfileStore` - `create/save/load/list_profiles/invalid_profiles/touch/
  rename/delete`, the active pointer (`get_active/set_active/clear_active`), and
  path helpers (`profile_dir/config_path/default_store_root`).
- `resolve_config_path(explicit, profile, store, cwd_default)` - decision D3:
  explicit `-c FILE` > `--profile NAME` > active pointer > `./config.toml`.
- `ProfileError` - fail-closed error for a missing or corrupt profile.

Explicitly not owned (later tasks): prompting/wizard, CLI wiring, statistics
aggregation, and writing the `config.toml` body.

## 3. Implementation Overview

- **Layout:** `<home>/profiles/<name>/{config.toml, profile.json}` plus
  `<home>/active_profile` (a one-line pointer file).
- **Profile-owned state (D2):** `default_store_root(name)` is
  `<home>/profiles/<name>/state`, so a project's runs/metrics/lock stay isolated
  and its statistics are trivially findable.
- **Fail-closed, same as StateStore:** `load()` raises `ProfileError` only when
  metadata exists but is unreadable/not-an-object; a missing profile is a
  distinct error. `list_profiles()` skips corrupt entries; `invalid_profiles()`
  reports them - never a silent reinitialize.
- **Atomic writes:** `profile.json` is written to a `.tmp` file then `replace()`d.
- **Forward compatible:** unknown keys in `profile.json` are dropped on load and
  the directory name is the authoritative identity (overrides any stored `name`).
- **Deletes** use the read-only/reparse-point-tolerant `force_rmtree` and clear
  the active pointer when they remove the active profile; **renames** move the
  whole directory and repoint the active pointer.

## 4. Dependencies

- Internal: `ador.util` (`utc_now_iso`, `force_rmtree`), `ador.__version__`.
- External: Python standard library only (`json`, `os`, `pathlib`,
  `dataclasses`).

## 5. Inputs And Outputs

- Inputs: a home path (defaults to `ador_home()`), profile names + metadata
  fields, an injectable `now` clock.
- Outputs: profile directories with `profile.json`, the `active_profile`
  pointer, resolved config paths.

## 6. Data Contracts

- `profile.json` schema = the `Profile` dataclass fields (see
  `Assisted_Config_And_Profiles_Plan.md` §5). Secret values are never persisted.
- The config-path resolution order (D3) is stable and script-safe; when no
  profile is used it returns `./config.toml`, preserving single-config behavior.

## 7. Workflow Integration

The foundation the assisted-config feature stands on: the wizard (task 3) calls
`ProfileStore.create` + writes `config_path(name)`; the CLI (task 4) wires
`resolve_config_path` into `_load` and bumps `touch()` on use; statistics (task
5) read each profile's metrics DB under `default_store_root`.

## 8. Usage

```python
from ador.profiles import ProfileStore, resolve_config_path

store = ProfileStore()                      # ADOR_HOME / %APPDATA% / ~/.config
store.create("sample-project", platform="gitlab", repo="grp/proj", runtime="docker")
store.set_active("sample-project")

path, used = resolve_config_path(None, None, store=store)   # -> the active profile
store.touch("sample-project")               # record a use (use_count, last_used_at)
```

## 9. Validation And Tests

- `tests/test_profiles.py` (offline, tmp `ADOR_HOME`, fixed clock): home
  resolution for override / Windows / POSIX shapes via the pure `_home_for`
  (never patches `os.name`, which would break pathlib); CRUD round-trip;
  duplicate-create refusal; rename + delete with active-pointer consistency;
  active-pointer lifecycle; the full resolution-order matrix; and fail-closed on
  corrupt/missing `profile.json` plus unknown-key tolerance.
- Minimum validation after a change:
  `uv run --group dev pytest tests/test_profiles.py` + `ruff check .`.

## 10. Limitations And Future Work

- Persistence only in this task; the wizard, `ador profile` CLI, `--profile`
  global flag, and statistics land in plan tasks 3-5.
- No cross-process locking on the profile store itself (profiles are edited by a
  single operator, unlike the per-run state lock); revisit if concurrent setup
  ever matters.
