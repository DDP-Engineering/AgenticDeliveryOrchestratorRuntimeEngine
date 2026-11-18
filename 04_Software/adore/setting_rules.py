"""Shared project setting domains used by core validation and web guidance."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
from typing import TYPE_CHECKING

from adore.util import parse_duration

if TYPE_CHECKING:
    from adore.config import Config

NUMERIC_LIMITS = json.loads(
    Path(__file__).with_name("setting_limits.json").read_text(encoding="utf-8")
)
STAGES = ("frame", "specify", "design", "build", "validate")
CONSTRAINTS = NUMERIC_LIMITS["_constraints"]
LABEL_MAX_LENGTH = CONSTRAINTS["label_length"]
ENDPOINT_MAX_LENGTH = CONSTRAINTS["endpoint_length"]
MAX_REVIEWERS = CONSTRAINTS["reviewers"]
MAX_RETRY_DELAYS = CONSTRAINTS["retry_delays"]
MAX_RETRY_DELAY_SECONDS = CONSTRAINTS["retry_delay_seconds"]


def numeric_domain(key: str, provider: str = "") -> dict:
    """Return inclusive effective bounds; stage overrides inherit the common domain."""
    lookup = (
        "budgets.per_gate_timeout_seconds"
        if key.startswith("workflow.stage_timeout_overrides.")
        else key
    )
    rule = NUMERIC_LIMITS.get(lookup)
    if rule is None:
        return {}
    return {
        "minimum": rule["minimum"],
        "maximum": rule.get("provider_maximum", {}).get(provider, rule["maximum"]),
        "unit": rule["unit"],
    }


def numeric_default(key: str) -> int | float | str | None:
    """Return the one declared default used by config, wizard and enrollment."""
    return NUMERIC_LIMITS[key]["default"]


def valid_numeric(key: str, value: object, provider: str = "") -> bool:
    """Check exact numeric types and inclusive bounds, including duration syntax."""
    domain = numeric_domain(key, provider)
    if not domain:
        return False
    if key == "clarification.answer_timeout":
        if not isinstance(value, str):
            return False
        try:
            value = parse_duration(value)
        except ValueError:
            return False
    if key == "budgets.max_cost_usd":
        if type(value) not in (int, float):
            return False
        if isinstance(value, float) and not math.isfinite(value):
            return False
    elif type(value) is not int:
        return False
    return domain["minimum"] <= value <= domain["maximum"]


def numeric_issues(config: Config, *, budgets: bool) -> list[str]:
    """Validate the budget subset or the other shared numeric project settings."""
    issues = []
    for key in NUMERIC_LIMITS:
        if key.startswith("_") or key.endswith(".*") or key.startswith("budgets.") != budgets:
            continue
        value = config
        for part in key.split("."):
            value = getattr(value, part)
        if not valid_numeric(key, value, config.executor.provider):
            domain = numeric_domain(key, config.executor.provider)
            kind = ("a finite number" if key == "budgets.max_cost_usd" else
                    "a positive duration" if key == "clarification.answer_timeout"
                    else "an integer")
            issues.append(f"[{key.split('.')[0]}] {key.split('.', 1)[1]} must be {kind} "
                          f"in {domain['minimum']}..{domain['maximum']} {domain['unit']}")
    return issues


def valid_label(value: object) -> bool:
    """One forge tag name; adapter-specific restrictions remain in the adapter."""
    return (
        isinstance(value, str)
        and 1 <= len(value) <= LABEL_MAX_LENGTH
        and value == value.strip()
        and not any(ord(c) < 32 or ord(c) == 127 for c in value)
    )


def valid_collection(key: str, value: object, provider: str = "") -> bool:
    """Use the same collection domain for TOML and reviewed web edits."""
    if key in {"platform.work_item_types", "platform.closed_states"}:
        return (
            isinstance(value, list)
            and 1 <= len(value) <= 32
            and all(
                isinstance(v, str)
                and 0 < len(v) <= 128
                and v == v.strip()
                and not any(ord(c) < 32 for c in v)
                for v in value
            )
            and len(set(value)) == len(value)
        )
    if key == "recovery.retry_backoff_seconds":
        return (
            isinstance(value, list)
            and 1 <= len(value) <= MAX_RETRY_DELAYS
            and all(type(v) is int and 0 <= v <= MAX_RETRY_DELAY_SECONDS for v in value)
        )
    if key == "workflow.stage_timeout_overrides":
        return (
            isinstance(value, dict)
            and set(value) <= set(STAGES)
            and all(
                valid_numeric(f"workflow.stage_timeout_overrides.{stage}", seconds, provider)
                for stage, seconds in value.items()
            )
        )
    if key == "executor.env_keys":
        return (
            isinstance(value, list)
            and len(value) <= 32
            and all(isinstance(v, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", v) for v in value)
            and len(set(value)) == len(value)
        )
    return False
