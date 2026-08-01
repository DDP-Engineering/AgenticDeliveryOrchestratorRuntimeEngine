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
@details Drives `adore` through main() against a real config file in a tmp dir,
         so config loading, validation, state store, and command wiring are
         exercised together.
"""

from __future__ import annotations

# IMPORTS
from pathlib import Path

from adore import __version__
from adore.cli import EXIT_ERROR, EXIT_OK, main
from adore.executor.launcher import OpencodeExecutor, build_executor
from adore.process_log import ProcessLogger, process_log_path
import pytest

# CONSTANTS

VALID_CONFIG = """
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../runtime-project"
root      = "__WORKTREE_ROOT__"

[executor.opencode]
command = "opencode run --dir {worktree} -m {model} {prompt}"
model   = "openai/gpt-5.4-fast"

[delivery]
reviewers = ["dan.pasare"]
"""

# HELPER FUNCTIONS


def _config_file(tmp_path: Path, text: str = VALID_CONFIG) -> str:
    """
    @brief      Write a config.toml with a tmp-scoped state and worktree root.
    @details    The worktree root is tmp-scoped so operator commands that
                sweep it (`adore cleanup`) never touch the real worktrees/.
    @param[in]  tmp_path pytest tmp dir.
    @param[in]  text TOML content.
    @return     The config path as a string for the CLI.
    """
    store_root = (tmp_path / ".adore").as_posix()
    worktree_root = (tmp_path / "worktrees").as_posix()
    text = text.replace("__WORKTREE_ROOT__", worktree_root)
    path = tmp_path / "config.toml"
    path.write_text(text + f'\n[state]\nstore_root = "{store_root}"\n', encoding="utf-8")
    return str(path)


# PUBLIC API / TESTS


def test_version_present() -> None:
    """
    @brief   The package exposes a non-empty version string.
    """
    assert isinstance(__version__, str)
    assert __version__


def test_build_executor_opencode() -> None:
    """
    @brief   The factory returns an opencode executor and rejects unknown kinds.
    """
    executor = build_executor("opencode", "opencode run {prompt}", "openai/gpt-5.4-fast")
    assert isinstance(executor, OpencodeExecutor)
    with pytest.raises(ValueError):
        build_executor("nope", "", "")


def test_cli_config_validate_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    @brief   `adore config validate` passes on a valid file.
    """
    assert main(["-c", _config_file(tmp_path), "config", "validate"]) == EXIT_OK
    assert "OK" in capsys.readouterr().out


