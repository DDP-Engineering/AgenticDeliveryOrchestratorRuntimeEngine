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
@brief Configurable executor launchers (opencode / pi / codex / qwen) and factory.
@details Runs the configured executor headless inside the run's container, one
         gate per launch, over a shared file-based gate protocol
         (FileProtocolExecutor): the gate command (with the shell-quoted prompt
         embedded) is written to a script in the run's io dir and executed as
         `sh /adore/io/gate.sh` - so no prompt content ever travels through argv
         (wsl.exe splits argv elements containing spaces) and the event stream
         is captured to a file, never streamed from stdout. Executors differ
         only in how they continue sessions and parse their own JSON event
         stream (session id, token usage); everything else - the WSL-safe
         protocol, clarification-questions detection, and session self-heal -
         is shared. Supported executors read the repo's AGENTS.md gate
         contract natively and get their push/merge guardrails from the repo's
         adapter plus container isolation (no remote credentials in the
         container).
"""

from __future__ import annotations

# IMPORTS
import json
from pathlib import Path
import re
import shlex
import shutil

from adore.branding import DEFAULT_QUESTIONS_FILE
from adore.executor.base import ExecTarget, Executor, GateRun
from adore.isolation import CONTAINER_IO_MOUNT, CONTAINER_WORKTREE_MOUNT
from adore.util import utc_now_iso

# CONSTANTS

GATE_SCRIPT = "gate.sh"
OUTPUT_FILE = "output.jsonl"
STDERR_FILE = "stderr.log"
ARCHIVE_DIR = "archive"

# opencode tags each event with "sessionID" / "session_id".
_OPENCODE_SESSION_RE = re.compile(r'"session_?[iI][dD]"\s*:\s*"([^"]+)"')
_ARCHIVE_STEM_RE = re.compile(r"[^A-Za-z0-9_.-]+")

# PUBLIC API


class FileProtocolExecutor(Executor):
    """
    @brief   Shared file-based gate protocol for headless CLI executors.
    @details One gate per launch: clear a stale questions file, write gate.sh
             (the command with the shell-quoted prompt) into the io dir, exec
             it in the container, and read every result back from files
             (output stream, stderr, questions) - never from live stdout.
             When an archive stem is provided, each actual launch copies its
             gate.sh/output/stderr/meta into an immutable archive directory
             before any dead-session self-heal can relaunch and overwrite the
             live exchange files.
             Continuation appends `--session <id>` (the convention shared by
             opencode and pi). Subclasses supply only the JSON parsers:
             `_extract_session_id` (required) and `_extract_usage` (optional,
             defaults to no usage). `forbidden_flags` and
             `session_reset_markers` are per-executor class attributes.
    """

    #: Command-template tokens rejected at construction (a bypass of the
    #: executor's own push/merge guardrails). Per-executor.
    forbidden_flags: tuple[str, ...] = ()
    #: stderr substrings that mean the stored session died with its container
    #: (or was pruned) - relaunch once with a fresh session.
    session_reset_markers: tuple[str, ...] = ("session not found",)

    def __init__(
        self,
        command_template: str,
        model: str,
        questions_file: str = DEFAULT_QUESTIONS_FILE,
    ) -> None:
        """
        @brief      Configure the launcher from the [executor.<name>] entry.
        @param[in]  command_template Command template with {prompt}, {model},
                                     {worktree} placeholders ({worktree} is the
                                     container mount /adore/work; unused tokens
                                     are ignored).
        @param[in]  model Model in provider/model form.
        @param[in]  questions_file Worktree filename the executor writes
                                   blocking questions to.
        @exception  ValueError When the template carries a forbidden flag.
        """
        # Tokenize with shlex so quoting is respected, and reject both the bare
        # flag and its `--flag=value` form. This stays a safety belt, not the
        # boundary: container isolation (no remote credentials) is what actually
        # keeps a misconfigured executor off the remote.
        try:
            tokens = shlex.split(command_template)
        except ValueError:
            tokens = command_template.split()
        for flag in self.forbidden_flags:
            if any(token == flag or token.startswith(f"{flag}=") for token in tokens):
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
        archive_stem: str = "",
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
                    `io/archive/<stem>-attemptN/` after each actual launch. A
                    dead session
                    (session_reset_markers in stderr) self-heals by relaunching
                    once with a fresh session.
        @param[in]  execute Exec seam bound to the run's container.
        @param[in]  worktree HOST path of the run's worktree.
        @param[in]  io_dir HOST path of the run's io exchange dir.
        @param[in]  prompt Gate instruction (never enters argv).
        @param[in]  session Executor session id to continue ("" = new).
        @param[in]  timeout Wall-clock bound (run budgets).
        @param[in]  archive_stem Optional immutable archive name stem.
        @return     A GateRun describing the outcome.
        """
        return self._run_gate_attempt(
            execute,
            worktree,
            io_dir,
            prompt,
            session=session,
            timeout=timeout,
            archive_stem=archive_stem,
            attempt=1,
            artifact_dirs=[],
        )

    def _run_gate_attempt(
        self,
        execute: ExecTarget,
        worktree: str | Path,
        io_dir: str | Path,
        prompt: str,
        *,
        session: str,
        timeout: float | None,
        archive_stem: str,
        attempt: int,
        artifact_dirs: list[str],
    ) -> GateRun:
        """
        @brief      Run one physical executor launch, archiving before retry.
        @details    Split from run_gate so a dead-session self-heal can carry
                    forward the first attempt's archive path before relaunching
                    with a fresh session.
        @param[in]  execute Exec seam bound to the run's container.
        @param[in]  worktree HOST path of the run's worktree.
        @param[in]  io_dir HOST path of the run's io exchange dir.
        @param[in]  prompt Gate instruction.
        @param[in]  session Executor session id for this attempt.
        @param[in]  timeout Wall-clock bound.
        @param[in]  archive_stem Optional immutable archive name stem.
        @param[in]  attempt Attempt number for this stem.
        @param[in]  artifact_dirs Archive dirs already produced.
        @return     A GateRun describing the final outcome.
        """
        worktree = Path(worktree)
        io_dir = Path(io_dir)
        io_dir.mkdir(parents=True, exist_ok=True)

        questions_path = worktree / self.questions_file
        questions_path.unlink(missing_ok=True)

        command = self._build_command(
            prompt=shlex.quote(prompt),
            model=shlex.quote(self.model),
            worktree=CONTAINER_WORKTREE_MOUNT,
            session=session,
        )
        # No `exec` prefix: the template may be a compound command, and the
        # script's exit status is the command's status either way. The command
        # is wrapped in a `{ ...; }` group so the output/stderr redirection
        # applies to the WHOLE compound (e.g. `a && b`), not just its last
        # stage - otherwise a compound template would lose the earlier stage's
        # stream. Group exit status is that of the last command run, unchanged.
        script = (
            "#!/bin/sh\n"
            f"cd {CONTAINER_WORKTREE_MOUNT}\n"
            f"{{ {command}; }} "
            f"> {CONTAINER_IO_MOUNT}/{OUTPUT_FILE} "
            f"2> {CONTAINER_IO_MOUNT}/{STDERR_FILE}\n"
        )
        with (io_dir / GATE_SCRIPT).open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)

        result = execute(["sh", f"{CONTAINER_IO_MOUNT}/{GATE_SCRIPT}"], timeout=timeout)

        output_path = io_dir / OUTPUT_FILE
        stderr_path = io_dir / STDERR_FILE
        output = self._read(output_path)
        stderr = self._read(stderr_path) or result.stderr
        artifacts = list(artifact_dirs)
        if archive_stem:
            try:
                archive_dir = self._archive_launch(
                    io_dir,
                    archive_stem,
                    attempt,
                    result,
                    output,
                    stderr,
                    timeout,
                    session,
                    output_path.is_file(),
                    stderr_path.is_file(),
                )
            except OSError as exc:
                archive_error = f"archive write failed: {exc}"
                return GateRun(
                    exit_code=result.exit_code or 1,
                    session_id=self._extract_session_id(output) or session,
                    output=output,
                    stderr=(stderr + "\n" + archive_error).strip(),
                    timed_out=result.timed_out,
                    artifact_dirs=artifacts,
                )
            artifacts.append(str(archive_dir))
        if (
            not result.ok
            and not result.timed_out
            and session
            and self._is_session_reset(stderr)
        ):
            # the stored session died with its container (or was pruned);
            # self-heal by relaunching once with a fresh session
            return self._run_gate_attempt(
                execute,
                worktree,
                io_dir,
                prompt,
                session="",
                timeout=timeout,
                archive_stem=archive_stem,
                attempt=attempt + 1,
                artifact_dirs=artifacts,
            )
        questions = self._read(questions_path)
        tokens_in, tokens_out, cost = self._extract_usage(output)
        return GateRun(
            exit_code=result.exit_code,
            has_questions=questions_path.is_file(),
            questions=questions,
            session_id=self._extract_session_id(output) or session,
            output=output,
            stderr=stderr,
            timed_out=result.timed_out,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            artifact_dirs=artifacts,
        )

    # -- executor-specific command build + parsing (subclasses) -------------------

    def _build_command(self, *, prompt: str, model: str, worktree: str, session: str) -> str:
        """
        @brief      Compose the executor command (shared default: append
                    `--session <id>` to continue).
        @details    Overridable so an executor whose continuation changes the
                    command STRUCTURE (e.g. Codex's `exec` -> `exec resume`)
                    can express it, rather than only appending a flag. `prompt`
                    and `model` arrive already shell-quoted; `session` is raw.
        @param[in]  prompt Shell-quoted prompt text.
        @param[in]  model Shell-quoted model string.
        @param[in]  worktree Container worktree mount (/adore/work).
        @param[in]  session Session id to continue ("" = new).
        @return     The full command string embedded into gate.sh.
        """
        command = self.command_template.format(
            prompt=prompt, model=model, worktree=worktree
        )
        if session:
            command += f" --session {shlex.quote(session)}"
        return command

    def _extract_session_id(self, output: str) -> str:
        """
        @brief      Pull the executor's session id from its event stream.
        @param[in]  output Raw event-stream text.
        @return     The session id, or "".
        """
        raise NotImplementedError  # pragma: no cover - abstract hook

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

    # -- internals ----------------------------------------------------------------

    def _archive_launch(
        self,
        io_dir: Path,
        archive_stem: str,
        attempt: int,
        result,
        output: str,
        stderr: str,
        timeout: float | None,
        session: str,
        output_present: bool,
        stderr_present: bool,
    ) -> Path:
        """
        @brief      Copy one completed launch's live exchange files to archive.
        @details    Creates a unique directory under `io/archive`. Empty
                    output/stderr files are still written so absence is visible
                    in meta.json without making operators guess whether a file
                    was skipped.
        @param[in]  io_dir Host io exchange directory.
        @param[in]  archive_stem Base name supplied by the orchestrator.
        @param[in]  attempt Physical launch number for this stem.
        @param[in]  result Container exec result.
        @param[in]  output Captured output stream or "".
        @param[in]  stderr Captured stderr stream or fallback stderr.
        @param[in]  timeout Launch timeout.
        @param[in]  session Session id used for this launch.
        @param[in]  output_present Whether live output.jsonl existed.
        @param[in]  stderr_present Whether live stderr.log existed.
        @return     Archive directory path.
        @exception  OSError When any archive write fails.
        """
        archive_root = io_dir / ARCHIVE_DIR
        archive_root.mkdir(parents=True, exist_ok=True)
        base_name = f"{self._safe_archive_stem(archive_stem)}-attempt{attempt}"
        archive_dir = archive_root / base_name
        suffix = 2
        while archive_dir.exists():
            archive_dir = archive_root / f"{base_name}-{suffix}"
            suffix += 1
        archive_dir.mkdir()
        shutil.copy2(io_dir / GATE_SCRIPT, archive_dir / GATE_SCRIPT)
        (archive_dir / OUTPUT_FILE).write_text(output, encoding="utf-8")
        (archive_dir / STDERR_FILE).write_text(stderr, encoding="utf-8")
        meta = {
            "created_at": utc_now_iso(),
            "archive_stem": archive_stem,
            "attempt": attempt,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "argv": result.argv,
            "timeout": timeout,
            "session": session,
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

    def _is_session_reset(self, stderr: str) -> bool:
        """
        @brief      Whether stderr signals a dead/pruned session (self-heal).
        @param[in]  stderr Captured stderr.
        @return     True when any reset marker is present.
        """
        lowered = stderr.lower()
        return any(marker in lowered for marker in self.session_reset_markers)

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


class OpencodeExecutor(FileProtocolExecutor):
    """
    @brief   opencode implementation of the executor launcher.
    @details Template is the [executor.opencode] command; session continuation
             appends `--session <id>` so gate-by-gate driving and clarification
             resume reuse the same opencode session. Rejects `--auto` (it would
             auto-approve the push/pr/merge permissions). Usage comes from
             opencode's step_finish events.
    """

    forbidden_flags = ("--auto",)

    def _extract_session_id(self, output: str) -> str:
        """
        @brief      The opencode session id ("sessionID"/"session_id" anywhere).
        @param[in]  output Raw --format json event stream.
        @return     The first session id found, or "".
        """
        match = _OPENCODE_SESSION_RE.search(output)
        return match.group(1) if match else ""

    def _extract_usage(self, output: str) -> tuple[int, int, float]:
        """
        @brief      Sum opencode step_finish token/cost totals for the launch.
        @details    step_finish events carry part.tokens{input,output} and
                    part.cost (schema pinned live 2026-07-03). Tolerant of
                    malformed lines - usage capture must never break a gate.
        @param[in]  output Raw --format json event stream.
        @return     (tokens_in, tokens_out, cost_usd) totals.
        """
        tokens_in = tokens_out = 0
        cost = 0.0
        for raw in output.splitlines():
            line = raw.strip()
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


class PiExecutor(FileProtocolExecutor):
    """
    @brief   Pi (@earendil-works/pi-coding-agent) executor launcher.
    @details Runs headless via the [executor.pi] template, e.g.
             `pi -p --mode json --model {model} {prompt}`; session continuation
             appends `--session <id>` (same convention as opencode). Pi reads
             the repo's AGENTS.md gate contract natively and enforces the
             push/merge guardrails through the repo's .pi agentic-guard
             extension (a return-value block, active in every mode including
             print/json) - plus container isolation (no remote credentials in
             the container). Pi's JSON stream opens with a
             {"type":"session","id":...} header; token usage is not reported in
             the stream today, so usage falls back to zeros (metrics tolerate
             it) until a spike pins a usage field.
    """

    # Pi loads its project-local guard/skills only after the project is
    # trusted; ADORE must pre-trust the worktree for headless runs (container
    # isolation still prevents remote writes regardless). See the executor
    # component doc / TODO for the trust-provisioning spike.
    session_reset_markers = ("session not found", "no such session")

    def _extract_session_id(self, output: str) -> str:
        """
        @brief      The Pi session id from the JSON stream's session header.
        @details    Pi's `--mode json` stream begins with
                    {"type":"session","version":N,"id":"<uuid>",...}; the id is
                    read from that event (order-independent parse), falling
                    back to a generic scan.
        @param[in]  output Raw json-lines event stream.
        @return     The session id, or "".
        """
        for raw in output.splitlines():
            line = raw.strip()
            if '"session"' not in line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict) and event.get("type") == "session" and event.get("id"):
                return str(event["id"])
        match = _OPENCODE_SESSION_RE.search(output)  # tolerate a sessionID field too
        return match.group(1) if match else ""


