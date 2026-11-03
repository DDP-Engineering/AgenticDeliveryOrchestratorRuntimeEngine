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
import io
import json
from pathlib import Path
import subprocess
import sys

from adore import execution
from adore.config import ExecutorCommand, default_config, validate_config
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
    executable = tools / "opencode.exe"
    executable.write_bytes(b"injected native executable")
    config = default_config()
    config.execution.backend = "local"
    config.platform.repo = "owner/repo"
    config.worktree.repo_path = str(work)
    config.state.store_root = str(tmp_path / "state")
    config.delivery.reviewers = ["reviewer"]
    config.executor.commands["opencode"] = ExecutorCommand(
        command="opencode run --dir {worktree} -m {model} --format json {prompt}",
        model="openai/model",
    )
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
    # Probe tests inject the controller factory too. Its unused scope constructor
    # must not load Windows APIs when these same offline fixtures run on Linux.
    monkeypatch.setattr("adore.local_execution.NativeScopes", lambda *_args: None)

    class Controller:
        """@brief Injected native command boundary records environment and redaction."""

        calls = []
        controlled = []

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


@pytest.mark.parametrize("mode,reason,code", [
    ("ready", "ready", 0), ("stderr", "ready", 0),
    ("codex-version", "ready", 0), ("ansi-version", "ready", 0),
    ("missing", "executable-missing", None), ("auth", "credential-missing", 0),
    ("corrupt-auth", "credential-invalid", None),
    ("exit", "executor-exit", 7), ("timeout", "timeout", 124),
    ("version", "version-invalid", 0),
])
def test_local_prerequisite_retains_safe_cause(tmp_path, monkeypatch, mode, reason, code):
    """@brief Native prerequisites distinguish availability/auth/version without raw output."""
    from adore.web.app import _probe_setup

    config, context, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    config.executor.env_keys = []
    auth = Path(context["home"]) / ".local/share/opencode/auth.json"
    auth.parent.mkdir(parents=True)
    if mode != "auth":
        auth.write_text("bad-PRIVATE" if mode == "corrupt-auth" else "{}", encoding="utf-8")
    if mode == "missing":
        (Path(context["path"]) / "opencode.exe").unlink()

    def execute(argv, **kwargs):
        kwargs["stdout"].write_text("" if mode == "stderr" else
            "PRIVATE output" if mode == "version" else
            "codex-cli 0.115.0" if mode == "codex-version" else
            "\x1b[32m1.2.3\x1b[0m" if mode == "ansi-version" else "1.2.3", encoding="utf-8")
        kwargs["stderr"].write_text("1.2.3" if mode == "stderr" else "", encoding="utf-8")
        return CommandResult(exit_code=7 if mode == "exit" else
                             124 if mode == "timeout" else 0, timed_out=mode == "timeout")

    controller.run_files = execute
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *a: controller)
    result = _probe_setup(config, lambda argv, **kw: CommandResult(stdout="version 1.2.3"))
    assert result["checks"]["executor_cli"] is (reason == "ready")
    assert result["executor_probe"] == {"ready": reason == "ready", "reason": reason,
                                        "exit_code": code}
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("mode,reason", [
    ("timestamp", "ready"), ("bad-time", "invalid-response"),
    ("wrong-nonce", "invalid-response"), ("tool-finish", "invalid-response"),
    ("tool-part", "invalid-response"), ("bool-time", "invalid-response"),
    ("reversed-time", "invalid-response"), ("duplicate", "invalid-response"),
    ("huge-time", "invalid-response"),
    ("auth-error", "credential-invalid"), ("model-error", "model-unavailable"),
    ("error-after-success", "credential-invalid"), ("stderr-auth", "credential-invalid"),
])
def test_native_opencode_completion_and_provider_errors(tmp_path, monkeypatch, mode, reason):
    """@brief Completed text and zero-exit structured provider errors are interpreted correctly."""
    from adore.web.model_connection import probe_model_connection

    config, _, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *a: controller)

    def execute(argv, **kwargs):
        nonce = argv[-1].split()[-1]
        events = [{"type": "text", "part": {"text": nonce,
                   "time": {"start": 10, "end": 11 if mode != "bad-time" else "bad"}}}]
        if mode == "wrong-nonce":
            events[0]["part"]["text"] = "wrong"
        if mode == "bool-time":
            events[0]["part"]["time"]["end"] = True
        if mode == "reversed-time":
            events[0]["part"]["time"]["end"] = 9
        if mode == "huge-time":
            events[0]["part"]["time"]["end"] = 10 ** 999
        if mode == "tool-finish":
            events.append({"type": "step_finish", "part": {"reason": "tool-calls"}})
        if mode == "tool-part":
            events.append({"type": "message.part.updated", "part": {"type": "tool"}})
        if mode in {"auth-error", "error-after-success", "model-error"}:
            if mode != "error-after-success":
                events = []
            events.append({"type": "error", "error": {
                "name": "ProviderModelNotFoundError" if mode == "model-error" else "APIError",
                "data": {"statusCode": 401, "message": "PRIVATE-PROVIDER-DETAIL"}}})
        tool_nonce = argv[-1].split("echo ", 1)[1].split(". Then", 1)[0]
        events.insert(0, {"type": "tool_use", "part": {"tool": "bash", "state": {
            "status": "completed", "output": tool_nonce}}})
        raw = "\n".join(map(json.dumps, events))
        if mode == "duplicate":
            raw = raw.replace('"end": 11', '"end": 11, "end": 12')
        kwargs["stdout"].write_text(raw, encoding="utf-8")
        kwargs["stderr"].write_text("HTTP 401 Unauthorized PRIVATE" if mode == "stderr-auth"
                                    else "", encoding="utf-8")
        return CommandResult(exit_code=1 if mode == "stderr-auth" else 0)

    controller.run_files = execute
    result = probe_model_connection(config, None, tmp_path / "absent.env")
    assert result["reason"] == reason
    assert result["ready"] is (reason == "ready")
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("mode,reason", [("account", "account-mismatch"),
    ("permission", "permission-denied"), ("wrapped-permission", "permission-denied"),
    ("cleanup", "cleanup-failed")])
