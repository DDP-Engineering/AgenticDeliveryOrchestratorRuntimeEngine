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
@brief Tests for the GitLab/GitHub/Gitea adapters using a fake command runner.
@details No real glab/gh/tea is invoked; the fake runner records every argv and
         returns canned CLI output, so both the command construction and the
         output parsing are verified offline.
"""

from __future__ import annotations

# IMPORTS
import json
from pathlib import Path

from adore.forge import ForgeError, GiteaForge, GitHubForge, GitLabForge, build_forge
from adore.util import CommandResult
import pytest

# DATA MODELS / TYPEDEFINITIONS


class FakeRunner:
    """
    @brief   Command runner double: records argv, replays canned results.
    """

    def __init__(self, *results: CommandResult) -> None:
        """
        @brief      Queue the results to replay in order.
        @param[in]  results CommandResults returned call by call.
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
    """
    return CommandResult(exit_code=0, stdout=stdout)


def _api_ok(stdout: str = "", status: int = 200, headers: str = "") -> CommandResult:
    """
    @brief      A canned `tea api -i` result: body on stdout, status+headers
                on stderr, ALWAYS exit 0 (tea does not fail on HTTP errors).
    @param[in]  stdout Canned response body.
    @param[in]  status HTTP status code for the stderr status line.
    @param[in]  headers Extra header lines for stderr (e.g. X-Total-Count).
    @return     CommandResult mimicking tea api -i.
    """
    stderr = f"HTTP/1.1 {status} X\n{headers}"
    return CommandResult(exit_code=0, stdout=stdout, stderr=stderr)


def _fail(stderr: str, exit_code: int = 1) -> CommandResult:
    """
    @brief      A failing canned result.
    @param[in]  stderr Canned stderr.
    @param[in]  exit_code Non-zero exit code.
    @return     The failing CommandResult.
    """
    return CommandResult(exit_code=exit_code, stderr=stderr)


# PUBLIC API / TESTS - factory


def test_build_forge_selects_adapter() -> None:
    """
    @brief   The factory maps kind to the right adapter, wires the gitea
             login through, and rejects unknown kinds and a login on a
             platform that has no login concept.
    """
    assert isinstance(build_forge("gitlab", "g/p"), GitLabForge)
    assert isinstance(build_forge("github", "o/r"), GitHubForge)
    gitea = build_forge("gitea", "o/r", login="home")
    assert isinstance(gitea, GiteaForge)
    assert gitea.login == "home"
    with pytest.raises(ValueError):
        build_forge("bitbucket", "x")
    with pytest.raises(ValueError):
        build_forge("gitlab", "g/p", login="home")


# PUBLIC API / TESTS - GitLab


def test_gitlab_list_ready_maps_json() -> None:
    """
    @brief   glab issue list JSON maps to normalized Tickets.
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
    """
    forge = GitLabForge("g/p", FakeRunner(_fail("404 Not Found")))
    assert forge.get_ticket(99) is None
    forge = GitLabForge("g/p", FakeRunner(_fail("connection refused")))
    with pytest.raises(ForgeError):
        forge.get_ticket(99)


def test_gitlab_post_comment_parses_note_id() -> None:
    """
    @brief   The note id comes from the "#note_<id>" URL glab prints.
    """
    runner = FakeRunner(_ok("https://gitlab.example/grp/proj/-/issues/14#note_9876\n"))
    note_id = GitLabForge("grp/proj", runner).post_comment(14, "[ADORE] hello")
    assert note_id == 9876
    argv = runner.calls[0]
    assert argv[:3] == ["glab", "issue", "note"]
    assert "--message" in argv


def test_gitlab_post_comment_falls_back_to_note_list() -> None:
    """
    @brief   When glab prints no URL, the id is recovered from the notes API.
    """
    notes = json.dumps(
        [
            {"id": 1, "body": "older", "author": {"username": "x"}, "system": False},
            {"id": 42, "body": "[ADORE] hello", "author": {"username": "x"}, "system": False},
        ]
    )
    runner = FakeRunner(_ok("created."), _ok(notes))
    assert GitLabForge("g/p", runner).post_comment(14, "[ADORE] hello") == 42


def test_gitlab_edit_comment_uses_api_put() -> None:
    """
    @brief   Note editing is `glab api --method PUT` with the encoded project
             path (glab has no note-edit subcommand; prereq report section 4)
             and the body as --raw-field (guaranteed string, no type
             inference).
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
    """
    runner = FakeRunner(_ok(), _ok(), _ok("https://gitlab.example/g/p/-/merge_requests/7\n"))
    forge = GitLabForge("g/p", runner)
    forge.add_labels(14, ["agent-working"])
    forge.remove_labels(14, ["agent-ready"])
    url = forge.open_merge_request(
        "adore/run-14", "develop", "Draft: fix", "body", reviewers=["dan.pasare"],
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
    """
    runner = FakeRunner(
        _ok("https://github.com/o/r/issues/3#issuecomment-555\n"),
        _ok("{}"),
    )
    forge = GitHubForge("o/r", runner)
    assert forge.post_comment(3, "[ADORE] hi") == 555
    forge.edit_comment(3, 555, "new body")
    edit_argv = runner.calls[1]
    assert "--method" in edit_argv and "PATCH" in edit_argv
    assert "repos/o/r/issues/comments/555" in edit_argv
    assert "--raw-field" in edit_argv and "body=new body" in edit_argv
    assert "--field" not in edit_argv  # --field would type-infer the body


