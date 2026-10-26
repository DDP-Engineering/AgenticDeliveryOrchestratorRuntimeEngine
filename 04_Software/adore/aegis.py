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
@file aegis.py
@brief Typed client for the agent-driven AEGIS companion CLI.
@details ADORE invokes ``python .agentic/aegis.py`` inside the isolated
         worktree. AEGIS owns task journals and workflow instructions; ADORE
         creates tasks, reads schema-1 status/check documents, runs objective
         verification, and fails loudly when the CLI or persisted journal
         crosses the documented trust boundary incorrectly. It speaks the
         documented CLI and schema, with no alternate-contract fallback.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import json
from pathlib import Path, PurePosixPath
import re
import shlex
from typing import Any

from adore.executor.base import ExecTarget
from adore.util import CommandResult

# CONSTANTS

AEGIS_CLI = ".agentic/aegis.py"
#: The AEGIS major line ADORE speaks. A major bump is the signal that the
#: companion contract itself changed, so it is refused rather than guessed at.
SUPPORTED_MAJOR = 0
#: Oldest AEGIS release whose flow ADORE conducts. 0.15.0 removed the deliver
#: stage: validate closes the task with its final strict check, `report` and
#: `advance` to done, and commit, push and review creation belong to ADORE.
#: An older payload ends in a deliver stage that asks the agent to wait for a
#: human and to commit, so it is refused at probe instead of half-conducted.
MINIMUM_SERIES = (0, 15)
#: The real compatibility contract. Version is metadata; this is the promise.
JSON_SCHEMA = 1
DEFAULT_TIMEOUT = 300
VERIFY_TIMEOUT = 5400
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_TEXT_BYTES = 64 * 1024
MAX_LIST_ITEMS = 10_000

AEGIS_SCRIPT = "aegis.sh"
AEGIS_STDOUT_FILE = "aegis.stdout"
AEGIS_STDERR_FILE = "aegis.stderr"

TASK_ID_RE = re.compile(r"^TASK-[0-9a-f]{8}$")
VERSION_RE = re.compile(r"^aegis\s+(\d+)\.(\d+)\.(\d+)$")

RUN_KINDS = ("feature", "fix", "change")
QUICK_KINDS = ("fix", "change")
#: The stages ADORE conducts, in AEGIS 0.15.0 path order. Validate closes the
#: task by advancing to done; no stage follows it.
FULL_STAGES = ("frame", "specify", "design", "build", "validate", "done")
QUICK_STAGES = ("frame", "build", "validate", "done")
ALL_STAGES = FULL_STAGES
ADOPTION_STAGES = ("survey", "components", "close")
#: Every stage AEGIS 0.15.0 reports for a journal: the conducted stages, the
#: legacy deliver stage older journals still hold, and adoption's phases.
#: Listings and deviation markers accept it all, so a journal another task
#: left behind never blocks a probe; the pinned task decodes against
#: ALL_STAGES only.
STATUS_STAGES = (*ALL_STAGES, "deliver", *ADOPTION_STAGES)
STAGE_STEP_FILES = {
    "frame": "1_frame.md",
    "specify": "2_specify.md",
    "design": "3_design.md",
    "build": "4_build.md",
    "validate": "5_validate.md",
    "done": None,
}
#: A Log entry opens with the stage it reports on, after an optional list
#: bullet and date. Anchored so prose that merely mentions a stage name is
#: never read as evidence that the stage ran.
_STAGE_LOG_RE = re.compile(
    rf"^\s*(?:[-*]\s+)?(?:\d{{4}}-\d{{2}}-\d{{2}}\s+)?({'|'.join(FULL_STAGES)})\s*:"
)
#: A recorded deviation in the one shape AEGIS itself harvests for its
#: delivery report: the standalone token, a stage it knows, then `:` or
#: ` - `. Prose that merely mentions the word is not a deviation.
DEVIATION_RE = re.compile(
    r"(?<![\w-])DEVIATION[ \t]+"
    rf"(?=(?:{'|'.join(STATUS_STAGES)})\b[ \t]*(?::|[ \t][-\u2013\u2014][ \t]))"
)

# DATA MODELS / TYPEDEFINITIONS


class AegisError(RuntimeError):
    """@brief Base class for unusable AEGIS interactions."""


