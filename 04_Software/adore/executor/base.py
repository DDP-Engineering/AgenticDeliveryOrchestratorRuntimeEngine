"""Pi executor interface and normalized stage results."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from adore.instructions import InstructionDelivery
from adore.util import CommandResult


class ExecTarget(Protocol):
    """
    Callable that runs a command in the run's execution backend.
    The backend binds resource identity/environment and exposes target
             paths for controlled commands. Pi additionally requires the backend's
             RPC process seam. Exit codes and authoritative timeouts are data.
    """

    def __call__(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> CommandResult:
        """
        Run one command inside the container.
        argv: Command and arguments (must stay WSL-safe: no
                         element may rely on embedded spaces surviving).
        timeout: Optional wall-clock bound.
        Returns: The captured CommandResult.
        """
        ...  # pragma: no cover - protocol signature only


@dataclass
class GateRun:
    """
    Result of running one workflow gate via the executor.
    The conductor's decision inputs (design 7a step 3): the exit
             code, authoritative wrapper-timeout flag, and whether the executor
             asked clarification questions. `output` is the raw event stream
             (also persisted in the run's io dir for audit). `artifact_dirs`
             names immutable per-launch archive directories created by the RPC
             launcher. There is deliberately no session id: every stage gets a
             FRESH executor session, so nothing is ever continued. `diagnostics`
             optionally carries host-normalized operational streams for safe viewing.
    """

    exit_code: int
    has_questions: bool = False
    questions: str = ""
    output: str = ""
    stderr: str = ""
    timed_out: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    tokens_reported: bool | None = None
    cost_usd: float = 0.0
    cost_reported: bool = False
    artifact_dirs: list[str] = field(default_factory=list)
    diagnostics: dict[str, str] | None = None

    @property
    def ok(self) -> bool:
        """
        True when the executor exited cleanly (code 0).
        Clean exit is necessary but not sufficient to advance: the
                 conductor still checks questions and runs invariants.
        Returns: Exit-status flag.
        """
        return self.exit_code == 0


class Executor(ABC):
    """Abstract executor launcher; Pi is its only implementation."""

    @abstractmethod
    def run_gate(
        self,
        execute: ExecTarget,
        worktree: str | Path,
        io_dir: str | Path,
        prompt: str,
        *,
        timeout: float | None = None,
        archive_stem: str = "",
        package_secrets: dict[str, str] | None = None,
        cancel: Callable[[], bool] | None = None,
        instructions: InstructionDelivery | None = None,
        context_key: str = "",
    ) -> GateRun:
        """
        Launch the executor for a single workflow gate.
        Each job gate starts a bounded process resuming its exact
                    private conversation. The durable workflow state/journal
                    remains authoritative for stage progression. Disposable
                    probes have no job conversation.
        execute: Exec seam bound to the run's container.
        worktree: HOST path of the run's worktree (questions file).
        io_dir: HOST path of the run's io exchange dir (recording
                           and diagnostics; mounted at /adore/io).
        prompt: Gate-specific instruction (any content; it never
                           travels through argv).
        timeout: Wall-clock bound (run budgets).
        archive_stem: Optional immutable archive name stem.
        package_secrets: Optional known credentials for bounded and
                                   redacted package-enabled gate retention.
        instructions: Optional acknowledgement-bound instruction handoff.
        context_key: Fingerprint of the ticket context acknowledged by the attempt.
        cancel: Cancellation check, passed only when
                           `cancel_grace_seconds` returns a value.
        Returns: A GateRun describing the outcome.
        """

    def cancel_grace_seconds(self, execute: ExecTarget) -> float | None:
        """
        Whether this launch watches the run's cancellation itself.
        `None` (the default): the conductor stops the target when a
                    cancel arrives. A number: `run_gate` takes a `cancel` check,
                    stops the executor itself, and the conductor stops the
                    target only when the gate is still running that many
                    seconds after the cancel was seen.
        execute: Exec seam the gate will run on.
        Returns: Seconds the executor needs to end on cancel, or None.
        """
        return None
