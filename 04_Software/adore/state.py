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
@file state.py
@brief Local, authoritative run state for ADORE (design doc 8a).
@details Owns the `.adore/runs/<run-id>/` layout (ticket.json, state.json,
         journal.jsonl), the deterministic run-id derived from the ticket
         reference, the content hash used for drift detection, the
         single-instance lock (with crash-safe stale reclaim), and the global
         pause flag. The local state is the source of truth; Git-platform
         labels/comments only reflect it. Corrupt persisted state fails closed:
         loading raises StateError so the caller can skip or escalate
         deterministically, never guess. The run-state schema is numbered from
         1 alongside the AEGIS JSON schema; any other value is refused, and no
         earlier state shape is migrated.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, fields
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
from typing import Any

from adore.branding import DEFAULT_STATE_ROOT, PRODUCT_SLUG
from adore.util import process_alive, utc_now_iso

# CONSTANTS

STATE_FILE = "state.json"
TICKET_FILE = "ticket.json"
JOURNAL_FILE = "journal.jsonl"
PAUSE_FILE = "paused"
#: ADORE's durable run-state schema, numbered from 1 alongside the AEGIS JSON
#: schema it is conducted with. It counts the shape of `state.json` only, and
#: is deliberately independent of any ADORE release number.
STATE_SCHEMA_VERSION = 1
_TASK_ID_RE = re.compile(r"^TASK-[0-9a-f]{8,64}$")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_STAGES = {"frame", "specify", "design", "build", "validate", "deliver", "done",
           "publishing"}
_LIFECYCLES = {
    "working", "parked-clarification", "awaiting-approval", "publishing",
    "in-review", "failed", "done", "cancelled", "stale",
}

# DATA MODELS / TYPEDEFINITIONS


class StateError(RuntimeError):
    """
    @brief   Raised when persisted state exists but cannot be trusted.
    @details Fail-closed signal for corrupt/unreadable state.json or
             ticket.json (for example after a crash or manual edit). Callers
             skip or escalate the affected run; they never reinitialize it.
    """


