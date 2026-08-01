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
"""

from __future__ import annotations

# IMPORTS
from datetime import UTC, datetime, timedelta
import json
import pathlib
from pathlib import Path

from adore.config import Config, ExecutorCommand
from adore.executor.base import Executor, GateRun
from adore.forge import Comment, Forge, ForgeError, MergeRequest, Ticket
from adore.isolation import IsolationError
from adore.aegis import AegisResponse
from adore.orchestrator import (
    _MR_MISSING_GRACE_POLLS,
    BLOCK_ESCALATE,
    BLOCK_PARK,
    BLOCK_RETRY,
    PUBLICATION_STAGE,
    QUICK_STAGES,
    STANDARD_STAGES,
    Orchestrator,
    classify_block,
)
from adore.state import RunState, StateStore
from adore.util import CommandResult
import pytest

# CONSTANTS

AC_BODY = "Do the thing.\n\n## Acceptance criteria\n- [ ] it works\n"

# The AEGIS run id FakeAegis mints for a default (feature) run.
AEGIS_RUN = "feature-2026-08-01T101112Z-0a1b2c3d"

# DATA MODELS / TYPEDEFINITIONS


class FakeForge(Forge):
    """
    @brief   In-memory Git platform recording every call for order asserts.
    """

    def __init__(self) -> None:
        """
        @brief   Empty platform.
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
        # when set, post_comment raises ForgeError for bodies containing it,
        # so one specific post can fail without disturbing the others
        self.post_fails_on = ""

    def add_ticket(self, iid: int, title: str = "T", body: str = AC_BODY,
                   labels: list[str] | None = None) -> Ticket:
        """
        @brief      Seed a ticket.
        @param[in]  iid Ticket id.
        @param[in]  title Title.
        @param[in]  body Description.
        @param[in]  labels Labels (default ready + P1).
        @return     The ticket.
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
        if self.post_fails_on and self.post_fails_on in body:
            self.calls.append(("post-refused", iid, body))
            raise ForgeError("the platform refused the comment (HTTP 500)")
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


class FakeAegis:
    """
    @brief   Scripted AEGIS 2.x CLI walking a real stage sequence.
    @details Answers the grouped commands ADORE issues with conforming
             envelopes and advances the stage pointer on `stage close`, so the
             conductor's `next`-driven loop is exercised exactly as it would be
             against a live payload. Every deviation - a stage that will not
             become ready, a failing verification, a blocked close, a
             non-conforming response - is a knob.
    """

    def __init__(self) -> None:
        """
        @brief   A fresh payload with no run started.
        """
        self.run_id = ""
        self.kind = ""
        self.profile = "full"
        self.stages: tuple[str, ...] = STANDARD_STAGES
        self.index = 0
        self.complete = False
        self.calls: list[list[str]] = []
        self.closes: list[str] = []
        # knobs
        self.blockers: dict[str, list[list[str]]] = {}  # stage -> per-attempt
        self.verify_results: list[int] = []             # exit codes, then 0
        self.close_blocked: dict[str, str] = {}         # stage -> error text
        self.start_blocked = ""
        self.status_override: list[CommandResult] = []
        # stage -> earlier stage to regress to once, as `route_to` would
        self.route_back: dict[str, str] = {}
        # (group, action) -> canned result, replacing the scripted behavior
        self.overrides: dict[tuple[str, str], CommandResult] = {}
        self.report_path = ".agentic/runs/RUN/report.md"
        self.on_delivery_report = None  # callback for tests
        self.evidence: list[dict] = []
        # worktree the bound container mounts; set from FakeContainers.provision
        self.worktree: pathlib.Path | None = None
        # stage -> control values written into graph.json stage_records
        self.stage_control: dict[str, dict] = {}
        # when set, the fake stops rewriting graph.json (damaged-graph tests)
        self.freeze_graph = False
        # when set, closing the last stage records the close but leaves the
        # pointer and `complete` alone, so `run status` keeps reporting the
        # already-closed final stage (the sequence-boundary regression case)
        self.stall_at_final_close = False

    # -- helpers ---------------------------------------------------------------

    @property
    def stage(self) -> str:
        """
        @brief   The stage the run currently sits on.
        @return  Stage name ("none" once the run completed).
        """
        return "none" if self.complete else self.stages[self.index]

    def _pending_blockers(self, stage: str, consume: bool) -> list[str]:
        """
        @brief      Blockers scripted for this attempt at a stage.
        @param[in]  stage Stage name.
        @param[in]  consume Whether to drop the attempt after reading it.
        @return     Blocker strings (empty when the stage is ready).
        """
        attempts = self.blockers.get(stage)
        if not attempts:
            return []
        return attempts.pop(0) if consume else list(attempts[0])

    def _envelope(self, status: str = "ok", **extras) -> str:
        """
        @brief      Render a conforming envelope.
        @param[in]  status Envelope status.
        @param[in]  extras Command-specific extras.
        @return     JSON text.
        """
        payload = {
            "status": status,
            "stage": self.stage,
            "artifact": f".agentic/runs/{self.run_id}/stages/{self.stage}/stage.toml",
            "next": "none" if self.complete else "aegis stage apply",
        }
        payload.update(extras)
        return json.dumps(payload)

    def _readiness(self, consume: bool = False) -> dict:
        """
        @brief      The `stage show` mapping for the current stage.
        @param[in]  consume Whether reading it consumes a scripted attempt.
        @return     The readiness mapping.
        """
        blockers = self._pending_blockers(self.stage, consume)
        return {
            "run_id": self.run_id,
            "stage": self.stage,
            "state": "applied",
            "ready": not blockers,
            "blockers": blockers,
            "files": [],
            "warnings": [],
            "artifact": f".agentic/runs/{self.run_id}/stages/{self.stage}/stage.toml",
        }

    def write_graph(self) -> None:
        """
        @brief   Persist the run graph AEGIS keeps in the worktree.
        @details A started AEGIS run always has a graph.json, so the fake
                 writes one - ADORE reads evidence and stage control from it,
                 and treats its absence as a broken run record.
        """
        if self.worktree is None or not self.run_id or self.freeze_graph:
            return
        run_dir = self.worktree / ".agentic" / "runs" / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        graph = {
            "run_id": self.run_id,
            "schema_version": 3,
            "stage": self.stage,
            "complete": self.complete,
            "evidence": self.evidence,
            "stage_records": {
                name: {"status": "applied", "unresolved_questions": [],
                       "requested_access_mode": "", "route_to": "",
                       **self.stage_control.get(name, {})}
                for name in self.stages
            },
        }
        if self.profile == "quick":
            graph["profile"] = "quick"
        (run_dir / "graph.json").write_text(
            json.dumps(graph, indent=2), encoding="utf-8"
        )

    def _quick_details(self) -> dict:
        """
        @brief   Quick-profile status fields, empty for full runs.
        @return  The extras mapping.
        """
        if self.profile != "quick":
            return {}
        return {"run_profile": "quick", "bypass_status": "bypassed",
                "bypassed_stages": [s for s in STANDARD_STAGES
                                    if s not in QUICK_STAGES]}

    # -- dispatch ---------------------------------------------------------------

    def __call__(self, argv: list[str]) -> CommandResult:
        """
        @brief      Answer one `run.sh` invocation.
        @param[in]  argv Full command tokens.
        @return     The CommandResult a real payload would produce.
        """
        self.calls.append(list(argv))
        verbs = [token for token in argv[2:] if not token.startswith("--")]
        override = self.overrides.get(tuple(verbs[:2]))
        if override is not None:
            return override
        # `--run` must follow the verbs on every command but start/validate
        if verbs[:2] not in (["run", "start"], ["config", "validate"]):
            assert "--run" in argv, f"missing --run on {verbs}"
            assert argv[argv.index("--run") + 1] == self.run_id
        assert argv[-1] == "--json"

        if verbs[:2] == ["run", "start"]:
            if self.start_blocked:
                return CommandResult(
                    exit_code=1,
                    stdout=json.dumps({
                        "status": "blocked", "stage": "none", "artifact": "none",
                        "next": "aegis config validate",
                        "error": self.start_blocked,
                    }),
                )
            self.kind = verbs[2]
            self.profile = "quick" if "--quick" in argv else "full"
            self.stages = QUICK_STAGES if self.profile == "quick" else STANDARD_STAGES
            self.run_id = f"{self.kind}-2026-08-01T101112Z-0a1b2c3d"
            self.report_path = f".agentic/runs/{self.run_id}/report.md"
            self.write_graph()
            return CommandResult(
                exit_code=0,
                stdout=self._envelope(run_id=self.run_id, kind=self.kind,
                                      **self._quick_details()),
            )
        if verbs[:2] in (["run", "status"], ["run", "resume"], ["delivery", "show"]):
            if self.status_override:
                return self.status_override.pop(0)
            target = self.route_back.pop(self.stage, "")
            if target:
                self.index = self.stages.index(target)
            return CommandResult(
                exit_code=0,
                stdout=self._envelope(
                    run_id=self.run_id,
                    complete=self.complete,
                    readiness={} if self.complete else self._readiness(),
                    evidence=self.evidence,
                    **self._quick_details(),
                ),
            )
        if verbs[:2] == ["stage", "show"]:
            return CommandResult(
                exit_code=0, stdout=self._envelope(**self._readiness(consume=True))
            )
        if verbs[:2] == ["stage", "close"]:
            stage = self.stage
            blocked = self.close_blocked.pop(stage, "")
            if blocked:
                return CommandResult(
                    exit_code=1, stdout=self._envelope("blocked", error=blocked)
                )
            self.closes.append(stage)
            if self.index + 1 >= len(self.stages):
                self.complete = not self.stall_at_final_close
            else:
                self.index += 1
            self.write_graph()
            return CommandResult(exit_code=0, stdout=self._envelope(
                complete=self.complete, **self._quick_details()))
        if verbs[:2] == ["verify", "run"]:
            code = self.verify_results.pop(0) if self.verify_results else 0
            return CommandResult(
                exit_code=1 if code else 0,
                stdout=self._envelope(
                    "failed" if code else "ok",
                    verification={"gates": {"test": {"status": "failed" if code
                                                     else "passed"}}},
                ),
            )
        if verbs[:2] == ["delivery", "report"]:
            if self.on_delivery_report is not None:
                self.on_delivery_report()
            return CommandResult(exit_code=0,
                                 stdout=self._envelope(report=self.report_path))
        if verbs[:2] == ["config", "validate"]:
            return CommandResult(exit_code=0, stdout=json.dumps({
                "status": "ok", "stage": "none",
                "artifact": ".agentic/workflow.toml",
                "next": "aegis run start feature", "schema_version": 3,
            }))
        if verbs[:2] == ["waive", "list"]:
            return CommandResult(exit_code=0, stdout=self._envelope(
                eligible_blockers=[], active_waivers=[], waiver_history=[]))
        raise AssertionError(f"unscripted AEGIS command: {verbs}")


class FakeContainers:
    """
    @brief   Container manager double delegating AEGIS commands to FakeAegis.
    """

    def __init__(self) -> None:
        self.states: dict[str, str] = {}
        self.events: list[tuple[str, str]] = []
        self.aegis = FakeAegis()
        self.exec_calls: list[list[str]] = []
        self.exec_envs: list[dict[str, str] | None] = []
        self.provision_envs: list[dict[str, str]] = []
        self.tool_checks: list[str] = []
        self.tool_check_failure: str = ""

    def status(self, name: str) -> str:
        return self.states.get(name, "absent")

    def ensure_volumes(self) -> None:
        self.events.append(("volumes", ""))

    def provision(self, name, repo_path, worktree_path, io_path, env) -> str:
        self.aegis.worktree = Path(worktree_path)
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
        tokens = [str(part) for part in argv]
        self.exec_calls.append(tokens)
        self.exec_envs.append(dict(env) if env is not None else None)
        if len(tokens) >= 2 and tokens[1] == ".agentic/tools/run.sh":
            return self.aegis(tokens)
        return CommandResult(exit_code=0)


class FakeExecutor(Executor):
    """
    @brief   Executor double replaying scripted GateRuns; records prompts.
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
    """
    return GateRun(exit_code=0, session_id=session)


def gate_cost(cost_usd: float, session: str = "ses_1") -> GateRun:
    """
    @brief      A clean gate result that reports what the launch cost.
    @param[in]  cost_usd USD the executor reported for this launch.
    @param[in]  session Session id carried forward.
    @return     The GateRun.
    """
    return GateRun(exit_code=0, session_id=session, tokens_in=1000,
                   tokens_out=500, cost_usd=cost_usd)


def write_agentic_failure_evidence(
    engine: Orchestrator,
    run_id: str,
    aegis: FakeAegis,
    *,
    summary: str = "Focused pytest failed before the fix.",
    command: str = "pytest tests/test_widget.py::test_widget_renders",
    gate: str = "test",
    report: str = "## Invariants\n- `INV-4` FAIL (blocking): failing gate evidence",
) -> None:
    """
    @brief      Seed AEGIS run artifacts for one run.
    @details    The failing evidence row goes through the fake CLI, which owns
                `graph.json` exactly as a real payload does; the validation
                summary and the report are written straight into the run
                directory, addressed by the run id ADORE persists - never by
                the retired `current_run` pointer.
    @param[in]  engine Test engine whose fake worktree root is used.
    @param[in]  run_id ADORE run id.
    @param[in]  aegis The fake AEGIS CLI that will mint the run.
    @param[in]  summary Evidence summary.
    @param[in]  command Failed command.
    @param[in]  gate Failing gate group name.
    @param[in]  report Existing report.md text.
    """
    aegis.evidence = [
        {
            "id": "E-0007",
            "kind": "test-run",
            "result": "fail",
            "status": "active",
            "summary": summary,
            "command": command,
            "stage": "validation",
            "failure_kind": "assertion",
        }
    ]
    worktree = engine.worktrees.path_for(run_id)  # type: ignore[attr-defined]
    run_dir = worktree / ".agentic" / "runs" / AEGIS_RUN
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "validation-summary.json").write_text(
        json.dumps({
            "schema_version": 3,
            "run_id": AEGIS_RUN,
            "gates": {gate: {"status": "failed", "commands": [command]},
                      "lint": {"status": "passed", "commands": []},
                      "security": {"status": "disabled", "commands": []}},
            "invariants": [
                {"id": "INV-4", "name": "evidence", "holds": False,
                 "policy": "blocking", "message": "failing gate evidence"},
                {"id": "INV-1", "name": "traceability", "holds": True,
                 "policy": "blocking", "message": "ok"},
            ],
            "working_tree": {"entries": [], "untracked": [],
                             "blocking_findings": []},
        }, indent=2),
        encoding="utf-8",
    )
    (run_dir / "report.md").write_text(report, encoding="utf-8")


def park_run(engine: Orchestrator, forge: FakeForge, iid: int = 14) -> str:
    """
    @brief      Drive a ticket into the parked state via a questions gate.
    @param[in]  engine The engine (its executor must be a FakeExecutor).
    @param[in]  forge The fake forge.
    @param[in]  iid Ticket id.
    @return     The run id.
    """
    forge.add_ticket(iid)
    engine.executor.results = [
        GateRun(exit_code=0, has_questions=True, questions="1. Which variant?",
                session_id="ses_q")
    ]
    engine.poll_once()
    return engine._run_id(iid)


def crash_a_working_run(engine: Orchestrator, iid: int, age_seconds: int) -> str:
    """
    @brief      Leave a `working` run on disk exactly as a dead conductor does.
    @details    `store.save` always re-stamps `updated_at`, so the age is
                written straight into the persisted state.json afterwards -
                which is also the only thing a killed process leaves behind.
    @param[in]  engine The orchestrator owning the store.
    @param[in]  iid Ticket the abandoned run belongs to.
    @param[in]  age_seconds How long ago the conductor last wrote state.
    @return     The run id.
    """
    run_id = engine._run_id(iid)
    engine.store.save(RunState(
        run_id=run_id,
        ticket_iid=iid,
        stage="implementation",
        lifecycle="working",
        branch=f"adore/{run_id}",
        base_ref="origin/main",
        container=engine.identity.container_name(run_id),
    ))
    path = engine.store.run_dir(run_id) / "state.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["updated_at"] = ago(age_seconds)
    path.write_text(json.dumps(data), encoding="utf-8")
    return run_id


def ago(seconds: int) -> str:
    """
    @brief      An ISO timestamp N seconds in the past.
    @param[in]  seconds Age.
    @return     The timestamp string.
    """
    return (datetime.now(UTC) - timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


# PUBLIC API / TESTS


def test_full_profile_walks_all_eight_stages_to_a_draft_mr(tmp_path: Path) -> None:
    """
    @brief   Happy path: one eligible ticket walks the full AEGIS 2.x eight
             stage sequence, ADORE closes each stage after verifying it, and
             the completed run publishes a draft MR.
    """
    executor = FakeExecutor([gate_ok(f"ses_{i}") for i in range(8)])
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14, title="Refresh button")
    summary = engine.poll_once()
    assert summary["picked"] == 14
    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "in-review"
    assert run.stage == PUBLICATION_STAGE
    assert run.aegis_run_id == "feature-2026-08-01T101112Z-0a1b2c3d"
    assert run.mr_iid == 1 and "/merge_requests/1" in run.mr_url
    assert run.executor_session == "ses_7"
    assert executor.sessions == ["", *[f"ses_{i}" for i in range(7)]]
    assert executor.archive_stems == [
        f"{index:03d}-{stage}"
        for index, stage in enumerate(STANDARD_STAGES, start=1)
    ]
    # ADORE - never the executor - issued every close, in sequence
    assert containers.aegis.closes == list(STANDARD_STAGES)
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert events.count("stage-closed") == 8
    assert "aegis-run-started" in events and "aegis-run-complete" in events
    # ticket snapshot saved; ONE status comment (edited in place) plus ONE
    # kind=delivery comment with the MR link
    assert engine.store.load_ticket(run.run_id)["iid"] == 14
    posts = [c for c in forge.calls if c[0] == "post"]
    edits = [c for c in forge.calls if c[0] == "edit"]
    assert len(posts) == 2 and len(edits) >= 4
    assert any("kind=delivery" in c[2] and run.mr_url in c[2] for c in posts)
    assert containers.events[-1] == ("stop", run.container)  # retained, not removed


def test_quick_profile_walks_the_four_stage_sequence(tmp_path: Path) -> None:
    """
    @brief   A ticket labelled for a fix plus the quick label starts
             `run start fix --quick` and conducts only the four declared
             stages; the four bypassed ones are never launched.
    """
    executor = FakeExecutor([gate_ok(f"ses_{i}") for i in range(4)])
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14, labels=["agent-ready", "P1", "bug", "agent-quick"])

    engine.poll_once()

    start = next(call for call in containers.aegis.calls if call[2:4] == ["run", "start"])
    assert start[2:6] == ["run", "start", "fix", "--quick"]
    assert containers.aegis.closes == list(QUICK_STAGES)
    assert executor.archive_stems == [
        f"{index:03d}-{stage}"
        for index, stage in enumerate(QUICK_STAGES, start=1)
    ]
    run = engine.store.load(engine._run_id(14))
    assert run.aegis_run_id.startswith("fix-")
    assert run.lifecycle == "in-review"


def test_quick_label_is_ignored_for_kinds_aegis_rejects(tmp_path: Path) -> None:
    """
    @brief   The quick label on an unmapped (feature) ticket never produces
             `--quick`: AEGIS allows it only for fix/change, so the conductor
             does not build a command that would be blocked.
    """
    engine, forge, containers, _ = make_engine(
        tmp_path, FakeExecutor([gate_ok() for _ in range(8)])
    )
    forge.add_ticket(14, labels=["agent-ready", "P1", "agent-quick"])

    engine.poll_once()

    start = next(call for call in containers.aegis.calls if call[2:4] == ["run", "start"])
    assert start[2:5] == ["run", "start", "feature"]
    assert "--quick" not in start


def test_the_aegis_run_is_started_once_and_resumed_afterwards(
    tmp_path: Path,
) -> None:
    """
    @brief   A run that already carries an AEGIS run id never starts a second
             governed run; the persisted id is pinned instead.
    """
    executor = FakeExecutor([
        GateRun(exit_code=0, has_questions=True, questions="1. Which variant?")
    ])
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14)
    engine.poll_once()  # parks during intake, after `run start`
    run_id = engine._run_id(14)
    aegis_run = engine.store.load(run_id).aegis_run_id
    assert aegis_run

    engine.executor.results = [gate_ok() for _ in range(8)]
    forge.human_comment(14, "Use the small variant.")
    engine.poll_once()

    starts = [c for c in containers.aegis.calls if c[2:4] == ["run", "start"]]
    assert len(starts) == 1
    assert engine.store.load(run_id).aegis_run_id == aegis_run


def test_executor_artifacts_are_journaled(tmp_path: Path) -> None:
    """
    @brief   GateRun artifact archive paths are surfaced through the run
             journal so `adore logs <run-id>` points at raw evidence.
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


