"""Shared low-level helpers: subprocess runner, durations, timestamps."""

from __future__ import annotations

from collections.abc import Callable, Sequence
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
from typing import BinaryIO, Protocol

_DURATION_RE = re.compile(r"^\s*(\d+)\s*([smhd]?)\s*$", re.IGNORECASE)
_DURATION_UNITS = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}

DEFAULT_COMMAND_TIMEOUT = 600.0

# CSI, OSC (BEL or ST terminated), DCS/SOS/PM/APC strings, then any other ESC
# sequence; an unterminated string sequence ends at its own line.
ANSI_ESCAPE = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b\n]*(?:\x07|\x1b\\)?"
    r"|[PX^_][^\x1b\n]*(?:\x1b\\)?|[ -/]*[0-~])"
)


@dataclass
class CommandResult:
    """
    Captured outcome of one external command invocation.
    `timed_out` is set ONLY when `run_command` itself killed the
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
    raw_stdout: bytes | None = field(default=None, repr=False)

    @property
    def stdout_bytes(self) -> bytes:
        """
        Exact captured stdout; text-only injected results encode their fixture.
        Returns: Original command bytes, without decoding or newline conversion.
        Note: The production runner always supplies raw_stdout, including on timeout.
        """
        return (self.raw_stdout if self.raw_stdout is not None
                else self.stdout.encode("utf-8", "surrogateescape"))

    @property
    def ok(self) -> bool:
        """
        True when the command exited with code 0.
        Returns: Success flag.
        """
        return self.exit_code == 0


class CommandRunner(Protocol):
    """
    Callable contract for running external commands.
    Concrete default is run_command; tests inject fakes so no real
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
        Run one command and capture its output.
        argv: Command and arguments (no shell).
        cwd: Optional working directory.
        timeout: Optional wall-clock limit in seconds.
        env: Optional replacement environment.
        Returns: The captured CommandResult.
        """
        ...  # pragma: no cover - protocol signature only


def _decode(stream: bytes | str | None) -> str:
    """
    Normalize a captured stream (bytes/str/None) to text.
    stream: Raw stream from a TimeoutExpired exception.
    Returns: Decoded text (empty when the stream is None).
    """
    if isinstance(stream, bytes):
        return stream.decode("utf-8", "replace")
    return stream or ""


def automatic_environment(env: dict[str, str] | None = None) -> dict[str, str]:
    """
    Copy a child environment and disable interactive pagers.
    env: Replacement environment; None inherits the current process.
    Returns: Independent environment with authoritative Git/generic pager values.
    Note: Explicit environments retain their account/credential boundary.
    """
    source = os.environ if env is None else env
    result = {key: value for key, value in source.items()
              if key.upper() not in {"GIT_PAGER", "PAGER"}}
    result.update(GIT_PAGER="cat", PAGER="cat")
    return result


def background_process_options() -> dict[str, int]:
    """
    Suppress console allocation for automated Windows child processes.
    Returns: Windows CREATE_NO_WINDOW options, or empty options on other hosts.
    Note: Keeps Job membership and process handles; no detached/breakaway flag.
    """
    # The stable Win32 value also permits offline platform simulation on Linux.
    return {"creationflags": 0x08000000} if sys.platform == "win32" else {}


def run_command(
    argv: Sequence[str],
    *,
    cwd: str | Path | None = None,
    timeout: float | None = DEFAULT_COMMAND_TIMEOUT,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """
    Run an external command without a shell, capturing all output.
    Never raises for command failure; errors are reported through
                the exit code (127 = binary missing, 126 = the OS refused the
                spawn, 124 = timeout) so callers decide deterministically.
                Raw stdout is retained for byte-exact consumers. Display output
                is decoded as UTF-8 with replacement to survive Windows console
                encodings; it must not be used to fingerprint file content.
                Windows Azure CLI launchers use their installation's Python,
                never cmd.exe; all human arguments remain literal argv entries.

                `timed_out=True` is set ONLY on the wrapper-timeout path
                below (`subprocess.TimeoutExpired`); the normal-completion
                path leaves it `False` even when a wrapped command (like
                `docker exec`) propagates an inner exit code of 124, so
                callers can tell "we killed it" from "it exited 124 on its
                own" (ADORE-ARCH-010).
    argv: Command and arguments (no shell).
    cwd: Optional working directory.
    timeout: Optional wall-clock limit in seconds.
    env: Optional replacement environment.
    Returns: The captured CommandResult.
    """
    argv_list = [str(part) for part in argv]
    try:
        from adore.azure_cli import windows_azure_argv

        child_env = automatic_environment(env)
        spawn_argv = windows_azure_argv(argv_list, child_env)
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            spawn_argv,
            capture_output=True,
            cwd=str(cwd) if cwd is not None else None,
            timeout=timeout,
            env=child_env,
            stdin=subprocess.DEVNULL,
            check=False,
            **background_process_options(),
        )
    except FileNotFoundError as exc:
        return CommandResult(argv=argv_list, exit_code=127, stderr=str(exc), raw_stdout=b"")
    except subprocess.TimeoutExpired as exc:
        stdout = _decode(exc.stdout)
        stderr = _decode(exc.stderr)
        return CommandResult(
            argv=argv_list,
            exit_code=124,
            stdout=stdout,
            stderr=stderr or f"timeout after {timeout}s",
            timed_out=True,
            raw_stdout=exc.stdout if isinstance(exc.stdout, bytes) else stdout.encode("utf-8"),
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
        return CommandResult(argv=argv_list, exit_code=126, stderr=str(exc), raw_stdout=b"")
    return CommandResult(
        argv=argv_list,
        exit_code=completed.returncode,
        stdout=_decode(completed.stdout),
        stderr=_decode(completed.stderr),
        raw_stdout=completed.stdout,
    )


def parse_duration(text: str | int | float) -> int:
    """
    Parse a human duration ("90s", "30m", "24h", "7d", 60) to seconds.
    text: Duration string with an optional s/m/h/d suffix, or a number
                     of seconds.
    Returns: The duration in whole seconds.
    Raises ValueError: When the value cannot be parsed.
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
    Current UTC time as a compact ISO-8601 string (Z suffix).
    Returns: Timestamp like "2026-07-02T14:02:33Z".
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_to_datetime(text: str) -> datetime | None:
    """
    Parse an ISO-8601 timestamp (Z or offset form) to aware UTC.
    text: Timestamp like "2026-07-02T14:02:33Z".
    Returns: The aware datetime, or None when unparseable/empty.
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
    Whether the current time falls in a configured quiet window.
    Windows are "HH:MM-HH:MM" local time; a window crossing
                midnight ("22:00-06:00") wraps. Malformed windows are ignored
                (config validation reports them separately).
    windows: Window strings from [polling] quiet_hours.
    now: Override for tests (defaults to local now).
    Returns: True when polling should pause.
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


def output_tail(text: str, redact: Callable[[str], str], *,
                lines: int = 20, chars: int = 2000) -> str:
    """
    Keep the last lines of process output as evidence safe to show.
    NUL and ANSI escapes are removed and the whole text is redacted
                before the cut, so a cut never separates a key from its value.
    text: Captured output.
    redact: Credential redaction for the whole cleaned text.
    lines: Maximum number of trailing lines kept.
    chars: Maximum length of the result.
    Returns: The trailing lines, or "" when the output is blank.
    """
    clean = ANSI_ESCAPE.sub("", str(text).replace("\x00", ""))
    kept = redact(clean).strip().splitlines()
    return "\n".join(kept[-lines:])[-chars:]


def force_rmtree(path: str | Path) -> None:
    """
    Remove a directory tree, tolerating read-only files and
                container-created symlinks.
    Two Windows hazards this handles: git objects are read-only
                (plain rmtree fails - clear the bit and retry), and a
                worktree that ran `uv sync` inside the Linux container holds
                POSIX symlinks like `.venv/lib64 -> lib` that surface as
                reparse points Windows scandir refuses (WinError 1920) - the
                link entry is removed directly instead of recursed into. A
                missing path is fine (idempotent cleanup).
    path: Directory to remove.
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
    Whether a process id is currently running (cross-platform).
    Used to tell a genuinely stale single-instance lock (its owner
                crashed) from a live one. FAILS CLOSED: any uncertainty - an
                access-denied probe, an unexpected OS error - reports the
                process as alive, so a held lock is never stolen on a guess;
                only a provably absent pid reports dead. On POSIX this is
                `os.kill(pid, 0)`; on Windows it is an OpenProcess probe that
                deliberately avoids `os.kill`, which there can terminate the
                target instead of merely testing it.
    pid: Candidate process id.
    Returns: True when the pid is (or may be) running; False only when it is
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
    Windows liveness probe via OpenProcess (no os.kill).
    pid: Candidate process id.
    Returns: True when the process exists (or cannot be ruled out).
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
    Load a dotenv-style file (KEY=VALUE lines) into a mapping.
    Comments (#) and blank lines are skipped; surrounding quotes
                on values are stripped; a missing file yields {} (secrets are
                optional when the platform CLI auth already covers them).
    path: Path to the .env file.
    Returns: Mapping of the declared variables.
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
    Decode external JSON without duplicate keys or non-finite numbers.
    source: Untrusted JSON text, bounded by the caller.
    Returns: Decoded JSON value.
    Raises ValueError: For malformed or ambiguous input.
    """
    def unique(pairs):
        """Reject repeated keys at every nested object boundary."""
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result

    def invalid(value):
        """Reject constants outside the JSON number grammar."""
        raise ValueError("non-finite JSON value")

    try:
        return json.loads(source, object_pairs_hook=unique, parse_constant=invalid)
    except RecursionError as exc:
        raise ValueError("JSON nesting exceeds decoder bound") from exc


class UnsafeFileError(OSError):
    """A file the agent can write is not a plain bounded regular file."""


def read_agent_file(path: Path, limit: int) -> bytes | None:
    """
    Read a file from a directory the agent can write, without following links.
    The agent could replace such a file with a link to any file of the ADORE
            account. Only a regular, singly linked file whose identity is the
            same before and after opening is read, and never past the bound.
    path: Handoff or exchange file inside a worktree or run IO directory.
    limit: Largest accepted size in bytes.
    Returns: The content, or None when the file is absent.
    Raises UnsafeFileError: Link, reparse point, other file type, extra hard
            link, replacement during the read or a size above the bound.
    Raises OSError: Any other read failure.
    """
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or getattr(before, "st_file_attributes", 0) & 0x400):
        raise UnsafeFileError(f"{path.name} is not a plain regular file")
    flags = (os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
             | getattr(os, "O_BINARY", 0))
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise UnsafeFileError(f"{path.name} could not be opened as a plain file") from exc
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)):
            raise UnsafeFileError(f"{path.name} changed while it was opened")
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise UnsafeFileError(f"{path.name} exceeds its size bound")
    return content


def open_agent_file_for_write(path: Path) -> BinaryIO:
    """
    Open a file in a directory the agent can write, empty and ready for writing.
    The agent could plant a link under a name the host is about to write and
            so make the host overwrite a file of its own account. An existing
            entry must be a regular, singly linked file; the file is emptied
            only after the opened handle proved to be that same file.
    path: Host-authored file inside a run IO directory.
    Returns: Binary handle positioned at the start of an empty file.
    Raises UnsafeFileError: Link, reparse point, other file type, extra hard
            link or replacement while opening.
    Raises OSError: Any other failure.
    """
    try:
        before = path.lstat()
    except FileNotFoundError:
        before = None
    if before is not None and (
            not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or getattr(before, "st_file_attributes", 0) & 0x400):
        raise UnsafeFileError(f"{path.name} is not a plain regular file")
    flags = (os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
             | getattr(os, "O_BINARY", 0))
    try:
        descriptor = os.open(path, flags, 0o644)
    except OSError as exc:
        raise UnsafeFileError(f"{path.name} could not be opened as a plain file") from exc
    try:
        opened = os.fstat(descriptor)
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or before is not None
                and (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)):
            raise UnsafeFileError(f"{path.name} changed while it was opened")
        os.ftruncate(descriptor, 0)
        return os.fdopen(descriptor, "wb")
    except BaseException:
        os.close(descriptor)
        raise


def write_agent_file(path: Path, content: bytes) -> None:
    """Replace the content of a host-authored file in an agent-writable directory."""
    with open_agent_file_for_write(path) as stream:
        stream.write(content)
