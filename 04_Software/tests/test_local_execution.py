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
@file    test_local_execution.py
@brief   Native local configuration, ownership, transport and account contracts.
@details Injects every process/CLI boundary; no model, container or real CLI runs.
"""

# IMPORTS
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import subprocess
import sys

from adore import execution
from adore.config import default_config, validate_config
from adore.local_execution import LocalBackend, local_environment
from adore.local_process import (
    LocalExecutionError,
    LocalProcessController,
    NativeScopes,
    atomic_record,
)
from adore.preparation import resolve_plan, validate_plan
from adore.util import CommandResult
import pytest

# LOCAL HELPERS


def local_fixture(tmp_path, monkeypatch):
    """@brief Select an injected installed native CLI and account without host calls."""
    home, work, tools = [tmp_path / name for name in ("home", "work", "tools")]
    for directory in (home, work, tools):
        directory.mkdir()
    from adore import pi_installation as managed

    from tests.test_pi_installation import fake_node, write_fake_packages

    executable = fake_node(tmp_path, monkeypatch)
    pi = managed.ManagedPi(executable, managed.adore_home() / "tools/pi" / managed.PI_VERSION)
    write_fake_packages(pi)
    monkeypatch.setattr(managed, "run_command", lambda argv, **_: CommandResult(
        stdout="v22.23.4" if len(argv) == 2 else managed.PI_VERSION))
    for command in ("git", "python", "pi"):
        (tools / (command + ".exe")).touch()
        (tools / command).touch()
        (tools / command).chmod(0o755)
    config = default_config()
    config.execution.backend = "local"
    config.platform.repo = "owner/repo"
    config.worktree.repo_path = str(work)
    config.state.store_root = str(tmp_path / "state")
    config.delivery.reviewers = ["reviewer"]
    config.executor.provider = "openai"
    config.executor.model = "model"
    config.executor.env_keys = ["OPENAI_API_KEY"]
    context = {
        "system": "Windows",
        "account": "execution-user",
        "host": "a" * 64,
        "machine": "execution-machine",
        "home": str(home),
        "path": str(tools),
    }
    monkeypatch.setattr("adore.local_execution.native_context", lambda: context)
    monkeypatch.setattr("adore.local_execution.NativeScopes", lambda *_args: None)

    class Controller:
        """@brief Injected native command boundary records environment and redaction."""

        calls = []
        controlled = []
        streams = []
        rpc_options = ()

        @contextmanager
        def stream(self, argv, *, cwd, env, **kwargs):
            self.streams.append((argv, cwd, env))
            fixture = Path(__file__).parent / "fixtures/pi_rpc/run_connection_test_endpoint.jsonl"
            command = [sys.executable, "-I", str(Path(__file__).with_name("fake_pi_rpc.py")),
                       str(fixture), *self.rpc_options]
            with subprocess.Popen(  # noqa: S603 - repository-owned offline fake
                command, cwd=cwd, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ) as process:
                yield process

        def run_files(self, argv, **kwargs):
            self.calls.append((argv, kwargs))
            text = "1.2.3" if "--version" in argv else '{"type":"result","value":"ok"}'
            kwargs["stdout"].write_text(text, encoding="utf-8")
            kwargs["stderr"].write_text("", encoding="utf-8")
            return CommandResult(argv=[argv[0], "[native-file-launch]"])

        def interrupt(self, *args):
            self.controlled.append(args)

        def recover(self, *args):
            self.controlled.append(args)

    controller = Controller()
    backend = LocalBackend(config, context=context, controller=controller)
    return config, context, backend, controller, work


# PUBLIC API / TESTS


def test_local_selection_is_explicit_and_rejects_container_contracts(tmp_path):
    """@brief Explicit local mode retains defaults and fails closed on conflicts."""
    config = default_config()
    config.platform.repo = "owner/repo"
    config.worktree.repo_path = str(tmp_path)
    config.executor.provider = "openai"
    config.executor.model = "model"
    config.delivery.reviewers = ["reviewer"]
    assert config.execution.backend == "container"
    config.execution.backend = "local"
    assert validate_config(config) == []
    assert config.local.account == "current"
    for field, value in [("preparation", "prepare.yml#setup@" + "a" * 40)]:
        setattr(config.execution, field, value)
        assert any("local" in issue for issue in validate_config(config))
        setattr(config.execution, field, "")
    config.container.egress.allowlist = ["pypi.org"]
    assert any("local" in issue for issue in validate_config(config))
    config.container.egress.allowlist = []
    assert validate_config(config) == []


@pytest.mark.parametrize("system", ["Windows", "Linux"])
@pytest.mark.parametrize("outcome", ["pass", "fail", "timeout"])
def test_native_direct_verification_uses_only_owned_platform_shell(
    tmp_path, monkeypatch, system, outcome,
):
    """@brief Only the exact configured command gets owned native shell authority."""
    config, context, _, controller, work = local_fixture(tmp_path, monkeypatch)
    context["system"] = system
    root = tmp_path / "Windows"
    shell = root / "System32/cmd.exe"
    shell.parent.mkdir(parents=True)
    shell.touch()
    monkeypatch.setenv("SystemRoot", str(root))
    monkeypatch.setenv("COMSPEC", str(work / "untrusted.exe"))
    command = 'echo "${value} {x} café" && test -f feature.txt'
    config.workflow.verify_command = command
    backend = LocalBackend(config, context=context, controller=controller)
    exchange = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, exchange, {"OPENAI_API_KEY": "provider-secret"})
    target = backend.bind("run-1", {"OPENAI_API_KEY": "provider-secret"})

    def execute(argv, **kwargs):
        """@brief Inject actual exit/timeout and output at the owned controller boundary."""
        controller.calls.append((argv, kwargs))
        kwargs["stdout"].write_text("café provider-secret")
        kwargs["stderr"].write_text("failure" if outcome == "fail" else "")
        return CommandResult(
            exit_code=7 if outcome == "fail" else 124 if outcome == "timeout" else 0,
            timed_out=outcome == "timeout",
        )

    controller.run_files = execute
    result = target.run_verification(command, timeout=17)
    argv, options = controller.calls[-1]
    expected = [str(shell.resolve()), "/d", "/s", "/c", command] if system == "Windows" else [
        str(Path("/bin/sh").resolve()), "-c", command,
    ]
    assert argv == expected
    assert options["cwd"] == work and options["timeout"] == 17
    assert options["env"] == target.env and options["capture_tail"] is True
    assert options["windows_verification"] == (system == "Windows")
    assert options["run_id"] == target.resource["id"] and options["host"] == context["host"]
    assert "provider-secret" not in result.stdout and "café" in result.stdout
    assert result.timed_out == (outcome == "timeout")
    assert result.exit_code == (7 if outcome == "fail" else 124 if outcome == "timeout" else 0)
    before = len(controller.calls)
    for forbidden in ["sh", "bash", "cmd.exe", "powershell.exe", "script.cmd"]:
        with pytest.raises(LocalExecutionError):
            target([forbidden, "-c", command], timeout=17)
    for invalid in [None, 1, True, [], "", command + "x", "test\nnext", "test\r", "test\x00"]:
        with pytest.raises(LocalExecutionError):
            target.run_verification(invalid, timeout=17)
    assert len(controller.calls) == before
    context["host"] = "b" * 64
    with pytest.raises(LocalExecutionError):
        target.run_verification(command, timeout=17)
    assert len(controller.calls) == before


@pytest.mark.parametrize("command", [
    r'"C:\Program Files\Project Tools\verify.exe" "argument with spaces"',
    r'echo "nested quotes" && echo %PROJECT_NAME% | findstr "text" > "result file.txt"',
    'echo café & echo "C:\\trailing path\\\\"',
    "echo plain",
])
@pytest.mark.parametrize("outcome", ["pass", "fail", "timeout", "cleanup"])
def test_native_windows_verification_preserves_command_at_child_boundary(
    tmp_path, monkeypatch, command, outcome,
):
    """@brief Owned cmd launch preserves shell text instead of applying C argv escaping."""
    from types import SimpleNamespace

    from adore import local_child

    config, context, _, _, work = local_fixture(tmp_path, monkeypatch)
    root = tmp_path / "Windows with spaces"
    shell = root / "System32/cmd.exe"
    shell.parent.mkdir(parents=True)
    shell.touch()
    monkeypatch.setenv("SystemRoot", str(root))
    config.workflow.verify_command = command
    jobs = Jobs()
    scopes = NativeScopes("Windows", windows=jobs)
    calls, envelopes = [], []

    def launch(command_line, **kwargs):
        """@brief Capture the exact CreateProcess input without invoking a Windows shell."""
        assert Path(envelopes[-1]["release"]).is_file()
        calls.append((command_line, kwargs))
        return SimpleNamespace(returncode=7 if outcome == "fail" else 0)

    class Process:
        """@brief Run the real trusted helper only after the controller's durable release."""

        pid = 42
        stdout = io.BytesIO(b"verification output")
        stderr = io.BytesIO(b"verification error" if outcome == "fail" else b"")
        waits = 0

        def wait(self, timeout):
            self.waits += 1
            if self.waits == 1:
                code = local_child.main(str(envelope_path))
                if outcome == "timeout":
                    raise subprocess.TimeoutExpired("injected", timeout)
                jobs.birth_value = None
                return code
            return 0

    envelope_path = None

    def spawn(argv, **kwargs):
        """@brief Exercise the parent envelope and child transport with an offline Job."""
        nonlocal envelope_path
        envelope_path = Path(argv[3])
        envelopes.append(json.loads(envelope_path.read_text()))
        assert not Path(envelopes[-1]["release"]).exists()
        return Process()

    controller = LocalProcessController(scopes, spawn=spawn)
    backend = LocalBackend(config, context=context, controller=controller)
    exchange = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, exchange, {})
    target = backend.bind("run-1", {})
    monkeypatch.setattr(local_child.subprocess, "run", launch)
    if outcome == "cleanup":
        scopes.remove = lambda *_: (_ for _ in ()).throw(LocalExecutionError("cleanup refused"))
        with pytest.raises(LocalExecutionError, match="cleanup refused"):
            target.run_verification(command, timeout=17)
    else:
        result = target.run_verification(command, timeout=17)
        assert result.exit_code == (7 if outcome == "fail" else 124 if outcome == "timeout" else 0)
        assert result.timed_out == (outcome == "timeout")
        assert result.stdout == "verification output"
        assert jobs.killed and jobs.removed
    command_line, options = calls[0]
    assert isinstance(command_line, str), "verification still uses C argv serialization"
    assert envelopes[-1]["windows_verification"] is True
    # Only the executable uses C-runtime quoting. cmd /s strips exactly the
    # extra outer pair around the original shell text; no backslash escaping.
    expected = subprocess.list2cmdline([str(shell.resolve())]) + f' /d /s /c "{command}"'
    assert command_line == expected
    assert options["executable"] == str(shell.resolve())
    assert options["cwd"] == str(work) and options["creationflags"] == 0x08000000
    assert options["stdin"] == subprocess.DEVNULL
    assert options["stdout"] is sys.stdout and options["stderr"] is sys.stderr
    assert options.get("shell", False) is False
    assert (envelope_path.parents[2] / "active-process.json").exists() == (outcome == "cleanup")