class AegisProtocolError(AegisError):
    """@brief AEGIS returned an unsupported or malformed CLI response."""


class AegisTimeoutError(AegisError):
    """@brief One AEGIS command exceeded ADORE's invocation bound."""


class AegisTaskError(AegisError):
    """@brief A task journal/status document violated the public contract."""


@dataclass(frozen=True)
class AegisProbe:
    """@brief Validated installed AEGIS release and machine schema."""

    version: str
    major: int
    minor: int
    patch: int
    schema: int


@dataclass(frozen=True)
class ChecklistItem:
    """@brief One current-stage task-journal checklist item."""

    done: bool
    item: str


@dataclass(frozen=True)
class AegisTask:
    """@brief Validated schema-1 view of one AEGIS task journal."""

    task_id: str
    title: str
    file: str
    header: Mapping[str, str]
    stage: str
    step_file: str | None
    done: bool
    checklist: tuple[ChecklistItem, ...]
    log: tuple[str, ...]

    @property
    def task_type(self) -> str:
        """@brief Return the journal's feature/fix/change type."""
        return self.header["type"]

    @property
    def path(self) -> str:
        """@brief Return the journal's full/quick workflow path."""
        return self.header["path"]

    @property
    def branch(self) -> str:
        """@brief Return the branch recorded in the journal."""
        return self.header["branch"]

    @property
    def requirements(self) -> tuple[str, ...]:
        """@brief Return comma-separated requirement ids as normalized values."""
        return tuple(
            item.strip()
            for item in self.header.get("requirements", "").split(",")
            if item.strip()
        )

    @property
    def deviations(self) -> tuple[str, ...]:
        """@brief Recorded `DEVIATION <stage>` log entries, token stripped, in order."""
        found = []
        for entry in self.log:
            match = DEVIATION_RE.search(entry)
            if match:
                found.append(" ".join(entry[match.end():].split()))
        return tuple(found)


@dataclass(frozen=True)
class AegisFinding:
    """@brief One structured AEGIS check finding."""

    level: str
    check: str
    path: str
    message: str


@dataclass(frozen=True)
class AegisCommandRun:
    """@brief One configured command considered by ``check --run``."""

    name: str
    status: str
    exit_code: int | None
    seconds: float | None
    reason: str = ""


@dataclass(frozen=True)
class AegisCheck:
    """@brief Validated complete schema-1 check result."""

    exit_code: int
    task_id: str | None
    findings: tuple[AegisFinding, ...]
    errors: int
    warnings: int
    notes: int
    strict_enabled: bool
    promoted_warnings: int
    passed: bool
    runs: tuple[AegisCommandRun, ...]
    raw: Mapping[str, Any]

    @property
    def executed_runs(self) -> tuple[AegisCommandRun, ...]:
        """@brief Configured commands that actually executed."""
        return tuple(item for item in self.runs if item.status != "skipped")


# HELPER FUNCTIONS


def _bounded_text(value: Any, field: str, *, empty: bool = False) -> str:
    """@brief Read one bounded string from a trust-boundary document."""
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise AegisProtocolError(f"AEGIS field {field!r} must be a string")
    if len(value.encode("utf-8")) > MAX_TEXT_BYTES:
        raise AegisProtocolError(f"AEGIS field {field!r} exceeds its size bound")
    return value


def _repository_path(value: Any, field: str) -> str:
    """@brief Validate one normalized repository-relative POSIX path."""
    text = _bounded_text(value, field)
    if "\\" in text or ":" in text:
        raise AegisProtocolError(f"AEGIS path {field!r} is not repository-relative")
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or text in {".", ".."}
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != text
    ):
        raise AegisProtocolError(f"AEGIS path {field!r} escapes or is not normalized")
    return text


def allowed_transition(previous: str, current: str, path: str) -> bool:
    """
    @brief Decide whether an executor-authored stage transition is documented.
    @details A stage may remain current while work continues, advance exactly
             once on the selected path, or route backward from validation to
             specify/design/build. Validate closes the task by advancing to
             done, and done returns to validation when ADORE must revalidate
             the candidate. All other skips and regressions fail closed.
    """
    sequence = QUICK_STAGES if path == "quick" else FULL_STAGES
    if previous not in sequence or current not in sequence:
        return False
    if current == previous:
        return True
    if sequence.index(current) == sequence.index(previous) + 1:
        return True
    if previous == "validate" and current in {"specify", "design", "build"}:
        return path == "full" or current == "build"
    return previous == "done" and current == "validate"


