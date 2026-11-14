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
@file    test_web_enrollment.py
@brief   Stable identity and safe enrollment public contract tests.
@details External runners are faked; barriers observe publication and rollback.
"""

# IMPORTS
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
from threading import Event

from adore.config import load_config
from adore.profiles import ProfileError, ProfileStore
from adore.state import RunState, StateStore
from adore.util import CommandResult
from adore.web.app import create_app
from adore.web.commands import CommandWorker
from adore.web.store import WebStoreError
import pytest

from tests.configuration_client import TestClient


# LOCAL HELPERS
@pytest.fixture(autouse=True)
def offline_wizard(monkeypatch):
    """@brief Fake every legacy wizard CLI even while tests demonstrate red behavior."""
    import adore.web.app as web_app
    from adore.wizard import run_wizard

    def wrapped(*args, **kwargs):
        return run_wizard(*args, **kwargs, runner=lambda argv, **options:
                          CommandResult(argv=argv, exit_code=127))

    monkeypatch.setattr(web_app, "run_wizard", wrapped)


def _body(tmp_path, **changes):
    """@brief Valid explicit setup with a local fixture clone."""
    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True, exist_ok=True)
    return {"name": "alpha", "display_name": "Alpha service", "kind": "gitea",
            "repo": "owner/alpha", "login": "ddp", "repo_path": str(clone),
            "reviewers": "reviewer", "auth_mode": "api-key", "image": "adore-test:latest",
            "provider": "openai", "model": "gpt-5.5", **changes}


def _login(client, username="admin", password="admin"):
    """@brief Return the authenticated account's CSRF header."""
    result = client.post("/api/v1/session", json={"username": username, "password": password})
    assert result.status_code == 200, result.text
    return {"X-CSRF-Token": result.json()["csrf"]}


def _no_probe(argv, **kwargs):
    """@brief Fail if preview, create or read launches an external command."""
    raise AssertionError(f"Unexpected external probe: {argv}")


def _create(tmp_path):
    """@brief Enroll one valid project and return the app and profile."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        result = client.post("/api/v1/projects", json=_body(tmp_path), headers=_login(client))
        assert result.status_code == 200, result.text
    return app, app.state.profiles.load("alpha")


def _import_body(tmp_path):
    """@brief Preserve a valid sample document with absolute external paths."""
    text = (Path(__file__).resolve().parents[1] / "config.example.toml").read_text(
        encoding="utf-8")
    changes = {".adore": tmp_path / "state", "../project": tmp_path / "clone",
               "worktrees": tmp_path / "trees", ".adore/metrics.db": tmp_path / "state/metrics.db",
               ".adore/metrics/runs.jsonl": tmp_path / "state/metrics/runs.jsonl",
               ".adore/metrics/stats.html": tmp_path / "state/metrics/stats.html"}
    for old, value in changes.items():
        text = text.replace('"' + old + '"', '"' + value.as_posix() + '"')
    return {"name": "imported", "display_name": "Imported service", "config_text": text}


# PUBLIC API / TESTS
def test_guided_candidate_review_binds_complete_setup_without_probes(tmp_path, monkeypatch):
    """@brief Explicit setup produces canonical paths, rules and revision offline."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    body = _body(tmp_path, ready_label="human-ready", max_iterations=7,
                 max_wall_clock_seconds=600, max_cost_usd=2.5, max_files_touched=20,
                 env_keys=["LOCAL_API_KEY"])
    with TestClient(app) as client:
        headers = _login(client)
        response = client.post("/api/v1/projects/setup-preview", json=body, headers=headers)
        assert response.status_code == 200, response.text
        preview = response.json()
        assert preview["structural_valid"], preview
        assert len(preview["revision"]) == 64
        assert preview["review"]["env_keys"] == ["LOCAL_API_KEY"]
        assert preview["review"]["ready_label"] == "human-ready"
        assert preview["review"]["max_iterations"] == 7
        assert Path(preview["review"]["config_path"]).is_absolute()
        assert not app.state.profiles.profile_dir("alpha").exists()
        monkeypatch.setattr(app.state.profiles, "_now", lambda: "2099-01-01T00:00:00Z")
        changed = client.post("/api/v1/projects/setup-create", json={
            **body, "display_name": "Changed label", "revision": preview["revision"]},
            headers=headers)
        assert changed.status_code == 409, changed.text
        created = client.post("/api/v1/projects/setup-create", json={
            **body, "revision": preview["revision"]}, headers=headers)
        assert created.status_code == 200, created.text
        assert created.json()["pickup_state"] == "stopped"
        assert created.json()["verification"]["status"] == "unverified"
        assert sha256(app.state.profiles.config_path("alpha").read_bytes()).hexdigest() == (
            preview["config_revision"])
        config = load_config(app.state.profiles.config_path("alpha"))
        assert config.executor.env_keys == ["LOCAL_API_KEY"]
        assert config.budgets.max_iterations == 7
        assert config.labels.lifecycle.ready == "human-ready"
        assert client.post("/api/v1/projects/setup-create", json={
            **body, "revision": preview["revision"]}, headers=headers).status_code == 409


def test_draft_verification_is_explicit_ephemeral_and_revision_bound(tmp_path):
    """@brief Draft probe returns honest failed checks; stale draft never probes."""
    calls = []

    def fake(argv, **_kwargs):
        calls.append(argv)
        return CommandResult(argv=argv, exit_code=127)

    app = create_app(tmp_path / "home", probe_runner=fake)
    body = _body(tmp_path)
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers)
        assert preview.status_code == 200
        assert calls == []
        revision = preview.json()["revision"]
        stale = client.post("/api/v1/projects/setup-check", json={
            **body, "revision": "0" * 64}, headers=headers)
        assert stale.status_code == 409 and calls == []
        result = client.post("/api/v1/projects/setup-check", json={
            **body, "revision": revision}, headers=headers)
        assert result.status_code == 200, result.text
        assert result.json()["status"] == "failed"
        assert result.json()["draft_revision"] == revision
        assert result.json()["revision"] == preview.json()["config_revision"]
        assert result.json()["checked_at"] and calls
        assert not app.state.profiles.profile_dir("alpha").exists()
        assert not list((tmp_path / "home").glob("**/readiness.json"))


