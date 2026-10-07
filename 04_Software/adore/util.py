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
@file util.py
@brief Shared low-level helpers: subprocess runner, durations, timestamps.
@details The CommandRunner protocol lets every shell-out (glab/gh/git/docker)
         be injected and faked in tests. Output is always captured, never
         streamed (see Prerequisites_Check_Report.md finding on buffering).
         Also: timestamps, quiet-hours windows, dotenv loading, and the
         read-only-tolerant force_rmtree used by teardown and cleanup.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Sequence
import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from typing import Protocol

# CONSTANTS

_DURATION_RE = re.compile(r"^\s*(\d+)\s*([smhd]?)\s*$", re.IGNORECASE)
_DURATION_UNITS = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}

DEFAULT_COMMAND_TIMEOUT = 600.0

# DATA MODELS / TYPEDEFINITIONS


@dataclass
class CommandResult:
    """
    @brief   Captured outcome of one external command invocation.
    @details `timed_out` is set ONLY when `run_command` itself killed the
             process for exceeding its wall-clock bound (a wrapper timeout,
             `subprocess.TimeoutExpired`). It is deliberately NOT inferred
             from `exit_code == 124`: a wrapped command (for example
             `docker exec`) propagates whatever exit code the INNER process
             used, and a payload legitimately exiting 124 for its own
             reasons must not be misreported as ADORE's own timeout
             (ADORE-ARCH-010) - see `aegis.py`'s `AegisClient._run`, the
             consumer that keys `AegisTimeoutError` on this flag rather than
             on the raw exit code.
    """

    argv: list[str] = field(default_factory=list)
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        """
        @brief   True when the command exited with code 0.
        @return  Success flag.
        """
        return self.exit_code == 0