def test_local_prerequisite_account_scope_and_cleanup(tmp_path, monkeypatch, mode, reason):
    """@brief Real native boundary failures remain visible and cannot report success."""
    from adore.local_execution import probe_local_executor

    config, _, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    root = tmp_path / "probe"
    root.mkdir()
    monkeypatch.setattr("adore.local_execution.tempfile.mkdtemp", lambda **kw: str(root))
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *a: controller)
    if mode == "account":
        config.local.account = "different-account"
    elif mode in {"permission", "wrapped-permission"}:
        def denied(*a, **kw):
            if mode == "wrapped-permission":
                try:
                    raise PermissionError("PRIVATE-OS-DETAIL")
                except PermissionError as exc:
                    raise LocalExecutionError("native launch ownership failed") from exc
            raise PermissionError("PRIVATE-OS-DETAIL")
        controller.run_files = denied
    else:
        def cleanup(*a, **kw):
            raise LocalExecutionError("native scope cleanup not confirmed")
        controller.recover = cleanup
    result = probe_local_executor(config)
    assert result["ready"] is False and result["reason"] == reason
    assert "PRIVATE" not in json.dumps(result)


def test_local_selection_is_explicit_and_rejects_container_contracts(tmp_path):
    """@brief Explicit local mode retains defaults and fails closed on conflicts."""
    config = default_config()
    config.platform.repo = "owner/repo"
    config.worktree.repo_path = str(tmp_path)
    config.executor.commands["opencode"] = ExecutorCommand(
        command="opencode run --dir {worktree} -m {model} --format json {prompt}",
        model="openai/model",
    )
    config.delivery.reviewers = ["reviewer"]
    assert config.execution.backend == "container"
    config.execution.backend = "local"
    assert validate_config(config) == []
    assert config.local.account == "current"
    for field, value in [("preparation", "prepare.yml#setup@" + "a" * 40)]:
        setattr(config.execution, field, value)
        assert any("local" in issue for issue in validate_config(config))
        setattr(config.execution, field, "")
    config.container.egress.mode = "none"
    assert any("local" in issue for issue in validate_config(config))
    config.container.egress.mode = "open"
    config.executor.stage_host_auth = True
    assert any("local" in issue for issue in validate_config(config))


def test_local_backend_is_available_through_the_shared_contract():
    """@brief Local selection has an adapter on the established backend boundary."""
    assert hasattr(execution, "LocalBackend"), "local backend adapter is absent"


@pytest.mark.parametrize("system", ["Windows", "Linux"])
@pytest.mark.parametrize("pathext", [".COM;.EXE;.BAT;.CMD", None])
def test_local_environment_preserves_executable_extensions(tmp_path, monkeypatch, system, pathext):
    """@brief Preserve inherited shell extensions without inheriting unapproved secrets."""
    config, context, _, _, _ = local_fixture(tmp_path, monkeypatch)
    context["system"] = system
    if pathext is None:
        monkeypatch.delenv("PATHEXT", raising=False)
    else:
        monkeypatch.setenv("PATHEXT", pathext)
    monkeypatch.setenv("GITEA_TOKEN", "forge-secret")
    monkeypatch.setenv("UNAPPROVED_SECRET", "unapproved")

    env = local_environment(config, context)

    if pathext is None or system != "Windows":
        assert "PATHEXT" not in env
    else:
        assert env["PATHEXT"] == pathext
    assert env["PATH"] == context["path"]
    assert "GITEA_TOKEN" not in env and "UNAPPROVED_SECRET" not in env


