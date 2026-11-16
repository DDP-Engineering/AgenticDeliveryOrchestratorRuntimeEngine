"""Web helpers for browsing a project's forge tickets on explicit request."""


from __future__ import annotations

from datetime import UTC, datetime
from time import monotonic
from typing import Any

from adore.config import Config
from adore.forge import Comment, Forge, ForgeError, ForgeResponseError, Ticket, build_forge
from adore.selection import ineligibility, start_blocker, start_preparation
from adore.state import StateError, StateStore, derive_run_id
from adore.util import CommandRunner

#: Tickets shown per read; one more is requested to detect truncation.
TICKET_LIMIT = 500
#: Whole-request and per-command bounds for forge CLI calls (seconds).
REQUEST_DEADLINE = 60.0
COMMAND_TIMEOUT = 30.0
#: Run lifecycles that no longer have work to cancel.
FINISHED_LIFECYCLES = ("done", "failed", "cancelled", "handed-off", "handoff-pending")
#: Start blocker while the project's pickup is stopped (`adore pause`).
PICKUP_PAUSED = "pickup_paused"


class TicketReadError(Exception):
    """Forge output that cannot be shown safely (malformed records)."""


class RunReadError(Exception):
    """A persisted run for a listed ticket cannot be read."""


def _bounded(runner: CommandRunner) -> CommandRunner:
    """
    Cap every forge command and the whole request by a deadline.
    runner: Credential-scoped project runner.
    Returns: A runner raising TimeoutError once the request deadline passed.
    """
    deadline = monotonic() + REQUEST_DEADLINE

    def bounded(argv, *, cwd=None, timeout=None, env=None):
        """Run one forge command within the remaining request budget."""
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError("ticket read deadline")
        return runner(
            argv,
            cwd=cwd,
            timeout=min(timeout or COMMAND_TIMEOUT, COMMAND_TIMEOUT, remaining),
            env=env,
        )

    return bounded


def _job(state: StateStore, config: Config, iid: int) -> dict[str, str] | None:
    """
    Describe the run ADORE holds for a ticket, if any.
    state: Project state store.
    config: Project configuration (platform identity).
    iid: Ticket number.
    Returns: {run_id, lifecycle}, or None when no run exists.
    Raises RunReadError: When the persisted run cannot be read.
    """
    try:
        from hashlib import sha256

        run_id = state.latest_run_id(derive_run_id(config.platform.kind, config.platform.repo, iid))
        if not state.exists(run_id):
            return None
        run = state.load(run_id)
        result = {"run_id": run_id, "lifecycle": run.lifecycle}
        if run.lifecycle == "cancelled":
            result["state_revision"] = sha256(
                (state.run_dir(run_id) / "state.json").read_bytes()).hexdigest()
        return result
    except (OSError, StateError) as exc:
        raise RunReadError("run state is unreadable") from exc


def open_forge(config: Config, runner: CommandRunner) -> Forge:
    """
    Build the project's forge adapter for one bounded request.
    config: Validated project configuration.
    runner: Credential-scoped project runner.
    Returns: The adapter.
    Raises ForgeError: When the platform identity is not usable.
    """
    try:
        return build_forge(
            config.platform.kind,
            config.platform.repo,
            _bounded(runner),
            login=config.platform.login,
            organization=config.platform.organization, project=config.platform.project,
            area_path=config.platform.area_path, work_item_types=config.platform.work_item_types,
            closed_states=config.platform.closed_states,
        )
    except ValueError as exc:
        raise ForgeError(str(exc)) from exc


