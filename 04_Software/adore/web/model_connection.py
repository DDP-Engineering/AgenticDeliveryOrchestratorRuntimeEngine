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
@brief   Explicit bounded model tests through configured executor CLIs.
@details Temporary empty workspaces use project egress and executor credentials.
         A completed nonce response proves connectivity; native OpenCode, Pi and Codex
         must also complete one shell call. Neither proves complete-job readiness.
"""

# IMPORTS
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from time import monotonic
from uuid import uuid4

from adore.branding import CONTAINER_CODEX_HOME, CONTAINER_IO_MOUNT, CONTAINER_OPENCODE_AUTH_DIR
from adore.isolation import ContainerManager, IsolationError
from adore.opencode_catalogue import catalogue_path, refresh, stage
from adore.preparation import PreparationError, effective_probe_config
from adore.util import load_env_file

# CONSTANTS
KINDS = {"opencode", "pi", "codex", "qwen"}
# Installed agents whose local test must also prove one completed shell tool call.
TOOL_KINDS = {"opencode", "pi", "codex"}
LOCAL_TIMEOUT_SECONDS = 90
LOCAL_OUTPUT_BYTES = 1048576
REASONS = {
    "tool-call-failed",
    "ready",
    "timeout",
    "image-missing",
    "cli-missing",
    "credential-invalid",
    "model-unavailable",
    "connection-failed",
    "invalid-response",
    "runtime-error",
}
# This script returns a closed result rather than transmitting raw provider output.
_RUNNER = r"""
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
import json, os, shutil, subprocess, sys, tempfile, time
kind, model, nonce = sys.argv[1:]
prompt = "Connection test. Do not call tools or read files. Reply exactly: " + nonce
commands = {
 "opencode": ["opencode", "run", "--format", "json", "--model", model, prompt],
 "pi": ["pi", "-p", "--mode", "json", "--no-session", "--no-tools",
        "--no-extensions", "--no-skills", "--no-prompt-templates", "--model", model, prompt],
 "codex": ["codex", "exec", "--json", "--ephemeral", "--skip-git-repo-check",
           "--ignore-user-config", "--disable", "plugins", "--sandbox", "read-only",
           "--model", model, prompt],
 "qwen": ["qwen", "--output-format", "json", "--core-tools", "ADORE_NO_TOOLS",
          "--approval-mode", "plan", "--model", model, "-p", prompt],
}
def unique(pairs):
    value = {}
    for k,v in pairs:
        if k in value: raise ValueError()
        value[k] = v
    return value
def emit(reason):
    print(json.dumps({"ready": reason == "ready", "reason": reason}))
if not shutil.which(kind):
    emit("cli-missing"); sys.exit(0)
