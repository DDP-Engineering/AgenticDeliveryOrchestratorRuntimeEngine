"""Shared ticket pickup eligibility rules."""


from __future__ import annotations

from dataclasses import replace

from adore.config import Config
from adore.forge import Ticket

#: Reason codes in the order the rules are checked; the first unmet rule wins.
INELIGIBILITY_REASONS = (
    "not_open",
    "epic",
    "missing_ready_label",
    "held",
    "excluded",
    "has_job",
    "missing_priority_label",
    "missing_acceptance_criteria",
)


def ineligibility(ticket: Ticket, config: Config, *, has_run: bool) -> str | None:
    """
    Name the first pickup rule a ticket does not meet.
    The state is confirmed even for listings that asked the forge
                for open tickets, because conducting a closed ticket would be
                worse than missing one.
    ticket: Candidate ticket.
    config: Project configuration (labels and readiness).
    has_run: Whether ADORE already holds a run for this ticket.
    Returns: A code from INELIGIBILITY_REASONS, or None when it is startable.
    """
    labels = config.labels
    if ticket.state != "opened":
        return "not_open"
    if labels.selection.type_epic in ticket.labels:
        return "epic"
    if labels.lifecycle.ready not in ticket.labels:
        return "missing_ready_label"
    if labels.control.hold in ticket.labels:
        return "held"
    if labels.control.exclude in ticket.labels:
        return "excluded"
    if has_run:
        return "has_job"
    readiness = config.readiness
    if readiness.require_priority_label and not any(
        label in ticket.labels for label in labels.selection.priority_order()
    ):
        return "missing_priority_label"
    if readiness.require_acceptance_criteria:
        body = ticket.description.lower()
        if "acceptance criteria" not in body and "- [ ]" not in ticket.description:
            return "missing_acceptance_criteria"
    return None


def _with_start_labels(ticket: Ticket, config: Config) -> tuple[Ticket, bool, bool]:
    """
    Add the labels an explicit Start may add to a copy of the ticket.
    ticket: Candidate ticket.
    config: Project configuration (labels and readiness).
    Returns: (prepared ticket, adds the ready label, needs a priority label).
    """
    labels = config.labels
    priorities = labels.selection.priority_order()
    adds_ready = labels.lifecycle.ready not in ticket.labels
    needs_priority = config.readiness.require_priority_label and not any(
        label in ticket.labels for label in priorities
    )
    added = ([labels.lifecycle.ready] if adds_ready else []) + (
        priorities[-1:] if needs_priority else []
    )
    return replace(ticket, labels=[*ticket.labels, *added]), adds_ready, needs_priority


def start_blocker(ticket: Ticket, config: Config, *, has_run: bool) -> str | None:
    """
    Name the pickup rule an explicit Start cannot satisfy by adding labels.
    ticket: Candidate ticket.
    config: Project configuration (labels and readiness).
    has_run: Whether ADORE already holds a run for this ticket.
    Returns: A code from INELIGIBILITY_REASONS, or None when Start can proceed.
    """
    prepared, _adds_ready, _needs_priority = _with_start_labels(ticket, config)
    return ineligibility(prepared, config, has_run=has_run)


def start_preparation(ticket: Ticket, config: Config, *, has_run: bool) -> tuple[bool, bool] | None:
    """
    Say which labels an explicit Start must add to make a ticket eligible.
    Start may add only the configured ready label and one priority
                label; every other rule (open state, hold, exclude, existing run,
                acceptance criteria) must already hold.
    ticket: Candidate ticket.
    config: Project configuration (labels and readiness).
    has_run: Whether ADORE already holds a run for this ticket.
    Returns: (adds the ready label, needs a priority label), or None when
                labels alone cannot make the ticket eligible.
    """
    prepared, adds_ready, needs_priority = _with_start_labels(ticket, config)
    if ineligibility(prepared, config, has_run=has_run) is not None:
        return None
    return adds_ready, needs_priority
