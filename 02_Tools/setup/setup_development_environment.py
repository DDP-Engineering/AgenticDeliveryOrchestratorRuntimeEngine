#!/usr/bin/env python3
"""Prepare the ADORE repository environment on Windows or Linux."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    """
    Prepare repository dependencies without running deployment or tests.
    argv: Optional arguments; only standard help is supported.
    Returns: Zero on completion, one for missing prerequisites or failed commands.
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
    print("Repository environment ready. Next: python 02_Tools/build/build_web_assets.py "
          "or python 02_Tools/package/create_delivery_package.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