def test_local_environment_preserves_auth_without_forge_credentials(tmp_path, monkeypatch):
    """@brief Native account auth is reused in place and approved secrets stay in memory."""
    config, context, backend, controller, work = local_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("GITHUB_TOKEN", "forge-secret")
    monkeypatch.setenv("UNAPPROVED_SECRET", "unapproved")
    config.local.environment.update(git_pager="less", PAGER="more")
    backend = LocalBackend(config, context=context, controller=controller)
    env = local_environment(config, context, {"OPENAI_API_KEY": "provider-secret"})
    assert env["GIT_PAGER"] == env["PAGER"] == "cat" and "git_pager" not in env
    assert "GITHUB_TOKEN" not in env and "UNAPPROVED_SECRET" not in env
    assert env["HOME"] == context["home"] and env["OPENAI_API_KEY"] == "provider-secret"
    auth = Path(context["home"]) / ".local/share/opencode/auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text('{"provider":{"refresh":"existing-subscription-secret"}}')
    io_dir = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, io_dir, env)
    resource = backend.resource_identity("run-1")
    target = backend.bind("run-1", env, resource)
    assert target(["opencode", "--version"], timeout=1).ok
    assert controller.calls[0][1]["env"]["GIT_PAGER"] == "cat"
    assert controller.calls[0][1]["secrets"] == ["existing-subscription-secret", "provider-secret"]
    assert auth.read_text() == '{"provider":{"refresh":"existing-subscription-secret"}}'
    assert not any(
        "existing-subscription-secret" in p.read_text() for p in io_dir.parent.rglob("*.json")
    )
    config.local.account = "another-account"
    with pytest.raises(LocalExecutionError):
        local_environment(config, context)


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


def test_local_opencode_environment_isolates_personal_configuration(tmp_path, monkeypatch):
    """@brief OpenCode resolves an ADORE-managed config home; auth data stays in place."""
    config, context, *_ = local_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "personal-config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "account-data"))
    managed = str(Path(config.state.store_root).resolve() / "executor-config")
    env = local_environment(config, context)
    assert env["XDG_CONFIG_HOME"] == managed
    assert env["OPENCODE_DISABLE_CLAUDE_CODE"] == "1"
    assert env["XDG_DATA_HOME"] == str(tmp_path / "account-data")
    config.executor.default = "codex"
    other = local_environment(config, context)
    assert other["XDG_CONFIG_HOME"] == str(tmp_path / "personal-config")
    assert "OPENCODE_DISABLE_CLAUDE_CODE" not in other


def test_local_opencode_environment_applies_permission_policy(tmp_path, monkeypatch):
    """@brief OpenCode tool calls run non-interactively while push and forge CLIs are denied."""
    config, context, *_ = local_fixture(tmp_path, monkeypatch)
    env = local_environment(config, context)
    assert json.loads(env["OPENCODE_PERMISSION"]) == {
        "edit": "allow",
        "bash": {
            "*": "allow", "git push*": "deny", "tea *": "deny", "gh *": "deny", "glab *": "deny"
        },
    }
    config.executor.default = "codex"
    assert "OPENCODE_PERMISSION" not in local_environment(config, context)


def test_local_environment_values_override_managed_opencode_settings(tmp_path, monkeypatch):
    """@brief Explicit operator values replace managed OpenCode entries and their directory."""
    config, context, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    own = str(tmp_path / "operator-config")
    config.local.environment.update(XDG_CONFIG_HOME=own, OPENCODE_PERMISSION='{"bash":"ask"}')
    env = local_environment(config, context)
    assert env["XDG_CONFIG_HOME"] == own and env["OPENCODE_PERMISSION"] == '{"bash":"ask"}'
    assert env["OPENCODE_DISABLE_CLAUDE_CODE"] == "1"
    config.local.environment["OPENCODE_DISABLE_CLAUDE_CODE"] = "0"
    assert local_environment(config, context)["OPENCODE_DISABLE_CLAUDE_CODE"] == "0"
    managed = Path(config.state.store_root) / "executor-config"
    if managed.exists():
        managed.rmdir()
    LocalBackend(config, context=context, controller=controller)
    assert not managed.exists()
    # Windows names are case-insensitive: an explicit lowercase name replaces the managed one;
    # other names keep their existing exact-name behavior.
    monkeypatch.setenv("LANG", "C")
    config.local.environment = {"xdg_config_home": own, "lang": "en"}
    env = local_environment(config, context)
    assert [key for key in env if key.upper() == "XDG_CONFIG_HOME"] == ["xdg_config_home"]
    assert env["LANG"] == "C" and env["lang"] == "en"
    # Linux names are case-sensitive, and other executors keep their inherited names.
    linux = local_environment(config, {**context, "system": "Linux"})
    assert linux["XDG_CONFIG_HOME"] == str(managed.resolve()) and linux["xdg_config_home"] == own
    personal = str(tmp_path / "personal-config")
    monkeypatch.setenv("XDG_CONFIG_HOME", personal)
    config.executor.default = "codex"
    assert local_environment(config, context)["XDG_CONFIG_HOME"] == personal
    config.executor.default = "opencode"
    LocalBackend(config, context=context, controller=controller)
    assert not managed.exists()


