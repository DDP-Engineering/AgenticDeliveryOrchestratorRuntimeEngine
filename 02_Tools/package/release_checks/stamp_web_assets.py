#!/usr/bin/env python3
"""Add the project license to built JS/CSS and bundle the license text."""

import argparse
import hashlib
import json
from pathlib import Path


STAMP = "BUILD_FINGERPRINT.json"


def fingerprint(repo: Path, static: Path) -> dict:
    """
    Compute deterministic hashes of frontend build inputs and outputs.
    repo: Repository root containing the frontend sources.
    static: Build output directory.
    Returns: Path-to-hash mappings for inputs and output files.
    Raises OSError: A required input or output cannot be read.
    """
    web = repo / "04_Software/web"
    inputs = [repo / "LICENSE.txt", repo / "02_Tools/package/release_checks/stamp_web_assets.py"]
    inputs += [web / name for name in ("index.html", "package.json", "package-lock.json", "tsconfig.json", "vite.config.ts", "THIRD_PARTY_NOTICES.md")]
    for folder in ("src", "public"):
        directory = web / folder
        if folder == "src" and not directory.is_dir():
            raise FileNotFoundError(directory)
        if directory.exists():
            inputs.extend(path for path in directory.rglob("*") if path.is_file())
    outputs = [path for path in static.rglob("*") if path.is_file() and path != static / STAMP]
    if not (static / "index.html").is_file():
        raise FileNotFoundError(static / "index.html")
    def hashes(paths, root, normalize_text=False):
        result = {}
        for path in sorted(paths):
            content = path.read_bytes()
            if normalize_text and path.suffix.lower() in {
                ".css", ".html", ".js", ".json", ".md", ".py", ".svg",
                ".ts", ".tsx", ".txt", ".yaml", ".yml",
            }:
                content = content.replace(b"\r\n", b"\n")
            result[path.relative_to(root).as_posix()] = hashlib.sha256(content).hexdigest()
        return result
    return {"inputs": hashes(inputs, repo, True), "outputs": hashes(outputs, static)}


def main(argv: list[str] | None = None) -> int:
    """
    Stamp an existing web build and copy its legal notices.

    argv: Optional CLI arguments; --output selects an isolated build.
    Returns: Zero after stamping the requested build.
    Raises SystemExit: The destination has no built index.html.
    """
    repo = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=repo / "04_Software" / "adore" / "web" / "static")
    static = parser.parse_args(argv).output.resolve()
    if not (static / "index.html").is_file():
        parser.error("output must contain a built index.html")
    # REUSE-IgnoreStart
    banner = (
        "/*\nCopyright (c) 2026 DDP Engineering\n"
        "This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
        "Commercial use requires a separate commercial license.\n"
        "See the LICENSE.txt file for full license details. "
        "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n*/\n"
    )
    # REUSE-IgnoreEnd
    for path in static.rglob("*"):
        if path.suffix not in (".js", ".css"):
            continue
        content = path.read_text(encoding="utf-8")
        if not content.startswith("/*\nCopyright (c) 2026 DDP Engineering"):
            path.write_text(banner + content, encoding="utf-8", newline="\n")
    (static / "LICENSE.txt").write_bytes((repo / "LICENSE.txt").read_bytes())
    (static / "THIRD_PARTY_NOTICES.md").write_bytes(
        (repo / "04_Software" / "web" / "THIRD_PARTY_NOTICES.md").read_bytes()
    )
    (static / STAMP).write_text(
        json.dumps(fingerprint(repo, static), indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
