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
@file test_orchestrator.py
@brief ADORE conductor, recovery, approval and notification tests.
@details Uses only injected offline fakes; no forge, git, container or model is
         contacted. The tests focus on observable contracts and fail-closed
         trust boundaries rather than private implementation structure.
"""

from __future__ import annotations

# IMPORTS
from collections import deque
from dataclasses import replace
import os
from pathlib import Path
from threading import Event

from adore.aegis import (
    AegisCheck,
    AegisCommandRun,
    AegisFinding,
    AegisTask,
    AegisTaskError,
    AegisTimeoutError,
)
from adore.config import Config, ContainerEgressConfig, ExecutorCommand
from adore.executor.base import GateRun
from adore.forge import Comment, Forge, ForgeError, MergeRequest, Ticket
from adore.isolation import ContainerManager, IsolationError
from adore.metrics import aggregate, load_summaries, profile_stats
import adore.orchestrator as orchestrator_module
from adore.orchestrator import Orchestrator
from adore.state import RunState, StateError, StateStore, content_hash
from adore.util import CommandResult, utc_now_iso
import pytest

# CONSTANTS

TASK_ID = "TASK-abc123ef"


# DATA MODELS / TYPEDEFINITIONS


class FakeForge:
    """@brief In-memory forge implementing both ticket and MR comment surfaces."""

    def __init__(self, ticket: Ticket | None = None) -> None:
        self.ticket = ticket or Ticket(
            iid=7,
            title="Bounded change",
            description="## Acceptance Criteria\n- [ ] Works",
            labels=["P1", "agent-working"],
        )
        self.mr = MergeRequest(iid=9, state="opened", web_url="https://forge/pr/9")
        self.ticket_comments: dict[int, str] = {}
        self.mr_comments: dict[int, str] = {}
        self.fail_comments = False
        self.fail_mr_label_removal = False
        self.next_comment = 100
        self.opened: list[dict] = []
        self.branch_mr_exists = False
        self.pipeline = "unknown"
        self.ready: list[Ticket] | None = None

    def list_ready(self, ready_label: str):
        # `ready` overrides the filtered answer, so a test can simulate a server
        # that silently ignores an unrecognised `labels=` filter.
        if self.ready is not None:
            return list(self.ready)
        return [self.ticket] if self.ticket and ready_label in self.ticket.labels else []

    def get_ticket(self, iid: int):
        return self.ticket if self.ticket and self.ticket.iid == iid else None

    def list_comments(self, iid: int):
        return [Comment(id=key, body=value) for key, value in self.ticket_comments.items()]

    def post_comment(self, iid: int, body: str):
        if self.fail_comments:
            raise ForgeError("ticket transport unavailable")
        self.next_comment += 1
        self.ticket_comments[self.next_comment] = body
        return self.next_comment

    def edit_comment(self, iid: int, comment_id: int, body: str):
        if self.fail_comments:
            raise ForgeError("ticket transport unavailable")
        self.ticket_comments[comment_id] = body

    def add_labels(self, iid: int, labels: list[str]):
        if self.ticket:
            self.ticket.labels = list(dict.fromkeys([*self.ticket.labels, *labels]))

    def remove_labels(self, iid: int, labels: list[str]):
        if self.ticket:
            self.ticket.labels = [item for item in self.ticket.labels if item not in labels]

    def get_merge_request(self, ref):
        if self.mr and ref == self.mr.iid:
            return self.mr
        if self.mr and isinstance(ref, str) and self.branch_mr_exists:
            return self.mr
        return None

    def list_mr_comments(self, mr_iid: int):
        return [Comment(id=key, body=value) for key, value in self.mr_comments.items()]

    def pipeline_status(self, mr_iid: int) -> str:
        # Default "unknown" keeps every existing review test silent, which is
        # also what a repository with no CI configured produces.
        return self.pipeline

    def post_mr_comment(self, mr_iid: int, body: str):
        if self.fail_comments:
            raise ForgeError("MR transport unavailable")
        self.next_comment += 1
        self.mr_comments[self.next_comment] = body
        return self.next_comment

    def edit_mr_comment(self, mr_iid: int, comment_id: int, body: str):
        if self.fail_comments:
            raise ForgeError("MR transport unavailable")
        self.mr_comments[comment_id] = body

    def remove_mr_labels(self, mr_iid: int, labels: list[str]):
        if self.fail_mr_label_removal:
            raise ForgeError("MR label transport unavailable")
        if self.mr:
            self.mr.labels = [item for item in self.mr.labels if item not in labels]

    def open_merge_request(self, source, target, title, body, **kwargs):
        self.opened.append({
            "source": source, "target": target, "title": title, "body": body, **kwargs,
        })
        self.branch_mr_exists = True
        return self.mr.web_url


class FakeWorktrees:
    """@brief Git/worktree fake with mutable target and candidate fingerprints."""

    repo_path = Path("C:/repo")

    def __init__(self) -> None:
        self.target = "a" * 40
        self.fingerprint = "b" * 64
        self.product_fingerprint = "c" * 64
        self.progress_fingerprint = "initial"
        self.checkpoints: list[str] = []
        self.pushes: list[str] = []
        self.removed: list[str] = []
        self.dirs: list[Path] = []
        self.dirty = False

    def exists(self, run_id):
        return True

    def path_for(self, run_id):
        return Path("C:/work") / run_id

    def create(self, run_id, branch, base_ref):
        return self.path_for(run_id)

    def fetch(self):
        return None

    def merge(self, run_id, ref):
        return CommandResult(exit_code=0)

    def merge_in_progress(self, run_id):
        return False

    def push(self, run_id, branch):
        self.pushes.append(branch)
        return CommandResult(exit_code=0)

    def is_dirty(self, run_id):
        return self.dirty

    def changed_files(self, run_id, base_ref):
        return 2

    def candidate_fingerprint(self, run_id, base_ref):
        return self.fingerprint

    def product_diff_fingerprint(self, run_id, base_ref):
        return self.product_fingerprint

    def worktree_progress_fingerprint(self, run_id):
        return self.progress_fingerprint

    def ref_head(self, ref):
        return self.target

    def commit_series(self, run_id, base_ref):
        return ["deadbeef checkpoint"]

    def commit_all_if_dirty(self, run_id, message):
        self.checkpoints.append(message)
        self.dirty = False
        return True

    def admin_dir_name(self, run_id):
        return run_id

    def list_dirs(self):
        return self.dirs

    def remove(self, run_id, **kwargs):
        self.removed.append(run_id)


class FakeContainers:
    """@brief Container lifecycle fake."""

    def __init__(self) -> None:
        self.stopped: list[str] = []
        self.interrupted: list[str] = []
        self.interrupt_event = Event()
        self.removed: list[str] = []
        self.cleanup_containers: list[str] = []
        self.cleanup_proxies: list[str] = []
        self.cleanup_networks: list[str] = []
        self.cleanup_calls: list[tuple[set[str], set[str]]] = []

    def ensure_volumes(self):
        return None

    def provision(self, *args, **kwargs):
        return "created"

    def verify_required_tools(self, *args, **kwargs):
        return None

    def exec(self, name, argv, **kwargs):
        return CommandResult(exit_code=0)

    def stop(self, name):
        self.stopped.append(name)

    def interrupt(self, name):
        self.interrupted.append(name)
        self.interrupt_event.set()

    def remove(self, name):
        self.removed.append(name)

    def list_containers(self, prefix):
        return []

    def cleanup_orphan_containers(self, prefix, targets, retained):
        self.cleanup_calls.append((set(targets), set(retained)))
        return list(self.cleanup_containers)

    def cleanup_egress_proxies(self, prefix, targets, retained):
        self.cleanup_calls.append((set(targets), set(retained)))
        return list(self.cleanup_proxies)

    def cleanup_egress_networks(self, targets, retained):
        self.cleanup_calls.append((set(targets), set(retained)))
        return list(self.cleanup_networks)


class FakeRuntime:
    """
    @brief   Stateful container-runtime double for cleanup: lists containers and
             networks with docker's substring name filter and removes exact
             names, so tests observe which resources survive.
    """

    def __init__(self, containers=(), networks=()) -> None:
        self.containers = set(containers)
        self.networks = set(networks)

    def __call__(self, argv, **kwargs):
        args = list(argv[1:])
        if args[:2] in (["ps", "--all"], ["network", "ls"]):
            needle = args[args.index("--filter") + 1].split("=", 1)[1]
            pool = self.containers if args[0] == "ps" else self.networks
            listing = "\n".join(sorted(name for name in pool if needle in name))
            return CommandResult(argv=list(argv), stdout=listing)
        if args[:2] == ["rm", "--force"]:
            self.containers.discard(args[2])
            return CommandResult(argv=list(argv))
        if args[:2] == ["network", "rm"]:
            self.networks.discard(args[2])
            return CommandResult(argv=list(argv))
        raise AssertionError(f"unexpected runtime call: {argv}")


class FakeExecutor:
    """@brief Fresh-session executor double with scripted stage results."""

    def __init__(self, *results: GateRun) -> None:
        self.results = deque(results)
        self.prompts: list[str] = []

    def run_gate(self, execute, worktree, io_dir, prompt, **kwargs):
        # Every gate is a FRESH executor session, so the launcher takes no
        # session argument and the conductor must never pass one.
        assert "session" not in kwargs
        self.prompts.append(prompt)
        if not self.results:
            return GateRun(exit_code=0)
        return self.results.popleft()


class FakeAegis:
    """@brief Typed-client fake returning scripted task journal snapshots."""

    def __init__(self, tasks: list[AegisTask], check: AegisCheck | None = None) -> None:
        self.tasks = deque(tasks)
        self.last = tasks[-1]
        self.check_result = check or passing_check()

    def task_status(self, task_id: str):
        if self.tasks:
            self.last = self.tasks.popleft()
        return self.last

    def check(self, *args, **kwargs):
        return self.check_result


# HELPER FUNCTIONS


def make_config(tmp_path: Path) -> Config:
    """@brief Return a directly injectable valid-enough configuration."""
    config = Config()
    config.agent.slug = "adore"
    config.agent.email = "adore@example.test"
    config.platform.kind = "github"
    config.platform.repo = "owner/repo"
    config.state.store_root = str(tmp_path / ".adore")
    config.delivery.target_branch = "main"
    config.delivery.reviewers = ["reviewer"]
    config.metrics.enabled = False
    return config


def make_engine(
    tmp_path: Path,
    *,
    forge: FakeForge | None = None,
    executor: FakeExecutor | None = None,
):
    """@brief Build the conductor and its fakes."""
    config = make_config(tmp_path)
    fake_forge = forge or FakeForge()
    worktrees = FakeWorktrees()
    containers = FakeContainers()
    fake_executor = executor or FakeExecutor()
    engine = Orchestrator(
        config,
        fake_forge,
        StateStore(config.state.store_root, "adore"),
        worktrees,
        containers,
        fake_executor,
        sleep=lambda _: None,
        log=lambda _: None,
    )
    return engine, fake_forge, worktrees, containers, fake_executor


def make_run(engine: Orchestrator, *, task_type="feature", path="full") -> RunState:
    """@brief Persist one active task-bound run and its ticket snapshot."""
    run = RunState(
        run_id="github-owner-repo-7",
        ticket_iid=7,
        active_task_id=TASK_ID,
        task_ids=[TASK_ID],
        aegis_type=task_type,
        aegis_path=path,
        branch="adore/github-owner-repo-7",
        base_ref="origin/main",
        worktree="C:/work/github-owner-repo-7",
        container="adore-run-github-owner-repo-7",
        content_hash=content_hash(
            engine.forge.ticket.title, engine.forge.ticket.description
        ),
        active_started_at=utc_now_iso(),
    )
    engine.store.save(run)
    ticket = engine.forge.ticket
    engine.store.save_ticket(run.run_id, {
        "title": ticket.title,
        "description": ticket.description,
        "labels": ticket.labels,
        "author": ticket.author,
        "web_url": ticket.web_url,
    })
    return run


def task(stage: str, *, path="full", task_type="feature") -> AegisTask:
    """@brief Return a validated task view for scripted conduction."""
    steps = {
        "frame": "1_frame.md", "specify": "2_specify.md", "design": "3_design.md",
        "build": "4_build.md", "validate": "5_validate.md",
        "deliver": "6_deliver.md", "done": "6_deliver.md",
    }
    return AegisTask(
        task_id=TASK_ID,
        title="Bounded change",
        file=f".agentic/tasks/{TASK_ID}.md",
        header={
            "stage": stage,
            "type": task_type,
            "path": path,
            "requirements": "REQ-FUNC-1",
            "branch": "adore/github-owner-repo-7",
            "base": "abc",
            "opened": "now",
        },
        stage=stage,
        step_file=steps[stage],
        done=stage == "done",
        checklist=(),
        log=(),
    )


def passing_check() -> AegisCheck:
    """@brief Return strict evidence with one successfully executed command."""
    return AegisCheck(
        exit_code=0,
        task_id=TASK_ID,
        findings=(),
        errors=0,
        warnings=0,
        notes=0,
        strict_enabled=True,
        promoted_warnings=0,
        passed=True,
        runs=(AegisCommandRun("test", "ok", 0, 1.0),),
        raw={},
    )


def sequence(*stages: str, path="full", task_type="feature") -> list[AegisTask]:
    """@brief Expand stage transitions into before/after status reads."""
    result: list[AegisTask] = []
    for current, following in zip(stages, stages[1:], strict=False):
        result.extend([
            task(current, path=path, task_type=task_type),
            task(following, path=path, task_type=task_type),
        ])
    # Strict verification and the next loop each read deliver once more.
    result.extend([
        task(stages[-1], path=path, task_type=task_type),
        task(stages[-1], path=path, task_type=task_type),
    ])
    return result


# PUBLIC API


@pytest.mark.parametrize(
    ("stages", "path", "task_type"),
    [
        (("frame", "specify", "design", "build", "validate", "deliver"),
         "full", "feature"),
        (("frame", "build", "validate", "deliver"), "quick", "fix"),
    ],
)
def test_clean_full_and_quick_paths_stop_for_fresh_approval(
    tmp_path: Path, stages, path: str, task_type: str,
) -> None:
    """@brief Both documented paths checkpoint locally and stop before push."""
    engine, forge, worktrees, containers, executor = make_engine(tmp_path)
    run = make_run(engine, task_type=task_type, path=path)
    client = FakeAegis(sequence(*stages, path=path, task_type=task_type))

    engine._conduct_task(run, forge.ticket, client, "")

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "awaiting-approval"
    assert saved.stage == "deliver"
    assert saved.validation_evidence["passed"] is True
    observations = [event for event in engine.store.read_journal(run.run_id)
                    if event.get("event") == "usage-observation"]
    assert len(observations) == len(executor.prompts)
    assert len({event["event_id"] for event in observations}) == len(observations)
    assert all(event["schema"] == 1 and event["token_status"] == "unavailable"
               and event["cost_status"] == "unavailable" for event in observations)
    assert saved.candidate_fingerprint == worktrees.fingerprint
    assert saved.validation_evidence["deviations"] == []
    assert "Deviations recorded: 0" in forge.ticket_comments[saved.approval_comment_id]
    assert len(executor.prompts) == len(stages) - 1
    assert not forge.opened
    assert containers.stopped
    stage_commits = [item for item in worktrees.checkpoints if "ADORE checkpoint" in item]
    assert len(stage_commits) == len(stages) - 1


def test_launch_telemetry_distinguishes_observed_and_disabled_capture(tmp_path):
    """@brief Completed gates record coverage without double-counting usage."""
    first = GateRun(exit_code=0, tokens_in=10, tokens_out=2,
                    cache_read_tokens=3, cache_write_tokens=1)
    engine, forge, _worktrees, _containers, _executor = make_engine(
        tmp_path / "observed", executor=FakeExecutor(first))
    run = make_run(engine)
    engine._conduct_task(run, forge.ticket,
                         FakeAegis(sequence("frame", "build", "validate", "deliver")), "")
    journal = engine.store.read_journal(run.run_id)
    observed = [event for event in journal if event.get("event") == "usage-observation"]
    usage = [event for event in journal if event.get("event") == "usage"]
    assert observed[0]["token_status"] == "reported"
    assert observed[0]["cost_status"] == "unavailable"
    assert observed[0]["tokens_in"] == 10
    assert observed[0]["cache_read_tokens"] == 3
    assert observed[0]["input_includes_cache"] is True
    assert len(usage) == 1 and usage[0]["tokens_in"] == 10
    assert usage[0]["cache_write_tokens"] == 1
    assert usage[0]["event_id"] == observed[0]["event_id"]
    assert usage[0]["attempt"] == observed[0]["attempt"]

    disabled, forge, _worktrees, _containers, _executor = make_engine(
        tmp_path / "disabled", executor=FakeExecutor(first))
    disabled.config.metrics.capture_tokens = False
    run = make_run(disabled)
    disabled._conduct_task(run, forge.ticket,
                           FakeAegis(sequence("frame", "build", "validate", "deliver")), "")
    journal = disabled.store.read_journal(run.run_id)
    observed = [event for event in journal if event.get("event") == "usage-observation"]
    assert observed[0]["token_status"] == "disabled"
    assert observed[0]["cost_status"] == "disabled"
    assert observed[0]["tokens_in"] is None
    assert not any(event.get("event") == "usage" for event in journal)


def test_launch_telemetry_preserves_reported_zero(tmp_path):
    """@brief Zero measured tokens remain reported in the durable journal."""
    result = GateRun(exit_code=0, tokens_reported=True)
    engine, forge, _worktrees, _containers, _executor = make_engine(
        tmp_path, executor=FakeExecutor(result))
    run = make_run(engine)
    engine._conduct_task(run, forge.ticket,
                         FakeAegis(sequence("frame", "build", "validate", "deliver")), "")
    observations = [event for event in engine.store.read_journal(run.run_id)
                    if event.get("event") == "usage-observation"]
    assert observations[0]["token_status"] == "reported"
    assert observations[0]["tokens_in"] == 0
    assert observations[0]["tokens_out"] == 0


def test_partial_telemetry_does_not_write_numeric_usage(tmp_path):
    """@brief Explicit incomplete telemetry stays unknown in projections."""
    result = GateRun(exit_code=0, tokens_in=4, tokens_reported=False)
    engine, forge, _worktrees, _containers, _executor = make_engine(
        tmp_path, executor=FakeExecutor(result))
    run = make_run(engine)
    engine._conduct_task(run, forge.ticket,
                         FakeAegis(sequence("frame", "build", "validate", "deliver")), "")
    journal = engine.store.read_journal(run.run_id)
    observations = [event for event in journal
                    if event.get("event") == "usage-observation"]
    assert observations[0]["token_status"] == "unavailable"
    assert observations[0]["tokens_in"] is None
    assert not any(event.get("event") == "usage" for event in journal)


def test_requested_cancel_stops_before_next_gate(tmp_path: Path) -> None:
    """@brief Durable cancellation takes precedence over another stage attempt."""
    engine, forge, _, containers, executor = make_engine(tmp_path)
    run = make_run(engine)
    assert engine.store.request_cancel(run.run_id)

    engine._conduct_task(run, forge.ticket, FakeAegis([task("frame")]), "")

    assert engine.store.load(run.run_id).lifecycle == "cancelled"
    assert not engine.store.cancel_requested(run.run_id)
    assert executor.prompts == []
    assert containers.removed


def test_requested_cancel_interrupts_active_gate(tmp_path: Path) -> None:
    """@brief A running executor gate is interrupted and finalized as cancelled."""
    engine, forge, _, containers, _ = make_engine(tmp_path)
    run = make_run(engine)

    class CancellingExecutor(FakeExecutor):
        def run_gate(self, execute, worktree, io_dir, prompt, **kwargs):
            engine.store.request_cancel(run.run_id)
            assert containers.interrupt_event.wait(2)
            return GateRun(exit_code=1, stderr="container stopped")

    engine.executor = CancellingExecutor()
    engine._conduct_task(run, forge.ticket, FakeAegis([task("frame")]), "")

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "cancelled"
    assert saved.failure_history == []
    assert containers.interrupted == [run.container]


def test_cancel_marker_survives_worker_crash_and_reconciles(tmp_path: Path) -> None:
    """@brief A later conductor poll completes an authorized durable cancel."""
    engine, _, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    engine.store.request_cancel(run.run_id)
    engine.store.pause()

    engine.poll_once()

    assert engine.store.load(run.run_id).lifecycle == "cancelled"
    assert not engine.store.cancel_requested(run.run_id)


def test_corrupt_cancel_marker_stops_reconciliation(tmp_path: Path) -> None:
    """@brief A damaged cancellation request cannot be guessed or discarded."""
    engine, _, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    (engine.store.run_dir(run.run_id) / "cancel.request").write_text(
        "junk", encoding="utf-8"
    )
    engine.store.pause()

    with pytest.raises(StateError):
        engine.poll_once()
    assert engine.store.load(run.run_id).lifecycle == "working"


def test_cancel_before_publication_does_not_push_or_open_draft(tmp_path: Path) -> None:
    """@brief A waiting cancellation wins before publication side effects."""
    engine, forge, worktrees, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = "awaiting-approval"
    engine.store.save(run)
    engine.store.request_cancel(run.run_id)

    engine._publish(run, forge.ticket)

    assert engine.store.load(run.run_id).lifecycle == "cancelled"
    assert worktrees.pushes == []
    assert forge.opened == []


def test_approval_presentation_lists_recorded_deviations(tmp_path: Path) -> None:
    """@brief Journal deviations reach the approver as a count plus full text."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine, task_type="fix", path="quick")
    stages = sequence("frame", "build", "validate", "deliver", path="quick", task_type="fix")
    stages[-1] = replace(stages[-1], log=(
        "2026-09-13 build: DEVIATION build - accepted one check warning",
        "2026-09-13 build: the DEVIATION policy is one line, said aloud",
    ))

    engine._conduct_task(run, forge.ticket, FakeAegis(stages), "")

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "awaiting-approval"
    assert saved.validation_evidence["deviations"] == ["build - accepted one check warning"]
    body = forge.ticket_comments[saved.approval_comment_id]
    assert "Deviations recorded: 1" in body
    assert "- build - accepted one check warning" in body
    assert "policy is one line" not in body