@dataclass
class RunState:
    """
    @brief   In-memory view of a single run's persisted state.
    @details Everything the orchestrator needs to resume a run after a restart:
             the active/historical AEGIS tasks, journal stage, recoverable
             failure counters, durable notification outbox, approval-bound
             candidate fingerprint, signaling ids, and isolated resources.
    """

    run_id: str
    ticket_iid: int
    schema_version: int = STATE_SCHEMA_VERSION
    stage: str = "frame"
    lifecycle: str = "working"
    active_task_id: str | None = None
    task_ids: list[str] = field(default_factory=list)
    aegis_type: str = "feature"
    aegis_path: str = "full"
    stage_failures: int = 0
    failure_history: list[dict[str, Any]] = field(default_factory=list)
    content_hash: str = ""
    status_comment_id: int | None = None
    question_comment_id: int | None = None
    incident_comment_id: int | None = None
    incident_target: str = ""
    last_seen_comment_id: int | None = None
    clarification_rounds: int = 0
    review_rounds: int = 0
    branch: str = ""
    base_ref: str = ""
    worktree: str = ""
    container: str = ""
    parked_at: str = ""
    parked_polls: int = 0
    reminder_sent: bool = False
    iterations: int = 0
    mr_iid: int | None = None
    mr_url: str = ""
    mr_missing_polls: int = 0
    #: Last forge pipeline verdict already surfaced for this MR/PR, so a red
    #: pipeline is reported once rather than on every poll of a run that may
    #: sit in review for days. Additive with a default, so state written before
    #: it existed still loads.
    pipeline_reported: str = ""
    notification_outbox: list[dict[str, Any]] = field(default_factory=list)
    candidate_fingerprint: str = ""
    candidate_base_ref: str = ""
    #: Product digest of the candidate a human approved, captured ONCE when
    #: publication begins and reused by every retry. Without it a retry
    #: recaptured the baseline from whatever the failed attempt left behind,
    #: which would let an unapproved product change become the new baseline.
    approved_product: str = ""
    approval_presented_at: str = ""
    approval_comment_id: int | None = None
    approval_label_removed: bool = False
    validation_evidence: dict[str, Any] = field(default_factory=dict)
    outcome: str = ""
    active_started_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """
        @brief   The state as a JSON-serializable mapping.
        @return  Plain mapping of all fields.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunState:
        """
        @brief      Rebuild a RunState from a persisted mapping.
        @details    Missing or wrong schema and unknown keys are rejected, so
                    foreign state is never reinterpreted as an AEGIS task run.
        @param[in]  data Mapping loaded from state.json.
        @return     The reconstructed RunState.
        """
        if data.get("schema_version") != STATE_SCHEMA_VERSION:
            raise StateError(
                f"unsupported run-state schema; ADORE requires schema "
                f"{STATE_SCHEMA_VERSION} and migrates no earlier run state"
            )
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise StateError(
                f"run-state schema {STATE_SCHEMA_VERSION} has unknown "
                f"keys: {unknown}"
            )
        state = cls(**data)
        if (
            not isinstance(state.run_id, str)
            or _RUN_ID_RE.fullmatch(state.run_id) is None
            or state.run_id in {".", ".."}
        ):
            raise StateError("run-state run_id must be a safe path component")
        if type(state.ticket_iid) is not int or state.ticket_iid < 1:
            raise StateError("run-state ticket_iid must be a positive integer")
        if state.stage not in _STAGES:
            raise StateError(f"run-state carries unknown stage {state.stage!r}")
        if state.lifecycle not in _LIFECYCLES:
            raise StateError(f"run-state carries unknown lifecycle {state.lifecycle!r}")
        if state.aegis_type not in {"feature", "fix", "change"}:
            raise StateError(f"run-state carries unknown AEGIS type {state.aegis_type!r}")
        if state.aegis_path not in {"full", "quick"}:
            raise StateError(f"run-state carries unknown AEGIS path {state.aegis_path!r}")
        if not isinstance(state.task_ids, list) or not all(
            isinstance(item, str) and _TASK_ID_RE.fullmatch(item)
            for item in state.task_ids
        ):
            raise StateError("run-state task_ids must be a valid TASK id list")
        if state.active_task_id is not None and (
            _TASK_ID_RE.fullmatch(state.active_task_id) is None
            or state.active_task_id not in state.task_ids
        ):
            raise StateError("run-state active_task_id must name a historical task")
        if type(state.stage_failures) is not int or state.stage_failures < 0:
            raise StateError("run-state stage_failures must be non-negative")
        if not isinstance(state.failure_history, list) or not all(
            isinstance(item, dict) for item in state.failure_history
        ):
            raise StateError("run-state failure_history must be an object list")
        if not isinstance(state.notification_outbox, list) or not all(
            isinstance(item, dict) for item in state.notification_outbox
        ):
            raise StateError("run-state notification_outbox must be an object list")
        if not isinstance(state.validation_evidence, dict):
            raise StateError("run-state validation_evidence must be an object")
        for name in ("candidate_fingerprint", "candidate_base_ref", "approved_product"):
            value = getattr(state, name)
            if value and re.fullmatch(r"[0-9a-f]{40,64}", value) is None:
                raise StateError(f"run-state {name} must be a hexadecimal digest")
        return state


# PUBLIC API


def derive_run_id(platform: str, project: str, ticket_iid: int) -> str:
    """
    @brief      Build the deterministic, stable run-id for a ticket.
    @details    Derived from the stable ticket reference (never random) so the
                same worktree, branch, container, and state dir are reused
                across restart and resume (design doc 8a).
    @param[in]  platform Git-platform kind (for example "gitlab").
    @param[in]  project  Project slug/path.
    @param[in]  ticket_iid Ticket internal id.
    @return     A stable run-id reused across restart and resume.
    """
    safe_project = project.replace("/", "-").replace(" ", "")
    return f"{platform}-{safe_project}-{ticket_iid}"


def content_hash(title: str, description: str) -> str:
    """
    @brief      Hash the ticket's meaningful content for drift detection.
    @details    A changed hash on re-poll means the spec moved while the run
                was parked or in progress; identity stays the same, only the
                hash flags drift (design doc 8a).
    @param[in]  title Ticket title.
    @param[in]  description Ticket body (including acceptance criteria).
    @return     Hex SHA-256 digest of the normalized content.
    """
    payload = f"{title.strip()}\x00{description.strip()}".encode()
    return hashlib.sha256(payload).hexdigest()


class StateStore:
    """
    @brief   Read/write access to the `.adore/` run state tree.
    @details Persists RunState, the ticket snapshot, and the journal; also
             owns the single-instance lock and the global pause flag. Writes
             are atomic (tmp + replace) so a crash never leaves half a file.
    """

    def __init__(
        self,
        root: str | Path = DEFAULT_STATE_ROOT,
        slug: str = PRODUCT_SLUG,
        *,
        process_alive: Callable[[int], bool] = process_alive,
    ) -> None:
        """
        @brief      Initialize the store rooted at the given directory.
        @param[in]  root Local state root (default ".adore").
        @param[in]  slug Agent slug; names the lock file ("<slug>.lock").
        @param[in]  process_alive Liveness probe used to reclaim a lock whose
                                  owner crashed (injectable for tests).
        """
        self.root = Path(root)
        self.slug = slug
        self._process_alive = process_alive

    # -- paths ----------------------------------------------------------------

    @property
    def runs_root(self) -> Path:
        """
        @brief   The directory holding all per-run state dirs.
        @return  `<root>/runs`.
        """
        return self.root / "runs"

    @property
    def lock_path(self) -> Path:
        """
        @brief   The single-instance lock file path.
        @return  `<root>/<slug>.lock`.
        """
        return self.root / f"{self.slug}.lock"

    def run_dir(self, run_id: str) -> Path:
        """
        @brief      One run's state directory.
        @param[in]  run_id Stable run identifier.
        @return     `<root>/runs/<run-id>`.
        """
        return self.runs_root / run_id

    def exists(self, run_id: str) -> bool:
        """
        @brief      Whether a run has persisted state.
        @param[in]  run_id Stable run identifier.
        @return     True when state.json exists for the run.
        """
        return (self.run_dir(run_id) / STATE_FILE).is_file()

    def cancel_requested(self, run_id: str) -> bool:
        """
        @brief Check a durable request to stop a running executor gate.
        @param[in] run_id Valid run identifier.
        @return True when a cancellation marker exists.
        @exception StateError For an invalid run ID or malformed marker.
        """
        marker = self._cancel_marker(run_id)
        try:
            info = marker.lstat()
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise StateError(f"cannot read cancel request for run {run_id!r}") from exc
        if not stat.S_ISREG(info.st_mode) or info.st_size != 0:
            raise StateError(f"invalid cancel request for run {run_id!r}")
        return True

    def request_cancel(self, run_id: str) -> bool:
        """
        @brief Persist an idempotent cancellation request for a live run.
        @param[in] run_id Valid run identifier.
        @return False if the run became terminal before the request.
        @exception StateError For an invalid run ID or malformed state/marker.
        """
        marker = self._cancel_marker(run_id)
        pending = self.cancel_requested(run_id)
        run = self.load(run_id)
        if run.lifecycle in ("done", "failed", "cancelled"):
            return False
        if pending:
            return True
        try:
            with marker.open("x", encoding="utf-8"):
                pass
        except FileExistsError:
            if not self.cancel_requested(run_id):
                raise StateError(f"invalid cancel request for run {run_id!r}") from None
        return True

    def clear_cancel_request(self, run_id: str) -> None:
        """
        @brief Remove a processed cancellation request.
        @param[in] run_id Valid run identifier.
        @exception StateError For an invalid run ID or malformed marker.
        """
        marker = self._cancel_marker(run_id)
        self.cancel_requested(run_id)
        marker.unlink(missing_ok=True)

    # -- run state ------------------------------------------------------------

    def save(self, state: RunState) -> None:
        """
        @brief      Persist a run's state atomically, stamping timestamps.
        @param[in]  state The RunState to write (updated_at is refreshed;
                          created_at is set on first save).
        """
        now = utc_now_iso()
        state.schema_version = STATE_SCHEMA_VERSION
        if not state.created_at:
            state.created_at = now
        if not state.active_started_at:
            state.active_started_at = now
        state.updated_at = now
        self._write_json(self.run_dir(state.run_id) / STATE_FILE, state.to_dict())

    def load(self, run_id: str) -> RunState:
        """
        @brief      Load a run's persisted state.
        @param[in]  run_id Stable run identifier.
        @return     The reconstructed RunState.
        @exception  FileNotFoundError When the run has no persisted state.
        @exception  StateError When state.json exists but is corrupt (fail
                    closed: the caller skips/escalates, never reinitializes).
        """
        path = self.run_dir(run_id) / STATE_FILE
        with path.open(encoding="utf-8") as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError as exc:
                raise StateError(f"corrupt state.json for run {run_id!r}: {exc}") from exc
        if not isinstance(data, dict):
            raise StateError(f"corrupt state.json for run {run_id!r}: not a JSON object")
        try:
            return RunState.from_dict(data)
        except TypeError as exc:
            raise StateError(f"corrupt state.json for run {run_id!r}: {exc}") from exc

    def list_runs(self) -> list[RunState]:
        """
        @brief   Load every readable run, sorted by run-id.
        @details Corrupt runs are skipped here so operational commands keep
                 working; they stay visible through invalid_runs() and are
                 never silently deleted or reinitialized.
        @return  All loadable runs found under `<root>/runs`.
        """
        runs: list[RunState] = []
        for entry in self._run_dirs():
            try:
                runs.append(self.load(entry.name))
            except StateError:
                continue
        return runs

    def invalid_runs(self) -> list[str]:
        """
        @brief   Run-ids whose state exists on disk but fails to load.
        @details The fail-closed counterpart of list_runs(): these runs need a
                 human (or `adore cleanup`); the poller must not touch them.
        @return  Sorted run-ids with corrupt state.json.
        """
        invalid: list[str] = []
        for entry in self._run_dirs():
            try:
                self.load(entry.name)
            except StateError:
                invalid.append(entry.name)
        return invalid

    def delete_run(self, run_id: str) -> None:
        """
        @brief      Hard-remove a run's entire state directory.
        @details    Destructive; used by `adore delete`. Cancel keeps state.
        @param[in]  run_id Stable run identifier.
        """
        target = self.run_dir(run_id)
        if target.is_dir():
            shutil.rmtree(target)

    # -- ticket snapshot --------------------------------------------------------

    def save_ticket(self, run_id: str, ticket: dict[str, Any]) -> None:
        """
        @brief      Persist the local ticket snapshot taken at pickup.
        @param[in]  run_id Stable run identifier.
        @param[in]  ticket Normalized ticket mapping (title, body, labels...).
        """
        self._write_json(self.run_dir(run_id) / TICKET_FILE, ticket)

    def load_ticket(self, run_id: str) -> dict[str, Any]:
        """
        @brief      Load the persisted ticket snapshot.
        @param[in]  run_id Stable run identifier.
        @return     The ticket mapping saved at pickup.
        @exception  FileNotFoundError When no snapshot exists.
        @exception  StateError When ticket.json exists but is corrupt.
        """
        path = self.run_dir(run_id) / TICKET_FILE
        with path.open(encoding="utf-8") as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError as exc:
                raise StateError(f"corrupt ticket.json for run {run_id!r}: {exc}") from exc
        if not isinstance(data, dict):
            raise StateError(f"corrupt ticket.json for run {run_id!r}: not a JSON object")
        return data

    # -- journal -----------------------------------------------------------------

    def journal(self, run_id: str, event: str, **details: Any) -> None:
        """
        @brief      Append one event to the run's journal (append-only JSONL).
        @param[in]  run_id Stable run identifier.
        @param[in]  event Short event name (for example "gate-advanced").
        @param[in]  details Arbitrary JSON-serializable event fields.
        """
        record = {"ts": utc_now_iso(), "event": event, **details}
        path = self.run_dir(run_id) / JOURNAL_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_journal(self, run_id: str) -> list[dict[str, Any]]:
        """
        @brief      Read the run's journal events in order.
        @details    Malformed lines are skipped, not fatal: journal appends
                    are not atomic, so a crash can leave a torn trailing line.
                    Losing one audit line is safer than blocking the run; the
                    authoritative state lives in state.json, not here.
        @param[in]  run_id Stable run identifier.
        @return     All parseable journal records (empty when none exist).
        """
        path = self.run_dir(run_id) / JOURNAL_FILE
        if not path.is_file():
            return []
        records: list[dict[str, Any]] = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    # -- single-instance lock ------------------------------------------------------

    def acquire_lock(self) -> bool:
        """
        @brief   Take the single-instance lock (exclusive create).
        @details State is locally authoritative, so two pollers on the same
                 repo must never run at once (design doc 12a). A lock left by a
                 CRASHED poller on THIS host - its recorded pid is provably gone
                 - is reclaimed automatically, so a hard crash under
                 systemd/Task Scheduler does not wedge every future start until
                 a manual `adore cleanup`. Every other case fails closed: a live
                 owner, an unreadable record, or a lock from a different host is
                 never stolen. The reclaim + re-create both go through the same
                 atomic `open("x")`, so two racing pollers cannot both win.
        @return  True when acquired; False when another instance holds it.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        if self._try_create_lock():
            return True
        if self.reclaim_stale_lock():
            return self._try_create_lock()
        return False

    def reclaim_stale_lock(self) -> bool:
        """
        @brief   Remove the lock only when its recorded local owner is gone.
        @details A live owner, a different-host owner, or an unreadable/unknown
                 record fails closed and remains in place.
        @return  True only when this call removed a provably stale lock.
        """
        if not self._lock_is_stale():
            return False
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            return False
        return True

    def _try_create_lock(self) -> bool:
        """
        @brief   Atomically create the lock file, recording pid + host.
        @return  True when this call created it; False when it already existed.
        """
        try:
            with self.lock_path.open("x", encoding="utf-8") as handle:
                json.dump(
                    {
                        "pid": os.getpid(),
                        "acquired_at": utc_now_iso(),
                        "host": socket.gethostname(),
                    },
                    handle,
                )
        except FileExistsError:
            return False
        return True

    def _lock_is_stale(self) -> bool:
        """
        @brief   Whether the current lock's owner is provably gone.
        @details Reclaim ONLY when the record is readable, names this host, and
                 carries a pid the liveness probe reports dead. An unreadable
                 record ({}), a missing/invalid pid, or a lock written on a
                 different host all return False (fail closed - keep the lock).
        @return  True when the lock may be safely reclaimed.
        """
        info = self.lock_info()
        if not info:
            return False
        host = info.get("host")
        if host is not None and host != socket.gethostname():
            return False
        pid = info.get("pid")
        if not isinstance(pid, int):
            return False
        return not self._process_alive(pid)

    def release_lock(self) -> None:
        """
        @brief   Release the single-instance lock if held.
        """
        self.lock_path.unlink(missing_ok=True)

    def lock_info(self) -> dict[str, Any] | None:
        """
        @brief   Who holds the lock, if anyone.
        @details A corrupt/unreadable lock file still counts as held (empty
                 record): failing closed here means never starting a second
                 poller just because the lock content is damaged.
        @return  The lock record (pid, acquired_at), {} when held but
                 unreadable, or None when free.
        """
        if not self.lock_path.is_file():
            return None
        try:
            with self.lock_path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    # -- global pause flag -------------------------------------------------------

    def pause(self) -> None:
        """
        @brief   Stop picking new tickets (`adore pause`); in-flight runs continue.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / PAUSE_FILE).write_text(utc_now_iso() + "\n", encoding="utf-8")

    def resume(self) -> None:
        """
        @brief   Allow picking new tickets again (`adore resume`).
        """
        (self.root / PAUSE_FILE).unlink(missing_ok=True)

    def is_paused(self) -> bool:
        """
        @brief   Whether new-ticket pickup is globally paused.
        @return  True when the pause flag is set.
        """
        return (self.root / PAUSE_FILE).is_file()

    # -- internals ------------------------------------------------------------------

    def _cancel_marker(self, run_id: str) -> Path:
        """@brief Keep cancellation markers inside a validated run directory."""
        if not isinstance(run_id, str) or _RUN_ID_RE.fullmatch(run_id) is None:
            raise StateError(f"invalid run ID for cancellation: {run_id!r}")
        return self.run_dir(run_id) / "cancel.request"

    def _run_dirs(self) -> list[Path]:
        """
        @brief   Sorted run directories that carry a state.json.
        @return  Existing run dirs (empty when the store is fresh).
        """
        if not self.runs_root.is_dir():
            return []
        return sorted(
            entry for entry in self.runs_root.iterdir() if (entry / STATE_FILE).is_file()
        )

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        """
        @brief      Write JSON atomically (tmp file + replace).
        @param[in]  path Destination file.
        @param[in]  data JSON-serializable mapping.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        tmp.replace(path)


# END OF FILE
