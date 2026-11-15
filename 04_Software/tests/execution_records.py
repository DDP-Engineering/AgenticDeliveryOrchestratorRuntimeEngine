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
@file    execution_records.py
@brief   Current execution evidence for isolated persisted-state test fixtures.
@details Builds a fresh, complete execution record through the public plan API.
         It neither repairs stored state nor changes production defaults.
"""

# IMPORTS
from adore.config import Config
from adore.preparation import resolve_plan

# PUBLIC API


def execution_record() -> dict:
    """@brief Return independent current-format container execution evidence.
    @return Complete record without preparation or allocated resources.
    """
    return {
        "plan": resolve_plan(Config()), "resource": {}, "status": "not-required",
        "attempts": 0, "steps": [], "history": [], "reprepare": False,
    }


# END OF FILE
