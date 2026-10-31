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
import os
from pathlib import Path

from adore import __version__, metrics
from adore.cli import EXIT_ERROR, EXIT_OK, main
from adore.config import load_config
from adore.executor.launcher import OpencodeExecutor, build_executor
from adore.forge import ForgeError
from adore.orchestrator import LockHeldError
from adore.process_log import ProcessLogger, process_log_path
from adore.state import RunState, StateStore
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


class FakeMutationEngine:
    """@brief Record CLI mutation calls without touching external systems."""

    def __init__(self, store=None) -> None:
        self.calls: list[tuple] = []
        self.store = store

    def retry(self, run_id: str) -> bool:
        self.calls.append(("retry", run_id))
        if self.store is not None:
            run = self.store.load(run_id)
            run.lifecycle = "working"
            run.outcome = ""
            self.store.save(run)
        return True

    def cancel(self, run_id: str, *, outcome: str = "cancelled") -> bool:
        self.calls.append(("cancel", run_id, outcome))
        return True

    def reset(self, run_id: str, stage: str) -> bool:
        self.calls.append(("reset", run_id, stage))
        return True


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


def test_cli_run_once_reports_an_unexpected_fault_without_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief   `run --loop` survives an unexpected fault and keeps polling, so a
             single pass must not be noisier for the same cause. `--once` is
             what cron and Task Scheduler call, where a traceback is just a
             nonzero exit with an ugly log.
    """
    from adore import cli as cli_module

    def boom(*args, **kwargs):
        raise KeyError("resume")

    monkeypatch.setattr(cli_module.Orchestrator, "poll_once", boom)
    config = _config_file(tmp_path)
    assert main(["-c", config, "run", "--once"]) == EXIT_ERROR
    assert "error:" in capsys.readouterr().out


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


@pytest.mark.parametrize(("target", "code"), [
    ("publishing", EXIT_OK), ("validate", EXIT_OK), ("deliver", EXIT_ERROR), ("done", EXIT_ERROR),
])
def test_cli_reset_accepts_only_current_stages_and_publishing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], target: str, code: int,
) -> None:
    """
    @brief   `reset --to` names a conducted AEGIS stage or publishing.
    @details AEGIS 0.15.0 has no deliver stage and done is no reset target, so
             the CLI refuses both and the saved run keeps its pointer.
    """
    config_path = _config_file(tmp_path)
    config = load_config(config_path)
    store = StateStore(config.state.store_root, config.agent.slug)
    store.save(RunState(run_id="run-1", ticket_iid=1, stage="build", lifecycle="failed"))

    assert main(["-c", config_path, "reset", "run-1", "--to", target, "--force"]) == code

    saved = store.load("run-1")
    if code == EXIT_OK:
        assert saved.stage == target
    else:
        assert saved.stage == "build"
        assert "cannot reset run-1" in capsys.readouterr().out


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


def test_cli_report_and_rebuild_reject_conflicting_usage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """@brief CLI metrics fail with a typed message on versioned replay conflict."""
    config = _config_file(tmp_path)
    store = StateStore(tmp_path / ".adore")
    store.save(RunState(run_id="a-clean", ticket_iid=2, lifecycle="done"))
    store.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="done"))
    usage = {"event_id": "run-1:1", "attempt": 1, "context": "build",
             "executor": "codex", "model": "example", "review_round": 0,
             "tokens_in": 10, "tokens_out": 2, "cost_usd": 0.5,
             "cost_reported": True}
    store.journal("run-1", "usage", **usage)
    assert main(["-c", config, "report", "run-1"]) == EXIT_OK
    assert '"tokens_in": 10' in capsys.readouterr().out
    store.journal("run-1", "usage", **{**usage, "tokens_in": 11})
    assert main(["-c", config, "report", "run-1"]) == EXIT_ERROR
    assert "conflicting versioned usage" in capsys.readouterr().out
    assert main(["-c", config, "stats", "--rebuild"]) == EXIT_ERROR
    assert "conflicting versioned usage" in capsys.readouterr().out
    assert not Path(load_config(config).metrics.db_path).exists()


def test_cli_rebuild_replays_usage_idempotently_without_changing_run_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """@brief Historical rebuild upserts known evidence and preserves journals."""
    config = _config_file(tmp_path)
    state = StateStore(tmp_path / ".adore")
    state.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="done"))
    usage = {"event_id": "run-1:1", "attempt": 1, "context": "build",
             "executor": "codex", "model": "local/test", "review_round": 0,
             "tokens_in": 7, "tokens_out": 3, "cost_usd": 0,
             "cost_reported": False}
    state.journal("run-1", "usage", **usage)
    state.journal("run-1", "usage", **usage)
    before = {item.name: item.read_bytes() for item in state.run_dir("run-1").iterdir()
              if item.is_file()}
    db = load_config(config).metrics.db_path
    assert main(["-c", config, "stats", "--rebuild"]) == EXIT_OK
    first = metrics.load_summaries(db)
    assert len(first) == 1
    assert (first[0].tokens_in, first[0].tokens_out) == (7, 3)
    assert main(["-c", config, "stats", "--rebuild"]) == EXIT_OK
    assert metrics.load_summaries(db) == first
    assert {item.name: item.read_bytes() for item in state.run_dir("run-1").iterdir()
            if item.is_file()} == before
    assert "rebuilt 1 run" in capsys.readouterr().out


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

    monkeypatch.setattr(
        "adore.cli.Orchestrator.from_config", lambda _config, **_kwargs: FakeEngine()
    )

    assert main(["-c", config, "run", "--once"]) == EXIT_OK

    out = capsys.readouterr().out
    assert "engine line" in out
    assert '"picked": null' in out
    log_text = process_log_path(tmp_path / ".adore").read_text(encoding="utf-8")
    assert "engine line" in log_text
    assert '"picked": null' in log_text


def test_cli_engine_prefers_profile_env_then_falls_back_to_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief   Engine commands pass the config-adjacent `.env` when present and
             otherwise the cwd fallback, independent of the selected config.
    """
    profile_dir = tmp_path / "profile"
    cwd_dir = tmp_path / "service-cwd"
    profile_dir.mkdir()
    cwd_dir.mkdir()
    config = _config_file(profile_dir)
    profile_env = profile_dir / ".env"
    cwd_env = cwd_dir / ".env"
    profile_env.write_text("KEY=profile\n", encoding="utf-8")
    cwd_env.write_text("KEY=cwd\n", encoding="utf-8")
    selected: list[Path] = []

    class FakeEngine:
        """@brief Minimal dry-run engine for env-path selection."""

        def __init__(self) -> None:
            self.log = print

        def poll_once(self, *, dry_run: bool = False) -> dict:
            return {"dry_run": dry_run}

    def build(_config, *, env_file):
        selected.append(Path(env_file))
        return FakeEngine()

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", build)
    monkeypatch.chdir(cwd_dir)

    assert main(["-c", config, "run", "--dry-run"]) == EXIT_OK
    profile_env.unlink()
    assert main(["-c", config, "run", "--dry-run"]) == EXIT_OK

    assert selected == [profile_env.resolve(), cwd_env]


