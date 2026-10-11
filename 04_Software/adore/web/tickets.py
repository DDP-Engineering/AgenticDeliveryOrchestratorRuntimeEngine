#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
"""
@file    tickets.py
@brief   Web helpers for browsing a project's forge tickets on explicit request.
@details Builds a bounded forge adapter for one request, shapes open tickets
         with the shared pickup eligibility and any existing run, and shapes
         human comments. Forge output is untrusted: anything malformed raises
         TicketReadError so the API answers with a typed error, never a partial
         list. Callers own authorization, auditing and HTTP mapping.
"""

# IMPORTS

from __future__ import annotations

from datetime import UTC, datetime
from time import monotonic
from typing import Any

from adore.config import Config
from adore.forge import Comment, Forge, ForgeError, ForgeResponseError, Ticket, build_forge
from adore.selection import ineligibility, start_blocker, start_preparation
from adore.state import StateError, StateStore, derive_run_id
from adore.util import CommandRunner

# CONSTANTS

#: Tickets shown per read; one more is requested to detect truncation.
TICKET_LIMIT = 500
#: Whole-request and per-command bounds for forge CLI calls (seconds).
REQUEST_DEADLINE = 60.0
COMMAND_TIMEOUT = 30.0
#: Run lifecycles that no longer have work to cancel.
FINISHED_LIFECYCLES = ("done", "failed", "cancelled", "handed-off", "handoff-pending")

# DATA MODELS / TYPEDEFINITIONS


class TicketReadError(Exception):
    """
    @brief   Forge output that cannot be shown safely (malformed records).
    """


class RunReadError(Exception):
    """
    @brief   A persisted run for a listed ticket cannot be read.
    """


# HELPER FUNCTIONS


def _bounded(runner: CommandRunner) -> CommandRunner:
    """
    @brief      Cap every forge command and the whole request by a deadline.
    @param[in]  runner Credential-scoped project runner.
    @return     A runner raising TimeoutError once the request deadline passed.
    """
    deadline = monotonic() + REQUEST_DEADLINE

    def bounded(argv, *, cwd=None, timeout=None, env=None):
        """@brief Run one forge command within the remaining request budget."""
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
    @brief      Describe the run ADORE holds for a ticket, if any.
    @param[in]  state Project state store.
    @param[in]  config Project configuration (platform identity).
    @param[in]  iid Ticket number.
    @return     {run_id, lifecycle}, or None when no run exists.
    @exception  RunReadError When the persisted run cannot be read.
    """
    run_id = derive_run_id(config.platform.kind, config.platform.repo, iid)
    if not state.exists(run_id):
        return None
    try:
        return {"run_id": run_id, "lifecycle": state.load(run_id).lifecycle}
    except (FileNotFoundError, StateError) as exc:
        raise RunReadError("run state is unreadable") from exc


# PUBLIC API


def open_forge(config: Config, runner: CommandRunner) -> Forge:
    """
    @brief      Build the project's forge adapter for one bounded request.
    @param[in]  config Validated project configuration.
    @param[in]  runner Credential-scoped project runner.
    @return     The adapter.
    @exception  ForgeError When the platform identity is not usable.
    """
    try:
        return build_forge(
            config.platform.kind,
            config.platform.repo,
            _bounded(runner),
            login=config.platform.login,
        )
    except ValueError as exc:
        raise ForgeError(str(exc)) from exc


def ticket_view(forge: Forge, config: Config, state: StateStore) -> dict[str, Any]:
    """
    @brief      Read open tickets with eligibility and job state.
    @param[in]  forge Bounded project forge adapter.
    @param[in]  config Project configuration (labels, readiness, identity).
    @param[in]  state Project state store.
    @return     {read_at, truncated, ready_label, tickets[]}.
    @exception  ForgeError When the forge CLI fails; TicketReadError when output
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
        rows.append(
            {
                "can_start": preparation is not None,
                "blocked_by": None
                if preparation is not None
                else start_blocker(ticket, config, has_run=job is not None),
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
    @brief      Read one ticket's human comments in forge order.
    @param[in]  forge Bounded project forge adapter.
    @param[in]  iid Ticket number.
    @return     {iid, comments[]}, or None when the ticket does not exist.
    @exception  ForgeError When the forge CLI fails; TicketReadError when a
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
    @brief      Describe the run ADORE holds for a ticket, if any.
    @param[in]  state Project state store.
    @param[in]  config Project configuration.
    @param[in]  iid Ticket number.
    @return     {run_id, lifecycle}, or None when no run exists.
    @exception  RunReadError When the persisted run cannot be read.
    """
    return _job(state, config, iid)


def read_ticket(forge: Forge, iid: int) -> Ticket | None:
    """
    @brief      Read one ticket, failing closed on a malformed record.
    @param[in]  forge Bounded project forge adapter.
    @param[in]  iid Ticket number.
    @return     The ticket, or None when it does not exist.
    @exception  ForgeError When the CLI fails; ForgeResponseError when malformed.
    """
    try:
        return forge.get_ticket(iid)
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ForgeResponseError("malformed issue record") from exc


def unfinished_run(state: StateStore, config: Config, iid: int) -> str | None:
    """
    @brief      Return the run id of a ticket's job that can still be cancelled.
    @param[in]  state Project state store.
    @param[in]  config Project configuration.
    @param[in]  iid Ticket number.
    @return     The run id, or None when there is no unfinished job.
    @exception  RunReadError When the persisted run cannot be read.
    """
    job = _job(state, config, iid)
    return job["run_id"] if job and job["lifecycle"] not in FINISHED_LIFECYCLES else None


def remove_ready_label(forge: Forge, config: Config, iid: int) -> tuple[Ticket | None, bool]:
    """
    @brief      Remove the configured ready label from a ticket when present.
    @param[in]  forge Bounded project forge adapter.
    @param[in]  config Project configuration (ready label).
    @param[in]  iid Ticket number.
    @return     (ticket or None when missing, whether the label was removed).
    @exception  ForgeError When reading or writing the ticket fails; its subclass
                ForgeResponseError when the ticket record is malformed.
    """
    ticket = read_ticket(forge, iid)
    ready = config.labels.lifecycle.ready
    if ticket is None or ready not in ticket.labels:
        return ticket, False
    forge.remove_labels(iid, [ready])
    return ticket, True


# END OF FILE
