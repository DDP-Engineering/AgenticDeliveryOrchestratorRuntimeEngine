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
@file    conversation.py
@brief   Bind Pi's own persistent session to one private job exchange directory.
@details Pi writes and compacts its transcript. This module checks ownership and
         current-format evidence before a process may resume it; it never repairs
         or imports a transcript. Callers retain the existing job execution lock.
"""

from __future__ import annotations

import math

# IMPORTS
import os
from pathlib import Path
import stat

from adore.execution import ExecutionRecoveryError
from adore.local_process import atomic_record, read_record
from adore.util import strict_json_loads

# CONSTANTS
CONVERSATION_DIR = "pi-conversation"
SESSION_FILE = "session.jsonl"
_RECORD_BYTES = 16 * 1024 * 1024
_ENTRY_TYPES = {
    "message", "thinking_level_change", "model_change", "usage", "compaction",
    "branch_summary", "custom", "label", "session_info", "custom_message", "context_edit",
}


# LOCAL HELPERS
def _checked(path: Path, *, directory: bool = False) -> os.stat_result:
    """@brief Refuse symlink, reparse, hardlink and unexpected file types."""
    info = path.lstat()
    if (path.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or not directory and info.st_nlink != 1):
        raise ValueError("unsafe conversation path")
    return info


# PUBLIC API
class PiConversation:
    """@brief Exact host/backend session binding; no personal-session discovery."""

    def __init__(self, io_dir: Path, worktree: Path, paths, *, required: bool = False,
                 context_key: str = "") -> None:
        """
        @brief Validate or initialize one job's private conversation binding.
        @param[in] io_dir Owned host exchange path, outside the worktree.
        @param[in] worktree Host worktree, used only for containment checks.
        @param[in] paths Existing backend-native IO and worktree paths.
        @param[in] required Refuse an absent binding for a previously launched job.
        @param[in] context_key Current ticket fingerprint, acknowledged with the prompt.
        @exception ExecutionRecoveryError Unsafe, foreign, missing or corrupt evidence.
        """
        self.directory = Path(io_dir).absolute() / CONVERSATION_DIR
        self.path = self.directory / SESSION_FILE
        self.receipt = self.directory / "binding.json"
        self.backend_file = paths.io.rstrip("/\\") + "/" + CONVERSATION_DIR + "/" + SESSION_FILE
        self.cwd = paths.worktree
        self.context_key = context_key
        self.owner = {"schema": 1, "io": str(Path(io_dir).absolute()), "cwd": self.cwd}
        try:
            for parent in self.directory.parents:
                if parent.exists() or parent.is_symlink():
                    _checked(parent, directory=True)
            if self.directory.resolve().is_relative_to(Path(worktree).resolve()):
                raise ValueError("conversation storage must be outside Git work")
            if not self.directory.exists():
                if required:
                    raise ValueError("required conversation binding is missing")
                self.directory.mkdir(mode=0o700)
                self.record = {**self.owner, "session_id": None, "required": False,
                               "context_key": ""}
                self._save()
            else:
                _checked(self.directory, directory=True)
                _checked(self.receipt)
                self.record = read_record(self.receipt)
                if (set(self.record) != {*self.owner, "session_id", "required", "context_key"}
                        or any(self.record.get(k) != v for k, v in self.owner.items())
                        or type(self.record["schema"]) is not int
                        or type(self.record["required"]) is not bool
                        or not isinstance(self.record["context_key"], str)
                        or self.record["session_id"] is not None
                        and (not isinstance(self.record["session_id"], str)
                             or not self.record["session_id"])
                        or self.record["required"] and self.record["session_id"] is None):
                    raise ValueError("foreign or corrupt conversation binding")
            self.resuming = self.path.exists() or self.path.is_symlink()
            self.context_changed = self.record["context_key"] != context_key
            if self.resuming:
                self._validate_file()
            elif self.record["required"]:
                raise ValueError("required conversation file is missing")
        except (OSError, ValueError, TypeError, OverflowError, RecursionError,
                ExecutionRecoveryError) as exc:
            raise ExecutionRecoveryError(
                "Pi job conversation missing, unsafe or corrupt; inspect the job, "
                "or delete the job through ADORE and start a new job"
            ) from exc

    def _save(self) -> None:
        """@brief Atomically persist non-secret ownership under private job permissions."""
        try:
            for directory in (self.directory, *self.directory.parents):
                _checked(directory, directory=True)
            atomic_record(self.receipt, self.record)
            if os.name == "posix":
                self.directory.chmod(0o700)
                self.receipt.chmod(0o600)
        except (OSError, ValueError) as exc:
            raise ExecutionRecoveryError("Pi job conversation binding could not be saved") from exc

    def _validate_file(self) -> None:
        """@brief Stream strict current Pi JSONL; refuse data Pi could silently discard."""
        before = _checked(self.path)
        parents: dict[str, str | None] = {}
        has_user = False
        with self.path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                raise ValueError("conversation file changed")
            first = handle.readline(_RECORD_BYTES + 1)
            if len(first) > _RECORD_BYTES or not first.endswith(b"\n"):
                raise ValueError("oversized or incomplete Pi session header")
            header = strict_json_loads(first.decode("utf-8"))
            if (not isinstance(header, dict) or header.get("type") != "session"
                    or type(header.get("version")) is not int or header["version"] != 3
                    or header.get("cwd") != self.cwd
                    or not isinstance(header.get("id"), str) or not header["id"]
                    or header.get("parentSession")
                    or header["id"] != self.record["session_id"]):
                raise ValueError("foreign or unsupported Pi session")
            while line := handle.readline(_RECORD_BYTES + 1):
                if len(line) > _RECORD_BYTES or not line.endswith(b"\n"):
                    raise ValueError("oversized or incomplete Pi session record")
                row = strict_json_loads(line.decode("utf-8"))
                if (not isinstance(row, dict) or not isinstance(row.get("type"), str)
                        or row["type"] not in _ENTRY_TYPES or not isinstance(row.get("id"), str)
                        or not row["id"] or row["id"] in parents
                        or "parentId" not in row
                        or row["parentId"] is not None and row["parentId"] not in parents
                        or row["type"] == "message" and not isinstance(row.get("message"), dict)):
                    raise ValueError("corrupt Pi session entry")
                if row["type"] == "message":
                    message = row["message"]
                    if not isinstance(message.get("role"), str) or (
                            message["role"] in {"user", "assistant"}
                            and not isinstance(message.get("content"), (str, list))):
                        raise ValueError("corrupt Pi session message")
                    has_user |= message["role"] == "user"
                elif row["type"] == "compaction":
                    kept, tokens = row.get("firstKeptEntryId"), row.get("tokensBefore")
                    if (not isinstance(row.get("summary"), str) or not isinstance(kept, str)
                            or type(tokens) not in (int, float) or not math.isfinite(tokens)
                            or tokens < 0):
                        raise ValueError("corrupt Pi compaction")
                    # Pi uses the compaction's own ID when retaining no older
                    # entry; otherwise the kept entry must be on this branch.
                    ancestor = row["id"] if kept == row["id"] else row["parentId"]
                    while ancestor is not None and ancestor != kept:
                        ancestor = parents.get(ancestor)
                    if ancestor != kept:
                        raise ValueError("foreign Pi compaction reference")
                parents[row["id"]] = row["parentId"]
            if not has_user:
                raise ValueError("Pi session has lost its conversation")
            after = _checked(self.path)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                raise ValueError("conversation file changed")
        if os.name == "posix":
            self.path.chmod(0o600)

    def bind(self, session_id: object, session_file: object) -> None:
        """
        @brief Pin the RPC identity before sending any model prompt.
        @param[in] session_id Pi get_state sessionId.
        @param[in] session_file Pi get_state sessionFile in backend path spelling.
        @exception ExecutionRecoveryError Missing or unexpected RPC session identity.
        """
        # Native Windows Pi normalizes separators; container paths stay POSIX.
        if (not isinstance(session_id, str) or not session_id
                or not isinstance(session_file, str)
                or session_file.replace("\\", "/") != self.backend_file.replace("\\", "/")
                or self.resuming and session_id != self.record["session_id"]):
            raise ExecutionRecoveryError("Pi RPC selected a different job conversation")
        self.record["session_id"] = session_id
        self._save()

    def accepted(self) -> None:
        """@brief Make history mandatory once Pi acknowledges the job prompt."""
        self.record["required"] = True
        self.record["context_key"] = self.context_key
        self._save()


# END OF FILE
