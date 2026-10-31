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
@file test_aegis_compatibility.py
@brief Replay captured AEGIS CLI evidence at the supported client boundary.
@details Frozen CLI output with source hashes; all command execution is injected.
         Tests do not depend on a sibling checkout, host CLIs, network or models.
"""

# IMPORTS
from copy import deepcopy
import json
from pathlib import Path

from adore.aegis import AegisClient, AegisProtocolError, AegisTaskError
from adore.util import CommandResult
import pytest

from tests.test_aegis import FakeExec

# CONSTANTS
FIXTURE = Path(__file__).parent / "fixtures/aegis_0_15_0.json"
LEGACY_FIXTURE = Path(__file__).parent / "fixtures/aegis_0_14_0.json"

# PUBLIC CONTRACT TESTS


def test_aegis_015_public_cli_is_compatible():
    """@brief Consume actual new-release responses with the existing typed client."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    task = data["task_id"]
    records = data["records"]
    order = ["version", "list", "create", "frame", "validate", "check"]
    runner = FakeExec(
        *(
            CommandResult(
                exit_code=records[key]["exit_code"],
                stdout=records[key]["stdout"],
                stderr=records[key]["stderr"],
            )
            for key in order
        )
    )
    client = AegisClient(runner)
    assert client.probe().version == "0.15.0"
    assert client.create_task("Compatibility fixture", "change") == task
    assert client.task_status(task).stage == "frame"
    assert client.task_status(task).stage == "validate"
    check = client.check(task, strict=True, run=True)
    assert check.passed and len(check.executed_runs) == 1
    assert runner.calls == [["python", ".agentic/aegis.py", *records[key]["argv"]] for key in order]
    assert "advance, pause, log, ruling, verdict" in data["journal"]
    assert "## State" in data["journal"]


@pytest.mark.parametrize("change", ["schema", "task", "path", "strict", "counts"])
def test_aegis_015_corrupt_output_still_fails_closed(change):
    """@brief Compatibility does not accept corrupt task/check evidence."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    task = data["task_id"]
    key = "frame" if change in {"schema", "task", "path"} else "check"
    payload = deepcopy(json.loads(data["records"][key]["stdout"]))
    if change == "schema":
        payload["schema"] = 2
    elif change == "task":
        payload["task"]["id"] = "TASK-ffffffff"
    elif change == "path":
        payload["task"]["file"] = "../escape.md"
    elif change == "strict":
        payload["strict"]["passed"] = False
    else:
        payload["summary"]["errors"] += 1
    client = AegisClient(FakeExec(CommandResult(exit_code=0, stdout=json.dumps(payload))))
    with pytest.raises(AegisTaskError if change == "task" else AegisProtocolError):
        if change in {"schema", "task", "path"}:
            client.task_status(task)
        else:
            client.check(task, strict=True, run=True)


def test_captured_aegis_014_is_refused_before_status():
    """@brief Historical serialization cannot authorize an unsupported stage flow."""
    data = json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))
    record = data["records"]["version"]
    runner = FakeExec(CommandResult(exit_code=0, stdout=record["stdout"]))
    with pytest.raises(AegisProtocolError, match="0.15.0"):
        AegisClient(runner).probe()
    assert len(runner.calls) == 1


# END OF FILE
