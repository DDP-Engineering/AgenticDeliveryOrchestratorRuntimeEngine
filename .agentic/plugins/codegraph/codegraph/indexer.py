#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file indexer.py
@brief Explicit indexing: incremental updates, rebuilds and cross-file labels.
@details A run checks the write preconditions, takes the writer lock,
         re-extracts only files whose content, extractor revision or module
         name changed, and publishes one complete generation in a single
         transaction with a new random snapshot ID. Cross-file resolution
         labels are recomputed for every reference at each publication from
         the binding evidence extraction recorded. A rebuild builds a
         temporary database, validates it, recovers or discards the old file
         together with its journal, then replaces it.
"""

# IMPORTS

from __future__ import annotations

import collections
import datetime
import hashlib
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path

from codegraph import config, natives, python_extract, safety, scope, store
from codegraph.config import Settings
from codegraph.safety import Refused

# CONSTANTS

MAX_WORKERS = 4
MAX_CANDIDATES = 5
HOOK_KILL = "CODEGRAPH_TEST_KILL_AT"
HOOK_PAUSE = "CODEGRAPH_TEST_PAUSE_FILE"
HOOK_FAIL_REBUILD = "CODEGRAPH_TEST_FAIL_REBUILD"
HOOK_WAIT_SECONDS = 120
#: name prefix of the database a build writes before it replaces the target
TEMP_PREFIX = ".codegraph-rebuild-"

# HELPER FUNCTIONS


def _hook_kill(point: str) -> None:
    """@brief Test-only: end the process abruptly at a named point."""
    if os.environ.get(HOOK_KILL) == point:
        os._exit(97)


def _hook_pause() -> None:
    """@brief Test-only: announce `<file>.waiting`, then wait until `<file>` exists."""
    path = os.environ.get(HOOK_PAUSE)
    if not path:
        return
    Path(path + ".waiting").write_text("waiting", encoding="utf-8")
    end = time.monotonic() + HOOK_WAIT_SECONDS
    while not Path(path).exists() and time.monotonic() < end:
        time.sleep(0.05)


def _now() -> str:
    """@brief Current UTC time in the protocol's ISO 8601 form."""
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")
    return stamp.replace("+00:00", "Z")


def _module_prefixes(qualname: str) -> list[str]:
    """@brief `a`, `a.b`, ... for a dotted name."""
    parts = qualname.split(".")
    return [".".join(parts[:index]) for index in range(1, len(parts) + 1)]


