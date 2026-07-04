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
@file gates.py
@brief Wrappers around the target repository's .agentic workflow CLI.
@details The conductor's own verification between gates (design 7a step 4):
         the executor runs these commands itself during a gate, and the
         orchestrator re-checks with the same CLI afterwards - the objective
         signal is the exit code, never the executor's word. Commands run
         INSIDE the run's container through the exec seam (the CLI needs the
         container's Python; run.sh is bash, spike finding 2026-07-03).
@author Eng. Dan Dumitru Pasare
@date 2026-07-03
@version 0.1.1
"""

from __future__ import annotations

# IMPORTS
from dataclasses import dataclass

from ador.executor.base import ExecTarget

# CONSTANTS

WORKFLOW_CLI = ".agentic/tools/run.sh"

# DATA MODELS / TYPEDEFINITIONS


@dataclass
class GateResult:
    """
    @brief   Outcome of one workflow CLI invocation.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.1
    """

    ok: bool
    exit_code: int
    output: str


# PUBLIC API


def run_workflow_cli(
    execute: ExecTarget,
    *args: str,
    timeout: float | None = 600,
) -> GateResult:
    """
    @brief      Run one .agentic CLI command inside the run's container.
    @details    Invoked as `bash .agentic/tools/run.sh <args...>` in the
                container working dir (/ador/work). Every argv element is a
                single token (WSL-safe). Failure is data: the caller decides
                retry/escalate from the exit code.
    @param[in]  execute Exec seam bound to the run's container.
    @param[in]  args CLI verb and arguments (for example "invariants").
    @param[in]  timeout Wall-clock bound.
    @return     The GateResult.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    result = execute(["bash", WORKFLOW_CLI, *args], timeout=timeout)
    return GateResult(
        ok=result.ok,
        exit_code=result.exit_code,
        output=(result.stdout + result.stderr).strip(),
    )


def invariants(execute: ExecTarget, timeout: float | None = 600) -> GateResult:
    """
    @brief      Evaluate workflow invariants (the between-gates check).
    @param[in]  execute Exec seam bound to the run's container.
    @param[in]  timeout Wall-clock bound.
    @return     GateResult; ok means the gate output is coherent.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.1
    """
    return run_workflow_cli(execute, "invariants", timeout=timeout)


def workflow_status(execute: ExecTarget, timeout: float | None = 300) -> GateResult:
    """
    @brief      Read the current workflow run state (run-state JSON).
    @param[in]  execute Exec seam bound to the run's container.
    @param[in]  timeout Wall-clock bound.
    @return     GateResult with the status JSON in output.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    return run_workflow_cli(execute, "status", timeout=timeout)


def gates_run(execute: ExecTarget, timeout: float | None = 1800) -> GateResult:
    """
    @brief      Re-run the workflow's configured test gates (`gates run`).
    @details    Delivery step 3 (design 11a): integrating the target branch
                can break a change that passed in isolation.
    @param[in]  execute Exec seam bound to the run's container.
    @param[in]  timeout Wall-clock bound.
    @return     GateResult with the pass/fail outcome.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    return run_workflow_cli(execute, "gates", "run", timeout=timeout)


def delivery_preflight(execute: ExecTarget, timeout: float | None = 1800) -> GateResult:
    """
    @brief      Run the authoritative delivery-preflight check.
    @details    The objective "done" signal (design 7): the delivery phase
                loops until this exits 0.
    @param[in]  execute Exec seam bound to the run's container.
    @param[in]  timeout Wall-clock bound.
    @return     GateResult with the pass/fail outcome.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.1
    """
    return run_workflow_cli(execute, "delivery-preflight", timeout=timeout)


# END OF FILE
