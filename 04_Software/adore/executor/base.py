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
@brief The executor launcher contract (design doc 6/7a).
@details The executor performs code reasoning inside the run's container and
         drives the .agentic CLI; it never touches the remote. One gate per
         launch: the launcher composes the command, runs it through the
         container exec seam, and reads the results back from files (the
         event stream from the io dir, clarification questions from the
         worktree) - never from live stdout.
"""

from __future__ import annotations

# IMPORTS
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from adore.util import CommandResult

# DATA MODELS / TYPEDEFINITIONS


class ExecTarget(Protocol):
    """
    @brief   Callable that runs a command inside the run's container.
    @details The orchestrator binds ContainerManager.exec to the run's
             container name and passes it in; tests pass fakes. Matches the
             exec seam: exit codes come back as data.
    """

    def __call__(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> CommandResult:
        """
        @brief      Run one command inside the container.
        @param[in]  argv Command and arguments (must stay WSL-safe: no
                         element may rely on embedded spaces surviving).
        @param[in]  timeout Optional wall-clock bound.
        @return     The captured CommandResult.
        """
        ...  # pragma: no cover - protocol signature only


@dataclass
class GateRun:
    """
    @brief   Result of running one workflow gate via the executor.
    @details The conductor's decision inputs (design 7a step 3): the exit
             code, authoritative wrapper-timeout flag, and whether the executor
             asked clarification questions. `output` is the raw event stream
             (also persisted in the run's io dir for audit). `artifact_dirs`
             names immutable per-launch archive directories created by the file
             protocol. There is deliberately no session id: every stage gets a
             FRESH executor session, so nothing is ever continued.
    """

    exit_code: int
    has_questions: bool = False
    questions: str = ""
    output: str = ""
    stderr: str = ""
    timed_out: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    tokens_reported: bool | None = None
    cost_usd: float = 0.0
    cost_reported: bool = False
    artifact_dirs: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """
        @brief   True when the executor exited cleanly (code 0).
        @details Clean exit is necessary but not sufficient to advance: the
                 conductor still checks questions and runs invariants.
        @return  Exit-status flag.
        """
        return self.exit_code == 0


# PUBLIC API


class Executor(ABC):
    """
    @brief   Abstract executor launcher (opencode/pi/codex).
    """

    @abstractmethod
    def run_gate(
        self,
        execute: ExecTarget,
        worktree: str | Path,
        io_dir: str | Path,
        prompt: str,
        *,
        timeout: float | None = None,
        archive_stem: str = "",
    ) -> GateRun:
        """
        @brief      Launch the executor for a single workflow gate.
        @details    Every launch starts a FRESH executor session. The durable
                    AEGIS journal, not model memory, is the resume authority,
                    so there is no session to continue and no session argument.
        @param[in]  execute Exec seam bound to the run's container.
        @param[in]  worktree HOST path of the run's worktree (questions file).
        @param[in]  io_dir HOST path of the run's io exchange dir (gate
                           script in, event stream out; mounted at /adore/io).
        @param[in]  prompt Gate-specific instruction (any content; it never
                           travels through argv).
        @param[in]  timeout Wall-clock bound (run budgets).
        @param[in]  archive_stem Optional immutable archive name stem.
        @return     A GateRun describing the outcome.
        """


# END OF FILE
