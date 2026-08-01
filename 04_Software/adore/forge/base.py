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
@details Every adapter (GitLab, GitHub, Gitea) implements this contract so the
         orchestrator never calls a platform CLI directly. Adapters cover the
         full remote surface ADORE needs: selection (list/get), signaling
         (comments, labels), and delivery (draft MR/PR). Merging is
         deliberately absent from the interface.

         `Forge` also carries the CLI-invocation plumbing shared by all three
         adapters verbatim (`_run`, `_parse_json`, `_is_not_found`): each
         wraps the injected `runner`, so a subclass only needs to set
         `self.runner` and, for the marker-based not-found heuristic,
         optionally override `_NOT_FOUND_MARKERS`. Gitea does not use
         `_is_not_found` - its `_api` seam already enforces the HTTP status
         line tea itself prints, which is a stronger signal than scanning
         stderr text for a marker, so that adapter's not-found handling is
         deliberately left as its own thing rather than forced through here.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.2.0
"""

from __future__ import annotations

# IMPORTS
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
from typing import Any

from adore.util import CommandResult, CommandRunner

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
    labels: list[str] = field(default_factory=list)


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
    @brief   Abstract Git-platform adapter (GitLab/GitHub/Gitea).
    @details Concrete adapters wrap `glab` / `gh` / `tea`. Identity is
             marker-based: comments carry a hidden marker; author is not
             relied upon. All methods raise ForgeError on unexpected CLI
             failure.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.2.0
    """

    #: injected by every concrete adapter's __init__.
    runner: CommandRunner

    #: stderr/stdout substrings (lowercased) that mean "resource is gone" for
    #: adapters whose CLI signals not-found through free text rather than a
    #: structured HTTP status. Subclasses override to widen the set.
    _NOT_FOUND_MARKERS: tuple[str, ...] = ("404", "not found")

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
    def list_mr_comments(self, mr_iid: int) -> list[Comment]:
        """
        @brief      List an MR/PR's discussion comments oldest-first.
        @details    The revise cycle feeds these to the executor as the
                    review thread (design 11b step 3).
        @param[in]  mr_iid MR iid / PR number.
        @return     All comments, system notes flagged where the platform
                    reports them.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-04
        @version    0.1.0
        """

    @abstractmethod
    def remove_mr_labels(self, mr_iid: int, labels: list[str]) -> None:
        """
        @brief      Remove labels from an MR/PR (clear the revise trigger).
        @param[in]  mr_iid MR iid / PR number.
        @param[in]  labels Label names to remove.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-04
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
        @param[in]  draft Open as draft (always true in ADORE).
        @param[in]  reviewers Human reviewers to assign.
        @param[in]  remove_source_branch Delete the branch on merge (GitLab).
        @param[in]  cwd Git checkout to run in - the platform CLIs resolve
                        remotes from a local repo even with --repo (live
                        finding 2026-07-04: "No git remotes found"); pass the
                        run's worktree.
        @return     The MR/PR web URL.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.2
        """

    # -- shared CLI plumbing (ADORE-PY-004) ----------------------------------------

    def _run(self, argv: list[str], cwd: str | None = None) -> CommandResult:
        """
        @brief      Run a platform CLI command, raising ForgeError on failure.
        @details    Identical across glab/gh/tea: the CLI name and subcommand
                    are already in argv, so the error message needs no
                    per-adapter parametrization.
        @param[in]  argv Full command vector.
        @param[in]  cwd Optional working directory (a git checkout when the
                        subcommand needs remote resolution).
        @return     The successful CommandResult.
        @exception  ForgeError When the command exits non-zero.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        result = self.runner(argv, cwd=cwd) if cwd else self.runner(argv)
        if not result.ok:
            raise ForgeError(f"{argv[0]} {argv[1]} failed", result.argv, result.stderr)
        return result

    def _is_not_found(self, result: CommandResult) -> bool:
        """
        @brief      Whether a failed result means the resource is gone.
        @details    Marker-based heuristic for adapters whose CLI reports
                    not-found as free text (glab, gh). Not used by the Gitea
                    adapter, whose `_api` seam enforces tea's own HTTP status
                    line instead - a stronger signal than text-scanning, and
                    intentionally not unified with this heuristic.
        @param[in]  result The failed CommandResult.
        @return     True when stderr/stdout indicates a 404/not-found.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        text = (result.stderr + result.stdout).lower()
        return any(marker in text for marker in self._NOT_FOUND_MARKERS)

    @staticmethod
    def _parse_json(result: CommandResult, expected: type) -> Any:
        """
        @brief      Parse a CLI JSON payload, checking the top-level type.
        @param[in]  result The successful CommandResult.
        @param[in]  expected Expected top-level type (list or dict).
        @return     The parsed payload.
        @exception  ForgeError When the output is not the expected JSON.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
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


# END OF FILE
