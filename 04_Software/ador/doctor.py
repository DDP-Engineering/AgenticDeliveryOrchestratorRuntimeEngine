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
@file doctor.py
@brief Environment detection + prerequisite guidance for assisted setup
       (Assisted_Config_And_Profiles_Plan, task 2).
@details The data/text layer beneath the `ador init` wizard (task 3) and a
         future `ador doctor` command. It PROBES the host for the tools ADOR
         needs - git, a container runtime (docker/podman, optionally inside
         WSL), the platform CLI (glab/gh) and its auth, the executor CLI - and
         returns typed results; and it supplies the exact, OS-specific
         install/setup instructions to print when something is missing. Every
         probe goes through the injectable CommandRunner (never a raw
         subprocess here), so the whole module is unit-testable offline with a
         fake runner; no prompting and no network calls of its own live here.
@author Eng. Dan Dumitru Pasare
@date 2026-07-05
@version 0.1.0
"""

from __future__ import annotations

# IMPORTS
from dataclasses import dataclass, field
import platform

from ador.util import CommandRunner, run_command

# CONSTANTS

# Component keys for guidance_for(); also the tool names probed.
GIT = "git"
DOCKER = "docker"
PODMAN = "podman"
WSL = "wsl"
GLAB = "glab"
GH = "gh"
GLAB_AUTH = "glab-auth"
GH_AUTH = "gh-auth"
OPENCODE = "opencode"

# Platform-CLI + auth mapping by platform kind.
_CLI_FOR_KIND = {"gitlab": GLAB, "github": GH}
_AUTH_COMPONENT_FOR_KIND = {"gitlab": GLAB_AUTH, "github": GH_AUTH}

# OS-specific (and a "*" generic) install/setup text. Kept as data so the
# wizard and `ador doctor` render identical instructions.
GUIDANCE: dict[str, dict[str, str]] = {
    GIT: {
        "windows": "Install Git for Windows: `winget install Git.Git` "
                   "(or https://git-scm.com/download/win).",
        "linux": "Install git: `sudo apt-get update && sudo apt-get install -y git`.",
    },
    DOCKER: {
        "windows": "Enable WSL2 (`wsl --install`), then install Docker Engine "
                   "INSIDE the distro (no Docker Desktop needed) and set the "
                   "runtime to `wsl -d <distro> -- docker`.",
        "linux": "Install Docker Engine: "
                 "https://docs.docker.com/engine/install/ubuntu/ .",
    },
    PODMAN: {
        "windows": "Install podman inside your WSL2 distro: "
                   "`sudo apt-get install -y podman uidmap slirp4netns`; use the "
                   "runtime `wsl -d <distro> -- podman` with "
                   'run_args=["--userns=keep-id"].',
        "linux": "Install podman: "
                 "`sudo apt-get install -y podman uidmap slirp4netns`; rootless "
                 'podman needs run_args=["--userns=keep-id"].',
    },
    WSL: {
        "windows": "Install WSL2: `wsl --install`; then install a distro (e.g. "
                   "Ubuntu-24.04) and a container runtime inside it.",
        "linux": "(WSL is a Windows feature; not applicable on Linux.)",
    },
    GLAB: {
        "windows": "Install the GitLab CLI: `winget install GLab.GLab` "
                   "(or `scoop install glab`).",
        "linux": "Install the GitLab CLI: download the .deb from the glab "
                 "releases page and `sudo apt-get install ./glab_*.deb` "
                 "(or `sudo apt-get install glab` where packaged).",
    },
    GH: {
        "windows": "Install the GitHub CLI: `winget install GitHub.cli`.",
        "linux": "Install the GitHub CLI: see "
                 "https://github.com/cli/cli/blob/trunk/docs/install_linux.md .",
    },
    GLAB_AUTH: {
        "*": (
            "Create a GitLab Personal Access Token: GitLab -> your avatar -> "
            "Preferences -> Access Tokens -> Add new token; scope `api`; role "
            "Developer (Developer cannot merge protected branches - intended, "
            "ADOR never merges). Copy it now (shown once). A GitLab PAT looks "
            "like `glpat-XXXXXXXXXXXXXXXXXXXX` (the prefix `glpat-` followed by "
            "20 characters). Then authenticate the CLI: `glab auth login` (for a "
            "corporate instance choose the hostname, e.g. gitlab.mycorp.fr, and "
            "paste the token). Alternatively set GITLAB_TOKEN in the project "
            ".env - the wizard records the key NAME, never the value."
        )
    },
    GH_AUTH: {
        "*": (
            "Create a fine-grained GitHub Personal Access Token with Contents + "
            "Pull requests + Issues (read/write), then run `gh auth login` and "
            "paste it. Alternatively set GITHUB_TOKEN in the project .env - the "
            "wizard records the key NAME, never the value."
        )
    },
    OPENCODE: {
        "*": (
            "opencode is baked into the executor image, so you only need it on "
            "the HOST for the `host` runtime. Install it per docker/README.md."
        )
    },
}

# DATA MODELS / TYPEDEFINITIONS


@dataclass
class ToolStatus:
    """
    @brief   Whether one CLI tool is present, and its reported version.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-05
    @version 0.1.0
    """

    name: str
    present: bool
    version: str = ""
    detail: str = ""


@dataclass
class AuthStatus:
    """
    @brief   Whether the platform CLI is present AND authenticated.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-05
    @version 0.1.0
    """

    kind: str            # gitlab | github
    cli: str             # glab | gh
    present: bool
    authenticated: bool
    detail: str = ""


@dataclass
class RuntimeDetection:
    """
    @brief   Host container-runtime availability (+ WSL distros on Windows).
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-05
    @version 0.1.0
    """

    docker: ToolStatus
    podman: ToolStatus
    wsl_distros: list[str] = field(default_factory=list)


@dataclass
class EnvironmentReport:
    """
    @brief   Aggregate of every probe, for the wizard and `ador doctor`.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-05
    @version 0.1.0
    """

    os_key: str
    git: ToolStatus
    runtimes: RuntimeDetection
    platform_cli: ToolStatus
    auth: AuthStatus
    executor: ToolStatus


# HELPER FUNCTIONS


def _os_key(system_name: str) -> str:
    """
    @brief      Normalize a platform.system() value to an ADOR OS key.
    @param[in]  system_name Raw platform name (e.g. "Windows", "Linux").
    @return     "windows" | "linux" | "macos" | "other".
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    name = system_name.strip().lower()
    if name.startswith("win"):
        return "windows"
    if name == "linux":
        return "linux"
    if name == "darwin":
        return "macos"
    return "other"


