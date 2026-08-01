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
@brief Tests for the AEGIS 2.x client (envelope parsing and command shape).
@details Trust-boundary coverage for everything crossing into ADORE from the
         AEGIS CLI: the happy envelope, blocked/failed governance signals,
         `--run` pinning, run-id capture, and every fail-loud path (exit 2,
         timeout, unparseable JSON, non-object payload, missing or mistyped
         envelope keys, status/exit-code contradictions). The exec seam is a
         fake, so nothing here touches bash, docker, or a real payload.
@author Eng. Dan Dumitru Pasare
@date 2026-08-01
@version 0.2.0
"""

from __future__ import annotations

# IMPORTS
import json

from adore.aegis import (
    AegisClient,
    AegisProtocolError,
    AegisTimeoutError,
    VERIFY_TIMEOUT,
)
from adore.util import CommandResult
import pytest

# CONSTANTS

RUN_ID = "feature-2026-08-01T101112Z-0a1b2c3d"

# DATA MODELS / TYPEDEFINITIONS


class FakeExec:
    """
    @brief   Exec-seam double replaying scripted results and recording argv.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-08-01
    @version 0.1.0
    """

    def __init__(self, *results: CommandResult) -> None:
        """
        @brief      Script one or more results (the last one repeats).
        @param[in]  results Results returned in order.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        self.results = list(results) or [CommandResult(exit_code=0, stdout="{}")]
        self.calls: list[list[str]] = []
        self.timeouts: list[float | None] = []

    def __call__(self, argv, *, timeout=None) -> CommandResult:
        """
        @brief      Record the invocation and return the next scripted result.
        @param[in]  argv Command tokens.
        @param[in]  timeout Wall-clock bound requested by the client.
        @return     The next CommandResult.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-08-01
        @version    0.1.0
        """
        self.calls.append([str(part) for part in argv])
        self.timeouts.append(timeout)
        return self.results.pop(0) if len(self.results) > 1 else self.results[0]


# HELPER FUNCTIONS


def envelope(**extras) -> str:
    """
    @brief      Render a conforming AEGIS `--json` envelope.
    @param[in]  extras Envelope overrides and command-specific extras.
    @return     The JSON text an AEGIS command would print.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-08-01
    @version    0.1.0
    """
    payload = {
        "status": "ok",
        "stage": "intake",
        "artifact": ".agentic/runs/x/stages/intake/stage.toml",
        "next": "aegis stage apply",
    }
    payload.update(extras)
    return json.dumps(payload)


def client(*results: CommandResult, run_id: str = RUN_ID) -> tuple[AegisClient, FakeExec]:
    """
    @brief      Build a client over a scripted fake exec seam.
    @param[in]  results Scripted results.
    @param[in]  run_id Pinned AEGIS run id ("" for an unstarted run).
    @return     (client, fake exec seam).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-08-01
    @version    0.1.0
    """
    execute = FakeExec(*results)
    return AegisClient(execute, run_id=run_id), execute


# PUBLIC API / TESTS


def test_envelope_happy_path_is_parsed_and_run_pinned() -> None:
    """
    @brief   A successful command yields the four envelope fields plus extras,
             and the argv pins `--run` and `--json` as single tokens.
    @version 0.1.0
    """
    aegis, execute = client(
        CommandResult(exit_code=0, stdout=envelope(stage="design", complete=False))
    )
    response = aegis.run_status()
    assert response.ok and not response.blocked and not response.failed
    assert response.stage == "design"
    assert response.next_command == "aegis stage apply"
    assert response.artifact.endswith("stage.toml")
    assert response.complete is False
    assert execute.calls == [[
        "bash", ".agentic/tools/run.sh", "run", "status", "--run", RUN_ID, "--json",
    ]]
    assert all(" " not in token for token in execute.calls[0])


def test_blocked_envelope_exposes_error_code_and_remediation() -> None:
    """
    @brief   A typed governance block is data, not an exception; the stable
             code is recovered from inside the `error` text and the
             remediation from its tail (contract notes 11.3).
    @version 0.1.0
    """
    aegis, _ = client(
        CommandResult(
            exit_code=1,
            stdout=envelope(
                status="blocked",
                next="aegis stage prepare",
                error=(
                    "RUN-POINTER-STALE: the selected run no longer exists.\n"
                    "Run `aegis run select <run-id>` with a valid run."
                ),
            ),
        )
    )
    response = aegis.stage_show()
    assert response.blocked
    assert response.code == "RUN-POINTER-STALE"
    assert response.remediation.startswith("Run `aegis run select")