def test_local_backend_refuses_unavailable_managed_opencode_directory(tmp_path, monkeypatch):
    """@brief A managed config path that is not a directory stops before any native launch."""
    config, context, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    managed = Path(config.state.store_root) / "executor-config"
    assert managed.is_dir()
    managed.rmdir()
    managed.write_text("not a directory")
    with pytest.raises(LocalExecutionError, match="managed executor configuration"):
        LocalBackend(config, context=context, controller=controller)


@pytest.mark.parametrize("change", ["policy", "resource", "auth", "executable"])
def test_local_identity_and_auth_fail_closed_before_native_commands(tmp_path, monkeypatch, change):
    """@brief Drift and corrupt auth/runtime input cannot authorize native commands."""
    config, context, backend, controller, work = local_fixture(tmp_path, monkeypatch)
    io_dir = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, io_dir, {})
    target = backend.bind("run-1", backend.environment)
    if change == "policy":
        config.local.environment["LANG"] = "changed"
    elif change == "resource":
        (io_dir.parent / "local-control/runtime.json").write_text("{}")
    elif change == "executable":
        (Path(context["path"]) / "opencode.exe").write_bytes(b"replaced")
    else:
        auth = Path(context["home"]) / ".local/share/opencode/auth.json"
        auth.parent.mkdir(parents=True)
        auth.write_text('{"token":"first","token":"second"}')
    with pytest.raises(LocalExecutionError):
        target(["opencode", "--version"], timeout=1)
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
    def spawn(argv, **kwargs):
        assert kwargs["env"]["GIT_PAGER"] == kwargs["env"]["PAGER"] == "cat"
        assert kwargs["env"]["HOME"] == "selected"
        assert kwargs.get("creationflags", 0) == (0x08000000 if sys.platform == "win32" else 0)
        return process

    controller = LocalProcessController(scopes, spawn=spawn)
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


def test_local_gate_preserves_native_argv_files_and_archives(tmp_path):
    """@brief Native gates bypass shells and retain fresh questions/usage/archive proof."""
    from adore.execution import ExecutionPaths
    from adore.executor.launcher import CodexExecutor

    work, exchange = tmp_path / "work with spaces", tmp_path / "io with spaces"
    work.mkdir()
    exchange.mkdir()
    (work / "questions.md").write_text("stale")
    calls = []

    class Target:
        """@brief Native file target with no shell command surface."""

        paths = ExecutionPaths(str(work), str(exchange), "")

        def __call__(self, argv, **kwargs):
            raise AssertionError("local gate invoked shell transport")

        def run_files(self, argv, stdout, stderr, **kwargs):
            assert not (work / "questions.md").exists()
            calls.append(argv)
            stdout.write_text('{"usage":{"input_tokens":12,"output_tokens":4}}')
            stderr.write_text("")
            (work / "questions.md").write_text("operator question")
            return CommandResult(argv=[argv[0], "[native-file-launch]"])

    executor = CodexExecutor(
        "codex exec --json --model {model} {prompt}", "provider/model", "questions.md"
    )
    result = executor.run_gate(
        Target(), work, exchange, "space path & literal", timeout=2, archive_stem="native-build"
    )
    assert calls == [
        ["codex", "exec", "--json", "--model", "provider/model", "space path & literal"]
    ]
    assert result.has_questions and result.questions == "operator question"
    assert result.tokens_in == 12 and result.tokens_out == 4
    assert len(result.artifact_dirs) == 1
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
    assert result["model_probe"]["context"] == "executor-local"
    assert controller.calls and any("--version" in argv for argv, _ in controller.calls)
    assert controller.calls[0][1]["env"]["OPENAI_API_KEY"] == "readiness-provider-key"


