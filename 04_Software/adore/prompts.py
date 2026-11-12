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
@file    prompts.py
@brief   Eager, fail-closed catalog of application-owned agent prompt fragments.
@details Fixed UTF-8 Markdown resources live beside this module. Their leading
         license comment is removed exactly; body whitespace is never normalized.
         Named string.Template values are inserted once as literal caller data.
"""

# IMPORTS
from pathlib import Path
from string import Template
from types import MappingProxyType

# CONSTANTS
PROMPT_ROOT = Path(__file__).with_name("prompts")
LEGAL_PREFIX = (
    "<!--\n"
    "Copyright (c) 2026 DDP Engineering\n"
    "This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
    "Commercial use requires a separate commercial license.\n"
    "See the LICENSE.txt file for full license details. "
    "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n"
    "-->\n"
)
FRAGMENTS = (
    "stage/intro.md",
    "stage/ticket.md",
    "stage/active-task.md",
    "stage/instructions.md",
    "stage/journal.md",
    "stage/autopilot.md",
    "stage/completion.md",
    "stage/single-stage.md",
    "stage/frame.md",
    "stage/quick-label.md",
    "stage/recovery-context.md",
    "stage/human-thread.md",
    "stage/packages-enabled.md",
    "stage/packages-disabled.md",
    "stage/network.md",
    "stage/closing.md",
    "recovery/revalidation-route.md",
    "recovery/integration-conflict.md",
    "recovery/continuation.md",
    "recovery/no-progress.md",
    "recovery/strict-verification.md",
    "review/pipeline.md",
    "review/ticket-content-changed.md",
    "system/internet-off.md",
    "system/server-internet.md",
)

# PUBLIC API


class PromptError(RuntimeError):
    """@brief A named prompt resource cannot be loaded or rendered safely."""


class PromptCatalog:
    """
    @brief   Load and validate the complete fixed catalog before use.
    @details Construction is the only read boundary; rendering never rereads files.
             No partial catalog or fallback is published when a resource is bad.
    """

    def __init__(self) -> None:
        """
        @brief Load every required resource, including unused conditional fragments.
        @exception PromptError A file is missing, unreadable, non-UTF-8, has an
                   invalid legal prefix or contains invalid dollar syntax.
        """
        templates = {}
        for fragment in FRAGMENTS:
            try:
                text = (PROMPT_ROOT / fragment).read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise PromptError(f"{fragment}: cannot read UTF-8 prompt: {exc}") from exc
            if not text.startswith(LEGAL_PREFIX):
                raise PromptError(f"{fragment}: missing or invalid leading project license comment")
            template = Template(text[len(LEGAL_PREFIX):])
            if not template.is_valid():
                raise PromptError(f"{fragment}: invalid dollar template syntax")
            templates[fragment] = template
        self._templates = MappingProxyType(templates)

    def render(self, fragment: str, **values: str) -> str:
        """
        @brief Render a loaded fragment with strict, single-pass substitution.
        @param[in] fragment Required catalog-relative Markdown filename.
        @param[in] values Named literal data; extra values are ignored.
        @return Body text with exactly the original resource whitespace.
        @exception PromptError Unknown fragment or a required value is missing.
        """
        try:
            template = self._templates[fragment]
        except KeyError as exc:
            raise PromptError(f"{fragment}: unknown prompt fragment") from exc
        try:
            return template.substitute(values)
        except KeyError as exc:
            raise PromptError(f"{fragment}: missing placeholder {exc.args[0]}") from exc


# END OF FILE
