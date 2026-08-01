#!/usr/bin/env python3
# -*- coding: utf-8 -*-  # noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file profiles.py
@brief Runtime-project profiles: the cross-platform store that lets one ADORE
       install serve many projects (Assisted_Config_And_Profiles_Plan, task 1).
@details A profile is a named `config.toml` plus a `profile.json` metadata
         sidecar, living under a global ADORE config home:
           - Windows: %APPDATA%\\adore  (fallback %LOCALAPPDATA%\\adore)
           - Linux:   $XDG_CONFIG_HOME/adore  (default ~/.config/adore)
           - Override: the ADORE_HOME environment variable (both OSes; tests).
         `<home>/profiles/<name>/` holds config.toml + profile.json; an
         `<home>/active_profile` file names the current default. This module is
         the persistence foundation used by the `adore init` wizard and the
         `adore profile` CLI. Corrupt metadata fails closed (ProfileError), never a
         silent reinitialize - same contract as StateStore.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, fields
import json
import os
from pathlib import Path

from adore import __version__
from adore.branding import PRODUCT_SLUG, PROFILE_HOME_ENV
from adore.util import force_rmtree, utc_now_iso

# CONSTANTS

CONFIG_FILE = "config.toml"
METADATA_FILE = "profile.json"
PROFILES_DIR = "profiles"
ACTIVE_POINTER = "active_profile"
DEFAULT_CONFIG_NAME = "config.toml"

_ENV_HOME = PROFILE_HOME_ENV
_ENV_APPDATA = "APPDATA"
_ENV_LOCALAPPDATA = "LOCALAPPDATA"
_ENV_XDG = "XDG_CONFIG_HOME"

# DATA MODELS / TYPEDEFINITIONS


class ProfileError(RuntimeError):
    """
    @brief   Raised when a profile is missing or its metadata is corrupt.
    @details Fail-closed signal (same shape as StateError / ForgeError /
             IsolationError): the caller reports it, never guesses or silently
             recreates a profile.
    """


@dataclass
class Profile:
    """
    @brief   Metadata sidecar for one runtime-project profile (profile.json).
    @details Describes the project the config.toml targets plus lightweight
             usage counters. Secret values NEVER live here (design decision
             D5): only env-key names belong in the config, tokens stay in .env.
             Rich run statistics (merged/failed/success-rate) are computed on
             demand from the project's metrics DB, not duplicated here.
    """

    name: str
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    last_used_at: str = ""
    use_count: int = 0
    platform: str = ""
    host: str = ""
    repo: str = ""
    runtime: str = ""
    host_os: str = ""
    adore_version: str = ""
    config_path: str = ""
    store_root: str = ""


# HELPER FUNCTIONS


_PROFILE_FIELDS = frozenset(f.name for f in fields(Profile))


def _profile_from_dict(data: dict, name: str) -> Profile:
    """
    @brief      Build a Profile from parsed JSON, tolerating unknown keys.
    @details    Forward-compatible like config loading: unknown keys are
                dropped and missing keys default. The directory name is the
                authoritative identity, so it always overrides any stored
                name.
    @param[in]  data Parsed profile.json mapping.
    @param[in]  name The profile's directory name (source of truth).
    @return     The reconstructed Profile.
    """
    known = {key: value for key, value in data.items() if key in _PROFILE_FIELDS}
    known["name"] = name
    return Profile(**known)


def _home_for(os_name: str, environ: Mapping[str, str]) -> Path:
    """
    @brief      Pure OS/env -> ADORE home decision (testable without globals).
    @details    Precedence: ADORE_HOME override, then the OS-native config dir
                (Windows %APPDATA%/%LOCALAPPDATA%, POSIX $XDG_CONFIG_HOME or
                ~/.config), each suffixed with "adore". Kept pure so tests can
                pass "nt"/"posix" and a fake environ instead of monkeypatching
                os.name (which would break pathlib process-wide).
    @param[in]  os_name Value of os.name ("nt" | "posix").
    @param[in]  environ Environment mapping to read overrides from.
    @return     The ADORE home directory (not created here).
    """
    override = environ.get(_ENV_HOME)
    if override:
        return Path(override)
    if os_name == "nt":
        base = environ.get(_ENV_APPDATA) or environ.get(_ENV_LOCALAPPDATA)
        if base:
            return Path(base) / PRODUCT_SLUG
        return Path.home() / "AppData" / "Roaming" / PRODUCT_SLUG
    xdg = environ.get(_ENV_XDG)
    if xdg:
        return Path(xdg) / PRODUCT_SLUG
    return Path.home() / ".config" / PRODUCT_SLUG


