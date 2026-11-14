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
@file       build_web_assets.py
@brief      Build ADORE's licensed production web assets from prepared sources.
@details    Uses the locked frontend environment, runs type checking and Vite,
            then stamps the application assets. Does not install dependencies,
            run tests, package archives or start services.
"""

from __future__ import annotations

# IMPORTS
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

# CONSTANTS
REPO = Path(__file__).resolve().parents[2]


# PUBLIC API
def main(argv: list[str] | None = None) -> int:
    """@brief Build production frontend assets within a thirty-minute limit.
    @param[in] argv Optional command arguments; only standard help is supported.
    @return Zero after building, one for missing prerequisites or build failure.
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

# END OF FILE
