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
@file test_profiles.py
@brief Tests for the runtime-project profile store (config home, CRUD, active
       pointer, config-path resolution) - all offline in a tmp ADORE home.
"""

from __future__ import annotations

# IMPORTS
import json
from pathlib import Path

from adore.profiles import (
    ProfileError,
    ProfileStore,
    _home_for,
    adore_home,
    resolve_config_path,
)
import pytest

# CONSTANTS

FIXED_NOW = "2026-07-05T00:00:00Z"

# HELPER FUNCTIONS


def _store(tmp_path: Path) -> ProfileStore:
    """
    @brief      A store rooted in a tmp ADORE home with a fixed clock.
    @param[in]  tmp_path pytest tmp dir.
    @return     The ProfileStore.
    """
    return ProfileStore(tmp_path / "home", now=lambda: FIXED_NOW)


# PUBLIC API / TESTS - config home resolution


def test_home_override_wins_on_any_os(tmp_path: Path) -> None:
    """
    @brief   ADORE_HOME overrides the OS-native location on both platforms.
    """
    env = {"ADORE_HOME": str(tmp_path / "custom"), "APPDATA": "ignored"}
    assert _home_for("nt", env) == tmp_path / "custom"
    assert _home_for("posix", env) == tmp_path / "custom"


def test_home_windows_uses_appdata_then_localappdata(tmp_path: Path) -> None:
    """
    @brief   On Windows the home is %APPDATA%\\adore, falling back to
             %LOCALAPPDATA%\\adore.
    """
    assert _home_for("nt", {"APPDATA": str(tmp_path / "roaming")}) == (
        tmp_path / "roaming" / "adore"
    )
    assert _home_for("nt", {"LOCALAPPDATA": str(tmp_path / "local")}) == (
        tmp_path / "local" / "adore"
    )


def test_home_posix_uses_xdg_then_default(tmp_path: Path) -> None:
    """
    @brief   On POSIX the home is $XDG_CONFIG_HOME/adore, or ~/.config/adore.
    """
    assert _home_for("posix", {"XDG_CONFIG_HOME": str(tmp_path / "xdg")}) == (
        tmp_path / "xdg" / "adore"
    )
    assert _home_for("posix", {}) == Path.home() / ".config" / "adore"


def test_adore_home_reads_env_at_call_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief   The public entry point honours a live ADORE_HOME override (safe:
             no os.name patching, which would break pathlib process-wide).
    """
    monkeypatch.setenv("ADORE_HOME", str(tmp_path / "live"))
    assert adore_home() == tmp_path / "live"


def test_previous_home_environment_variable_is_not_consulted(tmp_path: Path) -> None:
    """
    @brief   The pre-1.0 home override has no effect after the hard cut.
    """
    previous_home_env = "AD" + "OR_HOME"
    env = {
        previous_home_env: str(tmp_path / "previous"),
        "APPDATA": str(tmp_path / "roaming"),
    }
    assert _home_for("nt", env) == tmp_path / "roaming" / "adore"


# PUBLIC API / TESTS - CRUD round-trip


def test_profile_crud_round_trip(tmp_path: Path) -> None:
    """
    @brief   create -> load returns equal metadata; list is sorted; touch bumps
             the usage counters; the profile owns its state root.
    """
    store = _store(tmp_path)
    created = store.create("runtime-project", repo="g/p", platform="gitlab",
                           runtime="docker")
    assert created.created_at == FIXED_NOW and created.use_count == 0
    assert len(created.project_id) == 32
    assert store.exists("runtime-project")
    assert store.config_path("runtime-project").name == "config.toml"
    assert store.default_store_root("runtime-project").name == "state"

    loaded = store.load("runtime-project")
    assert loaded == created

    beta = store.create("beta", platform="github")
    assert beta.project_id != created.project_id
    assert [p.name for p in store.list_profiles()] == ["beta", "runtime-project"]

    touched = store.touch("runtime-project")
    assert touched.use_count == 1 and touched.last_used_at == FIXED_NOW


