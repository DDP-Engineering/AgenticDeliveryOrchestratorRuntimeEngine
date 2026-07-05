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
@brief Tests for the executor launcher (opencode, file-based gate protocol).
@details No container runs; a fake exec target records the argv and simulates
         the executor by writing the output/questions files a real gate run
         would produce. Verifies the WSL-safe script protocol, session
         continuation, questions detection, and the fail-closed negatives.
@author Eng. Dan Dumitru Pasare
@date 2026-07-03
@version 0.1.0
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable, Sequence
from pathlib import Path

from ador.executor.launcher import (
    GATE_SCRIPT,
    OUTPUT_FILE,
    OpencodeExecutor,
    PiExecutor,
    build_executor,
)
from ador.util import CommandResult
import pytest

# CONSTANTS

TEMPLATE = "opencode run --dir {worktree} -m {model} --format json {prompt}"
PI_TEMPLATE = "pi -p --mode json --model {model} {prompt}"

# DATA MODELS / TYPEDEFINITIONS


class FakeExec:
    """
    @brief   Exec-seam double: records argv, simulates gate side effects.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return worktree, tmp_path / "io"


def _executor() -> OpencodeExecutor:
    """
    @brief   A launcher with the standard test template.
    @return  The OpencodeExecutor.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.0
    """
    return OpencodeExecutor(TEMPLATE, "openai/gpt-5.4-fast")


# PUBLIC API / TESTS


def test_gate_script_protocol_is_wsl_safe(tmp_path: Path) -> None:
    """
    @brief   The prompt lives shell-quoted inside gate.sh; the exec argv is
             two space-free tokens, so nothing can be split by wsl.exe.
    @version 0.1.0
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

    assert exec_target.calls == [["sh", f"/ador/io/{GATE_SCRIPT}"]]
    assert exec_target.timeouts == [1200]
    script = (io_dir / GATE_SCRIPT).read_text(encoding="utf-8")
    assert "\r" not in script  # LF only; CRLF breaks sh
    assert "cd /ador/work" in script
    assert "--dir /ador/work" in script
    assert "-m openai/gpt-5.4-fast" in script
    assert "'" in script and "Global Refresh" in script  # prompt quoted inside
    assert f"> /ador/io/{OUTPUT_FILE}" in script
    assert run.ok
    assert run.session_id == "ses_abc123"
    assert not run.has_questions
    assert "session.start" in run.output


def test_session_continuation_appends_session_flag(tmp_path: Path) -> None:
    """
    @brief   A given session id is appended as --session and survives as the
             GateRun session when the output has none.
    @version 0.1.0
    """
    worktree, io_dir = _dirs(tmp_path)
    exec_target = FakeExec(CommandResult(exit_code=0))
    run = _executor().run_gate(
        exec_target, worktree, io_dir, "next gate", session="ses_prev"
    )
    script = (io_dir / GATE_SCRIPT).read_text(encoding="utf-8")
    assert "--session ses_prev" in script
    assert run.session_id == "ses_prev"  # no output file -> keep the known id


