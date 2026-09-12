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
@file test_aegis.py
@brief Offline contract tests for the AEGIS companion-CLI client.
@details Covers every supported operation and the untrusted version, JSON,
         schema, task identity, journal, path, stage, exit and timeout inputs.
"""

from __future__ import annotations

# IMPORTS
import json
from pathlib import Path
import shlex

from adore.aegis import (
    AEGIS_CLI,
    AEGIS_SCRIPT,
    AEGIS_STDERR_FILE,
    AEGIS_STDOUT_FILE,
    MAX_JSON_BYTES,
    VERIFY_TIMEOUT,
    AegisClient,
    AegisProtocolError,
    AegisTaskError,
    AegisTimeoutError,
    allowed_transition,
)
from adore.util import CommandResult
import pytest

# CONSTANTS

TASK_ID = "TASK-abc123ef"


# DATA MODELS / TYPEDEFINITIONS


class FakeExec:
    """@brief Scripted container-exec double."""

    def __init__(self, *results: CommandResult) -> None:
        self.results = list(results)
        self.calls: list[list[str]] = []
        self.timeouts: list[float | None] = []

    def __call__(self, argv, *, timeout=None) -> CommandResult:
        self.calls.append(list(argv))
        self.timeouts.append(timeout)
        if not self.results:
            raise AssertionError(f"unexpected AEGIS call: {argv}")
        return self.results.pop(0)


# HELPER FUNCTIONS


def result(
    payload=None,
    *,
    code: int = 0,
    stdout: str = "",
    stderr: str = "",
    timed_out=False,
):
    """@brief Build a captured command result from JSON or explicit text."""
    if payload is not None:
        stdout = json.dumps(payload)
    return CommandResult(
        exit_code=code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
    )


def task_payload(
    *, task_id: str = TASK_ID, stage: str = "frame", path: str = "full",
    branch: str = "adore/run-1", task_type: str = "feature",
):
    """@brief Return one valid schema-1 task-status document."""
    steps = {
        "frame": "1_frame.md",
        "specify": "2_specify.md",
        "design": "3_design.md",
        "build": "4_build.md",
        "validate": "5_validate.md",
        "deliver": "6_deliver.md",
        "done": "6_deliver.md",
    }
    return {
        "schema": 1,
        "command": "status",
        "task": {
            "id": task_id,
            "title": "Implement bounded change",
            "file": f".agentic/tasks/{task_id}.md",
            "header": {
                "stage": stage,
                "type": task_type,
                "path": path,
                "interaction": "checkpoint",
                "requirements": "REQ-FUNC-1",
                "branch": branch,
                "base": "abc123",
                "opened": "2026-08-14T10:00:00Z",
            },
            "stage": stage,
            "step_file": steps[stage],
            "done": stage == "done",
            "checklist": [{"done": True, "item": "Ticket is framed"}],
            "components": [],
            "log": ["2026-08-14: framed"],
        },
    }


def status_list(*, schema: int = 1, unreadable=None, stage: str = "frame"):
    """@brief Return a valid status-list probe document."""
    return {
        "schema": schema,
        "command": "status",
        "tasks": [{
            "id": TASK_ID,
            "title": "Implement bounded change",
            "stage": stage,
            "file": f".agentic/tasks/{TASK_ID}.md",
        }],
        "hidden_done": 0,
        "unreadable": [] if unreadable is None else unreadable,
    }


def check_payload(*, passed: bool = True, warnings: int = 0, runs=None):
    """@brief Return a strict check payload with internally consistent counts."""
    findings = [
        {"level": "WARN", "check": "docs", "path": "README.md", "message": "warn"}
        for _ in range(warnings)
    ]
    return {
        "schema": 1,
        "command": "check",
        "task": TASK_ID,
        "findings": findings,
        "summary": {"errors": 0, "warnings": warnings, "notes": 0},
        "result": "passed" if passed else "failed",
        "run": runs if runs is not None else [{
            "name": "test", "status": "ok", "exit": 0, "seconds": 1.25, "tail": "ok",
        }],
        "strict": {
            "enabled": True,
            "promoted_warnings": 0 if passed else warnings,
            "passed": passed,
        },
    }


# PUBLIC API


def test_probe_accepts_any_supported_minor_and_schema_1() -> None:
    """@brief Version and schema are both proved before work."""
    execute = FakeExec(result(stdout="aegis 0.6.9\n"), result(status_list()))
    probe = AegisClient(execute).probe()
    assert probe.version == "0.6.9" and probe.schema == 1
    assert execute.calls == [
        ["python", ".agentic/aegis.py", "--version"],
        ["python", ".agentic/aegis.py", "status", "--all", "--json"],
    ]


@pytest.mark.parametrize("version", ["aegis 0.5.0", "aegis 0.6.0", "aegis 0.99.7"])
def test_probe_accepts_the_whole_supported_major_from_the_floor_up(
    version: str,
) -> None:
    """
    @brief   A newer AEGIS minor needs no ADORE change.
    @details The supported range is declared once in the client. Anything at or
             above the floor within the major is conducted, so an AEGIS minor
             release does not require editing ADORE at all.
    """
    execute = FakeExec(result(stdout=version), result(status_list()))
    assert AegisClient(execute).probe().schema == 1


@pytest.mark.parametrize("version", ["aegis 1.0.0", "aegis 2.3.4"])
def test_probe_rejects_a_different_major(version: str) -> None:
    """@brief A major bump means the companion contract itself changed."""
    with pytest.raises(AegisProtocolError, match="unsupported"):
        AegisClient(FakeExec(result(stdout=version))).probe()


@pytest.mark.parametrize("version", ["aegis 0.4.9", "aegis 0.0.1"])
def test_probe_rejects_below_the_command_floor(version: str) -> None:
    """
    @brief   A payload older than the floor fails at probe, not mid-stage.
    @details `evolution` arrived in AEGIS 0.5.0 and this client calls it at
             delivery, so an older payload would satisfy a bare major check
             and then fail at the end of a task.
    """
    with pytest.raises(AegisProtocolError, match="at least"):
        AegisClient(FakeExec(result(stdout=version))).probe()


@pytest.mark.parametrize("version", ["0.6.0", "", "aegis", "aegis 0.6"])
def test_probe_rejects_malformed_version_text(version: str) -> None:
    """@brief Version text that is not the documented shape fails closed."""
    with pytest.raises(AegisProtocolError, match="unsupported"):
        AegisClient(FakeExec(result(stdout=version))).probe()


def test_probe_rejects_wrong_schema_and_unreadable_journal() -> None:
    """@brief A bad schema or any corrupt journal prevents pickup."""
    with pytest.raises(AegisProtocolError, match="schema"):
        AegisClient(FakeExec(
            result(stdout="aegis 0.6.0"), result(status_list(schema=2)),
        )).probe()


@pytest.mark.parametrize("stage", ["survey", "components", "close"])
def test_probe_accepts_authoritative_adoption_stages(stage: str) -> None:
    """@brief Repository probing accepts AEGIS adoption journals as foreign work."""
    execute = FakeExec(
        result(stdout="aegis 0.6.0"),
        result(status_list(stage=stage)),
    )
    assert AegisClient(execute).probe().schema == 1


def test_status_probe_still_rejects_an_unknown_stage() -> None:
    """@brief Status-list widening remains bounded to AEGIS's documented stages."""
    with pytest.raises(AegisProtocolError, match="unknown stage"):
        AegisClient(FakeExec(
            result(stdout="aegis 0.6.0"),
            result(status_list(stage="invented")),
        )).probe()
    with pytest.raises(AegisProtocolError, match="unreadable"):
        AegisClient(FakeExec(
            result(stdout="aegis 0.6.0"),
            result(status_list(unreadable=[{"file": "bad.md"}])),
        )).probe()


