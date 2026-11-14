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
@file test_model_connection.py
@brief Explicit Test AI connection contracts for Pi over RPC.
@details The container runtime is faked and Pi is the fake RPC process replaying
         recorded runs; provider output is never returned to the browser.
"""

import importlib
import json
from pathlib import Path
import subprocess
import sys

from adore import chatgpt
from adore.chatgpt import CONTAINER_SCRIPT, TOKEN_MARGIN_SECONDS
from adore.config import load_config
from adore.profiles import ProfileStore
from adore.util import CommandResult
from adore.web.model_connection import probe_model_connection
import pytest

from tests.configuration_client import TestClient


def project(tmp_path, provider="gitlab"):
    """@brief Create an offline project with real API identity/config storage."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha", store_root=str(tmp_path / "state"))
    path = profiles.config_path("alpha")
    raw = (Path(__file__).resolve().parents[1] / "config.example.toml").read_text()
    raw = raw.replace('store_root = ".adore"', f'store_root = "{(tmp_path / "state").as_posix()}"')
    raw = raw.replace('repo = "group/subgroup/project"', 'repo = "mygroup/myproject"')
    raw = raw.replace('kind = "gitlab"', f'kind = "{provider}"')
    path.write_text(raw, encoding="utf-8")
    return profiles


def test_explicit_model_test_returns_scoped_evidence(tmp_path, monkeypatch):
    """@brief Only explicit requests run the Pi model probe."""
    module = importlib.import_module("adore.web.app")
    profiles = project(tmp_path)
    calls = []

    def probe(config, runner, env_file, **_options):
        """@brief Fake one external model call without a paid provider."""
        calls.append(env_file)
        return {"ready": True, "reason": "ready", "executor": "pi",
                "model": config.executor.model}

    monkeypatch.setattr(module, "probe_model_connection", probe, raising=False)
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        result = client.post(
            "/api/v1/projects/alpha/model-connection-test", headers={"X-CSRF-Token": csrf}
        )
        assert result.status_code == 200
        assert result.json()["project_id"] == profiles.load("alpha").project_id
        assert result.json()["executor"] == "pi" and result.json()["ready"] is True
        assert len(calls) == 1


@pytest.mark.parametrize("mode", ["anonymous", "csrf", "developer", "locked", "corrupt", "stale"])
def test_model_test_rejects_trust_boundary(tmp_path, monkeypatch, mode):
    """@brief Untrusted requests/state cannot initiate or retain model evidence."""
    module = importlib.import_module("adore.web.app")
    profiles = project(tmp_path)
    calls = []

    def probe(config, runner, env_file, **_options):
        """@brief Simulate concurrent configuration drift after the request."""
        calls.append(True)
        if mode == "stale":
            path = profiles.config_path("alpha")
            path.write_text(path.read_text() + "\n# changed\n")
        return {"ready": True, "reason": "ready", "executor": "pi",
                "model": config.executor.model}

    monkeypatch.setattr(module, "probe_model_connection", probe)
    app = module.create_app(profiles.home)
    if mode == "developer":
        dev = app.state.web_store.create_user("dev", "longer-password", "developer")
        app.state.web_store.set_memberships(dev["id"], ["alpha"])
    with TestClient(app) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        if mode == "developer":
            client.cookies.clear()
            csrf = client.post(
                "/api/v1/session", json={"username": "dev", "password": "longer-password"}
            ).json()["csrf"]
        if mode == "anonymous":
            client.cookies.clear()
        if mode == "corrupt":
            profiles.config_path("alpha").write_text("corrupt [")
        if mode == "locked":
            from adore.state import StateStore

            store = StateStore(tmp_path / "state")
            store.acquire_lock()
        try:
            response = client.post(
                "/api/v1/projects/alpha/model-connection-test",
                headers={} if mode == "csrf" else {"X-CSRF-Token": csrf},
            )
            assert response.status_code in (401, 403, 409, 503)
            assert len(calls) == (1 if mode == "stale" else 0)
        finally:
            if mode == "locked":
                store.release_lock()


FAKE = Path(__file__).with_name("fake_pi_rpc.py")
FIXTURES = Path(__file__).parent / "fixtures" / "pi_rpc"
SECRET = "sk-test-private-key-0123456789"
CHATGPT_TOKEN = "eyJ-fake-chatgpt-access-token-0123"


def set_executor(profiles, provider: str, model: str, base_url: str = "") -> None:
    """@brief Replace the example [executor] provider/model; append an endpoint table."""
    path = profiles.config_path("alpha")
    raw = path.read_text(encoding="utf-8")
    raw = raw.replace('provider = "openai"\n', f'provider = "{provider}"\n', 1)
    raw = raw.replace('model = "gpt-5.5"\n', f'model = "{model}"\n', 1)
    if base_url:
        raw += f'\n[executor.endpoint]\nbase_url = "{base_url}"\n'
    path.write_text(raw, encoding="utf-8")


class Runtime:
    """@brief Fake container runtime: records commands, starts the fake Pi on `exec -i`."""

    def __init__(self, tmp_path: Path, fixture: str, *options: str,
                 image_missing: bool = False, copy_fails: bool = False,
                 cleanup_fails: bool = False, token_answer: dict | None = None) -> None:
        self.fixture = FIXTURES / f"{fixture}.jsonl"
        self.token_answer = token_answer or {"status": "ok", "token": CHATGPT_TOKEN,
                                             "expires": 4102444800000}
        self.options = list(options)
        self.image_missing, self.copy_fails = image_missing, copy_fails
        self.cleanup_fails = cleanup_fails
        self.calls: list[tuple[list[str], dict]] = []
        self.spawned: list[tuple[list[str], dict]] = []
        self.roots: list[Path] = []
        self.models: list[dict] = []
        self.record = tmp_path / "commands.log"

    def runner(self, argv, **kwargs):
        """@brief Answer the runtime CLI without a container."""
        argv = list(argv)
        self.calls.append((argv, kwargs))
        if "image" in argv and "inspect" in argv:
            return CommandResult(argv, 1 if self.image_missing else 0)
        if CONTAINER_SCRIPT in argv:
            return CommandResult(argv, 0 if self.token_answer.get("status") == "ok" else 1,
                                 stdout=json.dumps(self.token_answer) + "\n")
        if "inspect" in argv:
            removed = any("rm" in previous for previous, _ in self.calls[:-1])
            if self.cleanup_fails and removed:
                return CommandResult(argv, stdout="running")
            return CommandResult(argv, 1, stderr="No such container")
        if "run" in argv:
            # The egress proxy of an internet-off probe mounts no io dir.
            mount = next((arg for arg in argv if ":/adore/io" in arg), None)
            if mount:
                self.roots.append(Path(mount.split(":/adore/io")[0]))
        if "cp" in argv:
            self.models.append(json.loads((self.roots[0] / "pi-models.json").read_text("utf-8")))
            return CommandResult(argv, 1 if self.copy_fails else 0)
        if "rm" in argv and self.cleanup_fails:
            return CommandResult(argv, 1, stderr="permission denied")
        return CommandResult(argv)

    def popen(self, argv, **kwargs):
        """@brief Start the fake Pi in place of `<runtime> exec -i <name> node ...`."""
        self.spawned.append((list(argv), dict(kwargs.get("env") or {})))
        return subprocess.Popen(  # noqa: S603 - fixed test argv
            [sys.executable, "-I", str(FAKE), str(self.fixture), "--record", str(self.record),
             *self.options], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def probe(profiles, runtime: Runtime, **kwargs) -> dict:
    """@brief Run the probe against the fake runtime with a test-sized bound."""
    config = load_config(profiles.config_path("alpha"))
    kwargs.setdefault("chatgpt_dir", profiles.home / "chatgpt")
    return probe_model_connection(config, runtime.runner, profiles.profile_dir("alpha") / ".env",
                                  popen=runtime.popen, **kwargs)


@pytest.mark.parametrize(("fixture", "reason"), [
    ("run_connection_test_endpoint", "ready"),
    ("run_tool_calls_chatgpt", "tool-call-failed"),
    ("failed_invalid_api_key", "credential-invalid"),
    ("failed_unreachable_endpoint", "connection-failed"),
    ("failed_model_not_found_endpoint", "model-unavailable"),
    ("failed_rate_limit_retry", "rate-limited"),
])
def test_rpc_probe_reports_each_outcome_distinctly(tmp_path, monkeypatch, fixture, reason):
    """@brief One Pi RPC run in a temporary container; each recorded outcome has its reason."""
    profiles = project(tmp_path)
    (profiles.profile_dir("alpha") / ".env").write_text(f"OPENAI_API_KEY={SECRET}\n")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    runtime = Runtime(tmp_path, fixture, "--key-hint", "sk-test****6789")
    result = probe(profiles, runtime)
    assert result == {"executor": "pi", "model": "gpt-5.5", "ready": reason == "ready",
                      "reason": reason}
    argv, env = runtime.spawned[0]
    assert argv[argv.index("exec") + 1] == "-i"
    pi = argv[argv.index("node"):]
    assert pi[pi.index("--mode") + 1] == "rpc"
    assert pi[pi.index("--provider") + 1] == "openai" and pi[pi.index("--model") + 1] == "gpt-5.5"
    sent = [json.loads(line) for line in runtime.record.read_text("utf-8").splitlines()]
    assert sent[0]["type"] == "prompt" and "echo ADORE_TOOL_" in sent[0]["message"]
    run = next(kwargs for argv, kwargs in runtime.calls if "run" in argv and "infinity" in argv)
    assert run["env"]["OPENAI_API_KEY"] == SECRET
    assert all(SECRET not in " ".join(argv) for argv, _ in runtime.calls + runtime.spawned)
    assert SECRET not in json.dumps(result) and "sk-test" not in json.dumps(result)
    assert any("rm" in argv for argv, _ in runtime.calls)
    assert all(not root.exists() for root in runtime.roots)
    assert all("pull" not in argv for argv, _ in runtime.calls)


def test_connection_probe_passes_thinking_to_pi(tmp_path, monkeypatch):
    """@brief The disposable RPC probe receives the configured Pi reasoning effort."""
    profiles = project(tmp_path)
    path = profiles.config_path("alpha")
    path.write_text(path.read_text(encoding="utf-8").replace('model = "gpt-5.5"',
                    'model = "gpt-5.5"\nthinking = "medium"'), encoding="utf-8")
    (profiles.profile_dir("alpha") / ".env").write_text(f"OPENAI_API_KEY={SECRET}\n")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    runtime = Runtime(tmp_path, "run_connection_test_endpoint")
    probe(profiles, runtime)
    argv = runtime.spawned[0][0]
    assert argv[argv.index("--thinking") + 1] == "medium"


def set_internet(profiles, internet: bool, search: str = "") -> None:
    """@brief Set [executor] internet (and [executor.web] search) in the project config."""
    path = profiles.config_path("alpha")
    raw = path.read_text(encoding="utf-8")
    raw = raw.replace('model = "gpt-5.5"\n',
                      f'model = "gpt-5.5"\ninternet = {str(internet).lower()}\n', 1)
    if search:
        raw += f'\n[executor.web]\nsearch = "{search}"\n'
    path.write_text(raw, encoding="utf-8")


def test_probe_runs_under_the_internet_switch(tmp_path, monkeypatch):
    """@brief Off: the probe container sits behind the provider-only proxy; On: open network."""
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    profiles = project(tmp_path)
    runtime = Runtime(tmp_path, "run_connection_test_endpoint")
    assert probe(profiles, runtime)["reason"] == "ready"
    run = next(argv for argv, _ in runtime.calls if "run" in argv and "infinity" in argv)
    assert run[run.index("--network") + 1].startswith("adore-egress-")
    assert any(part.startswith("HTTPS_PROXY=http://adore-egress-proxy:") for part in run)
    assert any("run" in argv and "adore-egress-proxy:1.0.0" in argv for argv, _ in runtime.calls)
    assert ["docker", "image", "inspect", "adore-egress-proxy:1.0.0"] in [
        argv for argv, _ in runtime.calls]
    pi = runtime.spawned[0][0]
    assert "--append-system-prompt" not in pi and "pi-web-access" not in " ".join(pi)

    opened = project(tmp_path / "on")
    set_internet(opened, True, "brave")
    monkeypatch.setenv("BRAVE_API_KEY", "brave-test-key")
    runtime = Runtime(tmp_path / "on", "run_connection_test_endpoint")
    assert probe(opened, runtime)["reason"] == "ready"
    run = next(argv for argv, _ in runtime.calls if "run" in argv and "infinity" in argv)
    assert "--network" not in run
    assert not any(part.upper().startswith(("HTTP_PROXY=", "HTTPS_PROXY=")) for part in run)
    # The connection test loads no web tools and never receives the search key.
    assert "BRAVE_API_KEY" not in run
    assert all("BRAVE_API_KEY" not in env for _, env in runtime.spawned)
    assert not any("adore-egress-proxy:1.0.0" in argv for argv, _ in runtime.calls)


def test_rpc_probe_wrong_reply_is_an_invalid_response(tmp_path, monkeypatch):
    """@brief A completed run whose last reply is not the reply nonce is not ready."""
    profiles = project(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    fixture = (FIXTURES / "run_connection_test_endpoint.jsonl").read_text("utf-8")
    changed = tmp_path / "wrong_reply.jsonl"
    changed.write_text(fixture.replace('"text": "<NONCE>"', '"text": "something else"'),
                       encoding="utf-8")
    runtime = Runtime(tmp_path, "run_connection_test_endpoint")
    runtime.fixture = changed
    assert probe(profiles, runtime)["reason"] == "invalid-response"


def test_rpc_probe_timeout_aborts_and_releases_the_container(tmp_path, monkeypatch):
    """@brief A run past the bound is aborted, reported as timeout, and cleaned up."""
    from adore.web import model_connection

    profiles = project(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.setattr(model_connection, "CONTAINER_TIMEOUT_SECONDS", 1)
    runtime = Runtime(tmp_path, "run_tool_calls_chatgpt", "--hang")
    assert probe(profiles, runtime)["reason"] == "timeout"
    assert any("rm" in argv for argv, _ in runtime.calls)


def test_missing_credential_is_reported_without_a_container(tmp_path, monkeypatch):
    """@brief No saved or server key for the provider: credential-missing, nothing started."""
    profiles = project(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    runtime = Runtime(tmp_path, "run_connection_test_endpoint")
    assert probe(profiles, runtime)["reason"] == "credential-missing"
    assert runtime.calls == [] and runtime.spawned == []


@pytest.mark.parametrize("keyed", [False, True])
def test_endpoint_probe_places_models_json_and_passes_the_endpoint_key(
        tmp_path, monkeypatch, keyed):
    """@brief custom: models.json copied into the agent dir before Pi; key only in the env."""
    profiles = project(tmp_path)
    set_executor(profiles, "custom", "qwen/qwen3.5-9b", "http://172.27.80.1:1234/v1")
    monkeypatch.delenv("ADORE_ENDPOINT_API_KEY", raising=False)
    if keyed:
        (profiles.profile_dir("alpha") / ".env").write_text(f"ADORE_ENDPOINT_API_KEY={SECRET}\n")
    runtime = Runtime(tmp_path, "run_connection_test_endpoint")
    result = probe(profiles, runtime)
    assert result["reason"] == "ready" and result["model"] == "qwen/qwen3.5-9b"
    assert runtime.models == [{"providers": {"adore-endpoint": {
        "baseUrl": "http://172.27.80.1:1234/v1", "api": "openai-completions",
        "apiKey": "$ADORE_ENDPOINT_API_KEY" if keyed else "adore-no-key",
        "models": [{"id": "qwen/qwen3.5-9b"}]}}}]
    copy = next(argv for argv, _ in runtime.calls if "cp" in argv)
    assert copy[-2:] == ["/adore/io/pi-models.json", "/home/adore/.adore-pi-agent/models.json"]
    pi = runtime.spawned[0][0]
    assert pi[pi.index("--provider") + 1] == "adore-endpoint"
    run = next(kwargs for argv, kwargs in runtime.calls if "run" in argv and "infinity" in argv)
    assert (run["env"].get("ADORE_ENDPOINT_API_KEY") == SECRET) is keyed
    assert all(SECRET not in " ".join(argv) for argv, _ in runtime.calls + runtime.spawned)


def test_endpoint_probe_stops_when_models_json_cannot_be_placed(tmp_path, monkeypatch):
    """@brief A failed copy into the agent dir is a runtime error; Pi never starts."""
    profiles = project(tmp_path)
    set_executor(profiles, "custom", "m", "http://172.27.80.1:1234/v1")
    runtime = Runtime(tmp_path, "run_connection_test_endpoint", copy_fails=True)
    assert probe(profiles, runtime)["reason"] == "runtime-error"
    assert runtime.spawned == [] and any("rm" in argv for argv, _ in runtime.calls)


@pytest.mark.parametrize("mode", ["image", "cleanup", "garbage", "missing-cli"])
def test_runtime_failures_fail_closed(tmp_path, monkeypatch, mode):
    """@brief Missing image, cleanup failure, malformed output and a missing CLI fail closed."""
    profiles = project(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    options = {"garbage": ["--garbage"], "missing-cli": ["--crash-after", "0", "--exit", "127"]}
    runtime = Runtime(tmp_path, "run_connection_test_endpoint", *options.get(mode, []),
                      image_missing=mode == "image", cleanup_fails=mode == "cleanup")
    if mode == "missing-cli":
        runtime.popen = lambda argv, **kwargs: subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", "import sys; sys.exit(127)"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if mode == "cleanup":
        from adore.isolation import IsolationError

        with pytest.raises(IsolationError):
            probe(profiles, runtime)
        return
    result = probe(profiles, runtime)
    expected = {"image": "image-missing", "garbage": "invalid-response",
                "missing-cli": "cli-missing"}[mode]
    assert result["reason"] == expected and result["ready"] is False
    if mode == "image":
        assert not any("run" in argv for argv, _ in runtime.calls)


def chatgpt_project(tmp_path, *, state: str = "signed-in"):
    """@brief A ChatGPT project and the server's credential files."""
    profiles = project(tmp_path)
    set_executor(profiles, "chatgpt", "gpt-5.6-luna")
    directory = profiles.home / "chatgpt"
    chatgpt.prepare(directory)
    if state != "not-signed-in":
        (directory / "auth.json").write_text(json.dumps({"openai": {
            "type": "oauth", "access": "a", "refresh": "r", "expires": 1}}), encoding="utf-8")
    if state == "sign-in-again":
        (directory / "sign-in-again").write_text("", encoding="utf-8")
    return profiles


def test_chatgpt_probe_answers_with_a_fresh_access_token(tmp_path, monkeypatch):
    """@brief The token rides only on Pi's launch environment; the refresh token stays home."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    profiles = chatgpt_project(tmp_path)
    runtime = Runtime(tmp_path, "run_connection_test_endpoint")
    result = probe(profiles, runtime)
    assert result == {"executor": "pi", "model": "gpt-5.6-luna", "ready": True, "reason": "ready"}
    helper = next(argv for argv, _ in runtime.calls if CONTAINER_SCRIPT in argv)
    assert [helper[i + 1] for i, part in enumerate(helper) if part == "--volume"] == [
        f"{(profiles.home / 'chatgpt').resolve().as_posix()}:/adore/chatgpt"]
    assert int(helper[-1]) >= 90 + TOKEN_MARGIN_SECONDS
    argv, env = runtime.spawned[0]
    assert env["OPENAI_API_KEY"] == CHATGPT_TOKEN
    assert argv[argv.index("--provider") + 1] == "openai"
    run = next(kwargs for argv, kwargs in runtime.calls if "run" in argv and "/adore/io" in
               " ".join(argv))
    assert "OPENAI_API_KEY" not in (run.get("env") or {})
    assert all(CHATGPT_TOKEN not in " ".join(argv) for argv, _ in runtime.calls + runtime.spawned)
    assert all("/adore/chatgpt" not in " ".join(argv) for argv, _ in runtime.calls
               if CONTAINER_SCRIPT not in argv)


@pytest.mark.parametrize(("state", "answer", "reason"), [
    ("not-signed-in", None, "sign-in-required"),
    ("sign-in-again", None, "sign-in-required"),
    ("signed-in", {"status": "sign-in-again"}, "sign-in-required"),
    ("signed-in", {"status": "not-eligible"}, "subscription-refused"),
    ("signed-in", {"status": "unavailable"}, "connection-failed"),
    ("signed-in", {"status": "garbage"}, "runtime-error"),
])
def test_chatgpt_probe_without_a_token_starts_no_run_container(tmp_path, state, answer, reason):
    """@brief No token: a closed reason and no Pi run container."""
    profiles = chatgpt_project(tmp_path, state=state)
    runtime = Runtime(tmp_path, "run_connection_test_endpoint", token_answer=answer)
    assert probe(profiles, runtime)["reason"] == reason
    assert runtime.spawned == []
    assert not any("/adore/io" in " ".join(argv) for argv, _ in runtime.calls)


@pytest.mark.parametrize(("fixture", "old", "new", "reason"), [
    ("failed_invalid_api_key", "Incorrect API key provided",
     "subscription_sharing_user_not_eligible", "subscription-refused"),
    ("failed_rate_limit_retry", "", "", "usage-limit"),
])
def test_chatgpt_refusals_have_their_own_reasons(tmp_path, monkeypatch, fixture, old, new, reason):
    """@brief A plan that cannot share its subscription, and a reached usage limit."""
    profiles = chatgpt_project(tmp_path)
    text = (FIXTURES / f"{fixture}.jsonl").read_text("utf-8")
    changed = tmp_path / "changed.jsonl"
    changed.write_text(text.replace(old, new) if old else text, encoding="utf-8")
    runtime = Runtime(tmp_path, fixture)
    runtime.fixture = changed
    assert probe(profiles, runtime)["reason"] == reason


# END OF FILE