def test_guided_setup_accepts_supported_thinking_and_rejects_unsupported(tmp_path):
    """@brief Review and creation preserve valid Pi effort and reject invalid levels."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    body = _body(tmp_path, model="gpt-5", thinking="medium")
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        assert preview["structural_valid"], preview
        assert preview["review"]["thinking"] == "medium"
        invalid = client.post(
            "/api/v1/projects/setup-preview", json={**body, "model": "gpt-4"}, headers=headers
        ).json()
        assert not invalid["structural_valid"]
        created = client.post(
            "/api/v1/projects/setup-create",
            json={**body, "revision": preview["revision"]},
            headers=headers,
        )
        assert created.status_code == 200, created.text
        assert load_config(app.state.profiles.config_path("alpha")).executor.thinking == "medium"


def test_checked_enrollment_transfers_only_server_evidence(tmp_path):
    """@brief Server evidence binds creation; forged evidence is refused."""

    def fake(argv, **kwargs):
        return CommandResult(argv=argv, exit_code=127)

    app = create_app(tmp_path / "home", probe_runner=fake)
    body = _body(tmp_path)
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        reviewed = {**body, "revision": preview["revision"]}
        checked = client.post("/api/v1/projects/setup-check", json=reviewed, headers=headers).json()
        bad = client.post(
            "/api/v1/projects/setup-create",
            json={**reviewed, "evidence_token": "0" * 64},
            headers=headers,
        )
        assert bad.status_code == 409
        created = client.post(
            "/api/v1/projects/setup-create",
            json={**reviewed, "evidence_token": checked["evidence_token"]},
            headers=headers,
        )
        assert created.status_code == 200, created.text
        assert created.json()["verification"]["status"] == checked["status"] == "failed"
        assert created.json()["verification"]["checks"] == checked["checks"]


def test_partial_enrollment_evidence_remains_partial_and_goes_stale(tmp_path, monkeypatch):
    """@brief Unchecked repository evidence is neither promoted nor retained after edits."""
    import adore.web.app as web_app

    checks = {
        "git": True,
        "forge_cli": True,
        "forge_auth": True,
        "container_runtime": True,
        "executor_cli": True,
        "egress_proxy": True,
    }
    monkeypatch.setattr(web_app, "_probe_setup", lambda *_args, **_kwargs:
                        {"workflow": "not-inspected", "checks": dict(checks)})
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    body = _body(tmp_path)
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        reviewed = {**body, "revision": preview["revision"]}
        checked = client.post("/api/v1/projects/setup-check", json=reviewed, headers=headers).json()
        assert checked["status"] == "partial" and checked["workflow"] == "not-inspected"
        changed = client.post(
            "/api/v1/projects/setup-create",
            json={**reviewed, "display_name": "Other", "evidence_token": checked["evidence_token"]},
            headers=headers,
        )
        assert changed.status_code == 409
        created = client.post(
            "/api/v1/projects/setup-create",
            json={**reviewed, "evidence_token": checked["evidence_token"]},
            headers=headers,
        )
        assert created.status_code == 200, created.text
        assert created.json()["verification"]["status"] == "partial"
        assert created.json()["verification"]["workflow"] == "not-inspected"
        path = app.state.profiles.config_path("alpha")
        path.write_text(path.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
        result = client.get("/api/v1/projects").json()[0]
        assert result["verification"]["status"] == "stale"


def test_expired_enrollment_check_is_rejected(tmp_path, monkeypatch):
    """@brief A server check token cannot outlive its bounded in-memory lifetime."""
    import adore.web.app as web_app

    tick = [100.0]
    checks = {
        "git": True,
        "forge_cli": True,
        "forge_auth": True,
        "container_runtime": True,
        "executor_cli": True,
        "egress_proxy": True,
    }
    monkeypatch.setattr(web_app, "monotonic", lambda: tick[0])
    monkeypatch.setattr(web_app, "_probe_setup", lambda *_args, **_kwargs:
                        {"workflow": "aegis", "checks": dict(checks)})
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    body = _body(tmp_path)
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        reviewed = {**body, "revision": preview["revision"]}
        checked = client.post("/api/v1/projects/setup-check", json=reviewed, headers=headers).json()
        tick[0] += 901
        response = client.post(
            "/api/v1/projects/setup-create",
            json={**reviewed, "evidence_token": checked["evidence_token"]},
            headers=headers,
        )
        assert response.status_code == 409
        assert not app.state.profiles.profile_dir("alpha").exists()


def test_readiness_is_host_bound_and_requires_applicable_checks(tmp_path, monkeypatch):
    """@brief Evidence is stale on another host; missing configured checks fail closed."""
    import adore.local_process as local_process
    import adore.web.app as web_app

    checks = {
        "git": True,
        "forge_cli": True,
        "forge_auth": True,
        "container_runtime": True,
        "executor_cli": True,
        "egress_proxy": True,
    }
    monkeypatch.setattr(web_app, "_probe_setup", lambda *_args, **_kwargs:
                        {"workflow": "aegis", "checks": dict(checks)})
    host = ["a" * 64]
    monkeypatch.setattr(local_process, "native_context", lambda: {"host": host[0]})
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    body = _body(tmp_path)
    with TestClient(app) as client:
        headers = _login(client)
        created = client.post("/api/v1/projects", json=body, headers=headers)
        assert created.status_code == 200, created.text
        result = client.post("/api/v1/projects/alpha/readiness-check", json={}, headers=headers)
        assert result.json()["status"] == "partial", result.text
        host[0] = "b" * 64
        assert client.get("/api/v1/projects/alpha").json()["verification"]["status"] == "stale"
        host[0] = "a" * 64
        path = app.state.profiles.profile_dir("alpha") / "readiness.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        del record["checks"]["egress_proxy"]
        path.write_text(json.dumps(record), encoding="utf-8")
        assert client.get("/api/v1/projects/alpha").status_code == 503


@pytest.mark.parametrize("kind", ["executor_sign_in", "web_search_key"])
def test_configured_optional_readiness_check_cannot_be_omitted(tmp_path, monkeypatch, kind):
    """@brief Evidence cannot claim verification without configuration-required checks."""
    import adore.web.app as web_app

    body = _body(
        tmp_path,
        **({"provider": "chatgpt", "model": "gpt-5.6-luna"} if kind == "executor_sign_in" else {}),
    )
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers = _login(client)
        response = client.post("/api/v1/projects", json=body, headers=headers)
        assert response.status_code == 200, response.text
        path = app.state.profiles.config_path("alpha")
        if kind == "web_search_key":
            text = path.read_text(encoding="utf-8").replace(
                "[executor]\n", "[executor]\ninternet = true\n"
            )
            path.write_text(text + '\n[executor.web]\nsearch = "brave"\n', encoding="utf-8")
        checks = {
            "git": True,
            "forge_cli": True,
            "forge_auth": True,
            "container_runtime": True,
            "executor_cli": True,
        }
        if kind == "executor_sign_in":
            checks.update(executor_sign_in=True, egress_proxy=True)
        else:
            checks["web_search_key"] = True
        monkeypatch.setattr(web_app, "_probe_setup", lambda *a, **k:
                            {"workflow": "aegis", "checks": dict(checks)})
        checked = client.post("/api/v1/projects/alpha/readiness-check", headers=headers)
        assert checked.status_code == 200, checked.text
        stored = app.state.profiles.profile_dir("alpha") / "readiness.json"
        record = json.loads(stored.read_text(encoding="utf-8"))
        del record["checks"][kind]
        stored.write_text(json.dumps(record), encoding="utf-8")
        assert client.get("/api/v1/projects/alpha").status_code == 503


def test_chatgpt_draft_check_rejects_auth_drift(tmp_path, monkeypatch):
    """@brief A draft checked before subscription credentials change cannot transfer evidence."""
    import adore.web.app as web_app

    checks = {
        "git": True,
        "forge_cli": True,
        "forge_auth": True,
        "container_runtime": True,
        "executor_cli": True,
        "egress_proxy": True,
        "executor_sign_in": True,
    }
    monkeypatch.setattr(web_app, "_probe_setup", lambda *args, **kwargs:
                        {"workflow": "aegis", "checks": checks})
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    auth = app.state.profiles.home / "chatgpt" / "auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text("fixture-auth", encoding="utf-8")
    body = _body(tmp_path, provider="chatgpt", model="gpt-5.6-luna")
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        reviewed = {**body, "revision": preview["revision"]}
        checked = client.post("/api/v1/projects/setup-check", json=reviewed, headers=headers).json()
        auth.unlink()
        result = client.post(
            "/api/v1/projects/setup-create",
            headers=headers,
            json={**reviewed, "evidence_token": checked["evidence_token"]},
        )
        assert result.status_code == 409
        assert not app.state.profiles.profile_dir("alpha").exists()


def test_draft_probe_reports_verified_and_honors_selected_gitea_login(tmp_path):
    """@brief Successful host checks verify the prerequisites; no model check is claimed."""
    calls = []

    def fake(argv, **kwargs):
        calls.append(argv)
        assert 0 < kwargs["timeout"] <= 8
        if argv[:2] == ["tea", "api"]:
            return CommandResult(argv=argv, stdout='{"login":"fixture"}',
                                 stderr="HTTP/1.1 200 OK")
        return CommandResult(argv=argv, exit_code=0, stdout="fixture-1.0")

    body = _body(tmp_path)
    aegis = Path(body["repo_path"]) / ".agentic"
    aegis.mkdir()
    for name in ("aegis.py", "aegis.toml"):
        (aegis / name).touch()
    app = create_app(tmp_path / "home", probe_runner=fake)
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        result = client.post("/api/v1/projects/setup-check", json={
            **body, "revision": preview["revision"]}, headers=headers)
        assert result.status_code == 200, result.text
        assert result.json()["status"] == "partial"
        assert result.json()["checks"]["git"]
        assert "model_endpoint" not in result.json()["checks"]
        assert ["tea", "api", "-i", "--method", "GET", "--login", "ddp", "user"] in calls
        assert not app.state.profiles.profile_dir("alpha").exists()


@pytest.mark.parametrize("field,value", [("auth_mode", "host-auth"), ("executor_cli", "codex")])
def test_enrollment_refuses_host_sign_in_and_agent_choice(tmp_path, field, value):
    """@brief Pi is the only agent and host sign-in staging is gone: both fields are refused."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    body = {**_body(tmp_path), field: value}
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers)
        assert preview.status_code == 422, preview.text
        assert field in preview.text
    assert not app.state.profiles.profile_dir("alpha").exists()


