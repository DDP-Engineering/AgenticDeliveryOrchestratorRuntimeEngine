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
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re

from adore.state import StateError, StateStore
from adore.web.executor_evidence import _identity, _read, _signature
from adore.web.jobs import JobReadError, _object, _stamp

# CONSTANTS
_ATTEMPT = re.compile(
    r"(frame|specify|design|build|validate)-attempt-([1-9][0-9]*)"
    r"-attempt1(?:-([2-9]|[1-9][0-9]+))?")
_LIVE = re.compile(r"live-[a-f0-9]{32}")
_TEXT_BYTES = 16 * 1024 * 1024
_LINE_BYTES = _TEXT_BYTES + 64 * 1024
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
    raise ValueError("session item exceeds the record bound")


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
    if kind == "adore_prompt":
        if not isinstance(record.get("text"), str):
            raise ValueError("invalid prompt")
        identity = record.get("instruction_id", "")
        if identity != "adore-prompt" and not re.fullmatch(r"[a-f0-9]{32}", identity):
            raise ValueError("invalid instruction identity")
        return [{"kind": "prompt", "text": _text(record["text"]),
                 **({"instruction_id": identity} if identity != "adore-prompt" else {})}]
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


def _live_metadata(run: Path) -> dict | None:
    """@brief Resolve only a working run's exact launch-owned marker."""
    _folder(run)
    state = _object(_read(run / "state.json", 4 * 1024 * 1024), "job_evidence_corrupt")
    if state.get("lifecycle") != "working":
        return None
    io = run / "io"
    if not io.exists() and not io.is_symlink():
        return None
    _folder(io)
    try:
        marker = _object(_read(io / "live.json", 4096), "job_evidence_corrupt")
    except FileNotFoundError:
        return None
    lock_store = StateStore(io)
    try:
        _folder(lock_store.locks_root)
        _identity(lock_store.locks_root / "run-agent-session.lock")
        if not lock_store.run_locked("agent-session"):
            return None
    except FileNotFoundError:
        return None
    except StateError as exc:
        raise JobReadError("job_evidence_corrupt") from exc
    match = _ATTEMPT.fullmatch(marker.get("archive_id", ""))
    if (type(marker.get("schema")) is not int or marker["schema"] != 1
            or not _LIVE.fullmatch(marker.get("id", ""))
            or not match or int(match[2]) > 2**53 - 1):
        raise JobReadError("job_evidence_corrupt")
    start = _stamp(marker.get("start_at"), "job_evidence_corrupt")
    if start is None:
        raise JobReadError("job_evidence_corrupt")
    return {"id": marker["id"], "live": True, "archive_id": marker["archive_id"],
            "stage": match[1], "attempt": int(match[2]), "start_at": start,
            "end_at": None, "outcome": None, "exit_code": None}


def _continuity(source, info, launch: str, cursor: int) -> str:
    """@brief Hash a bounded consumed prefix and stable file/launch identity."""
    digest = sha256(f"{info.st_dev}:{info.st_ino}:{launch}:".encode())
    source.seek(0)
    remaining = cursor
    while remaining:
        chunk = source.read(min(remaining, 65536))
        if not chunk:
            return ""
        digest.update(chunk)
        remaining -= len(chunk)
    return digest.hexdigest()


# PUBLIC API
def list_sessions(run: Path) -> list[dict]:
    """
    @brief List an owned active launch first, then completed launches newest first.
    @param[in] run Verified run directory, never a browser-supplied path.
    @return Bounded metadata; absent archives are an empty list.
    @exception JobReadError Unsafe or corrupt archive metadata.
    """
    archive = run / "io" / "archive"
    try:
        _folder(run)
        live = _live_metadata(run)
        if (run / "io").exists() or (run / "io").is_symlink():
            _folder(run / "io")
        if not archive.exists() and not archive.is_symlink():
            return [live] if live else []
        _folder(archive)
        sessions = []
        for index, folder in enumerate(archive.iterdir()):
            if index >= _MAX_ARCHIVES:
                raise JobReadError("job_evidence_corrupt")
            if _ATTEMPT.fullmatch(folder.name):
                if (live and folder.name == live["archive_id"]
                        and not (folder / "meta.json").exists()):
                    continue
                sessions.append(_metadata(folder))
        return ([live] if live else []) + sorted(
            sessions, key=lambda item: (item["end_at"], item["id"]), reverse=True)
    except JobReadError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise JobReadError("job_evidence_corrupt") from exc


