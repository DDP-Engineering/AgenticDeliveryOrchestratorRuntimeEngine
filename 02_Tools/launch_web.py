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
@file launch_web.py
@brief Start the ADORE web API and control worker from an offline installation.
@details Foreground supervisor for a single host; service managers may use the
         two installed entrypoints directly.
"""

import argparse
from pathlib import Path
import subprocess
import sys
import time


def _stop(process) -> None:
    """@brief Stop one child before starting a replacement pair."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def _spawn_service(command: list[str]):
    """@brief Isolate child console signals so Ctrl-C reaches the supervisor."""
    if sys.platform == "win32":
        return subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    return subprocess.Popen(command, start_new_session=True)


def supervise(worker_command: list[str], api_command: list[str], *,
              restart_limit: int = 3, spawn=subprocess.Popen,
              pause=time.sleep) -> int:
    """@brief Restart a failed API/worker pair with finite backoff.

    @param[in] worker_command Command for the single-host control worker.
    @param[in] api_command Command for the HTTP API process.
    @param[in] restart_limit Number of whole-pair restarts after initial start.
    @return Zero on operator interruption, one on exhausted/crashed startup.
    @exception ValueError Invalid restart limit.
    """
    if type(restart_limit) is not int or not 0 <= restart_limit <= 10:
        raise ValueError("restart_limit must be between 0 and 10")
    restarts = 0
    while True:
        children = []
        try:
            children.append(spawn(worker_command))
            children.append(spawn(api_command))
            while all(child.poll() is None for child in children):
                pause(2)
        except KeyboardInterrupt:
            return 0
        except OSError:
            return 1
        finally:
            for child in children:
                _stop(child)
        if restarts >= restart_limit:
            return 1
        restarts += 1
        try:
            pause(min(2 ** (restarts - 1), 8))
        except KeyboardInterrupt:
            return 0


def main() -> int:
    """@brief Supervise the API and worker as separate processes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=None)
    parser.add_argument("--home", type=Path, default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--restart-limit", type=int, default=3,
                        help="Whole API/worker restarts after an unexpected exit (0-10)")
    args = parser.parse_args()
    bundle = Path(__file__).resolve().parent
    target = args.target.resolve() if args.target else (bundle / "runtime")
    python = target / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.is_file():
        raise SystemExit(f"installed Python not found: {python}")
    home_args = ["--home", str(args.home.resolve())] if args.home else []
    try:
        return supervise(
            [str(python), "-m", "adore.web.commands", *home_args],
            [str(python), "-m", "adore.web.server", *home_args,
             "--host", args.host, "--port", str(args.port)],
            restart_limit=args.restart_limit,
            spawn=_spawn_service,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE
