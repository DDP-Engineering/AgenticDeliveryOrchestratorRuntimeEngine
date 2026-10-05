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
@file    test_portable_settings.py
@brief   Portable working-rule public contract tests.
@details Offline source, deterministic roundtrip and hostile JSON boundaries.
"""

# IMPORTS
from hashlib import sha256
from importlib import import_module, util
import json
from pathlib import Path

from adore import __version__
import pytest

# CONSTANTS
EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.toml"

# PUBLIC API / TESTS


def test_portable_public_export_exists_and_roundtrips():
    """@brief Export provides deterministic values, not identity or host data."""
    assert util.find_spec("adore.portable_settings") is not None, "public portable export missing"
    portable = import_module("adore.portable_settings")
    raw = EXAMPLE.read_bytes()
    encoded = portable.export_settings(raw)
    assert encoded == portable.export_settings(raw)
    package = json.loads(encoded)
    assert package["kind"] == "adore-project-settings"
    assert package["schema_version"] == 1
    assert package["source"] == {
        "product": "ADORE",
        "version": __version__,
        "contract": "portable-rules-v1",
    }
    assert portable.parse_settings(encoded) == package["settings"]
    assert set(package["settings"]) == {"polling", "readiness", "recovery", "budgets"}
    assert set(package["settings"]["polling"]) == {
        "mode",
        "poll_interval_seconds",
        "poll_jitter_seconds",
        "poll_backoff",
        "max_concurrent_runs",
    }
    assert b"OPENCODE" not in encoded and b"worktrees" not in encoded
    changed = raw.replace(b"max_iterations           = 20", b"max_iterations           = 37")
    assert (
        portable.parse_settings(portable.export_settings(changed))["budgets"]["max_iterations"]
        == 37
    )


def test_portable_omits_recognized_nested_secrets_and_rejects_unknown_source():
    """@brief Known excluded data never leaks; unknown source structure rejects."""
    portable = import_module("adore.portable_settings")
    raw = EXAMPLE.read_bytes()
    secret = b"SECRET-SENTINEL"
    source = raw.replace(
        b'runtime_env = { UV_LINK_MODE = "copy" }',
        b'runtime_env = { UV_LINK_MODE = "copy", PRIVATE_SECRET = "SECRET-SENTINEL" }',
    )
    result = portable.export_settings(source)
    assert secret not in result and b"PRIVATE_SECRET" not in result
    assert result == portable.export_settings(raw)
    for extra in (
        b'\n[unknown]\nsecret="SECRET-SENTINEL"\n',
        b'\n[polling.unexpected]\nsecret="SECRET-SENTINEL"\n',
        b'\n[executor.opencode.extra]\nsecret="SECRET-SENTINEL"\n',
    ):
        with pytest.raises(portable.PortableSettingsError) as error:
            portable.export_settings(raw + extra)
        assert "SECRET" not in str(error.value)


@pytest.mark.parametrize(
    "change",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("schema_version", "1"),
        ("kind", "config"),
        ("settings", []),
        ("source", {}),
        ("checksum", "0" * 64),
        ("extra", {"secret": "SECRET"}),
    ],
)
def test_portable_rejects_envelope_corruption(change):
    """@brief Schema, type, checksum and unknown envelope data reject atomically."""
    portable = import_module("adore.portable_settings")
    package = json.loads(portable.export_settings(EXAMPLE.read_bytes()))
    package[change[0]] = change[1]
    with pytest.raises(portable.PortableSettingsError):
        portable.parse_settings(json.dumps(package).encode())


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("polling", "mode", "SECRET"),
        ("polling", "poll_interval_seconds", True),
        ("polling", "poll_interval_seconds", 1.0),
        ("polling", "poll_interval_seconds", 0),
        ("polling", "poll_interval_seconds", 1_000_000_001),
        ("polling", "poll_backoff", 1),
        ("polling", "unknown", "SECRET"),
        ("readiness", "require_priority_label", {"secret": "SECRET"}),
        ("recovery", "retry_backoff_seconds", []),
        ("recovery", "retry_backoff_seconds", [False]),
        ("recovery", "retry_backoff_seconds", [-1]),
        ("recovery", "retry_backoff_seconds", [1] * 101),
        ("budgets", "max_cost_usd", -1),
        ("budgets", "max_cost_usd", True),
        ("budgets", "max_cost_usd", float("inf")),
        ("budgets", "max_cost_usd", 1_000_000_001),
    ],
)
def test_portable_rejects_malformed_values_with_recomputed_checksum(section, key, value):
    """@brief A checksum cannot authorize malformed or secret-bearing payloads."""
    portable = import_module("adore.portable_settings")
    package = json.loads(portable.export_settings(EXAMPLE.read_bytes()))
    package["settings"][section][key] = value
    package.pop("checksum")
    package["checksum"] = sha256(
        json.dumps(package, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()
    with pytest.raises(portable.PortableSettingsError) as error:
        portable.parse_settings(json.dumps(package).encode())
    assert "SECRET" not in str(error.value)


def test_portable_requires_exact_compatible_source_and_complete_fields():
    """@brief Consumers reject unsupported source/fields rather than guessing."""
    portable = import_module("adore.portable_settings")
    for alter in (
        lambda p: p["source"].update(version="999.0.0"),
        lambda p: p["source"].update(contract="other"),
        lambda p: p["source"].update(product="other"),
        lambda p: p["source"].update(endpoint="SECRET"),
        lambda p: p["settings"]["budgets"].pop("max_cost_usd"),
        lambda p: p["settings"].update(container={"runtime_env": {"TOKEN": "SECRET"}}),
    ):
        package = json.loads(portable.export_settings(EXAMPLE.read_bytes()))
        alter(package)
        with pytest.raises(portable.PortableSettingsError):
            portable.parse_settings(json.dumps(package).encode())


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"null",
        b"[]",
        b"{",
        b"\xff",
        b" " * 65537,
        b'{"kind":1,"kind":2}',
        b'{"a":{"b":1,"b":2}}',
        b'{"a":NaN}',
        b"[" * 1100 + b"]" * 1100,
    ],
    ids=[
        "empty",
        "null",
        "array",
        "syntax",
        "encoding",
        "oversize",
        "duplicate",
        "nested-duplicate",
        "nan",
        "depth",
    ],
)
def test_portable_parser_rejects_bad_json(raw):
    """@brief Size, encoding, duplicates, nonfinite and nesting failures are typed."""
    portable = import_module("adore.portable_settings")
    with pytest.raises(portable.PortableSettingsError):
        portable.parse_settings(raw)


@pytest.mark.parametrize(
    "raw",
    [b"", b"\xff", b"[bad", b" " * 524289, b"[polling]\npoll_interval_seconds = true"],
    ids=["empty", "encoding", "syntax", "oversize", "boolean-limit"],
)
def test_portable_source_rejects_invalid_configuration(raw):
    """@brief Invalid authoritative sources never produce best-effort exports."""
    portable = import_module("adore.portable_settings")
    with pytest.raises(portable.PortableSettingsError):
        portable.export_settings(raw)


def test_portable_rejects_duplicates_in_otherwise_valid_package():
    """@brief Duplicate identical allowed fields cannot hide behind a valid checksum."""
    portable = import_module("adore.portable_settings")
    encoded = portable.export_settings(EXAMPLE.read_bytes())
    for original, duplicate in (
        (b'"schema_version":1', b'"schema_version":1,"schema_version":1'),
        (b'"poll_backoff":true', b'"poll_backoff":true,"poll_backoff":true'),
        (b'"product":"ADORE"', b'"product":"ADORE","product":"ADORE"'),
    ):
        assert original in encoded
        with pytest.raises(portable.PortableSettingsError):
            portable.parse_settings(encoded.replace(original, duplicate))
    package = json.loads(encoded)
    assert portable.parse_settings(json.dumps(package, indent=2).encode()) == package["settings"]


def test_portable_valid_zero_cap_and_false_rules_reproduce():
    """@brief Working-rule boundary values remain explicit rather than defaulted."""
    portable = import_module("adore.portable_settings")
    source = EXAMPLE.read_bytes().replace(b"max_cost_usd             = 5.0", b"max_cost_usd = 0")
    source = source.replace(b"poll_backoff          = true", b"poll_backoff = false")
    # Use TOML section append via existing declaration replacements, preserving other keys.
    import re

    source = re.sub(rb"max_cost_usd\s*=\s*5\.0", b"max_cost_usd = 0", source)
    source = re.sub(rb"poll_backoff\s*=\s*true", b"poll_backoff = false", source)
    source = re.sub(rb"max_iterations\s*=\s*20", b"max_iterations = 1000000000", source)
    values = portable.parse_settings(portable.export_settings(source))
    assert values["budgets"]["max_cost_usd"] == 0
    assert values["budgets"]["max_iterations"] == 1_000_000_000
    assert values["polling"]["poll_backoff"] is False


@pytest.mark.parametrize(
    "original,replacement",
    [
        (
            b'runtime_env = { UV_LINK_MODE = "copy" }',
            b'runtime_env = { TOKEN = { secret = "SECRET" } }',
        ),
        (b"max_iterations           = 20", b"max_iterations = false"),
        (b"poll_backoff          = true", b'poll_backoff = "SECRET"'),
    ],
)
def test_portable_rejects_malformed_known_source_values(original, replacement):
    """@brief Recognized nested maps and scalar domains also reject corrupt input."""
    portable = import_module("adore.portable_settings")
    source = EXAMPLE.read_bytes()
    if original not in source:
        import re

        key = original.split(b" ")[0]
        source = re.sub(key + rb"\s*=.*", replacement, source)
    else:
        source = source.replace(original, replacement)
    with pytest.raises(portable.PortableSettingsError):
        portable.export_settings(source)


# END OF FILE