def test_two_failures_then_success_resets_counter_and_questions_do_not_consume_it(
    tmp_path: Path,
) -> None:
    """@brief Attempt failures are stage-scoped; a question parks at zero."""
    executor = FakeExecutor(
        GateRun(exit_code=2, stderr="first"),
        GateRun(exit_code=2, stderr="second"),
        GateRun(exit_code=0),
        GateRun(exit_code=0, has_questions=True, questions="Which API?"),
    )
    engine, forge, _, _, _ = make_engine(tmp_path, executor=executor)
    run = make_run(engine, task_type="fix", path="quick")
    client = FakeAegis([
        task("frame", path="quick", task_type="fix"),
        task("frame", path="quick", task_type="fix"),
        task("frame", path="quick", task_type="fix"),
        task("build", path="quick", task_type="fix"),
        task("build", path="quick", task_type="fix"),
    ])

    engine._conduct_task(run, forge.ticket, client, "")

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "parked-clarification"
    assert saved.stage_failures == 0
    assert len(saved.failure_history) == 2
    assert saved.clarification_rounds == 1


def test_exact_third_failed_attempt_aborts_without_fourth_launch(tmp_path: Path) -> None:
    """@brief Default 3 means three attempts total, not three retries."""
    executor = FakeExecutor(*[
        GateRun(exit_code=2, stderr=f"failure {index}") for index in range(3)
    ])
    engine, forge, _, containers, _ = make_engine(tmp_path, executor=executor)
    run = make_run(engine)
    client = FakeAegis([task("frame") for _ in range(3)])

    engine._conduct_task(run, forge.ticket, client, "")

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "failed"
    assert saved.stage_failures == 3
    assert len(executor.prompts) == 3
    assert "attempt 3/3" in saved.outcome
    assert containers.stopped
    assert len(forge.ticket_comments) >= 2  # edited incident + separate terminal


