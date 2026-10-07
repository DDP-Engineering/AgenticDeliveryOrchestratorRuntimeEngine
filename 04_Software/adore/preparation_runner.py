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
@file    preparation_runner.py
@brief   Standalone Linux-container preparation file runner.
@details Copied into the bounded exchange directory; requires only Python 3.
         Drains both streams with bounded redacted retention and enforces a
         process-group wall timeout. No ADORE imports or host shell are used.
"""

# IMPORTS
import codecs
import contextlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
from threading import Thread

# CONSTANTS
MAX_OUTPUT_BYTES = 65536

# LOCAL HELPERS


def _drain(stream, path: Path, secrets: list[str]) -> None:
    """
    @brief Drain one pipe, redacting split credential values before bounded writes.
    @param[in] stream Child stdout/stderr byte stream.
    @param[in] path Owned output file.
    @param[in] secrets Known values read only from the container process environment.
    """
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    tail = max((len(value) for value in secrets), default=0) + 256
    buffer = ""
    retained = 0
    with path.open("wb") as output:
        while True:
            chunk = stream.read(4096)
            buffer += decoder.decode(chunk, final=not chunk)
            for value in secrets:
                buffer = buffer.replace(value, "[REDACTED]")
            buffer = re.sub(r"(?i)(Bearer\s+)\S+", r"\1[REDACTED]", buffer)
            count = len(buffer) if not chunk else max(0, len(buffer) - tail)
            data = buffer[:count].encode("utf-8")[: max(0, MAX_OUTPUT_BYTES - retained)]
            output.write(data)
            retained += len(data)
            buffer = buffer[count:]
            if not chunk:
                break


# PUBLIC API


def main(argv: list[str]) -> int:
    """
    @brief Run a file-safe shell step and write authoritative exit/timeout result.
    @param[in] argv Timeout, owned IO directory and worktree path.
    @return Actual shell status, or 124 only on enforced wall timeout.
    """
    timeout = float(argv[0])
    directory = Path(argv[1])
    keys = json.loads((directory / "secret-keys.json").read_text(encoding="utf-8"))
    values = {os.environ[k] for k in keys if os.environ.get(k)}
    if len(argv) > 3:
        auth_path = Path(argv[3])
        if auth_path.stat().st_size > 131072:
            raise ValueError("staged auth exceeds redaction bound")

        def unique(pairs):
            """@brief Reject ambiguous fields in the existing staged auth source."""
            record = {}
            for key, value in pairs:
                if key in record:
                    raise ValueError("duplicate staged auth field")
                record[key] = value
            return record

        auth = json.loads(auth_path.read_text(encoding="utf-8"), object_pairs_hook=unique)
        if not isinstance(auth, dict):
            raise ValueError("staged auth must be an object")
        pending = [(auth, 0)]
        while pending:
            value, depth = pending.pop()
            if depth > 16:
                raise ValueError("staged auth nesting exceeds redaction bound")
            if isinstance(value, str) and value:
                value.encode("utf-8")
                values.add(value)
            elif isinstance(value, (dict, list)):
                pending.extend(
                    (item, depth + 1)
                    for item in (value.values() if isinstance(value, dict) else value)
                )
    secrets = sorted(values, key=len, reverse=True)
    process = subprocess.Popen(  # noqa: S603 - fixed shell argv and reviewed script file
        ["sh", "-eu", str(directory / "run.sh")],
        cwd=argv[2],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    threads = [
        Thread(target=_drain, args=(stream, directory / f"{name}.txt", secrets))
        for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr"))
    ]
    for thread in threads:
        thread.start()
    timed_out = False
    try:
        code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        code = 124
    finally:
        # Release descendants in the shell's process group after every step.
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        for thread in threads:
            thread.join(timeout=5)
    # POSIX shell exit codes are 0..255; negative signals normalize like shells.
    code = 128 - code if code < 0 else code
    (directory / "result.json").write_text(
        json.dumps({"exit_code": code, "timed_out": timed_out}),
        encoding="utf-8",
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

# END OF FILE
