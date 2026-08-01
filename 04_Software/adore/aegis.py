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
@file aegis.py
@brief The single place that knows how to talk to the AEGIS 2.x CLI.
@details ADORE 2.0 speaks exactly one governance contract: the grouped AEGIS
         2.x CLI (`bash .agentic/tools/run.sh <group> <action> --run <id>
         --json`), invoked INSIDE the run's container through the exec seam.
         Every call returns the stable four-key envelope
         (`status`/`stage`/`artifact`/`next`) parsed into a frozen
         AegisResponse. Exit 0 and exit 1 are workflow signals and come back
         as data; anything else - a usage error, a wrapper that found no
         Python, unparseable output, a missing envelope key - is a typed
         AegisProtocolError, because it means ADORE built a bad command or
         the payload is broken. There is no version negotiation, no
         capability probing, and no AEGIS 1.x fallback: an unsupported
         payload fails loud and escalates.
@details `invoke` keys `AegisTimeoutError` on `CommandResult.timed_out`
         rather than on a raw exit code of 124 (ADORE-ARCH-010): a wrapped
         command like `docker exec` propagates the INNER process's exit
         code, so a payload legitimately exiting 124 for its own reasons is
         no longer misclassified as ADORE's own wrapper timeout - it falls
         into the ordinary exit-code-outside-0/1 `AegisProtocolError`
         instead, naming the exit code. The now-unused `TIMEOUT_EXIT_CODE`
         constant was removed.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
import re
from typing import Any

from adore.executor.base import ExecTarget

# CONSTANTS

# Repository-relative POSIX wrapper; bash because run.sh uses `set -o pipefail`.
WORKFLOW_CLI = ".agentic/tools/run.sh"

# Wall-clock bounds per command family (seconds). `verify run` executes every
# enabled gate group plus the invariant/traceability/coverage/working-tree
# audits, so it gets the long one.
DEFAULT_TIMEOUT = 600
STATUS_TIMEOUT = 300
VERIFY_TIMEOUT = 1800

# The four keys every AEGIS command emits, in the documented order.
ENVELOPE_KEYS = ("status", "stage", "artifact", "next")
ENVELOPE_STATUSES = ("ok", "blocked", "failed")

# Run kinds AEGIS accepts, and the subset the proportional profile allows.
RUN_KINDS = ("feature", "fix", "change", "adoption")
QUICK_KINDS = ("fix", "change")

# `^(feature|fix|change|adoption)-(YYYY-MM-DDTHHMMSSZ)-[0-9a-f]{8}$`. Validating
# the run-id at the source also keeps it usable as a single path segment under
# `.agentic/runs/`, so no later reader has to re-check for traversal.
RUN_ID_RE = re.compile(
    r"^(?:feature|fix|change|adoption)-\d{4}-\d{2}-\d{2}T\d{6}Z-[0-9a-f]{8}$"
)

# Typed AEGIS failures whose stable code is embedded in the `error` text rather
# than exposed as its own JSON field (contract notes 7 and 11.3).
INTEGRITY_CODES = (
    "PERSISTENCE-LOCK-TIMEOUT",
    "GRAPH-STALE-UPDATE",
    "REQUIREMENT-STALE-UPDATE",
)
RUN_RESOLUTION_CODES = (
    "RUN-POINTER-MISSING",
    "RUN-POINTER-INVALID",
    "RUN-POINTER-STALE",
    "RUN-ID-NOT-FOUND",
)
KNOWN_ERROR_CODES = (*INTEGRITY_CODES, *RUN_RESOLUTION_CODES)

# DATA MODELS / TYPEDEFINITIONS


class AegisError(RuntimeError):
    """
    @brief   Base class for AEGIS-facing failures ADORE cannot treat as data.
    @details Every subclass ends in escalation. Workflow outcomes (`blocked`,
             `failed`) are NOT errors - they come back as an AegisResponse.
    """


