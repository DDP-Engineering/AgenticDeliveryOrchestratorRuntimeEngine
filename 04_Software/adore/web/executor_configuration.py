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
@brief      Closed reviewed coding-agent selection.
@details    Updates one agent's command/model and default with exact TOML scope.
"""

# IMPORTS
from copy import deepcopy
import re
import tomllib

from adore.cli import _set_toml_scalar
from adore.util import strict_json_loads

# CONSTANTS
LAUNCH_PRESETS = {
    "executor.opencode.command": (
        "opencode run --dir {worktree} -m {model} --format json {prompt}",
    ),
    "executor.pi.command": ("pi -p --mode json --model {model} {prompt}",),
    "executor.codex.command": (
        "codex exec --json --model {model} --ignore-user-config "
        "--disable plugins --dangerously-bypass-approvals-and-sandbox {prompt}",
    ),
    "executor.qwen.command": ("qwen -p --model {model} --output-format json {prompt}",),
}
SUPPORTED_AGENTS = ("opencode", "pi", "codex", "qwen")


# PUBLIC API
def valid_selection(value: object) -> bool:
    """@brief Validate the exact bounded names-only selection transport.
    @param[in] value Parsed external JSON.
    @return True for one supported agent, nonempty command and model identifier.
    """
    return (isinstance(value, dict) and set(value) == {"agent", "command", "model"}
            and isinstance(value["agent"], str) and value["agent"] in SUPPORTED_AGENTS
            and isinstance(value["command"], str) and 0 < len(value["command"]) <= 4096
            and "{prompt}" in value["command"]
            and not any(ord(char) < 32 for char in value["command"])
            and isinstance(value["model"], str)
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", value["model"]) is not None)


def selection_value(tree: dict) -> dict:
    """@brief Project the configured default and its command/model as review values.
    @param[in] tree Parsed TOML using executor.<agent> tables.
    @return Complete selection map; invalid/missing configuration fails validation later.
    """
    executor = tree.get("executor", {})
    agent = executor.get("default", "opencode")
    entry = executor.get(agent, {})
    return {"agent": agent, "command": entry.get("command", ""), "model": entry.get("model", "")}


def set_selection(text: str, wire_value: str) -> str:
    """@brief Produce an atomic reviewed agent selection preserving unrelated TOML.
    @param[in] text Current human TOML.
    @param[in] wire_value Strict JSON selection including command and model.
    @return Candidate TOML with exactly the selected fields changed.
    @exception ValueError Invalid selection, unsupported preset or unsafe TOML spelling.
    """
    if len(wire_value) > 8192:
        raise ValueError("selection too large")
    value = strict_json_loads(wire_value)
    if not valid_selection(value):
        raise ValueError("invalid selection")
    original = tomllib.loads(text)
    agent = value["agent"]
    existing = original.get("executor", {}).get(agent, {}).get("command")
    if (original.get("execution", {}).get("backend", "container") != "local"
            and value["command"] != existing
            and value["command"] not in LAUNCH_PRESETS[f"executor.{agent}.command"]):
        raise ValueError("unsupported launch preset")
    expected = deepcopy(original)
    executor = expected.setdefault("executor", {})
    executor["default"] = agent
    entry = executor.setdefault(agent, {})
    entry.update(command=value["command"], model=value["model"])
    changed = _set_toml_scalar(text, "executor.default", agent)
    for field in ("command", "model"):
        changed = _set_toml_scalar(changed, f"executor.{agent}.{field}", value[field])
    if tomllib.loads(changed) != expected:
        raise ValueError("selection changed unrelated configuration")
    return changed


# END OF FILE
