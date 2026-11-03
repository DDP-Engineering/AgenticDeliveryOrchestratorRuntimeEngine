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
@file test_web_setting_catalog.py
@brief The web setting catalog lists exactly the keys the configuration produces.
@details The Configuration page's help texts are keyed by this catalog; a
         setting added to the configuration must be catalogued (and so get
         help texts) before the suite passes.
"""

import json
from pathlib import Path

from adore.config import default_config, load_config

# CONSTANTS

_ROOT = Path(__file__).resolve().parents[1]
_CATALOG = _ROOT / "web" / "src" / "settingKeys.json"
# Maps whose entries have project-chosen names; the catalog holds the bare key
# (an empty map) and one `*` pattern for their entries.
_NAMED_MAPS = ("local.environment", "container.runtime_env", "workflow.kind_labels",
               "workflow.stage_timeout_overrides")

# HELPER FUNCTIONS


def _leaves(value, prefix=""):
    """@brief Dotted keys of the leaves of a nested mapping (non-empty mappings are walked)."""
    if isinstance(value, dict) and value:
        return [leaf for key, child in value.items()
                for leaf in _leaves(child, f"{prefix}.{key}" if prefix else key)]
    return [prefix]


def _catalog_key(key):
    """@brief Replace a project-chosen name in a dotted key with `*`."""
    for name in _NAMED_MAPS:
        if key.startswith(name + "."):
            return name + ".*"
    return key


# PUBLIC API / TESTS


def test_setting_catalog_lists_every_configuration_key():
    """
    @brief   The catalog equals the configuration's keys: every leaf of the
             annotated example and of the default configuration and the named
             maps (bare and `*`).
    """
    example = load_config(_ROOT / "config.example.toml").to_dict()
    expected = {_catalog_key(key) for key in _leaves(example) + _leaves(default_config().to_dict())}
    expected |= set(_NAMED_MAPS) | {name + ".*" for name in _NAMED_MAPS}

    catalog = json.loads(_CATALOG.read_text(encoding="utf-8"))

    assert catalog == sorted(catalog)
    assert set(catalog) == expected
