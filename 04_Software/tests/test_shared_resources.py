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
@file test_shared_resources.py
@brief Offline shared-resource contention and ownership contracts.
@details Uses only injected offline fakes; no forge, git, container or model is
         contacted. The tests focus on observable contracts and fail-closed
         trust boundaries rather than private implementation structure.
"""

from __future__ import annotations

# IMPORTS
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
import json
from pathlib import Path
from threading import Barrier, Event
import time

from adore import chatgpt, metrics
from adore.isolation import IsolationError, WorktreeManager
from adore.resource_lock import ResourceLockError, resource_lock
from adore.state import LockHeldError, RunState, StateStore
from adore.util import CommandResult
import pytest

from tests.test_chatgpt import signed_in
from tests.test_orchestrator import make_engine, make_run


@pytest.fixture(autouse=True)
def isolated_server_home(tmp_path, monkeypatch):
    """@brief Kernel lock metadata never enters an operator's server home."""
    monkeypatch.setenv("ADORE_HOME", str(tmp_path / "server-home"))


# PUBLIC API

def test_shared_git_mutations_wait_but_another_repository_proceeds(tmp_path):
    """@brief Same-clone mutations serialize; independent repositories progress."""
    entered, release, second_started, second_entered = (Event() for _ in range(4))
    def runner(argv, **kwargs):
        if "worktree" in argv and "add" in argv:
            if str(tmp_path / "work" / "first") in argv:
                entered.set()
                assert release.wait(5)
            elif str(tmp_path / "work" / "second") in argv:
                second_entered.set()
        return CommandResult()
    a = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner)
    b = WorktreeManager(tmp_path / "repo", tmp_path / "work", runner)
    other = WorktreeManager(tmp_path / "other", tmp_path / "other-work", runner)
    def second():
        second_started.set()
        return b.create("second", "adore/second", "HEAD", new_branch=True)
    with ThreadPoolExecutor(3) as pool:
        first = pool.submit(a.create, "first", "adore/first", "HEAD", new_branch=True)
        try:
            assert entered.wait(5)
            peer = pool.submit(second)
            assert second_started.wait(5)
            assert not second_entered.wait(0.15)
            assert pool.submit(other.create, "third", "adore/third", "HEAD",
                               new_branch=True).result(2).name == "third"
        finally:
            release.set()
        first.result(5)
        peer.result(5)
    assert second_entered.is_set()


@pytest.mark.parametrize("bad", ["../foreign", ".", "..", "/foreign", "a/b", "a\\b"])
def test_worktree_identity_refuses_escaping_run_paths(tmp_path, bad):
    """@brief Invalid run names cannot address another run or repository."""
    calls = []
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work",
                              lambda argv: calls.append(argv) or CommandResult())
    with pytest.raises(IsolationError):
        manager.create(bad, "adore/test", "HEAD", new_branch=True)
    assert not calls


def test_project_barrier_checks_terminal_and_removed_execution_slots(tmp_path):
    """@brief Cleanup ownership outlives state and stays project scoped."""
    a, peer, other = (StateStore(tmp_path / name) for name in ("a", "a", "b"))
    a.save(RunState("one", 1, lifecycle="done"))
    with a.execution_slot("one"):
        with pytest.raises(LockHeldError), peer.project_barrier():
            pytest.fail("active slot must block the whole project")
        with other.project_barrier():
            pass
    with peer.project_barrier(), pytest.raises(LockHeldError), a.run_lock("one"):
        pytest.fail("run must stay excluded during archive/delete")
    with a.execution_slot("removed"), pytest.raises(LockHeldError), peer.project_barrier():
        pytest.fail("removed state still owns cleanup")


def test_refresh_is_serial_and_tokens_remain_call_scoped(tmp_path):
    """@brief Helpers sharing credentials serialize while returning distinct tokens."""
    directory = tmp_path / "auth"
    signed_in(directory)
    entered, release, second_started, second_entered = (Event() for _ in range(4))
    class Helper:
        def helper_command(self, name, argv, **kwargs):
            return argv
        def runner(self, argv, **kwargs):
            seconds = int(argv[-1])
            if seconds == 1:
                entered.set()
                assert release.wait(5)
            else:
                second_entered.set()
            return CommandResult(stdout=json.dumps({"status": "ok", "token":
                f"token-for-request-{seconds}", "expires": (time.time() + 100) * 1000}))
    def second():
        second_started.set()
        return chatgpt.bearer_token(Helper(), directory, 2)
    with ThreadPoolExecutor(2) as pool:
        a = pool.submit(chatgpt.bearer_token, Helper(), directory, 1)
        try:
            assert entered.wait(5)
            b = pool.submit(second)
            assert second_started.wait(5)
            assert not second_entered.wait(0.15)
        finally:
            release.set()
        assert a.result(5) == "token-for-request-1"
        assert b.result(5) == "token-for-request-2"


