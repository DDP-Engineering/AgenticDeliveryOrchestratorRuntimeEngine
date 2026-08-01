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
    CodexExecutor,
    OpencodeExecutor,
    PiExecutor,
    QwenExecutor,
    build_executor,
)
from adore.util import CommandResult
import pytest

# CONSTANTS

TEMPLATE = "opencode run --dir {worktree} -m {model} --format json {prompt}"
PI_TEMPLATE = "pi -p --mode json --model {model} {prompt}"
CODEX_TEMPLATE = (
    "codex exec {resume}--json --model {model} "
    "--ignore-user-config --disable plugins "
    "--dangerously-bypass-approvals-and-sandbox {prompt}"
)
QWEN_TEMPLATE = "qwen -p --model {model} --output-format json {prompt}"

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


def _executor() -> OpencodeExecutor:
    """
    @brief   A launcher with the standard test template.
    @return  The OpencodeExecutor.
    """
    return OpencodeExecutor(TEMPLATE, "openai/gpt-5.4-fast")


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
    assert "--dir /adore/work" in script
    assert "-m openai/gpt-5.4-fast" in script
    assert "'" in script and "Global Refresh" in script  # prompt quoted inside
    # the command is a `{ ...; }` group so redirection covers a whole compound
    # template, not just its last stage
    assert "{ " in script and "; } > " in script
    assert f"> /adore/io/{OUTPUT_FILE}" in script
    assert run.ok
    assert run.session_id == "ses_abc123"
    assert not run.has_questions
    assert "session.start" in run.output


def test_session_continuation_appends_session_flag(tmp_path: Path) -> None:
    """
    @brief   A given session id is appended as --session and survives as the
             GateRun session when the output has none.
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
        FakeExec(CommandResult(exit_code=124, stderr="timeout after 1200s")),
        worktree,
        io_dir,
        "p",
    )
    assert not run.ok
    assert run.exit_code == 124
    assert run.output == ""
    assert "timeout" in run.stderr


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
    assert "opencode run" in (archive / GATE_SCRIPT).read_text(encoding="utf-8")
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


def test_archive_records_nonzero_exit(tmp_path: Path) -> None:
    """
    @brief   A failed executor launch still archives the partial output and
             stderr before the conductor decides whether to retry.
    """
    worktree, io_dir = _dirs(tmp_path)

    def write_partial() -> None:
        (io_dir / OUTPUT_FILE).write_text("partial stream\n", encoding="utf-8")
        (io_dir / STDERR_FILE).write_text("tool exploded\n", encoding="utf-8")

    run = _executor().run_gate(
        FakeExec(CommandResult(exit_code=124), write_partial),
        worktree,
        io_dir,
        "p",
        archive_stem="003-requirement",
    )

    archive = io_dir / ARCHIVE_DIR / "003-requirement-attempt1"
    assert not run.ok
    assert run.artifact_dirs == [str(archive)]
    assert "partial stream" in (archive / OUTPUT_FILE).read_text(encoding="utf-8")
    assert "tool exploded" in (archive / STDERR_FILE).read_text(encoding="utf-8")
    meta = json.loads((archive / "meta.json").read_text(encoding="utf-8"))
    assert meta["exit_code"] == 124


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
        FakeExec(CommandResult(exit_code=0)),
        worktree,
        io_dir,
        "p",
        archive_stem="004-validation",
    )

    assert not run.ok
    assert "archive write failed" in run.stderr
    assert "disk full" in run.stderr
    assert run.artifact_dirs == []


def test_session_not_found_self_heals_with_fresh_session(tmp_path: Path) -> None:
    """
    @brief   A dead session (container recreated / pruned) relaunches once
             without --session instead of failing the gate (live finding
             2026-07-03).
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

    run = executor.run_gate(
        exec_target,
        worktree,
        io_dir,
        "p",
        session="ses_dead",
        archive_stem="004-implementation",
    )
    assert run.ok
    assert run.session_id == "ses_fresh"
    assert len(calls) == 2
    assert "--session ses_dead" in calls[0]
    assert "--session" not in calls[1]
    assert run.artifact_dirs == [
        str(io_dir / ARCHIVE_DIR / "004-implementation-attempt1"),
        str(io_dir / ARCHIVE_DIR / "004-implementation-attempt2"),
    ]
    first = Path(run.artifact_dirs[0])
    second = Path(run.artifact_dirs[1])
    assert "Session not found" in (first / STDERR_FILE).read_text(encoding="utf-8")
    assert "ses_fresh" in (second / OUTPUT_FILE).read_text(encoding="utf-8")


