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


def _drain(stream, path: Path, secrets: list[str], *,
           max_bytes: int = MAX_OUTPUT_BYTES, strict_utf8: bool = False) -> None:
    """
    @brief Drain one pipe, redacting split credential values before bounded writes.
    @param[in] stream Child stdout/stderr byte stream.
    @param[in] path Owned output file.
    @param[in] secrets Known values read only from the container process environment.
    @param[in] max_bytes Retained output bound; native AEGIS preserves its JSON limit.
    @param[in] strict_utf8 Native evidence refuses corrupt UTF-8.
    """
    decoder = codecs.getincrementaldecoder("utf-8")(
        errors="strict" if strict_utf8 else "replace")
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
            data = buffer[:count].encode("utf-8")[: max(0, max_bytes - retained)]
            if strict_utf8:
                data = data.decode("utf-8", errors="ignore").encode("utf-8")
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
