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
@file test_pi_providers.py
@brief Pi provider catalog, `[executor]` provider schema and endpoint models.json.
@details Offline: the catalog is the shipped file generated from the pinned Pi;
         configurations are written to a temporary folder and validated.
"""

from __future__ import annotations

# IMPORTS
import json
from pathlib import Path
import re

from adore import pi_providers
from adore.config import load_config, validate_config
from adore.pi_providers import (
    ENDPOINT_KEY_VARIABLE,
    CatalogError,
    credential_variable,
    models_json,
    pi_provider,
    secret_names,
)
import pytest

# CONSTANTS

BASE = """
[platform]
kind = "gitlab"
repo = "group/project"

[worktree]
repo_path = "../runtime-project"

[delivery]
reviewers = ["dan.pasare"]
"""
DOCKERFILE = Path(__file__).parents[1] / "docker" / "Dockerfile.executor-base"

# HELPER FUNCTIONS


def _issues(tmp_path: Path, executor: str, extra: str = "") -> list[str]:
    """@brief Validate BASE plus one [executor] body (and optional tables)."""
    path = tmp_path / "config.toml"
    path.write_text(BASE + "\n[executor]\n" + executor + "\n" + extra, encoding="utf-8")
    return validate_config(load_config(path))


# PUBLIC API / TESTS


def test_shipped_catalog_matches_the_pinned_pi_and_lists_key_providers() -> None:
    """@brief The catalog names the image's Pi version, one variable per provider, models."""
    catalog = pi_providers.catalog()
    pinned = re.search(r"pi-coding-agent@(\d+\.\d+\.\d+)", DOCKERFILE.read_text("utf-8"))
    assert pinned and catalog["pi_version"] == pinned.group(1)
    providers = pi_providers.api_key_providers()
    assert providers["openai"]["variable"] == "OPENAI_API_KEY"
    assert providers["anthropic"]["variable"] == "ANTHROPIC_API_KEY"
    assert providers["google"]["variable"] == "GEMINI_API_KEY"
    assert all(item["models"] for item in providers.values())
    # A GitHub token is a forge credential; classifier-only providers list no chat model.
    assert "github-copilot" not in providers and "typesafe" not in providers
    assert pi_providers.provider_ids()[-2:] == ("chatgpt", "custom")
    assert ENDPOINT_KEY_VARIABLE in pi_providers.key_variables()


def test_chatgpt_models_come_from_pis_chatgpt_catalog() -> None:
    """@brief A ChatGPT subscription serves only some OpenAI models; the catalog names them."""
    catalog = pi_providers.catalog()
    models = catalog["chatgpt_models"]
    assert "gpt-5.6-luna" in models
    assert not {"gpt-5.4", "gpt-5.4-mini", "gpt-5.5"} & set(models)
    assert set(models) <= set(pi_providers.api_key_providers()["openai"]["models"])
    assert pi_providers.public_catalog()["chatgpt"] == {"id": "chatgpt", "models": models}


def test_corrupt_catalog_fails_closed(tmp_path: Path, monkeypatch) -> None:
    """@brief A malformed catalog file is an error, never an empty provider list."""
    bad = tmp_path / "pi_catalog.json"
    provider = {"id": "x", "name": "X", "variable": "X_KEY", "models": ["a"]}
    for text in ("{", json.dumps({"pi_version": "1.4.0", "providers": []}),
                 json.dumps({"pi_version": "1.4.0", "providers": [
                     {"id": "x", "name": "X", "variable": "X_KEY", "models": ["a b"]}]}),
                 json.dumps({"pi_version": "1.4.0", "providers": [provider]}),
                 json.dumps({"pi_version": "1.4.0", "providers": [provider],
                             "chatgpt_models": []}),
                 json.dumps({"pi_version": "1.4.0", "providers": [provider],
                             "chatgpt_models": ["a", "a"]}),
                 json.dumps({"pi_version": "1.4.0", "providers": [provider],
                             "chatgpt_models": ["bad id"]})):
        bad.write_text(text, encoding="utf-8")
        monkeypatch.setattr(pi_providers, "CATALOG_PATH", bad)
        pi_providers.catalog.cache_clear()
        with pytest.raises(CatalogError):
            pi_providers.catalog()
    pi_providers.catalog.cache_clear()


def test_catalog_providers_carry_their_hosts() -> None:
    """@brief Every provider names the hosts of Pi's base URLs for the Off allowlist."""
    providers = pi_providers.api_key_providers()
    assert all(1 <= len(item["hosts"]) <= 8 for item in providers.values())
    assert providers["openai"]["hosts"] == ["api.openai.com"]
    assert providers["anthropic"]["hosts"] == ["api.anthropic.com"]
    assert providers["openrouter"]["hosts"] == ["openrouter.ai"]