@pytest.mark.parametrize("route", ["setup-preview", "setup-check", "setup-create"])
def test_guided_draft_routes_require_admin_csrf(tmp_path, route):
    """@brief Every draft boundary rejects Dev and missing mutation CSRF."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    app.state.web_store.create_user("dev", "test-password", "developer")
    with TestClient(app) as client:
        body = _body(tmp_path, revision="0" * 64) if route != "setup-preview" else _body(tmp_path)
        assert client.post(f"/api/v1/projects/{route}", json=body).status_code == 401
        headers = _login(client)
        assert client.post(f"/api/v1/projects/{route}", json=body).status_code == 403
        headers = _login(client, "dev", "test-password")
        response = client.post(f"/api/v1/projects/{route}", json=body, headers=headers)
        assert response.status_code == 403


@pytest.mark.parametrize("changes", [
    {"env_keys": ["literal-sensitive-value"]}, {"max_iterations": 0},
    {"max_cost_usd": -1}, {"repo_path": "/no-such-fixture-clone"},
    {"runtime": "untrusted-runtime"}, {"ready_label": ""},
])
def test_guided_invalid_explicit_fields_fail_closed(tmp_path, changes):
    """@brief Invalid setup rejects with no probes or runnable profile."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        result = client.post("/api/v1/projects/setup-preview", json=_body(tmp_path, **changes),
                             headers=_login(client))
        assert result.status_code in (200, 422)
        if result.status_code == 200:
            assert not result.json()["structural_valid"]
            assert result.json()["issues"]
        assert "literal-sensitive-value" not in result.text
    assert not app.state.profiles.profile_dir("alpha").exists()


