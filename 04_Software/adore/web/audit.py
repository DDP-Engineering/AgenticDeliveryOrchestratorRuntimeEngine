#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file audit.py
@brief Closed structured audit evidence and redaction contract.
@details Values are allowlisted before persistence and checked again on reads.
         Arbitrary text, nested credential metadata and environment values are redacted.
"""

from __future__ import annotations

# IMPORTS
from datetime import datetime
import json
import math
import re

# CONSTANTS
FIELDS = {
    "schema",
    "actor",
    "project_id",
    "resource_type",
    "resource_id",
    "phase",
    "result",
    "operation_id",
    "base_revision",
    "candidate_revision",
    "before",
    "after",
}
PHASES = {"prepare", "apply", "discard"}
RESULTS = {"prepared", "applied", "discarded", "rejected", "uncertain"}
TYPES = {"account", "access", "config", "project", "operation", "policy"}
_SAFE_FIELDS = {
    "exists",
    "disabled",
    "role",
    "project_ids",
    "granted",
    "pickup",
    "retention_days",
    "max_bytes",
    "value",
    "password_change_required",
}
_SAFE_WORDS = {"admin", "developer", "active", "stopped", "[redacted]"}


# DATA MODELS / TYPEDEFINITIONS
class AuditError(ValueError):
    """@brief Invalid or corrupt structured audit evidence."""


# PUBLIC API
def redact(value, *, depth: int = 0):
    """
    @brief Recursively project closed nonsecret values; arbitrary strings are redacted.
    @param[in] value Known before/after metadata, never a raw request body.
    @param[in] depth Bounded recursion depth.
    @return Redacted JSON-compatible evidence.
    """
    if depth > 8:
        return "[redacted]"
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float:
        return value if math.isfinite(value) else "[redacted]"
    if isinstance(value, str):
        return value if value in _SAFE_WORDS else "[redacted]"
    if isinstance(value, list):
        return [redact(item, depth=depth + 1) for item in value[:1000]]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key not in _SAFE_FIELDS:
                continue
            if key == "project_ids" and isinstance(item, list):
                result[key] = [
                    identity
                    for identity in item
                    if isinstance(identity, str) and re.fullmatch(r"[0-9a-f]{32}", identity)
                ]
            else:
                result[key] = redact(item, depth=depth + 1)
        return result
    return "[redacted]"


def evidence(
    *,
    actor: str | None,
    project_id: str | None = None,
    resource_type: str = "project",
    resource_id: str | None = None,
    phase: str = "apply",
    result: str = "applied",
    operation_id: int | None = None,
    base_revision: str | None = None,
    candidate_revision: str | None = None,
    before=None,
    after=None,
) -> dict:
    """@brief Construct and validate a closed redacted server-owned event payload."""
    value = dict(
        schema=1,
        actor=actor,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        phase=phase,
        result=result,
        operation_id=operation_id,
        base_revision=base_revision,
        candidate_revision=candidate_revision,
        before=redact(before),
        after=redact(after),
    )
    validate(value)
    return value


def validate(value: dict) -> dict:
    """@brief Fail closed on malformed persisted evidence or nonredacted values."""
    if (
        not isinstance(value, dict)
        or set(value) != FIELDS
        or type(value["schema"]) is not int
        or value["schema"] != 1
        or value["phase"] not in PHASES
        or value["result"] not in RESULTS
        or value["resource_type"] not in TYPES
        or value["result"] == "applied"
        and value["phase"] != "apply"
        or value["result"] == "prepared"
        and value["phase"] != "prepare"
        or value["result"] == "discarded"
        and value["phase"] != "discard"
    ):
        raise AuditError("audit evidence is corrupt")
    for key, pattern in (
        ("actor", r"[\w]{1,64}"),
        ("project_id", r"[0-9a-f]{32}"),
        ("resource_id", r"[A-Za-z0-9._-]{1,160}"),
        ("base_revision", r"[0-9a-f]{64}"),
        ("candidate_revision", r"[0-9a-f]{64}"),
    ):
        item = value[key]
        if item is not None and (not isinstance(item, str) or not re.fullmatch(pattern, item)):
            raise AuditError("audit evidence is corrupt")
    if value["operation_id"] is not None and (
        type(value["operation_id"]) is not int or value["operation_id"] < 1
    ):
        raise AuditError("audit evidence is corrupt")
    for key in ("before", "after"):
        if redact(value[key]) != value[key]:
            raise AuditError("audit evidence is corrupt")
    if value["result"] in ("rejected", "uncertain") and value["after"] is not None:
        raise AuditError("audit evidence is corrupt")
    return value


def decode(raw: str) -> dict:
    """@brief Decode a bounded persisted payload with the exact evidence schema."""
    try:
        if not isinstance(raw, str) or len(raw) > 131072:
            raise ValueError("invalid size")

        def pairs(items):
            """@brief Reject ambiguous duplicate fields at each JSON nesting depth."""
            result = {}
            for key, item in items:
                if key in result:
                    raise AuditError("audit evidence is corrupt")
                result[key] = item
            return result

        return validate(json.loads(raw, object_pairs_hook=pairs))
    except (TypeError, ValueError, KeyError, RecursionError) as exc:
        raise AuditError("audit evidence is corrupt") from exc


def instant(value: str) -> str:
    """@brief Validate a timezone-aware UTC instant used for half-open filtering."""
    try:
        stamp = datetime.fromisoformat(value)
        if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
            raise ValueError("not UTC")
        return stamp.isoformat()
    except (TypeError, ValueError, AttributeError) as exc:
        raise AuditError("invalid audit period") from exc


# END OF FILE