def test_stage_failure_retries_with_context_until_budget(tmp_path: Path) -> None:
    """
    @brief   A failing stage is relaunched with the failure context and the
             iterations budget ends the thrashing.
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
    assert "previous attempt of the intake stage failed" in executor.prompts[1]
    assert "boom-1" in executor.prompts[1]


def test_stage_failure_retry_prompt_includes_aegis_evidence(tmp_path: Path) -> None:
    """
    @brief   When a stage fails, the retry prompt includes existing AEGIS run
             failure evidence, not only the executor stderr tail.
    """
    config = make_config(tmp_path)
    config.budgets.max_iterations = 2
    executor = FakeExecutor([
        GateRun(exit_code=1, stderr="executor stderr was vague"),
        GateRun(exit_code=1, stderr="still failing"),
    ])
    engine, forge, containers, _ = make_engine(tmp_path, executor, config)
    forge.add_ticket(14)
    run_id = engine._run_id(14)
    write_agentic_failure_evidence(engine, run_id, containers.aegis)

    engine.poll_once()

    retry_prompt = executor.prompts[1]
    assert "previous attempt of the intake stage failed" in retry_prompt
    assert "executor stderr was vague" in retry_prompt
    assert "AEGIS failure evidence" in retry_prompt
    # validation-summary.json first: the authoritative verification account
    assert "Failing gate groups: test (failed)" in retry_prompt
    assert "security (disabled)" not in retry_prompt  # never rendered as failing
    assert "INV-4 (blocking): failing gate evidence" in retry_prompt
    assert "INV-1" not in retry_prompt  # holds, so not a finding
    # then the schema-3 graph evidence rows
    assert "E-0007 test-run stage=validation" in retry_prompt
    assert "pytest tests/test_widget.py::test_widget_renders" in retry_prompt
    assert "failure kind: assertion" in retry_prompt


def test_relaunch_prompt_includes_the_composed_run_orientation(
    tmp_path: Path,
) -> None:
    """
    @brief   A stage relaunch prepends the orientation ADORE composes from
             `aegis run resume`, so the fresh executor session knows where the
             run stands without re-deriving it. AEGIS 2.x answers with run
             state rather than prose, so the brief names the run, the stage,
             the exact next command, readiness, and recent evidence. A fresh
             run carries no brief on its very first launch.
    """
    config = make_config(tmp_path)
    config.budgets.max_iterations = 2
    executor = FakeExecutor([
        GateRun(exit_code=1, stderr="first attempt failed"),
        GateRun(exit_code=1, stderr="still failing"),
    ])
    engine, forge, containers, _ = make_engine(tmp_path, executor, config)
    containers.aegis.evidence = [
        {"id": "E-0007", "kind": "test-run", "result": "fail", "status": "active"}
    ]
    forge.add_ticket(14)

    engine.poll_once()

    assert "run orientation" not in executor.prompts[0]  # first launch
    retry_prompt = executor.prompts[1]
    assert "Current AEGIS run orientation" in retry_prompt
    assert f"- run: {AEGIS_RUN}" in retry_prompt
    assert "- stage: intake" in retry_prompt
    assert "- exact next command: aegis stage apply" in retry_prompt
    assert "E-0007 test-run fail (active)" in retry_prompt


def test_blocked_resume_escalates_instead_of_degrading(tmp_path: Path) -> None:
    """
    @brief   Once an AEGIS run exists, a `run resume` that does not answer the
             supported contract is a hard failure: ADORE 2.0 escalates rather
             than silently continuing with an empty brief.
    """
    config = make_config(tmp_path)
    config.budgets.max_iterations = 3
    executor = FakeExecutor([GateRun(exit_code=1, stderr="first attempt failed")])
    engine, forge, containers, _ = make_engine(tmp_path, executor, config)
    forge.add_ticket(14)

    containers.aegis.overrides[("run", "resume")] = CommandResult(
        exit_code=2, stderr="usage: aegis [-h] ..."
    )

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "AEGIS contract failure (AegisProtocolError)" in run.outcome
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert "aegis-contract-failure" in events


def test_absent_aegis_run_files_are_a_normal_no_evidence_case(
    tmp_path: Path,
) -> None:
    """
    @brief   An AEGIS run directory with no artifacts yet is a normal
             no-evidence case; the retry prompt still carries the original
             stderr context.
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
    assert "AEGIS failure evidence" not in retry_prompt


