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
@file test_web_package.py
@brief Offline installer fail-closed trust-boundary tests.
@details Uses a tiny fake delivery directory; no pip or network is invoked.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tomllib

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "02_Tools/install_web_offline.py"
LAUNCHER = Path(__file__).resolve().parents[2] / "02_Tools/launch_web.py"


def test_third_party_notices_match_locked_runtime_versions():
    """@brief About notices track the offline web dependency lockfiles."""
    software = Path(__file__).resolve().parents[1]
    source = (software / "web" / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    bundled = (software / "adore" / "web" / "static"
               / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert bundled == source
    with (software / "uv.lock").open("rb") as handle:
        python_versions = {item["name"]: item["version"]
                           for item in tomllib.load(handle)["package"]}
    node_lock = json.loads((software / "web" / "package-lock.json").read_text(
        encoding="utf-8"))["packages"]
    node_names = {"React": "react", "React DOM": "react-dom", "Scheduler": "scheduler"}
    for line in source.splitlines():
        if not line.startswith("| ") or "---" in line or "Component" in line:
            continue
        _, name, version, _license, _ = line.split("|")
        name, version = name.strip(), version.strip()
        if name in node_names:
            assert node_lock[f"node_modules/{node_names[name]}"]["version"] == version
        else:
            assert python_versions[name.lower()] == version


def _bundle(tmp_path, *, system=None, digest=None, prerequisites=None):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    shutil.copy2(INSTALLER, bundle / "install.py")
    payload = bundle / "payload.txt"
    payload.write_text("offline bytes", encoding="utf-8")
    manifest = {
        "schema": 1, "adore_version": "0.13.0",
        "system": system or platform.system(),
        "machine": platform.machine(),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "images": [],
        "prerequisites": prerequisites or {},
        "files": {
            "payload.txt": digest or hashlib.sha256(payload.read_bytes()).hexdigest(),
            "install.py": hashlib.sha256((bundle / "install.py").read_bytes()).hexdigest(),
        },
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle


def _install(bundle, target, *, env=None):
    return subprocess.run(
        [sys.executable, str(bundle / "install.py"), "--target", str(target)],
        capture_output=True, text=True, check=False, timeout=10, env=env,
    )


def test_installer_checks_host_prerequisites_before_target_mutation(tmp_path):
    """@brief A required offline tool has a named error and a check-only path."""
    executable = Path(sys.executable).name.lower()
    bundle = _bundle(tmp_path, prerequisites={
        "forge_cli": ["missing-adore-tool"]})
    target = tmp_path / "runtime"
    result = _install(bundle, target)
    assert result.returncode != 0
    assert "missing offline prerequisite forge_cli" in result.stderr
    assert not target.exists()


    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["prerequisites"] = {"forge_cli": [executable]}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    checked = subprocess.run(
        [sys.executable, str(bundle / "install.py"), "--check-only",
         "--target", str(target)], capture_output=True, text=True,
        check=False, timeout=10,
        env={**os.environ, "PATH": str(Path(sys.executable).parent)
             + os.pathsep + os.environ.get("PATH", "")},
    )
    assert checked.returncode == 0, checked.stderr
    assert "prerequisites verified" in checked.stdout
    assert not target.exists()


def test_installer_rejects_invalid_required_image_manifest_before_target(tmp_path):
    """@brief Untrusted image entries cannot reach a runtime command."""
    bundle = _bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["images"] = [{"tag": "bad;command", "archive": None}]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    target = tmp_path / "runtime"
    result = _install(bundle, target)
    assert result.returncode != 0
    assert "invalid image manifest" in result.stderr
    assert not target.exists()


def test_installer_rejects_executor_tag_not_in_media(tmp_path):
    """@brief A declared executor image must be a listed prerequisite."""
    bundle = _bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["executor_image_cli"] = "pi"
    manifest["executor_image_tag"] = "missing:latest"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    target = tmp_path / "runtime"
    result = _install(bundle, target)
    assert result.returncode != 0
    assert "invalid executor image prerequisite" in result.stderr
    assert not target.exists()


def test_installer_rejects_wrong_host_before_writing(tmp_path):
    """@brief Delivery media for another OS cannot create a target runtime."""
    bundle = _bundle(tmp_path, system="UnsupportedOS")
    target = tmp_path / "runtime"
    result = _install(bundle, target)
    assert result.returncode != 0
    assert "does not match this host" in result.stderr
    assert not target.exists()


def test_installer_rejects_changed_payload_before_writing(tmp_path):
    """@brief SHA-256 mismatch aborts before venv or pip starts."""
    bundle = _bundle(tmp_path, digest="0" * 64)
    target = tmp_path / "runtime"
    result = _install(bundle, target)
    assert result.returncode != 0
    assert "checksum mismatch" in result.stderr
    assert not target.exists()


def test_installer_rejects_unlisted_wheel_before_writing(tmp_path):
    """@brief A wheel not covered by the manifest cannot enter pip resolution."""
    bundle = _bundle(tmp_path)
    (bundle / "wheels").mkdir()
    (bundle / "wheels" / "extra-1.0-py3-none-any.whl").write_bytes(b"surprise")
    target = tmp_path / "runtime"
    result = _install(bundle, target)
    assert result.returncode != 0
    assert "unlisted bundle file" in result.stderr
    assert not target.exists()


def test_installer_reports_missing_ensurepip_before_writing(tmp_path):
    """@brief An Ubuntu-style missing venv prerequisite leaves no target."""
    bundle = _bundle(tmp_path)
    shadow = tmp_path / "shadow"
    shadow.mkdir()
    (shadow / "ensurepip.py").write_text(
        "# Copyright (c) 2026 DDP Engineering\n"
        "# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
        "# Commercial use requires a separate commercial license.\n"
        "# See the LICENSE.txt file for full license details.\n"
        "# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n"
        "raise ImportError('ensurepip unavailable')\n", encoding="utf-8"
    )
    target = tmp_path / "runtime"
    env = {**os.environ, "PYTHONPATH": str(shadow)}
    result = _install(bundle, target, env=env)
    assert result.returncode != 0
    assert "venv/ensurepip" in result.stderr
    assert not target.exists()


def test_launcher_reports_missing_offline_runtime(tmp_path):
    """@brief Startup reports a missing installed Python without fetching it."""
    result = subprocess.run(
        [sys.executable, str(LAUNCHER), "--target", str(tmp_path / "missing")],
        capture_output=True, text=True, check=False, timeout=10,
    )
    assert result.returncode != 0
    assert "installed Python not found" in result.stderr


def _launcher_supervise():
    """@brief Load the shipped supervisor as an operator-facing tool."""
    spec = importlib.util.spec_from_file_location("adore_web_launcher", LAUNCHER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.supervise


class _FakeService:
    """@brief Model a failed or live child without starting host processes."""

    def __init__(self, status):
        self.returncode = status
        self.terminated = False

    def poll(self):
        """@brief Return the configured child status."""
        return self.returncode

    def terminate(self):
        """@brief Record bounded shutdown of the surviving child."""
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout):
        """@brief Model the child exiting after termination."""
        assert timeout == 10
        return self.returncode


def test_launcher_restarts_failed_pair_with_bounded_backoff():
    """@brief A failed worker restarts both services, then Ctrl-C stops them."""
    services = []
    delays = []

    def spawn(command):
        """@brief Return two failed rounds then a healthy service pair."""
        round_number = len(services) // 2
        service = _FakeService(1 if round_number < 2 and command[0] == "worker"
                               else None)
        services.append(service)
        return service

    def pause(delay):
        """@brief Stop the healthy round at the poll boundary."""
        delays.append(delay)
        if len(delays) == 3:
            raise KeyboardInterrupt

    result = _launcher_supervise()(["worker"], ["api"], restart_limit=2,
                                   spawn=spawn, pause=pause)
    assert result == 0
    assert delays == [1, 2, 2]
    assert len(services) == 6
    assert all(service.terminated or service.poll() == 1 for service in services)


def test_launcher_stops_after_restart_limit():
    """@brief Repeated crashes return failure instead of restarting forever."""
    services = []

    def spawn(command):
        """@brief Fail every worker while the API remains alive."""
        service = _FakeService(1 if command[0] == "worker" else None)
        services.append(service)
        return service

    result = _launcher_supervise()(["worker"], ["api"], restart_limit=2,
                                   spawn=spawn, pause=lambda _: None)
    assert result == 1
    assert len(services) == 6
    assert all(service.terminated for service in services[1::2])


def test_launcher_rejects_invalid_limit_and_failed_api_start():
    """@brief Invalid bounds or a missing API executable stop without retry."""
    supervise = _launcher_supervise()
    with pytest.raises(ValueError, match="restart_limit"):
        supervise(["worker"], ["api"], restart_limit=-1,
                  spawn=lambda _: None)
    worker = _FakeService(None)
    calls = []

    def spawn(command):
        """@brief Fail the second process after the worker has started."""
        calls.append(command[0])
        if command[0] == "api":
            raise OSError("missing executable")
        return worker

    assert supervise(["worker"], ["api"], spawn=spawn,
                     pause=lambda _: None) == 1
    assert calls == ["worker", "api"]
    assert worker.terminated