def _resolve(conn: sqlite3.Connection) -> None:
    """
    @brief Recompute every reference's label, target and candidates.
    @details Only `direct-syntax` and `lexical-binding` set a target; name-only
             matches become ranked candidates (at most five) and are never
             promoted to confirmed links, even when there is a single match.
    """
    rows = conn.execute("SELECT s.id, s.kind, s.name, s.qualified_name, s.depth, f.module, "
                        "f.path FROM symbols s JOIN files f ON f.id = s.file_id").fetchall()
    by_qualified: dict[str, str] = {}
    modules: set[str] = set()
    by_name: dict[str, list[tuple]] = collections.defaultdict(list)
    for sid, kind, name, qualified, depth, module, path in rows:
        by_qualified.setdefault(qualified, sid)
        if kind == "module":
            modules.add(qualified)
        if kind in store.CANDIDATE_KINDS or (kind == "variable" and depth == 1):
            by_name[name].append((sid, module, path))

    def candidates(name: str, module: str, first: str | None = None) -> list[str]:
        package = module.rsplit(".", 1)[0] if "." in module else ""
        ranked = sorted(by_name.get(name, []), key=lambda item: (
            0 if item[1] == module else 1 if package and item[1].startswith(package + ".")
            or item[1] == package else 2, item[2], item[0]))
        chosen = [first] if first else []
        chosen += [sid for sid, _module, _path in ranked if sid not in chosen]
        return chosen[:MAX_CANDIDATES]

    def indexed_prefix(qualname: str) -> bool:
        return any(prefix in modules for prefix in _module_prefixes(qualname))

    updates, offered = [], []
    refs = conn.execute("SELECT r.rowid, r.kind, r.spelling, r.binding, r.local_target, "
                        "r.qualname, f.module FROM refs r JOIN files f ON f.id = r.file_id")
    for rowid, kind, spelling, binding, local, qualname, module in refs.fetchall():
        label, target, choices = "unresolved", None, []
        if binding == "local" and local:
            label, target = "lexical-binding", local
        elif binding == "import" and qualname:
            if kind == "import" and (qualname in modules or qualname in by_qualified):
                label, target = "direct-syntax", by_qualified.get(qualname)
            elif kind != "import" and qualname in by_qualified:
                label, target = "lexical-binding", by_qualified[qualname]
            elif not indexed_prefix(qualname):
                label = "external"
        elif binding == "builtin":
            label = "external"
        elif binding in ("self", "attribute", "unbound"):
            name = spelling.rsplit(".", 1)[-1]
            first = by_qualified.get(qualname) if binding == "self" and qualname else None
            choices = candidates(name, module, first)
            if choices:
                label = "candidate"
        updates.append((label, target, rowid))
        offered += [(rowid, sid, rank) for rank, sid in enumerate(choices)]
    conn.execute("DELETE FROM candidates")
    conn.executemany("UPDATE refs SET label = ?, target_id = ? WHERE rowid = ?", updates)
    conn.executemany("INSERT INTO candidates(ref_rowid, symbol_id, rank) VALUES (?, ?, ?)",
                     offered)


def _insert_facts(conn: sqlite3.Connection, file_id: int, facts) -> None:
    """@brief Insert one file's symbols and references."""
    conn.executemany(
        "INSERT INTO symbols(id, file_id, parent_id, kind, name, qualified_name, signature, "
        "start_line, start_column, end_line, end_column, depth, words) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(s.id, file_id, s.parent_id, s.kind, s.name, s.qualified_name, s.signature,
          s.start_line, s.start_column, s.end_line, s.end_column, s.depth,
          store.identifier_words(s.name)) for s in facts.symbols])
    conn.executemany(
        "INSERT INTO refs(file_id, from_id, kind, spelling, line, column, binding, "
        "local_target, qualname) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(file_id, r.from_id, r.kind, r.spelling, r.line, r.column, r.binding,
          r.local_target, r.qualname) for r in facts.references])


def _generation(target: Path) -> int:
    """@brief Generation of an existing readable CodeGraph database, else 0."""
    conn, _state = store.open_reader(target)
    if conn is None:
        return 0
    try:
        return int(store.read_meta(conn).get("generation", 0))
    except (sqlite3.Error, ValueError):
        return 0
    finally:
        conn.close()


