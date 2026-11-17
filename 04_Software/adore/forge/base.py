"""The Git-platform adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
from typing import Any

from adore.util import CommandResult, CommandRunner

#: The normalized pipeline vocabulary every adapter maps its platform's own
#: states onto. Only "failed" is acted on, and only by posting a notice: ADORE
#: does not gate delivery on CI. "none" and "unknown" are deliberately distinct
#: - no pipeline ran, versus the answer could not be read - even though both
#: are silent, because the journal records which one was observed.
PIPELINE_STATES = ("success", "failed", "running", "none", "unknown")


@dataclass
class Ticket:
    """Normalized ticket/issue view across platforms."""

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
    Normalized ticket comment/note across platforms.
    `system` marks platform-generated notes (label changes etc.),
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
    Normalized merge/pull request view across platforms.
    `state` is normalized to opened/merged/closed - the post-MR
             poll's terminal signals (design 11b).
    """

    iid: int
    state: str = "opened"
    web_url: str = ""
    draft: bool = True
    labels: list[str] = field(default_factory=list)


class ForgeError(RuntimeError):
    """
    Raised when a platform CLI call fails unexpectedly.
    Carries the command and stderr so failures are diagnosable from
             the journal without re-running anything.
    """

    def __init__(self, message: str, argv: list[str] | None = None, stderr: str = "") -> None:
        """
        Build the error with command context.
        message: Human-readable summary.
        argv: The command that failed.
        stderr: Captured stderr from the CLI.
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
    Raised when a platform CLI succeeded but its output has the wrong shape.
    Distinguishes untrusted malformed output (a forge or CLI defect)
             from an unavailable or failing CLI, so callers can report each.
    """


