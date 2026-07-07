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
@file process_log.py
@brief ADOR-owned rotating process log for scheduled run commands.
@details Keeps the command-line stdout behavior while appending the same lines
         to `<store_root>/ador.log`. This fills the Task Scheduler / --once
         audit gap without adding a configuration surface: defaults are fixed
         at 1 MiB with five backups.
@author Eng. Dan Dumitru Pasare
@date 2026-07-07
@version 0.1.0
"""

from __future__ import annotations

# IMPORTS
from pathlib import Path

from ador.util import utc_now_iso

# CONSTANTS

PROCESS_LOG_FILE = "ador.log"
PROCESS_LOG_MAX_BYTES = 1_048_576
PROCESS_LOG_BACKUPS = 5

# PUBLIC API


class ProcessLogger:
    """
    @brief   Tee-style line logger with fixed-size rotation.
    @details `emit()` prints to stdout and then appends the same line to disk;
             `append()` is available for tests and for non-stdout writes. The
             logger opens the file per line so short-lived `run --once`
             invocations do not need lifecycle management.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-07
    @version 0.1.0
    """

    def __init__(
        self,
        path: str | Path,
        *,
        max_bytes: int = PROCESS_LOG_MAX_BYTES,
        backups: int = PROCESS_LOG_BACKUPS,
    ) -> None:
        """
        @brief      Configure the logger.
        @param[in]  path Log file path.
        @param[in]  max_bytes Maximum current log size before rotation.
        @param[in]  backups Number of rotated backups to retain.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-07
        @version    0.1.0
        """
        self.path = Path(path)
        self.max_bytes = max(0, max_bytes)
        self.backups = max(0, backups)

    def emit(self, line: str) -> None:
        """
        @brief      Print a line and append it to the process log.
        @param[in]  line Text line without a required trailing newline.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-07
        @version    0.1.0
        """
        print(line)
        self.append(line)

    def append(self, line: str) -> None:
        """
        @brief      Append a timestamped line, rotating first when needed.
        @param[in]  line Text line without a required trailing newline.
        @exception  OSError When the log directory or file cannot be written.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-07
        @version    0.1.0
        """
        record = f"{utc_now_iso()} {line.rstrip()}\n"
        data_size = len(record.encode("utf-8"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rotate_if_needed(data_size)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record)

    def _rotate_if_needed(self, incoming_bytes: int) -> None:
        """
        @brief      Rotate `<path>` to numbered backups before append.
        @param[in]  incoming_bytes Bytes about to be appended.
        @exception  OSError When a filesystem operation fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-07
        @version    0.1.0
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
        @brief      Path for one rotated backup.
        @param[in]  index Backup number, where 1 is newest.
        @return     `<path>.<index>`.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-07
        @version    0.1.0
        """
        return self.path.with_name(f"{self.path.name}.{index}")


def process_log_path(store_root: str | Path) -> Path:
    """
    @brief      Default ADOR process log path for a state store.
    @param[in]  store_root Configured state store root.
    @return     `<store_root>/ador.log`.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-07
    @version    0.1.0
    """
    return Path(store_root) / PROCESS_LOG_FILE


# END OF FILE
