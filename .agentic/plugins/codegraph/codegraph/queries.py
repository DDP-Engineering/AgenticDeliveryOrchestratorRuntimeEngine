#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file queries.py
@brief Read-only CodeGraph queries: status, check, find, file, symbol, callers, refs.
@details Every query opens the database through a read-only connection and
         never writes, creates or repairs anything. Results cite source
         ranges; cited files are hashed again so a location from a file that
         changed since indexing is marked stale instead of reported as
         current. Ordinary queries therefore report freshness
         `not_fully_checked`; only `check` inspects the whole scope. Budgets
         and paging are applied to the final rendering.
"""

# IMPORTS

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import time
from pathlib import Path

from codegraph import config, protocol, safety, scope, store
from codegraph.python_extract import EXTRACTOR_REVISION

# CONSTANTS

HOOK_EDIT_DURING_CHECK = "CODEGRAPH_TEST_EDIT_DURING_CHECK"
MIN_DISPLAY = 10
HEX = re.compile(r"[0-9a-f]+")
SYMBOL_COLUMNS = ("s.id, s.kind, s.name, s.qualified_name, s.signature, f.path, s.start_line, "
                  "s.start_column, s.end_line, s.end_column, f.role, f.language, s.depth")
REF_COLUMNS = "r.rowid, r.kind, r.spelling, f.path, r.line, r.column, r.label, r.target_id, r.from_id"
MESSAGES = {
    "missing": "No CodeGraph index yet. Run know_graph_index, or use ordinary search.",
    "incompatible": "The CodeGraph database is not usable here. Run know_graph_index "
                    "--rebuild, or use ordinary search.",
    "busy": "The CodeGraph database is busy. Try again shortly, or use ordinary search.",
    "needs_recovery": "An indexing run was interrupted. Run know_graph_index to recover, "
                      "or use ordinary search.",
}
#: kinds an outline shows; parameters and locals are left to `symbol`
LISTED_KINDS = ("module", "class", "function", "method")
#: the bounds a request may set: records per answer, and the smallest byte budget
MAX_LIMIT = 200
MIN_BYTES = 512

# HELPER FUNCTIONS


class _Answer:
    """One query: settings, arguments, connection, and the envelope helpers."""

    def __init__(self, action: str, settings: config.Settings, args, capability: dict,
                 view_name: str) -> None:
        self.action = action
        self.settings = settings
        self.args = args
        self.capability = capability
        self.view_name = view_name
        self.limit = getattr(args, "limit", None) or settings.max_results
        self.max_bytes = getattr(args, "max_bytes", None) or settings.max_output_bytes
        self.conn: sqlite3.Connection | None = None
        self.meta: dict = {}
        self.hashes: dict[str, str | None] = {}
        self.displays: dict[str, str] = {}

    def invalid(self) -> str | None:
        """@brief Why the requested budgets cannot be served, or None."""
        limit, max_bytes = getattr(self.args, "limit", None), getattr(self.args, "max_bytes", None)
        if limit is not None and not 1 <= limit <= MAX_LIMIT:
            return f"--limit must be 1 through {MAX_LIMIT}"
        if max_bytes is not None and max_bytes < MIN_BYTES:
            return f"--max-bytes must be at least {MIN_BYTES}"
        return None

    def envelope(self, status: str = "ok", **fields) -> dict:
        """@brief An envelope for this action with the served generation."""
        if self.conn is not None:
            fields.setdefault("index", "ready")
            fields.setdefault("freshness", "not_fully_checked")
            fields.setdefault("meta", {key: self.meta.get(key) for key in
                                       ("snapshot", "generation", "indexed_at")})
        return protocol.envelope(self.action, status, capability=self.capability, **fields)

    # citations and display IDs

    def citation(self, path: str, recorded: str | None) -> str:
        """@brief `current` when the file still hashes as indexed, else `stale`."""
        if path not in self.hashes:
            try:
                self.hashes[path] = hashlib.sha256(
                    (self.settings.root / path).read_bytes()).hexdigest()
            except OSError:
                self.hashes[path] = None
        return "current" if recorded and self.hashes[path] == recorded else "stale"

    def display(self, sid: str | None) -> str | None:
        """@brief Shortest unique prefix of at least 10 characters."""
        if not sid:
            return None
        if sid not in self.displays:
            for length in range(MIN_DISPLAY, len(sid) + 1):
                prefix = sid[:length]
                count = self.conn.execute(
                    "SELECT count(*) FROM symbols WHERE id >= ? AND id < ?",
                    (prefix, prefix + "g")).fetchone()[0]
                if count <= 1:
                    break
            self.displays[sid] = prefix
        return self.displays[sid]

    def sha(self, path: str) -> str | None:
        """@brief The recorded content hash of an indexed file."""
        row = self.conn.execute("SELECT sha256 FROM files WHERE path = ?", (path,)).fetchone()
        return row[0] if row else None

    def symbol(self, row) -> dict:
        """@brief A symbol record from a SYMBOL_COLUMNS row."""
        (sid, kind, name, qualified, signature, path, start_line, start_column, end_line,
         end_column, role, language, depth) = row
        return {"id": sid, "display_id": self.display(sid), "kind": kind, "name": name,
                "qualified_name": qualified, "signature": signature, "path": path,
                "start": {"line": start_line, "column": start_column},
                "end": {"line": end_line, "column": end_column}, "role": role,
                "language": language, "depth": depth,
                "citation": self.citation(path, self.sha(path))}

    def reference(self, row, **extra) -> dict:
        """@brief A reference record from a REF_COLUMNS row."""
        _rowid, kind, spelling, path, line, column, label, target, origin = row
        record = {"kind": kind, "label": label, "path": path, "line": line, "column": column,
                  "spelling": spelling, "target": target, "from": origin,
                  "from_display": self.display(origin),
                  "citation": self.citation(path, self.sha(path))}
        record.update(extra)
        return record

    # targets and paging

    def resolve_target(self):
        """@brief (symbol row, None) or (None, envelope) for an ID or prefix target."""
        target = (self.args.target or "").strip().lower()
        if not target or not HEX.fullmatch(target) or len(target) > 32:
            return None, self.envelope("error", reason="invalid_request",
                                       message="a symbol ID is hexadecimal, as returned by find")
        rows = self.conn.execute(
            f"SELECT {SYMBOL_COLUMNS} FROM symbols s JOIN files f ON f.id = s.file_id "
            "WHERE s.id >= ? AND s.id < ? ORDER BY s.id LIMIT ?",
            (target, target + "g", self.limit + 1)).fetchall()
        if not rows:
            return None, self.envelope("not_found", reason="not_found",
                                       message="no symbol has this ID; it may have changed "
                                               "since indexing - run find again")
        if len(rows) > 1:
            choices = [self.symbol(row) for row in rows[:self.limit]]
            return None, self.finish(self.envelope("ambiguous", reason="ambiguous",
                                                   message="several symbols share this prefix; "
                                                           "use a longer ID", results=choices,
                                                   has_more=len(rows) > self.limit))
        return rows[0], None

    def page(self, target: str, ordering: str):
        """@brief (offset, digest) or (None, envelope) for the supplied page token."""
        digest = protocol.request_digest(self.action, target, ordering, self.limit)
        token = getattr(self.args, "page", None)
        if not token:
            return 0, digest
        try:
            snapshot, token_digest, offset = protocol.decode_page(token)
        except ValueError:
            return None, self.envelope("error", reason="invalid_request",
                                       message="malformed page token")
        if snapshot != self.meta.get("snapshot"):
            return None, self.envelope("expired", reason="expired",
                                       message="the index changed; repeat the query "
                                               "without a page token")
        if token_digest != digest:
            return None, self.envelope("error", reason="page_token_mismatch",
                                       message="this page token belongs to another query")
        return offset, digest

    def finish(self, env: dict, offset: int = 0, digest: str | None = None) -> dict:
        """@brief Apply the byte budget, with page tokens for the next records."""
        def next_page(kept: int) -> str | None:
            if digest is None:
                return None
            return protocol.encode_page(self.meta["snapshot"], digest, offset + kept)
        if env.get("has_more") and digest is not None and not env.get("next_page"):
            env["next_page"] = next_page(protocol.record_count(env))
        return protocol.fit(env, self.max_bytes, self.view_name,
                            next_page if digest is not None else None)

    # operations

    def status(self) -> tuple[dict | None, dict]:
        """@brief Availability, coverage, capability and the storage folder's Git view."""
        git = safety.destination_state(self.settings)
        folder = {"ignored": git["ignored"], "tracked": git["tracked"]}
        if self.conn is None:
            return None, folder
        counts = dict(self.conn.execute("SELECT status, count(*) FROM files GROUP BY status"))
        languages = [row[0] for row in self.conn.execute(
            "SELECT DISTINCT language FROM files WHERE status != 'skipped' ORDER BY 1")]
        details = {"available": True, "scope": counts, "languages": languages,
                   "inventory": self.meta.get("inventory"), "database_folder": folder}
        return details, folder

    def check(self) -> dict:
        """@brief Compare the whole scope with the recorded manifest, read-only."""
        deadline = (time.monotonic() + self.args.deadline
                    if getattr(self.args, "deadline", None) else None)
        selection = scope.select(self.settings)
        recorded = {path: (sha, status) for path, sha, status in self.conn.execute(
            "SELECT path, sha256, status FROM files WHERE status != 'skipped'")}
        stored_manifests = dict(self.conn.execute("SELECT path, sha256 FROM manifests"))
        self.conn.execute("COMMIT")   # the index is read; hashing sources holds no lock
        edit_hook = os.environ.get(HOOK_EDIT_DURING_CHECK)
        current, unknown, timed_out = {}, False, False
        for item in selection.files:
            if deadline is not None and time.monotonic() > deadline:
                unknown = timed_out = True
                break
            path = self.settings.root / item.path
            try:
                before = path.stat()
                data = path.read_bytes()
                if edit_hook == item.path:
                    with path.open("ab") as handle:
                        handle.write(b"\n")
                after = path.stat()
            except OSError:
                unknown = True   # removed or unreadable while the check ran
                continue
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                unknown = True
            current[item.path] = hashlib.sha256(data).hexdigest()
        manifests = scope.manifest_hashes(self.settings, selection.manifests)
        added = sorted(set(current) - set(recorded))
        deleted = sorted(set(recorded) - set(current)) if not unknown else []
        changed = sorted(path for path in set(current) & set(recorded)
                         if current[path] != recorded[path][0])
        failed = sorted(path for path, (_sha, status) in recorded.items() if status == "failed")
        manifests_changed = sorted(path for path in set(manifests) | set(stored_manifests)
                                   if manifests.get(path) != stored_manifests.get(path))
        config_changed = (self.meta.get("config_digest") != config.ingestion_digest(self.settings)
                          or self.meta.get("extractor") != EXTRACTOR_REVISION)
        if unknown:
            freshness = "unknown"
        elif added or deleted or changed or manifests_changed or config_changed:
            freshness = "stale"
        else:
            freshness = "current"
        lists = {"added": added, "changed": changed, "deleted": deleted, "failed": failed,
                 "manifests_changed": manifests_changed}
        more = any(len(values) > self.limit for values in lists.values())
        details = {key: values[:self.limit] for key, values in lists.items()}
        details["config_changed"] = config_changed
        message = None
        if timed_out:
            message = ("the check ran out of time before comparing every file; run it again "
                       "or allow it more time")
        elif unknown:
            message = "sources changed during the check; run it again"
        return self.finish(self.envelope(freshness=freshness, details=details, has_more=more,
                                         message=message))

    def find(self) -> dict:
        """@brief Ranked symbols matching a name, a prefix or identifier words."""
        target = (self.args.target or "").strip()
        if not target:
            return self.envelope("error", reason="invalid_request", message="find needs a name")
        offset, digest = self.page(target, "rank")
        if offset is None:
            return digest
        words = store.identifier_words(target).split()
        rows = self.conn.execute(
            f"SELECT {SYMBOL_COLUMNS} FROM symbols s JOIN files f ON f.id = s.file_id "
            "LEFT JOIN symbols p ON p.id = s.parent_id "
            "WHERE (s.kind IN ('module','class','function','method') OR (s.kind = 'variable' "
            "AND (p.kind IN ('module','class') OR p.kind IS NULL))) "
            "AND (s.qualified_name = ? OR s.name = ? OR substr(s.name, 1, ?) = ? "
            + "".join(" OR instr(' ' || s.words || ' ', ?) > 0" for _ in words[:1])
            + " OR instr(f.path, ?) > 0)",
            (target, target, len(target), target, *[f" {w} " for w in words[:1]], target)
        ).fetchall()

        def tier(row) -> int:
            qualified, name, path = row[3], row[2], row[5]
            row_words = set(store.identifier_words(name).split())
            if qualified == target:
                return 0
            if name == target:
                return 1
            if name.startswith(target):
                return 2
            if words and set(words) <= row_words:
                return 3
            if target in path:
                return 4
            return 9
        ranked = sorted((row for row in rows if tier(row) < 9),
                        key=lambda row: (tier(row), row[10] != "source", row[5], row[6], row[0]))
        window = ranked[offset:offset + self.limit]
        env = self.envelope(results=[self.symbol(row) for row in window],
                            has_more=len(ranked) > offset + len(window))
        return self.finish(env, offset, digest)

    def file(self) -> dict:
        """@brief The outline of one indexed file in source order."""
        raw = (self.args.target or "").strip().replace("\\", "/")
        candidate = Path(raw)
        if candidate.is_absolute():
            try:
                raw = candidate.resolve().relative_to(self.settings.root).as_posix()
            except ValueError:
                raw = ""
        parts = [part for part in raw.split("/") if part not in ("", ".")]
        path = "/".join(parts)
        if not path:
            return self.envelope("error", reason="invalid_request", message="file needs a path")
        row = self.conn.execute("SELECT id, role, language, status, reason FROM files "
                                "WHERE path = ? AND status != 'skipped'", (path,)).fetchone()
        if row is None:
            return self.envelope("not_found", reason="not_found",
                                 message=f"{path or raw} is not indexed")
        offset, digest = self.page(path, "source")
        if offset is None:
            return digest
        fid, role, language, status, reason = row
        rows = self.conn.execute(
            f"SELECT {SYMBOL_COLUMNS} FROM symbols s JOIN files f ON f.id = s.file_id "
            f"WHERE s.file_id = ? AND s.kind IN ({', '.join('?' * len(LISTED_KINDS))}) "
            "ORDER BY s.start_line, s.start_column, s.depth, s.id LIMIT ? OFFSET ?",
            (fid, *LISTED_KINDS, self.limit + 1, offset)).fetchall()
        window = rows[:self.limit]
        env = self.envelope(results=[self.symbol(r) for r in window],
                            details={"path": path, "role": role, "language": language,
                                     "extraction": status, "reason": reason},
                            has_more=len(rows) > self.limit)
        return self.finish(env, offset, digest)

    def symbol_query(self) -> dict:
        """@brief One symbol with a bounded one-hop neighborhood."""
        row, failure = self.resolve_target()
        if failure:
            return failure
        sid = row[0]
        neighbors = []
        for relation, sql, params in (
                ("caller", (f"SELECT {REF_COLUMNS} FROM refs r JOIN files f ON f.id = r.file_id "
                            "WHERE r.target_id = ? AND r.kind = 'call'"), (sid,)),
                ("caller", (f"SELECT {REF_COLUMNS} FROM refs r JOIN files f ON f.id = r.file_id "
                            "JOIN candidates c ON c.ref_rowid = r.rowid "
                            "WHERE c.symbol_id = ? AND r.kind = 'call'"), (sid,)),
                ("callee", (f"SELECT {REF_COLUMNS} FROM refs r JOIN files f ON f.id = r.file_id "
                            "WHERE r.from_id = ? AND r.kind = 'call'"), (sid,)),
                ("reference", (f"SELECT {REF_COLUMNS} FROM refs r JOIN files f ON f.id = "
                               "r.file_id WHERE r.target_id = ? AND r.kind != 'call'"), (sid,))):
            for ref in self.conn.execute(sql + " ORDER BY f.path, r.line, r.column, r.rowid",
                                         params):
                neighbors.append(self.reference(ref, relation=relation))
        window = neighbors[:self.limit]
        env = self.envelope(results=window, details={"symbol": self.symbol(row)},
                            has_more=len(neighbors) > len(window))
        return self.finish(env)

    def callers(self) -> dict:
        """@brief Linked incoming calls and, separately, candidate callers."""
        row, failure = self.resolve_target()
        if failure:
            return failure
        sid = row[0]
        offset, digest = self.page(sid, "location")
        if offset is None:
            return digest
        # one sequence - linked calls, then candidate calls - so offsets page both
        rows = self.conn.execute(
            f"SELECT {REF_COLUMNS}, 0 FROM refs r JOIN files f ON f.id = r.file_id "
            "WHERE r.target_id = ? AND r.kind = 'call' UNION ALL "
            f"SELECT {REF_COLUMNS}, 1 FROM refs r JOIN files f ON f.id = r.file_id "
            "JOIN candidates c ON c.ref_rowid = r.rowid WHERE c.symbol_id = ? "
            "AND r.kind = 'call' ORDER BY 10, 4, 5, 6, 1 LIMIT ? OFFSET ?",
            (sid, sid, self.limit + 1, offset)).fetchall()
        window = rows[:self.limit]
        env = self.envelope(
            results=[self.reference(r[:9]) for r in window if r[9] == 0],
            details={"candidates": [self.reference(r[:9]) for r in window if r[9] == 1]},
            has_more=len(rows) > self.limit)
        return self.finish(env, offset, digest)

    def refs(self) -> dict:
        """@brief Identifier references linked to one symbol."""
        row, failure = self.resolve_target()
        if failure:
            return failure
        sid = row[0]
        offset, digest = self.page(sid, "location")
        if offset is None:
            return digest
        rows = self.conn.execute(
            f"SELECT {REF_COLUMNS} FROM refs r JOIN files f ON f.id = r.file_id "
            "WHERE r.target_id = ? ORDER BY f.path, r.line, r.column, r.rowid LIMIT ? OFFSET ?",
            (sid, self.limit + 1, offset)).fetchall()
        window = rows[:self.limit]
        env = self.envelope(results=[self.reference(r) for r in window],
                            has_more=len(rows) > self.limit)
        return self.finish(env, offset, digest)

