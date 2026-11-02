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
@file pi_providers.py
@brief Pi providers, models, key variables and the endpoint models.json.
@details The provider catalog (`pi_catalog.json`) is generated from the pinned
         Pi by `02_Tools/generate_pi_catalog.py` (`pi --list-models`, offline):
         Pi's single-variable API-key providers, each with the environment
         variable Pi reads its key from and the models Pi knows. Two ADORE
         choices sit beside them: `chatgpt` (Pi provider `openai` signed in
         with a ChatGPT subscription; the sign-in is not available yet) and
         `custom`, an OpenAI-compatible endpoint that ADORE describes to Pi in
         a generated `models.json` under the provider id `adore-endpoint`.
         A key never enters a file: models.json names the variable
         (`$ADORE_ENDPOINT_API_KEY`) or a literal placeholder for an endpoint
         without a key, because Pi hides a model whose `$VAR` is unset.
"""

from __future__ import annotations

# IMPORTS
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

# CONSTANTS
CATALOG_PATH = Path(__file__).with_name("pi_catalog.json")
CHATGPT = "chatgpt"
CUSTOM = "custom"
#: Pi provider id ADORE gives an OpenAI-compatible endpoint in models.json.
ENDPOINT_PROVIDER = "adore-endpoint"
#: Credential variable of an endpoint key (optional).
ENDPOINT_KEY_VARIABLE = "ADORE_ENDPOINT_API_KEY"
#: Literal key Pi sends to an endpoint that needs none.
ENDPOINT_NO_KEY = "adore-no-key"
#: Pi API types an endpoint may speak (Pi docs/models-configuration.md).
ENDPOINT_APIS = ("openai-completions", "openai-responses", "anthropic-messages",
                 "google-generative-ai")
DEFAULT_ENDPOINT_API = ENDPOINT_APIS[0]
#: One model id: no whitespace, quotes or control characters (OpenRouter
#: aliases start with `~`, local servers use `:` tags and `/` paths).
MODEL_ID_RE = re.compile(r"[A-Za-z0-9~][A-Za-z0-9._:/@+~-]{0,199}")
_PROVIDER_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_VARIABLE_RE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_VERSION_RE = re.compile(r"\d+\.\d+\.\d+")


# DATA MODELS / TYPEDEFINITIONS


class CatalogError(ValueError):
    """@brief The shipped provider catalog is missing or malformed."""


# HELPER FUNCTIONS


def _validated(value: Any) -> dict:
    """
    @brief      Check the catalog's exact shape.
    @param[in]  value Parsed catalog JSON.
    @return     The catalog.
    @exception  CatalogError On any deviation.
    """
    if not isinstance(value, dict) or set(value) != {"pi_version", "providers"}:
        raise CatalogError("catalog keys")
    if not isinstance(value["pi_version"], str) or not _VERSION_RE.fullmatch(value["pi_version"]):
        raise CatalogError("catalog version")
    providers = value["providers"]
    if not isinstance(providers, list) or not providers:
        raise CatalogError("catalog providers")
    seen: set[str] = set()
    for item in providers:
        if (not isinstance(item, dict) or set(item) != {"id", "name", "variable", "models"}
                or not isinstance(item["id"], str) or not _PROVIDER_ID_RE.fullmatch(item["id"])
                or item["id"] in seen or item["id"] in (CHATGPT, CUSTOM, ENDPOINT_PROVIDER)
                or not isinstance(item["name"], str) or not 0 < len(item["name"]) <= 80
                or not isinstance(item["variable"], str)
                or not _VARIABLE_RE.fullmatch(item["variable"])
                or not isinstance(item["models"], list) or not item["models"]
                or not all(isinstance(model, str) and MODEL_ID_RE.fullmatch(model)
                           for model in item["models"])):
            raise CatalogError("catalog provider")
        seen.add(item["id"])
    return value


# PUBLIC API


@lru_cache(maxsize=1)
def catalog() -> dict:
    """
    @brief      The shipped Pi provider catalog, validated once.
    @return     `{"pi_version": str, "providers": [{"id", "name", "variable", "models"}]}`.
    @exception  CatalogError When the file is missing or malformed.
    """
    try:
        return _validated(json.loads(CATALOG_PATH.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, ValueError) as exc:
        raise CatalogError(f"Pi provider catalog unreadable: {exc}") from exc


def api_key_providers() -> dict[str, dict]:
    """
    @brief      Pi's API-key providers by id.
    @return     Provider id -> catalog entry.
    """
    return {item["id"]: item for item in catalog()["providers"]}


def provider_ids() -> tuple[str, ...]:
    """
    @brief      Every accepted `[executor] provider` value.
    @return     The catalog ids, then `chatgpt` and `custom`.
    """
    return (*api_key_providers(), CHATGPT, CUSTOM)


def key_variables() -> frozenset[str]:
    """
    @brief      Every credential variable a provider choice can name.
    @return     The catalog variables plus the endpoint key variable.
    """
    return frozenset({item["variable"] for item in catalog()["providers"]}
                     | {ENDPOINT_KEY_VARIABLE})


def credential_variable(provider: str) -> str | None:
    """
    @brief      The environment variable Pi reads this provider's key from.
    @param[in]  provider `[executor] provider` value.
    @return     The variable; None for `chatgpt` (a sign-in, not a key) and
                for an unknown provider.
    """
    if provider == CUSTOM:
        return ENDPOINT_KEY_VARIABLE
    entry = api_key_providers().get(provider)
    return entry["variable"] if entry else None


def credential_required(provider: str) -> bool:
    """
    @brief      Whether a run cannot start without a credential.
    @param[in]  provider `[executor] provider` value.
    @return     True for API-key providers and `chatgpt`; an endpoint key is optional.
    """
    return provider != CUSTOM


def pi_provider(provider: str) -> str:
    """
    @brief      The provider id Pi is started with (`--provider`).
    @param[in]  provider `[executor] provider` value.
    @return     `openai` for chatgpt, `adore-endpoint` for custom, else the id.
    """
    return {CHATGPT: "openai", CUSTOM: ENDPOINT_PROVIDER}.get(provider, provider)


def valid_endpoint_url(value: object) -> bool:
    """
    @brief      The one rule for an OpenAI-compatible endpoint address.
    @details    Shared by configuration validation, the web connection edit and
                the CLI wizard: http or https, a host, a valid port, at most 512
                characters, no user name, password, query or fragment (a key is
                a credential, never part of the address), and no whitespace,
                control characters, quotes or backslashes (the value is written
                into TOML text).
    @param[in]  value Candidate base URL.
    @return     True when the address is acceptable.
    """
    if (not isinstance(value, str) or not value or len(value) > 512
            or any(ord(char) <= 32 or ord(char) == 127 or char in "\"\\?#" for char in value)):
        return False
    try:
        url = urlsplit(value)
        url.port  # noqa: B018 - raises ValueError for an invalid port
    except ValueError:
        return False
    return (url.scheme in ("http", "https") and bool(url.hostname)
            and url.username is None and url.password is None)


def secret_names(executor) -> list[str]:
    """
    @brief      Names of the secrets a Pi launch receives.
    @param[in]  executor `ExecutorConfig`.
    @return     Sorted `env_keys` plus the provider's credential variable.
    """
    names = set(executor.env_keys)
    variable = credential_variable(executor.provider)
    if variable:
        names.add(variable)
    return sorted(names)


def models_json(executor, has_key: bool) -> dict | None:
    """
    @brief      Pi's models.json for an OpenAI-compatible endpoint.
    @param[in]  executor `ExecutorConfig` (validated).
    @param[in]  has_key Whether ADORE_ENDPOINT_API_KEY holds a value for the run.
    @return     The document for `provider = "custom"`, else None.
    """
    if executor.provider != CUSTOM:
        return None
    return {"providers": {ENDPOINT_PROVIDER: {
        "baseUrl": executor.endpoint.base_url,
        "api": executor.endpoint.api,
        "apiKey": f"${ENDPOINT_KEY_VARIABLE}" if has_key else ENDPOINT_NO_KEY,
        "models": [{"id": executor.model}],
    }}}


def public_catalog() -> dict:
    """
    @brief      The provider choices the web interface offers.
    @return     Pi version, API-key providers, and the chatgpt/custom entries.
    """
    data = catalog()
    return {"pi_version": data["pi_version"], "providers": data["providers"],
            "chatgpt": {"id": CHATGPT}, "custom": {
                "id": CUSTOM, "variable": ENDPOINT_KEY_VARIABLE, "apis": list(ENDPOINT_APIS)}}


# END OF FILE