def test_profile_create_rejects_duplicate_without_overwrite(tmp_path: Path) -> None:
    """
    @brief   Re-creating an existing profile fails closed unless overwrite=True.
    """
    store = _store(tmp_path)
    store.create("dup")
    with pytest.raises(ProfileError):
        store.create("dup")
    store.create("dup", overwrite=True, repo="g/p2")  # allowed
    assert store.load("dup").repo == "g/p2"


@pytest.mark.parametrize(
    "winerror, failures, recovered", [(5, 2, True), (32, 6, False), (None, 1, False)],
)
def test_profile_save_keeps_metadata_atomic_during_sharing_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, winerror, failures, recovered,
) -> None:
    """@brief Recover transient Windows locks and retain prior metadata on refusal."""
    store = _store(tmp_path)
    profile = store.create("shared", description="Before")
    path = store.profile_dir(profile.name) / "profile.json"
    original = path.read_bytes()
    replace = Path.replace
    attempts = 0

    def sharing_error(source, target):
        """@brief Deny replacements while checking that the original stays readable."""
        nonlocal attempts
        assert target == path
        assert path.read_bytes() == original
        attempts += 1
        if attempts <= failures:
            error = PermissionError("simulated file sharing error")
            error.winerror = winerror
            raise error
        return replace(source, target)

    monkeypatch.setattr(Path, "replace", sharing_error)
    profile.description = "After"
    if recovered:
        store.save(profile)
        assert attempts == failures + 1 and store.load(profile.name) == profile
    else:
        with pytest.raises(PermissionError):
            store.save(profile)
        assert attempts == failures and path.read_bytes() == original
    assert list(path.parent.glob("*.tmp")) == []


def test_profile_rename_and_delete(tmp_path: Path) -> None:
    """
    @brief   rename moves the directory and keeps identity; delete removes it
             (idempotent) and both keep the active pointer consistent.
    """
    store = _store(tmp_path)
    original = store.create("old", repo="g/p")
    store.set_active("old")

    store.rename("old", "new")
    assert not store.exists("old") and store.exists("new")
    assert store.load("new").name == "new"      # metadata name follows the dir
    assert store.load("new").project_id == original.project_id
    assert store.get_active() == "new"          # active pointer repointed

    store.delete("new")
    assert not store.exists("new")
    assert store.get_active() is None           # active cleared on delete
    store.delete("new")                         # idempotent, no raise


def test_profile_rename_rejects_missing_or_colliding(tmp_path: Path) -> None:
    """
    @brief   rename fails closed for an unknown source or an existing target.
    """
    store = _store(tmp_path)
    store.create("a")
    store.create("b")
    with pytest.raises(ProfileError):
        store.rename("ghost", "c")   # source missing
    with pytest.raises(ProfileError):
        store.rename("a", "b")       # target exists


# PUBLIC API / TESTS - active pointer


def test_active_pointer_lifecycle(tmp_path: Path) -> None:
    """
    @brief   set/get/clear the active profile; setting an unknown one fails.
    """
    store = _store(tmp_path)
    assert store.get_active() is None
    store.create("proj")
    store.set_active("proj")
    assert store.get_active() == "proj"
    store.clear_active()
    assert store.get_active() is None
    with pytest.raises(ProfileError):
        store.set_active("nope")


# PUBLIC API / TESTS - config-path resolution order (decision D3)


def test_resolve_config_path_precedence(tmp_path: Path) -> None:
    """
    @brief   Explicit -c wins over --profile wins over the active pointer wins
             over the local ./config.toml; an unknown --profile fails closed;
             a stale active pointer falls through to the default.
    """
    store = _store(tmp_path)
    store.create("proj")

    # explicit file beats everything
    path, used = resolve_config_path("custom.toml", "proj", store=store)
    assert path == Path("custom.toml") and used is None

    # named profile
    path, used = resolve_config_path(None, "proj", store=store)
    assert path == store.config_path("proj") and used == "proj"

    # unknown named profile fails closed
    with pytest.raises(ProfileError):
        resolve_config_path(None, "ghost", store=store)

    # active pointer
    store.set_active("proj")
    path, used = resolve_config_path(None, None, store=store)
    assert path == store.config_path("proj") and used == "proj"

    # local default when nothing is set
    store.clear_active()
    path, used = resolve_config_path(None, None, store=store)
    assert path == Path("config.toml") and used is None


