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
@file deletion_audit.py
@brief Durable local CLI deletion attempts outside the job directory.
@details SQLite is independent of optional web identity and keeps interrupted
         attempts uncertain. Corrupt or unsupported stores are never replaced.
"""

from __future__ import annotations

# IMPORTS
from contextlib import closing, contextmanager
from datetime import UTC, datetime
import os
from pathlib import Path
import re
import secrets
import sqlite3

from adore.state import StateError

# CONSTANTS
NAME = "deletion-audit.db"
_COLUMNS = {
    "event_key",
    "project",
    "project_id",
    "run_id",
    "created_at",
    "result",
    "imported",
    "dirty",
}


# DATA MODELS / TYPEDEFINITIONS
class DeletionAuditError(StateError):
    """@brief Local deletion audit is unavailable or corrupt."""


# PUBLIC API
class DeletionAudit:
    """@brief Own the standard-library local deletion receipt store."""

    def __init__(self, home: Path) -> None:
        """@brief Open or create a store without replacing an existing file."""
        self.path = home / NAME
        try:
            home.mkdir(parents=True, exist_ok=True)
            if self.path.is_symlink():
                raise DeletionAuditError("deletion audit path is a symbolic link")
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                fd = None
            if fd is not None:
                os.close(fd)
                with closing(sqlite3.connect(self.path)) as connection, connection:
                    connection.execute(
                        "CREATE TABLE events(event_key TEXT PRIMARY KEY, project TEXT NOT NULL, "
                        "project_id TEXT, run_id TEXT NOT NULL, created_at TEXT NOT NULL, "
                        "result TEXT NOT NULL, imported INTEGER NOT NULL, dirty INTEGER NOT NULL)"
                    )
                    connection.execute("PRAGMA user_version=1")
            with self.connect() as connection:
                self.validate(connection)
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise DeletionAuditError(
                "deletion audit unavailable or corrupt; inspect deletion-audit.db"
            ) from exc

    @contextmanager
    def connect(self):
        """@brief Open and close the existing ledger without implicit creation."""
        connection = sqlite3.connect(
            self.path.resolve().as_uri() + "?mode=rw", uri=True, timeout=10
        )
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def validate(connection, prefix="") -> None:
        """@brief Reject unsupported schemas and any invalid persisted receipt."""
        schema = prefix + "." if prefix else ""
        if connection.execute(f"PRAGMA {schema}user_version").fetchone()[0] != 1:
            raise DeletionAuditError(
                "unsupported deletion audit schema; delete deletion-audit.db to start fresh"
            )
        if connection.execute(f"PRAGMA {schema}quick_check").fetchone()[0] != "ok":
            raise DeletionAuditError("deletion audit is corrupt")
        columns = connection.execute(f"PRAGMA {schema}table_info(events)").fetchall()
        expected = [
            ("event_key", "TEXT", 0, 1),
            ("project", "TEXT", 1, 0),
            ("project_id", "TEXT", 0, 0),
            ("run_id", "TEXT", 1, 0),
            ("created_at", "TEXT", 1, 0),
            ("result", "TEXT", 1, 0),
            ("imported", "INTEGER", 1, 0),
            ("dirty", "INTEGER", 1, 0),
        ]
        if [(row[1], row[2], row[3], row[5]) for row in columns] != expected:
            raise DeletionAuditError("deletion audit is corrupt")
        for key, project, project_id, run_id, stamp, result, imported, dirty in connection.execute(
            "SELECT event_key,project,project_id,run_id,created_at,result,imported,dirty "
            f"FROM {schema}events"
        ):
            try:
                time = datetime.fromisoformat(stamp)
                valid = (
                    isinstance(key, str)
                    and re.fullmatch(r"[0-9a-f]{64}", key)
                    and isinstance(project, str)
                    and (not project or re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", project))
                    and (
                        project_id is None
                        or isinstance(project_id, str)
                        and re.fullmatch(r"[0-9a-f]{32}", project_id)
                    )
                    and isinstance(run_id, str)
                    and (
                        re.fullmatch(r"[A-Za-z0-9._-]{1,160}", run_id)
                        or not run_id
                        and imported == 1
                        and result == "applied"
                        and dirty == 0
                    )
                    and time.tzinfo is not None
                    and time.utcoffset().total_seconds() == 0
                    and (result, imported, dirty)
                    in (
                        ("uncertain", 0, 1),
                        ("uncertain", 1, 0),
                        ("applied", 0, 1),
                        ("applied", 1, 1),
                        ("applied", 1, 0),
                    )
                    and (bool(run_id) != (result == "applied" and imported == 1 and dirty == 0))
                )
                if not valid:
                    raise ValueError
            except (ValueError, TypeError, AttributeError) as exc:
                raise DeletionAuditError("deletion audit is corrupt") from exc

    def begin(self, project: str, project_id: str | None, run_id: str) -> str:
        """@brief Commit uncertain evidence before any destructive cleanup."""
        key = secrets.token_hex(32)
        try:
            with self.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self.validate(connection)
                connection.execute(
                    "INSERT INTO events VALUES(?,?,?,?,?,?,0,1)",
                    (key, project, project_id, run_id, datetime.now(UTC).isoformat(), "uncertain"),
                )
                self.validate(connection)
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise DeletionAuditError("cannot record deletion audit") from exc
        return key

    def confirm(self, key: str) -> None:
        """@brief Mark only the verified completed attempt applied."""
        try:
            with self.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self.validate(connection)
                cursor = connection.execute(
                    "UPDATE events SET result='applied',dirty=1 "
                    "WHERE event_key=? AND result='uncertain'",
                    (key,),
                )
                if cursor.rowcount != 1:
                    raise DeletionAuditError("deletion audit receipt unavailable")
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise DeletionAuditError("cannot confirm deletion audit") from exc


# END OF FILE
