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

# IMPORTS
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import re
import secrets
import sqlite3
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from adore import metrics
from adore.profiles import ProfileError, ProfileStore

# CONSTANTS
_HASHER = PasswordHasher()
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
    UNIQUE(actor_id, idempotency_key)
);
CREATE TABLE audit (
    id INTEGER PRIMARY KEY, actor_id INTEGER, action TEXT NOT NULL,
    project TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
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
CREATE TABLE worker_heartbeat (
    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
    updated_at TEXT NOT NULL
);
CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    language TEXT, theme TEXT
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
_PREFERENCES_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    language TEXT, theme TEXT
)
"""
_PRICE_SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY, project TEXT NOT NULL, executor TEXT NOT NULL,
    model TEXT NOT NULL, effective_from TEXT NOT NULL,
    input_usd_per_million TEXT NOT NULL,
    output_usd_per_million TEXT NOT NULL,
    actor_id INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL,
    UNIQUE(project, executor, model, effective_from)
)
"""


# DATA MODELS / TYPEDEFINITIONS
class WebStoreError(RuntimeError):
    """@brief Corrupt or unsupported web storage and invalid account actions."""


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
    result = {"language": row["language"], "theme": row["theme"]}
    if (result["language"] not in (None, "en", "fr", "de", "ro")
            or result["theme"] not in (None, "light", "dark", "system")):
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

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        new = not self.path.exists()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        marker = self.path.with_name(self.path.name + ".initialized")
        if new and marker.exists():
            raise WebStoreError("web database missing after initialization")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version == 0 and new:
                    for statement in _SCHEMA.split(";"):
                        if statement.strip():
                            connection.execute(statement)
                    connection.execute(
                        "INSERT INTO users(username,password_hash,role,created_at) "
                        "VALUES (?,?,?,?)",
                        ("admin", _HASHER.hash("admin"), "admin", _now()),
                    )
                    connection.execute("PRAGMA user_version=13")
                elif version == 1:
                    connection.execute(
                        "CREATE TABLE login_failures (identity_hash TEXT PRIMARY KEY, "
                        "failures INTEGER NOT NULL, window_started TEXT NOT NULL)"
                    )
                    connection.execute(_PRICE_SCHEMA)
                elif version == 2:
                    connection.execute(_PRICE_SCHEMA)
                elif version not in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13):
                    raise WebStoreError("unsupported or corrupt web database schema")
                if version in (1, 2, 3):
                    columns = {row[1] for row in connection.execute(
                        "PRAGMA table_info(memberships)"
                    ).fetchall()}
                    if "profile_created_at" not in columns:
                        connection.execute(
                            "ALTER TABLE memberships ADD COLUMN "
                            "profile_created_at TEXT NOT NULL DEFAULT ''"
                        )
                    # Legacy name-only grants cannot prove which incarnation
                    # of a profile they belonged to; require administrator regrant.
                    connection.execute(
                        "DELETE FROM memberships WHERE profile_created_at=''"
                    )
                    connection.execute("PRAGMA user_version=4")
                if version in (1, 2, 3, 4):
                    connection.execute(
                        "CREATE TABLE IF NOT EXISTS worker_heartbeat ("
                        "singleton INTEGER PRIMARY KEY CHECK(singleton=1), "
                        "updated_at TEXT NOT NULL)"
                    )
                    connection.execute("PRAGMA user_version=5")
                if version in (1, 2, 3, 4, 5):
                    connection.execute(_PREFERENCES_SCHEMA)
                    connection.execute("PRAGMA user_version=6")
                if version in (1, 2, 3, 4, 5, 6):
                    columns = {row[1] for row in connection.execute(
                        "PRAGMA table_info(memberships)"
                    ).fetchall()}
                    if "project_id" not in columns:
                        connection.execute(
                            "ALTER TABLE memberships ADD COLUMN "
                            "project_id TEXT NOT NULL DEFAULT ''"
                        )
                    for row in connection.execute(
                        "SELECT user_id,project,profile_created_at FROM memberships"
                    ).fetchall():
                        identity = _profile_identity(self.path.parent, row["project"])
                        if identity is None or identity[1] != row["profile_created_at"]:
                            connection.execute(
                                "DELETE FROM memberships WHERE user_id=? AND project=?",
                                (row["user_id"], row["project"]),
                            )
                        else:
                            connection.execute(
                                "UPDATE memberships SET project_id=? "
                                "WHERE user_id=? AND project=?",
                                (identity[0], row["user_id"], row["project"]),
                            )
                    connection.execute("PRAGMA user_version=7")
                if version in (1, 2, 3, 4, 5, 6, 7):
                    columns = {row[1] for row in connection.execute(
                        "PRAGMA table_info(operations)"
                    ).fetchall()}
                    if "project_id" not in columns:
                        connection.execute(
                            "ALTER TABLE operations ADD COLUMN "
                            "project_id TEXT NOT NULL DEFAULT ''"
                        )
                    # Old queued commands carry only a mutable profile label.
                    # Their target cannot be proven after a rename/replacement.
                    connection.execute(
                        "UPDATE operations SET status='uncertain', "
                        "result='project identity needs operator reconciliation', "
                        "updated_at=? WHERE status IN ('pending','running') "
                        "AND project_id=''",
                        (_now(),),
                    )
                    connection.execute("PRAGMA user_version=8")
                if version in (1, 2, 3, 4, 5, 6, 7, 8):
                    # Preserve legacy rates, but attach only rows whose creation
                    # follows the current profile's creation stamp. Older rates
                    # stay visible in the database for manual reconciliation.
                    connection.execute(
                        "CREATE TABLE prices_next ("
                        "id INTEGER PRIMARY KEY, project TEXT NOT NULL, "
                        "project_id TEXT NOT NULL, executor TEXT NOT NULL, "
                        "model TEXT NOT NULL, effective_from TEXT NOT NULL, "
                        "input_usd_per_million TEXT NOT NULL, "
                        "output_usd_per_million TEXT NOT NULL, "
                        "actor_id INTEGER NOT NULL REFERENCES users(id), "
                        "created_at TEXT NOT NULL, "
                        "UNIQUE(project_id,executor,model,effective_from))"
                    )
                    for row in connection.execute("SELECT * FROM prices").fetchall():
                        identity = _profile_identity(self.path.parent, row["project"])
                        bound = (identity[0] if identity is not None
                                 and row["created_at"] >= identity[1]
                                 else f"legacy-unbound-{row['id']}")
                        connection.execute(
                            "INSERT INTO prices_next VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (row["id"], row["project"], bound, row["executor"],
                             row["model"], row["effective_from"],
                             row["input_usd_per_million"],
                             row["output_usd_per_million"], row["actor_id"],
                             row["created_at"]),
                        )
                    connection.execute("DROP TABLE prices")
                    connection.execute("ALTER TABLE prices_next RENAME TO prices")
                    connection.execute("PRAGMA user_version=9")
                if version in (1, 2, 3, 4, 5, 6, 7, 8, 9):
                    connection.execute(
                        "CREATE TABLE IF NOT EXISTS usage_projection ("
                        "project_id TEXT NOT NULL, run_id TEXT NOT NULL, "
                        "source_id TEXT NOT NULL, event_json TEXT NOT NULL, "
                        "PRIMARY KEY(project_id,run_id,source_id))"
                    )
                    connection.execute("PRAGMA user_version=10")
                if version in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
                    connection.execute(
                        "CREATE TABLE IF NOT EXISTS usage_observation_projection ("
                        "project_id TEXT NOT NULL, run_id TEXT NOT NULL, "
                        "source_id TEXT NOT NULL, event_json TEXT NOT NULL, "
                        "PRIMARY KEY(project_id,run_id,source_id))"
                    )
                    connection.execute(
                        "CREATE TABLE IF NOT EXISTS usage_cursor ("
                        "project_id TEXT NOT NULL, run_id TEXT NOT NULL, "
                        "journal_length INTEGER NOT NULL, "
                        "journal_sha256 TEXT NOT NULL, "
                        "PRIMARY KEY(project_id,run_id))"
                    )
                    connection.execute("PRAGMA user_version=11")
                if version in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
                    connection.execute(
                        "CREATE TABLE IF NOT EXISTS audit_policy ("
                        "singleton INTEGER PRIMARY KEY CHECK(singleton=1), "
                        "retention_days INTEGER, max_bytes INTEGER)"
                    )
                    connection.execute(
                        "INSERT OR IGNORE INTO audit_policy(singleton,retention_days,max_bytes) "
                        "VALUES (1,NULL,NULL)"
                    )
                    connection.execute("PRAGMA user_version=12")
                if version in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
                    if "password_change_required" not in {
                        row[1] for row in connection.execute(
                            "PRAGMA table_info(users)"
                        ).fetchall()
                    }:
                        connection.execute(
                            "ALTER TABLE users ADD COLUMN "
                            "password_change_required INTEGER NOT NULL DEFAULT 0"
                        )
                    connection.execute("PRAGMA user_version=13")
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
                if "project_id" not in {
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(prices)"
                    ).fetchall()
                }:
                    raise WebStoreError("web database missing price identity")
                if not {"user_id", "language", "theme"}.issubset({
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
                self._audit_policy_row(connection)
                if connection.execute(
                    "SELECT COUNT(*) FROM users WHERE role='admin' AND disabled=0"
                ).fetchone()[0] < 1:
                    raise WebStoreError("web database has no active administrator")
            if not marker.exists():
                marker.write_text("ADORE web identity store initialized\n", encoding="utf-8")
        except sqlite3.DatabaseError as exc:
            raise WebStoreError(f"web database is corrupt: {exc}") from exc

    def touch_worker(self) -> None:
        """@brief Record that the single control worker is still operating."""
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO worker_heartbeat(singleton,updated_at) VALUES(1,?) "
                    "ON CONFLICT(singleton) DO UPDATE SET updated_at=excluded.updated_at",
                    (_now(),),
                )
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("worker heartbeat storage is corrupt") from exc

    def clear_worker(self) -> None:
        """@brief Remove worker readiness after graceful shutdown."""
        try:
            with self._connect() as connection:
                connection.execute("DELETE FROM worker_heartbeat WHERE singleton=1")
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("worker heartbeat storage is corrupt") from exc

    def worker_ready(self, *, max_age_seconds: int = 10) -> bool:
        """@brief Report a recent worker heartbeat, rejecting corrupt timestamps."""
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT updated_at FROM worker_heartbeat WHERE singleton=1"
                ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("worker heartbeat storage is corrupt") from exc
        if row is None:
            return False
        try:
            stamp = datetime.fromisoformat(row["updated_at"])
            if stamp.tzinfo is None:
                raise ValueError("missing timezone")
            age = (datetime.now(UTC) - stamp).total_seconds()
        except (TypeError, ValueError, OverflowError) as exc:
            raise WebStoreError("worker heartbeat timestamp is corrupt") from exc
        if age < -5:
            raise WebStoreError("worker heartbeat is in the future")
        return age <= max_age_seconds

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
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=10000")
            with connection:
                yield connection
        finally:
            connection.close()

    def reconcile_usage(self, project_id: str, run_id: str,
                        journal: list[dict]) -> list[dict]:
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
            for index, event in enumerate(source):
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
                incoming = event.get("tokens_in", 0)
                outgoing = event.get("tokens_out", 0)
                money = event.get("cost_usd", 0)
                if (type(incoming) is not int or incoming < 0
                        or type(outgoing) is not int or outgoing < 0
                        or type(money) not in (int, float) or money < 0
                        or not math.isfinite(money)):
                    raise WebStoreError("malformed usage amounts")
                key = event.get("event_id", f"legacy:{index}")
                if not isinstance(key, str) or len(key) > 200:
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
                        raise WebStoreError("projected usage is absent from journal")
                    prefix = json.dumps(journal[:prior_length], sort_keys=True,
                                        separators=(",", ":"), allow_nan=False)
                    if hashlib.sha256(prefix.encode()).hexdigest() != prior_digest:
                        raise WebStoreError("usage journal changed before cursor")
                prior = {row["source_id"]: row["event_json"] for row in
                         connection.execute(
                             "SELECT source_id,event_json FROM usage_projection "
                             "WHERE project_id=? AND run_id=?",
                             (project_id, run_id),
                         ).fetchall()}
                if set(prior) - {key for key, _payload, _event in usage}:
                    raise WebStoreError("projected usage is absent from journal")
                for key, payload, _event in usage:
                    if key in prior and prior[key] != payload:
                        raise WebStoreError("conflicting projected usage")
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
                if set(prior_observations) - set(observations):
                    raise WebStoreError("projected observation is absent from journal")
                for key, (_value, payload) in observations.items():
                    if key in prior_observations and prior_observations[key] != payload:
                        raise WebStoreError("conflicting projected observation")
                    if key not in prior_observations:
                        connection.execute(
                            "INSERT INTO usage_observation_projection"
                            "(project_id,run_id,source_id,event_json) VALUES(?,?,?,?)",
                            (project_id, run_id, key, payload),
                        )
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

    def create_user(self, username: str, password: str, role: str) -> dict[str, Any]:
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
                    "INSERT INTO users(username,password_hash,role,created_at) "
                    "VALUES (?,?,?,?)",
                    (username, _HASHER.hash(password), role, _now()),
                )
                row = connection.execute(
                    "SELECT * FROM users WHERE id=?", (cursor.lastrowid,)
                ).fetchone()
            return _user(row)
        except sqlite3.IntegrityError as exc:
            raise WebStoreError("username already exists") from exc

    def list_users(self) -> list[dict[str, Any]]:
        """@brief List accounts without their password hashes."""
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM users ORDER BY username").fetchall()
        return [_user(row) for row in rows]

    def user_by_id(self, user_id: int) -> dict[str, Any] | None:
        """@brief Recheck the actor before worker execution."""
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return _user(row) if row is not None else None

    def disable_user(self, user_id: int) -> None:
        """@brief Disable an account and revoke its sessions."""
        with self._connect() as connection:
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

    def enable_user(self, user_id: int) -> None:
        """@brief Re-enable an existing account without restoring old sessions."""
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE users SET disabled=0 WHERE id=?", (user_id,)
            )
            if cursor.rowcount != 1:
                raise WebStoreError("user not found")

    def change_password(self, user_id: int, old: str, new: str) -> None:
        """@brief Change own password, satisfy any reset marker and revoke sessions."""
        if len(new) < 8:
            raise WebStoreError("password must contain at least 8 characters")
        with self._connect() as connection:
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

    def reset_password(self, user_id: int, replacement: str) -> None:
        """@brief Set a recovery password the target must replace; revoke its sessions."""
        if len(replacement) < 8:
            raise WebStoreError("password must contain at least 8 characters")
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE users SET password_hash=?, password_change_required=1 WHERE id=?",
                (_HASHER.hash(replacement), user_id),
            )
            if cursor.rowcount != 1:
                raise WebStoreError("user not found")
            connection.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))

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
        """@brief Read one user's language and theme, or nullable fallbacks."""
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT p.language,p.theme FROM users u LEFT JOIN "
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
        if (not updates or set(updates) - {"language", "theme"}
                or any(key == "language" and value not in ("en", "fr", "de", "ro")
                       or key == "theme" and value not in ("light", "dark", "system")
                       for key, value in updates.items())):
            raise WebStoreError("invalid account preferences")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT p.language,p.theme FROM users u LEFT JOIN "
                    "user_preferences p ON p.user_id=u.id WHERE u.id=?",
                    (user_id,),
                ).fetchone()
                if row is None:
                    raise WebStoreError("user not found")
                values = {**_preferences(row), **updates}
                connection.execute(
                    "INSERT INTO user_preferences(user_id,language,theme) VALUES(?,?,?) "
                    "ON CONFLICT(user_id) DO UPDATE SET "
                    "language=excluded.language,theme=excluded.theme",
                    (user_id, values["language"], values["theme"]),
                )
        except sqlite3.DatabaseError as exc:
            raise WebStoreError("account preferences storage is corrupt") from exc
        return values

    def set_memberships(self, user_id: int, projects: list[str]) -> None:
        """@brief Replace a developer's project grants atomically."""
        grants = []
        for project in sorted(set(projects)):
            identity = _profile_identity(self.path.parent, project)
            if identity is None:
                raise WebStoreError("project not found")
            grants.append((user_id, project, identity[1], identity[0]))
        with self._connect() as connection:
            if connection.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone() is None:
                raise WebStoreError("user not found")
            connection.execute("DELETE FROM memberships WHERE user_id=?", (user_id,))
            connection.executemany(
                "INSERT INTO memberships(user_id,project,profile_created_at,project_id) "
                "VALUES (?,?,?,?)", grants,
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

    def set_membership(self, user_id: int, project: str, granted: bool) -> None:
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
                if connection.execute("SELECT 1 FROM users WHERE id=?",
                                      (user_id,)).fetchone() is None:
                    raise WebStoreError("user not found")
                rows = connection.execute(
                    "SELECT project,profile_created_at,project_id FROM memberships WHERE user_id=?",
                    (user_id,),
                ).fetchall()
                grants = [(user_id, profile.name, profile.created_at, profile.project_id)
                          for profile in self._granted_projects(rows, by_id)
                          if profile.project_id != identity[0]]
                if granted:
                    grants.append((user_id, project, identity[1], identity[0]))
                connection.execute("DELETE FROM memberships WHERE user_id=?", (user_id,))
                connection.executemany(
                    "INSERT INTO memberships(user_id,project,profile_created_at,project_id) "
                    "VALUES (?,?,?,?)", grants,
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

    def _operation_with_current_project(self, row: sqlite3.Row) -> dict[str, Any]:
        """@brief Resolve a queued command's immutable target to its current label."""
        operation = dict(row)
        project_id = operation["project_id"]
        if not project_id:
            return operation  # Historical terminal row without proven identity.
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

    def enqueue(self, actor_id: int, project: str, action: str,
                run_id: str, key: str) -> dict[str, Any]:
        """@brief Persist an idempotent operation request."""
        if (action not in ("start", "retry", "cancel", "pause", "resume", "delete")
                or not key or len(key) > 128):
            raise WebStoreError("invalid operation")
        identity = _profile_identity(self.path.parent, project)
        if identity is None:
            raise WebStoreError("project not found")
        stamp = _now()
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO operations(actor_id,project,project_id,"
                "action,run_id,status,created_at,updated_at,idempotency_key) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (actor_id, project, identity[0], action, run_id,
                 "pending", stamp, stamp, key),
            )
            row = connection.execute(
                "SELECT * FROM operations WHERE actor_id=? AND idempotency_key=?",
                (actor_id, key),
            ).fetchone()
            if (row["project_id"] != identity[0] or row["action"] != action
                    or row["run_id"] != run_id):
                raise WebStoreError("idempotency key belongs to another operation")
        return self._operation_with_current_project(row)

    def operation(self, operation_id: int) -> dict[str, Any] | None:
        """@brief Return one durable operation."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM operations WHERE id=?", (operation_id,)
            ).fetchone()
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

    def claim_next(self) -> dict[str, Any] | None:
        """@brief Atomically claim one pending operation for the worker."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM operations WHERE status='pending' "
                "ORDER BY CASE WHEN action='cancel' THEN 0 ELSE 1 END,id LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE operations SET status='running', updated_at=? WHERE id=?",
                (_now(), row["id"]),
            )
        return {**self._operation_with_current_project(row), "status": "running"}

    def pending_cancels(self, project: str | None = None) -> list[dict[str, Any]]:
        """@brief Inspect queued cancellations for one or every project."""
        identity = (_profile_identity(self.path.parent, project)
                    if project is not None else None)
        if project is not None and identity is None:
            raise WebStoreError("project not found")
        with self._connect() as connection:
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

    def recover_interrupted(self) -> int:
        """@brief Mark pre-restart running operations uncertain, never replay them."""
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE operations SET status='uncertain', "
                "result='worker stopped before outcome could be confirmed', "
                "updated_at=? WHERE status='running'", (_now(),)
            )
        return cursor.rowcount

    def finish(self, operation_id: int, status: str, result: str) -> None:
        """@brief Record a bounded worker result."""
        if status not in ("succeeded", "failed", "uncertain"):
            raise WebStoreError("invalid completion status")
        with self._connect() as connection:
            connection.execute(
                "UPDATE operations SET status=?,result=?,updated_at=? WHERE id=?",
                (status, result[:1000], _now(), operation_id),
            )

    def audit(self, actor_id: int | None, action: str, project: str = "",
              detail: str = "") -> None:
        """@brief Append a compact non-secret audit event."""
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO audit(actor_id,action,project,detail,created_at) "
                "VALUES (?,?,?,?,?)", (actor_id, action, project, detail[:256], _now())
            )
            self._prune_audit(connection)

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

    def set_audit_policy(self, retention_days: int | None,
                         max_bytes: int | None) -> dict[str, int | None]:
        """@brief Atomically set audit limits and prune existing oldest events."""
        for value, maximum in ((retention_days, 36500), (max_bytes, 1073741824)):
            if value is not None and (type(value) is not int or not 1 <= value <= maximum):
                raise WebStoreError("invalid audit policy")
        with self._connect() as connection:
            self._audit_policy_row(connection)
            connection.execute(
                "UPDATE audit_policy SET retention_days=?,max_bytes=? WHERE singleton=1",
                (retention_days, max_bytes),
            )
            self._prune_audit(connection)
        return {"retention_days": retention_days, "max_bytes": max_bytes}

    def _prune_audit(self, connection: sqlite3.Connection) -> None:
        """@brief Enforce configured age and UTF-8 payload size within a transaction."""
        policy = self._audit_policy_row(connection)
        days, byte_limit = policy["retention_days"], policy["max_bytes"]
        if days is None and byte_limit is None:
            return
        rows = connection.execute(
            "SELECT id,action,project,detail,created_at FROM audit ORDER BY id"
        ).fetchall()
        cutoff = datetime.now(UTC) - timedelta(days=days) if days is not None else None
        sizes = []
        expired = []
        for row in rows:
            try:
                stamp = datetime.fromisoformat(row["created_at"])
                if stamp.tzinfo is None:
                    raise ValueError("audit timestamp lacks timezone")
                size = sum(len(row[key].encode("utf-8")) for key in
                           ("action", "project", "detail", "created_at"))
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

    def audit_page(self, limit: int | None, offset: int) -> tuple[list[dict[str, Any]], int]:
        """
        @brief Return one newest-first slice of retained audit rows and their total.
        @param[in] limit Rows to return (1-500), or None for every row after offset.
        @param[in] offset Rows to skip from the newest.
        @return (rows, total retained rows).
        @exception WebStoreError Invalid bounds or a corrupt audit row.
        """
        if limit is not None and (type(limit) is not int or not 1 <= limit <= 500):
            raise WebStoreError("invalid audit limit")
        if type(offset) is not int or offset < 0:
            raise WebStoreError("invalid audit offset")
        with self._connect() as connection:
            self._prune_audit(connection)
            total = connection.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
            rows = connection.execute(
                "SELECT a.id,u.username AS actor,a.action,a.project,a.detail,"
                "a.created_at FROM audit a LEFT JOIN users u ON u.id=a.actor_id "
                "ORDER BY a.id DESC LIMIT ? OFFSET ?",
                (limit if limit is not None else -1, offset),
            ).fetchall()
        for row in rows:
            try:
                stamp = datetime.fromisoformat(row["created_at"])
                if stamp.tzinfo is None:
                    raise ValueError("audit timestamp lacks timezone")
            except (TypeError, ValueError) as exc:
                raise WebStoreError("audit row is corrupt") from exc
        return [dict(row) for row in rows], total

    def add_price(self, project: str, executor: str, model: str,
                  effective_from: str, input_rate: str, output_rate: str,
                  actor_id: int) -> dict[str, Any]:
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
                    (project, identity[0], executor, model, effective_from,
                     input_rate, output_rate, actor_id, _now()),
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