def ticket_view(forge: Forge, config: Config, state: StateStore) -> dict[str, Any]:
    """
    Read open tickets with eligibility and job state.
    forge: Bounded project forge adapter.
    config: Project configuration (labels, readiness, identity).
    state: Project state store.
    Returns: {read_at, truncated, ready_label, tickets[]}.
    Raises ForgeError: When the forge CLI fails; TicketReadError when output
                is malformed; RunReadError when a run cannot be read.
    """
    try:
        tickets = forge.list_open(TICKET_LIMIT + 1)
    except ForgeResponseError as exc:
        raise TicketReadError("malformed issue record") from exc
    rows = []
    for ticket in tickets[:TICKET_LIMIT]:
        job = _job(state, config, ticket.iid)
        reason = ineligibility(ticket, config, has_run=job is not None)
        preparation = start_preparation(ticket, config, has_run=job is not None)
        blocked_by = (None if preparation is not None
                      else start_blocker(ticket, config, has_run=job is not None))
        rows.append(
            {
                "can_start": preparation is not None,
                "blocked_by": blocked_by,
                "adds_ready_label": bool(preparation and preparation[0]),
                "needs_priority": bool(preparation and preparation[1]),
                "iid": ticket.iid,
                "title": ticket.title,
                "description": ticket.description,
                "labels": ticket.labels,
                "author": ticket.author,
                "web_url": ticket.web_url,
                "updated_at": ticket.updated_at,
                "startable": reason is None,
                "reason": reason,
                "job": job,
            }
        )
    return {
        "read_at": datetime.now(UTC).isoformat(),
        "truncated": len(tickets) > TICKET_LIMIT,
        "ready_label": config.labels.lifecycle.ready,
        "priority_labels": config.labels.selection.priority_order(),
        "tickets": rows,
    }


def comment_view(forge: Forge, iid: int) -> dict[str, Any] | None:
    """
    Read one ticket's human comments in forge order.
    forge: Bounded project forge adapter.
    iid: Ticket number.
    Returns: {iid, comments[]}, or None when the ticket does not exist.
    Raises ForgeError: When the forge CLI fails; TicketReadError when a
                comment record is malformed.
    """
    try:
        if forge.get_ticket(iid) is None:
            return None
        comments = forge.list_comments(iid)
    except (ForgeResponseError, KeyError, ValueError, TypeError, AttributeError) as exc:
        raise TicketReadError("malformed comment record") from exc
    shown = []
    for comment in comments:
        if not isinstance(comment, Comment) or not all(
            isinstance(value, str) for value in (comment.body, comment.author, comment.created_at)
        ):
            raise TicketReadError("malformed comment record")
        if not comment.system:
            shown.append(
                {"author": comment.author, "created_at": comment.created_at, "body": comment.body}
            )
    return {"iid": iid, "comments": shown}


def existing_job(state: StateStore, config: Config, iid: int) -> dict[str, str] | None:
    """
    Describe the run ADORE holds for a ticket, if any.
    state: Project state store.
    config: Project configuration.
    iid: Ticket number.
    Returns: {run_id, lifecycle}, or None when no run exists.
    Raises RunReadError: When the persisted run cannot be read.
    """
    return _job(state, config, iid)


def read_ticket(forge: Forge, iid: int) -> Ticket | None:
    """
    Read one ticket, failing closed on a malformed record.
    forge: Bounded project forge adapter.
    iid: Ticket number.
    Returns: The ticket, or None when it does not exist.
    Raises ForgeError: When the CLI fails; ForgeResponseError when malformed.
    """
    try:
        return forge.get_ticket(iid)
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ForgeResponseError("malformed issue record") from exc


def unfinished_run(state: StateStore, config: Config, iid: int) -> str | None:
    """
    Return the run id of a ticket's job that can still be cancelled.
    state: Project state store.
    config: Project configuration.
    iid: Ticket number.
    Returns: The run id, or None when there is no unfinished job.
    Raises RunReadError: When the persisted run cannot be read.
    """
    job = _job(state, config, iid)
    return job["run_id"] if job and job["lifecycle"] not in FINISHED_LIFECYCLES else None


def remove_ready_label(forge: Forge, config: Config, iid: int) -> tuple[Ticket | None, bool]:
    """
    Remove the configured ready label from a ticket when present.
    forge: Bounded project forge adapter.
    config: Project configuration (ready label).
    iid: Ticket number.
    Returns: (ticket or None when missing, whether the label was removed).
    Raises ForgeError: When reading or writing the ticket fails; its subclass
                ForgeResponseError when the ticket record is malformed.
    """
    ticket = read_ticket(forge, iid)
    ready = config.labels.lifecycle.ready
    if ticket is None or ready not in ticket.labels:
        return ticket, False
    forge.remove_labels(iid, [ready])
    return ticket, True
