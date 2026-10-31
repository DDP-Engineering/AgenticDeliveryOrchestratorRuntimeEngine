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
@file       create_package.py
@brief      Build a native, self-contained ADORE user distribution.
@details    Checks the release, compiles/licenses the frontend, provisions CPython,
            installs locked wheels and writes only an archive/hash to 07_Delivery.
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
import tarfile
import tempfile
import tomllib
import zipfile

# CONSTANTS
REPO = Path(__file__).resolve().parents[1]
PYTHON_VERSION = "3.12.13"
MAX_FILES = 30000
MAX_BYTES = 1024 * 1024 * 1024
USER_DOC_FILES = ("README.md", "Administrator_Guide.md", "Troubleshooting.md")


# PUBLIC API
def copy_user_documentation(destination: Path, *, source: Path | None = None) -> None:
    """@brief Copy only the curated end-user guides into a portable distribution.
    @param[in] destination Documentation directory inside the staged package.
    @param[in] source Guide source directory; defaults to repository user documentation.
    @exception RuntimeError A required guide is missing or linked.
    @note Additional source files are ignored; internal material never joins by default.
    """
    source = source or REPO / "01_Documentation/User_Guide"
    guides = [source / name for name in USER_DOC_FILES]
    if source.is_symlink() or not source.is_dir() or any(
        path.is_symlink() or not path.is_file() for path in guides
    ):
        raise RuntimeError("required portable user guide missing or linked")
    destination.mkdir()
    for path in guides:
        shutil.copy2(path, destination / path.name)


def run(argv: list[str], cwd: Path) -> str:
    """@brief Run a build command with a thirty-minute upper bound.
    @param[in] argv Build command and argument vector.
    @param[in] cwd Working directory.
    @return Captured standard output.
    @exception subprocess.SubprocessError The command fails or exceeds its limit.
    """
    result = subprocess.run(argv, cwd=cwd, check=True, text=True,
                            stdout=subprocess.PIPE, timeout=1800)
    return result.stdout


