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
@file test_identity.py
@brief Tests for marker-based identity and slug-derived naming.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.1.1
"""

from __future__ import annotations

# IMPORTS
from adore.identity import AgentIdentity

# CONSTANTS

IDENTITY = AgentIdentity(name="ADORE", slug="adore")

# PUBLIC API / TESTS


def test_derived_names() -> None:
    """
    @brief   All slug-derived identifiers follow design doc 5c.
    @version 0.1.1
    """
    assert IDENTITY.tag == "[ADORE]"
    assert IDENTITY.store_root == ".adore"
    assert IDENTITY.questions_file == "ADORE_QUESTIONS.md"
    assert IDENTITY.branch("gitlab-x-14") == "adore/gitlab-x-14"
    assert IDENTITY.container_name("gitlab-x-14") == "adore-run-gitlab-x-14"


def test_marker_round_trip() -> None:
    """
    @brief   A built marker parses back to its fields.
    @version 0.1.0
    """
    marker = IDENTITY.make_marker("gitlab-x-14", "status", state="working", stage="intake")
    fields = IDENTITY.parse_marker(f"some visible text\n{marker}")
    assert fields == {
        "run": "gitlab-x-14",
        "kind": "status",
        "state": "working",
        "stage": "intake",
    }


def test_human_comments_have_no_marker() -> None:
    """
    @brief   Comments without the marker are treated as human (resume signal).
    @version 0.1.1
    """
    assert not IDENTITY.is_own_comment("Looks good, please use variant B.")
    assert not IDENTITY.is_own_comment("")
    assert IDENTITY.is_own_comment("x\n<!-- adore:run=r kind=question -->")


def test_marker_is_slug_scoped() -> None:
    """
    @brief   Another agent's marker is not mistaken for ours.
    @version 0.1.0
    """
    other = AgentIdentity(name="Robo", slug="robo")
    body = "hello\n" + other.make_marker("r-1", "status")
    assert not IDENTITY.is_own_comment(body)
    assert other.is_own_comment(body)


def test_status_comment_format() -> None:
    """
    @brief   The status comment carries the visible line plus hidden marker
             (design doc 5d).
    @version 0.1.1
    """
    body = IDENTITY.status_comment("gitlab-x-14", "working", "intake", "2026-07-02 14:02")
    lines = body.splitlines()
    # Leads with the same [ADORE] tag as every other comment kind (uniform prefix).
    assert lines[0].startswith(IDENTITY.tag + " ")
    assert lines[0] == (
        "[ADORE] status: working - stage intake - run gitlab-x-14 - updated 2026-07-02 14:02"
    )
    fields = IDENTITY.parse_marker(body)
    assert fields is not None
    assert fields["kind"] == "status"
    assert fields["state"] == "working"


def test_first_marker_wins_when_body_has_two() -> None:
    """
    @brief   An edited/quoted body carrying two markers parses the first one
             deterministically.
    @version 0.1.0
    """
    body = (
        IDENTITY.make_marker("run-a", "status", state="working")
        + "\nquoted reply below\n"
        + IDENTITY.make_marker("run-b", "question")
    )
    fields = IDENTITY.parse_marker(body)
    assert fields is not None
    assert fields["run"] == "run-a"


def test_marker_split_across_lines_still_parses() -> None:
    """
    @brief   A marker re-wrapped onto several lines (platform editing, manual
             quoting) is still recognized as ours.
    @version 0.1.1
    """
    body = "status\n<!-- adore:run=run-x\nkind=status\nstate=parked -->"
    fields = IDENTITY.parse_marker(body)
    assert fields == {"run": "run-x", "kind": "status", "state": "parked"}


def test_malformed_marker_fails_closed_as_human() -> None:
    """
    @brief   A broken marker (no closing arrow) yields no fields; ambiguous
             comments count as human, which at worst re-asks a question.
    @version 0.1.1
    """
    assert IDENTITY.parse_marker("<!-- adore:run=r kind=status") is None


# END OF FILE
