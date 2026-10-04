#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file config.py
@brief CodeGraph settings from `.agentic/aegis.toml` and the database rule.
@details CodeGraph reads the same configuration file as AEGIS: `[layout]` for
         the source and test patterns and `[codegraph]` for its own settings.
         The database must be a `NAME.sqlite` file directly inside the
         repository's `.agentic/knowledge/codegraph/` folder after following
         links; that folder is the only one CodeGraph writes, the one Git
         ignores and the one the writer lock protects.
"""

# IMPORTS

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import tomllib

# CONSTANTS

STORAGE = Path(".agentic") / "knowledge" / "codegraph"
DEFAULT_DATABASE = ".agentic/knowledge/codegraph/codegraph.sqlite"
LOCK_NAME = "codegraph.lock"
DATABASE_NAME_RE = re.compile(r"[A-Za-z0-9_-]+\.sqlite")
DATABASE_RULE = ("[codegraph] database must be a NAME.sqlite file directly "
                 "inside .agentic/knowledge/codegraph/ (NAME: letters, digits, _ and -)")
#: revision of the built-in selection rules; part of the ingestion digest
SELECTION_REVISION = 1

# DATA MODELS / TYPEDEFINITIONS


class ConfigError(Exception):
    """A configuration problem, reported as one line."""


@dataclass
class Settings:
    """Resolved CodeGraph settings for one repository root."""

    root: Path
    config_path: Path
    database: Path
    source: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    include_untracked: bool = True
    index_tests: bool = True
    python_import_roots: list[str] = field(default_factory=list)
    max_file_bytes: int = 1048576
    parse_timeout_seconds: int = 10
    max_results: int = 20
    max_output_bytes: int = 8192

    @property
    def storage(self) -> Path:
        """@brief The folder that holds the database, its lock and temporaries."""
        return self.database.parent

# HELPER FUNCTIONS


def _str_list(value: object) -> list[str]:
    """@brief A layout value as a list of strings, tolerating a scalar (as AEGIS does)."""
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)] if value else []


def _strings(table: dict, key: str) -> list[str]:
    """@brief A `[codegraph]` list-of-strings value, or a ConfigError."""
    value = table.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"[codegraph] {key} must be a list of strings")
    return list(value)


def _flag(table: dict, key: str, default: bool) -> bool:
    """@brief A `[codegraph]` boolean, or a ConfigError."""
    value = table.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"[codegraph] {key} must be true or false")
    return value


def _integer(table: dict, key: str, default: int, low: int, high: int | None) -> int:
    """@brief A bounded `[codegraph]` integer, or a ConfigError."""
    value = table.get(key, default)
    upper = "" if high is None else f" and at most {high}"
    if (isinstance(value, bool) or not isinstance(value, int) or value < low
            or (high is not None and value > high)):
        raise ConfigError(f"[codegraph] {key} must be an integer of at least {low}{upper}")
    return value

# PUBLIC API


def resolve_database(root: Path, value: str) -> Path:
    """
    @brief Resolve and confine the database path.
    @param[in] root Repository root.
    @param[in] value Configured or command-line path, relative to the root or
               absolute.
    @return The resolved database path.
    @exception ConfigError when the path is not a `NAME.sqlite` file directly
               inside the repository's storage folder after following links.
    """
    storage = root.resolve() / STORAGE
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if (not DATABASE_NAME_RE.fullmatch(candidate.name)
            or not DATABASE_NAME_RE.fullmatch(resolved.name)
            or resolved.parent != storage
            or storage.parent.resolve() / storage.name != storage.resolve()):
        raise ConfigError(DATABASE_RULE)
    return resolved


def load(root: Path, config_path: Path | None = None,
         database: str | None = None) -> Settings:
    """
    @brief Read and validate the settings for one repository.
    @param[in] root Repository root.
    @param[in] config_path Configuration file; `<root>/.agentic/aegis.toml`.
    @param[in] database Database path overriding `[codegraph] database`.
    @return The validated settings.
    @exception ConfigError for unreadable TOML or an invalid setting.
    """
    path = config_path or root / ".agentic" / "aegis.toml"
    data: dict = {}
    if path.is_file():
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
            raise ConfigError(f"{path.name} is not valid TOML: {exc}") from None
    layout = data.get("layout") if isinstance(data.get("layout"), dict) else {}
    table = data.get("codegraph") if isinstance(data.get("codegraph"), dict) else {}
    configured = table.get("database", DEFAULT_DATABASE)
    if not isinstance(configured, str):
        raise ConfigError(DATABASE_RULE)
    return Settings(
        root=root.resolve(),
        config_path=path,
        database=resolve_database(root, database or configured),
        source=_str_list(layout.get("source")),
        tests=_str_list(layout.get("tests")),
        include=_strings(table, "include"),
        exclude=_strings(table, "exclude"),
        include_untracked=_flag(table, "include_untracked", True),
        index_tests=_flag(table, "index_tests", True),
        python_import_roots=_strings(table, "python_import_roots"),
        max_file_bytes=_integer(table, "max_file_bytes", 1048576, 1, None),
        parse_timeout_seconds=_integer(table, "parse_timeout_seconds", 10, 1, None),
        max_results=_integer(table, "max_results", 20, 1, 200),
        max_output_bytes=_integer(table, "max_output_bytes", 8192, 512, 32768),
    )


def ingestion_digest(settings: Settings) -> str:
    """
    @brief A digest of the settings that change what gets indexed.
    @details Result limits and time limits are left out: changing them never
             requires re-indexing.
    """
    relevant = {
        "source": settings.source, "tests": settings.tests,
        "include": settings.include, "exclude": settings.exclude,
        "include_untracked": settings.include_untracked,
        "index_tests": settings.index_tests,
        "python_import_roots": settings.python_import_roots,
        "max_file_bytes": settings.max_file_bytes,
        "selection_revision": SELECTION_REVISION,
    }
    return hashlib.sha256(json.dumps(relevant, sort_keys=True).encode()).hexdigest()

# END OF FILE