@pytest.mark.parametrize("bad", [False, True])
def test_local_model_challenge_uses_configured_native_cli_and_rejects_incomplete_response(
    tmp_path, monkeypatch, bad
):
    """@brief Nonce proof uses the gate environment and rejects incomplete provider JSON."""
    from adore.web.model_connection import probe_model_connection

    config, context, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *args: controller)

    def command(argv, **kwargs):
        assert kwargs["env"]["HOME"] == context["home"]
        tool, nonce = _challenge_nonces(argv)
        events = _tool_challenge_stream("opencode", tool, nonce)
        kept = events[:-1] if bad else events  # bad drops the final step_finish (stop)
        kwargs["stdout"].write_text("\n".join(json.dumps(v) for v in kept))
        kwargs["stderr"].write_text("")
        return CommandResult()

    controller.run_files = command
    result = probe_model_connection(
        config, lambda *args, **kwargs: pytest.fail("container call"), tmp_path / "absent.env"
    )
    assert result["ready"] is (not bad)
    assert result["reason"] == ("invalid-response" if bad else "ready")


def test_local_assisted_setup_and_portable_rules_keep_machine_identity_local(tmp_path, monkeypatch):
    """@brief Setup selects native existing auth without container/tool installation."""
    import tomllib

    from adore.profiles import ProfileStore
    from adore.web.app import ProjectInput, _prepare_project
    from adore.wizard import ScriptedAsker, run_wizard

    from tests.test_wizard import _answers, _clone

    clone = _clone(tmp_path)
    store = ProfileStore(tmp_path / "profiles")
    answers = _answers(clone, execution_backend="local", auth_mode="existing")
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
    assert not document.get("executor", {}).get("stage_host_auth", False)
    assert setup.metadata["runtime"] == "local"
    body = ProjectInput(
        name="web-native",
        kind="github",
        repo="owner/repo",
        repo_path=str(clone),
        reviewers="reviewer",
        execution_backend="local",
        auth_mode="existing",
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
        config.container.egress.mode = "none"
    else:
        config.local.environment["OPENAI_API_KEY"] = "unsafe-persisted-secret"
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


def test_local_native_settings_accept_installed_entrypoint_and_refuse_shell(tmp_path, monkeypatch):
    """@brief Admin native argv settings use existing paths and reject shell operators."""
    from hashlib import sha256

    from adore.web.app import ConfigEdit, HTTPException, _candidate_config_edit

    config, context, _, _, work = local_fixture(tmp_path, monkeypatch)
    path = tmp_path / "config.toml"
    text = (
        '[execution]\nbackend="local"\n[platform]\nrepo="owner/repo"\n'
        "[worktree]\nrepo_path=" + json.dumps(str(work)) + "\n"
        '[delivery]\nreviewers=["reviewer"]\n[executor.opencode]\n'
        'command="opencode run --dir {worktree} -m {model} --format json {prompt}"\n'
        'model="openai/model"\n'
    )
    path.write_text(text)
    command = json.dumps(str(Path(context["path"]) / "opencode.exe")) + " run {prompt}"
    body = ConfigEdit(
        key="executor.opencode.command",
        value=command,
        revision=sha256(path.read_bytes()).hexdigest(),
    )
    _, candidate = _candidate_config_edit(path, body)
    assert command in __import__("tomllib").loads(candidate)["executor"]["opencode"]["command"]
    body.value += " && unwanted"
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
    raw += b'\n[local]\naccount="native-account"\nhome="/native-home"\npath="/native-tools"\n'
    raw += b'environment={LANG="native-language"}\n'
    raw = __import__("re").sub(
        rb"required_tool_checks = \[.*?\]",
        b"required_tool_checks = []",
        raw,
        flags=__import__("re").S,
    )
    encoded = export_settings(raw)
    for value in (
        b"native-account",
        b"native-home",
        b"native-tools",
        b"native-language",
        b'"local"',
    ):
        assert value not in encoded


def test_local_endpoint_probe_uses_owned_native_python(tmp_path, monkeypatch):
    """@brief Explicit compatible endpoint checks share native account policy without images."""
    from adore.web.endpoint_probe import probe_endpoint

    config, context, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    # Match the fixture's injected Windows identity on every test host.
    python = Path(context["path"]) / "python.exe"
    python.write_bytes(b"injected native Python executable")
    config.workflow.aegis_python = str(python)
    config.local.environment = {
        "OPENAI_BASE_URL": "http://model.test/v1",
        "OPENCODE_CONFIG_CONTENT": json.dumps(
            {
                "provider": {
                    "openai": {
                        "npm": "@ai-sdk/openai-compatible",
                        "options": {"baseURL": "http://model.test/v1"},
                        "models": {"model": {"name": "model"}},
                    }
                }
            }
        ),
    }
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *args: controller)

    def command(argv, **kwargs):
        kwargs["stdout"].write_text("ready")
        kwargs["stderr"].write_text("")
        return CommandResult()

    controller.run_files = command
    result = probe_endpoint(config, lambda *a, **kw: pytest.fail("container endpoint probe"))
    assert result["context"] == "executor-local" and result["ready"]


