"""Offline tests for driving Pi through its RPC mode."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import subprocess
import sys
import time

from adore import metrics
from adore.branding import (
    CONTAINER_PI_AGENT_DIR,
    CONTAINER_PI_CLI,
    CONTAINER_PI_GUARD,
    CONTAINER_PI_WEB_ACCESS,
)
from adore.execution import ExecutionPaths
from adore.executor.base import GateRun
from adore.executor.launcher import (
    ARCHIVE_DIR,
    GATE_SCRIPT,
    OUTPUT_FILE,
    PiExecutor,
)
from adore.executor.pi_rpc import PiRpcResult, run_pi_rpc
from adore.prompts import PromptCatalog
import pytest

from tests.test_orchestrator import (
    FakeAegis,
    FakeExecutor,
    make_engine,
    make_run,
    task,
)

FAKE = Path(__file__).with_name("fake_pi_rpc.py")
FIXTURES = Path(__file__).parent / "fixtures" / "pi_rpc"
PROMPT = "Implement the stage."
FAST = {"abort_grace": 2.0, "exit_grace": 2.0, "stats_grace": 2.0, "startup_grace": 2.0}



class FakePi:
    """Spawn seam that starts the fake Pi and records what ADORE sent."""

    def __init__(self, tmp_path: Path, fixture: str, *options: str) -> None:
        self.record = tmp_path / f"{fixture}-commands.log"
        self.command = [sys.executable, "-I", str(FAKE), str(FIXTURES / f"{fixture}.jsonl"),
                        "--record", str(self.record), *options]
        self.processes: list[subprocess.Popen] = []
        self.argv: list[str] = []
        self.env: dict[str, str] = {}

    def __call__(self, argv: list[str], env: dict[str, str]) -> subprocess.Popen:
        self.argv, self.env = list(argv), dict(env)
        command = list(self.command)
        if "--session" in argv:
            session = argv[argv.index("--session") + 1]
            host = str(self.record.parent / "io/pi-conversation/session.jsonl")
            command.extend(["--session-file", host, "--session-path", session,
                            "--session-cwd", "/adore/work"])
        process = subprocess.Popen(  # noqa: S603 - fixed test argv
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        self.processes.append(process)
        return process

    def commands(self) -> list[dict]:
        """Commands the fake received, in order."""
        if not self.record.is_file():
            return []
        return [json.loads(line) for line in self.record.read_text("utf-8").splitlines()]

    def all_exited(self) -> bool:
        """Whether every spawned fake process has ended."""
        return all(process.poll() is not None for process in self.processes)


@pytest.mark.parametrize("fault", [False, True])
def test_live_launch_marker_owned_until_archive_and_removed_on_fault(tmp_path, monkeypatch, fault):
    """Only an actual RPC launch advertises live output, including archive handoff."""
    from adore.executor import pi_rpc
    worktree, io_dir = tmp_path / "work", tmp_path / "io"
    worktree.mkdir()
    io_dir.mkdir()
    (io_dir / "output.jsonl").write_text("old output", encoding="utf-8")
    seen = []

    def rpc(*args, **kwargs):
        """Inspect live ownership from inside the injected launch boundary."""
        marker = json.loads((io_dir / "live.json").read_text())
        assert marker["schema"] == 1 and marker["id"].startswith("live-")
        assert marker["archive_id"] == "build-attempt-1-attempt1"
        assert not (io_dir / "output.jsonl").read_bytes()
        seen.append(marker)
        if fault:
            raise OSError("injected spawn fault")
        (io_dir / "output.jsonl").write_text('{}\n', encoding="utf-8")
        return PiRpcResult(outcome="completed", exit_code=0)

    monkeypatch.setattr(pi_rpc, "run_pi_rpc", rpc)
    executor = PiExecutor("m")
    target = SpawnTarget(FakePi(tmp_path, "run_tool_calls_chatgpt"))
    if fault:
        with pytest.raises(OSError, match="injected"):
            executor.run_gate(target, worktree, io_dir, PROMPT, archive_stem="build-attempt-1")
    else:
        result = executor.run_gate(target, worktree, io_dir, PROMPT, archive_stem="build-attempt-1")
        assert Path(result.artifact_dirs[0]).name == seen[0]["archive_id"]
    assert seen and not (io_dir / "live.json").exists()


def test_live_rpc_completed_record_is_readable_before_launch_ends(tmp_path):
    """A short completed prompt reaches disk while the fake Pi still waits."""
    fixture = tmp_path / "live.jsonl"
    fixture.write_text('\n'.join(json.dumps(row) for row in [
        {"dir": "stdin", "record": {"type": "prompt"}},
        {"dir": "stdout", "record": {"type": "message_end", "message": {
            "role": "assistant", "content": [{"type": "text", "text": "VISIBLE_LIVE_PROMPT"}]}}},
    ]) + '\n', encoding="utf-8")
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt", "--hang")
    fake.command = [sys.executable, "-I", str(FAKE), str(fixture), "--hang"]
    output = tmp_path / "output.jsonl"
    observed = False

    def cancel_after_visible():
        """Observe the public evidence file before asking the fake to settle."""
        nonlocal observed
        observed = output.exists() and b"VISIBLE_LIVE_PROMPT" in output.read_bytes()
        return observed

    result = run_pi_rpc(fake, ["pi", "--mode", "rpc"], {}, PROMPT, timeout=2,
                        cancelled=cancel_after_visible, output_path=output, **FAST)
    assert observed and result.outcome == "cancelled"
    assert fake.all_exited()


@pytest.mark.parametrize("kind", ["hardlink", "oversize", "missing", "archive-reparse"])
def test_literal_rpc_archive_refuses_unsafe_recording(tmp_path, monkeypatch, kind):
    """Raw archive copies retain regular-file identity and total-byte bounds."""
    from adore.executor import pi_rpc
    from adore.isolation import IsolationError
    worktree, io_dir = _dirs(tmp_path)
    external = tmp_path / "external"
    external.write_text("outside-recording", encoding="utf-8")

    def rpc(*args, **kwargs):
        """Inject an untrusted recording after the RPC producer boundary."""
        output = kwargs["output_path"]
        output.unlink(missing_ok=True)
        if kind == "hardlink":
            output.hardlink_to(external)
        elif kind == "missing":
            return PiRpcResult(outcome="completed", exit_code=0,
                               output="sanitized operational tail")
        elif kind == "archive-reparse":
            import os
            output.write_bytes(b'{}\n')
            archive = io_dir / ARCHIVE_DIR
            outside = tmp_path / "external-archive"
            outside.mkdir()
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(str(outside), str(archive))
            else:
                archive.symlink_to(outside, target_is_directory=True)
        else:
            with output.open("wb") as handle:
                handle.truncate(pi_rpc.PERSIST_TOTAL_BYTES + 256)
        return PiRpcResult(outcome="completed", exit_code=0)

    monkeypatch.setattr(pi_rpc, "run_pi_rpc", rpc)
    executor = PiExecutor("m")
    target = SpawnTarget(FakePi(tmp_path, "run_tool_calls_chatgpt"))
    if kind == "missing":
        result = executor.run_gate(target, worktree, io_dir, PROMPT,
            archive_stem="build-attempt-1", package_secrets={})
        assert not result.ok and "archive write failed" in result.stderr
        archived = io_dir / ARCHIVE_DIR / "build-attempt-1-attempt1" / OUTPUT_FILE
        assert not archived.exists()
    else:
        with pytest.raises(IsolationError, match="recording|archive"):
            executor.run_gate(target,
            worktree, io_dir, PROMPT, archive_stem="build-attempt-1", package_secrets={})
    if kind == "archive-reparse":
        assert list((tmp_path / "external-archive").iterdir()) == []
        archive = io_dir / ARCHIVE_DIR
        if archive.is_symlink():
            archive.unlink()
        else:
            archive.rmdir()  # Removes only the temporary Windows junction.
    assert external.read_text(encoding="utf-8") == "outside-recording"
    assert not (io_dir / "live.json").exists()


class SpawnTarget:
    """Container-target double: container paths plus the spawn seam."""

    def __init__(self, fake: FakePi) -> None:
        self.paths = ExecutionPaths()
        self.fake = fake

    def spawn(self, argv, *, env=None):
        return self.fake(list(argv), dict(env or {}))

    def __call__(self, argv, *, timeout=None):  # pragma: no cover - not used by RPC
        raise AssertionError("RPC launches must not use the file protocol")




def _run(tmp_path: Path, fixture: str, *options: str, timeout: float | None = 30,
         cancelled: Callable[[], bool] | None = None, **limits) -> tuple[PiRpcResult, FakePi]:
    """Run the client against one fixture with test-sized grace periods."""
    fake = FakePi(tmp_path, fixture, *options)
    result = run_pi_rpc(
        fake, ["pi", "--mode", "rpc"], {}, PROMPT, timeout=timeout, cancelled=cancelled,
        output_path=tmp_path / "output.jsonl", stderr_path=tmp_path / "stderr.log",
        **{**FAST, **limits},
    )
    return result, fake


def _dirs(tmp_path: Path) -> tuple[Path, Path]:
    """Create a worktree and io directory."""
    worktree, io_dir = tmp_path / "work", tmp_path / "io"
    worktree.mkdir()
    io_dir.mkdir()
    return worktree, io_dir




def test_successful_run_with_tool_calls_sums_usage_over_turns(tmp_path: Path) -> None:
    """A recorded four-turn run completes and its turn usage is summed."""
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
    """A crash on exit after a clean `agent_settled` still succeeds."""
    result, _ = _run(tmp_path, "run_tool_calls_chatgpt", "--exit", "3")
    assert result.outcome == "completed" and result.exit_code == 0
    assert result.process_exit == 3


def test_timeout_aborts_and_the_process_is_gone_within_the_grace(tmp_path: Path) -> None:
    """A run that never settles is aborted at the deadline and ends."""
    started = time.monotonic()
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--hang", timeout=0.5)
    elapsed = time.monotonic() - started
    assert result.outcome == "timed-out" and result.timed_out
    assert result.exit_code == 124
    assert "abort" in [command["type"] for command in fake.commands()]
    assert fake.all_exited()
    assert elapsed < 0.5 + FAST["abort_grace"] + FAST["exit_grace"] + FAST["stats_grace"]


def test_timeout_kills_a_process_that_ignores_abort_and_stdin(tmp_path: Path) -> None:
    """A process ignoring `abort` and stdin EOF is terminated after the grace."""
    started = time.monotonic()
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--hang", "--ignore-abort",
                        timeout=0.3, abort_grace=0.5, exit_grace=0.5)
    elapsed = time.monotonic() - started
    assert result.timed_out and result.exit_code == 124
    assert fake.all_exited()
    assert elapsed < 10


def test_cancellation_marker_sends_abort_and_reports_cancelled(tmp_path: Path) -> None:
    """The recorded abort run ends as cancelled, not as success or timeout."""
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
    """Each recorded provider failure maps to its class and a failed launch."""
    result, fake = _run(tmp_path, fixture, "--key-hint", "sk-inval****0000")
    assert result.outcome == "failed" and result.exit_code == 1
    assert not result.timed_out
    assert result.failure == failure
    assert result.message.startswith(f"Pi run failed ({failure}): ")
    assert "****" not in result.message and "sk-inval" not in result.message
    assert fake.all_exited()


def test_crash_before_settling_fails_closed(tmp_path: Path) -> None:
    """A process that exits mid-run is a protocol failure with its code."""
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--crash-after", "6")
    assert result.outcome == "protocol-error"
    assert result.exit_code == 3 and not result.timed_out
    assert "exited before the run settled" in result.message
    assert fake.all_exited()


def test_malformed_stdout_line_fails_closed(tmp_path: Path) -> None:
    """A non-JSON stdout record ends the process and fails the launch."""
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--garbage")
    assert result.outcome == "protocol-error" and result.exit_code != 0
    assert "malformed" in result.message
    assert fake.all_exited()


def test_start_failure_is_a_protocol_failure(tmp_path: Path) -> None:
    """An executable that cannot start yields exit 127 evidence."""
    def spawn(argv, env):
        raise FileNotFoundError("node")

    result = run_pi_rpc(spawn, ["node"], {}, PROMPT, timeout=5, **FAST)
    assert result.outcome == "protocol-error" and result.exit_code == 127
    assert "could not start" in result.message


def test_large_output_stays_bounded(tmp_path: Path) -> None:
    """Many large records and an over-limit record keep evidence bounded."""
    limit = 256 * 1024
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--big-count", "200",
                        "--big-size", "100000", "--oversize", str(limit * 3),
                        max_record_bytes=limit)
    assert result.outcome == "completed" and result.usage.complete
    assert len(result.output.encode("utf-8")) <= 64 * 1024
    assert len(result.stderr.encode("utf-8")) <= 64 * 1024
    persisted = (tmp_path / "output.jsonl").read_bytes().splitlines()
    assert all(len(line) <= 16 * 1024 * 1024 for line in persisted)
    records = [json.loads(line) for line in persisted]
    assert not any(record.get("type") == "message_update" for record in records)
    assert any(record.get("adore_omitted_bytes") for record in records)
    assert result.records_skipped == 1
    assert fake.all_exited()


def test_unreadable_assistant_record_makes_tokens_unavailable(tmp_path: Path) -> None:
    """A skipped assistant `message_end` withdraws the token claim."""
    limit = 256 * 1024
    result, _ = _run(tmp_path, "run_tool_calls_chatgpt", "--pad-message-end",
                     str(limit * 2), max_record_bytes=limit)
    assert result.outcome == "completed"
    assert not result.usage.complete


def test_unreadable_final_assistant_record_fails_closed(tmp_path: Path) -> None:
    """An over-limit last assistant record cannot be read as a success."""
    limit = 256 * 1024
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--pad-message-end",
                        str(limit * 2), "--pad-last", max_record_bytes=limit)
    assert result.outcome == "protocol-error" and result.exit_code != 0
    assert "could not be read" in result.message
    assert fake.all_exited()


def test_deeply_nested_record_is_malformed(tmp_path: Path) -> None:
    """A record too deep to parse fails closed as a malformed record."""
    result, fake = _run(tmp_path, "run_tool_calls_chatgpt", "--deep", "200000")
    assert result.outcome == "protocol-error" and "malformed" in result.message
    assert fake.all_exited()


def test_guard_blocks_publication_commands_in_rpc_mode(tmp_path: Path) -> None:
    """The recorded guard run blocks git push, gh, glab and tea; echo runs."""
    result, _ = _run(tmp_path, "run_guard_blocks_forge")
    assert result.outcome == "completed"
    assert result.tool_calls == 5 and result.blocked_tools == 4


@pytest.mark.parametrize("fault", ["none", "missing", "json", "foreign-id", "cwd",
                                 "version", "hardlink", "binding", "partial", "rpc-path",
                                 "rpc-id", "baseline", "binding-owner", "linked-directory",
                                 "header-only", "missing-binding", "unknown-entry",
                                 "bad-compaction", "bad-compaction-ref", "bad-compaction-tokens",
                                 "bad-compaction-summary", "valid-compaction", "self-compaction"])
def test_pi_executor_launches_an_isolated_rpc_process(tmp_path: Path, fault) -> None:
    """Exact job history resumes across RPC restarts and fails closed on corruption."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    executor = PiExecutor("openai/gpt-5.6-luna")
    run = executor.run_gate(SpawnTarget(fake), worktree, io_dir, PROMPT, timeout=30,
                            archive_stem="build-attempt-1")
    assert run.ok and not run.timed_out
    assert fake.argv[:2] == ["node", CONTAINER_PI_CLI]
    assert "--session" in fake.argv
    assert "--no-session" not in fake.argv and "--continue" not in fake.argv
    for flag in ("--no-approve", "--no-skills", "--no-extensions",
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
    session = io_dir / "pi-conversation/session.jsonl"
    before = session.read_bytes()
    header = json.loads(before.splitlines()[0])
    assert header["cwd"] == "/adore/work"
    assert fake.argv[fake.argv.index("--session") + 1] == (
        "/adore/io/pi-conversation/session.jsonl")
    if fault in {"valid-compaction", "self-compaction"} or fault.startswith("bad-compaction"):
        previous = json.loads(before.splitlines()[-1])["id"]
        kept = "compacted" if fault == "self-compaction" else json.loads(
            before.splitlines()[1])["id"]
        compaction = {"type": "compaction", "id": "compacted", "parentId": previous}
        if fault != "bad-compaction":
            compaction.update(summary="Retain the prior job fact", tokensBefore=1234,
                              firstKeptEntryId=kept)
        if fault == "bad-compaction-ref":
            compaction["firstKeptEntryId"] = "foreign-entry"
        elif fault == "bad-compaction-tokens":
            compaction["tokensBefore"] = True
        elif fault == "bad-compaction-summary":
            compaction["summary"] = None
        session.write_bytes(before + json.dumps(compaction).encode() + b"\n")
        if not fault.startswith("bad-compaction"):
            fault = "none"
    if fault in {"rpc-path", "rpc-id", "baseline"}:
        from adore.isolation import IsolationError
        fake.command.extend(["--bad-session-state", {"rpc-path": "path", "rpc-id": "id",
                                                    "baseline": "tokens"}[fault]])
        if fault == "baseline":
            refused = executor.run_gate(SpawnTarget(fake), worktree, io_dir, "Must not send",
                                        archive_stem="validate-attempt-1", timeout=5)
            assert not refused.ok and "baseline" in refused.stderr
        else:
            with pytest.raises(IsolationError, match="conversation"):
                executor.run_gate(SpawnTarget(fake), worktree, io_dir, "Must not send",
                                  archive_stem="validate-attempt-1", timeout=5)
        assert len([c for c in fake.commands() if c["type"] == "prompt"]) == 1
        assert fake.all_exited()
        return
    if fault != "none":
        if fault == "missing":
            session.unlink()
        elif fault == "json":
            session.write_bytes(before + b"not json\n")
        elif fault in {"foreign-id", "cwd", "version"}:
            key = {"foreign-id": "id", "cwd": "cwd", "version": "version"}[fault]
            header[key] = 2 if fault == "version" else "foreign-job"
            session.write_bytes(json.dumps(header).encode() + b"\n" + before.split(b"\n", 1)[1])
        elif fault == "binding":
            (io_dir / "pi-conversation/binding.json").write_bytes(b'{}')
        elif fault == "missing-binding":
            (io_dir / "pi-conversation/binding.json").unlink()
        elif fault == "header-only":
            session.write_bytes(before.split(b"\n", 1)[0] + b"\n")
        elif fault == "unknown-entry":
            session.write_bytes(before + json.dumps({"type": "unrecognized", "id": "new",
                                                    "parentId": None}).encode() + b"\n")
        elif fault == "binding-owner":
            receipt = io_dir / "pi-conversation/binding.json"
            record = json.loads(receipt.read_text(encoding="utf-8"))
            record["io"] = str(tmp_path / "another-job/io")
            receipt.write_text(json.dumps(record), encoding="utf-8")
        elif fault == "linked-directory":
            import os
            directory = io_dir / "pi-conversation"
            saved = io_dir / "saved-conversation"
            directory.rename(saved)
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(str(saved), str(directory))
            else:
                directory.symlink_to(saved, target_is_directory=True)
        elif fault == "partial":
            session.write_bytes(before[:-2])
        elif fault.startswith("bad-compaction"):
            pass  # Already injected above, through the same public resume boundary.
        else:
            other = tmp_path / "outside.jsonl"
            other.write_bytes(before)
            session.unlink()
            session.hardlink_to(other)
        from adore.isolation import IsolationError
        with pytest.raises(IsolationError, match="conversation"):
            executor.run_gate(SpawnTarget(fake), worktree, io_dir, "Continue",
                              archive_stem="validate-attempt-1", timeout=5)
        assert len(fake.processes) == 1
        if fault == "linked-directory":
            assert (io_dir / "saved-conversation/session.jsonl").read_bytes() == before
            directory = io_dir / "pi-conversation"
            if directory.is_symlink():
                directory.unlink()
            else:
                directory.rmdir()
        return
    second = executor.run_gate(SpawnTarget(fake), worktree, io_dir, "Continue the prior fact",
                               archive_stem="validate-attempt-1", timeout=5)
    assert second.ok and second.tokens_in == run.tokens_in and second.tokens_out == run.tokens_out
    assert "differ" not in second.stderr
    after = session.read_bytes()
    assert after.startswith(before) and json.loads(after.splitlines()[0])["id"] == header["id"]
    assert len(fake.processes) == 2 and fake.all_exited()
    recording = Path(second.artifact_dirs[0]) / OUTPUT_FILE
    events = [json.loads(line) for line in recording.read_text(encoding="utf-8").splitlines()]
    assert len([r for r in events if r.get("type") == "message_end"
                and r.get("message", {}).get("role") == "assistant"]) == 4
    assert [r["text"] for r in events if r.get("type") == "adore_prompt"] == [
        "Continue the prior fact"]


def test_pi_executor_failure_reaches_the_existing_failure_path(tmp_path: Path) -> None:
    """A provider failure is a non-zero, non-timeout gate with its reason."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "failed_invalid_api_key", "--key-hint", "sk-inval****0000")
    run = PiExecutor("openai/gpt-5.4-mini").run_gate(
        SpawnTarget(fake), worktree, io_dir, PROMPT, timeout=30)
    assert not run.ok and not run.timed_out
    assert run.stderr.startswith("Pi run failed (credential): ")
    assert "sk-inval****0000" in (io_dir / OUTPUT_FILE).read_text(encoding="utf-8")
    assert "sk-inval" not in run.output + run.stderr




def test_pi_usage_event_passes_validation_and_reaches_statistics(tmp_path: Path) -> None:
    """The orchestrator journals Pi usage as one valid versioned event."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    gate = PiExecutor("openai/gpt-5.6-luna").run_gate(
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
    """Cancel reaches the executor; the container stop is only a backstop."""
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
    """A gate still running after its cancel grace gets the container stop."""
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
    """Container-target double that also records exec-seam commands."""

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
    """An API-key provider starts Pi with --provider and --model and no models.json."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    target = CopyTarget(fake)
    run = PiExecutor("gpt-5.4", provider="openai", thinking="medium").run_gate(
        target, worktree, io_dir, PROMPT, timeout=30)
    assert run.ok
    assert fake.argv[fake.argv.index("--provider") + 1] == "openai"
    assert fake.argv[fake.argv.index("--model") + 1] == "gpt-5.4"
    assert fake.argv[fake.argv.index("--thinking") + 1] == "medium"
    assert target.commands == [] and not (io_dir / "pi-models.json").exists()
    chatgpt = FakePi(tmp_path, "run_tool_calls_chatgpt")
    assert PiExecutor("gpt-5.6-luna", provider="chatgpt").run_gate(
        SpawnTarget(chatgpt), worktree, io_dir, PROMPT, timeout=30).ok
    assert chatgpt.argv[chatgpt.argv.index("--provider") + 1] == "openai"


def test_pi_executor_writes_the_endpoint_models_json_before_pi_starts(tmp_path: Path) -> None:
    """custom: models.json in io, copied into the agent dir, then Pi on adore-endpoint."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    target = CopyTarget(fake)
    models = {"providers": {"adore-endpoint": {
        "baseUrl": "http://172.27.80.1:1234/v1", "api": "openai-completions",
        "apiKey": "$ADORE_ENDPOINT_API_KEY", "models": [{"id": "qwen/qwen3.5-9b"}]}}}
    run = PiExecutor("qwen/qwen3.5-9b", provider="custom", models=models).run_gate(
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
    """A failed copy fails the gate with a reason and never starts Pi."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    models = {"providers": {"adore-endpoint": {"baseUrl": "http://h/v1",
              "api": "openai-completions", "apiKey": "adore-no-key", "models": [{"id": "m"}]}}}
    run = PiExecutor("m", provider="custom", models=models).run_gate(
        CopyTarget(fake, copy_ok=False), worktree, io_dir, PROMPT, timeout=30)
    assert not run.ok and run.exit_code == 1 and not run.timed_out
    assert "models.json" in run.stderr
    assert fake.processes == []


def test_pi_executor_loads_web_tools_when_internet_is_on(tmp_path: Path) -> None:
    """Internet on: pi-web-access with -e and web-search.json in the agent dir first."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    target = CopyTarget(fake)
    run = PiExecutor("gpt-5.4", provider="openai", internet=True,
                     web_search="brave").run_gate(target, worktree, io_dir, PROMPT, timeout=30)
    assert run.ok
    extensions = [fake.argv[index + 1] for index, part in enumerate(fake.argv) if part == "-e"]
    assert extensions == [CONTAINER_PI_GUARD, CONTAINER_PI_WEB_ACCESS]
    assert "--append-system-prompt" not in fake.argv
    assert target.commands == [["cp", "/adore/io/pi-web-search.json",
                                CONTAINER_PI_AGENT_DIR + "/web-search.json"]]
    document = json.loads((io_dir / "pi-web-search.json").read_text("utf-8"))
    assert document == {"provider": "brave", "workflow": "none", "toolActivation": "eager"}
    none = FakePi(tmp_path, "run_tool_calls_chatgpt")
    quiet = CopyTarget(none)
    assert PiExecutor("gpt-5.4", provider="openai", internet=True,
                      web_search="none").run_gate(quiet, worktree, io_dir, PROMPT, timeout=30).ok
    assert CONTAINER_PI_WEB_ACCESS not in none.argv and quiet.commands == []
    assert "--append-system-prompt" not in none.argv


def test_pi_executor_fails_the_stage_when_web_search_json_cannot_be_placed(
        tmp_path: Path) -> None:
    """A failed web-search.json copy fails the gate with a reason; Pi never starts."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    run = PiExecutor("gpt-5.4", provider="openai", internet=True).run_gate(
        CopyTarget(fake, copy_ok=False), worktree, io_dir, PROMPT, timeout=30)
    assert not run.ok and run.exit_code == 1
    assert "web search configuration could not be placed" in run.stderr
    assert fake.processes == []


def test_pi_executor_tells_the_agent_when_internet_is_off(tmp_path: Path) -> None:
    """Internet off: no web extension, no web-search.json, a system-prompt notice."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    target = CopyTarget(fake)
    assert PiExecutor("gpt-5.4", provider="openai").run_gate(
        target, worktree, io_dir, PROMPT, timeout=30).ok
    assert CONTAINER_PI_WEB_ACCESS not in fake.argv and target.commands == []
    notice = fake.argv[fake.argv.index("--append-system-prompt") + 1]
    assert notice == PromptCatalog().render("system/internet-off.md")
    assert "only the model provider" in notice.lower()
    for word in ("web search", "page", "download"):
        assert word in notice.lower()




@pytest.mark.parametrize("package", [False, True])
def test_pi_rpc_package_retention_keeps_usage_and_literal_session_archive(tmp_path, package):
    """RPC sessions keep literal bounded events while operational tails stay safe."""
    worktree, io_dir = _dirs(tmp_path)
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt", "--big-count", "4",
                  "--big-size", "40000", "--key-hint", "private-test-value")
    fixture = tmp_path / "literal-package.jsonl"
    rows = [json.loads(line) for line in (FIXTURES / "run_tool_calls_chatgpt.jsonl")
            .read_text(encoding="utf-8").splitlines()]
    index = next(index for index, row in enumerate(rows)
                 if row["dir"] == "stdout" and row["record"].get("type") == "agent_settled")
    rows.insert(index, {"dir": "stdout", "record": {"type": "message_end", "message": {
        "role": "toolResult", "content": [{"type": "text", "text": "private-test-value"}]}}})
    fixture.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    fake.command[3] = str(fixture)
    target = SpawnTarget(fake)
    target.redact = lambda text: text.replace("private-test-value", "[REDACTED]")
    options = {"package_secrets": {"KEY": "private-test-value"}} if package else {}
    run = PiExecutor("m").run_gate(
        target, worktree, io_dir, PROMPT,
        timeout=30, archive_stem="packages", **options)
    assert run.ok and run.tokens_reported
    assert (run.tokens_in, run.tokens_out) == (5275, 141)
    archive = Path(run.artifact_dirs[0])
    for root in (io_dir, archive):
        assert (root / "output.jsonl").stat().st_size > 65536
        assert b"private-test-value" in (root / "output.jsonl").read_bytes()
        assert b"private-test-value" not in (root / "stderr.log").read_bytes()
    assert "private-test-value" not in run.output + run.stderr
    assert fake.all_exited()


@pytest.mark.parametrize("package", [False, True])
@pytest.mark.parametrize("long", [False, True])
def test_rpc_questions_apply_bound_credentials_and_package_retention(tmp_path, monkeypatch,
                                                                   package, long):
    """RPC clarification text is safe before it reaches publication or journals."""
    from adore.executor import pi_rpc

    worktree, io_dir = _dirs(tmp_path)
    target = SpawnTarget(FakePi(tmp_path, "run_tool_calls_chatgpt"))
    target.redact = lambda text: text.replace("binding-only-token", "[REDACTED]")
    executor = PiExecutor("m")
    path = worktree / executor.questions_file
    body = "Clarify binding-only-token and literal-test-credential?"
    body += "x" * 100000 if long else ""

    def rpc(*args, **kwargs):
        path.write_text(body, encoding="utf-8")
        return pi_rpc.PiRpcResult(outcome="completed", exit_code=0)

    monkeypatch.setattr(pi_rpc, "run_pi_rpc", rpc)
    options = {"package_secrets": {"KEY": "literal-test-credential"}} if package else {}
    run = executor.run_gate(target, worktree, io_dir, PROMPT, **options)
    assert run.ok and run.has_questions and "Clarify" in run.questions
    assert "binding-only-token" not in run.questions
    if package:
        assert "literal-test-credential" not in run.questions
        assert len(run.questions.encode("utf-8")) <= 65536
        assert path.read_text(encoding="utf-8") == run.questions
    else:
        assert (len(run.questions) > 65536) is long


def test_package_rpc_questions_refuse_a_linked_file(tmp_path, monkeypatch):
    """An agent-controlled link cannot redirect host-side question retention."""
    import stat
    from types import SimpleNamespace

    from adore.executor import pi_rpc
    from adore.isolation import IsolationError

    worktree, io_dir = _dirs(tmp_path)
    executor = PiExecutor("m")
    path = worktree / executor.questions_file
    original = Path.lstat

    def lstat(candidate, *args, **kwargs):
        if candidate == path:
            return SimpleNamespace(st_mode=stat.S_IFLNK)
        return original(candidate, *args, **kwargs)

    def rpc(*args, **kwargs):
        path.write_text("PRIVATE host content", encoding="utf-8")
        monkeypatch.setattr(Path, "lstat", lstat)
        return pi_rpc.PiRpcResult(outcome="completed", exit_code=0)

    monkeypatch.setattr(pi_rpc, "run_pi_rpc", rpc)
    with pytest.raises(IsolationError, match="linked"):
        executor.run_gate(SpawnTarget(FakePi(tmp_path, "run_tool_calls_chatgpt")),
                          worktree, io_dir, PROMPT, package_secrets={})


def test_package_rpc_questions_redact_credentials_across_binding_cap(tmp_path, monkeypatch):
    """A binding's own byte cap cannot expose a partial package credential."""
    from adore.execution import redact_output
    from adore.executor import pi_rpc

    worktree, io_dir = _dirs(tmp_path)
    executor = PiExecutor("m")
    target = SpawnTarget(FakePi(tmp_path, "run_tool_calls_chatgpt"))
    target.redact = lambda text: redact_output(text, {})
    secret = "literal-test-credential" + "s" * 1000

    def rpc(*args, **kwargs):
        (worktree / executor.questions_file).write_text("x" * 65000 + secret, encoding="utf-8")
        return pi_rpc.PiRpcResult(outcome="completed", exit_code=0)

    monkeypatch.setattr(pi_rpc, "run_pi_rpc", rpc)
    run = executor.run_gate(target, worktree, io_dir, PROMPT, package_secrets={"KEY": secret})
    assert "literal-test-credential" not in run.questions
    assert len(run.questions.encode("utf-8")) <= 65536




def test_rpc_retains_concrete_operational_diagnostics_without_private_content(tmp_path):
    """Host normalization keeps concrete failures and test counts, never transcripts."""
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    fixture = tmp_path / "diagnostics.jsonl"
    records = [
        ("stdin", {"type": "prompt"}),
        ("stdout", {"type": "response", "command": "prompt", "success": True,
                    "data": {"disposition": "started"}}),
        ("stdout", {"type": "tool_execution_end", "isError": True,
                    "result": {"content": [{"type": "text", "text":
                    "ModuleNotFoundError: No module named 'yaml'\n1 failed, 2 passed\n"
                    "ModuleNotFoundError: No module named 'ghp_ABCDEFGHIJKLMNOPQRST'\n"
                    "ModuleNotFoundError: No module named 'configured_secret'\n"
                    "api_key=PRIVATE_KEY\nPRIVATE_CONFIG\nPRIVATE_SCRIPT\n"
                    "private_price = '31 passed'"}]}}),
        ("stderr", "ModuleNotFoundError: No module named 'yaml'\nPRIVATE_KEY"),
        ("stdout", {"type": "message_end", "message": {"role": "assistant",
                    "content": [{"type": "thinking", "thinking": "PRIVATE_REASONING"},
                                {"type": "text", "text": "PRIVATE_PROMPT"}],
                    "stopReason": "error", "errorMessage": "401 invalid_api_key PRIVATE_KEY"}}),
        ("stdout", {"type": "agent_settled", "aborted": False}),
    ]
    fixture.write_text("".join(json.dumps({"dir": direction, "record": record})+"\n"
                               for direction, record in records), encoding="utf-8")
    fake.command[3] = str(fixture)
    result = run_pi_rpc(fake, ["pi", "--mode", "rpc"], {}, PROMPT, timeout=10,
                        redact=lambda text: text.replace("configured_secret", "[REDACTED]"), **FAST)
    assert "ModuleNotFoundError: No module named 'yaml'" in result.diagnostics["stdout"]
    assert "pytest: 1 failed, 2 passed" in result.diagnostics["stdout"]
    assert "ModuleNotFoundError" in result.diagnostics["stderr"]
    assert "PRIVATE_" not in str(result.diagnostics)
    assert "ghp_" not in str(result.diagnostics)
    assert "configured_secret" not in str(result.diagnostics)
    assert "31 passed" not in str(result.diagnostics)


def test_public_retry_binds_host_diagnostics_to_launch_journal(tmp_path, monkeypatch):
    """Public recovery binds an immutable host snapshot to its launch digest."""
    from hashlib import sha256

    gate = GateRun(exit_code=0, has_questions=True, questions="Need input",
                   artifact_dirs=[str(tmp_path / "archive")],
                   diagnostics={"stdout": "ModuleNotFoundError: No module named 'yaml'",
                                "stderr": "pytest: 1 failed, 2 passed"})
    engine, *_ = make_engine(tmp_path, executor=FakeExecutor(gate))
    run = make_run(engine)
    run.lifecycle = "failed"
    engine.store.save(run)
    client = FakeAegis([task("frame")])
    client.probe = lambda: None
    monkeypatch.setattr("adore.orchestrator.AegisClient", lambda *args: client)
    assert engine.retry(run.run_id)
    events = engine.store.read_journal(run.run_id)
    event = next(row for row in events if row["event"] == "executor-artifacts")
    reference = event["diagnostics"]
    snapshot_path = engine.store.run_dir(run.run_id) / "executor-diagnostics" / reference["file"]
    raw = snapshot_path.read_bytes()
    assert sha256(raw).hexdigest() == reference["sha256"]
    snapshot = json.loads(raw)
    assert snapshot["attempt"] == reference["attempt"] == 1
    assert snapshot["run_id"] == run.run_id and snapshot["context"] == "frame"
    assert snapshot["stdout"] == gate.diagnostics["stdout"]
    assert engine.store.load(run.run_id).lifecycle == "parked-clarification"

    # A completed later attempt without archive/capture must supersede the older snapshot.
    saved = engine.store.load(run.run_id)
    saved.lifecycle = "failed"
    engine.store.save(saved)
    engine.executor.results.append(GateRun(exit_code=1, has_questions=True, questions="Need input"))
    assert engine.retry(run.run_id)
    latest = [event for event in engine.store.read_journal(run.run_id)
              if event["event"] == "executor-artifacts"][-1]
    assert latest["diagnostics"] is None and latest["artifacts"] == []


def test_rpc_snapshots_diagnostics_while_a_delayed_reader_outlives_join(tmp_path, monkeypatch):
    """A bounded delayed pipe cannot race or stall the public diagnostic snapshot."""
    from threading import Event

    from adore.executor import pi_rpc

    release, finished = Event(), Event()
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    original_pipe = None

    class DelayedPipe:
        """Inject a reader that remains alive after the child's bounded join."""
        first = True

        def read(self, _limit):
            if self.first:
                self.first = False
                release.wait(2)
                return b"ModuleNotFoundError: No module named 'yaml'\nPRIVATE_KEY\n"
            finished.set()
            return b""

        read1 = read

        def close(self):
            original_pipe.close()

    def spawn(argv, env):
        nonlocal original_pipe
        process = fake(argv, env)
        original_pipe = process.stderr
        process.stderr = DelayedPipe()
        return process

    monkeypatch.setattr(pi_rpc, "KILL_GRACE_SECONDS", 0.02)
    try:
        result = run_pi_rpc(spawn, ["pi", "--mode", "rpc"], {}, PROMPT, timeout=10, **FAST)
        assert result.outcome == "completed"
        assert result.diagnostics["stdout"].endswith("RPC completed")
        assert "PRIVATE_" not in str(result.diagnostics)
        assert not finished.is_set()  # the snapshot was taken with a reader still pending
    finally:
        release.set()
        assert finished.wait(2)
        if original_pipe is not None:
            original_pipe.close()


def test_public_diagnostic_normalizer_bounds_canonical_records():
    """Long operational results keep complete records inside the declared limits."""
    from adore.executor.diagnostics import normalize_diagnostics, validate_diagnostics
    from adore.state import StateError

    text = normalize_diagnostics("ModuleNotFoundError: No module named 'yaml'\n" * 2000)
    assert len(text.splitlines()) == 500 and len(text.encode("utf-8")) <= 65536
    assert validate_diagnostics({"stdout": text, "stderr": ""})["stdout"] == text
    for invalid in ({"stdout": text + "\nraw_private_value", "stderr": ""},
                    {"stdout": 1, "stderr": ""},
                    {"stdout": text + "\n" + text, "stderr": ""}):
        with pytest.raises(StateError):
            validate_diagnostics(invalid)


@pytest.mark.parametrize("ack", ["success", "rejected", "wrong-command", "missing"])
def test_live_instruction_rpc_acknowledgement_and_restart(tmp_path, ack):
    """The sole RPC writer steers/follows up; false or absent ack retains text."""
    import inspect

    from adore.instructions import InstructionDelivery, InstructionInbox

    assert "instructions" in inspect.signature(run_pi_rpc).parameters, "RPC inbox polling missing"
    root = tmp_path / "runs" / "one"
    root.mkdir(parents=True)
    box = InstructionInbox(root)
    delivery = InstructionDelivery(box, PromptCatalog())

    def response(command, **values):
        """Build a synthetic command acknowledgement."""
        return {"type": "response", "command": command, "success": True, **values}

    segments = [
        {"dir": "stdin", "record": {"type": "prompt"}},
        {"dir": "stdout", "record": response("prompt", data={"disposition": "started"})},
        {"dir": "stdin", "record": {"type": "steer"}},
        {
            "dir": "stdout",
            "record": response(
                "steer" if ack != "wrong-command" else "follow_up", success=ack != "rejected"
            ),
        },
        {
            "dir": "stdout",
            "record": {
                "type": "message_end",
                "message": {"role": "user", "content": "NOW_LITERAL"},
            },
        },
        {"dir": "stdin", "record": {"type": "follow_up"}},
        {"dir": "stdout", "record": response("follow_up")},
        {
            "dir": "stdout",
            "record": {
                "type": "message_end",
                "message": {"role": "user", "content": "AFTER_LITERAL"},
            },
        },
        {"dir": "stdout", "record": {"type": "agent_settled", "aborted": False}},
        {"dir": "stdin", "record": {"type": "get_session_stats"}},
        {"dir": "stdout", "record": response("get_session_stats")},
    ]
    if ack == "missing":
        segments.pop(3)
    fixture = tmp_path / "instruction-rpc.jsonl"
    fixture.write_text("\n".join(json.dumps(row) for row in segments) + "\n", encoding="utf-8")
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    fake.command = [sys.executable, "-I", str(FAKE), str(fixture), "--record", str(fake.record)]
    queued = []

    def queue_during_session():
        """Enqueue only after the fake has received the initial stage prompt."""
        if not queued and fake.commands():
            queued.extend(
                [
                    box.enqueue({"id": 7, "username": "operator"}, "  NOW_LITERAL $text\n", "now"),
                    box.enqueue({"id": 7, "username": "operator"}, "AFTER_LITERAL", "after"),
                ]
            )
        return False

    result = run_pi_rpc(
        fake,
        ["pi"],
        {},
        PROMPT,
        timeout=3,
        cancelled=queue_during_session,
        instructions=delivery,
        output_path=root / "output.jsonl",
        **FAST,
    )
    assert result.exit_code == 0 and fake.all_exited()
    commands = fake.commands()
    assert [row["type"] for row in commands] == [
        "prompt",
        "steer",
        "follow_up",
        "get_session_stats",
    ]
    assert (
        "  NOW_LITERAL $text\n" in commands[1]["message"] and "operator" in commands[1]["message"]
    )
    rows = {row["id"]: row for row in InstructionInbox(root).read()[0]}
    assert bool(rows[queued[0]["id"]]["delivery"]) is (ack == "success")
    assert rows[queued[1]["id"]]["delivery"]["how"] == "follow_up"
    if ack != "success":
        restarted = InstructionDelivery(InstructionInbox(root), PromptCatalog())
        assert "NOW_LITERAL" in restarted.suffix and "AFTER_LITERAL" not in restarted.suffix


@pytest.mark.parametrize("fault", ["spawn", "reject", "early-exit", "accepted"])
def test_prompt_fallback_receipt_requires_actual_pi_acceptance(tmp_path, fault):
    """Fallback prompt composition and failed startup never consume an instruction."""
    import inspect

    from adore.instructions import InstructionDelivery, InstructionInbox

    assert "instructions" in inspect.signature(run_pi_rpc).parameters, "RPC prompt receipt missing"
    root = tmp_path / "runs" / "one"
    root.mkdir(parents=True)
    box = InstructionInbox(root)
    box.enqueue({"id": 7, "username": "operator"}, "PENDING_LITERAL", "now")
    delivery = InstructionDelivery(box, PromptCatalog())
    fixture = "run_tool_calls_chatgpt" if fault == "accepted" else "failed_invalid_api_key"
    fake = FakePi(tmp_path, fixture)
    if fault in ("reject", "early-exit"):
        rejected = tmp_path / "rejected.jsonl"
        records = [{"dir": "stdin", "record": {"type": "prompt"}}]
        if fault == "reject":
            records.append(
                {
                    "dir": "stdout",
                    "record": {
                        "id": "initial",
                        "type": "response",
                        "command": "prompt",
                        "success": False,
                        "error": "rejected",
                    },
                }
            )
        else:
            records.append({"dir": "stdout", "record": {"type": "agent_start"}})
        rejected.write_text("\n".join(json.dumps(row) for row in records) + "\n")
        fake.command = [sys.executable, "-I", str(FAKE), str(rejected), "--crash-after", "1"]
    if fault == "spawn":

        def spawn(*args):
            raise FileNotFoundError("fake missing Pi")
    else:
        spawn = fake
    result = run_pi_rpc(
        spawn, ["pi"], {}, PROMPT + delivery.suffix, instructions=delivery, timeout=3, **FAST
    )
    assert (result.exit_code == 0) is (fault == "accepted")
    assert bool(box.read()[0][0]["delivery"]) is (fault == "accepted")



def test_cancellation_takes_precedence_over_live_instruction_dispatch(tmp_path):
    """Cancel retains newly queued text without sending steer or follow_up."""
    from adore.instructions import InstructionDelivery, InstructionInbox

    root = tmp_path / "runs" / "one"
    root.mkdir(parents=True)
    box = InstructionInbox(root)
    delivery = InstructionDelivery(box, PromptCatalog())
    fake = FakePi(tmp_path, "run_aborted_chatgpt", "--hang")
    queued = []

    def cancel():
        """Simulate an instruction arriving at the same boundary as cancellation."""
        if not queued:
            queued.append(box.enqueue({"id": 7, "username": "operator"}, "Pending", "now"))
        return True

    result = run_pi_rpc(fake, ["pi"], {}, PROMPT, instructions=delivery,
                        cancelled=cancel, timeout=3, **FAST)
    assert result.outcome == "cancelled" and fake.all_exited()
    assert not any(row["type"] in ("steer", "follow_up") for row in fake.commands())
    assert box.read()[0][0]["delivery"] is None
