#!/usr/bin/env python3
# -*- coding: utf-8 -*-  # noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file __main__.py
@brief Module entry point so `python -m adore` runs the CLI.
@details Delegates to adore.cli.main.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.1.0
"""

# IMPORTS

from adore.cli import main

# PUBLIC API

if __name__ == "__main__":
    raise SystemExit(main())

# END OF FILE
