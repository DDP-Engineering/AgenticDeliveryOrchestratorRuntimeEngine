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
@brief Tests for the AEGIS 3.x client (envelope parsing and command shape).
@details Trust-boundary coverage for everything crossing into ADORE from the
         AEGIS CLI: the happy envelope, blocked/failed governance signals,
         `--run` pinning, run-id capture, and every fail-loud path (exit 2,
         timeout, unparseable JSON, non-object payload, missing or mistyped
         envelope keys, status/exit-code contradictions). The exec seam is a
         fake, so nothing here touches bash, docker, or a real payload.
"""

from __future__ import annotations

# IMPORTS
import json

from adore.aegis import (
    CONTEXT_LIMIT_BYTES,
    VERIFY_TIMEOUT,
    AegisClient,
    AegisContext,
    AegisProtocolError,
    AegisTimeoutError,
)
from adore.util import CommandResult
import pytest

# CONSTANTS

RUN_ID = "feature-2026-08-01T101112Z-0a1b2c3d"

# DATA MODELS / TYPEDEFINITIONS


class FakeExec:
    """
    @brief   Exec-seam double replaying scripted results and recording argv.
    """

    def __init__(self, *results: CommandResult) -> None:
        """
        @brief      Script one or more results (the last one repeats).
        @param[in]  results Results returned in order.
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
    """
    payload = {
        "status": "ok",
        "stage": "intake",
        "artifact": ".agentic/runs/x/stages/intake/stage.toml",
        "next": "aegis stage apply",
    }
    payload.update(extras)
    return json.dumps(payload)


def context(**overrides) -> str:
    """@brief Render a conforming direct schema-1 context response."""
    artifact = ".agentic/runs/x/stages/intake/intake.toml"
    payload = {
        "context_schema_version": 1,
        "run_id": RUN_ID,
        "kind": "feature",
        "profile": "full",
        "stage": "intake",
        "reference": ".agentic/skills/agentic-development/reference/intake.md",
        "skill": ".agentic/skills/agentic-development/SKILL.md",
        "artifact": artifact,
        "unavailable_current_artifact": None,
        "previous_stage_artifacts": [],
        "unavailable_previous_stage_artifacts": [],
        "required_reads": [
            "AGENTS.md",
            ".agentic/skills/agentic-development/SKILL.md",
            ".agentic/skills/agentic-development/reference/intake.md",
            artifact,
        ],
        "next_commands": [
            "aegis stage prepare",
            "aegis stage apply",
            "aegis stage close",
        ],
        "human_gate": "stage close",
    }
    payload.update(overrides)
    return json.dumps(payload)


def client(*results: CommandResult, run_id: str = RUN_ID) -> tuple[AegisClient, FakeExec]:
    """
    @brief      Build a client over a scripted fake exec seam.
    @param[in]  results Scripted results.
    @param[in]  run_id Pinned AEGIS run id ("" for an unstarted run).
    @return     (client, fake exec seam).
    """
    execute = FakeExec(*results)
    return AegisClient(execute, run_id=run_id), execute


# PUBLIC API / TESTS


def test_envelope_happy_path_is_parsed_and_run_pinned() -> None:
    """
    @brief   A successful command yields the four envelope fields plus extras,
             and the argv pins `--run` and `--json` as single tokens.
    """
    aegis, execute = client(
        CommandResult(
            exit_code=0,
            stdout=envelope(
                stage="design", complete=False, run_id=RUN_ID,
            ),
        )
    )
    response = aegis.run_status()
    assert response.ok and not response.blocked and not response.failed
    assert response.stage == "design"
    assert response.next_command == "aegis stage apply"
    assert response.artifact.endswith("stage.toml")
    assert response.complete is False
    assert execute.calls == [[
        "bash", ".agentic/tools/run.sh", "--run", RUN_ID, "--json", "run", "status",
    ]]
    assert all(" " not in token for token in execute.calls[0])


def test_blocked_envelope_exposes_error_code_and_remediation() -> None:
    """
    @brief   A typed governance block is data, not an exception; the stable
             code is recovered from inside the `error` text and the
             remediation from its tail (contract notes 11.3).
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
    """
    summary = {"status": "failed", "gates": {"test": {"status": "failed"}}}
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


def test_blocked_verification_remains_classifiable_without_a_summary() -> None:
    """@brief A pre-verification governance block is still an envelope."""
    aegis, _ = client(CommandResult(
        exit_code=1,
        stdout=envelope(status="blocked", error="PERSISTENCE-LOCK-TIMEOUT"),
    ))
    assert aegis.verify_run().blocked


def test_run_start_captures_and_pins_the_run_id() -> None:
    """
    @brief   `run start` carries no `--run`; the minted id is captured and
             every later call pins it.
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
    assert execute.calls[1][2:5] == ["--run", RUN_ID, "--json"]


