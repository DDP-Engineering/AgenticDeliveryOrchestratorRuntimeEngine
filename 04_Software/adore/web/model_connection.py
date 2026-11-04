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
@file    model_connection.py
@brief   Explicit bounded model tests through Pi, ADORE's only coding agent.
@details A container test runs one `pi --mode rpc` process in a temporary empty
         container under the project's egress and credentials: Pi must run
         one shell command that prints a tool nonce, then reply with exactly
         a reply nonce. Pi's own failure class becomes a closed reason
         (invalid key, unreachable provider or endpoint, unknown model, rate
         limit). A provider that needs a credential and has none is reported
         before any container starts. A native (installed) Pi runs the same
         challenge over RPC inside its owned process scope. Neither proves complete-job
         readiness.
"""

# IMPORTS
import json
import os
from pathlib import Path
import subprocess
import tempfile
from time import monotonic
from uuid import uuid4

from adore import chatgpt
from adore.branding import CONTAINER_PI_AGENT_DIR, EXECUTOR_NAME
from adore.config import egress_policy
from adore.isolation import ContainerManager, IsolationError
from adore.pi_providers import (
    CHATGPT,
    ENDPOINT_KEY_VARIABLE,
    MODEL_ID_RE,
    credential_required,
    credential_variable,
    models_json,
    pi_provider,
    secret_names,
)
from adore.preparation import PreparationError, effective_probe_config
from adore.util import load_env_file

# CONSTANTS
LOCAL_TIMEOUT_SECONDS = 90
LOCAL_OUTPUT_BYTES = 1024 * 1024
#: Wall-clock bound of the Pi run inside the temporary container.
CONTAINER_TIMEOUT_SECONDS = 60
#: Wall-clock bound of one whole container probe (setup, run and cleanup).
PROBE_SECONDS = 90
#: ChatGPT token failure -> reason.
_TOKEN_REASONS = {
    "not-signed-in": "sign-in-required",
    "sign-in-again": "sign-in-required",
    "not-eligible": "subscription-refused",
    "unavailable": "connection-failed",
}
REASONS = {
    "tool-call-failed",
    "ready",
    "timeout",
    "image-missing",
    "cli-missing",
    "credential-missing",
    "credential-invalid",
    "model-unavailable",
    "connection-failed",
    "rate-limited",
    "provider-error",
    "invalid-response",
    "runtime-error",
    "sign-in-required",
    "subscription-refused",
    "usage-limit",
}
#: Pi failure class (`pi_rpc`) -> reason.
_FAILURE_REASONS = {
    "subscription": "subscription-refused",
    "credential": "credential-invalid",
    "sign-in": "sign-in-required",
    "model": "model-unavailable",
    "network": "connection-failed",
    "rate-limit": "rate-limited",
    "provider": "provider-error",
}
_MODELS_FILE = "pi-models.json"


# HELPER FUNCTIONS


def _shell_call_succeeded(event: dict, tool_nonce: str) -> bool:
    """@brief Recognize one completed, successful Pi shell call that printed the tool nonce.
    @param[in] event One decoded JSON event.
    @param[in] tool_nonce Token the shell command had to print.
    @return True only for a successful bash tool_execution_end carrying the nonce.
    """
    result = event.get("result")
    content = result.get("content", []) if isinstance(result, dict) else []
    return (event.get("type") == "tool_execution_end"
            and event.get("toolName") in {"bash", "powershell"}
            and event.get("isError") is False
            and any(tool_nonce in str(p.get("text", "")) for p in content
                    if isinstance(p, dict)))


def _native_tool_response(output: str, tool_nonce: str, nonce: str) -> str:
    """@brief Decide a local tool challenge: shell call first, then the exact final reply.
    @param[in] output Bounded, redacted JSON-lines event stream.
    @param[in] tool_nonce Token the shell command had to print.
    @param[in] nonce Unique expected final reply.
    @return ready, tool-call-failed or invalid-response.
    """
    from adore.util import strict_json_loads

    try:
        events = [strict_json_loads(line) for line in output.splitlines() if line.strip()]
        if not all(isinstance(event, dict) for event in events):
            return "invalid-response"
        if not any(_shell_call_succeeded(event, tool_nonce) for event in events):
            return "tool-call-failed"
        final = [e["message"] for e in events if e.get("type") == "message_end"
                 and isinstance(e.get("message"), dict)
                 and e["message"].get("role") == "assistant"]
        last = final[-1] if final else {}
        text = "".join(str(p.get("text", "")) for p in last.get("content", [])
                       if isinstance(p, dict) and p.get("type") == "text")
        replied, complete = text.strip() == nonce, last.get("stopReason") == "stop"
        return "ready" if replied and complete else "invalid-response"
    except (ValueError, TypeError, AttributeError, KeyError):
        return "invalid-response"


def _challenge() -> tuple[str, str, str]:
    """@brief A fresh shell-then-reply challenge: (prompt, tool nonce, reply nonce)."""
    nonce = "ADORE_OK_" + uuid4().hex
    tool_nonce = "ADORE_TOOL_" + uuid4().hex
    prompt = ("Connection test. Run this shell command exactly once: echo " + tool_nonce
              + ". Then reply with exactly: " + nonce)
    return prompt, tool_nonce, nonce


def _rpc_reason(result, tool_nonce: str, nonce: str, *, subscription: bool = False) -> str:
    """
    @brief      Turn one Pi RPC outcome into a closed reason.
    @param[in]  result `PiRpcResult` of the challenge run.
    @param[in]  tool_nonce Token the shell command had to print.
    @param[in]  nonce Expected final reply.
    @param[in]  subscription A ChatGPT subscription run: a rate limit is its usage limit.
    @return     A member of REASONS.
    """
    if result.outcome == "completed":
        return _native_tool_response(result.output, tool_nonce, nonce)
    if result.outcome == "failed":
        if subscription and result.failure == "rate-limit":
            return "usage-limit"
        return _FAILURE_REASONS.get(result.failure, "provider-error")
    if result.outcome == "timed-out":
        return "timeout"
    if result.exit_code in (126, 127):
        return "cli-missing"
    return "invalid-response"


# PUBLIC API


def probe_model_connection(config, runner, env_file: Path, *,
                           popen=subprocess.Popen, chatgpt_dir: Path | None = None) -> dict:
    """@brief Run one bounded challenge through the selected container/native target.
    @details A ChatGPT project first gets an access token from the server's
             sign-in (a helper container mounting only that directory) and
             passes it to Pi only in the launch environment.
    @param[in] config Validated project snapshot.
    @param[in] runner Injectable external runtime boundary.
    @param[in] env_file Selected profile executor secret file.
    @param[in] popen Process factory of the streaming `exec -i` (tests inject a fake Pi).
    @param[in] chatgpt_dir The server's ChatGPT credential directory (default: ADORE home).
    @return Closed redacted executor/model/readiness/reason evidence.
    @exception IsolationError Cleanup cannot be confirmed.
    """
    executor = config.executor
    model = executor.model
    result = {"executor": EXECUTOR_NAME, "model": model, "ready": False,
              "reason": "runtime-error"}
    if not isinstance(model, str) or not MODEL_ID_RE.fullmatch(model):
        return result
    deadline = monotonic() + PROBE_SECONDS

    def bounded(argv, *, cwd=None, timeout=None, env=None):
        """@brief Bound all setup/inference operations while reserving cleanup time."""
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError()
        value = runner(argv, cwd=cwd, timeout=min(timeout or 8, remaining), env=env)
        if value.timed_out:
            raise TimeoutError()
        return value

    if config.execution.backend == "local":
        from contextlib import ExitStack

        from adore.executor import pi_rpc
        from adore.local_execution import local_probe, local_probe_failure

        prompt, tool_nonce, nonce = _challenge()
        try:
            with local_probe(config, env_file) as (backend, target, _, _), ExitStack() as stack:
                if executor.provider == CHATGPT:
                    try:
                        token = chatgpt.bearer_token(
                            chatgpt.helper_for(config, None, runner=bounded),
                            chatgpt_dir or chatgpt.credential_dir(),
                            LOCAL_TIMEOUT_SECONDS + chatgpt.TOKEN_MARGIN_SECONDS,
                            timeout=max(1.0, deadline - monotonic() - 10))
                    except chatgpt.ChatGptError as exc:
                        reason = _TOKEN_REASONS.get(exc.code, "runtime-error")
                        return {**result, "reason": reason}
                    target = backend.bind(
                        target.name, {**target.env, chatgpt.TOKEN_VARIABLE: token},
                        target.resource, secrets=(token,))
                if not target.auth_available():
                    return {**result, "reason": "credential-missing"}
                backend.verify_required_tools("probe", [], env=target.env)
                argv = target.pi_argv(model, pi_provider(executor.provider))
                models = models_json(executor, bool(target.env.get(ENDPOINT_KEY_VARIABLE)))
                placements = [("", "models.json", models, "")] if models else []

                def spawn_native(command, _env):
                    """@brief Keep the owned native scope open for the RPC exchange."""
                    return stack.enter_context(target.pi_session(command, placements))

                if deadline - monotonic() <= 10:
                    return {**result, "reason": "timeout"}
                launched = pi_rpc.run_pi_rpc(
                    spawn_native, argv, {}, prompt,
                    timeout=max(1.0, min(LOCAL_TIMEOUT_SECONDS,
                                        deadline - monotonic() - 10)), redact=target.redact,
                    stdout_tail_bytes=LOCAL_OUTPUT_BYTES,
                )
                reason = _rpc_reason(launched, tool_nonce, nonce,
                                     subscription=executor.provider == CHATGPT)
                result.update(ready=reason == "ready", reason=reason)
        except TimeoutError:
            result["reason"] = "timeout"
        except (OSError, ValueError, TypeError, IsolationError) as exc:
            cause = local_probe_failure(exc)
            result["reason"] = {
                "node-missing": "cli-missing", "node-incompatible": "cli-missing",
                "node-invalid": "cli-missing", "pi-missing": "cli-missing",
                "version-invalid": "cli-missing", "timeout": "timeout",
            }.get(cause, "runtime-error")
        return result
    saved = {**load_env_file(env_file), **os.environ}
    variable = credential_variable(executor.provider)
    subscription = executor.provider == CHATGPT
    if (not subscription and credential_required(executor.provider)
            and not (variable and saved.get(variable))):
        result["reason"] = "credential-missing"
        return result
    try:
        config = effective_probe_config(config, runner=bounded)
    except (PreparationError, TimeoutError, OSError):
        return result
    runtime = ContainerManager(
        config.container.runtime,
        config.container.image,
        config.container.uv_cache_volume,
        config.container.npm_cache_volume,
        bounded,
        run_args=config.container.run_args,
        pull_never=True,
        egress=egress_policy(config),
        selinux_relabel=config.container.selinux_relabel,
    )
    launch_env: dict[str, str] = {}
    if subscription:
        try:
            token = chatgpt.bearer_token(
                runtime, chatgpt_dir or chatgpt.credential_dir(),
                PROBE_SECONDS + chatgpt.TOKEN_MARGIN_SECONDS,
                timeout=max(1.0, deadline - monotonic() - 10))
        except chatgpt.ChatGptError as exc:
            result["reason"] = _TOKEN_REASONS.get(exc.code, "runtime-error")
            return result
        except (TimeoutError, OSError):
            result["reason"] = "timeout"
            return result
        launch_env[chatgpt.TOKEN_VARIABLE] = token
    name = "adore-ai-test-" + uuid4().hex[:16]
    with tempfile.TemporaryDirectory(prefix="adore-ai-test-") as directory:
        root = Path(directory)
        for child in ("repo", "work", "io"):
            (root / child).mkdir()
        env = dict(config.container.runtime_env)
        # The connection test loads no web tools, so it never gets the search key.
        secrets = {key: saved[key] for key in secret_names(executor, "") if saved.get(key)}
        env.update(secrets)
        models = models_json(executor, ENDPOINT_KEY_VARIABLE in secrets)
        provisioned = False
        try:
            images = [config.container.image]
            if runtime.egress.mode == "allowlist-proxy":
                images.append(runtime.egress.proxy_image)
            for image in images:
                if not bounded([*runtime.runtime_argv, "image", "inspect", image]).ok:
                    result["reason"] = "image-missing"
                    return result
            runtime.ensure_volumes()
            provisioned = True
            runtime.provision(name, root / "repo", root / "work", root / "io", env)
            if models is not None:
                (root / "io" / _MODELS_FILE).write_bytes(
                    json.dumps(models, ensure_ascii=True).encode("utf-8"))
                if not runtime.exec(name, ["cp", f"/adore/io/{_MODELS_FILE}",
                                           f"{CONTAINER_PI_AGENT_DIR}/models.json"],
                                    timeout=10).ok:
                    return result
            from adore.executor import pi_rpc
            from adore.executor.launcher import PI_RPC_ENV, pi_rpc_argv

            prompt, tool_nonce, nonce = _challenge()
            values = [value for value in [*secrets.values(), *launch_env.values()]
                      if len(value) >= 4]

            def redact(text: str) -> str:
                for value in values:
                    text = text.replace(value, "[REDACTED]")
                return text

            remaining = max(1.0, min(CONTAINER_TIMEOUT_SECONDS, deadline - monotonic() - 10))
            launched = pi_rpc.run_pi_rpc(
                lambda argv, extra: runtime.spawn(name, argv, env={**extra, **launch_env},
                                                  popen=popen),
                pi_rpc_argv(model, pi_provider(executor.provider)), dict(PI_RPC_ENV), prompt,
                timeout=remaining, output_path=root / "io" / "output.jsonl",
                stderr_path=root / "io" / "stderr.log", redact=redact)
            reason = _rpc_reason(launched, tool_nonce, nonce, subscription=subscription)
            result.update(ready=reason == "ready", reason=reason)
        except TimeoutError:
            result["reason"] = "timeout"
        except (OSError, ValueError, TypeError, IsolationError):
            result["reason"] = "runtime-error"
        finally:
            if provisioned:
                runtime.runner = lambda argv, **kwargs: runner(argv, **{**kwargs, "timeout": 8})
                runtime.remove(name)
    return result


# END OF FILE
