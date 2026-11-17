"""Eager, fail-closed catalog of application-owned agent prompt fragments."""

from pathlib import Path
from string import Template
from types import MappingProxyType

PROMPT_ROOT = Path(__file__).with_name("prompts")
# REUSE-IgnoreStart
LEGAL_PREFIX = (
    "<!--\n"
    "Copyright (c) 2026 DDP Engineering\n"
    "This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
    "Commercial use requires a separate commercial license.\n"
    "See the LICENSE.txt file for full license details. "
    "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n"
    "-->\n"
)
# REUSE-IgnoreEnd
FRAGMENTS = (
    "live/instruction.md",
    "direct/implementation.md",
    "stage/intro.md",
    "stage/resume.md",
    "stage/ticket.md",
    "stage/active-task.md",
    "stage/instructions.md",
    "stage/journal.md",
    "stage/autopilot.md",
    "stage/completion.md",
    "stage/single-stage.md",
    "stage/frame.md",
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
    "review/pipeline.md",
    "review/ticket-content-changed.md",
    "review/discussion.md",
    "system/internet-off.md",
    "system/server-internet.md",
)


class PromptError(RuntimeError):
    """A named prompt resource cannot be loaded or rendered safely."""


class PromptCatalog:
    """
    Load and validate the complete fixed catalog before use.
    Construction is the only read boundary; rendering never rereads files.
             No partial catalog or fallback is published when a resource is bad.
    """

    def __init__(self) -> None:
        """
        Load every required resource, including unused conditional fragments.
        Raises PromptError: A file is missing, unreadable, non-UTF-8, has an
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
        Render a loaded fragment with strict, single-pass substitution.
        fragment: Required catalog-relative Markdown filename.
        values: Named literal data; extra values are ignored.
        Returns: Body text with exactly the original resource whitespace.
        Raises PromptError: Unknown fragment or a required value is missing.
        """
        try:
            template = self._templates[fragment]
        except KeyError as exc:
            raise PromptError(f"{fragment}: unknown prompt fragment") from exc
        try:
            return template.substitute(values)
        except KeyError as exc:
            raise PromptError(f"{fragment}: missing placeholder {exc.args[0]}") from exc
