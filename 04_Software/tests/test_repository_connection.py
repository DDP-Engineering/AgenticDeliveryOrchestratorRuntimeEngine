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
@file test_repository_connection.py
@brief Administrator host-readiness probe contract tests.
@details External command output is faked and never returned to the browser.
"""

import json
from pathlib import Path

from adore.profiles import ProfileStore
from adore.util import CommandResult
from adore.web.app import create_app
import pytest

from tests.configuration_client import TestClient


@pytest.mark.parametrize("metadata,code", [
    ([], "gitea_auth_missing"),
    ([{"name": "a", "url": "https://one.example"},
      {"name": "b", "url": "https://two.example"}], "gitea_auth_ambiguous"),
    ({"PRIVATE": "CLI-SECRET"}, "gitea_auth_invalid"),
])
def test_portable_gitea_missing_auth_api_is_safe(tmp_path, monkeypatch, metadata, code):
    """@brief Ticket reads expose a closed recovery cause; readiness remains a failed check."""
    profiles = project(tmp_path, "gitea")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-config"))

    def runner(argv, **kwargs):
        if argv[:3] == ["tea", "logins", "list"]:
            return CommandResult(stdout=json.dumps(metadata))
        if argv[:2] == ["tea", "api"]:
            return CommandResult(exit_code=1, stderr="Error: no available login")
        return CommandResult(stdout="tool version 1.0")

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        response = client.get("/api/v1/projects/alpha/tickets")
        assert response.status_code == 503 and response.json()["detail"]["code"] == code
        assert "PRIVATE" not in response.text and "CLI-SECRET" not in response.text
        check = client.post(
            "/api/v1/projects/alpha/readiness-check", headers={"X-CSRF-Token": csrf})
        assert check.status_code == 200, check.text
        assert check.json()["checks"]["forge_auth"] is False


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


@pytest.mark.parametrize("provider", ["gitlab", "github", "gitea"])
def test_connect_verifies_then_saves_scoped_account(tmp_path, provider):
    """@brief All providers save only after account and exact repository checks."""
    profiles = project(tmp_path, provider)
    calls = []
    repo = "mygroup/myproject"

    def runner(argv, *, cwd=None, timeout=None, env=None):
        calls.append((list(argv), env, timeout))
        is_user = argv[-1] == "user"
        return CommandResult(
            argv=list(argv),
            exit_code=0,
            stdout=json.dumps(
                {"username" if provider == "gitlab" else "login": "alice"}
                if is_user
                else {"path_with_namespace" if provider == "gitlab" else "full_name": repo}
            ),
            stderr="HTTP/1.1 200 OK" if provider == "gitea" else "",
        )

    app = create_app(profiles.home, probe_runner=runner)
    with TestClient(app) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        response = client.post(
            "/api/v1/projects/alpha/repository-connection",
            headers={"X-CSRF-Token": csrf},
            json={
                "server": "https://forge.example",
                "token": "test-private-value",
                "allow_http": False,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["account"] == "alice"
        assert "test-private-value" not in response.text
        assert len(calls) == 2 and all(t <= 8 for _, _, t in calls)
        assert all("test-private-value" not in " ".join(a) for a, _, _ in calls)
        saved = json.loads((profiles.profile_dir("alpha") / "repository-auth.json").read_text())
        assert (
            saved["token"] == "test-private-value"
            and saved["project_id"] == profiles.load("alpha").project_id
        )


def test_repository_connection_invalidates_previous_readiness(tmp_path, monkeypatch):
    """@brief A new scoped account never inherits the previous forge-auth result."""
    import adore.web.app as web_app

    profiles = project(tmp_path)
    checks = {
        "git": True,
        "forge_cli": True,
        "forge_auth": True,
        "container_runtime": True,
        "executor_cli": True,
        "egress_proxy": True,
    }
    monkeypatch.setattr(web_app, "_probe_setup", lambda *args, **kwargs:
                        {"workflow": "aegis", "checks": checks})

    def runner(argv, **kwargs):
        output = (
            {"username": "alice"}
            if argv[-1] == "user"
            else {"path_with_namespace": "mygroup/myproject"}
        )
        return CommandResult(argv=list(argv), stdout=json.dumps(output))

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        headers = {"X-CSRF-Token": csrf}
        assert (
            client.post("/api/v1/projects/alpha/readiness-check", headers=headers).json()["status"]
            == "partial"
        )
        response = client.post(
            "/api/v1/projects/alpha/repository-connection",
            headers=headers,
            json={"server": "https://forge.example", "token": "test-only", "allow_http": False},
        )
        assert response.status_code == 200, response.text
        assert client.get("/api/v1/projects/alpha").json()["verification"]["status"] == "stale"
        assert (
            client.post("/api/v1/projects/alpha/readiness-check", headers=headers).json()["status"]
            == "verified"
        )


@pytest.mark.parametrize(
    "server,token,allow",
    [
        ("https://user:pass@forge.example", "secret", False),
        ("https://forge.example/path", "secret", False),
        ("http://forge.example", "secret", False),
        ("https://forge.example", "bad\nvalue", False),
    ],
)
def test_connection_rejects_untrusted_inputs_without_commands(tmp_path, server, token, allow):
    """@brief Malformed server/token never reaches an external command."""
    profiles = project(tmp_path)

    def runner(*args, **kwargs):
        raise AssertionError("unexpected command")

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        response = client.post(
            "/api/v1/projects/alpha/repository-connection",
            headers={"X-CSRF-Token": csrf},
            json={"server": server, "token": token, "allow_http": allow},
        )
        assert response.status_code == 422
        assert token not in response.text
        assert not (profiles.profile_dir("alpha") / "repository-auth.json").exists()


@pytest.mark.parametrize("provider", ["gitea", "github", "gitlab"])
@pytest.mark.parametrize("failure", ["exit", "timeout", "json", "repository", "account"])
def test_failed_verification_retains_existing_credentials(tmp_path, provider, failure):
    """@brief Every external trust boundary rejects without replacing existing auth."""
    profiles = project(tmp_path, provider)
    path = profiles.profile_dir("alpha") / "repository-auth.json"
    path.write_text("old-protected-record", encoding="utf-8")

    def runner(argv, *, cwd=None, timeout=None, env=None):
        account = {"username" if provider == "gitlab" else "login": "alice"}
        repo = {"path_with_namespace" if provider == "gitlab" else "full_name": "mygroup/myproject"}
        if failure == "repository":
            repo = {"path_with_namespace" if provider == "gitlab" else "full_name": "other/repo"}
        if failure == "account":
            account = {"login": 17, "username": None}
        return CommandResult(
            argv=list(argv),
            exit_code=1 if failure == "exit" else 0,
            timed_out=failure == "timeout",
            stdout="not-json PRIVATE"
            if failure == "json"
            else json.dumps(account if argv[-1] == "user" else repo),
            stderr="HTTP/1.1 200 OK\nPRIVATE",
        )

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        response = client.post(
            "/api/v1/projects/alpha/repository-connection",
            headers={"X-CSRF-Token": csrf},
            json={"server": "https://forge.example", "token": "PRIVATE"},
        )
        assert response.status_code == 400, response.text
        assert "PRIVATE" not in response.text
        assert path.read_text() == "old-protected-record"


@pytest.mark.parametrize(
    "status", ["", "HTTP/1.1 401 Unauthorized", "HTTP/1.1 200 OK\nHTTP/1.1 503 Unavailable"]
)
def test_tea_zero_exit_requires_final_success_http_status(tmp_path, status):
    """@brief Tea zero exit cannot hide a missing or final failure HTTP status."""
    profiles = project(tmp_path, "gitea")

    def runner(argv, **kwargs):
        return CommandResult(
            argv=list(argv), exit_code=0, stdout='{"login":"alice"}', stderr=status
        )

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        response = client.post(
            "/api/v1/projects/alpha/repository-connection",
            headers={"X-CSRF-Token": csrf},
            json={"server": "https://forge.example", "token": "PRIVATE"},
        )
        assert response.status_code == 400


def test_connection_requires_admin_csrf_and_idle_project(tmp_path):
    """@brief Browser identity and conductor lock protect credential replacement."""
    from adore.state import StateStore

    profiles = project(tmp_path)

    def runner(*args, **kwargs):
        raise AssertionError("unauthorized command")

    app = create_app(profiles.home, probe_runner=runner)
    dev = app.state.web_store.create_user("dev", "longer-password", "developer")
    app.state.web_store.set_memberships(dev["id"], ["alpha"])
    body = {"server": "https://forge.example", "token": "PRIVATE"}
    with TestClient(app) as client:
        assert (
            client.post("/api/v1/projects/alpha/repository-connection", json=body).status_code
            == 401
        )
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        assert (
            client.post("/api/v1/projects/alpha/repository-connection", json=body).status_code
            == 403
        )
        state = StateStore(tmp_path / "state")
        assert state.acquire_lock()
        try:
            response = client.post(
                "/api/v1/projects/alpha/repository-connection",
                json=body,
                headers={"X-CSRF-Token": csrf},
            )
            assert response.status_code == 409
        finally:
            state.release_lock()
        client.delete("/api/v1/session", headers={"X-CSRF-Token": csrf})
        csrf = client.post(
            "/api/v1/session", json={"username": "dev", "password": "longer-password"}
        ).json()["csrf"]
        assert (
            client.post(
                "/api/v1/projects/alpha/repository-connection",
                json=body,
                headers={"X-CSRF-Token": csrf},
            ).status_code
            == 403
        )


@pytest.mark.parametrize("provider", ["gitea", "github", "gitlab"])
def test_saved_auth_binds_worker_and_readiness_without_executor_leak(
    tmp_path, provider, monkeypatch
):
    """@brief Saved credentials are actually used by production engine and readiness."""
    from adore import orchestrator as module
    from adore.config import load_config
    from adore.repository_auth import project_runner, save_connection

    profiles = project(tmp_path, provider)
    config = load_config(profiles.config_path("alpha"))
    directory = profiles.profile_dir("alpha")
    record = {
        "schema": 1,
        "project_id": profiles.load("alpha").project_id,
        "provider": provider,
        "repository": config.platform.repo,
        "login": config.platform.login,
        "server": "https://forge.example",
        "token": "PRIVATE",
        "account": "alice",
    }
    save_connection(directory, record)
    calls = []
    temporary = []

    def runner(argv, *, cwd=None, timeout=None, env=None):
        calls.append((list(argv), env))
        if argv[0] == "tea":
            path = Path(env["XDG_CONFIG_HOME"]) / "tea/config.yml"
            temporary.append(path)
            login = json.loads(path.read_text())["logins"][0]
            assert login["token"] == "PRIVATE" and login["url"] == "https://forge.example"
        elif argv[0] == "gh":
            assert env["GH_ENTERPRISE_TOKEN"] == "PRIVATE" and env["GH_HOST"] == "forge.example"
        elif argv[0] == "glab":
            assert (
                env["GITLAB_TOKEN"] == "PRIVATE" and env["GITLAB_HOST"] == "https://forge.example"
            )
        else:
            assert not env or "PRIVATE" not in env.values()
        return CommandResult(
            argv=list(argv),
            exit_code=0,
            stdout='{"login":"alice"}' if argv[:2] == ["tea", "api"] else "PRIVATE",
            stderr="HTTP/1.1 200 OK" if argv[:2] == ["tea", "api"] else "PRIVATE",
        )

    monkeypatch.setattr(
        module,
        "project_runner",
        lambda directory, config: project_runner(directory, config, runner),
    )
    engine = module.Orchestrator.from_config(config, env_file=directory / ".env")
    assert "PRIVATE" not in engine.secrets.values()
    scoped = engine.forge.runner
    result = scoped([{"gitea": "tea", "github": "gh", "gitlab": "glab"}[provider], "whoami"])
    assert result.stdout == "[REDACTED]" and result.stderr == "[REDACTED]"
    scoped(["git", "status"])
    assert all(not path.exists() for path in temporary)
    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        result = client.post(
            "/api/v1/projects/alpha/readiness-check", headers={"X-CSRF-Token": csrf}
        )
        assert result.status_code == 200, result.text
        assert result.json()["checks"]["forge_auth"] is True
        assert "PRIVATE" not in result.text
    assert any(argv[0] in {"gh", "glab", "tea"} for argv, env in calls)


@pytest.mark.parametrize("corruption", ["json", "scope", "identity", "unknown", "duplicate"])
def test_corrupt_scoped_credentials_never_fall_back(tmp_path, corruption):
    """@brief Malformed or drifted secret records block readiness before any CLI."""
    from adore.config import load_config
    from adore.repository_auth import save_connection

    profiles = project(tmp_path)
    directory = profiles.profile_dir("alpha")
    config = load_config(profiles.config_path("alpha"))
    value = {
        "schema": 1,
        "project_id": profiles.load("alpha").project_id,
        "provider": "gitlab",
        "repository": config.platform.repo,
        "login": "",
        "server": "https://forge.example",
        "token": "PRIVATE",
        "account": "alice",
    }
    save_connection(directory, value)
    path = directory / "repository-auth.json"
    if corruption == "scope":
        value["repository"] = "other/repo"
    if corruption == "identity":
        value["project_id"] = "f" * 32
    if corruption == "unknown":
        value["extra"] = True
    path.write_text("broken" if corruption == "json" else json.dumps(value), encoding="utf-8")
    if corruption == "duplicate":
        path.write_text(path.read_text()[:-1] + ',"token":"OTHER"}', encoding="utf-8")

    def runner(*args, **kwargs):
        raise AssertionError("fallback command")

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        response = client.post(
            "/api/v1/projects/alpha/readiness-check", headers={"X-CSRF-Token": csrf}
        )
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "repository_credentials_corrupt"
        assert "PRIVATE" not in response.text


def test_secret_storage_failure_preserves_old_record_and_redacts_audit(tmp_path, monkeypatch):
    """@brief Atomic replacement failure leaves old bytes and no request secret in audit."""
    from adore import repository_auth as auth
    from adore.config import load_config

    profiles = project(tmp_path)
    directory = profiles.profile_dir("alpha")
    config = load_config(profiles.config_path("alpha"))
    record = {
        "schema": 1,
        "project_id": profiles.load("alpha").project_id,
        "provider": "gitlab",
        "repository": config.platform.repo,
        "login": "",
        "server": "https://forge.example",
        "token": "OLD-PRIVATE",
        "account": "alice",
    }
    auth.save_connection(directory, record)
    before = (directory / "repository-auth.json").read_bytes()
    real_replace = auth.os.replace

    def fail_auth_replace(src, dest):
        if Path(dest).name == "repository-auth.json":
            raise OSError("PRIVATE storage failure")
        real_replace(src, dest)

    monkeypatch.setattr(auth.os, "replace", fail_auth_replace)

    def runner(argv, **kwargs):
        data = (
            {"username": "alice"}
            if argv[-1] == "user"
            else {"path_with_namespace": config.platform.repo}
        )
        return CommandResult(argv=list(argv), exit_code=0, stdout=json.dumps(data))

    app = create_app(profiles.home, probe_runner=runner)
    with TestClient(app) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        response = client.post(
            "/api/v1/projects/alpha/repository-connection",
            headers={"X-CSRF-Token": csrf},
            json={"server": "https://forge.example", "token": "NEW-PRIVATE"},
        )
        assert response.status_code == 503
        assert "PRIVATE" not in response.text
        assert (directory / "repository-auth.json").read_bytes() == before
        assert not list(directory.glob(".auth-*"))
        assert "PRIVATE" not in json.dumps(client.get("/api/v1/audit").json())


def test_config_drift_during_login_refuses_save(tmp_path):
    """@brief A changed config snapshot cannot acquire old verification credentials."""
    profiles = project(tmp_path)
    path = profiles.config_path("alpha")

    def runner(argv, **kwargs):
        path.write_text(path.read_text() + "\n# external change\n", encoding="utf-8")
        data = (
            {"username": "alice"}
            if argv[-1] == "user"
            else {"path_with_namespace": "mygroup/myproject"}
        )
        return CommandResult(argv=list(argv), exit_code=0, stdout=json.dumps(data))

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        response = client.post(
            "/api/v1/projects/alpha/repository-connection",
            headers={"X-CSRF-Token": csrf},
            json={"server": "https://forge.example", "token": "PRIVATE"},
        )
        assert response.status_code == 409
        assert not (profiles.profile_dir("alpha") / "repository-auth.json").exists()


def test_http_requires_acknowledgement_and_keeps_other_projects_unchanged(tmp_path):
    """@brief Local HTTP Gitea is explicit and does not alter another project or exports."""
    profiles = project(tmp_path, "gitea")
    profiles.create("beta")
    beta_before = (profiles.profile_dir("beta") / "profile.json").read_bytes()
    directory = profiles.profile_dir("alpha")
    (directory / "readiness.json").write_text("old-check", encoding="utf-8")

    def runner(argv, **kwargs):
        data = {"login": "alice"} if argv[-1] == "user" else {"full_name": "mygroup/myproject"}
        return CommandResult(
            argv=list(argv), exit_code=0, stdout=json.dumps(data), stderr="HTTP/1.1 200 OK"
        )

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        response = client.post(
            "/api/v1/projects/alpha/repository-connection",
            headers={"X-CSRF-Token": csrf},
            json={"server": "http://192.168.1.15:3001", "token": "PRIVATE", "allow_http": True},
        )
        assert response.status_code == 503, response.text
        assert (directory / "readiness.json").read_text(encoding="utf-8") == "old-check"
        (
            directory / "readiness.json"
        ).unlink()  # Operator removes invalid evidence in this fixture.
        response = client.post(
            "/api/v1/projects/alpha/repository-connection",
            headers={"X-CSRF-Token": csrf},
            json={"server": "http://192.168.1.15:3001", "token": "PRIVATE", "allow_http": True},
        )
        assert response.status_code == 200, response.text
        assert (profiles.profile_dir("beta") / "profile.json").read_bytes() == beta_before
        assert not (profiles.profile_dir("beta") / "repository-auth.json").exists()
        assert "PRIVATE" not in client.get("/api/v1/projects/alpha/config").text
        assert "PRIVATE" not in client.get("/api/v1/projects/alpha/config/portable-settings").text
        assert "PRIVATE" not in client.get("/api/v1/audit").text


@pytest.mark.parametrize(
    "payload,status,expected",
    [
        ('{"login":"alice"}', "HTTP/1.1 200 OK", True),
        ('{"login":"alice"}', "HTTP/1.1 401 Unauthorized", False),
        ("{}", "HTTP/1.1 200 OK", False),
        ("not-json", "HTTP/1.1 200 OK", False),
        ('{"login":"alice","login":"other"}', "HTTP/1.1 200 OK", False),
        ("", "Error: no available login\n", False),
        ("", "Error: login name 'home' does not exist\n", False),
    ],
)
def test_gitea_readiness_uses_supported_scoped_user_api(
    tmp_path, payload, status, expected, caplog
):
    """@brief Saved named tea login uses a supported API and rejects bad evidence."""
    from adore.config import load_config
    from adore.repository_auth import save_connection

    profiles = project(tmp_path, "gitea")
    path = profiles.config_path("alpha")
    raw = path.read_text(encoding="utf-8").replace('# login = "home"', 'login = "home"')
    path.write_text(raw, encoding="utf-8")
    config = load_config(path)
    save_connection(
        profiles.profile_dir("alpha"),
        {
            "schema": 1,
            "project_id": profiles.load("alpha").project_id,
            "provider": "gitea",
            "repository": config.platform.repo,
            "login": config.platform.login,
            "server": "https://forge.example",
            "token": "PRIVATE",
            "account": "alice",
        },
    )
    calls = []

    def runner(argv, *, cwd=None, timeout=None, env=None):
        """@brief Model tea whoami's unsupported flag and API response boundary."""
        calls.append(list(argv))
        if argv[:2] == ["tea", "whoami"]:
            return CommandResult(
                argv=list(argv), exit_code=1, stdout="", stderr="unsupported login flag"
            )
        if argv[:2] == ["tea", "api"]:
            assert "--login" in argv and argv[argv.index("--login") + 1] == (
                config.platform.login or "adore-project"
            )
            assert (
                json.loads((Path(env["XDG_CONFIG_HOME"]) / "tea/config.yml").read_text())["logins"][
                    0
                ]["token"]
                == "PRIVATE"
            )
            return CommandResult(argv=list(argv), exit_code=0, stdout=payload, stderr=status)
        return CommandResult(argv=list(argv), exit_code=0, stdout="", stderr="")

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        result = client.post(
            "/api/v1/projects/alpha/readiness-check", headers={"X-CSRF-Token": csrf}
        )
        assert result.status_code == 200
        assert result.json()["checks"]["forge_auth"] is expected
        if not expected:
            assert "forge_auth_failure" in caplog.text
            assert "PRIVATE" not in caplog.text
            if payload:
                assert payload not in caplog.text
            if status.startswith("Error:"):
                expected_reason = (
                    "login-missing" if "login name" in status else "no-logins"
                )
                assert f"reason={expected_reason}" in caplog.text
                assert "local_config=" in caplog.text
                assert status.strip() not in caplog.text
        assert any(a[:2] == ["tea", "api"] for a in calls)
