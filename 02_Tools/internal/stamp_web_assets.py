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
@file       stamp_web_assets.py
@brief      Add the project license to built JS/CSS and bundle the license text.
@details    Stamps deployable or isolated Vite build outputs.
"""

# IMPORTS
import argparse
from pathlib import Path


# PUBLIC API
def main(argv: list[str] | None = None) -> int:
    """@brief Stamp an existing web build and copy its legal notices.

    @param[in] argv Optional CLI arguments; --output selects an isolated build.
    @return Zero after stamping the requested build.
    @exception SystemExit The destination has no built index.html.
    """
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=repo / "04_Software" / "adore" / "web" / "static")
    static = parser.parse_args(argv).output.resolve()
    if not (static / "index.html").is_file():
        parser.error("output must contain a built index.html")
    banner = (
        "/*\nCopyright (c) 2026 DDP Engineering\n"
        "This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
        "Commercial use requires a separate commercial license.\n"
        "See the LICENSE.txt file for full license details. "
        "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n*/\n"
    )
    for path in static.rglob("*"):
        if path.suffix not in (".js", ".css"):
            continue
        content = path.read_text(encoding="utf-8")
        if not content.startswith("/*\nCopyright (c) 2026 DDP Engineering"):
            path.write_text(banner + content, encoding="utf-8")
    (static / "LICENSE.txt").write_bytes((repo / "LICENSE.txt").read_bytes())
    (static / "THIRD_PARTY_NOTICES.md").write_bytes(
        (repo / "04_Software" / "web" / "THIRD_PARTY_NOTICES.md").read_bytes()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE
