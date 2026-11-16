"""Closed wire structure for one project settings Save."""

import re

from adore.util import strict_json_loads
from adore.web.executor_configuration import CONNECTION_KEY, CONNECTION_KEYS

BATCH_KEY = "settings.batch"
MAX_BATCH_EDITS = 100
_KEY = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+")


def parse_batch(wire: str) -> tuple[tuple[str, str], ...]:
    """
    Decode a bounded set of exact nonoverlapping edit targets.
    wire: JSON array of key/value objects using existing wire values.
    Returns: Members sorted by key for deterministic preparation.
    Raises ValueError: Invalid structure, size, duplicate or overlapping key.
    """
    value = strict_json_loads(wire)
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_BATCH_EDITS:
        raise ValueError("invalid settings batch")
    edits: dict[str, str] = {}
    for entry in value:
        if (not isinstance(entry, dict) or set(entry) != {"key", "value"}
                or not isinstance(entry["key"], str) or not _KEY.fullmatch(entry["key"])
                or not isinstance(entry["value"], str)
                or entry["key"] == BATCH_KEY or entry["key"] in edits):
            raise ValueError("invalid settings batch member")
        key = entry["key"]
        if any(key.startswith(prior + ".") or prior.startswith(key + ".") for prior in edits):
            raise ValueError("overlapping settings batch targets")
        edits[key] = entry["value"]
    if CONNECTION_KEY in edits and CONNECTION_KEYS.intersection(edits):
        raise ValueError("overlapping connection targets")
    return tuple(sorted(edits.items()))
