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
@file    test_gitea_auth.py
@brief   Portable external Gitea authentication through injected CLI boundaries.
@details Uses temporary account directories and metadata; no live credentials or CLI.
"""

# IMPORTS
import json
import os
import platform
from types import SimpleNamespace

from adore.forge.base import ForgeError
from adore.repository_auth import project_runner
from adore.util import CommandResult
import pytest

# LOCAL HELPERS


def account(tmp_path, monkeypatch, system):
    """@brief Replace discovery roots with a synthetic current-account environment."""
    monkeypatch.setattr(platform, "system", lambda: system)
    for key in ("XDG_CONFIG_HOME", "HOME", "USERPROFILE", "LOCALAPPDATA", "APPDATA"):
        monkeypatch.delenv(key, raising=False)
    home = tmp_path / "account"
    home.mkdir()
    monkeypatch.setenv("HOME" if system == "Linux" else "USERPROFILE", str(home))
    if system == "Windows":
        monkeypatch.setenv("LOCALAPPDATA", str(home / "Local"))
        monkeypatch.setenv("APPDATA", str(home / "Roaming"))
    return home


def configured(login=""):
    """@brief Minimal external-auth profile; scoped records remain absent."""
    return SimpleNamespace(platform=SimpleNamespace(kind="gitea", login=login, repo="owner/repo"))


def row(name="local", default=False):
    """@brief Metadata may contain a CLI token field which must never escape."""
    return {
        "name": name,
        "url": "https://forge.example",
        "default": default,
        "token": "PRIVATE-METADATA-TOKEN",
    }


# PUBLIC API / TESTS


@pytest.mark.parametrize(
    "system,location",
    [
        ("Windows", "Local"),
        ("Windows", "Roaming"),
        ("Windows", ".config"),
        ("Linux", ".config"),
    ],
)
def test_portable_auth_recovers_standard_account_roots(tmp_path, monkeypatch, system, location):
    """@brief Missing CLI auth resolves from standard Windows/Linux current-account roots."""
    home = account(tmp_path, monkeypatch, system)
    root = home / location
    (root / "tea").mkdir(parents=True)
    (root / "tea/config.yml").write_text("opaque; ADORE must not read this", encoding="utf-8")
    calls = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        env = kwargs.get("env") or {}
        if argv[:3] == ["tea", "logins", "list"]:
            return CommandResult(
                stdout=json.dumps([row()] if env.get("XDG_CONFIG_HOME") == str(root) else [])
            )
        if "--login" in argv and env.get("XDG_CONFIG_HOME") == str(root):
            return CommandResult(stdout="verified response")
        return CommandResult(exit_code=1, stderr="Error: no available login\n")

    result = project_runner(tmp_path / "profile", configured(), runner)(
        ["tea", "api", "-i", "user"], timeout=8
    )
    assert result.ok and result.stdout == "verified response"
    retry, options = calls[-1]
    assert retry[-2:] == ["--login", "local"]
    assert 0 < options["timeout"] <= 8
    assert "PRIVATE-METADATA-TOKEN" not in str(calls)
    assert "XDG_CONFIG_HOME" not in os.environ


@pytest.mark.parametrize(
    "names,login,selected",
    [
        ([row()], "", "local"),
        ([row("a", "false"), row("b", "true")], "", "b"),
        ([row("a", True), row("b")], "b", "b"),
    ],
)
def test_portable_auth_selects_named_default_or_sole_login(
    tmp_path, monkeypatch, names, login, selected
):
    """@brief Explicit names win; string false does not create an accidental default."""
    account(tmp_path, monkeypatch, "Linux")
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        if argv[:3] == ["tea", "logins", "list"]:
            return CommandResult(stdout=json.dumps(names))
        if len(calls) > 1:
            assert argv[argv.index("--login") + 1] == selected
            return CommandResult(stdout="success")
        return CommandResult(
            exit_code=1,
            stderr=(
                f"Error: login name '{login}' does not exist"
                if login
                else "Error: no available login"
            ),
        )

    argv = ["tea", "api", "user"] + (["--login", login] if login else [])
    assert project_runner(tmp_path, configured(login), runner)(argv, timeout=8).ok
    assert len(calls) == 3


@pytest.mark.parametrize(
    "metadata,login,code",
    [
        ([], "", "gitea_auth_missing"),
        ([row("a"), row("b")], "", "gitea_auth_ambiguous"),
        ([row("a", True), row("b", True)], "", "gitea_auth_ambiguous"),
        ([row("other", True)], "configured", "gitea_auth_login_missing"),
        ({"logins": [row()]}, "", "gitea_auth_invalid"),
        ([{"name": "bad", "url": "https://user:password@forge.example"}], "", "gitea_auth_invalid"),
        ([row("a"), row("a")], "", "gitea_auth_invalid"),
    ],
)
def test_portable_auth_fails_closed_without_guessing(tmp_path, monkeypatch, metadata, login, code):
    """@brief Missing/ambiguous/corrupt CLI data never selects another credential."""
    account(tmp_path, monkeypatch, "Linux")

    def runner(argv, **kwargs):
        if argv[:3] == ["tea", "logins", "list"]:
            return CommandResult(stdout=json.dumps(metadata))
        return CommandResult(exit_code=1, stderr="Error: no available login")

    with pytest.raises(ForgeError, match=code) as error:
        project_runner(tmp_path, configured(login), runner)(["tea", "api", "user"], timeout=8)
    assert "PRIVATE" not in str(error.value) and "password" not in str(error.value)


@pytest.mark.parametrize(
    "source",
    [
        '[{"name":"a","name":"b","url":"https://forge.example"}]',
        '[{"name":"a","url":"https://forge.example","default":NaN}]',
        "PRIVATE-INVALID-OUTPUT",
        "[" * 2000,
        " " * 1048577,
    ],
    ids=["duplicate", "nonfinite", "invalid", "deep", "oversized"],
)
def test_portable_auth_rejects_ambiguous_json_without_echo(tmp_path, monkeypatch, source):
    """@brief External JSON ambiguity and non-JSON secrets produce a value-free error."""
    account(tmp_path, monkeypatch, "Linux")

    def runner(argv, **kwargs):
        return (
            CommandResult(stdout=source)
            if argv[1] == "logins"
            else CommandResult(exit_code=1, stderr="Error: no available login")
        )

    with pytest.raises(ForgeError, match="gitea_auth_invalid") as error:
        project_runner(tmp_path, configured(), runner)(["tea", "api", "user"], timeout=8)
    assert "PRIVATE" not in str(error.value)


def test_portable_auth_respects_explicit_xdg_and_other_commands(tmp_path, monkeypatch):
    """@brief An explicit account config root stays authoritative, including when empty."""
    home = account(tmp_path, monkeypatch, "Windows")
    alternate = home / "Local/tea"
    alternate.mkdir(parents=True)
    (alternate / "config.yml").touch()
    env = {"XDG_CONFIG_HOME": str(tmp_path / "explicit"), "HOME": str(home), "PRIVATE": "kept"}
    before = dict(env)
    calls = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        assert kwargs.get("env") == env
        if argv[0] != "tea":
            return CommandResult(stdout="git")
        return (
            CommandResult(stdout="[]")
            if argv[1] == "logins"
            else CommandResult(exit_code=1, stderr="Error: no available login")
        )

    target = project_runner(tmp_path, configured(), runner)
    assert target(["git", "status"], env=env).stdout == "git"
    with pytest.raises(ForgeError, match="gitea_auth_missing"):
        target(["tea", "api", "user"], env=env, timeout=8)
    assert len(calls) == 3 and env == before


@pytest.mark.parametrize(
    "result",
    [
        CommandResult(stdout="ok"),
        CommandResult(exit_code=0, stderr="HTTP/1.1 401 Unauthorized"),
        CommandResult(exit_code=1, stderr="HTTP/1.1 403 Forbidden"),
        CommandResult(exit_code=124, timed_out=True, stderr="Error: no available login"),
        CommandResult(exit_code=1, stderr="network unavailable"),
    ],
)
def test_portable_auth_preserves_http_failures_and_success(tmp_path, result):
    """@brief HTTP results, timeouts and unknown failures never switch accounts."""
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        return result

    assert project_runner(tmp_path, configured(), runner)(["tea", "api", "user"]) is result
    assert len(calls) == 1


def test_portable_gitea_doctor_checks_discovered_identity(tmp_path, monkeypatch):
    """@brief CLI doctor shares metadata recovery and verifies the final account response."""
    from adore.doctor import auth_status

    account(tmp_path, monkeypatch, "Linux")
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        if argv[1] == "logins":
            return CommandResult(stdout=json.dumps([row()]))
        if "--login" in argv:
            return CommandResult(stdout='{"login":"alice"}', stderr="HTTP/1.1 200 OK")
        return CommandResult(exit_code=1, stderr="Error: no available login")

    assert auth_status("gitea", runner).authenticated is True
    assert len(calls) == 3


def test_portable_auth_keeps_protected_credentials_authoritative(tmp_path):
    """@brief A saved scoped account cannot fall back into another user's CLI credentials."""
    from adore.profiles import ProfileStore
    from adore.repository_auth import save_connection

    profiles = ProfileStore(tmp_path / "profiles")
    profile = profiles.create("example")
    directory = profiles.profile_dir("example")
    save_connection(
        directory,
        {
            "schema": 1,
            "project_id": profile.project_id,
            "provider": "gitea",
            "repository": "owner/repo",
            "login": "",
            "server": "https://forge.example",
            "token": "protected-secret",
            "account": "alice",
        },
    )
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        assert argv[:2] == ["tea", "api"]
        assert "XDG_CONFIG_HOME" in kwargs["env"]
        return CommandResult(exit_code=1, stderr="Error: no available login")

    result = project_runner(directory, configured(), runner)(["tea", "api", "user"])
    assert result.exit_code == 1 and len(calls) == 1


