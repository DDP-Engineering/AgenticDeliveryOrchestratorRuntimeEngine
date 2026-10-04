#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file cli.py
@brief Command line of the CodeGraph plugin.
@details `codegraph.py <operation> --root PATH [options] [-- target]`. Every
         operation answers with one protocol envelope, printed as compact text
         by default, as JSON with `--json`, or as JSON carrying the text with
         `--text-envelope` (the view AEGIS requests). Progress goes only to
         standard error. With `--watch-stdin`, end-of-file on standard input
         cancels indexing; this is how AEGIS stops an indexer it no longer
         supervises.
"""

# IMPORTS

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path

from codegraph import config, indexer, natives, protocol, python_extract, scope, store
from codegraph.safety import Refused

# CONSTANTS

PROGRESS_EVERY = 50

# HELPER FUNCTIONS


def build_parser() -> argparse.ArgumentParser:
    """@brief Arguments shared by every operation."""
    parser = argparse.ArgumentParser(prog="codegraph", description=__doc__.split("@details")[0])
    parser.add_argument("operation", choices=protocol.ACTIONS)
    parser.add_argument("target", nargs="?", default=None)
    parser.add_argument("--root", required=True, help="repository root")
    parser.add_argument("--config", help="configuration file (default: .agentic/aegis.toml)")
    parser.add_argument("--database", help="database path overriding [codegraph] database")
    parser.add_argument("--protocol", type=int, default=protocol.PROTOCOL)
    views = parser.add_mutually_exclusive_group()
    views.add_argument("--json", action="store_true", help="print the JSON envelope")
    views.add_argument("--text-envelope", action="store_true",
                       help="print the JSON envelope carrying the compact text")
    parser.add_argument("--limit", type=int, help="maximum records")
    parser.add_argument("--max-bytes", type=int, help="maximum output bytes (at most 32768)")
    parser.add_argument("--page", help="page token from a previous response")
    parser.add_argument("--rebuild", action="store_true", help="index: replace the database")
    parser.add_argument("--watch-stdin", action="store_true",
                        help="index: cancel when standard input reaches end-of-file")
    parser.add_argument("--deadline", type=float, help="cancel after this many seconds")
    return parser


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """
    @brief Parse the command line, taking a target after `--` out first.
    @details Python 3.11 and early 3.12 releases match the optional `target`
             as empty right after the operation and then reject a later
             `-- name`; separating the marker first gives every supported
             version the same result.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if "--" not in argv:
        return parser.parse_args(argv)
    marker = argv.index("--")
    tail = argv[marker + 1:]
    args = parser.parse_args(argv[:marker])
    if len(tail) != 1 or args.target is not None:
        parser.error("give exactly one target, after --")
    args.target = tail[0]
    return args


def _watch_input(closed: threading.Event) -> None:
    """
    @brief Set `closed` when standard input reaches end-of-file.
    @details The watcher reads a private duplicate, and standard input itself
             becomes the null device first. On Windows a child process
             receives a copy of the standard-input handle, and a blocked read
             on the same pipe stalls that child's startup - Git and the
             extraction workers alike - until the read ends.
    """
    private = os.dup(0)
    null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null, 0)
    os.close(null)

    def watch() -> None:
        try:
            while os.read(private, 65536):
                pass
        except OSError:
            pass
        closed.set()
    threading.Thread(target=watch, daemon=True).start()


def _stopper(args) -> tuple:
    """@brief A should-stop callable and a function naming why it stopped."""
    closed = threading.Event()
    if args.watch_stdin:
        _watch_input(closed)
    deadline = time.monotonic() + args.deadline if args.deadline else None

    def should_stop() -> bool:
        return closed.is_set() or (deadline is not None and time.monotonic() > deadline)

    def reason() -> str:
        return "cancelled" if closed.is_set() else "deadline"
    return should_stop, reason