class CodexExecutor(FileProtocolExecutor):
    """
    @brief   OpenAI Codex (`@openai/codex`, the Rust CLI) executor launcher.
    @details Runs headless via `codex exec` from the [executor.codex] template,
             e.g. `codex exec {resume}--json --model {model}
             --ignore-user-config --disable plugins
             --dangerously-bypass-approvals-and-sandbox {prompt}`. Codex reads
             AGENTS.md natively and gets its guardrails from ADORE container
             isolation (no remote credentials in the container).

             Two Codex specifics vs opencode/pi:
             1. **Continuation is a subcommand, not a flag.** The first gate is
                `codex exec ...`; a later gate resumes the previous gate's
                session in the same container/cwd with `codex exec resume
                --last ...`. `_build_command` substitutes the `{resume}`
                placeholder accordingly - no session id is tracked (one session
                per run container); `_extract_session_id` is best-effort/audit.
             2. **Approval model is inverted.** The command MUST run
                non-interactively (`--sandbox workspace-write`,
                `--full-auto`, or
                `--dangerously-bypass-approvals-and-sandbox`, enforced by
                config validation). In ADORE, the container/worktree boundary
                is the external sandbox for full-auto Codex runs.
             3. **User config/plugins are ignored.** The orchestrator stages
                only auth.json into an isolated CODEX_HOME and the command
                disables the Codex `plugins` feature so workstation-local or
                bundled plugin marketplace state cannot alter a portable run.

             Usage is parsed best-effort from `codex exec --json`; the exact
             field schema is pinned by the live spike (until then, absent usage
             reads as zeros, which metrics tolerate).
    """

    forbidden_flags: tuple[str, ...] = ()

    def _build_command(self, *, prompt: str, model: str, worktree: str, session: str) -> str:
        """
        @brief      Codex command: `exec` (new) or `exec resume --last` (cont.).
        @details    Substitutes the template's `{resume}` placeholder. A
                    template without `{resume}` degrades gracefully to
                    stateless (each gate a fresh session) since str.format
                    ignores the unused key.
        @param[in]  prompt Shell-quoted prompt.
        @param[in]  model Shell-quoted model.
        @param[in]  worktree Container worktree mount.
        @param[in]  session Non-empty -> resume the previous gate's session.
        @return     The full command string.
        """
        resume = "resume --last " if session else ""
        return self.command_template.format(
            prompt=prompt, model=model, worktree=worktree, resume=resume
        )

    def _extract_session_id(self, output: str) -> str:
        """
        @brief      Best-effort Codex session/thread id from `--json` (audit
                    only; Codex continues via `resume --last`, not an id).
        @param[in]  output Raw json-lines event stream.
        @return     The id, or "".
        """
        for raw in output.splitlines():
            line = raw.strip()
            if '"session' not in line and '"thread' not in line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                sid = event.get("session_id") or event.get("thread_id")
                if sid:
                    return str(sid)
        return ""

    def _extract_usage(self, output: str) -> tuple[int, int, float]:
        """
        @brief      Best-effort token usage from Codex `--json` events.
        @details    Sums any event carrying a `usage`/token object with
                    input_tokens/output_tokens (+ optional cost_usd). The exact
                    schema is PROVISIONAL - pinned by the live spike; malformed
                    lines are ignored so usage capture never breaks a gate.
        @param[in]  output Raw json-lines event stream.
        @return     (tokens_in, tokens_out, cost_usd).
        """
        tokens_in = tokens_out = 0
        cost = 0.0
        for raw in output.splitlines():
            line = raw.strip()
            if '"input_tokens"' not in line and '"usage"' not in line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            usage = event.get("usage") if isinstance(event.get("usage"), dict) else event
            tokens_in += int(usage.get("input_tokens", 0) or 0)
            tokens_out += int(usage.get("output_tokens", 0) or 0)
            cost += float(usage.get("cost_usd", 0) or 0)
        return tokens_in, tokens_out, cost


