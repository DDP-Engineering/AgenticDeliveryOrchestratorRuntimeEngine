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
@file store.py
@brief Durable web accounts, sessions, memberships, audit, and command queue.
@details SQLite is local to one ADORE host. An existing corrupt store fails
         closed and never reboots the admin/admin account.
"""

from __future__ import annotations

from collections.abc import Callable

# IMPORTS
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import socket
import sqlite3
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from adore import metrics
from adore.deletion_audit import NAME as DELETION_AUDIT_NAME
from adore.deletion_audit import DeletionAudit, DeletionAuditError
from adore.profiles import ProfileError, ProfileStore
from adore.web import audit as audit_contract
from adore.web.ownership import OwnershipError, WebStoreError, WorkerOwner, process_birth

# CONSTANTS
_HASHER = PasswordHasher()
# The only schema this build reads or writes; there are no migrations (AGENTS.md).
_SCHEMA_VERSION = 17
_SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','developer')),
    disabled INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
    password_change_required INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE memberships (
    user_id INTEGER NOT NULL REFERENCES users(id),
    project TEXT NOT NULL, profile_created_at TEXT NOT NULL,
    project_id TEXT NOT NULL,
    PRIMARY KEY (user_id, project)
);
CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
    csrf TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE TABLE operations (
    id INTEGER PRIMARY KEY, actor_id INTEGER NOT NULL, project TEXT NOT NULL,
    project_id TEXT NOT NULL,
    action TEXT NOT NULL, run_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL, result TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT '',
    domain TEXT NOT NULL CHECK(domain IN
        ('execution','configuration_project','configuration_global')),
    owner_id TEXT, owner_generation INTEGER, generation INTEGER NOT NULL DEFAULT 0,
    admitted_run_id TEXT NOT NULL DEFAULT '',
    run_owner_id TEXT NOT NULL DEFAULT '', run_owner_generation INTEGER NOT NULL DEFAULT 0,
    resource_key TEXT NOT NULL,
    UNIQUE(actor_id, idempotency_key)
);
CREATE TABLE audit (
    id INTEGER PRIMARY KEY, actor_id INTEGER, action TEXT NOT NULL,
    project TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL, evidence TEXT, event_key TEXT
);
CREATE UNIQUE INDEX audit_event_key ON audit(event_key);
CREATE TABLE audit_attempts (
    event_key TEXT PRIMARY KEY, actor_id INTEGER NOT NULL, action TEXT NOT NULL,
    project TEXT NOT NULL, created_at TEXT NOT NULL, evidence TEXT,
    confirmed INTEGER NOT NULL DEFAULT 0 CHECK(confirmed IN (0,1))
);
CREATE TABLE audit_policy (
    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
    retention_days INTEGER, max_bytes INTEGER
);
INSERT INTO audit_policy(singleton,retention_days,max_bytes) VALUES (1,NULL,NULL);
CREATE TABLE login_failures (
    identity_hash TEXT PRIMARY KEY, failures INTEGER NOT NULL,
    window_started TEXT NOT NULL
);
CREATE TABLE prices (
    id INTEGER PRIMARY KEY, project TEXT NOT NULL, project_id TEXT NOT NULL,
    executor TEXT NOT NULL,
    model TEXT NOT NULL, effective_from TEXT NOT NULL,
    input_usd_per_million TEXT NOT NULL,
    output_usd_per_million TEXT NOT NULL,
    actor_id INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL,
    UNIQUE(project_id, executor, model, effective_from)
);
CREATE TABLE worker_owners (
    id TEXT PRIMARY KEY, generation INTEGER NOT NULL,
    role TEXT NOT NULL, project_id TEXT NOT NULL, run_id TEXT NOT NULL,
    host TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL,
    activity TEXT NOT NULL DEFAULT 'idle'
);
CREATE UNIQUE INDEX worker_scope ON worker_owners(role,project_id,run_id) WHERE status='active';
CREATE UNIQUE INDEX worker_generations ON worker_owners(role,project_id,run_id,generation DESC);
CREATE TABLE worker_processes (
    owner_id TEXT NOT NULL REFERENCES worker_owners(id), pid INTEGER NOT NULL,
    birth TEXT NOT NULL, PRIMARY KEY(owner_id,pid,birth)
);
CREATE INDEX operation_queue ON operations(domain,project_id,status,id);
CREATE UNIQUE INDEX active_operation_resource ON operations(domain,project_id,resource_key)
    WHERE status='running';
CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    language TEXT, theme TEXT, ticket_body_mode TEXT
);
CREATE TABLE usage_projection (
    project_id TEXT NOT NULL, run_id TEXT NOT NULL,
    source_id TEXT NOT NULL, event_json TEXT NOT NULL,
    PRIMARY KEY(project_id, run_id, source_id)
);
CREATE TABLE usage_observation_projection (
    project_id TEXT NOT NULL, run_id TEXT NOT NULL,
    source_id TEXT NOT NULL, event_json TEXT NOT NULL,
    PRIMARY KEY(project_id, run_id, source_id)
);
CREATE TABLE usage_cursor (
    project_id TEXT NOT NULL, run_id TEXT NOT NULL,
    journal_length INTEGER NOT NULL, journal_sha256 TEXT NOT NULL,
    PRIMARY KEY(project_id, run_id)
);
"""


# DATA MODELS / TYPEDEFINITIONS
# HELPER FUNCTIONS
def _now() -> str:
    return datetime.now(UTC).isoformat()


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"], "username": row["username"],
        "role": row["role"], "disabled": bool(row["disabled"]),
        "password_change_required": bool(row["password_change_required"]),
    }


def _preferences(row: sqlite3.Row) -> dict[str, str | None]:
    """@brief Validate persisted account preferences before returning them."""
    result = {"language": row["language"], "theme": row["theme"],
              "ticket_body_mode": row["ticket_body_mode"]}
    if (result["language"] not in (None, "en", "fr", "de", "ro")
            or result["theme"] not in (None, "light", "dark", "system")
            or result["ticket_body_mode"] not in (None, "rendered", "source")):
        raise WebStoreError("account preferences are corrupt")
    return result


def _price_value(value: str) -> Decimal:
    """@brief Parse a bounded, fixed-point USD rate without float rounding."""
    if not isinstance(value, str) or not re.fullmatch(r"\d+(?:\.\d{1,6})?", value):
        raise WebStoreError("invalid price")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise WebStoreError("invalid price") from exc
    if parsed > Decimal("1000000"):
        raise WebStoreError("price exceeds limit")
    return parsed


