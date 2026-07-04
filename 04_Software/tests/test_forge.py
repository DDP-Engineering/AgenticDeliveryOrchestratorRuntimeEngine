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
@file test_forge.py
@brief Tests for the GitLab/GitHub adapters using a fake command runner.
@details No real glab/gh is invoked; the fake runner records every argv and
         returns canned CLI output, so both the command construction and the
         output parsing are verified offline.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.1.1
"""

from __future__ import annotations

# IMPORTS
import json
from pathlib import Path

from ador.forge import ForgeError, GitHubForge, GitLabForge, build_forge
from ador.util import CommandResult
import pytest

# DATA MODELS / TYPEDEFINITIONS


class FakeRunner:
    """
    @brief   Command runner double: records argv, replays canned results.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    def __init__(self, *results: CommandResult) -> None:
        """
        @brief      Queue the results to replay in order.
        @param[in]  results CommandResults returned call by call.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.1
        """
        self.results = list(results)
        self.calls: list[list[str]] = []
        self.cwds: list[str | None] = []

    def __call__(
        self,
        argv: list[str],
        *,
        cwd: str | Path | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        """
        @brief      Record the call (argv + cwd) and pop the next result.
        @param[in]  argv Command vector.
        @param[in]  cwd Recorded (MR creation needs a git checkout).
        @param[in]  timeout Ignored.
        @param[in]  env Ignored.
        @return     The next queued CommandResult.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.1
        """
        self.calls.append([str(part) for part in argv])
        self.cwds.append(str(cwd) if cwd is not None else None)
        return self.results.pop(0)


# HELPER FUNCTIONS


def _ok(stdout: str = "") -> CommandResult:
    """
    @brief      A successful canned result.
    @param[in]  stdout Canned stdout.
    @return     CommandResult with exit code 0.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    return CommandResult(exit_code=0, stdout=stdout)


def _fail(stderr: str, exit_code: int = 1) -> CommandResult:
    """
    @brief      A failing canned result.
    @param[in]  stderr Canned stderr.
    @param[in]  exit_code Non-zero exit code.
    @return     The failing CommandResult.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    return CommandResult(exit_code=exit_code, stderr=stderr)


# PUBLIC API / TESTS - factory


def test_build_forge_selects_adapter() -> None:
    """
    @brief   The factory maps kind to the right adapter and rejects others.
    @version 0.1.0
    """
    assert isinstance(build_forge("gitlab", "g/p"), GitLabForge)
    assert isinstance(build_forge("github", "o/r"), GitHubForge)
    with pytest.raises(ValueError):
        build_forge("bitbucket", "x")


# PUBLIC API / TESTS - GitLab


def test_gitlab_list_ready_maps_json() -> None:
    """
    @brief   glab issue list JSON maps to normalized Tickets.
    @version 0.1.0
    """
    payload = json.dumps(
        [
            {
                "iid": 14,
                "title": "Global Refresh button",
                "description": "AC: ...",
                "labels": ["agent-ready", "P2"],
                "author": {"username": "dan.pasare"},
                "state": "opened",
                "web_url": "https://gitlab.example/i/14",
                "created_at": "2026-07-01T10:00:00Z",
                "updated_at": "2026-07-02T09:00:00Z",
            }
        ]
    )
    runner = FakeRunner(_ok(payload))
    tickets = GitLabForge("grp/proj", runner).list_ready("agent-ready")
    assert len(tickets) == 1
    ticket = tickets[0]
    assert (ticket.iid, ticket.author, ticket.labels) == (
        14,
        "dan.pasare",
        ["agent-ready", "P2"],
    )
    argv = runner.calls[0]
    assert argv[:3] == ["glab", "issue", "list"]
    assert "--repo" in argv and "grp/proj" in argv
    assert "--label" in argv and "agent-ready" in argv
    assert "--output" in argv and "json" in argv


def test_gitlab_get_ticket_returns_none_on_404() -> None:
    """
    @brief   A deleted ticket yields None; other failures raise ForgeError.
    @version 0.1.0
    """
    forge = GitLabForge("g/p", FakeRunner(_fail("404 Not Found")))
    assert forge.get_ticket(99) is None
    forge = GitLabForge("g/p", FakeRunner(_fail("connection refused")))
    with pytest.raises(ForgeError):
        forge.get_ticket(99)


def test_gitlab_post_comment_parses_note_id() -> None:
    """
    @brief   The note id comes from the "#note_<id>" URL glab prints.
    @version 0.1.0
    """
    runner = FakeRunner(_ok("https://gitlab.example/grp/proj/-/issues/14#note_9876\n"))
    note_id = GitLabForge("grp/proj", runner).post_comment(14, "[ADOR] hello")
    assert note_id == 9876
    argv = runner.calls[0]
    assert argv[:3] == ["glab", "issue", "note"]
    assert "--message" in argv


def test_gitlab_post_comment_falls_back_to_note_list() -> None:
    """
    @brief   When glab prints no URL, the id is recovered from the notes API.
    @version 0.1.0
    """
    notes = json.dumps(
        [
            {"id": 1, "body": "older", "author": {"username": "x"}, "system": False},
            {"id": 42, "body": "[ADOR] hello", "author": {"username": "x"}, "system": False},
        ]
    )
    runner = FakeRunner(_ok("created."), _ok(notes))
    assert GitLabForge("g/p", runner).post_comment(14, "[ADOR] hello") == 42


def test_gitlab_edit_comment_uses_api_put() -> None:
    """
    @brief   Note editing is `glab api --method PUT` with the encoded project
             path (glab has no note-edit subcommand; prereq report section 4)
             and the body as --raw-field (guaranteed string, no type
             inference).
    @version 0.1.1
    """
    runner = FakeRunner(_ok("{}"))
    GitLabForge("grp/sub/proj", runner).edit_comment(14, 9876, "updated body")
    argv = runner.calls[0]
    assert argv[:2] == ["glab", "api"]
    assert "--method" in argv and "PUT" in argv
    assert "projects/grp%2Fsub%2Fproj/issues/14/notes/9876" in argv
    assert "--raw-field" in argv and "body=updated body" in argv
    assert "--field" not in argv  # --field would type-infer the body


def test_gitlab_list_comments_flags_system_notes() -> None:
    """
    @brief   System notes are flagged so resume detection can skip them.
    @version 0.1.0
    """
    notes = json.dumps(
        [
            {
                "id": 1,
                "body": "changed label",
                "author": {"username": "dan"},
                "created_at": "t1",
                "system": True,
            },
            {
                "id": 2,
                "body": "real answer",
                "author": {"username": "dan"},
                "created_at": "t2",
                "system": False,
            },
        ]
    )
    comments = GitLabForge("g/p", FakeRunner(_ok(notes))).list_comments(14)
    assert [comment.system for comment in comments] == [True, False]


def test_gitlab_labels_and_mr() -> None:
    """
    @brief   Label updates use --label/--unlabel; MR creation is draft with
             reviewers and prints back the URL.
    @version 0.1.0
    """
    runner = FakeRunner(_ok(), _ok(), _ok("https://gitlab.example/g/p/-/merge_requests/7\n"))
    forge = GitLabForge("g/p", runner)
    forge.add_labels(14, ["agent-working"])
    forge.remove_labels(14, ["agent-ready"])
    url = forge.open_merge_request(
        "ador/run-14", "develop", "Draft: fix", "body", reviewers=["dan.pasare"],
        cwd="/tmp/worktree",
    )
    assert url == "https://gitlab.example/g/p/-/merge_requests/7"
    add_argv, remove_argv, mr_argv = runner.calls
    assert "--label" in add_argv and "agent-working" in add_argv
    assert "--unlabel" in remove_argv and "agent-ready" in remove_argv
    assert "--draft" in mr_argv
    assert "--reviewer" in mr_argv
    assert "merge" not in mr_argv  # the adapter can never merge
    # MR creation runs inside the worktree: glab resolves remotes from a
    # local checkout even with --repo (live finding 2026-07-04)
    assert runner.cwds[-1] == "/tmp/worktree"


# PUBLIC API / TESTS - GitHub


def test_github_list_ready_maps_json() -> None:
    """
    @brief   gh issue list JSON (label objects, OPEN state) is normalized.
    @version 0.1.0
    """
    payload = json.dumps(
        [
            {
                "number": 3,
                "title": "T",
                "body": "B",
                "labels": [{"name": "agent-ready"}, {"name": "P1"}],
                "author": {"login": "octo"},
                "state": "OPEN",
                "url": "https://github.com/o/r/issues/3",
                "createdAt": "t1",
                "updatedAt": "t2",
            }
        ]
    )
    runner = FakeRunner(_ok(payload))
    tickets = GitHubForge("o/r", runner).list_ready("agent-ready")
    assert tickets[0].labels == ["agent-ready", "P1"]
    assert tickets[0].state == "opened"
    assert tickets[0].author == "octo"
    assert runner.calls[0][:3] == ["gh", "issue", "list"]


def test_github_post_and_edit_comment() -> None:
    """
    @brief   Comment id parses from the issuecomment URL; edits go through
             the REST API with PATCH and a --raw-field string body.
    @version 0.1.1
    """
    runner = FakeRunner(
        _ok("https://github.com/o/r/issues/3#issuecomment-555\n"),
        _ok("{}"),
    )
    forge = GitHubForge("o/r", runner)
    assert forge.post_comment(3, "[ADOR] hi") == 555
    forge.edit_comment(3, 555, "new body")
    edit_argv = runner.calls[1]
    assert "--method" in edit_argv and "PATCH" in edit_argv
    assert "repos/o/r/issues/comments/555" in edit_argv
    assert "--raw-field" in edit_argv and "body=new body" in edit_argv
    assert "--field" not in edit_argv  # --field would type-infer the body


def test_github_open_pr_draft() -> None:
    """
    @brief   PR creation is draft with head/base and returns the URL.
    @version 0.1.0
    """
    runner = FakeRunner(_ok("https://github.com/o/r/pull/12\n"))
    url = GitHubForge("o/r", runner).open_merge_request(
        "ador/run-3", "develop", "Draft: fix", "body", reviewers=["octo"]
    )
    assert url == "https://github.com/o/r/pull/12"
    argv = runner.calls[0]
    assert argv[:3] == ["gh", "pr", "create"]
    assert "--draft" in argv
    assert "--head" in argv and "ador/run-3" in argv
    assert "--base" in argv and "develop" in argv


def test_github_get_ticket_not_found() -> None:
    """
    @brief   gh "could not resolve" failures map to None.
    @version 0.1.0
    """
    forge = GitHubForge("o/r", FakeRunner(_fail("could not resolve to an Issue")))
    assert forge.get_ticket(404) is None


def test_forge_error_carries_context() -> None:
    """
    @brief   ForgeError includes the command and stderr for the journal.
    @version 0.1.0
    """
    forge = GitLabForge("g/p", FakeRunner(_fail("rate limited", exit_code=4)))
    with pytest.raises(ForgeError) as excinfo:
        forge.list_ready("agent-ready")
    assert "rate limited" in str(excinfo.value)
    assert "glab issue" in str(excinfo.value)


# PUBLIC API / TESTS - hostile CLI output (negative paths)


def test_gitlab_invalid_json_raises_forge_error() -> None:
    """
    @brief   Non-JSON CLI output (HTML error page, warning text) raises
             ForgeError instead of crashing or returning garbage.
    @version 0.1.0
    """
    forge = GitLabForge("g/p", FakeRunner(_ok("WARNING: something\nnot json")))
    with pytest.raises(ForgeError):
        forge.list_ready("agent-ready")


def test_gitlab_unexpected_json_shape_raises() -> None:
    """
    @brief   Valid JSON of the wrong top-level shape is rejected.
    @version 0.1.0
    """
    forge = GitLabForge("g/p", FakeRunner(_ok('{"iid": 1}')))
    with pytest.raises(ForgeError):
        forge.list_ready("agent-ready")


def test_gitlab_empty_ready_list_is_not_an_error() -> None:
    """
    @brief   No eligible tickets is a normal outcome, not a failure.
    @version 0.1.0
    """
    assert GitLabForge("g/p", FakeRunner(_ok("[]"))).list_ready("agent-ready") == []


def test_gitlab_mr_create_without_url_raises() -> None:
    """
    @brief   `glab mr create` succeeding without printing an MR URL fails
             closed (the orchestrator must never guess the MR address).
    @version 0.1.0
    """
    forge = GitLabForge("g/p", FakeRunner(_ok("something changed, no url printed")))
    with pytest.raises(ForgeError):
        forge.open_merge_request("s", "develop", "Draft: t", "b")


def test_gitlab_post_comment_id_unrecoverable_raises() -> None:
    """
    @brief   When neither the URL nor the notes fallback yields the note id,
             posting fails closed (the id is required for idempotency).
    @version 0.1.0
    """
    runner = FakeRunner(_ok("no url in output"), _ok("[]"))
    with pytest.raises(ForgeError):
        GitLabForge("g/p", runner).post_comment(14, "[ADOR] question")


def test_github_invalid_json_raises_forge_error() -> None:
    """
    @brief   Non-JSON gh output raises ForgeError.
    @version 0.1.0
    """
    forge = GitHubForge("o/r", FakeRunner(_ok("<html>rate limited</html>")))
    with pytest.raises(ForgeError):
        forge.list_ready("agent-ready")


def test_github_pr_create_without_url_raises() -> None:
    """
    @brief   `gh pr create` succeeding with empty output fails closed.
    @version 0.1.0
    """
    forge = GitHubForge("o/r", FakeRunner(_ok("")))
    with pytest.raises(ForgeError):
        forge.open_merge_request("s", "develop", "Draft: t", "b")


# END OF FILE
