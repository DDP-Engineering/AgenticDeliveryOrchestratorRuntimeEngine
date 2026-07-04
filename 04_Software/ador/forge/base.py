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
@file base.py
@brief The Git-platform adapter interface.
@details Every adapter (GitLab, GitHub) implements this contract so the
         orchestrator never calls a platform CLI directly. Adapters cover the
         full remote surface ADOR needs: selection (list/get), signaling
         (comments, labels), and delivery (draft MR/PR). Merging is
         deliberately absent from the interface.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.1.0
"""

from __future__ import annotations

# IMPORTS
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# DATA MODELS / TYPEDEFINITIONS


@dataclass
class Ticket:
    """
    @brief   Normalized ticket/issue view across platforms.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    iid: int
    title: str
    description: str
    labels: list[str] = field(default_factory=list)
    author: str = ""
    state: str = "opened"
    web_url: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Comment:
    """
    @brief   Normalized ticket comment/note across platforms.
    @details `system` marks platform-generated notes (label changes etc.),
             which resume detection must ignore (design doc 9).
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    id: int
    body: str
    author: str = ""
    created_at: str = ""
    system: bool = False


@dataclass
class MergeRequest:
    """
    @brief   Normalized merge/pull request view across platforms.
    @details `state` is normalized to opened/merged/closed - the post-MR
             poll's terminal signals (design 11b).
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.0
    """

    iid: int
    state: str = "opened"
    web_url: str = ""
    draft: bool = True


class ForgeError(RuntimeError):
    """
    @brief   Raised when a platform CLI call fails unexpectedly.
    @details Carries the command and stderr so failures are diagnosable from
             the journal without re-running anything.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    def __init__(self, message: str, argv: list[str] | None = None, stderr: str = "") -> None:
        """
        @brief      Build the error with command context.
        @param[in]  message Human-readable summary.
        @param[in]  argv The command that failed.
        @param[in]  stderr Captured stderr from the CLI.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        detail = message
        if argv:
            detail += f" | argv: {' '.join(argv)}"
        if stderr.strip():
            detail += f" | stderr: {stderr.strip()}"
        super().__init__(detail)
        self.argv = argv or []
        self.stderr = stderr


# PUBLIC API


class Forge(ABC):
    """
    @brief   Abstract Git-platform adapter (GitLab/GitHub).
    @details Concrete adapters wrap `glab` / `gh`. Identity is marker-based:
             comments carry a hidden marker; author is not relied upon. All
             methods raise ForgeError on unexpected CLI failure.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    @abstractmethod
    def list_ready(self, ready_label: str) -> list[Ticket]:
        """
        @brief      List open tickets carrying the eligibility label.
        @param[in]  ready_label The opt-in label (for example "agent-ready").
        @return     Eligible tickets.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """

    @abstractmethod
    def get_ticket(self, iid: int) -> Ticket | None:
        """
        @brief      Fetch one ticket by id, for reconciliation and resume.
        @param[in]  iid Ticket id.
        @return     The ticket, or None when it no longer exists (deleted).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """

    @abstractmethod
    def list_comments(self, iid: int) -> list[Comment]:
        """
        @brief      List a ticket's comments oldest-first (resume detection).
        @param[in]  iid Ticket id.
        @return     All comments including system notes (flagged).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """

    @abstractmethod
    def post_comment(self, iid: int, body: str) -> int:
        """
        @brief      Post a marker-stamped comment on a ticket.
        @param[in]  iid Ticket id.
        @param[in]  body Comment body (marker appended by the caller).
        @return     The created comment id (recorded in state.json).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """

    @abstractmethod
    def edit_comment(self, iid: int, comment_id: int, body: str) -> None:
        """
        @brief      Edit an existing comment in place (single status comment).
        @param[in]  iid Ticket id.
        @param[in]  comment_id Comment id previously returned by post_comment.
        @param[in]  body Replacement body.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """

    @abstractmethod
    def add_labels(self, iid: int, labels: list[str]) -> None:
        """
        @brief      Add labels to a ticket.
        @param[in]  iid Ticket id.
        @param[in]  labels Label names to add.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """

    @abstractmethod
    def remove_labels(self, iid: int, labels: list[str]) -> None:
        """
        @brief      Remove labels from a ticket.
        @param[in]  iid Ticket id.
        @param[in]  labels Label names to remove.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """

    @abstractmethod
    def get_merge_request(self, ref: int | str) -> MergeRequest | None:
        """
        @brief      Fetch one MR/PR by iid/number or source branch.
        @details    Drives the post-MR poll: merged -> done, closed -> ended
                    (design 11b). Branch lookup typically finds only OPEN
                    MRs, so terminal-state polling must use the stored iid.
        @param[in]  ref MR iid/number, or the source branch name.
        @return     The MergeRequest, or None when none exists.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """

    @abstractmethod
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
        @brief      Open a DRAFT merge/pull request. Never merges.
        @param[in]  source Source branch.
        @param[in]  target Target branch.
        @param[in]  title MR/PR title.
        @param[in]  body MR/PR description.
        @param[in]  draft Open as draft (always true in ADOR).
        @param[in]  reviewers Human reviewers to assign.
        @param[in]  remove_source_branch Delete the branch on merge (GitLab).
        @param[in]  cwd Git checkout to run in - the platform CLIs resolve
                        remotes from a local repo even with --repo (live
                        finding 2026-07-04: "No git remotes found"); pass the
                        run's worktree.
        @return     The MR/PR web URL.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.1
        """


# END OF FILE