@pytest.mark.parametrize(
    ("gate", "expected"),
    [
        (
            GateRun(
                exit_code=124,
                stderr="executor stopped for an unrelated reason",
                timed_out=True,
            ),
            "EXECUTOR_TIMEOUT",
        ),
        (
            GateRun(
                exit_code=2,
                stderr="configuration mentions timeout but execution failed",
                timed_out=False,
            ),
            "EXECUTOR_EXIT",
        ),
    ],
)
def test_executor_timeout_classification_uses_typed_flag(
    tmp_path: Path, gate: GateRun, expected: str,
) -> None:
    """@brief Timeout classification never guesses from exit code or stderr text."""
    engine, forge, _, _, _ = make_engine(
        tmp_path, executor=FakeExecutor(gate)
    )
    engine.config.recovery.max_stage_failures = 1
    run = make_run(engine)

    engine._conduct_task(run, forge.ticket, FakeAegis([task("frame")]), "")

    saved = engine.store.load(run.run_id)
    assert saved.failure_history[-1]["code"] == expected


def test_aegis_timeout_retries_inside_the_same_conductor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A permitted timeout immediately reaches a second AEGIS attempt."""
    executor = FakeExecutor(
        GateRun(exit_code=0, has_questions=True, questions="Choose an API")
    )
    engine, forge, _, _, _ = make_engine(tmp_path, executor=executor)
    run = make_run(engine)
    clients: list[TimeoutThenTaskClient] = []

    class TimeoutThenTaskClient:
        """@brief Time out one status read, then expose a conductible task."""

        def __init__(self, *args, **kwargs) -> None:
            self.status_reads = 0
            clients.append(self)

        def probe(self) -> None:
            return None

        def task_status(self, task_id: str) -> AegisTask:
            self.status_reads += 1
            if self.status_reads == 1:
                raise AegisTimeoutError(f"status {task_id} timed out")
            return task("frame")

    monkeypatch.setattr(orchestrator_module, "AegisClient", TimeoutThenTaskClient)

    engine._conduct(run, forge.ticket)

    saved = engine.store.load(run.run_id)
    assert clients[0].status_reads == 2
    assert saved.lifecycle == "parked-clarification"
    assert saved.failure_history[-1]["code"] == "AEGIS_TIMEOUT"
    assert len(executor.prompts) == 1
    assert engine._in_flight_run_id == ""


def test_aegis_timeout_at_attempt_limit_is_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A timeout at the configured limit terminates as AEGIS_TIMEOUT."""
    engine, forge, _, containers, _ = make_engine(tmp_path)
    engine.config.recovery.max_stage_failures = 1
    run = make_run(engine)

    class TimeoutClient:
        """@brief AEGIS double whose active-task status always times out."""

        def __init__(self, *args, **kwargs) -> None:
            pass

        def probe(self) -> None:
            return None

        def task_status(self, task_id: str) -> AegisTask:
            raise AegisTimeoutError(f"status {task_id} timed out")

    monkeypatch.setattr(orchestrator_module, "AegisClient", TimeoutClient)

    engine._conduct(run, forge.ticket)

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "failed"
    assert saved.failure_history[-1]["code"] == "AEGIS_TIMEOUT"
    assert "timed out" in saved.failure_history[-1]["evidence"]
    assert containers.stopped


@pytest.mark.parametrize(
    ("timeout", "before", "after"),
    [
        ("72H", "2026-08-03T23:59:59Z", "2026-08-04T00:00:00Z"),
        (3600, "2026-08-01T00:59:59Z", "2026-08-01T01:00:00Z"),
    ],
)
def test_clarification_uses_the_validated_duration_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    timeout: str | int,
    before: str,
    after: str,
) -> None:
    """@brief Uppercase and numeric valid durations expire only at their bound."""
    engine, _, _, _, _ = make_engine(tmp_path)
    engine.config.clarification.answer_timeout = timeout  # type: ignore[assignment]
    run = make_run(engine)
    run.lifecycle = "parked-clarification"
    run.parked_at = "2026-08-01T00:00:00Z"
    engine.store.save(run)
    summary = {"resumed": 0, "timed_out": 0}

    monkeypatch.setattr(orchestrator_module, "utc_now_iso", lambda: before)
    engine._reconcile_clarification(run, summary)
    assert engine.store.load(run.run_id).lifecycle == "parked-clarification"
    assert summary["timed_out"] == 0

    parked = engine.store.load(run.run_id)
    monkeypatch.setattr(orchestrator_module, "utc_now_iso", lambda: after)
    engine._reconcile_clarification(parked, summary)
    assert engine.store.load(run.run_id).lifecycle == "failed"
    assert summary["timed_out"] == 1


def test_post_gate_questions_are_read_once_and_park_with_text(tmp_path: Path) -> None:
    """@brief The fallback handoff consumes one file without losing its text."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    run.worktree = str(worktree)
    engine.store.save(run)
    questions = worktree / engine.questions_file
    questions.write_text("Which API should be used?\n", encoding="utf-8")

    engine._conduct_task(
        run,
        forge.ticket,
        FakeAegis([task("frame"), task("frame")]),
        "",
    )

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "parked-clarification"
    assert any("Which API should be used?" in body for body in forge.ticket_comments.values())
    assert not questions.exists()


def test_park_removes_persisted_questions_handoff(tmp_path: Path) -> None:
    """@brief A posted and journaled question cannot enter a later checkpoint."""
    engine, _, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    run.worktree = str(worktree)
    engine.store.save(run)
    questions = worktree / engine.questions_file
    questions.write_text("Choose a backend", encoding="utf-8")

    engine._park(run, "Choose a backend")

    assert engine.store.load(run.run_id).lifecycle == "parked-clarification"
    assert engine.store.read_journal(run.run_id)[-1]["questions"] == "Choose a backend"
    assert not questions.exists()


@pytest.mark.parametrize(
    "lifecycle", ["parked-clarification", "awaiting-approval", "in-review"]
)
def test_closed_source_ticket_cancels_reconciled_run(
    tmp_path: Path, lifecycle: str
) -> None:
    """@brief Human ticket closure cancels every waiting reconciliation state."""
    engine, forge, worktrees, containers, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = lifecycle
    if lifecycle == "in-review":
        run.stage = "done"
        run.mr_iid = forge.mr.iid
        run.mr_url = forge.mr.web_url
    engine.store.save(run)
    forge.ticket.state = "closed"

    if lifecycle == "parked-clarification":
        engine._reconcile_clarification(run, {"resumed": 0, "timed_out": 0})
    elif lifecycle == "awaiting-approval":
        engine._reconcile_approval(run, {"approved": 0})
    else:
        engine._reconcile_review(run, {"done": 0, "revised": 0})

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "cancelled"
    assert saved.outcome == "ticket closed"
    assert containers.removed == [run.container]
    assert worktrees.removed == [run.run_id]


def test_clarification_resume_refreshes_changed_ticket_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief A resumed executor sees a visible note and the fresh ticket content."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = "parked-clarification"
    run.parked_at = utc_now_iso()
    engine.store.save(run)
    forge.ticket.description = "## Acceptance Criteria\n- [ ] Updated behavior"
    forge.ticket.labels.append("agent-answered")
    forge.ticket_comments[200] = "Use the updated behavior."
    threads: list[str] = []
    monkeypatch.setattr(
        engine,
        "_conduct",
        lambda state, ticket, thread="": threads.append(thread),
    )

    engine._reconcile_clarification(run, {"resumed": 0, "timed_out": 0})

    saved = engine.store.load(run.run_id)
    snapshot = engine.store.load_ticket(run.run_id)
    refresh = [
        event for event in engine.store.read_journal(run.run_id)
        if event["event"] == "ticket-content-refreshed"
    ]
    assert saved.content_hash == content_hash(forge.ticket.title, forge.ticket.description)
    assert snapshot["description"] == forge.ticket.description
    assert "ticket content changed since pickup" in threads[0]
    assert refresh[-1]["context"] == "clarification-resume"


def test_clarification_resume_rearms_only_the_active_wall_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief An answer after a long human wait starts a fresh active phase."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    engine.config.budgets.max_wall_clock_seconds = 60
    run = make_run(engine)
    run.lifecycle = "parked-clarification"
    run.parked_at = "2026-08-15T11:59:00Z"
    run.active_started_at = "2026-08-15T00:00:00Z"
    run.iterations = 2
    run.stage_failures = 1
    engine.store.save(run)
    forge.ticket.labels.append("agent-answered")
    forge.ticket_comments[200] = "Resume with the documented default."
    observed: list[tuple[str, int, int]] = []

    def conduct(state: RunState, ticket: Ticket, thread: str = "") -> None:
        observed.append((engine._budget_exceeded(state), state.iterations, state.stage_failures))

    monkeypatch.setattr(orchestrator_module, "utc_now_iso", lambda: "2026-08-15T12:00:00Z")
    monkeypatch.setattr(engine, "_conduct", conduct)

    summary = engine.poll_once()

    saved = engine.store.load(run.run_id)
    assert summary["resumed"] == 1
    assert observed == [("", 2, 1)]
    assert saved.active_started_at == "2026-08-15T12:00:00Z"


def test_approval_observation_refreshes_ticket_without_invalidating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief Ticket text drift is journaled but does not revoke a valid candidate."""
    engine, forge, worktrees, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = "awaiting-approval"
    run.stage = "deliver"
    run.validation_evidence = engine._validation_payload(passing_check())
    run.candidate_fingerprint = worktrees.fingerprint
    run.candidate_base_ref = worktrees.target
    run.approval_label_removed = True
    run.approval_presented_at = utc_now_iso()
    engine.store.save(run)
    forge.ticket.title = "Bounded change with clarified scope"
    forge.ticket.labels.append("agent-approved")
    published: list[str] = []
    monkeypatch.setattr(
        engine, "_publish", lambda state, ticket: published.append(ticket.title)
    )

    engine._reconcile_approval(run, {"approved": 0})

    saved = engine.store.load(run.run_id)
    snapshot = engine.store.load_ticket(run.run_id)
    refresh = [
        event for event in engine.store.read_journal(run.run_id)
        if event["event"] == "ticket-content-refreshed"
    ]
    assert published == [forge.ticket.title]
    assert saved.content_hash == content_hash(forge.ticket.title, forge.ticket.description)
    assert snapshot["title"] == forge.ticket.title
    assert refresh[-1]["context"] == "approval"