def test_local_node_entrypoint_drift_refuses_execution(tmp_path, monkeypatch):
    """@brief Explicit Windows npm entrypoints are pinned with the native executable."""
    config, context, _, controller, work = local_fixture(tmp_path, monkeypatch)
    node, script = Path(context["path"]) / "node.exe", Path(context["path"]) / "agent.js"
    node.write_bytes(b"installed node")
    script.write_text("installed executor")
    config.executor.default = "pi"
    config.executor.commands["pi"] = ExecutorCommand(
        command=json.dumps(str(node)) + " " + json.dumps(str(script)) + " -p {prompt}",
        model="openai/model",
    )
    backend = LocalBackend(config, context=context, controller=controller)
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


@pytest.mark.parametrize("content", ['{"provider":{"x":{"options":{"apiKey":"literal"}}}}', "{bad"])
def test_local_inline_configuration_refuses_literal_credentials(tmp_path, monkeypatch, content):
    """@brief Inline provider configuration cannot persist literal credentials or bad JSON."""
    config, _, _, _, _ = local_fixture(tmp_path, monkeypatch)
    assert validate_config(config) == []
    config.local.environment["OPENCODE_CONFIG_CONTENT"] = content
    assert any(issue.startswith("[local]") for issue in validate_config(config))


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
        backend.bind("run-1", backend.environment)(["opencode", "--version"])


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


@pytest.mark.parametrize("cancel", [False, True])
def test_local_child_release_barrier_and_cancel_are_native(tmp_path, monkeypatch, cancel):
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
    assert local_child.main(str(envelope)) == (125 if cancel else 7)
    assert bool(calls) is not cancel
    if calls:
        assert calls[0][0] == ["native", "prompt with spaces"]
        assert calls[0][1]["creationflags"] == 0x08000000
    envelope.write_text('{"unexpected":true}')
    with pytest.raises(ValueError):
        local_child.main(str(envelope))


@pytest.mark.parametrize("status", [0, 7])
def test_windows_supervisor_preserves_redirected_output(tmp_path, monkeypatch, status):
    """@brief A no-console supervisor must deliver both executor streams and its real exit."""
    from contextlib import redirect_stderr, redirect_stdout
    from types import SimpleNamespace

    from adore import local_child

    release = tmp_path / "release"
    release.touch()
    envelope = tmp_path / "command.json"
    envelope.write_text(json.dumps({"argv": ["installed.exe", "--version"],
        "cwd": str(tmp_path), "release": str(release),
        "scope": {"kind": "windows-job", "name": "owned"}}), encoding="utf-8")
    captured, errors = io.StringIO(), io.StringIO()

    def launch(argv, **kwargs):
        # Windows CREATE_NO_WINDOW does not reliably inherit an implicit stream.
        # Model that boundary: only explicitly forwarded handles retain output.
        if kwargs.get("stdout") is not None:
            kwargs["stdout"].write("1.19.3\n")
        if kwargs.get("stderr") is not None:
            kwargs["stderr"].write("executor diagnostic\n")
        assert kwargs["creationflags"] == 0x08000000
        return SimpleNamespace(returncode=status)

    monkeypatch.setattr(local_child.subprocess, "run", launch)
    with redirect_stdout(captured), redirect_stderr(errors):
        assert local_child.main(str(envelope)) == status
    assert captured.getvalue() == "1.19.3\n"
    assert errors.getvalue() == "executor diagnostic\n"


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


@pytest.mark.parametrize("kind", ["opencode", "pi", "codex", "qwen"])
@pytest.mark.parametrize("violation", ["none", "incomplete", "tool", "bad-json"])
def test_local_model_response_contract_all_executors(tmp_path, monkeypatch, kind, violation):
    """@brief Each native CLI needs completed nonce evidence and rejects tools/corrupt output."""
    from adore.web.model_connection import probe_model_connection

    config, context, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    (Path(context["path"]) / (kind + ".exe")).write_bytes(b"installed")
    config.executor.default = kind
    config.executor.commands[kind] = ExecutorCommand(
        command=kind + " --model {model} {prompt}", model="openai/model"
    )
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *args: controller)

    def execute(argv, **kwargs):
        tool, nonce = _challenge_nonces(argv)
        events = _tool_challenge_stream(kind, tool, nonce)
        if kind == "qwen":
            assert tool is None
            events = [{"type": "result", "result": nonce, "subtype": "success",
                       "is_error": False}]
        if violation == "incomplete":
            events = [{"type": "text", "part": {"text": nonce}}]
        if violation == "tool":
            # Qwen still refuses tools; the other agents must run the shell call.
            events = ([{"type": "tool", "part": {"type": "tool"}}, *events] if kind == "qwen"
                      else _tool_challenge_stream(kind, tool, nonce, "failed"))
        text = json.dumps(events) if kind == "qwen" else "\n".join(map(json.dumps, events))
        kwargs["stdout"].write_text("{bad" if violation == "bad-json" else text)
        kwargs["stderr"].write_text("")
        return CommandResult()

    controller.run_files = execute
    result = probe_model_connection(
        config, lambda *a, **kw: pytest.fail("container call"), tmp_path / "absent.env"
    )
    assert result["ready"] is (violation == "none")


