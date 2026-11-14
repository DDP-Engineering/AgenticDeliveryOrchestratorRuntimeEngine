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
@file test_web_chatgpt.py
@brief Sign in with ChatGPT from the web interface: routes, roles, audit and readiness.
@details The fake helper of `test_chatgpt` stands in for Pi in the executor
         image; no network, no real token.
"""

from __future__ import annotations

import importlib
import json
import re
import sqlite3

from adore import chatgpt
from adore.util import CommandResult
from adore.web.app import create_app
import pytest

from tests.configuration_client import TestClient
from tests.test_chatgpt import CALLBACK, FakeRuntime
from tests.test_model_connection import project, set_executor

STATE = "fake-state-0123456789"
REDIRECT = f"{CALLBACK}?code=fake-code-77&state={STATE}&client_id=x"


def app_for(tmp_path, *options: str, local: bool = False, popen=None):
    """@brief A web app with a ChatGPT project and the fake helper."""
    profiles = project(tmp_path)
    set_executor(profiles, "chatgpt", "gpt-5.6-luna")
    if local:
        # Native projects use the same server subscription.
        path = profiles.config_path("alpha")
        raw = re.sub(r"required_tool_checks = \[.*?\]", "required_tool_checks = []",
                     path.read_text(encoding="utf-8"), flags=re.S)
        path.write_text(raw.replace(
            'backend = "container"', 'backend = "local"').replace(
            'selinux_relabel = "auto"', 'selinux_relabel = "off"'), encoding="utf-8")
    runtime = FakeRuntime("--record", str(tmp_path / "pasted.txt"), *options)
    module = importlib.import_module("adore.web.app")
    app = module.create_app(profiles.home, probe_runner=runtime.runner,
                            chatgpt_popen=popen or runtime.popen)
    return app, profiles, runtime


def sign_in(client: TestClient, username: str = "admin", password: str = "admin") -> dict:
    """@brief Start a browser session and return the CSRF header."""
    csrf = client.post("/api/v1/session",
                       json={"username": username, "password": password}).json()["csrf"]
    return {"X-CSRF-Token": csrf}


def audit_text(profiles) -> str:
    """@brief Every audit row, as text."""
    with sqlite3.connect(profiles.home / "web.db") as connection:
        return json.dumps(connection.execute("SELECT * FROM audit").fetchall())


def test_admin_signs_the_server_in_and_out(tmp_path):
    """@brief Link out, wrong state refused, redirect in, signed in, disconnected."""
    app, profiles, runtime = app_for(tmp_path)
    directory = profiles.home / "chatgpt"
    with TestClient(app) as client:
        headers = sign_in(client)
        assert client.get("/api/v1/chatgpt-sign-in").json() == {
            "status": "not-signed-in", "pending": False}
        started = client.post("/api/v1/projects/alpha/chatgpt-sign-in", headers=headers)
        assert started.status_code == 200
        assert started.json()["authorize_url"].startswith("https://auth.openai.com/")
        assert started.json()["expires_in"] == chatgpt.SIGN_IN_SECONDS
        assert client.get("/api/v1/chatgpt-sign-in").json()["pending"] is True
        wrong = client.put("/api/v1/chatgpt-sign-in", headers=headers,
                           json={"redirect_url": f"{CALLBACK}?code=c&state=other-state-1"})
        assert wrong.status_code == 400
        assert wrong.json()["detail"]["code"] == "chatgpt_state_mismatch"
        done = client.put("/api/v1/chatgpt-sign-in", headers=headers,
                          json={"redirect_url": REDIRECT})
        assert done.status_code == 200
        assert done.json() == {"status": "signed-in", "pending": False}
        assert (tmp_path / "pasted.txt").read_text(encoding="utf-8") == REDIRECT + "\n"
        assert chatgpt.status(directory) == "signed-in"
        gone = client.delete("/api/v1/chatgpt-sign-in", headers=headers)
        assert gone.json() == {"status": "not-signed-in", "pending": False}
        assert not (directory / "auth.json").exists() and (directory / "device-id").exists()
        rows = audit_text(profiles)
    for action in ("chatgpt-sign-in-started", "chatgpt-sign-in-completed",
                   "chatgpt-disconnected"):
        assert action in rows
    for secret in (STATE, "fake-code", "auth.openai.com", "fake-access", "127.0.0.1:1455"):
        assert secret not in rows
    login = next(argv for argv in runtime.calls if "run" in argv)
    assert [login[i + 1] for i, part in enumerate(login) if part == "--volume"] == [
        f"{directory.resolve().as_posix()}:/adore/chatgpt"]


@pytest.mark.parametrize(("address", "options", "status", "code"), [
    (f"{CALLBACK}?error=access_denied&state={STATE}", [], 502, "chatgpt_access_denied"),
    (f"{CALLBACK}?error=subscription_sharing_user_not_eligible&state={STATE}", [], 502,
     "chatgpt_not_eligible"),
    (REDIRECT, ["--answer", "code-rejected"], 502, "chatgpt_code_rejected"),
    (REDIRECT, ["--answer", "unavailable"], 503, "chatgpt_sign_in_unavailable"),
    (REDIRECT, ["--answer", "refused"], 502, "chatgpt_sign_in_refused"),
])
def test_an_openai_refusal_ends_the_sign_in_with_its_code(tmp_path, address, options, status,
                                                          code):
    """@brief Each refusal has one code, ends the sign-in and is audited without values."""
    app, profiles, _ = app_for(tmp_path, *options)
    with TestClient(app) as client:
        headers = sign_in(client)
        client.post("/api/v1/projects/alpha/chatgpt-sign-in", headers=headers)
        result = client.put("/api/v1/chatgpt-sign-in", headers=headers,
                            json={"redirect_url": address})
        assert result.status_code == status and result.json()["detail"]["code"] == code
        assert client.get("/api/v1/chatgpt-sign-in").json() == {
            "status": "not-signed-in", "pending": False}
        rows = audit_text(profiles)
    assert "chatgpt-sign-in-failed" in rows and code in rows
    assert STATE not in rows and "fake-code" not in rows


def test_cancel_and_paste_without_pending_sign_in(tmp_path):
    """@brief Cancel ends the helper; a paste without a sign-in and a local run are refused."""
    app, _, runtime = app_for(tmp_path)
    with TestClient(app) as client:
        headers = sign_in(client)
        missing = client.put("/api/v1/chatgpt-sign-in", headers=headers,
                             json={"redirect_url": REDIRECT})
        assert missing.status_code == 409
        assert missing.json()["detail"]["code"] == "chatgpt_sign_in_not_pending"
        client.post("/api/v1/projects/alpha/chatgpt-sign-in", headers=headers)
        cancelled = client.delete("/api/v1/chatgpt-sign-in/pending", headers=headers)
        assert cancelled.json() == {"status": "not-signed-in", "pending": False}
        assert any(argv[1:3] == ["rm", "--force"] for argv in runtime.calls)


@pytest.mark.parametrize("stage,code", [
    ("runtime", "container_runtime_unavailable"), ("image", "executor_image_unavailable"),
])
@pytest.mark.parametrize("outcome", ["exit", "timeout", "invalid-exit"])
@pytest.mark.parametrize("runtime", ["docker", "wsl -d Ubuntu -- docker"])
def test_container_prerequisite_failure_does_not_start_sign_in(
    tmp_path, stage, code, outcome, runtime,
):
    """@brief Report container setup precisely before any OAuth helper or credential effect."""
    profiles = project(tmp_path)
    set_executor(profiles, "chatgpt", "gpt-5.6-luna")
    path = profiles.config_path("alpha")
    path.write_text(path.read_text(encoding="utf-8").replace(
        'runtime = "docker"', f'runtime = "{runtime}"'), encoding="utf-8")
    prefix = (["docker"] if runtime == "docker" else
              ["wsl", "-d", "Ubuntu", "--exec", "docker"])
    calls = []

    def runner(argv, **kwargs):
        calls.append(list(argv))
        if argv == [*prefix, "info"] and stage == "runtime" or (
            argv[len(prefix):len(prefix) + 2] == ["image", "inspect"] and stage == "image"
        ):
            return CommandResult(exit_code=(False if outcome == "invalid-exit" else
                                            0 if outcome == "timeout" else 1),
                                 timed_out=outcome == "timeout", stderr="PRIVATE")
        return CommandResult()

    def forbidden(*args, **kwargs):
        raise AssertionError("OAuth helper started without its container prerequisites")

    app = create_app(profiles.home, probe_runner=runner, chatgpt_popen=forbidden)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/projects/alpha/chatgpt-sign-in", headers=sign_in(client))
        assert response.status_code == 503, response.text
        assert response.json()["detail"]["code"] == code
        assert "PRIVATE" not in response.text
        assert client.get("/api/v1/chatgpt-sign-in").json()["pending"] is False
    assert not (profiles.home / "chatgpt/auth.json").exists()
    assert code in audit_text(profiles)
    assert calls[0] == [*prefix, "info"]
    if stage == "runtime":
        assert len(calls) == 1


def test_a_helper_that_cannot_start_is_unavailable(tmp_path, monkeypatch):
    """@brief An image without ADORE's helper fails the start with a typed code."""
    monkeypatch.setenv("FAKE_HELPER_FAIL", "1")
    app, _, _ = app_for(tmp_path)
    with TestClient(app) as client:
        result = client.post("/api/v1/projects/alpha/chatgpt-sign-in", headers=sign_in(client))
        assert result.status_code == 503
        assert result.json()["detail"]["code"] == "chatgpt_helper_failed"


