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
@file test_pi_rpc.py
@brief Offline tests for driving Pi through its RPC mode.
@details A fake Pi (`tests/fake_pi_rpc.py`) replays the recorded PI-01 spike
         fixtures over real pipes, so the client is exercised end to end
         without Pi, a container, a provider or a key. Covers completion,
         usage over turns, timeout and cancellation aborts, provider and
         protocol failures, bounded memory, the guard and the isolation flags.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable
import json
from pathlib import Path
import subprocess
import sys
import time

from adore import metrics
from adore.branding import CONTAINER_PI_AGENT_DIR, CONTAINER_PI_CLI, CONTAINER_PI_GUARD
from adore.execution import ExecutionPaths
from adore.executor.base import GateRun
from adore.executor.launcher import ARCHIVE_DIR, GATE_SCRIPT, OUTPUT_FILE, PiExecutor
from adore.executor.pi_rpc import PiRpcResult, run_pi_rpc
import pytest

from tests.test_orchestrator import (
    FakeAegis,
    FakeExecutor,
    make_engine,
    make_run,
    task,
)

# CONSTANTS

FAKE = Path(__file__).with_name("fake_pi_rpc.py")
FIXTURES = Path(__file__).parent / "fixtures" / "pi_rpc"
PROMPT = "Implement the stage."
FAST = {"abort_grace": 2.0, "exit_grace": 2.0, "stats_grace": 2.0}

# DATA MODELS / TYPEDEFINITIONS


class FakePi:
    """
    @brief   Spawn seam that starts the fake Pi and records what ADORE sent.
    """

    def __init__(self, tmp_path: Path, fixture: str, *options: str) -> None:
        self.record = tmp_path / f"{fixture}-commands.log"
        self.command = [sys.executable, "-I", str(FAKE), str(FIXTURES / f"{fixture}.jsonl"),
                        "--record", str(self.record), *options]
        self.processes: list[subprocess.Popen] = []
        self.argv: list[str] = []
        self.env: dict[str, str] = {}

    def __call__(self, argv: list[str], env: dict[str, str]) -> subprocess.Popen:
        self.argv, self.env = list(argv), dict(env)
        process = subprocess.Popen(  # noqa: S603 - fixed test argv
            self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        self.processes.append(process)
        return process

    def commands(self) -> list[dict]:
        """@brief Commands the fake received, in order."""
        if not self.record.is_file():
            return []
        return [json.loads(line) for line in self.record.read_text("utf-8").splitlines()]

    def all_exited(self) -> bool:
        """@brief Whether every spawned fake process has ended."""
        return all(process.poll() is not None for process in self.processes)


class SpawnTarget:
    """
    @brief   Container-target double: container paths plus the spawn seam.
    """

    def __init__(self, fake: FakePi) -> None:
        self.paths = ExecutionPaths()
        self.fake = fake

    def spawn(self, argv, *, env=None):
        return self.fake(list(argv), dict(env or {}))

    def __call__(self, argv, *, timeout=None):  # pragma: no cover - not used by RPC
        raise AssertionError("RPC launches must not use the file protocol")


# HELPER FUNCTIONS


def _run(tmp_path: Path, fixture: str, *options: str, timeout: float | None = 30,
         cancelled: Callable[[], bool] | None = None, **limits) -> tuple[PiRpcResult, FakePi]:
    """@brief Run the client against one fixture with test-sized grace periods."""
    fake = FakePi(tmp_path, fixture, *options)
    result = run_pi_rpc(
        fake, ["pi", "--mode", "rpc"], {}, PROMPT, timeout=timeout, cancelled=cancelled,
        output_path=tmp_path / "output.jsonl", stderr_path=tmp_path / "stderr.log",
        **{**FAST, **limits},
    )
    return result, fake


def _dirs(tmp_path: Path) -> tuple[Path, Path]:
    """@brief Create a worktree and io directory."""
    worktree, io_dir = tmp_path / "work", tmp_path / "io"
    worktree.mkdir()
    io_dir.mkdir()
    return worktree, io_dir


# PUBLIC API


def test_successful_run_with_tool_calls_sums_usage_over_turns(tmp_path: Path) -> None:
    """@brief A recorded four-turn run completes and its turn usage is summed."""
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt")
    assert result.outcome == "completed" and result.exit_code == 0
    assert not result.timed_out
    assert result.usage.turns == 4 and result.usage.complete
    assert (result.usage.tokens_in, result.usage.tokens_out) == (1819 + 3456, 141)
    assert (result.usage.cache_read, result.usage.cache_write) == (3456, 0)
    assert result.tool_calls == 3 and result.blocked_tools == 0
    sent = fake.commands()
    assert sent[0]["type"] == "prompt" and sent[0]["message"] == PROMPT
    assert [command["type"] for command in sent] == ["prompt", "get_session_stats"]
    assert fake.all_exited()


def test_exit_code_after_settling_is_not_the_result(tmp_path: Path) -> None:
    """@brief A crash on exit after a clean `agent_settled` still succeeds."""
    result, _ = _run(tmp_path, "run_tool_calls_chatgpt", "--exit", "3")
    assert result.outcome == "completed" and result.exit_code == 0
    assert result.process_exit == 3


def test_timeout_aborts_and_the_process_is_gone_within_the_grace(tmp_path: Path) -> None:
    """@brief A run that never settles is aborted at the deadline and ends."""
    started = time.monotonic()
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--hang", timeout=0.5)
    elapsed = time.monotonic() - started
    assert result.outcome == "timed-out" and result.timed_out
    assert result.exit_code == 124
    assert "abort" in [command["type"] for command in fake.commands()]
    assert fake.all_exited()
    assert elapsed < 0.5 + FAST["abort_grace"] + FAST["exit_grace"] + FAST["stats_grace"]


def test_timeout_kills_a_process_that_ignores_abort_and_stdin(tmp_path: Path) -> None:
    """@brief A process ignoring `abort` and stdin EOF is terminated after the grace."""
    started = time.monotonic()
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--hang", "--ignore-abort",
                        timeout=0.3, abort_grace=0.5, exit_grace=0.5)
    elapsed = time.monotonic() - started
    assert result.timed_out and result.exit_code == 124
    assert fake.all_exited()
    assert elapsed < 10


