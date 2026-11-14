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
@file       test_system_packages.py
@brief      Direct agent package authority and independent network contracts.
@details    All runtime, forge and process commands are injected and offline.
"""

# IMPORTS
from copy import deepcopy
from hashlib import sha256
import json

from adore.config import EgressPolicy, default_config, validate_config
from adore.isolation import ContainerManager, IsolationError
from adore.preparation import PreparationError, execution_policy, resolve_plan, validate_plan
from adore.state import StateError, validate_execution_record
from adore.util import CommandResult
import pytest


# HELPERS
def package_config():
    """@brief Return a valid container profile with opt-in authority."""
    config = default_config()
    config.platform.kind = "github"
    config.platform.repo = "owner/repo"
    config.worktree.repo_path = "/repo"
    config.executor.provider = "openai"
    config.executor.model = "model"
    config.container.system_packages = True
    return config


def fingerprint(plan):
    """@brief Rebind externally constructed state to test semantic validation."""
    plan["fingerprint"] = sha256(json.dumps(
        {k: v for k, v in plan.items() if k != "fingerprint"},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()
    return plan


# PUBLIC API / TESTS
def test_package_permission_defaults_off_and_is_strict_boolean():
    """@brief Legacy profiles receive no elevation; malformed booleans reject."""
    config = default_config()
    assert getattr(config.container, "system_packages", None) is False
    config = package_config()
    assert validate_config(config) == []
    for invalid in ("true", 1, None, [], {}):
        config.container.system_packages = invalid
        assert any("system_packages" in x for x in validate_config(config))


@pytest.mark.parametrize("option", [
    "--privileged", "--user=0", "-u0", "--network=host", "--net=host",
    "--pid=host", "--ipc=host", "--volume=/etc:/etc", "-v/etc:/etc",
    "--mount=type=bind,src=/,dst=/host", "--device=/dev/sda", "--cap-add=ALL",
    "--security-opt=no-new-privileges", "--entrypoint=sh", "--env=X=y",
    "--userns=host", "--volumes-from=other",
])
def test_package_permission_rejects_host_or_privilege_overrides(option):
    """@brief Managed administrative permission cannot expand host exposure."""
    config = package_config()
    config.container.run_args = [option]
    assert any("system_packages" in x for x in validate_config(config))


def test_package_permission_rejects_native_host_but_accepts_rootless_keep_id():
    """@brief Explicit opt-in is container-only and retains Podman UID mapping."""
    config = package_config()
    config.container.run_args = ["--userns=keep-id", "--memory=2g"]
    assert validate_config(config) == []
    config.execution.backend = "local"
    assert any("system_packages" in x for x in validate_config(config))


@pytest.mark.parametrize("runtime", ["docker", "podman", "wsl -d Ubuntu -- docker"])
@pytest.mark.parametrize("mode", ["open", "none", "allowlist-proxy"])
def test_package_authority_uses_owned_container_without_network_or_host_installs(runtime, mode):
    """@brief Authorization supplies no model secrets or network override."""
    calls = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return CommandResult(stdout="1000\n" if len(calls) == 1
                             else "adore-system-packages-ready\n")

    manager = ContainerManager(runtime, "project:1", "uv", "npm", runner,
                               egress=EgressPolicy(mode=mode, allowlist=["example.com"]))
    authorize = getattr(manager, "authorize_system_packages", None)
    assert callable(authorize), "missing container package authorization"
    authorize("owned-run")
    assert len(calls) == 2
    argv, kwargs = calls[1]
    assert argv[:len(manager.runtime_argv)] == manager.runtime_argv
    assert argv[len(manager.runtime_argv):len(manager.runtime_argv) + 4] == [
        "exec", "--user", "0", "owned-run",
    ]
    assert "--network" not in argv and "--privileged" not in argv
    assert kwargs["timeout"] == 30
    assert not kwargs.get("env"), "root bootstrap must not receive provider credentials"


@pytest.mark.parametrize("uid", ["0\n", "root", "1000\n1001", "-1", "", "1;echo bad"])
def test_package_authority_rejects_root_or_malformed_executor_identity(uid):
    """@brief Untrusted process output never chooses an elevated account."""
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        return CommandResult(stdout=uid)

    manager = ContainerManager("docker", "project:1", "uv", "npm", runner)
    authorize = getattr(manager, "authorize_system_packages", None)
    assert callable(authorize), "missing container package authorization"
    with pytest.raises(IsolationError):
        authorize("owned-run")
    assert len(calls) == 1


@pytest.mark.parametrize("result", [
    CommandResult(exit_code=1, stderr="sudo missing"),
    CommandResult(exit_code=0, timed_out=True),
    CommandResult(stdout=""), CommandResult(stdout="untrusted success"),
])
def test_package_authority_fails_closed_on_missing_or_failed_confirmation(result):
    """@brief Exit zero alone cannot prove the authorization contract."""
    results = iter([CommandResult(stdout="1000\n"), result])
    manager = ContainerManager("podman", "project:1", "uv", "npm",
                               runner=lambda *a, **k: next(results))
    authorize = getattr(manager, "authorize_system_packages", None)
    assert callable(authorize), "missing container package authorization"
    with pytest.raises(IsolationError):
        authorize("owned-run")


def test_package_execution_policy_pins_true_and_preserves_legacy_false_shape():
    """@brief Opt-in is fingerprinted; omitted legacy false keeps old identity."""
    config = package_config()
    plan = resolve_plan(config)
    assert plan["policy"]["container"].get("system_packages") is True
    assert validate_plan(plan) == plan
    config.container.system_packages = False
    assert "system_packages" not in execution_policy(config)["container"]
    assert execution_policy(config) != plan["policy"]
    assert validate_plan(resolve_plan(config))


@pytest.mark.parametrize("value", [False, "true", 1, None])
def test_package_plan_rejects_noncanonical_opt_in(value):
    """@brief Recomputed fingerprints cannot disguise corrupt permission types."""
    plan = resolve_plan(package_config())
    plan["policy"]["container"]["system_packages"] = value
    with pytest.raises(PreparationError):
        validate_plan(fingerprint(plan))


def test_package_only_state_preserves_exact_resource_without_claiming_recipe_success():
    """@brief Installed environment identity survives a restart with no fake setup."""
    record = {"plan": resolve_plan(package_config()), "resource": {
        "container_id": "a" * 64, "image_id": "sha256:" + "b" * 64,
    }, "status": "not-required", "attempts": 0, "steps": [], "history": [],
              "reprepare": False}
    validate_execution_record(record)
    corrupt = deepcopy(record)
    corrupt["resource"]["container_id"] = "other"
    with pytest.raises(StateError):
        validate_execution_record(corrupt)


def test_package_setting_requires_review_and_preserves_network(tmp_path):
    """@brief An admin stages and applies a boolean without enabling networking."""
    from adore.config import load_config
    from adore.state import StateStore
    from adore.web.app import create_app

    from tests.configuration_client import TestClient
    from tests.test_model_connection import project

    profiles = project(tmp_path)
    StateStore(tmp_path / "state").pause()
    path = profiles.config_path("alpha")
    original_network = load_config(path).container.egress
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        view = client.get("/api/v1/projects/alpha/config").json()
        metadata = {row["key"]: row for row in view["settings"]}
        assert metadata["container.system_packages"]["editable"] is True
        payload = {"key": "container.system_packages", "value": "true",
                   "revision": view["revision"]}
        assert client.put("/api/v1/projects/alpha/config", json=payload,
                          headers=headers).status_code == 409
        response = client.post("/api/v1/projects/alpha/config/pending",
                               json=payload, headers=headers)
        assert response.status_code == 200, response.text
        candidate = response.json()
        assert candidate["proposed_value"] is True and candidate["restart_required"] is True
        response = client.post("/api/v1/projects/alpha/config/apply", headers=headers,
                               json={"candidate_revision": candidate["candidate_revision"],
                                     "base_revision": view["revision"]})
        assert response.status_code == 200, response.text
    assert load_config(path).container.system_packages is True
    assert load_config(path).container.egress == original_network


@pytest.mark.parametrize("value", ['"true"', "1", "[]"])
def test_package_setting_refuses_non_boolean_candidates(tmp_path, value):
    """@brief Human-written settings cannot silently coerce administrative rights."""
    from adore.state import StateStore
    from adore.web.app import create_app

    from tests.configuration_client import TestClient
    from tests.test_model_connection import project

    profiles = project(tmp_path)
    StateStore(tmp_path / "state").pause()
    with TestClient(create_app(profiles.home)) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        headers = {"X-CSRF-Token": login.json()["csrf"]}
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        response = client.post("/api/v1/projects/alpha/config/pending", headers=headers,
                               json={"key": "container.system_packages", "value": value,
                                     "revision": revision})
        assert response.status_code == 400


@pytest.mark.parametrize(
    "drift", ["none", "permission", "network", "container", "image", "missing"],
)
def test_public_retry_pins_package_authority_and_container(tmp_path, monkeypatch, drift):
    """@brief Retry retains the prepared resource and fails before AI on drift."""
    from types import SimpleNamespace

    from adore import orchestrator as module
    from adore.executor.base import GateRun

    from tests.test_orchestrator import (
        TASK_ID,
        FakeAegis,
        FakeExecutor,
        make_engine,
        make_run,
        task,
    )

    engine, forge, worktrees, containers, executor = make_engine(
        tmp_path, executor=FakeExecutor(GateRun(
            exit_code=0, has_questions=True, questions="Need project clarification",
        )),
    )
    engine.config.container.system_packages = True
    engine.config.executor.provider = "openai"
    engine.config.executor.model = "model"
    identity = {"container_id": "a" * 64, "image_id": "sha256:" + "b" * 64,
                "status": "running"}
    containers.resource_identity = lambda _: dict(identity)
    containers.image_identity = lambda _: "sha256:" + "b" * 64
    authorized = []
    containers.authorize_system_packages = lambda name: authorized.append(name)

    class Client(FakeAegis):
        """@brief AEGIS fake observes authority before first AI interaction."""

        def __init__(self, *args):
            super().__init__([task("frame")])

        def probe(self):
            assert authorized, "agent reached AEGIS before package authorization"
            return SimpleNamespace(version="0.14.0", schema=1)

        def create_task(self, *args):
            return TASK_ID

    monkeypatch.setattr(module, "AegisClient", Client)
    run = make_run(engine)
    run.active_task_id = None
    run.task_ids = []
    run.lifecycle = "failed"
    engine.store.save(run)
    assert engine.retry(run.run_id)
    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "parked-clarification", saved.outcome
    assert saved.execution["resource"]["container_id"] == "a" * 64
    assert saved.execution["status"] == "not-required"
    assert "sudo -n" in executor.prompts[-1]
    assert "independently configured as allowlist-proxy" in executor.prompts[-1]
    assert not forge.opened
    before = len(authorized)
    saved.lifecycle = "failed"
    engine.store.save(saved)
    if drift == "permission":
        engine.config.container.system_packages = False
    elif drift == "network":
        engine.config.executor.internet = True
    elif drift in {"container", "image"}:
        identity[drift + "_id"] = ("c" * 64 if drift == "container"
                                   else "sha256:" + "c" * 64)
    elif drift == "missing":
        def missing(name):
            raise IsolationError("owned package container is absent")
        containers.resource_identity = missing
    assert engine.retry(run.run_id)
    saved = engine.store.load(run.run_id)
    if drift == "none":
        assert len(authorized) > before
    else:
        assert saved.lifecycle == "failed"
        assert len(authorized) == before


def test_package_gate_retains_bounded_redacted_installation_output(tmp_path):
    """@brief Long package logs cannot retain known credentials or claim full usage."""
    from adore.executor.launcher import PiExecutor

    io = tmp_path / "io"
    io.mkdir()
    secret = "provider-secret-123456"

    def execute(argv, **kwargs):
        (io / "output.jsonl").write_text(secret + "x" * 100000, encoding="utf-8")
        (io / "stderr.log").write_text("Bearer abcdef\n" + secret, encoding="utf-8")
        return CommandResult(exit_code=1)

    executor = PiExecutor("pi -p --mode json --model {model} {prompt}", "provider/model")
    result = executor.run_gate(execute, tmp_path, io, "install missing dependency",
                               archive_stem="build", package_secrets={"KEY": secret})
    assert result.exit_code == 1
    assert secret not in result.output + result.stderr
    assert "abcdef" not in result.stderr
    assert len(result.output.encode()) <= 65536
    assert result.tokens_reported is False and result.cost_reported is False
    for path in [io / "output.jsonl", io / "archive/build-attempt1/output.jsonl"]:
        assert len(path.read_bytes()) <= 65536
        assert secret not in path.read_text(encoding="utf-8")



@pytest.mark.parametrize("payload,secrets", [
    (b"line\n" * 16000, {}),
    (b"tkn " * 15000, {"KEY": "tkn"}),
    (b"\xff" * 24000, {}),
], ids=["newline-archive", "redaction-expansion", "invalid-utf8-expansion"])
def test_package_retention_bounds_encoded_files_after_normalization(tmp_path, payload, secrets):
    """@brief Retained live/archive UTF-8 bytes stay bounded after all transformations."""
    from adore.executor.launcher import PiExecutor

    io = tmp_path / "io"
    io.mkdir()

    def execute(argv, **kwargs):
        (io / "output.jsonl").write_bytes(payload)
        (io / "stderr.log").write_bytes(payload)
        return CommandResult(exit_code=1)

    executor = PiExecutor("pi -p --mode json --model {model} {prompt}", "provider/model")
    result = executor.run_gate(execute, tmp_path, io, "install dependency",
                               archive_stem="encoded", package_secrets=secrets)
    assert result.exit_code == 1
    for name, text in [("output.jsonl", result.output), ("stderr.log", result.stderr)]:
        assert len(text.encode("utf-8")) <= 65536
        for root in [io, io / "archive/encoded-attempt1"]:
            data = (root / name).read_bytes()
            assert len(data) <= 65536
            assert data.decode("utf-8") == text
            assert all(value not in data.decode("utf-8") for value in secrets.values())


def test_package_gate_refuses_linked_output_without_reading_target(tmp_path, monkeypatch):
    """@brief An executor-controlled link cannot redirect host-side retention."""
    from pathlib import Path
    import stat
    from types import SimpleNamespace

    from adore.executor.launcher import PiExecutor

    io = tmp_path / "io"
    io.mkdir()
    original = Path.lstat

    def lstat(path):
        if path.name == "output.jsonl":
            return SimpleNamespace(st_mode=stat.S_IFLNK)
        return original(path)

    monkeypatch.setattr(Path, "lstat", lstat)
    executor = PiExecutor("pi -p --mode json --model {model} {prompt}", "provider/model")
    with pytest.raises(IsolationError, match="linked"):
        executor.run_gate(lambda *a, **k: CommandResult(), tmp_path, io, "prepare",
                          package_secrets={})


def test_package_log_retention_preserves_complete_original_usage(tmp_path):
    """@brief Late Pi usage after long tool output still counts toward budgets."""
    from adore.executor.launcher import build_executor

    io = tmp_path / "io"
    io.mkdir()
    event = {"type": "turn_end", "message": {"usage": {
        "input": 10, "output": 20, "cacheRead": 2, "cacheWrite": 3}}}
    full_output = json.dumps(event) + "\n" + json.dumps({"tool": "x" * 100000})
    full_output += "\n" + json.dumps(event) + "\n"

    def execute(argv, **kwargs):
        (io / "output.jsonl").write_text(full_output, encoding="utf-8")
        return CommandResult()

    executor = build_executor("pi -p --model {model} {prompt}", "model")
    result = executor.run_gate(execute, tmp_path, io, "prepare", package_secrets={})
    assert result.tokens_in == 30 and result.tokens_out == 40 and result.tokens_reported
    assert result.cost_usd == 0 and not result.cost_reported
    assert len(result.output.encode()) <= 65536


@pytest.mark.parametrize("failure", ["none", "missing-sudo", "unsafe-directory", "visudo"])
def test_container_authorization_policy_with_offline_processes(tmp_path, monkeypatch, failure):
    """@brief Actual authorization code writes validated sudoers only in the container seam.
    @note System identity and subprocesses are faked; no package or setup script runs.
    """
    import os
    import pathlib
    import shutil
    import stat
    import subprocess
    import sys
    from types import SimpleNamespace

    from adore.package_permissions import PACKAGE_AUTHORIZATION_SCRIPT

    directory = tmp_path / "sudoers.d"
    directory.mkdir()
    calls = []

    class Directory:
        """@brief Container filesystem stand-in redirects only the fixed sudoers directory."""

        def lstat(self):
            return SimpleNamespace(st_mode=stat.S_IFDIR | (0o777 if failure == "unsafe-directory"
                                                         else 0o755), st_uid=0)

        def __str__(self):
            return str(directory)

        def __truediv__(self, name):
            return directory / name

    def run(argv, **kwargs):
        calls.append(argv)
        if argv[0].endswith("visudo"):
            with open(argv[-1], encoding="utf-8") as handle:
                content = handle.read()
            assert content.splitlines()[-1] == "#1000 ALL=(root) NOPASSWD: /usr/bin/apt-get"
            assert "HTTP_PROXY HTTPS_PROXY NO_PROXY" in content
            assert "API_KEY" not in content
            if failure == "visudo":
                raise subprocess.CalledProcessError(1, argv)
        else:
            assert argv == ["/usr/bin/sudo", "-u", "#1000", "--", "/usr/bin/sudo",
                            "-n", "--", "/usr/bin/apt-get", "--version"]

    monkeypatch.setattr(pathlib, "Path", lambda value: Directory())
    monkeypatch.setattr(os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(os, "fchmod", lambda *args: None, raising=False)
    monkeypatch.setattr(os, "environ", {"API_KEY": "must-not-reach-subprocesses"})
    monkeypatch.setattr(os.path, "isfile", lambda path: path == "/usr/bin/apt-get")
    monkeypatch.setattr(os, "access", lambda *args: True)
    monkeypatch.setattr(shutil, "which", lambda name: None if failure == "missing-sudo"
                        else "/usr/bin/" + name)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["authorization", "1000"])
    if failure == "none":
        exec(compile(PACKAGE_AUTHORIZATION_SCRIPT, "container-authorize", "exec"), {})
        assert (directory / "adore-system-packages").is_file()
        assert len(calls) == 2
    else:
        with pytest.raises((RuntimeError, subprocess.CalledProcessError)):
            exec(compile(PACKAGE_AUTHORIZATION_SCRIPT, "container-authorize", "exec"), {})
        assert not (directory / "adore-system-packages").exists()




@pytest.mark.parametrize("field,value", [("provider", "anthropic"), ("internet", True),
                                        ("web.search", "none"),
                                        ("endpoint.base_url", "https://endpoint.invalid/v1")])
def test_execution_plan_pins_pi_network_and_provider_policy(field, value):
    """@brief A changed model route or network authority cannot reuse a prepared plan."""
    config = package_config()
    original = resolve_plan(config)
    owner = config.executor
    for part in field.split(".")[:-1]:
        owner = getattr(owner, part)
    setattr(owner, field.split(".")[-1], value)
    changed = resolve_plan(config)
    assert original["fingerprint"] != changed["fingerprint"]
    assert validate_plan(changed) == changed