def adore_home() -> Path:
    """
    @brief      Resolve the global ADORE config home for the current host.
    @details    Read at call time so tests can point ADORE_HOME at a tmp dir;
                the branching logic lives in _home_for.
    @return     The ADORE home directory (not created here).
    """
    return _home_for(os.name, os.environ)


def resolve_config_path(
    explicit: str | None,
    profile: str | None,
    *,
    store: ProfileStore | None = None,
    cwd_default: str = DEFAULT_CONFIG_NAME,
) -> tuple[Path, str | None]:
    """
    @brief      Decide which config.toml a command should use (decision D3).
    @details    Precedence: an explicit `-c FILE` wins; then a named
                `--profile`; then the active-profile pointer; then the local
                ./config.toml. A named
                profile that does not exist fails closed; a stale active
                pointer (profile since deleted) falls through to the default
                rather than erroring.
    @param[in]  explicit The `-c/--config` value, or None.
    @param[in]  profile The `--profile` name, or None.
    @param[in]  store Profile store (defaults to the resolved adore_home()).
    @param[in]  cwd_default Fallback config filename in the working directory.
    @return     (config_path, resolved_profile_name_or_None).
    @exception  ProfileError When `profile` is named but does not exist.
    """
    if explicit:
        return Path(explicit), None
    store = store or ProfileStore()
    if profile:
        if not store.exists(profile):
            raise ProfileError(f"no such profile: {profile!r}")
        return store.config_path(profile), profile
    active = store.get_active()
    if active and store.exists(active):
        return store.config_path(active), active
    return Path(cwd_default), None


# PUBLIC API