def test_evidence_is_addressed_by_the_persisted_run_id_not_the_pointer(
    tmp_path: Path,
) -> None:
    """
    @brief   Evidence comes from `.agentic/runs/<persisted-run-id>/`. A
             `current_run` pointer - even one naming a different run - is never
             read (design decision 4).
    """
    config = make_config(tmp_path)
    config.budgets.max_iterations = 2
    executor = FakeExecutor([
        GateRun(exit_code=1, stderr="first failure"),
        GateRun(exit_code=1, stderr="still failing"),
    ])
    engine, forge, containers, _ = make_engine(tmp_path, executor, config)
    forge.add_ticket(14)
    run_id = engine._run_id(14)
    write_agentic_failure_evidence(engine, run_id, containers.aegis,
                                   summary="the pinned run")
    worktree = engine.worktrees.path_for(run_id)  # type: ignore[attr-defined]
    decoy = worktree / ".agentic" / "runs" / "feature-2026-01-01T000000Z-deadbeef"
    decoy.mkdir(parents=True, exist_ok=True)
    (decoy / "graph.json").write_text(
        json.dumps({"evidence": [{"id": "E-DECOY", "kind": "note",
                                  "result": "fail", "status": "active",
                                  "summary": "the decoy run"}]}),
        encoding="utf-8",
    )
    state_dir = worktree / ".agentic" / ".workspace" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "current_run").write_text(decoy.name, encoding="utf-8")

    engine.poll_once()

    retry_prompt = executor.prompts[1]
    assert AEGIS_RUN in retry_prompt
    assert "the pinned run" in retry_prompt
    assert "E-DECOY" not in retry_prompt


