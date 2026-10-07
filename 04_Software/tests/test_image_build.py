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
@file    test_image_build.py
@brief   Offline public project-image artifact and runtime contract tests.
@details Fakes every runtime boundary; no actual image builds or downloads.
"""

# IMPORTS
import importlib
import importlib.util
import json
from pathlib import Path

import pytest

# CONSTANTS
PROJECT = "a" * 32
BASE_ID = "sha256:" + "b" * 64
IMAGE_ID = "sha256:" + "c" * 64
CONTAINER_ID = "d" * 64


# LOCAL HELPERS
def api():
    """@brief Observe the new public module without an incidental import failure."""
    assert importlib.util.find_spec("adore.web.image_build") is not None, (
        "Project-owned Dockerfile artifact contract is missing"
    )
    return importlib.import_module("adore.web.image_build")


# PUBLIC API TESTS
def test_project_image_artifact_round_trip_and_revision(tmp_path):
    """@brief A legal non-root source/check snapshot survives export and edits."""
    module = api()
    store = module.ImageBuildStore(tmp_path / "profile", PROJECT)
    source = module.dockerfile_template()
    assert "Copyright (c) 2026 DDP Engineering" in source
    assert source.rstrip().endswith("USER adore")
    draft = store.save(source, ["python3 --version", "node --version"], revision="")
    assert store.read() == draft
    assert store.export()["dockerfile"] == source
    assert draft["network"] == "none"
    assert len(draft["revision"]) == 64
    changed = store.save(
        source.replace("USER adore", "RUN echo installed\nUSER adore"),
        draft["checks"],
        revision=draft["revision"],
    )
    assert changed["revision"] != draft["revision"]
    with pytest.raises(module.ImageBuildError, match="stale"):
        store.save(source, [], revision=draft["revision"])
    assert store.read() == changed


@pytest.mark.parametrize(
    "addition",
    [
        "COPY . /app\n",
        "ADD https://example.test/file /app\n",
        "ONBUILD RUN echo hi\n",
        "RUN --mount=type=bind,target=/host echo hi\n",
        "RUN --network=host echo hi\n",
        "FROM other:latest\n",
        "\x00",
        "ENV API_TOKEN=literal-secret\n",
        "RUN curl https://name:password@example.test/\n",
        "RUN echo \ud800\n",
        "RUN " + "x" * 65536 + "\n",
    ],
    ids=[
        "copy",
        "remote-add",
        "onbuild",
        "mount",
        "host-network",
        "extra-base",
        "nul",
        "credential",
        "url-credential",
        "unicode",
        "oversize",
    ],
)
def test_project_image_refuses_unsupported_or_corrupt_source(tmp_path, addition):
    """@brief Unsupported context/secrets/bytes fail before retaining input."""
    module = api()
    store = module.ImageBuildStore(tmp_path / "profile", PROJECT)
    with pytest.raises(module.ImageBuildError):
        store.save(module.dockerfile_template() + addition, [], revision="")
    assert store.read() is None


@pytest.mark.parametrize(
    "changes",
    [
        {"checks": ["echo x; cat /home/file"]},
        {"checks": [""]},
        {"checks": ["x" * 513]},
        {"checks": ["echo x"] * 33},
        {"network": "host"},
        {"timeout_seconds": True},
        {"timeout_seconds": 1801},
        {"memory_mib": 1},
        {"memory_mib": "1024"},
    ],
)
def test_project_image_refuses_invalid_checks_or_policy(tmp_path, changes):
    """@brief Human policy/check inputs have closed types and enforceable bounds."""
    module = api()
    store = module.ImageBuildStore(tmp_path / "profile", PROJECT)
    body = {"checks": ["python3 --version"], **changes}
    with pytest.raises(module.ImageBuildError):
        store.save(module.dockerfile_template(), revision="", **body)
    assert store.read() is None


@pytest.mark.parametrize("corruption", ["identity", "checksum", "extra", "duplicates"])
def test_project_image_refuses_corrupt_persisted_artifact(tmp_path, corruption):
    """@brief Persisted artifact corruption cannot become a fresh empty draft."""
    module = api()
    store = module.ImageBuildStore(tmp_path / "profile", PROJECT)
    draft = store.save(module.dockerfile_template(), [], revision="")
    if corruption == "identity":
        draft["project_id"] = "b" * 32
    elif corruption == "checksum":
        draft["dockerfile"] += "# changed\n"
    elif corruption == "extra":
        draft["context_path"] = "/home"
    path = tmp_path / "profile" / "image-build" / "draft.json"
    text = json.dumps(draft)
    if corruption == "duplicates":
        text = text.replace('"schema": 1', '"schema": 1, "schema": 1')
    path.write_text(text, encoding="utf-8")
    with pytest.raises(module.ImageBuildError):
        store.read()


def test_project_image_refuses_linked_storage_and_known_credentials(tmp_path):
    """@brief Linked artifact ownership and credential retention fail closed."""
    module = api()
    store = module.ImageBuildStore(tmp_path / "profile", PROJECT, secrets=["private-value"])
    with pytest.raises(module.ImageBuildError):
        store.save(
            module.dockerfile_template().replace(
                "USER adore", "RUN echo private-value\nUSER adore"
            ),
            [],
            revision="",
        )
    profile = tmp_path / "profile"
    profile.mkdir(exist_ok=True)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    try:
        (profile / "image-build").symlink_to(foreign, target_is_directory=True)
    except OSError:
        pytest.skip("platform denies symlink creation")
    with pytest.raises(module.ImageBuildError):
        store.save(module.dockerfile_template(), [], revision="")
    assert not list(foreign.iterdir())


class ImageRuntime:
    """@brief Closed offline runtime responses and observable owned effects."""

    def __init__(self, failure=""):
        self.calls, self.failure, self.labels = [], failure, {}
        self.container = ""
        self.on_build = None

    def __call__(self, argv, *, cwd=None, timeout=None, env=None):
        """@brief Simulate the selected runtime without real tools/downloads."""
        from adore.util import CommandResult

        argv = list(argv)
        self.calls.append((argv, cwd, timeout, env))
        assert timeout is not None and 0 < timeout <= 1800
        assert env is not None and "GITEA_TOKEN" not in env and "OPENAI_API_KEY" not in env
        result = CommandResult(argv=argv)
        if "info" in argv:
            value = {
                "ID": "owned-daemon",
                "OSType": "linux",
                "MemoryLimit": True,
                "CpuCfsQuota": True,
                "CpuCfsPeriod": True,
            }
            if self.failure == "capabilities":
                value["MemoryLimit"] = False
            result.stdout = json.dumps(value)
        elif "build" in argv:
            source = (Path(cwd) / "Dockerfile").read_text(encoding="utf-8")
            assert f"FROM {BASE_ID}" in source
            assert set(path.name for path in Path(cwd).iterdir()) == {"Dockerfile"}
            assert "--network" in argv and argv[argv.index("--network") + 1] == "none"
            assert "--memory" in argv and "--cpu-quota" in argv and "--force-rm" in argv
            for index, token in enumerate(argv):
                if token == "--label":
                    key, value = argv[index + 1].split("=", 1)
                    self.labels[key] = value
            if self.on_build:
                self.on_build()
            result.stdout = "building project tools\nBearer private-value\n"
            if self.failure == "build":
                result.exit_code = 7
            if self.failure == "timeout":
                result.exit_code, result.timed_out = 124, True
        elif "image" in argv and "inspect" in argv:
            if "--format" in argv:
                result.stdout = BASE_ID if argv[-1].startswith("adore-executor-base:") else IMAGE_ID
                if self.failure == "identity" and not argv[-1].startswith("adore-executor-base:"):
                    result.stdout = "unexpected-runtime-output"
            else:
                result.stdout = json.dumps(
                    [
                        {
                            "Id": IMAGE_ID,
                            "Config": {
                                "User": "root" if self.failure == "user" else "adore",
                                "Labels": self.labels,
                            },
                        }
                    ]
                )
                if self.failure == "metadata":
                    result.stdout = '[{"Id": "bad"}, {"Id": "other"}]'
        elif "run" in argv:
            self.container = argv[argv.index("--name") + 1]
            result.stdout = CONTAINER_ID
        elif "inspect" in argv:
            result.stdout = json.dumps(
                [
                    {
                        "Id": CONTAINER_ID,
                        "Image": IMAGE_ID,
                        "Name": "/" + self.container,
                        "State": {"Status": "running"},
                    }
                ]
            )
        elif "exec" in argv:
            result.stdout = "tool version 1\n"
            if self.failure == "tools" and "rustc" in argv:
                result.exit_code = 1
        elif "rm" in argv:
            assert argv[-1] == self.container
            result.stdout = self.container
        else:
            pytest.fail("unexpected image runtime call: " + repr(argv))
        return result


def build_project(tmp_path, failure=""):
    """@brief Make a stopped container profile and injectable image service."""
    from hashlib import sha256

    from adore.profiles import ProfileStore
    from adore.state import StateStore

    module = api()
    profiles = ProfileStore(tmp_path / "home")
    root = tmp_path / "state"
    project = profiles.create("alpha", store_root=str(root))
    path = profiles.config_path("alpha")
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    path.write_text(
        example.read_text(encoding="utf-8").replace(
            'store_root = ".adore"', f'store_root = "{root.as_posix()}"'
        ),
        encoding="utf-8",
    )
    StateStore(root).pause()
    store = module.ImageBuildStore(
        profiles.profile_dir("alpha"), project.project_id, secrets=["private-value"]
    )
    draft = store.save(
        module.dockerfile_template(), ["python3 --version", "rustc --version"], revision=""
    )
    assert hasattr(module, "ImageBuildService"), "Durable project image build pipeline is missing"
    runner = ImageRuntime(failure)
    service = module.ImageBuildService(profiles, runner=runner)
    operation = service.prepare("alpha", draft["revision"], sha256(path.read_bytes()).hexdigest())
    return module, profiles, store, service, runner, operation, path


def test_project_image_build_verifies_owned_identity_and_tools(tmp_path):
    """@brief A unique bounded build verifies exact image/tools without config mutation."""
    _module, _profiles, store, service, runner, operation, path = build_project(tmp_path)
    original = path.read_bytes()
    seen = []

    def observe_build():
        from hashlib import sha256

        seen.append(
            (
                store.operation(operation["id"])["phase"],
                sha256(
                    store.owned_path(operation["id"] + "/context/Dockerfile").read_bytes()
                ).hexdigest(),
            )
        )

    runner.on_build = observe_build
    finished = service.run("alpha", operation["id"])
    assert finished["phase"] == "verified", finished
    assert seen == [("building", finished["context_sha256"])]
    assert finished["image_id"] == IMAGE_ID
    assert finished["base_id"] == BASE_ID
    assert finished["verified_checks"] == [
        "opencode --version",
        "python3 --version",
        "rustc --version",
    ]
    assert len(finished["context_sha256"]) == 64
    assert "private-value" not in store.log(operation["id"])
    assert path.read_bytes() == original
    assert not store.owned_path(operation["id"] + "/context").exists()
    assert runner.calls[-1][0][-1] == runner.container
    assert not any("prune" in call[0] or "push" in call[0] for call in runner.calls)


@pytest.mark.parametrize(
    "failure", ["build", "timeout", "identity", "metadata", "user", "tools", "capabilities"]
)
def test_project_image_build_failure_never_selects_image(tmp_path, failure):
    """@brief Bad runtime/check outcomes remain terminal evidence and preserve config."""
    _module, _profiles, store, service, runner, operation, path = build_project(tmp_path, failure)
    original = path.read_bytes()
    finished = service.run("alpha", operation["id"])
    assert finished["phase"] in {"failed", "uncertain"}
    assert finished["error"]
    assert store.operation(operation["id"])["phase"] == finished["phase"]
    assert path.read_bytes() == original
    assert not any("prune" in call[0] for call in runner.calls)


def test_project_image_cancel_before_start_runs_no_commands(tmp_path):
    """@brief A queued cancel has a deterministic side-effect-free terminal result."""
    _module, _profiles, store, service, runner, operation, _path = build_project(tmp_path)
    store.cancel(operation["id"])
    assert service.run("alpha", operation["id"])["phase"] == "cancelled"
    assert runner.calls == []


def test_project_image_cancel_during_build_never_claims_unconfirmed_remote_cleanup(tmp_path):
    """@brief Unconfirmed daemon cancellation is uncertain and cannot be applied."""
    _module, _profiles, store, service, runner, operation, path = build_project(tmp_path)
    original = path.read_bytes()
    runner.on_build = lambda: store.cancel(operation["id"])
    result = service.run("alpha", operation["id"])
    assert result["phase"] == "uncertain"
    assert result["error"] == "image_cancel_unconfirmed"
    assert path.read_bytes() == original
    assert not any("run" in call[0] for call in runner.calls)


def test_project_image_restart_never_replays_an_interrupted_build(tmp_path):
    """@brief A persisted in-flight phase recovers terminally, never as a new build."""
    module, profiles, store, service, runner, operation, _path = build_project(tmp_path)
    service.set_phase("alpha", operation["id"], "building")
    recovered = module.ImageBuildService(profiles, runner=runner).recover("alpha", operation["id"])
    assert recovered["phase"] == "interrupted"
    assert not any("build" in call[0] for call in runner.calls)
    with pytest.raises(module.ImageBuildError):
        service.run("alpha", operation["id"])


@pytest.mark.parametrize(
    "corrupt",
    [
        {"phase": []},
        {"host": {}},
        {"resource": {}},
        {"image_id": 42},
        {"verified_checks": [None]},
        {"config_revision": "bad"},
        {"extra": True},
    ],
)
def test_image_operation_corruption_fails_closed(tmp_path, corrupt):
    """@brief Restart/status cannot guess missing or malformed operation evidence."""
    module, _profiles, store, service, runner, operation, _path = build_project(tmp_path)
    value = store.read_json(operation["id"] + "/record.json")
    value.update(corrupt)
    store.write_json(operation["id"] + "/record.json", value)
    with pytest.raises(module.ImageBuildError):
        service.recover("alpha", operation["id"])
    assert not runner.calls


def test_image_retention_revision_and_foreign_identity_fail_before_commands(tmp_path):
    """@brief Unique builds are bounded and cannot cross draft/config/project identity."""
    module, profiles, store, service, runner, operation, path = build_project(tmp_path)
    from hashlib import sha256

    revision = sha256(path.read_bytes()).hexdigest()
    with pytest.raises(module.ImageBuildError):
        service.prepare("alpha", "e" * 64, revision)
    for _ in range(module.MAX_OPERATIONS - 1):
        service.prepare("alpha", store.export()["revision"], revision)
    with pytest.raises(module.ImageBuildError, match="image_retention_full"):
        service.prepare("alpha", store.export()["revision"], revision)
    foreign = module.ImageBuildStore(profiles.profile_dir("alpha"), "f" * 32)
    with pytest.raises(module.ImageBuildError):
        foreign.operation(operation["id"])
    path.write_text(path.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    assert service.run("alpha", operation["id"])["phase"] == "failed"
    assert not runner.calls


@pytest.mark.parametrize(
    "runtime",
    ["docker --host other", "podman --remote", "wsl --user root -- docker", "sh -c docker", ""],
)
def test_image_runtime_options_are_closed(runtime):
    """@brief Runtime prefixes cannot introduce unreviewed remote/context wrappers."""
    with pytest.raises(api().ImageBuildError):
        api().ImageBuildService.runtime_argv(runtime)


def test_image_runtime_controlled_environment_and_project_secret_refusal(tmp_path, monkeypatch):
    """@brief Profile and service credentials are rejected/redacted, never forwarded."""
    monkeypatch.setenv("GITEA_TOKEN", "private-forge-token")
    monkeypatch.setenv("OPENAI_API_KEY", "private-model-token")
    module, profiles, store, service, runner, operation, _path = build_project(tmp_path)
    (profiles.profile_dir("alpha") / ".env").write_text(
        "OPENAI_API_KEY=private-project-key\n", encoding="utf-8"
    )
    secret_store = service.store("alpha")
    draft = secret_store.export()
    with pytest.raises(module.ImageBuildError):
        secret_store.save(
            draft["dockerfile"].replace("USER adore", "RUN echo private-project-key\nUSER adore"),
            [],
            revision=draft["revision"],
        )
    result = service.run("alpha", operation["id"])
    assert result["phase"] == "verified", result
    for argv, _cwd, _timeout, env in runner.calls:
        assert not any(
            value in json.dumps([argv, env])
            for value in ("private-forge-token", "private-model-token", "private-project-key")
        )
        assert env["DOCKER_BUILDKIT"] == "0"
        assert str(store.root) in env["DOCKER_CONFIG"]


def test_image_runtime_rejects_remote_environment_and_linked_storage(tmp_path, monkeypatch):
    """@brief Unsupported daemon auth and linked ownership fail before effects."""
    module, _profiles, store, service, runner, operation, _path = build_project(tmp_path)
    monkeypatch.setenv("DOCKER_HOST", "tcp://remote:2376")
    assert service.run("alpha", operation["id"])["phase"] == "failed"
    assert not runner.calls
    monkeypatch.setattr(Path, "is_junction", lambda self: self == store.root)
    with pytest.raises(module.ImageBuildError):
        store.read()


def test_owned_image_client_adapter_uses_shared_native_controller(tmp_path):
    """@brief The production adapter forwards explicit bounds, scope and redaction."""
    from adore.util import CommandResult
    from adore.web.image_build_runner import ImageBuildRunner

    _module, _profiles, store, _service, _runner, operation, _path = build_project(tmp_path)
    calls = []

    class Controller:
        def run_files(self, argv, **kwargs):
            calls.append((argv, kwargs))
            assert kwargs["run_id"] == operation["id"]
            assert kwargs["host"] == operation["host"]["host"]
            assert kwargs["stdout_limit"] == 65536
            assert kwargs["timeout"] == 12
            return CommandResult(argv=argv, stdout="safe")

        def recover(self, *args):
            calls.append(args)

    client = ImageBuildRunner(store, operation, controller=Controller())
    assert client(["docker", "info"], cwd=store.root, timeout=12, env={"PATH": "owned"}).ok
    client.recover()
    assert len(calls) == 2


@pytest.mark.parametrize("runtime", ["podman", "wsl -d Ubuntu-24.04 -- docker", "wsl -- podman"])
def test_image_supported_runtime_builds_are_bounded_and_scoped(tmp_path, runtime):
    """@brief Docker/Podman and WSL prefixes retain argv/context/resource contracts."""
    from hashlib import sha256

    from adore.util import CommandResult

    module, profiles, store, _service, fake, _operation, path = build_project(tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            'runtime = "docker"', 'runtime = "' + runtime + '"'
        ),
        encoding="utf-8",
    )
    observed = []

    def runner(argv, **kwargs):
        observed.append(list(argv))
        if "printenv" in argv:
            return CommandResult(argv=argv, stdout="/home/operator")
        if argv[-2:] == ["id", "-u"]:
            return CommandResult(argv=argv, stdout="1000")
        if "info" in argv and "podman" in argv:
            return CommandResult(
                argv=argv,
                stdout=json.dumps(
                    {
                        "host": {
                            "os": "linux",
                            "hostname": "fixture",
                            "cgroupVersion": "v2",
                            "cgroupControllers": ["cpu", "memory"],
                        },
                        "store": {
                            "graphRoot": "/store",
                            "runRoot": "/run/store",
                            "graphDriverName": "overlay",
                            "containerStore": {"number": len(observed)},
                        },
                    }
                ),
            )
        return fake(argv, **kwargs)

    service = module.ImageBuildService(profiles, runner=runner)
    value = service.prepare(
        "alpha", store.export()["revision"], sha256(path.read_bytes()).hexdigest()
    )
    result = service.run("alpha", value["id"])
    assert result["phase"] == "verified", result
    build = next(argv for argv in observed if "build" in argv)
    assert "--cpu-quota" in build and "--memory" in build
    if runtime.startswith("wsl"):
        assert "env" in build and "-i" in build and build[-1].startswith("/mnt/")
    if runtime.endswith("podman"):
        assert "--pull=never" in build and "--http-proxy=false" in build


def test_image_cleanup_refuses_a_replaced_owned_resource(tmp_path):
    """@brief A create receipt cannot authorize cleanup of a replacement container."""
    module, profiles, store, _service, fake, operation, _path = build_project(tmp_path)

    def runner(argv, **kwargs):
        result = fake(argv, **kwargs)
        if "inspect" in argv and "image" not in argv:
            value = json.loads(result.stdout)
            value[0]["Id"] = "f" * 64
            result.stdout = json.dumps(value)
        return result

    result = module.ImageBuildService(profiles, runner=runner).run("alpha", operation["id"])
    assert result["phase"] == "uncertain"
    assert result["resource"] is not None
    assert not any("rm" in call[0] for call in fake.calls)


def test_image_verification_accepts_strict_equivalent_raw_oci_identity(tmp_path):
    """@brief Raw OCI IDs and sha256-prefixed IDs denote the same pinned image."""
    module, profiles, _store, _service, fake, operation, _path = build_project(tmp_path)

    def runner(argv, **kwargs):
        result = fake(argv, **kwargs)
        if "inspect" in argv:
            result.stdout = result.stdout.replace("sha256:", "")
        return result

    result = module.ImageBuildService(profiles, runner=runner).run("alpha", operation["id"])
    assert result["phase"] == "verified", result
    assert result["image_id"] == IMAGE_ID


# END OF FILE
