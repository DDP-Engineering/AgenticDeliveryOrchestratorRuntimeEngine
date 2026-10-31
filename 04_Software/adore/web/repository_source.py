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
@file repository_source.py
@brief Enrollment from a repository URL: parsing, forge detection and the clone boundary.
@details Only https, http and ssh (including scp-like user@host:path) addresses without
         passwords, queries or fragments are accepted. Forge kind comes from the public
         hosts or from a matching server tea login. Commands run through the injected
         runner with prompts disabled, so a missing credential fails instead of hanging.
@example
    parsed = parse_repository_url("git@github.com:owner/repo.git")
    kind, login = detect_kind(parsed.host, tea_login_hosts(tea_output))
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from adore.util import CommandResult, CommandRunner

# CONSTANTS

MAX_URL = 512
MAX_ID = 60
LS_REMOTE_TIMEOUT = 20
CLONE_TIMEOUT = 600
MAX_REMOTE_BYTES = 2_000_000
MAX_REMOTE_BRANCHES = 10_000
_SEGMENT = re.compile(r"[A-Za-z0-9_.-]+")
_HOST = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?")
_USER = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
_SCP = re.compile(r"(?P<user>[^@\s]+)@(?P<host>[^:\s]+):(?P<path>[^\s]+)")
_HEAD = re.compile(r"^ref: refs/heads/([^\t\r\n]+)\tHEAD\r?$", re.M)
_ORIGIN = re.compile(r'^\[remote "origin"\]\s*$(.*?)(?=^\[|\Z)', re.M | re.S)
_PUBLIC = {"github.com": "github", "gitlab.com": "gitlab"}


# DATA MODELS / TYPEDEFINITIONS


class RepositorySourceError(ValueError):
    """@brief The repository address is not a supported, safe remote."""


@dataclass(frozen=True)
class RepositoryUrl:
    """@brief A validated remote: the address as given, its host, repository path and name."""

    url: str
    host: str
    repo: str
    name: str


# LOCAL HELPERS


def _git_env() -> dict[str, str]:
    """
    @brief      Environment for git that never prompts and speaks only network protocols.
    @note       An operator-set GIT_SSH_COMMAND is respected; it should keep SSH non-interactive.
    """
    return {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ALLOW_PROTOCOL": "ssh:https:http",
        "GIT_SSH_COMMAND": os.environ.get("GIT_SSH_COMMAND", "ssh -o BatchMode=yes"),
    }


# PUBLIC API


def parse_repository_url(url: object) -> RepositoryUrl:
    """
    @brief      Validate a remote address and split it into host and repository path.
    @param[in]  url Address typed by the administrator.
    @return     Parsed remote.
    @exception RepositorySourceError Unsupported scheme, credentials, query, local path or shape.
    """
    value = url.strip() if isinstance(url, str) else ""
    if (
        not value
        or len(value) > MAX_URL
        or any(ch.isspace() or not ch.isprintable() for ch in value)
        or value.startswith("-")
    ):
        raise RepositorySourceError("repository_url_invalid")
    scp = None if "://" in value else _SCP.fullmatch(value)
    if scp:
        user, host, path = scp["user"], scp["host"], scp["path"]
    else:
        try:
            parts = urlsplit(value)
            _port = parts.port  # Raises for a malformed port.
        except ValueError as exc:
            raise RepositorySourceError("repository_url_invalid") from exc
        if (
            parts.scheme not in {"https", "http", "ssh"}
            or not parts.hostname
            or parts.password is not None
            or parts.query
            or parts.fragment
            or parts.scheme != "ssh"
            and parts.username is not None
        ):
            raise RepositorySourceError("repository_url_invalid")
        user, host, path = parts.username, parts.hostname, parts.path
    path = path.strip("/")
    path = path[:-4] if path.endswith(".git") else path
    segments = path.split("/")
    if (
        not _HOST.fullmatch(host)
        or user is not None
        and not _USER.fullmatch(user)
        or len(segments) < 2
        or not all(_SEGMENT.fullmatch(item) and item not in {".", ".."} for item in segments)
    ):
        raise RepositorySourceError("repository_url_invalid")
    return RepositoryUrl(url=value, host=host.lower(), repo="/".join(segments), name=segments[-1])