def test_cancellation_marker_sends_abort_and_reports_cancelled(tmp_path: Path) -> None:
    """@brief The recorded abort run ends as cancelled, not as success or timeout."""
    result, fake = _run(tmp_path, "run_aborted_chatgpt", cancelled=lambda: True)
    assert result.outcome == "cancelled"
    assert result.exit_code == 130 and not result.timed_out
    assert [command["type"] for command in fake.commands()][:2] == ["prompt", "abort"]
    assert fake.all_exited()


@pytest.mark.parametrize(("fixture", "failure"), [
    ("failed_invalid_api_key", "credential"),
    ("failed_refresh_chatgpt", "sign-in"),
    ("failed_rate_limit_retry", "rate-limit"),
    ("failed_unreachable_endpoint", "network"),
    ("failed_model_not_supported_chatgpt", "model"),
    ("failed_no_credentials", "credential"),
])
def test_provider_failures_are_classified(tmp_path: Path, fixture: str, failure: str) -> None:
    """@brief Each recorded provider failure maps to its class and a failed launch."""
    result, fake = _run(tmp_path, fixture, "--key-hint", "sk-inval****0000")
    assert result.outcome == "failed" and result.exit_code == 1
    assert not result.timed_out
    assert result.failure == failure
    assert result.message.startswith(f"Pi run failed ({failure}): ")
    assert "****" not in result.message and "sk-inval" not in result.message
    assert fake.all_exited()


def test_crash_before_settling_fails_closed(tmp_path: Path) -> None:
    """@brief A process that exits mid-run is a protocol failure with its code."""
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--crash-after", "6")
    assert result.outcome == "protocol-error"
    assert result.exit_code == 3 and not result.timed_out
    assert "exited before the run settled" in result.message
    assert fake.all_exited()


def test_malformed_stdout_line_fails_closed(tmp_path: Path) -> None:
    """@brief A non-JSON stdout record ends the process and fails the launch."""
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--garbage")
    assert result.outcome == "protocol-error" and result.exit_code != 0
    assert "malformed" in result.message
    assert fake.all_exited()


def test_start_failure_is_a_protocol_failure(tmp_path: Path) -> None:
    """@brief An executable that cannot start yields exit 127 evidence."""
    def spawn(argv, env):
        raise FileNotFoundError("node")

    result = run_pi_rpc(spawn, ["node"], {}, PROMPT, timeout=5, **FAST)
    assert result.outcome == "protocol-error" and result.exit_code == 127
    assert "could not start" in result.message