def test_many_strict_findings_count_as_one_failed_invocation(tmp_path: Path) -> None:
    """@brief Finding cardinality never consumes more than one attempt."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    findings = tuple(
        AegisFinding("ERROR", f"check-{index}", "x.py", "failed")
        for index in range(10)
    )
    failed = replace(
        passing_check(),
        exit_code=1,
        findings=findings,
        errors=10,
        passed=False,
        runs=(AegisCommandRun("test", "failed", 1, 1.0),),
    )
    client = FakeAegis([task("deliver")], failed)
    engine._launch_stage = lambda *args, **kwargs: GateRun(  # type: ignore[method-assign]
        exit_code=0, has_questions=True, questions="Need policy decision"
    )

    assert not engine._strict_verification(run, client)
    saved = engine.store.load(run.run_id)
    assert saved.stage_failures == 1
    assert len(saved.failure_history) == 1


def test_incident_is_edited_and_terminal_failure_is_separate(tmp_path: Path) -> None:
    """@brief Recoverable failures share one incident identity; abort posts another."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    assert engine._stage_failure(run, "E_ONE", "one")
    first_id = engine.store.load(run.run_id).incident_comment_id
    assert engine._stage_failure(run, "E_TWO", "two")
    assert engine.store.load(run.run_id).incident_comment_id == first_id
    assert not engine._stage_failure(run, "E_THREE", "three")
    assert first_id in forge.ticket_comments
    assert "attempt 3/3" in forge.ticket_comments[first_id]
    assert any("failed loudly" in body for cid, body in forge.ticket_comments.items()
               if cid != first_id)


def test_notification_outage_stops_work_and_replay_is_idempotent(tmp_path: Path) -> None:
    """@brief Required write failure retains an outbox and blocks operator retry."""
    forge = FakeForge()
    forge.fail_comments = True
    engine, _, _, containers, _ = make_engine(tmp_path, forge=forge)
    run = make_run(engine)

    assert not engine._stage_failure(run, "BROKEN", "token=secret")
    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "failed" and len(saved.notification_outbox) == 1
    assert "secret" not in saved.notification_outbox[0]["body"]
    assert not engine.retry(run.run_id)
    forge.fail_comments = False
    saved.notification_outbox[0]["next_attempt_at"] = ""
    engine.store.save(saved)
    assert engine._retry_outbox(saved) == 1
    assert engine.store.load(run.run_id).notification_outbox == []
    assert containers.stopped


def test_deleted_mr_notification_falls_back_to_source_ticket(tmp_path: Path) -> None:
    """@brief A confirmed missing MR routes a pending incident to its ticket."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.mr_iid = 9
    forge.mr = None
    engine.store.save(run)
    body = "problem\n" + engine.identity.make_marker(run.run_id, "incident")
    comment_id = engine._required_comment(run, "incident", body, target="mr")
    assert comment_id in forge.ticket_comments
    assert not forge.mr_comments


def test_outbox_crash_replay_finds_existing_marker_without_duplicate(tmp_path: Path) -> None:
    """@brief A post-success/state-save crash is idempotent by notification marker."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    notification_id = "abc123"
    body = (
        "already delivered\n"
        + engine.identity.make_marker(
            run.run_id, "incident", notification=notification_id
        )
    )
    forge.ticket_comments[321] = body
    run.notification_outbox = [{
        "id": notification_id,
        "kind": "incident",
        "surface": "ticket",
        "resource": 7,
        "edit_id": None,
        "body": body,
        "attempts": 1,
        "next_attempt_at": "",
        "last_error": "crash",
    }]
    engine.store.save(run)
    assert engine._retry_outbox(run) == 1
    assert list(forge.ticket_comments) == [321]


def test_approval_rejects_stale_label_and_invalidates_on_target_drift(tmp_path: Path) -> None:
    """@brief Removal/re-add and both fingerprint dimensions bind approval."""
    forge = FakeForge()
    forge.ticket.labels.append("agent-approved")
    engine, _, worktrees, _, _ = make_engine(tmp_path, forge=forge)
    run = make_run(engine)
    run.stage = "deliver"
    run.validation_evidence = engine._validation_payload(passing_check())
    run.candidate_fingerprint = worktrees.fingerprint
    run.candidate_base_ref = worktrees.target
    engine.store.save(run)

    engine._present_for_approval(run, forge.ticket)
    saved = engine.store.load(run.run_id)
    assert "agent-approved" not in forge.ticket.labels
    assert not engine._approval_ready(saved, forge.ticket)
    forge.ticket.labels.append("agent-approved")
    assert engine._approval_ready(saved, forge.ticket)
    worktrees.target = "d" * 40
    assert not engine._approval_ready(saved, forge.ticket)
    assert "agent-approved" not in forge.ticket.labels


def test_approval_invalidation_rearms_clock_and_stage_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief Candidate drift begins clean re-conduction after a long approval wait."""
    engine, forge, worktrees, _, _ = make_engine(tmp_path)
    engine.config.budgets.max_wall_clock_seconds = 60
    run = make_run(engine)
    run.lifecycle = "awaiting-approval"
    run.stage = "deliver"
    run.validation_evidence = engine._validation_payload(passing_check())
    run.candidate_fingerprint = worktrees.fingerprint
    run.candidate_base_ref = worktrees.target
    run.approval_label_removed = True
    run.approval_presented_at = "2026-08-15T00:00:00Z"
    run.active_started_at = "2026-08-15T00:00:00Z"
    run.iterations = 2
    run.stage_failures = 3
    engine.store.save(run)
    forge.ticket.labels.append("agent-approved")
    worktrees.target = "d" * 40
    observed: list[tuple[str, int, int]] = []

    def conduct(state: RunState, ticket: Ticket, thread: str = "") -> None:
        observed.append((engine._budget_exceeded(state), state.iterations, state.stage_failures))

    monkeypatch.setattr(orchestrator_module, "utc_now_iso", lambda: "2026-08-15T12:00:00Z")
    monkeypatch.setattr(engine, "_conduct", conduct)

    summary = engine.poll_once()

    saved = engine.store.load(run.run_id)
    assert summary["approved"] == 0
    assert observed == [("", 2, 0)]
    assert saved.active_started_at == "2026-08-15T12:00:00Z"
    assert "agent-approved" not in forge.ticket.labels


def test_retry_rechecks_missing_approval_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief A removed approval label returns retry to one normal conduction."""
    engine, forge, worktrees, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = "failed"
    run.stage = "deliver"
    run.outcome = "PUSH_FAILED: unavailable"
    run.validation_evidence = engine._validation_payload(passing_check())
    run.candidate_fingerprint = worktrees.fingerprint
    run.candidate_base_ref = worktrees.target
    run.approval_label_removed = True
    run.approval_presented_at = utc_now_iso()
    engine.store.save(run)
    approval_checks: list[int] = []
    conducted: list[str] = []
    published: list[str] = []

    def approval_ready(state: RunState, ticket: Ticket) -> bool:
        approval_checks.append(ticket.iid)
        return False

    monkeypatch.setattr(engine, "_approval_ready", approval_ready)
    monkeypatch.setattr(
        engine,
        "_conduct",
        lambda state, ticket, thread="": conducted.append(state.run_id),
    )
    monkeypatch.setattr(
        engine, "_publish", lambda state, ticket: published.append(state.run_id)
    )

    assert engine.retry(run.run_id)

    saved = engine.store.load(run.run_id)
    assert approval_checks == [forge.ticket.iid]
    assert conducted == [run.run_id]
    assert published == []
    assert saved.approval_presented_at == ""


def test_retry_drift_reconducts_only_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief Freshness invalidation owns its re-conduction without an outer duplicate."""
    engine, forge, worktrees, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = "failed"
    run.stage = "deliver"
    run.outcome = "PUSH_FAILED: unavailable"
    run.validation_evidence = engine._validation_payload(passing_check())
    run.candidate_fingerprint = worktrees.fingerprint
    run.candidate_base_ref = worktrees.target
    run.approval_label_removed = True
    run.approval_presented_at = utc_now_iso()
    engine.store.save(run)
    forge.ticket.labels.append("agent-approved")
    worktrees.target = "d" * 40
    conducted: list[str] = []
    monkeypatch.setattr(
        engine,
        "_conduct",
        lambda state, ticket, thread="": conducted.append(state.run_id),
    )

    assert engine.retry(run.run_id)

    assert conducted == [run.run_id]
    assert "agent-approved" not in forge.ticket.labels


def test_executor_prompt_forbids_remote_and_uses_quick_only_as_hint(tmp_path: Path) -> None:
    """@brief Frame autonomy never gives the executor publication authority."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    forge.ticket.labels.append("agent-quick")
    run = make_run(engine, task_type="fix", path="quick")
    prompt = engine._stage_prompt(
        run, forge.ticket, task("frame", path="quick", task_type="fix"), "", ""
    )
    assert "autopilot-to-deliver" in prompt
    assert "quick-path hint" in prompt
    assert "Never commit, push, open or merge" in prompt
    assert "python .agentic/aegis.py" in prompt


def test_executor_prompt_forbids_child_task_journals(tmp_path: Path) -> None:
    """@brief A conducted run pins one journal; AEGIS 0.9.0 children stay out."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    prompt = engine._stage_prompt(run, forge.ticket, task("build"), "", "")
    assert "task --parent" in prompt
    assert "child task journal" in prompt


def test_executor_prompt_declares_autopilot_on_every_stage(tmp_path: Path) -> None:
    """
    @brief   Every stage prompt overrides the AEGIS checkpoint default.
    @details AEGIS 0.13 checkpoint mode stops before each stage transition,
             which ADORE would read as NO_STAGE_PROGRESS. The explicit
             autopilot instruction is the per-task override AEGIS defines.
    """
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    for stage in ("frame", "specify", "design", "build", "validate", "deliver"):
        prompt = engine._stage_prompt(run, forge.ticket, task(stage), "", "")
        assert "autopilot-to-deliver" in prompt
        assert "interaction: autopilot" in prompt
        assert "never pause to present" in prompt


def test_executor_prompt_does_not_contradict_itself_about_stopping(
    tmp_path: Path,
) -> None:
    """
    @brief   The autopilot override and the one-stage rule must not read as
             opposites.
    @details The override was added for AEGIS 0.13's checkpoint default, and it
             once said "never stop at a stage-boundary checkpoint" while the
             closing paragraph said "stop after the current stage". A model
             resolving that in favour of the louder, earlier instruction runs
             the whole task in one session, which costs ADORE its per-stage
             checkpoints, error budget and failure-context handback (live
             finding 2026-09-18: two of three GitHub launches). Autopilot must
             therefore speak only about WHO decides, never about how far to go.
    """
    engine, forge, _, _, _ = make_engine(tmp_path)
    prompt = engine._stage_prompt(make_run(engine), forge.ticket, task("frame"), "", "")
    autopilot, _, rest = prompt.partition("autopilot-to-deliver")
    clause = rest.split("\n\n")[0]
    assert "never stop" not in clause.lower()
    assert "pause" in clause.lower()          # it is about human pauses only
    assert "Do exactly ONE stage in this session" in prompt
    assert "end the session" in prompt


def test_approved_publication_opens_draft_and_pushes_close_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Publication is ADORE-owned, draft-only and requires task done."""
    engine, forge, worktrees, _, executor = make_engine(
        tmp_path, executor=FakeExecutor(GateRun(0), GateRun(0))
    )
    run = make_run(engine)
    run.stage = "deliver"
    run.lifecycle = "awaiting-approval"
    run.validation_evidence = engine._validation_payload(passing_check())
    run.candidate_fingerprint = worktrees.fingerprint
    run.candidate_base_ref = worktrees.target
    run.approval_label_removed = True
    run.approval_presented_at = utc_now_iso()
    engine.store.save(run)

    class PublishClient:
        """@brief Script delivery/task completion for the publication boundary."""

        statuses = deque([task("deliver"), task("deliver"), task("deliver"), task("done")])

        def __init__(self, *args, **kwargs):
            pass

        def probe(self):
            return None

        def task_status(self, task_id):
            return self.statuses.popleft()

        def report(self, task_id):
            return None

        def evolution(self, task_id):
            return {}

    monkeypatch.setattr(orchestrator_module, "AegisClient", PublishClient)

    engine._publish(run, forge.ticket)

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "in-review" and saved.stage == "done"
    assert forge.opened and forge.opened[0]["draft"] is True
    assert len(worktrees.pushes) == 2
    assert len(executor.prompts) == 2