class AegisProtocolError(AegisError):
    """
    @brief   The AEGIS response did not honor the supported contract.
    @details Raised for a usage error (exit 2), a wrapper that could not
             resolve Python, unparseable or non-object output, a missing or
             mistyped envelope key, a status/exit-code mismatch, or a
             `run start` that returned no usable run id. All of these mean an
             ADORE defect or a broken/unsupported payload, never a workflow
             state, so the conductor escalates instead of re-prompting the
             executor.
    """


class AegisTimeoutError(AegisError):
    """
    @brief   One AEGIS command exceeded its wall-clock bound.
    @details Kept distinct from AegisProtocolError: the payload is fine, the
             command simply did not finish, so the escalation reason names the
             command and the bound instead of blaming the contract.
    """


@dataclass(frozen=True)
class AegisResponse:
    """
    @brief   One parsed AEGIS `--json` envelope.
    @details `raw` keeps the entire decoded object so command-specific extras
             (`run_id`, `readiness`, `verification`, `report`, ...) stay
             available without a second parse; the four envelope fields are
             promoted because every command emits them.
    """

    exit_code: int
    status: str
    stage: str
    artifact: str
    next_command: str
    raw: Mapping[str, Any] = field(default_factory=dict)
    argv: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """
        @brief   True when AEGIS reported `status: ok` (exit 0).
        @return  Success flag.
        """
        return self.status == "ok"

    @property
    def blocked(self) -> bool:
        """
        @brief   True for a typed governance block (exit 1, `status: blocked`).
        @return  Blocked flag.
        """
        return self.status == "blocked"

    @property
    def failed(self) -> bool:
        """
        @brief   True when a verify/scope action found blocking findings.
        @return  Failed flag (exit 1, `status: failed`).
        """
        return self.status == "failed"

    @property
    def complete(self) -> bool:
        """
        @brief   Whether the AEGIS run is finished (delivery closed).
        @details Only `run status`/`stage close`-family payloads carry
                 `complete`; a missing key reads as False.
        @return  Completion flag.
        """
        return self.raw.get("complete") is True

    @property
    def error(self) -> str:
        """
        @brief   The typed error text of a blocked response ("" otherwise).
        @return  The `error` field as text.
        """
        value = self.raw.get("error")
        return str(value).strip() if value else ""

    @property
    def code(self) -> str:
        """
        @brief      The stable AEGIS error code behind a blocked response.
        @details    Only configuration errors expose `code` as its own field;
                    run-resolution and persistence failures embed it in the
                    `error` text, and the requirement conflict puts it mid
                    string (contract notes 11.3). Scanning the whole text is
                    therefore the only classification that works for all of
                    them.
        @return     The code, or "" when none is recognizable.
        """
        declared = self.raw.get("code")
        if isinstance(declared, str) and declared.strip():
            return declared.strip()
        text = self.error
        for candidate in KNOWN_ERROR_CODES:
            if candidate in text:
                return candidate
        return ""

    @property
    def remediation(self) -> str:
        """
        @brief      The concrete corrective action AEGIS suggested.
        @details    Configuration errors carry a `remediation` field. The other
                    typed errors render as `"<CODE>: <message>\\n<remediation>"`,
                    so the tail after the first newline is the remediation.
        @return     Remediation text, or "" when none is available.
        """
        declared = self.raw.get("remediation")
        if isinstance(declared, str) and declared.strip():
            return declared.strip()
        _, separator, tail = self.error.partition("\n")
        return tail.strip() if separator else ""

    def detail(self, key: str, default: Any = None) -> Any:
        """
        @brief      Read one command-specific extra from the decoded payload.
        @param[in]  key Extra key (for example "run_id" or "verification").
        @param[in]  default Value returned when the key is absent.
        @return     The decoded value or the default.
        """
        return self.raw.get(key, default)


# HELPER FUNCTIONS


def _tail(text: str, limit: int = 800) -> str:
    """
    @brief      Bound diagnostic text embedded in an exception message.
    @param[in]  text Raw output.
    @param[in]  limit Character budget.
    @return     The stripped tail, prefixed when truncated.
    """
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return "[... truncated ...] " + stripped[-limit:]