def _publish(conn: sqlite3.Connection, settings: Settings, selection, identity: str,
             reuse: bool, should_stop, progress, generation_base: int = 0) -> dict:
    """
    @brief Extract what changed and publish one generation; returns counts and meta.
    @param[in] generation_base Generation of the database being replaced, when not reusing.
    """
    roots = python_extract.import_roots(settings, selection.manifests)
    existing = {}
    if reuse:
        existing = {row[1]: (row[0], *row[2:]) for row in conn.execute(
            "SELECT id, path, sha256, extractor, module, status, role FROM files")}
    current, jobs, reused, roles = {}, [], 0, []
    for item in selection.files:
        if should_stop():
            raise python_extract.Cancelled()
        data = (settings.root / item.path).read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        module = python_extract.module_name(item.path, roots)
        current[item.path] = (item, sha, module)
        old = existing.get(item.path)
        if (old and old[1:4] == (sha, python_extract.EXTRACTOR_REVISION, module)
                and old[4] != "failed"):
            reused += 1
            if old[5] != item.role:
                roles.append((item.role, old[0]))
        else:
            jobs.append((item.path, data, module))
    facts = {}
    if jobs:
        workers = min(MAX_WORKERS, os.cpu_count() or 1, len(jobs))
        with python_extract.ExtractorPool(workers, settings.parse_timeout_seconds) as pool:
            for done, fact in enumerate(pool.extract_all(jobs, should_stop=should_stop), 1):
                facts[fact.path] = fact
                progress("extract", done, len(jobs))
    _hook_kill("before_publish")
    _hook_pause()
    if should_stop():
        raise python_extract.Cancelled()
    previous = store.read_meta(conn) if reuse else {}
    if os.environ.get(HOOK_KILL) == "after_insert":
        conn.execute("PRAGMA cache_size=1")  # test-only: spill pages so the kill leaves a hot journal
    conn.execute("BEGIN IMMEDIATE")
    try:
        keep = set(current) | set(selection.skipped)
        for path, (fid, *_rest) in existing.items():
            if path not in keep or path in facts or path in selection.skipped:
                conn.execute("DELETE FROM refs WHERE file_id = ?", (fid,))
                conn.execute("DELETE FROM symbols WHERE file_id = ?", (fid,))
            if path not in keep:
                conn.execute("DELETE FROM files WHERE id = ?", (fid,))
        for path, fact in facts.items():
            item, sha, module = current[path]
            conn.execute(
                "INSERT INTO files(path, role, language, sha256, size, status, reason, extractor, "
                "module) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(path) DO UPDATE SET "
                "role=excluded.role, language=excluded.language, sha256=excluded.sha256, "
                "size=excluded.size, status=excluded.status, reason=excluded.reason, "
                "extractor=excluded.extractor, module=excluded.module",
                (path, item.role, item.language, sha, item.size, fact.status, fact.reason,
                 python_extract.EXTRACTOR_REVISION, module))
            fid = conn.execute("SELECT id FROM files WHERE path = ?", (path,)).fetchone()[0]
            _insert_facts(conn, fid, fact)
        conn.executemany("UPDATE files SET role = ? WHERE id = ?", roles)
        for path, reason in selection.skipped.items():
            size = (settings.root / path).stat().st_size
            conn.execute(
                "INSERT INTO files(path, role, language, sha256, size, status, reason) "
                "VALUES (?, 'source', 'unsupported', NULL, ?, 'skipped', ?) ON CONFLICT(path) "
                "DO UPDATE SET sha256=NULL, size=excluded.size, status='skipped', "
                "reason=excluded.reason", (path, size, reason))
        _hook_kill("after_insert")
        conn.execute("DELETE FROM manifests")
        conn.executemany("INSERT INTO manifests(path, sha256) VALUES (?, ?)",
                         scope.manifest_hashes(settings, selection.manifests).items())
        progress("resolve", 0, 1)
        _resolve(conn)
        if should_stop():
            raise python_extract.Cancelled()
        meta = {"snapshot": secrets.token_hex(16),
                "generation": str(int(previous.get("generation", generation_base)) + 1),
                "indexed_at": _now(), "config_digest": config.ingestion_digest(settings),
                "extractor": python_extract.EXTRACTOR_REVISION,
                "plugin_version": str(natives.read_manifest().get("plugin_version", "0")),
                "inventory": selection.inventory, "import_roots": json.dumps(roots)}
        conn.execute("DELETE FROM meta")
        conn.executemany("INSERT INTO meta(key, value) VALUES (?, ?)", meta.items())
        if safety.plugin_identity() != identity:
            raise Refused("plugin_changed", "the plugin's files changed during indexing; "
                                            "nothing was published - index again")
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    counts = collections.Counter(fact.status for fact in facts.values())
    return {
        "files": {"indexed": len(facts), "reused": reused, "partial": counts["partial"],
                  "failed": counts["failed"], "skipped": len(selection.skipped)},
        "symbols": conn.execute("SELECT count(*) FROM symbols").fetchone()[0],
        "references": conn.execute("SELECT count(*) FROM refs").fetchone()[0],
        "meta": {"snapshot": meta["snapshot"], "generation": int(meta["generation"]),
                 "indexed_at": meta["indexed_at"]},
    }