def test_local_backend_is_available_through_the_shared_contract():
    """@brief Local selection has an adapter on the established backend boundary."""
    assert hasattr(execution, "LocalBackend"), "local backend adapter is absent"


def test_local_environment_ignores_personal_auth_and_forge_credentials(tmp_path, monkeypatch):
    """@brief Only approved project credentials enter the native environment."""
    config, context, backend, controller, work = local_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("GITHUB_TOKEN", "forge-secret")
    monkeypatch.setenv("UNAPPROVED_SECRET", "unapproved")
    env = local_environment(config, context, {"OPENAI_API_KEY": "provider-secret"})
    assert "GITHUB_TOKEN" not in env and "UNAPPROVED_SECRET" not in env
    assert env["HOME"] == context["home"] and env["OPENAI_API_KEY"] == "provider-secret"
    auth = Path(context["home"]) / ".pi/agent/auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text('{"provider":{"refresh":"existing-subscription-secret"}}')
    io_dir = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, io_dir, env)
    resource = backend.resource_identity("run-1")
    target = backend.bind("run-1", env, resource)
    assert target(["pi", "--version"], timeout=1).ok
    assert controller.calls[0][1]["env"]["GIT_PAGER"] == "cat"
    assert controller.calls[0][1]["secrets"] == ["provider-secret"]
    assert auth.read_text() == '{"provider":{"refresh":"existing-subscription-secret"}}'
    assert not any(
        "existing-subscription-secret" in p.read_text() for p in io_dir.parent.rglob("*.json")
    )
    config.local.account = "another-account"
    with pytest.raises(LocalExecutionError):
        local_environment(config, context)


@pytest.mark.parametrize("system", ["Windows", "Linux"])
def test_native_python_utf8_overrides_ambient_encoding(tmp_path, monkeypatch, system):
    """@brief Native Python uses UTF-8 without accepting ambient Python settings."""
    config, context, *_ = local_fixture(tmp_path, monkeypatch)
    context["system"] = system
    monkeypatch.setenv("PYTHONUTF8", "0")
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252:replace")
    monkeypatch.setenv("PYTHONPATH", "untrusted-python")
    supplied = {"PYTHONUTF8": "0", "PYTHONIOENCODING": "ascii"}
    env = local_environment(config, context, supplied)
    assert "PYTHONUTF8" not in env
    assert env["PYTHONIOENCODING"] == "utf-8"
    assert "PYTHONPATH" not in env
    assert supplied == {"PYTHONUTF8": "0", "PYTHONIOENCODING": "ascii"}
    assert os.environ["PYTHONUTF8"] == "0"
    assert os.environ["PYTHONIOENCODING"] == "cp1252:replace"


@pytest.mark.parametrize("system", ["Windows", "Linux"])
def test_native_unicode_python_evidence_survives_capture(tmp_path, monkeypatch, system):
    """@brief A bound native command retains non-ASCII JSON from a Python producer."""
    config, context, backend, controller, work = local_fixture(tmp_path, monkeypatch)
    context["system"] = system
    backend = LocalBackend(config, context=context, controller=controller)
    payload = '{"reply":"café — răspuns 日本語"}'

    def python_output(argv, **kwargs):
        """@brief Simulate the producer's stream encoding at the command boundary."""
        encoding = kwargs["env"].get("PYTHONIOENCODING", "cp1252")
        kwargs["stdout"].write_bytes(payload.encode(encoding, errors="replace"))
        kwargs["stderr"].write_bytes(b"")
        return CommandResult(argv=list(argv))

    monkeypatch.setattr(controller, "run_files", python_output)
    backend.provision("run-1", work, work, Path(config.state.store_root) / "runs/run-1/io", {})
    python = Path(context["path"]) / ("python.exe" if system == "Windows" else "python")
    result = backend.bind("run-1", {})([str(python), "unicode-json"], timeout=1)
    assert result.ok and result.stdout == payload


