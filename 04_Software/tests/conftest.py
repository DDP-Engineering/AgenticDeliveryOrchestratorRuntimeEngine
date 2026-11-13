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
import errno
from pathlib import Path

import pytest

# PUBLIC API / FIXTURES


@pytest.fixture
def symlink_support(tmp_path: Path) -> None:
    """@brief Require real link support only for tests exercising filesystem links.
    @param[in] tmp_path Isolated location used for a capability probe.
    @note Unsupported filesystems or accounts skip explicitly; other IO errors fail.
    """
    source, link = tmp_path / "symlink-probe-source", tmp_path / "symlink-probe-link"
    source.write_bytes(b"probe")
    try:
        link.symlink_to(source)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314 or exc.errno in {
            errno.EPERM, errno.EACCES, errno.ENOSYS, errno.EOPNOTSUPP,
        }:
            pytest.skip("The test account/filesystem cannot create symbolic links")
        raise
    finally:
        if link.is_symlink():
            link.unlink()
        source.unlink()


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
