#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file codegraph.py
@brief Entry point of the CodeGraph plugin.
@details AEGIS runs this file as `python -I -B -X utf8 codegraph.py <operation>`.
         Isolated mode leaves this folder off `sys.path`, so the entry adds it
         itself, and it disables bytecode writing before importing its own
         modules so a standalone run without `-B` writes none either.
         Extraction workers started with the `spawn` method re-run this file
         as `__mp_main__`, which repeats both settings and starts nothing.
"""

# IMPORTS

import sys

sys.dont_write_bytecode = True

from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE in sys.path:
    sys.path.remove(_HERE)
sys.path.insert(0, _HERE)

# PUBLIC API

if __name__ == "__main__":
    from codegraph.cli import main

    sys.exit(main())

# END OF FILE
