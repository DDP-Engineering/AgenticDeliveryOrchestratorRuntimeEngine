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
@file    executor_session.py
@brief   Bounded recorded Pi sessions within an authorized run.
@details Reads complete lines only, never system messages or other run files.
         Caller owns authentication and cost visibility. No text redaction occurs.
"""

# IMPORTS
import json
import math
import os
from pathlib import Path
import re

from adore.web.executor_evidence import _identity, _read, _signature
from adore.web.jobs import JobReadError, _object, _stamp

# CONSTANTS
_ATTEMPT = re.compile(
    r"(frame|specify|design|build|validate)-attempt-([1-9][0-9]*)"
    r"-attempt1(?:-([2-9]|[1-9][0-9]+))?")
_TEXT_BYTES = 16 * 1024
_LINE_BYTES = 256 * 1024
_SCAN_BYTES = 4 * 1024 * 1024
_FILE_BYTES = 64 * 1024 * 1024
_MAX_ARCHIVES = 10000


# LOCAL HELPERS
def _folder(path: Path) -> None:
    """@brief Check every parent for symlinks and reparse points."""
    for parent in (path, *path.parents):
        _identity(parent, directory=True)


def _text(value) -> str:
    """@brief Bound one readable value by UTF-8 bytes, retaining literal text."""
    value = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    raw = value.encode("utf-8")
    if len(raw) <= _TEXT_BYTES:
        return value
    marker = "\n[truncated]"
    return raw[:_TEXT_BYTES - len(marker)].decode("utf-8", errors="ignore") + marker


def _notice(text: str) -> dict:
    return {"kind": "notice", "text": text}


def _usage(value, include_cost: bool) -> dict:
    """@brief Project recognized finite usage counters, restricting structured costs."""
    if not isinstance(value, dict):
        raise ValueError("invalid usage")
    result = {}
    for key in ("input", "output", "cacheRead", "cacheWrite", "reasoning", "totalTokens"):
        if key in value:
            number = value[key]
            if type(number) is not int or not 0 <= number <= 2**53 - 1:
                raise ValueError("invalid tokens")
            result[key] = number
    if include_cost and "cost" in value:
        cost = value["cost"]
        if not isinstance(cost, dict):
            raise ValueError("invalid cost")
        result["cost"] = {}
        for key in ("input", "output", "cacheRead", "cacheWrite", "total"):
            if key in cost:
                number = cost[key]
                if (type(number) not in (int, float) or not 0 <= number <= 1e300
                        or not math.isfinite(number)):
                    raise ValueError("invalid cost")
                result["cost"][key] = number
    return result


def _items(record: dict, include_cost: bool) -> list[dict]:
    """@brief Convert one untrusted event to bounded readable items."""
    if not isinstance(record, dict):
        raise ValueError("invalid event")
    kind = record.get("type")
    if kind == "adore_malformed_record":
        return [_notice("Malformed session record omitted by the executor.")]
    if "adore_omitted_bytes" in record:
        return [_notice("Record omitted by the executor (oversize).")]
    if kind == "adore_output_truncated" or "adore_output_truncated" in record:
        return [_notice("Executor output was truncated.")]
    if kind in {"turn_start", "turn_end"}:
        return [{"kind": "turn", "text": kind}]
    if kind == "tool_execution_start":
        if not isinstance(record.get("toolName"), str) or not isinstance(record.get("args"), dict):
            raise ValueError("invalid tool call")
        return [{"kind": "tool_call", "text": _text(record["args"]),
                 "tool": _text(record["toolName"]), "call_id": _text(record.get("toolCallId", ""))}]
    if kind == "tool_execution_end":
        if type(record.get("isError")) is not bool or not isinstance(record.get("result"), dict):
            raise ValueError("invalid tool result")
        content = record["result"].get("content", [])
        if not isinstance(content, list):
            raise ValueError("invalid tool content")
        text = "\n".join(part["text"] for part in content
                         if isinstance(part, dict) and part.get("type") == "text"
                         and isinstance(part.get("text"), str))
        return [{"kind": "tool_result", "text": _text(text),
                 "tool": _text(record.get("toolName", "")),
                 "call_id": _text(record.get("toolCallId", "")), "is_error": record["isError"]}]
    if kind != "message_end":
        return []
    message = record.get("message")
    if not isinstance(message, dict):
        raise ValueError("invalid message")
    role = message.get("role")
    if role not in {"user", "assistant"}:
        return []
    content = message.get("content")
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    if not isinstance(content, list):
        raise ValueError("invalid content")
    texts, reasoning = [], []
    for part in content:
        if not isinstance(part, dict):
            raise ValueError("invalid part")
        if part.get("type") == "text":
            if not isinstance(part.get("text"), str):
                raise ValueError("invalid text")
            texts.append(part["text"])
        elif role == "assistant" and part.get("type") == "thinking":
            if isinstance(part.get("thinking"), str):
                reasoning.append(part["thinking"])
    result = []
    if texts:
        result.append({"kind": "prompt" if role == "user" else "assistant",
                       "text": _text("\n".join(texts))})
    if reasoning:
        result.append({"kind": "reasoning", "text": _text("\n".join(reasoning))})
    if role == "assistant" and "usage" in message:
        result.append({"kind": "usage", "text": "",
                       "usage": _usage(message["usage"], include_cost)})
    return result


def _metadata(folder: Path) -> dict:
    """@brief Validate current archive metadata without reading command or scripts."""
    match = _ATTEMPT.fullmatch(folder.name)
    if not match:
        raise JobReadError("run_not_found", 404)
    _folder(folder)
    meta = _object(_read(folder / "meta.json", 64 * 1024), "job_evidence_corrupt")
    if (type(meta.get("exit_code")) is not int or type(meta.get("timed_out")) is not bool
            or abs(meta["exit_code"]) > 2**53 - 1 or int(match[2]) > 2**53 - 1
            or meta.get("archive_stem") != f"{match[1]}-attempt-{match[2]}"):
        raise JobReadError("job_evidence_corrupt")
    end_at = _stamp(meta.get("created_at"), "job_evidence_corrupt")
    if end_at is None:
        raise JobReadError("job_evidence_corrupt")
    return {"id": folder.name, "stage": match[1], "attempt": int(match[2]),
            "start_at": None, "end_at": end_at,
            "outcome": "timed_out" if meta["timed_out"] else
            "succeeded" if meta["exit_code"] == 0 else "failed",
            "exit_code": meta["exit_code"]}


# PUBLIC API
def list_sessions(run: Path) -> list[dict]:
    """
    @brief List completed physical launches newest first in an authorized run.
    @param[in] run Verified run directory, never a browser-supplied path.
    @return Bounded metadata; absent archives are an empty list.
    @exception JobReadError Unsafe or corrupt archive metadata.
    """
    archive = run / "io" / "archive"
    try:
        _folder(run)
        if (run / "io").exists() or (run / "io").is_symlink():
            _folder(run / "io")
        if not archive.exists() and not archive.is_symlink():
            return []
        _folder(archive)
        sessions = []
        for index, folder in enumerate(archive.iterdir()):
            if index >= _MAX_ARCHIVES:
                raise JobReadError("job_evidence_corrupt")
            if _ATTEMPT.fullmatch(folder.name):
                sessions.append(_metadata(folder))
        return sorted(sessions, key=lambda item: (item["end_at"], item["id"]), reverse=True)
    except JobReadError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise JobReadError("job_evidence_corrupt") from exc


def read_session(run: Path, attempt_id: str, cursor: int = 0, limit: int = 200,
                 *, include_cost: bool = False) -> dict:
    """
    @brief Read complete JSONL records with bounded memory and line-start cursors.
    @param[in] run Authorized run directory.
    @param[in] attempt_id Exact existing archive folder name.
    @param[in] cursor Byte offset at a complete line start.
    @param[in] limit Maximum number of source items, from 1 to 200.
    @param[in] include_cost Administrator structured-cost visibility.
    @return Items and next_cursor; a message groups its text/reasoning/usage parts.
    @exception JobReadError Invalid cursor, missing attempt or unsafe source.
    @note Records never split across pages; each grouped part has its own text bound.
    """
    if (not isinstance(attempt_id, str) or not _ATTEMPT.fullmatch(attempt_id)
            or type(cursor) is not int or cursor < 0 or cursor > 2**53 - 1
            or type(limit) is not int or not 1 <= limit <= 200):
        raise JobReadError("run_not_found", 404)
    folder = run / "io" / "archive" / attempt_id
    try:
        session = _metadata(folder)
        path = folder / "output.jsonl"
        before = _identity(path)
        # A deliberately huge physical line cannot make a request scan unbounded
        # work. Ordinary malformed lines still skip through to subsequent records.
        if before.st_size > _FILE_BYTES:
            if cursor:
                raise JobReadError("job_evidence_corrupt")
            return {"session": session,
                    "items": [_notice("Session exceeds the 64 MiB read bound.")],
                    "next_cursor": None}
        items = []
        with path.open("rb") as source:
            if _signature(os.fstat(source.fileno())) != _signature(before):
                raise JobReadError("job_snapshot_changed", 409)
            if cursor > before.st_size:
                raise JobReadError("job_evidence_corrupt")
            if cursor:
                source.seek(cursor - 1)
                if source.read(1) != b"\n":
                    raise JobReadError("job_evidence_corrupt")
            source.seek(cursor)
            scanned, next_cursor = 0, None
            while source.tell() < before.st_size and scanned < _SCAN_BYTES:
                line = source.readline(_LINE_BYTES + 1)
                scanned += len(line)
                oversize = len(line) > _LINE_BYTES
                while not line.endswith(b"\n") and source.tell() < before.st_size:
                    chunk = source.readline(_LINE_BYTES + 1)
                    scanned += len(chunk)
                    line = chunk
                    oversize = True
                if not line.endswith(b"\n"):
                    # Completed archives never gain a finished tail later. Do not
                    # offer an endless Load more loop for an interrupted record.
                    next_cursor = None
                    break
                if oversize:
                    batch = [_notice("Oversize session record omitted.")]
                else:
                    try:
                        batch = _items(_object(line, "job_evidence_corrupt"), include_cost)
                    except (JobReadError, UnicodeError, ValueError, TypeError,
                            KeyError, RecursionError):
                        batch = [_notice("Malformed session record omitted.")]
                if len(batch) > 1:
                    batch = [{"kind": "assistant", "text": "", "parts": batch}]
                items.extend(batch)
                if len(items) >= limit:
                    next_cursor = source.tell() if source.tell() < before.st_size else None
                    break
            else:
                next_cursor = source.tell() if source.tell() < before.st_size else None
            if (_signature(os.fstat(source.fileno())) != _signature(before)
                    or _signature(_identity(path)) != _signature(before)):
                raise JobReadError("job_snapshot_changed", 409)
        _folder(folder)
        return {"session": session, "items": items, "next_cursor": next_cursor}
    except FileNotFoundError as exc:
        raise JobReadError("run_not_found", 404) from exc
    except JobReadError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise JobReadError("job_evidence_corrupt") from exc


# END OF FILE
