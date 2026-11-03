#!/usr/bin/env python3
# -*- coding: utf-8 -*-  # noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_executor_environment_choice.py
@brief Choosing where the executor runs from the web interface.
@details Administrators list the server's container images, choose the backend,
         runtime and image at enrollment and in reviewed Settings edits; every
         other environment key and image builds stay outside the web.
"""

from __future__ import annotations

# IMPORTS
from hashlib import sha256
from pathlib import Path

from adore.config import load_config
from adore.profiles import ProfileStore
from adore.state import StateStore
from adore.util import CommandResult
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest

from tests.test_web_enrollment import _body, offline_wizard  # noqa: F401 - autouse fixture

# CONSTANTS
LISTING = (
    "adore-executor-base:pi-0.87.1\n<none>:<none>\nadore-executor-python:pi-0.87.1\n"
    "adore-executor-base:pi-0.87.1\n"
)


# LOCAL HELPERS
class Runner:
    """@brief Records commands and answers `images` with a fixed listing."""

    def __init__(self, listing: str = LISTING, code: int = 0) -> None:
        self.calls: list[list[str]] = []
        self.listing, self.code = listing, code

    def __call__(self, argv, **_kwargs) -> CommandResult:
        self.calls.append(list(argv))
        if len(argv) > 1 and argv[1] == "images":
            return CommandResult(
                argv=list(argv), exit_code=self.code, stdout=self.listing if self.code == 0 else ""
            )
        return CommandResult(argv=list(argv), exit_code=127)


def _project(tmp_path: Path) -> tuple[ProfileStore, Path]:
    """@brief A stopped container profile from the example configuration."""
    profiles = ProfileStore(tmp_path / "home")
    root = tmp_path / "state"
    profiles.create("alpha", store_root=str(root))
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    path.write_text(
        example.read_text(encoding="utf-8").replace(
            'store_root = ".adore"', f'store_root = "{root.as_posix()}"'
        ),
        encoding="utf-8",
    )
    StateStore(root).pause()
    return profiles, path


def _login(client: TestClient, user: str = "admin", password: str = "admin") -> dict:
    """@brief The CSRF header of a fresh session."""
    reply = client.post("/api/v1/session", json={"username": user, "password": password})
    assert reply.status_code == 200, reply.text
    return {"X-CSRF-Token": reply.json()["csrf"]}


# TESTS
@pytest.mark.parametrize("runtime", ["docker", "podman"])
def test_administrators_list_the_server_images(tmp_path, runtime):
    """@brief Tagged images come back sorted and unique; untagged entries are dropped."""
    profiles, _path = _project(tmp_path)
    runner = Runner()
    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        _login(client)
        listed = client.get(f"/api/v1/executor-images?runtime={runtime}")
        assert listed.status_code == 200, listed.text
        assert listed.json() == {
            "runtime": runtime,
            "available": True,
            "images": ["adore-executor-base:pi-0.87.1", "adore-executor-python:pi-0.87.1"],
        }
    assert runner.calls == [[runtime, "images", "--format", "{{.Repository}}:{{.Tag}}"]]


def test_image_listing_fails_soft_and_is_restricted(tmp_path):
    """@brief A broken runtime is unavailable, an unknown one refused, developers excluded."""
    profiles, _path = _project(tmp_path)
    app = create_app(profiles.home, probe_runner=Runner(code=1))
    app.state.web_store.create_user("dev", "longer-password", "developer")
    with TestClient(app) as client:
        _login(client)
        assert client.get("/api/v1/executor-images?runtime=docker").json() == {
            "runtime": "docker",
            "available": False,
            "images": [],
        }
        assert client.get("/api/v1/executor-images?runtime=sh").status_code == 422
        client.delete("/api/v1/session")
        _login(client, "dev", "longer-password")
        assert client.get("/api/v1/executor-images?runtime=docker").status_code == 403


@pytest.mark.parametrize(
    "key,value",
    [("container.image", "adore-executor-base:pi-0.87.1"), ("container.runtime", "podman")],
)
def test_chosen_environment_keys_apply_through_review(tmp_path, key, value):
    """@brief The image and runtime change through a reviewed candidate."""
    profiles, path = _project(tmp_path)
    with TestClient(create_app(profiles.home, probe_runner=Runner())) as client:
        headers = _login(client)
        current = client.get("/api/v1/projects/alpha/config").json()
        assert any(item["key"] == key and item["editable"] for item in current["settings"])
        stage = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={"key": key, "value": value, "revision": current["revision"]},
        )
        assert stage.status_code == 200, stage.text
        applied = client.post(
            "/api/v1/projects/alpha/config/apply",
            headers=headers,
            json={"candidate_revision": stage.json()["candidate_revision"],
                  "base_revision": stage.json()["base_revision"]},
        )
        assert applied.status_code == 200, applied.text
    section, name = key.split(".")
    assert getattr(getattr(load_config(path), section), name) == value


def test_invalid_runtime_candidate_is_refused(tmp_path):
    """@brief Validation still applies to the chosen keys."""
    profiles, path = _project(tmp_path)
    original = path.read_bytes()
    with TestClient(create_app(profiles.home, probe_runner=Runner())) as client:
        headers = _login(client)
        response = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={
                "key": "container.runtime",
                "value": "rm -rf docker",
                "revision": sha256(original).hexdigest(),
            },
        )
        assert response.status_code in (400, 422), response.text
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "key", ["execution.preparation", "worktree.root", "container.uv_cache_volume"]
)
def test_other_environment_keys_stay_external(tmp_path, key):
    """@brief Keys outside the chosen set keep the external-ownership refusal."""
    profiles, path = _project(tmp_path)
    original = path.read_bytes()
    with TestClient(create_app(profiles.home, probe_runner=Runner())) as client:
        headers = _login(client)
        response = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={"key": key, "value": "external", "revision": sha256(original).hexdigest()},
        )
        assert response.status_code == 400, response.text
        assert response.json()["detail"]["code"] == "environment_managed_externally"
    assert path.read_bytes() == original


def test_enrollment_accepts_api_key_mode_without_credential_names(tmp_path):
    """@brief An executor whose image signs in by itself needs no forwarded variables."""
    body = _body(
        tmp_path,
        model="openai-codex/gpt-6-sol",
        env_keys=[],
        image="adore-executor-base:pi-0.87.1",
    )
    with TestClient(create_app(tmp_path / "home", probe_runner=Runner())) as client:
        headers = _login(client)
        preview = client.post("/api/v1/projects/setup-preview", headers=headers, json=body)
        assert preview.status_code == 200, preview.text
        assert preview.json()["structural_valid"], preview.json()
        assert preview.json()["review"]["env_keys"] == []
        assert preview.json()["review"]["image"] == "adore-executor-base:pi-0.87.1"


@pytest.mark.parametrize(
    "key,value",
    [
        ("container.image", "--privileged"),
        ("container.image", "image name:1"),
        ("container.runtime", "sh -c x docker"),
    ],
)
def test_chosen_values_must_be_an_image_or_runtime_command(tmp_path, key, value):
    """@brief An option, spaces or a wrapped shell never reach the run command line."""
    profiles, path = _project(tmp_path)
    original = path.read_bytes()
    with TestClient(create_app(profiles.home, probe_runner=Runner())) as client:
        headers = _login(client)
        response = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={"key": key, "value": value, "revision": sha256(original).hexdigest()},
        )
        assert response.status_code in (400, 422), response.text
        enrolled = client.post(
            "/api/v1/projects/setup-preview",
            headers=headers,
            json=_body(tmp_path, **{key.split(".")[1]: value}),
        )
        assert not enrolled.json()["structural_valid"], enrolled.text
    assert path.read_bytes() == original


def test_wsl_wrapped_runtime_stays_accepted(tmp_path):
    """@brief The documented WSL wrapper remains a valid runtime command."""
    profiles, _path = _project(tmp_path)
    with TestClient(create_app(profiles.home, probe_runner=Runner())) as client:
        headers = _login(client)
        current = client.get("/api/v1/projects/alpha/config").json()
        stage = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={
                "key": "container.runtime",
                "value": "wsl -d Ubuntu-24.04 -- docker",
                "revision": current["revision"],
            },
        )
        assert stage.status_code == 200, stage.text


def test_pending_image_build_binding_is_corrupt_but_discardable(tmp_path):
    """@brief Only an earlier build staged image bindings: refuse it, let it be discarded."""
    import json

    profiles, path = _project(tmp_path)
    original = path.read_bytes()
    config = load_config(path)
    built = "sha256:" + "b" * 64
    checks = list(config.container.required_tool_checks)
    candidate = original.decode("utf-8").replace(
        'image = "' + config.container.image + '"', 'image = "' + built + '"'
    )
    assert candidate.encode() != original
    base = sha256(original).hexdigest()
    pending = {
        "schema": 1,
        "base_revision": base,
        "candidate_revision": sha256(candidate.encode()).hexdigest(),
        "candidate_text": candidate,
        "key": "container.image",
        "value": built,
        "created_at": "2026-10-07T20:00:00+00:00",
        "restart_required": True,
        "image_build": {
            "id": "a" * 32,
            "project_id": profiles.load("alpha").project_id,
            "config_revision": base,
            "runtime": "docker",
            "runtime_identity": "docker",
            "base_id": "sha256:" + "c" * 64,
            "image_id": built,
            "context_sha256": "d" * 64,
            "verified_checks": ["executor --version", *checks],
            "draft_revision": "e" * 64,
        },
    }
    retained = path.parent / "pending_config.json"
    retained.write_text(json.dumps(pending), encoding="utf-8")
    with TestClient(create_app(profiles.home, probe_runner=Runner())) as client:
        headers = _login(client)
        viewed = client.get("/api/v1/projects/alpha/config/pending")
        assert viewed.status_code == 503
        assert viewed.json()["detail"]["code"] == "pending_config_corrupt"
        response = client.post(
            "/api/v1/projects/alpha/config/apply",
            headers=headers,
            json={"candidate_revision": pending["candidate_revision"],
                  "base_revision": pending["base_revision"]},
        )
        assert response.status_code == 503, response.text
        assert path.read_bytes() == original and retained.exists()
        assert client.delete(
            "/api/v1/projects/alpha/config/pending", headers=headers).status_code == 200
    assert not retained.exists() and path.read_bytes() == original


# END OF FILE