class Forge(ABC):
    """
    Abstract Git-platform adapter (GitLab/GitHub/Gitea).
    Concrete adapters wrap `glab` / `gh` / `tea`. Identity is
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
        List open tickets carrying the eligibility label.
        ready_label: The opt-in label (for example "agent-ready").
        Returns: Eligible tickets.
        """

    def list_open(self, limit: int) -> list[Ticket]:
        """
        List the repository's open issues, labelled or not, for browsing.
        Unlike `list_ready`, this is not a selection boundary: callers
                    apply the shared eligibility rules to every returned ticket.
                    Adapters return at most `limit` tickets so a caller asking for
                    one more than it shows can tell that the backlog was truncated.
        limit: Maximum number of tickets to return (positive).
        Returns: Open tickets, at most `limit`.
        Raises ForgeError: When the CLI fails or an issue record is malformed.
        """
        raise ForgeError(f"{type(self).__name__} cannot list open tickets")

    def _open_tickets(self, items: list[Any], limit: int) -> list[Ticket]:
        """
        Map raw issue records for browsing, failing closed on bad input.
        The selection mappers tolerate missing optional fields; browsing
                    shows every field to a person, so each record must be a mapping
                    with a list of labels and must map to well-typed text fields.
        items: Raw issue records from the CLI.
        limit: Maximum number of tickets to keep.
        Returns: The mapped tickets, at most `limit`.
        Raises ForgeError: When any kept record is malformed.
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
        Fetch one ticket by id, for reconciliation and resume.
        iid: Ticket id.
        Returns: The ticket, or None when it no longer exists (deleted).
        Raises ForgeError: Also from an adapter that cannot tell a deleted ticket
                    from one it may not read. Azure DevOps does this on purpose and
                    never returns None, so a deleted Work Item is a forge failure
                    there, not a deletion.
        """

    @abstractmethod
    def list_comments(self, iid: int) -> list[Comment]:
        """
        List a ticket's comments oldest-first (resume detection).
        iid: Ticket id.
        Returns: All comments including system notes (flagged).
        """

    @abstractmethod
    def post_comment(self, iid: int, body: str) -> int:
        """
        Post a marker-stamped comment on a ticket.
        iid: Ticket id.
        body: Comment body (marker appended by the caller).
        Returns: The created comment id (recorded in state.json).
        """

    @abstractmethod
    def edit_comment(self, iid: int, comment_id: int, body: str) -> None:
        """
        Edit an existing comment in place (single status comment).
        iid: Ticket id.
        comment_id: Comment id previously returned by post_comment.
        body: Replacement body.
        """

    @abstractmethod
    def add_labels(self, iid: int, labels: list[str]) -> None:
        """
        Add labels to a ticket.
        iid: Ticket id.
        labels: Label names to add.
        """

    def list_labels(self) -> list[str]:
        """
        Names of the labels defined in the repository.
        Raises ForgeError: When the adapter cannot list labels.
        """
        raise ForgeError("this forge cannot list labels")

    def create_label(self, name: str, color: str, description: str) -> None:
        """
        Create one repository label.
        name: Label name.
        color: Six hexadecimal digits, without #.
        description: Short explanation shown by the forge.
        Raises ForgeError: When the forge refuses or the adapter cannot create labels.
        """
        raise ForgeError("this forge cannot create labels")

    @abstractmethod
    def remove_labels(self, iid: int, labels: list[str]) -> None:
        """
        Remove labels from a ticket.
        iid: Ticket id.
        labels: Label names to remove.
        """

    @abstractmethod
    def get_merge_request(self, ref: int | str) -> MergeRequest | None:
        """
        Fetch one MR/PR by iid/number or source branch.
        Drives the post-MR poll: merged -> done, closed -> ended
                    (design 11b). Branch lookup typically finds only OPEN
                    MRs, so terminal-state polling must use the stored iid.
        ref: MR iid/number, or the source branch name.
        Returns: The MergeRequest, or None when none exists.
        """

    @abstractmethod
    def pipeline_status(self, mr_iid: int) -> str:
        """
        The forge pipeline verdict for an MR/PR, normalized.
        Read only by the post-MR poll, so a repository without CI
                    pays nothing for it. ADORE does not gate on the result and
                    never merges: a red pipeline is surfaced to the human and
                    nothing else happens automatically.

                    Implementations are BEST-EFFORT and must never raise. The
                    poll that calls this is watching a run that is doing no
                    code work, so a forge hiccup on advisory information must
                    not disturb it; anything unreadable is "unknown", which is
                    silent.
        mr_iid: MR iid / PR number.
        Returns: One of PIPELINE_STATES: "success", "failed", "running"
                    (not finished yet), "none" (no pipeline, or a verdict that
                    is neither pass nor fail, such as skipped or cancelled), or
                    "unknown" (could not be determined).
        """

    @abstractmethod
    def list_mr_comments(self, mr_iid: int) -> list[Comment]:
        """
        List an MR/PR's discussion comments oldest-first.
        The revise cycle feeds these to the executor as the
                    review thread (design 11b step 3).
        mr_iid: MR iid / PR number.
        Returns: All comments, system notes flagged where the platform
                    reports them.
        """

    @abstractmethod
    def post_mr_comment(self, mr_iid: int, body: str) -> int:
        """
        Post a marker-owned problem/status comment on an MR/PR.
        mr_iid: MR/PR number.
        body: Comment body.
        Returns: Created comment id.
        """

    @abstractmethod
    def edit_mr_comment(self, mr_iid: int, comment_id: int, body: str) -> None:
        """
        Edit one marker-owned MR/PR comment in place.
        mr_iid: MR/PR number.
        comment_id: Existing comment id.
        body: Replacement body.
        """

    @abstractmethod
    def remove_mr_labels(self, mr_iid: int, labels: list[str]) -> None:
        """
        Remove labels from an MR/PR (clear the revise trigger).
        mr_iid: MR iid / PR number.
        labels: Label names to remove.
        """

    def link_ticket(self, mr_iid: int, ticket_iid: int) -> None:
        """
        Associate a ticket with its PR when the provider requires a native link.
        mr_iid: Published or adopted PR ID.
        ticket_iid: Source ticket ID; repeated calls must be idempotent.
        Note: Other providers already retain the ticket reference in the description.
        """
        return None

    def update_merge_request_body(self, mr_iid: int, body: str) -> None:
        """
        Replace an existing review's description without changing review settings.
        mr_iid: MR/PR number bound to the run being published.
        body: Current approved candidate description.
        Raises ForgeError: When the write fails or the adapter does not support it.
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
        Open a draft or ready merge/pull request. Never merges.
        source: Source branch.
        target: Target branch.
        title: MR/PR title.
        body: MR/PR description.
        draft: Open as draft when true, otherwise ready for review.
        reviewers: Human reviewers to assign.
        remove_source_branch: Native deletion hint; conductor also cleans up after merge.
        cwd: Git checkout to run in - the platform CLIs resolve
                        remotes from a local repo even with --repo (live
                        finding 2026-07-04: "No git remotes found"); pass the
                        run's worktree.
        Returns: The MR/PR web URL.
        """

    # -- shared CLI plumbing (ADORE-PY-004) ----------------------------------------

    def _run(self, argv: list[str], cwd: str | None = None) -> CommandResult:
        """
        Run a platform CLI command, raising ForgeError on failure.
        Identical across glab/gh/tea: the CLI name and subcommand
                    are already in argv, so the error message needs no
                    per-adapter parametrization.
        argv: Full command vector.
        cwd: Optional working directory (a git checkout when the
                        subcommand needs remote resolution).
        Returns: The successful CommandResult.
        Raises ForgeError: When the command exits non-zero.
        """
        result = self.runner(argv, cwd=cwd) if cwd else self.runner(argv)
        if not result.ok:
            raise ForgeError(f"{argv[0]} {argv[1]} failed", result.argv, result.stderr)
        return result

    def _is_not_found(self, result: CommandResult) -> bool:
        """
        Whether a failed result means the resource is gone.
        Marker-based heuristic for adapters whose CLI reports
                    not-found as free text (glab, gh). Not used by the Gitea
                    adapter, whose `_api` seam enforces tea's own HTTP status
                    line instead - a stronger signal than text-scanning, and
                    intentionally not unified with this heuristic.
        result: The failed CommandResult.
        Returns: True when stderr/stdout indicates a 404/not-found.
        """
        text = (result.stderr + result.stdout).lower()
        return any(marker in text for marker in self._NOT_FOUND_MARKERS)

    @staticmethod
    def _parse_json(result: CommandResult, expected: type) -> Any:
        """
        Parse a CLI JSON payload, checking the top-level type.
        result: The successful CommandResult.
        expected: Expected top-level type (list or dict).
        Returns: The parsed payload.
        Raises ForgeError: When the output is not the expected JSON.
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