def test_damaged_aegis_artifacts_are_reported_not_hidden(
    tmp_path: Path,
) -> None:
    """
    @brief   A graph or validation summary that exists but cannot be parsed is
             reported in the prompt, so the executor knows evidence was present
             but damaged rather than absent.
    """
    config = make_config(tmp_path)
    config.budgets.max_iterations = 2
    executor = FakeExecutor([
        GateRun(exit_code=1, stderr="malformed graph"),
        GateRun(exit_code=1, stderr="still failing"),
    ])
    engine, forge, containers, _ = make_engine(tmp_path, executor, config)
    forge.add_ticket(14)
    worktree = engine.worktrees.path_for(engine._run_id(14))  # type: ignore[attr-defined]
    run_dir = worktree / ".agentic" / "runs" / AEGIS_RUN
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "graph.json").write_text("{", encoding="utf-8")
    (run_dir / "validation-summary.json").write_text("{", encoding="utf-8")
    containers.aegis.freeze_graph = True  # keep the damaged file on disk

    engine.poll_once()

    retry_prompt = executor.prompts[1]
    assert "validation-summary.json: could not parse" in retry_prompt
    assert "graph.json: could not parse failure evidence" in retry_prompt
    assert "malformed graph" in retry_prompt


def test_a_started_run_without_a_graph_escalates(tmp_path: Path) -> None:
    """
    @brief   A started AEGIS run always has a graph.json. If it is gone, the
             run record is broken - ADORE escalates instead of quietly
             producing an empty evidence block.
    """
    config = make_config(tmp_path)
    config.budgets.max_iterations = 3
    executor = FakeExecutor([GateRun(exit_code=1, stderr="stage failed")])
    engine, forge, containers, _ = make_engine(tmp_path, executor, config)
    forge.add_ticket(14)
    containers.aegis.freeze_graph = True  # never write the run record

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "AEGIS contract failure" in run.outcome
    assert "graph.json" in run.outcome


def test_failure_context_redacts_configured_executor_secrets(tmp_path: Path) -> None:
    """
    @brief   Exact configured secret values are redacted from stderr, graph,
             journal, and report evidence before they enter retry prompts.
    """
    secret = "sk-secret-1234"
    config = make_config(tmp_path)
    config.budgets.max_iterations = 2
    executor = FakeExecutor([
        GateRun(exit_code=1, stderr=f"executor leaked {secret}"),
        GateRun(exit_code=1, stderr="still failing"),
    ])
    engine, forge, containers, _ = make_engine(tmp_path, executor, config)
    engine.secrets = {"OPENAI_API_KEY": secret}
    forge.add_ticket(14)
    write_agentic_failure_evidence(
        engine,
        engine._run_id(14),
        containers.aegis,
        summary=f"Secret showed up in output: {secret}",
        command=f"pytest --token {secret}",
        report=f"## Invariants\n- FAIL: leaked {secret}",
    )

    engine.poll_once()

    retry_prompt = executor.prompts[1]
    assert secret not in retry_prompt
    assert "[REDACTED]" in retry_prompt


def test_stage_not_ready_relaunches_the_same_stage_with_its_blockers(
    tmp_path: Path,
) -> None:
    """
    @brief   The conductor's own verification gates the close: a stage AEGIS
             does not consider ready is relaunched with the exact blockers,
             and is never closed on the executor's word.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    containers.aegis.blockers["intake"] = [
        ["intake.statement must not be empty"], []
    ]
    forge.add_ticket(14)

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "in-review"
    assert len(executor.prompts) == 9  # intake twice, then seven stages once
    assert "does not consider it ready to close" in executor.prompts[1]
    assert "intake.statement must not be empty" in executor.prompts[1]
    assert containers.aegis.closes == list(STANDARD_STAGES)  # one close each
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert "stage-not-ready" in events


def test_failed_verification_relaunches_the_validation_stage(
    tmp_path: Path,
) -> None:
    """
    @brief   `aegis verify run` is ADORE's objective signal at validation and
             delivery: a failing run relaunches the stage instead of closing
             it.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    containers.aegis.verify_results = [1]  # first validation attempt fails
    forge.add_ticket(14)

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "in-review"
    validation_relaunch = executor.prompts[STANDARD_STAGES.index("validation") + 1]
    assert "`aegis verify run` failed at the validation stage" in validation_relaunch
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert "verify-failed" in events and "verify-passed" in events


def test_blocked_stage_close_escalates_with_the_aegis_remediation(
    tmp_path: Path,
) -> None:
    """
    @brief   ADORE never resolves a governance block itself: a blocked close
             ends the run with the exact AEGIS error on the ticket.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    containers.aegis.close_blocked["intake"] = (
        "INV-7 does not hold.\nRecord the missing process evidence."
    )
    forge.add_ticket(14)

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "AEGIS blocked `stage close (intake)`" in run.outcome
    assert "INV-7 does not hold" in run.outcome
    assert "remediation: Record the missing process evidence." in run.outcome
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert "aegis-blocked" in events


def test_unknown_stage_escalates(tmp_path: Path) -> None:
    """
    @brief   A stage outside the profile's declared sequence means the contract
             moved under ADORE; the run escalates instead of guessing.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14)
    containers.aegis.overrides[("run", "status")] = CommandResult(
        exit_code=0,
        stdout=json.dumps({
            "status": "ok", "stage": "repo-discovery", "artifact": "none",
            "next": "aegis stage prepare", "complete": False,
        }),
    )

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "not in the expected sequence" in run.outcome
    assert executor.prompts == []  # never launched into an unknown stage


def test_stage_regression_escalates(tmp_path: Path) -> None:
    """
    @brief   A backwards move - what an approved `route_to` produces - is a
             human decision in this ADORE version, so the conductor escalates
             instead of re-conducting the earlier stage.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    containers.aegis.route_back["alignment"] = "intake"
    forge.add_ticket(14)

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "routed the run back from 'alignment' to 'intake'" in run.outcome
    assert containers.aegis.closes == ["intake"]  # only the first close happened


def test_a_re_reported_final_stage_escalates_at_the_boundary(
    tmp_path: Path,
) -> None:
    """
    @brief   The regression guard holds at the end of the sequence too: AEGIS
             re-reporting the already-closed last stage without setting
             `complete` escalates as a typed protocol error, not as an
             unhandled IndexError that would crash the poll loop.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    containers.aegis.stall_at_final_close = True
    forge.add_ticket(14)

    engine.poll_once()  # must return normally, not raise

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "AegisProtocolError" in run.outcome
    assert "already closed final stage 'delivery'" in run.outcome
    assert containers.aegis.closes == list(STANDARD_STAGES)


def test_parked_ttl_reaps_container_but_keeps_run(tmp_path: Path) -> None:
    """
    @brief   TTL reap frees the container; the run stays parked and
             answerable (design 8b: reap != timeout).
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
    @brief   A validation stage AEGIS considers ready but that leaves a dirty
             tree (or zero commits) is NOT complete: validation relaunches
             with commit instructions until the work is committed (pilot
             finding 2026-07-03).
    """
    executor = FakeExecutor([gate_ok()] * 10)
    engine, forge, _, worktrees = make_engine(tmp_path, executor)
    worktrees.dirty = True
    forge.add_ticket(14)
    relaunch = STANDARD_STAGES.index("validation") + 1  # 0-based launch index

    original = executor.run_gate

    def run_gate(*args, **kwargs):
        # commit only once the validation relaunch is about to start
        if len(executor.prompts) >= relaunch:
            worktrees.dirty = False
        return original(*args, **kwargs)

    executor.run_gate = run_gate  # type: ignore[method-assign]
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "in-review"
    assert len(executor.prompts) == len(STANDARD_STAGES) + 1
    assert "UNCOMMITTED" in executor.prompts[relaunch]
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert "work-uncommitted" in events