@pytest.mark.parametrize(
    ("error", "expected", "has_lock_hint"),
    [
        (LockHeldError("another instance holds the lock"), "another instance", True),
        (ForgeError("forge transport failed"), "forge transport failed", False),
    ],
)
def test_cli_run_once_reserves_lock_advice_for_lock_contention(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    error: RuntimeError,
    expected: str,
    has_lock_hint: bool,
) -> None:
    """@brief Non-lock RuntimeErrors keep their text without lock-removal advice."""
    config = _config_file(tmp_path)

    class FailingEngine:
        """@brief Minimal run-once engine raising one scripted failure."""

        def __init__(self) -> None:
            self.log = print

        def poll_once(self, *, dry_run: bool = False) -> dict:
            raise error

    monkeypatch.setattr(
        "adore.cli.Orchestrator.from_config", lambda _config, **_kwargs: FailingEngine()
    )
    assert main(["-c", config, "run", "--once"]) == EXIT_ERROR
    out = capsys.readouterr().out
    assert expected in out
    assert ("provably stale local lock" in out) is has_lock_hint


@pytest.mark.parametrize(
    "argv",
    [
        ["retry", "run-1"],
        ["cancel", "run-1"],
        ["delete", "run-1", "--force"],
        ["reset", "run-1", "--to", "frame", "--force"],
    ],
)
def test_cli_operator_mutations_refuse_a_live_lock(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
) -> None:
    """@brief Retry/cancel/delete/reset fail closed without touching live work."""
    config = _config_file(tmp_path)
    store = StateStore(tmp_path / ".adore")
    store.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="failed"))
    engine = FakeMutationEngine()
    monkeypatch.setattr(
        "adore.cli.Orchestrator.from_config", lambda _config, **_kwargs: engine
    )
    assert store.acquire_lock()
    try:
        assert main(["-c", config, *argv]) == EXIT_ERROR
        assert "holds the lock" in capsys.readouterr().out
        assert engine.calls == []
        assert store.exists("run-1")
        assert store.lock_info()["pid"] == os.getpid()
    finally:
        store.release_lock()


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["retry", "run-1"], ("retry", "run-1")),
        (["cancel", "run-1"], ("cancel", "run-1", "cancelled")),
        (["delete", "run-1", "--force"], ("cancel", "run-1", "deleted")),
        (["reset", "run-1", "--to", "frame", "--force"],
         ("reset", "run-1", "frame")),
    ],
)
def test_cli_operator_mutations_acquire_and_release_the_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    expected: tuple,
) -> None:
    """@brief Every successful operator mutation releases its acquired lock."""
    config = _config_file(tmp_path)
    store = StateStore(tmp_path / ".adore")
    store.save(RunState(run_id="run-1", ticket_iid=1, lifecycle="failed"))
    engine = FakeMutationEngine(store)
    monkeypatch.setattr(
        "adore.cli.Orchestrator.from_config", lambda _config, **_kwargs: engine
    )

    assert main(["-c", config, *argv]) == EXIT_OK
    assert engine.calls == [expected]
    assert store.lock_info() is None