@pytest.mark.parametrize("kind", ["pi", "codex"])
def test_local_pi_and_codex_judge_only_the_last_assistant_message(kind):
    """@brief An early message with the nonce does not count when the final reply differs."""
    from adore.web.model_connection import _native_tool_response

    tool, nonce = "ADORE_TOOL_" + "a" * 32, "ADORE_OK_" + "b" * 32
    stream = "\n".join(map(json.dumps, _tool_challenge_stream(kind, tool, nonce, "early-reply")))
    assert _native_tool_response(kind, stream, tool, nonce) == "invalid-response"


def test_local_codex_shell_call_needs_exit_code_zero():
    """@brief A Codex command needs status completed and exit code 0 to count as a shell call."""
    from adore.web.model_connection import _native_tool_response

    tool, nonce = "ADORE_TOOL_" + "a" * 32, "ADORE_OK_" + "b" * 32
    for variant in ("shell-exit", "shell-status"):
        events = _tool_challenge_stream("codex", tool, nonce, variant)
        stream = "\n".join(map(json.dumps, events))
        assert _native_tool_response("codex", stream, tool, nonce) == "tool-call-failed"
    good = "\n".join(map(json.dumps, _tool_challenge_stream("codex", tool, nonce)))
    assert _native_tool_response("codex", good, tool, nonce) == "ready"


def test_local_model_test_keeps_large_pi_streams_while_gates_keep_64_kib(tmp_path, monkeypatch):
    """@brief Pi repeats the conversation in its events; the test keeps 1 MiB, jobs 64 KiB."""
    from adore.web.model_connection import probe_model_connection

    config, context, backend, controller, work = local_fixture(tmp_path, monkeypatch)
    limits = []
    io_dir = Path(config.state.store_root) / "runs/run-1/io"
    backend.provision("run-1", work, work, io_dir, {})
    controller.run_files = lambda argv, **kwargs: (
        limits.append(kwargs["stdout_limit"]), kwargs["stdout"].write_text("ok"),
        kwargs["stderr"].write_text(""), CommandResult())[-1]
    gate = backend.bind("run-1", backend.environment)
    assert gate.run_files(["opencode", "--version"], io_dir / "out.txt", io_dir / "err.txt").ok
    assert limits == [65536]
    (Path(context["path"]) / "pi.exe").write_bytes(b"installed")
    config.executor.default = "pi"
    config.executor.commands["pi"] = ExecutorCommand(command="pi --model {model} {prompt}",
                                                     model="openai/model")
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *args: controller)

    def execute(argv, **kwargs):
        tool, nonce = _challenge_nonces(argv)
        limits.append(kwargs["stdout_limit"])
        history = {"type": "message_end", "message": {"role": "system", "content": "x" * 95000}}
        stream = [history, history, history, *_tool_challenge_stream("pi", tool, nonce)]
        kwargs["stdout"].write_text("\n".join(map(json.dumps, stream)))
        kwargs["stderr"].write_text("")
        return CommandResult()

    controller.run_files = execute
    result = probe_model_connection(
        config, lambda *a, **kw: pytest.fail("container call"), tmp_path / "absent.env"
    )
    assert (result["ready"], result["reason"], limits) == (True, "ready", [65536, 1048576])


def _challenge_nonces(argv):
    """@brief Read the tool nonce (when asked) and the trailing reply nonce from the prompt."""
    import re

    found = re.search(r"ADORE_TOOL_[0-9a-f]{32}", argv[-1])
    return (found.group(0) if found else None), argv[-1].split()[-1]


