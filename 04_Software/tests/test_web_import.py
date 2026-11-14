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
@file test_web_import.py
@brief Existing configuration import through the web trust boundary.
@details Preview and save preserve source bytes and start with pickup paused.
"""

# IMPORTS
from hashlib import sha256
from pathlib import Path
import re

from adore.config_edit import config_edit_lock
from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.util import CommandResult
from adore.web.app import create_app
from adore.web.store import WebStore
import pytest

from tests.configuration_client import TestClient


# LOCAL HELPERS
def _document(tmp_path):
    """@brief Adapt the sample config to unambiguous absolute local paths."""
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    text = example.read_text(encoding="utf-8")
    paths = {
        'store_root = ".adore"': f'store_root = "{(tmp_path / "state").as_posix()}"',
        'repo_path = "../project"': f'repo_path = "{(tmp_path / "repo").as_posix()}"',
        'root = "worktrees"': f'root = "{(tmp_path / "trees").as_posix()}"',
        'db_path = ".adore/metrics.db"':
            f'db_path = "{(tmp_path / "state" / "metrics.db").as_posix()}"',
        'export_jsonl = ".adore/metrics/runs.jsonl"':
            f'export_jsonl = "{(tmp_path / "state" / "metrics" / "runs.jsonl").as_posix()}"',
        'html_out = ".adore/metrics/stats.html"':
            f'html_out = "{(tmp_path / "state" / "metrics" / "stats.html").as_posix()}"',
    }
    for old, new in paths.items():
        assert old in text
        text = text.replace(old, new)
    return text


def _csrf(client):
    """@brief Authenticate the bootstrap administrator."""
    return client.post("/api/v1/session", json={
        "username": "admin", "password": "admin"}).json()["csrf"]


# PUBLIC API / CONTRACT TESTS
def test_import_explicit_null_display_name_is_refused(tmp_path):
    """@brief Transport preserves explicit null instead of converting it to an omitted field."""
    home = tmp_path / "home"
    with TestClient(create_app(home)) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        response = client.post("/api/v1/projects/import-preview", headers=headers,
                               json={"config_text": _document(tmp_path), "display_name": None})
        assert response.status_code == 400, response.text
        assert response.json()["detail"]["issues"][0]["code"] == "invalid_display_name"
        assert ProfileStore(home).list_profiles() == []


def test_raw_import_preview_derives_identity_and_binds_exact_file(tmp_path):
    """@brief Preview without an ID and publish only the reviewed raw TOML."""
    home = tmp_path / "home"
    text = _document(tmp_path).replace("group/subgroup/project", "group/Raw-Import")
    with TestClient(create_app(home)) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        response = client.post("/api/v1/projects/import-preview",
                               json={"config_text": text}, headers=headers)
        assert response.status_code == 200, response.text
        preview = response.json()
        assert preview["validation"]["structural_valid"]
        assert preview["name"] == "raw-import"
        assert preview["display_name"] == "Raw-Import"
        assert preview["config_revision"] == sha256(text.encode("utf-8")).hexdigest()
        body = {key: preview[key] for key in ("name", "display_name", "revision")}
        changed = client.post("/api/v1/projects/import", headers=headers,
                              json={**body, "config_text": text + "\n# changed\n"})
        assert changed.status_code == 409
        assert not ProfileStore(home).config_path("raw-import").exists()
        created = client.post("/api/v1/projects/import", headers=headers,
                              json={**body, "config_text": text})
        assert created.status_code == 200, created.text
        assert created.json()["pickup_state"] == "stopped"
        assert ProfileStore(home).config_path("raw-import").read_bytes() == text.encode("utf-8")
        duplicate = client.post("/api/v1/projects/import-preview",
                                json={"config_text": text}, headers=headers).json()
        assert duplicate["name"] == "raw-import-2"
        assert "state_root_already_owned" in duplicate["issues"]
        assert duplicate["review"] is None


def test_raw_import_preview_never_derives_an_identity_from_secret_url(tmp_path):
    """@brief A malformed repository URL cannot expose credentials as an identity."""
    private = "fixture-private-value"
    text = _document(tmp_path).replace("group/subgroup/project",
                                       f"https://user:{private}@example.test")
    with TestClient(create_app(tmp_path / "home")) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        response = client.post("/api/v1/projects/import-preview",
                               json={"config_text": text}, headers=headers)
        assert response.status_code == 200
        assert private not in response.text
        assert response.json()["review"] is None
        assert response.json()["issues"] == ["secret_value:platform.repo"]


@pytest.mark.parametrize("revision", ["é", "", "0" * 65])
def test_import_confirmation_rejects_malformed_revision_as_typed_conflict(tmp_path, revision):
    """@brief Unicode and malformed untrusted revisions produce a safe conflict."""
    with TestClient(create_app(tmp_path / "home")) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        body = {"name": "alpha", "config_text": _document(tmp_path), "revision": revision}
        for route in ("import", "import-check"):
            response = client.post("/api/v1/projects/" + route, json=body, headers=headers)
            assert response.status_code == 409, response.text
            assert response.json()["detail"]["code"] == "stale_import_preview"


def test_exact_import_rejects_invalid_utf8_description_without_server_error(tmp_path):
    """@brief Malformed JSON identity text fails closed before digest/probe/publication."""
    import json
    with TestClient(create_app(tmp_path / "home")) as client:
        headers = {"X-CSRF-Token": _csrf(client), "Content-Type": "application/json"}
        body = {"name": "alpha", "description": "\ud800", "config_text": _document(tmp_path),
                "revision": "0" * 64}
        for route in ("import-preview", "import-check", "import"):
            response = client.post("/api/v1/projects/" + route, content=json.dumps(body),
                                   headers=headers)
            assert response.status_code == 422, response.text
            assert response.json()["detail"]["code"] == "invalid_request"
            assert response.json()["detail"]["issues"][0]["field"] == "description"


@pytest.mark.parametrize("route", ["import-preview", "import-check", "import"])
def test_exact_routes_enforce_admin_and_csrf_before_input_or_probes(tmp_path, route):
    """@brief Direct routes reject anonymous/Dev/missing/invalid CSRF consistently."""
    def runner(argv, **kwargs):
        """@brief Unauthorized callers must never reach an external command."""
        raise AssertionError("unexpected command")

    app = create_app(tmp_path / "home", probe_runner=runner)
    app.state.web_store.create_user("dev", "longer-password", "developer")
    body = {"name": "alpha", "config_text": _document(tmp_path), "revision": "0" * 64}
    with TestClient(app) as client:
        path = "/api/v1/projects/" + route
        assert client.post(path, json=body).status_code == 401
        headers = {"X-CSRF-Token": _csrf(client)}
        assert client.post(path, json=body).status_code == 403
        assert client.post(path, json=body, headers={"X-CSRF-Token": "bad"}).status_code == 403
        client.delete("/api/v1/session", headers=headers)
        csrf = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"}).json()["csrf"]
        assert client.post(path, json=body, headers={"X-CSRF-Token": csrf}).status_code == 403
        assert app.state.profiles.list_profiles() == []


@pytest.mark.parametrize("condition", ["corrupt", "active", "lock", "duplicate", "equal",
                                      "ancestor", "descendant", "corrupt-profile"])
def test_exact_import_rejects_state_and_ownership_boundaries(tmp_path, condition):
    """@brief Source inspection and confirmation fail closed on unsafe persisted data."""
    profiles = ProfileStore(tmp_path / "home")
    state = StateStore(tmp_path / "state")
    if condition == "corrupt":
        state.run_dir("bad").mkdir(parents=True)
        (state.run_dir("bad") / "state.json").write_text("{broken", encoding="utf-8")
    elif condition == "active":
        state.save(RunState(run_id="working", ticket_iid=1, lifecycle="working"))
    elif condition == "lock":
        state.root.mkdir()
        state.lock_path.write_text("{}", encoding="utf-8")
    elif condition == "duplicate":
        profiles.create("alpha", store_root=str(tmp_path / "other"))
    else:
        root = {"equal": state.root, "ancestor": tmp_path,
                "descendant": state.root / "child"}.get(condition, tmp_path / "other")
        profiles.create("other", store_root=str(root))
        if condition == "corrupt-profile":
            (profiles.profile_dir("other") / "profile.json").write_text("{bad", encoding="utf-8")
    with TestClient(create_app(profiles.home)) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        body = {"name": "alpha", "config_text": _document(tmp_path)}
        preview = client.post("/api/v1/projects/import-preview", json=body, headers=headers)
        if condition == "corrupt-profile":
            assert preview.status_code == 503
        else:
            assert preview.status_code == 200, preview.text
            assert preview.json()["validation"]["issues"]
            assert preview.json()["review"] is None
            assert client.post("/api/v1/projects/import", json={
                **body, "revision": preview.json()["revision"]}, headers=headers).status_code == 409
        if condition != "duplicate":
            assert not profiles.exists("alpha")


@pytest.mark.parametrize("mutation", ["owner", "run", "config-lock", "conductor-lock"])
def test_exact_confirmation_reinspects_mutations_at_publication_lock(
    tmp_path, monkeypatch, mutation,
):
    """@brief Changes between route inspection and locked publication cannot enroll."""
    profiles = ProfileStore(tmp_path / "home")
    body = {"name": "alpha", "config_text": _document(tmp_path)}
    acquire = StateStore.acquire_lock
    changed = False

    def changed_acquire(state):
        """@brief Simulate an external mutation at the conductor lock boundary."""
        nonlocal changed
        if not changed and state.root == tmp_path / "state":
            changed = True
            if mutation == "owner":
                profiles.create("concurrent", store_root=str(state.root / "child"))
            elif mutation == "run":
                state.save(RunState(run_id="late", ticket_iid=1, lifecycle="working"))
        return acquire(state)

    with TestClient(create_app(profiles.home)) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        revision = client.post("/api/v1/projects/import-preview", json=body,
                               headers=headers).json()["revision"]
        payload = {**body, "revision": revision}
        if mutation == "config-lock":
            with config_edit_lock(profiles.home / "web-enrollment" / "config.toml"):
                response = client.post("/api/v1/projects/import", json=payload, headers=headers)
        elif mutation == "conductor-lock":
            state = StateStore(tmp_path / "state")
            assert state.acquire_lock()
            try:
                response = client.post("/api/v1/projects/import", json=payload, headers=headers)
            finally:
                state.release_lock()
        else:
            monkeypatch.setattr(StateStore, "acquire_lock", changed_acquire)
            response = client.post("/api/v1/projects/import", json=payload, headers=headers)
        assert response.status_code == 409, response.text
        assert not profiles.exists("alpha")
        assert not StateStore(tmp_path / "state").is_paused()


def test_changed_physical_server_location_rejects_unchanged_text(tmp_path, monkeypatch):
    """@brief Simulated symlink resolution changes invalidate the public review digest."""
    body = {"name": "alpha", "config_text": _document(tmp_path)}
    original = Path.resolve
    changed = False

    def resolve(path, *args, **kwargs):
        """@brief Simulate a changed external path target without platform symlink privileges."""
        if changed and path == tmp_path / "state":
            return tmp_path / "new-state"
        return original(path, *args, **kwargs)

    with TestClient(create_app(tmp_path / "home")) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        preview = client.post("/api/v1/projects/import-preview", json=body,
                              headers=headers).json()
        monkeypatch.setattr(Path, "resolve", resolve)
        changed = True
        response = client.post("/api/v1/projects/import", json={
            **body, "revision": preview["revision"]}, headers=headers)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "stale_import_preview"


@pytest.mark.parametrize("bad", ["malformed", "secret", "url", "inline", "oversize", "surrogate"])
def test_exact_inspection_never_echoes_secret_or_invalid_input(tmp_path, bad):
    """@brief Bad encoding, sizes, secret keys and secret URLs have no review or echo."""
    private = "fixture-private-value"
    document = _document(tmp_path)
    if bad == "malformed":
        document += "\n[broken\n"
    elif bad == "secret":
        document += '\n[unsafe]\napi_key = "' + private + '"\n'
    elif bad == "url":
        document += '\n[unsafe]\nendpoint = "https://user:' + private + '@example.test"\n'
    elif bad == "inline":
        document += ('\n[container.runtime_env]\nOPENCODE_CONFIG_CONTENT = '
                     '\'{"apiKey":"' + private + '"}\'\n')
    elif bad == "surrogate":
        document = "\ud800"
    else:
        document = "#" + "é" * 270000
    with TestClient(create_app(tmp_path / "home")) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        body = {"name": "alpha", "config_text": document}
        if bad == "surrogate":
            import json
            preview = client.post("/api/v1/projects/import-preview", content=json.dumps(body),
                                  headers={**headers, "Content-Type": "application/json"})
        else:
            preview = client.post("/api/v1/projects/import-preview", json=body, headers=headers)
        assert private not in preview.text
        if bad in {"oversize", "surrogate"}:
            assert preview.status_code in (400, 413, 422)
        else:
            assert preview.json()["review"] is None
            assert preview.json()["validation"]["issues"]
            checked = client.post("/api/v1/projects/import-check", json={
                **body, "revision": preview.json()["revision"]}, headers=headers)
            assert checked.status_code == 400
            assert private not in checked.text


@pytest.mark.parametrize("mode", ["partial", "verified", "exception", "mutation"])
def test_explicit_import_probe_outcomes_reinspect_and_redact(tmp_path, monkeypatch, mode):
    """@brief Partial/error evidence and concurrent mutations cannot claim success."""
    profiles = ProfileStore(tmp_path / "home")
    document = _document(tmp_path)
    called = False

    def runner(argv, **kwargs):
        """@brief Simulate commands and an ownership change during an explicit probe."""
        nonlocal called
        if mode == "exception":
            raise TimeoutError("fixture-private-value")
        if mode == "mutation" and not called:
            profiles.create("late", store_root=str(tmp_path / "state"))
            called = True
        return CommandResult(argv=argv, exit_code=0, stdout="fixture-private-value")

    if mode == "verified":
        monkeypatch.setattr("adore.web.app._readiness_auth_bound", lambda *a: True)
    if mode in {"partial", "verified"}:
        clone = tmp_path / "repo" / ".agentic"
        clone.mkdir(parents=True)
        (clone / "aegis.py").touch()
        (clone / "aegis.toml").touch()
    if mode == "partial":
        # A WSL-wrapped runtime cannot be probed from the API host: coverage stays partial.
        assert 'runtime = "docker"' in document
        document = document.replace('runtime = "docker"', 'runtime = "wsl -d fixture -- docker"')
    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        body = {"name": "alpha", "config_text": document}
        preview = client.post("/api/v1/projects/import-preview", json=body,
                              headers=headers).json()
        checked = client.post("/api/v1/projects/import-check", json={
            **body, "revision": preview["revision"]}, headers=headers)
        assert checked.status_code == {"partial": 200, "verified": 200,
                                       "exception": 503, "mutation": 409}[mode]
        assert "fixture-private-value" not in checked.text
        if mode == "partial":
            assert checked.json()["status"] == "partial"
        if mode == "verified":
            assert checked.json()["status"] == "verified"
        assert not profiles.exists("alpha")


def test_admin_previews_then_imports_exact_config_paused(tmp_path):
    """@brief Import copies validated TOML and retains external state path."""
    profiles = ProfileStore(tmp_path / "home")
    document = _document(tmp_path)
    existing_state = StateStore(tmp_path / "state")
    existing_state.save(RunState(run_id="old-run", ticket_iid=42, lifecycle="done"))
    body = {"name": "alpha", "description": "Imported", "config_text": document}
    with TestClient(create_app(profiles.home)) as client:
        csrf = _csrf(client)
        headers = {"X-CSRF-Token": csrf}
        preview = client.post("/api/v1/projects/import-preview", json=body, headers=headers)
        assert preview.status_code == 200, preview.text
        assert preview.json()["issues"] == []
        assert preview.json()["repo"] == "group/subgroup/project"
        assert not profiles.exists("alpha")

        response = client.post("/api/v1/projects/import", json={
            **body, "revision": preview.json()["revision"]}, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["paused"] is True
        assert profiles.config_path("alpha").read_text(encoding="utf-8") == document
        assert Path(profiles.load("alpha").store_root) == tmp_path / "state"
        assert StateStore(tmp_path / "state").is_paused()
        assert client.get("/api/v1/projects/alpha/runs").json()[0]["run_id"] == "old-run"
        assert client.get("/api/v1/projects/alpha/config").status_code == 200


def test_import_reviews_all_locations_and_binds_declared_identity(tmp_path):
    """@brief Review exact bytes and consequential safe settings, bind identity too."""
    profiles = ProfileStore(tmp_path / "home")
    document = _document(tmp_path).replace("\n", "\r\n") + "# café\r\n"
    body = {"name": "alpha", "display_name": "Service", "description": "Exact",
            "config_text": document}
    with TestClient(create_app(profiles.home)) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        preview = client.post("/api/v1/projects/import-preview", json=body,
                              headers=headers).json()
        assert preview["config_revision"] == sha256(document.encode()).hexdigest()
        review = preview["review"]
        assert set(review["paths"]) == {"worktree.repo_path", "worktree.root",
            "state.store_root", "metrics.db_path", "metrics.export_jsonl", "metrics.html_out"}
        assert review["resolved_paths"]["state.store_root"] == str((tmp_path / "state").resolve())
        assert review["config_path"] == str(profiles.config_path("alpha").resolve())
        assert "agent" in review and "executor" in review and "container" in review
        assert review["executor"] == {"provider": "openai", "model": "gpt-5.5",
                                      "endpoint_base_url": "", "env_keys": []}
        for mutation in ({"display_name": "Changed"}, {"description": "Changed"},
                         {"name": "beta"}, {"config_text": document + "# changed\n"}):
            response = client.post("/api/v1/projects/import", json={
                **body, **mutation, "revision": preview["revision"]}, headers=headers)
            assert response.status_code == 409, response.text
        response = client.post("/api/v1/projects/import", json={
            **body, "revision": preview["revision"]}, headers=headers)
        assert response.status_code == 200, response.text
        assert profiles.config_path("alpha").read_bytes() == document.encode()
        assert response.json()["pickup_state"] == "stopped"


def test_import_explicit_check_is_ephemeral_failed_and_revision_bound(tmp_path):
    """@brief Fake probes preserve failed evidence and reject stale before commands."""
    calls = []

    def runner(argv, **kwargs):
        """@brief Simulate unavailable tools within the existing deadline."""
        calls.append((argv, kwargs))
        return CommandResult(argv=argv, exit_code=127, stdout="", stderr="offline")

    profiles = ProfileStore(tmp_path / "home")
    body = {"name": "alpha", "config_text": _document(tmp_path)}
    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        preview = client.post("/api/v1/projects/import-preview", json=body,
                              headers=headers).json()
        assert not calls
        response = client.post("/api/v1/projects/import-check", json={
            **body, "revision": preview["revision"]}, headers=headers)
        assert response.status_code == 200, response.text
        evidence = response.json()
        assert evidence["status"] == "failed" and evidence["revision"] == preview["revision"]
        assert evidence["config_revision"] == preview["config_revision"]
        assert evidence["checked_at"] and evidence["context"] == "api-host"
        assert calls and all(call[1]["timeout"] <= 8 for call in calls)
        assert not profiles.exists("alpha")
        calls.clear()
        assert client.post("/api/v1/projects/import-check", json={
            **body, "description": "changed", "revision": preview["revision"]},
            headers=headers).status_code == 409
        assert not calls


@pytest.mark.parametrize("path", ["state.store_root", "worktree.repo_path", "worktree.root",
                                  "metrics.db_path", "metrics.export_jsonl", "metrics.html_out"])
def test_import_rejects_each_relative_or_volume_root_location(tmp_path, path):
    """@brief Every consequential host location has an absolute non-root boundary."""
    profiles = ProfileStore(tmp_path / "home")
    document = _document(tmp_path)
    section, key = path.split(".")
    pattern = rf"(?ms)(\[{section}\].*?^{key} = )\"[^\"]*\""
    with TestClient(create_app(profiles.home)) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        for invalid in ("relative/place", Path(tmp_path.anchor).as_posix()):
            changed = re.sub(pattern, lambda match, value=invalid: match[1] + '"' + value + '"',
                             document)
            assert changed != document
            body = {"name": "alpha", "config_text": changed}
            preview = client.post("/api/v1/projects/import-preview", json=body,
                                  headers=headers).json()
            assert preview["validation"]["structural_valid"] is False
            assert any(item["field"] == path for item in preview["validation"]["issues"])
            assert client.post("/api/v1/projects/import", json={
                **body, "revision": preview["revision"]}, headers=headers).status_code == 400
        assert not profiles.exists("alpha")


def test_import_rejects_invalid_secret_relative_and_stale_input(tmp_path):
    """@brief Unreviewed or ambiguous input cannot create a profile."""
    profiles = ProfileStore(tmp_path / "home")
    document = _document(tmp_path)
    with TestClient(create_app(profiles.home)) as client:
        csrf = _csrf(client)
        headers = {"X-CSRF-Token": csrf}
        body = {"name": "alpha", "config_text": document}
        preview = client.post("/api/v1/projects/import-preview", json=body,
                              headers=headers).json()
        assert client.post("/api/v1/projects/import", json={
            **body, "revision": "bad-hash"}, headers=headers).status_code == 409
        for bad in (document + "\n[bad\n", document.replace(
            'store_root = "', 'store_root = "relative/'), document +
            '\n[unsafe]\napi_key = "not-a-real-secret"\n'):
            response = client.post("/api/v1/projects/import-preview", json={
                **body, "config_text": bad}, headers=headers)
            assert response.status_code == 200, response.text
            assert response.json()["issues"]
            assert client.post("/api/v1/projects/import", json={
                **body, "config_text": bad,
                "revision": response.json()["revision"]}, headers=headers).status_code == 400
        assert preview["issues"] == []
        assert not profiles.exists("alpha")


def test_import_requires_admin_csrf_and_unique_state_root(tmp_path):
    """@brief Developers and duplicate state owners cannot import."""
    profiles = ProfileStore(tmp_path / "home")
    document = _document(tmp_path)
    web = WebStore(profiles.home / "web.db")
    web.create_user("dev", "longer-password", "developer")
    body = {"name": "alpha", "config_text": document}
    with TestClient(create_app(profiles.home)) as client:
        csrf = _csrf(client)
        assert client.post("/api/v1/projects/import-preview", json=body).status_code == 403
        headers = {"X-CSRF-Token": csrf}
        preview = client.post("/api/v1/projects/import-preview", json=body,
                              headers=headers).json()
        assert client.post("/api/v1/projects/import", json={
            **body, "revision": preview["revision"]}).status_code == 403
        assert client.post("/api/v1/projects/import", json={
            **body, "revision": preview["revision"]}, headers=headers).status_code == 200
        other = {**body, "name": "beta"}
        conflict = client.post("/api/v1/projects/import-preview", json=other,
                               headers=headers)
        assert conflict.status_code == 200
        assert conflict.json()["issues"]
        client.delete("/api/v1/session", headers=headers)
        dev_csrf = client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"}).json()["csrf"]
        assert client.post("/api/v1/projects/import-preview", json=other,
                           headers={"X-CSRF-Token": dev_csrf}).status_code == 403


def test_import_rejects_active_state_and_conductor_lock(tmp_path):
    """@brief Existing active work must finish before ownership is imported."""
    profiles = ProfileStore(tmp_path / "home")
    document = _document(tmp_path)
    state = StateStore(tmp_path / "state")
    body = {"name": "alpha", "config_text": document}
    with TestClient(create_app(profiles.home)) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        revision = client.post("/api/v1/projects/import-preview", json=body,
                               headers=headers).json()["revision"]
        state.save(RunState(run_id="running", ticket_iid=42, lifecycle="working"))
        assert client.post("/api/v1/projects/import", json={
            **body, "revision": revision}, headers=headers).status_code == 409
        assert not profiles.exists("alpha")
        state.save(RunState(run_id="running", ticket_iid=42, lifecycle="done"))
        assert state.acquire_lock()
        try:
            assert client.post("/api/v1/projects/import", json={
                **body, "revision": revision}, headers=headers).status_code == 409
        finally:
            state.release_lock()
        assert not profiles.exists("alpha")


@pytest.mark.parametrize("bad", ["missing", "unknown", None, True, 1, [], {}, "checks"])
def test_import_probe_rejects_invalid_workflow(tmp_path, monkeypatch, bad):
    """@brief Exact import also validates workflow/checks before releasing evidence."""
    import adore.web.app as web_app

    evidence = {"checks": dict.fromkeys(["git", "forge_cli", "forge_auth", "container_runtime",
                                         "executor_cli", "egress_proxy"], True),
                "workflow": "direct"}
    if bad == "missing":
        evidence.pop("workflow")
    elif bad == "checks":
        evidence["checks"]["git"] = "not-checked"
    else:
        evidence["workflow"] = bad
    monkeypatch.setattr(web_app, "_probe_setup", lambda *a, **kw: evidence)
    app = create_app(tmp_path / "home")
    body = {"name": "alpha", "config_text": _document(tmp_path)}
    with TestClient(app) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        preview = client.post("/api/v1/projects/import-preview", json=body, headers=headers).json()
        result = client.post("/api/v1/projects/import-check", headers=headers,
                             json={**body, "revision": preview["revision"]})
        assert result.status_code == 503, result.text
        assert result.json()["detail"]["code"] == "readiness_probe_failed"
        assert not app.state.profiles.profile_dir("alpha").exists()


@pytest.mark.parametrize("workflow", ["aegis", "direct", "not-inspected"])
@pytest.mark.parametrize("bound", [True, False])
def test_import_workflow_is_independent_of_auth_verdict(tmp_path, monkeypatch, workflow, bound):
    """@brief Exact import uses the prerequisite and authentication verdict, not workflow."""
    import adore.web.app as web_app

    checks = dict.fromkeys(["git", "forge_cli", "forge_auth", "container_runtime",
                            "executor_cli", "egress_proxy"], True)
    monkeypatch.setattr(web_app, "_probe_setup", lambda *a, **kw:
                        {"workflow": workflow, "checks": checks})
    monkeypatch.setattr(web_app, "_readiness_auth_bound", lambda *a: bound)
    app = create_app(tmp_path / "home")
    body = {"name": "alpha", "config_text": _document(tmp_path)}
    with TestClient(app) as client:
        headers = {"X-CSRF-Token": _csrf(client)}
        preview = client.post("/api/v1/projects/import-preview", json=body, headers=headers).json()
        result = client.post("/api/v1/projects/import-check", headers=headers,
                             json={**body, "revision": preview["revision"]})
        assert result.status_code == 200, result.text
        assert result.json()["status"] == ("verified" if bound else "partial")
        assert result.json()["workflow"] == workflow
        assert result.json()["auth_bound"] is bound
        assert result.json()["required_checks"] == sorted(checks)


# END OF FILE
