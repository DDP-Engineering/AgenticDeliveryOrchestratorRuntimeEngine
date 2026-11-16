#!/usr/bin/env python3
"""Prepare the native executor payload at delivery build time."""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile

NODE_VERSION = "22.23.4"
FD_VERSION = "10.5.1"
RG_VERSION = "15.2.0"
NODE_HASHES = {
    "windows": "cbc74b5e0982c9dbb41525fd8fb5dcd32fbee237863f7829072f4639a1ce5f20",
    "linux": "1805bcd35e6815559bd2eb97db438d3fdb0eb3a5e6a977b7c1badca76337e9ce",
}
SEARCH_HASHES = {
    ("fd", "windows"): "e52306a600e60b7ba92019c81dc753e6ea6665379d005867d38215ffd14cf5c2",
    ("fd", "linux"): "f6c95edb190c241df6fddc815a5bab4051444993ac5d92ddc6eec0e0dc2342c7",
    ("rg", "windows"): "71b2fef860abe467217a538ff31de02f5258807c0129f771846f87bd029aafc5",
    ("rg", "linux"): "33e15bcf1624b25cdd2a55813a47a2f95dbe126268203e76aa6a585d1e7b149c",
}


def download(url: str, destination: Path, digest: str) -> None:
    """
    Download one bounded HTTPS archive and require its pinned SHA-256.
    url: Official release asset.
    destination: Temporary file.
    digest: Required checksum from the upstream release.
    Raises RuntimeError: Oversized or altered download.
    """
    checksum, size = hashlib.sha256(), 0
    with urllib.request.urlopen(url, timeout=120) as source, destination.open("xb") as output:
        while block := source.read(1024 * 1024):
            size += len(block)
            if size > 256 * 1024 * 1024:
                raise RuntimeError("native dependency archive exceeds 256 MiB")
            checksum.update(block)
            output.write(block)
    if checksum.hexdigest() != digest:
        raise RuntimeError("native dependency checksum mismatch: " + destination.name)


def unpack(archive: Path, destination: Path) -> Path:
    """
    Extract a verified single-root archive inside an owned directory.
    archive: Verified ZIP or TAR archive.
    destination: Empty temporary extraction directory.
    Returns: Extracted single root directory.
    Raises RuntimeError: Unsafe member, external link or unexpected layout.
    """
    destination.mkdir()
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as source:
            for item in source.infolist():
                target = destination / item.filename
                if (not target.resolve().is_relative_to(destination.resolve())
                        or "\\" in item.filename
                        or (item.external_attr >> 16) & 0o170000 == 0o120000):
                    raise RuntimeError("unsafe native dependency ZIP member")
            source.extractall(destination)
    else:
        with tarfile.open(archive) as source:
            source.extractall(destination, filter="data")
    roots = list(destination.iterdir())
    if len(roots) != 1 or not roots[0].is_dir() or roots[0].is_symlink():
        raise RuntimeError("native dependency archive must contain one directory")
    for path in roots[0].rglob("*"):
        if path.is_symlink() and not path.resolve(strict=True).is_relative_to(roots[0].resolve()):
            raise RuntimeError("native dependency contains an external link")
    return roots[0]


def dereference_links(root: Path) -> None:
    """
    Replace owned npm executable links with their exact in-tree files.
    root: Isolated installed package prefix.
    Raises RuntimeError: A package link escapes the prefix or targets a directory.
    """
    for directory, folders, files in os.walk(root, followlinks=False):
        for name in [*folders, *files]:
            path = Path(directory) / name
            if not path.is_symlink():
                continue
            target = path.resolve(strict=True)
            if not target.is_relative_to(root.resolve()) or not target.is_file():
                raise RuntimeError("external or directory link in native npm payload")
            data, mode = target.read_bytes(), target.stat().st_mode
            path.unlink()
            path.write_bytes(data)
            path.chmod(mode)