def test_declared_configuration_code_wins_over_text_scan() -> None:
    """
    @brief   Configuration errors carry structured `code`/`remediation`
             fields; those are preferred over scanning the message.
    @version 0.1.0
    """
    aegis, _ = client(
        CommandResult(
            exit_code=1,
            stdout=envelope(
                status="blocked",
                stage="none",
                error="workflow.toml: gates.test.mode must be enforce or disabled",
                code="WORKFLOW-INVALID-ENUM",
                key_path="gates.test.mode",
                remediation="Set gates.test.mode to enforce or disabled.",
            ),
        )
    )
    response = aegis.config_validate()
    assert response.code == "WORKFLOW-INVALID-ENUM"
    assert response.remediation == "Set gates.test.mode to enforce or disabled."


def test_failed_verification_is_data_with_the_summary_extra() -> None:
    """
    @brief   `verify run` exiting 1 with `status: failed` is a normal outcome
             carrying the validation summary, and gets the long timeout.
    @version 0.1.0
    """
    summary = {"gates": {"test": {"status": "failed"}}}
    aegis, execute = client(
        CommandResult(
            exit_code=1,
            stdout=envelope(
                status="failed",
                stage="validation",
                artifact=".agentic/runs/x/validation-summary.json",
                next="aegis verify run",
                verification=summary,
            ),
        )
    )
    response = aegis.verify_run()
    assert response.failed and not response.ok
    assert response.detail("verification") == summary
    assert execute.timeouts == [VERIFY_TIMEOUT]


def test_run_start_captures_and_pins_the_run_id() -> None:
    """
    @brief   `run start` carries no `--run`; the minted id is captured and
             every later call pins it.
    @version 0.1.0
    """
    started = envelope(next="aegis stage apply", run_id=RUN_ID, kind="feature")
    aegis, execute = client(
        CommandResult(exit_code=0, stdout=started),
        CommandResult(exit_code=0, stdout=envelope()),
        run_id="",
    )
    response = aegis.run_start("feature")
    assert response.ok and aegis.run_id == RUN_ID
    assert "--run" not in execute.calls[0]
    aegis.stage_show()
    assert execute.calls[1][-3:] == ["--run", RUN_ID, "--json"]


def test_quick_run_start_passes_the_profile_flag() -> None:
    """
    @brief   A quick fix run adds `--quick` before the global options.
    @version 0.1.0
    """
    aegis, execute = client(
        CommandResult(
            exit_code=0,
            stdout=envelope(
                run_id="fix-2026-08-01T101112Z-0a1b2c3d", run_profile="quick"
            ),
        ),
        run_id="",
    )
    aegis.run_start("fix", quick=True)
    assert execute.calls[0] == [
        "bash", ".agentic/tools/run.sh", "run", "start", "fix", "--quick", "--json",
    ]


def test_quick_is_rejected_for_kinds_aegis_does_not_allow() -> None:
    """
    @brief   Building `--quick feature` is an ADORE defect and fails before it
             ever reaches the payload.
    @version 0.1.0
    """
    aegis, execute = client(run_id="")
    with pytest.raises(AegisProtocolError, match="only valid for fix and change"):
        aegis.run_start("feature", quick=True)
    with pytest.raises(AegisProtocolError, match="unsupported AEGIS run kind"):
        aegis.run_start("refactor")
    assert execute.calls == []


def test_run_start_without_a_usable_run_id_fails_loud() -> None:
    """
    @brief   A successful start whose `run_id` is missing or malformed is a
             broken payload, never a run ADORE proceeds with blindly.
    @version 0.1.0
    """
    aegis, _ = client(
        CommandResult(exit_code=0, stdout=envelope(run_id="../escape")), run_id=""
    )
    with pytest.raises(AegisProtocolError, match="did not return a usable run id"):
        aegis.run_start("fix")
    assert aegis.run_id == ""

    aegis, _ = client(CommandResult(exit_code=0, stdout=envelope()), run_id="")
    with pytest.raises(AegisProtocolError, match="did not return a usable run id"):
        aegis.run_start("fix")


def test_run_scoped_command_without_a_run_id_fails_loud() -> None:
    """
    @brief   No AEGIS run means no run-scoped command; ADORE refuses to fall
             back on the worktree pointer.
    @version 0.1.0
    """
    aegis, execute = client(run_id="")
    with pytest.raises(AegisProtocolError, match="without an AEGIS run id"):
        aegis.stage_close()
    assert execute.calls == []


def test_exit_two_raises_instead_of_becoming_a_workflow_state() -> None:
    """
    @brief   Exit 2 is a usage error or a wrapper that found no Python - an
             ADORE/payload defect, and the plain-text output must not be
             mistaken for an envelope.
    @version 0.1.0
    """
    aegis, _ = client(
        CommandResult(
            exit_code=2,
            stderr="No AEGIS Python runtime is available. Set AEGIS_PYTHON.",
        )
    )
    with pytest.raises(AegisProtocolError, match="outside the supported 0/1 contract"):
        aegis.run_status()


