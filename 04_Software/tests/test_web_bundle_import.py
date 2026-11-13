#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
"""
@file    test_web_bundle_import.py
@brief   Prove complete exported ZIP import at the authenticated project boundary.
@details Isolated homes and fake runners preserve exact sources without external tools.
"""

# IMPORTS
import base64
from contextlib import contextmanager
from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZipFile

from adore.build_bundle import export_build_bundle
from adore.config import load_config
from adore.executor_recipes import RecipeStore, resolve_recipe
from adore.profiles import ProfileStore
from adore.recipe_sources import LEGAL_HEADER, Definition, Recipe, parse_recipe, recipe_archive
from adore.state import StateStore
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest


# LOCAL HELPERS
def document(root):
    """@brief Select absolute, unowned server locations and one executor image."""
    text = (Path(__file__).parents[1] / "config.example.toml").read_text(encoding="utf-8")
    for old, new in {
        ".adore": root / "state",
        "../project": root / "repo",
        "worktrees": root / "trees",
        ".adore/metrics.db": root / "state/metrics.db",
        ".adore/metrics/runs.jsonl": root / "state/runs.jsonl",
        ".adore/metrics/stats.html": root / "state/stats.html",
    }.items():
        text = text.replace('"' + old + '"', '"' + new.as_posix() + '"')
    text = text.replace("group/subgroup/project", "group/Bundled-Project")
    text = text.replace('image = "adore-executor-project:latest"', 'image = "bundle-executor:1"')
    return text.replace("\n", "\r\n")


def recipe():
    """@brief Carry an executable context file and a local base in the exported graph."""
    header = LEGAL_HEADER.encode()
    return Recipe(
        "bundle-executor:1",
        {
            "bundle-executor:1": Definition(
                "bundle-executor:1",
                "Dockerfile",
                {
                    "Dockerfile": (header + b"FROM bundle-base:1\nCOPY tool.sh /tool.sh\n", 0o644),
                    "tool.sh": (header + b"printf 'fixture'\n", 0o755),
                },
            ),
            "bundle-base:1": Definition(
                "bundle-base:1",
                "Dockerfile",
                {
                    "Dockerfile": (header + b"FROM ubuntu:22.04\n", 0o644),
                },
            ),
        },
    )


def encoded(source):
    """@brief Transfer the selected bytes through the JSON upload boundary."""
    return {"source": base64.b64encode(source).decode("ascii")}


def headers(client):
    """@brief Authenticate the isolated administrator with its CSRF token."""
    login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
    return {"X-CSRF-Token": login.json()["csrf"]}


def prepared(client, auth, source):
    """@brief Confirm only the exact identity and archive accepted by preview."""
    preview = client.post(
        "/api/v1/projects/import/bundle-preview", json=encoded(source), headers=auth
    )
    assert preview.status_code == 200, preview.text
    value = preview.json()
    assert value["validation"]["structural_valid"]
    return {**encoded(source), **{key: value[key] for key in ("name", "display_name", "revision")}}


# PUBLIC API / CONTRACT TESTS
def test_exported_zip_imports_exact_config_and_complete_sources_together(tmp_path):
    """@brief One confirmation publishes a paused project whose sources re-export exactly."""
    home = tmp_path / "home"
    raw = document(tmp_path).encode("utf-8")
    expected = recipe()
    source = recipe_archive(expected, config_raw=raw)

    def runner(*args, **kwargs):
        """@brief A plain ZIP import never invokes a runtime, forge or other command."""
        raise AssertionError("unexpected external command")

    with TestClient(create_app(home, probe_runner=runner)) as client:
        auth = headers(client)
        response = client.post(
            "/api/v1/projects/import/bundle-preview", json=encoded(source), headers=auth
        )
        assert response.status_code == 200, response.text
        preview = response.json()
        assert preview["validation"]["structural_valid"]
        assert not (home / "executor-recipes").exists()
        assert ProfileStore(home).list_profiles() == []
        body = {
            **encoded(source),
            **{key: preview[key] for key in ("name", "display_name", "revision")},
        }
        created = client.post("/api/v1/projects/import/bundle", json=body, headers=auth)
        assert created.status_code == 200, created.text
        assert created.json()["pickup_state"] == "stopped"
        path = ProfileStore(home).config_path(preview["name"])
        assert path.read_bytes() == raw
        config = load_config(path)
        assert StateStore(Path(config.state.store_root)).is_paused()
        assert resolve_recipe(config, home=home, runner=runner).definitions == expected.definitions
        with ZipFile(BytesIO(export_build_bundle(config, raw, home=home, runner=runner))) as output:
            assert output.read("config.toml") == raw
            assert (
                output.read("context/tool.sh")
                == expected.definitions[expected.image].files["tool.sh"][0]
            )
            assert output.getinfo("context/tool.sh").external_attr >> 16 & 0o777 == 0o755