def test_portable_auth_retry_is_single_and_bounded(tmp_path, monkeypatch):
    """@brief A deadline reached during discovery prevents replaying the API operation."""
    account(tmp_path, monkeypatch, "Linux")
    ticks = iter([0, 1, 2, 3, 20])
    monkeypatch.setattr("adore.gitea_auth.monotonic", lambda: next(ticks))
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        assert 0 < kwargs["timeout"] <= 8
        return (
            CommandResult(stdout=json.dumps([row()]))
            if argv[1] == "logins"
            else CommandResult(exit_code=1, stderr="Error: no available login")
        )

    with pytest.raises(ForgeError, match="gitea_auth_invalid"):
        project_runner(tmp_path, configured(), runner)(["tea", "api", "user"], timeout=8)
    assert len(calls) == 2


@pytest.mark.parametrize("tail", [["--login"], ["--login", ""], ["--login", "a", "--login", "b"]])
def test_portable_auth_rejects_invalid_explicit_login_arguments(tmp_path, tail):
    """@brief Invalid or duplicate login options cannot change the selected authority."""

    def runner(*args, **kwargs):
        raise AssertionError("untrusted argv reached CLI")

    with pytest.raises(ForgeError, match="gitea_auth_invalid"):
        project_runner(tmp_path, configured(), runner)(["tea", "api", "user", *tail])


# END OF FILE
