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
@file test_profile_cli.py
@brief Smoke tests for `adore profile ...` and `--profile` resolution, driven
       through main() against a tmp ADORE_HOME.
"""

from __future__ import annotations

# IMPORTS
from pathlib import Path

from adore.cli import EXIT_ERROR, EXIT_OK, main
from adore.metrics import RunSummary, record_summary
from adore.profiles import ProfileStore
import pytest

# CONSTANTS

MINIMAL_CONFIG = """
[platform]
kind = "gitlab"
repo = "grp/proj"

[worktree]
repo_path = "x"

[executor.opencode]
command = "opencode run --dir {{worktree}} -m {{model}} {{prompt}}"
model = "openai/gpt-5.5"

[delivery]
reviewers = ["dan.pasare"]

[state]
store_root = "{state}"
"""

# HELPER FUNCTIONS


def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    @brief      A tmp ADORE home wired into the environment for main().
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  monkeypatch Fixture to set ADORE_HOME.
    @return     The home path.
    """
    home = tmp_path / "home"
    monkeypatch.setenv("ADORE_HOME", str(home))
    return home


def _ready_profile(home: Path, name: str = "proj") -> ProfileStore:
    """
    @brief      Create a profile with a valid config.toml + metadata.
    @param[in]  home The ADORE home.
    @param[in]  name Profile name.
    @return     The store (rooted at home).
    """
    store = ProfileStore(home)
    cfg = store.config_path(name)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    state_root = store.default_store_root(name).as_posix()
    cfg.write_text(MINIMAL_CONFIG.format(state=state_root), encoding="utf-8")
    store.create(name, platform="gitlab", repo="grp/proj", runtime="docker",
                 config_path=str(cfg), store_root=str(store.default_store_root(name)))
    return store


# PUBLIC API / TESTS


def test_profile_list_empty(tmp_path: Path, monkeypatch, capsys) -> None:
    """
    @brief   `adore profile list` on an empty home is clean (exit 0).
    """
    _home(tmp_path, monkeypatch)
    assert main(["profile", "list"]) == EXIT_OK
    assert "no profiles" in capsys.readouterr().out


