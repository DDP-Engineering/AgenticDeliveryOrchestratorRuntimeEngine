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
@file endpoint_probe.py
@brief Check a configured compatible model through the selected execution backend.
@details Native probes reuse the selected account/environment and owned scopes.
         Container probes use the project's image and egress policy.
         The probe never falls back to an API-host connection or pulls images.
"""

from __future__ import annotations

# IMPORTS
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from uuid import uuid4

from adore.isolation import ContainerManager

# CONSTANTS
_PROBE = r'''
import json, os, sys, urllib.error, urllib.request
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None
url = os.environ["ADORE_PROBE_URL"].rstrip("/") + "/chat/completions"
model = os.environ["ADORE_PROBE_MODEL"]
payload = {"model": model, "messages": [{"role": "user", "content": "Call the probe tool."}],
           "tools": [{"type": "function", "function": {"name": "probe",
           "description": "Confirm tool support",
           "parameters": {"type": "object", "properties": {}}}}],
           "tool_choice": "required", "stream": True, "max_tokens": 32}
headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
key = os.environ.get("ADORE_PROBE_AUTH_ENV", "")
if key:
    secret = os.environ.get(key, "")
    if not secret:
        print("credential-missing"); sys.exit(2)
    headers["Authorization"] = "Bearer " + secret
request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
try:
    with urllib.request.build_opener(NoRedirect).open(request, timeout=5) as response:
        if response.status != 200:
            print("http-error"); sys.exit(2)
        found = False
        for index, line in enumerate(response):
            if index >= 128 or len(line) > 65536:
                print("tool-stream-incompatible"); sys.exit(2)
            if not line.startswith(b"data: "):
                continue
            body = line[6:].strip()
            if body == b"[DONE]":
                break
            event = json.loads(body)
            for choice in event.get("choices", []):
                if choice.get("delta", {}).get("tool_calls"):
                    found = True
        print("ready" if found else "tool-stream-incompatible")
        sys.exit(0 if found else 2)
except urllib.error.HTTPError as error:
    print("redirect-rejected" if 300 <= error.code < 400 else "http-" + str(error.code))
    sys.exit(2)
except Exception:
    print("endpoint-unreachable-or-incompatible")
    sys.exit(2)
'''


# PUBLIC API
def probe_endpoint(config, runner) -> dict[str, str | bool]:
    """
    @brief Probe an OpenCode chat-completions endpoint in a disposable container.
    @param[in] config Validated ADORE project configuration.
    @param[in] runner Bounded injectable command runner.
    @return Redacted model, context, readiness and reason.
    @exception IsolationError The runtime or cleanup fails.
    """
    result: dict[str, str | bool] = {
        "context": ("executor-local" if config.execution.backend == "local"
                    else "executor-container"),
        "ready": False,
        "model": "", "reason": "not-configured",
    }
    if config.executor.default != "opencode":
        result["reason"] = "unsupported-executor"
        return result
    settings = (config.local.environment if config.execution.backend == "local"
                else config.container.runtime_env)
    url = settings.get("OPENAI_BASE_URL", "")
    model = config.executor.commands["opencode"].model
    if not url:
        return result
    parsed = urlsplit(url)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        result["reason"] = "invalid-endpoint"
        return result
    result["model"] = model
    auth_env = ""
    try:
        inline = json.loads(settings.get(
            "OPENCODE_CONFIG_CONTENT", "{}"))
        provider, separator, model_id = model.partition("/")
        entry = inline["provider"][provider]
        options = entry["options"]
        if (not separator or entry["npm"] != "@ai-sdk/openai-compatible"
                or model_id not in entry["models"]
                or options["baseURL"] != url
                or type(options.get("timeout", 300000)) is not int
                or not 1000 <= options.get("timeout", 300000) <= 600000):
            result["reason"] = "invalid-provider-config"
            return result
        auth_ref = options.get("apiKey", "")
        if auth_ref:
            match = re.fullmatch(r"\{env:([A-Z][A-Z0-9_]{0,63})\}", auth_ref)
            if match is None or match[1] not in config.executor.env_keys:
                result["reason"] = "invalid-credential-reference"
                return result
            auth_env = match[1]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        result["reason"] = "invalid-provider-config"
        return result
    if config.execution.backend == "local":
        from adore.local_execution import local_probe

        with local_probe(config) as (_, target, _, _):
            target.env.update(ADORE_PROBE_URL=url, ADORE_PROBE_MODEL=model.partition("/")[2],
                              ADORE_PROBE_AUTH_ENV=auth_env)
            checked = target([config.workflow.aegis_python, "-c", _PROBE], timeout=8)
            reason = checked.stdout.strip().splitlines()[-1:] or ["probe-failed"]
            result["reason"] = reason[0] if reason[0] in {
                "ready", "credential-missing", "tool-stream-incompatible",
                "redirect-rejected", "http-error", "endpoint-unreachable-or-incompatible",
            } or re.fullmatch(r"http-[45]\d\d", reason[0]) else "probe-failed"
            result["ready"] = checked.ok and result["reason"] == "ready"
        return result
    runtime = ContainerManager(
        config.container.runtime, config.container.image,
        config.container.uv_cache_volume, config.container.npm_cache_volume,
        runner, run_args=config.container.run_args, pull_never=True,
        egress=config.container.egress,
        selinux_relabel=config.container.selinux_relabel,
    )
    images = [config.container.image]
    if config.container.egress.mode == "allowlist-proxy":
        images.append(config.container.egress.proxy_image)
    for image in images:
        inspected = runner([*runtime.runtime_argv, "image", "inspect", image],
                           timeout=8)
        if not inspected.ok:
            result["reason"] = "image-missing"
            return result
    name = f"adore-probe-{uuid4().hex[:16]}"
    with tempfile.TemporaryDirectory(prefix="adore-model-probe-") as directory:
        root = Path(directory)
        for child in ("repo", "work", "io"):
            (root / child).mkdir()
        probe_env = dict(config.container.runtime_env)
        if "SSL_CERT_FILE" not in probe_env and probe_env.get("NODE_EXTRA_CA_CERTS"):
            probe_env["SSL_CERT_FILE"] = probe_env["NODE_EXTRA_CA_CERTS"]
        try:
            runtime.ensure_volumes()
            runtime.provision(name, root / "repo", root / "work", root / "io",
                              probe_env)
            env = {**probe_env, "ADORE_PROBE_URL": url,
                   "ADORE_PROBE_MODEL": model.partition("/")[2],
                   "ADORE_PROBE_AUTH_ENV": auth_env}
            if auth_env and os.environ.get(auth_env):
                env[auth_env] = os.environ[auth_env]
            checked = runtime.exec(name, ["python", "-c", _PROBE],
                                   timeout=8, env=env)
            reason = checked.stdout.strip().splitlines()[-1:] or ["probe-failed"]
            result["reason"] = reason[0] if reason[0] in {
                "ready", "credential-missing", "tool-stream-incompatible",
                "redirect-rejected", "http-error", "endpoint-unreachable-or-incompatible",
            } or re.fullmatch(r"http-[45]\d\d", reason[0]) else "probe-failed"
            result["ready"] = checked.ok and result["reason"] == "ready"
        finally:
            runtime.remove(name)
    return result


# END OF FILE