def test_timeout_exit_code_raises_a_distinct_timeout_error() -> None:
    """
    @brief   A wall-clock timeout is not a contract violation; it gets its own
             typed error so escalation can name the command. Keyed on the
             seam's `timed_out` flag, not the raw exit code (ADORE-ARCH-010).
    @version 0.2.0
    """
    aegis, _ = client(CommandResult(exit_code=124, stderr="timeout after 1800s",
                                    timed_out=True))
    with pytest.raises(AegisTimeoutError, match="timed out"):
        aegis.verify_run()


def test_inner_exit_124_is_a_protocol_error_not_a_timeout() -> None:
    """
    @brief   A genuine INNER exit 124 from the payload (not ADORE's own
             wrapper timeout - `timed_out` is False because `docker exec`
             completed normally within its bound and merely propagated the
             payload's own exit code) must not be misreported as ADORE's
             timeout: it is an ordinary exit-code-outside-0/1 protocol
             error naming the exit code (ADORE-ARCH-010).
    @version 0.1.0
    """
    aegis, _ = client(CommandResult(exit_code=124, stdout='{"status": "ok"}',
                                    stderr="payload used exit code 124"))
    with pytest.raises(AegisProtocolError, match="exited 124"):
        aegis.verify_run()


def test_malformed_json_raises() -> None:
    """
    @brief   Unparseable output fails closed rather than degrading to an empty
             brief or a skipped check.
    @version 0.1.0
    """
    aegis, _ = client(CommandResult(exit_code=0, stdout="status: ok\nstage: intake\n"))
    with pytest.raises(AegisProtocolError, match="unparseable JSON"):
        aegis.run_status()


def test_non_object_payload_raises() -> None:
    """
    @brief   A JSON array is valid JSON but not the documented envelope.
    @version 0.1.0
    """
    aegis, _ = client(CommandResult(exit_code=0, stdout='["ok"]'))
    with pytest.raises(AegisProtocolError, match="non-object payload"):
        aegis.run_status()


def test_missing_and_mistyped_envelope_keys_raise() -> None:
    """
    @brief   Every one of the four envelope keys must be present and a string.
    @version 0.1.0
    """
    aegis, _ = client(
        CommandResult(
            exit_code=0,
            stdout=json.dumps({"status": "ok", "stage": "intake", "next": "none"}),
        )
    )
    with pytest.raises(AegisProtocolError, match="missing the envelope key 'artifact'"):
        aegis.run_status()

    aegis, _ = client(CommandResult(exit_code=0, stdout=envelope(stage=3)))
    with pytest.raises(AegisProtocolError, match="non-string 'stage'"):
        aegis.run_status()


def test_unknown_status_and_exit_code_contradictions_raise() -> None:
    """
    @brief   An unknown status, an exit-0 non-ok response, or an exit-1 'ok'
             response all mean the contract moved; fail loud.
    @version 0.1.0
    """
    aegis, _ = client(CommandResult(exit_code=0, stdout=envelope(status="degraded")))
    with pytest.raises(AegisProtocolError, match="unknown status"):
        aegis.run_status()

    aegis, _ = client(CommandResult(exit_code=0, stdout=envelope(status="blocked")))
    with pytest.raises(AegisProtocolError, match="exited 0 .* but reported status"):
        aegis.run_status()

    aegis, _ = client(CommandResult(exit_code=1, stdout=envelope()))
    with pytest.raises(AegisProtocolError, match="exited 1 .* but reported status 'ok'"):
        aegis.run_status()


def test_command_wrappers_use_the_grouped_verbs() -> None:
    """
    @brief   Each wrapper maps to its exact AEGIS 2.x group/action pair, and
             only `run start` / `config validate` omit `--run`.
    @version 0.1.0
    """
    expected = {
        "run_status": (["run", "status"], True),
        "run_resume": (["run", "resume"], True),
        "stage_show": (["stage", "show"], True),
        "stage_close": (["stage", "close"], True),
        "verify_run": (["verify", "run"], True),
        "delivery_report": (["delivery", "report"], True),
        "waive_list": (["waive", "list"], True),
        "config_validate": (["config", "validate"], False),
    }
    for name, (verbs, run_scoped) in expected.items():
        aegis, execute = client(CommandResult(exit_code=0, stdout=envelope()))
        getattr(aegis, name)()
        call = execute.calls[0]
        assert call[:2] == ["bash", ".agentic/tools/run.sh"]
        assert call[2:2 + len(verbs)] == verbs
        assert ("--run" in call) is run_scoped
        assert call[-1] == "--json"


# END OF FILE
