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
@file test_doctor.py
@brief Tests for environment detection + prerequisite guidance - offline, with
       a fake command runner (no real git/glab/gh/tea/docker/wsl calls).
@author Eng. Dan Dumitru Pasare
@date 2026-07-29
@version 0.2.0
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Sequence

from adore import doctor
from adore.util import CommandResult
import pytest

# HELPER FUNCTIONS


class FakeRunner:
    """
    @brief   Command runner double keyed by argv prefix; unknown -> 127.
    @details Maps `" ".join(argv)` by longest-prefix to a canned result, so a
             probe for an unlisted tool looks "not found" (exit 127), exactly
             like run_command on a missing binary.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-05
    @version 0.1.0
    """

    def __init__(self, responses: dict[str, CommandResult]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    def __call__(self, argv: Sequence[str], *, cwd=None, timeout=None, env=None) -> CommandResult:
        parts = [str(part) for part in argv]
        self.calls.append(parts)
        key = " ".join(parts)
        best = ""
        for prefix in self.responses:
            if key.startswith(prefix) and len(prefix) > len(best):
                best = prefix
        if best:
            return self.responses[best]
        return CommandResult(argv=parts, exit_code=127, stderr="not found")


def _ok(stdout: str = "") -> CommandResult:
    return CommandResult(exit_code=0, stdout=stdout)


def _fail(stderr: str = "", exit_code: int = 1) -> CommandResult:
    return CommandResult(exit_code=exit_code, stderr=stderr)


# PUBLIC API / TESTS - os key mapping


def test_os_key_mapping() -> None:
    """
    @brief   platform.system() values normalize to ADORE OS keys.
    @version 0.1.1
    """
    assert doctor._os_key("Windows") == "windows"
    assert doctor._os_key("Linux") == "linux"
    assert doctor._os_key("Darwin") == "macos"
    assert doctor._os_key("FreeBSD") == "other"


# PUBLIC API / TESTS - tool probes


def test_detect_git_present_and_absent() -> None:
    """
    @brief   A clean `git --version` -> present with version; exit 127 -> absent.
    @version 0.1.0
    """
    present = doctor.detect_git(FakeRunner({"git --version": _ok("git version 2.43.0")}))
    assert present.present and present.version == "git version 2.43.0"
    absent = doctor.detect_git(FakeRunner({}))          # nothing registered -> 127
    assert not absent.present and "not found" in absent.detail


def test_detect_platform_cli_maps_kind_and_rejects_unknown() -> None:
    """
    @brief   gitlab -> glab, github -> gh, gitea -> tea; an unknown kind
             fails closed.
    @version 0.1.1
    """
    runner = FakeRunner({
        "glab --version": _ok("glab 1.105.0"),
        "gh --version": _ok("gh version 2.96.0"),
        "tea --version": _ok("Version: 0.15.0"),
    })
    assert doctor.detect_platform_cli("gitlab", runner).name == "glab"
    assert doctor.detect_platform_cli("github", runner).present
    assert doctor.detect_platform_cli("gitea", runner).name == "tea"
    with pytest.raises(ValueError):
        doctor.detect_platform_cli("bitbucket", runner)


def test_auth_status_authenticated_unauth_and_missing() -> None:
    """
    @brief   auth status distinguishes authenticated (exit 0), present-but-not
             (non-zero), and CLI-missing (exit 127).
    @version 0.1.0
    """
    good = doctor.auth_status("gitlab", FakeRunner({"glab auth status": _ok("Logged in")}))
    assert good.present and good.authenticated
    bad = doctor.auth_status("gitlab", FakeRunner({"glab auth status": _fail("not logged in")}))
    assert bad.present and not bad.authenticated
    missing = doctor.auth_status("github", FakeRunner({}))
    assert not missing.present and not missing.authenticated


def test_auth_status_gitea_probes_whoami_not_auth_status() -> None:
    """
    @brief   The gitea probe must be `tea whoami`: tea has no `auth status`
             subcommand AND exits 0 for unknown subcommands ("No help topic"),
             so the generic probe would fake an authenticated state.
    @version 0.1.0
    """
    runner = FakeRunner({
        "tea whoami": _ok("# dpasare"),
        # what the WRONG probe would see: tea exits 0 with a help-topic error
        "tea auth status": _ok("No help topic for 'auth'"),
    })
    good = doctor.auth_status("gitea", runner)
    assert good.cli == "tea"
    assert good.present and good.authenticated
    assert runner.calls == [["tea", "whoami"]]
    bad = doctor.auth_status("gitea", FakeRunner({"tea whoami": _fail("Error: no login")}))
    assert bad.present and not bad.authenticated
    missing = doctor.auth_status("gitea", FakeRunner({}))
    assert not missing.present and not missing.authenticated


def test_detect_runtimes_windows_lists_wsl_distros() -> None:
    """
    @brief   On Windows docker/podman are probed and WSL distros parsed (null
             bytes / blank lines from the UTF-16 quirk are stripped).
    @version 0.1.0
    """
    runner = FakeRunner({
        "docker --version": _ok("Docker version 27.0.0"),
        # podman intentionally absent (-> 127)
        "wsl -l -q": _ok("Ubuntu-24.04\x00\n\nUbuntu-22.04\n"),
    })
    det = doctor.detect_runtimes(runner, os_key="windows")
    assert det.docker.present and not det.podman.present
    assert det.wsl_distros == ["Ubuntu-24.04", "Ubuntu-22.04"]


def test_detect_runtimes_linux_skips_wsl() -> None:
    """
    @brief   On Linux WSL is never probed (distros always empty).
    @version 0.1.0
    """
    runner = FakeRunner({
        "podman --version": _ok("podman version 4.9.3"),
        "wsl -l -q": _ok("SHOULD-NOT-BE-USED"),
    })
    det = doctor.detect_runtimes(runner, os_key="linux")
    assert det.podman.present and det.wsl_distros == []
    assert ["wsl", "-l", "-q"] not in runner.calls   # never called on Linux


def test_detect_executor_default_opencode() -> None:
    """
    @brief   The executor probe defaults to opencode.
    @version 0.1.0
    """
    status = doctor.detect_executor(runner=FakeRunner({"opencode --version": _ok("opencode 1.0")}))
    assert status.name == "opencode" and status.present


def test_detect_all_aggregate() -> None:
    """
    @brief   detect_all runs one probe of each and returns a full report.
    @version 0.1.0
    """
    runner = FakeRunner({
        "git --version": _ok("git version 2.43.0"),
        "glab --version": _ok("glab 1.105.0"),
        "glab auth status": _ok("Logged in"),
        "opencode --version": _ok("opencode 1.0"),
    })
    report = doctor.detect_all("gitlab", runner)
    assert report.git.present and report.platform_cli.present
    assert report.auth.authenticated and report.executor.present
    assert report.os_key in ("windows", "linux", "macos", "other")


# PUBLIC API / TESTS - guidance text


def test_guidance_is_os_specific_where_it_matters() -> None:
    """
    @brief   OS-specific components differ by OS; a "*" component (token setup)
             is shared and carries the explicit PAT format.
    @version 0.1.0
    """
    win = doctor.guidance_for(doctor.GIT, "windows")
    lin = doctor.guidance_for(doctor.GIT, "linux")
    assert "winget" in win and "apt-get" in lin and win != lin
    # non-Windows OSes fall back to the Linux text
    assert doctor.guidance_for(doctor.GIT, "macos") == lin
    # token setup is shared and explicit about the format
    token = doctor.guidance_for(doctor.GLAB_AUTH, "windows")
    assert token == doctor.guidance_for(doctor.GLAB_AUTH, "linux")
    assert "glpat-" in token and "never the value" in token


def test_guidance_unknown_component_is_graceful() -> None:
    """
    @brief   An unknown component returns a helpful fallback, not a KeyError.
    @version 0.1.0
    """
    assert "no setup guidance" in doctor.guidance_for("nonsense", "linux")


def test_auth_component_for_kind() -> None:
    """
    @brief   Maps a platform kind to its auth-guidance component; rejects others.
    @version 0.1.1
    """
    assert doctor.auth_component_for_kind("gitlab") == doctor.GLAB_AUTH
    assert doctor.auth_component_for_kind("github") == doctor.GH_AUTH
    assert doctor.auth_component_for_kind("gitea") == doctor.TEA_AUTH
    with pytest.raises(ValueError):
        doctor.auth_component_for_kind("svn")


def test_guidance_covers_tea_install_and_auth() -> None:
    """
    @brief   The tea install text exists per OS and the shared auth text names
             `tea login add` plus the [platform] login alternative - the
             wizard prints these verbatim when something is missing.
    @version 0.1.0
    """
    win = doctor.guidance_for(doctor.TEA, "windows")
    lin = doctor.guidance_for(doctor.TEA, "linux")
    assert "dl.gitea.com/tea" in win and "dl.gitea.com/tea" in lin and win != lin
    token = doctor.guidance_for(doctor.TEA_AUTH, "windows")
    assert token == doctor.guidance_for(doctor.TEA_AUTH, "linux")
    assert "tea login add" in token and "[platform] login" in token


# END OF FILE
