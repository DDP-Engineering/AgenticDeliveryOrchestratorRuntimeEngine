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
@file    test_automatic_processes.py
@brief   Offline background command and inherited pager contracts.
@details Injects subprocesses; never runs Git, executors or active project jobs.
"""

# IMPORTS
import os
import subprocess
import sys
from types import SimpleNamespace

from adore.config import branch_naming_preview
from adore.util import run_command
import pytest

# PUBLIC API / TESTS


@pytest.mark.parametrize("system", ["win32", "linux"])
@pytest.mark.parametrize("source", [None, {}, {"HOME": "selected", "PATH": "tools",
                                            "git_pager": "less", "PAGER": "more"}])
def test_automatic_runner_background_environment(monkeypatch, system, source):
    """@brief Child policy overrides pagers without mutating or widening environments."""
    monkeypatch.setenv("GIT_PAGER", "interactive-pager")
    monkeypatch.setenv("AMBIENT_ONLY", "must-not-leak")
    monkeypatch.setattr("adore.util.sys.platform", system)
    before = dict(source) if source is not None else None
    ambient = dict(os.environ)
    calls = []

    def launch(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=7, stdout=b"diff\r\n", stderr=b"failure")

    monkeypatch.setattr("adore.util.subprocess.run", launch)
    result = run_command(["git", "diff", "--", "path with spaces"], env=source, timeout=9)
    argv, options = calls[0]
    assert argv == ["git", "diff", "--", "path with spaces"]
    assert options["env"]["GIT_PAGER"] == options["env"]["PAGER"] == "cat"
    assert "git_pager" not in options["env"]
    assert options["stdin"] == subprocess.DEVNULL
    assert options.get("creationflags", 0) == (0x08000000 if system == "win32" else 0)
    if source is not None:
        assert "AMBIENT_ONLY" not in options["env"]
        assert source == before
    else:
        assert options["env"]["AMBIENT_ONLY"] == "must-not-leak"
    if source:
        assert options["env"]["HOME"] == "selected"
        assert options["env"]["PATH"] == "tools"
    assert dict(os.environ) == ambient
    assert result.exit_code == 7 and not result.timed_out
    assert result.stdout == "diff\r\n" and result.stderr == "failure"


@pytest.mark.parametrize("failure,code,timed_out", [
    (FileNotFoundError("missing"), 127, False),
    (PermissionError("denied"), 126, False),
    (subprocess.TimeoutExpired("git", 1, output=b"partial"), 124, True),
])
def test_automatic_runner_keeps_failed_spawn_outcomes(monkeypatch, failure, code, timed_out):
    """@brief Background launch options retain typed OS/timeout failures."""
    def launch(*args, **kwargs):
        assert kwargs["env"]["GIT_PAGER"] == "cat"
        raise failure

    monkeypatch.setattr("adore.util.subprocess.run", launch)
    result = run_command(["git", "diff"], timeout=1)
    assert result.exit_code == code and result.timed_out is timed_out
    if timed_out:
        assert result.stdout == "partial"


@pytest.mark.parametrize("system", ["win32", "linux"])
def test_branch_preview_background_regex_keeps_json_stdin(monkeypatch, system):
    """@brief Regex subprocess hides Windows consoles while retaining bounded JSON input."""
    monkeypatch.setattr("adore.util.sys.platform", system)

    def launch(argv, **kwargs):
        assert kwargs["env"]["GIT_PAGER"] == "cat"
        assert kwargs.get("creationflags", 0) == (0x08000000 if system == "win32" else 0)
        assert "input" in kwargs and "stdin" not in kwargs and kwargs["timeout"] == 1
        return SimpleNamespace(returncode=0, stdout="true")

    monkeypatch.setattr("adore.config.subprocess.run", launch)
    result = branch_naming_preview("adore/{run_id}", "^adore/", "project")
    assert result["rule_matches"] is True


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 console allocation contract")
def test_windows_automatic_child_has_no_console():
    """@brief A real bounded Python child reports no Windows console handle."""
    result = run_command([
        sys.executable, "-I", "-c",
        "import ctypes,os; print(ctypes.windll.kernel32.GetConsoleWindow()); "
        "print(os.environ['GIT_PAGER']); print(os.environ['PAGER'])",
    ], timeout=10)
    assert result.ok and result.stdout.splitlines() == ["0", "cat", "cat"]


# END OF FILE
