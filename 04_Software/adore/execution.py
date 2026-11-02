#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    execution.py
@brief   Shared execution paths, lifecycle and container adapter.
@details Keeps backend-specific command, identity and cleanup behavior out of
         the conductor. The local adapter and image builder extend this seam.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Sequence
from copy import copy
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Protocol

from adore.branding import CONTAINER_CODEX_HOME, CONTAINER_OPENCODE_AUTH_DIR
from adore.isolation import (
    CONTAINER_IO_MOUNT,
    CONTAINER_WORKTREE_MOUNT,
    ContainerManager,
    IsolationError,
)
from adore.util import CommandResult, strict_json_loads, utc_now_iso

# CONSTANTS
MAX_OUTPUT_BYTES = 65536
SHELL_HEADER = (
    "#!/bin/sh\n"
    "# Copyright (c) 2026 DDP Engineering\n"
    "# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
    "# Commercial use requires a separate commercial license.\n"
    "# See the LICENSE.txt file for full license details.\n"
    "# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n"
)


# DATA MODELS / TYPEDEFINITIONS


class ExecutionRecoveryError(IsolationError):
    """@brief Explicit recovery is required; transient retry cannot replay setup."""


class PreparationResultError(IsolationError):
    """@brief Preserve command evidence while refusing an incomplete runner receipt."""

    def __init__(self, outcome: dict) -> None:
        self.outcome = outcome
        super().__init__("preparation result missing or corrupt; explicit recovery required")


@dataclass(frozen=True)
class ExecutionPaths:
    """@brief Backend-native gate paths and shell, independent of host paths."""

    worktree: str = CONTAINER_WORKTREE_MOUNT
    io: str = CONTAINER_IO_MOUNT
    shell: str = "sh"


class ExecutionTarget(Protocol):
    """@brief Callable native command target and paths shared by all adapters."""

    paths: ExecutionPaths

    def __call__(self, argv: Sequence[str], *, timeout: float | None = None) -> CommandResult:
        """@brief Execute one bounded argv command on the bound owned target."""
        ...


class ExecutionBackend(Protocol):
    """@brief Adapter contract for paths, readiness, commands and owned lifecycle."""

    paths: ExecutionPaths

    def executor_environment(self, executor: str) -> dict[str, str]:
        """@brief Supply backend-specific executor homes without new credentials."""
        ...

    def auth_directory(self, executor: str) -> str:
        """@brief Return the backend-native directory for existing auth staging."""
        ...

    def provision(
        self,
        name: str,
        repo: Path,
        worktree: Path,
        io: Path,
        env: dict[str, str],
        *,
        image: str | None = None,
    ) -> str:
        """@brief Create/resume a target without executing preparation implicitly."""
        ...

    def bind(self, name: str, env: dict[str, str], expected: dict | None = None) -> ExecutionTarget:
        """@brief Bind command execution and paths to one owned resource."""
        ...

    def verify_required_tools(
        self, name: str, checks: Sequence[str], *, env: dict[str, str]
    ) -> None:
        """@brief Check declared tools without installing them."""
        ...

    def resource_identity(self, name: str) -> dict[str, str]:
        """@brief Read authoritative target identity for durable recovery."""
        ...

    def image_identity(self, image: str) -> str:
        """@brief Resolve image/build identity separately from run identity."""
        ...

    def stop(self, name: str, *, expected: dict | None = None) -> None:
        """@brief Park an owned target without releasing its persistent files."""
        ...

    def interrupt(self, name: str, *, expected: dict | None = None) -> None:
        """@brief Stop active commands within a bounded cancellation window."""
        ...

    def remove(self, name: str, *, expected: dict | None = None) -> None:
        """@brief Release only resources owned by the run; preserve shared images/caches."""
        ...