def test_local_environment_keeps_windows_system_names(tmp_path, monkeypatch):
    """@brief Windows machine/system names reach native commands; account names do not."""
    config, context, *_ = local_fixture(tmp_path, monkeypatch)
    system = {
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "PROCESSOR_ARCHITECTURE": "AMD64",
        "SystemDrive": "C:",
        "ProgramData": "C:\\ProgramData",
        "ProgramFiles(x86)": "C:\\Program Files (x86)",
    }
    excluded = {
        "HOMEDRIVE": "C:",
        "HOMEPATH": "\\Users\\someone",
        "COMPUTERNAME": "MACHINE",
        "GITEA_TOKEN": "forge-secret",
    }
    for key, value in {**system, **excluded}.items():
        monkeypatch.setenv(key, value)
    env = {key.upper(): value for key, value in local_environment(config, context).items()}
    assert all(env.get(key.upper()) == value for key, value in system.items())
    assert not any(key.upper() in env for key in excluded)
    linux = {key.upper() for key in local_environment(config, {**context, "system": "Linux"})}
    assert not any(key.upper() in linux for key in system)


@pytest.mark.parametrize("change", ["policy", "resource", "executable"])
def test_local_identity_and_auth_fail_closed_before_native_commands(tmp_path, monkeypatch, change):
    """@brief Drift and corrupt runtime input cannot authorize native commands."""
    config, context, backend, controller, work = local_fixture(tmp_path, monkeypatch)
    io_dir = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, io_dir, {})
    target = backend.bind("run-1", backend.environment)
    if change == "policy":
        config.local.path = str(work)
    elif change == "resource":
        (io_dir.parent / "local-control/runtime.json").write_text("{}")
    elif change == "executable":
        Path(backend.policy["executable"]).write_bytes(b"replaced")
    with pytest.raises(LocalExecutionError):
        target(["pi", "--version"], timeout=1)
    assert controller.calls == []


def test_local_plan_and_native_resource_roundtrip_are_closed(tmp_path, monkeypatch):
    """@brief Additive local state preserves its native identity and rejects corruption."""
    from adore.state import RunState, StateError

    config, _, backend, _, work = local_fixture(tmp_path, monkeypatch)
    plan = resolve_plan(config)
    assert plan["backend"] == "local" and plan["image"] == "" and plan["steps"] == []
    assert validate_plan(plan) == plan
    io_dir = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, io_dir, {})
    run = RunState(
        run_id="run-1",
        ticket_iid=1,
        execution={
            "plan": plan,
            "status": "not-required",
            "resource": backend.resource_identity("run-1"),
            "attempts": 0,
            "steps": [],
            "history": [],
            "reprepare": False,
        },
    )
    data = run.to_dict()
    assert RunState.from_dict(data).execution == run.execution
    data["execution"]["resource"]["pid"] = 7
    with pytest.raises(StateError):
        RunState.from_dict(data)


class Jobs:
    """@brief Injected Win32 scope/PID-birth boundary, never a real process."""

    def __init__(self):
        self.birth_value = "original-birth"
        self.killed = []
        self.removed = []

    def create(self, name):
        self.name = name

    def attach(self, name, pid):
        assert name == self.name and pid == 42

    def birth(self, pid):
        return self.birth_value

    def kill(self, name):
        self.killed.append(name)
        self.birth_value = None

    def remove(self, name):
        self.removed.append(name)


@pytest.mark.parametrize(
    "change", ["pid", "scope", "run", "duplicate", "control-failure", "other-job"]
)
def test_local_scope_control_refuses_reused_process_identity(tmp_path, change):
    """@brief Recovered controls fail closed at every persisted/native identity boundary."""
    jobs = Jobs()
    scopes = NativeScopes("Windows", windows=jobs)
    scope = scopes.create("b" * 32)
    lease = {
        "schema": 1,
        "run_id": "c" * 32,
        "host": "a" * 64,
        "pid": 42,
        "birth": "original-birth",
        "scope": scope,
    }
    atomic_record(tmp_path / "launches" / ("b" * 32) / "ownership.json", lease)
    if change == "pid":
        jobs.birth_value = "reused-birth"
    elif change == "scope":
        lease["scope"]["name"] = "unrelated-job"
    elif change == "other-job":
        lease["scope"]["name"] = "Local\\ADORE-" + "e" * 32
    elif change == "run":
        lease["run_id"] = "d" * 32
    elif change == "control-failure":

        def failed(_):
            raise LocalExecutionError("native control failed")

        jobs.kill = failed
    path = tmp_path / "active-process.json"
    atomic_record(path, lease)
    if change == "duplicate":
        path.write_text('{"schema":1,"schema":2}')
    with pytest.raises(LocalExecutionError):
        LocalProcessController(scopes).interrupt(tmp_path, "c" * 32, "a" * 64)
    assert jobs.killed == [] and path.exists()


@pytest.mark.parametrize("mode", ["success", "nonzero", "timeout", "bad-utf8", "cleanup",
                                  "split-known", "ansi-token", "spaced-marker", "long-known"])
def test_native_verification_capture_keeps_true_sanitized_tail(tmp_path, mode):
    """@brief Owned tail capture drains all bytes, masks split tokens and confirms cleanup."""
    jobs = Jobs()
    scopes = NativeScopes("Windows", windows=jobs)
    control = tmp_path / "control"
    # Credentials cross the 4096-byte drain boundary and the rolling eviction boundary.
    raw = (b"prefix\n" * 12000 + b"x" * 4090 + b"token=" + b"secret" * 15000
           + b"\nBearer " + b"credential" * 15000 + b"\n" + b" " * 4091
           + b"approved-secret\n" + "café end\n".encode())
    if mode == "bad-utf8":
        raw += b"\xff"
    if mode == "split-known":
        raw = b"x" * 4093 + b"approved-secret-long\n" + "café end\n".encode()
    elif mode == "ansi-token":
        raw = b"x" * 4093 + b"to\x1b[31mken=" + b"secret" * 15000 + b"\n"
        raw += b"approved-secret\n" + "café end\n".encode()
    elif mode == "spaced-marker":
        raw = b"authorization" + b" " * 80000 + b": Bearer hidden-value\n"
        raw += b"approved-secret\n" + "café end\n".encode()
    elif mode == "long-known":
        raw = b"x" * 4093 + b"K" * 10000 + b"\n" + "café end\n".encode()

    class Process:
        """@brief Offline supervisor exposing long streams after its durable release."""

        pid = 42
        stdout = io.BytesIO(raw)
        stderr = io.BytesIO(b"api_key=" + b"hidden" * 15000 + b"\nlast error")
        waits = 0

        def wait(self, timeout):
            assert list(control.glob("launches/*/release"))
            assert json.loads((control / "active-process.json").read_text())["pid"] == self.pid
            self.waits += 1
            if mode == "timeout" and self.waits == 1:
                raise subprocess.TimeoutExpired("injected", timeout)
            jobs.birth_value = None
            return 7 if mode == "nonzero" else 0

    process = Process()
    controller = LocalProcessController(scopes, spawn=lambda *args, **kwargs: process)
    if mode == "cleanup":
        scopes.remove = lambda *_: (_ for _ in ()).throw(LocalExecutionError("cleanup refused"))
    arguments = dict(cwd=tmp_path, env={}, timeout=1, stdout=tmp_path / "stdout",
                     stderr=tmp_path / "stderr", control=control, run_id="c" * 32,
                     host="a" * 64,
                     secrets=["approved-secret", "approved-secret-long", "K" * 10000],
                     capture_tail=True)
    if mode in {"bad-utf8", "cleanup"}:
        with pytest.raises(LocalExecutionError):
            controller.run_files(["platform-shell", "-c", "configured"], **arguments)
        assert (control / "active-process.json").exists()
    else:
        result = controller.run_files(["platform-shell", "-c", "configured"], **arguments)
        assert result.exit_code == (124 if mode == "timeout" else 7 if mode == "nonzero" else 0)
        assert result.timed_out == (mode == "timeout")
        text = arguments["stdout"].read_text()
        assert text.endswith("[REDACTED]\ncafé end\n") and len(text.encode()) <= 65536
        assert "secret" not in text and "credential" not in text and "approved" not in text
        assert "hidden-value" not in text and "-long" not in text and "K" not in text
        assert arguments["stderr"].read_text() == "api_key=[REDACTED]\nlast error"
        assert jobs.killed and jobs.removed and not (control / "active-process.json").exists()


