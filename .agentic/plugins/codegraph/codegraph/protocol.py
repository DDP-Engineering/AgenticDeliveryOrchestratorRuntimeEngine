#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file protocol.py
@brief The CodeGraph response envelope, its renderings, budgets and page tokens.
@details Every operation answers with one envelope (protocol version 1). The
         request outcome (`status`), the database state (`index`), freshness
         and indexing capability are separate fields, so an empty successful
         search can never be mistaken for an unavailable index. Three views
         exist: `json` (records), `text-envelope` (the compact text inside the
         envelope, used by AEGIS) and `text` (plain compact text). Budgets
         drop whole records from the end until the chosen view fits.
"""

# IMPORTS

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import re

from codegraph import natives

# CONSTANTS

PROTOCOL = 1
SUPPORTED_PROTOCOLS = (1,)
HARD_BYTE_CAP = 32768
ACTIONS = ("scope", "status", "check", "find", "file", "symbol", "callers", "refs", "index")
STATUSES = ("ok", "ambiguous", "not_found", "expired", "unavailable", "disabled", "error")
INDEX_STATES = ("ready", "missing", "incompatible", "busy", "needs_recovery")
FRESHNESS = ("current", "stale", "unknown", "not_fully_checked")
PYTHON_SUPPORT = ("tested", "untested")
REASONS = ("not_enabled", "plugin_missing", "missing", "incompatible", "busy", "needs_recovery",
           "scope_missing", "protocol", "invalid_request", "page_token_mismatch", "not_found",
           "ambiguous", "expired", "inventory_failed", "destination_not_ignored",
           "destination_tracked", "foreign_database", "plugin_changed", "cancelled", "deadline",
           "indexing_unsupported", "replace_failed", "internal")
HEX32 = re.compile(r"[0-9a-f]{32}")
#: record lists that budgets may shorten, in the order they are shortened
TRIMMABLE = (("details", "candidates"), ("results", None), ("details", "added"),
             ("details", "changed"), ("details", "deleted"), ("details", "failed"),
             ("details", "manifests_changed"))
#: the paged record lists; a budget always leaves at least one of their records
PAGED = (("details", "candidates"), ("results", None))
#: characters a descriptive text field of a kept record may use once the budget is exhausted
LONG_TEXT = 512
#: the fields that shortening may cut; locations and IDs stay exact so citations hold
SHORTENED = ("signature", "qualified_name", "name", "spelling")

_PLUGIN_VERSION: list[str] = []

# HELPER FUNCTIONS


def plugin_version() -> str:
    """@brief The plugin version recorded in MANIFEST.json."""
    if not _PLUGIN_VERSION:
        _PLUGIN_VERSION.append(str(natives.read_manifest().get("plugin_version", "0")))
    return _PLUGIN_VERSION[0]


def _display(record: dict) -> str:
    """@brief The ID shown in text: a unique prefix, or the first 10 characters."""
    return record.get("display_id") or (record.get("id") or "")[:10]


def _symbol_line(record: dict) -> str:
    """@brief One symbol as `qualified(tail) | path:start-end | id=prefix`."""
    name, signature = record.get("name", ""), record.get("signature", "")
    head = re.match(r"(?:async\s+)?(?:def|class)\s+" + re.escape(name), signature)
    if record.get("kind") in ("function", "method", "class") and head:
        tail = signature[head.end():]
    else:
        tail = f": {signature}" if signature else ""
    line = (f"{record.get('qualified_name', '')}{tail} | {record.get('path', '')}:"
            f"{record['start']['line']}-{record['end']['line']} | id={_display(record)}")
    if record.get("citation") == "stale":
        line += " (changed since indexing)"
    return line


def _reference_line(record: dict, prefix: str = "") -> str:
    """@brief One reference as `label kind spelling | path:line | from=prefix`."""
    origin = record.get("from_display") or (record.get("from") or "")[:10] or "-"
    line = (f"{prefix}{record.get('label', '')} {record.get('kind', '')} "
            f"{record.get('spelling', '')} | {record.get('path', '')}:{record.get('line', '')}"
            f" | from={origin}")
    if record.get("citation") == "stale":
        line += " (changed since indexing)"
    return line


def _pairs(mapping: dict) -> str:
    """@brief `a=1, b=2` from a flat mapping, in key order."""
    return ", ".join(f"{key}={value}" for key, value in sorted(mapping.items()))


def _body(env: dict) -> list[str]:
    """@brief The record or detail lines for one action."""
    action, details, results = env["action"], env.get("details") or {}, env.get("results") or []
    lines: list[str] = []
    if env.get("status") == "ambiguous":
        return [_symbol_line(record) for record in results]
    if action == "status" and env.get("indexing_supported") is not None:
        lines.append("indexing: " + (f"supported ({env.get('python_support')})"
                                     if env["indexing_supported"] else "unsupported"))
    if action in ("find", "file"):
        for record in results:
            indent = "  " * max(record.get("depth", 1) - 1, 0) if action == "file" else ""
            lines.append(indent + _symbol_line(record))
    elif action == "symbol":
        if details.get("symbol"):
            lines.append(_symbol_line(details["symbol"]))
        lines += [_reference_line(record, f"{record.get('relation', '')}: ") for record in results]
    elif action == "callers":
        lines += [_reference_line(record, "caller: ") for record in results]
        lines += [_reference_line(record, "candidate: ") for record in details.get("candidates", [])]
    elif action == "refs":
        lines += [_reference_line(record) for record in results]
    elif action in ("status", "check", "scope", "index"):
        for key, value in details.items():
            if isinstance(value, dict):
                value = _pairs(value) or "-"
            elif isinstance(value, list):
                value = ", ".join(str(item) for item in value) or "-"
            lines.append(f"{key}: {value}")
    elif details:
        lines.append(_pairs({key: value for key, value in details.items()
                             if not isinstance(value, (dict, list))}))
    return lines


def record_count(env: dict) -> int:
    """@brief Records shown: results plus candidate callers; the unit page offsets count."""
    return len(env.get("results") or []) + len((env.get("details") or {}).get("candidates", []))

# PUBLIC API


def envelope(action: str, status: str = "ok", *, reason: str | None = None,
             message: str | None = None, index: str | None = None,
             freshness: str | None = None, capability: dict | None = None,
             meta: dict | None = None, results: list | None = None,
             details: dict | None = None, has_more: bool = False,
             next_page: str | None = None) -> dict:
    """
    @brief Build one protocol-1 response envelope.
    @param[in] action The operation answered.
    @param[in] status Request outcome; see STATUSES.
    @param[in] capability `indexing_supported` and `python_support`, or None.
    @param[in] meta `snapshot`, `generation` and `indexed_at` of the served generation.
    @return The envelope with records in `results` and extras in `details`.
    """
    capability = capability or {}
    meta = meta or {}
    return {
        "schema": 1, "provider": "codegraph", "protocol": PROTOCOL,
        "plugin_version": plugin_version(), "action": action, "status": status,
        "reason": reason, "message": message, "index": index, "freshness": freshness,
        "indexing_supported": capability.get("indexing_supported"),
        "python_support": capability.get("python_support"),
        "snapshot": meta.get("snapshot"), "generation": meta.get("generation"),
        "indexed_at": meta.get("indexed_at"),
        "results": list(results or []), "details": dict(details or {}),
        "has_more": has_more, "next_page": next_page,
    }


def validate(env: dict) -> None:
    """
    @brief Check an envelope against the protocol vocabulary.
    @exception ValueError naming the first violation.
    """
    checks = [
        (env.get("schema") == 1, "schema must be 1"),
        (env.get("provider") == "codegraph", "provider must be codegraph"),
        (env.get("protocol") == PROTOCOL, f"protocol must be {PROTOCOL}"),
        (env.get("action") in ACTIONS, "unknown action"),
        (env.get("status") in STATUSES, "unknown status"),
        (env.get("reason") in (*REASONS, None), "unknown reason"),
        (env.get("index") in (*INDEX_STATES, None), "unknown index state"),
        (env.get("freshness") in (*FRESHNESS, None), "unknown freshness"),
        (env.get("indexing_supported") in (True, False, None), "indexing_supported must be bool"),
        (env.get("python_support") in (*PYTHON_SUPPORT, None), "unknown python_support"),
        (env.get("snapshot") is None or bool(HEX32.fullmatch(str(env["snapshot"]))),
         "snapshot must be 32 hexadecimal characters"),
        (env.get("generation") is None or (isinstance(env["generation"], int)
                                           and not isinstance(env["generation"], bool)),
         "generation must be an integer"),
        (isinstance(env.get("has_more"), bool), "has_more must be bool"),
    ]
    for passed, message in checks:
        if not passed:
            raise ValueError(message)


def render_text(env: dict) -> str:
    """@brief The compact text rendering of an envelope."""
    snapshot = env.get("snapshot")
    generation = env.get("generation")
    header = (f"CodeGraph | {env['action']} | {env['status']} | index={env.get('index') or '-'}"
              f" | freshness={env.get('freshness') or '-'}"
              f" | snapshot={snapshot[:10] if snapshot else '-'}"
              f" gen={generation if generation is not None else '-'}")
    footer = f"shown={record_count(env)} | more={'yes' if env.get('has_more') else 'no'}"
    if env.get("next_page"):
        footer += f" | next={env['next_page']}"
    lines = [header, *_body(env), footer]
    if env.get("message"):
        lines.append(env["message"])
    return "\n".join(lines)


def view(env: dict, view_name: str) -> dict:
    """@brief The envelope as sent in `json` or `text-envelope` view."""
    if view_name == "text-envelope":
        shown = {key: value for key, value in env.items() if key not in ("results", "details")}
        shown["text"] = render_text(env)
        return shown
    return {key: value for key, value in env.items() if key != "text"}


def serialize(obj: dict) -> str:
    """@brief Compact single-line JSON."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def output(env: dict, view_name: str) -> str:
    """@brief The exact standard output for an envelope in a view."""
    return render_text(env) if view_name == "text" else serialize(view(env, view_name))


