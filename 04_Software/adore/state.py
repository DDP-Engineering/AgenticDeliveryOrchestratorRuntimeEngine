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
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import tempfile
from threading import local
from typing import Any

from adore.branding import DEFAULT_STATE_ROOT, PRODUCT_SLUG
from adore.preparation import PreparationError, validate_plan
from adore.util import iso_to_datetime, process_alive, strict_json_loads, utc_now_iso

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
#: Stages a persisted run may name. ADORE conducts frame to done and points at
#: publishing.
_STAGES = {"frame", "specify", "design", "build", "validate", "done", "publishing"}
_LIFECYCLES = {
    "working", "parked-clarification", "awaiting-approval", "publishing",
    "in-review", "failed", "done", "cancelled", "stale", "handed-off", "handoff-pending",
}


# LOCAL HELPERS
def _clock_stamp(value: object) -> datetime:
    """
    @brief Refuse malformed durable clock evidence before budget accounting.
    @param[in] value Untrusted saved or current timestamp.
    @return A timezone-aware datetime.
    @exception StateError For nontext, invalid or timezone-free evidence.
    """
    try:
        if not isinstance(value, str):
            raise ValueError
        stamp = datetime.fromisoformat(value)
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError
        return stamp
    except (TypeError, ValueError, OverflowError) as exc:
        raise StateError("run-state active clock requires aware ISO timestamps") from exc


# DATA MODELS / TYPEDEFINITIONS


class StateError(RuntimeError):
    """
    @brief   Raised when persisted state exists but cannot be trusted.
    @details Fail-closed signal for corrupt/unreadable state.json or
             ticket.json (for example after a crash or manual edit). Callers
             skip or escalate the affected run; they never reinitialize it.
    """


class LockHeldError(RuntimeError):
    """@brief Another owner holds the requested admission or run scope."""


@dataclass
class RunState:
    """
    @brief   In-memory view of a single run's persisted state.
    @details Everything the orchestrator needs to resume a run after a restart:
             the recorded workflow, active/historical AEGIS tasks, stage, recoverable
             failure counters, durable notification outbox, approval-bound
             candidate fingerprint, signaling ids, and isolated resources.
    """

    run_id: str
    ticket_iid: int
    schema_version: int = STATE_SCHEMA_VERSION
    #: Selected once at claim. Constructor defaults never fill missing stored keys.
    workflow: str = "aegis"
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
    #: sit in review for days.
    pipeline_reported: str = ""
    notification_outbox: list[dict[str, Any]] = field(default_factory=list)
    candidate_fingerprint: str = ""
    candidate_base_ref: str = ""
    #: Candidate fingerprint of the last publication that reached review.
    #: Stage done spans approval, publication and review, so this is what
    #: tells a published candidate from one still waiting to publish.
    published_fingerprint: str = ""
    approval_presented_at: str = ""
    approval_comment_id: int | None = None
    approval_label_removed: bool = False
    validation_evidence: dict[str, Any] = field(default_factory=dict)
    #: Optional closed execution/preparation record. Empty means legacy mode.
    execution: dict[str, Any] = field(default_factory=dict)
    outcome: str = ""
    checkpoint_remote_commit: str = ""
    checkpoint_error: str = ""
    #: Effective clock anchor, shifted over inactive intervals to retain consumed work.
    active_started_at: str = ""
    #: A reserved job has not begun any executor/provisioning work yet.
    execution_pending: bool = False
    created_at: str = ""
    updated_at: str = ""

    def active_work_seconds(self, now: str) -> float:
        """
        @brief Return cumulative working time; inactive lifecycles freeze at last save.
        @param[in] now Aware current timestamp for an actively working job.
        @return Nonnegative elapsed seconds from the effective active-clock anchor.
        @exception StateError For malformed or timezone-free clock evidence.
        """
        end = _clock_stamp(now if self.lifecycle == "working" else self.updated_at)
        elapsed = max(0.0, (end - _clock_stamp(self.active_started_at)).total_seconds())
        return 0.0 if self.execution_pending else elapsed

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
        @details    Missing or wrong schema, unknown keys and missing keys are
                    rejected, so foreign state is never reinterpreted as a run
                    and state of another ADORE build is never filled in
                    with defaults (no migrations while ADORE is in development).
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
        missing = sorted(known - set(data))
        if missing:
            raise StateError(
                f"run-state schema {STATE_SCHEMA_VERSION} is missing keys {missing}; "
                "it was written by another ADORE build"
            )
        state = cls(**data)
        if not isinstance(state.workflow, str) or state.workflow not in {"aegis", "direct"}:
            raise StateError(f"run-state carries unknown workflow {state.workflow!r}")
        if state.workflow == "direct":
            if state.active_task_id is not None or state.task_ids != []:
                raise StateError("run-state direct workflow cannot carry AEGIS task bindings")
            if isinstance(state.stage, str) and state.stage in {"frame", "specify", "design"}:
                raise StateError(f"run-state direct workflow cannot name stage {state.stage!r}")
        if state.active_started_at != "" or state.created_at or state.updated_at:
            _clock_stamp(state.active_started_at)
        if type(state.iterations) is not int or state.iterations < 0:
            raise StateError("run-state iterations must be nonnegative")
        if type(state.execution_pending) is not bool:
            raise StateError("run-state execution_pending must be boolean")
        if state.execution_pending and (state.iterations != 0 or state.active_task_id is not None
                                        or state.task_ids != []):
            raise StateError("run-state pending execution cannot contain executor/task progress")
        if type(state.parked_polls) is not int or state.parked_polls < 0:
            raise StateError("run-state parked_polls must be nonnegative")
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
        validate_execution_record(state.execution)
        if not isinstance(state.checkpoint_error, str):
            raise StateError("run-state checkpoint_error must be text")
        if not isinstance(state.checkpoint_remote_commit, str) or (
            state.checkpoint_remote_commit
            and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", state.checkpoint_remote_commit) is None
        ):
            raise StateError("run-state checkpoint_remote_commit must be a commit digest")
        for name in ("candidate_fingerprint", "candidate_base_ref", "published_fingerprint"):
            value = getattr(state, name)
            if value and re.fullmatch(r"[0-9a-f]{40,64}", value) is None:
                raise StateError(f"run-state {name} must be a hexadecimal digest")
        return state