def test_profile_list_and_show(tmp_path: Path, monkeypatch, capsys) -> None:
    """
    @brief   list shows the profile row; show prints metadata + config path.
    """
    home = _home(tmp_path, monkeypatch)
    _ready_profile(home)
    assert main(["profile", "list"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "proj" in out and "gitlab" in out and "grp/proj" in out
    assert main(["profile", "show", "proj"]) == EXIT_OK
    out = capsys.readouterr().out
    assert '"repo": "grp/proj"' in out and "config :" in out
    assert main(["profile", "show", "ghost"]) == EXIT_ERROR


def test_profile_use_activates_and_resolves(tmp_path: Path, monkeypatch, capsys) -> None:
    """
    @brief   `use` sets the active profile; a later bare command resolves it
             and records a use (use_count bumped).
    """
    home = _home(tmp_path, monkeypatch)
    store = _ready_profile(home)
    assert main(["profile", "use", "proj"]) == EXIT_OK
    capsys.readouterr()
    # bare command (no -c, no --profile) uses the active profile
    assert main(["config", "validate"]) == EXIT_OK
    assert "OK" in capsys.readouterr().out
    assert store.load("proj").use_count >= 1


def test_profile_flag_resolves_and_touches(tmp_path: Path, monkeypatch, capsys) -> None:
    """
    @brief   `--profile NAME` resolves that profile's config for any command
             and bumps its use counter; an unknown profile fails cleanly.
    """
    home = _home(tmp_path, monkeypatch)
    store = _ready_profile(home)
    before = store.load("proj").use_count
    assert main(["--profile", "proj", "config", "validate"]) == EXIT_OK
    assert "OK" in capsys.readouterr().out
    assert store.load("proj").use_count == before + 1
    assert main(["--profile", "ghost", "status"]) == EXIT_ERROR
    assert "no such profile" in capsys.readouterr().out


def test_profile_path(tmp_path: Path, monkeypatch, capsys) -> None:
    """
    @brief   `path` prints the config path for a named / active profile, and
             errors when neither is available.
    """
    home = _home(tmp_path, monkeypatch)
    store = _ready_profile(home)
    assert main(["profile", "path", "proj"]) == EXIT_OK
    assert "config.toml" in capsys.readouterr().out
    assert main(["profile", "path"]) == EXIT_ERROR       # no active, no name
    capsys.readouterr()
    store.set_active("proj")
    assert main(["profile", "path"]) == EXIT_OK           # falls back to active
    assert "config.toml" in capsys.readouterr().out


def test_profile_rename(tmp_path: Path, monkeypatch, capsys) -> None:
    """
    @brief   rename moves the profile; the new name resolves, the old does not.
    """
    home = _home(tmp_path, monkeypatch)
    _ready_profile(home)
    assert main(["profile", "rename", "proj", "proj2"]) == EXIT_OK
    capsys.readouterr()
    assert main(["--profile", "proj2", "config", "validate"]) == EXIT_OK
    assert "OK" in capsys.readouterr().out
    assert main(["--profile", "proj", "status"]) == EXIT_ERROR


def test_profile_delete_needs_force(tmp_path: Path, monkeypatch, capsys) -> None:
    """
    @brief   delete refuses without --force, removes with it, and reports an
             unknown profile.
    """
    home = _home(tmp_path, monkeypatch)
    store = _ready_profile(home)
    assert main(["profile", "delete", "proj"]) == EXIT_ERROR
    assert "--force" in capsys.readouterr().out
    assert store.exists("proj")
    assert main(["profile", "delete", "proj", "--force"]) == EXIT_OK
    assert not store.exists("proj")
    assert main(["profile", "delete", "proj", "--force"]) == EXIT_ERROR  # gone


def test_profile_stats_render_in_list_and_show(tmp_path: Path, monkeypatch, capsys) -> None:
    """
    @brief   Seeding the profile's metrics DB surfaces RUNS/MERGED in `list`
             and the full stats block (success_rate) in `show`; a profile with
             no DB renders zeros, not an error.
    """
    home = _home(tmp_path, monkeypatch)
    store = _ready_profile(home)
    db = store.default_store_root("proj") / "metrics.db"
    record_summary(db, RunSummary(run_id="1", outcome="merged by human", lifecycle="done",
                                  ended_at="2026-07-01T00:00:00Z"))
    record_summary(db, RunSummary(run_id="2", outcome="failed", lifecycle="failed",
                                  ended_at="2026-07-02T00:00:00Z"))
    assert main(["profile", "list"]) == EXIT_OK
    list_out = capsys.readouterr().out
    assert "RUNS" in list_out and "MERGED" in list_out
    row = next(line for line in list_out.splitlines() if "proj" in line)
    assert "2" in row.split() and "1" in row.split()          # runs=2, merged=1

    assert main(["profile", "show", "proj"]) == EXIT_OK
    show_out = capsys.readouterr().out
    assert "success_rate=50.0%" in show_out and "runs=2" in show_out


def test_explicit_config_still_wins(tmp_path: Path, monkeypatch, capsys) -> None:
    """
    @brief   Regression: an explicit -c file behaves exactly as before and
             overrides any active profile (single-config users unaffected).
    """
    home = _home(tmp_path, monkeypatch)
    _ready_profile(home)
    ProfileStore(home).set_active("proj")
    other = tmp_path / "other.toml"
    other.write_text(MINIMAL_CONFIG.format(state=(tmp_path / "s").as_posix()),
                     encoding="utf-8")
    assert main(["-c", str(other), "config", "validate"]) == EXIT_OK
    out = capsys.readouterr().out
    assert str(other) in out and "OK" in out


# END OF FILE


def _purge_stub(monkeypatch: pytest.MonkeyPatch, calls: list[str]) -> None:
    """@brief Replace the container/worktree sweep with a recorder (no Docker in tests)."""
    from adore.orchestrator import Orchestrator

    def purge(self) -> dict:
        calls.append(self.identity.slug)
        return {"containers_removed": ["c1"], "worktrees_removed": ["run-1"],
                "worktrees_retained": ["run-h"]}

    monkeypatch.setattr(Orchestrator, "purge_resources", purge)


def test_profile_delete_remove_resources_sweeps_then_deletes(tmp_path: Path, monkeypatch,
                                                             capsys) -> None:
    """@brief Resource removal runs under the lock before the profile disappears."""
    import json

    from adore.state import RunState, StateStore

    home = _home(tmp_path, monkeypatch)
    store = _ready_profile(home)
    StateStore(store.default_store_root("proj")).save(
        RunState(run_id="run-1", ticket_iid=1, lifecycle="done"))
    calls: list[str] = []
    _purge_stub(monkeypatch, calls)
    assert main(["profile", "delete", "proj", "--force", "--remove-resources"]) == EXIT_OK
    report = json.loads(capsys.readouterr().out)
    assert calls and not store.exists("proj")
    assert report["deleted"] == "proj" and report["worktrees_retained"] == ["run-h"]
    assert report["state_retained"] is None


def test_profile_delete_remove_resources_keeps_external_state(tmp_path: Path, monkeypatch,
                                                              capsys) -> None:
    """@brief A state folder outside ADORE home is reported and left in place."""
    import json

    home = _home(tmp_path, monkeypatch)
    store = ProfileStore(home)
    external = tmp_path / "external-state"
    cfg = store.config_path("proj")
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(MINIMAL_CONFIG.format(state=external.as_posix()), encoding="utf-8")
    store.create("proj", config_path=str(cfg), store_root=str(external))
    external.mkdir(parents=True, exist_ok=True)
    (external / "keep.txt").write_text("history", encoding="utf-8")
    _purge_stub(monkeypatch, [])
    assert main(["profile", "delete", "proj", "--force", "--remove-resources"]) == EXIT_OK
    report = json.loads(capsys.readouterr().out)
    assert not store.exists("proj")
    assert (external / "keep.txt").is_file()
    assert Path(report["state_retained"]) == external


def test_profile_delete_remove_resources_refuses_unsafe_states(tmp_path: Path, monkeypatch,
                                                               capsys) -> None:
    """@brief Unfinished runs, a held lock or an invalid config delete nothing."""
    from adore.state import RunState, StateStore

    home = _home(tmp_path, monkeypatch)
    store = _ready_profile(home)
    calls: list[str] = []
    _purge_stub(monkeypatch, calls)
    state = StateStore(store.default_store_root("proj"))
    state.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="working"))
    assert main(["profile", "delete", "proj", "--force", "--remove-resources"]) == EXIT_ERROR
    assert store.exists("proj") and not calls
    state.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="done"))
    assert state.acquire_lock()
    try:
        assert main(["profile", "delete", "proj", "--force", "--remove-resources"]) == EXIT_ERROR
    finally:
        state.release_lock()
    assert store.exists("proj") and not calls
    corrupt = state.root / "runs" / "broken"
    corrupt.mkdir(parents=True)
    (corrupt / "state.json").write_text("{not json", encoding="utf-8")
    assert main(["profile", "delete", "proj", "--force", "--remove-resources"]) == EXIT_ERROR
    assert store.exists("proj") and not calls
    (corrupt / "state.json").unlink()
    corrupt.rmdir()
    store.config_path("proj").write_text("[platform]\nkind = 'nope'\n", encoding="utf-8")
    assert main(["profile", "delete", "proj", "--force", "--remove-resources"]) == EXIT_ERROR
    assert store.exists("proj") and not calls
    capsys.readouterr()


def test_profile_delete_remove_resources_reports_failed_profile_removal(tmp_path: Path,
                                                                       monkeypatch,
                                                                       capsys) -> None:
    """@brief If the profile folder cannot be removed, the report says so and exit fails."""
    import json

    home = _home(tmp_path, monkeypatch)
    store = _ready_profile(home)
    _purge_stub(monkeypatch, [])

    def locked(self, name):
        raise PermissionError("file in use")

    monkeypatch.setattr(ProfileStore, "delete", locked)
    assert main(["profile", "delete", "proj", "--force", "--remove-resources"]) == EXIT_ERROR
    report = json.loads(capsys.readouterr().out)
    assert report["deleted"] is None and "file in use" in report["error"]
    assert report["worktrees_removed"] == ["run-1"]
    assert store.exists("proj")
