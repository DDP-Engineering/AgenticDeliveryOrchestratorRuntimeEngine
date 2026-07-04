#!/usr/bin/env python3
# -*- coding: utf-8 -*-  # noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file cli.py
@brief Command-line interface for ADOR over the ador.core library.
@details Defines the `ador` command surface (lifecycle, operations, statistics,
         config) using only the standard library (argparse). Base services
         (config, status, runs, pause/resume) are wired; engine commands report
         "not implemented yet" with exit code 2 until their phase lands.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.1.0
"""

from __future__ import annotations

# IMPORTS
import argparse
import json
import tomllib

from ador import __version__
from ador.config import Config, load_config, validate_config
from ador.orchestrator import Orchestrator
from ador.state import StateStore

# CONSTANTS

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NOT_IMPLEMENTED = 2

_NOT_IMPLEMENTED = frozenset(
    {"reset", "stats", "report", "export", "cleanup"}
)

# HELPER FUNCTIONS


def _build_parser() -> argparse.ArgumentParser:
    """
    @brief   Build the top-level argument parser and subcommands.
    @return  Configured argparse.ArgumentParser.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """
    parser = argparse.ArgumentParser(prog="ador", description="Agentic Delivery Orchestrator")
    parser.add_argument("--version", action="version", version=f"ador {__version__}")
    parser.add_argument("-c", "--config", default="config.toml", help="Path to config.toml")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the poller")
    run.add_argument("--loop", action="store_true", help="Long-running loop")
    run.add_argument("--once", action="store_true", help="Single poll pass")
    run.add_argument("--dry-run", action="store_true", help="Show actions without side effects")

    sub.add_parser("status", help="Show overall state")
    sub.add_parser("runs", help="List active/parked/in-review runs")
    sub.add_parser("pause", help="Stop picking new tickets")
    sub.add_parser("resume", help="Allow picking new tickets")
    sub.add_parser("cleanup", help="Garbage-collect orphaned worktrees/containers/state")

    for name in ("retry", "cancel", "logs"):
        p = sub.add_parser(name, help=f"{name} a run")
        p.add_argument("run_id")

    delete = sub.add_parser("delete", help="Hard-remove a run including state")
    delete.add_argument("run_id")
    delete.add_argument("--force", action="store_true")

    reset = sub.add_parser("reset", help="Force a run back to a stage")
    reset.add_argument("run_id")
    reset.add_argument("--to", required=True, help="Target gate")

    stats = sub.add_parser("stats", help="Show statistics")
    stats.add_argument("--since")
    stats.add_argument("--by")
    stats.add_argument("--html", action="store_true")

    report = sub.add_parser("report", help="Show a run report")
    report.add_argument("run_id")

    export = sub.add_parser("export", help="Export metrics")
    export.add_argument("--csv", action="store_true")

    cfg = sub.add_parser("config", help="Config helpers")
    cfg.add_argument("action", choices=["show", "validate", "set"])
    cfg.add_argument("key", nargs="?")
    cfg.add_argument("value", nargs="?")

    return parser


def _load(args: argparse.Namespace) -> Config | None:
    """
    @brief      Load the config file named on the command line.
    @param[in]  args Parsed arguments (args.config is the path).
    @return     The Config, or None after printing a readable error.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    try:
        return load_config(args.config)
    except FileNotFoundError:
        print(f"error: config file not found: {args.config}")
        print("hint: copy config.example.toml to config.toml and adjust it")
    except tomllib.TOMLDecodeError as exc:
        print(f"error: {args.config} is not valid TOML: {exc}")
    return None


def _store(config: Config) -> StateStore:
    """
    @brief      Build the state store from config.
    @param[in]  config Loaded configuration.
    @return     The StateStore for this deployment.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    return StateStore(config.state.store_root, config.agent.slug)


# COMMAND HANDLERS


def _cmd_config(args: argparse.Namespace) -> int:
    """
    @brief      Handle `ador config show|validate|set`.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    if args.action == "set":
        print("ador config set: not implemented yet (edit config.toml directly)")
        return EXIT_NOT_IMPLEMENTED
    config = _load(args)
    if config is None:
        return EXIT_ERROR
    if args.action == "show":
        print(json.dumps(config.to_dict(), indent=2, ensure_ascii=False))
        return EXIT_OK
    issues = validate_config(config)
    if issues:
        print(f"{args.config}: {len(issues)} issue(s)")
        for issue in issues:
            print(f"  - {issue}")
        return EXIT_ERROR
    print(f"{args.config}: OK")
    return EXIT_OK


def _cmd_status(args: argparse.Namespace) -> int:
    """
    @brief      Handle `ador status`: config health, lock, pause, run counts.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.1
    """
    config = _load(args)
    if config is None:
        return EXIT_ERROR
    issues = validate_config(config)
    store = _store(config)
    runs = store.list_runs()
    invalid = store.invalid_runs()
    by_lifecycle: dict[str, int] = {}
    for run in runs:
        by_lifecycle[run.lifecycle] = by_lifecycle.get(run.lifecycle, 0) + 1
    lock = store.lock_info()

    print(f"{config.agent.name} status")
    print(f"  config : {args.config} ({'OK' if not issues else f'{len(issues)} issue(s)'})")
    print(f"  store  : {store.root}")
    print(f"  paused : {'yes' if store.is_paused() else 'no'}")
    print(f"  lock   : {'held (pid ' + str(lock.get('pid', '?')) + ')' if lock else 'free'}")
    breakdown = ", ".join(f"{count} {name}" for name, count in sorted(by_lifecycle.items()))
    print(f"  runs   : {len(runs)} total" + (f" ({breakdown})" if breakdown else ""))
    if invalid:
        print(f"  CORRUPT: {len(invalid)} run(s) with unreadable state: {', '.join(invalid)}")
        print("           these runs are skipped; inspect or remove them manually")
    return EXIT_OK


