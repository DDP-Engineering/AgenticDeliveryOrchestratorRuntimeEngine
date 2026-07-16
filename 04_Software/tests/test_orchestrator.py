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
@brief Tests for the thick-conductor engine (selection, gates, park/resume).
@details Every collaborator is faked (forge, executor, worktrees, containers)
         while the state store and config are real, so the deterministic
         state machine is exercised end to end offline: selection ordering,
         the per-gate loop with retries and budgets, the exact park sequence,
         resume detection (marker/system filtering, answered override), TTL
         reap, answer timeout, and reconciliation of deleted/closed tickets.
@author Eng. Dan Dumitru Pasare
@date 2026-07-03
@version 0.4.0
"""

from __future__ import annotations

# IMPORTS
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from adore import gates
from adore.config import Config, ExecutorCommand
from adore.executor.base import Executor, GateRun
from adore.forge import Comment, Forge, MergeRequest, Ticket
from adore.gates import GateResult
from adore.isolation import IsolationError
from adore.orchestrator import GATES, Orchestrator
from adore.state import RunState, StateStore
from adore.util import CommandResult
import pytest

# CONSTANTS

AC_BODY = "Do the thing.\n\n## Acceptance criteria\n- [ ] it works\n"

# DATA MODELS / TYPEDEFINITIONS


class FakeForge(Forge):
    """
    @brief   In-memory Git platform recording every call for order asserts.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.0
    """

    def __init__(self) -> None:
        """
        @brief   Empty platform.
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-03
        @version 0.1.1
        """
        self.tickets: dict[int, Ticket] = {}
        self.comments: dict[int, list[Comment]] = {}
        self.mrs: dict[int, MergeRequest] = {}
        self.mrs_by_branch: dict[str, int] = {}
        self.mr_comments: dict[int, list[Comment]] = {}
        self.mr_creations: list[dict] = []
        self.calls: list[tuple] = []
        self._next_comment_id = 100
        self._next_mr_iid = 0

    def add_ticket(self, iid: int, title: str = "T", body: str = AC_BODY,
                   labels: list[str] | None = None) -> Ticket:
        """
        @brief      Seed a ticket.
        @param[in]  iid Ticket id.
        @param[in]  title Title.
        @param[in]  body Description.
        @param[in]  labels Labels (default ready + P1).
        @return     The ticket.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        ticket = Ticket(iid=iid, title=title, description=body,
                        labels=labels if labels is not None else ["agent-ready", "P1"])
        self.tickets[iid] = ticket
        self.comments.setdefault(iid, [])
        return ticket

    def human_comment(self, iid: int, body: str) -> Comment:
        """
        @brief      Seed a human reply.
        @param[in]  iid Ticket id.
        @param[in]  body Comment body (no marker).
        @return     The comment.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        self._next_comment_id += 1
        comment = Comment(id=self._next_comment_id, body=body, author="human")
        self.comments.setdefault(iid, []).append(comment)
        return comment

    def list_ready(self, ready_label: str) -> list[Ticket]:
        self.calls.append(("list_ready", ready_label))
        return [t for t in self.tickets.values()
                if ready_label in t.labels and t.state == "opened"]

    def get_ticket(self, iid: int) -> Ticket | None:
        return self.tickets.get(iid)

    def list_comments(self, iid: int) -> list[Comment]:
        return list(self.comments.get(iid, []))

    def post_comment(self, iid: int, body: str) -> int:
        self._next_comment_id += 1
        self.comments.setdefault(iid, []).append(
            Comment(id=self._next_comment_id, body=body, author="bot")
        )
        self.calls.append(("post", iid, body))
        return self._next_comment_id

    def edit_comment(self, iid: int, comment_id: int, body: str) -> None:
        self.calls.append(("edit", iid, comment_id, body))

    def add_labels(self, iid: int, labels: list[str]) -> None:
        self.calls.append(("add_labels", iid, tuple(labels)))
        if iid in self.tickets:
            self.tickets[iid].labels.extend(labels)

    def remove_labels(self, iid: int, labels: list[str]) -> None:
        self.calls.append(("remove_labels", iid, tuple(labels)))
        if iid in self.tickets:
            self.tickets[iid].labels = [
                x for x in self.tickets[iid].labels if x not in labels
            ]

    def get_merge_request(self, ref: int | str) -> MergeRequest | None:
        if isinstance(ref, int):
            return self.mrs.get(ref)
        iid = self.mrs_by_branch.get(str(ref))
        mr = self.mrs.get(iid) if iid is not None else None
        # branch lookup only finds OPEN MRs (platform behavior)
        return mr if mr is not None and mr.state == "opened" else None

    def list_mr_comments(self, mr_iid: int) -> list[Comment]:
        return list(self.mr_comments.get(mr_iid, []))

    def remove_mr_labels(self, mr_iid: int, labels: list[str]) -> None:
        self.calls.append(("remove_mr_labels", mr_iid, tuple(labels)))
        if mr_iid in self.mrs:
            self.mrs[mr_iid].labels = [
                x for x in self.mrs[mr_iid].labels if x not in labels
            ]

    def open_merge_request(self, source, target, title, body, *, draft=True,
                           reviewers=None, remove_source_branch=True,
                           cwd=None) -> str:
        assert draft is True, "ADORE must only ever open DRAFT MRs"
        assert cwd, "MR creation needs a git checkout cwd (remote resolution)"
        self._next_mr_iid += 1
        url = f"https://gitlab.example/g/p/-/merge_requests/{self._next_mr_iid}"
        self.mrs[self._next_mr_iid] = MergeRequest(
            iid=self._next_mr_iid, state="opened", web_url=url, draft=True
        )
        self.mrs_by_branch[source] = self._next_mr_iid
        self.mr_creations.append({
            "source": source, "target": target, "title": title, "body": body,
            "reviewers": list(reviewers or []),
        })
        self.calls.append(("open_mr", source, target))
        return url


class FakeWorktrees:
    """
    @brief   Worktree manager double (interface subset the engine uses).
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.0
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.repo_path = root / "repo"
        self.removed: list[tuple[str, str | None]] = []
        self.remove_errors: list[Exception] = []  # raised (popped) before success
        self.touched = 0
        self.dirty = False
        self.ahead = 1
        self.fetched = 0
        self.merging = False
        self.merge_results: list[CommandResult] = []
        self.pushed: list[str] = []
        self.push_result = CommandResult(exit_code=0)
        self.delivery_commits: list[tuple[str, str]] = []

    def path_for(self, run_id: str) -> Path:
        return self.root / run_id

    def exists(self, run_id: str) -> bool:
        return (self.path_for(run_id) / ".git").exists()

    def create(self, run_id: str, branch: str, base_ref: str) -> Path:
        path = self.path_for(run_id)
        path.mkdir(parents=True, exist_ok=True)
        (path / ".git").write_text(f"gitdir: /x/.git/worktrees/{run_id}\n",
                                   encoding="utf-8")
        return path

    def admin_dir_name(self, run_id: str) -> str:
        return run_id

    def list_dirs(self) -> list[Path]:
        if not self.root.is_dir():
            return []
        return sorted(entry for entry in self.root.iterdir() if entry.is_dir())

    def remove(self, run_id: str, *, delete_branch: str | None = None) -> None:
        if self.remove_errors:
            raise self.remove_errors.pop(0)
        self.removed.append((run_id, delete_branch))

    def changed_files(self, run_id: str, base_ref: str) -> int:
        return self.touched

    def commit_all_if_dirty(self, run_id: str, message: str) -> bool:
        if not self.dirty:
            return False
        self.delivery_commits.append((run_id, message))
        self.dirty = False
        self.ahead += 1
        return True

    def is_dirty(self, run_id: str) -> bool:
        return self.dirty

    def commits_ahead(self, run_id: str, base_ref: str) -> int:
        return self.ahead

    def fetch(self, remote: str = "origin") -> None:
        self.fetched += 1

    def merge(self, run_id: str, ref: str) -> CommandResult:
        if self.merge_results:
            return self.merge_results.pop(0)
        return CommandResult(exit_code=0, stdout="Already up to date.")

    def merge_in_progress(self, run_id: str) -> bool:
        return self.merging

    def push(self, run_id: str, branch: str) -> CommandResult:
        self.pushed.append(branch)
        return self.push_result