def test_source_staging_cleanup_failure_never_publishes_a_project(tmp_path, monkeypatch):
    """@brief Finish source staging cleanup before making profile metadata visible."""
    from adore import executor_recipes

    home = tmp_path / "home"
    source = recipe_archive(recipe(), config_raw=document(tmp_path).encode())
    original = executor_recipes.TemporaryDirectory

    @contextmanager
    def failing_cleanup(*args, **kwargs):
        """@brief Simulate a temporary source file held open after staging."""
        with original(*args, **kwargs) as directory:
            yield directory
        raise PermissionError("fixture staging cleanup failure")

    with TestClient(create_app(home)) as client:
        auth = headers(client)
        body = prepared(client, auth, source)
        monkeypatch.setattr(executor_recipes, "TemporaryDirectory", failing_cleanup)
        result = client.post("/api/v1/projects/import/bundle", json=body, headers=auth)
        assert result.status_code == 503, result.text
        assert not ProfileStore(home).exists(body["name"])
        for image in recipe().definitions:
            assert RecipeStore(home).binding_digest(image) is None


def test_conflicting_root_recipe_is_a_typed_conflict_and_is_preserved(tmp_path):
    """@brief Import is not authority to replace shared existing source definitions."""
    home = tmp_path / "home"
    graph = recipe()
    changed = dict(graph.definitions)
    root = changed[graph.image]
    changed[graph.image] = replace(root, files={**root.files, "tool.sh": (b"# other\n", 0o755)})
    store = RecipeStore(home)
    digest = store.put(replace(graph, definitions=changed), expected_digest=None)
    source = recipe_archive(graph, config_raw=document(tmp_path).encode())
    with TestClient(create_app(home)) as client:
        result = client.post(
            "/api/v1/projects/import/bundle-preview", json=encoded(source), headers=headers(client)
        )
        assert result.status_code == 409, result.text
        assert result.json()["detail"]["code"] == "recipe_import_conflict"
        assert store.binding_digest(graph.image) == digest
        assert ProfileStore(home).list_profiles() == []


@pytest.mark.parametrize("route", ["bundle-preview", "bundle"])
def test_bundle_routes_authorize_before_decoding_or_retaining_sources(tmp_path, monkeypatch, route):
    """@brief Anonymous, developer and invalid-CSRF inputs cannot reach archive parsing."""
    import adore.web.app as api

    def refuse(*args, **kwargs):
        """@brief A rejected caller never crosses the archive trust boundary."""
        raise AssertionError("unexpected source access")

    monkeypatch.setattr(api, "read_project_bundle", refuse)
    home = tmp_path / "home"
    app = create_app(home)
    app.state.web_store.create_user("dev", "fixture-password", "developer")
    body = {"source": "not-base64", "name": "fixture", "revision": "0" * 64}
    with TestClient(app) as client:
        path = "/api/v1/projects/import/" + route
        assert client.post(path, json=body).status_code == 401
        auth = headers(client)
        assert client.post(path, json=body).status_code == 403
        assert client.post(path, json=body, headers={"X-CSRF-Token": "bad"}).status_code == 403
        client.delete("/api/v1/session", headers=auth)
        login = client.post(
            "/api/v1/session", json={"username": "dev", "password": "fixture-password"}
        )
        assert (
            client.post(path, json=body, headers={"X-CSRF-Token": login.json()["csrf"]}).status_code
            == 403
        )
        assert not (home / "executor-recipes").exists()
        assert ProfileStore(home).list_profiles() == []


@pytest.mark.parametrize("source", ["!invalid-base64!", "é", "eA=="])
def test_invalid_encoded_archive_is_typed_and_never_reflected(tmp_path, source):
    """@brief Bad transport and non-ZIP bytes do not create source/catalog state."""
    home = tmp_path / "home"
    with TestClient(create_app(home)) as client:
        result = client.post(
            "/api/v1/projects/import/bundle-preview",
            json={"source": source},
            headers=headers(client),
        )
        assert result.status_code == 400, result.text
        assert source not in result.text
        assert not (home / "executor-recipes").exists()


