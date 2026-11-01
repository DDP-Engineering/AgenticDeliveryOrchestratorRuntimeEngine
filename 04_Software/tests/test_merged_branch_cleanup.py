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
@file    test_merged_branch_cleanup.py
@brief   Offline contracts for human-merged branch cleanup on all forges.
@details Public polling and injected Git transport prove deletion and fail-closed boundaries.
"""

from __future__ import annotations

import json

from adore.config import validate_config
from adore.forge import ForgeError, GiteaForge
from adore.isolation import IsolationError, WorktreeManager
import pytest

from tests.test_forge import FakeRunner as ForgeRunner
from tests.test_forge import _api_ok
from tests.test_isolation import FakeRunner, _fail, _ok
from tests.test_orchestrator import make_engine, make_run


@pytest.mark.parametrize("kind", ["github", "gitlab", "gitea"])
@pytest.mark.parametrize("enabled", [True, False])
def test_merged_run_branch_cleanup_on_every_forge(tmp_path, kind, enabled):
    """@brief Public polling obeys the same cleanup choice on each forge."""
    engine, forge, worktrees, containers, _ = make_engine(tmp_path)
    engine.config.platform.kind = kind
    engine.config.delivery.remove_source_branch = enabled
    run = make_run(engine)
    run.lifecycle, run.stage, run.mr_iid = "in-review", "done", 9
    run.checkpoint_remote_commit = "d" * 40
    engine.store.save(run)
    engine.store.pause()
    forge.mr.state = "merged"
    deletions = []
    worktrees.remove_remote_branch = lambda *args: deletions.append(args)
    summary = engine.poll_once()
    assert summary["done"] == 1
    assert engine.store.load(run.run_id).outcome == "merged by human"
    assert deletions == ([(run.branch, "d" * 40, "main")] if enabled else [])
    assert worktrees.removed == [run.run_id]
    assert containers.removed == [run.container]


@pytest.mark.parametrize("state", ["opened", "closed"])
def test_unmerged_review_keeps_remote_branch(tmp_path, state):
    """@brief An open or closed unmerged review never authorizes deletion."""
    engine, forge, worktrees, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle, run.stage, run.mr_iid = "in-review", "done", 9
    engine.store.save(run)
    engine.store.pause()
    forge.mr.state = state
    deletions = []
    worktrees.remove_remote_branch = lambda *args: deletions.append(args)
    assert engine.poll_once()["done"] == 0
    assert deletions == []


def test_cleanup_failure_keeps_merge_outcome_and_local_evidence(tmp_path):
    """@brief Bounded transport failure reports retained branch without undoing human merge."""
    engine, forge, worktrees, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle, run.stage, run.mr_iid = "in-review", "done", 9
    engine.store.save(run)
    engine.store.pause()
    forge.mr.state = "merged"
    calls = []

    def refuse(*args):
        """@brief Simulate server refusing branch deletion."""
        calls.append(args)
        raise IsolationError("branch deletion refused")

    worktrees.remove_remote_branch = refuse
    assert engine.poll_once()["done"] == 1
    result = engine.store.load(run.run_id)
    assert result.lifecycle == "done"
    assert "merged by human" in result.outcome
    assert "branch retained" in result.outcome
    assert len(calls) == engine.config.recovery.max_transient_retries
    assert worktrees.removed == []


def test_publication_pins_head_when_progress_commits_disabled(tmp_path):
    """@brief Final approved push preserves exact commit identity for later cleanup."""
    engine, _, worktrees, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    assert engine.config.delivery.publish_checkpoints is False
    assert engine._push_branch(run).ok
    assert engine.store.load(run.run_id).checkpoint_remote_commit == worktrees.target


@pytest.mark.parametrize("foreign", ["branch", "review"])
def test_changed_cleanup_ownership_retains_branch(tmp_path, foreign):
    """@brief Persisted run or review ownership drift cannot authorize remote deletion."""
    engine, forge, worktrees, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle, run.stage, run.mr_iid = "in-review", "done", 9
    if foreign == "branch":
        run.branch = "somebody-elses-branch"
    else:
        run.mr_iid = 99
        forge.get_merge_request = lambda ref: forge.mr
    engine.store.save(run)
    engine.store.pause()
    forge.mr.state = "merged"
    calls = []
    worktrees.remove_remote_branch = lambda *args: calls.append(args)
    engine.poll_once()
    assert calls == []
    assert "branch retained" in engine.store.load(run.run_id).outcome
    assert worktrees.removed == []


@pytest.mark.parametrize("results", [
    [_fail("invalid ref")], [_ok(), _fail("remote unavailable")],
    [_ok(), _ok("a" * 40 + "\trefs/heads/adore/run-7"), _fail("local ref missing")],
])
def test_git_identity_failure_never_deletes(tmp_path, results):
    """@brief Git validation and missing legacy ownership fail closed before deletion."""
    runner = FakeRunner(*results)
    with pytest.raises(IsolationError):
        WorktreeManager(tmp_path, tmp_path / "worktrees", runner=runner).remove_remote_branch(
            "adore/run-7", "", "main",
        )
    assert not any("push" in call for call in runner.calls)


def test_remote_branch_removal_uses_exact_lease(tmp_path):
    """@brief The recorded publication identity authorizes only exact leased deletion."""
    ref = "refs/heads/adore/run-7"
    remote = "a" * 40
    runner = FakeRunner(_ok(), _ok(remote + "\t" + ref), _ok(), _ok())
    WorktreeManager(tmp_path, tmp_path / "worktrees", runner=runner).remove_remote_branch(
        "adore/run-7", remote, "main",
    )
    push = next(call for call in runner.calls if "push" in call)
    assert push[-4:] == ["push", f"--force-with-lease={ref}:{remote}", "origin", f":{ref}"]


def test_already_removed_branch_is_success_without_local_branch(tmp_path):
    """@brief Native forge auto-deletion and crash recovery are idempotent."""
    runner = FakeRunner(_ok(), _ok())
    WorktreeManager(tmp_path, tmp_path / "worktrees", runner=runner).remove_remote_branch(
        "adore/run-7", "a" * 40, "main",
    )
    assert not any("push" in call or "rev-parse" in call for call in runner.calls)


@pytest.mark.parametrize("output", [
    "b" * 40 + "\trefs/heads/adore/run-7",
    "a" * 40 + "\trefs/heads/foreign",
    "not-a-sha\trefs/heads/adore/run-7",
    "a" * 40 + "\trefs/heads/adore/run-7\n" + "b" * 40 + "\trefs/heads/adore/run-7",
])
def test_foreign_or_malformed_remote_identity_fails_closed(tmp_path, output):
    """@brief Foreign commits and malformed Git output cannot reach a delete command."""
    runner = FakeRunner(_ok(), _ok(output))
    with pytest.raises(IsolationError):
        WorktreeManager(tmp_path, tmp_path / "worktrees", runner=runner).remove_remote_branch(
            "adore/run-7", "a" * 40, "main",
        )
    assert not any("push" in call for call in runner.calls)


@pytest.mark.parametrize("branch,expected", [("main", "a" * 40), ("-x", "a" * 40),
                                         ("adore/run-7", "bad-sha")])
def test_invalid_or_target_branch_is_never_deleted(tmp_path, branch, expected):
    """@brief Reject protected target and invalid inputs before destructive transport."""
    runner = FakeRunner()
    with pytest.raises(IsolationError):
        WorktreeManager(tmp_path, tmp_path / "worktrees", runner=runner).remove_remote_branch(
            branch, expected, "main",
        )
    assert runner.calls == []


@pytest.mark.parametrize("after", ["a" * 40, "b" * 40])
def test_refused_or_racing_deletion_is_not_success(tmp_path, after):
    """@brief Server refusal and concurrent branch replacement preserve explicit failure."""
    ref = "refs/heads/adore/run-7"
    runner = FakeRunner(_ok(), _ok("a" * 40 + "\t" + ref),
                        _fail("refused"), _ok(after + "\t" + ref))
    with pytest.raises(IsolationError):
        WorktreeManager(tmp_path, tmp_path / "worktrees", runner=runner).remove_remote_branch(
            "adore/run-7", "a" * 40, "main",
        )


@pytest.mark.parametrize("value", [1, "false", None])
def test_branch_removal_choice_requires_boolean(tmp_path, value):
    """@brief Human configuration cannot enable deletion through truthy text or numbers."""
    engine, *_ = make_engine(tmp_path)
    engine.config.delivery.remove_source_branch = value
    assert any("remove_source_branch must be a boolean" in issue
               for issue in validate_config(engine.config))


@pytest.mark.parametrize("value", ["false", "true", 1, None])
def test_gitea_merge_evidence_requires_boolean(value):
    """@brief Malformed external merge evidence cannot authorize branch removal."""
    runner = ForgeRunner(_api_ok(json.dumps(
        {"number": 9, "state": "closed", "merged": value},
    )))
    with pytest.raises(ForgeError, match="merged"):
        GiteaForge("owner/repo", runner=runner).get_merge_request(9)
