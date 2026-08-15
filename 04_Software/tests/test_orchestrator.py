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
@brief ADORE 0.5 conductor, recovery, approval and notification tests.
@details Uses only injected offline fakes; no forge, git, container or model is
         contacted. The tests focus on observable contracts and fail-closed
         trust boundaries rather than private implementation structure.
"""

from __future__ import annotations

# IMPORTS
from collections import deque
from dataclasses import replace
from pathlib import Path

from adore.aegis import AegisCheck, AegisCommandRun, AegisFinding, AegisTask
from adore.config import Config
from adore.executor.base import GateRun
from adore.forge import Comment, Forge, ForgeError, MergeRequest, Ticket
import adore.orchestrator as orchestrator_module
from adore.orchestrator import Orchestrator
from adore.state import RunState, StateStore
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
        self.next_comment = 100
        self.opened: list[dict] = []

    def list_ready(self, ready_label: str):
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
        if self.mr and (ref == self.mr.iid or isinstance(ref, str)):
            return self.mr
        return None

    def list_mr_comments(self, mr_iid: int):
        return [Comment(id=key, body=value) for key, value in self.mr_comments.items()]

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
        if self.mr:
            self.mr.labels = [item for item in self.mr.labels if item not in labels]

    def open_merge_request(self, source, target, title, body, **kwargs):
        self.opened.append({
            "source": source, "target": target, "title": title, "body": body, **kwargs,
        })
        return self.mr.web_url


class FakeWorktrees:
    """@brief Git/worktree fake with mutable target and candidate fingerprints."""

    repo_path = Path("C:/repo")

    def __init__(self) -> None:
        self.target = "a" * 40
        self.fingerprint = "b" * 64
        self.product_fingerprint = "c" * 64
        self.checkpoints: list[str] = []
        self.pushes: list[str] = []
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
        return []

    def remove(self, run_id, **kwargs):
        return None


class FakeContainers:
    """@brief Container lifecycle fake."""

    def __init__(self) -> None:
        self.stopped: list[str] = []

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

    def remove(self, name):
        return None

    def list_containers(self, prefix):
        return []


class FakeExecutor:
    """@brief Fresh-session executor double with scripted stage results."""

    def __init__(self, *results: GateRun) -> None:
        self.results = deque(results)
        self.sessions: list[str] = []
        self.prompts: list[str] = []

    def run_gate(self, execute, worktree, io_dir, prompt, **kwargs):
        self.sessions.append(kwargs.get("session", "missing"))
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
    assert saved.candidate_fingerprint == worktrees.fingerprint
    assert len(executor.sessions) == len(stages) - 1
    assert set(executor.sessions) == {""}
    assert not forge.opened
    assert containers.stopped
    stage_commits = [item for item in worktrees.checkpoints if "ADORE checkpoint" in item]
    assert len(stage_commits) == len(stages) - 1


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
    assert len(executor.sessions) == 3
    assert "attempt 3/3" in saved.outcome
    assert containers.stopped
    assert len(forge.ticket_comments) >= 2  # edited incident + separate terminal


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
    assert len(executor.sessions) == 2 and set(executor.sessions) == {""}


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


def test_forge_contract_deliberately_has_no_merge_operation() -> None:
    """@brief The conductor's remote capability cannot merge by construction."""
    assert not hasattr(Forge, "merge")


# END OF FILE
