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
@file test_clone_cleanup.py
@brief Optional removal of the ADORE-made local clone when a project is deleted.
@details A clone is removed only on request and only when it lies under
         <ADORE home>/repos, is a clean git clone of the project's repository,
         is not another project's clone and has no linked worktree; every
         other case keeps it with a reason.
"""

from __future__ import annotations

# IMPORTS
import json
from pathlib import Path
import subprocess
import sys

from adore.cli import EXIT_ERROR, EXIT_OK, main
from adore.clone_cleanup import clone_decision
from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from adore.web.commands import CommandWorker
from fastapi.testclient import TestClient
import pytest

# CONSTANTS
CONFIG = """
[platform]
kind = "gitlab"
repo = "grp/proj"

[worktree]
repo_path = "{repo_path}"
root = "{worktrees}"

[executor.opencode]
command = "opencode run --dir {{worktree}} -m {{model}} {{prompt}}"
model = "openai/gpt-5.5"

[delivery]
reviewers = []

[state]
store_root = "{state}"
"""


# LOCAL HELPERS
def _clone(path: Path, origin: str = "ssh://git@forge.invalid/grp/proj.git") -> Path:
    """@brief A real git repository at path with the given origin."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "remote", "add", "origin", origin], check=True)
    return path


def _profile(
    home: Path, name: str = "proj", repo_path: Path | str = "", archived: bool = False
) -> ProfileStore:
    """@brief A profile whose config points at repo_path."""
    store = ProfileStore(home)
    cfg = store.config_path(name)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    state = store.default_store_root(name)
    cfg.write_text(
        CONFIG.format(
            repo_path=Path(repo_path).as_posix(),
            state=state.as_posix(),
            worktrees=(home / "worktrees" / name).as_posix(),
        ),
        encoding="utf-8",
    )
    store.create(
        name,
        platform="gitlab",
        repo="grp/proj",
        runtime="docker",
        config_path=str(cfg),
        store_root=str(state),
    )
    if archived:
        profile = store.load(name)
        profile.archived = True
        store.save(profile)
    return store


def _decide(store: ProfileStore, name: str = "proj"):
    from adore.config import load_config

    config = load_config(store.config_path(name))
    return clone_decision(store, name, config.worktree.repo_path, config.platform.repo)


def _login(client: TestClient) -> dict:
    login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
    return {"X-CSRF-Token": login.json()["csrf"]}


def _purge_stub(monkeypatch: pytest.MonkeyPatch, effect=None) -> list[str]:
    """@brief Replace the container/worktree sweep (no Docker in tests)."""
    from adore.orchestrator import Orchestrator

    calls: list[str] = []

    def purge(self) -> dict:
        calls.append(self.identity.slug)
        if effect:
            effect()
        return {"containers_removed": [], "worktrees_removed": [], "worktrees_retained": []}

    monkeypatch.setattr(Orchestrator, "purge_resources", purge)
    return calls


# TESTS
def test_clean_clone_of_the_project_under_repos_is_removable(tmp_path):
    """@brief The ADORE-made clone is removable; the decision names its path."""
    home = tmp_path / "home"
    clone = _clone(home / "repos" / "proj")
    decision = _decide(_profile(home, repo_path=clone))
    assert decision.removable and decision.reason == ""
    assert Path(decision.path) == clone.resolve()


