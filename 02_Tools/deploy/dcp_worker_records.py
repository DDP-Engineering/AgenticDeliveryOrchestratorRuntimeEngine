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
@file    dcp_worker_records.py
@brief   Perform the explicitly authorized DCP worker-record maintenance once.
@details Operator tool for the November 2026 worker deployment, not an application
         migration or compatibility reader. Requires stopped ADORE services,
         schema 16 input, schema 18 application and a private existing backup.
         Preserves accounts, history and configuration; refuses active work.
"""

# IMPORTS
import argparse
from dataclasses import fields
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile

from adore.profiles import ProfileStore
from adore.state import RunState
from adore.web.configuration import ConfigurationTasks
from adore.web.store import WebStore, _SCHEMA, _SCHEMA_VERSION


# HELPER FUNCTIONS
def atomic_bytes(path: Path, raw: bytes) -> None:
    """@brief Replace one private operator-maintained file atomically."""
    descriptor, name = tempfile.mkstemp(prefix=".operator-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


# PUBLIC API
def main() -> None:
    """@brief Back up and rewrite only the inspected stopped DCP records."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--backup", required=True, type=Path)
    parser.add_argument("--authorize-record-rewrite", action="store_true", required=True)
    args = parser.parse_args()
    home, backup = args.home.resolve(strict=True), args.backup.resolve(strict=True)
    if not home.is_dir() or not backup.is_dir() or backup.is_relative_to(home):
        raise RuntimeError("independent existing home and backup directories required")
    if backup.stat().st_mode & 0o077 or _SCHEMA_VERSION != 18:
        raise RuntimeError("private backup and exact schema-18 application required")
    for unit in ("adore-web.service", "adore-web-worker.service"):
        state = subprocess.check_output(
            ["systemctl", "show", unit, "-p", "ActiveState", "--value"], text=True,
            timeout=10,
        ).strip()
        if state != "inactive":
            raise RuntimeError("both ADORE services must be inactive")

    profiles = ProfileStore(home)
    replacements = []
    known = {field.name for field in fields(RunState)}
    for profile in profiles.list_profiles():
        root = Path(profile.store_root or profiles.default_store_root(profile.name))
        for path in sorted((root / "runs").glob("*/state.json")):
            raw = path.read_bytes()
            value = json.loads(raw)
            if value.get("lifecycle") not in ("done", "failed", "cancelled", "handed-off"):
                raise RuntimeError("nonterminal run requires operator resolution first")
            if known - set(value) != {"execution_pending"} or set(value) - known:
                raise RuntimeError("unexpected stored run shape; no guessed defaults allowed")
            value["execution_pending"] = False
            RunState.from_dict(value)
            replacements.append((path, raw, (json.dumps(value, indent=2) + "\n").encode()))

    original = home / "web.db"
    old = sqlite3.connect(f"file:{original}?mode=ro", uri=True)
    old.row_factory = sqlite3.Row
    if old.execute("PRAGMA user_version").fetchone()[0] != 16:
        raise RuntimeError("only the inspected DCP schema-16 database is authorized")
    if old.execute("SELECT 1 FROM operations WHERE status IN ('pending','running')").fetchone():
        raise RuntimeError("unfinished operations cannot be rewritten")
    saved = sqlite3.connect(backup / "web-stopped.db")
    old.backup(saved)
    saved.close()
    os.chmod(backup / "web-stopped.db", 0o600)
    archive = backup / "home-stopped.tar.gz"
    if archive.exists():
        raise RuntimeError("backup archive already exists")
    subprocess.run(
        ["tar", "-czf", str(archive), "-C", str(home), "--exclude=./repos",
         "--exclude=./profiles/*/worktrees", "--exclude=./operator-backups",
         "--exclude=./deploy-backup-*", "."], check=True, timeout=180,
    )
    os.chmod(archive, 0o600)

    descriptor, name = tempfile.mkstemp(prefix=".web-schema18-", suffix=".db", dir=home)
    os.close(descriptor)
    pending = Path(name)
    new = sqlite3.connect(pending)
    new.row_factory = sqlite3.Row
    try:
        new.executescript(_SCHEMA)
        new.execute("DELETE FROM audit_policy")
        targets = {row[0] for row in new.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        results = []
        counts = {}
        for table, in old.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            if table == "worker_heartbeat":
                continue
            if table not in targets:
                raise RuntimeError("unexpected source table")
            source_columns = [row[1] for row in old.execute(f'PRAGMA table_info("{table}")')]
            target_columns = [row[1] for row in new.execute(f'PRAGMA table_info("{table}")')]
            if table != "operations" and source_columns != target_columns:
                raise RuntimeError("unexpected shared table shape")
            rows = old.execute(f'SELECT * FROM "{table}"').fetchall()
            counts[table] = len(rows)
            for row in rows:
                value = dict(row)
                if table == "operations":
                    action = value["action"]
                    if action == "image-build":
                        reference = hashlib.sha256(
                            f'dcp-historical-image-build:{value["id"]}'.encode()).hexdigest()[:32]
                        value["action"], value["run_id"] = "configure", reference
                        value["detail"] += " [operator-retained image-build history]"
                        results.append((reference, {
                            "schema": 1, "operation_id": value["id"],
                            "status_code": 200 if value["status"] == "succeeded" else 409,
                            "body": {"previous_action": action, "result": value["result"]},
                        }))
                    elif action not in ("start", "retry", "restart", "cancel",
                                        "pause", "resume", "delete"):
                        raise RuntimeError("unexpected historical operation")
                    value.update(
                        domain="execution" if value["action"] in (
                            "start", "retry", "restart", "cancel") else "configuration_project",
                        owner_id=None, owner_generation=None, generation=0,
                        admitted_run_id="", run_owner_id="", run_owner_generation=0,
                        resource_key=WebStore._operation_resource(value["action"], value["run_id"]),
                    )
                columns = list(value)
                quoted = ",".join('"' + column + '"' for column in columns)
                placeholders = ",".join("?" for _ in columns)
                new.execute(f'INSERT INTO "{table}" ({quoted}) VALUES ({placeholders})',
                            [value[column] for column in columns])
            if table != "operations":
                copied = new.execute(f'SELECT * FROM "{table}"').fetchall()
                if [tuple(row) for row in rows] != [tuple(row) for row in copied]:
                    raise RuntimeError("shared records changed unexpectedly")
        new.execute("PRAGMA user_version=18")
        if new.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("prepared database failed integrity check")
        if new.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("prepared database has foreign-key violations")
        new.commit()
        new.close()
        prepared = WebStore(pending)
        with prepared._connect() as connection:
            for row in connection.execute("SELECT * FROM operations"):
                prepared._operation_record(row)
        directory = home / "configuration-tasks"
        directory.mkdir(mode=0o700, exist_ok=True)
        for reference, result in results:
            path = directory / (reference + ".result.json")
            if path.exists():
                raise RuntimeError("historical result already exists")
            atomic_bytes(path, json.dumps(result).encode())
        for path, before, after in replacements:
            if path.read_bytes() != before:
                raise RuntimeError("run changed while services were stopped")
            atomic_bytes(path, after)
        old.close()
        os.replace(pending, original)
        active = WebStore(original)
        tasks = ConfigurationTasks(profiles, active)
        with active._connect() as connection:
            for row in connection.execute("SELECT * FROM operations WHERE action='configure'"):
                tasks.outcome(dict(row))
        print(json.dumps({"schema": 18, "preserved_rows": counts,
                          "run_records_updated": len(replacements),
                          "historical_image_results": len(results), "backup": str(backup)}))
    finally:
        old.close()
        new.close()
        pending.unlink(missing_ok=True)
        pending.with_name(pending.name + ".initialized").unlink(missing_ok=True)


if __name__ == "__main__":
    main()

# END OF FILE
