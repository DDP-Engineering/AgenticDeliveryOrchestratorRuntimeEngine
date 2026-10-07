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
@file    portable_settings.py
@brief   Strict versioned portable working-rule export and parsing.
@details Complete closed allowlist, exact source compatibility and change-detection
         checksum. Owns no profile enrollment, credential or runtime state writes.
"""

from __future__ import annotations

# IMPORTS
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import secrets
import tempfile
import tomllib

from adore import __version__
from adore.config import default_config, load_config, validate_config

# CONSTANTS
KIND = "adore-project-settings"
SCHEMA_VERSION = 1
CONTRACT = "portable-rules-v1"
MAX_JSON_BYTES = 65536
MAX_SOURCE_BYTES = 524288
MAX_LIMIT = 1_000_000_000
PORTABLE_FIELDS = {
    "polling": (
        "mode",
        "poll_interval_seconds",
        "poll_jitter_seconds",
        "poll_backoff",
        "max_concurrent_runs",
    ),
    "readiness": (
        "require_acceptance_criteria",
        "require_priority_label",
        "require_known_component",
    ),
    "recovery": ("max_stage_failures", "max_transient_retries", "retry_backoff_seconds"),
    "budgets": (
        "max_iterations",
        "max_wall_clock_seconds",
        "per_gate_timeout_seconds",
        "max_cost_usd",
        "max_files_touched",
    ),
}
_NAMED_MAPS = {
    "local.environment": str,
    "container.runtime_env": str,
    "workflow.kind_labels": str,
    "workflow.stage_timeout_overrides": int,
}

# DATA MODELS / TYPEDEFINITIONS


class PortableSettingsError(ValueError):
    """@brief Value-free error at the portable source or package trust boundary."""

    def __init__(self, code: str = "portable_settings_invalid") -> None:
        """
        @brief      Store a fixed error code without including untrusted values.
        @param[in]  code Stable portable error identifier.
        """
        self.code = code
        super().__init__(code)


# LOCAL HELPERS


def _canonical(value: dict) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def _keys(value: object, expected) -> None:
    if type(value) is not dict or set(value) != set(expected):
        raise PortableSettingsError()


def _number(value: object, minimum: int = 0, *, integer: bool = True) -> None:
    """
    @brief      Reject wrong numeric types and unbounded portable limits.
    @param[in]  value Untrusted numeric value.
    @param[in]  minimum Inclusive lower bound.
    @param[in]  integer Require an integer rather than a finite JSON number.
    @exception  PortableSettingsError Value violates the closed numeric domain.
    """
    if (
        type(value) not in ((int,) if integer else (int, float))
        or not minimum <= value <= MAX_LIMIT
        or not math.isfinite(value)
    ):
        raise PortableSettingsError()


def _settings(value: object) -> dict:
    """
    @brief      Validate the complete closed portable shape without partial output.
    @param[in]  value Untrusted portable settings mapping.
    @return     Complete validated mapping.
    @exception  PortableSettingsError Shape, type or bound is invalid.
    """
    _keys(value, PORTABLE_FIELDS)
    for section, names in PORTABLE_FIELDS.items():
        _keys(value[section], names)
        for name in names:
            item = value[section][name]
            if name == "mode":
                if type(item) is not str or item not in ("loop", "once"):
                    raise PortableSettingsError()
            elif name == "poll_backoff" or section == "readiness":
                if type(item) is not bool:
                    raise PortableSettingsError()
            elif name == "retry_backoff_seconds":
                if type(item) is not list or not 1 <= len(item) <= 100:
                    raise PortableSettingsError()
                for seconds in item:
                    _number(seconds)
            else:
                _number(
                    item,
                    0 if name in ("max_cost_usd", "poll_jitter_seconds") else 1,
                    integer=name != "max_cost_usd",
                )
    return value


def _declared(value: object, template: object, prefix: str = "") -> None:
    """
    @brief      Reject unknown declared fields/types before the lenient TOML loader.
    @param[in]  value Untrusted declared TOML value.
    @param[in]  template Existing configuration's recognized structural model.
    @param[in]  prefix Dotted recognized location used for dynamic map domains.
    @exception  PortableSettingsError Unknown or malformed declared source.
    """
    if prefix in _NAMED_MAPS:
        if type(value) is not dict or any(
            type(key) is not str or type(item) is not _NAMED_MAPS[prefix]
            for key, item in value.items()
        ):
            raise PortableSettingsError()
        return
    if type(template) is dict:
        if type(value) is not dict:
            raise PortableSettingsError()
        for key, item in value.items():
            if prefix == "executor" and key not in template:
                _declared(item, {"command": "", "model": ""}, f"executor.{key}")
            elif key not in template or prefix == "executor" and key == "commands":
                raise PortableSettingsError()
            else:
                _declared(item, template[key], f"{prefix}.{key}" if prefix else key)
    elif type(template) is list:
        if type(value) is not list:
            raise PortableSettingsError()
        item_type = type(template[0]) if template else str
        if any(type(item) is not item_type for item in value):
            raise PortableSettingsError()
    elif type(template) is float:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise PortableSettingsError()
    elif type(value) is not type(template):
        raise PortableSettingsError()


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    """
    @brief      Reject duplicate JSON keys at every depth.
    @param[in]  pairs Decoder-provided ordered key/value pairs.
    @return     Fresh unique-key mapping.
    @exception  PortableSettingsError Duplicate key detected.
    """
    result = {}
    for key, value in pairs:
        if key in result:
            raise PortableSettingsError()
        result[key] = value
    return result


def _constant(_value: str) -> None:
    raise PortableSettingsError()


# PUBLIC API


def export_settings(raw: bytes) -> bytes:
    """
    @brief      Export a validated authoritative TOML snapshot as canonical JSON.
    @param[in]  raw Bounded UTF-8 active configuration bytes, never redacted data.
    @return     Deterministic complete envelope bytes with final LF.
    @exception  PortableSettingsError Invalid source structure, config or values.
    """
    try:
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_SOURCE_BYTES:
            raise PortableSettingsError()
        declared = tomllib.loads(raw.decode("utf-8"))
        _declared(declared, default_config().to_dict())
        with tempfile.TemporaryDirectory(prefix="adore-portable-") as temporary:
            path = Path(temporary) / "config.toml"
            path.write_bytes(raw)
            config = load_config(path)
        if validate_config(config):
            raise PortableSettingsError()
        resolved = config.to_dict()
        settings = _settings(
            {
                section: {name: resolved[section][name] for name in names}
                for section, names in PORTABLE_FIELDS.items()
            }
        )
        package = {
            "kind": KIND,
            "schema_version": SCHEMA_VERSION,
            "source": {"product": "ADORE", "version": __version__, "contract": CONTRACT},
            "settings": settings,
        }
        package["checksum"] = sha256(_canonical(package)).hexdigest()
        return _canonical(package) + b"\n"
    except (
        OSError,
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
        OverflowError,
        RecursionError,
    ) as exc:
        raise PortableSettingsError() from exc


def parse_settings(raw: bytes) -> dict:
    """
    @brief      Parse only portable defaults for a compatible new project.
    @param[in]  raw Bounded UTF-8 JSON package, treated as untrusted input.
    @return     Fresh complete portable settings mapping, without enrollment writes.
    @exception  PortableSettingsError Invalid/duplicate/schema/source/checksum input.
    @note       Checksum detects changes and makes no authenticity claim.
    """
    try:
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_JSON_BYTES:
            raise PortableSettingsError()
        package = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant
        )
        _keys(package, ("kind", "schema_version", "source", "settings", "checksum"))
        if (
            package["kind"] != KIND
            or type(package["schema_version"]) is not int
            or package["schema_version"] != SCHEMA_VERSION
        ):
            raise PortableSettingsError()
        _keys(package["source"], ("product", "version", "contract"))
        if package["source"] != {"product": "ADORE", "version": __version__, "contract": CONTRACT}:
            raise PortableSettingsError("portable_settings_incompatible")
        settings = _settings(package["settings"])
        checksum = package.pop("checksum")
        if (
            type(checksum) is not str
            or re.fullmatch(r"[0-9a-f]{64}", checksum) is None
            or not secrets.compare_digest(checksum, sha256(_canonical(package)).hexdigest())
        ):
            raise PortableSettingsError()
        return settings
    except PortableSettingsError:
        raise
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        raise PortableSettingsError() from exc


# END OF FILE