def _decode_envelope(
    stdout: str,
    exit_code: int,
    argv: Sequence[str],
    stderr: str,
) -> dict[str, Any]:
    """
    @brief      Decode and structurally validate one `--json` envelope.
    @details    The envelope must be a JSON object carrying all four keys as
                strings and a known `status`. `--json` writes only the payload
                to stdout, so stderr is diagnostic material for the exception
                and never part of the parsed document.
    @param[in]  stdout Captured standard output.
    @param[in]  exit_code Process exit code (0 or 1 at this point).
    @param[in]  argv The exact command that produced it.
    @param[in]  stderr Captured standard error (diagnostics only).
    @return     The decoded payload.
    @exception  AegisProtocolError When the output is not a conforming
                envelope, or the status contradicts the exit code.
    """
    rendered = " ".join(argv)
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise AegisProtocolError(
            f"AEGIS returned unparseable JSON for `{rendered}` "
            f"(exit {exit_code}): {exc}. stdout tail: {_tail(stdout)}"
            + (f" stderr tail: {_tail(stderr)}" if stderr.strip() else "")
        ) from exc
    if not isinstance(payload, dict):
        raise AegisProtocolError(
            f"AEGIS returned a non-object payload for `{rendered}` "
            f"(exit {exit_code}): {_tail(stdout)}"
        )
    for key in ENVELOPE_KEYS:
        if key not in payload:
            raise AegisProtocolError(
                f"AEGIS response for `{rendered}` is missing the envelope key "
                f"{key!r}: {_tail(stdout)}"
            )
        if not isinstance(payload[key], str):
            raise AegisProtocolError(
                f"AEGIS response for `{rendered}` has a non-string {key!r} "
                f"envelope key: {payload[key]!r}"
            )
    status = payload["status"]
    if status not in ENVELOPE_STATUSES:
        raise AegisProtocolError(
            f"AEGIS response for `{rendered}` reported the unknown status "
            f"{status!r}"
        )
    if exit_code == 0 and status != "ok":
        raise AegisProtocolError(
            f"AEGIS exited 0 for `{rendered}` but reported status {status!r}"
        )
    if exit_code == 1 and status == "ok":
        raise AegisProtocolError(
            f"AEGIS exited 1 for `{rendered}` but reported status 'ok'"
        )
    return payload


# PUBLIC API


