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
@file pi_rpc.py
@brief Drive one Pi `--mode rpc` process for one stage with bounded memory.
@details Pi's RPC mode speaks one JSON object per LF-terminated line on stdin
         and stdout. One process serves one stage: ADORE sends the prompt, keeps
         stdin open, and reads events until `agent_settled`, the only reliable
         end of a run. Done means settled, not aborted, and the last assistant
         message not ending with stopReason `error`; the exit code is not the
         result (Pi can crash on exit after a clean run).

         On the stage deadline or a cancellation request ADORE sends `abort`,
         waits a grace period for `agent_settled`, closes stdin (Pi's shutdown
         request), and terminates the process after a further grace period.

         Memory stays bounded: a reader thread holds at most one record of
         `max_record_bytes`, reduces it to a few small facts for the caller
         (usage, stop reason, tool status), persists a bounded copy for evidence
         and drops it. Streaming deltas are never persisted. Usage is summed over
         every assistant `message_end` (one per turn) and cross-checked once with
         `get_session_stats`. Pi's cost is an estimate, so no cost is reported.
@example result = run_pi_rpc(spawn, argv, env, prompt, timeout=1800)
"""

from __future__ import annotations

# IMPORTS
from collections import deque
from collections.abc import Callable, Iterator
import contextlib
from dataclasses import dataclass, field
import json
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
from typing import IO, Any

# CONSTANTS

ABORT_GRACE_SECONDS = 10.0
EXIT_GRACE_SECONDS = 5.0
KILL_GRACE_SECONDS = 5.0
STATS_GRACE_SECONDS = 5.0
POLL_SECONDS = 0.2

MAX_RECORD_BYTES = 16 * 1024 * 1024
PERSIST_RECORD_BYTES = 64 * 1024
PERSIST_TOTAL_BYTES = 32 * 1024 * 1024
STDERR_FILE_BYTES = 1024 * 1024
TAIL_BYTES = 64 * 1024
MESSAGE_CHARS = 2000
_CHUNK_BYTES = 64 * 1024
_PREFIX_BYTES = 512

EXIT_FAILED = 1
EXIT_NOT_EXECUTABLE = 126
EXIT_NOT_FOUND = 127
EXIT_TIMEOUT = 124
EXIT_CANCELLED = 130

GUARD_REASON_PREFIX = "ADORE blocks"

_UNREADABLE = "adore-unreadable"
_PROMPT_ID = "adore-prompt"
_ABORT_ID = "adore-abort"
_STATS_ID = "adore-stats"
_TOKEN_LIMIT = 1_000_000_000

_KEY_HINT_RE = re.compile(r"\b[A-Za-z]{2,8}-[A-Za-z0-9_-]*\*{3,}[A-Za-z0-9_-]*")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")
_TYPE_RE = re.compile(rb'"type"\s*:\s*"([A-Za-z_]+)"')
_ROLE_RE = re.compile(rb'"role"\s*:\s*"([A-Za-z]+)"')

#: Failure classes in match order: the first pattern found in Pi's error wins.
_FAILURE_CLASSES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("sign-in", re.compile(r"invalid_grant|OAuth refresh failed|sign in again", re.I)),
    ("model", re.compile(r"model_not_found|\b404\b|model\b.*\bnot (?:found|supported)", re.I)),
    ("credential", re.compile(
        r"\b40[13]\b|api key|unauthori[sz]ed|forbidden|invalid_api_key|credential", re.I)),
    ("rate-limit", re.compile(r"\b429\b|rate.?limit|too many requests|quota", re.I)),
    ("network", re.compile(
        r"connection error|ECONNREFUSED|ECONNRESET|ENOTFOUND|EAI_AGAIN|ETIMEDOUT|fetch failed",
        re.I)),
)

# DATA MODELS / TYPEDEFINITIONS


@dataclass
class PiUsage:
    """
    @brief   Token usage summed over the assistant turns of one launch.
    @details `tokens_in` includes cached prompt tokens (Pi reports them apart
             from `input`); `complete` is False when an assistant record could
             not be read or carried invalid usage, so the sum may be short.
    """

    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    turns: int = 0
    complete: bool = True

    @property
    def tokens_in(self) -> int:
        """@brief Prompt tokens including cache reads and writes."""
        return self.input + self.cache_read + self.cache_write

    @property
    def tokens_out(self) -> int:
        """@brief Completion tokens (Pi includes reasoning in output)."""
        return self.output


@dataclass
class PiRpcResult:
    """
    @brief   Outcome of one Pi RPC launch.
    @details `outcome` is completed, failed, timed-out, cancelled or
             protocol-error. `exit_code` follows ADORE's command convention:
             0 completed, 1 failed, 124 timed out, 130 cancelled, the process
             code (or 1) for a protocol failure, 127/126 when Pi could not start.
             `message` is the redacted failure sentence; `output` and `stderr`
             are bounded tails for evidence.
    """

    outcome: str
    exit_code: int
    timed_out: bool = False
    failure: str = ""
    message: str = ""
    usage: PiUsage = field(default_factory=PiUsage)
    tool_calls: int = 0
    blocked_tools: int = 0
    records_skipped: int = 0
    output: str = ""
    stderr: str = ""
    process_exit: int | None = None
    notes: list[str] = field(default_factory=list)


Spawn = Callable[[list[str], dict[str, str]], subprocess.Popen]

# LOCAL HELPERS


def _redactor(redact: Callable[[str], str] | None) -> Callable[[str], str]:
    """
    @brief      Combine the target's redaction with provider key-hint masking.
    @param[in]  redact Optional redaction of known secret values.
    @return     A function applying both to a text.
    """
    def clean(text: str) -> str:
        if redact is not None:
            text = redact(text)
        return _BEARER_RE.sub("Bearer [REDACTED]", _KEY_HINT_RE.sub("[REDACTED]", text))

    return clean


def _classify(error: str) -> str:
    """
    @brief      Name the failure class of a Pi provider error.
    @param[in]  error Pi's errorMessage or prompt rejection text.
    @return     credential, sign-in, rate-limit, model, network or provider.
    """
    for name, pattern in _FAILURE_CLASSES:
        if pattern.search(error):
            return name
    return "provider"


def _records(stream: IO[bytes], limit: int) -> Iterator[tuple[bytes | None, int, bytes]]:
    """
    @brief      Split a byte stream on LF while buffering at most `limit` bytes.
    @param[in]  stream Pi's stdout or stderr.
    @param[in]  limit Largest record kept whole.
    @return     (record or None when over the limit, size, prefix of a skipped record).
    """
    buffer = bytearray()
    size = 0
    prefix = b""
    over = False
    read = getattr(stream, "read1", stream.read)
    while True:
        chunk = read(_CHUNK_BYTES)
        if not chunk:
            break
        start = 0
        while start < len(chunk):
            newline = chunk.find(b"\n", start)
            end = len(chunk) if newline < 0 else newline
            part = chunk[start:end]
            size += len(part)
            if not over:
                buffer += part
                if len(buffer) > limit:
                    over, prefix, buffer = True, bytes(buffer[:_PREFIX_BYTES]), bytearray()
            if newline < 0:
                break
            yield (None if over else bytes(buffer).rstrip(b"\r")), size, prefix
            buffer, size, prefix, over = bytearray(), 0, b"", False
            start = newline + 1
    if size:
        yield (None if over else bytes(buffer).rstrip(b"\r")), size, prefix


def _usage(value: object) -> tuple[int, int, int, int] | None:
    """
    @brief      Validate one Pi usage object.
    @param[in]  value `message.usage` of an assistant message.
    @return     (input, output, cacheRead, cacheWrite) or None when invalid.
    """
    if not isinstance(value, dict):
        return None
    numbers = (value.get("input"), value.get("output"),
               value.get("cacheRead", 0), value.get("cacheWrite", 0))
    if any(type(number) is not int or not 0 <= number <= _TOKEN_LIMIT for number in numbers):
        return None
    return numbers  # type: ignore[return-value]


def _text(value: object, limit: int = MESSAGE_CHARS) -> str:
    """
    @brief      Bound an optional text field.
    @param[in]  value Field value.
    @param[in]  limit Maximum characters kept.
    @return     The text, or "" when absent or not a string.
    """
    return value[:limit] if isinstance(value, str) else ""


def _facts(record: dict) -> dict | None:
    """
    @brief      Reduce one protocol record to the facts the client acts on.
    @param[in]  record Parsed stdout record.
    @return     A small dict, or None when the record needs no action.
    """
    kind = record.get("type")
    if kind == "response":
        data = value if isinstance(value := record.get("data"), dict) else {}
        tokens = data.get("tokens")
        return {"kind": "response", "id": record.get("id"), "command": record.get("command"),
                "success": record.get("success") is True, "error": _text(record.get("error")),
                "disposition": data.get("disposition"),
                "tokens": tokens if isinstance(tokens, dict) else None}
    if kind == "message_end":
        message = record.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            return None
        content = value if isinstance(value := message.get("content"), list) else []
        text = "".join(part.get("text", "") for part in content
                       if isinstance(part, dict) and part.get("type") == "text"
                       and isinstance(part.get("text"), str))
        return {"kind": "assistant", "usage": _usage(message.get("usage")),
                "stop": message.get("stopReason"), "error": _text(message.get("errorMessage")),
                "text": text[-MESSAGE_CHARS:]}
    if kind == "tool_execution_end":
        result = value if isinstance(value := record.get("result"), dict) else {}
        content = items if isinstance(items := result.get("content"), list) else []
        text = "".join(part.get("text", "") for part in content
                       if isinstance(part, dict) and isinstance(part.get("text"), str))
        failed = record.get("isError") is True
        return {"kind": "tool", "blocked": failed and text.startswith(GUARD_REASON_PREFIX)}
    if kind == "agent_settled":
        return {"kind": "settled", "aborted": record.get("aborted") is True}
    return None


class _Evidence:
    """
    @brief   Bounded persistence and tail of the records a launch produced.
    """

    def __init__(self, path: Path | None, limit: int, clean: Callable[[str], str]) -> None:
        self.handle = path.open("wb") if path is not None else None
        self.limit, self.written, self.clean = limit, 0, clean
        self.truncated = False
        self.tail: deque[str] = deque()
        self.tail_bytes = 0
        self.lock = threading.Lock()

    def add(self, line: str) -> None:
        """
        @brief      Persist one line within the file limit and keep it in the tail.
        @param[in]  line Redacted line without its LF.
        """
        data = line.encode("utf-8") + b"\n"
        with self.lock:
            self._add(line, data)

    def _add(self, line: str, data: bytes) -> None:
        """
        @brief      Persist and retain one line; the caller holds the lock.
        @param[in]  line Redacted line without its LF.
        @param[in]  data The line encoded with its LF.
        """
        if self.handle is not None and not self.truncated:
            if self.written + len(data) > self.limit:
                self.truncated = True
                self.handle.write(b'{"type":"adore_output_truncated"}\n')
            else:
                self.handle.write(data)
                self.written += len(data)
        self.tail.append(line)
        self.tail_bytes += len(data)
        while self.tail_bytes > TAIL_BYTES and self.tail:
            self.tail_bytes -= len(self.tail.popleft().encode("utf-8")) + 1

    def close(self) -> None:
        """@brief Close the persisted file."""
        with self.lock:
            if self.handle is not None:
                self.handle.close()
                self.handle = None

    def text(self) -> str:
        """@brief The retained tail as text."""
        with self.lock:
            return "\n".join(self.tail)


def _stub(kind: str, size: int, **extra: Any) -> str:
    """
    @brief      Persisted placeholder for a record not kept whole.
    @param[in]  kind Record type, when known.
    @param[in]  size Record size in bytes.
    @param[in]  extra Additional fields.
    @return     One JSON line.
    """
    return json.dumps({"type": kind or "unknown", "adore_omitted_bytes": size, **extra})


def _read_stdout(stream: IO[bytes], sink: queue.Queue, evidence: _Evidence, limit: int) -> None:
    """
    @brief      Reader thread: parse records into facts and persist evidence.
    @param[in]  stream Pi's stdout.
    @param[in]  sink Queue receiving small fact dicts, then `{"kind": "eof"}`.
    @param[in]  evidence Bounded output persistence.
    @param[in]  limit Largest record parsed.
    """
    try:
        for line, size, prefix in _records(stream, limit):
            if line is None:
                kind = _TYPE_RE.search(prefix)
                role = _ROLE_RE.search(prefix)
                name = kind.group(1).decode("ascii") if kind else ""
                evidence.add(_stub(name, size, adore_skipped=True))
                sink.put({"kind": "oversize", "type": name,
                          "role": role.group(1).decode("ascii") if role else ""})
                continue
            if not line.strip():
                continue
            try:
                record = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, ValueError, RecursionError):
                record = None
            if not isinstance(record, dict):
                head = evidence.clean(line[:200].decode("utf-8", errors="replace"))
                evidence.add(json.dumps({"type": "adore_malformed_record", "bytes": size,
                                         "head": head}))
                sink.put({"kind": "malformed"})
                continue
            kind = record.get("type")
            if kind != "message_update":
                evidence.add(_stub(str(kind), size) if size > PERSIST_RECORD_BYTES
                             else evidence.clean(line.decode("utf-8")))
            facts = _facts(record)
            if facts is not None:
                sink.put(facts)
    except (OSError, ValueError):
        pass
    finally:
        sink.put({"kind": "eof"})


def _read_stderr(stream: IO[bytes], evidence: _Evidence) -> None:
    """
    @brief      Reader thread: keep a bounded, redacted copy of Pi's diagnostics.
    @param[in]  stream Pi's stderr (free text, never protocol).
    @param[in]  evidence Bounded stderr persistence.
    """
    try:
        for line, size, _prefix in _records(stream, TAIL_BYTES):
            text = (f"[{size} bytes omitted]" if line is None
                    else line.decode("utf-8", errors="replace"))
            evidence.add(evidence.clean(text))
    except (OSError, ValueError):
        pass


def _write_stdin(stream: IO[bytes], outbox: queue.Queue) -> None:
    """
    @brief      Writer thread: send queued commands; None closes stdin.
    @details    A separate thread honours stdin backpressure without blocking
                the deadline loop.
    @param[in]  stream Pi's stdin.
    @param[in]  outbox Queue of encoded commands.
    """
    try:
        while True:
            data = outbox.get()
            if data is None:
                break
            stream.write(data)
            stream.flush()
    except (OSError, ValueError):
        pass
    finally:
        with contextlib.suppress(OSError, ValueError):
            stream.close()


class _Launch:
    """
    @brief   State of one running Pi RPC process.
    """

    def __init__(self, process: subprocess.Popen, output: _Evidence, stderr: _Evidence,
                 max_record_bytes: int) -> None:
        self.process = process
        self.events: queue.Queue = queue.Queue()
        self.outbox: queue.Queue = queue.Queue()
        self.output, self.stderr = output, stderr
        self.threads = [
            threading.Thread(target=_read_stdout, daemon=True,
                             args=(process.stdout, self.events, output, max_record_bytes)),
            threading.Thread(target=_read_stderr, daemon=True, args=(process.stderr, stderr)),
            threading.Thread(target=_write_stdin, daemon=True, args=(process.stdin, self.outbox)),
        ]
        for thread in self.threads:
            thread.start()
        self.eof = False

    def send(self, command: dict) -> None:
        """@brief Queue one command as an LF-terminated JSON line."""
        self.outbox.put(json.dumps(command, ensure_ascii=False).encode("utf-8") + b"\n")

    def next(self, wait: float) -> dict | None:
        """@brief Next fact, or None when none arrived within `wait` seconds."""
        if self.eof:
            time.sleep(max(0.0, min(wait, POLL_SECONDS)))
            return None
        try:
            facts = self.events.get(timeout=max(0.0, wait))
        except queue.Empty:
            return None
        if facts["kind"] == "eof":
            self.eof = True
        return facts

    def shutdown(self, exit_grace: float) -> int | None:
        """
        @brief      Close stdin, then terminate and kill when the process stays.
        @param[in]  exit_grace Seconds allowed for an orderly exit.
        @return     The process exit code (None if it could not be reaped).
        """
        self.outbox.put(None)
        try:
            return self.process.wait(timeout=exit_grace)
        except subprocess.TimeoutExpired:
            pass
        for stop in (self.process.terminate, self.process.kill):
            try:
                stop()
                return self.process.wait(timeout=KILL_GRACE_SECONDS)
            except (OSError, subprocess.TimeoutExpired):
                continue
        return self.process.poll()

    def join(self) -> None:
        """@brief Wait briefly for the stream threads after the process ended."""
        for thread in self.threads:
            thread.join(timeout=KILL_GRACE_SECONDS)
        self.output.close()
        self.stderr.close()


def _end(process: subprocess.Popen) -> None:
    """
    @brief      Kill a started process whose launch could not be set up.
    @param[in]  process Process returned by the spawn seam.
    """
    # Kill first: a started reader thread may hold a stream's buffer lock.
    with contextlib.suppress(OSError):
        process.kill()
    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
        process.wait(timeout=KILL_GRACE_SECONDS)
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            with contextlib.suppress(OSError, ValueError):
                stream.close()


def bounded_text(text: str, limit: int = TAIL_BYTES) -> str:
    """
    @brief      Cut text to at most `limit` UTF-8 bytes without splitting a character.
    @param[in]  text Evidence text.
    @param[in]  limit Byte limit.
    @return     The text, or its longest prefix within the limit.
    """
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore")


# PUBLIC API


def run_pi_rpc(
    spawn: Spawn,
    argv: list[str],
    env: dict[str, str],
    prompt: str,
    *,
    timeout: float | None = None,
    cancelled: Callable[[], bool] | None = None,
    output_path: Path | None = None,
    stderr_path: Path | None = None,
    redact: Callable[[str], str] | None = None,
    abort_grace: float = ABORT_GRACE_SECONDS,
    exit_grace: float = EXIT_GRACE_SECONDS,
    stats_grace: float = STATS_GRACE_SECONDS,
    max_record_bytes: int = MAX_RECORD_BYTES,
) -> PiRpcResult:
    """
    @brief      Run one stage prompt through one Pi RPC process.
    @param[in]  spawn Starts `argv` with `env` and binary stdin/stdout/stderr pipes.
    @param[in]  argv Pi command line (`--mode rpc` and its isolation flags).
    @param[in]  env Variables added for this process only.
    @param[in]  prompt Stage prompt; sent over stdin, never through argv.
    @param[in]  timeout Stage wall-clock bound; None means no deadline.
    @param[in]  cancelled Polled check; True requests a cancel (abort).
    @param[in]  output_path Bounded evidence copy of Pi's records.
    @param[in]  stderr_path Bounded copy of Pi's diagnostics.
    @param[in]  redact Redaction of known secret values for evidence.
    @param[in]  abort_grace Seconds allowed for `agent_settled` after `abort`.
    @param[in]  exit_grace Seconds allowed for an exit after stdin closes.
    @param[in]  stats_grace Seconds allowed for the usage cross-check answer.
    @param[in]  max_record_bytes Largest stdout record held in memory.
    @return     The launch outcome; never raises for Pi's own failures.
    @exception  Exception Whatever `spawn` raises other than OSError, or a failing
                `cancelled` check; the process is ended before it propagates.
    """
    clean = _redactor(redact)
    try:
        process = spawn(list(argv), dict(env))
    except OSError as exc:
        code = EXIT_NOT_FOUND if isinstance(exc, FileNotFoundError) else EXIT_NOT_EXECUTABLE
        return PiRpcResult(outcome="protocol-error", exit_code=code,
                           message=clean(f"Pi protocol failure: Pi could not start: {exc}"))
    stdout = stderr = None
    try:
        stdout = _Evidence(output_path, PERSIST_TOTAL_BYTES, clean)
        stderr = _Evidence(stderr_path, STDERR_FILE_BYTES, clean)
        launch = _Launch(process, stdout, stderr, max_record_bytes)
    except BaseException:
        for evidence in (stdout, stderr):
            if evidence is not None:
                evidence.close()
        _end(process)
        raise
    result = PiRpcResult(outcome="", exit_code=EXIT_FAILED)
    usage = result.usage
    deadline = None if timeout is None else time.monotonic() + timeout
    stop = ""          # "", "timeout", "cancel" or "protocol"
    protocol = ""      # protocol failure sentence
    rejected = ""      # prompt rejection text
    settled: bool | None = None
    last = {"stop": None, "error": ""}
    abort_deadline = 0.0
    try:
        launch.send({"id": _PROMPT_ID, "type": "prompt", "message": prompt})
        while settled is None:
            now = time.monotonic()
            if not stop:
                reason = ("timeout" if deadline is not None and now >= deadline
                          else "cancel" if cancelled is not None and cancelled() else "")
                if reason:
                    stop, abort_deadline = reason, now + abort_grace
                    launch.send({"id": _ABORT_ID, "type": "abort"})
            elif now >= abort_deadline:
                break
            limit = abort_deadline if stop else deadline
            wait = POLL_SECONDS if limit is None else min(POLL_SECONDS, limit - now)
            facts = launch.next(wait)
            if facts is None:
                if launch.eof:
                    protocol = protocol or "exited"
                    break
                continue
            kind = facts["kind"]
            if kind == "eof":
                protocol = "exited"
                break
            if kind == "malformed":
                stop = "protocol"
                protocol = "Pi wrote a malformed stdout record (not a JSON object)"
                break
            if kind == "oversize":
                result.records_skipped += 1
                if facts["type"] == "message_end" and facts["role"] in ("", "assistant"):
                    usage.complete = False
                    last = {"stop": _UNREADABLE, "error": ""}
            elif kind == "response" and facts["id"] == _PROMPT_ID:
                if not facts["success"]:
                    rejected = facts["error"] or "the prompt was rejected"
                    break
                if facts["disposition"] != "started":
                    stop = "protocol"
                    protocol = f"Pi did not start a run (disposition {facts['disposition']!r})"
                    break
            elif kind == "response" and facts["command"] == "parse":
                stop, protocol = "protocol", "Pi could not parse an ADORE command"
                break
            elif kind == "assistant":
                numbers = facts["usage"]
                if numbers is None:
                    usage.complete = False
                else:
                    usage.input += numbers[0]
                    usage.output += numbers[1]
                    usage.cache_read += numbers[2]
                    usage.cache_write += numbers[3]
                    usage.turns += 1
                last = {"stop": facts["stop"], "error": facts["error"]}
            elif kind == "tool":
                result.tool_calls += 1
                result.blocked_tools += facts["blocked"]
            elif kind == "settled":
                settled = facts["aborted"]
        if settled is False and not stop:
            _cross_check(launch, usage, result, stats_grace)
    finally:
        result.process_exit = launch.shutdown(exit_grace)
        launch.join()
    result.output, result.stderr = stdout.text(), stderr.text()
    _conclude(result, stop, protocol, rejected, settled, last, clean)
    return result


def _cross_check(launch: _Launch, usage: PiUsage, result: PiRpcResult, grace: float) -> None:
    """
    @brief      Compare the per-turn sums with Pi's session totals once.
    @details    A mismatch is noted in the evidence; the per-turn sum stays the
                reported usage.
    @param[in]  launch Running launch (settled, stdin still open).
    @param[in]  usage Per-turn sums.
    @param[in,out] result Receives a note on mismatch.
    @param[in]  grace Seconds allowed for the answer.
    """
    launch.send({"id": _STATS_ID, "type": "get_session_stats"})
    until = time.monotonic() + grace
    while (remaining := until - time.monotonic()) > 0:
        facts = launch.next(min(POLL_SECONDS, remaining))
        if facts is None:
            if launch.eof:
                return
            continue
        if facts["kind"] == "eof":
            return
        if facts["kind"] != "response" or facts["id"] != _STATS_ID:
            continue
        tokens = facts["tokens"]
        if facts["success"] and tokens is not None:
            expected = (usage.input, usage.output, usage.cache_read, usage.cache_write)
            reported = (tokens.get("input"), tokens.get("output"),
                        tokens.get("cacheRead", 0), tokens.get("cacheWrite", 0))
            if reported != expected:
                result.notes.append(
                    f"Pi usage cross-check: per-turn totals {expected} differ from the "
                    f"session totals {reported}")
        return


def _conclude(result: PiRpcResult, stop: str, protocol: str, rejected: str,
              settled: bool | None, last: dict, clean: Callable[[str], str]) -> None:
    """
    @brief      Decide the outcome, exit code and failure sentence.
    @param[in,out] result Launch result being completed.
    @param[in]  stop Why ADORE stopped the run ("" when it did not).
    @param[in]  protocol Protocol failure, "exited" for an early exit.
    @param[in]  rejected Prompt rejection text.
    @param[in]  settled `agent_settled.aborted`, or None when it never came.
    @param[in]  last Stop reason and error of the last assistant message.
    @param[in]  clean Evidence redaction.
    """
    code = result.process_exit
    failed_code = code if isinstance(code, int) and code > 0 else EXIT_FAILED
    if stop == "protocol":
        result.outcome, result.exit_code = "protocol-error", failed_code
        result.message = f"Pi protocol failure: {protocol}"
    elif stop == "timeout":
        result.outcome, result.exit_code, result.timed_out = "timed-out", EXIT_TIMEOUT, True
        result.message = "Pi run timed out: ADORE aborted it at the stage timeout"
    elif stop == "cancel":
        result.outcome, result.exit_code = "cancelled", EXIT_CANCELLED
        result.message = "Pi run cancelled: ADORE aborted it on the cancel request"
    elif rejected:
        result.failure = _classify(rejected)
        result.outcome, result.exit_code = "failed", EXIT_FAILED
        result.message = f"Pi run failed ({result.failure}): {rejected}"
    elif settled is None:
        result.outcome, result.exit_code = "protocol-error", failed_code
        result.message = f"Pi protocol failure: Pi exited before the run settled (exit {code})"
    elif settled:
        result.outcome, result.exit_code = "protocol-error", failed_code
        result.message = "Pi protocol failure: Pi aborted the run without a request"
    elif last["stop"] == _UNREADABLE:
        result.outcome, result.exit_code = "protocol-error", failed_code
        result.message = ("Pi protocol failure: the last assistant message could not be read "
                          "(over the record limit)")
    elif last["stop"] == "error":
        error = last["error"] or "the run ended with an error"
        result.failure = _classify(error)
        result.outcome, result.exit_code = "failed", EXIT_FAILED
        result.message = f"Pi run failed ({result.failure}): {error}"
    else:
        result.outcome, result.exit_code = "completed", 0
    result.message = clean(result.message)[:MESSAGE_CHARS]


# END OF FILE
