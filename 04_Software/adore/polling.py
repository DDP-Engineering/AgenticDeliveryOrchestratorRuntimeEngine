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
@file       polling.py
@brief      Shared automatic polling cadence for CLI and web.
@details    In-memory error multiplier is owned by each scheduler/project.
            Delays start after a round finishes; quiet rounds retain backoff.
"""

from __future__ import annotations

# IMPORTS
import random

from adore.config import PollingConfig


# PUBLIC API
class PollCadence:
    """@brief Retain bounded error backoff between automatic polling rounds."""

    def __init__(self) -> None:
        self.multiplier = 1

    def next_delay(self, config: PollingConfig, *, failed: bool | None) -> float:
        """
        @brief      Calculate the wait after a completed or quiet round.
        @param[in]  config Validated positive interval/nonnegative jitter settings.
        @param[in]  failed False on success, True on error, None on quiet skip.
        @return     Interval times multiplier plus uniform nonnegative jitter.
        @exception  ValueError If cadence values have invalid types or bounds.
        @note       Disabling backoff resets the multiplier immediately.
        """
        self.validate(config)
        if failed is not None and type(failed) is not bool:
            raise ValueError("invalid polling outcome")
        if not config.poll_backoff or failed is False:
            self.multiplier = 1
        elif failed is True:
            self.multiplier = min(self.multiplier * 2, 8)
        return (config.poll_interval_seconds * self.multiplier
                + random.uniform(0, config.poll_jitter_seconds))

    @staticmethod
    def validate(config: PollingConfig) -> None:
        """
        @brief      Validate cadence before any scheduled external invocation.
        @param[in]  config Parsed polling settings.
        @exception  ValueError If types or bounds are invalid.
        """
        if (type(config.poll_interval_seconds) is not int or config.poll_interval_seconds <= 0
                or type(config.poll_jitter_seconds) is not int or config.poll_jitter_seconds < 0
                or type(config.poll_backoff) is not bool):
            raise ValueError("invalid polling cadence")

# END OF FILE
