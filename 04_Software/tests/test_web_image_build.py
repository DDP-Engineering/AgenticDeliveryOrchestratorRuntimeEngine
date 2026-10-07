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
import json

from adore.web.app import create_app
from adore.web.commands import CommandWorker
from fastapi.testclient import TestClient
import pytest

from tests.test_image_build import IMAGE_ID, build_project


def image_client(tmp_path):
    """@brief Create an administrator session on a stopped image-build profile."""
    _module, profiles, store, service, runner, operation, path = build_project(tmp_path)
    app = create_app(profiles.home, probe_runner=runner)
    client = TestClient(app)
    login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
    assert login.status_code == 200, login.text
    headers = {"x-csrf-token": login.json()["csrf"]}
    return client, headers, profiles, store, service, runner, operation, path


def test_web_project_image_define_build_review_and_apply(tmp_path):
    """@brief Explicit image selection uses the existing pending review/apply flow."""
    client, headers, profiles, store, _service, runner, _operation, path = image_client(tmp_path)
    base = "/api/v1/projects/alpha"
    current = client.get(base + "/image-build")
    assert current.status_code == 200, current.text
    source = current.json()["draft"]
    revision = sha256(path.read_bytes()).hexdigest()
    queued = client.post(
        base + "/image-build/operations",
        headers=headers,
        json={
            "revision": source["revision"],
            "config_revision": revision,
            "idempotency_key": "build-one",
        },
    )
    assert queued.status_code == 200, queued.text
    image_id = queued.json()["build"]["id"]
    worker = CommandWorker(profiles, client.app.state.web_store, image_runner=runner)
    assert worker.run_pending() == 1
    result = client.get(base + "/image-build/operations/" + image_id).json()
    assert result["build"]["phase"] == "verified", result
    original = path.read_bytes()
    pending = client.post(
        base + "/config/pending",
        headers=headers,
        json={
            "key": "container.image",
            "value": IMAGE_ID,
            "revision": revision,
            "image_build_id": image_id,
        },
    )
    assert pending.status_code == 200, pending.text
    review = pending.json()
    assert review["image_build"]["image_id"] == IMAGE_ID
    assert review["image_build"]["verified_checks"][-1] == "rustc --version"
    assert path.read_bytes() == original
    applied = client.post(
        base + "/config/apply",
        headers=headers,
        json={"candidate_revision": review["candidate_revision"], "base_revision": revision},
    )
    assert applied.status_code == 200, applied.text
    assert f'image = "{IMAGE_ID}"' in path.read_text(encoding="utf-8")
    assert 'required_tool_checks = ["python3 --version", "rustc --version"]' in (
        path.read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "boundary",
    ["csrf", "developer", "other-project", "local", "unpaused", "stale-config", "stale-draft"],
)
def test_web_image_build_rejects_untrusted_mutation(tmp_path, boundary):
    """@brief Authorization and stopped/revision boundaries fail before runtime calls."""
    client, headers, profiles, store, _service, runner, _op, path = image_client(tmp_path)
    revision = sha256(path.read_bytes()).hexdigest()
    draft_revision = store.export()["revision"]
    base = "/api/v1/projects/alpha"
    if boundary == "csrf":
        headers = {}
    elif boundary in {"developer", "other-project"}:
        web = client.app.state.web_store
        user = web.create_user("dev", "longer-password", "developer")
        if boundary == "developer":
            web.set_memberships(user["id"], ["alpha"])
        session = client.post(
            "/api/v1/session", json={"username": "dev", "password": "longer-password"}
        )
        headers = {"x-csrf-token": session.json()["csrf"]}
    elif boundary == "local":
        path.write_text(
            path.read_text(encoding="utf-8").replace('backend = "container"', 'backend = "local"'),
            encoding="utf-8",
        )
        revision = sha256(path.read_bytes()).hexdigest()
    elif boundary == "unpaused":
        from adore.state import StateStore

        StateStore(profiles.load("alpha").store_root).resume()
    elif boundary == "stale-config":
        revision = "e" * 64
    else:
        draft_revision = "e" * 64
    response = client.post(
        base + "/image-build/operations",
        headers=headers,
        json={"revision": draft_revision, "config_revision": revision, "idempotency_key": "bad"},
    )
    assert response.status_code in {400, 403, 404, 409}, response.text
    assert not runner.calls