def _progress(phase: str, done: int, total: int) -> None:
    """@brief Occasional progress lines on standard error."""
    if phase == "extract" and done not in (1, total) and done % PROGRESS_EVERY:
        return
    print(f"codegraph: {phase} {done}/{total}", file=sys.stderr, flush=True)


def _state(settings: config.Settings) -> str | None:
    """@brief The database state a reader would report, or None when even that fails."""
    try:
        conn, state = store.open_reader(settings.database)
    except Exception:  # noqa: BLE001 - only a description of the failure is wanted here
        return None
    if conn is not None:
        conn.close()
    return state


def _index(settings: config.Settings, args, capability: dict) -> dict:
    """@brief The `index` operation as an envelope; every refusal names the database state."""
    def failed(reason: str, message: str, index: str | None = None) -> dict:
        return protocol.envelope("index", "error", reason=reason, message=message,
                                 index=index or _state(settings), capability=capability)
    try:
        should_stop, why = _stopper(args)
        result = indexer.run_index(settings, rebuild=args.rebuild, should_stop=should_stop,
                                   progress=_progress)
    except Refused as exc:
        return failed(exc.reason, str(exc), exc.index)
    except scope.ScopeError as exc:
        return failed(exc.reason, str(exc))
    except python_extract.Cancelled:
        return failed(why(), "indexing stopped before publication; "
                             "the previous generation is unchanged")
    except sqlite3.DatabaseError as exc:
        name = getattr(exc, "sqlite_errorname", "") or ""
        if name.startswith(("SQLITE_BUSY", "SQLITE_LOCKED")):
            return failed("busy", "another process kept the database busy; nothing was "
                                  "published - index again", "busy")
        if name.startswith(("SQLITE_CORRUPT", "SQLITE_NOTADB")):
            return failed("incompatible", f"the database is damaged ({exc}); "
                                          "run know_graph_index --rebuild", "incompatible")
        return failed("internal", f"SQLite failed ({exc}); nothing was published")
    meta = result.pop("meta")
    return protocol.envelope("index", index="ready", capability=capability, meta=meta,
                             details=result)


def _scope(settings: config.Settings, capability: dict) -> dict:
    """@brief The `scope` operation as an envelope."""
    try:
        report = scope.report(settings)
    except scope.ScopeError as exc:
        status = "unavailable" if exc.reason == "scope_missing" else "error"
        return protocol.envelope("scope", status, reason=exc.reason, message=str(exc),
                                 index=_state(settings), capability=capability)
    return protocol.envelope("scope", index=_state(settings), capability=capability,
                             details=report)

# PUBLIC API


def main(argv: list[str] | None = None) -> int:
    """
    @brief Run one operation and print its response.
    @return The process exit code: 1 for status `error` or a configuration
            problem, 2 for usage errors, otherwise 0.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    args = parse_arguments(argv)
    view_name = "json" if args.json else "text-envelope" if args.text_envelope else "text"
    if args.protocol not in protocol.SUPPORTED_PROTOCOLS:
        env = protocol.envelope(args.operation, "error", reason="protocol",
                                message=f"protocol {args.protocol} is not supported",
                                capability=natives.capability(),
                                details={"supported": list(protocol.SUPPORTED_PROTOCOLS)})
        print(protocol.output(env, view_name))
        return 1
    try:
        settings = config.load(Path(args.root), Path(args.config) if args.config else None,
                               args.database)
    except config.ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    capability = natives.capability()
    try:
        if args.operation == "index":
            env = _index(settings, args, capability)
        elif args.operation == "scope":
            env = _scope(settings, capability)
        else:
            from codegraph import queries
            env = queries.answer(args.operation, settings, args, capability, view_name)
    except Exception as exc:  # noqa: BLE001 - an unexpected failure still answers with an envelope
        env = protocol.envelope(args.operation, "error", reason="internal",
                                message=f"{type(exc).__name__}: {exc}",
                                index=_state(settings), capability=capability)
    print(protocol.output(env, view_name))
    return protocol.exit_code(env["status"])

# END OF FILE
