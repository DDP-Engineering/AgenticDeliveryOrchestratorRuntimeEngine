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
@file       executor_configuration.py
@brief      Reviewed Pi launch presets and the atomic agent connection edit.
@details    A container project may choose only a preset for `executor.command`
            (its run uses the image's pinned Pi over RPC); a local project
            accepts any validated installed native argv. Provider, model and
            the OpenAI-compatible endpoint change together through one virtual
            edit key, `executor.connection`, so a candidate is never half a
            provider switch: choosing `custom` writes `[executor.endpoint]`,
            choosing any other provider removes it.
"""

# IMPORTS
from copy import deepcopy
import json
import re
import tomllib

from adore.branding import PI_NATIVE_COMMAND
from adore.cli import _newline, _set_toml_scalar
from adore.pi_providers import (
    CUSTOM,
    ENDPOINT_APIS,
    MODEL_ID_RE,
    provider_ids,
    valid_endpoint_url,
)
from adore.util import strict_json_loads

# CONSTANTS
LAUNCH_PRESETS = {"executor.command": (PI_NATIVE_COMMAND,)}
#: Virtual edit key of the provider/model/endpoint selection.
CONNECTION_KEY = "executor.connection"
#: Configuration rows edited through CONNECTION_KEY, never one by one.
CONNECTION_KEYS = frozenset({"executor.provider", "executor.model",
                             "executor.endpoint.base_url", "executor.endpoint.api"})
_FIELDS = {"provider", "model", "base_url", "api"}
_ENDPOINT_HEADER = re.compile(r"\s*\[\s*executor\s*\.\s*endpoint\s*\]\s*(?:#.*)?")
_TABLE_HEADER = re.compile(r"\s*\[")


# HELPER FUNCTIONS


def _without_endpoint(text: str) -> str:
    """
    @brief      Remove the `[executor.endpoint]` table (header through its last line).
    @param[in]  text Configuration text.
    @return     The text without the table; unchanged when there is none.
    @exception  ValueError When the endpoint is spelled another way (inline or dotted).
    """
    lines = text.split("\n")
    start = next((index for index, line in enumerate(lines)
                  if _ENDPOINT_HEADER.fullmatch(line.rstrip("\r"))), None)
    if start is None:
        if (tomllib.loads(text).get("executor") or {}).get("endpoint") is not None:
            raise ValueError("unsupported endpoint spelling")
        return text
    end = next((index for index in range(start + 1, len(lines))
                if _TABLE_HEADER.match(lines[index])), len(lines))
    # Drop the blank lines before the removed table; the next table keeps its own.
    while start > 0 and not lines[start - 1].strip():
        start -= 1
    # A table at the end took the final line feed with it; keep the file's last line ending.
    rest = lines[end:] if end < len(lines) else [""]
    return "\n".join(lines[:start] + rest)


# PUBLIC API


def valid_connection(value: object) -> bool:
    """
    @brief      Validate the exact provider/model/endpoint transport.
    @param[in]  value Parsed external JSON.
    @return     True for a known provider, one model id, and an endpoint
                (http(s) URL and Pi API type) exactly when the provider is custom.
    """
    if not isinstance(value, dict) or set(value) != _FIELDS:
        return False
    if not all(isinstance(value[field], str) for field in _FIELDS):
        return False
    if value["provider"] not in provider_ids() or not MODEL_ID_RE.fullmatch(value["model"]):
        return False
    if value["provider"] == CUSTOM:
        return valid_endpoint_url(value["base_url"]) and value["api"] in ENDPOINT_APIS
    return value["base_url"] == "" and value["api"] == ""


def connection_value(tree: dict) -> dict:
    """
    @brief      Project a configuration onto the connection review value.
    @param[in]  tree Parsed TOML.
    @return     `{provider, model, base_url, api}`; the endpoint fields are empty
                unless the provider is custom.
    """
    executor = tree.get("executor") if isinstance(tree.get("executor"), dict) else {}
    endpoint = executor.get("endpoint") if isinstance(executor.get("endpoint"), dict) else {}
    custom = executor.get("provider") == CUSTOM
    return {"provider": executor.get("provider", ""), "model": executor.get("model", ""),
            "base_url": endpoint.get("base_url", "") if custom else "",
            "api": endpoint.get("api", ENDPOINT_APIS[0]) if custom else ""}


def set_connection(text: str, wire_value: str) -> str:
    """
    @brief      Produce an atomic reviewed connection edit preserving unrelated TOML.
    @param[in]  text Current human TOML.
    @param[in]  wire_value Strict JSON `{provider, model, base_url, api}`.
    @return     Candidate TOML with exactly the connection fields changed.
    @exception  ValueError Invalid value or an unsupported TOML spelling.
    """
    if len(wire_value) > 4096:
        raise ValueError("connection too large")
    value = strict_json_loads(wire_value)
    if not valid_connection(value):
        raise ValueError("invalid connection")
    original = tomllib.loads(text)
    expected = deepcopy(original)
    executor = expected.setdefault("executor", {})
    executor.update(provider=value["provider"], model=value["model"])
    executor.pop("endpoint", None)
    changed = _without_endpoint(text)
    # Explicit string literals: a model ID such as "7" or "true" must stay a string.
    # Both values are validated (no quotes, backslashes or control characters).
    changed = _set_toml_scalar(changed, "executor.provider", value["provider"],
                               literal=json.dumps(value["provider"]))
    changed = _set_toml_scalar(changed, "executor.model", value["model"],
                               literal=json.dumps(value["model"]))
    if value["provider"] == CUSTOM:
        executor["endpoint"] = {"base_url": value["base_url"], "api": value["api"]}
        newline = _newline(changed)
        changed = (changed + ("" if changed.endswith("\n") else newline) + newline
                   + "[executor.endpoint]" + newline
                   + f'base_url = "{value["base_url"]}"' + newline
                   + f'api = "{value["api"]}"' + newline)
    if tomllib.loads(changed) != expected:
        raise ValueError("connection changed unrelated configuration")
    return changed


# END OF FILE
