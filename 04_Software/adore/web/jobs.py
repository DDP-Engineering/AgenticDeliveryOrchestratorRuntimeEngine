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
@file    jobs.py
@brief   Strict, complete local projections of authorized jobs.
@details The caller supplies authorized profiles. Reads use existing schema-1
         sources without modifying operational recovery behavior or invoking
         external tools. Optimistic content revisions detect changing sources.
"""

# IMPORTS
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit

from adore.profiles import Profile, ProfileStore
from adore.state import RunState, StateError

# CONSTANTS
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}")
_FILES = ("state.json", "ticket.json", "journal.jsonl")
_GROUPS = {
    "working": "active", "publishing": "active", "handoff-pending": "waiting",
    "parked-clarification": "waiting", "awaiting-approval": "waiting",
    "in-review": "review", "done": "terminal", "failed": "terminal",
    "cancelled": "terminal", "stale": "terminal", "handed-off": "terminal",
}
_SECRET = re.compile(
    r"(?i)((?:[\w.-]*(?:token|password|secret|api[_-]?key|authorization)[\w.-]*)"
    r"[\"']?\s*[:=]\s*)"
    r'''("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\s,;}]+)'''
)
_AUTH = re.compile(r"(?i)(\b(?:Bearer|Basic)\s+)\S+")


# DATA MODELS / TYPEDEFINITIONS
class JobReadError(RuntimeError):
    """@brief Safe typed read failure carrying a public code and HTTP status."""

    def __init__(self, code: str, status: int = 503):
        """
        @brief Record a safe failure without source bytes or exception text.
        @param[in] code Stable public error code.
        @param[in] status HTTP failure status.
        """
        super().__init__(code)
        self.code = code
        self.status = status


# LOCAL HELPERS
def _text(value: object, code: str) -> str:
    """
    @brief Validate and redact projected free text.
    @param[in] value Persisted value selected for display.
    @param[in] code Safe failure code for invalid input.
    @return Text with recognized credential values masked.
    @exception JobReadError For malformed text or Unicode.
    """
    if not isinstance(value, str) or "\x00" in value:
        raise JobReadError(code)
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise JobReadError(code) from exc
    return _SECRET.sub(r"\1[REDACTED]", _AUTH.sub(r"\1[REDACTED]", value))


def _stamp(value: object, code: str) -> str | None:
    """
    @brief Normalize an observed aware timestamp; empty legacy values stay unknown.
    @param[in] value Persisted ISO timestamp or legacy empty string.
    @param[in] code Safe failure code for invalid input.
    @return UTC ISO timestamp or None.
    @exception JobReadError For a nonempty malformed or naive timestamp.
    """
    if value == "":
        return None
    if not isinstance(value, str):
        raise JobReadError(code)
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        return parsed.astimezone(UTC).isoformat()
    except (ValueError, OverflowError) as exc:
        raise JobReadError(code) from exc


def _url(value: object) -> str | None:
    """
    @brief Admit absolute credential-free HTTP(S) evidence locations.
    @param[in] value Persisted link or legacy empty string.
    @return Unchanged valid link or None.
    @exception JobReadError For unsafe or malformed evidence links.
    """
    if value == "":
        return None
    if not isinstance(value, str):
        raise JobReadError("job_evidence_corrupt")
    decoded = unquote(value)
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in decoded):
        raise JobReadError("job_evidence_corrupt")
    if "\\" in decoded:
        raise JobReadError("job_evidence_corrupt")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if (parsed.scheme not in {"http", "https"} or not host or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise ValueError
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError
        try:
            ipaddress.ip_address(host)
        except ValueError:
            labels = host.encode("idna").decode("ascii").rstrip(".").split(".")
            if not all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?",
                                    label) for label in labels):
                raise ValueError from None
    except (ValueError, UnicodeError) as exc:
        raise JobReadError("job_evidence_corrupt") from exc
    return value


def _object(raw: bytes, code: str) -> dict:
    """
    @brief Reject malformed JSON, duplicate keys and non-finite constants.
    @param[in] raw Complete persisted bytes.
    @param[in] code Safe failure code for invalid input.
    @return One decoded JSON object.
    @exception JobReadError For unsupported or unparseable JSON.
    """
    def unique(pairs: list[tuple]) -> dict:
        """@brief Preserve one unambiguous value for each persisted object key."""
        value = dict(pairs)
        if len(value) != len(pairs):
            raise ValueError
        return value

    def invalid_constant(_value: str):
        raise ValueError

    try:
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise JobReadError(code) from exc


def _sources(profiles: ProfileStore, items: list[Profile]) -> dict:
    """
    @brief Capture authorized inventories and bytes.
    @param[in] profiles Profile home providing default state roots.
    @param[in] items Already authorized profile metadata.
    @return Mapping of composite source keys to exact bytes or explicit absence.
    @exception JobReadError For unreadable, linked or malformed source locations.
    """
    result = {}
    for item in items:
        result[(item.project_id, "", "profile")] = json.dumps(
            asdict(item), sort_keys=True, ensure_ascii=True).encode()
        root = Path(item.store_root or profiles.default_store_root(item.name)) / "runs"
        try:
            if root.is_symlink():
                raise JobReadError("run_state_corrupt")
            try:
                root.stat()
            except FileNotFoundError:
                result[(item.project_id, "", "runs")] = None
                continue
            if not root.is_dir() or root.is_symlink():
                raise JobReadError("run_state_corrupt")
            entries = sorted(root.iterdir())
            result[(item.project_id, "", "runs")] = json.dumps(
                [path.name for path in entries]).encode()
            for entry in entries:
                if (not entry.is_dir() or entry.is_symlink()
                        or not _RUN_ID.fullmatch(entry.name)):
                    raise JobReadError("run_state_corrupt")
                for name in _FILES:
                    path = entry / name
                    code = ("run_state_corrupt" if name == "state.json" else
                            "run_journal_corrupt" if name == "journal.jsonl" else
                            "job_evidence_corrupt")
                    try:
                        if path.is_symlink():
                            raise JobReadError(code)
                        result[(item.project_id, entry.name, name)] = path.read_bytes()
                    except FileNotFoundError as exc:
                        if name == "state.json":
                            raise JobReadError(code) from exc
                        result[(item.project_id, entry.name, name)] = None
                    except OSError as exc:
                        raise JobReadError(code) from exc
        except OSError as exc:
            raise JobReadError("run_state_corrupt") from exc
    return result


def _journal(raw: bytes | None) -> list[dict]:
    """
    @brief Strictly read evidence JSONL, preserving the operational reader unchanged.
    @param[in] raw Persisted journal bytes or absent legacy evidence.
    @return Validated event objects in saved order.
    @exception JobReadError For malformed records or selected evidence fields.
    """
    if raw is None:
        return []
    events = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        event = _object(line, "run_journal_corrupt")
        if not isinstance(event.get("event"), str) or not event["event"]:
            raise JobReadError("run_journal_corrupt")
        _text(event["event"], "run_journal_corrupt")
        if "ts" in event:
            _stamp(event["ts"], "run_journal_corrupt")
        for key in ("questions", "stage"):
            if key in event:
                _text(event[key], "run_journal_corrupt")
        if "stage" in event and event["stage"] not in {
            "frame", "specify", "design", "build", "validate", "deliver", "done", "publishing",
        }:
            raise JobReadError("run_journal_corrupt")
        if "executor" in event and (not isinstance(event["executor"], str)
                                    or not event["executor"].strip()
                                    or len(event["executor"]) > 200):
            raise JobReadError("run_journal_corrupt")
        events.append(event)
    return events


def _waiting(run: RunState, events: list[dict], ticket_url: str | None,
             mr_url: str | None, platform: str) -> dict:
    """
    @brief Derive actions from evidence matching the current lifecycle and wait.
    @param[in] run Validated state with observed comment/candidate references.
    @param[in] events Validated saved journal events.
    @param[in] ticket_url Safe actual ticket link, when available.
    @param[in] mr_url Safe actual MR/PR link, when available.
    @param[in] platform Recorded forge kind for comment anchors.
    @return Observed waiting evidence or explicit unknown fields.
    """
    result = {"availability": "unknown", "reason": None, "next_action": None,
              "responsible_role": None, "responsible_person": None, "evidence_url": None,
              "source": None}
    # Comment anchors are forge-specific. Unknown platforms keep the actual ticket location.
    def comment_url(comment_id: int) -> str:
        """@brief Locate observed comments using the selected forge's anchor contract."""
        if platform == "gitlab":
            return f"{ticket_url}#note_{comment_id}"
        if platform in {"github", "gitea"}:
            return f"{ticket_url}#issuecomment-{comment_id}"
        return ticket_url
    if run.lifecycle == "parked-clarification":
        parked = next((event for event in reversed(events) if event["event"] == "parked"), {})
        parked_at = _stamp(run.parked_at, "run_state_corrupt")
        event_at = _stamp(parked.get("ts", ""), "run_journal_corrupt")
        if (parked.get("questions") and parked_at and event_at
                and datetime.fromisoformat(event_at) >= datetime.fromisoformat(parked_at)):
            result.update(availability="observed", reason=_text(
                parked["questions"], "run_journal_corrupt"), source="journal:parked")
            if run.question_comment_id and ticket_url:
                result.update(next_action="answer_question_on_ticket",
                              responsible_role="human_responder",
                              evidence_url=comment_url(run.question_comment_id))
    elif (run.lifecycle == "awaiting-approval" and run.approval_comment_id
          and run.approval_presented_at and run.candidate_fingerprint
          and run.candidate_base_ref and ticket_url):
        result.update(availability="observed", reason="candidate_approval_requested",
                      next_action="review_candidate_on_ticket", responsible_role="human_approver",
                      evidence_url=comment_url(run.approval_comment_id),
                      source="state:approval_comment_id")
    elif run.lifecycle == "in-review" and mr_url:
        result.update(availability="observed", reason="draft_review_open",
                      next_action="review_draft_on_forge", responsible_role="human_reviewer",
                      evidence_url=mr_url, source="state:mr_url")
    return result


