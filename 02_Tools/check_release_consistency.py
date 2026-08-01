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
from pathlib import Path
import re
import sys
import tarfile
import tomllib
import zipfile

# CONSTANTS

EXPECTED_NAME = "adore"
EXPECTED_VERSION = "1.2.0"
# The executor base and egress-proxy images are versioned by their own content,
# independently of the project release; they stay at their built tag.
EXPECTED_IMAGE_VERSION = "1.0.0"
EXPECTED_CHANGELOG_HEADING = "## [1.2.0] - 2026-07-25"
EXPECTED_PRODUCT = "Agentic Delivery Orchestrator & Runtime Engine"
EXPECTED_TASK = "ADORE Orchestrator & Runtime Engine"
EXPECTED_RUNTIME_PREFIX = "adore-runtime"
EXPECTED_ARTIFACTS = {
    f"{EXPECTED_RUNTIME_PREFIX}-{EXPECTED_VERSION}.zip",
    f"{EXPECTED_RUNTIME_PREFIX}-{EXPECTED_VERSION}.tar.gz",
}
EXPECTED_BUNDLE_DIR = f"{EXPECTED_RUNTIME_PREFIX}-{EXPECTED_VERSION}"
REQUIRED_BUNDLE_FILES = frozenset({
    ".env.example",
    "README.md",
    "README_PACKAGED.md",
    "config.example.toml",
    "pyproject.toml",
    "uv.lock",
    "adore/__init__.py",
    "adore/branding.py",
    "deploy/adore.service",
    "docker/Dockerfile.executor-base",
    "Documentation/README.md",
    "Documentation/CLI_Reference.md",
    "Documentation/Getting_Started.md",
    "Documentation/Security_And_Credentials.md",
})
FORBIDDEN_BUNDLE_PARTS = frozenset({
    ".adore", ".venv", "__pycache__", "tests", "worktrees",
})
ALLOWED_HISTORY_PATH = Path("00_Planning/Onboarding_Wizards_Analysis_And_Proposal.md")
ALLOWED_HISTORY_LINE = (
    "> Historical note: this repository was renamed from Agentic Delivery "
    "Orchestrator (AD" + "OR) to ADORE for the 1.0.0 hard cut."
)
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
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
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
            if relative == ALLOWED_HISTORY_PATH and line == ALLOWED_HISTORY_LINE:
                continue
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
        if scripts != {EXPECTED_NAME: "adore.cli:main"}:
            issues.append("pyproject must expose only the adore console command")
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
        "04_Software/deploy/adore.service": (
            "__ADORE_DIR__", "__ADORE_USER__", ".venv/bin/adore",
            ".adore/adore.lock",
        ),
        "04_Software/deploy/install-windows.ps1": (
            f'$TaskName    = "{EXPECTED_TASK}"',
            '"adore-executor-base:1.0.0"',
        ),
        "04_Software/docker/README.md": (
            "adore-executor-base:1.0.0", "adore-egress-proxy:1.0.0",
        ),
        "02_Tools/package_runtime.ps1": (f'"{EXPECTED_RUNTIME_PREFIX}-$version"',),
        "02_Tools/package_runtime.sh": (f'"{EXPECTED_RUNTIME_PREFIX}-${{VERSION}}"',),
        "README.md": (f"Current release: **ADORE {EXPECTED_VERSION}**.",),
        "CHANGELOG.md": (EXPECTED_CHANGELOG_HEADING,),
        "07_Delivery/README.md": (
            f"{EXPECTED_RUNTIME_PREFIX}-{EXPECTED_VERSION}.zip",
            f"{EXPECTED_RUNTIME_PREFIX}-{EXPECTED_VERSION}.tar.gz",
            "Documentation/",
        ),
    }
    for relative, tokens in required.items():
        text = _require_text(root, relative, issues)
        _expect_tokens(relative, text, tokens, issues)

    if not (root / "04_Software/deploy/adore.service").is_file():
        issues.append("missing 04_Software/deploy/adore.service")
    old_service = "ad" + "or.service"
    if (root / "04_Software/deploy" / old_service).exists():
        issues.append("pre-1.0 systemd service still exists")
    old_package = "ad" + "or"
    if (root / "04_Software" / old_package).exists():
        issues.append("pre-1.0 Python package still exists")


