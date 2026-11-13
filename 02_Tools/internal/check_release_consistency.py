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
@file check_release_consistency.py
@brief Fail-closed repository check for the ADORE release identity.
@details Verifies package and lock metadata, canonical runtime/deployment
         resource names, documentation release markers, delivery artifacts,
         and exact forbidden pre-1.0 identity tokens. The project release
         version is a single constant (EXPECTED_VERSION); the executor/proxy
         image tags are versioned independently and are checked as their own
         literal tokens.
"""

from __future__ import annotations

# IMPORTS
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import sys
import tarfile
import tomllib
import zipfile

if __package__:
    from .stamp_web_assets import STAMP, fingerprint
else:
    from stamp_web_assets import STAMP, fingerprint

# CONSTANTS

EXPECTED_NAME = "adore"
EXPECTED_VERSION = "0.15.0"
# The executor base and egress-proxy images are versioned by their own content,
# independently of the project release; they stay at their built tag.
EXPECTED_IMAGE_VERSION = "1.0.0"
EXPECTED_CHANGELOG_HEADING = "## [0.15.0] - 2026-11-13"
EXPECTED_PRODUCT = "Agentic Delivery Orchestrator & Runtime Engine"
EXPECTED_TASK = "ADORE Orchestrator & Runtime Engine"
EXPECTED_RUNTIME_PREFIX = "adore-runtime"
EXPECTED_ARTIFACTS = {
    f"adore-{EXPECTED_VERSION}-windows-x64.zip",
    f"adore-{EXPECTED_VERSION}-linux-x64.tar.gz",
}
TEXT_SUFFIXES = {
    ".bat", ".cfg", ".cmd", ".html", ".ini", ".json", ".md", ".ps1",
    ".py", ".service", ".sh", ".svg", ".toml", ".txt", ".yaml", ".yml",
}
SKIP_DIRS = {".git", ".venv", ".adore", "__pycache__"}


# LOCAL HELPERS

def _read_text(path: Path) -> str:
    """
    @brief      Read a required UTF-8 repository text file.
    @param[in]  path File to read.
    @return     Decoded text.
    @exception OSError File cannot be read.
    @exception UnicodeError File is not valid UTF-8.
    """
    return path.read_text(encoding="utf-8-sig")


def _require_text(root: Path, relative: str, issues: list[str]) -> str:
    """
    @brief      Read a required file and record a deterministic issue on error.
    @param[in]  root Repository root.
    @param[in]  relative Repository-relative path.
    @param[out] issues Accumulated validation issues.
    @return     File text, or an empty string after a recorded failure.
    """
    path = root / relative
    try:
        return _read_text(path)
    except (OSError, UnicodeError) as exc:
        issues.append(f"cannot read required file {relative}: {exc}")
        return ""


def _expect_tokens(
    relative: str,
    text: str,
    expected: tuple[str, ...],
    issues: list[str],
) -> None:
    """
    @brief      Require exact release tokens in a repository surface.
    @param[in]  relative Repository-relative path used in messages.
    @param[in]  text File content.
    @param[in]  expected Required exact tokens.
    @param[out] issues Accumulated validation issues.
    """
    for token in expected:
        if token not in text:
            issues.append(f"{relative}: missing release token {token!r}")


def _legacy_patterns() -> tuple[re.Pattern[str], ...]:
    """
    @brief  Build exact legacy-token patterns without embedding banned tokens
            in the checker source itself.
    @return Compiled case-sensitive patterns.
    """
    old_upper = "AD" + "OR"
    old_lower = old_upper.lower()
    old_product = "Agentic Delivery " + "Orchestrator"
    old_repo = "AgenticDelivery" + "Orchestrator"
    return (
        re.compile(rf"\b{old_upper}\b"),
        re.compile(rf"\b{old_lower}\b"),
        re.compile(rf"{old_upper}_"),
        re.compile(rf"{old_lower}[_-]"),
        re.compile(rf"(?<![A-Za-z0-9])\.{old_lower}(?!e)"),
        re.compile(rf"/{old_lower}(?:/|\b)"),
        re.compile(rf"{re.escape(old_product)}(?! & Runtime Engine)"),
        re.compile(rf"{re.escape(old_repo)}(?!RuntimeEngine)"),
    )


def _is_text_candidate(path: Path) -> bool:
    """
    @brief      Identify repository text surfaces covered by the exact scan.
    @param[in]  path Candidate file path.
    @return     True for supported text/configuration source files.
    """
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {
        ".env.example", ".gitignore",
    }


def _check_legacy_identifiers(root: Path, issues: list[str]) -> None:
    """
    @brief      Reject legacy identity tokens in names and UTF-8 text files.
    @param[in]  root Repository root.
    @param[out] issues Accumulated validation issues.
    """
    patterns = _legacy_patterns()
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        parent = Path(directory)
        parent_relative = parent.relative_to(root)
        dirnames[:] = sorted(
            name for name in dirnames
            if name not in SKIP_DIRS
            and not (parent_relative == Path("07_Delivery")
                     and (name == "_technical" or name.startswith((
                         "web-candidate-", "portable-build-", "portable-check-",
                         "portable-unit-", "portable-python-"))))
        )
        for name in [*dirnames, *sorted(filenames)]:
            path = parent / name
            relative = path.relative_to(root)
            relative_text = relative.as_posix()
            if any(pattern.search(relative_text) for pattern in patterns):
                issues.append(f"legacy identity in path: {relative_text}")
            if path.is_file() and path.suffix.lower() == ".pptx":
                try:
                    with zipfile.ZipFile(path) as presentation:
                        for member in presentation.namelist():
                            if not member.endswith((".xml", ".rels")):
                                continue
                            text = presentation.read(member).decode("utf-8")
                            if any(pattern.search(text) for pattern in patterns):
                                issues.append(
                                    "legacy identity in "
                                    f"{relative_text}:{member}"
                                )
                except (OSError, UnicodeError, zipfile.BadZipFile) as exc:
                    issues.append(f"cannot scan presentation {relative_text}: {exc}")
                continue
            if not path.is_file() or not _is_text_candidate(path):
                continue
            try:
                lines = _read_text(path).splitlines()
            except (OSError, UnicodeError) as exc:
                issues.append(f"cannot scan {relative_text}: {exc}")
                continue
            for line_number, line in enumerate(lines, start=1):
                if any(pattern.search(line) for pattern in patterns):
                    issues.append(
                        f"legacy identity in {relative_text}:{line_number}: {line.strip()}"
                    )


def _check_metadata(root: Path, issues: list[str]) -> None:
    """
    @brief      Validate distribution, package, entry-point, and lock versions.
    @param[in]  root Repository root.
    @param[out] issues Accumulated validation issues.
    """
    pyproject_path = root / "04_Software/pyproject.toml"
    lock_path = root / "04_Software/uv.lock"
    try:
        pyproject = tomllib.loads(_read_text(pyproject_path))
        project = pyproject["project"]
        if project.get("name") != EXPECTED_NAME:
            issues.append(f"pyproject distribution must be {EXPECTED_NAME!r}")
        if project.get("version") != EXPECTED_VERSION:
            issues.append(f"pyproject version must be {EXPECTED_VERSION}")
        scripts = project.get("scripts", {})
        expected_scripts = {
            EXPECTED_NAME: "adore.cli:main",
            "adore-web": "adore.web.server:main",
            "adore-web-worker": "adore.web.commands:main",
        }
        if scripts != expected_scripts:
            issues.append("pyproject has unexpected console commands")
        packages = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
        if packages != [EXPECTED_NAME]:
            issues.append("wheel package selection must contain only adore")
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        issues.append(f"invalid 04_Software/pyproject.toml: {exc}")

    init_text = _require_text(root, "04_Software/adore/__init__.py", issues)
    if f'__version__ = "{EXPECTED_VERSION}"' not in init_text:
        issues.append(f"adore.__version__ does not match {EXPECTED_VERSION}")

    try:
        lock = tomllib.loads(_read_text(lock_path))
        editable = [
            package for package in lock.get("package", [])
            if package.get("source", {}).get("editable") == "."
        ]
        if len(editable) != 1:
            issues.append("uv.lock must contain exactly one editable root package")
        elif (
            editable[0].get("name") != EXPECTED_NAME
            or editable[0].get("version") != EXPECTED_VERSION
        ):
            issues.append(f"uv.lock editable package must be adore {EXPECTED_VERSION}")
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, TypeError) as exc:
        issues.append(f"invalid 04_Software/uv.lock: {exc}")


def _check_release_surfaces(root: Path, issues: list[str]) -> None:
    """
    @brief      Validate canonical image, deployment, package, and doc tokens.
    @param[in]  root Repository root.
    @param[out] issues Accumulated validation issues.
    """
    required = {
        "04_Software/adore/branding.py": (
            f'PRODUCT_NAME = "{EXPECTED_PRODUCT}"',
            'PROFILE_HOME_ENV = "ADORE_HOME"',
            'EXECUTOR_BASE_IMAGE = "adore-executor-base:1.0.0"',
            'EGRESS_PROXY_IMAGE = "adore-egress-proxy:1.0.0"',
            f'WINDOWS_TASK_NAME = "{EXPECTED_TASK}"',
            f'RUNTIME_PACKAGE_PREFIX = "{EXPECTED_RUNTIME_PREFIX}"',
        ),
        "02_Tools/deploy/adore.service": (
            "__ADORE_DIR__", "__ADORE_USER__", ".venv/bin/adore",
            ".adore/adore.lock",
        ),
        "02_Tools/deploy/install-windows.ps1": (
            f'$TaskName    = "{EXPECTED_TASK}"',
            '"adore-executor-base:1.0.0"',
        ),
        "04_Software/docker/README.md": (
            "adore-executor-base:1.0.0", "adore-egress-proxy:1.0.0",
        ),
        "README.md": (f"Current release: **ADORE {EXPECTED_VERSION}**.",),
        "CHANGELOG.md": (EXPECTED_CHANGELOG_HEADING,),
    }
    for relative, tokens in required.items():
        text = _require_text(root, relative, issues)
        _expect_tokens(relative, text, tokens, issues)

    if not (root / "02_Tools/deploy/adore.service").is_file():
        issues.append("missing 02_Tools/deploy/adore.service")
    old_service = "ad" + "or.service"
    if (root / "02_Tools/deploy" / old_service).exists():
        issues.append("pre-1.0 systemd service still exists")
    old_package = "ad" + "or"
    if (root / "04_Software" / old_package).exists():
        issues.append("pre-1.0 Python package still exists")


def _check_artifacts(root: Path, require_artifacts: bool, issues: list[str]) -> None:
    """
    @brief      Validate portable release identities and the minimal delivery layout.
    @param[in]  root Repository root.
    @param[in]  require_artifacts Require both Windows and Linux archives.
    @param[out] issues Accumulated validation issues.
    """
    delivery = root / "07_Delivery"
    present = {path.name for path in delivery.iterdir()} if delivery.is_dir() else set()
    if require_artifacts:
        allowed = EXPECTED_ARTIFACTS | {name + ".sha256" for name in EXPECTED_ARTIFACTS}
        for name in sorted(present - allowed):
            issues.append(f"unexpected delivery entry: {name}; keep only portable archives and optional hashes")
        for name in sorted(EXPECTED_ARTIFACTS - present):
            issues.append(f"required portable artifact missing: {name}")
    for name in sorted(present & EXPECTED_ARTIFACTS):
        _check_portable_artifact(delivery / name, issues)


def _check_portable_artifact(artifact: Path, issues: list[str]) -> None:
    """@brief Check archive release metadata and an optional adjacent SHA-256 file.
    @param[in] artifact Portable Windows ZIP or Linux TAR.GZ.
    @param[out] issues Accumulated validation issues.
    @note Full media verification belongs to the portable launcher's verifier.
    """
    system = "windows" if artifact.suffix == ".zip" else "linux"
    member_name = f"adore-{EXPECTED_VERSION}-{system}-x64/manifest.json"
    try:
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError("archive must be a regular file")
        if system == "windows":
            with zipfile.ZipFile(artifact) as archive:
                member = archive.getinfo(member_name)
                if member.file_size > 8 * 1024 * 1024:
                    raise ValueError("manifest exceeds 8 MiB")
                metadata = json.loads(archive.read(member))
        else:
            with tarfile.open(artifact) as archive:
                member = archive.getmember(member_name)
                if not member.isfile() or member.size > 8 * 1024 * 1024:
                    raise ValueError("manifest must be a regular file of at most 8 MiB")
                with archive.extractfile(member) as stream:
                    metadata = json.load(stream)
        if not isinstance(metadata, dict) or any(
            metadata.get(key) != value for key, value in {
                "schema": 1, "version": EXPECTED_VERSION,
                "system": system, "architecture": "x64",
            }.items()
        ):
            raise ValueError("portable manifest release identity does not match")
        checksum = artifact.with_name(artifact.name + ".sha256")
        if checksum.exists() or checksum.is_symlink():
            if checksum.is_symlink() or checksum.stat().st_size > 4096:
                raise ValueError("checksum must be a regular file of at most 4096 bytes")
            rows = [row for row in _read_text(checksum).splitlines()
                    if row and not row.startswith("#")]
            with artifact.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if rows != [f"{digest}  {artifact.name}"]:
                raise ValueError("adjacent checksum does not match the archive")
    except (OSError, ValueError, KeyError, TypeError, UnicodeError,
            zipfile.BadZipFile, tarfile.TarError) as exc:
        issues.append(f"{artifact.name}: invalid portable artifact: {exc}")


# EXPORTED FUNCTIONS / PUBLIC API

def check_package(artifact: Path) -> list[str]:
    """@brief Validate one portable archive's release identity and optional hash.
    @param[in] artifact Native Windows/Linux archive to inspect without extraction.
    @return Validation issues; empty means matching release metadata and hash.
    """
    issues: list[str] = []
    if artifact.name not in EXPECTED_ARTIFACTS:
        return [f"unexpected portable archive name: {artifact.name}"]
    _check_portable_artifact(artifact, issues)
    return issues


def check_repository(root: Path, *, require_artifacts: bool = False) -> list[str]:
    """
    @brief      Check the complete ADORE release identity contract.
    @param[in]  root Repository root.
    @param[in]  require_artifacts Require both canonical delivery archives.
    @return     Sorted deterministic issue descriptions; empty means success.
    """
    resolved = root.resolve()
    issues: list[str] = []
    static = resolved / "04_Software/adore/web/static"
    bundle_valid = False
    try:
        recorded = json.loads((static / STAMP).read_text(encoding="utf-8"))
        if recorded != fingerprint(resolved, static):
            issues.append("web bundle differs from its build inputs or outputs; run npm run build in 04_Software/web and commit the bundle")
        else:
            bundle_valid = True
    except (OSError, UnicodeError, ValueError) as exc:
        issues.append(f"cannot verify web bundle ({exc}); run npm run build in 04_Software/web and commit the bundle")
    if bundle_valid:
        # Rebuild independently: a manually refreshed fingerprint alone cannot
        # attest that the generated files actually came from the current sources.
        try:
            node = shutil.which("node")
            web = resolved / "04_Software/web"
            vite = web / "node_modules/vite/bin/vite.js"
            if not node or not vite.is_file():
                raise OSError("node and the installed local Vite are required to verify the web bundle")
            with tempfile.TemporaryDirectory(prefix="adore-web-consistency-") as tmp:
                generated = Path(tmp) / "static"
                subprocess.run([node, str(vite), "build", "--outDir", str(generated)],
                               cwd=web, check=True, capture_output=True, timeout=180)
                # Stamp using this checker's companion, with the candidate sources.
                subprocess.run([sys.executable, str(resolved / "02_Tools/internal/stamp_web_assets.py"),
                                "--output", str(generated)], cwd=web, check=True,
                               capture_output=True, timeout=30)
                if fingerprint(resolved, static)["outputs"] != fingerprint(resolved, generated)["outputs"]:
                    issues.append("web bundle differs from a fresh build; run npm run build in 04_Software/web and commit the bundle")
        except (OSError, subprocess.SubprocessError) as exc:
            issues.append(f"cannot rebuild web bundle for verification ({exc}); prepare frontend dependencies and retry")
    _check_metadata(resolved, issues)
    _check_release_surfaces(resolved, issues)
    _check_artifacts(resolved, require_artifacts, issues)
    _check_legacy_identifiers(resolved, issues)
    return sorted(set(issues))


def main(argv: list[str] | None = None) -> int:
    """
    @brief      Run the release check from the command line.
    @param[in]  argv Optional argument vector for tests.
    @return     Zero when consistent; one when any issue is found.
    """
    parser = argparse.ArgumentParser(
        description=f"verify the ADORE {EXPECTED_VERSION} release identity",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root (default: parent of 02_Tools)",
    )
    parser.add_argument(
        "--require-artifacts",
        action="store_true",
        help=f"also require both canonical {EXPECTED_VERSION} delivery archives",
    )
    args = parser.parse_args(argv)
    issues = check_repository(args.repo_root, require_artifacts=args.require_artifacts)
    if issues:
        for issue in issues:
            print(f"error: {issue}", file=sys.stderr)
        return 1
    print(f"ADORE {EXPECTED_VERSION} release identity is consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# END OF FILE
