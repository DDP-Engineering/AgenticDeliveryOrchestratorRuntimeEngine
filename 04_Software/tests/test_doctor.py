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
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Sequence
import json
from pathlib import Path

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
    """
    assert doctor._os_key("Windows") == "windows"
    assert doctor._os_key("Linux") == "linux"
    assert doctor._os_key("Darwin") == "macos"
    assert doctor._os_key("FreeBSD") == "other"


# PUBLIC API / TESTS - tool probes


def test_detect_git_present_and_absent() -> None:
    """
    @brief   A clean `git --version` -> present with version; exit 127 -> absent.
    """
    present = doctor.detect_git(FakeRunner({"git --version": _ok("git version 2.43.0")}))
    assert present.present and present.version == "git version 2.43.0"
    absent = doctor.detect_git(FakeRunner({}))          # nothing registered -> 127
    assert not absent.present and "not found" in absent.detail


def test_detect_platform_cli_maps_kind_and_rejects_unknown() -> None:
    """
    @brief   gitlab -> glab, github -> gh, gitea -> tea; an unknown kind
             fails closed.
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
    """
    status = doctor.detect_executor(runner=FakeRunner({"opencode --version": _ok("opencode 1.0")}))
    assert status.name == "opencode" and status.present


def test_detect_all_aggregate() -> None:
    """
    @brief   detect_all runs one probe of each and returns a full report.
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
    """
    assert "no setup guidance" in doctor.guidance_for("nonsense", "linux")


def test_auth_component_for_kind() -> None:
    """
    @brief   Maps a platform kind to its auth-guidance component; rejects others.
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
    """
    win = doctor.guidance_for(doctor.TEA, "windows")
    lin = doctor.guidance_for(doctor.TEA, "linux")
    assert "dl.gitea.com/tea" in win and "dl.gitea.com/tea" in lin and win != lin
    token = doctor.guidance_for(doctor.TEA_AUTH, "windows")
    assert token == doctor.guidance_for(doctor.TEA_AUTH, "linux")
    assert "tea login add" in token and "[platform] login" in token


def _aegis_repo(tmp_path: Path) -> Path:
    """
    @brief      A directory carrying the AEGIS Python companion CLI.
    @param[in]  tmp_path pytest tmp dir.
    @return     The repository root.
    """
    root = tmp_path / "target-repo"
    wrapper = root / ".agentic" / "aegis.py"
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    return root


def test_aegis_probe_accepts_a_valid_05_schema_1_payload(tmp_path: Path) -> None:
    """
    @brief   Version 0.5.x plus schema-1 status proves target readiness.
    """
    root = _aegis_repo(tmp_path)
    runner = FakeRunner({
        "python .agentic/aegis.py --version": CommandResult(
            exit_code=0, stdout="aegis 0.5.2\n",
        ),
        "python .agentic/aegis.py status --all --json": CommandResult(
            exit_code=0,
            stdout=json.dumps({
                "schema": 1, "command": "status", "tasks": [],
                "hidden_done": 0, "unreadable": [],
            }),
        ),
    })

    status = doctor.detect_aegis(root, runner)

    assert status.ok
    assert status.wrapper_present and status.config_valid
    assert status.schema_version == 1 and status.version == "aegis 0.5.2"
    assert runner.calls[0] == ["python", ".agentic/aegis.py", "--version"]


def test_aegis_probe_reports_a_missing_payload(tmp_path: Path) -> None:
    """
    @brief   No companion CLI means no AEGIS 0.5 payload; no command runs.
             command it knows will fail.
    """
    runner = FakeRunner({})
    status = doctor.detect_aegis(tmp_path / "bare", runner)
    assert not status.ok and not status.wrapper_present
    assert ".agentic/aegis.py is missing" in status.detail
    assert runner.calls == []


def test_aegis_probe_fails_closed_on_a_blocked_or_unparseable_answer(
    tmp_path: Path,
) -> None:
    """
    @brief   A nonconforming status and non-JSON output both read as
             not-ready with the detail preserved; neither is mistaken for a
             healthy repository.
    """
    root = _aegis_repo(tmp_path)
    blocked = doctor.detect_aegis(root, FakeRunner({
        "python .agentic/aegis.py --version": CommandResult(
            exit_code=0, stdout="aegis 0.5.0",
        ),
        "python .agentic/aegis.py status --all --json": CommandResult(
            exit_code=1,
            stdout=json.dumps({
                "schema": 1, "command": "status", "tasks": [],
                "unreadable": [{"file": "bad.md"}],
            }),
        ),
    }))
    assert not blocked.ok and blocked.wrapper_present
    assert "unreadable" in blocked.detail

    garbage = doctor.detect_aegis(root, FakeRunner({
        "python .agentic/aegis.py --version": CommandResult(
            exit_code=0, stdout="aegis 0.5.0",
        ),
        "python .agentic/aegis.py status --all --json": CommandResult(
            exit_code=2,
            stderr="No AEGIS Python runtime is available.",
        ),
    }))
    assert not garbage.ok
    assert "No AEGIS Python runtime" in garbage.detail


def test_aegis_probe_rejects_wrong_schema_or_version(tmp_path: Path) -> None:
    """
    @brief   ADORE 0.5 speaks only AEGIS 0.5.x schema 1.
    """
    root = _aegis_repo(tmp_path)
    status = doctor.detect_aegis(root, FakeRunner({
        "python .agentic/aegis.py --version": CommandResult(
            exit_code=0, stdout="aegis 0.5.0",
        ),
        "python .agentic/aegis.py status --all --json": CommandResult(
            exit_code=0,
            stdout=json.dumps({
                "schema": 2, "command": "status", "tasks": [],
                "hidden_done": 0, "unreadable": [],
            }),
        ),
    }))
    assert not status.ok and status.config_valid
    assert status.schema_version == 2
    assert "requires schema 1" in status.detail

    wrong = doctor.detect_aegis(root, FakeRunner({
        "python .agentic/aegis.py --version": CommandResult(
            exit_code=0, stdout="aegis 0.6.0",
        ),
    }))
    assert not wrong.ok and "0.6.0" in wrong.detail


def test_aegis_guidance_names_hard_break(tmp_path: Path) -> None:
    """
    @brief   Guidance states the 0.5-only contract and no 3.x migration.
    """
    text = doctor.guidance_for(doctor.AEGIS, "linux")
    assert text == doctor.guidance_for(doctor.AEGIS, "windows")
    assert "0.5" in text and "3.x" in text and "no" in text.lower()


# END OF FILE