class AegisClient:
    """
    @brief   Typed, run-pinned client for the AEGIS 2.x grouped CLI.
    @details Bound to one run's container exec seam. Once `run start` has
             produced a run id (or the caller restored one from ADORE's
             persisted state), every subsequent command pins it with `--run`,
             so the worktree-local `current_run` pointer is irrelevant to
             ADORE - the seam that already broke once in 1.x.
    """

    def __init__(self, execute: ExecTarget, run_id: str = "") -> None:
        """
        @brief      Bind the client to a container exec seam and optional run.
        @param[in]  execute Exec seam bound to the run's container.
        @param[in]  run_id Known AEGIS run id ("" until `run start` ran).
        """
        self.execute = execute
        self.run_id = run_id or ""

    # -- transport ------------------------------------------------------------

    def invoke(
        self,
        *argv: str,
        run_scoped: bool = True,
        timeout: float | None = DEFAULT_TIMEOUT,
    ) -> AegisResponse:
        """
        @brief      Run one AEGIS command and parse its envelope.
        @details    Composes `bash .agentic/tools/run.sh <argv...> [--run <id>]
                    --json` as single argv tokens (WSL-safe) and runs it in the
                    container working dir. Exit 0 and 1 are workflow signals
                    returned as data; every other code fails loud.
        @param[in]  argv Group, action, and any positional arguments.
        @param[in]  run_scoped Whether to pin `--run <id>` (all commands except
                               `run start` and `config validate`).
        @param[in]  timeout Wall-clock bound in seconds.
        @return     The parsed AegisResponse.
        @exception  AegisProtocolError When the command is unusable, the exit
                    code is neither 0 nor 1, or the envelope does not conform.
                    This includes a genuine INNER exit 124 from the payload
                    itself (not ADORE's own wrapper timeout) - see
                    `timed_out` below.
        @exception  AegisTimeoutError When ADORE's OWN wrapper bound expired
                    (`result.timed_out`), never merely because the exit code
                    happens to be 124: a wrapped command like `docker exec`
                    propagates whatever exit code the payload used, and a
                    payload legitimately exiting 124 for its own reasons must
                    not be misreported as ADORE's timeout and must not blame
                    the wrong component in the resulting escalation
                    (ADORE-ARCH-010).
        """
        command: list[str] = ["bash", WORKFLOW_CLI, *argv]
        if run_scoped:
            if not self.run_id:
                raise AegisProtocolError(
                    f"cannot run `aegis {' '.join(argv)}` without an AEGIS run "
                    "id; `run start` must succeed first"
                )
            command += ["--run", self.run_id]
        command.append("--json")
        result = self.execute(command, timeout=timeout)
        rendered = " ".join(command)
        if result.timed_out:
            raise AegisTimeoutError(
                f"AEGIS command `{rendered}` timed out after {timeout}s"
            )
        if result.exit_code not in (0, 1):
            raise AegisProtocolError(
                f"AEGIS command `{rendered}` exited {result.exit_code}, which is "
                "outside the supported 0/1 contract (usage error or broken "
                f"payload). stdout tail: {_tail(result.stdout)} stderr tail: "
                f"{_tail(result.stderr)}"
            )
        payload = _decode_envelope(
            result.stdout, result.exit_code, command, result.stderr
        )
        return AegisResponse(
            exit_code=result.exit_code,
            status=payload["status"],
            stage=payload["stage"],
            artifact=payload["artifact"],
            next_command=payload["next"],
            raw=payload,
            argv=tuple(command),
        )

    # -- run ------------------------------------------------------------------

    def run_start(self, kind: str, quick: bool = False) -> AegisResponse:
        """
        @brief      Create and select a new AEGIS run, capturing its run id.
        @details    The only command besides `config validate` that carries no
                    `--run`. On success the minted run id is validated against
                    the documented pattern and stored on the client, so every
                    later call pins it. A blocked start (for example an invalid
                    `--quick` combination reaching AEGIS anyway) is returned as
                    data with no run id recorded.
        @param[in]  kind Run kind: feature, fix, change, or adoption.
        @param[in]  quick Select the proportional four-stage profile.
        @return     The parsed AegisResponse.
        @exception  AegisProtocolError When the kind/profile combination is not
                    permitted, or the successful response carries no usable
                    `run_id`.
        @exception  AegisTimeoutError When the command exceeded its bound.
        """
        if kind not in RUN_KINDS:
            raise AegisProtocolError(
                f"unsupported AEGIS run kind {kind!r}; expected one of "
                f"{', '.join(RUN_KINDS)}"
            )
        if quick and kind not in QUICK_KINDS:
            raise AegisProtocolError(
                f"--quick is only valid for {' and '.join(QUICK_KINDS)} runs, "
                f"not {kind!r}"
            )
        argv = ["run", "start", kind]
        if quick:
            argv.append("--quick")
        response = self.invoke(*argv, run_scoped=False, timeout=DEFAULT_TIMEOUT)
        if response.ok:
            self.run_id = self._extract_run_id(response)
        return response

    def run_status(self) -> AegisResponse:
        """
        @brief      Read authoritative run state (stage, readiness, evidence).
        @return     The parsed AegisResponse.
        @exception  AegisProtocolError When the contract is violated.
        @exception  AegisTimeoutError When the command exceeded its bound.
        """
        return self.invoke("run", "status", timeout=STATUS_TIMEOUT)

    def run_resume(self) -> AegisResponse:
        """
        @brief      Read the run-orientation payload for a fresh session.
        @details    AEGIS 2.x answers `run resume` with the same envelope as
                    `run status` (contract notes 11.1); ADORE composes the
                    human-readable brief from it rather than quoting prose.
        @return     The parsed AegisResponse.
        @exception  AegisProtocolError When the contract is violated.
        @exception  AegisTimeoutError When the command exceeded its bound.
        """
        return self.invoke("run", "resume", timeout=STATUS_TIMEOUT)

    # -- stage ----------------------------------------------------------------

    def stage_show(self) -> AegisResponse:
        """
        @brief      Report current stage files, revision, readiness, blockers.
        @return     The parsed AegisResponse.
        @exception  AegisProtocolError When the contract is violated.
        @exception  AegisTimeoutError When the command exceeded its bound.
        """
        return self.invoke("stage", "show", timeout=STATUS_TIMEOUT)

    def stage_close(self) -> AegisResponse:
        """
        @brief      Approve the current stage as the delegated approver.
        @details    In a conducted run ADORE - never the executor - issues the
                    close, and only after objective verification. The real
                    human approval stays at the draft MR review.
        @return     The parsed AegisResponse.
        @exception  AegisProtocolError When the contract is violated.
        @exception  AegisTimeoutError When the command exceeded its bound.
        """
        return self.invoke("stage", "close", timeout=DEFAULT_TIMEOUT)

    # -- verification and delivery ---------------------------------------------

    def verify_run(self) -> AegisResponse:
        """
        @brief      Execute the complete deterministic verification sequence.
        @details    Exit 1 with `status: failed` is a normal governance outcome
                    (blocking findings), returned as data; the evidence lives in
                    `validation-summary.json` and in the `verification` extra.
        @return     The parsed AegisResponse.
        @exception  AegisProtocolError When the contract is violated.
        @exception  AegisTimeoutError When verification exceeded its bound.
        """
        return self.invoke("verify", "run", timeout=VERIFY_TIMEOUT)

    def delivery_report(self) -> AegisResponse:
        """
        @brief      Render the delivery report and return its path.
        @return     The parsed AegisResponse (`report` names `report.md`).
        @exception  AegisProtocolError When the contract is violated.
        @exception  AegisTimeoutError When the command exceeded its bound.
        """
        return self.invoke("delivery", "report", timeout=DEFAULT_TIMEOUT)

    def waive_list(self) -> AegisResponse:
        """
        @brief      List eligible blocker IDs, active waivers, and history.
        @details    Read-only on purpose: ADORE never waives (design decision
                    3). The eligible IDs become the exact `aegis waive add`
                    hint in the escalation comment a human acts on.
        @return     The parsed AegisResponse.
        @exception  AegisProtocolError When the contract is violated.
        @exception  AegisTimeoutError When the command exceeded its bound.
        """
        return self.invoke("waive", "list", timeout=STATUS_TIMEOUT)

    def config_validate(self) -> AegisResponse:
        """
        @brief      Validate the target repository's schema-3 AEGIS policy.
        @details    Carries no `--run`: it is the probe that proves a repo is
                    AEGIS 2.x governed before any run exists.
        @return     The parsed AegisResponse (`schema_version` on success).
        @exception  AegisProtocolError When the contract is violated.
        @exception  AegisTimeoutError When the command exceeded its bound.
        """
        return self.invoke(
            "config", "validate", run_scoped=False, timeout=STATUS_TIMEOUT
        )

    # -- internals -------------------------------------------------------------

    @staticmethod
    def _extract_run_id(response: AegisResponse) -> str:
        """
        @brief      Pull the minted run id out of a successful `run start`.
        @param[in]  response The `run start` response.
        @return     The validated run id.
        @exception  AegisProtocolError When `run_id` is absent, not a string,
                    or does not match the documented run-id pattern.
        """
        value = response.detail("run_id")
        if not isinstance(value, str) or not RUN_ID_RE.match(value):
            raise AegisProtocolError(
                "AEGIS `run start` did not return a usable run id: "
                f"{value!r}"
            )
        return value


# END OF FILE