def test_usage_extraction_from_event_stream(tmp_path: Path) -> None:
    """
    @brief   step_finish token/cost totals are summed into the GateRun;
             malformed lines never break the gate (design 13).
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
    """
    with pytest.raises(ValueError, match="--auto"):
        OpencodeExecutor(TEMPLATE + " --auto", "m")
    with pytest.raises(ValueError, match="--auto"):
        build_executor("opencode", "opencode run --auto {prompt}", "m")
    # the `--flag=value` form is caught too, not just the bare flag
    with pytest.raises(ValueError, match="--auto"):
        OpencodeExecutor(TEMPLATE + " --auto=true", "m")


def test_factory_wires_questions_file() -> None:
    """
    @brief   The factory passes the configured questions filename through and
             still rejects unknown kinds.
    """
    executor = build_executor("opencode", TEMPLATE, "m", questions_file="ROBO_QUESTIONS.md")
    assert isinstance(executor, OpencodeExecutor)
    assert executor.questions_file == "ROBO_QUESTIONS.md"
    with pytest.raises(ValueError):
        build_executor("gemini", TEMPLATE, "m")   # a genuinely unknown kind


# PUBLIC API / TESTS - Qwen executor (stateless per gate)


def test_factory_selects_qwen_and_bans_yolo() -> None:
    """
    @brief   `default = "qwen"` selects QwenExecutor; --yolo (auto-approve all
             tools) is rejected at construction.
    """
    executor = build_executor("qwen", QWEN_TEMPLATE, "qwen3-coder-plus")
    assert isinstance(executor, QwenExecutor)
    with pytest.raises(ValueError, match="--yolo"):
        QwenExecutor(QWEN_TEMPLATE + " --yolo", "m")


def test_qwen_is_stateless_no_session_or_resume(tmp_path: Path) -> None:
    """
    @brief   Qwen runs each gate fresh: a fresh gate surfaces no session id (so
             the conductor never propagates one), and even when a session id is
             passed the gate.sh carries neither --session nor a resume - the
             workflow's file-based state carries context.
    """
    worktree, io_dir = _dirs(tmp_path)
    executor = QwenExecutor(QWEN_TEMPLATE, "qwen3-coder-plus")

    fresh = executor.run_gate(FakeExec(CommandResult(exit_code=0)), worktree, io_dir,
                              "gate one")
    assert fresh.session_id == ""           # nothing to continue; stays empty in flow
    assert fresh.tokens_in == 0 and fresh.cost_usd == 0.0   # usage pinned in spike

    executor.run_gate(FakeExec(CommandResult(exit_code=0)), worktree, io_dir,
                      "gate two", session="ignored-by-qwen")
    script = (io_dir / GATE_SCRIPT).read_text(encoding="utf-8")
    assert "qwen -p --model qwen3-coder-plus --output-format json" in script
    assert "--session" not in script and "resume" not in script


def test_qwen_questions_and_failure_inherited(tmp_path: Path) -> None:
    """
    @brief   Clarification parking and fail-closed pass-through come from the
             shared base unchanged.
    """
    worktree, io_dir = _dirs(tmp_path)

    def ask() -> None:
        (worktree / "ADORE_QUESTIONS.md").write_text("1. Which target?\n", encoding="utf-8")

    parked = QwenExecutor(QWEN_TEMPLATE, "m").run_gate(
        FakeExec(CommandResult(exit_code=0), ask), worktree, io_dir, "p")
    assert parked.has_questions and "Which target" in parked.questions

    failed = QwenExecutor(QWEN_TEMPLATE, "m").run_gate(
        FakeExec(CommandResult(exit_code=124, stderr="timeout")), worktree, io_dir, "p")
    assert not failed.ok and failed.exit_code == 124


# PUBLIC API / TESTS - Codex executor (subcommand-resume + approval model)


def test_factory_selects_codex_and_allows_container_full_auto() -> None:
    """
    @brief   `default = "codex"` selects CodexExecutor; full-auto is allowed
             because ADORE relies on the executor container as the sandbox.
    """
    executor = build_executor("codex", CODEX_TEMPLATE, "gpt-5.5-codex")
    assert isinstance(executor, CodexExecutor)