def test_empty_branch_relaunches_validation_until_budget(tmp_path: Path) -> None:
    """
    @brief   Zero commits over base keeps relaunching validation and the
             iterations budget eventually escalates - never a hollow
             "validated".
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


def test_retry_of_publication_never_re_enters_the_stage_loop(
    tmp_path: Path,
) -> None:
    """
    @brief   Retrying a run that failed during publication resumes publication;
             it must not re-enter the AEGIS stage loop, whose run is already
             complete (live finding 2026-07-03).
    """
    engine, forge, containers, _ = make_engine(tmp_path, FakeExecutor())
    forge.add_ticket(14)
    run_id = engine._run_id(14)
    engine.store.save(RunState(
        run_id=run_id, ticket_iid=14, stage=PUBLICATION_STAGE,
        lifecycle="failed", aegis_run_id=AEGIS_RUN,
        branch="feature/adore-14", base_ref="origin/develop",
        container=f"c-{run_id}", outcome="push failed: x",
    ))
    containers.aegis.run_id = AEGIS_RUN
    containers.aegis.complete = True
    assert engine.retry(run_id) is True
    run = engine.store.load(run_id)
    assert run.lifecycle == "in-review"
    assert engine.executor.prompts == []  # no stage relaunched
    assert containers.aegis.closes == []  # no stage closed either
    assert forge.mr_creations[0]["source"] == "feature/adore-14"


def test_conduct_of_a_publishing_run_fails_closed(tmp_path: Path) -> None:
    """
    @brief   `_conduct` called on a run already in publication escalates
             instead of re-entering the stage loop (live finding 2026-07-04: a
             delivery run regressed to intake and burned gates).
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor())
    ticket = forge.add_ticket(14)
    run = RunState(run_id="r", ticket_iid=14, stage=PUBLICATION_STAGE,
                   container="c-r", branch="b")
    engine.store.save(run)
    engine._conduct(run, ticket)
    assert engine.store.load("r").lifecycle == "failed"
    assert engine.executor.prompts == []


def test_resume_of_a_publication_park_continues_publication(
    tmp_path: Path,
) -> None:
    """
    @brief   A run parked DURING publication resumes into publication with the
             thread - never back into the stage loop (live finding
             2026-07-04).
    """
    engine, forge, containers, worktrees = make_engine(tmp_path, FakeExecutor())
    forge.add_ticket(14)
    run_id = engine._run_id(14)
    worktrees.create(run_id, "feature/adore-14", "x")
    engine.store.save(RunState(
        run_id=run_id, ticket_iid=14, stage=PUBLICATION_STAGE,
        lifecycle="parked", aegis_run_id=AEGIS_RUN,
        branch="feature/adore-14", base_ref="origin/develop",
        container=f"c-{run_id}", question_comment_id=500,
        parked_at=ago(60), clarification_rounds=1,
    ))
    containers.aegis.run_id = AEGIS_RUN
    containers.aegis.complete = True
    forge.comments[14] = [Comment(id=501, body="tflint installed, go ahead",
                                  author="dan")]
    summary = engine.poll_once()
    assert summary["resumed"] == 1
    run = engine.store.load(run_id)
    assert run.lifecycle == "in-review"
    assert engine.executor.prompts == []  # no stage restarted
    assert forge.mr_creations  # publication completed


def test_resume_resets_the_active_work_budgets(tmp_path: Path) -> None:
    """
    @brief   Parked time is answer-wait, not work: an old created_at must not
             trip the wall clock on resume (live finding 2026-07-04: an 8h
             park escalated instantly).
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
    @brief   The AEGIS delivery report embedded in the MR description is
             tail-truncated at LINE boundaries with a marker - never mid-line
             fragments like `g",` (MR !29 review finding 2026-07-04).
    """
    engine, forge, _, worktrees = make_engine(
        tmp_path, FakeExecutor([gate_ok()] * 8)
    )
    forge.add_ticket(14)
    # `aegis delivery report` names the rendered report; ADORE reads it from
    # the run's worktree at exactly that repository-relative path
    report = (worktrees.path_for(engine._run_id(14)) / ".agentic" / "runs"
              / AEGIS_RUN / "report.md")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(f"- `E-{i:04}` gate/pass: line {i}" for i in range(200)),
        encoding="utf-8",
    )

    engine.poll_once()

    body = forge.mr_creations[0]["body"]
    block = body.split("### AEGIS delivery report\n```\n")[1].split("\n```")[0]
    lines = block.splitlines()
    assert lines[0] == "[... truncated ...]"
    assert lines[1].startswith("- `E-")  # complete line, bullet intact
    assert lines[-1].startswith("- `E-0199`")


def test_mr_description_ignores_a_report_path_outside_the_worktree(
    tmp_path: Path,
) -> None:
    """
    @brief   A `report` path that escapes the run's worktree is never read into
             the merge-request body; the MR is still opened, without a report
             section.
    """
    engine, forge, containers, _ = make_engine(
        tmp_path, FakeExecutor([gate_ok()] * 8)
    )
    forge.add_ticket(14)
    secret = tmp_path / "outside.md"
    secret.write_text("host-only content", encoding="utf-8")
    containers.aegis.report_path = "../../outside.md"

    engine.poll_once()

    body = forge.mr_creations[0]["body"]
    assert "### AEGIS delivery report" not in body
    assert "host-only content" not in body


# PUBLIC API / TESTS - delivery (design 11a/11b)


def test_delivery_sequence_and_draft_mr(tmp_path: Path) -> None:
    """
    @brief   The 11a order: fetch, merge target, push, DRAFT MR with
             reviewers, kind=delivery comment, in-review with the container
             retained (stopped) and the worktree kept.
    """
    engine, forge, containers, worktrees = make_engine(
        tmp_path, FakeExecutor([gate_ok()] * 8)
    )
    forge.add_ticket(14, title="Refresh")
    engine.poll_once()
    run = engine.store.load(engine._run_id(14))
    # two fetches: once when the worktree is first created (branch from a fresh
    # base) and once at the start of publication (integrate the target branch)
    assert worktrees.fetched == 2
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
    expected_order = ["delivery-start", "target-merged", "verify-run-passed",
                      "pushed", "mr-opened", "in-review"]
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert [e for e in events if e in expected_order] == expected_order


def test_delivery_commits_conductor_generated_artifacts_before_push(
    tmp_path: Path,
) -> None:
    """
    @brief   `aegis verify run` and `aegis delivery report` write final run
             records after the executor's last commit; ADORE commits those
             artifacts before it pushes and opens the draft MR.
    """
    engine, forge, containers, worktrees = make_engine(
        tmp_path, FakeExecutor([gate_ok()] * 8)
    )
    forge.add_ticket(14, title="Refresh")
    # `aegis delivery report` renders report.md after the executor's last
    # commit, so the tree is dirty when ADORE composes the MR body
    def mark_dirty() -> None:
        worktrees.dirty = True

    containers.aegis.on_delivery_report = mark_dirty
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


def test_delivery_fix_prompt_includes_aegis_evidence(tmp_path: Path) -> None:
    """
    @brief   A failed post-merge `aegis verify run` relaunches the executor
             with the existing AEGIS run evidence, not only the exit code.
    """
    executor = FakeExecutor([gate_ok()] * 10)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14)
    run_id = engine._run_id(14)
    write_agentic_failure_evidence(
        engine,
        run_id,
        containers.aegis,
        summary="Post-merge validation failed in the runtime-project gate.",
        command="make test",
    )
    # validation stage passes; the post-merge verification fails once
    containers.aegis.verify_results = [0, 0, 1]

    engine.poll_once()

    fixes = [p for p in executor.prompts if "after merging origin/develop" in p]
    assert len(fixes) == 1
    assert "`aegis verify run` failed" in fixes[0]
    assert "AEGIS failure evidence" in fixes[0]
    assert "Post-merge validation failed" in fixes[0]
    assert "Failing gate groups: test (failed)" in fixes[0]


def test_push_failure_escalates(tmp_path: Path) -> None:
    """
    @brief   A rejected push (auth, protected branch, push rules) escalates -
             no MR is ever opened on a branch that is not on the remote.
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


def test_in_review_run_ends_when_its_mr_vanishes(tmp_path: Path) -> None:
    """
    @brief   An in-review run whose MR is deleted on the platform rides out a
             few blips, then ends (design 4): it must not stay in-review and
             re-log "not found" on every poll forever. A transient 404 that
             resolves before the grace is exhausted is forgiven.
    """
    engine, forge, _, worktrees = make_engine(tmp_path, FakeExecutor([gate_ok()] * 6))
    forge.add_ticket(14)
    engine.poll_once()
    run_id = engine._run_id(14)
    mr_iid = engine.store.load(run_id).mr_iid
    del forge.mrs[mr_iid]  # the MR/PR is deleted on the platform
    for poll in range(1, _MR_MISSING_GRACE_POLLS):
        engine.poll_once()
        pending = engine.store.load(run_id)
        assert pending.lifecycle == "in-review"      # still tolerated
        assert pending.mr_missing_polls == poll
    engine.poll_once()  # the grace-th missing read ends the run
    ended = engine.store.load(run_id)
    assert ended.lifecycle == "failed"
    assert "no longer exists" in ended.outcome
    assert engine.store.exists(run_id)  # state kept for audit


def test_in_review_mr_missing_counter_resets_on_recovery(tmp_path: Path) -> None:
    """
    @brief   A transient not-found does not accumulate: once the MR reads back,
             the blip counter clears so a later real deletion still gets the
             full grace window.
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor([gate_ok()] * 6))
    forge.add_ticket(14)
    engine.poll_once()
    run_id = engine._run_id(14)
    mr = engine.store.load(run_id).mr_iid
    saved = forge.mrs[mr]
    del forge.mrs[mr]
    engine.poll_once()
    assert engine.store.load(run_id).mr_missing_polls == 1
    forge.mrs[mr] = saved  # MR reappears (the 404 was transient)
    engine.poll_once()
    assert engine.store.load(run_id).mr_missing_polls == 0
    assert engine.store.load(run_id).lifecycle == "in-review"