def _rebuild(settings: Settings, selection, identity: str, should_stop, progress) -> dict:
    """@brief Build into a temporary file, validate, then replace the target."""
    target = settings.database
    temporary = target.parent / f"{TEMP_PREFIX}{secrets.token_hex(8)}.tmp"
    try:
        conn = store.open_writer(temporary)
        try:
            store.initialize(conn)
            if os.environ.get(HOOK_FAIL_REBUILD):
                raise RuntimeError("test hook: rebuild failure")
            result = _publish(conn, settings, selection, identity, False, should_stop, progress,
                              _generation(target))
        finally:
            conn.close()
        check = sqlite3.connect(temporary)
        try:
            healthy = (check.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                       and check.execute("PRAGMA user_version").fetchone()[0]
                       == store.SCHEMA_VERSION)
        finally:
            check.close()
        if not healthy or store.header_kind(temporary) != "codegraph":
            raise Refused("internal", "the rebuilt database failed validation; "
                                      "the previous database was kept")
        if target.exists():
            try:
                old = sqlite3.connect(target, isolation_level=None)
                try:
                    old.execute("PRAGMA user_version").fetchone()
                finally:
                    old.close()
            except sqlite3.DatabaseError:
                pass
        # Whatever journal is still beside the target belongs to the file being
        # discarded - or to one already gone; it must not meet the new database.
        Path(str(target) + "-journal").unlink(missing_ok=True)
        safety.replace_file(temporary, target)
        return result
    finally:
        temporary.unlink(missing_ok=True)
        Path(str(temporary) + "-journal").unlink(missing_ok=True)

# PUBLIC API


def run_index(settings: Settings, rebuild: bool = False, should_stop=None,
              progress=None) -> dict:
    """
    @brief Index the configured scope, creating or updating the database.
    @param[in] rebuild Build a fresh database and replace the existing one.
    @param[in] should_stop Optional callable; True cancels before publication.
    @param[in] progress Optional callable(phase, done, total) for progress output.
    @return File, symbol and reference counts plus the published `meta`.
    @exception Refused when a precondition or the publication refuses.
    @exception scope.ScopeError when the scope is missing or cannot be listed.
    @exception python_extract.Cancelled when should_stop requested cancellation.
    """
    started = time.monotonic()
    should_stop = should_stop or (lambda: False)
    progress = progress or (lambda *_args: None)
    if not natives.capability()["indexing_supported"]:
        raise Refused("indexing_unsupported", "this Python has no matching vendored parser; "
                                              "queries still work")
    safety.require_ignored_storage(settings)
    scope.require_scope(settings)   # before the lock creates anything
    with safety.WriterLock(settings.storage):
        safety.require_ownership(settings.database)
        identity = safety.plugin_identity()
        selection = scope.select(settings)
        for stale in settings.storage.glob(f"{TEMP_PREFIX}*"):
            stale.unlink(missing_ok=True)   # left by a killed build; the lock makes it stale
        result = None
        if not rebuild and store.header_kind(settings.database) == "codegraph":
            conn = store.open_writer(settings.database)
            try:
                if conn.execute("PRAGMA user_version").fetchone()[0] == store.SCHEMA_VERSION:
                    result = _publish(conn, settings, selection, identity, True, should_stop,
                                      progress)
            finally:
                conn.close()
        if result is None:
            # a first build, a rebuild and an unsupported schema all build aside, so an
            # interrupted run never leaves a half-made file at the target
            result = _rebuild(settings, selection, identity, should_stop, progress)
    result["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return result

# END OF FILE