def test_github_open_pr_draft() -> None:
    """
    @brief   PR creation is draft with head/base and returns the URL.
    """
    runner = FakeRunner(_ok("https://github.com/o/r/pull/12\n"))
    url = GitHubForge("o/r", runner).open_merge_request(
        "adore/run-3", "develop", "Draft: fix", "body", reviewers=["octo"]
    )
    assert url == "https://github.com/o/r/pull/12"
    argv = runner.calls[0]
    assert argv[:3] == ["gh", "pr", "create"]
    assert "--draft" in argv
    assert "--head" in argv and "adore/run-3" in argv
    assert "--base" in argv and "develop" in argv


def test_github_get_ticket_not_found() -> None:
    """
    @brief   gh "could not resolve" failures map to None.
    """
    forge = GitHubForge("o/r", FakeRunner(_fail("could not resolve to an Issue")))
    assert forge.get_ticket(404) is None


def test_github_get_pr_requests_and_maps_labels() -> None:
    """
    @brief   `get_merge_request` requests the labels field AND maps GitHub's
             label objects to plain names - so the revise-label trigger sees
             them. gh returns only the fields named in --json, so a missing
             `labels` field would silently yield an empty label list.
    """
    payload = json.dumps(
        {
            "number": 7,
            "state": "OPEN",
            "url": "https://github.com/o/r/pull/7",
            "isDraft": True,
            "labels": [{"name": "agent-revise"}, {"name": "P1"}],
        }
    )
    runner = FakeRunner(_ok(payload))
    mr = GitHubForge("o/r", runner).get_merge_request(7)
    assert mr is not None
    assert mr.iid == 7
    assert mr.state == "opened"
    assert mr.draft is True
    assert mr.labels == ["agent-revise", "P1"]
    # the field set MUST carry labels or the revise trigger goes blind
    json_arg = runner.calls[0][runner.calls[0].index("--json") + 1]
    assert "labels" in json_arg.split(",")


def test_github_get_pr_not_found() -> None:
    """
    @brief   A missing PR (404) maps to None rather than raising.
    """
    forge = GitHubForge("o/r", FakeRunner(_fail("could not resolve to a PullRequest")))
    assert forge.get_merge_request(404) is None


def test_forge_error_carries_context() -> None:
    """
    @brief   ForgeError includes the command and stderr for the journal.
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
    """
    forge = GitLabForge("g/p", FakeRunner(_ok("WARNING: something\nnot json")))
    with pytest.raises(ForgeError):
        forge.list_ready("agent-ready")


def test_gitlab_unexpected_json_shape_raises() -> None:
    """
    @brief   Valid JSON of the wrong top-level shape is rejected.
    """
    forge = GitLabForge("g/p", FakeRunner(_ok('{"iid": 1}')))
    with pytest.raises(ForgeError):
        forge.list_ready("agent-ready")


def test_gitlab_empty_ready_list_is_not_an_error() -> None:
    """
    @brief   No eligible tickets is a normal outcome, not a failure.
    """
    assert GitLabForge("g/p", FakeRunner(_ok("[]"))).list_ready("agent-ready") == []


def test_gitlab_mr_create_without_url_raises() -> None:
    """
    @brief   `glab mr create` succeeding without printing an MR URL fails
             closed (the orchestrator must never guess the MR address).
    """
    forge = GitLabForge("g/p", FakeRunner(_ok("something changed, no url printed")))
    with pytest.raises(ForgeError):
        forge.open_merge_request("s", "develop", "Draft: t", "b")


def test_gitlab_post_comment_id_unrecoverable_raises() -> None:
    """
    @brief   When neither the URL nor the notes fallback yields the note id,
             posting fails closed (the id is required for idempotency).
    """
    runner = FakeRunner(_ok("no url in output"), _ok("[]"))
    with pytest.raises(ForgeError):
        GitLabForge("g/p", runner).post_comment(14, "[ADORE] question")


