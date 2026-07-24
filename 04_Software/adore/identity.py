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
@details No dedicated bot account is assumed: every comment ADORE posts carries
         a visible tag ("[ADORE]") plus a hidden HTML-comment marker, and any
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

from adore.branding import PRODUCT_ACRONYM, PRODUCT_SLUG

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
    @version 0.1.1
    """

    name: str = PRODUCT_ACRONYM
    slug: str = PRODUCT_SLUG

    @property
    def tag(self) -> str:
        """
        @brief   Visible comment tag, for example "[ADORE]".
        @return  The bracketed display tag.
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-02
        @version 0.1.1
        """
        return f"[{self.name}]"

    @property
    def store_root(self) -> str:
        """
        @brief   Default local state directory name (".adore").
        @return  The dot-prefixed store root.
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-02
        @version 0.1.1
        """
        return f".{self.slug}"

    @property
    def questions_file(self) -> str:
        """
        @brief   Clarification questions filename ("ADORE_QUESTIONS.md").
        @return  The uppercase slug questions filename.
        @author  Eng. Dan Dumitru Pasare
        @date    2026-07-02
        @version 0.1.1
        """
        return f"{self.slug.upper()}_QUESTIONS.md"

    def branch(self, run_id: str) -> str:
        """
        @brief      Run branch name ("adore/<run-id>").
        @param[in]  run_id Stable run identifier.
        @return     The branch name.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.1
        """
        return f"{self.slug}/{run_id}"

    def container_name(self, run_id: str) -> str:
        """
        @brief      Executor container name ("adore-run-<run-id>").
        @param[in]  run_id Stable run identifier.
        @return     The container name.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.1
        """
        return f"{self.slug}-run-{run_id}"

    def make_marker(self, run_id: str, kind: str, **extra: str) -> str:
        """
        @brief      Build the hidden machine marker line for a comment.
        @details    Rendered invisibly on GitLab and GitHub, for example:
                    `<!-- adore:run=gitlab-x-14 kind=status state=working -->`.
        @param[in]  run_id Stable run identifier.
        @param[in]  kind Comment kind (status | question | delivery).
        @param[in]  extra Additional key=value fields (state, stage, ...).
        @return     The marker line.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-02
        @version    0.1.1
        """
        parts = [f"run={run_id}", f"kind={kind}"]
        parts.extend(f"{key}={value}" for key, value in extra.items())
        return f"<!-- {self.slug}:{' '.join(parts)} -->"

    def parse_marker(self, body: str) -> dict[str, str] | None:
        """
        @brief      Extract this agent's marker fields from a comment body.
        @details    A marker found ONLY inside a quoted line (a Markdown
                    blockquote, leading ">") is ignored: when a human uses
                    "Reply"/"Quote" they carry ADORE's hidden marker into their
                    own comment, and counting that as ours would make resume
                    detection miss their answer. The agent always writes its
                    own marker on an unquoted line, so this never hides a
                    genuine ADORE comment.
        @param[in]  body Full comment text.
        @return     Mapping of marker fields (run, kind, ...), or None when the
                    comment carries no unquoted marker (that is, it is human).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-24
        @version    0.2.0
        """
        pattern = re.compile(rf"<!--\s*{re.escape(self.slug)}:(.*?)-->", re.DOTALL)
        # Drop blockquote lines before matching, then search the remainder with
        # DOTALL so a legitimately multi-line marker still parses. A marker that
        # survives only inside quoted lines is gone, so a quoted reply is human.
        unquoted = "\n".join(
            line for line in (body or "").splitlines()
            if not line.lstrip().startswith(">")
        )
        match = pattern.search(unquoted)
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
        @details    Leads with the visible tag ("[ADORE]") like every other
                    comment the agent posts, so all ADORE comments share one
                    prefix on the ticket.
        @param[in]  run_id Stable run identifier.
        @param[in]  state Run state (working | parked | in-review | failed...).
        @param[in]  stage Current gate (intake | requirement | ...).
        @param[in]  updated Human-readable UTC timestamp.
        @return     The full comment body (visible line + hidden marker).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-05
        @version    0.2.1
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