@pytest.mark.parametrize("mode", ["success", "nonzero", "timeout"])
def test_native_launch_records_ownership_before_release_and_redacts(tmp_path, mode):
    """@brief The native process boundary retains truthful bounded outcomes and ownership."""
    jobs = Jobs()
    scopes = NativeScopes("Windows", windows=jobs)
    control = tmp_path / "control"

    class Process:
        """@brief Simulate only the trusted supervisor, with controlled completion."""

        pid = 42
        stdout = io.BytesIO(b"approved-secret " + b"x" * 70000)
        stderr = io.BytesIO(b"")
        waits = 0

        def wait(self, timeout):
            assert (
                json.loads((control / "active-process.json").read_text())["birth"]
                == "original-birth"
            )
            assert list((control / "launches").glob("*/release"))
            self.waits += 1
            if mode == "timeout" and self.waits == 1:
                raise subprocess.TimeoutExpired("injected", timeout)
            jobs.birth_value = None
            return 7 if mode == "nonzero" else 0

    process = Process()
    controller = LocalProcessController(scopes, spawn=lambda *args, **kwargs: process)
    stdout, stderr = tmp_path / "stdout", tmp_path / "stderr"
    result = controller.run_files(
        ["installed.exe", "space path"],
        cwd=tmp_path,
        env={"HOME": "selected"},
        timeout=1,
        stdout=stdout,
        stderr=stderr,
        control=control,
        run_id="c" * 32,
        host="a" * 64,
        secrets=["approved-secret"],
    )
    assert result.exit_code == (124 if mode == "timeout" else 7 if mode == "nonzero" else 0)
    assert result.timed_out == (mode == "timeout")
    assert len(stdout.read_bytes()) <= 65536 and "approved-secret" not in stdout.read_text()
    assert jobs.killed and jobs.removed and not (control / "active-process.json").exists()
    assert all("approved-secret" not in p.read_text() for p in control.rglob("*.json"))


@pytest.mark.parametrize("interrupted", [False, True])
def test_native_rpc_stream_is_owned_before_release_and_drained(tmp_path, interrupted):
    """@brief The real streaming controller uses binary pipes and a verified job lease."""
    jobs = Jobs()
    scopes = NativeScopes("Windows", windows=jobs)
    control = tmp_path / "control"

    class Process:
        pid = 42
        stdin = io.BytesIO()
        stdout = io.BytesIO(b'{"type":"agent_settled"}')
        stderr = io.BytesIO()

        def poll(self):
            return None if not jobs.killed else 0

        def wait(self, *, timeout):
            assert timeout <= 5 and jobs.killed
            return 0

    process = Process()

    def spawn(argv, **kwargs):
        assert argv[-1] == "rpc"
        assert kwargs["stdin"] == kwargs["stdout"] == kwargs["stderr"] == subprocess.PIPE
        assert not (control / "active-process.json").exists()
        assert not list(control.glob("launches/*/release"))
        return process

    controller = LocalProcessController(scopes, spawn=spawn)
    with controller.stream(["node.exe", "cli.js"], cwd=tmp_path, env={}, control=control,
                           run_id="a" * 32, host="b" * 64) as stream:
        lease = json.loads((control / "active-process.json").read_text())
        assert lease["pid"] == process.pid and lease["scope"]["name"] == jobs.name
        assert list(control.glob("launches/*/release"))
        assert stream.stdin is process.stdin and stream.stdout is process.stdout
        if interrupted:
            stream.terminate()
            assert jobs.killed and stream.poll() == 0
        assert (control / "active-process.json").exists()
    assert jobs.killed and jobs.removed == [jobs.name]
    assert not (control / "active-process.json").exists()


@pytest.mark.parametrize("system", ["Windows", "Linux"])
def test_native_gate_uses_managed_rpc_and_ignores_hostile_personal_pi(
    tmp_path, monkeypatch, system,
):
    """@brief The isolated Windows RPC launch uses only the managed Node and agent resources."""
    from adore.executor.launcher import PiExecutor
    from adore.pi_installation import GUARD, managed_pi

    config, context, _, controller, work = local_fixture(tmp_path, monkeypatch)
    context["system"] = system
    backend = LocalBackend(config, context=context, controller=controller)
    personal = Path(context["home"]) / ".pi/agent"
    (personal / "extensions").mkdir(parents=True)
    (personal / "extensions/evil.ts").write_text("throw new Error('must not load')")
    (personal / "settings.json").write_text('{"extensions":["extensions/evil.ts"]}')
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(personal))
    monkeypatch.setenv("NODE_OPTIONS", "--require=hostile.js")
    monkeypatch.setenv("GITEA_TOKEN", "forge-secret")
    exchange = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, exchange, {})
    target = backend.bind("run-1", {"OPENAI_API_KEY": "provider-secret"})
    (work / "questions.md").write_text("stale")
    agent_dirs = []
    original_stream = controller.stream

    @contextmanager
    def stream(argv, **kwargs):
        assert not (work / "questions.md").exists()
        env = kwargs["env"]
        agent = Path(env["PI_CODING_AGENT_DIR"])
        assert agent != personal and not list(agent.iterdir())
        assert env["PI_OFFLINE"] == "1" and env["PI_TELEMETRY"] == "0"
        assert not {"GITEA_TOKEN", "NODE_OPTIONS"}.intersection(env)
        agent_dirs.append(agent)
        (work / "questions.md").write_text("operator question: provider-secret")
        with original_stream(argv, **kwargs) as process:
            yield process

    controller.stream = stream
    pi = managed_pi()
    executor = PiExecutor("ignored", "model", "questions.md", provider="openai")
    assert executor.cancel_grace_seconds(target) is not None
    result = executor.run_gate(
        target, work, exchange,
        "Connection test. Run echo ADORE_TOOL_" + "a" * 32
        + ". Then reply with exactly: ADORE_OK_" + "b" * 32,
        timeout=5, archive_stem="native-build",
    )
    argv, _, _ = controller.streams[0]
    assert argv[:2] == [str(pi.node), str(pi.cli)]
    assert {"--no-approve", "--no-extensions", "--no-skills", "--no-prompt-templates",
            "--no-themes", "--no-mcp", str(GUARD)}.issubset(argv)
    assert ("read,powershell,edit,write" in argv) == (system == "Windows")
    assert not agent_dirs[0].exists()
    assert result.exit_code == 0 and result.tokens_in and result.tokens_out
    assert result.questions == "operator question: [REDACTED]"
    assert (Path(result.artifact_dirs[0]) / "meta.json").is_file()


