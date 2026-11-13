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
@file       implementation_settings.py
@brief      Exact verification text and closed Implementation candidate values.
@details    Preserves unrelated human TOML and verifies the exact semantic edit.
"""

# IMPORTS
from copy import deepcopy
import json
import re
import tomllib

from adore.cli import _newline
from adore.util import strict_json_loads
from adore.web.executor_settings import PROVIDER_KEYS

# CONSTANTS
COLLECTION_KEYS = frozenset({"recovery.retry_backoff_seconds", "workflow.stage_timeout_overrides",
                             "executor.env_keys"})
#: The stages whose executor launch a timeout override bounds, matching
#: `adore.config.AEGIS_STAGES`; AEGIS 0.15.0 has no deliver stage.
STAGES = ("frame", "specify", "design", "build", "validate")
MAX_SAFE_INTEGER = 9007199254740991


# PUBLIC API


def valid_collection(key: str, value: object) -> bool:
    """@brief Check the exact supported collection type and its bounded domain.
    @param[in] key Complete configuration key.
    @param[in] value Parsed human or persisted input.
    @return True for a nonempty retry list, closed timeout map or names-only provider list.
    """
    def integer(item: object, minimum: int) -> bool:
        """@brief Reject booleans, fractions and integers beyond browser precision."""
        return type(item) is int and minimum <= item <= MAX_SAFE_INTEGER

    if key == "recovery.retry_backoff_seconds":
        return (isinstance(value, list) and 0 < len(value) <= 1000
                and all(integer(item, 0) for item in value))
    if key == "workflow.stage_timeout_overrides":
        return (isinstance(value, dict) and set(value) <= set(STAGES)
                and all(integer(item, 1) for item in value.values()))
    if key == "executor.env_keys":
        return (isinstance(value, list) and len(value) <= 32
                and all(isinstance(item, str)
                        and re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", item) for item in value)
                and len(set(value)) == len(value))
    return False


def set_collection(text: str, key: str, wire_value: str) -> str:
    """@brief Replace one approved complete collection in human TOML.
    @param[in] text Current TOML with comments and original line endings.
    @param[in] key One of the supported collection keys.
    @param[in] wire_value Strict JSON string of the complete proposed value.
    @return TOML whose parsed meaning differs only at the requested key.
    @exception ValueError Malformed value or unsupported human TOML spelling.
    """
    if key not in COLLECTION_KEYS or len(wire_value) > 32768:
        raise ValueError("unsupported collection")
    value = strict_json_loads(wire_value)
    if not valid_collection(key, value):
        raise ValueError("invalid collection")
    original = tomllib.loads(text)
    if key == "executor.env_keys" and not set(value) <= (
            PROVIDER_KEYS | set(original.get("executor", {}).get("env_keys", []))):
        raise ValueError("unknown new provider variable")
    expected = deepcopy(original)
    section, name = key.split(".")
    expected.setdefault(section, {})[name] = value
    literal = (json.dumps(value, separators=(",", ":")) if isinstance(value, list)
               else "{ " + ", ".join(f"{stage} = {value[stage]}"
                                      for stage in STAGES if stage in value) + " }")
    newline = _newline(text)
    lines = text.splitlines(keepends=True)

    def header(line: str) -> dict | None:
        """@brief Parse only a complete table-header line, including its comment."""
        if not re.match(r"^\s*\[", line):
            return None
        try:
            return tomllib.loads(line)
        except tomllib.TOMLDecodeError:
            return None

    inside = False
    index = 0
    while index < len(lines):
        table = header(lines[index])
        if table is not None:
            if table == {section: {name: {}}}:
                end = index + 1
                while end < len(lines) and header(lines[end]) is None:
                    end += 1
                del lines[index:end]
                inside = False
                continue
            inside = table == {section: {}}
        if inside and re.match(rf"^\s*(?:{name}|\"{name}\"|'{name}')\s*=", lines[index]):
            for end in range(index + 1, len(lines) + 1):
                try:
                    fragment = tomllib.loads("".join(lines[index:end]))
                except tomllib.TOMLDecodeError:
                    continue
                if set(fragment) != {name}:
                    raise ValueError("unsupported collection spelling")
                lines[index:end] = [f"{name} = {literal}{newline}"]
                changed = "".join(lines)
                if tomllib.loads(changed) != expected:
                    raise ValueError("collection edit changed other settings")
                return changed
            raise ValueError("unterminated collection")
        index += 1
    position = next((i for i, line in enumerate(lines) if header(line) == {section: {}}), None)
    if position is None:
        changed = "".join(lines)
        if changed and not changed.endswith("\n"):
            changed += newline
        changed += f"{newline}[{section}]{newline}{name} = {literal}{newline}"
    else:
        if not lines[position].endswith("\n"):
            lines[position] += newline
        lines.insert(position + 1, f"{name} = {literal}{newline}")
        changed = "".join(lines)
    if tomllib.loads(changed) != expected:
        raise ValueError("collection edit changed other settings")
    return changed


# END OF FILE