# PUBLIC API


def answer(action: str, settings: config.Settings, args, capability: dict,
           view_name: str) -> dict:
    """
    @brief Answer one read-only query with a protocol envelope.
    @param[in] action One of status, check, find, file, symbol, callers, refs.
    @param[in] args Parsed command-line arguments (target, limit, max_bytes, page, deadline).
    @param[in] capability Indexing capability of this interpreter.
    @param[in] view_name The view the budget applies to.
    """
    work = _Answer(action, settings, args, capability, view_name)
    conn, state = store.open_reader(settings.database)
    if conn is None:
        details = None
        if action == "status":
            details = {"available": False, "database_folder":
                       work.status()[1]}
        return protocol.envelope(action, "unavailable", reason=state, message=MESSAGES[state],
                                 index=state, capability=capability, details=details)
    work.conn = conn
    try:
        conn.execute("BEGIN")   # every read of this answer sees one generation
        work.meta = store.read_meta(conn)
        problem = work.invalid()
        if problem:
            return work.envelope("error", reason="invalid_request", message=problem)
        if action == "status":
            details, _folder = work.status()
            return work.envelope(details=details)
        if action == "check":
            try:
                return work.check()
            except scope.ScopeError as exc:
                status = "unavailable" if exc.reason == "scope_missing" else "error"
                return work.envelope(status, reason=exc.reason, message=str(exc),
                                     freshness="unknown")
        handler = {"find": work.find, "file": work.file, "symbol": work.symbol_query,
                   "callers": work.callers, "refs": work.refs}[action]
        return handler()
    except sqlite3.Error as exc:
        state = store.classify(exc)
        return protocol.envelope(action, "unavailable", reason=state, message=MESSAGES[state],
                                 index=state, capability=capability)
    finally:
        conn.close()

# END OF FILE