if kind == "opencode":
    try:
        config = json.loads(os.environ.get("OPENCODE_CONFIG_CONTENT", "{}"),
                            object_pairs_hook=unique)
        config["permission"] = {"*":"deny"}
        config["plugin"] = []
        os.environ["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
    except Exception:
        emit("invalid-response"); sys.exit(0)
os.environ["QWEN_CODE_UNATTENDED_RETRY"] = "0"
reason = "invalid-response"
try:
 with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
    process = subprocess.Popen(commands[kind], stdin=subprocess.DEVNULL, stdout=out, stderr=err)
    end = time.monotonic() + 45
    while process.poll() is None:
        if time.monotonic() >= end or out.tell() + err.tell() > 1048576:
            process.kill(); process.wait()
            emit("timeout" if time.monotonic() >= end else "invalid-response")
            sys.exit(0)
        time.sleep(.05)
    if out.tell() + err.tell() > 1048576:
        emit("invalid-response"); sys.exit(0)
    out.seek(0); err.seek(0)
    raw = out.read().decode("utf-8", errors="strict")
    failure = (raw + err.read().decode("utf-8", errors="replace")).lower()
    if process.returncode:
        if any(x in failure for x in ("401", "403", "unauthorized", "authentication", "api key")):
            reason = "credential-invalid"
        elif "model not found" in failure:
            reason = "model-unavailable"
        else:
            reason = "connection-failed"
    else:
        if kind == "qwen":
            parsed = json.loads(raw, object_pairs_hook=unique)
            events = parsed if isinstance(parsed, list) else [parsed]
        else:
            events = [json.loads(line, object_pairs_hook=unique)
                      for line in raw.splitlines() if line.strip()]
        found, complete, bad = False, False, False
        for event in events:
            if not isinstance(event, dict): raise ValueError()
            typ = event.get("type", "")
            if typ in ("error", "turn.failed", "tool_execution_start", "tool_use"):
                bad = True
            if kind == "opencode":
                part = event.get("part", {})
                if typ == "text" and part.get("text", "").strip() == nonce: found = True
                if typ == "step_finish" and part.get("reason") == "stop": complete = True
                if typ == "tool_use": bad = True
            elif kind == "pi" and typ == "message_end":
                msg = event.get("message", {})
                content = msg.get("content", [])
                if msg.get("role") == "assistant":
                    bad |= any(p.get("type") == "toolCall" for p in content)
                    answer = "".join(p.get("text", "") for p in content
                                     if p.get("type") == "text").strip() == nonce
                    found |= answer
                    complete |= msg.get("stopReason") == "stop" and answer
            elif kind == "codex":
                item = event.get("item", {})
                if typ == "item.completed" and item.get("type") == "agent_message":
                    found |= item.get("text", "").strip() == nonce
                if typ == "turn.completed": complete = True
                if item.get("type") in ("command_execution", "mcp_tool_call",
                                        "file_change", "web_search"):
                    bad = True
            elif kind == "qwen" and typ == "result":
                found |= event.get("result", "").strip() == nonce
                complete |= (event.get("subtype") == "success" and event.get("is_error") is False
                             and event.get("result", "").strip() == nonce)
        reason = "ready" if found and complete and not bad else "invalid-response"
except Exception:
    reason = "invalid-response"
emit(reason)
"""


# PUBLIC API
def _unique_result(pairs):
    """@brief Reject duplicate fields in the external diagnostic envelope."""
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate diagnostic field")
        value[key] = item
    return value


def _native_response(kind: str, output: str, nonce: str) -> bool:
    """@brief Require exact nonce, completion and no tool events from native CLI JSON.
    @param[in] kind Configured executor parser.
    @param[in] output Bounded, redacted event stream.
    @param[in] nonce Unique expected response.
    @return True only for a complete, unambiguous successful answer.
    """
    from adore.util import strict_json_loads

    try:
        parsed = strict_json_loads(output) if kind == "qwen" else None
        events = ((parsed if isinstance(parsed, list) else [parsed]) if kind == "qwen"
                  else [strict_json_loads(line) for line in output.splitlines() if line.strip()])
        found = complete = False
        for event in events:
            if not isinstance(event, dict):
                return False
            typ = event.get("type", "")
            if (not isinstance(typ, str) or typ.startswith("tool")
                    or "tool_calls" in event or "toolCalls" in event):
                return False
            if typ in {"error", "turn.failed", "tool_execution_start", "tool_use"}:
                return False
            if kind == "opencode":
                part = event.get("part", {})
                if not isinstance(part, dict):
                    return False
                if part.get("type") == "tool" or (
                        typ == "step_finish" and part.get("reason") != "stop"):
                    return False
                answer = typ == "text" and part.get("text", "").strip() == nonce
                if typ == "text" and not answer:
                    return False
                found |= answer
                stamp = part.get("time", {})
                if not isinstance(stamp, dict):
                    return False
                if "end" in stamp:
                    end, start = stamp["end"], stamp.get("start", 0)
                    if (type(end) not in {int, float} or type(start) not in {int, float}
                            or not math.isfinite(end) or not math.isfinite(start)
                            or not 0 <= start <= end or end <= 0):
                        return False
                    # Some OpenCode versions omit step_finish on shutdown.
                    # A completed exact nonce text part plus clean process exit
                    # proves this short access challenge, never a full job.
                    complete |= answer
                complete |= typ == "step_finish" and part.get("reason") == "stop"
            elif kind == "pi" and typ == "message_end":
                msg = event.get("message", {})
                content = msg.get("content", [])
                if any(p.get("type") == "toolCall" for p in content):
                    return False
                answer = (msg.get("role") == "assistant" and
                          "".join(p.get("text", "") for p in content
                                  if p.get("type") == "text").strip() == nonce)
                found |= answer
                complete |= answer and msg.get("stopReason") == "stop"
            elif kind == "codex":
                item = event.get("item", {})
                if item.get("type") in {
                    "command_execution", "mcp_tool_call", "file_change", "web_search"}:
                    return False
                found |= (typ == "item.completed" and item.get("type") == "agent_message"
                          and item.get("text", "").strip() == nonce)
                complete |= typ == "turn.completed"
            elif kind == "qwen" and typ == "result":
                found |= event.get("result", "").strip() == nonce
                complete |= event.get("subtype") == "success" and event.get("is_error") is False
        return found and complete
    except (ValueError, TypeError, AttributeError, OverflowError):
        return False


def _native_model_reason(kind: str, gate, nonce: str, tool_nonce: str = "") -> str:
    """@brief Classify bounded provider failures before interpreting nonce completion.
    @param[in] kind Selected native executor.
    @param[in] gate Captured, redacted native result.
    @param[in] nonce Expected exact challenge answer.
    @param[in] tool_nonce Required shell output token for tool-capable native probes.
    @return Closed cause only; provider messages never enter persisted evidence.
    """
    from adore.util import strict_json_loads

    if gate.timed_out:
        return "timeout"
    if gate.exit_code == 127:
        return "cli-missing"
    if gate.exit_code:
        # Match recognizable failures even when the CLI did not emit JSON.
        if re.search(r"\b(?:HTTP[/\d.]*\s+(?:401|403)|unauthorized|authentication failed)\b",
                     gate.stderr[:65536], re.I):
            return "credential-invalid"
        if re.search(r"\bmodel (?:not found|unavailable)\b", gate.stderr[:65536], re.I):
            return "model-unavailable"
    try:
        if len(gate.output.encode("utf-8")) > 1048576:
            return "invalid-response"
        if kind == "opencode":
            events = [strict_json_loads(line) for line in gate.output.splitlines() if line.strip()]
            for event in events:
                if not isinstance(event, dict):
                    return "invalid-response"
                if event.get("type") == "error":
                    error = event.get("error")
                    if not isinstance(error, dict):
                        return "invalid-response"
                    name, data = error.get("name"), error.get("data", {})
                    if not isinstance(name, str) or not isinstance(data, dict):
                        return "invalid-response"
                    if name in {"ProviderModelNotFoundError", "ModelNotFoundError"}:
                        return "model-unavailable"
                    status = data.get("statusCode")
                    if name in {"ProviderAuthError", "AuthenticationError"} or (
                            type(status) is int and status in {401, 403}):
                        return "credential-invalid"
                    return "connection-failed"
    except (ValueError, TypeError, UnicodeError):
        return "connection-failed" if gate.exit_code else "invalid-response"
    if gate.exit_code:
        return "connection-failed"
    if tool_nonce and kind in TOOL_KINDS:
        return _native_tool_response(kind, gate.output, tool_nonce, nonce)
    return "ready" if _native_response(kind, gate.output, nonce) else "invalid-response"
def _shell_call_succeeded(kind: str, event: dict, tool_nonce: str) -> bool:
    """@brief Recognize one completed, successful shell call that printed the tool nonce.
    @param[in] kind Configured executor parser (opencode, pi or codex).
    @param[in] event One decoded JSON event.
    @param[in] tool_nonce Token the shell command had to print.
    @return True only for the executor's successful shell-call event carrying the nonce.
    """
    typ = event.get("type")
    if kind == "opencode":
        part = event.get("part", {})
        state = part.get("state", {}) if isinstance(part, dict) else {}
        return (typ == "tool_use" and part.get("tool") == "bash"
                and state.get("status") == "completed"
                and tool_nonce in str(state.get("output", "")))
    if kind == "pi":
        result = event.get("result")
        content = result.get("content", []) if isinstance(result, dict) else []
        return (typ == "tool_execution_end" and event.get("toolName") == "bash"
                and event.get("isError") is False
                and any(tool_nonce in str(p.get("text", "")) for p in content
                        if isinstance(p, dict)))
    item = event.get("item", {})
    return (typ == "item.completed" and item.get("type") == "command_execution"
            and item.get("status") == "completed" and item.get("exit_code") == 0
            and tool_nonce in str(item.get("aggregated_output", "")))


def _native_tool_response(kind: str, output: str, tool_nonce: str, nonce: str) -> str:
    """@brief Decide a local tool challenge: shell call first, then the exact final reply.
    @param[in] kind Configured executor parser (opencode, pi or codex).
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
        if not any(_shell_call_succeeded(kind, event, tool_nonce) for event in events):
            return "tool-call-failed"
        if kind == "opencode":
            boundary = max((index for index, event in enumerate(events)
                            if event.get("type") == "tool_use" or (
                                event.get("type") == "step_finish"
                                and isinstance(event.get("part"), dict)
                                and event["part"].get("reason") == "tool-calls")), default=-1)
            final_events = events[boundary + 1:]
            return ("ready" if _native_response(
                kind, "\n".join(json.dumps(event) for event in final_events), nonce
            ) else "invalid-response")
        elif kind == "pi":
            final = [e["message"] for e in events if e.get("type") == "message_end"
                     and isinstance(e.get("message"), dict)
                     and e["message"].get("role") == "assistant"]
            last = final[-1] if final else {}
            text = "".join(str(p.get("text", "")) for p in last.get("content", [])
                           if isinstance(p, dict) and p.get("type") == "text")
            replied, complete = text.strip() == nonce, last.get("stopReason") == "stop"
        else:
            messages = [e["item"] for e in events if e.get("type") == "item.completed"
                        and isinstance(e.get("item"), dict)
                        and e["item"].get("type") == "agent_message"]
            replied = bool(messages) and str(messages[-1].get("text", "")).strip() == nonce
            complete = any(e.get("type") == "turn.completed" for e in events)
        return "ready" if replied and complete else "invalid-response"
    except (ValueError, TypeError, AttributeError, KeyError):
        return "invalid-response"


def probe_model_connection(config, runner, env_file: Path) -> dict:
    """@brief Run one bounded challenge through the selected container/native target.
    @param[in] config Validated project snapshot.
    @param[in] runner Injectable external runtime boundary.
    @param[in] env_file Selected profile executor secret file.
    @return Closed redacted executor/model/readiness/reason evidence.
    @exception IsolationError Cleanup cannot be confirmed.
    """
    kind = config.executor.default
    model = config.executor.commands[kind].model
    result = {"executor": kind, "model": model, "ready": False, "reason": "runtime-error"}
    if kind not in KINDS or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", model):
        return result
    if config.execution.backend == "local":
        from adore.executor.launcher import build_executor
        from adore.local_execution import local_probe, local_probe_failure

        nonce = "ADORE_OK_" + uuid4().hex
        tool_nonce = "ADORE_TOOL_" + uuid4().hex
        prompt = ("Connection test. Run this shell command exactly once: echo " + tool_nonce
                  + ". Then reply with exactly: " + nonce if kind in TOOL_KINDS
                  else "Connection test. Do not call tools or read files. Reply exactly: "
                  + nonce)
        try:
            with local_probe(config, env_file) as (_, target, work, exchange):
                # Pi repeats the conversation in its events; keep what the container keeps.
                target.output_limit = LOCAL_OUTPUT_BYTES
                executor = build_executor(kind, config.executor.commands[kind].command, model)
                gate = executor.run_gate(target, work, exchange, prompt,
                                         timeout=LOCAL_TIMEOUT_SECONDS)
                reason = _native_model_reason(kind, gate, nonce, tool_nonce)
                result.update(ready=reason == "ready", reason=reason)
        except TimeoutError:
            result["reason"] = "timeout"
        except (OSError, ValueError, TypeError, IsolationError) as exc:
            cause = local_probe_failure(exc)
            result["reason"] = {"executable-missing": "cli-missing",
                                "credential-invalid": "credential-invalid"}.get(
                                    cause, "runtime-error")
        return result
    deadline = monotonic() + 90

    def bounded(argv, *, cwd=None, timeout=None, env=None):
        """@brief Bound all setup/inference operations while reserving cleanup time."""
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError()
        value = runner(argv, cwd=cwd, timeout=min(timeout or 8, remaining), env=env)
        if value.timed_out:
            raise TimeoutError()
        return value

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
        egress=config.container.egress,
        selinux_relabel=config.container.selinux_relabel,
    )
    name = "adore-ai-test-" + uuid4().hex[:16]
    with tempfile.TemporaryDirectory(prefix="adore-ai-test-") as directory:
        root = Path(directory)
        for child in ("repo", "work", "io"):
            (root / child).mkdir()
        (root / "io" / "probe.py").write_text(_RUNNER, encoding="utf-8")
        env = dict(config.container.runtime_env)
        saved = {**load_env_file(env_file), **os.environ}
        env.update({key: saved[key] for key in config.executor.env_keys if saved.get(key)})
        if kind == "codex":
            env["CODEX_HOME"] = CONTAINER_CODEX_HOME
        auth = {
            "opencode": (".local/share/opencode/auth.json", CONTAINER_OPENCODE_AUTH_DIR),
            "codex": (".codex/auth.json", CONTAINER_CODEX_HOME),
        }.get(kind)
        provisioned = False
        try:
            images = [config.container.image]
            if config.container.egress.mode == "allowlist-proxy":
                images.append(config.container.egress.proxy_image)
            for image in images:
                if not bounded([*runtime.runtime_argv, "image", "inspect", image]).ok:
                    result["reason"] = "image-missing"
                    return result
            runtime.ensure_volumes()
            provisioned = True
            runtime.provision(name, root / "repo", root / "work", root / "io", env)
            if auth and config.executor.stage_host_auth and (Path.home() / auth[0]).is_file():
                staged = root / "io" / "auth.json"
                shutil.copyfile(Path.home() / auth[0], staged)
                staged.chmod(0o644)  # enclosing temporary directory is private
                if not runtime.exec(name, ["mkdir", "-p", auth[1]], env=env).ok:
                    raise IsolationError("auth staging failed")
                if not runtime.exec(
                    name, ["cp", "/adore/io/auth.json", auth[1] + "/auth.json"], env=env
                ).ok:
                    raise IsolationError("auth staging failed")
                staged.unlink()
            if kind == "opencode":
                # Newer models need a current catalogue: reuse the saved one, then refresh it
                # and save it for jobs. Best effort; the test never fails because of it.
                saved = catalogue_path(config.state.store_root)
                in_container = lambda argv, timeout=None: runtime.exec(  # noqa: E731
                    name, argv, env=env, timeout=timeout or 8)
                stage(in_container, saved, root / "io", CONTAINER_IO_MOUNT)
                refresh(in_container, saved, root / "io", CONTAINER_IO_MOUNT)
            checked = runtime.exec(
                name,
                ["python", "/adore/io/probe.py", kind, model, "ADORE_OK_" + uuid4().hex],
                timeout=50,
                env=env,
            )
            try:
                value = json.loads(checked.stdout, object_pairs_hook=_unique_result)
            except (ValueError, TypeError):
                result["reason"] = "invalid-response"
                return result
            if (
                not checked.ok
                or not isinstance(value, dict)
                or set(value) != {"ready", "reason"}
                or type(value["ready"]) is not bool
                or value["reason"] not in REASONS
                or value["ready"] != (value["reason"] == "ready")
            ):
                result["reason"] = "invalid-response"
            else:
                result.update(value)
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
