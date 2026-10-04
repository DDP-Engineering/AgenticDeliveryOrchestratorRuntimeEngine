#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file store.py
@brief The CodeGraph SQLite database: schema, ownership marker and connections.
@details A CodeGraph database carries application ID 0x43474731 in its SQLite
         header and schema version 1 in `user_version`. Readers open it through
         a read-only URI with `query_only` and a short busy timeout, never
         create it, and let SQLite classify its state: a hot journal a
         read-only connection cannot roll back is `needs_recovery`, a lock
         held past the busy timeout is `busy`, and anything that is not a
         CodeGraph database of this schema is `incompatible`. Journal files
         are never inspected or removed here.
"""

# IMPORTS

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

# CONSTANTS

APPLICATION_ID = 0x43474731
SCHEMA_VERSION = 1
SQLITE_HEADER = b"SQLite format 3\x00"
READER_BUSY_SECONDS = 0.2
WRITER_BUSY_SECONDS = 5.0
#: names whose kinds can be offered as candidate targets
CANDIDATE_KINDS = ("function", "method", "class")

SCHEMA = (
    "CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    ("CREATE TABLE files(id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, role TEXT NOT NULL,"
     " language TEXT NOT NULL, sha256 TEXT, size INTEGER NOT NULL, status TEXT NOT NULL,"
     " reason TEXT, extractor TEXT, module TEXT)"),
    "CREATE TABLE manifests(path TEXT PRIMARY KEY, sha256 TEXT NOT NULL)",
    ("CREATE TABLE symbols(rowid INTEGER PRIMARY KEY, id TEXT NOT NULL UNIQUE,"
     " file_id INTEGER NOT NULL, parent_id TEXT, kind TEXT NOT NULL, name TEXT NOT NULL,"
     " qualified_name TEXT NOT NULL, signature TEXT NOT NULL, start_line INTEGER NOT NULL,"
     " start_column INTEGER NOT NULL, end_line INTEGER NOT NULL, end_column INTEGER NOT NULL,"
     " depth INTEGER NOT NULL, words TEXT NOT NULL)"),
    ("CREATE TABLE refs(rowid INTEGER PRIMARY KEY, file_id INTEGER NOT NULL, from_id TEXT,"
     " kind TEXT NOT NULL, spelling TEXT NOT NULL, line INTEGER NOT NULL,"
     " column INTEGER NOT NULL, binding TEXT NOT NULL, local_target TEXT, qualname TEXT,"
     " label TEXT, target_id TEXT)"),
    ("CREATE TABLE candidates(ref_rowid INTEGER NOT NULL, symbol_id TEXT NOT NULL,"
     " rank INTEGER NOT NULL)"),
    "CREATE INDEX symbols_name ON symbols(name)",
    "CREATE INDEX symbols_qualified ON symbols(qualified_name)",
    "CREATE INDEX symbols_file ON symbols(file_id)",
    "CREATE INDEX refs_file ON refs(file_id)",
    "CREATE INDEX refs_target ON refs(target_id)",
    "CREATE INDEX candidates_symbol ON candidates(symbol_id)",
    "CREATE INDEX candidates_ref ON candidates(ref_rowid)",
)

# PUBLIC API


def header_kind(path: Path) -> str:
    """
    @brief Classify a database path from its first 100 bytes only.
    @return `missing`, `codegraph` (SQLite with the CodeGraph application ID)
            or `foreign` (anything else, including damaged headers).
    """
    if not path.exists():
        return "missing"
    try:
        with path.open("rb") as handle:
            header = handle.read(100)
    except OSError:
        return "foreign"
    if len(header) < 100 or not header.startswith(SQLITE_HEADER):
        return "foreign"
    return "codegraph" if int.from_bytes(header[68:72], "big") == APPLICATION_ID else "foreign"


def identifier_words(name: str) -> str:
    """@brief Lower-case identifier words of a name, space-separated."""
    words: list[str] = []
    for part in name.split("_"):
        words += [word.lower() for word in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z0-9]+", part)]
    return " ".join(word for word in words if word)


def open_reader(path: Path) -> tuple[sqlite3.Connection | None, str]:
    """
    @brief Open the database for reading without ever creating or repairing it.
    @return (connection, `ready`) or (None, `missing`, `incompatible`, `busy`
            or `needs_recovery`).
    """
    kind = header_kind(path)
    if kind == "missing":
        return None, "missing"
    if kind == "foreign":
        return None, "incompatible"
    conn = None
    try:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True,
                               timeout=READER_BUSY_SECONDS)
        conn.execute("PRAGMA query_only=1")
        if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            conn.close()
            return None, "incompatible"
        conn.execute("SELECT count(*) FROM meta").fetchone()
        return conn, "ready"
    except sqlite3.Error as exc:
        if conn is not None:
            conn.close()
        return None, classify(exc)


def classify(exc: sqlite3.Error) -> str:
    """@brief The reader's index state for a SQLite error."""
    name = getattr(exc, "sqlite_errorname", "") or ""
    if name == "SQLITE_READONLY_ROLLBACK":
        return "needs_recovery"
    if name.startswith(("SQLITE_BUSY", "SQLITE_LOCKED")):
        return "busy"
    return "incompatible"


def open_writer(path: Path) -> sqlite3.Connection:
    """
    @brief Open (or create) the database read-write with explicit transactions.
    @details Opening a CodeGraph database read-write lets SQLite roll back a
             hot journal on first access; that is the only recovery path.
    """
    conn = sqlite3.connect(path, timeout=WRITER_BUSY_SECONDS, isolation_level=None)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA synchronous=FULL")
    return conn


def initialize(conn: sqlite3.Connection) -> None:
    """@brief Stamp the CodeGraph marker and create the schema in a new database."""
    conn.execute(f"PRAGMA application_id={APPLICATION_ID}")
    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    conn.execute("BEGIN IMMEDIATE")
    for statement in SCHEMA:
        conn.execute(statement)
    conn.execute("COMMIT")


def read_meta(conn: sqlite3.Connection) -> dict:
    """@brief The meta table, with `generation` as an integer."""
    meta = {key: value for key, value in conn.execute("SELECT key, value FROM meta")}
    if "generation" in meta:
        meta["generation"] = int(meta["generation"])
    return meta

# END OF FILE