def test_github_invalid_json_raises_forge_error() -> None:
    """
    @brief   Non-JSON gh output raises ForgeError.
    """
    forge = GitHubForge("o/r", FakeRunner(_ok("<html>rate limited</html>")))
    with pytest.raises(ForgeError):
        forge.list_ready("agent-ready")


def test_github_pr_create_without_url_raises() -> None:
    """
    @brief   `gh pr create` succeeding with empty output fails closed.
    """
    forge = GitHubForge("o/r", FakeRunner(_ok("")))
    with pytest.raises(ForgeError):
        forge.open_merge_request("s", "develop", "Draft: t", "b")


# PUBLIC API / TESTS - Gitea


def test_gitea_repo_must_be_owner_repo() -> None:
    """
    @brief   Gitea has no subgroups: anything but OWNER/REPO fails closed at
             construction, before it can build malformed API endpoints.
    """
    with pytest.raises(ValueError):
        GiteaForge("owner/group/repo", FakeRunner())
    with pytest.raises(ValueError):
        GiteaForge("just-owner", FakeRunner())


def test_gitea_list_ready_maps_rest_json() -> None:
    """
    @brief   The issues REST payload is normalized: number to iid, label
             objects to names, user.login (never the display name), state
             open -> opened. The argv must filter type=issues (the endpoint
             returns PRs too), carry --login, and never start the endpoint
             with "/" (that breaks tea's /api/v1 prefixing).
    """
    payload = json.dumps(
        [
            {
                "number": 45,
                "title": "Refresh button",
                "body": "AC: ...",
                "labels": [{"name": "agent-ready"}, {"name": "P2"}],
                "user": {"login": "dpasare", "full_name": "Dan Dumitru Pasare"},
                "state": "open",
                "html_url": "http://gitea.local/o/r/issues/45",
                "created_at": "t1",
                "updated_at": "t2",
            }
        ]
    )
    runner = FakeRunner(_api_ok(payload))
    tickets = GiteaForge("o/r", runner, login="home").list_ready("agent-ready")
    assert len(tickets) == 1
    ticket = tickets[0]
    assert (ticket.iid, ticket.author, ticket.labels, ticket.state) == (
        45,
        "dpasare",
        ["agent-ready", "P2"],
        "opened",
    )
    argv = runner.calls[0]
    assert argv[:2] == ["tea", "api"]
    assert "-i" in argv  # the HTTP status line is the only error signal
    assert "--login" in argv and "home" in argv
    endpoint = argv[-1]
    assert not endpoint.startswith("/")
    assert endpoint.startswith("repos/o/r/issues?")
    assert "type=issues" in endpoint
    assert "labels=agent-ready" in endpoint
    assert "state=open" in endpoint


def test_gitea_list_ready_paginates_by_total_count() -> None:
    """
    @brief   Pagination follows X-Total-Count: a SHORT page must not stop the
             walk when the server clamps pages below the requested size
             (MAX_RESPONSE_ITEMS), and the pool is complete when the count is
             reached.
    """
    page = json.dumps(
        [{"number": i, "labels": [{"name": "agent-ready"}]} for i in range(20)]
    )
    runner = FakeRunner(
        _api_ok(page, headers="X-Total-Count: 40\n"),
        _api_ok(page, headers="X-Total-Count: 40\n"),
    )
    tickets = GiteaForge("o/r", runner).list_ready("agent-ready")
    assert len(tickets) == 40
    assert len(runner.calls) == 2
    assert "page=1" in runner.calls[0][-1]
    assert "page=2" in runner.calls[1][-1]


def test_gitea_list_ready_post_filters_unknown_label() -> None:
    """
    @brief   When the filter label does not exist in the repository, Gitea
             silently DROPS the labels= filter and returns every open issue
             (live finding, 1.25.4) - the adapter must post-filter so a typo'd
             ready label cannot select the entire backlog.
    """
    unfiltered = json.dumps(
        [
            {"number": 1, "title": "unrelated", "labels": []},
            {"number": 2, "title": "ready", "labels": [{"name": "agent-ready"}]},
        ]
    )
    tickets = GiteaForge("o/r", FakeRunner(_api_ok(unfiltered))).list_ready("agent-ready")
    assert [t.iid for t in tickets] == [2]
    assert GiteaForge("o/r", FakeRunner(_api_ok(unfiltered))).list_ready("typo-label") == []


