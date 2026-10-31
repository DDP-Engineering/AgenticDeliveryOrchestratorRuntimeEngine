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
import os
from pathlib import Path
import subprocess
import sys
import time

# PUBLIC API


def main(path: str) -> int:
    """
    @brief Start one native argv command only after the parent's ownership receipt.
    @param[in] path Parent-owned immutable launch envelope.
    @return Authoritative command exit status.
    @exception ValueError Invalid trusted transport.
    """
    envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    if set(envelope) != {"argv", "cwd", "release", "scope"}:
        raise ValueError("invalid native launch envelope")
    if (
        not isinstance(envelope["argv"], list)
        or not envelope["argv"]
        or any(not isinstance(arg, str) or "\x00" in arg for arg in envelope["argv"])
    ):
        raise ValueError("invalid native argv")
    scope = envelope["scope"]
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
    result = subprocess.run(  # noqa: S603 - native argv resolved by the parent
        envelope["argv"], cwd=envelope["cwd"], check=False, creationflags=0x08000000,
        stdin=subprocess.DEVNULL, stdout=sys.stdout, stderr=sys.stderr,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))

# END OF FILE
