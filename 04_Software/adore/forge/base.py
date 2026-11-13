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
"""

from __future__ import annotations

# IMPORTS
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
from typing import Any

from adore.util import CommandResult, CommandRunner

# CONSTANTS

#: The normalized pipeline vocabulary every adapter maps its platform's own
#: states onto. Only "failed" is acted on, and only by posting a notice: ADORE
#: does not gate delivery on CI. "none" and "unknown" are deliberately distinct
#: - no pipeline ran, versus the answer could not be read - even though both
#: are silent, because the journal records which one was observed.
PIPELINE_STATES = ("success", "failed", "running", "none", "unknown")

# DATA MODELS / TYPEDEFINITIONS


@dataclass
class Ticket:
    """
    @brief   Normalized ticket/issue view across platforms.
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
    """

    def __init__(self, message: str, argv: list[str] | None = None, stderr: str = "") -> None:
        """
        @brief      Build the error with command context.
        @param[in]  message Human-readable summary.
        @param[in]  argv The command that failed.
        @param[in]  stderr Captured stderr from the CLI.
        """
        detail = message
        if argv:
            detail += f" | argv: {' '.join(argv)}"
        if stderr.strip():
            detail += f" | stderr: {stderr.strip()}"
        super().__init__(detail)
        self.argv = argv or []
        self.stderr = stderr


class ForgeResponseError(ForgeError):
    """
    @brief   Raised when a platform CLI succeeded but its output has the wrong shape.
    @details Distinguishes untrusted malformed output (a forge or CLI defect)
             from an unavailable or failing CLI, so callers can report each.
    """


# PUBLIC API


class Forge(ABC):
    """
    @brief   Abstract Git-platform adapter (GitLab/GitHub/Gitea).
    @details Concrete adapters wrap `glab` / `gh` / `tea`. Identity is
             marker-based: comments carry a hidden marker; author is not
             relied upon. All methods raise ForgeError on unexpected CLI
             failure.
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
        """

    def list_open(self, limit: int) -> list[Ticket]:
        """
        @brief      List the repository's open issues, labelled or not, for browsing.
        @details    Unlike `list_ready`, this is not a selection boundary: callers
                    apply the shared eligibility rules to every returned ticket.
                    Adapters return at most `limit` tickets so a caller asking for
                    one more than it shows can tell that the backlog was truncated.
        @param[in]  limit Maximum number of tickets to return (positive).
        @return     Open tickets, at most `limit`.
        @exception  ForgeError When the CLI fails or an issue record is malformed.
        """
        raise ForgeError(f"{type(self).__name__} cannot list open tickets")

    def _open_tickets(self, items: list[Any], limit: int) -> list[Ticket]:
        """
        @brief      Map raw issue records for browsing, failing closed on bad input.
        @details    The selection mappers tolerate missing optional fields; browsing
                    shows every field to a person, so each record must be a mapping
                    with a list of labels and must map to well-typed text fields.
        @param[in]  items Raw issue records from the CLI.
        @param[in]  limit Maximum number of tickets to keep.
        @return     The mapped tickets, at most `limit`.
        @exception  ForgeError When any kept record is malformed.
        """
        tickets: list[Ticket] = []
        for item in items[:limit]:
            if not isinstance(item, dict) or not isinstance(item.get("labels") or [], list):
                raise ForgeResponseError("malformed issue record")
            try:
                ticket = self._to_ticket(item)  # type: ignore[attr-defined]
            except (KeyError, ValueError, TypeError, AttributeError) as exc:
                raise ForgeResponseError("malformed issue record") from exc
            text = (ticket.title, ticket.description, ticket.author, ticket.state,
                    ticket.web_url, ticket.created_at, ticket.updated_at)
            well_typed = all(isinstance(value, str) for value in text) and all(
                isinstance(label, str) for label in ticket.labels
            )
            if isinstance(ticket.iid, bool) or ticket.iid < 1 or not well_typed:
                raise ForgeResponseError("malformed issue record")
            tickets.append(ticket)
        return tickets

    @abstractmethod
    def get_ticket(self, iid: int) -> Ticket | None:
        """
        @brief      Fetch one ticket by id, for reconciliation and resume.
        @param[in]  iid Ticket id.
        @return     The ticket, or None when it no longer exists (deleted).
        """

    @abstractmethod
    def list_comments(self, iid: int) -> list[Comment]:
        """
        @brief      List a ticket's comments oldest-first (resume detection).
        @param[in]  iid Ticket id.
        @return     All comments including system notes (flagged).
        """

    @abstractmethod
    def post_comment(self, iid: int, body: str) -> int:
        """
        @brief      Post a marker-stamped comment on a ticket.
        @param[in]  iid Ticket id.
        @param[in]  body Comment body (marker appended by the caller).
        @return     The created comment id (recorded in state.json).
        """

    @abstractmethod
    def edit_comment(self, iid: int, comment_id: int, body: str) -> None:
        """
        @brief      Edit an existing comment in place (single status comment).
        @param[in]  iid Ticket id.
        @param[in]  comment_id Comment id previously returned by post_comment.
        @param[in]  body Replacement body.
        """

    @abstractmethod
    def add_labels(self, iid: int, labels: list[str]) -> None:
        """
        @brief      Add labels to a ticket.
        @param[in]  iid Ticket id.
        @param[in]  labels Label names to add.
        """

    def list_labels(self) -> list[str]:
        """
        @brief      Names of the labels defined in the repository.
        @exception  ForgeError When the adapter cannot list labels.
        """
        raise ForgeError("this forge cannot list labels")

    def create_label(self, name: str, color: str, description: str) -> None:
        """
        @brief      Create one repository label.
        @param[in]  name Label name.
        @param[in]  color Six hexadecimal digits, without #.
        @param[in]  description Short explanation shown by the forge.
        @exception  ForgeError When the forge refuses or the adapter cannot create labels.
        """
        raise ForgeError("this forge cannot create labels")

    @abstractmethod
    def remove_labels(self, iid: int, labels: list[str]) -> None:
        """
        @brief      Remove labels from a ticket.
        @param[in]  iid Ticket id.
        @param[in]  labels Label names to remove.
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
        """

    @abstractmethod
    def pipeline_status(self, mr_iid: int) -> str:
        """
        @brief      The forge pipeline verdict for an MR/PR, normalized.
        @details    Read only by the post-MR poll, so a repository without CI
                    pays nothing for it. ADORE does not gate on the result and
                    never merges: a red pipeline is surfaced to the human and
                    nothing else happens automatically.

                    Implementations are BEST-EFFORT and must never raise. The
                    poll that calls this is watching a run that is doing no
                    code work, so a forge hiccup on advisory information must
                    not disturb it; anything unreadable is "unknown", which is
                    silent.
        @param[in]  mr_iid MR iid / PR number.
        @return     One of PIPELINE_STATES: "success", "failed", "running"
                    (not finished yet), "none" (no pipeline, or a verdict that
                    is neither pass nor fail, such as skipped or cancelled), or
                    "unknown" (could not be determined).
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
        """

    @abstractmethod
    def post_mr_comment(self, mr_iid: int, body: str) -> int:
        """
        @brief      Post a marker-owned problem/status comment on an MR/PR.
        @param[in]  mr_iid MR/PR number.
        @param[in]  body Comment body.
        @return     Created comment id.
        """

    @abstractmethod
    def edit_mr_comment(self, mr_iid: int, comment_id: int, body: str) -> None:
        """
        @brief      Edit one marker-owned MR/PR comment in place.
        @param[in]  mr_iid MR/PR number.
        @param[in]  comment_id Existing comment id.
        @param[in]  body Replacement body.
        """

    @abstractmethod
    def remove_mr_labels(self, mr_iid: int, labels: list[str]) -> None:
        """
        @brief      Remove labels from an MR/PR (clear the revise trigger).
        @param[in]  mr_iid MR iid / PR number.
        @param[in]  labels Label names to remove.
        """

    def update_merge_request_body(self, mr_iid: int, body: str) -> None:
        """
        @brief Replace an existing review's description without changing review settings.
        @param[in] mr_iid MR/PR number bound to the run being published.
        @param[in] body Current approved candidate description.
        @exception ForgeError When the write fails or the adapter does not support it.
        """
        raise ForgeError("this forge cannot update an MR/PR description")

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
        @brief      Open a draft or ready merge/pull request. Never merges.
        @param[in]  source Source branch.
        @param[in]  target Target branch.
        @param[in]  title MR/PR title.
        @param[in]  body MR/PR description.
        @param[in]  draft Open as draft when true, otherwise ready for review.
        @param[in]  reviewers Human reviewers to assign.
        @param[in]  remove_source_branch Native deletion hint; conductor also cleans up after merge.
        @param[in]  cwd Git checkout to run in - the platform CLIs resolve
                        remotes from a local repo even with --repo (live
                        finding 2026-07-04: "No git remotes found"); pass the
                        run's worktree.
        @return     The MR/PR web URL.
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
        """
        try:
            payload = json.loads(result.stdout or "null")
        except json.JSONDecodeError as exc:
            raise ForgeResponseError(f"invalid JSON from CLI: {exc}", result.argv) from exc
        if not isinstance(payload, expected):
            raise ForgeResponseError(
                f"unexpected JSON shape (wanted {expected.__name__})", result.argv
            )
        return payload


# END OF FILE