@pytest.mark.parametrize("operation", ["cancel", "handoff"])
def test_foreign_saved_resource_refused_before_effects(tmp_path, operation):
    """@brief Corrupt state cannot redirect checkpoint/publication or cancellation."""
    engine, _, worktrees, containers, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.container = "another-project-run"
    engine.store.save(run)
    with pytest.raises(IsolationError):
        if operation == "cancel":
            engine.cancel(run.run_id)
        else:
            engine.handoff(run.run_id)
    assert not worktrees.checkpoints and not worktrees.pushes and not worktrees.removed
    assert not containers.removed


def test_concurrent_metrics_updates_publish_atomic_complete_snapshot(tmp_path, monkeypatch):
    """@brief A slow mirror writer cannot overwrite a later committed row."""
    db, mirror = tmp_path / "metrics.db", tmp_path / "metrics.jsonl"
    entered, release, second_started = Event(), Event(), Event()
    original = metrics.load_summaries
    def load(path, *args, **kwargs):
        rows = original(path, *args, **kwargs)
        if len(rows) == 1 and rows[0].run_id == "first":
            entered.set()
            assert release.wait(5)
        return rows
    monkeypatch.setattr(metrics, "load_summaries", load)
    def second():
        second_started.set()
        metrics.record_summary(db, metrics.RunSummary("second"), str(mirror))
    with ThreadPoolExecutor(2) as pool:
        a = pool.submit(metrics.record_summary, db, metrics.RunSummary("first"), str(mirror))
        try:
            assert entered.wait(5)
            b = pool.submit(second)
            assert second_started.wait(5)
            # Allow a broken unguarded writer to finish before releasing the old snapshot.
            with suppress(TimeoutError):
                b.result(0.2)
        finally:
            release.set()
        a.result(5)
        b.result(5)
    assert {json.loads(line)["run_id"] for line in mirror.read_text().splitlines()} == {
        row.run_id for row in original(db)} == {"first", "second"}

def test_two_runs_provision_checkpoint_and_finish_without_resource_overlap(tmp_path):
    """@brief Concurrent same-clone lifecycles preserve peer worktrees and metrics."""
    repo, root = tmp_path / "repo", tmp_path / "work"
    common = repo / ".git"
    branches, dirty = {}, {}
    agent_boundary = Barrier(2)
    def runner(argv, **kwargs):
        cwd, args = Path(argv[2]), argv[3:]
        if args[:2] == ["worktree", "add"]:
            branch, path = args[3], Path(args[4])
            path.mkdir(parents=True)
            (path / ".git").write_text("gitdir: " + str(common / "worktrees" / path.name))
            branches[path] = branch
            dirty[path] = True
        elif args[:2] == ["worktree", "remove"]:
            path = Path(args[-1])
            (path / ".git").unlink()
            path.rmdir()
        elif args[0] == "symbolic-ref":
            return CommandResult(stdout="refs/heads/" + branches[cwd])
        elif args[-1] == "--show-toplevel":
            return CommandResult(stdout=str(cwd))
        elif args[-1] == "--git-common-dir":
            return CommandResult(stdout=str(common))
        elif args[0] == "status":
            return CommandResult(stdout=" M source.py\0" if dirty[cwd] else "")
        elif args[0] == "commit":
            dirty[cwd] = False
        return CommandResult()
    db, mirror = tmp_path / "metrics.db", tmp_path / "metrics.jsonl"
    def job(run_id):
        manager = WorktreeManager(repo, root, runner)
        path = manager.create(run_id, "adore/" + run_id, "HEAD", new_branch=True)
        # Both agents reach this boundary; neither retains a repository lock.
        agent_boundary.wait(5)
        assert manager.commit_all_if_dirty(run_id, "owned checkpoint")
        metrics.record_summary(db, metrics.RunSummary(run_id), str(mirror))
        agent_boundary.wait(5)
        manager.remove(run_id, delete_branch="adore/" + run_id)
        return path
    with ThreadPoolExecutor(2) as pool:
        a, b = [pool.submit(job, name) for name in ("one", "two")]
        paths = [a.result(10), b.result(10)]
    assert paths[0] != paths[1] and not any(path.exists() for path in paths)
    assert {row.run_id for row in metrics.load_summaries(db)} == {"one", "two"}
    assert {json.loads(line)["run_id"] for line in mirror.read_text().splitlines()} == {
        "one", "two"}