@pytest.mark.parametrize(
    "case",
    [
        "outside",
        "repos-root",
        "relative",
        "missing",
        "plain-folder",
        "other-origin",
        "shared",
        "worktrees",
        "uncommitted",
    ],
)
def test_unsafe_clones_are_kept_with_a_reason(tmp_path, case):
    """@brief Every unsafe case keeps the clone and states why."""
    home = tmp_path / "home"
    clone = home / "repos" / "proj"
    expected = {
        "outside": "outside-repos",
        "repos-root": "outside-repos",
        "relative": "outside-repos",
        "missing": "missing",
        "plain-folder": "not-a-clone",
        "other-origin": "origin-mismatch",
        "shared": "shared",
        "worktrees": "worktrees",
        "uncommitted": "uncommitted",
    }[case]
    if case == "outside":
        clone = _clone(tmp_path / "elsewhere" / "proj")
    elif case == "repos-root":
        clone = _clone(home / "repos")
    elif case == "relative":
        clone = Path("repos/proj")
    elif case == "plain-folder":
        clone.mkdir(parents=True)
    elif case == "other-origin":
        _clone(clone, "ssh://git@forge.invalid/grp/other.git")
    elif case != "missing":
        _clone(clone)
    store = _profile(home, repo_path=clone)
    if case == "shared":
        _profile(home, "second", repo_path=clone)
    elif case == "worktrees":
        (clone / ".git" / "worktrees" / "run-h").mkdir(parents=True)
    elif case == "uncommitted":
        (clone / "notes.txt").write_text("work", encoding="utf-8")
    decision = _decide(store)
    assert not decision.removable and decision.reason == expected
    assert (case in ("missing", "relative")) or clone.exists()


def test_symlinked_clone_counts_as_outside(tmp_path):
    """@brief A clone path reached through a symlink is never removed."""
    home = tmp_path / "home"
    real = _clone(tmp_path / "real" / "proj")
    (home / "repos").mkdir(parents=True)
    link = home / "repos" / "proj"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    decision = _decide(_profile(home, repo_path=link))
    assert not decision.removable and decision.reason == "outside-repos"


