#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
"""
@file    rpc_probe.py
@brief   Minimal Pi RPC client used by the PI-01 spike to record redacted event logs.
@details Starts ``pi --mode rpc --no-session`` (or any command given after ``--``),
         sends one ``prompt``, streams every stdout record, optionally sends ``abort``
         after a delay or at the first tool call, then asks for ``get_session_stats``
         and ``get_state``, closes stdin and records the exit code.

         Every record is written to the output file as one JSON envelope per line::

             {"t_ms": 1234, "dir": "stdin"|"stdout"|"stderr"|"exit"|"probe", "record": ...}

         ``stdout`` records are Pi's protocol records exactly as received (after
         redaction); ``stdin`` records are the commands this probe sent; ``stderr``
         lines are text; ``exit`` carries the return code. Secrets are redacted at
         write time: the literal values of the environment variables named with
         ``--secret-env`` plus patterns for API keys, JWTs, e-mail addresses, UUIDs and
         the user's home directory.

         The probe is a spike tool, not product code: it has no dependency outside the
         Python standard library and is not imported by ADORE.

@example python rpc_probe.py --out fixtures/run.jsonl --cwd work --prompt "..." \\
             --secret-env OPENAI_API_KEY -- pi --mode rpc --no-session --model openai/gpt-5.4-mini
"""

# ==================================================================================================
# IMPORTS
# ==================================================================================================
import argparse
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

# ==================================================================================================
# CONSTANTS
# ==================================================================================================
SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "<REDACTED_JWT>"),
    (re.compile(r"\b(sk|rk|pk)-[A-Za-z0-9_-]{2,}\*{3,}[A-Za-z0-9_-]{2,}"), "<REDACTED_KEY_HINT>"),
    (re.compile(r"\b(sk|rk|pk)-[A-Za-z0-9_-]{16,}"), "<REDACTED_KEY>"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}"), "<REDACTED_KEY>"),
    (re.compile(r"\b(BSA|tvly|exa|AIza)[A-Za-z0-9_-]{16,}"), "<REDACTED_KEY>"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<REDACTED_EMAIL>"),
    (re.compile(r"urn:uuid:[0-9a-fA-F-]{36}"), "urn:uuid:<REDACTED_HOST_ID>"),
]
TERMINAL_EVENT = "agent_settled"

# ==================================================================================================
# HELPER FUNCTIONS
# ==================================================================================================


class Redactor:
    """@brief Replaces secret values and personal data in recorded strings."""

    def __init__(self, secret_names: list[str], extra_literals: list[str]) -> None:
        """
        @brief Collect the literal values to redact.
        @param[in] secret_names   Environment variable names whose values are secrets.
        @param[in] extra_literals Further literal strings to replace (paths, user names).
        """
        self.literals: list[tuple[str, str]] = []
        for name in secret_names:
            value = os.environ.get(name, "")
            if len(value) >= 6:
                self.literals.append((value, f"<REDACTED_{name}>"))
        for literal in extra_literals:
            if literal:
                self.literals.append((literal, "<REDACTED_PATH>"))
                self.literals.append((literal.replace("\\", "/"), "<REDACTED_PATH>"))
                self.literals.append((literal.replace("\\", "\\\\"), "<REDACTED_PATH>"))
        # Longest first so a path is replaced before a shorter prefix of it.
        self.literals.sort(key=lambda item: len(item[0]), reverse=True)

    def text(self, value: str) -> str:
        """
        @brief Redact one string.
        @param[in] value The string to clean.
        @return The string with secrets and personal data replaced.
        """
        for literal, replacement in self.literals:
            value = value.replace(literal, replacement)
        for pattern, replacement in SECRET_PATTERNS:
            value = pattern.sub(replacement, value)
        return value

    def deep(self, value: Any) -> Any:
        """
        @brief Redact every string inside a JSON value, keys included.
        @param[in] value Any JSON-compatible value.
        @return A redacted copy.
        """
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, list):
            return [self.deep(item) for item in value]
        if isinstance(value, dict):
            return {self.text(str(key)): self.deep(item) for key, item in value.items()}
        return value


def pump_lines(stream: Any, name: str, sink: "queue.Queue[tuple[str, bytes | None]]") -> None:
    """
    @brief Read a binary stream and push complete LF-terminated records into a queue.
    @details Splits only on LF and strips one preceding CR, as Pi's RPC framing requires;
             U+2028 and U+2029 inside JSON strings are not record boundaries.
    @param[in] stream Binary pipe of the child process.
    @param[in] name   ``stdout`` or ``stderr``.
    @param[in] sink   Queue receiving ``(name, line)`` and finally ``(name, None)``.
    """
    buffer = b""
    while True:
        chunk = stream.read1(65536) if hasattr(stream, "read1") else stream.read(65536)
        if not chunk:
            break
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            sink.put((name, line[:-1] if line.endswith(b"\r") else line))
    if buffer:
        sink.put((name, buffer))
    sink.put((name, None))


# ==================================================================================================
# PUBLIC API
# ==================================================================================================