def test_local_aegis_file_transport_uses_native_argv(tmp_path):
    """@brief Public AEGIS status uses the same native target without a shell."""
    from adore.aegis import AegisClient
    from adore.execution import ExecutionPaths

    from tests.test_aegis import TASK_ID, task_payload

    exchange = tmp_path / "exchange"
    calls = []

    class Target:
        """@brief Native AEGIS file boundary."""

        paths = ExecutionPaths(str(tmp_path), str(exchange), "")

        def __call__(self, argv, **kwargs):
            raise AssertionError("local AEGIS invoked shell transport")

        def run_files(self, argv, stdout, stderr, **kwargs):
            calls.append(argv)
            stdout.write_text(json.dumps(task_payload()))
            stderr.write_text("")
            return CommandResult()

    client = AegisClient(Target(), python_command="native-python", io_dir=exchange)
    assert client.task_status(TASK_ID).task_id == TASK_ID
    assert calls[0][0] == "native-python" and "status" in calls[0]


def test_local_conductor_pins_target_parks_retries_and_never_lists_containers(
    tmp_path, monkeypatch
):
    """@brief Public retry/cleanup keep native ownership and bypass every container boundary."""
    from types import SimpleNamespace

    from adore import orchestrator as module
    from adore.executor.base import GateRun

    from tests.test_orchestrator import FakeAegis, FakeExecutor, make_engine, make_run, task

    config, context, _, controller, work = local_fixture(tmp_path, monkeypatch)
    engine, _, trees, containers, executor = make_engine(
        tmp_path,
        executor=FakeExecutor(GateRun(exit_code=0, has_questions=True, questions="Question")),
    )
    # The pinned environment includes the state root, so bind the backend after moving it.
    config.state.store_root = str(engine.store.root)
    backend = LocalBackend(config, context=context, controller=controller)
    engine.config, engine.backend = config, backend
    config.platform.kind = "github"
    # This native retry scenario uses a worktree fake without remote transport.
    config.delivery.publish_checkpoints = False
    trees.repo_path = work
    trees.create = lambda *args: work
    containers.list_executors = lambda *args: pytest.fail("local container inventory")

    class Client(FakeAegis):
        """@brief Native retry is evaluated using offline AEGIS contract evidence."""

        def __init__(self, *args):
            super().__init__([task("frame")])

        def probe(self):
            return SimpleNamespace(version="0.5.0", schema=1)

        def create_task(self, *args):
            return "TASK-1234abcd"

    monkeypatch.setattr(module, "AegisClient", Client)
    run = make_run(engine)
    run.active_task_id, run.task_ids, run.lifecycle = None, [], "failed"
    engine.store.save(run)
    assert engine.retry(run.run_id)
    saved = engine.store.load(run.run_id)
    assert saved.lifecycle == "parked-clarification"
    assert saved.execution["resource"]["kind"] == "local"
    assert saved.execution["status"] == "not-required"
    saved.lifecycle = "failed"
    engine.store.save(saved)
    executor.results.append(GateRun(exit_code=0, has_questions=True, questions="Again"))
    assert engine.retry(run.run_id)
    assert engine.store.load(run.run_id).execution["resource"] == saved.execution["resource"]
    assert engine.cleanup()["containers_removed"] == []
    assert controller.controlled


def test_local_cleanup_failure_retains_worktree(tmp_path, monkeypatch):
    """@brief Unconfirmed native control never permits project-file removal."""
    from tests.test_orchestrator import make_engine, make_run

    config, _, backend, _, work = local_fixture(tmp_path, monkeypatch)
    engine, _, trees, _, _ = make_engine(tmp_path)
    engine.config, engine.backend = config, backend
    config.state.store_root = str(engine.store.root)
    trees.path_for = lambda *args: work
    trees.remove = lambda *args, **kwargs: pytest.fail("unsafe worktree removal")
    run = make_run(engine)
    run.lifecycle = "done"
    engine.store.save(run)
    assert engine.purge_resources()["worktrees_retained"] == [run.run_id]


def test_local_readiness_never_invokes_container_tools(tmp_path, monkeypatch):
    """@brief Explicit host checks use the configured installed CLI and current account."""
    from adore.web.app import _probe_setup

    config, _, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=readiness-provider-key\n")
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *args: controller)
    seen = []

    def runner(argv, **kwargs):
        seen.append(argv)
        assert not any(tool in argv for tool in ("docker", "podman", "wsl"))
        return CommandResult(
            argv=argv, stdout="git version 2.45.0" if argv[0] == "git" else "1.2.3"
        )

    result = _probe_setup(config, runner, env_file)
    assert result["checks"]["executor_cli"] is True
    assert result["local_probe"] == {"ready": True, "reason": "ready", "exit_code": 0}
    assert "model_endpoint" not in result["checks"]
    assert controller.calls and any("--version" in argv for argv, _ in controller.calls)
    assert controller.calls[0][1]["env"]["OPENAI_API_KEY"] == "readiness-provider-key"


@pytest.mark.parametrize("reason", ["node-missing", "node-incompatible", "pi-missing"])
def test_readiness_reports_managed_pi_prerequisite(tmp_path, monkeypatch, reason):
    """@brief Report the first closed prerequisite cause before running project tools."""
    from adore import pi_installation as managed
    from adore.local_execution import probe_local_executor

    config, _, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    pi = managed.managed_pi()
    if reason == "node-missing":
        monkeypatch.setenv("ADORE_NODE", str(tmp_path / "no-node"))
    elif reason == "node-incompatible":
        monkeypatch.setattr(managed, "run_command", lambda argv, **_: CommandResult(
            stdout="v22.10.0"))
    else:
        pi.cli.unlink()

    result = probe_local_executor(config)
    assert not result["ready"] and result["reason"] == reason
    assert not controller.calls and not controller.streams


@pytest.mark.parametrize("scenario", ["provider", "large", "keyless-endpoint"])
def test_local_model_challenge_uses_the_managed_rpc_installation(
    tmp_path, monkeypatch, scenario,
):
    """@brief The model connection probe sends the challenge through native RPC."""
    from adore.web.model_connection import probe_model_connection

    config, _, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *args: controller)
    if scenario == "large":
        controller.rpc_options = ("--pad-message-end", "300000", "--pad-last")
    elif scenario == "keyless-endpoint":
        config.executor.provider = "custom"
        config.executor.endpoint.base_url = "http://127.0.0.1:1234/v1"
        config.raw["executor"] = {"endpoint": {"base_url": config.executor.endpoint.base_url}}
        original = controller.stream

        @contextmanager
        def stream(argv, **kwargs):
            env = kwargs["env"]
            agent = Path(env["PI_CODING_AGENT_DIR"])
            model = json.loads((agent / "models.json").read_text())
            provider = model["providers"]["adore-endpoint"]
            assert provider["baseUrl"] == config.executor.endpoint.base_url
            assert provider["apiKey"] == "adore-no-key"
            with original(argv, **kwargs) as process:
                yield process

        controller.stream = stream
    config.executor.thinking = "off" if scenario == "keyless-endpoint" else "medium"
    env_file = tmp_path / ".env"
    if scenario == "keyless-endpoint":
        monkeypatch.delenv("ADORE_ENDPOINT_API_KEY", raising=False)
    else:
        env_file.write_text("OPENAI_API_KEY=fake-key\n")
    result = probe_model_connection(
        config, lambda *args, **kwargs: pytest.fail("container call"), env_file
    )
    assert result["ready"], result
    argv, _, env = controller.streams[0]
    assert argv[0].endswith("node.exe") and "--no-extensions" in argv
    assert argv[argv.index("--thinking") + 1] == config.executor.thinking
    if scenario != "keyless-endpoint":
        assert env["OPENAI_API_KEY"] == "fake-key"


