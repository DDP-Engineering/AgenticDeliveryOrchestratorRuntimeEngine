"""ADORE-owned rotating process log for scheduled run commands."""

from __future__ import annotations

import contextlib
from pathlib import Path

from adore.branding import PROCESS_LOG_FILE
from adore.resource_lock import ResourceLockError, resource_lock
from adore.util import utc_now_iso

PROCESS_LOG_MAX_BYTES = 1_048_576
PROCESS_LOG_BACKUPS = 5



class ProcessLogger:
    """
    Tee-style line logger with fixed-size rotation.
    `emit()` prints to stdout and then appends the same line to disk;
             `append()` is available for tests and for non-stdout writes. The
             logger opens the file per line so short-lived `run --once`
             invocations do not need lifecycle management.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        max_bytes: int = PROCESS_LOG_MAX_BYTES,
        backups: int = PROCESS_LOG_BACKUPS,
    ) -> None:
        """
        Configure the logger.
        path: Log file path.
        max_bytes: Maximum current log size before rotation.
        backups: Number of rotated backups to retain.
        """
        self.path = Path(path)
        self.max_bytes = max(0, max_bytes)
        self.backups = max(0, backups)

    def emit(self, line: str) -> None:
        """
        Print a line and append it to the process log.
        line: Text line without a required trailing newline.
        """
        print(line)
        self.append(line)

    def append(self, line: str) -> None:
        """
        Append a timestamped line, rotating first when needed.
        line: Text line without a required trailing newline.
        Raises OSError: When the log directory or file cannot be written.
        """
        record = f"{utc_now_iso()} {line.rstrip()}\n"
        data_size = len(record.encode("utf-8"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with resource_lock(self.path.with_name(self.path.name + ".write.lock")):
                # Another process can hold the file open, which on Windows
                # refuses the rename. Keep logging past the size bound and
                # rotate on a later line; a lost line would be worse.
                with contextlib.suppress(OSError):
                    self._rotate_if_needed(data_size)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(record)
        except ResourceLockError as exc:
            raise OSError("process log is busy or unavailable") from exc

    def _rotate_if_needed(self, incoming_bytes: int) -> None:
        """
        Rotate `<path>` to numbered backups before append.
        incoming_bytes: Bytes about to be appended.
        Raises OSError: When a filesystem operation fails.
        """
        if self.max_bytes <= 0 or not self.path.exists():
            return
        if self.path.stat().st_size + incoming_bytes <= self.max_bytes:
            return
        if self.backups <= 0:
            self.path.unlink(missing_ok=True)
            return
        self._backup_path(self.backups).unlink(missing_ok=True)
        for index in range(self.backups - 1, 0, -1):
            src = self._backup_path(index)
            if src.exists():
                src.replace(self._backup_path(index + 1))
        self.path.replace(self._backup_path(1))

    def _backup_path(self, index: int) -> Path:
        """
        Path for one rotated backup.
        index: Backup number, where 1 is newest.
        Returns: `<path>.<index>`.
        """
        return self.path.with_name(f"{self.path.name}.{index}")


def process_log_path(store_root: str | Path) -> Path:
    """
    Default ADORE process log path for a state store.
    store_root: Configured state store root.
    Returns: `<store_root>/adore.log`.
    """
    return Path(store_root) / PROCESS_LOG_FILE
