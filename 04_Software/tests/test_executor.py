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
@file test_executor.py
@brief Pi factory and refusal of unsupported process targets.
@details Existing RPC transport, archive and usage contracts live in test_pi_rpc.py.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable, Sequence
from pathlib import Path

from adore.executor.launcher import (
    PiExecutor,
    build_executor,
)
from adore.prompts import PromptCatalog
from adore.util import CommandResult

# CONSTANTS


# DATA MODELS / TYPEDEFINITIONS


class FakeExec:
    """
    @brief   Exec-seam double: records argv, simulates gate side effects.
    """

    def __init__(
        self,
        result: CommandResult,
        side_effect: Callable[[], None] | None = None,
    ) -> None:
        """
        @brief      Configure the double.
        @param[in]  result The CommandResult to return.
        @param[in]  side_effect Callable simulating what the executor wrote
                                (output file, questions file) while running.
        """
        self.result = result
        self.side_effect = side_effect
        self.calls: list[list[str]] = []
        self.timeouts: list[float | None] = []

    def __call__(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> CommandResult:
        """
        @brief      Record the call, run the side effect, return the result.
        @param[in]  argv Command vector.
        @param[in]  timeout Recorded for budget assertions.
        @return     The canned CommandResult.
        """
        self.calls.append([str(part) for part in argv])
        self.timeouts.append(timeout)
        if self.side_effect:
            self.side_effect()
        return self.result


# HELPER FUNCTIONS


# PUBLIC API / TESTS


def test_executor_failure_passes_through_as_data(tmp_path: Path) -> None:
    """@brief A callable-only target is refused without executing or writing files."""
    target = FakeExec(CommandResult())
    result = PiExecutor("m").run_gate(target, tmp_path, tmp_path / "io", "prompt")
    assert result.exit_code == 126 and not result.ok
    assert "RPC process target" in result.stderr
    assert target.calls == [] and not (tmp_path / "io").exists()


def test_factory_wires_questions_file() -> None:
    """
    @brief   The factory builds the Pi launcher and passes the configured
             questions filename through.
    """
    prompts = PromptCatalog()
    executor = build_executor("m", questions_file="ROBO_QUESTIONS.md", prompts=prompts)
    assert isinstance(executor, PiExecutor)
    assert executor.questions_file == "ROBO_QUESTIONS.md"
    assert executor.prompts is prompts


def test_factory_selects_pi() -> None:
    """
    @brief   Pi is the only executor: the factory always returns PiExecutor.
    """
    executor = build_executor("openai/gpt-5.5")
    assert isinstance(executor, PiExecutor)
    assert executor.questions_file == "ADORE_QUESTIONS.md"


def test_pi_rpc_argv_carries_thinking_level() -> None:
    """@brief Explicit Pi effort reaches the process; empty leaves its default."""
    from adore.executor.launcher import pi_rpc_argv
    assert pi_rpc_argv("gpt-5", "openai", thinking="medium")[-2:] == ["--thinking", "medium"]
    assert "--thinking" not in pi_rpc_argv("gpt-5", "openai")


# END OF FILE
