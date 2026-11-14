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
@file    processes.py
@brief   Gated, bounded local process trees and ancestry fencing.
@details Windows kill-on-close Jobs and Linux sessions contain trusted workers.
         Every child waits until containment exists; parent death never grants
         replay authority. An independent drainer retains at most 64 KiB output.
"""

from __future__ import annotations

# IMPORTS
from contextlib import suppress
import json
import os
import signal
import subprocess
import sys
from threading import Event, Lock, Thread
import time
from uuid import uuid4

from adore.util import automatic_environment, background_process_options, strict_json_loads
from adore.web.ownership import OwnershipError, process_birth

# CONSTANTS
ANCESTRY = "ADORE_WORKER_ANCESTRY"


# PUBLIC API
def assert_ancestry(raw: str | None = None) -> list[dict]:
    """@brief Refuse corrupt, dead, reused or unverifiable parent identities.
    @return Strictly validated ancestry; absent transport means standalone use.
    @exception OwnershipError An ancestor cannot demonstrably authorize effects.
    """
    raw = os.environ.get(ANCESTRY) if raw is None else raw
    if raw is None:
        return []
    try:
        if len(raw) > 8192:
            raise ValueError("oversize ancestry")
        parents = strict_json_loads(raw)
        if not isinstance(parents, list) or not 1 <= len(parents) <= 12:
            raise ValueError("invalid ancestry")
        pids = set()
        for parent in parents:
            if (not isinstance(parent, dict) or set(parent) != {"pid", "birth"}
                    or type(parent["pid"]) is not int or parent["pid"] < 1
                    or parent["pid"] in pids or not isinstance(parent["birth"], str)
                    or not 1 <= len(parent["birth"]) <= 160
                    or process_birth(parent["pid"]) != parent["birth"]):
                raise ValueError("parent identity unavailable")
            pids.add(parent["pid"])
        return parents
    except (ValueError, TypeError, OSError, RuntimeError) as exc:
        raise OwnershipError("worker ancestor identity unavailable") from exc


def child_environment(environment: dict[str, str]) -> dict[str, str]:
    """@brief Bind a new child to the complete verified parent chain."""
    parents = assert_ancestry(environment.get(ANCESTRY))
    birth = process_birth(os.getpid())
    if not birth:
        raise OwnershipError("worker parent identity unavailable")
    result = automatic_environment(environment)
    result[ANCESTRY] = json.dumps([*parents, {"pid": os.getpid(), "birth": birth}])
    # Validate depth before any child can start.
    assert_ancestry(result[ANCESTRY])
    return result


class ProcessTree:
    """@brief Own one gated worker and all descendants within an OS process scope."""

    def __init__(self, argv: list[str], environment: dict[str, str]) -> None:
        """@brief Establish containment before releasing the trusted wrapper.
        @param[in] argv Fixed argument vector, without shell interpretation.
        @param[in] environment Non-secret ownership transport and service environment.
        @exception OSError/RuntimeError Launch or containment was refused.
        """
        self.output = bytearray()
        self.output_lock = Lock()
        self.closed = False
        self.reported = None
        self.report_done = Event()
        self.jobs = None
        self.job = ""
        self.process = None
        try:
            env = child_environment(environment)
            options = background_process_options()
            if os.name == "nt":
                from adore.local_process import WindowsJobs

                self.jobs = WindowsJobs()
                self.job = "ADORE-worker-" + uuid4().hex
                self.jobs.create(self.job)
            else:
                options["start_new_session"] = True
            self.process = subprocess.Popen(
                [sys.executable, "-m", "adore.web.processes", *argv], env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                **options)
            self.birth = process_birth(self.process.pid)
            if not self.birth:
                raise OwnershipError("child process creation identity unavailable")
            if self.jobs is not None:
                self.jobs.attach(self.job, self.process.pid)
            self.process.stdin.write(b"G")
            self.process.stdin.flush()
            Thread(target=self._read_report, daemon=True).start()
            Thread(target=self._drain_output, daemon=True).start()
        except BaseException:
            if self.process is not None:
                self.kill()
                self.process.wait(timeout=5)
            self.close()
            raise

    def poll(self) -> int | None:
        """@brief Inspect exit without waiting for this or another project."""
        if os.name != "nt" and self.process.returncode is None:
            # Keep an exited leader unreaped until its entire original group is
            # killed. Its reserved PID cannot become a stranger's process group.
            if self._linux_exit() is None:
                return None
            self.kill()
        code = self.process.poll()
        if code is None or not self.report_done.is_set():
            return None
        return self.reported if self.reported is not None else code or 1

    def _linux_exit(self):
        """@brief Inspect our direct child without releasing its kernel PID identity."""
        try:
            return os.waitid(os.P_PID, self.process.pid,
                             os.WEXITED | os.WNOHANG | os.WNOWAIT)
        except ChildProcessError as exc:
            raise OwnershipError("owned process wait identity unavailable") from exc

    def _read_report(self) -> None:
        """@brief Read the trusted wrapper's bounded exit report, never engine output."""
        try:
            raw = self.process.stdout.readline(128)
            value = strict_json_loads(raw.decode("ascii"))
            if type(value) is int and -(2 ** 31) <= value < 2 ** 32:
                self.reported = value
        except (OSError, UnicodeError, ValueError):
            pass
        finally:
            self.process.stdout.close()
            self.report_done.set()

    def _drain_output(self) -> None:
        """@brief Drain continuously into a fixed-size tail, including long-lived workers."""
        try:
            while chunk := self.process.stderr.read1(8192):
                with self.output_lock:
                    self.output.extend(chunk)
                    del self.output[:-65536]
        except OSError:
            pass
        finally:
            self.process.stderr.close()

    def request_stop(self) -> None:
        """@brief Request cooperative tree stop through the owned private pipe."""
        if self.poll() is None:
            with suppress(OSError):
                self.process.stdin.write(b"S")
                self.process.stdin.flush()

    def kill(self) -> None:
        """@brief Force only this owned scope, including descendants of an exited root."""
        if self.jobs is not None:
            self.jobs.kill(self.job)
        elif self.process is not None and self.process.returncode is None:
            exited = self._linux_exit()
            if (exited is None
                    and getattr(self, "birth", None) != process_birth(self.process.pid)):
                raise OwnershipError("owned process birth unavailable during stop")
            # The leader is either birth-verified and live, or our own unreaped
            # direct child. No poll/wait can release its PID before this signal.
            with suppress(ProcessLookupError):
                os.killpg(self.process.pid, signal.SIGKILL)

    def tail(self, limit: int = 65536) -> str:
        """@brief Read bounded captured evidence after an observed process exit."""
        if type(limit) is not int or limit < 1:
            raise ValueError("output tail limit must be a positive integer")
        with self.output_lock:
            return bytes(self.output[-min(limit, 65536):]).decode("utf-8", "replace")

    def close(self) -> None:
        """@brief Release drained scope handles; retained output stays bounded."""
        if self.jobs is not None and self.job:
            self.jobs.kill(self.job)
            self.jobs.remove(self.job)
            self.job = ""
        if self.process is not None and self.process.stdin is not None:
            self.process.stdin.close()
        self.closed = True


