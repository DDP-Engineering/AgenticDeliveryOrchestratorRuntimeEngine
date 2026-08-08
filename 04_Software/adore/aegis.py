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
@brief The single place that knows how to talk to the AEGIS 3.x CLI.
@details ADORE 3.0 speaks exactly one governance contract: the grouped AEGIS
         3.x CLI (`bash .agentic/tools/run.sh --run <id> --json <group>
         <action>`), invoked INSIDE the run's container through the exec seam.
         Normal calls return the stable four-key envelope parsed into a frozen
         AegisResponse. Successful `run context` is the deliberate exception:
         its direct schema-1 object is parsed into AegisContext. Exit 0 and
         exit 1 are workflow signals and come back as data; anything else - a
         usage error, a wrapper that found no Python, unparseable output, or a
         malformed response - is a typed AegisProtocolError. There is no
         version negotiation, capability probing, or older AEGIS fallback.
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
from pathlib import PurePosixPath
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

# Fresh-session context is a distinct direct response family with tight wire
# and bootstrap bounds locked by AEGIS contract tests.
CONTEXT_SCHEMA_VERSION = 1
CONTEXT_LIMIT_BYTES = 4 * 1024
CONTEXT_BOOTSTRAP_LIMIT_BYTES = 30 * 1024
CONTEXT_PROFILES = ("full", "quick")
CONTEXT_HUMAN_GATE = "stage close"
CONTEXT_MAX_LIST_ITEMS = 32
CONTEXT_MAX_TEXT = 2048

# Operator-visible optional extras remain bounded even though the normal
# envelope itself has no global size limit.
MAX_WARNING_COUNT = 8
MAX_WARNING_LENGTH = 2048
MAX_APPROVER_LENGTH = 256

# Run kinds AEGIS accepts, and the subset the proportional profile allows.
RUN_KINDS = ("feature", "fix", "change", "adoption")
QUICK_KINDS = ("fix", "change")

FULL_STAGES = (
    "intake",
    "alignment",
    "requirement",
    "design",
    "check",
    "implementation",
    "validation",
    "delivery",
)
QUICK_STAGES = ("intake", "implementation", "validation", "delivery")
ADOPTION_STAGES = (
    "adoption-intake",
    "adoption-alignment",
    "repo-discovery",
    "component-map",
    "component-adoption",
    "baseline-review",
    "adoption-delivery",
)
ALL_STAGES = (*FULL_STAGES, *ADOPTION_STAGES)

STAGE_REFERENCES = {
    stage: f".agentic/skills/agentic-development/reference/{stage}.md"
    for stage in FULL_STAGES
}
STAGE_REFERENCES["delivery"] = ".agentic/skills/agentic-delivery/SKILL.md"
STAGE_REFERENCES.update({
    stage: f".agentic/skills/agentic-adoption/reference/{stage}.md"
    for stage in ADOPTION_STAGES
})
STAGE_SKILLS = {
    stage: (
        ".agentic/skills/agentic-delivery/SKILL.md"
        if stage == "delivery"
        else ".agentic/skills/agentic-development/SKILL.md"
    )
    for stage in FULL_STAGES
}
STAGE_SKILLS.update({
    stage: ".agentic/skills/agentic-adoption/SKILL.md"
    for stage in ADOPTION_STAGES
})

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


class AegisArtifactError(AegisError):
    """
    @brief   A persisted AEGIS artifact failed its file or schema contract.
    @details Raised for missing, escaping, oversized, unreadable, malformed,
             wrong-run, or semantically contradictory graph, verification,
             and report artifacts. Persisted AEGIS state is an external trust
             boundary: callers escalate this error and never substitute an
             empty value or infer success from the process exit code.
    """


class AegisTimeoutError(AegisError):
    """
    @brief   One AEGIS command exceeded its wall-clock bound.
    @details Kept distinct from AegisProtocolError: the payload is fine, the
             command simply did not finish, so the escalation reason names the
             command and the bound instead of blaming the contract.
    """


@dataclass(frozen=True)
class AegisUnavailableArtifact:
    """@brief One context record explaining a missing retained stage form."""

    stage: str
    reason: str
    recovery_command: str


@dataclass(frozen=True)
class AegisContext:
    """
    @brief   Validated direct schema-1 response from `run context --json`.
    @details Paths are normalized repository-relative POSIX paths. Commands
             remain orientation data; no caller may execute arbitrary entries.
    """

    context_schema_version: int
    run_id: str
    kind: str
    profile: str
    stage: str
    reference: str
    skill: str
    artifact: str
    unavailable_current_artifact: AegisUnavailableArtifact | None
    previous_stage_artifacts: tuple[str, ...]
    unavailable_previous_stage_artifacts: tuple[AegisUnavailableArtifact, ...]
    required_reads: tuple[str, ...]
    next_commands: tuple[str, ...]
    human_gate: str
    wire_size_bytes: int = 0


@dataclass(frozen=True)
class AegisAdvisory:
    """@brief One validated non-blocking stage-close advisory."""

    code: str
    status: str
    changed_path_count: int
    max_paths: int
    message: str
    restart_command: str


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
    warnings: tuple[str, ...] = ()
    advisories: tuple[AegisAdvisory, ...] = ()

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
    def terminal_outcome(self) -> str | None:
        """
        @brief      Return `normal`/`abandoned` for a completed run.
        @return     Terminal outcome, or None for a live/non-status response.
        @exception  AegisProtocolError For an invalid complete/outcome pair.
        """
        complete = self.raw.get("complete")
        outcome = self.raw.get("outcome")
        if complete is None:
            if outcome is not None:
                raise AegisProtocolError(
                    "AEGIS response reports a run outcome without complete"
                )
            return None
        if not isinstance(complete, bool):
            raise AegisProtocolError("AEGIS response has non-boolean complete")
        if not complete:
            if outcome is not None:
                raise AegisProtocolError(
                    "AEGIS live run unexpectedly reports a terminal outcome"
                )
            return None
        if outcome is None:
            return "normal"
        if outcome == "abandoned":
            return "abandoned"
        raise AegisProtocolError(
            f"AEGIS response reports unknown terminal outcome {outcome!r}"
        )

    @property
    def verification_status(self) -> str:
        """
        @brief      Return the structured verification verdict.
        @return     `ok`, `waived`, or `failed`.
        @exception  AegisProtocolError When verification data is malformed.
        """
        verification = self.raw.get("verification")
        if not isinstance(verification, Mapping):
            raise AegisProtocolError(
                "AEGIS verification response is missing the summary object"
            )
        status = verification.get("status")
        if status not in {"ok", "waived", "failed"}:
            raise AegisProtocolError(
                f"AEGIS verification summary has invalid status {status!r}"
            )
        if self.failed != (status == "failed"):
            raise AegisProtocolError(
                "AEGIS envelope and verification summary disagree on failure"
            )
        return str(status)

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


def _require_string(
    payload: Mapping[str, Any],
    key: str,
    *,
    allow_none_literal: bool = False,
) -> str:
    """@brief Read one required bounded non-empty string from a response."""
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AegisProtocolError(
            f"AEGIS response has missing/invalid string field {key!r}: {value!r}"
        )
    if len(value.encode("utf-8")) > CONTEXT_MAX_TEXT:
        raise AegisProtocolError(f"AEGIS response field {key!r} exceeds its bound")
    if value == "none" and not allow_none_literal:
        raise AegisProtocolError(
            f"AEGIS response field {key!r} may not be the none sentinel"
        )
    return value


def _require_string_list(
    payload: Mapping[str, Any],
    key: str,
) -> tuple[str, ...]:
    """@brief Read one bounded list of bounded non-empty strings."""
    value = payload.get(key)
    if not isinstance(value, list) or len(value) > CONTEXT_MAX_LIST_ITEMS:
        raise AegisProtocolError(
            f"AEGIS response field {key!r} must be a bounded list"
        )
    strings: list[str] = []
    for index, item in enumerate(value):
        if (
            not isinstance(item, str)
            or not item.strip()
            or len(item.encode("utf-8")) > CONTEXT_MAX_TEXT
        ):
            raise AegisProtocolError(
                f"AEGIS response field {key!r}[{index}] is not a bounded string"
            )
        strings.append(item)
    if len(strings) != len(set(strings)):
        raise AegisProtocolError(f"AEGIS response field {key!r} has duplicates")
    return tuple(strings)


def _repository_path(value: str, key: str, *, allow_none: bool = False) -> str:
    """@brief Validate a normalized repository-relative POSIX path."""
    if allow_none and value == "none":
        return value
    if "\\" in value or ":" in value:
        raise AegisProtocolError(
            f"AEGIS response path {key!r} is not repository-relative: {value!r}"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value in {"", ".", ".."}
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        raise AegisProtocolError(
            f"AEGIS response path {key!r} escapes or is not normalized: {value!r}"
        )
    return value


def _unavailable_record(
    value: Any,
    key: str,
    *,
    current_stage: str,
    current: bool,
) -> AegisUnavailableArtifact:
    """@brief Parse one closed-shape unavailable-artifact record."""
    if not isinstance(value, dict) or set(value) != {
        "stage", "reason", "recovery_command",
    }:
        raise AegisProtocolError(
            f"AEGIS context field {key!r} has an invalid record shape"
        )
    stage = _require_string(value, "stage")
    reason = _require_string(value, "reason")
    recovery = _require_string(value, "recovery_command")
    if stage not in ALL_STAGES or (current and stage != current_stage):
        raise AegisProtocolError(
            f"AEGIS context field {key!r} has invalid stage {stage!r}"
        )
    allowed = {"aegis stage prepare", "aegis stage show"} if current else {
        "aegis stage show"
    }
    if recovery not in allowed:
        raise AegisProtocolError(
            f"AEGIS context field {key!r} has unsafe recovery {recovery!r}"
        )
    return AegisUnavailableArtifact(stage, reason, recovery)


def _decode_context(
    stdout: str,
    argv: Sequence[str],
    stderr: str,
    *,
    pinned_run_id: str,
    expected_profile: str,
    expected_stage: str,
    expected_kind: str | None,
) -> AegisContext:
    """
    @brief Decode and validate the direct schema-1 context response.
    @exception AegisProtocolError For size, schema, state, type, or path faults.
    """
    rendered = " ".join(argv)
    if len(stdout.encode("utf-8")) > CONTEXT_LIMIT_BYTES:
        raise AegisProtocolError(
            f"AEGIS context for `{rendered}` exceeds {CONTEXT_LIMIT_BYTES} bytes"
        )
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise AegisProtocolError(
            f"AEGIS returned unparseable context JSON for `{rendered}`: {exc}. "
            f"stdout tail: {_tail(stdout)}"
            + (f" stderr tail: {_tail(stderr)}" if stderr.strip() else "")
        ) from exc
    if not isinstance(payload, dict):
        raise AegisProtocolError(
            f"AEGIS returned a non-object context for `{rendered}`"
        )
    required_keys = {
        "context_schema_version", "run_id", "kind", "profile", "stage",
        "reference", "skill", "artifact", "unavailable_current_artifact",
        "previous_stage_artifacts", "unavailable_previous_stage_artifacts",
        "required_reads", "next_commands", "human_gate",
    }
    if set(payload) != required_keys:
        missing = sorted(required_keys - set(payload))
        extra = sorted(set(payload) - required_keys)
        raise AegisProtocolError(
            f"AEGIS context has the wrong fixed shape; missing={missing}, extra={extra}"
        )
    if payload["context_schema_version"] != CONTEXT_SCHEMA_VERSION:
        raise AegisProtocolError(
            "AEGIS context has unsupported context_schema_version "
            f"{payload['context_schema_version']!r}"
        )
    run_id = _require_string(payload, "run_id")
    kind = _require_string(payload, "kind")
    profile = _require_string(payload, "profile")
    stage = _require_string(payload, "stage")
    reference = _repository_path(_require_string(payload, "reference"), "reference")
    skill = _repository_path(_require_string(payload, "skill"), "skill")
    artifact = _repository_path(
        _require_string(payload, "artifact", allow_none_literal=True),
        "artifact",
        allow_none=True,
    )
    human_gate = _require_string(payload, "human_gate")
    if not RUN_ID_RE.match(run_id) or run_id != pinned_run_id:
        raise AegisProtocolError(
            f"AEGIS context run id {run_id!r} disagrees with pinned run {pinned_run_id!r}"
        )
    if kind not in RUN_KINDS or (expected_kind is not None and kind != expected_kind):
        raise AegisProtocolError(
            f"AEGIS context kind {kind!r} disagrees with expected kind {expected_kind!r}"
        )
    if profile not in CONTEXT_PROFILES or profile != expected_profile:
        raise AegisProtocolError(
            f"AEGIS context profile {profile!r} disagrees with expected {expected_profile!r}"
        )
    if stage not in ALL_STAGES or stage != expected_stage:
        raise AegisProtocolError(
            f"AEGIS context stage {stage!r} disagrees with expected {expected_stage!r}"
        )
    if profile == "quick" and (kind not in QUICK_KINDS or stage not in QUICK_STAGES):
        raise AegisProtocolError("AEGIS context has an invalid quick run shape")
    if kind == "adoption" and stage not in ADOPTION_STAGES:
        raise AegisProtocolError("AEGIS adoption context has a development stage")
    if kind != "adoption" and stage in ADOPTION_STAGES:
        raise AegisProtocolError("AEGIS development context has an adoption stage")
    if reference != STAGE_REFERENCES[stage] or skill != STAGE_SKILLS[stage]:
        raise AegisProtocolError(
            "AEGIS context stage guidance paths disagree with the supported contract"
        )
    if human_gate != CONTEXT_HUMAN_GATE:
        raise AegisProtocolError(
            f"AEGIS context has invalid human_gate {human_gate!r}"
        )

    unavailable_value = payload["unavailable_current_artifact"]
    unavailable = (
        None
        if unavailable_value is None
        else _unavailable_record(
            unavailable_value,
            "unavailable_current_artifact",
            current_stage=stage,
            current=True,
        )
    )
    if (artifact == "none") != (unavailable is not None):
        raise AegisProtocolError(
            "AEGIS context artifact availability fields contradict each other"
        )
    previous = tuple(
        _repository_path(item, "previous_stage_artifacts")
        for item in _require_string_list(payload, "previous_stage_artifacts")
    )
    unavailable_previous_value = payload["unavailable_previous_stage_artifacts"]
    if (
        not isinstance(unavailable_previous_value, list)
        or len(unavailable_previous_value) > CONTEXT_MAX_LIST_ITEMS
    ):
        raise AegisProtocolError(
            "AEGIS context unavailable_previous_stage_artifacts must be a bounded list"
        )
    unavailable_previous = tuple(
        _unavailable_record(
            item,
            f"unavailable_previous_stage_artifacts[{index}]",
            current_stage=stage,
            current=False,
        )
        for index, item in enumerate(unavailable_previous_value)
    )
    reads = tuple(
        _repository_path(item, "required_reads")
        for item in _require_string_list(payload, "required_reads")
    )
    expected_reads = (
        "AGENTS.md", skill, reference,
        *((artifact,) if artifact != "none" else ()),
        *previous,
    )
    if reads != tuple(dict.fromkeys(expected_reads)):
        raise AegisProtocolError(
            "AEGIS context required_reads is not the exact bounded bootstrap set"
        )
    commands = _require_string_list(payload, "next_commands")
    expected_commands = (
        (unavailable.recovery_command,)
        if unavailable is not None
        else ("aegis stage prepare", "aegis stage apply", "aegis stage close")
    )
    if commands != expected_commands:
        raise AegisProtocolError(
            "AEGIS context next_commands contains an unknown recovery/procedure"
        )
    return AegisContext(
        context_schema_version=CONTEXT_SCHEMA_VERSION,
        run_id=run_id,
        kind=kind,
        profile=profile,
        stage=stage,
        reference=reference,
        skill=skill,
        artifact=artifact,
        unavailable_current_artifact=unavailable,
        previous_stage_artifacts=previous,
        unavailable_previous_stage_artifacts=unavailable_previous,
        required_reads=reads,
        next_commands=commands,
        human_gate=human_gate,
        wire_size_bytes=len(stdout.encode("utf-8")),
    )


def _bounded_strings(raw: Any, key: str) -> tuple[str, ...]:
    """@brief Validate one optional bounded list of operator-visible strings."""
    if raw is None:
        return ()
    if not isinstance(raw, list) or len(raw) > MAX_WARNING_COUNT:
        raise AegisProtocolError(f"AEGIS field {key!r} must be a bounded list")
    values: list[str] = []
    for index, value in enumerate(raw):
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value.encode("utf-8")) > MAX_WARNING_LENGTH
        ):
            raise AegisProtocolError(
                f"AEGIS field {key!r}[{index}] must be a bounded non-empty string"
            )
        values.append(value)
    return tuple(values)