def _probe(runner: CommandRunner, name: str, argv: list[str]) -> ToolStatus:
    """
    @brief      Probe a tool via `<tool> --version` (or similar) through runner.
    @details    Exit 127 (binary missing, per run_command's convention) means
                absent; a clean exit yields the first stdout line as version; a
                present-but-erroring tool is reported present with a detail.
    @param[in]  runner Injectable command runner.
    @param[in]  name Component name (also the ToolStatus name).
    @param[in]  argv Command to run.
    @return     The ToolStatus.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    result = runner(argv)
    if result.exit_code == 127:
        return ToolStatus(name=name, present=False, detail="not found on PATH")
    if result.ok:
        first = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
        return ToolStatus(name=name, present=True, version=first)
    return ToolStatus(name=name, present=True, detail=(result.stderr.strip() or "error"))


# PUBLIC API


def detect_os() -> str:
    """
    @brief   The current host's ADOR OS key.
    @return  "windows" | "linux" | "macos" | "other".
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-05
    @version 0.1.0
    """
    return _os_key(platform.system())


def detect_git(runner: CommandRunner = run_command) -> ToolStatus:
    """
    @brief      Whether git is available on the host.
    @param[in]  runner Injectable command runner.
    @return     The ToolStatus for git.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    return _probe(runner, GIT, ["git", "--version"])


def detect_wsl_distros(runner: CommandRunner = run_command) -> list[str]:
    """
    @brief      Installed WSL distro names (Windows only; else empty).
    @details    `wsl -l -q` emits UTF-16 on some hosts; run_command decodes as
                UTF-8, so null bytes are stripped and blank lines dropped before
                returning the names (robust to that quirk).
    @param[in]  runner Injectable command runner.
    @return     Distro names, or [] when WSL is absent.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    result = runner(["wsl", "-l", "-q"])
    if result.exit_code == 127 or not result.ok:
        return []
    cleaned = result.stdout.replace("\x00", "").replace("﻿", "")
    return [line.strip() for line in cleaned.splitlines() if line.strip()]


def detect_runtimes(
    runner: CommandRunner = run_command, *, os_key: str | None = None
) -> RuntimeDetection:
    """
    @brief      Host container-runtime availability.
    @param[in]  runner Injectable command runner.
    @param[in]  os_key Host OS key (defaults to detect_os()); WSL distros are
                       only probed on Windows.
    @return     The RuntimeDetection.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    key = os_key or detect_os()
    docker = _probe(runner, DOCKER, ["docker", "--version"])
    podman = _probe(runner, PODMAN, ["podman", "--version"])
    distros = detect_wsl_distros(runner) if key == "windows" else []
    return RuntimeDetection(docker=docker, podman=podman, wsl_distros=distros)