def test_resource_contention_is_bounded_and_failed_owner_releases(tmp_path):
    """@brief Busy locks fail typed and a failing holder cannot strand a peer."""
    path = tmp_path / "shared.lock"
    def peer():
        with pytest.raises(ResourceLockError, match="busy"), resource_lock(path, timeout=0):
            pytest.fail("foreign lock bypassed")
    with pytest.raises(ValueError, match="injected"), resource_lock(path):
        with resource_lock(path), ThreadPoolExecutor(1) as pool:
            pool.submit(peer).result(2)
        raise ValueError("injected")
    with resource_lock(path, timeout=0):
        pass


def test_metrics_failure_preserves_old_mirror_and_reports_contention(tmp_path, monkeypatch):
    """@brief Atomic replacement failure leaves valid old output and a typed refusal."""
    db, mirror = tmp_path / "m.db", tmp_path / "m.jsonl"
    metrics.record_summary(db, metrics.RunSummary("old"), str(mirror))
    previous = mirror.read_bytes()
    from adore import resource_lock as locks
    def refused(*args):
        raise PermissionError("injected replacement contention")
    monkeypatch.setattr(locks.os, "replace", refused)
    with pytest.raises(metrics.MetricsError):
        metrics.record_summary(db, metrics.RunSummary("new"), str(mirror))
    assert mirror.read_bytes() == previous
    assert {row.run_id for row in metrics.load_summaries(db)} == {"old", "new"}
    assert not list(tmp_path.glob(".m.jsonl-*"))


def test_metrics_sqlite_contention_is_bounded_and_typed(tmp_path):
    """@brief External SQLite ownership cannot become an unbounded terminal write."""
    from contextlib import closing
    import sqlite3
    db = tmp_path / "m.db"
    metrics.record_summary(db, metrics.RunSummary("old"))
    with closing(sqlite3.connect(db)) as connection:
        connection.execute("BEGIN EXCLUSIVE")
        try:
            with pytest.raises(metrics.MetricsError, match="locked"):
                metrics.record_summary(db, metrics.RunSummary("new"))
        finally:
            connection.rollback()
    metrics.record_summary(db, metrics.RunSummary("new"))
    assert {row.run_id for row in metrics.load_summaries(db)} == {"old", "new"}


def test_managed_pi_concurrent_install_publishes_once(tmp_path, monkeypatch):
    """@brief Two product prerequisite requests publish one immutable verified prefix."""
    from adore import pi_installation as pi

    from tests.test_pi_installation import fake_node, write_fake_packages
    node = fake_node(tmp_path, monkeypatch)
    entered, release, second_started = Event(), Event(), Event()
    installs = []
    def runner(argv, **kwargs):
        if argv[-1] == "--version":
            return CommandResult(stdout="v22.23.4" if len(argv) == 2 else pi.PI_VERSION)
        entered.set()
        assert release.wait(5)
        from pathlib import Path
        candidate = pi.ManagedPi(node, Path(argv[argv.index("--prefix") + 1]))
        write_fake_packages(candidate)
        installs.append(candidate.prefix)
        return CommandResult()
    def second():
        second_started.set()
        return pi.install_pi(progress=lambda _: None, runner=runner)
    with ThreadPoolExecutor(2) as pool:
        a = pool.submit(pi.install_pi, progress=lambda _: None, runner=runner)
        try:
            assert entered.wait(5)
            b = pool.submit(second)
            assert second_started.wait(5)
        finally:
            release.set()
        assert a.result(5) == b.result(5)
    assert len(installs) == 1
    assert pi.verify_pi(runner=runner).prefix.is_dir()