def test_questions_file_parks_the_gate(tmp_path: Path) -> None:
    """
    @brief   A questions file written during the gate is detected and read;
             a clean exit does not mask it.
    @version 0.1.0
    """
    worktree, io_dir = _dirs(tmp_path)
    executor = _executor()

    def ask() -> None:
        (worktree / "ADOR_QUESTIONS.md").write_text(
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
    @version 0.1.0
    """
    worktree, io_dir = _dirs(tmp_path)
    stale = worktree / "ADOR_QUESTIONS.md"
    stale.write_text("old round\n", encoding="utf-8")
    run = _executor().run_gate(FakeExec(CommandResult(exit_code=0)), worktree, io_dir, "p")
    assert not run.has_questions
    assert not stale.exists()


def test_executor_failure_passes_through_as_data(tmp_path: Path) -> None:
    """
    @brief   A failing or hung executor (non-zero / 124) is a conductor
             signal; missing output files read as empty, stderr falls back
             to the exec result.
    @version 0.1.0
    """
    worktree, io_dir = _dirs(tmp_path)
    run = _executor().run_gate(
        FakeExec(CommandResult(exit_code=124, stderr="timeout after 1200s")),
        worktree,
        io_dir,
        "p",
    )
    assert not run.ok
    assert run.exit_code == 124
    assert run.output == ""
    assert "timeout" in run.stderr


def test_session_not_found_self_heals_with_fresh_session(tmp_path: Path) -> None:
    """
    @brief   A dead session (container recreated / pruned) relaunches once
             without --session instead of failing the gate (live finding
             2026-07-03).
    @version 0.1.0
    """
    worktree, io_dir = _dirs(tmp_path)
    executor = _executor()
    calls: list[str] = []

    def exec_target(argv, *, timeout=None):
        script = (io_dir / GATE_SCRIPT).read_text(encoding="utf-8")
        calls.append(script)
        if "--session" in script:
            (io_dir / "stderr.log").write_text("Error: Session not found\n",
                                               encoding="utf-8")
            return CommandResult(exit_code=1, stderr="")
        (io_dir / "stderr.log").write_text("", encoding="utf-8")
        (io_dir / OUTPUT_FILE).write_text('{"sessionID":"ses_fresh"}\n',
                                          encoding="utf-8")
        return CommandResult(exit_code=0)

    run = executor.run_gate(exec_target, worktree, io_dir, "p", session="ses_dead")
    assert run.ok
    assert run.session_id == "ses_fresh"
    assert len(calls) == 2
    assert "--session ses_dead" in calls[0]
    assert "--session" not in calls[1]


def test_usage_extraction_from_event_stream(tmp_path: Path) -> None:
    """
    @brief   step_finish token/cost totals are summed into the GateRun;
             malformed lines never break the gate (design 13).
    @version 0.1.0
    """
    worktree, io_dir = _dirs(tmp_path)

    def write_stream() -> None:
        (io_dir / OUTPUT_FILE).write_text(
            '{"type":"step_finish","part":{"tokens":{"input":100,"output":20},'
            '"cost":0.01},"sessionID":"s"}\n'
            "not json with tokens keyword\n"
            '{"type":"step_finish","part":{"tokens":{"input":200,"output":30},'
            '"cost":0.02}}\n',
            encoding="utf-8",
        )

    run = _executor().run_gate(FakeExec(CommandResult(exit_code=0), write_stream),
                               worktree, io_dir, "p")
    assert run.tokens_in == 300
    assert run.tokens_out == 50
    assert abs(run.cost_usd - 0.03) < 1e-9


def test_auto_flag_is_rejected_at_construction() -> None:
    """
    @brief   --auto in the command template fails closed immediately: it
             would auto-approve the executor's own push/merge.
    @version 0.1.0
    """
    with pytest.raises(ValueError, match="--auto"):
        OpencodeExecutor(TEMPLATE + " --auto", "m")
    with pytest.raises(ValueError, match="--auto"):
        build_executor("opencode", "opencode run --auto {prompt}", "m")


def test_factory_wires_questions_file() -> None:
    """
    @brief   The factory passes the configured questions filename through and
             still rejects unknown kinds.
    @version 0.1.0
    """
    executor = build_executor("opencode", TEMPLATE, "m", questions_file="ROBO_QUESTIONS.md")
    assert isinstance(executor, OpencodeExecutor)
    assert executor.questions_file == "ROBO_QUESTIONS.md"
    with pytest.raises(ValueError):
        build_executor("codex", TEMPLATE, "m")


# PUBLIC API / TESTS - Pi executor (config-selectable alternative)


def test_factory_selects_pi() -> None:
    """
    @brief   `[executor] default = "pi"` selects the PiExecutor; a Pi template
             needs no --auto guard (Pi has no such flag) and is accepted.
    @version 0.1.0
    """
    executor = build_executor("pi", PI_TEMPLATE, "openai/gpt-5.5")
    assert isinstance(executor, PiExecutor)
    # the shared file protocol is inherited: same gate.sh, same argv shape
    assert executor.questions_file == "ADOR_QUESTIONS.md"


def test_pi_gate_uses_shared_protocol_and_session(tmp_path: Path) -> None:
    """
    @brief   Pi runs through the same WSL-safe gate.sh protocol and appends
             `--session` for continuation, exactly like opencode.
    @version 0.1.0
    """
    worktree, io_dir = _dirs(tmp_path)
    executor = PiExecutor(PI_TEMPLATE, "openai/gpt-5.5")
    run = executor.run_gate(FakeExec(CommandResult(exit_code=0)), worktree, io_dir,
                            "next gate", session="ses_prev", timeout=900)
    calls_script = (io_dir / GATE_SCRIPT).read_text(encoding="utf-8")
    assert "pi -p --mode json --model openai/gpt-5.5" in calls_script
    assert "--session ses_prev" in calls_script
    assert "\r" not in calls_script and "cd /ador/work" in calls_script
    assert run.session_id == "ses_prev"     # no output -> keep the known id


def test_pi_session_id_parsed_from_session_header(tmp_path: Path) -> None:
    """
    @brief   Pi's JSON stream opens with a {"type":"session","id":...} header;
             the id is read from that event (not opencode's sessionID key).
    @version 0.1.0
    """
    worktree, io_dir = _dirs(tmp_path)

    def write_stream() -> None:
        (io_dir / OUTPUT_FILE).write_text(
            '{"type":"session","version":3,"id":"pi-uuid-123","cwd":"/ador/work"}\n'
            '{"type":"message_update","assistantMessageEvent":{"type":"text_delta",'
            '"delta":"working"}}\n',
            encoding="utf-8",
        )

    run = PiExecutor(PI_TEMPLATE, "m").run_gate(
        FakeExec(CommandResult(exit_code=0), write_stream), worktree, io_dir, "p")
    assert run.session_id == "pi-uuid-123"
    # Pi does not report usage in the stream today -> zeros (metrics tolerate)
    assert run.tokens_in == 0 and run.tokens_out == 0 and run.cost_usd == 0.0


def test_pi_questions_and_failure_behave_like_the_shared_base(tmp_path: Path) -> None:
    """
    @brief   Clarification parking and fail-closed pass-through are inherited
             unchanged from the shared protocol.
    @version 0.1.0
    """
    worktree, io_dir = _dirs(tmp_path)

    def ask() -> None:
        (worktree / "ADOR_QUESTIONS.md").write_text("1. Which region?\n", encoding="utf-8")

    parked = PiExecutor(PI_TEMPLATE, "m").run_gate(
        FakeExec(CommandResult(exit_code=0), ask), worktree, io_dir, "p")
    assert parked.has_questions and "Which region" in parked.questions

    failed = PiExecutor(PI_TEMPLATE, "m").run_gate(
        FakeExec(CommandResult(exit_code=124, stderr="timeout")), worktree, io_dir, "p")
    assert not failed.ok and failed.exit_code == 124


# END OF FILE