def test_large_output_stays_bounded(tmp_path: Path) -> None:
    """@brief Many large records and an over-limit record keep evidence bounded."""
    limit = 256 * 1024
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--big-count", "200",
                        "--big-size", "100000", "--oversize", str(limit * 3),
                        max_record_bytes=limit)
    assert result.outcome == "completed" and result.usage.complete
    assert len(result.output.encode("utf-8")) <= 64 * 1024
    assert len(result.stderr.encode("utf-8")) <= 64 * 1024
    persisted = (tmp_path / "output.jsonl").read_bytes().splitlines()
    assert all(len(line) <= 64 * 1024 for line in persisted)
    records = [json.loads(line) for line in persisted]
    assert not any(record.get("type") == "message_update" for record in records)
    assert any(record.get("adore_omitted_bytes") for record in records)
    assert result.records_skipped == 1
    assert fake.all_exited()


def test_unreadable_assistant_record_makes_tokens_unavailable(tmp_path: Path) -> None:
    """@brief A skipped assistant `message_end` withdraws the token claim."""
    limit = 256 * 1024
    result, _ = _run(tmp_path, "run_tool_calls_chatgpt", "--pad-message-end",
                     str(limit * 2), max_record_bytes=limit)
    assert result.outcome == "completed"
    assert not result.usage.complete


def test_unreadable_final_assistant_record_fails_closed(tmp_path: Path) -> None:
    """@brief An over-limit last assistant record cannot be read as a success."""
    limit = 256 * 1024
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--pad-message-end",
                        str(limit * 2), "--pad-last", max_record_bytes=limit)
    assert result.outcome == "protocol-error" and result.exit_code != 0
    assert "could not be read" in result.message
    assert fake.all_exited()


def test_deeply_nested_record_is_malformed(tmp_path: Path) -> None:
    """@brief A record too deep to parse fails closed as a malformed record."""
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--deep", "200000")
    assert result.outcome == "protocol-error" and "malformed" in result.message
    assert fake.all_exited()


def test_guard_blocks_publication_commands_in_rpc_mode(tmp_path: Path) -> None:
    """@brief The recorded guard run blocks git push, gh, glab and tea; echo runs."""
    result, _ = _run(tmp_path, "run_guard_blocks_forge")
    assert result.outcome == "completed"
    assert result.tool_calls == 5 and result.blocked_tools == 4


def test_pi_executor_launches_an_isolated_rpc_process(tmp_path: Path) -> None:
    """@brief A container launch uses RPC mode, isolation flags and the guard."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    executor = PiExecutor("pi -p --mode json --model {model} {prompt}", "openai/gpt-5.6-luna")
    run = executor.run_gate(SpawnTarget(fake), worktree, io_dir, PROMPT, timeout=30,
                            archive_stem="build-attempt-1")
    assert run.ok and not run.timed_out
    assert fake.argv[:2] == ["node", CONTAINER_PI_CLI]
    for flag in ("--no-session", "--no-approve", "--no-skills", "--no-extensions",
                 "--no-prompt-templates", "--no-themes", "--no-mcp"):
        assert flag in fake.argv
    assert fake.argv[fake.argv.index("--mode") + 1] == "rpc"
    assert fake.argv[fake.argv.index("-e") + 1] == CONTAINER_PI_GUARD
    assert fake.argv[fake.argv.index("--model") + 1] == "openai/gpt-5.6-luna"
    assert PROMPT not in fake.argv
    assert fake.env == {
        "PI_CODING_AGENT_DIR": CONTAINER_PI_AGENT_DIR, "PI_OFFLINE": "1",
        "PI_TELEMETRY": "0", "PI_SKIP_VERSION_CHECK": "1",
    }
    assert "/.pi" not in CONTAINER_PI_AGENT_DIR
    assert (run.tokens_in, run.tokens_out) == (5275, 141)
    assert (run.cache_read_tokens, run.cache_write_tokens) == (3456, 0)
    assert run.tokens_reported is True
    assert run.cost_usd == 0.0 and run.cost_reported is False
    script = (io_dir / GATE_SCRIPT).read_text(encoding="utf-8")
    assert "--mode" in script and "rpc" in script and PROMPT not in script
    assert (io_dir / OUTPUT_FILE).is_file()
    archives = list((io_dir / ARCHIVE_DIR).iterdir())
    assert len(archives) == 1 and (archives[0] / OUTPUT_FILE).is_file()
    assert executor.cancel_grace_seconds(SpawnTarget(fake)) is not None


def test_pi_executor_failure_reaches_the_existing_failure_path(tmp_path: Path) -> None:
    """@brief A provider failure is a non-zero, non-timeout gate with its reason."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "failed_invalid_api_key", "--key-hint", "sk-inval****0000")
    run = PiExecutor("pi", "openai/gpt-5.4-mini").run_gate(
        SpawnTarget(fake), worktree, io_dir, PROMPT, timeout=30)
    assert not run.ok and not run.timed_out
    assert run.stderr.startswith("Pi run failed (credential): ")
    assert "sk-inval" not in (io_dir / OUTPUT_FILE).read_text(encoding="utf-8")


