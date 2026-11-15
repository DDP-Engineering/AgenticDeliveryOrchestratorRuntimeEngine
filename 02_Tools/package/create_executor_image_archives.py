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
@file       create_executor_image_archives.py
@brief      Publish the generic executor image for offline Docker/Podman import.
@details    Builds explicitly on request, with unique source-bound tags, or
            exports selected local images. No registry push or running-container
            mutation occurs. Only final archives and hashes enter 07_Delivery.
"""

# IMPORTS
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib

# CONSTANTS
REPO = Path(__file__).resolve().parents[2]
ROLES = ("executor-base",)
MAX_IMAGE_BYTES = 16 * 1024 * 1024 * 1024
LEGAL = (
    "# Copyright (c) 2026 DDP Engineering\n"
    "# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
    "# Commercial use requires a separate commercial license.\n"
    "# See the LICENSE.txt file for full license details. "
    "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n"
)


# LOCAL HELPERS
def run(argv: list[str], *, timeout: int = 900) -> str:
    """@brief Run a bounded explicit argv without a shell.
    @param[in] argv Command and arguments.
    @param[in] timeout Maximum command duration.
    @return Captured standard output.
    """
    return subprocess.run(argv, cwd=REPO, check=True, stdout=subprocess.PIPE,
                          text=True, timeout=timeout).stdout.strip()


def publish(source: Path, destination: Path) -> None:
    """@brief Publish a complete archive and its streaming SHA-256 on one volume.
    @param[in] source Complete compressed image archive in temporary storage.
    @param[in] destination Final repository-relative delivery path.
    """
    destination.parent.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".tmp", delete=False) as output:
        temporary = Path(output.name)
        try:
            with source.open("rb") as incoming:
                shutil.copyfileobj(incoming, output)
        except BaseException:
            output.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    with destination.open("rb") as incoming:
        digest = hashlib.file_digest(incoming, "sha256").hexdigest()
    destination.with_name(destination.name + ".sha256").write_text(
        LEGAL + f"{digest}  {destination.name}\n", encoding="utf-8", newline="\n")


# PUBLIC API
def main(argv: list[str] | None = None) -> int:
    """@brief Build/export selected Linux x64 images for offline import.
    @param[in] argv Optional runtime, roles and local image overrides.
    @return Zero after complete archives and hashes are published.
    @exception RuntimeError Invalid image metadata or uncommitted build sources.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", choices=("docker", "podman"), default="docker")
    parser.add_argument("--only", choices=ROLES, action="append", help="repeat to select image roles")
    parser.add_argument("--build", action="store_true", help="build from this clean committed checkout")
    parser.add_argument("--build-network", choices=("default", "host", "none"), default="default",
                        help="network used by explicit image builds")
    parser.add_argument("--image", action="append", default=[], metavar="ROLE=LOCAL_TAG",
                        help="export an already built local image for a role")
    args = parser.parse_args(argv)
    if args.build and args.image:
        parser.error("--build and --image are separate build/export operations")
    with (REPO / "04_Software/pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    defaults = {
        "executor-base": "adore-executor-base:1.0.0",
    }
    for value in args.image:
        role, separator, image = value.partition("=")
        if role not in ROLES or not separator or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@-]{0,250}", image):
            parser.error("--image requires a known ROLE and explicit local image reference")
        defaults[role] = image
    selected = list(dict.fromkeys(args.only or ROLES))
    if args.build:
        if run(["git", "status", "--porcelain", "--untracked-files=normal"]):
            raise RuntimeError("commit source changes before building source-bound delivery images")
        revision = run(["git", "rev-parse", "HEAD"])
        for role in selected:
            tag = f"adore-{role}:{version}-{revision[:12]}"
            dockerfile = REPO / f"04_Software/docker/Dockerfile.{role}"
            context = REPO / "04_Software/docker"
            print(f"Building {tag}", flush=True)
            network = [] if args.build_network == "default" else ["--network", args.build_network]
            run([args.runtime, "build", *network, "--platform", "linux/amd64",
                 "--label", f"org.opencontainers.image.revision={revision}",
                 "--file", str(dockerfile), "--tag", tag, str(context)], timeout=1800)
            defaults[role] = tag
    with tempfile.TemporaryDirectory(prefix="adore-image-delivery-") as directory:
        work = Path(directory)
        for role in selected:
            image = defaults[role]
            metadata = json.loads(run([args.runtime, "image", "inspect", image], timeout=30))
            if (not isinstance(metadata, list) or len(metadata) != 1
                    or metadata[0].get("Os") != "linux" or metadata[0].get("Architecture") != "amd64"):
                raise RuntimeError("delivery images must be local Linux amd64 images")
            sys.path.insert(0, str(REPO / "04_Software"))
            from adore.pi_installation import PI_VERSION

            actual = run([args.runtime, "run", "--rm", "--network", "none",
                          "--entrypoint", "node", image,
                          "/opt/pi/lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js",
                          "--version"], timeout=60)
            if actual != PI_VERSION:
                raise RuntimeError("executor image does not contain the current pinned Pi")
            run([args.runtime, "run", "--rm", "--network", "none",
                 "--entrypoint", "test", image, "-s", "/usr/local/LICENSE"], timeout=30)
            for tool in ("fd", "rg"):
                run([args.runtime, "run", "--rm", "--network", "none",
                     "--entrypoint", tool, image, "--version"], timeout=30)
            raw = work / "image.tar"
            save = [args.runtime, "save", "--output", str(raw)]
            if args.runtime == "podman":
                save += ["--format", "docker-archive"]
            run([*save, image], timeout=900)
            if not 0 < raw.stat().st_size <= MAX_IMAGE_BYTES:
                raise RuntimeError("image archive exceeds the 16 GiB export limit")
            name = f"adore-{version}-{role}-linux-x64.tar.gz"
            archive = work / name
            with raw.open("rb") as incoming, archive.open("wb") as output:
                with gzip.GzipFile(fileobj=output, mode="wb", compresslevel=6, mtime=0) as compressed:
                    shutil.copyfileobj(incoming, compressed)
            publish(archive, REPO / "07_Delivery" / name)
            raw.unlink()
            archive.unlink()
            print(f"Created 07_Delivery/{name} from {image}; import with {args.runtime} load --input <archive>", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Image delivery failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

# END OF FILE
