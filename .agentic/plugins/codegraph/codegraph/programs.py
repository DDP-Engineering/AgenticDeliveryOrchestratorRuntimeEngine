#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file programs.py
@brief Locate system programs on PATH, never inside the repository.
@details Windows searches the working directory before PATH unless
         `NoDefaultCurrentDirectoryInExePath` is set, and the plugin runs
         from the repository root, so a program committed there would run in
         place of the real one; `shutil.which` searches it too. The same rule
         as the AEGIS core's `system_program`: empty and relative PATH entries
         and anything inside the repository are skipped.
"""

# IMPORTS

from __future__ import annotations

import os
import sys
from pathlib import Path

# PUBLIC API


def find(name: str, root: Path) -> str | None:
    """
    @brief Absolute path of a program found on PATH outside root.
    @param[in] name Program name without extension, such as `git`.
    @param[in] root Repository root; nothing inside it is ever returned.
    @return None when no such location exists - the program counts as missing.
    """
    inside = root.resolve()
    # Windows: `.exe` only, as a bare-name launch would; a `.cmd` or `.bat`
    # runs through cmd.exe, which re-parses arguments such as file names
    names = [name + ".exe"] if sys.platform == "win32" and not Path(name).suffix else [name]
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        entry = entry.strip().strip('"')
        if not entry or not os.path.isabs(entry):
            continue
        try:
            folder = Path(entry).resolve()
        except (OSError, ValueError):
            continue
        if folder.is_relative_to(inside):
            continue   # a repository folder on PATH is never searched
        for candidate in names:
            path = folder / candidate
            # os.path.isfile reports an unreadable folder as False instead of raising
            if not os.path.isfile(path) or (sys.platform != "win32"
                                            and not os.access(path, os.X_OK)):
                continue
            try:
                resolved = path.resolve()
            except (OSError, ValueError):
                break
            if not resolved.is_relative_to(inside):
                return str(resolved)
            break   # this folder's match decides it; a link into the repository is skipped
    return None

# END OF FILE