def test_task_creation_and_status_are_pinned_and_validated() -> None:
    """@brief Task create/status expose only a validated task identity."""
    execute = FakeExec(
        result(stdout=f".agentic/tasks/{TASK_ID}.md\n"),
        result(task_payload()),
    )
    client = AegisClient(execute, "python3")
    assert client.create_task("Implement bounded change", "feature") == TASK_ID
    task = client.task_status(TASK_ID)
    assert task.task_id == TASK_ID
    assert task.stage == "frame" and task.branch == "adore/run-1"
    assert task.requirements == ("REQ-FUNC-1",)
    assert execute.calls[0] == [
        "python3", ".agentic/aegis.py", "task", "Implement bounded change",
        "--type", "feature",
    ]


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (lambda p: p["task"].update(id="TASK-deadbeef"), "pinned task"),
        (lambda p: p["task"].update(stage="unknown"), "stage"),
        (lambda p: p["task"].update(file="../escape.md"), "path"),
        (lambda p: p["task"]["header"].update(branch=""), "branch"),
        (lambda p: p["task"].update(checklist=[{"done": "yes", "item": "x"}]),
         "checklist"),
        (lambda p: p["task"].update(log=[1]), "log"),
    ],
)
def test_task_journal_trust_boundary_fails_closed(mutation, error: str) -> None:
    """@brief Wrong identity, stage, paths, headers, checklist and log are rejected."""
    payload = task_payload()
    mutation(payload)
    with pytest.raises((AegisProtocolError, AegisTaskError), match=error):
        AegisClient(FakeExec(result(payload))).task_status(TASK_ID)


