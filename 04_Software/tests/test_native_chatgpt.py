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
@file test_native_chatgpt.py
@brief Native ChatGPT sign-in, scoped stages and model diagnostics.
@details Injects managed Pi, process and helper boundaries for offline Windows/Linux proof.
"""

from __future__ import annotations

# IMPORTS
import json
from pathlib import Path
import subprocess
import sys
import time

from adore import chatgpt
from adore.pi_installation import ManagedPi, PiInstallationError
from adore.util import CommandResult
import pytest

from tests.test_chatgpt import CALLBACK, signed_in

TOKEN = "native-stage-access-0123456789"
FAKE = Path(__file__).with_name("fake_chatgpt_helper.py")


@pytest.fixture
def native(tmp_path, monkeypatch):
    """@brief Inject managed paths and the native external command boundary."""
    pi = ManagedPi(tmp_path / "node.exe", tmp_path / "managed pi")
    monkeypatch.setattr("adore.pi_installation.verify_pi", lambda **_: pi)
    monkeypatch.setenv("NODE_OPTIONS", "--import=hostile.js")
    monkeypatch.setenv("ADORE_PI_PACKAGE", "hostile-package")
    monkeypatch.setenv("GITEA_TOKEN", "forge-secret-value")
    calls = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return CommandResult(
            argv,
            stdout=json.dumps(
                {"status": "ok", "token": TOKEN, "expires": int(time.time() * 1000) + 3600000}
            ),
        )

    return chatgpt.NativeHelper(runner=runner), pi, calls


def test_native_token_uses_managed_paths_and_private_filtered_environment(tmp_path, native):
    """@brief The trusted helper uses no container, personal setup or project PATH."""
    helper, pi, calls = native
    directory = tmp_path / "auth"
    signed_in(directory)
    assert chatgpt.bearer_token(helper, directory, 2100) == TOKEN
    argv, options = calls[-1]
    assert argv[0] == str(pi.node)
    assert Path(argv[1]).name == "adore-chatgpt.mjs"
    env = options["env"]
    assert env["PI_CODING_AGENT_DIR"] == str(directory.resolve())
    assert env["ADORE_PI_PACKAGE"] == str(
        pi.prefix / "node_modules/@earendil-works/pi-coding-agent"
    )
    assert options["cwd"] == directory.resolve()
    assert "NODE_OPTIONS" not in env and "GITEA_TOKEN" not in env
    assert TOKEN not in " ".join(argv)
    assert "auth.json" not in " ".join(argv)


@pytest.mark.parametrize(
    "bad",
    [
        "garbage",
        "[]",
        "{}",
        '{"status":[]}',
        '{"status":{}}',
        '{"status":"ok","token":"short","expires":0}',
    ],
)
def test_native_token_rejects_invalid_helper_output(tmp_path, native, bad):
    """@brief Invalid native stdout never supplies a stage credential."""
    helper, _, _ = native
    helper.runner = lambda argv, **_: CommandResult(argv, stdout=bad)
    directory = tmp_path / "auth"
    signed_in(directory)
    with pytest.raises(chatgpt.ChatGptError, match="helper-failed"):
        chatgpt.bearer_token(helper, directory, 600)


@pytest.mark.parametrize(
    "code,timed_out,expected", [(1, False, "helper-failed"), (124, True, "unavailable")]
)
def test_native_token_refuses_bad_exit_and_timeout(tmp_path, native, code, timed_out, expected):
    """@brief A plausible answer cannot override a failed native helper exit."""
    helper, _, _ = native
    helper.runner = lambda argv, **_: CommandResult(
        argv,
        code,
        json.dumps({"status": "ok", "token": TOKEN, "expires": int(time.time() * 1000) + 3600000}),
        timed_out=timed_out,
    )
    directory = tmp_path / "auth"
    signed_in(directory)
    with pytest.raises(chatgpt.ChatGptError, match=expected):
        chatgpt.bearer_token(helper, directory, 600)


def test_native_sign_in_and_cancel_use_only_owned_process(tmp_path, native):
    """@brief Native login uses the same validated state protocol and bounded cancellation."""
    helper, _, _ = native
    processes = []

    def popen(argv, **kwargs):
        directory = kwargs["env"]["PI_CODING_AGENT_DIR"]
        process = subprocess.Popen(
            [sys.executable, "-I", str(FAKE), "--dir", directory, "login"], **kwargs
        )
        processes.append(process)
        return process

    directory = tmp_path / "auth"
    session = chatgpt.SignIn(helper, directory, popen=popen)
    url = session.start()
    assert url.startswith("https://auth.openai.com/")
    with pytest.raises(chatgpt.ChatGptError, match="state-mismatch"):
        session.submit(f"{CALLBACK}?code=fake&state=foreign-state")
    session.submit(f"{CALLBACK}?code=fake&state={session.state}")
    assert chatgpt.status(directory) == "signed-in"
    assert processes[-1].poll() is not None
    other = chatgpt.SignIn(helper, directory, popen=popen)
    other.start()
    other.cancel()
    assert processes[-1].poll() is not None
    other.cancel()


def test_native_missing_pi_is_typed_without_leaking_paths(tmp_path, monkeypatch):
    """@brief Missing native prerequisites use the shared closed helper failure."""

    def missing(**_):
        raise PiInstallationError("pi-missing", "private-path-and-host")

    monkeypatch.setattr("adore.pi_installation.verify_pi", missing)
    directory = tmp_path / "auth"
    signed_in(directory)
    with pytest.raises(chatgpt.ChatGptError, match="helper-failed"):
        chatgpt.bearer_token(chatgpt.NativeHelper(), directory, 600)


def test_native_helper_is_the_same_pinned_oauth_protocol():
    """@brief Packaged native and image helpers cannot drift."""
    root = Path(__file__).resolve().parents[1]
    assert (root / "adore/executor/adore-chatgpt.mjs").read_bytes() == (
        root / "docker/pi/adore-chatgpt.mjs"
    ).read_bytes()


@pytest.mark.parametrize("system", ["Windows", "Linux"])
def test_native_stage_token_is_explicit_and_redacted(tmp_path, monkeypatch, system):
    """@brief Only explicit gate binding can inject the subscription credential."""
    from adore.local_execution import LocalBackend

    from tests.test_local_execution import local_fixture

    config, context, _, controller, work = local_fixture(tmp_path, monkeypatch)
    config.executor.provider = "chatgpt"
    config.executor.env_keys = []
    context["system"] = system
    backend = LocalBackend(config, context=context, controller=controller)
    exchange = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, exchange, {})
    unbound = backend.bind("run-1", {"OPENAI_API_KEY": TOKEN})
    assert "OPENAI_API_KEY" not in unbound.env
    target = backend.bind("run-1", {"OPENAI_API_KEY": TOKEN}, secrets=(TOKEN,))
    assert target.auth_available()
    assert target.env["OPENAI_API_KEY"] == TOKEN
    assert target.redact("credential=" + TOKEN) == "credential=[REDACTED]"
    with target.pi_session(target.pi_argv(config.executor.model, "openai"), []):
        argv, _, env = controller.streams[-1]
        assert env["OPENAI_API_KEY"] == TOKEN and TOKEN not in str(argv)
        assert not (Path(env["PI_CODING_AGENT_DIR"]) / "auth.json").exists()
    assert TOKEN not in (exchange.parent / "local-control/runtime.json").read_text()


@pytest.mark.parametrize("code", [None, "not-signed-in", "sign-in-again", "unavailable"])
def test_native_model_probe_uses_subscription_source(tmp_path, monkeypatch, code):
    """@brief Model and shell checks use fresh subscription tokens or fail before Pi."""
    from adore.web.model_connection import probe_model_connection

    from tests.test_local_execution import local_fixture

    config, _, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    config.executor.provider = "chatgpt"
    config.executor.env_keys = []
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *_: controller)
    asked = []

    def source(helper, directory, seconds, **_):
        assert isinstance(helper, chatgpt.NativeHelper)
        asked.append(seconds)
        if code:
            raise chatgpt.ChatGptError(code)
        return TOKEN

    monkeypatch.setattr(chatgpt, "bearer_token", source)
    result = probe_model_connection(
        config, lambda *a, **k: pytest.fail("container called"), tmp_path / ".env"
    )
    if code:
        assert result["reason"] == (
            "connection-failed" if code == "unavailable" else "sign-in-required"
        )
        assert not controller.streams
    else:
        assert result["ready"] is True
        assert controller.streams[-1][2]["OPENAI_API_KEY"] == TOKEN
    assert asked == [90 + chatgpt.TOKEN_MARGIN_SECONDS]


@pytest.mark.parametrize(
    "state,ready", [("not-signed-in", False), ("signed-in", True), ("sign-in-again", False)]
)
def test_native_readiness_reads_subscription_without_model_or_refresh(
    tmp_path, monkeypatch, state, ready
):
    """@brief Host readiness uses the ADORE store rather than a personal API key."""
    from adore.local_execution import probe_local_executor

    from tests.test_local_execution import local_fixture

    config, _, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    config.executor.provider = "chatgpt"
    config.executor.env_keys = []
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *_: controller)
    directory = tmp_path / "subscription"
    if state != "not-signed-in":
        signed_in(directory)
    if state == "sign-in-again":
        (directory / chatgpt.MARK_FILE).touch()
    monkeypatch.setenv("OPENAI_API_KEY", "ambient-key-must-not-count")
    assert probe_local_executor(config, chatgpt_dir=directory)["ready"] is ready
    assert not controller.streams


@pytest.mark.parametrize("failure", [False, True])
def test_native_conductor_selects_helper_and_binds_only_the_stage(tmp_path, monkeypatch, failure):
    """@brief The default conductor token source and native target work together."""
    from tests.test_chatgpt_stage import RecordingExecutor
    from tests.test_local_execution import local_fixture
    from tests.test_orchestrator import make_engine, make_run, task

    root = tmp_path / "local"
    root.mkdir()
    config, _, backend, _, work = local_fixture(root, monkeypatch)
    executor = RecordingExecutor()
    engine, *_ = make_engine(tmp_path / "engine", executor=executor)
    config.executor.provider = "chatgpt"
    config.executor.env_keys = []
    engine.config, engine.backend = config, backend
    run = make_run(engine)
    run.stage = "build"
    run.worktree = str(work)
    exchange = Path(config.state.store_root) / "runs" / run.run_id / "io"
    backend.provision(run.container, work, work, exchange, {})
    from adore.preparation import resolve_plan

    run.execution = {
        "plan": resolve_plan(config),
        "resource": backend.resource_identity(run.container),
        "status": "not-required",
        "attempts": 0,
        "steps": [],
        "history": [],
        "reprepare": False,
    }
    asked = []

    def token(helper, directory, seconds):
        assert isinstance(helper, chatgpt.NativeHelper)
        asked.append(seconds)
        if failure:
            raise chatgpt.ChatGptError("sign-in-again")
        return TOKEN

    monkeypatch.setattr(chatgpt, "bearer_token", token)
    result = engine._launch_stage(run, engine.forge.ticket, task("build"))
    assert asked == [config.budgets.per_gate_timeout_seconds + 300]
    if failure:
        assert result.exit_code == 1 and executor.targets == []
    else:
        assert result.exit_code == 0
        assert executor.targets[0].env["OPENAI_API_KEY"] == TOKEN
        assert TOKEN not in executor.targets[0].redact(TOKEN)
    assert TOKEN not in str(engine.store.load(run.run_id).__dict__)


@pytest.mark.parametrize("expires", [0, True, "tomorrow", None])
def test_native_token_requires_a_valid_lifetime(tmp_path, native, expires):
    """@brief An otherwise plausible helper answer cannot carry an invalid expiry."""
    helper, _, _ = native
    directory = tmp_path / "auth"
    signed_in(directory)
    helper.runner = lambda argv, **_: CommandResult(
        argv, stdout=json.dumps({"status": "ok", "token": TOKEN, "expires": expires})
    )
    with pytest.raises(chatgpt.ChatGptError):
        chatgpt.bearer_token(helper, directory, 600)


@pytest.mark.parametrize("exit_code,expected", [(7, "helper-failed"), (0, "unreadable")])
def test_native_sign_in_refuses_failed_completion(tmp_path, native, exit_code, expected):
    """@brief A success event needs successful termination and a stored credential."""
    helper, _, _ = native
    state = "native-state-123456789"
    script = (
        "import json,sys; print(json.dumps("
        + repr({"event": "auth_url", "url": "https://auth.openai.com/authorize?state=" + state})
        + "),flush=True); "
        "sys.stdin.readline(); print(json.dumps({'event':'signed-in'}),flush=True); sys.exit("
        + str(exit_code)
        + ")"
    )

    def popen(argv, **kwargs):
        return subprocess.Popen([sys.executable, "-I", "-c", script], **kwargs)

    session = chatgpt.SignIn(helper, tmp_path / "auth", popen=popen)
    session.start()
    with pytest.raises(chatgpt.ChatGptError, match=expected):
        session.submit(f"{CALLBACK}?code=fake&state={state}")
    assert session.finished and session.process.poll() is not None


@pytest.mark.parametrize("phase", ["start", "submit"])
@pytest.mark.parametrize("code", [[], {}])
def test_native_sign_in_refuses_malformed_error_codes(tmp_path, native, phase, code):
    """@brief Unhashable helper JSON codes produce only the closed typed failure."""
    helper, _, _ = native
    state = "native-state-123456789"
    error = {"event": "error", "code": code}
    script = "import json,sys; "
    if phase == "submit":
        script += (
            "print(json.dumps("
            + repr({"event": "auth_url", "url": "https://auth.openai.com/authorize?state=" + state})
            + "),flush=True); sys.stdin.readline(); "
        )
    script += "print(json.dumps(" + repr(error) + "),flush=True)"

    def popen(argv, **kwargs):
        return subprocess.Popen([sys.executable, "-I", "-c", script], **kwargs)

    session = chatgpt.SignIn(helper, tmp_path / "auth", popen=popen)
    with pytest.raises(chatgpt.ChatGptError, match="helper-failed"):
        if phase == "start":
            session.start()
        else:
            session.start()
            session.submit(f"{CALLBACK}?code=fake&state={state}")
    assert session.finished and session.process.poll() is not None


def test_native_subscription_usage_limit_has_its_own_reason(tmp_path, monkeypatch):
    """@brief Native subscription quota is distinguished from API-key throttling."""
    from adore.executor.pi_rpc import PiRpcResult
    from adore.web.model_connection import probe_model_connection

    from tests.test_local_execution import local_fixture

    config, _, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    config.executor.provider = "chatgpt"
    config.executor.env_keys = []
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *_: controller)
    monkeypatch.setattr(chatgpt, "bearer_token", lambda *a, **k: TOKEN)
    monkeypatch.setattr(
        "adore.executor.pi_rpc.run_pi_rpc",
        lambda *a, **k: PiRpcResult("failed", 1, failure="rate-limit"),
    )
    result = probe_model_connection(
        config, lambda *a, **k: pytest.fail("container called"), tmp_path / ".env"
    )
    assert result["reason"] == "usage-limit"


# END OF FILE