def test_pi_executor_keeps_the_file_protocol_without_a_spawn_seam(tmp_path: Path) -> None:
    """@brief A native target without `spawn` keeps the configured launch."""
    from adore.util import CommandResult

    calls = []

    def execute(argv, *, timeout=None):
        calls.append(argv)
        return CommandResult(exit_code=0)

    worktree, io_dir = _dirs(tmp_path)
    executor = PiExecutor("pi -p --mode json --model {model} {prompt}", "m")
    assert executor.run_gate(execute, worktree, io_dir, PROMPT, timeout=5).ok
    assert calls and "pi -p --mode json" in (io_dir / GATE_SCRIPT).read_text("utf-8")
    assert executor.cancel_grace_seconds(execute) is None


def test_pi_usage_event_passes_validation_and_reaches_statistics(tmp_path: Path) -> None:
    """@brief The orchestrator journals Pi usage as one valid versioned event."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    gate = PiExecutor("pi", "openai/gpt-5.6-luna").run_gate(
        SpawnTarget(fake), worktree, io_dir, PROMPT, timeout=30)
    engine, *_ = make_engine(tmp_path)
    run = make_run(engine)
    run.iterations = 1
    engine._journal_usage(run, "build", gate)
    events = engine.store.read_journal(run.run_id)
    usage = [event for event in metrics.unique_usage_events(events, run.run_id)
             if event["event"] == "usage"]
    assert len(usage) == 1
    assert usage[0]["executor"] == "pi" and usage[0]["cost_reported"] is False
    summary = metrics.summarize_run(engine.store, run.run_id)
    assert (summary.tokens_in, summary.tokens_out) == (5275, 141)


def test_orchestrator_lets_an_rpc_executor_abort_before_interrupting(tmp_path: Path) -> None:
    """@brief Cancel reaches the executor; the container stop is only a backstop."""
    engine, forge, _, containers, _ = make_engine(tmp_path)
    run = make_run(engine)
    seen = {}

    class RpcExecutor(FakeExecutor):
        def cancel_grace_seconds(self, execute):
            return 30.0

        def run_gate(self, execute, worktree, io_dir, prompt, **kwargs):
            engine.store.request_cancel(run.run_id)
            seen["cancel"] = kwargs["cancel"]()
            time.sleep(0.5)  # longer than the watcher's poll interval
            return GateRun(exit_code=130, stderr="Pi run cancelled")

    engine.executor = RpcExecutor()
    engine._conduct_task(run, forge.ticket, FakeAegis([task("frame")]), "")
    assert seen["cancel"] is True
    assert containers.interrupted == []
    assert engine.store.load(run.run_id).lifecycle == "cancelled"


def test_orchestrator_interrupts_when_the_rpc_grace_runs_out(tmp_path: Path) -> None:
    """@brief A gate still running after its cancel grace gets the container stop."""
    engine, forge, _, containers, _ = make_engine(tmp_path)
    run = make_run(engine)

    class StuckExecutor(FakeExecutor):
        def cancel_grace_seconds(self, execute):
            return 0.2

        def run_gate(self, execute, worktree, io_dir, prompt, **kwargs):
            engine.store.request_cancel(run.run_id)
            assert containers.interrupt_event.wait(5)
            return GateRun(exit_code=1, stderr="container stopped")

    engine.executor = StuckExecutor()
    engine._conduct_task(run, forge.ticket, FakeAegis([task("frame")]), "")
    assert containers.interrupted == [run.container]
    assert engine.store.load(run.run_id).lifecycle == "cancelled"


class CopyTarget(SpawnTarget):
    """
    @brief   Container-target double that also records exec-seam commands.
    """

    def __init__(self, fake: FakePi, *, copy_ok: bool = True) -> None:
        super().__init__(fake)
        self.copy_ok = copy_ok
        self.commands: list[list[str]] = []

    def __call__(self, argv, *, timeout=None):
        from adore.util import CommandResult

        self.commands.append(list(argv))
        assert not self.fake.processes, "models.json must be in place before Pi starts"
        return CommandResult(argv=list(argv), exit_code=0 if self.copy_ok else 1,
                             stderr="" if self.copy_ok else "cp: permission denied")


def test_pi_executor_passes_the_provider_and_model_id(tmp_path: Path) -> None:
    """@brief An API-key provider starts Pi with --provider and --model and no models.json."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    target = CopyTarget(fake)
    run = PiExecutor("pi", "gpt-5.4", provider="openai").run_gate(
        target, worktree, io_dir, PROMPT, timeout=30)
    assert run.ok
    assert fake.argv[fake.argv.index("--provider") + 1] == "openai"
    assert fake.argv[fake.argv.index("--model") + 1] == "gpt-5.4"
    assert target.commands == [] and not (io_dir / "pi-models.json").exists()
    chatgpt = FakePi(tmp_path, "run_tool_calls_chatgpt")
    assert PiExecutor("pi", "gpt-5.6-luna", provider="chatgpt").run_gate(
        SpawnTarget(chatgpt), worktree, io_dir, PROMPT, timeout=30).ok
    assert chatgpt.argv[chatgpt.argv.index("--provider") + 1] == "openai"