def test_container_stop_and_bound_environment_are_run_scoped():
    """@brief Cancelling one target preserves the peer and copied launch environments."""
    from adore.execution import ContainerBackend, ExecutionRecoveryError
    class Manager:
        def __init__(self):
            self.active = {"first": "a" * 64, "second": "b" * 64}
            self.stopped = []
        def resource_identity(self, name):
            return {"container_id": self.active[name], "image_id": "sha256:" + "c" * 64,
                    "status": "running"}
        def stop(self, identity):
            self.stopped.append(identity)
    manager = Manager()
    first, second = ContainerBackend(manager), ContainerBackend(manager)
    one, two = {"PROVIDER_KEY": "one"}, {"PROVIDER_KEY": "two"}
    a, b = first.bind("first", one), second.bind("second", two)
    one["PROVIDER_KEY"] = "changed"
    assert a.env["PROVIDER_KEY"] == "one" and b.env["PROVIDER_KEY"] == "two"
    expected = manager.resource_identity("first")
    first.stop("first", expected=expected)
    assert manager.stopped == ["a" * 64]
    assert "second" in manager.active
    manager.active["first"] = "d" * 64
    with pytest.raises(ExecutionRecoveryError):
        first.stop("first", expected=expected)
    assert manager.stopped == ["a" * 64]


def test_project_namespaces_separate_same_ticket_resources(tmp_path, monkeypatch):
    """@brief Production construction retains each project's backend, model and resource key."""
    from types import SimpleNamespace

    from adore import orchestrator as module

    from tests.test_local_execution import local_fixture
    from tests.test_orchestrator import FakeForge, make_config
    native_root = tmp_path / "native-fixture"
    native_root.mkdir()
    local_fixture(native_root, monkeypatch)
    a, b = make_config(tmp_path / "a"), make_config(tmp_path / "b")
    a.worktree.repo_path = b.worktree.repo_path = str(tmp_path / "repo")
    a.worktree.root = b.worktree.root = str(tmp_path / "worktrees")
    a.executor.model, b.executor.model = "model-a", "model-b"
    a.container.runtime, b.container.runtime = "docker", "podman"
    b.execution.backend = "local"
    monkeypatch.setattr(module, "build_forge", lambda *args, **kwargs: FakeForge())
    monkeypatch.setattr(module, "build_executor", lambda *args, **kwargs:
                        SimpleNamespace(model=args[1]))
    from adore import local_execution
    monkeypatch.setattr(local_execution, "LocalBackend", lambda config:
                        SimpleNamespace(environment={"PROJECT": config.executor.model}))
    first, second = [module.Orchestrator.from_config(config, tmp_path / "missing.env")
                     for config in (a, b)]
    # Public admission owns allocation. Keep the external source observation injected.
    for engine in (first, second):
        engine.worktrees.runner = lambda *args, **kwargs: CommandResult()
        engine.worktrees.fresh_branch = lambda base, **kwargs: base
        engine.worktrees.fetch = lambda: None
        engine.worktrees.create = lambda run_id, *args, engine=engine, **kwargs: (
            engine.worktrees.path_for(run_id))
        engine.forge.ticket.labels = ["agent-ready", "P1"]
        engine._probe_repository_payload = lambda: None
        engine._has_payload = lambda _: False
    assert first.poll_once(ticket_iid=7, admit_only=True)["picked"] == 7
    assert second.poll_once(ticket_iid=7, admit_only=True)["picked"] == 7
    left, right = first.store.list_runs()[0], second.store.list_runs()[0]
    assert left.run_id == right.run_id
    assert left.container != right.container and left.worktree != right.worktree
    assert left.branch != right.branch
    assert first.executor.model == "model-a" and second.executor.model == "model-b"
    assert first.containers.runtime == "docker" and second.containers.runtime == "podman"
    assert second.backend.environment == {"PROJECT": "model-b"}