def test_local_assisted_setup_and_portable_rules_keep_machine_identity_local(tmp_path, monkeypatch):
    """@brief Setup selects managed Pi without launching an installer."""
    import tomllib

    from adore.profiles import ProfileStore
    from adore.web.app import ProjectInput, _prepare_project
    from adore.wizard import ScriptedAsker, run_wizard

    from tests.test_wizard import _answers, _clone

    clone = _clone(tmp_path)
    store = ProfileStore(tmp_path / "profiles")
    answers = _answers(clone, execution_backend="local")
    out = []
    setup = run_wizard(
        store,
        name="native",
        asker=ScriptedAsker(answers),
        runner=lambda *a, **kw: pytest.fail("setup launched container/tool command"),
        out=out.append,
        prepare_only=True,
        os_key="windows",
    )
    document = tomllib.loads(setup.document)
    assert document["execution"]["backend"] == "local"
    assert document["executor"]["env_keys"] == []
    assert setup.metadata["runtime"] == "local"
    body = ProjectInput(
        name="web-native",
        kind="github",
        repo="owner/repo",
        repo_path=str(clone),
        reviewers="reviewer",
        execution_backend="local",
        image="",
    )
    preview, _ = _prepare_project(store, body)
    assert preview["structural_valid"], preview["issues"]
    assert preview["review"]["execution_backend"] == "local"
    assert "machine" in preview["review"]["local_execution"]


@pytest.mark.parametrize("field", ["recipe", "egress", "secret"])
def test_local_backend_refuses_unsafe_direct_profiles(tmp_path, monkeypatch, field):
    """@brief Direct adapter users cannot bypass closed local configuration before launch."""
    config, context, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    if field == "recipe":
        config.execution.preparation = "prepare.yml#setup@" + "a" * 40
    elif field == "egress":
        config.container.egress.allowlist = ["pypi.org"]
    else:
        config.executor.env_keys = ["NODE_OPTIONS"]
    with pytest.raises(LocalExecutionError):
        LocalBackend(config, context=context, controller=controller)
    assert controller.calls == []


def test_linux_control_checks_delegated_scope_identity_before_kill(tmp_path):
    """@brief Linux control uses the exact owned cgroup and refuses inode/scope drift."""
    root = tmp_path / "delegated"
    root.mkdir()
    (root / "cgroup.controllers").write_text("pids")
    leaf = root / ("adore-" + "c" * 32)
    leaf.mkdir()
    (leaf / "cgroup.kill").write_text("")
    scopes = NativeScopes("Linux", str(root), linux_base=root, birth_reader=lambda pid: "boot:123")
    detail = leaf.stat()
    scope = {
        "kind": "linux-cgroup",
        "path": str(leaf),
        "device": detail.st_dev,
        "inode": detail.st_ino,
    }
    control = tmp_path / "control"
    atomic_record(
        control / "active-process.json",
        {
            "schema": 1,
            "run_id": "a" * 32,
            "host": "b" * 64,
            "pid": 42,
            "birth": "boot:123",
            "scope": scope,
        },
    )
    atomic_record(
        control / "launches" / ("c" * 32) / "ownership.json",
        {
            "schema": 1,
            "run_id": "a" * 32,
            "host": "b" * 64,
            "pid": 42,
            "birth": "boot:123",
            "scope": scope,
        },
    )
    driver = LocalProcessController(scopes)
    driver.interrupt(control, "a" * 32, "b" * 64)
    assert (leaf / "cgroup.kill").read_text() == "1"
    (leaf / "cgroup.kill").write_text("")
    scope["inode"] += 1
    atomic_record(
        control / "active-process.json",
        {
            "schema": 1,
            "run_id": "a" * 32,
            "host": "b" * 64,
            "pid": 42,
            "birth": "boot:123",
            "scope": scope,
        },
    )
    with pytest.raises(LocalExecutionError):
        driver.interrupt(control, "a" * 32, "b" * 64)
    assert (leaf / "cgroup.kill").read_text() == ""
    with pytest.raises(LocalExecutionError):
        NativeScopes("Linux", str(tmp_path), linux_base=root)


def test_local_native_settings_accept_tools_path_and_refuse_launch_overrides(tmp_path, monkeypatch):
    """@brief Reviewed project PATH does not permit a different Pi launcher."""
    from hashlib import sha256

    from adore.web.app import ConfigEdit, HTTPException, _candidate_config_edit

    config, context, _, _, work = local_fixture(tmp_path, monkeypatch)
    path = tmp_path / "config.toml"
    text = (
        '[execution]\nbackend="local"\n[platform]\nrepo="owner/repo"\n'
        "[worktree]\nrepo_path=" + json.dumps(str(work)) + "\n"
        '[delivery]\nreviewers=["reviewer"]\n[executor]\nprovider="openai"\nmodel="model"\n'
    )
    path.write_text(text)
    command = json.dumps(str(Path(context["path"]) / "pi.exe")) + " -p {prompt}"
    body = ConfigEdit(
        key="local.path",
        value=context["path"],
        revision=sha256(path.read_bytes()).hexdigest(),
    )
    _, candidate = _candidate_config_edit(path, body)
    assert __import__("tomllib").loads(candidate)["local"]["path"] == context["path"]
    body.key, body.value = "executor.command", command
    with pytest.raises(HTTPException):
        _candidate_config_edit(path, body)


def test_local_portable_export_excludes_all_native_settings(tmp_path, monkeypatch):
    """@brief Portable packages retain only working rules from valid local profiles."""
    from adore.portable_settings import export_settings

    from tests.test_portable_settings import EXAMPLE

    raw = EXAMPLE.read_bytes().replace(b'backend = "container"', b'backend = "local"')
    # The annotated example leaves backend at its default; append an explicit declaration.
    if b'backend = "local"' not in raw:
        raw += b'\n[execution]\nbackend="local"\n'
    raw += b'\n[local]\naccount="current"\npath="/native-tools"\n'
    raw = __import__("re").sub(
        rb"required_tool_checks = \[.*?\]",
        b"required_tool_checks = []",
        raw,
        flags=__import__("re").S,
    )
    encoded = export_settings(raw)
    for value in (
        b"native-tools",
        b'"local"',
    ):
        assert value not in encoded


def test_local_node_entrypoint_drift_refuses_execution(tmp_path, monkeypatch):
    """@brief Explicit Windows npm entrypoints are pinned with the native executable."""
    from adore.pi_installation import managed_pi

    config, _, backend, _, work = local_fixture(tmp_path, monkeypatch)
    pi = managed_pi()
    node, script = pi.node, pi.cli
    exchange = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, exchange, {})
    target = backend.bind("run-1", backend.environment)
    assert target([str(node), str(script), "--version"]).ok
    script.write_text("replaced installed executor")
    with pytest.raises(LocalExecutionError):
        target([str(node), str(script), "--version"])


@pytest.mark.parametrize("operation", ["stop", "interrupt", "remove", "command"])
def test_container_adapter_refuses_local_identity_before_cli(operation):
    """@brief Backend drift cannot authorize any container CLI or native cleanup."""

    class Manager:
        def __getattr__(self, name):
            pytest.fail("container CLI crossed mismatched native identity")

    backend = execution.ContainerBackend(Manager())
    with pytest.raises(execution.ExecutionRecoveryError):
        if operation == "command":
            backend.bind("run", {}, {"kind": "local"})(["anything"])
        else:
            getattr(backend, operation)("run", expected={"kind": "local"})