def test_pi_executor_writes_the_endpoint_models_json_before_pi_starts(tmp_path: Path) -> None:
    """@brief custom: models.json in io, copied into the agent dir, then Pi on adore-endpoint."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    target = CopyTarget(fake)
    models = {"providers": {"adore-endpoint": {
        "baseUrl": "http://172.27.80.1:1234/v1", "api": "openai-completions",
        "apiKey": "$ADORE_ENDPOINT_API_KEY", "models": [{"id": "qwen/qwen3.5-9b"}]}}}
    run = PiExecutor("pi", "qwen/qwen3.5-9b", provider="custom", models=models).run_gate(
        target, worktree, io_dir, PROMPT, timeout=30)
    assert run.ok
    assert json.loads((io_dir / "pi-models.json").read_text("utf-8")) == models
    assert target.commands == [["cp", "/adore/io/pi-models.json",
                                CONTAINER_PI_AGENT_DIR + "/models.json"]]
    assert fake.argv[fake.argv.index("--provider") + 1] == "adore-endpoint"
    assert fake.argv[fake.argv.index("--model") + 1] == "qwen/qwen3.5-9b"
    assert "ADORE_ENDPOINT_API_KEY" not in json.dumps(fake.env)
    assert fake.env["PI_CODING_AGENT_DIR"] == CONTAINER_PI_AGENT_DIR


def test_pi_executor_fails_the_stage_when_models_json_cannot_be_placed(tmp_path: Path) -> None:
    """@brief A failed copy fails the gate with a reason and never starts Pi."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    models = {"providers": {"adore-endpoint": {"baseUrl": "http://h/v1",
              "api": "openai-completions", "apiKey": "adore-no-key", "models": [{"id": "m"}]}}}
    run = PiExecutor("pi", "m", provider="custom", models=models).run_gate(
        CopyTarget(fake, copy_ok=False), worktree, io_dir, PROMPT, timeout=30)
    assert not run.ok and run.exit_code == 1 and not run.timed_out
    assert "models.json" in run.stderr
    assert fake.processes == []


def test_native_pi_template_receives_provider_and_model(tmp_path: Path) -> None:
    """@brief A native launch substitutes {model} as provider/model."""
    from adore.util import CommandResult

    def execute(argv, *, timeout=None):
        return CommandResult(exit_code=0)

    worktree, io_dir = _dirs(tmp_path)
    PiExecutor("pi -p --mode json --model {model} {prompt}", "claude-x",
               provider="anthropic").run_gate(execute, worktree, io_dir, PROMPT, timeout=5)
    assert "--model anthropic/claude-x" in (io_dir / GATE_SCRIPT).read_text("utf-8")


# END OF FILE