def test_cli_logs_remain_available_while_lock_is_held(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Read-only journal inspection does not contend with the conductor."""
    config = _config_file(tmp_path)
    store = StateStore(tmp_path / ".adore")
    store.journal("run-1", "picked", ticket=1)
    monkeypatch.setattr(
        "adore.cli.Orchestrator.from_config",
        lambda _config, **_kwargs: FakeMutationEngine(),
    )
    assert store.acquire_lock()
    try:
        assert main(["-c", config, "logs", "run-1"]) == EXIT_OK
        assert "picked" in capsys.readouterr().out
        assert store.lock_info()["pid"] == os.getpid()
    finally:
        store.release_lock()


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
        f'kind = "gitlab"\nrepo = "grp/proj"\n'
        f'repo_path = "{clone.as_posix()}"\n'
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


@pytest.mark.parametrize("reason", ["at_capacity", "workflow_unavailable", "held"])
def test_cli_manual_start_emits_safe_terminal_reason(tmp_path, monkeypatch, capsys, reason):
    """@brief The worker receives the concrete admission refusal without raw logs."""
    import json

    from adore import cli
    monkeypatch.setattr(cli.Orchestrator, "poll_once", lambda *a, **k: {
        "picked": None, "start_reason": reason})
    assert main(["-c", _config_file(tmp_path), "run", "--once", "--ticket", "7"]) == EXIT_ERROR
    line = capsys.readouterr().out.splitlines()[-1]
    assert line.startswith("ADORE_START_RESULT ")
    assert json.loads(line.removeprefix("ADORE_START_RESULT ")) == {
        "schema": 1, "ticket": 7, "exit_code": 1, "reason": reason}


@pytest.mark.parametrize("failure,reason", [
    (LockHeldError("PRIVATE"), "lock_held"),
    (ForgeError("PRIVATE"), "repository_unavailable"),
    (RuntimeError("PRIVATE"), "engine_fault"),
    (None, "started"),
])
def test_cli_manual_start_binds_exceptions_and_success(
    tmp_path, monkeypatch, capsys, failure, reason,
):
    """@brief Terminal evidence identifies the gate while excluding raw fault details."""
    import json

    from adore import cli
    def poll(*args, **kwargs):
        if failure is not None:
            raise failure
        return {"picked": 7}
    monkeypatch.setattr(cli.Orchestrator, "poll_once", poll)
    code = main(["-c", _config_file(tmp_path), "run", "--once", "--ticket", "7"])
    assert code == (EXIT_OK if failure is None else EXIT_ERROR)
    line = capsys.readouterr().out.splitlines()[-1]
    record = json.loads(line.removeprefix("ADORE_START_RESULT "))
    assert record == {"schema": 1, "ticket": 7, "exit_code": code, "reason": reason}
    assert "PRIVATE" not in line