class Probe:
    """@brief Drives one Pi RPC process and records the conversation."""

    def __init__(self, args: argparse.Namespace) -> None:
        """
        @brief Prepare output and redaction.
        @param[in] args Parsed command-line options.
        """
        self.args = args
        home = str(Path.home())
        self.redactor = Redactor(args.secret_env, [home, *args.redact_literal])
        self.out = open(args.out, "w", encoding="utf-8", newline="\n")
        self.start = time.monotonic()
        self.lines: "queue.Queue[tuple[str, bytes | None]]" = queue.Queue()
        self.next_id = 0
        self.summary: dict[str, Any] = {}

    def elapsed_ms(self) -> int:
        """@brief Milliseconds since the probe started. @return Elapsed milliseconds."""
        return int((time.monotonic() - self.start) * 1000)

    def write(self, direction: str, record: Any) -> None:
        """
        @brief Append one redacted envelope to the output file and echo a short form.
        @param[in] direction ``stdin``, ``stdout``, ``stderr``, ``exit`` or ``probe``.
        @param[in] record    The record to store.
        """
        envelope = {"t_ms": self.elapsed_ms(), "dir": direction, "record": self.redactor.deep(record)}
        self.out.write(json.dumps(envelope, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.out.flush()
        if not self.args.quiet:
            kind = record.get("type") if isinstance(record, dict) else "text"
            if isinstance(record, dict) and record.get("type") == "message_update":
                kind = "message_update/" + str(record.get("assistantMessageEvent", {}).get("type"))
            print(f"{envelope['t_ms']:>7} {direction:<6} {kind}", file=sys.stderr)

    def send(self, command: dict[str, Any]) -> str:
        """
        @brief Send one RPC command with a fresh id.
        @param[in] command Command without ``id``.
        @return The id used.
        """
        self.next_id += 1
        command = {"id": f"probe-{self.next_id}", **command}
        self.write("stdin", command)
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(command).encode("utf-8") + b"\n")
        self.process.stdin.flush()
        return command["id"]

    def wait_for(self, predicate: Any, timeout: float) -> dict[str, Any] | None:
        """
        @brief Consume records until one matches or the timeout expires.
        @param[in] predicate Callable receiving a stdout record.
        @param[in] timeout   Seconds to wait.
        @return The matching record, or None on timeout or end of stdout.
        """
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                name, line = self.lines.get(timeout=min(remaining, 0.5))
            except queue.Empty:
                continue
            if line is None:
                self.write("probe", {"event": f"{name}_closed"})
                if name == "stdout":
                    return None
                continue
            text = line.decode("utf-8", errors="replace")
            if name == "stderr":
                self.write("stderr", text)
                continue
            try:
                record = json.loads(text)
            except json.JSONDecodeError:
                self.write("probe", {"event": "non_json_stdout", "text": text})
                continue
            self.write("stdout", record)
            self.observe(record)
            if predicate(record):
                return record

    def observe(self, record: dict[str, Any]) -> None:
        """
        @brief Track facts for the summary printed at the end.
        @param[in] record One stdout record.
        """
        kind = record.get("type")
        counts = self.summary.setdefault("counts", {})
        counts[kind] = counts.get(kind, 0) + 1
        if kind == "tool_execution_start" and "first_tool_ms" not in self.summary:
            self.summary["first_tool_ms"] = self.elapsed_ms()
        if kind == "message_end" and record.get("message", {}).get("role") == "assistant":
            message = record["message"]
            self.summary.setdefault("assistant_usage", []).append(message.get("usage"))
            self.summary["last_stop_reason"] = message.get("stopReason")
            if message.get("errorMessage"):
                self.summary["last_error"] = self.redactor.text(str(message.get("errorMessage")))

    def run(self) -> int:
        """
        @brief Execute the probe scenario.
        @return Pi's exit code, or 124 when the probe had to kill it.
        """
        args = self.args
        env = dict(os.environ)
        for item in args.unset_env:
            env.pop(item, None)
        self.write("probe", {"event": "start", "argv": args.command, "cwd": args.cwd})
        self.process = subprocess.Popen(
            args.command,
            cwd=args.cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for stream, name in ((self.process.stdout, "stdout"), (self.process.stderr, "stderr")):
            threading.Thread(target=pump_lines, args=(stream, name, self.lines), daemon=True).start()

        for command in args.pre_command:
            command_id = self.send(json.loads(command))
            self.wait_for(lambda r, i=command_id: r.get("type") == "response" and r.get("id") == i, 30)

        prompt_id = self.send({"type": "prompt", "message": args.prompt})
        response = self.wait_for(lambda r: r.get("type") == "response" and r.get("id") == prompt_id, 60)
        self.summary["prompt_response"] = response
        settled = None
        if response and response.get("success") and response.get("data", {}).get("disposition") == "started":
            if args.abort_on_tool or args.abort_after is not None:
                trigger_timeout = args.abort_after if args.abort_after is not None else args.timeout
                if args.abort_on_tool:
                    trigger = self.wait_for(
                        lambda r: r.get("type") in ("tool_execution_start", TERMINAL_EVENT), trigger_timeout
                    )
                else:
                    trigger = self.wait_for(lambda r: r.get("type") == TERMINAL_EVENT, trigger_timeout)
                if trigger is None or trigger.get("type") != TERMINAL_EVENT:
                    sent_ms = self.elapsed_ms()
                    abort_id = self.send({"type": "abort"})
                    abort_response = None
                    deadline = time.monotonic() + args.timeout
                    while time.monotonic() < deadline and (abort_response is None or settled is None):
                        record = self.wait_for(
                            lambda r: (r.get("type") == "response" and r.get("id") == abort_id)
                            or r.get("type") == TERMINAL_EVENT,
                            deadline - time.monotonic(),
                        )
                        if record is None:
                            break
                        if record.get("type") == TERMINAL_EVENT:
                            settled = record
                            self.summary["abort_to_settled_ms"] = self.elapsed_ms() - sent_ms
                        else:
                            abort_response = record
                            self.summary["abort_to_response_ms"] = self.elapsed_ms() - sent_ms
                else:
                    settled = trigger
            if settled is None:
                settled = self.wait_for(lambda r: r.get("type") == TERMINAL_EVENT, args.timeout)
        self.summary["settled"] = settled

        for command in ({"type": "get_session_stats"}, {"type": "get_state"}):
            command_id = self.send(command)
            reply = self.wait_for(lambda r, i=command_id: r.get("type") == "response" and r.get("id") == i, 30)
            if command["type"] == "get_session_stats" and reply:
                self.summary["session_stats"] = reply.get("data")

        assert self.process.stdin is not None
        self.process.stdin.close()
        self.write("probe", {"event": "stdin_closed"})
        try:
            code = self.process.wait(timeout=args.exit_grace)
        except subprocess.TimeoutExpired:
            self.write("probe", {"event": "kill_after_grace", "grace_s": args.exit_grace})
            self.process.kill()
            self.process.wait()
            code = 124
        # Drain what is left after exit.
        self.wait_for(lambda _record: False, 1.0)
        self.write("exit", {"returncode": code})
        self.summary["exit_code"] = code
        self.out.close()
        print(json.dumps(self.redactor.deep(self.summary), indent=2, default=str))
        return code


def parse_args(argv: list[str]) -> argparse.Namespace:
    """
    @brief Parse probe options; the Pi command follows ``--``.
    @param[in] argv Command-line arguments without the program name.
    @return Parsed options.
    """
    if "--" in argv:
        split = argv.index("--")
        own, command = argv[:split], argv[split + 1 :]
    else:
        own, command = argv, ["pi", "--mode", "rpc", "--no-session"]
    parser = argparse.ArgumentParser(description=__doc__.split("@details")[0] if __doc__ else None)
    parser.add_argument("--out", required=True, help="fixture file to write (JSONL envelopes)")
    parser.add_argument("--cwd", default=".", help="working folder for Pi")
    parser.add_argument("--prompt", required=True, help="prompt text to send")
    parser.add_argument("--timeout", type=float, default=300.0, help="seconds to wait for agent_settled")
    parser.add_argument("--abort-after", type=float, help="send abort after this many seconds")
    parser.add_argument("--abort-on-tool", action="store_true", help="send abort at the first tool call")
    parser.add_argument("--exit-grace", type=float, default=10.0, help="seconds to wait for exit after stdin closes")
    parser.add_argument("--pre-command", action="append", default=[], help="JSON command sent before the prompt")
    parser.add_argument("--secret-env", action="append", default=[], help="env var whose value is redacted")
    parser.add_argument("--unset-env", action="append", default=[], help="env var removed from Pi's environment")
    parser.add_argument("--redact-literal", action="append", default=[], help="literal string to redact")
    parser.add_argument("--quiet", action="store_true", help="do not echo records to stderr")
    args = parser.parse_args(own)
    if not command:
        parser.error("missing Pi command after --")
    args.command = command
    return args


def reredact(paths: list[str], literals: list[str]) -> int:
    """
    @brief Apply the current redaction rules again to recorded fixture files, in place.
    @param[in] paths    Fixture files to rewrite.
    @param[in] literals Further literal strings to redact.
    @return 0.
    """
    redactor = Redactor([], [str(Path.home()), *literals])
    for path in paths:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        cleaned = [json.dumps(redactor.deep(json.loads(line)), ensure_ascii=False, separators=(",", ":")) for line in lines]
        Path(path).write_bytes(("\n".join(cleaned) + "\n").encode("utf-8"))
    return 0


def main(argv: list[str]) -> int:
    """
    @brief Entry point.
    @param[in] argv Command-line arguments without the program name.
    @return Process exit code (Pi's exit code).
    """
    if argv[:1] == ["--reredact"]:
        files = [item for item in argv[1:] if not item.startswith("--literal=")]
        literals = [item.split("=", 1)[1] for item in argv[1:] if item.startswith("--literal=")]
        return reredact(files, literals)
    return Probe(parse_args(argv)).run()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# ==================================================================================================
# END OF FILE
# ==================================================================================================