def _delivered_run(tmp_path: Path, executor_results: int = 6):
    """
    @brief      An engine with a run already delivered to in-review.
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  executor_results Clean gate results to queue.
    @return     (engine, forge, run_id).
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
    @brief   A run stopped at validated-delivery-pending is picked up by
             reconciliation and published.
    """
    engine, forge, containers, worktrees = make_engine(tmp_path, FakeExecutor())
    forge.add_ticket(14)
    run_id = engine._run_id(14)
    worktrees.create(run_id, "b", "x")
    engine.store.save(RunState(
        run_id=run_id, ticket_iid=14, stage=PUBLICATION_STAGE,
        lifecycle="validated", aegis_run_id=AEGIS_RUN,
        branch="feature/adore-14", base_ref="origin/develop",
        container=f"adore-run-{run_id}",
    ))
    containers.aegis.run_id = AEGIS_RUN
    containers.aegis.complete = True
    engine.poll_once()
    run = engine.store.load(run_id)
    assert run.lifecycle == "in-review"
    assert forge.mr_creations and forge.mr_creations[0]["source"] == "feature/adore-14"


# PUBLIC API / TESTS - operator commands: reset / cleanup (design 8c)


def test_reset_sets_the_stage_and_retry_continues_there(tmp_path: Path) -> None:
    """
    @brief   reset is state surgery on ADORE's pointer only: the run is left
             retry-able, and retry re-enters the stage loop, where AEGIS - not
             the reset value - decides which stage is current. AEGIS state is
             never touched. An invalid stage or unknown run fails cleanly.
    """
    engine, forge, containers, _ = make_engine(tmp_path, FakeExecutor())
    run_id = park_run(engine, forge)
    assert engine.reset(run_id, "check") is True
    run = engine.store.load(run_id)
    assert run.stage == "check" and run.lifecycle == "failed"
    assert engine.reset(run_id, "bogus") is False
    assert engine.reset("nope", "check") is False
    aegis_calls_before = len(containers.aegis.calls)
    assert containers.aegis.closes == []  # reset issued no AEGIS command
    assert len(containers.aegis.calls) == aegis_calls_before
    engine.executor.results = [gate_ok()] * 9
    assert engine.retry(run_id) is True
    assert engine.store.load(run_id).lifecycle == "in-review"
    # AEGIS still had the run at intake, so that is where conduction resumed
    assert "AEGIS INTAKE stage" in engine.executor.prompts[1]


def test_cleanup_sweeps_orphans_but_never_active_runs(tmp_path: Path) -> None:
    """
    @brief   cleanup clears a stale lock, removes containers/worktrees whose
             runs are terminal or unknown, keeps everything active, and only
             REPORTS corrupt state.
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


# PUBLIC API / TESTS - teardown (design 8b)
#
# The WSL bind-mount teardown-RACE retry itself now lives in
# WorktreeManager.remove (isolation.py, ADORE-ARCH-009) and is covered there
# (test_isolation.py). At this layer, _teardown is a thin pass-through: it
# calls worktrees.remove exactly once and, on any IsolationError, logs a husk
# message rather than retrying or crashing.


def test_teardown_logs_husk_on_worktree_removal_failure(tmp_path: Path) -> None:
    """
    @brief   _teardown makes exactly one worktree-removal attempt and logs a
             husk message on failure - it no longer retries itself; that is
             WorktreeManager.remove's job (ADORE-ARCH-009).
    """
    engine, _, _, worktrees = make_engine(tmp_path, FakeExecutor())
    logs: list[str] = []
    engine.log = logs.append
    run = RunState(run_id="r-15", ticket_iid=15, container="adore-run-r-15",
                   branch="feature/y")
    real = IsolationError("git failed", stderr="fatal: not a valid object name")
    worktrees.remove_errors = [real, real]

    engine._teardown(run, remove_worktree=True)

    assert worktrees.removed == []              # never succeeded
    assert len(worktrees.remove_errors) == 1    # only one attempt consumed
    assert any("husk left for `adore cleanup`" in line for line in logs)


# PUBLIC API / TESTS - metrics recording (design 13)


def test_terminal_states_record_metrics(tmp_path: Path) -> None:
    """
    @brief   A merged run lands one summary row (usage summed from journal
             events); a later escalation of another run adds its own row -
             never a duplicate for re-records.
    """
    from adore.metrics import load_summaries

    engine, forge, _, _ = make_engine(
        tmp_path,
        FakeExecutor([GateRun(exit_code=0, session_id="s", tokens_in=100,
                              tokens_out=10, cost_usd=0.01)] * 8),
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
    assert row.tokens_in == 800 and row.tokens_out == 80  # 8 launches
    assert abs(row.cost_usd - 0.08) < 1e-9
    assert row.executor_launches == 8
    assert row.gates_passed == 8  # one close per AEGIS stage
    assert row.time_to_mr_seconds >= 0 and row.mr_url


def test_metrics_disabled_records_nothing(tmp_path: Path) -> None:
    """
    @brief   [metrics] enabled=false switches recording off entirely.
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


def test_stage_allowlists_match_the_aegis_sequences() -> None:
    """
    @brief   The conductor's allowlists are exactly the AEGIS 2.x executable
             sequences (contract notes section 4): eight stages for the full
             profile, four for quick, with delivery closing both.
    """
    assert STANDARD_STAGES == ("intake", "alignment", "requirement", "design",
                               "check", "implementation", "validation",
                               "delivery")
    assert QUICK_STAGES == ("intake", "implementation", "validation",
                            "delivery")
    assert set(QUICK_STAGES) <= set(STANDARD_STAGES)
    assert PUBLICATION_STAGE not in STANDARD_STAGES


def test_parse_mr_iid_covers_all_three_platform_url_shapes() -> None:
    """
    @brief   The MR/PR number parses from GitLab, GitHub AND Gitea web URLs -
             Gitea uses plural "/pulls/N", which the original pattern missed;
             without the stored iid the post-MR poll cannot see terminal
             states. Garbage stays None.
    """
    parse = Orchestrator._parse_mr_iid
    assert parse("https://gitlab.example/g/p/-/merge_requests/29") == 29
    assert parse("https://github.com/o/r/pull/12") == 12
    assert parse("http://192.168.1.15:3001/o/r/pulls/30") == 30
    assert parse("http://gitea.local/o/r/issues/7") is None
    assert parse("not a url") is None


# PUBLIC API / TESTS - block classification (plan WP4)


def blocked(error: str = "", **extras) -> AegisResponse:
    """
    @brief      A blocked AEGIS response for classification tests.
    @param[in]  error The typed error text.
    @param[in]  extras Extra envelope fields.
    @return     The AegisResponse.
    """
    raw = {"status": "blocked", "stage": "check", "artifact": "none",
           "next": "aegis stage apply", "error": error, **extras}
    return AegisResponse(
        exit_code=1, status="blocked", stage="check", artifact="none",
        next_command="aegis stage apply", raw=raw,
    )


def test_classify_block_retries_only_a_live_persistence_lock() -> None:
    """
    @brief   A held OS lock is the one transient AEGIS failure: retry it. The
             rest of the integrity floor and every run-resolution error need a
             human, because ADORE never repairs AEGIS state.
    """
    lock = classify_block(blocked(
        "PERSISTENCE-LOCK-TIMEOUT: timed out after 15.0s waiting for x."
    ))
    assert lock.action == BLOCK_RETRY

    for code in ("GRAPH-STALE-UPDATE", "REQUIREMENT-STALE-UPDATE",
                 "RUN-POINTER-STALE", "RUN-ID-NOT-FOUND"):
        decision = classify_block(blocked(f"{code}: reload and retry."))
        assert decision.action == BLOCK_ESCALATE
        assert code in decision.reason


def test_classify_block_parks_on_human_attention_state() -> None:
    """
    @brief   Unresolved questions, an alignment pause, a repo-wide access
             request, and a routing request all need a human answer - they
             park, they do not end the run.
    """
    questions = classify_block(
        blocked("stage is not ready"),
        {"unresolved_questions": ["Which variant?"]},
    )
    assert questions.action == BLOCK_PARK

    pause = classify_block(blocked("stage is not ready"), {"decision": "pause"})
    assert pause.action == BLOCK_PARK and "pause" in pause.reason

    access = classify_block(
        blocked("stage is not ready"),
        {"requested_access_mode": "repo-wide"},
    )
    assert access.action == BLOCK_PARK and "repo-wide" in access.reason

    route = classify_block(blocked("stage is not ready"), {"route_to": "design"})
    assert route.action == BLOCK_PARK and "design" in route.reason