def test_active_task_decoder_rejects_adoption_stage() -> None:
    """@brief ADORE conducts only its seven stages even though probing is wider."""
    payload = task_payload()
    payload["task"]["stage"] = "survey"
    payload["task"]["header"]["stage"] = "survey"
    payload["task"]["step_file"] = "adopt.md"
    with pytest.raises(AegisTaskError, match="stage"):
        AegisClient(FakeExec(result(payload))).task_status(TASK_ID)


def test_task_creation_rejects_path_escape_and_extra_output() -> None:
    """@brief The created task path is exact and singular."""
    for stdout in ("../TASK-abc123ef.md\n", ".agentic/tasks/TASK-abc123ef.md\nnoise\n"):
        with pytest.raises(AegisProtocolError):
            AegisClient(FakeExec(result(stdout=stdout))).create_task("Title", "fix")


def test_container_transport_quotes_title_and_reads_validated_stdout(
    tmp_path: Path,
) -> None:
    """@brief Shell-sensitive ticket text crosses the WSL boundary only in a file."""
    io_dir = tmp_path / "io"
    calls: list[list[str]] = []
    title = "Fix user's $(touch /tmp/pwned) & preserve spaces"

    def execute(argv, *, timeout=None):
        """@brief Simulate the script's bounded stdout/stderr side effects."""
        calls.append(list(argv))
        (io_dir / AEGIS_STDOUT_FILE).write_text(
            f".agentic/tasks/{TASK_ID}.md\n", encoding="utf-8"
        )
        (io_dir / AEGIS_STDERR_FILE).write_text("", encoding="utf-8")
        return CommandResult(exit_code=0, stdout="wrapper output must be ignored")

    client = AegisClient(execute, "python3", io_dir)

    assert client.create_task(title, "fix") == TASK_ID
    assert calls == [["sh", f"/adore/io/{AEGIS_SCRIPT}"]]
    assert all(" " not in token for token in calls[0])
    script = (io_dir / AEGIS_SCRIPT).read_text(encoding="utf-8")
    expected = shlex.join(["python3", AEGIS_CLI, "task", title, "--type", "fix"])
    assert "\r" not in script
    assert expected in script
    assert f"> /adore/io/{AEGIS_STDOUT_FILE}" in script
    assert f"2> /adore/io/{AEGIS_STDERR_FILE}" in script


def test_container_transport_timeout_stays_typed_without_exchange_files(
    tmp_path: Path,
) -> None:
    """@brief A wrapper timeout wins even when the killed command wrote no files."""
    execute = FakeExec(result(code=124, stdout="unrelated", timed_out=True))

    with pytest.raises(AegisTimeoutError):
        AegisClient(execute, io_dir=tmp_path / "io").task_status(TASK_ID)

    assert execute.calls == [["sh", f"/adore/io/{AEGIS_SCRIPT}"]]


def test_container_transport_surfaces_bounded_pre_script_failure(
    tmp_path: Path,
) -> None:
    """@brief A failed container exec retains its real exit and bounded stderr."""
    stderr = "discarded-prefix\n" + ("x" * 1300) + "\nruntime daemon unavailable"
    execute = FakeExec(result(code=127, stderr=stderr))

    with pytest.raises(AegisProtocolError) as raised:
        AegisClient(execute, io_dir=tmp_path / "io").task_status(TASK_ID)

    message = str(raised.value)
    assert "exited 127" in message
    assert "runtime daemon unavailable" in message
    assert "discarded-prefix" not in message
    assert execute.calls == [["sh", f"/adore/io/{AEGIS_SCRIPT}"]]


@pytest.mark.parametrize("failure", ["missing", "unreadable"])
def test_container_transport_requires_readable_exchange_output(
    tmp_path: Path, failure: str,
) -> None:
    """@brief Missing or unreadable stdout fails closed as a typed protocol error."""
    io_dir = tmp_path / "io"

    def execute(argv, *, timeout=None):
        """@brief Leave stdout absent or replace it with an unreadable directory."""
        if failure == "unreadable":
            (io_dir / AEGIS_STDOUT_FILE).mkdir()
        (io_dir / AEGIS_STDERR_FILE).write_text("", encoding="utf-8")
        return CommandResult(exit_code=0)

    with pytest.raises(AegisProtocolError, match="stdout is missing or unreadable"):
        AegisClient(execute, io_dir=io_dir).task_status(TASK_ID)


