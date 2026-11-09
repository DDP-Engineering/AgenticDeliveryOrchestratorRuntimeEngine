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
@file    host_folders.py
@brief   Read-only bounded native directory navigation for administrators.
@details Lists directory names on the ADORE host without opening file contents,
         invoking tools or creating folders. Links and network/device paths are
         refused; clone publication owns destination checks and actual writes.
"""

# IMPORTS
from itertools import islice
import os
from pathlib import Path
import platform
import stat

# CONSTANTS
MAX_FOLDERS = 200
MAX_SCANNED = 2000
MAX_PATH = 4096


# DATA MODELS
class HostFolderError(ValueError):
    """@brief Invalid or unreadable host directory; no raw OS diagnostics escape."""


# LOCAL HELPERS
def _local_drive(anchor: str) -> bool:
    """@brief Refuse mapped network/unavailable Windows drives before filesystem reads."""
    if os.name != "nt":
        return True
    import ctypes

    drive_type = ctypes.windll.kernel32.GetDriveTypeW
    drive_type.argtypes = [ctypes.c_wchar_p]
    drive_type.restype = ctypes.c_uint
    return drive_type(anchor) in {2, 3, 5, 6}  # Removable, fixed, optical, RAM.


def _safe_text(value: str) -> bool:
    return bool(value) and len(value) <= MAX_PATH and all(ch.isprintable() for ch in value)


def _directory(value: str) -> Path:
    """@brief Validate a native absolute directory without following links.
    @param[in] value Untrusted administrator-supplied path.
    @return Normalized existing local directory.
    @exception HostFolderError Invalid, missing, linked or inaccessible directory.
    """
    if not _safe_text(value) or value.startswith(("//", "\\\\")):
        raise HostFolderError("host_folder_unavailable")
    path = Path(value)
    if (not path.is_absolute() or ".." in path.parts or len(path.parts) > 128
            or not _local_drive(path.anchor)):
        raise HostFolderError("host_folder_unavailable")
    try:
        for item in (*reversed(path.parents), path):
            info = item.lstat()
            if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise HostFolderError("host_folder_unavailable")
        return path.resolve(strict=True)
    except (OSError, ValueError) as exc:
        raise HostFolderError("host_folder_unavailable") from exc


# PUBLIC API
def list_host_folders(path: str | None = None) -> dict:
    """@brief Return directory metadata for one bounded host navigation step.
    @param[in] path Absolute directory, or None/empty for the current account home.
    @return Native system, path, parent, roots, up to 200 folders and truncated flag.
    @exception HostFolderError Invalid, missing, linked or inaccessible path.
    @note At most 2000 directory entries are examined; no file contents are opened.
    """
    directory = _directory(path or str(Path.home()))
    folders = []
    truncated = False
    try:
        with os.scandir(directory) as entries:
            for index, entry in enumerate(islice(entries, MAX_SCANNED + 1)):
                if index == MAX_SCANNED:
                    truncated = True
                    break
                try:
                    if (not entry.is_dir(follow_symlinks=False) or not _safe_text(entry.name)
                            or "\\" in entry.name or not _safe_text(str(directory / entry.name))):
                        continue
                    if getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400:
                        continue
                except OSError:
                    continue
                if len(folders) == MAX_FOLDERS:
                    truncated = True
                    break
                folders.append({"name": entry.name, "path": str(directory / entry.name)})
    except OSError as exc:
        raise HostFolderError("host_folder_unavailable") from exc
    roots = [directory.anchor]
    if os.name == "nt" and hasattr(os, "listdrives"):
        try:
            roots = [drive for drive in os.listdrives()
                     if len(drive) == 3 and drive[1:] == ":\\" and _local_drive(drive)]
        except OSError as exc:
            raise HostFolderError("host_folder_unavailable") from exc
    home = str(Path.home())
    if _safe_text(home) and Path(home).is_absolute() and home not in roots:
        roots.append(home)
    return {"system": platform.system(), "path": str(directory),
            "parent": str(directory.parent) if directory.parent != directory else None,
            "roots": roots, "folders": sorted(folders, key=lambda row: row["name"].casefold()),
            "truncated": truncated}


# END OF FILE