class QwenExecutor(FileProtocolExecutor):
    """
    @brief   Qwen Code (`@qwen-code/qwen-code`, a Gemini-CLI fork) launcher.
    @details Runs headless via `qwen -p` from the [executor.qwen] template, e.g.
             `qwen -p --model {model} --output-format json {prompt}`. Qwen reads
             AGENTS.md natively and gets its guardrails from the repo's `.qwen`
             settings (native PreToolUse/PostToolUse hooks reusing the shared
             `.agentic` guards + a push/pr/merge deny list) plus ADORE container
             isolation.

             Unlike opencode/pi/codex, Qwen has **no session continuation** -
             each gate is a fresh `qwen -p` run. This is viable because the
             workflow's state lives in files (`.agentic/`, git, the ticket
             thread ADORE re-sends on resume), so `_build_command` ignores the
             `session` argument (stateless) and `_extract_session_id` returns
             "". Whether stateless-per-gate holds in practice is the key spike
             assumption.

             Safety: `forbidden_flags` rejects `--yolo` (auto-approve all
             tools); config validation additionally bans `--approval-mode yolo`.
             Usage is not parsed yet (Qwen's `--output-format json` `stats`
             block is nested/model-keyed; pinned by the live spike), so it reads
             as zeros (metrics tolerate it), like Pi.
    """

    forbidden_flags = ("--yolo",)

    def _build_command(self, *, prompt: str, model: str, worktree: str, session: str) -> str:
        """
        @brief      Stateless command build: no session/resume (Qwen has none).
        @param[in]  prompt Shell-quoted prompt.
        @param[in]  model Shell-quoted model.
        @param[in]  worktree Container worktree mount.
        @param[in]  session Ignored (Qwen does not continue sessions).
        @return     The formatted command.
        """
        return self.command_template.format(prompt=prompt, model=model, worktree=worktree)

    def _extract_session_id(self, output: str) -> str:
        """
        @brief      No session id (Qwen runs stateless).
        @param[in]  output Ignored.
        @return     "".
        """
        return ""


def build_executor(
    kind: str,
    command_template: str,
    model: str,
    questions_file: str = DEFAULT_QUESTIONS_FILE,
) -> Executor:
    """
    @brief      Construct the configured executor (config selection point).
    @param[in]  kind Executor kind ("opencode" | "pi" | "codex" | "qwen").
    @param[in]  command_template Command template for the executor.
    @param[in]  model Model in provider/model form.
    @param[in]  questions_file Clarification questions filename.
    @return     An Executor instance.
    @exception  ValueError When the kind is unknown or the template carries a
                forbidden flag.
    """
    if kind == "opencode":
        return OpencodeExecutor(command_template, model, questions_file)
    if kind == "pi":
        return PiExecutor(command_template, model, questions_file)
    if kind == "codex":
        return CodexExecutor(command_template, model, questions_file)
    if kind == "qwen":
        return QwenExecutor(command_template, model, questions_file)
    raise ValueError(
        f"unsupported executor kind: {kind!r} (use opencode | pi | codex | qwen)"
    )


# END OF FILE
