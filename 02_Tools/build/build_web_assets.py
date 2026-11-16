#!/usr/bin/env python3
"""Build ADORE's licensed production web assets from prepared sources."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    """
    Build production frontend assets within a thirty-minute limit.
    argv: Optional command arguments; only standard help is supported.
    Returns: Zero after building, one for missing prerequisites or build failure.
    """
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    web = REPO / "04_Software/web"
    npm = shutil.which("npm")
    if not npm or not (web / "node_modules/vite/bin/vite.js").is_file():
        print("Prepare dependencies first: python "
              "02_Tools/setup/setup_development_environment.py", file=sys.stderr)
        return 1
    try:
        subprocess.run([npm, "run", "build"], cwd=web, check=True, timeout=1800)
    except (OSError, subprocess.SubprocessError) as error:
        print(f"Web asset build failed: {error}", file=sys.stderr)
        return 1
    print("Built licensed assets in 04_Software/adore/web/static")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