@pytest.mark.parametrize(("method", "path", "body"), [
    ("GET", "/api/v1/chatgpt-sign-in", None),
    ("POST", "/api/v1/projects/alpha/chatgpt-sign-in", None),
    ("PUT", "/api/v1/chatgpt-sign-in", {"redirect_url": REDIRECT}),
    ("DELETE", "/api/v1/chatgpt-sign-in/pending", None),
    ("DELETE", "/api/v1/chatgpt-sign-in", None),
])
def test_routes_are_admin_only_and_changes_need_csrf(tmp_path, method, path, body):
    """@brief Developers get 403 admin_required; a change without CSRF gets 403."""
    app, profiles, runtime = app_for(tmp_path)
    user = app.state.web_store.create_user("dev", "longer-password", "developer")
    app.state.web_store.set_memberships(user["id"], ["alpha"])
    with TestClient(app) as client:
        headers = sign_in(client, "dev", "longer-password")
        result = client.request(method, path, json=body, headers=headers)
        assert result.status_code == 403
        assert result.json()["detail"]["code"] == "admin_required"
    with TestClient(app) as client:
        sign_in(client)
        if method != "GET":
            result = client.request(method, path, json=body)
            assert result.status_code == 403
            assert result.json()["detail"]["code"] == "csrf_required"
    assert runtime.calls == []
    assert not (profiles.home / "chatgpt" / "auth.json").exists()