def test_catalog_hosts_are_validated(tmp_path: Path, monkeypatch) -> None:
    """@brief A provider without hosts, with none or with a malformed one is refused."""
    bad = tmp_path / "pi_catalog.json"
    provider = {"id": "x", "name": "X", "variable": "X_KEY", "models": ["a"],
                "hosts": ["api.x.example"]}

    def write(item: dict) -> None:
        bad.write_text(json.dumps({"pi_version": "1.4.0", "providers": [item],
                                   "chatgpt_models": ["a"]}), encoding="utf-8")
        monkeypatch.setattr(pi_providers, "CATALOG_PATH", bad)
        pi_providers.catalog.cache_clear()

    write(provider)
    assert pi_providers.catalog()["providers"][0]["hosts"] == ["api.x.example"]
    without = {key: value for key, value in provider.items() if key != "hosts"}
    for item in (without, {**provider, "hosts": []}, {**provider, "hosts": ["api.x/v1"]},
                 {**provider, "hosts": ["bad host"]}, {**provider, "hosts": "api.x.example"},
                 {**provider, "hosts": ["h.example"] * 9}):
        write(item)
        with pytest.raises(CatalogError):
            pi_providers.catalog()
    pi_providers.catalog.cache_clear()


def test_provider_choices_map_to_pi_and_their_key_variable() -> None:
    """@brief chatgpt is Pi's openai without a key variable; custom is the endpoint."""
    assert pi_provider("openai") == "openai" and credential_variable("openai") == "OPENAI_API_KEY"
    assert pi_provider("chatgpt") == "openai" and credential_variable("chatgpt") is None
    assert pi_provider("custom") == "adore-endpoint"
    assert credential_variable("custom") == ENDPOINT_KEY_VARIABLE
    assert credential_variable("no-such-provider") is None


@pytest.mark.parametrize("executor", [
    'provider = "openai"\nmodel = "gpt-5.4"',
    'provider = "openrouter"\nmodel = "~openai/gpt-luna-latest"',
    'provider = "chatgpt"\nmodel = "gpt-5.6-luna"',
    'provider = "anthropic"\nmodel = "a-model-pi-does-not-list"',
    'provider = "custom"\nmodel = "qwen/qwen3.5-9b"\n'
    '[executor.endpoint]\nbase_url = "http://192.168.1.20:1234/v1"\napi = "openai-completions"',
    'provider = "custom"\nmodel = "llama3:8b"\n'
    '[executor.endpoint]\nbase_url = "https://models.internal/v1"',
])
def test_valid_provider_model_and_endpoint_are_accepted(tmp_path: Path, executor: str) -> None:
    """@brief API-key providers, chatgpt and custom with its endpoint validate; free text model."""
    assert _issues(tmp_path, executor) == []


@pytest.mark.parametrize(("executor", "named"), [
    ('model = "gpt-5.4"', "[executor] provider"),
    ('provider = "no-such-provider"\nmodel = "gpt-5.4"', "[executor] provider"),
    ('provider = "openai"', "[executor] model"),
    ('provider = "openai"\nmodel = "gpt 5"', "[executor] model"),
    ('provider = "openai"\nmodel = "gpt-5.4"\napi_key = "sk-inline"', "'api_key'"),
    ('provider = "openai"\nmodel = "gpt-5.4"\n[executor.endpoint]\n'
     'base_url = "http://localhost:1234/v1"', "[executor.endpoint]"),
    ('provider = "custom"\nmodel = "m"', "[executor.endpoint] base_url"),
    ('provider = "custom"\nmodel = "m"\n[executor.endpoint]\nbase_url = "ftp://h/v1"',
     "[executor.endpoint] base_url"),
    ('provider = "custom"\nmodel = "m"\n[executor.endpoint]\nbase_url = "http://u:p@h/v1"',
     "[executor.endpoint] base_url"),
    ('provider = "custom"\nmodel = "m"\n[executor.endpoint]\nbase_url = "http://h/v1?k=1"',
     "[executor.endpoint] base_url"),
    ('provider = "custom"\nmodel = "m"\n[executor.endpoint]\nbase_url = "http:///v1"',
     "[executor.endpoint] base_url"),
    ('provider = "custom"\nmodel = "m"\n[executor.endpoint]\nbase_url = \'http://h/"v1\'',
     "[executor.endpoint] base_url"),
    ('provider = "custom"\nmodel = "m"\n[executor.endpoint]\nbase_url = "http://h:99999/v1"',
     "[executor.endpoint] base_url"),
    ('provider = "custom"\nmodel = "m"\n[executor.endpoint]\nbase_url = "http://h/v1"\n'
     'api = "bedrock"', "[executor.endpoint] api"),
    ('provider = "custom"\nmodel = "m"\n[executor.endpoint]\nbase_url = "http://h/v1"\n'
     'key = "sk-inline"', "'key'"),
])
def test_invalid_provider_schema_is_refused_naming_the_key(
        tmp_path: Path, executor: str, named: str) -> None:
    """@brief Each invalid or unknown executor value is refused with the key named."""
    issues = _issues(tmp_path, executor)
    assert any(named in issue for issue in issues), issues


