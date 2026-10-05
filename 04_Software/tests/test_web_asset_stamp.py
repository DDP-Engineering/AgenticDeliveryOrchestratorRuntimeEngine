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
@file       test_web_asset_stamp.py
@brief      Legal stamping contracts for isolated frontend builds.
@details    Exercises the CLI using temporary output only; dependency tools and
            production assets are never invoked or modified.
"""

# IMPORTS
from pathlib import Path
import subprocess
import sys

import pytest

# CONSTANTS
REPOSITORY = Path(__file__).resolve().parents[2]
STAMPER = REPOSITORY / "02_Tools" / "stamp_web_assets.py"


# LOCAL HELPERS
def stamp(output: Path) -> subprocess.CompletedProcess:
    """@brief Run the standalone asset-stamping CLI against a temporary build."""
    return subprocess.run(
        [sys.executable, str(STAMPER), "--output", str(output)],
        capture_output=True, text=True, timeout=10, check=False,
    )


# PUBLIC API / TESTS
def test_isolated_build_is_stamped_once_with_matching_notices(tmp_path):
    """@brief JS/CSS banners and legal notices are correct and idempotent."""
    output = tmp_path / "build with spaces"
    output.mkdir()
    (output / "index.html").write_text("<!doctype html>", encoding="utf-8")
    (output / "app.js").write_text("console.log('offline');", encoding="utf-8")
    (output / "app.css").write_text("body { color: black; }", encoding="utf-8")
    result = stamp(output)
    assert result.returncode == 0, result.stderr
    for suffix in ("js", "css"):
        content = (output / f"app.{suffix}").read_text(encoding="utf-8")
        assert content.startswith("/*\nCopyright (c) 2026 DDP Engineering\n")
        assert "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0" in content
    assert (output / "LICENSE.txt").read_bytes() == (REPOSITORY / "LICENSE.txt").read_bytes()
    assert (output / "THIRD_PARTY_NOTICES.md").read_bytes() == (
        REPOSITORY / "04_Software" / "web" / "THIRD_PARTY_NOTICES.md"
    ).read_bytes()
    first = {path.name: path.read_bytes() for path in output.iterdir()}
    assert stamp(output).returncode == 0
    assert {path.name: path.read_bytes() for path in output.iterdir()} == first


@pytest.mark.parametrize("existing", [False, True])
def test_missing_built_index_is_rejected_without_writing(existing, tmp_path):
    """@brief Missing or incomplete build directories fail before mutation."""
    output = tmp_path / "invalid"
    if existing:
        output.mkdir()
        (output / "app.js").write_text("unchanged", encoding="utf-8")
    result = stamp(output)
    assert result.returncode == 2
    assert "output must contain a built index.html" in result.stderr
    assert not (output / "LICENSE.txt").exists()
    if existing:
        assert (output / "app.js").read_text(encoding="utf-8") == "unchanged"
    else:
        assert not output.exists()

# END OF FILE
