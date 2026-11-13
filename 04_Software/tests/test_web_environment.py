#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
"""Offline shared image preparation, concurrent imports and reviewed API boundaries."""

from pathlib import Path
from threading import Event
from time import monotonic

from adore.branding import EGRESS_PROXY_IMAGE, EXECUTOR_BASE_IMAGE
from adore.config import Config
from adore.util import CommandResult
from adore.web.app import create_app
from adore.web.environment import EnvironmentPreparation
from fastapi.testclient import TestClient
import pytest

from tests.test_web_enrollment import _body, _import_body, _login


def config(*, local=False, internet=False, runtime="docker", image=EXECUTOR_BASE_IMAGE):
    result = Config()
    result.executor.provider = "openai"
    result.executor.internet = internet
    result.execution.backend = "local" if local else "container"
    result.container.runtime = runtime
    result.container.image = image
    return result


def finish(read, job):
    deadline = monotonic() + 10
    while job["status"] == "running" and monotonic() < deadline:
        Event().wait(0.01)
        job = read(job["id"])
    assert job["status"] != "running", job
    return job


class Engine:
    def __init__(self, images=()):
        self.images = set(images)
        self.calls = []
        self.building = Event()
        self.release = Event()
        self.release.set()
        self.fail_build = False

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), kwargs))
        if argv[-2:-1] == ["id"]:
            return CommandResult(stdout="1001\n" if argv[-1] == "-u" else "1002\n")
        if "inspect" in argv:
            return CommandResult(exit_code=0 if argv[-1] in self.images else 1)
        if "build" in argv:
            self.building.set()
            assert self.release.wait(5)
            assert kwargs["timeout"] == 1800
            if self.fail_build:
                return CommandResult(exit_code=1, stderr="PRIVATE credential and build output")
            # Native builds contain exactly the four bundled files, no project content.
            if argv[0] != "wsl":
                context = Path(argv[-1])
                assert sorted(p.relative_to(context).as_posix() for p in context.rglob("*")
                              if p.is_file()) == ["Dockerfile.egress-proxy",
                    "Dockerfile.executor-base", "pi/adore-chatgpt.mjs", "pi/adore-guard.ts"]
            self.images.add(argv[argv.index("--tag") + 1])
        return CommandResult()


@pytest.fixture(autouse=True)
def service_identity(monkeypatch):
    monkeypatch.setattr("adore.web.environment.os.getuid", lambda: 1001, raising=False)
    monkeypatch.setattr("adore.web.environment.os.getgid", lambda: 1002, raising=False)


def test_first_import_builds_shared_images_and_later_import_rechecks_without_building(tmp_path):
    engine = Engine()
    pool = EnvironmentPreparation(tmp_path, engine)
    first = finish(pool.read, pool.start(config()))
    assert first["status"] == "ready", first
    assert engine.images == {EXECUTOR_BASE_IMAGE, EGRESS_PROXY_IMAGE}
    builds = [argv for argv, _ in engine.calls if "build" in argv]
    assert len(builds) == 2
    assert "USER_UID=1001" in builds[0] and "USER_GID=1002" in builds[0]
    assert not Path(builds[0][-1]).exists()  # Context cleaned after each build.
    count = len(engine.calls)
    assert finish(pool.read, pool.start(config()))["status"] == "ready"
    assert not any("build" in argv for argv, _ in engine.calls[count:])
    engine.images.remove(EXECUTOR_BASE_IMAGE)
    assert finish(pool.read, pool.start(config()))["status"] == "ready"
    assert sum("build" in argv for argv, _ in engine.calls) == 3
    smoke = next(argv for argv, _ in engine.calls if "run" in argv)
    assert "--pull=never" in smoke and smoke[smoke.index("--network") + 1] == "none"
    assert not any("--volume" in argv or "--env" in argv for argv, _ in engine.calls)


@pytest.mark.parametrize("runtime", ["docker", "wsl -d Ubuntu -- docker"])
def test_simultaneous_imports_share_progress_and_only_build_once(tmp_path, runtime):
    engine = Engine()
    engine.release.clear()
    pool = EnvironmentPreparation(tmp_path, engine)
    first = pool.start(config(runtime=runtime))
    assert engine.building.wait(5)
    second = pool.start(config(runtime=runtime.replace(" -- ", " --exec ")))
    assert second["id"] == first["id"]
    assert second["stage"] == "building_executor"
    engine.release.set()
    assert finish(pool.read, first)["status"] == "ready"
    assert sum("build" in argv for argv, _ in engine.calls) == 2


def test_web_processes_serialize_shared_builds(tmp_path):
    engine = Engine()
    engine.release.clear()
    first = EnvironmentPreparation(tmp_path, engine)
    second = EnvironmentPreparation(tmp_path, engine)
    a = first.start(config())
    assert engine.building.wait(5)
    b = second.start(config())
    engine.release.set()
    assert finish(first.read, a)["status"] == "ready"
    assert finish(second.read, b)["status"] == "ready"
    assert sum("build" in argv for argv, _ in engine.calls) == 2