def test_publication_adopts_existing_open_mr_before_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief Crash recovery adopts a branch MR and never attempts a duplicate."""
    engine, forge, worktrees, _, _ = make_engine(
        tmp_path, executor=FakeExecutor(GateRun(0), GateRun(0))
    )
    forge.branch_mr_exists = True
    run = make_run(engine)
    run.stage = "deliver"
    run.lifecycle = "awaiting-approval"
    run.validation_evidence = engine._validation_payload(passing_check())
    run.candidate_fingerprint = worktrees.fingerprint
    run.candidate_base_ref = worktrees.target
    run.approval_label_removed = True
    run.approval_presented_at = utc_now_iso()
    engine.store.save(run)

    class AdoptClient:
        """@brief Script delivery completion after an existing MR is adopted."""

        statuses = deque([task("deliver"), task("deliver"), task("deliver"), task("done")])

        def __init__(self, *args, **kwargs):
            pass

        def probe(self):
            return None

        def task_status(self, task_id):
            return self.statuses.popleft()

        def report(self, task_id):
            return None

        def evolution(self, task_id):
            return {}

    monkeypatch.setattr(orchestrator_module, "AegisClient", AdoptClient)

    engine._publish(run, forge.ticket)

    saved = engine.store.load(run.run_id)
    adopted = [
        event for event in engine.store.read_journal(run.run_id)
        if event["event"] == "mr-adopted"
    ]
    assert saved.mr_iid == forge.mr.iid
    assert saved.mr_url == forge.mr.web_url
    assert saved.lifecycle == "in-review"
    assert forge.opened == []
    assert len(worktrees.pushes) == 2
    assert adopted[-1]["iid"] == forge.mr.iid


def test_publication_fails_closed_on_malformed_existing_mr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief Missing branch-MR identity blocks creation instead of risking a duplicate."""
    engine, forge, worktrees, _, _ = make_engine(
        tmp_path, executor=FakeExecutor(GateRun(0))
    )
    forge.branch_mr_exists = True
    forge.mr.web_url = ""
    run = make_run(engine)
    run.stage = "deliver"
    run.validation_evidence = engine._validation_payload(passing_check())
    run.candidate_fingerprint = worktrees.fingerprint
    run.candidate_base_ref = worktrees.target
    engine.store.save(run)

    class MalformedAdoptClient:
        """@brief Reach publication lookup with valid local delivery evidence."""

        statuses = deque([task("deliver"), task("deliver")])

        def __init__(self, *args, **kwargs):
            pass

        def probe(self):
            return None

        def task_status(self, task_id):
            return self.statuses.popleft()

        def report(self, task_id):
            return None

        def evolution(self, task_id):
            return {}

    monkeypatch.setattr(orchestrator_module, "AegisClient", MalformedAdoptClient)

    engine._publish(run, forge.ticket)

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "failed"
    assert saved.outcome.startswith("MR_CREATE_FAILED")
    assert forge.opened == []


def test_done_task_with_mr_recovers_close_out_before_review(tmp_path: Path) -> None:
    """@brief A done journal is checkpointed and pushed before leaving working."""
    engine, forge, worktrees, containers, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.stage = "deliver"
    run.mr_iid = forge.mr.iid
    run.mr_url = forge.mr.web_url
    engine.store.save(run)

    engine._conduct_task(run, forge.ticket, FakeAegis([task("done")]), "")

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "in-review"
    assert saved.stage == "done"
    assert worktrees.pushes == [run.branch]
    assert worktrees.checkpoints[-1] == f"ADORE recover close-out {TASK_ID}"
    assert containers.stopped[-1] == run.container
    engine._reconcile_stale_working(saved)
    assert engine.store.load(run.run_id).lifecycle == "in-review"


def test_review_round_creates_new_aegis_task_on_same_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Every bounded requested revision preserves the prior task journal."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = "in-review"
    run.stage = "done"
    run.mr_iid = 9
    run.mr_url = forge.mr.web_url
    forge.mr.labels = ["agent-revise"]
    engine.store.save(run)
    conducted: list[str] = []

    class ReviewClient:
        def __init__(self, *args, **kwargs):
            pass

        def probe(self):
            return None

        def create_task(self, title, task_type):
            assert task_type == "change"
            return "TASK-deadbeef"

    monkeypatch.setattr(orchestrator_module, "AegisClient", ReviewClient)
    monkeypatch.setattr(engine, "_conduct", lambda state, ticket, thread="": (
        conducted.append(state.active_task_id or "")
    ))
    summary = {"revised": 0}

    engine._reconcile_review(run, summary)

    saved = engine.store.load(run.run_id)
    assert saved.task_ids == [TASK_ID, "TASK-deadbeef"]
    assert saved.active_task_id == "TASK-deadbeef"
    assert saved.review_rounds == 1 and saved.lifecycle == "working"
    assert conducted == ["TASK-deadbeef"]


def test_strict_verification_runs_once_per_successful_run(tmp_path: Path) -> None:
    """
    @brief   The validate -> deliver transition verifies, and the next pass of
             the conduct loop reads the task back at deliver. Both call sites
             used to fire, so the whole strict catalogue AND every configured
             command ran twice on every successful run - a doubled test suite
             on a real repository (live finding 2026-09-18).
    """
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    client = FakeAegis(sequence("frame", "specify", "design", "build",
                                "validate", "deliver"))

    engine._conduct_task(run, forge.ticket, client, "")

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "awaiting-approval"
    strict = [e for e in engine.store.read_journal(run.run_id)
              if e["event"] == "strict-verification"]
    assert len(strict) == 1


def test_selection_never_trusts_the_server_label_filter(tmp_path: Path) -> None:
    """
    @brief   A server that silently drops an unrecognised `labels=` filter
             answers with its whole open backlog, which at this boundary would
             mean ADORE autonomously conducting arbitrary tickets. Gitea 1.25.4
             was observed doing exactly that; GitHub was verified to filter
             correctly and GitLab is unverified, so the label is re-checked
             here rather than trusted from any adapter.
    """
    engine, forge, _, _, _ = make_engine(tmp_path)
    ready = engine.config.labels.lifecycle.ready
    unrelated = Ticket(
        iid=99, title="Not for the agent",
        description="## Acceptance Criteria\n- [ ] x", labels=["P1"],
    )
    forge.ticket.labels = [ready, "P2"]
    forge.ready = [unrelated, forge.ticket]      # server ignored the filter

    assert engine._pick_ticket().iid == forge.ticket.iid


def test_selection_skips_a_ticket_that_is_not_open(tmp_path: Path) -> None:
    """
    @brief   Conducting a closed ticket is worse than missing one, so the state
             is confirmed at the boundary and not left to a CLI default.
    """
    engine, forge, _, _, _ = make_engine(tmp_path)
    forge.ticket.labels = [engine.config.labels.lifecycle.ready, "P2"]
    forge.ticket.state = "closed"
    forge.ready = [forge.ticket]

    assert engine._pick_ticket() is None


def test_explicit_ticket_start_keeps_readiness_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief A web-selected ticket must still satisfy normal readiness."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    ready = engine.config.labels.lifecycle.ready
    forge.ticket.labels = [ready, "P2"]
    other = Ticket(iid=99, title="Held", description="- [ ] Acceptance Criteria",
                   labels=[ready, "P1", engine.config.labels.control.hold])
    forge.ready = [other, forge.ticket]
    selected = []
    monkeypatch.setattr(engine, "_probe_repository_payload", lambda: None)
    monkeypatch.setattr(engine, "_claim_and_conduct", lambda ticket: selected.append(ticket.iid))

    assert engine.poll_once(ticket_iid=99)["picked"] is None
    assert selected == []
    assert engine.poll_once(ticket_iid=forge.ticket.iid)["picked"] == forge.ticket.iid
    assert selected == [forge.ticket.iid]


def test_publication_retry_survives_a_dirty_worktree(tmp_path: Path) -> None:
    """
    @brief   `_publish` retries itself after a bookkeeping stage failure, but a
             failed attempt can leave the worktree dirty and fingerprinting
             refuses a dirty candidate. The retry then died instantly as
             PUBLICATION_SETUP, so a failure budgeted for three attempts got
             one (live finding 2026-09-18, GitHub pilot). Leftover work is now
             checkpointed and the retry proceeds.
    """
    engine, _, worktrees, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.approved_product = "a" * 64          # publication already began
    run.worktree = str(tmp_path / "wt")
    engine.store.save(run)
    worktrees.dirty = True

    engine._settle_worktree(run, "publication retry")

    # the leftover work is committed, so the fingerprints that follow - in
    # `_publish` and in `retry`'s freshness check - no longer meet a dirty tree
    assert not worktrees.dirty
    assert any(
        e["event"] == "checkpoint" and "settle" in e["message"]
        for e in engine.store.read_journal(run.run_id)
    )


def test_settle_is_a_no_op_on_a_clean_worktree(tmp_path: Path) -> None:
    """
    @brief   Settling must not manufacture an empty commit on the first entry
             into publication, where validation already guarantees a clean tree.
    """
    engine, _, worktrees, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.worktree = str(tmp_path / "wt")
    worktrees.dirty = False

    engine._settle_worktree(run, "publication retry")

    assert not any(
        "settle" in e.get("message", "")
        for e in engine.store.read_journal(run.run_id)
    )


def test_approved_product_baseline_is_captured_once_and_reused(
    tmp_path: Path,
) -> None:
    """
    @brief   Recapturing the baseline on a retry would adopt whatever the
             failed attempt left as "approved", letting an unapproved product
             change pass the CANDIDATE_MUTATION guard meant to catch it. It is
             captured once and reused, so the comparison keeps referring to
             what the human actually approved.
    """
    engine, _, worktrees, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    captures: list[int] = []
    original = worktrees.product_diff_fingerprint

    def counting(run_id, base_ref):
        captures.append(1)
        return original(run_id, base_ref)

    worktrees.product_diff_fingerprint = counting
    first = engine._approved_product(run)
    second = engine._approved_product(engine.store.load(run.run_id))

    assert first == second and len(captures) == 1


def test_push_retries_a_transient_remote_failure(tmp_path: Path) -> None:
    """
    @brief   A one-off credential refresh used to end a fully validated run at
             the push, discarding the human approval bound to that candidate
             (live finding 2026-09-18). Every fetch around the push already
             retried; the push itself did not. Retrying is safe because the
             same refs produce the same remote state.
    """
    engine, _, worktrees, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    attempts: list[int] = []

    def flaky(run_id, branch):
        attempts.append(1)
        if len(attempts) == 1:
            return CommandResult(exit_code=1, stderr="remote: Failed to authenticate user")
        return CommandResult(exit_code=0)

    worktrees.push = flaky
    result = engine._push_branch(run)

    assert result.ok and len(attempts) == 2
    transient = [e for e in engine.store.read_journal(run.run_id)
                 if e["event"] == "transient-failure" and e["operation"] == "push"]
    assert len(transient) == 1


def test_push_still_fails_loudly_when_the_remote_refuses(tmp_path: Path) -> None:
    """
    @brief   A genuine refusal - a protected branch, a non-fast-forward - must
             still end the run. Retrying only delays it, bounded by
             max_transient_retries.
    """
    engine, _, worktrees, _, _ = make_engine(tmp_path)
    engine.config.recovery.max_transient_retries = 3
    run = make_run(engine)
    attempts: list[int] = []

    def refused(run_id, branch):
        attempts.append(1)
        return CommandResult(exit_code=1, stderr="remote: protected branch hook declined")

    worktrees.push = refused
    result = engine._push_branch(run)

    assert not result.ok and len(attempts) == 3