class FakeContainers:
    """
    @brief   Container manager double; invariants results are scriptable.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.2.0
    """

    def __init__(self) -> None:
        self.states: dict[str, str] = {}
        self.events: list[tuple[str, str]] = []
        self.invariants_results: list[int] = []
        self.exec_calls: list[list[str]] = []
        self.exec_envs: list[dict[str, str] | None] = []
        self.provision_envs: list[dict[str, str]] = []
        self.tool_checks: list[str] = []
        self.tool_check_failure: str = ""
        self.report_output = "report"

    def status(self, name: str) -> str:
        return self.states.get(name, "absent")

    def ensure_volumes(self) -> None:
        self.events.append(("volumes", ""))

    def provision(self, name, repo_path, worktree_path, io_path, env) -> str:
        action = "created" if name not in self.states else (
            "running" if self.states[name] == "running" else "started"
        )
        self.states[name] = "running"
        self.events.append(("provision", name))
        self.provision_envs.append(dict(env))
        return action

    def verify_required_tools(self, name, checks, *, env=None) -> None:
        if not checks:
            return
        self.tool_checks.extend([str(check) for check in checks])
        self.exec_envs.append(dict(env) if env is not None else None)
        if self.tool_check_failure:
            raise IsolationError(self.tool_check_failure)

    def start(self, name: str) -> None:
        self.states[name] = "running"
        self.events.append(("start", name))

    def stop(self, name: str) -> None:
        self.states[name] = "exited"
        self.events.append(("stop", name))

    def remove(self, name: str) -> None:
        self.states.pop(name, None)
        self.events.append(("remove", name))

    def list_containers(self, prefix: str) -> list[str]:
        return [name for name in self.states if name.startswith(prefix)]

    def exec(self, name, argv, *, timeout=None, env=None) -> CommandResult:
        self.exec_calls.append([str(part) for part in argv])
        self.exec_envs.append(dict(env) if env is not None else None)
        if "invariants" in argv:
            code = self.invariants_results.pop(0) if self.invariants_results else 0
            return CommandResult(exit_code=code, stdout="invariants")
        if "report" in argv:
            return CommandResult(exit_code=0, stdout=self.report_output)
        return CommandResult(exit_code=0)


class FakeExecutor(Executor):
    """
    @brief   Executor double replaying scripted GateRuns; records prompts.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.0
    """

    def __init__(self, results: list[GateRun] | None = None) -> None:
        self.results = list(results or [])
        self.prompts: list[str] = []
        self.sessions: list[str] = []
        self.archive_stems: list[str] = []

    def run_gate(self, execute, worktree, io_dir, prompt, *,
                 session="", timeout=None, archive_stem="") -> GateRun:
        self.prompts.append(prompt)
        self.sessions.append(session)
        self.archive_stems.append(archive_stem)
        if self.results:
            return self.results.pop(0)
        return GateRun(exit_code=0, session_id="ses_1")


# HELPER FUNCTIONS


def make_config(tmp_path: Path, **overrides) -> Config:
    """
    @brief      A valid in-memory config rooted in the test tmp dir.
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  overrides Attribute overrides applied via section.key paths.
    @return     The Config.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.1
    """
    config = Config()
    config.agent.slug = "adore"
    config.agent.email = "adore-bot@local"
    config.platform.repo = "g/p"
    config.state.store_root = str(tmp_path / ".adore")
    config.worktree.repo_path = str(tmp_path / "repo")
    config.worktree.root = str(tmp_path / "worktrees")
    config.delivery.reviewers = ["r"]
    config.executor.questions_file = "ADORE_QUESTIONS.md"
    config.executor.commands["opencode"] = ExecutorCommand("x {prompt}", "m")
    config.metrics.db_path = str(tmp_path / ".adore" / "metrics.db")
    config.metrics.export_jsonl = str(tmp_path / ".adore" / "runs.jsonl")
    for path, value in overrides.items():
        section, key = path.split(".")
        setattr(getattr(config, section), key, value)
    return config


def make_engine(tmp_path: Path, executor: FakeExecutor | None = None,
                config: Config | None = None) -> tuple[Orchestrator, FakeForge,
                                                       FakeContainers, FakeWorktrees]:
    """
    @brief      Build an engine wired with fakes and a real state store.
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  executor Optional scripted executor.
    @param[in]  config Optional prebuilt config.
    @return     (engine, forge, containers, worktrees).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    config = config or make_config(tmp_path)
    forge = FakeForge()
    containers = FakeContainers()
    worktrees = FakeWorktrees(tmp_path / "wt")
    engine = Orchestrator(
        config=config,
        forge=forge,
        store=StateStore(config.state.store_root, config.agent.slug),
        worktrees=worktrees,  # type: ignore[arg-type]
        containers=containers,  # type: ignore[arg-type]
        executor=executor or FakeExecutor(),
        log=lambda line: None,
    )
    return engine, forge, containers, worktrees


def gate_ok(session: str = "ses_1") -> GateRun:
    """
    @brief      A clean gate result.
    @param[in]  session Session id carried forward.
    @return     The GateRun.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    return GateRun(exit_code=0, session_id=session)


def write_agentic_failure_evidence(
    engine: Orchestrator,
    run_id: str,
    *,
    agentic_run: str = "feature-20260708T010203Z-abcd1234",
    summary: str = "Focused pytest failed before the fix.",
    command: str = "pytest tests/test_widget.py::test_widget_renders",
    stderr_tail: str = "AssertionError: widget title missing",
    report: str = "## Invariants\n- `INV-4` FAIL (blocking): failing gate evidence",
) -> None:
    """
    @brief      Seed workflow-template failure artifacts in a fake worktree.
    @param[in]  engine Test engine whose fake worktree root is used.
    @param[in]  run_id ADORE run id.
    @param[in]  agentic_run Active workflow run id.
    @param[in]  summary Evidence summary.
    @param[in]  command Failed command.
    @param[in]  stderr_tail Failed command stderr tail.
    @param[in]  report Existing report.md text.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-08
    @version    0.1.1
    """
    worktree = engine.worktrees.path_for(run_id)  # type: ignore[attr-defined]
    run_dir = worktree / ".agentic" / "runs" / agentic_run
    run_dir.mkdir(parents=True, exist_ok=True)
    (worktree / ".agentic" / "current_run").write_text(agentic_run, encoding="utf-8")
    graph = {
        "evidence": [
            {
                "id": "E-0007",
                "kind": "test-run",
                "result": "fail",
                "status": "active",
                "summary": summary,
                "command": command,
                "stage": "validation",
            }
        ]
    }
    (run_dir / "graph.json").write_text(
        json.dumps(graph, indent=2) + "\n", encoding="utf-8"
    )
    journal = {
        "event": "gate.output",
        "data": {
            "gate": "test",
            "command": command,
            "returncode": 1,
            "stdout_tail": "collected 1 item",
            "stderr_tail": stderr_tail,
        },
    }
    (run_dir / "journal.jsonl").write_text(
        json.dumps(journal) + "\n", encoding="utf-8"
    )
    (run_dir / "report.md").write_text(report, encoding="utf-8")


def park_run(engine: Orchestrator, forge: FakeForge, iid: int = 14) -> str:
    """
    @brief      Drive a ticket into the parked state via a questions gate.
    @param[in]  engine The engine (its executor must be a FakeExecutor).
    @param[in]  forge The fake forge.
    @param[in]  iid Ticket id.
    @return     The run id.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    forge.add_ticket(iid)
    engine.executor.results = [
        GateRun(exit_code=0, has_questions=True, questions="1. Which variant?",
                session_id="ses_q")
    ]
    engine.poll_once()
    return engine._run_id(iid)


def ago(seconds: int) -> str:
    """
    @brief      An ISO timestamp N seconds in the past.
    @param[in]  seconds Age.
    @return     The timestamp string.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    return (datetime.now(UTC) - timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


# PUBLIC API / TESTS


def test_pick_and_conduct_all_gates_to_validated(tmp_path: Path) -> None:
    """
    @brief   Happy path: one eligible ticket runs all five gates, invariants
             verified between, ends validated with delivery pending.
    @version 0.1.0
    """
    executor = FakeExecutor([gate_ok(f"ses_{i}") for i in range(6)])
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14, title="Refresh button")
    summary = engine.poll_once()
    assert summary["picked"] == 14
    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "in-review"
    assert run.stage == "delivery"
    assert run.mr_iid == 1 and "/merge_requests/1" in run.mr_url
    assert run.executor_session == "ses_5"
    assert executor.sessions == ["", "ses_0", "ses_1", "ses_2", "ses_3", "ses_4"]
    assert executor.archive_stems == [
        "001-intake",
        "002-alignment",
        "003-requirement",
        "004-check",
        "005-implementation",
        "006-validation",
    ]
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert events.count("gate-passed") == 6
    assert "validation-complete" in events
    # ticket snapshot saved; ONE status comment (edited in place) plus ONE
    # kind=delivery comment with the MR link
    assert engine.store.load_ticket(run.run_id)["iid"] == 14
    posts = [c for c in forge.calls if c[0] == "post"]
    edits = [c for c in forge.calls if c[0] == "edit"]
    assert len(posts) == 2 and len(edits) >= 4
    assert any("kind=delivery" in c[2] and run.mr_url in c[2] for c in posts)
    assert containers.events[-1] == ("stop", run.container)  # retained, not removed


