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
@file    gitea_auth.py
@brief   Portable current-account tea authentication discovery and recovery.
@details Reads bounded CLI metadata and config-file presence, never credential
         contents. Scoped credentials remain the repository_auth boundary.
"""

from __future__ import annotations

# IMPORTS
from dataclasses import dataclass
import os
from pathlib import Path
import platform
import re
from time import monotonic
from urllib.parse import urlsplit

from adore.forge.base import ForgeError
from adore.util import DEFAULT_COMMAND_TIMEOUT, CommandRunner, run_command, strict_json_loads

# CONSTANTS
_NAME = re.compile(r"[A-Za-z0-9_.-]{1,128}")
_MAX_METADATA = 1048576
_GUIDANCE = (
    "Open Project Summary > Connect repository, enter Repository server and Access token, "
    "then Verify and connect and Check host prerequisites."
)

# DATA MODELS / TYPEDEFINITIONS


class GiteaAuthError(ForgeError):
    """@brief Closed authentication cause with value-free operator recovery guidance."""

    def __init__(self, code: str):
        """@brief Preserve a safe code independently of external CLI output."""
        super().__init__(f"{code}: {_GUIDANCE}")
        self.code = code


@dataclass(frozen=True)
class TeaLogin:
    """@brief Non-secret CLI metadata; token and unknown fields are discarded."""

    name: str
    url: str
    default: bool
    ssh_host: str = ""


# LOCAL HELPERS


def _metadata(text: str) -> list[TeaLogin]:
    """@brief Reject ambiguous metadata before interpreting any authentication choice."""
    try:
        if len(text.encode("utf-8")) > _MAX_METADATA:
            raise ValueError
        rows = strict_json_loads(text)
        if not isinstance(rows, list) or len(rows) > 256:
            raise ValueError
        result, names = [], set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError
            fields = {key.casefold().replace("_", ""): value for key, value in row.items()}
            if len(fields) != len(row):
                raise ValueError
            name, url = fields.get("name"), fields.get("url")
            if not isinstance(name, str) or not _NAME.fullmatch(name) or name in names:
                raise ValueError
            if not isinstance(url, str) or len(url) > 2048 or any(ord(c) <= 32 for c in url):
                raise ValueError
            parsed = urlsplit(url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
                or "\\" in url
                or parsed.port == 0
            ):
                raise ValueError
            default = fields.get("default", False)
            if type(default) is not bool:
                if isinstance(default, str) and default.casefold() in {"true", "false"}:
                    default = default.casefold() == "true"
                else:
                    raise ValueError
            ssh = fields.get("sshhost", "")
            if not isinstance(ssh, str) or not re.fullmatch(r"[A-Za-z0-9.:[\]-]*", ssh):
                raise ValueError
            result.append(TeaLogin(name, url, default, ssh))
            names.add(name)
        return result
    except (ValueError, TypeError, AttributeError, UnicodeError) as exc:
        raise GiteaAuthError("gitea_auth_invalid") from exc


def _roots(env: dict[str, str]) -> list[Path]:
    """@brief Enumerate standard absolute account roots only; no application caches."""
    windows = platform.system() == "Windows"
    home = env.get("USERPROFILE" if windows else "HOME")
    candidates = [env.get("LOCALAPPDATA"), env.get("APPDATA")] if windows else []
    if home:
        candidates.append(str(Path(home) / ".config"))
    roots = []
    for value in candidates:
        if not value:
            continue
        root = Path(value)
        if root.is_absolute() and root not in roots:
            roots.append(root)
    return roots


def _missing(result, login: str) -> bool:
    """@brief Recognize only exact CLI errors proving no HTTP operation occurred."""
    return (
        result.exit_code == 1
        and not result.timed_out
        and not result.stdout.strip()
        and result.stderr.strip()
        in {
            "Error: no available login",
            *([f"Error: login name '{login}' does not exist"] if login else []),
        }
    )


# PUBLIC API


def discover_tea_logins(
    runner: CommandRunner = run_command,
    *,
    env: dict[str, str] | None = None,
    timeout: float = 8,
) -> tuple[list[TeaLogin], dict[str, str]]:
    """
    @brief      Discover current-account metadata within one bounded CLI budget.
    @param[in]  runner Injected CLI boundary.
    @param[in]  env Optional authoritative replacement environment.
    @param[in]  timeout Total discovery budget, capped at eight seconds.
    @return     Safe metadata and its child-only environment.
    @exception  GiteaAuthError Unavailable or malformed external metadata.
    """
    source = dict(os.environ if env is None else env)
    # Normalize case because Windows environment lookup is case-insensitive.
    explicit = next((v for k, v in source.items() if k.upper() == "XDG_CONFIG_HOME"), None)
    if explicit is not None and (not explicit or not Path(explicit).is_absolute()):
        raise GiteaAuthError("gitea_auth_invalid")
    environments = [source]
    if explicit is None:
        for root in _roots({key.upper(): value for key, value in source.items()}):
            try:
                present = (root / "tea/config.yml").is_file()
            except OSError as exc:
                raise GiteaAuthError("gitea_auth_invalid") from exc
            if present:
                environments.append({**source, "XDG_CONFIG_HOME": str(root)})
    deadline = monotonic() + min(timeout, 8)
    for child_env in environments:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise GiteaAuthError("gitea_auth_invalid")
        result = runner(
            ["tea", "logins", "list", "--output", "json"], timeout=remaining, env=child_env
        )
        if not result.ok or result.timed_out:
            raise GiteaAuthError("gitea_auth_invalid")
        logins = _metadata(result.stdout)
        if logins:
            return logins, child_env
    return [], source


def portable_tea_runner(runner: CommandRunner, *, login: str = "") -> CommandRunner:
    """
    @brief      Recover external tea API commands from pre-HTTP missing-login errors.
    @param[in]  runner Unscoped command boundary; protected credentials bypass this helper.
    @param[in]  login Configured authoritative login name, or default/sole selection.
    @return     Runner preserving successful, non-tea and HTTP-failed operations.
    @exception  GiteaAuthError Missing, ambiguous or invalid metadata; no unsafe fallback.
    """

    def external(argv, *, cwd=None, timeout=None, env=None):
        """@brief Retry the same API operation once, retaining a finite total bound."""
        if list(argv[:2]) != ["tea", "api"]:
            return runner(argv, cwd=cwd, timeout=timeout, env=env)
        limit = DEFAULT_COMMAND_TIMEOUT if timeout is None else timeout
        deadline = monotonic() + limit
        requested = login
        if "--login" in argv:
            index = list(argv).index("--login")
            if (
                list(argv).count("--login") != 1
                or index + 1 >= len(argv)
                or not isinstance(argv[index + 1], str)
                or not _NAME.fullmatch(argv[index + 1])
                or (login and argv[index + 1] != login)
            ):
                raise GiteaAuthError("gitea_auth_invalid")
            requested = argv[index + 1]
        result = runner(argv, cwd=cwd, timeout=limit, env=env)
        if not _missing(result, requested):
            return result
        logins, child_env = discover_tea_logins(
            runner, env=env, timeout=max(0, deadline - monotonic())
        )
        if not logins:
            raise GiteaAuthError("gitea_auth_missing")
        choices = (
            [item for item in logins if item.name == requested]
            if requested
            else [item for item in logins if item.default] or logins
        )
        if requested and not choices:
            raise GiteaAuthError("gitea_auth_login_missing")
        if len(choices) != 1:
            raise GiteaAuthError("gitea_auth_ambiguous")
        retry = list(argv)
        if "--login" not in retry:
            retry += ["--login", choices[0].name]
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise GiteaAuthError("gitea_auth_invalid")
        result = runner(retry, cwd=cwd, timeout=remaining, env=child_env)
        if _missing(result, choices[0].name):
            raise GiteaAuthError("gitea_auth_missing")
        return result

    return external


# END OF FILE