def _check_artifacts(root: Path, require_artifacts: bool, issues: list[str]) -> None:
    """
    @brief      Validate runtime delivery artifact names and release versions.
    @param[in]  root Repository root.
    @param[in]  require_artifacts Require both Windows and Linux archives.
    @param[out] issues Accumulated validation issues.
    """
    delivery = root / "07_Delivery"
    present = {
        path.name for path in delivery.glob(f"{EXPECTED_RUNTIME_PREFIX}-*")
        if path.is_file()
    }
    for name in sorted(present - EXPECTED_ARTIFACTS):
        issues.append(f"runtime artifact has wrong release identity: {name}")
    if require_artifacts:
        for name in sorted(EXPECTED_ARTIFACTS - present):
            issues.append(f"required runtime artifact missing: {name}")
    for name in sorted(present & EXPECTED_ARTIFACTS):
        _check_runtime_artifact(delivery / name, issues)


def _normalise_bundle_member(
    artifact: Path,
    name: str,
    issues: list[str],
) -> str | None:
    """
    @brief      Validate an archive member and strip its bundle root directory.
    @param[in]  artifact Runtime archive being inspected.
    @param[in]  name Raw archive member name.
    @param[out] issues Accumulated validation issues.
    @return     Bundle-relative member path, or None for its root directory.
    """
    if "\\" in name or name.startswith("/"):
        issues.append(f"{artifact.name}: unsafe archive member path {name!r}")
        return None
    normalized = name.rstrip("/")
    if normalized == EXPECTED_BUNDLE_DIR:
        return None
    prefix = f"{EXPECTED_BUNDLE_DIR}/"
    if not normalized.startswith(prefix):
        issues.append(
            f"{artifact.name}: member is outside {EXPECTED_BUNDLE_DIR}/: {name}"
        )
        return None
    relative = normalized.removeprefix(prefix)
    if not relative or any(part in {"", ".", ".."} for part in relative.split("/")):
        issues.append(f"{artifact.name}: unsafe archive member path {name!r}")
        return None
    return relative


def _read_archive_members(artifact: Path, issues: list[str]) -> dict[str, bytes]:
    """
    @brief      Read regular archive members under the canonical bundle root.
    @param[in]  artifact ZIP or tar.gz runtime artifact.
    @param[out] issues Accumulated validation issues.
    @return     Mapping of bundle-relative regular-file paths to their bytes.
    """
    files: dict[str, bytes] = {}

    def add_member(name: str, data: bytes) -> None:
        relative = _normalise_bundle_member(artifact, name, issues)
        if relative is None:
            return
        if relative in files:
            issues.append(f"{artifact.name}: duplicate archive member {relative}")
            return
        files[relative] = data

    try:
        if artifact.suffix == ".zip":
            with zipfile.ZipFile(artifact) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        _normalise_bundle_member(artifact, member.filename, issues)
                        continue
                    add_member(member.filename, archive.read(member))
        else:
            with tarfile.open(artifact, "r:gz") as archive:
                for member in archive.getmembers():
                    if member.issym() or member.islnk():
                        issues.append(
                            f"{artifact.name}: links are forbidden in runtime bundles: "
                            f"{member.name}"
                        )
                        continue
                    if member.isdir():
                        _normalise_bundle_member(artifact, member.name, issues)
                        continue
                    if not member.isfile():
                        issues.append(
                            f"{artifact.name}: unsupported archive member {member.name}"
                        )
                        continue
                    source = archive.extractfile(member)
                    if source is None:
                        issues.append(f"{artifact.name}: cannot read member {member.name}")
                        continue
                    add_member(member.name, source.read())
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
        issues.append(f"cannot inspect runtime artifact {artifact.name}: {exc}")
    return files