def test_archive_and_profile_deletion_refuse_active_terminal_cleanup(tmp_path, monkeypatch):
    """@brief All project operations observe live cleanup despite terminal saved state."""
    from adore.cli import main
    from adore.web.app import create_app
    from fastapi.testclient import TestClient

    from tests.test_profile_cli import _ready_profile
    home = tmp_path / "server-home"
    profiles = _ready_profile(home)
    profiles.create("other")
    state = StateStore(profiles.default_store_root("proj"))
    state.save(RunState("one", 1, lifecycle="done"))
    with state.execution_slot("one"), TestClient(create_app(home)) as client:
        csrf = client.post("/api/v1/session", json={"username": "admin", "password": "admin"}
                           ).json()["csrf"]
        headers = {"X-CSRF-Token": csrf}
        assert client.post("/api/v1/projects/proj/archive", headers=headers).status_code == 409
        assert client.post("/api/v1/projects/other/archive", headers=headers).status_code == 200
        assert main(["profile", "delete", "proj", "--force"]) != 0
        assert main(["profile", "delete", "proj", "--force", "--remove-resources"]) != 0
        assert profiles.exists("proj")
    # Windows profile removal succeeds with the stable barrier files outside it.
    assert main(["profile", "delete", "proj", "--force"]) == 0
    assert not profiles.exists("proj")


def test_refresh_failure_releases_common_lock_without_touching_peer_credentials(tmp_path):
    """@brief A failed helper does not strand the refresh scope or alter another store."""
    directory, other = tmp_path / "one", tmp_path / "two"
    signed_in(directory)
    signed_in(other)
    previous = (other / "auth.json").read_bytes()
    class Helper:
        fail = True
        def helper_command(self, name, argv, **kwargs):
            return argv
        def runner(self, argv, **kwargs):
            if self.fail:
                raise OSError("injected")
            return CommandResult(stdout=json.dumps({"status": "ok", "token": "request-token-1234",
                                  "expires": (time.time() + 100) * 1000}))
    helper = Helper()
    with pytest.raises(chatgpt.ChatGptError):
        chatgpt.bearer_token(helper, directory, 1)
    helper.fail = False
    assert chatgpt.bearer_token(helper, directory, 1) == "request-token-1234"
    assert (other / "auth.json").read_bytes() == previous


def test_metrics_rejects_database_as_mirror(tmp_path):
    """@brief A conflicting output path cannot replace the database with JSONL."""
    db = tmp_path / "m.db"
    metrics.record_summary(db, metrics.RunSummary("old"))
    with pytest.raises(metrics.MetricsError, match="different files"):
        metrics.record_summary(db, metrics.RunSummary("new"), str(db))
    assert [row.run_id for row in metrics.load_summaries(db)] == ["old"]


@pytest.mark.parametrize("runtime", ["docker", "podman", "wsl -d Ubuntu -- docker"])
@pytest.mark.parametrize("foreign", [False, True])
def test_warm_provision_checks_ownership_before_start(tmp_path, runtime, foreign):
    """@brief Warm provisioning accepts owned mounts and refuses a peer's IO binding."""
    from adore.isolation import ContainerManager

    from tests.test_isolation import FakeRunner, _ok, owned_container_receipt
    runner = FakeRunner(_ok("exited"))
    manager = ContainerManager(runtime, "image", "uv", "npm", runner)
    repo, work, io = [tmp_path / name for name in ("repo", "work", "io")]
    runner.results.extend([owned_container_receipt(
        manager, "owned", repo, work, tmp_path / "foreign" if foreign else io), _ok()])
    if foreign:
        with pytest.raises(IsolationError, match="another run"):
            manager.provision("owned", repo, work, io, {})
        assert not any("start" in command for command in runner.calls)
    else:
        assert manager.provision("owned", repo, work, io, {}) == "started"
        assert runner.calls[-1][-1] == "a" * 64


def test_git_contention_refuses_checkpoint_and_preserves_external_config_lock(tmp_path):
    """@brief External Git contention fails typed without stealing or rewriting its lock."""
    from tests.test_isolation import FakeRunner, _fail
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "work", FakeRunner(
        _fail("fatal: Unable to create index.lock: File exists")))
    with pytest.raises(IsolationError):
        manager.commit_all_if_dirty("one", "owned checkpoint")
    config = tmp_path / "repo" / ".git" / "config"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("[core]\n    worktree = /adore/work\n", encoding="utf-8")
    lock = config.with_name("config.lock")
    lock.write_text("external Git owner", encoding="utf-8")
    before = config.read_bytes()
    with pytest.raises(IsolationError, match="busy"):
        manager.scrub_container_worktree_config()
    assert lock.read_text() == "external Git owner" and config.read_bytes() == before


