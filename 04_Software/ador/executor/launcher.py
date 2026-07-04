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
@file launcher.py
@brief Configurable executor launcher and factory.
@details Runs the configured executor headless inside the run's container,
         one gate per launch. The gate command (with the shell-quoted prompt
         embedded) is written to a script in the run's io dir and executed as
         `sh /ador/io/gate.sh` - so no prompt content ever travels through
         argv (wsl.exe splits argv elements containing spaces) and the event
         stream is captured to a file, never streamed from stdout (opencode
         buffers). `--auto` is rejected outright: it would auto-approve the
         push/merge permissions that keep the executor off the remote.
@author Eng. Dan Dumitru Pasare
@date 2026-07-03
@version 0.1.1
"""

from __future__ import annotations

# IMPORTS
import json
from pathlib import Path
import re
import shlex

from ador.executor.base import ExecTarget, Executor, GateRun
from ador.isolation import CONTAINER_IO_MOUNT, CONTAINER_WORKTREE_MOUNT

# CONSTANTS

GATE_SCRIPT = "gate.sh"
OUTPUT_FILE = "output.jsonl"
STDERR_FILE = "stderr.log"

_SESSION_ID_RE = re.compile(r'"session_?[iI][dD]"\s*:\s*"([^"]+)"')
_FORBIDDEN_FLAGS = ("--auto",)

# PUBLIC API


class OpencodeExecutor(Executor):
    """
    @brief   opencode implementation of the executor launcher.
    @details Command comes from the [executor.opencode] template with
             {prompt}, {model}, and {worktree} substituted ({worktree} is the
             container-side mount, /ador/work). Session continuation appends
             `--session <id>` so gate-by-gate driving and clarification
             resume reuse the same opencode session (prereq report section 5).
    @author  Eng. Dan Dumitru Pasare
    @date    2026-07-03
    @version 0.1.1
    """

    def __init__(
        self,
        command_template: str,
        model: str,
        questions_file: str = "ADOR_QUESTIONS.md",
    ) -> None:
        """
        @brief      Configure the opencode launcher.
        @param[in]  command_template Command template with {prompt}, {model},
                                     {worktree} placeholders.
        @param[in]  model Model in provider/model form.
        @param[in]  questions_file Worktree filename the executor writes
                                   blocking questions to.
        @exception  ValueError When the template carries a forbidden flag
                    (--auto would let the executor approve its own pushes).
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.1
        """
        for flag in _FORBIDDEN_FLAGS:
            if flag in command_template.split():
                raise ValueError(
                    f"executor command must not use {flag}: it auto-approves the "
                    "push/pr/merge permissions that keep the executor off the remote"
                )
        self.command_template = command_template
        self.model = model
        self.questions_file = questions_file

    def run_gate(
        self,
        execute: ExecTarget,
        worktree: str | Path,
        io_dir: str | Path,
        prompt: str,
        *,
        session: str = "",
        timeout: float | None = None,
    ) -> GateRun:
        """
        @brief      Run one gate headless; read every result from files.
        @details    Sequence: clear a stale questions file (its presence
                    after the gate must mean it was written by THIS gate),
                    write gate.sh into the io dir (host side; LF endings),
                    exec it in the container, then read the event stream,
                    stderr, and questions file back from the host filesystem.
                    A missing output file is not an error here - the exit
                    code carries the failure and the conductor decides.
        @param[in]  execute Exec seam bound to the run's container.
        @param[in]  worktree HOST path of the run's worktree.
        @param[in]  io_dir HOST path of the run's io exchange dir.
        @param[in]  prompt Gate instruction (never enters argv).
        @param[in]  session opencode session id to continue ("" = new).
        @param[in]  timeout Wall-clock bound (run budgets).
        @return     A GateRun describing the outcome. A "Session not found"
                    failure (session died with its container) self-heals by
                    relaunching once with a fresh session.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.3
        """
        worktree = Path(worktree)
        io_dir = Path(io_dir)
        io_dir.mkdir(parents=True, exist_ok=True)

        questions_path = worktree / self.questions_file
        questions_path.unlink(missing_ok=True)

        command = self.command_template.format(
            prompt=shlex.quote(prompt),
            model=shlex.quote(self.model),
            worktree=CONTAINER_WORKTREE_MOUNT,
        )
        if session:
            command += f" --session {shlex.quote(session)}"
        # No `exec` prefix: the template may be a compound command, and the
        # script's exit status is the command's status either way.
        script = (
            "#!/bin/sh\n"
            f"cd {CONTAINER_WORKTREE_MOUNT}\n"
            f"{command} "
            f"> {CONTAINER_IO_MOUNT}/{OUTPUT_FILE} "
            f"2> {CONTAINER_IO_MOUNT}/{STDERR_FILE}\n"
        )
        with (io_dir / GATE_SCRIPT).open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)

        result = execute(["sh", f"{CONTAINER_IO_MOUNT}/{GATE_SCRIPT}"], timeout=timeout)

        output = self._read(io_dir / OUTPUT_FILE)
        stderr = self._read(io_dir / STDERR_FILE) or result.stderr
        if not result.ok and session and "session not found" in stderr.lower():
            # the stored session died with its container (or was pruned);
            # self-heal by relaunching once with a fresh session
            return self.run_gate(execute, worktree, io_dir, prompt,
                                 session="", timeout=timeout)
        questions = self._read(questions_path)
        tokens_in, tokens_out, cost = self._extract_usage(output)
        return GateRun(
            exit_code=result.exit_code,
            has_questions=questions_path.is_file(),
            questions=questions,
            session_id=self._extract_session_id(output) or session,
            output=output,
            stderr=stderr,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
        )

    # -- internals ------------------------------------------------------------------

    @staticmethod
    def _read(path: Path) -> str:
        """
        @brief      Read a result file, tolerating its absence.
        @param[in]  path File written by the gate script (or the executor).
        @return     The content, or "" when missing/unreadable.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    @staticmethod
    def _extract_usage(output: str) -> tuple[int, int, float]:
        """
        @brief      Sum token usage and cost from the event stream.
        @details    opencode's step_finish events carry
                    part.tokens{input,output,...} and part.cost (schema
                    pinned live 2026-07-03). Tolerant of malformed lines -
                    usage capture must never break a gate.
        @param[in]  output Raw --format json event stream text.
        @return     (tokens_in, tokens_out, cost_usd) totals for the launch.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-04
        @version    0.1.0
        """
        tokens_in = tokens_out = 0
        cost = 0.0
        for line in output.splitlines():
            line = line.strip()
            if not line or '"tokens"' not in line:
                continue
            try:
                part = json.loads(line).get("part", {})
            except (json.JSONDecodeError, AttributeError):
                continue
            tokens = part.get("tokens") or {}
            tokens_in += int(tokens.get("input", 0) or 0)
            tokens_out += int(tokens.get("output", 0) or 0)
            cost += float(part.get("cost", 0) or 0)
        return tokens_in, tokens_out, cost

    @staticmethod
    def _extract_session_id(output: str) -> str:
        """
        @brief      Pull the opencode session id from the raw event stream.
        @details    Matched by key name ("sessionID"/"session_id") anywhere in
                    the stream, tolerant of the exact event nesting; the
                    schema is pinned down by the first live gate run.
        @param[in]  output Raw --format json event stream text.
        @return     The first session id found, or "".
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-03
        @version    0.1.0
        """
        match = _SESSION_ID_RE.search(output)
        return match.group(1) if match else ""


def build_executor(
    kind: str,
    command_template: str,
    model: str,
    questions_file: str = "ADOR_QUESTIONS.md",
) -> Executor:
    """
    @brief      Construct the configured executor.
    @param[in]  kind Executor kind ("opencode" | "pi" | "codex").
    @param[in]  command_template Command template for the executor.
    @param[in]  model Model in provider/model form.
    @param[in]  questions_file Clarification questions filename.
    @return     An Executor instance.
    @exception  ValueError When the kind is unknown or the template carries a
                forbidden flag.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.1
    """
    if kind == "opencode":
        return OpencodeExecutor(command_template, model, questions_file)
    raise ValueError(f"unsupported executor kind: {kind}")


# END OF FILE