# HELPER FUNCTIONS


def validate_execution_record(record: object) -> None:
    """
    @brief Validate an additive closed execution identity/recovery record.
    @param[in] record Persisted untrusted execution mapping or legacy empty mapping.
    @exception StateError For corrupt identity, plan, status or preparation evidence.
    """
    if not isinstance(record, dict):
        raise StateError("run-state execution must be an object")
    if not record:
        return
    keys = {"plan", "resource", "status", "attempts", "steps", "history", "reprepare"}
    try:
        if set(record) != keys:
            raise ValueError("closed structure")
        validate_plan(record["plan"])
        if record["plan"]["backend"] == "local":
            from adore.local_execution import validate_local_resource
            from adore.local_process import LocalExecutionError

            if (record["status"] != "not-required" or type(record["attempts"]) is not int
                    or record["attempts"] != 0 or record["steps"] != []
                    or record["history"] != [] or record["reprepare"] is not False
                    or not isinstance(record["resource"], dict)):
                raise ValueError("local preparation evidence is unsupported")
            if record["resource"]:
                try:
                    validate_local_resource(record["resource"])
                except LocalExecutionError as exc:
                    raise ValueError("local resource identity") from exc
            return
        if (
            record["status"]
            not in {
                "pending",
                "running",
                "success",
                "failed",
                "interrupted",
                "cancelled",
                "not-required",
            }
            or type(record["attempts"]) is not int
            or not 0 <= record["attempts"] <= 3
            or type(record["reprepare"]) is not bool
            or not isinstance(record["steps"], list)
            or len(record["steps"]) > 32
            or not isinstance(record["history"], list)
            or len(record["history"]) > 3
        ):
            raise ValueError("status/attempts/evidence")
        if len(record["steps"]) > len(record["plan"]["steps"]):
            raise ValueError("step count")
        if record["status"] != "not-required" and not record["plan"]["selection"]:
            raise ValueError("recipe status without selection")
        if record["attempts"] > record["plan"]["policy"]["execution"]["preparation_max_attempts"]:
            raise ValueError("attempt bound")
        if record["status"] in {"running", "success", "failed", "interrupted", "cancelled"} and (
            record["attempts"] < 1 or not record["resource"]
        ):
            raise ValueError("preparation without resource/attempt")
        resource = record["resource"]
        if not isinstance(resource, dict):
            raise ValueError("resource")
        if resource and (
            set(resource) != {"container_id", "image_id"}
            or not isinstance(resource["container_id"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", resource["container_id"])
            or not isinstance(resource["image_id"], str)
            or not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", resource["image_id"])
        ):
            raise ValueError("resource identity")
        step_keys = {
            "index",
            "name",
            "started_at",
            "finished_at",
            "exit_code",
            "timed_out",
            "cancelled",
        }
        for index, step in enumerate(record["steps"]):
            if (
                not isinstance(step, dict)
                or set(step) != step_keys
                or type(step["index"]) is not int
                or step["index"] != index
                or step["name"] != record["plan"]["steps"][index]["name"]
                or type(step["exit_code"]) is not int
                or not -255 <= step["exit_code"] <= 255
                or type(step["timed_out"]) is not bool
                or type(step["cancelled"]) is not bool
                or iso_to_datetime(step["started_at"]) is None
                or iso_to_datetime(step["finished_at"]) is None
            ):
                raise ValueError("step evidence")
            stamps = [datetime.fromisoformat(step[key].replace("Z", "+00:00"))
                      for key in ("started_at", "finished_at")]
            if any(stamp.tzinfo is None for stamp in stamps) or stamps[1] < stamps[0]:
                raise ValueError("step timestamp order/timezone")
        if record["status"] == "success" and (
            not resource
            or record["attempts"] < 1
            or len(record["steps"]) != len(record["plan"]["steps"])
            or any(
                step["exit_code"] != 0 or step["timed_out"] or step["cancelled"]
                for step in record["steps"]
            )
        ):
            raise ValueError("success without complete evidence")
        if record["status"] == "not-required" and (
            record["plan"]["selection"] or record["attempts"] or record["steps"]
            or resource and not record["plan"]["policy"]["container"].get("system_packages")
        ):
            raise ValueError("legacy preparation mismatch")
        last_attempt = 0
        for history in record["history"]:
            if not isinstance(history, dict) or set(history) != {
                "attempt",
                "status",
                "resource",
                "steps",
            }:
                raise ValueError("history")
            if (
                type(history["attempt"]) is not int
                or not last_attempt < history["attempt"] <= record["attempts"]
                or history["status"] in {"pending", "not-required"}
            ):
                raise ValueError("history ordering")
            last_attempt = history["attempt"]
            historic = {
                **record,
                "attempts": history["attempt"],
                "status": history["status"],
                "resource": history["resource"],
                "steps": history["steps"],
                "history": [],
                "reprepare": False,
            }
            validate_execution_record(historic)
    except (
        PreparationError,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        AttributeError,
        OverflowError,
    ) as exc:
        raise StateError("run-state execution record is corrupt") from exc


def _run_id_stem(platform: str, project: str) -> str:
    """
    @brief      The ticket-independent start of every run-id of one project.
    @param[in]  platform Git-platform kind (for example "gitlab").
    @param[in]  project  Project slug/path.
    @return     "<platform>-<project with / as - and spaces removed>-".
    """
    safe_project = project.replace("/", "-").replace(" ", "")
    return f"{platform}-{safe_project}-"


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
    return f"{_run_id_stem(platform, project)}{ticket_iid}"


def run_id_pattern(platform: str, project: str) -> re.Pattern[str]:
    """
    @brief      Match exactly the run-ids `derive_run_id` makes for one project.
    @details    The ticket part must be digits only, so a project whose path
                merely extends this one ("owner/repo-tools" for "owner/repo")
                never matches. The pattern is anchored at the end, so `match`
                and `fullmatch` agree.
    @param[in]  platform Git-platform kind (for example "gitlab").
    @param[in]  project  Project slug/path.
    @return     Compiled pattern for this project's run-ids.
    """
    return re.compile(re.escape(_run_id_stem(platform, project)) + r"[0-9]+\Z")


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
        self.before_write: Callable[[], object] | None = None
        self._scoped_locks = local()

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
        if self.before_write is not None:
            self.before_write()
        marker = self._cancel_marker(run_id)
        pending = self.cancel_requested(run_id)
        run = self.load(run_id)
        if run.lifecycle in ("done", "failed", "cancelled",
                             "handoff-pending", "handed-off"):
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
        if self.before_write is not None:
            self.before_write()
        marker = self._cancel_marker(run_id)
        self.cancel_requested(run_id)
        marker.unlink(missing_ok=True)

    # -- run state ------------------------------------------------------------

    def save(self, state: RunState) -> None:
        """
        @brief      Persist state atomically, stamping timestamps and freezing inactive work time.
        @param[in]  state The RunState to write (updated_at is refreshed;
                          created_at is set on first save).
        """
        now = utc_now_iso()
        path = self.run_dir(state.run_id) / STATE_FILE
        if path.exists():
            previous = self.load(state.run_id)
            # Move the effective anchor over waiting time, including repeated
            # inactive saves. Resume keeps all work consumed before the wait.
            if previous.execution_pending:
                # A queued admission has consumed no active work on any read,
                # cancellation or crash path. Persist activation before effects.
                state.active_started_at = now
            elif previous.lifecycle != "working":
                waiting = max(0.0, (_clock_stamp(now)
                                   - _clock_stamp(previous.updated_at)).total_seconds())
                state.active_started_at = (
                    _clock_stamp(previous.active_started_at) + timedelta(seconds=waiting)
                ).isoformat()
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
                data = strict_json_loads(handle.read())
            except ValueError as exc:
                raise StateError(f"corrupt state.json for run {run_id!r}: {exc}") from exc
        if not isinstance(data, dict):
            raise StateError(f"corrupt state.json for run {run_id!r}: not a JSON object")
        try:
            state = RunState.from_dict(data)
            _clock_stamp(state.active_started_at)
            return state
        except TypeError as exc:
            raise StateError(f"corrupt state.json for run {run_id!r}: {exc}") from exc
        except StateError as exc:
            raise StateError(
                f"{exc} (run {run_id!r}; delete {self.run_dir(run_id)} to remove it)"
            ) from exc

    def list_runs(self) -> list[RunState]:
        """
        @brief   Load every readable run, sorted by run-id.
        @details Corrupt runs are skipped here so operational commands keep
                 working; they stay visible through invalid_runs() and are
                 never silently deleted or reinitialized. State removed after
                 enumeration is omitted; unrelated I/O errors still propagate.
        @return  All loadable runs found under `<root>/runs`.
        """
        runs: list[RunState] = []
        for entry in self._run_dirs():
            try:
                runs.append(self.load(entry.name))
            except (StateError, FileNotFoundError):
                continue
        return runs

    def invalid_runs(self) -> list[str]:
        """
        @brief   Run-ids whose state exists on disk but fails to load.
        @details The fail-closed counterpart of list_runs(): these runs need a
                 human (or `adore cleanup`); the poller must not touch them.
                 State removed after enumeration is not corrupt and is omitted;
                 unrelated I/O errors still propagate.
        @return  Sorted run-ids with corrupt state.json.
        """
        invalid: list[str] = []
        for entry in self._run_dirs():
            try:
                self.load(entry.name)
            except FileNotFoundError:
                continue
            except StateError:
                invalid.append(entry.name)
        return invalid

    def delete_run(self, run_id: str) -> None:
        """
        @brief      Hard-remove a run's entire state directory.
        @details    Destructive; used by `adore delete`. Cancel keeps state.
        @param[in]  run_id Stable run identifier.
        """
        if self.before_write is not None:
            self.before_write()
        target = self.run_dir(run_id)
        if target.is_dir():
            shutil.rmtree(target)

    # -- ticket snapshot --------------------------------------------------------

    def save_dispatch(self, run_id: str, revision: str, *, started: bool = False) -> None:
        """@brief Persist exact initial dispatch authority independently of the audit log.
        @param[in] run_id Run already protected by its lifecycle lock.
        @param[in] revision Exact SHA-256 of the admitted configuration.
        @param[in] started Irreversibly consume initial-launch authority before effects.
        @exception StateError Missing, corrupt or already consumed dispatch evidence.
        """
        if not isinstance(revision, str) or not re.fullmatch(r"[a-f0-9]{64}", revision):
            raise StateError("invalid dispatch configuration revision")
        if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
            raise StateError("invalid run dispatch identity")
        path = self.run_dir(run_id) / "dispatch.json"
        if started:
            previous = self.load_dispatch(run_id)
            if previous["status"] != "queued" or previous["config_revision"] != revision:
                raise StateError("dispatch authority already consumed or changed")
        elif path.exists() or path.is_symlink():
            raise StateError("dispatch evidence already exists")
        self._write_json(path, {"schema": 1, "config_revision": revision,
                                "status": "started" if started else "queued"})

    def load_dispatch(self, run_id: str) -> dict[str, Any]:
        """@brief Read closed dispatch schema 1; absence/corruption never grants launch authority.
        @exception StateError Invalid evidence; explicit operator recovery is required.
        """
        if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
            raise StateError("invalid run dispatch identity")
        path = self.run_dir(run_id) / "dispatch.json"
        try:
            if path.is_symlink():
                raise ValueError("linked evidence")
            with path.open(encoding="utf-8") as handle:
                raw = handle.read(4097)
            if len(raw) > 4096:
                raise ValueError("oversized evidence")
            value = strict_json_loads(raw)
            if (not isinstance(value, dict)
                    or set(value) != {"schema", "config_revision", "status"}
                    or type(value["schema"]) is not int or value["schema"] != 1
                    or not isinstance(value["config_revision"], str)
                    or not re.fullmatch(r"[a-f0-9]{64}", value["config_revision"])
                    or value["status"] not in ("queued", "started")):
                raise ValueError("invalid evidence")
        except (OSError, ValueError, TypeError, RecursionError) as exc:
            raise StateError(
                f"invalid dispatch evidence for {run_id}; inspect or delete {path}"
            ) from exc
        return value

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

    def request_handoff(self, run_id: str) -> None:
        """
        @brief Atomically request ownership transfer without editing conductor state.
        @param[in] run_id Existing safe run identity.
        @exception StateError When the run is corrupt or already released.
        """
        if self.before_write is not None:
            self.before_write()
        if _RUN_ID_RE.fullmatch(run_id) is None or run_id in {".", ".."}:
            raise StateError("handoff requires a safe run identity")
        run = self.load(run_id)
        if run.lifecycle in {"done", "cancelled"}:
            raise StateError("completed or cancelled runs cannot be handed off")
        path = self.run_dir(run_id) / "handoff-request.json"
        fd, temporary = tempfile.mkstemp(prefix=".handoff-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"schema": 1, "run_id": run_id,
                           "requested_at": utc_now_iso()}, handle)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def handoff_requested(self, run_id: str) -> bool:
        """
        @brief Read the durable request with exact identity and schema validation.
        @param[in] run_id Run owned by the calling conductor.
        @return True when a trusted request exists.
        @exception StateError When request data is corrupt or foreign.
        """
        path = self.run_dir(run_id) / "handoff-request.json"
        try:
            data = strict_json_loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return False
        except (OSError, ValueError) as exc:
            raise StateError(f"invalid handoff request: {exc}") from exc
        if (not isinstance(data, dict) or set(data) != {"schema", "run_id", "requested_at"}
                or type(data["schema"]) is not int or data["schema"] != 1
                or data["run_id"] != run_id or not isinstance(data["requested_at"], str)
                or not data["requested_at"]):
            raise StateError("invalid handoff request identity/schema")
        return True

    def clear_handoff_request(self, run_id: str) -> None:
        """@brief Remove a request after durable ownership transfer."""
        if self.before_write is not None:
            self.before_write()
        (self.run_dir(run_id) / "handoff-request.json").unlink(missing_ok=True)

    # -- journal -----------------------------------------------------------------

    def journal(self, run_id: str, event: str, **details: Any) -> None:
        """
        @brief      Append one event to the run's journal (append-only JSONL).
        @param[in]  run_id Stable run identifier.
        @param[in]  event Short event name (for example "gate-advanced").
        @param[in]  details Arbitrary JSON-serializable event fields.
        """
        record = {"ts": utc_now_iso(), "event": event, **details}
        if self.before_write is not None:
            self.before_write()
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

    @contextmanager
    def run_lock(self, run_id: str) -> Iterator[None]:
        """@brief Hold one crash-released, thread-reentrant lifecycle lock.
        @param[in] run_id Exact safe run identity.
        @exception LockHeldError Another process or store owns this run.
        @exception StateError Invalid identity or unavailable lock storage.
        @note Lock files remain present; only the kernel lock proves ownership.
        """
        if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
            raise StateError("invalid run lock identity")
        with self._scope_lock("run-" + run_id):
            yield

    @contextmanager
    def _scope_lock(self, name: str) -> Iterator[None]:
        """@brief Lock a stable inode without unlink/reclaim races on either host OS."""
        held = getattr(self._scoped_locks, "held", None)
        if held is None:
            held = self._scoped_locks.held = set()
        if name in held:
            yield
            return
        directory = self.root / "locks"
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StateError("cannot create lifecycle lock storage") from exc
        path = directory / (name + ".lock")
        if directory.is_symlink() or path.is_symlink():
            raise StateError("linked lifecycle lock storage")
        try:
            handle = path.open("a+b")
        except OSError as exc:
            raise StateError("cannot open lifecycle lock") from exc
        acquired = False
        try:
            if os.name == "nt":
                import msvcrt
                # Locking a byte beyond EOF is supported on Windows. No metadata
                # write is needed, so an occupied inode is never modified.
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    if exc.errno in (13, 11, 36):
                        raise LockHeldError("run lifecycle is owned by another conductor") from exc
                    raise StateError("cannot acquire lifecycle lock") from exc
            else:
                import fcntl
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise LockHeldError("run lifecycle is owned by another conductor") from exc
                except OSError as exc:
                    raise StateError("cannot acquire lifecycle lock") from exc
            acquired = True
            held.add(name)
            yield
        finally:
            try:
                if acquired:
                    held.remove(name)
                    if os.name == "nt":
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()

    def owns_run_lock(self, run_id: str) -> bool:
        """@brief Whether this thread already conducts the run under a kernel lock."""
        return "run-" + run_id in getattr(self._scoped_locks, "held", set())

    def run_locked(self, run_id: str) -> bool:
        """@brief Observe foreign lifecycle ownership without relying on PID age.
        @param[in] run_id Exact run to observe.
        @return True only while another store or thread holds its kernel lock.
        """
        try:
            with self.run_lock(run_id):
                return False
        except LockHeldError:
            return True

    @contextmanager
    def execution_slot(self, run_id: str) -> Iterator[None]:
        """@brief Retain a reserved executor place through final backend cleanup."""
        if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
            raise StateError("invalid execution slot identity")
        with self._scope_lock("execution-" + run_id):
            yield

    def execution_slots(self) -> set[str]:
        """@brief Return live cleanup/execution reservations, including removed run state.
        @return Set of run identities with a held kernel execution slot.
        """
        result = set()
        for path in (self.root / "locks").glob("execution-*.lock"):
            run_id = path.name[len("execution-"):-len(".lock")]
            # The current thread's reservation also counts for other run IDs.
            if "execution-" + run_id in getattr(self._scoped_locks, "held", set()):
                result.add(run_id)
                continue
            try:
                with self.execution_slot(run_id):
                    pass
            except LockHeldError:
                result.add(run_id)
        return result

    @contextmanager
    def admission_lock(self) -> Iterator[None]:
        """@brief Serialize short local reservations and preserve operator exclusion."""
        with self._scope_lock("admission"):
            if not self.acquire_lock():
                raise LockHeldError("another instance holds the admission lock")
            try:
                yield
            finally:
                self.release_lock()

    def acquire_lock(self) -> bool:
        """
        @brief   Take the project admission/operator lock (exclusive create).
        @details Short local admission transactions serialize capacity and
                 uniqueness. Run kernel locks separately protect each lifecycle.
                 A lock left by a CRASHED local operator - its PID is provably gone
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
        if self.before_write is not None:
            self.before_write()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / PAUSE_FILE).write_text(utc_now_iso() + "\n", encoding="utf-8")

    def resume(self) -> None:
        """
        @brief   Allow picking new tickets again (`adore resume`).
        """
        if self.before_write is not None:
            self.before_write()
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
        if self.before_write is not None:
            self.before_write()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        if self.before_write is not None:
            self.before_write()
        tmp.replace(path)


# END OF FILE