def test_offline_preview_and_enrollment_publish_separate_states(tmp_path):
    """@brief Preview writes nothing; successful creation is already paused."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", json=_body(tmp_path),
                              headers=headers)
        assert preview.status_code == 200, preview.text
        value = preview.json()
        assert value["structural_valid"] and value["issues"] == []
        assert value["verification"]["status"] == "unverified"
        assert not app.state.profiles.profile_dir("alpha").exists()
        response = client.post("/api/v1/projects", json=_body(tmp_path), headers=headers)
        assert response.status_code == 200, response.text
        project = response.json()
        assert project["name"] == "alpha" and project["display_name"] == "Alpha service"
        assert len(project["id"]) == 32 and project["paused"]
        assert project["pickup_state"] == "stopped"
        assert project["validation"]["structural_valid"]
        assert project["verification"]["status"] == "unverified"
        assert load_config(app.state.profiles.config_path("alpha")).platform.login == "ddp"
        assert client.get(f'/api/v1/projects/{project["id"]}').json()["id"] == project["id"]


def test_display_edit_keeps_membership_operations_and_paths(tmp_path):
    """@brief Human identity changes preserve all operational ownership."""
    app, profile = _create(tmp_path)
    profiles, web = app.state.profiles, app.state.web_store
    before = profiles.load("alpha")
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    operation = web.enqueue(dev["id"], "alpha", "start", "42", "old-operation")
    config = profiles.config_path("alpha").read_bytes()
    StateStore(profile.store_root).save(RunState(run_id="active-job", ticket_iid=1))
    with TestClient(app) as client:
        headers = _login(client)
        result = client.put(f"/api/v1/projects/{before.project_id}/identity",
                            json={"display_name": "Serviciu α"}, headers=headers)
        assert result.status_code == 200, result.text
        after = profiles.load("alpha")
        assert after.project_id == before.project_id
        assert after.name == "alpha" and after.store_root == profile.store_root
        assert profiles.config_path("alpha").read_bytes() == config
        assert web.memberships(dev["id"]) == {"alpha"}
        assert web.operation(operation["id"])["project_id"] == before.project_id
        assert StateStore(after.store_root).load("active-job").lifecycle == "working"
        headers = _login(client, "dev", "longer-password")
        value = client.get(f"/api/v1/projects/{before.project_id}").json()
        assert value["display_name"] == "Serviciu α"
        assert client.put("/api/v1/projects/alpha/identity", json={"display_name": "Denied"},
                          headers=headers).status_code == 403


@pytest.mark.parametrize("value", ["", " ", " padded ", "x" * 121,
                                  "line\nbreak", "x\u202ey", 42, None])
def test_display_input_and_corrupt_metadata_fail_closed(tmp_path, value):
    """@brief Invalid display metadata is rejected rather than reset."""
    app, _profile = _create(tmp_path)
    with TestClient(app) as client:
        response = client.put("/api/v1/projects/alpha/identity", json={"display_name": value},
                              headers=_login(client))
        assert response.status_code in (400, 422)
        assert app.state.profiles.load("alpha").display_name == "Alpha service"
        meta = app.state.profiles.profile_dir("alpha") / "profile.json"
        data = json.loads(meta.read_text(encoding="utf-8"))
        data["display_name"] = value
        meta.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ProfileError):
            app.state.profiles.load("alpha")
        assert client.get("/api/v1/projects").status_code == 503


@pytest.mark.parametrize("name", ["../escape", "Upper", "con", "con.txt", "lpt1", "trail.",
                                  "setup-preview", "setup-check", "setup-create",
                                  "import", "a" * 32, "x" * 65])
def test_id_policy_rejects_malformed_reserved_and_ambiguous_ids(tmp_path, name):
    """@brief Portable IDs cannot address devices, paths or immutable-ID aliases."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers = _login(client)
        available = client.post("/api/v1/projects/id-availability", json={"name": name},
                                headers=headers)
        assert available.status_code == 400, available.text
        assert available.json()["detail"]["code"] in (
            "invalid_project_name", "reserved_project_name")
        result = client.post("/api/v1/projects", json=_body(tmp_path, name=name), headers=headers)
        assert result.status_code == 400
        assert app.state.profiles.list_profiles() == []


def test_id_availability_checks_incomplete_casefold_and_corrupt_profiles(tmp_path):
    """@brief Advisory availability rechecks all persisted trust boundaries."""
    app = create_app(tmp_path / "home")
    with TestClient(app) as client:
        headers = _login(client)
        route = "/api/v1/projects/id-availability"
        assert client.post(route, json={"name": "alpha"}, headers=headers).json()["available"]
        directory = app.state.profiles.profile_dir("Alpha")
        directory.mkdir(parents=True)
        assert not client.post(route, json={"name": "alpha"}, headers=headers).json()["available"]
        (directory / "profile.json").write_text("[]", encoding="utf-8")
        assert client.post(route, json={"name": "beta"}, headers=headers).status_code == 503


