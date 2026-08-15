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

# PUBLIC API


class GitHubForge(Forge):
    """
    @brief   GitHub implementation of the Forge interface (via `gh`).
    """

    #: gh additionally reports an unresolvable --repo as "could not resolve
    #: to a Repository", which glab/tea never print - kept as an override
    #: rather than widening the shared default (ADORE-PY-004).
    _NOT_FOUND_MARKERS = ("404", "not found", "could not resolve")

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
        @param[in]  iid Issue number.
        @return     All comments (GitHub keeps system events separate, so
                    system is always False here).
        @exception  ForgeError When gh fails.
        """
        result = self._run(
            ["gh", "api", f"repos/{self.repo}/issues/{iid}/comments?per_page=100"]
        )
        return [
            Comment(
                id=int(item["id"]),
                body=item.get("body", ""),
                author=(item.get("user") or {}).get("login", ""),
                created_at=item.get("created_at", ""),
                system=False,
            )
            for item in self._parse_json(result, list)
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

    def list_mr_comments(self, mr_iid: int) -> list[Comment]:
        """
        @brief      Read PR conversation comments oldest-first (REST API).
        @details    PRs are issues on GitHub, so the issues comments endpoint
                    covers the conversation; inline review-thread comments
                    are a later refinement.
        @param[in]  mr_iid PR number.
        @return     All conversation comments.
        @exception  ForgeError When gh fails.
        """
        return self.list_comments(mr_iid)

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
        @brief      Open a draft PR via `gh pr create --draft`. Never merges.
        @param[in]  source Head branch.
        @param[in]  target Base branch.
        @param[in]  title PR title.
        @param[in]  body PR description.
        @param[in]  draft Open as draft (ADORE always passes true).
        @param[in]  reviewers Reviewer logins.
        @param[in]  remove_source_branch Ignored (a repo setting on GitHub).
        @return     PR web URL.
        @exception  ForgeError When gh fails or no URL is printed.
        """
        del remove_source_branch  # branch deletion is a repo setting on GitHub
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
