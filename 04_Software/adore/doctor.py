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
@details The data/text layer beneath the `adore init` wizard (task 3) and a
         future `adore doctor` command. It PROBES the host for the tools ADORE
         needs - git, a container runtime (docker/podman, optionally inside
         WSL), the platform CLI (glab/gh/tea) and its auth, the executor CLI -
         and
         returns typed results; and it supplies the exact, OS-specific
         install/setup instructions to print when something is missing. Every
         probe goes through the injectable CommandRunner (never a raw
         subprocess here), so the whole module is unit-testable offline with a
         fake runner; no prompting and no network calls of its own live here.
"""

from __future__ import annotations

# IMPORTS
from dataclasses import dataclass, field
import json
from pathlib import Path
import platform
import re
import shlex
from time import monotonic

from adore.aegis import MINIMUM_SERIES, SUPPORTED_MAJOR, VERSION_RE
from adore.gitea_auth import GiteaAuthError, portable_tea_runner
from adore.util import CommandResult, CommandRunner, run_command, strict_json_loads

# CONSTANTS

# Component keys for guidance_for(); also the tool names probed.
GIT = "git"
DOCKER = "docker"
PODMAN = "podman"
WSL = "wsl"
GLAB = "glab"
GH = "gh"
TEA = "tea"
GLAB_AUTH = "glab-auth"
GH_AUTH = "gh-auth"
TEA_AUTH = "tea-auth"
PI = "pi"
AEGIS = "aegis"
GIT_PUSH = "git-push"
GITIGNORE = "gitignore"
_CONTAINER_CLIS = (DOCKER, PODMAN)
_WSL_DISTRO_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_. -]{0,79}")
_WSL_INTERNAL_DISTROS = {"docker-desktop", "docker-desktop-data"}
_RUNTIME_DISCOVERY_SECONDS = 30
_RUNTIME_PROBE_SECONDS = 5
_WSL_RUNTIME_PROBE_SECONDS = 18
_RUNTIME_DISCOVERY_DISTROS = 8

# The AEGIS payload contract the target repository must satisfy.
AEGIS_WRAPPER = ".agentic/aegis.py"
AEGIS_SCHEMA_VERSION = 1
#: Human form of the supported range, built from the client's own constants so
#: doctor can never disagree with the gate the orchestrator actually applies.
AEGIS_SUPPORTED_TEXT = (
    f"{SUPPORTED_MAJOR}.x at "
    f"{'.'.join(str(part) for part in (*MINIMUM_SERIES, 0))} or newer"
)

# Platform-CLI + auth mapping by platform kind.
_CLI_FOR_KIND = {"gitlab": GLAB, "github": GH, "gitea": TEA}
_AUTH_COMPONENT_FOR_KIND = {"gitlab": GLAB_AUTH, "github": GH_AUTH, "gitea": TEA_AUTH}
# Auth probe argv by kind. Kind-specific on purpose: tea has no `auth status`
# subcommand - and tea exits 0 for UNKNOWN subcommands ("No help topic"), so a
# generic `<cli> auth status` would falsely report Gitea as authenticated.
# Gitea requires an HTTP-successful account API response with a valid identity.
_AUTH_PROBE_FOR_KIND = {
    "gitlab": (GLAB, "auth", "status"),
    "github": (GH, "auth", "status"),
    "gitea": (TEA, "api", "-i", "--method", "GET", "user"),
}

# OS-specific (and a "*" generic) install/setup text. Kept as data so the
# wizard and `adore doctor` render identical instructions.
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
            "ADORE never merges). Copy it now (shown once). A GitLab PAT looks "
            "like `glpat-XXXXXXXXXXXXXXXXXXXX` (the prefix `glpat-` followed by "
            "20 characters). Then authenticate the CLI: `glab auth login` (for a "
            "corporate instance choose the hostname, e.g. gitlab.mycorp.fr, and "
            "paste the token). ADORE uses glab's active/default authenticated "
            "host, so verify it is the intended corporate instance. Alternatively "
            "set GITLAB_TOKEN in the ADORE process environment; the wizard "
            "records secret key NAMES, never values."
        )
    },
    GH_AUTH: {
        "*": (
            "Create a fine-grained GitHub Personal Access Token with Contents + "
            "Pull requests + Issues (read/write), then run `gh auth login` and "
            "paste it. ADORE uses gh's active/default authenticated host, so "
            "verify it is the intended corporate instance. Alternatively set "
            "GITHUB_TOKEN in the ADORE process environment; the wizard records "
            "secret key NAMES, never values."
        )
    },
    TEA: {
        "windows": "Install the Gitea CLI: download tea from "
                   "https://dl.gitea.com/tea/ (rename to tea.exe) and put it "
                   "on PATH.",
        "linux": "Install the Gitea CLI: download tea from "
                 "https://dl.gitea.com/tea/ and put it on PATH "
                 "(or `go install code.gitea.io/tea@latest`).",
    },
    TEA_AUTH: {
        "*": (
            "Create a Gitea access token: Gitea -> Settings -> Applications -> "
            "Generate New Token, with read/write on repository and issue "
            "(ADORE never merges; no admin scopes). Then register the login: "
            "`tea login add --name <name> --url http://<host>:<port> --token "
            "<token>` and make it the default (`tea logins default <name>`) or "
            "set `[platform] login = \"<name>\"` in the profile config."
        )
    },
    PI: {
        "*": (
            "Pi, ADORE's coding agent, is pinned in the executor base image, so "
            "you only need it on the HOST for a local (native) run. Build the "
            "base and any runtime-project image per docker/README.md."
        )
    },
    AEGIS: {
        "*": (
            f"The target repository must carry an AEGIS {AEGIS_SUPPORTED_TEXT} "
            "payload with `.agentic/aegis.py` and JSON schema 1. Install the "
            "payload in the target clone without changing its source, then "
            "re-run `adore init <profile>` to repeat this check. ADORE speaks "
            "only the AEGIS companion CLI over JSON schema 1."
        )
    },
    GITIGNORE: {
        "*": (
            "Add a `.gitignore` to the target repository covering its build "
            "artifacts and tool caches. ADORE checkpoints each stage with "
            "`git add -A`, which is what captures governed artifacts and new "
            "source the executor wrote; only the repository's own ignore rules "
            "can tell those apart from generated files. Without it those files "
            "join the candidate, consume the `max_files_touched` budget, and "
            "give the reviewer noise to read past."
        )
    },
    GIT_PUSH: {
        "*": (
            "ADORE pushes the run branch with HOST git, using the host's own "
            "credentials - the platform CLI login does not cover this. Make "
            "`git ls-remote origin` succeed in the target clone before the "
            "first run: load your SSH key into an agent (`ssh-add`), or "
            "refresh the HTTPS credential helper. Otherwise the failure "
            "surfaces only at publication, after a human has already approved "
            "the candidate, and that approval is discarded."
        )
    },
}

# DATA MODELS / TYPEDEFINITIONS


@dataclass
class ToolStatus:
    """
    @brief   Whether one CLI tool is present, and its reported version.
    """

    name: str
    present: bool
    version: str = ""
    detail: str = ""


@dataclass
class AuthStatus:
    """
    @brief   Whether the platform CLI is present AND authenticated.
    """

    kind: str            # gitlab | github | gitea
    cli: str             # glab | gh | tea
    present: bool
    authenticated: bool
    detail: str = ""


@dataclass
class RuntimeDetection:
    """
    @brief   Host container-runtime availability (+ WSL distros on Windows).
    """

    docker: ToolStatus
    podman: ToolStatus
    wsl_distros: list[str] = field(default_factory=list)


@dataclass
class AegisStatus:
    """
    @brief   Whether a target repository carries a usable AEGIS payload.
    @details The Python companion CLI must exist, report a supported version, and
             return a valid schema-1 status-list payload with no unreadable
             journals. `detail` carries the bounded failure reason.
    """

    repo_path: str
    wrapper_present: bool
    config_valid: bool
    schema_version: int | None = None
    version: str = ""
    detail: str = ""

    @property
    def ok(self) -> bool:
        """
        @brief   True when the repository is governed by usable AEGIS.
        @return  Readiness flag.
        """
        return (
            self.wrapper_present
            and self.config_valid
            and self.schema_version == AEGIS_SCHEMA_VERSION
        )


@dataclass
class EnvironmentReport:
    """
    @brief   Aggregate of every probe, for the wizard and `adore doctor`.
    """

    os_key: str
    git: ToolStatus
    runtimes: RuntimeDetection
    platform_cli: ToolStatus
    auth: AuthStatus
    executor: ToolStatus


# HELPER FUNCTIONS


def aegis_version_supported(version: str) -> bool:
    """
    @brief      Whether reported `aegis --version` text is in the supported range.
    @param[in]  version Raw text reported by the companion CLI.
    @return     True when the major matches and the minor is at or above the floor.
    @details    Delegates to the client's regex and constants rather than keeping
                a second pattern here: one gate, one place to change. Doctor once
                carried its own copy, which silently went stale.
    """
    match = VERSION_RE.fullmatch(version.strip())
    if match is None:
        return False
    major, minor, _patch = (int(item) for item in match.groups())
    return major == SUPPORTED_MAJOR and (major, minor) >= MINIMUM_SERIES


def _os_key(system_name: str) -> str:
    """
    @brief      Normalize a platform.system() value to an ADORE OS key.
    @param[in]  system_name Raw platform name (e.g. "Windows", "Linux").
    @return     "windows" | "linux" | "macos" | "other".
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
    @brief   The current host's ADORE OS key.
    @return  "windows" | "linux" | "macos" | "other".
    """
    return _os_key(platform.system())


def detect_git(runner: CommandRunner = run_command) -> ToolStatus:
    """
    @brief      Whether git is available on the host.
    @param[in]  runner Injectable command runner.
    @return     The ToolStatus for git.
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
    """
    key = os_key or detect_os()
    docker = _probe(runner, DOCKER, ["docker", "--version"])
    podman = _probe(runner, PODMAN, ["podman", "--version"])
    distros = detect_wsl_distros(runner) if key == "windows" else []
    return RuntimeDetection(docker=docker, podman=podman, wsl_distros=distros)


def inventory_runtime_argv(command: str) -> list[str] | None:
    """@brief Resolve a standard runtime command for read-only inventory probes.
    @param[in] command Configured runtime command.
    @return Fixed native or WSL prefix, or None for unsupported commands.
    """
    if command in _CONTAINER_CLIS:
        return [command]
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    if (len(argv) != 5 or argv[:2] != [WSL, "-d"]
            or not _WSL_DISTRO_NAME.fullmatch(argv[2])
            or argv[2].lower() in _WSL_INTERNAL_DISTROS
            or argv[3] not in {"--", "--exec", "-e"} or argv[4] not in _CONTAINER_CLIS):
        return None
    return [WSL, "-d", argv[2], "--exec", argv[4]]


def discover_container_commands(runner: CommandRunner = run_command) -> list[str]:
    """@brief Suggest Docker and Podman commands whose version probes succeed.
    @param[in] runner Injectable host command runner.
    @return Native commands first, then commands in detected Windows WSL distros.
    @note Both the number of distros and the total probe duration are bounded.
    """
    deadline = monotonic() + _RUNTIME_DISCOVERY_SECONDS

    def probe(argv: list[str], *, limit: int = _RUNTIME_PROBE_SECONDS) -> CommandResult:
        remaining = deadline - monotonic()
        if remaining <= 0:
            return CommandResult(argv=argv, exit_code=124, timed_out=True)
        return runner(argv, timeout=min(remaining, limit))

    found = [cli for cli in _CONTAINER_CLIS if probe([cli, "--version"]).ok]
    if detect_os() == "windows":
        distros = [name for name in dict.fromkeys(detect_wsl_distros(probe))
                   if _WSL_DISTRO_NAME.fullmatch(name)
                   and name.lower() not in _WSL_INTERNAL_DISTROS]
        for distro in distros[:_RUNTIME_DISCOVERY_DISTROS]:
            for cli in _CONTAINER_CLIS:
                argv = [WSL, "-d", distro, "--exec", cli, "--version"]
                if probe(argv, limit=_WSL_RUNTIME_PROBE_SECONDS).ok:
                    found.append(shlex.join([WSL, "-d", distro, "--", cli]))
    return found


def detect_platform_cli(kind: str, runner: CommandRunner = run_command) -> ToolStatus:
    """
    @brief      Whether the platform CLI for this kind is present.
    @param[in]  kind "gitlab" (glab), "github" (gh) or "gitea" (tea).
    @param[in]  runner Injectable command runner.
    @return     The ToolStatus for glab/gh/tea.
    @exception  ValueError When kind is not gitlab/github/gitea.
    """
    cli = _CLI_FOR_KIND.get(kind)
    if cli is None:
        raise ValueError(f"unknown platform kind: {kind!r}")
    return _probe(runner, cli, [cli, "--version"])


def auth_status(
    kind: str, runner: CommandRunner = run_command, *, external_auth: bool = True,
) -> AuthStatus:
    """
    @brief      Verify platform authentication using its account probe.
    @details    Gitea shares portable current-account discovery and requires a
                successful HTTP response with a valid, unambiguous identity.
    @param[in]  kind "gitlab", "github" or "gitea".
    @param[in]  runner Injectable command runner.
    @param[in]  external_auth False when the caller already owns credential authority.
    @return     Presence and verified authentication, with value-free Gitea guidance.
    @exception  ValueError When kind is unsupported.
    """
    probe = _AUTH_PROBE_FOR_KIND.get(kind)
    if probe is None:
        raise ValueError(f"unknown platform kind: {kind!r}")
    cli = probe[0]
    auth_runner = portable_tea_runner(runner) if kind == "gitea" and external_auth else runner
    try:
        result = auth_runner(list(probe), timeout=8)
    except GiteaAuthError as exc:
        return AuthStatus(kind, cli, True, False, str(exc))
    if result.exit_code == 127:
        return AuthStatus(kind=kind, cli=cli, present=False, authenticated=False,
                          detail="CLI not installed")
    if kind == "gitea":
        valid = False
        try:
            if len(result.stdout.encode("utf-8")) > 1_000_000:
                raise ValueError("oversized identity")
            identity = strict_json_loads(result.stdout)
            statuses = re.findall(r"HTTP/\S+\s+(\d{3})", result.stderr)
            valid = bool(
                result.ok and not result.timed_out
                and statuses and 200 <= int(statuses[-1]) < 300
                and isinstance(identity, dict) and isinstance(identity.get("login"), str)
                and re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", identity["login"])
            )
        except (ValueError, TypeError, UnicodeError):
            pass
        return AuthStatus(kind, cli, True, valid,
                          "" if valid else str(GiteaAuthError("gitea_auth_invalid")))
    detail = result.stderr.strip() or result.stdout.strip()
    return AuthStatus(kind, cli, True, result.ok, detail)


def detect_aegis(
    repo_path: str | Path,
    runner: CommandRunner = run_command,
) -> AegisStatus:
    """
    @brief      Probe a target repository for a usable AEGIS payload.
    @details    Requires `.agentic/aegis.py`, exact a supported `aegis` version version
                output, and a schema-1 `status --all --json` document. ADORE
                refuses malformed output, unknown versions/schemas and any
                unreadable journal before ticket pickup.
    @param[in]  repo_path Local clone the runs are created from.
    @param[in]  runner Injectable command runner.
    @return     The AegisStatus.
    """
    root = Path(repo_path).expanduser()
    if not (root / AEGIS_WRAPPER).is_file():
        return AegisStatus(
            repo_path=str(root), wrapper_present=False, config_valid=False,
            detail=f"{AEGIS_WRAPPER} is missing",
        )
    version_result = runner(["python", AEGIS_WRAPPER, "--version"], cwd=str(root))
    version = version_result.stdout.strip()
    if version_result.exit_code == 127:
        return AegisStatus(
            repo_path=str(root), wrapper_present=True, config_valid=False,
            detail="python is not available to run the AEGIS companion CLI",
        )
    if not version_result.ok or not aegis_version_supported(version):
        return AegisStatus(
            repo_path=str(root), wrapper_present=True, config_valid=False,
            version=version,
            detail=(version_result.stderr.strip() or version
                    or "AEGIS returned no version")[:400],
        )
    result = runner(
        ["python", AEGIS_WRAPPER, "status", "--all", "--json"], cwd=str(root)
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return AegisStatus(
            repo_path=str(root), wrapper_present=True, config_valid=False,
            version=version,
            detail=(result.stderr.strip() or result.stdout.strip()
                    or "the AEGIS companion CLI produced no JSON")[:400],
        )
    valid_shape = (
        result.ok
        and isinstance(payload, dict)
        and payload.get("command") == "status"
        and isinstance(payload.get("tasks"), list)
        and payload.get("unreadable") == []
    )
    if not valid_shape:
        detail = (result.stderr.strip() or str(payload))[:400]
        return AegisStatus(
            repo_path=str(root), wrapper_present=True, config_valid=False,
            version=version, detail=detail,
        )
    schema = payload.get("schema")
    return AegisStatus(
        repo_path=str(root), wrapper_present=True, config_valid=True,
        schema_version=schema if isinstance(schema, int) else None,
        version=version,
        detail="" if schema == AEGIS_SCHEMA_VERSION
        else f"status reports schema {schema!r}, ADORE requires "
             f"schema {AEGIS_SCHEMA_VERSION}",
    )


def detect_gitignore(repo_path: str | Path) -> ToolStatus:
    """
    @brief      Whether the target clone carries a `.gitignore`.
    @details    ADORE's per-stage checkpoints run `git add -A`, which is what
                captures the governed artifacts and any new source the executor
                wrote. It cannot tell those apart from bytecode and tool caches;
                only the repository's own `.gitignore` can. Without one, a
                pilot candidate carried four `__pycache__` files and reported
                fifteen changed files for a two-file change (live finding
                2026-09-18), consuming the `max_files_touched` budget and
                giving the reviewer noise to read past.
    @param[in]  repo_path Local clone the run worktrees are created from.
    @return     The ToolStatus for the ignore file.
    """
    root = Path(repo_path).expanduser()
    if not root.is_dir():
        return ToolStatus(
            name=GITIGNORE, present=False,
            detail=f"the target clone directory does not exist: {root}",
        )
    if (root / ".gitignore").is_file():
        return ToolStatus(name=GITIGNORE, present=True, version="present")
    return ToolStatus(
        name=GITIGNORE, present=False,
        detail="the target repository has no .gitignore",
    )


def detect_push_access(
    repo_path: str | Path,
    runner: CommandRunner = run_command,
    remote: str = "origin",
) -> ToolStatus:
    """
    @brief      Whether HOST git can reach the target remote.
    @details    `WorktreeManager.push` is ADORE's only remote-writing git call
                and runs on the host with the host's own credentials, which are
                entirely separate from the glab/gh/tea auth probed elsewhere -
                `detect_git` only proves the binary exists. Unprobed, an
                unloaded SSH key or an expired HTTPS helper stays invisible
                until `_publish` reaches the push: by then every AEGIS stage
                has run, the budget is spent, and a human has approved a
                candidate that the resulting PUSH_FAILED discards.
                `git ls-remote` performs the same authentication and ref
                negotiation as a push while writing nothing.
    @param[in]  repo_path Local clone the run worktrees are created from.
    @param[in]  runner Injectable command runner.
    @param[in]  remote Remote name ADORE pushes to.
    @return     The ToolStatus for remote access.
    """
    root = Path(repo_path).expanduser()
    if not root.is_dir():
        # Check first: git run with a missing cwd fails as "no such file" on
        # POSIX and WinError 267 on Windows, which this would otherwise report
        # as a missing git binary or a raw OS code. During `adore init` the
        # likeliest cause is simply a mistyped clone path, so say that.
        return ToolStatus(
            name=GIT_PUSH, present=False,
            detail=f"the target clone directory does not exist: {root}",
        )
    result = runner(["git", "ls-remote", "--heads", remote], cwd=str(root))
    if result.exit_code == 127:
        return ToolStatus(name=GIT_PUSH, present=False, detail="git not found on PATH")
    if result.ok:
        return ToolStatus(name=GIT_PUSH, present=True, version=f"{remote} reachable")
    return ToolStatus(
        name=GIT_PUSH,
        present=True,
        detail=(result.stderr.strip() or f"cannot reach {remote}")[:400],
    )


def detect_executor(runner: CommandRunner = run_command) -> ToolStatus:
    """@brief Verify ADORE's pinned native Pi without consulting a global Pi.
    @param[in] runner Injectable command runner.
    @return Installed Pi version or a safe remediation message.
    """
    from adore.pi_installation import PiInstallationError, verify_pi

    try:
        installation = verify_pi(runner=runner)
    except PiInstallationError as exc:
        return ToolStatus(name=PI, present=False, detail=str(exc))
    except OSError:
        return ToolStatus(name=PI, present=False, detail="Cannot read the managed Pi installation")
    return ToolStatus(name=PI, present=True, version=installation.prefix.name)


def detect_all(kind: str, runner: CommandRunner = run_command) -> EnvironmentReport:
    """
    @brief      Run every probe once, for the wizard / a future `adore doctor`.
    @param[in]  kind Platform kind ("gitlab" | "github" | "gitea") for the
                     CLI/auth probes.
    @param[in]  runner Injectable command runner.
    @return     The aggregate EnvironmentReport.
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
    @param[in]  kind "gitlab" | "github" | "gitea".
    @return     GLAB_AUTH / GH_AUTH / TEA_AUTH.
    @exception  ValueError When kind is not gitlab/github/gitea.
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
    """
    entry = GUIDANCE.get(component)
    if not entry:
        return f"(no setup guidance for {component!r}; see the project docs)"
    if "*" in entry:
        return entry["*"]
    key = "windows" if os_key == "windows" else "linux"
    return entry.get(key, entry.get("linux", ""))


# END OF FILE