def test_gitea_list_ready_short_page_stops_without_total_count() -> None:
    """
    @brief   Without the X-Total-Count header a short page ends the walk; an
             empty page ends it even when a (lying) header promises more.
    """
    runner = FakeRunner(
        _api_ok(json.dumps([{"number": 1, "labels": [{"name": "agent-ready"}]}]))
    )
    assert len(GiteaForge("o/r", runner).list_ready("agent-ready")) == 1
    assert len(runner.calls) == 1
    runner = FakeRunner(_api_ok("[]", headers="X-Total-Count: 10\n"))
    assert GiteaForge("o/r", runner).list_ready("agent-ready") == []
    assert len(runner.calls) == 1


def test_gitea_http_error_despite_exit_zero() -> None:
    """
    @brief   tea api exits 0 even on HTTP errors (verified live on tea 0.15),
             so the adapter must read the status line itself: 404 maps to None
             where the contract allows, any other >= 400 raises, and a missing
             status line fails closed.
    """
    not_found = _api_ok('{"errors":null,"message":"not found"}', status=404)
    assert GiteaForge("o/r", FakeRunner(not_found)).get_ticket(99) is None
    assert GiteaForge("o/r", FakeRunner(not_found)).get_merge_request(99) is None
    with pytest.raises(ForgeError):  # list_ready must NOT swallow a 404
        GiteaForge("o/r", FakeRunner(not_found)).list_ready("agent-ready")
    with pytest.raises(ForgeError):
        GiteaForge("o/r", FakeRunner(_api_ok("{}", status=500))).get_ticket(1)
    no_status = CommandResult(exit_code=0, stdout="[]", stderr="")
    with pytest.raises(ForgeError):
        GiteaForge("o/r", FakeRunner(no_status)).list_ready("agent-ready")


def test_gitea_tea_failure_carries_context() -> None:
    """
    @brief   A tea-level failure (no login, network down) raises ForgeError
             with the argv and stderr for the journal.
    """
    forge = GiteaForge("o/r", FakeRunner(_fail("Error: no login found")))
    with pytest.raises(ForgeError) as excinfo:
        forge.list_ready("agent-ready")
    assert "no login found" in str(excinfo.value)
    assert "tea api" in str(excinfo.value)


def test_gitea_invalid_json_and_wrong_shape_raise() -> None:
    """
    @brief   A 200 with a non-JSON body (proxy page) or the wrong JSON shape
             is rejected instead of parsed into garbage.
    """
    with pytest.raises(ForgeError):
        GiteaForge("o/r", FakeRunner(_api_ok("<html>proxy</html>"))).list_ready("x")
    with pytest.raises(ForgeError):
        GiteaForge("o/r", FakeRunner(_api_ok('{"number": 1}'))).list_ready("x")


def test_gitea_list_comments_maps_and_never_flags_system() -> None:
    """
    @brief   Comments map id/body/user.login/created_at; Gitea keeps system
             events out of this endpoint, so system is always False.
    """
    payload = json.dumps(
        [
            {"id": 7, "body": "[ADORE] status", "user": {"login": "dpasare"},
             "created_at": "t1"},
            {"id": 8, "body": "answer", "user": {"login": "reviewer"},
             "created_at": "t2"},
        ]
    )
    comments = GiteaForge("o/r", FakeRunner(_api_ok(payload))).list_comments(45)
    assert [(c.id, c.author, c.system) for c in comments] == [
        (7, "dpasare", False),
        (8, "reviewer", False),
    ]


def test_gitea_post_comment_id_from_response_json() -> None:
    """
    @brief   The created comment id comes from the POST response JSON (no URL
             scraping); a response without an id fails closed - the id is
             required for idempotency.
    """
    runner = FakeRunner(_api_ok('{"id": 321, "body": "[ADORE] hello"}'))
    assert GiteaForge("o/r", runner).post_comment(45, "[ADORE] hello") == 321
    argv = runner.calls[0]
    assert "--method" in argv and "POST" in argv
    assert "--field" in argv and "body=[ADORE] hello" in argv
    assert argv[-1] == "repos/o/r/issues/45/comments"
    with pytest.raises(ForgeError):
        GiteaForge("o/r", FakeRunner(_api_ok("{}"))).post_comment(45, "x")


def test_gitea_edit_comment_patches_repo_global_id() -> None:
    """
    @brief   Comment edits PATCH the repo-global comment id with a
             guaranteed-string --field body.
    """
    runner = FakeRunner(_api_ok("{}"))
    GiteaForge("o/r", runner).edit_comment(45, 321, "updated body")
    argv = runner.calls[0]
    assert "--method" in argv and "PATCH" in argv
    assert argv[-1] == "repos/o/r/issues/comments/321"
    assert "--field" in argv and "body=updated body" in argv