def read_session(run: Path, attempt_id: str, cursor: int = 0, limit: int = 200,
                 *, include_cost: bool = False, continuity: str | None = None,
                 archive_id: str | None = None) -> dict:
    """
    @brief Read complete JSONL records with bounded memory and line-start cursors.
    @param[in] run Authorized run directory.
    @param[in] attempt_id Exact existing archive folder name.
    @param[in] cursor Byte offset at a complete line start.
    @param[in] limit Maximum number of source items, from 1 to 200.
    @param[in] include_cost Administrator structured-cost visibility.
    @param[in] continuity Stable file and consumed-prefix proof for live continuation.
    @param[in] archive_id Exact handoff identity retained by a live caller.
    @return Items and next_cursor; a message groups its text/reasoning/usage parts.
    @exception JobReadError Invalid cursor, missing attempt or unsafe source.
    @note Records never split across pages; each grouped part has its own text bound.
    """
    live = isinstance(attempt_id, str) and bool(_LIVE.fullmatch(attempt_id))
    if (not isinstance(attempt_id, str) or not (live or _ATTEMPT.fullmatch(attempt_id))
            or type(cursor) is not int or cursor < 0 or cursor > 2**53 - 1
            or type(limit) is not int or not 1 <= limit <= 200):
        raise JobReadError("run_not_found", 404)
    if ((continuity is not None and not re.fullmatch(r"[a-f0-9]{64}", continuity))
            or (archive_id is not None and not _ATTEMPT.fullmatch(archive_id))):
        raise JobReadError("job_evidence_corrupt")
    ended = {"session_ended": True, "archive_id": archive_id,
             "items": [], "next_cursor": None}
    folder = run / "io" if live else run / "io" / "archive" / attempt_id
    try:
        session = _live_metadata(run) if live else _metadata(folder)
        if live:
            if not session or session["id"] != attempt_id:
                return ended
            ended["archive_id"] = session["archive_id"]
            _folder(folder)
        path = folder / "output.jsonl"
        before = _identity(path)
        if before.st_size > _FILE_BYTES:
            if cursor:
                if live:
                    return ended
                raise JobReadError("job_evidence_corrupt")
            return {"session": session,
                    "items": [_notice("Session exceeds the 64 MiB read bound.")],
                    "next_cursor": None,
                    **({"session_ended": False, "thinking": None, "read_bound": True}
                       if live else {})}
        items = []
        with path.open("rb") as source:
            opened = os.fstat(source.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                if live:
                    return ended
                raise JobReadError("job_snapshot_changed", 409)
            if cursor > before.st_size:
                if live:
                    return ended
                raise JobReadError("job_evidence_corrupt")
            captured = sha256(f"{before.st_dev}:{before.st_ino}:{attempt_id}:".encode())
            if live:
                remaining = cursor
                while remaining:
                    chunk = source.read(min(remaining, 65536))
                    if not chunk:
                        return ended
                    captured.update(chunk)
                    remaining -= len(chunk)
                if continuity is not None and captured.hexdigest() != continuity:
                    return ended
                if cursor and continuity is None:
                    raise JobReadError("job_evidence_corrupt")
            if cursor:
                source.seek(cursor - 1)
                if source.read(1) != b"\n":
                    raise JobReadError("job_evidence_corrupt")
            source.seek(cursor)
            scanned, consumed, thinking = 0, cursor, None
            while source.tell() < before.st_size and scanned < _SCAN_BYTES:
                prior = captured.copy()
                line = source.readline(min(_LINE_BYTES + 1, before.st_size - source.tell()))
                if not line:
                    if live:
                        return ended
                    raise JobReadError("job_snapshot_changed", 409)
                scanned += len(line)
                captured.update(line)
                oversize = len(line) > _LINE_BYTES
                while not line.endswith(b"\n") and source.tell() < before.st_size:
                    line = source.readline(min(_LINE_BYTES + 1, before.st_size - source.tell()))
                    if not line:
                        if live:
                            return ended
                        raise JobReadError("job_snapshot_changed", 409)
                    scanned += len(line)
                    captured.update(line)
                    oversize = True
                if not line.endswith(b"\n"):
                    captured = prior
                    break
                if oversize:
                    batch = [_notice("Oversize session record omitted.")]
                else:
                    try:
                        record = _object(line, "job_evidence_corrupt")
                        batch = _items(record, include_cost)
                        stamp = _stamp(record.get("adore_at", ""), "job_evidence_corrupt")
                        if stamp:
                            for item in batch:
                                item["at"] = stamp
                        if live:
                            if (record.get("type") == "message_start"
                                    and isinstance(record.get("message"), dict)
                                    and record["message"].get("role") == "assistant"):
                                thinking = True
                            elif record.get("type") in {
                                    "message_end", "agent_end", "agent_settled"}:
                                thinking = False
                    except (JobReadError, UnicodeError, ValueError, TypeError,
                            KeyError, RecursionError):
                        batch = [_notice("Malformed session record omitted.")]
                if len(batch) > 1:
                    batch = [{"kind": "assistant", "text": "", "parts": batch}]
                items.extend(batch)
                consumed = source.tell()
                if len(items) >= limit:
                    break
            if live:
                next_cursor = consumed
                token = captured.hexdigest()
                # Never verify through the parser's read-ahead cache: a seek
                # within that buffer can otherwise hide a same-inode rewrite.
                with path.open("rb", buffering=0) as verification:
                    verified = os.fstat(verification.fileno())
                    if ((verified.st_dev, verified.st_ino) != (before.st_dev, before.st_ino)
                            or _continuity(verification, before, attempt_id, consumed) != token):
                        return ended
                after = _identity(path)
                opened = os.fstat(source.fileno())
                if ((after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
                        or min(after.st_size, opened.st_size) < before.st_size
                        or _live_metadata(run) != session):
                    return ended
            else:
                # An interrupted archived tail has no future complete record.
                next_cursor = (consumed if consumed < before.st_size
                               and source.tell() == consumed else None)
                if (_signature(os.fstat(source.fileno())) != _signature(before)
                        or _signature(_identity(path)) != _signature(before)):
                    raise JobReadError("job_snapshot_changed", 409)
        _folder(folder)
        result = {"session": session, "items": items, "next_cursor": next_cursor}
        if live:
            result.update(session_ended=False, continuity=token, thinking=thinking)
        return result
    except FileNotFoundError as exc:
        if live:
            return ended
        raise JobReadError("run_not_found", 404) from exc
    except JobReadError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise JobReadError("job_evidence_corrupt") from exc


# END OF FILE
