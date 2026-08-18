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
@file test_release_consistency.py
@brief Public-command tests for the ADORE release consistency check.
"""

from __future__ import annotations

# IMPORTS
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

# CONSTANTS

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "02_Tools" / "check_release_consistency.py"
PORTABLE_ZIPPER = REPO_ROOT / "02_Tools" / "create_portable_zip.py"
REQUIRED_INPUTS = (
    "README.md",
    "CHANGELOG.md",
    "02_Tools/package_runtime.ps1",
    "02_Tools/package_runtime.sh",
    "04_Software/pyproject.toml",
    "04_Software/uv.lock",
    "04_Software/adore/__init__.py",
    "04_Software/adore/branding.py",
    "04_Software/deploy/adore.service",
    "04_Software/deploy/install-windows.ps1",
    "04_Software/docker/README.md",
)


# HELPER FUNCTIONS

def _run(root: Path) -> subprocess.CompletedProcess[str]:
    """
    @brief      Execute the public release-check command for a repository root.
    @param[in]  root Repository root to validate.
    @return     Captured subprocess result.
    """
    return subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", str(root)],
        check=False,
        capture_output=True,
        text=True,
    )


def _copy_inputs(destination: Path) -> None:
    """
    @brief      Build an isolated minimal release-check fixture.
    @param[in]  destination Fixture repository root.
    """
    for relative in REQUIRED_INPUTS:
        source = REPO_ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (destination / "07_Delivery").mkdir(parents=True)


# PUBLIC API / TESTS

def test_repository_release_identity_is_consistent() -> None:
    """
    @brief   The current repository passes the public release check.
    """
    result = _run(REPO_ROOT)
    assert result.returncode == 0, result.stderr
    assert "ADORE 0.6.0 release identity is consistent" in result.stdout


def test_release_check_fails_closed_on_bad_metadata_and_old_identity(
    tmp_path: Path,
) -> None:
    """
    @brief   Mismatched package metadata and a forbidden pre-1.0 token are
             both reported; the command never guesses or silently repairs.
    """
    _copy_inputs(tmp_path)
    init_path = tmp_path / "04_Software/adore/__init__.py"
    init_path.write_text(
        init_path.read_text(encoding="utf-8").replace('"0.6.0"', '"9.9.9"'),
        encoding="utf-8",
    )
    old_name = "AD" + "OR"
    (tmp_path / "notes.txt").write_text(f"old executable: {old_name}\n", encoding="utf-8")

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "adore.__version__ does not match 0.6.0" in result.stderr
    assert "legacy identity in notes.txt:1" in result.stderr


def test_release_check_scans_presentation_xml(tmp_path: Path) -> None:
    """
    @brief   A pre-1.0 identity hidden inside a presentation fails the check.
    """
    _copy_inputs(tmp_path)
    presentation = tmp_path / "operator.pptx"
    previous_name = "AD" + "OR"
    with zipfile.ZipFile(presentation, "w") as archive:
        archive.writestr(
            "ppt/slides/slide1.xml",
            f"<slide><text>{previous_name} operator guide</text></slide>",
        )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "legacy identity in operator.pptx:ppt/slides/slide1.xml" in result.stderr


def test_portable_zip_command_writes_cross_platform_member_names(
    tmp_path: Path,
) -> None:
    """
    @brief   The public ZIP writer creates the documented nested tree with
             forward-slash names on every host.
    """
    bundle = tmp_path / "adore-runtime-test"
    nested = bundle / "Documentation"
    nested.mkdir(parents=True)
    (nested / "README.md").write_text("portable\n", encoding="utf-8")
    archive = tmp_path / "runtime.zip"

    result = subprocess.run(
        [sys.executable, str(PORTABLE_ZIPPER), str(bundle), str(archive)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    with zipfile.ZipFile(archive) as runtime_zip:
        names = runtime_zip.namelist()
        runtime_zip.extractall(tmp_path / "unpacked")
    assert names
    assert all("\\" not in name for name in names)
    assert (tmp_path / "unpacked/adore-runtime-test/Documentation/README.md").is_file()


def test_portable_zip_command_fails_closed_on_missing_bundle(
    tmp_path: Path,
) -> None:
    """
    @brief   A missing external bundle path returns an error and creates no ZIP.
    """
    archive = tmp_path / "runtime.zip"

    result = subprocess.run(
        [
            sys.executable,
            str(PORTABLE_ZIPPER),
            str(tmp_path / "missing"),
            str(archive),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "error:" in result.stderr
    assert not archive.exists()

# END OF FILE