def test_gitea_labels_via_tea_edit_subcommands() -> None:
    """
    @brief   Label ops go through `tea issues edit` / `tea pulls edit` (they
             resolve label NAMES to ids); empty lists make no call; the
             configured login is carried; failures raise ForgeError.
    """
    runner = FakeRunner(_ok(), _ok(), _ok())
    forge = GiteaForge("o/r", runner, login="home")
    forge.add_labels(45, ["agent-working", "P2"])
    forge.remove_labels(45, ["agent-ready"])
    forge.remove_mr_labels(30, ["agent-revise"])
    add_argv, remove_argv, mr_argv = runner.calls
    assert add_argv[:4] == ["tea", "issues", "edit", "45"]
    assert "--add-labels" in add_argv and "agent-working,P2" in add_argv
    assert "--remove-labels" in remove_argv and "agent-ready" in remove_argv
    assert mr_argv[:4] == ["tea", "pulls", "edit", "30"]
    assert "--remove-labels" in mr_argv and "agent-revise" in mr_argv
    for argv in runner.calls:
        assert "--login" in argv and "home" in argv
    forge.add_labels(45, [])  # no queued result left: a call would pop-fail
    with pytest.raises(ForgeError):
        GiteaForge("o/r", FakeRunner(_fail("Error: not found"))).add_labels(1, ["x"])


def test_gitea_get_pr_normalizes_merged_and_draft() -> None:
    """
    @brief   Gitea reports merged PRs as state closed + merged true - the
             normalization must say "merged" (the post-MR poll's terminal
             signal). Draft is the native field, with the WIP title prefix as
             fallback; labels map to names.
    """
    merged = json.dumps(
        {"number": 29, "state": "closed", "merged": True, "draft": False,
         "title": "feat x", "html_url": "http://g/o/r/pulls/29",
         "labels": [{"name": "P1"}]}
    )
    mr = GiteaForge("o/r", FakeRunner(_api_ok(merged))).get_merge_request(29)
    assert mr is not None
    assert (mr.iid, mr.state, mr.draft, mr.labels) == (29, "merged", False, ["P1"])
    wip_only = json.dumps(
        {"number": 30, "state": "open", "merged": False,
         "title": "WIP: feat y", "html_url": "http://g/o/r/pulls/30"}
    )
    mr = GiteaForge("o/r", FakeRunner(_api_ok(wip_only))).get_merge_request(30)
    assert mr is not None
    assert mr.state == "opened"
    assert mr.draft is True  # WIP title fallback for payloads without `draft`


def test_gitea_get_pr_by_branch_scans_open_pulls() -> None:
    """
    @brief   A branch ref scans the OPEN pulls for a matching head.ref
             (branch lookup finds only open MRs, per the interface contract);
             no match maps to None.
    """
    pulls = json.dumps(
        [
            {"number": 7, "state": "open", "title": "other",
             "head": {"ref": "adore/run-7"}, "html_url": "http://g/o/r/pulls/7"},
            {"number": 8, "state": "open", "title": "WIP: mine",
             "head": {"ref": "adore/run-45"}, "html_url": "http://g/o/r/pulls/8"},
        ]
    )
    runner = FakeRunner(_api_ok(pulls))
    mr = GiteaForge("o/r", runner).get_merge_request("adore/run-45")
    assert mr is not None and mr.iid == 8
    endpoint = runner.calls[0][-1]
    assert endpoint.startswith("repos/o/r/pulls?")
    assert "state=open" in endpoint
    runner = FakeRunner(_api_ok("[]"))
    assert GiteaForge("o/r", runner).get_merge_request("gone-branch") is None


def test_gitea_open_pr_wip_prefix_and_reviewers_best_effort() -> None:
    """
    @brief   Draft PRs get the `WIP: ` title prefix (never duplicated), the
             URL comes from the response JSON, and the reviewer request is a
             SEPARATE best-effort call whose failure must not lose the
             already-created PR.
    """
    created = '{"number": 30, "html_url": "http://g/o/r/pulls/30"}'
    runner = FakeRunner(_api_ok(created), _api_ok("{}"))
    url = GiteaForge("o/r", runner, login="home").open_merge_request(
        "adore/run-45", "master", "Resolve #45: fix", "body",
        reviewers=["dpasare"], cwd="/tmp/worktree",
    )
    assert url == "http://g/o/r/pulls/30"
    create_argv, reviewer_argv = runner.calls
    assert create_argv[-1] == "repos/o/r/pulls"
    assert "title=WIP: Resolve #45: fix" in create_argv
    assert "head=adore/run-45" in create_argv and "base=master" in create_argv
    assert "merge" not in create_argv  # the adapter can never merge
    assert runner.cwds == [None, None]  # pure API: no local checkout needed
    assert reviewer_argv[-1] == "repos/o/r/pulls/30/requested_reviewers"
    assert "--data" in reviewer_argv
    assert '{"reviewers": ["dpasare"]}' in reviewer_argv
    # reviewer rejection (e.g. no repo access) keeps the PR: URL still returned
    runner = FakeRunner(_api_ok(created), _api_ok('{"message": "no access"}', 422))
    url = GiteaForge("o/r", runner).open_merge_request(
        "s", "master", "Resolve #45: fix", "b", reviewers=["ghost"]
    )
    assert url == "http://g/o/r/pulls/30"


