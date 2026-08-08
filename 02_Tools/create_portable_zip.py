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
@file create_portable_zip.py
@brief Create one ZIP whose member names are portable POSIX paths.
@details Both runtime packagers call this standard-library helper so a ZIP
         built on Windows extracts to the same documented tree on Linux.
         Unsafe source entries and invalid input/output placement fail closed.
"""

from __future__ import annotations

# IMPORTS
import argparse
import os
from pathlib import Path
import sys
import tempfile
import zipfile

# EXPORTED FUNCTIONS / PUBLIC API

def create_portable_zip(bundle_dir: Path, archive_path: Path) -> None:
    """
    @brief      Archive a staged bundle with forward-slash member names.
    @param[in]  bundle_dir Root directory included in the ZIP.
    @param[out] archive_path Destination ZIP, atomically replaced on success.
    @exception ValueError When the bundle/output relationship is unsafe.
    @exception OSError When input inspection or archive I/O fails.
    """
    bundle = bundle_dir.resolve(strict=True)
    if not bundle.is_dir():
        raise ValueError(f"bundle is not a directory: {bundle}")
    archive_parent = archive_path.parent.resolve(strict=True)
    archive = archive_parent / archive_path.name
    if archive == bundle or bundle in archive.parents:
        raise ValueError("archive destination must be outside the bundle")

    entries = sorted(bundle.rglob("*"), key=lambda item: item.as_posix())
    for entry in entries:
        if entry.is_symlink():
            raise ValueError(f"links are forbidden in runtime bundles: {entry}")
        if not entry.is_dir() and not entry.is_file():
            raise ValueError(f"unsupported runtime bundle entry: {entry}")

    descriptor, temporary_name = tempfile.mkstemp(
        dir=archive_parent,
        prefix=f".{archive.name}.",
        suffix=".tmp",
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive_file:
            for entry in entries:
                member = entry.relative_to(bundle.parent).as_posix()
                archive_file.write(entry, member)
        os.replace(temporary, archive)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    """
    @brief      Run the portable ZIP command.
    @param[in]  argv Optional argument vector for tests.
    @return     Zero on success, one on a validated operational failure.
    """
    parser = argparse.ArgumentParser(
        description="create a portable runtime ZIP with POSIX member names",
    )
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument("archive_path", type=Path)
    args = parser.parse_args(argv)
    try:
        create_portable_zip(args.bundle_dir, args.archive_path)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# END OF FILE