def test_codex_first_gate_vs_resume_command_structure(tmp_path: Path) -> None:
    """
    @brief   The first gate runs `codex exec ...`; a continuing gate rewrites
             the structure to `codex exec resume --last ...` (not an appended
             --session flag).
    """
    worktree, io_dir = _dirs(tmp_path)
    executor = CodexExecutor(CODEX_TEMPLATE, "gpt-5.5-codex")

    executor.run_gate(FakeExec(CommandResult(exit_code=0)), worktree, io_dir, "gate one")
    new_script = (io_dir / GATE_SCRIPT).read_text(encoding="utf-8")
    assert "codex exec --json" in new_script
    assert "resume" not in new_script
    assert "--session" not in new_script          # codex never uses --session

    executor.run_gate(FakeExec(CommandResult(exit_code=0)), worktree, io_dir,
                      "gate two", session="anything-truthy")
    resume_script = (io_dir / GATE_SCRIPT).read_text(encoding="utf-8")
    assert "codex exec resume --last --json" in resume_script


def test_codex_parses_usage_from_json(tmp_path: Path) -> None:
    """
    @brief   Codex --json usage (input/output tokens, cost) is summed into the
             GateRun; a session/thread id is read best-effort. Schema is
             provisional (pinned by the spike); malformed lines are ignored.
    """
    worktree, io_dir = _dirs(tmp_path)

    def write_stream() -> None:
        (io_dir / OUTPUT_FILE).write_text(
            '{"type":"thread.started","thread_id":"th_abc"}\n'
            "not json with usage keyword\n"
            '{"type":"turn.completed","usage":{"input_tokens":120,"output_tokens":30,'
            '"cost_usd":0.02}}\n',
            encoding="utf-8",
        )

    run = CodexExecutor(CODEX_TEMPLATE, "m").run_gate(
        FakeExec(CommandResult(exit_code=0), write_stream), worktree, io_dir, "p")
    assert run.tokens_in == 120 and run.tokens_out == 30
    assert abs(run.cost_usd - 0.02) < 1e-9
    assert run.session_id == "th_abc"


def test_codex_questions_and_failure_inherited(tmp_path: Path) -> None:
    """
    @brief   Clarification parking and fail-closed pass-through come from the
             shared base unchanged.
    """
    worktree, io_dir = _dirs(tmp_path)

    def ask() -> None:
        (worktree / "ADORE_QUESTIONS.md").write_text("1. Which env?\n", encoding="utf-8")

    parked = CodexExecutor(CODEX_TEMPLATE, "m").run_gate(
        FakeExec(CommandResult(exit_code=0), ask), worktree, io_dir, "p")
    assert parked.has_questions and "Which env" in parked.questions

    failed = CodexExecutor(CODEX_TEMPLATE, "m").run_gate(
        FakeExec(CommandResult(exit_code=124, stderr="timeout")), worktree, io_dir, "p")
    assert not failed.ok and failed.exit_code == 124


# PUBLIC API / TESTS - Pi executor (config-selectable alternative)


def test_factory_selects_pi() -> None:
    """
    @brief   `[executor] default = "pi"` selects the PiExecutor; a Pi template
             needs no --auto guard (Pi has no such flag) and is accepted.
    """
    executor = build_executor("pi", PI_TEMPLATE, "openai/gpt-5.5")
    assert isinstance(executor, PiExecutor)
    # the shared file protocol is inherited: same gate.sh, same argv shape
    assert executor.questions_file == "ADORE_QUESTIONS.md"


def test_pi_gate_uses_shared_protocol_and_session(tmp_path: Path) -> None:
    """
    @brief   Pi runs through the same WSL-safe gate.sh protocol and appends
             `--session` for continuation, exactly like opencode.
    """
    worktree, io_dir = _dirs(tmp_path)
    executor = PiExecutor(PI_TEMPLATE, "openai/gpt-5.5")
    run = executor.run_gate(FakeExec(CommandResult(exit_code=0)), worktree, io_dir,
                            "next gate", session="ses_prev", timeout=900)
    calls_script = (io_dir / GATE_SCRIPT).read_text(encoding="utf-8")
    assert "pi -p --mode json --model openai/gpt-5.5" in calls_script
    assert "--session ses_prev" in calls_script
    assert "\r" not in calls_script and "cd /adore/work" in calls_script
    assert run.session_id == "ses_prev"     # no output -> keep the known id


def test_pi_session_id_parsed_from_session_header(tmp_path: Path) -> None:
    """
    @brief   Pi's JSON stream opens with a {"type":"session","id":...} header;
             the id is read from that event (not opencode's sessionID key).
    """
    worktree, io_dir = _dirs(tmp_path)

    def write_stream() -> None:
        (io_dir / OUTPUT_FILE).write_text(
            '{"type":"session","version":3,"id":"pi-uuid-123","cwd":"/adore/work"}\n'
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


# END OF FILE