def _view(item: Profile, run_id: str, sources: dict) -> dict:
    """
    @brief Validate schema-1 inputs and return the job evidence allowlist.
    @param[in] item Authorized owning profile.
    @param[in] run_id Selected safe source-directory identity.
    @param[in] sources Captured bytes and explicit absent legacy sources.
    @return Composite job identity, exact state and safe evidence fields.
    @exception JobReadError For corrupt state, snapshots or journal evidence.
    """
    data = _object(sources[(item.project_id, run_id, "state.json")], "run_state_corrupt")
    try:
        if type(data.get("schema_version")) is not int:
            raise StateError("invalid schema type")
        run = RunState.from_dict(data)
        if run.run_id != run_id:
            raise StateError("identity mismatch")
        for name in ("outcome", "mr_url", "updated_at", "created_at", "approval_presented_at",
                     "parked_at",
                     "candidate_fingerprint", "candidate_base_ref"):
            if not isinstance(getattr(run, name), str):
                raise StateError("invalid projected field")
        for name in ("question_comment_id", "approval_comment_id"):
            value = getattr(run, name)
            if value is not None and (type(value) is not int or value <= 0):
                raise StateError("invalid comment identity")
        for name in ("review_rounds", "stage_failures"):
            if type(getattr(run, name)) is not int or getattr(run, name) < 0:
                raise StateError("invalid counter")
    except (StateError, TypeError, ValueError, AttributeError) as exc:
        raise JobReadError("run_state_corrupt") from exc
    updated = _stamp(run.updated_at, "run_state_corrupt")
    created = _stamp(run.created_at, "run_state_corrupt")
    _stamp(run.approval_presented_at, "run_state_corrupt")
    _stamp(run.parked_at, "run_state_corrupt")
    raw_ticket = sources[(item.project_id, run_id, "ticket.json")]
    ticket = {} if raw_ticket is None else _object(raw_ticket, "job_evidence_corrupt")
    if "iid" in ticket and (type(ticket["iid"]) is not int or ticket["iid"] != run.ticket_iid):
        raise JobReadError("job_evidence_corrupt")
    title = _text(ticket["title"], "job_evidence_corrupt") if "title" in ticket else None
    title = title or None
    ticket_url, mr_url = _url(ticket.get("web_url", "")), _url(run.mr_url)
    raw_journal = sources[(item.project_id, run_id, "journal.jsonl")]
    events = _journal(raw_journal)
    activity = [stamp for stamp in [updated, *(_stamp(event.get("ts", ""),
                "run_journal_corrupt") for event in events)] if stamp is not None]
    last = max(activity, key=datetime.fromisoformat) if activity else None
    detail_url = f"/api/v1/jobs/{item.project_id}/{quote(run_id, safe='')}"
    return {
        "project_id": item.project_id, "project_name": _text(item.name, "job_evidence_corrupt"),
        "project_display_name": _text(item.display_name or item.name, "job_evidence_corrupt"),
        "project_archived": item.archived, "run_id": run.run_id, "ticket_iid": run.ticket_iid,
        "ticket_title": title, "ticket_url": ticket_url, "mr_url": mr_url,
        "lifecycle": run.lifecycle, "stage": run.stage,
        "status_group": _GROUPS[run.lifecycle], "outcome": _text(run.outcome, "run_state_corrupt"),
        "stage_failures": run.stage_failures, "review_rounds": run.review_rounds,
        "created_at": created, "updated_at": updated, "last_activity_at": last,
        "waiting": _waiting(run, events, ticket_url, mr_url, item.platform),
        "evidence_url": detail_url,
        "consumption": {"availability": "unknown"},
        "preparation": ({"status": run.execution["status"],
                         "attempts": run.execution["attempts"],
                         "image": run.execution["plan"]["image"],
                         "fingerprint": run.execution["plan"]["fingerprint"],
                         "steps": run.execution["steps"]}
                        if run.execution and run.execution["plan"]["selection"] else None),
        "timeline": [{"ts": _stamp(event.get("ts", ""), "run_journal_corrupt"),
                      "event": _text(event["event"], "run_journal_corrupt"),
                      "stage": event.get("stage")} for event in events],
        "coverage": {"ticket": "missing" if raw_ticket is None else "present",
                     "journal": "missing" if raw_journal is None else "present",
                     "title": "unknown" if title is None else "observed",
                     "last_activity": "unknown" if last is None else "observed"},
    }