# PUBLIC API / TESTS - fail-closed on corrupt metadata


def test_corrupt_profile_json_fails_closed(tmp_path: Path) -> None:
    """
    @brief   A corrupt profile.json raises ProfileError on load and is reported
             by invalid_profiles() while list_profiles() skips it (never a
             silent reinitialize).
    """
    store = _store(tmp_path)
    store.create("good", repo="g/p")
    bad_dir = store.profile_dir("bad")
    bad_dir.mkdir(parents=True)
    (bad_dir / "profile.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(ProfileError):
        store.load("bad")
    assert store.invalid_profiles() == ["bad"]
    assert [p.name for p in store.list_profiles()] == ["good"]


def test_load_missing_profile_raises(tmp_path: Path) -> None:
    """
    @brief   Loading a non-existent profile fails closed (distinct message).
    """
    store = _store(tmp_path)
    with pytest.raises(ProfileError):
        store.load("absent")


@pytest.mark.parametrize("change", ["unknown", "missing"])
def test_profile_json_of_another_build_is_refused(tmp_path: Path, change: str) -> None:
    """@brief An unknown or missing key means another build wrote profile.json."""
    store = _store(tmp_path)
    store.create("proj", repo="g/p")
    meta = store.profile_dir("proj") / "profile.json"
    data = json.loads(meta.read_text(encoding="utf-8"))
    if change == "unknown":
        data["future_field"] = "x"
    else:
        data.pop("display_name")
    meta.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProfileError, match="another ADORE build"):
        store.load("proj")


def test_profile_directory_name_overrides_the_stored_name(tmp_path: Path) -> None:
    """@brief The directory name is the profile's identity."""
    store = _store(tmp_path)
    store.create("proj", repo="g/p")
    meta = store.profile_dir("proj") / "profile.json"
    data = json.loads(meta.read_text(encoding="utf-8"))
    data["name"] = "WRONG"
    meta.write_text(json.dumps(data), encoding="utf-8")
    loaded = store.load("proj")
    assert loaded.name == "proj" and loaded.repo == "g/p"


def test_profile_identity_survives_rename_and_bad_ids_fail(tmp_path: Path) -> None:
    """@brief The project ID is stable across renames and a corrupt ID fails closed."""
    store = _store(tmp_path)
    identity = store.create("old", repo="g/p").project_id
    store.rename("old", "new")
    assert store.load("new").project_id == identity
    stored = json.loads((store.profile_dir("new") / "profile.json").read_text(
        encoding="utf-8"))
    stored["project_id"] = "invalid"
    (store.profile_dir("new") / "profile.json").write_text(
        json.dumps(stored), encoding="utf-8")
    with pytest.raises(ProfileError, match="project ID"):
        store.load("new")


# END OF FILE


@pytest.mark.parametrize("persistent", [False, True])
def test_profile_read_bounds_windows_sharing_contention(tmp_path, monkeypatch, persistent):
    """@brief Retry transient metadata replacement sharing; persistent denial fails closed."""
    store = ProfileStore(tmp_path)
    expected = store.create("alpha")
    target = store.profile_dir("alpha") / "profile.json"
    original_open = Path.open
    calls = []

    def contended(path, *args, **kwargs):
        if path == target:
            calls.append(True)
            if persistent or len(calls) <= 2:
                error = PermissionError("simulated metadata replacement sharing")
                error.winerror = 32
                raise error
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", contended)
    monkeypatch.setattr("adore.profiles.sleep", lambda seconds: None)
    if persistent:
        with pytest.raises(ProfileError):
            store.load("alpha")
        assert len(calls) == 5
    else:
        assert store.load("alpha").project_id == expected.project_id
        assert len(calls) == 3
    with original_open(target, encoding="utf-8") as stream:
        assert json.load(stream)["project_id"] == expected.project_id
