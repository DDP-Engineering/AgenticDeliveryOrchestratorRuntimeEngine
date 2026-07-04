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
@brief Git-platform adapter subpackage (GitLab/GitHub behind one interface).
@details Exposes the adapter contract, the data types, and the factory that
         selects the concrete adapter from [platform] config.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.1.0
"""

from __future__ import annotations

# IMPORTS
from ador.forge.base import Comment, Forge, ForgeError, MergeRequest, Ticket
from ador.forge.github import GitHubForge
from ador.forge.gitlab import GitLabForge
from ador.util import CommandRunner, run_command

# PUBLIC API

__all__ = [
    "Comment",
    "Forge",
    "ForgeError",
    "GitHubForge",
    "GitLabForge",
    "MergeRequest",
    "Ticket",
    "build_forge",
]


def build_forge(kind: str, repo: str, runner: CommandRunner = run_command) -> Forge:
    """
    @brief      Construct the configured Git-platform adapter.
    @param[in]  kind Platform kind ("gitlab" | "github").
    @param[in]  repo Repository path/slug for the platform CLI.
    @param[in]  runner Command runner (injectable for tests).
    @return     A concrete Forge.
    @exception  ValueError When the kind is unknown.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    if kind == "gitlab":
        return GitLabForge(repo, runner)
    if kind == "github":
        return GitHubForge(repo, runner)
    raise ValueError(f"unsupported platform kind: {kind}")


# END OF FILE