def test_web_image_apply_rejects_changed_source_and_corrupt_binding(tmp_path):
    """@brief An already reviewed image cannot apply after source or binding drift."""
    client, headers, _profiles, store, service, _runner, operation, path = image_client(tmp_path)
    service.run("alpha", operation["id"])
    base = "/api/v1/projects/alpha"
    revision = sha256(path.read_bytes()).hexdigest()
    pending = client.post(
        base + "/config/pending",
        headers=headers,
        json={
            "key": "container.image",
            "value": IMAGE_ID,
            "revision": revision,
            "image_build_id": operation["id"],
        },
    )
    assert pending.status_code == 200, pending.text
    candidate = pending.json()["candidate_revision"]
    draft = store.export()
    store.save(
        draft["dockerfile"].replace("USER adore", "RUN echo changed\nUSER adore"),
        draft["checks"],
        revision=draft["revision"],
    )
    response = client.post(
        base + "/config/apply", headers=headers, json={"candidate_revision": candidate}
    )
    assert response.status_code == 409, response.text
    assert sha256(path.read_bytes()).hexdigest() == revision
    pending_path = store.profile / "pending_config.json"
    value = json.loads(pending_path.read_text(encoding="utf-8"))
    value["image_build"]["image_id"] = "sha256:" + "f" * 64
    pending_path.write_text(json.dumps(value), encoding="utf-8")
    assert client.get(base + "/config/pending").status_code == 503


def test_image_worker_revocation_and_idempotency_are_durable(tmp_path):
    """@brief Replayed submissions do not allocate builds; revoked actors never execute."""
    client, headers, profiles, store, _service, runner, _op, path = image_client(tmp_path)
    body = {
        "revision": store.export()["revision"],
        "config_revision": sha256(path.read_bytes()).hexdigest(),
        "idempotency_key": "same",
    }
    url = "/api/v1/projects/alpha/image-build/operations"
    first = client.post(url, headers=headers, json=body)
    second = client.post(url, headers=headers, json=body)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(store.operations()) == 2  # Fixture request plus the one queued request.
    web = client.app.state.web_store
    actor = web.authenticate("admin", "admin")
    web.create_user("second_admin", "longer-password", "admin")
    web.disable_user(actor["id"])
    worker = CommandWorker(profiles, web, image_runner=runner)
    assert worker.run_pending() == 1
    assert store.operation(first.json()["build"]["id"])["phase"] == "failed"
    assert not runner.calls


def test_verified_image_review_rejects_recipe_image_conflict(tmp_path):
    """@brief Shared recipe authority rejects conflicting selection without YAML writes."""
    from adore.web.app import create_app
    from adore.web.image_build import ImageBuildService

    from tests.test_preparation import SourceRunner

    client, headers, profiles, store, _service, runner, _op, path = image_client(tmp_path)
    recipe = SourceRunner()
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            'preparation = ""', 'preparation = "prepare.yml#setup@' + "a" * 40 + '"'
        ),
        encoding="utf-8",
    )
    revision = sha256(path.read_bytes()).hexdigest()
    service = ImageBuildService(profiles, runner=runner)
    operation = service.prepare("alpha", store.export()["revision"], revision)
    assert service.run("alpha", operation["id"])["phase"] == "verified"

    def hybrid(argv, **kwargs):
        return recipe(argv, **kwargs) if argv[0] == "git" else runner(argv, **kwargs)

    with TestClient(create_app(profiles.home, probe_runner=hybrid)) as current:
        session = current.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = current.post(
            "/api/v1/projects/alpha/config/pending",
            headers={"x-csrf-token": session.json()["csrf"]},
            json={
                "key": "container.image",
                "value": IMAGE_ID,
                "revision": revision,
                "image_build_id": operation["id"],
            },
        )
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["code"] == "execution_plan_invalid"
    assert sha256(path.read_bytes()).hexdigest() == revision


def test_image_candidate_cannot_lose_its_multi_setting_review_binding(tmp_path):
    """@brief Stripping image evidence cannot hide the accompanying tool-check edit."""
    client, headers, _profiles, _store, service, _runner, operation, path = image_client(tmp_path)
    assert service.run("alpha", operation["id"])["phase"] == "verified"
    base = "/api/v1/projects/alpha"
    staged = client.post(
        base + "/config/pending",
        headers=headers,
        json={
            "key": "container.image",
            "value": IMAGE_ID,
            "revision": sha256(path.read_bytes()).hexdigest(),
            "image_build_id": operation["id"],
        },
    )
    assert staged.status_code == 200, staged.text
    pending_path = path.parent / "pending_config.json"
    value = json.loads(pending_path.read_text(encoding="utf-8"))
    del value["image_build"]
    pending_path.write_text(json.dumps(value), encoding="utf-8")
    original = path.read_bytes()
    assert client.get(base + "/config/pending").status_code == 503
    response = client.post(
        base + "/config/apply",
        headers=headers,
        json={"candidate_revision": value["candidate_revision"]},
    )
    assert response.status_code == 503
    assert path.read_bytes() == original


# END OF FILE