def test_classify_block_escalates_everything_else_with_remediation() -> None:
    """
    @brief   A waivable blocker is NOT auto-waived: it escalates, carrying the
             AEGIS error and its remediation for the human.
    """
    decision = classify_block(
        blocked("gate:test failed", remediation="Fix the failing test."),
        {"unresolved_questions": []},
    )
    assert decision.action == BLOCK_ESCALATE
    assert decision.reason == "gate:test failed"
    assert decision.hint == "Fix the failing test."


def test_recorded_questions_park_the_run(tmp_path: Path) -> None:
    """
    @brief   Questions the executor recorded in the AEGIS stage form park the
             run through the normal clarification flow, without the executor's
             questions file being involved at all.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    containers.aegis.stage_control["intake"] = {
        "unresolved_questions": ["Which variant should ship?"]
    }
    forge.add_ticket(14)

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "parked"
    assert containers.aegis.closes == []  # never closed a stage with questions
    posts = [c for c in forge.calls if c[0] == "post"]
    assert any("Which variant should ship?" in c[2] for c in posts)
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert "stage-questions" in events and "parked" in events


def test_reported_cost_over_the_cap_escalates_the_run(tmp_path: Path) -> None:
    """
    @brief   `[budgets] max_cost_usd` is a real bound, not a metrics label.
    @details Cost is summed from the journaled `usage` events and checked at
             the top of every stage iteration, so a misbehaving executor
             cannot spend unboundedly in dollars while staying inside the
             iteration and wall-clock budgets.
    """
    executor = FakeExecutor([gate_cost(2.0)] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14)

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    # $2 per launch against the $5.00 default: the check after the third
    # launch is the first to see a total over the cap
    assert run.outcome == "budget exceeded: cost $6.00"
    assert containers.aegis.closes == ["intake", "alignment", "requirement"]


def test_an_executor_reporting_no_cost_never_trips_the_budget(
    tmp_path: Path,
) -> None:
    """
    @brief   The cost cap is inert, not hair-trigger, when the executor
             reports tokens but no dollars.
    @details Executors that report zero cost still journal `usage` events, so
             the sum runs over real records and must stay at zero rather than
             tripping on their presence. The run walks the whole sequence.
    """
    executor = FakeExecutor([gate_cost(0.0) for _ in range(9)])
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14)

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "in-review"  # walked the whole sequence
    assert "cost" not in run.outcome
    assert list(containers.aegis.closes) == list(STANDARD_STAGES)
    usage = [e for e in engine.store.read_journal(run.run_id)
             if e["event"] == "usage"]
    assert usage and all(event["cost_usd"] == 0.0 for event in usage)


def test_an_escalation_posts_its_reason_on_the_ticket(tmp_path: Path) -> None:
    """
    @brief   An escalation reaches the operator watching the forge, not just
             the local journal.
    @details The edited status line only ever says "failed"; the AEGIS error,
             its remediation, and the composed `aegis waive add` hint used to
             exist only on the host. The dedicated comment carries all of it
             plus the `kind=escalation` marker.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14)
    containers.aegis.close_blocked["intake"] = "INV-7 does not hold."

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    posts = [call[2] for call in forge.calls if call[0] == "post" and call[1] == 14]
    escalations = [body for body in posts if "kind=escalation" in body]
    assert len(escalations) == 1
    body = escalations[0]
    assert run.outcome in body                      # the full reason, verbatim
    assert "INV-7 does not hold." in body           # including the AEGIS error
    assert f"adore logs {run.run_id}" in body
    assert f"adore retry {run.run_id}" in body


def test_a_forge_failure_during_the_escalation_post_still_fails_the_run(
    tmp_path: Path,
) -> None:
    """
    @brief   The escalation comment is best-effort: local state is
             authoritative, so a forge outage must not stop a run from
             reaching its terminal state.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14)
    containers.aegis.close_blocked["intake"] = "INV-7 does not hold."
    forge.post_fails_on = "Run escalated to failed"

    engine.poll_once()  # must return normally, not raise

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "INV-7 does not hold." in run.outcome
    assert any(call[0] == "post-refused" for call in forge.calls)
    events = [e["event"] for e in engine.store.read_journal(run.run_id)]
    assert "escalated" in events


def test_a_stale_working_run_is_escalated_and_frees_the_slot(
    tmp_path: Path,
) -> None:
    """
    @brief   A `working` run left behind by a dead conductor is escalated, not
             left to wedge pickup forever.
    @details With the default `max_concurrent_runs = 1` such a run silently
             stops the orchestrator: it counts against capacity and no
             reconciliation path used to revisit it. Reconciliation runs
             before the capacity check, so the freed slot is usable in the
             SAME poll pass.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14)
    forge.add_ticket(15)
    stale_id = crash_a_working_run(engine, 14, age_seconds=10_000)

    summary = engine.poll_once()

    stale = engine.store.load(stale_id)
    assert stale.lifecycle == "failed"
    assert "no live conductor" in stale.outcome
    assert f"adore retry {stale_id}" in stale.outcome
    events = [e["event"] for e in engine.store.read_journal(stale_id)]
    assert "stale-working-detected" in events and "escalated" in events
    # the ticket learns about it, not just the local journal
    assert any(call[0] in ("post", "edit") and call[1] == 14
               for call in forge.calls)
    # and the freed slot is used right away
    assert summary["picked"] == 15


def test_a_recently_updated_working_run_is_left_alone(tmp_path: Path) -> None:
    """
    @brief   Staleness is measured against the operator's own budgets, so a
             run that merely sits inside a long gate launch is never reaped
             out from under its live conductor.
    """
    engine, forge, containers, _ = make_engine(tmp_path, FakeExecutor())
    forge.add_ticket(14)
    forge.add_ticket(15)
    # older than one gate timeout, younger than wall clock + gate timeout
    fresh_id = crash_a_working_run(engine, 14, age_seconds=2_000)

    summary = engine.poll_once()

    assert engine.store.load(fresh_id).lifecycle == "working"
    events = [e["event"] for e in engine.store.read_journal(fresh_id)]
    assert "stale-working-detected" not in events
    assert summary.get("at_capacity") is True  # still holding the only slot
    assert summary["picked"] is None


def test_a_forge_failure_while_parking_escalates_with_the_questions(
    tmp_path: Path,
) -> None:
    """
    @brief   A ForgeError on the clarification post is fail-closed: the run
             cannot wait for an answer to a question nobody was asked, so the
             questions are journaled (the only copy left) and the run
             escalates instead of being stranded in `working`.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    containers.aegis.stage_control["intake"] = {
        "unresolved_questions": ["Which variant should ship?"]
    }
    forge.post_fails_on = "Clarification needed"
    forge.add_ticket(14)

    engine.poll_once()  # must return normally, not raise

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "failed to post the clarification comment" in run.outcome
    assert "questions preserved in the journal" in run.outcome
    journal = engine.store.read_journal(run.run_id)
    failed = [e for e in journal if e["event"] == "park-post-failed"]
    assert len(failed) == 1
    assert "Which variant should ship?" in failed[0]["questions"]
    assert "parked" not in [e["event"] for e in journal]


def test_a_held_lock_is_retried_once_then_escalates(tmp_path: Path) -> None:
    """
    @brief   A `stage close` blocked by a live persistence lock is retried once
             after a delay; a lock that is still held afterwards escalates
             instead of spinning.
    """
    slept: list[float] = []
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    engine.sleep = slept.append
    forge.add_ticket(14)
    containers.aegis.overrides[("stage", "close")] = CommandResult(
        exit_code=1,
        stdout=json.dumps({
            "status": "blocked", "stage": "intake", "artifact": "none",
            "next": "aegis stage close",
            "error": ("PERSISTENCE-LOCK-TIMEOUT: timed out after 15.0s "
                      "waiting for .agentic/.workspace/locks/run.lock."),
        }),
    )

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "persistence lock is still held" in run.outcome
    assert len(slept) == 1  # exactly one bounded retry
    blocked_events = [
        event for event in engine.store.read_journal(run.run_id)
        if event["event"] == "aegis-blocked"
    ]
    assert [event["action"] for event in blocked_events] == ["retry", "retry"]


def test_a_held_lock_at_run_start_escalates_instead_of_stranding(
    tmp_path: Path,
) -> None:
    """
    @brief   `run start` gets the same bounded lock retry as the stage loop: a
             lock still held on the second attempt escalates the run to failed
             rather than leaving it stranded in `working` with no conductor.
    """
    slept: list[float] = []
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    engine.sleep = slept.append
    forge.add_ticket(14)
    containers.aegis.start_blocked = (
        "PERSISTENCE-LOCK-TIMEOUT: timed out after 15.0s waiting for "
        ".agentic/.workspace/locks/run.lock."
    )

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "persistence lock is still held" in run.outcome
    starts = [call for call in containers.aegis.calls
              if call[2:4] == ["run", "start"]]
    assert len(starts) == 2  # the first attempt plus exactly one bounded retry
    assert len(slept) == 1
    blocked_events = [
        event for event in engine.store.read_journal(run.run_id)
        if event["event"] == "aegis-blocked"
    ]
    assert [event["action"] for event in blocked_events] == ["retry", "retry"]


def test_escalation_carries_the_exact_waive_command(tmp_path: Path) -> None:
    """
    @brief   ADORE never waives, so an escalation names the eligible blockers
             and the exact `aegis waive add` command a human would run.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14)
    containers.aegis.close_blocked["intake"] = "INV-7 does not hold."
    containers.aegis.overrides[("waive", "list")] = CommandResult(
        exit_code=0,
        stdout=json.dumps({
            "status": "ok", "stage": "intake", "artifact": "none",
            "next": "aegis stage close",
            "eligible_blockers": [{"id": "INV-7"}, {"id": "gate:test"}],
            "active_waivers": [], "waiver_history": [],
        }),
    )

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert 'aegis waive add INV-7 --reason "<why>"' in run.outcome
    assert 'aegis waive add gate:test --reason "<why>"' in run.outcome


