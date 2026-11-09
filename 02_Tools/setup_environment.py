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
@file       setup_environment.py
@brief      Prepare the ADORE repository environment on Windows or Linux.
@details    Synchronizes locked Python/frontend dependencies and Chromium.
            Does not run tests, install services or configure credentials.
"""

from __future__ import annotations

# IMPORTS
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

# CONSTANTS
REPO = Path(__file__).resolve().parents[1]


# PUBLIC API
def main(argv: list[str] | None = None) -> int:
    """@brief Prepare repository dependencies without running deployment or tests.
    @param[in] argv Optional arguments; only standard help is supported.
    @return Zero on completion, one for missing prerequisites or failed commands.
    """
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    if sys.version_info < (3, 11):
        print("Python 3.11 or later is required on the development host.", file=sys.stderr)
        return 1
    commands = {name: shutil.which(name) for name in ("git", "uv", "node", "npm")}
    missing = [name for name, executable in commands.items() if executable is None]
    if missing:
        print("Install these development tools first: " + ", ".join(missing), file=sys.stderr)
        return 1
    try:
        node = subprocess.run([commands["node"], "--version"], check=True,
                              capture_output=True, text=True, timeout=15).stdout.strip()
        if tuple(map(int, node.removeprefix("v").split(".")[:2])) < (22, 18):
            raise ValueError("Node.js 22.18 or later is required")
        for command, directory in (
            ([commands["uv"], "sync", "--frozen", "--extra", "web"], REPO / "04_Software"),
            ([commands["npm"], "ci"], REPO / "04_Software/web"),
            ([commands["npm"], "exec", "--", "playwright", "install", "chromium"],
             REPO / "04_Software/web"),
        ):
            subprocess.run(command, cwd=directory, check=True, timeout=1800)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Environment setup failed: {error}", file=sys.stderr)
        return 1
    print("Repository environment ready. Next: python 02_Tools/create_package.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# END OF FILE