class ProfileStore:
    """
    @brief   CRUD over runtime-project profiles under the ADORE config home.
    @details Persistence only: create/load/save/list/rename/delete a profile's
             metadata, manage the active-profile pointer, and expose the paths
             (config.toml, state dir) the wizard and CLI build on. Missing is
             not corrupt: load() raises ProfileError only when metadata exists
             but is unreadable; list_profiles() skips corrupt entries and
             invalid_profiles() reports them (mirrors StateStore).
    """

    def __init__(
        self,
        home: str | Path | None = None,
        *,
        now: Callable[[], str] = utc_now_iso,
    ) -> None:
        """
        @brief      Build the store rooted at an ADORE home.
        @param[in]  home Config home (defaults to adore_home()).
        @param[in]  now Timestamp function (injectable for deterministic tests).
        """
        self.home = Path(home) if home is not None else adore_home()
        self.profiles_dir = self.home / PROFILES_DIR
        self.active_pointer = self.home / ACTIVE_POINTER
        self._now = now

    # -- paths --------------------------------------------------------------------

    def profile_dir(self, name: str) -> Path:
        """
        @brief      The directory holding a profile's files.
        @param[in]  name Profile name.
        @return     `<home>/profiles/<name>`.
        """
        return self.profiles_dir / name

    def config_path(self, name: str) -> Path:
        """
        @brief      A profile's config.toml path (written by the wizard later).
        @param[in]  name Profile name.
        @return     `<home>/profiles/<name>/config.toml`.
        """
        return self.profile_dir(name) / CONFIG_FILE

    def default_store_root(self, name: str) -> Path:
        """
        @brief      The profile-owned state root (decision D2).
        @details    Keeps a project's runs/metrics/lock isolated under its
                    profile so statistics are trivially findable.
        @param[in]  name Profile name.
        @return     `<home>/profiles/<name>/state`.
        """
        return self.profile_dir(name) / "state"

    def _metadata_path(self, name: str) -> Path:
        """
        @brief      A profile's profile.json path.
        @param[in]  name Profile name.
        @return     `<home>/profiles/<name>/profile.json`.
        """
        return self.profile_dir(name) / METADATA_FILE

    # -- CRUD ---------------------------------------------------------------------

    def exists(self, name: str) -> bool:
        """
        @brief      Whether a profile's metadata is present.
        @param[in]  name Profile name.
        @return     True when profile.json exists.
        """
        return self._metadata_path(name).is_file()

    def create(self, name: str, *, overwrite: bool = False, **fields_: object) -> Profile:
        """
        @brief      Create and persist a new profile's metadata.
        @param[in]  name Profile name (directory identity).
        @param[in]  overwrite Allow replacing an existing profile.
        @param[in]  fields_ Optional Profile fields (repo, platform, runtime...).
        @return     The saved Profile (created_at/updated_at stamped).
        @exception  ProfileError When the profile exists and overwrite is False.
        """
        if self.exists(name) and not overwrite:
            raise ProfileError(f"profile already exists: {name!r}")
        allowed = {key: value for key, value in fields_.items() if key in _PROFILE_FIELDS}
        now = self._now()
        profile = Profile(name=name, adore_version=__version__, created_at=now, **allowed)
        self.save(profile)
        return profile

    def save(self, profile: Profile) -> None:
        """
        @brief      Persist a profile's metadata atomically, stamping updated_at.
        @param[in]  profile The Profile to write.
        """
        if not profile.created_at:
            profile.created_at = self._now()
        profile.updated_at = self._now()
        self._write_json(self._metadata_path(profile.name), asdict(profile))

    def load(self, name: str) -> Profile:
        """
        @brief      Load a profile's metadata.
        @param[in]  name Profile name.
        @return     The reconstructed Profile.
        @exception  ProfileError When the profile is missing or corrupt (fail
                    closed: reported, never reinitialized).
        """
        path = self._metadata_path(name)
        if not path.is_file():
            raise ProfileError(f"no such profile: {name!r}")
        try:
            with path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            raise ProfileError(f"corrupt profile.json for {name!r}: {exc}") from exc
        if not isinstance(data, dict):
            raise ProfileError(f"corrupt profile.json for {name!r}: not a JSON object")
        return _profile_from_dict(data, name)

    def list_profiles(self) -> list[Profile]:
        """
        @brief      All readable profiles, sorted by name.
        @details    Corrupt entries are skipped here (see invalid_profiles).
        @return     Loaded Profiles.
        """
        profiles: list[Profile] = []
        for name in self._profile_names():
            try:
                profiles.append(self.load(name))
            except ProfileError:
                continue
        return sorted(profiles, key=lambda profile: profile.name)

    def invalid_profiles(self) -> list[str]:
        """
        @brief      Names whose profile.json exists but fails to load.
        @details    The fail-closed counterpart of list_profiles(): these need
                    a human, not a silent recreate.
        @return     Sorted corrupt profile names.
        """
        broken: list[str] = []
        for name in self._profile_names():
            try:
                self.load(name)
            except ProfileError:
                broken.append(name)
        return sorted(broken)

    def touch(self, name: str) -> Profile:
        """
        @brief      Record a use: bump use_count and last_used_at.
        @param[in]  name Profile name.
        @return     The updated Profile.
        @exception  ProfileError When the profile is missing or corrupt.
        """
        profile = self.load(name)
        profile.use_count += 1
        profile.last_used_at = self._now()
        self.save(profile)
        return profile

    def rename(self, old: str, new: str) -> None:
        """
        @brief      Rename a profile (moves its whole directory).
        @details    The active pointer is repointed when it named the profile.
        @param[in]  old Existing profile name.
        @param[in]  new New profile name.
        @exception  ProfileError When old is missing or new already exists.
        """
        if not self.exists(old):
            raise ProfileError(f"no such profile: {old!r}")
        if self.exists(new):
            raise ProfileError(f"profile already exists: {new!r}")
        self.profile_dir(old).replace(self.profile_dir(new))
        profile = self.load(new)  # rewrite metadata name to match the new dir
        self.save(profile)
        if self.get_active() == old:
            self.set_active(new)

    def delete(self, name: str) -> None:
        """
        @brief      Remove a profile and everything under it (config + state).
        @details    Idempotent; clears the active pointer when it named the
                    profile. Uses the read-only/reparse-point-tolerant rmtree.
        @param[in]  name Profile name.
        """
        force_rmtree(self.profile_dir(name))
        if self.get_active() == name:
            self.clear_active()

    # -- active pointer -----------------------------------------------------------

    def get_active(self) -> str | None:
        """
        @brief      The active profile name, if one is set and still exists.
        @return     The active name, or None.
        """
        if not self.active_pointer.is_file():
            return None
        name = self.active_pointer.read_text(encoding="utf-8").strip()
        return name or None

    def set_active(self, name: str) -> None:
        """
        @brief      Set the active profile.
        @param[in]  name Profile name (must exist).
        @exception  ProfileError When the profile does not exist.
        """
        if not self.exists(name):
            raise ProfileError(f"no such profile: {name!r}")
        self.home.mkdir(parents=True, exist_ok=True)
        self.active_pointer.write_text(name + "\n", encoding="utf-8")

    def clear_active(self) -> None:
        """
        @brief      Unset the active profile (idempotent).
        """
        self.active_pointer.unlink(missing_ok=True)

    # -- internals ----------------------------------------------------------------

    def _profile_names(self) -> list[str]:
        """
        @brief      Directory names under `profiles/` that hold metadata.
        @return     Candidate profile names (unsorted).
        """
        if not self.profiles_dir.is_dir():
            return []
        return [
            entry.name
            for entry in self.profiles_dir.iterdir()
            if entry.is_dir() and (entry / METADATA_FILE).is_file()
        ]

    def _write_json(self, path: Path, data: dict) -> None:
        """
        @brief      Write JSON atomically (tmp file + replace).
        @param[in]  path Destination file.
        @param[in]  data JSON-serializable mapping.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        tmp.replace(path)


# END OF FILE