def test_readiness_reports_the_sign_in_for_chatgpt_projects_only(tmp_path):
    """@brief executor_sign_in follows the server's status; other providers omit it."""
    def offline(argv, **_kwargs):
        return CommandResult(list(argv), 127)

    profiles = project(tmp_path)
    set_executor(profiles, "chatgpt", "gpt-5.6-luna")
    module = importlib.import_module("adore.web.app")
    app = module.create_app(profiles.home, probe_runner=offline)
    with TestClient(app) as client:
        headers = sign_in(client)
        checks = client.post("/api/v1/projects/alpha/readiness-check",
                             headers=headers).json()["checks"]
        assert checks["executor_sign_in"] is False
        directory = chatgpt.prepare(profiles.home / "chatgpt")
        (directory / "auth.json").write_text(json.dumps({"openai": {
            "type": "oauth", "access": "a", "refresh": "r", "expires": 1}}), encoding="utf-8")
        checks = client.post("/api/v1/projects/alpha/readiness-check",
                             headers=headers).json()["checks"]
        assert checks["executor_sign_in"] is True
        assert client.get("/api/v1/projects").status_code == 200
        path = profiles.config_path("alpha")
        path.write_text(path.read_text(encoding="utf-8").replace(
            'provider = "chatgpt"', 'provider = "openai"'), encoding="utf-8")
        checks = client.post("/api/v1/projects/alpha/readiness-check",
                             headers=headers).json()["checks"]
        assert "executor_sign_in" not in checks