def _price_identity(project: str, executor: str, model: str,
                    effective_from: str) -> None:
    """@brief Validate price keys on writes and persisted reads."""
    if (not isinstance(project, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", project)
            or not isinstance(executor, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", executor)
            or not isinstance(model, str) or not model or len(model) > 160
            or any(ord(char) < 32 for char in model)
            or not isinstance(effective_from, str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", effective_from)):
        raise WebStoreError("invalid price identity")
    try:
        if date.fromisoformat(effective_from).isoformat() != effective_from:
            raise WebStoreError("invalid effective date")
    except ValueError as exc:
        raise WebStoreError("invalid effective date") from exc


def _profile_identity(home: Path, project: str) -> tuple[str, str] | None:
    """@brief Resolve a project's immutable ID and creation stamp."""
    if not isinstance(project, str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9._-]{0,63}", project
    ):
        raise WebStoreError("invalid project identity")
    profiles = ProfileStore(home)
    if not profiles.exists(project):
        return None
    try:
        profile = profiles.load(project)
    except (ProfileError, OSError, ValueError, TypeError) as exc:
        raise WebStoreError("project metadata is corrupt") from exc
    if not isinstance(profile.created_at, str) or not profile.created_at:
        raise WebStoreError("project identity is missing")
    return profile.project_id, profile.created_at


# PUBLIC API
class WebStore:
    """
    @brief Web identity and durable operation store.
    @details Every method opens its own connection to avoid sharing a SQLite
             handle between HTTP requests. The initial account is created only
             if the database file did not exist before initialization.
    """

    def __init__(self, path: str | Path, *,
                 process_probe: Callable[[int], str | None] = process_birth) -> None:
        self.path = Path(path)
        self._process_probe = process_probe
        new = not self.path.exists()
        created = False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        marker = self.path.with_name(self.path.name + ".initialized")
        if new and marker.exists():
            raise WebStoreError("web database missing after initialization")
        try:
            with self._connect() as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version == 0:
                    # Only initialization needs the writer lock. An opener that
                    # observes an unfinished fresh store waits, then rechecks;
                    # an existing schema-0 file is still refused, never reset.
                    connection.execute("BEGIN IMMEDIATE")
                    version = connection.execute("PRAGMA user_version").fetchone()[0]
                    if version != 0:
                        # Another initializer committed while this opener waited.
                        # Historical validation must not retain its writer lock.
                        connection.commit()
                if version == 0 and new:
                    for statement in _SCHEMA.split(";"):
                        if statement.strip():
                            connection.execute(statement)
                    connection.execute(
                        "INSERT INTO users(username,password_hash,role,created_at) "
                        "VALUES (?,?,?,?)",
                        ("admin", _HASHER.hash("admin"), "admin", _now()),
                    )
                    connection.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")
                    created = True
                elif version != _SCHEMA_VERSION:
                    # No migrations while ADORE is in development (AGENTS.md).
                    raise WebStoreError(
                        f"web database schema {version} is not supported by this build "
                        f"(it needs schema {_SCHEMA_VERSION}); delete {self.path} and "
                        f"{marker} to start fresh"
                    )
                if "password_change_required" not in {
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(users)"
                    ).fetchall()
                }:
                    raise WebStoreError("web database missing password policy")
                if "profile_created_at" not in {
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(memberships)"
                    ).fetchall()
                }:
                    raise WebStoreError("web database missing membership identity")
                if "project_id" not in {
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(memberships)"
                    ).fetchall()
                }:
                    raise WebStoreError("web database missing membership identity")
                if "project_id" not in {
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(operations)"
                    ).fetchall()
                }:
                    raise WebStoreError("web database missing operation identity")
                for table, required in (
                    ("operations", {"domain", "owner_id", "owner_generation", "generation",
                                    "admitted_run_id", "resource_key", "run_owner_id",
                                    "run_owner_generation"}),
                    ("worker_owners", {"id", "generation", "role", "project_id", "run_id",
                                       "host", "status", "updated_at", "activity"}),
                    ("worker_processes", {"owner_id", "pid", "birth"}),
                ):
                    columns = {row[1] for row in connection.execute(
                        f"PRAGMA table_info({table})").fetchall()}
                    if not required.issubset(columns):
                        raise WebStoreError("web database missing worker ownership schema")
                for table, name, columns, partial in (
                    ("worker_owners", "worker_scope", ("role", "project_id", "run_id"), 1),
                    ("worker_owners", "worker_generations",
                     ("role", "project_id", "run_id", "generation"), 0),
                    ("operations", "active_operation_resource",
                     ("domain", "project_id", "resource_key"), 1),
                ):
                    indexes = connection.execute(f"PRAGMA index_list({table})").fetchall()
                    index = next((row for row in indexes if row["name"] == name), None)
                    actual = tuple(row["name"] for row in connection.execute(
                        f"PRAGMA index_info({name})").fetchall())
                    if (index is None or index["unique"] != 1 or index["partial"] != partial
                            or actual != columns):
                        raise WebStoreError("web database ownership indexes are corrupt")
                if "project_id" not in {
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(prices)"
                    ).fetchall()
                }:
                    raise WebStoreError("web database missing price identity")
                if not {"user_id", "language", "theme", "ticket_body_mode"}.issubset({
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(user_preferences)"
                    ).fetchall()
                }):
                    raise WebStoreError("web database missing account preferences")
                if not {"project_id", "run_id", "source_id", "event_json"}.issubset({
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(usage_projection)"
                    ).fetchall()
                }):
                    raise WebStoreError("web database missing usage projection")
                for table, columns in (
                    ("usage_observation_projection",
                     {"project_id", "run_id", "source_id", "event_json"}),
                    ("usage_cursor", {"project_id", "run_id", "journal_length",
                                      "journal_sha256"}),
                ):
                    present = {row[1] for row in connection.execute(
                        f"PRAGMA table_info({table})"
                    ).fetchall()}
                    if not columns.issubset(present):
                        raise WebStoreError("web database missing usage projection")
                if not {"singleton", "retention_days", "max_bytes"}.issubset({
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(audit_policy)"
                    ).fetchall()
                }):
                    raise WebStoreError("web database missing audit policy")
                self._audit_storage(connection)
                for row in connection.execute("SELECT * FROM audit").fetchall():
                    self._audit_projection(row)
                self._audit_policy_row(connection)
                if connection.execute(
                    "SELECT COUNT(*) FROM users WHERE role='admin' AND disabled=0"
                ).fetchone()[0] < 1:
                    raise WebStoreError("web database has no active administrator")
            if not marker.exists():
                marker.write_text("ADORE web identity store initialized\n", encoding="utf-8")
            if created:
                print("ADORE: initial web administrator is admin/admin; "
                      "change the password in My account.")
        except sqlite3.DatabaseError as exc:
            raise WebStoreError(f"web database is corrupt: {exc}") from exc

    def register_worker(self, role: str, *, project_id: str = "",
                        run_id: str = "") -> WorkerOwner:
        """@brief Register one explicit role/project/run process incarnation.
        @param[in] role Supervisor, project, run or configuration role.
        @param[in] project_id Immutable project ID; empty only for global roles.
        @param[in] run_id Exact run identity for run workers.
        @return Current server-issued owner handle.
        @exception OwnershipError A live owner already holds the scope.
        """
        self._worker_scope(role, project_id, run_id)
        birth = self._process_probe(os.getpid())
        if not isinstance(birth, str) or not birth:
            raise OwnershipError("worker ownership process identity unavailable")
        owner_id = secrets.token_hex(32)
        with self._ownership_connect() as connection:
            rows = connection.execute(
                "SELECT * FROM worker_owners "
                "WHERE role=? AND project_id=? AND run_id=? ORDER BY generation DESC",
                (role, project_id, run_id)).fetchall()
        # Historical validation is deliberately outside the shared writer lock.
        for row in rows:
            self._worker_record(row)
        if len({row["generation"] for row in rows}) != len(rows):
            raise WebStoreError("worker ownership generation history is corrupt")
        if any(row["status"] == "active" for row in rows):
            raise OwnershipError("worker ownership scope is already active")
        expected = dict(rows[0]) if rows else None
        with self._ownership_connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            latest = connection.execute(
                "SELECT * FROM worker_owners WHERE role=? AND project_id=? AND run_id=? "
                "ORDER BY generation DESC LIMIT 1", (role, project_id, run_id)).fetchone()
            if (dict(latest) if latest else None) != expected:
                raise OwnershipError("worker ownership scope changed during registration")
            generation = (expected["generation"] if expected else 0) + 1
            connection.execute(
                "INSERT INTO worker_owners(id,generation,role,project_id,run_id,host,"
                "status,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (owner_id, generation, role, project_id, run_id, socket.gethostname(),
                 "active", _now()))
            connection.execute(
                "INSERT INTO worker_processes(owner_id,pid,birth) VALUES(?,?,?)",
                (owner_id, os.getpid(), birth))
        return WorkerOwner(owner_id, generation, role, project_id, run_id)

    @staticmethod
    def _worker_scope(role: str, project_id: str, run_id: str) -> None:
        """@brief Reject implicit/contradictory owner scope at the storage boundary."""
        if (role not in ("supervisor", "project", "run", "configuration")
                or not isinstance(project_id, str) or not isinstance(run_id, str)
                or (project_id and not re.fullmatch(r"[a-f0-9]{32}", project_id))
                or (run_id and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}", run_id))
                or (role == "supervisor" and (project_id or run_id))
                or (role == "project" and (not project_id or run_id))
                or (role == "run" and (not project_id or not run_id))
                or (role == "configuration" and run_id)):
            raise OwnershipError("invalid worker ownership scope")

    def _owned(self, connection, owner: WorkerOwner):
        """@brief Verify the complete immutable handle against durable active ownership."""
        if (not isinstance(owner, WorkerOwner) or not isinstance(owner.id, str)
                or not re.fullmatch(r"[a-f0-9]{64}", owner.id)
                or type(owner.generation) is not int or owner.generation < 1):
            raise OwnershipError("explicit worker ownership required")
        self._worker_scope(owner.role, owner.project_id, owner.run_id)
        row = connection.execute("SELECT * FROM worker_owners WHERE id=?", (owner.id,)).fetchone()
        if row is not None:
            self._worker_record(row)
        if (row is None or row["status"] != "active" or row["generation"] != owner.generation
                or (row["role"], row["project_id"], row["run_id"])
                != (owner.role, owner.project_id, owner.run_id)
                or row["host"] != socket.gethostname()):
            raise OwnershipError("worker ownership lost")
        return row

    def _worker_record(self, row) -> None:
        """@brief Refuse corrupt historical or active owner evidence before using it."""
        self._worker_scope(row["role"], row["project_id"], row["run_id"])
        if (not isinstance(row["id"], str) or not re.fullmatch(r"[a-f0-9]{64}", row["id"])
                or type(row["generation"]) is not int or row["generation"] < 1
                or row["status"] not in ("active", "stopped", "dead")
                or row["activity"] not in ("idle", "busy")
                or not isinstance(row["host"], str) or not row["host"]):
            raise WebStoreError("worker ownership record is corrupt")
        try:
            if datetime.fromisoformat(row["updated_at"]).tzinfo is None:
                raise ValueError("missing timezone")
        except (ValueError, TypeError, OverflowError) as exc:
            raise WebStoreError("worker heartbeat timestamp is corrupt") from exc

    def attach_worker(self, owner: WorkerOwner) -> None:
        """@brief Bind the current child process before it can perform any effect."""
        birth = self._process_probe(os.getpid())
        if not isinstance(birth, str) or not birth:
            raise OwnershipError("worker ownership process identity unavailable")
        with self._ownership_connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._owned(connection, owner)
            connection.execute(
                "INSERT OR IGNORE INTO worker_processes(owner_id,pid,birth) VALUES(?,?,?)",
                (owner.id, os.getpid(), birth))

    def _participant(self, connection, owner: WorkerOwner) -> None:
        """@brief Require this PID incarnation to participate in the owner."""
        self._owned(connection, owner)
        birth = self._process_probe(os.getpid())
        if (not birth or connection.execute(
                "SELECT 1 FROM worker_processes WHERE owner_id=? AND pid=? AND birth=?",
                (owner.id, os.getpid(), birth)).fetchone() is None):
            raise OwnershipError("worker ownership process identity changed")

    def touch_worker(self, owner: WorkerOwner) -> None:
        """@brief Refresh only the caller's explicit scoped heartbeat."""
        with self._ownership_connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._participant(connection, owner)
            connection.execute("UPDATE worker_owners SET updated_at=? WHERE id=?",
                               (_now(), owner.id))

    def authorize_worker(self, owner: WorkerOwner) -> dict[str, Any]:
        """@brief Authorize autonomous project polling under explicit ownership."""
        with self._ownership_connect() as connection:
            self._participant(connection, owner)
        if owner.role != "project":
            raise OwnershipError("project polling ownership required")
        profile = ProfileStore(self.path.parent).find_by_id(owner.project_id)
        if profile is None or profile.archived:
            raise OwnershipError("project polling ownership target unavailable")
        return {"action": "poll", "project_id": owner.project_id, "project": profile.name,
                "run_id": ""}

    def assert_worker(self, owner: WorkerOwner) -> None:
        """@brief Verify this process still participates in an exact role/project/run owner."""
        with self._ownership_connect() as connection:
            self._participant(connection, owner)

    def set_worker_activity(self, owner: WorkerOwner, activity: str) -> None:
        """@brief Publish activity only for the verified owner incarnation."""
        if activity not in ("idle", "busy"):
            raise ValueError("invalid worker activity")
        with self._ownership_connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._participant(connection, owner)
            connection.execute("UPDATE worker_owners SET activity=? WHERE id=?",
                               (activity, owner.id))

    def worker_activity(self) -> str:
        """@brief Aggregate recent supervisor activity without confusing ownership."""
        rows = self.worker_heartbeats(role="supervisor")
        active = [row for row in rows if row["ready"]]
        if not active:
            return "unknown"
        return "busy" if any(row["activity"] == "busy" for row in active) else "idle"

    def clear_worker(self, owner: WorkerOwner) -> None:
        """@brief Stop only an idle owner; running effects retain their ownership."""
        with self._ownership_connect() as connection:
            processes = connection.execute(
                "SELECT * FROM worker_processes WHERE owner_id=?", (owner.id,)).fetchall()
        for process in processes:
            if process["pid"] != os.getpid():
                try:
                    live = self._process_probe(process["pid"]) == process["birth"]
                except (WebStoreError, OSError):
                    live = True
                if live:
                    raise OwnershipError("worker ownership still has live participants")
        with self._ownership_connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._participant(connection, owner)
            current_processes = connection.execute(
                "SELECT * FROM worker_processes WHERE owner_id=?", (owner.id,)).fetchall()
            if [dict(row) for row in current_processes] != [dict(row) for row in processes]:
                raise OwnershipError("worker ownership participants changed during shutdown")
            if connection.execute(
                "SELECT 1 FROM operations WHERE owner_id=? AND status='running' LIMIT 1",
                (owner.id,)).fetchone():
                raise OwnershipError("worker ownership still has running operations")
            connection.execute("UPDATE worker_owners SET status='stopped' WHERE id=?", (owner.id,))

    def worker_heartbeats(self, *, role: str | None = None,
                          project_id: str | None = None, run_id: str | None = None,
                          max_age_seconds: float = 10) -> list[dict[str, Any]]:
        """@brief Inspect heartbeat evidence per role, immutable project and run.
        @return Scoped metadata and readiness; owner capability IDs stay private.
        @exception WebStoreError Corrupt persisted timestamps or scope.
        """
        with self._ownership_connect() as connection:
            rows = connection.execute(
                "SELECT * FROM worker_owners WHERE status='active'").fetchall()
        result = []
        for row in rows:
            self._worker_record(row)
            if ((role is not None and row["role"] != role)
                    or (project_id is not None and row["project_id"] != project_id)
                    or (run_id is not None and row["run_id"] != run_id)):
                continue
            try:
                stamp = datetime.fromisoformat(row["updated_at"])
                if stamp.tzinfo is None:
                    raise ValueError("missing timezone")
                age = (datetime.now(UTC) - stamp).total_seconds()
            except (ValueError, TypeError, OverflowError) as exc:
                raise WebStoreError("worker heartbeat timestamp is corrupt") from exc
            if age < -5:
                raise WebStoreError("worker heartbeat is in the future")
            if row["activity"] not in ("idle", "busy"):
                raise WebStoreError("worker activity is corrupt")
            result.append({"role": row["role"], "project_id": row["project_id"],
                           "run_id": row["run_id"], "generation": row["generation"],
                           "updated_at": row["updated_at"], "activity": row["activity"],
                           "ready": age <= max_age_seconds})
        return result

    def worker_ready(self, *, max_age_seconds: float = 10) -> bool:
        """@brief Readiness requires a recent supervisor heartbeat."""
        return any(row["ready"] for row in self.worker_heartbeats(
            role="supervisor", max_age_seconds=max_age_seconds))

    def allow_login(self, username: str, client: str) -> bool:
        """@brief Enforce five failed attempts per identity and client in ten minutes."""
        identity = _digest(f"{username.casefold()}\0{client}")
        cutoff = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT failures,window_started FROM login_failures WHERE identity_hash=?",
                (identity,),
            ).fetchone()
        return row is None or row["window_started"] < cutoff or row["failures"] < 5

    def record_login(self, username: str, client: str, *, success: bool) -> None:
        """@brief Clear the failure window after success or count a failed login."""
        identity = _digest(f"{username.casefold()}\0{client}")
        cutoff = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
        with self._connect() as connection:
            if success:
                connection.execute(
                    "DELETE FROM login_failures WHERE identity_hash=?", (identity,)
                )
                return
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT failures,window_started FROM login_failures WHERE identity_hash=?",
                (identity,),
            ).fetchone()
            count = row["failures"] + 1 if row and row["window_started"] >= cutoff else 1
            connection.execute(
                "INSERT INTO login_failures(identity_hash,failures,window_started) "
                "VALUES (?,?,?) ON CONFLICT(identity_hash) DO UPDATE SET "
                "failures=excluded.failures,window_started=excluded.window_started",
                (identity, count, row["window_started"] if row and
                 row["window_started"] >= cutoff else _now()),
            )

    @contextmanager
    def _connect(self):
        """@brief Yield and close one transactional SQLite connection."""
        connection = sqlite3.connect(self.path, timeout=10, uri=True)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=10000")
            with connection:
                yield connection
        finally:
            connection.close()

    @contextmanager
    def _ownership_connect(self):
        """@brief Translate ownership storage faults without changing account error contracts."""
        try:
            with self._connect() as connection:
                yield connection
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("worker ownership storage is corrupt") from exc

    def forget_run_usage(self, project_id: str, run_id: str, *,
                         remove_source: Callable[[], None]) -> None:
        """@brief Clear only a verified deleted job's replaceable usage projections.
        @param[in] project_id Immutable owning profile identity.
        @param[in] run_id Exact deleted job; caller holds the conductor lock.
        @param[in] remove_source Remove that job's source while projection readers are serialized.
        @exception WebStoreError Invalid identity or failed atomic projection cleanup.
        """
        if (not re.fullmatch(r"[0-9a-f]{32}", project_id)
                or not re.fullmatch(r"[A-Za-z0-9._-]{1,160}", run_id)):
            raise WebStoreError("invalid deleted usage identity")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                remove_source()
                for table in ("usage_projection", "usage_observation_projection", "usage_cursor"):
                    connection.execute(f"DELETE FROM {table} WHERE project_id=? AND run_id=?",
                                       (project_id, run_id))
        except sqlite3.Error as exc:
            raise WebStoreError("deleted usage projection cleanup failed") from exc

    def reconcile_usage(self, project_id: str, run_id: str,
                        journal: list[dict], *,
                        current_source: Callable[[], list[dict]] | None = None) -> list[dict]:
        """
        @brief Project identified usage into SQLite without replay inflation.
        @param[in] project_id Immutable profile identity.
        @param[in] run_id Owning run identity.
        @param[in] journal Retained run journal in persisted order.
        @return Validated, projected usage records in source order.
        @exception WebStoreError On malformed, changed or missing evidence.
        """
        if (not isinstance(project_id, str)
                or not re.fullmatch(r"[0-9a-f]{32}", project_id)
                or not isinstance(run_id, str)
                or not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", run_id)):
            raise WebStoreError("invalid usage identity")
        try:
            encoded_journal = json.dumps(
                journal, sort_keys=True, separators=(",", ":"), allow_nan=False)
            journal_digest = hashlib.sha256(encoded_journal.encode()).hexdigest()
            source = metrics.unique_usage_events(journal, run_id)
            usage = []
            observations: dict[str, tuple[tuple, str]] = {}
            for event in source:
                if event.get("event") == "usage-observation":
                    value = metrics.validate_usage_observation(event, run_id)
                    key = value[0]
                    payload = json.dumps(event, sort_keys=True,
                                         separators=(",", ":"), allow_nan=False)
                    if key in observations:
                        if observations[key][0] != value:
                            raise WebStoreError("conflicting usage observation")
                    else:
                        observations[key] = (value, payload)
                    continue
                if event.get("event") != "usage":
                    continue
                incoming = event.get("tokens_in")
                outgoing = event.get("tokens_out")
                money = event.get("cost_usd")
                if ((incoming is not None and (type(incoming) is not int or incoming < 0))
                        or (outgoing is not None and (type(outgoing) is not int or outgoing < 0))
                        or (money is not None and (type(money) not in (int, float) or money < 0
                                                   or not math.isfinite(money)))):
                    raise WebStoreError("malformed usage amounts")
                key = event.get("event_id")
                if not isinstance(key, str) or not key or len(key) > 200:
                    raise WebStoreError("malformed usage source identity")
                payload = json.dumps(event, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False)
                usage.append((key, payload, event))
        except (metrics.MetricsError, TypeError, ValueError, OverflowError) as exc:
            raise WebStoreError("usage journal is corrupt") from exc
        if len({key for key, _payload, _event in usage}) != len(usage):
            raise WebStoreError("duplicate usage source identity")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                fresh = current_source() if current_source is not None else None
                if fresh is not None and fresh[:len(journal)] != journal:
                    raise WebStoreError("usage source changed before projection")
                stale_snapshot = False
                cursor = connection.execute(
                    "SELECT journal_length,journal_sha256 FROM usage_cursor "
                    "WHERE project_id=? AND run_id=?", (project_id, run_id),
                ).fetchone()
                if cursor is not None:
                    prior_length = cursor["journal_length"]
                    prior_digest = cursor["journal_sha256"]
                    if (type(prior_length) is not int or prior_length < 0
                            or type(prior_digest) is not str
                            or not re.fullmatch(r"[0-9a-f]{64}", prior_digest)):
                        raise WebStoreError("usage cursor is corrupt")
                    if prior_length > len(journal):
                        if fresh is None or len(fresh) < prior_length:
                            raise WebStoreError("projected usage is absent from journal")
                        stale_snapshot = True
                    prefix_source = fresh if stale_snapshot else journal
                    prefix = json.dumps(prefix_source[:prior_length], sort_keys=True,
                                        separators=(",", ":"), allow_nan=False)
                    if hashlib.sha256(prefix.encode()).hexdigest() != prior_digest:
                        raise WebStoreError("usage journal changed before cursor")
                prior = {row["source_id"]: row["event_json"] for row in
                         connection.execute(
                             "SELECT source_id,event_json FROM usage_projection "
                             "WHERE project_id=? AND run_id=?",
                             (project_id, run_id),
                         ).fetchall()}
                if not stale_snapshot and set(prior) - {key for key, _payload, _event in usage}:
                    raise WebStoreError("projected usage is absent from journal")
                for key, payload, _event in usage:
                    if key in prior and prior[key] != payload:
                        raise WebStoreError("conflicting projected usage")
                    if key not in prior and stale_snapshot:
                        raise WebStoreError("stale usage snapshot is absent from projection")
                    if key not in prior:
                        connection.execute(
                            "INSERT INTO usage_projection"
                            "(project_id,run_id,source_id,event_json) VALUES(?,?,?,?)",
                            (project_id, run_id, key, payload),
                        )
                prior_observations = {
                    row["source_id"]: row["event_json"] for row in
                    connection.execute(
                        "SELECT source_id,event_json FROM usage_observation_projection "
                        "WHERE project_id=? AND run_id=?", (project_id, run_id),
                    ).fetchall()
                }
                if not stale_snapshot and set(prior_observations) - set(observations):
                    raise WebStoreError("projected observation is absent from journal")
                for key, (_value, payload) in observations.items():
                    if key in prior_observations and prior_observations[key] != payload:
                        raise WebStoreError("conflicting projected observation")
                    if key not in prior_observations and stale_snapshot:
                        raise WebStoreError("stale observation is absent from projection")
                    if key not in prior_observations:
                        connection.execute(
                            "INSERT INTO usage_observation_projection"
                            "(project_id,run_id,source_id,event_json) VALUES(?,?,?,?)",
                            (project_id, run_id, key, payload),
                        )
                if not stale_snapshot:
                    connection.execute(
                        "INSERT INTO usage_cursor"
                        "(project_id,run_id,journal_length,journal_sha256) VALUES(?,?,?,?) "
                        "ON CONFLICT(project_id,run_id) DO UPDATE SET "
                        "journal_length=excluded.journal_length, "
                        "journal_sha256=excluded.journal_sha256",
                        (project_id, run_id, len(journal), journal_digest),
                    )
                stored = {row["source_id"]: row["event_json"] for row in
                          connection.execute(
                              "SELECT source_id,event_json FROM usage_projection "
                              "WHERE project_id=? AND run_id=?",
                              (project_id, run_id),
                          ).fetchall()}
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("usage projection is corrupt") from exc
        try:
            return [json.loads(stored[key]) for key, _payload, _event in usage]
        except (KeyError, ValueError, TypeError) as exc:
            raise WebStoreError("usage projection is corrupt") from exc

    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        """@brief Verify local credentials without exposing password hashes."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE username=?", (username,)
            ).fetchone()
        if row is None or row["disabled"]:
            return None
        try:
            if not _HASHER.verify(row["password_hash"], password):
                return None
        except (VerifyMismatchError, InvalidHashError):
            return None
        return _user(row)

    def factory_password(self, user_id: int) -> bool:
        """@brief Identify the authenticated factory account's unchanged password.
        @param[in] user_id Authenticated account identity.
        @return Whether the public initial password remains in use.
        @exception WebStoreError Missing account or corrupt password hash.
        """
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT username, role, password_hash FROM users WHERE id=?", (user_id,)
                ).fetchone()
            if row is None:
                raise WebStoreError("account missing")
            if row["username"] != "admin" or row["role"] != "admin":
                return False
            try:
                return _HASHER.verify(row["password_hash"], "admin")
            except VerifyMismatchError:
                return False
        except (sqlite3.DatabaseError, InvalidHashError, VerificationError, TypeError) as exc:
            raise WebStoreError("account credentials corrupt") from exc

    def create_user(
        self, username: str, password: str, role: str, *, actor_id: int | None = None
    ) -> dict[str, Any]:
        """@brief Create a validated account; duplicate names fail closed."""
        if not username or len(username) > 64 or not username.replace("_", "").isalnum():
            raise WebStoreError("invalid username")
        if len(password) < 8:
            raise WebStoreError("password must contain at least 8 characters")
        if role not in ("admin", "developer"):
            raise WebStoreError("invalid role")
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO users(username,password_hash,role,created_at) VALUES (?,?,?,?)",
                    (username, _HASHER.hash(password), role, _now()),
                )
                row = connection.execute(
                    "SELECT * FROM users WHERE id=?", (cursor.lastrowid,)
                ).fetchone()
                if actor_id is not None:
                    self._write_audit(
                        connection,
                        actor_id,
                        "user-created",
                        detail=username,
                        payload=self._evidence(
                            connection,
                            actor_id,
                            resource_type="account",
                            resource_id=str(row["id"]),
                            before={"exists": False},
                            after={"role": role, "project_ids": [], "disabled": False},
                        ),
                    )
            return _user(row)
        except sqlite3.IntegrityError as exc:
            raise WebStoreError("username already exists") from exc

    def list_users(self) -> list[dict[str, Any]]:
        """@brief List accounts without their password hashes."""
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM users ORDER BY username").fetchall()
        return [_user(row) for row in rows]

    def create_user_with_access(
        self,
        username: str,
        password: str,
        role: str,
        project_ids: list[str],
        allow_no_projects: bool,
        actor_id: int,
    ) -> dict[str, Any]:
        """
        @brief      Commit an explicit account intent, grants and audit atomically.
        @param[in]  username Valid account identity.
        @param[in]  password Transient credential, stored only as Argon2id hash.
        @param[in]  role Explicit admin or developer role.
        @param[in]  project_ids Distinct immutable visible project identities.
        @param[in]  allow_no_projects Deliberate developer zero-project choice.
        @param[in]  actor_id Active administrator committing this intent.
        @return     Public account with exactly committed project IDs.
        @exception  WebStoreError Invalid intent, stale project or failed storage.
        @note       Profile lifecycle changes are rechecked before SQLite commit;
                    later replacements cannot inherit immutable identity grants.
        """
        if (
            not isinstance(username, str)
            or not username
            or len(username) > 64
            or not username.replace("_", "").isalnum()
        ):
            raise WebStoreError("invalid username")
        if not isinstance(password, str) or not 8 <= len(password) <= 1024:
            raise WebStoreError("password must contain at least 8 characters")
        if role not in ("admin", "developer"):
            raise WebStoreError("invalid role")
        if (
            type(allow_no_projects) is not bool
            or not isinstance(project_ids, list)
            or len(project_ids) > 1000
            or any(
                not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value)
                for value in project_ids
            )
            or len(set(project_ids)) != len(project_ids)
            or role == "admin"
            and project_ids
            or role == "developer"
            and not project_ids
            and not allow_no_projects
        ):
            raise WebStoreError("invalid grants")
        projects = self._projects_by_id()
        selected = []
        for identity in sorted(project_ids):
            profile = projects.get(identity)
            if profile is None:
                raise WebStoreError("project not found")
            if profile.archived:
                raise WebStoreError("project archived")
            selected.append(profile)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                actor = connection.execute("SELECT * FROM users WHERE id=?", (actor_id,)).fetchone()
                if (
                    actor is None
                    or actor["disabled"]
                    or actor["role"] != "admin"
                    or actor["password_change_required"]
                ):
                    raise WebStoreError("administrator required")
                if connection.execute(
                    "SELECT 1 FROM users WHERE username=?", (username,)
                ).fetchone():
                    raise WebStoreError("username already exists")
                cursor = connection.execute(
                    "INSERT INTO users(username,password_hash,role,created_at) VALUES (?,?,?,?)",
                    (username, _HASHER.hash(password), role, _now()),
                )
                user_id = cursor.lastrowid
                connection.executemany(
                    "INSERT INTO memberships(user_id,project,profile_created_at,project_id) "
                    "VALUES (?,?,?,?)",
                    [
                        (user_id, profile.name, profile.created_at, profile.project_id)
                        for profile in selected
                    ],
                )
                self._write_audit(
                    connection,
                    actor_id,
                    "user-created",
                    detail=username,
                    payload=self._evidence(
                        connection,
                        actor_id,
                        resource_type="account",
                        resource_id=str(user_id),
                        before={"exists": False},
                        after={"role": role, "project_ids": sorted(project_ids), "disabled": False},
                    ),
                )
                current = self._projects_by_id()
                for profile in selected:
                    live = current.get(profile.project_id)
                    if (
                        live is None
                        or live.archived
                        or live.name != profile.name
                        or live.created_at != profile.created_at
                    ):
                        raise WebStoreError("project changed during the update")
                row = connection.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            return {**_user(row), "project_ids": sorted(project_ids)}
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("user creation storage failed") from exc

    def membership_ids(self, user_id: int) -> list[str]:
        """@brief Return current immutable grants alongside compatible name reads."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT project,profile_created_at,project_id FROM memberships WHERE user_id=?",
                (user_id,),
            ).fetchall()
        return sorted(profile.project_id for profile in
                      self._granted_projects(rows, self._projects_by_id()))

    def user_by_id(self, user_id: int) -> dict[str, Any] | None:
        """@brief Recheck the actor before worker execution."""
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return _user(row) if row is not None else None

    def disable_user(self, user_id: int, *, actor_id: int | None = None) -> None:
        """@brief Disable an account and revoke its sessions."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            before = connection.execute(
                "SELECT disabled FROM users WHERE id=?", (user_id,)
            ).fetchone()
            row = connection.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
            if row is None:
                raise WebStoreError("user not found")
            if row["role"] == "admin":
                count = connection.execute(
                    "SELECT COUNT(*) FROM users WHERE role='admin' AND disabled=0"
                ).fetchone()[0]
                if count <= 1:
                    raise WebStoreError("cannot disable the last administrator")
            connection.execute("UPDATE users SET disabled=1 WHERE id=?", (user_id,))
            connection.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            if actor_id is not None:
                self._write_audit(
                    connection,
                    actor_id,
                    "user-disabled",
                    detail=str(user_id),
                    payload=self._evidence(
                        connection,
                        actor_id,
                        resource_type="account",
                        resource_id=str(user_id),
                        before={"disabled": bool(before[0])},
                        after={"disabled": True},
                    ),
                )

    def enable_user(self, user_id: int, *, actor_id: int | None = None) -> None:
        """@brief Re-enable an existing account without restoring old sessions."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            before = connection.execute(
                "SELECT disabled FROM users WHERE id=?", (user_id,)
            ).fetchone()
            cursor = connection.execute("UPDATE users SET disabled=0 WHERE id=?", (user_id,))
            if cursor.rowcount != 1:
                raise WebStoreError("user not found")
            if actor_id is not None:
                self._write_audit(
                    connection,
                    actor_id,
                    "user-enabled",
                    detail=str(user_id),
                    payload=self._evidence(
                        connection,
                        actor_id,
                        resource_type="account",
                        resource_id=str(user_id),
                        before={"disabled": bool(before[0])},
                        after={"disabled": False},
                    ),
                )

    def change_password(
        self, user_id: int, old: str, new: str, *, actor_id: int | None = None
    ) -> None:
        """@brief Change own password, satisfy any reset marker and revoke sessions."""
        if len(new) < 8:
            raise WebStoreError("password must contain at least 8 characters")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if row is None:
                raise WebStoreError("user not found")
            try:
                valid = _HASHER.verify(row["password_hash"], old)
            except (VerifyMismatchError, InvalidHashError):
                valid = False
            if not valid:
                raise WebStoreError("current password is incorrect")
            connection.execute(
                "UPDATE users SET password_hash=?, password_change_required=0 WHERE id=?",
                (_HASHER.hash(new), user_id),
            )
            connection.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))

            if actor_id is not None:
                self._write_audit(connection, actor_id, "password-changed",
                                  payload=self._evidence(connection, actor_id,
                                  resource_type="account", resource_id=str(user_id),
                                  before={"password_change_required":
                                          bool(row["password_change_required"])},
                                  after={"password_change_required": False}))

    def reset_password(
        self, user_id: int, replacement: str, *, actor_id: int | None = None
    ) -> None:
        """@brief Set a recovery password the target must replace; revoke its sessions."""
        if len(replacement) < 8:
            raise WebStoreError("password must contain at least 8 characters")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            before = connection.execute(
                "SELECT password_change_required FROM users WHERE id=?", (user_id,)
            ).fetchone()
            cursor = connection.execute(
                "UPDATE users SET password_hash=?, password_change_required=1 WHERE id=?",
                (_HASHER.hash(replacement), user_id),
            )
            if cursor.rowcount != 1:
                raise WebStoreError("user not found")
            connection.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            if actor_id is not None:
                self._write_audit(
                    connection,
                    actor_id,
                    "password-reset",
                    detail=str(user_id),
                    payload=self._evidence(
                        connection,
                        actor_id,
                        resource_type="account",
                        resource_id=str(user_id),
                        before={"password_change_required": bool(before[0])},
                        after={"password_change_required": True},
                    ),
                )

    def create_session(self, user_id: int) -> tuple[str, str]:
        """@brief Create opaque session and CSRF tokens with an expiry."""
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        expiry = (datetime.now(UTC) + timedelta(hours=12)).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO sessions(token_hash,user_id,csrf,expires_at) VALUES (?,?,?,?)",
                (_digest(token), user_id, csrf, expiry),
            )
        return token, csrf

    def session_user(self, token: str) -> dict[str, Any] | None:
        """@brief Resolve only active unexpired sessions."""
        if not token:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT u.*, s.csrf, s.expires_at FROM sessions s "
                "JOIN users u ON u.id=s.user_id WHERE s.token_hash=?",
                (_digest(token),),
            ).fetchone()
        if row is None or row["disabled"] or row["expires_at"] <= _now():
            return None
        return {**_user(row), "csrf": row["csrf"]}

    def revoke_session(self, token: str) -> None:
        """@brief Revoke one session."""
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash=?", (_digest(token),))

    def preferences(self, user_id: int) -> dict[str, str | None]:
        """@brief Read one user's presentation preferences, or nullable fallbacks.
        @param[in] user_id Authenticated account identity.
        @return Validated language, theme and ticket body mode; null means unset.
        @exception WebStoreError Missing account or corrupt saved preferences.
        """
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT p.language,p.theme,p.ticket_body_mode FROM users u LEFT JOIN "
                    "user_preferences p ON p.user_id=u.id WHERE u.id=?",
                    (user_id,),
                ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("account preferences storage is corrupt") from exc
        if row is None:
            raise WebStoreError("user not found")
        return _preferences(row)

    def set_preferences(self, user_id: int,
                        updates: dict[str, str]) -> dict[str, str | None]:
        """@brief Update only supplied preference fields in one transaction."""
        if (not updates or set(updates) - {"language", "theme", "ticket_body_mode"}
                or any(key == "language" and value not in ("en", "fr", "de", "ro")
                       or key == "theme" and value not in ("light", "dark", "system")
                       or key == "ticket_body_mode" and value not in ("rendered", "source")
                       for key, value in updates.items())):
            raise WebStoreError("invalid account preferences")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT p.language,p.theme,p.ticket_body_mode FROM users u LEFT JOIN "
                    "user_preferences p ON p.user_id=u.id WHERE u.id=?",
                    (user_id,),
                ).fetchone()
                if row is None:
                    raise WebStoreError("user not found")
                values = {**_preferences(row), **updates}
                connection.execute(
                    "INSERT INTO user_preferences(user_id,language,theme,ticket_body_mode) "
                    "VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET "
                    "language=excluded.language,theme=excluded.theme,"
                    "ticket_body_mode=excluded.ticket_body_mode",
                    (user_id, values["language"], values["theme"], values["ticket_body_mode"]),
                )
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("account preferences storage is corrupt") from exc
        return values

    def set_memberships(
        self, user_id: int, projects: list[str], *, actor_id: int | None = None
    ) -> None:
        """@brief Replace a developer's project grants atomically."""
        grants = []
        for project in sorted(set(projects)):
            identity = _profile_identity(self.path.parent, project)
            if identity is None:
                raise WebStoreError("project not found")
            grants.append((user_id, project, identity[1], identity[0]))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            before = [
                profile.project_id
                for profile in self._granted_projects(
                    connection.execute(
                        "SELECT * FROM memberships WHERE user_id=?", (user_id,)
                    ).fetchall(),
                    self._projects_by_id(),
                )
            ]
            if connection.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone() is None:
                raise WebStoreError("user not found")
            connection.execute("DELETE FROM memberships WHERE user_id=?", (user_id,))
            connection.executemany(
                "INSERT INTO memberships(user_id,project,profile_created_at,project_id) "
                "VALUES (?,?,?,?)",
                grants,
            )

            if actor_id is not None:
                self._write_audit(
                    connection,
                    actor_id,
                    "membership-changed",
                    detail=str(user_id),
                    payload=self._evidence(
                        connection,
                        actor_id,
                        resource_type="access",
                        resource_id=str(user_id),
                        before={"project_ids": sorted(before)},
                        after={"project_ids": sorted(row[3] for row in grants)},
                    ),
                )

    def project_members(self, project: str) -> set[int]:
        """
        @brief      IDs of the accounts granted a project.
        @details    Only grants that carry the project's current identity count,
                    as in `memberships`, so rows left by a deleted project of the
                    same name do not.
        @param[in]  project Profile name.
        @return     Granted account IDs.
        @exception  WebStoreError When the project does not exist.
        """
        identity = _profile_identity(self.path.parent, project)
        if identity is None:
            raise WebStoreError("project not found")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT user_id FROM memberships WHERE project_id=? AND profile_created_at=?",
                identity,
            ).fetchall()
        return {row["user_id"] for row in rows}

    def set_membership(
        self, user_id: int, project: str, granted: bool, *, actor_id: int | None = None
    ) -> None:
        """
        @brief      Grant or remove one account's access to one project.
        @details    Grants are matched by the project's immutable identity, so a
                    grant made before a rename is found. In one write transaction
                    the account's other grants are rewritten under their
                    projects' current names, as `set_memberships` stores them, so a
                    reused name never takes another project's grant; rows of
                    deleted projects, which grant nothing, are dropped. Other
                    accounts' grants are not touched.
        @param[in]  user_id Account ID.
        @param[in]  project Profile name.
        @param[in]  granted True to grant, False to remove.
        @exception  WebStoreError When the project or account does not exist,
                    project or membership metadata is corrupt, or a rename
                    lands during the update (nothing is changed then).
        """
        identity = _profile_identity(self.path.parent, project)
        if identity is None:
            raise WebStoreError("project not found")
        by_id = self._projects_by_id()
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                if (
                    connection.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone()
                    is None
                ):
                    raise WebStoreError("user not found")
                rows = connection.execute(
                    "SELECT project,profile_created_at,project_id FROM memberships WHERE user_id=?",
                    (user_id,),
                ).fetchall()
                before = sorted(
                    profile.project_id for profile in self._granted_projects(rows, by_id)
                )
                grants = [
                    (user_id, profile.name, profile.created_at, profile.project_id)
                    for profile in self._granted_projects(rows, by_id)
                    if profile.project_id != identity[0]
                ]
                if granted:
                    grants.append((user_id, project, identity[1], identity[0]))
                connection.execute("DELETE FROM memberships WHERE user_id=?", (user_id,))
                connection.executemany(
                    "INSERT INTO memberships(user_id,project,profile_created_at,project_id) "
                    "VALUES (?,?,?,?)",
                    grants,
                )
                if actor_id is not None:
                    self._write_audit(
                        connection,
                        actor_id,
                        "membership-changed",
                        project,
                        f"user {user_id} {'granted' if granted else 'removed'}",
                        payload=self._evidence(
                            connection,
                            actor_id,
                            project_id=identity[0],
                            resource_type="access",
                            resource_id=str(user_id),
                            before={"project_ids": before},
                            after={"project_ids": sorted(row[3] for row in grants)},
                        ),
                    )
        except sqlite3.IntegrityError as exc:  # a rename landed after the project snapshot
            raise WebStoreError("project changed during the update") from exc

    def memberships(self, user_id: int) -> set[str]:
        """@brief Get assigned profile names for the current request."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT project,profile_created_at,project_id "
                "FROM memberships WHERE user_id=?",
                (user_id,)
            ).fetchall()
        return {profile.name for profile in self._granted_projects(rows, self._projects_by_id())}

    def _projects_by_id(self) -> dict[str, Any]:
        """@brief Live projects by immutable ID, failing closed on corrupt metadata."""
        profiles = ProfileStore(self.path.parent)
        if profiles.invalid_profiles():
            raise WebStoreError("project metadata is corrupt")
        by_id = {}
        for profile in profiles.list_profiles():
            if profile.project_id in by_id:
                raise WebStoreError("duplicate project identity")
            by_id[profile.project_id] = profile
        return by_id

    @staticmethod
    def _granted_projects(rows: list[sqlite3.Row], by_id: dict[str, Any]) -> list[Any]:
        """@brief Live projects named by grant rows; a deleted project's row grants nothing."""
        granted = []
        for row in rows:
            if (not isinstance(row["project"], str)
                    or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", row["project"])
                    or not isinstance(row["project_id"], str)
                    or not re.fullmatch(r"[0-9a-f]{32}", row["project_id"])
                    or not isinstance(row["profile_created_at"], str)
                    or not row["profile_created_at"]):
                raise WebStoreError("membership identity is corrupt")
            profile = by_id.get(row["project_id"])
            if profile is not None and profile.created_at == row["profile_created_at"]:
                granted.append(profile)
        return granted

    def _operation_record(self, row) -> dict[str, Any]:
        """@brief Validate persisted operation scope without filesystem work."""
        operation = dict(row)
        action, domain = operation["action"], operation["domain"]
        expected = ("execution" if action in ("start", "retry", "restart", "cancel") else
                    "configuration_project" if action in ("pause", "resume", "delete") else
                    domain if action == "configure" and domain in (
                        "configuration_project", "configuration_global") else None)
        if (domain not in ("execution", "configuration_project", "configuration_global")
                or domain != expected or not isinstance(operation["run_id"], str)
                or operation["status"] not in (
                    "pending", "running", "succeeded", "failed", "uncertain")
                or type(operation["generation"]) is not int or operation["generation"] < 0
                or operation["resource_key"] != self._operation_resource(
                    action, operation["run_id"])):
            raise WebStoreError("operation scope or generation is corrupt")
        project_id, project = operation["project_id"], operation["project"]
        if domain == "configuration_global":
            if project_id or project:
                raise WebStoreError("global operation project scope is corrupt")
        elif (not isinstance(project_id, str) or not re.fullmatch(r"[a-f0-9]{32}", project_id)
              or not isinstance(project, str)
              or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", project)):
            raise WebStoreError("operation project scope is corrupt")
        return operation

    def _operation_with_current_project(self, row) -> dict[str, Any]:
        """@brief Resolve a queued command's immutable target to its current label."""
        operation = self._operation_record(row)
        project_id = operation["project_id"]
        if operation["domain"] == "configuration_global":
            if project_id or operation["project"]:
                raise WebStoreError("global operation has a project")
            return operation
        if (not isinstance(project_id, str)
                or not re.fullmatch(r"[0-9a-f]{32}", project_id)):
            raise WebStoreError("operation identity is corrupt")
        try:
            profile = ProfileStore(self.path.parent).find_by_id(project_id)
        except ProfileError as exc:
            raise WebStoreError("operation project identity is corrupt") from exc
        if profile is not None:
            operation["project"] = profile.name
        return operation

    def enqueue(
        self, actor_id: int, project: str, action: str, run_id: str, key: str
    ) -> dict[str, Any]:
        """@brief Persist an idempotent operation request."""
        if (
            action not in ("start", "retry", "cancel", "restart", "pause", "resume", "delete")
            or type(actor_id) is not int or actor_id < 1
            or not isinstance(key, str) or not key
            or len(key) > 128
        ):
            raise WebStoreError("invalid operation")
        identity = _profile_identity(self.path.parent, project)
        if identity is None:
            raise WebStoreError("project not found")
        domain = ("configuration_project" if action in ("pause", "resume", "delete")
                  else "execution")
        stamp = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "INSERT OR IGNORE INTO operations(actor_id,project,project_id,"
                "action,run_id,status,created_at,updated_at,idempotency_key,domain,resource_key) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (actor_id, project, identity[0], action, run_id, "pending", stamp, stamp, key,
                 domain, self._operation_resource(action, run_id)),
            )
            row = connection.execute(
                "SELECT * FROM operations WHERE actor_id=? AND idempotency_key=?",
                (actor_id, key),
            ).fetchone()
            if (
                row["project_id"] != identity[0]
                or row["action"] != action
                or row["run_id"] != run_id
            ):
                raise WebStoreError("idempotency key belongs to another operation")
            if cursor.rowcount:
                self._write_audit(
                    connection,
                    actor_id,
                    "operation-submitted",
                    project,
                    f"{action}:{run_id}",
                    payload=self._evidence(
                        connection,
                        actor_id,
                        project_id=identity[0],
                        resource_type="operation",
                        resource_id=str(row["id"]),
                        operation_id=row["id"],
                        phase="prepare",
                        result="prepared",
                    ),
                    event_key=_digest(f"operation:{row['id']}:submitted"),
                )
        return self._operation_with_current_project(row)

    def operation(self, operation_id: int) -> dict[str, Any] | None:
        """@brief Return one durable operation."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM operations WHERE id=?", (operation_id,)
            ).fetchone()
        return self._operation_with_current_project(row) if row else None

    def enqueue_configuration(self, actor_id: int, reference: str, key: str, *,
                              project_id: str | None) -> dict[str, Any]:
        """@brief Queue a protected configuration reference with explicit global/project scope.
        @param[in] reference Opaque reference to the existing protected candidate, never its data.
        @param[in] project_id Immutable project ID, or explicit None for global configuration.
        @exception WebStoreError Invalid scope, non-admin actor or conflicting idempotency key.
        """
        if (not isinstance(reference, str) or not re.fullmatch(r"[a-f0-9]{32}", reference)
                or not isinstance(key, str) or not key or len(key) > 128):
            raise WebStoreError("invalid configuration reference")
        if project_id is None:
            name, identity, domain = "", "", "configuration_global"
        else:
            if not isinstance(project_id, str) or not re.fullmatch(r"[a-f0-9]{32}", project_id):
                raise WebStoreError("invalid configuration project")
            profile = ProfileStore(self.path.parent).find_by_id(project_id)
            if profile is None:
                raise WebStoreError("project not found")
            name, identity, domain = profile.name, profile.project_id, "configuration_project"
        with self._ownership_connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            actor = connection.execute("SELECT role,disabled FROM users WHERE id=?",
                                       (actor_id,)).fetchone()
            if actor is None or actor["disabled"] or actor["role"] != "admin":
                raise WebStoreError("configuration requires an administrator")
            stamp = _now()
            cursor = connection.execute(
                "INSERT OR IGNORE INTO operations(actor_id,project,project_id,action,run_id,"
                "status,created_at,updated_at,idempotency_key,domain,resource_key) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (actor_id, name, identity, "configure", reference, "pending", stamp, stamp, key,
                 domain, "configuration:" + reference))
            row = connection.execute(
                "SELECT * FROM operations WHERE actor_id=? AND idempotency_key=?",
                (actor_id, key)).fetchone()
            if (row["project_id"], row["domain"], row["action"], row["run_id"]) != (
                    identity, domain, "configure", reference):
                raise WebStoreError("idempotency key belongs to another operation")
            if cursor.rowcount:
                self._write_audit(
                    connection, actor_id, "operation-submitted", name, "configure",
                    payload=self._evidence(connection, actor_id, project_id=identity or None,
                                           resource_type="operation", resource_id=str(row["id"]),
                                           operation_id=row["id"], phase="prepare",
                                           result="prepared"),
                    event_key=_digest(f"operation:{row['id']}:submitted"))
        return self._operation_with_current_project(row)

    def acknowledge_start(self, operation_id: int, *, owner: WorkerOwner,
                          generation: int, run_id: str, run_owner: WorkerOwner) -> None:
        """@brief Confirm Start only after exact durable run admission and pickup evidence.
        @param[in] operation_id Requested Start operation.
        @param[in] owner Current command owner.
        @param[in] generation Exact claim generation.
        @param[in] run_id Durably admitted job identity.
        @param[in] run_owner Current exclusive run owner.
        @details Completion describes admission; the subsequent job has its own lifecycle.
        """
        from adore.state import StateError, StateStore

        operation = self.authorize_effect(operation_id, owner=owner, generation=generation)
        if (not isinstance(run_owner, WorkerOwner) or run_owner.role != "run"
                or run_owner.project_id != owner.project_id or run_owner.run_id != run_id):
            raise OwnershipError("start run ownership mismatch")
        if operation["action"] != "start" or not operation["run_id"].isdigit():
            raise WebStoreError("invalid start admission")
        try:
            profiles = ProfileStore(self.path.parent)
            profile = profiles.find_by_id(operation["project_id"])
            if profile is None:
                raise WebStoreError("start project identity changed")
            state = StateStore(profile.store_root or profiles.default_store_root(profile.name))
            run = state.load(run_id)
            ticket = state.load_ticket(run_id)
            picked = any(event.get("event") == "picked"
                         and event.get("ticket") == run.ticket_iid
                         for event in state.read_journal(run_id))
            if (run.ticket_iid != int(operation["run_id"]) or ticket.get("iid") != run.ticket_iid
                    or run.lifecycle != "working"
                    or not picked):
                raise WebStoreError("start admission evidence is invalid")
        except (StateError, ProfileError, OSError, ValueError) as exc:
            raise WebStoreError("start admission evidence unavailable") from exc
        with self._ownership_connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._participant(connection, owner)
            self._participant(connection, run_owner)
            row = connection.execute(
                    "SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone()
            self._operation_owner(row, owner, generation)
            if row["status"] == "succeeded" and row["admitted_run_id"] == run_id:
                return
            if (row["status"] != "running"
                    or self._request_permission(connection, dict(row), profile)):
                raise OwnershipError("start admission ownership refused")
            connection.execute(
                "UPDATE operations SET admitted_run_id=?,run_owner_id=?,run_owner_generation=? "
                "WHERE id=?", (run_id, run_owner.id, run_owner.generation, operation_id))
            self._finish(connection, row, "succeeded", "completed")

    def operation_for_key(self, actor_id: int, key: str) -> dict | None:
        """@brief Resolve a durable idempotency key before preparing external work.
        @return Current operation or None; callers recheck immutable request binding.
        """
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM operations WHERE actor_id=? AND idempotency_key=?",
                (actor_id, key)).fetchone()
        return self._operation_with_current_project(row) if row else None

    def has_unfinished_operations(self, project: str) -> bool:
        """@brief Check for queued or executing operations before project archive."""
        identity = _profile_identity(self.path.parent, project)
        if identity is None:
            raise WebStoreError("project not found")
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT 1 FROM operations WHERE project_id=? AND status IN "
                    "('pending','running') LIMIT 1", (identity[0],),
                ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("operation storage is corrupt") from exc
        return row is not None

    def pending_domains(self, *, actions: tuple[str, ...] = ()) -> list[tuple[str, str]]:
        """@brief Discover explicit pending project domains without claiming them."""
        with self._ownership_connect() as connection:
            action_filter = ("AND action IN (" + ",".join("?" for _ in actions) + ") "
                             if actions else "")
            rows = connection.execute(
                "SELECT domain,project_id FROM operations WHERE status='pending' "
                + action_filter + "GROUP BY domain,project_id ORDER BY MIN(id)", actions).fetchall()
        return [(row["domain"], row["project_id"]) for row in rows]

    @staticmethod
    def _operation_resource(action: str, target: str) -> str:
        """@brief Normalize job identity across Retry and revision-bound Restart."""
        if not isinstance(target, str):
            raise WebStoreError("invalid operation target")
        if action == "configure":
            if not re.fullmatch(r"[a-f0-9]{32}", target):
                raise WebStoreError("invalid configuration reference")
            return "configuration:" + target
        if action == "start":
            if not re.fullmatch(r"[1-9][0-9]{0,18}", target):
                raise WebStoreError("invalid start ticket")
            return "ticket:" + target
        if action in ("retry", "restart"):
            pattern = (r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}\.[a-f0-9]{64}"
                       if action == "restart" else r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}")
            if not re.fullmatch(pattern, target):
                raise WebStoreError("invalid job target")
            run_id = target.rsplit(".", 1)[0] if action == "restart" else target
            return "job:" + run_id
        if ((action == "cancel" and not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}", target))
                or (action in ("pause", "resume") and target)
                or (action == "delete" and target not in ("", "remove-clone"))):
            raise WebStoreError("invalid operation target")
        return action + ":" + target

    @staticmethod
    def _claim_scope(owner: WorkerOwner, domain: str) -> None:
        """@brief Refuse cross-domain or implicit-project consumption."""
        if not isinstance(owner, WorkerOwner):
            raise OwnershipError("explicit worker ownership required")
        expected = ("execution" if owner.role in ("project", "run") else
                    "configuration_project" if owner.role == "configuration" and owner.project_id
                    else "configuration_global" if owner.role == "configuration" else None)
        if domain != expected:
            raise OwnershipError("worker ownership cannot consume this domain")

    def _profile_snapshot(self, project_id: str):
        """@brief Inspect local profile identity outside a SQLite writer transaction."""
        if not project_id:
            return None
        try:
            return ProfileStore(self.path.parent).find_by_id(project_id)
        except (ProfileError, OSError, ValueError):
            return "project_corrupt"

    def _request_permission(self, connection, operation: dict, profile) -> str:
        """@brief Return a closed denial after current actor/immutable-project checks."""
        actor = connection.execute("SELECT * FROM users WHERE id=?",
                                   (operation["actor_id"],)).fetchone()
        if actor is None or actor["disabled"]:
            return "permission_revoked"
        if operation["domain"] == "configuration_global":
            return "" if actor["role"] == "admin" else "permission_revoked"
        if isinstance(profile, str):
            return profile
        if profile is None:
            return "project_identity_changed"
        if profile.archived and operation["action"] != "delete":
            return "project_archived"
        if operation["domain"].startswith("configuration") and actor["role"] != "admin":
            return "permission_revoked"
        if actor["role"] == "admin":
            return ""
        grant = connection.execute(
            "SELECT profile_created_at FROM memberships WHERE user_id=? AND project_id=?",
            (actor["id"], operation["project_id"])).fetchone()
        if grant is None or grant["profile_created_at"] != profile.created_at:
            return "permission_revoked"
        return ""

    def claim_next(self, owner: WorkerOwner, *, domain: str, action: str = "",
                   actions: tuple[str, ...] = ()) -> dict[str, Any] | None:
        """@brief Atomically claim one authorized operation within the exact owner scope.
        @param[in] owner Server-issued role/project/run handle.
        @param[in] action Optional exact action filter.
        @param[in] actions Optional declared consumer action allowlist.
        @param[in] domain Explicit execution or project/global configuration domain.
        @return Claimed operation, or None; revoked requests finish without effects.
        """
        self._claim_scope(owner, domain)
        if domain == "execution":
            self.recover_interrupted(project_id=owner.project_id, role="run")
        if (not isinstance(actions, tuple) or any(item not in (
                "start", "retry", "restart", "cancel", "pause", "resume", "delete", "configure"
        ) for item in actions)):
            raise WebStoreError("invalid operation action filter")
        action_filter = ("AND o.action IN (" + ",".join("?" for _ in actions) + ") "
                         if actions else "")
        profile = self._profile_snapshot(owner.project_id)
        with self._ownership_connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._participant(connection, owner)
            running = connection.execute(
                "SELECT * FROM operations WHERE domain=? AND project_id=? AND status='running'",
                (domain, owner.project_id)).fetchall()
            for active in running:
                self._operation_record(active)
            row = connection.execute(
                "SELECT o.* FROM operations o WHERE o.status='pending' "
                "AND o.domain=? AND o.project_id=? AND (?='' OR o.action=?) "
                "AND (?='' OR o.resource_key=? OR o.resource_key=?) "
                "AND NOT EXISTS (SELECT 1 FROM operations r WHERE r.status='running' "
                "AND r.domain=o.domain AND r.project_id=o.project_id "
                "AND r.resource_key=o.resource_key) "
                "AND NOT EXISTS (SELECT 1 FROM worker_owners w WHERE w.role='run' "
                "AND w.status='active' AND w.project_id=o.project_id AND w.id<>? "
                "AND o.resource_key='job:' || w.run_id) "
                + action_filter
                + "ORDER BY CASE WHEN o.action='cancel' THEN 0 ELSE 1 END,o.id LIMIT 1",
                (domain, owner.project_id, action, action, owner.run_id,
                 "job:" + owner.run_id, "cancel:" + owner.run_id,
                 owner.id, *actions)).fetchone()
            if row is None:
                return None
            self._operation_record(row)
            if type(row["generation"]) is not int or row["generation"] < 0:
                raise WebStoreError("operation generation is corrupt")
            generation = row["generation"] + 1
            connection.execute(
                "UPDATE operations SET status='running',owner_id=?,owner_generation=?,"
                "generation=?,updated_at=? WHERE id=? AND status='pending'",
                (owner.id, owner.generation, generation, _now(), row["id"]))
            operation = {**dict(row), "status": "running", "owner_id": owner.id,
                         "owner_generation": owner.generation, "generation": generation}
            denial = self._request_permission(connection, operation, profile)
            if denial:
                self._finish(connection, operation, "failed", denial, denial)
                operation.update(status="failed", result=denial, reason=denial)
        return self._operation_with_current_project(operation)

    def authorize_effect(self, operation_id: int, *, owner: WorkerOwner,
                         generation: int, run_owner: WorkerOwner | None = None) -> dict[str, Any]:
        """@brief Recheck ownership, actor rights and project immediately before effects.
        @param[in] operation_id Exact queued operation identity.
        @param[in] owner Current command owner handle.
        @param[in] generation Exact operation claim generation.
        @param[in] run_owner Optional separately owned run scope for this child.
        @return Current authorized immutable request.
        @exception OwnershipError Stale owner, changed request or revoked access.
        """
        with self._ownership_connect() as connection:
            self._participant(connection, owner)
            row = connection.execute("SELECT * FROM operations WHERE id=?",
                                     (operation_id,)).fetchone()
            self._operation_owner(row, owner, generation)
            operation = self._operation_record(row)
            admitted = (row["status"] == "succeeded" and row["action"] == "start"
                        and row["admitted_run_id"])
            if row["status"] != "running" and not admitted:
                raise OwnershipError("operation ownership is no longer active")
            if operation["resource_key"].startswith("job:"):
                run_id = operation["resource_key"][4:]
                active = connection.execute(
                    "SELECT * FROM worker_owners WHERE role='run' AND project_id=? "
                    "AND run_id=? AND status='active'", (owner.project_id, run_id)).fetchone()
                if active is not None and active["id"] != owner.id:
                    if (not isinstance(run_owner, WorkerOwner) or run_owner.id != active["id"]
                            or run_owner.project_id != owner.project_id
                            or run_owner.run_id != run_id):
                        raise OwnershipError(
                            "operation ownership run is busy", reason="conductor_busy")
                    self._participant(connection, run_owner)
            denial = self._request_permission(
                connection, dict(row), self._profile_snapshot(row["project_id"]))
            if denial:
                raise OwnershipError("operation ownership refused: " + denial, reason=denial)
        return self._operation_with_current_project(row)

    @staticmethod
    def _operation_owner(row, owner: WorkerOwner, generation: int) -> None:
        """@brief Fence stale operation and owner generations, including terminal replay."""
        if (row is None or row["owner_id"] != owner.id
                or row["owner_generation"] != owner.generation
                or type(generation) is not int or row["generation"] != generation
                or row["project_id"] != owner.project_id):
            raise OwnershipError("operation ownership lost")
        WebStore._claim_scope(owner, row["domain"])
        if owner.role == "run" and row["resource_key"] not in (
                "job:" + owner.run_id, "cancel:" + owner.run_id):
            raise OwnershipError("operation ownership run identity changed")

    def pending_cancels(self, project: str | None = None) -> list[dict[str, Any]]:
        """@brief Inspect queued cancellations for one or every project."""
        identity = (_profile_identity(self.path.parent, project)
                    if project is not None else None)
        if project is not None and identity is None:
            raise WebStoreError("project not found")
        with self._ownership_connect() as connection:
            if project is None:
                rows = connection.execute(
                    "SELECT * FROM operations WHERE action='cancel' "
                    "AND status='pending' ORDER BY id"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM operations WHERE project_id=? AND action='cancel' "
                    "AND status='pending' ORDER BY id", (identity[0],)
                ).fetchall()
        return [self._operation_with_current_project(row) for row in rows]

    def recover_interrupted(self, *, project_id: str | None = None,
                            role: str | None = None) -> int:
        """@brief Recover only owners whose exact local process incarnations are dead.
        @param[in] project_id Optional immutable project recovery scope.
        @param[in] role Optional exact role recovery scope.
        @return Number of interrupted operations marked uncertain.
        @details Process inspection occurs before short CAS write transactions.
                 Stale heartbeat, shutdown requests and unknown probes never prove death.
        """
        with self._ownership_connect() as connection:
            owners = connection.execute(
                "SELECT * FROM worker_owners WHERE status='active' "
                "AND (? IS NULL OR project_id=?) AND (? IS NULL OR role=?)",
                (project_id, project_id, role, role)).fetchall()
            participants = connection.execute(
                "SELECT * FROM worker_processes ORDER BY owner_id,pid,birth").fetchall()
        recovered = 0
        for owner in owners:
            self._worker_record(owner)
            if owner["host"] != socket.gethostname():
                continue
            processes = [dict(row) for row in participants if row["owner_id"] == owner["id"]]
            if not processes:
                raise WebStoreError("worker ownership process evidence is corrupt")
            dead = True
            for process in processes:
                if (type(process["pid"]) is not int or process["pid"] < 1
                        or not isinstance(process["birth"], str) or not process["birth"]):
                    raise WebStoreError("worker ownership process evidence is corrupt")
                try:
                    birth = self._process_probe(process["pid"])
                except (WebStoreError, OSError):
                    dead = False
                    break
                if birth == process["birth"]:
                    dead = False
                    break
                if birth is not None and (not isinstance(birth, str) or not birth):
                    raise WebStoreError("worker process probe is corrupt")
            if not dead:
                continue
            with self._ownership_connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                current = connection.execute("SELECT * FROM worker_owners WHERE id=?",
                                             (owner["id"],)).fetchone()
                current_processes = [dict(row) for row in connection.execute(
                    "SELECT * FROM worker_processes WHERE owner_id=? ORDER BY pid,birth",
                    (owner["id"],)).fetchall()]
                if dict(current) != dict(owner) or current_processes != processes:
                    continue
                connection.execute("UPDATE worker_owners SET status='dead' WHERE id=?",
                                   (owner["id"],))
                rows = connection.execute(
                    "SELECT * FROM operations WHERE status='running' AND owner_id=? "
                    "AND owner_generation=?", (owner["id"], owner["generation"])).fetchall()
                for row in rows:
                    self._finish(
                        connection, row, "uncertain",
                        "worker stopped before outcome could be confirmed", "owner_dead")
                recovered += len(rows)
        return recovered

    def finish(self, operation_id: int, status: str, result: str, *,
               owner: WorkerOwner, generation: int, reason: str = "", detail: str = "") -> None:
        """@brief Commit a fenced observed outcome and audit atomically.
        @param[in] owner Current owner handle; terminal replay requires the same owner.
        @param[in] generation Exact operation claim generation.
        @param[in] reason Closed refusal code, excluding credentials.
        @param[in] detail Bounded, redacted engine tail.
        """
        if status not in ("succeeded", "failed", "uncertain"):
            raise WebStoreError("invalid completion status")
        try:
            with self._ownership_connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._participant(connection, owner)
                row = connection.execute(
                    "SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone()
                self._operation_owner(row, owner, generation)
                self._operation_record(row)
                if row["status"] in ("succeeded", "failed", "uncertain"):
                    if (row["status"], row["result"], row["reason"], row["detail"]) != (
                            status, result[:1000], reason[:64], detail[-2000:]):
                        raise WebStoreError("audit replay conflict")
                    return
                if row["status"] != "running":
                    raise OwnershipError("operation ownership was not claimed")
                if row["action"] == "start" and status == "succeeded":
                    raise WebStoreError("Start success requires durable run admission")
                self._finish(connection, row, status, result, reason, detail)
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("operation storage is corrupt") from exc

    def _finish(self, connection, row, status, result, reason="", detail=""):
        """@brief Confirm only observed worker outcome; arbitrary error text is excluded.
        @details Result, reason and engine detail stay on the operation row; the audit
                 evidence records only the action and its status.
        """
        connection.execute(
            "UPDATE operations SET status=?,result=?,reason=?,detail=?,updated_at=? "
            "WHERE id=?",
            (status, result[:1000], reason[:64], detail[-2000:], _now(), row["id"]),
        )
        after = (
            {"pickup": "stopped" if row["action"] == "pause" else "active"}
            if status == "succeeded" and row["action"] in ("pause", "resume")
            else None
        )
        self._write_audit(
            connection,
            row["actor_id"],
            "operation-finished",
            row["project"],
            f"{row['action']}:{status}",
            payload=self._evidence(
                connection,
                row["actor_id"],
                project_id=row["project_id"] or None,
                resource_type="operation",
                resource_id=str(row["id"]),
                operation_id=row["id"],
                result={"succeeded": "applied", "failed": "rejected", "uncertain": "uncertain"}[
                    status
                ],
                after=after,
            ),
            event_key=_digest(f"operation:{row['id']}:finished"),
        )

    def _write_audit(
        self, connection, actor_id, action, project="", detail="", *, payload=None, event_key=None,
        created_at=None,
    ) -> None:
        """@brief Persist evidence and enforce retention inside the owning transaction."""
        if (
            not isinstance(action, str)
            or not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", action)
            or not isinstance(project, str)
            or project
            and not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", project)
            or actor_id is not None
            and (type(actor_id) is not int or actor_id < 1)
        ):
            raise WebStoreError("audit row is corrupt")
        # Every audit row carries structured evidence; none is written without it.
        if payload is None:
            raise WebStoreError("audit row is corrupt")
        event_key = event_key or secrets.token_hex(32)
        try:
            audit_contract.validate(payload)
            stamp = audit_contract.instant(created_at) if created_at is not None else _now()
            encoded = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), allow_nan=False
            )
        except (ValueError, TypeError) as exc:
            raise WebStoreError("audit row is corrupt") from exc
        detail = self._safe_detail(action, detail, payload)
        try:
            connection.execute(
                "INSERT INTO audit(actor_id,action,project,detail,created_at,evidence,event_key) "
                "VALUES (?,?,?,?,?,?,?)",
                (actor_id, action, project, detail[:256], stamp, encoded, event_key),
            )
            self._prune_audit(connection)

        except sqlite3.DatabaseError as exc:
            raise WebStoreError("audit row is corrupt") from exc

    @staticmethod
    def _safe_detail(action, detail, payload=None):
        """@brief Keep recognized compact metadata; redact arbitrary or error text."""
        if not detail:
            return ""
        if action in ("config-staged", "config-applied", "config-updated"):
            return detail if payload and detail == payload["resource_id"] else "[redacted]"
        if action == "membership-changed" and re.fullmatch(
            r"(?:[0-9]+|user [0-9]+ (?:granted|removed))", detail
        ):
            return detail
        if action in ("operation-submitted", "operation-finished") and re.fullmatch(
            r"(?:(?:start|retry|cancel|pause|resume|delete):[A-Za-z0-9._-]{0,160}"
            r"|restart:[A-Za-z0-9._-]{1,160}\.[a-f0-9]{64})", detail
        ):
            return detail
        if action in (
            "user-created",
            "user-disabled",
            "user-enabled",
            "password-reset",
        ) and re.fullmatch(r"[A-Za-z0-9_]{1,64}", detail):
            return detail
        if action == "chatgpt-sign-in-failed" and (
            re.fullmatch(r"chatgpt_[a-z_]{1,48}", detail)
            or detail in {"container_runtime_unavailable", "executor_image_unavailable"}
        ):
            return detail
        return "[redacted]"

    @staticmethod
    def _validate_attempt(row):
        """@brief Validate durable replay receipt independently of retained history."""
        try:
            if (
                not re.fullmatch(r"[0-9a-f]{64}", row["event_key"])
                or type(row["actor_id"]) is not int
                or row["actor_id"] < 1
                or type(row["confirmed"]) is not int
                or row["confirmed"] not in (0, 1)
                or not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", row["action"])
                or row["project"]
                and not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", row["project"])
            ):
                raise ValueError("invalid attempt")
            audit_contract.instant(row["created_at"])
            if row["confirmed"]:
                if row["evidence"] is not None:
                    raise ValueError("completed receipt retained values")
            elif audit_contract.decode(row["evidence"])["result"] != "uncertain":
                raise ValueError("invalid attempt")
        except (ValueError, TypeError, KeyError) as exc:
            raise WebStoreError("audit row is corrupt") from exc

    def _evidence(self, connection, actor_id, **values):
        """@brief Snapshot only the validated account name and supplied server evidence."""
        row = connection.execute("SELECT username FROM users WHERE id=?", (actor_id,)).fetchone()
        try:
            return audit_contract.evidence(actor=row["username"] if row else None, **values)
        except (ValueError, TypeError) as exc:
            raise WebStoreError("audit row is corrupt") from exc

    def audit(
        self, actor_id: int | None, action: str, project: str = "", detail: str = "", **values
    ) -> None:
        """@brief Append server-owned structured evidence; values exclude request secrets."""
        confirmation_key = values.pop("confirmation_key", None)
        if confirmation_key is not None:
            identity = _profile_identity(self.path.parent, project) if project else None
            self.confirm_change(
                confirmation_key,
                after=values.get("after"),
                project_id=identity[0] if identity else None,
                detail=detail,
            )
            return
        try:
            with self._connect() as connection:
                identity = _profile_identity(self.path.parent, project) if project else None
                payload = self._evidence(
                    connection, actor_id, project_id=identity[0] if identity else None, **values
                )
                self._write_audit(connection, actor_id, action, project, detail, payload=payload)
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("audit row is corrupt") from exc

    def begin_change(
        self,
        actor_id: int,
        action: str,
        project: str = "",
        *,
        correlation: str | None = None,
        **values,
    ) -> str:
        """
        @brief Persist an uncertain filesystem attempt before changing external storage.
        @param[in] correlation Server-owned replay identity; stored only as SHA-256.
        @return Opaque correlation for confirmation after the owning mutation.
        @note Crash or exception keeps after unrecorded and result uncertain.
        """
        key = _digest(correlation) if correlation is not None else secrets.token_hex(32)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._prune_audit(connection)
                old = connection.execute(
                    "SELECT * FROM audit_attempts WHERE event_key=?", (key,)
                ).fetchone()
                if old:
                    self._validate_attempt(old)
                    if (old["actor_id"] != actor_id or old["action"] != action
                            or old["project"] != project):
                        raise WebStoreError("audit replay conflict")
                    return key
                identity = _profile_identity(self.path.parent, project) if project else None
                payload = self._evidence(
                    connection,
                    actor_id,
                    result="uncertain",
                    project_id=identity[0] if identity else None,
                    **values,
                )
                connection.execute(
                    "INSERT INTO audit_attempts(event_key,actor_id,action,project,created_at,"
                    "evidence) "
                    "VALUES (?,?,?,?,?,?)",
                    (key, actor_id, action, project, _now(), json.dumps(payload)),
                )
                self._write_audit(
                    connection, actor_id, action, project, payload=payload, event_key=key
                )
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("audit row is corrupt") from exc
        return key

    def confirm_change(
        self, key: str, *, after=None, project_id: str | None = None, detail: str = ""
    ) -> None:
        """@brief Atomically finalize one attempt and its retained evidence once."""
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._prune_audit(connection)
                row = connection.execute(
                    "SELECT * FROM audit_attempts WHERE event_key=?", (key,)
                ).fetchone()
                if row is None:
                    raise WebStoreError("audit attempt is unavailable")
                self._validate_attempt(row)
                if row["confirmed"]:
                    return
                payload = audit_contract.decode(row["evidence"])
                payload["result"] = {
                    "apply": "applied",
                    "prepare": "prepared",
                    "discard": "discarded",
                }[payload["phase"]]
                payload["after"] = audit_contract.redact(after)
                project = row["project"]
                if project_id is not None:
                    payload["project_id"] = project_id
                    item = ProfileStore(self.path.parent).find_by_id(project_id)
                    project = item.name if item else project
                    if payload["resource_type"] == "project":
                        payload["resource_id"] = project_id
                audit_contract.validate(payload)
                cursor = connection.execute(
                    "UPDATE audit SET evidence=?,detail=?,project=?,created_at=? WHERE event_key=?",
                    (
                        json.dumps(payload, sort_keys=True),
                        self._safe_detail(row["action"], detail, payload),
                        project,
                        _now(),
                        key,
                    ),
                )
                if not cursor.rowcount:
                    # Policy can remove the visible attempt before completion; confirmation
                    # is still recorded and subjected to the same explicit bounds.
                    self._write_audit(
                        connection,
                        row["actor_id"],
                        row["action"],
                        project,
                        detail,
                        payload=payload,
                        event_key=key,
                    )
                connection.execute(
                    "UPDATE audit_attempts SET confirmed=1,evidence=NULL WHERE event_key=?", (key,)
                )
                self._prune_audit(connection)
        except (sqlite3.DatabaseError, ValueError, TypeError) as exc:
            raise WebStoreError("audit row is corrupt") from exc

    @staticmethod
    def _audit_projection(row) -> dict:
        """@brief Validate one stored audit row and project its structured evidence."""
        item = dict(row)
        try:
            audit_contract.instant(item["created_at"])
            if (
                not isinstance(item["action"], str)
                or not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", item["action"])
                or not isinstance(item["detail"], str)
                or not isinstance(item["project"], str)
                or item["project"]
                and not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", item["project"])
                or type(item["id"]) is not int
                or item["actor_id"] is not None
                and type(item["actor_id"]) is not int
            ):
                raise ValueError("invalid row")
            raw = item.pop("evidence", None)
            key = item.pop("event_key", None)
            if key is not None and (
                not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key)
            ):
                raise ValueError("invalid correlation")
            if raw is None:
                raise ValueError("audit row has no evidence")
            item.update(audit_contract.decode(raw))
            item["correlation"] = key
            item["detail"] = WebStore._safe_detail(
                item["action"], item["detail"], item
            )
            return item
        except (ValueError, TypeError, KeyError) as exc:
            raise WebStoreError("audit row is corrupt") from exc

    @staticmethod
    def _audit_storage(connection):
        """@brief Reject unsupported/corrupt audit shapes on initialization and every read/write."""
        if connection.execute("PRAGMA user_version").fetchone()[0] != _SCHEMA_VERSION:
            raise WebStoreError("audit row is corrupt")
        expected = {"id", "actor_id", "action", "project", "detail", "created_at",
                    "evidence", "event_key"}
        actual = {row["name"] for row in connection.execute("PRAGMA table_info(audit)")}
        if not expected.issubset(actual):
            raise WebStoreError("audit row is corrupt")
        indexes = connection.execute("PRAGMA index_list(audit)").fetchall()
        if not any(row["unique"] and [column["name"] for column in
                   connection.execute(f"PRAGMA index_info('{row['name']}')")] == ["event_key"]
                   for row in indexes):
            raise WebStoreError("audit row is corrupt")
        columns = connection.execute("PRAGMA table_info(audit_attempts)").fetchall()
        required = {"event_key", "actor_id", "action", "project", "created_at",
                    "evidence", "confirmed"}
        if (not required.issubset({row["name"] for row in columns})
                or not any(row["name"] == "event_key" and row["pk"] == 1 for row in columns)):
            raise WebStoreError("audit row is corrupt")
        for row in connection.execute("SELECT * FROM audit_attempts"):
            WebStore._validate_attempt(row)

    @staticmethod
    def _audit_policy_row(connection: sqlite3.Connection) -> dict[str, int | None]:
        """@brief Read the singleton policy and reject corrupt persisted values."""
        row = connection.execute(
            "SELECT retention_days,max_bytes FROM audit_policy WHERE singleton=1"
        ).fetchone()
        if row is None:
            raise WebStoreError("audit policy is missing")
        values = dict(row)
        for key, maximum in (("retention_days", 36500), ("max_bytes", 1073741824)):
            value = values[key]
            if value is not None and (type(value) is not int or not 1 <= value <= maximum):
                raise WebStoreError("audit policy is corrupt")
        return values

    def audit_policy(self) -> dict[str, int | None]:
        """@brief Return the configured audit retention limits."""
        with self._connect() as connection:
            return self._audit_policy_row(connection)

    def set_audit_policy(
        self, retention_days: int | None, max_bytes: int | None, *, actor_id: int | None = None
    ) -> dict[str, int | None]:
        """@brief Atomically set audit limits and prune existing oldest events."""
        for value, maximum in ((retention_days, 36500), (max_bytes, 1073741824)):
            if value is not None and (type(value) is not int or not 1 <= value <= maximum):
                raise WebStoreError("invalid audit policy")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            before = self._audit_policy_row(connection)
            count = connection.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
            connection.execute(
                "UPDATE audit_policy SET retention_days=?,max_bytes=? WHERE singleton=1",
                (retention_days, max_bytes),
            )
            if actor_id is not None:
                self._write_audit(
                    connection,
                    actor_id,
                    "audit-policy-changed",
                    payload=self._evidence(
                        connection,
                        actor_id,
                        resource_type="policy",
                        resource_id="audit",
                        before=before,
                        after={"retention_days": retention_days, "max_bytes": max_bytes},
                    ),
                )
            else:
                self._prune_audit(connection)
            remaining = connection.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        result = {"retention_days": retention_days, "max_bytes": max_bytes}
        if actor_id is not None:
            result["deleted_events"] = max(0, count + 1 - remaining)
        return result

    def _prune_audit(self, connection: sqlite3.Connection) -> None:
        """@brief Enforce configured age and UTF-8 payload size within a transaction."""
        self._audit_storage(connection)
        policy = self._audit_policy_row(connection)
        days, byte_limit = policy["retention_days"], policy["max_bytes"]
        rows = connection.execute(
            "SELECT * FROM audit ORDER BY julianday(created_at), id"
        ).fetchall()
        cutoff = datetime.now(UTC) - timedelta(days=days) if days is not None else None
        sizes = []
        expired = []
        for row in rows:
            self._audit_projection(row)
            try:
                stamp = datetime.fromisoformat(row["created_at"])
                if stamp.tzinfo is None:
                    raise ValueError("audit timestamp lacks timezone")
                size = sum(
                    len(row[key].encode("utf-8"))
                    for key in ("action", "project", "detail", "created_at")
                )
                size += sum(
                    len((row[key] or "").encode("utf-8")) for key in ("evidence", "event_key")
                )
            except (TypeError, ValueError, AttributeError) as exc:
                raise WebStoreError("audit row is corrupt") from exc
            sizes.append((row["id"], size))
            if cutoff is not None and stamp < cutoff:
                expired.append(row["id"])
        for row_id in expired:
            connection.execute("DELETE FROM audit WHERE id=?", (row_id,))
        if byte_limit is not None:
            kept = [(row_id, size) for row_id, size in sizes if row_id not in expired]
            total = sum(size for _, size in kept)
            for row_id, size in kept:
                if total <= byte_limit:
                    break
                connection.execute("DELETE FROM audit WHERE id=?", (row_id,))
                total -= size

    def recent_audit(self, limit: int | None = 100) -> list[dict[str, Any]]:
        """@brief Return bounded recent audit rows for administrator review."""
        if limit is not None and (type(limit) is not int or not 1 <= limit <= 500):
            raise WebStoreError("invalid audit limit")
        return self.audit_page(limit, 0)[0]

    def _import_deletion_audit(self, connection) -> None:
        """@brief Atomically import local receipts without bootstrapping web identity.
        @exception WebStoreError The separate receipt store is unreadable or corrupt.
        """
        path = self.path.parent / DELETION_AUDIT_NAME
        try:
            path.stat()
            if path.is_symlink():
                raise WebStoreError("deletion audit path is a symbolic link")
        except FileNotFoundError:
            return
        except OSError as exc:
            raise WebStoreError("deletion audit unavailable") from exc
        try:
            connection.execute(
                "ATTACH DATABASE ? AS deletion_audit", (path.resolve().as_uri() + "?mode=rw",)
            )
            for database in ("main", "deletion_audit"):
                mode = connection.execute(f"PRAGMA {database}.journal_mode").fetchone()[0]
                if mode.lower() not in ("delete", "truncate", "persist"):
                    raise WebStoreError("deletion audit requires durable SQLite journal modes")
            connection.execute("BEGIN IMMEDIATE")
            for database in ("main", "deletion_audit"):
                mode = connection.execute(f"PRAGMA {database}.journal_mode").fetchone()[0]
                if mode.lower() not in ("delete", "truncate", "persist"):
                    raise WebStoreError("deletion audit requires durable SQLite journal modes")
            DeletionAudit.validate(connection, "deletion_audit")
            rows = connection.execute(
                "SELECT event_key,project,project_id,run_id,created_at,result,imported "
                "FROM deletion_audit.events WHERE dirty=1 ORDER BY created_at,event_key"
            ).fetchall()
            for row in rows:
                key, project, identity, run_id, stamp, result, imported = row
                payload = audit_contract.evidence(
                    actor=None,
                    project_id=identity,
                    resource_type="operation",
                    resource_id=run_id,
                    result=result,
                )
                if not imported:
                    self._write_audit(
                        connection, None, "job-deleted", project, payload=payload,
                        event_key=key, created_at=stamp,
                    )
                else:
                    old = connection.execute(
                        "SELECT * FROM audit WHERE event_key=?", (key,)
                    ).fetchone()
                    if old is not None:
                        prior = self._audit_projection(old)
                        if (
                            prior["action"] != "job-deleted"
                            or prior["actor_id"] is not None
                            or prior["actor"] is not None
                            or prior["project"] != project
                            or prior["project_id"] != identity
                            or prior["resource_id"] != run_id
                            or prior["result"] != "uncertain"
                            or result != "applied"
                        ):
                            raise WebStoreError("deletion audit identity conflict")
                        connection.execute(
                            "UPDATE audit SET evidence=? WHERE event_key=?",
                            (json.dumps(payload, sort_keys=True), key),
                        )
                if result == "applied":
                    connection.execute(
                        "UPDATE deletion_audit.events SET imported=1,dirty=0,project='',"
                        "project_id=NULL,run_id='' WHERE event_key=?",
                        (key,),
                    )
                else:
                    connection.execute(
                        "UPDATE deletion_audit.events SET imported=1,dirty=0 WHERE event_key=?",
                        (key,),
                    )
            connection.commit()
        except (sqlite3.Error, DeletionAuditError, ValueError, OSError) as exc:
            connection.rollback()
            raise WebStoreError("deletion audit unavailable or corrupt") from exc

    def audit_page(
        self,
        limit: int | None,
        offset: int,
        *,
        actor_id: int | None = None,
        project_id: str | None = None,
        action: str | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        project_reader: bool = False,
    ) -> tuple[list[dict], int]:
        """
        @brief Return filtered newest-first evidence and its count in one SQL snapshot.
        @param[in] limit Page size 1-500 or None for all rows.
        @param[in] offset Nonnegative number of matched rows to skip.
        @return Redacted rows and filtered total.
        @exception WebStoreError Invalid bounds/filter or corrupt persisted evidence.
        """
        if limit is not None and (type(limit) is not int or not 1 <= limit <= 500):
            raise WebStoreError("invalid audit limit")
        if type(offset) is not int or not 0 <= offset <= 2**63 - 1:
            raise WebStoreError("invalid audit offset")
        if actor_id is not None and (type(actor_id) is not int or not 1 <= actor_id <= 2**63 - 1):
            raise WebStoreError("invalid audit filter")
        if project_id is not None and (
            not isinstance(project_id, str) or not re.fullmatch(r"[0-9a-f]{32}", project_id)
        ):
            raise WebStoreError("invalid audit filter")
        if action is not None and (
            not isinstance(action, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", action)
        ):
            raise WebStoreError("invalid audit filter")
        try:
            start = audit_contract.instant(from_time) if from_time is not None else None
            end = audit_contract.instant(to_time) if to_time is not None else None
            if start and end and start >= end:
                raise ValueError("invalid period")
        except ValueError as exc:
            raise WebStoreError("invalid audit filter") from exc
        where, args = [], []
        for column, value in (
            ("actor_id", actor_id),
            ("json_extract(evidence,'$.project_id')", project_id),
            ("action", action),
        ):
            if value is not None:
                where.append(f"{column}=?")
                args.append(value)
        for operator, value in ((">=", start), ("<", end)):
            if value is not None:
                where.append(f"julianday(created_at){operator}julianday(?)")
                args.append(value)
        if project_reader:
            # Match the configuration read boundary: financial values remain Admin-only.
            where.append(
                "(json_extract(evidence,'$.resource_type') != 'config' OR "
                "json_extract(evidence,'$.resource_id') != 'budgets.max_cost_usd')"
            )
            where.append(
                "json_extract(evidence,'$.resource_type') IN ('config','project','operation')"
            )
            where.append(
                "action IN ('config-updated','config-staged','config-applied',"
                "'config-discarded','project-created','project-imported','project-cloned',"
                "'settings-imported','project-display-name-changed','project-archived',"
                "'project-restored','readiness-checked','operation-submitted',"
                "'operation-finished','project-deleted','job-deleted',"
                "'ticket-start-prepared','ticket-stopped')"
            )
        selection = " WHERE " + " AND ".join(where) if where else ""
        try:
            with self._connect() as connection:
                self._import_deletion_audit(connection)
                connection.execute("BEGIN IMMEDIATE")
                self._prune_audit(connection)
                total = connection.execute(
                    "SELECT COUNT(*) FROM audit" + selection, args
                ).fetchone()[0]
                rows = connection.execute(
                    "SELECT * FROM audit"
                    + selection
                    + " ORDER BY julianday(created_at) DESC, id DESC LIMIT ? OFFSET ?",
                    [*args, limit if limit is not None else -1, offset],
                ).fetchall()
                projected = [self._audit_projection(row) for row in rows]
                for item in projected:
                    if item["action"] == "job-deleted":
                        if item["actor_id"] is not None or item["actor"] is not None:
                            raise WebStoreError("deletion audit actor is corrupt")
                        item["resource_type"] = "job"
                    if item["action"] in ("ticket-start-prepared", "ticket-stopped"):
                        item["resource_type"] = "ticket"
                        if (
                            item["action"] == "ticket-start-prepared"
                            and item["result"] == "applied"
                        ):
                            item["phase"], item["result"] = "prepare", "prepared"
                    if item["action"] in ("operation-submitted", "operation-finished"):
                        operation = connection.execute(
                            "SELECT action,run_id,status,result,reason,project_id,actor_id "
                            "FROM operations WHERE id=?",
                            (item["operation_id"],),
                        ).fetchone()
                        if (
                            operation is None
                            or operation["action"]
                            not in (
                                "start",
                                "retry",
                                "cancel",
                                "restart",
                                "pause",
                                "resume",
                                "delete",
                            )
                            or operation["status"]
                            not in ("pending", "running", "succeeded", "failed", "uncertain")
                            or not isinstance(operation["run_id"], str)
                            or len(operation["run_id"]) > 225
                            or not isinstance(operation["result"], str)
                            or len(operation["result"]) > 1000
                            or not isinstance(operation["reason"], str)
                            or len(operation["reason"]) > 64
                            or operation["project_id"] != item["project_id"]
                            or operation["actor_id"] != item["actor_id"]
                            or item["action"] == "operation-finished"
                            and {
                                "succeeded": "applied",
                                "failed": "rejected",
                                "uncertain": "uncertain",
                            }.get(operation["status"])
                            != item["result"]
                        ):
                            raise WebStoreError("operation audit identity is corrupt")
                        target = operation["run_id"]
                        if (
                            operation["action"] == "start"
                            and target.isascii()
                            and target.isdecimal()
                            and int(target) > 0
                        ):
                            item["resource_type"], item["resource_id"] = "ticket", target
                        elif operation["action"] == "start":
                            raise WebStoreError("operation audit identity is corrupt")
                        elif operation["action"] in ("retry", "cancel", "restart"):
                            if operation["action"] == "restart" and not re.fullmatch(
                                r"[A-Za-z0-9._-]{1,160}\.[a-f0-9]{64}", target
                            ):
                                raise WebStoreError("operation audit identity is corrupt")
                            target = (
                                target.rsplit(".", 1)[0]
                                if operation["action"] == "restart"
                                else target
                            )
                            if not re.fullmatch(r"[A-Za-z0-9._-]{1,160}", target):
                                raise WebStoreError("operation audit identity is corrupt")
                            item["resource_type"], item["resource_id"] = "job", target
                        if (
                            item["action"] == "operation-finished"
                            and item["result"] == "rejected"
                            and (
                                operation["reason"]
                                in (
                                    "retry_failed",
                                    "engine_fault",
                                    "state_unavailable",
                                    "engine_setup_failed",
                                    "repository_unavailable",
                                    "executable_missing",
                                    "permission_denied",
                                    "invalid_result",
                                )
                                or operation["result"].startswith(
                                    (
                                        "retry:failed:",
                                        "start:engine_fault",
                                        "start:state_unavailable",
                                        "start:engine_setup_failed",
                                        "start:repository_unavailable",
                                        "start:workflow_unavailable",
                                        "start:invalid_result",
                                        "restart:failed",
                                    )
                                )
                            )
                        ):
                            item["result"] = "failed"
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("audit row is corrupt") from exc
        return projected, total

    def add_price(
        self,
        project: str,
        executor: str,
        model: str,
        effective_from: str,
        input_rate: str,
        output_rate: str,
        actor_id: int,
    ) -> dict[str, Any]:
        """@brief Add one immutable project/executor/model price version."""
        _price_identity(project, executor, model, effective_from)
        _price_value(input_rate)
        _price_value(output_rate)
        identity = _profile_identity(self.path.parent, project)
        if identity is None:
            raise WebStoreError("project does not exist")
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO prices(project,project_id,executor,model,effective_from,"
                    "input_usd_per_million,output_usd_per_million,actor_id,created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        project,
                        identity[0],
                        executor,
                        model,
                        effective_from,
                        input_rate,
                        output_rate,
                        actor_id,
                        _now(),
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM prices WHERE id=?", (cursor.lastrowid,)
                ).fetchone()
        except sqlite3.IntegrityError as exc:
            raise WebStoreError("price version already exists or actor is invalid") from exc
        return dict(row)

    def list_prices(self, project: str) -> list[dict[str, Any]]:
        """@brief Read every immutable price version for one project."""
        identity = _profile_identity(self.path.parent, project)
        if identity is None:
            return []
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM prices WHERE project_id=? "
                    "ORDER BY executor,model,effective_from", (identity[0],)
                ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("price storage is corrupt") from exc
        result = [dict(row) for row in rows]
        for row in result:
            _price_identity(row["project"], row["executor"], row["model"],
                            row["effective_from"])
            _price_value(row["input_usd_per_million"])
            _price_value(row["output_usd_per_million"])
        return result


# END OF FILE