def test_executor_artifacts_are_journaled(tmp_path: Path) -> None:
    """
    @brief   GateRun artifact archive paths are surfaced through the run
             journal so `adore logs <run-id>` points at raw evidence.
    @version 0.1.1
    """
    executor = FakeExecutor([
        GateRun(exit_code=1, stderr="boom", artifact_dirs=[".adore/runs/r/io/archive/a"])
    ])
    config = make_config(tmp_path)
    config.budgets.max_iterations = 1
    engine, forge, _, _ = make_engine(tmp_path, executor, config)
    forge.add_ticket(14)

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    artifact_events = [
        event for event in engine.store.read_journal(run.run_id)
        if event["event"] == "executor-artifacts"
    ]
    assert len(artifact_events) == 1
    assert artifact_events[0]["context"] == "intake"
    assert artifact_events[0]["artifacts"] == [".adore/runs/r/io/archive/a"]


def test_selection_priority_and_filters(tmp_path: Path) -> None:
    """
    @brief   Control labels always win, readiness rejects missing priority /
             acceptance criteria, and P1 beats P2.
    @version 0.1.0
    """
    engine, forge, _, _ = make_engine(tmp_path)
    forge.add_ticket(1, labels=["agent-ready", "P2"])
    forge.add_ticket(2, labels=["agent-ready", "P1"])
    forge.add_ticket(3, labels=["agent-ready", "P1", "agent-hold"])
    forge.add_ticket(4, labels=["agent-ready"])                      # no priority
    forge.add_ticket(5, labels=["agent-ready", "P1"], body="no ac")  # no criteria
    forge.add_ticket(6, labels=["agent-ready", "P1", "no-agent"])
    summary = engine.poll_once(dry_run=True)
    assert summary["picked"] == 2


def test_existing_run_is_never_picked_again(tmp_path: Path) -> None:
    """
    @brief   Idempotent recovery (design 8): a ticket with persisted run
             state is skipped on every later poll.
    @version 0.1.0
    """
    engine, forge, _, _ = make_engine(tmp_path)
    forge.add_ticket(14)
    engine.store.save(RunState(run_id=engine._run_id(14), ticket_iid=14,
                               lifecycle="working"))
    summary = engine.poll_once(dry_run=True)
    assert summary["picked"] is None


def test_park_sequence_question_comment_first(tmp_path: Path) -> None:
    """
    @brief   Park order (design 9): the questions comment is posted BEFORE
             the parked status marking, ids are recorded, and the container
             is stopped, not removed.
    @version 0.1.0
    """
    engine, forge, containers, _ = make_engine(tmp_path, FakeExecutor())
    run_id = park_run(engine, forge)
    run = engine.store.load(run_id)
    assert run.lifecycle == "parked"
    assert run.clarification_rounds == 1
    assert run.question_comment_id == run.last_seen_comment_id
    question_posts = [
        i for i, c in enumerate(forge.calls)
        if c[0] == "post" and "kind=question" in c[2]
    ]
    parked_marks = [
        i for i, c in enumerate(forge.calls)
        if c[0] == "edit" and "parked" in c[3]
    ]
    assert question_posts and parked_marks
    assert question_posts[0] < parked_marks[0]  # crash-safe ordering
    assert ("stop", run.container) in containers.events
    assert ("remove", run.container) not in containers.events


def test_resume_ignores_system_and_own_comments(tmp_path: Path) -> None:
    """
    @brief   Resume detection: system notes and marker-stamped comments never
             resume; a plain human reply does, and the executor gets the
             thread.
    @version 0.1.1
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor())
    run_id = park_run(engine, forge)
    forge.comments[14].append(Comment(id=990, body="label change", system=True))
    forge.comments[14].append(Comment(
        id=991, body="ours\n<!-- adore:run=x kind=status -->"))
    # ids above are BELOW the question id, plus one system note above it:
    forge.comments[14].append(Comment(id=99999, body="sys", system=True))
    summary = engine.poll_once()
    assert summary["resumed"] == 0
    forge.human_comment(14, "Use variant B please")
    forge.comments[14][-1] = Comment(id=100000, body="Use variant B please",
                                     author="dan")
    engine.executor.results = [gate_ok()] * 5
    summary = engine.poll_once()
    assert summary["resumed"] == 1
    run = engine.store.load(run_id)
    assert run.lifecycle == "in-review"
    resumed_prompt = engine.executor.prompts[1]
    assert "Use variant B please" in resumed_prompt
    assert "Clarification thread" in resumed_prompt


def test_answered_label_forces_resume(tmp_path: Path) -> None:
    """
    @brief   The manual agent-answered label resumes without any comment and
             is cleared afterwards.
    @version 0.1.0
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor())
    park_run(engine, forge)
    forge.tickets[14].labels.append("agent-answered")
    engine.executor.results = [gate_ok()] * 5
    summary = engine.poll_once()
    assert summary["resumed"] == 1
    assert ("remove_labels", 14, ("agent-answered",)) in forge.calls


def test_round_cap_escalates_to_failed(tmp_path: Path) -> None:
    """
    @brief   Exceeding max clarification rounds escalates instead of parking
             forever.
    @version 0.1.0
    """
    config = make_config(tmp_path)
    config.clarification.max_rounds = 1
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor(), config)
    run_id = park_run(engine, forge)  # round 1: parked
    forge.human_comment(14, "answer one")
    engine.executor.results = [
        GateRun(exit_code=0, has_questions=True, questions="again?")
    ]
    engine.poll_once()  # resume -> asks again -> round 2 > max 1 -> failed
    run = engine.store.load(run_id)
    assert run.lifecycle == "failed"
    assert "clarification" in run.outcome


def test_gate_failure_retries_with_context_until_budget(tmp_path: Path) -> None:
    """
    @brief   A failing gate is relaunched with the failure context and the
             iterations budget ends the thrashing.
    @version 0.1.0
    """
    config = make_config(tmp_path)
    config.budgets.max_iterations = 3
    executor = FakeExecutor([
        GateRun(exit_code=1, stderr="boom-1"),
        GateRun(exit_code=1, stderr="boom-2"),
        GateRun(exit_code=1, stderr="boom-3"),
    ])
    engine, forge, _, _ = make_engine(tmp_path, executor, config)
    forge.add_ticket(14)
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "iterations" in run.outcome
    assert len(executor.prompts) == 3
    assert "previous attempt of this gate failed" in executor.prompts[1]
    assert "boom-1" in executor.prompts[1]


def test_gate_failure_retry_prompt_includes_agentic_evidence(tmp_path: Path) -> None:
    """
    @brief   When a gate fails, the retry prompt includes existing `.agentic`
             failure evidence, not only the executor stderr tail.
    @version 0.1.0
    """
    config = make_config(tmp_path)
    config.budgets.max_iterations = 2
    executor = FakeExecutor([
        GateRun(exit_code=1, stderr="executor stderr was vague"),
        GateRun(exit_code=1, stderr="still failing"),
    ])
    engine, forge, _, _ = make_engine(tmp_path, executor, config)
    forge.add_ticket(14)
    run_id = engine._run_id(14)
    write_agentic_failure_evidence(engine, run_id)

    engine.poll_once()

    retry_prompt = executor.prompts[1]
    assert "previous attempt of this gate failed" in retry_prompt
    assert "executor stderr was vague" in retry_prompt
    assert "Agentic failure evidence" in retry_prompt
    assert "E-0007 test-run stage=validation" in retry_prompt
    assert "pytest tests/test_widget.py::test_widget_renders" in retry_prompt
    assert "AssertionError: widget title missing" in retry_prompt


def test_missing_agentic_current_run_is_skipped(tmp_path: Path) -> None:
    """
    @brief   Missing `.agentic/current_run` is a normal no-evidence case; the
             retry prompt still carries the original stderr context.
    @version 0.1.0
    """
    config = make_config(tmp_path)
    config.budgets.max_iterations = 2
    executor = FakeExecutor([
        GateRun(exit_code=1, stderr="stderr only"),
        GateRun(exit_code=1, stderr="still failing"),
    ])
    engine, forge, _, _ = make_engine(tmp_path, executor, config)
    forge.add_ticket(14)

    engine.poll_once()

    retry_prompt = executor.prompts[1]
    assert "stderr only" in retry_prompt
    assert "Agentic failure evidence" not in retry_prompt