def test_concurrent_process_log_rotation_keeps_run_attribution(tmp_path):
    """@brief Shared admission logs never race rotation or mix individual records."""
    from adore.process_log import ProcessLogger
    path = tmp_path / "adore.log"
    tokens = [f"run-{i}-unique-evidence" for i in range(20)]
    def append(token):
        ProcessLogger(path, max_bytes=80, backups=30).append(token)
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(append, tokens))
    paths = [path, *[path.with_name(path.name + "." + str(i)) for i in range(1, 31)]]
    lines = [line for file in paths if file.exists() for line in file.read_text().splitlines()]
    assert sorted(line.split(" ", 1)[1] for line in lines) == sorted(tokens)


def test_conduct_cli_writes_only_its_run_process_log(tmp_path, monkeypatch):
    """@brief Independent conduct-run processes have independent diagnostic files."""
    from adore import cli
    engine, *_ = make_engine(tmp_path)
    def conduct(run_id, **kwargs):
        engine.log("owned diagnostic " + run_id)
        return True
    monkeypatch.setattr(engine, "conduct_run", conduct)
    monkeypatch.setattr(cli, "_engine", lambda _: (engine.config, engine))
    for name in ("one", "two"):
        assert cli.main(["conduct", name, "--config-revision", "a" * 64]) == 0
        log = engine.store.run_dir(name) / "adore.log"
        assert "owned diagnostic " + name in log.read_text()
        assert "owned diagnostic " + ("two" if name == "one" else "one") not in log.read_text()
    assert not (engine.store.root / "adore.log").exists()


def test_clone_preview_uses_saved_namespaced_paths_only(tmp_path, monkeypatch):
    """@brief Clone preview recognizes saved project-suffixed worktrees and keeps peers."""
    from types import SimpleNamespace

    from adore import clone_cleanup as cleanup
    run = RunState("one", 1, lifecycle="failed", worktree=str(tmp_path / "one-p123456789abc"))
    monkeypatch.setattr(cleanup, "clone_decision", lambda *args, **kwargs:
                        SimpleNamespace(removable=True, path=str(tmp_path / "clone")))
    monkeypatch.setattr(cleanup, "_linked_folders", lambda _: [Path(run.worktree)])
    config = SimpleNamespace(worktree=SimpleNamespace(repo_path="repo", root="work"),
                             platform=SimpleNamespace(repo="owner/repo"),
                             execution=SimpleNamespace(backend="container"))
    assert cleanup.project_clone_decision(None, "one", config, [run]).removable
    monkeypatch.setattr(cleanup, "_linked_folders", lambda _: [tmp_path / "peer"])
    assert not cleanup.project_clone_decision(None, "one", config, [run]).removable
    run.worktree = ""
    assert not cleanup.project_clone_decision(None, "one", config, [run]).removable


@pytest.mark.parametrize("invalid", [-1, float("nan"), float("inf"), True, "10"])
def test_resource_lock_refuses_unbounded_timeout(tmp_path, invalid):
    """@brief Invalid bounds cannot turn resource contention into an endless wait."""
    with (pytest.raises(ResourceLockError),
          resource_lock(tmp_path / "invalid.lock", timeout=invalid)):
        pytest.fail("invalid lock bound accepted")


def test_cli_loaded_before_archive_cannot_admit_after_barrier(tmp_path, monkeypatch):
    """@brief Archive remains authoritative for a CLI that loaded its config earlier."""
    from adore import cli

    from tests.test_profile_cli import _ready_profile
    profiles = _ready_profile(tmp_path / "server-home")
    engine, forge, *_ = make_engine(tmp_path)
    forge.ticket.labels = ["agent-ready", "P1"]
    monkeypatch.setattr(engine, "_probe_repository_payload", lambda: None)
    def loaded(*args, **kwargs):
        profile = profiles.load("proj")
        profile.archived = True
        profiles.save(profile)
        return engine
    monkeypatch.setattr(cli.Orchestrator, "from_config", loaded)
    assert cli.main(["--profile", "proj", "run", "--once", "--ticket", "7",
                     "--admit-only"]) != 0
    assert not engine.store.list_runs()


