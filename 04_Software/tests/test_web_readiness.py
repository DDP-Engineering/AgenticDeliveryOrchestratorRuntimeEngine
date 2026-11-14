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
@file test_web_readiness.py
@brief Administrator host-readiness probe contract tests.
@details External command output is faked and never returned to the browser.
"""

import importlib
import json
from pathlib import Path

from adore.profiles import ProfileStore
from adore.util import CommandResult
from adore.web.app import create_app
import pytest

from tests.configuration_client import TestClient


def _project(tmp_path):
    """@brief Register one valid but deliberately unprovisioned project."""
    profiles = ProfileStore(tmp_path / "home")
    root = tmp_path / "state"
    profiles.create("alpha", store_root=str(root))
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    path.write_bytes(example.read_bytes().replace(
        b'store_root = ".adore"',
        f'store_root = "{root.as_posix()}"'.encode(),
    ))
    return profiles, path


@pytest.mark.parametrize("change", ["roundtrip", "old-field", "status",
                                     "extra", "context", "duplicate"])
def test_readiness_persistence_is_closed(tmp_path, monkeypatch, change):
    """@brief Current readiness roundtrips; stale and corrupt records fail closed."""
    module = importlib.import_module("adore.web.app")
    profiles, _ = _project(tmp_path)
    evidence = {"workflow": "aegis", "checks": {"git": True, "forge_cli": True, "forge_auth": True,
                "container_runtime": True, "executor_cli": False,
                "egress_proxy": True}}
    monkeypatch.setattr(module, "_probe_setup", lambda *a, **kw: evidence)
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post("/api/v1/session", json={"username": "admin", "password": "admin"}
                           ).json()["csrf"]
        response = client.post("/api/v1/projects/alpha/readiness-check",
                               headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        path = profiles.profile_dir("alpha") / "readiness.json"
        saved = json.loads(path.read_text(encoding="utf-8"))
        if change == "old-field":
            saved["executor_probe"] = {"ready": False}
        elif change == "status":
            saved["checks"]["executor_cli"] = "PRIVATE-OUTPUT"
        elif change == "extra":
            saved["extra"] = "PRIVATE-OUTPUT"
        elif change == "context":
            saved["context"] = "PRIVATE-OUTPUT"
        text = json.dumps(saved)
        if change == "duplicate":
            text = text.replace(
                '"executor_cli": false', '"executor_cli": false, "executor_cli": true'
            )
        path.write_text(text, encoding="utf-8")
        loaded = client.get("/api/v1/projects/alpha")
        assert loaded.status_code == (200 if change == "roundtrip" else 503), loaded.text
        assert "PRIVATE" not in loaded.text


def test_old_readiness_schema_is_refused_with_deletion_guidance(tmp_path, monkeypatch):
    """@brief An old readiness record is never migrated or removed automatically."""
    module = importlib.import_module("adore.web.app")
    profiles, _ = _project(tmp_path)
    checks = dict.fromkeys(["git", "forge_cli", "forge_auth", "container_runtime",
                            "executor_cli", "egress_proxy"], True)
    monkeypatch.setattr(module, "_probe_setup", lambda *args, **kwargs:
                        {"workflow": "aegis", "checks": checks})
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        assert (
            client.post(
                "/api/v1/projects/alpha/readiness-check", headers={"X-CSRF-Token": csrf}
            ).status_code
            == 200
        )
        path = profiles.profile_dir("alpha") / "readiness.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["schema"] = 1
        old = json.dumps(record).encode()
        path.write_bytes(old)
        response = client.get("/api/v1/projects/alpha")
        assert response.status_code == 503 and "readiness.json" in response.text
        assert path.read_bytes() == old
        retry = client.post(
            "/api/v1/projects/alpha/readiness-check", headers={"X-CSRF-Token": csrf}
        )
        assert retry.status_code == 503 and path.read_bytes() == old


def test_external_auth_change_makes_readiness_stale(tmp_path, monkeypatch):
    """@brief A different effective forge environment cannot inherit prior evidence."""
    module = importlib.import_module("adore.web.app")
    profiles, _ = _project(tmp_path)
    checks = {
        "git": True,
        "forge_cli": True,
        "forge_auth": True,
        "container_runtime": True,
        "executor_cli": True,
        "egress_proxy": True,
    }
    monkeypatch.setattr(module, "_probe_setup", lambda *args, **kwargs:
                        {"workflow": "aegis", "checks": checks})
    monkeypatch.setenv("GITLAB_TOKEN", "fixture-one")
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        assert (
            client.post(
                "/api/v1/projects/alpha/readiness-check", headers={"X-CSRF-Token": csrf}
            ).json()["status"]
            == "partial"
        )
        monkeypatch.setenv("GITLAB_TOKEN", "fixture-two")
        result = client.get("/api/v1/projects/alpha").json()["verification"]
        assert result["status"] == "stale"
        assert "fixture" not in json.dumps(result)


def test_external_cli_config_change_makes_readiness_stale(tmp_path, monkeypatch):
    """@brief A changed external CLI config invalidates its earlier check."""
    module = importlib.import_module("adore.web.app")
    profiles, _ = _project(tmp_path)
    root = tmp_path / "cli"
    auth = root / "glab-cli" / "config.yml"
    auth.parent.mkdir(parents=True)
    auth.write_text("fixture-one", encoding="utf-8")
    for key in ("XDG_CONFIG_HOME", "LOCALAPPDATA", "APPDATA", "USERPROFILE"):
        monkeypatch.setenv(key, str(root))
    checks = dict.fromkeys(["git", "forge_cli", "forge_auth", "container_runtime",
                            "executor_cli", "egress_proxy"], True)
    monkeypatch.setattr(module, "_probe_setup", lambda *args, **kwargs:
                        {"workflow": "aegis", "checks": checks})
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        assert (
            client.post(
                "/api/v1/projects/alpha/readiness-check", headers={"X-CSRF-Token": csrf}
            ).json()["status"]
            == "partial"
        )
        auth.write_text("fixture-two", encoding="utf-8")
        response = client.get("/api/v1/projects/alpha")
        assert response.json()["verification"]["status"] == "stale"
        assert "fixture" not in response.text


def test_auth_changes_during_probe_do_not_publish(tmp_path, monkeypatch):
    """@brief A concurrent authentication change invalidates the entire check."""
    module = importlib.import_module("adore.web.app")
    profiles, _ = _project(tmp_path)
    checks = {
        "git": True,
        "forge_cli": True,
        "forge_auth": True,
        "container_runtime": True,
        "executor_cli": True,
        "egress_proxy": True,
    }
    monkeypatch.setenv("GITLAB_TOKEN", "before")

    def probe(*args, **kwargs):
        monkeypatch.setenv("GITLAB_TOKEN", "after")
        return {"workflow": "aegis", "checks": checks}

    monkeypatch.setattr(module, "_probe_setup", lambda *args, **kwargs:
                        {"workflow": "aegis", "checks": checks})
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        headers = {"X-CSRF-Token": csrf}
        assert (
            client.post("/api/v1/projects/alpha/readiness-check", headers=headers).status_code
            == 200
        )
        path = profiles.profile_dir("alpha") / "readiness.json"
        before = path.read_bytes()
        monkeypatch.setattr(module, "_probe_setup", probe)
        result = client.post("/api/v1/projects/alpha/readiness-check", headers=headers)
        assert result.status_code == 409
        assert path.read_bytes() == before


def test_unbound_cli_identity_stays_partial(tmp_path, monkeypatch):
    """@brief Unobservable external CLI identity cannot produce Verified."""
    module = importlib.import_module("adore.web.app")
    profiles, _ = _project(tmp_path)
    checks = {
        "git": True,
        "forge_cli": True,
        "forge_auth": True,
        "container_runtime": True,
        "executor_cli": True,
        "egress_proxy": True,
    }
    monkeypatch.setattr(module, "_probe_setup", lambda *args, **kwargs:
                        {"workflow": "aegis", "checks": checks})
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        result = client.post(
            "/api/v1/projects/alpha/readiness-check", headers={"X-CSRF-Token": csrf}
        )
        assert result.json()["status"] == "partial"
        assert client.get("/api/v1/projects/alpha").json()["verification"]["status"] == "partial"


def test_malformed_probe_cannot_replace_good_readiness(tmp_path, monkeypatch):
    """@brief Invalid probe values fail before overwriting existing evidence."""
    module = importlib.import_module("adore.web.app")
    profiles, _ = _project(tmp_path)
    checks = {
        "git": True,
        "forge_cli": True,
        "forge_auth": True,
        "container_runtime": True,
        "executor_cli": True,
        "egress_proxy": True,
    }
    monkeypatch.setattr(module, "_probe_setup", lambda *args, **kwargs:
                        {"workflow": "aegis", "checks": dict(checks)})
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        headers = {"X-CSRF-Token": csrf}
        assert (
            client.post("/api/v1/projects/alpha/readiness-check", headers=headers).status_code
            == 200
        )
        path = profiles.profile_dir("alpha") / "readiness.json"
        before = path.read_bytes()
        checks["git"] = "bad"
        assert (
            client.post("/api/v1/projects/alpha/readiness-check", headers=headers).status_code
            == 503
        )
        assert path.read_bytes() == before


def test_admin_can_probe_host_prerequisites_without_disclosing_cli_output(tmp_path):
    """@brief An explicit probe reports booleans and bounds every command."""
    profiles, _path = _project(tmp_path)
    calls = []

    def runner(argv, *, cwd=None, timeout=None, env=None):
        calls.append((list(argv), timeout))
        return CommandResult(
            argv=list(argv),
            exit_code=127 if argv[0] == "glab" else 0,
            stdout="secret-host-output",
            stderr="secret-auth-detail",
        )

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        response = client.post("/api/v1/projects/alpha/readiness-check",
                               headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        value = response.json()
        assert value["context"] == "api-host"
        assert value["checks"]["git"] is True
        assert value["checks"]["forge_cli"] is False
        assert value["checks"]["forge_auth"] is False
        assert value["workflow"] == "not-inspected"
        assert value["checks"]["executor_cli"] is True
        assert "model_endpoint" not in value["checks"] and "model_probe" not in value
        assert "secret" not in response.text
        assert calls and all(timeout <= 8 for _argv, timeout in calls)
        assert any("--pull=never" in argv and "--network" in argv
                   and "none" in argv for argv, _timeout in calls)


@pytest.mark.parametrize("outcome", ["ready", "stopped", "timeout", "invalid-exit"])
def test_readiness_uses_configured_wsl_runtime_info(tmp_path, outcome):
    """@brief Check the selected WSL daemon; an unavailable engine cannot launch Pi probes."""
    profiles, path = _project(tmp_path)
    path.write_text(path.read_text(encoding="utf-8").replace(
        'runtime = "docker"', 'runtime = "wsl -d Ubuntu -- docker"'), encoding="utf-8")
    prefix = ["wsl", "-d", "Ubuntu", "--exec", "docker"]
    calls = []

    def runner(argv, **kwargs):
        calls.append(list(argv))
        if argv == [*prefix, "info"]:
            return CommandResult(exit_code=1 if outcome == "stopped" else
                                 False if outcome == "invalid-exit" else 0,
                                 timed_out=outcome == "timeout", stderr="PRIVATE")
        return CommandResult(stdout="PRIVATE")

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        response = client.post("/api/v1/projects/alpha/readiness-check",
                               headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        assert response.json()["checks"]["container_runtime"] is (outcome == "ready")
        assert "PRIVATE" not in response.text
    assert [*prefix, "info"] in calls
    assert not any(call in (["docker", "--version"], ["podman", "--version"])
                   for call in calls)
    if outcome != "ready":
        assert not any("--entrypoint" in call for call in calls)


def test_host_executor_presence_does_not_hide_missing_image_tool(tmp_path):
    """@brief Readiness checks the actual executor image without a pull."""
    profiles, _path = _project(tmp_path)
    calls = []

    def runner(argv, *, cwd=None, timeout=None, env=None):
        calls.append(list(argv))
        return CommandResult(argv=list(argv),
                             exit_code=1 if "--entrypoint" in argv else 0,
                             stdout="", stderr="private runtime detail")

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        response = client.post("/api/v1/projects/alpha/readiness-check",
                               headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        assert response.json()["checks"]["executor_cli"] is False
        assert "private" not in response.text
        assert any("--entrypoint" in argv for argv in calls)
        assert any(argv[-1] == "pi" for argv in calls if "--entrypoint" in argv)


def test_readiness_probe_requires_admin_csrf_and_valid_config(tmp_path):
    """@brief Membership alone cannot launch a host probe; corrupt TOML fails."""
    profiles, path = _project(tmp_path)

    def runner(argv, *, cwd=None, timeout=None, env=None):
        raise AssertionError(f"unexpected probe: {argv}")

    app = create_app(profiles.home, probe_runner=runner)
    user = app.state.web_store.create_user("dev", "longer-password", "developer")
    app.state.web_store.set_memberships(user["id"], ["alpha"])
    with TestClient(app) as client:
        admin_csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        assert client.post("/api/v1/projects/alpha/readiness-check").status_code == 403
        assert client.post("/api/v1/projects/missing/readiness-check",
                           headers={"X-CSRF-Token": admin_csrf}).status_code == 404
        path.write_text("[broken", encoding="utf-8")
        corrupt = client.post("/api/v1/projects/alpha/readiness-check",
                              headers={"X-CSRF-Token": admin_csrf})
        assert corrupt.status_code == 503
        client.delete("/api/v1/session", headers={"X-CSRF-Token": admin_csrf})
        dev_csrf = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"}).json()["csrf"]
        assert client.post("/api/v1/projects/alpha/readiness-check",
                           headers={"X-CSRF-Token": dev_csrf}).status_code == 403


@pytest.mark.parametrize("backend", ["container", "local"])
@pytest.mark.parametrize("files,workflow", [([], "direct"), (["aegis.toml"], "direct"),
    (["aegis.py"], "aegis"), (["aegis.py", "aegis.toml"], "aegis")])
def test_workflow_is_read_only_file_information(tmp_path, monkeypatch, backend, files, workflow):
    """@brief Both backends inspect only aegis.py and leave clone bytes untouched."""
    import adore.local_execution as local_execution

    module = importlib.import_module("adore.web.app")
    profiles, path = _project(tmp_path)
    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True)
    for name in files:
        target = clone / ".agentic" / name
        target.parent.mkdir(exist_ok=True)
        target.write_text("raise RuntimeError('must not run')\n", encoding="utf-8")
    text = path.read_text(encoding="utf-8").replace('repo_path = "../project"',
                                                  f'repo_path = "{clone.as_posix()}"')
    if backend == "local":
        from tests.test_local_execution import local_fixture

        native = tmp_path / "native-fixture"
        native.mkdir()
        local_fixture(native, monkeypatch)
        text = text.replace('backend = "container"', 'backend = "local"')
        start = text.index("required_tool_checks = [")
        end = text.index("]", start) + 1
        text = text[:start] + "required_tool_checks = []" + text[end:]
        text += '\n[local]\naccount = "current"\n'
        monkeypatch.setattr(local_execution, "probe_local_executor", lambda *a, **kw:
                            {"ready": True, "reason": "ready", "exit_code": 0})
    path.write_text(text, encoding="utf-8")
    before = {str(p.relative_to(clone)): p.read_bytes() for p in clone.rglob("*") if p.is_file()}
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        assert not any("aegis" in str(arg) for arg in argv)
        return CommandResult(argv=argv, exit_code=0)

    with TestClient(module.create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post("/api/v1/session", json={"username": "admin", "password": "admin"}
                           ).json()["csrf"]
        result = client.post("/api/v1/projects/alpha/readiness-check",
                             headers={"X-CSRF-Token": csrf})
        assert result.status_code == 200, result.text
        evidence = result.json()
        assert evidence["workflow"] == workflow
        assert "aegis_files" not in evidence["checks"]
        assert "aegis_files" not in evidence["required_checks"]
        saved = json.loads((profiles.profile_dir("alpha") / "readiness.json").read_text())
        assert saved["schema"] == 3 and saved["workflow"] == workflow
        project = client.get("/api/v1/projects").json()[0]
        assert project["verification"]["workflow"] == workflow
        assert "aegis_files" not in project["verification_requirements"]
    assert calls
    assert before == {str(p.relative_to(clone)): p.read_bytes()
                      for p in clone.rglob("*") if p.is_file()}


@pytest.mark.parametrize("workflow", ["aegis", "direct", "not-inspected"])
@pytest.mark.parametrize("condition,status", [("passed", "verified"), ("failed", "failed"),
    ("runtime-unknown", "partial"), ("auth-unbound", "partial")])
def test_workflow_never_changes_prerequisite_verdict(tmp_path, monkeypatch, workflow,
                                                    condition, status):
    """@brief The descriptive enum cannot pass, fail or complete host prerequisites."""
    module = importlib.import_module("adore.web.app")
    profiles, _path = _project(tmp_path)
    checks = dict.fromkeys(["git", "forge_cli", "forge_auth", "container_runtime",
                            "executor_cli", "egress_proxy"], True)
    if condition == "failed":
        checks["git"] = False
    if condition == "runtime-unknown":
        checks["container_runtime"] = None
    monkeypatch.setattr(module, "_readiness_auth_bound", lambda *a: condition != "auth-unbound")
    monkeypatch.setattr(module, "_probe_setup", lambda *a, **kw:
                        {"workflow": workflow, "checks": checks})
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post("/api/v1/session", json={"username": "admin", "password": "admin"}
                           ).json()["csrf"]
        result = client.post("/api/v1/projects/alpha/readiness-check",
                             headers={"X-CSRF-Token": csrf})
        assert result.status_code == 200, result.text
        assert result.json()["status"] == status
        assert result.json()["workflow"] == workflow
        assert client.get("/api/v1/projects/alpha").json()["verification"]["status"] == status


@pytest.mark.parametrize("bad", ["missing", "unknown", None, True, 1, [], {}])
def test_invalid_workflow_probe_preserves_saved_evidence(tmp_path, monkeypatch, bad):
    """@brief Missing/invalid workflow fails typed before overwriting previous evidence."""
    module = importlib.import_module("adore.web.app")
    profiles, _path = _project(tmp_path)
    evidence = {"workflow": "direct", "checks": dict.fromkeys(
        ["git", "forge_cli", "forge_auth", "container_runtime", "executor_cli", "egress_proxy"],
        True)}
    monkeypatch.setattr(module, "_probe_setup", lambda *a, **kw: evidence)
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post("/api/v1/session", json={"username": "admin", "password": "admin"}
                           ).json()["csrf"]
        headers = {"X-CSRF-Token": csrf}
        result = client.post("/api/v1/projects/alpha/readiness-check", headers=headers)
        assert result.status_code == 200, result.text
        path = profiles.profile_dir("alpha") / "readiness.json"
        before = path.read_bytes()
        if bad == "missing":
            evidence.pop("workflow")
        else:
            evidence["workflow"] = bad
        result = client.post("/api/v1/projects/alpha/readiness-check", headers=headers)
        assert result.status_code == 503, result.text
        assert result.json()["detail"]["code"] == "readiness_probe_failed"
        assert path.read_bytes() == before


@pytest.mark.parametrize("bad", ["missing", "unknown", None, True, 1, [], {}, "old-schema"])
@pytest.mark.parametrize("stale", [False, True])
def test_corrupt_workflow_is_refused_even_if_stale(tmp_path, monkeypatch, bad, stale):
    """@brief Invalid saved workflow/schema is never repaired, including stale records."""
    module = importlib.import_module("adore.web.app")
    profiles, config_path = _project(tmp_path)
    evidence = {"workflow": "direct", "checks": dict.fromkeys(
        ["git", "forge_cli", "forge_auth", "container_runtime", "executor_cli", "egress_proxy"],
        True)}
    monkeypatch.setattr(module, "_probe_setup", lambda *a, **kw: evidence)
    with TestClient(module.create_app(profiles.home)) as client:
        csrf = client.post("/api/v1/session", json={"username": "admin", "password": "admin"}
                           ).json()["csrf"]
        headers = {"X-CSRF-Token": csrf}
        result = client.post("/api/v1/projects/alpha/readiness-check", headers=headers)
        assert result.status_code == 200, result.text
        path = profiles.profile_dir("alpha") / "readiness.json"
        record = json.loads(path.read_text())
        if bad == "missing":
            record.pop("workflow")
        elif bad == "old-schema":
            record["schema"] = 2
        else:
            record["workflow"] = bad
        path.write_text(json.dumps(record))
        before = path.read_bytes()
        if stale:
            config_path.write_bytes(config_path.read_bytes() + b"\n# changed\n")
        for result in (client.get("/api/v1/projects/alpha"), client.get("/api/v1/projects"),
                       client.post("/api/v1/projects/alpha/readiness-check", headers=headers)):
            assert result.status_code == 503, result.text
            assert "readiness_corrupt" in result.text and "readiness.json" in result.text
        assert path.read_bytes() == before


# END OF FILE
