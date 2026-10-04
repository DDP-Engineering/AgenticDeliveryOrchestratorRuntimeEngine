#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file natives.py
@brief Vendored Tree-sitter parser selection and indexing capability.
@details `vendor/` holds the pure-Python parts of the pinned binding and
         grammar once, plus one native binary per supported interpreter. The
         binary names carry Python's own extension-module suffixes, so the
         import system loads the binary built for the running interpreter
         and ignores the rest. Capability checks only look at file names;
         nothing here imports a native module until `new_parser` is called,
         which only the indexer does.
"""

# IMPORTS

from __future__ import annotations

import importlib.machinery
import json
import platform
import sys
from pathlib import Path

# CONSTANTS

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
VENDOR = PLUGIN_ROOT / "vendor"
MANIFEST = PLUGIN_ROOT / "MANIFEST.json"
#: vendored packages that must both offer a binary for this interpreter
PACKAGES = ("tree_sitter", "tree_sitter_python")

# PUBLIC API


def read_manifest(path: Path = MANIFEST) -> dict:
    """
    @brief Read the plugin manifest.
    @param[in] path Manifest file; the plugin's own by default.
    @return The parsed manifest object.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def platform_key(version: tuple[int, int] | None = None) -> str:
    """
    @brief Name this platform and interpreter as the manifest's matrix does.
    @param[in] version (major, minor); the running interpreter by default.
    @return For example `win32-amd64-3.12` or `linux-x86_64-3.12`.
    """
    major, minor = version or sys.version_info[:2]
    return f"{sys.platform}-{platform.machine().lower()}-{major}.{minor}"


def binding_present(package: Path, suffixes: list[str]) -> bool:
    """@brief Whether `package` holds `_binding` with one of `suffixes`."""
    return any((package / f"_binding{suffix}").is_file() for suffix in suffixes)


def capability(vendor: Path = VENDOR, manifest: dict | None = None,
               suffixes: list[str] | None = None) -> dict:
    """
    @brief Report whether this interpreter can index, without importing natives.
    @param[in] vendor Folder holding the vendored packages.
    @param[in] manifest Manifest with the `tested` matrix; read when omitted.
    @param[in] suffixes Extension suffixes to accept; the interpreter's own by
               default. Free-threaded and other ABIs have different suffixes
               and therefore find no binary.
    @return `indexing_supported` and `python_support` (`tested`, `untested`,
            or None when indexing is unsupported).
    """
    accepted = list(importlib.machinery.EXTENSION_SUFFIXES if suffixes is None
                    else suffixes)
    if not all(binding_present(vendor / name, accepted) for name in PACKAGES):
        return {"indexing_supported": False, "python_support": None}
    tested = (manifest if manifest is not None else read_manifest()).get("tested", [])
    return {"indexing_supported": True,
            "python_support": "tested" if platform_key() in tested else "untested"}


def ensure_on_path(vendor: Path = VENDOR) -> None:
    """
    @brief Put the vendored packages first on `sys.path`.
    @details First position matters: without isolated mode, `PYTHONPATH` and
             site-packages could otherwise supply another `tree_sitter`.
    """
    entry = str(vendor)
    if entry in sys.path:
        sys.path.remove(entry)
    sys.path.insert(0, entry)


def new_parser():
    """
    @brief Load the vendored binding and Python grammar and return a parser.
    @return A `tree_sitter.Parser` configured for Python.
    @exception ImportError when this interpreter has no matching binary.
    """
    ensure_on_path()
    import tree_sitter
    import tree_sitter_python
    return tree_sitter.Parser(tree_sitter.Language(tree_sitter_python.language()))

# END OF FILE
