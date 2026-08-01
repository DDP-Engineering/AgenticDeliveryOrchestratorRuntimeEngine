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
@file __init__.py
@brief Git-platform adapter subpackage (GitLab/GitHub/Gitea behind one interface).
@details Exposes the adapter contract, the data types, and the factory that
         selects the concrete adapter from [platform] config.
"""

from __future__ import annotations

# IMPORTS
from adore.forge.base import Comment, Forge, ForgeError, MergeRequest, Ticket
from adore.forge.gitea import GiteaForge
from adore.forge.github import GitHubForge
from adore.forge.gitlab import GitLabForge
from adore.util import CommandRunner, run_command

# PUBLIC API

__all__ = [
    "Comment",
    "Forge",
    "ForgeError",
    "GiteaForge",
    "GitHubForge",
    "GitLabForge",
    "MergeRequest",
    "Ticket",
    "build_forge",
]


def build_forge(
    kind: str, repo: str, runner: CommandRunner = run_command, *, login: str = ""
) -> Forge:
    """
    @brief      Construct the configured Git-platform adapter.
    @param[in]  kind Platform kind ("gitlab" | "github" | "gitea").
    @param[in]  repo Repository path/slug for the platform CLI.
    @param[in]  runner Command runner (injectable for tests).
    @param[in]  login tea login name ([platform] login); gitea only.
    @return     A concrete Forge.
    @exception  ValueError When the kind is unknown, or login is set for a
                kind that has no login concept.
    """
    if login and kind != "gitea":
        raise ValueError(f"platform login is only supported for gitea, not {kind!r}")
    if kind == "gitlab":
        return GitLabForge(repo, runner)
    if kind == "github":
        return GitHubForge(repo, runner)
    if kind == "gitea":
        return GiteaForge(repo, runner, login=login)
    raise ValueError(f"unsupported platform kind: {kind}")


# END OF FILE