class BoundTarget:
    """@brief Callable gate target carrying backend-native paths and identity."""

    def __init__(
        self, backend: ContainerBackend, name: str, env: dict[str, str], expected: dict | None
    ) -> None:
        self.backend, self.name, self.env, self.expected = backend, name, env, expected
        self.paths = backend.paths

    def __call__(self, argv: Sequence[str], *, timeout: float | None = None) -> CommandResult:
        """@brief Execute argv only after verifying the pinned resource identity."""
        self.backend.verify_identity(self.name, self.expected, running=True)
        return self.backend.manager.exec(self.name, argv, timeout=timeout, env=self.env)

    def spawn(self, argv: Sequence[str], *, env: dict[str, str] | None = None):
        """
        @brief      Start a streaming command after verifying the pinned identity.
        @details    The bound executor environment is extended by `env` (for
                    example Pi's isolation variables); the caller bounds and
                    ends the returned process.
        @param[in]  argv Command and arguments to run inside the container.
        @param[in]  env Extra exec-time variables for this command only.
        @return     The started `subprocess.Popen` with binary pipes.
        @exception  ExecutionRecoveryError When the resource identity changed.
        """
        self.backend.verify_identity(self.name, self.expected, running=True)
        return self.backend.manager.spawn(
            self.name, argv, env={**self.env, **(env or {})})


# PUBLIC API


class ContainerBackend:
    """@brief Container implementation of shared execution and recovery contract."""

    paths = ExecutionPaths()

    def __init__(self, manager: ContainerManager) -> None:
        self.manager = manager

    def executor_environment(self, executor: str) -> dict[str, str]:
        """@brief Retain the container Codex home environment contract."""
        return {"CODEX_HOME": CONTAINER_CODEX_HOME} if executor == "codex" else {}

    def auth_directory(self, executor: str) -> str:
        """@brief Preserve container-native staged authentication destinations."""
        return {"opencode": CONTAINER_OPENCODE_AUTH_DIR, "codex": CONTAINER_CODEX_HOME}.get(
            executor, ""
        )

    def provision(
        self,
        name: str,
        repo: Path,
        worktree: Path,
        io: Path,
        env: dict[str, str],
        *,
        image: str | None = None,
    ) -> str:
        """@brief Provision using the normalized image while retaining legacy defaults."""
        manager = copy(self.manager) if image is not None else self.manager
        if image is not None:
            manager.image = image
            manager.pull_never = True
        manager.ensure_volumes()
        return manager.provision(name, repo, worktree, io, env)

    def bind(self, name: str, env: dict[str, str], expected: dict | None = None) -> ExecutionTarget:
        """@brief Bind this adapter's command and target-path contract."""
        return BoundTarget(self, name, env, expected)

    def verify_required_tools(
        self, name: str, checks: Sequence[str], *, env: dict[str, str]
    ) -> None:
        """@brief Retain declared image-tool readiness without any setup effects."""
        self.manager.verify_required_tools(name, checks, env=env)

    def resource_identity(self, name: str) -> dict[str, str]:
        """@brief Return authoritative container/image IDs and current status."""
        return self.manager.resource_identity(name)

    def image_identity(self, image: str) -> str:
        """@brief Resolve a local image without changing it."""
        return self.manager.image_identity(image)

    def verify_identity(self, name: str, expected: dict | None, *, running: bool = False) -> None:
        """@brief Refuse stale IDs before issuing commands or resource controls."""
        if expected:
            if (expected.get("kind") == "local"
                    or not {"container_id", "image_id"} <= expected.keys()):
                raise ExecutionRecoveryError(
                    "execution backend changed; restore the pinned profile")
            observed = self.resource_identity(name)
            if (
                observed["container_id"] != expected["container_id"]
                or observed["image_id"] != expected["image_id"]
                or running
                and observed["status"] != "running"
            ):
                raise ExecutionRecoveryError(
                    "execution resource identity changed; explicit recovery required"
                )

    def stop(self, name: str, *, expected: dict | None = None) -> None:
        """@brief Stop the verified run target, retaining its container filesystem."""
        self.verify_identity(name, expected)
        self.manager.stop(name)

    def interrupt(self, name: str, *, expected: dict | None = None) -> None:
        """@brief Interrupt only the verified active run target."""
        self.verify_identity(name, expected)
        self.manager.interrupt(name)

    def remove(self, name: str, *, expected: dict | None = None) -> None:
        """@brief Release the verified target and its owned egress resources."""
        if expected and (expected.get("kind") == "local"
                         or not {"container_id", "image_id"} <= expected.keys()):
            raise ExecutionRecoveryError(
                    "execution backend changed; restore the pinned profile")
        # Explicit cleanup of an already absent resource is idempotent.
        if expected and self.manager.status(name) != "absent":
            self.verify_identity(name, expected)
        self.manager.remove(name)