def test_an_unavailable_waive_list_never_hides_the_original_error(
    tmp_path: Path,
) -> None:
    """
    @brief   The waive hint is advisory. If `waive list` itself is unusable the
             escalation still carries the AEGIS error that caused it - the part
             that must never be lost.
    """
    executor = FakeExecutor([gate_ok()] * 9)
    engine, forge, containers, _ = make_engine(tmp_path, executor)
    forge.add_ticket(14)
    containers.aegis.close_blocked["intake"] = "INV-7 does not hold."
    containers.aegis.overrides[("waive", "list")] = CommandResult(
        exit_code=2, stderr="usage: aegis [-h] ..."
    )

    engine.poll_once()

    run = engine.store.load(engine._run_id(14))
    assert run.lifecycle == "failed"
    assert "INV-7 does not hold." in run.outcome
    assert "aegis waive add" not in run.outcome


# PUBLIC API / TESTS - executor prompts (plan WP5)


def status_response(stage: str, quick: bool = False) -> AegisResponse:
    """
    @brief      A `run status` response for prompt composition tests.
    @param[in]  stage The reported stage.
    @param[in]  quick Whether the run uses the proportional profile.
    @return     The AegisResponse.
    """
    raw = {
        "status": "ok",
        "stage": stage,
        "artifact": f".agentic/runs/{AEGIS_RUN}/stages/{stage}/stage.toml",
        "next": "aegis stage apply",
        "run_id": AEGIS_RUN,
    }
    if quick:
        raw["run_profile"] = "quick"
    return AegisResponse(
        exit_code=0, status="ok", stage=stage, artifact=raw["artifact"],
        next_command="aegis stage apply", raw=raw,
    )


def test_every_stage_prompt_speaks_the_aegis_2x_vocabulary(
    tmp_path: Path,
) -> None:
    """
    @brief   Each of the eight stage prompts names its own AEGIS stage and
             tells the executor to work through the generated forms, not
             through CLI flags.
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor())
    ticket = forge.add_ticket(14, title="Refresh")
    for stage in STANDARD_STAGES:
        prompt = engine._gate_prompt(
            stage, ticket, "", "", status=status_response(stage),
            aegis_run_id=AEGIS_RUN,
        )
        assert f"AEGIS {stage.upper()} stage" in prompt
        assert "bash .agentic/tools/run.sh <group> <action>" in prompt
        assert "content goes into the generated forms, never into CLI flags" \
            in prompt
        assert "aegis stage apply" in prompt


def test_every_stage_prompt_forbids_closing_and_waiving(tmp_path: Path) -> None:
    """
    @brief   The two actions ADORE and humans reserve are refused in every
             stage prompt, including the revise prompt: `stage close` belongs
             to the delegated approver, `waive add` to a human.
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor())
    ticket = forge.add_ticket(14)
    for stage in (*STANDARD_STAGES, "revise"):
        prompt = engine._gate_prompt(stage, ticket, "", "",
                                     aegis_run_id=AEGIS_RUN)
        assert "NEVER run `aegis stage close`" in prompt
        assert "NEVER run `aegis waive add`" in prompt
        assert "NEVER push, open merge/pull requests, or merge" in prompt


def test_stage_prompt_pins_the_run_and_relays_the_next_command(
    tmp_path: Path,
) -> None:
    """
    @brief   The executor is told to pin the same `--run` the orchestrator
             pins, and is handed AEGIS's own exact next command plus the form
             path so it never has to guess either.
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor())
    ticket = forge.add_ticket(14)
    prompt = engine._gate_prompt(
        "design", ticket, "", "", status=status_response("design"),
        aegis_run_id=AEGIS_RUN,
    )
    assert f"`--run {AEGIS_RUN}`" in prompt
    assert "AEGIS says the exact next command is `aegis stage apply`." in prompt
    assert f".agentic/runs/{AEGIS_RUN}/stages/design/stage.toml" in prompt

    # before `run start` there is no run to pin, so no pin instruction
    unpinned = engine._gate_prompt("intake", ticket, "", "")
    assert "--run" not in unpinned


def test_quick_run_prompts_name_the_bypassed_stages(tmp_path: Path) -> None:
    """
    @brief   Quick implementation and validation prompts tell the executor that
             alignment, requirement, design, and check were bypassed, so it
             does not hunt for requirement rows, a design, or check IDs - and
             that the not-applicable audits are expected, not failures.
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor())
    ticket = forge.add_ticket(14)

    implementation = engine._gate_prompt(
        "implementation", ticket, "", "",
        status=status_response("implementation", quick=True),
        aegis_run_id=AEGIS_RUN,
    )
    assert "QUICK run" in implementation
    assert "were bypassed at intake" in implementation
    assert "aegis evidence prepare add" in implementation
    assert "linked_check_evidence" in implementation

    validation = engine._gate_prompt(
        "validation", ticket, "", "",
        status=status_response("validation", quick=True),
        aegis_run_id=AEGIS_RUN,
    )
    assert "not-applicable - quick run" in validation
    assert "not something to fix" in validation

    # a full run keeps the standard wording
    full = engine._gate_prompt(
        "implementation", ticket, "", "",
        status=status_response("implementation"), aegis_run_id=AEGIS_RUN,
    )
    assert "QUICK run" not in full
    assert "GREEN evidence" in full


def test_stage_prompt_names_both_question_channels(tmp_path: Path) -> None:
    """
    @brief   Questions may go into the stage form's control table (the primary
             AEGIS 2.x channel) or into the questions file (the secondary one);
             the prompt names both, and the conductor honors either.
    """
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor())
    ticket = forge.add_ticket(14)
    prompt = engine._gate_prompt("alignment", ticket, "", "")
    assert "`control.unresolved_questions`" in prompt
    assert engine.questions_file in prompt


def test_stage_timeout_overrides_bound_individual_launches(
    tmp_path: Path,
) -> None:
    """
    @brief   `[workflow] stage_timeout_overrides` raises the per-launch bound
             for the stages that need more room; every other stage keeps
             `[budgets] per_gate_timeout_seconds`.
    """
    config = make_config(tmp_path)
    config.budgets.per_gate_timeout_seconds = 1800
    config.workflow.stage_timeout_overrides = {"implementation": 5400}
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor([gate_ok()] * 8),
                                      config)
    forge.add_ticket(14)

    engine.poll_once()

    assert engine._stage_timeout("implementation") == 5400
    assert engine._stage_timeout("intake") == 1800
    assert engine._stage_timeout("delivery") == 1800


def test_kind_and_quick_labels_come_from_the_workflow_section(
    tmp_path: Path,
) -> None:
    """
    @brief   The AEGIS run kind and profile are resolved from ticket labels
             through `[workflow]`; the FIRST configured mapping the ticket
             matches wins, so overlapping labels stay deterministic.
    """
    config = make_config(tmp_path)
    config.workflow.kind_labels = {"defect": "fix", "tweak": "change"}
    config.workflow.quick_label = "ai-quick"
    engine, forge, _, _ = make_engine(tmp_path, FakeExecutor(), config)

    plain = forge.add_ticket(1, labels=["agent-ready", "P1"])
    assert engine._run_kind(plain) == ("feature", False)

    fix = forge.add_ticket(2, labels=["agent-ready", "P1", "defect", "ai-quick"])
    assert engine._run_kind(fix) == ("fix", True)

    both = forge.add_ticket(3, labels=["agent-ready", "P1", "tweak", "defect"])
    assert engine._run_kind(both) == ("fix", False)  # first mapping wins

    # the quick label cannot apply to a feature run - AEGIS forbids it
    feature_quick = forge.add_ticket(4, labels=["agent-ready", "P1", "ai-quick"])
    assert engine._run_kind(feature_quick) == ("feature", False)


# END OF FILE