def _cmd_runs(args: argparse.Namespace) -> int:
    """
    @brief      Handle `ador runs`: list persisted runs as a table.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.1
    """
    config = _load(args)
    if config is None:
        return EXIT_ERROR
    store = _store(config)
    runs = store.list_runs()
    invalid = store.invalid_runs()
    if not runs and not invalid:
        print("no runs")
        return EXIT_OK
    if runs:
        header = f"{'RUN-ID':<40} {'TICKET':>6} {'STAGE':<14} {'LIFECYCLE':<10} UPDATED"
        print(header)
        for run in runs:
            print(
                f"{run.run_id:<40} {run.ticket_iid:>6} {run.stage:<14} "
                f"{run.lifecycle:<10} {run.updated_at}"
            )
    for run_id in invalid:
        print(f"{run_id:<40} {'?':>6} {'?':<14} {'CORRUPT':<10} state.json unreadable")
    return EXIT_OK


def _cmd_pause(args: argparse.Namespace, *, paused: bool) -> int:
    """
    @brief      Handle `ador pause` / `ador resume`.
    @param[in]  args Parsed arguments.
    @param[in]  paused True to pause, False to resume.
    @return     Process exit code.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    config = _load(args)
    if config is None:
        return EXIT_ERROR
    store = _store(config)
    if paused:
        store.pause()
        print("paused: no new tickets will be picked (in-flight runs continue)")
    else:
        store.resume()
        print("resumed: ticket pickup is allowed again")
    return EXIT_OK


def _engine(args: argparse.Namespace) -> tuple[Config, Orchestrator] | None:
    """
    @brief      Load + validate config, then build the engine.
    @details    Engine commands refuse to start on an invalid config -
                `validate at startup` is the design contract (12a).
    @param[in]  args Parsed arguments.
    @return     (config, orchestrator), or None after a printed error.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    config = _load(args)
    if config is None:
        return None
    issues = validate_config(config)
    if issues:
        print(f"error: {args.config} has {len(issues)} issue(s); "
              "run `ador config validate`")
        return None
    return config, Orchestrator.from_config(config)


def _cmd_run(args: argparse.Namespace) -> int:
    """
    @brief      Handle `ador run [--loop|--once|--dry-run]`.
    @details    Default mode comes from [polling] mode; flags override.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    built = _engine(args)
    if built is None:
        return EXIT_ERROR
    config, engine = built
    if args.dry_run:
        summary = engine.poll_once(dry_run=True)
        print(json.dumps(summary))
        return EXIT_OK
    loop = args.loop or (config.polling.mode == "loop" and not args.once)
    if loop:
        return engine.run_loop()
    try:
        summary = engine.poll_once()
    except RuntimeError as exc:
        store = _store(config)
        print(f"error: {exc} ({store.lock_path})")
        print("hint: if no other ador process is running, remove the stale "
              "lock file and re-run")
        return EXIT_ERROR
    print(json.dumps(summary))
    return EXIT_OK


def _cmd_run_op(args: argparse.Namespace) -> int:
    """
    @brief      Handle per-run operations: cancel, retry, logs, delete.
    @param[in]  args Parsed arguments (args.run_id set).
    @return     Process exit code.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    built = _engine(args)
    if built is None:
        return EXIT_ERROR
    config, engine = built
    store = _store(config)
    if args.command == "logs":
        events = store.read_journal(args.run_id)
        if not events:
            print(f"no journal for run {args.run_id}")
            return EXIT_ERROR
        for event in events:
            details = {k: v for k, v in event.items() if k not in ("ts", "event")}
            suffix = f" {json.dumps(details, ensure_ascii=False)}" if details else ""
            print(f"{event.get('ts', '?')} {event.get('event', '?')}{suffix}")
        return EXIT_OK
    if args.command == "cancel":
        ok = engine.cancel(args.run_id)
        print("cancelled" if ok else f"no such run: {args.run_id}")
        return EXIT_OK if ok else EXIT_ERROR
    if args.command == "retry":
        ok = engine.retry(args.run_id)
        print("retried" if ok else f"cannot retry: {args.run_id}")
        return EXIT_OK if ok else EXIT_ERROR
    # delete: destructive - confirm via --force (design 8c guardrail)
    if not store.exists(args.run_id):
        print(f"no such run: {args.run_id}")
        return EXIT_ERROR
    if not args.force:
        print("delete removes ALL run state irrecoverably; re-run with --force")
        return EXIT_ERROR
    engine.cancel(args.run_id, outcome="deleted")
    store.delete_run(args.run_id)
    print(f"deleted {args.run_id}")
    return EXIT_OK


# PUBLIC API


def main(argv: list[str] | None = None) -> int:
    """
    @brief      Program entry point for the `ador` command.
    @param[in]  argv Optional argument vector (defaults to sys.argv).
    @return     Process exit code (0 = success, 1 = error, 2 = not implemented).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.1
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "config":
        return _cmd_config(args)
    if args.command == "status":
        return _cmd_status(args)
    if args.command == "runs":
        return _cmd_runs(args)
    if args.command == "pause":
        return _cmd_pause(args, paused=True)
    if args.command == "resume":
        return _cmd_pause(args, paused=False)
    if args.command == "run":
        return _cmd_run(args)
    if args.command in ("cancel", "retry", "logs", "delete"):
        return _cmd_run_op(args)
    if args.command in _NOT_IMPLEMENTED:
        print(f"ador {args.command}: not implemented yet")
        return EXIT_NOT_IMPLEMENTED
    parser.error(f"unknown command: {args.command}")
    return EXIT_ERROR  # pragma: no cover - parser.error exits


# END OF FILE
