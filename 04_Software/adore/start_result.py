#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    start_result.py
@brief   Bound terminal results for manual ticket admission and explicit Retry.
@details The CLI emits one final versioned line. The worker accepts only bounded,
         duplicate-free evidence bound to the requested ticket and process exit.
"""

# IMPORTS
import json

from adore.selection import INELIGIBILITY_REASONS
from adore.util import strict_json_loads

# CONSTANTS
START_PREFIX = "ADORE_START_RESULT "
RETRY_PREFIX = "ADORE_RETRY_RESULT "
RETRY_REASONS = frozenset({
    "retried", "retry_failed", "run_unavailable", "not_failed", "notification_pending",
    "reprepare_unavailable", "configuration_invalid", "engine_setup_failed", "lock_held",
    "repository_unavailable", "state_unavailable", "engine_fault",
    "executable_missing", "account_mismatch", "permission_denied", "at_capacity",
})
START_REASONS = frozenset(INELIGIBILITY_REASONS) | {
    "started", "at_capacity", "workflow_unavailable", "ticket_unavailable",
    "project_archived", "configuration_invalid", "engine_setup_failed",
    "lock_held", "engine_fault", "invalid_request", "not_eligible",
    "repository_unavailable", "state_unavailable",
}


# DATA MODELS
class StartResultError(ValueError):
    """@brief Missing or corrupt terminal admission evidence."""


# PUBLIC API
def emit_start_result(ticket: int, exit_code: int, reason: str) -> None:
    """@brief Emit a closed reason with no CLI/forge/executor text.
    @param[in] ticket Requested positive ticket identity.
    @param[in] exit_code Actual CLI exit code.
    @param[in] reason Allowlisted admission outcome.
    """
    if reason not in START_REASONS:
        reason = "engine_fault"
    print(START_PREFIX + json.dumps({"schema": 1, "ticket": ticket,
                                    "exit_code": exit_code, "reason": reason}))


def read_start_result(stdout: str, *, ticket: int, exit_code: int) -> str:
    """@brief Validate only the final bounded result line, ignoring preceding logs.
    @param[in] stdout Captured untrusted process output.
    @param[in] ticket Requested identity to bind.
    @param[in] exit_code Observed process exit to bind.
    @return Allowlisted reason.
    @exception StartResultError Invalid, ambiguous or mismatched evidence.
    """
    try:
        line = stdout[-2048:].rstrip().splitlines()[-1]
        if len(line) > 1024 or not line.startswith(START_PREFIX):
            raise ValueError
        value = strict_json_loads(line[len(START_PREFIX):])
        if (not isinstance(value, dict)
                or set(value) != {"schema", "ticket", "exit_code", "reason"}
                or type(value["schema"]) is not int or value["schema"] != 1
                or type(value["ticket"]) is not int or value["ticket"] != ticket
                or type(value["exit_code"]) is not int or value["exit_code"] != exit_code
                or not isinstance(value["reason"], str) or value["reason"] not in START_REASONS
                or (value["reason"] == "started") != (exit_code == 0)):
            raise ValueError
        return value["reason"]
    except (ValueError, IndexError, TypeError, KeyError) as exc:
        raise StartResultError("invalid manual start result") from exc

def emit_retry_result(run_id: str, exit_code: int, reason: str) -> None:
    """@brief Emit a closed Retry reason, bound to the requested job and exit code.
    @param[in] run_id Requested job identity.
    @param[in] exit_code Actual process exit.
    @param[in] reason Allowlisted operation outcome; no raw process diagnostics.
    """
    if reason not in RETRY_REASONS:
        reason = "engine_fault"
    print(RETRY_PREFIX + json.dumps({"schema": 1, "run_id": run_id,
                                    "exit_code": exit_code, "reason": reason}))


def read_retry_result(stdout: str, *, run_id: str, exit_code: int) -> str:
    """@brief Read only bounded final evidence matching the requested Retry.
    @param[in] stdout Captured untrusted CLI output.
    @param[in] run_id Requested job identity.
    @param[in] exit_code Observed process exit.
    @return Allowlisted Retry reason.
    @exception StartResultError Missing, corrupt or mismatched terminal evidence.
    """
    try:
        line = stdout[-2048:].rstrip().splitlines()[-1]
        if len(line) > 1024 or not line.startswith(RETRY_PREFIX):
            raise ValueError
        value = strict_json_loads(line[len(RETRY_PREFIX):])
        if (not isinstance(value, dict)
                or set(value) != {"schema", "run_id", "exit_code", "reason"}
                or type(value["schema"]) is not int or value["schema"] != 1
                or not isinstance(value["run_id"], str) or value["run_id"] != run_id
                or type(value["exit_code"]) is not int or value["exit_code"] != exit_code
                or not isinstance(value["reason"], str) or value["reason"] not in RETRY_REASONS
                or (value["reason"] == "retried") != (exit_code == 0)):
            raise ValueError
        return value["reason"]
    except (ValueError, IndexError, TypeError, KeyError) as exc:
        raise StartResultError("invalid Retry result") from exc

RESTART_PREFIX = "ADORE_RESTART_RESULT "
RESTART_REASONS = frozenset({
    "restarted", "not_started", "cleanup_refused", "cleanup_failed", "engine_fault",
    "engine_setup_failed", "configuration_invalid", "lock_held", "run_unavailable",
    "force_required", "repository_unavailable",
})


def emit_restart_result(run_id: str, revision: str, exit_code: int, reason: str,
                        picked: int | None = None, retained: bool = False) -> None:
    """@brief Emit one terminal restart outcome bound to job, revision and exit."""
    if reason not in RESTART_REASONS:
        reason = "engine_fault"
    print(
        RESTART_PREFIX
        + json.dumps(
            {
                "schema": 1,
                "run_id": run_id,
                "revision": revision,
                "exit_code": exit_code,
                "reason": reason,
                "picked": picked,
                "retained": retained,
            }
        )
    )


def read_restart_result(
    stdout: str, *, run_id: str, revision: str, exit_code: int, ticket: int
) -> tuple[str, bool]:
    """@brief Validate the final closed restart result against the queued request.
    @exception StartResultError Missing, ambiguous or mismatched evidence.
    """
    try:
        line = stdout[-4096:].rstrip().splitlines()[-1]
        if len(line) > 2048 or not line.startswith(RESTART_PREFIX):
            raise ValueError
        value = strict_json_loads(line[len(RESTART_PREFIX) :])
        if (
            not isinstance(value, dict)
            or set(value)
            != {"schema", "run_id", "revision", "exit_code", "reason", "picked", "retained"}
            or type(value["schema"]) is not int
            or value["schema"] != 1
            or value["run_id"] != run_id
            or value["revision"] != revision
            or type(value["exit_code"]) is not int
            or value["exit_code"] != exit_code
            or not isinstance(value["reason"], str)
            or value["reason"] not in RESTART_REASONS
            or type(value["retained"]) is not bool
            or (value["reason"] == "restarted") != (exit_code == 0)
            or (exit_code == 0 and (type(value["picked"]) is not int or value["picked"] != ticket))
        ):
            raise ValueError
        if exit_code != 0 and (value["picked"] is not None or value["retained"]):
            raise ValueError
        return value["reason"], value["retained"]
    except (ValueError, IndexError, TypeError, KeyError) as exc:
        raise StartResultError("invalid restart result") from exc


# END OF FILE