def test_publication_visibility_and_competing_api_instances(tmp_path, monkeypatch):
    """@brief Worker discovery sees no unpaused profile and a competing API loses."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    other = create_app(tmp_path / "home", probe_runner=_no_probe)
    entered, release = Event(), Event()
    original = ProfileStore.create
    observations = []

    def blocked_create(store, name, **kwargs):
        observations.append(ProfileStore(store.home).list_profiles())
        assert StateStore(kwargs["store_root"]).is_paused()
        entered.set()
        assert release.wait(10)
        result = original(store, name, **kwargs)
        assert ProfileStore(store.home).load(name).project_id == result.project_id
        seen = []
        worker = CommandWorker(ProfileStore(store.home), app.state.web_store,
                               runner=lambda argv, env: seen.append(argv) or 0)
        worker.poll_project(name)
        assert seen  # CLI receives a profile whose state is already paused.
        assert StateStore(kwargs["store_root"]).is_paused()
        return result

    monkeypatch.setattr(ProfileStore, "create", blocked_create)
    body = _body(tmp_path)
    with TestClient(app) as one, TestClient(other) as two, ThreadPoolExecutor(1) as pool:
        headers, other_headers = _login(one), _login(two)
        future = pool.submit(one.post, "/api/v1/projects", json=body, headers=headers)
        try:
            assert entered.wait(10)
            conflict = two.post("/api/v1/projects", json=body, headers=other_headers)
            assert conflict.status_code == 409, conflict.text
        finally:
            release.set()
        assert future.result(timeout=10).status_code == 200
    assert observations == [[]]
    assert len(app.state.profiles.list_profiles()) == 1


@pytest.mark.parametrize("failure", ["pause", "metadata", "audit", "config"])
def test_failed_creation_rolls_back_and_preserves_running_projects(tmp_path, monkeypatch, failure):
    """@brief Failed publication cannot leave a runnable orphan or change another project."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    existing = app.state.profiles.create("running", store_root=str(tmp_path / "running-state"))
    StateStore(existing.store_root).save(RunState(run_id="job", ticket_iid=9))
    original_create, original_audit = ProfileStore.create, app.state.web_store.audit
    with TestClient(app) as client:
        headers = _login(client)

        def broken_create(*args, **kwargs):
            original_create(*args, **kwargs)
            raise OSError("private storage failure")

        def broken_audit(actor, action, *args, **kwargs):
            if action == "project-created":
                raise WebStoreError("private audit failure")
            return original_audit(actor, action, *args, **kwargs)

        if failure == "pause":
            def broken_pause(self):
                raise OSError("private")

            monkeypatch.setattr(StateStore, "pause", broken_pause)
        elif failure == "metadata":
            monkeypatch.setattr(ProfileStore, "create", broken_create)
        elif failure == "config":
            original_write = Path.write_bytes

            def broken_write(path, data):
                if path == app.state.profiles.config_path("alpha"):
                    raise OSError("private config failure")
                return original_write(path, data)

            monkeypatch.setattr(Path, "write_bytes", broken_write)
        else:
            monkeypatch.setattr(app.state.web_store, "audit", broken_audit)
        result = client.post("/api/v1/projects", json=_body(tmp_path), headers=headers)
        assert result.status_code == 503, result.text
        assert "private" not in result.text
    assert not app.state.profiles.profile_dir("alpha").exists()
    assert not StateStore(existing.store_root).is_paused()
    assert StateStore(existing.store_root).load("job").lifecycle == "working"


def test_readiness_storage_failure_is_typed_and_redacted(tmp_path, monkeypatch):
    """@brief An evidence write failure has a stable safe public finding."""
    app, _item = _create(tmp_path)
    import adore.web.app as web_app

    def broken(*args, **kwargs):
        raise OSError("private storage failure")

    monkeypatch.setattr(web_app, "_write_pending_config", broken)
    app = create_app(tmp_path / "home", probe_runner=lambda argv, **kwargs:
                     CommandResult(argv=argv, exit_code=127))
    with TestClient(app) as client:
        response = client.post("/api/v1/projects/alpha/readiness-check", headers=_login(client))
    assert response.status_code == 503
    assert response.json()["detail"]["issues"][0]["code"] == "readiness_store_failed"
    assert "private" not in response.text


@pytest.mark.parametrize("document", ['[agent]\nname = 123\n',
                                      '[platform]\nrepo = []\n',
                                      '[state]\nstore_root = 7\n'])
def test_malformed_import_field_types_return_structured_findings(tmp_path, document):
    """@brief Human TOML types fail closed through the public preview boundary."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        response = client.post("/api/v1/projects/import-preview", json={
            "name": "bad", "config_text": document}, headers=_login(client))
    assert response.status_code == 200
    assert response.json()["validation"]["structural_valid"] is False
    assert response.json()["validation"]["issues"]


def test_structured_setup_findings_and_direct_unauthorized_requests(tmp_path):
    """@brief Bad setup is actionable; Dev cannot reach mutations through the API."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    app.state.web_store.create_user("dev", "longer-password", "developer")
    with TestClient(app) as client:
        body = _body(tmp_path, kind="invalid")
        assert client.post("/api/v1/projects/setup-preview", json=body).status_code == 401
        headers = _login(client)
        result = client.post("/api/v1/projects/setup-preview", json=body, headers=headers)
        assert result.status_code == 200, result.text
        assert not result.json()["structural_valid"]
        issue = result.json()["issues"][0]
        assert issue["code"] == "setup_field_invalid" and issue["field"] == "kind"
        assert issue["remediation"] and "invalid" not in issue["remediation"]
        assert client.post("/api/v1/projects", json=body, headers=headers).status_code == 400
        for route, payload in (("", body), ("/setup-preview", body),
                               ("/id-availability", {"name": "beta"})):
            assert client.post("/api/v1/projects" + route, json=payload).status_code == 403
        dev_headers = _login(client, "dev", "longer-password")
        for route, payload in (("", body), ("/setup-preview", body),
                               ("/id-availability", {"name": "beta"})):
            assert client.post("/api/v1/projects" + route, json=payload,
                               headers=dev_headers).status_code == 403
    assert app.state.profiles.list_profiles() == []


