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
@file       test_web_config_raw.py
@brief      Administrator original TOML download and trust boundaries.
@details    Offline HTTP tests preserve exact bytes and prevent denied disclosure.
"""

# IMPORTS
from hashlib import sha1
from io import BytesIO
import json
from pathlib import Path
import re
import tarfile
from zipfile import ZipFile

from adore.profiles import ProfileStore
from adore.util import CommandResult
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest

# CONSTANTS
_REVISION = "a" * 40
_MANIFEST = "docker/build.json"
_DOCKERFILE = "docker/Dockerfile"
_IMAGE = "registry.example:5000/example/executor:Reviewed"
_SOURCE = "assets/input.bin"


# LOCAL HELPERS
@pytest.fixture
def docker_project(raw_project, tmp_path):
    """@brief Create a Docker project and a fake immutable Git object database."""
    profiles, path, raw = raw_project
    repo = tmp_path / "repo"
    repo.mkdir()
    text = raw.decode().split("[private_fixture]")[0]
    text = re.sub(r'^repo_path = .+$', f'repo_path = "{repo.as_posix()}"', text, flags=re.M)
    text = re.sub(r'^image = .+$', f'image = "{_IMAGE}"', text, count=1, flags=re.M)
    text = text.replace("[container]", f'[container]\nbuild_definition = "{_MANIFEST}@{_REVISION}"')
    raw = text.encode()
    path.write_bytes(raw)
    manifest = {"schema": 1, "image": _IMAGE, "dockerfile": _DOCKERFILE,
                "files": [_DOCKERFILE, _SOURCE]}
    blobs = {_DOCKERFILE: b"FROM scratch\nCOPY assets/input.bin /input.bin\n",
             _SOURCE: b"\x00\xff\x10", "unrelated.txt": b"never included",
             ".env": b"token=never included"}
    commands = []

    def runner(argv, *, cwd, timeout, env):
        """@brief Model exact Git paths and binary archive output without external commands."""
        commands.append(argv)
        assert Path(cwd) == repo and timeout <= 30
        assert env["GIT_NO_LAZY_FETCH"] == "1"
        assert argv[0] == "git"
        if argv[1] == "rev-parse":
            if argv[2:] == ["--show-toplevel"]:
                return CommandResult(stdout=repo.as_posix() + "\n")
            assert argv[2:] == ["--verify", f"{_REVISION}^{{commit}}"]
            return CommandResult(stdout=_REVISION + "\n")
        paths = argv[argv.index("--") + 1:]
        assert argv[argv.index("--") - 1] == _REVISION
        present = {name: (json.dumps(manifest).encode() if name == _MANIFEST else blobs[name])
                   for name in paths if name == _MANIFEST or name in blobs}
        if argv[1] == "ls-tree":
            records = []
            for name, data in present.items():
                git_blob = b"blob " + str(len(data)).encode() + b"\0" + data
                digest = sha1(git_blob, usedforsecurity=False).hexdigest()
                records.append(f"100644 blob {digest} {len(data)}\t{name}\0")
            return CommandResult(stdout="".join(records))
        assert argv[1] == "archive"
        destination = Path(next(arg.removeprefix("--output=") for arg in argv
                                if arg.startswith("--output=")))
        with tarfile.open(destination, "w") as archive:
            for name, data in present.items():
                item = tarfile.TarInfo(name)
                item.size = len(data)
                archive.addfile(item, BytesIO(data))
        return CommandResult()

    return profiles, path, raw, manifest, blobs, commands, runner


# PUBLIC CONTRACT TESTS
def test_export_docker_build_bundle_contains_only_declared_bytes(docker_project):
    """@brief Admin ZIP has the original TOML, relative Compose paths and exact Git blobs."""
    profiles, _, raw, _, blobs, commands, runner = docker_project
    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        url = "/api/v1/projects/alpha/config/raw"
        response = client.get(url + "?download=true&include_build=true")
        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == "application/zip"
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["content-disposition"].endswith('"adore-docker-build.zip"')
        with ZipFile(BytesIO(response.content)) as bundle:
            assert set(bundle.namelist()) == {
                "config.toml", "compose.yaml", "BUILD.txt", "recipe.json",
                f"context/{_DOCKERFILE}", f"context/{_SOURCE}",
            }
            assert bundle.read("config.toml") == client.get(url + "?download=true").content == raw
            compose = bundle.read("compose.yaml").decode()
            assert json.loads(compose[compose.index("{"):]) == {"services": {"executor": {
                "image": _IMAGE, "build": {"context": "./context", "dockerfile": _DOCKERFILE},
            }}}
            assert bundle.read(f"context/{_SOURCE}") == blobs[_SOURCE]
            assert bundle.read(f"context/{_DOCKERFILE}") == blobs[_DOCKERFILE]
        assert [argv[1] for argv in commands] == [
            "rev-parse", "rev-parse", "ls-tree", "archive", "ls-tree", "archive",
        ]


@pytest.mark.parametrize(("invalid", "error"), [
    ("unregistered", "recipe_base_missing"),
    ("mutable", "build_definition_invalid"),
    ("missing", "build_source_unavailable"),
    ("traversal", "build_definition_invalid"),
    ("credential", "build_definition_invalid"),
    ("private_key", "build_definition_invalid"),
    ("wrong_image", "build_definition_invalid"),
    ("inline", "build_config_has_secrets"),
])
def test_export_docker_build_refuses_unsafe_definition(docker_project, invalid, error):
    """@brief Bad registrations fail closed and the standalone export remains available."""
    profiles, path, raw, manifest, blobs, commands, runner = docker_project
    if invalid == "unregistered":
        path.write_bytes(raw.replace(f'{_MANIFEST}@{_REVISION}'.encode(), b""))
    elif invalid == "mutable":
        path.write_bytes(raw.replace(_REVISION.encode(), b"main"))
    elif invalid == "missing":
        del blobs[_SOURCE]
    elif invalid == "traversal":
        manifest["files"].append("../private.txt")
    elif invalid == "credential":
        manifest["files"].append(".env")
    elif invalid == "private_key":
        blobs[_SOURCE] = b"-----BEGIN OPENSSH PRIVATE KEY-----\nfixture-private\n"
    elif invalid == "wrong_image":
        manifest["image"] = "another:tag"
    elif invalid == "inline":
        path.write_bytes(raw + b'\n[extra]\napi_key = "fixture-private"\n')
    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        url = "/api/v1/projects/alpha/config/raw"
        assert client.get(url + "?include_build=true").status_code == 401
        assert not commands
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get(url + "?include_build=true")
        assert response.status_code == 400, response.text
        assert response.json()["detail"]["code"] == error
        assert client.get(url + "?download=true").content == path.read_bytes()


@pytest.fixture
def raw_project(tmp_path):
    """@brief Create an isolated saved profile with a private inline fixture field."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha")
    path = profiles.config_path("alpha")
    source = (Path(__file__).resolve().parents[1] / "config.example.toml").read_text(
        encoding="utf-8").encode("utf-8")
    raw = (source + b'\n[private_fixture]\nvalue = "inline-private-fixture"\n').replace(
        b"\n", b"\r\n"
    )
    path.write_bytes(raw)
    return profiles, path, raw