@pytest.mark.parametrize("bad", ["image", "native", "secret", "malformed_toml"])
def test_archive_config_mismatch_or_invalid_toml_has_no_publication(tmp_path, bad):
    """@brief Archive metadata never bypasses native TOML configuration checks."""
    home = tmp_path / "home"
    text = document(tmp_path)
    if bad == "image":
        text = text.replace('image = "bundle-executor:1"', 'image = "different:1"')
    elif bad == "native":
        text = text.replace('backend = "container"', 'backend = "local"')
        text = re.sub(r"required_tool_checks\s*=\s*\[[\s\S]*?\]", "required_tool_checks = []", text)
    elif bad == "secret":
        text += '\n[private]\napi_key="fixture-private-secret"\n'
    else:
        text += "\n[broken\n"
    source = recipe_archive(recipe(), config_raw=text.encode())
    with TestClient(create_app(home)) as client:
        result = client.post(
            "/api/v1/projects/import/bundle-preview", json=encoded(source), headers=headers(client)
        )
        if bad in {"image", "native"}:
            assert result.status_code == 400, result.text
            assert result.json()["detail"]["code"] == "bundle_image_mismatch"
        else:
            assert result.status_code == 200, result.text
            assert not result.json()["validation"]["structural_valid"]
        assert "fixture-private-secret" not in result.text
        assert ProfileStore(home).list_profiles() == []