class CommandRunner(Protocol):
    """
    @brief   Callable contract for running external commands.
    @details Concrete default is run_command; tests inject fakes so no real
             CLI (glab/gh/git/docker) is needed.
    """

    def __call__(
        self,
        argv: Sequence[str],
        *,
        cwd: str | Path | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        """
        @brief      Run one command and capture its output.
        @param[in]  argv Command and arguments (no shell).
        @param[in]  cwd Optional working directory.
        @param[in]  timeout Optional wall-clock limit in seconds.
        @param[in]  env Optional replacement environment.
        @return     The captured CommandResult.
        """
        ...  # pragma: no cover - protocol signature only


# HELPER FUNCTIONS


def _decode(stream: bytes | str | None) -> str:
    """
    @brief      Normalize a captured stream (bytes/str/None) to text.
    @param[in]  stream Raw stream from a TimeoutExpired exception.
    @return     Decoded text (empty when the stream is None).
    """
    if isinstance(stream, bytes):
        return stream.decode("utf-8", "replace")
    return stream or ""


# PUBLIC API


def run_command(
    argv: Sequence[str],
    *,
    cwd: str | Path | None = None,
    timeout: float | None = DEFAULT_COMMAND_TIMEOUT,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """
    @brief      Run an external command without a shell, capturing all output.
    @details    Never raises for command failure; errors are reported through
                the exit code (127 = binary missing, 126 = the OS refused the
                spawn, 124 = timeout) so callers decide deterministically.
                Output is decoded as UTF-8 with replacement to survive Windows
                console encodings.

                `timed_out=True` is set ONLY on the wrapper-timeout path
                below (`subprocess.TimeoutExpired`); the normal-completion
                path leaves it `False` even when a wrapped command (like
                `docker exec`) propagates an inner exit code of 124, so
                callers can tell "we killed it" from "it exited 124 on its
                own" (ADORE-ARCH-010).
    @param[in]  argv Command and arguments (no shell).
    @param[in]  cwd Optional working directory.
    @param[in]  timeout Optional wall-clock limit in seconds.
    @param[in]  env Optional replacement environment.
    @return     The captured CommandResult.
    """
    argv_list = [str(part) for part in argv]
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            argv_list,
            capture_output=True,
            cwd=str(cwd) if cwd is not None else None,
            timeout=timeout,
            env=env,
            check=False,
        )
    except FileNotFoundError as exc:
        return CommandResult(argv=argv_list, exit_code=127, stderr=str(exc))
    except subprocess.TimeoutExpired as exc:
        stdout = _decode(exc.stdout)
        stderr = _decode(exc.stderr)
        return CommandResult(
            argv=argv_list,
            exit_code=124,
            stdout=stdout,
            stderr=stderr or f"timeout after {timeout}s",
            timed_out=True,
        )
    except OSError as exc:
        # Everything else the OS can refuse: a locked or antivirus-held
        # executable (WinError 5), a command line past the Windows
        # 32767-character limit (WinError 206), an unusable cwd. None of these
        # is a RuntimeError, so an uncaught one escapes every ForgeError /
        # IsolationError handler above and takes the poll loop down with it.
        # Reporting a failed command keeps the failure inside the caller's
        # existing error path. 126 mirrors the shell's "found but not
        # executable", distinct from 127 (missing) and 124 (timeout).
        return CommandResult(argv=argv_list, exit_code=126, stderr=str(exc))
    return CommandResult(
        argv=argv_list,
        exit_code=completed.returncode,
        stdout=_decode(completed.stdout),
        stderr=_decode(completed.stderr),
    )


def parse_duration(text: str | int | float) -> int:
    """
    @brief      Parse a human duration ("90s", "30m", "24h", "7d", 60) to seconds.
    @param[in]  text Duration string with an optional s/m/h/d suffix, or a number
                     of seconds.
    @return     The duration in whole seconds.
    @exception  ValueError When the value cannot be parsed.
    """
    if isinstance(text, int | float):
        if text < 0:
            raise ValueError(f"negative duration: {text!r}")
        return int(text)
    match = _DURATION_RE.match(text)
    if not match:
        raise ValueError(f"invalid duration: {text!r}")
    value, unit = match.groups()
    return int(value) * _DURATION_UNITS[unit.lower()]


def utc_now_iso() -> str:
    """
    @brief   Current UTC time as a compact ISO-8601 string (Z suffix).
    @return  Timestamp like "2026-07-02T14:02:33Z".
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_to_datetime(text: str) -> datetime | None:
    """
    @brief      Parse an ISO-8601 timestamp (Z or offset form) to aware UTC.
    @param[in]  text Timestamp like "2026-07-02T14:02:33Z".
    @return     The aware datetime, or None when unparseable/empty.
    """
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def in_quiet_hours(windows: Sequence[str], now: datetime | None = None) -> bool:
    """
    @brief      Whether the current time falls in a configured quiet window.
    @details    Windows are "HH:MM-HH:MM" local time; a window crossing
                midnight ("22:00-06:00") wraps. Malformed windows are ignored
                (config validation reports them separately).
    @param[in]  windows Window strings from [polling] quiet_hours.
    @param[in]  now Override for tests (defaults to local now).
    @return     True when polling should pause.
    """
    moment = (now or datetime.now()).time()
    for window in windows:
        match = re.match(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$", str(window))
        if not match:
            continue
        h1, m1, h2, m2 = (int(part) for part in match.groups())
        start = h1 * 60 + m1
        end = h2 * 60 + m2
        current = moment.hour * 60 + moment.minute
        inside = start <= current < end if start <= end else current >= start or current < end
        if inside:
            return True
    return False


def force_rmtree(path: str | Path) -> None:
    """
    @brief      Remove a directory tree, tolerating read-only files and
                container-created symlinks.
    @details    Two Windows hazards this handles: git objects are read-only
                (plain rmtree fails - clear the bit and retry), and a
                worktree that ran `uv sync` inside the Linux container holds
                POSIX symlinks like `.venv/lib64 -> lib` that surface as
                reparse points Windows scandir refuses (WinError 1920) - the
                link entry is removed directly instead of recursed into. A
                missing path is fine (idempotent cleanup).
    @param[in]  path Directory to remove.
    """
    # One callback shape serves both APIs: shutil.rmtree passes it to `onerror`
    # (<=3.11) and to `onexc` (3.12+); the ignored third positional differs
    # (exc_info tuple vs exception), so the same handler works for both.
    def _on_error(func, target, _exc) -> None:
        with contextlib.suppress(OSError):
            os.chmod(target, stat.S_IWRITE)
        with contextlib.suppress(OSError):
            func(target)
            return
        # Reparse point / symlink unreadable to Windows: drop the link entry
        # itself (never follows into the target) rather than recursing.
        with contextlib.suppress(OSError):
            os.rmdir(target)
            return
        with contextlib.suppress(OSError):
            os.unlink(target)

    target = Path(path)
    if target.exists() or target.is_symlink():
        if sys.version_info >= (3, 12):
            shutil.rmtree(target, onexc=_on_error)
        else:
            shutil.rmtree(target, onerror=_on_error)


def process_alive(pid: int) -> bool:
    """
    @brief      Whether a process id is currently running (cross-platform).
    @details    Used to tell a genuinely stale single-instance lock (its owner
                crashed) from a live one. FAILS CLOSED: any uncertainty - an
                access-denied probe, an unexpected OS error - reports the
                process as alive, so a held lock is never stolen on a guess;
                only a provably absent pid reports dead. On POSIX this is
                `os.kill(pid, 0)`; on Windows it is an OpenProcess probe that
                deliberately avoids `os.kill`, which there can terminate the
                target instead of merely testing it.
    @param[in]  pid Candidate process id.
    @return     True when the pid is (or may be) running; False only when it is
                certainly gone.
    """
    if pid <= 0:
        return False
    if sys.platform == "win32":
        return _windows_process_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by another user - treat as alive
    except OSError:
        return True  # unknown failure - fail closed (assume alive)
    return True


def _windows_process_alive(pid: int) -> bool:
    """
    @brief      Windows liveness probe via OpenProcess (no os.kill).
    @param[in]  pid Candidate process id.
    @return     True when the process exists (or cannot be ruled out).
    """
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    process_query_limited_information = 0x1000
    still_active = 259
    error_access_denied = 5
    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        # denied => the process exists (alive); anything else => not found
        return ctypes.get_last_error() == error_access_denied
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return True  # cannot determine - fail closed
        return exit_code.value == still_active
    finally:
        kernel32.CloseHandle(handle)


def load_env_file(path: str | Path = ".env") -> dict[str, str]:
    """
    @brief      Load a dotenv-style file (KEY=VALUE lines) into a mapping.
    @details    Comments (#) and blank lines are skipped; surrounding quotes
                on values are stripped; a missing file yields {} (secrets are
                optional when the platform CLI auth already covers them).
    @param[in]  path Path to the .env file.
    @return     Mapping of the declared variables.
    """
    env_path = Path(path)
    if not env_path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            values[key] = value
    return values


def strict_json_loads(source: str) -> object:
    """
    @brief Decode external JSON without duplicate keys or non-finite numbers.
    @param[in] source Untrusted JSON text, bounded by the caller.
    @return Decoded JSON value.
    @exception ValueError For malformed or ambiguous input.
    """
    def unique(pairs):
        """@brief Reject repeated keys at every nested object boundary."""
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result

    def invalid(value):
        """@brief Reject constants outside the JSON number grammar."""
        raise ValueError("non-finite JSON value")

    try:
        return json.loads(source, object_pairs_hook=unique, parse_constant=invalid)
    except RecursionError as exc:
        raise ValueError("JSON nesting exceeds decoder bound") from exc


# END OF FILE