def test_container_transport_rejects_oversized_exchange_output(tmp_path: Path) -> None:
    """@brief Container output is read with the same finite JSON byte bound."""
    io_dir = tmp_path / "io"

    def execute(argv, *, timeout=None):
        """@brief Write one byte beyond the accepted stdout boundary."""
        (io_dir / AEGIS_STDOUT_FILE).write_bytes(b"x" * (MAX_JSON_BYTES + 1))
        (io_dir / AEGIS_STDERR_FILE).write_text("", encoding="utf-8")
        return CommandResult(exit_code=0)

    with pytest.raises(AegisProtocolError, match="stdout exceeds its size bound"):
        AegisClient(execute, io_dir=io_dir).task_status(TASK_ID)


def test_check_parses_strict_findings_and_executed_commands() -> None:
    """@brief Strict verification preserves one invocation and its command evidence."""
    execute = FakeExec(result(check_payload()))
    check = AegisClient(execute).check(TASK_ID, strict=True, run=True)
    assert check.passed and len(check.executed_runs) == 1
    assert execute.calls[0] == [
        "python", ".agentic/aegis.py", "check", "--task", TASK_ID,
        "--strict", "--run", "--json",
    ]
    assert execute.timeouts == [VERIFY_TIMEOUT]


def test_failed_strict_check_is_data_but_contradiction_is_protocol_error() -> None:
    """@brief Exit one is a valid failed strict result only when JSON agrees."""
    failed = AegisClient(FakeExec(result(
        check_payload(passed=False, warnings=1), code=1,
    ))).check(TASK_ID, strict=True, run=True)
    assert not failed.passed and failed.promoted_warnings == 1
    with pytest.raises(AegisProtocolError, match="disagrees"):
        AegisClient(FakeExec(result(check_payload(), code=1))).check(
            TASK_ID, strict=True
        )


def test_check_rejects_malformed_run_evidence_and_summary_mismatch() -> None:
    """@brief Command records and finding counts are untrusted inputs."""
    malformed = check_payload(runs=[{"name": "test", "status": "ok"}])
    with pytest.raises(AegisProtocolError, match="lacks exit"):
        AegisClient(FakeExec(result(malformed))).check(TASK_ID, strict=True)
    mismatch = check_payload(warnings=1)
    mismatch["summary"]["warnings"] = 0
    with pytest.raises(AegisProtocolError, match="disagrees"):
        AegisClient(FakeExec(result(mismatch))).check(TASK_ID, strict=True)


def test_evolution_and_report_command_shapes() -> None:
    """@brief Every remaining supported AEGIS operation has one exact command."""
    execute = FakeExec(
        result({"schema": 1, "command": "evolution", "task": TASK_ID}),
        result(stdout=f"report appended to .agentic/tasks/{TASK_ID}.md\n"),
    )
    client = AegisClient(execute)
    assert client.evolution(TASK_ID)["command"] == "evolution"
    client.report(TASK_ID)
    assert execute.calls == [
        ["python", ".agentic/aegis.py", "evolution", "--task", TASK_ID, "--json"],
        ["python", ".agentic/aegis.py", "report", TASK_ID],
    ]


@pytest.mark.parametrize("stdout", ["", "not-json", "[]", '{"schema":1'])
def test_json_protocol_rejects_empty_malformed_or_non_object(stdout: str) -> None:
    """@brief The JSON boundary never guesses or accepts partial output."""
    with pytest.raises(AegisProtocolError):
        AegisClient(FakeExec(result(stdout=stdout))).task_status(TASK_ID)


def test_protocol_rejects_invalid_utf8_marker_timeout_and_unexpected_exit() -> None:
    """@brief Decoding replacement, timeout and exit two are distinct loud errors."""
    with pytest.raises(AegisProtocolError, match="invalid UTF-8"):
        AegisClient(FakeExec(result(stdout="\ufffd"))).task_status(TASK_ID)
    with pytest.raises(AegisTimeoutError):
        AegisClient(FakeExec(result(code=124, timed_out=True))).task_status(TASK_ID)
    with pytest.raises(AegisProtocolError, match="exited 2"):
        AegisClient(FakeExec(result(code=2, stdout="usage"))).task_status(TASK_ID)


@pytest.mark.parametrize(
    ("previous", "current", "path", "expected"),
    [
        ("frame", "specify", "full", True),
        ("frame", "build", "quick", True),
        ("validate", "build", "full", True),
        ("validate", "specify", "full", True),
        ("deliver", "validate", "full", True),
        ("frame", "design", "full", False),
        ("build", "frame", "quick", False),
        ("deliver", "build", "full", False),
    ],
)
def test_transition_allowlist(previous: str, current: str, path: str, expected: bool) -> None:
    """@brief Only documented progression and validation rollback are legal."""
    assert allowed_transition(previous, current, path) is expected


# END OF FILE
