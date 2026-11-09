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
@file usage_events.py
@brief Usage journal records in the shape the current orchestrator writes.
"""

from __future__ import annotations

from typing import Any


def versioned_usage(run_id: str, attempt: int, **fields: Any) -> dict[str, Any]:
    """
    @brief      Build one usage record with its launch identity and every field.
    @details    A nonzero cost counts as reported unless the caller says
                otherwise; a zero cost leaves pricing to the price table.
    @param[in]  run_id Run owning the record.
    @param[in]  attempt Launch attempt; the event ID is `<run_id>:<attempt>`.
    @param[in]  fields Values that replace the defaults (tokens, cost, ts, ...).
    @return     Keyword arguments for `StateStore.journal(run_id, "usage", ...)`.
    """
    event: dict[str, Any] = {
        "event_id": f"{run_id}:{attempt}", "attempt": attempt, "context": "build",
        "executor": "codex", "model": "example", "review_round": 0,
        "tokens_in": 0, "tokens_out": 0, "cost_usd": 0, "cost_reported": False,
    }
    if fields.get("cost_usd") and "cost_reported" not in fields:
        event["cost_reported"] = True
    event.update(fields)
    return event
