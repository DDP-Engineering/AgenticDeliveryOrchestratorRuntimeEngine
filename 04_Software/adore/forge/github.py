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
@file github.py
@brief GitHub adapter implemented over the `gh` CLI.
@details Mirrors the GitLab adapter using `gh issue list --json`,
         `gh issue comment`, `gh api` for comment reads/edits, and
         `gh pr create --draft`. The command runner is injected so the
         adapter is unit-testable without gh. `_run` and `_parse_json` moved
         to the shared `Forge` base (ADORE-PY-004); `_NOT_FOUND_MARKERS`
         stays a class-attribute override here since gh's "could not
         resolve" text is not shared by glab/tea.
"""

from __future__ import annotations

# IMPORTS
import re
from typing import Any

from adore.forge.base import Comment, Forge, ForgeError, MergeRequest, Ticket
from adore.util import CommandRunner, run_command

# CONSTANTS

_ISSUE_JSON_FIELDS = "number,title,body,labels,author,state,url,createdAt,updatedAt"
_COMMENT_ID_RE = re.compile(r"#issuecomment-(\d+)")
_PR_URL_RE = re.compile(r"https?://\S+/pull/\d+")
# GitHub caps a REST page at 100 and `gh api` fetches exactly one page, so a
# list endpoint must be walked or it silently returns only the OLDEST 100
# items; bounded so a runaway never loops.
_PAGE_SIZE = 100
_MAX_LIST_PAGES = 50

# PUBLIC API


class GitHubForge(Forge):
    """
    @brief   GitHub implementation of the Forge interface (via `gh`).
    """

    #: gh additionally reports an unresolvable --repo as "could not resolve
    #: to a Repository", which glab/tea never print - kept as an override
    #: rather than widening the shared default (ADORE-PY-004).
    #: "no pull requests found" is gh's BRANCH lookup miss (cli/cli
    #: pkg/cmd/pr/shared/finder.go). It shares no wording with the 404/number
    #: forms, and without it the very first `get_merge_request(branch)` of
    #: every run - the adoption probe `_publish` runs before creating the
    #: draft - raises instead of reporting "no MR yet", failing the run after
    #: the push and after human approval.
    _NOT_FOUND_MARKERS = (
        "404", "not found", "could not resolve", "no pull requests found",
    )

    def __init__(self, repo: str, runner: CommandRunner = run_command) -> None:
        """
        @brief      Bind the adapter to a GitHub repository.
        @param[in]  repo GitHub repository (OWNER/REPO).
        @param[in]  runner Command runner (injectable for tests).
        """
        self.repo = repo
        self.runner = runner

    # -- selection ----------------------------------------------------------------

    def list_ready(self, ready_label: str) -> list[Ticket]:
        """
        @brief      List open issues carrying the label via `gh issue list`.
        @details    `--limit 500` (gh paginates internally up to the limit) so a
                    busy repository does not silently truncate the selection
                    pool at 100 and drop a high-priority ticket the caller would
                    have ranked first.
        @param[in]  ready_label Eligibility label.
        @return     Eligible tickets, unordered (caller ranks by priority).
        @exception  ForgeError When gh fails.
        """
        result = self._run(
            [
                "gh", "issue", "list",
                "--repo", self.repo,
                "--label", ready_label,
                "--state", "open",
                "--json", _ISSUE_JSON_FIELDS,
                "--limit", "500",
            ]
        )
        return [self._to_ticket(item) for item in self._parse_json(result, list)]

    def list_open(self, limit: int) -> list[Ticket]:
        """
        @brief      List open issues without a label filter via `gh issue list`.
        @param[in]  limit Maximum number of tickets (gh paginates up to it).
        @return     Open tickets, at most `limit`.
        @exception  ForgeError When gh fails or a record is malformed.
        """
        result = self._run(
            [
                "gh", "issue", "list",
                "--repo", self.repo,
                "--state", "open",
                "--json", _ISSUE_JSON_FIELDS,
                "--limit", str(limit),
            ]
        )
        return self._open_tickets(self._parse_json(result, list), limit)

    def get_ticket(self, iid: int) -> Ticket | None:
        """
        @brief      Fetch one issue; None when it was deleted.
        @param[in]  iid Issue number.
        @return     The ticket or None on 404.
        @exception  ForgeError When gh fails for another reason.
        """
        result = self.runner(
            [
                "gh", "issue", "view", str(iid),
                "--repo", self.repo,
                "--json", _ISSUE_JSON_FIELDS,
            ]
        )
        if not result.ok:
            if self._is_not_found(result):
                return None
            raise ForgeError("gh issue view failed", result.argv, result.stderr)
        return self._to_ticket(self._parse_json(result, dict))

    # -- comments -----------------------------------------------------------------

    def list_comments(self, iid: int) -> list[Comment]:
        """
        @brief      Read all issue comments oldest-first via the REST API.
        @details    Paginated through `_paged`: a single page is the OLDEST
                    100 comments, so on a busier ticket the newest ones -
                    including the human answer a parked run is waiting for -
                    would never be read, and the run would die on the
                    clarification timeout instead of resuming.
        @param[in]  iid Issue number.
        @return     All comments (GitHub keeps system events separate, so
                    system is always False here).
        @exception  ForgeError When gh fails.
        """
        return [
            self._to_comment(item)
            for item in self._paged(f"repos/{self.repo}/issues/{iid}/comments")
        ]

    def post_comment(self, iid: int, body: str) -> int:
        """
        @brief      Create a comment via `gh issue comment`.
        @details    The id is parsed from the "#issuecomment-<id>" URL gh
                    prints; falls back to matching the newest comment body.
        @param[in]  iid Issue number.
        @param[in]  body Comment body.
        @return     Created comment id.
        @exception  ForgeError When gh fails or the id cannot be found.
        """
        result = self._run(
            ["gh", "issue", "comment", str(iid), "--repo", self.repo, "--body", body]
        )
        match = _COMMENT_ID_RE.search(result.stdout)
        if match:
            return int(match.group(1))
        for comment in reversed(self.list_comments(iid)):
            if comment.body.strip() == body.strip():
                return comment.id
        raise ForgeError("could not determine created comment id", result.argv, result.stderr)

    def edit_comment(self, iid: int, comment_id: int, body: str) -> None:
        """
        @brief      Edit a comment in place via the REST API (PATCH).
        @details    The body goes through --raw-field: in gh api, --field
                    infers types (true/false/numbers), --raw-field is
                    guaranteed string - same finding as the glab adapter.
        @param[in]  iid Issue number (unused; GitHub comment ids are global).
        @param[in]  comment_id Comment id.
        @param[in]  body Replacement body.
        @exception  ForgeError When gh fails.
        """
        del iid  # comment ids are repo-global on GitHub
        self._run(
            [
                "gh", "api", "--method", "PATCH",
                f"repos/{self.repo}/issues/comments/{comment_id}",
                "--raw-field", f"body={body}",
            ]
        )

    # -- labels -------------------------------------------------------------------

    def add_labels(self, iid: int, labels: list[str]) -> None:
        """
        @brief      Add labels via `gh issue edit --add-label`.
        @param[in]  iid Issue number.
        @param[in]  labels Labels to add.
        @exception  ForgeError When gh fails.
        """
        if not labels:
            return
        self._run(
            [
                "gh", "issue", "edit", str(iid),
                "--repo", self.repo,
                "--add-label", ",".join(labels),
            ]
        )

    def remove_labels(self, iid: int, labels: list[str]) -> None:
        """
        @brief      Remove labels via `gh issue edit --remove-label`.
        @param[in]  iid Issue number.
        @param[in]  labels Labels to remove.
        @exception  ForgeError When gh fails.
        """
        if not labels:
            return
        self._run(
            [
                "gh", "issue", "edit", str(iid),
                "--repo", self.repo,
                "--remove-label", ",".join(labels),
            ]
        )

    # -- delivery -----------------------------------------------------------------

    def get_merge_request(self, ref: int | str) -> MergeRequest | None:
        """
        @brief      Fetch one PR by number or head branch via `gh pr view`.
        @details    `labels` MUST stay in the requested `--json` field set: gh
                    returns only the fields named here, so omitting it makes
                    `data["labels"]` absent and every MR read back with an empty
                    label list - which silently disables the revise-label
                    trigger in the orchestrator's post-MR poll.
        @param[in]  ref PR number, or the head branch name (open PRs only).
        @return     The MergeRequest (state normalized), or None.
        @exception  ForgeError When gh fails for another reason.
        """
        result = self.runner(
            ["gh", "pr", "view", str(ref), "--repo", self.repo,
             "--json", "number,state,url,isDraft,labels"]
        )
        if not result.ok:
            if self._is_not_found(result):
                return None
            raise ForgeError("gh pr view failed", result.argv, result.stderr)
        data = self._parse_json(result, dict)
        state = str(data.get("state", "OPEN")).lower()
        return MergeRequest(
            iid=int(data["number"]),
            state="opened" if state == "open" else state,
            web_url=data.get("url", ""),
            draft=bool(data.get("isDraft", False)),
            labels=[label["name"] for label in data.get("labels") or []],
        )

    def pipeline_status(self, mr_iid: int) -> str:
        """
        @brief      The PR's combined check verdict, normalized; never raises.
        @details    `statusCheckRollup` merges both surfaces GitHub exposes:
                    Actions check runs, which report `status` plus
                    `conclusion`, and commit statuses from external CI, which
                    report only `state`. It is requested in its OWN `gh pr
                    view` call rather than being added to the field set
                    `get_merge_request` asks for, so a gh version that does not
                    know the field cannot break the MR read that the whole
                    post-MR poll depends on.
        @param[in]  mr_iid PR number.
        @return     A PIPELINE_STATES value.
        """
        result = self.runner(
            ["gh", "pr", "view", str(mr_iid), "--repo", self.repo,
             "--json", "statusCheckRollup"]
        )
        if not result.ok:
            return "unknown"
        try:
            data = self._parse_json(result, dict)
        except ForgeError:
            return "unknown"
        rollup = data.get("statusCheckRollup")
        if not isinstance(rollup, list):
            return "unknown"
        states = {
            self._check_state(item) for item in rollup if isinstance(item, dict)
        }
        # Worst verdict wins: one red check makes the whole rollup red, and a
        # check still running outranks the greens that already landed.
        for verdict in ("failed", "running", "success"):
            if verdict in states:
                return verdict
        return "none"

    @staticmethod
    def _check_state(item: dict[str, Any]) -> str:
        """
        @brief      Normalize one statusCheckRollup entry.
        @details    A CheckRun is only meaningful once `status` is COMPLETED;
                    until then its `conclusion` is empty and it counts as
                    running. A StatusContext has no `status` field at all, so
                    it falls through to `state`. NEUTRAL, SKIPPED and CANCELLED
                    are not failures.
        @param[in]  item One rollup entry.
        @return     A PIPELINE_STATES value other than "unknown".
        """
        status = str(item.get("status") or "").upper()
        if status and status != "COMPLETED":
            return "running"
        verdict = str(item.get("conclusion") or item.get("state") or "").upper()
        if verdict in {"FAILURE", "ERROR", "TIMED_OUT", "STARTUP_FAILURE",
                       "ACTION_REQUIRED"}:
            return "failed"
        if verdict == "SUCCESS":
            return "success"
        if verdict in {"PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "EXPECTED"}:
            return "running"
        return "none"

    def list_mr_comments(self, mr_iid: int) -> list[Comment]:
        """
        @brief      Read the whole PR review thread oldest-first (REST API).
        @details    A GitHub PR carries THREE comment surfaces and the revise
                    loop needs all of them. PRs are issues, so the issues
                    endpoint covers the conversation tab; a submitted review's
                    own text lives under `pulls/<n>/reviews`; inline diff
                    comments live under `pulls/<n>/comments`. Reading only the
                    conversation handed the revision executor an EMPTY thread
                    whenever a reviewer used "Files changed" then "Review
                    changes", which is the normal way to request changes, so
                    the round was spent revising blind.
        @param[in]  mr_iid PR number.
        @return     Conversation, review-body and inline comments, oldest first.
        @exception  ForgeError When gh fails.
        """
        comments = self.list_comments(mr_iid)
        comments.extend(self._review_comments(mr_iid))
        comments.sort(key=lambda item: (item.created_at, item.id))
        return comments

    def _review_comments(self, mr_iid: int) -> list[Comment]:
        """
        @brief      Submitted review bodies plus inline diff comments.
        @details    A review with an empty body is a bare approve/close event
                    that carries no instruction, so it is dropped rather than
                    padding the thread the executor reads.
        @param[in]  mr_iid PR number.
        @return     Review-surface comments (empty when the PR has none).
        @exception  ForgeError When gh fails.
        """
        found: list[Comment] = []
        for surface in ("reviews", "comments"):
            for item in self._paged(f"repos/{self.repo}/pulls/{mr_iid}/{surface}"):
                if not str(item.get("body") or "").strip():
                    continue
                found.append(self._to_comment(item))
        return found

    def post_mr_comment(self, mr_iid: int, body: str) -> int:
        """@brief Post a PR conversation comment through the issues surface."""
        return self.post_comment(mr_iid, body)

    def edit_mr_comment(self, mr_iid: int, comment_id: int, body: str) -> None:
        """@brief Edit a PR conversation comment through the issues surface."""
        self.edit_comment(mr_iid, comment_id, body)

    def remove_mr_labels(self, mr_iid: int, labels: list[str]) -> None:
        """
        @brief      Remove PR labels via `gh pr edit --remove-label`.
        @param[in]  mr_iid PR number.
        @param[in]  labels Labels to remove.
        @exception  ForgeError When gh fails.
        """
        if not labels:
            return
        self._run(
            ["gh", "pr", "edit", str(mr_iid), "--repo", self.repo,
             "--remove-label", ",".join(labels)]
        )

    def open_merge_request(
        self,
        source: str,
        target: str,
        title: str,
        body: str,
        *,
        draft: bool = True,
        reviewers: list[str] | None = None,
        remove_source_branch: bool = True,
        cwd: str | None = None,
    ) -> str:
        """
        @brief      Open a draft or ready PR via `gh pr create`. Never merges.
        @param[in]  source Head branch.
        @param[in]  target Base branch.
        @param[in]  title PR title.
        @param[in]  body PR description.
        @param[in]  draft Open as draft when true, otherwise ready for review.
        @param[in]  reviewers Reviewer logins.
        @param[in]  remove_source_branch Conductor cleans up after human merge.
        @param[in]  cwd Git checkout to run in; gh resolves remotes from a
                        local repo even with --repo, so the run's worktree is
                        passed (see the Forge base contract).
        @return     PR web URL.
        @exception  ForgeError When gh fails or no URL is printed.
        """
        del remove_source_branch  # The conductor owns leased post-merge cleanup.
        argv = [
            "gh", "pr", "create",
            "--repo", self.repo,
            "--head", source,
            "--base", target,
            "--title", title,
            "--body", body,
        ]
        if draft:
            argv.append("--draft")
        for reviewer in reviewers or []:
            argv += ["--reviewer", reviewer]
        result = self._run(argv, cwd=cwd)
        match = _PR_URL_RE.search(result.stdout)
        if not match:
            raise ForgeError("gh pr create printed no PR URL", result.argv, result.stdout)
        return match.group(0)

    # -- internals ------------------------------------------------------------------

    def list_labels(self) -> list[str]:
        """@brief Repository label names, read page by page."""
        return [str(item["name"]) for item in self._paged(f"repos/{self.repo}/labels")
                if isinstance(item, dict) and item.get("name")]

    def create_label(self, name: str, color: str, description: str) -> None:
        """@brief Create a repository label (GitHub takes the colour without #)."""
        self._run(["gh", "api", "--method", "POST", f"repos/{self.repo}/labels",
                   "-f", f"name={name}", "-f", f"color={color}",
                   "-f", f"description={description}"])

    def _paged(self, path: str) -> list[dict[str, Any]]:
        """
        @brief      GET every page of a REST list endpoint.
        @details    `gh api` fetches ONE page and GitHub caps a page at 100,
                    so an unwalked call returns the oldest 100 items and hides
                    the rest with no error. Pages are walked until a short
                    (last) page; `_MAX_LIST_PAGES` bounds a runaway.
        @param[in]  path Endpoint path, without a query string.
        @return     The concatenated item list.
        @exception  ForgeError When gh fails or a page is malformed.
        """
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            result = self._run(
                ["gh", "api", f"{path}?per_page={_PAGE_SIZE}&page={page}"]
            )
            batch = self._parse_json(result, list)
            items.extend(batch)
            if len(batch) < _PAGE_SIZE or page >= _MAX_LIST_PAGES:
                return items
            page += 1

    @staticmethod
    def _to_comment(item: dict[str, Any]) -> Comment:
        """
        @brief      Map one gh comment, review, or inline-comment record.
        @details    A submitted review timestamps itself with `submitted_at`
                    rather than `created_at`; falling back keeps every surface
                    on one sortable timeline instead of pinning reviews to the
                    start of the thread.
        @param[in]  item Raw comment/review mapping.
        @return     The normalized Comment (GitHub keeps system events on a
                    separate timeline, so `system` is always False).
        """
        return Comment(
            id=int(item["id"]),
            body=item.get("body", ""),
            author=(item.get("user") or {}).get("login", ""),
            created_at=item.get("created_at") or item.get("submitted_at", ""),
            system=False,
        )

    @staticmethod
    def _to_ticket(item: dict[str, Any]) -> Ticket:
        """
        @brief      Map one gh issue JSON record to a Ticket.
        @details    gh returns labels as objects with a name field and states
                    as OPEN/CLOSED; both are normalized to the GitLab shape.
        @param[in]  item Raw issue mapping.
        @return     The normalized Ticket.
        """
        state = str(item.get("state", "OPEN")).lower()
        return Ticket(
            iid=int(item["number"]),
            title=item.get("title", ""),
            description=item.get("body") or "",
            labels=[label["name"] for label in item.get("labels") or []],
            author=(item.get("author") or {}).get("login", ""),
            state="opened" if state == "open" else state,
            web_url=item.get("url", ""),
            created_at=item.get("createdAt", ""),
            updated_at=item.get("updatedAt", ""),
        )


# END OF FILE