def test_gitea_open_pr_title_prefix_edges_and_missing_url() -> None:
    """
    @brief   An already-WIP title is not double-prefixed, a non-draft PR gets
             no prefix, and a created PR without html_url fails closed.
    """
    created = '{"number": 31, "html_url": "http://g/o/r/pulls/31"}'
    runner = FakeRunner(_api_ok(created))
    GiteaForge("o/r", runner).open_merge_request("s", "m", "WIP: already", "b")
    assert "title=WIP: already" in runner.calls[0]
    runner = FakeRunner(_api_ok(created))
    GiteaForge("o/r", runner).open_merge_request("s", "m", "plain", "b", draft=False)
    assert "title=plain" in runner.calls[0]
    with pytest.raises(ForgeError):
        GiteaForge("o/r", FakeRunner(_api_ok('{"number": 32}'))).open_merge_request(
            "s", "m", "t", "b"
        )


def test_gitlab_post_and_edit_mr_incident_comment() -> None:
    """@brief GitLab MR incidents use merge-request notes, not ticket notes."""
    runner = FakeRunner(_ok('{"id": 765}'), _ok("{}"))
    forge = GitLabForge("group/project", runner)
    assert forge.post_mr_comment(29, "problem") == 765
    forge.edit_mr_comment(29, 765, "updated")
    assert "merge_requests/29/notes" in " ".join(runner.calls[0])
    assert "merge_requests/29/notes/765" in " ".join(runner.calls[1])


@pytest.mark.parametrize("kind", ["github", "gitea"])
def test_issue_style_forges_route_pr_comments_through_issue_surface(kind: str) -> None:
    """@brief GitHub/Gitea PR conversation comments reuse validated issue APIs."""
    if kind == "github":
        runner = FakeRunner(
            _ok("https://github.com/o/r/issues/9#issuecomment-777\n"), _ok("{}")
        )
        forge = GitHubForge("o/r", runner)
    else:
        runner = FakeRunner(_api_ok('{"id":777}', status=201), _api_ok("{}"))
        forge = GiteaForge("o/r", runner)
    assert forge.post_mr_comment(9, "problem") == 777
    forge.edit_mr_comment(9, 777, "updated")
    assert len(runner.calls) == 2


# PUBLIC API / TESTS - branch lookup misses (the adoption probe)


def test_github_branch_without_pr_is_absence_not_failure() -> None:
    """
    @brief   gh's BRANCH miss wording differs from its 404/number wording.
             `_publish` probes by branch before creating the draft, so a miss
             must read as "no PR yet"; raising there failed every run after
             the push and after human approval.
    """
    runner = FakeRunner(_fail('no pull requests found for branch "adore/o-r-14"'))
    assert GitHubForge("o/r", runner).get_merge_request("adore/o-r-14") is None


def test_gitlab_branch_without_mr_is_absence_not_failure() -> None:
    """
    @brief   Same adoption probe on glab, whose branch miss reads "no open
             merge request available for" and matched no inherited marker.
    """
    runner = FakeRunner(_fail('no open merge request available for "adore/g-p-14"'))
    assert GitLabForge("g/p", runner).get_merge_request("adore/g-p-14") is None


def test_branch_lookup_still_raises_on_a_real_failure() -> None:
    """
    @brief   Widening the markers must not swallow genuine errors: an auth or
             transport failure still raises instead of reporting absence,
             which would make ADORE open a duplicate MR.
    """
    runner = FakeRunner(_fail("error connecting to gitlab.example: timeout"))
    with pytest.raises(ForgeError):
        GitLabForge("g/p", runner).get_merge_request("adore/g-p-14")


# PUBLIC API / TESTS - comment pagination


def test_github_list_comments_walks_every_page() -> None:
    """
    @brief   One gh api call returns the OLDEST 100 comments. Without a page
             walk a parked run never sees the newer human answer and dies on
             the clarification timeout, so the adapter must page to the end.
    """
    first = "[" + ",".join(
        f'{{"id":{index},"body":"b","user":{{"login":"u"}},"created_at":"t"}}'
        for index in range(1, 101)
    ) + "]"
    second = '[{"id":137,"body":"answer","user":{"login":"human"},"created_at":"t"}]'
    runner = FakeRunner(_ok(first), _ok(second))
    comments = GitHubForge("o/r", runner).list_comments(14)
    assert len(comments) == 101
    assert comments[-1].id == 137  # the answer the resume check filters on
    assert "page=1" in runner.calls[0][-1]
    assert "page=2" in runner.calls[1][-1]


def test_gitlab_list_notes_walk_every_page_on_both_surfaces() -> None:
    """
    @brief   GitLab reaches the 100-note cap fastest, because every ADORE
             label change adds a system note. Issue and MR surfaces both page.
    """
    first = "[" + ",".join(
        f'{{"id":{index},"body":"b","author":{{"username":"u"}},"system":true}}'
        for index in range(1, 101)
    ) + "]"
    second = '[{"id":137,"body":"answer","author":{"username":"human"}}]'
    runner = FakeRunner(_ok(first), _ok(second), _ok(first), _ok(second))
    forge = GitLabForge("g/p", runner)
    assert [item.id for item in forge.list_comments(14)][-1] == 137
    assert [item.id for item in forge.list_mr_comments(7)][-1] == 137
    assert "page=2" in runner.calls[1][-1]
    assert "merge_requests/7/notes" in runner.calls[2][-1]


# PUBLIC API / TESTS - pipeline verdicts


def test_gitlab_pipeline_status_maps_head_pipeline() -> None:
    """
    @brief   GitLab carries the verdict inline on the MR document, so one call
             answers. Cancelled is not a failure, and an older GitLab that
             omits the key reads as unknown rather than as a pass.
    """
    forge = GitLabForge("g/p", FakeRunner(_ok('{"head_pipeline":{"status":"failed"}}')))
    assert forge.pipeline_status(9) == "failed"
    forge = GitLabForge("g/p", FakeRunner(_ok('{"head_pipeline":{"status":"running"}}')))
    assert forge.pipeline_status(9) == "running"
    forge = GitLabForge("g/p", FakeRunner(_ok('{"head_pipeline":{"status":"canceled"}}')))
    assert forge.pipeline_status(9) == "none"
    forge = GitLabForge("g/p", FakeRunner(_ok('{"head_pipeline":null}')))
    assert forge.pipeline_status(9) == "none"
    forge = GitLabForge("g/p", FakeRunner(_ok('{"iid":9}')))
    assert forge.pipeline_status(9) == "unknown"


def test_github_pipeline_status_rolls_up_checks_and_statuses() -> None:
    """
    @brief   statusCheckRollup mixes Actions check runs (status + conclusion)
             with external commit statuses (state). The worst verdict wins, an
             unfinished check outranks the greens already in, and NEUTRAL or
             SKIPPED is not a failure.
    """
    red = (
        '{"statusCheckRollup":['
        '{"__typename":"CheckRun","status":"COMPLETED","conclusion":"SUCCESS"},'
        '{"__typename":"CheckRun","status":"COMPLETED","conclusion":"FAILURE"}]}'
    )
    assert GitHubForge("o/r", FakeRunner(_ok(red))).pipeline_status(9) == "failed"

    busy = (
        '{"statusCheckRollup":['
        '{"__typename":"CheckRun","status":"COMPLETED","conclusion":"SUCCESS"},'
        '{"__typename":"CheckRun","status":"IN_PROGRESS","conclusion":""}]}'
    )
    assert GitHubForge("o/r", FakeRunner(_ok(busy))).pipeline_status(9) == "running"

    external = '{"statusCheckRollup":[{"__typename":"StatusContext","state":"SUCCESS"}]}'
    assert GitHubForge("o/r", FakeRunner(_ok(external))).pipeline_status(9) == "success"

    neutral = (
        '{"statusCheckRollup":['
        '{"__typename":"CheckRun","status":"COMPLETED","conclusion":"SKIPPED"}]}'
    )
    assert GitHubForge("o/r", FakeRunner(_ok(neutral))).pipeline_status(9) == "none"
    assert GitHubForge("o/r", FakeRunner(_ok('{"statusCheckRollup":[]}'))
                       ).pipeline_status(9) == "none"