def fit(env: dict, max_bytes: int, view_name: str, next_page=None) -> dict:
    """
    @brief Drop whole records from the end until the view fits the budget.
    @param[in] max_bytes Requested budget; never more than 32768.
    @param[in] next_page Optional callable(records kept) returning a page token.
    @return A shortened copy with `has_more` set when anything was dropped.
    @details One paged record always stays, even over the budget, so that a
             page token always moves forward and paging ends. When what stays
             is still over the budget, its signature, names and spelling are
             cut to 511 characters plus an ellipsis; paths and IDs are never
             cut, so a citation always names a real location.
    """
    limit = min(max_bytes, HARD_BYTE_CAP)
    fitted = copy.deepcopy(env)
    while len(output(fitted, view_name).encode("utf-8")) > limit:
        for section, key in TRIMMABLE:
            records = fitted[section].get(key) if key else fitted[section]
            if records and not ((section, key) in PAGED and record_count(fitted) <= 1):
                records.pop()
                break
        else:
            break
        fitted["has_more"] = True
        if next_page is not None:
            fitted["next_page"] = next_page(record_count(fitted))
    if len(output(fitted, view_name).encode("utf-8")) > limit:
        # what remains is one record too large for the budget: shorten its long
        # text fields so the answer stays far below the 32 KiB cap
        records = [*fitted["results"], *fitted["details"].get("candidates", [])]
        if isinstance(fitted["details"].get("symbol"), dict):
            records.append(fitted["details"]["symbol"])
        for record in records:
            for key in SHORTENED:
                value = record.get(key)
                if isinstance(value, str) and len(value) > LONG_TEXT:
                    record[key] = value[:LONG_TEXT - 1] + "\u2026"
    return fitted


def request_digest(action: str, target: str, ordering: str, limit: int) -> str:
    """@brief 16 hexadecimal characters identifying one paged request."""
    data = json.dumps([action, target, ordering, limit]).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:16]


def encode_page(snapshot: str, digest: str, offset: int) -> str:
    """@brief An opaque base64url page token."""
    raw = f"{snapshot}:{digest}:{offset}".encode("ascii")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_page(token: str) -> tuple[str, str, int]:
    """
    @brief Split a page token into snapshot, request digest and offset.
    @exception ValueError for anything that is not a well-formed token.
    """
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode("ascii")
        snapshot, digest, offset = raw.split(":")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise ValueError("malformed page token") from None
    if not (HEX32.fullmatch(snapshot) and re.fullmatch(r"[0-9a-f]{16}", digest)
            and offset.isdecimal()):
        raise ValueError("malformed page token")
    return snapshot, digest, int(offset)


def exit_code(status: str) -> int:
    """@brief 1 for `error`, otherwise 0."""
    return 1 if status == "error" else 0

# END OF FILE