def stop_trees(children: list[ProcessTree], *, grace: float = 2.0,
               timeout: float = 5.0) -> None:
    """@brief Stop all scopes concurrently, then force them under shared deadlines.
    @note Unconfirmed processes keep durable ownership and recovery evidence.
    """
    failures = []

    def attempt(action) -> None:
        """@brief One failed scope never skips stop/kill/drain of another scope."""
        try:
            action()
        except Exception as exc:  # noqa: BLE001 - aggregate after all owned scopes
            failures.append(exc)

    for child in children:
        attempt(child.request_stop)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        live = []
        for child in children:
            attempt(lambda child=child, live=live: live.append(child.poll() is None))
        if not any(live):
            break
        time.sleep(0.02)
    # Kill descendants even when the wrapper exited before them.
    for child in children:
        attempt(child.kill)
    deadline = time.monotonic() + timeout
    for child in children:
        attempt(lambda child=child: child.process.wait(
            timeout=max(0.01, deadline - time.monotonic())))
    for child in children:
        attempt(child.close)
    if failures:
        raise OwnershipError("owned process shutdown could not be confirmed") from failures[0]


def main() -> int:
    """@brief Guard one trusted child; EOF/Stop/parent death quiesces its tree."""
    if not sys.argv[1:] or os.read(sys.stdin.fileno(), 1) != b"G":
        return 1
    assert_ancestry()
    stop = Event()

    def read_stop() -> None:
        """@brief EOF also stops children when the controlling process disappears."""
        os.read(sys.stdin.fileno(), 1)
        stop.set()

    Thread(target=read_stop, daemon=True).start()
    for name in ("SIGTERM", "SIGINT", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: stop.set())
    process = subprocess.Popen(sys.argv[1:], stdin=subprocess.DEVNULL,
                               stdout=sys.stderr, stderr=sys.stderr,
                               env=child_environment(dict(os.environ)),
                               **background_process_options())
    try:
        while process.poll() is None and not stop.wait(0.1):
            assert_ancestry()
        code = process.returncode if process.returncode is not None else 124
        print(json.dumps(code), flush=True)
        return code
    finally:
        if os.name != "nt":
            # Our dedicated session contains the actual child and its ordinary
            # subprocesses. Killing the wrapper too prevents late dispatch.
            os.killpg(os.getpgrp(), signal.SIGKILL)
        elif process.poll() is None:
            process.terminate()
            with suppress(subprocess.TimeoutExpired):
                process.wait(timeout=1)
            if process.poll() is None:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())

# END OF FILE