@pytest.mark.parametrize("bad", ["extra", "oversized", "unicode"])
def test_bundle_request_shape_limits_and_unicode_fail_closed(tmp_path, bad):
    """@brief Request validation never leaks input or creates an import on malformed metadata."""
    home = tmp_path / "home"
    body = encoded(recipe_archive(recipe(), config_raw=document(tmp_path).encode()))
    if bad == "extra":
        body["config_text"] = "fixture-private-secret"
    elif bad == "oversized":
        body["source"] = "A" * (18 * 1024 * 1024 * 4 // 3 + 5)
    else:
        body["description"] = "\ud800"
    with TestClient(create_app(home)) as client:
        result = client.post(
            "/api/v1/projects/import/bundle-preview",
            content=json.dumps(body),
            headers={**headers(client), "Content-Type": "application/json"},
        )
        assert result.status_code == 422, result.text
        assert result.json()["detail"]["code"] == "invalid_request"
        assert "fixture-private-secret" not in result.text
        assert not (home / "executor-recipes").exists()
        assert not (home / "executor-recipes").exists()


@pytest.mark.parametrize("change", ["archive", "base_binding", "ownership"])
def test_confirmation_binds_archive_associations_and_server_ownership(tmp_path, change):
    """@brief Confirmation refuses any changed evidence observed by automatic validation."""
    home = tmp_path / "home"
    graph = recipe()
    source = recipe_archive(graph, config_raw=document(tmp_path).encode())
    with TestClient(create_app(home)) as client:
        auth = headers(client)
        body = prepared(client, auth, source)
        if change == "archive":
            changed = dict(graph.definitions)
            root = changed[graph.image]
            changed[graph.image] = replace(
                root, files={**root.files, "tool.sh": (b"# new\n", 0o755)}
            )
            body.update(
                encoded(
                    recipe_archive(
                        replace(graph, definitions=changed), config_raw=document(tmp_path).encode()
                    )
                )
            )
        elif change == "base_binding":
            RecipeStore(home).put(
                parse_recipe(b"FROM ubuntu:24.04\n", "bundle-base:1"), expected_digest=None
            )
        else:
            ProfileStore(home).create("other", store_root=str(tmp_path / "state/child"))
        result = client.post("/api/v1/projects/import/bundle", json=body, headers=auth)
        assert result.status_code == 409, result.text
        assert result.json()["detail"]["code"] == "stale_import_preview"
        assert not ProfileStore(home).exists(body["name"])
        assert RecipeStore(home).binding_digest(graph.image) is None


@pytest.mark.parametrize("failure", ["source_write", "profile_write", "late_ownership"])
def test_failed_publication_rolls_back_new_bindings_and_preserves_external_state(
    tmp_path, monkeypatch, failure
):
    """@brief Neither write faults nor a late native ownership conflict leave a partial project."""
    from adore import executor_recipes

    home = tmp_path / "home"
    store = RecipeStore(home)
    source = recipe_archive(recipe(), config_raw=document(tmp_path).encode())
    create = ProfileStore.create
    acquire = StateStore.acquire_lock
    replace_file = executor_recipes.os.replace

    def fail_create(profiles, name, **kwargs):
        """@brief Fail only the new imported profile, preserving unrelated metadata."""
        if name == "bundled-project":
            raise PermissionError("fixture profile write")
        return create(profiles, name, **kwargs)

    def fail_write(source, target):
        """@brief Fail after a supplemental binding but before the root association."""
        if Path(target) == store.binding_path("bundle-executor:1"):
            raise PermissionError("fixture binding write")
        return replace_file(source, target)

    def late_owner(state, *args, **kwargs):
        """@brief A competing profile acquires nested ownership at the native lock boundary."""
        if state.root == tmp_path / "state":
            create(ProfileStore(home), "concurrent", store_root=str(tmp_path / "state/child"))
        return acquire(state, *args, **kwargs)

    with TestClient(create_app(home)) as client:
        auth = headers(client)
        body = prepared(client, auth, source)
        if failure == "source_write":
            monkeypatch.setattr(executor_recipes.os, "replace", fail_write)
        elif failure == "profile_write":
            monkeypatch.setattr(ProfileStore, "create", fail_create)
        else:
            monkeypatch.setattr(StateStore, "acquire_lock", late_owner)
        result = client.post("/api/v1/projects/import/bundle", json=body, headers=auth)
        assert result.status_code >= 400, result.text
        assert not ProfileStore(home).exists(body["name"])
        assert not StateStore(tmp_path / "state").is_paused()
        for image in recipe().definitions:
            assert store.binding_digest(image) is None
        if failure == "late_ownership":
            assert ProfileStore(home).exists("concurrent")


@pytest.mark.parametrize("existing", ["identical_root", "different_base"])
def test_import_reuses_identical_roots_and_preserves_existing_base_associations(tmp_path, existing):
    """@brief Embedded source snapshots do not replace another project's base binding."""
    home = tmp_path / "home"
    graph = recipe()
    store = RecipeStore(home)
    if existing == "identical_root":
        digest = store.put(graph, expected_digest=None)
        image = graph.image
    else:
        image = "bundle-base:1"
        digest = store.put(parse_recipe(b"FROM ubuntu:24.04\n", image), expected_digest=None)
    with TestClient(create_app(home)) as client:
        auth = headers(client)
        body = prepared(client, auth, recipe_archive(graph, config_raw=document(tmp_path).encode()))
        result = client.post("/api/v1/projects/import/bundle", json=body, headers=auth)
        assert result.status_code == 200, result.text
        assert store.binding_digest(image) == digest
        config = load_config(ProfileStore(home).config_path(body["name"]))
        assert resolve_recipe(config, home=home).definitions == graph.definitions


@pytest.mark.parametrize("corrupt", ["binding", "object"])
def test_corrupt_recipe_storage_is_refused_without_repair(tmp_path, corrupt):
    """@brief Current-schema corrupt storage is preserved for explicit operator action."""
    home = tmp_path / "home"
    graph = recipe()
    store = RecipeStore(home)
    digest = store.put(graph, expected_digest=None)
    target = (
        store.binding_path(graph.image)
        if corrupt == "binding"
        else store.root / "objects" / (digest + ".zip")
    )
    target.write_bytes(b"{broken")
    with TestClient(create_app(home)) as client:
        result = client.post(
            "/api/v1/projects/import/bundle-preview",
            headers=headers(client),
            json=encoded(recipe_archive(graph, config_raw=document(tmp_path).encode())),
        )
        assert result.status_code == 503, result.text
        assert result.json()["detail"]["code"] == "recipe_store_corrupt"
        assert target.read_bytes() == b"{broken"
        assert ProfileStore(home).list_profiles() == []


def test_catalog_lock_contention_does_not_publish_or_release_another_lock(tmp_path):
    """@brief Source mutation ownership is required in addition to the project locks."""
    home = tmp_path / "home"
    source = recipe_archive(recipe(), config_raw=document(tmp_path).encode())
    with TestClient(create_app(home)) as client:
        auth = headers(client)
        body = prepared(client, auth, source)
        lock = StateStore(home / "executor-recipes", "adore-recipes")
        assert lock.acquire_lock()
        try:
            before = lock.lock_path.read_bytes()
            result = client.post("/api/v1/projects/import/bundle", json=body, headers=auth)
            assert result.status_code == 409, result.text
            assert lock.lock_path.read_bytes() == before
            assert not ProfileStore(home).exists(body["name"])
            assert RecipeStore(home).binding_digest(recipe().image) is None
        finally:
            lock.release_lock()


def test_failed_source_rollback_escalates_without_erasing_existing_data(tmp_path, monkeypatch):
    """@brief A filesystem rollback failure reports uncertainty instead of false import success."""
    home = tmp_path / "home"
    store = RecipeStore(home)
    source = recipe_archive(recipe(), config_raw=document(tmp_path).encode())
    create = ProfileStore.create
    unlink = Path.unlink

    def fail_create(profiles, name, **kwargs):
        """@brief Fail only this new profile's publication."""
        if name == "bundled-project":
            raise PermissionError("fixture publication")
        return create(profiles, name, **kwargs)

    def fail_rollback(path, *args, **kwargs):
        """@brief Preserve a still-valid binding when the disk refuses its removal."""
        if path == store.binding_path(recipe().image):
            raise PermissionError("fixture rollback")
        return unlink(path, *args, **kwargs)

    with TestClient(create_app(home)) as client:
        auth = headers(client)
        body = prepared(client, auth, source)
        monkeypatch.setattr(ProfileStore, "create", fail_create)
        monkeypatch.setattr(Path, "unlink", fail_rollback)
        result = client.post("/api/v1/projects/import/bundle", json=body, headers=auth)
        assert result.status_code == 503, result.text
        assert result.json()["detail"]["code"] == "recipe_write_failed"
        assert not ProfileStore(home).exists(body["name"])
        assert store.get(recipe().image).definitions == recipe().definitions


@pytest.mark.parametrize("boundary", ["project", "enrollment"])
def test_final_unlock_failure_does_not_leave_a_profile_without_sources(
    tmp_path, monkeypatch, boundary
):
    """@brief Project and enrollment cleanup remain inside the coordinated rollback boundary."""
    home = tmp_path / "home"
    source = recipe_archive(recipe(), config_raw=document(tmp_path).encode())
    release = StateStore.release_lock
    failed = False

    def failed_unlock(state):
        """@brief Simulate an error reported at the final project lock release."""
        nonlocal failed
        release(state)
        target = tmp_path / "state" if boundary == "project" else home / "web-enrollment"
        if state.root == target and not failed:
            failed = True
            raise PermissionError("fixture final project unlock")

    with TestClient(create_app(home)) as client:
        auth = headers(client)
        body = prepared(client, auth, source)
        monkeypatch.setattr(StateStore, "release_lock", failed_unlock)
        result = client.post("/api/v1/projects/import/bundle", json=body, headers=auth)
        assert result.status_code >= 400, result.text
        assert not ProfileStore(home).exists(body["name"])
        assert not StateStore(tmp_path / "state").is_paused()
        for image in recipe().definitions:
            assert RecipeStore(home).binding_digest(image) is None
        page = client.get("/api/v1/audit").json()
        events = page["events"] if isinstance(page, dict) else page
        assert not any(
            event["action"] == "project-imported" and event["result"] == "applied"
            for event in events
        )


def test_bundle_environment_preparation_binds_review_and_does_not_publish(tmp_path):
    """ZIP preparation requires CSRF and exact review before any runtime work."""
    from adore.util import CommandResult

    from tests.test_web_environment import finish

    calls = []
    def environment_runner(argv, **kwargs):
        calls.append(argv)
        return CommandResult()

    home = tmp_path / "home"
    source = recipe_archive(recipe(), config_raw=document(tmp_path).encode("utf-8"))
    with TestClient(create_app(home, environment_runner=environment_runner)) as client:
        auth = headers(client)
        body = prepared(client, auth, source)
        path = "/api/v1/projects/import/bundle-environment"
        assert client.post(path, json=body).status_code == 403
        stale = client.post(path, json={**body, "revision": "0" * 64}, headers=auth)
        assert stale.status_code == 409
        assert not calls
        response = client.post(path, json=body, headers=auth)
        assert response.status_code == 202, response.text
        job = finish(lambda job_id: client.get(
            "/api/v1/environment-preparations/" + job_id).json(), response.json())
        assert job["status"] == "ready", job
        assert calls
        assert ProfileStore(home).list_profiles() == []
        assert not (home / "executor-recipes").exists()