@pytest.mark.parametrize("content", [b"\xff", b"x" * 65537], ids=["bad-utf8", "oversize"])
def test_local_output_refuses_corrupt_retained_evidence(tmp_path, monkeypatch, content):
    """@brief Native output must be bounded valid UTF-8 before evidence is returned."""
    config, _, backend, controller, work = local_fixture(tmp_path, monkeypatch)
    exchange = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, exchange, {})

    def corrupt(argv, **kwargs):
        kwargs["stdout"].write_bytes(content)
        kwargs["stderr"].write_bytes(b"")
        return CommandResult()

    controller.run_files = corrupt
    with pytest.raises(LocalExecutionError):
        backend.bind("run-1", backend.environment)(["pi", "--version"])


def test_container_cleanup_retains_persisted_native_worktree(tmp_path, monkeypatch):
    """@brief Restoring a container profile cannot release a native run's worktree."""
    from tests.test_orchestrator import make_engine, make_run

    config, context, _, controller, work = local_fixture(tmp_path, monkeypatch)
    engine, _, trees, _, _ = make_engine(tmp_path)
    # The pinned environment includes the state root, so bind the backend after moving it.
    config.state.store_root = str(engine.store.root)
    backend = LocalBackend(config, context=context, controller=controller)
    run = make_run(engine)
    backend.provision(run.container, work, work, engine._io_dir(run.run_id), {})
    run.execution = {
        "plan": resolve_plan(config),
        "status": "not-required",
        "resource": {},
        "attempts": 0,
        "steps": [],
        "history": [],
        "reprepare": False,
    }
    run.execution["resource"] = backend.resource_identity(run.container)
    run.lifecycle = "done"
    engine.store.save(run)
    trees.path_for = lambda *args: work
    trees.remove = lambda *args, **kwargs: pytest.fail(
        "native worktree deleted by container profile"
    )
    assert engine.purge_resources()["worktrees_retained"] == [run.run_id]
    assert engine.cleanup()["worktrees_removed"] == []
    with pytest.raises(execution.ExecutionRecoveryError):
        engine.cancel(run.run_id)


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("cancel", [False, True])
def test_local_child_release_barrier_and_cancel_are_native(
    tmp_path, monkeypatch, cancel, streaming,
):
    """@brief Trusted child starts argv only after release and honors pre-release cancellation."""
    from types import SimpleNamespace

    from adore import local_child

    envelope = tmp_path / "command.json"
    envelope.write_text(
        json.dumps(
            {
                "argv": ["native", "prompt with spaces"],
                "cwd": str(tmp_path),
                "release": str(tmp_path / "release"),
                "scope": {"kind": "windows-job", "name": "owned"},
            }
        )
    )
    (tmp_path / ("cancel" if cancel else "release")).touch()
    calls = []

    def launch(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(local_child.subprocess, "run", launch)
    assert local_child.main(str(envelope), streaming=streaming) == (125 if cancel else 7)
    assert bool(calls) is not cancel
    if calls:
        assert calls[0][0] == ["native", "prompt with spaces"]
        assert calls[0][1]["stdin"] == (sys.stdin if streaming else subprocess.DEVNULL)
        assert calls[0][1]["stdout"] is sys.stdout and calls[0][1]["stderr"] is sys.stderr
    envelope.write_text('{"unexpected":true}')
    with pytest.raises(ValueError):
        local_child.main(str(envelope))


@pytest.mark.parametrize("invalid", [
    "false", "nonboolean", "linux", "rpc", "switch", "missing-command", "other-shell",
    "relative-shell", "newline", "carriage-return", "nul", "empty",
])
def test_local_child_refuses_invalid_windows_verification_transport(tmp_path, monkeypatch, invalid):
    """@brief A malformed dedicated transport cannot release a project command."""
    from adore import local_child

    envelope = {
        "argv": [r"C:\Windows\System32\cmd.exe", "/d", "/s", "/c", "echo valid"],
        "cwd": str(tmp_path), "release": str(tmp_path / "release"),
        "scope": {"kind": "windows-job", "name": "owned"}, "windows_verification": True,
    }
    if invalid in {"false", "nonboolean"}:
        envelope["windows_verification"] = False if invalid == "false" else "true"
    elif invalid == "linux":
        envelope["scope"] = {"kind": "linux-cgroup", "path": str(tmp_path)}
    elif invalid == "switch":
        envelope["argv"][1] = "/k"
    elif invalid == "missing-command":
        envelope["argv"].pop()
    elif invalid == "other-shell":
        envelope["argv"][0] = r"C:\Windows\System32\powershell.exe"
    elif invalid == "relative-shell":
        envelope["argv"][0] = "cmd.exe"
    elif invalid in {"newline", "carriage-return", "nul", "empty"}:
        envelope["argv"][-1] = {
            "newline": "echo a\necho b", "carriage-return": "echo a\r", "nul": "echo a\x00",
            "empty": "",
        }[invalid]
    path = tmp_path / "command.json"
    path.write_text(json.dumps(envelope))
    (tmp_path / "release").touch()
    monkeypatch.setattr(local_child.subprocess, "run", lambda *_args, **_kwargs: pytest.fail(
        "invalid verification transport launched a process"))
    with pytest.raises(ValueError):
        local_child.main(str(path), streaming=invalid == "rpc")
    assert not (tmp_path / "cgroup.procs").exists()


def test_local_child_windows_verification_cancel_prevents_launch(tmp_path, monkeypatch):
    """@brief Cancellation still wins over release for the dedicated Windows command."""
    from adore import local_child

    envelope = {
        "argv": [r"C:\Windows\System32\cmd.exe", "/d", "/s", "/c", 'echo "valid"'],
        "cwd": str(tmp_path), "release": str(tmp_path / "release"),
        "scope": {"kind": "windows-job", "name": "owned"}, "windows_verification": True,
    }
    path = tmp_path / "command.json"
    path.write_text(json.dumps(envelope))
    (tmp_path / "cancel").touch()
    (tmp_path / "release").touch()
    monkeypatch.setattr(local_child.subprocess, "run", lambda *_args, **_kwargs: pytest.fail(
        "cancelled verification launched a process"))
    assert local_child.main(str(path)) == 125


@pytest.mark.parametrize("mode", ["nonboolean", "linux"])
def test_native_controller_refuses_invalid_windows_verification_mode(tmp_path, mode):
    """@brief Invalid transport selection fails before any scope or supervisor is created."""
    scopes = NativeScopes("Windows", windows=Jobs())
    if mode == "linux":
        scopes.system = "Linux"
    controller = LocalProcessController(scopes, spawn=lambda *_args, **_kwargs: pytest.fail(
        "invalid transport selection launched a supervisor"))
    with pytest.raises(LocalExecutionError, match="verification mode"):
        controller.run_files(
            [r"C:\Windows\System32\cmd.exe", "/d", "/s", "/c", "echo valid"],
            cwd=tmp_path, env={}, timeout=1, stdout=tmp_path / "stdout", stderr=tmp_path / "stderr",
            control=tmp_path / "control", run_id="c" * 32, host="a" * 64, secrets=[],
            windows_verification="true" if mode == "nonboolean" else True,
        )
    assert not (tmp_path / "control").exists()


@pytest.mark.parametrize("query_ok", [True, False])
def test_windows_job_removal_confirms_all_descendants(tmp_path, query_ok):
    """@brief Injected Win32 accounting controls drain confirmation, retaining handles on error."""
    from adore.local_process import WindowsJobs

    job = WindowsJobs.__new__(WindowsJobs)

    class Api:
        def QueryInformationJobObject(self, *args):
            return query_ok  # zero-initialized accounting means no remaining children

        def CloseHandle(self, handle):
            assert handle == 42
            return True

    job.api, job.handles = Api(), {"owned": 42}
    if query_ok:
        job.remove("owned")
        assert job.handles == {}
    else:
        with pytest.raises(LocalExecutionError):
            job.remove("owned")
        assert job.handles == {"owned": 42}


@pytest.mark.parametrize("events", ["populated 0\nfrozen 0\n", "populated nonsense\n"])
def test_linux_scope_removal_requires_closed_liveness(tmp_path, monkeypatch, events):
    """@brief Owned cgroup removal accepts empty evidence and refuses corrupt liveness."""
    root = tmp_path / "delegated"
    root.mkdir()
    (root / "cgroup.controllers").write_text("pids")
    leaf = root / ("adore-" + "c" * 32)
    leaf.mkdir()
    (leaf / "cgroup.events").write_text(events)
    scopes = NativeScopes("Linux", str(root), linux_base=root)
    stat = leaf.stat()
    scope = {"kind": "linux-cgroup", "path": str(leaf), "device": stat.st_dev, "inode": stat.st_ino}
    removed = []
    monkeypatch.setattr(Path, "rmdir", lambda path: removed.append(path))
    if "nonsense" in events:
        with pytest.raises(LocalExecutionError):
            scopes.remove(scope)
        assert removed == []
    else:
        scopes.remove(scope)
        assert removed == [leaf]


def _tool_challenge_stream(tool, nonce, variant="ok"):
    """@brief Event streams shaped like Pi 1.4.0 output."""
    shell_output = "unrelated\n" if variant == "wrong-output" else f"{tool}\n"
    failed = variant == "failed"
    other = variant == "other-tool"  # the nonce printed by a tool that is not the shell
    shell = {"type": "tool_execution_end", "toolName": "read" if other else "bash",
             "isError": failed, "result": {"content": [{"type": "text", "text": shell_output}]}}
    reply = {"reply-only": f"{tool} {nonce}", "wrong-reply": "ADORE_OK_other",
             "early-reply": "ADORE_OK_other"}.get(variant, nonce)
    early = nonce if variant == "early-reply" else "I'll run the command once."
    finished = variant != "unfinished"
    replied = variant != "no-reply"
    # The tool-use turn before the final answer, as recorded live; the tool_execution_end
    # with result None is synthetic and exercises the guard for malformed events.
    before = [{"type": "message_end", "message": {"role": "assistant", "stopReason": "toolUse",
               "content": [{"type": "toolCall", "name": "bash", "text": early}]}},
              {"type": "tool_execution_end", "toolName": "bash", "isError": False,
               "result": None}]
    if variant == "early-reply":
        before[0]["message"]["content"] = [{"type": "text", "text": early}]
    between = []
    if variant in ("extra-tool", "extra-tool-after"):  # a failed other tool spoils nothing
        failed_other = {"type": "tool_execution_end", "toolName": "read", "isError": True,
                        "result": {"content": []}}
        if variant == "extra-tool":
            before = [*before, failed_other]
        else:
            between = [failed_other]
    final = ([{"type": "message_end", "message": {
        "role": "assistant", "stopReason": "stop" if finished else "length",
        "content": [{"type": "text", "text": reply}]}}] if replied else [])
    if variant in ("no-tool", "reply-only"):
        return [*before, *final]
    return [*before, shell, *between, *final]


@pytest.mark.parametrize(
    "variant, reason",
    [
        ("ok", "ready"),
        ("failed", "tool-call-failed"),
        ("no-tool", "tool-call-failed"),
        ("wrong-output", "tool-call-failed"),
        ("reply-only", "tool-call-failed"),
        ("wrong-reply", "invalid-response"),
        ("no-reply", "invalid-response"),
        ("unfinished", "invalid-response"),
        ("other-tool", "tool-call-failed"),
        ("extra-tool", "ready"),
        ("extra-tool-after", "ready"),
        ("bad-json", "invalid-response"),
        ("non-object", "invalid-response"),
        ("early-reply", "invalid-response"),
    ],
)
def test_local_model_challenge_requires_a_completed_shell_call(variant, reason):
    """@brief Completed RPC evidence needs the shell nonce and final assistant reply."""
    from adore.web.model_connection import _native_tool_response

    tool, nonce = "ADORE_TOOL_" + "a" * 32, "ADORE_OK_" + "b" * 32
    stream = _tool_challenge_stream(tool, nonce, variant)
    tail = {"bad-json": "\n{bad", "non-object": "\n[1]"}.get(variant, "")
    assert _native_tool_response("\n".join(map(json.dumps, stream)) + tail, tool, nonce) == reason


def test_local_aegis_preserves_the_existing_json_exchange_bound(tmp_path, monkeypatch):
    """@brief Native AEGIS stdout retains the established 4 MiB JSON bound."""
    from adore.aegis import AEGIS_STDOUT_FILE, MAX_JSON_BYTES

    config, _, backend, controller, work = local_fixture(tmp_path, monkeypatch)
    exchange = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, exchange, {})

    def output(argv, **kwargs):
        assert kwargs["stdout_limit"] == MAX_JSON_BYTES
        kwargs["stdout"].write_text(json.dumps({"journal": "x" * 100000}))
        kwargs["stderr"].write_text("")
        return CommandResult()

    controller.run_files = output
    target = backend.bind("run-1", backend.environment)
    assert target.run_files(
        ["pi", "status"], exchange / AEGIS_STDOUT_FILE, exchange / "aegis.stderr", timeout=1
    ).ok
    assert len((exchange / AEGIS_STDOUT_FILE).read_bytes()) > 65536


