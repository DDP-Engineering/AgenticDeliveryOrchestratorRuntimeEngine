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


def test_auth_status_gitea_probes_verified_account_api() -> None:
    """
    @brief   Gitea authentication requires a successful account API, not CLI exit alone.
    """
    runner = FakeRunner({
        "tea api -i --method GET user": CommandResult(
            stdout='{"login":"dpasare"}', stderr="HTTP/1.1 200 OK"),
        # what the WRONG probe would see: tea exits 0 with a help-topic error
        "tea auth status": _ok("No help topic for 'auth'"),
    })
    good = doctor.auth_status("gitea", runner)
    assert good.cli == "tea"
    assert good.present and good.authenticated
    assert runner.calls == [["tea", "api", "-i", "--method", "GET", "user"]]
    bad = doctor.auth_status("gitea", FakeRunner({
        "tea api -i --method GET user": _fail("Error: no login")}))
    assert bad.present and not bad.authenticated
    missing = doctor.auth_status("gitea", FakeRunner({}))
    assert not missing.present and not missing.authenticated


@pytest.mark.parametrize("result", [
    CommandResult(stdout='{"login":"alice"}', stderr="HTTP/1.1 401 Unauthorized"),
    CommandResult(stdout='{"login":"alice","login":"bob"}', stderr="HTTP/1.1 200 OK"),
    CommandResult(stdout='{"login":"alice","bad":NaN}', stderr="HTTP/1.1 200 OK"),
    CommandResult(stdout="PRIVATE-OUTPUT", stderr="HTTP/1.1 200 OK"),
    CommandResult(stdout='{"login":"bad identity"}', stderr="HTTP/1.1 200 OK"),
    CommandResult(stdout='{"login":"alice"}'),
    CommandResult(stdout=" " * 1000001, stderr="HTTP/1.1 200 OK"),
    CommandResult(stdout='{"login":"alice"}', stderr="HTTP/1.1 200 OK", timed_out=True),
])
def test_auth_status_gitea_rejects_unverified_identity(result) -> None:
    """@brief Malformed identities, missing HTTP proof and timeout never authenticate."""
    status = doctor.auth_status("gitea", FakeRunner({"tea api": result}))
    assert status.present and not status.authenticated
    assert "Connect repository" in status.detail
    assert "PRIVATE" not in status.detail


def test_auth_status_gitea_respects_caller_credential_authority() -> None:
    """@brief A caller-owned credential scope disables external-login discovery."""
    runner = FakeRunner({"tea api": _fail("Error: no available login")})
    assert not doctor.auth_status("gitea", runner, external_auth=False).authenticated
    assert len(runner.calls) == 1


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


def test_detect_push_access_reports_a_reachable_remote(tmp_path: Path) -> None:
    """
    @brief   `git ls-remote` proves the HOST credentials ADORE pushes with,
             which the platform-CLI auth probe does not cover. It runs in the
             target clone so the remote resolves.
    """
    runner = FakeRunner({"git ls-remote": _ok("abc123\trefs/heads/main")})
    status = doctor.detect_push_access(tmp_path, runner)
    assert status.present and status.version == "origin reachable"
    assert runner.calls[0] == ["git", "ls-remote", "--heads", "origin"]