def _decode_advisories(raw: Any, *, kind: str) -> tuple[AegisAdvisory, ...]:
    """@brief Validate the optional closed quick-scope advisory surface."""
    if raw is None:
        return ()
    if not isinstance(raw, list) or len(raw) > 1:
        raise AegisProtocolError("AEGIS advisories must be a list of at most one item")
    advisories: list[AegisAdvisory] = []
    expected_restart = f"aegis run start {kind}"
    for item in raw:
        if not isinstance(item, dict) or set(item) != {
            "code", "status", "changed_path_count", "max_paths", "message",
            "restart_command",
        }:
            raise AegisProtocolError("AEGIS advisory has an invalid fixed shape")
        if item["code"] != "QUICK-SCOPE-ADVISORY" or item["status"] != "advisory":
            raise AegisProtocolError("AEGIS advisory has unknown code or status")
        changed = item["changed_path_count"]
        maximum = item["max_paths"]
        if (
            not isinstance(changed, int) or isinstance(changed, bool) or changed <= 0
            or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 0
            or changed <= maximum
        ):
            raise AegisProtocolError("AEGIS advisory has invalid path counts")
        message = item["message"]
        restart = item["restart_command"]
        if (
            not isinstance(message, str) or not message.strip()
            or len(message.encode("utf-8")) > MAX_WARNING_LENGTH
            or restart != expected_restart
        ):
            raise AegisProtocolError("AEGIS advisory has invalid message/restart command")
        advisories.append(AegisAdvisory(
            code=item["code"], status=item["status"], changed_path_count=changed,
            max_paths=maximum, message=message, restart_command=restart,
        ))
    return tuple(advisories)