def test_local_review_apply_rechecks_native_identity_and_permissions(tmp_path, monkeypatch):
    """@brief Local account fields change only through review; read-only context stays accurate."""
    import re

    from adore.web.app import create_app
    from fastapi.testclient import TestClient

    from tests.test_web_pending_config import _headers, _project

    _config, context, _backend, _controller, _work = local_fixture(tmp_path, monkeypatch)
    profiles, path, _state = _project(tmp_path)
    text = path.read_text(encoding="utf-8").replace('backend = "container"', 'backend = "local"')
    text = re.sub(r"required_tool_checks = \[.*?\]", "required_tool_checks = []", text, flags=re.S)
    path.write_text(text, encoding="utf-8")
    with TestClient(create_app(profiles.home)) as client:
        headers = _headers(client)
        current = client.get("/api/v1/projects/alpha/config")
        assert current.status_code == 200
        environment = current.json()["executor_environment"]
        assert environment == {
            "backend": "local", "image": None, "config_path": str(path.resolve())}
        original = path.read_bytes()
        body = {"key": "local.path", "value": context["path"],
                "revision": current.json()["revision"]}
        assert client.post("/api/v1/projects/alpha/config/pending", json=body).status_code == 403
        direct = client.put("/api/v1/projects/alpha/config", json=body, headers=headers)
        assert direct.status_code == 409
        assert direct.json()["detail"]["code"] == "pending_config_required"
        staged = client.post("/api/v1/projects/alpha/config/pending", json=body, headers=headers)
        assert staged.status_code == 200, staged.text
        # Staging writes nothing until the reviewed apply.
        assert path.read_bytes() == original


# END OF FILE
