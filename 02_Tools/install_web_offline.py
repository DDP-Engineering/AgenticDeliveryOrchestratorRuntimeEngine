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
@file install_web_offline.py
@brief Verify and install an ADORE web bundle without network access.
@details Uses only a host Python with venv/pip and the supplied wheelhouse.
"""

from __future__ import annotations

# IMPORTS
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import venv


def _digest(path: Path) -> str:
    """@brief Return SHA-256 for manifest verification."""
    hash_ = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hash_.update(chunk)
    return hash_.hexdigest()


def main() -> int:
    """@brief Check exact host compatibility and install from local wheels."""
    executable = Path(sys.executable)
    if executable.is_symlink():
        resolved = executable.resolve(strict=True)
        os.execv(str(resolved), [str(resolved), str(Path(__file__).resolve()),
                                 *sys.argv[1:]])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path("runtime"))
    parser.add_argument("--check-only", action="store_true",
                        help="Verify bundle and host prerequisites without installation")
    parser.add_argument("--load-images", action="store_true")
    parser.add_argument("--runtime", choices=("docker", "podman"), default="docker")
    args = parser.parse_args()
    bundle = Path(__file__).resolve().parent
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != 1:
        raise SystemExit("unsupported offline bundle schema")
    current = f"{sys.version_info.major}.{sys.version_info.minor}"
    if (platform.system() != manifest["system"]
            or platform.machine() != manifest["machine"]
            or current != manifest["python"]):
        raise SystemExit("bundle OS, architecture, or Python version does not match this host")
    listed = set(manifest["files"])
    actual = {path.relative_to(bundle).as_posix() for path in bundle.rglob("*")
              if path.is_file()} - {"manifest.json"}
    if extra := actual - listed:
        raise SystemExit(f"unlisted bundle file: {sorted(extra)[0]}")
    for name, expected in manifest["files"].items():
        path = (bundle / name).resolve()
        if not path.is_relative_to(bundle.resolve()) or not path.is_file():
            raise SystemExit(f"missing bundle file: {name}")
        if _digest(path) != expected:
            raise SystemExit(f"bundle checksum mismatch: {name}")
    prerequisites = manifest.get("prerequisites", {})
    if not isinstance(prerequisites, dict):
        raise SystemExit("invalid prerequisite manifest")
    for group, alternatives in prerequisites.items():
        if (group not in {"git", "forge_cli", "executor_cli", "container_runtime"}
                or not isinstance(alternatives, list) or not alternatives
                or any(not isinstance(item, str)
                       or not re.fullmatch(r"[a-z][a-z0-9.-]*", item)
                       for item in alternatives)):
            raise SystemExit(f"invalid prerequisite group: {group}")
        if not any(shutil.which(item) for item in alternatives):
            raise SystemExit(
                f"missing offline prerequisite {group}: "
                f"install one of {', '.join(alternatives)} before ADORE"
            )
    try:
        import ensurepip
        ensurepip.version()
    except (ImportError, OSError, RuntimeError) as exc:
        raise SystemExit(
            "host Python lacks venv/ensurepip; supply python3-venv (Ubuntu) "
            "or a Python distribution with bundled pip before offline install"
        ) from exc
    if args.check_only and args.load_images:
        raise SystemExit("--check-only cannot load images")
    target = args.target.resolve()
    if not args.check_only and target.exists():
        raise SystemExit(f"target already exists; choose an empty target: {target}")
    images = manifest.get("images")
    if (not isinstance(images, list)
            or any(not isinstance(item, dict)
                   or not isinstance(item.get("tag"), str)
                   or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,254}",
                                       item["tag"])
                   or (item.get("archive") is not None and (
                       not isinstance(item["archive"], str)
                       or not re.fullmatch(r"image-[1-9][0-9]*\.tar", item["archive"])
                       or item["archive"] not in listed))
                   for item in images)
            or len({item["tag"] for item in images}) != len(images)):
        raise SystemExit("invalid image manifest")
    executor_cli = manifest.get("executor_image_cli", "any")
    executor_image = manifest.get("executor_image_tag", "")
    if (executor_cli not in ("any", "opencode", "pi", "codex")
            or not isinstance(executor_image, str)
            or (executor_image and executor_image not in {
                item["tag"] for item in images})):
        raise SystemExit("invalid executor image prerequisite")
    runtime_argv = ([args.runtime] if shutil.which(args.runtime)
                    else ["wsl", "--", args.runtime]
                    if platform.system() == "Windows" and shutil.which("wsl")
                    else None)
    if images and runtime_argv is None:
        raise SystemExit(f"missing offline prerequisite image loader: {args.runtime}")
    if args.load_images:
        for item in images:
            if item["archive"] is not None:
                archive = str(bundle / item["archive"])
                if runtime_argv[0] == "wsl":
                    translated = subprocess.run(
                        ["wsl", "--", "wslpath", "-a", archive],
                        capture_output=True, text=True, check=False, timeout=15,
                    )
                    if translated.returncode or not translated.stdout.strip():
                        raise SystemExit("cannot map bundled image path into WSL")
                    archive = translated.stdout.strip()
                subprocess.run([*runtime_argv, "load", "-i", archive],
                               check=True, timeout=600)
    for item in images:
        if args.check_only and item["archive"] is not None:
            continue  # The media itself supplies this image after preflight.
        present = subprocess.run(
            [*runtime_argv, "image", "inspect", item["tag"]],
            capture_output=True, check=False, timeout=15,
        )
        if present.returncode:
            raise SystemExit(f"missing offline prerequisite image: {item['tag']}")
    if executor_cli != "any" and executor_image and not (
            args.check_only and any(item["tag"] == executor_image
                                    and item["archive"] is not None for item in images)):
        checked = subprocess.run(
            [*runtime_argv, "run", "--rm", "--pull=never", "--network", "none",
             "--entrypoint", "python", executor_image, "-c",
             "import shutil,sys; sys.exit(0 if shutil.which(sys.argv[1]) else 1)",
             executor_cli],
            capture_output=True, check=False, timeout=15,
        )
        if checked.returncode:
            raise SystemExit(
                f"missing offline prerequisite executor in image: {executor_cli}"
            )
    if args.check_only:
        print("Offline bundle and host prerequisites verified")
        return 0
    venv.EnvBuilder(with_pip=True).create(target)
    python = target / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--no-index", "--no-cache-dir",
         "--find-links", str(bundle / "wheels"),
         "-r", str(bundle / "requirements.txt"),
         f"adore[web]=={manifest['adore_version']}"],
        check=True, timeout=600,
    )
    print(f"Installed ADORE {manifest['adore_version']} at {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE
