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
@file package_web_offline.py
@brief Build a host-specific offline ADORE web installation directory.
@details Download and build only on the packaging host. Installation verifies
         every included file and uses pip with --no-index.
"""

from __future__ import annotations

# IMPORTS
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tomllib


# HELPER FUNCTIONS
def _run(argv: list[str], cwd: Path) -> None:
    """@brief Run one bounded build command and fail on nonzero exit."""
    subprocess.run(argv, cwd=cwd, check=True, timeout=1800)


def _digest(path: Path) -> str:
    """@brief SHA-256 for the offline manifest."""
    hash_ = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hash_.update(chunk)
    return hash_.hexdigest()


# PUBLIC API
def main() -> int:
    """@brief Produce one OS/Python specific offline web bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("07_Delivery"))
    parser.add_argument("--image", action="append", default=[],
                        help="Prebuilt Docker/Podman image tag to archive (repeatable)")
    parser.add_argument("--require-image", action="append", default=[],
                        help="Image tag already supplied offline on the install host")
    parser.add_argument("--executor-image", default="",
                        help="Which listed image contains the selected executor CLI")
    parser.add_argument("--runtime", choices=("docker", "podman"), default="docker")
    parser.add_argument("--forge", choices=("any", "gitlab", "github", "gitea"),
                        default="any", help="Forge CLI required on the install host")
    parser.add_argument("--executor", choices=("any", "opencode", "pi", "codex"),
                        default="any", help="Executor CLI required on the install host")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    software = repo / "04_Software"
    with (software / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    name = (f"adore-web-{version}-{platform.system().lower()}-"
            f"{platform.machine().lower()}-py{sys.version_info.major}{sys.version_info.minor}")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bundle = output / name
    if bundle.exists():
        raise SystemExit(f"bundle already exists: {bundle}")
    bundle.mkdir()
    wheels = bundle / "wheels"
    wheels.mkdir()
    static = software / "adore" / "web" / "static"
    if not (static / "index.html").is_file() or not (static / "LICENSE.txt").is_file():
        raise SystemExit("build UI first: cd 04_Software/web && npm ci && npm run build")
    _run(["uv", "build", "--wheel", "--out-dir", str(wheels), str(software)], repo)
    requirements = subprocess.run(
        ["uv", "export", "--locked", "--extra", "web", "--no-dev", "--no-hashes",
         "--no-emit-project", "--format", "requirements-txt"],
        cwd=software, check=True, capture_output=True, text=True, timeout=1800,
    ).stdout
    (bundle / "requirements.txt").write_text(
        "# Copyright (c) 2026 DDP Engineering\n"
        "# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
        "# Commercial use requires a separate commercial license.\n"
        "# See the LICENSE.txt file for full license details.\n"
        "# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n"
        + requirements, encoding="utf-8",
    )
    _run([sys.executable, "-m", "pip", "download", "--dest", str(wheels),
          "-r", str(bundle / "requirements.txt")], repo)
    images = []
    for index, tag in enumerate(args.image, start=1):
        archive = bundle / f"image-{index}.tar"
        _run([args.runtime, "save", "-o", str(archive), tag], repo)
        images.append({"tag": tag, "archive": archive.name})
    for tag in args.require_image:
        if tag in {item["tag"] for item in images}:
            raise SystemExit(f"image tag listed twice: {tag}")
        images.append({"tag": tag, "archive": None})
    executor_image = args.executor_image or (
        images[0]["tag"] if len(images) == 1 and args.executor != "any" else "")
    if executor_image and executor_image not in {item["tag"] for item in images}:
        raise SystemExit("executor image tag must be listed with --image or --require-image")
    shutil.copy2(repo / "LICENSE.txt", bundle / "LICENSE.txt")
    shutil.copy2(repo / "02_Tools" / "install_web_offline.py", bundle / "install.py")
    shutil.copy2(repo / "02_Tools" / "launch_web.py", bundle / "launch.py")
    manifest = {
        "schema": 1, "adore_version": version, "system": platform.system(),
        "machine": platform.machine(),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "images": images,
        "executor_image_cli": args.executor,
        "executor_image_tag": executor_image,
        "prerequisites": {
            "git": ["git"],
            "forge_cli": ({"gitlab": ["glab"], "github": ["gh"],
                           "gitea": ["tea"]}.get(args.forge, ["glab", "gh", "tea"])),
            "container_runtime": ([args.runtime, "wsl"]
                                  if platform.system() == "Windows"
                                  else [args.runtime]),
        },
        "files": {path.relative_to(bundle).as_posix(): _digest(path)
                  for path in sorted(bundle.rglob("*")) if path.is_file()},
    }
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE
