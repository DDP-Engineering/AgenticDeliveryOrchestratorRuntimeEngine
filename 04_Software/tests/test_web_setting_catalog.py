"""The web setting catalog lists exactly the keys the configuration produces."""

import json
from pathlib import Path

from adore.config import default_config, load_config

_ROOT = Path(__file__).resolve().parents[1]
_CATALOG = _ROOT / "web" / "src" / "settingKeys.json"
# Maps whose entries have project-chosen names; the catalog holds the bare key
# (an empty map) and one `*` pattern for their entries.
_NAMED_MAPS = ("container.runtime_env", "workflow.kind_labels",
               "workflow.stage_timeout_overrides")


def _leaves(value, prefix=""):
    """Dotted keys of the leaves of a nested mapping (non-empty mappings are walked)."""
    if isinstance(value, dict) and value:
        return [leaf for key, child in value.items()
                for leaf in _leaves(child, f"{prefix}.{key}" if prefix else key)]
    return [prefix]


def _catalog_key(key):
    """Replace a project-chosen name in a dotted key with `*`."""
    for name in _NAMED_MAPS:
        if key.startswith(name + "."):
            return name + ".*"
    return key


# PUBLIC API / TESTS


def test_setting_catalog_lists_every_configuration_key():
    """
    The catalog equals the configuration's keys: every leaf of the
             annotated example and of the default configuration and the named
             maps (bare and `*`).
    """
    example = load_config(_ROOT / "config.example.toml").to_dict()
    expected = {_catalog_key(key) for key in _leaves(example) + _leaves(default_config().to_dict())}
    expected |= set(_NAMED_MAPS) | {name + ".*" for name in _NAMED_MAPS}

    catalog = json.loads(_CATALOG.read_text(encoding="utf-8"))

    assert catalog == sorted(catalog)
    assert set(catalog) == expected
