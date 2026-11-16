"""Atomic reviewed Pi provider/model/endpoint configuration."""

from copy import deepcopy
import json
import re
import tomllib

from adore.cli import _newline, _set_toml_scalar
from adore.pi_providers import (
    CUSTOM,
    ENDPOINT_APIS,
    MODEL_ID_RE,
    provider_ids,
    thinking_levels,
    valid_endpoint_url,
)
from adore.util import strict_json_loads

#: Virtual edit key of the provider/model/endpoint selection.
CONNECTION_KEY = "executor.connection"
#: Configuration rows edited through CONNECTION_KEY, never one by one.
CONNECTION_KEYS = frozenset({"executor.provider", "executor.model", "executor.thinking",
                             "executor.endpoint.base_url", "executor.endpoint.api"})
_FIELDS = {"provider", "model", "thinking", "base_url", "api"}
_ENDPOINT_HEADER = re.compile(r"\s*\[\s*executor\s*\.\s*endpoint\s*\]\s*(?:#.*)?")
_TABLE_HEADER = re.compile(r"\s*\[")


def _without_endpoint(text: str) -> str:
    """
    Remove the `[executor.endpoint]` table (header through its last line).
    text: Configuration text.
    Returns: The text without the table; unchanged when there is none.
    Raises ValueError: When the endpoint is spelled another way (inline or dotted).
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


def valid_connection(value: object) -> bool:
    """
    Validate the exact provider/model/endpoint transport.
    value: Parsed external JSON.
    Returns: True for a known provider, one model id, and an endpoint
                (http(s) URL and Pi API type) exactly when the provider is custom.
    """
    if not isinstance(value, dict) or set(value) != _FIELDS:
        return False
    if not all(isinstance(value[field], str) for field in _FIELDS):
        return False
    if value["provider"] not in provider_ids() or not MODEL_ID_RE.fullmatch(value["model"]):
        return False
    if value["thinking"] and value["thinking"] not in thinking_levels(
        value["provider"], value["model"]
    ):
        return False
    if value["provider"] == CUSTOM:
        return valid_endpoint_url(value["base_url"]) and value["api"] in ENDPOINT_APIS
    return value["base_url"] == "" and value["api"] == ""


def connection_value(tree: dict) -> dict:
    """
    Project a configuration onto the connection review value.
    tree: Parsed TOML.
    Returns: `{provider, model, thinking, base_url, api}`; the endpoint fields are empty
                unless the provider is custom.
    """
    executor = tree.get("executor") if isinstance(tree.get("executor"), dict) else {}
    endpoint = executor.get("endpoint") if isinstance(executor.get("endpoint"), dict) else {}
    custom = executor.get("provider") == CUSTOM
    return {"provider": executor.get("provider", ""), "model": executor.get("model", ""),
            "thinking": executor.get("thinking", ""),
            "base_url": endpoint.get("base_url", "") if custom else "",
            "api": endpoint.get("api", ENDPOINT_APIS[0]) if custom else ""}


def set_connection(text: str, wire_value: str) -> str:
    """
    Produce an atomic reviewed connection edit preserving unrelated TOML.
    text: Current human TOML.
    wire_value: Strict JSON `{provider, model, thinking, base_url, api}`.
    Returns: Candidate TOML with exactly the connection fields changed.
    Raises ValueError: Invalid value or an unsupported TOML spelling.
    """
    if len(wire_value) > 4096:
        raise ValueError("connection too large")
    value = strict_json_loads(wire_value)
    if not valid_connection(value):
        raise ValueError("invalid connection")
    original = tomllib.loads(text)
    expected = deepcopy(original)
    executor = expected.setdefault("executor", {})
    executor.update(provider=value["provider"], model=value["model"], thinking=value["thinking"])
    executor.pop("endpoint", None)
    changed = _without_endpoint(text)
    # Explicit string literals: a model ID such as "7" or "true" must stay a string.
    # Both values are validated (no quotes, backslashes or control characters).
    changed = _set_toml_scalar(changed, "executor.provider", value["provider"],
                               literal=json.dumps(value["provider"]))
    changed = _set_toml_scalar(changed, "executor.model", value["model"],
                               literal=json.dumps(value["model"]))
    changed = _set_toml_scalar(changed, "executor.thinking", value["thinking"],
                               literal=json.dumps(value["thinking"]))
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
