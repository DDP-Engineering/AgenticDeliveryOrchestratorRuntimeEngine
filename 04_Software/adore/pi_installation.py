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
@file    pi_installation.py
@brief   Install and verify the ADORE-managed native Pi release.
@details Resolve Node from the server account, never the project PATH. Publish
         only a verified candidate, under the release pin, without global npm.
"""

# IMPORTS
from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
import re
import tempfile

from adore.profiles import adore_home
from adore.util import run_command, strict_json_loads

# CONSTANTS
PI_VERSION = "1.4.0"
WEB_VERSION = "0.46.0"
PI_PACKAGE = "@earendil-works/pi-coding-agent"
WEB_PACKAGE = "pi-web-access"
NODE_MINIMUM = (22, 23, 4)
PI_ENV = {"PI_OFFLINE": "1", "PI_TELEMETRY": "0", "PI_SKIP_VERSION_CHECK": "1"}
GUARD = Path(__file__).with_name("executor") / "adore-guard.ts"


class PiInstallationError(RuntimeError):
    """@brief A safe, actionable native Pi prerequisite or installation failure."""

    def __init__(self, reason: str, message: str, exit_code: int | None = None):
        """@brief Retain only the closed reason and measured exit code."""
        super().__init__(message)
        self.reason, self.exit_code = reason, exit_code


@dataclass(frozen=True)
class ManagedPi:
    """@brief Exact native paths derived from the build pin and service account."""

    node: Path
    prefix: Path

    @property
    def cli(self) -> Path:
        """@brief The pinned package's native CLI entrypoint."""
        return self.prefix / "node_modules" / PI_PACKAGE / "dist/bundle/cli.js"

    @property
    def web(self) -> Path:
        """@brief The pinned web extension package folder."""
        return self.prefix / "node_modules" / WEB_PACKAGE


# LOCAL HELPERS


def _node_path() -> Path:
    """@brief Resolve an absolute host Node without current-directory search."""
    override = os.environ.get("ADORE_NODE")
    basename = "node.exe" if os.name == "nt" else "node"
    candidates = ([Path(override)] if override else [
        Path(root) / basename for root in os.get_exec_path() if Path(root).is_absolute()
    ])
    for path in candidates:
        if (path.is_absolute() and (os.name != "nt" or path.suffix.lower() == ".exe")
                and path.is_file() and os.access(path, os.X_OK)):
            return path.resolve(strict=True)
    raise PiInstallationError(
        "node-missing", "Node 22.23.4 or later in the 22.x line is required. "
        "Add Node to the ADORE service PATH or set ADORE_NODE to its absolute executable."
    )


def _linked(path: Path) -> bool:
    """@brief Recognize symlinks and Windows reparse points on the managed tree."""
    return path.is_symlink() or bool(
        getattr(path.lstat(), "st_file_attributes", 0) & 0x400
    )


def _regular(root: Path, path: Path) -> bool:
    """@brief Refuse an aliased or external managed package path."""
    try:
        return (path.is_file() and all(
            not _linked(part) for part in (path, *path.parents)
            if part.is_relative_to(root)
        ) and path.resolve(strict=True).is_relative_to(root.resolve(strict=True)))
    except OSError:
        return False


def _check_packages(pi: ManagedPi) -> None:
    """@brief Check declared package pins and the exact owned entrypoint."""
    for name, pin in ((PI_PACKAGE, PI_VERSION), (WEB_PACKAGE, WEB_VERSION)):
        manifest = pi.prefix / "node_modules" / name / "package.json"
        if not _regular(pi.prefix.parent.parent, manifest):
            raise PiInstallationError(
                "pi-missing", f"Managed Pi {PI_VERSION} is missing or unsafe. "
                "Run 'adore pi install'."
            )
        try:
            if manifest.stat().st_size > 131072:
                raise ValueError
            data = strict_json_loads(manifest.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("name") != name or data.get("version") != pin:
                raise ValueError
        except (OSError, ValueError) as exc:
            raise PiInstallationError(
                "version-invalid", f"Managed Pi package metadata is invalid at {pi.prefix}. "
                "Move that prefix aside and run 'adore pi install'.", 0
            ) from exc
    if not _regular(pi.prefix.parent.parent, pi.cli) or not GUARD.is_file():
        raise PiInstallationError(
            "pi-missing", "Managed Pi entrypoint or ADORE guard is missing. "
            "Check the ADORE installation and run 'adore pi install'."
        )


def _environment(root: Path) -> dict[str, str]:
    """@brief Keep personal npm, Pi and Node configuration out of tool operations."""
    keep = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "TMPDIR",
            "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS"}
    env = {key: value for key, value in os.environ.items() if key.upper() in keep}
    return {**env, **PI_ENV, "HOME": str(root), "USERPROFILE": str(root),
            "APPDATA": str(root), "LOCALAPPDATA": str(root), "XDG_CONFIG_HOME": str(root),
            "XDG_CACHE_HOME": str(root), "PI_CODING_AGENT_DIR": str(root / "agent")}


