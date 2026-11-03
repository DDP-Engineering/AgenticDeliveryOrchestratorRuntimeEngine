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
@file    test_pi_installation.py
@brief   Offline managed Pi installation and verification contracts.
@details Fake Node and npm commands exercise the publication boundary.
"""

# IMPORTS
from adore.cli import main
import pytest


def test_verify_missing_node(tmp_path, monkeypatch, capsys):
    """@brief Diagnose a missing Node before using a global Pi."""
    monkeypatch.setenv("ADORE_HOME", str(tmp_path))
    monkeypatch.setenv("ADORE_NODE", str(tmp_path / "missing"))
    assert main(["pi", "verify"]) == 1
    assert "Node" in capsys.readouterr().err



def write_fake_packages(pi):
    """@brief Write npm's expected manifests and CLI without accessing a registry."""
    import json

    from adore import pi_installation as managed

    for name, version in ((managed.PI_PACKAGE, managed.PI_VERSION),
                          (managed.WEB_PACKAGE, managed.WEB_VERSION)):
        package = pi.prefix / "node_modules" / name
        package.mkdir(parents=True)
        (package / "package.json").write_text(json.dumps({"name": name, "version": version}))
    pi.cli.parent.mkdir(parents=True)
    pi.cli.write_text("// Fake installed entrypoint", encoding="utf-8")


def fake_node(tmp_path, monkeypatch):
    """@brief Select a fake native Node under a host directory with spaces."""
    node = tmp_path / "Node Tools" / "node.exe"
    npm = node.parent / "node_modules/npm/bin/npm-cli.js"
    npm.parent.mkdir(parents=True)
    npm.touch()
    node.write_bytes(b"test node")
    node.chmod(0o755)
    monkeypatch.setenv("ADORE_NODE", str(node))
    monkeypatch.setenv("ADORE_HOME", str(tmp_path / "ADORE Home"))
    return node


def test_install_verify_and_change_build_pin(tmp_path, monkeypatch):
    """@brief Verify idempotent publication and select only the new build pin."""
    from pathlib import Path

    from adore import pi_installation as managed
    from adore.util import CommandResult

    node = fake_node(tmp_path, monkeypatch)
    monkeypatch.setenv("NODE_OPTIONS", "--require=hostile.js")
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path / "personal"))
    messages, installs = [], []

    def run(argv, *, cwd, env, timeout):
        assert argv[0] == str(node)
        assert timeout <= 300 and "NODE_OPTIONS" not in env
        assert env["PI_CODING_AGENT_DIR"] == str(cwd / "agent")
        if argv[-1] == "--version":
            return CommandResult(stdout="v22.23.4" if len(argv) == 2 else managed.PI_VERSION)
        prefix = Path(argv[argv.index("--prefix") + 1])
        assert str(node.parent / "node_modules/npm/bin/npm-cli.js") == argv[1]
        assert {"--global=false", "--ignore-scripts", f"{managed.PI_PACKAGE}@{managed.PI_VERSION}",
                f"{managed.WEB_PACKAGE}@{managed.WEB_VERSION}"}.issubset(argv)
        write_fake_packages(managed.ManagedPi(node, prefix))
        installs.append(prefix)
        return CommandResult()

    first = managed.install_pi(progress=messages.append, runner=run)
    assert managed.verify_pi(runner=run) == first
    assert managed.install_pi(progress=messages.append, runner=run) == first
    assert len(installs) == 1 and not installs[0].exists()
    assert any("Verifying" in message for message in messages)
    monkeypatch.setattr(managed, "PI_VERSION", "9.8.7")
    with pytest.raises(managed.PiInstallationError, match="missing"):
        managed.verify_pi(runner=run)
    second = managed.install_pi(progress=messages.append, runner=run)
    assert first.prefix != second.prefix and first.cli.is_file() and second.cli.is_file()
    assert managed.verify_pi(runner=run) == second


@pytest.mark.parametrize("failure", ["old-node", "node-24", "npm", "timeout", "version"])
def test_install_rejects_bad_node_or_unverified_npm_candidate(tmp_path, monkeypatch, failure):
    """@brief A failed installation never publishes files or discloses npm output."""
    from pathlib import Path

    from adore import pi_installation as managed
    from adore.util import CommandResult

    node = fake_node(tmp_path, monkeypatch)

    def run(argv, **_kwargs):
        if argv == [str(node), "--version"]:
            return CommandResult(stdout={
                "old-node": "v22.19.0", "node-24": "v24.18.0",
            }.get(failure, "v22.23.4"))
        if failure in {"old-node", "node-24"}:
            pytest.fail("Incompatible Node must stop before npm")
        if argv[-1] == "--version":
            return CommandResult(stdout="0.0.1")
        if failure in {"npm", "timeout"}:
            return CommandResult(exit_code=124 if failure == "timeout" else 9,
                                 stderr="private npm output", timed_out=failure == "timeout")
        write_fake_packages(managed.ManagedPi(node, Path(argv[argv.index("--prefix") + 1])))
        return CommandResult()

    with pytest.raises(managed.PiInstallationError) as error:
        managed.install_pi(progress=lambda _: None, runner=run)
    assert error.value.reason == {
        "old-node": "node-incompatible", "node-24": "node-incompatible",
        "npm": "npm-failed", "timeout": "npm-failed", "version": "version-invalid",
    }[failure]
    assert "private npm output" not in str(error.value)
    assert not (managed.adore_home() / "tools/pi" / managed.PI_VERSION).exists()


def test_managed_pi_ships_the_reviewed_guard():
    """@brief Native Pi receives the same extension source as the executor image."""
    from adore.pi_installation import GUARD

    image_guard = GUARD.parents[2] / "docker/pi/adore-guard.ts"
    assert GUARD.read_bytes() == image_guard.read_bytes()