def prepare_native_tools(destination: Path, work: Path, system: str) -> dict:
    """
    Build one host-matched self-contained Node/Pi/search payload.
    destination: Application-owned payload directory inside staging.
    work: Temporary build directory.
    system: windows or linux.
    Returns: Exact bundled tool versions for the delivery manifest.
    Raises RuntimeError: A downloaded tool or installation fails verification.
    """
    from adore.pi_installation import PI_PACKAGE, PI_VERSION, WEB_PACKAGE, WEB_VERSION

    destination.mkdir()
    suffix = "win-x64.zip" if system == "windows" else "linux-x64.tar.xz"
    filename = f"node-v{NODE_VERSION}-{suffix}"
    archive = work / filename
    print(f"Preparing offline Node {NODE_VERSION}, Pi {PI_VERSION} and search tools", flush=True)
    download(f"https://nodejs.org/dist/v{NODE_VERSION}/{filename}", archive, NODE_HASHES[system])
    extracted = unpack(archive, work / "node-extracted")
    node_root = destination / "node"
    shutil.copytree(extracted, node_root, symlinks=False)
    if system == "linux":
        # Copies of upstream npm/npx symlinks break relative module resolution.
        for entry in (extracted / "bin").iterdir():
            if entry.is_symlink():
                relative = os.path.relpath(entry.resolve(strict=True), extracted / "bin")
                # REUSE-IgnoreStart
                wrapper = (
                    "#!/bin/sh\n"
                    "# Copyright (c) 2026 DDP Engineering\n"
                    "# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
                    "# Commercial use requires a separate commercial license.\n"
                    "# See the LICENSE.txt file for full license details. "
                    "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n"
                    'script_dir=$(/usr/bin/dirname -- "$0")\n'
                    f'exec "$script_dir/node" "$script_dir/{relative}" "$@"\n'
                )
                # REUSE-IgnoreEnd
                (node_root / "bin" / entry.name).write_text(wrapper, encoding="utf-8")
                (node_root / "bin" / entry.name).chmod(0o755)
    node = node_root / ("node.exe" if system == "windows" else "bin/node")
    npm = node_root / ("node_modules/npm/bin/npm-cli.js" if system == "windows"
                       else "lib/node_modules/npm/bin/npm-cli.js")
    prefix = destination / "pi"
    home = work / "npm-home"
    home.mkdir()
    keep = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP",
            "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS"}
    env = {key: value for key, value in os.environ.items() if key.upper() in keep}
    env.update(HOME=str(home), USERPROFILE=str(home), APPDATA=str(home),
               LOCALAPPDATA=str(home), XDG_CONFIG_HOME=str(home), XDG_CACHE_HOME=str(home),
               PI_CODING_AGENT_DIR=str(home / "agent"), PI_OFFLINE="1",
               PI_TELEMETRY="0", PI_SKIP_VERSION_CHECK="1")
    result = subprocess.run(
        [str(node), str(npm), "install", "--prefix", str(prefix), "--global=false",
         "--ignore-scripts", "--no-audit", "--no-fund", "--userconfig", str(home / "npmrc"),
         "--globalconfig", str(home / "global-npmrc"), "--cache", str(home / "cache"),
         f"{PI_PACKAGE}@{PI_VERSION}", f"{WEB_PACKAGE}@{WEB_VERSION}"],
        cwd=home, env=env, capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise RuntimeError(f"native Pi package installation failed (exit {result.returncode})")
    dereference_links(prefix)
    # Build-time-only npm bookkeeping names the staging prefix; never deliver it.
    for name in ("package-lock.json", "package.json"):
        (prefix / name).unlink(missing_ok=True)
    (prefix / "node_modules/.package-lock.json").unlink(missing_ok=True)
    bins = destination / "bin"
    bins.mkdir()
    licenses = destination / "licenses"
    licenses.mkdir()
    for command, repo, version, stem in (
        ("fd", "sharkdp/fd", FD_VERSION, f"fd-v{FD_VERSION}"),
        ("rg", "BurntSushi/ripgrep", RG_VERSION, f"ripgrep-{RG_VERSION}"),
    ):
        target = ("x86_64-pc-windows-msvc.zip" if system == "windows"
                  else "x86_64-unknown-linux-musl.tar.gz")
        name = f"{stem}-{target}"
        archive = work / name
        tag = f"v{version}" if command == "fd" else version
        download(f"https://github.com/{repo}/releases/download/{tag}/{name}",
                 archive, SEARCH_HASHES[(command, system)])
        tree = unpack(archive, work / f"{command}-extracted")
        binary = command + (".exe" if system == "windows" else "")
        shutil.copy2(tree / binary, bins / binary)
        (bins / binary).chmod(0o755)
        notices = licenses / command
        notices.mkdir()
        for path in tree.iterdir():
            if path.is_file() and path.name.upper().startswith(("LICENSE", "COPYING", "NOTICE")):
                shutil.copy2(path, notices / path.name)
        if not any(notices.iterdir()):
            raise RuntimeError("missing upstream search-tool license")
        subprocess.run([str(bins / binary), "--version"], check=True, cwd=home,
                       env=env, capture_output=True, timeout=15)
    cli = prefix / "node_modules" / PI_PACKAGE / "dist/bundle/cli.js"
    checked = subprocess.run([str(node), str(cli), "--version"], check=True,
                             capture_output=True, text=True, env=env, cwd=home, timeout=30)
    if checked.stdout.strip() != PI_VERSION:
        raise RuntimeError("bundled Pi does not report the required version")
    return {"node": NODE_VERSION, "pi": PI_VERSION, "web": WEB_VERSION,
            "fd": FD_VERSION, "rg": RG_VERSION}