def test_invalid_agentic_run_id_reports_unavailable(tmp_path: Path) -> None:
    """
    @brief   `.agentic/current_run` must be one path segment; traversal-like
             values are reported instead of read.
    @version 0.1.0
    """
    config = make_config(tmp_path)
    config.budgets.max_iterations = 2
    executor = FakeExecutor([
        GateRun(exit_code=1, stderr="bad run id"),
        GateRun(exit_code=1, stderr="still failing"),
    ])
    engine, forge, _, _ = make_engine(tmp_path, executor, config)
    forge.add_ticket(14)
    worktree = engine.worktrees.path_for(engine._run_id(14))  # type: ignore[attr-defined]
    (worktree / ".agentic").mkdir(parents=True, exist_ok=True)
    (worktree / ".agentic" / "current_run").write_text("../escape", encoding="utf-8")

    engine.poll_once()

    assert "invalid .agentic/current_run value" in executor.prompts[1]


def test_malformed_graph_and_torn_journal_do_not_break_evidence_prompt(
    tmp_path: Path,
) -> None:
    """
    @brief   Malformed graph evidence is reported, while a torn journal line is
             skipped and intact gate-output evidence is still used.
    @version 0.1.0
    """
    config = make_config(tmp_path)
    config.budgets.max_iterations = 2
    executor = FakeExecutor([
        GateRun(exit_code=1, stderr="malformed graph"),
        GateRun(exit_code=1, stderr="still failing"),
    ])
    engine, forge, _, _ = make_engine(tmp_path, executor, config)
    forge.add_ticket(14)
    worktree = engine.worktrees.path_for(engine._run_id(14))  # type: ignore[attr-defined]
    run_dir = worktree / ".agentic" / "runs" / "run-1"
    run_dir.mkdir(parents=True, exist_ok=True)
    (worktree / ".agentic" / "current_run").write_text("run-1", encoding="utf-8")
    (run_dir / "graph.json").write_text("{", encoding="utf-8")
    journal = {
        "event": "gate.output",
        "data": {
            "gate": "lint",
            "command": "ruff check .",
            "returncode": 1,
            "stderr_tail": "E501 line too long",
        },
    }
    (run_dir / "journal.jsonl").write_text(
        json.dumps(journal) + "\n" + '{"event": "gate.output"', encoding="utf-8"
    )

    engine.poll_once()

    retry_prompt = executor.prompts[1]
    assert "could not parse failure evidence" in retry_prompt
    assert "lint exit 1: ruff check ." in retry_prompt
    assert "E501 line too long" in retry_prompt


def test_failure_context_redacts_configured_executor_secrets(tmp_path: Path) -> None:
    """
    @brief   Exact configured secret values are redacted from stderr, graph,
             journal, and report evidence before they enter retry prompts.
    @version 0.1.0
    """
    secret = "sk-secret-1234"
    config = make_config(tmp_path)
    config.budgets.max_iterations = 2
    executor = FakeExecutor([
        GateRun(exit_code=1, stderr=f"executor leaked {secret}"),
        GateRun(exit_code=1, stderr="still failing"),
    ])
    engine, forge, _, _ = make_engine(tmp_path, executor, config)
    engine.secrets = {"OPENAI_API_KEY": secret}
    forge.add_ticket(14)
    write_agentic_failure_evidence(
        engine,
        engine._run_id(14),
        summary=f"Secret showed up in output: {secret}",
        command=f"pytest --token {secret}",
        stderr_tail=f"traceback included {secret}",
        report=f"## Invariants\n- FAIL: leaked {secret}",
    )

    engine.poll_once()

    retry_prompt = executor.prompts[1]
    assert secret not in retry_prompt
    assert "[REDACTED]" in retry_prompt


def test_invariants_failure_relaunches_same_gate(tmp_path: Path) -> None:
    """
    @brief   The conductor's own verification gates advancement: a failing
             invariants check relaunches the gate with that context.
    @version 0.1.0
    """
    executor = FakeExecutor([gate_ok()] * 7)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    containers.invariants_results = [1, 0, 0, 0, 0, 0, 0]
    forge.add_ticket(14)
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "in-review"
    assert len(executor.prompts) == 7  # intake twice, then five gates once
    assert "invariants check failed" in executor.prompts[1]
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert "invariants-failed" in events


def test_parked_ttl_reaps_container_but_keeps_run(tmp_path: Path) -> None:
    """
    @brief   TTL reap frees the container; the run stays parked and
             answerable (design 8b: reap != timeout).
    @version 0.1.0
    """
    config = make_config(tmp_path)
    config.container.parked_ttl_polls = 1
    engine, forge, containers, _ = make_engine(tmp_path, FakeExecutor(), config)
    run_id = park_run(engine, forge)
    summary = engine.poll_once()
    assert summary["reaped"] == 1
    run = engine.store.load(run_id)
    assert run.lifecycle == "parked"
    assert ("remove", run.container) in containers.events


def test_answer_timeout_releases_the_ticket(tmp_path: Path) -> None:
    """
    @brief   Past answer_timeout the run ends terminal, the worktree goes,
             state stays, and a closing comment is posted; the reminder
             posted once before it.
    @version 0.1.0
    """
    engine, forge, _, worktrees = make_engine(tmp_path, FakeExecutor())
    run_id = park_run(engine, forge)
    run = engine.store.load(run_id)
    run.parked_at = ago(300000)  # > 72h
    engine.store.save(run)
    summary = engine.poll_once()
    assert summary["timed_out"] == 1
    run = engine.store.load(run_id)
    assert run.lifecycle == "failed"
    assert run.outcome == "answer-timeout"
    assert (run_id, run.branch) in worktrees.removed
    bodies = [c[2] for c in forge.calls if c[0] == "post"]
    assert any("releasing this ticket" in b for b in bodies)
    assert engine.store.exists(run_id)  # audit state kept


def test_paused_and_capacity_block_pickup(tmp_path: Path) -> None:
    """
    @brief   Pause stops pickup entirely; max_concurrent_runs bounds
             parallelism (resume checks still run in both cases).
    @version 0.1.0
    """
    engine, forge, _, _ = make_engine(tmp_path)
    forge.add_ticket(14)
    engine.store.pause()
    summary = engine.poll_once()
    assert summary.get("paused") is True
    assert summary["picked"] is None
    engine.store.resume()
    engine.store.save(RunState(run_id="other-run", ticket_iid=99,
                               lifecycle="working"))
    summary = engine.poll_once()
    assert summary.get("at_capacity") is True


def test_deleted_and_closed_tickets_reconcile(tmp_path: Path) -> None:
    """
    @brief   A deleted ticket orphans the run (full teardown); a closed one
             cancels it gracefully (design 8c).
    @version 0.1.0
    """
    engine, forge, _, worktrees = make_engine(tmp_path, FakeExecutor())
    run_id = park_run(engine, forge)
    del forge.tickets[14]
    engine.poll_once()
    run = engine.store.load(run_id)
    assert run.outcome == "orphaned"
    assert (run_id, run.branch) in worktrees.removed

    engine2, forge2, _, _ = make_engine(tmp_path / "b", FakeExecutor())
    run_id2 = park_run(engine2, forge2)
    forge2.tickets[14].state = "closed"
    engine2.poll_once()
    assert engine2.store.load(run_id2).outcome == "ticket-closed"


def test_cancel_and_retry_roundtrip(tmp_path: Path) -> None:
    """
    @brief   cancel tears down but keeps state; retry re-arms and conducts
             from the stored stage to completion.
    @version 0.1.0
    """
    engine, forge, containers, worktrees = make_engine(tmp_path, FakeExecutor())
    run_id = park_run(engine, forge)
    assert engine.cancel(run_id) is True
    run = engine.store.load(run_id)
    assert run.outcome == "cancelled"
    assert (run_id, run.branch) in worktrees.removed
    assert engine.cancel("nope") is False

    engine.executor.results = [gate_ok()] * 6
    assert engine.retry(run_id) is True
    assert engine.store.load(run_id).lifecycle == "in-review"


def test_labels_channel_transitions(tmp_path: Path) -> None:
    """
    @brief   With channel=labels the lifecycle labels move with the run and
             no status comment is posted.
    @version 0.1.0
    """
    config = make_config(tmp_path)
    config.state.channel = "labels"
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor(), config)
    park_run(engine, forge)
    label_calls = [c for c in forge.calls if c[0] in ("add_labels", "remove_labels")]
    assert ("add_labels", 14, ("agent-working",)) in label_calls
    assert ("add_labels", 14, ("agent-clarify",)) in label_calls
    status_edits = [c for c in forge.calls if c[0] == "edit"]
    assert status_edits == []  # comments channel off
    # the question comment itself still posts (it is content, not status)
    assert any("kind=question" in c[2] for c in forge.calls if c[0] == "post")