def test_admin_raw_configuration_preserves_original_bytes(raw_project):
    """@brief Both read forms retain saved bytes, private fields and config revision."""
    profiles, path, raw = raw_project
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        for suffix in ("", "?download=true"):
            response = client.get("/api/v1/projects/alpha/config/raw" + suffix)
            assert response.status_code == 200
            assert response.content == raw
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["content-type"].startswith("text/plain")
            if suffix:
                assert (
                    response.headers["content-disposition"] == 'attachment; filename="config.toml"'
                )
        assert path.read_bytes() == raw
        assert not (path.parent / "pending_config.json").exists()


@pytest.mark.parametrize(
    "payload",
    [b"", b"[broken", b"value=\xff", b"#" * 524289],
    ids=["empty", "invalid-toml", "invalid-utf8", "oversized"],
)
def test_raw_configuration_corruption_withholds_bytes(raw_project, payload):
    """@brief Empty, malformed, invalid UTF-8 and oversized files fail closed."""
    profiles, path, _ = raw_project
    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        path.write_bytes(payload)
        response = client.get("/api/v1/projects/alpha/config/raw")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "config_corrupt"


def test_raw_configuration_denied_roles_and_missing_source(raw_project):
    """@brief Anonymous and Dev reads disclose nothing; missing source is typed."""
    profiles, path, _ = raw_project
    app = create_app(profiles.home)
    with TestClient(app) as client:
        target = "/api/v1/projects/alpha/config/raw"
        assert client.get(target).status_code == 401
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        csrf = login.json()["csrf"]
        created = client.post(
            "/api/v1/users",
            json={"username": "reader", "password": "fixture-password", "role": "developer"},
            headers={"X-CSRF-Token": csrf},
        )
        assert created.status_code == 200
        app.state.web_store.set_memberships(created.json()["id"], ["alpha"])
        client.delete("/api/v1/session", headers={"X-CSRF-Token": csrf})
        client.post("/api/v1/session", json={"username": "reader", "password": "fixture-password"})
        assert client.get(target).status_code == 403
        assert client.get("/api/v1/projects/missing/config/raw").status_code == 403
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        assert client.get("/api/v1/projects/missing/config/raw").status_code == 404
        path.unlink()
        assert client.get(target).status_code == 503


def test_raw_configuration_changed_source_fails_closed(raw_project, monkeypatch):
    """@brief Concurrent saved-file replacement cannot produce a mixed snapshot."""
    profiles, path, raw = raw_project
    original_open = Path.open
    reads = 0

    def changing_open(source, *args, **kwargs):
        """@brief Simulate an external writer replacing the configured file."""
        nonlocal reads
        if source == path and args and args[0] == "rb":
            reads += 1
            if reads == 2:
                with original_open(path, "wb") as writer:
                    writer.write(raw + b"\n# external writer\n")
        return original_open(source, *args, **kwargs)

    with TestClient(create_app(profiles.home)) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        monkeypatch.setattr(Path, "open", changing_open)
        response = client.get("/api/v1/projects/alpha/config/raw")
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "stale_config_revision"


# END OF FILE