# PUBLIC API
def read_jobs(profiles: ProfileStore, items: list[Profile]) -> tuple[list[dict], str]:
    """
    @brief Capture a complete authorized projection and optimistic source revision.
    @param[in] profiles Profile home used to resolve default state locations.
    @param[in] items Already authorized current and archived profiles.
    @return Validated jobs and digest of selected profile/source content.
    @exception JobReadError For corrupt sources or a mutation during the read.
    @note Caller rechecks current grants/profile metadata before returning to the browser.
    """
    if len({item.project_id for item in items}) != len(items):
        raise JobReadError("project_identity_ambiguous")
    sources = _sources(profiles, items)
    rows = [_view(item, key[1], sources) for item in items
            for key in sorted(sources) if key[0] == item.project_id and key[2] == "state.json"]
    if sources != _sources(profiles, items):
        raise JobReadError("job_snapshot_changed", 409)
    digest = sha256()
    for key, value in sorted(sources.items()):
        digest.update(json.dumps(key).encode())
        digest.update(b"missing" if value is None else sha256(value).digest())
    # Normalize offsets before comparing; textual ISO offsets do not order UTC instants.
    rows.sort(key=lambda row: row["run_id"])
    rows.sort(key=lambda row: row["project_id"])
    rows.sort(key=lambda row: (row["last_activity_at"] is not None,
                              datetime.fromisoformat(row["last_activity_at"])
                              if row["last_activity_at"] else datetime.min.replace(tzinfo=UTC)),
              reverse=True)
    return rows, digest.hexdigest()


# END OF FILE
