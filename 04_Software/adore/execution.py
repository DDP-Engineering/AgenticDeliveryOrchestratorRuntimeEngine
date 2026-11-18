"""Shared execution paths, lifecycle and container adapter."""

from __future__ import annotations

from collections.abc import Sequence
from copy import copy
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Protocol

from adore.isolation import (
    CONTAINER_IO_MOUNT,
    CONTAINER_WORKTREE_MOUNT,
    ContainerManager,
    IsolationError,
)
from adore.util import CommandResult, strict_json_loads, utc_now_iso

MAX_OUTPUT_BYTES = 65536
# REUSE-IgnoreStart
SHELL_HEADER = (
    "#!/bin/sh\n"
    "# Copyright (c) 2026 DDP Engineering\n"
    "# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
    "# Commercial use requires a separate commercial license.\n"
    "# See the LICENSE.txt file for full license details.\n"
    "# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n"
)
# REUSE-IgnoreEnd


class ExecutionRecoveryError(IsolationError):
    """Explicit recovery is required; transient retry cannot replay setup."""


class PreparationResultError(IsolationError):
    """Preserve command evidence while refusing an incomplete runner receipt."""

    def __init__(self, outcome: dict) -> None:
        self.outcome = outcome
        super().__init__("preparation result missing or corrupt; explicit recovery required")


@dataclass(frozen=True)
class ExecutionPaths:
    """Backend-native gate paths and shell, independent of host paths."""

    worktree: str = CONTAINER_WORKTREE_MOUNT
    io: str = CONTAINER_IO_MOUNT
    shell: str = "sh"


class ExecutionTarget(Protocol):
    """Callable native command target and paths shared by all adapters."""

    paths: ExecutionPaths

    def __call__(self, argv: Sequence[str], *, timeout: float | None = None) -> CommandResult:
        """Execute one bounded argv command on the bound owned target."""
        ...


class ExecutionBackend(Protocol):
    """Adapter contract for paths, readiness, commands and owned lifecycle."""

    paths: ExecutionPaths

    def executor_environment(self) -> dict[str, str]:
        """Supply backend-specific executor homes without new credentials."""
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
        """Create/resume a target without executing preparation implicitly."""
        ...

    def bind(self, name: str, env: dict[str, str], expected: dict | None = None) -> ExecutionTarget:
        """Bind command execution and paths to one owned resource."""
        ...

    def verify_required_tools(
        self, name: str, checks: Sequence[str], *, env: dict[str, str]
    ) -> None:
        """Check declared tools without installing them."""
        ...

    def resource_identity(self, name: str) -> dict[str, str]:
        """Read authoritative target identity for durable recovery."""
        ...

    def image_identity(self, image: str) -> str:
        """Resolve image/build identity separately from run identity."""
        ...

    def stop(self, name: str, *, expected: dict | None = None) -> None:
        """Park an owned target without releasing its persistent files."""
        ...

    def interrupt(self, name: str, *, expected: dict | None = None) -> None:
        """Stop active commands within a bounded cancellation window."""
        ...

    def remove(self, name: str, *, expected: dict | None = None) -> None:
        """Release only resources owned by the run; preserve shared images/caches."""
        ...


class BoundTarget:
    """Callable gate target carrying backend-native paths and identity."""

    def __init__(
        self, backend: ContainerBackend, name: str, env: dict[str, str], expected: dict | None,
        secrets: Sequence[str] = (),
    ) -> None:
        self.backend, self.name = backend, name
        self.env, self.expected = dict(env), dict(expected) if expected else None
        self.paths = backend.paths
        self.secrets = sorted((value for value in secrets if value), key=len, reverse=True)

    def redact(self, text: str) -> str:
        """
        Mask this target's per-launch secret values in evidence.
        text: Evidence text before retention.
        Returns: The text with each value replaced by [REDACTED].
        """
        for value in self.secrets:
            text = text.replace(value, "[REDACTED]")
        return text

    def __call__(self, argv: Sequence[str], *, timeout: float | None = None) -> CommandResult:
        """
        Execute the admitted immutable ID and settle expired commands.
        argv: Command argument vector.
        timeout: Maximum command duration.
        Returns: Original command result after any required verified interruption.
        Raises ExecutionRecoveryError: When ownership or recovery is unconfirmed.
        """
        observed = self.backend._admit_command(self.name, self.expected)
        result = self.backend.manager.exec(
            observed["container_id"], argv, timeout=timeout, env=self.env,
        )
        if result.timed_out:
            self.backend._settle_timeout(self.name, observed)
        return result

    def spawn(self, argv: Sequence[str], *, env: dict[str, str] | None = None):
        """
        Start a streaming command after verifying the pinned identity.
        The bound executor environment is extended by `env` (for
                    example Pi's isolation variables); the caller bounds and
                    ends the returned process.
        argv: Command and arguments to run inside the container.
        env: Extra exec-time variables for this command only.
        Returns: The started `subprocess.Popen` with binary pipes.
        Raises ExecutionRecoveryError: When the resource identity changed.
        """
        observed = self.backend._admit_command(self.name, self.expected)
        self._stream_identity = observed
        return self.backend.manager.spawn(
            observed["container_id"], argv, env={**self.env, **(env or {})})

    def settle_timeout(self) -> None:
        """Quiesce all timed-out RPC descendants before the container is reused."""
        observed = getattr(self, "_stream_identity", None)
        if observed is None:
            raise ExecutionRecoveryError("no admitted RPC invocation to settle")
        self.backend._settle_timeout(self.name, observed)

    def settle_failed_session(self) -> None:
        """
        Quiesce what an RPC session that ended in a protocol failure left running.
        Ending the client does not end Pi inside the container. The container
                    is stopped exactly as after a timeout and starts again with
                    the next command. One that is no longer running, or is no
                    longer the admitted one, is left to the next command's checks.
        Raises ExecutionRecoveryError: When the interruption cannot be confirmed.
        """
        observed = getattr(self, "_stream_identity", None)
        if observed is None:
            return
        try:
            current = self.backend.resource_identity(self.name)
        except IsolationError:
            return
        if current["status"] != "running" or any(
                current[key] != observed[key] for key in ("container_id", "image_id")):
            return
        self.backend._settle_timeout(self.name, observed)


