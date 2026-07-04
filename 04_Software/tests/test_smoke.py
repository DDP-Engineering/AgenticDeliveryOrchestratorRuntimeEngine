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
@file test_smoke.py
@brief Smoke tests: package version, executor factory, and the CLI end-to-end.
@details Drives `ador` through main() against a real config file in a tmp dir,
         so config loading, validation, state store, and command wiring are
         exercised together.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.1.1
"""

from __future__ import annotations

# IMPORTS
from pathlib import Path

from ador import __version__
from ador.cli import EXIT_ERROR, EXIT_NOT_IMPLEMENTED, EXIT_OK, main
from ador.executor.launcher import OpencodeExecutor, build_executor
import pytest

# CONSTANTS

VALID_CONFIG = """
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../cockpit-gcp"

[executor.opencode]
command = "opencode run --dir {worktree} -m {model} {prompt}"
model   = "openai/gpt-5.4-fast"

[delivery]
reviewers = ["dan.pasare"]
"""

# HELPER FUNCTIONS


def _config_file(tmp_path: Path, text: str = VALID_CONFIG) -> str:
    """
    @brief      Write a config.toml with a tmp-scoped state root.
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  text TOML content.
    @return     The config path as a string for the CLI.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    store_root = (tmp_path / ".ador").as_posix()
    path = tmp_path / "config.toml"
    path.write_text(text + f'\n[state]\nstore_root = "{store_root}"\n', encoding="utf-8")
    return str(path)


# PUBLIC API / TESTS


def test_version_present() -> None:
    """
    @brief   The package exposes a non-empty version string.
    @version 0.1.0
    """
    assert isinstance(__version__, str)
    assert __version__


def test_build_executor_opencode() -> None:
    """
    @brief   The factory returns an opencode executor and rejects unknown kinds.
    @version 0.1.0
    """
    executor = build_executor("opencode", "opencode run {prompt}", "openai/gpt-5.4-fast")
    assert isinstance(executor, OpencodeExecutor)
    with pytest.raises(ValueError):
        build_executor("nope", "", "")


def test_cli_config_validate_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    @brief   `ador config validate` passes on a valid file.
    @version 0.1.0
    """
    assert main(["-c", _config_file(tmp_path), "config", "validate"]) == EXIT_OK
    assert "OK" in capsys.readouterr().out


def test_cli_config_validate_reports_issues(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   `ador config validate` lists issues and exits 1.
    @version 0.1.0
    """
    bad = VALID_CONFIG.replace('kind = "gitlab"', 'kind = "bitbucket"')
    assert main(["-c", _config_file(tmp_path, bad), "config", "validate"]) == EXIT_ERROR
    assert "[platform] kind" in capsys.readouterr().out


def test_cli_missing_config_is_a_clean_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   A missing config file prints a hint instead of a traceback.
    @version 0.1.0
    """
    assert main(["-c", str(tmp_path / "nope.toml"), "status"]) == EXIT_ERROR
    assert "not found" in capsys.readouterr().out


def test_cli_status_pause_resume_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   status/pause/resume/runs work together against the state store.
    @version 0.1.0
    """
    config = _config_file(tmp_path)
    assert main(["-c", config, "status"]) == EXIT_OK
    assert "paused : no" in capsys.readouterr().out
    assert main(["-c", config, "pause"]) == EXIT_OK
    capsys.readouterr()
    assert main(["-c", config, "status"]) == EXIT_OK
    assert "paused : yes" in capsys.readouterr().out
    assert main(["-c", config, "resume"]) == EXIT_OK
    capsys.readouterr()
    assert main(["-c", config, "runs"]) == EXIT_OK
    assert "no runs" in capsys.readouterr().out


def test_cli_reset_guardrail_and_cleanup_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   reset refuses without --force (design 8c), fails cleanly on an
             unknown run with --force, and cleanup prints a JSON report.
    @version 0.2.0
    """
    config = _config_file(tmp_path)
    assert main(["-c", config, "reset", "x", "--to", "intake"]) == EXIT_ERROR
    assert "--force" in capsys.readouterr().out
    assert main(["-c", config, "reset", "x", "--to", "intake",
                 "--force"]) == EXIT_ERROR
    assert "cannot reset" in capsys.readouterr().out
    assert main(["-c", config, "cleanup"]) == EXIT_OK
    assert '"lock_cleared": false' in capsys.readouterr().out


def test_cli_config_set_still_exits_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   The one remaining stub (`config set`) exits 2 with a message,
             never a traceback.
    @version 0.1.0
    """
    config = _config_file(tmp_path)
    assert main(["-c", config, "config", "set", "a", "b"]) == EXIT_NOT_IMPLEMENTED
    assert "not implemented" in capsys.readouterr().out


def test_cli_stats_and_export_work_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   stats/export on an empty store answer cleanly (exit 0), and
             report on an unknown run errors cleanly.
    @version 0.1.0
    """
    config = _config_file(tmp_path)
    assert main(["-c", config, "stats"]) == EXIT_OK
    assert "no recorded runs" in capsys.readouterr().out
    assert main(["-c", config, "export", "--csv"]) == EXIT_OK
    assert capsys.readouterr().out.startswith("run_id,")
    assert main(["-c", config, "report", "nope"]) == EXIT_ERROR


def test_cli_run_ops_on_unknown_run_fail_cleanly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   retry/cancel/logs/delete on an unknown run print a clean error
             (no traceback, no network) and exit 1; delete additionally
             requires --force.
    @version 0.1.0
    """
    config = _config_file(tmp_path)
    assert main(["-c", config, "cancel", "nope"]) == EXIT_ERROR
    assert main(["-c", config, "retry", "nope"]) == EXIT_ERROR
    assert main(["-c", config, "logs", "nope"]) == EXIT_ERROR
    assert main(["-c", config, "delete", "nope"]) == EXIT_ERROR
    out = capsys.readouterr().out
    assert "no such run" in out or "cannot retry" in out


def test_cli_invalid_toml_is_a_clean_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   A syntactically broken config prints a readable error, exit 1.
    @version 0.1.0
    """
    path = tmp_path / "config.toml"
    path.write_text("[platform\nbroken =", encoding="utf-8")
    assert main(["-c", str(path), "status"]) == EXIT_ERROR
    assert "not valid TOML" in capsys.readouterr().out


def test_cli_surfaces_corrupt_runs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    @brief   A run with unreadable state stays visible in `runs` and `status`
             instead of disappearing or crashing the command.
    @version 0.1.0
    """
    config = _config_file(tmp_path)
    run_dir = tmp_path / ".ador" / "runs" / "broken-run"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("garbage", encoding="utf-8")
    assert main(["-c", config, "runs"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "broken-run" in out
    assert "CORRUPT" in out
    assert main(["-c", config, "status"]) == EXIT_OK
    assert "CORRUPT" in capsys.readouterr().out


# END OF FILE
