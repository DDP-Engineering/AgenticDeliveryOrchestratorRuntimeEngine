<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Runtime-Project Profiles (`adore/profiles.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/profiles.py`.
> Scope note: this component is the **persistence foundation**. The pieces built
> on it are documented separately: the `adore init` wizard in Component_Wizard.md;
> environment detection/guidance in Component_Doctor.md; the `adore profile`
> commands + `--profile` resolution + per-profile statistics in Component_CLI.md;
> the operator integration guide in
> `01_Documentation/Integrating_A_Runtime_Project.md`.

## 1. Purpose

Let one ADORE install serve many target projects. A **runtime-project profile**
is a named `config.toml` plus a `profile.json` metadata sidecar, stored under a
global, cross-platform ADORE config home. This module owns the store: resolving
the home, CRUD over profiles, the active-profile pointer, and the config-path
resolution order that lets every command target a chosen profile.

## 2. Responsibilities

- `adore_home()` - resolve the global config home (delegates to the pure
  `_home_for(os_name, environ)`): `ADORE_HOME` override, else Windows
  `%APPDATA%`/`%LOCALAPPDATA%`\\adore, else POSIX `$XDG_CONFIG_HOME`/`~/.config`
  /adore.
- `Profile` - the `profile.json` metadata (immutable `project_id`, name, description, created/updated/
  last-used timestamps, use_count, platform/host/repo/runtime/host_os,
  adore_version, config_path, store_root, archived). **No secret values ever**.
- `ProfileStore` - `create/save/load/list_profiles/invalid_profiles/touch/
  rename/delete`, the active pointer (`get_active/set_active/clear_active`), and
  path helpers (`profile_dir/config_path/default_store_root`).
- `resolve_config_path(explicit, profile, store, cwd_default)`:
  explicit `-c FILE` > `--profile NAME` > active pointer > `./config.toml`.
- `ProfileError` - fail-closed error for a missing or corrupt profile.

Explicitly not owned: prompting/config generation (the wizard), command parsing
(the CLI), and metric aggregation (the metrics component). Those implemented
components use this store; they do not duplicate its persistence rules.

## 3. Implementation Overview

- **Layout:** `<home>/profiles/<name>/{config.toml, profile.json}` plus
  `<home>/active_profile` (a one-line pointer file).
- **Profile-owned state (D2):** `default_store_root(name)` is
  `<home>/profiles/<name>/state`, so a project's runs/metrics/lock stay isolated
  and its statistics are trivially findable.
- **Fail-closed, same as StateStore:** `load()` raises `ProfileError` when
  metadata exists but is unreadable, not an object, written by another build or
  invalid; a missing profile is a distinct error. `list_profiles()` skips corrupt entries; `invalid_profiles()`
  reports them - never a silent reinitialize.
- **Atomic writes:** `profile.json` is written to a `.tmp` file then `replace()`d.
- **No migrations:** `profile.json` must carry exactly the `Profile` fields.
  Unknown or missing keys are refused with `profile.json of project X was
  written by another ADORE build (unknown keys [...], missing keys [...]);
  delete or fix that file`. The directory name is the authoritative profile
  label (overrides any stored `name`). `create()` assigns a random 128-bit
  project ID; `save()` requires one and refuses a malformed ID. Renaming
  retains the stored ID. A malformed stored ID or a non-boolean `archived` is
  corrupt metadata and raises `ProfileError`.
- **Deletes** use the read-only/reparse-point-tolerant `force_rmtree` and clear
  the active pointer when they remove the active profile; **renames** move the
  whole directory and repoint the active pointer.

## 4. Dependencies

- Internal: `adore.util` (`utc_now_iso`, `force_rmtree`), `adore.__version__`.
- External: Python standard library only (`json`, `os`, `pathlib`,
  `dataclasses`).

## 5. Inputs And Outputs

- Inputs: a home path (defaults to `adore_home()`), profile names + metadata
  fields, an injectable `now` clock.
- Outputs: profile directories with `profile.json`, the `active_profile`
  pointer, resolved config paths.

## 6. Data Contracts

- `profile.json` schema = the `Profile` dataclass fields in
  `adore/profiles.py`. Secret values are never persisted.
- The config-path resolution order (D3) is stable and script-safe; when no
  profile is used it returns `./config.toml`, preserving single-config behavior.

## 7. Workflow Integration

The foundation the assisted-config feature stands on: the wizard (task 3) calls
`ProfileStore.create` + writes `config_path(name)`; the CLI (task 4) wires
`resolve_config_path` into `_load` and bumps `touch()` on use; statistics (task
5) read each profile's metrics DB under `default_store_root`.

## 8. Usage

```python
from adore.profiles import ProfileStore, resolve_config_path

store = ProfileStore()                      # ADORE_HOME / %APPDATA% / ~/.config
store.create("<profile-name>", platform="gitlab", repo="<group>/<repository>", runtime="docker")
store.set_active("<profile-name>")

path, used = resolve_config_path(None, None, store=store)   # -> the active profile
store.touch("<profile-name>")               # record a use (use_count, last_used_at)
```

## 9. Validation And Tests

- `tests/test_profiles.py` (offline, tmp `ADORE_HOME`, fixed clock): home
  resolution for override / Windows / POSIX shapes via the pure `_home_for`
  (never patches `os.name`, which would break pathlib); CRUD round-trip;
  duplicate-create refusal; rename + delete with active-pointer consistency;
  active-pointer lifecycle; the full resolution-order matrix; and fail-closed on
  corrupt/missing `profile.json`, refusal of a `profile.json` of another build
  (`test_profile_json_of_another_build_is_refused`), the directory name
  overriding the stored name and stable project identity across renames
  (`test_profile_identity_survives_rename_and_bad_ids_fail`).
- Minimum validation after a change:
  `uv run --group dev pytest tests/test_profiles.py` + `ruff check .`.

## 10. Limitations And Future Work

- The wizard, `adore profile` CLI, `--profile` global flag, and per-profile
  statistics are implemented in their respective components.
- ProfileStore provides atomic metadata replacement. Web enrollment serializes
  creation with its home-wide enrollment lock; display edits use the shared
  config edit lock. Direct host/CLI writes must respect their operator ownership.

## Web display identity and ID availability

`Profile.display_name` is a human label independent of directory `name` and the
immutable `project_id`. The key is required like every other `profile.json`
key; an invalid value makes metadata corrupt. `save()` stores the profile name
when no display name is given. Labels contain 1–120 Unicode
characters, are trimmed, and contain no Unicode control/format characters.
`validate_display_name()` raises `ProfileError` with `invalid_display_name` and
field `display_name`, without including input values.

`validate_profile_id()` validates web IDs: lowercase ASCII letters/digits first,
then letters/digits/dot/underscore/hyphen, at most 64 characters. Trailing dots,
Windows device stems (including extensions), 32-hex identity aliases and reserved
route names (including `setup-check`, `setup-create`, `transfer-source`, `transfer-preview`,
`transfer-check` and `transfer-create`) are rejected.
`ProfileStore.id_availability()` checks complete and incomplete filesystem
entries case-insensitively, immutable IDs and corrupt or
duplicate metadata. Availability is advisory; the web publication lock rechecks
it before creating a directory. CLI rename retains its separate behavior.

Public transfer route-name coverage: `test_web_transfer.py`.
Public contract coverage: `test_web_enrollment.py` exercises display edits that
keep membership, operations and paths, corrupt labels, portable IDs, incomplete ownership and preserved grants/operations.