def test_readiness_reflects_the_internet_switch(tmp_path, monkeypatch):
    """@brief Off adds the proxy image check; On with Brave adds the key check; exa neither."""
    from tests.test_model_connection import set_internet

    proxy_present = {"value": False}

    def runner(argv, **_kwargs):
        if list(argv[-3:]) == ["image", "inspect", "adore-egress-proxy:1.0.0"]:
            return CommandResult(list(argv), 0 if proxy_present["value"] else 1)
        return CommandResult(list(argv), 127)

    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    profiles = project(tmp_path)
    module = importlib.import_module("adore.web.app")
    app = module.create_app(profiles.home, probe_runner=runner)
    path = profiles.config_path("alpha")
    base = path.read_text(encoding="utf-8")
    with TestClient(app) as client:
        headers = sign_in(client)

        def checks() -> dict:
            return client.post("/api/v1/projects/alpha/readiness-check",
                               headers=headers).json()["checks"]

        assert checks()["egress_proxy"] is False
        proxy_present["value"] = True
        result = checks()
        assert result["egress_proxy"] is True and "web_search_key" not in result
        set_internet(profiles, True, "brave")
        result = checks()
        assert "egress_proxy" not in result and result["web_search_key"] is False
        (profiles.profile_dir("alpha") / ".env").write_text("BRAVE_API_KEY=brave-test-key\n",
                                                            encoding="utf-8")
        assert checks()["web_search_key"] is True
        path.write_text(base, encoding="utf-8")
        set_internet(profiles, True)
        result = checks()
        assert "egress_proxy" not in result and "web_search_key" not in result


def test_a_chatgpt_connection_result_holds_only_while_signed_in(tmp_path, monkeypatch):
    """@brief Disconnecting hides the saved Test AI connection result of ChatGPT projects."""
    from adore.state import StateStore

    app, profiles, _ = app_for(tmp_path)
    StateStore(tmp_path / "state").pause()
    directory = chatgpt.prepare(profiles.home / "chatgpt")
    (directory / "auth.json").write_text(json.dumps({"openai": {
        "type": "oauth", "access": "a", "refresh": "r", "expires": 1}}), encoding="utf-8")
    module = importlib.import_module("adore.web.app")
    monkeypatch.setattr(module, "probe_model_connection", lambda config, *_a, **_k: {
        "executor": "pi", "model": config.executor.model, "ready": True, "reason": "ready"})
    with TestClient(app) as client:
        headers = sign_in(client)
        assert client.post("/api/v1/projects/alpha/model-connection-test",
                           headers=headers).json()["ready"] is True
        assert client.get("/api/v1/projects/alpha/config").json()["model_connection"]["ready"]
        client.delete("/api/v1/chatgpt-sign-in", headers=headers)
        assert client.get("/api/v1/projects/alpha/config").json()["model_connection"] is None


def test_a_second_start_replaces_the_pending_sign_in(tmp_path):
    """@brief Starting again ends the first helper; only the new sign-in waits."""
    app, _, runtime = app_for(tmp_path)
    with TestClient(app) as client:
        headers = sign_in(client)
        client.post("/api/v1/projects/alpha/chatgpt-sign-in", headers=headers)
        first = next(argv for argv in runtime.calls if "run" in argv)
        first_name = first[first.index("--name") + 1]
        assert client.post("/api/v1/projects/alpha/chatgpt-sign-in",
                           headers=headers).status_code == 200
        names = [argv[argv.index("--name") + 1] for argv in runtime.calls if "run" in argv]
        assert len(names) == 2 and names[1] != first_name
        assert ["docker", "rm", "--force", first_name] in runtime.calls
        assert ["docker", "rm", "--force", names[1]] not in runtime.calls
        assert client.get("/api/v1/chatgpt-sign-in").json()["pending"] is True
        assert client.put("/api/v1/chatgpt-sign-in", headers=headers,
                          json={"redirect_url": REDIRECT}).json()["status"] == "signed-in"