def test_guided_setup_rejects_unknown_secret_fields_without_echo(tmp_path):
    """@brief Unsupported JSON credentials are rejected, never silently ignored."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        result = client.post("/api/v1/projects",
                             json=_body(tmp_path, api_key="fixture-sensitive-value"),
                             headers=_login(client))
        assert result.status_code == 422
        assert "fixture-sensitive-value" not in result.text
        assert not app.state.profiles.exists("alpha")


def test_readiness_is_revision_bound_persisted_and_display_independent(tmp_path):
    """@brief Explicit fake probes produce evidence; config changes make it stale."""
    app, profile = _create(tmp_path)
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        return CommandResult(argv=argv, exit_code=0, stdout="", stderr="private detail")

    probed = create_app(app.state.profiles.home, probe_runner=runner)
    with TestClient(probed) as client:
        headers = _login(client)
        checked = client.post("/api/v1/projects/alpha/readiness-check", headers=headers)
        assert checked.status_code == 200, checked.text
        result = checked.json()
        assert result["revision"] and result["checked_at"]
        assert result["project_id"] == profile.project_id
        assert calls and "private" not in checked.text
        view = client.get("/api/v1/projects/alpha").json()
        assert view["verification"]["revision"] == result["revision"]
        assert view["verification"]["status"] != "unverified"
        renamed = client.put("/api/v1/projects/alpha/identity", json={"display_name": "Changed"},
                             headers=headers).json()
        assert renamed["verification"]["status"] == view["verification"]["status"]
        path = app.state.profiles.config_path("alpha")
        path.write_bytes(path.read_bytes() + b"\n# new revision\n")
        stale = client.get("/api/v1/projects/alpha").json()
        assert stale["verification"]["status"] == "stale"
        assert stale["validation"]["structural_valid"] and stale["paused"]
        path.write_text("[broken", encoding="utf-8")
        invalid = client.get("/api/v1/projects/alpha").json()
        assert not invalid["validation"]["structural_valid"]
        assert invalid["verification"]["status"] == "stale"
    with TestClient(create_app(app.state.profiles.home, probe_runner=_no_probe)) as client:
        _login(client)
        assert client.get("/api/v1/projects/alpha").json()["verification"]["status"] == "stale"


def test_readiness_rejects_mid_probe_revision_change(tmp_path):
    """@brief A probe cannot certify config bytes changed while commands ran."""
    app, _profile = _create(tmp_path)
    path = app.state.profiles.config_path("alpha")

    def runner(argv, **kwargs):
        path.write_bytes(path.read_bytes() + b"\n# concurrent edit\n")
        return CommandResult(argv=argv, exit_code=0, stdout="", stderr="")

    with TestClient(create_app(app.state.profiles.home, probe_runner=runner)) as client:
        result = client.post("/api/v1/projects/alpha/readiness-check", headers=_login(client))
        assert result.status_code == 409, result.text
        assert result.json()["detail"]["code"] == "stale_config_revision"
    assert not (app.state.profiles.profile_dir("alpha") / "readiness.json").exists()


@pytest.mark.parametrize("record", [{}, [], {"schema": 99}, {"schema": True},
                                   {"checked_at": "bad"}])
def test_corrupt_readiness_metadata_fails_closed(tmp_path, record):
    """@brief Corrupt stored verification never becomes a fresh or empty result."""
    app, _profile = _create(tmp_path)
    evidence = app.state.profiles.profile_dir("alpha") / "readiness.json"
    evidence.write_text(json.dumps(record), encoding="utf-8")
    with TestClient(app) as client:
        _login(client)
        response = client.get("/api/v1/projects/alpha")
        assert response.status_code == 503, response.text
        assert response.json()["detail"]["code"] == "readiness_probe_failed"
        assert response.json()["detail"]["issues"][0]["code"] == "readiness_corrupt"


def test_wizard_preparation_keeps_cli_defaults_and_never_probes(tmp_path):
    """@brief Preparation has no effects while normal CLI enrollment still saves unpaused."""
    from adore.wizard import ScriptedAsker, WizardSetup, run_wizard

    profiles = ProfileStore(tmp_path / "home")
    answers = _body(tmp_path)
    candidate = run_wizard(profiles, name="alpha", asker=ScriptedAsker(answers),
                           runner=_no_probe, prepare_only=True, out=lambda message: None)
    assert isinstance(candidate, WizardSetup) and candidate.document
    assert not profiles.profile_dir("alpha").exists()
    saved = run_wizard(profiles, name="alpha", asker=ScriptedAsker(answers),
                       runner=lambda argv, **kwargs: CommandResult(argv=argv, exit_code=127),
                       out=lambda message: None)
    assert saved.name == "alpha" and not StateStore(saved.store_root).is_paused()


def test_import_visibility_rollback_and_retained_state(tmp_path, monkeypatch):
    """@brief Exact imports pause before metadata; an audit failure restores external state."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    body = _import_body(tmp_path)
    state = StateStore(tmp_path / "state")
    state.save(RunState(run_id="retained", ticket_iid=1, lifecycle="done"))
    saved_bytes = (state.run_dir("retained") / "state.json").read_bytes()
    original = ProfileStore.create

    def observed_create(store, name, **kwargs):
        assert ProfileStore(store.home).list_profiles() == []
        assert state.is_paused()
        return original(store, name, **kwargs)

    monkeypatch.setattr(ProfileStore, "create", observed_create)
    with TestClient(app) as client:
        headers = _login(client)
        revision = client.post("/api/v1/projects/import-preview", json=body,
                               headers=headers).json()["revision"]
        original_audit = app.state.web_store.audit

        def broken_audit(actor, action, *args, **kwargs):
            if action == "project-imported":
                raise WebStoreError("private import failure")
            return original_audit(actor, action, *args, **kwargs)

        monkeypatch.setattr(app.state.web_store, "audit", broken_audit)
        failed = client.post("/api/v1/projects/import", json={**body, "revision": revision},
                             headers=headers)
        assert failed.status_code == 503 and "private" not in failed.text
        assert not state.is_paused()
        assert not app.state.profiles.profile_dir("imported").exists()
        assert (state.run_dir("retained") / "state.json").read_bytes() == saved_bytes
        monkeypatch.setattr(app.state.web_store, "audit", original_audit)
        success = client.post("/api/v1/projects/import", json={**body, "revision": revision},
                              headers=headers)
        assert success.status_code == 200 and success.json()["paused"]
        assert success.json()["display_name"] == "Imported service"
        assert (app.state.profiles.config_path("imported").read_bytes()
                == body["config_text"].encode())