def test_build_failure_is_redacted_and_retry_reuses_existing_images(tmp_path):
    engine = Engine([EXECUTOR_BASE_IMAGE])
    engine.fail_build = True
    pool = EnvironmentPreparation(tmp_path, engine)
    failed = finish(pool.read, pool.start(config()))
    assert failed["error"] == "environment_build_failed"
    assert "PRIVATE" not in str(failed)
    engine.fail_build = False
    retried = finish(pool.read, pool.start(config()))
    assert retried["status"] == "ready" and retried["id"] != failed["id"]
    assert all(argv[argv.index("--tag") + 1] == EGRESS_PROXY_IMAGE
               for argv, _ in engine.calls if "build" in argv)


@pytest.mark.parametrize("distro", ["Ubuntu", "Team Linux"])
def test_wsl_builds_use_linux_paths_and_selected_distro_identity(tmp_path, distro):
    engine = Engine()
    pool = EnvironmentPreparation(tmp_path, engine)
    result = finish(pool.read, pool.start(config(runtime=f'wsl -d "{distro}" -- docker')))
    assert result["status"] == "ready", result
    assert all(argv[:5] == ["wsl", "-d", distro, "--exec", "docker"]
               for argv, _ in engine.calls if "id" not in argv)
    builds = [argv for argv, _ in engine.calls if "build" in argv]
    assert all("\\" not in argv[-1] and ":" not in argv[-1] for argv in builds)
    assert "USER_UID=1001" in builds[0] and "USER_GID=1002" in builds[0]


@pytest.mark.parametrize("failure", ["exit", "timeout", "invalid-exit", "exception"])
def test_unavailable_daemon_never_builds_or_starts_executor(tmp_path, failure):
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        if failure == "exception":
            raise OSError("PRIVATE")
        return CommandResult(exit_code=1 if failure == "exit" else
                             False if failure == "invalid-exit" else 0,
                             timed_out=failure == "timeout", stderr="PRIVATE")

    pool = EnvironmentPreparation(tmp_path, runner)
    result = finish(pool.read, pool.start(config()))
    assert result["status"] == "failed" and "PRIVATE" not in str(result)
    assert len(calls) == 1 and calls[0][-1] == "info"


def test_native_import_and_missing_custom_image_do_not_build(tmp_path):
    engine = Engine()
    pool = EnvironmentPreparation(tmp_path, engine)
    assert pool.start(config(local=True))["status"] == "ready"
    assert engine.calls == []
    result = finish(pool.read, pool.start(config(image="private/project:latest")))
    assert result["error"] == "executor_image_unavailable"
    assert not any("build" in argv for argv, _ in engine.calls)


@pytest.mark.parametrize("method", ["setup", "import"])
def test_reviewed_environment_routes_preserve_candidate_and_enforce_authorization(tmp_path, method):
    engine = Engine([EXECUTOR_BASE_IMAGE, EGRESS_PROXY_IMAGE])
    app = create_app(tmp_path / "home", environment_runner=engine)
    app.state.web_store.create_user("dev", "longer-password", "developer")
    body = (_body(tmp_path, image=EXECUTOR_BASE_IMAGE) if method == "setup"
            else _import_body(tmp_path))
    if method == "import":
        body["config_text"] = body["config_text"].replace(
            'image = "adore-executor-project:latest"', f'image = "{EXECUTOR_BASE_IMAGE}"')
    preview_route = "setup-preview" if method == "setup" else "import-preview"
    path = f"/api/v1/projects/{method}-environment"
    with TestClient(app) as client:
        headers = _login(client)
        preview = client.post(f"/api/v1/projects/{preview_route}", json=body,
                              headers=headers).json()
        reviewed = {**body, "revision": preview["revision"]}
        assert client.post(path, json=reviewed).status_code == 403
        assert client.post(path, json={**reviewed, "revision": "0" * 64},
                           headers=headers).status_code == 409
        assert engine.calls == []
        started = client.post(path, json=reviewed, headers=headers)
        assert started.status_code == 202, started.text
        def read(job_id):
            return client.get(f"/api/v1/environment-preparations/{job_id}").json()
        done = finish(read, started.json())
        assert done["status"] == "ready", done
        assert not app.state.profiles.list_profiles()
        assert client.get("/api/v1/environment-preparations/unknown").status_code == 404
        client.delete("/api/v1/session", headers=headers)
        assert client.get(f"/api/v1/environment-preparations/{done['id']}").status_code == 401
        developer = _login(client, "dev", "longer-password")
        assert client.post(path, json=reviewed, headers=developer).status_code == 403
        assert client.get(f"/api/v1/environment-preparations/{done['id']}").status_code == 403