def test_quick_run_start_passes_the_profile_flag() -> None:
    """
    @brief   A quick fix run adds `--quick` before the global options.
    """
    aegis, execute = client(
        CommandResult(
            exit_code=0,
            stdout=envelope(
                run_id="fix-2026-08-01T101112Z-0a1b2c3d",
                kind="fix",
                run_profile="quick",
            ),
        ),
        run_id="",
    )
    aegis.run_start("fix", quick=True)
    assert execute.calls[0] == [
        "bash", ".agentic/tools/run.sh", "--json", "run", "start", "fix", "--quick",
    ]


def test_quick_is_rejected_for_kinds_aegis_does_not_allow() -> None:
    """
    @brief   Building `--quick feature` is an ADORE defect and fails before it
             ever reaches the payload.
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
    """
    aegis, execute = client(run_id="")
    with pytest.raises(AegisProtocolError, match="without an AEGIS run id"):
        aegis.stage_close("ADORE delegated conductor", run_kind="fix")
    assert execute.calls == []


def test_exit_two_raises_instead_of_becoming_a_workflow_state() -> None:
    """
    @brief   Exit 2 is a usage error or a wrapper that found no Python - an
             ADORE/payload defect, and the plain-text output must not be
             mistaken for an envelope.
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
    """
    aegis, _ = client(CommandResult(exit_code=124, stdout='{"status": "ok"}',
                                    stderr="payload used exit code 124"))
    with pytest.raises(AegisProtocolError, match="exited 124"):
        aegis.verify_run()


def test_malformed_json_raises() -> None:
    """
    @brief   Unparseable output fails closed rather than degrading to an empty
             brief or a skipped check.
    """
    aegis, _ = client(CommandResult(exit_code=0, stdout="status: ok\nstage: intake\n"))
    with pytest.raises(AegisProtocolError, match="unparseable JSON"):
        aegis.run_status()


def test_non_object_payload_raises() -> None:
    """
    @brief   A JSON array is valid JSON but not the documented envelope.
    """
    aegis, _ = client(CommandResult(exit_code=0, stdout='["ok"]'))
    with pytest.raises(AegisProtocolError, match="non-object payload"):
        aegis.run_status()


