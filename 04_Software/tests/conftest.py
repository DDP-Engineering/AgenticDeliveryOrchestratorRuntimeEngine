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
@brief Shared pytest fixtures for the ADOR test suite.
@author Eng. Dan Dumitru Pasare
@date 2026-07-05
@version 0.1.0
"""

from __future__ import annotations

# IMPORTS
from pathlib import Path

import pytest

# PUBLIC API / FIXTURES


@pytest.fixture
def ador_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    @brief      An isolated ADOR config home wired into the environment.
    @details    Sets ADOR_HOME so any `ProfileStore()` built inside `main()` /
                the CLI resolves to a throwaway per-test directory, never the
                developer's real home.
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  monkeypatch Fixture used to set ADOR_HOME.
    @return     The home directory path.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    home = tmp_path / "ador-home"
    monkeypatch.setenv("ADOR_HOME", str(home))
    return home


# END OF FILE