def _tool_challenge_stream(kind, tool, nonce, variant="ok"):
    """@brief Event streams shaped like OpenCode 1.19.4, Pi 1.4.0 and Codex 0.159.3 output."""
    shell_output = "unrelated\n" if variant == "wrong-output" else f"{tool}\n"
    failed = variant == "failed"
    other = variant == "other-tool"  # the nonce printed by a tool that is not the shell
    shell = {
        "opencode": {"type": "tool_use", "part": {"tool": "read" if other else "bash", "state": {
            "status": "error" if failed else "completed", "output": shell_output,
            "error": "The user rejected permission to use this specific tool call."
            if failed else None}}},
        "pi": {"type": "tool_execution_end", "toolName": "read" if other else "bash",
               "isError": failed, "result": {"content": [{"type": "text", "text": shell_output}]}},
        "codex": {"type": "item.completed", "item": {
            "type": "mcp_tool_call" if other else "command_execution",
            "status": "failed" if failed or variant == "shell-status" else "completed",
            "exit_code": 1 if failed or variant == "shell-exit" else 0,
            "aggregated_output": shell_output + "\r\n"}},
    }.get(kind)
    reply = {"reply-only": f"{tool} {nonce}", "wrong-reply": "ADORE_OK_other",
             "early-reply": "ADORE_OK_other"}.get(variant, nonce)
    early = nonce if variant == "early-reply" else "I'll run the command once."
    finished = variant != "unfinished"
    replied = variant != "no-reply"
    # The tool-use turn before the final answer, as recorded live; the Pi tool_execution_end
    # with result None is synthetic and exercises the guard for malformed events.
    before = {
        "opencode": [],
        "pi": [{"type": "message_end", "message": {"role": "assistant", "stopReason": "toolUse",
                "content": [{"type": "toolCall", "name": "bash", "text": early}]}},
               {"type": "tool_execution_end", "toolName": "bash", "isError": False,
                "result": None}],
        "codex": [{"type": "item.completed", "item": {"type": "agent_message", "text": early}}],
    }.get(kind, [])
    if kind == "pi" and variant == "early-reply":
        before[0]["message"]["content"] = [{"type": "text", "text": early}]
    between = ([{"type": "step_finish", "part": {"reason": "tool-calls"}}]
               if kind == "opencode" else [])
    if variant in ("extra-tool", "extra-tool-after"):  # a failed other tool spoils nothing
        failed_other = {
            "opencode": {"type": "tool_use", "part": {"tool": "read", "state": {
                "status": "error", "output": ""}}},
            "pi": {"type": "tool_execution_end", "toolName": "read", "isError": True,
                   "result": {"content": []}},
            "codex": {"type": "item.completed", "item": {
                "type": "mcp_tool_call", "status": "failed"}},
        }[kind]
        if variant == "extra-tool":
            before = [*before, failed_other]
        else:
            between = [*between, failed_other]
    final = {
        "opencode": [*([{"type": "text", "part": {"text": reply}}] if replied else []),
                     {"type": "step_finish", "part": {"reason": "stop" if finished else "length"}}],
        "pi": ([{"type": "message_end", "message": {
            "role": "assistant", "stopReason": "stop" if finished else "length",
            "content": [{"type": "text", "text": reply}]}}] if replied else []),
        "codex": [*([{"type": "item.completed", "item": {"type": "agent_message", "text": reply}}]
                    if replied else []),
                  *([{"type": "turn.completed"}] if finished else [])],
    }.get(kind, [])
    if variant in ("no-tool", "reply-only"):
        return [*before, *final]
    return [*before, shell, *between, *final]


@pytest.mark.parametrize("kind", ["opencode", "pi", "codex"])
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
        ("timeout", "timeout"),
        ("exit", "connection-failed"),
    ],
)
def test_local_model_challenge_requires_a_completed_shell_call(
    tmp_path, monkeypatch, kind, variant, reason
):
    """@brief Installed agents must run the shell nonce before their reply counts as ready."""
    from adore.web.model_connection import probe_model_connection

    config, context, _, controller, _ = local_fixture(tmp_path, monkeypatch)
    (Path(context["path"]) / (kind + ".exe")).write_bytes(b"installed")
    config.executor.default = kind
    config.executor.commands[kind] = ExecutorCommand(
        command=kind + " --model {model} {prompt}", model="openai/model"
    )
    monkeypatch.setattr("adore.local_execution.LocalProcessController", lambda *args: controller)
    seen = {}

    def execute(argv, **kwargs):
        tool, nonce = _challenge_nonces(argv)
        seen["timeout"], seen["tool"] = kwargs["timeout"], tool
        stream = _tool_challenge_stream(kind, tool, nonce, variant)
        text = "\n".join(map(json.dumps, stream))
        tail = {"bad-json": "\n{bad", "non-object": "\n[1]"}.get(variant, "")
        kwargs["stdout"].write_text(text + tail)
        kwargs["stderr"].write_text("")
        return CommandResult(exit_code=1 if variant == "exit" else 0,
                             timed_out=variant == "timeout")

    controller.run_files = execute
    result = probe_model_connection(
        config, lambda *a, **kw: pytest.fail("container call"), tmp_path / "absent.env"
    )
    assert seen["tool"] is not None and seen["timeout"] == 90
    assert (result["ready"], result["reason"]) == (reason == "ready", reason)


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
        ["opencode", "status"], exchange / AEGIS_STDOUT_FILE, exchange / "aegis.stderr", timeout=1
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
        body = {"key": "local.account", "value": context["account"],
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
