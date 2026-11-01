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
@file test_checkpoint_handoff.py
@brief Checkpoint publication and human handoff contracts.
@details Uses only injected offline fakes; no forge, git, container or model is
         contacted. The tests focus on observable contracts and fail-closed
         trust boundaries rather than private implementation structure.
"""

from __future__ import annotations

import json
from pathlib import Path

from adore.cli import main
from adore.config import load_config, validate_config
import adore.isolation as isolation_module
from adore.isolation import IsolationError, WorktreeManager
from adore.state import RunState, StateError, StateStore
import pytest

from .test_config import MINIMAL_VALID
from .test_isolation import FakeRunner, _fail, _ok
from .test_orchestrator import FakeAegis, FakeWorktrees, make_engine, make_run, task
from .test_smoke import _config_file


class CheckpointWorktrees(FakeWorktrees):
    """@brief Script guarded checkpoint transport independently of delivery pushes."""

    def __init__(self):
        super().__init__()
        self.remote_pushes = []
        self.transport_errors = []
        self.head = "d" * 40
        self.commit_error = False

    def push_checkpoint(self, run_id, branch, expected):
        self.remote_pushes.append((branch, expected))
        if self.transport_errors:
            raise self.transport_errors.pop(0)
        return self.head

    def ref_head(self, ref):
        return self.target if ref.startswith("origin/") else self.head

    def worktree_progress_fingerprint(self, run_id):
        """@brief Keep simulated source progress stable across checkpoint transport."""
        return self.fingerprint

    def commit_all_if_dirty(self, run_id, message):
        if self.commit_error:
            raise IsolationError("commit failed; dirty files retained")
        return super().commit_all_if_dirty(run_id, message)


def setup_run(tmp_path):
    """@brief Return a run with independently observable checkpoint transport."""
    engine, forge, _, containers, executor = make_engine(tmp_path)
    engine.worktrees = CheckpointWorktrees()
    run = make_run(engine)
    return engine, run, forge, engine.worktrees, containers, executor


def test_checkpoint_handoff_configuration_default_on(tmp_path):
    """@brief Profiles without an override publish guarded progress by default."""
    path = tmp_path / "config.toml"
    path.write_text(MINIMAL_VALID)
    assert load_config(path).delivery.publish_checkpoints is True


@pytest.mark.parametrize(
    "value,valid", [("true", True), ("false", True), ("1", False), ('"yes"', False)]
)
def test_checkpoint_handoff_configuration_boolean_boundary(tmp_path, value, valid):
    """@brief Explicit overrides accept only TOML booleans."""
    path = tmp_path / "config.toml"
    path.write_text(MINIMAL_VALID + "\npublish_checkpoints = " + value)
    config = load_config(path)
    issues = validate_config(config)
    assert any("publish_checkpoints" in issue for issue in issues) is (not valid)
    if valid:
        assert config.delivery.publish_checkpoints is (value == "true")


@pytest.mark.parametrize("enabled", [False, True])
def test_checkpoint_handoff_progress_push_retains_approval_boundary(tmp_path, enabled):
    """@brief Progress publication follows the selected policy and retains approval."""
    engine, run, forge, worktrees, _, executor = setup_run(tmp_path)
    engine.config.delivery.publish_checkpoints = enabled
    run.stage = "build"
    engine.store.save(run)
    snapshots = [
        task("build"),
        task("validate"),
        task("validate"),
        task("done"),
        task("done"),
        task("done"),
    ]
    engine._conduct_task(run, forge.ticket, FakeAegis(snapshots), "")
    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "awaiting-approval"
    assert bool(worktrees.remote_pushes) is enabled
    assert worktrees.pushes == [] and forge.opened == []
    if enabled:
        assert saved.checkpoint_remote_commit == worktrees.head
        assert "Work in progress" in "\n".join(forge.ticket_comments.values())
        assert any(e["event"] == "checkpoint-pushed" for e in engine.store.read_journal(run.run_id))


def test_checkpoint_handoff_transport_failure_is_visible_and_recovers(tmp_path):
    """@brief Failed progress uploads retain local commits and report stale remote state."""
    engine, run, forge, worktrees, _, _ = setup_run(tmp_path)
    engine.config.delivery.publish_checkpoints = True
    worktrees.transport_errors = [IsolationError("transport unavailable")] * 3
    run.stage = "build"
    engine.store.save(run)
    engine._conduct_task(
        run,
        forge.ticket,
        FakeAegis(
            [
                task("build"),
                task("validate"),
                task("validate"),
                task("done"),
                task("done"),
                task("done"),
            ]
        ),
        "",
    )
    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "awaiting-approval"
    assert any(
        e["event"] == "checkpoint-push-failed" for e in engine.store.read_journal(run.run_id)
    )
    assert "remote checkpoint" in "\n".join(forge.ticket_comments.values()).lower()
    assert saved.checkpoint_error == ""
    assert saved.checkpoint_remote_commit == worktrees.head


def test_checkpoint_handoff_remote_ownership_stops_execution(tmp_path):
    """@brief A foreign remote update prevents another executor launch."""
    engine, run, forge, worktrees, _, executor = setup_run(tmp_path)
    engine.config.delivery.publish_checkpoints = True
    worktrees.transport_errors = [
        isolation_module.CheckpointConflictError("developer changed branch")
    ]
    run.stage = "build"
    engine.store.save(run)
    engine._conduct_task(run, forge.ticket, FakeAegis([task("build"), task("validate")]), "")
    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "failed"
    assert "REMOTE_CHECKPOINT_CONFLICT" in saved.outcome
    assert len(executor.prompts) == 1
    assert len(worktrees.remote_pushes) == 1


@pytest.mark.parametrize("notification_failure", [False, True])
def test_checkpoint_handoff_idle_preserves_human_ownership(tmp_path, notification_failure):
    """@brief Handoff preserves resources and ownership even when forge signaling fails."""
    engine, run, forge, worktrees, containers, executor = setup_run(tmp_path)
    run.lifecycle = "failed"
    engine.store.save(run)
    forge.fail_comments = notification_failure
    assert engine.handoff(run.run_id)
    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "handed-off"
    assert run.container in containers.stopped
    assert not containers.removed and not worktrees.removed
    assert worktrees.remote_pushes and not forge.opened
    assert not engine.retry(run.run_id)
    assert not engine.reset(run.run_id, "build")
    engine.config.worktree.root = str(tmp_path)
    engine.store.pause()
    worktrees.dirs = [Path(run.worktree)]
    engine.poll_once()
    engine.cleanup()
    assert not worktrees.removed and not executor.prompts
    assert engine.handoff(run.run_id)
    assert len(worktrees.remote_pushes) == 1


@pytest.mark.parametrize("failure", ["stop", "commit", "push"])
def test_checkpoint_handoff_failure_preserves_recovery_evidence(tmp_path, failure):
    """@brief Failed stop grants no ownership; commit or push failure retains local recovery."""
    engine, run, forge, worktrees, containers, _ = setup_run(tmp_path)
    if failure == "stop":

        def stop(_):
            raise IsolationError("stop unavailable")

        containers.stop = stop
    elif failure == "commit":
        worktrees.dirty = True
        worktrees.commit_error = True
    else:
        worktrees.transport_errors = [IsolationError("push unavailable")] * 3
    result = engine.handoff(run.run_id)
    saved = engine.store.load(run.run_id)
    assert result is (failure != "stop")
    assert saved.lifecycle == ("handoff-pending" if failure == "stop" else "handed-off")
    assert not worktrees.removed and not containers.removed
    if failure != "stop":
        assert saved.checkpoint_error
        assert "local" in "\n".join(forge.ticket_comments.values()).lower()


def test_checkpoint_handoff_request_after_gate_prevents_next_session(tmp_path):
    """@brief A request arriving during a gate transfers only after that gate returns."""
    engine, run, forge, worktrees, containers, executor = setup_run(tmp_path)
    original = executor.run_gate

    def gate(*args, **kwargs):
        engine.store.request_handoff(run.run_id)
        assert run.container not in containers.stopped
        return original(*args, **kwargs)

    executor.run_gate = gate
    run.stage = "build"
    engine.store.save(run)
    engine._conduct_task(run, forge.ticket, FakeAegis([task("build"), task("validate")]), "")
    assert engine.store.load(run.run_id).lifecycle == "handed-off"
    assert len(executor.prompts) == 1
    assert not engine.store.handoff_requested(run.run_id)


def test_checkpoint_handoff_state_is_strict(tmp_path):
    """@brief Missing or corrupt checkpoint identities fail closed."""
    original = RunState("run-1", 1).to_dict()
    missing = {key: value for key, value in original.items()
               if key not in ("checkpoint_remote_commit", "checkpoint_error")}
    with pytest.raises(StateError, match="missing keys"):
        RunState.from_dict(missing)
    original["checkpoint_remote_commit"] = "not-a-commit"
    with pytest.raises(StateError):
        RunState.from_dict(original)


def test_checkpoint_handoff_request_rejects_corrupt_or_foreign_marker(tmp_path):
    """@brief Durable requests carry exact run identity and cannot target arbitrary paths."""
    engine, run, _, _, _, _ = setup_run(tmp_path)
    engine.store.request_handoff(run.run_id)
    assert engine.store.handoff_requested(run.run_id)
    marker = engine.store.run_dir(run.run_id) / "handoff-request.json"
    marker.write_text(json.dumps({"run_id": "foreign"}))
    with pytest.raises(StateError):
        engine.store.handoff_requested(run.run_id)
    with pytest.raises((StateError, FileNotFoundError)):
        engine.store.request_handoff("../escape")


def test_checkpoint_handoff_cli_queues_with_live_lock(tmp_path, monkeypatch, capsys):
    """@brief An operator may request handoff without stealing the conductor lock."""
    import adore.cli as cli

    config_path = _config_file(tmp_path)
    config = load_config(config_path)
    store = StateStore(config.state.store_root, config.agent.slug)
    store.save(RunState("run-1", 1))
    assert store.acquire_lock()

    class Engine:
        def handoff(self, run_id):
            pytest.fail("must queue while conductor owns lock")

    monkeypatch.setattr(cli, "_engine", lambda _: (config, Engine()))
    try:
        assert main(["-c", config_path, "handoff", "run-1"]) == 0
        assert "queued" in capsys.readouterr().out
        assert store.handoff_requested("run-1")
    finally:
        store.release_lock()


@pytest.mark.parametrize("remote", ["", "a" * 40 + "\trefs/heads/adore/ticket\n"])
def test_checkpoint_handoff_guarded_git_push(tmp_path, remote):
    """@brief A compare-and-update push accepts a new branch or owned ancestor only."""
    head = "b" * 40
    replies = [_ok(), _ok("refs/heads/adore/ticket"), _ok(head), _ok(remote)]
    if remote:
        replies.append(_ok())
    replies += [_ok(), _ok(head + "\trefs/heads/adore/ticket\n")]
    runner = FakeRunner(*replies)
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    assert manager.push_checkpoint("run-1", "adore/ticket", "a" * 40 if remote else "") == head
    push = next(c for c in runner.calls if "push" in c)
    assert f"--force-with-lease=refs/heads/adore/ticket:{'a' * 40 if remote else ''}" in push
    assert "--force" not in push


@pytest.mark.parametrize(
    "remote",
    [
        "bad\trefs/heads/adore/ticket",
        "a" * 40 + "\trefs/heads/foreign",
        "a" * 40 + "\trefs/heads/adore/ticket\n" + "a" * 40 + "\trefs/heads/adore/ticket",
    ],
)
def test_checkpoint_handoff_malformed_remote_never_pushes(tmp_path, remote):
    """@brief Foreign, duplicate and malformed remote identities fail closed."""
    runner = FakeRunner(_ok(), _ok("refs/heads/adore/ticket"), _ok("b" * 40), _ok(remote))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(IsolationError):
        manager.push_checkpoint("run-1", "adore/ticket", "")
    assert not any("push" in c for c in runner.calls)


def test_checkpoint_handoff_remote_conflict_and_push_race(tmp_path):
    """@brief Unexpected remote commits and rejected leases never fall back to force."""
    foreign = "c" * 40 + "\trefs/heads/adore/ticket\n"
    runner = FakeRunner(_ok(), _ok("refs/heads/adore/ticket"), _ok("b" * 40), _ok(foreign))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(isolation_module.CheckpointConflictError):
        manager.push_checkpoint("run-1", "adore/ticket", "a" * 40)
    assert not any("push" in c for c in runner.calls)
    runner = FakeRunner(
        _ok(),
        _ok("refs/heads/adore/ticket"),
        _ok("b" * 40),
        _ok(),
        _fail("stale info"),
        _ok(foreign),
    )
    manager.runner = runner
    with pytest.raises(isolation_module.CheckpointConflictError):
        manager.push_checkpoint("run-1", "adore/ticket", "")
    assert sum("push" in c for c in runner.calls) == 1


def test_checkpoint_handoff_failed_run_publishes_commits_without_resuming(tmp_path):
    """@brief Failed recovery checkpoints become remote without any executor or dirty commit."""
    engine, run, forge, worktrees, _, executor = setup_run(tmp_path)
    engine.config.delivery.publish_checkpoints = True
    run.lifecycle = "failed"
    run.outcome = "NO_STAGE_PROGRESS: preserved"
    engine.store.save(run)
    worktrees.dirty = True
    engine.store.pause()
    engine.poll_once()
    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "failed" and saved.outcome == run.outcome
    assert saved.checkpoint_remote_commit == worktrees.head
    assert worktrees.dirty and not worktrees.checkpoints
    assert not executor.prompts and not forge.opened
    state_path = engine.store.run_dir(run.run_id) / "state.json"
    state_before = state_path.read_bytes()
    pushes_before = list(worktrees.remote_pushes)
    engine.poll_once()
    assert state_path.read_bytes() == state_before
    assert worktrees.remote_pushes == pushes_before


def test_checkpoint_handoff_protocol_failure_stops_without_transport_retries(tmp_path):
    """@brief Malformed Git identities stop instead of being treated as a transient outage."""
    engine, run, forge, worktrees, _, executor = setup_run(tmp_path)
    engine.config.delivery.publish_checkpoints = True
    worktrees.transport_errors = [isolation_module.CheckpointProtocolError("foreign ref")]
    run.stage = "build"
    engine.store.save(run)
    engine._conduct_task(run, forge.ticket, FakeAegis([task("build"), task("validate")]), "")
    assert engine.store.load(run.run_id).outcome.startswith("REMOTE_CHECKPOINT_PROTOCOL:")
    assert len(worktrees.remote_pushes) == len(executor.prompts) == 1
    engine.store.pause()
    engine.poll_once()
    assert len(worktrees.remote_pushes) == 1


def test_checkpoint_handoff_git_replay_nonancestor_and_failed_transport(tmp_path):
    """@brief A published head is idempotent; rewriting ancestry is refused; outage is visible."""
    head = "b" * 40
    runner = FakeRunner(
        _ok(), _ok("refs/heads/adore/ticket"), _ok(head), _ok(head + "\trefs/heads/adore/ticket\n")
    )
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    assert manager.push_checkpoint("run-1", "adore/ticket", "") == head
    assert not any("push" in call for call in runner.calls)
    runner = FakeRunner(
        _ok(),
        _ok("refs/heads/adore/ticket"),
        _ok(head),
        _ok("a" * 40 + "\trefs/heads/adore/ticket\n"),
        _fail("not an ancestor"),
    )
    manager.runner = runner
    with pytest.raises(isolation_module.CheckpointConflictError):
        manager.push_checkpoint("run-1", "adore/ticket", "a" * 40)
    assert not any("push" in call for call in runner.calls)
    runner = FakeRunner(
        _ok(), _ok("refs/heads/adore/ticket"), _ok(head), _ok(), _fail("transport down"), _ok()
    )
    manager.runner = runner
    with pytest.raises(IsolationError):
        manager.push_checkpoint("run-1", "adore/ticket", "")


@pytest.mark.parametrize(
    "kind,url,fragment",
    [
        ("gitea", "https://forge/owner/repo/issues/7", "/src/branch/"),
        ("github", "https://forge/owner/repo/issues/7", "/tree/"),
        ("gitlab", "https://forge/group/repo/-/issues/7", "/-/tree/"),
    ],
)
def test_checkpoint_handoff_comment_has_forge_branch_link(tmp_path, kind, url, fragment):
    """@brief Handoff links are portable across all three forge adapters."""
    engine, run, forge, _, _, _ = setup_run(tmp_path)
    engine.config.platform.kind = kind
    snapshot = engine.store.load_ticket(run.run_id)
    snapshot["web_url"] = url
    engine.store.save_ticket(run.run_id, snapshot)
    assert engine.handoff(run.run_id)
    body = "\n".join(forge.ticket_comments.values())
    assert fragment + "adore%2Fgithub-owner-repo-7" in body
    # the takeover note names the AEGIS 0.15.0 resume view, not a Handoff section
    assert "python .agentic/aegis.py brief" in body
    assert "and Handoff" not in body


def test_checkpoint_handoff_metrics_records_human_ownership(tmp_path):
    """@brief Explicit takeover is a terminal ownership outcome, distinct from merge or failure."""
    from adore.metrics import is_terminal

    assert is_terminal("handed-off")
    assert not is_terminal("working")


def test_checkpoint_handoff_pending_crash_resumes_before_any_executor(tmp_path):
    """@brief A crash during transfer resumes finalization and never resumes development."""
    engine, run, forge, worktrees, containers, executor = setup_run(tmp_path)
    engine.store.request_handoff(run.run_id)
    run.lifecycle = "handoff-pending"
    engine.store.save(run)
    engine.store.pause()
    engine.poll_once()
    assert engine.store.load(run.run_id).lifecycle == "handed-off"
    assert worktrees.remote_pushes and run.container in containers.stopped
    assert not executor.prompts


def test_checkpoint_handoff_owner_not_announced_before_git_finishes(tmp_path):
    """@brief A developer cannot see handed-off while the conductor still writes Git files."""
    engine, run, _, worktrees, _, _ = setup_run(tmp_path)
    original = worktrees.commit_all_if_dirty

    def commit(run_id, message):
        assert engine.store.load(run_id).lifecycle == "handoff-pending"
        return original(run_id, message)

    worktrees.commit_all_if_dirty = commit
    assert engine.handoff(run.run_id)
    assert engine.store.load(run.run_id).lifecycle == "handed-off"


def test_checkpoint_handoff_delivery_still_requires_fresh_approval(tmp_path, monkeypatch):
    """@brief WIP visibility preserves normal approved draft publication without AEGIS."""
    import adore.orchestrator as conductor
    from adore.util import utc_now_iso

    from .test_orchestrator import passing_check

    engine, run, forge, worktrees, _, executor = setup_run(tmp_path)
    engine.config.delivery.publish_checkpoints = True
    run.stage = "done"
    run.lifecycle = "awaiting-approval"
    run.validation_evidence = engine._validation_payload(passing_check())
    run.candidate_fingerprint = worktrees.fingerprint
    run.candidate_base_ref = worktrees.target
    run.approval_label_removed = True
    run.approval_presented_at = utc_now_iso()
    engine.store.save(run)
    engine.store.pause()
    engine.poll_once()
    assert not forge.opened and not worktrees.pushes
    forge.ticket.labels.append("agent-approved")

    class NoAegis:
        """@brief Publication runs no AEGIS command after approval."""

        def __init__(self, *args, **kwargs):
            raise AssertionError("publication must not run an AEGIS command")

    monkeypatch.setattr(conductor, "AegisClient", NoAegis)
    engine.poll_once()
    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "in-review" and forge.opened[0]["draft"] is True
    assert saved.checkpoint_remote_commit == worktrees.head
    assert worktrees.pushes == [run.branch]
    assert executor.prompts == []


@pytest.mark.parametrize("lifecycle", ["done", "cancelled"])
def test_checkpoint_handoff_cli_rejects_released_run(tmp_path, monkeypatch, capsys, lifecycle):
    """@brief Completed resources cannot be reclaimed as a human takeover."""
    import adore.cli as cli

    config_path = _config_file(tmp_path)
    config = load_config(config_path)
    store = StateStore(config.state.store_root, config.agent.slug)
    store.save(RunState("run-1", 1, lifecycle=lifecycle))
    monkeypatch.setattr(cli, "_engine", lambda _: (config, None))
    assert main(["-c", config_path, "handoff", "run-1"]) == 1
    assert "cannot request handoff" in capsys.readouterr().out


def test_checkpoint_handoff_cli_completes_when_lock_is_free(tmp_path, monkeypatch, capsys):
    """@brief Idle operator handoff takes the conductor lock and uses the typed engine."""
    import adore.cli as cli

    config_path = _config_file(tmp_path)
    config = load_config(config_path)
    store = StateStore(config.state.store_root, config.agent.slug)
    store.save(RunState("run-1", 1))

    class Engine:
        def handoff(self, run_id):
            assert store.lock_info() is not None
            assert store.handoff_requested(run_id)
            return True

    monkeypatch.setattr(cli, "_engine", lambda _: (config, Engine()))
    assert main(["-c", config_path, "handoff", "run-1"]) == 0
    assert "handed off" in capsys.readouterr().out
    assert store.lock_info() is None


def test_checkpoint_handoff_foreign_local_branch_never_pushes(tmp_path):
    """@brief Local manual checkout changes do not publish another branch as the candidate."""
    runner = FakeRunner(_ok(), _ok("refs/heads/developer"))
    manager = WorktreeManager(tmp_path / "repo", tmp_path / "worktrees", runner)
    with pytest.raises(isolation_module.CheckpointConflictError):
        manager.push_checkpoint("run-1", "adore/ticket", "")
    assert not any("push" in call for call in runner.calls)