def logged_stages(log: Sequence[str]) -> frozenset[str]:
    """
    @brief      Stages that carry a Log entry of their own in a task journal.
    @details    AEGIS writes one Log line per stage it completes, opened by the
                stage name after an optional date. Matching is anchored to the
                start of an entry so prose merely mentioning a stage cannot be
                mistaken for evidence that the stage ran.
    @param[in]  log The task journal's Log entries.
    @return     The stage names with an entry of their own.
    """
    found = {
        match.group(1)
        for entry in log
        if (match := _STAGE_LOG_RE.match(entry)) is not None
    }
    return frozenset(found)


def evidenced_transition(
    previous: str, current: str, path: str, log: Sequence[str]
) -> bool:
    """
    @brief      Whether a multi-stage forward jump is backed by the journal.
    @details    An executor is instructed to stop after one stage, but a model
                may run the whole task in a single session instead. That is a
                contract DEVIATION, not a skipped stage, and the two must not
                share a verdict: refusing both discards completed, correct work
                and leaves a run that `adore retry` cannot clear, because it
                replays the same refusal (live finding 2026-09-18, GitHub
                pilot - the same model stopped per stage six times running on
                another forge, so the behaviour is nondeterministic).

                The durable journal answers which stages actually ran. Only a
                FORWARD jump on the selected path is considered, and only when
                every stage from `previous` up to `current` carries its own Log
                entry. A genuine skip leaves gaps and stays refused, so the
                trust boundary is unchanged.
    @param[in]  previous The stage ADORE last recorded.
    @param[in]  current The stage the journal now reports.
    @param[in]  path The selected full/quick workflow path.
    @param[in]  log The task journal's Log entries.
    @return     True when the jump is evidenced and may be accepted.
    """
    sequence = QUICK_STAGES if path == "quick" else FULL_STAGES
    if previous not in sequence or current not in sequence:
        return False
    start, end = sequence.index(previous), sequence.index(current)
    if end <= start + 1:
        return False  # not a jump; allowed_transition already ruled on it
    done = logged_stages(log)
    return all(stage in done for stage in sequence[start:end])


# PUBLIC API