def redact_output(text: str, secrets: dict[str, str]) -> str:
    """
    @brief Bound and redact retained external output, including configured values.
    @param[in] text External command output.
    @param[in] secrets In-memory credential values; never written to evidence.
    @return Bounded redacted text.
    """
    for value in sorted((v for v in secrets.values() if v), key=len, reverse=True):
        text = text.replace(value, "[REDACTED]")
    text = re.sub(r"(?i)(Bearer\s+)\S+", r"\1[REDACTED]", text)
    return text.encode("utf-8")[:MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore")


def run_preparation_step(
    target: ExecutionTarget,
    io_dir: Path,
    attempt: int,
    index: int,
    step: dict,
    *,
    timeout: float,
    secrets: dict[str, str],
    auth_file: str | None = None,
) -> dict:
    """
    @brief Execute one pinned script through bounded files and return its evidence.
    @param[in] target Verified backend-bound command target.
    @param[in] io_dir Host exchange directory.
    @param[in] attempt Monotonic operator-authorized preparation attempt.
    @param[in] index Zero-based step index.
    @param[in] step Normalized name/run mapping.
    @param[in] timeout Remaining bounded wall time.
    @param[in] secrets In-memory values used for output redaction.
    @param[in] auth_file Existing staged executor auth path, solely for redaction.
    @return Closed timestamped outcome with authoritative exit/timeout evidence.
    @exception IsolationError For missing or malformed file-protocol evidence.
    """
    relative = f"preparation/attempt-{attempt}/step-{index + 1}"
    directory = io_dir / relative
    if not directory.resolve().is_relative_to(io_dir.resolve()) or any(
        parent.is_symlink() for parent in (directory.parent, directory.parent.parent)
    ):
        raise IsolationError("preparation transport escaped owned IO directory")
    directory.mkdir(parents=True, exist_ok=False)
    if not directory.resolve().is_relative_to(io_dir.resolve()) or any(
        parent.is_symlink() for parent in (directory.parent, directory.parent.parent)
    ):
        raise IsolationError("preparation transport escaped owned IO directory")
    (directory / "run.sh").write_text(
        SHELL_HEADER + step["run"] + "\n", encoding="utf-8", newline="\n"
    )
    (directory / "runner.py").write_bytes(
        Path(__file__).with_name("preparation_runner.py").read_bytes()
    )
    (directory / "secret-keys.json").write_text(json.dumps(list(secrets)), encoding="utf-8")
    started = utc_now_iso()
    argv = [
        "python3",
        f"{target.paths.io}/{relative}/runner.py",
        str(timeout),
        f"{target.paths.io}/{relative}",
        target.paths.worktree,
    ]
    if auth_file is not None:
        argv.append(auth_file)
    result = target(argv, timeout=timeout + 10)
    outcome = {
        "index": index,
        "name": step["name"],
        "started_at": started,
        "finished_at": utc_now_iso(),
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "cancelled": False,
        "stdout": "",
        "stderr": "",
    }
    missing_stream = False
    for stream in ("stdout", "stderr"):
        path = directory / f"{stream}.txt"
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise PreparationResultError(outcome)
        if path.exists() and not path.is_file():
            raise PreparationResultError(outcome)
        if path.is_file():
            with path.open("rb") as handle:
                text = handle.read(MAX_OUTPUT_BYTES).decode("utf-8", errors="replace")
            outcome[stream] = redact_output(text, secrets)
        else:
            missing_stream = True
            if stream == "stderr":
                outcome[stream] = redact_output(result.stderr, secrets)
    meta = directory / "result.json"
    if not result.timed_out:
        try:
            if (
                missing_stream
                or meta.is_symlink()
                or not meta.is_file()
                or not meta.resolve().is_relative_to(directory.resolve())
                or meta.stat().st_size > 2048
            ):
                raise ValueError
            record = strict_json_loads(meta.read_text(encoding="utf-8"))
            if (
                set(record) != {"exit_code", "timed_out"}
                or type(record["exit_code"]) is not int
                or not -255 <= record["exit_code"] <= 255
                or type(record["timed_out"]) is not bool
                or record["timed_out"]
                and record["exit_code"] != 124
                or result.exit_code != record["exit_code"]
            ):
                raise ValueError
            outcome.update(record)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            raise PreparationResultError(outcome) from exc
    return outcome


def __getattr__(name: str):
    """@brief Expose the local adapter lazily without cyclic contract imports."""
    if name == "LocalBackend":
        from adore.local_execution import LocalBackend

        return LocalBackend
    raise AttributeError(name)

# END OF FILE
