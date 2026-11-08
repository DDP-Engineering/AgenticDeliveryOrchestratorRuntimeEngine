#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
"""
@file    test_selection.py
@brief   Contract tests for the shared ticket pickup eligibility rules.
@details The orchestrator's selection and the web ticket browser both ask
         `ineligibility`; these tests pin the first unmet rule it reports.
"""

# IMPORTS

from __future__ import annotations

from dataclasses import replace

from adore.config import Config, ReadinessConfig, validate_config
from adore.forge import Ticket
from adore.selection import INELIGIBILITY_REASONS, ineligibility, start_blocker, start_preparation
import pytest

# HELPER FUNCTIONS


def _ticket(*labels: str, state: str = "opened", description: str = "") -> Ticket:
    """
    @brief      Build a ticket with the given labels.
    @param[in]  labels Ticket labels.
    @param[in]  state Normalized ticket state.
    @param[in]  description Ticket body.
    @return     The ticket.
    """
    return Ticket(iid=12, title="Ticket", description=description, labels=list(labels), state=state)


# PUBLIC API / TESTS


def test_ready_prioritized_open_ticket_without_job_is_startable() -> None:
    """
    @brief   A ticket meeting every rule has no ineligibility reason.
    """
    assert ineligibility(_ticket("agent-ready", "P2"), Config(), has_run=False) is None


@pytest.mark.parametrize(
    ("ticket", "has_run", "reason"),
    [
        (_ticket("agent-ready", "P2", state="closed"), False, "not_open"),
        (_ticket("P2"), False, "missing_ready_label"),
        (_ticket("agent-ready", "P2", "agent-hold"), False, "held"),
        (_ticket("agent-ready", "P2", "no-agent"), False, "excluded"),
        (_ticket("agent-ready", "P2"), True, "has_job"),
        (_ticket("agent-ready"), False, "missing_priority_label"),
        (_ticket("P2", "agent-hold"), True, "missing_ready_label"),
    ],
)
def test_first_unmet_rule_is_reported(ticket: Ticket, has_run: bool, reason: str) -> None:
    """
    @brief   Rules are checked in selection order and the first failure is named.
    @param[in]  ticket Candidate ticket.
    @param[in]  has_run Whether a run already exists for it.
    @param[in]  reason Expected reason code.
    """
    assert ineligibility(ticket, Config(), has_run=has_run) == reason
    assert reason in INELIGIBILITY_REASONS


def test_acceptance_criteria_rule_applies_only_when_configured() -> None:
    """
    @brief   Acceptance criteria are required only when readiness asks for them.
    """
    strict = replace(Config(), readiness=ReadinessConfig(require_acceptance_criteria=True))
    assert (
        ineligibility(_ticket("agent-ready", "P2"), strict, has_run=False)
        == "missing_acceptance_criteria"
    )
    assert (
        ineligibility(
            _ticket("agent-ready", "P2", description="- [ ] works"), strict, has_run=False
        )
        is None
    )
    relaxed = replace(Config(), readiness=ReadinessConfig(require_priority_label=False))
    assert ineligibility(_ticket("agent-ready"), relaxed, has_run=False) is None


@pytest.mark.parametrize(
    ("ticket", "has_run", "expected"),
    [
        (_ticket("agent-ready", "P2"), False, (False, False)),
        (_ticket("P2"), False, (True, False)),
        (_ticket(), False, (True, True)),
        (_ticket("agent-ready"), False, (False, True)),
        (_ticket("P2", "agent-hold"), False, None),
        (_ticket("no-agent"), False, None),
        (_ticket("P2", state="closed"), False, None),
        (_ticket("P2"), True, None),
    ],
)
def test_start_preparation_names_only_label_fixes(
    ticket: Ticket, has_run: bool, expected: tuple[bool, bool] | None
) -> None:
    """
    @brief   Start may add the ready and priority labels and nothing else.
    @param[in]  ticket Candidate ticket.
    @param[in]  has_run Whether a run already exists.
    @param[in]  expected (adds ready label, needs priority) or None.
    """
    assert start_preparation(ticket, Config(), has_run=has_run) == expected


def test_start_preparation_keeps_acceptance_criteria_blocking() -> None:
    """
    @brief   Missing acceptance criteria cannot be fixed by labels.
    """
    strict = replace(Config(), readiness=ReadinessConfig(require_acceptance_criteria=True))
    assert start_preparation(_ticket(), strict, has_run=False) is None
    described = _ticket(description="- [ ] done")
    assert start_preparation(described, strict, has_run=False) == (True, True)


def test_start_blocker_names_the_rule_labels_cannot_fix() -> None:
    """
    @brief   The blocker skips label rules Start can fix and names the real obstacle.
    """
    assert start_blocker(_ticket("agent-hold"), Config(), has_run=False) == "held"
    assert start_blocker(_ticket("P2"), Config(), has_run=True) == "has_job"
    assert start_blocker(_ticket(), Config(), has_run=False) is None



def test_epic_type_label_blocks_selection_and_rejects_empty_configuration() -> None:
    """@brief Shared selection uses the configured label and rejects invalid settings."""
    config = Config()
    config.labels.selection.type_epic = "initiative"
    assert (ineligibility(_ticket("agent-ready", "P2", "initiative"), config,
                          has_run=False) == "epic")
    assert start_preparation(_ticket("initiative"), config, has_run=False) is None
    assert ineligibility(_ticket("agent-ready", "P2", "epic"), config, has_run=False) is None
    config.labels.selection.type_epic = " "
    assert any("type_epic" in issue for issue in validate_config(config))


# END OF FILE
