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
@file test_gates.py
@brief Tests for the .agentic workflow CLI wrappers.
@author Eng. Dan Dumitru Pasare
@date 2026-07-03
@version 0.1.1
"""

from __future__ import annotations

# IMPORTS
from adore.gates import (
    delivery_preflight,
    invariants,
    run_workflow_cli,
    workflow_resume,
    workflow_status,
)
from adore.util import CommandResult

# DATA MODELS / TYPEDEFINITIONS


class FakeExec:
    """
    @brief   Exec-seam double returning one canned result.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.0
    """

    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.calls: list[list[str]] = []

    def __call__(self, argv, *, timeout=None) -> CommandResult:
        self.calls.append([str(part) for part in argv])
        return self.result


# PUBLIC API / TESTS


def test_cli_runs_via_bash_with_single_tokens() -> None:
    """
    @brief   The CLI is invoked as `bash run.sh <verb>` - bash because run.sh
             uses pipefail (spike finding), single tokens for WSL safety.
    @version 0.1.0
    """
    execute = FakeExec(CommandResult(exit_code=0, stdout="{}"))
    result = run_workflow_cli(execute, "status")
    assert result.ok and result.output == "{}"
    assert execute.calls == [["bash", ".agentic/tools/run.sh", "status"]]
    assert all(" " not in token for token in execute.calls[0])


def test_failure_is_data_not_exception() -> None:
    """
    @brief   A failing check comes back as a GateResult; the conductor
             decides retry/escalate.
    @version 0.1.0
    """
    execute = FakeExec(CommandResult(exit_code=3, stderr="invariant broken"))
    result = invariants(execute)
    assert not result.ok
    assert result.exit_code == 3
    assert "invariant broken" in result.output


def test_named_wrappers_use_design_verbs() -> None:
    """
    @brief   invariants / status / resume / delivery-preflight map to the
             design-doc CLI verbs (confirmed against the live CLI in the pilot).
    @version 0.1.1
    """
    for wrapper, verb in (
        (invariants, "invariants"),
        (workflow_status, "status"),
        (workflow_resume, "resume"),
        (delivery_preflight, "delivery-preflight"),
    ):
        execute = FakeExec(CommandResult(exit_code=0))
        wrapper(execute)
        assert execute.calls[0][-1] == verb


# END OF FILE