def _review_run(engine, forge, **overrides):
    """
    @brief      An in-review run bound to the fake forge's draft MR.
    @param[in]  engine The orchestrator under test.
    @param[in]  forge The FakeForge backing it.
    @param[in]  overrides Extra RunState fields to set.
    @return     The persisted RunState.
    """
    run = make_run(engine)
    run.lifecycle = "in-review"
    run.stage = "done"
    run.mr_iid = forge.mr.iid
    run.mr_url = forge.mr.web_url
    for key, value in overrides.items():
        setattr(run, key, value)
    engine.store.save(run)
    return run


class _ReviewClient:
    """@brief AEGIS client double that only has to create the revision task."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def probe(self):
        return None

    def create_task(self, title, task_type):
        return "TASK-deadbeef"


def test_failed_pipeline_starts_a_governed_repair_round(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief   A newly red pipeline starts a revision on the SAME bounded path
             the revise label uses, with no label applied and no human action.
             The executor is told the pipeline is what must go green, and the
             run returns to `working` so the round ends at a fresh approval
             before anything is pushed.
    """
    engine, forge, _, _, _ = make_engine(tmp_path)
    forge.pipeline = "failed"
    run = _review_run(engine, forge)
    threads: list[str] = []
    monkeypatch.setattr(orchestrator_module, "AegisClient", _ReviewClient)
    monkeypatch.setattr(engine, "_conduct", lambda state, ticket, thread="": (
        threads.append(thread)
    ))

    engine._reconcile_review(run, {"revised": 0})

    saved = engine.store.load(run.run_id)
    assert saved.review_rounds == 1 and saved.lifecycle == "working"
    assert saved.active_task_id == "TASK-deadbeef"
    assert "pipeline" in threads[0] and "green" in threads[0]
    # the reviewer watching the draft is told why commits are about to arrive
    announced = "\n".join(forge.mr_comments.values())
    assert "automatic repair round (1/3)" in announced
    # the verdict is cleared so the NEXT pipeline run is judged on its own
    assert saved.pipeline_reported == ""
    # no label was involved, so none was removed
    assert forge.mr.labels == []


def test_failed_pipeline_is_not_repaired_twice_for_one_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief   An unchanged red verdict must not restart a repair round on every
             poll while the previous one is still in flight, so only a CHANGE
             is a signal.
    """
    engine, forge, _, _, _ = make_engine(tmp_path)
    forge.pipeline = "failed"
    run = _review_run(engine, forge, pipeline_reported="failed")
    monkeypatch.setattr(orchestrator_module, "AegisClient", _ReviewClient)
    monkeypatch.setattr(engine, "_conduct", lambda *a, **k: None)

    engine._reconcile_review(run, {"revised": 0})

    saved = engine.store.load(run.run_id)
    assert saved.review_rounds == 0 and saved.lifecycle == "in-review"


def test_notify_mode_reports_a_red_pipeline_without_acting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief   With automatic repair off, the red pipeline is surfaced once on
             the MR and the run keeps waiting for a human.
    """
    engine, forge, _, _, _ = make_engine(tmp_path)
    engine.config.review.on_pipeline_failure = "notify"
    forge.pipeline = "failed"
    run = _review_run(engine, forge)
    monkeypatch.setattr(orchestrator_module, "AegisClient", _ReviewClient)

    engine._reconcile_review(run, {"revised": 0})

    saved = engine.store.load(run.run_id)
    assert saved.review_rounds == 0 and saved.lifecycle == "in-review"
    posted = "\n".join(forge.mr_comments.values())
    assert "failed" in posted and engine.config.review.revise_label in posted


def test_pipeline_repair_stops_at_the_review_round_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief   A permanently red pipeline cannot loop: once the review-round
             budget is spent the run is left in review with a comment saying
             so, rather than being failed or repaired again.
    """
    engine, forge, _, _, _ = make_engine(tmp_path)
    engine.config.review.max_review_rounds = 2
    forge.pipeline = "failed"
    run = _review_run(engine, forge, review_rounds=2)
    monkeypatch.setattr(orchestrator_module, "AegisClient", _ReviewClient)

    engine._reconcile_review(run, {"revised": 0})

    saved = engine.store.load(run.run_id)
    assert saved.review_rounds == 2 and saved.lifecycle == "in-review"
    assert "budget is spent" in "\n".join(forge.mr_comments.values())


def test_ignore_mode_never_reads_the_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief   A repository with no CI pays nothing: the adapter is not called.
    """
    engine, forge, _, _, _ = make_engine(tmp_path)
    engine.config.review.on_pipeline_failure = "ignore"
    asked: list[int] = []
    forge.pipeline_status = lambda mr_iid: asked.append(mr_iid) or "failed"
    run = _review_run(engine, forge)
    monkeypatch.setattr(orchestrator_module, "AegisClient", _ReviewClient)

    engine._reconcile_review(run, {"revised": 0})

    assert asked == []
    assert engine.store.load(run.run_id).lifecycle == "in-review"


def test_review_revision_rearms_only_the_active_wall_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A late review request starts a fresh bounded revision phase."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    engine.config.budgets.max_wall_clock_seconds = 60
    run = make_run(engine)
    run.lifecycle = "in-review"
    run.stage = "done"
    run.mr_iid = forge.mr.iid
    run.mr_url = forge.mr.web_url
    run.active_started_at = "2026-08-15T00:00:00Z"
    run.iterations = 2
    run.stage_failures = 2
    forge.mr.labels = ["agent-revise"]
    engine.store.save(run)
    observed: list[tuple[str, int, int]] = []

    class ReviewClient:
        """@brief Create one fresh revision task through the normal poll path."""

        def __init__(self, *args, **kwargs):
            pass

        def probe(self):
            return None

        def create_task(self, title, task_type):
            return "TASK-deadbeef"

    def conduct(state: RunState, ticket: Ticket, thread: str = "") -> None:
        observed.append((engine._budget_exceeded(state), state.iterations, state.stage_failures))

    monkeypatch.setattr(orchestrator_module, "AegisClient", ReviewClient)
    monkeypatch.setattr(orchestrator_module, "utc_now_iso", lambda: "2026-08-15T12:00:00Z")
    monkeypatch.setattr(engine, "_conduct", conduct)

    summary = engine.poll_once()

    saved = engine.store.load(run.run_id)
    assert summary["revised"] == 1
    assert observed == [("", 2, 0)]
    assert saved.active_started_at == "2026-08-15T12:00:00Z"


def test_revision_task_failure_preserves_revise_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief A task-creation failure cannot consume the human revise intent."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = "in-review"
    run.stage = "done"
    run.mr_iid = forge.mr.iid
    run.mr_url = forge.mr.web_url
    forge.mr.labels = ["agent-revise"]
    engine.store.save(run)

    class FailingReviewClient:
        """@brief Fail only at the AEGIS task-creation boundary."""

        def __init__(self, *args, **kwargs):
            pass

        def probe(self):
            return None

        def create_task(self, title, task_type):
            raise AegisTaskError("task creation failed")

    monkeypatch.setattr(orchestrator_module, "AegisClient", FailingReviewClient)

    engine._reconcile_review(run, {"revised": 0})

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "failed"
    assert saved.outcome.startswith("REVIEW_START_FAILED")
    assert "agent-revise" in forge.mr.labels
    assert saved.task_ids == [TASK_ID]


def test_revision_label_removal_failure_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief A created revision task is journaled while its trigger stays visible."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = "in-review"
    run.stage = "done"
    run.mr_iid = forge.mr.iid
    run.mr_url = forge.mr.web_url
    forge.mr.labels = ["agent-revise"]
    forge.fail_mr_label_removal = True
    engine.store.save(run)

    class CreatedReviewClient:
        """@brief Create one task before the forge label write fails."""

        def __init__(self, *args, **kwargs):
            pass

        def probe(self):
            return None

        def create_task(self, title, task_type):
            return "TASK-deadbeef"

    monkeypatch.setattr(orchestrator_module, "AegisClient", CreatedReviewClient)

    engine._reconcile_review(run, {"revised": 0})

    saved = engine.store.load(run.run_id)
    created = [
        event for event in engine.store.read_journal(run.run_id)
        if event["event"] == "revision-task-created"
    ]
    assert saved.lifecycle == "failed"
    assert saved.outcome.startswith("REVISE_LABEL_REMOVE")
    assert saved.active_task_id == TASK_ID
    assert "agent-revise" in forge.mr.labels
    assert created[-1]["task"] == "TASK-deadbeef"


def test_human_merge_is_visible_in_aggregate_and_profile_metrics(tmp_path: Path) -> None:
    """@brief The actual merged-by-human outcome drives all headline metrics."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    db = tmp_path / "metrics.db"
    engine.config.metrics.enabled = True
    engine.config.metrics.db_path = str(db)
    run = make_run(engine)
    run.lifecycle = "in-review"
    run.stage = "done"
    run.mr_iid = 9
    run.mr_url = forge.mr.web_url
    forge.mr.state = "merged"
    engine.store.save(run)
    summary = {"done": 0}

    engine._reconcile_review(run, summary)

    rows = load_summaries(db)
    assert rows[0].outcome == "merged by human"
    assert aggregate(rows)["all"]["merged"] == 1
    assert profile_stats(db)["success_rate"] == 100.0
    assert summary["done"] == 1


def test_merged_mr_precedes_closed_source_ticket(tmp_path: Path) -> None:
    """@brief An authoritative merge wins over simultaneous source-ticket closure."""
    engine, forge, worktrees, containers, _ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = "in-review"
    run.stage = "done"
    run.mr_iid = forge.mr.iid
    run.mr_url = forge.mr.web_url
    forge.mr.state = "merged"
    forge.ticket.state = "closed"
    engine.store.save(run)
    summary = {"done": 0}

    engine._reconcile_review(run, summary)

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "done"
    assert saved.outcome == "merged by human"
    assert summary["done"] == 1
    assert containers.removed == [run.container]
    assert worktrees.removed == [run.run_id]


def test_cleanup_reports_live_lock_without_releasing_it(tmp_path: Path) -> None:
    """@brief Cleanup leaves its live conductor lock intact and names the pid."""
    engine, _, _, _, _ = make_engine(tmp_path)
    assert engine.store.acquire_lock()
    try:
        report = engine.cleanup()
        assert report["lock_cleared"] is False
        assert report["lock_held_by"] == os.getpid()
        assert engine.store.lock_path.is_file()
    finally:
        engine.store.release_lock()


def test_cleanup_preserves_failed_run_resources_and_reports_egress_gc(
    tmp_path: Path,
) -> None:
    """
    @brief   Failed worktrees/containers/proxy/networks remain retryable while
             this project's state-less run resources are reported as removed.
    """
    engine, _, worktrees, containers, _ = make_engine(tmp_path)
    failed = make_run(engine)
    failed.lifecycle = "failed"
    engine.store.save(failed)
    root = tmp_path / "worktrees"
    worktrees.path_for = lambda run_id: root / run_id
    failed_path = root / failed.run_id
    orphan_path = root / "github-owner-repo-99"
    failed_path.mkdir(parents=True)
    orphan_path.mkdir(parents=True)
    worktrees.dirs = [failed_path, orphan_path]
    containers.cleanup_containers = ["adore-run-github-owner-repo-99"]
    containers.cleanup_proxies = ["adore-run-github-owner-repo-99-egress-proxy"]
    containers.cleanup_networks = ["adore-egress-adore-run-github-owner-repo-99"]

    report = engine.cleanup()

    assert failed_path.is_dir()
    assert not orphan_path.exists()
    assert failed.run_id not in worktrees.removed
    assert report["worktrees_removed"] == ["github-owner-repo-99"]
    assert report["containers_removed"] == ["adore-run-github-owner-repo-99"]
    assert report["proxy_containers_removed"] == [
        "adore-run-github-owner-repo-99-egress-proxy",
    ]
    assert report["egress_networks_removed"] == [
        "adore-egress-adore-run-github-owner-repo-99",
    ]
    assert len(containers.cleanup_calls) == 3
    for targets, retained in containers.cleanup_calls:
        assert failed.container in retained and failed.container not in targets
        assert "adore-run-github-owner-repo-99" in targets


@pytest.mark.parametrize(
    ("labels", "expected"),
    [([], "change"), (["bug"], "fix")],
)
def test_ticket_kind_mapping_uses_configured_default_and_bug_label(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    labels: list[str],
    expected: str,
) -> None:
    """@brief Kind mapping honors the configured fallback and bug -> fix map."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    engine.config.workflow.default_kind = "change"
    forge.ticket.labels = labels
    monkeypatch.setattr(engine, "_conduct", lambda run, ticket: None)

    engine._claim_and_conduct(forge.ticket)

    assert engine.store.load(engine._run_id(forge.ticket.iid)).aegis_type == expected


