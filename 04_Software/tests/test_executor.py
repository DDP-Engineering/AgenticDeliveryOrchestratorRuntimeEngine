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
@file test_executor.py
@brief Tests for the Pi executor launcher (file-based gate protocol).
@details No container runs; a fake exec target records the argv and simulates
         the executor by writing the output/questions files a real gate run
         would produce. Verifies the WSL-safe script protocol, session
         continuation, questions detection, and the fail-closed negatives.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable, Sequence
import json
from pathlib import Path

from adore.executor.launcher import (
    ARCHIVE_DIR,
    GATE_SCRIPT,
    OUTPUT_FILE,
    STDERR_FILE,
    PiExecutor,
    build_executor,
)
from adore.util import CommandResult
import pytest

# CONSTANTS

PI_TEMPLATE = "pi -p --mode json --model {model} {prompt}"

# DATA MODELS / TYPEDEFINITIONS


class FakeExec:
    """
    @brief   Exec-seam double: records argv, simulates gate side effects.
    """

    def __init__(
        self,
        result: CommandResult,
        side_effect: Callable[[], None] | None = None,
    ) -> None:
        """
        @brief      Configure the double.
        @param[in]  result The CommandResult to return.
        @param[in]  side_effect Callable simulating what the executor wrote
                                (output file, questions file) while running.
        """
        self.result = result
        self.side_effect = side_effect
        self.calls: list[list[str]] = []
        self.timeouts: list[float | None] = []

    def __call__(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> CommandResult:
        """
        @brief      Record the call, run the side effect, return the result.
        @param[in]  argv Command vector.
        @param[in]  timeout Recorded for budget assertions.
        @return     The canned CommandResult.
        """
        self.calls.append([str(part) for part in argv])
        self.timeouts.append(timeout)
        if self.side_effect:
            self.side_effect()
        return self.result


# HELPER FUNCTIONS


def _dirs(tmp_path: Path) -> tuple[Path, Path]:
    """
    @brief      A worktree dir and io dir for a fake run.
    @param[in]  tmp_path pytest tmp dir.
    @return     (worktree, io_dir), worktree created.
    """
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return worktree, tmp_path / "io"


def _executor() -> PiExecutor:
    """
    @brief   A file-protocol launcher (no `spawn` seam) with the Pi template.
    @return  The PiExecutor.
    """
    return PiExecutor(PI_TEMPLATE, "openai/gpt-5.4-fast")


# PUBLIC API / TESTS


def test_gate_script_protocol_is_wsl_safe(tmp_path: Path) -> None:
    """
    @brief   The prompt lives shell-quoted inside gate.sh; the exec argv is
             two space-free tokens, so nothing can be split by wsl.exe.
    """
    worktree, io_dir = _dirs(tmp_path)
    prompt = 'Run the intake gate for ticket #14: "Global Refresh" (scope: small)'
    executor = _executor()

    def write_output() -> None:
        (io_dir / OUTPUT_FILE).write_text(
            '{"type":"session.start","sessionID":"ses_abc123"}\n', encoding="utf-8"
        )

    exec_target = FakeExec(CommandResult(exit_code=0), write_output)
    run = executor.run_gate(exec_target, worktree, io_dir, prompt, timeout=1200)

    assert exec_target.calls == [["sh", f"/adore/io/{GATE_SCRIPT}"]]
    assert exec_target.timeouts == [1200]
    script = (io_dir / GATE_SCRIPT).read_text(encoding="utf-8")
    assert "\r" not in script  # LF only; CRLF breaks sh
    assert "cd /adore/work" in script
    assert "--model openai/gpt-5.4-fast" in script
    assert "'" in script and "Global Refresh" in script  # prompt quoted inside
    # the command is a `{ ...; }` group so redirection covers a whole compound
    # template, not just its last stage
    assert "{ " in script and "; } > " in script
    assert f"> /adore/io/{OUTPUT_FILE}" in script
    assert run.ok
    assert not run.has_questions
    assert "session.start" in run.output
    assert "--session" not in script  # every gate is a fresh session


def test_questions_file_parks_the_gate(tmp_path: Path) -> None:
    """
    @brief   A questions file written during the gate is detected and read;
             a clean exit does not mask it.
    """
    worktree, io_dir = _dirs(tmp_path)
    executor = _executor()

    def ask() -> None:
        (worktree / "ADORE_QUESTIONS.md").write_text(
            "1. Which variant applies?\n", encoding="utf-8"
        )

    run = executor.run_gate(FakeExec(CommandResult(exit_code=0), ask), worktree, io_dir, "p")
    assert run.ok
    assert run.has_questions
    assert "Which variant" in run.questions


def test_stale_questions_file_is_cleared_before_launch(tmp_path: Path) -> None:
    """
    @brief   A leftover questions file from an earlier round never
             false-parks the next gate: presence after the gate must mean it
             was written by THIS gate.
    """
    worktree, io_dir = _dirs(tmp_path)
    stale = worktree / "ADORE_QUESTIONS.md"
    stale.write_text("old round\n", encoding="utf-8")
    run = _executor().run_gate(FakeExec(CommandResult(exit_code=0)), worktree, io_dir, "p")
    assert not run.has_questions
    assert not stale.exists()


def test_executor_failure_passes_through_as_data(tmp_path: Path) -> None:
    """
    @brief   A failing or hung executor (non-zero / 124) is a conductor
             signal; missing output files read as empty, stderr falls back
             to the exec result.
    """
    worktree, io_dir = _dirs(tmp_path)
    run = _executor().run_gate(
        FakeExec(CommandResult(
            exit_code=124,
            stderr="process ended after the wall-clock bound",
            timed_out=True,
        )),
        worktree,
        io_dir,
        "p",
    )
    assert not run.ok
    assert run.exit_code == 124
    assert run.timed_out
    assert run.output == ""
    assert "wall-clock" in run.stderr


def test_a_silent_launch_does_not_inherit_the_previous_stream(tmp_path: Path) -> None:
    """
    @brief   A launch that produces nothing must read back as nothing.
    @details An executor can exit 0 in a second without writing, and the live
             exchange files then still hold the PREVIOUS stage's transcript.
             Reading them attributed that stage's work to this one in the
             archive and re-counted its tokens against the cost budget (live
             finding 2026-09-18: a build attempt archived byte-identical
             design output, same sessionID). The streams are cleared before
             every launch, exactly as the questions file already was.
    """
    worktree, io_dir = _dirs(tmp_path)
    executor = _executor()

    def write_previous_stage() -> None:
        (io_dir / OUTPUT_FILE).write_text(
            '{"type":"turn_end","message":{"usage":{"input":900,"output":100}}}\n',
            encoding="utf-8",
        )
        (io_dir / STDERR_FILE).write_text("design noise\n", encoding="utf-8")

    first = executor.run_gate(
        FakeExec(CommandResult(exit_code=0), write_previous_stage),
        worktree, io_dir, "design", archive_stem="design",
    )
    assert first.tokens_in == 900

    # now a launch that writes nothing at all
    silent = executor.run_gate(
        FakeExec(CommandResult(exit_code=0)), worktree, io_dir,
        "build", archive_stem="build",
    )

    assert silent.output == ""          # not the design transcript
    assert silent.tokens_in == 0 and silent.cost_usd == 0.0   # not re-counted
    archived = (io_dir / ARCHIVE_DIR / "build-attempt1" / OUTPUT_FILE)
    assert archived.read_text(encoding="utf-8") == ""


def test_gate_launch_archive_preserves_output_and_meta(tmp_path: Path) -> None:
    """
    @brief   A normal launch keeps the live exchange files and also creates an
             immutable per-launch archive with gate.sh/output/stderr/meta.
    """
    worktree, io_dir = _dirs(tmp_path)

    def write_output() -> None:
        (io_dir / OUTPUT_FILE).write_text('{"sessionID":"ses_archive"}\n',
                                          encoding="utf-8")
        (io_dir / STDERR_FILE).write_text("minor warning\n", encoding="utf-8")

    run = _executor().run_gate(
        FakeExec(CommandResult(exit_code=0), write_output),
        worktree,
        io_dir,
        "p",
        archive_stem="001-intake",
    )

    archive = io_dir / ARCHIVE_DIR / "001-intake-attempt1"
    assert run.artifact_dirs == [str(archive)]
    assert (io_dir / OUTPUT_FILE).read_text(encoding="utf-8") == (
        archive / OUTPUT_FILE
    ).read_text(encoding="utf-8")
    assert "minor warning" in (archive / STDERR_FILE).read_text(encoding="utf-8")
    assert "pi -p --mode json" in (archive / GATE_SCRIPT).read_text(encoding="utf-8")
    meta = json.loads((archive / "meta.json").read_text(encoding="utf-8"))
    assert meta["exit_code"] == 0
    assert meta["archive_stem"] == "001-intake"
    assert meta["output_file_present"] is True
    assert meta["stderr_file_present"] is True


def test_archive_records_missing_output_as_empty_file(tmp_path: Path) -> None:
    """
    @brief   Missing output.jsonl remains a valid executor outcome and is
             archived as an empty file with presence pinned in meta.json.
    """
    worktree, io_dir = _dirs(tmp_path)
    run = _executor().run_gate(
        FakeExec(CommandResult(exit_code=0)),
        worktree,
        io_dir,
        "p",
        archive_stem="002-check",
    )

    archive = io_dir / ARCHIVE_DIR / "002-check-attempt1"
    assert run.ok
    assert run.artifact_dirs == [str(archive)]
    assert (archive / OUTPUT_FILE).read_text(encoding="utf-8") == ""
    meta = json.loads((archive / "meta.json").read_text(encoding="utf-8"))
    assert meta["output_file_present"] is False
    assert meta["stderr_file_present"] is False


def test_archive_records_nonzero_exit_and_timeout(tmp_path: Path) -> None:
    """
    @brief   A failed executor launch still archives the partial output and
             stderr before the conductor decides whether to retry.
    """
    worktree, io_dir = _dirs(tmp_path)

    def write_partial() -> None:
        (io_dir / OUTPUT_FILE).write_text("partial stream\n", encoding="utf-8")
        (io_dir / STDERR_FILE).write_text("tool exploded\n", encoding="utf-8")

    run = _executor().run_gate(
        FakeExec(CommandResult(exit_code=124, timed_out=True), write_partial),
        worktree,
        io_dir,
        "p",
        archive_stem="003-requirement",
    )

    archive = io_dir / ARCHIVE_DIR / "003-requirement-attempt1"
    assert not run.ok
    assert run.timed_out
    assert run.artifact_dirs == [str(archive)]
    assert "partial stream" in (archive / OUTPUT_FILE).read_text(encoding="utf-8")
    assert "tool exploded" in (archive / STDERR_FILE).read_text(encoding="utf-8")
    meta = json.loads((archive / "meta.json").read_text(encoding="utf-8"))
    assert meta["exit_code"] == 124
    assert meta["timed_out"] is True


def test_archive_write_failure_fails_gate_as_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief   An archive write failure never silently advances the gate; it is
             returned as a failed GateRun for the conductor to handle.
    """
    worktree, io_dir = _dirs(tmp_path)
    executor = _executor()

    def fail_archive(*_args, **_kwargs):
        """
        @brief   Simulate a disk failure while writing the archive.
        """
        raise OSError("disk full")

    monkeypatch.setattr(executor, "_archive_launch", fail_archive)

    run = executor.run_gate(
        FakeExec(CommandResult(exit_code=124, timed_out=True)),
        worktree,
        io_dir,
        "p",
        archive_stem="004-validation",
    )

    assert not run.ok
    assert run.timed_out
    assert "archive write failed" in run.stderr
    assert "disk full" in run.stderr
    assert run.artifact_dirs == []


def test_factory_wires_questions_file() -> None:
    """
    @brief   The factory builds the Pi launcher and passes the configured
             questions filename through.
    """
    executor = build_executor(PI_TEMPLATE, "m", questions_file="ROBO_QUESTIONS.md")
    assert isinstance(executor, PiExecutor)
    assert executor.questions_file == "ROBO_QUESTIONS.md"


def test_pi_gate_uses_the_shared_fresh_session_protocol(tmp_path: Path) -> None:
    """
    @brief   Without a `spawn` seam Pi runs through the WSL-safe gate.sh
             protocol, with no session flag appended.
    """
    worktree, io_dir = _dirs(tmp_path)
    run = PiExecutor(PI_TEMPLATE, "openai/gpt-5.5").run_gate(
        FakeExec(CommandResult(exit_code=0)), worktree, io_dir, "next gate",
        timeout=900,
    )
    script = (io_dir / GATE_SCRIPT).read_text(encoding="utf-8")
    assert "pi -p --mode json --model openai/gpt-5.5" in script
    assert "--session" not in script
    assert "\r" not in script and "cd /adore/work" in script
    assert run.ok


def test_pi_counts_completed_turn_usage_once(tmp_path: Path) -> None:
    """@brief Pi's final turn events count cached input without duplicate updates."""
    worktree, io_dir = _dirs(tmp_path)
    usage = {"input": 100, "output": 20, "cacheRead": 50,
             "cacheWrite": 10, "totalTokens": 180,
             "cost": {"total": 0.25}}

    def write_stream() -> None:
        events = [
            {"type": "message_update", "usage": usage},
            {"type": "message_end", "message": {"usage": usage}},
            {"type": "turn_end", "message": {"usage": usage}},
            {"type": "turn_end", "message": {"usage": {
                "input": 30, "output": 5, "cacheRead": 0,
                "cacheWrite": 0}}},
        ]
        (io_dir / OUTPUT_FILE).write_text(
            "\n".join(json.dumps(event) for event in events), encoding="utf-8")

    run = PiExecutor(PI_TEMPLATE, "openai-codex/gpt-6-sol").run_gate(
        FakeExec(CommandResult(exit_code=0), write_stream), worktree, io_dir,
        "gate")
    assert (run.tokens_in, run.tokens_out) == (190, 25)
    assert (run.cache_read_tokens, run.cache_write_tokens) == (50, 10)
    assert run.tokens_reported is True
    assert run.cost_usd == 0.0 and not run.cost_reported


def test_pi_explicit_zero_turn_is_reported(tmp_path: Path) -> None:
    """@brief Pi's complete final usage may legitimately be zero."""
    worktree, io_dir = _dirs(tmp_path)

    def write_stream() -> None:
        (io_dir / OUTPUT_FILE).write_text(json.dumps({
            "type": "turn_end", "message": {"usage": {
                "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}},
        }), encoding="utf-8")

    run = PiExecutor(PI_TEMPLATE, "m").run_gate(
        FakeExec(CommandResult(exit_code=0), write_stream), worktree, io_dir, "gate")
    assert run.tokens_reported is True
    assert (run.tokens_in, run.tokens_out) == (0, 0)
    assert (run.cache_read_tokens, run.cache_write_tokens) == (0, 0)


def test_pi_ignores_malformed_or_unfinished_usage(tmp_path: Path) -> None:
    """@brief Corrupt and partial Pi events never inflate token totals."""
    worktree, io_dir = _dirs(tmp_path)

    def write_stream() -> None:
        events = [
            "not json",
            json.dumps({"type": "message_update", "usage": {
                "input": 900, "output": 900}}),
            json.dumps({"type": "turn_end", "message": {"usage": "bad"}}),
            json.dumps({"type": "turn_end", "message": {"usage": {
                "input": True, "output": 1}}}),
            json.dumps({"type": "turn_end", "message": {"usage": {
                "input": -1, "output": 1}}}),
            json.dumps({"type": "turn_end", "message": {"usage": {
                "input": 1_000_000_001, "output": 1}}}),
        ]
        (io_dir / OUTPUT_FILE).write_text("\n".join(events), encoding="utf-8")

    run = PiExecutor(PI_TEMPLATE, "m").run_gate(
        FakeExec(CommandResult(exit_code=0), write_stream), worktree, io_dir,
        "gate")
    assert (run.tokens_in, run.tokens_out) == (0, 0)
    assert run.tokens_reported is False


def test_factory_selects_pi() -> None:
    """
    @brief   Pi is the only executor: the factory always returns PiExecutor.
    """
    executor = build_executor(PI_TEMPLATE, "openai/gpt-5.5")
    assert isinstance(executor, PiExecutor)
    # the shared file protocol is inherited: same gate.sh, same argv shape
    assert executor.questions_file == "ADORE_QUESTIONS.md"


def test_pi_questions_and_failure_behave_like_the_shared_base(tmp_path: Path) -> None:
    """
    @brief   Clarification parking and fail-closed pass-through are inherited
             unchanged from the shared protocol.
    """
    worktree, io_dir = _dirs(tmp_path)

    def ask() -> None:
        (worktree / "ADORE_QUESTIONS.md").write_text("1. Which region?\n", encoding="utf-8")

    parked = PiExecutor(PI_TEMPLATE, "m").run_gate(
        FakeExec(CommandResult(exit_code=0), ask), worktree, io_dir, "p")
    assert parked.has_questions and "Which region" in parked.questions

    failed = PiExecutor(PI_TEMPLATE, "m").run_gate(
        FakeExec(CommandResult(exit_code=124, stderr="timeout")), worktree, io_dir, "p")
    assert not failed.ok and failed.exit_code == 124


def test_pi_rpc_argv_carries_thinking_level() -> None:
    """@brief Explicit Pi effort reaches the process; empty leaves its default."""
    from adore.executor.launcher import pi_rpc_argv
    assert pi_rpc_argv("gpt-5", "openai", thinking="medium")[-2:] == ["--thinking", "medium"]
    assert "--thinking" not in pi_rpc_argv("gpt-5", "openai")


# END OF FILE
