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
@file    verification_hint.py
@brief   Suggest an editable verification command from bounded repository files.
@details Pure, read-only discovery: ordered root matches precede a unique immediate
         child. No command, network, toolchain validation or stored configuration.
"""

from __future__ import annotations

# IMPORTS
import json
import os
from pathlib import Path
import re
import stat

# CONSTANTS
_MAX_BYTES = 1024 * 1024
_CHILD_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]*")
_NPM_PLACEHOLDER = 'echo "Error: no test specified" && exit 1'

# HELPER FUNCTIONS


def _eligible(path: Path, root: Path, *, directory: bool = False) -> Path | None:
    """
    @brief     Resolve evidence inside the clone before inspecting its type/size.
    @param[in] path Candidate file or first-level directory.
    @param[in] root Resolved clone boundary.
    @param[in] directory Whether directory rather than file evidence is required.
    @return    Contained eligible target, or None for absent/ineligible evidence.
    @exception OSError Access failures other than missing evidence propagate.
    """
    target = path.resolve()
    if not target.is_relative_to(root):
        return None
    try:
        info = target.stat()
    except FileNotFoundError:
        return None
    if directory:
        return target if stat.S_ISDIR(info.st_mode) else None
    return target if stat.S_ISREG(info.st_mode) and info.st_size <= _MAX_BYTES else None


def _read(path: Path, root: Path) -> str | None:
    """
    @brief     Read only an eligible manifest, rechecking before bounded access.
    @param[in] path Manifest candidate path.
    @param[in] root Resolved clone boundary.
    @return    UTF-8 contents or None for ineligible evidence.
    @exception OSError, UnicodeError Unreadable evidence is not an empty scan.
    @note      These checks do not promise hostile-filesystem snapshot isolation.
    """
    target = _eligible(path, root)
    if target is None:
        return None
    with target.open("rb") as handle:
        info = os.fstat(handle.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_BYTES
                or _eligible(path, root) != target):
            return None
        data = handle.read(_MAX_BYTES + 1)
    return data.decode("utf-8") if len(data) <= _MAX_BYTES else None


def _scan(directory: Path, root: Path) -> tuple[str, str] | None:
    """
    @brief     Apply the ordered table in one directory without recursive descent.
    @param[in] directory Root or immediate child to inspect.
    @param[in] root Resolved clone boundary, also used for source provenance.
    @return    First eligible command and actual repository-relative source.
    """
    package = directory / "package.json"
    text = _read(package, root)
    if text is not None:
        try:
            document = json.loads(text)
        except json.JSONDecodeError:
            document = None
        scripts = document.get("scripts") if isinstance(document, dict) else None
        test = scripts.get("test") if isinstance(scripts, dict) else None
        if isinstance(test, str) and test.strip() and test.strip() != _NPM_PLACEHOLDER:
            command = "npm test"
            if _eligible(directory / "pnpm-lock.yaml", root):
                command = "pnpm test"
            elif _eligible(directory / "yarn.lock", root):
                command = "yarn test"
            return command, package.relative_to(root).as_posix()

    for name in ("pyproject.toml", "pytest.ini", "tox.ini"):
        path = directory / name
        if _eligible(path, root):
            command = ("uv run pytest -q" if _eligible(directory / "uv.lock", root)
                       else "python -m pytest -q")
            return command, path.relative_to(root).as_posix()

    for name, command in (("go.mod", "go test ./..."), ("Cargo.toml", "cargo test"),
                          ("pom.xml", "mvn -q test")):
        path = directory / name
        if _eligible(path, root):
            return command, path.relative_to(root).as_posix()

    for name in ("build.gradle", "build.gradle.kts"):
        path = directory / name
        if _eligible(path, root):
            command = "./gradlew test" if _eligible(directory / "gradlew", root) else "gradle test"
            return command, path.relative_to(root).as_posix()

    # iterdir rather than glob preserves access errors instead of treating them
    # as an empty directory. Dotnet provenance is pattern-first, then lexical.
    entries = sorted(directory.iterdir())
    for suffix in (".sln", ".csproj"):
        for path in entries:
            if path.name.endswith(suffix) and _eligible(path, root):
                return "dotnet test", path.relative_to(root).as_posix()

    makefile = directory / "Makefile"
    text = _read(makefile, root)
    if text is not None and re.search(r"^ *test[ \t]*:(?!=)", text, re.MULTILINE):
        return "make test", makefile.relative_to(root).as_posix()
    return None

# PUBLIC API


def suggest_verification_command(root: Path) -> tuple[str, str] | None:
    """
    @brief     Read a clone's files to suggest, never run, a verification command.
    @param[in] root Existing clone root; links outside its resolved boundary are ignored.
    @return    (command, forward-slash relative source) or None when no unique match.
    @exception OSError, UnicodeError Filesystem/encoding failures propagate to callers.
    @note      Files over 1 MiB are ignored. Only package.json and Makefile need
               contents. One safe-named matching first-level directory gets a cd
               prefix only after no root match; matching children are counted
               before the portable-name restriction is applied.
    """
    root = root.resolve(strict=True)
    match = _scan(root, root)
    if match is not None:
        return match
    matches: list[tuple[Path, tuple[str, str]]] = []
    for child in root.iterdir():
        if _eligible(child, root, directory=True) is not None:
            match = _scan(child, root)
            if match is not None:
                matches.append((child, match))
                if len(matches) > 1:
                    return None
    if not matches:
        return None
    child, (command, source) = matches[0]
    if _CHILD_NAME.fullmatch(child.name) is None:
        return None
    return f"cd {child.name} && {command}", source

# END OF FILE
