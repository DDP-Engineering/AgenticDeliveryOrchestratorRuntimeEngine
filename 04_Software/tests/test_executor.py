"""Pi factory and refusal of unsupported process targets."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from adore.executor.launcher import (
    PiExecutor,
    build_executor,
)
from adore.prompts import PromptCatalog
from adore.util import CommandResult


class FakeExec:
    """Exec-seam double: records argv, simulates gate side effects."""

    def __init__(
        self,
        result: CommandResult,
        side_effect: Callable[[], None] | None = None,
    ) -> None:
        """
        Configure the double.
        result: The CommandResult to return.
        side_effect: Callable simulating what the executor wrote
                                (output file, questions file) while running.
        """
        self.result = result
        self.side_effect = side_effect
        self.calls: list[list[str]] = []
        self.timeouts: list[float | None] = []

    def __call__(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> CommandResult:
        """
        Record the call, run the side effect, return the result.
        argv: Command vector.
        timeout: Recorded for budget assertions.
        Returns: The canned CommandResult.
        """
        self.calls.append([str(part) for part in argv])
        self.timeouts.append(timeout)
        if self.side_effect:
            self.side_effect()
        return self.result


# PUBLIC API / TESTS


def test_executor_failure_passes_through_as_data(tmp_path: Path) -> None:
    """A callable-only target is refused without executing or writing files."""
    target = FakeExec(CommandResult())
    result = PiExecutor("m").run_gate(target, tmp_path, tmp_path / "io", "prompt")
    assert result.exit_code == 126 and not result.ok
    assert "RPC process target" in result.stderr
    assert target.calls == [] and not (tmp_path / "io").exists()


def test_factory_wires_questions_file() -> None:
    """
    The factory builds the Pi launcher and passes the configured
             questions filename through.
    """
    prompts = PromptCatalog()
    executor = build_executor("m", questions_file="ROBO_QUESTIONS.md", prompts=prompts)
    assert isinstance(executor, PiExecutor)
    assert executor.questions_file == "ROBO_QUESTIONS.md"
    assert executor.prompts is prompts


def test_factory_selects_pi() -> None:
    """Pi is the only executor: the factory always returns PiExecutor."""
    executor = build_executor("openai/gpt-5.5")
    assert isinstance(executor, PiExecutor)
    assert executor.questions_file == "ADORE_QUESTIONS.md"


def test_pi_rpc_argv_carries_thinking_level() -> None:
    """Explicit Pi effort reaches the process; empty leaves its default."""
    from adore.executor.launcher import pi_rpc_argv
    assert pi_rpc_argv("gpt-5", "openai", thinking="medium")[-2:] == ["--thinking", "medium"]
    assert "--thinking" not in pi_rpc_argv("gpt-5", "openai")
