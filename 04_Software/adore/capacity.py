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
@file       capacity.py
@brief      Canonical project admission ceiling including reviewed staged reductions.
@details    A lower staged polling.max_concurrent_runs fences new reservations while
            bound active configuration bytes remain unchanged for admitted jobs.
"""

# IMPORTS
from datetime import datetime
from hashlib import sha256
import re
import tomllib

from adore.config import Config, load_config
from adore.state import StateError
from adore.util import strict_json_loads


# PUBLIC API
def initial_start_slots(state, runs: list) -> set[str]:
    """@brief Count started execution/cleanup slots, excluding queued reservations.
    @param[in] state Project state store with current live execution locks.
    @param[in] runs Validated current runs.
    @return Occupied starts; pending reservations retain admission without deadlocking dispatch.
    """
    return state.execution_slots() | {
        run.run_id
        for run in runs
        if run.lifecycle == "working" and not run.execution_pending
        or run.lifecycle == "handoff-pending"
        or run.lifecycle == "parked-clarification"
        and run.parked_polls == 0
    }


def admission_limit(config: Config) -> int:
    """@brief Reread canonical N and apply only a current staged lower N.
    @param[in] config Bound project config or an explicitly injected configuration.
    @return Positive ceiling; staged increases wait for safe application.
    @exception StateError Corrupt, linked, oversized or stale capacity evidence;
               names the staged record the operator can explicitly discard.
    """
    try:
        current = load_config(config.source_path) if config.source_path is not None else config
        limit = current.polling.max_concurrent_runs
        if type(limit) is not int or limit < 1:
            raise ValueError("invalid limit")
    except (OSError, ValueError, TypeError) as exc:
        raise StateError("cannot read valid current project capacity") from exc
    if config.source_path is None:
        return limit
    pending = config.source_path.parent / "pending_config.json"
    try:
        if pending.is_symlink():
            raise ValueError("linked staged record")
        try:
            size = pending.stat().st_size
        except FileNotFoundError:
            return limit
        if size > 2097152:
            raise ValueError("oversized staged record")
        try:
            raw_pending = pending.read_text(encoding="utf-8")
        except FileNotFoundError:
            # Explicit discard can win this read, never a missing active config.
            return limit
        value = strict_json_loads(raw_pending)
        if (
            not isinstance(value, dict)
            or type(value.get("schema")) is not int
            or value["schema"] != 1
            or any(
                not isinstance(value.get(key), str)
                for key in (
                    "base_revision",
                    "candidate_revision",
                    "candidate_text",
                    "key",
                    "value",
                    "created_at",
                )
            )
            or any(
                not re.fullmatch(r"[a-f0-9]{64}", value[key])
                for key in ("base_revision", "candidate_revision")
            )
            or type(value.get("restart_required")) is not bool
            or len(value["candidate_text"].encode("utf-8")) > 1048576
            or sha256(value["candidate_text"].encode("utf-8")).hexdigest()
            != value["candidate_revision"]
            or datetime.fromisoformat(value["created_at"]).utcoffset() is None
        ):
            raise ValueError("invalid staged evidence")
        revision = sha256(config.source_path.read_bytes()).hexdigest()
        if revision == value["candidate_revision"]:
            return limit
        if revision != value["base_revision"]:
            raise ValueError("staged base changed")
        proposed = (
            tomllib.loads(value["candidate_text"]).get("polling", {}).get("max_concurrent_runs", 1)
        )
        if type(proposed) is not int or proposed < 1:
            raise ValueError("invalid staged limit")
        return min(limit, proposed)
    except (OSError, ValueError, TypeError, AttributeError, OverflowError, RecursionError) as exc:
        raise StateError(
            "invalid staged project capacity; discard or delete "
            + str(pending)
            + " after inspecting active settings"
        ) from exc


# END OF FILE
