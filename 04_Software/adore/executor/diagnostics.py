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
@file    diagnostics.py
@brief   Normalize operational diagnostics at the host capture boundary.
@details Host capture preserves concrete missing-module and test-result facts.
         A closed grammar suppresses arbitrary private content before immutable
         run-owned snapshots are bound to executor-artifacts journal entries.
"""

# IMPORTS
from collections import deque
from hashlib import sha256
import json
from pathlib import Path
import re
from uuid import uuid4

from adore.executor.base import GateRun
from adore.state import StateError

# CONSTANTS
LIMIT = 64 * 1024
_MODULE = re.compile(
    r"^ModuleNotFoundError: No module named ['\"]([A-Za-z_][A-Za-z0-9_.]{0,79})['\"]$")
_RESULT = r"[0-9]{1,7} (?:failed|passed|skipped|errors?|deselected|xfailed|xpassed)"
_SUMMARY = re.compile(
    rf"(?:=+\s*)?(?:pytest: )?(?P<counts>{_RESULT}(?:, {_RESULT})*)"
    r"(?:, [0-9]{1,7} warnings?)?(?: in [0-9]+(?:\.[0-9]+)?s(?: \([0-9:]+\))?)?"
    r"(?:\s*=+)?")
# Recognized credentials can also be syntactically valid Python module identifiers.
_CREDENTIAL_IDENTIFIER = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}|[a-fA-F0-9]{32,})")
_CATEGORIES = (
    ("not-found", r"ENOENT|MODULE_NOT_FOUND|ModuleNotFoundError|command not found|not recognized"),
    ("permission", r"EACCES|EPERM|permission denied"),
    ("credential", r"\b40[13]\b|invalid_api_key|unauthori[sz]ed|invalid_grant|sign in again"),
    ("rate-limit", r"\b429\b|rate.?limit|too many requests|quota"),
    ("network", r"ECONNREFUSED|ECONNRESET|ENOTFOUND|EAI_AGAIN|ETIMEDOUT|fetch failed"),
    ("model", r"model_not_found|model.*not (?:found|supported)"),
    ("timeout", r"timed? out|timeout|deadline"),
    ("protocol", r"malformed|invalid json|protocol"),
)


# PUBLIC API
def normalize_diagnostics(text: str) -> str:
    """
    @brief Keep concrete closed operational facts, withholding all arbitrary prose.
    @param[in] text Already credential-redacted protocol errors or tool/stderr diagnostics.
    @return At most 64 KiB of canonical exceptions, test counts and failure categories.
    @note No assistant content, tool arguments, paths, values or reasoning is forwarded.
    """
    rows = deque(maxlen=500)
    for raw in text.splitlines():
        line = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", raw).strip()
        module = _MODULE.fullmatch(line)
        summary = _SUMMARY.fullmatch(line)
        if module:
            rows.append("[other output withheld]" if _CREDENTIAL_IDENTIFIER.search(module[1])
                        else f"ModuleNotFoundError: No module named '{module[1]}'")
        elif summary:
            rows.append("pytest: " + summary["counts"])
        elif line in {"RPC completed", "RPC failed", "RPC timed-out", "RPC cancelled",
                       "RPC protocol-error", "[other output withheld]",
                       "AssertionError", "SyntaxError", "TypeError", "ImportError"}:
            rows.append(line)
        else:
            category = next((name for name, pattern in _CATEGORIES
                             if re.search(pattern, line, re.I)), None)
            if line.startswith("diagnostic: ") and line[12:] in {name for name, _ in _CATEGORIES}:
                category = line[12:]
            if category:
                rows.append("diagnostic: " + category)
            elif line:
                rows.append("[other output withheld]")
    # A row is short and ASCII; discard whole oldest rows rather than cutting a credential boundary.
    while sum(len(row) + 1 for row in rows) > LIMIT:
        rows.popleft()
    return "\n".join(rows)


def protocol_diagnostics(record: dict, clean) -> str:
    """
    @brief Select only protocol errors and failed tool results before normalization.
    @param[in] record Untrusted parsed Pi protocol object.
    @param[in] clean Existing bound credential redactor.
    @return Canonical diagnostics without assistant content or tool arguments.
    """
    text = ""
    if record.get("type") == "response" and record.get("success") is False:
        text = record.get("error", "")
    elif record.get("type") == "message_end":
        message = record.get("message")
        if isinstance(message, dict) and message.get("role") == "assistant":
            text = message.get("errorMessage", "")
    elif record.get("type") == "tool_execution_end" and record.get("isError") is True:
        result = record.get("result")
        content = result.get("content", []) if isinstance(result, dict) else []
        if isinstance(content, list):
            text = "\n".join(part["text"] for part in content if isinstance(part, dict)
                             and part.get("type") == "text" and isinstance(part.get("text"), str))
    return normalize_diagnostics(clean(text)) if isinstance(text, str) else ""


def validate_diagnostics(value: object) -> dict:
    """
    @brief Fail closed unless a snapshot contains exactly canonical bounded streams.
    @param[in] value Untrusted persisted or launcher-provided stream mapping.
    @return Validated canonical stream mapping.
    @exception StateError Invalid keys, stream types, bounds or canonical content.
    """
    if (not isinstance(value, dict) or set(value) != {"stdout", "stderr"}
            or any(not isinstance(text, str) or len(text.encode("utf-8")) > LIMIT
                   or normalize_diagnostics(text) != text for text in value.values())):
        raise StateError("invalid operational executor diagnostics")
    return value


def record_diagnostics(root: Path, run_id: str, attempt: int, context: str,
                       result: GateRun) -> dict | None:
    """
    @brief Persist host-normalized output outside writable executor IO and bind its digest.
    @param[in] root Authoritative run directory.
    @param[in] run_id Owning run identity.
    @param[in] attempt Cumulative executor launch number.
    @param[in] context Recorded launch context.
    @param[in] result Host-side launcher result; absent diagnostics stay unavailable.
    @return Journal reference to the exact immutable snapshot, or None.
    @exception StateError Invalid diagnostics or unsafe output location.
    """
    if result.diagnostics is None:
        return None
    streams = validate_diagnostics(result.diagnostics)
    folder = root / "executor-diagnostics"
    for parent in (folder, *folder.parents):
        if parent.is_symlink() or (parent.exists()
                and getattr(parent.lstat(), "st_file_attributes", 0) & 0x400):
            raise StateError("unsafe executor diagnostics location")
    folder.mkdir(parents=True, exist_ok=True)
    name = f"attempt-{attempt}-{uuid4().hex}.json"
    value = {"schema": 1, "run_id": run_id, "attempt": attempt, "context": context,
             "exit_code": result.exit_code, "timed_out": result.timed_out, **streams}
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True).encode("utf-8")
    with (folder / name).open("xb") as handle:
        handle.write(raw)
    return {"file": name, "sha256": sha256(raw).hexdigest(), "attempt": attempt}


# END OF FILE