def test_stage_host_auth_copies_and_scrubs(tmp_path: Path) -> None:
    """
    @brief   With stage_host_auth on, the host auth.json goes through the io
             mount into the container and is scrubbed from io immediately; a
             missing host file only logs.
    @version 0.1.1
    """
    config = make_config(tmp_path)
    config.executor.stage_host_auth = True
    engine, forge, containers, _ = make_engine(tmp_path, FakeExecutor([gate_ok()] * 5),
                                               config)
    auth = tmp_path / "auth.json"
    auth.write_text('{"openai":{"type":"oauth"}}', encoding="utf-8")
    engine.host_auth_path = auth
    forge.add_ticket(14)
    engine.poll_once()
    run_id = engine._run_id(14)
    cp_calls = [c for c in containers.exec_calls if c and c[0] == "cp"]
    assert ["cp", "/adore/io/host-auth.json",
            "/home/adore/.local/share/opencode/auth.json"] in cp_calls
    assert not (engine._io_dir(run_id) / "host-auth.json").exists()  # scrubbed
    events = [e["event"] for e in engine.store.read_journal(run_id)]
    assert "host-auth-staged" in events


def test_stage_host_auth_off_by_default_and_missing_file(tmp_path: Path) -> None:
    """
    @brief   Default off: no staging exec happens; on-but-missing logs and
             continues (the executor fails visibly later, not silently).
    @version 0.1.0
    """
    engine, forge, containers, _ = make_engine(tmp_path, FakeExecutor([gate_ok()] * 5))
    forge.add_ticket(14)
    engine.poll_once()
    assert not any(c and c[0] == "cp" for c in containers.exec_calls)

    config = make_config(tmp_path / "m")
    config.executor.stage_host_auth = True
    logged: list[str] = []
    engine2, forge2, containers2, _ = make_engine(tmp_path / "m",
                                                  FakeExecutor([gate_ok()] * 5), config)
    engine2.log = logged.append
    engine2.host_auth_path = tmp_path / "m" / "missing-auth.json"
    forge2.add_ticket(14)
    engine2.poll_once()
    assert not any(c and c[0] == "cp" for c in containers2.exec_calls)
    assert any("missing" in line for line in logged)


def test_host_auth_path_is_per_executor(tmp_path: Path) -> None:
    """
    @brief   The OAuth-bridge source + container dir follow the configured
             executor; Codex host auth is copied into ADORE's isolated
             container CODEX_HOME.
    @version 0.1.1
    """
    opencode_engine, _, _, _ = make_engine(tmp_path)
    assert opencode_engine.host_auth_container_dir.endswith("opencode")
    assert str(opencode_engine.host_auth_path).endswith("auth.json")

    codex_config = make_config(tmp_path / "cx", **{"executor.default": "codex"})
    codex_engine, _, _, _ = make_engine(tmp_path / "cx", config=codex_config)
    assert codex_engine.host_auth_container_dir == "/home/adore/.adore-codex"
    assert str(codex_engine.host_auth_path).replace("\\", "/").endswith(".codex/auth.json")


def test_codex_provision_uses_isolated_codex_home(tmp_path: Path) -> None:
    """
    @brief   Selecting the Codex executor injects an ADORE-owned CODEX_HOME;
             opencode does not receive Codex-specific environment.
    @version 0.1.1
    """
    codex_config = make_config(tmp_path / "cx", **{"executor.default": "codex"})
    engine, forge, containers, _ = make_engine(tmp_path / "cx",
                                               FakeExecutor([gate_ok()] * 5),
                                               codex_config)
    forge.add_ticket(14)
    engine.poll_once()
    assert containers.provision_envs[-1]["CODEX_HOME"] == "/home/adore/.adore-codex"

    opencode_engine, opencode_forge, opencode_containers, _ = make_engine(
        tmp_path / "op", FakeExecutor([gate_ok()] * 5)
    )
    opencode_forge.add_ticket(14)
    opencode_engine.poll_once()
    assert "CODEX_HOME" not in opencode_containers.provision_envs[-1]


def test_runtime_env_reaches_provision_and_exec(tmp_path: Path) -> None:
    """
    @brief   Non-secret [container] runtime_env values are injected on both
             container creation and exec calls, so wrapped runtimes do not
             drop them between gate launches.
    @version 0.1.0
    """
    config = make_config(tmp_path, **{"container.runtime_env": {"UV_LINK_MODE": "copy"}})
    engine, forge, containers, _ = make_engine(tmp_path, FakeExecutor([gate_ok()] * 5),
                                               config)
    forge.add_ticket(14)
    engine.poll_once()
    assert containers.provision_envs[-1]["UV_LINK_MODE"] == "copy"
    assert any(env and env["UV_LINK_MODE"] == "copy" for env in containers.exec_envs)


def test_required_tool_checks_run_after_provision(tmp_path: Path) -> None:
    """
    @brief   Project-image required tool checks run immediately after the
             container is provisioned and use the same runtime env as gates.
    @version 0.1.0
    """
    config = make_config(
        tmp_path,
        **{
            "container.required_tool_checks": ["make --version", "tflint --version"],
            "container.runtime_env": {"UV_LINK_MODE": "copy"},
        },
    )
    engine, forge, containers, _ = make_engine(tmp_path, FakeExecutor([gate_ok()] * 6),
                                               config)
    forge.add_ticket(14)
    engine.poll_once()
    assert containers.tool_checks[:2] == ["make --version", "tflint --version"]
    assert len(containers.tool_checks) >= 2
    assert any(env and env["UV_LINK_MODE"] == "copy" for env in containers.exec_envs)


def test_required_tool_check_failure_fails_run_closed(tmp_path: Path) -> None:
    """
    @brief   A missing project-image tool escalates the run before the
             executor spends any gate iterations.
    @version 0.1.0
    """
    config = make_config(
        tmp_path,
        **{"container.required_tool_checks": ["terraform --version"]},
    )
    executor = FakeExecutor([gate_ok()] * 6)
    engine, forge, containers, _ = make_engine(tmp_path, executor, config)
    containers.tool_check_failure = "required tool check failed: terraform --version"
    forge.add_ticket(14)
    engine.poll_once()
    run = engine.store.list_runs()[0]
    assert run.lifecycle == "failed"
    assert "isolation failed" in run.outcome
    assert "terraform --version" in run.outcome
    assert executor.prompts == []


def test_uncommitted_work_relaunches_validation(tmp_path: Path) -> None:
    """
    @brief   A passing validation gate with a dirty tree (or zero commits) is
             NOT complete: validation relaunches with commit instructions
             until the work is committed (pilot finding 2026-07-03).
    @version 0.1.0
    """
    executor = FakeExecutor([gate_ok()] * 8)
    engine, forge, _, worktrees = make_engine(tmp_path, executor)
    worktrees.dirty = True
    forge.add_ticket(14)

    def commit_on_seventh() -> None:
        # called before the prompt is recorded: 6 recorded = 7th launch
        if len(executor.prompts) >= 6:
            worktrees.dirty = False

    original = executor.run_gate

    def run_gate(*args, **kwargs):
        commit_on_seventh()
        return original(*args, **kwargs)

    executor.run_gate = run_gate  # type: ignore[method-assign]
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "in-review"
    assert len(executor.prompts) == 7  # six gates + one validation relaunch
    assert "UNCOMMITTED" in executor.prompts[6]
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert "work-uncommitted" in events


def test_empty_branch_relaunches_validation_until_budget(tmp_path: Path) -> None:
    """
    @brief   Zero commits over base keeps relaunching validation and the
             iterations budget eventually escalates - never a hollow
             "validated".
    @version 0.1.0
    """
    config = make_config(tmp_path)
    config.budgets.max_iterations = 8
    engine, forge, _, worktrees = make_engine(tmp_path, FakeExecutor(), config)
    worktrees.ahead = 0
    forge.add_ticket(14)
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "iterations" in run.outcome


def test_branch_template_supports_repo_conventions(tmp_path: Path) -> None:
    """
    @brief   A "feature/" branch convention is one config line; the default
             stays slug/run-id (pilot finding 2026-07-03: GitLab push rules
             may require a feature/ prefix).
    @version 0.1.1
    """
    config = make_config(tmp_path)
    config.worktree.branch_template = "feature/{slug}-{iid}"
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor([gate_ok()] * 6), config)
    forge.add_ticket(14)
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    assert run.branch == "feature/adore-14"


