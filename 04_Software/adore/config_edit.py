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
@file config_edit.py
@brief Coordinate ADORE CLI and web configuration writes on one host.
@details Uses the existing crash-reclaiming local lock convention. This guards
         ADORE-mediated edits, not direct host file modification.
"""

from __future__ import annotations

from collections.abc import Iterator

# IMPORTS
from contextlib import contextmanager
from pathlib import Path

from adore.state import StateStore


# DATA MODELS / TYPEDEFINITIONS
class ConfigEditLockedError(RuntimeError):
    """@brief Another ADORE process owns the configuration edit lock."""


# PUBLIC API
@contextmanager
def config_edit_lock(path: Path) -> Iterator[None]:
    """
    @brief Hold an exclusive edit lock for one configuration directory.
    @param[in] path Config file being edited.
    @exception ConfigEditLockedError When another local editor owns the lock.
    """
    guard = StateStore(path.parent, "adore-config")
    if not guard.acquire_lock():
        raise ConfigEditLockedError("another ADORE config edit holds the lock")
    try:
        yield
    finally:
        guard.release_lock()


# END OF FILE