class ContainerBackend:
    """Container implementation of shared execution and recovery contract."""

    paths = ExecutionPaths()

    def __init__(self, manager: ContainerManager) -> None:
        self.manager = manager
        self._pending_resume: dict[str, dict[str, str]] = {}
        self._blocked: set[str] = set()
        self._operator_parked: set[str] = set()

    def _checked_identity(
        self, name: str, expected: dict | None, *, status: str | None = "running",
    ) -> dict[str, str]:
        """
        Require authoritative ownership and lifecycle before a control.
        name: Owned run name used for strict runtime inspection.
        expected: Optional durable or invocation identity pins.
        status: Required authoritative lifecycle state.
        Returns: Validated current container identity.
        Raises ExecutionRecoveryError: When identity or state is unconfirmed.
        """
        if expected and (
            expected.get("kind") == "local"
            or not {"container_id", "image_id"} <= expected.keys()
        ):
            raise ExecutionRecoveryError("execution backend changed; restore the pinned profile")
        try:
            observed = self.resource_identity(name)
        except IsolationError as exc:
            raise ExecutionRecoveryError("execution resource identity unconfirmed") from exc
        if status is not None and observed["status"] != status or expected and any(
            observed[key] != expected[key] for key in ("container_id", "image_id")
        ):
            raise ExecutionRecoveryError("execution resource identity or state changed")
        return observed

    def _admit_command(self, name: str, expected: dict | None) -> dict[str, str]:
        """
        Resume only a proven timed-out resource before command dispatch.
        name: Owned run name.
        expected: Durable identity pins when available.
        Returns: Authoritative running invocation identity.
        Raises ExecutionRecoveryError: When recovery remains unsafe.
        """
        if name in self._blocked or name in self._operator_parked:
            raise ExecutionRecoveryError(
                "container recovery unconfirmed; explicit recovery required",
            )
        pending = self._pending_resume.get(name)
        if pending is not None:
            self._blocked.add(name)
            try:
                observed = self._checked_identity(name, expected or pending, status="exited")
                # Reject changed caller pins before any restart effect.
                if any(pending[key] != observed[key] for key in ("container_id", "image_id")):
                    raise ExecutionRecoveryError("execution resource identity changed")
                if name in self._operator_parked:
                    raise ExecutionRecoveryError("container restart cancelled by operator")
                self.manager.start(observed["container_id"])
                if name in self._operator_parked:
                    self.manager.interrupt(observed["container_id"])
                    self._checked_identity(name, pending, status="exited")
                    raise ExecutionRecoveryError("container restart cancelled by operator")
                self._checked_identity(name, pending)
            except IsolationError as exc:
                raise ExecutionRecoveryError("container restart unconfirmed") from exc
            self._pending_resume.pop(name, None)
            self._blocked.discard(name)
        try:
            observed = self._checked_identity(name, expected)
            if name in self._operator_parked:
                raise ExecutionRecoveryError("container execution cancelled by operator")
        except IsolationError:
            self._blocked.add(name)
            raise
        return observed

    def _settle_timeout(self, name: str, expected: dict[str, str]) -> None:
        """
        Confirm all expired command processes stopped before returning.
        name: Owned run name.
        expected: Immutable identity captured before command dispatch.
        Raises ExecutionRecoveryError: When interruption cannot be confirmed.
        """
        self._blocked.add(name)
        try:
            self._checked_identity(name, expected)
            self.manager.interrupt(expected["container_id"])
            self._checked_identity(name, expected, status="exited")
        except IsolationError as exc:
            raise ExecutionRecoveryError("container timeout interruption unconfirmed") from exc
        if name not in self._operator_parked:
            self._pending_resume[name] = expected
        self._blocked.discard(name)

    def executor_environment(self) -> dict[str, str]:
        """A container gets no backend-specific executor home."""
        return {}

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
        """Provision the selected image without running preparation implicitly."""
        resumed = name in self._pending_resume
        if resumed or name in self._blocked:
            self._admit_command(name, self._pending_resume.get(name))
        manager = copy(self.manager) if image is not None else self.manager
        if image is not None:
            manager.image = image
            manager.pull_never = True
        manager.ensure_volumes()
        result = manager.provision(name, repo, worktree, io, env)
        self._operator_parked.discard(name)
        return "started" if resumed and result == "running" else result

    def bind(self, name: str, env: dict[str, str], expected: dict | None = None,
             *, secrets: Sequence[str] = ()) -> ExecutionTarget:
        """
        Bind this adapter's command and target-path contract.
        name: Container name.
        env: Exec-time environment of every command on the target.
        expected: Pinned resource identity.
        secrets: Values that exist only for this binding (a ChatGPT
                    stage token) and are masked in the launch evidence.
        Returns: The bound target.
        """
        return BoundTarget(self, name, env, expected, secrets)

    def verify_required_tools(
        self, name: str, checks: Sequence[str], *, env: dict[str, str]
    ) -> None:
        """Retain declared image-tool readiness without any setup effects."""
        self.manager.verify_required_tools(name, checks, env=env)

    def authorize_system_packages(self, name: str, *, expected: dict) -> None:
        """
        Grant environment administration only on the verified owned container.
        name: Run container name.
        expected: Persisted container and image identities.
        """
        self.verify_identity(name, expected, running=True)
        # Address the immutable ID, so a name replacement between inspect and
        # exec cannot receive the administrative bootstrap.
        self.manager.authorize_system_packages(expected["container_id"])

    def resource_identity(self, name: str) -> dict[str, str]:
        """Return authoritative container/image IDs and current status."""
        return self.manager.resource_identity(name)

    def image_identity(self, image: str) -> str:
        """Resolve a local image without changing it."""
        return self.manager.image_identity(image)

    def verify_identity(self, name: str, expected: dict | None, *, running: bool = False) -> None:
        """Refuse stale IDs before issuing commands or resource controls."""
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
        """Stop the verified run target, retaining its container filesystem."""
        self._operator_parked.add(name)
        self._pending_resume.pop(name, None)
        observed = self._checked_identity(name, expected, status=None)
        self.manager.stop(observed["container_id"])

    def interrupt(self, name: str, *, expected: dict | None = None) -> None:
        """Interrupt only the verified active run target."""
        self._operator_parked.add(name)
        self._pending_resume.pop(name, None)
        observed = self._checked_identity(name, expected, status=None)
        self.manager.interrupt(observed["container_id"])

    def remove(self, name: str, *, expected: dict | None = None) -> None:
        """Remove the immutable executor; path-bound companion release stays separate."""
        self._operator_parked.add(name)
        self._pending_resume.pop(name, None)
        if expected and (expected.get("kind") == "local"
                         or not {"container_id", "image_id"} <= expected.keys()):
            raise ExecutionRecoveryError(
                    "execution backend changed; restore the pinned profile")
        # Explicit cleanup of an already absent resource is idempotent.
        if self.manager.status(name) != "absent":
            observed = self._checked_identity(name, expected, status=None)
            # Lifecycle controls never re-resolve a mutable name at the runtime.
            # Full proxy/network release needs host path proof and belongs to release_owned.
            self.manager.remove_executor(observed["container_id"])
        self._operator_parked.discard(name)


def redact_output(text: str, secrets: dict[str, str]) -> str:
    """
    Bound and redact retained external output, including configured values.
    text: External command output.
    secrets: In-memory credential values; never written to evidence.
    Returns: Bounded redacted text.
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
) -> dict:
    """
    Execute one pinned script through bounded files and return its evidence.
    target: Verified backend-bound command target.
    io_dir: Host exchange directory.
    attempt: Monotonic operator-authorized preparation attempt.
    index: Zero-based step index.
    step: Normalized name/run mapping.
    timeout: Remaining bounded wall time.
    secrets: In-memory values used for output redaction.
    Returns: Closed timestamped outcome with authoritative exit/timeout evidence.
    Raises IsolationError: For missing or malformed file-protocol evidence.
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