def test_delete_api_and_restore_require_safe_project_boundary(tmp_path):
    """@brief Deletion refuses cleanup slots and queued deletion cannot be restored."""
    from adore.profiles import ProfileStore
    from adore.web.app import create_app
    from fastapi.testclient import TestClient
    profiles = ProfileStore(tmp_path / "server-home")
    profile = profiles.create("one", archived=True)
    state = StateStore(profiles.default_store_root("one"))
    state.save(RunState("run", 1, lifecycle="done"))
    with TestClient(create_app(profiles.home)) as client:
        csrf = client.post("/api/v1/session", json={"username": "admin", "password": "admin"}
                           ).json()["csrf"]
        headers = {"X-CSRF-Token": csrf}
        payload = {"confirm_name": "one", "idempotency_key": "delete-owned-one"}
        with state.execution_slot("run"):
            assert client.post("/api/v1/projects/one/delete", headers=headers,
                               json=payload).status_code == 409
        response = client.post("/api/v1/projects/one/delete", headers=headers, json=payload)
        assert response.status_code == 200, response.text
        assert client.post("/api/v1/projects/one/restore", headers=headers).status_code == 409
    assert profiles.load(profile.name).archived


def test_repository_locks_stay_inside_git_metadata(tmp_path):
    """@brief Normal provisioning does not dirty the clone or prevent clone deletion."""
    repo, root = tmp_path / "repo", tmp_path / "worktrees"
    manager = WorktreeManager(repo, root, lambda *args, **kwargs: CommandResult())
    manager.create("owned", "adore/owned", "HEAD", new_branch=True)
    manager.fetch()
    assert [path.name for path in repo.iterdir()] == [".git"]
    assert len(list((repo / ".git" / "adore-resource-locks").glob("*.lock"))) == 2


def test_cancel_one_run_preserves_peer_worktree_and_runtime(tmp_path):
    """@brief Full cancellation targets only one run's dedicated resource identities."""
    from dataclasses import replace
    import shutil
    engine, _, trees, containers, _ = make_engine(tmp_path)
    root = tmp_path / "worktrees"
    trees.path_for = lambda run_id: root / run_id
    first = make_run(engine)
    second_id = "github-owner-repo-8"
    second = replace(first, run_id=second_id, ticket_iid=8,
                     branch=engine._branch_name(second_id, 8),
                     container=engine._container_name(second_id), worktree=str(root / second_id))
    engine.store.save(second)
    for run in (first, second):
        Path(run.worktree).mkdir(parents=True)
    def remove(run_id, **kwargs):
        trees.removed.append(run_id)
        shutil.rmtree(trees.path_for(run_id))
    trees.remove = remove
    assert engine.cancel(first.run_id)
    assert not Path(first.worktree).exists() and Path(second.worktree).is_dir()
    assert engine.store.load(second_id).lifecycle == "working"
    assert containers.removed == [first.container] and trees.removed == [first.run_id]


def test_native_release_preserves_peer_process_scope_and_receipt(tmp_path, monkeypatch):
    """@brief Independent native backends release only their verified control scopes."""
    from adore.local_execution import LocalBackend

    from tests.test_local_execution import local_fixture
    config, context, first, controller, work = local_fixture(tmp_path, monkeypatch)
    second = LocalBackend(config, context=context, controller=controller)
    peer_work = tmp_path / "peer-work"
    peer_work.mkdir()
    first_io = Path(config.state.store_root) / "runs" / "one" / "io"
    peer_io = Path(config.state.store_root) / "runs" / "two" / "io"
    first.provision("first", work, work, first_io, {})
    second.provision("second", work, peer_work, peer_io, {})
    own, peer = first.resource_identity("first"), second.resource_identity("second")
    first.remove("first", expected=own)
    assert own["id"] != peer["id"]
    assert (peer_io.parent / "local-control" / "runtime.json").is_file()
    assert all(call[1] == own["id"] for call in controller.controlled)
    assert second.resource_identity("second") == peer


@pytest.mark.parametrize("profile_owned", [False, True])
def test_same_state_root_keeps_kernel_ownership_across_ambient_homes(tmp_path, monkeypatch,
                                                                    profile_owned):
    """@brief Explicit web home and CLI ambient home cannot split one state lock."""
    root = (tmp_path / "server" / "profiles" / "one" / "state"
            if profile_owned else tmp_path / "external-state")
    first = StateStore(root)
    monkeypatch.setenv("ADORE_HOME", str(tmp_path / "ambient-one"))
    location = first.locks_root
    with first.execution_slot("terminal-cleanup"):
        monkeypatch.setenv("ADORE_HOME", str(tmp_path / "ambient-two"))
        second = StateStore(root)
        assert second.locks_root == location
        with pytest.raises(LockHeldError), second.project_barrier():
            pytest.fail("ambient-home change bypassed an execution reservation")
    if profile_owned:
        assert not location.is_relative_to(root.parent)
    else:
        assert location == root / "locks"