def _check_node(node: Path, runner, cwd: Path) -> None:
    """@brief Require the supported Node major and minimum known-good Windows version."""
    result = runner([str(node), "--version"], cwd=cwd, env=_environment(cwd), timeout=10)
    match = re.fullmatch(r"v([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})", result.stdout.strip())
    if not result.ok or result.timed_out or match is None:
        raise PiInstallationError("node-invalid", "Node version check failed.", result.exit_code)
    version = tuple(map(int, match.groups()))
    if version[0] != NODE_MINIMUM[0] or version < NODE_MINIMUM:
        raise PiInstallationError(
            "node-incompatible", "Use Node 22.23.4 or later in the 22.x line "
            f"for managed Pi (found {match[0]}).", result.exit_code
        )


def _check_cli(pi: ManagedPi, runner, cwd: Path) -> None:
    """@brief Verify that the exact installed entrypoint reports the build pin."""
    result = runner([str(pi.node), str(pi.cli), "--version"],
                    cwd=cwd, env=_environment(cwd), timeout=15)
    if result.timed_out:
        raise PiInstallationError(
            "timeout", "Managed Pi version check timed out.", result.exit_code
        )
    if not result.ok:
        raise PiInstallationError(
            "executor-exit", f"Managed Pi version check failed (exit {result.exit_code}).",
            result.exit_code
        )
    if result.stdout.strip() != PI_VERSION:
        raise PiInstallationError("version-invalid", "Managed Pi reports the wrong version.", 0)


def _npm_cli(node: Path) -> Path:
    """@brief Find npm JavaScript adjacent to Node or its distro npm installation."""
    for root in (node.parent, node.parent.parent):
        for relative in ("node_modules/npm/bin/npm-cli.js", "lib/node_modules/npm/bin/npm-cli.js",
                         "share/nodejs/npm/bin/npm-cli.js"):
            found = root / relative
            if found.is_file():
                return found.resolve(strict=True)
    raise PiInstallationError("npm-missing", "Install npm for the selected Node distribution.")


# PUBLIC API


def managed_pi() -> ManagedPi:
    """@brief Inspect managed paths without running programs or writing files."""
    pi = ManagedPi(_node_path(), adore_home().resolve() / "tools" / "pi" / PI_VERSION)
    _check_packages(pi)
    return pi


def verify_pi(*, runner=None) -> ManagedPi:
    """@brief Verify compatible Node, pinned files and the CLI without provider access."""
    runner = runner or run_command
    node = _node_path()
    with tempfile.TemporaryDirectory(prefix="adore-pi-check-") as directory:
        cwd = Path(directory)
        _check_node(node, runner, cwd)
        pi = ManagedPi(node, adore_home().resolve() / "tools" / "pi" / PI_VERSION)
        _check_packages(pi)
        _check_cli(pi, runner, cwd)
        return pi


def install_pi(*, progress: Callable[[str], None], runner=None) -> ManagedPi:
    """@brief Install one version using isolated npm and publish only after verification."""
    runner = runner or run_command
    node = _node_path()
    root = adore_home().resolve() / "tools" / "pi"
    pi = ManagedPi(node, root / PI_VERSION)
    try:
        with tempfile.TemporaryDirectory(prefix="adore-pi-install-") as directory:
            cwd = Path(directory)
            progress("Checking Node for managed Pi.")
            _check_node(node, runner, cwd)
            root.parent.parent.mkdir(parents=True, exist_ok=True)
            for directory in (root.parent, root):
                directory.mkdir(exist_ok=True)
                if _linked(directory) or not directory.is_dir():
                    raise PiInstallationError(
                        "permission-denied", "Managed Pi tools path is linked or invalid."
                    )
            if pi.prefix.exists() or pi.prefix.is_symlink():
                _check_packages(pi)
                _check_cli(pi, runner, cwd)
                progress(f"Managed Pi {PI_VERSION} is already verified.")
                return pi
            npm = _npm_cli(node)
            progress(f"Installing Pi {PI_VERSION} and web tools {WEB_VERSION} with npm.")
            with tempfile.TemporaryDirectory(prefix=".install-", dir=root) as staging:
                candidate = ManagedPi(node, Path(staging) / "package")
                candidate.prefix.mkdir()
                result = runner(
                    [str(node), str(npm), "install", "--prefix", str(candidate.prefix),
                     "--global=false", "--ignore-scripts", "--no-audit", "--no-fund",
                     "--userconfig", str(cwd / "user.npmrc"),
                     "--globalconfig", str(cwd / "global.npmrc"),
                     f"--cache={cwd / 'cache'}", f"{PI_PACKAGE}@{PI_VERSION}",
                     f"{WEB_PACKAGE}@{WEB_VERSION}"],
                    cwd=cwd, env=_environment(cwd), timeout=300,
                )
                if not result.ok or result.timed_out:
                    detail = "timed out after 300 seconds" if result.timed_out else (
                        f"failed (exit {result.exit_code}); check npm registry access "
                        "and write permissions for the ADORE service account"
                    )
                    raise PiInstallationError("npm-failed", f"Managed Pi npm install {detail}.")
                progress("Verifying installed Pi before publishing.")
                _check_packages(candidate)
                _check_cli(candidate, runner, cwd)
                candidate.prefix.rename(pi.prefix)
            progress(f"Managed Pi {PI_VERSION} is ready at {pi.prefix}.")
            return pi
    except OSError as exc:
        raise PiInstallationError(
            "permission-denied", f"Could not publish managed Pi at {pi.prefix}. "
            "Check the service account's write permissions or retry after another install finishes."
        ) from exc


# END OF FILE