def test_branch_template_must_stay_unique(tmp_path: Path) -> None:
    """
    @brief   A template without {run_id}/{iid} would collide across tickets;
             validation rejects it.
    @version 0.1.1
    """
    from adore.config import validate_config

    config = make_config(tmp_path)
    config.worktree.branch_template = "feature/adore"
    issues = validate_config(config)
    assert any("branch_template" in issue for issue in issues)


def test_branch_rule_checks_the_rendered_template(tmp_path: Path) -> None:
    """
    @brief   With the repo push rule configured, validation accepts a
             compliant template, rejects one the rule would reject, and
             flags an invalid regex - so a push-rule surprise cannot reach a
             run.
    @version 0.1.1
    """
    from adore.config import validate_config

    rule = r"^(feature|bugfix|release|hotfix)\/.*$"
    config = make_config(tmp_path)
    config.worktree.branch_rule = rule
    config.worktree.branch_template = "feature/{slug}-{iid}"
    assert not any("branch" in i for i in validate_config(config))

    config.worktree.branch_template = "{slug}/{run_id}"  # no feature/ prefix
    issues = validate_config(config)
    assert any("REJECT" in i for i in issues)

    config.worktree.branch_rule = "(unclosed"
    issues = validate_config(config)
    assert any("not a valid regex" in i for i in issues)


def test_files_budget_ignores_in_progress_merge(tmp_path: Path) -> None:
    """
    @brief   Staged upstream files during a target merge never trip the
             files-touched budget (live finding 2026-07-03); the executor
             gets to resolve the conflict instead.
    @version 0.1.0
    """
    config = make_config(tmp_path)
    config.budgets.max_files_touched = 3
    engine, forge, _, worktrees = make_engine(tmp_path, FakeExecutor([gate_ok()] * 7),
                                              config)
    worktrees.merge_results = [CommandResult(exit_code=1, stdout="CONFLICT")]
    worktrees.touched = 18  # what a half-merged upstream looks like

    def resolve_and_clear() -> None:
        if any("merge conflicts" in p for p in engine.executor.prompts):
            worktrees.merging = False
            worktrees.touched = 2

    worktrees.merging = False
    original = engine.executor.run_gate

    def run_gate(*args, **kwargs):
        result = original(*args, **kwargs)
        resolve_and_clear()
        return result

    engine.executor.run_gate = run_gate  # type: ignore[method-assign]

    forge.add_ticket(14)
    worktrees.merging = True  # conflict leaves the merge open
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "in-review"  # not "budget exceeded"


def test_retry_of_delivery_stage_never_restarts_the_gates(tmp_path: Path) -> None:
    """
    @brief   Retrying a run that failed during delivery resumes the delivery
             sequence; it must not re-run intake..validation (live finding
             2026-07-03).
    @version 0.1.1
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor())
    forge.add_ticket(14)
    run_id = engine._run_id(14)
    engine.store.save(RunState(
        run_id=run_id, ticket_iid=14, stage="delivery", lifecycle="failed",
        branch="feature/adore-14", base_ref="origin/develop",
        container=f"c-{run_id}", outcome="push failed: x",
    ))
    assert engine.retry(run_id) is True
    run = engine.store.load(run_id)
    assert run.lifecycle == "in-review"
    assert engine.executor.prompts == []  # no gate relaunched; pure delivery
    assert forge.mr_creations[0]["source"] == "feature/adore-14"


def test_conduct_with_unknown_stage_fails_closed(tmp_path: Path) -> None:
    """
    @brief   _conduct with a stage outside GATES escalates instead of
             silently restarting from intake (live finding 2026-07-04: a
             delivery run regressed to intake and burned gates).
    @version 0.1.0
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor())
    ticket = forge.add_ticket(14)
    run = RunState(run_id="r", ticket_iid=14, stage="bogus-stage",
                   container="c-r", branch="b")
    engine.store.save(run)
    engine._conduct(run, ticket)
    assert engine.store.load("r").lifecycle == "failed"
    assert engine.executor.prompts == []


def test_resume_of_delivery_stage_park_continues_delivery(tmp_path: Path) -> None:
    """
    @brief   A run parked DURING delivery resumes into the delivery sequence
             with the thread - never back to intake (live finding 2026-07-04).
    @version 0.1.1
    """
    engine, forge, _, worktrees = make_engine(tmp_path, FakeExecutor())
    forge.add_ticket(14)
    run_id = engine._run_id(14)
    worktrees.create(run_id, "feature/adore-14", "x")
    engine.store.save(RunState(
        run_id=run_id, ticket_iid=14, stage="delivery", lifecycle="parked",
        branch="feature/adore-14", base_ref="origin/develop",
        container=f"c-{run_id}", question_comment_id=500,
        parked_at=ago(60), clarification_rounds=1,
    ))
    forge.comments[14] = [Comment(id=501, body="tflint installed, go ahead",
                                  author="dan")]
    summary = engine.poll_once()
    assert summary["resumed"] == 1
    run = engine.store.load(run_id)
    assert run.lifecycle == "in-review"
    assert engine.executor.prompts == []  # no gate restarted from intake
    assert forge.mr_creations  # delivery completed


def test_resume_resets_the_active_work_budgets(tmp_path: Path) -> None:
    """
    @brief   Parked time is answer-wait, not work: an old created_at must not
             trip the wall clock on resume (live finding 2026-07-04: an 8h
             park escalated instantly).
    @version 0.1.0
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor())
    run_id = park_run(engine, forge)
    run = engine.store.load(run_id)
    run.created_at = ago(999999)  # far beyond max_wall_clock_seconds
    run.iterations = 5
    engine.store.save(run)
    forge.human_comment(14, "answer")
    engine.executor.results = [gate_ok()] * 6
    engine.poll_once()
    run = engine.store.load(run_id)
    assert run.lifecycle == "in-review"  # not "budget exceeded: wall clock"


def test_recreated_container_resets_the_executor_session(tmp_path: Path) -> None:
    """
    @brief   Executor sessions live inside the container: after a reap the
             resumed run must NOT pass the dead session id (live finding
             2026-07-03: "Session not found" thrash).
    @version 0.1.0
    """
    engine, forge, containers, _ = make_engine(tmp_path, FakeExecutor())
    run_id = park_run(engine, forge)  # stored session: ses_q
    containers.remove(engine.store.load(run_id).container)  # TTL reap
    forge.human_comment(14, "answer")
    engine.executor.results = [gate_ok()] * 6
    engine.poll_once()
    # resume relaunches: the dead session must have been cleared first
    assert engine.executor.sessions[1] == ""
    events = [e["event"] for e in engine.store.read_journal(run_id)]
    assert "session-reset" in events


def test_mr_description_truncates_on_line_boundaries(tmp_path: Path) -> None:
    """
    @brief   Long evidence blocks in the MR description are tail-truncated
             at LINE boundaries with a marker - never mid-line fragments like
             `g",` (MR !29 review finding 2026-07-04).
    @version 0.1.0
    """
    engine, forge, containers, _ = make_engine(tmp_path, FakeExecutor([gate_ok()] * 6))
    containers.report_output = "\n".join(
        f"- `E-{i:04}` gate/pass: line {i}" for i in range(200)
    )
    forge.add_ticket(14)
    engine.poll_once()
    body = forge.mr_creations[0]["body"]
    report_block = body.split("### Workflow report\n```\n")[1].split("\n```")[0]
    lines = report_block.splitlines()
    assert lines[0] == "[... truncated ...]"
    assert lines[1].startswith("- `E-")  # complete line, bullet intact
    assert lines[-1].startswith("- `E-0199`")


# PUBLIC API / TESTS - delivery (design 11a/11b)


def test_delivery_sequence_and_draft_mr(tmp_path: Path) -> None:
    """
    @brief   The 11a order: fetch, merge target, push, DRAFT MR with
             reviewers, kind=delivery comment, in-review with the container
             retained (stopped) and the worktree kept.
    @version 0.1.0
    """
    engine, forge, containers, worktrees = make_engine(
        tmp_path, FakeExecutor([gate_ok()] * 6)
    )
    forge.add_ticket(14, title="Refresh")
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    assert worktrees.fetched == 1
    assert worktrees.pushed == [run.branch]
    creation = forge.mr_creations[0]
    assert creation["source"] == run.branch
    assert creation["target"] == "develop"
    assert creation["title"] == "Resolve #14: Refresh"
    assert "Related to #14" in creation["body"]
    assert "close" not in creation["body"].lower()  # human decides closure
    assert creation["reviewers"] == ["r"]
    assert run.lifecycle == "in-review"
    assert worktrees.removed == []  # environment retained for review
    expected_order = ["delivery-start", "target-merged", "gates-run-passed",
                      "delivery-preflight-passed", "pushed", "mr-opened",
                      "in-review"]
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert [e for e in events if e in expected_order] == expected_order


def test_delivery_commits_conductor_generated_artifacts_before_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief   Delivery gates/report may write final workflow metadata after the
             executor's last commit; ADORE commits those artifacts before it
             pushes and opens the draft MR.
    @version 0.1.1
    """
    engine, forge, _, worktrees = make_engine(tmp_path, FakeExecutor([gate_ok()] * 6))

    def dirty_gates_run(execute, timeout=1800):
        worktrees.dirty = True
        return GateResult(ok=True, exit_code=0, output="gates ok")

    monkeypatch.setattr(gates, "gates_run", dirty_gates_run)
    forge.add_ticket(14, title="Refresh")
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    assert worktrees.delivery_commits == [
        (run.run_id, "Record delivery verification for ticket 14")
    ]
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert events.index("delivery-artifacts-committed") < events.index("pushed")
    assert worktrees.pushed == [run.branch]


