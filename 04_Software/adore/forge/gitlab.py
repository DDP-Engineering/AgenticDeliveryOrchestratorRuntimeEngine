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
@file gitlab.py
@brief GitLab adapter implemented over the `glab` CLI.
@details Uses `glab issue list --output json` for selection, `glab issue note`
         to create comments, and `glab api` for everything glab has no
         subcommand for: reading notes and editing a note in place (PUT), per
         the Prerequisites_Check_Report findings. The command runner is
         injected so the adapter is unit-testable without glab.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.1.0
"""

from __future__ import annotations

# IMPORTS
import json
import re
from typing import Any
import urllib.parse

from adore.forge.base import Comment, Forge, ForgeError, MergeRequest, Ticket
from adore.util import CommandResult, CommandRunner, run_command

# CONSTANTS

_NOTE_ID_RE = re.compile(r"#note_(\d+)")
_MR_URL_RE = re.compile(r"https?://\S+/-/merge_requests/\d+")
_NOT_FOUND_MARKERS = ("404", "not found")
# GitLab caps `--per-page` at 100, so paginate to see every ready ticket rather
# than silently truncating the selection pool; bounded so a runaway never loops.
_PAGE_SIZE = 100
_MAX_LIST_PAGES = 50

# PUBLIC API


class GitLabForge(Forge):
    """
    @brief   GitLab implementation of the Forge interface (via `glab`).
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    def __init__(self, repo: str, runner: CommandRunner = run_command) -> None:
        """
        @brief      Bind the adapter to a GitLab project path.
        @param[in]  repo GitLab project path (GROUP/.../PROJECT).
        @param[in]  runner Command runner (injectable for tests).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        self.repo = repo
        self.runner = runner

    # -- selection ----------------------------------------------------------------

    def list_ready(self, ready_label: str) -> list[Ticket]:
        """
        @brief      List open issues carrying the label, via JSON output.
        @details    Paginated: GitLab caps `--per-page` at 100, so a repository
                    with more than 100 ready tickets would otherwise drop the
                    overflow from the selection pool - including a high-priority
                    ticket the caller would have ranked first. Pages are walked
                    until a short (last) page, bounded by `_MAX_LIST_PAGES`.
        @param[in]  ready_label Eligibility label.
        @return     Eligible tickets, unordered (caller ranks by priority).
        @exception  ForgeError When glab fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-24
        @version    0.1.1
        """
        tickets: list[Ticket] = []
        page = 1
        while True:
            result = self._run(
                [
                    "glab", "issue", "list",
                    "--repo", self.repo,
                    "--label", ready_label,
                    "--output", "json",
                    "--per-page", str(_PAGE_SIZE),
                    "--page", str(page),
                ]
            )
            batch = self._parse_json(result, list)
            tickets.extend(self._to_ticket(item) for item in batch)
            if len(batch) < _PAGE_SIZE or page >= _MAX_LIST_PAGES:
                return tickets
            page += 1

    def get_ticket(self, iid: int) -> Ticket | None:
        """
        @brief      Fetch one issue; None when it was deleted.
        @param[in]  iid Issue iid.
        @return     The ticket or None on 404.
        @exception  ForgeError When glab fails for another reason.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        result = self.runner(
            ["glab", "issue", "view", str(iid), "--repo", self.repo, "--output", "json"]
        )
        if not result.ok:
            if self._is_not_found(result):
                return None
            raise ForgeError("glab issue view failed", result.argv, result.stderr)
        return self._to_ticket(self._parse_json(result, dict))

    # -- comments -----------------------------------------------------------------

    def list_comments(self, iid: int) -> list[Comment]:
        """
        @brief      Read all notes oldest-first via the notes API.
        @param[in]  iid Issue iid.
        @return     All notes, system notes flagged.
        @exception  ForgeError When glab fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        endpoint = (
            f"projects/{self._project_enc}/issues/{iid}/notes"
            "?order_by=created_at&sort=asc&per_page=100"
        )
        result = self._run(["glab", "api", endpoint])
        return [
            Comment(
                id=int(note["id"]),
                body=note.get("body", ""),
                author=(note.get("author") or {}).get("username", ""),
                created_at=note.get("created_at", ""),
                system=bool(note.get("system", False)),
            )
            for note in self._parse_json(result, list)
        ]

    def post_comment(self, iid: int, body: str) -> int:
        """
        @brief      Create a note via `glab issue note`.
        @details    The note id is parsed from the "#note_<id>" URL glab
                    prints; if the output format changes, falls back to
                    finding the newest note with the same body.
        @param[in]  iid Issue iid.
        @param[in]  body Note body.
        @return     Created note id.
        @exception  ForgeError When glab fails or the id cannot be found.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        result = self._run(
            ["glab", "issue", "note", str(iid), "--repo", self.repo, "--message", body]
        )
        match = _NOTE_ID_RE.search(result.stdout)
        if match:
            return int(match.group(1))
        for comment in reversed(self.list_comments(iid)):
            if comment.body.strip() == body.strip():
                return comment.id
        raise ForgeError("could not determine created note id", result.argv, result.stderr)

    def edit_comment(self, iid: int, comment_id: int, body: str) -> None:
        """
        @brief      Edit a note in place via the API (PUT).
        @details    glab has no note-edit subcommand (prereq report section 4),
                    so this is `glab api --method PUT .../notes/:id`. The body
                    goes through --raw-field: in glab api, --field infers
                    types (true/false/numbers), --raw-field is guaranteed
                    string (verified live against glab 1.105, 2026-07-03).
        @param[in]  iid Issue iid.
        @param[in]  comment_id Note id.
        @param[in]  body Replacement body.
        @exception  ForgeError When glab fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.1
        """
        endpoint = f"projects/{self._project_enc}/issues/{iid}/notes/{comment_id}"
        self._run(["glab", "api", "--method", "PUT", endpoint, "--raw-field", f"body={body}"])

    # -- labels -------------------------------------------------------------------

    def add_labels(self, iid: int, labels: list[str]) -> None:
        """
        @brief      Add labels via `glab issue update --label`.
        @param[in]  iid Issue iid.
        @param[in]  labels Labels to add.
        @exception  ForgeError When glab fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        if not labels:
            return
        argv = ["glab", "issue", "update", str(iid), "--repo", self.repo]
        for label in labels:
            argv += ["--label", label]
        self._run(argv)

    def remove_labels(self, iid: int, labels: list[str]) -> None:
        """
        @brief      Remove labels via `glab issue update --unlabel`.
        @param[in]  iid Issue iid.
        @param[in]  labels Labels to remove.
        @exception  ForgeError When glab fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        if not labels:
            return
        argv = ["glab", "issue", "update", str(iid), "--repo", self.repo]
        for label in labels:
            argv += ["--unlabel", label]
        self._run(argv)

    # -- delivery -----------------------------------------------------------------

    def get_merge_request(self, ref: int | str) -> MergeRequest | None:
        """
        @brief      Fetch one MR by iid or source branch via `glab mr view`.
        @param[in]  ref MR iid, or the source branch name (open MRs only).
        @return     The MergeRequest, or None when not found.
        @exception  ForgeError When glab fails for another reason.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        result = self.runner(
            ["glab", "mr", "view", str(ref), "--repo", self.repo, "--output", "json"]
        )
        if not result.ok:
            if self._is_not_found(result):
                return None
            raise ForgeError("glab mr view failed", result.argv, result.stderr)
        data = self._parse_json(result, dict)
        return MergeRequest(
            iid=int(data["iid"]),
            state=data.get("state", "opened"),
            web_url=data.get("web_url", ""),
            draft=bool(data.get("draft", data.get("work_in_progress", False))),
            labels=list(data.get("labels") or []),
        )

    def list_mr_comments(self, mr_iid: int) -> list[Comment]:
        """
        @brief      Read all MR notes oldest-first via the notes API.
        @param[in]  mr_iid MR iid.
        @return     All notes, system notes flagged.
        @exception  ForgeError When glab fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-04
        @version    0.1.0
        """
        endpoint = (
            f"projects/{self._project_enc}/merge_requests/{mr_iid}/notes"
            "?order_by=created_at&sort=asc&per_page=100"
        )
        result = self._run(["glab", "api", endpoint])
        return [
            Comment(
                id=int(note["id"]),
                body=note.get("body", ""),
                author=(note.get("author") or {}).get("username", ""),
                created_at=note.get("created_at", ""),
                system=bool(note.get("system", False)),
            )
            for note in self._parse_json(result, list)
        ]

    def remove_mr_labels(self, mr_iid: int, labels: list[str]) -> None:
        """
        @brief      Remove MR labels via the API (PUT remove_labels).
        @param[in]  mr_iid MR iid.
        @param[in]  labels Labels to remove.
        @exception  ForgeError When glab fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-04
        @version    0.1.0
        """
        if not labels:
            return
        endpoint = f"projects/{self._project_enc}/merge_requests/{mr_iid}"
        self._run(["glab", "api", "--method", "PUT", endpoint,
                   "--raw-field", f"remove_labels={','.join(labels)}"])

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
        @brief      Open a draft MR via `glab mr create --draft`. Never merges.
        @param[in]  source Source branch.
        @param[in]  target Target branch.
        @param[in]  title MR title.
        @param[in]  body MR description.
        @param[in]  draft Open as draft (ADORE always passes true).
        @param[in]  reviewers Reviewer usernames.
        @param[in]  remove_source_branch Delete the branch on merge.
        @return     MR web URL.
        @exception  ForgeError When glab fails or no URL is printed.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.1
        """
        argv = [
            "glab", "mr", "create",
            "--repo", self.repo,
            "--source-branch", source,
            "--target-branch", target,
            "--title", title,
            "--description", body,
            "--yes",
        ]
        if draft:
            argv.append("--draft")
        if remove_source_branch:
            argv.append("--remove-source-branch")
        for reviewer in reviewers or []:
            argv += ["--reviewer", reviewer]
        result = self._run(argv, cwd=cwd)
        match = _MR_URL_RE.search(result.stdout)
        if not match:
            raise ForgeError("glab mr create printed no MR URL", result.argv, result.stdout)
        return match.group(0)

    # -- internals ------------------------------------------------------------------

    @property
    def _project_enc(self) -> str:
        """
        @brief   URL-encoded project path for API endpoints.
        @return  The percent-encoded repo path.
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-02
        @version 0.1.0
        """
        return urllib.parse.quote(self.repo, safe="")

    def _run(self, argv: list[str], cwd: str | None = None) -> CommandResult:
        """
        @brief      Run a glab command, raising ForgeError on failure.
        @param[in]  argv Full command vector.
        @param[in]  cwd Optional working directory (a git checkout when the
                        subcommand needs remote resolution).
        @return     The successful CommandResult.
        @exception  ForgeError When the command exits non-zero.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        result = self.runner(argv, cwd=cwd) if cwd else self.runner(argv)
        if not result.ok:
            raise ForgeError(f"{argv[0]} {argv[1]} failed", result.argv, result.stderr)
        return result

    @staticmethod
    def _is_not_found(result: CommandResult) -> bool:
        """
        @brief      Whether a failed result means the resource is gone.
        @param[in]  result The failed CommandResult.
        @return     True when stderr indicates a 404/not-found.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        text = (result.stderr + result.stdout).lower()
        return any(marker in text for marker in _NOT_FOUND_MARKERS)

    @staticmethod
    def _parse_json(result: CommandResult, expected: type) -> Any:
        """
        @brief      Parse a CLI JSON payload, checking the top-level type.
        @param[in]  result The successful CommandResult.
        @param[in]  expected Expected top-level type (list or dict).
        @return     The parsed payload.
        @exception  ForgeError When the output is not the expected JSON.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        try:
            payload = json.loads(result.stdout or "null")
        except json.JSONDecodeError as exc:
            raise ForgeError(f"invalid JSON from CLI: {exc}", result.argv) from exc
        if not isinstance(payload, expected):
            raise ForgeError(
                f"unexpected JSON shape (wanted {expected.__name__})", result.argv
            )
        return payload

    @staticmethod
    def _to_ticket(item: dict[str, Any]) -> Ticket:
        """
        @brief      Map one glab issue JSON record to a Ticket.
        @param[in]  item Raw issue mapping.
        @return     The normalized Ticket.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        return Ticket(
            iid=int(item["iid"]),
            title=item.get("title", ""),
            description=item.get("description") or "",
            labels=list(item.get("labels") or []),
            author=(item.get("author") or {}).get("username", ""),
            state=item.get("state", "opened"),
            web_url=item.get("web_url", ""),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", ""),
        )


# END OF FILE
