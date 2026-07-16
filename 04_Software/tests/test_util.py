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
@file test_util.py
@brief Tests for the shared low-level helpers (runner, durations, timestamps).
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.1.1
"""

from __future__ import annotations

# IMPORTS
import re
import sys

from adore.util import (
    in_quiet_hours,
    iso_to_datetime,
    load_env_file,
    parse_duration,
    run_command,
    utc_now_iso,
)
import pytest

# PUBLIC API / TESTS


def test_parse_duration_units() -> None:
    """
    @brief   Durations parse for every documented unit and bare numbers.
    @version 0.1.0
    """
    assert parse_duration("90s") == 90
    assert parse_duration("30m") == 1800
    assert parse_duration("24h") == 86400
    assert parse_duration("2d") == 172800
    assert parse_duration("60") == 60
    assert parse_duration(60) == 60
    assert parse_duration("24H") == 86400


def test_parse_duration_rejects_garbage() -> None:
    """
    @brief   Invalid durations raise ValueError.
    @version 0.1.0
    """
    for bad in ("", "h", "12x", "-5s", "1.5h"):
        with pytest.raises(ValueError):
            parse_duration(bad)


def test_run_command_captures_output() -> None:
    """
    @brief   The runner captures stdout and the exit code without a shell.
    @version 0.1.1
    """
    result = run_command([sys.executable, "-c", "print('hello adore')"])
    assert result.ok
    assert result.exit_code == 0
    assert "hello adore" in result.stdout


def test_run_command_missing_binary_reports_127() -> None:
    """
    @brief   A missing executable becomes exit code 127, never an exception.
    @version 0.1.1
    """
    result = run_command(["definitely-not-a-real-binary-adore"])
    assert not result.ok
    assert result.exit_code == 127


def test_utc_now_iso_shape() -> None:
    """
    @brief   Timestamps are compact UTC ISO-8601 with a Z suffix.
    @version 0.1.0
    """
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", utc_now_iso())


def test_run_command_timeout_reports_124() -> None:
    """
    @brief   A hung command becomes exit code 124, never a raised exception.
    @version 0.1.0
    """
    result = run_command([sys.executable, "-c", "import time; time.sleep(30)"], timeout=1)
    assert not result.ok
    assert result.exit_code == 124


def test_iso_to_datetime_round_trip_and_garbage() -> None:
    """
    @brief   Z-form timestamps parse to aware UTC; garbage yields None.
    @version 0.1.0
    """
    parsed = iso_to_datetime("2026-07-03T10:00:00Z")
    assert parsed is not None and parsed.utcoffset().total_seconds() == 0
    assert iso_to_datetime("") is None
    assert iso_to_datetime("not-a-date") is None


def test_in_quiet_hours_windows() -> None:
    """
    @brief   Plain and midnight-crossing windows match; malformed windows are
             ignored.
    @version 0.1.0
    """
    from datetime import datetime

    night = datetime(2026, 7, 3, 23, 30)
    morning = datetime(2026, 7, 3, 5, 0)
    noon = datetime(2026, 7, 3, 12, 0)
    windows = ["22:00-06:00"]
    assert in_quiet_hours(windows, night)
    assert in_quiet_hours(windows, morning)
    assert not in_quiet_hours(windows, noon)
    assert not in_quiet_hours(["garbage", ""], night)
    assert in_quiet_hours(["11:00-13:00"], noon)


def test_load_env_file(tmp_path) -> None:
    """
    @brief   KEY=VALUE lines load; comments/blank/quotes handled; a missing
             file is empty, not an error.
    @version 0.1.0
    """
    env = tmp_path / ".env"
    env.write_text(
        "# comment\n\nOPENAI_API_KEY=sk-test\nQUOTED='v a l'\nBROKEN\n",
        encoding="utf-8",
    )
    values = load_env_file(env)
    assert values == {"OPENAI_API_KEY": "sk-test", "QUOTED": "v a l"}
    assert load_env_file(tmp_path / "missing.env") == {}


# END OF FILE