def _check_bundle_metadata(
    artifact: Path,
    files: dict[str, bytes],
    issues: list[str],
) -> None:
    """
    @brief      Confirm embedded package, lock, and operator-doc metadata.
    @param[in]  artifact Runtime archive being inspected.
    @param[in]  files Bundle-relative regular-file bytes.
    @param[out] issues Accumulated validation issues.
    """
    try:
        pyproject = tomllib.loads(files["pyproject.toml"].decode("utf-8-sig"))
        project = pyproject["project"]
        if project.get("name") != EXPECTED_NAME or project.get("version") != EXPECTED_VERSION:
            issues.append(
                f"{artifact.name}: embedded pyproject metadata is not adore {EXPECTED_VERSION}"
            )
        if project.get("scripts") != {EXPECTED_NAME: "adore.cli:main"}:
            issues.append(f"{artifact.name}: embedded pyproject console command is wrong")
    except (KeyError, TypeError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        issues.append(f"{artifact.name}: invalid embedded pyproject.toml: {exc}")

    try:
        lock = tomllib.loads(files["uv.lock"].decode("utf-8-sig"))
        editable = [
            package for package in lock.get("package", [])
            if package.get("source", {}).get("editable") == "."
        ]
        if len(editable) != 1 or (
            editable[0].get("name") != EXPECTED_NAME
            or editable[0].get("version") != EXPECTED_VERSION
        ):
            issues.append(
                f"{artifact.name}: embedded uv.lock root package is not adore {EXPECTED_VERSION}"
            )
    except (TypeError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        issues.append(f"{artifact.name}: invalid embedded uv.lock: {exc}")

    try:
        init_text = files["adore/__init__.py"].decode("utf-8-sig")
        if f'__version__ = "{EXPECTED_VERSION}"' not in init_text:
            issues.append(f"{artifact.name}: embedded adore.__version__ is wrong")
        runtime_readme = files["README.md"].decode("utf-8-sig")
        _expect_tokens(
            f"{artifact.name}:README.md",
            runtime_readme,
            ("Documentation/Integrating_A_Runtime_Project.md",),
            issues,
        )
        if "../01_Documentation/" in runtime_readme:
            issues.append(f"{artifact.name}: README.md has an unpackable documentation link")
        packaged_readme = files["README_PACKAGED.md"].decode("utf-8-sig")
        _expect_tokens(
            f"{artifact.name}:README_PACKAGED.md",
            packaged_readme,
            (
                f"Version: {EXPECTED_VERSION}",
                "[Documentation](Documentation/README.md)",
                "Authenticate `glab` or `gh` on the host",
                "`[executor].env_keys`",
            ),
            issues,
        )
        documentation_index = files["Documentation/README.md"].decode("utf-8-sig")
        _expect_tokens(
            f"{artifact.name}:Documentation/README.md",
            documentation_index,
            ("# ADORE Documentation", "Security_And_Credentials.md"),
            issues,
        )
    except (KeyError, UnicodeError) as exc:
        issues.append(f"{artifact.name}: invalid embedded runtime metadata: {exc}")


def _check_runtime_artifact(artifact: Path, issues: list[str]) -> None:
    """
    @brief      Validate layout, exclusions, identity, and metadata in an archive.
    @param[in]  artifact Canonically named runtime ZIP or tar.gz archive.
    @param[out] issues Accumulated validation issues.
    """
    files = _read_archive_members(artifact, issues)
    missing = REQUIRED_BUNDLE_FILES - files.keys()
    for relative in sorted(missing):
        issues.append(f"{artifact.name}: missing required bundle file {relative}")
    for relative in sorted(files):
        parts = relative.split("/")
        name = parts[-1]
        if name in {".env", "config.toml"} or any(
            part in FORBIDDEN_BUNDLE_PARTS for part in parts
        ) or name.endswith((".pyc", ".pyo")):
            issues.append(f"{artifact.name}: forbidden bundle member {relative}")
        if _is_text_candidate(Path(relative)):
            try:
                text = files[relative].decode("utf-8-sig")
            except UnicodeError as exc:
                issues.append(f"{artifact.name}: cannot decode {relative}: {exc}")
                continue
            if any(pattern.search(line) for pattern in _legacy_patterns() for line in text.splitlines()):
                issues.append(f"{artifact.name}: legacy identity in bundle file {relative}")
    if not missing:
        _check_bundle_metadata(artifact, files, issues)


# EXPORTED FUNCTIONS / PUBLIC API

def check_repository(root: Path, *, require_artifacts: bool = False) -> list[str]:
    """
    @brief      Check the complete ADORE release identity contract.
    @param[in]  root Repository root.
    @param[in]  require_artifacts Require both canonical delivery archives.
    @return     Sorted deterministic issue descriptions; empty means success.
    """
    resolved = root.resolve()
    issues: list[str] = []
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
        default=Path(__file__).resolve().parents[1],
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
