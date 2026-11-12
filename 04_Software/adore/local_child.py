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
@file    local_child.py
@brief   Trusted native launcher with a durable-ownership release barrier.
@details Requires only Python. Joins the Linux scope before starting any child;
         Windows parent assigns its Job before publishing the release marker.
"""

# IMPORTS
import json
import ntpath
import os
from pathlib import Path
import subprocess
import sys
import time

# PUBLIC API


def main(path: str, *, streaming: bool = False) -> int:
    """
    @brief Start native argv or dedicated Windows verification after the ownership receipt.
    @param[in] path Parent-owned immutable launch envelope.
    @param[in] streaming Forward the parent's stdin pipe for RPC.
    @return Authoritative command exit status.
    @exception ValueError Invalid trusted transport.
    """
    envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    keys = {"argv", "cwd", "release", "scope"}
    if set(envelope) not in (keys, keys | {"windows_verification"}):
        raise ValueError("invalid native launch envelope")
    if (
        not isinstance(envelope["argv"], list)
        or not envelope["argv"]
        or any(not isinstance(arg, str) or "\x00" in arg for arg in envelope["argv"])
    ):
        raise ValueError("invalid native argv")
    scope = envelope["scope"]
    argv = envelope["argv"]
    windows_verification = "windows_verification" in envelope
    if windows_verification and (
        envelope["windows_verification"] is not True or streaming
        or scope["kind"] != "windows-job" or len(argv) != 5
        or argv[1:4] != ["/d", "/s", "/c"]
        or not ntpath.isabs(argv[0]) or ntpath.basename(argv[0]).lower() != "cmd.exe"
        or '"' in argv[0] or not argv[-1] or any(char in argv[-1] for char in "\r\n")
    ):
        raise ValueError("invalid native Windows verification transport")
    if scope["kind"] == "linux-cgroup":
        (Path(scope["path"]) / "cgroup.procs").write_text(str(os.getpid()), encoding="ascii")
    elif scope["kind"] != "windows-job":
        raise ValueError("unsupported native scope")
    release = Path(envelope["release"])
    deadline = time.monotonic() + 30
    while True:
        if (Path(path).parent / "cancel").exists():
            return 125
        if release.is_file():
            break
        if time.monotonic() >= deadline:
            raise TimeoutError("native launch was never released")
        time.sleep(0.02)
    if scope["kind"] == "linux-cgroup":
        os.chdir(envelope["cwd"])
        os.execve(envelope["argv"][0], envelope["argv"], dict(os.environ))
    # The Windows supervisor remains a member of the non-breakaway Job.
    # This standalone -I launcher cannot import ADORE's package helpers.
    # Windows CREATE_NO_WINDOW needs explicit standard handles: implicit
    # inheritance can exit cleanly while discarding both captured streams.
    # These are the supervisor's parent-owned pipes, drained by its controller.
    options = {}
    if windows_verification:
        # cmd does not decode C-runtime backslash-quote escapes. /s /c removes
        # this extra outer quote pair, leaving the configured shell text intact.
        # Pin lpApplicationName separately; never search PATH or use shell=True.
        options["executable"] = argv[0]
        argv = subprocess.list2cmdline(argv[:1]) + ' /d /s /c "' + argv[-1] + '"'
    result = subprocess.run(  # noqa: S603 - native command resolved by the parent
        argv, cwd=envelope["cwd"], check=False, creationflags=0x08000000, **options,
        stdin=sys.stdin if streaming else subprocess.DEVNULL, stdout=sys.stdout, stderr=sys.stderr,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], streaming=sys.argv[2:] == ["rpc"]))

# END OF FILE