def test_detect_gitignore_flags_a_target_without_one(tmp_path: Path) -> None:
    """
    @brief   ADORE checkpoints with `git add -A` and cannot tell new source
             from generated files; only the repository's ignore rules can. A
             target without a .gitignore is flagged at setup rather than
             discovered as fifteen changed files for a two-file change.
    """
    assert not doctor.detect_gitignore(tmp_path).present
    assert "no .gitignore" in doctor.detect_gitignore(tmp_path).detail
    (tmp_path / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    assert doctor.detect_gitignore(tmp_path).present
    assert "max_files_touched" in doctor.guidance_for(doctor.GITIGNORE, "linux")


def test_detect_push_access_names_a_missing_clone_directory(tmp_path: Path) -> None:
    """
    @brief   During `adore init` the likeliest cause is a mistyped clone path.
             git run with a missing cwd fails as "no such file" on POSIX and
             WinError 267 on Windows, either of which would otherwise be
             reported as a missing git binary or a raw OS code.
    """
    status = doctor.detect_push_access(tmp_path / "not-cloned-yet", FakeRunner({}))
    assert not status.present
    assert "does not exist" in status.detail


def test_detect_push_access_surfaces_a_credential_failure(tmp_path: Path) -> None:
    """
    @brief   An unloaded SSH key fails here, at setup, instead of at
             publication - where it would discard a human approval that had
             already been given for the candidate.
    """
    runner = FakeRunner({"git ls-remote": _fail("Permission denied (publickey).")})
    status = doctor.detect_push_access(tmp_path, runner)
    assert status.present and not status.version
    assert "publickey" in status.detail
    assert "ssh-add" in doctor.guidance_for(doctor.GIT_PUSH, "linux")


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
    assert "glpat-" in token and "never values" in token
    assert "active/default authenticated host" in token
    assert "active/default authenticated host" in doctor.guidance_for(
        doctor.GH_AUTH, "linux"
    )


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


def test_aegis_probe_accepts_a_valid_015_schema_1_payload(tmp_path: Path) -> None:
    """
    @brief   Version 0.15.x plus schema-1 status proves target readiness.
    """
    root = _aegis_repo(tmp_path)
    runner = FakeRunner({
        "python .agentic/aegis.py --version": CommandResult(
            exit_code=0, stdout="aegis 0.15.2\n",
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
    assert status.schema_version == 1 and status.version == "aegis 0.15.2"
    assert runner.calls[0] == ["python", ".agentic/aegis.py", "--version"]


def test_aegis_probe_reports_a_missing_payload(tmp_path: Path) -> None:
    """
    @brief   No companion CLI means no AEGIS payload; no command runs.
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
            exit_code=0, stdout="aegis 0.15.0",
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
            exit_code=0, stdout="aegis 0.15.0",
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
    @brief   ADORE speaks only AEGIS schema 1.
    """
    root = _aegis_repo(tmp_path)
    status = doctor.detect_aegis(root, FakeRunner({
        "python .agentic/aegis.py --version": CommandResult(
            exit_code=0, stdout="aegis 0.15.0",
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

    # below the floor: AEGIS before 0.15.0 ends in a deliver stage
    too_old = doctor.detect_aegis(root, FakeRunner({
        "python .agentic/aegis.py --version": CommandResult(
            exit_code=0, stdout="aegis 0.14.9",
        ),
    }))
    assert not too_old.ok and "0.14.9" in too_old.detail

    # a different major means the companion contract itself changed
    other_major = doctor.detect_aegis(root, FakeRunner({
        "python .agentic/aegis.py --version": CommandResult(
            exit_code=0, stdout="aegis 1.0.0",
        ),
    }))
    assert not other_major.ok and "1.0.0" in other_major.detail


def test_aegis_doctor_shares_one_gate_with_the_client() -> None:
    """
    @brief   Doctor and the orchestrator never disagree about what is supported.
    @details Doctor once carried its own version regex, which silently went
             stale when the client's supported range moved. It now derives the
             answer from the client's constants, so this holds for any minor.
    """
    assert doctor.aegis_version_supported("aegis 0.15.0")
    assert doctor.aegis_version_supported("aegis 0.99.7")
    assert not doctor.aegis_version_supported("aegis 0.14.9")
    assert not doctor.aegis_version_supported("aegis 0.5.0")
    assert not doctor.aegis_version_supported("aegis 1.0.0")
    assert not doctor.aegis_version_supported("nonsense")


def test_aegis_guidance_names_hard_break(tmp_path: Path) -> None:
    """
    @brief   Guidance states the supported range and the schema it speaks.
    """
    text = doctor.guidance_for(doctor.AEGIS, "linux")
    assert text == doctor.guidance_for(doctor.AEGIS, "windows")
    assert doctor.AEGIS_SUPPORTED_TEXT in text
    assert "schema 1" in text and "only" in text.lower()


# END OF FILE
