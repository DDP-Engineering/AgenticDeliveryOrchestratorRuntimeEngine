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
@file metrics.py
@brief Statistics capture and query for ADOR (standard-library only).
@details Appends a run-summary record to a SQLite database at each run's
         terminal state and mirrors it to JSONL. Access is CLI-first with an
         optional static HTML report. No Prometheus/exporter.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.1.0
"""

from __future__ import annotations

# IMPORTS
from dataclasses import dataclass

# DATA MODELS / TYPEDEFINITIONS


@dataclass
class RunSummary:
    """
    @brief   One completed run's metrics record.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    run_id: str
    ticket_iid: int
    outcome: str
    wall_clock_seconds: int = 0
    tokens_in: int = 0
    tokens_out: int = 0


# PUBLIC API


def record_summary(db_path: str, summary: RunSummary) -> None:
    """
    @brief      Append a run summary to the SQLite metrics database.
    @param[in]  db_path Path to the SQLite database file.
    @param[in]  summary The run summary to persist.
    @todo       Create schema on first use and insert the row (sqlite3).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    raise NotImplementedError


# END OF FILE