def test_merge_conflict_relaunches_executor_to_resolve(tmp_path: Path) -> None:
    """
    @brief   A conflicted target merge relaunches the executor with the
             conflict context; once concluded the delivery continues.
    @version 0.1.0
    """
    engine, forge, _, worktrees = make_engine(tmp_path, FakeExecutor([gate_ok()] * 7))
    worktrees.merge_results = [
        CommandResult(exit_code=1, stdout="CONFLICT (content): README.md"),
        CommandResult(exit_code=0, stdout="Already up to date."),
    ]
    forge.add_ticket(14)
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "in-review"
    conflict_prompts = [p for p in engine.executor.prompts if "merge conflicts" in p]
    assert len(conflict_prompts) == 1
    assert "CONFLICT (content)" in conflict_prompts[0]


def test_delivery_fix_prompt_includes_agentic_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief   A failed delivery gates-run check relaunches the executor with
             existing workflow evidence from `.agentic` artifacts.
    @version 0.1.0
    """
    executor = FakeExecutor([gate_ok()] * 7)
    engine, forge, _, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14)
    run_id = engine._run_id(14)
    write_agentic_failure_evidence(
        engine,
        run_id,
        summary="Post-merge validation failed in the runtime-project gate.",
        command="make test",
        stderr_tail="tests failed after target merge",
    )
    calls = {"count": 0}

    def gates_run_once_then_pass(execute, timeout=1800):
        calls["count"] += 1
        if calls["count"] == 1:
            return GateResult(ok=False, exit_code=2, output="gates run stdout was vague")
        return GateResult(ok=True, exit_code=0, output="gates ok")

    monkeypatch.setattr(gates, "gates_run", gates_run_once_then_pass)

    engine.poll_once()

    delivery_prompts = [p for p in executor.prompts if "gates-run check failed" in p]
    assert len(delivery_prompts) == 1
    assert "gates run stdout was vague" in delivery_prompts[0]
    assert "Agentic failure evidence" in delivery_prompts[0]
    assert "Post-merge validation failed" in delivery_prompts[0]
    assert "tests failed after target merge" in delivery_prompts[0]


def test_push_failure_escalates(tmp_path: Path) -> None:
    """
    @brief   A rejected push (auth, protected branch, push rules) escalates -
             no MR is ever opened on a branch that is not on the remote.
    @version 0.1.0
    """
    engine, forge, _, worktrees = make_engine(tmp_path, FakeExecutor([gate_ok()] * 6))
    worktrees.push_result = CommandResult(
        exit_code=1, stderr="remote: GitLab: branch name does not follow the pattern"
    )
    forge.add_ticket(14)
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "push failed" in run.outcome
    assert forge.mr_creations == []


def test_existing_open_mr_is_adopted_never_duplicated(tmp_path: Path) -> None:
    """
    @brief   Idempotent recovery: a branch that already has an open MR (crash
             after creation, or a manual pilot push) is adopted as-is.
    @version 0.1.0
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor([gate_ok()] * 6))
    forge.add_ticket(14)
    run_id = engine._run_id(14)
    branch = engine._branch_name(run_id, 14)
    forge.mrs[7] = MergeRequest(iid=7, state="opened",
                                web_url="https://x/-/merge_requests/7")
    forge.mrs_by_branch[branch] = 7
    engine.poll_once()
    run = engine.store.load(run_id)
    assert run.lifecycle == "in-review"
    assert run.mr_iid == 7
    assert forge.mr_creations == []  # adopted, not duplicated


def test_merged_mr_completes_the_run_with_teardown(tmp_path: Path) -> None:
    """
    @brief   A human merge (detected by iid, which also finds non-open MRs)
             marks the run done and tears down container + worktree, keeping
             state for audit.
    @version 0.1.0
    """
    engine, forge, containers, worktrees = make_engine(
        tmp_path, FakeExecutor([gate_ok()] * 6)
    )
    forge.add_ticket(14)
    engine.poll_once()
    run_id = engine._run_id(14)
    run = engine.store.load(run_id)
    forge.mrs[run.mr_iid].state = "merged"
    summary = engine.poll_once()
    assert summary["done"] == 1
    run = engine.store.load(run_id)
    assert run.lifecycle == "done" and run.outcome == "merged"
    assert (run_id, run.branch) in worktrees.removed
    assert ("remove", run.container) in containers.events
    assert engine.store.exists(run_id)  # audit state kept


def test_closed_mr_ends_the_run(tmp_path: Path) -> None:
    """
    @brief   An MR closed without merging terminates the run with cleanup
             (design 11b).
    @version 0.1.0
    """
    engine, forge, _, worktrees = make_engine(tmp_path, FakeExecutor([gate_ok()] * 6))
    forge.add_ticket(14)
    engine.poll_once()
    run_id = engine._run_id(14)
    run = engine.store.load(run_id)
    forge.mrs[run.mr_iid].state = "closed"
    summary = engine.poll_once()
    assert summary["mr_closed"] == 1
    run = engine.store.load(run_id)
    assert run.lifecycle == "failed" and run.outcome == "mr-closed"
    assert (run_id, run.branch) in worktrees.removed


def _delivered_run(tmp_path: Path, executor_results: int = 6):
    """
    @brief      An engine with a run already delivered to in-review.
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  executor_results Clean gate results to queue.
    @return     (engine, forge, run_id).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-04
    @version    0.1.0
    """
    engine, forge, _, _ = make_engine(tmp_path,
                                      FakeExecutor([gate_ok()] * executor_results))
    forge.add_ticket(14)
    engine.poll_once()
    return engine, forge, engine._run_id(14)


def test_revise_label_triggers_the_revise_cycle(tmp_path: Path) -> None:
    """
    @brief   The agent-revise label on the open MR triggers exactly the 11b
             cycle: label cleared FIRST, executor launched with the review
             thread, delivery tail re-run, same branch pushed, MR updated
             (never recreated), update comment posted, back to in-review.
    @version 0.1.0
    """
    engine, forge, run_id = _delivered_run(tmp_path)
    run = engine.store.load(run_id)
    forge.mrs[run.mr_iid].labels.append("agent-revise")
    forge.mr_comments[run.mr_iid] = [
        Comment(id=900, body="Please use ISO week format", author="reviewer"),
    ]
    engine.executor.results = [gate_ok("ses_rev")]
    summary = engine.poll_once()
    assert summary["revised"] == 1
    run = engine.store.load(run_id)
    assert run.lifecycle == "in-review"
    assert run.review_rounds == 1
    # trigger cleared before work; label removal recorded
    assert ("remove_mr_labels", run.mr_iid, ("agent-revise",)) in forge.calls
    assert "agent-revise" not in forge.mrs[run.mr_iid].labels
    # executor saw the review thread and the revise instruction
    revise_prompt = engine.executor.prompts[-1]
    assert "ISO week format" in revise_prompt
    assert "requested changes" in revise_prompt
    # same MR: exactly one creation ever; update comment posted
    assert len(forge.mr_creations) == 1
    delivery_posts = [c for c in forge.calls
                      if c[0] == "post" and "kind=delivery" in c[2]]
    assert len(delivery_posts) == 2  # initial + revise update
    events = [e["event"] for e in engine.store.read_journal(run_id)]
    assert "revise-start" in events and "mr-updated" in events


def test_plain_mr_comment_never_triggers_revise(tmp_path: Path) -> None:
    """
    @brief   Design 11b: no auto-react - a reviewer comment WITHOUT the
             revise label leaves the run untouched.
    @version 0.1.0
    """
    engine, forge, run_id = _delivered_run(tmp_path)
    run = engine.store.load(run_id)
    forge.mr_comments[run.mr_iid] = [
        Comment(id=900, body="just thinking out loud", author="reviewer"),
    ]
    launches_before = len(engine.executor.prompts)
    summary = engine.poll_once()
    assert summary["revised"] == 0
    assert len(engine.executor.prompts) == launches_before
    assert engine.store.load(run_id).lifecycle == "in-review"