def test_explicit_web_home_barrier_matches_child_cli_ownership(tmp_path, monkeypatch):
    """@brief Supported --home deployment sees terminal slots despite a different ambient home."""
    from adore.profiles import ProfileStore
    from adore.web.app import create_app
    from fastapi.testclient import TestClient
    home = tmp_path / "explicit-web-home"
    profiles = ProfileStore(home)
    profiles.create("one")
    root = profiles.default_store_root("one")
    child = StateStore(root)
    monkeypatch.setenv("ADORE_HOME", str(home))
    with child.execution_slot("cleanup-without-state"):
        monkeypatch.setenv("ADORE_HOME", str(tmp_path / "different-ambient-home"))
        with TestClient(create_app(home)) as client:
            csrf = client.post("/api/v1/session", json={"username": "admin", "password": "admin"}
                               ).json()["csrf"]
            response = client.post("/api/v1/projects/one/archive", headers={"X-CSRF-Token": csrf})
            assert response.status_code == 409
            assert not profiles.load("one").archived


def test_metrics_delete_and_upsert_publish_one_current_snapshot(tmp_path, monkeypatch):
    """@brief A delayed deletion export cannot overwrite a concurrently completed row."""
    db, mirror = tmp_path / "metrics.db", tmp_path / "metrics.jsonl"
    metrics.record_summary(db, metrics.RunSummary("deleted"), str(mirror))
    metrics.record_summary(db, metrics.RunSummary("retained"), str(mirror))
    entered, release, second_started = Event(), Event(), Event()
    original = metrics.load_summaries
    def load(path, *args, **kwargs):
        rows = original(path, *args, **kwargs)
        if {row.run_id for row in rows} == {"retained"}:
            entered.set()
            assert release.wait(5)
        return rows
    monkeypatch.setattr(metrics, "load_summaries", load)
    def upsert():
        second_started.set()
        metrics.record_summary(db, metrics.RunSummary("completed"), str(mirror))
    with ThreadPoolExecutor(2) as pool:
        deletion = pool.submit(metrics.delete_summary, db, "deleted", str(mirror))
        try:
            assert entered.wait(5)
            completion = pool.submit(upsert)
            assert second_started.wait(5)
            with suppress(TimeoutError):
                completion.result(0.2)
        finally:
            release.set()
        deletion.result(5)
        completion.result(5)
    expected = {"retained", "completed"}
    assert {row.run_id for row in original(db)} == expected
    assert {json.loads(line)["run_id"] for line in mirror.read_text().splitlines()} == expected


@pytest.mark.parametrize("contains", ["state", "locks"])
def test_clone_containing_retained_state_is_not_removed(tmp_path, monkeypatch, contains):
    """@brief Optional clone removal cannot delete retained state or held kernel inodes."""
    from types import SimpleNamespace

    from adore import clone_cleanup as cleanup
    clone = tmp_path / ("clone" if contains == "state" else "locks")
    state_root = clone / "state" if contains == "state" else tmp_path
    monkeypatch.setattr(cleanup, "clone_decision", lambda *args, **kwargs:
                        SimpleNamespace(removable=True, path=str(clone)))
    config = SimpleNamespace(worktree=SimpleNamespace(repo_path=str(clone)),
                             platform=SimpleNamespace(repo="owner/repo"),
                             state=SimpleNamespace(store_root=str(state_root)))
    assert not cleanup.project_clone_decision(None, "one", config, []).removable


def test_nested_profile_barrier_survives_profile_directory_deletion(tmp_path):
    """@brief Stable inode placement stays outside every enclosing profile after removal."""
    import shutil
    outer = tmp_path / "server" / "profiles" / "outer"
    root = outer / "nested" / "profiles" / "inner" / "state"
    store = StateStore(root)
    store.save(RunState("finished", 1, lifecycle="done"))
    location = store.locks_root
    assert not location.is_relative_to(outer)
    with store.project_barrier():
        shutil.rmtree(outer)
        assert store.locks_root == StateStore(root).locks_root == location
        with pytest.raises(LockHeldError), StateStore(root).run_lock("finished"):
            pytest.fail("profile removal replaced a still-owned kernel inode")
    assert not root.exists()


# END OF FILE