class AegisClient:
    """@brief Typed AEGIS client using direct or file-transport execution."""

    def __init__(
        self,
        execute: ExecTarget,
        python_command: str = "python",
        io_dir: str | Path | None = None,
    ) -> None:
        """
        @brief      Bind the client to a direct or container execution seam.
        @param[in]  execute Command executor, normally a bound container exec.
        @param[in]  python_command Python command in the target environment.
        @param[in]  io_dir Host side of the run's `/adore/io` mount. When set,
                           AEGIS commands and results cross the runtime boundary
                           through bounded files so raw arguments never enter
                           the WSL-wrapped container argv.
        """
        self.execute = execute
        self.python_command = python_command
        self.io_dir = Path(io_dir) if io_dir is not None else None

    def probe(self) -> AegisProbe:
        """@brief Prove the payload is a supported AEGIS major with schema 1."""
        result = self._run(["--version"], timeout=DEFAULT_TIMEOUT)
        match = VERSION_RE.fullmatch(result.stdout.strip())
        if match is None:
            raise AegisProtocolError(
                f"AEGIS --version returned an unsupported value: {result.stdout.strip()!r}"
            )
        major, minor, patch = (int(item) for item in match.groups())
        minimum = ".".join(str(part) for part in (*MINIMUM_SERIES, 0))
        if major != SUPPORTED_MAJOR:
            raise AegisProtocolError(
                f"AEGIS {major}.{minor}.{patch} is unsupported; ADORE speaks the "
                f"AEGIS {SUPPORTED_MAJOR}.x line from {minimum}"
            )
        if (major, minor) < MINIMUM_SERIES:
            raise AegisProtocolError(
                f"AEGIS {major}.{minor}.{patch} is unsupported; ADORE requires at "
                f"least {minimum}, where validate closes the task; upgrade the "
                "repository's .agentic payload"
            )
        payload, _ = self._json(["status", "--all", "--json"])
        self._status_list(payload)
        return AegisProbe(
            version=f"{major}.{minor}.{patch}", major=major, minor=minor,
            patch=patch, schema=JSON_SCHEMA,
        )

    def create_task(self, title: str, task_type: str) -> str:
        """@brief Create a task journal and return its validated task id."""
        if task_type not in RUN_KINDS:
            raise AegisProtocolError(f"unsupported AEGIS task type {task_type!r}")
        clean = title.strip()
        if not clean or clean != title or len(clean.encode("utf-8")) > 2048:
            raise AegisProtocolError("AEGIS task title must be a bounded trimmed string")
        result = self._run(["task", title, "--type", task_type])
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if len(lines) != 1:
            raise AegisProtocolError("AEGIS task creation must print exactly one path")
        path = _repository_path(lines[0], "task path")
        task_id = PurePosixPath(path).stem
        expected = f".agentic/tasks/{task_id}.md"
        if not TASK_ID_RE.fullmatch(task_id) or path != expected:
            raise AegisProtocolError(f"AEGIS returned an invalid task path {path!r}")
        return task_id

    def list_tasks(self, *, include_done: bool = True) -> tuple[AegisTask, ...]:
        """@brief List task summaries and fail on any unreadable journal."""
        argv = ["status"]
        if include_done:
            argv.append("--all")
        argv.append("--json")
        payload, _ = self._json(argv)
        summaries = self._status_list(payload)
        return tuple(self.task_status(item["id"]) for item in summaries)

    def task_status(self, task_id: str) -> AegisTask:
        """@brief Return a fully validated view of one task journal."""
        self._task_id(task_id)
        payload, _ = self._json(["status", task_id, "--json"])
        if payload.get("command") != "status" or not isinstance(payload.get("task"), dict):
            raise AegisTaskError("AEGIS task status has an invalid command/task shape")
        return self._decode_task(payload["task"], expected=task_id)

    def check(
        self,
        task_id: str | None = None,
        *,
        strict: bool = False,
        run: bool = False,
        timeout: float | None = None,
    ) -> AegisCheck:
        """@brief Run the advisory or strict AEGIS check catalog."""
        argv = ["check"]
        if task_id is not None:
            self._task_id(task_id)
            argv += ["--task", task_id]
        if strict:
            argv.append("--strict")
        if run:
            argv.append("--run")
        argv.append("--json")
        payload, result = self._json(
            argv,
            timeout=(
                timeout
                if timeout is not None
                else VERIFY_TIMEOUT if run else DEFAULT_TIMEOUT
            ),
            allowed=(0, 1) if strict else (0,),
        )
        return self._decode_check(payload, result.exit_code, task_id, strict)

    # LOCAL HELPERS

    def _command(self, argv: Sequence[str]) -> list[str]:
        return [self.python_command, AEGIS_CLI, *argv]

    def _run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = DEFAULT_TIMEOUT,
        allowed: tuple[int, ...] = (0,),
    ) -> CommandResult:
        command = self._command(argv)
        result = (
            self.execute(command, timeout=timeout)
            if self.io_dir is None
            else self._run_from_files(command, timeout=timeout)
        )
        if "\ufffd" in result.stdout or "\ufffd" in result.stderr:
            raise AegisProtocolError(
                f"AEGIS command `{' '.join(command)}` returned invalid UTF-8"
            )
        if result.timed_out:
            raise AegisTimeoutError(
                f"AEGIS command `{' '.join(command)}` timed out after {timeout}s"
            )
        if result.exit_code not in allowed:
            detail = (result.stderr or result.stdout).strip()[-1200:]
            raise AegisProtocolError(
                f"AEGIS command `{' '.join(command)}` exited {result.exit_code}: {detail}"
            )
        return result

    def _run_from_files(
        self,
        command: Sequence[str],
        *,
        timeout: float | None,
    ) -> CommandResult:
        """
        @brief      Invoke AEGIS through the host-mounted run exchange directory.
        @param[in]  command Complete AEGIS command tokens.
        @param[in]  timeout Wall-clock execution bound.
        @return     Container exit/timeout data with bounded file output.
        @exception  AegisProtocolError When exchange setup or output is unusable.
        """
        assert self.io_dir is not None  # construction chooses this path
        from adore.execution import SHELL_HEADER, ExecutionPaths

        paths = getattr(self.execute, "paths", ExecutionPaths())
        native = getattr(self.execute, "run_files", None)
        script_path = self.io_dir / AEGIS_SCRIPT
        stdout_path = self.io_dir / AEGIS_STDOUT_FILE
        stderr_path = self.io_dir / AEGIS_STDERR_FILE
        try:
            self.io_dir.mkdir(parents=True, exist_ok=True)
            stdout_path.unlink(missing_ok=True)
            stderr_path.unlink(missing_ok=True)
            quoted = " ".join(shlex.quote(str(token)) for token in command)
            script = (
                SHELL_HEADER
                + f"cd {shlex.quote(paths.worktree)}\n"
                f"{quoted} > {shlex.quote(paths.io + '/' + AEGIS_STDOUT_FILE)} "
                f"2> {shlex.quote(paths.io + '/' + AEGIS_STDERR_FILE)}\n"
            )
            if native is not None:
                script = SHELL_HEADER + "# Native AEGIS argv launch; no shell is executed.\n"
            with script_path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
        except OSError as exc:
            raise AegisProtocolError(f"AEGIS exchange setup failed: {exc}") from exc

        result = (
            native(list(command), stdout_path, stderr_path, timeout=timeout)
            if native is not None
            else self.execute([paths.shell, f"{paths.io}/{AEGIS_SCRIPT}"], timeout=timeout)
        )
        if result.timed_out:
            return result
        if result.exit_code != 0 and (
            not stdout_path.exists() or not stderr_path.exists()
        ):
            if "\ufffd" in result.stdout or "\ufffd" in result.stderr:
                raise AegisProtocolError(
                    f"AEGIS command `{' '.join(command)}` returned invalid UTF-8"
                )
            detail = (result.stderr or result.stdout).strip()[-1200:]
            raise AegisProtocolError(
                f"AEGIS command `{' '.join(command)}` exited "
                f"{result.exit_code}: {detail}"
            )
        stdout = self._read_exchange(stdout_path, "stdout", MAX_JSON_BYTES)
        stderr = self._read_exchange(stderr_path, "stderr", MAX_TEXT_BYTES)
        return replace(result, stdout=stdout, stderr=stderr)

    @staticmethod
    def _read_exchange(path: Path, stream: str, limit: int) -> str:
        """
        @brief      Read one required bounded AEGIS exchange artifact.
        @param[in]  path Host exchange-file path.
        @param[in]  stream Diagnostic stream name.
        @param[in]  limit Maximum accepted byte count.
        @return     UTF-8-decoded content; invalid bytes remain visible as U+FFFD.
        @exception  AegisProtocolError When the artifact is absent, unreadable,
                    or exceeds its bound.
        """
        try:
            with path.open("rb") as handle:
                content = handle.read(limit + 1)
        except OSError as exc:
            raise AegisProtocolError(
                f"AEGIS exchange {stream} is missing or unreadable: {exc}"
            ) from exc
        if len(content) > limit:
            raise AegisProtocolError(f"AEGIS exchange {stream} exceeds its size bound")
        return content.decode("utf-8", "replace")

    def _json(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = DEFAULT_TIMEOUT,
        allowed: tuple[int, ...] = (0,),
    ) -> tuple[dict[str, Any], CommandResult]:
        result = self._run(argv, timeout=timeout, allowed=allowed)
        encoded = result.stdout.encode("utf-8")
        if not encoded or len(encoded) > MAX_JSON_BYTES:
            raise AegisProtocolError("AEGIS JSON output is empty or exceeds its bound")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise AegisProtocolError(f"AEGIS returned malformed JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise AegisProtocolError("AEGIS JSON output must be an object")
        if type(payload.get("schema")) is not int or payload["schema"] != JSON_SCHEMA:
            raise AegisProtocolError(
                f"AEGIS JSON schema {payload.get('schema')!r} is unsupported; expected 1"
            )
        return payload, result

    @staticmethod
    def _task_id(task_id: str) -> None:
        if not isinstance(task_id, str) or TASK_ID_RE.fullmatch(task_id) is None:
            raise AegisProtocolError(f"invalid AEGIS task id {task_id!r}")

    def _status_list(self, payload: Mapping[str, Any]) -> list[dict[str, Any]]:
        if payload.get("command") != "status" or not isinstance(payload.get("tasks"), list):
            raise AegisProtocolError("AEGIS status list has an invalid command/tasks shape")
        unreadable = payload.get("unreadable")
        if not isinstance(unreadable, list) or unreadable:
            raise AegisProtocolError(f"AEGIS reports unreadable task journals: {unreadable!r}")
        if len(payload["tasks"]) > MAX_LIST_ITEMS:
            raise AegisProtocolError("AEGIS status task list exceeds its bound")
        result: list[dict[str, Any]] = []
        for index, item in enumerate(payload["tasks"]):
            if not isinstance(item, dict):
                raise AegisProtocolError(f"AEGIS tasks[{index}] must be an object")
            task_id = item.get("id")
            self._task_id(task_id)
            file = _repository_path(item.get("file"), f"tasks[{index}].file")
            if file != f".agentic/tasks/{task_id}.md":
                raise AegisProtocolError(f"AEGIS task {task_id} has a mismatched file")
            stage = item.get("stage")
            if stage not in STATUS_STAGES:
                raise AegisProtocolError(f"AEGIS task {task_id} has unknown stage {stage!r}")
            result.append(dict(item))
        return result

    def _decode_task(self, raw: Mapping[str, Any], *, expected: str) -> AegisTask:
        task_id = raw.get("id")
        self._task_id(task_id)
        if task_id != expected:
            raise AegisTaskError(
                f"AEGIS returned task {task_id!r} for pinned task {expected!r}"
            )
        title = _bounded_text(raw.get("title"), "task.title")
        file = _repository_path(raw.get("file"), "task.file")
        if file != f".agentic/tasks/{task_id}.md":
            raise AegisTaskError("AEGIS task file disagrees with its id")
        header_raw = raw.get("header")
        if not isinstance(header_raw, dict):
            raise AegisTaskError("AEGIS task header must be an object")
        required = {"stage", "type", "path", "requirements", "branch", "base", "opened"}
        missing = sorted(required - set(header_raw))
        if missing:
            raise AegisTaskError(f"AEGIS task header is missing {missing}")
        header = {
            str(key): _bounded_text(value, f"task.header.{key}", empty=True)
            for key, value in header_raw.items()
        }
        stage = raw.get("stage")
        if stage not in ALL_STAGES or header["stage"] != stage:
            raise AegisTaskError(f"AEGIS task carries an invalid/disagreeing stage {stage!r}")
        if header["type"] not in RUN_KINDS:
            raise AegisTaskError(f"AEGIS task has unsupported type {header['type']!r}")
        if header["path"] not in {"full", "quick"}:
            raise AegisTaskError(f"AEGIS task has unsupported path {header['path']!r}")
        if header["path"] == "quick" and header["type"] not in QUICK_KINDS:
            raise AegisTaskError("AEGIS quick path is only valid for fix/change tasks")
        if not header["branch"].strip() or any(ord(char) < 32 for char in header["branch"]):
            raise AegisTaskError("AEGIS task branch must be a non-empty safe string")
        step_file = raw.get("step_file")
        expected_step = STAGE_STEP_FILES[stage]
        if step_file != expected_step:
            raise AegisTaskError(
                f"AEGIS task stage {stage!r} names unexpected step file {step_file!r}"
            )
        if raw.get("done") is not (stage == "done"):
            raise AegisTaskError("AEGIS task done flag disagrees with its stage")
        checklist_raw = raw.get("checklist")
        log_raw = raw.get("log")
        if not isinstance(checklist_raw, list) or len(checklist_raw) > MAX_LIST_ITEMS:
            raise AegisTaskError("AEGIS task checklist must be a bounded list")
        if not isinstance(log_raw, list) or len(log_raw) > MAX_LIST_ITEMS:
            raise AegisTaskError("AEGIS task log must be a bounded list")
        checklist: list[ChecklistItem] = []
        for index, item in enumerate(checklist_raw):
            if not isinstance(item, dict) or type(item.get("done")) is not bool:
                raise AegisTaskError(f"AEGIS checklist[{index}] has an invalid shape")
            checklist.append(ChecklistItem(
                done=item["done"],
                item=_bounded_text(item.get("item"), f"checklist[{index}].item"),
            ))
        log = tuple(
            _bounded_text(item, f"log[{index}]") for index, item in enumerate(log_raw)
        )
        return AegisTask(
            task_id=task_id, title=title, file=file, header=header, stage=stage,
            step_file=step_file, done=stage == "done", checklist=tuple(checklist),
            log=log,
        )

    def _decode_check(
        self,
        payload: Mapping[str, Any],
        exit_code: int,
        task_id: str | None,
        strict: bool,
    ) -> AegisCheck:
        if payload.get("command") != "check" or payload.get("task") != task_id:
            raise AegisProtocolError("AEGIS check response disagrees with the request")
        findings_raw = payload.get("findings")
        summary = payload.get("summary")
        runs_raw = payload.get("run")
        if not isinstance(findings_raw, list) or not isinstance(summary, dict) \
                or not isinstance(runs_raw, list):
            raise AegisProtocolError("AEGIS check response has an invalid shape")
        findings: list[AegisFinding] = []
        for index, item in enumerate(findings_raw):
            if not isinstance(item, dict) or item.get("level") not in {"ERROR", "WARN", "NOTE"}:
                raise AegisProtocolError(f"AEGIS finding[{index}] has an invalid shape")
            findings.append(AegisFinding(
                level=item["level"],
                check=_bounded_text(item.get("check"), f"finding[{index}].check"),
                path=_bounded_text(item.get("path"), f"finding[{index}].path"),
                message=_bounded_text(item.get("message"), f"finding[{index}].message"),
            ))
        counts: dict[str, int] = {}
        for key in ("errors", "warnings", "notes"):
            value = summary.get(key)
            if type(value) is not int or value < 0:
                raise AegisProtocolError(f"AEGIS check summary.{key} must be non-negative")
            counts[key] = value
        actual = {
            "errors": sum(item.level == "ERROR" for item in findings),
            "warnings": sum(item.level == "WARN" for item in findings),
            "notes": sum(item.level == "NOTE" for item in findings),
        }
        if counts != actual:
            raise AegisProtocolError("AEGIS check summary disagrees with its findings")
        strict_raw = payload.get("strict")
        if strict:
            if not isinstance(strict_raw, dict) or strict_raw.get("enabled") is not True:
                raise AegisProtocolError("AEGIS strict check omitted its strict result")
            promoted = strict_raw.get("promoted_warnings")
            passed = strict_raw.get("passed")
            if type(promoted) is not int or promoted < 0 or type(passed) is not bool:
                raise AegisProtocolError("AEGIS strict result has invalid fields")
            if (exit_code == 0) is not passed:
                raise AegisProtocolError("AEGIS strict result disagrees with its exit code")
        else:
            if strict_raw is not None or exit_code != 0:
                raise AegisProtocolError("AEGIS advisory check has an invalid strict/exit result")
            promoted, passed = 0, True
        runs: list[AegisCommandRun] = []
        for index, item in enumerate(runs_raw):
            if not isinstance(item, dict) or item.get("status") not in {
                "ok", "failed", "stopped", "skipped",
            }:
                raise AegisProtocolError(f"AEGIS check run[{index}] has an invalid shape")
            status = item["status"]
            exit_value = item.get("exit")
            seconds = item.get("seconds")
            if status != "skipped" and (
                type(exit_value) is not int
                or not isinstance(seconds, (int, float))
            ):
                raise AegisProtocolError(f"AEGIS executed run[{index}] lacks exit/seconds")
            runs.append(AegisCommandRun(
                name=_bounded_text(item.get("name"), f"run[{index}].name"),
                status=status,
                exit_code=exit_value if type(exit_value) is int else None,
                seconds=float(seconds) if isinstance(seconds, (int, float)) else None,
                reason=_bounded_text(item.get("reason", ""), f"run[{index}].reason", empty=True),
            ))
        return AegisCheck(
            exit_code=exit_code,
            task_id=task_id,
            findings=tuple(findings),
            errors=counts["errors"],
            warnings=counts["warnings"],
            notes=counts["notes"],
            strict_enabled=strict,
            promoted_warnings=promoted,
            passed=passed,
            runs=tuple(runs),
            raw=dict(payload),
        )


# END OF FILE
