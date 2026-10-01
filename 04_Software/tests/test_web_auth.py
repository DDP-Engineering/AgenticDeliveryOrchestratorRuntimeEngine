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
@file test_web_auth.py
@brief Public authentication and durable bootstrap contract tests.
@details Exercises the web account store through account and session operations.
"""

import shutil
import sqlite3

from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.store import WebStore, WebStoreError
import pytest


def test_default_admin_is_hashed_and_preserved(tmp_path):
    """@brief A fresh install permits login and a restart preserves changes."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    assert admin["role"] == "admin"
    with sqlite3.connect(path) as connection:
        raw = connection.execute("SELECT password_hash FROM users").fetchone()[0]
    assert raw != "admin" and raw.startswith("$argon2id$")
    store.change_password(admin["id"], "admin", "replacement-long-password")
    assert WebStore(path).authenticate("admin", "replacement-long-password")
    assert WebStore(path).authenticate("admin", "admin") is None


def test_account_preferences_follow_user_and_survive_upgrade(tmp_path):
    """@brief Locale/theme belong to accounts and schema-five data survives upgrade."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    dev = store.create_user("dev", "longer-password", "developer")
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE IF EXISTS user_preferences")
        connection.execute("PRAGMA user_version=5")
    upgraded = WebStore(path)
    assert upgraded.preferences(admin["id"]) == {"language": None, "theme": None}
    assert upgraded.set_preferences(admin["id"], {"language": "ro"}) == {
        "language": "ro", "theme": None}
    assert upgraded.set_preferences(admin["id"], {"theme": "dark"}) == {
        "language": "ro", "theme": "dark"}
    assert WebStore(path).preferences(admin["id"]) == {
        "language": "ro", "theme": "dark"}
    assert WebStore(path).preferences(dev["id"]) == {
        "language": None, "theme": None}
    assert WebStore(path).authenticate("admin", "admin")


def test_account_preferences_reject_corrupt_or_unsupported_values(tmp_path):
    """@brief Invalid writes and corrupt persisted settings fail closed."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    with pytest.raises(WebStoreError):
        store.set_preferences(admin["id"], {"language": "es"})
    with pytest.raises(WebStoreError):
        store.set_preferences(admin["id"], {"theme": "neon"})
    store.set_preferences(admin["id"], {"language": "fr"})
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE user_preferences SET language='invalid'")
    with pytest.raises(WebStoreError, match="preferences"):
        store.preferences(admin["id"])


