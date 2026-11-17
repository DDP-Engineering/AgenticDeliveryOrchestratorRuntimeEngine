"""Public container timeout admission, evidence and recovery contracts."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict
import json
from types import SimpleNamespace

from adore import orchestrator as orchestrator_module
from adore.execution import ContainerBackend, ExecutionRecoveryError
from adore.isolation import ContainerManager, IsolationError
from adore.util import CommandResult
import pytest

from tests.test_orchestrator import FakeAegis, FakeExecutor, make_engine, make_run, task

NAME = "owned-timeout-run"
CID = "a" * 64
IMAGE = "sha256:" + "b" * 64


class Runtime:
    """Inject authoritative runtime receipts and observable lifecycle effects."""

    def __init__(self, results=(), fault=""):
        """
        Prepare a running resource and bounded result sequence.
        results: Command results emitted by exec.
        fault: Deliberately corrupt or fail one runtime boundary.
        """
        self.results = deque(results)
        self.fault = fault
        self.status = "running"
        self.calls = []
        self.executions = []
        self.stops = 0
        self.starts = 0
        self.resource_id = CID
        self.on_start = None
        self.bindings = []

    def __call__(self, argv, **kwargs):
        """
        Simulate the external Docker-compatible CLI contract.
        argv: Exact runtime argument vector.
        Returns: An injected command or authoritative lifecycle receipt.
        """
        self.calls.append(list(argv))
        operation = argv[1]
        if operation == "inspect":
            if self.status == "absent":
                return CommandResult(exit_code=1, stderr="Error: No such object: " + NAME)
            if "--format" in argv:
                if "io.ddp.adore.git-binding" in argv[argv.index("--format") + 1]:
                    return CommandResult(stdout="null")
                return CommandResult(stdout=self.status)
            after = bool(self.executions)
            if self.fault == "before-corrupt" or (after and self.fault == "after-corrupt"):
                return CommandResult(stdout="{corrupt")
            resource = "c" * 64 if (
                self.fault == "before-id" or after and self.fault == "after-id"
                or self.stops and self.fault == "stopped-id"
            ) else self.resource_id
            image = "sha256:" + "d" * 64 if (
                self.fault == "before-image" or after and self.fault == "after-image"
            ) else IMAGE
            return CommandResult(stdout=json.dumps([{
                "Id": resource, "Image": image, "Name": "/" + NAME,
                "State": {"Status": self.status}, "Mounts": self.bindings,
            }]))
        if operation == "exec":
            self.executions.append(list(argv))
            return self.results.popleft() if self.results else CommandResult(stdout="next")
        if operation == "stop":
            self.stops += 1
            if self.fault == "stop-failed":
                return CommandResult(exit_code=1, stderr="denied")
            if self.fault != "stop-noop":
                self.status = "exited"
            return CommandResult(stdout="stop receipt, not executor output")
        if operation == "start":
            self.starts += 1
            if self.on_start is not None:
                self.on_start()
            if self.fault == "start-failed":
                return CommandResult(exit_code=1, stderr="unavailable")
            if self.fault != "start-noop":
                self.status = "running"
            return CommandResult(stdout="start receipt, not executor output")
        if operation == "volume":
            return CommandResult()
        if operation == "rm":
            if self.fault != "rm-noop":
                self.status = "absent"
            return CommandResult()
        raise AssertionError("unexpected runtime operation: " + repr(argv))


def bound(runtime, pinned=True):
    """
    Bind the public backend to one existing injected resource.
    runtime: Runtime CLI double.
    pinned: Supply durable identity pins or exercise legacy admission.
    Returns: Backend, bound target and declared expected identity.
    """
    manager = ContainerManager("docker", "image", "uv", "npm", runtime)
    backend = ContainerBackend(manager)
    expected = {"container_id": CID, "image_id": IMAGE} if pinned else None
    return backend, backend.bind(NAME, {}, expected), expected


# PUBLIC API / TESTS

@pytest.mark.parametrize("pinned", [True, False])
def test_timeout_parks_then_resumes_the_original_container(pinned):
    """
    A timeout settles writers and a later command resumes the same resource.
    pinned: Exercise durable pins and legacy invocation ownership.
    """
    original = CommandResult(exit_code=124, timed_out=True, stdout="original-out",
                             stderr="original-error")
    runtime = Runtime([original, CommandResult(stdout="next")])
    backend, target, _expected = bound(runtime, pinned)
    result = target(["work"], timeout=5)
    assert asdict(result) == asdict(original)
    assert backend.resource_identity(NAME)["status"] == "exited"
    assert runtime.stops == 1 and runtime.starts == 0
    assert target(["next"], timeout=5).stdout == "next"
    observed = backend.resource_identity(NAME)
    assert observed["container_id"] == CID and observed["image_id"] == IMAGE
    assert observed["status"] == "running"
    assert runtime.starts == 1
    for call in runtime.calls:
        if call[1] in {"stop", "start", "exec"}:
            assert CID in call


@pytest.mark.parametrize("pinned", [True, False])
def test_bound_commands_address_the_admitted_immutable_id(pinned):
    """
    Runtime name replacement cannot redirect admitted command dispatch.
    pinned: Exercise both supported identity admission modes.
    """
    runtime = Runtime()
    _backend, target, _expected = bound(runtime, pinned)
    assert target(["echo", "hello"]).ok
    assert CID in runtime.executions[0]
    assert NAME not in runtime.executions[0]


def test_normal_provision_resumes_a_confirmed_timeout_resource(tmp_path):
    """
    Ordinary provisioning retains owned timeout state and the same ID.
    tmp_path: Existing host mount roots for the injected container.
    """
    runtime = Runtime([CommandResult(exit_code=124, timed_out=True)])
    backend, target, _expected = bound(runtime)
    assert target(["work"]).timed_out
    runtime.bindings = [{"Type": "bind", "Destination": destination,
                         "Source": str(path).replace("\\", "/")}
                        for destination, path in [("/adore/repo/.git", tmp_path / ".git"),
                                                  ("/adore/work", tmp_path),
                                                  ("/adore/io", tmp_path / "io")]]
    assert backend.provision(NAME, tmp_path, tmp_path, tmp_path / "io", {}) == "started"
    assert runtime.stops == runtime.starts == 1
    assert target(["next"]).ok


@pytest.mark.parametrize("expected", [
    {"kind": "local", "container_id": CID, "image_id": IMAGE},
    {"container_id": CID},
    {"container_id": "c" * 64, "image_id": IMAGE},
    {"container_id": CID, "image_id": "sha256:" + "d" * 64},
])
def test_changed_caller_pins_cannot_restart_pending_recovery(expected):
    """
    Corrupt or changed caller ownership is rejected before restart.
    expected: Changed identity presented after a confirmed timeout.
    """
    runtime = Runtime([CommandResult(exit_code=124, timed_out=True)])
    backend, target, _expected = bound(runtime)
    assert target(["work"]).timed_out
    with pytest.raises(ExecutionRecoveryError):
        backend.bind(NAME, {}, expected)(["later"])
    assert runtime.starts == 0 and len(runtime.executions) == 1


@pytest.mark.parametrize("exit_code", [0, 1, 124])
def test_ordinary_exits_do_not_trigger_timeout_recovery(exit_code):
    """
    Ordinary results preserve lifecycle even when exit124 is returned.
    exit_code: An ordinary executor exit without timeout evidence.
    """
    original = CommandResult(exit_code=exit_code, stdout="output", stderr="stderr")
    runtime = Runtime([original])
    _backend, target, _expected = bound(runtime)
    assert asdict(target(["work"])) == asdict(original)
    assert runtime.stops == runtime.starts == 0


@pytest.mark.parametrize("exit_code", [0, 124, 143])
def test_recovery_preserves_timeout_result_fields(exit_code):
    """
    Lifecycle receipts cannot replace original timeout or stream data.
    exit_code: Runtime-reported exit accompanying an actual timeout.
    """
    original = CommandResult(exit_code=exit_code, timed_out=True, stdout="out", stderr="err")
    runtime = Runtime([original])
    _backend, target, _expected = bound(runtime)
    assert asdict(target(["work"])) == asdict(original)
    assert runtime.stops == 1


@pytest.mark.parametrize("fault", [
    "after-id", "after-image", "after-corrupt", "stop-failed", "stop-noop", "stopped-id",
])
def test_unconfirmed_timeout_cleanup_blocks_later_bound_execution(fault):
    """
    Unsafe runtime evidence cannot admit a new command or a replacement.
    fault: Corrupt ownership, interruption or stopped-state evidence.
    """
    runtime = Runtime([CommandResult(exit_code=124, timed_out=True)], fault)
    backend, target, expected = bound(runtime)
    with pytest.raises(ExecutionRecoveryError):
        target(["work"])
    before = len(runtime.executions)
    with pytest.raises(ExecutionRecoveryError):
        backend.bind(NAME, {}, expected)(["later"])
    assert len(runtime.executions) == before == 1
    assert runtime.starts == 0
    for call in runtime.calls:
        if call[1] == "stop":
            assert call[-1] == CID


@pytest.mark.parametrize("fault", ["start-failed", "start-noop"])
def test_unconfirmed_restart_blocks_the_next_executor(fault):
    """
    Pending restart requires confirmed running identity before dispatch.
    fault: Failed or contradictory restart receipt.
    """
    runtime = Runtime([CommandResult(exit_code=124, timed_out=True)], fault)
    backend, target, expected = bound(runtime)
    assert target(["work"]).timed_out
    with pytest.raises(ExecutionRecoveryError):
        target(["later"])
    with pytest.raises(ExecutionRecoveryError):
        backend.bind(NAME, {}, expected)(["again"])
    assert len(runtime.executions) == 1


@pytest.mark.parametrize("fault", ["before-id", "before-image", "before-corrupt"])
def test_untrusted_initial_identity_dispatches_no_command(fault):
    """
    Existing identity trust boundaries remain closed before execution.
    fault: Invalid or contradictory initial external identity.
    """
    runtime = Runtime(fault=fault)
    _backend, target, _expected = bound(runtime)
    with pytest.raises(IsolationError):
        target(["work"])
    runtime.fault = ""
    with pytest.raises(ExecutionRecoveryError):
        target(["later"])
    assert runtime.executions == []
    assert runtime.starts == runtime.stops == 0


@pytest.mark.parametrize("control", ["stop", "interrupt"])
def test_operator_stop_cancels_pending_automatic_restart(control):
    """
    Explicit lifecycle control retains authority over a pending resume.
    control: Operator-owned parking or cancellation action.
    """
    runtime = Runtime([CommandResult(exit_code=124, timed_out=True)])
    backend, target, expected = bound(runtime)
    assert target(["work"]).timed_out
    getattr(backend, control)(NAME, expected=expected)
    with pytest.raises(ExecutionRecoveryError):
        target(["later"])
    assert runtime.starts == 0 and len(runtime.executions) == 1


def test_failed_admission_stays_blocked_until_operator_uses_a_fresh_backend():
    """Explicit release cannot silently reopen failed active admission."""
    runtime = Runtime([CommandResult(exit_code=124, timed_out=True)], "stop-failed")
    backend, target, expected = bound(runtime)
    with pytest.raises(ExecutionRecoveryError):
        target(["work"])
    runtime.fault = ""
    backend.remove(NAME, expected=expected)
    # Model a separately authorized recreation, never automatic replacement.
    runtime.resource_id = "c" * 64
    runtime.status = "running"
    fresh = {"container_id": runtime.resource_id, "image_id": IMAGE}
    with pytest.raises(ExecutionRecoveryError):
        backend.bind(NAME, {}, fresh)(["recreated"])
    assert len(runtime.executions) == 1
    assert ContainerBackend(backend.manager).bind(NAME, {}, fresh)(["recreated"]).ok


def test_operator_interrupt_during_restart_prevents_executor_dispatch():
    """Cancellation arriving during deferred restart remains authoritative."""
    runtime = Runtime([CommandResult(exit_code=124, timed_out=True)])
    backend, target, expected = bound(runtime)
    assert target(["work"]).timed_out
    runtime.on_start = lambda: backend.interrupt(NAME, expected=expected)
    with pytest.raises(ExecutionRecoveryError):
        target(["later"])
    assert len(runtime.executions) == 1
    assert backend.resource_identity(NAME)["status"] == "exited"


@pytest.mark.parametrize("cancel", [False, True])
def test_unconfirmed_recovery_is_terminal_without_another_executor_attempt(
    tmp_path, monkeypatch, cancel,
):
    """
    Failed recovery persists an infrastructure failure instead of retrying.
    tmp_path: Isolated state store.
    monkeypatch: Inject the offline AEGIS transport.
    cancel: Give a concurrent operator cancellation precedence.
    """
    class Executor(FakeExecutor):
        """Report an unconfirmed owned-resource recovery."""

        def run_gate(self, *args, **kwargs):
            """Record the launch and reject unsafe recovery."""
            self.prompts.append("attempt")
            if cancel:
                engine.store.request_cancel(run.run_id)
            raise ExecutionRecoveryError("container interruption unconfirmed")

    class Client(FakeAegis):
        """Keep the current build journal at the public client seam."""

        def __init__(self, *args):
            super().__init__([task("build")])

        def probe(self):
            """Accept the injected protocol without invoking a CLI."""
            return SimpleNamespace(version="0.5.0", schema=1)

    monkeypatch.setattr(orchestrator_module, "AegisClient", Client)
    executor = Executor()
    engine, _forge, _worktrees, _containers, _executor = make_engine(tmp_path, executor=executor)
    run = make_run(engine)
    run.stage = "build"
    run.lifecycle = "failed"
    engine.store.save(run)
    assert engine.retry(run.run_id)
    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == ("cancelled" if cancel else "failed")
    if not cancel:
        assert saved.outcome.startswith("INFRASTRUCTURE_EXHAUSTED:")
    assert len(executor.prompts) == 1


@pytest.mark.parametrize("unsafe", [False, True])
def test_pi_rpc_timeout_settles_container_before_next_gate(tmp_path, monkeypatch, unsafe):
    """RPC timeout parks all container writers and refuses unconfirmed recovery."""
    from adore.executor import pi_rpc
    from adore.executor.launcher import PiExecutor

    runtime = Runtime(fault="stop-noop" if unsafe else "")
    backend, target, _ = bound(runtime, True)
    backend.manager.spawn = lambda *a, **k: object()
    def timeout(spawn, argv, env, *args, **kwargs):
        spawn(argv, env)
        return pi_rpc.PiRpcResult(outcome="timed-out", exit_code=124, timed_out=True)

    monkeypatch.setattr(pi_rpc, "run_pi_rpc", timeout)
    executor = PiExecutor("m")
    if unsafe:
        with pytest.raises(ExecutionRecoveryError, match="interruption unconfirmed"):
            executor.run_gate(target, tmp_path, tmp_path / "io", "prepare")
        with pytest.raises(ExecutionRecoveryError):
            target.spawn(["pi"])
    else:
        assert executor.run_gate(target, tmp_path, tmp_path / "io", "prepare").timed_out
        assert runtime.stops == 1 and runtime.status == "exited"
        observed = []
        backend.manager.spawn = lambda name, argv, **kwargs: observed.append(name)
        target.spawn(["pi"])
        assert runtime.starts == 1 and observed == [CID]


def test_rpc_timeout_does_not_interrupt_a_replacement_after_unpinned_spawn():
    """The admitted streaming invocation remains the authority without durable pins."""
    runtime = Runtime()
    backend, target, _ = bound(runtime, False)
    backend.manager.spawn = lambda *a, **k: object()
    target.spawn(["pi"])
    runtime.resource_id = "c" * 64
    with pytest.raises(ExecutionRecoveryError):
        target.settle_timeout()
    assert runtime.stops == 0
