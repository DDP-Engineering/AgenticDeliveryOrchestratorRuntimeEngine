#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file __init__.py
@brief CodeGraph: an optional, read-only code-navigation index for AEGIS.
@details The package indexes configured repository source into a
         checkout-local SQLite database and answers bounded, source-cited
         queries. Read operations use only the standard library; vendored
         Tree-sitter parsers load only while indexing.
"""

# END OF FILE
