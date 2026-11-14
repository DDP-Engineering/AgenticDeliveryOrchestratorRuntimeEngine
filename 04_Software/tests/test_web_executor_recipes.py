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
@file    test_web_executor_recipes.py
@brief   Prove scoped source management and independent project/job metadata.
@details All requests use temporary stores; external command execution is refused.
"""

# IMPORTS
import base64
from hashlib import sha256
from pathlib import Path
import re

from adore.config import load_config
from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
import pytest

from tests.configuration_client import TestClient


# LOCAL HELPERS
@pytest.fixture
def recipe_project(tmp_path):
    """@brief Build a pair of profiles sharing one unregistered executor image."""
    profiles = ProfileStore(tmp_path / "home")
    source = (Path(__file__).parents[1] / "config.example.toml").read_text()
    source = re.sub(r"^image = .+$", 'image = "sample-executor:1"', source, count=1, flags=re.M)
    for name in ("alpha", "beta"):
        profiles.create(name)
        current = re.sub(
            r"^store_root = .+$",
            f'store_root = "{(profiles.profile_dir(name) / "state").as_posix()}"',
            source,
            flags=re.M,
        )
        profiles.config_path(name).write_text(current, encoding="utf-8")

    def no_command(*args, **kwargs):
        pytest.fail("recipe attachment must not run an external command")

    app = create_app(profiles.home, probe_runner=no_command)
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        yield profiles, client, {"X-CSRF-Token": login.json()["csrf"]}


def payload(
    profiles, *, image="sample-executor:1", source=b'FROM scratch\nCMD ["sleep", "infinity"]\n'
):
    """@brief Encode an explicit current-profile source request without secrets."""
    return {
        "image": image,
        "source": base64.b64encode(source).decode(),
        "revision": sha256(profiles.config_path("alpha").read_bytes()).hexdigest(),
        "expected_digest": None,
    }


# PUBLIC CONTRACT TESTS
def test_recipe_status_and_shared_attachment_preserve_project_state(recipe_project):
    """@brief An attached definition is reused by image without rewriting run/profile data."""
    profiles, client, headers = recipe_project
    url = "/api/v1/projects/alpha/executor-recipe"
    before = profiles.config_path("alpha").read_bytes()
    pending = profiles.profile_dir("alpha") / "pending_config.json"
    pending.write_bytes(b"user-owned-pending-fixture")
    config = load_config(profiles.config_path("alpha"))
    store = StateStore(config.state.store_root, config.agent.slug)
    run = RunState(
        "gitea-example-sample-7",
        7,
        lifecycle="parked-clarification",
        stage="validate",
        iterations=8,
        checkpoint_remote_commit="a" * 40,
    )
    store.save(run)
    state = store.run_dir(run.run_id) / "state.json"
    state_before = state.read_bytes()
    credentials = profiles.profile_dir("alpha") / ".env"
    credentials.write_bytes(b"FIXTURE_KEY=fixture-private\n")
    status = client.get(url)
    assert status.status_code == 200
    assert status.json()["available"] is False
    request = payload(profiles)
    preview = client.post(url + "/preview", json=request, headers=headers)
    assert preview.status_code == 200, preview.text
    assert preview.json()["available"] is True
    assert not (profiles.home / "executor-recipes").exists()
    saved = client.put(url, json=request, headers=headers)
    assert saved.status_code == 200, saved.text
    shared = client.get("/api/v1/projects/beta/executor-recipe").json()
    assert shared["available"] is True
    assert shared["digest"] == saved.json()["digest"]
    assert profiles.config_path("alpha").read_bytes() == before
    assert pending.read_bytes() == b"user-owned-pending-fixture"
    assert state.read_bytes() == state_before
    assert credentials.read_bytes() == b"FIXTURE_KEY=fixture-private\n"
    assert saved.json()["source"] == "managed"
    history = client.get("/api/v1/audit").json()
    events = history["events"] if isinstance(history, dict) else history
    assert any(
        event["action"] == "executor-recipe-saved" and event["result"] == "applied"
        for event in events
    )


def test_recipe_replacement_and_project_revision_are_bound(recipe_project):
    """@brief Competing image replacements and stale project selections fail closed."""
    profiles, client, headers = recipe_project
    url = "/api/v1/projects/alpha/executor-recipe"
    first = client.put(url, json=payload(profiles), headers=headers)
    assert first.status_code == 200
    request = payload(profiles, source=b"FROM scratch\nLABEL change=one\n")
    assert client.put(url, json=request, headers=headers).status_code == 409
    request["expected_digest"] = first.json()["digest"]
    preview = client.post(url + "/preview", json=request, headers=headers)
    assert preview.status_code == 200
    assert client.put(url, json=request, headers=headers).status_code == 200
    assert client.put(url, json=request, headers=headers).status_code == 409
    request["revision"] = "0" * 64
    assert client.post(url + "/preview", json=request, headers=headers).status_code == 409


def test_missing_base_is_attached_in_the_same_project(recipe_project):
    """@brief A retained root becomes exportable when its local base is attached."""
    profiles, client, headers = recipe_project
    url = "/api/v1/projects/alpha/executor-recipe"
    root = client.put(url, json=payload(profiles, source=b"FROM sample-base:1\n"), headers=headers)
    assert root.status_code == 200
    assert root.json()["missing_images"] == ["sample-base:1"]
    failed = client.get("/api/v1/projects/alpha/config/raw?include_build=true")
    assert failed.status_code == 400
    assert failed.json()["detail"]["code"] == "recipe_base_missing"
    base = client.put(url, json=payload(profiles, image="sample-base:1"), headers=headers)
    assert base.status_code == 200
    assert base.json()["available"] is True
    assert client.get("/api/v1/projects/alpha/config/raw?include_build=true").status_code == 200


def test_recipe_mutations_require_csrf_and_a_relevant_image(recipe_project):
    """@brief Invalid transport, unrelated tags and missing CSRF leave no stored sources."""
    profiles, client, headers = recipe_project
    url = "/api/v1/projects/alpha/executor-recipe"
    assert client.put(url, json=payload(profiles)).status_code == 403
    bad = payload(profiles)
    bad["source"] = "not-base64"
    assert client.post(url + "/preview", json=bad, headers=headers).status_code == 400
    assert (
        client.put(url, json=payload(profiles, image="unrelated:1"), headers=headers).status_code
        == 400
    )
    assert not (profiles.home / "executor-recipes").exists()


def test_recipe_anonymous_and_developer_requests_are_refused(recipe_project):
    """@brief Source catalogs are administrator-only, before any recipe read."""
    profiles, client, headers = recipe_project
    url = "/api/v1/projects/alpha/executor-recipe"
    created = client.post(
        "/api/v1/users",
        json={"username": "reader", "password": "test-password", "role": "developer"},
        headers=headers,
    )
    assert created.status_code in (200, 201)
    client.post("/api/v1/session/logout", headers=headers)
    client.cookies.clear()
    assert client.get(url).status_code == 401
    assert client.post(url + "/preview", json=payload(profiles)).status_code == 401
    assert client.put(url, json=payload(profiles)).status_code == 401
    login = client.post("/api/v1/session", json={"username": "reader", "password": "test-password"})
    dev_headers = {"X-CSRF-Token": login.json()["csrf"]}
    assert client.get(url).status_code == 403
    assert (
        client.post(url + "/preview", json=payload(profiles), headers=dev_headers).status_code
        == 403
    )
    assert client.put(url, json=payload(profiles), headers=dev_headers).status_code == 403
    assert not (profiles.home / "executor-recipes").exists()


def test_corrupt_recipe_metadata_keeps_settings_and_standalone_export_available(recipe_project):
    """@brief Recipe failures are scoped to the selected definition and name explicit recovery."""
    from adore.executor_recipes import RecipeStore

    profiles, client, headers = recipe_project
    url = "/api/v1/projects/alpha/executor-recipe"
    assert client.put(url, json=payload(profiles), headers=headers).status_code == 200
    path = RecipeStore(profiles.home).binding_path("sample-executor:1")
    path.write_bytes(b'{"schema":99}')
    result = client.get(url)
    assert result.status_code == 503
    assert result.json()["detail"]["code"] == "recipe_store_corrupt"
    assert result.json()["detail"]["recovery"].endswith(path.name)
    assert client.get("/api/v1/projects/alpha/config").status_code == 200
    raw = client.get("/api/v1/projects/alpha/config/raw?download=true")
    assert raw.status_code == 200
    assert raw.content == profiles.config_path("alpha").read_bytes()
    assert path.read_bytes() == b'{"schema":99}'




@pytest.mark.parametrize("method", ["GET", "POST", "PUT"])
@pytest.mark.parametrize("fault", ["deleted", "oversized", "linked", "changed"])
def test_recipe_final_config_reads_fail_closed(recipe_project, monkeypatch, method, fault):
    """@brief Mid-request config loss, replacement and unsafe files produce typed refusals."""
    import importlib

    module = importlib.import_module("adore.web.app")
    profiles, client, headers = recipe_project
    path = profiles.config_path("alpha")
    request = payload(profiles)
    status = module.recipe_status
    changed = False
    original_link = Path.is_symlink

    def inspect_link(candidate):
        return (changed and candidate == path and fault == "linked") or original_link(candidate)

    def replace_during_status(*args, **kwargs):
        nonlocal changed
        result = status(*args, **kwargs)
        changed = True
        if fault == "deleted":
            path.unlink()
        elif fault == "oversized":
            path.write_bytes(b"#" * (524288 + 1))
        elif fault == "changed":
            path.write_bytes(path.read_bytes() + b"\n# external edit\n")
        return result

    monkeypatch.setattr(Path, "is_symlink", inspect_link)
    monkeypatch.setattr(module, "recipe_status", replace_during_status)
    url = "/api/v1/projects/alpha/executor-recipe" + ("/preview" if method == "POST" else "")
    response = client.request(
        method, url, headers=headers, **({"json": request} if method != "GET" else {})
    )
    assert response.status_code == (409 if fault == "changed" else 503)
    assert response.json()["detail"]["code"] == (
        "stale_config_revision" if fault == "changed" else "config_corrupt"
    )
    assert not (profiles.home / "executor-recipes").exists()


# END OF FILE