def test_configured_feature_label_overrides_nonfeature_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A configured feature label wins before a non-feature fallback."""
    engine, forge, _, _, _ = make_engine(tmp_path)
    engine.config.workflow.default_kind = "change"
    engine.config.workflow.kind_labels["enhancement"] = "feature"
    forge.ticket.labels = ["enhancement"]
    monkeypatch.setattr(engine, "_conduct", lambda run, ticket: None)

    engine._claim_and_conduct(forge.ticket)

    assert engine.store.load(engine._run_id(forge.ticket.iid)).aegis_type == "feature"


def test_budget_check_reads_cost_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief One budget decision reads and sums the durable journal once."""
    engine, _, _, _, _ = make_engine(tmp_path)
    run = make_run(engine)
    calls: list[str] = []

    def cost_spent(state: RunState) -> float:
        calls.append(state.run_id)
        return engine.config.budgets.max_cost_usd

    monkeypatch.setattr(engine, "_cost_spent", cost_spent)

    assert engine._budget_exceeded(run).startswith("cost budget reached")
    assert calls == [run.run_id]


def test_from_config_env_filter_and_process_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief   Direct construction defaults sensibly but an explicit env file is
             filtered by env_keys and overridden by the process environment.
    """
    config = make_config(tmp_path)
    config.executor.env_keys = ["ADORE_TEST_SECRET", "ADORE_FILE_ONLY"]
    config.executor.commands["opencode"] = ExecutorCommand(
        command="opencode run {prompt}",
        model="test-model",
    )
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ADORE_TEST_SECRET=file\nADORE_FILE_ONLY=file-only\nIGNORED=value\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ADORE_TEST_SECRET", "process")
    monkeypatch.delenv("ADORE_FILE_ONLY", raising=False)

    engine = Orchestrator.from_config(config, env_file=env_file)

    assert engine.secrets == {
        "ADORE_TEST_SECRET": "process",
        "ADORE_FILE_ONLY": "file-only",
    }


def test_terminal_status_failure_preserves_lifecycle_and_outcome(tmp_path: Path) -> None:
    """@brief A queued cancellation-status replay cannot rewrite terminal truth."""
    forge = FakeForge()
    engine, _, _, _, _ = make_engine(tmp_path, forge=forge)
    run = make_run(engine)
    forge.fail_comments = True

    assert engine.cancel(run.run_id, outcome="ticket closed")

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "cancelled"
    assert saved.outcome == "ticket closed"
    assert len(saved.notification_outbox) == 1
    assert saved.notification_outbox[0]["kind"] == "status"


def test_nonterminal_status_failure_still_stops_work(tmp_path: Path) -> None:
    """@brief Required status signaling remains fail-closed during active work."""
    forge = FakeForge()
    engine, _, _, containers, _ = make_engine(tmp_path, forge=forge)
    run = make_run(engine)
    forge.fail_comments = True

    engine._status(run)

    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "failed"
    assert saved.outcome.startswith("STATUS_NOTIFICATION")
    assert containers.stopped == [run.container]


def test_forge_contract_deliberately_has_no_merge_operation() -> None:
    """@brief The conductor's remote capability cannot merge by construction."""
    assert not hasattr(Forge, "merge")


# END OF FILE


@pytest.mark.parametrize("signal", ["both", "files", "log", "rewrite", "empty"])
def test_partial_stage_requires_candidate_and_append_only_evidence(tmp_path, monkeypatch, signal):
    """@brief Useful partial work continues; incomplete or rewritten evidence fails."""
    engine, forge, worktrees, _, executor = make_engine(tmp_path)
    engine.config.recovery.max_stage_failures = 1
    engine.config.budgets.max_iterations = 2
    run = make_run(engine)
    run.stage = "build"
    before = replace(task("build"), log=("original work",))
    logs = {
        "both": ("original work", "build partial green: tests pass, browser work remains"),
        "files": ("original work",),
        "log": ("original work", "build partial green: tests pass"),
        "rewrite": ("rewritten work", "build partial green: tests pass"),
        "empty": ("original work", " "),
    }
    after = replace(before, log=logs[signal])
    snapshots = [before, after, after, replace(after, log=(*after.log, "continued work"))]
    original = executor.run_gate
    def execute(*args, **kwargs):
        result = original(*args, **kwargs)
        if signal != "log":
            worktrees.progress_fingerprint += "change"
        return result
    monkeypatch.setattr(executor, "run_gate", execute)
    engine._conduct_task(run, forge.ticket, FakeAegis(snapshots), "")
    if signal == "both":
        assert len(executor.prompts) == 2
        assert "BUDGET_EXHAUSTED" in run.outcome
        assert run.stage_failures == 0
        assert len(worktrees.checkpoints) == 2
        assert "browser work remains" in executor.prompts[1]
        assert "Handoff" in executor.prompts[1]
    else:
        assert len(executor.prompts) == 1
        assert run.failure_history[-1]["code"] == "NO_STAGE_PROGRESS"


def test_partial_stage_preserves_prior_failure_count(tmp_path, monkeypatch):
    """@brief A continuation never resets a real failure and remains iteration bounded."""
    engine, forge, worktrees, _, executor = make_engine(tmp_path)
    engine.config.budgets.max_iterations = 1
    run = make_run(engine)
    run.stage = "build"
    run.stage_failures = 2
    before = replace(task("build"), log=("old",))
    after = replace(before, log=("old", "build: partial tests pass"))
    def execute(*args, **kwargs):
        worktrees.progress_fingerprint = "changed"
        return GateRun(exit_code=0)
    monkeypatch.setattr(executor, "run_gate", execute)
    engine._conduct_task(run, forge.ticket, FakeAegis([before, after]), "")
    assert "BUDGET_EXHAUSTED" in run.outcome
    assert run.stage_failures == 2
    assert worktrees.checkpoints



def test_partial_stage_eventually_advances_and_requests_approval(tmp_path, monkeypatch):
    """@brief Continuation leads to governed validation and the existing approval stop."""
    engine, forge, worktrees, _, executor = make_engine(tmp_path)
    engine.config.recovery.max_stage_failures = 1
    run = make_run(engine)
    run.stage = "build"
    before = replace(task("build"), log=("build red: regression fails",))
    after = replace(before, log=(*before.log, "build partial green: focused tests pass"))
    original = executor.run_gate
    def execute(*args, **kwargs):
        worktrees.progress_fingerprint += "change"
        return original(*args, **kwargs)
    monkeypatch.setattr(executor, "run_gate", execute)
    client = FakeAegis([before, after, after, task("validate"),
                        task("validate"), task("deliver"), task("deliver")])
    engine._conduct_task(run, forge.ticket, client, "")
    assert run.lifecycle == "awaiting-approval"
    assert not run.failure_history
    assert len(executor.prompts) == 3
    assert not worktrees.pushes


@pytest.mark.parametrize("when", ["before", "after"])
def test_partial_stage_snapshot_failure_stops_visibly(tmp_path, monkeypatch, when):
    """@brief Untrustworthy progress observations are terminal, never continuations."""
    engine, forge, worktrees, _, executor = make_engine(tmp_path)
    run = make_run(engine)
    run.stage = "build"
    before = task("build")
    after = replace(before, log=("build: useful work",))
    calls = 0
    def observe(run_id):
        nonlocal calls
        calls += 1
        if calls == (1 if when == "before" else 2):
            raise IsolationError("unreadable worktree")
        return "baseline"
    monkeypatch.setattr(worktrees, "worktree_progress_fingerprint", observe)
    engine._conduct_task(run, forge.ticket, FakeAegis([before, after]), "")
    assert "WORKTREE_PROGRESS" in run.outcome
    assert run.lifecycle == "failed"
    assert len(executor.prompts) == (0 if when == "before" else 1)
    assert not worktrees.checkpoints


def test_nonzero_gate_with_candidate_work_is_still_failure(tmp_path, monkeypatch):
    """@brief Progress never overrides a genuine failed gate."""
    engine, forge, worktrees, _, executor = make_engine(tmp_path)
    engine.config.recovery.max_stage_failures = 1
    run = make_run(engine)
    run.stage = "build"
    def execute(*args, **kwargs):
        worktrees.progress_fingerprint = "changed"
        return GateRun(exit_code=2, stderr="failed gate")
    monkeypatch.setattr(executor, "run_gate", execute)
    engine._conduct_task(run, forge.ticket, FakeAegis([task("build")]), "")
    assert run.failure_history[-1]["code"] == "EXECUTOR_EXIT"
    assert not worktrees.checkpoints


@pytest.mark.parametrize("bound", ["none", "iterations", "clock", "files"])
def test_disabled_cost_cap_preserves_other_bounds_and_usage(tmp_path, monkeypatch, bound):
    """@brief High reported cost remains visible but cannot stop a zero-cap run."""
    engine, _, worktrees, _, _ = make_engine(tmp_path)
    engine.config.budgets.max_cost_usd = 0
    run = make_run(engine)
    engine.store.journal(run.run_id, "usage", cost_usd=6.22)
    if bound == "iterations":
        run.iterations = engine.config.budgets.max_iterations
    elif bound == "clock":
        run.active_started_at = "2020-01-01T00:00:00Z"
    elif bound == "files":
        monkeypatch.setattr(worktrees, "changed_files", lambda *args: 121)
    before = engine.store.read_journal(run.run_id)
    def forbidden_cost_read(*args):
        pytest.fail("Disabled cap must not enforce dollar accounting")
    monkeypatch.setattr(engine, "_cost_spent", forbidden_cost_read)
    reason = engine._budget_exceeded(run)
    if bound == "none":
        assert reason == ""
    else:
        assert {"iterations": "iteration budget", "clock": "active work clock",
                "files": "file budget"}[bound] in reason
    assert engine.store.read_journal(run.run_id) == before


@pytest.mark.parametrize("cap", [0, 5.0])
def test_reported_cost_cap_controls_validation_resume_without_erasing_usage(tmp_path, cap):
    """@brief Preserved subscription work reaches approval at zero; paid caps still stop."""
    engine, forge, _, _, executor = make_engine(tmp_path)
    engine.config.budgets.max_cost_usd = cap
    run = make_run(engine)
    run.stage = "validate"
    engine.store.journal(run.run_id, "usage", cost_usd=6.22)
    engine._conduct_task(run, forge.ticket, FakeAegis(sequence("validate", "deliver")), "")
    assert run.lifecycle == ("awaiting-approval" if cap == 0 else "failed")
    assert any(e.get("cost_usd") == 6.22 for e in engine.store.read_journal(run.run_id))
    assert bool(executor.prompts) == (cap == 0)
    if cap > 0:
        assert "cost budget reached ($6.22)" in run.outcome