@pytest.mark.parametrize("env", [
    {"OPENAI_API_KEY": "fixture-sensitive-value"},
    {"OPENAI_BASE_URL": "https://user:fixture-sensitive-value@model.invalid/v1"},
    {"OPENAI_BASE_URL": "https://model.invalid/v1?token=fixture-sensitive-value"},
])
def test_import_rejects_secret_runtime_values_and_provider_json(tmp_path, env):
    """@brief Secret rejection covers values and URLs without values in findings."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    body = _import_body(tmp_path)
    inline = ", ".join(key + " = " + json.dumps(value) for key, value in env.items())
    body["config_text"] = body["config_text"].replace(
        'runtime_env = { UV_LINK_MODE = "copy" }', "runtime_env = { " + inline + " }")
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/import-preview", json=body, headers=headers)
        assert preview.status_code == 200, preview.text
        assert not preview.json()["validation"]["structural_valid"]
        assert preview.json()["validation"]["issues"][0]["code"] == "secret_value"
        assert "fixture-sensitive-value" not in preview.text
        result = client.post("/api/v1/projects/import", json={
            **body, "revision": preview.json()["revision"]}, headers=headers)
        assert result.status_code == 400 and "fixture-sensitive-value" not in result.text
    assert not app.state.profiles.profile_dir("imported").exists()


@pytest.mark.parametrize("value", [
    json.dumps({"provider": {"local": {"options": {"apiKey": "fixture-sensitive-value"}}}}),
    json.dumps({"provider": {"local": {"options": {"apiKey": "{env:LOCAL_API_KEY}"}}}}),
])
def test_import_refuses_removed_agent_environment(tmp_path, value):
    """@brief A removed agent's environment variable is refused without echoing its value."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    body = _import_body(tmp_path)
    body["config_text"] = body["config_text"].replace(
        'runtime_env = { UV_LINK_MODE = "copy" }',
        "runtime_env = { OPENCODE_CONFIG_CONTENT = " + json.dumps(value) + " }")
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/import-preview", json=body, headers=headers)
        assert preview.status_code == 200, preview.text
        assert not preview.json()["validation"]["structural_valid"]
        assert "fixture-sensitive-value" not in preview.text
        assert {"code": "config_invalid",
                "field": "container.runtime_env.OPENCODE_CONFIG_CONTENT",
                "remediation": "Remove this key from config.toml; this build does not read it."
                } in preview.json()["validation"]["issues"]
        response = client.post("/api/v1/projects/import", json={
            **body, "revision": preview.json()["revision"]}, headers=headers)
        assert response.status_code == 400 and "fixture-sensitive-value" not in response.text
    assert not app.state.profiles.profile_dir("imported").exists()


@pytest.mark.parametrize(("old", "new", "field"), [
    ("[executor]\n", '[executor]\ndefault = "opencode"\n', "executor.default"),
    ("[executor]\n", "[executor.codex]\nmodel = \"m\"\n\n[executor]\n", "executor.codex"),
    ("[executor]\n", "[executor]\nstage_host_auth = true\n", "executor.stage_host_auth"),
])
def test_import_names_the_removed_agent_key_to_delete(tmp_path, old, new, field):
    """@brief An earlier build's agent configuration is refused, naming the key to delete."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    body = _import_body(tmp_path)
    assert old in body["config_text"]
    body["config_text"] = body["config_text"].replace(old, new, 1)
    with TestClient(app) as client:
        preview = client.post("/api/v1/projects/import-preview", json=body,
                              headers=_login(client))
        assert preview.status_code == 200, preview.text
        assert not preview.json()["validation"]["structural_valid"]
        assert {"code": "config_invalid", "field": field,
                "remediation": "Remove this key from config.toml; this build does not read it."
                } in preview.json()["validation"]["issues"]


@pytest.mark.parametrize("display", [None, "", " x "])
def test_explicit_invalid_enrollment_display_is_rejected(tmp_path, display):
    """@brief Explicit invalid names are not treated as legacy omission."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        result = client.post("/api/v1/projects", json=_body(tmp_path, display_name=display),
                             headers=_login(client))
        assert result.status_code == 400, result.text
    assert not app.state.profiles.profile_dir("alpha").exists()


@pytest.mark.parametrize("field,value", [
    ("revision", "x"), ("project_id", "0" * 32), ("checked_at", "2099-01-01T00:00:00+00:00"),
    ("checked_at", "2026-01-01"), ("checks", {"git": "yes"}),
    ("model_probe", {"context": "executor-container", "ready": False,
                     "model": "", "reason": "unrecognized-private-reason"}),
])
def test_readiness_rejects_tampered_valid_record_fields(tmp_path, field, value):
    """@brief Time, identity, schema and command-result evidence remain strict boundaries."""
    app, _profile = _create(tmp_path)
    def runner(argv, **kwargs):
        return CommandResult(argv=argv, exit_code=0)
    with TestClient(create_app(app.state.profiles.home, probe_runner=runner)) as client:
        headers = _login(client)
        checked = client.post("/api/v1/projects/alpha/readiness-check", headers=headers)
        assert checked.status_code == 200
        path = app.state.profiles.profile_dir("alpha") / "readiness.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record[field] = value
        path.write_text(json.dumps(record), encoding="utf-8")
        result = client.get("/api/v1/projects/alpha")
        assert result.status_code == 503, result.text
        assert "unrecognized-private-reason" not in result.text
        assert result.json()["detail"]["issues"][0]["code"] == "readiness_corrupt"