def test_cli_config_validate_reports_issues(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   `adore config validate` lists issues and exits 1.
    """
    bad = VALID_CONFIG.replace('kind = "gitlab"', 'kind = "bitbucket"')
    assert main(["-c", _config_file(tmp_path, bad), "config", "validate"]) == EXIT_ERROR
    assert "[platform] kind" in capsys.readouterr().out


def test_cli_missing_config_is_a_clean_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   A missing config file prints a hint instead of a traceback.
    """
    assert main(["-c", str(tmp_path / "nope.toml"), "status"]) == EXIT_ERROR
    assert "not found" in capsys.readouterr().out


def test_cli_status_pause_resume_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   status/pause/resume/runs work together against the state store.
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
    """
    config = _config_file(tmp_path)
    assert main(["-c", config, "reset", "x", "--to", "intake"]) == EXIT_ERROR
    assert "--force" in capsys.readouterr().out
    assert main(["-c", config, "reset", "x", "--to", "intake",
                 "--force"]) == EXIT_ERROR
    assert "cannot reset" in capsys.readouterr().out
    assert main(["-c", config, "cleanup"]) == EXIT_OK
    assert '"lock_cleared": false' in capsys.readouterr().out


def test_cli_config_set_updates_existing_key_and_preserves_comments(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   `config set` replaces an existing scalar in place, keeps comments
             and other keys, and infers the value type (here: int).
    """
    text = VALID_CONFIG + "\n[budgets]\nmax_iterations = 20  # a comment\n"
    config = _config_file(tmp_path, text)
    assert main(["-c", config, "config", "set", "budgets.max_iterations", "12"]) == EXIT_OK
    body = Path(config).read_text(encoding="utf-8")
    assert "max_iterations = 12" in body
    assert "# a comment" in body          # the comment line is preserved
    assert 'repo = "group/project"' in body  # untouched keys survive
    assert main(["-c", config, "config", "validate"]) == EXIT_OK


def test_cli_config_set_adds_missing_section(
    tmp_path: Path,
) -> None:
    """
    @brief   Setting a key in an absent section appends the table; the result
             still validates.
    """
    config = _config_file(tmp_path)  # VALID_CONFIG has no [budgets]
    assert main(["-c", config, "config", "set", "budgets.max_files_touched", "25"]) == EXIT_OK
    body = Path(config).read_text(encoding="utf-8")
    assert "[budgets]" in body and "max_files_touched = 25" in body
    assert main(["-c", config, "config", "validate"]) == EXIT_OK


def test_cli_config_set_refuses_when_result_is_invalid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   An edit that would make the config invalid is refused and the file
             is left byte-for-byte unchanged (validate before write).
    """
    config = _config_file(tmp_path)
    before = Path(config).read_text(encoding="utf-8")
    assert main(["-c", config, "config", "set", "budgets.max_iterations", "0"]) == EXIT_ERROR
    out = capsys.readouterr().out
    assert "refusing to write" in out and "max_iterations" in out
    assert Path(config).read_text(encoding="utf-8") == before  # untouched


def test_cli_config_set_rejects_secret_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   A secret-looking key is refused and the operator is pointed at
             .env; config.toml only holds secret NAMES, never values.
    """
    config = _config_file(tmp_path)
    assert main(["-c", config, "config", "set", "platform.api_token", "s3cr3t"]) == EXIT_ERROR
    assert ".env" in capsys.readouterr().out


def test_cli_config_set_rejects_bad_key_and_missing_value(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   A key without a section, and a missing value, both fail closed with
             a usage/format message rather than a traceback.
    """
    config = _config_file(tmp_path)
    assert main(["-c", config, "config", "set", "toplevel", "x"]) == EXIT_ERROR
    assert "section" in capsys.readouterr().out
    assert main(["-c", config, "config", "set", "budgets.max_iterations"]) == EXIT_ERROR
    assert "usage" in capsys.readouterr().out


def test_cli_stats_and_export_work_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   stats/export on an empty store answer cleanly (exit 0), and
             report on an unknown run errors cleanly.
    """
    config = _config_file(tmp_path)
    assert main(["-c", config, "stats"]) == EXIT_OK
    assert "no recorded runs" in capsys.readouterr().out
    assert main(["-c", config, "export", "--csv"]) == EXIT_OK
    assert capsys.readouterr().out.startswith("run_id,")
    assert main(["-c", config, "report", "nope"]) == EXIT_ERROR


def test_cli_run_once_writes_process_log(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief   `adore run --once` preserves stdout and appends the same run-owned
             lines to `<store_root>/adore.log`.
    """
    config = _config_file(tmp_path)

    class FakeEngine:
        """
        @brief   Minimal engine for run-command CLI smoke coverage.
        """

        def __init__(self) -> None:
            """
            @brief   Initialize with the same log slot Orchestrator exposes.
            """
            self.log = print

        def poll_once(self, *, dry_run: bool = False) -> dict:
            """
            @brief      Emit one engine line and return a summary.
            @param[in]  dry_run Whether the CLI requested dry-run.
            @return     Poll summary.
            """
            self.log("engine line")
            return {"picked": None, "dry_run": dry_run}

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", lambda _config: FakeEngine())

    assert main(["-c", config, "run", "--once"]) == EXIT_OK

    out = capsys.readouterr().out
    assert "engine line" in out
    assert '"picked": null' in out
    log_text = process_log_path(tmp_path / ".adore").read_text(encoding="utf-8")
    assert "engine line" in log_text
    assert '"picked": null' in log_text


def test_process_log_rotates(tmp_path: Path) -> None:
    """
    @brief   The ADORE process log keeps a bounded current file and numbered
             backups with the newest backup at `.1`.
    """
    path = tmp_path / "adore.log"
    logger = ProcessLogger(path, max_bytes=50, backups=2)

    logger.append("first payload")
    logger.append("second payload")
    logger.append("third payload")

    assert "third payload" in path.read_text(encoding="utf-8")
    assert "second payload" in (tmp_path / "adore.log.1").read_text(encoding="utf-8")
    assert "first payload" in (tmp_path / "adore.log.2").read_text(encoding="utf-8")
    assert not (tmp_path / "adore.log.3").exists()


def test_cli_run_ops_on_unknown_run_fail_cleanly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   retry/cancel/logs/delete on an unknown run print a clean error
             (no traceback, no network) and exit 1; delete additionally
             requires --force.
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
    """
    path = tmp_path / "config.toml"
    path.write_text("[platform\nbroken =", encoding="utf-8")
    assert main(["-c", str(path), "status"]) == EXIT_ERROR
    assert "not valid TOML" in capsys.readouterr().out


def test_cli_surfaces_corrupt_runs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    @brief   A run with unreadable state stays visible in `runs` and `status`
             instead of disappearing or crashing the command.
    """
    config = _config_file(tmp_path)
    run_dir = tmp_path / ".adore" / "runs" / "broken-run"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("garbage", encoding="utf-8")
    assert main(["-c", config, "runs"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "broken-run" in out
    assert "CORRUPT" in out
    assert main(["-c", config, "status"]) == EXIT_OK
    assert "CORRUPT" in capsys.readouterr().out


# PUBLIC API / TESTS - `adore init` through main()


def _answers_file(tmp_path: Path) -> str:
    """
    @brief      Write a valid non-interactive answers file + a clone dir.
    @param[in]  tmp_path pytest tmp dir.
    @return     The answers file path.
    """
    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True)
    answers = tmp_path / "answers.toml"
    answers.write_text(
        f'kind = "gitlab"\nhosting = "public"\nvisibility = "private"\n'
        f'repo = "grp/proj"\nrepo_path = "{clone.as_posix()}"\n'
        f'has_push_rule = "no"\nruntime = "docker"\nmodel = "openai/gpt-5.5"\n'
        f'auth_mode = "api-key"\nreviewers = "dan.pasare"\n'
        f'budgets_choice = "recommended"\npolling_mode = "once"\n'
        f'state_location = "profile"\nconfirm = "yes"\n',
        encoding="utf-8",
    )
    return str(answers)


def test_cli_init_via_main_writes_profile(
    adore_home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   `adore init <name> --answers FILE` creates a profile through the CLI
             wiring; `profile list` then shows it.
    """
    assert main(["init", "smoketest", "--answers", _answers_file(tmp_path)]) == EXIT_OK
    capsys.readouterr()
    assert main(["profile", "list"]) == EXIT_OK
    assert "smoketest" in capsys.readouterr().out


def test_cli_init_answers_file_errors(
    adore_home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   A missing or invalid --answers file is a clean error (exit 1).
    """
    assert main(["init", "p", "--answers", str(tmp_path / "nope.toml")]) == EXIT_ERROR
    assert "not found" in capsys.readouterr().out
    bad = tmp_path / "bad.toml"
    bad.write_text("this = = broken", encoding="utf-8")
    assert main(["init", "p", "--answers", str(bad)]) == EXIT_ERROR
    assert "not valid TOML" in capsys.readouterr().out


def test_cli_init_wizard_error_exits_one(
    adore_home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    @brief   A wizard failure (existing profile without --force) surfaces as a
             clean `init failed:` error, exit 1.
    """
    answers = _answers_file(tmp_path)
    assert main(["init", "dup", "--answers", answers]) == EXIT_OK
    capsys.readouterr()
    assert main(["init", "dup", "--answers", answers]) == EXIT_ERROR
    assert "init failed" in capsys.readouterr().out


# END OF FILE