def test_purge_resources_touches_only_this_projects_non_human_runs(tmp_path: Path) -> None:
    """
    @brief   Project deletion releases the containers and worktrees recorded for
             this project's runs, keeps human-owned work, and never sweeps by
             name prefix or shared worktree root (other projects share both).
    """
    engine, _, worktrees, containers, _ = make_engine(tmp_path)
    root = tmp_path / "worktrees"
    worktrees.path_for = lambda run_id: root / run_id
    failed = make_run(engine)
    failed.lifecycle = "failed"
    engine.store.save(failed)
    engine.store.save(RunState(run_id="done-run", ticket_iid=9, lifecycle="done"))
    engine.store.save(RunState(run_id="cancelled-run", ticket_iid=11, lifecycle="cancelled"))
    engine.store.save(RunState(run_id="human-run", ticket_iid=8, lifecycle="handed-off",
                               container="adore-run-human-run"))
    engine.store.save(RunState(run_id="pending-run", ticket_iid=10, lifecycle="handoff-pending"))
    for name in (failed.run_id, "done-run", "human-run", "pending-run", "other-project-run"):
        (root / name).mkdir(parents=True)

    report = engine.purge_resources()

    assert not (root / failed.run_id).exists() and not (root / "done-run").exists()
    for kept in ("human-run", "pending-run", "other-project-run"):
        assert (root / kept).is_dir(), kept
    assert sorted(report["worktrees_removed"]) == sorted([failed.run_id, "done-run"])
    assert "adore-run-cancelled-run" in containers.removed
    assert report["worktrees_retained"] == ["human-run", "pending-run"]
    assert sorted(containers.removed) == sorted([
        failed.container, "adore-run-done-run", "adore-run-cancelled-run"])
    assert containers.cleanup_calls == []  # no prefix sweeps


def _shared_host(tmp_path: Path, engine: Orchestrator, worktrees: FakeWorktrees, *,
                 run_ids=(), dirs=(), mode: str = "allowlist-proxy"):
    """
    @brief      Put the engine on a host whose slug, worktree root and egress
                network prefix every project shares.
    @param[in]  run_ids Run IDs that get an executor, proxy and network.
    @param[in]  dirs Directory names created under the shared worktree root.
    @param[in]  mode Egress mode of the real ContainerManager under test.
    @return     (worktree root, FakeRuntime).
    """
    root = tmp_path / "shared-worktrees"
    root.mkdir()
    for name in dirs:
        (root / name).mkdir()
    worktrees.path_for = lambda run_id: root / run_id
    worktrees.list_dirs = lambda: sorted(p for p in root.iterdir() if p.is_dir())
    runtime = FakeRuntime()
    for run_id in run_ids:
        executor = f"adore-run-{run_id}"
        runtime.containers |= {executor, f"{executor}-egress-proxy"}
        runtime.networks.add(f"adore-egress-{executor}")
    engine.containers = ContainerManager(
        "docker", "adore-executor-base:1.0.0", "uv-cache", "npm-cache", runtime,
        egress=ContainerEgressConfig(mode=mode),
    )
    return root, runtime


def test_cleanup_leaves_other_projects_resources_on_a_shared_host(tmp_path: Path) -> None:
    """
    @brief   Cleanup for owner/repo removes only its own cancelled run: another
             project's runs (whatever their lifecycle, since that project's
             state is never read here), a look-alike owner/repo-tools run and
             an unrelated folder keep every container, proxy, network and
             directory.
    """
    engine, _, worktrees, _, _ = make_engine(tmp_path)
    own_run = "github-owner-repo-5"
    engine.store.save(RunState(run_id=own_run, ticket_iid=5, lifecycle="cancelled"))
    foreign = ["github-owner-other-1", "github-owner-other-2", "github-owner-other-3",
               "github-owner-repo-tools-4"]
    root, runtime = _shared_host(tmp_path, engine, worktrees, run_ids=[*foreign, own_run],
                                 dirs=[*foreign, own_run, "notes"])
    containers_before, networks_before = set(runtime.containers), set(runtime.networks)

    report = engine.cleanup()

    own = f"adore-run-{own_run}"
    assert runtime.containers == containers_before - {own, f"{own}-egress-proxy"}
    assert runtime.networks == networks_before - {f"adore-egress-{own}"}
    assert sorted(path.name for path in root.iterdir()) == sorted([*foreign, "notes"])
    assert report["containers_removed"] == [own]
    assert report["proxy_containers_removed"] == [f"{own}-egress-proxy"]
    assert report["egress_networks_removed"] == [f"adore-egress-{own}"]
    assert report["worktrees_removed"] == [own_run]


def test_cleanup_removes_this_projects_finished_and_stateless_run_resources(
    tmp_path: Path,
) -> None:
    """
    @brief   Done, cancelled and stale runs (also under a recorded ID outside
             the run-ID form or a recorded container name of another form),
             and this project's run IDs without state (found by container or
             by worktree directory), lose executor, proxy, networks and
             worktree in any egress mode; working, failed and human-owned runs
             keep theirs.
    """
    engine, _, worktrees, _, _ = make_engine(tmp_path)
    make_run(engine)  # github-owner-repo-7, working
    for iid, lifecycle in ((5, "cancelled"), (8, "done"), (12, "stale"), (6, "failed"),
                           (10, "handed-off"), (11, "handoff-pending")):
        engine.store.save(RunState(run_id=f"github-owner-repo-{iid}", ticket_iid=iid,
                                   lifecycle=lifecycle))
    engine.store.save(RunState(run_id="legacy-done", ticket_iid=4, lifecycle="done"))
    renamed = "adore-run-renamed-15"
    engine.store.save(RunState(run_id="github-owner-repo-15", ticket_iid=15,
                               lifecycle="cancelled", container=renamed))
    kept = [f"github-owner-repo-{iid}" for iid in (6, 7, 10, 11)]
    gone = [f"github-owner-repo-{iid}" for iid in (5, 8, 9, 12)]  # 9: no state
    root, runtime = _shared_host(
        tmp_path, engine, worktrees, run_ids=[*kept, *gone], mode="open",
        dirs=[*kept, *gone, "github-owner-repo-13", "legacy-done"],
    )
    runtime.containers |= {renamed, f"{renamed}-egress-proxy"}
    runtime.networks.add(f"adore-egress-{renamed}")

    report = engine.cleanup()

    executors = sorted([*(f"adore-run-{run_id}" for run_id in gone), renamed])
    assert report["containers_removed"] == executors
    assert report["proxy_containers_removed"] == [f"{name}-egress-proxy" for name in executors]
    assert report["egress_networks_removed"] == [f"adore-egress-{name}" for name in executors]
    assert report["worktrees_removed"] == sorted([*gone, "github-owner-repo-13", "legacy-done"])
    assert sorted(path.name for path in root.iterdir()) == sorted(kept)
    for run_id in kept:
        executor = f"adore-run-{run_id}"
        assert {executor, f"{executor}-egress-proxy"} <= runtime.containers
        assert f"adore-egress-{executor}" in runtime.networks


def test_cleanup_keeps_resources_of_runs_with_corrupt_state(tmp_path: Path) -> None:
    """
    @brief   A run whose state file is unreadable keeps its worktree, executor,
             proxy and network and is reported under corrupt_runs.
    """
    engine, _, worktrees, _, _ = make_engine(tmp_path)
    run_id = "github-owner-repo-14"
    broken = engine.store.run_dir(run_id)
    broken.mkdir(parents=True, exist_ok=True)
    (broken / "state.json").write_text("{not json", encoding="utf-8")
    root, runtime = _shared_host(tmp_path, engine, worktrees, run_ids=[run_id], dirs=[run_id])
    before = (set(runtime.containers), set(runtime.networks))

    report = engine.cleanup()

    assert report["corrupt_runs"] == [run_id]
    assert (root / run_id).is_dir()
    assert (runtime.containers, runtime.networks) == before
    for key in ("containers_removed", "proxy_containers_removed",
                "egress_networks_removed", "worktrees_removed"):
        assert report[key] == [], key


def test_cleanup_keeps_truncated_egress_names_shared_with_a_protected_run(
    tmp_path: Path,
) -> None:
    """
    @brief   A long repository path truncates proxy and network names, so a done
             and a handed-off run share them; the done run's executor and
             worktree go, the shared proxy and network stay.
    """
    engine, _, worktrees, _, _ = make_engine(tmp_path)
    engine.config.platform.kind = "gitea"
    engine.config.platform.repo = "dpasare/2026_Networked_Intelligent_Lab_Orchestrator"
    done, human = (f"gitea-dpasare-2026_Networked_Intelligent_Lab_Orchestrator-{iid}"
                   for iid in (26, 27))
    engine.store.save(RunState(run_id=done, ticket_iid=26, lifecycle="done"))
    engine.store.save(RunState(run_id=human, ticket_iid=27, lifecycle="handed-off"))
    root, runtime = _shared_host(tmp_path, engine, worktrees, dirs=[done, human])
    proxy = "adore-run-gitea-dpasare-2026_Networked_Intelligent-egress-proxy"
    network = "adore-egress-adore-run-gitea-dpasare-2026_Networked_Intellige"
    runtime.containers |= {f"adore-run-{done}", f"adore-run-{human}", proxy}
    runtime.networks.add(network)

    report = engine.cleanup()

    assert report["containers_removed"] == [f"adore-run-{done}"]
    assert report["proxy_containers_removed"] == []
    assert report["egress_networks_removed"] == []
    assert report["worktrees_removed"] == [done]
    assert runtime.containers == {f"adore-run-{human}", proxy}
    assert runtime.networks == {network}
    assert (root / human).is_dir() and not (root / done).exists()


def test_cleanup_continues_when_the_container_runtime_fails(tmp_path: Path) -> None:
    """
    @brief   Failed runtime listings and sweeps are skipped: cleanup still
             removes the eligible worktree and returns its report.
    """
    engine, _, worktrees, containers, _ = make_engine(tmp_path)
    run_id = "github-owner-repo-5"
    engine.store.save(RunState(run_id=run_id, ticket_iid=5, lifecycle="done"))
    root = tmp_path / "worktrees"
    (root / run_id).mkdir(parents=True)
    worktrees.path_for = lambda candidate: root / candidate
    worktrees.dirs = [root / run_id]

    def unavailable(*args):
        raise IsolationError("container runtime unavailable")

    for method in ("list_containers", "cleanup_orphan_containers",
                   "cleanup_egress_proxies", "cleanup_egress_networks"):
        setattr(containers, method, unavailable)

    report = engine.cleanup()

    assert report["worktrees_removed"] == [run_id]
    assert not (root / run_id).exists()
    for key in ("containers_removed", "proxy_containers_removed", "egress_networks_removed"):
        assert report[key] == [], key


def test_cleanup_reports_only_worktrees_it_removed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A worktree directory that survives removal is not reported as removed."""
    engine, _, worktrees, _, _ = make_engine(tmp_path)
    run_id = "github-owner-repo-5"
    engine.store.save(RunState(run_id=run_id, ticket_iid=5, lifecycle="done"))
    stuck = tmp_path / "worktrees" / run_id
    stuck.mkdir(parents=True)
    worktrees.path_for = lambda candidate: stuck.parent / candidate
    worktrees.dirs = [stuck]
    monkeypatch.setattr(orchestrator_module, "force_rmtree", lambda path: None)

    report = engine.cleanup()

    assert stuck.is_dir()
    assert report["worktrees_removed"] == []