def test_schema_one_upgrade_preserves_credentials(tmp_path):
    """@brief The identity schema migration keeps a changed admin password."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    store.change_password(admin["id"], "admin", "replacement-long-password")
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE login_failures")
        connection.execute("PRAGMA user_version=1")
    upgraded = WebStore(path)
    assert upgraded.authenticate("admin", "replacement-long-password")
    assert upgraded.authenticate("admin", "admin") is None


def test_schema_three_upgrade_requires_regrant_for_name_only_memberships(tmp_path):
    """@brief Legacy name-only grants fail closed across a schema upgrade."""
    home = tmp_path / "home"
    profiles = ProfileStore(home)
    profiles.create("alpha")
    path = home / "web.db"
    store = WebStore(path)
    dev = store.create_user("dev", "longer-password", "developer")
    store.set_memberships(dev["id"], ["alpha"])
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE memberships DROP COLUMN profile_created_at")
        connection.execute("PRAGMA user_version=3")
    upgraded = WebStore(path)
    assert upgraded.memberships(dev["id"]) == set()
    upgraded.set_memberships(dev["id"], ["alpha"])
    assert upgraded.memberships(dev["id"]) == {"alpha"}
    assert upgraded.authenticate("admin", "admin")


def test_project_grant_follows_immutable_id_after_rename(tmp_path):
    """@brief A renamed project retains grants; a recycled name cannot take them."""
    home = tmp_path / "home"
    profiles = ProfileStore(home)
    original = profiles.create("alpha")
    store = WebStore(home / "web.db")
    dev = store.create_user("dev", "longer-password", "developer")
    store.set_memberships(dev["id"], ["alpha"])
    profiles.rename("alpha", "renamed")
    profiles.create("alpha")
    assert profiles.load("renamed").project_id == original.project_id
    assert store.memberships(dev["id"]) == {"renamed"}
    with sqlite3.connect(home / "web.db") as connection:
        connection.execute("UPDATE memberships SET project_id='bad' WHERE user_id=?",
                           (dev["id"],))
    with pytest.raises(WebStoreError, match="membership identity"):
        store.memberships(dev["id"])


def test_name_grant_migration_binds_matching_profile_and_quarantines_old_queue(tmp_path):
    """@brief Schema upgrade preserves proven grants and parks unsafe commands."""
    home = tmp_path / "home"
    profiles = ProfileStore(home)
    original = profiles.create("alpha")
    store = WebStore(home / "web.db")
    dev = store.create_user("dev", "longer-password", "developer")
    store.set_memberships(dev["id"], ["alpha"])
    old = store.enqueue(dev["id"], "alpha", "start", "42", "old-queue")
    with sqlite3.connect(store.path) as connection:
        connection.execute("ALTER TABLE memberships DROP COLUMN project_id")
        connection.execute("ALTER TABLE operations DROP COLUMN project_id")
        connection.execute("PRAGMA user_version=6")
    migrated = WebStore(store.path)
    assert migrated.memberships(dev["id"]) == {"alpha"}
    assert migrated.operation(old["id"])["status"] == "uncertain"
    profiles.rename("alpha", "renamed")
    assert migrated.memberships(dev["id"]) == {"renamed"}
    with sqlite3.connect(store.path) as connection:
        row = connection.execute(
            "SELECT project_id FROM memberships WHERE user_id=?", (dev["id"],)
        ).fetchone()
    assert row[0] == original.project_id


def test_schema_four_missing_membership_identity_fails_closed(tmp_path):
    """@brief A claimed current schema cannot omit its project grant key."""
    path = tmp_path / "web.db"
    WebStore(path)
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE memberships DROP COLUMN profile_created_at")
    with pytest.raises(WebStoreError, match="membership identity"):
        WebStore(path)


def test_schema_four_upgrade_adds_worker_readiness_without_resetting_admin(tmp_path):
    """@brief The readiness migration preserves changed account credentials."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    store.change_password(admin["id"], "admin", "replacement-long-password")
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE worker_heartbeat")
        connection.execute("PRAGMA user_version=4")
    upgraded = WebStore(path)
    assert upgraded.authenticate("admin", "replacement-long-password")
    assert upgraded.authenticate("admin", "admin") is None
    assert not upgraded.worker_ready()
    upgraded.touch_worker()
    assert upgraded.worker_ready()


def test_schema_nine_upgrade_adds_projection_without_resetting_admin(tmp_path):
    """@brief Usage and coverage migrations keep changed credentials intact."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    store.change_password(admin["id"], "admin", "replacement-long-password")
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE usage_projection")
        connection.execute("DROP TABLE usage_observation_projection")
        connection.execute("DROP TABLE usage_cursor")
        connection.execute("PRAGMA user_version=9")
    upgraded = WebStore(path)
    assert upgraded.authenticate("admin", "replacement-long-password")
    assert upgraded.authenticate("admin", "admin") is None
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 12
        assert connection.execute("SELECT COUNT(*) FROM usage_projection").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM usage_cursor").fetchone()[0] == 0


def test_schema_ten_upgrade_adds_coverage_cursor(tmp_path):
    """@brief Existing numeric projection survives the cursor migration."""
    path = tmp_path / "web.db"
    WebStore(path)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE usage_observation_projection")
        connection.execute("DROP TABLE usage_cursor")
        connection.execute("PRAGMA user_version=10")
    WebStore(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 12
        assert connection.execute("SELECT COUNT(*) FROM usage_projection").fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM usage_observation_projection"
        ).fetchone()[0] == 0


def test_schema_eleven_upgrade_preserves_audit_and_changed_password(tmp_path):
    """@brief Audit policy migration does not reset existing identity/history."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    store.change_password(admin["id"], "admin", "replacement-long-password")
    store.audit(admin["id"], "before-migration")
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE audit_policy")
        connection.execute("PRAGMA user_version=11")
    upgraded = WebStore(path)
    assert upgraded.authenticate("admin", "replacement-long-password")
    assert upgraded.authenticate("admin", "admin") is None
    assert upgraded.audit_policy() == {"retention_days": None, "max_bytes": None}
    assert upgraded.recent_audit()[0]["action"] == "before-migration"