def test_custom_endpoint_can_use_the_managed_local_backend(tmp_path: Path) -> None:
    """@brief A managed native agent directory can host the generated endpoint model."""
    endpoint = ('provider = "custom"\nmodel = "m"\n[executor.endpoint]\n'
                'base_url = "http://127.0.0.1:1234/v1"\n')
    local = "\n[execution]\nbackend = \"local\"\n"
    issues = _issues(tmp_path, endpoint, local)
    assert issues == []
    assert not any("[executor] provider" in issue for issue in _issues(tmp_path, endpoint))


def test_chatgpt_is_refused_for_a_local_run_and_stage_limits_beyond_the_token(
        tmp_path: Path) -> None:
    """@brief A ChatGPT access token lasts about an hour and needs the image's Pi."""
    chatgpt = 'provider = "chatgpt"\nmodel = "gpt-5.6-luna"\n'
    assert not _issues(tmp_path, chatgpt, "\n[budgets]\nper_gate_timeout_seconds = 3000\n")
    local = _issues(tmp_path, chatgpt, "\n[execution]\nbackend = \"local\"\n")
    assert any("[executor] provider" in issue and "local" in issue for issue in local), local
    assert any("ChatGPT sign-in is available only for container projects" in issue
               for issue in local), local
    gate = _issues(tmp_path, chatgpt, "\n[budgets]\nper_gate_timeout_seconds = 3001\n")
    assert any("[budgets] per_gate_timeout_seconds" in issue and "3000" in issue
               for issue in gate), gate
    stage = _issues(tmp_path, chatgpt,
                    "\n[workflow]\nstage_timeout_overrides = { build = 3001 }\n")
    assert any("[workflow] stage_timeout_overrides.build" in issue and "3000" in issue
               for issue in stage), stage
    keyed = 'provider = "openai"\nmodel = "gpt-5.5"\n'
    assert not _issues(tmp_path, keyed, "\n[budgets]\nper_gate_timeout_seconds = 3601\n"
                       "[workflow]\nstage_timeout_overrides = { build = 7200 }\n")


def test_secret_names_add_the_provider_variable_to_additional_names(tmp_path: Path) -> None:
    """@brief A launch receives the provider's key variable plus the configured extra names."""
    path = tmp_path / "config.toml"
    path.write_text(BASE + '\n[executor]\nprovider = "anthropic"\nmodel = "m"\n'
                    'env_keys = ["EXTRA_TOKEN"]\n', encoding="utf-8")
    assert secret_names(load_config(path).executor) == ["ANTHROPIC_API_KEY", "EXTRA_TOKEN"]
    path.write_text(BASE + '\n[executor]\nprovider = "chatgpt"\nmodel = "m"\n', encoding="utf-8")
    assert secret_names(load_config(path).executor) == []


def test_endpoint_models_json_has_the_spike_shape_with_and_without_a_key(tmp_path: Path) -> None:
    """@brief The models.json names the key variable, or a literal placeholder without one."""
    path = tmp_path / "config.toml"
    path.write_text(BASE + '\n[executor]\nprovider = "custom"\nmodel = "qwen/qwen3.5-9b"\n'
                    '[executor.endpoint]\nbase_url = "http://172.27.80.1:1234/v1"\n',
                    encoding="utf-8")
    executor = load_config(path).executor
    assert models_json(executor, has_key=False) == {"providers": {"adore-endpoint": {
        "baseUrl": "http://172.27.80.1:1234/v1", "api": "openai-completions",
        "apiKey": "adore-no-key", "models": [{"id": "qwen/qwen3.5-9b"}]}}}
    keyed = models_json(executor, has_key=True)["providers"]["adore-endpoint"]
    assert keyed["apiKey"] == "$ADORE_ENDPOINT_API_KEY"
    path.write_text(BASE + '\n[executor]\nprovider = "openai"\nmodel = "gpt-5.4"\n',
                    encoding="utf-8")
    assert models_json(load_config(path).executor, has_key=True) is None


# END OF FILE
