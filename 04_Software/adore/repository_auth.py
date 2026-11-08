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
@file    repository_auth.py
@brief   Project-scoped repository account verification and CLI credentials.
@details Secrets never enter command arguments, shared CLI config or executors.
"""

# IMPORTS
from dataclasses import replace
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import quote, urlsplit

from adore.forge.base import ForgeError
from adore.gitea_auth import portable_tea_runner
from adore.util import CommandRunner, run_command

# CONSTANTS
AUTH_FILE = "repository-auth.json"
_FIELDS = {"schema", "project_id", "provider", "repository", "login", "server", "token", "account"}
_CLI = {"gitea": "tea", "github": "gh", "gitlab": "glab"}
_AUTH_ENV = {
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GH_ENTERPRISE_TOKEN",
    "GITHUB_ENTERPRISE_TOKEN",
    "GH_HOST",
    "GH_CONFIG_DIR",
    "GH_DEBUG",
    "GITLAB_TOKEN",
    "GITLAB_ACCESS_TOKEN",
    "OAUTH_TOKEN",
    "GITLAB_HOST",
    "GITLAB_URI",
    "GL_HOST",
    "GITLAB_API_HOST",
    "GLAB_CONFIG_DIR",
    "GLAB_DEBUG",
    "GLAB_SKIP_TLS_VERIFY",
    "SKIP_TLS_VERIFY",
    "GLAB_ENABLE_CI_AUTOLOGIN",
    "GITLAB_CI",
}


# DATA MODELS / TYPEDEFINITIONS
class RepositoryAuthError(ForgeError):
    """@brief Value-free failure of authentication input, verification or storage."""

    def __init__(self, code: str):
        """@brief Carry a stable safe code without source values."""
        super().__init__(code)
        self.code = code


# HELPER FUNCTIONS


def validate_connection(provider: str, server: str, token: str, allow_http: bool = False) -> str:
    """@brief Validate explicit origin and token; return canonical server origin.
    @exception RepositoryAuthError If malformed or unacknowledged insecure input.
    """
    try:
        url = urlsplit(server)
        if (
            provider not in _CLI
            or not isinstance(server, str)
            or len(server) > 512
            or any(ord(c) <= 32 or ord(c) >= 127 for c in server)
            or url.scheme not in {"https", "http"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
            or "\\" in server
            or url.port == 0
            or not re.fullmatch(r"[A-Za-z0-9.:-]+", url.netloc)
            or (url.scheme == "http" and (not allow_http or provider == "github"))
            or not isinstance(token, str)
            or not 1 <= len(token) <= 4096
            or any(ord(c) <= 32 or ord(c) >= 127 for c in token)
        ):
            raise ValueError
        return f"{url.scheme}://{url.netloc.lower()}"
    except (ValueError, TypeError, AttributeError) as exc:
        raise RepositoryAuthError("repository_connection_invalid") from exc


def _object(pairs):
    """@brief Reject duplicate JSON fields at every object boundary."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def _identity(directory: Path) -> str:
    """@brief Read existing immutable profile identity without exposing metadata."""
    try:
        value = json.loads(
            (directory / "profile.json").read_text(encoding="utf-8"), object_pairs_hook=_object
        )
        identity = value["project_id"]
        if not isinstance(identity, str) or not re.fullmatch(r"[0-9a-f]{32}", identity):
            raise ValueError
        return identity
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise RepositoryAuthError("repository_credentials_corrupt") from exc


def credential_runner(value: dict, runner: CommandRunner = run_command) -> CommandRunner:
    """@brief Inject credentials only into one forge CLI; redact returned streams.
    @param[in] value Internally validated scoped record.
    @param[in] runner Injectable subprocess boundary.
    @return Scoped runner, leaving non-forge commands untouched.
    """
    provider, server, token = value["provider"], value["server"], value["token"]
    host = urlsplit(server).netloc

    def scoped(argv, *, cwd=None, timeout=None, env=None):
        """@brief Execute without shared config or command-line secrets."""
        if not argv or argv[0] != _CLI[provider]:
            return runner(argv, cwd=cwd, timeout=timeout, env=env)
        child_env = {
            k: v for k, v in (os.environ if env is None else env).items() if k not in _AUTH_ENV
        }
        with tempfile.TemporaryDirectory(prefix="adore-forge-") as temp:
            root = Path(temp)
            if provider == "gitea":
                (root / "tea").mkdir(mode=0o700)
                path = root / "tea" / "config.yml"
                payload = {
                    "logins": [
                        {
                            "name": value["login"] or "adore-project",
                            "url": server,
                            "token": token,
                            "default": True,
                            "insecure": False,
                            "version_check": False,
                        }
                    ],
                    "preferences": {"editor": False},
                }
                _write_secret(path, payload)
                child_env["XDG_CONFIG_HOME"] = temp
            elif provider == "github":
                child_env.update(GH_HOST=host, GH_CONFIG_DIR=temp, GH_PROMPT_DISABLED="1")
                child_env["GH_TOKEN" if host == "github.com" else "GH_ENTERPRISE_TOKEN"] = token
            else:
                _write_secret(
                    root / "config.yml",
                    {
                        "host": host,
                        "hosts": {
                            host: {"api_host": host, "api_protocol": urlsplit(server).scheme}
                        },
                    },
                )
                child_env.update(
                    GITLAB_HOST=server,
                    GITLAB_TOKEN=token,
                    GLAB_CONFIG_DIR=temp,
                    GLAB_NO_PROMPT="1",
                    GLAB_USE_KEYRING="false",
                )
            result = runner(argv, cwd=cwd, timeout=timeout, env=child_env)
        return replace(
            result,
            stdout=result.stdout.replace(token, "[REDACTED]"),
            stderr=result.stderr.replace(token, "[REDACTED]"),
        )

    return scoped


def _write_secret(path: Path, value: dict) -> None:
    """@brief Atomically publish a protected JSON file without following symlinks."""
    fd, temp = tempfile.mkstemp(prefix=".auth-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.chmod(temp, 0o600)
            json.dump(value, stream, ensure_ascii=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


# PUBLIC API


def verify_connection(
    config,
    project_id: str,
    server: str,
    token: str,
    allow_http: bool,
    runner: CommandRunner = run_command,
) -> dict:
    """@brief Verify account and exact repository through bounded read-only CLI calls.
    @return Internal secret-bearing record; caller must return only connection_view.
    @exception RepositoryAuthError On invalid input or unusable verification.
    """
    platform = config.platform
    value = {
        "schema": 1,
        "project_id": project_id,
        "provider": platform.kind,
        "repository": platform.repo,
        "login": platform.login,
        "server": validate_connection(platform.kind, server, token, allow_http),
        "token": token,
        "account": "",
    }
    scoped = credential_runner(value, runner)
    endpoint = (
        f"projects/{quote(platform.repo, safe='')}"
        if platform.kind == "gitlab"
        else f"repos/{platform.repo}"
    )
    try:
        responses = []
        for route in ("user", endpoint):
            argv = [_CLI[platform.kind], "api"]
            if platform.kind == "gitea":
                argv += ["-i", "--method", "GET", "--login", platform.login or "adore-project"]
            else:
                argv += ["--method", "GET"]
            result = scoped([*argv, route], timeout=8)
            statuses = re.findall(r"^HTTP/[\d.]+\s+(\d{3})", result.stderr, re.MULTILINE)
            if (
                not result.ok
                or result.timed_out
                or len(result.stdout) > 1048576
                or platform.kind == "gitea"
                and (not statuses or not 200 <= int(statuses[-1]) < 300)
            ):
                raise ValueError
            data = json.loads(result.stdout, object_pairs_hook=_object)
            if not isinstance(data, dict):
                raise ValueError
            responses.append(data)
        account = responses[0].get("username" if platform.kind == "gitlab" else "login")
        repository = responses[1].get(
            "path_with_namespace" if platform.kind == "gitlab" else "full_name"
        )
        if (
            not isinstance(account, str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", account)
            or not isinstance(repository, str)
            or repository.casefold() != platform.repo.casefold()
        ):
            raise ValueError
        value["account"] = account
        return value
    except (OSError, ValueError, TypeError, AttributeError, TimeoutError) as exc:
        raise RepositoryAuthError("repository_connection_failed") from exc


def connection_view(value: dict) -> dict:
    """@brief Return only browser-safe verified identity fields."""
    return {
        key: value[key] for key in ("project_id", "provider", "server", "repository", "account")
    }


def save_connection(directory: Path, value: dict) -> None:
    """@brief Bind successful verification to existing profile and publish privately.
    @exception RepositoryAuthError On identity change or storage failure.
    """
    if _identity(directory) != value["project_id"]:
        raise RepositoryAuthError("repository_credentials_corrupt")
    try:
        _write_secret(directory / AUTH_FILE, value)
    except OSError as exc:
        raise RepositoryAuthError("repository_credentials_store_failed") from exc


def load_connection(directory: Path, config) -> dict | None:
    """@brief Read validated private profile credentials for scoped use or redaction.
    @exception RepositoryAuthError Corruption/scope mismatch never falls back.
    """
    path = directory / AUTH_FILE
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise RepositoryAuthError("repository_credentials_corrupt") from exc
    try:
        if path.is_symlink() or path.stat().st_size > 16384:
            raise ValueError
        if os.name != "nt" and path.stat().st_mode & 0o077:
            raise ValueError
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object)
        if (
            not isinstance(value, dict)
            or set(value) != _FIELDS
            or type(value["schema"]) is not int
            or value["schema"] != 1
            or any(not isinstance(value[k], str) for k in _FIELDS - {"schema"})
            or value["project_id"] != _identity(directory)
            or (value["provider"], value["repository"], value["login"])
            != (config.platform.kind, config.platform.repo, config.platform.login)
            or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", value["account"])
        ):
            raise ValueError
        if (
            validate_connection(value["provider"], value["server"], value["token"], True)
            != value["server"]
        ):
            raise ValueError
    except (OSError, ValueError, TypeError, KeyError, RepositoryAuthError) as exc:
        raise RepositoryAuthError("repository_credentials_corrupt") from exc
    return value


def project_runner(directory: Path, config, runner: CommandRunner = run_command) -> CommandRunner:
    """@brief Load validated profile credentials into a scoped command runner.
    @return Protected scoped runner, portable external tea runner, or other forge runner.
    @exception RepositoryAuthError Corruption/scope mismatch never falls back.
    """
    value = load_connection(directory, config)
    if value is not None:
        return credential_runner(value, runner)
    return (portable_tea_runner(runner, login=config.platform.login)
            if config.platform.kind == "gitea" else runner)


# END OF FILE