# END OF FILE


def test_native_admin_uses_managed_helper_without_container(tmp_path, monkeypatch):
    """@brief Native projects can complete the same admin/CSRF-bound OAuth flow."""
    from pathlib import Path
    import subprocess
    import sys

    from adore.pi_installation import ManagedPi

    pi = ManagedPi(tmp_path / "node.exe", tmp_path / "pi")
    monkeypatch.setattr("adore.pi_installation.verify_pi", lambda **_: pi)
    calls = []

    def popen(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.Popen(
            [
                sys.executable,
                "-I",
                str(Path(__file__).with_name("fake_chatgpt_helper.py")),
                "--dir",
                kwargs["env"]["PI_CODING_AGENT_DIR"],
                "login",
            ],
            **kwargs,
        )

    app, profiles, runtime = app_for(tmp_path, local=True, popen=popen)
    with TestClient(app) as client:
        headers = sign_in(client)
        assert client.post("/api/v1/projects/alpha/chatgpt-sign-in").status_code == 403
        start = client.post("/api/v1/projects/alpha/chatgpt-sign-in", headers=headers)
        assert start.status_code == 200, start.json()
        assert (
            client.put(
                "/api/v1/chatgpt-sign-in",
                headers=headers,
                json={"redirect_url": REDIRECT},
            ).json()["status"]
            == "signed-in"
        )
        assert (
            client.delete("/api/v1/chatgpt-sign-in", headers=headers).json()["status"]
            == "not-signed-in"
        )
    assert calls[0][0][0] == str(pi.node)
    assert runtime.calls == []
    assert "fake-access" not in audit_text(profiles)

@pytest.mark.parametrize(
    "answer,status,code",
    [("signed-in", 200, None), ("not-eligible", 502, "chatgpt_not_eligible")],
)
def test_native_callback_completion_is_observed_without_manual_submit(
    tmp_path, monkeypatch, answer, status, code
):
    """@brief Status observes and audits Pi callback completion or a closed refusal."""
    from pathlib import Path
    import subprocess
    import sys
    import time

    from adore.pi_installation import ManagedPi

    pi = ManagedPi(tmp_path / "node.exe", tmp_path / "pi")
    monkeypatch.setattr("adore.pi_installation.verify_pi", lambda **_: pi)

    def popen(argv, **kwargs):
        return subprocess.Popen(
            [
                sys.executable,
                "-I",
                str(Path(__file__).with_name("fake_chatgpt_helper.py")),
                "--dir",
                kwargs["env"]["PI_CODING_AGENT_DIR"],
                "--auto-complete",
                "--answer",
                answer,
                "login",
            ],
            **kwargs,
        )

    app, profiles, runtime = app_for(tmp_path, local=True, popen=popen)
    with TestClient(app) as client:
        headers = sign_in(client)
        assert (
            client.post(
                "/api/v1/projects/alpha/chatgpt-sign-in", headers=headers
            ).status_code
            == 200
        )
        deadline = time.monotonic() + 2
        while True:
            view = client.get("/api/v1/chatgpt-sign-in")
            if (
                view.status_code != 200
                or not view.json()["pending"]
                or time.monotonic() > deadline
            ):
                break
            time.sleep(0.02)
        assert view.status_code == status
        if code:
            assert view.json()["detail"]["code"] == code
        else:
            assert view.json() == {"status": "signed-in", "pending": False}
        again = client.get("/api/v1/chatgpt-sign-in")
        assert again.json()["pending"] is False
    rows = audit_text(profiles)
    assert (
        rows.count(
            "chatgpt-sign-in-completed" if code is None else "chatgpt-sign-in-failed"
        )
        == 1
    )
    assert "fake-access" not in rows and "fake-code" not in rows
    assert runtime.calls == []