# PUBLIC API


class AegisClient:
    """
    @brief   Typed, run-pinned client for the AEGIS 3.x grouped CLI.
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
        @details    Composes `bash .agentic/tools/run.sh [--run <id>] --json
                    <argv...>` as single argv tokens (WSL-safe) and runs it in
                    the container working dir. This normal-envelope transport
                    deliberately supports only exit 0/1. Future wrappers for
                    `verify gates` or executable `verify impact --run` must
                    add their propagated tool exit codes (including 124/127)
                    explicitly rather than weakening this boundary.
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
        command: list[str] = ["bash", WORKFLOW_CLI]
        if run_scoped:
            if not self.run_id:
                raise AegisProtocolError(
                    f"cannot run `aegis {' '.join(argv)}` without an AEGIS run "
                    "id; `run start` must succeed first"
                )
            command += ["--run", self.run_id]
        command.append("--json")
        command.extend(argv)
        result = self._execute(command, timeout)
        payload = _decode_envelope(
            result.stdout, result.exit_code, command, result.stderr
        )
        return self._response(result.exit_code, payload, command)

    def _execute(
        self,
        command: list[str],
        timeout: float | None,
    ):
        """@brief Execute one current-wrapper command under the 0/1 contract."""
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
        return result

    @staticmethod
    def _response(
        exit_code: int,
        payload: Mapping[str, Any],
        command: Sequence[str],
        *,
        warnings: tuple[str, ...] = (),
        advisories: tuple[AegisAdvisory, ...] = (),
    ) -> AegisResponse:
        """@brief Promote one already-validated envelope to AegisResponse."""
        return AegisResponse(
            exit_code=exit_code,
            status=payload["status"],
            stage=payload["stage"],
            artifact=payload["artifact"],
            next_command=payload["next"],
            raw=payload,
            argv=tuple(command),
            warnings=warnings,
            advisories=advisories,
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
            returned_kind = response.detail("kind")
            returned_profile = response.detail("run_profile", "full")
            if returned_kind != kind or returned_profile != ("quick" if quick else "full"):
                self.run_id = ""
                raise AegisProtocolError(
                    "AEGIS `run start` kind/profile disagrees with the requested run"
                )
            warnings = _bounded_strings(response.detail("warnings"), "warnings")
            response = self._response(
                response.exit_code,
                response.raw,
                response.argv,
                warnings=warnings,
            )
        return response

    def run_status(self) -> AegisResponse:
        """
        @brief      Read authoritative run state (stage, readiness, evidence).
        @return     The parsed AegisResponse.
        @exception  AegisProtocolError When the contract is violated.
        @exception  AegisTimeoutError When the command exceeded its bound.
        """
        response = self.invoke("run", "status", timeout=STATUS_TIMEOUT)
        if response.ok:
            returned_run = response.detail("run_id")
            if returned_run != self.run_id:
                raise AegisProtocolError(
                    f"AEGIS status run id {returned_run!r} disagrees with pinned run "
                    f"{self.run_id!r}"
                )
            if not isinstance(response.detail("complete"), bool):
                raise AegisProtocolError(
                    "AEGIS status response is missing boolean complete"
                )
            _ = response.terminal_outcome
        return response

    def run_context(
        self,
        *,
        expected_profile: str,
        expected_stage: str,
        expected_kind: str | None = None,
    ) -> AegisContext | AegisResponse:
        """
        @brief      Read the direct schema-1 fresh-session bootstrap response.
        @details    Exit 0 is AegisContext; exit 1 remains a validated blocked
                    envelope returned as AegisResponse.
        @param[in]  expected_profile Profile already established by status.
        @param[in]  expected_stage Stage already established by status.
        @param[in]  expected_kind Optional ADORE ticket-selected run kind.
        @return     Valid context or blocked envelope.
        """
        if not self.run_id:
            raise AegisProtocolError(
                "cannot run `aegis run context` without an AEGIS run id; "
                "`run start` must succeed first"
            )
        command = [
            "bash", WORKFLOW_CLI, "--run", self.run_id, "--json",
            "run", "context",
        ]
        result = self._execute(command, STATUS_TIMEOUT)
        if result.exit_code == 1:
            payload = _decode_envelope(
                result.stdout, result.exit_code, command, result.stderr
            )
            if payload["status"] != "blocked":
                raise AegisProtocolError(
                    "AEGIS `run context` exit 1 must be a blocked envelope"
                )
            return self._response(result.exit_code, payload, command)
        return _decode_context(
            result.stdout,
            command,
            result.stderr,
            pinned_run_id=self.run_id,
            expected_profile=expected_profile,
            expected_stage=expected_stage,
            expected_kind=expected_kind,
        )

    def run_resume(self) -> AegisResponse:
        """
        @brief      Read the run-orientation payload for a fresh session.
        @details    AEGIS 3.x answers `run resume` with the same envelope as
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

    def stage_prepare(self) -> AegisResponse:
        """
        @brief      Prepare a genuinely unprepared stage during safe recovery.
        @return     The parsed normal envelope.
        @exception  AegisProtocolError When the contract is violated.
        @exception  AegisTimeoutError When the command exceeded its bound.
        """
        return self.invoke("stage", "prepare", timeout=DEFAULT_TIMEOUT)

    def stage_close(self, approver: str, *, run_kind: str) -> AegisResponse:
        """
        @brief      Approve the current stage as the delegated approver.
        @details    In a conducted run ADORE - never the executor - issues the
                    close, and only after objective verification. The real
                    human approval stays at the draft MR review.
        @return     The parsed AegisResponse.
        @exception  AegisProtocolError When the contract is violated.
        @exception  AegisTimeoutError When the command exceeded its bound.
        """
        identity = approver.strip() if isinstance(approver, str) else ""
        if (
            not identity
            or identity != approver
            or len(identity.encode("utf-8")) > MAX_APPROVER_LENGTH
            or any(ord(character) < 32 for character in identity)
        ):
            raise AegisProtocolError(
                "AEGIS stage-close approver must be a bounded non-empty identity"
            )
        if run_kind not in RUN_KINDS:
            raise AegisProtocolError(f"invalid AEGIS run kind {run_kind!r}")
        response = self.invoke(
            "stage", "close", "--approver", identity, timeout=DEFAULT_TIMEOUT
        )
        if response.ok:
            if response.detail("approver") != identity:
                raise AegisProtocolError(
                    "AEGIS stage-close response did not record the delegated approver"
                )
            if not isinstance(response.detail("complete"), bool):
                raise AegisProtocolError(
                    "AEGIS stage-close response is missing boolean complete"
                )
            advisories = _decode_advisories(
                response.detail("advisories"), kind=run_kind
            )
            response = self._response(
                response.exit_code,
                response.raw,
                response.argv,
                advisories=advisories,
            )
        return response

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
        response = self.invoke("verify", "run", timeout=VERIFY_TIMEOUT)
        if not response.blocked:
            _ = response.verification_status
        return response

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
                    AEGIS 3.x governed before any run exists.
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