def main(argv: list[str] | None = None) -> int:
    """@brief Build one host-matched ZIP or TAR.GZ without changing host Python.
    @param[in] argv Optional command arguments.
    @return Zero after verification and complete archive publication.
    @exception RuntimeError Runtime layout or resource limits are invalid.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    system = platform.system().lower()
    if system not in {"windows", "linux"} or platform.machine().lower() not in {"amd64", "x86_64"}:
        parser.error("build on native Windows or Linux x64")
    output = (REPO / "07_Delivery").resolve()
    uv = shutil.which("uv")
    if not uv:
        parser.error("uv is required on the build host")
    software = REPO / "04_Software"
    npm = shutil.which("npm")
    if not npm:
        parser.error("prepare the repository first: python 02_Tools/setup_environment.py")
    for checker in ("check_release_notes.py", "check_release_consistency.py"):
        print(run([sys.executable, str(REPO / "02_Tools/internal" / checker)], REPO).strip())
    subprocess.run([npm, "run", "build"], cwd=software / "web", check=True, timeout=1800)
    with (software / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    static = software / "adore/web/static"
    if not (static / "index.html").is_file() or not (static / "LICENSE.txt").is_file():
        parser.error("build the web assets first (04_Software/web: npm ci; npm run build)")
    output.mkdir(parents=True, exist_ok=True)
    name = f"adore-{version}-{system}-x64"
    suffix = ".zip" if system == "windows" else ".tar.gz"
    archive = output / (name + suffix)
    with tempfile.TemporaryDirectory(prefix="adore-portable-") as temporary:
        work = Path(temporary)
        bundle = work / name
        bundle.mkdir()
        managed = work / "managed"
        print(f"Preparing CPython {PYTHON_VERSION} for {system}/x64", flush=True)
        run([uv, "python", "install", PYTHON_VERSION, "--install-dir", str(managed),
             "--no-bin", "--no-registry", "--no-progress"], REPO)
        roots = sorted({path.resolve() for path in managed.glob("cpython-*") if path.is_dir()})
        if len(roots) != 1:
            raise RuntimeError("expected exactly one managed CPython distribution")
        runtime = bundle / "python"
        shutil.copytree(roots[0], runtime, symlinks=False,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo",
                                                     "test", "tests", "idlelib", "turtledemo",
                                                     "tkinter", "tcl", "include"))
        interpreter = runtime / ("python.exe" if system == "windows" else "bin/python3.12")
        wheels = work / "wheels"
        run([uv, "build", "--wheel", "--python", str(interpreter),
             "--out-dir", str(wheels), str(software)], REPO)
        requirements = work / "requirements.txt"
        requirements.write_text(run([
            uv, "export", "--frozen", "--extra", "web", "--no-dev", "--no-hashes",
            "--no-emit-project", "--format", "requirements-txt",
        ], software), encoding="utf-8")
        wheel, = wheels.glob("adore-*.whl")
        run([uv, "pip", "install", "--python", str(interpreter), "--system",
             "--break-system-packages",
             "--no-deps", "--no-build", "--link-mode", "copy",
             "-r", str(requirements), str(wheel)], REPO)
        # Console-script shebangs point into build staging. Public wrappers use -m.
        scripts = runtime / ("Scripts" if system == "windows" else "bin")
        if scripts.exists():
            for entry in scripts.iterdir():
                if system == "linux" and re.fullmatch(r"python(?:3(?:\.12)?)?", entry.name):
                    continue
                if entry.is_dir():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()
        for metadata in runtime.rglob("direct_url.json"):
            metadata.unlink()
        site_packages = Path(run([str(interpreter), "-I", "-B", "-c",
                                  'import sysconfig; print(sysconfig.get_path("purelib"))'],
                                 bundle).strip())
        if not site_packages.resolve().is_relative_to(runtime.resolve()):
            raise RuntimeError("bundled Python site-packages escaped its runtime")
        shutil.copy2(REPO / "02_Tools/portable/adore_portable.pth",
                     site_packages / "adore_portable.pth")
        for cache in list(runtime.rglob("__pycache__")):
            shutil.rmtree(cache)
        for cache in list(runtime.rglob("*.pyc")) + list(runtime.rglob("*.pyo")):
            cache.unlink()
        # Python loads a few bootstrap modules before processing .pth files.
        # Stable hash-based caches keep even isolated child startup read-only
        # after ZIP/TAR timestamps change, with no build-path code filenames.
        run([str(interpreter), "-I", "-B", "-m", "compileall", "-q",
             "--invalidation-mode", "unchecked-hash", "-s", str(runtime), str(runtime)], bundle)
        for source in (REPO / "02_Tools/portable").iterdir():
            if (source.is_file() and source.suffix != ".pth"
                    and (system == "windows" or source.suffix != ".cmd")):
                if system == "windows" and source.suffix == ".sh":
                    continue
                shutil.copy2(source, bundle / source.name)
                if source.suffix == ".sh":
                    (bundle / source.name).chmod(0o755)
        shutil.copy2(REPO / "LICENSE.txt", bundle / "LICENSE.txt")
        copy_user_documentation(bundle / "Documentation")
        files = sorted(path for path in bundle.rglob("*") if path.is_file())
        if len(files) > MAX_FILES or sum(path.stat().st_size for path in files) > MAX_BYTES:
            raise RuntimeError("portable distribution exceeds the 30000-file / 1 GiB build limit")
        manifest = {
            "schema": 1, "version": version, "system": system, "architecture": "x64",
            "python_version": PYTHON_VERSION,
            "python_source": "https://github.com/astral-sh/python-build-standalone",
            "lock_sha256": hashlib.sha256((software / "uv.lock").read_bytes()).hexdigest(),
            "files": {path.relative_to(bundle).as_posix():
                      hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in files},
        }
        (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                              encoding="utf-8")
        run([str(interpreter), "-I", "-B", str(bundle / "launch.py"), "--verify"], bundle)
        staged = work / archive.name
        if system == "windows":
            with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_DEFLATED) as handle:
                for path in sorted(bundle.rglob("*")):
                    if path.is_file():
                        handle.write(path, path.relative_to(work).as_posix())
        else:
            with tarfile.open(staged, "w:gz") as handle:
                handle.add(bundle, arcname=name)
        # The native build workspace may be on another volume (notably WSL).
        # Publish via a complete temporary file on the delivery volume.
        with tempfile.NamedTemporaryFile(prefix=archive.name + ".", suffix=".tmp",
                                         dir=output, delete=False) as destination:
            publication = Path(destination.name)
            try:
                with staged.open("rb") as source:
                    shutil.copyfileobj(source, destination)
            except BaseException:
                destination.close()
                publication.unlink(missing_ok=True)
                raise
        try:
            os.replace(publication, archive)
        finally:
            publication.unlink(missing_ok=True)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + ".sha256").write_text(
        "# Copyright (c) 2026 DDP Engineering\n"
        "# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
        "# Commercial use requires a separate commercial license.\n"
        "# See the LICENSE.txt file for full license details. "
        "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n"
        f"{digest}  {archive.name}\n", encoding="utf-8", newline="\n")
    print(f"Created {archive.relative_to(REPO)} ({archive.stat().st_size:,} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"Packaging failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

# END OF FILE
