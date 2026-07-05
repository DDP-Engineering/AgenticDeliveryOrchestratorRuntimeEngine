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
@file identity.py
@brief Marker-based agent identity and derived naming (design doc 5c/5d).
@details No dedicated bot account is assumed: every comment ADOR posts carries
         a visible tag ("[ADOR]") plus a hidden HTML-comment marker, and any
         comment without the marker is treated as human. This module builds and
         parses those markers, formats the status comment, and derives every
         slug-based name (branch, container, state dir, questions file).
@author Eng. Dan Dumitru Pasare
@date 2026-07-05
@version 0.1.1
"""

from __future__ import annotations

# IMPORTS
from dataclasses import dataclass
import re

# CONSTANTS

_TOKEN_RE = re.compile(r"([A-Za-z0-9_-]+)=(\S+)")

# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True)
class AgentIdentity:
    """
    @brief   The configured bot identity plus every name derived from it.
    @details Renaming the bot is a single config change; all derived
             identifiers (5c) flow from name/slug through this class.
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-02
    @version 0.1.0
    """

    name: str = "ADOR"
    slug: str = "ador"

    @property
    def tag(self) -> str:
        """
        @brief   Visible comment tag, for example "[ADOR]".
        @return  The bracketed display tag.
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-02
        @version 0.1.0
        """
        return f"[{self.name}]"

    @property
    def store_root(self) -> str:
        """
        @brief   Default local state directory name (".ador").
        @return  The dot-prefixed store root.
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-02
        @version 0.1.0
        """
        return f".{self.slug}"

    @property
    def questions_file(self) -> str:
        """
        @brief   Clarification questions filename ("ADOR_QUESTIONS.md").
        @return  The uppercase slug questions filename.
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-02
        @version 0.1.0
        """
        return f"{self.slug.upper()}_QUESTIONS.md"

    def branch(self, run_id: str) -> str:
        """
        @brief      Run branch name ("ador/<run-id>").
        @param[in]  run_id Stable run identifier.
        @return     The branch name.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        return f"{self.slug}/{run_id}"

    def container_name(self, run_id: str) -> str:
        """
        @brief      Executor container name ("ador-run-<run-id>").
        @param[in]  run_id Stable run identifier.
        @return     The container name.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        return f"{self.slug}-run-{run_id}"

    def make_marker(self, run_id: str, kind: str, **extra: str) -> str:
        """
        @brief      Build the hidden machine marker line for a comment.
        @details    Rendered invisibly on GitLab and GitHub, for example:
                    `<!-- ador:run=gitlab-x-14 kind=status state=working -->`.
        @param[in]  run_id Stable run identifier.
        @param[in]  kind Comment kind (status | question | delivery).
        @param[in]  extra Additional key=value fields (state, stage, ...).
        @return     The marker line.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        parts = [f"run={run_id}", f"kind={kind}"]
        parts.extend(f"{key}={value}" for key, value in extra.items())
        return f"<!-- {self.slug}:{' '.join(parts)} -->"

    def parse_marker(self, body: str) -> dict[str, str] | None:
        """
        @brief      Extract this agent's marker fields from a comment body.
        @param[in]  body Full comment text.
        @return     Mapping of marker fields (run, kind, ...), or None when the
                    comment carries no marker (that is, it is human).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        pattern = re.compile(rf"<!--\s*{re.escape(self.slug)}:(.*?)-->", re.DOTALL)
        match = pattern.search(body or "")
        if not match:
            return None
        return dict(_TOKEN_RE.findall(match.group(1)))

    def is_own_comment(self, body: str) -> bool:
        """
        @brief      True when a comment body carries this agent's marker.
        @details    Comments without the marker are treated as human (resume
                    detection, section 9).
        @param[in]  body Full comment text.
        @return     Ownership flag.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.0
        """
        return self.parse_marker(body) is not None

    def status_comment(self, run_id: str, state: str, stage: str, updated: str) -> str:
        """
        @brief      Format the single edited status comment (design doc 5d).
        @details    Leads with the visible tag ("[ADOR]") like every other
                    comment the agent posts, so all ADOR comments share one
                    prefix on the ticket.
        @param[in]  run_id Stable run identifier.
        @param[in]  state Run state (working | parked | in-review | failed...).
        @param[in]  stage Current gate (intake | requirement | ...).
        @param[in]  updated Human-readable UTC timestamp.
        @return     The full comment body (visible line + hidden marker).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-05
        @version    0.2.0
        """
        visible = (
            f"{self.tag} status: {state} - stage {stage} - run {run_id} - updated {updated}"
        )
        marker = self.make_marker(run_id, "status", state=state, stage=stage)
        return f"{visible}\n{marker}"


# PUBLIC API


def identity_from_config(name: str, slug: str) -> AgentIdentity:
    """
    @brief      Build the AgentIdentity from the [agent] config values.
    @param[in]  name Display/brand name.
    @param[in]  slug Lowercase token (already derived by config loading).
    @return     A frozen AgentIdentity.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    return AgentIdentity(name=name, slug=slug)


# END OF FILE
