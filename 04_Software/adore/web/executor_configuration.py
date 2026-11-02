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
@file       executor_configuration.py
@brief      Reviewed Pi launch command presets.
@details    A container project may choose only a preset for `executor.command`
            (its run uses the image's pinned Pi over RPC); a local project
            accepts any validated installed native argv.
"""

# IMPORTS
from adore.branding import PI_NATIVE_COMMAND

# CONSTANTS
LAUNCH_PRESETS = {"executor.command": (PI_NATIVE_COMMAND,)}


# END OF FILE