def test_missing_and_mistyped_envelope_keys_raise() -> None:
    """
    @brief   Every one of the four envelope keys must be present and a string.
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


def test_context_success_is_parsed_as_its_own_response_family() -> None:
    """@brief Exit-0 context is direct schema-1 data, never an envelope."""
    aegis, execute = client(CommandResult(exit_code=0, stdout=context()))
    response = aegis.run_context(
        expected_profile="full", expected_stage="intake", expected_kind="feature"
    )
    assert isinstance(response, AegisContext)
    assert response.run_id == RUN_ID
    assert response.required_reads[-1].endswith("intake.toml")
    assert response.human_gate == "stage close"
    assert execute.calls == [[
        "bash", ".agentic/tools/run.sh", "--run", RUN_ID, "--json",
        "run", "context",
    ]]


def test_context_exit_one_remains_a_validated_blocked_envelope() -> None:
    """@brief The response family is selected after exit-code discrimination."""
    aegis, _ = client(CommandResult(
        exit_code=1,
        stdout=envelope(status="blocked", error="RUN-ID-NOT-FOUND: gone"),
    ))
    response = aegis.run_context(
        expected_profile="full", expected_stage="intake"
    )
    assert not isinstance(response, AegisContext)
    assert response.blocked


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"context_schema_version": 2}, "context_schema_version"),
        ({"profile": 3}, "invalid string field 'profile'"),
        ({"run_id": "fix-2026-08-01T101112Z-0a1b2c3d"}, "disagrees with pinned"),
        ({"profile": "quick"}, "disagrees with expected"),
        ({"stage": "design"}, "disagrees with expected"),
        ({"human_gate": "auto close"}, "invalid human_gate"),
        ({"artifact": "../graph.json"}, "escapes or is not normalized"),
        ({"required_reads": ["AGENTS.md", "../secret"]}, "escapes"),
        ({"next_commands": ["rm -rf ."]}, "unknown recovery/procedure"),
    ),
)
def test_context_rejects_schema_state_type_path_and_command_faults(
    overrides: dict,
    message: str,
) -> None:
    """@brief Every direct-context trust-boundary fault fails loud."""
    aegis, _ = client(CommandResult(exit_code=0, stdout=context(**overrides)))
    with pytest.raises(AegisProtocolError, match=message):
        aegis.run_context(expected_profile="full", expected_stage="intake")


def test_context_rejects_missing_extra_malformed_and_oversized_objects() -> None:
    """@brief The context schema is closed and the UTF-8 wire budget is hard."""
    payload = json.loads(context())
    del payload["skill"]
    aegis, _ = client(CommandResult(exit_code=0, stdout=json.dumps(payload)))
    with pytest.raises(AegisProtocolError, match="wrong fixed shape"):
        aegis.run_context(expected_profile="full", expected_stage="intake")

    aegis, _ = client(CommandResult(exit_code=0, stdout="not-json"))
    with pytest.raises(AegisProtocolError, match="unparseable context JSON"):
        aegis.run_context(expected_profile="full", expected_stage="intake")

    oversized = context(extra="x" * CONTEXT_LIMIT_BYTES)
    aegis, _ = client(CommandResult(exit_code=0, stdout=oversized))
    with pytest.raises(AegisProtocolError, match="exceeds 4096 bytes"):
        aegis.run_context(expected_profile="full", expected_stage="intake")


@pytest.mark.parametrize("exit_code", (2, 7, 124, 127))
def test_current_context_wrapper_rejects_unsupported_exit_codes(exit_code: int) -> None:
    """@brief Propagated tool exits are unsupported until a wrapper owns them."""
    aegis, _ = client(CommandResult(exit_code=exit_code, stdout=context()))
    with pytest.raises(AegisProtocolError, match=f"exited {exit_code}"):
        aegis.run_context(expected_profile="full", expected_stage="intake")


def test_run_start_warnings_are_bounded_and_preserved() -> None:
    """@brief Optional displaced-run warnings remain visible as typed strings."""
    warning = f"Run {RUN_ID} remains incomplete; use aegis run select {RUN_ID}."
    aegis, _ = client(CommandResult(
        exit_code=0,
        stdout=envelope(run_id=RUN_ID, kind="feature", warnings=[warning]),
    ), run_id="")
    response = aegis.run_start("feature")
    assert response.warnings == (warning,)

    aegis, _ = client(CommandResult(
        exit_code=0,
        stdout=envelope(run_id=RUN_ID, kind="feature", warnings=[3]),
    ), run_id="")
    with pytest.raises(AegisProtocolError, match="bounded non-empty string"):
        aegis.run_start("feature")


def test_stage_close_requires_and_validates_the_delegated_approver() -> None:
    """@brief ADORE identity is explicit in argv and confirmed by AEGIS."""
    identity = "ADORE 3.0 delegated conductor"
    aegis, execute = client(CommandResult(
        exit_code=0,
        stdout=envelope(approver=identity, complete=False),
    ))
    response = aegis.stage_close(identity, run_kind="feature")
    assert response.advisories == ()
    assert execute.calls[0] == [
        "bash", ".agentic/tools/run.sh", "--run", RUN_ID, "--json",
        "stage", "close", "--approver", identity,
    ]

    aegis, _ = client(CommandResult(
        exit_code=0,
        stdout=envelope(approver="human", complete=False),
    ))
    with pytest.raises(AegisProtocolError, match="did not record"):
        aegis.stage_close(identity, run_kind="feature")

    aegis, execute = client()
    with pytest.raises(AegisProtocolError, match="bounded non-empty identity"):
        aegis.stage_close(" ", run_kind="feature")
    assert execute.calls == []


def test_stage_close_advisory_is_typed_and_malformed_shapes_fail_closed() -> None:
    """@brief The one current non-blocking advisory retains exact semantics."""
    identity = "ADORE 3.0 delegated conductor"
    advisory = {
        "code": "QUICK-SCOPE-ADVISORY",
        "status": "advisory",
        "changed_path_count": 3,
        "max_paths": 2,
        "message": "Quick scope widened; restart as a full run.",
        "restart_command": "aegis run start fix",
    }
    aegis, _ = client(CommandResult(
        exit_code=0,
        stdout=envelope(approver=identity, complete=False, advisories=[advisory]),
    ))
    response = aegis.stage_close(identity, run_kind="fix")
    assert response.advisories[0].code == "QUICK-SCOPE-ADVISORY"

    bad = dict(advisory, restart_command="aegis run start feature")
    aegis, _ = client(CommandResult(
        exit_code=0,
        stdout=envelope(approver=identity, complete=False, advisories=[bad]),
    ))
    with pytest.raises(AegisProtocolError, match="message/restart"):
        aegis.stage_close(identity, run_kind="fix")


@pytest.mark.parametrize(
    ("complete", "outcome", "expected"),
    ((False, None, None), (True, None, "normal"), (True, "abandoned", "abandoned")),
)
def test_run_status_exposes_a_typed_terminal_outcome(
    complete: bool,
    outcome: str | None,
    expected: str | None,
) -> None:
    """@brief Completion and abandonment are never conflated."""
    extras = {"run_id": RUN_ID, "complete": complete}
    if outcome is not None:
        extras["outcome"] = outcome
    aegis, _ = client(CommandResult(exit_code=0, stdout=envelope(**extras)))
    assert aegis.run_status().terminal_outcome == expected


def test_verification_status_preserves_ok_waived_failed_and_rejects_disagreement() -> None:
    """@brief Exit 0 is not a synonym for passed verification."""
    for status in ("ok", "waived"):
        aegis, _ = client(CommandResult(
            exit_code=0, stdout=envelope(verification={"status": status}),
        ))
        assert aegis.verify_run().verification_status == status
    aegis, _ = client(CommandResult(
        exit_code=0, stdout=envelope(verification={"status": "failed"}),
    ))
    with pytest.raises(AegisProtocolError, match="disagree"):
        aegis.verify_run()


def test_command_wrappers_use_the_grouped_verbs() -> None:
    """
    @brief   Each wrapper maps to its exact AEGIS 3.x group/action pair, and
             only `run start` / `config validate` omit `--run`.
    """
    identity = "ADORE 3.0 delegated conductor"
    expected = (
        ("run_status", ["run", "status"], True,
         {"run_id": RUN_ID, "complete": False}, (), {}),
        ("run_resume", ["run", "resume"], True, {}, (), {}),
        ("stage_show", ["stage", "show"], True, {}, (), {}),
        ("stage_close", ["stage", "close", "--approver", identity], True,
         {"approver": identity, "complete": False}, (identity,), {"run_kind": "feature"}),
        ("verify_run", ["verify", "run"], True,
         {"verification": {"status": "ok"}}, (), {}),
        ("delivery_report", ["delivery", "report"], True, {}, (), {}),
        ("waive_list", ["waive", "list"], True, {}, (), {}),
        ("config_validate", ["config", "validate"], False, {}, (), {}),
    )
    for name, verbs, run_scoped, extras, args, kwargs in expected:
        aegis, execute = client(
            CommandResult(exit_code=0, stdout=envelope(**extras))
        )
        getattr(aegis, name)(*args, **kwargs)
        call = execute.calls[0]
        assert call[:2] == ["bash", ".agentic/tools/run.sh"]
        offset = 5 if run_scoped else 3
        assert call[offset:offset + len(verbs)] == verbs
        assert ("--run" in call) is run_scoped
        assert call[4 if run_scoped else 2] == "--json"


# END OF FILE