def test_review_rounds_cap_escalates(tmp_path: Path) -> None:
    """
    @brief   Exceeding max_review_rounds escalates instead of revising
             forever.
    @version 0.1.0
    """
    engine, forge, run_id = _delivered_run(tmp_path)
    run = engine.store.load(run_id)
    run.review_rounds = engine.config.review.max_review_rounds
    engine.store.save(run)
    forge.mrs[run.mr_iid].labels.append("agent-revise")
    engine.poll_once()
    run = engine.store.load(run_id)
    assert run.lifecycle == "failed"
    assert "review rounds" in run.outcome


def test_revise_questions_park_the_run(tmp_path: Path) -> None:
    """
    @brief   A revise launch that asks questions parks normally (the
             clarification flow owns it from there).
    @version 0.1.0
    """
    engine, forge, run_id = _delivered_run(tmp_path)
    run = engine.store.load(run_id)
    forge.mrs[run.mr_iid].labels.append("agent-revise")
    engine.executor.results = [
        GateRun(exit_code=0, has_questions=True, questions="Which format?")
    ]
    engine.poll_once()
    run = engine.store.load(run_id)
    assert run.lifecycle == "parked"
    assert run.clarification_rounds == 1


def test_legacy_validated_run_gets_delivered(tmp_path: Path) -> None:
    """
    @brief   A pre-phase-4 run stopped at validated-delivery-pending is
             picked up by reconciliation and delivered.
    @version 0.1.1
    """
    engine, forge, _, worktrees = make_engine(tmp_path, FakeExecutor())
    forge.add_ticket(14)
    run_id = engine._run_id(14)
    worktrees.create(run_id, "b", "x")
    engine.store.save(RunState(
        run_id=run_id, ticket_iid=14, stage="delivery", lifecycle="validated",
        branch="feature/adore-14", base_ref="origin/develop",
        container=f"adore-run-{run_id}",
    ))
    engine.poll_once()
    run = engine.store.load(run_id)
    assert run.lifecycle == "in-review"
    assert forge.mr_creations and forge.mr_creations[0]["source"] == "feature/adore-14"


# PUBLIC API / TESTS - operator commands: reset / cleanup (design 8c)


def test_reset_sets_the_stage_and_retry_continues_there(tmp_path: Path) -> None:
    """
    @brief   reset is state surgery: stage pointer moved, run left
             retry-able; retry then conducts from exactly that stage. An
             invalid stage or unknown run fails cleanly.
    @version 0.1.0
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor())
    run_id = park_run(engine, forge)
    assert engine.reset(run_id, "check") is True
    run = engine.store.load(run_id)
    assert run.stage == "check" and run.lifecycle == "failed"
    assert engine.reset(run_id, "bogus") is False
    assert engine.reset("nope", "check") is False
    engine.executor.results = [gate_ok()] * 3  # check, implementation, validation
    assert engine.retry(run_id) is True
    assert engine.store.load(run_id).lifecycle == "in-review"
    # first retried prompt is the check gate, not intake
    assert "CHECK gate" in engine.executor.prompts[1]


def test_cleanup_sweeps_orphans_but_never_active_runs(tmp_path: Path) -> None:
    """
    @brief   cleanup clears a stale lock, removes containers/worktrees whose
             runs are terminal or unknown, keeps everything active, and only
             REPORTS corrupt state.
    @version 0.1.1
    """
    engine, forge, containers, worktrees = make_engine(tmp_path, FakeExecutor())
    run_id = park_run(engine, forge)          # active (parked) run
    active_container = engine.store.load(run_id).container
    containers.states[active_container] = "exited"
    # orphans: a container and a worktree husk for an unknown run
    containers.states["adore-run-ghost-1"] = "exited"
    (worktrees.root / "ghost-2").mkdir(parents=True)
    # a corrupt run: reported, not touched
    engine.store.save(RunState(run_id="broken", ticket_iid=9))
    (engine.store.run_dir("broken") / "state.json").write_text("garbage",
                                                               encoding="utf-8")
    engine.store.acquire_lock()               # stale lock

    report = engine.cleanup()
    assert report["lock_cleared"] is True
    assert report["containers_removed"] == ["adore-run-ghost-1"]
    assert active_container in containers.states       # active kept
    assert "ghost-2" in report["worktrees_removed"]
    assert not (worktrees.root / "ghost-2").exists()
    assert worktrees.exists(run_id)                    # active worktree kept
    assert report["corrupt_runs"] == ["broken"]
    assert engine.store.exists("broken")               # reported, not deleted


# PUBLIC API / TESTS - teardown WSL bind-mount race (design 8b)


def test_teardown_retries_past_the_wsl_bind_mount_race(tmp_path: Path) -> None:
    """
    @brief   Worktree removal that transiently fails with the WSL mount-race
             signature (ENOSYS) is retried with backoff until it succeeds -
             no husk left, no manual cleanup needed.
    @version 0.1.1
    """
    engine, _, _, worktrees = make_engine(tmp_path, FakeExecutor())
    sleeps: list[float] = []
    engine.sleep = lambda d: sleeps.append(d)
    run = RunState(run_id="r-14", ticket_iid=14, container="adore-run-r-14",
                   branch="feature/x")
    enosys = IsolationError("git worktree failed",
                            stderr="failed to delete '...': Function not implemented")
    worktrees.remove_errors = [enosys, enosys]  # clears on the 3rd attempt

    engine._teardown(run, remove_worktree=True)

    assert worktrees.removed == [("r-14", "feature/x")]  # eventually removed
    assert len(sleeps) == 2                              # two backoff waits


def test_teardown_does_not_retry_a_real_worktree_error(tmp_path: Path) -> None:
    """
    @brief   A non-transient removal error is NOT retried (retries must not
             mask real failures); the husk is left for `adore cleanup`.
    @version 0.1.1
    """
    engine, _, _, worktrees = make_engine(tmp_path, FakeExecutor())
    sleeps: list[float] = []
    engine.sleep = lambda d: sleeps.append(d)
    run = RunState(run_id="r-15", ticket_iid=15, container="adore-run-r-15",
                   branch="feature/y")
    real = IsolationError("git failed", stderr="fatal: not a valid object name")
    worktrees.remove_errors = [real, real]

    engine._teardown(run, remove_worktree=True)

    assert worktrees.removed == []              # never succeeded
    assert sleeps == []                         # no retry on a real error
    assert len(worktrees.remove_errors) == 1    # only one attempt consumed


# PUBLIC API / TESTS - metrics recording (design 13)


def test_terminal_states_record_metrics(tmp_path: Path) -> None:
    """
    @brief   A merged run lands one summary row (usage summed from journal
             events); a later escalation of another run adds its own row -
             never a duplicate for re-records.
    @version 0.1.1
    """
    from adore.metrics import load_summaries

    engine, forge, _, _ = make_engine(
        tmp_path,
        FakeExecutor([GateRun(exit_code=0, session_id="s", tokens_in=100,
                              tokens_out=10, cost_usd=0.01)] * 6),
    )
    forge.add_ticket(14)
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    forge.mrs[run.mr_iid].state = "merged"
    engine.poll_once()
    rows = load_summaries(engine.config.metrics.db_path)
    assert len(rows) == 1
    row = rows[0]
    assert row.outcome == "merged"
    assert row.tokens_in == 600 and row.tokens_out == 60  # 6 launches
    assert abs(row.cost_usd - 0.06) < 1e-9
    assert row.executor_launches == 6
    assert row.time_to_mr_seconds >= 0 and row.mr_url


def test_metrics_disabled_records_nothing(tmp_path: Path) -> None:
    """
    @brief   [metrics] enabled=false switches recording off entirely.
    @version 0.1.1
    """
    from adore.metrics import load_summaries

    config = make_config(tmp_path)
    config.metrics.enabled = False
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor(), config)
    forge.add_ticket(14)
    engine.executor.results = [
        GateRun(exit_code=1, stderr="x")] * engine.config.budgets.max_iterations
    engine.poll_once()  # escalates on budget
    assert engine.store.load(engine._run_id(14)).lifecycle == "failed"
    assert load_summaries(engine.config.metrics.db_path) == []


def test_gate_order_matches_the_workflow_cli_stages() -> None:
    """
    @brief   The conductor drives the six development gates in the workflow
             CLI's canonical order (models.py STAGES, minus delivery which is
             phase 4). Alignment sits between intake and requirement.
    @version 0.1.1
    """
    assert GATES == ("intake", "alignment", "requirement", "check",
                     "implementation", "validation")


# END OF FILE