def test_pipeline_status_never_raises_on_a_forge_failure() -> None:
    """
    @brief   The post-MR poll watches a run doing no code work, so an
             unreadable pipeline must degrade to "unknown" - which is silent -
             rather than raising into the poll. A gh too old to know the field
             is exactly this case.
    """
    old_gh = FakeRunner(_fail("unknown JSON field: statusCheckRollup"))
    assert GitHubForge("o/r", old_gh).pipeline_status(9) == "unknown"
    assert GitLabForge("g/p", FakeRunner(_fail("timeout"))).pipeline_status(9) == "unknown"
    assert GiteaForge("o/r", FakeRunner(_api_ok("", status=500))).pipeline_status(9) == "unknown"


def test_gitea_pipeline_status_reads_the_head_commit_status() -> None:
    """
    @brief   Gitea keys status by commit, so the pull is read for head.sha and
             then its combined status. An empty state means no CI reported.
    """
    pull = '{"number":9,"head":{"sha":"abc123"}}'
    failed = '{"state":"failure","statuses":[{"status":"failure"}],"total_count":1}'
    runner = FakeRunner(_api_ok(pull), _api_ok(failed))
    forge = GiteaForge("o/r", runner)
    assert forge.pipeline_status(9) == "failed"
    assert "commits/abc123/status" in runner.calls[1][-1]

    runner = FakeRunner(_api_ok(pull), _api_ok('{"state":"","total_count":0}'))
    assert GiteaForge("o/r", runner).pipeline_status(9) == "none"


def test_gitea_no_ci_at_all_is_none_not_running() -> None:
    """
    @brief   Gitea answers `state: "pending"` with an EMPTY status list when
             nothing has reported on the commit, so a repository with no CI
             would otherwise read as a pipeline forever in progress (live
             finding against Gitea 1.27.2). The count decides first.
    """
    pull = '{"number":9,"head":{"sha":"abc123"}}'
    empty = '{"state":"pending","statuses":null,"total_count":0}'
    runner = FakeRunner(_api_ok(pull), _api_ok(empty))
    assert GiteaForge("o/r", runner).pipeline_status(9) == "none"

    # a genuine queued pipeline still reads as running
    queued = '{"state":"pending","statuses":[{"status":"pending"}],"total_count":1}'
    runner = FakeRunner(_api_ok(pull), _api_ok(queued))
    assert GiteaForge("o/r", runner).pipeline_status(9) == "running"


# PUBLIC API / TESTS - the PR review surfaces the revise loop feeds on


def test_github_mr_comments_include_review_bodies_and_inline_comments() -> None:
    """
    @brief   A reviewer using "Files changed" then "Review changes" writes to
             pulls/<n>/reviews and pulls/<n>/comments, not the conversation.
             Reading only the conversation handed the revision executor an
             empty thread. Bodyless reviews are bare approve events and are
             dropped; everything else merges onto one timeline, oldest first.
    """
    conversation = (
        '[{"id":1,"body":"conversation","user":{"login":"a"},'
        '"created_at":"2026-01-01T00:00:00Z"}]'
    )
    reviews = (
        '[{"id":50,"body":"please rename the helper","user":{"login":"rev"},'
        '"submitted_at":"2026-01-02T00:00:00Z"},'
        '{"id":51,"body":"","user":{"login":"rev"},'
        '"submitted_at":"2026-01-02T12:00:00Z"}]'
    )
    inline = (
        '[{"id":60,"body":"this line is wrong","user":{"login":"rev"},'
        '"created_at":"2026-01-03T00:00:00Z"}]'
    )
    runner = FakeRunner(_ok(conversation), _ok(reviews), _ok(inline))
    comments = GitHubForge("o/r", runner).list_mr_comments(9)
    assert [item.body for item in comments] == [
        "conversation", "please rename the helper", "this line is wrong",
    ]


def test_gitea_mr_comments_include_review_bodies_and_inline_comments() -> None:
    """
    @brief   Gitea splits the same way: review text and inline diff comments
             live behind pulls/<n>/reviews, one extra call per review.
    """
    conversation = (
        '[{"id":1,"body":"conversation","user":{"login":"a"},'
        '"created_at":"2026-01-01T00:00:00Z"}]'
    )
    reviews = (
        '[{"id":50,"body":"please rename the helper","user":{"login":"rev"},'
        '"submitted_at":"2026-01-02T00:00:00Z"}]'
    )
    inline = (
        '[{"id":60,"body":"this line is wrong","user":{"login":"rev"},'
        '"created_at":"2026-01-03T00:00:00Z"}]'
    )
    runner = FakeRunner(
        _api_ok(conversation), _api_ok(reviews), _api_ok(inline),
    )
    comments = GiteaForge("o/r", runner).list_mr_comments(9)
    assert [item.body for item in comments] == [
        "conversation", "please rename the helper", "this line is wrong",
    ]
    assert comments[1].author == "rev"


# END OF FILE