def tea_login_hosts(text: str) -> dict[str, str]:
    """
    @brief      Map server hosts to tea login names from `tea logins list --output json`.
    @param[in]  text Command output; field names are matched case-insensitively.
    @return     Host to login name; empty when the output is unusable.
    """
    try:
        items = json.loads(text)
    except (TypeError, ValueError):
        return {}
    hosts: dict[str, str] = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        fields = {str(key).casefold().replace("_", ""): value for key, value in item.items()}
        name = fields.get("name")
        if not isinstance(name, str) or not name:
            continue
        try:
            url_host = (
                urlsplit(fields["url"]).hostname if isinstance(fields.get("url"), str) else None
            )
        except ValueError:
            url_host = None
        candidates = [
            url_host,
            fields.get("sshhost") if isinstance(fields.get("sshhost"), str) else None,
        ]
        for host in candidates:
            if host:
                hosts.setdefault(host.lower(), name)
    return hosts


def detect_kind(host: str, tea_hosts: dict[str, str]) -> tuple[str | None, str]:
    """
    @brief      Decide the forge kind for a host, with the Gitea login when known.
    @param[in]  host Remote host name.
    @param[in]  tea_hosts Output of tea_login_hosts.
    @return     (kind or None, tea login name or "").
    """
    if host in _PUBLIC:
        return _PUBLIC[host], ""
    if host in tea_hosts:
        return "gitea", tea_hosts[host]
    return None, ""


def default_branch(text: str) -> str | None:
    """@brief The default branch named by `git ls-remote --symref <url> HEAD` output."""
    match = _HEAD.search(text or "")
    return match.group(1) if match else None


def valid_branch_name(name: str) -> bool:
    """
    @brief      Validate a short remote branch name without executing Git.
    @param[in]  name Short name below refs/heads/, including nested branches.
    @return     True for a bounded Git branch name suitable for enrollment.
    """
    return (
        isinstance(name, str) and 0 < len(name) <= 1024
        and name != "@" and not name.startswith(("-", "/"))
        and not name.endswith(("/", "."))
        and not any(part in name for part in ("..", "//", "@{", "\\", "\ufffd"))
        and not re.search(r"[\x00-\x20\x7f~^:?*\[]", name)
        and all(not part.startswith(".") and not part.endswith(".lock")
                for part in name.split("/"))
    )


def remote_branches(text: str) -> list[str]:
    """
    @brief      Validate a bounded remote advertisement and list its branches.
    @param[in]  text Git ls-remote --symref output for HEAD and refs/heads/*.
    @return     Sorted short names; an empty repository returns an empty list.
    @exception  RepositorySourceError Corrupt, duplicate, inconsistent or oversized refs.
    @note       Symbolic HEAD supplies the default; its absence never implies main/master.
    """
    if not isinstance(text, str) or len(text) > MAX_REMOTE_BYTES:
        raise RepositorySourceError("repository_branches_invalid")
    try:
        if len(text.encode("utf-8")) > MAX_REMOTE_BYTES:
            raise ValueError("oversized remote advertisement")
        branches: set[str] = set()
        symbolic: str | None = None
        head_seen = False
        for raw in text.split("\n"):
            line = raw[:-1] if raw.endswith("\r") else raw
            if not line:
                continue
            if line.startswith("ref: "):
                match = _HEAD.fullmatch(line)
                if symbolic is not None or not match or not valid_branch_name(match[1]):
                    raise ValueError("invalid symbolic HEAD")
                symbolic = match[1]
                continue
            match = re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\t(.+)", line)
            if not match:
                raise ValueError("invalid remote ref")
            ref = match[1]
            if ref == "HEAD":
                if head_seen:
                    raise ValueError("duplicate HEAD")
                head_seen = True
                continue
            if not ref.startswith("refs/heads/"):
                raise ValueError("unexpected remote ref")
            branch = ref[len("refs/heads/"):]
            if not valid_branch_name(branch) or branch in branches:
                raise ValueError("invalid or duplicate branch")
            branches.add(branch)
            if len(branches) > MAX_REMOTE_BRANCHES:
                raise ValueError("too many remote branches")
        if symbolic is not None and symbolic not in branches:
            raise ValueError("default branch missing from advertisement")
    except ValueError as exc:
        raise RepositorySourceError("repository_branches_invalid") from exc
    return sorted(branches)


def suggest_id(name: str, available: Callable[[str], bool]) -> str:
    """
    @brief      Derive a unique project ID from a repository name.
    @param[in]  name Repository name.
    @param[in]  available True when an ID is free.
    @return     Lowercase ID matching the project ID rule, suffixed -2..-99 when taken.
    @exception RepositorySourceError No free ID within the suffix range.
    """
    slug = (
        re.sub(r"[^a-z0-9._-]+", "-", name.lower()).strip("-._")[:MAX_ID].rstrip("-._") or "project"
    )
    if available(slug):
        return slug
    for number in range(2, 100):
        candidate = f"{slug[: MAX_ID - len(str(number)) - 1].rstrip('-._')}-{number}"
        if available(candidate):
            return candidate
    raise RepositorySourceError("project_exists")


def origin_matches(first: str, second: str) -> bool:
    """@brief True when two remotes name the same host and repository (case-insensitive)."""
    try:
        a, b = parse_repository_url(first), parse_repository_url(second)
    except RepositorySourceError:
        return False
    return a.host == b.host and a.repo.casefold() == b.repo.casefold()


def read_origin(clone: Path) -> str | None:
    """@brief The `origin` URL recorded in a clone's .git/config, or None."""
    try:
        text = (clone / ".git" / "config").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    section = _ORIGIN.search(text)
    url = re.search(r"^\s*url\s*=\s*(\S+)\s*$", section.group(1), re.M) if section else None
    return url.group(1) if url else None


def ls_remote(url: str, runner: CommandRunner) -> CommandResult:
    """@brief Read every forge's HEAD and branch refs without cloning."""
    return runner(
        ["git", "ls-remote", "--symref", "--", url, "HEAD", "refs/heads/*"],
        timeout=LS_REMOTE_TIMEOUT,
        env=_git_env(),
    )


def tea_logins(runner: CommandRunner) -> dict[str, str]:
    """@brief Portable host suggestions; ambiguous or unavailable accounts need explicit choice."""
    from adore.gitea_auth import GiteaAuthError, discover_tea_logins

    try:
        rows, _ = discover_tea_logins(runner)
    except GiteaAuthError:
        return {}
    groups = {}
    for row in rows:
        for host in {urlsplit(row.url).hostname, row.ssh_host or None} - {None}:
            groups.setdefault(host.lower(), []).append(row)
    hosts = {}
    for host, logins in groups.items():
        candidates = [row for row in logins if row.default] or logins
        if len(candidates) == 1:
            hosts[host] = candidates[0].name
    return hosts


def clone(url: str, dest: Path, runner: CommandRunner) -> CommandResult:
    """@brief Clone the remote into a not-yet-existing folder with prompts disabled."""
    return runner(
        ["git", "clone", "--origin", "origin", "--", url, str(dest)],
        timeout=CLONE_TIMEOUT,
        env=_git_env(),
    )


def branch_exists(dest: Path, branch: str, runner: CommandRunner) -> bool:
    """@brief True when the clone has the remote-tracking branch origin/<branch>."""
    return runner(
        [
            "git",
            "-C",
            str(dest),
            "rev-parse",
            "--verify",
            "--quiet",
            f"refs/remotes/origin/{branch}",
        ],
        timeout=10,
    ).ok


# END OF FILE
