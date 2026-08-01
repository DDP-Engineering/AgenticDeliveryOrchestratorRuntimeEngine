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
@file conftest.py
@brief Shared pytest fixtures for the ADORE test suite.
"""

from __future__ import annotations

# IMPORTS
from pathlib import Path

import pytest

# PUBLIC API / FIXTURES


@pytest.fixture
def adore_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    @brief      An isolated ADORE config home wired into the environment.
    @details    Sets ADORE_HOME so any `ProfileStore()` built inside `main()` /
                the CLI resolves to a throwaway per-test directory, never the
                developer's real home.
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  monkeypatch Fixture used to set ADORE_HOME.
    @return     The home directory path.
    """
    home = tmp_path / "adore-home"
    monkeypatch.setenv("ADORE_HOME", str(home))
    return home


# END OF FILE
