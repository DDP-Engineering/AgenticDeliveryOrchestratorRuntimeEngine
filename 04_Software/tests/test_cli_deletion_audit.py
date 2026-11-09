#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""@file test_cli_deletion_audit.py
@brief Offline CLI deletion and durable History boundary tests.
@details Fake resource cleanup and temporary profile homes avoid real services.
"""

from adore.cli import main
from adore.state import StateStore
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest

from tests.test_web_tickets import _admin, _project, _run


def test_cli_delete_survives_job_removal_without_web_bootstrap(tmp_path, monkeypatch):
    """@brief A CLI deletion before web setup appears once after web initialization."""
    profiles = _project(tmp_path)
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    run_id = _run(tmp_path, 12, "failed")
    state = StateStore(tmp_path / "state")

    class Engine:
        """@brief Emulate owned cleanup without invoking any real resources."""

        def delete(self, run_id, *, owned_resources=False):
            state.delete_run(run_id)

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", lambda *a, **kw: Engine())
    assert main(["--profile", "alpha", "delete", run_id, "--force"]) == 0
    assert not state.exists(run_id)
    assert not (profiles.home / "web.db").exists()
    with TestClient(create_app(profiles.home)) as client:
        _admin(client)
        for _ in range(2):
            rows = client.get("/api/v1/audit-page?limit=all").json()["items"]
            deleted = [row for row in rows if row["action"] == "job-deleted"]
            assert len(deleted) == 1
            assert deleted[0]["actor_id"] is None
            assert deleted[0]["resource_id"] == run_id
            assert deleted[0]["result"] == "applied"


def test_cli_delete_refuses_corrupt_audit_before_cleanup(tmp_path, monkeypatch):
    """@brief Corrupt audit evidence is never overwritten and leaves the job intact."""
    profiles = _project(tmp_path)
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    run_id = _run(tmp_path, 12, "failed")
    ledger = profiles.home / "deletion-audit.db"
    ledger.write_bytes(b"corrupt")
    calls = []

    class Engine:
        """@brief A called delete would indicate lost fail-closed behavior."""

        def delete(self, run_id, *, owned_resources=False):
            calls.append(run_id)

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", lambda *a, **kw: Engine())
    assert main(["--profile", "alpha", "delete", run_id, "--force"]) != 0
    assert not calls
    assert StateStore(tmp_path / "state").exists(run_id)
    assert ledger.read_bytes() == b"corrupt"


def test_interrupted_deletion_keeps_uncertain_evidence(tmp_path, monkeypatch):
    """@brief Failed cleanup does not claim deletion even after History reads the attempt."""
    from adore.state import StateError

    profiles = _project(tmp_path)
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    run_id = _run(tmp_path, 12, "failed")
    app = create_app(profiles.home)

    class Engine:
        """@brief Interrupt after another reader has imported the initial receipt."""

        def delete(self, run_id, *, owned_resources=False):
            assert app.state.web_store.recent_audit(None)[0]["result"] == "uncertain"
            raise StateError("injected cleanup interruption")

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", lambda *a, **kw: Engine())
    assert main(["--profile", "alpha", "delete", run_id, "--force"]) != 0
    assert StateStore(tmp_path / "state").exists(run_id)
    rows = [r for r in app.state.web_store.recent_audit(None) if r["action"] == "job-deleted"]
    assert len(rows) == 1 and rows[0]["result"] == "uncertain"


def test_history_refreshes_attempt_after_confirmed_deletion(tmp_path, monkeypatch):
    """@brief A receipt imported during cleanup becomes applied once, after success."""
    profiles = _project(tmp_path)
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    run_id = _run(tmp_path, 12, "failed")
    app = create_app(profiles.home)

    class Engine:
        """@brief Observe the pre-cleanup event and remove only isolated job state."""

        def delete(self, run_id, *, owned_resources=False):
            assert app.state.web_store.recent_audit(None)[0]["result"] == "uncertain"
            StateStore(tmp_path / "state").delete_run(run_id)

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", lambda *a, **kw: Engine())
    assert main(["--profile", "alpha", "delete", run_id, "--force"]) == 0
    rows = [r for r in app.state.web_store.recent_audit(None) if r["action"] == "job-deleted"]
    assert len(rows) == 1 and rows[0]["result"] == "applied"


def test_unsupported_ledger_names_the_file_and_keeps_job(tmp_path, monkeypatch, capsys):
    """@brief An unsupported ledger is refused with the explicit fresh-store path."""
    import sqlite3

    profiles = _project(tmp_path)
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    run_id = _run(tmp_path, 12, "failed")
    with sqlite3.connect(profiles.home / "deletion-audit.db") as db:
        db.execute("PRAGMA user_version=99")
    monkeypatch.setattr("adore.cli.Orchestrator.from_config", lambda *a, **kw: object())
    assert main(["--profile", "alpha", "delete", run_id, "--force"]) != 0
    assert "deletion-audit.db" in capsys.readouterr().out
    assert StateStore(tmp_path / "state").exists(run_id)


def test_confirm_failure_reports_job_was_removed(tmp_path, monkeypatch, capsys):
    """@brief Post-delete audit failure never claims that the job was retained."""
    from adore.deletion_audit import DeletionAuditError

    profiles = _project(tmp_path)
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    run_id = _run(tmp_path, 12, "failed")

    class Engine:
        def delete(self, run_id, *, owned_resources=False):
            StateStore(tmp_path / "state").delete_run(run_id)

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", lambda *a, **kw: Engine())

    def fail(*args):
        raise DeletionAuditError("injected")

    monkeypatch.setattr("adore.cli.DeletionAudit.confirm", fail)
    assert main(["--profile", "alpha", "delete", run_id, "--force"]) != 0
    output = capsys.readouterr().out
    assert "deleted" in output and "uncertain" in output
    assert not StateStore(tmp_path / "state").exists(run_id)


def test_impossible_ledger_state_refuses_before_delete(tmp_path, monkeypatch):
    """@brief An impossible stored receipt cannot disappear silently from History."""
    import sqlite3

    from adore.deletion_audit import DeletionAudit

    profiles = _project(tmp_path)
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    run_id = _run(tmp_path, 12, "failed")
    ledger = DeletionAudit(profiles.home)
    ledger.begin("alpha", profiles.load("alpha").project_id, run_id)
    with sqlite3.connect(ledger.path) as db:
        db.execute("UPDATE events SET dirty=0,imported=0")
    calls = []

    class Engine:
        def delete(self, run_id, *, owned_resources=False):
            calls.append(run_id)

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", lambda *a, **kw: Engine())
    assert main(["--profile", "alpha", "delete", run_id, "--force"]) != 0
    assert not calls and StateStore(tmp_path / "state").exists(run_id)


def test_existing_web_store_deletion_uses_projection_cleanup_and_audit(tmp_path, monkeypatch):
    """@brief The normal CLI callback removes source and records one event."""
    profiles = _project(tmp_path)
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    run_id = _run(tmp_path, 12, "failed")
    app = create_app(profiles.home)

    class Engine:
        on_delete = None

        def delete(self, run_id, *, owned_resources=False):
            self.on_delete(run_id, lambda: StateStore(tmp_path / "state").delete_run(run_id))

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", lambda *a, **kw: Engine())
    assert main(["--profile", "alpha", "delete", run_id, "--force"]) == 0
    rows = [r for r in app.state.web_store.recent_audit(None) if r["action"] == "job-deleted"]
    assert len(rows) == 1 and rows[0]["result"] == "applied"


def test_import_refuses_wal_without_losing_unimported_evidence(tmp_path, monkeypatch):
    """@brief Non-atomic multi-database journaling fails closed without scrubbing the receipt."""
    import sqlite3

    from adore.deletion_audit import DeletionAudit
    from adore.web.store import WebStore, WebStoreError
    import pytest

    profiles = _project(tmp_path)
    ledger = DeletionAudit(profiles.home)
    key = ledger.begin("alpha", profiles.load("alpha").project_id, "job-12")
    ledger.confirm(key)
    web = WebStore(profiles.home / "web.db")
    with sqlite3.connect(web.path) as db:
        db.execute("PRAGMA journal_mode=WAL")
    with pytest.raises(WebStoreError):
        web.recent_audit(None)
    with sqlite3.connect(ledger.path) as db:
        assert db.execute("SELECT run_id,imported FROM events").fetchone() == ("job-12", 0)


def test_import_rejects_changed_identity(tmp_path):
    """@brief Imported uncertain evidence cannot be rebound to a different job."""
    import sqlite3

    from adore.deletion_audit import DeletionAudit
    from adore.web.store import WebStore, WebStoreError
    import pytest

    profiles = _project(tmp_path)
    ledger = DeletionAudit(profiles.home)
    key = ledger.begin("alpha", profiles.load("alpha").project_id, "job-12")
    web = WebStore(profiles.home / "web.db")
    assert web.recent_audit(None)[0]["result"] == "uncertain"
    ledger.confirm(key)
    with sqlite3.connect(ledger.path) as db:
        db.execute("UPDATE events SET run_id='other-job'")
    with pytest.raises(WebStoreError):
        web.recent_audit(None)


def test_delayed_import_obeys_timestamp_order_and_paging(tmp_path):
    """@brief A late import does not move an older deletion ahead of newer web changes."""
    import sqlite3

    from adore.deletion_audit import DeletionAudit
    from adore.web.store import WebStore

    profiles = _project(tmp_path)
    ledger = DeletionAudit(profiles.home)
    key = ledger.begin("alpha", profiles.load("alpha").project_id, "job-12")
    ledger.confirm(key)
    with sqlite3.connect(ledger.path) as db:
        db.execute("UPDATE events SET created_at='2000-01-01T00:00:00+00:00'")
    web = WebStore(profiles.home / "web.db")
    web.audit(1, "login")
    first, total = web.audit_page(1, 0)
    last, _ = web.audit_page(1, 1)
    assert total == 2 and first[0]["action"] == "login" and last[0]["action"] == "job-deleted"


def test_history_rejects_invented_cli_actor(tmp_path):
    """@brief Corrupted CLI evidence cannot impersonate a web account."""
    import json
    import sqlite3

    from adore.deletion_audit import DeletionAudit
    from adore.web.store import WebStore, WebStoreError
    import pytest

    profiles = _project(tmp_path)
    ledger = DeletionAudit(profiles.home)
    key = ledger.begin("alpha", profiles.load("alpha").project_id, "job-12")
    ledger.confirm(key)
    web = WebStore(profiles.home / "web.db")
    web.recent_audit(None)
    with sqlite3.connect(web.path) as db:
        raw = db.execute("SELECT evidence FROM audit WHERE action='job-deleted'").fetchone()[0]
        evidence = json.loads(raw)
        evidence["actor"] = "admin"
        db.execute(
            "UPDATE audit SET evidence=? WHERE action='job-deleted'", (json.dumps(evidence),)
        )
    with pytest.raises(WebStoreError):
        web.recent_audit(None)


def test_delete_refuses_audit_permission_error(tmp_path, monkeypatch):
    """@brief Unwritable audit storage blocks cleanup and retains the job."""
    import sqlite3

    profiles = _project(tmp_path)
    monkeypatch.setenv("ADORE_HOME", str(profiles.home))
    run_id = _run(tmp_path, 12, "failed")
    calls = []

    class Engine:
        def delete(self, run_id, *, owned_resources=False):
            calls.append(run_id)

    monkeypatch.setattr("adore.cli.Orchestrator.from_config", lambda *a, **kw: Engine())
    real_connect = sqlite3.connect

    def denied(database, *args, **kwargs):
        if str(database).endswith("deletion-audit.db"):
            raise PermissionError("injected audit permission")
        return real_connect(database, *args, **kwargs)

    monkeypatch.setattr("adore.deletion_audit.sqlite3.connect", denied)
    assert main(["--profile", "alpha", "delete", run_id, "--force"]) != 0
    assert not calls and StateStore(tmp_path / "state").exists(run_id)


@pytest.mark.parametrize("policy", ["age", "size"])
def test_delayed_import_retention_keeps_newer_event(tmp_path, policy):
    """@brief Delayed old receipts never evict a newer event under retention limits."""
    import sqlite3

    from adore.deletion_audit import DeletionAudit
    from adore.web.store import WebStore

    profiles = _project(tmp_path)
    ledger = DeletionAudit(profiles.home)
    key = ledger.begin("alpha", profiles.load("alpha").project_id, "job-12")
    ledger.confirm(key)
    with sqlite3.connect(ledger.path) as db:
        db.execute("UPDATE events SET created_at='2000-01-01T00:00:00+00:00'")
    web = WebStore(profiles.home / "web.db")
    web.audit(1, "login")
    with sqlite3.connect(web.path) as db:
        row = db.execute(
            "SELECT action,project,detail,created_at,evidence,event_key FROM audit"
        ).fetchone()
        size = sum(len((value or "").encode("utf-8")) for value in row)
    web.set_audit_policy(1 if policy == "age" else None, size if policy == "size" else None)
    assert [row["action"] for row in web.recent_audit(None)] == ["login"]
