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
@file fake_pi_rpc.py
@brief Fake `pi --mode rpc` process that replays recorded spike fixtures.
@details Run as a child process by the tests (stdlib only). Each fixture line is
         an envelope `{"t_ms", "dir", "record"}` written by the PI-01 probe. The
         fake answers every stdin command with the recorded output that
         followed the same command type in the fixture, so the client decides
         when to send `abort`. Response ids are rewritten to the client's ids.
         Options inject the failure modes the recordings do not contain.
         `<NONCE>` and `<TOOL_NONCE>` in a recording (the Test AI connection
         challenge) are replaced by the nonces of the prompt actually sent.
@example python fake_pi_rpc.py fixture.jsonl --record commands.log --hang
"""

from __future__ import annotations

# IMPORTS
import argparse
import json
from pathlib import Path
import re
import sys
import time
from uuid import uuid4

# CONSTANTS
#: Placeholder -> value, filled from the prompt the client sent.
NONCES: dict[str, str] = {}
SESSION: list[dict] = []


def _append(options, message: dict) -> None:
    """@brief Simulate Pi-owned append-only session persistence without a model."""
    if options.session_file is None:
        return
    SESSION.append({"type": "message", "id": uuid4().hex,
                    "parentId": SESSION[-1].get("id") if len(SESSION) > 1 else None,
                    "message": message})
    options.session_file.write_text(
        "".join(json.dumps(row) + "\n" for row in SESSION), encoding="utf-8")

# HELPER FUNCTIONS


def _segments(path: Path) -> tuple[list[dict], list[tuple[dict, list[dict]]], int]:
    """
    @brief      Split a fixture into the output answering each stdin command.
    @param[in]  path Fixture file.
    @return     (leading envelopes, [(stdin record, following envelopes)], exit code).
    """
    leading: list[dict] = []
    segments: list[tuple[dict, list[dict]]] = []
    exit_code = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        envelope = json.loads(line)
        if envelope["dir"] == "exit":
            exit_code = int(envelope["record"].get("returncode", 0))
        elif envelope["dir"] == "stdin":
            segments.append((envelope["record"], []))
        elif envelope["dir"] in ("stdout", "stderr"):
            (segments[-1][1] if segments else leading).append(envelope)
    return leading, segments, exit_code


def _write(record: object, key_hint: str) -> None:
    """
    @brief      Write one protocol record as an LF-terminated JSON line.
    @param[in]  record Record to write.
    @param[in]  key_hint Replacement for the fixture's redacted key hint.
    """
    text = json.dumps(record, ensure_ascii=False)
    for placeholder, value in NONCES.items():
        text = text.replace(placeholder, value)
    if key_hint:
        text = text.replace("<REDACTED_KEY_HINT>", key_hint)
    sys.stdout.buffer.write(text.encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()


def _emit(envelopes: list[dict], command: dict, options: argparse.Namespace,
          *, limit: int | None = None) -> int:
    """
    @brief      Replay envelopes, rewriting response ids to the command's id.
    @param[in]  envelopes Recorded output following the command.
    @param[in]  command Command the client actually sent.
    @param[in]  options Parsed fake options.
    @param[in]  limit Maximum number of stdout records to write.
    @return     Number of stdout records written.
    """
    written = 0
    padded = False
    assistant_ends = [index for index, envelope in enumerate(envelopes)
                      if envelope["dir"] == "stdout" and isinstance(envelope["record"], dict)
                      and envelope["record"].get("type") == "message_end"
                      and envelope["record"].get("message", {}).get("role") == "assistant"]
    pad_index = (assistant_ends[-1] if options.pad_last and assistant_ends
                 else assistant_ends[0] if assistant_ends else -1)
    for index, envelope in enumerate(envelopes):
        record = envelope["record"]
        if (isinstance(record, dict) and record.get("type") == "message_end"
                and isinstance(record.get("message"), dict)):
            _append(options, record["message"])
        if envelope["dir"] == "stderr":
            sys.stderr.write(str(record) + "\n")
            sys.stderr.flush()
            continue
        if limit is not None and written >= limit:
            break
        if isinstance(record, dict) and record.get("type") == "response" and "id" in command:
            record = {**record, "id": command["id"]}
        if options.pad_message_end and not padded and index == pad_index:
            record = {**record, "padding": "x" * options.pad_message_end}
            padded = True
        _write(record, options.key_hint)
        written += 1
        if written == 1 and command.get("type") == "prompt":
            if options.garbage:
                sys.stdout.buffer.write(b"this is not a protocol record\n")
                sys.stdout.buffer.flush()
            if options.deep:
                sys.stdout.buffer.write(b'{"type":"tool_execution_update","a":'
                                        + b"[" * options.deep + b"]" * options.deep + b"}\n")
                sys.stdout.buffer.flush()
            for _ in range(options.big_count):
                _write({"type": "tool_execution_update", "toolName": "bash",
                        "partialResult": {"content": [
                            {"type": "text", "text": "y" * options.big_size}]}},
                       options.key_hint)
            if options.oversize:
                _write({"type": "tool_execution_update", "toolName": "bash",
                        "partialResult": {"content": [
                            {"type": "text", "text": "z" * options.oversize}]}},
                       options.key_hint)
    return written


# PUBLIC API


def main() -> int:
    """
    @brief      Replay a fixture against the commands read from stdin.
    @return     The recorded (or overridden) exit code.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--hang", action="store_true")
    parser.add_argument("--ignore-abort", action="store_true")
    parser.add_argument("--crash-after", type=int)
    parser.add_argument("--garbage", action="store_true")
    parser.add_argument("--big-count", type=int, default=0)
    parser.add_argument("--big-size", type=int, default=0)
    parser.add_argument("--oversize", type=int, default=0)
    parser.add_argument("--pad-message-end", type=int, default=0)
    parser.add_argument("--pad-last", action="store_true")
    parser.add_argument("--deep", type=int, default=0)
    parser.add_argument("--key-hint", default="")
    parser.add_argument("--exit", type=int)
    parser.add_argument("--session-file", type=Path)
    parser.add_argument("--session-path")
    parser.add_argument("--session-cwd")
    parser.add_argument("--bad-session-state", choices=("path", "id", "tokens"))
    options = parser.parse_args()
    if options.session_file is not None:
        if options.session_file.exists():
            SESSION.extend(json.loads(line) for line in options.session_file.read_text(
                encoding="utf-8").splitlines())
        else:
            SESSION.append({"type": "session", "version": 3, "id": uuid4().hex,
                            "cwd": options.session_cwd})
    leading, segments, exit_code = _segments(options.fixture)
    for envelope in leading:
        if envelope["dir"] == "stderr":
            sys.stderr.write(str(envelope["record"]) + "\n")
    position = 0
    for raw in sys.stdin.buffer:
        if options.record:
            with options.record.open("ab") as handle:
                handle.write(raw)
        command = json.loads(raw)
        kind = command.get("type")
        if options.session_file is not None and kind == "get_state":
            _write({"id": command.get("id"), "type": "response", "command": kind,
                    "success": True, "data": {
                    "sessionId": "foreign-job" if options.bad_session_state == "id"
                    else SESSION[0]["id"],
                    "sessionFile": "/foreign/session.jsonl" if options.bad_session_state == "path"
                    else options.session_path}}, "")
            continue
        if options.session_file is not None and kind == "get_session_stats":
            totals = {key: 0 for key in ("input", "output", "cacheRead", "cacheWrite")}
            for row in SESSION:
                for key in totals:
                    totals[key] += row.get("message", {}).get("usage", {}).get(key, 0)
            _write({"id": command.get("id"), "type": "response", "command": kind,
                    "success": True, "data": {
                    "tokens": {} if options.bad_session_state == "tokens" else totals}}, "")
            continue
        if kind == "prompt":
            _append(options, {"role": "user", "content": command.get("message", "")})
            message = str(command.get("message", ""))
            for placeholder, pattern in (("<NONCE>", r"ADORE_OK_[0-9a-f]+"),
                                         ("<TOOL_NONCE>", r"ADORE_TOOL_[0-9a-f]+")):
                found = re.search(pattern, message)
                if found:
                    NONCES[placeholder] = found.group(0)
        if options.ignore_abort and kind == "abort":
            continue
        if options.hang and kind == "abort":
            _write({"type": "agent_settled", "aborted": True}, "")
            _write({"id": command.get("id"), "type": "response", "command": "abort",
                    "success": True}, "")
            continue
        index = next((i for i in range(position, len(segments))
                      if segments[i][0].get("type") == kind), None)
        if index is None:
            _write({"id": command.get("id"), "type": "response", "command": kind,
                    "success": False, "error": "fake: no recorded response"}, "")
            continue
        position = index + 1
        envelopes = segments[index][1]
        if kind == "prompt" and options.hang:
            _emit(envelopes, command, options, limit=1)
            continue
        if kind == "prompt" and options.crash_after is not None:
            _emit(envelopes, command, options, limit=options.crash_after)
            return 3
        _emit(envelopes, command, options)
    if options.ignore_abort:
        time.sleep(60)
    code = exit_code if options.exit is None else options.exit
    return code if 0 <= code < 256 else 3


if __name__ == "__main__":
    raise SystemExit(main())

# END OF FILE