def test_schema_twelve_missing_or_corrupt_policy_fails_startup(tmp_path):
    """@brief Existing v12 identity data cannot silently reset audit limits."""
    path = tmp_path / "web.db"
    WebStore(path)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE audit_policy")
    with pytest.raises(WebStoreError):
        WebStore(path)


def test_corrupt_existing_store_never_recreates_admin(tmp_path):
    """@brief Existing corrupt identity data fails closed."""
    path = tmp_path / "web.db"
    path.write_bytes(b"not sqlite")
    with pytest.raises(WebStoreError):
        WebStore(path)
    assert path.read_bytes() == b"not sqlite"


def test_deleted_identity_store_never_recreates_default_admin(tmp_path):
    """@brief A missing database after bootstrap requires explicit recovery."""
    path = tmp_path / "web.db"
    WebStore(path)
    path.unlink()
    with pytest.raises(WebStoreError, match="missing after initialization"):
        WebStore(path)


def test_stopped_service_home_copy_restores_identity_profile_and_run(tmp_path):
    """@brief A quiescent manual backup preserves all default-home evidence."""
    original = tmp_path / "original"
    profiles = ProfileStore(original)
    profiles.create("alpha")
    state = StateStore(profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="done"))
    web = WebStore(original / "web.db")
    admin = web.authenticate("admin", "admin")
    web.change_password(admin["id"], "admin", "replacement-long-password")
    web.add_price("alpha", "codex", "local-1", "2026-01-01", "2", "4", admin["id"])

    restored = tmp_path / "restored"
    shutil.copytree(original, restored)
    recovered = WebStore(restored / "web.db")
    assert recovered.authenticate("admin", "replacement-long-password")
    assert recovered.authenticate("admin", "admin") is None
    assert recovered.list_prices("alpha")[0]["input_usd_per_million"] == "2"
    assert ProfileStore(restored).load("alpha").name == "alpha"
    assert StateStore(ProfileStore(restored).default_store_root("alpha")).load(
        "run-1"
    ).lifecycle == "done"


def test_login_failure_window_is_bounded(tmp_path):
    """@brief Repeated bad credentials lock out one identity and client."""
    store = WebStore(tmp_path / "web.db")
    for _ in range(5):
        assert store.allow_login("admin", "local")
        store.record_login("admin", "local", success=False)
    assert not store.allow_login("admin", "local")
    assert store.allow_login("admin", "another-client")


def test_sessions_and_disabled_accounts(tmp_path):
    """@brief Sessions can be revoked and disabled users cannot sign in."""
    store = WebStore(tmp_path / "web.db")
    admin = store.authenticate("admin", "admin")
    token, csrf = store.create_session(admin["id"])
    assert csrf and store.session_user(token)["username"] == "admin"
    store.revoke_session(token)
    assert store.session_user(token) is None
    user = store.create_user("dev", "longer-password", "developer")
    assert store.authenticate("dev", "longer-password")
    store.disable_user(user["id"])
    assert store.authenticate("dev", "longer-password") is None
    store.enable_user(user["id"])
    assert store.authenticate("dev", "longer-password") is not None
    with pytest.raises(WebStoreError, match="last administrator"):
        store.disable_user(admin["id"])


def test_admin_password_reset_revokes_sessions(tmp_path):
    """@brief Recovery sets a fresh hash and invalidates old sessions."""
    store = WebStore(tmp_path / "web.db")
    user = store.create_user("dev", "longer-password", "developer")
    token, _csrf = store.create_session(user["id"])
    store.reset_password(user["id"], "new-long-password")
    assert store.session_user(token) is None
    assert store.authenticate("dev", "longer-password") is None
    assert store.authenticate("dev", "new-long-password")
    with pytest.raises(WebStoreError, match="8 characters"):
        store.reset_password(user["id"], "short")
    with pytest.raises(WebStoreError, match="user not found"):
        store.reset_password(999, "new-long-password")