def test_clone_below_a_symlinked_folder_counts_as_outside(tmp_path):
    """@brief A symlinked folder inside repos also blocks removal, even pointing inside repos."""
    home = tmp_path / "home"
    _clone(home / "repos" / "real" / "proj")
    group = home / "repos" / "group"
    try:
        group.symlink_to(home / "repos" / "real", target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    decision = _decide(_profile(home, repo_path=group / "proj"))
    assert not decision.removable and decision.reason == "outside-repos"


def test_delete_preview_reports_the_clone_for_administrators(tmp_path):
    """@brief The dialog reads the clone decision; handed-off worktrees keep the clone."""
    home = tmp_path / "home"
    clone = _clone(home / "repos" / "proj")
    store = _profile(home, repo_path=clone, archived=True)
    app = create_app(home)
    app.state.web_store.create_user("dev", "longer-password", "developer")
    with TestClient(app) as client:
        _login(client)
        preview = client.get("/api/v1/projects/proj/delete-preview")
        assert preview.status_code == 200, preview.text
        assert preview.json()["clone"] == {
            "path": str(clone.resolve()),
            "removable": True,
            "reason": "",
        }
        StateStore(store.default_store_root("proj")).save(
            RunState(run_id="run-h", ticket_iid=1, lifecycle="handed-off")
        )
        from adore.config import load_config
        from adore.isolation import WorktreeManager

        config = load_config(store.config_path("proj"))
        worktrees = WorktreeManager(config.worktree.repo_path, config.worktree.root)
        worktrees.path_for("run-h").mkdir(parents=True)
        kept = client.get("/api/v1/projects/proj/delete-preview").json()["clone"]
        assert kept["removable"] is False and kept["reason"] == "worktrees"
        client.delete("/api/v1/session")
        client.post("/api/v1/session", json={"username": "dev", "password": "longer-password"})
        assert client.get("/api/v1/projects/proj/delete-preview").status_code in (403, 404)


def test_delete_with_clone_removal_is_rechecked_and_passed_to_the_worker(tmp_path):
    """@brief An unsafe request is refused; a safe one queues `--remove-clone`."""
    home = tmp_path / "home"
    clone = _clone(home / "repos" / "proj")
    store = _profile(home, repo_path=clone, archived=True)
    app = create_app(home)
    calls = []

    def runner(argv, _env):
        calls.append(argv)
        store.delete("proj")
        return 0

    with TestClient(app) as client:
        headers = _login(client)
        (clone / "notes.txt").write_text("work", encoding="utf-8")
        refused = client.post(
            "/api/v1/projects/proj/delete",
            headers=headers,
            json={"confirm_name": "proj", "idempotency_key": "delete-key-1", "remove_clone": True},
        )
        assert refused.status_code == 409
        assert refused.json()["detail"]["code"] == "clone_not_removable"
        (clone / "notes.txt").unlink()
        queued = client.post(
            "/api/v1/projects/proj/delete",
            headers=headers,
            json={"confirm_name": "proj", "idempotency_key": "delete-key-2", "remove_clone": True},
        )
        assert queued.status_code == 200, queued.text
        assert CommandWorker(store, app.state.web_store, runner=runner).run_pending() == 1
    assert calls == [
        [
            sys.executable,
            "-m",
            "adore",
            "profile",
            "delete",
            "proj",
            "--force",
            "--remove-resources",
            "--remove-clone",
        ]
    ]


def test_cli_removes_the_clone_after_the_profile(tmp_path, monkeypatch, capsys):
    """@brief `--remove-clone` deletes the profile, then the clone, and reports it."""
    home = tmp_path / "home"
    monkeypatch.setenv("ADORE_HOME", str(home))
    clone = _clone(home / "repos" / "proj")
    store = _profile(home, repo_path=clone)
    _purge_stub(monkeypatch)
    assert (
        main(["profile", "delete", "proj", "--force", "--remove-resources", "--remove-clone"])
        == EXIT_OK
    )
    report = json.loads(capsys.readouterr().out)
    assert not store.exists("proj") and not clone.exists()
    assert Path(report["clone_removed"]) == clone.resolve() and report["clone_retained"] is None


def test_cli_without_the_option_keeps_the_clone(tmp_path, monkeypatch, capsys):
    """@brief Without the choice the clone stays."""
    home = tmp_path / "home"
    monkeypatch.setenv("ADORE_HOME", str(home))
    clone = _clone(home / "repos" / "proj")
    store = _profile(home, repo_path=clone)
    _purge_stub(monkeypatch)
    assert main(["profile", "delete", "proj", "--force", "--remove-resources"]) == EXIT_OK
    report = json.loads(capsys.readouterr().out)
    assert not store.exists("proj") and clone.is_dir() and report["clone_removed"] is None


def test_cli_refuses_an_unsafe_clone_before_deleting_anything(tmp_path, monkeypatch, capsys):
    """@brief A clone that is not removable stops the delete before any resource goes."""
    home = tmp_path / "home"
    monkeypatch.setenv("ADORE_HOME", str(home))
    clone = _clone(home / "repos" / "proj", "ssh://git@forge.invalid/grp/other.git")
    store = _profile(home, repo_path=clone)
    calls = _purge_stub(monkeypatch)
    assert (
        main(["profile", "delete", "proj", "--force", "--remove-resources", "--remove-clone"])
        == EXIT_ERROR
    )
    assert "origin-mismatch" in capsys.readouterr().out
    assert store.exists("proj") and clone.is_dir() and not calls
    assert main(["profile", "delete", "proj", "--force", "--remove-clone"]) == EXIT_ERROR
    assert store.exists("proj")


def test_cli_keeps_a_clone_that_became_unsafe_during_purge(tmp_path, monkeypatch, capsys):
    """@brief A worktree still linked after purge keeps the clone; the profile still goes."""
    home = tmp_path / "home"
    monkeypatch.setenv("ADORE_HOME", str(home))
    clone = _clone(home / "repos" / "proj")
    store = _profile(home, repo_path=clone)
    linked = clone / ".git" / "worktrees" / "run-h"

    def link() -> None:
        linked.mkdir(parents=True)
        (linked / "gitdir").write_text(str(clone.parent / "live" / ".git"), encoding="utf-8")
        (clone.parent / "live").mkdir()
        (clone.parent / "live" / ".git").write_text(f"gitdir: {linked}\n", encoding="utf-8")

    _purge_stub(monkeypatch, link)
    assert (
        main(["profile", "delete", "proj", "--force", "--remove-resources", "--remove-clone"])
        == EXIT_OK
    )
    report = json.loads(capsys.readouterr().out)
    assert not store.exists("proj") and clone.is_dir()
    assert report["clone_removed"] is None
    assert report["clone_retained"] == {"path": str(clone.resolve()), "reason": "worktrees"}


# END OF FILE


def _commit(clone: Path) -> None:
    """@brief One commit so `git worktree add` works."""
    (clone / "README.md").write_text("x\n", encoding="utf-8")
    git = ["git", "-C", str(clone), "-c", "user.name=t", "-c", "user.email=t@e.invalid"]
    subprocess.run([*git, "add", "README.md"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "init"], check=True)


def test_own_failed_run_worktree_does_not_block_before_the_sweep(tmp_path):
    """@brief ADORE's own worktrees are removed by the sweep, so the preview offers removal."""
    from adore.clone_cleanup import project_clone_decision
    from adore.config import load_config

    home = tmp_path / "home"
    clone = _clone(home / "repos" / "proj")
    _commit(clone)
    store = _profile(home, repo_path=clone, archived=True)
    config = load_config(store.config_path("proj"))
    run = RunState(run_id="run-f", ticket_iid=1, lifecycle="failed")
    subprocess.run(
        [
            "git",
            "-C",
            str(clone),
            "worktree",
            "add",
            "-q",
            str(Path(config.worktree.root) / "run-f"),
        ],
        check=True,
    )
    assert project_clone_decision(store, "proj", config, [run]).removable
    # The same worktree still linked after the sweep keeps the clone.
    assert _decide(store).reason == "worktrees"


def test_failed_removal_is_reported_as_kept(tmp_path, monkeypatch, capsys):
    """@brief A clone that is still there after removal is reported, never claimed removed."""
    import adore.cli as cli_module

    home = tmp_path / "home"
    monkeypatch.setenv("ADORE_HOME", str(home))
    clone = _clone(home / "repos" / "proj")
    store = _profile(home, repo_path=clone)
    _purge_stub(monkeypatch)
    monkeypatch.setattr(cli_module, "force_rmtree", lambda path: None)
    assert (
        main(["profile", "delete", "proj", "--force", "--remove-resources", "--remove-clone"])
        == EXIT_OK
    )
    report = json.loads(capsys.readouterr().out)
    assert not store.exists("proj") and clone.is_dir() and report["clone_removed"] is None
    assert report["clone_retained"] == {"path": str(clone.resolve()), "reason": "removal-failed"}


@pytest.mark.parametrize("other", ["relative", "nested-root"])
def test_another_project_inside_or_relative_counts_as_shared(tmp_path, other):
    """@brief Another project's relative clone path or worktrees inside the clone keep it."""
    home = tmp_path / "home"
    clone = _clone(home / "repos" / "proj")
    store = _profile(home, repo_path=clone)
    if other == "relative":
        _profile(home, "second", repo_path="repos/proj")
    else:
        _profile(home, "second", repo_path=tmp_path / "elsewhere")
        cfg = store.config_path("second")
        text = cfg.read_bytes().decode()
        text = text.replace((home / "worktrees" / "second").as_posix(), (clone / "wt").as_posix())
        cfg.write_bytes(text.encode())
    assert _decide(store).reason == "shared"


def test_malformed_input_is_kept_as_unknown(tmp_path):
    """@brief A non-string clone path or repository never raises and never removes."""
    home = tmp_path / "home"
    store = ProfileStore(home)
    assert clone_decision(store, "proj", 5, "grp/proj").reason == "unknown"  # type: ignore[arg-type]
    clone = _clone(home / "repos" / "proj")
    assert clone_decision(store, "proj", str(clone), None).reason == "unknown"  # type: ignore[arg-type]


def test_foreign_linked_worktree_blocks_before_the_sweep(tmp_path):
    """@brief A worktree made by hand from the clone survives the sweep, so it keeps the clone."""
    from adore.clone_cleanup import project_clone_decision
    from adore.config import load_config

    home = tmp_path / "home"
    clone = _clone(home / "repos" / "proj")
    _commit(clone)
    store = _profile(home, repo_path=clone, archived=True)
    config = load_config(store.config_path("proj"))
    subprocess.run(
        ["git", "-C", str(clone), "worktree", "add", "-q", str(tmp_path / "mine")], check=True
    )
    run = RunState(run_id="run-f", ticket_iid=1, lifecycle="failed")
    assert project_clone_decision(store, "proj", config, [run]).reason == "worktrees"
