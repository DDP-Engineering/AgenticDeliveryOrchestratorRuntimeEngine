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
@brief Pi executor launcher (ADORE's only coding agent) and its factory.
@details Runs a fresh gate through a bound backend and shared file protocol.
         Containers execute a WSL-safe shell script; native targets receive
         argv with substitutions applied after tokenization. Both retain
         bounded output, questions, usage and immutable invocation archives.
         On a container target Pi runs instead as one `pi --mode rpc`
         process per gate driven by `pi_rpc` over live pipes.
         The durable AEGIS journal is the sole session-resume authority.
         Native worktrees rely on the selected account's host permissions;
         container profiles retain their existing isolation contract.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable
import json
from pathlib import Path
import re
import shlex
import shutil

from adore.branding import (
    CONTAINER_PI_AGENT_DIR,
    CONTAINER_PI_CLI,
    CONTAINER_PI_GUARD,
    DEFAULT_QUESTIONS_FILE,
)
from adore.execution import SHELL_HEADER, ExecutionPaths
from adore.executor import pi_rpc
from adore.executor.base import ExecTarget, Executor, GateRun
from adore.util import CommandResult, utc_now_iso

# CONSTANTS

GATE_SCRIPT = "gate.sh"
OUTPUT_FILE = "output.jsonl"
STDERR_FILE = "stderr.log"
ARCHIVE_DIR = "archive"

_ARCHIVE_STEM_RE = re.compile(r"[^A-Za-z0-9_.-]+")

#: Pi RPC launch flags: RPC mode, no session file, no project trust, and none
#: of the account's personal skills, extensions, templates, themes or MCP.
PI_RPC_FLAGS = (
    "--mode", "rpc", "--no-session", "--no-approve", "--no-skills", "--no-extensions",
    "--no-prompt-templates", "--no-themes", "--no-mcp",
)
#: Pi environment for a container launch: the ADORE-owned agent directory
#: replaces the personal ~/.pi/agent; no network calls of Pi's own.
PI_RPC_ENV = {
    "PI_CODING_AGENT_DIR": CONTAINER_PI_AGENT_DIR,
    "PI_OFFLINE": "1",
    "PI_TELEMETRY": "0",
    "PI_SKIP_VERSION_CHECK": "1",
}
#: Seconds a cancelled Pi gate needs to abort and end before the conductor
#: stops the container instead.
PI_CANCEL_GRACE_SECONDS = (
    pi_rpc.ABORT_GRACE_SECONDS + pi_rpc.EXIT_GRACE_SECONDS + pi_rpc.KILL_GRACE_SECONDS + 5.0
)

# PUBLIC API


class FileProtocolExecutor(Executor):
    """
    @brief   Shared file-based gate protocol for headless CLI executors.
    @details One gate per launch: clear a stale questions file, write gate.sh
             (the command with the shell-quoted prompt) into the io dir, exec
             it in the container, and read every result back from files
             (output stream, stderr, questions) - never from live stdout.
             When an archive stem is provided, the launch copies its
             gate.sh/output/stderr/meta into an immutable archive directory.
             Every launch is a fresh session; subclasses supply only the
             optional `_extract_usage` JSON parser (default: no usage).
    """

    def __init__(
        self,
        command_template: str,
        model: str,
        questions_file: str = DEFAULT_QUESTIONS_FILE,
    ) -> None:
        """
        @brief      Configure the launcher from the [executor] section.
        @param[in]  command_template Command template with {prompt}, {model},
                                     {worktree} placeholders ({worktree} is the
                                     container mount /adore/work; unused tokens
                                     are ignored).
        @param[in]  model Model in provider/model form.
        @param[in]  questions_file Worktree filename the executor writes
                                   blocking questions to.
        """
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
        timeout: float | None = None,
        archive_stem: str = "",
        cancel: Callable[[], bool] | None = None,
    ) -> GateRun:
        """
        @brief      Run one gate headless; read every result from files.
        @details    Sequence: clear a stale questions file (its presence after
                    the gate must mean it was written by THIS gate), write
                    gate.sh into the io dir (host side; LF endings), exec it in
                    the container, then read the event stream, stderr, and
                    questions file back from the host filesystem. A missing
                    output file is not an error - the exit code carries the
                    failure and the conductor decides. When archive_stem is
                    set, the live files are copied to
                    `io/archive/<stem>-attempt1/`.

                    The launch is always a FRESH executor session, so there is
                    no session to continue and no dead-session relaunch: the
                    conductor re-sends everything a stage needs in its prompt,
                    and the durable AEGIS journal is the resume authority.
        @param[in]  execute Command/file seam bound to the run target.
        @param[in]  worktree HOST path of the run's worktree.
        @param[in]  io_dir HOST path of the run's io exchange dir.
        @param[in]  prompt Gate instruction (native argv or container script).
        @param[in]  timeout Wall-clock bound (run budgets).
        @param[in]  archive_stem Optional immutable archive name stem.
        @param[in]  cancel Unused: the conductor stops the target on cancel.
        @return     A GateRun describing the outcome.
        """
        worktree = Path(worktree)
        io_dir = Path(io_dir)
        io_dir.mkdir(parents=True, exist_ok=True)

        questions_path = worktree / self.questions_file
        questions_path.unlink(missing_ok=True)

        # The same rule the questions file already follows, for the streams:
        # whatever is read back afterwards must have been written by THIS
        # launch. A launch that produces nothing - an executor exiting 0 in a
        # second, a refused session - otherwise leaves the PREVIOUS stage's
        # transcript in place, and it is then archived as this stage's
        # evidence and re-counted by `_extract_usage` against the cost budget
        # (live finding 2026-09-18: a build attempt archived byte-identical
        # design output). Removing them first makes an empty read mean
        # exactly what it says.
        output_path = io_dir / OUTPUT_FILE
        stderr_path = io_dir / STDERR_FILE
        output_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)

        paths = getattr(execute, "paths", ExecutionPaths())
        native = getattr(execute, "run_files", None)
        command = self._build_command(
            prompt=shlex.quote(prompt),
            model=shlex.quote(self.model),
            worktree=shlex.quote(paths.worktree),
        )
        # No `exec` prefix: the template may be a compound command, and the
        # script's exit status is the command's status either way. The command
        # is wrapped in a `{ ...; }` group so the output/stderr redirection
        # applies to the WHOLE compound (e.g. `a && b`), not just its last
        # stage - otherwise a compound template would lose the earlier stage's
        # stream. Group exit status is that of the last command run, unchanged.
        script = (
            SHELL_HEADER
            + f"cd {shlex.quote(paths.worktree)}\n"
            f"{{ {command}; }} "
            f"> {shlex.quote(paths.io + '/' + OUTPUT_FILE)} "
            f"2> {shlex.quote(paths.io + '/' + STDERR_FILE)}\n"
        )
        if native is not None:
            from adore.local_execution import local_argv

            argv = local_argv(self.command_template, prompt=prompt,
                              model=self.model, worktree=paths.worktree)
            script = SHELL_HEADER + "# Native argv launch; no shell is executed.\n"
            redact = getattr(execute, "redact", lambda text: text)
            script += "# argv: " + redact(json.dumps(argv, ensure_ascii=True)) + "\n"
        with (io_dir / GATE_SCRIPT).open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)

        result = (
            native(argv, output_path, stderr_path, timeout=timeout)
            if native is not None
            else execute([paths.shell, f"{paths.io}/{GATE_SCRIPT}"], timeout=timeout)
        )

        if native is not None and hasattr(execute, "read_output"):
            execute.read_output(questions_path, optional=True)
        output = self._read(output_path)
        stderr = self._read(stderr_path) or result.stderr
        artifacts: list[str] = []
        if archive_stem:
            try:
                archive_dir = self._archive_launch(
                    io_dir,
                    archive_stem,
                    result,
                    output,
                    stderr,
                    timeout,
                    output_path.is_file(),
                    stderr_path.is_file(),
                )
            except OSError as exc:
                archive_error = f"archive write failed: {exc}"
                return GateRun(
                    exit_code=result.exit_code or 1,
                    output=output,
                    stderr=(stderr + "\n" + archive_error).strip(),
                    timed_out=result.timed_out,
                    artifact_dirs=artifacts,
                )
            artifacts.append(str(archive_dir))
        questions = self._read(questions_path)
        if native is not None:
            questions = getattr(execute, "redact", lambda text: text)(questions)
        tokens_in, tokens_out, cost, cache_read, cache_write = (
            self._extract_usage_detail(output))
        return GateRun(
            exit_code=result.exit_code,
            has_questions=questions_path.is_file(),
            questions=questions,
            output=output,
            stderr=stderr,
            timed_out=result.timed_out,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
            tokens_reported=self._tokens_reported(output),
            cost_usd=cost,
            cost_reported=self._cost_reported(output),
            artifact_dirs=artifacts,
        )

    # -- executor-specific command build + parsing (subclasses) -------------------

    def _build_command(self, *, prompt: str, model: str, worktree: str) -> str:
        """
        @brief      Compose the executor command from the configured template.
        @details    `prompt` and `model` arrive already shell-quoted.
        @param[in]  prompt Shell-quoted prompt text.
        @param[in]  model Shell-quoted model string.
        @param[in]  worktree Container worktree mount (/adore/work).
        @return     The full command string embedded into gate.sh.
        """
        return self.command_template.format(
            prompt=prompt, model=model, worktree=worktree
        )

    def _extract_usage(self, output: str) -> tuple[int, int, float]:
        """
        @brief      Sum token usage and cost from the event stream.
        @details    Default: no usage reporting (returns zeros). Executors that
                    emit usage in their stream override this. Metrics tolerate
                    zeros (design 13; the OAuth pilot ran that way).
        @param[in]  output Raw event-stream text.
        @return     (tokens_in, tokens_out, cost_usd).
        """
        return 0, 0, 0.0

    def _extract_usage_detail(
        self, output: str,
    ) -> tuple[int, int, float, int | None, int | None]:
        """@brief Preserve optional cache categories alongside total input."""
        incoming, outgoing, cost = self._extract_usage(output)
        return incoming, outgoing, cost, None, None

    def _cost_reported(self, output: str) -> bool:
        """@brief Whether the executor explicitly reported a cost value."""
        return False

    def _tokens_reported(self, output: str) -> bool:
        """@brief Whether a complete, valid token count was observed."""
        return False

    # -- internals ----------------------------------------------------------------

    def _archive_launch(
        self,
        io_dir: Path,
        archive_stem: str,
        result,
        output: str,
        stderr: str,
        timeout: float | None,
        output_present: bool,
        stderr_present: bool,
        output_file: Path | None = None,
    ) -> Path:
        """
        @brief      Copy one completed launch's live exchange files to archive.
        @details    Creates a unique directory under `io/archive`. Empty
                    output/stderr files are still written so absence is visible
                    in meta.json without making operators guess whether a file
                    was skipped.
        @param[in]  io_dir Host io exchange directory.
        @param[in]  archive_stem Base name supplied by the orchestrator.
        @param[in]  result Container exec result.
        @param[in]  output Captured output stream or "".
        @param[in]  stderr Captured stderr stream or fallback stderr.
        @param[in]  timeout Launch timeout.
        @param[in]  output_present Whether live output.jsonl existed.
        @param[in]  stderr_present Whether live stderr.log existed.
        @param[in]  output_file Bounded output file copied instead of `output`.
        @return     Archive directory path.
        @exception  OSError When any archive write fails.
        """
        archive_root = io_dir / ARCHIVE_DIR
        archive_root.mkdir(parents=True, exist_ok=True)
        # One physical launch per gate now that nothing relaunches, so the
        # suffix is constant; the collision loop below still disambiguates a
        # reused stem.
        base_name = f"{self._safe_archive_stem(archive_stem)}-attempt1"
        archive_dir = archive_root / base_name
        suffix = 2
        while archive_dir.exists():
            archive_dir = archive_root / f"{base_name}-{suffix}"
            suffix += 1
        archive_dir.mkdir()
        shutil.copy2(io_dir / GATE_SCRIPT, archive_dir / GATE_SCRIPT)
        if output_file is not None and output_file.is_file():
            shutil.copy2(output_file, archive_dir / OUTPUT_FILE)
        else:
            (archive_dir / OUTPUT_FILE).write_text(output, encoding="utf-8")
        (archive_dir / STDERR_FILE).write_text(stderr, encoding="utf-8")
        meta = {
            "created_at": utc_now_iso(),
            "archive_stem": archive_stem,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "argv": result.argv,
            "timeout": timeout,
            "output_file_present": output_present,
            "stderr_file_present": stderr_present,
        }
        (archive_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return archive_dir

    @staticmethod
    def _safe_archive_stem(value: str) -> str:
        """
        @brief      Make an archive stem safe as one directory name segment.
        @param[in]  value Raw stem.
        @return     Filesystem-safe non-empty stem.
        """
        safe = _ARCHIVE_STEM_RE.sub("-", value.strip()).strip(".-")
        return safe or "launch"

    @staticmethod
    def _read(path: Path) -> str:
        """
        @brief      Read a result file, tolerating its absence.
        @param[in]  path File written by the gate script (or the executor).
        @return     The content, or "" when missing/unreadable.
        """
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""


class PiExecutor(FileProtocolExecutor):
    """
    @brief   Pi (@earendil-works/pi-coding-agent) executor launcher.
    @details On a container target (one with a `spawn` seam) every gate runs
             one fresh `pi --mode rpc --no-session` process from the image's
             pinned installation, driven by `pi_rpc`: fixed argv, prompt over
             stdin, `abort` on the stage timeout or a cancel. The account's
             personal Pi resources are off (`PI_RPC_FLAGS`, an ADORE-owned
             agent directory) and ADORE's guard extension is loaded with `-e`,
             so it blocks `git push` and forge CLIs without project trust; the
             boundary stays that no forge credential is in the container. The
             configured [executor] command is not used there.

             A native target has no `spawn` seam and keeps the file protocol
             with the configured template, where completed `turn_end` events
             carry the usage.

             Usage is summed over the assistant turns, cached prompt tokens
             included in input. Pi's cost is an executor estimate, not
             provider-billed cost, so no cost is reported; administrator price
             rules may estimate from the captured tokens.
    """

    def run_gate(
        self,
        execute: ExecTarget,
        worktree: str | Path,
        io_dir: str | Path,
        prompt: str,
        *,
        timeout: float | None = None,
        archive_stem: str = "",
        cancel: Callable[[], bool] | None = None,
    ) -> GateRun:
        """
        @brief      Run one gate through Pi's RPC mode on a container target.
        @details    Clears stale questions and streams, writes a descriptive
                    gate.sh (no shell runs; the prompt never enters it), runs
                    `pi_rpc`, archives the bounded evidence and reads the
                    questions file. Targets without `spawn` use the file
                    protocol unchanged.
        @param[in]  execute Exec seam bound to the run's target.
        @param[in]  worktree HOST path of the run's worktree.
        @param[in]  io_dir HOST path of the run's io exchange dir.
        @param[in]  prompt Gate instruction, sent over stdin.
        @param[in]  timeout Stage wall-clock bound.
        @param[in]  archive_stem Optional immutable archive name stem.
        @param[in]  cancel Cancellation check polled during the run.
        @return     A GateRun: exit 0 completed, 1 failed, 124 timed out,
                    130 cancelled, otherwise a protocol failure.
        """
        spawn = getattr(execute, "spawn", None)
        if spawn is None:
            return super().run_gate(execute, worktree, io_dir, prompt,
                                    timeout=timeout, archive_stem=archive_stem)
        worktree = Path(worktree)
        io_dir = Path(io_dir)
        io_dir.mkdir(parents=True, exist_ok=True)
        questions_path = worktree / self.questions_file
        questions_path.unlink(missing_ok=True)
        output_path = io_dir / OUTPUT_FILE
        stderr_path = io_dir / STDERR_FILE
        output_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)
        argv = pi_rpc_argv(self.model)
        with (io_dir / GATE_SCRIPT).open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                SHELL_HEADER
                + "# Pi RPC launch through the container exec seam; no shell is executed.\n"
                + "# The stage prompt is sent over stdin.\n"
                + "# argv: " + json.dumps(argv, ensure_ascii=True) + "\n"
                + "# env: " + json.dumps(PI_RPC_ENV, ensure_ascii=True) + "\n"
            )
        result = pi_rpc.run_pi_rpc(
            lambda command, env: spawn(command, env=env),
            argv, dict(PI_RPC_ENV), prompt,
            timeout=timeout, cancelled=cancel,
            output_path=output_path, stderr_path=stderr_path,
            redact=getattr(execute, "redact", None),
        )
        evidence = pi_rpc.bounded_text("\n".join(
            part for part in (result.message, *result.notes, result.stderr) if part))
        artifacts: list[str] = []
        if archive_stem:
            launch = CommandResult(argv=argv, exit_code=result.exit_code,
                                   timed_out=result.timed_out)
            try:
                artifacts.append(str(self._archive_launch(
                    io_dir, archive_stem, launch, result.output, evidence, timeout,
                    output_path.is_file(), stderr_path.is_file(), output_file=output_path)))
            except OSError as exc:
                return GateRun(exit_code=result.exit_code or 1, output=result.output,
                               stderr=(evidence + f"\narchive write failed: {exc}").strip(),
                               timed_out=result.timed_out)
        usage = result.usage
        reported = usage.complete and usage.turns > 0
        return GateRun(
            exit_code=result.exit_code,
            has_questions=questions_path.is_file(),
            questions=self._read(questions_path),
            output=result.output,
            stderr=evidence,
            timed_out=result.timed_out,
            tokens_in=usage.tokens_in if reported else 0,
            tokens_out=usage.tokens_out if reported else 0,
            cache_read_tokens=usage.cache_read if reported else None,
            cache_write_tokens=usage.cache_write if reported else None,
            tokens_reported=reported,
            cost_usd=0.0,
            cost_reported=False,
            artifact_dirs=artifacts,
        )

    def cancel_grace_seconds(self, execute: ExecTarget) -> float | None:
        """
        @brief      A container Pi gate aborts itself on cancel.
        @param[in]  execute Exec seam the gate will run on.
        @return     The abort-and-exit grace on a container target, else None.
        """
        return PI_CANCEL_GRACE_SECONDS if hasattr(execute, "spawn") else None

    def _tokens_reported(self, output: str) -> bool:
        """@brief Recognize a complete final turn, including a zero-token turn."""
        for raw in output.splitlines():
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or event.get("type") != "turn_end":
                continue
            message = event.get("message")
            usage = message.get("usage") if isinstance(message, dict) else None
            if (isinstance(usage, dict)
                    and all(type(usage.get(key, 0 if key.startswith("cache") else None))
                            is int
                            and 0 <= usage.get(key, 0) <= 1_000_000_000
                            for key in ("input", "output", "cacheRead", "cacheWrite"))):
                return True
        return False

    def _extract_usage(self, output: str) -> tuple[int, int, float]:
        """@brief Sum final Pi turn usage, including cached prompt tokens.
        @param[in] output Pi JSONL event stream from one gate.
        @return Input/output tokens and zero billed cost.
        @note Streaming updates and message-end events duplicate turn-end usage.
        """
        tokens_in, tokens_out, cost, _read, _write = (
            self._extract_usage_detail(output))
        return tokens_in, tokens_out, cost

    def _extract_usage_detail(
        self, output: str,
    ) -> tuple[int, int, float, int | None, int | None]:
        """@brief Keep Pi cache counts separate; input already includes them."""
        tokens_in = tokens_out = cache_read = cache_write = 0
        observed = False
        for raw in output.splitlines():
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or event.get("type") != "turn_end":
                continue
            message = event.get("message")
            usage = message.get("usage") if isinstance(message, dict) else None
            if not isinstance(usage, dict):
                continue
            values = [usage.get(key, 0 if key.startswith("cache") else None)
                      for key in ("input", "output", "cacheRead", "cacheWrite")]
            if any(type(value) is not int or not 0 <= value <= 1_000_000_000
                   for value in values):
                continue
            prompt, completion, turn_cache_read, turn_cache_write = values
            tokens_in += prompt + turn_cache_read + turn_cache_write
            tokens_out += completion
            cache_read += turn_cache_read
            cache_write += turn_cache_write
            observed = True
        return (tokens_in, tokens_out, 0.0,
                cache_read if observed else None,
                cache_write if observed else None)


def pi_rpc_argv(model: str) -> list[str]:
    """
    @brief      Fixed command line of a container Pi RPC launch.
    @param[in]  model Model in provider/model form.
    @return     `node <cli.js> --mode rpc ... -e <guard> --model <model>`.
    """
    return ["node", CONTAINER_PI_CLI, *PI_RPC_FLAGS, "-e", CONTAINER_PI_GUARD,
            "--model", model]


def build_executor(
    command_template: str,
    model: str,
    questions_file: str = DEFAULT_QUESTIONS_FILE,
) -> Executor:
    """
    @brief      Construct the Pi launcher (config selection point).
    @details    Pi is the only implementation of the executor interface.
    @param[in]  command_template Native Pi argv template ([executor] command).
    @param[in]  model Model in provider/model form.
    @param[in]  questions_file Clarification questions filename.
    @return     A PiExecutor.
    """
    return PiExecutor(command_template, model, questions_file)


# END OF FILE
