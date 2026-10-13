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
@file    test_web_image_build.py
@brief   Project image HTTP, worker and reviewed selection contracts.
@details Uses an injectable runtime and local test sessions, never live builds.
"""

from hashlib import sha256

from adore.web.app import create_app
from adore.web.commands import CommandWorker
from fastapi.testclient import TestClient
import pytest

from tests.test_image_build import build_project


def image_client(tmp_path):
    """@brief Create an administrator session on a stopped image-build profile."""
    _module, profiles, store, service, runner, operation, path = build_project(tmp_path)
    app = create_app(profiles.home, probe_runner=runner)
    client = TestClient(app)
    login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
    assert login.status_code == 200, login.text
    headers = {"x-csrf-token": login.json()["csrf"]}
    return client, headers, profiles, store, service, runner, operation, path


def test_executor_environment_guidance_is_truthful_and_role_scoped(tmp_path):
    """@brief Container metadata uses current config and limits server paths to Admin."""
    client, _headers, profiles, _store, _service, runner, _operation, path = image_client(tmp_path)
    current = client.get("/api/v1/projects/alpha/config")
    assert current.status_code == 200
    environment = current.json()["executor_environment"]
    assert environment["backend"] == "container"
    assert environment["image"] == current.json()["config"]["container"]["image"]
    assert environment["config_path"] == str(path.resolve())
    assert not runner.calls
    web = client.app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.set_memberships(dev["id"], ["alpha"])
    client.post("/api/v1/session", json={"username": "dev", "password": "longer-password"})
    visible = client.get("/api/v1/projects/alpha/config")
    assert visible.status_code == 200
    assert visible.json()["executor_environment"]["config_path"] is None
    assert str(path.resolve()) not in visible.text
    web.set_memberships(dev["id"], [])
    assert client.get("/api/v1/projects/alpha/config").status_code == 404


# The backend, runtime, image and local account fields are chosen in the web
# (tests/test_executor_environment_choice.py); every other environment key stays external.
@pytest.mark.parametrize("key", ["execution.preparation", "container.uv_cache_volume",
                                  "container.run_args", "worktree.root"])
@pytest.mark.parametrize("route", ["/config", "/config/pending"])
def test_web_environment_edits_are_external(tmp_path, key, route):
    """@brief Both edit surfaces reject environment ownership before writes or probes."""
    client, headers, _profiles, store, _service, runner, _operation, path = image_client(tmp_path)
    original = path.read_bytes()
    body = {"key": key, "value": "external", "revision": sha256(original).hexdigest()}
    response = client.request("PUT" if route == "/config" else "POST",
                              "/api/v1/projects/alpha" + route, headers=headers, json=body)
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["code"] == "environment_managed_externally"
    assert path.read_bytes() == original
    assert not (store.profile / "pending_config.json").exists()
    assert not runner.calls
    metadata = client.get("/api/v1/projects/alpha/config").json()["settings"]
    assert not any(item["editable"] for item in metadata if item["key"] == key)


@pytest.mark.parametrize("method,route,body", [
    ("PUT", "/image-build", {"dockerfile": "arbitrary", "checks": [], "revision": ""}),
    ("POST", "/image-build/operations", {"revision": "a" * 64,
      "config_revision": "b" * 64, "idempotency_key": "retired-build"}),
])
def test_retired_web_build_requests_preserve_artifacts(tmp_path, method, route, body):
    """@brief Obsolete clients get a typed retirement response without saved effects."""
    client, headers, _profiles, store, _service, runner, _operation, path = image_client(tmp_path)
    original, draft, operations = path.read_bytes(), store.export(), store.operations()
    response = client.request(method, "/api/v1/projects/alpha" + route,
                              headers=headers, json=body)
    assert response.status_code == 410, response.text
    assert response.json()["detail"]["code"] == "environment_managed_externally"
    assert path.read_bytes() == original and store.export() == draft
    assert store.operations() == operations and not runner.calls
    assert client.get("/api/v1/projects/alpha/image-build").status_code == 200
    assert client.get("/api/v1/projects/alpha/image-build/export").status_code == 200


def test_retained_queued_image_build_fails_without_runtime(tmp_path):
    """@brief A pre-upgrade queue cannot restart the retired build workflow."""
    client, _headers, profiles, store, _service, runner, operation, path = image_client(tmp_path)
    web = client.app.state.web_store
    actor = web.authenticate("admin", "admin")
    queued = web.enqueue(actor["id"], "alpha", "image-build", operation["id"], "old-request")
    worker = CommandWorker(profiles, web, image_runner=runner)
    assert worker.run_pending() == 1
    outcome = web.operation(queued["id"])
    assert outcome["status"] == "failed"
    assert "externally" in outcome["result"]
    assert store.operation(operation["id"])["phase"] == "failed"
    assert not runner.calls
    assert path.exists()


def test_non_environment_candidate_still_applies(tmp_path):
    """@brief Budget settings retain the current candidate/apply ownership contract."""
    client, headers, _profiles, _store, _service, runner, _operation, path = image_client(tmp_path)
    base = "/api/v1/projects/alpha"
    staged = client.post(base + "/config/pending", headers=headers,
                         json={"key": "budgets.max_iterations", "value": "30",
                               "revision": sha256(path.read_bytes()).hexdigest()})
    assert staged.status_code == 200, staged.text
    applied = client.post(base + "/config/apply", headers=headers,
                          json={"candidate_revision": staged.json()["candidate_revision"]})
    assert applied.status_code == 200, applied.text
    assert client.get(base + "/config").json()["config"]["budgets"]["max_iterations"] == 30
    assert not runner.calls



@pytest.mark.parametrize("role", ["anonymous", "csrf", "developer"])
def test_retired_build_keeps_authentication_boundaries(tmp_path, role):
    """@brief Retirement does not grant unauthenticated or unauthorized mutation access."""
    client, headers, _profiles, store, _service, runner, _operation, path = image_client(tmp_path)
    original = path.read_bytes()
    if role == "anonymous":
        client.cookies.clear()
    elif role == "csrf":
        headers = {}
    else:
        web = client.app.state.web_store
        dev = web.create_user("dev", "longer-password", "developer")
        web.set_memberships(dev["id"], ["alpha"])
        headers = {"x-csrf-token": client.post("/api/v1/session", json={
            "username": "dev", "password": "longer-password"}).json()["csrf"]}
    response = client.post("/api/v1/projects/alpha/image-build/operations", headers=headers,
        json={"revision": store.export()["revision"],
              "config_revision": sha256(original).hexdigest(),
              "idempotency_key": "unauthorized-build"})
    assert response.status_code == (401 if role == "anonymous" else 403)
    assert path.read_bytes() == original and not runner.calls


def test_environment_guidance_uses_reviewed_recipe_image(tmp_path):
    """@brief A recipe-selected effective image is shown from the normalized plan."""
    import re

    from tests.test_preparation import SourceRunner

    client, _headers, profiles, _store, _service, _runner, _operation, path = image_client(tmp_path)
    text = re.sub(r'^image = ".*"', 'image = "project:1"',
                  path.read_text(encoding="utf-8"), flags=re.MULTILINE)
    text = text.replace('preparation = ""', 'preparation = "prepare.yml#setup@' + "a" * 40 + '"')
    path.write_text(text, encoding="utf-8")
    with TestClient(create_app(profiles.home, probe_runner=SourceRunner())) as current:
        current.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = current.get("/api/v1/projects/alpha/config")
        assert response.status_code == 200, response.text
        assert response.json()["executor_environment"]["image"] == "project:1"
        assert response.json()["execution_plan"]["image_source"] == "recipe"



def test_environment_guidance_does_not_guess_an_invalid_recipe_image(tmp_path):
    """@brief Invalid configured preparation exposes no misleading effective image."""
    from tests.test_preparation import SourceRunner

    _client, _headers, profiles, _store, _service, _runner, _operation, path = (
        image_client(tmp_path))
    text = path.read_text(encoding="utf-8")
    text = text.replace('preparation = ""', 'preparation = "missing.yml#setup@' + "a" * 40 + '"')
    path.write_text(text, encoding="utf-8")
    with TestClient(create_app(profiles.home, probe_runner=SourceRunner())) as current:
        current.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = current.get("/api/v1/projects/alpha/config")
        assert response.status_code == 200
        assert response.json()["executor_environment"]["image"] is None
        assert response.json()["execution_plan"] is None
        assert response.json()["issues"]


# END OF FILE