def test_preview_lists_the_settings_that_keep_their_defaults(tmp_path):
    """@brief Review and create shows every editable setting still at ADORE's default."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers = _login(client)
        kept = client.post("/api/v1/projects/setup-preview", json=_body(tmp_path),
                           headers=headers).json()
        changed = client.post("/api/v1/projects/setup-preview",
                              json=_body(tmp_path, max_cost_usd=2.5), headers=headers).json()
    defaults = {item["key"]: item["value"] for item in kept["defaults"]}
    assert defaults["polling.poll_interval_seconds"] == 60
    assert defaults["labels.lifecycle.working"] == "agent-working"
    assert defaults["budgets.max_cost_usd"] == 5.0
    assert all(set(item) == {"key", "value"} for item in kept["defaults"])
    # A value changed in the wizard is no longer a default.
    assert "budgets.max_cost_usd" not in {item["key"] for item in changed["defaults"]}


def test_enrollment_reviews_an_endpoint_provider_and_names_its_credential(tmp_path):
    """@brief Step 2 provider/endpoint answers reach the reviewed config; no key is asked."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    body = _body(tmp_path, provider="custom", model="qwen/qwen3.5-9b",
                 endpoint_base_url="http://172.27.80.1:1234/v1",
                 endpoint_api="openai-completions")
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        assert preview["structural_valid"], preview
        review = preview["review"]
        assert (review["provider"], review["model"]) == ("custom", "qwen/qwen3.5-9b")
        assert review["endpoint_base_url"] == "http://172.27.80.1:1234/v1"
        assert review["endpoint_api"] == "openai-completions"
        assert review["credential_variable"] == "ADORE_ENDPOINT_API_KEY"
        created = client.post("/api/v1/projects/setup-create", json={
            **body, "revision": preview["revision"]}, headers=headers)
        assert created.status_code == 200, created.text
        config = load_config(app.state.profiles.config_path("alpha"))
        assert config.executor.provider == "custom"
        assert config.executor.endpoint.base_url == "http://172.27.80.1:1234/v1"
        openai = client.post("/api/v1/projects/setup-preview", headers=headers,
                             json=_body(tmp_path, name="beta")).json()
        assert openai["review"]["credential_variable"] == "OPENAI_API_KEY"
        assert openai["review"]["endpoint_base_url"] == ""


@pytest.mark.parametrize(("changes", "field"), [
    ({"provider": "no-such-provider"}, "provider"),
    ({"provider": "custom", "model": "m"}, "endpoint_base_url"),
    ({"provider": "custom", "model": "m", "endpoint_base_url": "http://u:p@h/v1"},
     "endpoint_base_url"),
    ({"provider": "anthropic", "model": ""}, "model"),
])
def test_enrollment_refuses_an_invalid_provider_selection(tmp_path, changes, field):
    """@brief An unknown provider, an endpoint without URL and a missing model are findings."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        preview = client.post("/api/v1/projects/setup-preview", headers=_login(client),
                              json=_body(tmp_path, **changes)).json()
    assert preview["structural_valid"] is False
    assert any(issue["field"] == field for issue in preview["issues"]), preview["issues"]


@pytest.mark.parametrize("files,workflow", [(None, "not-inspected"), ([], "direct"),
    (["aegis.toml"], "direct"), (["aegis.py"], "aegis"),
    (["aegis.py", "aegis.toml"], "aegis")])
def test_draft_workflow_preview_check_and_creation(tmp_path, files, workflow):
    """@brief Read-only preview/check agree; creation preserves the measured observation."""
    body = _body(tmp_path)
    clone = Path(body["repo_path"])
    if files is None:
        (clone / ".git").rmdir()
        clone.rmdir()
        body["clone_url"] = "https://forge.test/owner/alpha.git"
    else:
        for name in files:
            target = clone / ".agentic" / name
            target.parent.mkdir(exist_ok=True)
            target.write_text("raise RuntimeError('never execute')\n", encoding="utf-8")
    if files is not None:
        (clone / "go.mod").write_text("module example\n", encoding="utf-8")
    before = {str(p.relative_to(clone)): p.read_bytes() for p in clone.rglob("*") if p.is_file()}

    def runner(argv, **kwargs):
        assert not any("aegis" in str(arg) for arg in argv)
        return CommandResult(argv=argv, exit_code=127)

    app = create_app(tmp_path / "home", probe_runner=runner)
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        assert preview["structural_valid"], preview
        assert preview["workflow"] == workflow
        assert "verification_hint" not in preview
        checked = client.post("/api/v1/projects/setup-check", headers=headers,
                              json={**body, "revision": preview["revision"]})
        assert checked.status_code == 200, checked.text
        assert checked.json()["workflow"] == workflow
        assert "aegis_files" not in checked.json()["checks"]
        assert before == {str(p.relative_to(clone)): p.read_bytes()
                          for p in clone.rglob("*") if p.is_file()}
        if files is None:
            assert not clone.exists()
        else:
            created = client.post("/api/v1/projects/setup-create", headers=headers, json={
                **body, "revision": preview["revision"],
                "evidence_token": checked.json()["evidence_token"]})
            assert created.status_code == 200, created.text
            assert created.json()["verification"]["workflow"] == workflow
            assert created.json()["verification"]["checks"] == checked.json()["checks"]
            assert before == {str(p.relative_to(clone)): p.read_bytes()
                              for p in clone.rglob("*") if p.is_file()}


@pytest.mark.parametrize("bad", ["missing", "unknown", None, True, 1, [], {}])
def test_draft_invalid_workflow_never_issues_evidence(tmp_path, monkeypatch, bad):
    """@brief Draft probes validate the required enum before issuing any token."""
    import adore.web.app as web_app

    evidence = {"checks": dict.fromkeys(["git", "forge_cli", "forge_auth", "container_runtime",
                                         "executor_cli", "egress_proxy"], True)}
    if bad != "missing":
        evidence["workflow"] = bad
    monkeypatch.setattr(web_app, "_probe_setup", lambda *a, **kw: evidence)
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    body = _body(tmp_path)
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        result = client.post("/api/v1/projects/setup-check", headers=headers,
                             json={**body, "revision": preview["revision"]})
        assert result.status_code == 503, result.text
        assert result.json()["detail"]["code"] == "readiness_probe_failed"
        assert "evidence_token" not in result.json()
        assert not app.state.profiles.profile_dir("alpha").exists()


# END OF FILE



def test_removed_verification_command_cannot_be_reintroduced_through_enrollment(tmp_path):
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers = _login(client)
        result = client.post("/api/v1/projects/setup-preview", headers=headers,
                             json={**_body(tmp_path), "verify_command": "must-not-run"})
        assert result.status_code == 422
        assert not app.state.profiles.list_profiles()
