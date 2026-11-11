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
@file    executor_evidence.py
@brief   Bounded operational projections of untrusted executor archives.
@details The caller supplies authorized profiles. Reads use existing schema-1
         archives without exposing transcripts, reasoning, credentials or costs.
         Only closed protocol facts and diagnostic classes reach the browser.
"""

# IMPORTS
from hashlib import sha256
import os
from pathlib import Path
import re
import stat

from adore.executor.diagnostics import validate_diagnostics
from adore.profiles import Profile, ProfileStore
from adore.state import StateError
from adore.web.jobs import JobReadError, _event_stage, _journal, _object, _stamp

# CONSTANTS
_SNAPSHOT_BYTES = 150 * 1024
_JOURNAL_BYTES = 32 * 1024 * 1024


# LOCAL HELPERS
def _identity(path: Path, *, directory: bool = False):
    """@brief Refuse links, reparse points and nonregular or multiply linked files."""
    info = path.lstat()
    if (path.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400
            or (not stat.S_ISDIR(info.st_mode) if directory else
                not stat.S_ISREG(info.st_mode) or info.st_nlink != 1)):
        raise JobReadError("job_evidence_corrupt")
    return info


def _signature(info):
    """@brief Bind file identity and contents across a bounded read."""
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _read(path: Path, limit: int) -> bytes:
    """@brief Read a stable unlinked file without accepting growth beyond its limit."""
    before = _identity(path)
    if before.st_size > limit:
        raise JobReadError("job_evidence_corrupt")
    with path.open("rb") as handle:
        if _signature(os.fstat(handle.fileno())) != _signature(before):
            raise JobReadError("job_snapshot_changed", 409)
        raw = handle.read(limit + 1)
        if (len(raw) > limit or _signature(os.fstat(handle.fileno())) != _signature(before)
                or _signature(_identity(path)) != _signature(before)):
            raise JobReadError("job_snapshot_changed", 409)
    return raw


# PUBLIC API
def read_executor_output(profiles: ProfileStore, item: Profile, run_id: str,
                         state_revision: str) -> dict:
    """
    @brief Read the latest journal-bound host-normalized executor diagnostics.
    @param[in] profiles Profile owner supplying the default state root.
    @param[in] item Already authorized immutable project identity.
    @param[in] run_id Selected validated run identity.
    @param[in] state_revision Exact state bytes inspected by the job endpoint.
    @return Concrete operational stdout/stderr or explicit missing provenance.
    @exception JobReadError Unsafe, corrupt, oversized or changing evidence.
    @note Raw executor IO, scripts, prompts, transcripts and configuration are never read.
    """
    root = Path(item.store_root or profiles.default_store_root(item.name)) / "runs" / run_id
    missing = {"project_id": item.project_id, "run_id": run_id, "availability": "missing",
               "state_revision": state_revision, "in_progress": False, "attempt": None,
               "stage": None, "recorded_at": None, "stdout": None, "stderr": None,
               "exit_code": None, "timed_out": None}
    try:
        for parent in (root, *root.parents):
            _identity(parent, directory=True)
        state = _read(root / "state.json", 4 * 1024 * 1024)
        if sha256(state).hexdigest() != state_revision:
            raise JobReadError("job_snapshot_changed", 409)
        run = _object(state, "run_state_corrupt")
        journal_path = root / "journal.jsonl"
        if not journal_path.exists() and not journal_path.is_symlink():
            return missing
        journal = _read(journal_path, _JOURNAL_BYTES)
        event = None
        for entry in reversed(_journal(journal)):
            if entry["event"] == "executor-artifacts":
                event = entry
                break
            if entry["event"] == "stage-launch" and run["lifecycle"] in {"working", "publishing"}:
                missing["in_progress"] = True
        # Earlier launches have no proven operational capture; never fall back to raw IO.
        if event is None or event.get("diagnostics") is None:
            if journal != _read(journal_path, _JOURNAL_BYTES) or state != _read(
                root / "state.json", 4 * 1024 * 1024
            ):
                raise JobReadError("job_snapshot_changed", 409)
            return missing
        reference = event["diagnostics"]
        if (not isinstance(reference, dict) or set(reference) != {"file", "sha256", "attempt"}
                or type(reference["attempt"]) is not int or reference["attempt"] < 1
                or not isinstance(reference["file"], str)
                or not re.fullmatch(r"attempt-[1-9][0-9]*-[a-f0-9]{32}\.json", reference["file"])
                or reference["file"].split("-")[1] != str(reference["attempt"])
                or not isinstance(reference["sha256"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", reference["sha256"])):
            raise JobReadError("job_evidence_corrupt")
        folder = root / "executor-diagnostics"
        before = _signature(_identity(folder, directory=True))
        raw = _read(folder / reference["file"], _SNAPSHOT_BYTES)
        if sha256(raw).hexdigest() != reference["sha256"]:
            raise JobReadError("job_evidence_corrupt")
        snapshot = _object(raw, "job_evidence_corrupt")
        if (set(snapshot) != {"schema", "run_id", "attempt", "context", "stdout", "stderr",
                             "exit_code", "timed_out"}
                or type(snapshot["schema"]) is not int or snapshot["schema"] != 1
                or snapshot["run_id"] != run_id or type(snapshot["attempt"]) is not int
                or snapshot["attempt"] != reference["attempt"]
                or snapshot["attempt"] > run["iterations"]
                or snapshot["context"] != event.get("context")
                or type(snapshot["exit_code"]) is not int
                or not -2**31 <= snapshot["exit_code"] < 2**31
                or type(snapshot["timed_out"]) is not bool):
            raise JobReadError("job_evidence_corrupt")
        streams = validate_diagnostics({key: snapshot[key] for key in ("stdout", "stderr")})
        if (journal != _read(journal_path, _JOURNAL_BYTES)
                or state != _read(root / "state.json", 4 * 1024 * 1024)
                or before != _signature(_identity(folder, directory=True))):
            raise JobReadError("job_snapshot_changed", 409)
        stage = _event_stage({"event": "executor-artifacts", "context": snapshot["context"]})
        return {**missing, "availability": "observed", **streams,
                "attempt": snapshot["attempt"],
                "in_progress": missing["in_progress"] and run["iterations"] > snapshot["attempt"],
                "stage": stage,
                "recorded_at": _stamp(event["ts"], "run_journal_corrupt"),
                "exit_code": snapshot["exit_code"], "timed_out": snapshot["timed_out"]}
    except FileNotFoundError:
        return missing
    except JobReadError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, StateError,
            RecursionError) as exc:
        raise JobReadError("job_evidence_corrupt") from exc


# END OF FILE