def detect_platform_cli(kind: str, runner: CommandRunner = run_command) -> ToolStatus:
    """
    @brief      Whether the platform CLI for this kind is present.
    @param[in]  kind "gitlab" (glab) or "github" (gh).
    @param[in]  runner Injectable command runner.
    @return     The ToolStatus for glab/gh.
    @exception  ValueError When kind is not gitlab/github.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    cli = _CLI_FOR_KIND.get(kind)
    if cli is None:
        raise ValueError(f"unknown platform kind: {kind!r}")
    return _probe(runner, cli, [cli, "--version"])


def auth_status(kind: str, runner: CommandRunner = run_command) -> AuthStatus:
    """
    @brief      Whether the platform CLI is authenticated.
    @details    Runs `glab auth status` / `gh auth status`: exit 127 = CLI
                missing; exit 0 = authenticated; otherwise present-but-not.
    @param[in]  kind "gitlab" or "github".
    @param[in]  runner Injectable command runner.
    @return     The AuthStatus.
    @exception  ValueError When kind is not gitlab/github.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    cli = _CLI_FOR_KIND.get(kind)
    if cli is None:
        raise ValueError(f"unknown platform kind: {kind!r}")
    result = runner([cli, "auth", "status"])
    if result.exit_code == 127:
        return AuthStatus(kind=kind, cli=cli, present=False, authenticated=False,
                          detail="CLI not installed")
    detail = (result.stderr.strip() or result.stdout.strip())
    return AuthStatus(kind=kind, cli=cli, present=True, authenticated=result.ok,
                      detail=detail)


def detect_executor(name: str = OPENCODE, runner: CommandRunner = run_command) -> ToolStatus:
    """
    @brief      Whether an executor CLI is present on the host.
    @param[in]  name Executor CLI name (default opencode).
    @param[in]  runner Injectable command runner.
    @return     The ToolStatus.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    return _probe(runner, name, [name, "--version"])


def detect_all(kind: str, runner: CommandRunner = run_command) -> EnvironmentReport:
    """
    @brief      Run every probe once, for the wizard / a future `ador doctor`.
    @param[in]  kind Platform kind ("gitlab" | "github") for the CLI/auth probes.
    @param[in]  runner Injectable command runner.
    @return     The aggregate EnvironmentReport.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    key = detect_os()
    return EnvironmentReport(
        os_key=key,
        git=detect_git(runner),
        runtimes=detect_runtimes(runner, os_key=key),
        platform_cli=detect_platform_cli(kind, runner),
        auth=auth_status(kind, runner),
        executor=detect_executor(runner=runner),
    )


def auth_component_for_kind(kind: str) -> str:
    """
    @brief      The guidance component key for a platform kind's auth setup.
    @param[in]  kind "gitlab" | "github".
    @return     GLAB_AUTH / GH_AUTH.
    @exception  ValueError When kind is not gitlab/github.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    component = _AUTH_COMPONENT_FOR_KIND.get(kind)
    if component is None:
        raise ValueError(f"unknown platform kind: {kind!r}")
    return component


def guidance_for(component: str, os_key: str) -> str:
    """
    @brief      OS-specific install/setup text for a prerequisite component.
    @details    Components with a "*" entry share one instruction for all OSes
                (e.g. token creation); otherwise Windows gets its own text and
                every non-Windows OS falls back to the Linux instructions
                (the plan targets Windows + Ubuntu).
    @param[in]  component A component key (GIT, DOCKER, GLAB_AUTH, ...).
    @param[in]  os_key OS key from detect_os() / _os_key().
    @return     The guidance text (a helpful fallback for unknown components).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-05
    @version    0.1.0
    """
    entry = GUIDANCE.get(component)
    if not entry:
        return f"(no setup guidance for {component!r}; see the project docs)"
    if "*" in entry:
        return entry["*"]
    key = "windows" if os_key == "windows" else "linux"
    return entry.get(key, entry.get("linux", ""))


# END OF FILE
